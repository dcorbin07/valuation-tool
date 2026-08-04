"""
Why a name scores what it does — an EXACT decomposition of the composite.

The hot score is a percentile rank of a composite, and the composite is a weighted average
of standardized themes. This splits that average back into per-theme CONTRIBUTIONS that sum
to the composite, so "why is this name here" is answered by arithmetic instead of by a
hand-written rationale that can drift away from the maths.

WHY THE DECOMPOSITION LIVES HERE AND NOT IN THE READ PATH. Two pieces of the score do not
survive into the saved snapshot:

  * `value` is scored on two different input sets — earnings-based yields for profitable
    names, sales multiples for loss-makers — and soft bucketing BLENDS both branches by how
    established a name looks. The snapshot stores one blended `value` column, which cannot be
    split back into the two branches it came from.
  * weights can change between the scan and the read: `_effective_weights` picks up whatever
    the self-learning loop has adopted, so re-deriving an attribution later would explain the
    score with weights the scan never used.

So the decomposition is computed at SCAN TIME, from the same frame the ranking was built on,
and stored on the row. `composite_score` is not called twice: `decompose()` is the single
implementation and the composite is the row-sum of its own contributions, so the explanation
cannot disagree with the number it explains.

Units: contributions are in composite units (cross-sectional standard deviations of the
theme, times its renormalized weight). They are NOT percentage points of the 1-100 score —
that score is a percentile RANK of the composite, which is a monotone but non-linear map.
Anything rendering these has to say so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .cross_sectional import standardize_factors


def p_established(df: pd.DataFrame) -> pd.Series:
    """Smooth probability a name is 'established' (profitable), from operating margin:
    0% -> 0.5, +5% -> 0.73, -5% -> 0.27. Falls back to the hard bucket if margin is missing."""
    om = pd.to_numeric(df.get("op_margin"), errors="coerce")
    # Clip the exponent before exp(). A name with a huge negative operating margin (early-stage
    # biotech, a shell with token revenue) sends this to exp(1e4) and numpy warns about
    # overflow on every scan. The saturated answer is already correct - 0 or 1 - so this only
    # silences a spurious RuntimeWarning, it does not change any score.
    p = 1.0 / (1.0 + np.exp(np.clip(-(om / 0.05), -700.0, 700.0)))
    hard = (df["bucket"] == "established").astype(float)
    return p.fillna(hard)


def _branch(d: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Per-theme contributions for one weight set: z * w / (weight present on this name).

    Row-sum equals `composite_score(d, weights)` by construction — same standardization, same
    renormalization, just not summed yet. A name missing a theme contributes 0 for it and has
    that weight redistributed across the rest (the `denom`), which is what makes a partially
    covered name comparable to a fully covered one.
    """
    cols = list(weights.keys())
    z = standardize_factors(d, cols)
    w = pd.Series(weights, dtype=float)
    present = z.notna().astype(float)
    denom = (present * w).sum(axis=1).replace(0, np.nan)
    # NaN denom (no theme scored this name at all) makes the whole row NaN rather than a
    # zero that would read as "scored, and neutral".
    return z.fillna(0.0).mul(w, axis=1).div(denom, axis=0)


def decompose(df: pd.DataFrame, est_w: dict, spec_w: dict, soft: bool = True):
    """(composite, contributions) — contributions sum EXACTLY to the composite.

    Mirrors `screen._composites`, which now delegates here so the two can never diverge.
    """
    cols = sorted(set(est_w) | set(spec_w))

    if soft and "value_est" in df.columns and "value_spec" in df.columns:
        # Soft bucketing: a borderline name (tiny profit/loss) shouldn't be scored 100% by
        # one rulebook. Score it under BOTH and blend by how established it looks, so the
        # cutoff is a gradient, not a cliff.
        d = df.copy()
        d["value"] = df["value_est"]
        c_est = _branch(d, est_w)
        d["value"] = df["value_spec"]
        c_spec = _branch(d, spec_w)
        ok = c_est.notna().any(axis=1) & c_spec.notna().any(axis=1)
        p = p_established(df)
        contrib = (c_est.reindex(columns=cols).fillna(0.0).mul(p, axis=0)
                   + c_spec.reindex(columns=cols).fillna(0.0).mul(1.0 - p, axis=0))
        contrib = contrib.where(ok, np.nan)
    else:
        # Hard split (used when soft bucketing is off).
        contrib = pd.DataFrame(np.nan, index=df.index, columns=cols)
        for bucket, w in [("established", est_w), ("speculative", spec_w)]:
            sub = df[df["bucket"] == bucket]
            if sub.empty:
                continue
            # Under ~5 names a within-bucket z-score is meaningless, so those names are
            # standardized against the whole cross-section instead.
            src = sub if len(sub) >= 5 else df
            c = _branch(src, w).reindex(index=sub.index)
            contrib.loc[sub.index, list(w.keys())] = c[list(w.keys())].values

    composite = contrib.sum(axis=1, min_count=1)
    return composite, contrib


def row_attribution(contrib_row: pd.Series, min_abs: float = 1e-6) -> list:
    """One name's contributions as a JSON-safe list, biggest mover first.

    `share` is the fraction of the total ABSOLUTE push a theme accounts for — with negatives
    in the mix, a share of the signed total would exceed 100% or flip sign and read as
    nonsense. It answers "how much of what moved this name was this theme", which is the
    question a reader actually has.
    """
    items = [(k, float(v)) for k, v in contrib_row.items()
             if v is not None and not pd.isna(v)]
    total = sum(abs(v) for _, v in items)
    items.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return [{"theme": k, "c": round(v, 4),
             "share": round(abs(v) / total, 4) if total > 0 else 0.0}
            for k, v in items if abs(v) > min_abs]
