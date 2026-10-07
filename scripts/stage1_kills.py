# -*- coding: utf-8 -*-
"""`STAGE1-BATCH1` — every arm's FREE PRE-OUTCOME KILL, in its own pass. ZERO TRIALS HERE.

Register `PREREG_stage1_batch1.md`; ten equity trials booked at `fcb73f5` before any runner
existed. **This pass computes no outcome statistic: no forward return is read, no arm is scored.**
Under `MB1-SEL` a pre-outcome control can only ever BLOCK a design, never produce a finding, so
it adds no degree of freedom — which is why the kills are free and why they are run FIRST.
`O10`'s process defect was computing a gating control and the outcomes in one pass; the scoring
runner **refuses** without a passing artifact from this one.

**THE BUILD QUADRANT ONLY.** 2009-2019 × `stable_key_half(ticker) == 0`, using
`r4_x1_accounting_universe.stable_key_half` — **CALLED, never re-implemented** (`B7`). The check
quadrant is not touched anywhere in this file, pinned by test.

**COVERAGE IS MEASURED ON EACH ARM'S OWN POPULATION, NEVER ON THE PANEL.** `O-1` applied an
alert-book figure to the panel and was **~17× wrong**.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.r4_x1_accounting_universe import stable_key_half               # noqa: E402

#: §0 — the quadrant. Half 0 is the BUILD half; half 1 is never read in Stage 1.
BUILD_HALF = 0
BUILD_END = "2019-12-31"
#: §0 — the both-halves boundary inside the build quadrant.
BUILD_HALF_SPLIT = "2014-12-31"
#: the project's own non-null rule, inherited by every coverage kill here.
COVERAGE_FLOOR = 0.70
#: the costume bar, `N6`'s, which `N6` itself cleared at 0.2604.
COSTUME_BAR = 0.60
#: A2a's inertness bar. `S15` was "nearly inert" at 0.9879 and told us almost nothing.
INERT_BAR = 0.995
#: A3's daily-observation requirement, and the floor that stops a short trading year reading as
#: a coverage hole (`MC12`: 2001 read exactly 0.000 against a fixed >=250 bar after the NYSE
#: closed following 9/11, and the year-relative replacement then went vacuous on 1997).
MIN_DAILY_OBS = 200
MIN_PLAUSIBLE_SESSIONS = 220
#: A8's announcements-per-ticker-year band, around the ~4 a year the record expects.
ANN_PER_YEAR_BAND = (3.0, 5.0)


def build_quadrant(panel):
    """The build quadrant, and nothing else. Returns (frame, census)."""
    p = panel.copy()
    p["_half"] = [stable_key_half(t) for t in p["ticker"]]
    d = p["date"].astype(str)
    b = p[(p["_half"] == BUILD_HALF) & (d <= BUILD_END)]
    g = sorted(b["date"].unique())
    npd = b.groupby("date")["ticker"].nunique()
    early = [x for x in g if str(x)[:10] <= BUILD_HALF_SPLIT]
    cen = {"rows": int(len(b)), "dates": len(g), "names": int(b["ticker"].nunique()),
           "first": str(g[0])[:10], "last": str(g[-1])[:10],
           "names_per_date": {"min": int(npd.min()), "median": float(npd.median()),
                              "max": int(npd.max())},
           "halves": {"early_dates": len(early), "late_dates": len(g) - len(early),
                      "boundary": BUILD_HALF_SPLIT}}
    return b, cen


def _nonnull_share(frame, col):
    if col not in frame.columns:
        return {"present": False, "share": 0.0, "rows": int(len(frame))}
    v = pd.to_numeric(frame[col], errors="coerce")
    return {"present": True, "share": float(v.notna().mean()), "rows": int(len(frame)),
            "nonnull": int(v.notna().sum())}


def costume_rho(frame, col, against):
    """Mean per-date |Spearman| of `col` against `against`. The costume bar's own statistic."""
    rs = []
    for d in sorted(frame["date"].unique()):
        g = frame[frame["date"] == d]
        a = pd.to_numeric(g[col], errors="coerce")
        b = pd.to_numeric(g[against], errors="coerce")
        m = a.notna() & b.notna()
        if m.sum() < 20:
            continue
        r = a[m].rank().corr(b[m].rank())
        if r == r:
            rs.append(abs(float(r)))
    if not rs:
        return None
    return {"mean_abs_rho": float(np.mean(rs)), "max_abs_rho": float(np.max(rs)),
            "dates": len(rs)}


def verdict(name, passed, detail):
    return {"arm": name, "kill_passes": (None if passed is None else bool(passed)),
            "detail": detail}
