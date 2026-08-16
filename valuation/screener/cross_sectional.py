"""
Self-calibrating factor scoring — ported from the screener project.

Each factor is standardized ACROSS the universe within a single cross-section
(one scan date) via a winsorized z-score, then combined by weight. "Good"
value/quality/momentum is thus defined relative to the peer set that day, not a
hard-coded threshold that may be miscalibrated. Factor columns must be oriented
higher = better. Missing values are neutralized per name and the remaining
weights renormalized, so a name isn't punished for one missing input.
"""
import os

import numpy as np
import pandas as pd

# Robust (median / MAD) standardization instead of mean / standard deviation.
#
# Winsorization at 2% already caps the tails, but the LOCATION and SCALE are still a mean and
# a standard deviation, both of which the surviving 2% tails still drag around — and factor
# inputs here are heavily skewed (fcf_yield, interest_cov, gp_on_capital all have long right
# tails even after clipping). Median/MAD estimates both from the middle of the distribution.
#
# TESTED AND REJECTED (P6.3, full 2,710-name universe). Robust standardization made the
# COMPOSITE substantially worse, while barely touching any individual signal:
#
#                        classic    robust
#     long-short t         3.485     1.721
#     long-short ann     +17.58%    +8.42%
#     top-decile alpha   +11.77%    +8.99%
#     monotonicity        -0.939    -0.624
#     theme IC t-stats   essentially unchanged (quality +3.39 -> +3.35, value +1.34 -> +1.68)
#
# The reason is worth remembering: rank-IC is INVARIANT to a monotone rescaling, so per-signal
# ICs cannot see this change at all — but the composite is a weighted SUM of z-scores and is
# very much scale-sensitive. MAD < SD for fat-tailed data, so dividing by the smaller scale
# INFLATES the tails, and the top decile then gets picked by whoever has one extreme factor
# reading rather than broad strength across themes. Making the scale estimate robust made the
# SELECTION less robust.
#
# Kept off by default and switchable via VALQUO_ROBUST_Z so the negative result is documented
# and re-testable. Judging a standardization change by per-signal IC would have called this
# harmless — it costs half the long-short t.
USE_ROBUST_Z = os.getenv("VALQUO_ROBUST_Z", "").strip().lower() in ("1", "true", "yes", "on")

# MA59: the third one-env-var path back to a rejected intervention (the other
# two are in config.py, which warns the same way). Silent when unset, which is
# every ordinary run; loud only for the person who opted in, because a run
# scoring the rejected arm still prints its results under the ordinary
# headline and nothing else anywhere would say so.
if USE_ROBUST_Z:      # pragma: no cover - opt-in path
    import warnings
    warnings.warn(
        "REJECTED INTERVENTION ENABLED — VALQUO_ROBUST_Z: median/MAD robust "
        "z-scores HALVED the long-short t (3.485 -> 1.721, P6). Per-signal ICs "
        "cannot see this change, so nothing else will flag it.",
        RuntimeWarning, stacklevel=2)

# Scales the MAD so it estimates the same quantity as the standard deviation for normally
# distributed data (1 / Phi^-1(0.75)), keeping robust and classic z-scores on one scale —
# which matters because themes average z-scores across inputs that may use either.
MAD_TO_SIGMA = 1.4826


def winsorize(s, p=0.02):
    s = s.astype(float)
    if s.notna().sum() == 0:
        return s
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def robust_zscore(s, p=0.02):
    """(x - median) / (1.4826 * MAD), winsorized first.

    Falls back to the classic z-score when the MAD is zero — that happens when more than half
    the cross-section shares one value (a sparse or heavily-defaulted input), where MAD
    scaling would divide by zero and blank the whole column.
    """
    s = winsorize(s, p)
    med = s.median()
    mad = (s - med).abs().median()
    if not mad or np.isnan(mad) or mad == 0:
        sd = s.std(ddof=0)
        if not sd or np.isnan(sd) or sd == 0:
            return pd.Series(np.nan, index=s.index)
        return (s - s.mean()) / sd
    return (s - med) / (MAD_TO_SIGMA * mad)


def zscore(s, p=0.02, robust=None):
    """Standardize a cross-section, higher = better. `robust` defaults to USE_ROBUST_Z."""
    if robust is None:
        robust = USE_ROBUST_Z
    if robust:
        return robust_zscore(s, p)
    s = winsorize(s, p)
    mu, sd = s.mean(), s.std(ddof=0)
    if not sd or np.isnan(sd) or sd == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - mu) / sd


def rank_score(s):
    """Cross-sectional rank mapped to [-1, +1]. Higher = better, like every other scorer here.

    LEDGER S20 ("rank composite, not z-sum") — a RESEARCH ARM, not a default. Nothing in the
    shipped scoring path calls this; `standardize_factors(method="rank")` and the S20 study are
    the only callers, and they share this one definition deliberately: two rank implementations
    that drift apart is a defect class this project has already paid for four times.

    Two properties that matter for the study, both exact rather than approximate:

      * it is INVARIANT TO WINSORIZATION, and to any other monotone transform of its input, so
        the S20 arm subsumes the S21 one (pinned by a test);
      * Spearman IC is likewise invariant, so per-signal rank ICs CANNOT SEE this change at all
        while the composite - a weighted SUM, and scale-sensitive - may move a great deal. That
        is P6.3's lesson (`USE_ROBUST_Z` above) restated as an identity.

    NaN propagates: pandas `rank` leaves missing values missing, so a name short an input is
    renormalised away by the composite exactly as under `zscore`.
    """
    s = pd.to_numeric(s, errors="coerce")
    return (s.rank(pct=True) - 0.5) * 2.0


def zscore_nowinsor(s):
    """`zscore` with winsorization disabled — LEDGER S21's challenger arm. RESEARCH ARM.

    `winsorize(s, 0)` clips to [quantile(0), quantile(1)] = [min, max], which is an exact no-op,
    so this needs no change to `winsorize` itself.

    Note the direction, which is inverted relative to the ledger item's wording: `zscore` ALREADY
    winsorizes before standardizing (see below), so the informative arm is winsorization OFF, and
    an improvement here would mean REMOVING the shipped clipping. See PREREG_s20_s21_construction.md §2.
    """
    return zscore(s, p=0.0)


def standardize_factors(df, factor_cols, method="zscore"):
    out = pd.DataFrame(index=df.index)
    for c in factor_cols:
        if c not in df:
            out[c] = np.nan
            continue
        col = df[c].astype(float)
        if method == "rank":
            out[c] = rank_score(col)
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
