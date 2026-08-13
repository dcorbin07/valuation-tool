"""What the Dip Detector is allowed to say, gated on the V6 register.

WHY THIS IS A MODULE AND NOT A PARAGRAPH IN A TEMPLATE
------------------------------------------------------
The Dip Detector screens for healthy companies trading well below their 52-week high. The
screen is measurement. The INTERESTING claim — that such names go on to recover, that the
drawdown is "just sentiment", that it "will pass" — is a statement about forward returns that
nothing in this repository has measured. The pipeline lane is pre-registering it as **V6**.

So the tab has to say something true in the meantime, and it has to STOP saying it the day the
register closes. Prose in a template does not stop; someone has to remember. This project's
own record is the argument: the public landing page rendered a pre-B6 `+17.4%/yr` for weeks
because the figure lived in a config dict nobody thought to grep, and `/methodology` still
calls the Deflated Sharpe "undeflated" more than a week after M1 settled that it is not.

`STATUS` is the one thing the V6 close-out flips. Everything the tab renders is derived from
it. Closing the register is: set `STATUS`, fill `VERDICT_*`, done — and `tests/test_dip.py`
fails until the filled state is internally consistent, so a half-finished flip cannot ship
quietly.

THE THREE STATES
----------------
  OPEN       — the register is running. The tab says the claim is being tested and that this
               is a screen, not a prediction. This is today.
  POSITIVE   — V6 came back positive. The copy upgrades, and it upgrades WITH ITS NUMBERS,
               because an upgraded sentence with no effect size is how "healthy dips recover"
               becomes folklore. `VERDICT_DETAIL` is mandatory in this state.
  NULL       — V6 came back null or negative. The copy SAYS SO. This is the state most likely
               to be quietly skipped, which is exactly why the test requires it to be as
               sayable as POSITIVE. The edge lane's paired-vintage research module makes the
               same move for the same reason: it carries no sign branch at all, so its
               unflattering verdict is exactly as reachable as its flattering one.

               (That module is named here only by description. The V1 outbound fence forbids
               its literal name in any file under `valuation/web` or `valuation/saas`, because
               `PT-OUTBOUND` leaked a research FIGURE to Discord — and a fence that is
               weakened to accommodate a comment praising it would be worth nothing. The fence
               caught this docstring on its first run, which is the fence working.)

WHAT MAY NEVER BE SAID, IN ANY STATE
------------------------------------
`BANNED` is enforced against the RENDERED payload, not against this file, because rendering is
where copy leaks — that was V4's lesson when a research page's publishing rule had to be
asserted line by line against the HTML rather than against the row list. A positive V6 would
license a quantified sentence about a measured population; it would still not license "buy the
dip", which is advice, or "this will pass", which is a promise about one name.
"""
from __future__ import annotations

# --------------------------------------------------------------------------------------- #
# THE ONE CONSTANT THE V6 CLOSE-OUT FLIPS
# --------------------------------------------------------------------------------------- #

OPEN, POSITIVE, NULL = "open", "positive", "null"

#: The state of the V6 register. TODAY: open — pre-registered, not yet run.
STATUS = OPEN

#: The register that governs this copy. Named so the close-out knows where to look, and so a
#: reader can check that the file exists rather than taking the citation on trust.
REGISTER = "PREREG_v6_healthy_drawdown.md"
OWNER_LANE = "pipeline builder"

#: Filled by the close-out. In POSITIVE these carry the effect size and its caveats; in NULL,
#: what was measured and what came back. Left empty in OPEN, and the test pins that.
VERDICT_HEADLINE = ""
VERDICT_DETAIL = ""

# --------------------------------------------------------------------------------------- #
# THE COPY
# --------------------------------------------------------------------------------------- #

#: What the tab IS, in every state. Deliberately a description of a screen and nothing more.
WHAT_IT_IS = ("Companies whose price is well below their own 52-week high while their "
              "fundamentals still score healthy. Each row shows how far the price has fallen "
              "from that high, the sub-scores that cleared the health floor, and the model's "
              "fair-value read for context.")

#: The OPEN explainer. Quoted from the commissioning note so that the sentence the product
#: shows and the sentence the lane agreed to are the same sentence.
OPEN_EXPLAINER = ("Whether healthy names in drawdown actually recover better than the market "
                  "is a testable claim — we are testing it, and this page will say the answer "
                  "when the register closes. Until then this is a screen, not a prediction.")

#: The standing caveat. Survives a POSITIVE verdict, because a measured group average is not a
#: statement about the next name a reader clicks — V3's per-name/group distinction, which the
#: score's own confidence language already had to learn.
ALWAYS = ("A drawdown is a fact about the price. Nothing here says why it happened, and a "
          "cheap-looking healthy company can stay cheap or get cheaper.")


def _open_state() -> dict:
    return {"headline": "This is a screen, not a prediction.",
            "explainer": OPEN_EXPLAINER,
            "verdict": None}


def _closed_state() -> dict:
    return {"headline": VERDICT_HEADLINE,
            "explainer": VERDICT_DETAIL,
            "verdict": STATUS}


def posture() -> dict:
    """Everything the tab renders about what it does and does not claim.

    One payload, one authority. The template and `static/app.js` both read this rather than
    holding copy of their own — the rule `score_confidence` and `theme_status` already follow,
    and the reason the theme legend's hardcoded caption was able to call a live theme dormant.
    """
    state = _open_state() if STATUS == OPEN else _closed_state()
    return {
        "status": STATUS,
        "register": REGISTER,
        "owner_lane": OWNER_LANE,
        "what_it_is": WHAT_IT_IS,
        "always": ALWAYS,
        "headline": state["headline"],
        "explainer": state["explainer"],
        "verdict": state["verdict"],
        # An outbound push of a dip list is a recommendation-shaped message, so it waits for
        # the evidence. Derived from STATUS rather than set by hand: a close-out that upgrades
        # the copy and forgets the digest would otherwise leave the two disagreeing.
        "digest_eligible": STATUS != OPEN,
    }


# --------------------------------------------------------------------------------------- #
# THE POSTURE LINE, ENFORCED
# --------------------------------------------------------------------------------------- #

#: Phrasings that may not appear on this surface in ANY state. Two families, and they are
#: banned for different reasons:
#:
#:   RECOMMENDATION — "buy the dip", "load up". Advice, which this product does not give
#:     anywhere; the whole app is careful about this and the Dip Detector is the surface most
#:     likely to slip, because Don's own phrasing for it was an instruction.
#:
#:   PREDICTION — "will recover", "will pass", "temporary", "oversold", "sentiment-driven".
#:     These assert the V6 claim. Note "sentiment-driven" is banned even though Don used the
#:     phrase: attributing a drawdown to sentiment is a causal claim about why a price moved,
#:     and this screen reads no news, no flow and no positioning. It sees a price and a
#:     balance sheet.
BANNED = (
    "buy the dip", "buy this dip", "load up", "back up the truck", "screaming buy",
    "will recover", "will bounce", "will pass", "will rebound", "bound to recover",
    "due for a bounce", "temporary dip", "temporary setback", "sentiment-driven",
    "sentiment driven", "oversold", "mispriced by the market", "guaranteed", "risk-free",
    "sure thing", "no reason for the fall", "unjustified selloff", "unjustified sell-off",
)


def violations(text: str) -> list:
    """Which banned phrasings appear in `text`. Case-insensitive; substring, not word.

    Substring on purpose: "oversold" has to be caught inside "clearly oversold here", and a
    word-boundary rule would miss hyphenation a copy edit introduces.
    """
    low = (text or "").lower()
    return [p for p in BANNED if p in low]
