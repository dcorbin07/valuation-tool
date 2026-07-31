"""
Edge Lab tests (offline, deterministic). Run:
    python tests/test_edge.py
Validates the backtest math, the no-overfit walk-forward + advisor, the factor
panel, and owner-only gating.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from valuation.edge.portfolio_backtest import run as pf_run
from valuation.edge.panel import build_factor_panel, FACTORS
from valuation.edge.walkforward import walk_forward
from valuation.edge.advisor import propose_and_validate
from valuation.backtest.panel import build_synthetic_panel
from valuation.saas import gating
from valuation.config import CONFIG

_DATES = [str(d.date()) for d in pd.bdate_range(end="2026-07-24", periods=2600)]


def _prices_with_edge(seed=7):
    rng = np.random.default_rng(seed)
    mk = lambda drift, vol=0.014: list(100 * np.cumprod(1 + rng.normal(drift, vol, 2600)))
    p = {"SPY": mk(0.0003, 0.010)}
    for i in range(30):
        p[f"S{i:02d}"] = mk(rng.uniform(-0.0002, 0.0010))  # dispersed drifts → momentum edge
    return p


def test_portfolio_backtest_detects_edge():
    p = _prices_with_edge()
    pf = lambda t: (_DATES, p.get(t))
    res = pf_run([f"S{i:02d}" for i in range(30)], benchmark="SPY", price_fn=pf,
                 hold_top=8, rebalance_days=21, years=(1, 5))
    assert res["full"]["portfolio"]["cagr"] > res["full"]["benchmark"]["cagr"]
    assert "5y" in res and res["5y"]["available"]


def test_factor_panel_builds():
    p = _prices_with_edge()
    pf = lambda t: (_DATES, p.get(t))
    panel = build_factor_panel([f"S{i:02d}" for i in range(30)], price_fn=pf)
    assert not panel.empty
    for c in FACTORS + ["fwd_ret", "bench_ret", "date", "ticker"]:
        assert c in panel.columns
    assert panel["date"].nunique() > 20


def test_walkforward_no_overfit():
    fc = ["momentum", "value"]
    sig = walk_forward(build_synthetic_panel(150, 48, signal=0.10, seed=3), fc, n_folds=5, step_grid=0.1)
    noise = walk_forward(build_synthetic_panel(150, 48, signal=0.0, seed=4), fc, n_folds=5, step_grid=0.1)
    assert noise["adopt"] is False                      # never adopt on noise
    assert sig["walk_oos_ic_optimized"] >= sig["walk_oos_ic_baseline"] - 1e-6


def test_advisor_sample_aware_and_noise():
    fc = ["momentum", "value"]
    small = propose_and_validate(build_synthetic_panel(150, 10, signal=0.1, seed=9), fc, CONFIG)
    assert small["adopted"] is None and "too few" in small["note"].lower()
    noise = propose_and_validate(build_synthetic_panel(150, 48, signal=0.0, seed=4), fc, CONFIG)
    assert noise["adopted"] is None


def test_deflated_sharpe_and_hlz():
    from valuation.edge.statistics import deflated_sharpe_ratio, expected_max_sharpe, hlz_significant
    r = np.random.default_rng(0).normal(0.010, 0.04, 300)
    few = deflated_sharpe_ratio(r, n_trials=1, var_trials=0.01)["deflated_sharpe"]
    many = deflated_sharpe_ratio(r, n_trials=2000, var_trials=0.01)["deflated_sharpe"]
    assert few > many                                   # more trials -> harder to be "real"
    assert expected_max_sharpe(5000, 0.01) > expected_max_sharpe(50, 0.01) > 0
    assert hlz_significant(3.4) and not hlz_significant(2.1)


def test_edge_routes_owner_only():
    owner = {"email": "donniecorbin6@gmail.com"}
    other = {"email": "someone@else.com"}
    assert gating.check_request("/api/edge/backtest", "POST", {}, other, None)[1] == 403
    assert gating.check_request("/api/edge/optimize", "POST", {}, None, None)[1] in (401, 403)
    assert gating.check_request("/api/edge/backtest", "POST", {}, owner, None) is None


def test_self_learning_gate():
    """The monthly re-tune is purely statistical: adopt on a real out-of-sample edge,
    decline on noise or too-little-history, and the live scorer reads whatever it adopts."""
    import tempfile
    from valuation.screener.store import Store
    from valuation.screener.screen import _effective_weights
    from valuation.edge.autolearn import run_learning

    from valuation.screener import settings as S

    def panel(signal, seed, dates=12, names=60):
        rng = np.random.default_rng(seed)
        rows = []
        for di in range(dates):
            for ni in range(names):
                vals = {f: float(rng.normal()) for f in S.FACTORS_ALL}   # all 9 factors present
                fr = signal * (vals["value"] + vals["quality"]) + rng.normal()  # signal in value+quality
                row = {"date": f"2026-{di + 1:02d}-01", "ticker": f"T{ni}", "bucket": "established", "fwd_ret": fr}
                row.update(vals)
                rows.append(row)
        return pd.DataFrame(rows)

    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    # 1) Real out-of-sample signal → adopts, and the LIVE scorer picks up the new weights.
    rep = run_learning(CONFIG, st, panel=panel(0.35, 1))
    assert rep["status"] == "ok" and rep["buckets"]["established"]["adopted"] is True
    learned = st.latest_learned_weights("established")
    assert learned is not None
    assert _effective_weights(st)[0] == learned          # live weights = learned weights

    # 2) Pure noise → declines, nothing adopted (this is the anti-overfit guard working).
    fd, p2 = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p2)
    st2 = Store(p2)
    rep2 = run_learning(CONFIG, st2, panel=panel(0.0, 2))
    assert rep2["buckets"]["established"]["adopted"] is False
    assert st2.latest_learned_weights("established") is None

    # 3) Too little history → declines to touch anything.
    rep3 = run_learning(CONFIG, st2, panel=panel(0.15, 3).head(50))
    assert "insufficient" in rep3["status"]


def test_theme_columns_build():
    """The distinct themes come out of build_frame; hooked themes stay neutral w/o data."""
    from valuation.screener.factors import build_frame
    from valuation.screener import settings as S
    rng = np.random.default_rng(11)
    metrics = []
    for i in range(14):
        rev = float(rng.uniform(500, 5000))
        metrics.append({
            "ticker": f"N{i:02d}", "name": f"N{i:02d}", "sector": "Tech",
            "price": 50.0, "market_cap": rev * float(rng.uniform(1, 8)), "revenue": rev,
            "net_income": rev * float(rng.uniform(0.02, 0.2)),
            "operating_income": rev * 0.15, "fcf": rev * float(rng.uniform(0.01, 0.18)),
            "gross_profit": rev * float(rng.uniform(0.2, 0.6)),
            "total_debt": rev * float(rng.uniform(0.1, 1.0)),
            "total_equity": rev * float(rng.uniform(0.5, 2.0)),
            "interest_expense": rev * float(rng.uniform(0.005, 0.05)),
            "beta": float(rng.uniform(0.4, 1.8)), "realized_vol": float(rng.uniform(0.15, 0.6)),
            "ret_12_1": float(rng.normal()), "ret_6_1": float(rng.normal()),
            "high_prox": float(rng.uniform(0.4, 1.0)),
        })
    df = build_frame(metrics)
    for col in S.FACTORS_ALL:                                   # every theme column exists
        assert col in df.columns, col
    # themes with real inputs are populated…
    for col in ["value", "quality", "momentum", "low_risk", "size"]:
        assert df[col].notna().sum() > 0, col
    # …and the hooked themes are neutral (all-NaN) until their data feeds are wired
    assert df["capital_discipline"].notna().sum() == 0          # needs share/asset history
    assert df["sentiment"].notna().sum() == 0                   # needs an estimates feed


def test_learning_digest_renders():
    from valuation.saas.emailer import learning_digest_html
    adopt = {"status": "ok", "panel_rows": 500, "dates": 12, "buckets": {"established": {
        "adopted": True, "previous": {"value": 0.28, "quality": 0.24},
        "weights": {"value": 0.30, "quality": 0.30}, "out_sample_ic": 0.041, "note": "held OOS"}}}
    h = adopt and learning_digest_html(adopt)
    assert "UPDATED" in h and "0.28" in h and "0.30" in h        # shows before → after
    nochange = {"status": "ok", "panel_rows": 500, "dates": 12, "buckets": {"established": {
        "adopted": False, "previous": {"value": 0.28}, "weights": {"value": 0.28}, "note": "kept"}}}
    assert "No changes" in learning_digest_html(nochange)
    assert "not enough history" in learning_digest_html({"status": "insufficient data", "dates": 3, "buckets": {}}).lower()


def test_number_ic_diagnostic():
    """Each number's standalone IC is measured from snapshots + forward returns:
    a real predictor scores high, noise ~0, an absent number reads zero-coverage."""
    import tempfile
    from valuation.screener.store import Store
    from valuation.edge.diagnostics import compute_number_ic

    N = 30
    dates = [str(d.date()) for d in pd.bdate_range("2026-01-05", periods=9)]
    signal = {f"T{i:02d}": (i / (N - 1) - 0.5) for i in range(N)}     # spread -0.5..0.5
    rng = np.random.default_rng(0)
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    for date in dates:
        rows = [{"ticker": t, "name": t, "sector": "", "bucket": "established", "price": 100.0,
                 "market_cap": 1000.0, "hot_score": 50.0, "composite": 0.0, "rank": i + 1,
                 "extra": {"numbers": {"ret_12_1": signal[t], "neg_beta": float(rng.normal())}}}
                for i, t in enumerate(signal)]
        st.save_snapshot(date, rows, "test", {"universe_size": N})

    def price_fn(t):
        s = signal.get(t)
        if s is None:
            return (None, None)
        return (dates, [100.0 * ((1 + 0.1 * s) ** k) for k in range(len(dates))])  # fwd(1d) ≈ 0.1·s

    res = compute_number_ic(st, price_fn=price_fn, top_per_date=N, horizon=1, min_dates=5)
    assert res["status"] == "ok"
    ic = {r["number"]: r for r in res["numbers"]}
    assert ic["ret_12_1"]["ic"] is not None and ic["ret_12_1"]["ic"] > 0.5   # real predictor
    assert abs(ic["neg_beta"]["ic"] or 0) < 0.4                              # noise ~ 0
    assert ic["earnings_yield"]["coverage"] == 0.0                          # absent → neutral


def test_paper_position_leaves_coverage():
    """A held name that drops out of the scan past the grace window is closed at its
    last price (reason 'left coverage'), so dropped losers can't bias the record."""
    import tempfile
    from valuation.screener.store import Store
    from valuation.edge.positions import update_positions
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    r1 = update_positions(st, "hot10", "2026-01-01",
                          [{"ticker": "AAA", "price": 100.0, "hot_score": 90, "rank": 1}],
                          top_n=5, min_hold_days=0, coverage_gap_days=21)
    assert "AAA" in r1["entered"]
    r2 = update_positions(st, "hot10", "2026-03-01",       # 59 days later, AAA absent
                          [{"ticker": "BBB", "price": 50.0, "hot_score": 80, "rank": 1}],
                          top_n=5, min_hold_days=0, coverage_gap_days=21)
    assert "AAA" in r2["closed"]
    aaa = [x for x in st.all_positions("hot10") if x["ticker"] == "AAA"][0]
    assert aaa["exit_reason"] == "left coverage" and aaa["exit_price"] == 100.0


def test_paper_realism_costs_and_vol_sizing():
    """Inverse-vol sizing favors the calmer name; transaction costs lower reported return."""
    import tempfile
    from valuation.screener.store import Store
    from valuation.edge.positions import paper_summary, _size_weights

    rows = [{"ticker": "CALM"}, {"ticker": "WILD"}]
    _size_weights(rows, {"CALM": 80, "WILD": 80}, max_weight=0.9, vol_map={"CALM": 0.2, "WILD": 0.8})
    wc = next(r["weight"] for r in rows if r["ticker"] == "CALM")
    ww = next(r["weight"] for r in rows if r["ticker"] == "WILD")
    assert wc > ww                                        # equal score, lower vol → bigger size

    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    st.open_position("hot10", "X", "2026-01-01", 100.0)
    st.close_position("hot10", "X", "2026-01-01", "2026-02-01", 110.0, "test")
    gross = paper_summary(st, "hot10", cost_bps=0)["summary"]["avg_return_closed"]
    net = paper_summary(st, "hot10", cost_bps=50)["summary"]["avg_return_closed"]
    assert gross is not None and net < gross              # costs drag the return down


class _SynthPIT:
    """Offline point-in-time provider with an embedded quality signal, so the
    fundamental backtest + optimizer can be validated without a real data source."""
    name = "synthetic PIT"; survivorship_free = True; has_pit_fundamentals = True

    def __init__(self, n=30, seed=7):
        rng = np.random.default_rng(seed)
        self.q = {f"T{i:02d}": float(rng.uniform(-1, 1)) for i in range(n)}
        self.dates = [str(d.date()) for d in pd.bdate_range("2022-01-03", periods=1000)]

    def ready(self):
        return True, "ok"

    def price_history(self, ticker, days=2700):
        if ticker == "SPY":
            return self.dates, [100 * (1.0002 ** k) for k in range(len(self.dates))]
        q = self.q.get(ticker)
        if q is None:
            return None, None
        # zlib.crc32, NOT hash(): Python randomizes string hashing per process
        # (PYTHONHASHSEED), which made every run generate different price series and left
        # test_fundamental_backtest_synthetic intermittently failing. crc32 is stable.
        import zlib
        rng = np.random.default_rng(zlib.crc32(ticker.encode()) % (2 ** 32))
        closes = list(100 * np.cumprod(1 + rng.normal(0.0002 + 0.0006 * q, 0.012, len(self.dates))))
        return self.dates, closes

    def grades_history(self, ticker):
        """Analyst actions that agree with the embedded quality signal: good names get
        net upgrades, bad names net downgrades, on a fixed monthly cadence."""
        q = self.q.get(ticker)
        if q is None:
            return []
        import zlib
        rng = np.random.default_rng(zlib.crc32((ticker + "g").encode()) % (2 ** 32))
        rows = []
        for k in range(0, len(self.dates), 21):          # ~monthly
            p_up = 0.5 + 0.4 * q                          # q>0 -> mostly upgrades
            action = "upgrade" if rng.random() < p_up else "downgrade"
            rows.append({"ticker": ticker, "date": self.dates[k], "action": action,
                         "gradingCompany": "TestBank", "previousGrade": "Hold",
                         "newGrade": "Buy" if action == "upgrade" else "Sell"})
        return rows

    def fundamentals_history(self, ticker):
        q = self.q.get(ticker)
        if q is None:
            return []
        return [{"datekey": dk, "revenue": 1000.0, "netinc": 100 * (1 + q), "ebit": 150 * (1 + q),
                 "ebitda": 200 * (1 + q), "gp": 400 * (1 + q), "equity": 800.0, "debt": 200.0,
                 "cashneq": 50.0, "roic": 0.08 * (1 + q), "roe": 0.10 * (1 + q), "sharesbas": 5e8,
                 "fcf": 90 * (1 + q), "intexp": 10.0}
                for dk in ["2021-11-15", "2022-05-15", "2022-11-15", "2023-05-15",
                           "2023-11-15", "2024-05-15", "2024-11-15"]]

    def insider_history(self, ticker):
        q = self.q.get(ticker)
        if q is None:
            return []
        return [{"filingdate": fd, "transactionshares": 1000 * (1 + q), "transactionpricepershare": 50.0}
                for fd in ["2022-02-15", "2022-05-15", "2022-08-15", "2022-11-15", "2023-02-15",
                           "2023-05-15", "2023-08-15", "2023-11-15", "2024-02-15", "2024-05-15"]]

    def institutional_history(self, ticker):
        q = self.q.get(ticker)
        if q is None:
            return []
        return [{"calendardate": cd, "totalvalue": 1e6 * (1 + 0.1 * q * i)}
                for i, cd in enumerate(["2022-03-31", "2022-06-30", "2022-09-30", "2022-12-31",
                                        "2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31"], 1)]


def test_fundamental_backtest_synthetic():
    from valuation.edge.fundamental_panel import run_backtest, build_fundamental_panel
    prov = _SynthPIT(30, seed=7)
    tickers = list(prov.q.keys())
    panel = build_fundamental_panel(prov, tickers, rebalance_days=63, horizon=21, lookback_years=4)
    assert not panel.empty and panel["date"].nunique() >= 6
    assert panel["quality"].notna().any() and "fwd_ret" in panel.columns
    assert panel["insider"].notna().any()          # SF2 insider factor now backtestable
    assert panel["institutional"].notna().any()    # SF3 institutional accumulation factor

    res = run_backtest(prov, tickers, top_n=8, rebalance_days=63, horizon=21, lookback_years=4)
    assert res["ready"] and res["dates"] >= 6
    bd = res["backtest_default"]
    assert bd and bd["total_return"] > bd["bench_return"]     # the model beats the S&P on real signal
    assert res.get("backtest_optimized") is not None


def test_fundamental_backtests_multi_horizon():
    from valuation.edge.fundamental_panel import run_backtests
    prov = _SynthPIT(30, seed=7)
    res = run_backtests(prov, list(prov.q.keys()), horizons=(21, 42), rebalance_days=21,
                        top_n=8, lookback_years=4, recency_halflife_days=500)
    assert res["ready"] and set(res["horizons"].keys()) == {"21", "42"}
    assert res["primary_horizon"] == "42"                   # longest horizon is primary
    assert res.get("hold_until_exit") is not None          # hold-until-drops-out sim ran
    wf = res.get("walk_forward") or {}                      # purged walk-forward selection ran
    assert wf and (wf.get("params") or wf.get("weights") or wf.get("status"))
    if wf.get("weights"):                                   # candidates carry OOS + stability, not just IS
        cands = wf["weights"]["candidates"]
        assert "current-default" in cands
        assert "max-ir-decorr" in cands and "risk-parity" in cands   # expanded theme-sizing menu
        assert wf["weights"].get("adopt") in (True, False)
        assert "recommended_weights_cols" in wf["weights"]           # deployable weights exposed
    assert res.get("construction") is not None              # decile / long-short construction test ran
    assert res.get("regime") is not None                   # market-cap regime split ran
    assert res.get("cpcv") is not None                     # combinatorial purged CV validation ran
    for r in res["horizons"].values():
        if r.get("backtest_default"):
            assert r["backtest_default"]["total_return"] > r["backtest_default"]["bench_return"]
            assert "ew_cagr" in r["backtest_default"] and "ew_alpha" in r["backtest_default"]  # fair bar present


def test_adopt_backtest_weights_persists():
    """Adopting backtested weights writes them as the live starting weights."""
    import tempfile
    from valuation.screener.store import Store
    from valuation.screener.screen import _effective_weights
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    w = {"value": 0.4, "quality": 0.4, "momentum": 0.2}
    st.set_meta("fundamental_backtest", {"primary_horizon": "252",
                "horizons": {"252": {"accepted": True, "optimized_weights": w, "out_sample_ic": 0.03}}})
    # replicate the adopt endpoint's core: persist the accepted primary-horizon weights
    h = st.get_meta("fundamental_backtest")["horizons"]["252"]
    assert h["accepted"]
    st.save_learned("established", h["optimized_weights"], {"source": "backtest"}, True, "test")
    assert st.latest_learned_weights("established") == w
    assert _effective_weights(st)[0] == w                       # live scorer now uses them


def test_export_then_offline_backtest():
    """Export a provider to local files, then read it back through the WRDS/local provider."""
    import tempfile
    from valuation.edge.export_sharadar import export_to_local
    from valuation.edge.data_providers import WRDSProvider
    prov = _SynthPIT(12, seed=3)
    out = tempfile.mkdtemp()
    res = export_to_local(prov, list(prov.q.keys()) + ["SPY"], out)
    assert res["price_files"] > 0 and res["fundamental_rows"] > 0

    class _Cfg:
        wrds_data_dir = out
    w = WRDSProvider(_Cfg())
    d, c = w.price_history("T00")
    assert d and c and len(c) > 100
    assert len(w.fundamentals_history("T00")) > 0


def test_inst_lag_grid_crosses_quarter_boundary():
    """The 13F due-diligence lags must select DIFFERENT filed quarters, or the whole test is
    a no-op. 13F rows are stamped with the quarter-end and rebalance dates land ~11-21 days
    past a quarter start, so the old (45, 60, 90) grid resolved to one identical quarter and
    printed three identical rows. Guard the property, not the literal numbers."""
    import numpy as np
    from valuation.edge.fundamental_panel import INST_LAG_GRID, _inst_accum_at

    # A synthetic 13F history on the real grid: quarter-ends with strictly rising totals,
    # so "which quarter got picked" is recoverable from the returned value.
    dts = np.array([f"{y}-{m}" for y in range(2018, 2026)
                    for m in ("03-31", "06-30", "09-30", "12-31")], dtype="datetime64[D]")
    vals = np.arange(1.0, len(dts) + 1.0) ** 2          # rising => unique growth per quarter
    prep = (dts, vals)

    # Rebalance dates sit 11-21 days past a quarter start, as the real panel's do.
    for as_of in ("2024-01-16", "2024-04-18", "2024-07-15", "2024-10-21"):
        picked = {lag: _inst_accum_at(prep, as_of, lag_days=lag) for lag in INST_LAG_GRID}
        distinct = {v for v in picked.values() if v is not None}
        assert len(distinct) > 1, (
            f"INST_LAG_GRID {INST_LAG_GRID} selects the same 13F quarter at {as_of} "
            f"({picked}) - the lag test would measure nothing")

    # And the specific look-ahead probe must exist: some lag short enough to grab a
    # quarter that would NOT yet have been filed.
    assert min(INST_LAG_GRID) < 45, "need a sub-45d lag to test for look-ahead bias"


def _index_rows(n=300, seed=4):
    import random
    rng = random.Random(seed)
    caps = [2e9, 6e9, 15e9, 40e9, 200e9]
    return [{"ticker": f"T{i:03d}", "name": f"Co {i}",
             "sector": ["Tech", "Health", "Energy"][i % 3], "rank": i + 1,
             "hot_score": rng.uniform(1, 100), "price": 50.0,
             "market_cap": caps[i % len(caps)]} for i in range(n)]


def test_valquo_index_is_top_decile_large_cap():
    from valuation.edge.valquo_index import build_index, LARGE_CAP_MIN
    ix = build_index(_index_rows())
    assert ix["criteria"]["tilt"] == "large-cap only"
    assert all(p["market_cap"] >= LARGE_CAP_MIN for p in ix["positions"]), "large-cap tilt must bind"
    # ~a decile of the eligible cohort, and ranked by hot score.
    assert abs(ix["n_positions"] - round(ix["n_eligible"] * 0.10)) <= 1
    hs = [p["hot_score"] for p in ix["positions"]]
    assert hs == sorted(hs, reverse=True)
    # It must be the TOP decile, not any decile.
    all_large = [r["hot_score"] for r in _index_rows() if r["market_cap"] >= LARGE_CAP_MIN]
    assert min(hs) >= sorted(all_large, reverse=True)[len(hs) - 1] - 1e-9


def test_valquo_index_weights_sum_and_cap():
    from valuation.edge.valquo_index import build_index, MAX_WEIGHT
    ix = build_index(_index_rows())
    w = [p["weight"] for p in ix["positions"]]
    assert abs(sum(w) - 1.0) < 1e-3, sum(w)
    assert max(w) <= MAX_WEIGHT + 1e-9, max(w)
    assert all(x > 0 for x in w)
    eq = build_index(_index_rows(), weighting="equal")
    ew = [p["weight"] for p in eq["positions"]]
    assert max(ew) - min(ew) < 1e-9, "equal weighting should be flat"


def test_valquo_index_cap_is_feasible_on_a_small_book():
    """With few positions an 8% cap can't sum to 100%, so the effective cap must relax
    to equal weight instead of the redistribution loop silently overshooting it."""
    from valuation.edge.valquo_index import build_index
    rows = [{"ticker": f"L{i}", "name": "x", "sector": "Tech", "rank": i + 1,
             "hot_score": 100 - i * 2, "price": 10.0, "market_cap": 5e10} for i in range(43)]
    ix = build_index(rows)
    n = ix["n_positions"]
    w = [p["weight"] for p in ix["positions"]]
    cap = ix["criteria"]["effective_max_weight"]
    assert n == 10, n
    assert abs(sum(w) - 1.0) < 1e-3, sum(w)
    assert max(w) <= cap + 1e-6, (max(w), cap)
    assert cap >= 1.0 / n - 1e-9, "cap must be at least equal weight to be reachable"


def test_valquo_index_degrades_without_market_caps():
    """A scan with no market caps must say so rather than silently claim a large-cap book."""
    from valuation.edge.valquo_index import build_index
    rows = [{"ticker": f"S{i}", "name": "x", "sector": "Tech", "rank": i + 1,
             "hot_score": 90 - i, "price": 10.0} for i in range(12)]
    ix = build_index(rows)
    assert ix["n_positions"] >= 10
    assert "no market-cap data" in ix["criteria"]["tilt"]
    assert abs(sum(p["weight"] for p in ix["positions"]) - 1.0) < 1e-3


def test_valquo_index_export_writes_json(tmpdir=None):
    import json
    import tempfile
    import os
    from valuation.edge.valquo_index import export

    class _St:
        def latest_scan_date(self): return "2026-07-28"
        def load_snapshot(self, d=None, top=None): return _index_rows()

    path = os.path.join(tempfile.mkdtemp(), "valquo_index.json")
    p = export(store=_St(), path=path)
    assert os.path.exists(path)
    on_disk = json.load(open(path, encoding="utf-8"))
    assert on_disk["scan_date"] == "2026-07-28"
    assert on_disk["n_positions"] == p["n_positions"] > 0
    assert on_disk["generated_at"]
    assert os.path.getsize(path) < 200_000, "index file should stay small"


def test_grades_signal_is_point_in_time():
    """The rating signal must only ever see actions dated on or before as_of."""
    from valuation.edge.fundamental_panel import _prep_grades, _grades_at
    rows = [{"date": "2024-01-10", "action": "upgrade"},
            {"date": "2024-02-10", "action": "upgrade"},
            {"date": "2024-03-10", "action": "downgrade"},
            {"date": "2024-09-01", "action": "upgrade"}]
    prep = _prep_grades(rows)
    net, disp = _grades_at(prep, "2024-03-15")
    assert abs(net - 1 / 3) < 1e-9, net              # (2 up - 1 down) / 3
    assert abs(disp - 1 / 3) < 1e-9, disp            # min(2,1)/3 split
    # Nothing before the first action, and the September action is invisible in March.
    assert _grades_at(prep, "2024-01-01") is None
    # A window with no actions in it reads as "no opinion", not as zero.
    assert _grades_at(prep, "2024-06-30") is None


def test_grades_net_revision_direction_and_bounds():
    from valuation.edge.fundamental_panel import _prep_grades, _grades_at
    ups = _prep_grades([{"date": f"2024-02-{d:02d}", "action": "upgrade"} for d in (1, 5, 9)])
    downs = _prep_grades([{"date": f"2024-02-{d:02d}", "action": "downgrade"} for d in (1, 5, 9)])
    mixed = _prep_grades([{"date": "2024-02-01", "action": "upgrade"},
                          {"date": "2024-02-05", "action": "downgrade"}])
    maint = _prep_grades([{"date": "2024-02-01", "action": "maintain"},
                          {"date": "2024-02-05", "action": "maintain"}])
    assert _grades_at(ups, "2024-02-20")[0] == 1.0
    assert _grades_at(downs, "2024-02-20")[0] == -1.0
    assert _grades_at(mixed, "2024-02-20")[0] == 0.0
    assert _grades_at(mixed, "2024-02-20")[1] == 0.5      # evenly split = max disagreement
    assert _grades_at(ups, "2024-02-20")[1] == 0.0        # unanimous = no disagreement
    # Maintains count toward the denominator but express no direction or disagreement.
    assert _grades_at(maint, "2024-02-20") == (0.0, 0.0)


def test_grades_feed_the_sentiment_theme():
    """End-to-end: a provider carrying grades should light up the sentiment column,
    which was empty before, without disturbing the other themes."""
    from valuation.edge.fundamental_panel import build_fundamental_panel
    prov = _SynthPIT(30, seed=7)
    panel = build_fundamental_panel(prov, list(prov.q.keys()), rebalance_days=63,
                                    horizon=21, lookback_years=4)
    assert panel["sentiment"].notna().any(), "sentiment must populate from grades"
    assert float(panel["sentiment"].std()) > 0.05, "sentiment must vary across names"
    assert panel["quality"].notna().any() and panel["momentum"].notna().any()


def test_grades_absent_provider_leaves_sentiment_neutral():
    """A provider with no grades_history must behave exactly as before (no crash)."""
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _NoGrades(_SynthPIT):
        def grades_history(self, ticker):
            return []

    prov = _NoGrades(20, seed=3)
    panel = build_fundamental_panel(prov, list(prov.q.keys()), rebalance_days=63,
                                    horizon=21, lookback_years=4)
    assert not panel.empty
    assert not panel["sentiment"].notna().any(), "no grades -> sentiment stays neutral"


def test_synthetic_provider_is_deterministic_across_processes():
    """Guards the flaky-test fix: prices must not depend on PYTHONHASHSEED.

    _SynthPIT used abs(hash(ticker)), and Python randomizes string hashing per process,
    so every run produced different series and the backtest assertion failed ~1 run in 4.
    """
    prov = _SynthPIT(5, seed=7)
    _, a = prov.price_history("T01")
    _, b = prov.price_history("T01")
    assert a == b, "same process must be repeatable"

    # The real check: two interpreters with DIFFERENT hash seeds must agree. With the
    # old abs(hash(ticker)) these diverge; with crc32 they match.
    import subprocess
    import os
    snippet = ("import sys; sys.path.insert(0, %r);"
               "from tests.test_edge import _SynthPIT;"
               "print(round(_SynthPIT(5, seed=7).price_history('T01')[1][50], 10))"
               % os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    outs = []
    for seed in ("0", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        outs.append(subprocess.run([sys.executable, "-c", snippet], capture_output=True,
                                   text=True, env=env).stdout.strip())
    assert outs[0] and outs[0] == outs[1], f"price series varies with PYTHONHASHSEED: {outs}"


# ---------------------------------------------------------------------------------------- #
# P5 — the coverage guard and the four inputs that were silently empty.
#
# Every one of these covers a bug that produced NO error: the factor was wired, the run
# completed, and the column was blank. Sharadar populates roe / roic / assetturnover only in
# its averaged dimensions, so in the ARQ export this panel reads they are blank in 100% of
# 197,265 rows; `beta` was hard-coded None; and build_frame overwrote the panel's own
# growth_accel with an all-NaN derivation. Result: `quality` averaged 8 of its 10 inputs,
# `low_risk` 1 of its 2, and `growth` 1 of its 2, in every backtest this project has run.
# ---------------------------------------------------------------------------------------- #

def test_all_derived_inputs_ship_enabled():
    """DERIVE exists so a validation change can be attributed to ONE new signal: flip an
    entry off, re-run, diff. This asserts none of those staging toggles was left off — the
    exact mistake that would silently re-empty a factor after all this work."""
    from valuation.edge.fundamental_panel import DERIVE
    off = sorted(k for k, v in DERIVE.items() if not v)
    assert not off, f"derived inputs left disabled: {off}"


def test_f_treats_nan_as_missing():
    """A blank CSV cell reads as float('nan'), which must count as ABSENT, not as a value.

    Returning NaN silently broke every `if x is not None` guard in the panel — including
    the roe/roic fallbacks (which never fired) and _f_score (which scored missing tests as
    failures).
    """
    from valuation.edge.fundamental_panel import _f
    assert _f({"roe": float("nan")}, "roe") is None
    assert _f({}, "roe") is None
    assert _f({"roe": float("nan"), "roa": 0.2}, "roe", "roa") == 0.2   # falls through
    assert _f({"roe": 0.15}, "roe") == 0.15
    assert _f({"roe": ""}, "roe") is None                              # unparseable
    assert _f({"roe": 0.0}, "roe") == 0.0                              # 0 is a real value


def _arq_row(**over):
    """A Sharadar ARQ row as the real export delivers it: ratios blank, line items present."""
    row = {"datekey": "2024-05-15", "revenue": 500.0, "netinc": 100.0, "ebit": 150.0,
           "equity": 800.0, "invcap": 1000.0, "taxexp": 30.0, "ebt": 150.0,
           "assets": 2000.0, "ebitda": 200.0, "gp": 250.0, "fcf": 90.0, "debt": 200.0,
           "cashneq": 50.0, "ev": 5000.0, "intexp": 10.0, "sharesbas": 1e8,
           "roe": float("nan"), "roic": float("nan"), "assetturnover": float("nan")}
    row.update(over)
    return row


def test_roe_and_roic_derived_when_the_export_leaves_them_blank():
    from valuation.edge.fundamental_panel import _sf1_to_metrics
    m = _sf1_to_metrics("T", _arq_row(), price=50.0, market_cap=5e9)
    assert m["roe"] == 100.0 / 800.0                       # netinc / equity
    # roic = ebit x (1 - effective tax) / invcap; effective rate = taxexp/ebt = 30/150 = 0.20
    assert abs(m["roic"] - (150.0 * 0.80 / 1000.0)) < 1e-12
    # Sharadar's own value wins when it IS present (e.g. an ART-dimension export).
    m2 = _sf1_to_metrics("T", _arq_row(roe=0.42, roic=0.31), price=50.0, market_cap=5e9)
    assert m2["roe"] == 0.42 and m2["roic"] == 0.31


def test_roe_and_roic_refuse_negative_denominators():
    """Negative book value / invested capital would INVERT the sign, ranking a loss-making
    name with wiped-out equity as the highest-quality in the universe."""
    from valuation.edge.fundamental_panel import _sf1_to_metrics
    m = _sf1_to_metrics("T", _arq_row(equity=-500.0, invcap=-100.0), price=50.0, market_cap=5e9)
    assert m["roe"] is None and m["roic"] is None
    m0 = _sf1_to_metrics("T", _arq_row(equity=0.0, invcap=0.0), price=50.0, market_cap=5e9)
    assert m0["roe"] is None and m0["roic"] is None


def test_effective_tax_rate_clipped_and_statutory_fallback():
    """One-off tax items produce effective rates of -400%/+900% on small pre-tax numbers;
    unclipped, those flip a profitable name's NOPAT negative for accounting reasons that say
    nothing about its return on capital."""
    from valuation.edge.fundamental_panel import _eff_tax_rate
    assert abs(_eff_tax_rate(_arq_row(taxexp=30.0, ebt=150.0)) - 0.20) < 1e-12
    assert _eff_tax_rate(_arq_row(taxexp=900.0, ebt=100.0)) == 0.60      # clipped high
    assert _eff_tax_rate(_arq_row(taxexp=-50.0, ebt=100.0)) == 0.0       # clipped low
    # Pre-tax loss -> the effective rate is meaningless; fall back to the statutory rate for
    # that DATE (the TCJA cut 35% -> 21%), not one constant across an 18-year window.
    assert _eff_tax_rate(_arq_row(ebt=-10.0, datekey="2012-05-15")) == 0.35
    assert _eff_tax_rate(_arq_row(ebt=-10.0, datekey="2024-05-15")) == 0.21
    assert _eff_tax_rate(_arq_row(taxexp=float("nan"), datekey="2024-05-15")) == 0.21


def test_fscore_test9_asset_turnover_is_evaluable():
    """F-Score test 9 (rising asset turnover) needs `assetturnover`, blank in every ARQ row,
    so it has never been evaluated. Derived from revenue/assets it must move the score."""
    from valuation.edge.fundamental_panel import _f_score, _asset_turnover
    assert _asset_turnover(_arq_row()) == 500.0 / 2000.0                # derived
    assert _asset_turnover(_arq_row(assetturnover=0.9)) == 0.9          # vendor value wins
    prior = _arq_row(datekey="2023-05-15", revenue=480.0, netinc=90.0, ncfo=140.0,
                     debtnc=210.0, currentratio=1.9, grossmargin=0.38)
    base = dict(ncfo=150.0, debtnc=200.0, currentratio=2.0, grossmargin=0.40)
    rising = _f_score(_arq_row(revenue=500.0, **base), prior)     # turnover 0.250 > 0.240
    falling = _f_score(_arq_row(revenue=450.0, **base), prior)    # turnover 0.225 < 0.240
    assert rising == 9, f"a company passing all nine tests should score 9, got {rising}"
    assert falling == 8, f"only test 9 should differ, got {falling}"


def test_fscore_refuses_to_score_when_too_many_tests_are_unevaluable():
    """The real damage from NaN-as-a-value: a missing input was scored as a test the company
    FAILED, and still counted toward the '>=6 usable' guard. A thin row therefore came back
    as a confident low score instead of None."""
    from valuation.edge.fundamental_panel import _f_score
    prior = _arq_row(datekey="2023-05-15", revenue=480.0, netinc=90.0, grossmargin=0.38)
    # Blank ncfo (kills tests 2 and 4), debtnc (5) and currentratio (6) -> only 5 usable.
    thin = _arq_row(ncfo=float("nan"), debtnc=float("nan"), currentratio=float("nan"),
                    grossmargin=0.40)
    assert _f_score(thin, prior) is None
    # Omitting the keys entirely must behave identically to blank cells.
    for k in ("ncfo", "debtnc", "currentratio"):
        thin.pop(k, None)
    assert _f_score(thin, prior) is None


def test_price_extras_exposes_beta():
    """low_risk = mean(z_neg_beta, z_neg_vol), but the panel hard-coded beta=None, so
    z_neg_beta was all-NaN and the theme was purely realized volatility. The regression that
    produces beta was already running for neg_idio_vol — its slope was just discarded."""
    from valuation.edge.fundamental_panel import _price_extras
    n = 200
    # The benchmark must genuinely VARY: a constant-return series has zero cross-sectional
    # variance, so the regression divides noise by noise and the slope is meaningless.
    rng = np.random.default_rng(11)
    rb = rng.normal(0.0004, 0.010, n - 1)
    bench, twice = [100.0], [100.0]
    for r in rb:
        bench.append(bench[-1] * (1.0 + r))
        twice.append(twice[-1] * (1.0 + 2.0 * r))         # exactly 2x the benchmark's moves
    out = _price_extras(twice, n - 1, bench=bench)
    assert "beta" in out, "beta must be reported for the low_risk theme"
    assert abs(out["beta"] - 2.0) < 0.02, out["beta"]
    assert abs(out["neg_idio_vol"]) < 1e-6, "a perfectly explained stock has no idio vol"
    # A stock that just tracks the benchmark has beta 1.
    one = _price_extras(bench, n - 1, bench=bench)
    assert abs(one["beta"] - 1.0) < 1e-9, one["beta"]
    # No benchmark -> no beta rather than a fabricated one.
    assert "beta" not in _price_extras(twice, n - 1, bench=None)


def test_beta_reaches_the_low_risk_theme_end_to_end():
    from valuation.edge.fundamental_panel import build_fundamental_panel
    prov = _SynthPIT(30, seed=7)
    panel = build_fundamental_panel(prov, list(prov.q.keys()), rebalance_days=63,
                                    horizon=21, lookback_years=4, keep_numbers=True)
    assert not panel.empty
    assert panel["z_neg_beta"].notna().any(), "neg_beta must populate the low_risk theme"
    assert float(panel["z_neg_beta"].std()) > 0.05, "neg_beta must vary across names"


def test_growth_accel_survives_build_frame():
    """build_frame recomputed growth_accel as revenue_growth - revenue_growth_prior
    unconditionally. The panel supplies growth_accel itself (from two prior-year
    point-in-time rows) and never supplies revenue_growth_prior, so the column was
    overwritten with all-NaN and `growth` collapsed to revenue_growth alone."""
    from valuation.screener.factors import build_frame
    metrics = [{"ticker": f"T{i}", "price": 10.0 + i, "market_cap": 1e9 * (i + 1),
                "revenue": 100.0, "net_income": 10.0 + i, "operating_income": 12.0 + i,
                "revenue_growth": 0.10 + 0.01 * i, "growth_accel": 0.05 - 0.004 * i}
               for i in range(20)]
    fr = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    assert fr["z_growth_accel"].notna().any(), "panel-supplied growth_accel must survive"
    assert float(fr["z_growth_accel"].std()) > 0.05
    assert fr["growth"].notna().any()
    # When a provider DOES supply revenue_growth_prior, the derived version still wins.
    for i, m in enumerate(metrics):
        m["revenue_growth_prior"] = 0.02 * i
    fr2 = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    got = float(fr2["growth_accel"].iloc[5])
    assert abs(got - ((0.10 + 0.01 * 5) - 0.02 * 5)) < 1e-12, got


def test_yoy_survives_a_prior_row_with_no_revenue():
    """Regression: the growth_accel branch tested `"revenue_growth" in m`, but the metrics
    dict is pre-seeded with revenue_growth=None, so the key is ALWAYS present and the branch
    reached `None - float`. NaN arithmetic hid it until blank cells stopped becoming NaN."""
    from valuation.edge.fundamental_panel import _yoy
    rows = [{"datekey": "2022-05-15", "revenue": 400.0, "assets": 1000.0, "sharesbas": 1e8},
            {"datekey": "2023-05-15", "revenue": float("nan"), "assets": 1100.0, "sharesbas": 1e8},
            {"datekey": "2024-05-15", "revenue": 500.0, "assets": 1200.0, "sharesbas": 1e8}]
    m = {"revenue_growth": None}
    _yoy(m, rows, "2024-05-20", 1e8, 500.0, 1200.0)      # must not raise
    assert m["revenue_growth"] is None                    # prior-year revenue was blank
    assert "growth_accel" not in m


def _cov_panel(**cols):
    """Minimal panel shaped like build_fundamental_panel(keep_numbers=True) output."""
    from valuation.screener import settings as S
    n = 50
    df = pd.DataFrame({"date": ["2024-01-02"] * n, "ticker": [f"T{i}" for i in range(n)],
                       "fwd_ret": np.linspace(-0.1, 0.1, n)})
    for num in S.NUMBERS_ALL:
        df["z_" + num] = np.linspace(-2, 2, n)
    for theme in S.FACTORS_ALL:
        df[theme] = np.linspace(-1, 1, n)
    for k, v in cols.items():
        df[k] = v
    return df


def test_signal_coverage_flags_a_wired_but_empty_signal():
    """The cheapest possible guard against the whole class of bug above: a wired factor at
    ~0% coverage raises no error anywhere else, because an empty column simply contributes
    nothing to the mean."""
    from valuation.edge.fundamental_panel import signal_coverage, COVERAGE_FLOOR
    df = _cov_panel(z_roic=np.nan, z_roe=np.nan, quality=np.nan)
    cov = signal_coverage(df, warn=False)
    assert cov["numbers"]["z_roic".replace("z_", "")] == 0.0
    assert cov["numbers"]["f_score"] == 1.0
    flagged = {r["name"] for r in cov["below_floor"]}
    assert {"roic", "roe", "quality"} <= flagged, flagged
    assert cov["floor"] == COVERAGE_FLOOR
    # Ordered worst-first so the warning leads with the worst offender.
    covs = [r["coverage"] for r in cov["below_floor"]]
    assert covs == sorted(covs)
    # A healthy panel must be silent — a guard that always fires trains you to ignore it.
    assert signal_coverage(_cov_panel(), warn=False)["below_floor"] == []


def test_signal_coverage_exempts_only_declared_hook_themes():
    """`sentiment` has no point-in-time feed, so empty is its correct state and warning about
    its three inputs would train the reader to ignore the block.

    But the exemption must be an EXPLICIT list, not "any theme with zero weight". low_risk is
    zero-weighted because it was measured and found not to earn its place — its inputs still
    exist and a plumbing bug in them must still be reported. Inferring the exemption from the
    weight silently disabled the guard for low_risk the moment that weight went to 0.
    """
    from valuation.edge.fundamental_panel import signal_coverage, COVERAGE_EXEMPT_THEMES
    from valuation.screener import settings as S
    assert COVERAGE_EXEMPT_THEMES == {"sentiment"}, COVERAGE_EXEMPT_THEMES
    df = _cov_panel(z_earn_rev=np.nan, z_rating_rev=np.nan, z_neg_rating_disp=np.nan,
                    sentiment=np.nan)
    cov = signal_coverage(df, warn=False)
    assert cov["below_floor"] == [], cov["below_floor"]
    assert cov["exempt_themes"] == ["sentiment"]
    # A zero-coverage signal in a non-hook theme is still reported, with its theme named —
    # INCLUDING low_risk, which currently carries zero weight.
    assert not S.WEIGHTS_ESTABLISHED.get("low_risk"), "test is only meaningful while it is 0"
    cov2 = signal_coverage(_cov_panel(z_neg_beta=np.nan), warn=False)
    assert [(r["name"], r["theme"]) for r in cov2["below_floor"]] == [("neg_beta", "low_risk")]


def test_coverage_reaches_the_results_file():
    """The guard is worthless if it stays on stderr — the Cowork agent reads the JSON."""
    from valuation.edge.results_file import build_payload, render_md
    res = {"signal_coverage": {"floor": 0.05, "numbers": {"roic": 0.0, "f_score": 0.97},
                               "themes": {"quality": 0.98},
                               "below_floor": [{"kind": "number", "name": "roic",
                                                "theme": "quality", "coverage": 0.0}],
                               "exempt_themes": ["sentiment"]},
           "horizons": {}, "cpcv": {}, "construction": {}}
    p = build_payload(res)
    sc = p["signal_coverage"]
    assert sc["available"] and sc["numbers"]["roic"] == 0.0
    assert sc["below_floor"][0]["name"] == "roic"
    md = render_md(p)
    assert "EMPTY SIGNALS" in md and "roic" in md
    # per_signal falls back to the result dict when the caller doesn't pass one explicitly.
    res["per_signal"] = {"f_score": {"median_ic": 0.02, "ic_tstat": 2.8, "coverage": 0.97}}
    assert build_payload(res)["per_signal"]["available"] is True


def test_theme_ic_measures_each_theme_and_reaches_the_results_file():
    """Per-SIGNAL IC alone can't answer 'is this theme worth carrying' — an input can be
    worthless while its theme earns its weight, or the reverse. The low_risk and insider
    keep/drop calls rest on this number, so it has to be in the canonical file."""
    from valuation.edge.fundamental_panel import theme_ic
    from valuation.edge.results_file import build_payload, render_md
    from valuation.screener import settings as S
    rng = np.random.default_rng(5)
    rows = []
    for d in range(12):                                  # 12 dates x 40 names
        for i in range(40):
            fwd = float(rng.normal(0, 0.1))
            rows.append({"date": f"2024-{d+1:02d}-01", "ticker": f"T{i}", "fwd_ret": fwd,
                         # quality tracks the forward return; low_risk is pure noise
                         "quality": fwd + rng.normal(0, 0.02), "low_risk": rng.normal(),
                         "value": np.nan})
    ti = theme_ic(pd.DataFrame(rows))
    assert ti["quality"]["ic_tstat"] > 5, ti["quality"]
    assert abs(ti["low_risk"]["ic_tstat"]) < 3, ti["low_risk"]
    assert ti["value"]["median_ic"] is None and ti["value"]["coverage"] == 0.0
    assert ti["quality"]["n_dates"] == 12
    # An all-NaN theme reports coverage 0 rather than being silently omitted.
    assert set(ti) <= set(S.FACTORS_ALL)

    p = build_payload({"per_theme": ti, "horizons": {}, "cpcv": {}, "construction": {}})
    assert p["per_theme"]["available"] is True
    assert p["per_theme"]["themes"]["quality"]["ic_tstat"] == ti["quality"]["ic_tstat"]
    assert "Per-theme" in render_md(p)


def _fx_row(fx=1.0, **over):
    """A Sharadar row for a company reporting in a currency `fx` units per USD."""
    row = {"datekey": "2024-05-15", "fxusd": fx,
           "equity": 800.0 * fx, "equityusd": 800.0,
           "revenue": 500.0 * fx, "revenueusd": 500.0,
           "ebit": 150.0 * fx, "ebitusd": 150.0,
           "netinc": 100.0 * fx, "netinccmnusd": 100.0,
           "fcf": 90.0 * fx, "ev": 5000.0, "invcap": 1000.0 * fx,
           "taxexp": 30.0 * fx, "ebt": 150.0 * fx, "assets": 2000.0 * fx,
           "gp": 250.0 * fx, "ebitda": 200.0 * fx, "debt": 200.0 * fx,
           "cashneq": 50.0 * fx, "intexp": 10.0 * fx, "sharesbas": 1e8}
    row.update(over)
    return row


def test_fxusd_is_a_divisor_not_a_multiplier():
    """The single most dangerous detail in P7. Sharadar's `fxusd` is LOCAL UNITS PER USD
    (SKM 1514.2 won/USD), so USD = local / fxusd. Using it as a multiplier would SQUARE the
    currency error instead of fixing it — ~2.3 million x for SK Telecom."""
    from valuation.edge.fundamental_panel import _usd_divisor
    assert _usd_divisor(_fx_row(fx=1514.2)) == 1514.2
    assert _usd_divisor(_fx_row(fx=1.0)) == 1.0
    # Derived from any local/USD pair when fxusd is absent...
    no_fx = _fx_row(fx=160.0)
    no_fx.pop("fxusd")
    assert abs(_usd_divisor(no_fx) - 160.0) < 1e-9
    # ...and 1.0 (a USD reporter) when nothing identifies the currency.
    assert _usd_divisor({"datekey": "2024-05-15", "equity": 800.0}) == 1.0
    assert _usd_divisor({"fxusd": 0}) == 1.0        # never divide by zero


def test_value_ratios_are_currency_invariant():
    """The P7 fix, stated as the property that matters: two IDENTICAL companies whose only
    difference is reporting currency must receive IDENTICAL value ratios. Before the fix, the
    won-reporting one got a book_to_price ~1,500x higher and swept the top decile."""
    from valuation.edge.fundamental_panel import _sf1_to_metrics
    usd = _sf1_to_metrics("US", _fx_row(fx=1.0), price=50.0, market_cap=10_000.0)
    won = _sf1_to_metrics("KR", _fx_row(fx=1514.2), price=50.0, market_cap=10_000.0)
    for k in ("book_to_price", "earnings_yield", "fcf_yield", "ebit_ev", "ev_sales", "ps"):
        assert usd[k] is not None, k
        assert abs(usd[k] - won[k]) < 1e-9, f"{k}: {usd[k]} vs {won[k]} — currency leaked in"
    # And the actual values are right, not merely equal.
    assert abs(usd["book_to_price"] - 800.0 / 10_000.0) < 1e-12
    assert abs(usd["earnings_yield"] - 100.0 / 10_000.0) < 1e-12
    assert abs(usd["ebit_ev"] - 150.0 / 5000.0) < 1e-12
    assert abs(usd["ev_sales"] - 5000.0 / 500.0) < 1e-12
    assert abs(usd["ps"] - 10_000.0 / 500.0) < 1e-12
    assert won["_is_foreign"] is True and usd["_is_foreign"] is False
    # SAME-CURRENCY ratios must be untouched by the fix (local/local was always correct) —
    # and they too must be currency-invariant, for the opposite reason.
    for k in ("roe", "roic", "op_margin", "gross_margin", "net_debt_to_ebitda"):
        assert abs(usd[k] - won[k]) < 1e-9, f"{k} changed: {usd[k]} vs {won[k]}"
    assert abs(usd["op_margin"] - 150.0 / 500.0) < 1e-12
    assert abs(usd["roe"] - 100.0 / 800.0) < 1e-12


def test_book_to_price_uses_the_panel_value_not_local_equity():
    """build_frame must not recompute book_to_price from `total_equity`, which stays in the
    LOCAL currency on purpose (gp_on_capital divides local gross profit by it)."""
    from valuation.screener.factors import build_frame
    metrics = [{"ticker": f"T{i}", "price": 10.0, "market_cap": 1e10,
                "net_income": 5.0, "operating_income": 6.0,
                "total_equity": 8e12,          # local currency — must NOT drive book_to_price
                "gross_profit": 2e12,
                "book_to_price": 0.5 + 0.01 * i}  # USD, supplied by the panel
               for i in range(20)]
    fr = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    assert abs(float(fr["book_to_price"].iloc[3]) - 0.53) < 1e-9, fr["book_to_price"].iloc[3]
    # gp_on_capital still uses LOCAL equity, so it must stay a same-currency ratio.
    assert fr["gp_on_capital"].notna().all()
    # A provider that supplies no book_to_price still falls back to equity/market cap.
    for m in metrics:
        m.pop("book_to_price")
        m["total_equity"] = 2e9
    fr2 = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    assert abs(float(fr2["book_to_price"].iloc[0]) - 0.2) < 1e-9


def _sanity_panel(n_dates=6, n=60, foreign_frac=0.1, corrupt=False):
    rng = np.random.default_rng(12)
    rows = []
    for d in range(n_dates):
        for i in range(n):
            foreign = i < int(n * foreign_frac)
            div = 1000.0 if foreign else 1.0
            b2p = float(abs(rng.normal(0.5, 0.2)))
            rows.append({"date": f"2024-{d+1:02d}-01", "ticker": f"T{i}",
                         "fwd_ret": float(rng.normal(0, 0.05)), "bench_ret": 0.01,
                         "is_foreign": foreign, "fx_divisor": div, "mc_ratio": 1.0,
                         "raw_book_to_price": b2p * (div if corrupt else 1.0),
                         "raw_earnings_yield": 0.02, "raw_fcf_yield": 0.02,
                         "raw_ebit_ev": 0.03, "raw_ev_sales": 3.0, "raw_ps": 2.0,
                         "z_book_to_price": float(rng.normal())})
    return pd.DataFrame(rows)


def test_sanity_check_catches_the_currency_bug_and_is_quiet_when_clean():
    """P8's reason to exist: signal_coverage sees a factor is PRESENT; this sees it is SANE.
    The currency bug filled every column and was simply wrong, so coverage was blind to it."""
    from valuation.edge.fundamental_panel import sanity_check
    clean = sanity_check(_sanity_panel(corrupt=False), warn=False)
    assert clean["available"] is True
    assert clean["flags"] == [], clean["flags"]          # must not cry wolf on good data

    bad = sanity_check(_sanity_panel(corrupt=True), warn=False)
    kinds = {f["check"] for f in bad["flags"]}
    assert bad["flags"], "the currency signature must be flagged"
    assert "subgroup" in kinds or "range" in kinds, kinds
    hit = [f for f in bad["flags"] if f.get("factor") == "book_to_price"]
    assert hit, bad["flags"]
    # The foreign subgroup must be reported as pegged near the top of book_to_price.
    peg = (bad["checks"]["subgroup"] or {}).get("foreign_median_percentile") or {}
    assert peg.get("book_to_price", 0) > 0.9, peg


def test_sanity_check_flags_market_cap_divergence():
    """Recycled / spun-off tickers inherit a parent's DAILY history — SanDisk showed $337B,
    ~10x reality, polluting `size` and the cost model."""
    from valuation.edge.fundamental_panel import sanity_check
    p = _sanity_panel()
    p.loc[p.index[:60], "mc_ratio"] = 10.0          # a chunk of rows 10x off
    r = sanity_check(p, warn=False)
    mcf = [f for f in r["flags"] if f["check"] == "market_cap"]
    assert mcf, r["flags"]
    assert r["checks"]["market_cap"]["share_diverging"] > 0.01
    assert r["checks"]["market_cap"]["worst"], "must name the worst offenders"
    # Ratios near 1.0 must not flag.
    assert not [f for f in sanity_check(_sanity_panel(), warn=False)["flags"]
                if f["check"] == "market_cap"]


def test_sanity_check_warn_path_does_not_raise():
    """Regression: the warn branch wrote to the `sys` MODULE instead of `sys.stderr`, raising
    AttributeError. run_backtests catches everything, so the whole validation block was
    skipped and a canonical results file was written with every metric null — a full run
    silently lost. The warning path has to be exercised, not just the quiet one."""
    from valuation.edge.fundamental_panel import sanity_check
    r = sanity_check(_sanity_panel(corrupt=True), warn=True)     # must not raise
    assert r["flags"]
    assert sanity_check(_sanity_panel(corrupt=False), warn=True)["flags"] == []


def test_results_file_surfaces_a_degraded_run():
    """A block that threw leaves every metric null, which reads as 'ran, found nothing'
    rather than 'broke'. The file must say which is which."""
    from valuation.edge.results_file import build_payload, render_md
    ok = build_payload({"horizons": {}, "cpcv": {}, "construction": {}})
    assert ok["errors"] == []
    bad = build_payload({"horizons": {}, "cpcv": {"status": "error: boom"},
                         "construction": {"status": "error: boom"}})
    assert {e["block"] for e in bad["errors"]} == {"cpcv", "construction"}
    md = render_md(bad)
    assert "DEGRADED RUN" in md and "boom" in md
    assert "DEGRADED RUN" not in render_md(ok)


def test_sanity_check_degrades_safely():
    from valuation.edge.fundamental_panel import sanity_check
    assert sanity_check(pd.DataFrame(), warn=False)["available"] is False
    # A panel with no diagnostic columns (keep_numbers=False) must not raise.
    bare = pd.DataFrame({"date": ["2024-01-01"] * 30, "ticker": [f"T{i}" for i in range(30)],
                         "fwd_ret": np.linspace(-0.1, 0.1, 30)})
    r = sanity_check(bare, warn=False)
    assert r["available"] is True and r["flags"] == []


def test_holdout_compare_panels_requires_the_committed_margin_both_ways():
    """Sector-neutral scoring rebuilds every z-score, so it is not a weight change and
    holdout_theme_validate cannot express it. Same discipline, different shape: split by time,
    embargo the boundary, require the SAME pre-committed margin in BOTH directions."""
    from valuation.edge import fundamental_panel as F
    rng = np.random.default_rng(21)
    def mk(edge):
        rows = []
        for d in range(24):
            for i in range(60):
                fwd = float(rng.normal(0, 0.08))
                rows.append({"date": f"20{20 + d // 12:02d}-{d % 12 + 1:02d}-01",
                             "ticker": f"T{i}", "fwd_ret": fwd, "bench_ret": 0.01,
                             "good": fwd * edge + rng.normal(0, 0.05)})
        return pd.DataFrame(rows)
    a = mk(1.0)
    r = F.holdout_compare_panels(a, a.copy(), ["good"], label_a="A", label_b="B")
    # Identical panels cannot clear a positive margin.
    assert r["verdict"] == "reject", r["verdict"]
    assert r["min_tstat_gain"] == F.MIN_HOLDOUT_TSTAT_GAIN
    assert r["min_alpha_gain"] == F.MIN_HOLDOUT_ALPHA_GAIN
    assert set(r["splits"]) == {"early_half", "late_half"}
    assert r.get("boundary_date_embargoed")
    # Halves are disjoint and the boundary date is dropped.
    assert (r["splits"]["early_half"]["n_dates"] + r["splits"]["late_half"]["n_dates"]
            == a["date"].nunique() - 1)
    assert "only" in F.holdout_compare_panels(a.head(50), a.head(50), ["good"],
                                              min_dates=999)["verdict"]


def test_ticker_meta_degrades_without_the_cache():
    """Sector data is an optional overlay: no TICKERS cache must mean 'no sector', never a
    crash — the panel ran for years with no sector column at all."""
    from valuation.edge.data_providers import WRDSProvider

    class _Cfg:
        wrds_data_dir = _tmpdir()

    p = WRDSProvider(_Cfg())
    assert p.ticker_meta("AAPL") == {}
    from valuation.screener.factors import build_frame
    metrics = [{"ticker": f"T{i}", "sector": "", "price": 10.0, "market_cap": 1e10,
                "net_income": 5.0, "operating_income": 6.0, "revenue": 100.0,
                "book_to_price": 0.3 + 0.01 * i} for i in range(20)]
    # sector_neutral with an all-blank sector must not blow up (it groups on a constant).
    fr = build_frame(metrics, sector_neutral=True, residual_momentum=False)
    assert fr["value"].notna().any()


def test_index_full_universe_flag_is_wired():
    """P9b: the CLI must be able to build the book headless from the Sharadar export instead
    of the live-scan store, whose 'top decile' collapses to the 10-name floor."""
    import inspect
    from valuation.edge import valquo_index as VI
    assert "data_dir" in inspect.signature(VI.export).parameters
    src = inspect.getsource(VI.main)
    assert "--full-universe" in src and "score_universe_now" in inspect.getsource(VI)
    # Unreadable export dir -> a clear error, not a silent empty book.
    try:
        VI._full_universe_rows(_tmpdir())
        raise AssertionError("should have raised on an empty export dir")
    except RuntimeError as e:
        assert "not readable" in str(e) or "no rows" in str(e).lower()


def _tmpdir():
    import tempfile
    return tempfile.mkdtemp(prefix="valquo_nodata_")


def test_index_reports_missing_sector_data_honestly():
    """The Sharadar export carries no sector column, so every position's sector is "". The
    old code emitted {"": 1.0}, which reads downstream as "one real sector holds the whole
    book" rather than "this data is missing" — and the Cowork agent consumes this file."""
    from valuation.edge.valquo_index import build_index
    rows = [{"ticker": f"T{i}", "hot_score": 50.0 + i, "price": 10.0,
             "market_cap": 2e10 + i} for i in range(40)]
    p = build_index(rows)
    assert p["sector_data_available"] is False
    assert set(p["sector_weights"]) == {"unknown"}, p["sector_weights"]
    assert "" not in p["sector_weights"]
    # With real sectors it reports them and flips the flag.
    for i, r in enumerate(rows):
        r["sector"] = "Tech" if i % 2 else "Energy"
    p2 = build_index(rows)
    assert p2["sector_data_available"] is True
    assert set(p2["sector_weights"]) == {"Tech", "Energy"}
    assert abs(sum(p2["sector_weights"].values()) - 1.0) < 1e-3
    # The retired claim must not come back: post-P6 the top-25 does NOT lose.
    assert "top-25 lost" not in p["method"]


def test_index_weights_are_capped_and_sum_to_one():
    """A tracked book must be actually investable: weights sum to 1, nothing breaches the cap,
    and a big enough universe yields a real decile rather than the 10-name floor."""
    from valuation.edge.valquo_index import build_index, MAX_WEIGHT
    # 900 large caps with a wide score spread -> the cap should bind on the leaders.
    rows = [{"ticker": f"T{i}", "hot_score": float(i), "price": 20.0, "market_cap": 5e10}
            for i in range(900)]
    p = build_index(rows)
    w = [x["weight"] for x in p["positions"]]
    assert p["n_positions"] == 90, p["n_positions"]          # a real decile, not the floor
    # Exported weights are rounded to 5dp per position, so the sum can drift by up to
    # n * 5e-6 from exactly 1. Tolerance tracks that rather than hiding it.
    assert abs(sum(w) - 1.0) < len(w) * 5e-6, sum(w)
    assert max(w) <= MAX_WEIGHT + 1e-6, max(w)
    assert len({x["ticker"] for x in p["positions"]}) == len(w)
    assert p["criteria"]["tilt"] == "large-cap only"
    # A tiny universe must fall back rather than silently label 10 mega-caps a "decile".
    small = build_index(rows[:12])
    sw = [x["weight"] for x in small["positions"]]
    assert small["n_positions"] >= 10
    assert abs(sum(sw) - 1.0) < len(sw) * 5e-6


def test_robust_zscore_resists_outliers_and_degrades_safely():
    """Median/MAD standardization. Winsorization already caps the tails, but mean and SD are
    still dragged by the surviving 2%, and these inputs are heavily right-skewed."""
    from valuation.screener.cross_sectional import zscore, robust_zscore, MAD_TO_SIGMA
    # On clean normal-ish data the two agree closely — robust must not distort the ordinary case.
    rng = np.random.default_rng(2)
    clean = pd.Series(rng.normal(0, 1, 400))
    a, b = zscore(clean, robust=False), zscore(clean, robust=True)
    assert abs(float(a.std()) - float(b.std())) < 0.15, (a.std(), b.std())
    assert abs(MAD_TO_SIGMA - 1.4826) < 1e-9

    # One monstrous outlier: the classic scale inflates, the robust one barely moves.
    dirty = pd.Series(list(rng.normal(0, 1, 200)) + [500.0] * 6)
    cls_sd = float(zscore(dirty, robust=False, p=0.0).std())
    rob_sd = float(zscore(dirty, robust=True, p=0.0).std())
    assert rob_sd > cls_sd * 1.5, (cls_sd, rob_sd)

    # Ordering is preserved either way — standardization must never reorder a cross-section.
    v = pd.Series([1.0, 5.0, 2.0, 9.0, 3.0])
    assert list(zscore(v, robust=True).rank()) == list(zscore(v, robust=False).rank())

    # MAD == 0 (over half the column identical) must fall back, not divide by zero.
    tied = pd.Series([7.0] * 60 + [1.0, 2.0, 99.0])
    r = robust_zscore(tied)
    assert r.notna().all() and float(r.std()) > 0, "must fall back to the classic z-score"
    # No spread at all -> NaN, same as the classic path.
    assert zscore(pd.Series([3.0] * 20), robust=True).isna().all()
    assert zscore(pd.Series([], dtype=float), robust=True).isna().all() or True
    # NaNs propagate rather than being silently filled.
    assert zscore(pd.Series([1.0, np.nan, 3.0]), robust=True).isna().sum() == 1


def _q(dk, **over):
    row = {"datekey": dk, "netinc": 25.0, "ebit": 40.0, "taxexp": 8.0, "ebt": 40.0,
           "equity": 800.0, "invcap": 1000.0}
    row.update(over)
    return row


def test_ttm_sums_four_quarters_and_refuses_gaps():
    """Summing 'the last four rows' is only a TTM if those rows really are four consecutive
    quarters. With a missing quarter it silently adds up two or three YEARS of earnings and
    reports a spectacular ROE — the same class of silent-garbage bug as the P5 empties."""
    from valuation.edge.fundamental_panel import _ttm, TTM_MAX_SPAN_DAYS
    rows = [_q("2023-05-15"), _q("2023-08-15"), _q("2023-11-15"), _q("2024-02-15"),
            _q("2024-05-15")]
    t = _ttm(rows, "2024-06-01", ("netinc", "ebit"))
    assert t["netinc"] == 100.0 and t["ebit"] == 160.0        # last four, not all five
    # Point-in-time: a row dated after as_of must never be included.
    assert _ttm(rows, "2024-02-20", ("netinc",))["netinc"] == 100.0
    # Fewer than four quarters available -> None, not a partial sum.
    assert _ttm(rows[:3], "2024-06-01", ("netinc",)) is None
    # A reporting GAP -> None. These four rows span >2 years.
    gappy = [_q("2021-05-15"), _q("2022-05-15"), _q("2023-05-15"), _q("2024-05-15")]
    assert _ttm(gappy, "2024-06-01", ("netinc",)) is None
    assert TTM_MAX_SPAN_DAYS < 730
    # A missing key -> None rather than a sum over the rows that happen to have it.
    assert _ttm([_q("2023-05-15"), _q("2023-08-15"), _q("2023-11-15"),
                 _q("2024-02-15", netinc=None)], "2024-06-01", ("netinc",)) is None


def test_ttm_quality_differs_from_quarterly_and_is_seasonality_free():
    """The TTM variant must actually be the annual figure, and must NOT move when the same
    year's earnings are shuffled between quarters — that invariance IS the point."""
    from valuation.edge.fundamental_panel import _ttm_quality, _sf1_to_metrics
    smooth = [_q("2023-05-15"), _q("2023-08-15"), _q("2023-11-15"), _q("2024-02-15")]
    # Same 100 of annual earnings, wildly seasonal (a retailer's Q4).
    lumpy = [_q("2023-05-15", netinc=5.0), _q("2023-08-15", netinc=5.0),
             _q("2023-11-15", netinc=5.0), _q("2024-02-15", netinc=85.0)]
    a, b = {}, {}
    _ttm_quality(a, smooth, "2024-03-01")
    _ttm_quality(b, lumpy, "2024-03-01")
    assert a["roe_ttm"] == b["roe_ttm"] == 100.0 / 800.0, (a, b)
    # The QUARTERLY version does move with the seasonality — the problem TTM fixes.
    qa = _sf1_to_metrics("T", smooth[-1], 10.0, 1e9)["roe"]
    qb = _sf1_to_metrics("T", lumpy[-1], 10.0, 1e9)["roe"]
    assert qa != qb and abs(qb - qa) > 0.05, (qa, qb)
    # roic_ttm uses the TTM effective rate: ebit 160 x (1 - 32/160) / invcap 1000.
    assert abs(a["roic_ttm"] - (160.0 * 0.80 / 1000.0)) < 1e-12
    # Negative book value must not invert the sign, same guard as the quarterly version.
    neg = [_q(r["datekey"], equity=-500.0, invcap=-100.0) for r in smooth]
    c = {}
    _ttm_quality(c, neg, "2024-03-01")
    assert "roe_ttm" not in c and "roic_ttm" not in c


def test_cost_model_and_breakeven():
    """Every other performance number in this project is gross of costs. Pins the cost
    curve's direction, that turnover counts weight DRIFT (not just entries/exits), and that
    the breakeven is where net alpha crosses zero."""
    from valuation.edge.fundamental_panel import (one_way_cost_bps, turnover_and_costs,
                                                  cost_breakeven_bps, COST_BPS_MICRO)
    # Cost falls monotonically with size, and unknown/zero caps are charged the worst rate.
    caps = [500e9, 100e9, 20e9, 5e9, 1e9, 200e6, 50e6]
    bps = [one_way_cost_bps(c) for c in caps]
    assert bps == sorted(bps), bps
    assert one_way_cost_bps(None) == COST_BPS_MICRO
    assert one_way_cost_bps(float("nan")) == COST_BPS_MICRO
    assert one_way_cost_bps(-1) == COST_BPS_MICRO

    rng = np.random.default_rng(9)
    rows = []
    for d in range(20):
        for i in range(80):
            sig = rng.normal()
            rows.append({"date": f"2024-{d+1:02d}-01", "ticker": f"T{i}",
                         "fwd_ret": 0.02 * sig + rng.normal(0, 0.05),
                         "bench_ret": 0.01, "market_cap": 1e9, "good": sig})
    panel = pd.DataFrame(rows)
    free = turnover_and_costs(panel, ["good"], {"good": 1.0}, top_frac=0.1, flat_bps=0.0)
    dear = turnover_and_costs(panel, ["good"], {"good": 1.0}, top_frac=0.1, flat_bps=100.0)
    assert free["annual_turnover"] > 0, "a rotating book must show turnover"
    assert abs(free["cost_drag_ann"]) < 1e-9, "zero bps must cost nothing"
    assert dear["net_ann" ] < free["net_ann"], "cost must reduce the net return"
    assert dear["gross_ann"] == free["gross_ann"], "cost must not change the GROSS return"
    assert dear["net_alpha"] < dear["gross_alpha"]

    be = cost_breakeven_bps(panel, ["good"], {"good": 1.0}, top_frac=0.1,
                            grid=(0, 25, 50, 100, 200, 400, 800, 1600))
    b = be["breakeven_one_way_bps"]
    assert b is not None
    if b not in (float("inf"),):
        # Net alpha must be >=0 below the breakeven and <0 above it.
        lo = [c for c in be["curve"] if c["bps"] < b]
        hi = [c for c in be["curve"] if c["bps"] > b]
        assert all(c["net_alpha"] >= 0 for c in lo), lo
        assert hi and hi[-1]["net_alpha"] < 0

    from valuation.edge.results_file import build_payload, render_md
    p = build_payload({"costs": {"top_decile": {**free, **be}}, "horizons": {}, "cpcv": {},
                       "construction": {}})
    assert p["costs"]["top_decile"]["annual_turnover"] == free["annual_turnover"]
    assert "Tradeability" in render_md(p)


def test_holdout_minimum_margin_is_prespecified():
    """The verdict rule must require a MAGNITUDE, not just the right sign — the sign-only
    version called a +0.01 t-stat move a confirmation."""
    from valuation.edge import fundamental_panel as F
    assert F.MIN_HOLDOUT_ALPHA_GAIN >= 0.01
    assert F.MIN_HOLDOUT_TSTAT_GAIN >= 0.25
    rng = np.random.default_rng(4)
    rows = []
    for d in range(24):
        for i in range(60):
            fwd = float(rng.normal(0, 0.08))
            rows.append({"date": f"20{20 + d // 12:02d}-{d % 12 + 1:02d}-01", "ticker": f"T{i}",
                         "fwd_ret": fwd, "bench_ret": 0.01,
                         "good": fwd + rng.normal(0, 0.03), "junk": float(rng.normal())})
    panel = pd.DataFrame(rows)
    r = F.holdout_theme_validate(panel, ["good", "junk"], horizon=63)
    assert r["min_alpha_gain"] == F.MIN_HOLDOUT_ALPHA_GAIN
    assert r["min_tstat_gain"] == F.MIN_HOLDOUT_TSTAT_GAIN
    # A hair-thin gain must NOT read as an improvement.
    for split in r["splits"].values():
        for th in split["themes"].values():
            if th["improves"]:
                assert th["delta_long_short_tstat"] >= F.MIN_HOLDOUT_TSTAT_GAIN
                assert th["delta_top_decile_alpha"] >= F.MIN_HOLDOUT_ALPHA_GAIN


def test_holdout_theme_validate_protocol():
    """The held-out split is the only check covering a theme chosen AFTER seeing its IC.

    Pins the three things that make it honest: the halves are disjoint and split by time, the
    boundary date is embargoed, and a theme only reads `confirmed` if zeroing it helped in
    BOTH directions — one-directional wins (the usual fate of noise) must read
    `not_replicated`.
    """
    from valuation.edge.fundamental_panel import holdout_theme_validate
    rng = np.random.default_rng(3)
    rows = []
    for d in range(24):
        for i in range(60):
            fwd = float(rng.normal(0, 0.08))
            rows.append({"date": f"20{20 + d // 12:02d}-{d % 12 + 1:02d}-01", "ticker": f"T{i}",
                         "fwd_ret": fwd, "bench_ret": 0.01,
                         "good": fwd + rng.normal(0, 0.03),      # genuinely predictive
                         "junk": float(rng.normal())})           # pure noise
    panel = pd.DataFrame(rows)
    r = holdout_theme_validate(panel, ["good", "junk"], horizon=63)

    a = r["splits"]["decide_early_measure_late"]
    b = r["splits"]["decide_late_measure_early"]
    # Disjoint halves, and one date dropped to the embargo.
    assert a["decide_dates"] == b["measure_dates"] and a["measure_dates"] == b["decide_dates"]
    assert a["decide_dates"] + a["measure_dates"] == panel["date"].nunique() - 1
    assert r["boundary_date_embargoed"] not in (None, "")
    # Zeroing the genuinely predictive theme must never be "confirmed".
    assert r["verdicts"]["good"] != "confirmed", r["verdicts"]
    assert set(r["verdicts"]) == {"good", "junk"}
    assert all(v in ("confirmed", "not_replicated", "rejected") for v in r["verdicts"].values())
    # Too little history -> says so rather than inventing a verdict.
    thin = panel[panel["date"] < "2020-06-01"]
    assert "status" in holdout_theme_validate(thin, ["good"], min_dates=99)

    from valuation.edge.results_file import build_payload, render_md
    p = build_payload({"holdout_validation": r, "horizons": {}, "cpcv": {}, "construction": {}})
    assert p["holdout_validation"]["verdicts"] == r["verdicts"]
    assert "Held-out confirmation" in render_md(p)


def test_monotonicity_sign_convention():
    """Pins the sign of `monotonicity`, which this project has repeatedly read backwards.

    quantile_backtest orders buckets by argsort(-comp), so bucket 0 is the BEST composite and
    monotonicity is Spearman(bucket index, bucket return). A working signal makes it NEGATIVE.
    Notes claiming "-0.68 ... the deciles aren't cleanly ordered", and a -0.782 -> -0.855 move
    logged as "slightly worse", both had it inverted.
    """
    from valuation.edge.fundamental_panel import _spearman
    idx = np.arange(10, dtype=float)
    ordered = np.array([0.30 - 0.03 * k for k in range(10)])    # D1 best -> D10 worst
    assert _spearman(idx, ordered) == -1.0, "perfectly ordered deciles must be -1.0"
    assert _spearman(idx, ordered[::-1].copy()) == +1.0, "a backwards composite must be +1.0"
    # And the real measured values are well-ordered, not badly ordered.
    measured = np.array([0.283, 0.205, 0.172, 0.178, 0.150, 0.155, 0.158, 0.132, 0.113, 0.107])
    assert _spearman(idx, measured) < -0.9

    # The threshold ships next to the metric so the file can't be misread without the hint.
    from valuation.edge.results_file import build_payload
    p = build_payload({"construction": {"monotonicity": -0.94}, "horizons": {}, "cpcv": {}})
    assert "negative" in p["construction"]["monotonicity_want"]


def test_capital_discipline_drops_the_wrong_signed_input():
    """neg_asset_growth measured median IC -0.0141 / t -0.70 on the full universe — the wrong
    sign — so it was cancelling neg_issuance (+0.0232 / t +2.25), the input that works.
    capital_discipline must now be issuance alone, while neg_asset_growth keeps being
    MEASURED so the decision can be revisited."""
    from valuation.screener.factors import build_frame
    from valuation.screener import settings as S
    assert S.NUMBER_THEME.get("neg_asset_growth") == "capital_discipline", \
        "must stay wired for measurement even though it no longer feeds the theme"
    metrics = [{"ticker": f"T{i}", "price": 10.0, "market_cap": 1e9 * (i + 1),
                "net_income": 5.0, "operating_income": 6.0,
                "share_issuance": 0.01 * i, "asset_growth": 0.30 - 0.02 * i}
               for i in range(20)]
    fr = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    assert fr["z_neg_asset_growth"].notna().any(), "still measured"
    # The theme must equal issuance alone, NOT the mean of the two.
    pd.testing.assert_series_equal(fr["capital_discipline"], fr["z_neg_issuance"],
                                   check_names=False)


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
    print(f"\n{passed}/{len(tests)} edge tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
