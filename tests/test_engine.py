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
    assert b.p_established > 0.7, b.p_established
    assert b.lenses["dcf"]["weight"] > b.lenses["multiples"]["weight"], b.lenses
    # Headline sits between the two lenses it blended.
    lo, hi = sorted([r.dcf_per_share, r.comps.comps_fair_value])
    assert lo <= b.value <= hi


def test_blend_favours_multiples_for_cash_burning_growth():
    r = value_from_company(build_growth(), CONFIG, mc_trials=300)
    b = r.fair_value_blend
    assert b.valuable
    assert b.p_established < 0.3, b.p_established
    assert b.lenses["multiples"]["weight"] > 0.8, b.lenses


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
