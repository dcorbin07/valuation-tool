"""How old the forward track is, and how much of it was actually recorded (LA8).

WHY THIS MODULE EXISTS
----------------------
`VALQUO_LIVE_AUDIT.md` **LA8** found that every surface rendering the forward track's age was
rendering `len(series)` -- the number of rows the recorder managed to write -- under the word
"Days", beside "Alpha / yr" and "Sharpe". At the time of the audit the track was **7 trading
days old with 2 recorded rows**, and the server's own note read *"Live track is 2 trading days
old -- far too short to judge."*

That sentence is false in the flattering direction, and the direction is the point. A reader is
told the record is SHORT. The true statement is that the recorder is **missing 71% of its
rows** -- a different problem, with a different owner (ledger `PT-WRITER`, Cowork lane), and one
that a reader might act on. The single number that would have made the recording failure visible
on the surface where someone would notice it was being spent to say something else.

THREE CLOCKS, AND CONFLATING ANY TWO IS THE DEFECT
--------------------------------------------------
LA3 already separated two of them. This module adds the third and names all three, because the
whole class of bug here is one quantity standing in for another:

  * **rows** (`len(series)`) -- how many days the recorder wrote down. Correct for a **GATE**
    ("have we recorded enough to say anything?"). `index_track.MIN_LIVE_DAYS` reads this and
    must keep reading it: moving the gate onto elapsed time would let a gappy track reach the
    floor sooner, advancing the public "backtested -> live" posture on the strength of days
    nobody recorded.
  * **elapsed to the last row** (`index_track._elapsed_trading_days`) -- the window the recorded
    return actually accrued over. Correct for an **EXPONENT** (annualisation). LA3's fix.
  * **age** (this module) -- trading days from inception to **today**. Correct for a **DISPLAY**
    that claims to say how old the track is.

The third is not a restatement of the second. `_elapsed_trading_days` measures to the LAST
RECORDED ROW, so a recorder that stopped three weeks ago leaves it frozen -- the track appears
to stop ageing at the moment it stopped being written. That is the most flattering failure mode
available, and it is invisible in every other field. Age measures to today, so a dead recorder
shows up as a widening gap instead of as silence.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not touch the gate, the headline, or any contract posture sentence. Those read rows on
purpose and say so. This module supplies the AGE CLAUSE of a sentence whose posture half is
quoted verbatim around it, and `tests/test_track_age.py` fails if that posture wording moves.

THE GAPLESS CASE IS BYTE-IDENTICAL, WHICH IS WHAT MAKES IT SAFE
---------------------------------------------------------------
On a track recorded every trading day since inception, `recorded == age`, `complete` is true,
and `phrase()` returns exactly the string the old code built -- "N trading days old". So the fix
changes what is displayed only where the display was wrong. Same property LA3 relied on, and it
is pinned by test rather than asserted here.
"""
from __future__ import annotations

from typing import Optional

#: The unit every surface states. Trading days, not calendar days: `MIN_LIVE_DAYS`, the
#: freshness badge and `track_meter.gap_report` all count trading days, and a second unit on the
#: same card would be a fourth clock.
UNIT = "trading day"


def _plural(n: int, word: str = UNIT) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def describe(age: Optional[int], recorded: int) -> dict:
    """The display vocabulary for a track that is `age` trading days old with `recorded` rows.

    `age` may be None or 0 when inception is unknown or is today, in which case there is no
    honest age to show and the row count is all there is; the result then reports itself as
    complete rather than inventing a gap. `recorded > age` is likewise treated as complete --
    it means the recorder wrote a row on a day the calendar does not call a trading day, which
    is a data question, not a coverage claim, and this module will not report a negative gap.
    """
    recorded = int(recorded or 0)
    known = age is not None and int(age) > 0
    age_n = int(age) if known else recorded
    complete = (not known) or recorded >= age_n
    missing = 0 if complete else age_n - recorded

    if complete:
        return {
            "age": age_n,
            "recorded": recorded,
            "complete": True,
            # `missing` is computed once, above, and read in both branches. A second literal
            # here would be a place for the clamp to stop applying without any test noticing.
            "missing": missing,
            # Byte-identical to what the old code built. See the module docstring.
            "phrase": f"{_plural(age_n)} old",
            "label": f"day {age_n}",
            "short": f"{age_n}d",
            "metric_note": "",
        }
    return {
        "age": age_n,
        "recorded": recorded,
        "complete": False,
        "missing": missing,
        # "with only N of those days recorded" -- "only" is doing honest work: the reader is
        # being told the number is smaller than the one before it, which is the whole finding.
        "phrase": f"{_plural(age_n)} old, with only {recorded} of those days recorded",
        "label": f"day {age_n} · {recorded} recorded",
        "short": f"{age_n}d · {recorded} rec",
        "metric_note": f"{recorded} of {age_n} recorded",
    }
