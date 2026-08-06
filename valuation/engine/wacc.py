"""
WACC — cost of capital, built live.

Cost of equity via CAPM (live risk-free rate + beta * equity risk premium).
Cost of debt from the company's own interest/debt when available, otherwise a
synthetic rating spread inferred from interest coverage (Damodaran's method).
Weights use market value of equity and (book as proxy for market) debt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..data.models import CompanyData

# Interest-coverage -> default spread over the risk-free rate (approx. Damodaran,
# large-cap). Ordered high-coverage (safe) to low-coverage (risky).
_SYNTHETIC_SPREAD = [
    (12.5, 0.0063), (9.5, 0.0078), (7.5, 0.0098), (6.0, 0.0108), (4.5, 0.0122),
    (4.0, 0.0156), (3.5, 0.0200), (3.0, 0.0240), (2.5, 0.0351), (2.0, 0.0421),
    (1.5, 0.0515), (1.25, 0.0820), (0.8, 0.0864), (0.5, 0.1134), (-1e9, 0.1512),
]


def _synthetic_spread(coverage: Optional[float]) -> float:
    if coverage is None:
        return 0.02  # default BBB-ish
    for threshold, spread in _SYNTHETIC_SPREAD:
        if coverage >= threshold:
            return spread
    return 0.15


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


@dataclass
class WACCResult:
    wacc: float
    cost_of_equity: float
    cost_of_debt_pretax: float
    cost_of_debt_aftertax: float
    beta: float
    risk_free: float
    erp: float
    weight_equity: float
    weight_debt: float
    tax_rate: float
    market_value_equity: float
    market_value_debt: float
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__


# Blume/Bloomberg "adjusted beta": b_adj = w*b_raw + (1-w)*1.0, w = 0.67. None = off
# (today's behaviour). Note the existing sanity check above only rejects beta <= 0 or
# > 3.0 — it has no low-side floor, so a beta of 0.08 passes as plausible.
BETA_SHRINK = None


def compute_wacc(cd: CompanyData, cfg, rf: Optional[float] = None,
                 beta_override: Optional[float] = None,
                 erp_override: Optional[float] = None) -> WACCResult:
    notes = []
    rf = rf if rf is not None else (cd.risk_free_rate if cd.risk_free_rate is not None else cfg.default_risk_free)
    erp = erp_override if erp_override is not None else cfg.equity_risk_premium
    tax = cfg.marginal_tax_rate

    # Beta: sanitize (Yahoo betas are noisy; unlevered names sometimes missing).
    beta = beta_override if beta_override is not None else cd.beta
    if beta is None or beta <= 0 or beta > 3.0:
        beta = 1.10
        notes.append("Beta missing/implausible; used 1.10.")
    if BETA_SHRINK is not None:
        beta = BETA_SHRINK * beta + (1.0 - BETA_SHRINK) * 1.0
    ke = rf + beta * erp

    # Cost of debt.
    kd = None
    if cd.interest_expense and cd.total_debt and cd.total_debt > 0:
        kd = cd.interest_expense / cd.total_debt
        if not (rf + 0.001 <= kd <= rf + 0.12):
            kd = None  # implausible; fall back to synthetic
    if kd is None:
        kd = rf + _synthetic_spread(cd.interest_coverage)
        notes.append("Cost of debt from synthetic rating (interest-coverage spread).")
    kd = _clamp(kd, rf + 0.002, rf + 0.15)
    kd_at = kd * (1 - tax)

    # Weights (market value of equity; book debt as a proxy for market debt).
    mve = cd.market_cap if cd.market_cap else (
        (cd.price or 0) * (cd.shares_diluted or 0))
    mvd = cd.total_debt or 0.0
    total = mve + mvd
    if total <= 0:
        we, wd = 1.0, 0.0
        notes.append("No capital-structure data; assumed 100% equity.")
    else:
        we, wd = mve / total, mvd / total

    wacc = we * ke + wd * kd_at
    wacc_raw = wacc
    wacc = _clamp(wacc, 0.04, 0.25)
    if abs(wacc - wacc_raw) > 1e-9:
        notes.append(f"WACC clamped to sane band (raw {wacc_raw:.2%}).")

    return WACCResult(
        wacc=wacc, cost_of_equity=ke, cost_of_debt_pretax=kd, cost_of_debt_aftertax=kd_at,
        beta=beta, risk_free=rf, erp=erp, weight_equity=we, weight_debt=wd, tax_rate=tax,
        market_value_equity=mve, market_value_debt=mvd, notes=notes,
    )
