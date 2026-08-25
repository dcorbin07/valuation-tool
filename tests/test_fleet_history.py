"""(D) THE RECORDERS — the four history-starved books, and the clocks that had not started.

**NO AMOUNT OF CODING PRODUCES A SERIES RETROACTIVELY.** This is the one blocker family where
waiting is strictly more expensive than acting, so these pin the properties that make a series
worth having when it is finally long enough to read.

  * **APPEND-ONLY AND IDEMPOTENT PER DATE.** A cycle can legitimately run twice in a day (a
    retry, a manual dispatch) and must not double-record; a series whose past can be rewritten
    is not evidence.
  * **A MISSING NAME IS MISSING, NEVER ZERO AND NEVER FORWARD-FILLED.** An expanding
    percentile over a forward-filled series counts one observation many times and reports a
    burn-in that was never served -- `I-2`'s finding in its most damaging form.
  * **ABSENT AND EMPTY ARE DIFFERENT** (`O21-D2`'s `C5`): "no recorder ever ran" and "the
    recorder ran and saw nothing" need different fixes.

    python tests/test_fleet_history.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet_history as H      # noqa: E402


class FakeStore:
    def __init__(self, n):
        self.n = n

    def load_intraday(self, run_time=None, top=None):
        return [{"ticker": "T%d" % i} for i in range(self.n)]


class TheSeriesContract(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fleethist_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_an_absent_series_is_reported_absent_and_not_as_zero_days(self):
        r = H.read("iv60_atm", self.root)
        self.assertTrue(r["ok"])
        self.assertTrue(r["absent"])
        self.assertEqual(r["n"], 0)
        self.assertIn("first cycle", r["reason"])

    def test_a_day_is_recorded_and_reads_back(self):
        H.record_iv60("2026-08-24", quotes={"AAPL": 0.31, "MSFT": 0.28}, root=self.root)
        r = H.read("iv60_atm", self.root)
        self.assertFalse(r["absent"])
        self.assertEqual(r["n"], 1)
        self.assertEqual(r["rows"][0]["payload"], {"AAPL": 0.31, "MSFT": 0.28})

    def test_recording_the_same_day_TWICE_does_not_double_record(self):
        """A cycle can legitimately run twice -- a retry, a manual dispatch."""
        a = H.record_iv60("2026-08-24", quotes={"AAPL": 0.31}, root=self.root)
        b = H.record_iv60("2026-08-24", quotes={"AAPL": 0.99}, root=self.root)
        self.assertTrue(a["wrote"])
        self.assertFalse(b["wrote"])
        self.assertTrue(b["already_present"])
        r = H.read("iv60_atm", self.root)
        self.assertEqual(r["n"], 1)
        self.assertEqual(r["rows"][0]["payload"]["AAPL"], 0.31, "the FIRST write stands")

    def test_a_BACKWARD_write_is_refused_and_says_why(self):
        """A series whose past can be rewritten is not evidence."""
        H.record_iv60("2026-08-24", quotes={"AAPL": 0.31}, root=self.root)
        back = H.record_iv60("2026-08-20", quotes={"AAPL": 0.10}, root=self.root)
        self.assertFalse(back["ok"])
        self.assertFalse(back["wrote"])
        self.assertIn("append-only", back["reason"])
        self.assertIn("GAP", back["reason"], "the refusal must say what to do instead")

    def test_an_unknown_series_cannot_be_written_by_accident(self):
        r = H.record("not_a_series", "2026-08-24", {}, root=self.root)
        self.assertFalse(r["ok"])
        self.assertIn("closed set", r["reason"])

    def test_days_accumulate_in_order(self):
        for i, d in enumerate(("2026-08-20", "2026-08-21", "2026-08-24")):
            H.record_iv60(d, quotes={"AAPL": 0.30 + i / 100.0}, root=self.root)
        r = H.read("iv60_atm", self.root)
        self.assertEqual([x["date"] for x in r["rows"]],
                         ["2026-08-20", "2026-08-21", "2026-08-24"])


class AMissingNameIsMissing(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fleethist_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_history_for_SKIPS_days_the_name_was_absent(self):
        """Not forward-filled and not zero-filled. An expanding percentile over a
        forward-filled series counts one observation many times."""
        H.record_iv60("2026-08-20", quotes={"AAPL": 0.30, "MSFT": 0.25}, root=self.root)
        H.record_iv60("2026-08-21", quotes={"MSFT": 0.26}, root=self.root)
        H.record_iv60("2026-08-24", quotes={"AAPL": 0.32}, root=self.root)
        self.assertEqual(H.history_for("iv60_atm", "AAPL", self.root),
                         [("2026-08-20", 0.30), ("2026-08-24", 0.32)])
        self.assertEqual(len(H.history_for("iv60_atm", "MSFT", self.root)), 2)

    def test_an_unsolvable_IV_is_OMITTED_and_never_recorded_as_zero(self):
        """A zero would enter an expanding percentile as the cheapest observation the name
        ever had, which is precisely backwards."""
        H.record_iv60("2026-08-24",
                      quotes={"AAPL": 0.31, "BAD": None, "NAN": float("nan"),
                              "ZERO": 0.0, "TEXT": "x"},
                      root=self.root)
        p = H.read("iv60_atm", self.root)["rows"][0]["payload"]
        self.assertEqual(sorted(p), ["AAPL"])
        self.assertEqual(H.history_for("iv60_atm", "ZERO", self.root), [])

    def test_a_name_never_seen_has_an_EMPTY_history_not_a_default(self):
        H.record_iv60("2026-08-24", quotes={"AAPL": 0.31}, root=self.root)
        self.assertEqual(H.history_for("iv60_atm", "NOSUCH", self.root), [])


class TheRecorders(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fleethist_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_alert_count_records_one_number_per_day(self):
        H.record_alert_count("2026-08-24", store=FakeStore(37), root=self.root)
        r = H.read("alert_count", self.root)
        self.assertEqual(r["rows"][0]["payload"], {"n": 37})
        self.assertEqual(r["rows"][0]["raw"]["n_alerts"], "37")

    def test_an_EMPTY_dip_reject_day_is_a_real_observation_and_is_recorded(self):
        """"Nobody was rejected today" is evidence about the day. Recording nothing would make
        it indistinguishable from the recorder not having run."""
        H.record_dip_rejects("2026-08-24", rejects=[], root=self.root)
        r = H.read("dip_rejects", self.root)
        self.assertEqual(r["n"], 1)
        self.assertEqual(r["rows"][0]["payload"], [])
        self.assertFalse(r["vacuous"], "a recorded empty day is not a vacuous series")

    def test_dip_rejects_dedupe_and_uppercase(self):
        H.record_dip_rejects("2026-08-24", rejects=["aapl", "AAPL", "msft"], root=self.root)
        self.assertEqual(H.read("dip_rejects", self.root)["rows"][0]["payload"],
                         ["AAPL", "MSFT"])

    def test_a_first_appearance_is_datable_which_is_the_whole_point_for_F11(self):
        H.record_dip_rejects("2026-08-20", rejects=["MSFT"], root=self.root)
        H.record_dip_rejects("2026-08-21", rejects=["MSFT", "AAPL"], root=self.root)
        H.record_dip_rejects("2026-08-24", rejects=["AAPL"], root=self.root)
        hist = H.history_for("dip_rejects", "AAPL", self.root)
        self.assertEqual([d for d, _ in hist], ["2026-08-21", "2026-08-24"])
        self.assertEqual(hist[0][0], "2026-08-21", "AAPL's FIRST appearance")

    def test_record_all_runs_every_recorder_and_never_raises_on_one_failing(self):
        """A recorder that raised would take the whole cycle down with it, and the cycle's
        other work is independent of whether a series accrued."""
        out = H.record_all("2026-08-24", store=FakeStore(3), rejects=["AAA"],
                           quotes={"AAA": 0.4}, root=self.root)
        self.assertEqual(out["recorded"], 3)
        self.assertEqual(sorted(out["series"]), ["alert_count", "dip_rejects", "iv60_atm"])
        self.assertTrue(all(v["ok"] for v in out["series"].values()))

    def test_record_all_is_idempotent_for_a_day(self):
        H.record_all("2026-08-24", store=FakeStore(3), rejects=["AAA"],
                     quotes={"AAA": 0.4}, root=self.root)
        again = H.record_all("2026-08-24", store=FakeStore(9), rejects=["BBB"],
                             quotes={"BBB": 0.9}, root=self.root)
        self.assertEqual(again["recorded"], 0)
        self.assertTrue(all(v["already_present"] for v in again["series"].values()))


class TheCoverageReport(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fleethist_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_it_names_every_series_even_before_any_has_started(self):
        cov = H.coverage(self.root)
        self.assertEqual(sorted(cov), ["alert_count", "dip_rejects", "iv60_atm"])
        self.assertTrue(all(not v["present"] for v in cov.values()))

    def test_it_reports_the_span_once_a_series_has_days(self):
        H.record_alert_count("2026-08-20", store=FakeStore(1), root=self.root)
        H.record_alert_count("2026-08-24", store=FakeStore(2), root=self.root)
        cov = H.coverage(self.root)["alert_count"]
        self.assertTrue(cov["present"])
        self.assertEqual((cov["first"], cov["last"], cov["n_days"]),
                         ("2026-08-20", "2026-08-24", 2))


class F20IsNotRebuiltHere(unittest.TestCase):

    def test_no_series_duplicates_the_bound_paper_index_track(self):
        """F-20 needs two years of the paper index book's daily series. That series is the
        BOUND track, written by `PT-WRITER`'s door. A second writer would be a second copy of
        a fact (`MA5`) and would put two series under one name -- the split `PT-SPLIT` had to
        unpick. F-20 is TIME-starved, not recorder-starved."""
        self.assertNotIn("index_track", H.SERIES)
        self.assertNotIn("index_vol", H.SERIES)
        self.assertEqual(sorted(H.SERIES), ["alert_count", "dip_rejects", "iv60_atm"])


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
