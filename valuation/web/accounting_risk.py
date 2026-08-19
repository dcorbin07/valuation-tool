"""MA28-CARD — the accounting red-flag crash statistic, disclosed on the hot list.

WHAT IT SAYS, AND THE EXACT SHAPE IT IS ALLOWED TO SAY IT IN
-----------------------------------------------------------
`MA28-CARD` measured one thing on the 18-year point-in-time panel: names tripping **two or more**
of three published accounting stress tests — Beneish M above -1.78, Altman Z below 1.81, and
top-decile within-date external financing — lost **more than half their value** over the
following quarter at **2.66%** against a base rate of **0.87%**. A ratio of **3.04x**, and it
replicated: 3.42x early, 2.93x late, every window's observed value beyond the MAXIMUM of its own
500-draw permutation null rather than merely beyond the p95.

THE RATIO AND BOTH RATES, NEVER THE DIFFERENCE — and that is a measured rule, not a style
preference. The base rate is era-dependent: 0.34% early against 1.36% late, a four-fold move
spanning COVID 2020Q1 and 2022. So the absolute gap swings from 0.86pp to 2.39pp across halves
while the ratio barely moves. **A card saying "1.6 percentage points more likely" quotes an era
average that describes neither half.** The flag scales the market's own crash frequency
multiplicatively; it does not add a constant. `RATIO` is DERIVED from the two rates, which are
themselves derived from the four counts, so no figure here can drift from its own arithmetic —
and `test_accounting_risk.py` fails on any subtraction of the two rates anywhere in this module.

WHAT IT IS NOT, AND THE REGISTER IS EXPLICIT ABOUT EACH
-------------------------------------------------------
1. **NOT A RETURN CLAIM.** The register gated this on crash-rate replication and *explicitly not*
   on alpha — `top_decile_alpha` is computed nowhere in its arm path, pinned there by an AST
   test. `S10-ACCT` already ran the same flag as a portfolio SCREEN and was REJECTED, and `S10`
   had measured why that leg can never pass: this book's maximum drawdown is one market-wide
   quarter (COVID 2020Q1, trough index 44 of 69), which no name-level flag can move. So the card
   may not imply flagged names underperform, are worth avoiding, or should be sold. `BANNED`
   enumerates those wordings and they are checked against the RENDERED payload.

2. **NOT AN ACCUSATION.** Beneish's M-score is an earnings-*manipulation* index in the academic
   literature, and the single most tempting copy edit on this surface is to say so in plain
   words. A published statistical index crossing a published threshold is not evidence that a
   named company committed fraud, and this product will not say it did. The FRAUD family in
   `BANNED` is there for that and is the family whose false positives cost least.

3. **NOT A SCREEN.** It orders nothing, filters nothing, gates nothing. `MA30`'s tenure
   disclosure and `MA29`'s refusal count carry the same rule and the same test: the moment a
   disclosure decides which rows appear it has become a selection rule needing its own register
   and the both-halves gate.

4. **NOT 2-OF-FOUR.** The audit proposes four flags including NT late-filing notices. Those are
   not buildable from anything this project owns, so the measured rule is 2-of-**three** and is
   therefore NARROWER. A pass here does not license the audit's four-flag version.

THE AUDIT'S OWN PRODUCT SENTENCE WAS WRONG AND SHIPPING IT VERBATIM WOULD HAVE PUBLISHED A
NUMBER THAT REFUTES ITSELF
------------------------------------------------------------------------------------------
`VALQUO_MASTER_AUDIT.md:950` proposes displaying that flagged names *"fell 20%+ in a quarter
2.66% of the time against 0.87%"*. Those two rates are the **-50%** rates; the register found the
pairing before measuring anything and fixed it. At -20% the real figures are **16.8% against
9.0%, a ratio of 1.88x**. The error runs in the direction that DISCREDITS the card: a 20%+
quarterly fall is an ordinary event and a 0.87% base rate for it is transparently impossible, so
a reader who knew the market would have dismissed the whole disclosure on sight. The threshold
this module states is -50%, and it states it in the same sentence as the rates.

COVERAGE FIRST, AND THE ASYMMETRY IS THE REASON THE "NOT SCORED" RULE EXISTS
----------------------------------------------------------------------------
Per the standing coverage rule, before any verdict: Beneish computable on **68.6%** of panel
rows, Altman **76.7%**, external financing **94.5%**. **22.0% of rows carry fewer than two
computable inputs and so CANNOT be flagged at all** — they sit in the base-rate group by
construction.

A name that cannot be scored must render as **not scored**, never as **clean**, and that is not
merely a principle here — it has a number. The sliver with **no** computable input at all (3,191
rows, 2.8%) crashed at **1.75%**, which is **2.01x the base rate of the names that were scored
and not flagged**. Absence of a flag is not absence of risk, and on the thinnest-data rows it ran
the wrong way. Failing open on a risk card is the worst available failure and this is the
measurement that says so.

WHY NO NAME ON THIS SURFACE CARRIES A FLAG TODAY — MEASURED, NOT ASSUMED
------------------------------------------------------------------------
The card is a disclosure and not a per-name verdict, because a per-name verdict is not
computable on the live path. Two independent reasons, both structural, both checked rather than
argued:

  * **NO INPUTS.** All three flags need **total assets**; Altman also needs total liabilities,
    working capital and retained earnings; Beneish also needs receivables, current assets, net
    PP&E, depreciation, SG&A and operating cash flow; external financing needs the two financing
    cash-flow lines. Not one of those balance-sheet or cash-flow-statement items exists on any
    live source — the free stack's `company_to_metrics` contract carries 44 keys and the
    licensed SF1 export that has them is gitignored and not in the deploy image.
    `missing_inputs()` computes this from the row it is handed on every request, so the claim is
    re-derived from live data rather than frozen in this comment.

  * **ONE FLAG IS NOT A PER-NAME PROPERTY AT ALL.** External financing flags the **top decile
    within each date**. It is a cross-sectional rank, so a single name has no flag until the
    whole cross-section is scored — which means even a complete set of inputs would require
    scoring the list, not the name.

So this module deliberately contains **no flag arithmetic**. Writing it would put a second copy
of the Beneish and Altman formulas in the tree — `scripts/s10_accounting_veto.py` is the one
definition and `scripts/ma28_riskcard.py` imports it rather than retyping it — and that copy
could not execute on a single live row. A duplicate definition of a formula that can never run
is two of this project's own named defect classes at once.

WHAT STOPS THIS FROM QUIETLY BECOMING FALSE
-------------------------------------------
`REQUIRED_INPUTS` is pinned against the SHIPPED formulas by an AST test that reads
`s10_accounting_veto.py`'s syntax tree, so a change to what the flags read fails this card's
suite. And `coverage()` reports `scoreable` from the live rows: the day a lane adds total assets
to the metrics contract, that count stops being zero and
`test_the_day_the_inputs_arrive_this_card_owes_a_scorer` FAILS — forcing the per-name half to be
built rather than letting the card go on saying "not scored" after that has stopped being true.
`track_meter`'s not-yet-due-versus-due-and-missing distinction, applied to a product surface:
the gap is dated rather than discovered years later.

FAIL-SOFT. This is a note under a public list. Any malformed input returns a block that renders
nothing, never an exception — the rule `tenure.py` and `refusals.py` already follow.
"""
from __future__ import annotations

from typing import Any, List, Optional

# --------------------------------------------------------------------------------------- #
# PROVENANCE
# --------------------------------------------------------------------------------------- #

REGISTER = "PREREG_ma28_accounting_riskcard.md"
ARTIFACT = "data/free_analysis/MA28_CARD.json"
SCRIPT = "scripts/ma28_riskcard.py"
FORMULA_SOURCE = "scripts/s10_accounting_veto.py"

PASS, WITHDRAWN = "pass", "withdrawn"

#: The state of the MA28-CARD register. Everything the surface renders is gated on it, so a
#: retraction is one constant and not a hunt through templates — `dip_posture.STATUS`'s rule,
#: and the reason a pre-B6 figure was able to sit on the public landing page for weeks.
STATUS = PASS

# --------------------------------------------------------------------------------------- #
# THE PUBLISHED THRESHOLDS — none of them fitted on this panel, which is the rare strength
# --------------------------------------------------------------------------------------- #

#: Beneish's and Altman's own published values, and a plain top decile. This panel chose none
#: of the three, so there is no threshold-fitting to discount here.
BENEISH_FLAG_ABOVE = -1.78
ALTMAN_FLAG_BELOW = 1.81
EXTFIN_TOP_DECILE = 0.90
MIN_FLAGS = 2                       # "two or more" — of THREE, not the audit's four

#: The one named bad outcome, and the window it is measured over. Stated wherever the rates are,
#: because the audit's own error was pairing these rates with a different threshold.
CRASH_THRESHOLD = -0.50
HORIZON_SESSIONS = 63

# --------------------------------------------------------------------------------------- #
# THE MEASUREMENT — COUNTS ONLY. Every rate and every ratio below is derived from these.
# --------------------------------------------------------------------------------------- #
#
# Pinning counts rather than rates is deliberate and it is checkable: `test_accounting_risk.py`
# asserts the derived rates reproduce the artifact's own `rate_flagged` / `rate_kept` / `ratio`
# to the last bit (they do — max |delta| 0.0 on all three windows). A rate typed beside a count
# is two copies of one fact, and this project has corrected four stale figures that began that
# way.

#: (crashes among flagged, flagged rows, crashes among kept, kept rows), per window.
COUNTS = {
    "full_sample": (174, 6542, 939, 107403),
    "early_half": (35, 2998, 169, 49521),
    "late_half": (138, 3462, 767, 56419),
}

#: Newey-West t on the mean per-date difference, per half. Quoted so the surface can say the
#: result held in both halves separately without a second measurement of it living anywhere.
NW_T = {"full_sample": 4.960538894438159,
        "early_half": 2.778041181147273,
        "late_half": 4.578782190103890}

#: 500 within-date permutation draws per window. The observed value exceeded the permutation
#: MAXIMUM in every window, not merely the 95th percentile — empirical p < 0.002 each.
PERMUTATION_DRAWS = 500

#: Panel-row coverage of each input, per the standing coverage rule. Read before any verdict.
COVERAGE = {"beneish": 0.6859361972881654,
            "altman": 0.7666769055245952,
            "extfin": 0.945122646891044}

#: Share of panel rows carrying two or more flags.
FLAGGED_SHARE = 0.05741366448725262

#: Rows that cannot be flagged at all, because fewer than two of the three inputs compute.
#: They sit in the base-rate group by construction.
UNSCOREABLE_ROWS = 25079
#: The sliver with NO computable input, and how often it crashed. This is the number behind the
#: "not scored is not clean" rule — see the module docstring.
NO_INPUT_ROWS = 3191
NO_INPUT_CRASH_RATE = 0.01754935756816045

#: `C4` — the control the register predicted would kill this and which passed 5 of 5 with the
#: gradient INVERTED. Altman Z contains market cap directly (`X4 = marketcap / liabilities`), so
#: the flag is mechanically size-linked and `U7`, `S10` and `V6-B` were each decided by exactly
#: that failure mode. Flagged names ARE smaller — median cap $2.69bn against $5.19bn — and the
#: effect nonetheless STRENGTHENS monotonically with size.
SIZE_QUINTILE_RATIOS = (2.009509983342549, 1.9994509516837482, 2.9644147676289174,
                        3.1684383561643834, 5.169137387650286)

#: `C5` — the largest mean per-date |Spearman| against any of the nine panel themes, and its
#: pre-committed bar. Far under, so this is not a repackaged incumbent.
INCUMBENT_RHO = -0.18580892884109151
INCUMBENT_BAR = 0.50

#: The audit's own mis-paired figures, kept because correcting a published error in silence is
#: how it comes back. At the -20% threshold the real rates are these.
AUDIT_ERROR_AT_20PCT = (0.1684500152858453, 0.08975540720464047)


# --------------------------------------------------------------------------------------- #
# DERIVED — nothing below is typed
# --------------------------------------------------------------------------------------- #

def rates(window: str = "full_sample") -> dict:
    """The two rates and their ratio for one window, derived from the four counts.

    THE RATIO IS RETURNED AND THE DIFFERENCE IS NOT, and that is the module's central rule
    rather than an omission. See the docstring: the base rate moves four-fold across the halves,
    so the pp gap swings 0.86 -> 2.39 while the ratio moves 3.42 -> 2.93.
    """
    cf, nf, ck, nk = COUNTS[window]
    flagged = float(cf) / float(nf)
    kept = float(ck) / float(nk)
    return {"flagged": flagged, "kept": kept, "ratio": flagged / kept,
            "n_flagged": nf, "n_kept": nk,
            "n_crash_flagged": cf, "n_crash_kept": ck}


def panel_rows() -> int:
    """Every row the statistic was measured on — flagged plus kept, from the counts."""
    _, nf, _, nk = COUNTS["full_sample"]
    return nf + nk


def unscoreable_share() -> float:
    """The 22% that cannot be flagged, derived rather than typed."""
    return float(UNSCOREABLE_ROWS) / float(panel_rows())


def no_input_vs_base_ratio() -> float:
    """How much more often the NO-input rows crashed than the scored-and-not-flagged ones.

    Reads 2.01x. This is the whole justification for rendering "not scored" and never "clean":
    on the thinnest-data rows, absence of a flag ran the wrong way.
    """
    return NO_INPUT_CRASH_RATE / rates("full_sample")["kept"]


def _pct(x, dp: int = 2) -> str:
    return ("%." + str(dp) + "f%%") % (100.0 * float(x))


def _x(x) -> str:
    return "%.2fx" % float(x)


# --------------------------------------------------------------------------------------- #
# THE COPY — one module owns it, a test pins it verbatim (V3 / `score_confidence`'s rule)
# --------------------------------------------------------------------------------------- #

LABEL = "Accounting stress and the risk of a very bad quarter"

#: The claim, in the exact shape the register permits: the ratio and BOTH rates, the threshold
#: in the same sentence as the rates, and the replication. Interpolated from the derived
#: figures so the sentence and the payload cannot disagree.
def headline() -> str:
    r = rates("full_sample")
    return ("On an 18-year panel of %s companies, names tripping at least two of three published "
            "accounting stress tests went on to lose more than half their value over the next "
            "quarter %s of the time, against %s for the names that did not trip them — a ratio "
            "of %s. It held separately in both halves of the period: %s early and %s late."
            % ("2,531", _pct(r["flagged"]), _pct(r["kept"]), _x(r["ratio"]),
               _x(rates("early_half")["ratio"]), _x(rates("late_half")["ratio"])))


#: Why the ratio is the quotable form. On the surface rather than in a comment, because the
#: obvious way to render this claim is the one the measurement forbids.
#:
#: THIS SENTENCE WAS REWRITTEN AFTER `violations()` FIRED ON IT, and the near-miss is worth
#: recording. Its first cut illustrated the forbidden form by quoting it — "a single 'so many
#: points more likely' figure would be an average of two eras" — which contains the banned
#: substring verbatim, so the module's own explanation of what may not be said was the first
#: thing the guard caught. `MA5` hit the identical shape when a source sweep fired on its own
#: documentation. The guard is blunt on purpose and was not weakened; the copy was.
def why_the_ratio() -> str:
    e, l = rates("early_half"), rates("late_half")
    return ("The ratio is the figure that travels; the gap measured in percentage points does "
            "not. The background rate of a halving moved about four-fold between the two halves "
            "— %s early against %s late — so any single averaged gap would describe neither era. "
            "The flag appears to scale the market's own crash rate rather than add a fixed "
            "amount to it." % (_pct(e["kept"]), _pct(l["kept"])))


#: What the three tests are, without asserting what a crossing means about a company.
WHAT_IS_MEASURED = (
    "The three tests are published academic measures, and this project fitted none of them: the "
    "Beneish M-score above -1.78, the Altman Z-score below 1.81, and being in the top tenth of "
    "companies that quarter for raising new money through shares and debt. Crossing two of the "
    "three is a statistical description of a company's accounts. It is not a finding about any "
    "company's conduct, and nothing here says one has done anything wrong.")

#: The register's own scope limit, said to a reader rather than left in the write-up.
NOT_A_RETURN_CLAIM = (
    "This is about one specific bad outcome and nothing else. The same flag was separately "
    "tested as a rule for leaving names out of a portfolio and was rejected — it did not improve "
    "the portfolio's worst stretch, because that stretch was one market-wide quarter that no "
    "single-company signal can move. So this says nothing about returns: not that flagged names "
    "do worse, not that unflagged names do better.")

#: The size control, reported because it is the finding and because its direction is unusual
#: enough that a reader would otherwise assume the opposite.
SIZE_NOTE = (
    "The obvious objection is that this is really a size measurement — one of the three tests "
    "has market value built into it, and flagged companies are smaller on average. It was "
    "checked within five company-size bands separately and the pattern holds in all five, and it "
    "is STRONGEST among the very largest companies (about %s there against about %s among the "
    "smallest). Large companies almost never halve in a quarter — unless their accounts are "
    "stressed, in which case they still do."
    % (_x(SIZE_QUINTILE_RATIOS[4]), _x(SIZE_QUINTILE_RATIOS[0])))

#: The coverage rule, and the measured reason "not scored" may never render as "clean".
def coverage_note() -> str:
    return ("Coverage, stated before the result: the three inputs could be computed on %s, %s "
            "and %s of panel rows, and %s of rows carried too few inputs to be flagged at all. "
            "Those rows are counted with the unflagged ones, which understates rather than "
            "flatters the flag. Read a blank as \"not scored\", never as \"clean\": the rows "
            "where nothing at all could be computed actually halved about %s as often as the "
            "rows that were scored and came back unflagged."
            % (_pct(COVERAGE["beneish"], 1), _pct(COVERAGE["altman"], 1),
               _pct(COVERAGE["extfin"], 1), _pct(unscoreable_share(), 1),
               _x(no_input_vs_base_ratio())))

#: Why no name in the list above carries a flag. The count comes from the live rows, so this
#: sentence stops being rendered the day it stops being true.
#:
#: The five inputs it names by hand are checked against `REQUIRED_INPUTS` by test, so the prose
#: cannot come to list a field the formulas stopped reading — the stale-figure failure this
#: project has corrected four times, in the one place here where a name is typed twice.
def not_scored_note(n_rows: int) -> str:
    return ("None of the %s names listed here is scored on this. The measurement ran on a "
            "licensed point-in-time accounts export; the live data feed behind this list does "
            "not carry the balance-sheet and cash-flow lines the three tests need — total "
            "assets, total liabilities, working capital, retained earnings and the financing "
            "cash flows among them. One of the three is also a ranking against every other "
            "company that quarter, so it is not a property a single name has on its own. The "
            "figures above describe a measured group of past companies; they are not a label "
            "being applied to anything on this page."
            % ("{:,}".format(int(n_rows)) if n_rows else "the"))


#: The standing caveat, in every state. One panel, one history, and a group rate is not a
#: statement about the next name a reader clicks — V3's per-name/group distinction.
ALWAYS = (
    "One historical panel, not a forward test, and a rate measured across thousands of "
    "companies is never a probability for any one of them.")

#: Rendered when `STATUS` is anything other than PASS. A withdrawal has to be as sayable as the
#: result — `dip_posture`'s rule about a NULL, applied to a retraction.
WITHDRAWN_NOTE = (
    "The measurement behind this disclosure is no longer published, so its figures are not "
    "shown.")


# --------------------------------------------------------------------------------------- #
# THE LIVE-INPUT GATE — measured on the rows, every request
# --------------------------------------------------------------------------------------- #

#: Every field the three shipped formulas read, from `scripts/s10_accounting_veto.py`. Pinned
#: against that file's SYNTAX TREE by test, so a change to what the flags read fails here rather
#: than silently leaving this list describing an older formula.
REQUIRED_INPUTS = (
    # Altman Z
    "assets", "liabilities", "workingcapital", "retearn", "ebit", "marketcap", "revenue",
    # Beneish M (adds these; also needs the prior-year quarter of every one of them)
    "receivables", "cor", "assetsc", "ppnenet", "depamor", "sgna", "netinc", "ncfo",
    # external financing
    "ncfcommon", "ncfdebt",
)

#: The one field all three flags need. Named separately because it makes the gate a single
#: checkable fact rather than a list to eyeball: no total assets, no flag, on any of the three.
UNIVERSAL_INPUT = "assets"


def missing_inputs(row: Any) -> List[str]:
    """Which required fields a live row does not carry a usable number for.

    Deliberately checks the ROW rather than a schema constant: a field can be in the contract
    and be None on every name, which is the coverage rule's whole subject. A row that is not a
    dict is missing everything, which is the safe direction.
    """
    if not isinstance(row, dict):
        return list(REQUIRED_INPUTS)
    return [k for k in REQUIRED_INPUTS if _num(row.get(k)) is None]


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f                                        # NaN is not a value


def scoreable(row: Any) -> bool:
    """Could this row be flagged at all? False for every live row today, and measured so."""
    return not missing_inputs(row)


# --------------------------------------------------------------------------------------- #
# THE BLOCK
# --------------------------------------------------------------------------------------- #

def block(rows: Any = None) -> dict:
    """The payload the hot list renders. Fail-soft: bad input renders nothing, never raises.

    ADDITIVE. It reads `rows` and returns; it never annotates, reorders or drops one. A test
    fails if that stops being true, because a disclosure that touches the rows has become a
    screen.
    """
    try:
        listed = [r for r in (rows or []) if isinstance(r, dict)]
        n = len(listed)
        if STATUS != PASS:
            return {"available": False, "status": STATUS, "label": LABEL,
                    "withdrawn_note": WITHDRAWN_NOTE}

        # Measured per request rather than asserted once: `scoreable` is what makes the
        # "not scored" sentence true, and it is what fails the suite when it stops being zero.
        n_scoreable = sum(1 for r in listed if scoreable(r))
        absent = sorted(set().union(*[set(missing_inputs(r)) for r in listed])) if listed \
            else list(REQUIRED_INPUTS)
        r = rates("full_sample")
        return {
            "available": True,
            "status": STATUS,
            "register": REGISTER,
            "artifact": ARTIFACT,
            "label": LABEL,
            "headline": headline(),
            "why_the_ratio": why_the_ratio(),
            "what_is_measured": WHAT_IS_MEASURED,
            "not_a_return_claim": NOT_A_RETURN_CLAIM,
            "size_note": SIZE_NOTE,
            "coverage_note": coverage_note(),
            "not_scored_note": not_scored_note(n),
            "always": ALWAYS,
            # The numbers, beside the prose, so a caller rendering its own layout has them
            # rather than having to parse them back out of a sentence.
            "rate_flagged": r["flagged"],
            "rate_kept": r["kept"],
            "ratio": r["ratio"],
            "ratio_early": rates("early_half")["ratio"],
            "ratio_late": rates("late_half")["ratio"],
            "crash_threshold": CRASH_THRESHOLD,
            "horizon_sessions": HORIZON_SESSIONS,
            "min_flags": MIN_FLAGS,
            "panel_rows": panel_rows(),
            "coverage": dict(COVERAGE),
            "unscoreable_share": unscoreable_share(),
            # THE GATE. Zero today, and the day it is not, this card owes a per-name half.
            "rows": n,
            "names_scored": n_scoreable,
            "inputs_absent": absent,
        }
    except Exception:                                    # pragma: no cover — fail-soft by design
        return {"available": False, "status": STATUS, "label": LABEL}


# --------------------------------------------------------------------------------------- #
# THE POSTURE LINE, ENFORCED AGAINST WHAT IS RENDERED
# --------------------------------------------------------------------------------------- #

#: Wordings that may not appear on this surface. Four families, banned for different reasons:
#:
#:   FRAUD — "fraud", "cooking the books", "manipulating earnings". Beneish's index is an
#:     earnings-manipulation index in the literature, so this is the family a copy edit reaches
#:     for naturally, and it is the one that would put an accusation about a named real company
#:     on a public page. Nothing measured here supports it.
#:
#:   RETURNS — "underperform", "lose money", "worse returns". The register gated this on the
#:     crash rate and explicitly NOT on alpha, and `S10-ACCT` REJECTED the same flag as a
#:     portfolio screen. A crash-rate result rendered as a return result is the exact slide
#:     `dip_posture`'s DISTRESS family exists to stop, one surface over.
#:
#:   ADVICE — "avoid", "sell", "stay away", "steer clear". This product does not give advice
#:     anywhere, and a risk card is the surface most likely to slip into it.
#:
#:   PREDICTION / PER-NAME PROBABILITY — "will crash", "likely to halve", "chance this company".
#:     V3's rule. A group rate rendered as one company's odds is the single most natural
#:     misreading of a percentage on a page about named companies.
BANNED = (
    # FRAUD
    "fraud", "fraudulent", "cooking the books", "cook the books", "manipulating earnings",
    "manipulates earnings", "earnings manipulation", "manipulator", "dishonest", "lying",
    "misleading investors", "book-cooking", "crooked", "scam",
    # RETURNS — not measured, and separately rejected as a screen
    "underperform", "under-perform", "lose money", "loses money", "worse returns",
    "poor returns", "lower returns", "drag on returns", "hurt performance",
    # ADVICE
    "avoid these", "avoid them", "steer clear", "stay away", "sell these", "sell them",
    "do not buy", "don't buy", "worth avoiding", "get out",
    # PREDICTION / PER-NAME PROBABILITY
    "will crash", "will halve", "will collapse", "will fall", "going to zero", "goes to zero",
    "likely to halve", "likely to crash", "chance this company", "probability this company",
    "this company's odds", "expect it to", "bound to",
    # The forbidden ARITHMETIC, in words. The ratio and both rates, never the difference.
    "percentage points more likely", "points more likely", "1.6pp", "1.6 percentage points",
)


def violations(text: str) -> list:
    """Which banned wordings a rendered string contains. Empty is the only passing answer."""
    low = (text or "").lower()
    return [p for p in BANNED if p in low]


def rendered_text(blk: dict) -> str:
    """Every sentence this block puts in front of a reader, for the copy assertion.

    Asserted against THIS rather than against the module source, because a phrase can be
    assembled at render time out of parts that are each innocent — `dip_posture`'s design, and
    V4's lesson that rendering is where copy leaks.
    """
    if not isinstance(blk, dict):
        return ""
    keys = ("label", "headline", "why_the_ratio", "what_is_measured", "not_a_return_claim",
            "size_note", "coverage_note", "not_scored_note", "always", "withdrawn_note")
    return " ".join(str(blk.get(k) or "") for k in keys)
