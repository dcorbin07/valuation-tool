"""
Rate-limit-tolerant live-input cache — batch, cache, resume.

WHY THIS EXISTS. Two full-universe measurements of the beta ladder died on Yahoo's rolling
quota (`HANDOFF_live_data_bugs.md` §7.1): run 1 made 402 corroborating calls in 3.7 minutes and
exhausted it; run 2 was worse — 302 of 403 names arrived with `beta=None` and a largely empty
`CompanyData`, so six names all reported an identical WACC of 5.26%, the signature of a name with
no market cap. The reportable run was 46 names, paced and serial.

The lesson recorded there is not about Yahoo: **a measurement that consumes the resource it is
measuring will report on its own exhaustion and call it a result.** So this module splits the two
things that were fused:

  * `fetch`  — the only phase that touches the network. Paced, batched, cached on disk, resumable,
               and it ABORTS cleanly when throttling appears rather than finishing with degraded
               data. A failed unit is never recorded, so the next run retries it.
  * `report` — ZERO network calls. It drives the REAL ladder (`valuation.engine.wacc._resolve_beta`)
               against the cache, so it is deterministic, re-runnable, and cannot be contaminated
               by the conditions it is reporting on.

WHAT IS BORROWED, AND FROM WHERE. The resume discipline is `mine_options_cache.py`'s, deliberately:
a JSON manifest as the ledger, saved atomically (tmp + `os.replace`) after every unit rather than
at the end; skip-existing keyed on STATUS not on file existence; and the tri-state rule at
`mine_options_cache.py:332-336` — a unit whose fetch FAILED is not written to the manifest at all,
so it is retried, while "the vendor genuinely has nothing" is durable and never refetched. That
distinction is the same one `BetaEstimate.unavailable` draws, and it is the whole reason a
throttled run cannot silently become a verdict.

SCOPE. New file. Nothing under `valuation/**` is edited — not `valuation/edge/**`, and not
`wacc.py` or `beta.py` either. The ladder and the estimator are IMPORTED AND DRIVEN, never
reimplemented, so the project keeps one definition of each.

THE TRAP THIS MODULE EXISTS TO AVOID, stated because it is silent. Batched `yf.download` returns a
**tz-naive** index; the market proxy from `beta._market_returns()` is **tz-aware**
(America/New_York). `compute_beta` intersects the two indices, so a naive batch yields ZERO paired
months, returns `unavailable`, and rung 3a of the ladder responds by keeping the vendor beta
untouched. Corroboration would be disabled on every name in the product with no error raised
anywhere — the "silently empty factor" class of defect this project has now hit five times.
`_align_index` is the fix and `tests/test_live_cache.py` pins it.

USAGE
    python -m scripts.live_cache capture           # pin the served universe (own API, not Yahoo)
    python -m scripts.live_cache fetch             # paced/batched/resumable Yahoo pull
    python -m scripts.live_cache report            # offline coverage + rung distribution
    python -m scripts.live_cache status            # what the cache holds right now

Re-run `fetch` until `status` reports no pending names. It picks up exactly where it stopped.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.request

# --------------------------------------------------------------------------------------------
# Frozen operating parameters. Committed in PREREG_v2f_live_coverage.md before any coverage
# number existed. Pacing may be made SLOWER at the command line but never faster than the guard.
# --------------------------------------------------------------------------------------------

SERVED_URL = "https://valquo.co/api/hotstocks?top=500"

#: Seconds between per-name vendor calls. Run 1 averaged ~0.55s/call across 402 names and
#: exhausted the quota; this is ~5x slower and is the pacing the reportable 46-name run used.
MIN_INTERVAL_S = 2.5

#: Uniform jitter added to the interval, so a long run does not present as a metronome.
JITTER_S = 0.75

#: Names per batched history call. `yf.download` fetches many tickers in ONE request, which is
#: what collapses ~500 history calls into ~13. Larger batches are one request but a bigger
#: response; 40 keeps a failure cheap to retry.
BATCH_SIZE = 40

#: Throttle events tolerated before the fetch aborts. NOT a retry budget — every throttle is
#: already retried with backoff. This is the circuit breaker that stops a run from grinding
#: through a quota outage and producing a cache full of holes.
THROTTLE_BUDGET = 5

#: Backoff after a throttle: 30s, 60s, 120s, capped.
BACKOFF_BASE_S = 30.0
BACKOFF_MAX_S = 240.0

#: Attempts per batch/name within a single run, before the unit is left for the next run.
MAX_ATTEMPTS = 3

#: The estimator's own window, restated so the cache records what it fetched.
BETA_PERIOD = "5y"
BETA_INTERVAL = "1mo"
MARKET_PROXY = "SPY"

#: Minimum paired months for a cached close series to count as COVERED (PREREG §4). Two is the
#: point below which `compute_beta` cannot regress at all; it is a coverage floor, not a quality
#: bar — the quality bars are the ladder's own MIN_BETA_OBSERVATIONS / MIN_COMPUTED_OBSERVATIONS.
MIN_PAIRED_MONTHS = 2

DEFAULT_ROOT = os.path.join("data", "live_cache")

TERMINAL_STATUSES = ("complete", "no_data")


# --------------------------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------------------------

def _root(root: str) -> str:
    return root or DEFAULT_ROOT


def _ensure(path: str) -> str:
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    return path


def log(root: str, msg: str) -> None:
    """Progress to stdout and to disk. Never raises — a logging failure must not kill a fetch."""
    line = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        _ensure(_root(root))
        with open(os.path.join(_root(root), "PROGRESS.txt"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _atomic_write_json(path: str, obj) -> None:
    """tmp + os.replace, the `theta_bulk`/`mine_options_cache` idiom.

    A half-written cache entry is worse than a missing one: the missing one is retried, the
    half-written one is skipped as complete.
    """
    _ensure(os.path.dirname(path))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------------------------
# Throttle detection and pacing
# --------------------------------------------------------------------------------------------

def _rate_limit_types():
    """yfinance's rate-limit exception, if this version has one.

    Nothing in the repository catches it today (grep: it appears only in prose), so every
    throttled call is currently swallowed by a bare `except Exception` and is indistinguishable
    from "no data". Detecting it is the point of this module.
    """
    out = []
    try:
        from yfinance.exceptions import YFRateLimitError
        out.append(YFRateLimitError)
    except Exception:
        pass
    return tuple(out)


_RL_TYPES = _rate_limit_types()
_RL_MARKERS = ("rate limit", "ratelimit", "429", "too many requests", "quota")


def is_throttle(exc: BaseException) -> bool:
    """True when the failure is the vendor refusing, not the data being absent."""
    if _RL_TYPES and isinstance(exc, _RL_TYPES):
        return True
    text = ("%s %s" % (type(exc).__name__, exc)).lower()
    return any(m in text for m in _RL_MARKERS)


class Guard:
    """Paces outbound calls, counts throttles, and trips a circuit breaker.

    The counter is checked CONTINUOUSLY and printed BEFORE any coverage figure, which is the
    §7.1 lesson made structural: run 2 discovered its contamination only at the end, by which
    point it had already produced numbers.
    """

    def __init__(self, min_interval=MIN_INTERVAL_S, jitter=JITTER_S,
                 budget=THROTTLE_BUDGET, sleep=time.sleep):
        self.min_interval = float(min_interval)
        self.jitter = float(jitter)
        self.budget = int(budget)
        self.throttles = 0
        self.calls = 0
        self._sleep = sleep
        self._last = 0.0

    @property
    def tripped(self) -> bool:
        return self.throttles >= self.budget

    def wait(self) -> None:
        gap = time.time() - self._last
        delay = self.min_interval + random.uniform(0, self.jitter) - gap
        if delay > 0:
            self._sleep(delay)
        self._last = time.time()
        self.calls += 1

    def note_throttle(self, attempt: int) -> float:
        self.throttles += 1
        back = min(BACKOFF_BASE_S * (2 ** max(attempt, 0)), BACKOFF_MAX_S)
        self._sleep(back)
        return back


# --------------------------------------------------------------------------------------------
# Manifest — the resume ledger
# --------------------------------------------------------------------------------------------

class Manifest:
    """Per-ticker, per-leg status. Saved atomically after EVERY unit of work.

    THE TRI-STATE RULE (`mine_options_cache.py:332-336`): only positive outcomes are durable.
    A throttled or failed unit is not recorded, so the next run retries it. This is what makes
    "covered" impossible to inflate by running into a quota wall.
    """

    def __init__(self, root: str):
        self.path = os.path.join(_root(root), "manifest.json")
        self.data = _read_json(self.path) or {}

    def status(self, ticker: str, leg: str):
        return (self.data.get(ticker) or {}).get(leg, {}).get("status")

    def done(self, ticker: str, leg: str) -> bool:
        return self.status(ticker, leg) in TERMINAL_STATUSES

    def mark(self, ticker: str, leg: str, status: str, **meta) -> None:
        if status not in TERMINAL_STATUSES:
            raise ValueError(
                "refusing to record non-terminal status %r: a failed fetch must stay unrecorded "
                "so it is retried" % status)
        rec = self.data.setdefault(ticker, {})
        rec[leg] = dict(meta, status=status, at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.save()

    def save(self) -> None:
        _atomic_write_json(self.path, self.data)


# --------------------------------------------------------------------------------------------
# Phase 1a — capture the served universe (our own API; NOT Yahoo, so not quota-bound)
# --------------------------------------------------------------------------------------------

def capture(root: str = DEFAULT_ROOT, url: str = SERVED_URL, timeout: int = 40,
            opener=None) -> dict:
    """Pin the served universe and the full snapshot rows to disk.

    The denominator is fixed HERE, before any per-name fetch, so it cannot drift mid-run and
    cannot be chosen once the numerator is known (PREREG §3).

    This is also the only route by which a checkout can see the real per-name record at all:
    `auto-scan.yml` runs the scan on a GitHub runner and POSTs to the live site, so the store on
    Render's disk is the only copy — and `/api/hotstocks` is its one public, credential-free
    window. It serves the LATEST scan date only, so the record can be accrued forward from a
    checkout but never backfilled.
    """
    root = _root(root)
    _ensure(root)
    if opener is None:
        def opener(u):
            return urllib.request.urlopen(u, timeout=timeout).read().decode("utf-8")
    payload = json.loads(opener(url))

    rows = payload.get("rows") or []
    scan_date = payload.get("scan_date") or ""
    tickers = [r["ticker"] for r in rows if r.get("ticker")]

    pinned = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": url,
        "scan_date": scan_date,
        "provider": payload.get("provider"),
        "universe_size": payload.get("universe_size"),
        "scored": payload.get("scored"),
        "n_rows": len(rows),
        "history": payload.get("history") or [],
        "tickers": tickers,
    }
    _atomic_write_json(os.path.join(root, "universe.json"), pinned)
    if scan_date:
        _atomic_write_json(os.path.join(root, "snapshot_%s.json" % scan_date), payload)
    log(root, "captured %d served names, scan_date=%s, universe_size=%s"
        % (len(tickers), scan_date or "?", payload.get("universe_size")))
    return pinned


def load_universe(root: str = DEFAULT_ROOT) -> dict:
    u = _read_json(os.path.join(_root(root), "universe.json"))
    if not u:
        raise SystemExit("no pinned universe — run `capture` first")
    return u


def seed_store(root: str = DEFAULT_ROOT, db_path: str | None = None) -> dict:
    """Write every captured snapshot into a DEDICATED store the theme meter can read.

    This is the bridge the V2 write-up said did not exist: the real per-name record accrues only
    on Render's disk, and `/api/hotstocks` is its one public window. Capturing it and replaying
    it through the project's OWN writer (`Store.save_snapshot`) means the meter reads real rows
    through the same loader it always used — no second format, no parallel schema.

    IT WRITES TO ITS OWN DATABASE, NEVER `data/screener.db`. The real store already carries a
    2099-01-01 test fixture (`tests/test_saas.py:200`) that wins `latest_scan_date()`; adding
    captured production rows to that same file would entangle a bug from another lane with this
    record. A separate file also means deleting it costs nothing.

    ONE CAPTURE IS ONE DATE. The endpoint serves only the latest scan, so this accrues the
    record FORWARD, one calendar day per run. It cannot backfill the eight earlier dates the
    endpoint lists in `history` — those exist only on Render.
    """
    import glob
    from valuation.screener.store import Store

    root = _root(root)
    db_path = db_path or os.path.join(root, "served.db")
    _ensure(os.path.dirname(db_path))
    st = Store(db_path)
    dates, total = [], 0
    for path in sorted(glob.glob(os.path.join(root, "snapshot_*.json"))):
        payload = _read_json(path) or {}
        rows = payload.get("rows") or []
        scan_date = payload.get("scan_date")
        if not scan_date or not rows:
            continue
        st.save_snapshot(scan_date, rows, provider=payload.get("provider") or "",
                         params={"universe_size": payload.get("universe_size"),
                                 "captured_from": payload.get("source") or SERVED_URL})
        dates.append(scan_date)
        total += len(rows)
    log(root, "seeded %s with %d rows across %d date(s): %s"
        % (db_path, total, len(dates), ", ".join(dates) or "none"))
    return {"db": db_path, "dates": dates, "n_rows": total}


def theme_coverage(root: str = DEFAULT_ROOT) -> dict:
    """Per-theme non-null coverage of the captured snapshot.

    The COVERAGE RULE, applied to the live product rather than to the panel: a theme that is
    null on every served row contributes nothing and can never be read, and nothing about a
    normal run surfaces that.
    """
    u = load_universe(root)
    payload = _read_json(os.path.join(_root(root), "snapshot_%s.json" % u["scan_date"])) or {}
    rows = payload.get("rows") or []
    vals, present = {}, set()
    for r in rows:
        factors = (r.get("extra") or {}).get("factors") or {}
        for k, v in factors.items():
            present.add(k)
            if v is not None:
                vals.setdefault(k, []).append(v)

    out = {}
    for k in sorted(present):
        got = vals.get(k, [])
        uniq = len(set(got))
        out[k] = {
            "n_non_null": len(got),
            "coverage": (len(got) / len(rows)) if rows else 0.0,
            "n_distinct": uniq,
            # PRESENT IS NOT USABLE, and reporting only the former is how a dead theme hides in
            # plain sight — `screen.py:288` says so, and the live feed proves it: `insider` is
            # 100% non-null and takes ONE distinct value, because with no insider_score
            # `build_frame` fills the column with the constant 0.0. A constant column has no
            # ranking information, so it cannot be corroborated, tuned, or measured.
            "degenerate": bool(got) and uniq < 2,
        }
    return {"scan_date": u.get("scan_date"), "n_rows": len(rows), "themes": out}


# --------------------------------------------------------------------------------------------
# Phase 1b — the Yahoo legs: batched closes + paced vendor betas
# --------------------------------------------------------------------------------------------

def _align_index(series, tz):
    """Make a batched close series comparable with the market proxy.

    See the module docstring: without this the intersection is empty and every name silently
    reports `unavailable`. Pinned by test.
    """
    if tz is not None and getattr(series.index, "tz", None) is None:
        return series.tz_localize(tz)
    if tz is None and getattr(series.index, "tz", None) is not None:
        return series.tz_localize(None)
    return series


def closes_path(root: str, ticker: str) -> str:
    return os.path.join(_root(root), "closes", "%s.json" % ticker.upper().replace("/", "_"))


def vendor_path(root: str, ticker: str) -> str:
    return os.path.join(_root(root), "vendor", "%s.json" % ticker.upper().replace("/", "_"))


def market_path(root: str) -> str:
    return os.path.join(_root(root), "market.json")


def _series_to_json(series) -> dict:
    """Serialize a close series so it survives the round trip EXACTLY.

    The obvious version — `str(timestamp)` — is wrong for a tz-aware monthly index and the
    breakage is delayed: five years of monthly closes straddle several DST changes, so the
    strings carry mixed UTC offsets ("-04:00" and "-05:00") and `pd.to_datetime` refuses to
    parse the list at all. Normalising to UTC and recording the zone separately keeps the
    instants unambiguous, and the reconstructed index compares equal to the original — which
    is the only property that matters, because `compute_beta` INTERSECTS this index with the
    market's.
    """
    tz = getattr(series.index, "tz", None)
    idx = series.index.tz_convert("UTC") if tz is not None else series.index
    return {"index": [i.isoformat() for i in idx],
            "tz": str(tz) if tz is not None else None,
            "values": [float(v) for v in series.values]}


def _json_to_series(obj):
    import pandas as pd
    if not obj or not obj.get("index"):
        return None
    tz = obj.get("tz")
    if tz:
        idx = pd.to_datetime(obj["index"], utc=True).tz_convert(tz)
    else:
        idx = pd.to_datetime(obj["index"])
    return pd.Series(obj["values"], index=idx)


def fetch_market(root: str, guard: Guard, downloader=None) -> bool:
    """Cache the market proxy's monthly closes so `report` needs no network at all."""
    root = _root(root)
    if _read_json(market_path(root)):
        return True
    guard.wait()
    try:
        s = (downloader or _download)([MARKET_PROXY])
        series = s.get(MARKET_PROXY)
        if series is None or len(series) < MIN_PAIRED_MONTHS:
            log(root, "market proxy %s returned nothing — will retry next run" % MARKET_PROXY)
            return False
        _atomic_write_json(market_path(root), _series_to_json(series))
        log(root, "cached market proxy %s (%d monthly closes)" % (MARKET_PROXY, len(series)))
        return True
    except Exception as e:
        log(root, "market proxy fetch failed (%s) — will retry next run" % type(e).__name__)
        return False


def _download(tickers):
    """One batched history request. Returns {ticker: Series of monthly closes}."""
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    d = yf.download(tickers=list(tickers), period=BETA_PERIOD, interval=BETA_INTERVAL,
                    progress=False, auto_adjust=True, threads=False)
    if d is None or len(d) == 0:
        return {}
    out = {}
    cols = getattr(d.columns, "levels", None)
    if cols is not None and "Close" in d.columns.get_level_values(0):
        close = d["Close"]
        for t in close.columns:
            s = close[t].dropna()
            if len(s):
                out[str(t)] = s
    elif "Close" in d.columns:
        s = d["Close"].dropna()
        if len(s):
            out[str(list(tickers)[0])] = s
    return out


def fetch_closes(tickers, root: str, manifest: Manifest, guard: Guard,
                 batch_size: int = BATCH_SIZE, downloader=None) -> dict:
    """Batched, resumable monthly-close pull.

    Batching is what makes this affordable: ~500 per-name history calls become ~13 requests.
    A batch that throttles is retried with backoff; if it still fails, NOTHING in it is
    recorded and the next run picks it up.
    """
    root = _root(root)
    pending = [t for t in tickers if not manifest.done(t, "closes")]
    stats = {"complete": 0, "no_data": 0, "deferred": 0, "batches": 0}
    if not pending:
        return stats

    mkt = _json_to_series(_read_json(market_path(root)))
    tz = getattr(mkt.index, "tz", None) if mkt is not None else None

    for start in range(0, len(pending), batch_size):
        if guard.tripped:
            log(root, "THROTTLE BUDGET EXHAUSTED (%d) — stopping cleanly; cache intact, "
                      "re-run to resume" % guard.throttles)
            break
        batch = pending[start:start + batch_size]
        stats["batches"] += 1
        got = None
        for attempt in range(MAX_ATTEMPTS):
            guard.wait()
            try:
                got = (downloader or _download)(batch)
                break
            except Exception as e:
                if is_throttle(e):
                    back = guard.note_throttle(attempt)
                    log(root, "throttled on batch %d (%s); backed off %.0fs (%d/%d)"
                        % (stats["batches"], type(e).__name__, back, guard.throttles,
                           guard.budget))
                    if guard.tripped:
                        break
                else:
                    log(root, "batch %d failed (%s: %s)"
                        % (stats["batches"], type(e).__name__, e))
                    break
        if got is None:
            stats["deferred"] += len(batch)
            log(root, "batch %d deferred — %d names left unrecorded for the next run"
                % (stats["batches"], len(batch)))
            continue

        for t in batch:
            s = got.get(t)
            if s is None or len(s) < MIN_PAIRED_MONTHS:
                # The vendor answered and had nothing for this name. That IS durable — a
                # delisted or unlisted ticker will not sprout history on a retry.
                if got:
                    manifest.mark(t, "closes", "no_data", n=0 if s is None else int(len(s)))
                    stats["no_data"] += 1
                else:
                    stats["deferred"] += 1
                continue
            s = _align_index(s, tz)
            _atomic_write_json(closes_path(root, t), _series_to_json(s))
            manifest.mark(t, "closes", "complete", n=int(len(s)))
            stats["complete"] += 1
        log(root, "closes batch %d/%d: +%d complete, +%d no_data (throttles %d)"
            % (stats["batches"], (len(pending) + batch_size - 1) // batch_size,
               stats["complete"], stats["no_data"], guard.throttles))
    return stats


def _vendor_beta(ticker: str):
    """The single vendor field the whole ladder starts from (`yahoo.py:194`)."""
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    info = yf.Ticker(ticker).info or {}
    b = info.get("beta")
    return (float(b) if isinstance(b, (int, float)) else None), bool(info)


def fetch_vendor(tickers, root: str, manifest: Manifest, guard: Guard, getter=None) -> dict:
    """Paced per-name vendor-beta pull. This is the leg that cannot be batched.

    `beta` lives in `.info`, which is one request per name — so this is where the quota goes and
    where the pacing matters. A name that throttles is left unrecorded and retried.
    """
    root = _root(root)
    pending = [t for t in tickers if not manifest.done(t, "vendor")]
    stats = {"complete": 0, "no_data": 0, "deferred": 0}
    for i, t in enumerate(pending):
        if guard.tripped:
            log(root, "THROTTLE BUDGET EXHAUSTED (%d) — stopping cleanly at %d/%d; "
                      "re-run to resume" % (guard.throttles, i, len(pending)))
            break
        done = False
        for attempt in range(MAX_ATTEMPTS):
            guard.wait()
            try:
                beta, had_info = (getter or _vendor_beta)(t)
                if not had_info:
                    break                # empty payload: a failed fetch, counted once below
                _atomic_write_json(vendor_path(root, t),
                                   {"ticker": t, "beta": beta,
                                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
                manifest.mark(t, "vendor", "complete", beta=beta)
                stats["complete"] += 1
                done = True
                break
            except Exception as e:
                if is_throttle(e):
                    back = guard.note_throttle(attempt)
                    log(root, "throttled on %s; backed off %.0fs (%d/%d)"
                        % (t, back, guard.throttles, guard.budget))
                    if guard.tripped:
                        break
                else:
                    break
        if not done and not guard.tripped:
            stats["deferred"] += 1
        if (i + 1) % 25 == 0:
            log(root, "vendor %d/%d: %d complete, %d deferred, throttles %d"
                % (i + 1, len(pending), stats["complete"], stats["deferred"], guard.throttles))
    return stats


# --------------------------------------------------------------------------------------------
# Phase 2 — the offline report. ZERO network calls.
# --------------------------------------------------------------------------------------------

def load_closes(root: str, ticker: str):
    return _json_to_series(_read_json(closes_path(_root(root), ticker)))


class offline_beta:
    """Context manager: make `compute_beta` read the cache instead of the network.

    It PRIMES the estimator's own market cache and INJECTS cached closes into the real
    `compute_beta`, so the arithmetic executed is the shipped arithmetic — this does not
    reimplement the estimator, it feeds it. That is what keeps the report comparable with the
    46-name run in the record.

    Runtime injection, in a script, restored on exit. `tests/test_engine.py` already stubs this
    same function so its tests cannot touch the network; this is that pattern, not a new one.
    """

    def __init__(self, root: str):
        self.root = _root(root)
        self._saved = None

    def __enter__(self):
        import valuation.data.beta as B
        mkt = _json_to_series(_read_json(market_path(self.root)))
        if mkt is None:
            raise SystemExit("market proxy not cached — run `fetch` first")
        B._MKT.update(returns=mkt.pct_change().dropna(), ts=time.time())
        real = B.compute_beta
        self._saved = (B, real)

        def cached(ticker, closes=None):
            if closes is None:
                closes = load_closes(self.root, ticker)
            if closes is None:
                return B.BetaEstimate(None, 0, error="closes not cached")
            return real(ticker, closes=closes)

        B.compute_beta = cached
        return self

    def __exit__(self, *exc):
        B, real = self._saved
        B.compute_beta = real
        return False


def resolve_all(root: str, tickers) -> dict:
    """Drive the REAL ladder over the cache and count rungs. No network."""
    from valuation.data.models import CompanyData
    from valuation.engine.wacc import _resolve_beta

    rungs, rows, uncovered = {}, [], []
    if not list(tickers):
        # Nothing to resolve. Do NOT open the offline context — it requires a cached market
        # proxy, and demanding one to report "zero covered names" would make the report refuse
        # in exactly the state it most needs to describe.
        return {"rungs": rungs, "rows": rows, "uncovered": uncovered}
    with offline_beta(root):
        for t in tickers:
            v = _read_json(vendor_path(root, t))
            closes = load_closes(root, t)
            if v is None:
                uncovered.append((t, "vendor field not cached"))
                continue
            cd = CompanyData(ticker=t, beta=v.get("beta"))
            notes = []
            beta, prov = _resolve_beta(cd, None, notes)
            rungs[prov.source] = rungs.get(prov.source, 0) + 1
            rows.append({"ticker": t, "beta": beta, "rung": prov.source,
                         "vendor": v.get("beta"),
                         "n_observations": prov.n_observations,
                         "substituted": bool(prov.substituted),
                         "n_closes": int(len(closes)) if closes is not None else 0})
    return {"rungs": rungs, "rows": rows, "uncovered": uncovered}


def coverage(root: str = DEFAULT_ROOT) -> dict:
    """Coverage exactly as PREREG §4 defines it: what the ladder can be RUN on, offline."""
    root = _root(root)
    u = load_universe(root)
    tickers = u["tickers"]
    man = Manifest(root)

    covered, partial = [], []
    for t in tickers:
        has_vendor = _read_json(vendor_path(root, t)) is not None
        s = load_closes(root, t)
        has_closes = s is not None and len(s) >= MIN_PAIRED_MONTHS
        no_data = man.status(t, "closes") == "no_data"
        if has_vendor and (has_closes or no_data):
            covered.append(t)
        else:
            partial.append({"ticker": t, "vendor": has_vendor,
                            "closes": bool(has_closes), "closes_status": man.status(t, "closes")})
    n = len(tickers)
    return {
        "scan_date": u.get("scan_date"),
        "captured_at": u.get("captured_at"),
        "n_served": n,
        "n_covered": len(covered),
        "coverage": (len(covered) / n) if n else 0.0,
        "covered": covered,
        "not_covered": partial,
    }


def report(root: str = DEFAULT_ROOT, out: str | None = None) -> dict:
    root = _root(root)
    cov = coverage(root)
    res = resolve_all(root, cov["covered"])
    themes = theme_coverage(root)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "network_calls": 0,
        "universe": {k: cov[k] for k in ("scan_date", "captured_at", "n_served",
                                         "n_covered", "coverage")},
        "beta": {"rungs": res["rungs"], "n_resolved": len(res["rows"])},
        "themes": themes,
        "not_covered_sample": cov["not_covered"][:25],
        "rows": res["rows"],
    }
    if out:
        _atomic_write_json(out, payload)
    return payload


def render(payload: dict) -> str:
    u, b = payload["universe"], payload["beta"]
    L = []
    L.append("LIVE-INPUT COVERAGE — served universe %s (captured %s)"
             % (u["scan_date"], u["captured_at"]))
    L.append("=" * 78)
    L.append("")
    L.append("BETA LADDER — coverage %d / %d served names (%.1f%%)"
             % (u["n_covered"], u["n_served"], 100.0 * u["coverage"]))
    L.append("  a name counts only if the ladder RUNS on it offline (PREREG §4).")
    L.append("")
    if b["rungs"]:
        L.append("  rung distribution over %d resolved names:" % b["n_resolved"])
        for k, v in sorted(b["rungs"].items(), key=lambda kv: -kv[1]):
            L.append("    %-24s %5d  %5.1f%%" % (k, v, 100.0 * v / max(b["n_resolved"], 1)))
    else:
        L.append("  nothing resolved yet — run `fetch`.")
    L.append("")
    t = payload["themes"]
    L.append("LIVE THEME COVERAGE — %d served rows, scan_date %s"
             % (t["n_rows"], t["scan_date"]))
    L.append("    %-22s %5s %7s %8s" % ("theme", "n", "cov", "distinct"))
    dead = []
    for k, v in sorted(t["themes"].items(), key=lambda kv: -kv[1]["coverage"]):
        if v["n_non_null"] == 0:
            flag, why = "   <-- ABSENT", "absent"
        elif v["degenerate"]:
            flag, why = "   <-- CONSTANT: reads as covered, contributes nothing", "constant"
        else:
            flag, why = "", None
        if why:
            dead.append((k, why))
        L.append("    %-22s %5d %6.1f%% %8d%s"
                 % (k, v["n_non_null"], 100.0 * v["coverage"], v["n_distinct"], flag))
    L.append("")
    L.append("A theme at 0% is not thin, it is ABSENT, and a CONSTANT theme is not covered at")
    L.append("100% — it carries no ranking information at all. Neither is fixed by elapsed time")
    L.append("or by breadth: both are writer defects, not coverage ones.")
    if dead:
        L.append("")
        L.append("  contributing nothing to the live score: %s"
                 % ", ".join("%s (%s)" % (k, w) for k, w in dead))
    return "\n".join(L)


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------

def status(root: str = DEFAULT_ROOT) -> dict:
    root = _root(root)
    u = _read_json(os.path.join(root, "universe.json"))
    if not u:
        return {"pinned": False}
    man = Manifest(root)
    tickers = u["tickers"]
    return {
        "pinned": True,
        "scan_date": u["scan_date"],
        "n_served": len(tickers),
        "closes_done": sum(1 for t in tickers if man.done(t, "closes")),
        "vendor_done": sum(1 for t in tickers if man.done(t, "vendor")),
        "market_cached": _read_json(market_path(root)) is not None,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("mode", choices=["capture", "fetch", "report", "status", "seed"])
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.add_argument("--limit", type=int, default=None,
                   help="fetch only the first N served names (smoke test; say so if you quote it)")
    p.add_argument("--interval", type=float, default=MIN_INTERVAL_S,
                   help="seconds between vendor calls; may be raised, not lowered below the guard")
    p.add_argument("--batch", type=int, default=BATCH_SIZE)
    p.add_argument("--budget", type=int, default=THROTTLE_BUDGET)
    p.add_argument("--out", default=None, help="write the report JSON here")
    p.add_argument("--db", default=None,
                   help="seed mode: where to write the captured store "
                        "(default <root>/served.db; NEVER data/screener.db)")
    a = p.parse_args(argv)
    root = _root(a.root)

    if a.mode == "capture":
        capture(root)
        print(json.dumps(status(root), indent=2))
        return 0

    if a.mode == "status":
        print(json.dumps(status(root), indent=2))
        return 0

    if a.mode == "seed":
        print(json.dumps(seed_store(root, a.db), indent=2))
        return 0

    if a.mode == "fetch":
        u = load_universe(root)
        tickers = u["tickers"][:a.limit] if a.limit else u["tickers"]
        man = Manifest(root)
        guard = Guard(min_interval=max(a.interval, 0.0), budget=a.budget)
        log(root, "fetch start: %d names, interval %.2fs, batch %d, throttle budget %d"
            % (len(tickers), a.interval, a.batch, a.budget))
        if not fetch_market(root, guard):
            log(root, "market proxy unavailable — aborting; nothing recorded")
            return 2
        c = fetch_closes(tickers, root, man, guard, batch_size=a.batch)
        v = fetch_vendor(tickers, root, man, guard)
        # THE CONTAMINATION COUNT IS PRINTED BEFORE ANY COVERAGE FIGURE. PREREG §5.
        log(root, "THROTTLE EVENTS THIS RUN: %d (budget %d)%s"
            % (guard.throttles, guard.budget,
               "  <-- ABORTED EARLY" if guard.tripped else ""))
        log(root, "closes: %s" % c)
        log(root, "vendor: %s" % v)
        print(json.dumps(status(root), indent=2))
        return 0

    payload = report(root, out=a.out)
    print(render(payload))
    if a.out:
        print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
