"""
Screener unit tests with a mocked Tradier client. No network access required.
"""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from data.universe import UniverseSnapshot, UniverseTicker
from screener import Screener, ScreenerConfig


# ─── Test helpers ────────────────────────────────────────────────────────────


def make_put_option(strike: float, delta: float, bid: float, ask: float,
                     mid_iv: float = 0.30, open_interest: int = 500) -> dict:
    """Build a Tradier-shaped option dict for a put."""
    return {
        "symbol": f"SPY260620P{int(strike*1000):08d}",
        "strike": strike,
        "option_type": "put",
        "bid": bid,
        "ask": ask,
        "last": (bid + ask) / 2,
        "volume": 100,
        "open_interest": open_interest,
        "greeks": {
            "delta": -delta,  # puts have negative delta
            "gamma": 0.01,
            "theta": -0.05,
            "vega": 0.20,
            "mid_iv": mid_iv,
        },
    }


def make_complete_chain(spot: float = 100.0, base_iv: float = 0.30) -> list[dict]:
    """Make a chain of puts spanning roughly 0.05 to 0.95 delta."""
    chain = []
    # 20 strikes from spot-30% to spot+10%, in $5 increments
    strikes = [round(spot - 30 + i * 5, 1) for i in range(15)]
    for strike in strikes:
        # Crude delta approximation: far OTM puts have small delta, ITM puts large
        moneyness = strike / spot
        if moneyness < 0.7:
            delta = 0.05
        elif moneyness < 0.8:
            delta = 0.10
        elif moneyness < 0.85:
            delta = 0.15
        elif moneyness < 0.9:
            delta = 0.20  # our target zone
        elif moneyness < 0.95:
            delta = 0.30
        elif moneyness < 1.0:
            delta = 0.45
        elif moneyness < 1.05:
            delta = 0.55
        else:
            delta = 0.80
        # Intrinsic + small extrinsic
        intrinsic = max(0, strike - spot)
        extrinsic = max(0.05, base_iv * spot * 0.08 * (1 - abs(0.5 - delta)))
        mid = intrinsic + extrinsic
        bid = mid * 0.97
        ask = mid * 1.03
        chain.append(make_put_option(strike, delta, bid, ask, mid_iv=base_iv))
    return chain


def make_universe(symbols: list[str]) -> UniverseSnapshot:
    return UniverseSnapshot(
        build_timestamp_utc="2026-05-19T00:00:00+00:00",
        config={},
        count=len(symbols),
        tickers=[
            UniverseTicker(
                symbol=s,
                name=s,
                exchange="NASDAQ",
                last_price=100.0,
                market_cap=10e9,
                avg_volume_30d=1e6,
                is_etf=False,
            )
            for s in symbols
        ],
    )


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestPickTargetExpiration(unittest.TestCase):
    def _screener(self, **overrides) -> Screener:
        config = ScreenerConfig(
            apply_earnings_filter=False, apply_atm_iv_filter=False, **overrides
        )
        return Screener(config, MagicMock(), None)

    def test_picks_closest_to_target_dte(self):
        s = self._screener(min_dte=25, max_dte=50, target_dte=35)
        today = date(2026, 5, 18)
        # DTE = 21 (out), 30, 35, 40, 55 (out)
        expirations = [
            today + timedelta(days=21),
            today + timedelta(days=30),
            today + timedelta(days=35),
            today + timedelta(days=40),
            today + timedelta(days=55),
        ]
        result = s._pick_target_expiration(expirations, today)
        self.assertEqual(result, today + timedelta(days=35))

    def test_returns_none_when_none_in_window(self):
        s = self._screener()
        today = date(2026, 5, 18)
        expirations = [
            today + timedelta(days=7),
            today + timedelta(days=14),
            today + timedelta(days=90),
        ]
        result = s._pick_target_expiration(expirations, today)
        self.assertIsNone(result)

    def test_empty_expirations_returns_none(self):
        s = self._screener()
        result = s._pick_target_expiration([], date(2026, 5, 18))
        self.assertIsNone(result)


class TestFindTargetDeltaPut(unittest.TestCase):
    def _screener(self) -> Screener:
        return Screener(
            ScreenerConfig(apply_earnings_filter=False, apply_atm_iv_filter=False),
            MagicMock(),
            None,
        )

    def test_finds_closest_to_target(self):
        s = self._screener()
        puts = [
            make_put_option(80, 0.05, 0.10, 0.20),
            make_put_option(85, 0.15, 0.50, 0.60),
            make_put_option(90, 0.20, 1.00, 1.10),  # exact target
            make_put_option(95, 0.35, 2.00, 2.20),
        ]
        opt, dist = s._find_target_delta_put(puts, 0.20)
        self.assertEqual(opt["strike"], 90)
        self.assertAlmostEqual(dist, 0.0)

    def test_skips_options_without_greeks(self):
        s = self._screener()
        puts = [
            {"strike": 90, "greeks": {}},  # no delta
            make_put_option(85, 0.20, 0.5, 0.6),
        ]
        opt, _ = s._find_target_delta_put(puts, 0.20)
        self.assertEqual(opt["strike"], 85)

    def test_returns_none_when_no_greeks_anywhere(self):
        s = self._screener()
        puts = [{"strike": 90, "greeks": {}}]
        opt, dist = s._find_target_delta_put(puts, 0.20)
        self.assertIsNone(opt)
        self.assertEqual(dist, float("inf"))


class TestFindStrike(unittest.TestCase):
    def _screener(self) -> Screener:
        return Screener(
            ScreenerConfig(apply_earnings_filter=False, apply_atm_iv_filter=False),
            MagicMock(),
            None,
        )

    def test_finds_exact_strike(self):
        s = self._screener()
        puts = [
            make_put_option(85, 0.10, 0.5, 0.6),
            make_put_option(90, 0.20, 1.0, 1.1),
            make_put_option(95, 0.35, 2.0, 2.2),
        ]
        opt = s._find_strike(puts, 90.0, tolerance=0.51)
        self.assertEqual(opt["strike"], 90)

    def test_within_tolerance(self):
        s = self._screener()
        puts = [make_put_option(89.5, 0.15, 0.5, 0.6)]
        opt = s._find_strike(puts, 90.0, tolerance=0.51)
        self.assertEqual(opt["strike"], 89.5)

    def test_outside_tolerance_returns_none(self):
        s = self._screener()
        puts = [make_put_option(88.0, 0.10, 0.3, 0.4)]
        opt = s._find_strike(puts, 90.0, tolerance=0.5)
        self.assertIsNone(opt)


class TestFullScreenPipeline(unittest.TestCase):
    """End-to-end test of the per-ticker pipeline with mocked Tradier responses."""

    def setUp(self):
        self.today = date.today()
        self.target_exp = self.today + timedelta(days=35)

        self.mock_tradier = MagicMock()
        self.mock_tradier.get_option_expirations.return_value = [
            self.today + timedelta(days=14),
            self.target_exp,
            self.today + timedelta(days=60),
        ]
        self.mock_tradier.get_option_chain.return_value = make_complete_chain(
            spot=100.0, base_iv=0.30
        )

        self.config = ScreenerConfig(
            apply_earnings_filter=False,
            apply_atm_iv_filter=False,
            min_short_put_open_interest=0,  # tighten in dedicated test
            max_bid_ask_pct=1.0,            # tighten in dedicated test
        )
        self.screener = Screener(self.config, self.mock_tradier, None)
        self.universe = make_universe(["SPY"])

    def test_basic_candidate_produced(self):
        result = self.screener.screen(self.universe)
        self.assertEqual(result.stats.input, 1)
        self.assertEqual(result.stats.passed, 1)
        self.assertEqual(len(result.candidates), 1)
        c = result.candidates[0]
        self.assertEqual(c.symbol, "SPY")
        self.assertEqual(c.target_expiration, self.target_exp)
        self.assertAlmostEqual(c.short_put_delta, 0.20, places=1)
        self.assertEqual(c.long_put_strike, c.short_put_strike - 5.0)
        self.assertGreater(c.spread_credit_mid, 0)
        self.assertGreater(c.spread_max_loss, 0)

    def test_drops_when_no_expiration_in_window(self):
        self.mock_tradier.get_option_expirations.return_value = [
            self.today + timedelta(days=7),
            self.today + timedelta(days=100),
        ]
        result = self.screener.screen(self.universe)
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.no_expiration_in_dte, 1)

    def test_drops_when_chain_empty(self):
        self.mock_tradier.get_option_chain.return_value = []
        result = self.screener.screen(self.universe)
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.chain_empty, 1)

    def test_drops_when_bid_ask_too_wide(self):
        # Build a chain where the 20-delta put has a 30% wide bid-ask
        wide_chain = []
        for opt in make_complete_chain(100, 0.30):
            d = abs(opt["greeks"]["delta"])
            if 0.18 <= d <= 0.22:
                mid = (opt["bid"] + opt["ask"]) / 2
                opt["bid"] = mid * 0.80
                opt["ask"] = mid * 1.20
            wide_chain.append(opt)
        self.mock_tradier.get_option_chain.return_value = wide_chain
        config = ScreenerConfig(
            apply_earnings_filter=False, apply_atm_iv_filter=False,
            max_bid_ask_pct=0.10, min_short_put_open_interest=0,
        )
        screener = Screener(config, self.mock_tradier, None)
        result = screener.screen(self.universe)
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.bid_ask_too_wide, 1)

    def test_drops_when_low_open_interest(self):
        chain = []
        for opt in make_complete_chain(100, 0.30):
            d = abs(opt["greeks"]["delta"])
            if 0.18 <= d <= 0.22:
                opt["open_interest"] = 10  # below threshold
            chain.append(opt)
        self.mock_tradier.get_option_chain.return_value = chain
        config = ScreenerConfig(
            apply_earnings_filter=False, apply_atm_iv_filter=False,
            min_short_put_open_interest=100, max_bid_ask_pct=1.0,
        )
        screener = Screener(config, self.mock_tradier, None)
        result = screener.screen(self.universe)
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.low_open_interest, 1)

    def test_drops_when_atm_iv_too_low(self):
        # Build a chain with low ATM IV (0.10)
        self.mock_tradier.get_option_chain.return_value = make_complete_chain(
            100, 0.10
        )
        config = ScreenerConfig(
            apply_earnings_filter=False,
            apply_atm_iv_filter=True,
            min_atm_iv=0.25,
            min_short_put_open_interest=0, max_bid_ask_pct=1.0,
        )
        screener = Screener(config, self.mock_tradier, None)
        result = screener.screen(self.universe)
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.atm_iv_too_low, 1)

    def test_api_error_counted_not_crashed(self):
        from broker import TradierError
        self.mock_tradier.get_option_expirations.side_effect = TradierError("boom")
        result = self.screener.screen(self.universe)
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.api_error, 1)


class TestEarningsFilter(unittest.TestCase):
    def test_drops_when_earnings_in_window(self):
        today = date.today()
        target_exp = today + timedelta(days=35)

        mock_tradier = MagicMock()
        mock_tradier.get_option_expirations.return_value = [target_exp]
        mock_tradier.get_option_chain.return_value = make_complete_chain(100, 0.30)

        mock_earnings = MagicMock()
        # Earnings 10 days from now — inside the window
        mock_earnings.get_next_earnings.return_value = today + timedelta(days=10)

        config = ScreenerConfig(
            apply_earnings_filter=True, apply_atm_iv_filter=False,
            min_short_put_open_interest=0, max_bid_ask_pct=1.0,
        )
        screener = Screener(config, mock_tradier, mock_earnings)
        result = screener.screen(make_universe(["AAPL"]))
        self.assertEqual(result.stats.passed, 0)
        self.assertEqual(result.stats.has_earnings_in_window, 1)

    def test_passes_when_earnings_outside_window(self):
        today = date.today()
        target_exp = today + timedelta(days=35)

        mock_tradier = MagicMock()
        mock_tradier.get_option_expirations.return_value = [target_exp]
        mock_tradier.get_option_chain.return_value = make_complete_chain(100, 0.30)

        mock_earnings = MagicMock()
        # Earnings 90 days from now — well outside the window
        mock_earnings.get_next_earnings.return_value = today + timedelta(days=90)

        config = ScreenerConfig(
            apply_earnings_filter=True, apply_atm_iv_filter=False,
            min_short_put_open_interest=0, max_bid_ask_pct=1.0,
        )
        screener = Screener(config, mock_tradier, mock_earnings)
        result = screener.screen(make_universe(["AAPL"]))
        self.assertEqual(result.stats.passed, 1)

    def test_passes_when_earnings_unknown(self):
        today = date.today()
        target_exp = today + timedelta(days=35)

        mock_tradier = MagicMock()
        mock_tradier.get_option_expirations.return_value = [target_exp]
        mock_tradier.get_option_chain.return_value = make_complete_chain(100, 0.30)

        mock_earnings = MagicMock()
        mock_earnings.get_next_earnings.return_value = None  # unknown

        config = ScreenerConfig(
            apply_earnings_filter=True, apply_atm_iv_filter=False,
            min_short_put_open_interest=0, max_bid_ask_pct=1.0,
        )
        screener = Screener(config, mock_tradier, mock_earnings)
        result = screener.screen(make_universe(["AAPL"]))
        # Unknown earnings == let through (conservative default)
        self.assertEqual(result.stats.passed, 1)


class TestSorting(unittest.TestCase):
    """Candidates should sort by ATM IV descending."""

    def test_sorted_by_atm_iv_desc(self):
        today = date.today()
        target_exp = today + timedelta(days=35)

        mock_tradier = MagicMock()
        mock_tradier.get_option_expirations.return_value = [target_exp]

        # Three different IV levels
        chains = {
            "LOW": make_complete_chain(100, 0.20),
            "MID": make_complete_chain(100, 0.35),
            "HIGH": make_complete_chain(100, 0.50),
        }
        def chain_side_effect(symbol, exp, with_greeks):
            return chains[symbol]
        mock_tradier.get_option_chain.side_effect = chain_side_effect

        config = ScreenerConfig(
            apply_earnings_filter=False, apply_atm_iv_filter=False,
            min_short_put_open_interest=0, max_bid_ask_pct=1.0,
        )
        screener = Screener(config, mock_tradier, None)
        result = screener.screen(make_universe(["LOW", "MID", "HIGH"]))
        self.assertEqual(len(result.candidates), 3)
        symbols_in_order = [c.symbol for c in result.candidates]
        self.assertEqual(symbols_in_order, ["HIGH", "MID", "LOW"])


class TestConfigValidation(unittest.TestCase):
    def test_earnings_filter_on_requires_calendar(self):
        config = ScreenerConfig(apply_earnings_filter=True)
        with self.assertRaises(ValueError):
            Screener(config, MagicMock(), None)


if __name__ == "__main__":
    unittest.main()
