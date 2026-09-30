"""
Optional AI qualitative layer.

Given the full quantitative valuation, an LLM (Anthropic Claude by default, or
OpenAI) writes the parts a DCF can't: an economic-moat read, the key risks and
catalysts, a bull and bear thesis, and — most usefully — a critique of the
tool's own auto-generated assumptions (e.g. "your 27% terminal margin is well
above this company's 9% five-year average").

If no API key is configured, a transparent rule-based fallback produces the same
structure directly from the numbers, so the tool is always fully functional.
"""
from __future__ import annotations

import json
import logging
import re
from statistics import median

_log = logging.getLogger(__name__)

#: Anything that looks like a provider key, redacted before a failure reason is logged or
#: rendered. The reasons below never interpolate the key -- this is the belt to that braces,
#: because a provider's own exception text is not ours to vouch for.
_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,})")


def _safe(msg: object) -> str:
    """A failure reason fit to log and to show a user. Never carries a key."""
    return _KEY_RE.sub("sk-***", str(msg))


class AIReplyError(RuntimeError):
    """The provider answered and the answer was not usable.

    **WHY THIS EXISTS RATHER THAN A BARE `json.JSONDecodeError`.** Measured live on
    valquo.co 2026-09-30, `/api/value` reported `rule-based (no AI key configured) (AI call
    failed: Expecting value: line 1 column 1 (char 0))` -- which is `json.loads("")`, and says
    nothing about WHY the text was empty. Three different conditions produce that identical
    string and they want different responses:

    * `stop_reason == "max_tokens"` -- adaptive thinking consumed the whole budget, so the
      turn carries a thinking block and no text. Raise `max_tokens`.
    * `stop_reason == "refusal"` -- the safety classifiers declined; HTTP 200, `content` empty.
      Retrying the same prompt is pointless.
    * a reply that is prose rather than JSON -- the prompt needs tightening.

    A decode error reports none of them, so the reason is constructed where it is known.
    """


# --------------------------------------------------------------------------- #
# Prompt construction
# --------------------------------------------------------------------------- #
def _facts(result) -> dict:
    cd = result.company
    a = result.assumptions
    sc = result.scenarios
    return {
        "ticker": cd.ticker, "name": cd.name, "sector": cd.sector, "industry": cd.industry,
        "price": cd.price, "regime": result.classification.regime,
        "revenue_mm": cd.revenue, "revenue_growth_ttm": cd.rev_growth_ttm,
        "revenue_cagr_3y": cd.rev_cagr_3y, "operating_margin": cd.ebit_margin,
        "gross_margin": cd.gross_margin, "fcf_margin": cd.fcf_margin,
        "roic": cd.roic, "wacc": result.wacc.wacc, "net_debt_to_ebitda": cd.net_debt_to_ebitda,
        "cash_runway_years": cd.cash_runway_years, "rule_of_40": result.classification.rule_of_40,
        "base_fair_value": sc.base.per_share, "bear": sc.bear.per_share, "bull": sc.bull.per_share,
        "upside_pct": (result.upside * 100 if result.upside is not None else None),
        # The prompt is given only surfaces that APPLY. Feeding it the FCFF reverse DCF for an
        # insurer is how a narrative comes to argue revenue growth for a company valued on book.
        "prob_undervalued": (result.montecarlo.prob_undervalued
                             if result.montecarlo is not None else None),
        "comps_fair_value": result.comps.comps_fair_value,
        "reverse_dcf_implied_growth": (result.reverse.implied_avg_growth
                                       if result.reverse is not None else None),
        "assumed_start_growth": a.start_growth, "assumed_terminal_growth": a.terminal_growth,
        "assumed_target_margin": a.target_margin, "assumed_current_margin": a.current_margin,
        "hist_operating_margins": [m for m in (cd.ebit_margin_history or []) if m is not None][:5],
        "tv_pct_of_ev": sc.base.tv_pct_of_ev, "score": result.score.score,
        "recommendation": result.score.recommendation,
    }


_SCHEMA = {
    "business_summary": "2-3 sentence plain-English description of what the company does and its position",
    "moat": {"rating": "Wide | Narrow | None", "text": "1-2 sentences justifying it"},
    "key_risks": ["3-5 concrete, company-specific risks"],
    "catalysts": ["2-4 things that could re-rate the stock"],
    "bull_thesis": "3-4 sentences making the strongest evidence-based bull case",
    "bear_thesis": "3-4 sentences making the strongest evidence-based bear case",
    "assumption_critique": ["2-4 specific critiques of the tool's assumptions vs history/reality"],
    "overall_take": "2-3 sentence balanced synthesis; reference the score and the main tension",
}


def _build_prompt(result) -> str:
    facts = _facts(result)
    return (
        "You are a rigorous, skeptical equity research analyst. You are NOT a "
        "cheerleader: be balanced, cite the numbers, and flag where the model's "
        "automated assumptions look aggressive or too conservative.\n\n"
        "Here is a quantitative DCF valuation of a company (all $ in millions, "
        "rates as decimals):\n"
        f"{json.dumps(facts, indent=2, default=str)}\n\n"
        "Return ONLY valid minified JSON matching exactly this schema (no prose, "
        "no code fences):\n"
        f"{json.dumps(_SCHEMA)}\n"
    )


# --------------------------------------------------------------------------- #
# Provider calls
# --------------------------------------------------------------------------- #
#: Output budget for the analyst turn. **1600 WAS THE LIVE DEFECT, NOT A PREFERENCE.**
#: `max_tokens` caps thinking AND response text together, and on the configured
#: `claude-sonnet-5` adaptive thinking is ON whenever the `thinking` parameter is omitted
#: (a change from Sonnet 4.6, which ran thinking-off by default). The schema below asks for
#: eight fields including four multi-sentence theses, so at 1600 the model could spend the
#: whole budget reasoning and return `stop_reason: "max_tokens"` with a thinking block and no
#: text at all -- and since `thinking.display` also defaults to `"omitted"` on this model, that
#: block's own text is empty too. `"".join(getattr(b, "text", ""))` then yields `""`.
#:
#: Thinking is deliberately NOT disabled to buy the budget back: on this model a
#: thinking-disabled turn can leak `<thinking>` tags into the visible text, which is strictly
#: worse for something whose next step is `json.loads`.
_MAX_TOKENS = 8000


def _call_anthropic(prompt: str, cfg) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    msg = client.messages.create(
        model=cfg.ai_model_anthropic, max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    source = f"Claude ({cfg.ai_model_anthropic})"

    # THE STOP REASON IS READ BEFORE THE CONTENT, because two of its values mean the content
    # cannot be parsed and say why. Reading `content` first turns both into a decode error.
    stop = getattr(msg, "stop_reason", None)
    if stop == "refusal":
        det = getattr(msg, "stop_details", None)
        cat = getattr(det, "category", None) if det is not None else None
        raise AIReplyError(
            "the provider declined the request (stop_reason=refusal, category=%s); the reply "
            "carries no content and retrying the same prompt will not change that"
            % (cat or "unspecified"))

    text = "".join(getattr(b, "text", "") for b in msg.content)
    if not text.strip() and stop == "max_tokens":
        raise AIReplyError(
            "the reply carried no text: the %d-token budget was consumed before any was "
            "written (stop_reason=max_tokens, %d content block(s))"
            % (_MAX_TOKENS, len(msg.content or [])))
    return _parse_json(text, source, stop_reason=stop, blocks=len(msg.content or []))


def _call_openai(prompt: str, cfg) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.chat.completions.create(
        model=cfg.ai_model_openai, max_tokens=1600,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    choices = list(resp.choices or [])
    if not choices:
        raise AIReplyError("the provider returned no choices")
    ch = choices[0]
    return _parse_json(ch.message.content, f"OpenAI ({cfg.ai_model_openai})",
                       stop_reason=getattr(ch, "finish_reason", None), blocks=len(choices))


def _parse_json(text: str, source: str, stop_reason=None, blocks=None) -> dict:
    """Recover the JSON object from a model reply, or fail with a reason a human can act on.

    Handles a fenced block (```json ... ```), leading or trailing prose, and a reply that is a
    JSON object with text either side of it. What it will NOT do is hand an empty string to
    `json.loads` and let the decoder narrate the failure -- an empty reply is its own condition
    with its own cause, and the decoder cannot see the cause.
    """
    t = (text or "").strip()
    if not t:
        raise AIReplyError(
            "the reply was empty (stop_reason=%s, %s content block(s)); nothing was returned to "
            "parse" % (stop_reason or "unreported",
                       "unreported" if blocks is None else blocks))

    # A fence may be ```json, ``` or ~~~, and may be unterminated when the turn was cut short.
    # Taking the span between the first `{` and the last `}` handles every one of those plus
    # bare prose either side, so the fence is stripped by CONSEQUENCE rather than by pattern --
    # `t.strip("`")` alone mangles a reply whose JSON legitimately ends in a backtick.
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise AIReplyError(
            "the reply contained no JSON object (stop_reason=%s); it began %r"
            % (stop_reason or "unreported", t[:120]))
    obj = t[start:end + 1]

    try:
        data = json.loads(obj)
    except ValueError as e:
        raise AIReplyError(
            "the reply's JSON did not parse (stop_reason=%s): %s; it began %r"
            % (stop_reason or "unreported", _safe(e), obj[:120]))
    # DEFENCE IN DEPTH, AND UNREACHABLE FROM THE RULE ABOVE -- said rather than pretended.
    # The span runs from the first `{` to the last `}`, so a bare array or scalar is already
    # refused as "no JSON object" and cannot arrive here. Mutation showed a test claiming to
    # exercise this branch was really exercising that one. It stays because it is free and
    # becomes live the moment the extraction rule is relaxed.
    if not isinstance(data, dict):
        raise AIReplyError("the reply parsed to %s rather than an object" % type(data).__name__)
    data["source"] = source
    return data


# --------------------------------------------------------------------------- #
# Rule-based fallback (no API key needed)
# --------------------------------------------------------------------------- #
def _pct(x, nd=0):
    return f"{x*100:.{nd}f}%" if x is not None else "n/a"


#: What the fallback says about itself when there is genuinely no key. It is the DEFAULT, not
#: the only value, because the live payload read `rule-based (no AI key configured) (AI call
#: failed: ...)` -- two mutually exclusive claims in one string, on an account where a key IS
#: configured. A reader who trusted the first clause would have gone looking for a missing
#: environment variable that was never missing.
_NO_KEY = "rule-based (no AI key configured)"


def _financial_narrative(result, moat, risks, catalysts, uw, source) -> dict:
    """Bull, bear, critique and take for a bank or insurer, in book-value terms.

    Reads `result.financial_surfaces` where the pipeline built it -- the justified-P/B Monte
    Carlo and the implied-ROE reverse question -- and derives the same three inputs straight
    from the filings when it did not, so a narrative is produced either way rather than
    silently reverting to the FCFF wording this function exists to avoid.
    """
    cd, cls, a, sc = result.company, result.classification, result.assumptions, result.scenarios
    surf = dict(getattr(result, "financial_surfaces", None) or {})
    rev = dict(surf.get("reverse") or {})

    ke = getattr(result.wacc, "cost_of_equity", None)
    g = a.terminal_growth
    eq, sh, ni = cd.total_equity, cd.shares_diluted, cd.net_income
    bvps = rev.get("book_value_per_share")
    if bvps is None and eq and sh and eq > 0 and sh > 0:
        bvps = eq / sh
    roe = rev.get("current_roe")
    if roe is None and eq and eq > 0 and ni is not None:
        roe = ni / eq

    pb_now = (cd.price / bvps) if (bvps and bvps > 0 and cd.price) else None
    implied = rev.get("implied_roe")

    def _m(x):
        return f"${x:,.2f}" if x is not None else "n/a"

    bull = (f"In the bull case the shares are worth ~{_m(sc.bull.per_share)} "
            f"({(sc.bull.per_share/cd.price-1)*100:+.0f}% vs {_m(cd.price)}) if the firm sustains "
            f"a return on equity near {_pct(roe)} against a {_pct(ke)} cost of equity and keeps "
            f"compounding book value, which is what a justified price-to-book multiple pays for. "
            f"Book value per share is {_m(bvps)} today.")
    bear = (f"In the bear case fair value is ~{_m(sc.bear.per_share)} "
            f"({(sc.bear.per_share/cd.price-1)*100:+.0f}%) if returns on equity fade toward the "
            f"{_pct(ke)} cost of equity, at which point the justified multiple collapses toward "
            f"book value — the model is far more sensitive to the ROE-minus-cost-of-equity spread "
            f"than to any single year's earnings.")

    crit = []
    if pb_now is not None:
        crit.append(f"The shares trade at {pb_now:.2f}x book against book value per share of "
                    f"{_m(bvps)}; the whole answer is whether that multiple is justified.")
    if implied is not None and roe is not None:
        crit.append(f"Today's price requires a sustained ROE of ~{_pct(implied)} under the same "
                    f"justified-P/B formula, against {_pct(roe)} earned now — a gap of "
                    f"{(implied-roe)*100:+.1f} percentage points that has to be closed for the "
                    "price to be right.")
    elif rev.get("out_of_range"):
        crit.append("No return on equity inside a plausible range reproduces today's price under "
                    "the justified price-to-book formula, so the multiple is doing work the "
                    "model cannot account for: " + str(rev["out_of_range"]))
    if ke is not None and g is not None:
        crit.append(f"The justified multiple divides by the {_pct(ke)} cost of equity less "
                    f"{_pct(g,1)} long-run growth, so both are load-bearing: a percentage point "
                    "on either moves the answer materially.")
    crit.append("Free-cash-flow and operating-margin assumptions do not enter this valuation — "
                "for a bank or insurer the unlevered cash-flow model is not applied, so any "
                "margin or growth figure shown elsewhere is reference-only.")
    if cls.dcf_reliability == "low":
        crit.append("DCF reliability is LOW for this profile, which is expected here rather than "
                    "a warning: the discounted-cash-flow lens is not the one being used.")

    take = (f"On the model, {cd.name} looks {uw} ({_m(sc.base.per_share)} base fair value vs "
            f"{_m(cd.price)}), scoring {result.score.score}/100 → "
            f"{result.score.recommendation}. The central tension is whether the return on equity "
            f"it earns justifies the multiple the market pays for its book; confidence in this "
            f"valuation is {result.score.confidence}.")

    return {
        "source": source,
        "business_summary": (f"{cd.name} operates in {cd.industry or cd.sector or 'financials'} "
                             f"and is valued on a justified price-to-book multiple built from a "
                             f"{_pct(roe)} return on equity against a {_pct(ke)} cost of equity, "
                             f"rather than on discounted free cash flow."),
        "moat": moat, "key_risks": risks, "catalysts": catalysts,
        "bull_thesis": bull, "bear_thesis": bear, "assumption_critique": crit,
        "overall_take": take,
    }


def _rule_based(result, source: str = _NO_KEY) -> dict:
    cd, cls, a, sc = result.company, result.classification, result.assumptions, result.scenarios
    hist = [m for m in (cd.ebit_margin_history or []) if m is not None]
    hist_med = median(hist) if hist else None

    # Moat from value-creation spread + gross margin.
    spread = (cd.roic - result.wacc.wacc) if (cd.roic is not None) else None
    if spread is not None and spread > 0.08 and (cd.gross_margin or 0) > 0.45:
        moat = {"rating": "Wide", "text": f"ROIC of {_pct(cd.roic)} sits well above the {_pct(result.wacc.wacc)} "
                f"cost of capital on {_pct(cd.gross_margin)} gross margins — signs of durable pricing power."}
    elif spread is not None and spread > 0.0:
        moat = {"rating": "Narrow", "text": f"ROIC {_pct(cd.roic)} modestly exceeds WACC {_pct(result.wacc.wacc)}; "
                "some competitive advantage but not a fortress."}
    else:
        moat = {"rating": "None", "text": "Returns on capital do not clearly exceed the cost of capital — "
                "no evident economic moat on the current numbers."}

    risks = []
    if cls.is_cash_burning:
        rw = cd.cash_runway_years
        risks.append(f"Cash-burning with ~{rw:.1f} years of runway — dilution/financing risk if losses persist."
                     if rw is not None else "Cash-burning with limited visibility on the path to breakeven.")
    if cd.net_debt_to_ebitda is not None and cd.net_debt_to_ebitda > 3:
        risks.append(f"Elevated leverage (net debt/EBITDA {cd.net_debt_to_ebitda:.1f}x).")
    # A PRICED-FOR-OPTIMISM RISK BUILT ON THE REVERSE DCF IS ONLY AVAILABLE WHERE THAT MODEL
    # APPLIES. `result.reverse` is `None` for a financial, and a risk bullet is part of a
    # verdict-shaped narrative, so inheriting one from an inapplicable model is the same defect
    # as letting it into the score.
    _rv = result.reverse
    if _rv is not None and _rv.implied_avg_growth is not None and _rv.base_avg_growth is not None \
            and _rv.implied_avg_growth - _rv.base_avg_growth > 0.03:
        risks.append(f"Priced for optimism: the market implies ~{_pct(_rv.implied_avg_growth)} growth "
                     f"vs our {_pct(_rv.base_avg_growth)} base — little margin for error.")
    if a.target_margin - a.current_margin > 0.04:
        risks.append(f"Value hinges on margin expansion from {_pct(a.current_margin)} to {_pct(a.target_margin)} — "
                     "execution risk if it stalls.")
    if sc.base.tv_pct_of_ev > 0.80:
        risks.append(f"{_pct(sc.base.tv_pct_of_ev)} of value sits in the terminal value — sensitive to long-run assumptions.")
    if cls.regime == "cyclical":
        risks.append("Cyclical end-markets: margins and demand can swing sharply with the economic cycle.")
    if not risks:
        risks.append("No single dominant risk stands out on the numbers; monitor competitive and demand trends.")

    catalysts = []
    if a.target_margin > a.current_margin + 0.01:
        catalysts.append("Operating-margin recovery toward the modeled target.")
    if cls.regime in ("growth", "hypergrowth"):
        catalysts.append("Operating leverage as revenue scales over fixed costs.")
        catalysts.append("Crossing into sustained positive free cash flow.")
    # NOT FOR A BANK OR INSURER, AND THE REASON IS THAT `net_debt` DOES NOT MEAN WHAT IT MEANS
    # ELSEWHERE THERE. Deposits, policy reserves and float are OPERATING liabilities, not
    # borrowings, so a financial's computed net debt can come back negative while the firm holds
    # no distributable cash whatsoever -- and the sentence this guard removes would then assert
    # buyback capacity out of an accounting artifact. Buybacks at a regulated financial are
    # gated on regulatory capital, which this model does not read at all.
    if cd.net_debt is not None and cd.net_debt < 0 and cls.regime != "financial":
        catalysts.append("Net-cash balance sheet supports buybacks / opportunistic M&A.")
    if not catalysts:
        catalysts.append("Multiple re-rating if results beat conservative expectations.")

    uw = "undervalued" if (result.upside or 0) > 0.10 else ("overvalued" if (result.upside or 0) < -0.10 else "roughly fairly valued")

    # ------------------------------------------------------------------------------------
    # A FINANCIAL'S NARRATIVE IS WRITTEN IN ITS OWN MODEL'S TERMS
    # ------------------------------------------------------------------------------------
    # The prose below this block argues from start growth, target operating margin and the
    # terminal-value share of enterprise value -- every one of them an input to the unlevered
    # FCFF model, which carries weight ZERO in a financial's fair value. Left unbranched it
    # produced a bull case citing a revenue-growth and margin ramp for an insurer whose headline
    # came from a justified price-to-book multiple, and a critique of a "target operating margin"
    # that never entered the answer. The quantities that DID produce it are book value per share,
    # ROE and the cost of equity, so those are what a financial's narrative cites.
    if cls.regime == "financial":
        return _financial_narrative(result, moat, risks, catalysts, uw, source)

    bull = (f"In the bull case the shares are worth ~${sc.bull.per_share:,.2f} "
            f"({(sc.bull.per_share/cd.price-1)*100:+.0f}% vs ${cd.price:,.2f}) if growth holds near "
            f"{_pct(a.start_growth)} and margins reach {_pct(a.target_margin)}. "
            f"{'A long reinvestment runway and' if cls.regime in ('growth','hypergrowth') else 'Steady cash generation and'} "
            f"{'improving' if a.target_margin>a.current_margin else 'resilient'} profitability drive the upside.")
    bear = (f"In the bear case fair value is ~${sc.bear.per_share:,.2f} "
            f"({(sc.bear.per_share/cd.price-1)*100:+.0f}%) if growth disappoints and margins stall near today's "
            f"{_pct(cd.ebit_margin)}. With {_pct(sc.base.tv_pct_of_ev)} of value in the terminal period, small "
            "changes to long-run assumptions move the answer a lot.")

    crit = []
    if hist_med is not None and a.target_margin - hist_med > 0.03:
        crit.append(f"Target operating margin {_pct(a.target_margin)} is above the ~{_pct(hist_med)} historical median — "
                    "verify this is achievable.")
    if hist_med is not None and a.target_margin < hist_med - 0.03:
        crit.append(f"Target margin {_pct(a.target_margin)} sits below the ~{_pct(hist_med)} historical median — "
                    "possibly conservative.")
    if a.terminal_growth >= (result.wacc.risk_free or 0.03):
        crit.append(f"Terminal growth {_pct(a.terminal_growth,1)} is at/above the risk-free rate — aggressive for a perpetuity.")
    crit.append(f"Growth fades from {_pct(a.start_growth)} to {_pct(a.terminal_growth,1)} over {a.n_years} years; "
                "the fade path is a simplification.")
    if cls.dcf_reliability == "low":
        crit.append("DCF reliability is LOW for this profile — lean on the comps and reverse-DCF cross-checks.")

    take = (f"On the model, {cd.name} looks {uw} (${sc.base.per_share:,.2f} base fair value vs ${cd.price:,.2f}), "
            f"scoring {result.score.score}/100 → {result.score.recommendation}. "
            f"The central tension is {'whether the growth/margin ramp justifies the price' if cls.regime in ('growth','hypergrowth') else 'valuation versus business quality'}; "
            f"confidence in the DCF here is {result.score.confidence}.")

    return {
        "source": source,
        "business_summary": (f"{cd.name} operates in {cd.industry or cd.sector or 'its sector'} and is modeled as a "
                             f"{cls.regime} company growing revenue ~{_pct(cls.blended_growth)} with "
                             f"{_pct(cd.ebit_margin)} operating margins."),
        "moat": moat, "key_risks": risks, "catalysts": catalysts,
        "bull_thesis": bull, "bear_thesis": bear, "assumption_critique": crit, "overall_take": take,
    }


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def _failed_source(provider: str, model: str, e: BaseException) -> str:
    """The fallback's label when a key WAS configured and the call failed anyway.

    It names the provider, the model it tried, the exception CLASS and the redacted reason --
    and it never says "no AI key configured", because that sentence was measured false on the
    live service while being printed beside the failure that disproved it.
    """
    return "rule-based (%s %s call failed: %s: %s)" % (
        provider, model or "unspecified model", type(e).__name__, _safe(e))


def analyze(result, cfg) -> dict:
    provider = cfg.resolved_ai_provider
    if provider == "anthropic" and cfg.anthropic_api_key:
        try:
            return _call_anthropic(_build_prompt(result), cfg)
        except Exception as e:
            # The CLASS is logged as well as the message: `AIReplyError` means the provider
            # answered and we could not use it, while `AuthenticationError` or a connection
            # error mean the call never landed. Those want different fixes and the message
            # alone does not separate them. `_safe` guarantees no key reaches the log.
            _log.warning("AI analyst call failed: %s: %s", type(e).__name__, _safe(e))
            return _rule_based(result,
                               _failed_source("Anthropic", cfg.ai_model_anthropic, e))
    if provider == "openai" and cfg.openai_api_key:
        try:
            return _call_openai(_build_prompt(result), cfg)
        except Exception as e:
            _log.warning("AI analyst call failed: %s: %s", type(e).__name__, _safe(e))
            return _rule_based(result, _failed_source("OpenAI", cfg.ai_model_openai, e))
    # NO KEY FOR THE RESOLVED PROVIDER -- the one state in which the default label is true.
    return _rule_based(result)
