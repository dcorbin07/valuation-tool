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

THE TWO SENTENCES THAT MAY NOT TRAVEL ALONE
-------------------------------------------
`INDEX-BOOK`'s ledger row states it as a void condition: *"BOTH ALPHA SENTENCES ARE TRUE AND
NEITHER MAY TRAVEL ALONE."* Against its OWN large-cap universe the served book earns
**+4.1209pp/yr**, stable across halves. Against the **all-cap equal-weighted** universe -- the
benchmark every previously published figure used -- it earns **−0.0576pp**, i.e. nothing. Roughly
70% of that gap is the small-cap premium a large-cap tier declines to hold rather than the
composite failing, which is why both readings are honest and why quoting the +4.12 alone is not.
`block()` therefore refuses to emit one without the other.

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
STUDY = "INDEX-BOOK"
STUDY_COMMIT = "ceffd04"
STUDY_DATE = "2026-10-02"
STUDY_ARTIFACT = "data/free_analysis/INDEX_BOOK.json"
STUDY_RECORD = "HANDOFF_edge_audit.md INDEX-BOOK"

#: The construction the Index serves, in words, from `build_index` and the constants beside it.
SERVED_CONSTRUCTION = ("$10B large-cap tier, score-weighted, 8% position cap, "
                       "0.30 no-trade band")

#: The panel both arms were measured on. Identical for the served and research books, which is
#: what makes the two comparable at all.
PANEL = "2,531-name point-in-time panel, 69 quarterly dates (~18 years)"

# --- THE SERVED BOOK (the Index) -------------------------------------------------------------
# Percent per year, as the record states them. Named `_pct` rather than stored as fractions
# because the x100 confusion is a family this project has paid for more than once.

#: Roth/IRA: net of modelled trading costs, no tax. THE LEADING FIGURE (18-AMEND).
SERVED_ROTH_PCT = 17.1619
SERVED_ROTH_SHARPE = 1.0318
SERVED_ROTH_MAXDD_PCT = -23.03

#: Taxable: the IDENTICAL run with the rates switched on. FIFO, 40.8% short / 23.8% long.
SERVED_TAXABLE_PCT = 12.2033
SERVED_TAXABLE_SHARPE = 0.7595
SERVED_TAXABLE_MAXDD_PCT = -24.76

#: The clean difference on identical lots and trades.
TAX_COST_PP = 4.9586

#: SPY over the same window on the same benchmark basis, and what the taxable book does to it.
SPY_PCT = 15.23
TAXABLE_VS_SPY_PP = -3.03

#: Why the tax cost is this large, measured rather than asserted.
SHORT_TERM_SHARE_PCT = 84.08

#: The study's own main cost path, which the lot path above reproduces to ~2e-4. Both ship: a
#: reader who finds one in the record and the other on the page should see why they differ.
SERVED_NET_PCT = 17.1817
SERVED_SHARPE = 1.0318
SERVED_MAXDD_PCT = -23.06
SERVED_TURNOVER = 2.4372
SERVED_COST_BPS_ONE_WAY = 9.58

#: THE THREE ALPHA LEGS. Halves are reported because averaging them away is what hid the
#: instability in the first place.
ALPHA_VS_OWN_TIER_PP = 4.1209
ALPHA_VS_OWN_TIER_EARLY_PP = 4.0615
ALPHA_VS_OWN_TIER_LATE_PP = 4.1746

ALPHA_VS_SPY_PP = 1.9488
ALPHA_VS_SPY_EARLY_PP = 3.7202
ALPHA_VS_SPY_LATE_PP = 0.2702

#: Against the benchmark every previously published figure used. Essentially nothing, and it
#: may not be omitted when the +4.12 is quoted.
ALPHA_VS_ALL_CAP_EW_PP = -0.0576

# --- THE RESEARCH DECILE (NOT the Index) -----------------------------------------------------
# All-cap tier, EQUAL weight, no band. Kept because `/proof` legitimately reports it -- as the
# research decile, labelled, and never as the Index.
RESEARCH_NET_PCT = 23.2893
RESEARCH_ALPHA_VS_EW_PP = 6.0500
RESEARCH_ALPHA_VS_SPY_PP = 8.0564
RESEARCH_SHARPE = 1.0997
RESEARCH_MAXDD_PCT = -28.48
RESEARCH_TURNOVER = 2.6066
RESEARCH_COST_BPS_ONE_WAY = 33.35
RESEARCH_LABEL = "RESEARCH DECILE (all caps, equal-weighted)"

# --- POWER, each arm at its OWN tracking error ------------------------------------------------
# `MB8`'s rule: an `se` may not be borrowed across constructions. Pairing the served book's edge
# with the all-cap decile's tracking error would be a numerator from one book over a denominator
# from another.
SERVED_TE_VS_SPY = 8.4381
SERVED_MONTHS_TO_DETECT = 4383
SERVED_YEARS_TO_DETECT = 365

RESEARCH_TE_VS_SPY = 11.3878
RESEARCH_MONTHS_TO_DETECT = 385
RESEARCH_YEARS_TO_DETECT = 32.1

#: What the contract's power arithmetic uses TODAY, and why it is wrong twice over.
CONTRACT_EDGE_IN_USE_PP = 9.9864
CONTRACT_TE_IN_USE = 11.40
CONTRACT_MONTHS_IN_USE = 242


def power_sentence() -> str:
    """What the five-year forward test can and cannot show, for the served book.

    Stated plainly because the alternative is a reader assuming a null is evidence. The
    contract's own §2 already says 60 months runs at 49% power against the figure it uses; that
    figure is the ALL-CAP decile's and it is GROSS. On the book actually served, at its own
    measured tracking error, the requirement is 4,383 months.
    """
    return ("On the book the Index actually serves, detecting its edge over SPY would take "
            "about {m:,} months — roughly {y:.0f} years — at the book's own measured tracking "
            "error of {te:.2f} pp/yr. So the five-year forward test can show whether the Index "
            "is being recorded honestly and whether its costs and turnover behave as modelled. "
            "It cannot show whether the Index beats SPY: no five-year result, in either "
            "direction, would settle that.").format(
        m=SERVED_MONTHS_TO_DETECT, y=SERVED_YEARS_TO_DETECT, te=SERVED_TE_VS_SPY)


def block() -> dict:
    """The backtest block for the Index's surfaces. Roth leads; both alpha legs always travel.

    Returns percent-per-year figures under `_pct` keys and percentage-point differences under
    `_pp`, so a caller cannot multiply one by 100 and get the other.
    """
    return {
        "source": "measured",
        "study": STUDY, "study_commit": STUDY_COMMIT, "study_date": STUDY_DATE,
        "study_record": STUDY_RECORD, "artifact": STUDY_ARTIFACT,
        "construction": SERVED_CONSTRUCTION,
        "panel": PANEL,
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
            "sharpe": SERVED_TAXABLE_SHARPE,
            "max_drawdown_pct": SERVED_TAXABLE_MAXDD_PCT,
            # The cost of transparency, stated rather than left to be derived.
            "vs_spy_pp": TAXABLE_VS_SPY_PP,
            "below_spy_sentence": (
                "After tax this book lands {d:.2f} pp a year BELOW SPY ({spy:.2f}%), because "
                "{st:.2f}% of its realised gains are short-term — a quarterly book turning over "
                "{t:.2f}x a year realises almost everything inside a year.").format(
                d=abs(TAXABLE_VS_SPY_PP), spy=SPY_PCT, st=SHORT_TERM_SHARE_PCT,
                t=SERVED_TURNOVER),
        },
        "tax_cost_pp": TAX_COST_PP,
        "tax_cost_sentence": (
            "Both treatments are the SAME run with the tax rates as the only knob, so the "
            "{c:.4f} pp a year is a clean difference on identical lots and trades."
        ).format(c=TAX_COST_PP),
        # The caveat runs AGAINST the taxable arm, so it travels with it.
        "dividend_caveat": (
            "The panel's forward returns carry no dividends, so dividend income is absent from "
            "the return and dividend tax is absent from the after-tax figure. That understates "
            "a real taxable investor's drag, most of all for a large-cap book."),

        "alpha": {
            # Both legs, always. See the module docstring.
            "vs_own_tier_pp": ALPHA_VS_OWN_TIER_PP,
            "vs_own_tier_early_pp": ALPHA_VS_OWN_TIER_EARLY_PP,
            "vs_own_tier_late_pp": ALPHA_VS_OWN_TIER_LATE_PP,
            "vs_own_tier_label": "vs an equal-weighted basket of the same large-cap tier",
            "vs_all_cap_ew_pp": ALPHA_VS_ALL_CAP_EW_PP,
            "vs_all_cap_ew_label": "vs the all-cap equal-weighted universe",
            "vs_spy_pp": ALPHA_VS_SPY_PP,
            "vs_spy_early_pp": ALPHA_VS_SPY_EARLY_PP,
            "vs_spy_late_pp": ALPHA_VS_SPY_LATE_PP,
            "both_sentence": (
                "Against an equal-weighted basket of its own large-cap tier the book earns "
                "{t:+.4f} pp a year, and that is stable across the sample's halves "
                "({te:+.4f} early, {tl:+.4f} late). Against the ALL-CAP equal-weighted "
                "universe — the benchmark the site's older figures used — it earns "
                "{a:+.4f} pp, which is nothing. Both are true: roughly 70% of the gap is the "
                "small-cap premium a large-cap tier declines to hold, not the ranking failing "
                "in large caps."
            ).format(t=ALPHA_VS_OWN_TIER_PP, te=ALPHA_VS_OWN_TIER_EARLY_PP,
                     tl=ALPHA_VS_OWN_TIER_LATE_PP, a=ALPHA_VS_ALL_CAP_EW_PP),
            "vs_spy_sentence": (
                "Against SPY the full-sample figure is {f:+.4f} pp a year, and the halves "
                "disagree sharply — {e:+.4f} pp early against {l:+.4f} pp late. The halves are "
                "shown rather than averaged, because the average describes neither."
            ).format(f=ALPHA_VS_SPY_PP, e=ALPHA_VS_SPY_EARLY_PP, l=ALPHA_VS_SPY_LATE_PP),
        },

        "sharpe": SERVED_SHARPE,
        "max_drawdown_pct": SERVED_MAXDD_PCT,
        "annual_turnover": SERVED_TURNOVER,
        "realised_cost_bps_one_way": SERVED_COST_BPS_ONE_WAY,

        "power": {
            "months_to_detect_vs_spy": SERVED_MONTHS_TO_DETECT,
            "years_to_detect_vs_spy": SERVED_YEARS_TO_DETECT,
            "own_tracking_error_pp": SERVED_TE_VS_SPY,
            "sentence": power_sentence(),
        },

        "caption": (
            "In-sample and hypothetical: {p}, which the model was also tuned on. It is not a "
            "forward test and not a projection for any individual — your own rates, lot history "
            "and state tax are not modelled."
        ).format(p=PANEL),

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
    """
    return {
        "available": True,
        "mode": "served",
        "config": "served-index-book",
        "lines": [
            # LEVELS. Roth first (18-AMEND): the Index is a Roth product.
            {"kind": "level", "key": "roth",
             "label": "In a Roth/IRA — net of costs, no tax",
             "value": SERVED_ROTH_PCT / 100.0},
            {"kind": "level", "key": "taxable",
             "label": "In a regular brokerage account — after tax",
             "value": SERVED_TAXABLE_PCT / 100.0},
            # EXCESSES, each naming its benchmark. All three travel together.
            {"kind": "excess", "key": "vs_own_tier",
             "label": "vs an equal-weighted basket of the same large-cap tier",
             "gross": None, "net": ALPHA_VS_OWN_TIER_PP / 100.0},
            {"kind": "excess", "key": "vs_all_cap_ew",
             "label": "vs the all-cap equal-weighted universe",
             "gross": None, "net": ALPHA_VS_ALL_CAP_EW_PP / 100.0},
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
        "halves_note": block()["alpha"]["vs_spy_sentence"],
        "tax_note": block()["taxable"]["below_spy_sentence"],
        "power_note": power_sentence(),
        "study": STUDY, "study_commit": STUDY_COMMIT, "study_date": STUDY_DATE,
        # The SPMO keys the renderer null-guards. This card makes no reported-benchmark claim.
        "spmo_available": False, "partial_note": None, "band_note": None,
    }


def research_block() -> dict:
    """The all-cap equal-weighted decile. For `/proof` only, and labelled as research.

    Separated from `block()` so a surface cannot reach the Index's figures and the research
    decile's through one call and render them interchangeably, which is how the research
    decile came to be published as the Index.
    """
    return {
        "label": RESEARCH_LABEL,
        "is_the_served_book": False,
        "not_the_index": ("This is the research decile — all caps, equal-weighted, no band. It "
                          "is NOT the Valquo Index, which holds a $10B large-cap tier, "
                          "score-weighted with an 8% cap and a 0.30 no-trade band."),
        "panel": PANEL,
        "net_pct": RESEARCH_NET_PCT,
        "alpha_vs_ew_pp": RESEARCH_ALPHA_VS_EW_PP,
        "alpha_vs_spy_pp": RESEARCH_ALPHA_VS_SPY_PP,
        "sharpe": RESEARCH_SHARPE,
        "max_drawdown_pct": RESEARCH_MAXDD_PCT,
        "annual_turnover": RESEARCH_TURNOVER,
        "realised_cost_bps_one_way": RESEARCH_COST_BPS_ONE_WAY,
        "months_to_detect_vs_spy": RESEARCH_MONTHS_TO_DETECT,
        "own_tracking_error_pp": RESEARCH_TE_VS_SPY,
        "study": STUDY, "study_commit": STUDY_COMMIT,
    }
