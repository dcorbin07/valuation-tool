"""How long the hot list's edge lasted, in the language S22 registered for it.

WHY THIS MODULE EXISTS
----------------------
Extension **S22** (`PREREG_s22_term_structure.md`, committed alone at `6b187dd` before
`scripts/term_structure.py` existed; results in `HANDOFF_edge_audit.md` session 18) asked what
the composite predicts as the forward window lengthens from one quarter to two years. The
answer was **CONSTANT-RATE**: annualized top-decile alpha is essentially flat from three months
to two years, and the alpha is well measured at every horizon (alpha HAC t never below 3.16,
and 3.83 at two years).

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
VERDICT = "CONSTANT-RATE"

#: Horizons scored, in quarters: 63d through 504d.
HORIZON_QUARTERS = 8

#: The panel every figure here comes from — corrected 2,531 names / 69 rebalance dates.
PANEL_NAMES = 2531
PANEL_DATES = 69

#: Annualized top-decile alpha at the two horizons the sentence names (percent).
ALPHA_ANN_FIRST_QUARTER = 6.6
ALPHA_ANN_TWO_YEARS = 5.1

#: Share of top-decile spells lasting exactly one rebalance, and one-period retention.
ONE_REBALANCE_SHARE = 0.706
ONE_PERIOD_RETENTION = 0.366

#: Median per-date rank IC at 63d and at 504d — the independent route to the same finding,
#: never touching the decile machinery. Methodology only; too technical for a name row.
RANK_IC_FIRST_QUARTER = 0.0336
RANK_IC_TWO_YEARS = 0.0655

# --- the registered sentence (verbatim from SOURCE §6) -----------------------------------

#: `HANDOFF_edge_audit.md` session 18 §6 calls this "the defensible product sentence" and
#: registers it as the ONE claim derivable with no extrapolation. Do not tidy or shorten it.
DEFENSIBLE = (
    "In the backtest, the top decile of the hot list beat the equal-weighted universe by about "
    "6.6% annualized over the next three months — and was still ahead by about 5.1% annualized "
    "two years later — even though a given name typically stays in the top decile for only one "
    "quarterly rebalance."
)

#: The half that belongs on an individual name: a limit, not a figure. An exact substring of
#: DEFENSIBLE by design, so a name row cannot state a softer version than the legend.
PER_NAME = (
    "a given name typically stays in the top decile for only one quarterly rebalance"
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
    "It is not a finding that the book should rebalance less often — the list is re-ranked "
    "every quarter, and what was measured is how one quarter's selection went on to do, not a "
    "comparison of holding policies."
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
    return ("Measured on the corrected {n:,}-name / {d}-date panel: {c0}; {c1}; and it is the "
            "{c2}.").format(n=PANEL_NAMES, d=PANEL_DATES, c0=CAVEAT_CLAUSES[0],
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
        "not_a_hold_rule": NOT_A_HOLD_RULE,
        "band": BAND,
        "band_scope": BAND_SCOPE,
        "horizon_quarters": HORIZON_QUARTERS,
        "rank_ic": {"first_quarter": RANK_IC_FIRST_QUARTER, "two_years": RANK_IC_TWO_YEARS},
        "tenure": {"one_rebalance_share": ONE_REBALANCE_SHARE,
                   "one_period_retention": ONE_PERIOD_RETENTION},
        "source": SOURCE,
        "register": REGISTER,
    }
