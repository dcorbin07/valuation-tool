"""
Advisory optimizer — Claude proposes, the held-out data decides.

Mirrors the self-review in your screener project: it's advisory, sample-aware, and
mechanism-driven, never curve-fit. It splits the panel into a discovery half and an
untouched holdout half. From the discovery half's factor ICs it generates candidate
weightings (a positive-IC tilt heuristic, plus — if a key is set — Claude's
mechanism-driven proposals). Each candidate is then judged ONLY on the holdout, and
a change is adopted only if it beats the current weights out-of-sample. Below a
minimum sample it refuses to conclude anything.
"""
from __future__ import annotations

import json

from ..backtest.optimize import _standardize_per_date, _composite_col
from ..backtest.engine import factor_ic, information_coefficient


def _holdout_ic(std, weights, factor_cols, ret_col="fwd_ret", date_col="date"):
    d = std.copy()
    d["__c"] = _composite_col(d, weights, factor_cols)
    return information_coefficient(d, "__c", ret_col, date_col)["mean_ic"]


def _heuristic_candidates(factor_cols, fic):
    cands = []
    pos = {c: max(0.0, fic.get(c, 0.0) or 0.0) for c in factor_cols}
    tot = sum(pos.values())
    if tot > 0:
        cands.append({"weights": {c: round(pos[c] / tot, 3) for c in factor_cols},
                      "rationale": "Tilt toward factors with positive in-sample information coefficient.",
                      "source": "heuristic"})
    cands.append({"weights": {c: round(1.0 / len(factor_cols), 3) for c in factor_cols},
                  "rationale": "Equal-weight baseline.", "source": "heuristic"})
    return cands


def _claude_candidates(factor_cols, fic, current, cfg):
    import anthropic
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    prompt = (
        "You tune factor weights for a stock-ranking model. Be conservative and "
        "mechanism-driven — do NOT overfit, do not zero out a factor without a real "
        "reason, keep weights between 0 and 0.6, and they must sum to 1.\n"
        f"Factors: {factor_cols}\n"
        f"Current weights: {json.dumps(current)}\n"
        f"In-sample factor information coefficients (higher = more predictive): {json.dumps({k: round(v, 4) for k, v in fic.items()})}\n\n"
        "Propose up to 3 alternative weightings, each with a one-sentence rationale grounded in the ICs. "
        "Return ONLY minified JSON: [{\"weights\":{...},\"rationale\":\"...\"}]"
    )
    msg = client.messages.create(model=cfg.ai_model_anthropic, max_tokens=700,
                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(getattr(b, "text", "") for b in msg.content).strip()
    if text.startswith("```"):
        text = text.strip("`"); text = text[text.find("["):]
    s, e = text.find("["), text.rfind("]")
    data = json.loads(text[s:e + 1])
    out = []
    for d in data:
        if isinstance(d, dict) and isinstance(d.get("weights"), dict):
            out.append({"weights": {k: float(v) for k, v in d["weights"].items()},
                        "rationale": str(d.get("rationale", "")), "source": "claude"})
    return out


def propose_and_validate(panel, factor_cols, cfg, current_weights=None, min_sample_dates=30) -> dict:
    dates = sorted(panel["date"].unique())
    if len(dates) < min_sample_dates:
        return {"proposals": [], "adopted": None,
                "note": f"Only {len(dates)} rebalance dates — too few to conclude anything "
                        f"(need ≥ {min_sample_dates}). No change (sample-aware)."}

    mid = dates[len(dates) // 2]
    disc = panel[panel["date"] < mid]
    hold = panel[panel["date"] >= mid]
    fic = factor_ic(disc, factor_cols)
    current = current_weights or {c: 1.0 / len(factor_cols) for c in factor_cols}

    cands = _heuristic_candidates(factor_cols, fic)
    if cfg and cfg.resolved_ai_provider == "anthropic" and cfg.anthropic_api_key:
        try:
            cands += _claude_candidates(factor_cols, fic, current, cfg)
        except Exception:
            pass

    std_hold = _standardize_per_date(hold, factor_cols)
    base_ic = _holdout_ic(std_hold, current, factor_cols)

    scored = []
    for cand in cands:
        w = cand["weights"]
        if set(w) != set(factor_cols) or abs(sum(w.values()) - 1.0) > 0.06:
            continue
        ic = _holdout_ic(std_hold, w, factor_cols)
        scored.append({**cand, "holdout_ic": (float(ic) if ic == ic else None)})
    scored.sort(key=lambda x: (x["holdout_ic"] is not None, x["holdout_ic"] or -9), reverse=True)

    adopted = None
    if scored and scored[0]["holdout_ic"] is not None and scored[0]["holdout_ic"] > 0 \
            and scored[0]["holdout_ic"] > base_ic + 1e-4:
        adopted = scored[0]

    return {"factor_ic_discovery": {k: round(v, 4) for k, v in fic.items()},
            "baseline_holdout_ic": round(base_ic, 4) if base_ic == base_ic else None,
            "proposals": scored, "adopted": adopted,
            "note": ("Adopted a weighting that beat the current one on the untouched holdout half."
                     if adopted else
                     "No proposal beat current weights out-of-sample — keeping current (this is the anti-overfit guard working).")}
