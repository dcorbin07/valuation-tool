# -*- coding: utf-8 -*-
"""ITEM 86 — three jobs that had been failing for weeks, and one event stuck eleven days.

Every one of the three was reported as a single Sunday's or a single day's failure. Measured
against the run history, none of them was:

  * **the weekly theme crawl has failed EVERY Sunday since Tradier closed** -- 10-11, 10-18,
    10-25, 11-01 -- with the last success on 2026-10-06, two days before the 10-08 closure. Its
    universe is `--universe broker`, which is `broker_universe.build()`, which is Tradier. It
    refused correctly ("the broker universe came back empty", exit 3) and refusing was the wrong
    answer, because the broker is not the only universe there is;
  * **`valreads-record` has failed on all three runs it has ever had** -- 10-18, 10-25, 11-01 --
    on a blind-register guard that cannot work in a shallow clone, each time after the recorder
    had run for ~27 minutes and verified its own append-only guarantee;
  * **both LIVE CHECK failures are the check running before the thing it checks could exist.**
    The check's crons are 13:45Z and 23:05Z; the failing runs were at 18:50Z and 22:27Z -- the
    MORNING cron delivered 5.1 and 8.7 hours late, landing in the afternoon and then demanding
    publications that were still being written. On 10-30 the intraday job ran 18:47:36 ->
    18:59:54Z and the check ran at 18:50:13Z. On 11-02 the scan published later that evening and
    the live `scan_date` is now 2026-11-02, so the complaint was premature, not true.

`PT-GAPDUE`'s shape twice over, and the fix is a due-time rule rather than a looser check --
modelled on `check_index_track`, including its own hard-won refinement: **before the deadline,
assert the PREVIOUS session rather than skipping**, because a skip asserts nothing and a
publisher that died a week ago would pass.
"""
from __future__ import annotations

import datetime as _dt
import io
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401  (must precede the valuation imports)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import live_check as LC
from scripts import theme_cache_build as TCB

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: A real trading session, and the one before it, from the project's own calendar rather than by
#: counting weekdays -- the day after a holiday is exactly when a hand-rolled calendar is wrong.
SESSION = _dt.date(2026, 11, 2)
PREV = _dt.date(2026, 10, 30)


class _Rep(LC.Report):
    """The real Report, with its printing silenced."""

    def _emit(self, verdict, name, detail):
        self.lines.append("%-4s  %-44s %s" % (verdict, name, detail))


def _hot(scan_date):
    return {"rows": [{"ticker": "AAPL"}],
            "scan_date": scan_date,
            "health": {"theme_contributing": {"institutional": 0.7, "insider": 0.71,
                                              "capital_discipline": 0.93}}}


class _At(object):
    """Freeze `live_check`'s clock."""

    def __init__(self, when):
        self.when = when

    def __enter__(self):
        self._keep = LC._utcnow
        LC._utcnow = lambda: self.when
        return self

    def __exit__(self, *a):
        LC._utcnow = self._keep
        return False


# =============================================================================================
class TheThemeCrawlNoLongerDependsOnADeadBroker(unittest.TestCase):
    """#1. Tradier closed on 2026-10-08 and this crawl is a feature that used it."""

    def setUp(self):
        self._bu = None

    def _patch_broker(self, rows):
        from valuation.screener import broker_universe as BU
        self._bu = BU.build
        BU.build = lambda cfg, limit=0: rows
        self.addCleanup(lambda: setattr(BU, "build", self._bu))

    def _patch_live(self, rows, note=""):
        from valuation.screener import providers as P

        class _Prov(object):
            universe_note = note

            def __init__(self, *a, **k):
                pass

            def get_universe(self, scope="bundled"):
                return rows

        keep = P.FreeProvider
        P.FreeProvider = _Prov
        self.addCleanup(lambda: setattr(P, "FreeProvider", keep))

    def test_an_empty_broker_falls_back_to_the_live_scans_own_universe(self):
        self._patch_broker([])
        self._patch_live([{"ticker": "AAPL"}, {"ticker": "MSFT"}],
                         note="no TRADIER_TOKEN — cannot source the broker universe")
        got = TCB.served_from_universe("broker", limit=1500)
        self.assertEqual([r["ticker"] for r in got["served"]], ["AAPL", "MSFT"])
        self.assertIn("broker universe came back empty", got["reason"])
        self.assertIn("Tradier closed", got["reason"])

    def test_the_fallback_records_the_source_it_actually_got(self):
        """A cache is only meaningful beside a statement of which population it covers, and
        after a fallback that is no longer what the command line claims."""
        self._patch_broker([])
        self._patch_live([{"ticker": "AAPL"}])
        got = TCB.served_from_universe("broker", limit=1500)
        self.assertEqual(got["scan_date"], "live_universe_top_1")
        self.assertNotIn("broker_top", got["scan_date"] or "")

    def test_a_live_broker_is_still_preferred_and_is_still_labelled_as_the_broker(self):
        """The fallback must not quietly become the primary if Tradier ever returns."""
        self._patch_broker([{"ticker": "IBM"}])
        self._patch_live([{"ticker": "AAPL"}])
        got = TCB.served_from_universe("broker", limit=1500)
        self.assertEqual([r["ticker"] for r in got["served"]], ["IBM"])
        self.assertEqual(got["scan_date"], "broker_top_1500")

    def test_it_still_REFUSES_when_there_is_no_universe_at_all(self):
        """The original guarantee, kept: a cache built over nothing reads to `live_themes.py`
        exactly like the absent file this builder exists to replace."""
        self._patch_broker([])
        self._patch_live([])
        got = TCB.served_from_universe("broker", limit=1500)
        self.assertEqual(got["served"], [])
        self.assertIsNone(got["scan_date"])

    def test_the_truncation_takes_the_front_of_the_source_order(self):
        """EDGAR's own list is SIZE-ORDERED (NVDA, AAPL, MSFT, GOOGL...), so the first `limit`
        names are the large end. `B12`'s alphabetical-slice defect was looked for and is absent
        -- but only because the cut happens BEFORE the alphabetical sort, so that is pinned."""
        self._patch_broker([])
        self._patch_live([{"ticker": "ZBIG"}, {"ticker": "YBIG"}, {"ticker": "ASMALL"}])
        got = TCB.served_from_universe("broker", limit=2)
        self.assertEqual(sorted(r["ticker"] for r in got["served"]), ["YBIG", "ZBIG"])
        self.assertNotIn("ASMALL", [r["ticker"] for r in got["served"]])

    def test_the_explicit_live_spec_works_on_its_own(self):
        self._patch_live([{"ticker": "AAPL"}])
        got = TCB.served_from_universe("live", limit=10)
        self.assertEqual([r["ticker"] for r in got["served"]], ["AAPL"])


# =============================================================================================
class TheHotListCheckWaitsUntilTheScanIsDue(unittest.TestCase):
    """#3, half one: the 2026-11-02 false alarm."""

    def test_the_previous_sessions_scan_passes_before_the_deadline(self):
        rep = _Rep()
        with _At(_dt.datetime(2026, 11, 2, 22, 27, tzinfo=_dt.timezone.utc)):
            self._run(rep, _hot(PREV.isoformat()))
        line = [l for l in rep.lines if "fresh" in l][0]
        self.assertIn("PASS", line, rep.lines)
        self.assertIn("not due until", line)

    def test_the_same_state_FAILS_once_the_deadline_has_passed(self):
        """So a scanner that stopped is still caught -- the next morning, not never."""
        rep = _Rep()
        with _At(_dt.datetime(2026, 11, 3, 12, 1, tzinfo=_dt.timezone.utc)):
            self._run(rep, _hot(PREV.isoformat()))
        line = [l for l in rep.lines if "fresh" in l][0]
        self.assertIn("FAIL", line, rep.lines)

    def test_a_genuinely_old_scan_fails_even_before_the_deadline(self):
        """The previous session is the most slack there is. A week-old scan is not 'not due'."""
        rep = _Rep()
        with _At(_dt.datetime(2026, 11, 2, 22, 27, tzinfo=_dt.timezone.utc)):
            self._run(rep, _hot("2026-09-25"))
        line = [l for l in rep.lines if "fresh" in l][0]
        self.assertIn("FAIL", line, rep.lines)
        self.assertIn("already due", line)

    def test_the_sessions_own_scan_passes_outright(self):
        rep = _Rep()
        with _At(_dt.datetime(2026, 11, 2, 22, 27, tzinfo=_dt.timezone.utc)):
            self._run(rep, _hot(SESSION.isoformat()))
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_it_never_SKIPS(self):
        """`check_index_track`'s lesson: a skip before the deadline asserts nothing for half the
        runs, and a publisher that died a week ago would pass."""
        for scan in (PREV.isoformat(), "2026-09-25", SESSION.isoformat()):
            rep = _Rep()
            with _At(_dt.datetime(2026, 11, 2, 22, 27, tzinfo=_dt.timezone.utc)):
                self._run(rep, _hot(scan))
            self.assertEqual(rep.skipped, 0, "%s skipped: %s" % (scan, rep.lines))

    def _run(self, rep, payload):
        import json as _json

        keep = LC.fetch

        def _fake(base, path, **kw):
            return 200, _json.dumps(payload).encode("utf-8"), "application/json"

        LC.fetch = _fake
        try:
            LC.check_hot_list("https://x", rep, SESSION)
        finally:
            LC.fetch = keep


# =============================================================================================
class TheSignalsCheckJudgesAgeNotTheRunnersClock(unittest.TestCase):
    """#3, half two: the 2026-10-30 false alarm."""

    def _run(self, rep, run_time, now):
        import json as _json

        keep = LC.fetch

        def _fake(base, path, **kw):
            return (200, _json.dumps({"run_time": run_time, "rows": [{"t": 1}]})
                    .encode("utf-8"), "application/json")

        LC.fetch = _fake
        try:
            LC.check_signals("https://x", rep, now)
        finally:
            LC.fetch = keep

    def test_the_1030_shape_passes(self):
        """The intraday job ran 18:47:36 -> 18:59:54Z; the check ran at 18:50:13Z. The newest
        feed it could possibly have seen was the previous session's."""
        rep = _Rep()
        self._run(rep, "2026-10-29 23:27", _dt.datetime(2026, 10, 30, 18, 50))
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_a_feed_two_sessions_old_fails(self):
        rep = _Rep()
        self._run(rep, "2026-10-28 14:00", _dt.datetime(2026, 10, 30, 18, 50))
        self.assertTrue(any("FAIL" in l for l in rep.lines), rep.lines)

    def test_an_evening_run_now_ASSERTS_instead_of_standing_down(self):
        """Half this job's runs used to assert nothing about the feed.

        The 2026-11-02 report reads `SKIP ... it is 22:27 UTC, outside 13:00-21:30`. That skip
        existed because the old rule was unanswerable outside market hours; the age rule is
        answerable at any hour, so standing down only cost coverage -- a feed that died a week
        ago would have been caught by the morning run alone, and only if it landed in the band.
        """
        rep = _Rep()
        self._run(rep, "2026-10-28 14:00", _dt.datetime(2026, 10, 30, 22, 27))
        self.assertEqual(rep.skipped, 0, rep.lines)
        self.assertTrue(any("FAIL" in l for l in rep.lines), rep.lines)

    def test_a_non_trading_day_still_stands_down(self):
        """That one is a fact about the market rather than a gap in what can be measured."""
        rep = _Rep()
        self._run(rep, "2026-10-30 23:04", _dt.datetime(2026, 11, 1, 18, 0))
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.skipped, 1, rep.lines)

    def test_the_clock_the_job_happened_to_run_at_is_not_the_subject(self):
        """GitHub decides that, not the product. 23:04 is still that day's feed."""
        rep = _Rep()
        self._run(rep, "2026-10-30 23:04", _dt.datetime(2026, 10, 30, 19, 0))
        self.assertEqual(rep.failed, 0, rep.lines)


# =============================================================================================
class TheBlindRegisterGuardCannotRunInAShallowClone(unittest.TestCase):
    """#2. It fired against a correct tree on all three runs this workflow has ever had."""

    def test_a_shallow_clone_is_reported_UNVERIFIABLE_rather_than_violated(self):
        """`C5`: absent is not the same as measured zero. Proved by making `git` say shallow."""
        sys.path.insert(0, os.path.join(REPO, "tests"))
        import test_valreads as TV

        case = TV.TestTheRegisterCameFirst(
            "test_the_register_is_a_strict_git_ancestor_of_the_recorder")
        keep = subprocess.run

        def _fake(cmd, *a, **kw):
            if "--is-shallow-repository" in cmd:
                class _R(object):
                    stdout = b"true\n"
                    stderr = b""
                    returncode = 0
                return _R()
            return keep(cmd, *a, **kw)

        subprocess.run = _fake
        try:
            with self.assertRaises(unittest.SkipTest) as cm:
                case.test_the_register_is_a_strict_git_ancestor_of_the_recorder()
            self.assertIn("SHALLOW", str(cm.exception))
            self.assertIn("land gate", str(cm.exception))
        finally:
            subprocess.run = keep

    def test_it_still_asserts_the_property_in_a_full_clone(self):
        """The positive control. A guard that skips everywhere is not a guard -- and this
        checkout and the land gate are both full clones, so the real assertion runs."""
        out = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                             cwd=REPO, capture_output=True)
        self.assertEqual(out.stdout.decode().strip(), "false",
                         "this checkout is shallow, so the control cannot run")
        sys.path.insert(0, os.path.join(REPO, "tests"))
        import test_valreads as TV
        case = TV.TestTheRegisterCameFirst(
            "test_the_register_is_a_strict_git_ancestor_of_the_recorder")
        case.test_the_register_is_a_strict_git_ancestor_of_the_recorder()

    def test_the_recorder_workflow_asks_for_the_full_history(self):
        src = io.open(os.path.join(REPO, "pending_workflows", "valreads-record.yml"),
                      encoding="utf-8").read()
        self.assertIn("fetch-depth: 0", src)


# =============================================================================================
class TheRepointedScheduleGuardStillBites(unittest.TestCase):
    """Main was RED and nobody had noticed, because no land had run since Don's install.

    Don ran item 85's fixed installer on 2026-10-29 19:39 (`817ca26`, "from main's own
    pending_workflows") and it installed all three files in one run, exactly as designed. That
    put item 84B's hot job -- which fires on EVERY schedule by design and decides internally --
    onto main, where two guards in `test_proposal_auto_scan_themes.py` assumed a job is alive on
    exactly the crons its `if` names. The last land gate ran 2026-10-28, before the install, so
    the suite had been red on main for four days with no lane finding out.

    **THE REPOINT MUST STILL REFUSE THE SHAPE IT WAS WRITTEN FOR**, or it is a loophole rather
    than a correction. Session 70's job fired on every schedule and ran a 1,500-name SEC crawl
    75 unwanted times a week; that is still refused, because it gates nothing on a decision.
    """

    def _mod(self):
        sys.path.insert(0, os.path.join(REPO, "tests"))
        import test_proposal_auto_scan_themes as TP
        return TP

    def test_a_catch_all_job_that_decides_NOTHING_is_still_refused(self):
        TP = self._mod()
        case = TP.EveryJobNamesItsOwnSchedule("test_the_PROPOSAL_jobs_each_name_their_own_schedule")
        with self.assertRaises(AssertionError) as cm:
            case._assert_named("fixture", "greedy",
                               "${{ github.event_name == 'schedule' }}",
                               "    steps:\n      - run: python crawl.py\n")
        self.assertIn("decision step", str(cm.exception))

    def test_the_real_hot_job_is_permitted_and_names_its_decision_step(self):
        TP = self._mod()
        src = TP._authoritative()
        body = src.split("\njobs:", 1)[1]
        blocks = TP._job_blocks(body)
        ifs = TP._job_ifs(body)
        self.assertIn("hot", ifs, sorted(ifs))
        self.assertTrue(TP._fires_on_every_schedule(ifs["hot"]),
                        "the installed hot job no longer fires on every schedule: %r"
                        % ifs["hot"])
        self.assertEqual(TP._decides_internally(blocks["hot"]), "decide")

    def test_session_70s_own_text_is_still_caught(self):
        """The original positive control, re-run through the repointed clause."""
        TP = self._mod()
        case = TP.EveryJobNamesItsOwnSchedule("test_the_PROPOSAL_jobs_each_name_their_own_schedule")
        bad = ("${{ always() && (github.event_name == 'schedule' || "
               "github.event.inputs.kind == 'themes') }}")
        with self.assertRaises(AssertionError):
            case._assert_named("fixture", "themes-assemble", bad, "    steps:\n")


class TheTwoDeadlinesComeFromOneFunction(unittest.TestCase):
    """`B7`. Two copies of "the morning after a session" is two places to get the roll wrong."""

    def test_the_track_row_rule_delegates(self):
        self.assertEqual(LC._track_row_due_after(_dt.date(2026, 10, 6)),
                         _dt.datetime(2026, 10, 7, 12, 0, tzinfo=_dt.timezone.utc))

    def test_the_hot_scan_rule_uses_the_same_helper(self):
        self.assertEqual(
            LC._due_the_morning_after(SESSION, LC.HOT_SCAN_DUE_UTC_HOUR,
                                      LC.HOT_SCAN_DUE_UTC_MINUTE),
            _dt.datetime(2026, 11, 3, 12, 0, tzinfo=_dt.timezone.utc))

    def test_the_day_roll_crosses_a_month_end(self):
        self.assertEqual(LC._due_the_morning_after(_dt.date(2026, 10, 31), 12),
                         _dt.datetime(2026, 11, 1, 12, 0, tzinfo=_dt.timezone.utc))

    def test_no_session_means_no_deadline_rather_than_a_crash(self):
        self.assertIsNone(LC._due_the_morning_after(None, 12))


if __name__ == "__main__":
    unittest.main(verbosity=2)
