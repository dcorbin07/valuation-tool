"""
Portfolio backtest — "if I had followed the tool's picks, would I have beaten the
S&P?"

Simulates holding an equal-weight basket of the top-N ranked names, rebalanced on
a fixed cadence, over the full price history, then reports the outcome at 1-, 5-,
and 10-year horizons vs a benchmark (SPY): CAGR, total return, volatility, Sharpe,
max drawdown, and alpha (excess CAGR). After costs.

The ranking at each rebalance date uses ONLY data up to that date (point-in-time),
so there's no look-ahead. `score_fn(ticker, i, closes)` plugs in the signal you're
testing — momentum by default, or the intraday technical score (feeds the Signals
tab into the backtest). Fundamental-composite ranking needs point-in-time
fundamentals (see EDGE_LAB.md); the price-based path is clean and works today.

Honest caveat: free price history only includes names still listed, so results
carry SURVIVORSHIP BIAS and overstate edge. Treat a positive result as "worth
confirming on survivorship-free data," not proof.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# ---------------- score functions (point-in-time) ---------------- #
def momentum_score(ticker, i, closes):
    """12-1 month momentum known at bar i."""
    if i < TRADING_DAYS:
        return None
    p0, p1 = closes[i - TRADING_DAYS], closes[i - 21]
    return (p1 / p0 - 1.0) if p0 > 0 else None


def technical_score_fn(ticker, i, closes):
    """Intraday technical setup score using only bars up to i (feeds Signals → backtest)."""
    from ..intraday.technical import technical_signals
    if i < 60:
        return None
    window = list(closes[max(0, i - 400):i + 1])
    res = technical_signals({"close": window})
    return res.get("score")


# ---------------- simulation ---------------- #
def simulate(price_frame: pd.DataFrame, score_fn=momentum_score, benchmark="SPY",
             hold_top=10, rebalance_days=21, cost_bps=10.0, warmup=252) -> dict:
    cal = price_frame.index
    tickers = [c for c in price_frame.columns if c != benchmark]
    rt = 2 * cost_bps / 1e4
    reb = list(range(warmup, len(cal) - 1, rebalance_days))
    if len(reb) < 2:
        return {"error": "not enough history"}

    port_daily, dates = [], []
    for k, i in enumerate(reb):
        nexti = reb[k + 1] if k + 1 < len(reb) else len(cal) - 1
        scored = []
        for t in tickers:
            s = score_fn(t, i, price_frame[t].values)
            if s is not None and not (isinstance(s, float) and np.isnan(s)):
                scored.append((t, s))
        scored.sort(key=lambda x: -x[1])
        held = [t for t, _ in scored[:hold_top]]
        for j in range(i, nexti):
            if held:
                rets = [price_frame[t].iloc[j + 1] / price_frame[t].iloc[j] - 1
                        for t in held if price_frame[t].iloc[j] > 0]
                day = float(np.nanmean(rets)) if rets else 0.0
            else:
                day = 0.0
            if j == i:
                day -= rt          # round-trip cost at each rebalance
            port_daily.append(day)
            dates.append(cal[j + 1])

    port = pd.Series(port_daily, index=dates)
    bench = price_frame[benchmark].pct_change().reindex(port.index).fillna(0.0)
    return {"port_ret": port, "bench_ret": bench,
            "port_cum": (1 + port).cumprod(), "bench_cum": (1 + bench).cumprod(),
            "n_rebalances": len(reb), "hold_top": hold_top, "cost_bps": cost_bps}


def _stats(ret: pd.Series) -> dict:
    n = len(ret)
    if n < 5:
        return {}
    cum = (1 + ret).prod()
    yrs = n / TRADING_DAYS
    cagr = cum ** (1 / yrs) - 1 if yrs > 0 else np.nan
    vol = float(ret.std(ddof=1) * np.sqrt(TRADING_DAYS))
    sharpe = float(cagr / vol) if vol > 0 else None
    curve = (1 + ret).cumprod()
    mdd = float((curve / curve.cummax() - 1).min())
    return {"total_return": float(cum - 1), "cagr": float(cagr), "volatility": vol,
            "sharpe": sharpe, "max_drawdown": mdd}


def horizon_stats(sim: dict, years=(1, 5, 10)) -> dict:
    if "error" in sim:
        return sim
    port, bench = sim["port_ret"], sim["bench_ret"]
    out = {}
    for y in years:
        w = int(y * TRADING_DAYS)
        if len(port) < w:
            out[f"{y}y"] = {"available": False}
            continue
        p, b = _stats(port.iloc[-w:]), _stats(bench.iloc[-w:])
        out[f"{y}y"] = {"available": True, "portfolio": p, "benchmark": b,
                        "alpha_cagr": (p.get("cagr", 0) - b.get("cagr", 0))}
    # full-sample too
    out["full"] = {"available": True, "portfolio": _stats(port), "benchmark": _stats(bench),
                   "alpha_cagr": _stats(port).get("cagr", 0) - _stats(bench).get("cagr", 0),
                   "years": round(len(port) / TRADING_DAYS, 1)}
    return out


def run(tickers: list, benchmark="SPY", price_fn=None, score_fn=momentum_score,
        hold_top=10, rebalance_days=21, cost_bps=10.0, years=(1, 5, 10)) -> dict:
    """Load prices for tickers+benchmark, simulate, return horizon stats + curves."""
    if price_fn is None:
        from ..screener.prices import close_series
        price_fn = lambda t: close_series(t, days=2700)
    series = {}
    for t in [benchmark] + list(tickers):
        dts, cl = price_fn(t)
        if dts and cl and len(cl) > 260:
            series[t] = pd.Series(cl, index=pd.to_datetime(dts))
    if benchmark not in series:
        return {"error": f"could not load benchmark {benchmark}"}
    frame = pd.DataFrame(series).sort_index().ffill().dropna(how="all")
    frame = frame.dropna(axis=1, thresh=int(len(frame) * 0.6))
    sim = simulate(frame, score_fn=score_fn, benchmark=benchmark,
                   hold_top=hold_top, rebalance_days=rebalance_days, cost_bps=cost_bps)
    stats = horizon_stats(sim, years=years)
    if "error" not in sim:
        stats["_curve"] = {"dates": [str(d.date()) for d in sim["port_cum"].index[::5]],
                           "port": [float(x) for x in sim["port_cum"].values[::5]],
                           "bench": [float(x) for x in sim["bench_cum"].values[::5]]}
        stats["survivorship_caveat"] = ("Free price history only includes still-listed names, so "
                                        "this overstates edge. Confirm on survivorship-free data.")
    return stats
