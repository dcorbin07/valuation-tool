"""
Screener + backtest tests (offline, synthetic). Run:
    python tests/test_screener.py     # or python -m pytest tests/
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.screener.screen import run_scan
from valuation.screener.sectors import sector_attractiveness
from valuation.screener.portfolio import build_portfolio
from valuation.screener.store import Store
from valuation.backtest.panel import build_synthetic_panel
from valuation.backtest.engine import summarize
from valuation.data.models import CompanyData
from valuation.screener.providers import company_to_metrics
from tests.screener_fixtures import SyntheticProvider


def _scan(tmp="/tmp/_test_screener.db"):
    store = Store(tmp)
    res = run_scan(scope="synthetic", cfg=None, store=store,
                   provider=SyntheticProvider(14), run_dcf_top=0, save=True)
    return res, store


def test_scan_ranks_by_edge():
    res, _ = _scan()
    rows = res["rows"]
    assert res["scored"] > 100
    prov = SyntheticProvider(14)
    # rebuild edges deterministically
    edges = {r["ticker"]: prov.get_metrics(r["ticker"])["_edge"] for r in rows}
    top = sum(edges[r["ticker"]] for r in rows[:15]) / 15
    bot = sum(edges[r["ticker"]] for r in rows[-15:]) / 15
    assert top > bot + 1.0, (top, bot)          # high-edge names rank near the top
    assert rows[0]["rank"] == 1 and rows[0]["hot_score"] >= 95


def test_hot_scores_in_range():
    res, _ = _scan()
    for r in res["rows"]:
        assert 1 <= r["hot_score"] <= 100
        assert r["bucket"] in {"established", "speculative"}


def test_sector_attractiveness():
    res, _ = _scan()
    sects = sector_attractiveness(res["rows"])
    assert len(sects) >= 5
    assert all("avg_composite" in s and "sector_rank" in s for s in sects)
    # sorted descending by composite
    comps = [s["avg_composite"] for s in sects if s["avg_composite"] is not None]
    assert comps == sorted(comps, reverse=True)


def test_portfolio_sector_cap_and_weights():
    res, _ = _scan()
    pf = build_portfolio(res["rows"], n=15, weighting="score", max_sector_weight=0.30)
    tot = sum(p["weight"] for p in pf["positions"])
    assert abs(tot - 1.0) < 1e-6
    assert pf["stats"]["max_sector_weight"] <= 0.301
    assert pf["stats"]["n_names"] == 15


def test_store_roundtrip():
    res, store = _scan()
    reloaded = store.load_snapshot(top=10)
    assert len(reloaded) == 10
    assert reloaded[0]["ticker"] == res["rows"][0]["ticker"]


def test_backtest_detects_signal_rejects_noise():
    sig = summarize(build_synthetic_panel(120, 40, signal=0.12, seed=1),
                    factor_cols=["momentum", "value"], horizon_days=21)
    noise = summarize(build_synthetic_panel(120, 40, signal=0.0, seed=2),
                      factor_cols=["momentum", "value"], horizon_days=21)
    assert sig["has_edge"] is True
    assert noise["has_edge"] is False
    assert sig["ic"]["mean_ic"] > noise["ic"]["mean_ic"]


def test_currency_conversion_fixes_adr():
    # Mizuho-style ADR: statements in JPY (millions of yen), price/cap in USD.
    # This is the bug that valued MFG at $6,320 vs a $10.63 price and flooded the
    # hot list with foreign ADRs.
    cd = CompanyData(ticker="MFG", currency="USD", financial_currency="JPY")
    cd.price = 10.63
    cd.market_cap = 70000.0        # USD millions
    cd.shares_diluted = 2530.0     # ordinary-share basis (wrong for a per-ADR price)
    cd.net_income = 900000.0       # ¥900B
    cd.revenue = 4000000.0         # ¥4T
    cd.total_equity = 9000000.0    # ¥9T

    # BEFORE: mixing JPY statements with a USD cap => nonsense (P/E ~0.08, EY ~1290%)
    pre = company_to_metrics(cd)
    assert pre["earnings_yield"] > 5
    assert pre["pe"] is not None and pre["pe"] < 0.2

    # Apply what the fetch now does for an ADR (JPY->USD ≈ 0.0067) + price-consistent shares.
    cd.apply_fx(0.0067)
    cd.shares_diluted = cd.market_cap / cd.price
    post = company_to_metrics(cd)
    assert 0.02 < post["earnings_yield"] < 0.25    # ~8.6% — sane
    assert 5 < post["pe"] < 25                      # ~11.6x — sane
    assert 3000 < cd.net_income < 9000             # ~$6.0B USD net income


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} screener tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
