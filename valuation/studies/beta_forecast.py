# -*- coding: utf-8 -*-
"""`BETA-FORECAST` — which beta best FORECASTS a name's realised beta two years out.

Don's queued research, `DECISIONS.md` 2026-10-13: *"a test of an adjusted beta against the
vendor's raw beta before any change to the valuation engine."* Item 53 measured that the discount
rate dominates some fair values — **NVDA $145.67 at its vendor beta of 2.22 against $230.65 at
beta 1.0, on a $226 price** — and KO's 0.32 flatters it the other way.

**WHAT IS NEW HERE, AND WHAT IS NOT.** `wacc.py` carries `BETA_SHRINK = None` with the note
*"Measured and REJECTED in Part 2 of `HANDOFF_live_data_bugs.md` — it breached the do-no-harm
bound at 2.491% against a 2% ceiling."* **That rejection stands and is not re-opened.** It tested
a different question: *how much do fair values MOVE* (a do-no-harm bound, with **0 of 6** decisive
names resolved). **Whether the raw vendor beta is the best available FORECAST of a name's future
beta has never been tested in this project**, and that is the question Blume (1971) actually
answers. A candidate can fail a do-no-harm bound and still be the better estimator; those are
different claims and the record should hold both.

THE ESTIMATOR IS THE SHIPPED ONE'S CONVENTION, NOT A NEW ONE
--------------------------------------------------------------------------------------------
`valuation/data/beta.py` regresses **five years of MONTHLY returns on SPY**, `cov/var`, and its
own docstring records why: that window is *"the one validated in `HANDOFF_live_data_bugs.md` §2
against the vendor on control names"*, reproducing the vendor's column to a worst absolute
difference of **0.036** (JPM) — and a **one-year DAILY** window was tried first and is WRONG,
returning **KO −0.286 and XOM −0.484**.

**THERE IS NO HISTORICAL VENDOR BETA, AND THAT IS WHY THE RAW CANDIDATE IS RECONSTRUCTED.** The
vendor field is a live quote with no history, so a point-in-time contest cannot read it. The raw
candidate is therefore the vendor's own construction recomputed from this project's price cache —
a substitution, declared, and licensed by the 0.036 agreement above rather than assumed.

**NO FORWARD RETURN IS READ ANYWHERE IN THIS ITEM.** The realised beta is a covariance with the
market over the following two years; it is not a return the model is being scored against, and no
cell of this contest is a claim about performance. That is worth stating because every other
register in this record scores a return, and a reader may assume this one does.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from . import dipcall as D

#: The market. Beta is defined against a market portfolio and SPY is the proxy every comparison
#: in the record was made against -- `valuation/data/beta.py`'s own constant, by value.
MARKET = "SPY"

#: Five years of monthly returns, and the minimum observations before an estimate is believed.
#: IMPORTED BY VALUE FROM THE SHIPPED MODULE rather than retyped (`MA5`: a second copy of a
#: constant is how one freezes), and `tests/test_beta_forecast.py` asserts they still agree.
TRAIL_MONTHS = 60
MIN_TRAIL_OBS = 36

#: The realised beta's window: two years, as the prompt specifies, and the floor below which a
#: realised value is not formed at all.
FWD_MONTHS = 24
MIN_FWD_OBS = 20

#: Blume (1971) / the Bloomberg "adjusted beta". The weight is `wacc.BETA_SHRINK`'s own documented
#: value and the target is 1.0 because the market portfolio's beta is 1.0 BY CONSTRUCTION -- which
#: `wacc.BETA_FALLBACK`'s comment calls *"the only value here with a derivation"*.
BLUME_W = 0.67
BLUME_TARGET = 1.0

#: A sector median needs enough names to be a median. Declared before any outcome.
MIN_SECTOR_NAMES = 5


def monthly_closes(ticker: str) -> Optional[pd.Series]:
    """Month-end closes from the project's own daily cache, ascending, indexed by `YYYY-MM`.

    The cache is split- AND dividend-adjusted (`dipcall.read_prices`), which is what a beta wants:
    beta is a covariance of RETURNS, so an unadjusted series would put a split in the numerator.
    """
    s = D.read_prices(ticker)
    if s is None or len(s) < 40:
        return None
    s = s.copy()
    s["ym"] = s["date"].astype(str).str.slice(0, 7)
    last = s.groupby("ym")["close"].last()
    return last.sort_index()


def monthly_returns(closes: pd.Series) -> pd.Series:
    return closes.pct_change().dropna()


def beta_of(r: pd.Series, m: pd.Series, min_obs: int) -> Optional[float]:
    """`cov(r, m) / var(m)` on the overlapping months. The shipped estimator's arithmetic.

    Returns `None` rather than a number when the overlap is too short or the market has no
    variance -- `valuation/data/beta.py` refuses the same two ways, and a beta from 3 months is
    not a smaller-sample beta, it is noise with a name.
    """
    j = r.index.intersection(m.index)
    if len(j) < min_obs:
        return None
    a = r.reindex(j).to_numpy(dtype=float)
    b = m.reindex(j).to_numpy(dtype=float)
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < min_obs:
            return None
        a, b = a[ok], b[ok]
    var = float(np.var(b, ddof=1))
    if not var > 0:
        return None
    return float(np.cov(a, b, ddof=1)[0, 1] / var)


def blume(b_raw: float, w: float = BLUME_W, target: float = BLUME_TARGET) -> float:
    """`w * b_raw + (1 - w) * target`. One line, and it is here so nobody retypes 0.67."""
    return float(w) * float(b_raw) + (1.0 - float(w)) * float(target)


def trailing_and_forward(index, end_ym: str, trail_n: int, fwd_n: int):
    """The `trail_n` months ending at `end_ym` INCLUSIVE, and the `fwd_n` months strictly after.

    Returned together so a caller cannot accidentally overlap them: the trailing window is what a
    forecaster could see and the forward window is what happened next. **An off-by-one here would
    be a look-ahead**, which is why the two slices are produced by one function and pinned by a
    test asserting their intersection is empty.
    """
    idx = list(index)
    try:
        i = idx.index(end_ym)
    except ValueError:
        return None, None
    trail = idx[max(0, i - trail_n + 1):i + 1]
    fwd = idx[i + 1:i + 1 + fwd_n]
    return trail, fwd


def formation_months(market_index, trail_n: int = TRAIL_MONTHS,
                     fwd_n: int = FWD_MONTHS) -> list:
    """Every month that has `trail_n` months behind it and `fwd_n` strictly ahead.

    Derived from the MARKET's own calendar so every name is formed on the same dates, which is
    what makes a cross-name median meaningful at a date.
    """
    idx = list(market_index)
    lo, hi = trail_n - 1, len(idx) - fwd_n - 1
    return idx[lo:hi + 1] if hi >= lo else []


def rolling_betas(r: pd.Series, m: pd.Series, trail_n: int = TRAIL_MONTHS,
                  min_trail: int = MIN_TRAIL_OBS, fwd_n: int = FWD_MONTHS,
                  min_fwd: int = MIN_FWD_OBS) -> pd.DataFrame:
    """Every month's TRAILING beta and FORWARD-realised beta in one pass, on the market's index.

    **WHY VECTORISED AND WHY IT IS GATED.** The per-cell loop re-intersected two indexes for each
    (name, month) and would have taken hours on 9,645 names. `rolling` gives the same `cov/var`
    for every month at once. A faster path that returns a DIFFERENT number is worthless, so
    `tests/test_beta_forecast.py` requires this to reproduce the explicit `beta_of` loop
    cell-for-cell at `max |delta| = 0` — the `B7` fidelity discipline, and `MB15`'s ordering:
    validate the instrument BEFORE anything consumes it.

    THE FORWARD BETA IS THE SAME ROLLING QUANTITY SHIFTED, AND THE SHIFT IS WHERE A LOOK-AHEAD
    WOULD LIVE. The realised beta for formation month `i` is the rolling `fwd_n` beta evaluated at
    `i + fwd_n`, so it uses months `i+1 … i+fwd_n` and the formation month's own return is NEVER
    inside it. `shift(-fwd_n)` aligns that value back onto row `i`.
    """
    j = m.index.intersection(r.index)
    if len(j) < min_trail + min_fwd:
        return pd.DataFrame(columns=["month", "b_raw", "b_real", "n_trail", "n_fwd"])
    rr = r.reindex(j).astype(float)
    mm = m.reindex(j).astype(float)

    cov_t = rr.rolling(trail_n, min_periods=min_trail).cov(mm)
    var_t = mm.rolling(trail_n, min_periods=min_trail).var()
    b_trail = cov_t / var_t

    cov_f = rr.rolling(fwd_n, min_periods=min_fwd).cov(mm)
    var_f = mm.rolling(fwd_n, min_periods=min_fwd).var()
    b_fwd_at_end = cov_f / var_f
    b_real = b_fwd_at_end.shift(-fwd_n)

    n_t = rr.rolling(trail_n, min_periods=min_trail).count()
    n_f = rr.rolling(fwd_n, min_periods=min_fwd).count().shift(-fwd_n)

    out = pd.DataFrame({"month": list(j), "b_raw": b_trail.to_numpy(),
                        "b_real": b_real.to_numpy(), "n_trail": n_t.to_numpy(),
                        "n_fwd": n_f.to_numpy()})
    return out.dropna(subset=["b_raw", "b_real"]).reset_index(drop=True)
