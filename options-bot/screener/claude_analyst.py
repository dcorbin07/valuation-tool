"""
claude_analyst.py — the AI layer.

  deep_dive()    : Opus 4.8 qualitative read on a fresh top candidate (web search on).
  self_review()  : advisory, anti-overfit review of the track record.

Both return (text, cost_usd). Cost is computed from the API usage so the daily
cost breaker can track real spend.
"""

import json
import config as C


def _cost(model, usage):
    """Approximate $ cost from usage. Rates in config — verify at claude.com/pricing."""
    rates = C.MODEL_RATES.get(model, {"in": 15.0, "out": 75.0})
    cin = (getattr(usage, "input_tokens", 0) / 1e6) * rates["in"]
    cout = (getattr(usage, "output_tokens", 0) / 1e6) * rates["out"]
    searches = getattr(getattr(usage, "server_tool_use", None), "web_search_requests", 0) or 0
    return cin + cout + searches * C.WEB_SEARCH_COST_PER_USE


def _call(model, prompt, api_key, use_search=True, max_tokens=1600):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    def extract(resp):
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
        return text, _cost(model, resp.usage)

    if use_search:
        try:
            resp = client.messages.create(
                model=model, max_tokens=max_tokens,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
                messages=[{"role": "user", "content": prompt}])
            t, c = extract(resp)
            if t:
                return t, c
        except Exception:
            pass
    resp = client.messages.create(model=model, max_tokens=max_tokens,
                                  messages=[{"role": "user", "content": prompt}])
    return extract(resp)


# ---------------------------------------------------------------------------
#  Deep dive
# ---------------------------------------------------------------------------

def deep_dive(d, score, api_key):
    bucket = score.bucket
    comp = ", ".join(f"{k} {v:.0f}" for k, v in score.components.items())
    prompt = f"""You are a sharp, skeptical equity analyst. A quantitative screen flagged this {bucket.upper()} small/mid-cap. Give a qualitative read on what the numbers can't show. Be concrete, flag uncertainty, do NOT give buy/sell advice.

{d.get('name')} ({d['ticker']}) | {d.get('sector')}
Composite score {score.composite}/100 ({comp})
Revenue ${(d.get('revenue') or 0)/1e9:.2f}B | Operating income ${(d.get('operating_income') or 0)/1e9:.2f}B | Rev growth {(d.get('latest_rev_growth') or 0)*100:.0f}%
Net debt ${(d.get('net_debt') or 0)/1e9:.2f}B

Use web search for current conditions, then answer briefly:
1. Industry direction — expanding, mature, or declining?
2. Position in the trend — direct player or a picks-and-shovels/derivative play on a bigger theme?
3. Disruption risk to the business or its market.
4. Backing & dependence — reliance on big customers, government contracts/subsidies, a dominant partner?
5. Do the numbers mislead — cyclical peak, one-time item, value trap, or (for unprofitable names) a credible path to profitability vs. a cash-burn risk?
6. Strongest bear case vs strongest bull case (2-3 sentences each).
End with the single most important thing to verify before acting."""
    return _call(C.DIVE_MODEL, prompt, api_key, use_search=True)


# ---------------------------------------------------------------------------
#  Self-review (advisory, anti-overfit)
# ---------------------------------------------------------------------------

def self_review(track_rows, api_key):
    """
    track_rows: list of dicts with at least
      {run_date, ticker, bucket, composite, components, ret_30, bench_iwm_30, bench_ijr_30, ...}
    Returns advisory suggestions; refuses to over-conclude on a small sample.
    """
    n = len(track_rows)
    if n < C.SELF_REVIEW_MIN_SAMPLE:
        return (f"Insufficient sample for reliable conclusions: {n} logged picks "
                f"(need >= {C.SELF_REVIEW_MIN_SAMPLE}). No changes recommended — keep logging.",
                0.0)

    sample = json.dumps(track_rows[-300:], default=str)[:14000]
    prompt = f"""You are a quantitative researcher reviewing a stock screen's live track record. Your job is to find ROBUST, MECHANISM-BASED lessons — NOT to curve-fit to noise. {n} picks logged.

Strict rules:
- Distinguish signal from noise. With this sample, only flag patterns that are large, consistent, and have a plausible CAUSAL mechanism. If a pattern could be luck, say so.
- Returns are measured vs the Russell 2000 (IWM) and S&P SmallCap 600 (IJR) — judge OUTPERFORMANCE, not absolute return in a rising market.
- NEVER propose numeric weight tweaks fit to past returns (that is overfitting). Propose STRUCTURAL changes only: categories of opportunity we're systematically blind to, signals we under/over-use for a clear reason, or gem types our buckets miss.
- Explicitly separate "what we can conclude" from "what needs more data."

Track record (JSON):
{sample}

Provide: (1) what's working / not, with effect sizes and a noise caveat; (2) any systematic blind spots (e.g. a category of missed gems) and the mechanism; (3) at most 2 STRUCTURAL suggestions, each with its rationale and a way to validate it out-of-sample; (4) what you can't yet conclude. This is advisory — a human approves before anything changes."""
    return _call(C.REVIEW_MODEL, prompt, api_key, use_search=False, max_tokens=1800)
