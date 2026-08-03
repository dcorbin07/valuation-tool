"""Tests for the trend-following instrument basket (T2)."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from trend import (
    AssetClass,
    by_asset_class,
    get_basket,
    get_symbols,
    lookup,
)


class TestBasket(unittest.TestCase):
    def test_basket_nonempty_and_reasonable_size(self):
        basket = get_basket()
        # Trend-following sweet spot is ~25-35 instruments
        self.assertGreaterEqual(len(basket), 20)
        self.assertLessEqual(len(basket), 40)

    def test_all_four_core_asset_classes_present(self):
        classes = {i.asset_class for i in get_basket()}
        for required in (AssetClass.EQUITY, AssetClass.BOND,
                         AssetClass.COMMODITY, AssetClass.CURRENCY):
            self.assertIn(required, classes)

    def test_no_duplicate_symbols(self):
        symbols = get_symbols()
        self.assertEqual(len(symbols), len(set(symbols)))

    def test_symbols_are_uppercase(self):
        for s in get_symbols():
            self.assertEqual(s, s.upper())

    def test_cross_asset_diversification(self):
        # Each core class should have at least 3 instruments for real diversification
        grouped = by_asset_class()
        for cls in (AssetClass.EQUITY, AssetClass.BOND, AssetClass.COMMODITY):
            self.assertGreaterEqual(len(grouped[cls]), 3,
                                    f"{cls} has too few instruments")

    def test_lookup_works(self):
        spy = lookup("spy")  # case-insensitive
        self.assertIsNotNone(spy)
        self.assertEqual(spy.symbol, "SPY")
        self.assertEqual(spy.asset_class, AssetClass.EQUITY)

    def test_lookup_missing_returns_none(self):
        self.assertIsNone(lookup("NOTREAL"))

    def test_core_equity_indices_present(self):
        symbols = set(get_symbols())
        # The essentials a trend basket should not omit
        for essential in ("SPY", "QQQ", "TLT", "GLD"):
            self.assertIn(essential, symbols)


if __name__ == "__main__":
    unittest.main()
