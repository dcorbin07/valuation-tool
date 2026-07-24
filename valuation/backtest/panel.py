"""
Panel construction for the backtest.

A panel is a long table: one row per (ticker, rebalance date) with the score
known on that date, the realized forward return over the holding horizon, and the
benchmark's forward return.

Two builders:
  * build_synthetic_panel — a known signal + noise, for validating the engine
    offline (it must detect real signal and reject pure noise).
  * build_price_panel — from real prices (free): a point-in-time MOMENTUM score
    (12-1 month return, computed only from data up to each date) paired with
    realized forward returns. This is survivorship-BIASED (free feeds only carry
    names still listed) and covers the momentum factor cleanly; a full
    point-in-time FUNDAMENTAL panel needs SEC EDGAR filing dates (see the runbook
    and the screener project's pit_data.py). You can inject that via `score_fn`.
"""
from __future__ import annotations

from typing import Optional, Callable

import numpy as np
import pandas as pd


def build_synthetic_panel(n_names=120, n_dates=40, signal=0.10, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        bench = float(rng.normal(0.008, 0.04))
        for i in range(n_names):
            score = float(rng.normal(0, 1))
            fwd = signal * score + float(rng.normal(0, 0.08)) + bench
            rows.append({"date": f"P{d:03d}", "ticker": f"T{i:03d}", "composite": score,
                         "momentum": score + float(rng.normal(0, 0.5)),
                         "value": score * 0.6 + float(rng.normal(0, 0.6)),
                         "fwd_ret": fwd, "bench_ret": bench})
    return pd.DataFrame(rows)


def build_price_panel(tickers: list, horizon_days: int = 21, lookback_years: int = 5,
                      rebalance_days: int = 21, benchmark: str = "SPY",
                      score_fn: Optional[Callable] = None,
                      price_fn: Optional[Callable] = None) -> pd.DataFrame:
    """Build a real-price panel. `price_fn(ticker)` -> (dates, closes); defaults to
    the free Stooq/yfinance feed. `score_fn(ticker, as_of_idx, closes)` -> score;
    defaults to point-in-time 12-1 momentum."""
    if price_fn is None:
        from ..screener.prices import close_series
        price_fn = lambda t: close_series(t, days=260 * lookback_years + 60)

    # Load aligned close series.
    series = {}
    for t in [benchmark] + list(tickers):
        dts, cl = price_fn(t)
        if dts and cl and len(cl) > 260:
            series[t] = pd.Series(cl, index=pd.to_datetime(dts))
    if benchmark not in series:
        raise RuntimeError(f"Could not load benchmark {benchmark} prices.")
    bench = series[benchmark]

    # Common trading calendar.
    cal = bench.index
    idxs = list(range(252, len(cal) - horizon_days, rebalance_days))

    def pit_momentum(closes, i):
        if i < 252:
            return None
        p0, p1 = closes.iloc[i - 252], closes.iloc[i - 21]
        return (p1 / p0 - 1.0) if p0 > 0 else None

    rows = []
    for i in idxs:
        date = cal[i]
        b0, b1 = bench.iloc[i], bench.iloc[i + horizon_days]
        bench_ret = (b1 / b0 - 1.0) if b0 > 0 else np.nan
        for t in tickers:
            s = series.get(t)
            if s is None:
                continue
            # align to benchmark calendar
            sa = s.reindex(cal).ffill()
            if i + horizon_days >= len(sa) or pd.isna(sa.iloc[i]) or pd.isna(sa.iloc[i + horizon_days]):
                continue
            fwd = sa.iloc[i + horizon_days] / sa.iloc[i] - 1.0 if sa.iloc[i] > 0 else np.nan
            score = score_fn(t, i, sa) if score_fn else pit_momentum(sa, i)
            if score is None or pd.isna(score) or pd.isna(fwd):
                continue
            rows.append({"date": str(date.date()), "ticker": t, "composite": float(score),
                         "momentum": float(score), "fwd_ret": float(fwd), "bench_ret": float(bench_ret)})
    return pd.DataFrame(rows)
