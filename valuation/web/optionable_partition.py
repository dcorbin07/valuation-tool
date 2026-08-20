"""The optionable partition, as a REPORTED DIAGNOSTIC — which is all `P1S0` left it as.  [MB11]

WHAT THIS IS
------------
About a quarter of the names in this project's research panel have listed options. The live
hot list is drawn largely from that quarter, because options need liquidity and liquidity comes
with size. So "how has the model's own ranking behaved on the part of the universe the product
actually occupies?" is a question about the product, not about a trading idea — and it has been
measured.

It came back with a shape nobody predicted: **the optionable subset did WORSE over 2016-2020
and BETTER over 2021-2025, at every one of the three horizons tested.** That is a description
of where the product's universe has sat. It is not a rule, and this module exists to make sure
it is never rendered as one.

WHY IT MAY BE REPORTED AND MAY NOT BE USED
------------------------------------------
`P1S0` closed the whole options-expression family on a both-halves failure. `P1S0-CONTROL` then
asked the obvious follow-up — was the dead early half a weak PERIOD or a weaker UNIVERSE? — and
returned **NULL against its own pre-committed rule**, because the two legs disagreed. Its own
write-up says the two effects *interact and its gate cannot separate them*.

So there are three separate reasons this carries no forecast, and all three are measured:

1. **THE ATTRIBUTION FAILED.** The registered rule was: both legs clear -> UNIVERSE, both fail
   -> PERIOD, anything else -> NULL. It returned NULL. Nobody knows which it was.

2. **THE FULL PANEL DID NOT SORT EITHER IN THAT WINDOW.** Over 2016-2020 the whole 2,531-name
   panel ran its deciles BACKWARDS at all three horizons (monotonicity positive: +0.115, +0.152,
   +0.248). So the early weakness is not a fact about options-listed companies; it is at least
   partly a fact about those five years, for everything.

3. **IT REVERSES.** A description that changes sign between the two halves of its own sample is
   the last thing anyone should extrapolate from. That reversal is the single most important
   feature of the table below and the copy leads with it.

WHY THE FIGURES ARE DIFFERENCES HERE AND RATIOS ON THE DIP SURFACE
------------------------------------------------------------------
`MA28-CARD`'s rule — quote the ratio and both rates, never the difference — governs a RATE: the
probability of an event, where the base rate moves and an absolute gap moves with it. These are
not rates. They are annualised alpha, a difference of two returns, and a "ratio of alphas" is
not a quantity anyone can interpret (both sides cross zero — the optionable subset's own H=252
early figure is NEGATIVE, which makes a ratio meaningless rather than merely awkward). So both
sides are stated and the gap is stated, which is the ratio rule's actual purpose: never publish
one number that hides the two it came from.

WHAT MAY NEVER BE SAID
----------------------
`BANNED` is asserted against the RENDERED payload, not against this file — `dip_posture`'s
design, and V4's lesson that rendering is where copy leaks. The families are FORECAST,
RECOMMENDATION and ATTRIBUTION. Note what is deliberately NOT banned: ordinary past-tense
description. "The optionable subset did better late" is what was measured and must stay
sayable, or the surface cannot report its own diagnostic. What is banned is the tense change —
"will", "expect", "going forward" — and the causal claim `P1S0-CONTROL` explicitly could not
make.

SOURCED, NOT INVENTED
---------------------
Every figure is a literal here, transcribed once from `data/free_analysis/P1S0_GATE.json` (the
optionable arm) and `P1S0_CONTROL.json` (the full-panel arm). It cannot be derived at render
time: `data/` is gitignored and never ships with a deploy, which is the same constraint
`tidemark_surface` documents. The page that renders this is static by construction and takes no
arguments, and it stays that way.

The six gaps are DERIVED from the two sides rather than transcribed a third time, so a
transcription slip in one side cannot silently agree with a hand-typed gap — `accounting_risk`'s
rule that only the raw counts are pinned and every derived figure is computed.
"""
from __future__ import annotations

# --------------------------------------------------------------------------------------- #
# PROVENANCE
# --------------------------------------------------------------------------------------- #

REGISTER = "PREREG_p1s0control_period_or_universe.md"
GATE_REGISTER = "PREREG_p1s0_optionable_gate.md"
ARTIFACTS = ("data/free_analysis/P1S0_GATE.json", "data/free_analysis/P1S0_CONTROL.json")

#: The partition. `modes.pit_liquid` — names carrying a point-in-time liquid option chain.
N_OPTIONABLE_NAMES = 619
N_PANEL_NAMES = 2531

#: The two windows, from the H=63 arm (the power anchor). The other two horizons use slightly
#: different windows because each embargoes its own boundary; the years are stated loosely on
#: the surface for that reason, and precisely here.
EARLY_WINDOW = ("2016-01-20", "2020-10-20")
LATE_WINDOW = ("2021-04-22", "2025-10-27")

#: Annualised top-decile alpha, in percent, by arm and window. TRANSCRIBED — the two sides —
#: and every gap below is DERIVED from them.
#:   full  = the whole 2,531-name panel scored over the SAME dates (P1S0_CONTROL)
#:   opt   = the point-in-time optionable subset (P1S0_GATE, modes.pit_liquid)
HORIZONS = (
    {"days": 63, "label": "next quarter",
     "full_early": 4.284968705583039, "opt_early": 2.817664383006252,
     "full_late": 14.60410952103895, "opt_late": 24.307846868585395},
    {"days": 252, "label": "next year",
     "full_early": 6.042706550726021, "opt_early": -0.08168588889261308,
     "full_late": 11.854230233961291, "opt_late": 22.781390621069983},
    {"days": 504, "label": "next two years",
     "full_early": 2.0437022401810473, "opt_early": 0.5163009659756745,
     "full_late": 9.733290973192038, "opt_late": 11.288231624406292},
)


# --------------------------------------------------------------------------------------- #
# THE COPY
# --------------------------------------------------------------------------------------- #

HEADING = "The part of the universe this product actually occupies"

#: The callout's own heading. In the module because the template may hold no copy of
#: its own -- and deliberately NOT a repeat of `NOT_A_FORECAST`'s first sentence, which
#: the first cut duplicated word for word directly above it.
CALLOUT_HEADING = "Why this is reported and why it is not used"

LEDE = ("Roughly a quarter of the research panel has listed options, and the hot list is drawn "
        "largely from that quarter. Here is how the model's own ranking behaved on it — "
        "reported because it is a description of the product's own universe, and reported with "
        "the reason it cannot be used.")

WHAT_IT_IS = (
    "The panel holds {:,} companies. {:,} of them carried a liquid, point-in-time options chain, "
    "and those are the names that tend to be large and liquid enough to reach the hot list. "
    "The model's top-decile ranking was scored separately on that subset and on the whole "
    "panel over the same dates, so the only thing that differs between the two columns is "
    "which companies are in them.").format(N_PANEL_NAMES, N_OPTIONABLE_NAMES)

#: The finding, and the copy leads with the reversal rather than with either half.
WHAT_WAS_MEASURED = (
    "It reverses. Over roughly 2016 to 2020 the options-listed subset did WORSE than the full "
    "panel at all three horizons. Over roughly 2021 to 2025 it did BETTER, at all three. A "
    "description that changes sign between the two halves of its own sample is the last thing "
    "anyone should carry forward, and that is the single most important line in the table.")

#: The three separate reasons this is not a forecast. All three are measured, not asserted.
NOT_A_FORECAST = (
    "This describes the past and carries no forecast. Three separate reasons, each of them "
    "measured rather than argued. The registered test that was supposed to attribute the early "
    "weakness — to the period, or to these companies — returned NO ANSWER: its two legs "
    "disagreed and the rule written down beforehand calls that a null. Over the same early "
    "window the FULL panel did not sort either, its deciles running backwards at all three "
    "horizons, so the weakness is at least partly a fact about those five years and not about "
    "options-listed companies. And the whole family of ideas this was measured for was closed "
    "on the evidence and stays closed; nothing here reopens it.")

#: The one sentence a reader is most likely to construct for themselves, refused explicitly.
CANNOT_SEPARATE = (
    "The honest summary is that the weak early half was a weak PERIOD and a weaker UNIVERSE at "
    "once, and the test could not separate them. Anyone quoting one of those two without the "
    "other is quoting something this project did not measure.")

SOURCE_NOTE = (
    "Top-decile alpha against an equal-weighted benchmark, annualised, gross of costs, on one "
    "18-year point-in-time panel. Each horizon embargoes its own half boundary, so the two "
    "windows shift slightly between rows; the years above are stated loosely for that reason.")

# --------------------------------------------------------------------------------------- #
# THE POSTURE LINE, ENFORCED
# --------------------------------------------------------------------------------------- #

#: Phrasings that may not appear on this surface, EVER. Three families:
#:
#:   FORECAST — the tense change. "will outperform", "expect", "going forward". This is the
#:     whole point of MB11: the measurement is a description of a window that has ended.
#:
#:   RECOMMENDATION — advice, which this product does not give anywhere.
#:
#:   ATTRIBUTION — "because they are optionable", "options-listed names are better". This is
#:     the causal claim `P1S0-CONTROL` was built to test and explicitly could not make. It is
#:     the most tempting family here, because a reader who sees the late column will construct
#:     it unaided, which is why `CANNOT_SEPARATE` says it out loud and then refuses it.
#:
#: DELIBERATELY NOT BANNED: ordinary past-tense description. "did better", "did worse",
#: "outperformed" in the past tense are what was measured and must stay sayable, or the
#: surface cannot report its own diagnostic. A ban that forbids stating the finding would be a
#: guard that defeats the item it guards.
BANNED = (
    # FORECAST
    "will outperform", "will beat", "will do better", "should outperform", "expect it to",
    "expected to outperform", "going forward", "from here", "in future", "in the future",
    "likely to outperform", "predicts", "is a signal", "as a signal", "tradable", "tradeable",
    "an edge", "our edge", "exploit",
    # RECOMMENDATION
    "buy", "sell", "you should", "we recommend", "worth owning", "avoid these",
    # ATTRIBUTION — the claim the register could not make
    "because they are optionable", "because it is optionable", "options-listed names are "
    "better", "optionable names are better", "having options makes", "the reason is options",
)


def violations(text: str) -> list:
    """Which banned phrasings appear in `text`. Case-insensitive substring, `dip_posture`'s
    rule — substring so a hyphenation or a suffix cannot walk around it.

    SCOPE, AND THE FIRST RUN GOT THIS WRONG. `dip_posture` asserts its BANNED tuple against
    the whole rendered page because it OWNS that page. This section is one of nine on `/work`,
    and run against the whole page the tuple fired on `tradable`, `buy` and `sell` in
    sentences belonging to other items — a false positive on innocent pre-existing copy, which
    is `MA28-CARD-UI`'s defect and the same one `MB38`'s boast check hit on the word
    "provenance". The rule is asserted against THIS SECTION of the rendered HTML: still the
    rendered payload, because rendering is where copy leaks, but scoped to the copy this item
    owns. Policing another item's prose is not this guard's job and would be switched off
    inside a week.
    """
    low = (text or "").lower()
    return [b for b in BANNED if b in low]


# --------------------------------------------------------------------------------------- #
# THE PAYLOAD
# --------------------------------------------------------------------------------------- #

def rows() -> list:
    """One row per horizon, with the gap DERIVED rather than transcribed a third time."""
    out = []
    for h in HORIZONS:
        out.append({
            "days": h["days"],
            "label": h["label"],
            "full_early": h["full_early"],
            "opt_early": h["opt_early"],
            "full_late": h["full_late"],
            "opt_late": h["opt_late"],
            # Positive = the FULL panel did better. Negative = the optionable subset did.
            "gap_early": h["full_early"] - h["opt_early"],
            "gap_late": h["full_late"] - h["opt_late"],
        })
    return out


def payload() -> dict:
    """Everything the section renders. Static: no argument, no store, no clock."""
    return {
        "heading": HEADING,
        "callout_heading": CALLOUT_HEADING,
        "lede": LEDE,
        "what_it_is": WHAT_IT_IS,
        "what_was_measured": WHAT_WAS_MEASURED,
        "not_a_forecast": NOT_A_FORECAST,
        "cannot_separate": CANNOT_SEPARATE,
        "source_note": SOURCE_NOTE,
        "register": REGISTER,
        "rows": rows(),
        "n_optionable": N_OPTIONABLE_NAMES,
        "n_panel": N_PANEL_NAMES,
    }
