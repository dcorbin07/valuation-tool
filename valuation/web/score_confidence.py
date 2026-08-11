"""The hot score's confidence language, as V3's noise calibration left it.

WHY THIS MODULE EXISTS
----------------------
Extension **V3** (`PREREG_v3_score_calibration.md`, committed blind at `251c989`; results in
`HANDOFF_extensions_v3.md`) pointed a permutation null at the *product's* score rather than at
its returns, and the pre-registered primary statistic **failed**:

    composite at rank 10, latest cross-section — real 1.0909 against a noise p95 of 1.1117,
    empirical p 0.116. VERDICT: NOT DISTINGUISHABLE. Holds on 45 of 69 dates, against a
    pre-registered generality gate of 42.

In plain terms: a reader told that the #10 name "scores 97" is being given a number that
roughly **one in nine chance-assembled universes reaches at that rank**. The pre-registration
accepted in writing, before the run, that this outcome would require the product's confidence
language to weaken. This module is that weakening.

WHAT IS AND IS NOT SETTLED BY IT
--------------------------------
V3 measured the **cross-sectional score**, not forward returns, and its handoff is explicit
that the two are different objects: *"A composite can rank names in an order that is
indistinguishable from chance at a given rank and still have a real top-minus-bottom return
spread."* So nothing here touches the edge research — not the long-short HAC t of 2.620
against its 2.28 floor, not R1's factor alpha, not the top-decile alpha the backtest reports.

**Do not attach these sentences to a backtested RETURN claim.** The recency caveat below
(21 of 69 dates) is a property of the top decile's *score* versus a chance-assembled book. A
return claim carries its own evidence and its own caveats, and merging the two would understate
the edge research as surely as the reverse would oversell the score.

THE WORDING IS QUOTED, NOT PARAPHRASED
--------------------------------------
Every sentence below appears verbatim in `HANDOFF_extensions_v3.md` and is pinned there by
`tests/test_score_confidence.py`, which normalises the markdown and fails if either side is
reworded. That is deliberate: the handoff's wording was written to survive scrutiny, and a
product surface that "tidies" a calibrated sentence is how a hedge quietly becomes a claim.

ONE SOURCE, TWO CONSUMERS
-------------------------
The persistent legend (server-rendered) and the per-name "why this score" panel (rendered by
`static/app.js`) both read these constants — the legend from the Jinja context processor in
`web/app.py`, the panel from the JSON blob that same template injects. `PER_NAME` is an exact
substring of `DEFENSIBLE` rather than a second, shorter rewrite of it, so the short form on a
name row cannot drift away from the long form in the legend. That is the same rule the
vs-SPY fix landed for outbound figures: one authority, no second computation of the claim.
"""
from __future__ import annotations

# --- provenance ------------------------------------------------------------------------
SOURCE = "HANDOFF_extensions_v3.md"
REGISTER = "PREREG_v3_score_calibration.md"
VERDICT = "NOT DISTINGUISHABLE"
PRIMARY_RANK = 10

#: The per-name verdict holds on 45 of 69 rebalance dates (gate: 42). The group-level result
#: holds on only 21 of 69 — which is why it may never be stated as a standing property.
PER_NAME_DATES = (45, 69)
GROUP_DATES = (21, 69)

# --- the calibrated sentences (verbatim from SOURCE) ------------------------------------

#: The legend sentence. `HANDOFF_extensions_v3.md` labels this "the defensible sentence" and
#: builds the robustness count into it, so the claim and its limit travel together.
DEFENSIBLE = (
    "On recent cross-sections the top decile as a group scores better than a chance-assembled "
    "book. Where an individual name sits inside that decile is not distinguishable from "
    "chance — and that second half holds on 45 of 69 dates tested."
)

#: The half that belongs on an individual name. An exact substring of DEFENSIBLE by design.
PER_NAME = (
    "Where an individual name sits inside that decile is not distinguishable from chance"
)

#: Finding 3 — the only V3 result pointing at a fixable defect rather than at a limit of what
#: a cross-section can support (real top decile present-weight 0.94798; 9 of 500 noise draws
#: this thin, empirical p 0.018).
THIN_DATA = (
    "A high score can partly reflect missing data: names near the top are scored on less "
    "information than the average name, more so than chance would produce."
)

#: What may no longer be said, per the handoff's "PLAIN SENTENCES FOR THE PRODUCT".
NO_LONGER_SAYABLE = (
    "that a specific rank, or the gap between #3 and #12, means anything"
)


def group_caveat() -> str:
    """The recency caveat that must accompany any top-decile GROUP claim.

    Stated as a bare count of dates, never as a rate: 21 of 69 overlapping cross-sections of
    largely the same names are nowhere near 21 independent draws, and V3's handoff refuses to
    convert such a count into a significance statement for exactly the reason session 9
    established — 16 co-moving countries proved worth 2 to 4 independent draws, and a bar
    carrying a claimed 3.84% measured out at 28.7%.
    """
    hit, total = GROUP_DATES
    return (f"The group-level half holds on {hit} of {total} dates tested — it is a property "
            f"of recent cross-sections, not a standing one.")


def for_template() -> dict:
    """Everything a surface needs to state the score's precision honestly.

    Injected site-wide by the context processor so a page cannot render the score while
    forgetting the calibration, and so `app.js` reads the same strings the legend does.
    """
    return {
        "verdict": VERDICT,
        "primary_rank": PRIMARY_RANK,
        "defensible": DEFENSIBLE,
        "per_name": PER_NAME,
        "thin_data": THIN_DATA,
        "group_caveat": group_caveat(),
        "no_longer_sayable": NO_LONGER_SAYABLE,
        "per_name_dates": {"held": PER_NAME_DATES[0], "of": PER_NAME_DATES[1]},
        "group_dates": {"held": GROUP_DATES[0], "of": GROUP_DATES[1]},
        "source": SOURCE,
        "register": REGISTER,
    }
