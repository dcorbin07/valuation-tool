"""
Combine technical + options-context signals into one intraday buy-setup score.

Technical carries most of the weight (it's the more reliable, higher-coverage
input); options context tilts and confirms. Returns a blended 0-100 score, the
merged pattern labels, and a short human-readable summary of the setup.
"""
from __future__ import annotations

from .technical import technical_signals
from .options import options_signals

W_TECH = 0.70
W_OPT = 0.30

# Horizon reweights the technical/options blend and adds a small tilt:
#   short    — leans on options flow + fresh breakouts (faster setups)
#   swing    — the balanced default
#   position — leans on durable trend (200-DMA), fades overbought chasing
_HORIZON_WEIGHTS = {"short": (0.60, 0.40), "swing": (0.70, 0.30), "position": (0.82, 0.18)}


def evaluate(bars: dict, option_summary: dict | None = None, horizon: str = "swing") -> dict:
    tech = technical_signals(bars)
    opt = options_signals(option_summary)

    if tech.get("score") is None:
        return {"score": None, "labels": [], "note": tech.get("note", "no data"),
                "technical": tech, "options": opt}

    w_tech, w_opt = _HORIZON_WEIGHTS.get(horizon, _HORIZON_WEIGHTS["swing"])
    if opt.get("available"):
        score = w_tech * tech["score"] + w_opt * opt["score"]
    else:
        score = tech["score"]

    # Horizon tilt.
    d = tech.get("detail", {})
    if horizon == "position":
        if d.get("above_200dma"):
            score += 3
        if d.get("rsi") is not None and d["rsi"] > 75:
            score -= 3          # don't chase an extended name for a longer hold
    elif horizon == "short":
        if any(("Breakout" in l or "Volume surge" in l) for l in tech.get("labels", [])):
            score += 3
    score = max(0.0, min(100.0, score))

    labels = list(tech["labels"]) + list(opt["labels"])
    return {
        "score": round(float(score), 1),
        "labels": labels,
        "technical_score": tech["score"],
        "options_score": opt["score"] if opt.get("available") else None,
        "detail": {**tech.get("detail", {}), **{f"opt_{k}": v for k, v in opt.get("detail", {}).items()}},
        "summary": _summary(score, labels),
    }


def _summary(score, labels) -> str:
    strength = "strong" if score >= 70 else ("constructive" if score >= 58 else
                                             ("neutral" if score >= 45 else "weak"))
    lead = labels[0] if labels else "no standout pattern"
    return f"{strength.capitalize()} setup — {lead}" + (f" (+{len(labels) - 1} more)" if len(labels) > 1 else "")
