"""
Screener + backtest tests (offline, synthetic). Run:
    python tests/test_screener.py     # or python -m pytest tests/
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

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


def _growth_row(ticker, price, sector, revenue=None, net_debt=None, ev_sales=None,
                op_margin=None, revenue_growth=None, gross_margin=None, market_cap=None,
                ey=None, fcfy=None, ev_ebitda=None):
    extra = {k: v for k, v in
             {"earnings_yield": ey, "fcf_yield": fcfy, "revenue": revenue,
              "net_debt": net_debt, "ev_sales": ev_sales, "ev_ebitda": ev_ebitda,
              "op_margin": op_margin, "revenue_growth": revenue_growth,
              "gross_margin": gross_margin}.items()
             if v is not None}
    return {"ticker": ticker, "price": price, "sector": sector, "market_cap": market_cap,
            "fair_value": None, "upside": None, "extra": extra}


def test_fair_value_bridges_ev_multiples_with_net_debt():
    """EV multiples used to be skipped for lack of net debt. The scan carries it now,
    so a cheap-on-EV/Sales name re-rates — and leverage is charged, not ignored."""
    from valuation.screener.fairvalue import estimate_fair_values
    # Six peers at 4x EV/Sales; two subjects at 2x (half the peer multiple), identical
    # except that one is funded with net cash and the other with net debt.
    rows = [_growth_row(f"P{i}", 100.0, "Tech", revenue=100.0, net_debt=0.0, ev_sales=4.0,
                        market_cap=400.0) for i in range(6)]
    cash = _growth_row("CASHY", 100.0, "Tech", revenue=100.0, net_debt=-100.0,
                       ev_sales=2.0, market_cap=300.0)
    lev = _growth_row("LEVY", 100.0, "Tech", revenue=100.0, net_debt=100.0,
                      ev_sales=2.0, market_cap=100.0)
    rows += [cash, lev]
    estimate_fair_values(rows)
    assert cash["fair_value"] is not None, "an EV multiple alone must now produce a value"
    # implied EV = 4x100 = 400 -> equity 500 on a 300 cap -> 100 * 500/300
    assert abs(cash["fair_value"] - 100.0 * 500.0 / 300.0) < 1e-6, cash["fair_value"]
    # Same implied EV, but the debt is subtracted: equity 300 on a 100 cap, then clamped.
    assert lev["fair_value"] is not None
    assert lev["upside"] > cash["upside"], "the levered name re-rates further off a smaller cap"


def test_fair_value_uses_ev_ebitda_where_ebitda_is_positive():
    """The EV/EBITDA half of the same bridge. EV/Sales alone can't tell a 40%-margin
    business from a 4%-margin one at the same price; EBITDA can, so a name that is cheap
    on EBITDA must re-rate on it even when it has no usable equity yield at all.

    A NEGATIVE EBITDA (so the multiple is meaningless) must be dropped, not used — that
    is the whole reason the multiple is filtered on positivity rather than presence."""
    from valuation.screener.fairvalue import estimate_fair_values
    peers = [_growth_row(f"P{i}", 100.0, "Industrials", revenue=100.0, net_debt=0.0,
                         ev_ebitda=12.0, market_cap=400.0) for i in range(6)]
    # Cheap on EBITDA (6x vs the 12x peer median) and carrying net debt, so the bridge
    # matters: implied EV = 400 x (12/6) = 800, equity = 800 - 100 = 700 on a 300 cap.
    sub = _growth_row("CHEAPEBIT", 100.0, "Industrials", revenue=100.0, net_debt=100.0,
                      ev_ebitda=6.0, market_cap=300.0)
    rows = peers + [sub]
    estimate_fair_values(rows)
    assert sub["fair_value"] is not None, "EV/EBITDA alone must produce a value"
    assert abs(sub["fair_value"] - 100.0 * 700.0 / 300.0) < 1e-6, sub["fair_value"]

    # Same name, EBITDA negative -> the multiple is not information and must be ignored.
    neg = _growth_row("BURN", 100.0, "Industrials", revenue=100.0, net_debt=100.0,
                      ev_ebitda=-6.0, market_cap=300.0)
    rows2 = [_growth_row(f"Q{i}", 100.0, "Industrials", revenue=100.0, net_debt=0.0,
                         ev_ebitda=12.0, market_cap=400.0) for i in range(6)] + [neg]
    estimate_fair_values(rows2)
    assert neg.get("fair_value") is None, neg.get("fair_value")


def test_fair_value_uses_the_growth_lens_for_a_preprofit_grower():
    """A loss-maker used to get NOTHING here (both equity yields negative). It is now
    valued on revenue, and flagged low confidence."""
    from valuation.screener.fairvalue import estimate_fair_values
    peers = [_growth_row(f"P{i}", 100.0, "Technology", revenue=100.0, net_debt=0.0,
                         ev_sales=4.0, market_cap=400.0, ey=0.04) for i in range(6)]
    grower = _growth_row("ROCK", 60.0, "Technology", revenue=600.0, net_debt=-700.0,
                         ev_sales=50.0, op_margin=-0.33, revenue_growth=0.45,
                         gross_margin=0.34, market_cap=30000.0, ey=-0.01)
    rows = peers + [grower]
    estimate_fair_values(rows)
    assert grower["fair_value"] is not None and grower["fair_value"] > 0
    assert grower["fair_value_method"] in ("growth", "blended"), grower["fair_value_method"]
    assert grower["fair_value_confidence"] == "low"
    # A mature profitable peer is NOT growth-led.
    assert peers[0]["fair_value_confidence"] == "medium"


def test_fair_value_growth_lens_rewards_faster_growth():
    from valuation.screener.fairvalue import estimate_fair_values
    def one(g):
        rows = [_growth_row(f"P{i}", 100.0, "Technology", revenue=100.0, net_debt=0.0,
                            ev_sales=4.0, market_cap=400.0) for i in range(6)]
        sub = _growth_row("SUB", 20.0, "Technology", revenue=200.0, net_debt=-50.0,
                          ev_sales=10.0, op_margin=-0.10, revenue_growth=g,
                          gross_margin=0.70, market_cap=2000.0)
        rows.append(sub)
        estimate_fair_values(rows)
        return sub["fair_value"]
    slow, fast = one(0.05), one(0.50)
    assert slow is not None and fast is not None
    assert fast > slow * 1.5, (slow, fast)


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
        def cache_fundamentals(self, ticker, data):
            self.data = data

    from valuation.screener.providers import METRICS_SCHEMA
    assert _usable_cache({"market_cap": 275_844.66}) is None            # legacy: no stamp
    assert _usable_cache({"market_cap": 275e9, "units": "usd",
                          "schema": METRICS_SCHEMA}) is not None

    class _Cfg:
        fmp_api_key = "k"
    p = FMPProvider(_Cfg(), _FakeStore({"ticker": "DELL", "market_cap": 275_844.66}))
    p._get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network"))
    p._free_fallback = lambda t: None
    # Legacy cache must not be returned; with nothing else able to serve the name we get
    # None, which is the honest answer — not a silently mis-scaled row.
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


def test_api_keys_never_reach_the_health_block():
    """`requests` puts the full URL — query string and all — in its HTTPError text, and the
    universe note is served publicly by /api/hotstocks. Redact before it can be stored."""
    from valuation.screener.providers import _redact
    key = "DkkPylwVxZZ91CAiCOhXshz7fQbETlUS"          # shape only; not a live credential
    for msg in (f"402 Client Error for url: https://x/company-screener?exchange=NYSE&apikey={key}",
                f"failed https://api.tradier.com/v1/q?token={key}&y=1",
                f"Authorization: Bearer {key}"):
        out = _redact(msg)
        assert key not in out, out
        assert "<redacted>" in out, out


def test_fmp_universe_falls_back_for_the_scope_that_was_asked_for():
    """The fallback hardcoded "bundled", so a whole_market scan silently became a 191-name
    scan when FMP's screener 402'd. It must fall back for the SCOPE requested."""
    from valuation.screener.providers import FMPProvider

    class _Cfg:
        fmp_api_key = "k"
        tradier_token = ""            # no broker -> chain continues past it
        sec_user_agent = "test test@example.com"
        universe_limit = 0

    p = FMPProvider(_Cfg())
    p._get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("402 Payment Required"))
    # EDGAR is a network call, so stub the whole free chain and assert the SCOPE is passed on.
    seen = {}
    import valuation.screener.providers as P

    class _Free:
        universe_note = ""
        def __init__(self, *a, **k): pass
        def get_universe(self, scope):
            seen["scope"] = scope
            return [{"ticker": "AAA", "name": "A", "sector": "", "industry": "",
                     "market_cap": None}] * 900
    orig = P.FreeProvider
    try:
        P.FreeProvider = _Free
        rows = p.get_universe("whole_market")
    finally:
        P.FreeProvider = orig
    assert seen["scope"] == "whole_market", seen
    assert len(rows) == 900
    assert "no bulk endpoint" in p.universe_note


def test_fmp_budget_and_circuit_breaker_fall_back_instead_of_dropping_names():
    """A per-scan FMP ceiling bounds SPEND, not how many names get ranked — and once the
    subscription starts refusing symbols we stop paying to rediscover that every time."""
    from valuation.screener.providers import FMPProvider

    def _provider(max_calls):
        class _Cfg:
            fmp_api_key = "k"
            fmp_max_calls = max_calls
        p = FMPProvider(_Cfg())
        p._get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("402 premium symbol"))
        p._free = _Stub()
        return p

    class _Stub:                       # stands in for the free stack; always serves
        def get_metrics(self, t):
            return {"ticker": t, "units": "usd", "market_cap": 1e10}

    # Budget: only 2 names' worth of calls, but all 20 names still get ranked.
    p = _provider(6)
    got = [p.get_metrics(f"T{i}") for i in range(20)]
    assert all(g is not None for g in got), "no name may be dropped just because FMP refused it"
    b = p.budget
    assert b["calls_used"] == 6, b                     # spend is bounded...
    assert b["served_by_free_fallback"] == 20, b       # ...coverage is not
    assert b["served_by_fmp"] == 0 and b["fmp_errors"] == 2, b

    # Uncapped: the breaker must stop paying to rediscover a refusing subscription.
    p2 = _provider(0)
    for i in range(40):
        assert p2.get_metrics(f"T{i}") is not None
    b2 = p2.budget
    assert b2["fmp_disabled_mid_scan"] is True, b2
    assert b2["fmp_errors"] == FMPProvider.FAIL_STREAK_OFF, b2
    assert b2["served_by_free_fallback"] == 40, b2


def test_broker_universe_normalizes_class_share_symbols():
    """Tradier writes BRK/B; the fundamentals feeds and yfinance want BRK-B. Unconverted,
    some of the largest companies in the market silently fail every lookup."""
    from valuation.screener import broker_universe as B
    assert B.normalize("BRK/B") == "BRK-B"
    assert B.normalize("bf/b") == "BF-B"
    assert B.normalize("AAPL") == "AAPL"


def test_broker_universe_ranks_by_liquidity_and_drops_junk():
    from valuation.screener import broker_universe as B

    class _Cfg:
        tradier_token = "t"
        tradier_env = "live"
    names = {"BIG": "Big Co", "SMALL": "Small Co", "PENNY": "Penny Co",
             "THIN": "Thin Co", "BRK/B": "Berkshire"}
    quotes = {
        "BIG":   {"symbol": "BIG", "type": "stock", "last": 100.0, "average_volume": 5e6,
                  "week_52_high": 125.0},
        "SMALL": {"symbol": "SMALL", "type": "stock", "last": 20.0, "average_volume": 1e5},
        "PENNY": {"symbol": "PENNY", "type": "stock", "last": 0.40, "average_volume": 9e9},
        "THIN":  {"symbol": "THIN", "type": "stock", "last": 50.0, "average_volume": 10},
        "BRK/B": {"symbol": "BRK/B", "type": "stock", "last": 400.0, "average_volume": 4e6},
    }
    B_list, B_quote = B.list_symbols, B.quote_batch
    try:
        B.list_symbols = lambda cfg=None, session=None: names
        B.quote_batch = lambda t, cfg=None, session=None: quotes
        rows = B.build(_Cfg(), limit=10)
    finally:
        B.list_symbols, B.quote_batch = B_list, B_quote

    tickers = [r["ticker"] for r in rows]
    assert "PENNY" not in tickers, "sub-$1 names are not investable"
    assert "THIN" not in tickers, "illiquid names must not consume a fundamentals call"
    assert "BRK-B" in tickers, tickers
    # Most liquid first: BIG ($500M/day) then BRK-B ($1.6B/day)... check the actual order.
    advs = [r["avg_dollar_volume"] for r in rows]
    assert advs == sorted(advs, reverse=True), advs
    big = next(r for r in rows if r["ticker"] == "BIG")
    assert abs(big["high_prox"] - 0.8) < 1e-9          # 100 / 125
    assert big["market_cap"] is None                   # the broker doesn't publish it


def test_freshness_counts_trading_days_not_calendar_days():
    """A Friday scan read on Sunday is current. Flagging it as two days stale trains the
    reader to ignore the badge, which is how staleness warnings stop working."""
    import datetime as dt
    from valuation.screener.freshness import status, trading_days_between

    fri, sun, mon = dt.date(2026, 7, 31), dt.date(2026, 8, 2), dt.date(2026, 8, 3)
    assert trading_days_between(fri, sun) == 0
    assert trading_days_between(fri, mon) == 1
    assert status(fri.isoformat(), today=sun)["level"] == "fresh"

    # The real failure: the scan died on 07-29 and the site served it for days.
    late = status("2026-07-29", today=dt.date(2026, 8, 6))
    assert late["level"] == "stale" and late["stale"] is True
    assert "2026-07-29" in late["message"]
    # No date at all must read as "undated", never as fresh.
    unknown = status(None)
    assert unknown["level"] == "unknown" and unknown["stale"] is True


def test_live_track_never_annualizes_a_stub_or_leads_with_it():
    """The whole point of the live column: a short track is shown but cannot be the headline,
    and a handful of days is never compounded into a yearly rate."""
    from valuation.screener import index_track as T

    def _series(n):
        return {"inception_date": "2026-07-01", "benchmark": "SPY",
                "series": [{"date": f"2026-{7 + d // 28:02d}-{(d % 28) + 1:02d}",
                            "valquo": 0.30 * (d + 1) + (0.05 if d % 3 else -0.04),
                            "spy": 0.20 * (d + 1)} for d in range(n)]}

    class _St:
        def __init__(self, d): self.d = d
        def get_meta(self, k, default=None): return self.d

    thin = T.summarize("roth", meta_path="/nope", history_path="/nope", store=_St(_series(5)))
    assert thin["available"] is True and thin["days"] == 5
    assert thin["thin"] is True
    assert thin["headline"] == "backtested", "5 days must never lead"
    assert thin["live"]["ann_alpha"] is None, "must not compound 5 days into a yearly rate"
    assert thin["live"]["sharpe"] is None, "too few points for a meaningful stdev"
    assert thin["live"]["cum_valquo_pct"] is not None, "cumulative IS honest to show"

    # AMENDED 2026-08-09 (Part 10). This used to read:
    #     assert long["thin"] is False and long["headline"] == "live"
    # i.e. it PINNED the defect — that 60 trading days alone promotes the live number to the
    # headline and drops the "too early to judge" pill, automatically, with nobody approving
    # it. The paper-track contract makes that a decision, not a date, so the day count is now
    # necessary and not sufficient. The claim this test still owns is the ANNUALISATION rule:
    # past the floor, ann_alpha is computed. That is a value and it is unchanged.
    long = T.summarize("roth", meta_path="/nope", history_path="/nope", contract="/nope",
                       store=_St(_series(T.MIN_LIVE_DAYS + 5)))
    assert long["headline"] == "backtested", "day count alone must never promote the live number"
    assert long["thin"] is True
    assert long["live"]["ann_alpha"] is not None

    # Backtested figures always travel with the live ones, never merged into them.
    # AMENDED 2026-08-08 (P2 crowding-memo sweep). This pinned the literal 1.17, which was the
    # PRE-B6 2,710-name figure; the corrected 69-date panel reads 1.10 and the settings block
    # was re-measured, so the literal failed. The claim under test is the PLUMBING — that the
    # backtested block is populated from the book config and kept separate from the live one —
    # and the specific number was never what it was asserting. Pointing it at the config keeps
    # the claim, stops it rotting on every legitimate re-measurement, and the not-None check
    # stops an empty dict from satisfying it vacuously.
    from valuation.screener import settings as _S
    _want = _S.BOOK_CONFIGS["roth"]["measured"]["net_sharpe"]
    assert _want is not None
    assert thin["backtested"]["net_sharpe"] == _want
    assert "live" not in (thin["backtested"].get("basis") or "")


def test_live_track_suppresses_an_implausible_sharpe():
    """A near-constant excess series drives the denominator to zero and the ratio to
    infinity. 'Sharpe 444' on the page would discredit every other number on it."""
    from valuation.screener import index_track as T

    class _St:
        def get_meta(self, k, default=None):
            return {"inception_date": "2026-01-01", "benchmark": "SPY",
                    "series": [{"date": f"2026-01-{d:02d}", "valquo": 0.3 * d, "spy": 0.2 * d}
                               for d in range(1, 26)]}          # perfectly linear
    out = T.summarize("roth", meta_path="/nope", history_path="/nope", store=_St())
    assert out["days"] == 25
    assert out["live"]["sharpe"] is None, out["live"]["sharpe"]


# --------------------------------------------------------------------------- #
# The contract gate (Part 10). `index_track.MIN_LIVE_DAYS = 60` used to flip the
# public posture on its own, on a date already fixed by the inception. See
# PAPER_TRACK_CONTRACT.md §5 and index_track's module docstring, rule 3.
# --------------------------------------------------------------------------- #
def _contract(body: str) -> str:
    """A throwaway contract file containing `body`."""
    import tempfile
    d = tempfile.mkdtemp(prefix="valquo_contract_")
    p = os.path.join(d, "PAPER_TRACK_CONTRACT.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


def _track_store(n):
    class _St:
        def get_meta(self, k, default=None):
            return {"inception_date": "2026-07-30", "benchmark": "SPY",
                    "series": [{"date": f"2026-{7 + d // 28:02d}-{(d % 28) + 1:02d}",
                                "valquo": 0.30 * (d + 1) + (0.05 if d % 3 else -0.04),
                                "spy": 0.20 * (d + 1)} for d in range(n)]}
    return _St()


def _sum(n, contract):
    from valuation.screener import index_track as T
    return T.summarize("roth", meta_path="/nope", history_path="/nope",
                       contract=contract, store=_track_store(n))


PASSED_CONTRACT = "| field | value |\n|---|---|\n| Operational gate passed | YES - 2027-01-30 |\n"


def test_day_count_alone_can_never_flip_the_headline():
    """THE PINNING TEST for Part 10, and the reason this file exists in this shape.

    `MIN_LIVE_DAYS` used to be the whole rule: on the 60th trading day `headline` flipped to
    "live", `thin` flipped false (dropping the "too early to judge" pill at
    templates/index.html:114 and raising hero.may_lead), with no approval step. The contract
    says the posture changes on the 6-month OPERATIONAL GATE, not on elapsed time.

    Fails if anyone restores the day-count-only rule, at any horizon.
    """
    from valuation.screener import index_track as T

    for n in (T.MIN_LIVE_DAYS, T.MIN_LIVE_DAYS + 1, T.MIN_LIVE_DAYS * 5, 2000):
        out = _sum(n, "/nope/no_contract.md")
        assert out["days"] == n
        assert out["headline"] == "backtested", f"{n} days promoted the live number with no gate"
        assert out["thin"] is True, f"the 'too early to judge' pill went down at {n} days"
        assert out["gate"]["passed"] is False

    # ...and the gate genuinely works, or the above would pass vacuously.
    ok = _sum(T.MIN_LIVE_DAYS + 5, _contract(PASSED_CONTRACT))
    assert ok["gate"]["passed"] is True, ok["gate"]["reason"]
    assert ok["headline"] == "live" and ok["thin"] is False


def test_the_gate_is_an_extra_condition_and_never_a_replacement():
    """A gate-passed flag that let a three-day track lead would be worse than the bug it
    replaces. Both conditions, always."""
    from valuation.screener import index_track as T
    p = _contract(PASSED_CONTRACT)
    for n in (1, 5, 20, T.MIN_LIVE_DAYS - 1):
        out = _sum(n, p)
        assert out["gate"]["passed"] is True
        assert out["headline"] == "backtested", f"{n} days led because the gate had passed"
        assert out["thin"] is True


def test_every_unusable_contract_resolves_to_not_passed():
    """Fail-CLOSED, exhaustively. The conservative error is a mature track still labelled
    'backtested'; the harmful one is a thin track labelled 'live', and no accident may reach
    it. Note the fenced case: documenting the row form must not flip the gate on."""
    from valuation.screener import index_track as T

    cases = {
        "missing file": None,
        "no row at all": "# Contract\n\nNothing here.\n",
        "pending": "| Operational gate passed | *pending* |\n",
        "explicit no": "| Operational gate passed | no |\n",
        "blank value": "| Operational gate passed |  |\n",
        "date only": "| Operational gate passed | 2027-01-30 |\n",
        "near miss": "| Operational gate passed | yes-ish, mostly |\n",
        "wrong field": "| Operational gate date | YES - 2027-01-30 |\n",
        "malformed row": "| Operational gate passed YES - 2027-01-30 |\n",
        "inside a fence": "```\n| Operational gate passed | YES - 2027-01-30 |\n```\n",
        # This is the SHIPPED shape: the contract documents the canonical row in a fenced
        # block inside a blockquote. If the blockquote markers were not stripped first, the
        # fence would not register and this would only be skipped by accident.
        "fenced inside a blockquote": ("> On gate day, set this row:\n>\n> ```\n"
                                       "> | Operational gate passed | YES - 2027-01-30 |\n> ```\n"),
        "two rows disagreeing": ("| Operational gate passed | YES - 2027-01-30 |\n"
                                 "| Operational gate passed | pending |\n"),
    }
    for name, body in cases.items():
        path = "/nope/absent.md" if body is None else _contract(body)
        g = T.gate_state(path)
        assert g["passed"] is False, f"{name!r} was read as a PASS: {g}"
        out = _sum(T.MIN_LIVE_DAYS + 50, path)
        assert out["headline"] == "backtested", f"{name!r} promoted the headline"
        assert out["thin"] is True

    # Accepted spellings, so the edge lane is not fighting the parser on gate day.
    for body in ("| Operational gate passed | YES - 2027-01-30 |\n",
                 "| operational   gate passed | yes |\n",
                 "| **Operational gate passed** | **PASSED** on 2027-01-30 |\n",
                 "| Operational gate passed | true |\n"):
        assert T.gate_state(_contract(body))["passed"] is True, body


def test_the_gate_changes_labels_and_provably_not_values():
    """Part 10's bound: this is a LABELS-ONLY change. Same series, gate off vs gate on —
    every number must be bit-identical while the labels differ."""
    from valuation.screener import index_track as T
    n = T.MIN_LIVE_DAYS + 30
    off = _sum(n, "/nope/absent.md")
    on = _sum(n, _contract(PASSED_CONTRACT))

    assert off["headline"] != on["headline"] and off["thin"] != on["thin"], "inert"
    for k in ("days", "since", "as_of", "cum_valquo_pct", "cum_spy_pct", "excess_pp",
              "ann_alpha", "sharpe", "hit_rate"):
        assert off["live"][k] == on["live"][k], f"live.{k} moved: {off['live'][k]} -> {on['live'][k]}"
    assert off["backtested"] == on["backtested"]
    for k in ("config", "benchmark", "inception", "min_live_days", "available", "days", "series"):
        assert off[k] == on[k], f"{k} moved"


def test_the_shipped_contract_still_carries_the_row_the_site_reads():
    """The register row is the ONLY thing that can promote the live number. If it is ever
    deleted or renamed, the site silently loses its one approval step — so its absence must
    be loud here rather than quiet in production. Deliberately asserts the row EXISTS, not
    what it says: on gate day the edge lane sets it to YES and this test must still pass."""
    from valuation.screener import index_track as T
    g = T.gate_state()
    assert g["contract_present"] is True, f"{T.CONTRACT_FILE} is not where the site looks for it"
    assert g["value"] is not None, (f"{T.CONTRACT_FILE} has lost its '{T.GATE_FIELD}' row — the "
                                   f"headline gate now has no register to read")


def test_live_track_is_absent_not_invented_when_there_is_no_data():
    from valuation.screener import index_track as T
    out = T.summarize("roth", meta_path="/nope/a.json", history_path="/nope/b.csv")
    assert out["available"] is False and out["live"] is None
    assert out["headline"] == "backtested"
    assert out["backtested"]["net_sharpe"] is not None, "the backtest still has something to say"


# --------------------------------------------------------------------------- #
# Broker fundamentals (the free route) — offline, against a payload shaped like
# the live Tradier one. See valuation/screener/broker_fundamentals.py.
# --------------------------------------------------------------------------- #
def _broker_payload(ev=1.1e12, pe=25.0, sector_code=311, roe_1y=0.34, roe_3m=0.08,
                    ev_ebitda=20.0):
    """A Tradier-shaped payload: several result blocks per symbol, most tables null."""
    return {
        "company": {"ACME": [
            {"type": "Company", "tables": {
                "company_profile": None, "asset_classification": None,
                "historical_asset_classification": {"morningstar_sector_code": sector_code}}},
            {"type": "Stock", "tables": {
                "share_class_profile": {"market_cap": 1.0e12, "enterprise_value": ev,
                                        "shares_outstanding": 5.0e9},
                "ownership_summary": {"shares_outstanding": 5.0e9}}},
        ]},
        "ratios": {"ACME": [
            {"type": "Company", "tables": {
                "operation_ratios_restate": None,
                "operation_ratios_a_o_r": [
                    # The 3M block comes FIRST on purpose: it is a quarterly ROE and must lose.
                    {"period_3m": {"r_o_e": roe_3m, "total_debt_equity_ratio": 0.5},
                     "period_1y": {"r_o_e": roe_1y}},
                ]}},
            {"type": "Stock", "tables": {
                "valuation_ratios": {"p_e_ratio": pe, "p_s_ratio": 4.0, "p_b_ratio": 8.0,
                                     "e_v_to_e_b_i_t_d_a": ev_ebitda,
                                     "book_value_per_share": 25.0},
                "alpha_beta": {"period_60m": {"beta": 1.2}, "period_36m": {"beta": 0.9}}}},
        ]},
        "financials": {"ACME": []},
    }


def test_broker_fundamentals_maps_and_derives_the_absolutes():
    from valuation.screener import broker_fundamentals as BF
    m = BF.to_metrics("ACME", _broker_payload())
    assert m["market_cap"] == 1.0e12
    assert m["sector"] == "Technology"
    # revenue = mc / ps, net_income = mc / pe, equity = bvps * shares, ebitda = ev / ev_ebitda
    assert abs(m["revenue"] - 2.5e11) < 1, m["revenue"]
    assert abs(m["net_income"] - 4.0e10) < 1, m["net_income"]
    assert abs(m["total_equity"] - 1.25e11) < 1, m["total_equity"]
    assert abs(m["ebitda"] - 5.5e10) < 1, m["ebitda"]
    assert abs(m["net_debt"] - 1.0e11) < 1, m["net_debt"]      # ev - mc
    assert abs(m["earnings_yield"] - 0.04) < 1e-9
    assert m["beta"] == 1.2, "60-month beta is preferred over the 36-month one"
    # Everything the broker has no table for must be explicitly None, never fabricated.
    for gap in BF.GAP_FIELDS:
        assert m[gap] is None, f"{gap} has no broker source and must stay None"


def test_broker_roe_uses_the_annual_window_not_the_quarterly_one():
    """Morningstar publishes 3M and 1Y ROE in one table. A quarterly ROE is ~1/4 of the
    annual one, so mixing them across a cross-section makes the quality theme a coin flip
    on which window a name happened to report."""
    from valuation.screener import broker_fundamentals as BF
    m = BF.to_metrics("ACME", _broker_payload(roe_1y=0.34, roe_3m=0.08))
    assert m["roe"] == 0.34, m["roe"]


def test_broker_zero_enterprise_value_is_missing_not_free():
    """EV is reported as exactly 0 for banks — a 'not applicable' sentinel. Taken as a
    number it sets net_debt = -market_cap and ev_sales = 0, which would hand every large
    bank the cheapest EV/Sales in the universe and peg the sector to the top of value."""
    from valuation.screener import broker_fundamentals as BF
    # Shaped like the live payload: verified 2026-08-02 that all 11 banks in a 200-name
    # sample report ev == 0 AND ev_to_ebitda == null together.
    m = BF.to_metrics("ACME", _broker_payload(ev=0.0, ev_ebitda=None))
    assert m["ev"] is None
    assert m["net_debt"] is None, "net_debt must not become -market_cap"
    assert m["ev_sales"] is None, "ev_sales must not become 0 (the cheapest in the universe)"
    assert m["book_to_price"] is not None, "the non-EV value inputs still work for a bank"
    assert m["earnings_yield"] is not None


def test_broker_loss_maker_has_no_earnings_rather_than_zero():
    """A loss-making company has no published P/E. Inferring 0 (or a negative) earnings
    from a missing ratio would invent data; leaving it None puts the name in the
    'speculative' bucket, which is where a loss-maker belongs."""
    from valuation.screener import broker_fundamentals as BF
    from valuation.screener.factors import classify_bucket
    m = BF.to_metrics("ACME", _broker_payload(pe=None))
    assert m["net_income"] is None and m["earnings_yield"] is None
    assert classify_bucket(m) == "speculative"


def test_broker_merge_never_overwrites_a_reported_value_with_a_derived_one():
    """The free stack reads actual filings. Where it has a real revenue, the broker's
    ratio-inverted reconstruction must not replace it."""
    from valuation.screener import broker_fundamentals as BF
    broker = {"revenue": 999.0, "sector": "Technology", "beta": 1.2, "market_cap": 5.0}
    free = {"revenue": 100.0, "sector": "", "beta": None, "market_cap": None, "fcf": 7.0}
    out = BF.merge(broker, free)
    assert out["revenue"] == 100.0, "reported revenue wins"
    assert out["sector"] == "Technology", "an empty string counts as missing"
    assert out["beta"] == 1.2 and out["market_cap"] == 5.0
    assert out["fcf"] == 7.0, "free-only fields survive the merge"
    assert out["source"] == "free+broker"
    assert set(out["broker_filled"]) == {"sector", "beta", "market_cap"}


def test_broker_row_survives_when_the_free_stack_returns_nothing():
    """The resilience property: from a throttled cloud IP the per-name yfinance fetch comes
    back empty and USED TO drop the name from the scan entirely. It must now survive on the
    broker's half rather than disappear."""
    from valuation.screener import broker_fundamentals as BF
    broker = BF.to_metrics("ACME", _broker_payload())
    out = BF.merge(broker, None)
    assert out is not None and out["market_cap"] == 1.0e12
    assert BF.merge(None, None) is None


def test_broker_prefetch_absent_token_degrades_quietly():
    from valuation.screener.providers import FreeProvider

    class _Cfg:
        tradier_token = ""
        sec_user_agent = "x"
    p = FreeProvider(_Cfg(), None)
    assert p.prefetch(["AAPL"]) == {}
    assert "TRADIER_TOKEN" in p.broker_stats["note"]
    assert p._broker_metrics("AAPL") is None


def test_metrics_cache_from_an_older_schema_is_discarded():
    """A cached row written before the broker merge is missing sector/beta/ev. Served as-is
    it is indistinguishable from a name the feed genuinely has no sector for, which is how
    the blank-sector bug survived for weeks."""
    from valuation.screener.providers import _usable_cache, METRICS_SCHEMA
    assert _usable_cache({"units": "usd", "schema": METRICS_SCHEMA}) is not None
    assert _usable_cache({"units": "usd", "schema": 1}) is None
    assert _usable_cache({"units": "usd"}) is None, "an unstamped row predates the schema"
    assert _usable_cache({"units": "millions", "schema": METRICS_SCHEMA}) is None


def test_broker_coverage_report_separates_covered_from_gap_fields():
    from valuation.screener import broker_fundamentals as BF
    rows = [BF.to_metrics("ACME", _broker_payload()),
            {"market_cap": 1.0, "source": "free", "fcf": 2.0, "op_margin": 0.1}]
    cov = BF.coverage(rows)
    assert cov["names"] == 2
    assert cov["broker_fields"]["market_cap"] == 1.0
    assert cov["gap_fields"]["fcf"] == 0.5, "only the free row has FCF"
    assert cov["by_source"]["broker"] == 1 and cov["by_source"]["free"] == 1


def test_theme_coverage_distinguishes_present_from_contributing():
    """A constant theme is 100% 'covered' and contributes nothing: zscore() of a zero-variance
    column is all-NaN and composite_score renormalizes it away. Live, `insider` is exactly
    that — no insider_score reaches build_frame, so the column is the constant 0.0 and its
    12.5% weight is silently inert. Reporting only presence hides that."""
    import pandas as pd
    from valuation.screener.screen import _theme_contribution

    df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0], "insider": [0.0, 0.0, 0.0, 0.0]})
    out = _theme_contribution(df)
    assert out["value"] == 1.0
    assert out["insider"] == 0.0, "a constant theme must not read as contributing"


def test_morningstar_sector_codes_match_the_apps_sector_names():
    """A broker sector only helps if it lands in the peer-median lookup — a near-miss like
    'Financials' would silently fall through to the generic default multiple."""
    from valuation.screener.broker_fundamentals import SECTOR_CODES
    from valuation.engine.comps import SECTOR_MULTIPLES
    assert set(SECTOR_CODES.values()) == set(SECTOR_MULTIPLES), \
        set(SECTOR_CODES.values()) ^ set(SECTOR_MULTIPLES)


# --------------------------------------------------------------------------- #
# Market session guard — the thing standing between a fixed-UTC cron and a
# forward paper track marked on intraday prices all winter.
# --------------------------------------------------------------------------- #
def test_market_holidays_match_the_published_nyse_calendar():
    """Computed, not listed, so it cannot expire — which is only safe if it is right.
    Checked against the actual NYSE closures for two full years."""
    from valuation.screener.market_session import market_holidays
    assert {d.isoformat() for d in market_holidays(2025)} == {
        "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
        "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25"}
    assert {d.isoformat() for d in market_holidays(2024)} == {
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
        "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25"}


def test_holiday_falling_at_a_weekend_moves_to_the_observed_weekday():
    from valuation.screener.market_session import market_holidays
    # 4 Jul 2026 is a Saturday -> observed Friday the 3rd; 25 Dec 2027 is a Saturday -> the 24th.
    assert __import__("datetime").date(2026, 7, 3) in market_holidays(2026)
    assert __import__("datetime").date(2026, 7, 4) not in market_holidays(2026)
    assert __import__("datetime").date(2027, 12, 24) in market_holidays(2027)


def test_session_guard_blocks_before_the_close_and_opens_after():
    """The bug this exists for: 20:45 UTC is 4:45pm ET in summer but 3:45pm ET in winter, so a
    fixed-UTC cron runs mid-session for half the year and nothing in the output looks wrong."""
    import datetime as dt
    from valuation.screener.market_session import session_state

    wednesday = dt.date(2026, 8, 5)                       # a plain trading day
    assert session_state(dt.datetime.combine(wednesday, dt.time(15, 45)))["ok"] is False
    assert session_state(dt.datetime.combine(wednesday, dt.time(16, 45)))["ok"] is True
    # Right at the bell is still too early: the closing print settles over the next minutes.
    assert session_state(dt.datetime.combine(wednesday, dt.time(16, 0)))["ok"] is False


def test_session_guard_skips_weekends_and_holidays():
    import datetime as dt
    from valuation.screener.market_session import session_state
    sat = session_state(dt.datetime(2026, 8, 8, 17, 0))
    assert sat["ok"] is False and "weekend" in sat["reason"]
    xmas = session_state(dt.datetime(2026, 12, 25, 17, 0))
    assert xmas["ok"] is False and "holiday" in xmas["reason"]


# --------------------------------------------------------------------------- #
# Landing showcase — the numbers behind the "show, don't tell" hero.
# --------------------------------------------------------------------------- #
def test_range_bar_flags_a_price_outside_the_scenario_range():
    """A strongly over- or under-valued name puts the price beyond bear/bull. Clamping the
    marker silently would draw it at the edge as though it were inside the range."""
    from valuation.web.showcase import range_bar
    hot = range_bar({"bear": 98.5, "base": 119.6, "bull": 145.3, "price": 308.9})
    assert hot["price_pos"] == 100.0 and hot["price_outside"] == "above"
    assert 0 < hot["base_pos"] < 100
    cheap = range_bar({"bear": 98.5, "base": 119.6, "bull": 145.3, "price": 40.0})
    assert cheap["price_pos"] == 0.0 and cheap["price_outside"] == "below"
    inside = range_bar({"bear": 98.5, "base": 119.6, "bull": 145.3, "price": 120.0})
    assert inside["price_outside"] == ""
    # A degenerate range must not divide by zero.
    assert range_bar({"bear": 10.0, "base": 10.0, "bull": 10.0, "price": 5.0}) is None


def test_sparkline_puts_both_lines_on_one_shared_axis():
    """Drawing each series to its own scale would make a line that LOST look like it won."""
    from valuation.web.showcase import sparkline
    s = sparkline([{"date": "2026-07-01", "valquo": 0.0, "spy": 0.0},
                   {"date": "2026-07-02", "valquo": 10.0, "spy": 5.0}], width=100, height=50)
    assert s["ok"] and s["n"] == 2
    iy = [float(p.split(",")[1]) for p in s["index"].split()]
    by = [float(p.split(",")[1]) for p in s["bench"].split()]
    # Both start together; the better performer ends HIGHER on screen (smaller y).
    assert abs(iy[0] - by[0]) < 1e-6
    assert iy[1] < by[1], "the outperforming line must be drawn above the benchmark"
    # One point cannot make a line — say so rather than emit a degenerate path.
    assert sparkline([{"date": "2026-07-01", "valquo": 1.0, "spy": 1.0}])["ok"] is False
    assert sparkline([])["ok"] is False


def test_landing_sample_missing_a_price_is_treated_as_no_sample():
    """The template formats price/fair_value with %.2f, which raises on None — inside
    render_template, i.e. OUTSIDE the route's try/except. A half-filled sample would 500 the
    home page rather than degrade to the static copy."""
    from valuation.web.showcase import load

    class _St:
        def __init__(self, v):
            self.v = v

        def get_meta(self, k, default=None):
            return self.v
    assert load(_St({"ticker": "AAPL", "price": 100.0, "fair_value": 120.0})) is not None
    assert load(_St({"ticker": "AAPL", "fair_value": 120.0})) is None      # no price
    assert load(_St({"price": 1.0, "fair_value": 2.0})) is None            # no ticker
    assert load(_St({"ticker": "AAPL", "price": 100.0})) is None           # no fair value
    assert load(_St("not-a-dict")) is None


def test_landing_context_degrades_to_nothing_rather_than_raising():
    from valuation.web.showcase import landing_context

    class _Dead:
        def get_meta(self, k, default=None):
            raise RuntimeError("no db")

        def latest_scan_date(self):
            raise RuntimeError("no db")
    ctx = landing_context(_Dead())
    assert ctx["sample"] is None and ctx["scan"] is None


# ---------------------------------------------------------------------------------------- #
# "Why this score" attribution. The point of these is that the explanation and the ranking
# come from ONE calculation: an attribution that merely looks plausible next to a score it
# was not derived from is worse than none, because it reads as an audit and isn't one.
# ---------------------------------------------------------------------------------------- #
def test_score_attribution_sums_to_the_composite_it_explains():
    res, _ = _scan()
    checked = 0
    for r in res["rows"]:
        why = (r["extra"] or {}).get("why") or []
        if not why:
            continue
        total = sum(w["c"] for w in why)
        # Contributions are rounded to 4dp each, so ~10 themes can drift ~5e-4 in the worst
        # case. Anything beyond that means the pieces are not the score's pieces.
        assert abs(total - r["composite"]) < 1e-3, (r["ticker"], total, r["composite"])
        assert r["extra"]["why_composite"] == r["composite"]
        checked += 1
    assert checked > 100, f"only {checked} rows carried an attribution"


def test_attribution_is_ordered_by_size_and_keeps_the_sign_of_the_drag():
    res, _ = _scan()
    negatives = 0
    for r in res["rows"]:
        why = (r["extra"] or {}).get("why") or []
        mags = [abs(w["c"]) for w in why]
        assert mags == sorted(mags, reverse=True), r["ticker"]
        negatives += sum(1 for w in why if w["c"] < 0)
    # A decomposition where nothing ever holds a name back is a decomposition of the wrong
    # thing: z-scores are centred, so every cross-section has losers on every theme.
    assert negatives > 0


def test_attribution_shares_are_of_the_absolute_push_not_the_signed_total():
    """Shares must stay in [0, 1] and sum to 1 even when themes cancel out.

    With a signed denominator a name whose positives and negatives nearly cancel gets a
    near-zero total and shares in the hundreds of percent — the exact rows a reader is most
    likely to open.
    """
    res, _ = _scan()
    seen_mixed = False
    for r in res["rows"]:
        why = (r["extra"] or {}).get("why") or []
        if not why:
            continue
        shares = [w["share"] for w in why]
        assert all(0.0 <= s <= 1.0 for s in shares), (r["ticker"], shares)
        assert abs(sum(shares) - 1.0) < 0.01, (r["ticker"], sum(shares))
        if any(w["c"] > 0 for w in why) and any(w["c"] < 0 for w in why):
            seen_mixed = True
    assert seen_mixed, "no name had themes pulling in both directions"


def test_decomposition_did_not_change_the_ranking_it_explains():
    """The composite must still be the OLD composite, computed the old way.

    `_composites` now delegates to the attribution module. That is only safe if it produces
    the identical number — this recomputes it from `composite_score` directly, the way the
    scan did before the decomposition existed, under both bucketing modes.
    """
    import numpy as np
    import pandas as pd
    from valuation.screener.factors import build_frame
    from valuation.screener.cross_sectional import composite_score
    from valuation.screener.screen import _composites, _p_established
    from valuation.screener import settings as S
    from tests.screener_fixtures import SyntheticProvider

    prov = SyntheticProvider(14)
    tickers = [u["ticker"] for u in prov.get_universe()]
    metrics = [prov.get_metrics(t) for t in tickers]
    for m, t in zip(metrics, tickers):
        m.setdefault("ticker", t)
    df = build_frame(metrics)
    est_w, spec_w = S.WEIGHTS_ESTABLISHED, S.WEIGHTS_SPECULATIVE

    d = df.copy()
    d["value"] = df["value_est"]
    comp_est = composite_score(d, est_w)
    d["value"] = df["value_spec"]
    comp_spec = composite_score(d, spec_w)
    p = _p_established(df)
    expected_soft = p * comp_est + (1.0 - p) * comp_spec
    got_soft = _composites(df, est_w, spec_w, soft=True)
    assert np.allclose(got_soft.values, expected_soft.values, atol=1e-12, equal_nan=True)

    expected_hard = pd.Series(index=df.index, dtype=float)
    for bucket, w in [("established", est_w), ("speculative", spec_w)]:
        sub = df[df["bucket"] == bucket]
        if len(sub) >= 5:
            expected_hard.loc[sub.index] = composite_score(sub, w)
        elif len(sub) > 0:
            expected_hard.loc[sub.index] = composite_score(df, w).loc[sub.index]
    got_hard = _composites(df, est_w, spec_w, soft=False)
    assert np.allclose(got_hard.values, expected_hard.values, atol=1e-12, equal_nan=True)


def test_a_name_no_theme_scored_has_no_attribution_rather_than_a_zero():
    """An unscoreable name must come back NaN, not 0.0.

    A zero composite would rank mid-pack — a name nobody could score would sit above every
    genuinely cheap-but-flawed one.
    """
    import numpy as np
    import pandas as pd
    from valuation.screener.attribution import decompose

    df = pd.DataFrame({
        "value": [1.0, -1.0, 0.5, np.nan],
        "quality": [0.5, -0.5, 1.0, np.nan],
        "momentum": [0.2, 0.1, -0.3, np.nan],
        "bucket": ["established"] * 4,
        "op_margin": [0.2, 0.1, 0.15, 0.1],
    }, index=["A", "B", "C", "DEAD"])
    w = {"value": 0.4, "quality": 0.4, "momentum": 0.2}
    comp, contrib = decompose(df, w, w, soft=False)
    assert np.isnan(comp.loc["DEAD"])
    assert contrib.loc["DEAD"].isna().all()
    assert not np.isnan(comp.loc["A"])
    assert abs(float(contrib.loc["A"].sum()) - float(comp.loc["A"])) < 1e-12


# ---------------------------------------------------------------------------------------- #
# The unified "what does this tool do with this name" view. It spans the ranking, the book
# and the options alerts, which is exactly why its failure mode is a confident sentence that
# is not true of any of them.
# ---------------------------------------------------------------------------------------- #
def test_name_view_joins_the_ranking_the_book_and_the_options_record():
    res, store = _scan()
    from valuation.web.unified import name_view
    top = res["rows"][0]["ticker"]
    v = name_view(store, top)
    s = v["stock"]
    assert s["in_scan"] and s["rank"] == 1
    assert s["n_scored"] == res["scored"]
    # The attribution shown here is the SAME one the Hot tab shows — not a re-derivation.
    assert s["why"] == (res["rows"][0]["extra"] or {}).get("why")
    assert s["index"]["available"] and isinstance(s["index"]["in_book"], bool)
    assert v["options"]["n_logged"] == 0
    assert any(a["kind"] == "caveat" for a in v["action"])


def test_name_view_says_a_name_is_absent_rather_than_bad():
    res, store = _scan()
    from valuation.web.unified import name_view
    v = name_view(store, "NOTATICKER")
    assert v["stock"]["in_scan"] is False
    msg = v["stock"]["message"].lower()
    assert "not in" in msg and "says nothing about" in msg
    # No score, no rank, no fabricated neutral value.
    assert "hot_score" not in v["stock"] and "rank" not in v["stock"]


def test_name_view_never_quotes_a_per_ticker_hit_rate():
    """One name yields a handful of trades at most; a rate off that is noise wearing a %."""
    import datetime as _dt
    from valuation.edge import options_tracker as OT
    from valuation.web.unified import name_view
    res, store = _scan()
    t = res["rows"][0]["ticker"]
    ts = _dt.datetime.utcnow().isoformat(timespec="seconds")
    aid = OT.log_alert(store, {"ticker": t, "alert_ts": ts, "opt_right": "call", "strike": 100.0,
                               "expiry": "2026-12-18", "entry_premium": 4.00, "dte": 60,
                               "score": 88.0})
    assert OT.record_outcome(store, alert_id=aid, exit_premium=8.00, exit_ts=ts,
                             exit_reason="target")
    v = name_view(store, t)
    o = v["options"]
    assert o["n_logged"] == 1 and o["n_closed"] == 1
    ch = o["closed_here"]
    assert ch["n_won"] == 1 and ch["n"] == 1
    assert "rate" in ch["note"]
    # A rate on one trade must not appear anywhere in the payload or the action lines.
    assert "hit_rate" not in ch and "expectancy" not in ch
    text = " ".join(a["text"] for a in v["action"])
    assert "1 of 1 closed option trade(s) on this name won" in text
    assert "100%" not in text


def test_name_view_sizes_in_whole_contracts_and_reports_zero_honestly():
    """A premium above the risk budget sizes to ZERO. Rounding it to one breaks the rule."""
    import datetime as _dt
    from valuation.edge import options_tracker as OT
    from valuation.web.unified import name_view
    res, store = _scan()
    t = res["rows"][0]["ticker"]
    ts = _dt.datetime.utcnow().isoformat(timespec="seconds")
    OT.log_alert(store, {"ticker": t, "alert_ts": ts, "opt_right": "call", "strike": 100.0,
                         "expiry": "2026-12-18", "entry_premium": 25.00, "dte": 60})
    v = name_view(store, t, risk_budget=1000.0)
    sz = v["options"]["latest"]["sizing"]
    assert sz["contracts"] == 0          # $25 x 100 = $2,500 > $1,000
    assert "zero, not one" in sz["note"]

    v2 = name_view(store, t, risk_budget=10000.0)
    assert v2["options"]["latest"]["sizing"]["contracts"] == 4


def test_name_view_withholding_options_is_not_the_same_as_having_none():
    """The free tier doesn't LOOK at the options record — it must not report an empty one."""
    from valuation.web.unified import name_view
    res, store = _scan()
    t = res["rows"][0]["ticker"]
    v = name_view(store, t, with_options=False)
    assert v["options"]["withheld"] is True
    text = " ".join(a["text"] for a in v["action"])
    assert "No scream-buy options alert has ever fired" not in text
    assert "part of Signals" in text
    # The convexity framing survives the withholding — a reader who sees a contract exists
    # but no caveat is the worst of both.
    assert "CONVEX" in v["options"]["convexity"]


def test_name_view_action_lines_describe_the_model_not_the_reader():
    from valuation.web.unified import name_view
    res, store = _scan()
    v = name_view(store, res["rows"][0]["ticker"])
    text = " ".join(a["text"] for a in v["action"]).lower()
    for phrase in ("you should", "we recommend", "buy now", "strong buy", "guaranteed"):
        assert phrase not in text, phrase


def test_name_view_survives_a_store_with_no_scan_at_all():
    import tempfile
    from valuation.web.unified import name_view
    store = Store(os.path.join(tempfile.mkdtemp(prefix="valquo_empty_"), "s.db"))
    v = name_view(store, "AAPL")
    assert v["stock"]["in_scan"] is False
    assert "No scan" in v["stock"]["message"]
    assert v["options"]["n_logged"] == 0


# A real Form 4, trimmed: AAPL accession 0001140361-26-025622 (Newstead, SVP/GC).
# One open-market SALE of 12,819 shares at $220.00 so the parser has a priced txn to score.
_FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <issuer><issuerCik>0000320193</issuerCik><issuerTradingSymbol>AAPL</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Newstead Jennifer</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isOfficer>true</isOfficer>
      <officerTitle>SVP, GC and Secretary</officerTitle></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>12819</value></transactionShares>
        <transactionPricePerShare><value>220.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""

# What EDGAR actually serves at the primaryDocument path the old code used.
_FORM4_RENDERED_HTML = ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'
                        '<html><body><table><tr><td>SEC Form 4<br></td></table></body></html>')


def test_form4_url_strips_the_xsl_rendered_view():
    """THE bug: EDGAR's `primaryDocument` for a Form 4 is the XSL-RENDERED HTML view
    (xslF345X01-X06; 99.3% of 370,681 filings). Fetching it and parsing it as XML raises,
    the raise was swallowed, and every ticker scored a constant 50. The raw XML lives at
    the same path with that directory removed."""
    from valuation.screener.insider import form4_xml_url
    got = form4_xml_url(320193, "0001140361-26-025622", "xslF345X06/form4.xml")
    assert got == ("https://www.sec.gov/Archives/edgar/data/320193/"
                   "000114036126025622/form4.xml"), got
    assert "xslF345" not in got
    # every rendered prefix EDGAR uses, with the filing counts that motivated this
    for pref in ("xslF345X01", "xslF345X02", "xslF345X03",
                 "xslF345X04", "xslF345X05", "xslF345X06"):
        assert "xsl" not in form4_xml_url(1, "0-0-0", f"{pref}/ownership.xml")
    # a document that is ALREADY raw XML must pass through untouched
    assert form4_xml_url(1, "0-0-0", "wf-form4_123.xml").endswith("/wf-form4_123.xml")


def test_form4_parser_reads_a_known_good_filing():
    """Fails if the parser returns empty for a real Form 4 — the regression that hid the
    bug, since [] is indistinguishable from 'this insider transacted nothing'."""
    from valuation.screener.insider import _parse_form4
    txns = _parse_form4(_FORM4_XML)
    assert txns, "a known-good Form 4 must not parse to an empty transaction list"
    assert len(txns) == 1 and txns[0]["code"] == "S"
    assert abs(txns[0]["value_usd"] - 12819 * 220.00) < 1e-6
    # Pinning observed behaviour, not endorsing it: _role_multiplier matches the literal
    # word "officer", so an isOfficer=true filer titled "SVP, GC and Secretary" gets the
    # DIRECTOR weight of 1.0. Noted in HANDOFF_live_data_bugs.md; out of scope to retune
    # here, since changing role weights moves every live score.
    assert txns[0]["role_mult"] == 1.0


def test_form4_parse_failure_raises_instead_of_scoring_neutral():
    """The rendered HTML must RAISE, not silently become a neutral score. This is the
    exact swallow (`except Exception: return out`) that made the signal a constant."""
    from valuation.screener.insider import _parse_form4, Form4ParseError
    try:
        _parse_form4(_FORM4_RENDERED_HTML)
    except Form4ParseError as e:
        assert "document starts" in str(e), str(e)
    else:
        raise AssertionError("parsing EDGAR's rendered HTML must raise, not return []")


def test_unreadable_insider_scores_none_not_fifty():
    """'We could not read the filings' and 'we read them and saw nothing' must not collapse
    to the same number. The old contract returned 50.0 for both."""
    from valuation.screener import insider as I

    class _Resp:
        def __init__(self, text): self.text = text
        def json(self): return {"filings": {"recent": {
            "form": ["4"], "accessionNumber": ["0001140361-26-025622"],
            "primaryDocument": ["xslF345X06/form4.xml"], "filingDate": ["2999-01-01"]}}}

    import types
    fake = types.SimpleNamespace(get=lambda *a, **k: _Resp(_FORM4_RENDERED_HTML))
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _imp(name, *a, **k):
        return fake if name == "requests" else real_import(name, *a, **k)

    import builtins
    orig_cik = I._edgar.resolve_cik
    builtins.__import__, I._edgar.resolve_cik = _imp, (lambda t, c: 320193)
    try:
        d = I.insider_detail("AAPL")
    finally:
        builtins.__import__, I._edgar.resolve_cik = real_import, orig_cik
    assert d["form4_seen"] == 1, d
    assert d["parse_failures"] == 1, d
    assert d["score"] is None, "an unreadable filing must not become a confident 50"


def test_publication_band_has_exactly_one_definition():
    """CONSOLIDATE-1's durable half: make copy six fail on the day it is written.

    Four sessions in a row found "a new bug" that was the same decision implemented once
    more — the valuation page refusing at 5x, the growth lens capping at 20x, the multiples
    lens capping at nothing, `pipeline.py` and `scoring.py` each restating `ratio > 5 or
    ratio < 0.2` as literals, and `screen.py` erasing the refusal entirely. Nothing had
    regressed; there were simply five copies.

    So: exactly ONE module may define the band, and no other file in engine/ or screener/
    may restate it as a literal. A new surface that invents its own bar fails here.
    """
    import re, pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    owner = root / "valuation" / "engine" / "publication.py"
    assert owner.exists(), "the single owner of the publication decision is missing"

    # The surfaces that answer "may this fair value be published?" — the engine and the
    # screener. Other lanes (web, report) import the constant and are checked separately;
    # `intraday` and `edge` have their own unrelated `ratio` variables.
    scope = sorted(list((root / "valuation" / "engine").rglob("*.py"))
                   + list((root / "valuation" / "screener").rglob("*.py")))
    definers, restaters = [], []
    for path in scope:
        rel = path.relative_to(root).as_posix()
        src = path.read_text(encoding="utf-8", errors="replace")
        # strip comments AND docstrings — prose that quotes the old literals is not a copy
        src = re.sub(r'"""[\s\S]*?"""', "", src)
        body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        # a DEFINITION assigns the band a numeric literal
        if re.search(r"^\s*FV_BAND_(HIGH|LOW)\s*=\s*[0-9]", body, re.M):
            definers.append(rel)
        # a RESTATEMENT compares a price ratio against a bare number
        if re.search(r"ratio\s*[<>]=?\s*(?!FV_BAND)[0-9]", body):
            restaters.append(rel)

    assert definers == ["valuation/engine/publication.py"], (
        f"the band must be defined in exactly one place, found: {definers}")
    assert not restaters, (
        f"these files compare a price ratio against a literal instead of importing "
        f"FV_BAND_HIGH/FV_BAND_LOW: {restaters}")


def test_every_publication_site_resolves_to_the_same_constant():
    """The other half: every surface that decides must resolve to the one object."""
    from valuation.engine.publication import FV_BAND_HIGH, decide
    from valuation.engine import pipeline
    from valuation.screener import fairvalue as FV

    assert pipeline.FV_BAND_HIGH is FV_BAND_HIGH
    assert FV.MAX_LENS_VALUE is FV_BAND_HIGH
    from valuation.engine import scoring
    assert scoring.FV_BAND_HIGH is FV_BAND_HIGH

    # the web lane is another lane's code, but it must still read OUR constant
    from valuation.web import withhold
    assert withhold._band() == float(FV_BAND_HIGH)

    # and the boundary is exactly where it was: == publishes, > refuses
    assert decide(100.0 * FV_BAND_HIGH, 100.0).publish is True
    assert decide(100.0 * FV_BAND_HIGH + 0.01, 100.0).publish is False


def test_a_refused_row_is_not_re_estimated_from_peers():
    """The one-line half, and the leak that put KSPI, STLA and CHTR on the public hot list.

    `_enrich_with_dcf` wrote `fair_value = None` on a refusal and recorded nothing, so
    `estimate_fair_values` read that None as "no DCF computed yet" and substituted a peer
    estimate. A recorded refusal must survive the estimator untouched."""
    from valuation.screener.fairvalue import estimate_fair_values
    from valuation.engine.publication import ROW_WITHHELD, ROW_WITHHELD_REASON, record_refusal

    peers = [{"ticker": f"P{i}", "sector": "Tech", "price": 100.0, "market_cap": 1e9,
              "extra": {"earnings_yield": 0.05, "net_debt": 0.0}} for i in range(6)]
    refused = {"ticker": "KSPI", "sector": "Tech", "price": 92.19, "market_cap": 1e9,
               "extra": {"earnings_yield": 0.30, "net_debt": 0.0}}
    record_refusal(refused, "Cannot value this name: the model's $1,248.48 is 13.6x the price.")

    estimate_fair_values([refused] + peers, peer_rows=[refused] + peers)
    assert refused["fair_value"] is None, (
        f"a refused row was re-estimated to {refused['fair_value']} — the refusal was erased")
    assert refused[ROW_WITHHELD] is True
    assert refused[ROW_WITHHELD_REASON]
    # ...while an ordinary row still gets its estimate
    assert any(p.get("fair_value") is not None for p in peers)


def test_a_recorded_refusal_survives_the_snapshot_round_trip():
    """THE test for this class of bug, and the one whose absence kept the leak live.

    `test_a_refused_row_is_not_re_estimated_from_peers` above was GREEN the entire time
    production was publishing refused names, because it exercises the estimator IN MEMORY and
    the database sits between the scan and the serve. `store.save_snapshot` wrote a fixed
    18-column INSERT that did not name `fair_value_withheld`, so the refusal was recorded
    correctly, discarded by the writer, and read back as a bare `fair_value = None` — which
    `estimate_fair_values` treats as "no DCF yet" and replaces with a peer estimate.

    Reproduced on the real 399-row production snapshot before the fix: refusing rank-1 STT and
    serving it through the round trip republished $386.68083192601813 as "blended".

    Note what this test asserts and the ratio-walking catch-all cannot: the catch-all checks
    that no PUBLISHED value exceeds the 5x band, and a refused 11x model replaced by a 3.2x
    peer estimate sits comfortably UNDER the band. No ratio test can see this. The invariant
    is about the DECISION surviving persistence, so the test has to cross the same boundary
    the decision does.
    """
    import tempfile
    from valuation.screener.store import Store
    from valuation.screener.fairvalue import estimate_fair_values
    from valuation.engine.publication import ROW_WITHHELD, ROW_WITHHELD_REASON, record_refusal

    rows = [{"ticker": f"P{i}", "sector": "Tech", "price": 100.0, "market_cap": 1e9, "rank": i + 2,
             "extra": {"earnings_yield": 0.05, "net_debt": 0.0, "revenue": 5e8}} for i in range(6)]
    refused = {"ticker": "KSPI", "sector": "Tech", "price": 92.19, "market_cap": 1e9, "rank": 1,
               "extra": {"earnings_yield": 0.30, "net_debt": 0.0, "revenue": 5e8}}
    reason = "Cannot value this name: the model's $1,248.48 is 13.6x the price."
    record_refusal(refused, reason)

    st = Store(os.path.join(tempfile.mkdtemp(), "roundtrip.db"))
    st.save_snapshot("2026-08-07", [refused] + rows, "test", {})
    back = st.load_snapshot("2026-08-07")

    got = next(r for r in back if r["ticker"] == "KSPI")
    assert got.get(ROW_WITHHELD) is True, (
        "the database dropped the refusal — this is the leak: the scan recorded it and the "
        "writer discarded it")
    assert got.get(ROW_WITHHELD_REASON) == reason, "a blanked cell must still say why"

    # ...and it must still be honoured by the SERVE path that runs on the rows read back.
    estimate_fair_values(back, peer_rows=back)
    got = next(r for r in back if r["ticker"] == "KSPI")
    assert got.get("fair_value") is None, (
        f"a refused row came back out of the database and was re-estimated to "
        f"{got.get('fair_value')} — exactly what valquo.co was serving")
    assert got.get("fair_value_method") == "withheld"
    # a row that was never refused still gets its estimate, and carries neither key
    ordinary = next(r for r in back if r["ticker"] == "P0")
    assert ROW_WITHHELD not in ordinary and ROW_WITHHELD_REASON not in ordinary


def test_not_dcf_valuable_is_not_a_refusal():
    """The mirror-image defect, found while measuring Bug B and live in this lane's code.

    `_enrich_with_dcf` refused on `base_fair_value is None and reason`, which is ALSO true of a
    name the model simply cannot value — no free cash flow, no revenue, an ADR bank whose
    P/B–ROE inputs are missing. Nothing has been refused about those names and a peer multiple
    is the right tool for them, but they were blanked and told "no fair value is published".

    Measured on the real production list: 17 of 387 served names report a "not DCF-valuable"
    reason and NONE of them is a genuine refusal. Running the old expression over NVS, SAP and
    TD suppressed ordinary peer estimates of $185.41, $364.97 and $79.73.

    The test is the VERDICT from `publication.decide`, not the presence of a reason string."""
    from valuation.screener import screen as screen_mod
    from valuation.engine import pipeline as pipeline_mod
    from valuation.engine.publication import ROW_WITHHELD

    class _Blend:
        def __init__(self, value, withheld, reason):
            self.value, self.withheld_value, self.reason = value, withheld, reason
            self.growth_led = False

    class _Res:
        def __init__(self, blend, price, base):
            self.fair_value_blend, self.base_fair_value, self.upside = blend, base, None
            self.company = type("CD", (), {"price": price})()

    cases = {
        # not valuable: the model never produced a number. NOT a refusal.
        "NVS": _Res(_Blend(None, None, "Not DCF-valuable: the company doesn't generate "
                                       "positive free cash flow."), 153.67, None),
        # genuine refusal: the model DID produce a number and it is 14x the price.
        "KSPI": _Res(_Blend(None, 1289.60, "Cannot value this name: ..."), 92.11, None),
    }
    orig = pipeline_mod.value_ticker
    pipeline_mod.value_ticker = lambda t, cfg, mc_trials=None: cases[t]
    try:
        rows = [{"ticker": "NVS", "price": 153.67}, {"ticker": "KSPI", "price": 92.11}]
        from valuation.config import CONFIG as _CFG
        screen_mod._enrich_with_dcf(rows, _CFG, refusal_only=True)
    finally:
        pipeline_mod.value_ticker = orig

    assert not rows[0].get(ROW_WITHHELD), (
        "a name the model merely cannot value was recorded as REFUSED — that suppresses a "
        "perfectly ordinary peer estimate and tells the reader a refusal happened")
    assert rows[1].get(ROW_WITHHELD) is True, (
        "a genuine >5x refusal was not recorded — this is the leak")


def test_snapshot_migration_adds_the_withheld_columns_and_reads_old_rows_as_not_withheld():
    """A database written before the columns existed must migrate in place, and its existing
    rows have no opinion about refusals — so they must read as NOT withheld. The alternative
    (unknown => withheld) would blank fair values across the stored history on no evidence.

    The honest consequence, stated here so it is not lost: an already-stored snapshot keeps
    serving whatever it stored until the next scan overwrites its date."""
    import sqlite3, tempfile
    from valuation.screener.store import Store
    from valuation.engine.publication import ROW_WITHHELD, record_refusal

    path = os.path.join(tempfile.mkdtemp(), "old.db")
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE snapshot_rows (
            scan_date TEXT, ticker TEXT, name TEXT, sector TEXT, bucket TEXT,
            price REAL, market_cap REAL, hot_score REAL, composite REAL, rank INTEGER,
            z_value REAL, z_quality REAL, z_growth REAL, z_momentum REAL, z_insider REAL,
            fair_value REAL, upside REAL, extra TEXT, PRIMARY KEY (scan_date, ticker));
        INSERT INTO snapshot_rows (scan_date,ticker,price,fair_value,rank,extra)
            VALUES ('2026-08-01','OLD',10.0,42.0,1,'{}');""")
    con.commit(); con.close()

    st = Store(path)                                   # opening it runs the migration
    cols = {r[1] for r in sqlite3.connect(path)
            .execute("PRAGMA table_info(snapshot_rows)").fetchall()}
    assert {"fair_value_withheld", "fair_value_withheld_reason"} <= cols

    old = st.load_snapshot("2026-08-01")[0]
    assert old["fair_value"] == 42.0 and ROW_WITHHELD not in old

    fresh = {"ticker": "NEW", "price": 10.0, "rank": 1, "extra": {}}
    record_refusal(fresh, "Cannot value this name: the model's $140.00 is 14.0x the price.")
    st.save_snapshot("2026-08-02", [fresh], "test", {})
    assert st.load_snapshot("2026-08-02")[0].get(ROW_WITHHELD) is True


def test_net_debt_is_unit_stamped_like_market_cap():
    """`net_debt` was missing from providers._ABSOLUTE_USD, so it alone came out in the
    provider's native millions while market_cap / ev / total_debt beside it were scaled to
    dollars. fairvalue.py then computed `ev = market_cap + net_debt` as dollars + millions,
    making the net-debt term ~1e-6 of its true size. CHTR's real net debt / market cap is
    4.68; the lens saw 96,644 against 20.6 billion."""
    from valuation.data.models import CompanyData
    from valuation.screener.providers import company_to_metrics, _ABSOLUTE_USD
    assert "net_debt" in _ABSOLUTE_USD
    cd = CompanyData(ticker="LEV", currency="USD", price=100.0, shares_diluted=100.0,
                     market_cap=10_000.0, total_debt=50_000.0, cash_sti=0.0,
                     revenue=20_000.0, ebit=3_000.0, da=1_000.0)
    m = company_to_metrics(cd)
    # ev is mc + nd; all three must live on the same scale or the bridge is meaningless
    assert abs(m["ev"] - (m["market_cap"] + m["net_debt"])) < 1.0, (
        m["ev"], m["market_cap"], m["net_debt"])
    assert m["net_debt"] / m["market_cap"] == pytest_approx(5.0), m["net_debt"] / m["market_cap"]


def pytest_approx(x, tol=1e-6):
    class _A:
        def __eq__(self, other): return abs(other - x) < tol
        def __repr__(self): return f"~{x}"
    return _A()


def test_multiples_lens_refuses_above_five_times_price():
    """The EV bridge reduces to `implied/price = r + (nd/mc)*(r-1)`, so at the 3x re-rate
    cap a name with 4.68x leverage has a CEILING of 12.4x price. MAX_GROWTH_VALUE was
    checked inside _growth_value only — the multiples branch had no absolute cap at all,
    and this lens feeds the PUBLIC /api/hotstocks. One bar now, 5x, matching the valuation
    page's FV_BAND_HIGH."""
    from valuation.screener import fairvalue as FV
    from valuation.engine.publication import FV_BAND_HIGH
    # CONSOLIDATE-1: the lens no longer owns a bar. MAX_GROWTH_VALUE (the dead 20x) is gone
    # and MAX_LENS_VALUE is an alias for the one constant, not a second definition.
    assert FV.MAX_LENS_VALUE is FV_BAND_HIGH
    assert not hasattr(FV, "MAX_GROWTH_VALUE"), "the dead 20x bar must not come back"

    # a heavily levered name whose EV multiple is 3x cheaper than its peers
    row = {"ticker": "LEV", "sector": "Utilities", "price": 10.0, "market_cap": 1_000.0,
           "extra": {"ev_sales": 0.5, "net_debt": 4_000.0}}
    peers = [{"ticker": f"P{i}", "sector": "Utilities", "price": 10.0,
              "market_cap": 1_000.0, "extra": {"ev_sales": 3.0, "net_debt": 0.0}}
             for i in range(6)]
    meds = FV.peer_medians([row] + peers)
    got = FV._mature_value(row, meds, 10.0)
    assert got is None, f"published {got} on a $10.00 price — must refuse above 5x"

    # and an ordinary name is untouched
    ok = {"ticker": "ORD", "sector": "Utilities", "price": 10.0, "market_cap": 1_000.0,
          "extra": {"ev_sales": 2.5, "net_debt": 0.0}}
    v = FV._mature_value(ok, FV.peer_medians([ok] + peers), 10.0)
    assert v is not None and v <= 50.0


def _growth_frames():
    """The two frames yfinance actually returns, with GILD's real 2026-08-05 values."""
    import pandas as pd
    ge = pd.DataFrame({"stockTrend": [-0.1214, 0.1963, -1.0838, 15.0829],
                       "indexTrend": [0.4471, 0.2290, 0.2919, 0.1438]},
                      index=["0q", "+1q", "0y", "+1y"])
    rev = pd.DataFrame({"avg": [1, 2, 3, 32296850630], "growth": [0.0102, 0.0233, 0.0289, 0.0615],
                        "currency": ["USD"] * 4},
                       index=["0q", "+1q", "0y", "+1y"])
    return ge, rev


def test_analyst_revenue_growth_reads_the_revenue_series_not_earnings():
    """THE bug. `growth_estimates.loc["+1y"].iloc[0]` takes `stockTrend` — EARNINGS growth —
    which off a negative base reads 15.0829 for GILD. Measured across 241 names: the
    positional read differed from a real revenue figure by >1pp on 202 of 239, and 194 of
    those sat INSIDE the [-0.30, 1.00] band the engine rejects on, so they were silently
    wrong. The revenue-estimate frame's NAMED `growth` column is the right source (0.0615)."""
    from valuation.data.yahoo import _analyst_revenue_growth
    ge, rev = _growth_frames()

    class _T:
        growth_estimates = ge
        revenue_estimate = rev

    got = _analyst_revenue_growth(_T(), {"revenueGrowth": 0.044})
    assert abs(got - 0.0615) < 1e-9, f"got {got} — must read the revenue series, not stockTrend"
    assert got != 15.0829 and abs(got - 1.0) > 1e-9, "and must not be the clamped earnings value"


def test_analyst_revenue_growth_rejects_out_of_band_at_the_source():
    """Defence-in-depth: the engine rejects out-of-band values too, but the source must not
    hand them on. `info["revenueGrowth"]` is not clean either — COF reads 11.11."""
    from valuation.data.yahoo import _analyst_revenue_growth
    _, rev = _growth_frames()
    rev = rev.copy()
    rev.loc["+1y", "growth"] = 11.11

    class _T:
        growth_estimates = None
        revenue_estimate = rev

    assert _analyst_revenue_growth(_T(), {"revenueGrowth": 11.11}) is None, \
        "an 1111% revenue growth must be refused, not passed on"

    class _NoFrames:
        growth_estimates = None
        revenue_estimate = None

    assert _analyst_revenue_growth(_NoFrames(), {"revenueGrowth": 0.044}) == 0.044
    assert _analyst_revenue_growth(_NoFrames(), {"revenueGrowth": -0.9}) is None


def test_analyst_revenue_growth_survives_a_frame_without_the_stock_column():
    """BRK.B's growth_estimates frame has ONLY an `indexTrend` column, so the positional
    read was taking the S&P 500's growth estimate as Berkshire's revenue growth. Selecting
    by name must simply not find a revenue series and fall back."""
    import pandas as pd
    from valuation.data.yahoo import _analyst_revenue_growth
    ge = pd.DataFrame({"indexTrend": [0.4471, 0.1438]}, index=["0q", "+1y"])

    class _T:
        growth_estimates = ge
        revenue_estimate = None

    assert _analyst_revenue_growth(_T(), {"revenueGrowth": 0.051}) == 0.051


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
