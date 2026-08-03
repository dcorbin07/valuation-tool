"""
Tests for the trend bot's core logic (T3-T6). Pure functions, no network.
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import EquitySide
from trend import (
    Direction,
    PortfolioConfig,
    RiskConfig,
    SignalConfig,
    StrategyConfig,
    TrendRiskManager,
    TrendStrategy,
    compute_signal_from_closes,
    orders_to_reach_target,
)
from trend.signals import Signal


# ─── T3: Signals ────────────────────────────────────────────────────────────


class TestSignals(unittest.TestCase):
    def _rising_series(self, n=300, start=100.0, daily=0.001):
        # Steadily rising series → positive 12mo momentum → LONG
        return [start * ((1 + daily) ** i) for i in range(n)]

    def _falling_series(self, n=300, start=100.0, daily=-0.001):
        return [start * ((1 + daily) ** i) for i in range(n)]

    def test_rising_series_is_long(self):
        sig = compute_signal_from_closes("SPY", self._rising_series(), SignalConfig())
        self.assertEqual(sig.direction, Direction.LONG)
        self.assertGreater(sig.momentum_return, 0)
        self.assertTrue(sig.usable)

    def test_falling_series_is_short(self):
        sig = compute_signal_from_closes("TLT", self._falling_series(), SignalConfig())
        self.assertEqual(sig.direction, Direction.SHORT)
        self.assertLess(sig.momentum_return, 0)

    def test_insufficient_data_unusable(self):
        sig = compute_signal_from_closes("XYZ", [100.0] * 50, SignalConfig())
        self.assertFalse(sig.usable)
        self.assertEqual(sig.direction, Direction.FLAT)

    def test_volatility_positive_for_varying_series(self):
        sig = compute_signal_from_closes("SPY", self._rising_series(), SignalConfig())
        self.assertGreater(sig.annualized_vol, 0)

    def test_deadband_makes_flat(self):
        # Flat series with a big deadband → FLAT
        flat = [100.0 + (i % 2) * 0.01 for i in range(300)]  # barely moves
        cfg = SignalConfig(momentum_deadband=0.50)  # 50% deadband
        sig = compute_signal_from_closes("X", flat, cfg)
        self.assertEqual(sig.direction, Direction.FLAT)


# ─── T4: Strategy ───────────────────────────────────────────────────────────


def sig(symbol, direction, vol, price=100.0):
    return Signal(symbol, direction, 0.2 if direction == Direction.LONG else -0.2,
                  vol, price, 300, True)


class TestStrategy(unittest.TestCase):
    def test_inverse_vol_weighting(self):
        # Lower vol → bigger weight
        signals = {
            "LOWVOL": sig("LOWVOL", Direction.LONG, 0.10),
            "HIGHVOL": sig("HIGHVOL", Direction.LONG, 0.40),
        }
        target = TrendStrategy(StrategyConfig()).build_target(signals)
        weights = {w.symbol: w.normalized_weight for w in target.weights}
        self.assertGreater(weights["LOWVOL"], weights["HIGHVOL"])

    def test_gross_normalizes_to_one(self):
        signals = {
            "A": sig("A", Direction.LONG, 0.20),
            "B": sig("B", Direction.SHORT, 0.20),
            "C": sig("C", Direction.LONG, 0.30),
        }
        target = TrendStrategy(StrategyConfig()).build_target(signals)
        gross = sum(abs(w.normalized_weight) for w in target.weights)
        self.assertAlmostEqual(gross, 1.0, places=6)

    def test_shorts_are_negative(self):
        signals = {"A": sig("A", Direction.SHORT, 0.20)}
        target = TrendStrategy(StrategyConfig()).build_target(signals)
        self.assertLess(target.weights[0].normalized_weight, 0)

    def test_flat_and_unusable_excluded(self):
        signals = {
            "GOOD": sig("GOOD", Direction.LONG, 0.20),
            "FLAT": sig("FLAT", Direction.FLAT, 0.20),
            "BAD": Signal("BAD", Direction.LONG, 0.2, 0.2, 100, 300, False),
        }
        target = TrendStrategy(StrategyConfig()).build_target(signals)
        self.assertEqual(len(target.weights), 1)
        self.assertEqual(target.weights[0].symbol, "GOOD")


# ─── T5: Risk ───────────────────────────────────────────────────────────────


class TestRisk(unittest.TestCase):
    def _target(self, signals):
        return TrendStrategy(StrategyConfig()).build_target(signals)

    def test_kill_switch_flattens(self):
        target = self._target({"A": sig("A", Direction.LONG, 0.20)})
        rm = TrendRiskManager(RiskConfig(daily_loss_limit_pct=-0.05))
        res = rm.size(target, 100000, {"A": 100}, today_pnl_pct=-0.06)
        self.assertTrue(res.kill_switch_active)
        self.assertEqual(len(res.targets), 0)

    def test_gross_exposure_capped(self):
        signals = {f"S{i}": sig(f"S{i}", Direction.LONG, 0.15) for i in range(5)}
        target = self._target(signals)
        rm = TrendRiskManager(RiskConfig(max_gross_exposure=1.0, target_annual_vol=0.50))
        res = rm.size(target, 100000, {f"S{i}": 100 for i in range(5)})
        # Even with high vol target, gross can't exceed 100%
        self.assertLessEqual(res.gross_exposure, 1.01)

    def test_per_instrument_cap(self):
        # One instrument would dominate; cap holds it to 20%
        signals = {"BIG": sig("BIG", Direction.LONG, 0.05)}  # very low vol → big weight
        target = self._target(signals)
        rm = TrendRiskManager(RiskConfig(max_per_instrument=0.20))
        res = rm.size(target, 100000, {"BIG": 100})
        if "BIG" in res.targets:
            self.assertLessEqual(abs(res.targets["BIG"].target_notional), 0.21 * 100000)

    def test_produces_signed_shares(self):
        signals = {
            "LONGER": sig("LONGER", Direction.LONG, 0.20, price=50),
            "SHORTER": sig("SHORTER", Direction.SHORT, 0.20, price=50),
        }
        target = self._target(signals)
        rm = TrendRiskManager(RiskConfig())
        res = rm.size(target, 100000, {"LONGER": 50, "SHORTER": 50})
        self.assertGreater(res.targets["LONGER"].target_shares, 0)
        self.assertLess(res.targets["SHORTER"].target_shares, 0)


# ─── T6: Portfolio rebalance diff (the tricky sign-flip logic) ───────────────


class TestRebalanceOrders(unittest.TestCase):
    def test_open_long_from_zero(self):
        orders = orders_to_reach_target("SPY", 0, 100)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].side, EquitySide.BUY)
        self.assertEqual(orders[0].quantity, 100)

    def test_open_short_from_zero(self):
        orders = orders_to_reach_target("TLT", 0, -50)
        self.assertEqual(orders[0].side, EquitySide.SELL_SHORT)
        self.assertEqual(orders[0].quantity, 50)

    def test_add_to_long(self):
        orders = orders_to_reach_target("SPY", 100, 150)
        self.assertEqual(orders[0].side, EquitySide.BUY)
        self.assertEqual(orders[0].quantity, 50)

    def test_reduce_long(self):
        orders = orders_to_reach_target("SPY", 100, 60)
        self.assertEqual(orders[0].side, EquitySide.SELL)
        self.assertEqual(orders[0].quantity, 40)

    def test_close_long_fully(self):
        orders = orders_to_reach_target("SPY", 100, 0)
        self.assertEqual(orders[0].side, EquitySide.SELL)
        self.assertEqual(orders[0].quantity, 100)

    def test_close_short_fully(self):
        orders = orders_to_reach_target("TLT", -50, 0)
        self.assertEqual(orders[0].side, EquitySide.BUY_TO_COVER)
        self.assertEqual(orders[0].quantity, 50)

    def test_add_to_short(self):
        orders = orders_to_reach_target("TLT", -50, -80)
        self.assertEqual(orders[0].side, EquitySide.SELL_SHORT)
        self.assertEqual(orders[0].quantity, 30)

    def test_reduce_short(self):
        orders = orders_to_reach_target("TLT", -50, -20)
        self.assertEqual(orders[0].side, EquitySide.BUY_TO_COVER)
        self.assertEqual(orders[0].quantity, 30)

    def test_long_to_short_flip_two_orders(self):
        orders = orders_to_reach_target("SPY", 100, -50)
        self.assertEqual(len(orders), 2)
        # First flatten the long, then open the short
        self.assertEqual(orders[0].side, EquitySide.SELL)
        self.assertEqual(orders[0].quantity, 100)
        self.assertEqual(orders[1].side, EquitySide.SELL_SHORT)
        self.assertEqual(orders[1].quantity, 50)

    def test_short_to_long_flip_two_orders(self):
        orders = orders_to_reach_target("TLT", -50, 30)
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[0].side, EquitySide.BUY_TO_COVER)
        self.assertEqual(orders[0].quantity, 50)
        self.assertEqual(orders[1].side, EquitySide.BUY)
        self.assertEqual(orders[1].quantity, 30)

    def test_no_change_no_orders(self):
        self.assertEqual(orders_to_reach_target("SPY", 100, 100), [])


if __name__ == "__main__":
    unittest.main()
