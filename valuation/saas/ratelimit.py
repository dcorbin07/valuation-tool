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
    # Not a path either: demo-SESSION CREATION (`auth.demo_view`), which costs nothing to
    # serve but is the one gate on the recruiter master-link. Limiting it means a leaked or
    # guessed token shows up as refused traffic in the logs instead of being farmed
    # silently. 20/hour is many more than a human opening a résumé link will ever need.
    "demo:session": (20, 3600),
}

# Stop a rotating-IP flood from growing the table without bound. Evicting the
# least-recently-seen key is the right trade: an attacker who can rotate IPs faster than
# this can already evade per-IP limiting, while ordinary users keep their counters.
_MAX_KEYS = 20000

_hits: dict = {}                 # (ip, bucket) -> [timestamps]
_seen: dict = {}                 # (ip, bucket) -> last touch, for eviction
_lock = threading.Lock()


def bucket_for(path: str, body: dict | None) -> str | None:
    """Which limit bucket this request falls into, or None for 'not limited'."""
    if path == "/api/value":
        return "ai:value" if (body or {}).get("run_ai") else None
    return path if path in LIMITS else None


def client_ip(request) -> str:
    """Best available client identity behind Render's proxy.

    Takes the RIGHTMOST X-Forwarded-For entry, not the leftmost. With exactly one trusted
    proxy in front, the rightmost hop is the address the proxy actually observed; the
    leftmost is whatever the client typed and is trivially spoofable, which would make the
    limiter bypassable by rotating a header.
    """
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.remote_addr or "unknown"


def check(ip: str, bucket: str, now: float | None = None):
    """Record a hit. Returns None if allowed, or `retry_after` seconds if over the limit.

    A blocked request is NOT recorded, so hammering a blocked endpoint cannot extend the
    penalty indefinitely -- the window still drains on schedule.
    """
    limit, window = LIMITS[bucket]
    if limit <= 0:               # a bucket configured to 0 is closed outright
        return window
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
        if len(stamps) >= limit:
            _hits[key] = stamps
            return max(1, int(window - (now - stamps[0])))
        stamps.append(now)
        _hits[key] = stamps
        return None


def reset():
    """Clear all counters (tests)."""
    with _lock:
        _hits.clear()
        _seen.clear()
