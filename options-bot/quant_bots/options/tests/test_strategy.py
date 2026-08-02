"""
Strategy module unit tests. No network access required.
"""
import unittest
from datetime import date, timedelta

from screener import ScreenedCandidate
from strategy import (
    PutCreditSpreadStrategy,
    StrategyConfig,
    make_fingerprint,
)


# ─── Test helpers ───────────────────────────────────────────────────────────


def make_candidate(
    symbol: str = "SPY",
    spot: float = 100.0,
    short_strike: float = 90.0,
    long_strike: float = 85.0,
    short_mid: float = 1.20,
    long_mid: float = 0.40,
    atm_iv: float = 0.30,
    is_etf: bool = False,
) -> ScreenedCandidate:
    target_exp = date.today() + timedelta(days=35)
    spread_width = short_strike - long_strike
    credit_mid = short_mid - long_mid
    return ScreenedCandidate(
        symbol=symbol,
        last_price=spot,
        is_etf=is_etf,
        target_expiration=target_exp,
        dte=35,
        short_put_strike=short_strike,
        short_put_delta=0.20,
        short_put_bid=short_mid * 0.98,
        short_put_ask=short_mid * 1.02,
        short_put_mid=short_mid,
        short_put_iv=atm_iv,
        short_put_open_interest=500,
        long_put_strike=long_strike,
        long_put_bid=long_mid * 0.98,
        long_put_ask=long_mid * 1.02,
        long_put_mid=long_mid,
        spread_credit_mid=credit_mid,
        spread_max_loss=(spread_width - credit_mid) * 100,
        spread_return_on_risk=(
            credit_mid / (spread_width - credit_mid)
            if (spread_width - credit_mid) > 0 else 0
        ),
        atm_iv=atm_iv,
        next_earnings=None,
    )


# ─── Tests ──────────────────────────────────────────────────────────────────


class TestOrderConstruction(unittest.TestCase):
    def test_basic_order_built(self):
        s = PutCreditSpreadStrategy(StrategyConfig())
        candidate = make_candidate(symbol="SPY", spot=100.0,
                                     short_strike=90, long_strike=85,
                                     short_mid=1.20, long_mid=0.40)
        result = s.build_orders([candidate])
        self.assertEqual(len(result.orders), 1)
        order = result.orders[0]
        self.assertEqual(order.symbol, "SPY")
        self.assertEqual(order.short_strike, 90.0)
        self.assertEqual(order.long_strike, 85.0)
        self.assertEqual(order.contracts, 1)
        # Credit at 95% of mid: (1.20 - 0.40) * 0.95 = 0.76
        self.assertAlmostEqual(order.target_credit_per_contract, 0.76, places=4)
        # Max loss: (5.0 - 0.76) * 100 = 424
        self.assertAlmostEqual(order.estimated_max_loss, 424.0, places=2)

    def test_occ_symbols_built_correctly(self):
        s = PutCreditSpreadStrategy(StrategyConfig())
        candidate = make_candidate(symbol="SPY", short_strike=565, long_strike=560)
        # Force expiration to a known date for the assertion
        candidate.target_expiration = date(2026, 6, 19)
        result = s.build_orders([candidate])
        order = result.orders[0]
        self.assertEqual(order.short_put_occ, "SPY260619P00565000")
        self.assertEqual(order.long_put_occ, "SPY260619P00560000")

    def test_two_legs_returned(self):
        s = PutCreditSpreadStrategy(StrategyConfig())
        candidate = make_candidate()
        order = s.build_orders([candidate]).orders[0]
        legs = order.to_legs()
        self.assertEqual(len(legs), 2)
        # First leg should be SELL_TO_OPEN (short), second BUY_TO_OPEN (long)
        self.assertEqual(legs[0].side.value, "sell_to_open")
        self.assertEqual(legs[1].side.value, "buy_to_open")

    def test_width_taken_from_candidate(self):
        """Spread width is derived from the strikes the screener picked."""
        s = PutCreditSpreadStrategy(StrategyConfig())
        candidate = make_candidate(short_strike=100, long_strike=95)
        order = s.build_orders([candidate]).orders[0]
        self.assertEqual(order.spread_width, 5.0)


class TestCreditFloor(unittest.TestCase):
    def test_below_floor_dropped(self):
        s = PutCreditSpreadStrategy(StrategyConfig(min_credit_dollars=0.50))
        # Credit at mid = 0.30, target = 0.30 * 0.95 = 0.285 < 0.50 floor
        candidate = make_candidate(short_mid=0.50, long_mid=0.20)
        result = s.build_orders([candidate])
        self.assertEqual(len(result.orders), 0)
        self.assertEqual(result.dropped_low_credit, 1)

    def test_above_floor_kept(self):
        s = PutCreditSpreadStrategy(StrategyConfig(min_credit_dollars=0.20))
        candidate = make_candidate(short_mid=1.20, long_mid=0.40)
        result = s.build_orders([candidate])
        self.assertEqual(len(result.orders), 1)


class TestIdempotency(unittest.TestCase):
    def test_existing_fingerprint_skipped(self):
        s = PutCreditSpreadStrategy(StrategyConfig())
        candidate = make_candidate(symbol="AAPL", short_strike=180, long_strike=175)
        candidate.target_expiration = date(2026, 6, 19)
        existing = make_fingerprint("AAPL", date(2026, 6, 19), 180.0, 175.0)
        result = s.build_orders([candidate], already_open_fingerprints={existing})
        self.assertEqual(len(result.orders), 0)
        self.assertEqual(result.skipped_existing, 1)

    def test_different_fingerprint_not_skipped(self):
        s = PutCreditSpreadStrategy(StrategyConfig())
        candidate = make_candidate(symbol="AAPL", short_strike=180, long_strike=175)
        candidate.target_expiration = date(2026, 6, 19)
        # Open position is on different strikes — should NOT skip
        existing = make_fingerprint("AAPL", date(2026, 6, 19), 175.0, 170.0)
        result = s.build_orders([candidate], already_open_fingerprints={existing})
        self.assertEqual(len(result.orders), 1)


class TestFingerprintStability(unittest.TestCase):
    def test_same_inputs_same_fingerprint(self):
        f1 = make_fingerprint("SPY", date(2026, 6, 19), 565.0, 560.0)
        f2 = make_fingerprint("SPY", date(2026, 6, 19), 565.0, 560.0)
        self.assertEqual(f1, f2)

    def test_case_insensitive_underlying(self):
        f1 = make_fingerprint("spy", date(2026, 6, 19), 565.0, 560.0)
        f2 = make_fingerprint("SPY", date(2026, 6, 19), 565.0, 560.0)
        self.assertEqual(f1, f2)

    def test_strike_precision(self):
        # 565.0 and 565.001 should be different fingerprints
        f1 = make_fingerprint("SPY", date(2026, 6, 19), 565.0, 560.0)
        f2 = make_fingerprint("SPY", date(2026, 6, 19), 565.001, 560.0)
        self.assertNotEqual(f1, f2)


if __name__ == "__main__":
    unittest.main()
