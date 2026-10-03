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
  * **THAT REASONING LED TO A REFERENCE `R7` LATER REJECTED, and item 24 retired it.** This
    section used to read: *"the live book runs behind the term-structure gate ... the right
    reference for a gated live book is the gated late-half number: +12.88%."* The filter it
    names was rejected on corrected data -- its +8.89pp replication was a `B1` price-basis
    artefact, and split-clean it makes its own out-of-sample book WORSE at -1.12pp against a
    +5.00pp bar -- so +12.88% is the expectancy of a book nobody runs. It is kept in
    `retired_references` with that verdict attached rather than deleted.
  * **THE REFERENCE IS NOW THE CORRECTED ALERT BOOK ITSELF: +3.2702%/trade** over 3,870 trades
    (`U1-SPLIT`), with the control beside it -- five-seed random entry on the same names earns
    **+8.3342%**, so the alert's day-selection subtracts **5.0640pp** at a paired name-year sign
    test of z -4.9612. **The honest reference carries a negative result, which is why it is the
    right one:** comparing the live book against a rejected filter asks whether it keeps up with
    something we do not run, where the question that matters is whether the alert adds anything.

Both references are therefore reported side by side with what each includes, and
`primary_reference` names the one that actually matches how the live book trades. Getting this
wrong in either direction is easy and is the reason it is spelled out rather than assumed.

--------------------------------------------------------------------------------------------
WHERE OUTCOMES COME FROM.

**CORRECTED BY ITEM 24, AND THE OLD TEXT IS WHY THE RECORD DROPPED ITS LOSERS.** It read:
*"an external scheduled job (Cowork) writes exits back via `options_tracker.record_outcome`.
Until it does, alerts sit open - and a book of open alerts with no closes is the honest state."*
That job no longer exists. So "until it does" was never going to arrive, the only in-repo caller
of `record_outcome` is `paper_track` (which closes what the PAPER BROKER bought), and an alert
the broker declined -- usually on the $1,000 sizing veto, a fact about this account's size -- was
unscoreable forever.

**THE CENSORING WAS THEREFORE ONE-SIDED AND CORRELATED WITH PREMIUM.** Affordability excludes
the EXPENSIVE contracts, and measured on the live service 2026-10-03 the two clearest cases were
ELV alert 14 (420C, entry 27.80, last 7.00, **-75%**) and HCA alert 7 (430C, entry 22.40, last
8.60, **-62%**) -- both well past their own pre-registered -50% stop, neither held, neither
scored. `MA36`'s defect one layer up, with affordability in place of expiry.

**NOW:** `options_selfscore` scores each alert against ITS OWN logged exit policy on daily
bid-side marks, through the one shared `options_tracker.exit_decision` rule that `paper_track`
also delegates to. The paper book stays a separate object answering a different question -- what
a $1,000-budget account actually got, fills and sizing included -- and is not touched.
"""
from __future__ import annotations

from typing import Optional

from . import options_confidence as C
from .options_tracker import (MIN_CLOSED_PER_BUCKET, _stats, epoch_census,  # noqa: F401
                              epoch_filter, EPOCH_ALL)
# `EPOCH_ALL` is re-exported deliberately: `paper_report`'s own docstring tells a caller to pass
# it, and making them reach into a second module for the sentinel is how two spellings start.

# The reference the live book is actually comparable to: late-half, behind the term gate.
# ITEM 24 -- RETIRED AS A REFERENCE, KEPT AS A RECORD.
#
# +12.88% is the term-structure filter's late-half expectancy from phase 3b, n=307, and
# `primary_reference` named it *"the only reference that matches how the live book trades"*.
# **`R7` REJECTED THAT FILTER ON CORRECTED DATA.** Its +8.89pp out-of-sample replication was an
# artefact of the `B1` price basis; re-run split-clean, the filter makes its own out-of-sample
# book WORSE -- a gain of **-1.12pp against a +5.00pp bar** -- and is no longer tail-enriching.
# So the live book is not gated by a filter the project kept, and this number is the expectancy
# of a book nobody runs.
#
# IT IS NOT DELETED. It is what the surface used to claim, a reader who saw it needs to be able
# to find it, and `scream_log`'s principle -- nothing removed, everything dated -- applies to a
# reference as much as to a row. It moves to `retired_references` with its verdict attached.
GATED_LATE_HALF_EXPECTANCY = 0.1288      # phase 3b, n=307 -- REJECTED by R7, see above

# The corrected alert book's own measured expectancy, which is what the live book IS.
# `U1-SPLIT` re-derived R2 on a split-clean basis: the alert book earns +3.2702%/trade over
# 3,870 trades, and the five-seed random-entry control earns +8.3342%, a gap of **-5.0640pp**
# at a paired name-year sign test of z -4.9612 (p 7e-07).
#
# **SO THE HONEST REFERENCE CARRIES A NEGATIVE RESULT, AND THAT IS WHY IT IS THE RIGHT ONE.**
# A surface that compares the live book against +12.88% is asking "is it keeping up with a
# filter we rejected"; the question that matters is "does the alert's day-selection add
# anything", and the measured answer is that it subtracts 5.06pp against random entry.
CORRECTED_ALERT_BOOK_EXPECTANCY = 0.032702          # U1-SPLIT, n=3,870
CORRECTED_RANDOM_ENTRY_EXPECTANCY = 0.083342        # U1-SPLIT, five seeds, n=29,654
R2_GAP_PP = -5.0640
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
        gap = live["expectancy_pct"] - CORRECTED_ALERT_BOOK_EXPECTANCY

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
        "headline_expectancy": (CORRECTED_ALERT_BOOK_EXPECTANCY if thin
                                else live["expectancy_pct"]),
        "headline_source": ("backtest, corrected basis (live sample too thin)" if thin
                            else "live"),
        "primary_reference": {
            "value": CORRECTED_ALERT_BOOK_EXPECTANCY, "n": 3870,
            "what": "the corrected alert book's own measured expectancy (U1-SPLIT, "
                    "split-clean) - what this strategy actually earned per trade on 3,870 "
                    "simulated trades",
            "and_the_part_that_matters": (
                "random entry on the same names earned +8.3342%%, so the alert's "
                "day-selection subtracts %.4fpp (paired name-year sign test z -4.9612, "
                "p 7e-07). The live book is not expected to beat this reference - R2 is why "
                "`O11` governs and why nothing here licenses a trade." % abs(R2_GAP_PP)),
        },
        "other_references": [
            {"value": CORRECTED_RANDOM_ENTRY_EXPECTANCY, "n": 29654,
             "what": "five-seed random entry on the same universe - the control the alert "
                     "loses to, and the only comparison that isolates day-selection"},
            {"value": FULL_SAMPLE_EXPECTANCY, "n": 1540,
             "what": "full sample 2016-2025 on the VOID pre-B1 price basis - kept for "
                     "continuity with older write-ups, not a comparison for anything"},
        ],
        # ITEM 24 -- WHAT THIS SURFACE USED TO CLAIM, with the verdict that retired it.
        "retired_references": [
            {"value": GATED_LATE_HALF_EXPECTANCY, "n": 307,
             "was": "primary_reference, described as `the only reference that matches how the "
                    "live book trades`",
             "retired_by": "R7",
             "why": ("the term-structure filter it describes was REJECTED on corrected data: "
                     "its +8.89pp out-of-sample replication was an artefact of the B1 price "
                     "basis, and re-run split-clean the filter makes its own out-of-sample "
                     "book WORSE, a gain of -1.12pp against a +5.00pp bar")},
            {"value": UNGATED_LATE_HALF_EXPECTANCY, "n": 770,
             "was": "other_references",
             "retired_by": "U1-SPLIT",
             "why": ("a pre-B1 figure: option chains are as-traded while the bars are "
                     "split-adjusted, and nothing in the options lane consulted the split "
                     "table, so one GE reverse split booked a +31,921%% trade against a true "
                     "value of zero")},
        ],
        "expectancy_gap_vs_reference": gap,
        "hit_rate_reference": C.HIT_RATE,
        # ITEM 24 -- THE CAVEAT CREDITED A JOB THAT NO LONGER EXISTS.
        #
        # It read *"Outcomes are written back by the external Robinhood job, so open alerts
        # outnumbering closed ones early on is expected, not a fault."* Both halves were wrong by
        # 2026-10-03. The job is gone, so open alerts outnumbering closed ones was NOT a
        # transient of a young book -- it was the permanent state of a record that could not
        # score itself, and it WAS a fault. Measured: 26 open against 7 closed, with ELV alert
        # 14 at -75% and HCA alert 7 at -62%, both past their own -50% stop and neither scored.
        "caveat": ("Expectancy, not win rate: the backtested hit rate is 37%. Alerts are now "
                   "scored against their OWN exit rules on daily bid-side marks "
                   "(`/admin/score-alerts`), independently of whether the paper broker bought "
                   "the contract - so an alert the $1,000 budget declined is still scored. "
                   "Alerts logged from a descriptor with no option chain are counted apart as "
                   "`no_contract`: they have nothing to mark and no date on which they could "
                   "mature, so they are neither open nor closed."),
        "outcome_source": ("self-scored from the alert's own logged exit policy. The external "
                           "Robinhood job this record used to depend on no longer exists, and "
                           "its absence was not visible as an absence - it looked like a young "
                           "book with more open than closed."),
    }
