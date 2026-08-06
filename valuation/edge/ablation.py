"""ablation.py — does the seven-theme composite earn its complexity?  [AUDIT X3, re-run]

X3 was run once before, on 2026-08-03 (`scripts/ablation.py`,
`data/free_analysis/ABLATION_RESULTS.json`), and the ledger records it DONE with the verdict
"EARNS ITS COMPLEXITY". **That run is void, for two independent reasons, and this module is the
re-run.**

  1. **It used the pre-B6 panel** — 110 dates, 136,478 rows, full-composite alpha +11.88%.
     B6 (the `.tail(4659)` per-ticker truncation, fixed 2026-08-04) meant the first 41 of those
     dates carried an INVERTED universe in which every name present was one that had already
     stopped trading. The corrected panel is 69 dates and the same alpha is +7.17%. Every gain
     the old verdict rested on was measured across that boundary.
  2. **It scored against the retired conventions** — a 2.0pp bar against the best single signal
     and a 1.0pp bar against the best three-theme prefix, both pre-registered in
     `PREREG_free_analysis.md` on 2026-08-03. X7 (2026-08-05) then measured what pure noise
     produces on this pipeline and put the top-decile alpha margin at **1.95pp**. A 1.0pp bar
     is BELOW the noise floor; a three-theme prefix could clear it on a shuffled signal.

The old run is also absent from `RESEARCH_LOG.md`, so roughly a dozen ablation arms were never
charged to the trial count. This re-run logs itself.

Everything here is scored against X7's calibrated bars and against a paired nested difference
that this module computes itself, because X7 calibrates no bar for a nested-model comparison and
inventing one would be the same error the old run made in the other direction.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

# ---- X7's calibrated floors (placebo percentiles over 100 draws, full pipeline, N = 84).
# These are floors for THIS panel and universe, not universal constants. Quoted here so a
# reader of a result never has to go looking for which bar it was scored against.
X7_ALPHA_MARGIN = 0.0195        # top-decile alpha: placebo p95
X7_LS_T_NAIVE = 2.14            # long-short t: placebo p95, measured on the NAIVE statistic
X7_THEME_IC_T = 2.71            # per-theme IC t: placebo p95 across 8 themes
X7_PBO_MAX = 0.197              # PBO: placebo p5. Note PBO's placebo MEDIAN is 46.7%
X7_DEFLATED_SHARPE = 0.7216     # placebo p95 at N = 84
X7_SOURCE = "HANDOFF_edge_audit.md Part 4 (X7 placebo, 100 draws, full pipeline)"


def alpha_series(panel, cols, weights, n_q: int = 10):
    """Per-period (top decile − equal-weight universe) forward return, and the long-short series.

    This repeats `quantile_backtest`'s inner loop rather than calling it, because the series
    themselves are needed for the paired nested comparison and `quantile_backtest` returns only
    their summary. It is pinned by `test_x3_alpha_series_reproduces_quantile_backtest`, which
    asserts `ppy * mean(series)` equals the shipped `top_decile_alpha` to floating point — if
    the two ever drift apart the test fails rather than the ablation quietly measuring a
    different object from the headline.
    """
    from ..screener.cross_sectional import zscore
    from .fundamental_panel import composite_from_frame

    a, ls, dates_used = [], [], []
    for d in sorted(panel["date"].unique()):
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)
        fwd = sub["fwd_ret"].values
        ok = np.isfinite(comp) & np.isfinite(fwd)
        c_, f_ = comp[ok], fwd[ok]
        if len(f_) < n_q * 3:
            continue
        buckets = np.array_split(np.argsort(-c_), n_q)
        a.append(float(np.mean(f_[buckets[0]]) - np.mean(f_)))
        ls.append(float(np.mean(f_[buckets[0]]) - np.mean(f_[buckets[-1]])))
        dates_used.append(str(d)[:10])
    return {"alpha": a, "long_short": ls, "dates": dates_used}


def paired_diff(a, b, draws: int = 4000, seed: int = 0) -> dict:
    """CI on mean(a) − mean(b) where a and b are the SAME periods of two nested models.

    Periods are resampled with replacement and both series are indexed by the SAME draw, which
    is what makes it paired: a quarter that was good for the market is good for both arms and
    cancels out of the difference. Resampling them independently would put the market's variance
    back into a comparison it has no business being in, and would make every arm look
    indistinguishable from every other.

    **No calibrated floor exists for this quantity.** X7 calibrated the top-decile alpha margin,
    the long-short t and the theme IC t; it did not calibrate a paired nested difference, and
    none is invented here. The pre-registered rule is simply that the CI95 must exclude zero for
    the longer model to be said to beat the shorter one.
    """
    import random
    n = min(len(a), len(b))
    if n < 8:
        return {"ok": False, "reason": f"{n} paired periods"}
    a, b = np.asarray(a[:n], dtype=float), np.asarray(b[:n], dtype=float)
    d = a - b
    rnd = random.Random(seed)
    vals = []
    for _ in range(draws):
        idx = [rnd.randrange(n) for _ in range(n)]
        vals.append(float(np.mean(d[idx])))
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[min(len(vals) - 1, int(0.975 * len(vals)))]
    ppy = 4.0                                    # 63-trading-day periods
    from .fundamental_panel import _nw_tstat, _tstat
    return {"ok": True, "n_periods": n,
            "mean_diff_ann": float(np.mean(d) * ppy),
            "ci95_ann": [lo * ppy, hi * ppy],
            "excludes_zero": bool(lo > 0 or hi < 0),
            "positive_at_significance": bool(lo > 0),
            "tstat": _tstat(list(d)), "tstat_nw": _nw_tstat(list(d), lag=1),
            "note": "paired period bootstrap; no X7-calibrated floor exists for this quantity."}


def deflated_sharpe_at(detail: dict, n_trials: int) -> Optional[dict]:
    """Recompute a recorded Deflated Sharpe at a different trial count, exactly.

    Bailey-Lopez de Prado's `sr0` is the only term N enters, so a recorded run's statistic can be
    moved to a new N without re-running the backtest: back the skew/kurtosis denominator out of
    the recorded probability, then re-evaluate with the new `sr0`. Used to report what X3's own
    eight arms cost the shipped headline — which is the entire point of M1 and would otherwise
    be a claim rather than a number.
    """
    from .fundamental_panel import _ncdf, _nppf
    sr = detail.get("sharpe_per_period")
    var_sr = detail.get("var_sr_across_trials")
    n = detail.get("n_periods")
    p_old = detail.get("probability")
    n_old = detail.get("n_trials")
    if None in (sr, var_sr, n, p_old, n_old) or n < 2:
        return None
    emc = 0.5772156649015329

    def _sr0(N):
        return float((var_sr ** 0.5)
                     * ((1 - emc) * _nppf(1 - 1.0 / N) + emc * _nppf(1 - 1.0 / (N * np.e))))

    z_old = float(_nppf(min(max(p_old, 1e-12), 1 - 1e-12)))
    sr0_old = _sr0(n_old)
    if z_old == 0:
        return None
    root_denom = (sr - sr0_old) * ((n - 1) ** 0.5) / z_old      # sqrt(1 - skew*sr + ...)
    sr0_new = _sr0(n_trials)
    z_new = (sr - sr0_new) * ((n - 1) ** 0.5) / root_denom
    return {"n_trials": int(n_trials), "sr0_benchmark": sr0_new,
            "probability": float(_ncdf(z_new)),
            "was": {"n_trials": int(n_old), "sr0_benchmark": sr0_old,
                    "probability": float(p_old)},
            "trials_haircut": float(np.sqrt(2.0 * np.log(max(2, n_trials))))}


def arm_result(panel, label, cols, weights, n_q: int = 10, horizon: int = 63) -> dict:
    """One ablation arm, scored against the calibrated bars and nothing else."""
    from .fundamental_panel import quantile_backtest
    r = quantile_backtest(panel, cols, weights, n_q=n_q, horizon=horizon)
    s = alpha_series(panel, cols, weights, n_q=n_q)
    a = r.get("top_decile_alpha")
    t = r.get("long_short_tstat")
    return {"label": label, "cols": list(cols), "weights": weights,
            "top_decile_alpha": a, "top_decile_alpha_tstat_nw": r.get("top_decile_alpha_tstat_nw"),
            "long_short_ann": r.get("long_short_ann"),
            "long_short_tstat": t, "long_short_tstat_nw": r.get("long_short_tstat_nw"),
            "monotonicity": r.get("monotonicity"), "n_periods": r.get("n_periods"),
            "equal_weight_ann": r.get("equal_weight_ann"),
            "decile_ann_return": r.get("decile_ann_return"),
            # X7, not the retired conventions. Both flags are about THIS arm on its own, not
            # about whether it beats another arm — that is `paired_diff`'s job.
            "clears_x7_alpha_margin": (None if a is None else bool(a > X7_ALPHA_MARGIN)),
            "clears_x7_ls_t": (None if t is None else bool(t > X7_LS_T_NAIVE)),
            "_series": s}
