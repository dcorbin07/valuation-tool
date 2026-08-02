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


def test_metrics_are_in_usd_dollars_not_millions():
    """The screener's absolute figures are USD DOLLARS, and ratios are unaffected by the scale.

    This was the bug behind "$0.00 market cap" on every Index name: CompanyData carries
    millions, FMP's profile carries dollars, and both fed the same scan. Downstream — the
    10e9 large-cap floor and the UI's market_cap/1e9 — assumes dollars, so a $276B Dell
    arrived as 275,844 and rendered as $0.0B.
    """
    from valuation.screener.providers import METRICS_UNITS
    cd = CompanyData(ticker="DELL", name="Dell Technologies Inc.", sector="Technology")
    cd.price = 426.91
    cd.market_cap = 275_844.66          # CompanyData is in millions, by its own contract
    cd.net_income = 5_000.0
    cd.revenue = 100_000.0
    cd.total_equity = 3_000.0
    m = company_to_metrics(cd)

    assert m["units"] == METRICS_UNITS == "usd"
    assert abs(m["market_cap"] - 275_844.66e6) < 1.0, m["market_cap"]
    # The FMP mapper already speaks dollars — it must stamp the convention WITHOUT rescaling,
    # or every FMP row looks like a stale cache entry and gets refetched forever.
    from valuation.screener.providers import _fmp_to_metrics
    fm = _fmp_to_metrics("DELL", {"grossProfitTTM": 1.2e10}, {},
                         {"companyName": "Dell Technologies Inc.", "sector": "Technology",
                          "marketCap": 275_844_661_248, "price": 426.91})
    assert fm["units"] == "usd"
    assert fm["market_cap"] == 275_844_661_248 and fm["gross_profit"] == 1.2e10
    assert fm["name"] == "Dell Technologies Inc." and fm["sector"] == "Technology"
    assert abs(m["net_income"] - 5e9) < 1.0
    assert abs(m["revenue"] - 100e9) < 1.0
    # Ratios are unit-free and must NOT move: 5000/275844.66 either way.
    assert abs(m["earnings_yield"] - (5_000.0 / 275_844.66)) < 1e-12
    assert abs(m["pe"] - (275_844.66 / 5_000.0)) < 1e-9
    # Per-share price is not a currency aggregate and must stay untouched.
    assert m["price"] == 426.91


def test_nano_cap_floor_is_applied_in_dollars():
    from valuation.screener.factors import prefilter
    base = {"ticker": "X", "price": 20.0, "avg_dollar_volume": 5e6}
    assert prefilter({**base, "market_cap": 40e6})[0] is False     # $40M — nano-cap
    assert prefilter({**base, "market_cap": 60e6})[0] is True      # $60M — real small cap
    # The old millions-denominated comparison let a $60 company through and, worse, would
    # now reject every genuine name in a dollars-denominated scan.
    assert prefilter({**base, "market_cap": 60.0})[0] is False


def test_cache_written_before_the_usd_normalization_is_discarded():
    """A cached metrics dict with no `units` stamp holds millions — mixing it into a fresh
    scan would put two currencies' worth of scale in one cross-section."""
    from valuation.screener.providers import FMPProvider, _usable_cache

    class _FakeStore:
        def __init__(self, data):
            self.data = data
        def get_cached_fundamentals(self, ticker, max_age_days=None):
            return self.data

    assert _usable_cache({"market_cap": 275_844.66}) is None            # legacy: no stamp
    assert _usable_cache({"market_cap": 275e9, "units": "usd"}) is not None

    class _Cfg:
        fmp_api_key = "k"
    p = FMPProvider(_Cfg(), _FakeStore({"ticker": "DELL", "market_cap": 275_844.66}))
    # Legacy cache must not be returned; with no network the fetch fails and we get None,
    # which is the honest answer — not a silently mis-scaled row.
    assert p.get_metrics("DELL") is None


def test_scan_backfills_blank_company_names_and_sectors():
    """yfinance's `.info` is throttled from cloud IPs and comes back empty, so the per-name
    fetch returns a bare ticker for a name and no sector at all. The universe listing has
    both — the scan must fall back to it instead of shipping "DELL" with a blank sector."""
    from valuation.screener.screen import _fill_from_universe

    u = {"ticker": "DELL", "name": "Dell Technologies Inc.", "sector": "Technology",
         "industry": "Computer Hardware", "market_cap": 275e9}

    # The Yahoo failure mode: name falls back to the ticker, sector is empty.
    m = _fill_from_universe({"ticker": "DELL", "name": "DELL", "sector": ""}, u)
    assert m["name"] == "Dell Technologies Inc."
    assert m["sector"] == "Technology"
    assert m["market_cap"] == 275e9

    # A real fetched value always wins over the listing.
    m2 = _fill_from_universe({"ticker": "DELL", "name": "Dell Inc", "sector": "Tech",
                              "market_cap": 271e9}, u)
    assert (m2["name"], m2["sector"], m2["market_cap"]) == ("Dell Inc", "Tech", 271e9)


def test_scan_reports_display_field_coverage():
    """A blank name or sector is invisible to every scoring check, so the scan measures it."""
    res, _ = _scan()
    cov = res["health"]["display_coverage"]
    assert cov["name"] == 1.0 and cov["sector"] == 1.0 and cov["market_cap"] == 1.0, cov


def test_profile_lookup_fills_from_the_store_without_network():
    """profiles.lookup must resolve from data the live scan already fetched — no API call."""
    from valuation.screener import profiles
    res, store = _scan()
    tickers = [r["ticker"] for r in res["rows"][:5]]

    class _NoKeyCfg:
        fmp_api_key = ""
        sec_user_agent = "test test@example.com"
    got = profiles.lookup(tickers, cfg=_NoKeyCfg(), store=store, max_api=0)
    assert set(got) == set(tickers), got
    assert all(got[t]["name"] and got[t]["sector"] for t in tickers)

    # And a book row with blank fields gets decorated in place.
    rows = [{"ticker": tickers[0], "name": "", "sector": ""}]
    assert profiles.decorate(rows, cfg=_NoKeyCfg(), store=store, max_api=0) == 1
    assert rows[0]["name"] and rows[0]["sector"]


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
