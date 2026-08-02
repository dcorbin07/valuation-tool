"""
cross_sectional.py — self-calibrating factor scoring.

Replaces the old absolute-threshold anchors (+50% DCF -> 100, etc.). Each factor
is standardized ACROSS the universe within a single cross-section (one date) via a
winsorized z-score, then combined by weight. "Good" value/quality/momentum is thus
defined relative to the peer set on that day, not a hard-coded number that may be
miscalibrated for small-caps.

Factor columns must be oriented higher = better before being passed in (the panel
layer orients raw metrics, e.g. cheaper -> higher value). Missing factor values are
neutralized for that name and the remaining weights renormalized, so a name isn't
punished for one missing input.
"""
import numpy as np
import pandas as pd


def winsorize(s, p=0.02):
    s = s.astype(float)
    if s.notna().sum() == 0:
        return s
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def zscore(s, p=0.02):
    s = winsorize(s, p)
    mu, sd = s.mean(), s.std(ddof=0)
    if not sd or np.isnan(sd) or sd == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - mu) / sd


def standardize_factors(df, factor_cols, method="zscore"):
    """Return a frame of standardized factor columns (NaN preserved where input is NaN)."""
    out = pd.DataFrame(index=df.index)
    for c in factor_cols:
        if c not in df:
            out[c] = np.nan
            continue
        col = df[c].astype(float)
        if method == "rank":
            out[c] = (col.rank(pct=True) - 0.5) * 2.0     # [-1, 1], NaN where col NaN
        else:
            out[c] = zscore(col)
    return out


def composite_score(df, weights, method="zscore"):
    """
    df: one cross-section (rows = names on a date) with the oriented factor columns
        named in `weights`. weights: {factor: weight}.
    Returns a Series: the weighted average of present standardized factors (z-score
    units), with per-name renormalization over whichever factors are available.
    """
    factor_cols = list(weights.keys())
    z = standardize_factors(df, factor_cols, method)
    w = pd.Series(weights, dtype=float)
    present = z.notna().astype(float)
    denom = (present * w).sum(axis=1).replace(0, np.nan)      # available weight per name
    contrib = (z.fillna(0.0) * w).sum(axis=1)
    return contrib / denom                                    # weighted mean of present z-scores


def score_cross_section(df, weights, method="zscore"):
    """Convenience: attach standardized factors + composite to a cross-section copy."""
    out = df.copy()
    z = standardize_factors(df, list(weights.keys()), method)
    for c in z.columns:
        out[f"z_{c}"] = z[c]
    out["composite"] = composite_score(df, weights, method)
    return out
