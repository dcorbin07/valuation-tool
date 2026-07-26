"""Intraday signal tests (offline, synthetic bars). Run: python tests/test_intraday.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.intraday.signals import evaluate
from valuation.intraday.contracts import contract_idea, HORIZONS


def _uptrend_bars(n=260):
    close = [10.0 * (1 + 0.001 * i) for i in range(n)]
    return {"close": close, "high": [c * 1.01 for c in close],
            "low": [c * 0.99 for c in close], "volume": [1e6] * n}


def test_horizon_changes_score():
    bars = _uptrend_bars()
    opt = {"put_volume": 100, "call_volume": 400, "put_oi": 1000, "call_oi": 1000, "atm_iv": 0.35}
    sc = {h: evaluate(bars, opt, horizon=h)["score"] for h in HORIZONS}
    assert all(v is not None and 0 <= v <= 100 for v in sc.values())
    assert len({round(v, 1) for v in sc.values()}) >= 2      # horizon actually changes the blend


def test_contract_idea_scales_with_horizon():
    short = contract_idea(100.0, 0.30, "short")
    pos = contract_idea(100.0, 0.30, "position")
    assert short and pos
    assert short["dte_range"][1] < pos["dte_range"][0]              # nearer expiries for short
    assert pos["expected_move_abs"] > short["expected_move_abs"]     # longer horizon = bigger move
    assert "Put credit spread" in short["defined_risk"]
    assert contract_idea(None, 0.3, "swing") is None                # no price -> no idea


def test_bearish_scores_downtrend():
    from valuation.intraday.signals import evaluate_bearish
    n = 260
    down = {"close": [100.0 * (1 - 0.001 * i) for i in range(n)]}
    down["high"] = [c * 1.01 for c in down["close"]]
    down["low"] = [c * 0.99 for c in down["close"]]
    down["volume"] = [1e6] * n
    sb_down = evaluate_bearish(down, None, "swing")["score"]
    sb_up = evaluate_bearish(_uptrend_bars(), None, "swing")["score"]
    assert sb_down is not None and sb_down > 55        # a downtrend reads bearish
    assert sb_down > sb_up                              # ...and more bearish than an uptrend


def test_contract_direction():
    from valuation.intraday.contracts import contract_idea
    bull = contract_idea(100.0, 0.3, "swing", "bull")
    bear = contract_idea(100.0, 0.3, "swing", "bear")
    assert "call" in bull["directional"] and "Put credit spread" in bull["defined_risk"]
    assert "put" in bear["directional"] and "Call credit spread" in bear["defined_risk"]


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
    print(f"\n{passed}/{len(tests)} intraday tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
