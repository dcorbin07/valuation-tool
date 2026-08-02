"""
backtest_engine.py — does the composite score predict forward returns?

Consumes a point-in-time PANEL: one row per name per rebalance date, with the
composite score and the realized FORWARD return over the holding horizon, plus a
benchmark forward return. Agnostic to how the panel was built (see the data layer).
It will NOT invent edge.

  - Information Coefficient (IC): per-date rank correlation between score and forward
    return. The cleanest "does it rank-predict returns" measure. Mean IC ~0 = no edge;
    a small positive mean IC with a t-stat >~2 that holds out-of-sample = a real signal.
  - Per-factor IC: which individual factors carry signal vs. are dead weight.
  - Quantile spread: do top-scored names beat bottom-scored, monotonically, after costs?
  - Long-top vs benchmark: realistic for a long-only small-cap trader.
  - Out-of-sample split: does the signal survive in the second half?

HONESTY CAVEAT: a free first-pass panel built only from currently-listed names carries
SURVIVORSHIP BIAS — delisted losers are missing, inflating any apparent edge. Treat a
positive free-data result as "worth paying for survivorship-free data to confirm," not proof.
"""
import numpy as np
import pandas as pd


def _spearman(a, b):
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 5 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return np.nan   # not enough variation to define a rank correlation
    # Spearman = Pearson correlation of the ranks. Done directly so we don't need scipy
    # (pandas' method="spearman" imports scipy under the hood).
    return d["a"].rank().corr(d["b"].rank())


def information_coefficient(panel, score_col="composite", ret_col="fwd_ret", date_col="date"):
    ics = []
    for _, g in panel.groupby(date_col):
        ics.append(_spearman(g[score_col], g[ret_col]))
    ics = pd.Series(ics, dtype=float).dropna()
    n = len(ics)
    mean = float(ics.mean()) if n else np.nan
    sd = float(ics.std(ddof=1)) if n > 1 else np.nan
    t = mean / (sd / np.sqrt(n)) if (sd and sd > 0) else np.nan
    return {"n_periods": n, "mean_ic": mean, "ic_std": sd,
            "ic_t": float(t) if t == t else np.nan,
            "hit_rate": float((ics > 0).mean()) if n else np.nan, "ic_series": ics}


def factor_ic(panel, factor_cols, ret_col="fwd_ret", date_col="date"):
    return {c: information_coefficient(panel, c, ret_col, date_col)["mean_ic"]
            for c in factor_cols if c in panel}


def quantile_returns(panel, score_col="composite", ret_col="fwd_ret", date_col="date",
                     q=5, cost_bps=0.0):
    rt = 2 * cost_bps / 1e4   # round-trip cost, full-turnover assumption
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
    return {"quantile_mean": qmean, "quantile_mean_net": qmean - rt,
            "top_minus_bottom": spread,
            "top_minus_bottom_net": spread - 2 * rt,   # both legs turn over
            "monotonic_increasing": mono, "n_periods": len(per)}


def long_top_vs_bench(panel, score_col="composite", ret_col="fwd_ret",
                      bench_col="bench_ret", date_col="date", q=5, cost_bps=0.0):
    rt = 2 * cost_bps / 1e4
    port, bench = [], []
    for _, g in panel.groupby(date_col):
        gg = g.dropna(subset=[score_col, ret_col]).copy()
        if len(gg) < q:
            continue
        gg["qb"] = pd.qcut(gg[score_col].rank(method="first"), q, labels=False)
        top = gg[gg["qb"] == q - 1]
        port.append(float(top[ret_col].mean()) - rt)
        bench.append(float(g[bench_col].dropna().mean()) if bench_col in g else np.nan)
    if not port:
        return None
    port, bench = np.array(port), np.array(bench)
    active = port - bench
    n = len(active); mean = float(np.nanmean(active))
    sd = float(np.nanstd(active, ddof=1)) if n > 1 else np.nan
    t = mean / (sd / np.sqrt(n)) if (sd and sd > 0) else np.nan
    return {"n_periods": n, "mean_active": mean, "active_t": float(t) if t == t else np.nan,
            "port_mean": float(port.mean()), "bench_mean": float(np.nanmean(bench)),
            "cum_port": float(np.prod(1 + port) - 1),
            "cum_bench": float(np.prod(1 + bench[~np.isnan(bench)]) - 1)}


def oos_split(panel, score_col="composite", ret_col="fwd_ret", date_col="date"):
    dates = sorted(panel[date_col].unique())
    if len(dates) < 4:
        return None
    mid = dates[len(dates) // 2]
    return {"in_sample": information_coefficient(panel[panel[date_col] < mid], score_col, ret_col, date_col),
            "out_sample": information_coefficient(panel[panel[date_col] >= mid], score_col, ret_col, date_col)}


def summarize(panel, score_col="composite", factor_cols=None, ret_col="fwd_ret",
              bench_col="bench_ret", date_col="date", q=5, cost_bps=5.0):
    """Run everything and return a results dict + a plain-English verdict."""
    ic = information_coefficient(panel, score_col, ret_col, date_col)
    qr = quantile_returns(panel, score_col, ret_col, date_col, q, cost_bps)
    lt = long_top_vs_bench(panel, score_col, ret_col, bench_col, date_col, q, cost_bps)
    oos = oos_split(panel, score_col, ret_col, date_col)
    fic = factor_ic(panel, factor_cols, ret_col, date_col) if factor_cols else {}

    # verdict heuristic — deliberately demanding
    holds_oos = bool(oos and oos["in_sample"]["mean_ic"] is not None
                     and oos["out_sample"]["mean_ic"] is not None
                     and oos["in_sample"]["mean_ic"] > 0 and oos["out_sample"]["mean_ic"] > 0)
    significant = bool(ic["ic_t"] == ic["ic_t"] and abs(ic["ic_t"]) >= 2.0 and ic["mean_ic"] > 0)
    spread_pos = bool(qr and qr["top_minus_bottom_net"] > 0)
    edge = significant and holds_oos and spread_pos
    verdict = ("EDGE worth pursuing (confirm on survivorship-free data)" if edge
               else "NO reliable edge after costs — do not deploy on this basis")
    return {"ic": ic, "quantiles": qr, "long_top_vs_bench": lt, "oos": oos,
            "factor_ic": fic, "edge": edge, "verdict": verdict}


def print_report(res):
    ic = res["ic"]; qr = res["quantiles"]; lt = res["long_top_vs_bench"]; oos = res["oos"]
    print(f"Information Coefficient: mean={ic['mean_ic']:.4f}  t={ic['ic_t']:.2f}  "
          f"hit_rate={ic['hit_rate']*100:.0f}%  over {ic['n_periods']} periods")
    if res["factor_ic"]:
        print("Per-factor mean IC: " + ", ".join(f"{k}={v:+.3f}" for k, v in res["factor_ic"].items()))
    if qr:
        qs = "  ".join(f"Q{i+1}={v*100:+.2f}%" for i, v in enumerate(qr["quantile_mean"]))
        print(f"Quantile mean fwd return: {qs}")
        print(f"Top-minus-bottom (net of costs): {qr['top_minus_bottom_net']*100:+.2f}%  "
              f"monotonic={qr['monotonic_increasing']}")
    if lt:
        print(f"Long-top vs benchmark: active={lt['mean_active']*100:+.3f}%/period  "
              f"t={lt['active_t']:.2f}  cum_port={lt['cum_port']*100:+.1f}%  cum_bench={lt['cum_bench']*100:+.1f}%")
    if oos:
        print(f"Out-of-sample IC: in={oos['in_sample']['mean_ic']:.4f}  out={oos['out_sample']['mean_ic']:.4f}")
    print(f"VERDICT: {res['verdict']}")
