"""
Options-context signals from an option-chain summary.

Not a full flow tape (that needs a paid feed) — but from Tradier's chain data we
get put/call volume, open interest, and at-the-money implied volatility, which
give a real read on positioning: call-heavy vs put-heavy flow, unusually active
call volume vs open interest, and the IV regime (which matters directly for your
put-spread entries). All None-safe: no chain → returns a neutral 50.
"""
from __future__ import annotations


def _clamp(x, lo=0, hi=100):
    return float(max(lo, min(hi, x)))


def options_signals(opt: dict | None) -> dict:
    if not opt:
        return {"score": 50.0, "labels": [], "detail": {}, "available": False}
    labels, score = [], 50.0
    pv, cv = opt.get("put_volume"), opt.get("call_volume")
    poi, coi = opt.get("put_oi"), opt.get("call_oi")
    iv = opt.get("atm_iv")
    pcr = None

    if pv is not None and cv is not None and (pv + cv) > 0:
        pcr = pv / max(cv, 1)
        if pcr < 0.7:
            score += 12; labels.append(f"Call-heavy flow (P/C {pcr:.2f})")
        elif pcr > 1.4:
            score -= 10; labels.append(f"Put-heavy flow (P/C {pcr:.2f})")

    if cv and coi and coi > 0 and (cv / coi) > 0.5:
        score += 8; labels.append("Unusual call volume vs OI")

    if iv is not None:
        if iv > 0.6:
            labels.append(f"High IV {iv:.0%} (rich premium)")
        elif iv < 0.2:
            labels.append(f"Low IV {iv:.0%}")

    return {"score": _clamp(score), "labels": labels, "available": True,
            "detail": {"put_call_ratio": pcr, "atm_iv": iv,
                       "call_volume": cv, "put_volume": pv}}
