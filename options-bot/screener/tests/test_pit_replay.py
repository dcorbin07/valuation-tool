"""
C1 — the point-in-time guarantees the live-model replay rests on.

Making `scoring.score_stock` replayable historically is only worth anything if
the inputs it is fed were genuinely knowable on the date they are fed for. Two
of them are easy to get wrong and silent when you do:

  * INSIDER. The live pipeline takes "the six most recent Form 4s". Replayed,
    that must mean "the six most recent filed ON OR BEFORE the rebalance date".
    Off-by-one here does not crash, does not change coverage, and hands the
    model tomorrow's insider buying.
  * LIQUIDITY. `prices.get_quote` computes average dollar volume off the TAIL of
    the series — as of today. Correct for a daily screener; in a 2021 backtest
    it is four years of look-ahead in the gate that decides universe membership.

    cd screener && python -m unittest tests.test_pit_replay -v
"""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import panel_cache as PC
import pit_data


class InsiderIsPointInTime(unittest.TestCase):
    """
    Drives `insider_asof` against a stubbed index/document store, so it tests the
    as-of logic rather than the network.
    """

    def setUp(self):
        self._idx, self._txns = PC.form4_index, PC.form4_txns
        self.index = [
            {"filed": "2024-06-01", "url": "u6"},
            {"filed": "2024-05-01", "url": "u5"},
            {"filed": "2024-04-01", "url": "u4"},
            {"filed": "2024-03-01", "url": "u3"},
            {"filed": "2024-02-01", "url": "u2"},
            {"filed": "2024-01-01", "url": "u1"},
            {"filed": "2023-12-01", "url": "u0"},
        ]
        PC.form4_index = lambda t: (self.index if t != "EMPTY" else [])
        PC.form4_txns = lambda url: [{"code": "P", "role": "CEO",
                                      "value_usd": 100_000.0, "person": url,
                                      "date": url}]

    def tearDown(self):
        PC.form4_index, PC.form4_txns = self._idx, self._txns

    def _urls(self, as_of, limit=6):
        return [t["person"] for t in PC.insider_asof("X", as_of, limit)]

    def test_nothing_filed_after_the_as_of_date_is_used(self):
        got = self._urls(date(2024, 3, 15))
        self.assertNotIn("u4", got)
        self.assertNotIn("u5", got)
        self.assertNotIn("u6", got)
        self.assertEqual(got, ["u3", "u2", "u1", "u0"])

    def test_a_filing_on_the_as_of_date_itself_counts(self):
        """
        Form 4s are due within two business days and are public on filing, so a
        filing dated the rebalance date was knowable. Excluding it would be
        conservative but wrong; including a LATER one would be look-ahead.
        """
        self.assertIn("u3", self._urls(date(2024, 3, 1)))
        self.assertNotIn("u4", self._urls(date(2024, 3, 1)))

    def test_limit_takes_the_most_recent_not_the_oldest(self):
        got = self._urls(date(2024, 6, 30), limit=3)
        self.assertEqual(got, ["u6", "u5", "u4"])

    def test_no_form4_history_at_all_is_none_not_empty(self):
        """
        `scoring.insider_score` treats None as 'not fetched' and renormalizes it
        away, and [] as a real 'no qualifying activity' observation scoring a
        neutral 50. Collapsing the two would score a filer we know nothing about
        as if we had looked and found nothing.
        """
        self.assertIsNone(PC.insider_asof("EMPTY", date(2024, 6, 1)))

    def test_a_filer_with_history_but_none_yet_is_empty_not_none(self):
        self.assertEqual(PC.insider_asof("X", date(2023, 1, 1)), [])

    def test_the_window_actually_moves_with_the_date(self):
        """A replay that returns the same six filings on every rebalance date
        would look fine and be a constant."""
        early = set(self._urls(date(2024, 2, 15)))
        late = set(self._urls(date(2024, 6, 15)))
        self.assertNotEqual(early, late)


class LiquidityIsPointInTime(unittest.TestCase):
    def setUp(self):
        days = pd.bdate_range("2020-01-01", periods=400)
        # Volume steps up 100x in the second half: if the gate is reading the
        # tail of the series, an early date will show the LATE volume.
        vol = np.array([1e4] * 200 + [1e6] * 200, dtype=float)
        self.df = pd.DataFrame({"Date": [d.strftime("%Y-%m-%d") for d in days],
                                "Close": [10.0] * 400, "Volume": vol})
        self.dates, self.closes = pit_data._price_arrays(self.df)
        self.volumes = pit_data._volume_array(self.df)

    def test_early_date_sees_early_volume(self):
        adv = pit_data.avg_dollar_volume(self.dates, self.closes, self.volumes,
                                         pd.Timestamp("2020-06-01"))
        self.assertAlmostEqual(adv, 10.0 * 1e4, delta=1.0,
                               msg="the liquidity gate is reading future volume")

    def test_late_date_sees_late_volume(self):
        adv = pit_data.avg_dollar_volume(self.dates, self.closes, self.volumes,
                                         pd.Timestamp("2021-06-01"))
        self.assertAlmostEqual(adv, 10.0 * 1e6, delta=1.0)

    def test_missing_volume_column_is_none_not_zero(self):
        """None renormalizes away; 0.0 would fail the liquidity gate and delete
        the name from the universe for a reason that is not about the name."""
        self.assertIsNone(pit_data._volume_array(pd.DataFrame({"Date": [], "Close": []})))
        self.assertIsNone(pit_data.avg_dollar_volume(self.dates, self.closes, None,
                                                     pd.Timestamp("2020-06-01")))


class PanelCarriesBothModelsInputs(unittest.TestCase):
    """
    C1's central claim is that the two models are scored on ONE feed. If the
    panel stops carrying the live model's raw line items, the live path silently
    degrades (every name loses coverage and drops out) rather than failing.
    """

    def test_point_in_time_factors_emits_the_live_scorers_field_names(self):
        facts = {"facts": {"us-gaap": {
            "Revenues": {"units": {"USD": [
                {"start": "2022-01-01", "end": "2022-12-31", "val": 800.0,
                 "filed": "2023-02-01", "fp": "FY", "form": "10-K"},
                {"start": "2021-01-01", "end": "2021-12-31", "val": 600.0,
                 "filed": "2023-02-01", "fp": "FY", "form": "10-K"},
                {"start": "2020-01-01", "end": "2020-12-31", "val": 500.0,
                 "filed": "2023-02-01", "fp": "FY", "form": "10-K"},
            ]}},
            "NetIncomeLoss": {"units": {"USD": [
                {"start": "2022-01-01", "end": "2022-12-31", "val": 80.0,
                 "filed": "2023-02-01", "fp": "FY", "form": "10-K"}]}},
            "OperatingIncomeLoss": {"units": {"USD": [
                {"start": "2022-01-01", "end": "2022-12-31", "val": 100.0,
                 "filed": "2023-02-01", "fp": "FY", "form": "10-K"}]}},
            "StockholdersEquity": {"units": {"USD": [
                {"end": "2022-12-31", "val": 400.0, "filed": "2023-02-01"}]}},
            "CommonStockSharesOutstanding": {"units": {"shares": [
                {"end": "2022-12-31", "val": 10.0, "filed": "2023-02-01"}]}},
        }}}
        f = pit_data.point_in_time_factors(facts, 50.0, "2023-06-01")
        for k in ("net_income", "operating_income", "total_debt", "cash",
                  "op_margin", "net_debt_to_ebitda", "latest_rev_growth",
                  "prior_rev_growth", "market_cap", "revenue"):
            self.assertIn(k, f, f"the live scorer's input `{k}` is not emitted")
        self.assertAlmostEqual(f["op_margin"], 100.0 / 800.0)
        self.assertAlmostEqual(f["op_margin"], f["opm"],
                               msg="op_margin and opm must be the same number")
        self.assertAlmostEqual(f["latest_rev_growth"], 800.0 / 600.0 - 1)
        self.assertAlmostEqual(f["prior_rev_growth"], 600.0 / 500.0 - 1,
                               msg="a third revenue year is needed for growth "
                                   "acceleration; with two it silently scores "
                                   "on level alone")
        self.assertAlmostEqual(f["market_cap"], 500.0)

    def test_nothing_filed_after_the_as_of_date_reaches_the_factors(self):
        facts = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
            {"start": "2022-01-01", "end": "2022-12-31", "val": 80.0,
             "filed": "2099-01-01", "fp": "FY", "form": "10-K"}]}}}}}
        f = pit_data.point_in_time_factors(facts, 50.0, "2023-06-01")
        self.assertIsNone(f["net_income"],
                          "a datapoint filed in the future was used")


if __name__ == "__main__":
    unittest.main()
