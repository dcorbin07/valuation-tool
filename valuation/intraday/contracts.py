"""
Contract ideas for a bullish signal, by horizon.

Rules-based *guides*, not live-chain picks (a live chain per name needs a paid
feed and is heavy at scale). From the underlying price and ATM implied vol we
frame an expiry band, an expected 1-sigma move, and two ways to express the view:
a simple directional call and a defined-risk put credit spread (your options-bots
style). Strikes are guides to confirm against the real chain.
"""
from __future__ import annotations

from typing import Optional

HORIZONS = ("short", "swing", "position")

_DTE = {"short": (21, 35), "swing": (45, 75), "position": (90, 180)}   # days to expiry
_CALL_DELTA = {"short": 40, "swing": 35, "position": 30}
_SHORT_PUT_DELTA = {"short": 30, "swing": 25, "position": 20}


def contract_idea(price: Optional[float], iv: Optional[float], horizon: str = "swing",
                  direction: str = "bull") -> Optional[dict]:
    if not price or price <= 0:
        return None
    lo, hi = _DTE.get(horizon, _DTE["swing"])
    mid = (lo + hi) // 2
    ivv = iv if (iv and iv > 0) else 0.30                 # fallback IV when the chain is thin
    em = price * ivv * (mid / 365.0) ** 0.5               # ~1-sigma move over ~mid DTE
    em_pct = em / price
    width = max(1.0, round(price * 0.05))                 # ~5%-wide spread, min $1
    cdelta = _CALL_DELTA.get(horizon, 35)
    sdelta = _SHORT_PUT_DELTA.get(horizon, 25)
    if direction == "bear":
        short_call = round(price + em, 2)                 # ~1-sigma OTM short call
        long_call = round(short_call + width, 2)
        directional = f"~{cdelta}Δ put, ~{mid} DTE"
        defined_risk = (f"Call credit spread: sell ~${short_call} call / buy ~${long_call} "
                        f"(~${int(width)} wide), ~{mid} DTE")
    else:
        short_put = round(price - em, 2)                  # ~1-sigma OTM short put
        long_put = round(short_put - width, 2)
        directional = f"~{cdelta}Δ call, ~{mid} DTE"
        defined_risk = (f"Put credit spread: sell ~${short_put} put / buy ~${long_put} "
                        f"(~${int(width)} wide), ~{mid} DTE")
    return {
        "horizon": horizon,
        "direction": direction,
        "dte_range": [lo, hi],
        "expected_move_pct": round(em_pct, 4),
        "expected_move_abs": round(em, 2),
        "directional": directional,
        "defined_risk": defined_risk,
        "note": (f"~1σ move ±{em_pct:.0%} over ~{mid} days; ~{sdelta}Δ short strike. "
                 f"Guides only — confirm on the live chain."),
    }
