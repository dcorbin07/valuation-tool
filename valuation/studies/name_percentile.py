"""
I-2 -- the name-level percentile engine.

`IDEAS_LEDGER.md` PART 3. A port of TIDEMARK's expanding-percentile machinery
(`tidemark/stats/percentile.py`, `tests/test_percentile.py`) from ONE long time series to
**per-name signal histories** on this project's panel. Unblocks `E-6` (the temporal axis), and
ships with the burn-in census so the survivorship cost is a printed fact before any arm.

**METHOD CROSSES; NO TIDEMARK DATA CROSSES.** `MB24` marks data flow between the two projects
OUT OF SCOPE and that is untouched here: nothing under `data/` is read from TIDEMARK, no series
is imported, and the only thing that travels is the four rules below and the test that enforces
the first of them. This is exactly the fence `MB22`/`MB23` established when they ported
`power_gate` and `hodrick` -- *"No TIDEMARK data crosses. `MB24` marks data flow out of scope;
only the method crosses"*.

**ZERO TRIALS. NO VERDICT. NO OUTCOME RELATIONSHIP IS COMPUTED HERE.** This module never sees
`fwd_ret`. It transforms a signal column and counts what survives; scoring the transform against
returns is `E-6`'s arm, `E-6`'s register and `E-6`'s trial.

THE FOUR RULES, WHICH ARE TIDEMARK'S AND ARE QUOTED BECAUSE THEY ARE THE POINT
------------------------------------------------------------------------------
1. **EXPANDING WINDOW, NOT ROLLING.** *"Cheap versus its own history" must mean the whole
   history known at that date.* A rolling window silently changes the claim to "cheap versus the
   last k quarters", which is weaker and is the version that makes everything look
   mean-reverting because the reference level chases the value.

2. **NO LOOK-AHEAD, ENFORCED IN CODE.** The percentile at t uses observations up to and
   including t and nothing after. `tests/test_i2_name_percentile.py` carries the ported
   load-bearing test -- *"if this fails, every percentile in the project is a lie"* -- in its
   panel form: computing on a panel truncated to its first k dates must be BIT-IDENTICAL to
   computing on the whole panel and truncating afterwards.

3. **A BURN-IN, BELOW WHICH THE ANSWER IS `NaN` AND NOT A NUMBER.** A percentile computed on
   eleven observations is not a percentile.

4. **PUBLICATION LAG IS APPLIED, NOT ASSUMED AWAY.** A value carries the date it was actually
   knowable, not the date it describes.

THE ONE PLACE THE PORT MUST DIFFER, AND IT IS A DECISION RATHER THAN A DETAIL
-----------------------------------------------------------------------------
TIDEMARK's series is a dense monthly index with no gaps, so "360 observations" and "30 years"
are the same statement. **This panel is not dense.** It carries 69 quarterly dates and 2,531
names, and the median name is present on 48 of them -- names list, delist and lapse coverage.

So an observation count and an elapsed span come apart, and a register writing *"a five-year
burn-in"* has to mean one of them. This module implements the **observation count** (TIDEMARK's
semantics: `dropna()` then index positionally, so the burn-in is a count of the name's own valid
readings) and then **reports the elapsed span it actually bought**, per row, in
`history_years`. That turns an invisible assumption into a printed number: a register can say
"20 observations" and check whether its median row got five years or nine.

`eligible_rows()` additionally accepts an explicit `min_history_years`, so a register that means
calendar time can require BOTH. It has no default, for the reason in the next paragraph.

NOTHING HERE HAS A DEFAULT THAT COULD BECOME A BAR
---------------------------------------------------
`burn_in` and `invert` are required. `MA5` measured that a default is exactly how the
Harvey-Liu-Zhu bar froze at 3.0 and stayed there for months; and TIDEMARK's own docstring says
of orientation that *"sign errors here invert every conclusion in the project"*. This record has
three sign incidents already -- the `monotonicity` convention read backwards for weeks, `U3`'s
`drag_vs_equity_pp` printing a gain under a loss's name, and `MB8`'s register pricing a
fail-open with the wrong sign. So the caller declares the direction; the module will not guess.

THE DATE COLUMN IS A STRING ON THIS PANEL, AND THAT HAS ALREADY COST A CONTROL
------------------------------------------------------------------------------
`panel_r5r6.pkl` and its siblings carry `date` as `str`. `MB21`'s `C1` coerced those to
`pd.Timestamp`, matched **zero of 113,945 rows**, and then scored a perfect 0.000e+00 by
comparing nothing. Ordering is taken on the ISO string, which sorts chronologically, and the
format is VALIDATED rather than assumed -- a non-ISO date raises instead of silently sorting
into a wrong order.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "PERCENTILE_RULES",
    "burn_in_census",
    "eligible_rows",
    "expanding_percentile",
    "name_percentiles",
    "publication_lag_dates",
    "validate_dates",
]

PERCENTILE_RULES = (
    "1 expanding window, never rolling; 2 no look-ahead, enforced by test; 3 a burn-in below "
    "which the answer is NaN and not a number; 4 publication lag applied, not assumed away. "
    "Ported from TIDEMARK; method only, no data (MB24)."
)

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")


# --------------------------------------------------------------------------- dates

def validate_dates(dates: Sequence) -> List[str]:
    """Normalise to ISO `YYYY-MM-DD` strings and REFUSE anything that is not one.

    Ordering the panel means ordering these; an ISO string sorts chronologically and anything
    else may not. `MB21`'s `C1` is why this raises rather than coercing: a silent mismatch there
    produced an empty frame that a control then scored perfectly.
    """
    out = []
    for d in dates:
        s = str(d)[:10]
        if not _ISO.match(s):
            raise ValueError(
                f"name_percentile: date {d!r} is not ISO YYYY-MM-DD. Ordering is taken on the "
                f"string, so a different format would sort into a wrong order silently.")
        out.append(s)
    return out


def publication_lag_dates(dates: Sequence, lag_days: int) -> List[str]:
    """The dates a reading was actually KNOWABLE, given a lag in calendar days.

    Rule 4. `lag_days = 0` is the identity and is the honest default ONLY when the caller has
    established the input is already point-in-time -- which this panel's fundamentals are, being
    lagged by filing date upstream. It is still required, so a register states which it meant.
    """
    if lag_days is None:
        raise ValueError("name_percentile.publication_lag_dates: lag_days is required")
    ref = pd.to_datetime(pd.Index(validate_dates(dates)))
    return [d.strftime("%Y-%m-%d") for d in (ref + pd.Timedelta(days=int(lag_days)))]


# --------------------------------------------------------------------------- the engine

def expanding_percentile(values: Sequence[float], burn_in: int) -> np.ndarray:
    """Fraction of the history up to and INCLUDING t that is <= the value at t.

    Uses only past-and-present data by construction, and returns NaN before `burn_in` valid
    observations exist. `values` must already be in chronological order and free of NaN -- the
    panel wrapper below handles the dropping, so that this function is the definition and
    nothing else.

    Deliberately the plain O(n^2) form. It is the docstring written out, it runs in milliseconds
    on the longest history here (69 quarters), and this is the function every number a consumer
    produces ultimately rests on. TIDEMARK's own note applies unchanged: *a cleverer incremental
    version would be faster and harder to check against the docstring.*
    """
    if burn_in is None:
        raise ValueError("name_percentile.expanding_percentile: burn_in is required, there is "
                         "no default -- rule 3 is a register's decision, not a library's")
    b = int(burn_in)
    if b < 1:
        raise ValueError(f"burn_in must be >= 1, got {b}")
    v = np.asarray(values, dtype=float)
    n = v.size
    out = np.full(n, np.nan)
    for i in range(b - 1, n):
        out[i] = np.count_nonzero(v[:i + 1] <= v[i]) / (i + 1)
    return out


def name_percentiles(frame: pd.DataFrame, value_col: str, *, burn_in: int, invert: bool,
                     name_col: str = "ticker", date_col: str = "date",
                     lag_days: int = 0, out_col: Optional[str] = None) -> pd.DataFrame:
    """Expanding percentile of `value_col` within each NAME's own history.

    Returns the frame's `(name, date)` keys plus:
        `<out_col>`      0..1, NaN before the burn-in
        `n_history`      how many of the name's own observations the percentile rests on
        `history_years`  how many CALENDAR years those observations spanned  (see the docstring)
        `knowable_at`    the date the reading was usable, after `lag_days`

    `invert` is REQUIRED: `True` mirrors the percentile (`1 - p`), for an input where a high raw
    value means the opposite of what the register wants a high percentile to mean. It is applied
    EXACTLY ONCE, pinned by test, because a double inversion is a no-op that looks like a
    decision.
    """
    if invert is None:
        raise ValueError("name_percentile.name_percentiles: `invert` is required. TIDEMARK's "
                         "own rule: a sign error here inverts every conclusion.")
    if value_col not in frame.columns:
        raise KeyError(f"name_percentile: column {value_col!r} is not in the frame")
    oc = out_col or f"{value_col}_pct"

    work = frame[[name_col, date_col, value_col]].copy()
    work[date_col] = validate_dates(work[date_col])
    work["_v"] = pd.to_numeric(work[value_col], errors="coerce")

    pieces = []
    for name, g in work.groupby(name_col, sort=True):
        g = g.sort_values(date_col, kind="mergesort")
        ok = g["_v"].notna().to_numpy()
        gv = g.loc[ok]
        if not len(gv):
            continue
        p = expanding_percentile(gv["_v"].to_numpy(dtype=float), burn_in=burn_in)
        if invert:
            p = 1.0 - p
        ds = pd.to_datetime(pd.Index(gv[date_col].tolist()))
        span = np.array([(ds[i] - ds[0]).days / 365.25 for i in range(len(ds))], dtype=float)
        pieces.append(pd.DataFrame({
            name_col: gv[name_col].to_numpy(),
            date_col: gv[date_col].to_numpy(),
            oc: p,
            "n_history": np.arange(1, len(gv) + 1, dtype=int),
            "history_years": span,
        }))
    if not pieces:
        return pd.DataFrame(columns=[name_col, date_col, oc, "n_history", "history_years",
                                     "knowable_at"])
    out = pd.concat(pieces, ignore_index=True)
    out["knowable_at"] = publication_lag_dates(out[date_col].tolist(), lag_days)
    return out


def eligible_rows(pct: pd.DataFrame, value_pct_col: str, *,
                  min_history_years: Optional[float] = None) -> pd.Series:
    """Boolean mask of rows a register may actually score.

    A row is eligible when the percentile is not NaN (rule 3 has been satisfied) and, if the
    register declared one, when the history also spans `min_history_years` of CALENDAR time.
    The second gate exists because an observation count and an elapsed span come apart on a
    panel with gaps -- see the module docstring.
    """
    ok = pct[value_pct_col].notna()
    if min_history_years is not None:
        ok = ok & (pct["history_years"] >= float(min_history_years))
    return ok


# --------------------------------------------------------------------------- the census

def burn_in_census(frame: pd.DataFrame, value_col: str, burn_ins: Sequence[int], *,
                   invert: bool, name_col: str = "ticker", date_col: str = "date",
                   min_names_per_date: int = 0) -> Dict[str, object]:
    """What each candidate burn-in costs, as a printed fact rather than an assumption.

    Rule 3 is a survivorship trade: a longer burn-in buys a better-founded percentile and pays
    for it in rows, in names and in dates -- and the bill falls on the EARLY end of the panel,
    where the youngest history is. `E-6`'s pre-outcome kill reads the row fraction here.

    Reports, per burn-in: eligible rows and their share, eligible names, eligible dates, the
    first eligible date, and the MEDIAN CALENDAR YEARS the burn-in actually bought -- which is
    the number a register saying "five years" needs in order to know whether it got five years.

    **This computes no outcome relationship.** It never touches `fwd_ret`.
    """
    base = frame[[name_col, date_col, value_col]].copy()
    base[date_col] = validate_dates(base[date_col])
    total_rows = int(base[value_col].notna().sum())
    all_dates = sorted(base[date_col].unique())

    rows = []
    for b in burn_ins:
        p = name_percentiles(base, value_col, burn_in=int(b), invert=invert,
                             name_col=name_col, date_col=date_col)
        ok = eligible_rows(p, f"{value_col}_pct")
        e = p.loc[ok]
        per_date = e.groupby(date_col)[name_col].nunique() if len(e) else pd.Series(dtype=int)
        usable = per_date[per_date >= int(min_names_per_date)] if len(per_date) else per_date
        rows.append({
            "burn_in_observations": int(b),
            "eligible_rows": int(len(e)),
            "eligible_row_share": (len(e) / total_rows) if total_rows else None,
            "eligible_names": int(e[name_col].nunique()) if len(e) else 0,
            "eligible_dates": int(len(usable)),
            "first_eligible_date": (str(usable.index.min()) if len(usable) else None),
            "median_names_per_eligible_date": (float(usable.median()) if len(usable) else None),
            "min_names_per_date_required": int(min_names_per_date),
            "median_history_years_at_eligibility": (
                float(e.loc[e["n_history"] == int(b), "history_years"].median())
                if (e["n_history"] == int(b)).any() else None),
            "median_history_years_all_eligible_rows": (
                float(e["history_years"].median()) if len(e) else None),
        })
    return {
        "value_col": value_col,
        "panel_rows_with_a_value": total_rows,
        "panel_dates": len(all_dates),
        "panel_names": int(base[name_col].nunique()),
        "panel_first_date": all_dates[0] if all_dates else None,
        "panel_last_date": all_dates[-1] if all_dates else None,
        "rules": PERCENTILE_RULES,
        "burn_ins": rows,
        "note": ("burn_in counts a NAME'S OWN observations, not elapsed calendar time; the two "
                 "come apart on a panel with gaps, so median_history_years is reported beside "
                 "every row share. No outcome relationship is computed here."),
    }
