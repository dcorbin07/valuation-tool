"""
The forward paper book — the only out-of-sample test the options edge has left.

--------------------------------------------------------------------------------------------
WHY THIS MATTERS MORE THAN ANYTHING ELSE IN THE OPTIONS TRACK.

Every number the single-leg engine has ever produced comes from ONE 2016-2025 ThetaData panel of
55 large caps. It has been split in half, cost-charged at the touch, gated, and filtered, and it
survived all of it - but survival on a panel that has been looked at this many times is weak
evidence compared to a single day of data nobody has seen. This book is that data. It starts
empty, accumulates one alert at a time, and will take a year or more to say anything.

So the reporting rule here is deliberately conservative, and it is the SAME rule the stock index
uses: **the backtested expectancy stays the headline until the live sample is meaningful.** The
live figure is shown from day one - hiding it would be worse - but labelled "live since <date>,
thin" and explicitly marked not-yet-comparable until it clears `options_tracker`'s 30-closed-trade
floor. Below that floor a single contract that triples decides the sign of the statistic.

--------------------------------------------------------------------------------------------
WHAT "COMPARABLE" MEANS, AND THE TRAP IN COMPARING AT ALL.

The natural comparison - live expectancy vs the +10.4% backtest headline - is the WRONG one, and
would flatter or damn the live book for the wrong reason:

  * The headline is a FULL-SAMPLE figure dominated by 2016-2020 (+16.4% early, +4.4% late). The
    live book can only ever be compared against the recent regime.
  * The live book runs behind the term-structure gate, which the backtest headline does not. The
    right reference for a gated live book is the gated late-half number: **+12.88%**.

Both references are therefore reported side by side with what each includes, and
`primary_reference` names the one that actually matches how the live book trades. Getting this
wrong in either direction is easy and is the reason it is spelled out rather than assumed.

--------------------------------------------------------------------------------------------
WHERE OUTCOMES COME FROM.

This app writes the alert and its contract. Real fills and marks live behind the Robinhood
connector, which the web app cannot reach, so an external scheduled job (Cowork) writes exits
back via `options_tracker.record_outcome`. Until it does, alerts sit open - and a book of open
alerts with no closes is the honest state, reported as such rather than as a zero.
"""
from __future__ import annotations

from typing import Optional

from . import options_confidence as C
from .options_tracker import (MIN_CLOSED_PER_BUCKET, _stats, epoch_census,  # noqa: F401
                              epoch_filter, EPOCH_ALL)
# `EPOCH_ALL` is re-exported deliberately: `paper_report`'s own docstring tells a caller to pass
# it, and making them reach into a second module for the sentinel is how two spellings start.

# The reference the live book is actually comparable to: late-half, behind the term gate.
GATED_LATE_HALF_EXPECTANCY = 0.1288      # phase 3b, n=307
UNGATED_LATE_HALF_EXPECTANCY = C.LATE_HALF_EXPECTANCY
FULL_SAMPLE_EXPECTANCY = C.FULL_SAMPLE_EXPECTANCY


def _first_ts(rows) -> Optional[str]:
    ts = [str(r.get("alert_ts")) for r in rows if r.get("alert_ts")]
    return min(ts) if ts else None


def paper_report(store, epoch=None) -> dict:
    """Live realized expectancy against the reference it is genuinely comparable to.

    AUDIT MA37 — SCOPED TO ONE ERA, defaulting to the current one. This read every row in the
    table, so after the 2026-08-13 reset both the expectancy AND `live_since` (a bare
    `min(alert_ts)`) described a blend of the live record and a record the project had formally
    retired for predating the corrected alert stack. `live since <date>` naming a date from the
    archived era is the more misleading half: it makes the live book look older than it is.
    Pass `EPOCH_ALL` for the blend; `epochs` reports every era's row count regardless.
    """
    clause, args, ep = epoch_filter(store, epoch)
    with store._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts WHERE 1=1" + clause, args)
        keys = [d[0] for d in cur.description]
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]

    closed = [r for r in rows if str(r.get("status")) == "closed"]
    open_rows = [r for r in rows if str(r.get("status")) != "closed"]
    live = _stats(closed)
    n = live["n_closed"]
    since = _first_ts(rows)

    thin = n < MIN_CLOSED_PER_BUCKET
    if not rows:
        label = "no live alerts logged yet"
    elif thin:
        label = (f"live since {since}, thin ({n} closed of {len(rows)} logged) - "
                 f"not yet comparable, needs {MIN_CLOSED_PER_BUCKET}")
    else:
        label = f"live since {since} ({n} closed)"

    gap = None
    if not thin and live["expectancy_pct"] is not None:
        gap = live["expectancy_pct"] - GATED_LATE_HALF_EXPECTANCY

    return {
        "label": label,
        "live_since": since,
        "n_logged": len(rows),
        "n_open": len(open_rows),
        "n_closed": n,
        "thin": thin,
        "min_required": MIN_CLOSED_PER_BUCKET,
        "live": live,
        # AUDIT MA37 — which era every number above was computed on, and what else exists.
        # The archived record is EXCLUDED, never deleted and never invisible.
        "record_epoch": ep,
        "epochs": epoch_census(store),
        # The headline stays backtested until the live sample is meaningful - same rule as the
        # stock index. `headline_source` says which is being quoted rather than leaving a reader
        # to guess whether a number is measured or expected.
        "headline_expectancy": (GATED_LATE_HALF_EXPECTANCY if thin else live["expectancy_pct"]),
        "headline_source": "backtest (live sample too thin)" if thin else "live",
        "primary_reference": {
            "value": GATED_LATE_HALF_EXPECTANCY, "n": 307,
            "what": "late half (2021-2025) behind the term-structure gate - the only reference "
                    "that matches how the live book trades",
        },
        "other_references": [
            {"value": UNGATED_LATE_HALF_EXPECTANCY, "n": 770,
             "what": "late half, NO term gate - what the live book would have done unfiltered"},
            {"value": FULL_SAMPLE_EXPECTANCY, "n": 1540,
             "what": "full sample 2016-2025 - dominated by the early period, NOT a fair "
                     "comparison for a book trading today"},
        ],
        "expectancy_gap_vs_reference": gap,
        "hit_rate_reference": C.HIT_RATE,
        "caveat": ("Expectancy, not win rate: the backtested hit rate is 37%. Outcomes are "
                   "written back by the external Robinhood job, so open alerts outnumbering "
                   "closed ones early on is expected, not a fault."),
    }
