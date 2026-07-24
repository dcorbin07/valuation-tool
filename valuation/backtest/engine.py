"""
Backtest engine — does the hot-stocks score actually predict forward returns?

Ported and extended from the screener project. Consumes a point-in-time PANEL
(one row per name per rebalance date, with the composite score, the realized
forward return, and a benchmark forward return) and reports:

  * Information Coefficient (IC): per-date rank correlation of score vs forward
    return. Mean IC ≈ 0 = no edge; small positive mean IC with t > ~2 that holds
    out-of-sample = a real signal.
  * Per-factor IC: which factors carry signal vs. are dead weight.
  * Quantile spread after costs: do top-scored names beat bottom, monotonically?
  * Long-top vs benchmark + an equity curve (cumulative return, annualized return,
    volatility, Sharpe, max drawdown) — the "would this have made money" view.
  * Out-of-sample split: does the signal survive in the second half?

It will NOT invent edge. And a free panel of only currently-listed names carries
SURVIVORSHIP BIAS, so a positive result means "worth confirming on survivorship-
free data," not proof.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _spearman(a, b):
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 5 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return np.nan
    return d["a"].rank().corr(d["b"].rank())


def information_coefficient(panel, score_col="composite", ret_col="fwd_ret", date_col="date"):
    ics = [_spearman(g[score_col], g[ret_col]) for _, g in panel.groupby(date_col)]
    ics = pd.Series(ics, dtype=float).dropna()
    n = len(ics)
    mean = float(ics.mean()) if n else np.nan
    sd = float(ics.std(ddof=1)) if n > 1 else np.nan
    t = mean / (sd / np.sqrt(n)) if (sd and sd > 0) else np.nan
    return {"n_periods": n, "mean_ic": mean, "ic_std": sd,
            "ic_t": float(t) if t == t else np.nan,
            "hit_rate": float((ics > 0).mean()) if n else np.nan}


def factor_ic(panel, factor_cols, ret_col="fwd_ret", date_col="date"):
    return {c: information_coefficient(panel, c, ret_col, date_col)["mean_ic"]
            for c in factor_cols if c in panel}


def quantile_returns(panel, score_col="composite", ret_col="fwd_ret", date_col="date",
                     q=5, cost_bps=0.0):
    rt = 2 * cost_bps / 1e4
    per = []
    for _, g in panel.groupby(date_col):
        gg = g.dropna(subset=[score_col, ret_col]).copy()
        if len(gg) < q:
            continue
        gg["qb"] = pd.qcut(gg[score_col].rank(method="first"), q, labels=False)
        per.append(gg.groupby("qb")[ret_col].mean())
    if not per:
        return None
    qmean = pd.concat(per, axis=1).mean(axis=1)
    spread = float(qmean.iloc[-1] - qmean.iloc[0])
    mono = bool((qmean.diff().dropna() > 0).all())
    return {"quantile_mean": [float(x) for x in qmean.tolist()],
            "top_minus_bottom": spread, "top_minus_bottom_net": spread - 2 * rt,
            "monotonic_increasing": mono, "n_periods": len(per)}


def _period_returns(panel, score_col, ret_col, bench_col, date_col, q, cost_bps):
    rt = 2 * cost_bps / 1e4
    dates, port, bench = [], [], []
    for dt, g in panel.groupby(date_col):
        gg = g.dropna(subset=[score_col, ret_col]).copy()
        if len(gg) < q:
            continue
        gg["qb"] = pd.qcut(gg[score_col].rank(method="first"), q, labels=False)
        top = gg[gg["qb"] == q - 1]
        dates.append(dt)
        port.append(float(top[ret_col].mean()) - rt)
        bench.append(float(g[bench_col].dropna().mean()) if bench_col in g else np.nan)
    return dates, np.array(port), np.array(bench)


def long_top_vs_bench(panel, score_col="composite", ret_col="fwd_ret",
                      bench_col="bench_ret", date_col="date", q=5, cost_bps=0.0):
    dates, port, bench = _period_returns(panel, score_col, ret_col, bench_col, date_col, q, cost_bps)
    if len(port) == 0:
        return None
    active = port - bench
    n = len(active)
    mean = float(np.nanmean(active))
    sd = float(np.nanstd(active, ddof=1)) if n > 1 else np.nan
    t = mean / (sd / np.sqrt(n)) if (sd and sd > 0) else np.nan
    return {"n_periods": n, "mean_active": mean, "active_t": float(t) if t == t else np.nan,
            "port_mean": float(np.nanmean(port)), "bench_mean": float(np.nanmean(bench)),
            "cum_port": float(np.prod(1 + port) - 1),
            "cum_bench": float(np.prod(1 + bench[~np.isnan(bench)]) - 1)}


def equity_curve(panel, score_col="composite", ret_col="fwd_ret", bench_col="bench_ret",
                 date_col="date", q=5, cost_bps=5.0, horizon_days=21):
    """Top-quantile portfolio equity curve + risk stats vs benchmark."""
    dates, port, bench = _period_returns(panel, score_col, ret_col, bench_col, date_col, q, cost_bps)
    if len(port) == 0:
        return None
    cum_port = np.cumprod(1 + port)
    valid_b = np.where(np.isnan(bench), 0.0, bench)
    cum_bench = np.cumprod(1 + valid_b)
    ppy = 252.0 / max(1, horizon_days)      # rebalance periods per year

    def stats(rets, cum):
        n = len(rets)
        ann_ret = cum[-1] ** (ppy / n) - 1 if n else np.nan
        vol = float(np.std(rets, ddof=1)) * np.sqrt(ppy) if n > 1 else np.nan
        sharpe = (ann_ret / vol) if (vol and vol > 0) else np.nan
        peak = np.maximum.accumulate(cum)
        mdd = float(np.min(cum / peak - 1.0)) if n else np.nan
        return {"ann_return": float(ann_ret), "volatility": float(vol),
                "sharpe": float(sharpe) if sharpe == sharpe else None, "max_drawdown": mdd,
                "total_return": float(cum[-1] - 1)}

    return {"dates": [str(d) for d in dates],
            "cum_port": [float(x) for x in cum_port],
            "cum_bench": [float(x) for x in cum_bench],
            "port": stats(port, cum_port), "bench": stats(valid_b, cum_bench)}


def oos_split(panel, score_col="composite", ret_col="fwd_ret", date_col="date"):
    dates = sorted(panel[date_col].unique())
    if len(dates) < 4:
        return None
    mid = dates[len(dates) // 2]
    return {"in_sample": information_coefficient(panel[panel[date_col] < mid], score_col, ret_col, date_col),
            "out_sample": information_coefficient(panel[panel[date_col] >= mid], score_col, ret_col, date_col)}


def summarize(panel, score_col="composite", factor_cols=None, ret_col="fwd_ret",
              bench_col="bench_ret", date_col="date", q=5, cost_bps=5.0, horizon_days=21):
    ic = information_coefficient(panel, score_col, ret_col, date_col)
    quint = quantile_returns(panel, score_col, ret_col, date_col, q, cost_bps)
    lvb = long_top_vs_bench(panel, score_col, ret_col, bench_col, date_col, q, cost_bps)
    eq = equity_curve(panel, score_col, ret_col, bench_col, date_col, q, cost_bps, horizon_days)
    oos = oos_split(panel, score_col, ret_col, date_col)
    fic = factor_ic(panel, factor_cols or [], ret_col, date_col) if factor_cols else {}

    # Verdict: demand a significant, monotonic, cost-surviving, out-of-sample signal.
    reasons = []
    edge = True
    if not (ic["mean_ic"] == ic["mean_ic"] and ic["mean_ic"] > 0 and ic.get("ic_t", 0) and ic["ic_t"] > 2):
        edge = False; reasons.append(f"IC not significant (mean {ic['mean_ic']:.3f}, t {ic.get('ic_t', float('nan')):.2f}).")
    if quint and not quint["monotonic_increasing"]:
        edge = False; reasons.append("Quantile returns not monotonic.")
    if quint and quint["top_minus_bottom_net"] <= 0:
        edge = False; reasons.append("Top-minus-bottom spread does not survive costs.")
    if oos and not (oos["out_sample"]["mean_ic"] == oos["out_sample"]["mean_ic"]
                    and oos["out_sample"]["mean_ic"] > 0):
        edge = False; reasons.append("Signal does not hold out-of-sample.")
    if edge:
        verdict = ("Evidence of a real, cost-surviving, out-of-sample edge — "
                   "still confirm on survivorship-free data before trusting it.")
    else:
        verdict = "No reliable edge on this data: " + " ".join(reasons)

    return {"ic": ic, "factor_ic": fic, "quantiles": quint, "long_vs_bench": lvb,
            "equity": eq, "oos": oos, "has_edge": edge, "verdict": verdict,
            "cost_bps": cost_bps, "q": q, "horizon_days": horizon_days}
