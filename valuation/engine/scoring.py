"""
The 1-100 opportunity score.

A transparent, regime-aware composite of five sub-scores (each 0-100):

  * Valuation     — margin of safety vs intrinsic value, P(undervalued) from the
                    Monte Carlo, and a comps cross-check.
  * Quality       — value creation (ROIC vs WACC), gross margin, profitability.
  * Growth        — durable revenue growth, with a Rule-of-40 check for growth names.
  * Financial health — leverage, interest coverage, and (for cash-burners) how
                    many years of runway the balance sheet funds.
  * Momentum      — price trend (200-day MA, 6-month return), a light overlay.

The weights shift by regime: for a hypergrowth cash-burner the DCF is less
reliable, so valuation is down-weighted and growth + runway matter more; for a
mature compounder, valuation and quality dominate. Everything is exposed so the
score is explainable, never a black box.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..data.models import CompanyData
from .classify import Classification

# Regime -> weights for (valuation, quality, growth, health, momentum)
_WEIGHTS = {
    "mature":     {"valuation": 0.40, "quality": 0.20, "growth": 0.05, "health": 0.20, "momentum": 0.15},
    "growth":     {"valuation": 0.30, "quality": 0.20, "growth": 0.20, "health": 0.15, "momentum": 0.15},
    "hypergrowth":{"valuation": 0.20, "quality": 0.15, "growth": 0.30, "health": 0.25, "momentum": 0.10},
    "cyclical":   {"valuation": 0.35, "quality": 0.15, "growth": 0.10, "health": 0.25, "momentum": 0.15},
    "financial":  {"valuation": 0.30, "quality": 0.25, "growth": 0.10, "health": 0.20, "momentum": 0.15},
}


def _lerp(x: Optional[float], pts) -> Optional[float]:
    """Piecewise-linear map from x to a 0-100 score via (x, score) breakpoints."""
    if x is None:
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, s0), (x1, s1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0) if x1 != x0 else 0
            return s0 + (s1 - s0) * t
    return pts[-1][1]


def _blend(parts):
    """Weighted average of (score, weight) ignoring None scores."""
    num = sum(s * w for s, w in parts if s is not None)
    den = sum(w for s, w in parts if s is not None)
    return (num / den) if den else None


@dataclass
class ScoreResult:
    score: int
    recommendation: str
    confidence: str
    subscores: dict = field(default_factory=dict)
    weights: dict = field(default_factory=dict)
    drivers: list = field(default_factory=list)   # human-readable explanations

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _valuation_score(cd, base_fv, mc, comps) -> tuple[Optional[float], list]:
    drivers = []
    parts = []
    price = cd.price
    if base_fv and price and price > 0:
        mos = base_fv / price - 1.0
        s = _lerp(mos, [(-0.5, 0), (-0.25, 18), (-0.10, 38), (0.0, 50),
                        (0.15, 63), (0.30, 74), (0.60, 88), (1.0, 100)])
        parts.append((s, 0.55))
        drivers.append(f"Base fair value ${base_fv:,.2f} vs ${price:,.2f} → "
                       f"{mos:+.0%} margin of safety.")
    if mc and mc.prob_undervalued is not None:
        parts.append((mc.prob_undervalued * 100, 0.30))
        drivers.append(f"Monte Carlo: {mc.prob_undervalued:.0%} of trials value it above the price.")
    if comps and comps.comps_fair_value and price and price > 0:
        cmos = comps.comps_fair_value / price - 1.0
        s = _lerp(cmos, [(-0.4, 10), (0.0, 50), (0.4, 85), (0.8, 100)])
        parts.append((s, 0.15))
        drivers.append(f"Comps imply ${comps.comps_fair_value:,.2f} ({cmos:+.0%}).")
    return _blend(parts), drivers


def _quality_score(cd, wacc) -> tuple[Optional[float], list]:
    drivers = []
    parts = []
    roe = None
    if cd.net_income is not None and cd.total_equity not in (None, 0) and cd.total_equity > 0:
        roe = cd.net_income / cd.total_equity
    # Return on capital: prefer ROIC vs WACC; fall back to ROE (works for banks /
    # names where invested capital or EBIT isn't reported) so quality isn't n/a.
    if cd.roic is not None and wacc is not None:
        spread = cd.roic - wacc
        s = _lerp(spread, [(-0.05, 5), (0.0, 45), (0.05, 65), (0.10, 82), (0.20, 100)])
        parts.append((s, 0.5))
        drivers.append(f"ROIC {cd.roic:.0%} vs WACC {wacc:.0%} → {spread:+.0%} value-creation spread.")
    elif roe is not None:
        s = _lerp(roe, [(-0.05, 5), (0.0, 40), (0.10, 60), (0.20, 82), (0.35, 100)])
        parts.append((s, 0.5))
        drivers.append(f"Return on equity {roe:.0%}.")
    if cd.gross_margin is not None:
        s = _lerp(cd.gross_margin, [(0.05, 15), (0.25, 45), (0.45, 68), (0.70, 90), (0.90, 100)])
        parts.append((s, 0.3))
    # Profitability: operating margin, or net margin if EBIT isn't available.
    if cd.ebit_margin is not None:
        s = _lerp(cd.ebit_margin, [(-0.10, 5), (0.0, 35), (0.10, 60), (0.20, 82), (0.35, 100)])
        parts.append((s, 0.2))
    elif cd.net_margin is not None:
        s = _lerp(cd.net_margin, [(-0.10, 5), (0.0, 35), (0.10, 60), (0.20, 82), (0.35, 100)])
        parts.append((s, 0.2))
    return _blend(parts), drivers


def _growth_score(cd, cls) -> tuple[Optional[float], list]:
    drivers = []
    parts = []
    g = cls.blended_growth
    if g is not None:
        s = _lerp(g, [(-0.10, 5), (0.0, 30), (0.05, 50), (0.10, 65),
                      (0.20, 80), (0.35, 92), (0.50, 100)])
        parts.append((s, 0.7))
        drivers.append(f"Forward revenue growth ~{g:.0%}.")
    if cls.rule_of_40 is not None and cls.regime in ("growth", "hypergrowth"):
        s = _lerp(cls.rule_of_40, [(-20, 5), (0, 25), (20, 45), (40, 72), (60, 92), (80, 100)])
        parts.append((s, 0.3))
        tag = "clears" if cls.rule_of_40 >= 40 else "misses"
        drivers.append(f"Rule of 40 = {cls.rule_of_40:.0f} ({tag} the 40 bar).")
    return _blend(parts), drivers


def _health_score(cd, cls) -> tuple[Optional[float], list]:
    drivers = []
    lev = _lerp(cd.net_debt_to_ebitda, [(-1.0, 100), (0.0, 92), (1.0, 82),
                                        (2.0, 68), (3.0, 50), (4.0, 30), (6.0, 8)]) \
        if cd.net_debt_to_ebitda is not None else None
    cov = _lerp(cd.interest_coverage, [(0.5, 5), (1.5, 30), (3.0, 55),
                                       (6.0, 80), (12.0, 100)]) \
        if cd.interest_coverage is not None else None

    if cls.is_cash_burning:
        runway = cd.cash_runway_years
        rs = _lerp(runway, [(0.5, 3), (1.0, 12), (2.0, 32), (3.0, 52),
                            (5.0, 76), (7.0, 90), (10.0, 100)]) if runway is not None else 25
        parts = [(rs, 0.5), (lev, 0.3), (cov, 0.2)]
        if runway is not None:
            drivers.append(f"Cash-burning: ~{runway:.1f} yrs of runway at the current burn.")
    else:
        fcf_ok = 100 if (cd.fcf is not None and cd.fcf > 0) else 40
        parts = [(lev, 0.5), (cov, 0.3), (fcf_ok, 0.2)]
        if cd.net_debt_to_ebitda is not None:
            drivers.append(f"Net debt/EBITDA {cd.net_debt_to_ebitda:.1f}x"
                           + (", positive FCF." if (cd.fcf and cd.fcf > 0) else "."))
    return _blend(parts), drivers


def _momentum_score(cd) -> tuple[Optional[float], list]:
    drivers = []
    parts = []
    if cd.price and cd.ma_200:
        rel = cd.price / cd.ma_200 - 1.0
        s = _lerp(rel, [(-0.30, 15), (-0.10, 40), (0.0, 55), (0.10, 70), (0.30, 90), (0.5, 100)])
        parts.append((s, 0.6))
        drivers.append(f"Price {rel:+.0%} vs 200-day average.")
    if cd.ret_6m is not None:
        s = _lerp(cd.ret_6m, [(-0.4, 10), (-0.1, 40), (0.0, 52), (0.2, 72), (0.5, 95)])
        parts.append((s, 0.4))
    return _blend(parts), drivers


def _recommendation(score: int) -> str:
    if score >= 80:
        return "Strong Buy"
    if score >= 66:
        return "Buy"
    if score >= 46:
        return "Hold"
    if score >= 31:
        return "Reduce"
    return "Avoid"


def compute_score(cd: CompanyData, cls: Classification, wacc: float,
                  base_fv: Optional[float], mc, comps, blend=None) -> ScoreResult:
    # A valuation the model REFUSED to publish must not come back in through the side
    # door. Passing `base_fv=None` only dropped the margin-of-safety term (weight 0.55);
    # `mc.prob_undervalued` (0.30) is the share of Monte Carlo trials OF THAT SAME
    # withheld DCF beating the price, and `comps.comps_fair_value` (0.15) is corrupted the
    # same way. On KSPI those two alone printed a valuation sub-score of 100.0/100 for a
    # name the model had declined to value, and the composite read 93 "Strong Buy".
    # So when the headline is withheld, the ENTIRE valuation sub-score is dropped and the
    # composite renormalizes over the four sub-scores that rest on published inputs.
    withheld = blend is not None and not getattr(blend, "valuable", False)
    if withheld:
        val, d_val = None, ["Valuation withheld — no fair-value, Monte Carlo or comps term "
                            "contributes to this score. Scored on quality, growth, financial "
                            "health and momentum only."]
    else:
        val, d_val = _valuation_score(cd, base_fv, mc, comps)
    qual, d_qual = _quality_score(cd, wacc)
    grow, d_grow = _growth_score(cd, cls)
    health, d_health = _health_score(cd, cls)
    mom, d_mom = _momentum_score(cd)

    subs = {"valuation": val, "quality": qual, "growth": grow, "health": health, "momentum": mom}
    weights = dict(_WEIGHTS.get(cls.regime, _WEIGHTS["mature"]))

    # Composite over available sub-scores (re-normalize weights for any missing).
    num = sum(subs[k] * weights[k] for k in subs if subs[k] is not None)
    den = sum(weights[k] for k in subs if subs[k] is not None)
    composite = (num / den) if den else 50.0
    composite = int(round(max(1, min(100, composite))))

    # Confidence from DCF reliability + data completeness.
    missing = sum(1 for v in subs.values() if v is None)
    if cls.dcf_reliability == "low" or missing >= 2:
        confidence = "low"
    elif cls.dcf_reliability == "medium" or missing == 1:
        confidence = "medium"
    else:
        confidence = "high"

    drivers = d_val + d_qual + d_grow + d_health + d_mom

    # Data-sanity guard: a fair value >5x or <0.2x the price is almost always a
    # data problem (currency, share count, a one-off item) rather than a real
    # opportunity — never surface that as a strong buy.
    # A growth-led valuation legitimately lands far below a price that's discounting
    # years of compounding — that's the thesis, not a data glitch — so the low side of
    # the guard doesn't apply to it. The high side still does: a fair value 5x the price
    # is a currency/share-count smell whatever the archetype.
    # THE CAP MUST EVALUATE WHEN THE VALUE IS WITHHELD. Written `if base_fv and ...`, it
    # could not fire once the guard set base_fv=None — so publishing a bad number capped
    # KSPI at 50, while WITHHOLDING it let KSPI print 93. A safety check that only works
    # when the unsafe thing is present is worse than no check. It now falls back to the
    # value the guard suppressed.
    growth_led = bool(getattr(blend, "growth_led", False)) if blend is not None else False
    checked_fv = base_fv if base_fv else getattr(blend, "withheld_value", None)
    if checked_fv and cd.price and cd.price > 0:
        ratio = checked_fv / cd.price
        if ratio > 5 or (ratio < 0.2 and not growth_led):
            composite = min(composite, 50)
            confidence = "low"
            drivers.insert(0, f"⚠ Model fair value is {ratio:.1f}× the price — implausible; likely a data "
                              f"issue (currency, share count, or a one-off). Capped and flagged unreliable, "
                              f"not a recommendation.")
        elif ratio < 0.2:
            confidence = "low"
            drivers.insert(0, f"Model fair value is {ratio*100:.0f}% of the price. On a growth name that is "
                              f"a disagreement with the market about future growth, not necessarily a data "
                              f"error — see the implied-growth read.")

    return ScoreResult(
        score=composite, recommendation=_recommendation(composite), confidence=confidence,
        subscores={k: (round(v, 1) if v is not None else None) for k, v in subs.items()},
        weights=weights, drivers=drivers,
    )
