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
class InputProvenance:
    """Where one valuation input came from, and whether it is the company's own number.

    A headline that moved because a vendor field vanished must be distinguishable from one
    that moved because the company changed. Nothing in this engine could tell those apart:
    the beta fallback appended a note to a list nobody read, and the risk-free rate falls back
    to a config constant the same silent way.
    """
    value: Optional[float] = None
    source: str = ""              # vendor | vendor_corroborated | computed | fallback | override
    as_of: str = ""               # when the underlying observation is from, where knowable
    n_observations: Optional[int] = None
    vendor_value: Optional[float] = None   # what the vendor said, even when it was rejected
    substituted: bool = False     # True = NOT this company's own measured number
    note: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


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
    beta_provenance: Optional[InputProvenance] = None
    risk_free_provenance: Optional[InputProvenance] = None

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        for k in ("beta_provenance", "risk_free_provenance"):
            if isinstance(d.get(k), InputProvenance):
                d[k] = d[k].to_dict()
        return d

    @property
    def rests_on_substituted_inputs(self) -> bool:
        """True when the number does not rest on this company's own measured inputs."""
        return any(p is not None and p.substituted
                   for p in (self.beta_provenance, self.risk_free_provenance))


# Blume/Bloomberg "adjusted beta": b_adj = w*b_raw + (1-w)*1.0, w = 0.67. None = off
# (today's behaviour). Measured and REJECTED in Part 2 of HANDOFF_live_data_bugs.md — it
# breached the do-no-harm bound at 2.491% against a 2% ceiling.
BETA_SHRINK = None

# THE STATED FALLBACK. The market portfolio's beta is 1.0 BY CONSTRUCTION — that is the whole
# content of the number, and it is the only value here with a derivation. The previous constant
# was a bare `1.10`, which asserts the average listed company is 10% riskier than the market
# and appears nowhere else in this repository with a justification.
#
# It is now nearly unreachable, which is the actual fix: a missing vendor beta lands on a beta
# COMPUTED FROM THIS COMPANY'S OWN PRICES (see `data/beta.py`), and only a name with neither a
# usable vendor value nor enough price history of its own gets a constant.
BETA_FALLBACK = 1.0

# A vendor beta at or below this gets CORROBORATED before it is believed. It does NOT get
# rejected for being small: §2 of HANDOFF_live_data_bugs.md measured GILD 0.336, CI 0.321,
# CHTR 0.678, MRK 0.211 and XOM 0.173 as genuinely low-beta, and flooring the VALUE would
# assert something false about all of them. Only KSPI's 0.080 is an artifact, and what makes
# it one is the 30 monthly observations behind it.
#
# So this constant decides WHO GETS CHECKED; `MIN_BETA_OBSERVATIONS` decides who gets
# REJECTED. That is deliberate, and it is what makes the exact value here low-stakes — a
# long-history name is accepted no matter how far below this it sits.
BETA_LOW_TRIGGER = 0.25

# The high side, unchanged from the original check.
BETA_HIGH_CAP = 3.0


def _resolve_beta(cd: CompanyData, beta_override, notes):
    """THE beta ladder. Returns `(beta, InputProvenance)` and never raises.

    Vendor-first, deliberately. Switching every name to a self-computed beta would move every
    valuation in the product and leave nothing to compare against; vendor-first means a name
    whose vendor beta is ordinary is touched by none of this, which is both the conservative
    choice and the one that leaves a control group in existence.

    The rungs:
      1. an explicit override wins, as before;
      2. a vendor beta in (0, cap] and above the low trigger is ACCEPTED UNCHANGED, with no
         extra network call — this is the overwhelming majority of names;
      3. anything else is CORROBORATED against a beta computed from the company's own prices.
         With enough history the vendor value still wins if it is in range, because a low beta
         with five years behind it is a fact about the company. Without enough history it is
         not supportable and the computed value is used;
      4. and only a name with neither a usable vendor value nor enough price history of its
         own reaches the stated constant.

    Rung 3 is what fixes MRK: when the vendor field vanishes the answer becomes ~0.18, computed
    from Merck's own prices, instead of a constant that moved WACC by 3.78pp overnight.

    THE CORROBORATION IS BEST-EFFORT, AND ITS FAILURE MODE IS "NO CHANGE". If the check cannot
    RUN — Yahoo throttles a 500-name scan, the network is down — an in-range vendor beta is kept
    exactly as it is. This is deliberate and it is the more important half of the design: the
    first version of this function rejected on a failed call, and a measurement over 402 names
    on 2026-08-07 hit the rate limit and pushed **178 names onto the constant**, reproducing the
    original bug with a new trigger. A vendor beta is only ever overruled by positive evidence
    that its history is short. That means KSPI's artifact survives a throttled run, which is
    today's behaviour and therefore costs nothing that was not already being paid.
    """
    vendor = cd.beta
    if beta_override is not None:
        return float(beta_override), InputProvenance(
            value=float(beta_override), source="override", vendor_value=vendor,
            note="caller-supplied beta")

    in_range = vendor is not None and 0 < vendor <= BETA_HIGH_CAP
    if in_range and vendor > BETA_LOW_TRIGGER:
        return float(vendor), InputProvenance(
            value=float(vendor), source="vendor", vendor_value=vendor,
            note="vendor beta within the plausible band")

    # Rung 3 — corroborate. Reached only when the vendor value is missing, out of range, or
    # low enough that the observation count behind it decides whether to believe it.
    from ..data.beta import compute_beta, MIN_BETA_OBSERVATIONS
    est = compute_beta(cd.ticker)

    if in_range and est.unavailable:
        # The check could not RUN. Keep the company's own vendor number untouched — a busy
        # network is not evidence about a company. See the docstring; this is measured.
        notes.append(f"Low beta {vendor:.3f} could not be corroborated "
                     f"({est.error or 'no data'}); vendor value kept unchanged.")
        return float(vendor), InputProvenance(
            value=float(vendor), source="vendor_uncorroborated", vendor_value=vendor,
            n_observations=None, note="corroboration unavailable; vendor value kept")

    if in_range and est.n_observations >= MIN_BETA_OBSERVATIONS:
        # A low beta with real history is REAL. Measured: GILD, CI, CHTR, MRK, XOM.
        notes.append(f"Low beta {vendor:.3f} corroborated by {est.n_observations} monthly "
                     f"observations; kept.")
        return float(vendor), InputProvenance(
            value=float(vendor), source="vendor_corroborated", vendor_value=vendor,
            n_observations=est.n_observations, as_of=est.as_of,
            note="low but supported by sufficient history")

    if est.supportable:
        why = ("vendor beta missing" if vendor is None else
               f"vendor beta {vendor:.3f} rests on only {est.n_observations} monthly "
               f"observations" if in_range else
               f"vendor beta {vendor:.3f} outside (0, {BETA_HIGH_CAP}]")
        notes.append(f"{why}; used a beta computed from this company's own prices "
                     f"({est.value:.3f}, n={est.n_observations}).")
        return float(est.value), InputProvenance(
            value=float(est.value), source="computed", vendor_value=vendor,
            n_observations=est.n_observations, as_of=est.as_of, substituted=True, note=why)

    notes.append(f"Beta missing/implausible and not computable "
                 f"(n={est.n_observations}); used the stated market beta {BETA_FALLBACK}.")
    return BETA_FALLBACK, InputProvenance(
        value=BETA_FALLBACK, source="fallback", vendor_value=vendor,
        n_observations=est.n_observations, substituted=True,
        note=est.error or "no vendor beta and insufficient price history")


def compute_wacc(cd: CompanyData, cfg, rf: Optional[float] = None,
                 beta_override: Optional[float] = None,
                 erp_override: Optional[float] = None) -> WACCResult:
    notes = []
    # The risk-free rate has the SAME silent-substitution shape as beta did: `macro.py` falls
    # back to `cfg.default_risk_free` when the live 10Y fetch fails, and nothing downstream
    # could tell a live rate from a config constant. Stamp it too.
    if rf is not None:
        rf_prov = InputProvenance(value=float(rf), source="override",
                                  note="caller-supplied risk-free rate")
    elif cd.risk_free_rate is not None:
        rf = cd.risk_free_rate
        rf_prov = InputProvenance(value=float(rf), source="vendor", as_of=cd.as_of,
                                  note="live risk-free rate attached to the company data")
    else:
        rf = cfg.default_risk_free
        rf_prov = InputProvenance(value=float(rf), source="fallback", substituted=True,
                                  note="live risk-free rate unavailable; config default used")
    erp = erp_override if erp_override is not None else cfg.equity_risk_premium
    tax = cfg.marginal_tax_rate

    # Beta: resolve through a stated ladder and STAMP where the answer came from.
    beta, beta_prov = _resolve_beta(cd, beta_override, notes)
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
        beta_provenance=beta_prov, risk_free_provenance=rf_prov,
    )
