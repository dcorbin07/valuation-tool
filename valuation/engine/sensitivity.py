"""
Sensitivity grid — implied share price across WACC x terminal growth.

Mirrors the Sensitivity tab in the Nike workbook: rows are WACC, columns are the
terminal growth rate, each cell re-values the base case. Shows how much of the
answer rides on the two assumptions a DCF is most sensitive to.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..data.models import CompanyData
from .assumptions import AssumptionSet, shift_assumptions
from .dcf import intrinsic_per_share, _terminal_roic


@dataclass
class SensitivityResult:
    wacc_axis: list = field(default_factory=list)
    growth_axis: list = field(default_factory=list)
    grid: list = field(default_factory=list)   # grid[i][j] = price at wacc_i, g_j
    base_wacc: float = 0.0
    base_growth: float = 0.0

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def build_sensitivity(cd: CompanyData, base: AssumptionSet, wacc: float,
                      wacc_step=0.01, g_step=0.005, n=2) -> SensitivityResult:
    troic = _terminal_roic(cd, wacc)
    wacc_axis = [round(wacc + (i - n) * wacc_step, 4) for i in range(2 * n + 1)]
    g_axis = [round(base.terminal_growth + (j - n) * g_step, 4) for j in range(2 * n + 1)]

    grid = []
    for w in wacc_axis:
        w = max(0.04, min(0.25, w))
        row = []
        for g in g_axis:
            gd = g - base.terminal_growth
            a = shift_assumptions(base, term_delta=gd)
            # keep terminal growth strictly below WACC
            if a.terminal_growth >= w - 0.003:
                row.append(None)
                continue
            ps = intrinsic_per_share(cd, a, w, troic)
            row.append(round(ps, 2) if ps is not None else None)
        grid.append(row)

    return SensitivityResult(
        wacc_axis=wacc_axis, growth_axis=g_axis, grid=grid,
        base_wacc=wacc, base_growth=base.terminal_growth,
    )
