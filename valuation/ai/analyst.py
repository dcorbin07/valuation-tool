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
from statistics import median


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
        "prob_undervalued": result.montecarlo.prob_undervalued,
        "comps_fair_value": result.comps.comps_fair_value,
        "reverse_dcf_implied_growth": result.reverse.implied_avg_growth,
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
def _call_anthropic(prompt: str, cfg) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    msg = client.messages.create(
        model=cfg.ai_model_anthropic, max_tokens=1600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(getattr(b, "text", "") for b in msg.content)
    return _parse_json(text, f"Claude ({cfg.ai_model_anthropic})")


def _call_openai(prompt: str, cfg) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.chat.completions.create(
        model=cfg.ai_model_openai, max_tokens=1600,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _parse_json(resp.choices[0].message.content, f"OpenAI ({cfg.ai_model_openai})")


def _parse_json(text: str, source: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        t = t[start:end + 1]
    data = json.loads(t)
    data["source"] = source
    return data


# --------------------------------------------------------------------------- #
# Rule-based fallback (no API key needed)
# --------------------------------------------------------------------------- #
def _pct(x, nd=0):
    return f"{x*100:.{nd}f}%" if x is not None else "n/a"


def _rule_based(result) -> dict:
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
    if result.reverse.implied_avg_growth is not None and result.reverse.base_avg_growth is not None \
            and result.reverse.implied_avg_growth - result.reverse.base_avg_growth > 0.03:
        risks.append(f"Priced for optimism: the market implies ~{_pct(result.reverse.implied_avg_growth)} growth "
                     f"vs our {_pct(result.reverse.base_avg_growth)} base — little margin for error.")
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
    if cd.net_debt is not None and cd.net_debt < 0:
        catalysts.append("Net-cash balance sheet supports buybacks / opportunistic M&A.")
    if not catalysts:
        catalysts.append("Multiple re-rating if results beat conservative expectations.")

    uw = "undervalued" if (result.upside or 0) > 0.10 else ("overvalued" if (result.upside or 0) < -0.10 else "roughly fairly valued")
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
        "source": "rule-based (no AI key configured)",
        "business_summary": (f"{cd.name} operates in {cd.industry or cd.sector or 'its sector'} and is modeled as a "
                             f"{cls.regime} company growing revenue ~{_pct(cls.blended_growth)} with "
                             f"{_pct(cd.ebit_margin)} operating margins."),
        "moat": moat, "key_risks": risks, "catalysts": catalysts,
        "bull_thesis": bull, "bear_thesis": bear, "assumption_critique": crit, "overall_take": take,
    }


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def analyze(result, cfg) -> dict:
    provider = cfg.resolved_ai_provider
    if provider == "anthropic" and cfg.anthropic_api_key:
        try:
            return _call_anthropic(_build_prompt(result), cfg)
        except Exception as e:
            out = _rule_based(result)
            out["source"] += f"  (AI call failed: {e})"
            return out
    if provider == "openai" and cfg.openai_api_key:
        try:
            return _call_openai(_build_prompt(result), cfg)
        except Exception as e:
            out = _rule_based(result)
            out["source"] += f"  (AI call failed: {e})"
            return out
    return _rule_based(result)
