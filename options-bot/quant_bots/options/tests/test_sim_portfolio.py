"""
Money-math tests for the options SimPortfolio (spread-level simulation).
Units: credit and close costs are PER-SPREAD DOLLARS (premium/share × 100).
So a $0.72/share credit is 72.0; cash flows multiply only by contracts.
A put credit spread profits when the buy-to-close cost falls below the credit.
"""
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from portfolio.sim_portfolio import OptionsSimPortfolio, SimSpread

SID = "SLV-2026-07-01-61-56"


def make_spread(credit_per_spread=72.0, contracts=9):
    # 72.0 = $0.72/share × 100
    return SimSpread(spread_id=SID, underlying="SLV", expiration="2026-07-01",
                     short_strike=61.0, long_strike=56.0, contracts=contracts,
                     credit_received_per_spread=credit_per_spread)


class TestOpenClose(unittest.TestCase):
    def test_open_receives_credit(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))
        # credit = 72 * 9 = 648
        self.assertAlmostEqual(p.cash, 100_648.0)

    def test_close_at_profit(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))           # +648
        pnl = p.close_spread(SID, close_cost_per_spread=36.0)  # buy back at half
        self.assertAlmostEqual(pnl, 324.0)            # (72-36)*9
        self.assertAlmostEqual(p.cash, 100_324.0)     # 100648 - 36*9
        self.assertEqual(len(p.open_spreads), 0)

    def test_close_at_loss(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))
        pnl = p.close_spread(SID, close_cost_per_spread=144.0)  # 2x credit
        self.assertAlmostEqual(pnl, -648.0)           # (72-144)*9

    def test_close_worthless_full_profit(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))
        pnl = p.close_spread(SID, close_cost_per_spread=0.0)
        self.assertAlmostEqual(pnl, 648.0)


class TestValuation(unittest.TestCase):
    def test_equity_flat_at_open_when_marked_at_credit(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))
        # marked at the same 72 → equity = 100648 - 72*9 = 100000
        self.assertAlmostEqual(p.total_equity({SID: 72.0}), 100_000.0)

    def test_equity_rises_as_close_cost_falls(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))
        # close cost 72 -> 36 → equity rises by 324
        self.assertAlmostEqual(p.total_equity({SID: 36.0}), 100_324.0)

    def test_unrealized_pnl(self):
        p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
        p.open_spread(make_spread(72.0, 9))
        self.assertAlmostEqual(p.unrealized_pnl({SID: 36.0}), 324.0)


class TestPersistence(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
            p.open_spread(make_spread())
            p.save(path)
            p2 = OptionsSimPortfolio.load_or_init(path)
            self.assertAlmostEqual(p2.cash, p.cash)
            self.assertEqual(len(p2.open_spreads), 1)

    def test_equity_curve_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            curve = Path(tmp) / "equity_curve.jsonl"
            p = OptionsSimPortfolio(cash=100_000, starting_equity=100_000)
            p.open_spread(make_spread())
            snap = p.record_equity_snapshot(curve, {SID: 36.0})
            for k in ("date", "equity", "return_since_start", "num_positions"):
                self.assertIn(k, snap)


if __name__ == "__main__":
    unittest.main()
