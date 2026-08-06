"""
Tests for the Sharadar adapter and the point-in-time universe.

No network, no API key — everything runs against a synthetic sqlite mirror.

The tests that matter most are the LOOK-AHEAD ones. A backtest that leaks
future data doesn't crash; it produces a beautiful equity curve that is
worthless, and there is no symptom to notice. So the leaks have to be caught
by construction, and asserted on.
"""
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.pit_universe import PITUniverseBuilder, PITUniverseConfig
from core.sharadar import (
    AsOfHistory, SharadarClient, SharadarError, SharadarHistory, SharadarStore,
)


def _days(n, start=date(2020, 1, 1)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


class _Mirror(unittest.TestCase):
    """Builds a small synthetic Sharadar mirror once per test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.days = _days(300)
        self.store = SharadarStore(Path(self.tmp.name) / "s.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    # C5. Sharadar's DAILY.marketcap is denominated in MILLIONS of USD, and this
    # fixture writes straight into the `daily` table, so `cap` in every spec
    # below is a DOLLAR figure that gets divided by this before insertion.
    #
    # It used to be inserted raw, i.e. the synthetic mirror spoke DOLLARS while
    # the real feed speaks MILLIONS. That single mismatch is why this suite
    # passed on a module that returned an EMPTY universe on every real date from
    # 2000 to 2026 — a fixture cannot disagree with you about what the feed
    # means, and this one silently agreed with the bug. Specs stay in dollars
    # because that is what the assertions and the config thresholds are written
    # in; the conversion happens here, once, in the same direction the real
    # loader converts.
    MARKETCAP_UNITS_PER_USD = 1e6

    def _load(self, specs, wobble=0.0):
        """
        specs: {ticker: (first_idx, last_idx, price, cap_in_DOLLARS, category, volume)}

        `wobble` adds a deterministic zig-zag to the price path. Filter tests
        want flat prices so the level assertions are exact; the strategy
        integration tests need SOME variation, because a constant series has
        zero volatility and every signal generator marks a zero-vol name as
        unusable (correctly — you cannot inverse-vol weight it).
        """
        sep, tick, dly = [], [], []
        for t, (a, b, px0, cap, cat, vol) in specs.items():
            for i, d in enumerate(self.days[a:b + 1]):
                px = px0 * (1.0 + wobble * ((i % 7) - 3) / 3.0) if wobble else px0
                sep.append({"ticker": t, "date": d.isoformat(), "open": px, "high": px,
                            "low": px, "close": px, "volume": vol,
                            "closeadj": px * 1.10,     # dividends added back
                            "closeunadj": px * 4.0,    # pretend a later 4:1 split
                            "lastupdated": d.isoformat()})
                cap_millions = cap / self.MARKETCAP_UNITS_PER_USD
                dly.append({"ticker": t, "date": d.isoformat(),
                            "marketcap": cap_millions, "ev": cap_millions})
            tick.append({"table": "SEP", "ticker": t, "permaticker": t + "P", "name": t,
                         "exchange": "NASDAQ",
                         "isdelisted": "N" if b == len(self.days) - 1 else "Y",
                         "category": cat, "sector": "Tech",
                         "firstpricedate": self.days[a].isoformat(),
                         "lastpricedate": self.days[b].isoformat()})
        self.store.ingest_sep(sep)
        self.store.ingest_tickers(tick)
        self.store.ingest_daily(dly)


class TestSurvivorship(_Mirror):
    """The property the whole subscription exists for."""

    def setUp(self):
        super().setUp()
        last = len(self.days) - 1
        self._load({
            "LIVES": (0, last, 50.0, 5e9, "Domestic Common Stock", 1e6),
            "DIES":  (0, 150,  50.0, 5e9, "Domestic Common Stock", 1e6),
            "IPOS":  (200, last, 50.0, 5e9, "Domestic Common Stock", 1e6),
        })
        self.b = PITUniverseBuilder(self.store, PITUniverseConfig(min_market_cap=1e9))

    def test_a_company_that_later_died_is_in_its_own_era(self):
        syms = self.b.build(self.days[100]).symbols()
        self.assertIn("DIES", syms,
                      "a company alive on this date is missing — that IS survivorship bias")

    def test_it_is_gone_after_delisting(self):
        self.assertNotIn("DIES", self.b.build(self.days[200]).symbols())

    def test_a_company_that_had_not_listed_yet_is_absent(self):
        self.assertNotIn("IPOS", self.b.build(self.days[100]).symbols(),
                         "a not-yet-listed company leaked into an earlier universe")

    def test_it_appears_once_listed(self):
        self.assertIn("IPOS", self.b.build(self.days[250]).symbols())

    def test_delisted_names_are_counted_not_hidden(self):
        snap = self.b.build(self.days[100])
        self.assertEqual(snap.delisted_included, 1)

    def test_survivorship_report_quantifies_the_gap(self):
        rep = self.b.survivorship_report(self.days[100])
        self.assertEqual(rep["delisted_since"], 1)
        self.assertGreater(rep["pct_invisible_to_a_live_screener"], 0)


class TestUniverseFilters(_Mirror):
    def setUp(self):
        super().setUp()
        last = len(self.days) - 1
        self._load({
            "GOOD":    (0, last, 50.0, 5e9, "Domestic Common Stock", 1e6),
            "PENNY":   (0, last, 3.0,  5e9, "Domestic Common Stock", 1e6),
            "TINY":    (0, last, 50.0, 1e8, "Domestic Common Stock", 1e6),
            "ILLIQUID":(0, last, 50.0, 5e9, "Domestic Common Stock", 1e3),
            "SPAC":    (0, last, 50.0, 5e9, "Blank Checks", 1e6),
            "ADR":     (0, last, 50.0, 5e9, "ADR Common Stock", 1e6),
            "PREF":    (0, last, 50.0, 5e9, "Domestic Preferred", 1e6),
        })

    def _syms(self, **kw):
        cfg = PITUniverseConfig(min_price=20.0, min_market_cap=2e9,
                                min_avg_volume=500_000, **kw)
        return PITUniverseBuilder(self.store, cfg).build(self.days[-1]).symbols()

    def test_keeps_only_the_qualifying_name(self):
        self.assertEqual(self._syms(), ["GOOD"])

    def test_adrs_can_be_opted_in(self):
        self.assertCountEqual(self._syms(include_adrs=True), ["GOOD", "ADR"])

    def test_rejection_reasons_are_reported(self):
        cfg = PITUniverseConfig(min_price=20.0, min_market_cap=2e9, min_avg_volume=500_000)
        snap = PITUniverseBuilder(self.store, cfg).build(self.days[-1])
        self.assertEqual(snap.rejected["price"], 1)      # PENNY
        self.assertEqual(snap.rejected["cap"], 1)        # TINY
        self.assertEqual(snap.rejected["volume"], 1)     # ILLIQUID
        self.assertEqual(snap.rejected["category"], 3)   # SPAC, ADR, PREF

    def test_price_screen_uses_UNADJUSTED_price(self):
        """
        closeadj is back-adjusted, so a stock that later split 4:1 looks like it
        traded at a quarter of its real price. Screening 'over $20' on adjusted
        prices silently excludes names that genuinely qualified at the time.
        Fixture: close=50, closeunadj=200. A $100 floor must still admit it.
        """
        cfg = PITUniverseConfig(min_price=100.0, min_market_cap=2e9, min_avg_volume=500_000)
        self.assertIn("GOOD", PITUniverseBuilder(self.store, cfg)
                      .build(self.days[-1]).symbols())


class TestAdjustmentSemantics(_Mirror):
    def setUp(self):
        super().setUp()
        self._load({"AAA": (0, len(self.days) - 1, 50.0, 5e9, "Domestic Common Stock", 1e6)})

    def test_closes_default_to_the_total_return_series(self):
        c = self.store.closes("AAA", self.days[0], self.days[-1])
        self.assertAlmostEqual(c[0][1], 55.0)      # closeadj = 50 * 1.10

    def test_unadjusted_is_available_for_price_levels(self):
        c = self.store.closes("AAA", self.days[0], self.days[-1], adjusted=False)
        self.assertAlmostEqual(c[0][1], 200.0)     # closeunadj

    def test_price_on_defaults_to_unadjusted(self):
        """A price LEVEL question must not be answered with a back-adjusted series."""
        self.assertAlmostEqual(self.store.price_on("AAA", self.days[50]), 200.0)


class TestLookAheadIsStructurallyBlocked(_Mirror):
    def setUp(self):
        super().setUp()
        self._load({"AAA": (0, len(self.days) - 1, 50.0, 5e9, "Domestic Common Stock", 1e6)})

    def test_as_of_history_cannot_return_the_future(self):
        ao = AsOfHistory(self.store, as_of=self.days[100])
        bars = ao.get_history("AAA", self.days[0], self.days[-1])   # asks for everything
        self.assertLessEqual(max(b["date"] for b in bars), self.days[100].isoformat())

    def test_as_of_quotes_cannot_return_the_future(self):
        ao = AsOfHistory(self.store, as_of=self.days[100])
        self.assertTrue(ao.get_quotes(["AAA"]))

    def test_mr_dimensions_are_refused(self):
        """
        MR* is restated with hindsight AND sets datekey to the period end.
        Two independent look-ahead traps, so it must be impossible to ask for
        by accident rather than merely discouraged in a docstring.
        """
        for dim in ("MRQ", "MRY", "MRT"):
            with self.assertRaises(SharadarError):
                self.store.pit_fundamental("AAA", self.days[100], dimension=dim)

    def test_pit_fundamental_takes_the_earliest_datekey(self):
        """
        If Sharadar appends a row on restatement, the LATEST datekey for a
        reportperiod is the restated figure — knowable only with hindsight.
        Taking the earliest returns what was actually filed at the time.
        """
        import json
        rows = [
            # Same reportperiod, filed twice: original then restatement.
            ("AAA", "ARQ", "2020-03-31", "2020-04-20", "2020-03-31",
             json.dumps({"netinc": 100, "note": "as originally filed"})),
            ("AAA", "ARQ", "2020-03-31", "2020-11-15", "2020-03-31",
             json.dumps({"netinc": 60, "note": "restated later"})),
        ]
        self.store.db.executemany(
            "INSERT INTO sf1 (ticker,dimension,calendardate,datekey,reportperiod,payload) "
            "VALUES (?,?,?,?,?,?)", rows)
        self.store.db.commit()
        got = self.store.pit_fundamental("AAA", date(2021, 1, 1), dimension="ARQ")
        self.assertEqual(got["netinc"], 100,
                         "returned the RESTATED figure — that is look-ahead bias")

    def test_a_filing_is_not_knowable_on_its_own_filing_date(self):
        """
        datekey is a bare date. A filing accepted at 16:30 ET was not tradable
        at that day's close, so the comparison must be strict.
        """
        import json
        self.store.db.execute(
            "INSERT INTO sf1 (ticker,dimension,calendardate,datekey,reportperiod,payload) "
            "VALUES (?,?,?,?,?,?)",
            ("AAA", "ARQ", "2020-03-31", "2020-04-20", "2020-03-31", json.dumps({"x": 1})))
        self.store.db.commit()
        self.assertIsNone(self.store.pit_fundamental("AAA", date(2020, 4, 20), "ARQ"))
        self.assertIsNotNone(self.store.pit_fundamental("AAA", date(2020, 4, 21), "ARQ"))


class TestDropsIntoExistingStrategyCode(_Mirror):
    """
    The whole design bet: every signal generator holds an UNTYPED `self.tradier`
    and calls one method on it. If that holds, Sharadar swaps in with no change
    to any strategy code at all.
    """

    def setUp(self):
        super().setUp()
        last = len(self.days) - 1
        self._load({f"T{i}": (0, last, 50.0 + i * 5, 5e9, "Domestic Common Stock", 1e6)
                    for i in range(8)}, wobble=0.03)

    def test_momentum_generator_runs_unchanged(self):
        from momentum.signals import MomentumConfig, MomentumSignalGenerator
        gen = MomentumSignalGenerator(
            MomentumConfig(min_bars_required=60, lookback_days=60,
                           long_count=2, short_count=2),
            SharadarHistory(self.store))
        sel = gen.generate([f"T{i}" for i in range(8)], today=self.days[-1])
        self.assertTrue(sel.longs)
        self.assertTrue(sel.all_prices)
        self.assertTrue(sel.recent_returns, "return panel is empty — vol targeting "
                                            "would silently fall back")

    def test_reversion_generator_runs_unchanged(self):
        from reversion.signals import MeanReversionConfig, MeanReversionSignalGenerator
        gen = MeanReversionSignalGenerator(
            MeanReversionConfig(min_bars_required=60, long_count=2, short_count=2),
            SharadarHistory(self.store))
        sel = gen.generate([f"T{i}" for i in range(8)], today=self.days[-1])
        self.assertIsNotNone(sel)

    def test_get_history_matches_the_tradier_shape(self):
        bars = SharadarHistory(self.store).get_history("T0", self.days[0], self.days[10])
        self.assertTrue(bars)
        self.assertEqual(set(bars[0]), {"date", "close"})
        self.assertIsInstance(bars[0]["date"], str)
        self.assertIsInstance(bars[0]["close"], float)

    def test_intraday_intervals_are_refused_rather_than_faked(self):
        with self.assertRaises(SharadarError):
            SharadarHistory(self.store).get_history(
                "T0", self.days[0], self.days[10], interval="1min")


class TestClientEncoding(unittest.TestCase):
    def test_filter_encoding(self):
        e = SharadarClient._encode
        self.assertIn("ticker=AAPL", e({"ticker": "AAPL"}))
        self.assertIn("ticker=AAPL%2CMSFT", e({"ticker": ["AAPL", "MSFT"]}))
        self.assertIn("date.gte=2024-01-01", e({"date": {"gte": "2024-01-01"}}))

    def test_missing_key_is_an_explicit_error(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"NASDAQ_DATA_LINK_API_KEY": ""}, clear=True):
            with self.assertRaises(SharadarError):
                SharadarClient()


if __name__ == "__main__":
    unittest.main()
