# -*- coding: utf-8 -*-
"""E10 — the pick logger wrote rows for sessions that never happened.

THE DEFECT
----------
`saas/tracker.log_options` dated a row `day or date.today().isoformat()` with no calendar
check, so a scan that ran on Labor Day 2026-09-07 logged options picks for a day the market
was shut (DELL was the observed one). `log_hot` has the same hole: its `scan_date` is whatever
the scan called itself.

WHY A HOLIDAY ROW IS NOT MERELY UNTIDY
--------------------------------------
The track's claim is *"if you had followed these picks on this date, here is what happened"*.
On a closed day nobody could have followed anything, so the row has no counterfactual behind
it -- and `update_returns` prices it against an index with no entry for that day, which is
`track._calendar_index`'s neighbouring hazard in a new place.

THE TWO HALVES, AND THE SECOND IS THE ONE THAT NEEDED A DECISION
----------------------------------------------------------------
Going forward: `track.log_picks` refuses. Backwards: the rows already written are KEPT and
COUNTED, because a record that quietly drops what it recorded is worse than one that explains
it. The count is computed on READ, so it covers rows written long before the guard existed.

THE REFUSAL IS RETURNED AND NOT RAISED, WHICH IS LOAD-BEARING
-------------------------------------------------------------
Both call sites in `saas/tracker.py` wrap the logger in a bare `except Exception: pass`. An
exception would be swallowed there, making a skip indistinguishable from a successful write --
exactly the shape of the `TypeError` that left every horizon on the Track Record tab reading
"accruing" for seven weeks while picks from early August were long past a month old.
"""
import datetime as dt
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.edge import track                                     # noqa: E402
from valuation.saas import tracker                                   # noqa: E402
from valuation.screener.market_session import is_trading_day         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPJS = os.path.join(REPO, "valuation", "web", "static", "app.js")

LABOR_DAY = "2026-09-07"          # the observed row's date
NEXT_SESSION = "2026-09-08"
A_SATURDAY = "2026-09-05"


class _Store(object):
    """Records what the logger asked to write, and nothing else."""

    def __init__(self):
        self.writes = []

    def save_track_picks(self, source, run_date, rows):
        self.writes.append((source, str(run_date)[:10], len(rows)))


class TheCalendarItselfIsRight(unittest.TestCase):
    """Checked first. If the calendar were wrong, every assertion below would be about the
    wrong dates and would still pass."""

    def test_labor_day_2026_is_closed_and_the_next_session_is_open(self):
        self.assertFalse(is_trading_day(dt.date.fromisoformat(LABOR_DAY)))
        self.assertTrue(is_trading_day(dt.date.fromisoformat(NEXT_SESSION)))

    def test_a_weekend_is_closed(self):
        self.assertFalse(is_trading_day(dt.date.fromisoformat(A_SATURDAY)))


class TheLoggerRefuses(unittest.TestCase):
    def test_a_holiday_writes_nothing(self):
        st = _Store()
        r = track.log_picks(st, "options", LABOR_DAY, ["DELL", "AAPL"])
        self.assertEqual(st.writes, [], "a closed day must not reach the record")
        self.assertFalse(r["written"])
        self.assertEqual(r["skipped"], 2)
        self.assertIn("not a trading day", r["reason"])

    def test_a_weekend_writes_nothing(self):
        st = _Store()
        track.log_picks(st, "hot10", A_SATURDAY, ["AAA"])
        self.assertEqual(st.writes, [])

    def test_a_TRADING_day_still_writes(self):
        """The positive control. A guard that refuses everything is not a guard, and this is
        the assertion that would catch it."""
        st = _Store()
        r = track.log_picks(st, "options", NEXT_SESSION, ["DELL", "AAPL"])
        self.assertEqual(st.writes, [("options", NEXT_SESSION, 2)])
        self.assertTrue(r["written"])
        self.assertEqual(r["n"], 2)
        self.assertIsNone(r["reason"])

    def test_it_RETURNS_the_refusal_rather_than_raising(self):
        """Because both call sites swallow exceptions, a raise would be invisible."""
        st = _Store()
        try:
            r = track.log_picks(st, "options", LABOR_DAY, ["DELL"])
        except Exception as e:                                       # noqa: BLE001
            self.fail("log_picks raised on a closed day: %r" % (e,))
        self.assertIsInstance(r, dict)

    def test_an_unparseable_date_fails_OPEN(self):
        """A calendar this cannot check must not stop a legitimate write -- losing a day's
        picks is irreversible on an append-only record, and an odd date string is not
        evidence the market was shut."""
        st = _Store()
        r = track.log_picks(st, "hot10", "not-a-date", ["AAA"])
        self.assertEqual(len(st.writes), 1)
        self.assertTrue(r["written"])
        self.assertIn("not checkable", r["reason"])


class TheCallerSeesTheRefusal(unittest.TestCase):
    def test_log_options_returns_the_skip(self):
        st = _Store()
        rows = [{"ticker": "DELL", "opt_score": 99}]

        import valuation.saas.notify as N
        old = N.screaming_buys
        N.screaming_buys = lambda r, m: rows
        try:
            r = tracker.log_options(st, rows, 0, day=LABOR_DAY)
        finally:
            N.screaming_buys = old
        self.assertEqual(st.writes, [])
        self.assertIsNotNone(r, "a swallowed skip is indistinguishable from a write")
        self.assertFalse(r["written"])

    def test_log_options_still_writes_on_a_session(self):
        st = _Store()
        rows = [{"ticker": "DELL", "opt_score": 99}]
        import valuation.saas.notify as N
        old = N.screaming_buys
        N.screaming_buys = lambda r, m: rows
        try:
            r = tracker.log_options(st, rows, 0, day=NEXT_SESSION)
        finally:
            N.screaming_buys = old
        self.assertEqual(st.writes, [("options", NEXT_SESSION, 1)])
        self.assertTrue(r["written"])


class ExistingRowsAreLabelledNotDeleted(unittest.TestCase):
    """The backwards half. Written through `save_track_picks` DIRECTLY, which is how the real
    rows got there -- before the guard existed."""

    def setUp(self):
        from valuation.web import app as W
        self.W = W
        self.st = W._store()
        # One closed day and two open ones.
        self.st.save_track_picks("options", LABOR_DAY,
                                 [{"ticker": "DELL", "rank": 1}, {"ticker": "AAPL", "rank": 2}])
        self.st.save_track_picks("options", NEXT_SESSION, [{"ticker": "DELL", "rank": 1}])
        self.st.save_track_picks("options", "2026-09-09", [{"ticker": "MSFT", "rank": 1}])

    def test_the_rows_are_still_there(self):
        """Counted, not purged. The record keeps what it recorded."""
        picks = self.st.all_track_picks("options") or []
        days = {str(p.get("run_date") or "")[:10] for p in picks}
        self.assertIn(LABOR_DAY, days, "an existing row must not be deleted")

    def test_the_census_counts_them(self):
        c = self.W._track_counts(self.st, "options")
        self.assertEqual(c["n_non_trading_days"], 1)
        self.assertEqual(c["n_rows_on_non_trading_days"], 2)
        self.assertEqual(c["non_trading_days"], [LABOR_DAY])

    def test_the_census_does_not_change_the_headline_counts(self):
        """A disclosure, not a screen: it may not drop a pick or a day."""
        c = self.W._track_counts(self.st, "options")
        self.assertEqual(c["n_logged"], 4)
        self.assertEqual(c["n_days"], 3)

    def test_a_clean_log_reports_zero_rather_than_nothing(self):
        """Zero and absent must not read alike -- a census that never ran and one that found
        nothing are different states."""
        c = self.W._track_counts(self.st, "hot10")
        self.assertEqual(c["n_non_trading_days"], 0)
        self.assertEqual(c["n_rows_on_non_trading_days"], 0)
        self.assertEqual(c["non_trading_days"], [])


class TheCardShowsIt(unittest.TestCase):
    """Read on the CODE, comments stripped: a positive assertion satisfied by a comment goes
    green while the card shows nothing."""

    def _body(self):
        src = open(APPJS, encoding="utf-8").read()
        i = src.index("function _trackCard")
        j = src.index("\nfunction ", i + 1)
        return _strip_js_comments(src[i:j])

    def test_the_card_reads_the_count(self):
        self.assertIn("n_rows_on_non_trading_days", self._body())

    def test_the_card_RENDERS_it_rather_than_merely_reading_it(self):
        """Reading a field is not rendering it -- the failure one lane over was a payload
        served to nobody."""
        body = self._body()
        self.assertIn("shutLine", body)
        self.assertEqual(body.count("${shutLine}"), 2,
                         "both branches of the card must show it: %d" % body.count("${shutLine}"))

    def test_it_says_the_rows_are_kept(self):
        self.assertIn("kept rather than deleted", self._body())

    def test_a_zero_renders_NO_sentence(self):
        """A zero needs no sentence, and printing "0 picks are dated on closed days" on every
        card is how a disclosure becomes noise and then gets removed."""
        body = self._body()
        self.assertIn("nShut", body)
        self.assertRegex(body, r"nShut\s*\n?\s*\?")

    def test_the_stripper_is_not_vacuous(self):
        kept = _strip_js_comments("const a = 1; // x\n/* y */\nconst b = 2;")
        self.assertIn("const a = 1;", kept)
        self.assertIn("const b = 2;", kept)
        self.assertNotIn("/* y */", kept)
        self.assertIn("function _trackCard", self._body())


def _strip_js_comments(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in js.splitlines())


if __name__ == "__main__":
    unittest.main(verbosity=2)
