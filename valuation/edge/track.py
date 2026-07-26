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
            d, c = price_fn(t)
            cache[t] = pd.Series(c, index=pd.to_datetime(d)) if (d and c) else None
        return cache[t]

    bench = series(benchmark)
    computed = 0
    for p in picks:
        s = series(p["ticker"])
        if s is None or bench is None:
            continue
        rd = pd.to_datetime(p["run_date"])
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
    return {"computed": computed, "picks": len(picks)}


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
