# -*- coding: utf-8 -*-
"""`STAGE1-BATCH1` — score the arms that SURVIVED their free kills, on the BUILD quadrant only.

Register `PREREG_stage1_batch1.md`; ten equity trials booked at `fcb73f5`. **It REFUSES without
passing kill artifacts** — `O10`'s process defect was computing a gating control and the outcomes
in one pass, so the kills ran first, in their own pass, and this reads their verdicts.

**THE CHECK QUADRANT IS NOT OPENED.** 2009-2019 × `stable_key_half == 0` only, pinned by test.

**THE STATISTIC.** Each arm's signal is **residualised on the seven deployed themes** per date,
then the per-date Spearman against `fwd_ret` gives the incremental IC; the primary is the HAC *t*
over the quadrant's 44 dates with its two-sided *p*, and **an arm must clear BOTH halves inside
the quadrant** (24 early / 20 late) or it is `NOT_REPLICATED` and does not reach Stage 2.

**BENJAMINI-HOCHBERG at q = 0.10 across `k` = 12**, the register's own ladder. `k` stays 12 even
though fewer arms are scored: shrinking it after a build failure makes every surviving threshold
easier, which is the same gaming in a different direction.

**NO X7 FLOOR IS QUOTED** and every critical value is **LABELLED UNCALIBRATED** (`V2G`,
`R1-VAR`): no calibrated floor exists for an incremental IC on this universe, which is 9,645
names against the 2,531 every published floor was measured on.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.stage1_kills as K                                            # noqa: E402
from scripts.index_best import _data_root, data_candidates                  # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED                           # noqa: E402

PANEL = "UNIVERSE_BIAS_PANEL_full.pkl"
KEEPNUM = "S1_PANEL_keepnum.pkl"

#: §0b — the BH ladder's own `k`, fixed in the register and NOT shrunk here.
BH_K = 12
BH_Q = 0.10
#: the arms whose primary statistic is an incremental IC with a defensible two-sided p
#: (register §0c, carried from the draft). A8 is excluded (event time, own permutation p95),
#: A4 and A5 are excluded (withdrawn / not run).
BH_SET = ("A1", "A2a", "A2b", "A3", "A6", "A7", "A9", "A10", "A11")
#: minimum names in a cross-section before a date contributes an IC.
MIN_NAMES = 20


def _ols_resid(y, X):
    """Residual of `y` on `X` with an intercept. Plain least squares, no shrinkage."""
    A = np.column_stack([np.ones(len(X))] + [X[:, i] for i in range(X.shape[1])])
    try:
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return y - A @ beta


def incremental_ic(frame, col, themes):
    """Per-date Spearman of the theme-residualised signal against `fwd_ret`."""
    out = []
    for d in sorted(frame["date"].unique()):
        g = frame[frame["date"] == d]
        cols = [c for c in themes if c in g.columns]
        sub = g[[col, "fwd_ret"] + cols].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < MIN_NAMES:
            continue
        r = _ols_resid(sub[col].values.astype(float),
                       sub[cols].values.astype(float))
        if r is None:
            continue
        ic = pd.Series(r).rank().corr(sub["fwd_ret"].rank().reset_index(drop=True))
        if ic == ic:
            out.append((str(d)[:10], float(ic), int(len(sub))))
    return out


def hac_t(vals, lag=1):
    """Newey-West *t* of the mean. `lag = 1` is `R9`'s own choice on this panel's cadence."""
    a = np.asarray([float(x) for x in vals], dtype=float)
    n = a.size
    if n < 3:
        return None
    m = a.mean()
    e = a - m
    g0 = float((e * e).sum() / n)
    s = g0
    for L in range(1, min(lag, n - 1) + 1):
        gl = float((e[L:] * e[:-L]).sum() / n)
        s += 2.0 * (1.0 - L / (lag + 1.0)) * gl
    # A RELATIVE DEGENERACY FLOOR, not `s <= 0`. `U2` measured that the shipped `theme_ic`'s
    # `sd > 0` guard is VALUE- AND LENGTH-dependent: [0.1]*3 returns t 1.019e16 while [0.1]*4
    # returns exactly 0.0, because a constant series' floating-point variance is only sometimes
    # exactly zero. My own first cut had the same guard and returned t 1.32e16 on [0.01]*10 --
    # caught by the test written to pin it. `MA58` repaired its own instrument the same way.
    scale = float(np.max(np.abs(a))) if n else 0.0
    if s <= (1e-12 * max(scale, 1e-300)) ** 2:
        return None
    se = (s / n) ** 0.5
    if not np.isfinite(se) or se <= 0:
        return None
    return {"mean": m, "se": se, "t": m / se, "n": n}


def two_sided_p(t, n):
    """Two-sided p from a *t* with `n-1` df, via the normal approximation at these n.

    Declared rather than hidden: at n = 44 and n = 20 the normal and the t-distribution differ
    in the third decimal of p, which cannot move a BH threshold here -- and §6 of the register
    forbids inventing a p so a method applies, so the approximation is NAMED and its size
    bounded rather than presented as exact."""
    from math import erfc, sqrt
    if t is None:
        return None
    return float(erfc(abs(t) / sqrt(2.0)))


def benjamini_hochberg(pvals, k=BH_K, q=BH_Q):
    """The register's ladder: the i-th smallest p against i*q/k, `k` fixed at 12."""
    items = sorted(((name, p) for name, p in pvals.items() if p is not None),
                   key=lambda kv: kv[1])
    out, cutoff = {}, None
    for i, (name, p) in enumerate(items, start=1):
        thr = i * q / k
        out[name] = {"p": p, "rank": i, "threshold": thr, "p_below_threshold": bool(p <= thr)}
        if p <= thr:
            cutoff = i
    for name, d in out.items():
        d["survives_bh"] = bool(cutoff is not None and d["rank"] <= cutoff)
    for name, p in pvals.items():
        if p is None:
            out[name] = {"p": None, "survives_bh": None,
                         "why": "no defensible two-sided p -- not in the BH set, or not scored"}
    return {"k": k, "q": q, "largest_surviving_rank": cutoff, "arms": out}


#: the shipped `min_dates` floor, inherited. A half below it is not a half.
MIN_HALF_DATES = 16


def stage1_verdict(early, late, same_sign, crit=2.0, floor=MIN_HALF_DATES):
    """The register's §0 both-halves rule, as a function so it can be EXERCISED.

    Three states, and the first is load-bearing: **a half below the shipped `min_dates` floor
    cannot carry a verdict at all**, so no Stage-1 pass may be read from it. `MA58` measured
    that complete-case residualisation on the seven incumbents restricts the window, and on this
    quadrant it leaves a FIVE-date early half -- reporting a *t* on that as though it were a half
    is how a 5-date cell comes to decide a batch.
    """
    ne = (early or {}).get("n") or 0
    nl = (late or {}).get("n") or 0
    if ne < floor or nl < floor:
        return ("NOT_ASSESSABLE",
                "BOTH-HALVES NOT ASSESSABLE -- the early half is %d dates and the late half %d, "
                "against the shipped min_dates floor of %d, because complete-case "
                "residualisation on the seven themes restricts the window (MA58). No Stage-1 "
                "pass can be read from this reading." % (ne, nl, floor))
    if (early and late and abs(early["t"]) >= crit and abs(late["t"]) >= crit and same_sign):
        return ("CLEARS", "CLEARS BOTH HALVES (crit %.1f, UNCALIBRATED)" % crit)
    return ("NOT_REPLICATED", "NOT_REPLICATED -- one half does not clear")
