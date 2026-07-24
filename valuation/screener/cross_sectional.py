"""
Self-calibrating factor scoring — ported from the screener project.

Each factor is standardized ACROSS the universe within a single cross-section
(one scan date) via a winsorized z-score, then combined by weight. "Good"
value/quality/momentum is thus defined relative to the peer set that day, not a
hard-coded threshold that may be miscalibrated. Factor columns must be oriented
higher = better. Missing values are neutralized per name and the remaining
weights renormalized, so a name isn't punished for one missing input.
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
    out = pd.DataFrame(index=df.index)
    for c in factor_cols:
        if c not in df:
            out[c] = np.nan
            continue
        col = df[c].astype(float)
        if method == "rank":
            out[c] = (col.rank(pct=True) - 0.5) * 2.0
        else:
            out[c] = zscore(col)
    return out


def composite_score(df, weights, method="zscore"):
    """Weighted average of present standardized factors, renormalized per name."""
    factor_cols = list(weights.keys())
    z = standardize_factors(df, factor_cols, method)
    w = pd.Series(weights, dtype=float)
    present = z.notna().astype(float)
    denom = (present * w).sum(axis=1).replace(0, np.nan)
    contrib = (z.fillna(0.0) * w).sum(axis=1)
    return contrib / denom
