"""
Unit tests for the universe builder's parsing and filtering logic.

These tests don't hit the network. The Tradier enrichment step is exercised
via the smoke test in scripts/test_universe.py instead.
"""
import unittest
from unittest.mock import MagicMock

from data.universe import (
    LIQUID_ETF_WHITELIST,
    UniverseBuilder,
    UniverseConfig,
    UniverseTicker,
    parse_market_cap,
    parse_price,
)


class TestParsePrice(unittest.TestCase):
    def test_plain_number(self):
        self.assertEqual(parse_price(123.45), 123.45)

    def test_int(self):
        self.assertEqual(parse_price(100), 100.0)

    def test_dollar_string(self):
        self.assertEqual(parse_price("$123.45"), 123.45)

    def test_dollar_string_with_commas(self):
        self.assertEqual(parse_price("$1,234.56"), 1234.56)

    def test_string_no_dollar(self):
        self.assertEqual(parse_price("99.99"), 99.99)

    def test_empty_string_returns_zero(self):
        self.assertEqual(parse_price(""), 0.0)

    def test_garbage_returns_zero(self):
        self.assertEqual(parse_price("N/A"), 0.0)

    def test_none_returns_zero(self):
        self.assertEqual(parse_price(None), 0.0)


class TestParseMarketCap(unittest.TestCase):
    def test_billion_string(self):
        self.assertAlmostEqual(parse_market_cap("1.23B"), 1.23e9)

    def test_million_string(self):
        self.assertAlmostEqual(parse_market_cap("456M"), 456e6)

    def test_thousand_string(self):
        self.assertAlmostEqual(parse_market_cap("789K"), 789e3)

    def test_number(self):
        self.assertAlmostEqual(parse_market_cap(2_000_000_000), 2e9)

    def test_string_no_suffix(self):
        self.assertAlmostEqual(parse_market_cap("2500000000"), 2.5e9)

    def test_with_commas(self):
        self.assertAlmostEqual(parse_market_cap("2,500,000,000"), 2.5e9)

    def test_empty_returns_zero(self):
        self.assertEqual(parse_market_cap(""), 0.0)

    def test_none_returns_zero(self):
        self.assertEqual(parse_market_cap(None), 0.0)


class TestBaselineFilters(unittest.TestCase):
    """The _apply_baseline_filters step takes raw Nasdaq rows -> tickers."""

    def _make_builder(self, **config_kwargs) -> UniverseBuilder:
        config = UniverseConfig(**config_kwargs)
        mock_tradier = MagicMock()
        return UniverseBuilder(config=config, tradier=mock_tradier)

    def test_basic_pass(self):
        builder = self._make_builder(min_price=10, min_market_cap=1e9)
        rows = [{
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "lastsale": "$185.50",
            "marketCap": "2.85T",  # T-suffix not handled; will parse as 0
            # Use B for testability:
            "marketCap": "2850B",
        }]
        result = list(builder._apply_baseline_filters(rows))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].symbol, "AAPL")
        self.assertEqual(result[0].last_price, 185.50)

    def test_price_too_low_filtered(self):
        builder = self._make_builder(min_price=20.0, min_market_cap=1e9)
        rows = [{
            "symbol": "PENNY",
            "lastsale": "$5.00",
            "marketCap": "2B",
        }]
        result = list(builder._apply_baseline_filters(rows))
        self.assertEqual(len(result), 0)

    def test_market_cap_too_low_filtered(self):
        builder = self._make_builder(min_price=10, min_market_cap=2e9)
        rows = [{
            "symbol": "SMALL",
            "lastsale": "$50.00",
            "marketCap": "500M",
        }]
        result = list(builder._apply_baseline_filters(rows))
        self.assertEqual(len(result), 0)

    def test_dedup_same_symbol(self):
        builder = self._make_builder(min_price=10, min_market_cap=1e9)
        rows = [
            {"symbol": "AAPL", "lastsale": "$185", "marketCap": "3000B"},
            {"symbol": "AAPL", "lastsale": "$186", "marketCap": "3000B"},
        ]
        result = list(builder._apply_baseline_filters(rows))
        self.assertEqual(len(result), 1)

    def test_skips_warrants_and_units(self):
        """Symbols with dots, slashes, etc. are typically warrants/units/preferreds."""
        builder = self._make_builder(min_price=10, min_market_cap=1e9)
        rows = [
            {"symbol": "BRK.A", "lastsale": "$500000", "marketCap": "700B"},
            {"symbol": "ABC.W", "lastsale": "$50", "marketCap": "10B"},
            {"symbol": "ABC^P", "lastsale": "$50", "marketCap": "10B"},
            {"symbol": "PLAIN", "lastsale": "$50", "marketCap": "10B"},
        ]
        result = list(builder._apply_baseline_filters(rows))
        symbols = [t.symbol for t in result]
        self.assertEqual(symbols, ["PLAIN"])

    def test_missing_symbol_skipped(self):
        builder = self._make_builder(min_price=10, min_market_cap=1e9)
        rows = [
            {"symbol": "", "lastsale": "$50", "marketCap": "10B"},
            {"lastsale": "$50", "marketCap": "10B"},  # no symbol key
            {"symbol": "VALID", "lastsale": "$50", "marketCap": "10B"},
        ]
        result = list(builder._apply_baseline_filters(rows))
        self.assertEqual([t.symbol for t in result], ["VALID"])

    def test_symbol_uppercased(self):
        builder = self._make_builder(min_price=10, min_market_cap=1e9)
        rows = [{"symbol": "aapl", "lastsale": "$185", "marketCap": "3000B"}]
        result = list(builder._apply_baseline_filters(rows))
        self.assertEqual(result[0].symbol, "AAPL")


class TestETFWhitelist(unittest.TestCase):
    def test_includes_major_indices(self):
        for sym in ["SPY", "QQQ", "IWM", "DIA"]:
            self.assertIn(sym, LIQUID_ETF_WHITELIST)

    def test_includes_sector_spdrs(self):
        for sym in ["XLF", "XLE", "XLK", "XLV"]:
            self.assertIn(sym, LIQUID_ETF_WHITELIST)

    def test_no_duplicates(self):
        self.assertEqual(len(LIQUID_ETF_WHITELIST), len(set(LIQUID_ETF_WHITELIST)))

    def test_all_uppercase(self):
        for sym in LIQUID_ETF_WHITELIST:
            self.assertEqual(sym, sym.upper())


class TestSnapshotRoundTrip(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        from pathlib import Path
        import tempfile
        from data.universe import UniverseSnapshot

        snapshot = UniverseSnapshot(
            build_timestamp_utc="2026-05-19T01:42:00+00:00",
            config={"min_price": 20.0},
            count=2,
            tickers=[
                UniverseTicker(
                    symbol="SPY",
                    name="SPDR S&P 500",
                    exchange="NYSE",
                    last_price=712.45,
                    market_cap=530e9,
                    avg_volume_30d=65e6,
                    is_etf=True,
                ),
                UniverseTicker(
                    symbol="AAPL",
                    name="Apple Inc.",
                    exchange="NASDAQ",
                    last_price=185.50,
                    market_cap=2850e9,
                    avg_volume_30d=55e6,
                    is_etf=False,
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universe.json"
            mock_tradier = MagicMock()
            builder = UniverseBuilder(UniverseConfig(), mock_tradier)
            builder.save(snapshot, path)

            loaded = UniverseBuilder.load(path)
            self.assertEqual(loaded.count, 2)
            self.assertEqual(loaded.tickers[0].symbol, "SPY")
            self.assertTrue(loaded.tickers[0].is_etf)
            self.assertEqual(loaded.tickers[1].symbol, "AAPL")
            self.assertFalse(loaded.tickers[1].is_etf)


if __name__ == "__main__":
    unittest.main()
