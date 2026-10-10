"""How long the hot list's edge lasted, in the language S22 registered for it.

WHY THIS MODULE EXISTS
----------------------
Extension **S22** (`PREREG_s22_term_structure.md`, committed alone at `6b187dd` before
`scripts/term_structure.py` existed; results in `HANDOFF_edge_audit.md` session 18) asked what
the composite predicts as the forward window lengthens from one quarter to two years. The
answer was **CONSTANT-RATE** on the 2,531-name panel: annualized top-decile alpha essentially
flat from three months to two years.

**RESTATED 2026-10-10 ON THE CORRECTED 9,645-NAME UNIVERSE, AND THE SHAPE CHANGED CLASS TO
`INTERMEDIATE`.** The alpha is still positive and still separable at every one of the eight
horizons (alpha HAC t never below 3.02, and 3.38 at two years), and it is no longer flat: it
decays from 6.07% annualized at one quarter to 2.56% at two years. The two panels share ZERO
rebalance dates, so this moved under a universe change and a grid change at once.

That is a genuinely good result, and a good result is exactly when a product surface is most
likely to overstate. So the handoff did not leave the wording to a page: its §6 registers **one
sentence** as the only claim derivable from a measured figure with no extrapolation, naming the
horizon it was measured at, and lists the caveats "without which it may not be displayed".
`DEFENSIBLE` below is that sentence, verbatim.

WHAT IS AND IS NOT SETTLED BY IT
--------------------------------
S22 measured the **long-only top decile against the equal-weighted universe**, on the same
single in-sample panel every other published figure comes from. It is not a forward test, and a
longer forward window is not new data — the eight horizons are eight views of one sample, not
eight samples.

**THE LONG-SHORT SPREAD IS DELIBERATELY ABSENT FROM EVERY CONSTANT HERE.** It does not persist:
long-short HAC t falls 2.7167 at one quarter to 0.6846 at two years, and the handoff is explicit
that nobody may quote a long-short figure beyond about a year. The persistence lives entirely in
the long leg. Because the shipped product IS a long-only hot list, the product statistic and the
long-short research statistic diverge with horizon — and the record has been quoting them side
by side. Blending them on a page would import a decayed statistic into a claim that does not
depend on it, so `test_hold_horizon.py` fails if a long-short figure ever appears in this
module or beside this copy on a rendered page.

THE MISUSE THE HANDOFF NAMED IN ADVANCE
---------------------------------------
§7: *"It is not a finding that the book should rebalance less often, and that inference is the
most likely way this result gets misused."* `cum_alpha(H)` is the buy-and-hold return of the
cohort selected on **one** date; a quarterly-rebalanced book re-selects and compounds fresh
selections. Those are different claims and only the first was measured. `NOT_A_HOLD_RULE` ships
that distinction rather than leaving it in a research file, because the surface most able to
cause the misreading is the one that states the two-year figure.

V3'S PRECISION RULE STILL BINDS
-------------------------------
V3 measured the *score* and found the per-name result not distinguishable from chance. Nothing
here may become a per-name promise: the S22 figures are properties of the **top decile as a
group**, and the only half of the registered sentence that belongs on an individual name row is
the one that limits it — `PER_NAME`, an exact substring of `DEFENSIBLE` rather than a second
editable rewrite of it, the same one-source rule `score_confidence.py` follows.

THE VALUATION BAND IS A DIFFERENT OBJECT
----------------------------------------
`BAND_*` frames the existing bear/base/bull spread as the zone the model considers full value —
context, not a target. It is grouped in this module because it landed with the same task, but it
comes from the **valuation engine on one company's filings**, not from the backtested composite.
The two do not validate each other, `BAND_SCOPE` says so on the page, and no S22 figure may
appear in the band copy.
"""
from __future__ import annotations

# --- provenance ------------------------------------------------------------------------
SOURCE = "HANDOFF_edge_audit.md"
REGISTER = "PREREG_s22_term_structure.md"

#: RESTATED 2026-10-10 BY THE CANONICAL MOVE, AND THE VERDICT ITSELF CHANGED CLASS.
#:
#: On the 2,531-name panel S22's registered shape was **CONSTANT-RATE** (R_8 = 6.195):
#: annualized alpha essentially flat from three months to two years. Re-measured on the
#: corrected 9,645-name panel the shape is **INTERMEDIATE** (R_8 = 3.372) -- the alpha is
#: still positive at every horizon and it is no longer flat: it decays to roughly two fifths
#: of its one-quarter rate by two years.
#:
#: THE SENTENCE BELOW THEREFORE CHANGED ITS MEANING AND NOT ONLY ITS DIGITS, which is why it
#: is restated rather than having two numbers swapped inside it. "Still ahead by about 5.1%"
#: described a flat curve; "about 2.6%" describes a decaying one, and a reader who is told the
#: first about a panel that measured the second has been misled about the shape even though
#: both figures are positive.
VERDICT = "INTERMEDIATE"
VERDICT_PUBLISHED_2531_PANEL = "CONSTANT-RATE"
R8_SHAPE_STATISTIC = 3.372278505288152
R8_SHAPE_STATISTIC_PUBLISHED = 6.194976482813532

#: Horizons scored, in quarters: 63d through 504d.
HORIZON_QUARTERS = 8

#: The panel every figure here comes from — the corrected 9,645-name raw universe over 69
#: rebalance dates. The previous panel held 2,531 names, and the two share ZERO rebalance
#: dates: the grid is derived from the universe's own trading calendar, so widening the
#: universe shifts every date.
PANEL_NAMES = 9645
PANEL_DATES = 69
PANEL_NAMES_PUBLISHED = 2531
PANEL_SHARED_DATES = 0

#: Annualized top-decile alpha at the two horizons the sentence names (percent).
ALPHA_ANN_FIRST_QUARTER = 6.07
ALPHA_ANN_TWO_YEARS = 2.56
ALPHA_ANN_FIRST_QUARTER_PUBLISHED = 6.6
ALPHA_ANN_TWO_YEARS_PUBLISHED = 5.1

#: Share of top-decile spells lasting exactly one rebalance, and one-period retention.
ONE_REBALANCE_SHARE = 0.706
ONE_PERIOD_RETENTION = 0.366

#: Median per-date rank IC at 63d and at 504d — the independent route to the same finding,
#: never touching the decile machinery. Methodology only; too technical for a name row.
RANK_IC_FIRST_QUARTER = 0.0594
RANK_IC_TWO_YEARS = 0.1017
#: The published pair, kept so the restatement is legible. The CLAIM they support -- that the
#: two-year rank IC exceeds the one-quarter one -- SURVIVES on the corrected panel, and it
#: survives by a wider margin (0.0594 -> 0.1017 against 0.0336 -> 0.0655).
RANK_IC_FIRST_QUARTER_PUBLISHED = 0.0336
RANK_IC_TWO_YEARS_PUBLISHED = 0.0655

# --- the registered sentence (verbatim from SOURCE §6) -----------------------------------

#: `HANDOFF_edge_audit.md` session 18 §6 calls this "the defensible product sentence" and
#: registers it as the ONE claim derivable with no extrapolation. Do not tidy or shorten it.
#: THE SENTENCE AS THE HANDOFF REGISTERED IT, verbatim, for the 2,531-name panel. KEPT, and
#: still pinned against `HANDOFF_edge_audit.md` by test, because it is the register and a
#: product surface may not reword it.
DEFENSIBLE_REGISTERED = (
    "In the backtest, the top decile of the hot list beat the equal-weighted universe by about "
    "6.6% annualized over the next three months — and was still ahead by about 5.1% annualized "
    "two years later — even though a given name typically stays in the top decile for only one "
    "quarterly rebalance."
)

#: THE SENTENCE THE PRODUCT SHIPS, DERIVED FROM THE REGISTERED ONE BY SUBSTITUTION AND NOT
#: REWRITTEN (item 47, the canonical move).
#:
#: The register is the edge lane's file and this lane does not edit it, so the corrected
#: sentence cannot be registered here. What it CAN be is provably descended from the one that
#: was: the two published figures are replaced by the two corrected constants, and one clause
#: is appended because the SHAPE changed class (`CONSTANT-RATE` -> `INTERMEDIATE`) and "still
#: ahead by about 2.6%" inside a sentence written for a flat curve would understate what moved.
#:
#: `tests/test_hold_horizon.py` asserts the descent rather than the wording: the registered
#: sentence is verbatim in the handoff, and this one is exactly that sentence with those two
#: substitutions and that one clause. So the product copy is still not independently editable,
#: which is the property the verbatim pin existed for.
#:
#: NOT DONE, and named: r1's lane owns `HANDOFF_edge_audit.md`, so the corrected sentence is
#: not registered there. Until it is, the register's own figures are the previous panel's.
_SHAPE_CLAUSE = (", a lower rate rather than the same one — the decay is why this panel's "
                 "shape is INTERMEDIATE where the previous one measured CONSTANT-RATE")
DEFENSIBLE = (DEFENSIBLE_REGISTERED
              .replace("about 6.6% annualized",
                       "about %.2f%% annualized" % ALPHA_ANN_FIRST_QUARTER)
              .replace("about 5.1% annualized two years later",
                       "about %.2f%% annualized two years later%s"
                       % (ALPHA_ANN_TWO_YEARS, _SHAPE_CLAUSE)))

#: The half that belongs on an individual name: a limit, not a figure. An exact substring of
#: DEFENSIBLE by design, so a name row cannot state a softer version than the legend.
PER_NAME = (
    "a given name typically stays in the top decile for only one quarterly rebalance"
)

#: ITEM 22 -- WHICH BOOK THE 6.6% IS ABOUT, NAMED BEFORE ANY OTHER CAVEAT.
#:
#: `DEFENSIBLE` says "the top decile of the hot list ... versus the equal-weighted universe",
#: which is accurate and is not enough: a reader on a page that also sells the Valquo Index
#: takes "the top decile of the hot list" for the product. They are different books and
#: INDEX-BOOK measured the difference -- the served book earns +4.1209pp against an
#: equal-weighted basket of its own large-cap tier and MINUS 0.0576pp against the all-cap
#: equal-weighted universe this figure is measured against, with roughly 70% of the gap being
#: the small-cap premium a large-cap tier declines to hold.
#:
#: IT IS NOT SPLICED INTO `DEFENSIBLE`. That string is a registered research sentence quoted
#: verbatim from the handoff and pinned by `tests/test_hold_horizon.py`; rewriting it to fix a
#: product problem would silently restate a research claim. `NOT_A_HOLD_RULE` already
#: establishes the pattern -- append, never splice -- and this follows it.
#:
#: It LEADS the caveat rather than trailing it, because it is a statement about WHICH OBJECT
#: the figure describes. A trailing identity disclaimer is read after the reader has already
#: decided what they are looking at.
RESEARCH_OBJECT = (
    "the ranking across all ~2,500 companies, equal-weighted top 10% - not the Valquo Index, "
    "which holds a $10 billion large-cap tier, score-weighted, with an 8% position cap and a "
    "no-trade band"
)

#: The caveats §6 says the sentence may not be displayed without. Held as separate clauses
#: because each one is independently quoted verbatim from the handoff — a single joined string
#: would straddle the handoff's bold markers and could only be pinned loosely.
CAVEAT_CLAUSES = (
    "long-only top decile versus the equal-weighted universe",
    "gross of costs",
    "same single in-sample panel every other published figure comes from — not a forward test",
)

#: §7's warning, shipped rather than left in the research file. Opens with the handoff's own
#: sentence verbatim; the clause after the dash is the plain-language reason.
NOT_A_HOLD_RULE = (
    # THE FIRST CLAUSE IS §7's, VERBATIM, and `tests/test_hold_horizon.py` pins that it is --
    # "so the product's version cannot soften the research one". The cadence correction is
    # therefore APPENDED rather than spliced into the quote: rewriting "the list is re-ranked
    # every quarter" would have silently restated a research sentence to fix a product one.
    "It is not a finding that the book should rebalance less often — the list is re-ranked "
    "every quarter, and what was measured is how one quarter's selection went on to do, not a "
    "comparison of holding policies. "
    # THE SCOPE, which is what was missing and what made the sentence wrong in a product
    # context: that quarterly cadence is the BACKTEST's. The live list re-ranks every close.
    "That quarterly cadence is the BACKTEST's: the live Hot Stocks list is re-ranked after "
    "every market close, while the Valquo Index changes only at a quarterly rebalance. Three "
    "different clocks, and this measurement belongs to the quarterly one."
)

# --- the valuation band (NOT an S22 object — see the module docstring) --------------------

#: The reframe: a zone, not a number to trade toward.
BAND = (
    "Read the bear–base–bull spread as the zone the model considers full value — context for "
    "today's price, not a target, and not a forecast of when or whether the price gets there."
)

#: Why the band may not be read as corroborating the ranking, or the other way round.
BAND_SCOPE = (
    "This band comes from the valuation model on this company's own filings. It is a different "
    "measurement from the hot list's backtested ranking, and the two do not check each other."
)


def caveat() -> str:
    """The mandatory caveat line, assembled from the clauses §6 requires.

    Rendered as one sentence so a surface cannot ship three of four clauses: the string is
    built here, and the test asserts every clause survives into the page.
    """
    return ("This is {obj}. Measured on the corrected {n:,}-name / {d}-date panel: {c0}; "
            "{c1}; and it is the {c2}.").format(
                obj=RESEARCH_OBJECT, n=PANEL_NAMES, d=PANEL_DATES, c0=CAVEAT_CLAUSES[0],
                c1=CAVEAT_CLAUSES[1], c2=CAVEAT_CLAUSES[2])


def per_name_note() -> str:
    """The name-row form: the group/name distinction V3 requires, plus S22's tenure limit."""
    return ("The backtested edge is a property of the top decile as a group, not a promise "
            "about this name — and {p}.".format(p=PER_NAME))


def for_template() -> dict:
    """One source for the legend, the name panel and the valuation band.

    Injected site-wide next to `score_confidence` for the same reason: `index.html` is rendered
    by BOTH `web/app.py` and `saas/app_saas.py`, and this project's recurring defect is the
    second render path being forgotten.
    """
    return {
        "verdict": VERDICT,
        "defensible": DEFENSIBLE,
        "per_name": PER_NAME,
        "per_name_note": per_name_note(),
        "caveat": caveat(),
        "research_object": RESEARCH_OBJECT,
        "not_a_hold_rule": NOT_A_HOLD_RULE,
        "band": BAND,
        "band_scope": BAND_SCOPE,
        "horizon_quarters": HORIZON_QUARTERS,
        "rank_ic": {"first_quarter": RANK_IC_FIRST_QUARTER, "two_years": RANK_IC_TWO_YEARS},
        # ITEM 47: the panel size and the two alpha figures reach the template so
        # `/methodology` can state them without typing a figure of its own. The PUBLISHED
        # panel size travels too, because the correction is only legible beside what it
        # replaced -- the page says the universe widened and the headline fell.
        "panel_names": PANEL_NAMES,
        "panel_dates": PANEL_DATES,
        "panel_names_published": PANEL_NAMES_PUBLISHED,
        "panel_shared_dates": PANEL_SHARED_DATES,
        "alpha_ann": {"first_quarter": ALPHA_ANN_FIRST_QUARTER,
                      "two_years": ALPHA_ANN_TWO_YEARS},
        "verdict_published": VERDICT_PUBLISHED_2531_PANEL,
        "tenure": {"one_rebalance_share": ONE_REBALANCE_SHARE,
                   "one_period_retention": ONE_PERIOD_RETENTION},
        "source": SOURCE,
        "register": REGISTER,
    }
