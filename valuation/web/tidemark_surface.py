"""TIDEMARK as a surface: where each market sits, and — first — how much that is worth.

WHY THIS MODULE EXISTS
----------------------
TIDEMARK (`C:/Users/donni/Downloads/Market Rotation/tidemark`, a SEPARATE project with its own
charter, its own register and its own trial budget) asked whether tilting new contributions
toward markets that are cheap against their own history beats contributing on a fixed schedule
to a fixed allocation. Its Phase 1 finished on vintage `2026-08-17` and ruled that **the
question cannot be asked on this data at any bar worth trusting**.

`VALQUO_MASTER_AUDIT_4.md` **MB25** commissions that result as a linked page here. **MB26**
names the one thing that must not ship with it.

WHAT CROSSES THE BOUNDARY, AND WHY THE LICENCE ARGUMENT IS CHEAP
----------------------------------------------------------------
Only **derived statistics**: percentile, episode count, effective n, band half-width, tier
label, refusal reason, vintage, and the market and anchor names. **No raw series level crosses,
ever** — not a Case-Shiller index value, not a NAREIT yield, not a Ken French factor return.

The cheapest possible compliance argument is that **TIDEMARK's own construction already
satisfies this**, so nothing had to be stripped. Its dashboard builder's docstring states the
rule in its own words — *"No forward-return numbers. None."* — and the two bands it publishes
are `SE(p) = sqrt(p(1-p)/n_eff)` and `1.96/sqrt(episodes)`, neither of which requires a licensed
value to compute. A percentile is a statement about a series' **rank**, not about its level: it
is not invertible to the underlying number and carries none of it.

**A premise correction against MB25's own framing.** It names three constrained sources —
Case-Shiller (S&P copyright, explicitly not redistributable), NAREIT (terms unverified) and Ken
French. Measured against the anchor registry actually behind this payload, **only two of the
three appear at all**: `us_housing_price_to_rent` reads Case-Shiller via `fred_CSUSHPINSA`, and
`reit_dividend_yield` / `reit_yield_spread` read `nareit_monthly`. **Ken French feeds no anchor
in TIDEMARK**, so the constraint on it is real and vacuous here rather than load-bearing. Said
plainly because "we complied with three constraints" reads stronger than "two of them applied".

WHAT IS DELIBERATELY ABSENT
---------------------------
**No forward return, no conditional mean, no strategy claim, no combined verdict.** TIDEMARK
shipped none, and this page may not manufacture one by arranging its outputs beside Valquo's.

`usd_real_broad` — TIDEMARK's own withdrawn/BROKEN anchor — does not appear, on its builder's
stated reasoning: a withdrawn anchor rendered beside live ones is an invitation to read it.

MB26 — THE PROHIBITION, IMPLEMENTED RATHER THAN PROMISED
--------------------------------------------------------
Valquo and TIDEMARK have **different denominators and different critical values**, so a reader
who compares or averages a statistic from one with a statistic from the other has been misled by
the layout. Both `N`s and both hurdles go on the page, each labelled with the project it belongs
to, and **no statistic from one project may appear inside a sentence about the other**.

Valquo's denominator is **derived live** from `research_log`, never typed here — and the
strongest argument for that is what happened while this item was being built. MB25/MB26 quote
549 trials at 3.3031 (equity) / 3.3775 (options). Measured against a worktree 31 commits behind
`main`, the register read equity **232** (hurdle 3.3005) and options **297** (3.3745) — both
audit figures stale. Measured again after merging `main`, equity is **234**, whose hurdle is
**3.3031 — exactly the audit's number** — while options is **302** at **3.3795**, which is still
not the audit's 3.3775. **So the same pair of quoted constants was wrong, then half right, inside
one session**, and any figure typed onto this page would have been wrong for one of those reads.
That is the whole case for deriving, and it is a measurement rather than an argument.

TIDEMARK's **66** and **2.89** ARE literals, because they belong to a project this repository
cannot read at runtime. They carry TIDEMARK's vintage beside them so their staleness is visible
rather than assumed — the asymmetry is deliberate and is disclosed on the page.

**AND THE HURDLE IS NOT COMPUTED HERE EITHER — `MA5`'s rule, which this module broke on its
first cut.** `sqrt(2*ln N)` must be written exactly ONCE in the shipped package, in
`statistics.hlz_hurdle`, because the same idea written four times is how a frozen `3.0` survived
in three of them. The first version of `valquo_denominator()` computed it inline and
`test_ma5_there_is_exactly_one_sqrt_2_ln_N_in_the_shipped_package` failed — the guard `MA5`
built catching a fifth copy from a lane that had the warning in view.

THE STALENESS GATE, AND ITS PRE-COMMITTED NUMBER
-------------------------------------------------
`index_track.gate_state()`'s pattern: **every unrecognised outcome fails toward showing no
number**, never toward a claim. Past `STALE_AFTER_DAYS` the page renders the vintage and a
staleness note **instead of** every reading.

**DISCLOSURE, on TIDEMARK's own precedent of disclosing exactly this: I am not blind.** The
vintage was `2026-08-17` and two days old when 90 was chosen. The number is derived from the
data's frequency rather than from today's age — the anchors are monthly series published with a
one-month lag, so a vintage older than a quarter means at least three monthly observations exist
that this page has never seen. It is a PRESENTATION choice; no verdict anywhere depends on it.

WHAT "VERBATIM" CAN AND CANNOT MEAN HERE
----------------------------------------
MB25 requires the captions to ship verbatim on the `V3` / `hold_horizon.py` precedent. TIDEMARK
is not in this repository, so a test cannot diff these strings against its documents. What is
enforced is the achievable half, and it is stated rather than implied: every caption is a
**committed literal** (so a reword shows in a diff, `MA13`'s idiom) and every caption is asserted
to **survive into the rendered page** (so a template cannot silently drop one). **Drift between
these strings and TIDEMARK's own wording can only be caught by a human re-reading both**, and
that is a real limit of this pin.
"""
from __future__ import annotations

import datetime as _dt
import math

# --- provenance -------------------------------------------------------------------------

#: The project this page reports. Not Valquo, and never merged with it.
PROJECT = "TIDEMARK"

#: TIDEMARK's provenance unit is the vintage, not a wall-clock stamp.
VINTAGE = "2026-08-17"

#: Documents behind every figure and caption below, in TIDEMARK's tree.
SOURCES = ("POWER_GATE.md", "PREREG_ANCHOR_SELECTION.md", "PREREG_P1_GATE.md",
           "scripts/p1_8_dashboard.py")

#: Pre-committed. See the module docstring for the derivation and the non-blindness note.
STALE_AFTER_DAYS = 90

# --- MB26: the two denominators, never blended -------------------------------------------

#: TIDEMARK's own multiplicity budget. Literal because this repository cannot read that
#: project at runtime; sqrt(2*ln(66)) = 2.8947, which TIDEMARK reports as |t| ~ 2.89.
TIDEMARK_TRIALS = 66
TIDEMARK_HURDLE = 2.89

#: The sentence that must accompany any side-by-side display of the two projects.
DENOMINATOR_WARNING = (
    "These two projects have different denominators and different bars. Valquo's trial "
    "register and TIDEMARK's are separate budgets, so a number from one may not be compared "
    "with, averaged against, or read as corroborating a number from the other."
)

#: MB26's prohibition, stated on the page rather than only enforced in the test.
NO_COMBINED_VERDICT = (
    "There is no combined verdict, and there will not be one. Valquo measures a "
    "cross-sectional stock ranking; TIDEMARK measured whether cross-asset rotation is "
    "answerable at all. Neither result is evidence about the other."
)

# --- the headline, verbatim from TIDEMARK's dashboard ------------------------------------

#: The dashboard's own <h2>. It is the finding, not a caveat attached to one.
HEADLINE = "The rotation question was asked. It came back unanswerable."

HEADLINE_WHAT = (
    "This project set out to test whether tilting new contributions toward markets that are "
    "cheap versus their own history beats contributing on a fixed schedule to a fixed "
    "allocation. That test cannot be run on this data at any bar worth trusting, and the "
    "ruling is binding: see POWER_GATE.md."
)

HEADLINE_WHY = (
    "The reason is sample size, not sentiment. Markets get cheap together \u2014 six separate "
    "cheap episodes between 2008 and 2016 are one macroeconomic event seen six times \u2014 so "
    "three markets pooled hold 3 independent episodes, which is fewer than the charter "
    "requires of a single market on its own."
)

HEADLINE_STATUS = (
    "This is the project's headline finding, not a caveat attached to one. \u201cNot answerable "
    "on this data\u201d is a complete answer and it was the expected one \u2014 written into the "
    "charter in advance, before any of it was measured."
)

#: MB25 requires this in TIDEMARK's own words rather than a paraphrase: "A dashboard shipped
#: without that sentence reads as a signal."
RULING = (
    "NO PHASE-2 QUESTION MAY BE ASKED ON THIS DATA. Not one of the three canonical markets "
    "reaches the power the project's own pre-registered arithmetic requires, and neither does "
    "the pooled test. The shortfall is not marginal: the best-placed market has 82 of the 155 "
    "independent years required, and the worst has 25."
)

#: POWER_GATE.md \u00a73.1 \u2014 "the same ruling read the other way round, which is more useful".
RULING_INVERSE = (
    "Read the other way round: the edge would have to run at an information ratio of 0.41 to "
    "0.74, depending on the market, before this data could detect it \u2014 against the charter's "
    "own plausible range of 0.2 to 0.4 for a costed cross-asset value overlay. The problem is "
    "not that the answer is uncertain. It is that the edge would have to be larger than such an "
    "overlay plausibly is."
)

#: The pooled co-movement arithmetic behind the headline (P1.5). All derived counts.
POOLED_EPISODES = 3
POOLED_NAIVE_SUM = 10
COMOVEMENT_DISCOUNT = 3.333
COMMON_WINDOW_YEARS = 24.7
YEARS_REQUIRED = 155.0
YEARS_BEST_MARKET = 82.3
YEARS_WORST_MARKET = 25.2

# --- the two bands, described in TIDEMARK's own terms ------------------------------------

BAND_WHERE = (
    "Where it sits: the percentile plus or minus 1.96 standard errors, computed at the "
    "effective sample size (raw observations divided by the measured design effect), never at "
    "raw n \u2014 a raw-n interval would be three to ten times too narrow."
)

BAND_IMPLIES = (
    "What it implies: 1.96 divided by the square root of the episode count \u2014 the tightest "
    "interval that count could support, in standard deviations. It needs no return data at all."
)

BAND_APPROXIMATE = "Both are approximations and are labelled as such."

#: The design rule the whole surface exists to make unmissable, from the builder's docstring.
DESIGN_RULE = (
    "A market at the 90th percentile with twelve independent episodes gets a band you can act "
    "on. One at the 90th percentile with two gets a band so wide that the honest caption is "
    "\u201cwe cannot tell you what this implies.\u201d Both are legitimate outputs, so the tier "
    "is stated before the number, in words, on every card."
)

#: The dashboard's footer, which is the claim limit for the whole page.
NO_STRATEGY_CLAIM = (
    "No strategy claim is made on this page, and none may be made on this data. Every "
    "percentile is a true statement about where a market sits in its own measured history. "
    "None of them is a statement about what happens next."
)

#: Why the two empty tiers are still rendered. Hiding them would hide the scale.
EMPTY_TIERS_NOTE = (
    "The two tiers at the top are empty, and that is the finding rather than an oversight. "
    "They are shown so the scale is visible: this dashboard is capable of saying \u201cyou can "
    "act on this\u201d, and on this data it never does."
)

# --- tiers, verbatim from the builder's TIERS table ---------------------------------------

TIERS: tuple[dict, ...] = (
    {
        "tier": "ACTIONABLE",
        "label": "A band you can act on",
        "description": ("At least 12 independent episodes AND enough independent history to "
                        "support a test. The reading means something you could lean on."),
    },
    {
        "tier": "INDICATIVE",
        "label": "Suggestive, not decisive",
        "description": ("Clears the charter's 4-episode kill condition and the anchor is "
                        "admissible, but the record is too short to support a test. Read the "
                        "direction, not the magnitude."),
    },
    {
        "tier": "NOT INTERPRETABLE",
        "label": "We cannot tell you what this implies",
        "description": ("Fewer than 4 independent episodes, or the anchor is inadmissible, or "
                        "its episode count is not robust to how the count is taken. The "
                        "percentile is a true statement about the past and supports no "
                        "inference about the future."),
    },
    {
        "tier": "REFUSED",
        "label": "No number is shown, deliberately",
        "description": ("There is not enough of its own history for a percentile to mean "
                        "anything. The refusal is the output, not a gap waiting to be filled."),
    },
)

TIER_ORDER = tuple(t["tier"] for t in TIERS)

# --- the derived statistics ----------------------------------------------------------------
#
# MACHINE-COPIED from TIDEMARK's own collect() at vintage 2026-08-17 -- not hand-typed, so a
# transcription error is not one of the ways this can be wrong. Exactly the nine keys MB25
# allowlists. The percentile standard error is deliberately NOT stored: it is recomputed by
# `percentile_se()` from percentile and n_eff using TIDEMARK's own formula, which keeps the
# payload to the allowlist and turns the reproduction into a real control.

MARKETS: tuple[dict, ...] = (
    {
        "market":      "REITs vs Treasuries",
        "anchor":      "reit_yield_spread",
        "percentile":  0.11145038167938931,
        "episodes":    5,
        "n_eff":       25.161322034277227,
        "band_sigma":  0.8765386471799175,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "Yield curve",
        "anchor":      "curve_10y_3m",
        "percentile":  0.3613636363636364,
        "episodes":    5,
        "n_eff":       45.825182488659706,
        "band_sigma":  0.8765386471799175,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "Corporate credit (quality spread)",
        "anchor":      "credit_baa_aaa",
        "percentile":  0.017815646785437646,
        "episodes":    4,
        "n_eff":       82.32400211735978,
        "band_sigma":  0.98,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "International housing (16 countries)",
        "anchor":      "intl_housing_rent_yield",
        "percentile":  None,
        "episodes":    3.0,
        "n_eff":       None,
        "band_sigma":  1.1316065276116665,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     "Measured per country across 16 countries, so there is no single reading to plot. The record ends in 2020 and is five years stale.",
        "as_of":       "2026-08-17",
    },
    {
        "market":      "US equities vs bonds",
        "anchor":      "us_equity_erp",
        "percentile":  0.12286689419795221,
        "episodes":    2,
        "n_eff":       44.20667606987484,
        "band_sigma":  1.3859292911256331,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "Cash",
        "anchor":      "cash_real_short_rate",
        "percentile":  0.4810810810810811,
        "episodes":    6,
        "n_eff":       68.50177584924747,
        "band_sigma":  0.8001666493091716,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "Corporate credit (vs Treasuries)",
        "anchor":      "credit_baa_10y",
        "percentile":  0.35113636363636364,
        "episodes":    5,
        "n_eff":       47.49125920940833,
        "band_sigma":  0.8765386471799175,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "US equities",
        "anchor":      "us_equity_caey",
        "percentile":  0.010869565217391304,
        "episodes":    5,
        "n_eff":       115.70281300794271,
        "band_sigma":  0.8765386471799175,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-08-31",
    },
    {
        "market":      "International equities (16 countries)",
        "anchor":      "intl_equity_dp",
        "percentile":  None,
        "episodes":    4.5,
        "n_eff":       None,
        "band_sigma":  0.98,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     "Measured per country across 16 countries, so there is no single reading to plot. The record ends in 2020 and is five years stale.",
        "as_of":       "2026-08-17",
    },
    {
        "market":      "US government bonds",
        "anchor":      "govt_bond_real_yield",
        "percentile":  0.3117178612059158,
        "episodes":    3,
        "n_eff":       44.969810419768265,
        "band_sigma":  1.1316065276116665,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "Broad commodities",
        "anchor":      "commodities_real",
        "percentile":  0.6328320802005012,
        "episodes":    2,
        "n_eff":       37.6867939180145,
        "band_sigma":  1.3859292911256331,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     "This is not a valuation anchor at all. It is a price measured against a general price index, or an index with no underlying cash flow, so it says what this costs — not what it costs relative to what it produces. It is shown so the dashboard can report where the market stands without pretending that is a valuation.",
        "as_of":       "2026-07-31",
    },
    {
        "market":      "REITs",
        "anchor":      "reit_dividend_yield",
        "percentile":  0.05343511450381679,
        "episodes":    1,
        "n_eff":       39.36081428133981,
        "band_sigma":  1.96,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-07-31",
    },
    {
        "market":      "US dollar (nominal, NOT a valuation anchor)",
        "anchor":      "usd_nominal_broad",
        "percentile":  0.40217391304347827,
        "episodes":    1,
        "n_eff":       22.666637401659596,
        "band_sigma":  1.96,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     "This is not a valuation anchor at all. It is a price measured against a general price index, or an index with no underlying cash flow, so it says what this costs — not what it costs relative to what it produces. It is shown so the dashboard can report where the market stands without pretending that is a valuation.",
        "as_of":       "2026-08-31",
    },
    {
        "market":      "Gold",
        "anchor":      "gold_real",
        "percentile":  0.010025062656641603,
        "episodes":    0,
        "n_eff":       34.84587284868342,
        "band_sigma":  None,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     "This is not a valuation anchor at all. It is a price measured against a general price index, or an index with no underlying cash flow, so it says what this costs — not what it costs relative to what it produces. It is shown so the dashboard can report where the market stands without pretending that is a valuation.",
        "as_of":       "2026-07-31",
    },
    {
        "market":      "US housing",
        "anchor":      "us_housing_price_to_rent",
        "percentile":  0.1716101694915254,
        "episodes":    0,
        "n_eff":       8.251107890295827,
        "band_sigma":  None,
        "tier":        "NOT INTERPRETABLE",
        "refusal":     None,
        "as_of":       "2026-05-31",
    },
    {
        "market":      "Bitcoin",
        "anchor":      "btc_real",
        "percentile":  None,
        "episodes":    None,
        "n_eff":       None,
        "band_sigma":  None,
        "tier":        "REFUSED",
        "refusal":     "No percentile is shown. This market has less history than the engine's 30-year burn-in requires, so a percentile against \"its own history\" would be a number with nothing behind it. The refusal is the output. It is not missing data and it will not be filled in later.",
        "as_of":       "2026-08-17",
    },
)

#: MB25's allowlist, exactly. `payload()["markets"]` rows carry these keys and nothing else,
#: and `tests/test_tidemark_surface.py` fails if the set ever changes.
MARKET_KEYS = ("market", "anchor", "percentile", "episodes", "n_eff",
               "band_sigma", "tier", "refusal", "as_of")

#: Rendered instead of every reading once the vintage is older than STALE_AFTER_DAYS.
STALENESS_NOTE = (
    "This reading is not shown. TIDEMARK's vintage is {vintage}, which is {age} days old "
    "against a pre-committed limit of {limit}. The underlying series are monthly, so a vintage "
    "this old has missed observations that exist. The vintage is shown instead of the number, "
    "deliberately — a stale reading rendered as a current one is worse than no reading."
)


def percentile_se(percentile: float | None, n_eff: float | None) -> float | None:
    """TIDEMARK's own `SE(p) = sqrt(p(1-p)/n_eff)`, at the EFFECTIVE n and never at raw n.

    Recomputed here rather than carried across so the payload stays exactly to MB25's
    allowlist. That makes it a control as well as a convenience: the test asserts this
    reproduces TIDEMARK's published standard errors, so a wrong `n_eff` in the table below
    would surface as a mismatch rather than as a plausible band.
    """
    if percentile is None or n_eff is None or n_eff <= 0:
        return None
    if not (0.0 <= percentile <= 1.0):
        return None
    return math.sqrt(max(percentile * (1.0 - percentile), 1e-12) / n_eff)


def _today(today=None) -> _dt.date:
    if today is None:
        return _dt.date.today()
    if isinstance(today, _dt.datetime):
        return today.date()
    return today


def freshness(today=None) -> dict:
    """Is the vintage fresh enough to show numbers? `gate_state()`'s fail-closed shape.

    Every unrecognised outcome resolves to `fresh: False`, so a malformed vintage, a clock
    problem or a future-dated stamp all end at "show the vintage, not the number" rather than
    at a claim. `age_days` is None when it could not be computed, which is a different state
    from "old" and is reported as one.
    """
    out = {"vintage": VINTAGE, "limit_days": STALE_AFTER_DAYS, "age_days": None,
           "fresh": False, "reason": ""}
    try:
        stamped = _dt.date.fromisoformat(VINTAGE)
    except Exception:
        out["reason"] = "the vintage is not a readable date, so freshness cannot be established"
        return out
    try:
        age = (_today(today) - stamped).days
    except Exception:
        out["reason"] = "the current date could not be read, so freshness cannot be established"
        return out
    out["age_days"] = age
    if age < 0:
        out["reason"] = "the vintage is dated in the future, which is not a state this trusts"
        return out
    if age > STALE_AFTER_DAYS:
        out["reason"] = ("the vintage is {a} days old, past the pre-committed limit of "
                         "{l}".format(a=age, l=STALE_AFTER_DAYS))
        return out
    out["fresh"] = True
    out["reason"] = "the vintage is {a} days old, inside the pre-committed limit of {l}".format(
        a=age, l=STALE_AFTER_DAYS)
    return out


def markets(today=None) -> list[dict]:
    """The per-market rows, carrying MB25's nine allowlisted keys and nothing else.

    Stale: every reading is replaced by the staleness note and the four numeric fields and the
    tier go None. The tier goes too, deliberately — it is a verdict about how much a
    reading is worth, so leaving it standing beside a suppressed reading would be a judgement
    with nothing under it.
    """
    f = freshness(today)
    rows = []
    for m in MARKETS:
        if f["fresh"]:
            rows.append({k: m[k] for k in MARKET_KEYS})
            continue
        note = STALENESS_NOTE.format(vintage=VINTAGE,
                                     age=("unknown" if f["age_days"] is None
                                          else f["age_days"]),
                                     limit=STALE_AFTER_DAYS)
        rows.append({"market": m["market"], "anchor": m["anchor"], "percentile": None,
                     "episodes": None, "n_eff": None, "band_sigma": None, "tier": None,
                     "refusal": note, "as_of": VINTAGE})
    return rows


def tier_counts(today=None) -> list[dict]:
    """Tier rows with their counts. The two empty tiers are RETAINED — see EMPTY_TIERS_NOTE."""
    rows = markets(today)
    return [dict(t, count=sum(1 for r in rows if r["tier"] == t["tier"])) for t in TIERS]


def valquo_denominator() -> dict:
    """Valquo's own trial register, DERIVED — never typed beside TIDEMARK's.

    MB26 wants both denominators on the page. Valquo's moves whenever a register lands, so
    quoting it would guarantee it goes stale; MB25/MB26's own figures already had by the day
    this shipped. Unreadable resolves to `available: False` with a reason, and the page then
    says the denominator could not be read rather than showing TIDEMARK's alone next to a gap
    a reader would fill in.
    """
    out = {"available": False, "equity": None, "options": None,
           "equity_hurdle": None, "options_hurdle": None, "reason": ""}
    try:
        from ..edge import research_log as RL
        by = (RL.detail() or {}).get("by_domain") or {}
        eq, op = by.get("equity"), by.get("options")
        if not eq or not op:
            out["reason"] = "the research log did not report both domains"
            return out
        from ..edge.statistics import hlz_hurdle
        out.update(available=True, equity=int(eq), options=int(op),
                   equity_hurdle=hlz_hurdle(eq), options_hurdle=hlz_hurdle(op),
                   reason="derived from RESEARCH_LOG.md at render time")
    except Exception:
        out["reason"] = "the research log could not be read"
    return out


def denominators(today=None) -> dict:
    """MB26's pair, each labelled with the project it belongs to. Never summed, never averaged."""
    return {
        "warning": DENOMINATOR_WARNING,
        "no_combined_verdict": NO_COMBINED_VERDICT,
        "tidemark": {"project": PROJECT, "trials": TIDEMARK_TRIALS,
                     "hurdle": TIDEMARK_HURDLE, "vintage": VINTAGE,
                     "note": "TIDEMARK's own budget, at its own vintage."},
        "valquo": dict(valquo_denominator(), project="Valquo",
                       note="Valquo's own budget, derived at render time."),
    }


def payload(today=None) -> dict:
    """Everything the page renders. Derived statistics and copy only — no series level.

    The template renders this and holds no TIDEMARK prose of its own, so there is exactly one
    place any of this wording can be changed.
    """
    f = freshness(today)
    return {
        "project": PROJECT,
        "vintage": VINTAGE,
        "sources": list(SOURCES),
        "freshness": f,
        "headline": {"title": HEADLINE, "what": HEADLINE_WHAT, "why": HEADLINE_WHY,
                     "status": HEADLINE_STATUS},
        "ruling": RULING,
        "ruling_inverse": RULING_INVERSE,
        "pooled": {"episodes": POOLED_EPISODES, "naive_sum": POOLED_NAIVE_SUM,
                   "comovement_discount": COMOVEMENT_DISCOUNT,
                   "common_window_years": COMMON_WINDOW_YEARS,
                   "years_required": YEARS_REQUIRED,
                   "years_best_market": YEARS_BEST_MARKET,
                   "years_worst_market": YEARS_WORST_MARKET},
        "design_rule": DESIGN_RULE,
        "bands": {"where": BAND_WHERE, "implies": BAND_IMPLIES,
                  "approximate": BAND_APPROXIMATE},
        "tiers": tier_counts(today),
        "empty_tiers_note": EMPTY_TIERS_NOTE,
        "markets": markets(today),
        "no_strategy_claim": NO_STRATEGY_CLAIM,
        "denominators": denominators(today),
    }
