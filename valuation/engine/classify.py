"""
Company classification — the "adaptive" part of the engine.

Different kinds of companies need different DCF assumptions. A mature, cash-
generative firm (Nike, Coca-Cola) is modeled very differently from a fast-
growing cash-burner (early-stage SaaS) or a cyclical (energy, materials). We
detect the regime from the financials and let it drive the assumption logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..data.models import CompanyData

CYCLICAL_SECTORS = {"Energy", "Basic Materials", "Industrials"}
FINANCIAL_SECTORS = {"Financial Services", "Financials", "Financial"}
FINANCIAL_INDUSTRY_HINTS = ("bank", "insurance", "capital markets", "mortgage", "reit—")


@dataclass
class Classification:
    regime: str = "mature"           # mature | growth | hypergrowth | cyclical | financial
    is_cash_burning: bool = False
    blended_growth: Optional[float] = None   # best forward-ish revenue growth estimate
    rule_of_40: Optional[float] = None       # growth% + fcf-margin% (for growth names)
    dcf_reliability: str = "high"    # high | medium | low  (how much to trust the DCF)
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "is_cash_burning": self.is_cash_burning,
            "blended_growth": self.blended_growth,
            "rule_of_40": self.rule_of_40,
            "dcf_reliability": self.dcf_reliability,
            "reasons": self.reasons,
        }


def _blended_growth(cd: CompanyData) -> Optional[float]:
    """A robust forward-ish growth estimate: analyst consensus if available,
    otherwise blend of 3y CAGR and latest YoY, bounded to sane values."""
    candidates = []
    if cd.analyst_rev_growth_next is not None:
        candidates.append(("analyst", cd.analyst_rev_growth_next, 0.5))
    if cd.rev_cagr_3y is not None:
        candidates.append(("3y_cagr", cd.rev_cagr_3y, 0.3))
    if cd.rev_growth_ttm is not None:
        candidates.append(("ttm_yoy", cd.rev_growth_ttm, 0.2))
    if not candidates:
        return None
    wsum = sum(w for _, _, w in candidates)
    g = sum(v * w for _, v, w in candidates) / wsum
    # Bound to a plausible modeling range.
    return max(-0.30, min(1.00, g))


def classify(cd: CompanyData) -> Classification:
    c = Classification()
    g = _blended_growth(cd)
    c.blended_growth = g
    fcf_m = cd.fcf_margin
    c.is_cash_burning = (cd.fcf is not None and cd.fcf < 0)

    # Rule of 40 (growth% + FCF-margin%): a durable-growth quality check.
    if g is not None and fcf_m is not None:
        c.rule_of_40 = (g + fcf_m) * 100.0

    sector = (cd.sector or "")
    industry = (cd.industry or "").lower()

    # --- Financials: FCFF/DCF is not appropriate (debt is raw material) ---
    if sector in FINANCIAL_SECTORS or any(h in industry for h in FINANCIAL_INDUSTRY_HINTS):
        c.regime = "financial"
        c.dcf_reliability = "low"
        c.reasons.append("Bank/insurer/financial: unlevered FCF DCF is unreliable; "
                         "lean on multiples and dividend/earnings power instead.")
        return c

    gg = g if g is not None else 0.05

    # --- Hypergrowth / cash-burning growth ---
    if gg >= 0.25 or (gg >= 0.15 and c.is_cash_burning):
        c.regime = "hypergrowth"
        c.dcf_reliability = "low" if c.is_cash_burning else "medium"
        c.reasons.append(f"High revenue growth (~{gg:.0%})"
                         + (" with negative FCF (cash-burning)" if c.is_cash_burning else "")
                         + ": modeled with a long runway and margin convergence to maturity.")
        return c

    # --- Growth ---
    if gg >= 0.10:
        c.regime = "growth"
        c.dcf_reliability = "medium" if c.is_cash_burning else "high"
        c.reasons.append(f"Solid growth (~{gg:.0%}): extended forecast with a fading growth path.")
        return c

    # --- Cyclical (only if not already growthy) ---
    if sector in CYCLICAL_SECTORS:
        c.regime = "cyclical"
        c.dcf_reliability = "medium"
        c.reasons.append("Cyclical sector: margins normalized toward the mid-cycle average "
                         "rather than the latest (possibly peak/trough) year.")
        return c

    # --- Mature / stable (default) ---
    c.regime = "mature"
    c.dcf_reliability = "high"
    c.reasons.append("Mature, stable profile: standard 5-year FCFF DCF.")
    if c.is_cash_burning:
        c.dcf_reliability = "medium"
        c.reasons.append("Note: currently FCF-negative despite low growth — watch cash runway.")
    return c
