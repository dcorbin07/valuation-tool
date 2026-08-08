"""
Engine tests. Run with either:

    python -m pytest tests/
    python tests/test_engine.py     # no pytest required

Data is synthetic (fixtures.py) so tests run fully offline. They validate the
math and the wiring, using Donovan's Nike model as a known reference point.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG
from valuation.engine.classify import classify
from valuation.engine.assumptions import build_base_assumptions, apply_overrides
from valuation.engine.wacc import compute_wacc
from valuation.engine.dcf import run_dcf
from valuation.engine.scoring import compute_score
from valuation.engine.pipeline import value_from_company
from tests.fixtures import build_nike, build_growth


def test_absurd_fair_value_capped_not_strong_buy():
    # A wildly implausible fair value (data glitch) must never present as a strong buy.
    cd = build_nike()
    cls = classify(cd)
    w = compute_wacc(cd, CONFIG).wacc
    bad = compute_score(cd, cls, w, base_fv=cd.price * 50, mc=None, comps=None)
    assert bad.score <= 50 and bad.confidence == "low"
    assert any("implausible" in d.lower() for d in bad.drivers)
    # A sane fair value is scored on its merits, not force-capped.
    ok = compute_score(cd, cls, w, base_fv=cd.price * 1.2, mc=None, comps=None)
    assert 1 <= ok.score <= 100


def test_quality_fallback_roe_net_margin():
    from valuation.data.models import CompanyData
    from valuation.engine.scoring import _quality_score
    # A bank-like name: no ROIC / EBIT / gross profit, but net income, equity, revenue.
    cd = CompanyData(ticker="BANKX")
    cd.net_income, cd.total_equity, cd.revenue = 6000.0, 60000.0, 40000.0
    q, drivers = _quality_score(cd, 0.09)
    assert q is not None                                   # was n/a before the fallback
    assert any("equity" in d.lower() for d in drivers)     # ROE fallback used


def test_financial_pb_roe_value():
    from valuation.data.models import CompanyData
    from valuation.engine.financials import financial_fair_value
    cd = CompanyData(ticker="BANKX")
    cd.total_equity, cd.shares_diluted, cd.net_income = 60000.0, 6585.0, 6030.0  # ROE ~10%
    bvps = 60000.0 / 6585.0
    # ROE 10% > Ke 8% (g 3%) -> justified P/B (0.07/0.05)=1.4 -> premium to book
    fv = financial_fair_value(cd, ke=0.08, g=0.03)
    assert fv is not None and abs(fv - bvps * 1.4) < 0.5
    # ROE below cost of equity -> trades below book
    assert financial_fair_value(cd, ke=0.13, g=0.03) < bvps


def _beta_case(vendor, computed, n):
    """A CompanyData plus a stubbed estimator — these tests must never touch the network."""
    from valuation.data import beta as beta_mod
    from valuation.data.models import CompanyData
    cd = CompanyData(ticker="TEST", price=100.0, shares_diluted=10.0, market_cap=1000.0,
                     total_debt=0.0, risk_free_rate=0.043, beta=vendor)
    orig = beta_mod.compute_beta
    beta_mod.compute_beta = lambda t, closes=None: beta_mod.BetaEstimate(
        computed, n, as_of="2026-08-01")
    return cd, orig, beta_mod


def test_an_ordinary_vendor_beta_is_accepted_with_no_extra_work():
    """The control group, and the reason the ladder is vendor-first: a name whose vendor beta
    is ordinary must be touched by none of this — same number, and no extra network call."""
    from valuation.data import beta as beta_mod
    from valuation.data.models import CompanyData
    cd = CompanyData(ticker="TEST", price=100.0, shares_diluted=10.0, market_cap=1000.0,
                     total_debt=0.0, risk_free_rate=0.043, beta=1.2)
    orig = beta_mod.compute_beta

    def _explode(*a, **k):
        raise AssertionError("an ordinary vendor beta must not trigger a beta computation")
    beta_mod.compute_beta = _explode
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert w.beta == 1.2
    assert w.beta_provenance.source == "vendor"
    assert w.beta_provenance.substituted is False


def test_a_vanished_vendor_beta_lands_on_a_computed_beta_not_a_constant():
    """THE reproducibility bug. Yahoo stopped returning a beta for MRK between 2026-08-04 and
    2026-08-05; the old code substituted 1.10, WACC went 5.53% -> 9.31%, and the name went from
    'cannot value this name' to a published 91 'Strong Buy' — because a vendor field vanished,
    not because anything about Merck changed.

    With the ladder, a missing vendor beta resolves to a beta computed from the company's OWN
    prices, so the headline no longer moves when the field does."""
    cd, orig, beta_mod = _beta_case(vendor=None, computed=0.180, n=59)
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert abs(w.beta - 0.180) < 1e-9, f"fell back to a constant instead of computing: {w.beta}"
    assert w.beta != 1.10
    assert w.beta_provenance.source == "computed"
    assert w.beta_provenance.substituted is True, "a computed beta is not the vendor's number"
    assert w.rests_on_substituted_inputs is True


def test_a_low_beta_with_real_history_is_kept():
    """A low beta is not a bug. GILD 0.336, CI 0.321, CHTR 0.678, MRK 0.211 and XOM 0.173 were
    all measured GENUINE against five years of monthly returns. Flooring the VALUE would assert
    something false about every one of them, so a long-history name is kept no matter how low
    it sits."""
    cd, orig, beta_mod = _beta_case(vendor=0.173, computed=0.206, n=59)   # the XOM shape
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert w.beta == 0.173, "a corroborated low beta must survive untouched"
    assert w.beta_provenance.source == "vendor_corroborated"
    assert w.beta_provenance.n_observations == 59


def test_a_low_beta_on_short_history_is_rejected_for_its_HISTORY():
    """KSPI: a five-year monthly beta of 0.080 with only 30 monthly observations behind it, on
    an ADR that listed in 2024. It produced a 5.10% WACC and a +1,255% upside.

    The rejection must be driven by the observation count, not by the size of the number —
    otherwise it would also reject the genuinely low betas in the test above."""
    cd, orig, beta_mod = _beta_case(vendor=0.080, computed=0.886, n=30)
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert w.beta != 0.080, "KSPI's 30-observation beta was accepted"
    assert abs(w.beta - 0.886) < 1e-9
    assert w.beta_provenance.source == "computed"
    assert w.beta_provenance.n_observations == 30
    assert "observations" in (w.beta_provenance.note or ""), (
        "the rejection must be stated as a history problem, not a size problem")

    # ...and the SAME low value with real history behind it is kept — which is what proves the
    # rule is about history rather than magnitude.
    cd2, orig2, bm2 = _beta_case(vendor=0.080, computed=0.886, n=59)
    try:
        w2 = compute_wacc(cd2, CONFIG)
    finally:
        bm2.compute_beta = orig2
    assert w2.beta == 0.080, "identical value, longer history — must be kept"


def test_the_stated_fallback_is_the_market_beta_and_is_marked_substituted():
    """Only a name with neither a usable vendor beta nor enough price history of its own gets a
    constant. The old one was a bare 1.10 with no derivation anywhere in the repo; the market
    portfolio's beta is 1.0 by construction."""
    from valuation.engine.wacc import BETA_FALLBACK
    assert BETA_FALLBACK == 1.0
    cd, orig, beta_mod = _beta_case(vendor=None, computed=None, n=0)
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert w.beta == BETA_FALLBACK
    assert w.beta_provenance.source == "fallback"
    assert w.beta_provenance.substituted is True
    assert w.rests_on_substituted_inputs is True


def test_risk_free_fallback_is_stamped_too():
    """`macro.py` falls back to `cfg.default_risk_free` the same silent way the beta did, and
    nothing downstream could tell a live rate from a config constant."""
    from valuation.data.models import CompanyData
    cd = CompanyData(ticker="TEST", price=100.0, shares_diluted=10.0, market_cap=1000.0,
                     total_debt=0.0, beta=1.2, risk_free_rate=None)
    w = compute_wacc(cd, CONFIG)
    assert w.risk_free_provenance.source == "fallback"
    assert w.risk_free_provenance.substituted is True
    cd.risk_free_rate = 0.043
    assert compute_wacc(cd, CONFIG).risk_free_provenance.source == "vendor"


def test_a_throttled_corroboration_keeps_the_vendor_beta():
    """THE REGRESSION THIS SHIPPED WITH AND ALMOST SHIPPED WITHOUT A TEST.

    The first version of the ladder rejected a low vendor beta whenever `compute_beta` came back
    empty — without asking WHY it was empty. Measured 2026-08-07 over 402 names: the corroborating
    calls exhausted Yahoo's quota, 176 returned `YFRateLimitError`, and **178 names were pushed
    onto the constant**. That is the original MRK bug with a new trigger, and production scans
    500 names at a time, which is precisely the burst that provokes it.

    A vendor beta may only be overruled by positive evidence that its history is short.
    """
    from valuation.data import beta as beta_mod
    from valuation.data.models import CompanyData
    cd = CompanyData(ticker="TEST", price=100.0, shares_diluted=10.0, market_cap=1000.0,
                     total_debt=0.0, risk_free_rate=0.043, beta=0.211)     # the MRK shape
    orig = beta_mod.compute_beta
    beta_mod.compute_beta = lambda t, closes=None: beta_mod.BetaEstimate(
        None, 0, error="YFRateLimitError: Too Many Requests. Rate limited.")
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert abs(w.beta - 0.211) < 1e-9, f"a rate limit moved a published beta: {w.beta}"
    assert w.beta_provenance.source == "vendor_uncorroborated"
    assert w.beta_provenance.substituted is False, "the vendor's own number is not a substitution"
    assert w.rests_on_substituted_inputs is False


def test_a_throttled_corroboration_still_reaches_the_constant_with_no_vendor_beta():
    """Fail-open is not fail-never. With no usable vendor value AND no computation, there is
    nothing to keep, so the stated constant is correct — and that is exactly the population the
    OLD code sent to a constant, so this path is not a widening."""
    cd, orig, beta_mod = _beta_case(vendor=None, computed=None, n=0)
    try:
        w = compute_wacc(cd, CONFIG)
    finally:
        beta_mod.compute_beta = orig
    assert w.beta == 1.0
    assert w.beta_provenance.source == "fallback"
    assert w.beta_provenance.substituted is True


def test_wacc_matches_nike():
    cd = build_nike()
    w = compute_wacc(cd, CONFIG)
    assert 0.085 <= w.wacc <= 0.098, w.wacc          # ~9.1% like the original model
    assert 0.09 <= w.cost_of_equity <= 0.105


def test_classification():
    assert classify(build_nike()).regime == "mature"
    g = classify(build_growth())
    assert g.regime == "hypergrowth"
    assert g.is_cash_burning is True
    assert g.dcf_reliability == "low"


def test_nike_fair_value_reasonable():
    cd = build_nike()
    cls = classify(cd)
    w = compute_wacc(cd, CONFIG)
    a = build_base_assumptions(cd, cls, cd.risk_free_rate, CONFIG)
    r = run_dcf(cd, a, w.wacc)
    assert r.per_share is not None
    assert 25 <= r.per_share <= 55, r.per_share       # sane band around the $42 model
    assert 0 < r.tv_pct_of_ev < 0.95


def test_growth_cashburner_turns_positive():
    cd = build_growth()
    cls = classify(cd)
    w = compute_wacc(cd, CONFIG)
    a = build_base_assumptions(cd, cls, cd.risk_free_rate, CONFIG)
    r = run_dcf(cd, a, w.wacc)
    fcffs = [row["fcff"] for row in r.rows]
    assert fcffs[0] < 0, "early years should burn cash"
    assert fcffs[-1] > 0, "should turn FCF-positive by the end of the forecast"
    # NOL shield: first-year taxes ~ 0 while EBIT is negative
    assert abs(r.rows[0]["taxes"]) < 1e-6
    assert r.per_share is not None and r.per_share > 0


def test_scenarios_ordered():
    for build in (build_nike, build_growth):
        r = value_from_company(build(), CONFIG, mc_trials=1500)
        assert r.scenarios.bear.per_share < r.scenarios.base.per_share < r.scenarios.bull.per_share


def test_scoring_bounds_and_reco():
    for build in (build_nike, build_growth):
        r = value_from_company(build(), CONFIG, mc_trials=1500)
        assert 1 <= r.score.score <= 100
        assert r.score.recommendation in {"Strong Buy", "Buy", "Hold", "Reduce", "Avoid"}
        assert r.score.confidence in {"high", "medium", "low"}


def test_montecarlo_prob():
    r = value_from_company(build_nike(), CONFIG, mc_trials=3000)
    p = r.montecarlo.prob_undervalued
    assert p is None or 0.0 <= p <= 1.0
    assert r.montecarlo.p10 <= r.montecarlo.median <= r.montecarlo.p90


def test_reverse_and_comps():
    r = value_from_company(build_nike(), CONFIG, mc_trials=1500)
    assert r.reverse.implied_avg_growth is not None
    assert r.comps.comps_fair_value is not None and r.comps.comps_fair_value > 0


def test_overrides_change_value():
    cd = build_nike()
    cls = classify(cd)
    w = compute_wacc(cd, CONFIG)
    a = build_base_assumptions(cd, cls, cd.risk_free_rate, CONFIG)
    base_v = run_dcf(cd, a, w.wacc).per_share
    a2 = apply_overrides(a, cls, {"target_margin": 0.16})
    higher = run_dcf(cd, a2, w.wacc).per_share
    assert higher > base_v, "raising the target margin should raise fair value"


def test_pipeline_serializable():
    r = value_from_company(build_nike(), CONFIG, mc_trials=1500, run_ai=True)
    js = json.dumps(r.to_dict())          # must not raise
    assert len(js) > 1000
    assert r.ai is not None and "overall_take" in r.ai


def _unprofitable(revenue=55.0, price=8.0, total_debt=10.0, cash=30.0):
    """An RCAT-like name: real revenue, deeply negative EBIT/FCF -> the DCF goes negative.

    Note the DCF still floors at net cash, so to exercise the genuinely-not-valuable
    path a caller must ALSO make net debt positive (debt > cash) and strip revenue.
    """
    from valuation.data.models import CompanyData
    return CompanyData(
        ticker="RCAT", name="Unprofitable Co", sector="Industrials",
        industry="Aerospace & Defense", currency="USD", price=price, shares_diluted=90.0,
        market_cap=price * 90.0, beta=2.2, revenue=revenue, ebit=-40.0,
        gross_profit=(11.0 if revenue else 0.0), net_income=-45.0, effective_tax_rate=0.0,
        da=3.0, capex=5.0, total_debt=total_debt, cash_sti=cash, interest_expense=1.0,
        invested_capital=60.0, fcf=-38.0, total_equity=70.0,
        fiscal_years=[2025, 2024, 2023],
        revenue_history=([revenue, 17.0, 9.0] if revenue else [0.0, 0.0, 0.0]),
        ebit_history=[-40.0, -30.0, -20.0], ebit_margin_history=[-0.73, -1.76, -2.2],
        ma_200=9.0, ret_6m=-0.2, ret_1m=-0.05, price_52w_high=15.0, price_52w_low=5.0,
        risk_free_rate=0.043)


def test_blend_favours_dcf_for_established_profitable():
    """A mature, profitable name should lean on the DCF, not the multiples."""
    r = value_from_company(build_nike(), CONFIG, mc_trials=300)
    b = r.fair_value_blend
    assert b.valuable and b.value > 0
    assert b.maturity > 0.7, b.maturity
    assert b.p_established == b.maturity, "legacy alias must track the maturity score"
    assert b.lenses["dcf"]["weight"] > b.lenses["multiples"]["weight"], b.lenses
    assert b.lenses["dcf"]["weight"] > b.lenses.get("growth", {}).get("weight", 0), b.lenses
    # Headline sits inside the span of the lenses it blended.
    vals = [l["value"] for l in b.lenses.values()]
    assert min(vals) <= b.value <= max(vals)
    assert b.headline_mode == "point", "a mature name gets a point value, not a growth read"


def test_blend_favours_the_growth_lens_for_cash_burning_growth():
    """A loss-making grower is valued on REVENUE, not on profit it doesn't have.

    Was: 'multiples' carried >80% of the blend, which meant a mature sector multiple
    priced a hypergrowth company (the RKLB $2.63 bug). The revenue lens carries it now.
    """
    r = value_from_company(build_growth(), CONFIG, mc_trials=300)
    b = r.fair_value_blend
    assert b.valuable
    assert b.maturity < 0.3, b.maturity
    assert b.lenses["growth"]["weight"] > 0.6, b.lenses
    assert b.growth_led is True and b.confidence == "low"
    assert r.growth_lens is not None and r.growth_lens.applies


def test_negative_dcf_is_dropped_not_averaged():
    """The RCAT bug: a negative DCF must never reach the headline figure."""
    r = value_from_company(_unprofitable(), CONFIG, mc_trials=300)
    b = r.fair_value_blend
    assert r.dcf_per_share < 0, "fixture should produce a negative DCF"
    assert b.dcf_meaningful is False
    assert "dcf" not in b.lenses, "a negative DCF must be dropped from the blend"
    assert b.valuable and b.value > 0, "revenue is present, so multiples should carry it"
    assert r.base_fair_value > 0, "headline must never be negative"


def test_dcf_still_floors_at_net_cash_when_revenue_is_gone():
    """Sanity boundary: no revenue but MORE cash than debt is genuinely worth its net
    cash, so we should still publish that rather than refuse."""
    r = value_from_company(_unprofitable(revenue=0.0), CONFIG, mc_trials=300)
    assert r.base_fair_value is not None and r.base_fair_value > 0


def test_not_valuable_when_no_lens_applies():
    """No profit, no revenue AND net debt -> refuse to publish a number, and say why."""
    r = value_from_company(_unprofitable(revenue=0.0, total_debt=200.0, cash=10.0),
                           CONFIG, mc_trials=300)
    b = r.fair_value_blend
    assert b.valuable is False
    assert b.value is None
    assert r.base_fair_value is None, "must not fall back to the negative DCF"
    assert r.upside is None
    assert "not dcf-valuable" in b.reason.lower() or "not valuable" in b.reason.lower(), b.reason
    assert b.reason in r.warnings, "the reason should surface as a warning"
    # A score is still produced (valuation sub-score just drops out).
    assert 1 <= r.score.score <= 100


def test_blend_serializes_for_the_api():
    r = value_from_company(build_nike(), CONFIG, mc_trials=200)
    d = r.to_dict()
    import json
    json.loads(json.dumps(d))                       # must be JSON-clean
    assert d["fair_value_blend"]["method"]
    assert d["dcf_per_share"] is not None
    assert d["base_fair_value"] == r.fair_value_blend.value
    # The growth lens and the same-method scenarios have to reach the UI too.
    assert d["growth_lens"] is not None and "implied_ev_sales_now" in d["growth_lens"]
    assert set(d["fair_value_scenarios"]) >= {"bear", "base", "bull", "method"}


# --------------------------------------------------------------------------- #
# Growth / pre-profit valuation (the RKLB $2.63-against-a-$65-price bug)
# --------------------------------------------------------------------------- #
def _preprofit_grower(price=65.0, revenue=600.0, shares=580.0, cash=1000.0, debt=250.0):
    """An RKLB-like name: real fast-growing revenue, deeply negative EBIT and FCF.

    The old engine had nothing valid to value this on — both equity yields are
    negative, so it fell through to a mature sector EV/Sales benchmark.
    """
    from valuation.data.models import CompanyData
    return CompanyData(
        ticker="ROCK", name="Pre-profit Grower", sector="Industrials",
        industry="Aerospace & Defense", currency="USD", price=price, shares_diluted=shares,
        market_cap=price * shares, beta=2.2, revenue=revenue, ebit=-0.33 * revenue,
        gross_profit=0.34 * revenue, net_income=-0.33 * revenue, effective_tax_rate=0.0,
        da=44.0, capex=100.0, total_debt=debt, cash_sti=cash, interest_expense=12.0,
        invested_capital=900.0, fcf=-0.5 * revenue, total_equity=1100.0,
        fiscal_years=[2025, 2024, 2023],
        revenue_history=[revenue, revenue / 1.38, revenue / 2.1],
        ebit_history=[-198.0, -182.0, -136.0], ebit_margin_history=[-0.33, -0.42, -0.48],
        analyst_rev_growth_next=1.42,
        ma_200=50.0, ret_6m=0.5, ret_1m=0.1, price_52w_high=70.0, price_52w_low=20.0,
        risk_free_rate=0.043)


def test_growth_lens_values_a_preprofit_name_on_revenue():
    """The headline must come from revenue, not from a mature sector multiple."""
    r = value_from_company(_preprofit_grower(), CONFIG, mc_trials=300)
    b, g = r.fair_value_blend, r.growth_lens
    assert r.dcf_per_share < 0, "fixture should still produce a negative DCF"
    assert g is not None and g.applies, g.reason if g else "no growth lens"
    assert b.valuable and b.value > 0
    assert b.lenses["growth"]["weight"] > 0.6, b.lenses
    # The growth lens must beat the naive mature-multiple read it replaced.
    assert g.value > r.comps.comps_fair_value, (g.value, r.comps.comps_fair_value)
    # …and it reports the sales multiple its own arithmetic justifies TODAY.
    assert g.implied_ev_sales_now > 0
    assert g.current_ev_sales > g.implied_ev_sales_now, "fixture is priced above our read"


def test_growth_name_leads_with_the_implied_growth_read():
    """Item 4 of the brief: a growth name's headline is the reverse-DCF read, and the
    point value is presented as a range with low confidence."""
    r = value_from_company(_preprofit_grower(), CONFIG, mc_trials=300)
    b = r.fair_value_blend
    assert b.growth_led is True
    assert b.headline_mode == "implied_growth"
    assert "%" in b.headline and "growth" in b.headline.lower()
    assert b.confidence == "low"
    assert b.value_low is not None and b.value_high is not None
    assert b.value_low < b.value < b.value_high


def test_scenario_cards_use_the_same_method_as_the_headline():
    """Item 5: bear/base/bull must not be the excluded (negative) DCF cone."""
    for build in (_preprofit_grower, build_growth, build_nike):
        r = value_from_company(build(), CONFIG, mc_trials=300)
        s = r.fair_value_scenarios
        assert s["base"] is not None
        assert abs(s["base"] - r.fair_value_blend.value) < 1e-6, "base card must equal the headline"
        assert s["bear"] < s["base"] < s["bull"], s
        assert s["bear"] > 0, "a scenario card must never show a negative value"
        assert s["method"], "the cards have to say how they were built"


def test_implied_growth_says_at_least_when_the_solver_hits_its_bound():
    """A saturated reverse DCF is a floor, not an estimate — say so."""
    r = value_from_company(_preprofit_grower(price=400.0), CONFIG, mc_trials=200)
    assert r.reverse.implied_growth_bounded == "above", r.reverse.implied_growth_bounded
    assert "at least" in r.reverse.growth_verdict.lower()
    assert "at least" in r.fair_value_blend.headline.lower()


def test_maturity_score_orders_companies():
    from valuation.engine.growth import maturity_score
    mature, _ = maturity_score(op_margin=0.18, fcf_margin=0.15, growth=0.04, market_cap=200000)
    middling, _ = maturity_score(op_margin=0.06, fcf_margin=0.04, growth=0.20, market_cap=8000)
    early, _ = maturity_score(op_margin=-0.35, fcf_margin=-0.50, growth=0.60, market_cap=800)
    assert mature > 0.8 and early < 0.2, (mature, early)
    assert mature > middling > early
    # No inputs at all -> genuinely undecided, not a confident guess either way.
    assert maturity_score()[0] == 0.5


def test_growth_lens_scales_the_multiple_with_the_growth_rate():
    """'Revenue multiples scaled to the growth rate': a faster grower is worth more
    per dollar of TODAY's revenue, all else equal."""
    from valuation.engine.growth import compound_growth, fade_path, growth_equity_value
    slow = fade_path(0.05, 0.03, 8)
    fast = fade_path(0.45, 0.03, 8)
    eq_slow, ev_slow, _ = growth_equity_value(100.0, slow, 8, 2.0, 0.12, mature_rate=0.09)
    eq_fast, ev_fast, _ = growth_equity_value(100.0, fast, 8, 2.0, 0.12, mature_rate=0.09)
    assert ev_fast > 3 * ev_slow, (ev_slow, ev_fast)
    assert compound_growth(fast, 8) > compound_growth(slow, 8)
    # Net debt is bridged, not ignored: the same business with debt is worth less.
    eq_levered, _, _ = growth_equity_value(100.0, fast, 8, 2.0, 0.12, net_debt=500.0,
                                           mature_rate=0.09)
    assert abs((eq_fast - eq_levered) - 500.0) < 1e-6


def test_growth_lens_degenerates_to_a_sales_multiple_when_mature():
    """No cliff between the archetypes: at maturity the horizon is 0 and the lens is
    just 'revenue x multiple', which is what a mature name should get."""
    from valuation.engine.growth import growth_equity_value, years_to_maturity
    assert years_to_maturity(10, 1.0) == 0.0
    eq, ev, rev_h = growth_equity_value(100.0, [0.4] * 5, 0.0, 2.5, 0.12, mature_rate=0.09)
    assert abs(ev - 250.0) < 1e-9 and abs(rev_h - 100.0) < 1e-9


def test_growth_lens_charges_the_losses_it_has_to_fund():
    """Cash raised to cover operating losses is dilution an exit multiple never pays
    back, so it is charged. Profitable years are not credited (one-sided by design)."""
    from valuation.engine.growth import operating_loss_pv
    losses = operating_loss_pv(100.0, [0.3] * 5, [-0.2] * 5, 5, 0.13, 0.09)
    assert losses > 0
    profits = operating_loss_pv(100.0, [0.3] * 5, [0.2] * 5, 5, 0.13, 0.09)
    assert profits == 0.0
    r = value_from_company(_preprofit_grower(), CONFIG, mc_trials=200)
    assert r.growth_lens.funding_gap_pv > 0, "a cash burner must be charged for its burn"


def test_exit_multiple_is_anchored_to_mature_fundamentals():
    """A sector's CURRENT EV/Sales embeds the growth it's expected to deliver. Using it
    as an EXIT multiple, after already compounding revenue to the horizon, counts that
    growth twice — so a frothy benchmark is capped against the fundamental anchor."""
    from valuation.engine.growth import exit_sales_multiple, fundamental_sales_multiple
    fund = fundamental_sales_multiple(0.27, mature_rate=0.09, terminal_growth=0.03)
    frothy = exit_sales_multiple({"ev_sales": 30.0, "ev_ebitda": 60.0}, 0.27,
                                 mature_rate=0.09, terminal_growth=0.03)
    assert frothy <= 2.0 * fund + 1e-9, (frothy, fund)
    # A higher sustainable margin is worth a higher multiple of sales.
    assert (fundamental_sales_multiple(0.30, 0.09, 0.03)
            > fundamental_sales_multiple(0.10, 0.09, 0.03))
    assert exit_sales_multiple({}, None) is None


def _foreign_reporting(fin="KZT", px="USD", fx_rate=None, fx_unresolved=False):
    """Nike's numbers wearing a foreign reporting currency — the KSPI shape."""
    cd = build_nike()
    cd.currency, cd.financial_currency = px, fin
    cd.fx_rate, cd.fx_unresolved = fx_rate, fx_unresolved
    return cd


def test_unresolved_fx_refuses_to_publish_a_fair_value():
    """BUG 1, half 2. `yahoo.fetch` sets fx_unresolved when statements are in one currency,
    the price in another, and the FX rate can't be fetched. Nothing downstream had ever
    acted on it, so the engine published a fair value built from unknown units. It must
    now refuse — silently emitting a number here is the whole failure mode."""
    r = value_from_company(_foreign_reporting(fx_unresolved=True), CONFIG, mc_trials=200)
    assert r.base_fair_value is None, "must not publish a fair value on unresolved FX"
    assert r.upside is None, "and must not publish an upside derived from it"
    b = r.fair_value_blend
    assert b.valuable is False, "the UI's not-valuable state is keyed on this"
    assert "KZT" in b.reason and "USD" in b.reason, b.reason
    assert b.reason in r.warnings, "the refusal must surface to the reader"


def test_unconverted_foreign_currency_refuses_to_publish():
    """Currencies differ and NO conversion was applied (fx_rate is None) — the P7 shape,
    where local-currency cash flows get compared to a USD share price."""
    r = value_from_company(_foreign_reporting(fin="JPY", fx_rate=None), CONFIG, mc_trials=200)
    assert r.base_fair_value is None and r.upside is None
    assert "JPY" in r.fair_value_blend.reason


def test_resolved_fx_still_publishes():
    """The guard must not fire merely because a name reports abroad. A converted name is
    valuable like any other — otherwise the fix would just blank every ADR."""
    r = value_from_company(_foreign_reporting(fin="JPY", fx_rate=0.0067), CONFIG, mc_trials=200)
    assert r.base_fair_value is not None and r.base_fair_value > 0
    assert r.fair_value_blend.valuable is True


def test_fair_value_far_above_price_is_withheld_not_warned():
    """KSPI shipped $1,249.16 against a $92.00 price (+1,258%) with a warning attached
    saying it was 'almost certainly a data problem' — and printed the number anyway.
    The threshold that produced that warning is now binding."""
    cd = build_nike()
    cd.price = (cd.price or 100.0) / 40.0          # same model, implausible price
    r = value_from_company(cd, CONFIG, mc_trials=200)
    assert r.base_fair_value is None, "a >5x fair value must not be published"
    assert r.upside is None
    assert "Cannot value this name" in r.fair_value_blend.reason
    assert any("Cannot value this name" in w for w in r.warnings)


def test_guard_leaves_a_normal_name_alone():
    """The guard must be inert on the reference model — a fix that suppresses good names
    is not a fix."""
    r = value_from_company(build_nike(), CONFIG, mc_trials=200)
    assert r.base_fair_value is not None and r.base_fair_value > 0
    assert r.fair_value_blend.valuable is True
    assert not any("Cannot value this name" in w for w in r.warnings)


def test_flat_revenue_capex_heavy_name_flags_its_reinvestment_shortfall():
    """CHTR's forecast reinvests $79M in year 1 against $2,948M of observed net capital
    spend (capex $11,659M - D&A $8,711M). Reinvestment is modelled as
    `delta revenue / sales_to_capital`, which collapses toward zero when revenue is flat —
    so a cable operator is charged almost nothing to stand still. Measured across 241
    names: 34 are undercharged by >5% of revenue, 22 by >10% (SRE 57.9%, ORCL 54.7%).

    Flagged, NOT corrected — changing how reinvestment is modelled moves every valuation
    and needs its own pre-registered task. The guard must SAY SO."""
    cd = build_nike()
    cd.capex, cd.da = 11_659.0, 1_000.0        # heavy net capex
    cd.revenue_history = [cd.revenue, cd.revenue, cd.revenue]   # flat -> no growth capital
    r = value_from_company(cd, CONFIG, mc_trials=200)
    b = r.scenarios.base
    assert b.observed_net_capex == 10_659.0
    assert b.reinvestment_y1 is not None
    assert b.reinvestment_y1 < b.observed_net_capex, (
        "flat revenue must reinvest less than observed net capex — that IS the defect")
    assert any("net capital spend" in w for w in r.warnings), r.warnings

    # a name that already reinvests above its net capex must stay quiet
    quiet = build_nike()
    quiet.capex, quiet.da = 500.0, 2_000.0     # D&A exceeds capex -> negative net capex
    rq = value_from_company(quiet, CONFIG, mc_trials=200)
    assert not any("net capital spend" in w for w in rq.warnings), rq.warnings


def test_withheld_valuation_contributes_nothing_to_the_score():
    """KSPI printed a valuation sub-score of 100.0/100 and a composite of 93 "Strong Buy"
    on a name the model had DECLINED to value. Passing base_fv=None dropped only the
    margin-of-safety term (0.55); `mc.prob_undervalued` (0.30) — the share of Monte Carlo
    trials OF THE WITHHELD DCF beating the price, 1.00 on KSPI — and `comps_fair_value`
    (0.15, $326.32 against a $92.19 price) rebuilt it."""
    from valuation.engine.scoring import compute_score
    from valuation.engine.blend import FairValueBlend

    cd = build_nike()
    cls = classify(cd)
    w = compute_wacc(cd, CONFIG).wacc

    class _MC:      prob_undervalued = 1.0
    class _Comps:   comps_fair_value = cd.price * 3.5

    withheld = FairValueBlend(value=None, valuable=False,
                              withheld_value=cd.price * 13.6, reason="Cannot value this name")
    s = compute_score(cd, cls, w, base_fv=None, mc=_MC(), comps=_Comps(), blend=withheld)
    assert s.subscores["valuation"] is None, (
        f"valuation sub-score {s.subscores['valuation']} — nothing derived from a withheld "
        f"valuation may enter the score")
    assert not any("of trials value it above the price" in d for d in s.drivers), s.drivers
    assert not any("Comps imply" in d for d in s.drivers), s.drivers
    # the four uncontaminated sub-scores still carry a partial score
    assert s.subscores["quality"] is not None and s.subscores["momentum"] is not None
    assert 1 <= s.score <= 100


def test_absurd_value_cap_still_fires_when_the_value_is_withheld():
    """The cap read `if base_fv and ...`, so it could not fire once the guard set
    base_fv=None: PUBLISHING a 13.6x fair value capped KSPI at 50, while WITHHOLDING it let
    KSPI print 93. A safety check that only works when the unsafe thing is present is worse
    than no check."""
    from valuation.engine.scoring import compute_score
    from valuation.engine.blend import FairValueBlend

    cd = build_nike()
    cls = classify(cd)
    w = compute_wacc(cd, CONFIG).wacc

    class _MC:      prob_undervalued = 1.0
    class _Comps:   comps_fair_value = cd.price * 3.5

    withheld = FairValueBlend(value=None, valuable=False, withheld_value=cd.price * 13.6)
    s = compute_score(cd, cls, w, base_fv=None, mc=_MC(), comps=_Comps(), blend=withheld)
    assert s.score <= 50, f"a 13.6x withheld valuation must still cap the score, got {s.score}"
    assert s.confidence == "low"
    assert any("implausible" in d.lower() for d in s.drivers), s.drivers


def test_implausible_analyst_growth_is_rejected_not_clamped():
    """THE root cause of the $2,471 Merck DCF. `analyst_rev_growth_next` was being fed an
    EARNINGS growth estimate (yahoo.py:293 reads the `stockTrend` column), which explodes
    off a negative base: GILD 15.0829, MRK 2.4942. The old blend CLAMPED that to 1.00,
    which reads as a legitimate 100% revenue forecast — so two mature pharma names were
    classified HYPERGROWTH and modelled at 60% growth for 10 years (revenue x17.2).

    Garbage must be DISCARDED, not squashed onto the edge of the valid range."""
    from valuation.engine.classify import _blended_growth
    cd = build_nike()
    # MRK's actual reported revenue: 1.3% TTM, 3.1% 3y CAGR
    cd.revenue = 65011.0
    cd.revenue_history = [65011.0, 64168.0, 60115.0, 59283.0]
    cd.fiscal_years = [2025, 2024, 2023, 2022]
    g3, gt = cd.rev_cagr_3y, cd.rev_growth_ttm

    cd.analyst_rev_growth_next = 2.4942                  # MRK's contaminated value
    g = _blended_growth(cd)
    assert g is not None and g < 0.10, (
        f"blended growth {g:.3f} — a 249% 'revenue growth' must be rejected, not clamped")
    assert abs(g - (g3 * 0.3 + gt * 0.2) / 0.5) < 1e-9, "must fall back to CAGR+TTM"

    cd.analyst_rev_growth_next = 15.0829                 # GILD's
    assert _blended_growth(cd) < 0.10

    # ...and a plausible estimate is still used, at its full weight
    cd.analyst_rev_growth_next = 0.08
    assert abs(_blended_growth(cd) - (0.08 * 0.5 + g3 * 0.3 + gt * 0.2)) < 1e-9


def test_mature_pharma_is_not_classified_hypergrowth():
    """The consequence the rejection exists to prevent: a 1-3%-growth name must not be
    handed a hypergrowth regime and a 60% start growth."""
    cd = build_nike()
    cd.revenue = 65011.0
    cd.revenue_history = [65011.0, 64168.0, 60115.0, 59283.0]
    cd.fiscal_years = [2025, 2024, 2023, 2022]
    cd.analyst_rev_growth_next = 2.4942
    cls = classify(cd)
    assert cls.regime != "hypergrowth", cls.regime
    a = build_base_assumptions(cd, cls, cd.risk_free_rate, CONFIG)
    assert a.start_growth < 0.10, a.start_growth
    assert a.n_years <= 7, "a mature name must not get the 10-year hypergrowth runway"


def test_low_beta_defensive_name_does_not_degenerate_the_terminal_value():
    """The MRK/GILD/CI/CHTR shape. A genuinely low-beta defensive large-cap gets a low
    WACC, and terminal growth is set independently at 3.0% — so `TV = FCF/(WACC - g)` ran
    on a 1.8-3.1pp denominator and produced $1,700-$2,500 fair values against $128-$282
    prices. Those betas are REAL (independently re-estimated: GILD 0.336 vs Yahoo 0.336,
    CHTR 0.678 vs 0.668), so the fix cannot be "assume the beta is wrong".

    Written during the Part 2 investigation and confirmed failing against the 0.005 floor
    (`terminal spread 2.19%`); restored now that MIN_TERMINAL_SPREAD = 0.030 ships."""
    from valuation.engine.dcf import run_dcf

    cd = build_nike()
    cd.beta = 0.21                      # MRK's actual beta
    w = compute_wacc(cd, CONFIG)
    a = build_base_assumptions(cd, classify(cd), w.risk_free, CONFIG)
    r = run_dcf(cd, a, w.wacc)

    spread = r.wacc - r.terminal_growth
    assert spread >= 0.03 - 1e-9, (
        f"terminal spread {spread:.2%} — a perpetuity discounted only {spread:.2%} above "
        f"its own growth rate is a division by near-zero, not a valuation")
    assert r.terminal_multiple is not None and r.terminal_multiple <= 1 / 0.03 + 1e-6, (
        f"implied terminal multiple {r.terminal_multiple:.1f}x terminal FCFF")
    # the effective growth must be reported honestly when the clamp binds
    if r.assumed_terminal_growth is not None and r.assumed_terminal_growth > r.terminal_growth:
        assert abs(r.terminal_growth - (r.wacc - 0.03)) < 1e-9


def test_healthy_name_is_untouched_by_the_terminal_clamp():
    """Do-no-harm: the clamp must not bind on a normal-beta name, or the fix is a
    universe-wide repricing wearing a bug fix's clothes."""
    from valuation.engine.dcf import run_dcf
    from valuation.engine.assumptions import build_base_assumptions

    cd = build_nike()                   # beta ~1
    w = compute_wacc(cd, CONFIG)
    a = build_base_assumptions(cd, classify(cd), w.risk_free, CONFIG)
    r = run_dcf(cd, a, w.wacc)
    assert r.terminal_growth == a.terminal_growth, "clamp must not bind on a normal name"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    ok = _run_all()
    sys.exit(0 if ok else 1)
