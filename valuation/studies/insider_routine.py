# -*- coding: utf-8 -*-
"""Cohen-Malloy-Pomorski ROUTINE / OPPORTUNISTIC classification of insider trades.

`PKG-MB20`. Lives under `valuation/studies/` because `MA23`'s boundary test forbids a non-study
module importing `valuation.studies`, and nothing on the live scoring path may depend on this.

THE RULE, STATED ONCE AND NEVER RESTATED ELSEWHERE.
    A trade by insider `o` in ticker `t`, in calendar month `m` of year `y`, is **ROUTINE** if
    that same `(t, o)` pair also traded in month `m` in years `y-1` AND `y-2`. Otherwise it is
    **OPPORTUNISTIC**.

    Three consecutive years, which is Cohen-Malloy-Pomorski's published rule and the one the
    hypothesis names.

IT IS POINT-IN-TIME BY CONSTRUCTION, not by a filter applied afterwards. The test looks only at
years STRICTLY BEFORE the trade's own, so a trade can never be classified using anything that
had not already happened when it was made. There is no `as_of` parameter and there is nothing to
get wrong: a routine label becomes available exactly when the third repeat occurs, which is what
"routine only from the year the third repeat becomes observable" means.

A CORRECTION TO THE PREMISE THIS INHERITS, AND IT IS WHY THE RULE IS WRITTEN OUT ABOVE RATHER
THAN CITED. `MA57`'s published routine share of **48.72%** is a **FOUR**-consecutive-year figure:
its test is `all((y - dd) in ys for dd in (1, 2, 3))`, i.e. year `y` plus the three before it.
On the identical population the three-year rule reads **60.47%** (52,798 of 87,318 pairs against
MA57's 42,537). The pair count reproduces exactly, so it is the same object and only the rule
differs. `scripts/mb20_census.py` reproduces MA57's own figure under MA57's own rule as the
instrument check that licenses the comparison.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

#: Consecutive years required. Cohen-Malloy-Pomorski's published rule.
CONSECUTIVE_YEARS = 3

ROUTINE = "ROUTINE"
OPPORTUNISTIC = "OPPORTUNISTIC"
#: A trade with no owner or no trade date can be classified NEITHER way. It is a NAMED STATE and
#: never silently folded into `OPPORTUNISTIC` -- doing that would turn the opportunistic arm into
#: a data-availability screen wearing a behavioural screen's name, which is `S10`'s failure mode.
UNCLASSIFIABLE = "UNCLASSIFIABLE"


def classify(frame: pd.DataFrame,
             ticker_col: str = "ticker",
             owner_col: str = "ownername",
             date_col: str = "transactiondate") -> pd.Series:
    """Return a Series of `ROUTINE` / `OPPORTUNISTIC` / `UNCLASSIFIABLE`, aligned to `frame`.

    Vectorised: the membership test is a set lookup over `(ticker, owner, month, year)` keys, so
    the cost is linear in rows rather than quadratic in an insider's history.
    """
    tk = frame[ticker_col].astype("string")
    ow = frame[owner_col].astype("string")
    td = pd.to_datetime(frame[date_col], errors="coerce")

    ok = tk.notna() & ow.notna() & td.notna()
    out = pd.Series(UNCLASSIFIABLE, index=frame.index, dtype=object)
    if not ok.any():
        return out

    sub = pd.DataFrame({"tk": tk[ok], "ow": ow[ok],
                        "y": td[ok].dt.year.astype("int64"),
                        "m": td[ok].dt.month.astype("int64")})
    # The observed set of (pair, month, year) cells. A trade is routine when its own cell's two
    # PRIOR years are both present -- strictly before, so no look-ahead is possible.
    seen = set(zip(sub["tk"].tolist(), sub["ow"].tolist(),
                   sub["m"].tolist(), sub["y"].tolist()))
    keys = list(zip(sub["tk"].tolist(), sub["ow"].tolist(),
                    sub["m"].tolist(), sub["y"].tolist()))
    lab = [ROUTINE if all((t, o, m, y - back) in seen
                          for back in range(1, CONSECUTIVE_YEARS))
           else OPPORTUNISTIC
           for (t, o, m, y) in keys]
    out.loc[ok] = lab
    return out


def coverage(labels: Iterable[str]) -> dict:
    """Census of the three states. `UNCLASSIFIABLE` is REPORTED, never read as zero."""
    s = pd.Series(list(labels), dtype=object)
    n = int(len(s))
    counts = {k: int((s == k).sum()) for k in (ROUTINE, OPPORTUNISTIC, UNCLASSIFIABLE)}
    classifiable = counts[ROUTINE] + counts[OPPORTUNISTIC]
    return {
        "rows": n,
        "counts": counts,
        "frac_classifiable": (classifiable / n) if n else None,
        # The routine share is quoted over the CLASSIFIABLE rows, because a share over all rows
        # silently mixes "not routine" with "cannot tell" -- two different statements.
        "routine_share_of_classifiable": (counts[ROUTINE] / classifiable) if classifiable else None,
    }


def opportunistic_mask(labels: Iterable[str]) -> np.ndarray:
    """Rows the opportunistic-only variant KEEPS.

    An `UNCLASSIFIABLE` row is KEPT. That is the conservative direction and it is deliberate:
    dropping it would make the variant differ from the incumbent wherever the DATA is missing as
    well as wherever the BEHAVIOUR differs, so a verdict could not be attributed to the
    hypothesis. On this export the choice is inert -- every row the shipped score can value is
    classifiable, measured, so the set is empty -- but a refusal that costs nothing today is the
    one you want present the day the export changes.
    """
    s = pd.Series(list(labels), dtype=object)
    return (s != ROUTINE).to_numpy()
