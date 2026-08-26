"""The point-in-time dollar-ADV instrument (B13 / S7-4).

Every test pins a defect that was MEASURED during the build, not one imagined afterwards. The
two that matter most are the CRSP negative-price convention and the date-scoped join: both fail
SILENTLY and both fail hardest on exactly the illiquid names a liquidity screen is about.
"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import pandas as pd  # noqa: E402

from valuation.edge import adv as ADV  # noqa: E402


class NegativePriceConvention(unittest.TestCase):
    """CRSP stores a bid/ask MIDPOINT as a NEGATIVE price when the close did not trade --
    28,283 rows = 0.404% of the panel's daily frame. A naive `prc * vol` goes negative on
    precisely the least liquid rows, and a negative ADV sits below every floor, so the filter
    would appear to work while working for the wrong reason."""

    def test_a_negative_price_still_yields_a_positive_dollar_volume(self):
        got = ADV.dollar_volume([-12.5], [1000])
        self.assertAlmostEqual(float(got[0]), 12500.0)

    def test_it_matches_the_positive_case_exactly(self):
        a = ADV.dollar_volume([12.5], [1000])
        b = ADV.dollar_volume([-12.5], [1000])
        self.assertAlmostEqual(float(a[0]), float(b[0]))

    def test_the_share_is_reported_rather_than_absorbed(self):
        d = pd.DataFrame({"prc": [10.0, -2.0, 3.0, -4.0], "vol": [1, 1, 1, 1]})
        r = ADV.negative_price_share(d)
        self.assertEqual(r["negative_price_rows"], 2)
        self.assertEqual(r["pct"], 50.0)


class TheJoinIsDateScoped(unittest.TestCase):
    """1,053 of 2,271 matched tickers map to more than one permno. A ticker is a lease, not an
    identity -- S3-I5's problem in a third table, after the option chains and the IBES actuals."""

    def setUp(self):
        # one ticker, two companies: permno 111 until 2015, permno 222 after 2018
        self.sn = pd.DataFrame({
            "ticker": ["XYZ", "XYZ", "XYZ"],
            "permno": [111, 111, 222],
            "namedt": ["2000-01-01", "2010-01-01", "2018-06-01"],
            "nameenddt": ["2009-12-31", "2015-12-31", "2024-12-31"]})
        self.iv = ADV.ticker_permno_intervals(self.sn)

    def test_the_permno_depends_on_the_date(self):
        self.assertEqual(ADV.permno_on(self.iv, "XYZ", "2012-05-05"), 111)
        self.assertEqual(ADV.permno_on(self.iv, "XYZ", "2020-05-05"), 222)

    def test_a_date_in_the_gap_resolves_to_nothing_rather_than_to_the_nearest(self):
        """Between 2016 and mid-2018 the ticker belonged to neither. Snapping to the nearest
        holder is how one company's volume is attributed to another."""
        self.assertIsNone(ADV.permno_on(self.iv, "XYZ", "2017-01-01"))

    def test_adjacent_rows_with_the_same_permno_merge_into_one_interval(self):
        """CRSP splits a row on ANY name or exchange edit, so an unmerged history has many
        intervals per identity."""
        self.assertEqual(len(self.iv["XYZ"]), 2)

    def test_the_last_interval_is_open_ended(self):
        """CRSP's own last date is 2024-12-31 on this account. Left closed there, every 2025
        observation would fall outside every interval -- the vendor's cut masquerading as a
        coverage gap."""
        self.assertEqual(self.iv["XYZ"][-1][2], ADV.OPEN_END)
        self.assertEqual(ADV.permno_on(self.iv, "XYZ", "2030-01-01"), 222)

    def test_an_unknown_ticker_resolves_to_nothing(self):
        self.assertIsNone(ADV.permno_on(self.iv, "NOPE", "2020-01-01"))


class TheWindowIsPointInTime(unittest.TestCase):
    def setUp(self):
        n = 200
        self.d = pd.DataFrame({
            "permno": [1] * n,
            "date": pd.date_range("2020-01-01", periods=n, freq="B"),
            "prc": [10.0] * n,
            "vol": list(range(1, n + 1))})

    def test_the_window_ends_on_the_PRIOR_session(self):
        """A liquidity screen applied when selecting on date D may not read D's own tape: the
        panel's other point-in-time rules are strictly-before, and volume is the series most
        correlated with the day's news."""
        s = ADV.adv_series(self.d, window=5, min_sessions=5)
        row = s[s["date"] == self.d["date"].iloc[10]]
        # sessions 6..10 are volumes 6..10 -> mean 8, times price 10
        self.assertAlmostEqual(float(row["adv"].iloc[0]), 80.0)

    def test_a_short_history_yields_no_adv_rather_than_a_small_one(self):
        """A name with four sessions has an 'average' that is not one, and admitting it lets a
        barely-traded name clear a floor on noise."""
        s = ADV.adv_series(self.d.head(3), window=60, min_sessions=20)
        self.assertEqual(len(s), 0)

    def test_the_DEFAULT_refuses_a_short_history(self):
        """FOUND BY MUTATION, NOT BY READING: the test above passes `min_sessions` explicitly,
        so it kept passing against a module whose DEFAULT had been dropped to 1 -- and the
        default is what every real caller gets. A guard that only holds when the caller restates
        it is not a guard."""
        s = ADV.adv_series(self.d.head(8))
        self.assertEqual(len(s), 0)
        self.assertGreaterEqual(ADV.MIN_SESSIONS, 20)

    def test_the_default_admits_a_long_enough_history(self):
        """The positive control, so the rule above is pinned rather than merely made strict."""
        s = ADV.adv_series(self.d)
        self.assertGreater(len(s), 0)

    def test_the_shipped_window_is_the_live_screens_own(self):
        """MIN_AVG_DOLLAR_VOLUME is calibrated against `prices.py`'s ~60-session mean. Choosing a
        different window here silently re-scales the threshold."""
        self.assertEqual(ADV.ADV_WINDOW_SESSIONS, 60)
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "valuation", "screener", "prices.py"), encoding="utf-8").read()
        self.assertIn("min(60, n)", src,
                      "the live screen's ADV window moved; the panel instrument now measures a "
                      "different quantity from the constant it shares")


class MissingIsNotZero(unittest.TestCase):
    def test_coverage_error_exists_and_is_an_exception(self):
        """A zero ADV is BELOW every floor, so a missing measure returned as zero converts
        'we cannot see this name' into 'this name is illiquid, drop it' -- a survivorship filter
        wearing a liquidity filter's name (S10's defect)."""
        self.assertTrue(issubclass(ADV.CoverageError, Exception))

    def test_coverage_is_measured_on_the_population_asked_about(self):
        have = {("A", "2020-01-01"): 1.0}
        cells = [("A", "2020-01-01"), ("B", "2020-01-01"), ("C", "2020-01-01")]
        c = ADV.coverage(have, cells)
        self.assertEqual(c["cells"], 3)
        self.assertEqual(c["with_adv"], 1)
        self.assertEqual(c["without_adv"], 2)
        self.assertAlmostEqual(c["pct"], 33.33, places=1)


class TheCutIsRecorded(unittest.TestCase):
    def test_the_crsp_cut_is_a_named_constant(self):
        """Five of the panel's 69 rebalance dates fall after it -- 8.22% of rows. A reader must
        be able to see the boundary without re-deriving it."""
        self.assertEqual(ADV.CRSP_CUT, dt.date(2024, 12, 31))


if __name__ == "__main__":
    unittest.main(verbosity=2)
