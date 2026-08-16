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


#  MA41 — THIS WAS THE ONLY SPLITTER IN THE TREE WITHOUT A PURGE/EMBARGO.
#
#  Measured before the fix: `grep -c embargo valuation/edge/walkforward.py` -> 0. Every sibling
#  splitter has one — `fundamental_panel._wf_folds(embargo=1)`, `_cpcv_paths`,
#  `loo_holdout.split`, `param_search.cpcv_index_paths`. This one trained on `folds[:k]` and
#  tested on `folds[k]` with ADJACENT dates, so the last training date's forward return window
#  overlaps the first test dates: the optimiser picks weights partly on the same realised
#  returns it is then scored against, and `walk_oos_ic_optimized` is inflated.
#
#  WHY IT MATTERS MORE HERE THAN IN A STUDY: this function feeds a LIVE "Adopt" verdict.
#  `lab.run_optimize` (`lab.py:88`) prints "Adopt: adaptive weights beat baseline out-of-sample"
#  and returns weights refit on ALL data, and `run_optimize` is reachable from the web app
#  (`valuation/web/app.py:1030`, `POST /api/edge/optimize`). An inflated out-of-sample IC on a
#  live weight-adoption surface is the same class as Pass A's MA1/MA3.
#
#  WHAT IS FIXED AND WHAT IS DELIBERATELY NOT. The lookahead is fixed: one fold-adjacent
#  rebalance date is dropped from the END of every training set, which is the unit the sibling
#  splitters use and the right one here (the panel's horizon and its rebalance period are both
#  63 days, so the overlap is exactly one period).
#
#  The ADOPT BOOLEAN IS NOT CHANGED, and that is a decision rather than an oversight. The gate
#  is `walk_opt > 0 and walk_opt > base` — a bare comparison of two means with no standard
#  error, which the audit rightly calls mis-specified. But putting a threshold on it means
#  choosing one, and this project has no calibrated floor for a walk-forward IC difference;
#  inventing a bar here is the exact error the record warns about most often (X3, session 10).
#  So the SE and the margin ship as REPORTED fields, the verdict string carries them, and
#  changing what adopts is left to an item that can register a bar first.

def walk_forward(panel, factor_cols, ret_col="fwd_ret", date_col="date",
                 n_folds=5, step_grid=0.25, default_weights=None, embargo=1) -> dict:
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
    embargoed = 0
    skipped = 0
    for k in range(1, len(folds)):
        train_sorted = sorted(d for f in folds[:k] for d in f)
        # THE EMBARGO. Drop the last `embargo` training dates, whose forward-return windows
        # reach into the test fold. Dropping from the END is what makes it a purge rather than
        # a resample: the discarded dates are exactly the contaminated ones.
        if embargo and len(train_sorted) > embargo:
            train_sorted = train_sorted[:-embargo]
            embargoed += embargo
        elif embargo:
            # Not enough training dates to embargo and still train. Skipping is the honest
            # action: scoring this fold would report a contaminated IC as an out-of-sample one.
            skipped += 1
            continue
        train_dates = set(train_sorted)
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

    # The margin and its dispersion, REPORTED not gated (see the block comment above). The
    # per-fold differences are paired by construction — the same test fold scores both arms —
    # so their SE is the right one for the margin, and `margin_t` is a DIAGNOSTIC with NO
    # calibrated floor. Nobody may compare it to 2.0, or to X7's bars, which were calibrated on
    # a different statistic on a different object.
    diffs = [o - b for o, b in zip(oos_opt, oos_base) if o == o and b == b]
    margin = float(np.mean(diffs)) if diffs else float("nan")
    if len(diffs) > 1:
        se = float(np.std(diffs, ddof=1) / np.sqrt(len(diffs)))
        margin_t = margin / se if se > 0 else float("nan")
    else:
        se, margin_t = float("nan"), float("nan")

    adopt = bool(walk_opt == walk_opt and walk_opt > 0 and walk_opt > walk_base)
    caveat = (f" Margin {margin:+.4f} over {len(diffs)} folds, SE {se:.4f}, t {margin_t:.2f} — "
              f"REPORTED ONLY: this gate compares two means with no threshold, and no "
              f"calibrated floor exists for a walk-forward IC difference.")
    verdict = (f"Adopt: adaptive weights beat baseline out-of-sample "
               f"(walk-forward IC {walk_opt:.3f} > {walk_base:.3f})."
               if adopt else
               f"Keep baseline: optimization did not beat it out-of-sample "
               f"(walk-forward IC {walk_opt:.3f} vs {walk_base:.3f}) — the in-sample gain was overfit.")
    return {"adopt": adopt, "final_weights": final if adopt else base,
            "walk_oos_ic_optimized": walk_opt, "walk_oos_ic_baseline": walk_base,
            "n_folds": len(folds) - 1, "verdict": verdict + caveat,
            "embargo": int(embargo), "embargoed_train_dates": int(embargoed),
            "folds_skipped_for_embargo": int(skipped), "n_folds_scored": len(oos_opt),
            "margin": margin, "margin_se": se, "margin_t": margin_t,
            "margin_note": "diagnostic only; no calibrated floor exists for this quantity"}
