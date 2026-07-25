"""
AI reasoning for the top intraday setups — bounded cost.

One Claude call covers the whole top-N (not N calls), so each refresh costs a few
cents at most. Claude gets each name's score, pattern labels, and key indicator
values and returns a crisp one-liner: why it's a setup + the main risk. Without a
key it falls back to a rule-based sentence from the labels, so it always returns
something.
"""
from __future__ import annotations

import json


def explain_top(rows: list, cfg, n: int = 10) -> dict:
    top = rows[:n]
    if not top:
        return {}

    if cfg.resolved_ai_provider == "anthropic" and cfg.anthropic_api_key:
        try:
            return _anthropic(top, cfg)
        except Exception:
            pass
    # rule-based fallback
    return {r["ticker"]: _fallback(r) for r in top}


def _fallback(r) -> str:
    labs = ", ".join(r.get("labels", [])[:4]) or "no standout pattern"
    return f"{r.get('summary', '')}. Signals: {labs}."


def _anthropic(top, cfg) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    compact = [{"ticker": r["ticker"], "score": r["score"], "labels": r.get("labels", []),
                "rsi": (r.get("detail") or {}).get("rsi"),
                "macd_hist": (r.get("detail") or {}).get("macd_hist"),
                "above_200dma": (r.get("detail") or {}).get("above_200dma"),
                "dist_52w_high": (r.get("detail") or {}).get("dist_52w_high"),
                "options_score": r.get("options_score")} for r in top]
    prompt = (
        "You are a disciplined trading assistant. For each stock below you get an "
        "intraday technical/options setup score (0-100) and the detected signals. "
        "For EACH ticker, write ONE crisp sentence: what the setup is and the single "
        "biggest risk to it. Be concrete, no hype, and never promise profit.\n\n"
        f"{json.dumps(compact, default=str)}\n\n"
        "Return ONLY minified JSON mapping ticker -> sentence."
    )
    msg = client.messages.create(model=cfg.ai_model_anthropic, max_tokens=900,
                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(getattr(b, "text", "") for b in msg.content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    s, e = text.find("{"), text.rfind("}")
    data = json.loads(text[s:e + 1])
    return {k: str(v) for k, v in data.items()}
