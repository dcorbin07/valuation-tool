"""Tests for the sim-execution helpers and SIM-mode rebalance integration."""
import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import EquitySide, SimPortfolio, apply_orders_to_sim, finalize_sim, load_sim, sim_paths


class _Order:
    def __init__(self, symbol, side, quantity):
        self.symbol, self.side, self.quantity = symbol, side, quantity


class TestSimExecution(unittest.TestCase):
    def test_apply_orders_buys_and_shorts(self):
        sim = SimPortfolio(cash=100000, starting_equity=100000)
        orders = [_Order("SPY", EquitySide.BUY, 100),
                  _Order("TLT", EquitySide.SELL_SHORT, 50)]
        fills = apply_orders_to_sim(sim, orders, {"SPY": 500.0, "TLT": 90.0})
        self.assertEqual(len(fills), 2)
        self.assertEqual(sim.signed_shares()["SPY"], 100)
        self.assertEqual(sim.signed_shares()["TLT"], -50)

    def test_sell_reduces_long(self):
        sim = SimPortfolio(cash=100000, starting_equity=100000)
        apply_orders_to_sim(sim, [_Order("SPY", EquitySide.BUY, 100)], {"SPY": 500.0})
        apply_orders_to_sim(sim, [_Order("SPY", EquitySide.SELL, 40)], {"SPY": 510.0})
        self.assertEqual(sim.signed_shares()["SPY"], 60)

    def test_no_price_skips_fill(self):
        sim = SimPortfolio(cash=100000, starting_equity=100000)
        fills = apply_orders_to_sim(sim, [_Order("XYZ", EquitySide.BUY, 10)], {})
        self.assertEqual(len(fills), 0)

    def test_finalize_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sim = SimPortfolio(cash=100000, starting_equity=100000)
            apply_orders_to_sim(sim, [_Order("SPY", EquitySide.BUY, 10)], {"SPY": 500.0})
            snap = finalize_sim(sim, root, "trend", {"SPY": 510.0}, label="test")
            pf, curve = sim_paths(root, "trend")
            self.assertTrue(pf.exists())
            self.assertTrue(curve.exists())
            self.assertIn("equity", snap)

    def test_load_sim_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sim = load_sim(root, "momentum", initial_cash=50000)
            apply_orders_to_sim(sim, [_Order("AAA", EquitySide.BUY, 5)], {"AAA": 100.0})
            finalize_sim(sim, root, "momentum", {"AAA": 100.0})
            sim2 = load_sim(root, "momentum", initial_cash=50000)
            self.assertEqual(sim2.signed_shares()["AAA"], 5)


if __name__ == "__main__":
    unittest.main()
