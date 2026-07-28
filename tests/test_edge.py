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
        rng = np.random.default_rng(abs(hash(ticker)) % (2 ** 32))
        closes = list(100 * np.cumprod(1 + rng.normal(0.0002 + 0.0006 * q, 0.012, len(self.dates))))
        return self.dates, closes

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
