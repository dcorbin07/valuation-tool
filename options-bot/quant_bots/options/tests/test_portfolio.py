"""
Portfolio module unit tests. No network required — Tradier is mocked.
"""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from portfolio import (
    ExitDecision,
    PortfolioConfig,
    PortfolioManager,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def leg(symbol: str, quantity: float, cost_basis: float) -> dict:
    """A Tradier position leg. cost_basis negative=short(received), positive=long(paid)."""
    return {"symbol": symbol, "quantity": quantity, "cost_basis": cost_basis}


def quote(symbol: str, bid: float, ask: float, last: float = None) -> dict:
    return {"symbol": symbol, "bid": bid, "ask": ask, "last": last or (bid + ask) / 2}


def worthless_long_quote(symbol: str) -> dict:
    """
    A far-OTM long wing that nobody bids for: 0.00 x 0.05, no trade today.

    This is a REAL market, not a missing quote — the bid of zero means "nobody
    will pay a cent", which is the ordinary state of the long leg on a spread
    that is winning. The pricing layer must accept it (long_bid = 0.00) rather
    than call the spread unpriceable, or the profit target would never fire.
    Contrast with a genuinely absent quote, which has no bid, ask, OR last.
    """
    return {"symbol": symbol, "bid": 0.0, "ask": 0.05, "last": 0.0}


# SPY 35-DTE put credit spread: short 565, long 560.
# Opened for $1.00 credit/spread = $100 received (short premium higher than long).
EXP = (date.today() + timedelta(days=35))
EXP_STR = EXP.strftime("%y%m%d")
SHORT_OCC = f"SPY{EXP_STR}P00565000"
LONG_OCC = f"SPY{EXP_STR}P00560000"


def make_manager(quotes: dict, positions: list) -> PortfolioManager:
    tradier = MagicMock()
    tradier.get_positions.return_value = positions
    tradier.get_quotes.side_effect = lambda syms: [quotes[s] for s in syms if s in quotes]
    return PortfolioManager(PortfolioConfig(), tradier)


# ─── Pairing ────────────────────────────────────────────────────────────────


class TestPairing(unittest.TestCase):
    def test_basic_spread_paired(self):
        positions = [
            leg(SHORT_OCC, -1, -150.0),  # received $150 for short
            leg(LONG_OCC, 1, 50.0),      # paid $50 for long → net $100 credit
        ]
        quotes = {
            SHORT_OCC: quote(SHORT_OCC, 0.45, 0.50),
            LONG_OCC: quote(LONG_OCC, 0.15, 0.20),
        }
        mgr = make_manager(quotes, positions)
        snap = mgr.sync()
        self.assertEqual(len(snap.spreads), 1)
        s = snap.spreads[0]
        self.assertEqual(s.underlying, "SPY")
        self.assertEqual(s.short_strike, 565.0)
        self.assertEqual(s.long_strike, 560.0)
        self.assertEqual(s.contracts, 1)
        self.assertAlmostEqual(s.credit_received_per_spread, 100.0)

    def test_unpaired_short_with_no_long(self):
        positions = [leg(SHORT_OCC, -1, -150.0)]
        quotes = {SHORT_OCC: quote(SHORT_OCC, 0.45, 0.50)}
        mgr = make_manager(quotes, positions)
        snap = mgr.sync()
        self.assertEqual(len(snap.spreads), 0)
        self.assertEqual(len(snap.unpaired_legs), 1)

    def test_stock_positions_ignored(self):
        positions = [
            {"symbol": "AAPL", "quantity": 100, "cost_basis": 18000.0},  # stock
            leg(SHORT_OCC, -1, -150.0),
            leg(LONG_OCC, 1, 50.0),
        ]
        quotes = {
            SHORT_OCC: quote(SHORT_OCC, 0.45, 0.50),
            LONG_OCC: quote(LONG_OCC, 0.15, 0.20),
        }
        mgr = make_manager(quotes, positions)
        snap = mgr.sync()
        self.assertEqual(len(snap.spreads), 1)


# ─── Exit decisions ─────────────────────────────────────────────────────────


class TestExitDecisions(unittest.TestCase):
    def _spread_with_close_cost(self, close_cost_per_share_short_ask, long_bid,
                                  credit_cb_short=-100.0, credit_cb_long=0.0,
                                  dte_days=35):
        exp = date.today() + timedelta(days=dte_days)
        exp_str = exp.strftime("%y%m%d")
        short_occ = f"SPY{exp_str}P00565000"
        long_occ = f"SPY{exp_str}P00560000"
        positions = [
            leg(short_occ, -1, credit_cb_short),
            leg(long_occ, 1, credit_cb_long),
        ]
        quotes = {
            short_occ: quote(short_occ, close_cost_per_share_short_ask - 0.05,
                             close_cost_per_share_short_ask),
            long_occ: quote(long_occ, long_bid, long_bid + 0.05),
        }
        mgr = make_manager(quotes, positions)
        return mgr.sync().spreads[0]

    def test_close_profit_at_50pct(self):
        # Opened for $100 credit ($1.00). Now costs $0.50 to close → captured 50%.
        # short cost basis -100 = $1.00 credit/spread.
        s = self._spread_with_close_cost(
            close_cost_per_share_short_ask=0.50, long_bid=0.0,
            credit_cb_short=-100.0, credit_cb_long=0.0,
        )
        # close cost = (0.50 - 0.0) * 100 = $50. credit $100. pnl = $50 = 50%.
        self.assertEqual(s.decision, ExitDecision.CLOSE_PROFIT)

    def test_hold_when_small_profit(self):
        # Opened $100 credit, costs $0.80 to close → captured only 20%.
        s = self._spread_with_close_cost(
            close_cost_per_share_short_ask=0.80, long_bid=0.0,
            credit_cb_short=-100.0,
        )
        self.assertEqual(s.decision, ExitDecision.HOLD)

    def test_close_stop_at_2x_loss(self):
        # Opened $100 credit. Now costs $3.20 to close → loss of $220 = 2.2x credit.
        # (Comfortably past the 2.0x stop threshold so the test isn't fragile to
        # the helper's bid = ask-0.05 construction.)
        s = self._spread_with_close_cost(
            close_cost_per_share_short_ask=3.20, long_bid=0.0,
            credit_cb_short=-100.0,
        )
        self.assertEqual(s.decision, ExitDecision.CLOSE_STOP)

    def test_close_time_at_21_dte(self):
        # Profitable-but-not-enough, but DTE is 21 → time exit.
        s = self._spread_with_close_cost(
            close_cost_per_share_short_ask=0.80, long_bid=0.0,
            credit_cb_short=-100.0, dte_days=21,
        )
        self.assertEqual(s.decision, ExitDecision.CLOSE_TIME)

    def test_profit_takes_priority_over_time(self):
        # Both profit target AND time exit met → profit wins (checked first).
        s = self._spread_with_close_cost(
            close_cost_per_share_short_ask=0.40, long_bid=0.0,
            credit_cb_short=-100.0, dte_days=21,
        )
        self.assertEqual(s.decision, ExitDecision.CLOSE_PROFIT)


# ─── Closing legs ───────────────────────────────────────────────────────────


class TestClosingLegs(unittest.TestCase):
    def test_closing_legs_reverse_sides(self):
        positions = [
            leg(SHORT_OCC, -1, -150.0),
            leg(LONG_OCC, 1, 50.0),
        ]
        quotes = {
            SHORT_OCC: quote(SHORT_OCC, 0.40, 0.45),
            LONG_OCC: quote(LONG_OCC, 0.10, 0.15),
        }
        mgr = make_manager(quotes, positions)
        s = mgr.sync().spreads[0]
        legs = s.to_closing_legs()
        self.assertEqual(len(legs), 2)
        # Closing a short put = buy_to_close; closing the long = sell_to_close
        self.assertEqual(legs[0].side.value, "buy_to_close")
        self.assertEqual(legs[1].side.value, "sell_to_close")


# ─── P&L math ───────────────────────────────────────────────────────────────


class TestPnLMath(unittest.TestCase):
    def test_pnl_computation(self):
        # $100 credit, costs $30 to close → +$70 unrealized, 70% of credit.
        positions = [
            leg(SHORT_OCC, -1, -100.0),
            leg(LONG_OCC, 1, 0.0),
        ]
        quotes = {
            SHORT_OCC: quote(SHORT_OCC, 0.25, 0.30),
            LONG_OCC: worthless_long_quote(LONG_OCC),
        }
        mgr = make_manager(quotes, positions)
        s = mgr.sync().spreads[0]
        # close cost = 0.30 * 100 = $30. pnl = 100 - 30 = $70.
        self.assertAlmostEqual(s.unrealized_pnl_dollars, 70.0)
        self.assertAlmostEqual(s.pnl_pct_of_credit, 0.70)

    def test_multi_contract_pnl(self):
        # 5 contracts, $100 credit each. Costs $40 to close each.
        positions = [
            leg(SHORT_OCC, -5, -500.0),
            leg(LONG_OCC, 5, 0.0),
        ]
        quotes = {
            SHORT_OCC: quote(SHORT_OCC, 0.35, 0.40),
            LONG_OCC: worthless_long_quote(LONG_OCC),
        }
        mgr = make_manager(quotes, positions)
        s = mgr.sync().spreads[0]
        self.assertEqual(s.contracts, 5)
        self.assertAlmostEqual(s.credit_received_per_spread, 100.0)
        # close cost = $40/spread × 5 = $200 total pnl... wait:
        # pnl_per_spread = 100 - 40 = 60; × 5 = $300
        self.assertAlmostEqual(s.unrealized_pnl_dollars, 300.0)


if __name__ == "__main__":
    unittest.main()
