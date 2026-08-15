"""Per-IP rate limiting for the endpoints that cost real money to serve.

SECURITY_AUDIT.md H1: OPEN_ACCESS defaults to true, so `gating.check_request` allows
everything under /api/ before any login check. That is a deliberate product decision and
this module does not argue with it — reading the hot list freely is the point. The problem
is narrower: four endpoints spend the OWNER's budget on every anonymous request.

    /api/signals/run   -> explain_top() -> an Anthropic call per run
    /api/scan/run      -> whole-market scan -> 3 FMP requests per uncached name
    /api/backtest/run  -> CPU-heavy on a 512 MB box
    /api/value         -> another Anthropic call, but ONLY when run_ai is set

A script looping any of those drains the API balance and starves the 22:23 UTC scan the
product depends on. No account or token is needed. There was no rate limiting anywhere in
the codebase, and FMP_MAX_CALLS defaults to 0 = unlimited.

The limits below are deliberately generous for a human clicking around and tight for a
loop. Anything not listed is not limited at all.

Deliberately in-memory: the service runs as a single Render instance, and a dependency-free
counter that works is worth more than a Redis-backed one that is not deployed. If the app is
ever scaled to multiple instances this becomes per-instance (i.e. N times looser) --
noted rather than hidden.
"""
from __future__ import annotations

import threading
import time

# path -> (max requests, window seconds). Only money/CPU endpoints appear here.
LIMITS = {
    "/api/signals/run": (3, 3600),      # Anthropic spend per call
    "/api/scan/run": (3, 3600),         # FMP quota, 3 requests per uncached name
    "/api/backtest/run": (10, 3600),    # CPU
    "/api/optimize/run": (10, 3600),    # CPU
    "/api/portfolio": (30, 3600),       # CPU
    "/api/export/pdf": (30, 3600),      # CPU (renders a document)
    "/api/export/excel": (30, 3600),
    # Not a path: /api/value is only limited when it asks for the AI layer. The plain
    # valuation is the product's core action and stays unlimited. See bucket_for().
    "ai:value": (20, 3600),
    # MA7. The line above was HALF RIGHT: the AI layer is a paid call, but the PLAIN
    # valuation reaches the same upstream. `/api/value` runs the full adaptive DCF on a
    # CALLER-SUPPLIED symbol, so it fetches that name's fundamentals — exactly the FMP quota
    # this module limits `/api/scan/run` to 3/hour to protect. The result cache defends
    # against REPEATS; nothing defended against ENUMERATION, and the universe is ~7,100 names.
    #
    # DENOMINATED IN NAME-VALUATIONS, NOT REQUESTS, because the requests are not the scarce
    # thing and they differ in cost by up to 25x. One `/api/value` costs 1; one `/api/rank`
    # costs the length of the list it was handed; one `/api/dip` costs its shortlist. A
    # per-REQUEST cap would have to be set for the worst case and would then be absurdly tight
    # for the common one — this way 120 buys either 120 single valuations or ~5 full 25-name
    # ranks or any mix, which is the same budget the audit proposed, charged correctly.
    #
    # Generous on purpose: 120/hour is far more than a human clicking around will reach, and
    # far less than an enumeration loop needs to be worth running.
    "vendor:valuation": (120, 3600),
    # Not a path either: demo-SESSION CREATION (`auth.demo_view`), which costs nothing to
    # serve but is the one gate on the recruiter master-link. Limiting it means a leaked or
    # guessed token shows up as refused traffic in the logs instead of being farmed
    # silently. 20/hour is many more than a human opening a résumé link will ever need.
    "demo:session": (20, 3600),
    # MA10. The admin token used to bypass this module ENTIRELY (`if bucket and not
    # _admin_ok()`), which made one credential simultaneously the key to the product and an
    # uncapped lever on the owner's Anthropic and FMP spend. It lives in two independent
    # stores (GitHub Actions secrets and Render env) and is read by ten scheduled jobs, so a
    # leak is not hypothetical and a hard exemption is the worst possible failure mode.
    #
    # Generous, not tight: the point is a CEILING, not a limit anyone legitimate will meet.
    # 600/hour is ten a minute sustained — every cron on the schedule put together uses a
    # small fraction of it, while a spend-draining loop hits it in seconds. Per-IP like every
    # other bucket, so the crons do not share a counter with each other or with a leak.
    "admin:api": (600, 3600),
}

#: The bucket an authenticated admin caller falls into, in place of the old total exemption.
ADMIN_BUCKET = "admin:api"

# Stop a rotating-IP flood from growing the table without bound. Evicting the
# least-recently-seen key is the right trade: an attacker who can rotate IPs faster than
# this can already evade per-IP limiting, while ordinary users keep their counters.
_MAX_KEYS = 20000

_hits: dict = {}                 # (ip, bucket) -> [timestamps]
_seen: dict = {}                 # (ip, bucket) -> last touch, for eviction
_lock = threading.Lock()


#: The shared upstream budget, denominated in NAME VALUATIONS (MA7).
VENDOR_BUCKET = "vendor:valuation"

#: What `/api/rank` will actually value, whatever the caller sends. Mirrors the `[:25]` slice
#: in `web/app.py::api_rank`; a test pins the two together so charging cannot drift from doing.
RANK_MAX = 25


def _vendor_cost(path: str, body: dict | None, args=None) -> int:
    """How many NAME VALUATIONS this request can cost upstream, worst case.

    Worst case, not actual: the limiter runs in `before_request`, so it cannot know which
    names will be cache hits. Over-charging a warm cache is the conservative direction and the
    only one available here — the alternative is to charge nothing until the damage is done.
    """
    body = body or {}
    if path == "/api/value":
        return 1
    if path == "/api/rank":
        tickers = body.get("tickers") or []
        n = len([t for t in tickers if str(t).strip()]) if isinstance(tickers, list) else 0
        return max(1, min(n, RANK_MAX))
    if path == "/api/dip":
        # The shortlist is CALLER-SUPPLIED, so the cost is caller-controlled. Constants are
        # imported rather than restated: a second copy of DEFAULT_SHORTLIST here is how the
        # charge and the fan-out come to disagree.
        try:
            from ..web import dip
            from ..web.query_params import clamp_int
            return clamp_int((args or {}).get("shortlist"),
                             default=dip.DEFAULT_SHORTLIST, cap=dip.MAX_SHORTLIST)
        except Exception:
            return 25          # fail EXPENSIVE: an unknown fan-out is charged the ceiling
    return 1


def buckets_for(path: str, body: dict | None, args=None):
    """Every (bucket, cost) this request must clear, or () for 'not limited'.

    A tuple rather than one bucket because a request can be scarce in two ways at once: an
    `/api/value` with `run_ai` spends the owner's FMP quota AND an Anthropic call, and the old
    single-bucket form could only charge it for one of them. Returning both means the AI cap
    stays exactly as tight as it was while the vendor cap now applies to every request.
    """
    if path in ("/api/value", "/api/rank", "/api/dip"):
        cost = _vendor_cost(path, body, args)
        out = [(VENDOR_BUCKET, cost)]
        if (body or {}).get("run_ai"):
            out.append(("ai:value", cost))
        return tuple(out)
    return ((path, 1),) if path in LIMITS else ()


def bucket_for(path: str, body: dict | None) -> str | None:
    """The PRIMARY bucket, or None. Kept for callers and tests that want one name.

    `buckets_for` is the authority — this returns only the first of what may be several, so a
    caller enforcing this alone would let the AI cap go unchecked on an `/api/value` run.
    """
    b = buckets_for(path, body)
    return b[0][0] if b else None


#: How many trusted proxies sit in front of this app. ONE on Render today.
#:
#: MA8. This number was never written down — it was implied by `parts[-1]`, and the audit's
#: point is that the code could not tell which world it was in. It has two opposite failure
#: modes and they are not symmetric:
#:
#:   * TOO LOW (configured 1, actually 2 — e.g. a CDN added in front of Render). The entry
#:     taken is the inner proxy's view of the OUTER one: a single shared address. EVERY
#:     visitor then lands in one bucket and the per-IP limiter silently becomes a GLOBAL cap
#:     that one scraper exhausts for everybody. Availability, for all users, quietly.
#:   * TOO HIGH (configured 2, actually 1). The entry taken is whatever the client typed,
#:     which is trivially spoofable, so the limiter is bypassed by rotating a header.
#:
#: Both are silent. Neither raises. `forwarded_shape()` below is what makes the choice
#: checkable against reality instead of assumed — see its docstring.
TRUSTED_PROXY_HOPS = 1

#: Observed X-Forwarded-For chain LENGTHS -> how many requests had that length. Counts only:
#: no address is retained here, so this diagnostic stores nothing about any visitor.
_xff_depths: dict = {}
_xff_seen = 0

#: Below this many observations `forwarded_shape` refuses to call it, rather than reporting a
#: confident verdict off three requests. A diagnostic that is green before it has evidence is
#: the vacuous-pass failure this project has now caught in four separate instruments.
_SHAPE_MIN_OBSERVATIONS = 20


def _trusted_hops() -> int:
    """The configured hop count, overridable without a code change.

    An env override exists because the day this number becomes wrong is the day a CDN is put
    in front of the app — a deploy-time infrastructure change, made by someone who should not
    have to edit Python to keep the limiter correct.
    """
    import os
    try:
        n = int(os.environ.get("TRUSTED_PROXY_HOPS") or TRUSTED_PROXY_HOPS)
    except (TypeError, ValueError):
        n = TRUSTED_PROXY_HOPS
    return max(1, n)


def client_ip(request) -> str:
    """Best available client identity behind Render's proxy.

    Takes the entry `TRUSTED_PROXY_HOPS` from the RIGHT of X-Forwarded-For, not the leftmost.
    With exactly one trusted proxy in front, the rightmost hop is the address the proxy
    actually observed; the leftmost is whatever the client typed and is trivially spoofable,
    which would make the limiter bypassable by rotating a header.

    A chain SHORTER than the configured hop count falls back to `remote_addr` — the direct
    peer, which is the one address that cannot be forged from off-box. Reading the leftmost
    entry instead would be reading the client's own claim, which is the failure mode the
    rightmost rule exists to avoid.
    """
    xff = request.headers.get("X-Forwarded-For", "")
    parts = [p.strip() for p in xff.split(",") if p.strip()] if xff else []
    with _lock:
        global _xff_seen
        _xff_seen += 1
        # Depths are bucketed at 10 so a pathological header cannot grow this dict.
        d = min(len(parts), 10)
        _xff_depths[d] = _xff_depths.get(d, 0) + 1
    hops = _trusted_hops()
    if len(parts) >= hops:
        return parts[-hops]
    return request.remote_addr or "unknown"


def forwarded_shape() -> dict:
    """Is `TRUSTED_PROXY_HOPS` right? Answer it from live traffic, not from assumption.

    MA8's own prescribed verification was "log the parsed value for a handful of real requests
    and compare with Render's own client-IP header — one deploy, one grep". This is that,
    without the deploy: the chain LENGTH is the whole question, and it is observable on every
    request the app already serves.

    Returns counts and a verdict. The verdict is `insufficient` until enough requests have been
    seen to mean anything, and `mismatch` is deliberately loud, because its consequence — one
    shared bucket for every visitor — looks exactly like "the rate limiter is working" from the
    inside.
    """
    with _lock:
        depths = dict(_xff_depths)
        seen = _xff_seen
    hops = _trusted_hops()
    modal = max(depths, key=lambda k: depths[k]) if depths else None
    if seen < _SHAPE_MIN_OBSERVATIONS:
        verdict = "insufficient"
        note = (f"only {seen} request(s) observed; needs {_SHAPE_MIN_OBSERVATIONS} before this "
                f"says anything. It is not evidence the configuration is right.")
    elif modal == hops:
        verdict = "consistent"
        note = f"chain length {modal} matches TRUSTED_PROXY_HOPS={hops}."
    elif modal is not None and modal > hops:
        verdict = "mismatch"
        note = (f"chain length {modal} EXCEEDS TRUSTED_PROXY_HOPS={hops}: the address being "
                f"bucketed is a proxy's, not a visitor's, so every visitor may be sharing one "
                f"rate-limit bucket. Set TRUSTED_PROXY_HOPS={modal}.")
    else:
        verdict = "mismatch"
        note = (f"chain length {modal} is BELOW TRUSTED_PROXY_HOPS={hops}: requests are falling "
                f"back to remote_addr. Set TRUSTED_PROXY_HOPS={modal or 1}.")
    return {"trusted_proxy_hops": hops, "requests_observed": seen,
            "chain_lengths": {str(k): v for k, v in sorted(depths.items())},
            "modal_chain_length": modal, "verdict": verdict, "note": note,
            "stores_addresses": False}


def check(ip: str, bucket: str, now: float | None = None, cost: int = 1):
    """Record a hit. Returns None if allowed, or `retry_after` seconds if over the limit.

    A blocked request is NOT recorded, so hammering a blocked endpoint cannot extend the
    penalty indefinitely -- the window still drains on schedule.

    `cost` (MA7) is how many units of the bucket this request consumes: one `/api/rank` over
    25 names costs 25 name-valuations, not one request. It defaults to 1, so every existing
    caller and every per-request bucket behaves exactly as before.

    A request that cannot AFFORD its cost is refused whole. It is never partially admitted --
    charging 12 of a 25-name request and running all 25 would be a limiter that reports a
    number it did not enforce.
    """
    limit, window = LIMITS[bucket]
    if limit <= 0:               # a bucket configured to 0 is closed outright
        return window
    cost = max(1, int(cost))
    now = time.time() if now is None else now
    key = (ip, bucket)
    with _lock:
        if len(_hits) > _MAX_KEYS:
            oldest = sorted(_seen.items(), key=lambda kv: kv[1])[: len(_hits) // 4]
            for k, _ in oldest:
                _hits.pop(k, None)
                _seen.pop(k, None)
        stamps = [t for t in _hits.get(key, []) if now - t < window]
        _seen[key] = now
        if len(stamps) + cost > limit:
            _hits[key] = stamps
            # An empty window with a cost above the whole limit would divide by an absent
            # first stamp; the caller can never afford it, so quote the full window.
            return max(1, int(window - (now - stamps[0]))) if stamps else window
        stamps.extend([now] * cost)
        _hits[key] = stamps
        return None


def reset():
    """Clear all counters (tests)."""
    global _xff_seen
    with _lock:
        _hits.clear()
        _seen.clear()
        _xff_depths.clear()
        _xff_seen = 0
