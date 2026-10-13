"""WHAT THE PRICE ASSUMES — the sentence a valuation page should lead with, and the warning
that has to sit above a fair value nobody should decide on.  [item 52, parts 2, 3 and 7b]

**WHY THIS IS THE LEAD AND NOT A BOX FURTHER DOWN.** TSLA's page showed a base fair value of
**$23.23** against a price of **$378.03** and a badge reading *"DCF reliability: high"*. Every
one of those is produced correctly by the model and together they tell a reader to trust a
number that is −94% of the price. The decision-grade statement for a name like that is not the
fair value at all: it is **what growth the price is already paying for**, which the engine
computes on every run (`reverse_dcf`) and the page buried.

**THREE NUMBERS, IN ONE SENTENCE, BECAUSE SEPARATELY THEY MISLEAD.** The price's implied
growth, the growth the business actually shows, and the model's own base case. Each alone
invites the wrong reading — the implied figure looks like a forecast, the business figure looks
like a projection, and the model's figure looks company-specific when for a hypergrowth name it
is nothing of the kind (see `hypergrowth_template_note`).

**THE STORY-STOCK RULE IS STATED ON THE PAGE, NOT INFERRED.** Don's instruction was that this
is page copy rather than a research claim, and that the rule must be written down. It is:
`STORY_GAP_PP` points a year or more between what the price assumes and what the business
shows. **It is a threshold chosen for a disclosure, and it carries no verdict** — it has never
been tested against returns and nothing here says a story stock does worse. What it does is
decide whether a reader is told not to lean on the DCF, and for that purpose being roughly
right and visible beats being precise and hidden.

**NOTHING HERE SCORES ANYTHING.** No number this module produces enters a score, a composite,
the hot list, the Index or the forward record, and no figure already published moves. It reads
what the engine already computed and says it in words.
"""
from __future__ import annotations

from typing import Optional

#: The gap, in PERCENTAGE POINTS A YEAR, between what the price assumes and what the business
#: shows, at or above which the page calls a name a story stock and says not to lean on the
#: DCF. Stated on the surface itself (`STORY_RULE_TEXT`) so a reader can disagree with the
#: rule rather than with an unexplained warning.
#:
#: 15 IS A DISCLOSURE THRESHOLD AND IS NOT CALIBRATED AGAINST ANYTHING. Don's prompt proposed
#: it; this project has never tested it, and the warning it triggers is a caveat rather than a
#: claim, so a wrong threshold costs a reader a caveat they did not need. The cost of the
#: opposite error -- a reader deciding on a $23 fair value for a $378 stock -- is not symmetric.
STORY_GAP_PP = 15.0

STORY_RULE_TEXT = (
    "We call a company a story stock when the price assumes at least %d percentage points a "
    "year more growth than the business has actually shown. That is a rule for deciding when "
    "to show this warning, not a finding: we have never tested whether story stocks do better "
    "or worse." % int(STORY_GAP_PP)
)

#: The regimes and flags for which the DCF is the wrong lens, from the engine's own
#: classification rather than from a list typed here.
_WARN_REGIMES = ("hypergrowth",)

WARNING_HEADLINE = "Do not use the fair value below to decide on this company."

#: One reason per trigger. A warning that cannot say WHY is one a reader learns to scroll past.
_WHY = {
    "hypergrowth": ("Almost all of this company's value is growth that has not happened yet, "
                    "and a cash-flow model cannot pin that down: small changes in the growth "
                    "and margin assumptions move the answer enormously."),
    "cash_burning": ("This company does not yet generate the cash a discounted-cash-flow model "
                     "discounts, so the model is valuing a path to profitability rather than a "
                     "business as it stands."),
    "growth_led": ("The fair value here is led by a growth model rather than by cash flows, "
                   "which means it is an opinion about future revenue more than a measurement "
                   "of today's business."),
    "low_reliability": ("The model's own reliability flag for this company type is LOW: the "
                        "discounted-cash-flow lens is not the one that fits it."),
    "story": ("The price already assumes far more growth than this business has shown, so the "
              "gap between the two is the whole question and a single fair value cannot "
              "express it."),
}


def _pct(x, dp=0):
    if x is None:
        return None
    return "%.*f%%" % (dp, float(x) * 100.0)


def story_gap_pp(reverse, business_growth) -> Optional[float]:
    """Points a year between what the price assumes and what the business shows, or None.

    **`None` IS NOT ZERO.** A name with no implied figure (the solver did not converge, or the
    model declined to value it) has an UNKNOWN gap, and returning 0.0 would read as "the price
    assumes exactly what the business does" -- the most reassuring possible answer to a
    question nobody answered. The COVERAGE RULE's direction.
    """
    imp = getattr(reverse, "implied_avg_growth", None) if reverse is not None else None
    if imp is None or business_growth is None:
        return None
    return (float(imp) - float(business_growth)) * 100.0


def is_story_stock(reverse, business_growth) -> Optional[bool]:
    gap = story_gap_pp(reverse, business_growth)
    if gap is None:
        return None
    return gap >= STORY_GAP_PP


def price_assumes(reverse, business_growth, *, is_financial: bool = False,
                  implied_roe=None, book_roe=None) -> dict:
    """The lead sentence, plus the parts it was built from so a surface can re-use them.

    `available` is False when the engine produced no implied figure, and the surface then says
    so rather than rendering a sentence with a hole in it.
    """
    out = {"available": False, "sentence": "", "implied": None, "business": None,
            "model": None, "bounded": "", "is_financial": bool(is_financial),
            "gap_pp": None}

    if is_financial:
        # THE MATCHING QUESTION, as the reverse box already asks it. A bank's value is not a
        # discounted free-cash-flow stream, so "what growth does the price assume" is the
        # wrong question and the honest one is what return on equity it has to earn.
        if implied_roe is None:
            out["sentence"] = ("We could not work out what return on equity this price "
                               "assumes, so there is no implied read to show.")
            return out
        out.update(available=True, implied=implied_roe, business=book_roe)
        # THE CONCEPT IS NAMED. "about 18.2% on its book value" is the same arithmetic and
        # leaves a reader to work out what it is called; a bank's whole question is the
        # return on equity, and the sentence should say the words.
        if book_roe is None:
            out["sentence"] = ("The price assumes this company earns a return on equity of "
                               "about %s." % _pct(implied_roe, 1))
        else:
            out["sentence"] = ("The price assumes this company earns a return on equity of "
                               "about %s; it has been earning about %s."
                               % (_pct(implied_roe, 1), _pct(book_roe, 1)))
        return out

    imp = getattr(reverse, "implied_avg_growth", None) if reverse is not None else None
    base = getattr(reverse, "base_avg_growth", None) if reverse is not None else None
    bounded = (getattr(reverse, "implied_growth_bounded", "") or "") if reverse is not None else ""
    if imp is None:
        out["sentence"] = ("We could not work out what growth this price assumes, so there is "
                           "no implied read to show.")
        return out

    # "AT LEAST", NOT "ABOUT", WHEN THE SOLVER HIT ITS BOUND. The engine flags exactly the
    # priced-for-perfection names where the figure matters most, and reporting a floor as an
    # estimate is how the understatement would go unnoticed.
    lead = "at least about" if bounded == "above" else ("at most about" if bounded == "below"
                                                        else "about")
    bits = ["The price assumes %s %s a year of growth" % (lead, _pct(imp))]
    if business_growth is not None:
        bits.append("the business grew %s over the last year" % _pct(business_growth))
    else:
        bits.append("we have no measured growth for the last year")
    if base is not None:
        bits.append("the model's base case uses %s a year" % _pct(base))
    # A SEMICOLON AFTER THE FIRST CLAUSE AND "and" BEFORE THE LAST, which is the shape Don's
    # own example takes: the implied figure is the lead and the other two are what it is read
    # against, so they belong on the same side of the break.
    tail = " and ".join(bits[1:])
    out.update(available=True, implied=imp, business=business_growth, model=base,
               bounded=bounded, gap_pp=story_gap_pp(reverse, business_growth),
               sentence=(bits[0] + ("; " + tail if tail else "") + "."))
    return out


def dcf_warning(*, regime: str = "", dcf_reliability: str = "", cash_burning: bool = False,
                growth_led: bool = False, reverse=None, business_growth=None) -> dict:
    """Should the page tell a reader not to decide on the fair value, and why.

    Every trigger is read from the engine's own classification. `triggers` is a LIST because a
    name can be several at once and a reader deserves each reason rather than the first one.
    """
    trig = []
    if regime in _WARN_REGIMES:
        trig.append("hypergrowth")
    if cash_burning:
        trig.append("cash_burning")
    if growth_led:
        trig.append("growth_led")
    if str(dcf_reliability).lower() == "low":
        trig.append("low_reliability")
    if is_story_stock(reverse, business_growth):
        trig.append("story")
    return {
        "warn": bool(trig),
        "triggers": trig,
        "headline": WARNING_HEADLINE if trig else "",
        "why": [_WHY[t] for t in trig],
        "rule": STORY_RULE_TEXT if "story" in trig else "",
        "gap_pp": story_gap_pp(reverse, business_growth),
        # WHAT THE RELIABILITY BADGE MAY SAY WHEN THIS FIRES. "DCF reliability: high" beside a
        # warning not to use the DCF is a contradiction a reader resolves in favour of the
        # badge, because a badge looks like a measurement. It is renamed to what it actually
        # measures -- whether the INPUTS this company type needs are the ones the model wants
        # -- and never left reading as trust in the fair value.
        "reliability_label": ("How well this company type fits a cash-flow model"
                              if trig else "DCF reliability"),
        "reliability_suppressed": bool(trig),
    }


def hypergrowth_template_note(regime: str, reverse, cap_pct: float = 60.0) -> str:
    """Item 52 part 7b: the model's base growth for a hypergrowth name is a TEMPLATE.

    MEASURED, NOT ASSERTED. `GROWTH_CAP_BY_REGIME["hypergrowth"]` is 0.60 and the start growth
    is clamped to it, so every hypergrowth name whose own growth exceeds 60% starts at exactly
    60% and follows the same 10-year fade: `_fade_path(0.60, 0.030, 10, 2)` has mean 0.3435 --
    the 34.35% that appeared on BOTH NVDA's page (growth input 77%) and APLD's (100%).
    Without this sentence "the model's base case uses 34%" reads as a forecast about the
    company, which it is not.
    """
    if regime != "hypergrowth":
        return ""
    base = getattr(reverse, "base_avg_growth", None) if reverse is not None else None
    if base is None:
        return ""
    return ("That base case is not a forecast about this company. For a hypergrowth name the "
            "model caps the starting growth at %s a year and fades it on a fixed path, so "
            "every company in this category whose own growth is above the cap gets the same "
            "numbers." % _pct(cap_pct / 100.0))
