"""
Multi-factor, point-in-time PRICE panel for walk-forward optimization.

Builds several standard, price-derived factors that are all computable point-in-
time (no fundamentals needed), so the optimizer can honestly tune their weights on
free data today:
  mom_12_1  12-1 month momentum
  mom_3_1   3-1 month momentum
  reversal  negative last-month return (short-term reversal)
  trend     price vs its 200-day average
  low_vol   negative recent volatility (low-vol premium)

Each row is (date, ticker, factors…, fwd_ret, bench_ret) for one name at one
rebalance date, paired with the realized forward return. A fundamental composite
panel would add PIT fundamentals (see EDGE_LAB.md); this price panel is clean and
runs now.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TD = 252
FACTORS = ["mom_12_1", "mom_3_1", "reversal", "trend", "low_vol"]


def build_factor_panel(tickers, benchmark="SPY", price_fn=None, rebalance_days=21,
                       lookback_years=8) -> pd.DataFrame:
    if price_fn is None:
        from ..screener.prices import close_series
        price_fn = lambda t: close_series(t, days=TD * lookback_years + 60)

    series = {}
    for t in [benchmark] + list(tickers):
        d, c = price_fn(t)
        if d and c and len(c) > TD + 40:
            series[t] = pd.Series(c, index=pd.to_datetime(d))
    if benchmark not in series:
        return pd.DataFrame()
    frame = pd.DataFrame(series).sort_index().ffill()
    cal = frame.index
    bench = frame[benchmark]
    names = [t for t in tickers if t in frame.columns]

    rows = []
    for i in range(TD, len(cal) - rebalance_days, rebalance_days):
        b0, b1 = bench.iloc[i], bench.iloc[i + rebalance_days]
        bret = (b1 / b0 - 1.0) if b0 > 0 else np.nan
        for t in names:
            s = frame[t].values
            if np.isnan(s[i]) or s[i] <= 0 or np.isnan(s[i - TD]):
                continue
            sma200 = np.nanmean(s[i - 200:i]) if i >= 200 else np.nan
            recent = s[i - 63:i]
            rets = np.diff(recent) / recent[:-1]
            fwd = s[i + rebalance_days] / s[i] - 1.0
            rows.append({
                "date": str(cal[i].date()), "ticker": t,
                "mom_12_1": s[i - 21] / s[i - TD] - 1.0,
                "mom_3_1": s[i - 21] / s[i - 63] - 1.0 if s[i - 63] > 0 else np.nan,
                "reversal": -(s[i] / s[i - 21] - 1.0) if s[i - 21] > 0 else np.nan,
                "trend": (s[i] / sma200 - 1.0) if sma200 and sma200 > 0 else np.nan,
                "low_vol": -float(np.std(rets)) if len(rets) > 5 else np.nan,
                "fwd_ret": float(fwd), "bench_ret": float(bret),
            })
    return pd.DataFrame(rows)
