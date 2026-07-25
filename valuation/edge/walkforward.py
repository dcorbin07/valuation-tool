"""
Walk-forward optimization — tune the ranking weights WITHOUT overfitting.

A single train/test split can still be gamed. Walk-forward is the honest test:
optimize the factor weights on everything up to a point, apply them to the *next*
unseen fold, roll forward, and stitch those out-of-sample results together. The
adaptive weights only "win" if their stitched out-of-sample performance beats a
static baseline (equal weight / current weights). If they don't, we keep the
baseline — the in-sample gain was overfit.

This is the mechanism behind "keep optimizing the edge without overfitting": run
it periodically as data accrues; adopt new weights only when they survive here.
"""
from __future__ import annotations

import numpy as np

from ..backtest.optimize import _weight_grid, _standardize_per_date, _ic_for


def walk_forward(panel, factor_cols, ret_col="fwd_ret", date_col="date",
                 n_folds=5, step_grid=0.25, default_weights=None) -> dict:
    std = _standardize_per_date(panel, factor_cols, date_col)
    dates = sorted(std[date_col].unique())
    if len(dates) < (n_folds + 1) * 2:
        return {"error": "Not enough rebalance dates for walk-forward.",
                "adopt": False, "final_weights": default_weights}

    folds = [list(a) for a in np.array_split(dates, n_folds + 1)]
    grid = _weight_grid(factor_cols, step_grid)
    eq = {c: 1.0 / len(factor_cols) for c in factor_cols}
    base = default_weights or eq

    oos_opt, oos_base = [], []
    for k in range(1, len(folds)):
        train_dates = set(d for f in folds[:k] for d in f)
        test_dates = set(folds[k])
        tr = std[std[date_col].isin(train_dates)]
        te = std[std[date_col].isin(test_dates)]
        best, best_ic = base, -9.0
        for w in grid:
            ic = _ic_for(tr, w, factor_cols, ret_col, date_col)
            if ic == ic and ic > best_ic:
                best, best_ic = w, ic
        oos_opt.append(_ic_for(te, best, factor_cols, ret_col, date_col))
        oos_base.append(_ic_for(te, base, factor_cols, ret_col, date_col))

    walk_opt = float(np.nanmean(oos_opt)) if oos_opt else float("nan")
    walk_base = float(np.nanmean(oos_base)) if oos_base else float("nan")

    # Final weights fit on ALL data (only used if walk-forward blessed the approach).
    final, final_ic = base, -9.0
    for w in grid:
        ic = _ic_for(std, w, factor_cols, ret_col, date_col)
        if ic == ic and ic > final_ic:
            final, final_ic = w, ic

    adopt = bool(walk_opt == walk_opt and walk_opt > 0 and walk_opt > walk_base)
    verdict = (f"Adopt: adaptive weights beat baseline out-of-sample "
               f"(walk-forward IC {walk_opt:.3f} > {walk_base:.3f})."
               if adopt else
               f"Keep baseline: optimization did not beat it out-of-sample "
               f"(walk-forward IC {walk_opt:.3f} vs {walk_base:.3f}) — the in-sample gain was overfit.")
    return {"adopt": adopt, "final_weights": final if adopt else base,
            "walk_oos_ic_optimized": walk_opt, "walk_oos_ic_baseline": walk_base,
            "n_folds": len(folds) - 1, "verdict": verdict}
