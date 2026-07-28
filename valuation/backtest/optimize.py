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


def _compositions(n, total):
    """Non-negative integer tuples of length n summing to total (weights that sum to 1
    in `step` units). Enumerates only valid combos — vastly fewer than the full product,
    which matters once there are many factors (5**9 ≈ 2M vs ~500)."""
    if n == 1:
        yield (total,)
        return
    for i in range(total + 1):
        for rest in _compositions(n - 1, total - i):
            yield (i,) + rest


def _weight_grid(factor_cols, step=0.25):
    units = int(round(1 / step))
    return [dict(zip(factor_cols, [round(u * step, 4) for u in combo]))
            for combo in _compositions(len(factor_cols), units)]


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

    # Significance floor (multiple-testing guard): the OOS IC wasn't used to pick the
    # weights, so under the null it's ~N(0, 1/sqrt((names-1)*oos_dates)). Requiring it to
    # clear ~1.64 sigma rejects noise regardless of how many grid points we searched —
    # which matters now that more factors mean a much bigger grid.
    _oos_dates = int(oos_p[date_col].nunique())
    _avg_names = float(oos_p.groupby(date_col).size().mean()) if _oos_dates else 0.0
    _std_null = (1.0 / ((max(1.0, _avg_names - 1.0) * max(1, _oos_dates)) ** 0.5)) if _oos_dates else 1.0
    _sig_floor = 1.64 * _std_null

    accepted = bool(is_ic > 0 and oos_ic == oos_ic and oos_ic > 0
                    and oos_ic >= min_oos_fraction * is_ic and oos_ic >= _sig_floor)
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
