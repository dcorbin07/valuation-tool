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


# ----------------------------- options exit rule -----------------------------
def _flat_then(move_pct, n_pre=80, n_post=200, start=100.0):
    """80 quiet bars (so realized vol is defined) then a decisive step to start*(1+move_pct).

    The step is deliberately far beyond the ~12% 1-sigma band at iv=0.30/swing, so the
    target or stop is unambiguously crossed and the test isn't sitting on a boundary.
    """
    pre = [start * (1 + 0.001 * ((i % 5) - 2)) for i in range(n_pre)]   # tiny wiggle
    post = [start * (1 + move_pct)] * n_post
    return pre + post


def test_options_exit_take_profit_fires_first():
    from valuation.edge.options_exit import simulate_exit
    closes = _flat_then(+0.40)                      # strong rally after entry
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bull", iv=0.30)
    assert e["outcome"] == "take_profit", e["outcome"]
    assert e["signal_return"] > 0
    assert e["exit_idx"] > e["entry_idx"]
    assert e["bars_held"] <= round(e["dte"] * 252 / 365) + 1


def test_options_exit_stop_loss_fires_first():
    from valuation.edge.options_exit import simulate_exit
    closes = _flat_then(-0.40)                      # sharp decline after entry
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bull", iv=0.30)
    assert e["outcome"] == "stop_loss", e["outcome"]
    assert e["signal_return"] < 0


def test_options_exit_time_stop_when_nothing_triggers():
    from valuation.edge.options_exit import simulate_exit
    closes = [100.0] * 400                          # dead flat: never hits +/-1 sigma
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bull", iv=0.30)
    assert e["outcome"] == "time_stop", e["outcome"]
    assert abs(e["signal_return"]) < 1e-9
    assert e["bars_held"] == round(e["dte"] * 252 / 365)


def test_options_exit_bearish_profits_on_a_fall():
    from valuation.edge.options_exit import simulate_exit
    closes = _flat_then(-0.40)
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bear", iv=0.30)
    assert e["outcome"] == "take_profit", e["outcome"]
    assert e["signal_return"] > 0, "a bearish signal should profit when price falls"
    assert e["underlying_return"] < 0


def test_options_exit_vol_fallback_is_strictly_pre_entry():
    """Direct no-look-ahead check: mutating bars AFTER the entry must not move the vol."""
    from valuation.edge.options_exit import realized_vol
    closes = _flat_then(+0.40)
    v_before = realized_vol(closes, end_idx=79)
    tampered = list(closes)
    for i in range(79, len(tampered)):            # violent post-entry noise
        tampered[i] = 100.0 * (3.0 if i % 2 else 0.4)
    v_after = realized_vol(tampered, end_idx=79)
    assert v_before is not None and v_before > 0
    assert v_after == v_before, "realized_vol must ignore everything at/after entry_idx"


def test_options_exit_summary_shapes():
    from valuation.edge.options_exit import simulate_exit, summarize_exits
    ex = [simulate_exit(_flat_then(+0.40), 79, iv=0.30),
          simulate_exit(_flat_then(-0.40), 79, iv=0.30),
          simulate_exit([100.0] * 400, 79, iv=0.30)]
    s = summarize_exits(ex)
    assert s["n"] == 3
    assert set(s["by_outcome"]) == {"take_profit", "stop_loss", "time_stop"}
    assert abs(s["take_profit_rate"] - 1 / 3) < 1e-9
    assert summarize_exits([])["n"] == 0


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

