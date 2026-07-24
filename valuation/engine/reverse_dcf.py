"""
Reverse DCF — what is the market pricing in?

Holding everything else at the base case, we solve for the revenue-growth (and,
separately, the operating-margin) assumption that makes the model's fair value
equal today's price. If the market-implied growth is wildly above what the
company has ever done, the stock is priced for perfection; if it's below trend,
expectations are cheap. It's the single best sanity check on a DCF.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable

from ..data.models import CompanyData
from .assumptions import AssumptionSet, shift_assumptions
from .dcf import intrinsic_per_share, _terminal_roic


def _bisect(f: Callable[[float], float], lo: float, hi: float, tol=1e-3, iters=60) -> Optional[float]:
    """Find x in [lo, hi] with f(x)=0, assuming f is increasing. Returns None if
    the target isn't bracketed (price outside the achievable range)."""
    flo, fhi = f(lo), f(hi)
    if flo is None or fhi is None:
        return None
    if flo > 0:      # even the low assumption overvalues -> price below range
        return lo
    if fhi < 0:      # even the high assumption undervalues -> price above range
        return hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if fm is None:
            return None
        if abs(fm) < tol:
            return mid
        if fm < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass
class ReverseDCFResult:
    price: Optional[float]
    implied_start_growth: Optional[float]
    implied_avg_growth: Optional[float]
    base_start_growth: float
    base_avg_growth: float
    implied_target_margin: Optional[float]
    base_target_margin: float
    growth_verdict: str = ""
    margin_verdict: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _avg(path):
    return sum(path) / len(path) if path else 0.0


def reverse_dcf(cd: CompanyData, base: AssumptionSet, wacc: float) -> ReverseDCFResult:
    price = cd.price
    troic = _terminal_roic(cd, wacc)
    base_avg_g = _avg(base.rev_growth_path)

    res = ReverseDCFResult(
        price=price, implied_start_growth=None, implied_avg_growth=None,
        base_start_growth=base.start_growth, base_avg_growth=base_avg_g,
        implied_target_margin=None, base_target_margin=base.target_margin,
    )
    if not price or price <= 0 or cd.shares_diluted in (None, 0):
        res.growth_verdict = "No price/shares — reverse DCF unavailable."
        return res

    # Solve growth shift.
    def fg(dg):
        ps = intrinsic_per_share(cd, shift_assumptions(base, growth_delta=dg), wacc, troic)
        return None if ps is None else ps - price

    dg = _bisect(fg, -0.30, 0.60)
    if dg is not None:
        res.implied_start_growth = base.start_growth + dg
        res.implied_avg_growth = base_avg_g + dg
        gap = res.implied_avg_growth - base_avg_g
        if gap > 0.03:
            res.growth_verdict = (f"Market prices in ~{res.implied_avg_growth:.1%} avg revenue growth — "
                                  f"{gap:.1%} above our base ({base_avg_g:.1%}). Priced for optimism.")
        elif gap < -0.03:
            res.growth_verdict = (f"Market prices in only ~{res.implied_avg_growth:.1%} avg growth — "
                                  f"below our base ({base_avg_g:.1%}). Expectations look cheap.")
        else:
            res.growth_verdict = (f"Market-implied growth (~{res.implied_avg_growth:.1%}) is close to our "
                                  f"base case — fairly priced on growth.")

    # Solve margin shift.
    def fm(dm):
        ps = intrinsic_per_share(cd, shift_assumptions(base, margin_delta=dm), wacc, troic)
        return None if ps is None else ps - price

    dm = _bisect(fm, -0.20, 0.30)
    if dm is not None:
        res.implied_target_margin = base.target_margin + dm
        mgap = dm
        if mgap > 0.02:
            res.margin_verdict = (f"…or a terminal operating margin of ~{res.implied_target_margin:.1%} "
                                  f"vs our {base.target_margin:.1%} target.")
        elif mgap < -0.02:
            res.margin_verdict = (f"…or only a ~{res.implied_target_margin:.1%} terminal margin vs our "
                                  f"{base.target_margin:.1%} — a low bar.")
        else:
            res.margin_verdict = (f"…consistent with roughly our {base.target_margin:.1%} terminal margin.")
    return res
