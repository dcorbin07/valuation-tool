"""
Gradient-boosted-tree signal combiner — PRE-SPECIFIED GATE. Committed BEFORE it was ever run.

The live composite is LINEAR: a weighted sum of z-scored themes. That cannot express an
interaction — "value only pays when quality is high", "momentum only in calm regimes". Trees
can. This tests whether that extra expressiveness is worth anything OUT OF SAMPLE, or whether
it just fits noise more elaborately.

Committed results-free so the git history proves the gate was fixed before any number came back.
Everything this project has learned says that is the only way a flexible model gets a fair test:
a GBM with 32 features on 136k rows will ALWAYS beat a linear composite in-sample.

--------------------------------------------------------------------------------------------
PROTOCOL — fixed in advance.

  FEATURES   the z-scored per-number columns (z_*) the panel already produces. They are
             standardized WITHIN each date, which is exactly right for a cross-sectional model
             and means no scaling step can leak across dates.
  TARGET     the cross-sectional RANK of forward return within each date, mapped to [0,1].
             Ranks, not raw returns, because the composite is only ever used to ORDER names —
             and because a single +400% row would otherwise dominate the loss.
  SPLITS     the SAME CPCV paths the linear weights are judged on (_cpcv_paths, with purging
             and embargo). Train on the train blocks, predict the held-out blocks, never both.
  SCORE      median out-of-sample IC across paths, exactly like the linear candidates, plus the
             constructed book's net alpha so the comparison is in money as well as correlation.

  MODEL      HistGradientBoostingRegressor, deliberately SMALL and heavily regularized
             (shallow depth, high min-samples-per-leaf, early stopping). A large model would
             prove only that trees can memorize.
  IMPORT     sklearn is OPTIONAL. It is not in requirements.txt, and a missing import returns
             a status dict — it must never break a backtest run.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, and deliberately strict because a flexible model gets many
implicit degrees of freedom that a weighted sum does not:

  1. Median OOS IC must beat the linear composite by at least MIN_IC_GAIN.
  2. The constructed book's NET alpha must improve by at least MIN_ALPHA_GAIN, for BOTH shipped
     configs (roth top-25 and taxable decile) — a combiner that only helps one book shape is
     fitting that shape.
  3. It must hold in BOTH time halves, same rule every other change in this project has faced.
  4. Deflated Sharpe must not DEGRADE. A model with more effective trials that produces the
     same edge is worse, not equal.

Failing any of these is a reject. Rejecting is the expected outcome: the linear composite has
survived CPCV repeatedly, and the honest prior is that 8 themes over 110 dates does not contain
enough independent information to fit interactions reliably.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..screener import settings as S

# Pre-committed gate.
MIN_IC_GAIN = 0.005          # median OOS IC must beat linear by this much
MIN_ALPHA_GAIN = 0.01        # ...and net alpha by 100bps, in BOTH configs and BOTH halves

# Model, fixed in advance. Small on purpose.
GBM_PARAMS = dict(max_depth=3, max_iter=200, learning_rate=0.05,
                  min_samples_leaf=200, l2_regularization=1.0,
                  early_stopping=True, validation_fraction=0.15, random_state=0)


def sklearn_available() -> bool:
    try:
        import sklearn  # noqa: F401
        return True
    except Exception:
        return False


def _feature_cols(panel) -> list:
    """The z-scored numbers, in a STABLE order so a model is reproducible across runs."""
    return [c for c in ("z_" + n for n in S.NUMBERS_ALL)
            if c in panel.columns and panel[c].notna().any()]


def _xy(panel, dates, feats):
    sub = panel[panel["date"].isin(dates)]
    sub = sub.dropna(subset=["fwd_ret"])
    if sub.empty:
        return None, None
    X = sub[feats].astype(float).to_numpy()
    # Cross-sectional rank within each date, in [0,1]. Ranking per date removes any level
    # effect (a good year lifts every name) so the model learns ORDERING, which is all the
    # composite is ever used for.
    y = sub.groupby("date")["fwd_ret"].rank(pct=True).to_numpy()
    return X, y


def fit_predict(panel, train_dates, test_dates, feats=None, params=None):
    """Train on train_dates, return {(date,ticker): score} for test_dates. None if no sklearn."""
    if not sklearn_available():
        return None
    from sklearn.ensemble import HistGradientBoostingRegressor
    feats = feats or _feature_cols(panel)
    Xtr, ytr = _xy(panel, train_dates, feats)
    if Xtr is None or len(Xtr) < 500:
        return None
    m = HistGradientBoostingRegressor(**(params or GBM_PARAMS))
    m.fit(Xtr, ytr)
    te = panel[panel["date"].isin(test_dates)].dropna(subset=["fwd_ret"])
    if te.empty:
        return None
    pred = m.predict(te[feats].astype(float).to_numpy())
    return {(d, t): float(p) for d, t, p in zip(te["date"], te["ticker"], pred)}


def cpcv_compare(panel, cols, weights, n_groups: int = 6, k_test: int = 2,
                 embargo: int = 1) -> dict:
    """GBM vs the linear composite on the SAME purged CPCV paths.

    Returns median OOS IC for each and the per-path detail, so the comparison is like-for-like
    rather than a GBM number quoted next to a linear number from a different split.
    """
    from .fundamental_panel import _cpcv_paths, _spearman
    from ..screener.cross_sectional import zscore
    out = {"available": sklearn_available(), "min_ic_gain": MIN_IC_GAIN,
           "n_paths": 0, "linear_median_ic": None, "gbm_median_ic": None, "paths": []}
    if not out["available"]:
        return {**out, "status": "sklearn not installed (optional dependency)"}
    dates = sorted(panel["date"].unique())
    paths = _cpcv_paths(dates, n_groups=n_groups, k_test=k_test, embargo=embargo)
    if not paths:
        return {**out, "status": "not enough dates for CPCV"}
    feats = _feature_cols(panel)
    out["n_features"] = len(feats)
    lin_ics, gbm_ics = [], []
    for tr, te in paths:
        scores = fit_predict(panel, tr, te, feats)
        if not scores:
            continue
        li, gi = [], []
        for d in te:
            sub = panel[panel["date"] == d].dropna(subset=["fwd_ret"])
            if len(sub) < 20:
                continue
            comp = np.zeros(len(sub))
            for c in cols:
                z = zscore(sub[c]).values
                comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
            g = np.array([scores.get((d, t), np.nan) for t in sub["ticker"]], dtype=float)
            ok = np.isfinite(g)
            if ok.sum() < 20:
                continue
            fr = sub["fwd_ret"].values
            a = _spearman(comp[ok], fr[ok])
            b = _spearman(g[ok], fr[ok])
            if a == a:
                li.append(a)
            if b == b:
                gi.append(b)
        if li and gi:
            lin_ics.append(float(np.median(li)))
            gbm_ics.append(float(np.median(gi)))
            out["paths"].append({"n_train": len(tr), "n_test": len(te),
                                 "linear_ic": lin_ics[-1], "gbm_ic": gbm_ics[-1]})
    if not lin_ics:
        return {**out, "status": "no usable paths"}
    out["n_paths"] = len(lin_ics)
    out["linear_median_ic"] = float(np.median(lin_ics))
    out["gbm_median_ic"] = float(np.median(gbm_ics))
    out["ic_gain"] = out["gbm_median_ic"] - out["linear_median_ic"]
    out["gbm_paths_better"] = float(np.mean([g > l for g, l in zip(gbm_ics, lin_ics)]))
    out["clears_ic_gate"] = bool(out["ic_gain"] >= MIN_IC_GAIN)
    return out


def walk_forward_scores(panel, n_groups: int = 6, embargo: int = 1) -> dict:
    """Out-of-sample GBM score for EVERY row, via expanding-window walk-forward.

    Needed to construct a book from GBM scores without look-ahead: each block is predicted by a
    model trained only on strictly earlier blocks (with an embargo), so no row is ever scored by
    a model that saw its own period or anything after it.
    """
    if not sklearn_available():
        return {}
    dates = sorted(panel["date"].unique())
    blocks = [list(b) for b in np.array_split(range(len(dates)), n_groups)]
    feats = _feature_cols(panel)
    scores = {}
    for bi in range(1, len(blocks)):
        te = [dates[i] for i in blocks[bi]]
        last_train = blocks[bi][0] - 1 - embargo
        if last_train < 8:
            continue
        tr = [dates[i] for i in range(last_train + 1)]
        got = fit_predict(panel, tr, te, feats)
        if got:
            scores.update(got)
    return scores
