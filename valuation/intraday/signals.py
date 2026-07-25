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


def evaluate(bars: dict, option_summary: dict | None = None) -> dict:
    tech = technical_signals(bars)
    opt = options_signals(option_summary)

    if tech.get("score") is None:
        return {"score": None, "labels": [], "note": tech.get("note", "no data"),
                "technical": tech, "options": opt}

    if opt.get("available"):
        score = W_TECH * tech["score"] + W_OPT * opt["score"]
    else:
        score = tech["score"]

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
