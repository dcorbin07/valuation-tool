"""
Factor-weight optimizer — with hard anti-overfitting guards.

Given a panel that carries individual factor columns, it searches weight
combinations to maximize the Information Coefficient IN-SAMPLE (first half of the
history), then validates the winner OUT-OF-SAMPLE (second half). It only returns
tuned weights if the edge actually persists out-of-sample; otherwise it tells you
to keep the defaults. This is the whole point — an optimizer with no hold-out is
just a machine for fooling yourself.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .engine import information_coefficient
from ..screener.cross_sectional import zscore


def _standardize_per_date(panel, factor_cols, date_col="date"):
    out = panel.copy()
    for c in factor_cols:
        out["z_" + c] = out.groupby(date_col)[c].transform(lambda s: zscore(s))
    return out


def _composite_col(df, weights, factor_cols):
    zcols = ["z_" + c for c in factor_cols]
    Z = df[zcols].to_numpy(dtype=float)
    w = np.array([weights[c] for c in factor_cols], dtype=float)
    present = ~np.isnan(Z)
    denom = (present * w).sum(axis=1)
    denom[denom == 0] = np.nan
    contrib = np.nansum(np.where(present, Z, 0.0) * w, axis=1)
    return contrib / denom


def _weight_grid(factor_cols, step=0.25):
    vals = [round(i * step, 4) for i in range(int(round(1 / step)) + 1)]
    grid = []
    for combo in itertools.product(vals, repeat=len(factor_cols)):
        if abs(sum(combo) - 1.0) < 1e-9:
            grid.append(dict(zip(factor_cols, combo)))
    return grid


def _ic_for(df, weights, factor_cols, ret_col, date_col):
    d = df.copy()
    d["__c"] = _composite_col(d, weights, factor_cols)
    return information_coefficient(d, "__c", ret_col, date_col)["mean_ic"]


def optimize_weights(panel, factor_cols, ret_col="fwd_ret", date_col="date",
                     step=0.25, min_oos_fraction=0.5, default_weights=None) -> dict:
    """Search weights on the in-sample half, validate on the out-of-sample half."""
    std = _standardize_per_date(panel, factor_cols, date_col)
    dates = sorted(std[date_col].unique())
    if len(dates) < 6:
        return {"accepted": False, "reason": "Not enough rebalance dates to split in/out-of-sample.",
                "recommended_weights": default_weights}
    mid = dates[len(dates) // 2]
    is_p, oos_p = std[std[date_col] < mid], std[std[date_col] >= mid]

    grid = _weight_grid(factor_cols, step)
    scored = [(w, _ic_for(is_p, w, factor_cols, ret_col, date_col)) for w in grid]
    scored = [(w, ic) for w, ic in scored if ic == ic]      # drop NaN
    if not scored:
        return {"accepted": False, "reason": "Could not compute in-sample IC.",
                "recommended_weights": default_weights}
    scored.sort(key=lambda x: x[1], reverse=True)
    best_w, is_ic = scored[0]
    oos_ic = _ic_for(oos_p, best_w, factor_cols, ret_col, date_col)

    # Default (equal-weight) baseline for comparison.
    eq = {c: 1.0 / len(factor_cols) for c in factor_cols}
    eq_oos = _ic_for(oos_p, eq, factor_cols, ret_col, date_col)

    accepted = bool(is_ic > 0 and oos_ic == oos_ic and oos_ic > 0
                    and oos_ic >= min_oos_fraction * is_ic)
    if accepted:
        verdict = (f"Tuned weights hold out-of-sample (IS IC {is_ic:.3f} → OOS IC {oos_ic:.3f}). "
                   f"Recommended over equal-weight (OOS {eq_oos:.3f}).")
        rec = best_w
    else:
        why = ("OOS IC not positive" if not (oos_ic == oos_ic and oos_ic > 0)
               else f"OOS edge collapsed ({oos_ic:.3f} < {min_oos_fraction:.0%} of IS {is_ic:.3f})")
        verdict = (f"Rejected: {why}. Keep the default weights — the in-sample gain was overfit.")
        rec = default_weights

    return {"accepted": accepted, "recommended_weights": rec, "best_in_sample_weights": best_w,
            "in_sample_ic": float(is_ic), "out_sample_ic": float(oos_ic) if oos_ic == oos_ic else None,
            "equal_weight_oos_ic": float(eq_oos) if eq_oos == eq_oos else None,
            "n_periods": len(dates), "verdict": verdict}
