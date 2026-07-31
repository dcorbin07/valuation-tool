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


def _scan(tmp=None):
    # A FIXED db path persisted across runs (snapshots are keyed by scan date, so re-running
    # on the same day layered rows onto the previous run's). Each call now gets its own file,
    # so these tests cannot influence each other or a previous invocation.
    if tmp is None:
        import tempfile
        tmp = os.path.join(tempfile.mkdtemp(prefix="valquo_test_"), "screener.db")
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
    # build_portfolio rounds each weight to 4dp, so the sum can legitimately drift by up to
    # n * 5e-5. The old 1e-6 bound was ~750x tighter than the rounding allows and passed only
    # when the weights happened to round favourably — an intermittent failure, observed once.
    assert abs(tot - 1.0) < len(pf["positions"]) * 5e-5, tot
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


def _fv_row(ticker, price, sector, ey=None, fcfy=None, fair_value=None):
    extra = {}
    if ey is not None:
        extra["earnings_yield"] = ey
    if fcfy is not None:
        extra["fcf_yield"] = fcfy
    return {"ticker": ticker, "price": price, "sector": sector,
            "fair_value": fair_value, "upside": None, "extra": extra}


def test_fair_value_estimate_reprices_to_peer_median():
    """A name yielding twice its sector's median should be worth ~2x its price."""
    from valuation.screener.fairvalue import estimate_fair_values
    # Six peers at a 5% earnings yield, plus one at 10% (twice as cheap).
    rows = [_fv_row(f"P{i}", 100.0, "Tech", ey=0.05) for i in range(6)]
    rows.append(_fv_row("CHEAP", 100.0, "Tech", ey=0.10))
    n = estimate_fair_values(rows)
    assert n == 7, f"expected all 7 estimated, got {n}"
    cheap = rows[-1]
    assert abs(cheap["fair_value"] - 200.0) < 1e-6, cheap["fair_value"]
    assert abs(cheap["upside"] - 1.0) < 1e-6, cheap["upside"]
    assert cheap["fair_value_method"] == "multiples"
    # A peer trading exactly at the median is worth about its price.
    assert abs(rows[0]["fair_value"] - 100.0) < 1e-6


def test_fair_value_never_overwrites_a_dcf():
    from valuation.screener.fairvalue import estimate_fair_values
    rows = [_fv_row(f"P{i}", 100.0, "Tech", ey=0.05) for i in range(6)]
    rows.append(_fv_row("DCF", 100.0, "Tech", ey=0.50, fair_value=123.0))
    estimate_fair_values(rows)
    dcf = rows[-1]
    assert dcf["fair_value"] == 123.0, "a real DCF value must survive"
    assert dcf["fair_value_method"] == "dcf"


def test_fair_value_skips_unusable_inputs_and_clamps():
    """Loss-makers (negative yield) get no estimate; extremes are clamped, not absurd."""
    from valuation.screener.fairvalue import estimate_fair_values, MAX_RERATE
    rows = [_fv_row(f"P{i}", 100.0, "Tech", ey=0.05) for i in range(6)]
    rows.append(_fv_row("LOSS", 100.0, "Tech", ey=-0.08))     # loss-making
    rows.append(_fv_row("NOPRICE", None, "Tech", ey=0.05))    # no price
    rows.append(_fv_row("NODATA", 100.0, "Tech"))             # no yields at all
    rows.append(_fv_row("WILD", 100.0, "Tech", ey=5.0))       # 100x the peer median
    estimate_fair_values(rows)
    assert rows[-4]["fair_value"] is None, "loss-maker must not get a fair value"
    assert rows[-3]["fair_value"] is None, "no price -> no estimate"
    assert rows[-2]["fair_value"] is None, "no inputs -> no estimate"
    assert abs(rows[-1]["fair_value"] - 100.0 * MAX_RERATE) < 1e-6, "must clamp the re-rate"


def test_fair_value_thin_sector_falls_back_to_universe():
    """A sector with too few peers must borrow the universe median, not self-anchor."""
    from valuation.screener.fairvalue import estimate_fair_values
    rows = [_fv_row(f"P{i}", 100.0, "Tech", ey=0.05) for i in range(8)]
    rows.append(_fv_row("LONE", 100.0, "Utilities", ey=0.10))   # only name in its sector
    estimate_fair_values(rows)
    lone = rows[-1]
    # Universe median is ~0.05, so the lone name re-rates up rather than to itself (1.0x).
    assert lone["fair_value"] > 150.0, lone["fair_value"]


def test_fair_value_medians_come_from_peer_rows_not_the_slice():
    """Passing a full population keeps the peer group stable when only a slice is shown."""
    from valuation.screener.fairvalue import estimate_fair_values
    everyone = [_fv_row(f"P{i}", 100.0, "Tech", ey=0.05) for i in range(10)]
    shown = [_fv_row("CHEAP", 100.0, "Tech", ey=0.10)]
    estimate_fair_values(shown, peer_rows=everyone + shown)
    assert abs(shown[0]["fair_value"] - 200.0) < 1e-6, shown[0]["fair_value"]


def test_ticker_search_endpoint_ranks_exact_first():
    try:
        from valuation.web.app import app
    except ImportError as e:                    # web deps (Flask et al) aren't installed
        print(f"         -> skipped, needs the web deps: {e}")
        return
    c = app.test_client()
    r = c.get("/api/tickers?q=AAPL")
    assert r.status_code == 200, r.status_code
    res = r.get_json()["results"]
    assert res and res[0]["ticker"] == "AAPL", res[:3]
    # Empty query returns nothing rather than the whole universe.
    assert c.get("/api/tickers?q=").get_json()["results"] == []
    # Prefix search surfaces multiple candidates.
    many = c.get("/api/tickers?q=A").get_json()["results"]
    assert len(many) > 1 and all(m["ticker"].startswith("A") or "A" in m["ticker"] for m in many)


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
