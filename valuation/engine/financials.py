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
