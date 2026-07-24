"""
Monte Carlo simulation.

Instead of a single point estimate, we draw thousands of trials by perturbing
the key drivers (growth, margin, terminal growth, WACC) around the base case and
re-valuing each time. The output is a probability distribution of fair value and,
crucially, P(undervalued) — the share of trials in which intrinsic value exceeds
today's price. The perturbation sizes scale with the regime's uncertainty, so a
hypergrowth name gets a genuinely wide distribution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..data.models import CompanyData
from .classify import Classification
from .assumptions import AssumptionSet, shift_assumptions
from .dcf import intrinsic_per_share, _terminal_roic
from .scenarios import _DELTAS


@dataclass
class MonteCarloResult:
    trials: int
    mean: float
    median: float
    std: float
    p5: float
    p10: float
    p25: float
    p75: float
    p90: float
    p95: float
    prob_undervalued: Optional[float]   # P(intrinsic > price)
    price: Optional[float]
    hist_bins: list = field(default_factory=list)     # bin edges
    hist_counts: list = field(default_factory=list)   # counts per bin

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def run_monte_carlo(cd: CompanyData, cls: Classification, base: AssumptionSet,
                    wacc: float, trials: int = 10000, seed: int = 42) -> MonteCarloResult:
    rng = np.random.default_rng(seed)
    dg, dm, dt, _ = _DELTAS.get(cls.regime, _DELTAS["mature"])
    # Treat the bull/bear shift as roughly a 1.5-sigma move.
    sg, sm, st = dg / 1.5, dm / 1.5, dt / 1.5
    sw = {"mature": 0.008, "cyclical": 0.012, "growth": 0.012,
          "hypergrowth": 0.018, "financial": 0.010}.get(cls.regime, 0.010)

    troic = _terminal_roic(cd, wacc)
    gd = rng.normal(0, sg, trials)
    md = rng.normal(0, sm, trials)
    td = rng.normal(0, st, trials)
    wd = rng.normal(0, sw, trials)

    vals = np.empty(trials)
    for i in range(trials):
        a = shift_assumptions(base, gd[i], md[i], td[i])
        w = float(np.clip(wacc + wd[i], 0.04, 0.25))
        ps = intrinsic_per_share(cd, a, w, troic)
        vals[i] = ps if (ps is not None and np.isfinite(ps)) else np.nan

    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        vals = np.array([0.0])
    # Clip extreme tails for stable stats/plot (keep 0.5–99.5 pct).
    lo, hi = np.percentile(vals, [0.5, 99.5])
    clipped = np.clip(vals, lo, hi)
    counts, edges = np.histogram(clipped, bins=40)

    price = cd.price
    prob_uv = float(np.mean(vals > price)) if (price and price > 0) else None

    p = lambda q: float(np.percentile(vals, q))
    return MonteCarloResult(
        trials=len(vals), mean=float(np.mean(vals)), median=float(np.median(vals)),
        std=float(np.std(vals)), p5=p(5), p10=p(10), p25=p(25), p75=p(75), p90=p(90),
        p95=p(95), prob_undervalued=prob_uv, price=price,
        hist_bins=[float(x) for x in edges], hist_counts=[int(x) for x in counts],
    )
