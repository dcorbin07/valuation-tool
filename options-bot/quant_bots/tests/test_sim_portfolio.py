"""
Tests for the SimPortfolio accounting layer. This is money math — the
realized-P&L, average-cost, and sign-flip cases all need to be exactly right.
Pure, no network.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import SimPortfolio


class TestFills(unittest.TestCase):
    def test_open_long_reduces_cash(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)
        self.assertAlmostEqual(p.cash, 100_000 - 100 * 500.0)
        self.assertEqual(p.holdings["SPY"].shares, 100)
        self.assertAlmostEqual(p.holdings["SPY"].avg_cost, 500.0)

    def test_open_short_adds_cash(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("TLT", -50, 90.0)
        self.assertAlmostEqual(p.cash, 100_000 + 50 * 90.0)
        self.assertEqual(p.holdings["TLT"].shares, -50)

    def test_add_to_long_updates_avg_cost(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)
        p.apply_fill("SPY", 100, 520.0)
        self.assertEqual(p.holdings["SPY"].shares, 200)
        self.assertAlmostEqual(p.holdings["SPY"].avg_cost, 510.0)  # (500+520)/2

    def test_partial_close_realizes_pnl(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)     # long 100 @ 500
        p.apply_fill("SPY", -40, 520.0)     # sell 40 @ 520 → +$20 × 40 = $800
        self.assertAlmostEqual(p.realized_pnl, 800.0)
        self.assertEqual(p.holdings["SPY"].shares, 60)
        self.assertAlmostEqual(p.holdings["SPY"].avg_cost, 500.0)  # unchanged

    def test_full_close_removes_holding(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)
        p.apply_fill("SPY", -100, 510.0)    # close all → +$10 × 100 = $1000
        self.assertAlmostEqual(p.realized_pnl, 1000.0)
        self.assertNotIn("SPY", p.holdings)

    def test_short_profit_when_price_falls(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("TLT", -50, 90.0)      # short 50 @ 90
        p.apply_fill("TLT", 50, 80.0)       # cover 50 @ 80 → +$10 × 50 = $500
        self.assertAlmostEqual(p.realized_pnl, 500.0)
        self.assertNotIn("TLT", p.holdings)

    def test_long_to_short_flip(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)     # long 100
        p.apply_fill("SPY", -150, 510.0)    # sell 150: close 100 (+$1000), open short 50
        self.assertAlmostEqual(p.realized_pnl, 1000.0)
        self.assertEqual(p.holdings["SPY"].shares, -50)
        self.assertAlmostEqual(p.holdings["SPY"].avg_cost, 510.0)


class TestValuation(unittest.TestCase):
    def test_total_equity_long(self):
        p = SimPortfolio(cash=50_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)     # cash now 0, holding worth 50k @ cost
        eq = p.total_equity({"SPY": 510.0})  # marked up to 510
        # cash (50000 - 50000) + 100*510 = 51000
        self.assertAlmostEqual(eq, 51_000.0)

    def test_unrealized_pnl_short(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("TLT", -50, 90.0)
        # price drops to 80 → short gains (90-80)*50 = 500
        self.assertAlmostEqual(p.unrealized_pnl({"TLT": 80.0}), 500.0)

    def test_signed_shares_map(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        p.apply_fill("SPY", 100, 500.0)
        p.apply_fill("TLT", -50, 90.0)
        ss = p.signed_shares()
        self.assertEqual(ss["SPY"], 100)
        self.assertEqual(ss["TLT"], -50)


class TestSlippage(unittest.TestCase):
    def test_slippage_worsens_fills(self):
        p = SimPortfolio(cash=100_000, starting_equity=100_000)
        # Buy with 0.05 slippage → effective 500.05
        p.apply_fill("SPY", 100, 500.0, slippage_per_share=0.05)
        self.assertAlmostEqual(p.holdings["SPY"].avg_cost, 500.05)
        self.assertAlmostEqual(p.cash, 100_000 - 100 * 500.05)


class TestPersistence(unittest.TestCase):
    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portfolio.json"
            p = SimPortfolio(cash=100_000, starting_equity=100_000)
            p.apply_fill("SPY", 100, 500.0)
            p.apply_fill("TLT", -50, 90.0)
            p.save(path)

            p2 = SimPortfolio.load_or_init(path)
            self.assertAlmostEqual(p2.cash, p.cash)
            self.assertEqual(p2.holdings["SPY"].shares, 100)
            self.assertEqual(p2.holdings["TLT"].shares, -50)

    def test_load_missing_inits_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nope.json"
            p = SimPortfolio.load_or_init(path, initial_cash=250_000)
            self.assertEqual(p.cash, 250_000)
            self.assertEqual(p.starting_equity, 250_000)

    def test_corrupt_file_inits_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not valid")
            p = SimPortfolio.load_or_init(path, initial_cash=100_000)
            self.assertEqual(p.cash, 100_000)


class TestEquityCurve(unittest.TestCase):
    def test_snapshot_appends_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            curve = Path(tmp) / "equity_curve.jsonl"
            p = SimPortfolio(cash=100_000, starting_equity=100_000)
            p.apply_fill("SPY", 100, 500.0)
            snap1 = p.record_equity_snapshot(curve, {"SPY": 510.0})
            snap2 = p.record_equity_snapshot(curve, {"SPY": 520.0})
            lines = curve.read_text().strip().split("\n")
            self.assertEqual(len(lines), 2)
            # Equity rose as SPY went 510 → 520
            self.assertGreater(snap2["equity"], snap1["equity"])
            self.assertIn("return_since_start", snap1)

    def test_return_since_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            curve = Path(tmp) / "ec.jsonl"
            p = SimPortfolio(cash=100_000, starting_equity=100_000)
            p.apply_fill("SPY", 100, 500.0)   # 50k deployed
            snap = p.record_equity_snapshot(curve, {"SPY": 550.0})  # +10% on holding
            # equity = 50k cash + 55k = 105k → +5% overall
            self.assertAlmostEqual(snap["return_since_start"], 0.05, places=4)


if __name__ == "__main__":
    unittest.main()
