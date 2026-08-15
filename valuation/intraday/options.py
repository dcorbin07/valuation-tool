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

    # AUDIT MA38 - the numerator and the denominator must be taken over the SAME contracts.
    # `call_volume` sums every contract in the front expiry; `call_oi` sums only those whose open
    # interest is KNOWN (B4 made it exclude the -1 the cache writes when the OI call failed, which
    # was right). Dividing one by the other inflates the ratio by roughly 1/coverage, so the bonus
    # over-fires. A PRECISION CORRECTION against the audit, which says this fires "where the
    # module's own docstring says the reconstruction cannot": that STRICTER-than-live promise in
    # options_backtest's header is scoped to the VOLUME-SURGE deviation, not a blanket guarantee.
    # What it does break is that docstring's ARGUMENT - that every known deviation runs in the
    # conservative direction, so a surviving edge is not an artifact of one. This was a second
    # deviation running the other way.
    #
    # MEASURED on 11,818 front-expiry chain-days across 12 symbols: 27.3% are PARTIALLY covered
    # (not all-or-nothing, so the `coi > 0` guard below does not already catch it), and 5 of them
    # - 0.04% - cross this 0.5 bar for no reason but the mismatch.
    #
    # The repair is to take both sums over the same rows. The audit proposed two others and
    # BOTH were measured to be far more disruptive than the defect: scaling `coi` by 1/coverage
    # kills 262 otherwise-legitimate fires (52x the defect) and suppressing below 0.9 coverage
    # kills 660 (132x), because volume is CONCENTRATED in the known-OI rows (median +0.44 excess
    # share) - so imputing average OI onto rows that carry far below-average volume is not a
    # neutral correction. No threshold is introduced here, deliberately: an uncalibrated bar is
    # what those two options amount to.
    #
    # `call_volume_oi_known` is absent on the LIVE path (Tradier ships no coverage figure), so
    # the fallback is `cv` and live behaviour is bit-identical to before this change.
    cv_oi = opt.get("call_volume_oi_known")
    cv_num = cv if cv_oi is None else cv_oi
    if cv_num and coi and coi > 0 and (cv_num / coi) > 0.5:
        score += 8; labels.append("Unusual call volume vs OI")

    if iv is not None:
        if iv > 0.6:
            labels.append(f"High IV {iv:.0%} (rich premium)")
        elif iv < 0.2:
            labels.append(f"Low IV {iv:.0%}")

    return {"score": _clamp(score), "labels": labels, "available": True,
            "detail": {"put_call_ratio": pcr, "atm_iv": iv,
                       # carried through for the term-structure filter; not scored here
                       "atm_iv_60d": opt.get("atm_iv_60d"),
                       "call_volume": cv, "put_volume": pv,
                       # AUDIT MA38 - B4 computed these and NOTHING anywhere read them, so the
                       # bonus above rested on a coverage figure no consumer could see. Surfaced
                       # rather than retired, because an OI ratio built on 20% of a chain is not
                       # the same statistic as one built on 100% and a reader is entitled to
                       # know which they have. None on the live path, which ships no coverage.
                       "call_oi_known_frac": opt.get("call_oi_known_frac"),
                       "put_oi_known_frac": opt.get("put_oi_known_frac"),
                       # which numerator the bonus above actually used
                       "oi_ratio_basis": "matched" if opt.get("call_volume_oi_known") is not None
                                         else "whole_chain"}}
