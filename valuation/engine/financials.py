"""
Valuation lens for banks / insurers / financials.

An unlevered FCFF DCF doesn't fit a bank — debt (deposits, borrowings) is raw
material, not financing, so "free cash flow to the firm" is meaningless. The
standard approach is a **justified price-to-book from ROE**, which falls straight
out of the Gordon/residual-income identity:

    P/B = (ROE − g) / (Ke − g)          fair equity value = P/B × book value

A bank that earns its cost of equity is worth ~1× book; earning above it is worth
a premium, below it a discount. Transparent, robust, and the right tool here.
"""
from __future__ import annotations

from typing import Optional

from ..data.models import CompanyData


def justified_pb(roe: float, ke: float, g: float) -> Optional[float]:
    """Justified price-to-book = (ROE − g) / (Ke − g), bounded to a sane range.
    Returns None if the denominator is degenerate (Ke not safely above g)."""
    if ke is None or (ke - g) <= 0.005:
        return None
    pb = (roe - g) / (ke - g)
    return max(0.2, min(pb, 6.0))


def financial_fair_value(cd: CompanyData, ke: float, g: float,
                         roe_override: Optional[float] = None) -> Optional[float]:
    """Per-share fair value for a financial via justified P/B × book value/share."""
    eq, sh, ni = cd.total_equity, cd.shares_diluted, cd.net_income
    if not (eq and eq > 0 and sh and sh > 0):
        return None
    roe = roe_override if roe_override is not None else (ni / eq if ni is not None else None)
    if roe is None:
        return None
    # Keep g safely below both Ke and ROE so the multiple stays well-behaved.
    caps = [g]
    if ke:
        caps.append(ke - 0.005)
    caps.append(max(0.0, roe) * 0.9)
    g = min(caps)
    pb = justified_pb(roe, ke, g)
    if pb is None:
        return None
    return (eq / sh) * pb


def financial_scenarios(cd: CompanyData, ke: float, g: float):
    """(bear, base, bull) per-share by flexing ROE ±20%. None if not computable."""
    eq, sh, ni = cd.total_equity, cd.shares_diluted, cd.net_income
    if not (eq and eq > 0 and sh and sh > 0 and ni is not None):
        return None
    roe = ni / eq
    base = financial_fair_value(cd, ke, g, roe)
    if base is None:
        return None
    bear = financial_fair_value(cd, ke, g, roe * 0.8) or base * 0.8
    bull = financial_fair_value(cd, ke, g, roe * 1.2) or base * 1.2
    return bear, base, bull


# ------------------------------------------------------------------------------------------
# THE DERIVED SURFACES, ON THE MODEL THAT ACTUALLY PRODUCED THE HEADLINE
# ------------------------------------------------------------------------------------------
# WHY THESE EXIST. `pipeline` replaces the headline per-share values with the justified
# P/B-ROE model for a financial, and then went on running the FCFF Monte Carlo, the FCFF
# sensitivity grid and the FCFF reverse DCF on `base` -- the unlevered cash-flow assumptions
# `blend.py`'s own comment says never apply here. Measured on KNSL 2026-09-30: the headline read
# pb_roe $291.03 against a $323.25 price (-10%), while the score's drivers said "Monte Carlo:
# 100% of trials value it above the price" -- a statement about a model carrying weight ZERO in
# that company's fair value, and worth 0.30 of the valuation subscore.
#
# EVERY ONE OF THESE CALLS `financial_fair_value` RATHER THAN RE-DERIVING `pb x bvps` (B7).
# That function caps `g` below both Ke and ROE before applying the multiple, and a second copy
# of the arithmetic would drop that capping and produce a distribution the headline cannot
# reach -- which is the same class of defect as the FCFF surfaces being fixed here.


def _bvps(cd) -> Optional[float]:
    eq, sh = cd.total_equity, cd.shares_diluted
    if not (eq and eq > 0 and sh and sh > 0):
        return None
    return eq / sh


def _roe(cd) -> Optional[float]:
    eq, ni = cd.total_equity, cd.net_income
    if not (eq and eq > 0) or ni is None:
        return None
    return ni / eq


def pb_roe_monte_carlo(cd: CompanyData, ke: float, g: float, trials: int = 10000,
                       roe_sd: float = 0.20, ke_sd: float = 0.15, seed: int = 12345) -> dict:
    """Monte Carlo on the justified-P/B model: perturb ROE and Ke, not free cash flow.

    `roe_sd` and `ke_sd` are RELATIVE, because an absolute standard deviation that suits a 20%
    ROE is nonsense at 4%. A draw whose `Ke` falls at or below `g` is SKIPPED rather than
    clamped: that is an undefined model, not a pessimistic case, and clamping it would quietly
    replace the adverse tail a reader cares about with a boundary value.

    Returns `{}` when the inputs do not support the model -- never a fabricated distribution.
    """
    import random

    roe, bvps = _roe(cd), _bvps(cd)
    if roe is None or bvps is None or ke is None:
        return {}

    rng = random.Random(seed)
    vals = []
    for _ in range(max(1, int(trials))):
        r = roe * (1.0 + rng.gauss(0.0, roe_sd))
        k = ke * (1.0 + rng.gauss(0.0, ke_sd))
        if k is None or k - g <= 0.005:
            continue
        v = financial_fair_value(cd, k, g, roe_override=r)
        if v is not None and v > 0:
            vals.append(v)
    if not vals:
        return {}

    vals.sort()

    def q(f):
        return vals[min(len(vals) - 1, max(0, int(round(f * (len(vals) - 1)))))]

    out = {"model": "justified P/B from ROE", "trials": len(vals),
           "p10": q(0.10), "p50": q(0.50), "p90": q(0.90),
           "mean": sum(vals) / len(vals),
           "inputs": {"roe": roe, "cost_of_equity": ke, "terminal_growth": g,
                      "book_value_per_share": bvps,
                      "roe_sd_relative": roe_sd, "ke_sd_relative": ke_sd}}
    price = cd.price
    if price and price > 0:
        out["prob_undervalued"] = sum(1 for v in vals if v > price) / float(len(vals))
    return out


def pb_roe_sensitivity(cd: CompanyData, ke: float, g: float,
                       roe_steps=(-0.25, -0.125, 0.0, 0.125, 0.25),
                       ke_steps=(-0.02, -0.01, 0.0, 0.01, 0.02)) -> dict:
    """A fair-value grid over ROE (relative steps) and cost of equity (absolute steps)."""
    roe, bvps = _roe(cd), _bvps(cd)
    if roe is None or bvps is None or ke is None:
        return {}
    rows = []
    for dr in roe_steps:
        rows.append([financial_fair_value(cd, ke + dk, g, roe_override=roe * (1.0 + dr))
                     for dk in ke_steps])
    return {"model": "justified P/B from ROE",
            "roe_axis": [roe * (1.0 + d) for d in roe_steps],
            "ke_axis": [ke + d for d in ke_steps],
            "grid": rows, "book_value_per_share": bvps, "base_roe": roe}


def implied_roe(cd: CompanyData, ke: float, g: float) -> dict:
    """The ROE today's price-to-book requires, under the SAME justified-P/B formula.

    **THIS IS THE REVERSE QUESTION A FINANCIAL ACTUALLY POSES.** The FCFF reverse DCF asks what
    revenue growth and margin the price implies; for a bank or insurer that is as inapplicable
    as the FCFF DCF itself. Inverting `P/B = (ROE - g)/(Ke - g)` gives
    `ROE = P/B x (Ke - g) + g`, so the answer is in the model's own terms.

    **IT IS SOLVED RATHER THAN ALGEBRAICALLY INVERTED**, because `financial_fair_value` caps `g`
    and bounds the multiple to [0.2, 6.0]: a closed-form inverse would ignore both and report an
    ROE the forward model could never turn back into today's price. A bisection on the real
    function cannot disagree with it. When the price sits outside the bounded model's reachable
    range that is REPORTED, not extrapolated.
    """
    roe, bvps = _roe(cd), _bvps(cd)
    price = cd.price
    if bvps is None or not price or price <= 0 or ke is None:
        return {}

    lo, hi = -0.50, 2.00
    v_lo = financial_fair_value(cd, ke, g, roe_override=lo)
    v_hi = financial_fair_value(cd, ke, g, roe_override=hi)
    if v_lo is None or v_hi is None:
        return {}

    out = {"model": "implied ROE from justified P/B", "current_pb": price / bvps,
           "cost_of_equity": ke, "terminal_growth": g, "book_value_per_share": bvps}
    if roe is not None:
        out["current_roe"] = roe

    if price < min(v_lo, v_hi) or price > max(v_lo, v_hi):
        out["implied_roe"] = None
        out["out_of_range"] = (
            "today's price of %.2f sits outside the bounded model's reachable range "
            "[%.2f, %.2f], because the justified multiple is capped at [0.2, 6.0]; no ROE "
            "inside [-50%%, 200%%] reproduces it" % (price, min(v_lo, v_hi), max(v_lo, v_hi)))
        return out

    for _ in range(80):
        mid = (lo + hi) / 2.0
        v = financial_fair_value(cd, ke, g, roe_override=mid)
        if v is None:
            break
        if (v > price) == (v_hi > v_lo):
            hi = mid
        else:
            lo = mid
    need = (lo + hi) / 2.0
    out["implied_roe"] = need
    if roe is not None:
        out["gap_pp"] = (need - roe) * 100.0
    return out
