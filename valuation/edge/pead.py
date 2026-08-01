"""
Post-earnings announcement drift (PEAD) — PRE-SPECIFIED GATE. Committed BEFORE it was run.

The oldest and most replicated anomaly in the literature: prices under-react to earnings news
and keep drifting in the direction of the surprise for weeks. Now testable here because the
EVENTS earnings code was decoded (code 22 — see bulk.EARNINGS_CODES).

--------------------------------------------------------------------------------------------
THE SIGNAL — two variants, both computed strictly from data public by the rebalance date.

  pead_car    CUMULATIVE ABNORMAL RETURN around the most recent earnings announcement:
              the stock's return over [t-1, t+1] around the announcement, minus the
              benchmark's over the same window. This is the SURPRISE, measured by the market's
              own reaction rather than by an analyst estimate — we have no point-in-time
              estimates (IBES is parked), and the price reaction is the cleaner measure anyway
              because it already embeds whatever the market expected.

  pead_drift  the same CAR, but only counted while the announcement is still RECENT
              (within DRIFT_WINDOW_DAYS). PEAD is documented to decay over ~1-3 months, so a
              CAR from eight months ago is not drift, it is stale momentum. Names whose last
              announcement is older than the window get NO signal rather than a decayed one —
              an explicit absence is honest; a faded number pretends to information.

POINT-IN-TIME: only announcements with date <= as_of are used, and the CAR window must have
CLOSED by as_of (t+1 <= as_of), so a signal never contains a return from the future. That is
enforced in the code, not just intended.

COVERAGE CAVEAT inherited from the decode: EVENTS earnings coverage is PARTIAL (~2.83 per
ticker-year vs ~4 expected). A name with no recent announcement is UNKNOWN, not "no news", so
the signal is left NaN and the theme mean simply skips it.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, and the same one every other signal has faced:

  1. Standalone median IC t-stat >= MIN_IC_TSTAT on the full universe. A signal that cannot
     clear this on its own has no business in a theme.
  2. Adding it must clear the STANDING margins (MIN_HOLDOUT_ALPHA_GAIN = 100bps,
     MIN_HOLDOUT_TSTAT_GAIN = 0.25) in BOTH held-out directions, via holdout_compare_panels.
  3. Coverage must be >= MIN_COVERAGE. A signal present on a tenth of rows cannot move a book
     and would just add noise to the theme mean.

Rejecting is a perfectly good outcome. PEAD is real in the literature but heavily arbitraged
since the 1990s, and our earnings dates are partial — both push against finding it here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Pre-committed gate.
MIN_IC_TSTAT = 2.0
MIN_COVERAGE = 0.30

# Signal construction, fixed in advance.
CAR_WINDOW = (-1, 1)          # trading days around the announcement
DRIFT_WINDOW_DAYS = 63        # ~one quarter; PEAD decays over ~1-3 months


def _car(closes, dates64, bench, i_ann, window=CAR_WINDOW):
    """Cumulative abnormal return over the window around index i_ann, vs the benchmark."""
    lo, hi = i_ann + window[0], i_ann + window[1]
    if lo < 1 or hi >= len(closes):
        return None
    a, b = closes[lo - 1], closes[hi]
    if not (a and b and a > 0 and b > 0):
        return None
    stock = b / a - 1.0
    if bench is None:
        return stock
    ba, bb = bench[lo - 1], bench[hi]
    if not (ba and bb and ba > 0 and bb > 0):
        return stock
    return stock - (bb / ba - 1.0)


def pead_signals(closes, dates64, bench, ann_dates, as_of,
                 drift_days: int = DRIFT_WINDOW_DAYS) -> dict:
    """{pead_car, pead_drift} as of `as_of`, or {} when there is no usable announcement.

    Strictly point-in-time twice over: the announcement must be on or before `as_of`, AND its
    CAR window must have closed by `as_of`, so no future return can leak into the score.
    """
    if not ann_dates or dates64 is None or len(dates64) == 0:
        return {}
    cutoff = np.datetime64(str(as_of)[:10], "D")
    anns = [a for a in ann_dates if np.datetime64(str(a)[:10], "D") <= cutoff]
    if not anns:
        return {}
    latest = np.datetime64(str(anns[-1])[:10], "D")
    i_ann = int(np.searchsorted(dates64, latest, side="right")) - 1
    if i_ann < 1:
        return {}
    # The CAR window must be CLOSED by as_of, else we would be using unrealized future days.
    i_now = int(np.searchsorted(dates64, cutoff, side="right")) - 1
    if i_ann + CAR_WINDOW[1] > i_now:
        return {}
    car = _car(closes, dates64, bench, i_ann)
    if car is None:
        return {}
    out = {"pead_car": float(car)}
    age = int((cutoff - dates64[i_ann]).astype(int))
    # Drift only while the announcement is RECENT. An older CAR is stale momentum, not drift,
    # and is left ABSENT rather than decayed — absence is honest, a faded number is not.
    if age <= drift_days:
        out["pead_drift"] = float(car)
    return out
