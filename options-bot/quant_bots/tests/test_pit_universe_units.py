"""
C5 — the units bug that made the point-in-time universe EMPTY on every date.

`core/pit_universe.py` had only ever been exercised against a synthetic 30-name
mirror. On real Sharadar data it returned a universe of ZERO names on all 27
tested dates from 2000 to 2026, because:

    Sharadar's DAILY.marketcap is denominated in MILLIONS of USD.
    PITUniverseConfig.min_market_cap is written in DOLLARS (2_000_000_000).

So AAPL on 2015-06-30 presented as 722,571.4 against a threshold of
2,000,000,000 and failed the cap gate — as did every other company that has ever
listed. Measured before the fix: 5,945 names listed on 2015-06-30, universe size
0. Cross-check: 722,571.4 x 1e6 = $722.57B, matching the project's own recorded
"AAPL 2015Q2 $722.6B verified".

A synthetic fixture cannot catch this. Its author picks the units, and naturally
picks the ones the code expects. That is precisely what C5 exists to test.

    python -m unittest tests.test_pit_universe_units -v
"""
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pit_universe import PITUniverseBuilder, PITUniverseConfig
from core.sharadar import SharadarStore

# AAPL's real market cap on 2015-06-30, as Sharadar stores it (millions) and as
# the rest of this codebase means it (dollars).
AAPL_CAP_SHARADAR_MILLIONS = 722_571.4
AAPL_CAP_USD = 722_571_400_000.0


class _Mirror:
    """A two-name mirror carrying values in the units the REAL feed uses."""

    def __init__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = SharadarStore(Path(self.dir.name) / "t.db")
        self.store.ingest_tickers([
            {"table": "SEP", "ticker": "AAPL", "permaticker": "1", "name": "APPLE",
             "exchange": "NASDAQ", "isdelisted": "N",
             "category": "Domestic Common Stock", "currency": "USD",
             "firstpricedate": "1990-01-01", "lastpricedate": "2026-07-31"},
            {"table": "SEP", "ticker": "GONE", "permaticker": "2", "name": "DEAD CO",
             "exchange": "NYSE", "isdelisted": "Y",
             "category": "Domestic Common Stock", "currency": "USD",
             "firstpricedate": "1990-01-01", "lastpricedate": "2016-01-04"},
        ])
        sep, daily = [], []
        for day in range(1, 29):
            d = f"2015-06-{day:02d}"
            for t, px, cap in (("AAPL", 125.425, AAPL_CAP_SHARADAR_MILLIONS),
                               ("GONE", 42.0, 9_000.0)):
                sep.append({"ticker": t, "date": d, "open": px, "high": px,
                            "low": px, "close": px, "volume": 5_000_000.0,
                            "closeadj": px, "closeunadj": px,
                            "lastupdated": d})
                daily.append({"ticker": t, "date": d, "marketcap": cap})
        self.store.ingest_sep(sep)
        self.store.ingest_daily(daily)

    def close(self):
        self.store.close()
        self.dir.cleanup()


class MarketCapUnits(unittest.TestCase):
    def setUp(self):
        self.m = _Mirror()

    def tearDown(self):
        self.m.close()

    def test_store_returns_dollars_not_millions(self):
        got = self.m.store.marketcap_on("AAPL", date(2015, 6, 28))
        self.assertAlmostEqual(got, AAPL_CAP_USD, delta=1e6)
        self.assertGreater(got, 1e11,
                           "a mega-cap must not present as a six-figure number")

    def test_the_dollar_threshold_now_admits_a_mega_cap(self):
        """The exact comparison that failed: 722,571.4 vs 2,000,000,000."""
        cfg = PITUniverseConfig()
        self.assertGreaterEqual(
            self.m.store.marketcap_on("AAPL", date(2015, 6, 28)),
            cfg.min_market_cap,
            "AAPL fails a $2B cap floor — the units regression is back")

    def test_universe_is_not_empty(self):
        snap = PITUniverseBuilder(self.m.store, PITUniverseConfig()).build(
            date(2015, 6, 28))
        self.assertGreater(snap.count, 0,
                           "the point-in-time universe is empty, which is what "
                           "the units bug looked like on real data")
        self.assertIn("AAPL", snap.symbols())

    def test_a_genuinely_small_name_is_still_rejected(self):
        """
        The fix must not simply admit everything. GONE is $9.0B in Sharadar's
        units, i.e. $9bn — above the $2B floor. Raise the floor past it and it
        must drop out, proving the comparison is still doing work.
        """
        cfg = PITUniverseConfig(min_market_cap=20_000_000_000.0)
        snap = PITUniverseBuilder(self.m.store, cfg).build(date(2015, 6, 28))
        self.assertIn("AAPL", snap.symbols())
        self.assertNotIn("GONE", snap.symbols())

    def test_delisted_names_are_included_in_a_historical_universe(self):
        """The module's entire purpose. GONE stopped trading in 2016 and must
        still appear in a 2015 universe."""
        snap = PITUniverseBuilder(self.m.store, PITUniverseConfig()).build(
            date(2015, 6, 28))
        self.assertIn("GONE", snap.symbols())
        self.assertGreater(snap.delisted_included, 0)

    def test_a_name_is_absent_after_it_stops_trading(self):
        snap = PITUniverseBuilder(self.m.store, PITUniverseConfig()).build(
            date(2020, 6, 30))
        self.assertNotIn("GONE", snap.symbols())

    def test_the_conversion_constant_is_named_not_inline(self):
        self.assertEqual(SharadarStore.MARKETCAP_UNITS_PER_USD, 1e6)

    def test_missing_marketcap_is_none_not_zero(self):
        """None renormalizes away; 0.0 would silently fail every cap floor and
        look exactly like the bug being fixed."""
        self.assertIsNone(self.m.store.marketcap_on("NOSUCH", date(2015, 6, 28)))


class AntiCheat(unittest.TestCase):
    """
    scalemarketcap / scalerevenue are MAX-OVER-LIFETIME buckets: a company that
    became a mega-cap in 2024 is labelled mega-cap in 2005. Filtering a
    "point-in-time" universe on them leaks look-ahead into the very thing being
    validated. The schema must not even carry them.
    """

    def test_lookahead_columns_are_absent_from_the_schema(self):
        with tempfile.TemporaryDirectory() as d:
            store = SharadarStore(Path(d) / "t.db")
            cols = {r[1] for r in store.db.execute("PRAGMA table_info(tickers)")}
            self.assertNotIn("scalemarketcap", cols)
            self.assertNotIn("scalerevenue", cols)
            store.close()


if __name__ == "__main__":
    unittest.main()
