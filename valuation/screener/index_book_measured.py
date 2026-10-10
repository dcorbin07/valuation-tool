# -*- coding: utf-8 -*-
"""The Valquo Index's backtest, as measured on the book the Index ACTUALLY serves.

WHY THIS MODULE EXISTS
----------------------
Until now the figures beside the forward track came from `BOOK_CONFIGS` recomputed off the
banked panel, and that object is the **all-cap, EQUAL-WEIGHTED decile** -- its own `basis`
string said so. The Index serves something else: the **$10B large-cap tier, SCORE-weighted,
8% cap, 0.30 no-trade band**. So the tab published +26.15% gross and +19.35% net for a book
nobody holds, beside a live curve of the book they do.

`INDEX-BOOK` (r1, 2026-10-02, commit `ceffd04`) measured the served construction on the same
machinery, and it is materially lower on every axis. These are those figures.

WHY THEY ARE COMMITTED CONSTANTS RATHER THAN READ OR DERIVED
------------------------------------------------------------
Deriving them needs an ~18-year panel build, which is not a thing a web request does. Reading
them from `data/free_analysis/INDEX_BOOK.json` is worse than it looks: `data/` is gitignored, so
on the service the file is simply absent and the block would go dark for a reason unrelated to
the measurement.

So they are literals -- which is the family that produced E9 and E12 one session ago, and the
difference matters. A stale-literal defect is a figure that tracks a CLOCK: a trial count, a
universe size, a date. These track a dated STUDY with a committed artifact, and
`tests/test_index_book_measured.py` asserts **every one of them appears verbatim in
`HANDOFF_edge_audit.md` and `VALQUO_LEDGER.md`** -- both tracked. Re-run the study and the record
moves; the record moving turns this module red. That is `MA13`'s committed-literal idiom: the
human record and the machine record are the same bytes.

THE ALL-CAP LEG IS OFF THE TAB, BY DON'S RULING, AND THE REASON IS THE INTERESTING PART
--------------------------------------------------------------------------------------
`INDEX-BOOK`'s ledger row made it a void condition that both alpha sentences travel together:
against its OWN large-cap tier the published book earned **+4.1209pp/yr** and against the
**all-cap equal-weighted** universe **−0.0576pp**, i.e. nothing, so quoting the first alone
misled.

**ON THE CORRECTED UNIVERSE THAT PAIRING STOPS WORKING, AND IT STOPS WORKING IN THE FLATTERING
DIRECTION.** The all-cap leg goes **−0.0576pp -> +5.9288pp** -- and that is **mostly the
BENCHMARK FALLING** (all-cap equal weight 17.2393% -> 12.1116%/yr) rather than the Index rising
(17.1817% -> 18.0403%). Quoting +5.93pp as an alpha gain overstates it about sixfold, and the
guard that used to force the honest pairing would now be forcing the misleading number onto the
page.

**DON RULED ON 2026-10-10 (DECISIONS.md): the Index tab DROPS the all-cap leg and is shown
against SPY and against the equal-weighted $10B tier -- like for like -- with its return,
drawdown and Sharpe beside them.** The constant is KEPT rather than deleted, because the
correction is only legible beside the figure it replaced and a reader who finds +5.93pp in r1's
table needs to be able to find out why it is not on the page; `all_cap_leg_note()` is the one
place that explains it, and `card()` no longer emits it as a line.

WHAT REPLACED THE VOID CONDITION, so the tab is not simply quoting its best number: the two
benchmarks it now shows are the two the book can be held against like for like, and **both are
rendered as LEVELS beside the Index's own level** rather than as a bare excess, so a reader can
see what the benchmark did.

18-AMEND (Don, 2026-10-03): THE INDEX IS A ROTH PRODUCT
-------------------------------------------------------
Every figure leads with the **Roth/IRA** treatment -- net of modelled trading costs, no tax. The
taxable figure sits beside it, labelled for a regular brokerage account and shown for
transparency, and transparency here has a specific cost: **after tax the book lands 3.03pp BELOW
SPY.** That sentence ships with the figure rather than being left for a reader to derive.

Both treatments come from ONE lot path with the rates as the only knob, so the tax cost is a
clean difference on identical lots and trades rather than the gap between two constructions.

WHEN THIS CHANGES
-----------------
`r1`'s `INDEX-BEST` is expected to measure alternative constructions. If Don adopts one, the
Index's numbers switch to it -- and that would be an ADOPTED construction change, i.e. a vintage
event, which is not this module's call to make.
"""
from __future__ import annotations

#: Provenance. Quoted in the payload so a reader can find the study rather than trust the page.
#:
#: THE CONSTRUCTION STUDY AND THE RE-MEASUREMENT ARE TWO OBJECTS AND BOTH ARE NAMED. `STUDY`
#: is still `INDEX-BOOK` -- it measured the served construction, and the construction has not
#: changed -- while every FIGURE below now comes from its re-run on the corrected universe
#: (`CORRECTED-CLAIMS` part 1 / `INDEX_BOOK_CORRECTED.json`, 2026-10-07). Collapsing the two
#: into one `study_commit` would make the page claim the 2026-10-02 run produced numbers it
#: did not.
STUDY = "INDEX-BOOK"
STUDY_COMMIT = "ceffd04"
STUDY_DATE = "2026-10-02"
STUDY_ARTIFACT = "data/free_analysis/INDEX_BOOK.json"
STUDY_RECORD = "HANDOFF_edge_audit.md INDEX-BOOK"

#: The re-measurement these figures are read from.
CORRECTED_DATE = "2026-10-07"
CORRECTED_ARTIFACT = "data/free_analysis/INDEX_BOOK_CORRECTED.json"
CORRECTED_RECORD = "CANONICAL_FIGURE_TABLE.md + HANDOFF_edge_audit.md CORRECTED-FLOORS part 2"

#: The construction the Index serves, in words, from `build_index` and the constants beside it.
SERVED_CONSTRUCTION = ("$10B large-cap tier, score-weighted, 8% position cap, "
                       "0.30 no-trade band")

#: The panel both arms were measured on. Identical for the served and research books, which is
#: what makes the two comparable at all.
#:
#: RESTATED 2026-10-10 (the canonical move). The published panel was 2,531 names over
#: 2009-01-15 -> 2026-01-28; this one is 9,645 over 2009-03-27 -> 2026-04-09, and **THE TWO
#: SHARE ZERO REBALANCE DATES** -- the grid is derived from the universe's own trading calendar,
#: so a 3.8x wider universe shifts every date. `X2` measured the grid ALONE moving the
#: long-short *t* by 0.81 on one universe, so every figure below moved under a universe change
#: AND a grid change and the two are not separated.
PANEL = "9,645-name point-in-time panel, 69 quarterly dates (2009-03-27 to 2026-04-09)"
PANEL_PUBLISHED = "2,531-name point-in-time panel, 69 quarterly dates (2009-01-15 to 2026-01-28)"
PANEL_SHARED_DATES = 0
DISJOINT_PANELS_CAVEAT = (
    "These figures are measured on the corrected {p}. The previously published figures came "
    "from the {q}, and the two panels share ZERO rebalance dates — the grid is derived from the "
    "universe's own trading calendar, so widening the universe 3.8x shifts every "
    "date. So each figure moved under a universe change AND a grid change, and the two are not "
    "separated.").format(p=PANEL, q=PANEL_PUBLISHED)

# --- THE SERVED BOOK (the Index) -------------------------------------------------------------
# Percent per year, as the record states them. Named `_pct` rather than stored as fractions
# because the x100 confusion is a family this project has paid for more than once.
#
# EVERY LITERAL BELOW IS PINNED TO A TRACKED RECORD and `tests/test_index_book_measured.py`
# names which one per figure. `CANONICAL_FIGURE_TABLE.md` is GENERATED by
# `scripts/canon_figure_table.py` from the landed artifacts, so re-running the study moves the
# record and turns this module red -- `MA13`'s committed-literal idiom, with the record written
# by the measurement rather than by this page.

#: Roth/IRA: net of modelled trading costs, no tax. THE LEADING FIGURE (18-AMEND).
SERVED_ROTH_PCT = 18.0169
SERVED_ROTH_SHARPE = 0.9694
SERVED_ROTH_MAXDD_PCT = -28.96

#: Taxable: the IDENTICAL run with the rates switched on. FIFO, 40.8% short / 23.8% long.
SERVED_TAXABLE_PCT = 12.5036

#: The study's own main cost path, which the lot path above reproduces to ~2e-4. Both ship: a
#: reader who finds one in the record and the other on the page should see why they differ.
SERVED_NET_PCT = 18.0403
SERVED_SHARPE = 0.969432
SERVED_MAXDD_PCT = -28.9973
SERVED_TURNOVER = 2.809390
SERVED_COST_BPS_ONE_WAY = 9.435593

#: The two benchmarks the Index is now shown against, AS LEVELS, so a reader can see what the
#: benchmark did rather than only the difference (Don, 2026-10-10).
SPY_PCT = 15.8226
ALL_CAP_EW_PCT = 12.1116

#: THE ALPHA LEGS THE TAB SHOWS. Both are like-for-like: SPY is what a visitor would otherwise
#: buy, and the tier basket is the same names equal-weighted.
ALPHA_VS_OWN_TIER_PP = 4.6177
ALPHA_VS_SPY_PP = 2.2177

#: Against the benchmark every previously published figure used. **OFF THE TAB** by Don's
#: 2026-10-10 ruling and kept here so the correction is legible -- see the module docstring and
#: `all_cap_leg_note()`. The published figure was -0.0576pp.
ALPHA_VS_ALL_CAP_EW_PP = 5.9288
ALPHA_VS_ALL_CAP_EW_PUBLISHED_PP = -0.0576
ALL_CAP_EW_PUBLISHED_PCT = 17.2393
SERVED_NET_PUBLISHED_PCT = 17.1817

#: DERIVED, not a second literal (`B7`): the tier basket's own level is the book's level less
#: the alpha measured against it, and the tax cost is the difference between the two treatments
#: of ONE run. Deriving them keeps one definition of each quantity and reproduces the artifact
#: exactly (13.4226 and 5.5133).
TIER_EW_PCT = round(SERVED_NET_PCT - ALPHA_VS_OWN_TIER_PP, 4)
TAX_COST_PP = round(SERVED_ROTH_PCT - SERVED_TAXABLE_PCT, 4)

#: WHAT IS NOT RESTATED, named rather than left to be assumed absent (`V6`'s rule: an absent
#: measurement and a null must not read the same).
#:
#: * THE HALF-SAMPLE SPLIT. The corrected run's halves are in `INDEX_BOOK_CORRECTED.json` and
#:   are in no tracked record, so publishing them here would be four literals nothing pins.
#:   The PUBLISHED halves (+3.7202 early, +0.2702 late against SPY) describe the 2,531-name
#:   book and **may not be quoted beside these figures.**
#: * THE POWER ARITHMETIC. The served book's own tracking error against SPY is likewise
#:   unpinned, so `power_sentence()` states the conclusion without inventing a month count.
#:   `MB8`'s rule forbids borrowing the all-cap decile's tracking error to fill the gap.
HALVES_NOT_RESTATED = (
    "The corrected run's half-sample split is in r1's artifact and is NOT restated here. The "
    "published panel's halves (+3.7202pp early, +0.2702pp late against SPY) describe the "
    "2,531-name book and may not be quoted beside these figures.")

# --- THE RESEARCH DECILE (NOT the Index) -----------------------------------------------------
# All-cap tier, EQUAL weight, no band. `/proof` legitimately reports it -- as the research
# decile, labelled, and never as the Index -- and since item 47 it reads the FIGURES from the
# tracked `BACKTEST_RESULTS.json` rather than from literals here. See `research_block()`.

RESEARCH_LABEL = "RESEARCH DECILE (all caps, equal-weighted)"

#: THE ONE FIGURE DON'S 2026-10-10 RULING NAMES, so it is carried rather than derived: "the
#: research decile's result vs SPY is shown plainly, including that it is -1.14pp/yr net of
#: costs on the corrected universe."
#:
#: ITS PIN IS WEAKER THAN EVERY OTHER LITERAL IN THIS MODULE AND THAT IS STATED RATHER THAN
#: GLOSSED. The figure is arm B of `INDEX_BOOK_CORRECTED.json` (-1.1374442pp, quoted to 2dp by
#: the ruling) and it is in no GENERATED record -- `CANONICAL_FIGURE_TABLE.md`'s Index section
#: carries the served arm's rows and not arm B's. It is pinned to `DECISIONS.md`, which is
#: tracked and is Don's own words rather than this lane's. The direction is also checkable
#: against the tracked artifact without this literal: `BACKTEST_RESULTS.json` puts the research
#: decile's GROSS excess over SPY at +4.02pp/yr against a measured cost drag of ~4.29pp/yr, so
#: the net figure is negative on the canonical file's own numbers too.
RESEARCH_ALPHA_VS_SPY_PP = -1.14

#: THE THREE FIGURES `PAPER_TRACK_CONTRACT.md` §2 WAS SIGNED WITH, kept under their own names
#: and NOT restated (item 47).
#:
#: Amendment 2 (accepted by Don 2026-10-04) put the SERVED book's own power arithmetic into the
#: signed contract: a +1.9488pp edge over SPY against the book's own 8.4381pp tracking error,
#: needing about 4,383 months. All three are the 2,531-name panel's.
#:
#: **THE CONTRACT IS NOT UPDATED AND MUST NOT BE.** `DECISIONS.md` (2026-10-07) is explicit
#: that the canonical move does not touch the forward contract's frozen parameters, and the
#: contract's own rule forbids revising `sigma` downward -- a signed pre-registration whose
#: numbers follow the latest measurement is not a pre-registration. So the contract keeps the
#: figures it was signed with, this module publishes the corrected ones, and BOTH are named
#: with their panel so nothing can mix them. `tests/test_index_book_measured.py` checks §2
#: against THESE, not against the live constants.
CONTRACT_SIGNED_ALPHA_VS_SPY_PP = 1.9488
CONTRACT_SIGNED_TE_VS_SPY = 8.4381
CONTRACT_SIGNED_MONTHS_TO_DETECT = 4383
CONTRACT_SIGNED_PANEL = "the 2,531-name panel, as measured when Amendment 2 was signed"

#: What the contract's power arithmetic used BEFORE Amendment 2, and why it was wrong twice
#: over: the ALL-CAP equal-weighted decile's edge, measured GROSS.
#:
#: SUPERSEDED 2026-10-04. Don accepted `PREREG_DRAFT_contract_amendment_2.md` and
#: `PAPER_TRACK_CONTRACT.md` section 2 now carries the served figures (5a-2). THE NAMES AND
#: VALUES ARE KEPT rather than renamed or deleted: the correction is only legible beside the
#: figure it replaced, `/proof` and the Index tab both render the comparison, and a reader who
#: finds 9.9864 in an older write-up needs to be able to find out what it was. `_IN_USE` now
#: means "in use in section 2 until 2026-10-04".
CONTRACT_EDGE_IN_USE_PP = 9.9864
CONTRACT_TE_IN_USE = 11.40
CONTRACT_MONTHS_IN_USE = 242


def all_cap_leg_note() -> str:
    """Why the all-cap comparison is off the tab. ONE definition of that explanation."""
    return ("Against the ALL-CAP equal-weighted universe this book now reads "
            "{n:+.4f} pp a year against the previously published {o:+.4f} pp — and that is mostly the BENCHMARK FALLING ({be:.4f}% to {ba:.4f}%/yr) rather than the "
            "Index rising ({ie:.4f}% to {ia:.4f}%/yr). Quoting it as an alpha gain overstates "
            "it about sixfold, so it is off the tab by Don's 2026-10-10 ruling; the Index is "
            "shown against SPY and against an equal-weighted basket of its own $10B tier, like "
            "for like.").format(n=ALPHA_VS_ALL_CAP_EW_PP, o=ALPHA_VS_ALL_CAP_EW_PUBLISHED_PP,
                                be=ALL_CAP_EW_PUBLISHED_PCT, ba=ALL_CAP_EW_PCT,
                                ie=SERVED_NET_PUBLISHED_PCT, ia=SERVED_NET_PCT)


def power_sentence() -> str:
    """What the five-year forward test can and cannot show, for the served book.

    Stated plainly because the alternative is a reader assuming a null is evidence.

    THE MONTH COUNT IS GONE AND THAT IS DELIBERATE (item 47, the canonical move). The published
    sentence quoted 4,383 months at the served book's own 8.4381 pp/yr tracking error. The
    corrected run measures both again -- and **neither figure is in any tracked record**, so
    carrying them as literals would be exactly the stale-literal defect this module's docstring
    says it avoids. `MB8`'s rule forbids filling the gap with the all-cap decile's tracking
    error, which is the one that IS published.

    So the sentence states the conclusion, which is what protects a reader, and names where the
    arithmetic lives. The conclusion is unchanged and is not close: on the published run it was
    365 years and on the corrected one it is centuries again, because the edge over SPY is
    ~2.2pp against a tracking error several times larger.
    """
    return ("On the book the Index actually serves, its measured edge over SPY is "
            "{a:+.4f} pp a year against a tracking error several times that size, so detecting "
            "it would take CENTURIES rather than years -- the arithmetic is in r1's {art} and "
            "is not restated here. So the five-year forward test can show whether the Index "
            "is being recorded honestly and whether its costs and turnover behave as modelled. "
            "It cannot show whether the Index beats SPY: no five-year result, in either "
            "direction, would settle that. This is the paper-track contract's own conclusion "
            "since Amendment 2 (accepted 2026-10-04).").format(a=ALPHA_VS_SPY_PP,
                                                               art=CORRECTED_ARTIFACT)


def taxable_below_spy_sentence() -> str:
    """The cost of transparency, built ONLY from pinned figures.

    THE PUBLISHED SENTENCE QUOTED A LEVEL DIFFERENCE AND THIS ONE DOES NOT, for a measurable
    reason. It read "after tax this book lands 3.03 pp BELOW SPY", which needs the taxable
    book's level minus SPY's; the two legs come from different cost paths (the lot engine and
    the study's main path), and differencing them mixes 18.0169 with 18.0403 and puts a ~0.02pp
    error into an implied SPY level nobody measured.

    The same warning is exact from the pinned legs: the tax bill is LARGER THAN THE WHOLE
    MARGIN OVER SPY. That is the sentence a reader needs, and it needs no third number.
    """
    return ("Both treatments are the SAME run with the tax rates as the only knob, so the "
            "{c:.4f} pp a year is a clean difference on identical lots and trades -- and it is "
            "LARGER THAN THE BOOK'S ENTIRE {a:.4f} pp margin over SPY, so after tax a regular "
            "brokerage account lands BELOW SPY. A quarterly book turning over {t:.2f}x a year "
            "realises almost everything inside a year, so almost all of it is taxed at the "
            "short-term rate.").format(c=TAX_COST_PP, a=ALPHA_VS_SPY_PP, t=SERVED_TURNOVER)


def block() -> dict:
    """The backtest block for the Index's surfaces. Roth leads; both benchmarks are like-for-like.

    Returns percent-per-year figures under `_pct` keys and percentage-point differences under
    `_pp`, so a caller cannot multiply one by 100 and get the other.
    """
    return {
        "source": "measured",
        "study": STUDY, "study_commit": STUDY_COMMIT, "study_date": STUDY_DATE,
        "study_record": STUDY_RECORD, "artifact": STUDY_ARTIFACT,
        # The re-measurement these figures are actually from, named separately so the page
        # cannot claim the construction study produced them.
        "corrected_date": CORRECTED_DATE, "corrected_artifact": CORRECTED_ARTIFACT,
        "corrected_record": CORRECTED_RECORD,
        "construction": SERVED_CONSTRUCTION,
        "panel": PANEL,
        "panel_published": PANEL_PUBLISHED,
        "panel_shared_rebalance_dates": PANEL_SHARED_DATES,
        "disjoint_panels_caveat": DISJOINT_PANELS_CAVEAT,
        "is_the_served_book": True,

        # 18-AMEND: the Index is a Roth product, so this is the headline treatment.
        "lead": "roth",
        "roth": {
            "label": "in a Roth/IRA",
            "basis": "net of modelled trading costs, no tax",
            "return_pct": SERVED_ROTH_PCT,
            "sharpe": SERVED_ROTH_SHARPE,
            "max_drawdown_pct": SERVED_ROTH_MAXDD_PCT,
        },
        "taxable": {
            "label": "for a regular brokerage account, shown for transparency",
            "basis": ("after tax, through the shipped FIFO lot-level engine at 40.8% "
                      "short-term and 23.8% long-term"),
            "return_pct": SERVED_TAXABLE_PCT,
            # NOT RESTATED, and reported absent rather than inherited: the corrected run's
            # taxable Sharpe and drawdown are in r1's artifact and in no tracked record, so a
            # literal here would be pinned to nothing. The published 0.7595 / -24.76 describe
            # the 2,531-name book and may not be shown beside these figures.
            "sharpe": None,
            "max_drawdown_pct": None,
            "not_restated_reason": ("the corrected run's taxable Sharpe and drawdown are in "
                                    "r1's artifact and in no tracked record, so they are "
                                    "reported absent rather than borrowed from the previous "
                                    "panel"),
            "below_spy_sentence": taxable_below_spy_sentence(),
        },
        "tax_cost_pp": TAX_COST_PP,
        "tax_cost_sentence": taxable_below_spy_sentence(),
        # The caveat runs AGAINST the taxable arm, so it travels with it.
        "dividend_caveat": (
            "The panel's forward returns carry no dividends, so dividend income is absent from "
            "the return and dividend tax is absent from the after-tax figure. That understates "
            "a real taxable investor's drag, most of all for a large-cap book."),

        # LIKE FOR LIKE (Don, 2026-10-10). Both benchmarks ship as LEVELS beside the book's own
        # level, so a reader can see what the benchmark did and not only the difference.
        "benchmarks": {
            "spy_pct": SPY_PCT,
            "spy_label": "SPY total return over the same windows",
            "tier_equal_weight_pct": TIER_EW_PCT,
            "tier_equal_weight_label": ("an equal-weighted basket of the same $10B large-cap "
                                        "tier"),
            "all_cap_equal_weight_pct": ALL_CAP_EW_PCT,
            "all_cap_equal_weight_label": ("the all-cap equal-weighted universe -- NOT shown "
                                           "on the tab; see all_cap_leg_note"),
        },
        "alpha": {
            "vs_own_tier_pp": ALPHA_VS_OWN_TIER_PP,
            "vs_own_tier_label": "vs an equal-weighted basket of the same large-cap tier",
            "vs_spy_pp": ALPHA_VS_SPY_PP,
            "vs_spy_label": "vs SPY total return",
            # KEPT IN THE PAYLOAD AND OFF THE TAB. A reader who finds +5.93pp in r1's table
            # must be able to find out why it is not rendered; deleting it would make the
            # correction invisible rather than explained.
            "vs_all_cap_ew_pp": ALPHA_VS_ALL_CAP_EW_PP,
            "vs_all_cap_ew_published_pp": ALPHA_VS_ALL_CAP_EW_PUBLISHED_PP,
            "vs_all_cap_ew_shown_on_the_tab": False,
            "vs_all_cap_ew_note": all_cap_leg_note(),
            "both_sentence": (
                "Against an equal-weighted basket of its own large-cap tier the book earns "
                "{t:+.4f} pp a year ({bk:.4f}% against the basket's {bm:.4f}%), and against SPY "
                "{a:+.4f} pp ({bk:.4f}% against {spy:.4f}%). Both benchmarks are like for like: "
                "SPY is what a visitor would otherwise buy, and the basket is the same names "
                "equal-weighted."
            ).format(t=ALPHA_VS_OWN_TIER_PP, a=ALPHA_VS_SPY_PP, bk=SERVED_NET_PCT,
                     bm=TIER_EW_PCT, spy=SPY_PCT),
            "halves_not_restated": HALVES_NOT_RESTATED,
        },

        "sharpe": SERVED_SHARPE,
        "max_drawdown_pct": SERVED_MAXDD_PCT,
        "annual_turnover": SERVED_TURNOVER,
        "realised_cost_bps_one_way": SERVED_COST_BPS_ONE_WAY,

        "power": {
            # NOT RESTATED -- see `power_sentence`. Reported as absent with a reason rather
            # than carried over from the previous panel.
            "months_to_detect_vs_spy": None,
            "years_to_detect_vs_spy": None,
            "own_tracking_error_pp": None,
            "not_restated_reason": ("the corrected run's tracking error against SPY is in "
                                    "r1's artifact and in no tracked record; MB8 forbids "
                                    "borrowing the all-cap decile's"),
            "sentence": power_sentence(),
        },

        "caption": (
            "In-sample and hypothetical: {p}, which the model was also tuned on. It is not a "
            "forward test and not a projection for any individual -- your own rates, lot "
            "history and state tax are not modelled. {c}"
        ).format(p=PANEL, c=DISJOINT_PANELS_CAVEAT),

        "pending": ("r1's INDEX-BEST may measure alternative constructions; if Don adopts one, "
                    "these figures switch to it, and that is a vintage event"),
    }


def card() -> dict:
    """The served book's figures in the shape the Index tab's renderer already consumes.

    WHY THE EXISTING SHAPE RATHER THAN A NEW ONE. That renderer's own comment states the
    property worth keeping: *"The server owns every label and every number; nothing here
    computes an excess, so the card cannot drift from what was measured."* So the fix is to
    change what the server puts IN the card, not to add a second renderer that could word the
    same figures differently -- which is the defect that put a 25-name backtest beside a decile
    record in the first place.

    Values are FRACTIONS here, because `spct` in the renderer multiplies by 100. The module's
    constants are percent; the conversion happens once, at this boundary, rather than at four
    call sites.

    `gross` is `None` on every excess line and that is not an omission: `INDEX-BOOK` measured
    the alpha legs NET, and inventing a gross figure by adding back a cost estimate would be a
    number nobody measured. The renderer prints only the net half when gross is absent.

    THE ALL-CAP EXCESS LINE IS GONE (Don, 2026-10-10) and the BENCHMARK LEVELS replace it, so
    the tab shows the Index against the two things it can be held against like for like, with
    what each of those two actually returned.
    """
    return {
        "available": True,
        "mode": "served",
        "config": "served-index-book",
        "lines": [
            # LEVELS. Roth first (18-AMEND): the Index is a Roth product.
            {"kind": "level", "key": "roth",
             "label": "In a Roth/IRA -- net of costs, no tax",
             "value": SERVED_ROTH_PCT / 100.0},
            {"kind": "level", "key": "taxable",
             "label": "In a regular brokerage account -- after tax",
             "value": SERVED_TAXABLE_PCT / 100.0},
            # THE TWO BENCHMARKS, AS LEVELS, so the excesses below can be read against them.
            {"kind": "level", "key": "bench_spy",
             "label": "SPY total return, same windows",
             "value": SPY_PCT / 100.0},
            {"kind": "level", "key": "bench_tier",
             "label": "An equal-weighted basket of the same $10B tier",
             "value": TIER_EW_PCT / 100.0},
            # EXCESSES, each naming its benchmark. Like for like, both of them.
            {"kind": "excess", "key": "vs_own_tier",
             "label": "vs an equal-weighted basket of the same large-cap tier",
             "gross": None, "net": ALPHA_VS_OWN_TIER_PP / 100.0},
            {"kind": "excess", "key": "vs_spy",
             "label": "vs SPY",
             "gross": None, "net": ALPHA_VS_SPY_PP / 100.0},
        ],
        "sharpe": SERVED_ROTH_SHARPE,
        "annual_turnover": SERVED_TURNOVER,
        "max_drawdown_pct": SERVED_ROTH_MAXDD_PCT,
        "realised_cost_bps_one_way": SERVED_COST_BPS_ONE_WAY,
        "tax_cost_pp": TAX_COST_PP,
        "caption": block()["caption"],
        "basis_note": ("Measured on the construction the Index actually serves: {c}. "
                       "{b}").format(c=SERVED_CONSTRUCTION,
                                     b=block()["alpha"]["both_sentence"]),
        "all_cap_note": all_cap_leg_note(),
        "halves_note": HALVES_NOT_RESTATED,
        "disjoint_panels_caveat": DISJOINT_PANELS_CAVEAT,
        "tax_note": block()["taxable"]["below_spy_sentence"],
        "power_note": power_sentence(),
        "study": STUDY, "study_commit": STUDY_COMMIT, "study_date": STUDY_DATE,
        "corrected_date": CORRECTED_DATE,
        # The SPMO keys the renderer null-guards. This card makes no reported-benchmark claim.
        "spmo_available": False, "partial_note": None, "band_note": None,
    }


def research_block() -> dict:
    """The all-cap equal-weighted research decile. For `/proof` only, and labelled as research.

    Separated from `block()` so a surface cannot reach the Index's figures and the research
    decile's through one call and render them interchangeably, which is how the research
    decile came to be published as the Index.

    EVERY FIGURE HERE IS NOW `None`, AND THAT IS THE HONEST STATE RATHER THAN AN OMISSION
    (item 47). The published block carried seven literals from `INDEX_BOOK`'s arm B
    (23.2893%/yr net, +6.05pp vs the equal-weighted universe, +8.0564pp vs SPY, Sharpe 1.0997,
    -28.48% drawdown, 2.6066x turnover, 33.35 bps). On the corrected universe all seven move --
    arm B reads 14.6851%/yr net at Sharpe 0.7117 and **-1.1374pp vs SPY**, i.e. the SIGN of the
    headline flips -- and **not one of the corrected seven is in any tracked record**, so
    restating them here would put seven literals on a public page with nothing to pin them to
    and nothing to turn red when the study is re-run.

    WHAT REPLACES THEM, and it is strictly better for the reader: `/proof` reports the research
    decile from `BACKTEST_RESULTS.json`, which is TRACKED, ships in the deploy image and is
    read at request time -- so the figures cannot go stale against the artifact at all. This
    block keeps the LABEL and the not-the-Index sentence, which is the part a surface must not
    be able to word for itself, plus the one corrected figure Don's 2026-10-10 ruling names.
    """
    return {
        "label": RESEARCH_LABEL,
        "is_the_served_book": False,
        "not_the_index": ("This is the research decile -- all caps, equal-weighted, no band. It "
                          "is NOT the Valquo Index, which holds a $10B large-cap tier, "
                          "score-weighted with an 8% cap and a 0.30 no-trade band."),
        "panel": PANEL,
        "panel_published": PANEL_PUBLISHED,
        "disjoint_panels_caveat": DISJOINT_PANELS_CAVEAT,
        # Don's 2026-10-10 ruling 3: shown plainly. Net of measured costs, on the corrected
        # universe, this book does NOT beat SPY.
        "net_alpha_vs_spy_pp": RESEARCH_ALPHA_VS_SPY_PP,
        "net_alpha_vs_spy_sentence": (
            "Net of measured trading costs the research decile earns {a:+.2f} pp a year "
            "against SPY on the corrected universe -- it does NOT beat SPY. (Don's ruling of "
            "2026-10-10; the figure is arm B of r1's {art}.)"
        ).format(a=RESEARCH_ALPHA_VS_SPY_PP, art=CORRECTED_ARTIFACT),
        # NOT RESTATED. See the docstring: the corrected values exist and are pinned nowhere
        # tracked, so they are reported absent rather than carried over from the old panel.
        "net_pct": None,
        "alpha_vs_ew_pp": None,
        "sharpe": None,
        "max_drawdown_pct": None,
        "annual_turnover": None,
        "realised_cost_bps_one_way": None,
        "months_to_detect_vs_spy": None,
        "own_tracking_error_pp": None,
        "not_restated_reason": (
            "the corrected run's figures for this arm are in r1's artifact and in no tracked "
            "record, so they are reported absent rather than borrowed from the 2,531-name "
            "panel; /proof reads the research decile from the tracked BACKTEST_RESULTS.json "
            "instead"),
        "read_the_tracked_artifact": "BACKTEST_RESULTS.json",
        "study": STUDY, "study_commit": STUDY_COMMIT,
        "corrected_date": CORRECTED_DATE,
    }
