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

    assert _usable_cache({"market_cap": 275_844.66}) is None            # legacy: no stamp
    assert _usable_cache({"market_cap": 275e9, "units": "usd"}) is not None

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

    long = T.summarize("roth", meta_path="/nope", history_path="/nope",
                       store=_St(_series(T.MIN_LIVE_DAYS + 5)))
    assert long["thin"] is False and long["headline"] == "live"
    assert long["live"]["ann_alpha"] is not None

    # Backtested figures always travel with the live ones, never merged into them.
    assert thin["backtested"]["net_sharpe"] == 1.17
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


def test_live_track_is_absent_not_invented_when_there_is_no_data():
    from valuation.screener import index_track as T
    out = T.summarize("roth", meta_path="/nope/a.json", history_path="/nope/b.csv")
    assert out["available"] is False and out["live"] is None
    assert out["headline"] == "backtested"
    assert out["backtested"]["net_sharpe"] is not None, "the backtest still has something to say"


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
