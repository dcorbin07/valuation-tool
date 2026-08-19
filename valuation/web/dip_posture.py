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

TWO REGISTERS, TWO ANSWERS — AND THE WHOLE POINT IS THAT THEY DISAGREE
---------------------------------------------------------------------
V6 asked whether these names go on to BEAT THE MARKET. Four arms, all NULL. That question is
settled and the copy still says so.

V6-B asked a different question of the same population: not "do they go up more" but "do they
go DOWN less". Its M1 arm separated — hugely, and it replicated. So this surface now carries
**one dead claim and one live one**, and the entire risk in the copy is that a reader collapses
them into "healthy dips are good buys". They are not the same claim and neither implies the
other:

  RETURN  (`STATUS`, V6)      — NULL.     "not shown to beat the market"
  RISK    (`RISK_STATUS`, V6-B) — POSITIVE. "fell a further 20% about a quarter less often"

They are two constants rather than one because they are two registers with two verdicts, and
overloading a single `STATUS` would have forced a choice about which one the tab "really" says.
It says both. `headline`/`explainer` stay bound to the RETURN register exactly as before — every
pin written against them still holds — and the risk claim arrives on its own keys beside them.

WHAT V6-B DID *NOT* EARN, AND THIS IS THE SHARPEST EDGE ON THIS FILE
--------------------------------------------------------------------
The metric that separated (M1) is **a further −20% drawdown**. That is DEEPENING. The arm that
measured actual death — bankruptcy, regulatory delisting — is **M2, and it is VOID on power**:
42 distress events against a pre-committed floor of 60. Its point estimate happens to run the
same way and **none of that is quotable**.

So "these names go bust less often" is NOT earned, and the proposed copy "dips like this died
less often" was rejected by the edge lane in its own write-up. `BANNED` now carries a DISTRESS
family for exactly this, and it is banned on the same footing as "buy the dip": both are
sentences the measurement does not support, and the distress one is more tempting precisely
because a true neighbouring result sits next to it.


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

#: The state of the V6 register. CLOSED 2026-08-13: all four arms came back NULL.
STATUS = NULL

#: The register that governs this copy. Named so the close-out knows where to look, and so a
#: reader can check that the file exists rather than taking the citation on trust.
#:
#: CORRECTED AT CLOSE-OUT: this read `PREREG_v6_healthy_drawdown.md`, which never existed —
#: the register was committed as `PREREG_v6_dip_detector.md` (alone at `93e3e60`, before this
#: tab was written). The docstring above says the citation is here so a reader "can check that
#: the file exists rather than taking the citation on trust", and on the shipped value that
#: check would have failed. The two lanes named the same unbuilt thing differently, which is
#: the ordinary cost of registering ahead of a product rather than a defect in either.
REGISTER = "PREREG_v6_dip_detector.md"
OWNER_LANE = "pipeline builder"

# --------------------------------------------------------------------------------------- #
# THE SECOND REGISTER — V6-B, THE RISK QUESTION
# --------------------------------------------------------------------------------------- #

#: The state of the V6-B register. CLOSED 2026-08-13: arm M1 separated and replicated.
#: This is a SEPARATE verdict on a SEPARATE question — see the docstring. It is deliberately
#: not folded into `STATUS`, because the two registers disagree and the surface must say so.
RISK_STATUS = POSITIVE
RISK_REGISTER = "PREREG_v6b_dip_survival.md"

#: The sentence the edge lane registered as the one this tab has earned, quoted from
#: `HANDOFF_edge_audit.md` V6-B §3 ("So the sentence the tab has earned is about falling
#: further, not about dying"). Pinned verbatim by test, and rendered rather than paraphrased:
#: a paraphrase is where "fell another 20% less often" turns into "went bust less often", and
#: §3 exists precisely because that paraphrase was the copy originally proposed.
RISK_REGISTERED_SENTENCE = (
    "Historically, healthy names already down 20% have gone on to fall another 20% about a "
    "quarter less often than unhealthy ones in the same drawdown — 33% of the time against 43%.")

#: The headline. Leads with what was measured and names the population, because "healthy dips
#: are safer" without "than other dips" is a comparison with nothing on the other side.
RISK_HEADLINE = ("Tested: among names already down 20%, the healthy ones fell another 20% "
                 "far less often — 32.5% of the time against 43.4%.")

#: The numbers, the replication, and the two caveats that must travel with them.
RISK_DETAIL = (
    "That is a 10.8-point absolute reduction, or about a quarter fewer in relative terms, "
    "measured on 37,014 drawdown episodes across an 18-year point-in-time panel of 2,531 "
    "companies. It held in both halves of the period separately — 2009-2017 and 2017-2026 — "
    "and it held in all five company-size tiers, though only four of the five also held in "
    "both halves on their own. The effect is LARGEST in the smallest companies and WEAKEST in "
    "the very largest, which is the opposite of where most of this site's coverage sits, so "
    "expect it to be milder for household-name megacaps. And this is one historical panel, "
    "not a forward test.")

#: The distinction, stated on the surface rather than left to inference. This is the sentence
#: that stops a risk result being read as a return result.
RISK_NOT_A_PROMISE = (
    "Read this as a statement about how often things got WORSE, never as a forecast that they "
    "will get better. It says these names fell a further 20% less often than their unhealthy "
    "peers — not that they recovered, and not that they avoided failing outright, which was "
    "measured separately and came back too thin to call either way.")

#: Filled by the close-out. In POSITIVE these carry the effect size and its caveats; in NULL,
#: what was measured and what came back. Left empty in OPEN, and the test pins that.
VERDICT_HEADLINE = ("Tested: healthy names in a drawdown did not measurably beat the market.")
VERDICT_DETAIL = (
    "V6 tested four versions of this screen on an 18-year, 2,531-name point-in-time panel — "
    "20% and 30% below the 52-week high, held for the following three and six months — "
    "against both the whole market and against fallen names carrying no health filter. None "
    "of the four cleared its bar in both halves of the period. Two things travel with that. "
    "The smallest effect the test could reliably have seen was larger than the effect it was "
    "looking for, so the honest reading is 'not shown', not 'shown to be false'. And the "
    "result was negative across 2009-2017 and positive across 2017-2026 — which is why a "
    "screen like this one can look convincing when it is only checked against recent years.")

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
        # --- the SECOND register, on its own keys ---------------------------------------- #
        # Deliberately not merged into `headline`/`explainer`. Those are the RETURN verdict and
        # every existing pin is written against them; a risk result that quietly overwrote the
        # return result's slot would read as though V6 had been revised, which it has not.
        "risk_status": RISK_STATUS,
        "risk_register": RISK_REGISTER,
        "risk_headline": RISK_HEADLINE if RISK_STATUS == POSITIVE else "",
        "risk_detail": RISK_DETAIL if RISK_STATUS == POSITIVE else "",
        "risk_not_a_promise": RISK_NOT_A_PROMISE if RISK_STATUS == POSITIVE else "",
        "risk_sentence": RISK_REGISTERED_SENTENCE if RISK_STATUS == POSITIVE else "",
        # An outbound push of a dip list is a recommendation-shaped message, so it waits for
        # the evidence. Derived from STATUS rather than set by hand: a close-out that upgrades
        # the copy and forgets the digest would otherwise leave the two disagreeing.
        #
        # CHANGED AT THE V6 CLOSE-OUT, `STATUS != OPEN` -> `STATUS == POSITIVE`, and the
        # original is the more interesting half of this comment. The rule that a NULL must be
        # exactly as PUBLISHABLE as a POSITIVE is right, and the copy above still obeys it.
        # But it was carried one step too far: the digest does not push the VERDICT, it pushes
        # a LIST OF NAMES. On `!= OPEN` the arrival of a NULL — evidence that the claim is not
        # supported — would have SILENTLY ENABLED that push, which is this very comment's
        # "waits for the evidence" running backwards. The defect was invisible until a real
        # verdict existed, and it only ever fires in the unflattering branch.
        # ROUTED, not decided: whether the dip list should ever go out is Don's and the app
        # lane's call, and this leaves it exactly where it was rather than opening it.
        #
        # CHANGED AGAIN AT THE V6-B CLOSE-OUT, `STATUS == POSITIVE` -> `RISK_STATUS ==
        # POSITIVE`. That routing came back: Don's call is to ship it now the claim is earned,
        # RISK-FRAMED ONLY. The gate moves to the register that actually earned something,
        # which also means a future revision of V6 — the RETURN question — can no longer
        # unblock an outbound push on its own. That is strictly tighter than what it replaces,
        # and `test_the_digest_is_gated_on_the_RISK_register_and_not_the_return_one` pins both
        # halves: risk drives it, return cannot.
        "digest_eligible": RISK_STATUS == POSITIVE,
        # The digest may not write its own claim. It renders THIS, or it does not send — see
        # `saas/notify.dip_digest_text`, which takes the sentence from here and then re-checks
        # its own finished message against `violations()` before it goes out.
        "digest_claim": RISK_REGISTERED_SENTENCE if RISK_STATUS == POSITIVE else "",
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
#:
#:   DISTRESS — "bankrupt", "goes to zero", "blow up", "died less often". ADDED AT THE V6-B
#:     CLOSE-OUT, and the only family here whose neighbour is TRUE. V6-B's M1 measured a
#:     further −20% fall and separated decisively; its M2 measured actual bankruptcy and
#:     regulatory delisting and is VOID on power at 42 events against a floor of 60. A reader
#:     — or a future copy edit — who slides from "fell further less often" to "went bust less
#:     often" has crossed from a replicated result to an unmeasured one WITHOUT CHANGING THE
#:     SHAPE OF THE SENTENCE. The edge lane's own write-up rejected exactly that wording. This
#:     is the family most likely to be introduced by someone trying to make the true claim
#:     sound punchier, which is why it is enforced against the rendered HTML like the rest.
BANNED = (
    "buy the dip", "buy this dip", "load up", "back up the truck", "screaming buy",
    "will recover", "will bounce", "will pass", "will rebound", "bound to recover",
    "due for a bounce", "temporary dip", "temporary setback", "sentiment-driven",
    "sentiment driven", "oversold", "mispriced by the market", "guaranteed", "risk-free",
    "sure thing", "no reason for the fall", "unjustified selloff", "unjustified sell-off",
    # DISTRESS — V6-B M2 is VOID, so none of this is earned.
    "bankrupt", "insolven", "goes to zero", "go to zero", "went to zero", "goes bust",
    "go bust", "went bust", "blow up", "blows up", "blew up", "wiped out", "wipe out",
    "died less", "die less", "dies less", "less likely to die", "survive better",
    "survives better", "never fails", "avoid the failures", "goes under", "go under",
    "went under", "default less", "defaults less",
)


def violations(text: str) -> list:
    """Which banned phrasings appear in `text`. Case-insensitive; substring, not word.

    Substring on purpose: "oversold" has to be caught inside "clearly oversold here", and a
    word-boundary rule would miss hyphenation a copy edit introduces.
    """
    low = (text or "").lower()
    return [p for p in BANNED if p in low]
