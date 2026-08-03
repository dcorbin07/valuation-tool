"""
Tests for OCC option symbol construction. No API access required — these run
purely on local logic. Run with:

    python -m pytest tests/

or:

    python -m unittest tests.test_occ_symbol
"""
import unittest
from datetime import date

from broker.occ_symbol import (
    OptionContract,
    OptionType,
    build_occ_symbol,
    parse_occ_symbol,
)


class TestBuildOCCSymbol(unittest.TestCase):
    def test_basic_call(self):
        sym = build_occ_symbol("AAPL", date(2025, 10, 17), OptionType.CALL, 255.0)
        self.assertEqual(sym, "AAPL251017C00255000")

    def test_basic_put(self):
        sym = build_occ_symbol("SPY", date(2025, 6, 20), OptionType.PUT, 565.0)
        self.assertEqual(sym, "SPY250620P00565000")

    def test_fractional_strike_half_dollar(self):
        sym = build_occ_symbol("SPY", date(2025, 6, 20), OptionType.PUT, 565.50)
        self.assertEqual(sym, "SPY250620P00565500")

    def test_fractional_strike_quarter_dollar(self):
        sym = build_occ_symbol("F", date(2025, 1, 17), OptionType.CALL, 12.25)
        self.assertEqual(sym, "F250117C00012250")

    def test_low_strike_under_one_dollar(self):
        sym = build_occ_symbol("ABC", date(2025, 1, 17), OptionType.CALL, 0.50)
        self.assertEqual(sym, "ABC250117C00000500")

    def test_high_strike_four_digit(self):
        sym = build_occ_symbol("BRK", date(2025, 1, 17), OptionType.CALL, 5000.0)
        self.assertEqual(sym, "BRK250117C05000000")

    def test_underlying_lowercased_input(self):
        sym = build_occ_symbol("spy", date(2025, 6, 20), OptionType.PUT, 565.0)
        self.assertEqual(sym, "SPY250620P00565000")

    def test_single_digit_month_day_padding(self):
        sym = build_occ_symbol("AAPL", date(2025, 1, 3), OptionType.CALL, 100.0)
        # Jan 3, 2025 -> 250103
        self.assertEqual(sym, "AAPL250103C00100000")


class TestBuildOCCSymbolErrors(unittest.TestCase):
    def test_empty_underlying_raises(self):
        with self.assertRaises(ValueError):
            build_occ_symbol("", date(2025, 10, 17), OptionType.CALL, 100)

    def test_zero_strike_raises(self):
        with self.assertRaises(ValueError):
            build_occ_symbol("AAPL", date(2025, 10, 17), OptionType.CALL, 0)

    def test_negative_strike_raises(self):
        with self.assertRaises(ValueError):
            build_occ_symbol("AAPL", date(2025, 10, 17), OptionType.CALL, -1)

    def test_strike_too_high_raises(self):
        with self.assertRaises(ValueError):
            build_occ_symbol(
                "BRK", date(2025, 10, 17), OptionType.CALL, 100_000.0
            )

    def test_expiration_too_old_raises(self):
        with self.assertRaises(ValueError):
            build_occ_symbol(
                "AAPL", date(1999, 10, 17), OptionType.CALL, 100
            )


class TestParseOCCSymbol(unittest.TestCase):
    def test_parse_basic_call(self):
        c = parse_occ_symbol("AAPL251017C00255000")
        self.assertEqual(c.underlying, "AAPL")
        self.assertEqual(c.expiration, date(2025, 10, 17))
        self.assertEqual(c.option_type, OptionType.CALL)
        self.assertAlmostEqual(c.strike, 255.0)

    def test_parse_basic_put(self):
        c = parse_occ_symbol("SPY250620P00565000")
        self.assertEqual(c.underlying, "SPY")
        self.assertEqual(c.expiration, date(2025, 6, 20))
        self.assertEqual(c.option_type, OptionType.PUT)
        self.assertAlmostEqual(c.strike, 565.0)

    def test_parse_fractional_strike(self):
        c = parse_occ_symbol("SPY250620P00565500")
        self.assertAlmostEqual(c.strike, 565.50)

    def test_parse_single_letter_underlying(self):
        c = parse_occ_symbol("F250117C00012250")
        self.assertEqual(c.underlying, "F")
        self.assertAlmostEqual(c.strike, 12.25)


class TestParseOCCSymbolErrors(unittest.TestCase):
    def test_too_short_raises(self):
        with self.assertRaises(ValueError):
            parse_occ_symbol("ABC")

    def test_invalid_type_char_raises(self):
        # X is not a valid option type
        with self.assertRaises(ValueError):
            parse_occ_symbol("AAPL251017X00255000")

    def test_invalid_date_raises(self):
        # Month 13 isn't a real month
        with self.assertRaises(ValueError):
            parse_occ_symbol("AAPL251317C00255000")


class TestRoundTrip(unittest.TestCase):
    """Building then parsing should give the original components back."""

    cases = [
        ("AAPL", date(2025, 10, 17), OptionType.CALL, 255.0),
        ("SPY", date(2026, 1, 16), OptionType.PUT, 565.50),
        ("F", date(2025, 1, 17), OptionType.CALL, 12.25),
        ("BRK", date(2030, 12, 31), OptionType.CALL, 5000.0),
        ("ABC", date(2025, 6, 20), OptionType.PUT, 0.50),
    ]

    def test_round_trip_all_cases(self):
        for underlying, exp, otype, strike in self.cases:
            with self.subTest(symbol=f"{underlying} {exp} {otype.name} ${strike}"):
                sym = build_occ_symbol(underlying, exp, otype, strike)
                parsed = parse_occ_symbol(sym)
                self.assertEqual(parsed.underlying, underlying)
                self.assertEqual(parsed.expiration, exp)
                self.assertEqual(parsed.option_type, otype)
                self.assertAlmostEqual(parsed.strike, strike, places=3)


if __name__ == "__main__":
    unittest.main()
