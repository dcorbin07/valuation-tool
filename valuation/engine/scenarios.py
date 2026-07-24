"""
Bull / base / bear scenarios.

Built by shifting the base-case drivers (revenue growth, operating margin,
terminal growth, reinvestment efficiency). Shift magnitudes scale with how
uncertain the regime is — a hypergrowth name gets a much wider cone than a
mature one, matching the reality that its value is far less pinned down.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.models import CompanyData
from .classify import Classification
from .assumptions import AssumptionSet, shift_assumptions
from .dcf import run_dcf, DCFResult

# Per-regime (growth_delta, margin_delta, terminal_delta, stc_multiplier)
_DELTAS = {
    "mature":     (0.020, 0.020, 0.0025, 1.10),
    "cyclical":   (0.050, 0.040, 0.0050, 1.10),
    "growth":     (0.040, 0.030, 0.0050, 1.12),
    "hypergrowth":(0.080, 0.050, 0.0050, 1.15),
    "financial":  (0.030, 0.030, 0.0050, 1.10),
}


@dataclass
class ScenarioSet:
    bear: DCFResult
    base: DCFResult
    bull: DCFResult

    def to_dict(self) -> dict:
        return {
            "bear": self.bear.to_dict(),
            "base": self.base.to_dict(),
            "bull": self.bull.to_dict(),
            "bear_price": self.bear.per_share,
            "base_price": self.base.per_share,
            "bull_price": self.bull.per_share,
        }


def build_scenarios(cd: CompanyData, cls: Classification, base: AssumptionSet,
                    wacc: float) -> ScenarioSet:
    dg, dm, dt, stc = _DELTAS.get(cls.regime, _DELTAS["mature"])

    bull_a = shift_assumptions(base, +dg, +dm, +dt, stc_mult=stc, label="bull")
    bear_a = shift_assumptions(base, -dg, -dm, -dt, stc_mult=1.0 / stc, label="bear")

    return ScenarioSet(
        bear=run_dcf(cd, bear_a, wacc),
        base=run_dcf(cd, base, wacc),
        bull=run_dcf(cd, bull_a, wacc),
    )
