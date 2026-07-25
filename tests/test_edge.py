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


def test_edge_routes_owner_only():
    owner = {"email": "donniecorbin6@gmail.com"}
    other = {"email": "someone@else.com"}
    assert gating.check_request("/api/edge/backtest", "POST", {}, other, None)[1] == 403
    assert gating.check_request("/api/edge/optimize", "POST", {}, None, None)[1] in (401, 403)
    assert gating.check_request("/api/edge/backtest", "POST", {}, owner, None) is None


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
