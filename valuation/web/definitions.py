"""PLAIN DEFINITIONS FOR THE PAGE'S OWN JARGON — one module, one wording.  [item 53 part 4]

WHY THIS MODULE EXISTS
----------------------
The valuation page asks a reader to act on words it never defines: *discount rate*, *base
value*, *Rule of 40*, *what the price assumes*, *hot score*. Item 52 replaced the Buy/Hold
label with two plain reads, which makes the remaining jargon more load-bearing rather than
less — a reader who is no longer handed a verdict has to understand the inputs.

THE SHAPE IS `score_confidence.py`'S, AND THAT IS DELIBERATE
------------------------------------------------------------
One module owns the wording, every surface reads it, and a test pins it. The alternative —
`title=` strings written inline next to each number — is how the same term comes to be defined
two different ways on one page, which is the `B7` family applied to prose.

WHAT A DEFINITION HERE MAY AND MAY NOT DO
-----------------------------------------
It explains what a number IS. It does not say whether the number is good, does not recommend
anything, and does not restate a calibrated hedge in looser words. Where a term already has
calibrated language elsewhere — the hot score's limits in `score_confidence.py`, the DCF
warning in `price_assumes.py` — the definition here says what the thing is and POINTS at the
calibrated sentence rather than paraphrasing it. A paraphrase of a hedge is how a hedge
becomes a claim, which is `score_confidence`'s own stated reason for being quoted verbatim.

**NO NUMBERS THAT MOVE.** A definition carrying "the 10-year Treasury is 5.28%" would be wrong
within weeks and nothing would fail. Live figures belong on the page, beside the number they
describe; these sentences explain the KIND of thing it is. The one exception is the Rule of 40's
own bar of 40, which is the definition — the rule is named for it.
"""
from __future__ import annotations

#: term -> (short label, plain definition). The label is what a surface may use as a heading;
#: the definition is the hover text. Both are quoted verbatim by `tests/test_definitions.py`.
#:
#: Written for somebody who has not read a finance textbook and is not pretending otherwise.
DEFINITIONS = {
    "dcf": (
        "Discounted cash flow (DCF)",
        "A way of valuing a company by estimating the cash it will produce in future years "
        "and then discounting those amounts back to today, because money arriving in ten "
        "years is worth less than money arriving now. The answer depends heavily on the "
        "growth you assume and on the discount rate, so two reasonable people can get very "
        "different numbers from the same company."
    ),
    "discount_rate": (
        "Discount rate (WACC)",
        "The annual return this company's investors and lenders would expect, used to convert "
        "future cash into today's money. A higher rate means a lower value, because future "
        "cash is being penalised more. It is built from the risk-free rate, the extra return "
        "expected from shares generally, and this company's own beta — so a volatile share "
        "price pushes the rate up and the value down, without anybody forming a view about "
        "the business."
    ),
    "beta": (
        "Beta",
        "How much this share price has moved relative to the market. A beta of 1.0 moves with "
        "the market; 2.0 has historically moved about twice as much in both directions. It is "
        "a measurement of past price movement, not a judgement about the company, and it "
        "feeds straight into the discount rate above."
    ),
    "base_value": (
        "Base value",
        "What our model thinks one share is worth under its middle set of assumptions — not "
        "the optimistic case and not the pessimistic one. It is an estimate from a model, not "
        "a price target and not a forecast of where the share price will go."
    ),
    "rule_of_40": (
        "Rule of 40",
        "Revenue growth plus profit margin, added together, for a fast-growing company. The "
        "idea is that growth and profitability trade off against each other, so a company "
        "scoring 40 or more on the two combined is considered to be managing the trade-off "
        "well. It is an industry rule of thumb from software investing, not a law."
    ),
    "reverse_dcf": (
        "What the price assumes",
        "The same cash-flow model run backwards: instead of asking what the company is worth, "
        "it asks what growth rate would make today's share price exactly right. Comparing "
        "that with what the business actually grows is often more useful than a single fair "
        "value, because it turns the question into one you can judge."
    ),
    "margin_of_safety": (
        "Margin of safety",
        "The gap between our base value and the current price, as a percentage. Positive means "
        "the model's estimate sits above the price. It is the gap between a price and an "
        "estimate, so it is only as good as the estimate."
    ),
    "hot_score": (
        "Hot score",
        "A 0-100 ranking of this company against every other name in the daily scan, built "
        "from the themes listed beside it. It is a RANKING, not a forecast and not a price "
        "target: it says where this name sits today relative to the others scanned. What the "
        "evidence behind it does and does not support is set out in the limits shown with it, "
        "which are measured and deliberately not reworded here."
    ),
    "themes": (
        "Themes",
        "The groups of measurements the ranking is built from — value, quality, growth, "
        "momentum, size, insider buying, institutional ownership and capital discipline. Each "
        "is scored against the rest of the scan on the day, so every number is relative to "
        "the other names rather than absolute. Where a theme could not be scored for a "
        "company, the ranking spreads its weight over the others and the page says so."
    ),
    "sub_scores": (
        "Sub-scores",
        "The five 0-100 components behind the main valuation score: quality, growth, financial "
        "health, momentum and valuation. They are scored against thresholds this model sets, "
        "not against other companies, and the weights differ by company type — a fast-growing "
        "company's score leans on growth where a mature one's leans on valuation."
    ),
    "business_quality": (
        "Business quality",
        "A plain read of the four sub-scores that describe the COMPANY rather than its price: "
        "quality, growth, financial health and momentum. It deliberately excludes valuation, "
        "so a good business at a high price reads as a good business at a high price instead "
        "of averaging out to something in the middle."
    ),
    "price_vs_model": (
        "Price vs our model",
        "How today's share price compares with our base value, as a plain percentage or "
        "multiple. It is one number against one estimate; where the model does not suit the "
        "company, the page says so above rather than leaving this to be read as a verdict."
    ),
    "monte_carlo": (
        "Monte Carlo",
        "The same model run thousands of times with the assumptions varied randomly within "
        "plausible ranges, to see how often the answer lands above today's price. It shows how "
        "sensitive the estimate is to its own inputs. It does not add information the model "
        "did not already have."
    ),
    "comps": (
        "Comparable companies (comps)",
        "An estimate built from what the market pays for similar companies — their earnings "
        "and sales multiples applied to this one. It is shown beside the cash-flow estimate as "
        "an independent read, and is not blended into it."
    ),
}

#: Which of the above carry calibrated language that lives elsewhere, so a surface can point
#: at it rather than this module restating it. Values are a human description of where.
POINTS_ELSEWHERE = {
    "hot_score": "score_confidence.py (the measured limits, quoted verbatim from V3's handoff)",
    "reverse_dcf": "price_assumes.py (the DCF warning and the story-stock rule)",
    "price_vs_model": "price_assumes.py (the DCF warning and the story-stock rule)",
}

#: Terms this module must cover, because item 53 part 4 names them. A LITERAL rather than
#: `DEFINITIONS.keys()`, which is `MA13`'s idiom: a test that iterates the thing it pins
#: cannot notice a deletion. Removing a term from `DEFINITIONS` must go red.
REQUIRED = ("dcf", "discount_rate", "base_value", "rule_of_40", "reverse_dcf",
            "hot_score", "sub_scores")


def label(term: str) -> str:
    """The short heading for a term, or "" if it is not defined here."""
    got = DEFINITIONS.get(str(term or ""))
    return got[0] if got else ""


def text(term: str) -> str:
    """The plain definition, or "" if it is not defined here.

    Empty string rather than a placeholder: a surface rendering "" shows nothing, where a
    surface rendering "(no definition)" shows a reader that the page is broken.
    """
    got = DEFINITIONS.get(str(term or ""))
    return got[1] if got else ""


def payload() -> dict:
    """Every definition, for the one place that hands them to the page.

    A single dict so the client has ONE object to read and nothing has to know which terms
    exist -- adding a term here makes it available on the page without a second edit.
    """
    return {k: {"label": v[0], "text": v[1],
                "calibrated_elsewhere": POINTS_ELSEWHERE.get(k, "")}
            for k, v in DEFINITIONS.items()}
