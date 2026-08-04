"""
C4 — the self-improvement loop was wired to nothing and reviewed an empty table.

`store.update_returns`, `prices.benchmark_return`, `config.BENCHMARKS` and
`config.TRACK_HORIZONS_DAYS` were all implemented and nothing called any of them,
so `ret_7`/`ret_30`/`ret_90` stayed NULL forever. The only guard on the review
was a ROW count, which the rows satisfied and the values did not — so the review
always ran, always found nothing, and always reported success.

Every test here fails against the pre-C4 code:
  * `update_track_returns` did not exist;
  * `review_readiness` did not exist and `run_review` had no guard;
  * `store.track_rows_needing` / `track_coverage` did not exist.

    cd screener && python -m unittest tests.test_track_loop -v
"""
import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import config as C
import prices
import pipeline
from store import Store


def _series(start, n, step=0.01, start_px=100.0):
    """n business-day bars compounding at `step`/bar from `start`."""
    days = pd.bdate_range(start, periods=n)
    px = [start_px * (1 + step) ** i for i in range(n)]
    return pd.DataFrame({"Date": [d.strftime("%Y-%m-%d") for d in days],
                         "Close": px, "Volume": [1e6] * n})


class ForwardReturnFrom(unittest.TestCase):
    def test_exact_session_arithmetic(self):
        df = _series("2024-01-01", 60, step=0.01)
        v, s = prices.forward_return_from("X", date(2024, 1, 1), 30, df=df)
        self.assertEqual(s, "ok")
        self.assertAlmostEqual(v, 1.01 ** 30 - 1, places=9)

    def test_horizon_not_yet_closed_is_not_a_zero(self):
        """
        The distinction that matters most. A horizon that has not elapsed must
        come back as NOT_CLOSED so the row stays NULL and is retried, never as
        0.0 — a flat return written into the track record is a fabricated
        observation.
        """
        recent = date.today() - timedelta(days=5)
        df = _series(recent - timedelta(days=10), 12)
        v, s = prices.forward_return_from("X", recent, 30, df=df)
        self.assertEqual(s, prices.NOT_CLOSED)
        self.assertIsNone(v)

    def test_delisted_freezes_the_last_observed_return(self):
        """A name that stops printing must freeze, not vanish. Dropping the
        losers that delisted is exactly how a track record lies."""
        df = _series("2020-01-01", 20, step=-0.05)     # long dead by today
        v, s = prices.forward_return_from("X", date(2020, 1, 1), 90,
                                          grace_sessions=C.DELISTING_GRACE_DAYS, df=df)
        self.assertEqual(s, prices.DELISTED)
        self.assertLess(v, 0.0)

    def test_no_history_is_reported_not_guessed(self):
        v, s = prices.forward_return_from("X", date(2024, 1, 1), 30,
                                          df=pd.DataFrame({"Date": [], "Close": []}))
        self.assertEqual(s, prices.NO_DATA)
        self.assertIsNone(v)


class TrackingLoopFillsTheTable(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.run_date = date(2021, 1, 4)
        for i in range(50):
            self.store.log_track(self.run_date, f"T{i:02d}", 100.0)
        self.hist = _series("2020-12-01", 400, step=0.001)

    def _prices(self, _symbol):
        return self.hist

    def test_returns_are_null_before_the_loop_runs(self):
        """The pre-C4 state, asserted so the fix has something to be a fix OF."""
        cov = self.store.track_coverage()
        self.assertEqual(cov["rows"], 50)
        self.assertEqual(cov["ret_30"], 0)

    def test_loop_fills_every_horizon(self):
        pipeline.update_track_returns(self.store, today=date(2026, 1, 1),
                                      get_prices=self._prices, verbose=False)
        cov = self.store.track_coverage()
        for h in C.TRACK_HORIZONS_DAYS:
            self.assertEqual(cov[f"ret_{h}"], 50, f"ret_{h} not filled")

    def test_benchmarks_are_logged_at_the_30_session_horizon(self):
        pipeline.update_track_returns(self.store, today=date(2026, 1, 1),
                                      get_prices=self._prices, verbose=False)
        row = self.store.db.execute(
            "SELECT ret_30, bench_iwm_30, bench_ijr_30 FROM track_record "
            "WHERE ticker='T00'").fetchone()
        self.assertIsNotNone(row[0])
        self.assertIsNotNone(row[1], "IWM benchmark return not logged")
        self.assertIsNotNone(row[2], "IJR benchmark return not logged")

    def test_benchmark_is_measured_from_the_run_date_not_from_today(self):
        """
        `prices.benchmark_return(symbol, days)` measures the LAST `days`
        sessions — i.e. from today. Comparing a pick's 2021 forward return
        against the benchmark's return over the most recent 30 sessions is not
        a comparison. The loop must anchor both at the run date.
        """
        pipeline.update_track_returns(self.store, today=date(2026, 1, 1),
                                      get_prices=self._prices, verbose=False)
        row = self.store.db.execute(
            "SELECT ret_30, bench_iwm_30 FROM track_record WHERE ticker='T00'").fetchone()
        # Same synthetic series for pick and benchmark, same anchor => identical.
        self.assertAlmostEqual(row[0], row[1], places=9)

    def test_rerunning_is_idempotent(self):
        first = pipeline.update_track_returns(self.store, today=date(2026, 1, 1),
                                              get_prices=self._prices, verbose=False)
        second = pipeline.update_track_returns(self.store, today=date(2026, 1, 1),
                                               get_prices=self._prices, verbose=False)
        self.assertGreater(first["filled"], 0)
        self.assertEqual(second["filled"], 0, "a second pass must touch nothing")


class ReviewGuard(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def _log(self, n, filled=0):
        for i in range(n):
            self.store.log_track(date(2021, 1, 4), f"T{i:03d}", 100.0)
        for i in range(filled):
            self.store.update_returns(date(2021, 1, 4), f"T{i:03d}", ret_30=0.01)

    def test_all_null_table_is_refused(self):
        """The exact pre-C4 failure: rows exist, values do not, review runs."""
        self._log(500, filled=0)
        ok, reasons, cov = pipeline.review_readiness(self.store)
        self.assertFalse(ok)
        self.assertEqual(cov["ret_30"], 0)
        self.assertTrue(any("realized" in r for r in reasons))

    def test_row_count_alone_does_not_pass(self):
        """
        500 rows is far past any plausible row-count threshold and 10 realized
        returns is far below the sample floor. A row count cannot tell them
        apart; this guard must.
        """
        self._log(500, filled=10)
        ok, _reasons, _ = pipeline.review_readiness(self.store)
        self.assertFalse(ok)

    def test_low_fill_rate_is_refused_even_with_a_big_sample(self):
        """A loop that stopped filling must fail the review, not quietly shrink
        the sample. 60 filled clears SELF_REVIEW_MIN_SAMPLE=40 but is only 12%
        of the table."""
        self._log(500, filled=60)
        ok, reasons, _ = pipeline.review_readiness(self.store)
        self.assertFalse(ok)
        self.assertTrue(any("not filling" in r for r in reasons))

    def test_a_healthy_table_passes(self):
        self._log(100, filled=100)
        ok, reasons, _ = pipeline.review_readiness(self.store)
        self.assertTrue(ok, reasons)

    def test_thresholds_come_from_config(self):
        self.assertGreaterEqual(C.SELF_REVIEW_MIN_SAMPLE, 1)
        self.assertGreater(C.MIN_TRACK_RETURN_COVERAGE, 0.0)
        self.assertLessEqual(C.MIN_TRACK_RETURN_COVERAGE, 1.0)


class StoreHelpers(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.store.log_track(date(2021, 1, 4), "AAA", 10.0)
        self.store.log_track(date(2021, 1, 4), "BBB", 20.0)

    def test_rows_needing_shrinks_as_they_are_filled(self):
        self.assertEqual(len(self.store.track_rows_needing("ret_30")), 2)
        self.store.update_returns(date(2021, 1, 4), "AAA", ret_30=0.05)
        self.assertEqual(len(self.store.track_rows_needing("ret_30")), 1)

    def test_update_returns_accepts_an_iso_string_run_date(self):
        """track_rows_needing hands back the stored string; the writer must take it."""
        rd, tkr, _ = self.store.track_rows_needing("ret_7")[0]
        self.assertIsInstance(rd, str)
        self.store.update_returns(rd, tkr, ret_7=0.02)
        self.assertEqual(self.store.track_coverage()["ret_7"], 1)

    def test_column_names_are_validated(self):
        with self.assertRaises(ValueError):
            self.store.track_rows_needing("ret_30; DROP TABLE track_record")
        with self.assertRaises(ValueError):
            self.store.update_returns(date(2021, 1, 4), "AAA", **{"a=1;--": 1})

    def test_delisted_flag_is_set(self):
        self.store.mark_delisted(date(2021, 1, 4), "AAA")
        row = self.store.db.execute(
            "SELECT delisted FROM track_record WHERE ticker='AAA'").fetchone()
        self.assertEqual(row[0], 1)


if __name__ == "__main__":
    unittest.main()
