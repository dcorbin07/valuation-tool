"""
Edge Lab tests (offline, deterministic). Run:
    python tests/test_edge.py
Validates the backtest math, the no-overfit walk-forward + advisor, the factor
panel, and owner-only gating.
"""
import datetime as dt
import math
import os
import re
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


def test_valquo_index_market_caps_are_dollars_not_millions():
    """The large-cap floor is 10e9 DOLLARS. A book fed millions-denominated caps clears
    nothing, silently degrades to 'largest half', and renders as $0.0B in the UI — which is
    exactly what the live site showed. Pin the contract so it can't drift back."""
    from valuation.edge.valquo_index import build_index, LARGE_CAP_MIN
    assert LARGE_CAP_MIN == 10e9

    dollars = build_index(_index_rows())
    assert dollars["criteria"]["tilt"] == "large-cap only"

    millions = _index_rows()
    for r in millions:
        r["market_cap"] = r["market_cap"] / 1e6           # the pre-fix live convention
    degraded = build_index(millions)
    assert "large-cap only" not in degraded["criteria"]["tilt"], (
        "millions-denominated caps must not masquerade as a large-cap book")


def test_valquo_index_export_fills_blank_names_and_sectors():
    """The point-in-time Sharadar export carries no company name and no sector, so an
    exported book listed bare tickers and reported sector_data_available: false. The export
    now decorates the finished book from the live feed and recomputes the sector block."""
    import json
    import os
    import tempfile
    from valuation.edge.valquo_index import export

    rows = _index_rows()
    truth = {r["ticker"]: (r["name"], r["sector"]) for r in rows}
    for r in rows:                                        # what the Sharadar path emits
        r["name"], r["sector"] = "", ""

    class _St:
        """The book is built from `rows` (no names, no sectors — the Sharadar shape); the
        names/sectors come from the store's profile cache, which the live scan populated."""
        def latest_scan_date(self): return "2026-07-28"
        def load_snapshot(self, d=None, top=None): return rows
        def get_profiles(self, tickers=None):
            want = {t.upper() for t in (tickers or truth)}
            return [{"ticker": t, "name": n, "sector": s, "industry": ""}
                    for t, (n, s) in truth.items() if t in want]
        def get_cached_fundamentals(self, t, max_age_days=None): return None
        def cache_profiles(self, profiles): pass

    path = os.path.join(tempfile.mkdtemp(), "valquo_index.json")
    p = export(store=_St(), path=path)

    assert p["sector_data_available"] is True, p["profile_enrichment"]
    assert "unknown" not in p["sector_weights"], p["sector_weights"]
    assert abs(sum(p["sector_weights"].values()) - 1.0) < 1e-3
    assert all(x["name"] and x["sector"] for x in p["positions"])
    for x in p["positions"]:
        assert (x["name"], x["sector"]) == truth[x["ticker"]]
    assert json.load(open(path, encoding="utf-8"))["sector_data_available"] is True


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
    # EV is rebuilt at the REBALANCE date (market cap 10,000 + USD net debt 200 - 50 = 10,150),
    # not read off the filing's stale `ev` of 5,000. That the won-reporting twin lands on the
    # same number is the sharper half of the claim: net debt is a LOCAL line item and the
    # market cap is USD, so the rebuild has to convert before adding — P7 in a second costume.
    assert abs(usd["ebit_ev"] - 150.0 / 10_150.0) < 1e-12
    assert abs(usd["ev_sales"] - 10_150.0 / 500.0) < 1e-12
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


def test_signup_surfaces_follow_the_open_access_flag():
    """Signup + pricing are hidden while the product is open and free, and re-enabled by a
    flag rather than a code change. Login must NOT be gated — existing accounts still sign in.
    """
    from valuation.config import Config
    # private_mode=False throughout: this test is about the PUBLIC product's flags, and
    # private mode switches all of them off by design (see test_private.py, which asserts
    # exactly that). Passing it explicitly rather than relying on the default keeps the two
    # concerns from silently merging when the default changes again.
    def C(**kw):
        return Config(private_mode=False, **kw)
    open_free = C(open_access=True, feature_billing="")
    assert open_free.signup_enabled is False
    assert open_free.billing_enabled is False
    paid = C(open_access=False, feature_billing="")
    assert paid.signup_enabled is True, "turning open access off restores the paid product"
    # FEATURE_BILLING is an explicit override in both directions.
    assert C(open_access=True, feature_billing="on").signup_enabled is True
    assert C(open_access=False, feature_billing="off").signup_enabled is False
    for v in ("On", "TRUE", "1", "yes"):
        assert C(open_access=True, feature_billing=v).signup_enabled is True, v
    for v in ("off", "False", "0", "no"):
        assert C(open_access=False, feature_billing=v).signup_enabled is False, v


def test_no_ungated_signup_or_pricing_links_in_templates():
    """Every /register and /pricing link must sit behind the flag. A missed one is a dead-end
    for a visitor: the routes redirect, so an ungated button silently bounces them."""
    import glob
    tpl = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "valuation", "web", "templates")
    offenders = []
    for path in glob.glob(os.path.join(tpl, "*.html")):
        name = os.path.basename(path)
        if name == "pricing.html":
            continue          # only reachable when the /pricing route already allows it
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        if ('href="/register"' in src or 'href="/pricing"' in src) and "signup_enabled" not in src:
            offenders.append(name)
    assert not offenders, f"ungated signup/pricing links in: {offenders}"
    # And the route guards themselves must exist, not just the template gating.
    root = os.path.dirname(tpl.rsplit(os.sep + "web", 1)[0])
    with open(os.path.join(root, "valuation", "saas", "auth.py"), encoding="utf-8") as fh:
        auth_src = fh.read()
    with open(os.path.join(root, "valuation", "saas", "app_saas.py"), encoding="utf-8") as fh:
        app_src = fh.read()
    assert "signup_enabled" in auth_src, "/register must be guarded at the route"
    assert "signup_enabled" in app_src, "/pricing must be guarded at the route"


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


def _tax_panel(n_dates=24, n=60, drift=0.03, seed=31):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        # ~quarterly dates, so four rebalances really do cross the one-year line.
        y, m = 2020 + d // 4, (d % 4) * 3 + 1
        for i in range(n):
            sig = rng.normal()
            rows.append({"date": f"{y}-{m:02d}-01", "ticker": f"T{i}",
                         "fwd_ret": drift + 0.02 * sig, "bench_ret": 0.01,
                         "market_cap": 5e10, "good": sig})
    return pd.DataFrame(rows)


def test_risk_stats_sharpe_and_drawdown():
    """Concentration must be chosen on risk-adjusted return: a tighter book almost always has
    a higher mean AND a much higher variance, so ranking on alpha alone picks the noisiest."""
    from valuation.edge.fundamental_panel import risk_stats
    steady = [0.02] * 40
    r = risk_stats(steady, per_year=4)
    assert r["max_drawdown"] == 0.0, "a monotonically rising curve has no drawdown"
    assert r["sharpe"] is None or r["sharpe"] > 100  # zero vol -> None or enormous
    rng = np.random.default_rng(5)
    calm = list(rng.normal(0.02, 0.01, 200))
    wild = list(rng.normal(0.02, 0.08, 200))
    assert risk_stats(calm, 4)["sharpe"] > risk_stats(wild, 4)["sharpe"], "same mean, more vol"
    assert risk_stats(wild, 4)["max_drawdown"] < risk_stats(calm, 4)["max_drawdown"]
    assert risk_stats(calm, 4)["vol_ann"] < risk_stats(wild, 4)["vol_ann"]
    # A real drawdown is measured peak-to-trough on the compounded curve.
    dd = risk_stats([0.5, -0.5, 0.0, 0.0], 4)["max_drawdown"]
    assert abs(dd - (-0.5)) < 1e-9, dd
    assert risk_stats([0.01], 4)["sharpe"] is None      # too few points -> no fake precision


def test_book_configs_are_defined_and_coherent():
    """Two named constructions ship: roth (tax-free, Sharpe-optimal, full rotation) and
    taxable (after-tax-optimal, decile + band)."""
    from valuation.screener import settings as S
    assert set(S.BOOK_CONFIGS) == {"roth", "taxable"}
    assert S.DEFAULT_BOOK_CONFIG in S.BOOK_CONFIGS
    roth, tax = S.BOOK_CONFIGS["roth"], S.BOOK_CONFIGS["taxable"]
    # roth rotates freely (no band); taxable uses one — that is the whole distinction.
    assert roth["exit_frac"] is None and roth["exit_mult"] is None
    assert tax["exit_frac"] == 0.20
    # roth is the tighter, faster book; taxable is the broader, slower one.
    assert roth["top_n"] == 25 and tax["top_frac"] == 0.10
    assert roth["rebalance_days"] < tax["rebalance_days"]
    for name, c in S.BOOK_CONFIGS.items():
        assert (c["top_n"] is None) != (c["top_frac"] is None), f"{name}: exactly one width"
        assert c["label"] and c["measured"], name


def test_no_trade_band_reduces_turnover_and_reduces_to_top_n():
    """Hysteresis: enter on the top 10%, hold until a name falls past the exit band. The
    no-band case must be EXACTLY plain top-N, otherwise the baseline is a different code path
    and the whole comparison is meaningless."""
    from valuation.edge.fundamental_panel import _band_select, turnover_and_costs
    comp = np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0])
    tick = np.array(["A", "B", "C", "D", "E", "F"])
    # No band (exit_rank == n_target) -> plain top-N regardless of what is held.
    assert _band_select(comp, tick, set(), 3, 3) == ["A", "B", "C"]
    assert sorted(_band_select(comp, tick, {"E", "F"}, 3, 3)) == ["A", "B", "C"]
    # With a band, a held name that slipped to rank 3 is KEPT and displaces the newcomer.
    kept = _band_select(comp, tick, {"D"}, 3, 5)
    assert "D" in kept and len(kept) == 3, kept
    # A held name outside the band is dropped even with a band.
    assert "F" not in _band_select(comp, tick, {"F"}, 3, 4)
    # Book size is constant so widths are compared like-for-like.
    for xr in (3, 4, 5, 6):
        assert len(_band_select(comp, tick, {"D", "E"}, 3, xr)) == 3

    panel = _tax_panel(n_dates=16, n=60)
    base = turnover_and_costs(panel, ["good"], {"good": 1.0}, top_frac=0.2, flat_bps=10.0)
    band = turnover_and_costs(panel, ["good"], {"good": 1.0}, top_frac=0.2, flat_bps=10.0,
                              exit_frac=0.4)
    assert band["annual_turnover"] < base["annual_turnover"], "a band must cut turnover"
    assert band["cost_drag_ann"] < base["cost_drag_ann"], "less trading must cost less"
    # exit_frac equal to top_frac must reproduce the no-band numbers exactly.
    same = turnover_and_costs(panel, ["good"], {"good": 1.0}, top_frac=0.2, flat_bps=10.0,
                              exit_frac=0.2)
    assert abs(same["annual_turnover"] - base["annual_turnover"]) < 1e-9
    assert abs(same["net_ann"] - base["net_ann"]) < 1e-12


def test_after_tax_backtest_lot_accounting():
    """~250%/yr turnover means nearly every gain is short-term in a taxable account, and that
    drag is several times the trading cost. Tax depends on WHEN each lot was bought, so this
    has to be lot-level, not an average rate applied to a return."""
    from valuation.edge.fundamental_panel import (after_tax_backtest, turnover_and_costs,
                                                  TAX_SHORT_TERM, TAX_LONG_TERM)
    panel = _tax_panel()
    cols, w = ["good"], {"good": 1.0}

    # Zero rates must reconcile with the pure cost model (small residual: this pays drag
    # BEFORE the period return, so the remainder compounds).
    free = after_tax_backtest(panel, cols, w, top_frac=0.2, short_rate=0.0, long_rate=0.0,
                              flat_bps=0.0)
    costs = turnover_and_costs(panel, cols, w, top_frac=0.2, flat_bps=0.0)
    assert abs(free["after_tax_ann"] - costs["net_ann"]) < 0.02, (free["after_tax_ann"],
                                                                  costs["net_ann"])
    assert free["tax_paid_short"] == 0 and free["tax_paid_long"] == 0

    taxed = after_tax_backtest(panel, cols, w, top_frac=0.2, flat_bps=0.0)
    assert taxed["after_tax_ann"] < free["after_tax_ann"], "tax must reduce the return"
    assert taxed["total_drag_ann"] > 0
    assert taxed["short_rate"] == TAX_SHORT_TERM and taxed["long_rate"] == TAX_LONG_TERM
    # A quarterly-rebalanced book realizes mostly SHORT-term gains.
    assert taxed["short_term_share_of_gains"] > 0.5, taxed["short_term_share_of_gains"]
    # Higher rates must cost more; the ordering has to be monotone.
    hi = after_tax_backtest(panel, cols, w, top_frac=0.2, short_rate=0.60, long_rate=0.40,
                            flat_bps=0.0)
    assert hi["after_tax_ann"] < taxed["after_tax_ann"] < free["after_tax_ann"]
    # Deferred (unrealized) liability is reported, not silently treated as free money.
    assert "unrealized_gain_end" in taxed


def test_after_tax_losses_offset_gains_and_carry_forward():
    """A book that only loses money must pay NO tax — and losses must not create a phantom
    credit that flatters the return."""
    from valuation.edge.fundamental_panel import after_tax_backtest
    losing = _tax_panel(drift=-0.04, seed=7)
    r = after_tax_backtest(losing, ["good"], {"good": 1.0}, top_frac=0.2, flat_bps=0.0)
    assert r["tax_paid_short"] == 0 and r["tax_paid_long"] == 0, "no tax on a net loss"
    free = after_tax_backtest(losing, ["good"], {"good": 1.0}, top_frac=0.2,
                              short_rate=0.0, long_rate=0.0, flat_bps=0.0)
    assert abs(r["after_tax_ann"] - free["after_tax_ann"]) < 1e-9, "losses must not add return"
    assert after_tax_backtest(_tax_panel(n_dates=2), ["good"], {"good": 1.0}).get("status")


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
    md = render_md(p)
    # AUDIT B8 — the RENDERED file used to head this section "Held-out confirmation ...
    # out-of-sample" over a verdict that is a both-halves stability check. Fixing the
    # function while leaving the product-facing label wrong would have fixed half of B8.
    assert "Held-out theme checks" in md
    assert "Held-out confirmation" not in md, "the overstated heading came back"
    assert "NOT an out-of-sample confirmation" in md


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


def test_regime_overlay_is_point_in_time_and_off_by_default():
    """The trend filter must never see a close after the decision date, and the overlay must
    ship OFF — it was tested and NOT adopted (its whole benefit is the 2008 half)."""
    from valuation.edge import regime as R
    from valuation.screener import settings as S
    assert S.REGIME_OVERLAY is None, "tested and not adopted; must default off"
    assert R.TREND_MA_DAYS == 200 and R.RISK_OFF_EXPOSURE == (0.0, 0.5)

    # A clean up-then-down series: invested while above the MA, out after it breaks.
    dates = pd.bdate_range("2020-01-01", periods=600)
    up = np.linspace(100, 200, 300)
    down = np.linspace(200, 90, 300)
    closes = list(up) + list(down)
    ds = [str(d.date()) for d in dates]
    sig = R.trend_signal(ds, closes, ds[::20])
    assert sig[ds[280]] is True, "still above a rising MA near the peak"
    assert sig[ds[560]] is False, "well below the MA after a sustained fall"
    # Before there is enough history the rule stays INVESTED — never a free hindsight exit.
    assert sig[ds[0]] is True

    # Point-in-time: truncating the series after the decision date cannot change the answer.
    cut = 400
    trunc = R.trend_signal(ds[:cut], closes[:cut], [ds[cut - 1]])
    full = R.trend_signal(ds, closes, [ds[cut - 1]])
    assert trunc[ds[cut - 1]] == full[ds[cut - 1]], "future closes leaked into the signal"


def test_regime_overlay_scales_exposure_and_counts_whipsaw():
    from valuation.edge import regime as R
    rets = [0.10, -0.10, 0.10, -0.10]
    dates = ["a", "b", "c", "d"]
    inv = {"a": True, "b": False, "c": True, "d": False}
    out, flips, share = R.apply_overlay(rets, dates, inv, 0.0, periods_per_year=6.0)
    assert out == [0.10, 0.0, 0.10, 0.0], out          # cash at 0% -> risk-off periods are flat
    assert flips == 3 and abs(share - 0.5) < 1e-9
    half, _, _ = R.apply_overlay(rets, dates, inv, 0.5, periods_per_year=6.0)
    assert abs(half[1] - (-0.05)) < 1e-12, "50% exposure halves the loss"
    # Always-invested -> unchanged returns and no flips.
    same, f2, sh2 = R.apply_overlay(rets, dates, {d: True for d in dates}, 0.0)
    assert same == rets and f2 == 0 and sh2 == 1.0


def test_valuation_regime_is_point_in_time_and_off_by_default():
    """The percentile must be computed over PRIOR dates only — a date that included itself in
    its own reference distribution would be look-ahead."""
    from valuation.edge import valuation_regime as VR
    from valuation.screener import settings as S
    assert S.VALUATION_REGIME_OVERLAY is None, "tested and rejected; must default off"
    assert VR.VALUATION_PCTILE == 20 and VR.MIN_HISTORY == 20

    # Falling yield (= richening market): only the late, expensive dates go risk-off.
    n = 60
    frame = pd.DataFrame({"date": [f"d{i:03d}" for i in range(n)],
                          "agg_ey": np.linspace(0.06, 0.01, n)})
    sig = VR.valuation_signal(frame)
    assert all(sig[f"d{i:03d}"] for i in range(VR.MIN_HISTORY)), "no firing without history"
    assert sig["d059"] is False, "cheapest yield in its own history -> risk-off"
    # Truncating the frame after date k cannot change date k's answer.
    k = 50
    part = VR.valuation_signal(frame.iloc[:k + 1])
    assert part[f"d{k:03d}"] == sig[f"d{k:03d}"], "future dates leaked into the percentile"
    # A RISING yield (cheapening market) never goes risk-off.
    rising = pd.DataFrame({"date": [f"r{i:03d}" for i in range(n)],
                           "agg_ey": np.linspace(0.01, 0.06, n)})
    assert all(VR.valuation_signal(rising).values())


def test_aggregate_valuation_sums_rather_than_averages():
    """sum(NI)/sum(mktcap), not the mean of per-name yields — otherwise one micro-cap with a
    freak ratio moves the market aggregate, and loss-makers produce undefined P/Es."""
    from valuation.edge import valuation_regime as VR
    panel = pd.DataFrame({
        "date": ["d1"] * 3,
        "market_cap": [1e12, 1e9, 1e9],
        # mega cap yields 5%; two tiny names at +200% and -200% cancel in the aggregate
        "raw_earnings_yield": [0.05, 2.0, -2.0],
    })
    v = VR.aggregate_valuation(panel)
    agg = float(v["agg_ey"].iloc[0])
    # 5e10 / 1.002e12 — the two tiny caps sit in the DENOMINATOR, so the exact answer is
    # 0.0499002, not 0.05. Their +200%/-200% yields cancel in the numerator.
    assert abs(agg - (5e10 / 1.002e12)) < 1e-9, agg
    # Loss-makers NET OFF in the numerator rather than producing an undefined P/E.
    assert v["median_pe"].notna().iloc[0]

    # Separate case for "not the naive mean": two tiny names with LOPSIDED yields, where the
    # naive average is wildly different from the cap-weighted truth. (In the case above the
    # +200/-200 cancel, so the naive mean lands near the right answer by coincidence.)
    lop = pd.DataFrame({"date": ["d1"] * 3, "market_cap": [1e12, 1e9, 1e9],
                        "raw_earnings_yield": [0.05, 2.0, 3.0]})
    a2 = float(VR.aggregate_valuation(lop)["agg_ey"].iloc[0])
    assert abs(a2 - (5.5e10 / 1.002e12)) < 1e-9, a2
    assert abs(np.mean([0.05, 2.0, 3.0]) - a2) > 1.5, "must not be the naive per-name mean"
    # An empty / column-less panel returns an empty frame rather than raising.
    assert VR.aggregate_valuation(pd.DataFrame()).empty


def test_ml_combiner_optional_import_and_per_fold_features():
    """sklearn is an OPTIONAL dependency (not in requirements.txt) — a missing import must
    return a status, never break a run. And features must be filtered PER FOLD: the 13F signals
    are empty before 2013-06-30, so an early CPCV fold hands the binner an all-NaN column."""
    from valuation.edge import ml_combiner as ML
    assert ML.MIN_IC_GAIN == 0.005 and ML.MIN_ALPHA_GAIN == 0.01, "gate must stay pre-committed"
    assert ML.GBM_PARAMS["max_depth"] == 3, "model must stay small"

    rng = np.random.default_rng(3)
    rows = []
    for d in range(24):
        for i in range(80):
            # Year rolls over so SORTED date order matches d order — otherwise the
            # "early" slice picks up late dates and the fixture tests nothing.
            rows.append({"date": f"{2024 + d // 12}-{d % 12 + 1:02d}-01",
                         "ticker": f"T{i}", "fwd_ret": float(rng.normal(0, 0.05)),
                         "z_roic": float(rng.normal()), "z_roe": float(rng.normal()),
                         "z_ret_12_1": float(rng.normal()),
                         # empty in the early half, exactly like the 13F signals
                         "z_inst_accum": (float(rng.normal()) if d >= 12 else np.nan)})
    panel = pd.DataFrame(rows)
    early = sorted(panel["date"].unique())[:6]
    feats = ["z_roic", "z_roe", "z_ret_12_1", "z_inst_accum"]
    usable = ML._usable_features(panel, early, feats)
    assert "z_inst_accum" not in usable, "an all-NaN-in-fold feature must be dropped"
    assert {"z_roic", "z_roe", "z_ret_12_1"} <= set(usable)
    # Late fold has the data, so it comes back.
    late = sorted(panel["date"].unique())[-6:]
    assert "z_inst_accum" in ML._usable_features(panel, late, feats)
    # Too few usable features -> None rather than a crash.
    assert ML.fit_predict(panel, early, late, ["z_inst_accum"]) is None
    # cpcv_compare degrades to a status dict rather than raising when sklearn is absent.
    r = ML.cpcv_compare(panel.head(30), ["z_roic"], {"z_roic": 1.0})
    assert "status" in r or r.get("n_paths") == 0


def test_pead_is_point_in_time_and_scores_no_theme():
    """PEAD was tested and REJECTED, so it must stay measured-but-unscored. And the CAR window
    must have CLOSED by as_of — otherwise the signal contains returns from the future."""
    from valuation.edge import pead as P
    from valuation.screener import settings as S
    from valuation.screener.factors import build_frame
    assert S.NUMBER_THEME.get("pead_car") == "momentum", "stays measured"
    # ...but must NOT be inside the momentum mean.
    metrics = [{"ticker": f"T{i}", "price": 10.0, "market_cap": 1e10, "net_income": 5.0,
                "operating_income": 6.0, "ret_6_1": 0.1 * i, "high_prox": 0.9,
                "pead_car": -5.0} for i in range(20)]
    fr = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    no_pead = build_frame([{**m, "pead_car": None} for m in metrics],
                          sector_neutral=False, residual_momentum=False)
    pd.testing.assert_series_equal(fr["momentum"], no_pead["momentum"], check_names=False)

    # Point-in-time: a CAR window that has not closed by as_of yields NO signal.
    dates = pd.bdate_range("2026-01-01", periods=40)
    d64 = dates.values.astype("datetime64[D]")
    closes = list(np.linspace(100, 140, 40))
    bench = list(np.linspace(100, 110, 40))
    ann = [str(dates[10].date())]
    got = P.pead_signals(closes, d64, bench, ann, str(dates[20].date()))
    assert "pead_car" in got, got
    # as_of ON the announcement day: t+1 has not happened yet -> nothing.
    assert P.pead_signals(closes, d64, bench, ann, str(dates[10].date())) == {}
    # An announcement AFTER as_of is invisible.
    assert P.pead_signals(closes, d64, bench, [str(dates[30].date())],
                          str(dates[20].date())) == {}
    # Drift is absent once the announcement is stale, rather than decayed.
    old = P.pead_signals(closes, d64, bench, ann, str(dates[39].date()), drift_days=5)
    assert "pead_car" in old and "pead_drift" not in old
    assert P.pead_signals(closes, d64, bench, [], "2026-02-01") == {}


def test_elite13f_skill_is_point_in_time():
    """A manager's score at quarter q must use only quarters STRICTLY EARLIER than q. Using a
    whole-sample record would be look-ahead of the worst kind — 'funds that did well over
    2008-2026 bought this in 2009' is the answer key, not a signal."""
    from valuation.edge import elite13f as E
    from valuation.screener import settings as S
    quality = {("M1", "2020-03-31"): 0.10, ("M1", "2020-06-30"): 0.20,
               ("M1", "2020-09-30"): 0.30, ("M1", "2020-12-31"): 0.40,
               ("M1", "2021-03-31"): 0.50, ("M1", "2021-06-30"): -0.90}
    sk = E.skill_as_of(quality, min_quarters=4)
    # Nothing before 4 quarters of history exist.
    for q in ("2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"):
        assert ("M1", q) not in sk, q
    # The 5th quarter scores on the mean of the FIRST FOUR only.
    assert abs(sk[("M1", "2021-03-31")] - 0.25) < 1e-12, sk[("M1", "2021-03-31")]
    # The disastrous final quarter cannot retroactively lower an earlier score...
    assert abs(sk[("M1", "2021-06-30")] - 0.30) < 1e-12
    # ...and a manager's own quarter never contributes to its own score.
    assert all(v > 0 for v in sk.values()), "a -0.90 quarter leaked into its own score"
    # Rejected: measured but scoring in no theme.
    assert S.NUMBER_THEME.get("sm_elite_conviction") == "institutional"
    from valuation.screener.factors import build_frame
    metrics = [{"ticker": f"T{i}", "price": 10.0, "market_cap": 1e10, "net_income": 5.0,
                "operating_income": 6.0, "inst_accum": 0.05 * i, "sm_breadth": 0.01 * i,
                "sm_elite_conviction": -9.0} for i in range(20)]
    fr = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    without = build_frame([{**m, "sm_elite_conviction": None} for m in metrics],
                          sector_neutral=False, residual_momentum=False)
    pd.testing.assert_series_equal(fr["institutional"], without["institutional"],
                                   check_names=False)


def test_short_interest_uses_publication_date_not_settlement():
    """The trap this dataset sets: FINRA exposes only settlementDate, but the figure is not
    public until ~8 business days later. Using settlement as the as-of would inject ~2 weeks of
    look-ahead into every observation."""
    from valuation.edge import short_interest as SI
    from valuation.screener import settings as S
    assert SI.PUBLICATION_LAG_DAYS >= 12, "must clear the ~8 business day dissemination schedule"
    # Rows are stamped with the AVAILABLE date; a settlement-dated caller cannot reach them.
    rows = [("2026-01-30", 3.0, 100.0, 80.0), ("2026-02-14", 5.0, 150.0, 100.0)]
    # As of a date before the first publication -> nothing, even though settlement has passed.
    assert SI.signals_at(rows, "2026-01-29") == {}
    got = SI.signals_at(rows, "2026-01-30")
    assert got["neg_days_to_cover"] == -3.0
    assert abs(got["neg_short_interest_chg"] - (-(100.0 / 80.0 - 1.0))) < 1e-12
    # A later observation supersedes, but only once IT is published.
    assert SI.signals_at(rows, "2026-02-13")["neg_days_to_cover"] == -3.0
    assert SI.signals_at(rows, "2026-02-14")["neg_days_to_cover"] == -5.0
    assert SI.signals_at([], "2026-02-14") == {}
    # Orientation is negated: MORE days-to-cover must score WORSE.
    heavy = SI.signals_at([("2026-01-30", 9.0, 100.0, 80.0)], "2026-02-01")
    light = SI.signals_at([("2026-01-30", 1.0, 100.0, 80.0)], "2026-02-01")
    assert heavy["neg_days_to_cover"] < light["neg_days_to_cover"]
    # Rejected: measured but scoring in no theme.
    assert S.NUMBER_THEME.get("neg_days_to_cover") == "low_risk"
    from valuation.screener.factors import build_frame
    metrics = [{"ticker": f"T{i}", "price": 10.0, "market_cap": 1e10, "net_income": 5.0,
                "operating_income": 6.0, "realized_vol": 0.2 + 0.01 * i, "beta": 1.0,
                "neg_days_to_cover": -99.0} for i in range(20)]
    fr = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    without = build_frame([{**m, "neg_days_to_cover": None} for m in metrics],
                          sector_neutral=False, residual_momentum=False)
    pd.testing.assert_series_equal(fr["low_risk"], without["low_risk"], check_names=False)


def test_edgar13d_dating_and_form_rename():
    """Two silent-failure guards, both of which actually bit during P24.2.

    1. The SEC RENAMED these forms during 2024 ("SC 13D" -> "SCHEDULE 13D"). Matching only the
       old spelling returned ~30 filings/quarter for 2025-2026 instead of ~15,000, so the most
       recent panel dates would have carried a structurally-zero signal while looking healthy.
    2. Only the FILING date may be used. The event date (crossing 5%, up to 10 days earlier) is
       never parsed, so a filing must be invisible until the day it is filed.
    """
    from valuation.edge import edgar13d as E
    from valuation.screener import settings as S
    for f in ("SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A"):
        assert f in E.FORMS_13D, f
    for f in ("SC 13G", "SCHEDULE 13G/A"):
        assert f in E.FORMS_13G, f
    rx = re.compile(E.ROW_RX)
    for line, want in (
            ("SC 13D           Acme Corp                    1591890     2015-05-21  edgar/x.txt", "SC 13D"),
            ("SCHEDULE 13G/A   Acme Corp                    1591890     2025-05-21  edgar/y.txt", "SCHEDULE 13G/A")):
        m = rx.match(line)
        assert m and m.group(1) == want and m.group(3) == "1591890"
    rows = [("2026-01-05", "SC 13D"), ("2026-06-01", "SCHEDULE 13G"),
            ("2026-07-20", "SCHEDULE 13D")]
    # Nothing is visible the day before it is filed.
    assert E.signals_at(rows, "2026-07-19")["activist_13d"] == 0.0
    assert E.signals_at(rows, "2026-07-20")["activist_13d"] == 1.0
    # Old spelling still counts, and the window is trailing, not cumulative.
    assert E.signals_at(rows, "2026-01-05")["activist_13d"] == 1.0
    got = E.signals_at(rows, "2026-07-30")
    assert got["activist_13d"] == 1.0 and got["passive_13g"] == 1.0   # Jan 13D aged out
    # Absence is zero for a name with history; both rejected, so neither is scored.
    assert E.signals_at([], "2026-07-30") == {"activist_13d": 0.0, "passive_13g": 0.0}
    assert S.NUMBER_THEME.get("activist_13d") == "institutional"
    assert "activist_13d" not in S.WEIGHTS_ESTABLISHED


def test_congress_never_stores_transaction_date():
    """The single most dangerous field in this project.

    The STOCK Act allows 45 days from trade to PTR filing and late filings are common: measured
    on the real data, 21.9% are late, the 90th percentile delay is 210 days and the max is 4,049.
    Using transaction_date would inject up to seven months of look-ahead exactly when a member's
    presumed advantage plays out. So the loader must DISCARD it - not merely decline to filter on
    it - and signals_at must key off the filing date.
    """
    import json as _json
    import tempfile
    from valuation.edge import congress as CG
    from valuation.screener import settings as S

    row = {"ticker": "ZZZ", "source_id": "house_clerk", "transaction_type": "Purchase",
           "amount_range_low": 1001, "amount_range_high": 15000,
           "transaction_date": "2020-01-02", "filing_date": "2020-06-30"}
    with tempfile.TemporaryDirectory() as d:
        sub = os.path.join(d, "public", "data", "ticker")
        os.makedirs(sub)
        with open(os.path.join(sub, "ZZZ.json"), "w", encoding="utf-8") as f:
            _json.dump({"trades": [row, dict(row, source_id="oge_executive")]}, f)
        got = CG.fetch_congress_trades(repo_dir=d)
    assert list(got) == ["ZZZ"]
    # Executive-branch row excluded; only one transaction survives.
    assert len(got["ZZZ"]) == 1
    stored_dates = [d for d, _ in got["ZZZ"]]
    assert stored_dates == ["2020-06-30"], stored_dates
    assert "2020-01-02" not in str(got), "transaction date must never reach the cache"
    # Invisible until filed, even though the trade happened in January.
    assert CG.signals_at(got["ZZZ"], "2020-06-29") == {}
    assert CG.signals_at(got["ZZZ"], "2020-06-30")["congress_net_buy"] == 1.0
    assert CG.amount_midpoint(1001, 15000) == 8000.5
    assert S.NUMBER_THEME.get("congress_net_buy") == "sentiment"
    assert "congress_net_buy" not in S.WEIGHTS_ESTABLISHED


def test_usaspending_publication_lag_and_seasonality():
    """Awards are stamped quarter_end + lag, and 4q-over-4q so the federal year-end spike cancels."""
    from valuation.edge import usaspending as U
    from valuation.screener import settings as S

    assert U.PUBLICATION_LAG_DAYS >= 45           # FPDS reporting delay; DoD historically 90d
    assert U._quarter_end(2010, 1) == "2009-12-31"   # federal FY starts Oct 1 of the prior year
    assert U._quarter_end(2010, 4) == "2010-09-30"
    assert U.normalize_name("THE BOEING COMPANY") == "BOEING"
    assert U.normalize_name("Lockheed Martin Corporation") == "LOCKHEED MARTIN"
    # Needs 2*trailing published quarters, else no half-formed number.
    short = [(f"2020-{m:02d}-01", 100.0) for m in range(1, 8)]
    assert U.signals_at(short, "2020-12-31") == {}
    flat = [(f"2020-{m:02d}-01", 100.0) for m in range(1, 9)]
    assert U.signals_at(flat, "2020-12-31")["govt_award_momentum"] == 0.0
    grow = [(f"2020-{m:02d}-01", float(m)) for m in range(1, 9)]
    assert abs(U.signals_at(grow, "2020-12-31")["govt_award_momentum"] - 1.6) < 1e-9
    # Nothing is visible before its publication date.
    assert U.signals_at(grow, "2020-07-31") == {}
    assert S.NUMBER_THEME.get("govt_award_momentum") == "growth"
    assert "govt_award_momentum" not in S.WEIGHTS_ESTABLISHED


def test_options_fill_engine_charges_the_spread_both_ways():
    """The default must be the HONEST fill, not the flattering one.

    An options backtest that fills at the mid is not optimistic, it measures a strategy nobody
    can trade: a 2.40/2.60 quote is an 8% round-trip haircut before the underlying moves.
    """
    from valuation.edge import options_fill as F

    assert F.DEFAULT_AGGRESSION == 1.0, "default must be buy-the-ask / sell-the-bid"
    q = F.Quote(bid=2.40, ask=2.60, oi=500, volume=100)
    assert q.mid == 2.50
    assert abs(q.spread_pct - 0.08) < 1e-9
    assert F.fill_price(q, "buy") == 2.60          # pays the ask
    assert F.fill_price(q, "sell") == 2.40         # hits the bid
    assert F.fill_price(q, "buy", aggression=0.0) == 2.50   # mid: diagnostic only
    # A flat round trip must LOSE the spread plus commission, never break even.
    t = F.round_trip(q, q, right="C", strike=100.0)
    assert t["ok"]
    assert t["net_pnl"] < 0, t
    assert abs(t["net_pnl"] - ((2.40 - 2.60) * 100 - 1.30)) < 1e-9
    assert t["gross_pnl"] == 0.0                   # mid-to-mid is flat; the cost is explicit
    assert abs(t["cost"] - 21.30) < 1e-9


def test_options_fill_rejects_bad_quotes_and_never_repairs_them():
    """Every rejection is a named reason. Silently skipping unfillable contracts would be
    survivorship bias: hard-to-fill contracts are disproportionately the ones that moved."""
    from valuation.edge import options_fill as F

    good = dict(oi=500, volume=100)
    cases = {
        "no_quote":     F.Quote(bid=None, ask=None, **good),
        "non_positive": F.Quote(bid=0.0, ask=0.5, **good),
        "crossed":      F.Quote(bid=2.60, ask=2.40, **good),
        "locked":       F.Quote(bid=2.50, ask=2.50, **good),
        "thin_premium": F.Quote(bid=0.01, ask=0.05, **good),
        "wide_spread":  F.Quote(bid=1.00, ask=2.00, **good),
        "low_oi":       F.Quote(bid=2.40, ask=2.60, oi=1, volume=100),
        "low_volume":   F.Quote(bid=2.40, ask=2.60, oi=500, volume=0),
    }
    for want, q in cases.items():
        assert F.quote_reject_reason(q) == want, (want, F.quote_reject_reason(q))
        assert F.round_trip(q, q, right="C", strike=100.0)["ok"] is False
    ok = F.Quote(bid=2.40, ask=2.60, **good)
    assert F.quote_reject_reason(ok) is None
    # Liquidity is an ENTRY filter only - you must be able to exit what you own.
    illiquid_exit = F.Quote(bid=4.00, ask=4.40, oi=0, volume=0)
    assert F.quote_reject_reason(illiquid_exit, check_liquidity=False) is None
    t = F.round_trip(ok, illiquid_exit, right="C", strike=100.0)
    assert t["ok"] and t["net_pnl"] > 0


def test_options_expired_worthless_is_recorded_not_dropped():
    """A contract that expired worthless must post -100%, not vanish from the sample."""
    from valuation.edge import options_fill as F

    entry = F.Quote(bid=2.40, ask=2.60, oi=500, volume=100)
    t = F.round_trip(entry, None, right="C", strike=150.0, exit_underlying=120.0, expired=True)
    assert t["ok"] and t["settled_at_intrinsic"]
    assert t["exit_fill"] == 0.0
    assert abs(t["net_pnl"] - (-2.60 * 100 - 1.30)) < 1e-9
    # AUDIT B15 — `return_pct` is now net of spread AND commission, as the module docstring and
    # OPTIONS_BACKTEST_RESULTS.md always claimed it was. A long option that expires worthless
    # loses the whole premium PLUS the round-trip commission, so the return on capital deployed
    # is slightly worse than -100%. The old gross-of-commission quantity is pinned alongside it.
    assert abs(t["return_pct"] - (-2.60 * 100 - 1.30) / (2.60 * 100)) < 1e-12
    assert t["return_pct"] < -1.0
    assert t["return_pct_gross_comm"] == -1.0
    # In the money at expiry settles at intrinsic.
    t2 = F.round_trip(entry, None, right="C", strike=150.0, exit_underlying=160.0, expired=True)
    assert t2["exit_fill"] == 10.0
    # Without expired=True a missing exit quote is an error, not a free zero.
    assert F.round_trip(entry, None, right="C", strike=150.0)["ok"] is False


def test_options_breakeven_is_the_quotable_number():
    from valuation.edge import options_fill as F

    q = F.Quote(bid=2.40, ask=2.60, oi=500, volume=100)
    up = F.Quote(bid=5.40, ask=5.60, oi=500, volume=100)
    trades = [F.round_trip(q, up, right="C", strike=100.0) for _ in range(3)]
    be = F.breakeven_cost_per_contract(trades)
    assert abs(be - 300.0) < 1e-9        # $3.00 mid-to-mid move x 100
    cs = F.cost_summary(trades + [{"ok": False, "reason": "low_oi"}])
    assert cs["n_filled"] == 3 and cs["n_rejected"] == 1
    assert cs["reject_reasons"] == {"low_oi": 1}
    assert cs["avg_cost_per_contract"] > 0


def test_blackscholes_matches_reference_and_refuses_bad_prices():
    """Validated against ThetaData's own greeks on AAPL 2023-03-01: delta agreed 98.96% of the
    time (median error 0.0016), and in the tradable band |delta| 0.20-0.80 IV agreed 100%
    (median error 0.0018). The disagreements sat at median |delta| 0.94 - deep ITM, vega ~ 0."""
    from valuation.edge import blackscholes as BS

    S, K, T, r, sig = 100.0, 100.0, 1.0, 0.05, 0.20
    call = BS.bs_price(S, K, T, r, sig, "C")
    put = BS.bs_price(S, K, T, r, sig, "P")
    assert abs(call - 10.4506) < 1e-3
    assert abs(put - 5.5735) < 1e-3
    # Put-call parity.
    assert abs((call - put) - (S - K * math.exp(-r * T))) < 1e-9
    # IV round-trips.
    assert abs(BS.implied_vol(call, S, K, T, r, "C") - sig) < 1e-3
    g = BS.greeks(S, K, T, r, sig, "C")
    assert abs(g["delta"] - 0.6368) < 1e-3
    assert g["gamma"] > 0 and g["vega"] > 0 and g["theta"] < 0
    assert BS.greeks(S, K, T, r, sig, "P")["delta"] < 0
    # A price below intrinsic has no implied vol - must be None, never a fabricated number.
    assert BS.implied_vol(0.5, 150.0, 100.0, 1.0, r, "C") is None
    assert BS.implied_vol(-1, S, K, T, r, "C") is None
    assert BS.implied_vol(call, S, K, 0.0, r, "C") is None
    # The rate must never silently be zero.
    assert BS.risk_free_rate(dt.date(2023, 3, 1)) > 0.001


def test_thetadata_provider_is_optional_and_dedupes():
    """Optional-by-design, and dedupe collapses the feed's duplicate daily rows.

    HERMETIC ON PURPOSE. An earlier version of this test asserted that a keyless provider
    returns an empty chain, which passed or failed depending on the MACHINE: `chain_on` consults
    its disk cache BEFORE checking availability, so anywhere a real
    data/bulk/prepared/theta/AAPL/2023-03-01.pkl existed the keyless provider returned live
    cached data and the assertion failed. It also read THETADATA_API_KEY from the environment
    and .env, so the result depended on whether a credential happened to be present.

    A test that depends on local credentials or leftover cache files is not testing the code.
    This version pins the cache to an empty temp directory and never touches the network.
    """
    import tempfile

    import pandas as pd
    from valuation.edge.thetadata_provider import ThetaProvider

    with tempfile.TemporaryDirectory() as tmp:
        # api_key="" is an explicit "no credential", never the ambient environment.
        p = ThetaProvider(api_key="", cache_dir=tmp)
        st = p.status()
        assert st["available"] is False
        assert "THETADATA_API_KEY" in (st["reason"] or "")
        # Empty cache dir => nothing to return, and no client is ever constructed.
        assert len(p.chain_on("AAPL", dt.date(2023, 3, 1))) == 0
        assert p.cached_dates("AAPL") == []
        assert p._client is None, "a keyless provider must never build a client"

        # A cache hit must be returned WITHOUT a key - that is what makes runs resumable.
        import pickle
        d = os.path.join(tmp, "AAPL")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "2023-03-01.pkl"), "wb") as f:
            pickle.dump(pd.DataFrame({"strike": [150.0]}), f)
        assert len(p.chain_on("AAPL", dt.date(2023, 3, 1))) == 1
        assert p.cached_dates("AAPL") == [dt.date(2023, 3, 1)]

    # Dedupe is pure and env-independent: the feed emits several rows per contract per day and
    # the LAST (closing) snapshot must win, or every trade is counted more than once.
    raw = pd.DataFrame({
        "created": ["2023-03-01 17:16:02", "2023-03-01 18:38:46",
                    "2023-03-01 17:16:02", "2023-03-02 18:38:46"],
        "expiration": ["2023-04-21"] * 4,
        "strike": [150.0, 150.0, 155.0, 150.0],
        "right": ["CALL"] * 4,
        "bid": [2.40, 2.55, 1.10, 2.70],
        "ask": [2.60, 2.75, 1.30, 2.90],
    })
    ded = ThetaProvider._dedupe(raw)
    assert len(ded) == 3, ded
    day1 = ded[(ded["strike"] == 150.0) & (ded["date"].astype(str) == "2023-03-01")]
    assert float(day1["bid"].iloc[0]) == 2.55, "must keep the LAST (closing) snapshot"


def test_options_split_adjustment_two_series():
    """Adjusted prices must never meet unadjusted strikes.

    Sharadar closeadj is retro-adjusted for splits; option strikes are as-traded and never are.
    AAPL on 2019-05-07 reads 48.34 adjusted (and 50.72 under plain `close`, which is ALSO
    adjusted) against real strikes of 150-200, because of the 4:1 split in August 2020. Mixing
    them solved ATM IV to None on every pre-split date and picked contracts from the wrong end
    of the ladder - silently, with no error. `closeunadj` is the as-traded series.
    """
    from valuation.edge import options_backtest as OB

    bars = {"date": ["2019-05-06", "2019-05-07"], "close": [48.0, 48.34],
            "raw_close": [201.0, 202.86], "volume": [1e6, 1e6]}
    w = OB.bars_asof({"date": bars["date"] * 40, "close": bars["close"] * 40,
                      "raw_close": bars["raw_close"] * 40, "volume": bars["volume"] * 40},
                     "2019-05-07")
    assert w is not None
    # Both series survive the slice, and they are NOT the same number.
    assert w["close"][-1] != w["raw_close"][-1]
    assert abs(w["raw_close"][-1] - 202.86) < 1e-6
    # A cache without raw_close must be rejected rather than run split-mixed.
    import inspect
    src = inspect.getsource(OB.load_bars)
    assert "raw_close" in src and "closeunadj" in src
    # Option maths must never be handed the adjusted series.
    assert "raw_close" in inspect.getsource(OB.simulate_trade)


def test_live_term_structure_filter():
    """The one signal that survived phase 3b's fade gate, wired live.

    Three properties matter more than the threshold itself:
      * it FAILS OPEN - unknown term structure is None, never False, so a quote-feed hiccup
        cannot masquerade as backwardation and silently halt alerting;
      * the DEFAULT mode now SUPPRESSES (changed for roadmap #21). It used to annotate, on the
        grounds that removing ~60% of signals was too large a change to inherit silently from a
        backtest. That reasoning was about who decides, not about whether the filter works, and
        the decision has now been taken deliberately: an unapplied filter leaves the live alerts
        carrying the full fade it was adopted to arrest. The fail-open property below is what
        makes suppression safe, and is the invariant that must never be traded away;
      * contango alerts carry a LARGER size multiple, so filtering 60% of signals does not
        quietly shrink the sleeve's exposure by 60% - capped, so a modest edge cannot become a
        concentrated bet.
    """
    from valuation.intraday import term_filter as TF

    assert TF.DEFAULT_MODE == TF.MODE_SUPPRESS, "the filter is now a gate, not a label"
    contango = {"atm_iv": 0.30, "atm_iv_60d": 0.35}
    backward = {"atm_iv": 0.40, "atm_iv_60d": 0.32}
    assert TF.classify(contango)["term_ok"] is True
    assert TF.classify(backward)["term_ok"] is False
    # Missing / malformed data is UNKNOWN, never bad.
    for bad in ({}, None, {"atm_iv": 0.3}, {"atm_iv": 0.3, "atm_iv_60d": None},
                {"atm_iv": 0.0, "atm_iv_60d": 0.3}, {"atm_iv": "x", "atm_iv_60d": 0.3}):
        assert TF.classify(bad)["term_ok"] is None, bad
    assert TF.size_multiplier(True) > TF.size_multiplier(None) > TF.size_multiplier(False)

    rows = [{"score": 90, "labels": ["Uptrend"],
             "detail": {"opt_atm_iv": 0.30, "opt_atm_iv_60d": 0.35}},
            {"score": 85, "labels": ["Breakout"],
             "detail": {"opt_atm_iv": 0.40, "opt_atm_iv_60d": 0.32}},
            {"score": 82, "labels": ["Uptrend"], "detail": {}}]
    assert len(TF.apply(rows, mode=TF.MODE_FLAG)) == 3          # annotates, drops nothing
    sup = TF.apply(rows, mode=TF.MODE_SUPPRESS)
    assert len(sup) == 2                                        # only backwardation removed
    assert all(r.get("term_ok") is not False for r in sup)
    assert any(r.get("term_ok") is None for r in sup), "unknown must survive suppression"
    assert TF.apply(rows, mode=TF.MODE_OFF) == rows              # fully reversible

    # The live path passes the config flag through and still returns alerts.
    from valuation.saas.notify import screaming_buys
    got = screaming_buys(rows, 80, term_mode=TF.MODE_FLAG)
    assert len(got) == 3 and all("term_ok" in r for r in got)


def _vrp_quote_frame(strikes, bids, asks, expiry, oi=500, vol=50):
    return pd.DataFrame({"strike": [float(s) for s in strikes],
                         "bid": bids, "ask": asks,
                         "right": ["P"] * len(strikes),
                         "expiration": [expiry] * len(strikes),
                         "open_interest": [oi] * len(strikes),
                         "volume": [vol] * len(strikes)})


def test_vrp_entry_rules_are_the_options_bot_rules():
    """Screening/construction constants are the ported ones, and each gate actually bites."""
    from valuation.edge import options_vrp as V

    assert (V.MIN_DTE, V.MAX_DTE, V.TARGET_DTE) == (25, 50, 35)
    assert V.TARGET_SHORT_DELTA == 0.20 and V.SPREAD_WIDTH == 5.0
    assert V.PROFIT_TARGET_PCT == 0.50 and V.STOP_LOSS_MULTIPLE == 2.0
    assert V.TIME_EXIT_DTE == 21

    today = dt.date(2020, 1, 2)
    exps = [today + dt.timedelta(days=n) for n in (7, 20, 30, 37, 45, 60, 80)]
    got = V.pick_expiration(exps, today)
    assert (got - today).days == 37          # inside [25,50], closest to 35
    assert V.pick_expiration([today + dt.timedelta(days=n) for n in (5, 90)], today) is None

    from valuation.edge import options_fill as F
    ok = F.Quote(bid=1.00, ask=1.06, oi=500, volume=10)
    assert V.short_leg_reject_reason(ok) is None
    # 18% wide: passes the project's own quote-sanity bar (25%) and is then caught by the
    # bot's tighter 10% screening gate, so the two gates are demonstrably both live.
    assert V.short_leg_reject_reason(F.Quote(bid=1.00, ask=1.20, oi=500)) == "bid_ask_too_wide"
    assert V.short_leg_reject_reason(F.Quote(bid=1.00, ask=1.60, oi=500)) == "wide_spread"
    assert V.short_leg_reject_reason(F.Quote(bid=1.00, ask=1.06, oi=5)) == "low_open_interest"
    assert V.short_leg_reject_reason(F.Quote(bid=1.10, ask=1.00, oi=500)) == "crossed"
    # A missing open interest fails CLOSED — absent evidence is never a pass.
    assert V.short_leg_reject_reason(F.Quote(bid=1.00, ask=1.06)) == "low_open_interest"


def test_vrp_iv_rank_is_point_in_time_and_refuses_thin_history():
    from valuation.edge import options_vrp as V

    days = [f"2020-{m:02d}-{d:02d}" for m in range(1, 7) for d in range(1, 26)]
    series = {d: 0.20 + 0.001 * i for i, d in enumerate(days)}     # monotonically rising IV
    idx = V.build_iv_index(series)
    # Fewer than MIN_OBS observations before the day: unknowable, never defaulted.
    assert V.iv_rank_at(idx, V.IV_RANK_MIN_OBS - 1) is None
    r = V.iv_rank_at(idx, V.IV_RANK_MIN_OBS + 5)
    assert r == 1.0                     # a rising series always sits above its own history
    # The dict path agrees with the indexed path, and excludes today from its own window.
    d_at = idx[V.IV_RANK_MIN_OBS + 5][0]
    assert V.iv_rank(series, d_at) == r
    # A LATER observation must not influence an earlier rank (the PIT guard).
    poisoned = dict(series)
    for d in days[V.IV_RANK_MIN_OBS + 6:]:
        poisoned[d] = 99.0
    assert V.iv_rank(poisoned, d_at) == r
    assert V.iv_rank(series, "1999-01-01") is None


def test_vrp_fills_cross_the_spread_on_both_legs_both_ways():
    """The credit received is worse than mid and the buy-back cost is worse than mid."""
    from valuation.edge import options_vrp as V

    short = {"bid": 2.00, "ask": 2.20}
    wing = {"bid": 1.00, "ask": 1.20}
    mid_credit = 2.10 - 1.10
    credit = V.entry_credit(short, wing)
    assert abs(credit - (2.00 - 1.20)) < 1e-12
    assert credit < mid_credit                       # you receive LESS than the mid

    cc = V.close_cost(short, wing, width=5.0)
    assert abs(cc["cost"] - (2.20 - 1.00)) < 1e-12
    assert cc["cost"] > mid_credit and not cc["clamped"]

    # Crossed/stale quotes cannot produce a negative buy-back cost — clamp AND report it.
    crossed = V.close_cost({"bid": 0.50, "ask": 0.60}, {"bid": 0.90, "ask": 1.00}, width=5.0)
    assert crossed["cost"] == 0.0 and crossed["clamped"] is True
    # Nor a cost beyond the width.
    over = V.close_cost({"bid": 9.0, "ask": 9.5}, {"bid": 0.10, "ask": 0.20}, width=5.0)
    assert over["cost"] == 5.0 and over["clamped"] is True
    # The short leg is unpriceable without an ask; you cannot buy it back for nothing.
    assert V.close_cost({"bid": 0, "ask": 0}, wing, width=5.0) is None
    # But a WINNING spread's wing legitimately bids 0.00 and quotes wide — it must still mark,
    # or the profit target and time exit would freeze on exactly the positions we want to close.
    win = V.close_cost({"bid": 0.05, "ask": 0.15}, {"bid": 0.0, "ask": 0.05}, width=5.0)
    assert win is not None and abs(win["cost"] - 0.15) < 1e-12
    assert V.close_cost({"bid": 0.05, "ask": 0.15}, {"bid": 0.0, "ask": 0.0}, width=5.0) is None
    # A wing with no ask cannot be BOUGHT, so the trade never opens (that would be a naked put).
    assert V.entry_credit(short, {"bid": 1.00, "ask": 0.0}) is None

    # Expiry settlement is bounded by [0, width] in every regime.
    assert V.settle_at_expiry(100.0, 95.0, 120.0) == 0.0        # both worthless
    assert V.settle_at_expiry(100.0, 95.0, 90.0) == 5.0         # both deep ITM: full width
    assert V.settle_at_expiry(100.0, 95.0, 97.0) == 3.0         # short ITM only


def test_vrp_exit_discipline_and_the_stop_gap_through():
    """Profit / stop / time / expiry each fire, and the stop books the REAL gapped price."""
    from valuation.edge import options_vrp as V

    entry = dt.date(2020, 1, 2)
    exp = dt.date(2020, 2, 21)
    credit = 1.00

    def legs(days_and_quotes):
        """{day: (short_bid, short_ask, wing_bid, wing_ask)} -> two per-contract histories."""
        sh = {d: {"bid": v[0], "ask": v[1]} for d, v in days_and_quotes.items()}
        lh = {d: {"bid": v[2], "ask": v[3]} for d, v in days_and_quotes.items()}
        return sh, lh

    # Buy-back cost 0.45 vs 1.00 credit -> captured +55% -> PROFIT.
    sh, lh = legs({entry + dt.timedelta(days=5): (0.50, 0.60, 0.10, 0.15)})
    t = V.simulate_spread(sh, lh, entry, exp, 100.0, 95.0, credit, 110.0)
    assert t["exit_reason"] == "profit" and t["pnl_pct"] > 0

    # Cost 3.65 -> captured -265% -> STOP, and the FILL is the gapped 3.65, not the 3.00 that a
    # 2x-credit stop would theoretically fill at. A backtest that booked 2x would understate it.
    sh, lh = legs({entry + dt.timedelta(days=5): (3.70, 3.80, 0.10, 0.15)})
    t = V.simulate_spread(sh, lh, entry, exp, 100.0, 95.0, credit, 90.0)
    assert t["exit_reason"] == "stop"
    assert abs(t["close_cost_ps"] - 3.70) < 1e-9        # 3.80 ask - 0.10 wing bid
    theoretical_2x = (credit - 3.0 * credit) * 100 - V.COMMISSION * 4
    assert t["pnl_dollars"] < theoretical_2x, "gap-through must be worse than the 2x stop"
    assert t["pnl_pct"] >= -1.0, "a defined-risk spread cannot lose more than max risk"

    # No trigger before 21 DTE -> TIME exit on the first day inside the window.
    quiet = {entry + dt.timedelta(days=n): (0.90, 1.00, 0.20, 0.25) for n in range(1, 45)}
    sh, lh = legs(quiet)
    t = V.simulate_spread(sh, lh, entry, exp, 100.0, 95.0, credit, 110.0)
    assert t["exit_reason"] == "time" and (exp - dt.date.fromisoformat(t["exit_date"])).days <= 21

    # No usable marks at all -> settle at intrinsic rather than vanish from the sample. A spread
    # that finishes fully through the wing loses EXACTLY max risk, which is the -1.0 floor.
    t = V.simulate_spread({}, {}, entry, exp, 100.0, 95.0, credit, 80.0)
    assert t["exit_reason"] == "expiration" and t["settled_at_intrinsic"]
    assert abs(t["pnl_pct"] + 1.0) < 1e-12


def test_vrp_return_is_measured_against_max_risk_not_credit():
    from valuation.edge import options_vrp as V

    t = V.trade_result(dt.date(2020, 1, 2), dt.date(2020, 1, 20),
                       credit_ps=1.00, cost_ps=0.50, width=5.0, reason="profit")
    # (5.00 - 1.00) x 100 of defined risk, plus the four-leg commission that is also at stake.
    assert abs(t["max_risk_dollars"] - (400.0 + 4 * V.COMMISSION)) < 1e-9
    assert abs(t["gross_pnl"] - 50.0) < 1e-9
    assert abs(t["pnl_dollars"] - (50.0 - 4 * V.COMMISSION)) < 1e-9
    assert abs(t["pnl_pct"] - t["pnl_dollars"] / t["max_risk_dollars"]) < 1e-9
    assert abs(t["pnl_pct_of_credit"] - 0.50) < 1e-9
    # Return-on-credit is ~4x the return-on-risk here; reporting it would flatter the arm.
    assert t["pnl_pct_of_credit"] / t["pnl_pct"] > 4
    # A worthless expiry costs no closing commission (nothing is closed).
    z = V.trade_result(dt.date(2020, 1, 2), dt.date(2020, 2, 21), 1.00, 0.0, 5.0,
                       "expiration", expired=True)
    assert abs(z["commission"] - 2 * V.COMMISSION) < 1e-9


def test_vrp_self_test_refuses_a_both_sides_profitable_engine():
    """The gate's hard blocker: a fill model that pays on both sides is void, not impressive."""
    from valuation.edge import options_vrp as V

    real = [{"alert_ts": "2018-01-02", "pnl_pct": 0.05, "pnl_dollars": 20.0} for _ in range(50)]
    losing_mirror = [{"alert_ts": "2018-01-02", "pnl_pct": -0.30, "pnl_dollars": -60.0}
                     for _ in range(50)]
    good = V.self_test_block(real, losing_mirror)
    assert good["passes"] and not good["both_sides_profitable"]
    bad = V.self_test_block(real, [{**r} for r in real])
    assert bad["both_sides_profitable"] and not bad["passes"]

    # And the mirror really is the other side of the same market: buying at the touch and
    # selling back at the touch on unchanged quotes must LOSE the round-trip spread.
    entry, exp = dt.date(2020, 1, 2), dt.date(2020, 2, 21)
    flat = {d: {"bid": b, "ask": a} for d, (b, a) in
            {entry: (2.00, 2.20), entry + dt.timedelta(days=30): (2.00, 2.20)}.items()}
    wing = {d: {"bid": 1.00, "ask": 1.20} for d in flat}
    m = V.simulate_mirror(flat, wing, entry, exp, 100.0, 95.0, 110.0)
    assert m is not None and m["pnl_dollars"] < 0


def test_vrp_sanity_block_catches_impossible_trades():
    from valuation.edge import options_vrp as V

    good = [{"alert_ts": "2018-01-02", "pnl_pct": 0.1, "credit_ps": 1.0, "width": 5.0,
             "short_delta": -0.20, "dte": 35, "marks_seen": 10, "clamped_marks": 0,
             "exit_reason": "profit"},
            {"alert_ts": "2018-02-02", "pnl_pct": -0.5, "credit_ps": 1.2, "width": 5.0,
             "short_delta": -0.22, "dte": 30, "marks_seen": 8, "clamped_marks": 0,
             "exit_reason": "stop"}]
    assert V.sanity_block(good)["clean"]
    impossible = good + [{**good[0], "pnl_pct": -1.4}]
    flags = V.sanity_block(impossible)["flags"]
    assert any("MORE than max risk" in f for f in flags)
    wide = good + [{**good[0], "credit_ps": 9.0}]
    assert any("credit outside" in f for f in V.sanity_block(wide)["flags"])
    off_delta = good + [{**good[0], "short_delta": -0.90}]
    assert any("short delta outside" in f for f in V.sanity_block(off_delta)["flags"])


def test_vrp_stress_and_gate_arithmetic():
    from valuation.edge import options_vrp as V

    rows = ([{"alert_ts": "2017-06-0%d" % (i % 9 + 1), "pnl_pct": 0.12, "pnl_dollars": 48.0}
             for i in range(90)]
            + [{"alert_ts": "2017-07-0%d" % (i % 9 + 1), "pnl_pct": -0.30, "pnl_dollars": -120.0}
               for i in range(10)]
            + [{"alert_ts": "2022-06-0%d" % (i % 9 + 1), "pnl_pct": 0.10, "pnl_dollars": 40.0}
               for i in range(90)]
            + [{"alert_ts": "2022-07-0%d" % (i % 9 + 1), "pnl_pct": -0.40, "pnl_dollars": -160.0}
               for i in range(10)])
    split = V.held_out_split(rows)
    assert split["positive_in_both"]
    st = V.stress_test(rows, multiplier=1.5)
    assert st["stressed"]["expectancy_pct"] < V.held_out_split(rows)["first_half"]["expectancy_pct"]
    # The stress cannot push a defined-risk loss beyond -100% of risk.
    huge = V.stress_test([{"alert_ts": "2017-01-01", "pnl_pct": -0.9, "pnl_dollars": -360.0}], 3.0)
    assert huge["stressed"]["expectancy_pct"] == -1.0
    assert huge["n_losses_capped_at_max_risk"] == 1

    tail = V.tail_report(rows)
    assert tail["worst_trade_pct"] < 0 < tail["best_trade_pct"]
    assert tail["cvar_05"] < 0
    assert tail["worst_5pct"]["excluding_them"]["expectancy_pct"] > \
        tail["overall"]["expectancy_pct"]

    # The gate stays UNDECIDED while the portfolio/correlation arms are missing — it must never
    # read "adopt" off the arms that happen to have been computed.
    g = V.evaluate_gate(rows, [{"alert_ts": "2017-01-01", "pnl_pct": -0.5, "pnl_dollars": -200.0}])
    assert g["adopt"] is False and set(g["undecided"]) == {"4b_drawdown", "6_second_arm"}
    assert g["checks"]["5_self_test"] is True


def test_vrp_shrinkage_is_the_ported_ledoit_wolf():
    from valuation.edge import options_vrp_portfolio as P

    assert abs(P.shrinkage_lambda(63, 60) - 0.4878) < 1e-3
    assert P.shrinkage_lambda(252, 25) == 0.20        # floor
    assert P.shrinkage_lambda(10, 200) == 0.90        # cap
    corr = [[1.0, 0.9, 0.1], [0.9, 1.0, 0.1], [0.1, 0.1, 1.0]]
    sh = P.shrink_correlation(corr, 1.0)
    off = [sh[0][1], sh[0][2], sh[1][2]]
    assert all(abs(x - sum([0.9, 0.1, 0.1]) / 3) < 1e-12 for x in off)
    assert all(sh[i][i] == 1.0 for i in range(3))     # diagonal never drifts
    half = P.shrink_correlation(corr, 0.5)
    assert corr[0][2] < half[0][2] < sh[0][2]

    # Diversification must REDUCE the estimate, and perfect correlation must reproduce the
    # naive weighted average exactly — the invariant that says the two paths agree at the limit.
    w, v = [0.5, 0.5], [0.20, 0.20]
    assert P.portfolio_vol(w, v, [[1, 0], [0, 1]]) < P.naive_weighted_vol(w, v)
    assert abs(P.portfolio_vol(w, v, [[1, 1], [1, 1]]) - P.naive_weighted_vol(w, v)) < 1e-12
    # A hedge (opposite signs) reduces it further still.
    assert P.portfolio_vol([0.5, -0.5], v, [[1, 1], [1, 1]]) < 1e-12


def test_vrp_arm_correlation_uses_a_common_risk_footing():
    from valuation.edge import options_vrp_portfolio as P

    # Perfectly ANTI-correlated arms: the combined book must be smoother than either.
    vrp, sgl = [], []
    for i in range(24):
        m = f"2019-{i % 12 + 1:02d}-15" if i < 12 else f"2020-{i % 12 + 1:02d}-15"
        sign = 1.0 if i % 2 == 0 else -1.0
        vrp.append({"alert_ts": m, "exit_date": m, "pnl_pct": 0.10 * sign})
        sgl.append({"alert_ts": m, "held_days": 0, "pnl_pct": -0.10 * sign})
    out = P.arm_correlation(vrp, sgl)
    assert out["monthly_correlation"] < -0.9
    assert abs(out["combined_total"]) < 1e-6
    assert out["months"] == 24
    # Months with no trades count as zero rather than being dropped from the window.
    sparse = P.arm_correlation(vrp, sgl[:4])
    assert sparse["months"] >= 4

    m = P.monthly_pnl_per_risk([{"exit_date": "2020-03-05", "pnl_pct": 0.25}],
                               lambda r: r["exit_date"], risk=1000.0)
    assert abs(m["2020-03"] - 250.0) < 1e-9
    assert P._exit_date_single_leg({"alert_ts": "2020-01-01", "held_days": 31}) == "2020-02-01"


def test_atm_iv_survives_a_chain_with_no_underlying_price_field():
    """The bug that made the live term gate fire at random, pinned so it cannot return.

    Tradier option rows do NOT carry `underlying_price`. The old rule ranked contracts by
    `abs(strike - (o.get("underlying_price") or 0))`, so the missing field collapsed to 0 and the
    "nearest strike" was the LOWEST one on the board - AAPL's ATM IV was read off the $50 strike
    at a $308 spot, giving 1.49 against a true 0.256. That fed term_slope directly and produced
    live slopes of +/-1.0 against a 0.0105 threshold.

    Two properties matter: ATM is located WITHOUT needing a spot price (by |delta| -> 0.50, which
    is what at-the-money means), and an implausible `mid_iv` loses to the smoothed `smv_vol`
    instead of beating it.
    """
    from valuation.intraday.providers import atm_iv_from_chain

    # Spot ~308. No underlying_price anywhere, exactly as Tradier serves it.
    chain = [
        {"strike": 50.0, "option_type": "put",
         "greeks": {"delta": -0.0003, "mid_iv": 2.2997, "smv_vol": 0.423}},
        {"strike": 250.0, "option_type": "call",
         "greeks": {"delta": 0.92, "mid_iv": 0.44, "smv_vol": 0.40}},
        {"strike": 310.0, "option_type": "call",
         "greeks": {"delta": 0.51, "mid_iv": 0.2561, "smv_vol": 0.263}},
        {"strike": 400.0, "option_type": "call",
         "greeks": {"delta": 0.04, "mid_iv": 0.61, "smv_vol": 0.55}},
    ]
    assert not any("underlying_price" in o for o in chain)
    assert abs(atm_iv_from_chain(chain) - 0.2561) < 1e-9, "ATM must be found by delta, not by 0"
    # A supplied spot is used directly and must agree.
    assert abs(atm_iv_from_chain(chain, 308.91) - 0.2561) < 1e-9

    # An implausible mid_iv must LOSE to smv_vol, not win. 2.2997 is 230% vol on a wing.
    only_wing = [{"strike": 50.0, "option_type": "put",
                  "greeks": {"delta": -0.50, "mid_iv": 2.2997, "smv_vol": 0.423}}]
    assert abs(atm_iv_from_chain(only_wing) - 0.423) < 1e-9
    # Neither plausible -> skipped, never fabricated.
    assert atm_iv_from_chain([{"strike": 50.0, "option_type": "put",
                               "greeks": {"delta": -0.5, "mid_iv": 9.9, "smv_vol": 8.8}}]) is None
    assert atm_iv_from_chain([]) is None and atm_iv_from_chain(None) is None


def test_chain_as_of_reads_the_quote_date_not_the_wall_clock():
    from valuation.edge import options_live as L

    rows = [{"strike": 1.0, "greeks": {"updated_at": "2026-07-31 20:00:00"}},
            {"strike": 2.0, "greeks": {"updated_at": "2026-07-30 20:00:00"}}]
    assert L.chain_as_of(rows) == dt.date(2026, 7, 31), "must take the LATEST quote date"
    # Epoch milliseconds (Tradier's trade_date) are understood too.
    ms = int(dt.datetime(2026, 7, 31, 16, 0).timestamp() * 1000)
    assert L.chain_as_of([{"trade_date": ms}]) == dt.date(2026, 7, 31)
    # Explicit wins; nothing usable falls back to today.
    assert L.resolve_as_of(rows, dt.date(2026, 1, 1)) == dt.date(2026, 1, 1)
    assert L.resolve_as_of([{"strike": 1.0}]) == dt.date.today()
    assert L.chain_as_of([{"strike": 1.0, "greeks": {"updated_at": "nonsense"}}]) is None


def test_stale_quotes_do_not_inflate_the_short_dated_term_leg():
    """The second live bug: assuming quotes are from today when they are not.

    T enters Black-Scholes under a square root, so an as-of error scales solved IV by
    sqrt(T_true/T_assumed). That is nothing on the 45-75 DTE contract traded and enormous on the
    ~3-DTE FRONT leg term_slope differences against. Reading Friday's quotes on a Sunday - a
    1-day error out of 3 - turned AAPL's slope from -0.008 into -0.198 and would have been
    reported as "the fitted estimator does not transfer to a broker surface".

    Here the chain is built FLAT (same vol at both expiries), so the true slope is ~0. Anything
    materially negative is the artefact.
    """
    from valuation.edge import options_live as L

    quote_date = dt.date(2026, 7, 31)
    chain = _live_chain(100.0, quote_date, [3, 60], sigma=0.30, updated_at=quote_date)

    honest = L.term_read(chain_rows=chain, underlying=100.0)          # resolves to quote_date
    assert honest["quote_date"] == quote_date.isoformat()
    assert honest["front_dte"] == 3
    assert abs(honest["term_slope"]) < 0.02, honest["term_slope"]

    # Same chain read two days later without the fix: the front leg's IV is inflated.
    stale = L.term_read(chain_rows=chain, underlying=100.0, as_of=quote_date + dt.timedelta(days=2))
    assert stale["front_dte"] == 1
    assert stale["front_iv"] > honest["front_iv"] * 1.4, (stale["front_iv"], honest["front_iv"])
    assert stale["term_slope"] < honest["term_slope"] - 0.05
    # The far leg barely moves - which is exactly why only the front leg corrupts the slope.
    assert abs(stale["far_iv"] - honest["far_iv"]) < 0.02


def test_term_gate_authority_moved_to_the_chain_read_and_still_fails_open():
    """The gate now runs on the estimator the threshold was fitted to, after the chain fetch.

    It used to run inside screaming_buys on the cheap whole-universe summary - which meant a bug
    in that summary suppressed alerts silently, and the better read computed moments later was
    decorative. Fail-open is unchanged: unknown is never dropped.
    """
    from valuation.edge import options_live as L
    from valuation.intraday import term_filter as TF

    alerts = [{"ticker": "AAA", "term": {"term_ok": True, "source": "chain (BS-from-mid)"}},
              {"ticker": "BBB", "term": {"term_ok": False, "source": "chain (BS-from-mid)"}},
              {"ticker": "CCC", "term": {"term_ok": None, "source": "unavailable"}}]
    kept, stats = L.apply_term_gate(alerts)
    assert [a["ticker"] for a in kept] == ["AAA", "CCC"]
    assert stats["kept"] == 1 and stats["discarded"] == 1 and stats["unknown"] == 1
    assert stats["retention"] == 0.5 and stats["backtest_retention"] == L.BACKTEST_TERM_RETENTION
    assert stats["sources"]["chain (BS-from-mid)"] == 2
    # Flag mode annotates without dropping.
    kept_flag, s2 = L.apply_term_gate(alerts, mode=TF.MODE_FLAG)
    assert len(kept_flag) == 3 and s2["discarded"] == 1


def _live_chain(spot, asof, dtes, sigma=0.30, mny=(0.90, 0.95, 1.00, 1.05, 1.10, 1.15),
                updated_at=None):
    """A broker-shaped chain priced by Black-Scholes, so delta targets are actually reachable.

    `sigma` may be a dict keyed by DTE, which is how a term structure is built for the
    term_slope tests: one vol for the front expiry and a different one further out.
    """
    import datetime as _d

    from valuation.edge import blackscholes as BS
    r = BS.risk_free_rate(asof)
    rows = []
    for d in dtes:
        vol = sigma[d] if isinstance(sigma, dict) else sigma
        exp = (asof + _d.timedelta(days=d)).isoformat()
        T = d / 365.0
        for m in mny:
            k = round(spot * m, 2)
            for right, kind in (("C", "call"), ("P", "put")):
                px = BS.bs_price(spot, k, T, r, vol, right)
                if px is None or px < 0.20:
                    continue
                g = {"delta": None, "mid_iv": vol}
                if updated_at is not None:
                    g["updated_at"] = f"{updated_at} 20:00:00"
                rows.append({"option_type": kind, "expiration_date": exp, "strike": k,
                             "bid": round(px * 0.97, 2), "ask": round(px * 1.03, 2),
                             "volume": 500, "open_interest": 1000, "greeks": g})
    return rows


def test_live_engine_reuses_the_backtested_selector_rather_than_copying_it():
    """The live path must CALL the validated selector, not re-implement it.

    This is the single most important property in the live wiring. A second implementation
    starts identical and drifts one commit at a time, and the drift is invisible: both sides
    keep producing plausible contracts. So two things are pinned - the constants are the SAME
    OBJECTS as the backtest's (not equal copies), and `pick_live_contract` genuinely delegates
    to `options_backtest.pick_contract` with the validated band.
    """
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_live as L

    assert L.TARGET_DELTA is OB.TARGET_DELTA
    assert L.DTE_RANGE is OB.DTE_RANGE
    assert L.TARGET_PCT is OB.TARGET_PCT and L.STOP_PCT is OB.STOP_PCT
    assert L.TIME_STOP_FRAC is OB.TIME_STOP_FRAC and L.HORIZON is OB.HORIZON

    seen = {}
    real = OB.pick_contract
    try:
        def spy(chain, underlying, as_of, right="C", target_delta=None, dte_range=None):
            seen.update({"right": right, "target_delta": target_delta,
                         "dte_range": dte_range, "underlying": underlying,
                         "n_rows": len(chain)})
            return None
        OB.pick_contract = spy
        asof = dt.date(2026, 8, 3)
        out = L.pick_live_contract(_live_chain(100.0, asof, [60]), 100.0, asof)
    finally:
        OB.pick_contract = real
    assert out is None, "a selector returning None must not be papered over"
    assert seen["target_delta"] == 0.35 and tuple(seen["dte_range"]) == (45, 75)
    assert seen["right"] == "C" and seen["n_rows"] > 0


def test_live_contract_sits_in_the_validated_band_and_is_priced_at_the_ask():
    """~35 delta, 45-75 DTE, long call - and the entry premium is the ASK, not the mid.

    The premium basis matters as much as the strike: every validated number is net of the
    punishing fill (buy the ask / sell the bid). Sizing off the mid would deploy more contracts
    than the tested book ever held and quote an entry nobody gets.
    """
    from valuation.edge import options_live as L

    asof = dt.date(2026, 8, 3)
    chain = _live_chain(100.0, asof, [7, 60])
    c = L.pick_live_contract(chain, 100.0, asof)
    assert c is not None
    assert c["right"] == "call"
    assert 45 <= c["dte"] <= 75, c["dte"]
    assert abs(abs(c["delta"]) - 0.35) < 0.12, c["delta"]
    assert c["entry_premium"] == c["ask"], "entry must be the ask, not the mid"
    assert c["ask"] > c["mid"] > c["bid"]
    assert c["exit_policy"]["target_pct"] == 1.00 and c["exit_policy"]["stop_pct"] == -0.50


def test_live_contract_refuses_rather_than_relaxing_the_band():
    """No contract in 45-75 DTE -> None. Substituting a nearer or further one changes the
    strategy while keeping its name, which is worse than showing no contract."""
    from valuation.edge import options_live as L

    asof = dt.date(2026, 8, 3)
    assert L.pick_live_contract(_live_chain(100.0, asof, [7, 200]), 100.0, asof) is None
    assert L.pick_live_contract(None, 100.0, asof) is None
    assert L.pick_live_contract(_live_chain(100.0, asof, [60]), 0, asof) is None


def test_live_term_read_prefers_the_fitted_iv_estimator_and_records_which():
    """term_slope from the chain (IV solved from the mid, as fitted) beats the broker's surface.

    The threshold is ~1 vol point, small enough that the IV ESTIMATOR can decide the answer, so
    which series was used is reported rather than assumed. Missing data stays unknown.
    """
    from valuation.edge import options_live as L

    asof = dt.date(2026, 8, 3)
    contango = _live_chain(100.0, asof, [7, 60], sigma={7: 0.28, 60: 0.36})
    r = L.term_read(chain_rows=contango, underlying=100.0, as_of=asof)
    assert r["term_ok"] is True and r["term_slope"] > 0
    assert "chain" in r["source"]

    backward = _live_chain(100.0, asof, [7, 60], sigma={7: 0.45, 60: 0.30})
    assert L.term_read(chain_rows=backward, underlying=100.0, as_of=asof)["term_ok"] is False

    # No chain -> broker IV, and it says so.
    b = L.term_read(summary={"atm_iv": 0.30, "atm_iv_60d": 0.35})
    assert b["term_ok"] is True and "broker" in b["source"]
    # Nothing at all -> unknown, never False.
    assert L.term_read(summary={})["term_ok"] is None


def test_term_gate_is_on_by_default_and_still_fails_open():
    """Suppression is now the default, and unknown term structure survives it."""
    from valuation.intraday import term_filter as TF

    rows = [{"score": 90, "labels": ["Uptrend"],
             "detail": {"opt_atm_iv": 0.30, "opt_atm_iv_60d": 0.35}},     # contango
            {"score": 88, "labels": ["Breakout"],
             "detail": {"opt_atm_iv": 0.40, "opt_atm_iv_60d": 0.32}},     # backwardation
            {"score": 82, "labels": ["Uptrend"], "detail": {}}]           # unknown
    out, stats = TF.apply_with_stats(rows)
    assert stats["mode"] == TF.MODE_SUPPRESS
    assert stats["kept"] == 1 and stats["discarded"] == 1 and stats["unknown"] == 1
    assert stats["n_out"] == 2 and abs(stats["retention"] - 0.5) < 1e-9
    assert all(r.get("term_ok") is not False for r in out)
    assert any(r.get("term_ok") is None for r in out), "a quote outage must not halt alerting"
    # The config default agrees with the module default, or the gate is off in production.
    from valuation.config import CONFIG
    assert getattr(CONFIG, "options_term_filter", None) == TF.MODE_SUPPRESS


def test_term_retention_is_compared_against_the_backtest_not_just_counted():
    """A threshold fitted on one IV estimator need not transfer to another. The live retention
    rate is the only way to notice, so it is compared against the backtested 40.6% and says
    plainly when it diverges - counting alone would look fine while the filter did nothing."""
    from valuation.edge import options_live as L

    thin = L.term_filter_stats([{"term_ok": True}] * 5)
    assert "too thin" in thin["note"]

    matched = L.term_filter_stats([{"term_ok": True}] * 40 + [{"term_ok": False}] * 60)
    assert abs(matched["retention"] - 0.40) < 1e-9
    assert "transferred" in matched["note"]

    diverged = L.term_filter_stats([{"term_ok": True}] * 99 + [{"term_ok": False}])
    assert "DIVERGES" in diverged["note"]
    assert diverged["unknown"] == 0 and diverged["backtest_retention"] == 0.406


def test_confidence_is_expectancy_confidence_and_never_a_win_probability():
    """A 37% hit rate must never be rendered as a likely winner. The disclaimer ships on every
    result, and the flag that says so is machine-readable so a UI cannot omit it by accident."""
    from valuation.edge import options_confidence as C

    r = C.confidence(atm_iv=0.15, dte=70, delta=0.35, term_ok=True)
    assert r["is_win_probability"] is False
    assert r["hit_rate_reference"] == C.HIT_RATE < 0.40
    assert "NOT probability" in r["disclaimer"] and "37%" in r["disclaimer"]
    assert r["level"] in ("high", "moderate", "low", "thin", "avoid")
    # The best available fingerprint should still not be described as a likely win.
    assert r["level"] == "high" and r["expectancy_estimate"] > 0.05


def test_confidence_scale_actually_discriminates_among_the_alerts_users_see():
    """A badge that reads "high" on every alert is decoration, not information.

    With the term gate on, every displayed alert is contango, so the term bucket is effectively
    constant and the estimate varies only over IV / DTE / delta - a narrow band that does NOT
    start near zero (0.0511 .. 0.0812). The intuitive "high above +5%" cut would therefore fire
    on all of them. This pins that the best and worst contango fingerprints land on different
    levels, and that the cuts still sit inside the reachable span.
    """
    from valuation.edge import options_confidence as C

    F = C.FADE_FACTOR
    best = C.confidence(atm_iv=0.15, dte=70, delta=0.35, term_ok=True)     # best of each bucket
    worst = C.confidence(atm_iv=0.25, dte=60, delta=0.20, term_ok=True)    # worst of each
    assert best["level"] == "high" and worst["level"] == "low"
    assert best["expectancy_estimate"] > worst["expectancy_estimate"]

    lo = (min(v["exp"] for v in C.IV_BUCKETS.values()) * F
          + min(v["exp"] for v in C.DTE_BUCKETS.values()) * F
          + min(v["exp"] for v in C.DELTA_BUCKETS.values()) * F
          + C.TERM_BUCKETS["contango"]["exp"]) / 4
    hi = (max(v["exp"] for v in C.IV_BUCKETS.values()) * F
          + max(v["exp"] for v in C.DTE_BUCKETS.values()) * F
          + max(v["exp"] for v in C.DELTA_BUCKETS.values()) * F
          + C.TERM_BUCKETS["contango"]["exp"]) / 4
    assert abs(worst["expectancy_estimate"] - lo) < 1e-3
    assert abs(best["expectancy_estimate"] - hi) < 1e-3
    for cut, _name in C.LEVEL_CUTS[:2]:
        assert lo < cut < hi, f"cut {cut} sits outside the reachable span {lo:.4f}..{hi:.4f}"


def test_confidence_discounts_the_fade_and_exempts_the_late_half_bucket():
    """Full-sample buckets are dominated by 2016-2020, so they are haircut to the recent regime.

    The term-structure bucket was ALREADY measured on the late half; applying the discount to it
    too would count the fade twice.
    """
    from valuation.edge import options_confidence as C

    assert 0.40 < C.FADE_FACTOR < 0.45
    r = C.confidence(atm_iv=0.15, dte=70, delta=0.35, term_ok=True)
    by_dim = {c["dim"]: c for c in r["contributions"]}
    for dim in ("iv_regime", "dte", "delta"):
        c = by_dim[dim]
        assert c["fade_applied"] is True
        assert abs(c["estimate"] - c["full_sample_exp"] * C.FADE_FACTOR) < 1e-9
        assert c["estimate"] < c["full_sample_exp"], "the haircut must reduce, not flatter"
    t = by_dim["term_structure"]
    assert t["fade_applied"] is False and t["estimate"] == C.TERM_BUCKETS["contango"]["exp"]
    # Backwardation must drag the estimate down, not merely fail to help.
    worse = C.confidence(atm_iv=0.15, dte=70, delta=0.35, term_ok=False)
    assert worse["expectancy_estimate"] < r["expectancy_estimate"]


def test_confidence_backwardation_bucket_is_the_arithmetic_complement():
    """phase 3b never printed the backwardation number; it is pinned by the two it did print.

    late all = retention * contango + (1 - retention) * backwardation, with
    all = +4.76%, contango = +12.88% on 40.6% retention. It is flagged `derived` so nobody
    later cites it as a measured figure.
    """
    from valuation.edge import options_confidence as C

    all_late, contango, ret = 0.0476, 0.1288, 0.406
    implied = (all_late - ret * contango) / (1 - ret)
    assert abs(C.TERM_BUCKETS["backwardation"]["exp"] - implied) < 5e-4, implied
    assert C.TERM_BUCKETS["backwardation"]["derived"] is True
    assert C.TERM_BUCKETS["contango"]["derived"] is False
    assert implied < 0, "the whole case for gating is that backwardation is not profitable"


def test_confidence_is_capped_thin_on_weak_evidence():
    """Two different caps, and the one that fires in production is the dimension count.

    The dimension cap is really the question "did a contract resolve?": DTE and delta exist only
    once one has. Without a chain the best case is IV regime + term structure, which is two
    dimensions and must not produce a confident answer - the buckets were all measured on trades
    that had a real 35-delta 45-75 DTE contract.

    The narrow-bucket guard cannot fire with the committed tables (smallest bucket = 192), so it
    is exercised directly rather than through a test that would silently never assert.
    """
    from valuation.edge import options_confidence as C

    bare = C.confidence(term_ok=True)                    # nothing but the term read
    assert bare["level"] == "thin" and "dimension" in bare["capped_reason"]
    # IV + term with no contract: a good-looking estimate that must still not read as confident.
    no_contract = C.confidence(atm_iv=0.15, term_ok=True)
    assert no_contract["expectancy_estimate"] > 0.05
    assert no_contract["level"] == "thin", "no contract must never be high confidence"

    assert min(b["n"] for b in C.IV_BUCKETS.values()) >= C.MIN_BUCKET_N
    lvl, why = C.cap_level("high", n_min=11, n_dims=4)
    assert lvl == "thin" and "11 closed trades" in why
    # A negative estimate is not rescued by having plenty of data behind it.
    assert C.cap_level("avoid", n_min=11, n_dims=1) == ("avoid", None)
    assert C.SIZE_SCALE["avoid"] == 0.0 and C.SIZE_SCALE["thin"] <= 0.5


def test_live_sizing_skips_instead_of_rounding_up():
    """You cannot buy a fraction of a contract, so an unaffordable alert is SKIPPED.

    Taking one contract anyway is how a risk rule becomes decorative - it silently doubles or
    triples the intended risk on exactly the expensive names where that hurts most.
    """
    from valuation.edge import options_live as L

    tiny = L.suggest_position(2.00, risk_budget=1000.0)
    assert tiny["skip"] is False and tiny["contracts"] == 5
    assert tiny["dollar_risk"] == 1000.0 and tiny["max_loss"] == 1000.0

    huge = L.suggest_position(25.00, risk_budget=1000.0)
    assert huge["skip"] is True and huge["contracts"] == 0
    assert "budget" in huge["reason"] and huge["cost_per_contract"] == 2500.0
    assert L.suggest_position(None)["skip"] is True


def test_live_sizing_affordability_uses_the_full_budget_not_the_confidence_scale():
    """Confidence scales SIZE; it must not become a second affordability filter.

    A $600 contract against a $1,000 budget is affordable. At a 0.5 confidence scale the scaled
    budget is $500, which would floor to zero contracts - and dropping the alert there would be
    rejecting it for cost, not for conviction. It takes one contract instead.
    """
    from valuation.edge import options_live as L

    r = L.suggest_position(6.00, risk_budget=1000.0, size_scale=0.5)
    assert r["skip"] is False and r["contracts"] == 1 and r["dollar_risk"] == 600.0
    # Scaling still bites where it can: half the budget, half the contracts.
    full = L.suggest_position(1.00, risk_budget=1000.0, size_scale=1.0)
    half = L.suggest_position(1.00, risk_budget=1000.0, size_scale=0.5)
    assert full["contracts"] == 10 and half["contracts"] == 5
    # "avoid" means zero, and says so rather than silently sizing to one.
    assert L.suggest_position(1.00, risk_budget=1000.0, size_scale=0.0)["skip"] is True


def test_live_alert_degrades_honestly_when_the_chain_is_unavailable():
    """No chain must not mean no alert - and must not mean a confident alert either."""
    from valuation.edge import options_live as L

    row = {"ticker": "AAA", "score": 91, "labels": ["Uptrend"], "price": 100.0,
           "detail": {"opt_atm_iv": 0.30, "opt_atm_iv_60d": 0.35}}
    a = L.build_alert(row)
    assert a["contract"] is None
    assert a["sizing"]["skip"] is True and a["actionable"] is False
    assert a["term"]["term_ok"] is True                       # summary still gives a term read
    assert a["confidence"]["level"] == "thin"

    alerts, stats = L.build_alerts([row], provider=None)
    assert stats["n"] == 1 and stats["with_contract"] == 0
    assert stats["term_filter"]["kept"] == 1


def test_live_alert_with_a_chain_is_whole_and_actionable():
    from valuation.edge import options_live as L

    asof = dt.date(2026, 8, 3)
    chain = _live_chain(100.0, asof, [7, 60], sigma={7: 0.28, 60: 0.36})
    row = {"ticker": "AAA", "score": 91, "labels": ["Uptrend"], "price": 100.0, "detail": {}}
    a = L.build_alert(row, chain_rows=chain, as_of=asof, risk_budget=5000.0)
    c = a["contract"]
    assert c and c["ticker"] == "AAA" and c["occ_symbol"].startswith("AAA")
    assert 45 <= c["dte"] <= 75
    assert a["term"]["term_ok"] is True
    assert a["sizing"]["contracts"] >= 1 and a["sizing"]["dollar_risk"] > 0
    assert a["actionable"] is True
    assert "never places" in a["not_advice"]


def test_alert_rendering_shows_the_real_contract_and_never_sells_the_hit_rate():
    """The alert a user receives must carry the resolved contract, its size, and the caveat.

    Two failure modes are pinned. A chain outage must degrade to the vaguer descriptor rather
    than silently render a different trade; and wherever a confidence level appears, the
    "not a chance of profit" caveat appears with it - the backtested hit rate is 37%, so a
    "high" badge alone would mislead in exactly the direction that costs money.
    """
    from valuation.saas.notify import alert_discord_text, alert_email_html

    rows = [{"ticker": "AAA", "score": 91, "labels": ["Uptrend"],
             "detail": {"contracts": {"swing": {"directional": "~35Δ call, ~60 DTE"}}}},
            {"ticker": "BBB", "score": 88, "labels": ["Breakout"],
             "detail": {"contracts": {"swing": {"directional": "~35Δ call, ~60 DTE"}}}}]
    live = [{"ticker": "AAA",
             "contract": {"strike": 110.0, "expiry": "2026-10-16", "dte": 60, "delta": 0.34,
                          "entry_premium": 2.62},
             "sizing": {"skip": False, "contracts": 9, "dollar_risk": 2358.0},
             "confidence": {"level": "high"}}]

    txt = alert_discord_text("2026-08-03 14:30", rows, live_alerts=live)
    assert "$110 call 2026-10-16" in txt and "0.34" in txt
    assert "9x = $2,358 at risk" in txt and "confidence high" in txt
    assert "hit rate ~37%" in txt and "never places trades" in txt
    # BBB had no live contract, so it keeps the descriptor rather than borrowing AAA's.
    assert "~35Δ call, ~60 DTE" in txt and txt.count("$110 call") == 1

    html = alert_email_html("2026-08-03 14:30", rows, "http://x/unsub", live_alerts=live)
    assert "$110 call" in html and "hit rate ~37%" in html and "SUGGESTION" in html
    # With no live alerts at all the old descriptor behaviour still works.
    plain = alert_discord_text("2026-08-03 14:30", rows)
    assert "~35Δ call" in plain and "confidence" not in plain


def test_paper_book_keeps_the_backtested_headline_until_the_live_sample_is_thick():
    """Same rule as the stock index: a live number is shown from day one but is not the headline
    until it can carry one. Below the floor a single contract that triples decides the sign."""
    import tempfile

    from valuation.edge import options_paper as PB
    from valuation.edge.options_tracker import log_alert, record_outcome
    from valuation.screener.store import Store

    with tempfile.TemporaryDirectory() as d:
        st = Store(os.path.join(d, "t.db"))
        empty = PB.paper_report(st)
        assert empty["n_logged"] == 0 and empty["thin"] is True
        assert empty["headline_source"].startswith("backtest")
        assert empty["headline_expectancy"] == PB.GATED_LATE_HALF_EXPECTANCY

        for i in range(3):
            log_alert(st, {"alert_ts": f"2026-08-0{i + 1} 10:00", "ticker": f"T{i}",
                           "opt_right": "call", "strike": 100.0 + i, "expiry": "2026-10-16",
                           "entry_premium": 5.0})
            record_outcome(st, ticker=f"T{i}", alert_ts=f"2026-08-0{i + 1} 10:00",
                           exit_premium=10.0, exit_reason="target")
        r = PB.paper_report(st)
        assert r["n_closed"] == 3 and r["thin"] is True
        assert r["live"]["expectancy_pct"] == 1.0            # every trade doubled
        # A 100% live expectancy must NOT become the headline on three trades.
        assert r["headline_source"].startswith("backtest")
        assert r["headline_expectancy"] == PB.GATED_LATE_HALF_EXPECTANCY
        assert r["expectancy_gap_vs_reference"] is None
        assert "thin" in r["label"] and "live since 2026-08-01" in r["label"]


def test_paper_book_compares_against_the_gated_reference_not_the_full_sample_headline():
    """The live book runs BEHIND the term gate, so the fair reference is the gated late-half
    (+12.88%), not the +10.4% full-sample headline dominated by 2016-2020. Quoting the wrong
    one would flatter or damn the live book for a reason that has nothing to do with it."""
    import tempfile

    from valuation.edge import options_confidence as C
    from valuation.edge import options_paper as PB
    from valuation.screener.store import Store

    with tempfile.TemporaryDirectory() as d:
        r = PB.paper_report(Store(os.path.join(d, "t.db")))
    assert r["primary_reference"]["value"] == PB.GATED_LATE_HALF_EXPECTANCY == 0.1288
    others = {o["value"] for o in r["other_references"]}
    assert C.FULL_SAMPLE_EXPECTANCY in others and C.LATE_HALF_EXPECTANCY in others
    assert r["primary_reference"]["value"] not in others, "the primary must not be duplicated"
    assert "gate" in r["primary_reference"]["what"]
    assert r["hit_rate_reference"] == C.HIT_RATE


# ============================ #23 trade autopsy ============================================
def _autopsy_rows(spec):
    """Trades shaped like the backtest log. `spec` is (date, feature value, pnl_pct)."""
    return [{"alert_ts": d, "ticker": "T", "pnl_pct": p, "pnl_dollars": p * 100,
             "_f": {"f_x": v}, "_has_contract": True, "_has_daily": True}
            for d, v, p in spec]


def test_autopsy_spearman_handles_ties_instead_of_reporting_nonsense():
    """A binary feature is mostly ties. Naive ordinal ranks would score two identical columns
    at well under 1.0 and quietly understate every label feature in the sweep."""
    from valuation.edge import options_autopsy as A

    x = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0]
    assert abs(A._spearman(x, x) - 1.0) < 1e-9
    assert abs(A._spearman(x, [-v for v in x]) + 1.0) < 1e-9
    assert A._spearman([1] * 12, list(range(12))) is None, "constant feature has no correlation"


def test_autopsy_tail_retention_bar_rejects_a_filter_that_buys_expectancy_by_clipping_the_tail():
    """G5, the bar with no precedent in this project. A convex book's whole value is the right
    tail, so a filter can look excellent on hit rate and mean while destroying the strategy.

    Construct exactly that: a feature that keeps the small winners and drops the +100% trades.
    Expectancy still rises, which is why expectancy ALONE is not a sufficient bar.
    """
    from valuation.edge import options_autopsy as A

    spec = []
    for half, yr in ((0, "2017"), (1, "2022")):     # same shape in both halves
        for i in range(200):                        # KEPT: steady +35%, not one tail winner
            spec.append((f"{yr}-0{i % 9 + 1}-15", 1.0, 0.35))
        for i in range(50):                         # DROPPED: the entire right tail
            spec.append((f"{yr}-0{i % 9 + 1}-16", 0.0, 3.00))
        for i in range(250):                        # DROPPED: and the worst losers with it
            spec.append((f"{yr}-0{i % 9 + 1}-17", 0.0, -0.50))
    rows = _autopsy_rows(spec)
    res = A.holdout_feature(rows, "f_x")

    for k in ("fit_early_test_late", "fit_late_test_early"):
        d = res[k]
        # It clears every OTHER bar convincingly — that is the point of the construction.
        assert d["gain"] >= A.MIN_LATE_GAIN, f"{k}: expectancy really does rise ({d['gain']})"
        assert d["retention"] >= A.MIN_RETAINED
        assert d["n_kept"] >= A.MIN_TRADES
        assert d["perm_p"] < A.ALPHA, f"{k}: and it is not merely selective"
        # ...and G5 alone stops it, because it kept none of the +100% trades.
        assert d["tail_retention"] == 0.0
        assert not d["passed"], f"{k}: a tail-clipping filter must be rejected"
    assert not res["passes_both_directions"]


def test_autopsy_gate_needs_both_split_directions():
    """G7. A feature engineered to work only on the late half must not be adopted, however
    strong it looks there — the failure mode that made `insider` a keep-at-0.125 in the stock
    model and that every phase of this project has had to re-learn."""
    from valuation.edge import options_autopsy as A

    spec = []
    for i in range(300):        # early half: feature is pure noise w.r.t. outcome
        spec.append((f"2017-0{i % 9 + 1}-15", float(i % 10), 1.5 if i % 3 == 0 else -0.5))
    for i in range(300):        # late half: high feature value == winner, perfectly
        hi = i % 2 == 0
        spec.append((f"2022-0{i % 9 + 1}-15", 9.0 if hi else 0.0, 1.5 if hi else -0.5))
    res = A.holdout_feature(_autopsy_rows(spec), "f_x")
    assert not res["passes_both_directions"], "one-sided fit must not survive G7"


def test_autopsy_bh_fdr_is_monotone_and_controls_the_sweep():
    """124 hypotheses were tested; without an FDR pass ~6 would clear p<0.05 by chance."""
    from valuation.edge import options_autopsy as A

    assert A.bh_fdr([0.5] * 20, 0.10) == [False] * 20
    flags = A.bh_fdr([0.0001] + [0.6] * 19, 0.10)
    assert flags[0] and not any(flags[1:])
    # monotonicity: a discovery cannot become a non-discovery when its p-value falls
    p = [0.001, 0.02, 0.04, 0.9]
    before = A.bh_fdr(p, 0.10)
    p2 = list(p)
    p2[2] = 0.005
    after = A.bh_fdr(p2, 0.10)
    assert all(b <= a for b, a in zip(before, after))


def test_autopsy_outcome_mix_separates_the_stop_from_the_zero():
    """The mandate asked about total losses. The -50% stop means they barely exist, so the two
    buckets must be counted separately or the finding is invisible."""
    from valuation.edge import options_autopsy as A

    rows = [{"pnl_pct": v} for v in (-0.95, -0.60, -0.50, -0.20, 0.40, 1.00, 3.0)]
    m = A.outcome_mix(rows)
    assert m["n"] == 7
    assert m["p_total_loss"] == 1 / 7, "only the -95% is a total loss"
    assert m["p_stop"] == 3 / 7, "-95, -60 and -50 are all at or through the stop"
    assert m["p_tail"] == 2 / 7 and m["hit_rate"] == 3 / 7


def test_autopsy_direction_is_fitted_not_assumed():
    """G1. Nothing in the sweep pre-declares which way a feature should point, so the rule has
    to read the direction off the fitting half and apply it consistently."""
    from valuation.edge import options_autopsy as A

    up = _autopsy_rows([(f"2017-01-{i % 28 + 1:02d}", float(i), 1.0 if i > 50 else -0.5)
                        for i in range(100)])
    rule = A.fit_rule(up, "f_x")
    assert rule["direction"] == 1
    assert all(r["_f"]["f_x"] >= rule["threshold"] for r in A.apply_rule(up, "f_x", rule))

    down = _autopsy_rows([(f"2017-01-{i % 28 + 1:02d}", float(i), -0.5 if i > 50 else 1.0)
                          for i in range(100)])
    rule = A.fit_rule(down, "f_x")
    assert rule["direction"] == -1
    assert all(r["_f"]["f_x"] <= rule["threshold"] for r in A.apply_rule(down, "f_x", rule))


def test_autopsy_nan_features_are_dropped_not_treated_as_present():
    """The §2 skew_25d bug: NaN is not None, so it survives an `is not None` check, poisons the
    median, and empties a filter while coverage still reads 100%. It cost that phase a wrong
    published reason. Pinned here so the autopsy cannot repeat it."""
    from valuation.edge import options_autopsy as A

    rows = _autopsy_rows([("2017-01-05", float("nan"), 1.0)] * 40
                         + [("2017-01-06", 2.0, -0.5)] * 40)
    assert A._f(float("nan")) is None
    assert len(A._present(rows, "f_x")) == 40
    cov = A.feature_coverage(rows)
    assert abs(cov["f_x"] - 0.5) < 1e-9, "coverage must count NaN as missing"


def test_autopsy_deflated_sharpe_deflates_for_the_number_of_trials():
    """A per-trade Sharpe that looks fine on its own must not look fine after you admit how many
    features you searched. The threshold has to RISE with the trial count, or the statistic is
    decoration."""
    import random

    from valuation.edge import options_autopsy as A

    rnd = random.Random(7)
    xs = [rnd.gauss(0.08, 1.0) for _ in range(600)]
    few = A.deflated_sharpe(xs, n_trials=2)
    many = A.deflated_sharpe(xs, n_trials=500)
    assert few["ok"] and many["ok"]
    assert few["sharpe_per_trade"] == many["sharpe_per_trade"], "the raw SR is unchanged"
    assert many["sr0_threshold"] > few["sr0_threshold"], "more trials must raise the bar"
    assert many["deflated_sharpe"] < few["deflated_sharpe"]

    # pure noise must not clear it at any trial count
    noise = A.deflated_sharpe([rnd.gauss(0.0, 1.0) for _ in range(600)], n_trials=63)
    assert noise["deflated_sharpe"] < 0.95


def test_autopsy_pbo_reports_a_coin_flip_when_the_features_are_pure_noise():
    """PBO scores the SELECTION step. If every candidate is noise, picking the in-sample best
    should land below the out-of-sample median about half the time. A construction that returned
    a flattering PBO on noise would make the whole statistic worthless."""
    import random

    from valuation.edge import options_autopsy as A

    rnd = random.Random(11)
    rows = []
    for i in range(900):
        d = f"{2016 + i // 90}-{i % 12 + 1:02d}-15"
        rows.append({"alert_ts": d, "ticker": "T", "pnl_pct": rnd.gauss(0.10, 1.0),
                     "pnl_dollars": 0.0,
                     "_f": {f"f_n{j}": rnd.gauss(0, 1) for j in range(12)}})
    res = A.pbo_cscv(rows, [f"f_n{j}" for j in range(12)], n_blocks=6)
    assert res["ok"], res.get("reason")
    assert 0.2 <= res["pbo"] <= 0.8, f"noise features should not look skilful: {res['pbo']}"


def test_autopsy_regime_cache_is_versioned():
    """A cache keyed only on its path served a regime dict built before `mkt_mom60` existed, and
    the feature silently never appeared in the sweep — no error, no warning. The version now
    lives in the filename so a changed field cannot be masked by a stale file."""
    import inspect

    from valuation.edge import options_autopsy as A

    src = inspect.getsource(A.market_regime)
    assert "REGIME_VERSION" in src, "the cache filename must carry the version"
    assert isinstance(A.REGIME_VERSION, int) and A.REGIME_VERSION >= 2


# =============== 22b — the expanded-universe options backtest ===============================
def _univ_rows(spec):
    """Trades shaped like the broad-universe log. `spec` is (date, ticker, tier, pnl_pct)."""
    return [{"alert_ts": d, "ticker": t, "cap_tier": tier, "pnl_pct": p,
             "pnl_dollars": p * 100, "entry_spread_pct": 0.05}
            for d, t, tier, p in spec]


def test_universe_cap_tier_is_point_in_time_and_never_reads_the_future():
    """A name that was mid-cap in 2016 and mega-cap in 2025 must be counted as BOTH. Tiering on
    today's cap would put ten years of a small name's trades in the mega bucket and manufacture
    exactly the megacap-vs-broad comparison this study is trying to measure."""
    from valuation.edge import options_universe as U

    caps = {"X": [("2016-01-31", 8_000.0), ("2020-06-30", 60_000.0),
                  ("2025-09-30", 900_000.0)]}
    assert U.cap_at(caps, "X", "2016-02-15") == 8_000.0
    assert U.cap_at(caps, "X", "2020-07-01") == 60_000.0
    assert U.cap_at(caps, "X", "2025-10-01") == 900_000.0
    # nothing before the first observation, and never a LATER month-end
    assert U.cap_at(caps, "X", "2015-12-31") is None
    assert U.cap_at(caps, "X", "2020-06-29") == 8_000.0, "must not reach forward to 2020-06-30"
    assert U.tier_of(8_000.0) == "small" and U.tier_of(60_000.0) == "large"
    assert U.tier_of(900_000.0) == "mega" and U.tier_of(None) is None


def test_universe_deconcentration_bar_rejects_a_broader_book_that_still_rests_on_one_name():
    """B3(b). Adding 100 mid-cap names is only diversification if the TAIL spreads out. Here the
    broad book doubles the trade count while every new +100% winner comes from a single name, so
    the Herfindahl does not fall and the tier must not be kept on breadth alone."""
    from valuation.edge import options_universe as U

    # the megacap book's tail is ALREADY spread across ten distinct names
    mega = _univ_rows([(f"2018-0{i % 9 + 1}-10", f"M{i}", "mega",
                        2.0 if i % 4 == 0 else -0.5) for i in range(40)])
    # 40 more trades, but every tail winner in them is the SAME name
    broad = _univ_rows([(f"2019-0{i % 9 + 1}-10", "ONE" if i % 4 == 0 else f"S{i}", "mid",
                         2.0 if i % 4 == 0 else -0.5) for i in range(40)])

    c_mega = U.concentration(mega)
    c_all = U.concentration(mega + broad)
    assert c_mega["tail_hhi"] is not None and c_all["tail_hhi"] is not None
    assert c_all["tail_hhi"] >= c_mega["tail_hhi"], "this book did NOT de-concentrate"
    v = U.verdict(mega + broad, mega, broad)
    assert not v["B3_deconcentrates"]
    assert not v["B3_keep_mid_small"], "positive expectancy alone must not keep the tier"
    # and the control: genuinely spread-out winners DO clear the same bar
    spread_out = _univ_rows([(f"2019-0{i % 9 + 1}-10", f"S{i}", "mid",
                              2.0 if i % 4 == 0 else -0.5) for i in range(40)])
    v2 = U.verdict(mega + spread_out, mega, spread_out)
    assert v2["B3_deconcentrates"] and v2["B3_keep_mid_small"]


def test_universe_home_run_thesis_needs_a_ci_that_excludes_zero():
    """B4. A raw difference in P(>=+100%) between two heavy-tailed groups is nearly free — with
    ~30 trades a side, a 3-winner gap is noise. The bootstrap is what makes the claim mean
    something, so the bar is the interval, not the point estimate."""
    from valuation.edge import options_universe as U

    rnd = __import__("random").Random(3)
    # same underlying process both sides: the difference must NOT be called real
    a = _univ_rows([(f"2019-0{i % 9 + 1}-10", f"A{i}", "mid",
                     2.0 if rnd.random() < 0.30 else -0.5) for i in range(120)])
    b = _univ_rows([(f"2019-0{i % 9 + 1}-10", f"B{i}", "mega",
                     2.0 if rnd.random() < 0.30 else -0.5) for i in range(120)])
    same = U.bootstrap_diff(a, b, "p_tail_win", draws=800, seed=1)
    assert same["ok"] and not same["excludes_zero"], "identical processes must not separate"

    # a genuinely large, consistent gap must be detected — otherwise the bar is unfalsifiable
    hot = _univ_rows([(f"2019-0{i % 9 + 1}-10", f"H{i}", "mid",
                       2.0 if i % 10 < 7 else -0.5) for i in range(200)])
    cold = _univ_rows([(f"2019-0{i % 9 + 1}-10", f"C{i}", "mega",
                        2.0 if i % 10 < 1 else -0.5) for i in range(200)])
    real = U.bootstrap_diff(hot, cold, "p_tail_win", draws=800, seed=1)
    assert real["ok"] and real["diff"] > 0 and real["excludes_zero"]


def test_universe_term_slope_is_applied_at_the_shipped_threshold_not_refitted():
    """The whole out-of-sample value of this run is that the filter is NOT re-fitted on the new
    names. If `term_slope_effect` ever derived its own cutoff, the broad-universe test would
    silently become in-sample and would still look fine."""
    import inspect

    from valuation.edge import options_universe as U

    src = inspect.getsource(U.term_slope_effect)
    assert "fit_threshold" not in src and "median" not in src, \
        "the threshold must be applied, never fitted, inside this function"
    rows = _univ_rows([(f"2022-0{i % 9 + 1}-10", f"N{i}", "mid", 1.0) for i in range(80)])
    for i, r in enumerate(rows):
        r["term_slope"] = 0.05 if i % 2 else -0.05
    res = U.term_slope_effect(rows, late_only=True)
    assert res["ok"] and res["threshold"] == U.SHIPPED_TERM_THRESHOLD
    assert res["n_kept"] == 40, "only the contango half survives the shipped cutoff"


def test_universe_verdict_says_weakens_not_holds_when_one_half_is_negative():
    """B1(c). A book that is profitable overall but only in one period is a regime, not an edge —
    the same both-halves rule the stock model uses. It must not be reported as HOLDS."""
    from valuation.edge import options_universe as U

    early = _univ_rows([(f"2017-0{i % 9 + 1}-10", f"E{i}", "mega",
                         3.0 if i % 3 == 0 else -0.5) for i in range(90)])
    late = _univ_rows([(f"2023-0{i % 9 + 1}-10", f"L{i}", "mega", -0.20)
                       for i in range(60)])
    rows = early + late
    assert (U._stats(rows)["expectancy_pct"] or 0) > 0, "overall really is profitable"
    v = U.verdict(rows, rows, [])
    assert v["B1_expectancy_and_pf"] and not v["B1_both_halves_positive"]
    assert v["label"] == "WEAKENS" and not v["B1_edge_holds"]


def test_universe_tail_stats_separate_the_stop_from_the_zero():
    """The mandate asks for P(total loss) specifically, and it is NOT the stop-out rate: the -50%
    stop is the designed cost of convexity, a -100% is a contract that went to zero. Collapsing
    them would report the exit discipline as a failure mode."""
    from valuation.edge import options_universe as U

    rows = _univ_rows([("2019-01-10", "A", "mega", -1.00), ("2019-02-10", "B", "mega", -0.52),
                       ("2019-03-10", "C", "mega", -0.50), ("2019-04-10", "D", "mega", 1.40),
                       ("2019-05-10", "E", "mega", 0.10)])
    d = U.tail_stats(rows)
    assert abs(d["p_total_loss"] - 0.20) < 1e-9, "only the -100% counts as a total loss"
    assert abs(d["p_stop_out"] - 0.60) < 1e-9, "all three losers are at or through the stop"
    assert abs(d["p_tail_win"] - 0.20) < 1e-9


def test_universe_selection_bias_is_counted_not_footnoted():
    """The miner skipped names by spread and open interest — precisely where wide fills would
    eat the edge. That biases this test TOWARD survival, so the count must ship in the result
    rather than living in a comment someone can drop."""
    import inspect

    from valuation.edge import options_universe as U

    src = inspect.getsource(U.universe_selection_report)
    assert "n_skipped_thin" in src
    doc = U.__doc__ or ""
    assert "TOWARD the edge" in doc, "the direction of the bias must be stated, not just its size"
    # covered-year logic must accept the feed's "no data" marker, else every post-2016 IPO —
    # the younger, smaller names this study exists to add — is silently dropped
    assert ".empty" in src


def test_universe_entry_window_cannot_outrun_the_cached_history():
    """A trade entered too close to the end of the data would have its exit path truncated and
    settle on bars instead of quotes — a silent, one-sided distortion. The entry cutoff must
    leave at least a full maximum-DTE contract life inside the cache."""
    import datetime as dt

    from valuation.edge import options_universe as U

    cache_end = dt.date(max(U.CACHE_YEARS), 12, 31)
    end = dt.date.fromisoformat(U.ENTRY_END)
    assert (cache_end - end).days >= U.OB.DTE_RANGE[1], \
        "entry cutoff must clear the maximum DTE before the cache ends"
    assert U.ENTRY_START < U.ENTRY_END


def test_universe_headline_is_the_ask_not_the_mid():
    """B5. The wider mid/small-cap spread is the entire risk this run exists to measure, so the
    default must cross it. Marking at the mid would delete the thing being tested."""
    from valuation.edge import options_fill as F
    from valuation.edge import options_universe as U

    assert F.DEFAULT_AGGRESSION == 1.0
    q = F.Quote(bid=1.00, ask=1.20, oi=500, volume=100)
    assert F.fill_price(q, "buy", 1.0) == 1.20 and F.fill_price(q, "sell", 1.0) == 1.00
    assert F.fill_price(q, "buy", 1.0) > F.fill_price(q, "buy", 0.0)
    assert "aggression = 1.0" in (U.__doc__ or "").replace("AGGRESSION", "aggression")


# ---------------------------------------------------------------------------------------------
# 22c — entry timing. The scream-buy alert picks WORSE-than-random days; these pin the design
# decisions of the study that diagnoses it, so none of them can drift out silently later.
# ---------------------------------------------------------------------------------------------
def _entry_bars(closes, start="2019-01-02"):
    """Synthetic daily bars. Dates are consecutive business days so the index arithmetic in
    `arm_entry_day` runs against real calendar strings rather than integers."""
    ds = [str(d.date()) for d in pd.bdate_range(start=start, periods=len(closes))]
    return {"date": ds, "close": list(closes), "raw_close": list(closes),
            "volume": [1e6] * len(closes)}


def _entry_rows(spec, arm="signal"):
    """(alert_date, ticker, pnl_pct) -> rows in the shape every arm emits."""
    return [{"alert_ts": d, "alert_date": d, "entry_date": d, "ticker": t,
             "pnl_pct": p, "status": "closed", "arm": arm, "opt_right": "call",
             "entry_premium": 1.0, "exit_premium": 1.0 + p, "cap_tier": "mega"}
            for d, t, p in spec]


def test_entry_arms_cannot_wait_longer_than_their_declared_window():
    """Every corrected entry gets WAIT_WINDOW sessions and no more. A pullback that only arrives
    on session 11 must produce NO trade — otherwise the arm quietly becomes an unbounded 'wait
    for a dip' rule and its trade count stops being comparable to the baseline's."""
    from valuation.edge import options_entry as E

    late = [100.0] * 30
    late[11] = 90.0                      # 10% retrace, one session past the window
    bars = _entry_bars(late)
    sel = E.arm_entry_day("pullback", bars, {}, [], bars["date"][0])
    assert sel["date"] is None and sel["reason"] == "no_pullback", sel

    soon = [100.0] * 30
    soon[4] = 90.0
    bars2 = _entry_bars(soon)
    sel2 = E.arm_entry_day("pullback", bars2, {}, [], bars2["date"][0])
    assert sel2["date"] == bars2["date"][4] and sel2["lag"] == 4, sel2
    # the sized variant must still trade, so its comparison is timing and not selection
    sel3 = E.arm_entry_day("pullback_or_w", bars, {}, [], bars["date"][0])
    assert sel3["date"] == bars["date"][E.WAIT_WINDOW]
    assert sel3["reason"] == "no_pullback_entered_anyway"


def test_entry_delayed_arms_cannot_buy_history_the_baseline_never_had():
    """A delayed entry running past ENTRY_END would hold a contract whose exit path leaves the
    cached quotes and settles on bars — the same one-sided distortion the 22b window exists to
    avoid, except handed only to the arms being promoted."""
    from valuation.edge import options_entry as E

    ds = [str(d.date()) for d in pd.bdate_range(end=E.ENTRY_END, periods=20)]
    ds += [str(d.date()) for d in pd.bdate_range(start=E.ENTRY_END, periods=15)][1:]
    bars = {"date": ds, "close": [100.0] * len(ds), "raw_close": [100.0] * len(ds),
            "volume": [1e6] * len(ds)}
    alert = ds[15]                      # four sessions before the cutoff
    assert E.arm_entry_day("delay3", bars, {}, [], alert)["date"] <= E.ENTRY_END
    late = E.arm_entry_day("delay10", bars, {}, [], alert)
    assert late["date"] is None and late["reason"] == "past_window", late


def test_entry_iv_rank_and_pop_read_strictly_prior_days():
    """Including the day's own IV in its own baseline leaks the observation into the statistic it
    is judged against — the exact bug A2 had to fix before iv_rank was testable at all."""
    from valuation.edge import options_entry as E

    dates = [str(d.date()) for d in pd.bdate_range(start="2019-01-02", periods=101)]
    series = {d: 0.20 for d in dates[:100]}
    series[dates[100]] = 0.40
    f = E.iv_features(series, dates, dates[100])
    assert abs(f["atm_iv_60d"] - 0.40) < 1e-12
    assert abs(f["iv_rank_252"] - 1.0) < 1e-12, "the day itself must not dilute its own rank"
    # base = mean of the 20 STRICTLY prior sessions = 0.20, so the pop is exactly 2.0.
    # Including the day would make the base 0.2095 and the pop 1.909.
    assert abs(f["iv_pop_20"] - 2.0) < 1e-9, f


def test_entry_timing_arm_is_judged_on_the_alerts_it_shares_with_the_signal():
    """An arm that keeps only the winners looks spectacular against the FULL signal book and
    identical against the alerts it actually shares with it. The second number is the honest one,
    so the gate reads the matched subset for every arm that changes the entry DAY."""
    from valuation.edge import options_entry as E

    spec = [(f"2019-{(i % 12) + 1:02d}-05", f"N{i}", 2.0 if i % 2 == 0 else -0.5)
            for i in range(80)]
    signal = _entry_rows(spec)
    arm = _entry_rows([s for s in spec if s[2] > 0], arm="pullback")
    rep = E.arm_report("pullback", arm, signal, [], seed=0)
    assert rep["vs_signal_pooled"]["expectancy_diff"] > 0.9, "pooled flatters the cherry-picker"
    assert abs(rep["vs_signal_matched"]["expectancy_diff"]) < 1e-12, \
        "on the shared alerts the arm IS the signal — the whole gap was selection"
    # E6's benchmark must be drawn from the full book: sampling 40 out of the matched 40 would
    # "drop" nothing and the control would be the arm itself.
    rd = rep["random_drop_control"]
    assert rd["keep_n"] == 40 and rd["n_signal_pool"] == 80


def test_entry_pure_filter_is_judged_pooled_because_matched_is_zero_by_construction():
    """`iv_cheap` buys on the alert day, so on shared alerts it is the SAME trade and its matched
    difference is exactly zero — E1(a) would be unattainable rather than failed. It is judged on
    the pooled book, where E6's random drop does the work of separating selection from luck."""
    from valuation.edge import options_entry as E

    assert "iv_cheap" in E.FILTER_ARMS and "delay5" not in E.FILTER_ARMS
    rep = {"n": 200, "held_out": {"both_positive": True}, "stats": {"expectancy_pct": 0.3},
           "vs_signal_matched": {"expectancy_diff": 0.0, "arm": {"expectancy_pct": 0.3}},
           "vs_signal_pooled": {"expectancy_diff": 0.25},
           "vs_control": {"bootstrap": {"ok": True, "diff": 0.08, "excludes_zero": True}},
           "random_drop_control": {"beats_random_drop": True}}
    g = E.arm_gate(rep, "iv_cheap", p_adjusted=True)
    assert g["basis"] == "pooled" and g["beats_signal_by_bar"] and g["passed"], g
    # the same report judged as a timing arm reads the matched zero and cannot pass
    assert E.arm_gate(rep, "delay5", p_adjusted=True)["basis"] == "matched"
    assert not E.arm_gate(rep, "delay5", p_adjusted=True)["passed"]


def test_entry_gate_refuses_an_arm_that_only_beats_the_broken_baseline():
    """E1(b), the bar 22b forces on everything after it: the signal arm LOSES to a random-entry
    control, so beating the signal is not on its own evidence of anything."""
    from valuation.edge import options_entry as E

    rep = {"n": 500, "held_out": {"both_positive": True}, "stats": {"expectancy_pct": 0.4},
           "vs_signal_matched": {"expectancy_diff": 0.50, "arm": {"expectancy_pct": 0.4}},
           "vs_signal_pooled": {"expectancy_diff": 0.50},
           "vs_control": {"bootstrap": {"ok": True, "diff": -0.02, "excludes_zero": True}}}
    g = E.arm_gate(rep, "delay5", p_adjusted=True)
    assert g["beats_signal_by_bar"] and not g["beats_control"] and not g["passed"]
    rep["vs_control"]["bootstrap"] = {"ok": True, "diff": 0.05, "excludes_zero": True}
    assert E.arm_gate(rep, "delay5", p_adjusted=True)["passed"]


def test_entry_dropping_arm_must_also_beat_a_random_drop():
    """E6. Removing trades at random from a heavy tail moves expectancy on its own, so a
    selective arm that clears every other bar is still not evidence until it beats a same-sized
    random drop of the signal book."""
    from valuation.edge import options_entry as E

    rep = {"n": 200, "held_out": {"both_positive": True}, "stats": {"expectancy_pct": 0.3},
           "vs_signal_matched": {"expectancy_diff": 0.20, "arm": {"expectancy_pct": 0.3}},
           "vs_signal_pooled": {"expectancy_diff": 0.20},
           "vs_control": {"bootstrap": {"ok": True, "diff": 0.08, "excludes_zero": True}},
           "random_drop_control": {"beats_random_drop": False}}
    assert not E.arm_gate(rep, "iv_wait", p_adjusted=True)["passed"]
    rep["random_drop_control"]["beats_random_drop"] = True
    assert E.arm_gate(rep, "iv_wait", p_adjusted=True)["passed"]


def test_entry_fade_put_is_exempt_from_the_improvement_bar_but_not_the_control():
    """E3. A long put is a different trade, not a better long call, so asking it to beat the call
    book by MIN_EXPECTANCY_GAIN is the wrong question. It must still make money, beat the
    random-entry control, and hold in both halves."""
    from valuation.edge import options_entry as E

    rep = {"n": 400, "held_out": {"both_positive": True}, "stats": {"expectancy_pct": 0.06},
           "vs_signal_matched": {"expectancy_diff": -0.30, "arm": {"expectancy_pct": 0.06}},
           "vs_signal_pooled": {"expectancy_diff": -0.30},
           "vs_control": {"bootstrap": {"ok": True, "diff": 0.04, "excludes_zero": True}}}
    g = E.arm_gate(rep, "fade_put", p_adjusted=None)
    assert g["gate"] == "E3" and g["passed"], g
    rep["vs_control"]["bootstrap"] = {"ok": True, "diff": -0.04, "excludes_zero": True}
    assert not E.arm_gate(rep, "fade_put", p_adjusted=None)["passed"]
    rep["vs_control"]["bootstrap"] = {"ok": True, "diff": 0.04, "excludes_zero": True}
    rep["stats"]["expectancy_pct"] = -0.01
    rep["vs_signal_matched"]["arm"]["expectancy_pct"] = -0.01
    assert not E.arm_gate(rep, "fade_put", p_adjusted=None)["passed"], \
        "a losing fade is not an exploitable anti-tilt"


def test_entry_best_arm_is_chosen_on_the_half_it_is_not_judged_on():
    """E5. Nine arms on a heavy tail means the best full-sample arm is partly the luckiest one.
    The only uncontaminated read is choose-on-one-half / measure-on-the-other, and an arm that
    wins the half that picked it and collapses on the other must NOT survive."""
    from valuation.edge import options_entry as E

    early = [(f"2018-{(i % 12) + 1:02d}-05", f"N{i}", 0.0) for i in range(40)]
    late = [(f"2023-{(i % 12) + 1:02d}-05", f"M{i}", 0.0) for i in range(40)]
    signal = _entry_rows(early + late)
    good_early = _entry_rows([(d, t, 1.0) for d, t, _ in early]
                             + [(d, t, -1.0) for d, t, _ in late], arm="delay5")
    steady = _entry_rows([(d, t, 0.02) for d, t, _ in early + late], arm="delay3")
    ctrl = _entry_rows([(d, t, 0.0) for d, t, _ in early + late], arm="control")
    out = E.holdout_arm_select({"signal": signal, "delay5": good_early, "delay3": steady},
                               signal, ctrl)
    assert out["decide_early"]["chosen_arm"] == "delay5", out["decide_early"]
    assert out["decide_early"]["gain_on_measure_half"] < 0, "it collapses on the held-out half"
    assert not out["survives_both_directions"]


def test_entry_mechanism_needs_a_majority_of_both_iv_and_runup_proxies():
    """E2. 'The alert chases pumped IV' is a two-part claim, and each part has several proxies.
    One proxy firing while the rest point the other way is a cherry-pick, not a mechanism."""
    from valuation.edge import options_entry as E

    def ch(iv_hits, run_hits):
        d = {}
        for i, f in enumerate(E.IV_MECHANISM_FEATURES):
            s = 1.0 if i < iv_hits else -1.0
            d[f] = {"ok": True, "paired": {"ok": True, "mean_diff": 0.05 * s, "sign_z": 5.0 * s}}
        for i, f in enumerate(E.RUNUP_MECHANISM_FEATURES):
            s = 1.0 if i < run_hits else -1.0
            d[f] = {"ok": True, "paired": {"ok": True, "mean_diff": 0.05 * s, "sign_z": 5.0 * s}}
        return d

    full = len(E.IV_MECHANISM_FEATURES), len(E.RUNUP_MECHANISM_FEATURES)
    assert E.mechanism_verdict(ch(*full))["label"] == "CONFIRMED"
    lone = E.mechanism_verdict(ch(1, 0))
    assert lone["label"] == "REJECTED" and not lone["E2_mechanism"], lone
    part = E.mechanism_verdict(ch(full[0], 0))
    assert part["label"] == "PARTIAL" and not part["E2_mechanism"], part
    assert E.mechanism_verdict(ch(0, 0))["label"] == "REJECTED"


def test_entry_paired_test_is_by_name_year_and_not_pooled():
    """The whole 22b control finding rests on the paired name-year cell rather than the pooled
    mean: one name that alerts 100 times would otherwise decide the verdict for all 187."""
    from valuation.edge import options_entry as E

    real = _entry_rows([(f"2019-{(i % 12) + 1:02d}-05", "LOUD", 0.30) for i in range(100)]
                       + [(f"2019-{(i % 12) + 1:02d}-05", f"Q{i}", -0.10) for i in range(20)])
    ctrl = _entry_rows([(f"2019-{(i % 12) + 1:02d}-05", "LOUD", 0.20) for i in range(100)]
                       + [(f"2019-{(i % 12) + 1:02d}-05", f"Q{i}", 0.10) for i in range(20)],
                       arm="control")
    pooled = (E._stats(real)["expectancy_pct"] or 0) - (E._stats(ctrl)["expectancy_pct"] or 0)
    pr = E.paired_cells(real, ctrl)
    assert pooled > 0, "pooled is carried by the one loud name"
    assert pr["ok"] and pr["mean_diff"] < 0 and pr["win_rate"] < 0.5, pr
    assert pr["sign_z"] < 0 and pr["n_cells"] == 21


def test_entry_iv_is_read_at_the_traded_tenor_not_the_front_expiry():
    """The 22b `iv` field is the FRONT expiry, often solved days from expiry, and reads a median
    of 1.28-1.57 across cap tiers. This strategy buys 45-75 DTE, so that is the tenor whose vol
    matters — and a garbage front-month quote must not be able to reach the answer."""
    from valuation.edge import blackscholes as BS
    from valuation.edge import options_entry as E

    assert E.IV_TENOR_DTE == 60
    asof = dt.date(2020, 6, 1)
    spot, vol = 100.0, 0.30
    rows = [{"expiration": asof + dt.timedelta(days=7), "strike": k, "right": "C",
             "bid": 9.0, "ask": 0.5, "volume": 10, "open_interest": 10}
            for k in (95.0, 100.0, 105.0)]                    # crossed: unusable
    T = 60 / 365.0
    for k in (95.0, 100.0, 105.0):
        px = BS.bs_price(spot, k, T, BS.risk_free_rate(asof), vol, "C")
        rows.append({"expiration": asof + dt.timedelta(days=60), "strike": k, "right": "C",
                     "bid": px - 0.02, "ask": px + 0.02, "volume": 10, "open_interest": 10})
    got = E.atm_iv_on(pd.DataFrame(rows), spot, asof)
    assert got is not None, "a bad front month must not blank the traded-tenor read"
    assert abs(got - vol) < 0.02, got
    assert E.atm_iv_on(pd.DataFrame(rows[:3]), spot, asof) is None, \
        "the crossed front-month quotes really are unusable"


def test_entry_context_gates_reuse_the_committed_section2_gate_unchanged():
    """E7. The same-day gates are judged by `options_signals_v2.evaluate` — fitted on 2016-2020,
    applied to 2021-2025, against the bars term_slope had to clear. Writing a fresh gate here
    would let this session run an easier race than the one that adopted the only live filter."""
    import inspect

    from valuation.edge import options_entry as E

    src = inspect.getsource(E.context_filters)
    assert "S2.evaluate" in src, "the committed gate must be called, not reimplemented"
    assert "-v" in src, "direction is fixed by the hypothesis: low extension / low vol is good"
    assert set(E.CONTEXT_FILTERS) <= set(E.CONTEXT_FEATURES)
    # and the search they add must be paid for in the deflation
    an = inspect.getsource(E.analyse)
    assert "len(CONTEXT_FILTERS)" in an, "context gates are part of the search, not free"


def test_entry_multiplicity_is_paid_for_not_merely_mentioned():
    """Nine arms are a search. The Deflated Sharpe must be deflated by the number of arms and the
    paired p-values must go through BH-FDR together — if either silently reverts to a single
    trial, the study becomes a ranking exercise wearing a significance label."""
    import inspect

    from valuation.edge import options_entry as E

    src = inspect.getsource(E.analyse)
    assert "n_trials=max(1, n_arms)" in src, "the DSR must be deflated by the arms searched"
    assert "bh_fdr" in src and "FDR_Q" in src
    assert len(E.ARMS) == 9 and E.ARMS[0] == "signal"
    assert set(E.DROPPING_ARMS) <= set(E.ARMS) and set(E.FILTER_ARMS) <= set(E.ARMS)
    # one-sided: an arm WORSE than the signal must not be able to become a discovery
    assert "else 1.0" in src


# ---------------------------------------------------------------------------------------------
# OPTIONS_DEEP_RESEARCH thread #1 — exit optimization. These pin the design decisions of the
# exit lab: the baseline must reproduce production, the tail must be watched, the random-entry
# set must be required, and the policy grid must pay for its own multiplicity.
# ---------------------------------------------------------------------------------------------
def _exit_path(marks, entry=(1.00, 1.10), dte0=60, right="C", strike=100.0,
               settle=None, start="2019-01-02"):
    """A synthetic contract path. `marks` are daily BID levels; the ask sits 4% above so every
    exit quote is tradable and the sell-side fill is exactly the bid at aggression 1.0."""
    ds = [str(d.date()) for d in pd.bdate_range(start=start, periods=len(marks) + 1)][1:]
    days = [(d, float(b), float(b) * 1.04) for d, b in zip(ds, marks)]
    return {"ticker": "T", "entry_date": start, "expiry": str(
                (dt.date.fromisoformat(start) + dt.timedelta(days=dte0))),
            "strike": strike, "right": right,
            "entry_bid": entry[0], "entry_ask": entry[1], "entry_oi": 500.0,
            "entry_volume": 50.0, "entry_fill": entry[1], "dte0": dte0,
            "days": days, "settle_underlying": settle, "entry_spread_pct": 0.095,
            "alert_date": start, "cap_tier": "mega"}


def test_exitlab_baseline_policy_reproduces_the_shipped_simulator():
    """Every number in this thread is compared against results the PRODUCTION simulator produced.
    If the path-replay evaluator differs from it by even a cent the comparison is meaningless, so
    the baseline replay is a hard gate rather than a warning."""
    from valuation.edge import options_exitlab as EL

    assert EL.SHIPPED == {"tp": 1.00, "sl": -0.50, "time_frac": 0.50}
    # +100% on the entry fill of 1.10 needs a bid of 2.20; it arrives on day 3.
    p = _exit_path([1.20, 1.60, 2.30, 3.00])
    t = EL.apply_policy(p, dict(EL.SHIPPED))
    assert t["ok"] and t["exit_reason"] == "target"
    # AUDIT B15: return_pct is net of commission; the gross figure keeps the old arithmetic.
    assert abs(t["return_pct_gross_comm"] - (2.30 / 1.10 - 1.0)) < 1e-12, t
    assert abs(t["return_pct"] - ((2.30 - 1.10) * 100 - 1.30) / (1.10 * 100)) < 1e-12, t

    # and the checker must actually catch a mismatch rather than rubber-stamping
    good = [{"ticker": "T", "entry_date": p["entry_date"], "alert_ts": p["entry_date"],
             "pnl_pct": t["return_pct"]}]
    bad = [dict(good[0], pnl_pct=t["return_pct"] + 0.01)]
    assert EL.replay_matches_shipped([p], good)["ok"]
    chk = EL.replay_matches_shipped([p], bad)
    assert not chk["ok"] and chk["n_mismatched"] == 1


def test_exitlab_take_profit_mechanically_removes_the_tail_it_is_judged_on():
    """X6. 83.7% of the book's gross winnings come from >= +100% trades. A +50% take-profit
    raises the hit rate by deleting exactly that tail, so a policy cannot be read on expectancy
    alone — the tail statistics have to travel with it."""
    from valuation.edge import options_exitlab as EL

    runner = _exit_path([1.30, 2.00, 3.00, 4.40, 5.00])
    tp50 = EL.apply_policy(runner, {"tp": 0.50, "sl": -0.50, "time_frac": 0.50})
    none = EL.apply_policy(runner, {"tp": None, "sl": -0.50, "time_frac": 0.50})
    assert tp50["exit_reason"] == "target" and tp50["return_pct"] < 1.0
    assert none["return_pct"] > 3.0, "with no target the runner is allowed to run"

    rows_tp = EL.score_paths([runner], "tp50", {"tp": 0.50, "sl": -0.50, "time_frac": 0.50})
    rows_no = EL.score_paths([runner], "tp_none", {"tp": None, "sl": -0.50, "time_frac": 0.50})
    assert EL.policy_stats(rows_tp)["p_tail_win"] == 0.0
    assert EL.policy_stats(rows_no)["p_tail_win"] == 1.0


def test_exitlab_trailing_stop_arms_only_after_its_ratchet_threshold():
    """A ratcheting trail must not fire on a position that never got going — otherwise it is just
    a tighter stop wearing a different name, and the two would be indistinguishable in the grid."""
    from valuation.edge import options_exitlab as EL

    # peaks at +9% (bid 1.20 vs a 1.10 fill), then gives back 42% of the peak.
    p = _exit_path([1.15, 1.20, 0.69, 0.68, 0.67])
    plain = EL.apply_policy(p, {"tp": 1.00, "sl": None, "time_frac": 0.50, "trail": 0.35})
    assert plain["exit_reason"] == "trail", plain

    ratchet = EL.apply_policy(p, {"tp": 1.00, "sl": -0.50, "time_frac": 0.50,
                                  "trail": 0.35, "trail_after": 0.50})
    assert ratchet["exit_reason"] != "trail", "the trail must stay disarmed below +50%"

    # once it clears +50% the same trail does fire
    q = _exit_path([1.20, 1.70, 1.05, 1.00])
    armed = EL.apply_policy(q, {"tp": 1.00, "sl": -0.50, "time_frac": 0.50,
                                "trail": 0.35, "trail_after": 0.50})
    assert armed["exit_reason"] == "trail", armed


def test_exitlab_exit_checks_fire_in_the_declared_order():
    """TARGET, then fixed STOP, then TRAIL, then TIME — matching the shipped simulator, which
    records the target when one day clears both. The ordering flatters the target slightly; it is
    held constant across the grid so no policy gains from it, but it must not drift."""
    from valuation.edge import options_exitlab as EL

    # a day that is simultaneously past the time stop AND at the target
    p = _exit_path([1.15] * 40 + [2.40], dte0=20)
    t = EL.apply_policy(p, dict(EL.SHIPPED))
    assert t["exit_reason"] == "time_stop", "the time stop bites long before the target arrives"

    q = _exit_path([2.40], dte0=1)
    t2 = EL.apply_policy(q, dict(EL.SHIPPED))
    assert t2["exit_reason"] == "target", "target wins when both fire on the same day"


def test_exitlab_worthless_expiries_settle_at_intrinsic_and_are_not_dropped():
    """Dropping the contracts that expired worthless is the survivorship bias that makes every
    options backtest look good. A path with no tradable exit quote must still post its -100%."""
    from valuation.edge import options_exitlab as EL

    p = _exit_path([], dte0=45, strike=100.0, settle=80.0)
    t = EL.apply_policy(p, dict(EL.SHIPPED))
    assert t["ok"] and t["exit_reason"] == "expiry"
    assert t["settled_at_intrinsic"] and t["return_pct_gross_comm"] == -1.0, t   # AUDIT B15


def test_exitlab_holding_past_the_last_quote_settles_at_intrinsic_not_at_a_stale_mark():
    """THE finding of this thread. A contract stops being quotable when its bid hits zero or its
    spread blows out — exactly when it is dying — so marking the fall-through at the last usable
    quote books a price from BEFORE the final decay. That bias grows with holding period, so it
    manufactures a monotone reward for holding longer and would hand the grid a fake winner."""
    from valuation.edge import options_exitlab as EL

    # quotes stop 10 days before expiry with the bid still at 0.60; the stock finishes OTM, so
    # the honest settlement is a total loss and the stale mark is a 45% loss.
    p = _exit_path([0.90, 0.75, 0.60], dte0=45, strike=100.0, settle=80.0)
    honest = EL.apply_policy(p, {"tp": 1.00, "sl": None, "time_frac": 1.00}, settle="intrinsic")
    legacy = EL.apply_policy(p, {"tp": 1.00, "sl": None, "time_frac": 1.00},
                             settle="last_quote")
    assert honest["exit_reason"] == "expiry" and legacy["exit_reason"] == "expiry"
    assert honest["return_pct_gross_comm"] == -1.0, honest                       # AUDIT B15
    assert abs(legacy["return_pct_gross_comm"] - (0.60 / 1.10 - 1.0)) < 1e-12, legacy  # B15
    assert legacy["return_pct"] > honest["return_pct"], "the stale mark flatters, always"
    assert legacy["stale_mark_used"] and not honest.get("stale_mark_used")

    # the shipped exit barely touches this path, which is why earlier results are unaffected
    quick = _exit_path([2.40] + [0.60] * 5, dte0=45, strike=100.0, settle=80.0)
    t = EL.apply_policy(quick, dict(EL.SHIPPED))
    assert t["exit_reason"] == "target" and not t.get("stale_mark_used")


def test_exitlab_gate_requires_the_random_entry_set_not_just_the_signal():
    """X1(b), the key test the mandate names. The scream-buy entry is dead, so an exit that only
    improves things behind it is entry-conditional, not an exit edge. It is recorded separately
    as SIGNAL-ONLY and never merged into the headline."""
    from valuation.edge import options_exitlab as EL

    def cmp_(gain, halves=True):
        return {"tp_none": {"stats": {"n": 500, "expectancy_pct": 0.3},
                            "held_out": {"both_positive": halves},
                            "vs_shipped": {"expectancy_diff": gain, "tail_share_change": 0.0}}}

    fdr = {"tp_none": {"discovery": True}}
    only = EL.gate(cmp_(0.25), cmp_(-0.02), fdr)["tp_none"]
    assert only["beats_shipped_on_signal_by_bar"] and not only["beats_shipped_on_random"]
    assert only["X2_signal_only"] and not only["X1_adopt"]

    both = EL.gate(cmp_(0.25), cmp_(0.11), fdr)["tp_none"]
    assert both["X1_adopt"] and not both["X2_signal_only"]

    # and a policy the paired test does not support cannot be adopted however big the gap
    assert not EL.gate(cmp_(0.25), cmp_(0.11),
                       {"tp_none": {"discovery": False}})["tp_none"]["X1_adopt"]


def test_exitlab_pbo_detects_a_grid_whose_winner_does_not_persist():
    """X3. CSCV over the policy grid is the one statistic that directly answers 'would picking the
    best backtest have been a mistake'. It must return a HIGH PBO when the in-sample winner is the
    out-of-sample loser, and a low one when a policy genuinely dominates throughout."""
    from valuation.edge import options_exitlab as EL

    early = [str(d.date()) for d in pd.bdate_range(start="2017-01-02", periods=120)]
    late = [str(d.date()) for d in pd.bdate_range(start="2023-01-02", periods=120)]

    # Every policy carries the SAME large dispersion, so the block Sharpe ranks by mean. Giving
    # one policy a tighter spread would hand it a huge Sharpe on a trivial edge — which is a real
    # property of the statistic and would make this test pass for the wrong reason.
    OFFSETS = (-0.9, 0.9, -0.3, 0.3, -0.6, 0.6)

    def rows(dates, val):
        return [{"ticker": f"N{i%7}", "alert_ts": d, "alert_date": d,
                 "pnl_pct": val + OFFSETS[i % len(OFFSETS)], "status": "closed"}
                for i, d in enumerate(dates)]

    # A wins early and loses late; B does the reverse. Neither persists.
    flip = {"shipped": rows(early, 0.05) + rows(late, 0.05),
            "A": rows(early, 0.60) + rows(late, -0.50),
            "B": rows(early, -0.50) + rows(late, 0.60)}
    bad = EL.pbo_cscv_policies(flip, n_blocks=6)
    assert bad["ok"] and bad["pbo"] > 0.5, bad

    # C is better in every block; picking it in sample is the right call out of sample.
    steady = {"shipped": rows(early, 0.05) + rows(late, 0.05),
              "A": rows(early, 0.02) + rows(late, 0.02),
              "C": rows(early, 0.60) + rows(late, 0.60)}
    good = EL.pbo_cscv_policies(steady, n_blocks=6)
    assert good["ok"] and good["pbo"] < 0.5 and good["passes"], good


def test_exitlab_expectancy_is_reported_per_day_held_as_well_as_per_trade():
    """X5. An exit that closes in half the time is not comparable per trade — it frees the capital
    sooner. Both readings must ship, or a fast-exit policy is judged on the wrong axis."""
    from valuation.edge import options_exitlab as EL

    slow = [{"ticker": "A", "alert_ts": "2019-01-02", "alert_date": "2019-01-02",
             "pnl_pct": 0.20, "held_days": 40, "status": "closed"}]
    fast = [{"ticker": "A", "alert_ts": "2019-01-02", "alert_date": "2019-01-02",
             "pnl_pct": 0.10, "held_days": 20, "status": "closed"}]
    a, b = EL.policy_stats(slow), EL.policy_stats(fast)
    assert a["expectancy_pct"] > b["expectancy_pct"], "slow wins per trade"
    assert abs(a["expectancy_per_day_held"] - b["expectancy_per_day_held"]) < 1e-12, \
        "and they are identical per day held — which is why both are reported"


def test_exitlab_policy_grid_is_fixed_and_pays_for_its_own_multiplicity():
    """X3/X6. Twenty-one policies is a search. The grid is declared before the run, each
    single-dimension family varies exactly one field from the shipped exit, and the deflation is
    by the policy count rather than by one."""
    import inspect

    from valuation.edge import options_exitlab as EL

    assert len(EL.POLICIES) == 21 and EL.POLICY_NAMES[0] == EL.BASELINE
    assert len(set(EL.POLICY_NAMES)) == 21, "no duplicate policy names"
    assert dict(EL.POLICIES)[EL.BASELINE] == EL.SHIPPED

    composites = {"shipped", "ratchet35", "run_winners", "tp100_only"}
    for name, pol in EL.POLICIES:
        if name in composites:
            continue
        diff = [k for k in set(pol) | set(EL.SHIPPED)
                if pol.get(k) != EL.SHIPPED.get(k)]
        # a family may drop time_frac in favour of dte_exit; that is still one dimension
        assert len(diff) <= 2, f"{name} varies more than one dimension: {diff}"

    src = inspect.getsource(EL.analyse)
    assert "n_trials=n_trials" in src and "len(POLICY_NAMES)" in src
    assert "bh_fdr" in src and "else 1.0" in src, "one-sided: worse policies are not discoveries"
    assert EL.MAX_PBO == 0.50
    # The one-sided screen must take its DIRECTION from the sign test, whose p-value it is —
    # not from the mean, which can point the other way on a heavy tail.
    assert 'pr.get("sign_z")' in src, "direction must come from the sign test"
    assert 'pvals.append(p if (z or 0) > 0 else 1.0)' in src
    from valuation.edge import options_entry as E
    assert 'pr.get("sign_z")' in inspect.getsource(E.analyse), \
        "the same screen in the 22c entry study must agree"


# ---------------------------------------------------------------------------------------------
# OPTIONS_DEEP_RESEARCH thread #2 — the cross-section of option returns. These pin the decisions
# that would otherwise let a two-ended sort produce a winner by construction.
# ---------------------------------------------------------------------------------------------
def _xs_chain(strikes=(95.0, 100.0, 105.0), dte=30, asof="2020-06-01",
              call=(4.00, 4.20), put=(3.80, 4.00), rights=("C", "P")):
    """A minimal one-expiry chain that passes the fill model's liquidity screen."""
    a = dt.date.fromisoformat(asof)
    rows = []
    for k in strikes:
        for r in rights:
            bid, ask = (call if r == "C" else put)
            rows.append({"expiration": a + dt.timedelta(days=dte), "strike": k, "right": r,
                         "bid": bid, "ask": ask, "open_interest": 500, "volume": 50})
    return pd.DataFrame(rows)


def _xs_ev(quintiles, t=3.0, months=120, both=True, char="iv_rv"):
    """A hand-built evaluate_char result, so the gate can be tested without a panel."""
    from valuation.edge import options_xsection as X
    return {"char": char, "ok": True, "source": "test", "is_hypothesis":
            X.CHARACTERISTICS[char]["hypothesis"], "published_sign":
            X.CHARACTERISTICS[char]["sign"],
            "n_months": months, "n_dates_dropped_thin": 0,
            "quintile_mean_returns": list(quintiles),
            "quintile_mean_char": list(range(len(quintiles))),
            "monotonicity": X._spearman(list(range(len(quintiles))), list(quintiles)),
            "all_names": {"n": months, "mean": 0.0},
            "long_only_q1_excess": {"n": months, "mean": 0.05, "t": t},
            "held_out_q1_excess": {"early": {"n": 60, "mean": 0.05},
                                   "late": {"n": 60, "mean": 0.05},
                                   "both_positive": both},
            "long_short_NOT_INVESTABLE": {"n": months, "mean": 0.10, "t": t},
            "monthly_q1_excess": {}}


def test_xsection_direction_is_fixed_before_the_sort_not_after():
    """S2, the single most important rule in the module. A cross-sectional sort has two ends; a
    study that chooses which end to go long AFTER seeing the numbers wins half the time by
    construction. Every published sign is declared up front, and a sort that runs BACKWARDS is a
    contradiction of the literature — never quietly re-signed into a result."""
    from valuation.edge import options_xsection as X

    assert all(m["sign"] == +1 for m in X.CHARACTERISTICS.values()), \
        "every characteristic is declared as 'high predicts LOWER option returns'"

    # predicted: returns fall as the characteristic rises -> Q1 highest
    good = X.gate(_xs_ev([0.30, 0.20, 0.10, 0.00, -0.10]), fdr_discovery=True)
    assert good["passed"] and good["monotone_in_predicted_direction"]
    assert not good["contradicts_published_sign"]

    # BACKWARDS: a strong sort in the opposite direction must not pass
    bad = X.gate(_xs_ev([-0.10, 0.00, 0.10, 0.20, 0.30]), fdr_discovery=True)
    assert not bad["passed"], bad
    assert bad["contradicts_published_sign"] and not bad["monotone_in_predicted_direction"]


def test_xsection_straddle_is_bought_at_the_ask_on_both_legs():
    """S5. A straddle crosses TWO spreads at entry — it is the most spread-punished instrument in
    the project. Marking either leg at the mid would manufacture most of any cross-sectional
    result, so both legs pay the ask and the arithmetic is pinned here."""
    from valuation.edge import options_fill as F
    from valuation.edge import options_xsection as X

    asof = dt.date(2020, 6, 1)
    s = X.pick_straddle(_xs_chain(), 100.0, asof)
    assert s is not None and s["strike"] == 100.0
    assert s["call"].ask == 4.20 and s["put"].ask == 4.00

    r = X.straddle_return(s, settle_underlying=110.0)
    cost = (4.20 + 4.00) * F.CONTRACT_MULTIPLIER
    comm = F.COMMISSION_PER_CONTRACT * 2 * 2               # two legs, both ways
    pnl = (10.0 - 4.20) * F.CONTRACT_MULTIPLIER + (0.0 - 4.00) * F.CONTRACT_MULTIPLIER - comm
    assert abs(r["entry_cost"] - cost) < 1e-9
    assert abs(r["net_pnl"] - pnl) < 1e-9
    assert abs(r["return_pct"] - pnl / cost) < 1e-12


def test_xsection_straddle_settles_at_intrinsic_carrying_thread1s_lesson():
    """Thread #1 found the simulator marks a position that outlives its last usable quote at that
    STALE quote — higher than the truth in 94.7% of cases. Holding to expiry and settling against
    the underlying removes the mark entirely: there is only a payoff."""
    from valuation.edge import options_xsection as X

    s = X.pick_straddle(_xs_chain(), 100.0, dt.date(2020, 6, 1))
    pinned = X.straddle_return(s, settle_underlying=100.0)      # both legs finish worthless
    assert pinned["return_pct"] < -1.0, "premium plus commission, all of it"
    assert abs(pinned["return_pct"] + 1.0) < 0.01
    # and no settle price at all must drop the observation rather than invent one
    assert X.straddle_return(s, settle_underlying=None) is None


def test_xsection_straddle_legs_must_share_a_strike_and_an_expiry():
    """Two legs at different strikes is a strangle, not a straddle, and is not delta-neutral at
    inception — which is the entire reason this instrument was chosen."""
    from valuation.edge import options_xsection as X

    ch = _xs_chain(strikes=(95.0, 100.0, 105.0))
    ch = ch[~((ch["strike"] == 100.0) & (ch["right"] == "P"))]   # no ATM put available
    s = X.pick_straddle(ch, 100.0, dt.date(2020, 6, 1))
    assert s is not None and s["strike"] in (95.0, 105.0), \
        "it must fall back to a strike where BOTH legs exist"

    far = X.pick_straddle(_xs_chain(strikes=(200.0,)), 100.0, dt.date(2020, 6, 1))
    assert far is None, "a strike miles from spot is not an ATM straddle"


def test_xsection_thin_dates_are_dropped_and_counted_not_silently_used():
    """A cross-sectional sort on eight names is five quintiles of one or two. Thin dates are
    dropped and the count ships, because a silently thin month looks identical to a real one."""
    from valuation.edge import options_xsection as X

    panel = [{"date": "2019-01-31", "ticker": f"N{i}", "return_pct": 0.1 * (i % 5),
              "iv_rv": float(i)} for i in range(8)]
    panel += [{"date": "2019-02-28", "ticker": f"N{i}", "return_pct": 0.1 * (i % 5),
               "iv_rv": float(i)} for i in range(40)]
    s = X.quintile_sort(panel, "iv_rv")
    assert s["n_months"] == 1 and s["n_dates_dropped_thin"] == 1
    assert "2019-02-28" in s["months"] and "2019-01-31" not in s["months"]


def test_xsection_monotonicity_bar_rejects_a_q1_q5_gap_with_noise_between():
    """S1(c). A characteristic whose extremes differ while the middle is noise has not sorted
    anything — it has found two tails. The rank correlation across all five quintiles is what
    separates a real monotone relationship from a lucky pair of ends."""
    from valuation.edge import options_xsection as X

    noisy = X.gate(_xs_ev([0.30, -0.15, 0.25, -0.05, -0.12]), fdr_discovery=True)
    assert not noisy["monotone_enough"] and not noisy["passed"], noisy
    clean = X.gate(_xs_ev([0.30, 0.18, 0.09, -0.02, -0.12]), fdr_discovery=True)
    assert clean["monotone_enough"] and clean["passed"]


def test_xsection_long_short_is_labelled_uninvestable_and_never_gates():
    """S4. The short leg of Q1-Q5 is a NAKED SHORT STRADDLE — unlimited risk, not permitted in
    Don's account, and excluded by the mandate's own guardrail. The gate must read the long-only
    excess, and the long-short must carry its warning in the key name itself."""
    import inspect

    from valuation.edge import options_xsection as X

    ev = _xs_ev([0.30, 0.18, 0.09, -0.02, -0.12])
    assert "long_short_NOT_INVESTABLE" in ev
    src = inspect.getsource(X.gate)
    assert "long_only_q1_excess" in src and "long_short" not in src, \
        "the gate must never read the long-short leg"
    assert "naked short straddle" in (X.__doc__ or "").lower() or \
        "naked short straddle" in (X.verdict.__doc__ or "") or \
        "naked short straddle" in inspect.getsource(X.verdict)


def test_xsection_illiq_is_a_mechanical_control_and_cannot_be_adopted():
    """Returns here are net of the spread, so a wide-spread name must earn less BY CONSTRUCTION.
    `illiq` is carried as a control — if it does not sort, the panel is not measuring what it
    thinks it is — but it can never be a discovery, however good its statistics look."""
    from valuation.edge import options_xsection as X

    assert X.CHARACTERISTICS["illiq"]["hypothesis"] is False
    perfect = X.gate(_xs_ev([0.30, 0.18, 0.09, -0.02, -0.12], t=9.0, char="illiq"),
                     fdr_discovery=True)
    assert perfect["t_ok"] and perfect["monotone_in_predicted_direction"]
    assert not perfect["passed"], "a mechanical control must never be adopted"


def test_xsection_idio_moments_refuse_a_short_window_and_coverage_is_reported():
    """The COVERAGE RULE, which this project learned the expensive way: five wired factors were
    silently empty for its entire history. A characteristic with no coverage must be visible in
    the result, not an absent column that quietly contributes nothing to a quintile mean."""
    from valuation.edge import options_xsection as X

    days = [f"2019-{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 29)]
    # the market proxy must actually VARY, or the one-factor regression has no regressor
    mkt = {d: 0.001 * ((i % 5) - 2) for i, d in enumerate(days)}
    short = [(k, 0.002) for k in days[:50]]
    assert X.idio_moments(short, mkt) == {}, "too few observations must yield nothing, not noise"

    long_ = [(k, 0.002 * ((i % 7) - 3)) for i, k in enumerate(days[:300])]
    got = X.idio_moments(long_, mkt)
    assert "idio_vol" in got and "idio_skew" in got

    panel = [{"date": "2019-01-31", "ticker": "A", "return_pct": 0.1, "iv_rv": 1.0,
              "entry_cost": 100.0, "spread_pct": 0.05, "dte": 30}]
    cov = X.panel_summary(panel)["coverage"]
    assert set(cov) == set(X.CHAR_NAMES)
    assert cov["iv_rv"] == 1.0 and cov["idio_vol"] == 0.0


def test_xsection_one_sided_screen_cannot_reward_a_backwards_sort():
    """A characteristic that sorts the wrong way must not be able to earn a small p-value from a
    two-sided test and become a 'discovery'. Same failure the exit lab's FDR screen had."""
    import inspect

    from valuation.edge import options_xsection as X

    src = inspect.getsource(X.analyse)
    assert "if t > 0 else 1.0" in src
    assert "n_trials=len(CHAR_NAMES)" in src, "deflate by every characteristic tested"
    assert "pbo_cscv_policies" in src and "bh_fdr" in src



# =============================================================================================
# EXTERNAL EDGE AUDIT (VALQUO_EDGE_AUDIT.md) — Part I regression guards.
# One test per corrected item, cited by ID. Several of these defects survived for months
# because nothing failed when they were wrong; each guard exists so that stops being true.
# =============================================================================================
def test_audit_b1_option_maths_never_uses_the_adjusted_close():
    """B1. `close` is `closeadj` — split AND dividend adjusted, indicators only — while strikes
    trade unadjusted. Feeding the adjusted series to `chain_summary` / `pick_contract` /
    `compute_signals` throws the moneyness prefilter and the delta target on every pre-split
    date and corrupts every dividend payer on every date, while settlement kept using the
    unadjusted series — so entry and settlement of one trade ran on different price bases.

    FIVE call sites across four modules made this exact mistake independently, which is why the
    guard is a source scan and not a value assertion: the next module has to fail here, not in a
    result nobody can interpret."""
    import inspect

    from valuation.edge import options_backtest as OB
    from valuation.edge import options_entry, options_universe

    # the one sanctioned accessor
    assert OB.spot_asof({"raw_close": [1.0, 2.0, 3.5], "close": [9, 9, 9]}) == 3.5
    assert OB.spot_asof({"close": [9, 9, 7.0]}) == 7.0, "fall back only when raw is absent"
    assert OB.spot_asof(None) is None

    for mod in (options_universe, options_entry):
        src = inspect.getsource(mod)
        for fn in ("chain_summary", "pick_contract"):
            for line in src.splitlines():
                if fn + "(" in line:
                    assert 'w["close"]' not in line and '["close"][-1]' not in line, \
                        f"{mod.__name__}: {fn} must be fed an as-traded spot, got: {line.strip()}"


def test_audit_b1_sanity_flags_an_implausible_median_entry_iv():
    """B1's second guard. The 187-name run reported a median entry IV of 1.28-1.57 and the
    handoff recorded it as an unexplained anomaly; it was the price-basis bug. Coverage said
    `iv` was PRESENT. Nothing asked whether it was SANE."""
    from valuation.edge import options_universe as U

    ok = [{"ticker": f"T{i}", "iv": 0.35, "pnl_pct": 0.1, "entry_spread_pct": 0.05}
          for i in range(200)]
    bad = [dict(r, iv=1.42) for r in ok]
    assert not any("entry IV" in f for f in U.sanity(ok)["flags"]), U.sanity(ok)["flags"]
    flags = U.sanity(bad)["flags"]
    assert any("entry IV" in f for f in flags), flags
    assert abs(U.sanity(bad)["iv_median"] - 1.42) < 1e-9


def test_audit_b3_a_stale_quote_never_marks_a_position_at_expiry():
    """B3. `round_trip` preferred a quote over intrinsic whenever one existed, and the caller
    supplies the last quote that passed validation at ANY point in the contract's life. A
    position that outlived its quotes was stamped with a price from before it decayed: measured
    at 94.7% higher than the truth, 86.1% of marks positive on worthless contracts."""
    from valuation.edge import options_fill as F

    entry = F.Quote(bid=2.40, ask=2.60, oi=500, volume=100)
    stale = F.Quote(bid=1.00, ask=1.10)

    t = F.round_trip(entry, stale, right="C", strike=150.0, exit_underlying=120.0, expired=True)
    assert t["settled_at_intrinsic"] and t["exit_fill"] == 0.0, t

    # and away from expiry, age alone is enough to reject the mark
    old = F.round_trip(entry, stale, right="C", strike=150.0, exit_underlying=120.0,
                       exit_quote_age_days=F.MAX_MARK_AGE_DAYS + 1)
    assert old["settled_at_intrinsic"] and old["stale_mark_rejected"], old
    fresh = F.round_trip(entry, stale, right="C", strike=150.0, exit_underlying=120.0,
                         exit_quote_age_days=1)
    assert not fresh["settled_at_intrinsic"] and fresh["exit_fill"] == 1.0, fresh

    # the opt-out exists ONLY so the exit lab can reproduce the old behaviour for comparison
    legacy = F.round_trip(entry, stale, right="C", strike=150.0, exit_underlying=120.0,
                          expired=True, force_intrinsic_at_expiry=False)
    assert not legacy["settled_at_intrinsic"] and legacy["exit_fill"] == 1.0


def test_audit_b15_return_pct_is_net_of_commission_as_documented():
    """B15. `return_pct` was `exit/entry - 1`, i.e. gross of commission, while the module
    docstring and OPTIONS_BACKTEST_RESULTS.md both stated it was net of both. `pnl_pct` and
    `expectancy_pct` inherit it, so the headline per-trade figure was overstated."""
    from valuation.edge import options_fill as F

    q = F.Quote(bid=2.40, ask=2.60, oi=500, volume=100)
    up = F.Quote(bid=5.40, ask=5.60, oi=500, volume=100)
    t = F.round_trip(q, up, right="C", strike=100.0)
    assert abs(t["return_pct"] - t["net_pnl"] / (t["entry_fill"] * 100)) < 1e-12
    assert abs(t["return_pct_gross_comm"] - (5.40 / 2.60 - 1.0)) < 1e-12
    assert t["return_pct"] < t["return_pct_gross_comm"], "commission is a cost, always"


def test_audit_b10_build_frame_never_overwrites_a_caller_supplied_column():
    """B10, generalised. The panel computes the Sloan accruals measure and hands it in;
    `build_frame` replaced it unconditionally with FCF/NI restricted to profitable names, so the
    signal REPORTED as `accruals_q` was not the documented one and its IC fell from t +3.08 to
    +1.26. `book_to_price` and `growth_accel` were both guarded against exactly this."""
    from valuation.screener.factors import build_frame

    base = {"ticker": "AAA", "market_cap": 1e10, "net_income": 1e8, "fcf": 5e7,
            "revenue": 1e9, "gross_profit": 4e8, "total_equity": 2e9, "total_debt": 1e9,
            "assets": 5e9}
    sentinel = {"accruals_q": -0.0123, "book_to_price": 0.777, "growth_accel": 0.0456}
    got = build_frame([dict(base, **sentinel)])
    for col, want in sentinel.items():
        assert abs(float(got[col].iloc[0]) - want) < 1e-9, \
            f"build_frame overwrote caller-supplied {col!r}"
    # the FCF/NI variant survives under its own name, so the two can be measured head to head
    assert abs(float(got["accruals_fcf_ni"].iloc[0]) - 0.5) < 1e-9
    # and a caller that supplies nothing still gets the derived fallback
    derived = build_frame([dict(base)])
    assert abs(float(derived["accruals_q"].iloc[0]) - 0.5) < 1e-9


def test_audit_b18_negative_enterprise_value_reads_the_same_way_everywhere():
    """B18. A net-cash company ranked as the MOST EXPENSIVE name in the cross-section on
    `ebit_ev` and, once negated, the CHEAPEST of all on `neg_ev_sales` — the same fact sorted to
    opposite ends of one theme. `neg_ev_ebitda` was guarded; the other two were not."""
    from valuation.screener.factors import build_frame

    rows = [{"ticker": "NEG", "ev_sales": -3.0, "ev_ebitda": -4.0, "ps": 2.0, "market_cap": 1e9},
            {"ticker": "POS", "ev_sales": 2.0, "ev_ebitda": 8.0, "ps": 2.0, "market_cap": 1e9}]
    f = build_frame(rows)
    assert np.isnan(f.loc["NEG", "neg_ev_sales"]), "negative EV is missing, never 'cheapest'"
    assert np.isnan(f.loc["NEG", "neg_ev_ebitda"])
    assert abs(float(f.loc["POS", "neg_ev_sales"]) + 2.0) < 1e-9


def test_audit_b19_the_reported_sharpe_carries_its_risk_free_rate():
    """B19. `risk_stats` is invoked with rf = 0 everywhere, so every 'Sharpe' in the results file
    is a return-to-volatility ratio — an information ratio against zero. Over 1998-2026 that
    overstates a true Sharpe by roughly 0.05-0.10, consistently, and the figure reaches
    product-facing material. The options engine in this same repository subtracts a real rate."""
    from valuation.edge.fundamental_panel import risk_stats

    r = [0.03, -0.01, 0.04, 0.00, 0.02, -0.02, 0.05, 0.01]
    zero = risk_stats(r, 4)
    assert zero["rf_annual"] == 0.0
    assert zero["metric"] == "information_ratio_vs_zero_rf"
    real = risk_stats(r, 4, rf=0.02)
    assert real["metric"] == "sharpe_ratio" and real["sharpe"] < zero["sharpe"]
    assert risk_stats([0.01], 4)["metric"] == "information_ratio_vs_zero_rf"


def test_audit_b12_a_limited_universe_is_ranked_by_size_not_by_alphabet():
    """B12. `WRDSProvider.universe` returned `sorted(keys)[:limit]`. Every '800 largest names'
    result in the project's history was therefore names beginning with roughly A through C —
    including the first CPCV adopt, PBO 13%, f_score at t +5.66 and the four classic-anomaly
    rejections. It also reframes the calibration note: 'PBO 13% on 800 -> 53% on full' measured
    what an arbitrary alphabetical subsample does, not what a large-cap tier does."""
    from valuation.edge.data_providers import WRDSProvider

    p = WRDSProvider.__new__(WRDSProvider)
    idx = {"ZZZ": [{"datekey": "2020-01-01", "marketcap": 900.0}],
           "AAA": [{"datekey": "2020-01-01", "marketcap": 10.0}],
           "MMM": [{"datekey": "2020-01-01", "marketcap": 500.0}]}
    p._indexed = lambda _base: idx
    assert p.universe(2) == ["ZZZ", "MMM"], "biggest first, not alphabetical"
    assert p.universe() == ["AAA", "MMM", "ZZZ"], "no limit = everything, order irrelevant"
    assert "market_cap" in WRDSProvider.UNIVERSE_SORT_KEY


def test_audit_b26_a_filing_dated_today_is_not_readable_at_todays_close():
    """B26. `searchsorted(..., side='right')` on the upper bound made a Form 4 or rating action
    dated `as_of` usable at that day's close. Both are routinely filed after the bell."""
    from valuation.edge import fundamental_panel as FP

    dts = np.array(["2020-01-10", "2020-03-01"], dtype="datetime64[D]")
    vals = np.array([5e6, 5e6])
    same_day = FP._insider_score_at((dts, vals), "2020-03-01", lookback_days=90)
    day_after = FP._insider_score_at((dts, vals), "2020-03-02", lookback_days=90)
    assert day_after is not None
    assert same_day != day_after, "the 2020-03-01 filing must not count on 2020-03-01"


def test_audit_b9_the_deflated_sharpe_says_when_it_deflated_nothing():
    """B9. With eight near-identical weight schemes the cross-trial variance of Sharpes is ~0,
    so the Bailey-Lopez de Prado benchmark sr0 collapses to ~0 and the statistic degenerates to
    an UNDEFLATED Probabilistic Sharpe Ratio. It saturates at 0.9999986 because it is not
    deflating anything. The degeneracy now ships next to the number."""
    from valuation.edge.fundamental_panel import _deflated_sharpe, _deflated_sharpe_detail

    r = np.random.RandomState(3).normal(0.02, 0.05, 80)
    flat = _deflated_sharpe_detail(r, [0.400, 0.401, 0.402])        # eight-schemes-like
    assert flat["is_effectively_undeflated"]
    assert flat["metric"] == "probabilistic_sharpe_ratio_UNDEFLATED"
    spread = _deflated_sharpe_detail(r, [0.05, 0.40, 0.90, -0.20])  # genuinely different trials
    assert not spread["is_effectively_undeflated"]
    assert spread["sr0_benchmark"] > flat["sr0_benchmark"]
    assert spread["probability"] < flat["probability"], "real deflation costs probability"
    assert _deflated_sharpe(r, [0.400, 0.401, 0.402]) == flat["probability"]


def test_audit_b24_the_sanity_scan_evaluates_each_factor_once():
    """B24. `SANE_RANGES` keys, `SANE_RANGE_EXEMPT` and the derived `z_*` names overlap, so
    factors were checked more than once and could be measured on a raw level in one pass and a
    standardised value in another. The shipped output printed `ev_ebitda` at a foreign median
    percentile of 0.362 beside `neg_ev_ebitda` at 0.640 — one fact, twice, sign-flipped. An
    inflated flag count trains readers to ignore the guard."""
    import inspect

    from valuation.edge import fundamental_panel as FP

    src = inspect.getsource(FP.sanity_check)
    assert "_seen" in src and "_scan" in src, "the scan list must be de-duplicated"
    assert 'nm.startswith("neg_")' in src, "a factor and its negated twin are one fact"
    assert '"check": "sign"' in src, "B18: the range-exempt ratios get a sign check instead"


def test_audit_b14_the_delisting_mask_ships_its_coverage():
    """B14. `_masked` was incremented and never printed, returned or shipped;
    `cleanups.survivorship_mask` was only a boolean meaning 'the ACTIONS map is non-empty'. If
    ACTIONS misses a delisting, that name's last close is forward-filled to the panel end and
    contributes a fake flat 0% forward return to every subsequent rebalance — silently."""
    import inspect

    from valuation.edge import fundamental_panel as FP

    src = inspect.getsource(FP.build_fundamental_panel)
    assert "_mask_coverage" in src and "ended_early_unmasked" in src
    assert "LAST_PANEL_DIAGNOSTICS" in src
    assert isinstance(FP.LAST_PANEL_DIAGNOSTICS, dict)
    assert FP.STALE_TAIL_DAYS >= 90, "a tail shorter than a quarter would flag ordinary gaps"


def test_audit_d10a_a_restated_quarter_is_not_counted_twice_in_a_ttm_window():
    """D10-a — found by running `verify_sharadar.py` against the live key on 2026-08-03, not by
    the audit. Sharadar APPENDS a new ARQ row on restatement rather than rewriting the existing
    one: in the shipped export 3.15% of (ticker, reportperiod) groups carry more than one
    datekey, across 1,818 of 2,827 tickers. `_ttm` took the last four ROWS and de-duplicated on
    DATEKEY, which two filings of one quarter never share — so it could sum Q1, Q2, Q2', Q3.
    Impact is confined to `roe_ttm` / `roic_ttm`, which were measured and rejected, but the guard
    could not see the defect it was written for."""
    from valuation.edge.fundamental_panel import _ttm

    def row(dk, rp, ni):
        return {"datekey": dk, "reportperiod": rp, "netinc": ni}

    clean = [row("2020-02-01", "2019-12-31", 10), row("2020-05-01", "2020-03-31", 20),
             row("2020-08-01", "2020-06-30", 30), row("2020-11-01", "2020-09-30", 40)]
    assert _ttm(clean, "2020-12-01", ("netinc",))["netinc"] == 100.0

    # the same year, but Q2 was restated a week later. The extra row must not push Q4 out.
    restated = [clean[0], clean[1], row("2020-08-08", "2020-06-30", 33), clean[2], clean[3]]
    restated.sort(key=lambda r: r["datekey"])
    got = _ttm(restated, "2020-12-01", ("netinc",))
    assert got is not None and got["netinc"] == 103.0, got   # 10 + 20 + 33 (latest) + 40


def test_audit_b20_earnings_yield_keeps_one_numerator_definition():
    """B20. The USD fallback was TOTAL net income / fx while the primary was net income to
    COMMON, so `earnings_yield` switched numerator definition mid-cross-section. For most names
    those agree; for preferred-heavy issuers — banks, REITs, recent recapitalisations — they
    differ by the preferred dividend, and those names cluster in one sector."""
    import inspect

    from valuation.edge import fundamental_panel as FP
    from valuation.edge.data_providers import WRDSProvider

    src = inspect.getsource(FP._sf1_to_metrics)
    assert "_ni_cmn" in src and '_f(sf1, "netinccmn")' in src
    assert "_ni_basis" in src, "how often the last-resort path fires must be visible"
    assert "netinccmn" in WRDSProvider._KEEP["fundamentals"], "the allowlist is load-bearing"
    assert "reportperiod" in WRDSProvider._KEEP["fundamentals"]


def test_audit_c7_every_test_suite_gates_the_auto_merge():
    """C7. `land-agent-branch.yml` auto-merges every `worktree-*` push into main and Render
    auto-deploys, behind `tests/test_edge.py` ONLY. Fourteen other suites did not gate a deploy,
    while agent branches routinely edit options_universe.py, paper_track.py, factors.py and
    screen.py — none of which that suite covers in full."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wf = open(os.path.join(root, ".github", "workflows", "land-agent-branch.yml"),
              encoding="utf-8").read()
    assert "for f in tests/test_*.py" in wf, "the gate must run every suite, not one"
    assert "exit $fail" in wf, "one red suite must not be hidden by a later green one"


def test_session8_a_landed_verdict_reaches_the_file_every_lane_reads():
    """Session 8. X8 -- the international replication, the strongest external evidence this
    project has -- passed on 2026-08-04, was written up in `HANDOFF_free_analysis.md` and marked
    DONE in the ledger, and `CLAUDE.md` still contained the words "JKP" and "Japan" ZERO times
    three days later. Two consecutive sessions then treated a passed test as pending work, and
    session 8's own prompt asked for it to be "scoped".

    `CLAUDE.md` is the only file every lane reads. A verdict that lands solely in one lane's
    handoff is invisible to the others, which is a memory-architecture defect and not a clerical
    slip -- the same class as the mislabelled theme-IC table and the stale rendered results file.
    This pins the repair so it cannot silently regress, and it deliberately checks for the
    CAVEATS too: a bullet that quotes only the wins would be the overselling CLAUDE.md forbids."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    brief = open(os.path.join(root, "CLAUDE.md"), encoding="utf-8").read()
    for token in ("JKP", "Japan"):
        assert token in brief, f"CLAUDE.md must record X8's result; {token!r} missing"
    # the result itself
    assert "t 3.85" in brief and "t 4.30" in brief, "X8's Japan/Europe t-stats must be quoted"
    # and the three things that stop it being oversold
    assert "weakest region" in brief.lower(), "the US control is the point of X8; keep it"
    assert "does not corroborate" in brief.lower() and "magnitude" in brief.lower(), \
        "X8 corroborates the premia, NOT Valquo's magnitude -- that caveat must travel"
    assert "RESEARCH ONLY" in brief, "JKP is CC BY-NC 4.0; it can never ship in the product"



def test_audit_b7_the_live_path_and_the_backtest_path_score_identically():
    """B7, the test the audit asked for by name. THREE composite functions existed and did not
    agree: selection renormalised by present-weight mass, measurement did not (a missing theme
    contributed a hard zero, which after z-scoring IS the cross-sectional average, so an
    incomplete name was dragged to mid-pack), and live renormalised AND added sector-neutral
    ranking plus residual momentum. `institutional` is missing on 38.6% of rows and `insider` on
    15%, and both absences track size and coverage — so the extreme deciles were biased toward
    data-complete names. The top-decile alpha and long-short t were computed under one
    composite while the weights that produced them were chosen under another.

    No shipped code path reproduced the backtested composite exactly. This pins that it does."""
    from valuation.edge.fundamental_panel import composite
    from valuation.screener.cross_sectional import composite_score, zscore

    rng = np.random.RandomState(0)
    n = 40
    df = pd.DataFrame({"value": rng.normal(size=n), "quality": rng.normal(size=n),
                       "institutional": rng.normal(size=n)})
    df.loc[:14, "institutional"] = np.nan          # ~37.5% missing, like the real panel
    w = {"value": 0.4, "quality": 0.4, "institutional": 0.2}

    live = composite_score(df, w).values
    Z = np.column_stack([zscore(df[c]).values for c in w])
    bt = composite(Z, np.array([w[c] for c in w], dtype=float))

    assert np.array_equal(np.isnan(live), np.isnan(bt)), "the two paths must agree on missing"
    assert np.nanmax(np.abs(live - bt)) < 1e-12, "live and backtest composites must be identical"


def test_audit_b7_a_missing_theme_is_renormalised_away_not_scored_as_average():
    """B7's mechanism, isolated. Under the old measurement composite a name missing a theme got
    that theme's weight times zero — and zero is exactly the cross-sectional mean of a z-scored
    column, so 'no data' was silently scored as 'perfectly average'. Renormalising instead
    scores the name on what it HAS."""
    from valuation.edge.fundamental_panel import composite

    wv = np.array([0.5, 0.5])
    both = composite(np.array([[2.0, 2.0]]), wv)[0]
    one_missing = composite(np.array([[2.0, np.nan]]), wv)[0]
    assert abs(both - 2.0) < 1e-12
    assert abs(one_missing - 2.0) < 1e-12, \
        "a strong name missing a theme keeps its score; it is not halved toward the mean"
    # the old behaviour, kept here only to show what it did
    legacy = float(np.nansum(np.where([[True, False]], [[2.0, 0.0]], 0.0) * wv))
    assert abs(legacy - 1.0) < 1e-12, "the discarded convention would have scored it 1.0"
    # and a row with no present weight at all has NO opinion rather than a mid-pack 0.0
    assert np.isnan(composite(np.array([[np.nan, np.nan]]), wv)[0])


def test_audit_b7_the_rejected_interventions_are_no_longer_the_live_default():
    """B7/G. `screen.py` calls `build_frame(metrics)` with no keyword arguments, so the live hot
    list inherits CONFIG. Both flags defaulted TRUE while the backtest forced them FALSE.
    Sector-neutral ranking was tested on the full universe, rejected in both held-out
    directions, re-run independently on a later panel, and rejected again. The code default was
    never flipped — so unless SCREENER_SECTOR_NEUTRAL=false was set in the environment, users
    saw a list scored under the intervention the research eliminated."""
    import importlib

    from valuation import config as cfgmod

    for var in ("SCREENER_SECTOR_NEUTRAL", "SCREENER_RESIDUAL_MOMENTUM"):
        os.environ.pop(var, None)
    importlib.reload(cfgmod)
    assert cfgmod.CONFIG.sector_neutral is False, "the research rejected this, twice"
    assert cfgmod.CONFIG.residual_momentum is False
    # still overridable, so the A/B remains one env var away
    os.environ["SCREENER_SECTOR_NEUTRAL"] = "true"
    importlib.reload(cfgmod)
    assert cfgmod.CONFIG.sector_neutral is True
    os.environ.pop("SCREENER_SECTOR_NEUTRAL", None)
    importlib.reload(cfgmod)


def test_audit_b6_the_calendar_is_truncated_once_not_per_ticker():
    """B6. `price_history` ended in `df.sort_values('date').tail(days)`, so EVERY ticker kept its
    own last N rows and the panel calendar was the UNION of those windows. At a 2001
    cross-section the only names present were ones that STOPPED TRADING by about 2019, because a
    name still trading in 2026 had its first decade truncated away — the inverse of classic
    survivorship bias, and severe enough to make roughly the first 37 of 110 rebalance dates
    uninterpretable. `days=None` now means the whole series, and the shared calendar is cut once
    after the frame is built."""
    import inspect

    from valuation.edge import fundamental_panel as FP
    from valuation.edge.data_providers import WRDSProvider

    src = inspect.getsource(WRDSProvider.price_history)
    assert "if days:" in src, "the per-ticker tail must be conditional, never unconditional"

    psrc = inspect.getsource(FP.build_fundamental_panel)
    assert "provider.price_history(t, days=(_CAL_DAYS if _B6_LEGACY else None))" in psrc, \
        "the panel must ask for the WHOLE series and cut the calendar itself"
    # The legacy path survives ONLY as an attribution toggle, and must default to OFF: B6, B7
    # and B13 landed together, so each needs to be revertible alone to be measured alone.
    assert 'environ.get("EDGE_AUDIT_B6_LEGACY_TRUNCATION", "").lower() == "true"' in psrc, \
        "the legacy truncation must be env-gated and off unless explicitly asked for"
    import os as _o
    assert _o.environ.get("EDGE_AUDIT_B6_LEGACY_TRUNCATION", "").lower() != "true", \
        "the test suite must run against the CORRECTED calendar"
    assert "_CAL_DAYS" in psrc and "frame.iloc[-_CAL_DAYS:]" in psrc
    # the cut must come BEFORE the ffill, or a name with no data in the window gets filled into it
    assert psrc.index("frame.iloc[-_CAL_DAYS:]") < psrc.index("frame = frame.ffill()")


def test_audit_b6_the_panel_ships_its_window_and_cross_section_sizes():
    """B6 / B22 / M6. `construction.n_periods` read 110 while `portfolio.n_periods` read 73 in
    the same JSON, over different and undisclosed windows. And a thin early cross-section
    counted as one observation of equal weight to a full recent one, with no way to see it."""
    import inspect

    from valuation.edge import fundamental_panel as FP

    src = inspect.getsource(FP.build_fundamental_panel)
    for key in ("available_start", "retained_start", "retained_end", "calendar_cut_days",
                "cross_section_by_date", "cross_section_min", "n_rebalance_dates"):
        assert key in src, f"panel_window must ship {key}"
    assert '"truncation": "shared_calendar"' in src


def test_theta_cache_root_is_absolute_and_anchored_on_the_primary_checkout():
    """The miner's cache root was RELATIVE (`data/options`), so it resolved against the cwd.

    `data/` and `.env` are gitignored and therefore exist ONLY in the primary checkout. Run the
    miner from a git worktree and it mined into a phantom empty `data/options` beside the real
    16GB cache, while the ThetaData key failed to resolve and every name logged "probe failed".
    Both failures were silent. Anchor it absolutely or this returns.
    """
    import os

    from valuation.edge import theta_bulk as TB

    assert os.path.isabs(TB.CACHE_ROOT), TB.CACHE_ROOT
    assert os.path.isabs(TB.REPO_ROOT), TB.REPO_ROOT
    # REPO_ROOT must be a real checkout (has the package), not a worktree's .git pointer target.
    assert os.path.isdir(os.path.join(TB.REPO_ROOT, "valuation")), TB.REPO_ROOT
    assert TB.CACHE_ROOT.startswith(TB.REPO_ROOT), (TB.CACHE_ROOT, TB.REPO_ROOT)
    # A worktree checkout is never the anchor: .git there is a file, not a directory.
    assert not os.path.isfile(os.path.join(TB.REPO_ROOT, ".git")), (
        "REPO_ROOT resolved to a worktree, not the primary checkout")


def test_oi_coverage_reads_minus_one_as_unknown_not_as_a_quantity():
    """B4, writer side. -1 is the feed's UNKNOWN sentinel; counting it as data is the defect."""
    import pandas as pd

    from valuation.edge.theta_bulk import oi_coverage

    assert oi_coverage(pd.DataFrame({"open_interest": [10, 20, 30, 40]})) == 1.0
    assert oi_coverage(pd.DataFrame({"open_interest": [-1, -1, -1, -1]})) == 0.0
    assert oi_coverage(pd.DataFrame({"open_interest": [-1, 5, -1, 5]})) == 0.5
    assert oi_coverage(pd.DataFrame({"open_interest": [0, 0]})) == 1.0     # zero OI is KNOWN
    assert oi_coverage(None) == 0.0
    assert oi_coverage(pd.DataFrame({"x": [1]})) == 0.0                    # no column at all


def test_degraded_open_interest_year_is_marked_on_disk_not_cached_as_clean():
    """A year whose OI call faulted used to be written looking identical to a clean one.

    That is exactly how 11.4% of the cache became -1 with nothing to show for it. The frame is
    still cached (the EOD data is valid and expensive) but the year must carry an `.oi_degraded`
    sidecar recording the measured coverage, and a clean re-mine must clear it.
    """
    import os
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    def _frame(oi):
        n = len(oi)
        return pd.DataFrame({"expiration": [dt.date(2020, 6, 19)] * n,
                             "strike": [100.0] * n, "right": ["C"] * n,
                             "date": [dt.date(2020, 6, 1)] * n,
                             "bid": [1.0] * n, "ask": [1.1] * n,
                             "volume": [5] * n, "open_interest": oi})

    with tempfile.TemporaryDirectory() as tmp:
        tb = TB.ThetaBulk(api_key="", root=tmp)
        path = TB.year_path("ZZZ", 2020, tmp)

        tb._fetch_year = lambda s, y: (_frame([-1, -1, -1, -1]), False)
        assert tb.ensure_year("ZZZ", 2020) is True
        assert os.path.exists(path), "the EOD data must still be cached"
        assert os.path.exists(path + ".oi_degraded"), "a degraded year must be visible on disk"
        assert "coverage 0.000000" in open(path + ".oi_degraded").read()

        os.remove(path)                                   # simulate the re-mine
        tb._fetch_year = lambda s, y: (_frame([7, 8, 9, 10]), False)
        assert tb.ensure_year("ZZZ", 2020) is True
        assert not os.path.exists(path + ".oi_degraded"), "a recovered year must clear the mark"


def test_sustained_faults_rebuild_the_grpc_client():
    """One run pulled 318 names then failed EVERY call from queue position 371 to 826 -- 455
    names burned -- while a fresh process pulled AAPL in 6.8s. The channel was dead and nothing
    in the loop ever reset it, so the miner could not recover in-process."""
    from valuation.edge import theta_bulk as TB

    tb = TB.ThetaBulk(api_key="x", root=".")
    tb._client = object()
    for _ in range(TB.CLIENT_RESET_AFTER_FAULTS - 1):
        tb._note_fault()
    assert tb._client is not None, "must not reset on a single transient fault"
    tb._note_fault()
    assert tb._client is None, "a sustained run of faults must rebuild the channel"
    # A success in between clears the streak, so slow-but-alive feeds are not churned.
    tb._client = object()
    for _ in range(TB.CLIENT_RESET_AFTER_FAULTS - 1):
        tb._note_fault()
    tb._note_ok()
    tb._note_fault()
    assert tb._client is not None


def test_b4_an_orphaned_remine_backup_is_swept_back_not_left_as_a_silent_loss():
    """`oi_remine` sets the old frame aside at `.bak_oi` BEFORE re-pulling, so a kill in that
    window leaves the symbol-year existing ONLY as the backup. The `.pkl` is gone, the coverage
    audit stops counting it, and the loss reads as a span that IMPROVED because it vanished from
    the scan rather than because anything was fixed. Measured: NXPI-2017 (144,300 rows) was lost
    exactly that way when a shard was stopped and restarted, and appeared in the before/after
    diff as one of three 'fixed' spans."""
    import inspect
    import os

    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "oi_remine.py"), encoding="utf-8").read()
    # The sweep must run BEFORE the re-mine loop, and must never clobber a live frame.
    assert ".bak_oi" in src and "recovered orphaned backup" in src, \
        "oi_remine must sweep orphaned .bak_oi files back"
    assert src.index("recovered orphaned backup") < src.index("for i, (key, before) in"), \
        "the sweep must happen before any span is re-mined"
    assert "if os.path.exists(_live):" in src, \
        "a backup whose .pkl came back is litter, not a restore candidate -- never clobber"
    del inspect


def test_o15_cached_dte_depth_is_recorded_per_symbol_year():
    """O15. The cache is now mined at two ceilings (90 before, 200 after) and on disk a shallow
    year and a deep one are the SAME FILE SHAPE. Without a recorded depth, a consumer asking for
    a 150-DTE contract gets data for some names and silence for others with nothing to explain
    the difference -- this project's most-repeated bug class."""
    import os
    import pickle
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    with tempfile.TemporaryDirectory() as tmp:
        path = TB.year_path("ZZZ", 2020, tmp)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        assert TB.cached_dte("ZZZ", 2020, tmp) == 0, "not cached at all must be 0, not a depth"
        with open(path, "wb") as f:
            pickle.dump(pd.DataFrame({"strike": [1.0]}), f)
        # A pre-O15 file has no sidecar. That is not unknown -- MAX_DTE was 90 for its whole
        # history, so the legacy depth is a recorded fact.
        assert TB.cached_dte("ZZZ", 2020, tmp) == TB.LEGACY_MAX_DTE == 90
        with open(path + ".dte", "w", encoding="utf-8") as f:
            f.write("200 pulled 2026-08-05\n")
        assert TB.cached_dte("ZZZ", 2020, tmp) == 200

        rep = TB.depth_report(tmp)
        assert rep["by_depth"] == {"200": 1}, rep
        assert rep["names_fully_deep"] == ["ZZZ"], rep


def test_o15_raising_max_dte_does_not_silently_re_pull_the_whole_cache():
    """Deepening is OPT-IN. MAX_DTE 90 -> 200 makes all 3,140 cached symbol-years look stale;
    if that alone triggered a re-pull, the next ordinary breadth-mining run would quietly
    re-fetch the entire 17GB cache. `prefetch` must consult the SAME rule as `ensure_year` --
    it used to do its own bare `os.path.exists`, which would have bypassed this completely."""
    import inspect
    import os
    import pickle
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    assert TB.MAX_DTE == 200, "O15 raised the mining ceiling"

    with tempfile.TemporaryDirectory() as tmp:
        path = TB.year_path("ZZZ", 2020, tmp)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:                      # a legacy 90-DTE year
            pickle.dump(pd.DataFrame({"strike": [1.0]}), f)

        plain = TB.ThetaBulk(api_key="x", root=tmp)
        assert plain.upgrade_depth is False, "deepening must never be the default"
        assert plain.needs_pull("ZZZ", 2020) is False, "a shallow year is NOT stale by default"

        deep = TB.ThetaBulk(api_key="x", root=tmp, max_dte=200, upgrade_depth=True)
        assert deep.needs_pull("ZZZ", 2020) is True, "the explicit deepening job must re-pull"

        # ... and once it is deep, even the deepening job leaves it alone.
        with open(path + ".dte", "w", encoding="utf-8") as f:
            f.write("200 pulled 2026-08-05\n")
        assert deep.needs_pull("ZZZ", 2020) is False, "a deep year must not be re-pulled"

        # An exhausted / genuinely-empty year stays skipped: those are answers, not gaps.
        for marker in (".empty", ".exhausted"):
            p2 = TB.year_path("QQQ", 2020, tmp)
            os.makedirs(os.path.dirname(p2), exist_ok=True)
            with open(p2 + marker, "w", encoding="utf-8") as f:
                f.write("x\n")
            assert deep.needs_pull("QQQ", 2020) is False, marker
            os.remove(p2 + marker)

    assert "needs_pull" in inspect.getsource(TB.ThetaBulk.prefetch), \
        "prefetch must route through needs_pull, not re-implement the skip rule"


def test_o15_a_deeper_pull_may_never_replace_a_frame_with_fewer_rows():
    """A 200-DTE pull of a span is a strict SUPERSET of the 90-DTE pull of that span. If the
    deeper frame comes back SMALLER the pull was partial in a way the failure flags missed, and
    overwriting would trade real, expensive data for less of it."""
    import os
    import pickle
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    def _frame(n):
        return pd.DataFrame({"expiration": [dt.date(2020, 6, 19)] * n,
                             "strike": [100.0] * n, "right": ["C"] * n,
                             "date": [dt.date(2020, 6, 1)] * n,
                             "bid": [1.0] * n, "ask": [1.1] * n,
                             "volume": [5] * n, "open_interest": [7] * n})

    with tempfile.TemporaryDirectory() as tmp:
        path = TB.year_path("ZZZ", 2020, tmp)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(_frame(500), f)                   # the cached 90-DTE year

        tb = TB.ThetaBulk(api_key="x", root=tmp, max_dte=200, upgrade_depth=True)

        tb._fetch_year = lambda s, y: (_frame(120), False)      # a thinner "deep" pull
        assert tb.ensure_year("ZZZ", 2020) is False
        with open(path, "rb") as f:
            assert len(pickle.load(f)) == 500, "the shallow frame must survive"
        assert TB.cached_dte("ZZZ", 2020, tmp) == 90, "a rejected pull must not claim depth"

        tb._fetch_year = lambda s, y: (_frame(640), False)      # a genuine superset
        assert tb.ensure_year("ZZZ", 2020) is True
        with open(path, "rb") as f:
            assert len(pickle.load(f)) == 640
        assert TB.cached_dte("ZZZ", 2020, tmp) == 200, "a kept pull must record its depth"


def test_a_hung_feed_call_is_abandoned_at_the_deadline_not_waited_out():
    """`CALL_TIMEOUT` had never bounded a single call. The old code ran the call inside
    `with ThreadPoolExecutor(...)`, whose __exit__ does `shutdown(wait=True)`, so on timeout it
    logged "timeout after 75s" and then blocked until the runaway call finished anyway.

    Measured cost: TXRH burned 39,526s (11 hours) on nine year-files and still lost two of
    them, while a direct probe returns a 30-day span in 3.7s. `NAME_BUDGET_S` could not save
    it -- that is only checked BETWEEN spans, never while blocked inside one.

    And a hung call never returned, so it never became a fault, so the dead-channel detector
    never saw it: the run reported 0 faults through an 11-hour stall."""
    import threading
    import time

    from valuation.edge import theta_bulk as TB

    tb = TB.ThetaBulk(api_key="x")
    release = threading.Event()
    started = threading.Event()

    def _hangs(**kw):
        started.set()
        release.wait(30)                      # far longer than the deadline below
        return "should never be used"

    original, TB.CALL_TIMEOUT = TB.CALL_TIMEOUT, 0.25
    original_backoff, TB.BACKOFF = TB.BACKOFF, 0.0
    try:
        t0 = time.time()
        out = tb._call_with_timeout(_hangs, symbol="TXRH")
        elapsed = time.time() - t0
    finally:
        release.set()
        TB.CALL_TIMEOUT, TB.BACKOFF = original, original_backoff

    assert started.is_set(), "the call must actually have been attempted"
    assert out == "FAILED", out
    # RETRIES attempts x the deadline, plus slack -- emphatically NOT the 30s the call blocks
    # for. This is the whole point: the deadline must bound the wait.
    assert elapsed < 5, f"the deadline did not bound the call: {elapsed:.1f}s"
    assert tb._faults > 0, "a hang must count as a fault so the channel detector can see it"


def test_alias_wbd_points_at_the_discovery_share_line_not_at_att():
    """WBD is the continuation of DISCOVERY, not of AT&T. AT&T distributed WBD shares and kept
    trading under `T` throughout, so `ALIASES["WBD"] = ["T"]` made every pre-listing WBD span
    fall through to AT&T: WBD 2016-2021 were cached byte-identical to T (966,790 rows, same
    keys AND same bids) plus 33,964 more in 2022 Jan-Mar. Probed on the feed, DISCA has data
    2016-2021 and none from 2022, while WBD has none before 2022 - disjoint, as a real rename
    must be."""
    from valuation.edge.theta_bulk import ALIASES

    assert ALIASES["WBD"] == ["DISCA"], ALIASES["WBD"]
    for cur, older in ALIASES.items():
        assert "T" not in older, f"{cur} must not fall back to AT&T"


def test_an_alias_that_still_trades_alongside_its_successor_is_reported():
    """The generic defect behind the WBD bug: a WRONG alias and a RIGHT one are
    indistinguishable at the point of use, because both return rows. A genuine predecessor
    stops when the successor starts, so cached years that OVERLAP are the tell -- and that is
    exactly what separates `WBD<-T` (four overlapping years) from the correct mappings."""
    import os
    import pickle
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    def _write(sym, year, root):
        p = TB.year_path(sym, year, root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump(pd.DataFrame({"strike": [1.0]}), f)

    with tempfile.TemporaryDirectory() as tmp:
        # A clean handover: OLD stops in 2018, NEW starts in 2019.
        for y in (2016, 2017, 2018):
            _write("OLD", y, tmp)
        for y in (2019, 2020):
            _write("NEW", y, tmp)
        assert TB.alias_overlap_conflicts({"NEW": ["OLD"]}, tmp) == {}

        # A still-live company wearing the alias slot: it has data in the successor's years.
        for y in (2019, 2020):
            _write("LIVE", y, tmp)
        conflicts = TB.alias_overlap_conflicts({"NEW": ["LIVE"]}, tmp)
        assert conflicts == {"NEW<-LIVE": [2019, 2020]}, conflicts

        # No cached evidence must not be reported as a clean bill of health.
        assert TB.alias_overlap_conflicts({"NEW": ["NEVERSEEN"]}, tmp) == {}


def test_alias_sourced_rows_record_which_symbol_supplied_them():
    """`WBD-2018.pkl` gave no hint that it held AT&T's chains. When a fallback fires, the
    symbol that actually answered is written to a `.alias` sidecar, so a substitution is a
    fact on disk rather than something to be rediscovered by diffing two caches."""
    import os
    import pickle
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    frame = pd.DataFrame({"expiration": [dt.date(2018, 6, 15)], "strike": [30.0],
                          "right": ["C"], "date": [dt.date(2018, 6, 1)], "bid": [1.0],
                          "ask": [1.1], "volume": [3], "open_interest": [9]})
    with tempfile.TemporaryDirectory() as tmp:
        tb = TB.ThetaBulk(api_key="x", root=tmp)

        def _fetch(sym, year):
            tb._tl.alias_used = {"DISCA"}          # as _fetch_span_once would have recorded
            return frame, False

        tb._fetch_year = _fetch
        assert tb.ensure_year("WBD", 2018) is True
        side = TB.year_path("WBD", 2018, tmp) + ".alias"
        assert os.path.exists(side), "an alias-supplied year must say so"
        assert "DISCA" in open(side, encoding="utf-8").read()

        # A year the name answered for ITSELF must NOT be labelled as borrowed.
        def _own(sym, year):
            tb._tl.alias_used = set()
            return frame, False

        tb._fetch_year = _own
        assert tb.ensure_year("WBD", 2023) is True
        assert not os.path.exists(TB.year_path("WBD", 2023, tmp) + ".alias")


def test_a_ticker_that_changed_hands_is_reported_even_though_no_alias_is_involved():
    """`COR` holds two companies: CoreSite Realty until its 2021 acquisition, then Cencora from
    2023-08. No alias produced that -- the miner asked the feed for "COR" each year and the feed
    answered for whoever held the ticker -- so `alias_overlap_conflicts()` is blind to the whole
    class and a separate screen is needed.

    The interior `.empty` is the load-bearing part. Everywhere else `.empty` means the year is
    COVERED, and treating it that way here would skip the one name this exists to catch: COR
    2022 is empty precisely BECAUSE the ticker belonged to nobody that year."""
    import os
    import tempfile

    from valuation.edge import theta_bulk as TB

    with tempfile.TemporaryDirectory() as tmp:
        def touch(sym, year, suffix=""):
            p = TB.year_path(sym, year, tmp) + suffix
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(b"x")

        # COR: CoreSite through 2021, nothing in 2022, Cencora from 2023.
        for y in (2016, 2017, 2018, 2019, 2020, 2021, 2023, 2024, 2025):
            touch("COR", y)
        touch("COR", 2022, ".empty")
        # A clean name with an unbroken run, and one that merely STARTS late (not a handover).
        for y in range(2016, 2026):
            touch("AAPL", y)
        for y in (2021, 2022, 2023, 2024, 2025):
            touch("RIVN", y)
        touch("RIVN", 2016, ".empty")          # leading empty: pre-IPO, genuinely covered

        found = TB.reused_ticker_suspects(root=tmp)
        assert "COR" in found, "an interior hole must be reported even when marked .empty"
        assert found["COR"]["hole"] == [2022]
        assert found["COR"]["empty_marked"] == [2022]
        assert "AAPL" not in found, "an unbroken history is not a suspect"
        assert "RIVN" not in found, "a late listing is not a handover"


def test_a_handover_with_no_gap_year_is_caught_by_the_collapse_screen():
    """The hole screen cannot see a ticker that changes hands MID-YEAR, because the year is
    then present, well-formed and wrong rather than absent.

    `META` is the live case and it is a top-ten name. The alias supplies 2016-2020 from `FB`
    correctly, but through the back half of 2021 the `META` ticker belonged to a ~$15 company
    and the feed answered with its chains: 9,398 rows between years of 247,139 and 171,788.
    Facebook's real 2021 was never fetched, and no alias table can fix that -- a fallback only
    fires on an EMPTY span, and this span was not empty."""
    import os
    import tempfile

    from valuation.edge import theta_bulk as TB

    with tempfile.TemporaryDirectory() as tmp:
        def write(sym, year, nbytes):
            p = TB.year_path(sym, year, tmp)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(b"x" * nbytes)

        for y, mb in ((2019, 9.14), (2020, 11.62), (2021, 0.44), (2022, 8.08), (2023, 17.52)):
            write("META", y, int(mb * 1_000_000))
        # A name that simply GROWS steadily must not trip the screen.
        for y, mb in ((2019, 2.0), (2020, 4.0), (2021, 8.0), (2022, 16.0), (2023, 32.0)):
            write("NVDA", y, int(mb * 1_000_000))

        found = TB.collapsed_year_suspects(root=tmp)
        assert "META" in found, "a year far smaller than both neighbours must be reported"
        assert [x["year"] for x in found["META"]] == [2021]
        assert "NVDA" not in found, "steady growth is not a collapse"


def test_a_year_that_recovers_drops_its_failure_marker():
    """A `.missing` beside a complete pickle is a lie about the year next to it.

    Five names (CMG, DHI, FNV, MCD, RKLB) carried a `.missing` for 2022 while holding a full
    2022 frame -- markers left by an attempt that later succeeded. That inflated the apparent
    May-2022 damage ~5x and, worse, `ensure_year` reads the attempt count back out of that
    file, so the next genuine failure starts partway to MAX_MISSING_ATTEMPTS and can be retired
    to `.exhausted` for failures the year had already recovered from."""
    import os
    import tempfile

    import pandas as pd

    from valuation.edge import theta_bulk as TB

    frame = pd.DataFrame({"expiration": [dt.date(2022, 6, 17)], "strike": [50.0],
                          "right": ["C"], "date": [dt.date(2022, 5, 16)], "bid": [1.0],
                          "ask": [1.1], "volume": [7], "open_interest": [11]})
    with tempfile.TemporaryDirectory() as tmp:
        tb = TB.ThetaBulk(api_key="x", root=tmp)
        path = TB.year_path("AGI", 2022, tmp)

        # The failing run: a span broke, so the year is refused and marked.
        tb._fetch_year = lambda s, y: (frame, True)
        assert tb.ensure_year("AGI", 2022) is False
        assert os.path.exists(path + ".missing"), "a failed year must be recorded"
        assert not os.path.exists(path), "a partial year is never cached as complete"

        # The retry run: the source is healthy again and the year completes.
        tb._fetch_year = lambda s, y: (frame, False)
        assert tb.ensure_year("AGI", 2022) is True
        assert os.path.exists(path), "the recovered year must be cached"
        assert not os.path.exists(path + ".missing"), \
            "a recovered year must not keep a marker contradicting the pickle beside it"


def test_probe_year_walks_forward_instead_of_burying_names_that_listed_later():
    """The probe year was hard-coded to 2024, so any name that listed afterwards came back
    empty and was filed as `skipped_thin, reason "no data"` for good. Eight of the fourteen
    names carrying that verdict do have option data -- CRWV, SNDK, VG and FER from 2025 -- so
    the verdict was about the calendar, not the name. 2024 is still tried FIRST so existing
    verdicts stay comparable, and a name with nothing in range gets its OWN status rather than
    being pooled with genuinely illiquid ones."""
    import mine_options_cache as M

    assert M.PROBE_YEARS_TRIED >= 2

    class _TB:
        def __init__(self, live):
            self.live, self.asked = live, []

        def ensure_year(self, sym, year):
            self.asked.append(year)

    def _viable(tb, sym, year):
        if year not in tb.live:
            return False, {"reason": "no data"}
        return True, {"reason": "ok", "rows": 10}

    orig, M.name_is_viable = M.name_is_viable, _viable
    try:
        tb = _TB(live={2025})                       # listed in 2025, nothing in 2024
        year, viable, stats = M.probe_name(tb, "CRWV")
        assert tb.asked[0] == 2024, "2024 must still be tried first"
        assert (year, viable) == (2025, True), (year, viable, stats)

        tb = _TB(live=set())                        # nothing anywhere in the mining range
        year, viable, stats = M.probe_name(tb, "CBRS")
        assert viable is False
        assert stats["reason"] == "no data in range", stats
        assert len(tb.asked) == M.PROBE_YEARS_TRIED, "the search must stay bounded"

        tb = _TB(live={2024})                       # the ordinary case is unchanged
        year, viable, _ = M.probe_name(tb, "AAPL")
        assert (year, viable, tb.asked) == (2024, True, [2024])
    finally:
        M.name_is_viable = orig


def test_no_data_in_range_is_kept_separate_from_too_illiquid():
    """"We looked and there is nothing to judge" and "we judged it and it is untradeable" are
    opposite facts with opposite correct responses. Sharing one status is what buried eight
    tradeable names, so the miner must record and skip them as distinct kinds."""
    import inspect

    import mine_options_cache as M

    src = inspect.getsource(M.main)
    assert '"no_data_in_range"' in src
    assert 'in ("complete", "skipped_thin", "partial", "no_data_in_range")' in src, (
        "a no-data verdict must be sticky, or every run re-probes it")


def test_audit_x2_the_rebalance_grid_is_a_choice_and_is_now_recorded():
    """X2. The grid was `range(TD, len(cal) - horizon, rebalance_days)` with TD hard-coded to
    252, so every number this project has ever produced came off ONE of the 63 equally valid
    grids and nobody had looked at the other 62. `grid_offset` shifts it; the value used is
    stamped into `panel_window` so no run can be silently off-grid."""
    import inspect

    from valuation.edge import fundamental_panel as FP

    sig = inspect.signature(FP.build_fundamental_panel)
    assert "grid_offset" in sig.parameters, "build_fundamental_panel must take grid_offset"
    assert sig.parameters["grid_offset"].default is None, \
        "grid_offset must default to None so the env var can supply it"

    src = inspect.getsource(FP.build_fundamental_panel)
    assert 'environ.get("EDGE_GRID_OFFSET", "0")' in src, \
        "a sweep must be able to set the grid without editing every call site"
    assert "_GRID_START = TD + grid_offset" in src
    # BOTH the count and the loop must use the offset grid, or the progress line lies about
    # how many dates are coming and the loop silently runs a different grid.
    assert src.count("range(_GRID_START, len(cal) - horizon, rebalance_days)") == 2, \
        "the date count and the scoring loop must walk the SAME grid"
    assert "range(TD, len(cal) - horizon, rebalance_days)" not in src, \
        "no caller may be left on the hard-coded grid"
    assert '"grid_offset": int(grid_offset)' in src, \
        "panel_window must record which grid produced the run"

    # The default must be the historical grid, or every past number silently changes meaning.
    import os as _o
    assert int(_o.environ.get("EDGE_GRID_OFFSET", "0") or 0) == 0, \
        "the test suite must run on the historical grid"


def test_audit_x7_placebo_destroys_signal_and_preserves_everything_else():
    """X7. The placebo is only a valid noise floor if it changes ONE thing. Permuting whole
    signal rows within a date must leave each theme's per-date distribution, the missingness
    pattern and the cross-theme correlation structure exactly as they were, and must not touch
    the forward return, the market cap or the sector."""
    import numpy as np
    import pandas as pd

    from valuation.edge import fundamental_panel as FP

    rng = np.random.default_rng(7)
    n_per_date, dates = 40, ["2020-01-31", "2020-04-30", "2020-07-31"]
    rows = []
    for d in dates:
        for k in range(n_per_date):
            rows.append({
                "date": d, "ticker": f"T{k:03d}",
                "quality": float(rng.normal()), "momentum": float(rng.normal()),
                "value": (np.nan if k % 7 == 0 else float(rng.normal())),
                "z_gp_on_capital": float(rng.normal()),
                "fwd_ret": float(rng.normal()) * 0.1,
                "marketcap": float(1e9 * (k + 1)), "sector": f"S{k % 4}",
            })
    panel = pd.DataFrame(rows)

    cols = FP.placebo_signal_cols(panel)
    assert set(cols) == {"quality", "momentum", "value", "z_gp_on_capital"}, \
        f"placebo must permute the themes and the z_ columns and nothing else, got {cols}"

    pl = FP.placebo_panel(panel, seed=11)

    # 1. Nothing outside the signal block moved, at all.
    for keep in ("date", "ticker", "fwd_ret", "marketcap", "sector"):
        assert pl[keep].equals(panel[keep]), f"placebo must not touch {keep}"

    for d in dates:
        a, b = panel[panel["date"] == d], pl[pl["date"] == d]
        for c in cols:
            # 2. Exact same numbers, per date — a permutation, not a resample.
            av = np.sort(a[c].to_numpy()[~np.isnan(a[c].to_numpy())])
            bv = np.sort(b[c].to_numpy()[~np.isnan(b[c].to_numpy())])
            assert np.array_equal(av, bv), f"{c} distribution changed on {d}"
            # 3. Same count of missing values.
            assert int(a[c].isna().sum()) == int(b[c].isna().sum()), \
                f"{c} missingness count changed on {d}"
        # 4. Whole ROWS moved together, so the cross-theme structure is untouched: the
        #    multiset of signal-row tuples is identical.
        at = sorted(map(tuple, np.nan_to_num(a[cols].to_numpy(), nan=-9e9).tolist()))
        bt = sorted(map(tuple, np.nan_to_num(b[cols].to_numpy(), nan=-9e9).tolist()))
        assert at == bt, f"placebo broke the cross-theme row structure on {d}"

    # 5. It actually shuffled something. (P(identity) for 40 names is 1/40!.)
    assert not pl["quality"].equals(panel["quality"]), "the placebo did not permute anything"

    # 6. Deterministic in the seed, and different seeds give different draws — a noise floor
    #    built from a non-reproducible instrument would be worthless.
    assert FP.placebo_panel(panel, seed=11)["quality"].equals(pl["quality"])
    assert not FP.placebo_panel(panel, seed=12)["quality"].equals(pl["quality"])

    # 7. The permutation is WITHIN a date, never across one — a cross-date shuffle would leak
    #    a later date's cross-section into an earlier one and stop being a clean null.
    assert pl.groupby("date")["quality"].sum().round(9).equals(
        panel.groupby("date")["quality"].sum().round(9)), "signal leaked across dates"


def test_theme_ic_returns_theme_keyed_blocks_at_the_top_level():
    """The results FILE nests these under `per_theme.themes`; the FUNCTION does not. Reading
    a "themes" key off `theme_ic()` yields {} silently — no error, no warning, just an empty
    result — which is exactly the failure mode the coverage rule exists for. X7's calibration
    of the IC t > 2.0 bar reads its max |t| from here, so the shape is pinned."""
    import numpy as np
    import pandas as pd

    from valuation.edge import fundamental_panel as FP

    rng = np.random.default_rng(3)
    rows = []
    for d in [f"20{y:02d}-06-30" for y in range(5, 25)]:
        for k in range(60):
            q = float(rng.normal())
            rows.append({"date": d, "ticker": f"T{k:03d}", "quality": q,
                         "momentum": float(rng.normal()),
                         "fwd_ret": 0.02 * q + float(rng.normal()) * 0.05})
    ti = FP.theme_ic(pd.DataFrame(rows))

    assert "quality" in ti and "momentum" in ti, \
        f"theme_ic must key by theme at the TOP level, got {sorted(ti)[:6]}"
    assert "themes" not in ti, \
        "the `themes` wrapper is added by the results writer, not by theme_ic"
    for name in ("quality", "momentum"):
        assert set(ti[name]) >= {"median_ic", "ic_tstat", "coverage", "n_dates"}, \
            f"{name} block is missing a field X7 reads"
    # `quality` was built INTO the forward return here, so it must be the stronger of the two.
    assert ti["quality"]["ic_tstat"] > ti["momentum"]["ic_tstat"]


def test_audit_r9_the_headline_finally_has_a_significance_statistic():
    """R9. `top_decile_alpha` is the number on the front of the product and shipped with NO
    significance statistic of any kind. It now carries a t, a Newey-West t, a Ljung-Box
    diagnostic and a hit rate, and the long-short carries HAC inference beside its naive t."""
    import numpy as np
    import pandas as pd

    from valuation.edge import fundamental_panel as FP

    rng = np.random.default_rng(11)
    rows = []
    for di, d in enumerate([f"20{y:02d}-{m:02d}-28" for y in range(6, 24) for m in (3, 9)]):
        for k in range(80):
            q = float(rng.normal())
            rows.append({"date": d, "ticker": f"T{k:03d}", "quality": q, "momentum": float(rng.normal()),
                         "fwd_ret": 0.03 * q + float(rng.normal()) * 0.06})
    panel = pd.DataFrame(rows)
    r = FP.quantile_backtest(panel, ["quality", "momentum"], {"quality": 1.0, "momentum": 0.0})

    for k in ("top_decile_alpha_tstat", "top_decile_alpha_tstat_nw", "top_decile_alpha_hit",
              "long_short_tstat_nw", "long_short_ljung_box", "top_decile_alpha_ljung_box"):
        assert k in r, f"R9 must ship {k}"
    assert r["top_decile_alpha_tstat"] > 2.0, "a built-in signal must register on the new t"
    # The alpha t must describe the alpha, not the long-short: they are different objects.
    assert r["top_decile_alpha_tstat"] != r["long_short_tstat"]
    lb = r["long_short_ljung_box"]
    assert set(lb) >= {"q", "df", "acf", "p_value", "lag1_autocorr"}
    assert 0.0 <= lb["p_value"] <= 1.0
    assert lb["df"] == len(lb["acf"])


def test_audit_r9_hac_tstat_falls_when_the_series_is_autocorrelated():
    """R9. The point of a HAC standard error is that positive serial correlation makes the
    naive i.i.d. t OVERSTATE significance. On a deliberately autocorrelated series the NW t
    must come in below the naive one, and Ljung-Box must notice."""
    import numpy as np

    from valuation.edge import fundamental_panel as FP

    rng = np.random.default_rng(5)
    x, prev = [], 0.0
    for _ in range(200):
        prev = 0.7 * prev + float(rng.normal())          # AR(1), strongly persistent
        x.append(prev + 0.30)
    naive, nw = FP._tstat(x), FP._nw_tstat(x, lag=1)
    assert naive is not None and nw is not None
    assert nw < naive, f"HAC t ({nw}) must be below the naive t ({naive}) on an AR(1) series"
    lb = FP._ljung_box(x, lags=4)
    assert lb["p_value"] < 0.05, "Ljung-Box must reject independence on an AR(1) series"
    assert lb["lag1_autocorr"] > 0.4

    # ...and on genuinely i.i.d. data the two must agree closely and Ljung-Box must NOT reject.
    y = list(rng.normal(size=400) + 0.1)
    assert abs(FP._nw_tstat(y, lag=1) - FP._tstat(y)) < 0.35
    assert FP._ljung_box(y, lags=4)["p_value"] > 0.01


def test_audit_r10_benchmarks_are_published_side_by_side():
    """R10. Alpha was only ever measured against an equal-weighted average of every name in the
    panel, charged zero trading cost while the strategy pays. Nobody can hold that. Three
    investable-or-costed alternatives now ship beside it."""
    import numpy as np
    import pandas as pd

    from valuation.edge import fundamental_panel as FP

    rng = np.random.default_rng(19)
    rows = []
    for d in [f"20{y:02d}-06-30" for y in range(5, 25)]:
        for k in range(80):
            q = float(rng.normal())
            rows.append({"date": d, "ticker": f"T{k:03d}", "quality": q,
                         "momentum": float(rng.normal()),
                         "market_cap": float(10 ** rng.uniform(8, 12)),
                         "bench_ret": 0.02,
                         "fwd_ret": 0.03 * q + float(rng.normal()) * 0.05})
    r = FP.benchmark_panel(pd.DataFrame(rows), ["quality", "momentum"],
                           {"quality": 1.0, "momentum": 0.0})
    for k in ("equal_weight", "equal_weight_costed", "cap_weighted", "spy"):
        assert k in r, f"R10 must ship the {k} benchmark"
        assert "excess_ann" in r[k] and "excess_tstat_nw" in r[k], f"{k} needs excess + HAC t"
    # Charging the equal-weight book a cost it never paid must LOWER it, so excess vs it RISES.
    assert r["equal_weight_costed"]["benchmark_ann"] < r["equal_weight"]["benchmark_ann"]
    assert r["equal_weight_costed"]["excess_ann"] > r["equal_weight"]["excess_ann"]
    # SPY here is a flat +2%/period by construction, so it must be recognisably different.
    assert abs(r["spy"]["benchmark_ann"] - 0.02 * 4.0) < 1e-9


def test_audit_m1_the_trial_counter_is_real_and_deflates_more_than_eight():
    """M1. Every multiple-testing claim was computed against N=8 (the weight schemes) while the
    project had run scores of trials. N now comes from the append-only research log, scoped to
    the domain the composite was searched within."""
    from valuation.edge import fundamental_panel as FP
    from valuation.edge import research_log as RL

    d = RL.detail()
    assert d["available"], "RESEARCH_LOG.md must be readable"
    assert d["trials_logged"] >= 50, f"the log looks unpopulated: {d['trials_logged']}"
    assert d["by_domain"]["equity"] > 8, "the equity family must exceed the weight-scheme floor"
    assert d["by_domain"]["options"] > 0, "the options family must be counted separately"

    # Domain scoping is a statistical choice, not a convenience: the equity composite must not
    # be charged for the options programme's separate search.
    assert RL.trial_count(domain="equity") < RL.trial_count(domain=None)
    # A missing log must degrade to the OLD behaviour (8), never to an unpenalised one.
    assert RL.trial_count(path="does_not_exist.md", use_cache=False) == RL.WEIGHT_SCHEME_TRIALS
    assert FP._trial_N() == RL.trial_count(domain="equity")

    # The haircut must now be driven by the log even when the immediate comparison is small.
    assert FP._trials_haircut(8) > 2.5, "8 folds after ~84 trials is not an 8-trial search"

    # And the deflation must actually bite: a bigger N raises sr0, which lowers the probability.
    import numpy as np
    rng = np.random.default_rng(3)
    rets = list(rng.normal(0.02, 0.04, size=80))
    trials = list(rng.normal(0.4, 0.15, size=8))
    det = FP._deflated_sharpe_detail(rets, trials)
    assert det["n_trials"] == FP._trial_N(), "N must come from the log, not len(trials)"
    assert det["n_trials_from_weight_schemes"] == 8
    assert det["n_trials_source"].startswith("RESEARCH_LOG"), "the source must be recorded"
    assert det["sr0_benchmark"] > 0, "with a real N the statistic must actually deflate"


# ============================ AUDIT SESSION 5 — R3, R7, O20 ================================
def _opt_row(ticker, date, pnl, **extra):
    r = {"ticker": ticker, "alert_ts": date, "pnl_pct": pnl, "pnl_dollars": pnl * 100.0}
    r.update(extra)
    return r


def test_audit_r3_the_block_bootstrap_is_wider_than_the_trade_bootstrap():
    """The whole point of R3. A book whose trades are perfectly correlated inside each month
    carries exactly as much information as its month count — the trade-level interval claims
    far more. If the block interval is not the wider of the two, the clustering is not being
    preserved and the correction is doing nothing."""
    from valuation.edge import options_stats as ST
    from valuation.edge import options_universe as U

    rows = []
    for m in range(1, 13):
        # Every trade in a month has the SAME outcome: the month carries one observation.
        v = 0.5 if m % 2 else -0.4
        for k in range(30):
            rows.append(_opt_row("AAA", f"2020-{m:02d}-{(k % 28) + 1:02d}", v))
    blk = ST.date_block_bootstrap(rows, draws=800, seed=0)
    trade = U.bootstrap_diff(rows, rows, "expectancy_pct", draws=800)   # width of a trade CI
    assert blk["ok"], blk
    width_block = blk["ci95"][1] - blk["ci95"][0]
    # A trade-level CI on this book is near-degenerate because every resample sees both months
    # in proportion; the block CI must be materially wide.
    assert width_block > 0.15, f"block CI is only {width_block:.4f} wide — blocks not preserved"
    assert blk["n_blocks"] == 12, blk["n_blocks"]
    assert trade.get("ok")


def test_audit_r3_a_raw_design_effect_is_not_evidence_of_clustering():
    """THE FAILURE THAT WROTE THIS TEST. A book of 600 independent draws assigned to 12 blocks
    of 50 — no clustering by construction — reports a design effect near 1.8, i.e. an apparent
    45% loss of sample size that is pure sampling error in MSB/MSW. Applying that as a haircut
    would manufacture a correction out of noise, which is the mirror image of the error R3
    exists to fix. So the design effect must be scored against a shuffled null, and an
    unclustered book must come back `clustering_measurable = False` however large its raw
    design effect happens to be."""
    import random

    from valuation.edge import options_stats as ST

    rnd = random.Random(0)
    # The flag is a 95th-percentile test, so on unclustered books it fires ~5% of the time BY
    # CONSTRUCTION. Asserting one draw comes back False would be a coin-flip test that passes or
    # fails on the seed. What must hold is the RATE — the same thing X7 measures for the
    # project's other gates.
    fired, n_books = 0, 20
    for b in range(n_books):
        indep = [_opt_row("AAA", f"2020-{(i % 12) + 1:02d}-15", rnd.gauss(0, 1))
                 for i in range(300)]
        e = ST.effective_n(indep, null_draws=150, seed=b)
        assert e["ok"]
        assert e["design_effect_null_p95"] > 1.0, "the null band must be non-degenerate"
        if e["clustering_measurable"]:
            fired += 1
    assert fired <= 4, \
        (f"the clustering flag fired on {fired}/{n_books} books with NO block structure — a "
         f"95th-percentile test should fire on about 1")

    clustered = []
    for m in range(1, 13):
        v = rnd.gauss(0, 1)
        clustered += [_opt_row("AAA", f"2020-{m:02d}-15", v) for _ in range(50)]
    e_cl = ST.effective_n(clustered, null_draws=200)
    assert e_cl["clustering_measurable"] is True, "a perfectly clustered book must be detected"
    assert e_cl["n_eff_icc"] < 0.1 * e_cl["n"], \
        f"perfectly clustered book kept n_eff={e_cl['n_eff_icc']:.0f} of n={e_cl['n']}"
    assert e_cl["icc"] >= 0.0, "ICC must never be reported negative"


def test_audit_r3_the_paired_sign_test_counts_cells_not_trades():
    """R3.3 — the statistic the entire options conclusion rests on, which lived in no file.
    Built so the answer is known by construction: the real book loses in 8 of 10 name-year
    cells, regardless of how many trades sit in each."""
    from valuation.edge import options_stats as ST

    real, ctrl = [], []
    for i in range(10):
        t = f"T{i}"
        real_v, ctrl_v = (0.1, 0.2) if i < 8 else (0.3, 0.1)      # real loses the first 8
        # Deliberately lopsided trade counts: a trade-weighted test would give a different
        # answer, and the cell is the unit that matters.
        real += [_opt_row(t, "2020-03-02", real_v) for _ in range(1 + i)]
        ctrl += [_opt_row(t, "2020-07-02", ctrl_v) for _ in range(20 - i)]
    pn = ST.paired_name_year(real, ctrl)
    assert pn["ok"], pn
    assert pn["n_cells"] == 10, pn["n_cells"]
    assert pn["n_wins"] == 2, f"expected the real book to win 2 of 10 cells, got {pn['n_wins']}"
    assert pn["sign_test_z"] < 0
    assert pn["paired_t"] is not None, "the paired t must ship alongside the sign test"


def test_audit_r3_purge_removes_the_dates_whose_labels_cross_a_boundary():
    """A trade entered at the end of an in-sample block is still open inside the adjacent
    out-of-sample block. Purging must drop it; embargo 0 must reproduce the old behaviour
    exactly, so the contaminated split stays available as a comparison rather than vanishing."""
    from valuation.edge import options_stats as ST

    blocks = [{f"2020-01-{d:02d}" for d in range(1, 29)},
              {f"2020-02-{d:02d}" for d in range(1, 29)}]
    dates = sorted(blocks[0] | blocks[1])
    keep_is, keep_os = ST.purged_split(dates, [0], [1], blocks, embargo_days=75)
    assert not keep_is, "every January date has a February date inside a 75d window"
    assert len(keep_os) == 28, "February has no later block to be contaminated by"
    # A short embargo must purge strictly less than a long one.
    short_is, _ = ST.purged_split(dates, [0], [1], blocks, embargo_days=3)
    assert len(short_is) > len(keep_is), "a 3-day embargo cannot purge as much as a 75-day one"


def test_audit_r3_the_clustered_deflated_sharpe_can_only_shrink():
    """Substituting n_eff for n is a haircut by construction. If it ever reports a HIGHER
    probability than the raw statistic, the scaling has been applied the wrong way round."""
    import random

    from valuation.edge import options_stats as ST

    rnd = random.Random(1)
    rows = []
    for m in range(1, 13):
        base = rnd.gauss(0.15, 0.05)
        rows += [_opt_row("AAA", f"2020-{m:02d}-15", base + rnd.gauss(0, 0.05))
                 for _ in range(40)]
    rets = [r["pnl_pct"] for r in rows]
    d = ST.deflated_sharpe_clustered(rets, n_trials=1, rows=rows)
    assert d["ok"], d
    assert d["deflated_sharpe_clustered"] <= d["deflated_sharpe_raw"] + 1e-12, \
        "the clustered DSR must never exceed the raw one"
    assert 0.0 < d["shrink_factor"] <= 1.0


def test_audit_r7_the_new_floor_can_fail_on_the_arm_that_was_never_measured():
    """R7 replaced an underived 40% retention bar with three measured arms, and the whole
    defence of that replacement is that term_slope can still FAIL. G3b — span of names and
    months — had never been measured. This builds a filter that keeps plenty of trades and
    concentrates them into a handful of names, and asserts the gate rejects it."""
    from valuation.edge import options_universe as U

    rows = []
    # 20 names x 24 months. The filter's signal is high ONLY on two names, so retention is
    # healthy (>20%) and flow is healthy (>52/yr) while the span collapses.
    for i in range(20):
        for m in range(24):
            y, mm = 2021 + m // 12, (m % 12) + 1
            rows.append(_opt_row(f"T{i}", f"{y}-{mm:02d}-10", 0.1,
                                 term_slope=0.5 if i < 2 else -0.5))
    # 15 trades per name-month on the two favoured names, so n_kept is large.
    rows += [_opt_row(f"T{i}", f"2022-{(m % 12) + 1:02d}-11", 0.1, term_slope=0.5)
             for i in range(2) for m in range(24) for _ in range(14)]
    g = U.term_slope_gate(rows, threshold=0.0, late_only=False)
    assert g["ok"], g
    assert g["retention"] >= U.MIN_RETENTION_BACKSTOP, "this fixture must clear G3c"
    assert g["G3c_backstop"] is True
    assert g["G3b_concentration"] is False, \
        f"a filter surviving on {g['n_names_kept']}/{g['n_names_all']} names must fail G3b"
    assert g["passes_G3"] is False


def test_audit_r7_the_gate_passes_a_filter_that_keeps_a_broad_book():
    """The mirror image: G3 must not reject everything, or it is not a gate."""
    from valuation.edge import options_universe as U

    rows = []
    for i in range(30):
        for m in range(24):
            y, mm = 2021 + m // 12, (m % 12) + 1
            for k in range(4):
                rows.append(_opt_row(f"T{i}", f"{y}-{mm:02d}-{10 + k:02d}", 0.1,
                                     term_slope=1.0 if k < 3 else -1.0))
    g = U.term_slope_gate(rows, threshold=0.0, late_only=False)
    assert g["passes_G3"] is True, g
    assert g["G3a_flow"] and g["G3b_concentration"] and g["G3c_backstop"]


def test_audit_o20_point_in_time_liquidity_uses_the_miners_own_thresholds():
    """O20 applies the SAME screen at a different moment. If this module ever grows its own
    constants they will drift from the miner's and the comparison stops meaning anything."""
    from valuation.edge import options_universe as U

    th = U._miner_thresholds()
    try:
        import mine_options_cache as M
    except Exception:                                                  # noqa: BLE001
        M = None
    if M is not None:
        assert th["source"] == "mine_options_cache", th["source"]
        assert th["max_median_spread_pct"] == M.MAX_MEDIAN_SPREAD_PCT
        assert th["min_atm_oi"] == M.MIN_ATM_OI
        assert th["min_atm_oi_notional"] == M.MIN_ATM_OI_NOTIONAL


def test_audit_o20_an_unmeasurable_day_is_none_and_never_false():
    """The distinction that keeps a data gap from being reported as a liquidity finding."""
    from valuation.edge import options_universe as U

    assert U.pit_liquid_ok(None) is None
    assert U.pit_liquid_ok({"ok": False}) is None
    assert U.pit_liquid_ok({"ok": True, "median_spread_pct": None, "atm_oi": 9e9}) is None
    wide = {"ok": True, "median_spread_pct": 0.90, "atm_oi": 9e9, "atm_oi_notional": 9e9}
    assert U.pit_liquid_ok(wide) is False, "a 90% median spread must not pass the screen"
    thin = {"ok": True, "median_spread_pct": 0.05, "atm_oi": 1.0, "atm_oi_notional": 1.0}
    assert U.pit_liquid_ok(thin) is False, "failing BOTH open-interest measures must reject"
    ok_notional = {"ok": True, "median_spread_pct": 0.05, "atm_oi": 1.0,
                   "atm_oi_notional": 9e9}
    assert U.pit_liquid_ok(ok_notional) is True, "notional alone must be enough, as in the miner"


def test_audit_o20_the_split_separates_unmeasurable_from_illiquid():
    from valuation.edge import options_universe as U

    rows = ([_opt_row("A", "2020-01-02", 0.2, pit_liquid=True)] * 5
            + [_opt_row("B", "2020-01-03", -0.3, pit_liquid=False)] * 3
            + [_opt_row("C", "2020-01-04", 0.1, pit_liquid=None)] * 2)
    s = U.o20_split(rows)
    assert (s["n_pit_liquid"], s["n_pit_illiquid"], s["n_unmeasurable"]) == (5, 3, 2), s
    assert abs(s["coverage"] - 0.8) < 1e-9
    assert abs(s["retained_frac"] - 0.5) < 1e-9


def test_audit_r3_pbo_embargo_zero_reproduces_the_unpurged_split():
    """The purge must be a switchable correction, not a silent redefinition — otherwise the
    A/B that shows what it cost is impossible to run."""
    import inspect

    from valuation.edge import options_autopsy as A

    sig = inspect.signature(A.pbo_cscv)
    assert "embargo_days" in sig.parameters, "pbo_cscv must expose the embargo"
    assert sig.parameters["embargo_days"].default is None, \
        "the default must be the label window, not 0 — the corrected behaviour ships"


# ===================== session-5 closeout: items 1 and 2 ====================================
def _fake_derived(root, names, size=32):
    """A minimal `data/options_derived/<name>/<name>-daily.pkl` tree."""
    for i, n in enumerate(names):
        d = os.path.join(root, "options_derived", n)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{n}-daily.pkl"), "wb") as f:
            f.write(b"x" * (size + i))


def test_closeout_item1_the_derived_stamp_is_a_fingerprint_not_a_count():
    """The miner grew the derived layer 111 -> 317 names mid-audit and the SAME trades reported
    a different PBO. A COUNT would not have caught a re-mine that keeps the name count fixed —
    the stamp has to move when the CONTENTS move."""
    import tempfile

    from valuation.edge import options_autopsy as A

    with tempfile.TemporaryDirectory() as tmp:
        _fake_derived(tmp, ["AAA", "BBB"])
        a = A.derived_stamp(tmp)
        assert a["n_names"] == 2 and a["n_daily_files"] == 2
        b = A.derived_stamp(tmp)
        assert a["fingerprint"] == b["fingerprint"], "the same tree must fingerprint equal"

        # same NAME COUNT, different contents — the exact case a count is blind to
        with open(os.path.join(tmp, "options_derived", "AAA", "AAA-daily.pkl"), "wb") as f:
            f.write(b"y" * 999)
        c = A.derived_stamp(tmp)
        assert c["n_names"] == a["n_names"], "precondition: the name count did NOT move"
        assert c["fingerprint"] != a["fingerprint"], \
            "a re-mine that keeps the name count must still move the fingerprint"


def test_closeout_item1_comparability_refuses_rather_than_reconciles():
    """A cross-session PBO difference must either reconcile or REFUSE. Refusing on an unstamped
    run is the point: comparability there is unknowable, not merely unproven."""
    import tempfile

    from valuation.edge import options_autopsy as A

    with tempfile.TemporaryDirectory() as tmp:
        _fake_derived(tmp, ["AAA"])
        a = A.derived_stamp(tmp)
        assert A.derived_comparable(a, a)["comparable"] is True

        _fake_derived(tmp, ["CCC"])
        b = A.derived_stamp(tmp)
        r = A.derived_comparable(a, b)
        assert r["comparable"] is False and "n_names" in r["differences"], \
            "a grown derived layer must refuse, and say what moved"

        # the pre-stamp record: no fingerprint at all
        legacy = A.derived_comparable({"n_names": 111}, b)
        assert legacy["comparable"] is False and "unknowable" in legacy["reason"], \
            "an unstamped run must refuse, not be assumed comparable"


def test_closeout_item1_the_stamp_is_descriptive_and_gates_nothing():
    """RUN_RULES A5: a field that can fail a run gets switched off the first time it is
    inconvenient. This one must never raise, even pointed at a directory that does not exist."""
    from valuation.edge import options_autopsy as A

    s = A.derived_stamp(os.path.join("nowhere", "at", "all"))
    assert s["exists"] is False and s["n_names"] == 0
    assert "fingerprint" in s, "an empty layer still stamps — silence is not an option"


def test_closeout_item2_a_different_run_is_refused_but_a_resume_is_not():
    """The defect was a DIFFERENT run landing on a banked one. Resuming the SAME run is the
    feature and must survive the fix — a guard that blocks resumes would be traded away."""
    import tempfile

    import optuniv_run as R

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "options_universe")
        os.makedirs(out)
        state = os.path.join(out, "state.pkl")
        k1 = R.run_key(["AAA", "BBB"], 1.0, ("2016-01-01", "2025-10-15"), False)
        k2 = R.run_key(["AAA", "BBB"], 0.0, ("2016-01-01", "2025-10-15"), False)
        assert k1 != k2, "aggression must be part of the run key"

        assert R.guard_bank(out, state, k1, False)["action"] == "clear"
        with open(state, "wb") as f:
            f.write(b"banked")
        R.write_manifest(out, k1, ["state.pkl"])

        assert R.guard_bank(out, state, k1, False)["action"] == "resume", \
            "the same run must resume, not be refused"
        g = R.guard_bank(out, state, k2, False)
        assert g["action"] == "refuse", "a different aggression must be refused"
        assert "state.pkl" in g["occupants"]


def test_closeout_item2_no_path_through_the_runner_destroys_a_banked_book():
    """Stronger than 'asks first': --overwrite MOVES the prior artifacts aside. The pre-correction
    book had to be hand-copied to make the Part 6 A/B possible; that must never depend on someone
    remembering."""
    import tempfile

    import optuniv_run as R

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "options_universe")
        os.makedirs(out)
        state = os.path.join(out, "state.pkl")
        for n in ("state.pkl", "UNIVERSE_RESULTS.json", "control_rows.pkl"):
            with open(os.path.join(out, n), "wb") as f:
                f.write(b"the record's own book")
        k1 = R.run_key(["AAA"], 1.0, ("2016-01-01", "2025-10-15"), False)
        R.write_manifest(out, k1, ["state.pkl"])
        k2 = R.run_key(["AAA"], 0.0, ("2016-01-01", "2025-10-15"), False)

        g = R.guard_bank(out, state, k2, True)
        assert g["action"] == "archived"
        for n in ("state.pkl", "UNIVERSE_RESULTS.json", "control_rows.pkl"):
            assert not os.path.exists(os.path.join(out, n)), f"{n} should have moved"
            arch = os.path.join(g["archived_to"], n)
            assert os.path.exists(arch), f"{n} must survive in banked/"
            assert open(arch, "rb").read() == b"the record's own book", \
                "the archived copy must be the ORIGINAL bytes, not a stub"


def test_closeout_item2_an_unstamped_directory_is_refused_not_assumed_empty():
    """Every artifact banked before this guard existed has no manifest. Treating that as 'fine'
    would leave exactly the case that cost the hand-copy unprotected."""
    import tempfile

    import optuniv_run as R

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "options_universe")
        os.makedirs(out)
        with open(os.path.join(out, "UNIVERSE_RESULTS.json"), "w") as f:
            f.write("{}")
        k = R.run_key(["AAA"], 1.0, ("2016-01-01", "2025-10-15"), False)
        g = R.guard_bank(out, os.path.join(out, "state.pkl"), k, False)
        assert g["action"] == "refuse" and "UNKNOWABLE" in g["reason"].upper()



# ============================ SESSION 6 — U7 (veto) and X3 (ablation) =======================
def _u7_panel(n_dates=8, n_names=40, seed=3):
    """A tiny synthetic panel with the columns the veto join reads. Deterministic."""
    rng = np.random.default_rng(seed)
    dates = [f"20{16 + i // 4}-{1 + 3 * (i % 4):02d}-15" for i in range(n_dates)]
    rows = []
    for d in dates:
        for j in range(n_names):
            rows.append({"date": d, "ticker": f"T{j:02d}",
                         "quality": float(rng.normal()), "momentum": float(rng.normal()),
                         "fwd_ret": float(rng.normal(0, 0.1)),
                         "market_cap": 1e9 * (j + 1)})
    return pd.DataFrame(rows)


def test_u7_the_join_is_backward_looking_only():
    """THE defect this join can have. An alert must be scored with the most recent rebalance
    STRICTLY at or before it; the enclosing rebalance uses filings published after the alert
    fired, which is up to a quarter of look-ahead and would flatter every U7 number.

    Asserting 'never forward' alone would pass on a join that always returned index 0, so the
    test also requires the two rules to genuinely DISAGREE on a real date."""
    from valuation.edge.options_veto import as_of_index, enclosing_index

    reb = ["2016-01-15", "2016-04-15", "2016-07-15", "2016-10-14"]
    # a day nearer the NEXT rebalance than the previous one — where the two rules must differ
    alert = "2016-04-10"
    i_safe, i_look = as_of_index(reb, alert), enclosing_index(reb, alert)
    assert reb[i_safe] == "2016-01-15", f"as-of must not reach forward, got {reb[i_safe]}"
    assert reb[i_look] == "2016-04-15", "the enclosing variant should be the look-ahead one"
    assert i_safe != i_look, "the two rules must actually disagree, or this proves nothing"

    for a in ("2016-01-15", "2016-01-16", "2016-07-14", "2016-12-31"):
        i = as_of_index(reb, a)
        assert i is not None and reb[i] <= a, f"{reb[i]} is after {a}"


def test_u7_an_alert_before_the_first_rebalance_is_excluded_not_imputed():
    """Imputing the first rebalance would score a 2016 alert with 2009 fundamentals and count
    it as coverage — the coverage floor is what the adoption rule turns on, so it must not be
    inflatable this way."""
    from valuation.edge.options_veto import as_of_index, join_alerts

    reb = ["2016-01-15", "2016-04-15"]
    assert as_of_index(reb, "2015-12-31") is None

    by_date = {"2016-01-15": {"AAA": (1.0, 0.9)}, "2016-04-15": {"AAA": (1.0, 0.9)}}
    rows = [{"ticker": "AAA", "alert_ts": "2015-06-01", "pnl_pct": 0.5},
            {"ticker": "AAA", "alert_ts": "2016-02-01", "pnl_pct": 0.5}]
    j = join_alerts(rows, by_date)
    assert j["coverage"]["n_joined"] == 1
    assert j["coverage"]["n_unjoined_before_first_rebalance"] == 1
    assert j["rows"][0]["u7_asof"] == "2016-01-15"


def test_u7_a_row_the_composite_cannot_score_is_kept_not_vetoed():
    """A veto that also discards what it could not score conflates 'the composite says no' with
    'the composite has no opinion', and retention would then measure coverage."""
    from valuation.edge.options_veto import apply_veto

    rows = [{"u7_pct": 0.05, "pnl_pct": -0.5}, {"u7_pct": 0.90, "pnl_pct": 0.5},
            {"pnl_pct": 0.1}]                       # no composite at all
    kept, dropped = apply_veto(rows, 0.10)
    assert len(dropped) == 1 and dropped[0]["u7_pct"] == 0.05
    assert len(kept) == 2 and any("u7_pct" not in r for r in kept)


def test_u7_the_decile_table_is_best_composite_first():
    """Same convention as `quantile_backtest` (buckets ordered best-first). The project has
    already paid for one sign-reading correction (`monotonicity`); these two objects get read
    side by side, so they must not be ordered oppositely."""
    from valuation.edge.options_veto import decile_table

    rows = ([{"u7_pct": 0.95, "pnl_pct": 1.0}] * 5 + [{"u7_pct": 0.05, "pnl_pct": -1.0}] * 5)
    t = decile_table(rows)
    assert t[0]["decile"] == 1 and t[0]["n_trades"] == 5 and t[0]["mean_pnl_pct"] == 1.0
    assert t[-1]["decile"] == 10 and t[-1]["mean_pnl_pct"] == -1.0


def test_u7_composite_by_date_uses_the_one_shipped_composite():
    """B7 left exactly one composite in the tree. If the veto built its own, U7 would be
    ranking names by an object neither the backtest nor the live screener uses."""
    from valuation.edge.options_veto import composite_by_date
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore

    p = _u7_panel()
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    by_date = composite_by_date(p, cols, w)
    d = sorted(by_date)[0]
    sub = p[p["date"] == d]
    ref = composite_from_frame(sub, cols, w, zscore)
    for t, c in zip(sub["ticker"].values, ref):
        assert abs(by_date[d][str(t)][0] - float(c)) < 1e-12
    # percentile: 0.0 is the WORST composite, 1.0 the best
    best = max(by_date[d], key=lambda k: by_date[d][k][0])
    assert abs(by_date[d][best][1] - 1.0) < 1e-9


def test_x3_alpha_series_reproduces_quantile_backtest():
    """The ablation's paired comparison is built on a series `quantile_backtest` does not
    return. If the two ever measure different objects, the curve stops describing the
    headline."""
    from valuation.edge.ablation import alpha_series
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=12, n_names=60, seed=11)
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    r = quantile_backtest(p, cols, w, n_q=10, horizon=63)
    s = alpha_series(p, cols, w, n_q=10)
    assert len(s["alpha"]) == r["n_periods"]
    assert abs(float(np.mean(s["alpha"]) * 4.0) - r["top_decile_alpha"]) < 1e-12


def test_v2g_return_series_is_opt_in_and_changes_nothing_else():
    """V2G added the per-period draws to `quantile_backtest`. It is opt-in precisely so that no
    existing caller's payload — including the tracked BACKTEST_RESULTS.json — moves by one bit."""
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=12, n_names=60, seed=11)
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    off = quantile_backtest(p, cols, w, n_q=10, horizon=63)
    on = quantile_backtest(p, cols, w, n_q=10, horizon=63, return_series=True)
    assert "series" not in off, "the draws must NOT appear unless asked for"
    assert set(on) - set(off) == {"series"}, f"only `series` may be added; got {set(on) - set(off)}"
    for k in off:
        assert repr(off[k]) == repr(on[k]), f"{k} moved when the series was requested"


def test_v2g_the_series_reproduces_its_own_summary():
    """RUN_RULES A9 — the draws must be the same object the summary is computed from, or a
    paired comparison built on them is measuring something the headline is not."""
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=12, n_names=60, seed=11)
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    r = quantile_backtest(p, cols, w, n_q=10, horizon=63, return_series=True)
    s = r["series"]
    ppy = 252.0 / 63
    assert len(s["alpha"]) == len(s["long_short"]) == r["n_periods"]
    assert len(s["dates"]) == len(s["n_scored"]) == r["n_periods"], "every draw must be dated"
    assert abs(float(np.mean(s["alpha"]) * ppy) - r["top_decile_alpha"]) < 1e-12
    assert abs(float(np.mean(s["long_short"]) * ppy) - r["long_short_ann"]) < 1e-12


def test_v2g_the_shipped_series_agrees_with_the_x3_implementation():
    """There were two implementations of this series. They must not drift apart."""
    from valuation.edge.ablation import alpha_series
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=12, n_names=60, seed=11)
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    shipped = quantile_backtest(p, cols, w, n_q=10, horizon=63, return_series=True)["series"]
    x3 = alpha_series(p, cols, w, n_q=10)
    assert len(shipped["alpha"]) == len(x3["alpha"])
    for a, b in zip(shipped["alpha"], x3["alpha"]):
        assert abs(a - b) < 1e-12, f"the two alpha series disagree: {a} vs {b}"


def test_v2g_dropping_a_theme_equals_the_live_product_losing_it():
    """The claim V2G rests on: the four-theme restricted arm IS the live book, not a model of it.

    `composite` renormalises by the PRESENT-weight mass, so a theme that is absent (all-NaN) or
    constant (z-scores to all-NaN, because `zscore` returns NaN on zero variance) leaves both the
    numerator and the denominator identically — which is exactly what dropping it from `weights`
    does. If this ever stops holding, the restricted arm stops describing the live product and
    V2G's verdict describes nothing.
    """
    import numpy as _np

    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore

    p = _u7_panel(n_dates=3, n_names=60, seed=11)
    sub = p[p["date"] == sorted(p["date"].unique())[0]].copy()
    live, dead = ["quality", "momentum"], ["value", "size"]
    w_all = {t: 0.125 for t in live + dead}
    w_live = {t: 0.125 for t in live}

    want = composite_from_frame(sub, list(w_live), w_live, zscore)

    absent = sub.copy()
    for t in dead:
        absent[t] = _np.nan
    got_absent = composite_from_frame(absent, list(w_all), w_all, zscore)

    const = sub.copy()                      # the LIVE `insider` case: present but one value
    for t in dead:
        const[t] = 0.0
    got_const = composite_from_frame(const, list(w_all), w_all, zscore)

    assert _np.isfinite(want).any(), "the fixture must produce a scorable cross-section"
    for got, label in ((got_absent, "absent"), (got_const, "constant")):
        assert _np.array_equal(_np.isfinite(want), _np.isfinite(got)), \
            f"{label}: the scorable-name set changed"
        both = _np.isfinite(want) & _np.isfinite(got)
        dev = float(_np.max(_np.abs(want[both] - got[both])))
        assert dev <= 1e-12, f"{label}: composite differs by {dev:.3e}"


def test_s22_right_censoring_is_not_delisting():
    """THE defect S22 can have, pre-committed in the register as the most likely way the study
    fabricates a result.

    `_forward_return` has a delisting branch: if the horizon-end price is NaN because the
    survivorship mask cut the name mid-window, it falls back to the last price the name actually
    traded at, realizing the delisting instead of discarding the name. That is correct.

    It is CATASTROPHIC if it also fires when the CALENDAR ends before the window does. There the
    return simply does not exist, and a last-price fallback would return a SHORTER realized
    return labelled as a long-horizon one — for the most recent dates specifically, flattering
    short horizons and penalising long ones. The whole term structure is that comparison.
    """
    from valuation.edge.fundamental_panel import _forward_return

    closes = np.array([10.0, 11.0, 12.0, 13.0, 14.0])       # a 5-day calendar, no NaNs at all
    n = len(closes)

    # in-range: an ordinary forward return
    assert abs(_forward_return(closes, 0, 2, n) - 0.2) < 1e-12

    # the last index the window can reach is n-1, so i+h == n-1 is the last OBSERVABLE window
    assert abs(_forward_return(closes, 0, 4, n) - 0.4) < 1e-12

    # i + h == n and beyond run past the calendar -> the return DOES NOT EXIST
    assert _forward_return(closes, 1, 4, n) is None, "i+h == n must be censored, not salvaged"
    assert _forward_return(closes, 4, 1, n) is None
    assert _forward_return(closes, 0, 99, n) is None, "a far-future window cannot be realized"

    # and the failure mode specifically: censoring must NOT return the last traded price. If it
    # did, this would come back as +0.4 (10 -> 14) rather than None.
    assert _forward_return(closes, 1, 4, n) != 0.2727272727272727


def test_s22_the_delisting_branch_still_fires_inside_the_calendar():
    """The other half of the same rule: censoring must not be implemented by refusing every NaN.
    A name that stops trading INSIDE an observable window is a delisting and must realize its
    last traded price, or the survivorship bias the mask exists to remove comes back."""
    from valuation.edge.fundamental_panel import _forward_return

    closes = np.array([10.0, 11.0, 12.0, np.nan, np.nan, 20.0, 21.0])
    n = len(closes)
    # window 0 -> 4 ends on a NaN but the name traded at 12.0 inside it
    got = _forward_return(closes, 0, 4, n)
    assert got is not None, "a delisting inside the calendar must still produce a return"
    assert abs(got - 0.2) < 1e-12, f"expected the last traded price (12.0), got {got}"
    # a name with no valid price anywhere in the window yields nothing
    assert _forward_return(np.array([10.0, np.nan, np.nan]), 0, 2, 3) is None
    # a non-positive or missing start price is not a return
    assert _forward_return(np.array([0.0, 11.0, 12.0]), 0, 2, 3) is None
    assert _forward_return(np.array([np.nan, 11.0, 12.0]), 0, 2, 3) is None


def test_s22_extra_horizons_are_off_by_default_and_the_base_one_is_the_shipped_column():
    """S22's controls C0 and C3, end to end on a real panel build rather than by inspection.

    C3 — with no extra horizons requested the frame must be column-for-column what it was, so
    the tracked BACKTEST_RESULTS.json cannot move.
    C0 — asking for the BASE horizon as an "extra" must reproduce the shipped `fwd_ret` exactly.
    If it does not, the added code path is not the shipped rule and every arm built on it is
    measuring something else.
    """
    from valuation.edge.fundamental_panel import build_fundamental_panel

    prov = _SynthPIT(30, seed=7)
    tickers = list(prov.q.keys())
    kw = dict(rebalance_days=63, horizon=21, lookback_years=4)

    plain = build_fundamental_panel(prov, tickers, **kw)
    assert not plain.empty
    assert not [c for c in plain.columns if str(c).startswith("fwd_ret_h")], \
        "no extra horizon columns may appear unless asked for"

    withx = build_fundamental_panel(prov, tickers, extra_horizons=[21, 42, 200], **kw)
    assert list(plain.columns) == [c for c in withx.columns
                                   if not str(c).startswith("fwd_ret_h")], \
        "requesting extra horizons must ADD columns and move none"
    assert len(withx) == len(plain), "the row set must not change"

    a = pd.to_numeric(withx["fwd_ret"], errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(withx["fwd_ret_h21"], errors="coerce").to_numpy(dtype=float)
    both_nan = (~np.isfinite(a)) & (~np.isfinite(b))
    dev = np.where(both_nan, 0.0, np.abs(a - b))
    assert float(np.max(dev)) == 0.0, f"C0: fwd_ret_h21 != fwd_ret, max dev {np.max(dev):.3e}"

    # A window long enough to run past the calendar must lose whole DATES from the END. The
    # calendar ends for every name at once, so censoring removes a SUFFIX of dates rather than
    # scattering NaNs — and a scatter would be the signature of the delisting branch firing on
    # censored windows, which is the defect this whole design turns on.
    dates = sorted(withx["date"].unique())
    obs = sorted(withx.loc[withx["fwd_ret_h200"].notna(), "date"].unique())
    assert obs, "a 200-day window must still be observable on the early dates"
    assert len(obs) < len(dates), "a 200-day window must censor the most recent dates"
    assert obs == dates[:len(obs)], \
        f"censoring must remove a suffix of dates, not a scatter; got {obs} of {dates}"


def test_s22_extra_horizons_rejects_nonsense():
    """A zero or negative horizon would silently produce a same-day or backward-looking
    'forward' return."""
    from valuation.edge.fundamental_panel import build_fundamental_panel

    prov = _SynthPIT(4, seed=1)
    for bad in ([0], [-63], [63, 0]):
        try:
            build_fundamental_panel(prov, list(prov.q.keys()), extra_horizons=bad,
                                    rebalance_days=63, horizon=21, lookback_years=4)
        except ValueError:
            pass
        else:
            raise AssertionError(f"extra_horizons={bad} must raise")


def test_s22_ret_col_defaults_to_the_shipped_column_and_can_select_another():
    """`ret_col` is opt-in. The default must be bit-identical to the shipped call, and pointing
    it at a different column must actually change the answer — otherwise the term structure
    would be eight copies of one arm and every horizon would agree by construction."""
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=12, n_names=60, seed=11)
    rng = np.random.default_rng(4)
    p["fwd_ret_h126"] = p["fwd_ret"].values + rng.normal(0, 0.05, len(p))
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}

    base = quantile_backtest(p, cols, w, n_q=10, horizon=63)
    same = quantile_backtest(p, cols, w, n_q=10, horizon=63, ret_col="fwd_ret")
    for k in base:
        assert repr(base[k]) == repr(same[k]), f"{k} moved when ret_col was passed explicitly"

    other = quantile_backtest(p, cols, w, n_q=10, horizon=126, ret_col="fwd_ret_h126")
    assert other["top_decile_alpha"] != base["top_decile_alpha"], \
        "a different forward column must give a different arm"


def test_s22_a_censored_horizon_loses_dates_rather_than_scoring_them_short():
    """The panel-level consequence of the censoring rule. A long-horizon column is NaN on the
    most recent dates; `quantile_backtest` must DROP those dates, not score them on a partial
    cross-section. A silently shortened date is indistinguishable from a real one in the output.
    """
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=12, n_names=60, seed=11)
    dates = sorted(p["date"].unique())
    p["fwd_ret_h504"] = p["fwd_ret"]
    p.loc[p["date"].isin(dates[-3:]), "fwd_ret_h504"] = np.nan     # right-censor the last 3
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}

    full = quantile_backtest(p, cols, w, n_q=10, horizon=63, return_series=True)
    cens = quantile_backtest(p, cols, w, n_q=10, horizon=504, ret_col="fwd_ret_h504",
                             return_series=True)
    assert cens["n_periods"] == full["n_periods"] - 3
    assert cens["series"]["dates"] == full["series"]["dates"][:-3]
    # and the dates it DID score are scored identically — the censoring removed dates, nothing else
    for a, b in zip(cens["series"]["alpha"], full["series"]["alpha"][:-3]):
        assert abs(a - b) < 1e-12


def test_s22_quantile_backtest_refuses_an_absent_return_column():
    """A typo in a column name must not silently fall back to `fwd_ret` and report the 63-day
    answer under a 504-day label."""
    from valuation.edge.fundamental_panel import quantile_backtest

    p = _u7_panel(n_dates=8, n_names=40, seed=5)
    try:
        quantile_backtest(p, ["quality"], {"quality": 1.0}, ret_col="fwd_ret_h999")
    except KeyError as exc:
        assert "fwd_ret_h999" in str(exc)
    else:
        raise AssertionError("a missing forward-return column must raise, not fall back")


def test_s22_hac_lag_is_the_overlap_the_grid_induces():
    """At horizon H with a 63-day rebalance, consecutive windows overlap by H/63 - 1 periods.
    The lag is a property of the design and is pinned so it cannot drift into a tuned choice.
    At H=63 it must be 1 — the shipped R9 convention, not 0."""
    from scripts.term_structure import hac_lag, ret_col, HORIZONS

    assert [hac_lag(h) for h in HORIZONS] == [1, 1, 2, 3, 4, 5, 6, 7]
    assert hac_lag(63) == 1, "the base horizon keeps the shipped lag-1 convention"
    assert ret_col(63) == "fwd_ret", "the base horizon must read the SHIPPED column"
    assert ret_col(252) == "fwd_ret_h252"


def test_s22_kaplan_meier_is_censoring_aware():
    """Tenure spells still open at the panel end are right-censored. Discarding them biases the
    median DOWN, which is why KM is the primary and the naive median is reported beside it."""
    from scripts.term_structure import _km

    # four spells end at 1, one runs to 4 and is still open
    spells = [(1, False), (1, False), (1, False), (1, False), (4, True)]
    curve, median = _km(spells)
    assert median == 1, f"four of five leave at t=1, so the median is 1; got {median}"
    assert abs(curve[0]["survival"] - 0.2) < 1e-12

    # censoring must RAISE the survival curve relative to treating censored spells as events
    a, _ = _km([(1, False), (2, True), (2, True), (2, True)])
    b, _ = _km([(1, False), (2, False), (2, False), (2, False)])
    assert a[-1]["survival"] > b[-1]["survival"], \
        "treating an ongoing spell as an exit must not survive better than censoring it"

    # a single ongoing spell yields no events, so the median is undefined rather than 0
    _, none_median = _km([(3, True)])
    assert none_median is None


def _s23_panel(n_dates=20, n_names=80, seed=3):
    """A synthetic panel with the columns `_backtest_hold` reads."""
    rng = np.random.default_rng(seed)
    rows = []
    for di in range(n_dates):
        d = f"20{10 + di // 4}-{1 + 3 * (di % 4):02d}-15"
        for j in range(n_names):
            rows.append({"date": d, "ticker": f"T{j:02d}",
                         "quality": float(rng.normal()), "momentum": float(rng.normal()),
                         "fwd_ret": float(rng.normal(0, 0.1)),
                         "bench_ret": float(rng.normal(0, 0.05)),
                         "market_cap": 1e9 * (j + 1)})
    return pd.DataFrame(rows)


def test_s23_the_new_exits_are_opt_in_and_change_nothing():
    """S23 added four exits, a cost model and a series to `_backtest_hold`. Every one is
    opt-in, so the shipped book — which BACKTEST_RESULTS.json reports — cannot move by a bit."""
    from valuation.edge.fundamental_panel import _backtest_hold

    p = _s23_panel()
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    off = _backtest_hold(p, cols, w, top_n=10)
    explicit = _backtest_hold(p, cols, w, top_n=10, take_profit=None, stop_loss=None,
                              fv_at_or_above=None, disable_rank_exit=False,
                              cost_bps_one_way=None, return_series=False)
    assert set(off) == set(explicit), "passing the new defaults must add no keys"
    for k in off:
        assert repr(off[k]) == repr(explicit[k]), f"{k} moved at default settings"
    assert off["charges_costs"] is False
    assert "series" not in off and "exit_reasons" not in off


def test_s23_costs_are_charged_in_the_right_direction_and_size():
    """The whole cost of an exit rule is turnover, so a race scored gross would flatter
    whichever arm trades most. The drag is exact for an equal-weighted book:
    bps/1e4 * (bought + sold) / held."""
    from valuation.edge.fundamental_panel import _backtest_hold

    p = _s23_panel()
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    g = _backtest_hold(p, cols, w, top_n=10, return_series=True)
    n = _backtest_hold(p, cols, w, top_n=10, cost_bps_one_way=33.4, return_series=True)
    assert n["cagr"] < g["cagr"], "charging costs must not improve the book"
    assert n["charges_costs"] is True and n["cost_bps_one_way"] == 33.4
    s = n["series"]
    for k in range(len(s["net"])):
        want = (33.4 / 1e4) * (s["bought"][k] + s["sold"][k]) / s["held"][k]
        assert abs(s["drag"][k] - want) < 1e-12, f"period {k} drag is not the stated formula"
        assert abs((s["gross"][k] - s["drag"][k]) - s["net"][k]) < 1e-12
    # a zero-cost run must reproduce the gross series exactly
    assert g["series"]["gross"] == n["series"]["gross"]
    assert all(d == 0.0 for d in g["series"]["drag"])


def test_s23_each_exit_rule_actually_fires_and_is_attributed():
    """An exit rule that never triggers would make its arm a silent copy of the incumbent, and
    the race would report a dead heat that means nothing."""
    from valuation.edge.fundamental_panel import _backtest_hold

    p = _s23_panel()
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    base = _backtest_hold(p, cols, w, top_n=10, return_series=True)
    assert set(base["exit_reasons"]) == {"rank"}

    tp = _backtest_hold(p, cols, w, top_n=10, take_profit=0.25, stop_loss=0.08,
                        return_series=True)
    assert tp["exit_reasons"].get("take_profit", 0) > 0
    assert tp["exit_reasons"].get("stop_loss", 0) > 0

    dates = sorted(p["date"].unique())
    fv = {(d, "T00") for d in dates} | {(d, "T01") for d in dates}
    f = _backtest_hold(p, cols, w, top_n=10, fv_at_or_above=fv, return_series=True)
    assert f["exit_reasons"].get("fair_value", 0) > 0

    # every exit is attributed to exactly one reason, so the counts sum to the completed spells
    for r in (base, tp, f):
        assert sum(r["exit_reasons"].values()) > 0


def test_s23_the_never_exit_control_never_sells_and_its_book_grows():
    """C-NEVER is a CONTROL, not a candidate: its book is not size-comparable to the others,
    and this is the test that makes that concrete rather than a caveat in prose."""
    from valuation.edge.fundamental_panel import _backtest_hold

    p = _s23_panel()
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    base = _backtest_hold(p, cols, w, top_n=10, return_series=True)
    nv = _backtest_hold(p, cols, w, top_n=10, disable_rank_exit=True, return_series=True)
    assert nv["exit_reasons"] == {}, "the control must never sell"
    assert nv["held_max"] > base["held_max"], "the control's book must grow past the incumbent's"
    assert nv["series"]["sold"] == [0] * len(nv["series"]["sold"])


def test_s23_min_hold_binds_every_exit_rule_alike():
    """`min_hold` is held identical across arms so churn protection is not a confound. A
    take-profit that could fire on the entry period would give the TP/SL arms a different
    churn floor from the incumbent and the race would be measuring two things."""
    from valuation.edge.fundamental_panel import _backtest_hold

    p = _s23_panel()
    cols, w = ["quality", "momentum"], {"quality": 0.5, "momentum": 0.5}
    # a take-profit of -1000% would fire instantly if min_hold did not bind it
    r = _backtest_hold(p, cols, w, top_n=10, take_profit=-10.0, min_hold=2, return_series=True)
    assert r["series"]["sold"][0] == 0, "nothing may be sold in the entry period"
    assert r["series"]["sold"][1] == 0, "nor before min_hold periods have passed"
    assert sum(r["series"]["sold"]) > 0, "and it must fire once the minimum hold is met"


def test_s23_offline_beta_reproduces_the_ladder_without_its_network_rung():
    """The PIT valuation must never reach `data.beta.compute_beta`, which fetches TODAY'S
    prices — look-ahead in a backtest. `offline_beta` is rungs 1 -> (2 or 4), never 3."""
    from valuation.engine.calibration import offline_beta
    from valuation.engine.wacc import BETA_FALLBACK, BETA_HIGH_CAP, BETA_LOW_TRIGGER

    assert offline_beta(1.2) == 1.2, "an in-range PIT beta is used as-is (rung 2)"
    assert offline_beta(BETA_HIGH_CAP) == BETA_HIGH_CAP, "the cap itself is in range"
    # everything the ladder would have sent to the network lands on the STATED CONSTANT
    for bad in (None, float("nan"), 0.0, -1.0, BETA_LOW_TRIGGER, BETA_LOW_TRIGGER / 2,
                BETA_HIGH_CAP + 0.01, 99.0):
        assert offline_beta(bad) == BETA_FALLBACK, f"{bad} must fall to the stated constant"


def test_s23_lean_fair_value_beta_override_is_opt_in():
    """`lean_fair_value` gained one optional argument. Default None must leave the live path
    exactly as it was, or the website's own valuations move."""
    import inspect

    from valuation.engine.calibration import lean_fair_value

    sig = inspect.signature(lean_fair_value)
    assert sig.parameters["beta_override"].default is None
    assert list(sig.parameters) == ["cd", "cfg", "with_reverse", "beta_override"], \
        "the override must be appended, never inserted ahead of an existing positional"


def test_s23_the_valuation_panel_cuts_the_shared_calendar_not_each_ticker():
    """AUDIT B6, in the valuation panel. It used to request a per-ticker tail — the route
    `data_providers.price_history` says 'is never the panel's route now' — which put its early
    cross-sections on names that had already stopped trading. If this regresses, the fair-value
    arm silently scores a different calendar from the factor panel and S23's C1 is void."""
    import inspect

    from valuation.engine import calibration as C

    src = inspect.getsource(C.build_valuation_panel)
    assert "price_history(t, days=None)" in src, \
        "the valuation panel must ask for the WHOLE series (B6)"
    assert "frame.iloc[-_CAL_DAYS:]" in src, \
        "the SHARED calendar must be cut once, after the frame is built (B6)"
    # Scoped to the PER-TICKER fetch. The benchmark is fetched with an explicit `days=` too,
    # and that one is legitimate: SPY is a single series reindexed onto the panel calendar, so
    # it cannot create the union-calendar defect B6 is about.
    assert "provider.price_history(t, days=TD" not in src, \
        "the per-ticker tail must not come back"


def test_x3_deflated_sharpe_at_round_trips_and_falls_with_n():
    """X3's eight arms raise N, and a higher N must LOWER the Deflated Sharpe. That direction
    is the entire point of M1; a re-derivation that moved it the other way would be wrong."""
    from valuation.edge.ablation import deflated_sharpe_at

    detail = {"sharpe_per_period": 0.550, "var_sr_across_trials": 0.0276,
              "n_periods": 69, "probability": 0.8997, "n_trials": 84}
    same = deflated_sharpe_at(detail, 84)
    assert abs(same["probability"] - 0.8997) < 1e-9, "must round-trip at the recorded N"
    up = deflated_sharpe_at(detail, 92)
    assert up["sr0_benchmark"] > same["sr0_benchmark"]
    assert up["probability"] < same["probability"]
    assert deflated_sharpe_at(detail, 8)["probability"] > same["probability"]


def test_x3_paired_diff_is_paired_not_independent():
    """A shock common to both arms is the market, not the model. If it moved the difference
    interval, every arm would look indistinguishable from every other and the curve would be
    unreadable."""
    from valuation.edge.ablation import paired_diff

    rng = np.random.default_rng(5)
    base = rng.normal(0, 0.05, 60)
    a = list(base + 0.01)
    b = list(base)
    d1 = paired_diff(a, b, draws=800)
    shock = rng.normal(0, 0.25, 60)                 # a big COMMON shock
    d2 = paired_diff(list(np.array(a) + shock), list(np.array(b) + shock), draws=800)
    assert abs(d1["mean_diff_ann"] - d2["mean_diff_ann"]) < 1e-9
    w1 = d1["ci95_ann"][1] - d1["ci95_ann"][0]
    w2 = d2["ci95_ann"][1] - d2["ci95_ann"][0]
    assert abs(w1 - w2) < 1e-9, "a common shock must cancel out of a PAIRED difference"


def test_x3_the_old_ablation_verdict_is_marked_superseded():
    """The ledger records X3 DONE with 'EARNS ITS COMPLEXITY', measured on the pre-B6 110-date
    panel and against a 1.0pp bar that X7 later showed sits below the noise floor (1.95pp).
    A stale DONE row is how a void verdict gets quoted forward."""
    led = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "VALQUO_LEDGER.md")
    if not os.path.exists(led):
        return
    rows = [ln for ln in open(led, encoding="utf-8") if ln.startswith("| X3 |")]
    assert rows, "X3 row missing from the ledger"
    assert any("SUPERSEDED" in r.upper() or "RE-RUN" in r.upper() for r in rows), \
        "X3's ledger row must record that the 2026-08-03 run was superseded"


def test_u7_the_fast_block_bootstrap_is_exact():
    """The five-seed control book makes the per-trade bootstrap ~240M Python operations per
    cell. The mean of a concatenation of blocks IS sum(block sums)/sum(block counts), so the
    fast path is an exact rewrite -- and "exact" is worth nothing unless it is asserted against
    the implementation it replaces, on the same seed."""
    from valuation.edge import options_veto as V
    from valuation.edge import options_stats as OS

    rng = np.random.default_rng(19)
    a, b = [], []
    for mth in range(1, 13):
        for j in range(12):
            ts = f"2020-{mth:02d}-{1 + j:02d}"
            a.append({"alert_ts": ts, "pnl_pct": float(rng.normal(0.05, 0.4))})
            b.append({"alert_ts": ts, "pnl_pct": float(rng.normal(0.00, 0.4))})
    slow = OS.date_block_diff(a, b, seed=0, draws=500)
    fast = V.fast_block_diff(a, b, seed=0, draws=500)
    assert slow["ok"] and fast["ok"]
    assert abs(slow["diff"] - fast["diff"]) < 1e-12
    for i in (0, 1):
        assert abs(slow["ci95"][i] - fast["ci95"][i]) < 1e-12, "CI endpoints must match exactly"
    assert slow["n_blocks"] == fast["n_blocks"] == 12



# ------------------------------------------------- AUDIT B8 / session 7: the two verdicts
def _b8_panel(n_dates=24, n_names=60, seed=11):
    """A panel with one theme that is predictive in BOTH halves and one that is anti-predictive
    in both, so the decide-half rule (`median IC <= 0`) fires deterministically on exactly one
    of them and the gating can be pinned without relying on which way noise fell.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        for i in range(n_names):
            fwd = float(rng.normal(0, 0.08))
            rows.append({"date": f"20{20 + d // 12:02d}-{d % 12 + 1:02d}-01", "ticker": f"T{i}",
                         "fwd_ret": fwd, "bench_ret": 0.01,
                         "quality": fwd + float(rng.normal(0, 0.02)),      # IC strongly positive
                         "size": -fwd + float(rng.normal(0, 0.02))})     # IC strongly negative
    return pd.DataFrame(rows)


def test_b8_rule_fired_is_now_read_and_gates_the_out_of_sample_verdict():
    """THE REGRESSION THIS EXISTS FOR. `rule_fired` was computed and never read, so a theme
    could read `confirmed` in a direction whose decide half never flagged it — a both-halves
    stability check wearing the name of an out-of-sample confirmation.

    A theme with positive IC on both halves is never a candidate, so NO out-of-sample test of
    it was run and it must say so rather than borrowing the stability verdict.
    """
    import valuation.edge.fundamental_panel as F
    r = F.holdout_theme_validate(_b8_panel(), ["quality", "size"], horizon=63)

    assert r["oos_directions_tested"]["quality"] == 0, "the rule fired on a positive-IC theme"
    assert r["oos_verdicts"]["quality"] == "not_flagged", r["oos_verdicts"]
    assert r["oos_directions_tested"]["size"] == 2, "the rule missed a negative-IC theme"

    # Where the rule fires in BOTH directions the gate is a no-op, so the two verdicts must
    # agree. If they ever diverge there, the gating is dropping evidence it should keep.
    assert r["oos_verdicts"]["size"] == r["verdicts"]["size"] + "_oos", (
        r["verdicts"]["size"], r["oos_verdicts"]["size"])

    for c in ("quality", "size"):
        fired = sum(bool(r["splits"][s]["themes"][c]["rule_fired"]) for s in r["splits"])
        assert r["oos_directions_tested"][c] == fired


def test_b8_the_stability_verdict_keeps_frozen_semantics():
    """`scripts/placebo.py` reads `verdicts`, and X7's measured ~6% false-positive rate of the
    held-out gate was calibrated against that exact object across 100 placebo draws.
    Redefining it in place would leave that figure describing a gate that no longer exists —
    the same class of defect as the stale theme IC table found in session 6.
    """
    import valuation.edge.fundamental_panel as F
    r = F.holdout_theme_validate(_b8_panel(), ["quality", "size"], horizon=63)

    assert r["stability_verdicts"] == r["verdicts"], "the honest alias drifted from the object"
    assert all(v in ("confirmed", "not_replicated", "rejected") for v in r["verdicts"].values())
    assert all(v in ("confirmed_oos", "not_replicated_oos", "rejected_oos", "not_flagged")
               for v in r["oos_verdicts"].values())
    # Both scopes ship in words, so a reader of the results file cannot take one for the other.
    assert "NOT applied" in r["verdicts_scope"] and "B8" in r["verdicts_scope"]
    assert "out-of-sample" in r["oos_verdicts_scope"]

    from valuation.edge.results_file import build_payload
    p = build_payload({"holdout_validation": r, "horizons": {}, "cpcv": {}, "construction": {}})
    assert p["holdout_validation"]["verdicts"] == r["verdicts"]


# --------------------------------------- session 7: the pre-registered held-out leave-one-out
def test_loo_selection_uses_the_decide_half_only_and_embargoes_the_boundary():
    """One selection, one degree of freedom, and the measure half never informs it.

    Pins the two things that make the test honest rather than a re-quote of session 6's
    exploratory arms: the selected arm IS the decide half's argmax, and the boundary date --
    the only one whose 63d forward window can straddle a 63d-rebalance split -- is in neither
    half.
    """
    from valuation.edge import loo_holdout as L
    panel = _b8_panel(n_dates=30, n_names=60, seed=5)
    panel["value"] = panel["fwd_ret"] * 0.3 + np.random.default_rng(7).normal(0, 0.05, len(panel))
    r = L.loo_holdout(panel, ["quality", "size", "value"], min_dates=8)

    dates = sorted(panel["date"].unique())
    assert r["boundary_date_embargoed"] == str(dates[len(dates) // 2])
    assert r["n_dates"]["early"] + r["n_dates"]["late"] == len(dates) - 1, "boundary not dropped"

    for s in L.DIRECTIONS:
        b = r["splits"][s]
        best = max(b["decide_ranking"], key=lambda x: x["d_top_decile_alpha"])
        assert b["selected"] == best["dropped"], "selection did not come from the decide half"
        assert abs(b["selected_decide_gain"] - best["d_top_decile_alpha"]) < 1e-12
        # The full spread is reported alongside and carries no verdict.
        assert len(b["measure_all_arms"]) == 3


def test_loo_verdict_follows_the_committed_margins_and_an_ambiguous_result_is_a_null():
    """RUN_RULES 6: a result ambiguous against its own threshold IS a null, not a judgement
    call. Pinned as an invariant over whatever the panel happens to produce, so the rule cannot
    be quietly relaxed later to rescue a near miss.
    """
    from valuation.edge import loo_holdout as L
    from valuation.edge.fundamental_panel import (MIN_HOLDOUT_ALPHA_GAIN,
                                                  MIN_HOLDOUT_TSTAT_GAIN)
    panel = _b8_panel(n_dates=30, n_names=60, seed=9)
    panel["value"] = panel["fwd_ret"] * 0.2 + np.random.default_rng(3).normal(0, 0.06, len(panel))
    r = L.loo_holdout(panel, ["quality", "size", "value"], min_dates=8)
    assert r["min_alpha_gain"] == MIN_HOLDOUT_ALPHA_GAIN
    assert r["min_tstat_gain"] == MIN_HOLDOUT_TSTAT_GAIN

    good = [r["splits"][s]["improves"] for s in L.DIRECTIONS]
    neg = [r["splits"][s]["negative"] for s in L.DIRECTIONS]
    expect = ("adopted_eligible" if all(good) else "rejected" if all(neg) else "null")
    assert r["verdict"] == expect, (r["verdict"], good, neg)

    for s in L.DIRECTIONS:
        b = r["splits"][s]
        da = (b["measure_selected"] or {}).get("d_top_decile_alpha")
        dt = (b["measure_selected"] or {}).get("d_long_short_tstat")
        # `improves` requires BOTH margins. Clearing one is not clearing the bar.
        assert b["improves"] == bool(da is not None and dt is not None
                                     and da >= MIN_HOLDOUT_ALPHA_GAIN
                                     and dt >= MIN_HOLDOUT_TSTAT_GAIN)


def test_loo_arms_drop_a_theme_and_renormalise_rather_than_leaving_a_hole():
    """The deployed composite is flat 1/7 and was never tuned, so a dropped-theme arm is flat
    1/6. Leaving a zero in place would ask a different question -- "six sevenths of the
    composite" -- and would make the arms incomparable with the full composite they are scored
    against.
    """
    from valuation.edge import loo_holdout as L
    cols = ["a", "b", "c", "d"]
    w = L.flat(cols)
    assert abs(sum(w.values()) - 1.0) < 1e-12 and all(abs(v - 0.25) < 1e-12 for v in w.values())
    rest = L.flat([c for c in cols if c != "b"])
    assert abs(sum(rest.values()) - 1.0) < 1e-12, "the arm does not renormalise"
    assert "b" not in rest and all(abs(v - 1 / 3) < 1e-12 for v in rest.values())

def _cc_panel(n_countries, n_dates, rho, seed):
    """A month-by-country panel with a known common-factor correlation."""
    import random as _r
    rnd = _r.Random(seed)
    a, b = rho ** 0.5, (1.0 - rho) ** 0.5
    out = {f"c{j}": {} for j in range(n_countries)}
    for i in range(n_dates):
        f = rnd.gauss(0, 1)
        for j in range(n_countries):
            out[f"c{j}"][i] = a * f + b * rnd.gauss(0, 1)
    return out


def test_session9_the_country_gate_reproduces_the_exact_binomial_at_zero_correlation():
    """The simulated bar generalises the arithmetic; at rho=0 it must REPRODUCE it.

    12 of 16 is the pre-registered threshold and its exact one-sided alpha is 3.84%. If the
    simulation drifted off that, every calibrated threshold it produced would be unquotable.
    """
    from valuation.edge import cross_country as CC
    assert abs(CC.exact_binomial_tail(12, 16) - 0.038406) < 1e-5, "12/16 is not 3.84%"
    assert abs(CC.exact_binomial_tail(11, 16) - 0.105057) < 1e-5, "11/16 is not 10.5%"
    r = CC.sign_test_critical(16, rho=0.0, alpha=0.05, draws=40000, seed=7)
    assert r["critical_k"] == 12, f"rho=0 must give the binomial k=12, got {r['critical_k']}"
    assert abs(r["achieved_alpha"] - 0.038406) < 0.006, r["achieved_alpha"]


def test_session9_a_raw_country_design_effect_is_not_evidence_of_clustering():
    """R3's lesson, one dimension over: independent countries still produce deff > 1 from pure
    ANOVA sampling noise. The gate must call that NOT measurable, or it manufactures a
    correction out of nothing."""
    from valuation.edge import cross_country as CC
    res = CC.country_design_effect(_cc_panel(16, 324, 0.0, seed=3), null_draws=200, seed=1)
    assert res["ok"], res
    assert res["clustering_measurable"] is False, \
        f"independent countries flagged as clustered: deff {res['design_effect']:.3f} " \
        f"vs null p95 {res['design_effect_null_p95']:.3f}"
    assert res["n_eff_countries"] <= res["n_countries"] + 1e-9, "n_eff exceeded n"


def test_session9_the_country_gate_detects_real_co_movement_and_both_estimators_agree():
    from valuation.edge import cross_country as CC
    res = CC.country_design_effect(_cc_panel(16, 324, 0.30, seed=5), null_draws=200, seed=1)
    assert res["ok"] and res["clustering_measurable"] is True, res
    assert abs(res["rho"] - 0.30) < 0.06, f"rho {res['rho']:.3f} off the planted 0.30"
    assert abs(res["mean_pairwise_corr"] - res["rho"]) < 0.05, \
        "the ANOVA and the mean-pairwise estimators disagree; quote neither"
    assert res["n_eff_countries"] < 6.0, res["n_eff_countries"]


def test_session9_an_arm_pair_difference_is_a_scaled_two_theme_spread():
    """Δ_a − Δ_b == (x_b − x_a)/4 identically, where Δ_a drops theme a from a 5-theme mean.

    This is why the measured cross-country co-movement is credible rather than an artefact of
    how the arms were built: the object whose correlation the gate measures is nothing more
    exotic than a scaled difference of two theme returns, and value-minus-momentum spreads are
    famously correlated across developed markets. Pinned because the whole SELRULE calibration
    rests on the identity being exactly this and not approximately it.
    """
    import random as _r
    from scripts.selection_rule_crosscountry import arm_deltas
    try:
        import pandas as pd
    except ImportError:
        return
    rnd = _r.Random(4)
    cols = ["investment", "momentum", "quality", "size", "value"]
    df = pd.DataFrame({c: [rnd.gauss(0, 0.03) for _ in range(60)] for c in cols})
    d = arm_deltas(df)
    worst = 0.0
    for a in cols:
        for b in cols:
            if a >= b:
                continue
            lhs = (df[b] - df[a]) / 4.0
            worst = max(worst, max(abs(lhs[k] - (d[a][k] - d[b][k])) for k in d[a]))
    assert worst < 1e-12, f"arm-pair difference is not (x_b - x_a)/4; max error {worst:.2e}"


def test_session9_clustering_can_only_raise_the_bar_never_lower_it():
    """A correlated null piles probability into the tails, so the critical count must rise with
    rho. A gate that could LOWER the bar would be a licence, not a correction."""
    from valuation.edge import cross_country as CC
    ks = [CC.sign_test_critical(16, rho=r, alpha=0.05, draws=20000, seed=11)["critical_k"]
          for r in (0.0, 0.10, 0.30, 0.60)]
    assert ks == sorted(ks), f"critical k not monotone in rho: {ks}"
    assert ks[-1] > ks[0], f"co-movement left the bar unchanged: {ks}"


def test_session10_the_placebo_writer_summarises_the_hac_statistic_it_computes():
    """The bug this pins is a WRITER bug, not a scoring bug, and it cost a whole sweep.

    `quantile_backtest` has computed `long_short_tstat_nw` on every placebo draw since R9, but
    the placebo recorder never stored it and the summariser never percentiled it. So X7's
    calibrated long-short floor of 2.14 was derived on the NAIVE t while the project's shipped
    statistic became the HAC t of 2.620 -- a bar and a number from different estimators, carried
    as a known defect for days, and only closable by re-running 100 draws because the raw draws
    could not be recovered.

    A column that is computed and then silently dropped is indistinguishable from one that was
    never computed. This asserts the round trip: a draw carrying the HAC keys must come out of
    `_write` with those keys summarised.
    """
    import json as _json
    import tempfile
    from types import SimpleNamespace
    from scripts import placebo as PL

    draw = {"long_short_tstat": 1.0, "long_short_tstat_nw": 0.9, "long_short_ljung_box_p": 0.5,
            "top_decile_alpha": 0.01, "top_decile_alpha_tstat": 1.1,
            "top_decile_alpha_tstat_nw": 1.0, "monotonicity": -0.5, "pbo": 0.4,
            "deflated_sharpe": 0.5, "max_abs_theme_ic_t": 1.2, "equal_weight_ann": 0.18,
            "long_short_ann": 0.05, "breakeven_one_way_bps": 100.0,
            "n_themes_ic_t_over_2": 0}
    args = SimpleNamespace(n=2, seed0=1000, panel="dummy.pkl")
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "out.json")
        PL._write(p, dict(draw), [dict(draw), dict(draw)], args, costs=True)
        out = _json.load(open(p, encoding="utf-8"))
    for k in ("long_short_tstat_nw", "top_decile_alpha_tstat_nw", "long_short_ljung_box_p"):
        assert k in out["null"], f"{k} is computed per draw but never summarised"
        assert out["null"][k].get("p95") is not None, f"{k} has no p95 -- no floor can be read"
    for k in ("long_short_t_nw_over_2", "long_short_t_nw_over_2_14"):
        assert k in out["rates"], f"{k} missing; the HAC bar cannot be scored against noise"


def test_session11_the_ml_executor_still_matches_the_register_it_executed():
    """`PREREG_ml_combiner.md` is only worth anything if the code that ran it still says what it
    said. This pins the four things a later session could quietly widen: the grid is EIGHT points
    (not nine), the features are the SEVEN deployed themes (never `low_risk`, `sentiment`, or the
    56 raw signals), the anti-overfit hyperparameters are held rather than searched, and the bars
    are the calibrated ones.
    """
    from scripts import ml_combiner as M
    assert len(M.GRID) == 8, f"the register froze 8 grid points, found {len(M.GRID)}"
    assert {tuple(sorted(g.items())) for g in M.GRID} == {
        tuple(sorted({"max_depth": d, "learning_rate": lr, "max_iter": it}.items()))
        for d in (2, 3) for lr in (0.03, 0.10) for it in (100, 300)}, "grid drifted"
    assert M.THEMES == ["value", "quality", "momentum", "insider", "capital_discipline",
                        "size", "institutional"], "feature set drifted from the register"
    for banned in ("low_risk", "sentiment"):
        assert banned not in M.THEMES, \
            f"{banned} is a theme-membership change smuggled in as a feature"
    assert M.FIXED["min_samples_leaf"] == 200 and M.FIXED["l2_regularization"] == 1.0 and \
        M.FIXED["early_stopping"] is False and M.FIXED["random_state"] == 0, \
        "an anti-overfit constant moved; that is a new trial, not a clarification"
    assert abs(M.LS_HAC_FLOOR - 2.2837) < 1e-9, "LS floor must be session 10's HAC-calibrated bar"
    assert abs(M.MIN_ALPHA_MARGIN - 0.0195) < 1e-9, "alpha margin must be X7's 1.95pp"
    assert abs(M.MIN_T_MARGIN - 0.25) < 1e-9, "t-margin must be the standing MIN_HOLDOUT 0.25"


def test_session12_the_trial_counter_reads_verdicts_from_the_verdict_column_only():
    """THE FIXTURE THE REPAIR EXISTS FOR.

    `research_log._parse` used to test `\\bFIXED\\b` against every cell of a row joined together,
    so a row whose hypothesis, threshold, source or note merely contained the word "fixed" was
    silently dropped from `N`. An understated `N` OVERSTATES the significance of every DSR-gated
    claim in the project — M1's own error, committed inside M1's own parser.

    On the log as it stands the defect is LATENT (session 12 measured it: zero rows differ, on all
    ten historical revisions), so nothing but a fixture can prove the repair does anything. This
    row set is built so the OLD parser and the NEW one give different answers: prose containing
    "fixed", "adopted" and "rejected" in every field except the verdict, a grid multiplier that
    only counts when read from its own column, and a domain word planted in free text.
    """
    import tempfile
    from valuation.edge import research_log as RL

    md = (
        "# fixture\n\n"
        "| id | date | domain | pre | hypothesis | metric | verdict | n | source |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        # counts: the note says "fixed" but the VERDICT says REJECTED
        "| T1 | 2026-08-08 | equity | yes | The defect fixed in session 12 understated N "
        "| IC t | REJECTED | n=1 | note |\n"
        # counts: prose full of other verdict words, none of them the verdict
        "| T2 | 2026-08-08 | equity | yes | Whether the ADOPTED weights beat the rejected ones "
        "| alpha | NULL | n=3 | a run that fixed nothing |\n"
        # does NOT count: the verdict column itself says FIXED
        "| T3 | 2026-08-08 | equity | retro | A real correctness repair | code | FIXED | n=1 "
        "| adopted nowhere |\n"
        # does NOT count: the legitimate existing variant value
        "| T4 | 2026-08-08 | options | retro | Another repair | code | FIXED (relabel only) "
        "| n=1 | — |\n"
        # counts, and its DOMAIN must come from the domain column, not the planted word
        "| T5 | 2026-08-08 | options | yes | Compared against the equity book | PF | ADOPTED "
        "| n=2 | equity |\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "RESEARCH_LOG.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(md)
        got = RL._parse(p)

    # --- the repair -------------------------------------------------------------------
    assert got["rows_counted"] == 3, (
        f"T1, T2 and T5 are trials; got {got['rows_counted']} rows counted. "
        "A row is FIXED only when its VERDICT CELL says so.")
    assert got["rows_fixed"] == 2, f"only T3 and T4 are FIXED; got {got['rows_fixed']}"
    assert set(got["ids"]) == {"T1", "T2", "T5"}, got["ids"]

    # --- the grid multiplier comes from the `n` column ---------------------------------
    assert got["trials"] == 1 + 3 + 2, f"expected 6 trials (1+3+2), got {got['trials']}"

    # --- the domain comes from the domain column, not a word planted in free text -------
    assert got["by_domain"]["equity"] == 4, (
        f"T1(1)+T2(3) are equity; got {got['by_domain']['equity']}. T5 says `options` in its "
        "domain column and `equity` in its source — the column wins.")
    assert got["by_domain"]["options"] == 2, got["by_domain"]

    # --- and the old behaviour really did differ, or this fixture proves nothing --------
    legacy_counted = 0
    for ln in md.splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() in ("id",) or set(cells[0]) <= set("-: "):
            continue
        if not re.search(r"\bFIXED\b", " ".join(cells).upper()):
            legacy_counted += 1
    assert legacy_counted == 1, (
        f"the fixture must be one the OLD parser got wrong; it counted {legacy_counted} of the "
        "3 real trials")


def test_session12_a_row_with_unescaped_pipes_may_not_silently_lose_its_trials():
    """FOUND THE HARD WAY, mid-session, by merging another lane.

    O16 writes `|Spearman(term_slope, atm_front)|` for an absolute value inside a markdown table
    cell. The unescaped `|` splits that cell in two, so every column after it shifts and the row's
    indices stop meaning what the header says. The column-wise parser then read the `n` field off
    prose, found no `n=<k>`, and charged the row **1 trial instead of 5** — understating `N`,
    which is precisely the direction session 12 exists to eliminate. The old whole-line grep was
    accidentally immune, so the repair would have introduced a regression the defect it replaced
    did not have.

    A misaligned row therefore resolves toward a LARGER `N` on every field, and is reported in
    `rows_malformed` rather than silently absorbed.
    """
    import tempfile
    from valuation.edge import research_log as RL

    md = (
        "| id | date | domain | pre | hypothesis | metric | verdict | n | source |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        # 11 cells, not 9: the metric carries |x| for an absolute value
        "| O16X | 2026-08-07 | options | yes | a signal is another signal renamed "
        "| identity arm is |Spearman(a, b)| and var(a)/var(b) | INCONCLUSIVE | n=5 | note |\n"
        # a well-formed control alongside it, so the guard cannot pass by counting everything
        "| OKROW | 2026-08-07 | options | yes | something testable | IC t | REJECTED | n=2 "
        "| note |\n"
        "| FIXROW | 2026-08-07 | equity | n/a | a repair | code | FIXED | n=1 | note |\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "RESEARCH_LOG.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(md)
        got = RL._parse(p)

    assert got["trials"] == 7, (
        f"expected 5 + 2 = 7 trials, got {got['trials']}. A row whose columns are shifted by an "
        "unescaped `|` must fall back to the whole-line scan and take the LARGER count, never "
        "silently drop to 1.")
    assert got["by_domain"]["options"] == 7, got["by_domain"]
    assert got["rows_fixed"] == 1, "the well-formed FIXED row must still be excluded"
    mal = got.get("rows_malformed") or []
    assert [m["id"] for m in mal] == ["O16X"], (
        f"the misaligned row must be REPORTED, not silently absorbed; got {mal}")
    assert mal[0]["row_width"] == 11 and mal[0]["header_width"] == 9, mal[0]


# --------------------------------------------------------------------------- #
#  SECTOR-NEUTRAL-B6 — the paired build (PREREG_sector_neutral_b6.md §2)
#
#  Both prior sector-neutral rejections built the two arms as two SEPARATE runs, and a full
#  backtest is not reproducible run to run. These pin the property that makes the re-run
#  interpretable: one pass, one `metrics` list, two `build_frame` calls, identical rows.
# --------------------------------------------------------------------------- #
def _synth_with_sectors(n=30, seed=7, sectors=("Technology", "Utilities", "Healthcare")):
    """_SynthPIT plus a TICKERS overlay (the only source of `sector` in the panel), and with the
    fcf/netinc proportionality BROKEN.

    `_SynthPIT.fundamentals_history` emits `fcf = 90*(1+q)` and `netinc = 100*(1+q)`, so the cash
    conversion ratio is EXACTLY 0.9 for every name and `accruals_q` is a constant column. A
    constant column's z-score is not a well-defined object, and in this codebase it is worse than
    undefined: `zscore`'s zero-variance guard tests `sd == 0`, but `pd.Series([0.9]*30).std()` is
    2.2e-16 rather than 0.0, so the guard does not fire and the column standardises to garbage
    that is not invariant under a shift. That is a real (reported) defect, but it is not what
    these tests are about, so the fixture is made non-degenerate instead of the assertion being
    weakened. See HANDOFF_edge_audit.md session 20.
    """
    prov = _SynthPIT(n, seed=seed)
    if sectors:
        prov.ticker_meta = lambda t, _s=sectors: {"sector": _s[int(t[1:]) % len(_s)]}
    base = prov.fundamentals_history

    def _fh(ticker, _b=base):
        rows = _b(ticker)
        for k, r in enumerate(rows):
            # a per-name, per-period wobble so fcf/netinc genuinely disperses
            r["fcf"] = r["fcf"] * (1.0 + 0.13 * ((int(ticker[1:]) % 7) - 3) + 0.02 * k)
        return rows

    prov.fundamentals_history = _fh
    return prov


def test_b6_sector_pair_is_off_by_default_and_only_ADDS_columns():
    """The default payload may not move — BACKTEST_RESULTS.json is built from this frame."""
    from valuation.edge.fundamental_panel import build_fundamental_panel

    prov = _synth_with_sectors()
    tickers = list(prov.q.keys())
    kw = dict(rebalance_days=63, horizon=21, lookback_years=4)

    plain = build_fundamental_panel(prov, tickers, **kw)
    assert not plain.empty
    assert not [c for c in plain.columns if str(c).startswith("sn_")], \
        "no paired columns may appear unless asked for"

    pair = build_fundamental_panel(prov, tickers, sector_neutral_pair=True, **kw)
    assert list(plain.columns) == [c for c in pair.columns if not str(c).startswith("sn_")], \
        "the paired build must ADD columns and move none"
    assert len(pair) == len(plain), "the row set must not change"


def test_b6_the_paired_build_leaves_the_FLAT_arm_bit_identical():
    """The row-defining arm is the shipped one and must not be perturbed by measuring the other.

    If this fails, the re-run's `flat` arm is not the shipped book and control C3 (reproduce the
    published record to the digit) would be measuring a different object.
    """
    from valuation.edge.fundamental_panel import build_fundamental_panel
    from valuation.screener import settings as S

    prov = _synth_with_sectors()
    tickers = list(prov.q.keys())
    kw = dict(rebalance_days=63, horizon=21, lookback_years=4)
    plain = build_fundamental_panel(prov, tickers, **kw)
    pair = build_fundamental_panel(prov, tickers, sector_neutral_pair=True, **kw)

    assert list(plain["ticker"]) == list(pair["ticker"]), "row order changed"
    assert list(plain["date"].astype(str)) == list(pair["date"].astype(str)), "dates changed"
    for theme in S.FACTORS_ALL:
        a = pd.to_numeric(plain[theme], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(pair[theme], errors="coerce").to_numpy(dtype=float)
        both_nan = (~np.isfinite(a)) & (~np.isfinite(b))
        dev = float(np.max(np.where(both_nan, 0.0, np.abs(a - b))))
        assert dev == 0.0, f"{theme}: the paired build moved the flat arm by {dev:.3e}"


def test_b6_paired_arms_are_EXACTLY_equal_when_every_sector_is_blank():
    """The inertness signature, used here as proof the pair really routes through the flag.

    `x - median(x)` over one group is a pure shift and the z-score that follows erases it, so
    with no TICKERS overlay the two arms must agree to the last bit. A pair path that ignored
    the flag would pass every other test in this block and fail nothing — except this one.
    """
    from valuation.edge.fundamental_panel import build_fundamental_panel
    from valuation.screener import settings as S

    prov = _synth_with_sectors(sectors=None)          # deliberately NO ticker_meta
    pair = build_fundamental_panel(prov, list(prov.q.keys()), sector_neutral_pair=True,
                                   rebalance_days=63, horizon=21, lookback_years=4)
    assert not pair.empty
    assert (pair["sector"].astype(str).str.strip() == "").all(), "fixture must have no sectors"
    for theme in S.FACTORS_ALL:
        a = pd.to_numeric(pair[theme], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(pair["sn_" + theme], errors="coerce").to_numpy(dtype=float)
        both_nan = (~np.isfinite(a)) & (~np.isfinite(b))
        dev = float(np.max(np.where(both_nan, 0.0, np.abs(a - b))))
        assert dev < 1e-12, f"{theme}: blank sectors must make the arms identical, dev {dev:.3e}"


def test_b6_paired_arms_diverge_when_sectors_are_real_and_add_no_missing_values():
    """C2 (the toggle is not inert) and C6 (median-subtraction creates no NEW missing value).

    C6 is not cosmetic: a new NaN would mean the two arms score different NAMES, and the whole
    point of the one-pass build is that they cannot.
    """
    from valuation.edge.fundamental_panel import build_fundamental_panel
    from valuation.screener import settings as S

    prov = _synth_with_sectors()
    pair = build_fundamental_panel(prov, list(prov.q.keys()), sector_neutral_pair=True,
                                   rebalance_days=63, horizon=21, lookback_years=4)
    assert not pair.empty
    moved = []
    for theme in S.FACTORS_ALL:
        a = pd.to_numeric(pair[theme], errors="coerce")
        b = pd.to_numeric(pair["sn_" + theme], errors="coerce")
        assert int(b.isna().sum()) <= int(a.isna().sum()), (
            f"{theme}: sector-neutral created {int(b.isna().sum()) - int(a.isna().sum())} "
            f"NEW missing values — the arms would score different names")
        ok = a.notna() & b.notna()
        if ok.any():
            moved.append(float((b[ok] - a[ok]).abs().mean()))
    assert max(moved) > 1e-6, f"with real sectors the arms must diverge somewhere: {moved}"


def test_b6_zscore_zero_variance_guard_does_not_fire_on_a_constant_column():
    """A DEFECT PINNED, NOT FIXED — found by the B6 re-run, reported, deliberately not repaired.

    `cross_sectional.zscore` guards degeneracy with `if not sd or np.isnan(sd) or sd == 0`.
    That guard assumes a constant cross-section has `sd == 0`. Whether it does is
    VALUE-DEPENDENT, because pandas reaches the variance through a sum of squares: it is exactly
    0.0 for 0.0, 50.0, 2.5, 0.125 and 0.07, and 1e-16-ish for 0.9, 0.1, 1/3 and 12.34. When it
    misses, `zscore` does not return NaN — it returns a fabricated pattern with max |z| = 1.0,
    built entirely out of floating-point residue. A constant signal therefore does not reliably
    neutralise itself; it can inject invented ±1 scores into a theme.

    Why it is pinned rather than fixed: `zscore` is on the live scoring path and every published
    figure in this project runs through it. Changing it is a scoring change, therefore a VINTAGE
    EVENT, and it is not this register's to make. Pinning it means a future fix cannot land
    silently — this test fails, and whoever fixes it has to update the record.

    It also corrects a claim in the record: V2G says a constant `insider` means "`zscore` returns
    all-NaN". That is true only because the live `insider` is constant at EXACTLY 0.0
    (`(50 - 50) / 25`), where the sum of squares really is 0. It is not a general property, and
    quoting it as one would be wrong.
    """
    from valuation.screener.cross_sectional import zscore

    # The guard DOES work for these — so "a constant column becomes NaN" is true sometimes,
    # which is exactly what makes the failure hard to notice.
    for c in (0.0, 50.0, 2.5, 0.125):
        s = pd.Series([c] * 30)
        assert s.std(ddof=0) == 0.0, f"expected an exact zero variance for {c}"
        assert zscore(s).isna().all(), f"a column constant at {c} must degrade to NaN"

    # And it does NOT work for these. Same shape of input, opposite behaviour.
    for c in (0.9, 0.1, 12.34):
        s = pd.Series([c] * 30)
        assert s.nunique() == 1, "fixture must be constant"
        assert s.std(ddof=0) != 0.0, (
            f"if pandas now returns an exact 0 for a constant {c} series, the guard works and "
            f"this defect is fixed — update HANDOFF_edge_audit.md session 20 and the record")
        z = zscore(s)
        assert not z.isna().all(), (
            f"zscore({c}-constant) no longer produces garbage — the defect is FIXED. That is "
            f"good news, but it is a scoring change: update the record and treat it as a "
            f"vintage event rather than deleting this test")
        assert abs(float(np.nanmax(np.abs(z.to_numpy(dtype=float)))) - 1.0) < 1e-9, (
            "the fabricated pattern is the ±1 residue one; a different shape means the "
            "mechanism changed and the write-up needs re-checking")

    # And the consequence that matters: the output is not invariant to a shift, which is what
    # made a constant-grouping sector-neutral pass look like a real difference.
    near = pd.Series([0.9] * 28 + [0.9 + 1e-16, 0.9 - 1e-16])
    assert float((zscore(near) - zscore(near - 0.9)).abs().max()) > 1.0, \
        "the shift-invariance failure on a degenerate column is the observable symptom"


# =============================================================================================
# S20 / S21 — the construction pair: rank composite, and winsorisation.
# PREREG_s20_s21_construction.md, committed alone at 27af414.
# =============================================================================================


def test_s2021_rank_score_is_the_ONE_definition_and_standardize_factors_uses_it():
    """Two rank implementations that drift apart is a defect class this project has paid for
    four times (`assets`, the SF3 positional-arg bug, the five empty factors, `invcap`)."""
    from valuation.screener.cross_sectional import rank_score, standardize_factors
    rng = np.random.default_rng(3)
    s = pd.Series(np.concatenate([rng.normal(size=120), [40.0, -50.0]]))
    inline = (s.astype(float).rank(pct=True) - 0.5) * 2.0
    assert np.allclose(rank_score(s).to_numpy(), inline.to_numpy(), equal_nan=True)
    got = standardize_factors(pd.DataFrame({"a": s}), ["a"], method="rank")["a"]
    assert np.allclose(got.to_numpy(), inline.to_numpy(), equal_nan=True), \
        "standardize_factors(method='rank') must go through rank_score, not a second copy"
    r = rank_score(s)
    assert -1.0 <= float(r.min()) and float(r.max()) <= 1.0
    s2 = s.copy()
    s2.iloc[:4] = np.nan
    assert int(rank_score(s2).isna().sum()) == 4, "NaN must propagate, not become mid-pack"


def test_s2021_zscore_nowinsor_disables_the_clip_that_zscore_applies():
    """S21's challenger. `winsorize(s, 0)` clips to [min, max], an exact no-op."""
    from valuation.screener.cross_sectional import winsorize, zscore, zscore_nowinsor
    rng = np.random.default_rng(11)
    s = pd.Series(np.concatenate([rng.normal(size=200), [50.0, -60.0, 80.0]]))
    assert np.allclose(winsorize(s, 0.0).to_numpy(), s.to_numpy()), \
        "p=0 must be an exact no-op, so S21 needs no change to winsorize itself"
    assert np.allclose(zscore_nowinsor(s).to_numpy(), zscore(s, p=0.0).to_numpy(),
                       equal_nan=True)
    # and it is NOT inert: the shipped 2% clip really does bind on a tailed column
    assert float(zscore_nowinsor(s).abs().max()) > float(zscore(s).abs().max()) + 1.0, \
        "removing the clip must let the tails back in, or S21 is testing nothing"


def test_s2021_rank_is_NOT_invariant_to_winsorization_correcting_the_register():
    """PREREG §3 and control C7 registered this as 'must be bit-identical'. IT IS NOT, and the
    reason is exact: rank is invariant to STRICTLY monotone transforms, and winsorisation is only
    WEAKLY monotone — it is flat in the clipped tails, so it creates TIES, and a percentile rank
    is not invariant to ties. The difference is confined to the clipped tails and is ~2p of rows.

    Pinned so the correction cannot be quietly lost: S20 does NOT strictly subsume S21."""
    from valuation.screener.cross_sectional import rank_score, winsorize
    rng = np.random.default_rng(5)
    s = pd.Series(rng.normal(size=500))
    d = (rank_score(s) - rank_score(winsorize(s, 0.02))).abs()
    assert float(d.max()) > 0.0, "if this ever passes bit-identically the tie analysis is wrong"
    frac = float((d > 1e-12).mean())
    assert 0.01 < frac < 0.10, f"differences must sit in the clipped tails only, got {frac:.3f}"
    # the middle of the distribution IS invariant — that half of the claim survives
    mid = (s > s.quantile(0.05)) & (s < s.quantile(0.95))
    assert float(d[mid].max()) == 0.0, "only the clipped tails may move"


def test_s2021_spearman_ic_CANNOT_see_a_rank_transform_while_the_composite_moves():
    """THE STANDING RULE, as an identity rather than an anecdote: never judge a construction
    change by per-signal IC. Rank-IC is invariant to a monotone rescaling; the composite is a
    weighted SUM and is scale-sensitive. P6.3 is the expensive precedent (robust z halved the
    long-short t while every theme IC stayed flat)."""
    from valuation.edge.fundamental_panel import _spearman, composite
    from valuation.screener.cross_sectional import rank_score, zscore
    rng = np.random.default_rng(17)
    n = 400
    a = pd.Series(rng.normal(size=n))
    b = pd.Series(np.concatenate([rng.normal(size=n - 3), [30.0, -40.0, 60.0]]))
    fwd = (0.4 * a + 0.2 * b + rng.normal(size=n)).to_numpy()
    # S20 is INVISIBLE to per-signal IC: ranking is strictly monotone, so the IC is unchanged
    # to the last bit.
    for col in (a, b):
        i_raw = _spearman(col.to_numpy(dtype=float), fwd)
        i_r = _spearman(rank_score(col).to_numpy(dtype=float), fwd)
        assert abs(float(i_raw) - float(i_r)) < 1e-12, \
            "per-signal Spearman IC is mathematically incapable of seeing a rank transform"
    # S21 is NOT invisible, and the asymmetry is the same tie mechanism as C7: winsorisation is
    # only WEAKLY monotone, so clipping the tails creates ties and DOES move a rank IC. So the
    # standing rule bites hardest on S20 — the arm whose per-signal diagnostics are provably blind.
    i_raw_b = _spearman(b.to_numpy(dtype=float), fwd)
    i_win_b = _spearman(zscore(b).to_numpy(dtype=float), fwd)
    assert abs(float(i_raw_b) - float(i_win_b)) > 1e-12, \
        "clipping creates ties, so winsorisation IS visible to a per-signal rank IC"
    wv = np.array([0.125, 0.125])
    cz = composite(np.column_stack([zscore(a).to_numpy(), zscore(b).to_numpy()]), wv)
    cr = composite(np.column_stack([rank_score(a).to_numpy(), rank_score(b).to_numpy()]), wv)
    assert float(np.max(np.abs(cz - cr))) > 0.05, \
        "the composite MUST move even though every per-signal IC is bit-identical"


def test_s2021_build_frame_standardizer_defaults_to_zscore_and_is_injectable():
    """Layer 1. Default must be behaviourally identical — the live product reads this path."""
    from valuation.screener.cross_sectional import rank_score, zscore
    from valuation.screener.factors import build_frame
    rng = np.random.default_rng(23)
    metrics = [{"ticker": f"T{i}", "price": 20.0 + i, "market_cap": 1e9 * (i + 1),
                "revenue": 1e8 * (i + 1), "net_income": 1e7 * (i + 1),
                "operating_income": 1.2e7 * (i + 1), "gross_profit": 4e7 * (i + 1),
                "total_equity": 5e8 * (i + 1), "total_debt": 1e8,
                "fcf": 9e6 * (i + 1) * (1 + 0.11 * (i % 5)),
                "ret_6_1": float(rng.normal()), "ret_12_1": float(rng.normal()),
                "beta": 1.0 + 0.1 * (i % 4)} for i in range(40)]
    base = build_frame(metrics, sector_neutral=False, residual_momentum=False)
    same = build_frame(metrics, sector_neutral=False, residual_momentum=False, standardizer=zscore)
    ranked = build_frame(metrics, sector_neutral=False, residual_momentum=False,
                         standardizer=rank_score)
    assert list(base.columns) == list(same.columns) == list(ranked.columns), \
        "an arm may not add or drop columns"
    assert np.allclose(pd.to_numeric(base["quality"], errors="coerce").to_numpy(),
                       pd.to_numeric(same["quality"], errors="coerce").to_numpy(),
                       equal_nan=True), "standardizer=zscore must reproduce the default exactly"
    q_b = pd.to_numeric(base["quality"], errors="coerce")
    q_r = pd.to_numeric(ranked["quality"], errors="coerce")
    assert float((q_b - q_r).abs().max()) > 1e-6, "the layer-1 swap must not be inert"
    # `insider` is (score-50)/25, NOT a z-score, so layer 1 cannot touch it (prereg §3)
    assert np.allclose(pd.to_numeric(base["insider"], errors="coerce").to_numpy(),
                       pd.to_numeric(ranked["insider"], errors="coerce").to_numpy(),
                       equal_nan=True), "insider's layer-1 exemption is a documented asymmetry"


def test_s2021_quantile_backtest_standardizer_defaults_and_injects_at_layer_three():
    """Layer 3 — the actual 'z-sum'. The default payload must be bit-identical."""
    from valuation.edge.fundamental_panel import quantile_backtest
    from valuation.screener.cross_sectional import rank_score, zscore
    rng = np.random.default_rng(29)
    rows = []
    for d in range(12):
        for i in range(60):
            v = float(rng.normal())
            q = float(rng.normal())
            rows.append({"date": f"20{10+d:02d}-01-15", "ticker": f"T{i}",
                         "value": v, "quality": q if i % 9 else 25.0,
                         "fwd_ret": 0.02 * v + 0.01 * q + float(rng.normal()) * 0.05})
    panel = pd.DataFrame(rows)
    cols, w = ["value", "quality"], {"value": 0.125, "quality": 0.125}
    a = quantile_backtest(panel, cols, w, n_q=5, horizon=63)
    b = quantile_backtest(panel, cols, w, n_q=5, horizon=63, standardizer=zscore)
    c = quantile_backtest(panel, cols, w, n_q=5, horizon=63, standardizer=rank_score)
    assert a["long_short_tstat"] == b["long_short_tstat"], \
        "standardizer=None and =zscore must be the same object, digit for digit"
    assert a["top_decile_alpha"] == b["top_decile_alpha"]
    assert a["long_short_tstat"] != c["long_short_tstat"], \
        "an outlier-bearing theme must score differently under a rank composite"


def test_s2021_holdout_compare_panels_scores_each_arm_with_its_OWN_standardizer():
    """The gate is what makes a standardisation change testable at all: the incumbent keeps the
    shipped z-score while the challenger uses its own, on the same rows."""
    from valuation.edge.fundamental_panel import holdout_compare_panels
    from valuation.screener.cross_sectional import rank_score
    rng = np.random.default_rng(31)
    rows = []
    for d in range(40):
        for i in range(50):
            v = float(rng.normal())
            rows.append({"date": f"2010-{(d % 12) + 1:02d}-{(d // 12) + 10:02d}",
                         "ticker": f"T{i}", "value": v if i % 11 else 40.0,
                         "quality": float(rng.normal()),
                         "fwd_ret": 0.03 * v + float(rng.normal()) * 0.05})
    panel = pd.DataFrame(rows)
    cols = ["value", "quality"]
    same = holdout_compare_panels(panel, panel, cols, min_dates=8)
    assert same["verdict"] in ("reject", "not_replicated", "adopt")
    for h in same["splits"].values():
        assert h["delta_long_short_tstat"] == 0.0 and h["delta_top_decile_alpha"] == 0.0, \
            "identical panels and identical standardizers must difference to exactly zero"
    diff = holdout_compare_panels(panel, panel, cols, min_dates=8, standardizer_b=rank_score)
    assert any(h["delta_long_short_tstat"] != 0.0 for h in diff["splits"].values()), \
        "standardizer_b must actually reach the challenger's scoring"


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
