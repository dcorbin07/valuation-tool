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

# --------------------------------------------------------------------------- #
# PUBLICATION GUARD (2026-08-04).
#
# The engine already DETECTED implausible output — it warned "almost certainly a data
# problem (currency or share count)" — and then published the number anyway. KSPI
# (Kaspi.kz, statements in KZT, USD ADR price $92.00) shipped a $1,249.16 base fair
# value at +1,258% upside with that warning attached and "confidence: low". A confident
# wrong number is worse than no number: the reader sees $1,249, not the caveat.
#
# So the same thresholds that produced the warning are now BINDING. Tripping the guard
# marks the blend not-valuable, which is the state the UI already renders as
# "Not DCF-valuable" with upside "n/a" — no web-layer change needed.
#
# Thresholds are the pre-existing warning bands, deliberately not retuned here.
#
# ONLY the high side refuses. A fair value far BELOW the price is not this failure mode:
# the product is not telling anyone to buy, and suppressing it would hide legitimate
# "this is expensive" verdicts — including the honest net-cash floor on a revenue-less
# shell ($0.22 against a $8.00 price), which `test_dcf_still_floors_at_net_cash_when_
# revenue_is_gone` deliberately requires us to publish. The low side keeps its warning.
FV_BAND_HIGH = 5.0    # fair value > 5x price -> refuse


def publication_guard(cd: CompanyData, blend, growth_led: bool = False) -> Optional[str]:
    """Refuse to publish a fair value we cannot stand behind. Returns the reason, or None.

    Two independent refusals:
      1. UNRESOLVED CURRENCY — statements in one currency, price in another, and the FX
         rate could not be fetched. Every monetary input is then in the wrong units by an
         unknown factor. `yahoo.fetch` sets `fx_unresolved` for exactly this case and
         nothing downstream had ever acted on it.
      2. SANITY BAND — the published number is more than 5x the market price. See the
         note above for why the low side warns rather than refuses.
    """
    fin = (getattr(cd, "financial_currency", "") or "").upper()
    px_ccy = (getattr(cd, "currency", "") or "USD").upper()
    if getattr(cd, "fx_unresolved", False):
        return (f"Cannot value this name: the statements are reported in {fin or 'a foreign currency'} "
                f"but the price is in {px_ccy}, and the exchange rate could not be resolved. "
                f"Every figure would be wrong by an unknown factor, so no fair value is published.")
    if fin and fin != px_ccy and getattr(cd, "fx_rate", None) is None:
        return (f"Cannot value this name: the statements are in {fin} and the price is in {px_ccy}, "
                f"but no currency conversion was applied. No fair value is published.")

    fv = blend.value if getattr(blend, "valuable", False) else None
    px = getattr(cd, "price", None)
    if fv and px and px > 0:
        ratio = fv / px
        if ratio > FV_BAND_HIGH:
            return (f"Cannot value this name: the model's ${fv:,.2f} is {ratio:.1f}x the ${px:,.2f} "
                    f"price. That gap is a data problem (currency or share count), not an "
                    f"opportunity, so no fair value is published.")
    return None


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
    fair_value_blend: Optional[object] = None      # FairValueBlend (archetype-adaptive)
    growth_lens: Optional[object] = None           # GrowthValue (revenue-multiple lens)
    fair_value_scenarios: dict = field(default_factory=dict)  # bear/base/bull, SAME method
    ai: Optional[dict] = None
    warnings: list = field(default_factory=list)

    @property
    def base_fair_value(self) -> Optional[float]:
        """The headline fair value: the archetype-adaptive blend when it applies, else
        the raw DCF. None means genuinely not valuable — callers must not fall back to
        the DCF's (negative) number, which is the bug this replaced."""
        b = self.fair_value_blend
        if b is not None:
            return b.value if b.valuable else None
        return self.scenarios.base.per_share

    @property
    def dcf_per_share(self) -> Optional[float]:
        """The unblended DCF figure, kept for the scenario range and diagnostics."""
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
            "fair_value_blend": (self.fair_value_blend.to_dict()
                                 if self.fair_value_blend is not None else None),
            "growth_lens": (self.growth_lens.to_dict()
                            if self.growth_lens is not None else None),
            "fair_value_scenarios": self.fair_value_scenarios,
            "base_fair_value": self.base_fair_value,
            "dcf_per_share": self.dcf_per_share,
            "upside": self.upside,
            "warnings": self.warnings,
            "sources": self.company.sources,
        }


def _blend_scenarios(cd, cls, scenarios, comps, rev, growth_scn, maturity, maturity_parts) -> dict:
    """bear / base / bull run through the SAME blend as the headline.

    Each scenario carries its own DCF (already shifted on growth/margin/terminal) and
    its own growth-lens value (shifted the same way, plus exit-multiple compression or
    expansion). The mature-multiples lens has no forecast to shift, so it gets the same
    multiple factor — a bear case in which the multiple does NOT compress isn't a bear case.
    """
    from .blend import blended_fair_value
    from .growth import SCENARIO_MULTIPLE

    out = {"method": "", "bear": None, "base": None, "bull": None}
    per_share = {"bear": scenarios.bear.per_share, "base": scenarios.base.per_share,
                 "bull": scenarios.bull.per_share}
    growth_ps = {k: (growth_scn.get(k).value if growth_scn.get(k) is not None else None)
                 for k in per_share}

    # Every case must use the SAME lenses, or the three numbers stop being one
    # valuation's range and become three different valuations — which is how a bear case
    # can come out ABOVE the bull case (seen on Unity: the DCF survived the bull case and
    # not the bear one). The base case decides which lenses are live; in the other cases a
    # lens that goes non-positive is floored at zero ("worthless under these assumptions")
    # rather than dropped. That also keeps the base card identical to the headline.
    def _live(v):
        return v is not None and float(v) > 0

    use_dcf, use_growth = _live(per_share["base"]), _live(growth_ps["base"])
    if not (use_dcf or use_growth or comps.comps_fair_value):
        return out

    def _floor(v):
        return max(float(v), 1e-9) if v is not None else 1e-9

    for name in ("bear", "base", "bull"):
        cmp_v = comps.comps_fair_value
        if cmp_v is not None:
            cmp_v = cmp_v * SCENARIO_MULTIPLE[name]
        b = blended_fair_value(cd, cls, _floor(per_share[name]) if use_dcf else None, cmp_v,
                               reverse=rev,
                               growth_value=_floor(growth_ps[name]) if use_growth else None,
                               maturity=maturity, maturity_parts=maturity_parts, quiet=True)
        out[name] = b.value if b.valuable else None
        if name == "base":
            out["method"] = b.method
    return out


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

    # Banks / insurers: the FCFF DCF doesn't fit them, so replace the headline
    # per-share values with a justified P/B–ROE model (book value × (ROE−g)/(Ke−g)).
    if cls.regime == "financial":
        from .financials import financial_scenarios
        fin = financial_scenarios(cd, wacc.cost_of_equity, base.terminal_growth)
        if fin:
            scenarios.bear.per_share, scenarios.base.per_share, scenarios.bull.per_share = fin
            scenarios.base.label = "base · P/B–ROE"
            cd.quality_notes.append(
                "Financial regime: fair value uses a justified P/B–ROE model "
                "(book value × (ROE−g)/(Ke−g)), not an unlevered FCF DCF.")

    trials = mc_trials if mc_trials is not None else cfg.montecarlo_trials
    mc = run_monte_carlo(cd, cls, base, wacc_value, trials=trials)
    rev = reverse_dcf(cd, base, wacc_value)
    comps = compute_comps(cd, peers=peers,
                          fetch_fn=(lambda p: fetcher.get_company(p, cfg)) if peers else None)
    sens = build_sensitivity(cd, base, wacc_value)

    # Archetype-adaptive headline value: DCF for established/profitable names, a
    # growth-scaled REVENUE multiple for growth/pre-profit ones, P/B-ROE for financials —
    # and nothing at all rather than a negative DCF figure when no lens genuinely applies.
    from .blend import blended_fair_value
    from .growth import maturity_from_company, build_growth_scenarios, mature_discount_rate

    maturity, maturity_parts = maturity_from_company(cd, growth=cls.blended_growth)
    mature_rate = mature_discount_rate(wacc.risk_free, wacc.erp, wacc_value)
    growth_scn = ({} if cls.regime == "financial"
                  else build_growth_scenarios(cd, cls, base, wacc_value, maturity,
                                              comps.benchmark, mature_rate=mature_rate))
    growth_lens = growth_scn.get("base")

    blend = blended_fair_value(
        cd, cls, scenarios.base.per_share, comps.comps_fair_value, reverse=rev,
        growth_value=(growth_lens.value if growth_lens is not None else None),
        maturity=maturity, maturity_parts=maturity_parts)

    # Bear / base / bull computed the SAME WAY as the headline. Showing the raw DCF cone
    # next to a multiples-based headline is how a growth name ended up displaying three
    # negative scenario cards under a positive fair value.
    fv_scen = _blend_scenarios(cd, cls, scenarios, comps, rev, growth_scn,
                               maturity, maturity_parts)
    blend.value_low, blend.value_high = fv_scen.get("bear"), fv_scen.get("bull")

    # Refuse to publish before anything downstream consumes the number — the score must
    # not be computed against a fair value the reader is never shown.
    refusal = publication_guard(cd, blend, growth_led=getattr(blend, "growth_led", False))
    if refusal:
        blend.valuable = False
        blend.withheld_value = blend.value   # kept for guards only — never published
        blend.value = None
        blend.reason = refusal
        blend.confidence = "low"
        blend.headline = refusal

    # Score against the SAME number the user is shown, so the valuation sub-score and the
    # headline can't disagree. compute_score already tolerates None (it renormalizes).
    score = compute_score(cd, cls, wacc_value,
                          blend.value if blend.valuable else None, mc, comps, blend=blend)

    result = ValuationResult(
        company=cd, classification=cls, wacc=wacc, assumptions=base, scenarios=scenarios,
        montecarlo=mc, reverse=rev, comps=comps, sensitivity=sens, score=score,
        fair_value_blend=blend, growth_lens=growth_lens, fair_value_scenarios=fv_scen,
        warnings=list(cd.quality_notes),
    )
    if not blend.valuable and blend.reason:
        result.warnings.insert(0, blend.reason)

    # Loud, top-of-list warning when the model output is implausible vs the price —
    # this is the tell for a data problem (e.g. an ADR's currency/share mismatch).
    # EXCEPT on a growth-led valuation: a pre-profit name whose price already discounts
    # a decade of compounding SHOULD come out far below it on our numbers. Calling that
    # a data error taught the reader to ignore the one signal that matters there.
    fv, px = result.base_fair_value, cd.price
    if fv and px and px > 0:
        ratio = fv / px
        if ratio > 5 or (ratio < 0.2 and not blend.growth_led):
            result.warnings.insert(0, f"Fair value ${fv:,.2f} is {ratio:.1f}× the ${px:,.2f} price — almost "
                                      f"certainly a data problem (currency or share count), not a real "
                                      f"opportunity. Verify the figures before trusting this valuation.")
        elif ratio < 0.2:
            result.warnings.insert(0, f"Our valuation (${fv:,.2f}) is a fraction of the ${px:,.2f} price. "
                                      f"For a pre-profit growth name that is a disagreement about future "
                                      f"growth, not a data error — see the implied-growth read.")

    if run_ai:
        try:
            from ..ai.analyst import analyze
            result.ai = analyze(result, cfg)
        except Exception as e:
            result.warnings.append(f"AI analysis unavailable: {e}")

    return result
