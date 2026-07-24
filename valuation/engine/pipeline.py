"""
Pipeline — one call that turns a ticker into a complete valuation.

This is the single entry point used by the web app, the CLI, and the exporters.
It fetches data, classifies the company, builds assumptions (optionally with UI
overrides), computes WACC, runs the DCF scenarios, Monte Carlo, reverse DCF,
comps and sensitivity, then scores the opportunity 1-100.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..config import CONFIG
from ..data import fetcher
from ..data.models import CompanyData
from .classify import classify, Classification
from .assumptions import build_base_assumptions, apply_overrides, AssumptionSet
from .wacc import compute_wacc, WACCResult
from .scenarios import build_scenarios, ScenarioSet
from .montecarlo import run_monte_carlo, MonteCarloResult
from .reverse_dcf import reverse_dcf, ReverseDCFResult
from .comps import compute_comps, CompsResult
from .sensitivity import build_sensitivity, SensitivityResult
from .scoring import compute_score, ScoreResult


@dataclass
class ValuationResult:
    company: CompanyData
    classification: Classification
    wacc: WACCResult
    assumptions: AssumptionSet
    scenarios: ScenarioSet
    montecarlo: MonteCarloResult
    reverse: ReverseDCFResult
    comps: CompsResult
    sensitivity: SensitivityResult
    score: ScoreResult
    ai: Optional[dict] = None
    warnings: list = field(default_factory=list)

    @property
    def base_fair_value(self) -> Optional[float]:
        return self.scenarios.base.per_share

    @property
    def upside(self) -> Optional[float]:
        p = self.company.price
        fv = self.base_fair_value
        if p and fv and p > 0:
            return fv / p - 1.0
        return None

    def to_dict(self) -> dict:
        return {
            "company": self.company.to_dict(),
            "classification": self.classification.to_dict(),
            "wacc": self.wacc.to_dict(),
            "assumptions": self.assumptions.to_dict(),
            "scenarios": self.scenarios.to_dict(),
            "montecarlo": self.montecarlo.to_dict(),
            "reverse": self.reverse.to_dict(),
            "comps": self.comps.to_dict(),
            "sensitivity": self.sensitivity.to_dict(),
            "score": self.score.to_dict(),
            "ai": self.ai,
            "base_fair_value": self.base_fair_value,
            "upside": self.upside,
            "warnings": self.warnings,
            "sources": self.company.sources,
        }


def value_ticker(ticker: str, cfg=CONFIG, overrides: Optional[dict] = None,
                 peers: Optional[list] = None, run_ai: bool = False,
                 mc_trials: Optional[int] = None) -> ValuationResult:
    """Fetch a ticker's live data, then value it."""
    cd = fetcher.get_company(ticker, cfg)
    return value_from_company(cd, cfg, overrides=overrides, peers=peers,
                              run_ai=run_ai, mc_trials=mc_trials)


def value_from_company(cd: CompanyData, cfg=CONFIG, overrides: Optional[dict] = None,
                       peers: Optional[list] = None, run_ai: bool = False,
                       mc_trials: Optional[int] = None) -> ValuationResult:
    """Value an already-fetched company (used by tests and batch mode)."""
    overrides = overrides or {}
    cls = classify(cd)

    # WACC (respect explicit overrides for beta/erp/risk-free/wacc).
    wacc = compute_wacc(cd, cfg,
                        rf=overrides.get("risk_free"),
                        beta_override=overrides.get("beta"),
                        erp_override=overrides.get("erp"))
    wacc_value = float(overrides["wacc"]) if overrides.get("wacc") else wacc.wacc

    base = build_base_assumptions(cd, cls, wacc.risk_free, cfg)
    base = apply_overrides(base, cls, overrides)

    scenarios = build_scenarios(cd, cls, base, wacc_value)
    trials = mc_trials if mc_trials is not None else cfg.montecarlo_trials
    mc = run_monte_carlo(cd, cls, base, wacc_value, trials=trials)
    rev = reverse_dcf(cd, base, wacc_value)
    comps = compute_comps(cd, peers=peers,
                          fetch_fn=(lambda p: fetcher.get_company(p, cfg)) if peers else None)
    sens = build_sensitivity(cd, base, wacc_value)
    score = compute_score(cd, cls, wacc_value, scenarios.base.per_share, mc, comps)

    result = ValuationResult(
        company=cd, classification=cls, wacc=wacc, assumptions=base, scenarios=scenarios,
        montecarlo=mc, reverse=rev, comps=comps, sensitivity=sens, score=score,
        warnings=list(cd.quality_notes),
    )

    if run_ai:
        try:
            from ..ai.analyst import analyze
            result.ai = analyze(result, cfg)
        except Exception as e:
            result.warnings.append(f"AI analysis unavailable: {e}")

    return result
