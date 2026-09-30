"""
Live track record — the "paper account" that follows the tool's picks.

Every scan logs its top-N picks with the date. As time passes, `update_returns`
computes the realized forward return of each matured pick at 1m/3m/6m/1y and the
S&P's return over the same window, and stores it. `summary` then reports, per
horizon, the average pick return vs the benchmark, the alpha, and the hit rate —
an honest, accruing record of whether following the picks actually beats the S&P.

This complements the historical portfolio backtest: the backtest looks *back*
(with survivorship caveats), the track record accrues *forward* on real, dated
picks (survivorship-free going forward).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = (21, 63, 126, 252)   # ~1m, 3m, 6m, 1y (trading days)


def log_picks(store, source: str, run_date: str, tickers: list):
    store.save_track_picks(source, run_date,
                           [{"ticker": t, "rank": i + 1} for i, t in enumerate(tickers)])


def _calendar_index(dates) -> pd.DatetimeIndex:
    """Vendor date strings -> a NAIVE index of calendar dates, one convention for every vendor.

    **THE DEFECT THIS CLOSES (2026-09-30): NOTHING IN THIS TRACK HAD EVER MATURED.** Stooq returns
    plain `2026-09-29` strings and the yfinance fallback returns `2026-09-29 00:00:00-04:00`, so a
    yfinance-served series parsed to a TZ-AWARE index while `run_date` parsed NAIVE, and
    `searchsorted` raised `TypeError: Cannot compare tz-naive and tz-aware` on the first such
    ticker. The caller (`web/app._maybe_refresh_track`) swallowed it, so every horizon on the
    Track Record tab read "accruing" for seven weeks while picks from early August were long
    past a month old. `index_mark._closes` had already learned this (`utc=True`); this module
    had not.

    The DATE PART of the vendor's own string is kept, not a UTC conversion: `00:00-04:00` is the
    exchange's calendar day, and converting it to UTC first would move nothing today but would
    move the day for any vendor stamping later than midnight local.
    """
    return pd.DatetimeIndex(pd.to_datetime([str(d)[:10] for d in dates], errors="coerce"))


def update_returns(store, source: str, benchmark="SPY", horizons=HORIZONS,
                   price_fn=None, top=None) -> dict:
    if price_fn is None:
        from ..screener.prices import close_series
        price_fn = lambda t: close_series(t, days=1500)

    picks = store.all_track_picks(source)
    if top:
        picks = [p for p in picks if (p.get("rank") or 999) <= top]

    cache = {}
    def series(t):
        if t not in cache:
            try:
                d, c = price_fn(t)
            except Exception:                                           # noqa: BLE001
                d, c = None, None
            if d and c:
                sr = pd.Series(c, index=_calendar_index(d))
                sr = sr[~sr.index.isna()]
                # One row per calendar day, oldest first -- a vendor frame that repeats a day
                # (an intraday bar beside the close) would otherwise shift every horizon by one.
                sr = sr[~sr.index.duplicated(keep="last")].sort_index()
                cache[t] = sr if len(sr) else None
            else:
                cache[t] = None
        return cache[t]

    bench = series(benchmark)
    if bench is None:
        # Said, not swallowed: with no benchmark nothing can be scored, and a caller that only
        # sees `computed: 0` cannot tell that from "nothing has matured yet".
        return {"computed": 0, "picks": len(picks), "unpriced": [], "failed": [],
                "benchmark_priced": False}
    computed, unpriced, failed = 0, set(), []
    for p in picks:
        s = series(p["ticker"])
        if s is None:
            unpriced.add(p["ticker"])
            continue
        try:
            computed += _score_pick(store, source, p, s, bench, horizons)
        except Exception as e:                                          # noqa: BLE001
            # ONE bad pick must not stop the rest -- the loop used to die on the first
            # yfinance-served ticker and take every later pick with it.
            failed.append({"ticker": p.get("ticker"), "run_date": p.get("run_date"),
                           "error": type(e).__name__})
    return {"computed": computed, "picks": len(picks), "unpriced": sorted(unpriced),
            "failed": failed[:20], "n_failed": len(failed), "benchmark_priced": True}


#: Where a partly-finished refresh remembers how far it got. In the STORE, not in a module
#: global -- the whole defect is that the old gate and status lived in the process.
REFRESH_KEY = "track_refresh:%s"

#: Picks scored per invocation. Small enough that one call is a fraction of a request and a
#: deploy loses at most this many names' work, large enough that a cycle converges in a handful
#: of calls at the batch fetcher's measured ~7.7 names/s.
REFRESH_BUDGET = 60


def refresh_progress(store, source: str) -> dict:
    """What the last refresh got through. Safe to call on a cold store."""
    return store.get_meta(REFRESH_KEY % source, None) or {
        "cursor": 0, "picks": None, "computed": 0, "unpriced": [], "failed": 0,
        "cycle_started": None, "last_at": None, "done_at": None}


def refresh_step(store, source: str, benchmark: str = "SPY", horizons=HORIZONS,
                 budget: int = None, price_batch=None) -> dict:
    """Score the NEXT slice of logged picks and persist how far we got.

    **WHY THIS EXISTS.** The refresh was a per-process daemon thread behind a 12-hour gate held
    in a module global, doing all 410 picks in one pass with a per-name price fetch. Every
    deploy killed it and reset the gate, so it started from nothing each time and never
    finished -- measured 2026-09-30, 3 of 410 picks scored by 06:51Z across seven deploys.
    Three separate things had to change and all three are here: the work is BATCHED (one
    `yf.download` per chunk rather than one request per name), it is BOUNDED (`budget` picks per
    call), and the cursor is in the STORE so the next process CONTINUES instead of restarting.

    **THE CURSOR ADVANCES ONLY OVER WORK ACTUALLY DONE.** If the benchmark cannot be priced
    nothing can be scored, so the step returns without moving the cursor -- recording progress
    through names that were never scored is how a record silently skips them. A name no vendor
    could price is counted UNPRICED and the cursor does move past it: it was attempted, the
    answer is "no price today", and the next cycle asks again.
    """
    if price_batch is None:
        from ..screener.prices import get_history_batch

        def price_batch(ts):
            return get_history_batch(ts, days=1500)

    import datetime as _dt

    picks = store.all_track_picks(source)
    st = refresh_progress(store, source)
    n = len(picks)
    budget = int(budget or REFRESH_BUDGET)

    # A cycle that has finished, or one whose pick list changed under it, starts again.
    if st.get("cursor", 0) >= n or st.get("picks") not in (None, n):
        st = {"cursor": 0, "picks": n, "computed": 0, "unpriced": [], "failed": 0,
              "cycle_started": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
              "last_at": None, "done_at": None}
    st["picks"] = n
    if not n:
        st["done_at"] = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        store.set_meta(REFRESH_KEY % source, st)
        return dict(st, stepped=0, benchmark_priced=None)

    lo = int(st.get("cursor", 0))
    slice_ = picks[lo:lo + budget]
    want = sorted({benchmark} | {p["ticker"] for p in slice_})
    frames = price_batch(want)

    def series(t):
        df = frames.get(t)
        if df is None or not len(df):
            return None
        sr = pd.Series(list(df["Close"]), index=_calendar_index(list(df["Date"])))
        sr = sr[~sr.index.isna()]
        sr = sr[~sr.index.duplicated(keep="last")].sort_index()
        return sr if len(sr) else None

    bench = series(benchmark)
    if bench is None:
        # FAIL CLOSED: no benchmark, nothing scoreable, cursor UNMOVED so the slice is retried.
        st["last_at"] = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        store.set_meta(REFRESH_KEY % source, st)
        return dict(st, stepped=0, benchmark_priced=False)

    unpriced = set(st.get("unpriced") or [])
    for pk in slice_:
        sr = series(pk["ticker"])
        if sr is None:
            unpriced.add(pk["ticker"])
            continue
        try:
            st["computed"] = int(st.get("computed", 0)) + _score_pick(
                store, source, pk, sr, bench, horizons)
        except Exception:                                               # noqa: BLE001
            st["failed"] = int(st.get("failed", 0)) + 1

    st["cursor"] = lo + len(slice_)
    st["unpriced"] = sorted(unpriced)
    st["last_at"] = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if st["cursor"] >= n:
        st["done_at"] = st["last_at"]
    store.set_meta(REFRESH_KEY % source, st)
    return dict(st, stepped=len(slice_), benchmark_priced=True)


def _score_pick(store, source, p, s, bench, horizons) -> int:
    """Write every matured horizon (and the all-time mark) for one logged pick."""
    computed = 0
    rd = pd.to_datetime(str(p["run_date"])[:10])
    bi = bench.index.searchsorted(rd)
    si = s.index.searchsorted(rd)
    for h in horizons:
        if store.has_track_return(source, p["run_date"], p["ticker"], h):
            continue
        if si + h >= len(s) or bi + h >= len(bench) or si >= len(s) or bi >= len(bench):
            continue
        p0, p1 = s.iloc[si], s.iloc[si + h]
        b0, b1 = bench.iloc[bi], bench.iloc[bi + h]
        if p0 > 0 and b0 > 0:
            store.save_track_return(source, p["run_date"], p["ticker"], h,
                                    float(p1 / p0 - 1), float(b1 / b0 - 1))
            computed += 1
    # All-time (entry -> latest close): recomputed every refresh since it moves daily.
    if 0 <= si < len(s) and 0 <= bi < len(bench):
        p0, b0 = s.iloc[si], bench.iloc[bi]
        if p0 > 0 and b0 > 0:
            store.save_track_return(source, p["run_date"], p["ticker"], 0,
                                    float(s.iloc[-1] / p0 - 1), float(bench.iloc[-1] / b0 - 1))
    return computed


def summary(store, source: str, horizons=HORIZONS) -> dict:
    out = {}
    for h in list(horizons) + [0]:          # 0 = all-time (entry -> latest)
        rows = store.track_returns(source, h)
        key = "all" if h == 0 else str(h)
        if not rows:
            out[key] = None
            continue
        fr = np.array([r["fwd_ret"] for r in rows])
        br = np.array([r["bench_ret"] for r in rows])
        active = fr - br
        out[key] = {"n": len(rows), "avg_return": float(fr.mean()),
                    "avg_bench": float(br.mean()), "avg_alpha": float(active.mean()),
                    "hit_rate_vs_bench": float((active > 0).mean()),
                    "win_rate": float((fr > 0).mean())}
    return out
