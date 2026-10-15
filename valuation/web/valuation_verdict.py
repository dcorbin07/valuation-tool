"""THE VALUATION-VERDICT HEADLINE — the one module that owns this wording.  [item 60]

Don's ruling, 2026-10-14: the valuation page opens on a **valuation verdict**, not a Buy/Hold/
Sell call. That is consistent with his 2026-10-13 removal of Buy/Hold/Reduce and with the site
being educational.

**NO BUY, SELL OR TARGET-PRICE LANGUAGE APPEARS ANYWHERE**, and that is enforced rather than
intended: `BANNED` is asserted against the **RENDERED PAYLOAD** by a test, not against this
source. `dip_posture.py` established why — rendering is where copy leaks, and a ban checked
against the source passes while a template composes the forbidden phrase from two permitted
halves.

THE RULE, AND WHY IT IS SHOWN ON THE CARD
-----------------------------------------
The verdict is set by where the price sits against the model's own bear/base/bull range:

* price **below bear** → "Undervalued vs our model";
* price **between bear and bull** → "Fairly valued vs our model", plus how far it sits from base;
* price **above bull** → "Overvalued vs our model".

A reader is told the rule in one sentence on the card, because a verdict whose rule is hidden is
a recommendation wearing a measurement's clothes. "vs our model" is in every verdict string and
is not decoration: it is the whole claim. The model is one model, it has been wrong, and the
phrase is what keeps the sentence honest.

WHEN THERE IS NO VERDICT, AND THE ONE PLACE THIS RULE IS IN TENSION WITH ITSELF
-------------------------------------------------------------------------------
There is **no verdict** when the model withholds its value, when it cannot value the name, or
when it rates its own reliability for that company type as **low**. Don's ruling names KNSL as
the worked example.

**AND KNSL IS NOT A WITHHELD NAME**, which is worth stating because a withheld-only rule would
have got it wrong. Measured live 2026-10-14: `valuable=True`, no withheld value, price $349.07
against bear $230.81 and bull $365.93 — so on the range rule alone it would read "Fairly
valued". What makes it a no-verdict name is `dcf_reliability: low`.

**THE TENSION, RECORDED RATHER THAN SMOOTHED OVER.** KNSL's regime is `financial`, and a
financial is valued on justified price-to-book from ROE — **not** on a discounted cash flow. So
"DCF reliability is low" is arguably not a statement about the method actually used, and one
could argue the flag should not bind here. It binds because the ruling names this name, and
because the honest reading is the conservative one: if the model's own reliability label for a
company type is low, publishing a verdict off it claims more than the model supports. **The
REASON shown to the reader says what is true** — that the name is valued as a financial on
justified P/B and that the model rates its reliability for this type as low — rather than
implying a DCF was used and failed.

WHAT THIS MODULE DOES NOT DO
----------------------------
It changes no valuation arithmetic. Every number it reads is already computed and already
rendered somewhere on the page; item 60 is layout and wording only, and a test asserts this
module performs no valuation (it imports no engine module).
"""
from __future__ import annotations

from typing import Optional

#: Provenance, the `score_confidence` pattern: the ruling this wording comes from.
SOURCE = "DECISIONS.md, 2026-10-14 — \"valuation page headline: a valuation verdict, not "
SOURCE += "buy/hold/sell\""

UNDER, FAIR, OVER, NONE = "undervalued", "fairly_valued", "overvalued", "no_verdict"

#: The verdict strings, verbatim. **"vs our model" IS THE CLAIM** and may not be dropped: it is
#: what separates a measurement against one model from a statement about what a stock is worth.
LABEL = {
    UNDER: "Undervalued vs our model",
    FAIR: "Fairly valued vs our model",
    OVER: "Overvalued vs our model",
    NONE: "No valuation verdict",
}

#: The rule, in one plain sentence, shown ON the card. A verdict whose rule is hidden is a
#: recommendation wearing a measurement's clothes.
RULE_SENTENCE = ("We compare today's price with our model's own range: below the bear value we "
                 "call it undervalued, above the bull value overvalued, and anywhere in "
                 "between fairly valued. It is a comparison with one model, not advice.")

#: What each confidence label MEANS, in a few words, because the bare word is not informative.
#: These are the model's own labels; this module does not invent a fourth.
CONFIDENCE_MEANS = {
    "high": "the inputs this model needs are present and consistent",
    "medium": "some inputs are estimated, so treat the range as wide",
    "low": "key inputs are missing or inconsistent, so the range is weak evidence",
}

#: WHY THERE IS NO VERDICT, one reason per cause. Each is a sentence a reader can act on by
#: reading further rather than a code.
NO_VERDICT_REASON = {
    "withheld": ("Our model's value for this name came out so far from the market price that we "
                 "do not trust it, so we are not publishing a verdict."),
    "not_valuable": ("Our model could not put a value on this name — the inputs it needs are "
                     "not available — so there is no verdict to give."),
    "low_reliability": ("Our model rates its own reliability for this kind of company as low, "
                        "so we are not publishing a verdict off it."),
    "no_range": ("Our model produced a value but not a bear-to-bull range, and the verdict is "
                 "defined by that range, so there is no verdict."),
    "no_price": ("We do not have a current price for this name, so there is nothing to compare "
                 "the model's value with."),
    # THE THIRD LIMB OF THE BRIEF'S OWN RULE, and the one my first cut missed. The page already
    # tells the reader not to use this value; a 26px verdict computed FROM it directly above
    # that box is item 52's defect at larger type.
    "model_warns": ("Our model is telling you not to use its own value for this name, so there "
                    "is no verdict to give. The reason is below, and the range is still shown "
                    "so you can judge it yourself."),
}

#: **ASSERTED AGAINST THE RENDERED PAYLOAD, NEVER AGAINST THIS SOURCE.** `dip_posture.py`'s
#: design, and for its reason: rendering is where copy leaks. A source-level ban passes happily
#: while a template builds "price target" out of two permitted words.
BANNED = (
    "buy", "sell", "strong buy", "hold", "reduce", "accumulate",
    "price target", "target price", "upside target", "fair value target",
    "will rise", "will fall", "will go up", "will go down", "should buy", "should sell",
    "we recommend", "recommendation", "outperform", "underperform",
)

#: Phrases that are legitimate even though they contain a banned substring. **DECLARED, SO THE
#: BAN IS CHECKED ON WORDS AND NOT ON SUBSTRINGS** -- this project's most repeated test defect is
#: a substring ban tripping on prose that documents the rule, and the honest fix is to name the
#: exceptions rather than loosen the ban.
BANNED_EXCEPTIONS = (
    "buyback", "buybacks", "buyer", "buyers", "selling, general",
    "holder", "holders", "holding", "holdings", "household", "stakeholder",
    "sell-through", "sells",
)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def money0(x) -> str:
    """Whole dollars. The range is a range; cents in it would imply a precision it lacks."""
    v = _f(x)
    return "—" if v is None else ("$%s" % format(int(round(v)), ","))


def range_text(bear, base, bull) -> str:
    """`"$248–$425 (base $324)"`. An en dash, because this is a range and not a subtraction."""
    lo, mid, hi = _f(bear), _f(base), _f(bull)
    if lo is None or hi is None:
        return "" if mid is None else ("base %s" % money0(mid))
    core = "%s–%s" % (money0(lo), money0(hi))
    return core if mid is None else "%s (base %s)" % (core, money0(mid))


def classify(price, bear, bull) -> Optional[str]:
    """`UNDER` / `FAIR` / `OVER`, or `None` when the comparison cannot be made.

    **THE BOUNDARIES ARE INCLUSIVE OF "FAIR" ON BOTH SIDES.** A price exactly at the bear value
    is inside the range, not below it — so a name sitting precisely on a boundary reads as
    fairly valued rather than flipping on the last cent. `None` is returned rather than a guess
    when a leg is missing, and the caller turns that into a stated no-verdict.
    """
    p, lo, hi = _f(price), _f(bear), _f(bull)
    if p is None or lo is None or hi is None or p <= 0:
        return None
    if lo > hi:                  # a malformed range: refuse rather than silently swap the legs
        return None
    if p < lo:
        return UNDER
    if p > hi:
        return OVER
    return FAIR


def gap_sentence(price, base) -> str:
    """How far the price sits from the base value, in words. Empty when it cannot be computed."""
    p, b = _f(price), _f(base)
    if p is None or b is None or b <= 0:
        return ""
    rel = p / b - 1.0
    if abs(rel) < 0.005:
        return "The price is within half a percent of our base value."
    return ("The price sits %.0f%% %s our base value of %s."
            % (abs(rel) * 100.0, "above" if rel > 0 else "below", money0(b)))


def headline(*, ticker: str, name: str = "", price=None, bear=None, base=None, bull=None,
             confidence: str = "", valuable: bool = True, withheld=None,
             dcf_reliability: str = "", regime: str = "", method: str = "",
             business_quality: str = "", price_vs_model: str = "",
             assumes_sentence: str = "", warning: dict = None) -> dict:
    """The whole card, rendered. **Reads inputs; computes no valuation.**

    Returns a dict the template renders directly, so the wording a user sees and the wording a
    test checks are the same object -- which is the only arrangement in which the ban means
    anything.
    """
    out = {
        "ticker": str(ticker or "").upper(),
        "name": str(name or ""),
        "price": _f(price),
        "price_text": money0(price),
        "range_text": range_text(bear, base, bull),
        "bear": _f(bear), "base": _f(base), "bull": _f(bull),
        "rule": RULE_SENTENCE,
        "confidence": str(confidence or "").lower(),
        "confidence_means": CONFIDENCE_MEANS.get(str(confidence or "").lower(), ""),
        "method": str(method or ""),
        "verdict": NONE,
        "label": LABEL[NONE],
        "gap": "",
        "no_verdict_reason": "",
        "no_verdict_cause": "",
        "reads": [],
        "price_assumes": "",
        "warning": "",
        "warning_why": [],
        "warning_triggers": [],
    }

    # ---- is there a verdict at all? Each cause is reported SEPARATELY, because "we withheld
    # ---- the value" and "we could not value it" are different facts for a reader.
    cause = None
    w0 = (warning or {})
    if withheld not in (None, ""):
        cause = "withheld"
    elif not valuable:
        cause = "not_valuable"
    elif str(dcf_reliability or "").lower() == "low":
        cause = "low_reliability"
    elif bool(w0.get("warn")):
        # A FIRED WARNING OUTRANKS A COMPUTABLE VERDICT. Measured live: AAPL, TSLA and NVDA all
        # carry "Do not use the fair value below to decide on this company", and NVDA would
        # otherwise have read "Fairly valued vs our model" immediately above it. MSFT and KO
        # do not warn, so the brief's own worked example is unaffected -- checked before this
        # branch was added rather than hoped for afterwards.
        cause = "model_warns"
    elif _f(price) is None:
        cause = "no_price"
    elif _f(bear) is None or _f(bull) is None:
        cause = "no_range"

    if cause is None:
        v = classify(price, bear, bull)
        if v is None:
            cause = "no_range"
        else:
            out["verdict"], out["label"] = v, LABEL[v]
            out["gap"] = gap_sentence(price, base) if v == FAIR else ""
            # ABOVE OR BELOW THE RANGE, THE DISTANCE IS STILL WORTH A LINE -- a reader seeing
            # "Overvalued" deserves to know whether that is by 2% or by 60%.
            if v in (UNDER, OVER):
                out["gap"] = gap_sentence(price, base)

    if cause is not None:
        out["no_verdict_cause"] = cause
        out["no_verdict_reason"] = NO_VERDICT_REASON[cause]
        # AND FOR A FINANCIAL, SAY WHAT IT WAS VALUED ON. "DCF reliability is low" would imply a
        # DCF was used; a financial is valued on justified price-to-book from ROE, and a reason
        # that misdescribes the method is worse than a shorter one.
        # THE TRIGGER'S OWN WORDS, not a generic line. `dcf_warning` already composes a
        # per-trigger `why`, so the reader learns WHICH rule fired and the wording lives in one
        # place.
        if cause == "model_warns":
            whys = [str(x).strip() for x in (w0.get("why") or []) if str(x).strip()]
            if whys:
                out["no_verdict_reason"] = (
                    NO_VERDICT_REASON["model_warns"].split(" The reason is below")[0]
                    + " " + whys[0].rstrip(".") + ".")
        if cause == "low_reliability" and str(regime or "").lower() == "financial":
            out["no_verdict_reason"] = (
                "This is valued as a financial — book value times a justified price-to-book "
                "from its return on equity, not a cash-flow model — and our model rates its "
                "own reliability for this kind of company as low, so we are not publishing a "
                "verdict off it.")

    # ---- THE TWO READS, one line each, from `score.business_quality` and
    # ---- `score.price_vs_model` -- the bands the page already renders. They are passed in as
    # ---- STRINGS rather than looked up here, so this module cannot drift into a second
    # ---- definition of either band.
    for label, text in (("Business quality", business_quality),
                        ("Price vs our model", price_vs_model)):
        if str(text or "").strip():
            out["reads"].append({"label": label, "text": str(text).strip()})

    # ---- WHAT THE PRICE ASSUMES: `price_assumes.lead.sentence`, REUSED AND NOT REBUILT.
    # `price_assumes()` already composes that sentence and already handles the financial
    # branch (a bank's question is return on equity, not growth). A second copy here would be
    # two definitions of one sentence -- `B7` -- and they would drift the first time either
    # was reworded.
    out["price_assumes"] = str(assumes_sentence or "").strip()

    # ---- THE WARNING, read from the fields the engine actually emits. My first cut looked for
    # `text` or `note`, which `dcf_warning` does not emit at all -- so it would have shown no
    # warning while one was active, and an absent warning and an unreadable one look identical
    # on a page. `warn` is the boolean; `headline` is the sentence; `why` is the list of
    # reasons, and it ships so the card can say WHICH rule fired rather than only that one did.
    w = (warning or {})
    if w.get("warn"):
        out["warning"] = str(w.get("headline") or "").strip()
        out["warning_why"] = [str(x) for x in (w.get("why") or []) if str(x).strip()]
        out["warning_triggers"] = [str(x) for x in (w.get("triggers") or []) if str(x).strip()]
    else:
        out["warning"] = ""
        out["warning_why"] = []
        out["warning_triggers"] = []
    return out


def for_template() -> dict:
    """The constants a template needs, so no wording is retyped in HTML or JavaScript."""
    return {"rule": RULE_SENTENCE, "labels": dict(LABEL),
            "confidence_means": dict(CONFIDENCE_MEANS),
            "no_verdict_reasons": dict(NO_VERDICT_REASON), "source": SOURCE}


def contains_banned(text: str) -> list:
    """Which banned phrases appear in `text`, as WORDS. `[]` is the passing answer.

    **WORD-BOUNDARY MATCHING WITH DECLARED EXCEPTIONS, NOT A SUBSTRING SCAN.** A substring ban
    on "buy" flags "buyback" and "buyer"; a substring ban on "hold" flags "shareholder" and
    "holdings". This project's most repeated test defect is a substring ban firing on correct
    prose, so the exceptions are NAMED and removed first, and what remains is matched on word
    boundaries.
    """
    import re
    s = " " + " ".join(str(text or "").lower().split()) + " "
    for ex in BANNED_EXCEPTIONS:
        s = s.replace(ex, " ")
    hits = []
    for phrase in BANNED:
        if re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", s):
            hits.append(phrase)
    return sorted(set(hits))
