"""ITEM 30 — THE LIVE CHECKER'S VERDICT LOGIC, WITH THE NETWORK BLOCKED.

**THIS SUITE MUST NEVER REACH valquo.co, AND THAT IS NOT A STYLE PREFERENCE.** The gate runs
every suite on every land; a suite that called the live site would make the land depend on the
site being up, so a deploy outage would read as a code failure and a code failure could be
dismissed as an outage. Worse, the checker's whole value is that it is the ONLY thing that talks
to production — if its own tests did too, a green suite would stop meaning the logic is right.

So `live_check.fetch` is replaced outright and `urllib.request.urlopen` is blocked, with a test
that the block bites. What is under test is the VERDICT: given a payload, does the checker call it
a pass or a fail, and does the process exit non-zero.

WHAT THESE PIN, each one a way this class of checker goes wrong:

  * **A SKIP IS NEVER A PASS.** Counted separately, and the exit code ignores it. The opposite
    convention is how `/api/signals` would quietly stop being checked every weekend.
  * **AN EXPORT IS JUDGED BY ITS MAGIC BYTES.** This app answers `200` with a JSON error body
    when an export fails, and a JSON error is "non-empty" — so a length check would pass on a
    broken export. Driven with exactly that payload.
  * **A NOT-FOUND TICKER IS JUDGED BY ITS STATUS.** The defect was a `200` carrying a score of 40
    and a recommendation of "Reduce" for a company nobody identified, so a checker that only
    looked for an error key would have passed it.
  * **THE TWO ALERT SURFACES ARE COMPARED TO EACH OTHER**, not to a number typed into the
    checker. They disagreed by exactly the 8 rows one of them was mis-classifying, and a
    hard-coded 15 would have gone stale the first time a real alert closed.
  * **FRESHNESS COMES FROM THE MARKET CALENDAR**, so it does not fail on a holiday.

    python tests/test_live_check.py
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.


def _load():
    """Import `scripts/live_check.py` by path — it is a script, not a package module."""
    p = os.path.join(REPO, "scripts", "live_check.py")
    spec = importlib.util.spec_from_file_location("live_check_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LC = _load()

SESSION = _dt.date(2026, 10, 2)

GOOD_HOT = {"scan_date": "2026-10-02", "rows": [{"ticker": "A"}] * 100,
            "health": {"theme_contributing": {"institutional": 0.9, "insider": 0.8,
                                              "capital_discipline": 0.96}}}


class _Net:
    """Replaces `live_check.fetch` with a table, and blocks the transport underneath it."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def __enter__(self):
        self._fetch = LC.fetch
        import urllib.request
        self._urlopen = urllib.request.urlopen
        self._build = urllib.request.build_opener

        def _no_net(*a, **k):
            raise AssertionError("this suite must not touch the network")

        urllib.request.urlopen = _no_net
        urllib.request.build_opener = _no_net
        self._ur = urllib.request

        def fake(base, path, *, method="GET", body=None, timeout=240):
            key = (method, path.split("?")[0]) if method != "POST" else \
                  (method, path, json.dumps(body, sort_keys=True))
            self.calls.append(key)
            for k, v in self.table.items():
                if k == key or (len(k) == 2 and k == (method, path.split("?")[0])):
                    return v
            return 404, b"{}", "application/json"

        LC.fetch = fake
        return self

    def __exit__(self, *exc):
        LC.fetch = self._fetch
        self._ur.urlopen = self._urlopen
        self._ur.build_opener = self._build
        return False


def _j(obj, code=200):
    return code, json.dumps(obj).encode("utf-8"), "application/json"


class TheNetworkIsBlocked(unittest.TestCase):
    def test_the_block_bites(self):
        with _Net({}):
            import urllib.request
            with self.assertRaises(AssertionError):
                urllib.request.urlopen("https://valquo.co/")

    def test_and_is_restored(self):
        """A harness that left urllib broken would poison every later suite in the process."""
        with _Net({}):
            pass
        import urllib.request
        self.assertNotEqual(getattr(urllib.request.urlopen, "__name__", ""), "_no_net")


class ASkipIsNeverAPass(unittest.TestCase):
    def test_counts_are_separate(self):
        rep = LC.Report()
        rep.ok("a", "1")
        rep.skip("b", "why")
        rep.bad("c", "2")
        self.assertEqual((rep.passed, rep.failed, rep.skipped), (1, 1, 1))

    def test_a_skip_alone_does_not_fail_the_run(self):
        rep = LC.Report()
        rep.ok("a", "1")
        rep.skip("b", "why")
        self.assertEqual(rep.finish(), 0)

    def test_one_fail_fails_the_run(self):
        rep = LC.Report()
        for _ in range(20):
            rep.ok("a", "1")
        rep.bad("b", "2")
        self.assertEqual(rep.finish(), 1)


class TheHotListChecks(unittest.TestCase):
    def test_a_fresh_list_with_live_themes_passes(self):
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(GOOD_HOT)}):
            LC.check_hot_list("https://x", rep, SESSION)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.passed, 5)

    def test_a_stale_scan_date_fails(self):
        d = dict(GOOD_HOT, scan_date="2026-09-25")
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(d)}):
            LC.check_hot_list("https://x", rep, SESSION)
        self.assertTrue(any("FAIL" in ln and "fresh" in ln for ln in rep.lines), rep.lines)

    def test_a_dead_theme_fails_and_names_the_number(self):
        """THE LIVE STATE ON 2026-10-04: institutional and insider both 0.00."""
        d = json.loads(json.dumps(GOOD_HOT))
        d["health"]["theme_contributing"]["institutional"] = 0.0
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(d)}):
            LC.check_hot_list("https://x", rep, SESSION)
        line = [ln for ln in rep.lines if "institutional" in ln][0]
        self.assertIn("FAIL", line)
        self.assertIn("0.00", line, "the number must be on the line, pass or fail")

    def test_a_missing_theme_fails_rather_than_passing_on_None(self):
        """A theme the payload omits is not a theme that is contributing."""
        d = json.loads(json.dumps(GOOD_HOT))
        del d["health"]["theme_contributing"]["insider"]
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(d)}):
            LC.check_hot_list("https://x", rep, SESSION)
        self.assertTrue(any("FAIL" in ln and "insider" in ln for ln in rep.lines), rep.lines)


class TheDipChecks(unittest.TestCase):
    """REWRITTEN 2026-10-07, because the version these replace PASSED ON THE BROKEN STATE.

    It asserted that the budget was spent on names that QUALIFY and that the shortfall was
    REPORTED. Both were true while the page showed two rows out of 218 qualifying, so the live
    run printed `PASS dip spends its budget on qualifying names - 12 of 218 qualifiers valued,
    206 reported as capped`. A check that passes on the state it was written to catch is worse
    than no check: it is read as evidence the thing works.

    The property now is an IDENTITY, which a disclosure cannot satisfy:

        n_qualified_on_depth == rows + n_unmeasured + rejected_health + rejected_shallow
                                + n_health_not_scored

    with `capped` zero.

    THE FIFTH TERM IS DON'S THIRD GROUP (DECISIONS.md, 2026-10-07) and it is in the identity for
    the same reason the others are: a name that leaves `rejected_health` for a new bucket and is
    not counted anywhere looks like a SMALLER rejection count, i.e. like an improvement. These
    fixtures went red when the term was added, which is the check doing its job -- a payload it
    cannot verify is reported as unverifiable rather than passed.
    """

    def _run(self, payload):
        rep = LC.Report()
        with _Net({("GET", "/api/dip"): _j(payload)}):
            LC.check_dip("https://x", rep)
        return rep

    def _line(self, rep):
        return [ln for ln in rep.lines if "every qualifying name" in ln][0]

    def _unmeasured_line(self, rep):
        """BY THE CHECK'S NAME, not by the word. The identity line now also contains
        "unmeasured", so `if "unmeasured" in ln` picks the wrong line and the assertion lands on
        a different check -- which is the wrong-object family in a test selector."""
        return [ln for ln in rep.lines if "reports its unmeasured" in ln][0]

    def test_the_whole_qualifying_set_served_passes(self):
        # `n_unmeasured` is 0 HERE ON PURPOSE: a separate check fails any unmeasured name,
        # so a fixture carrying some would fail the suite for a reason that is not the subject.
        # The identity's tolerance of unmeasured names is pinned by its own test below.
        rep = self._run({"n_eligible": 242, "n_qualified_on_depth": 204, "n_measured": 204,
                         "capped": 0, "n_unmeasured": 0, "rejected_health": 180,
                         "rejected_shallow": 17, "rejected_checks": 38,
                         # NON-ZERO ON PURPOSE. A fixture carrying `0` here would satisfy the
                         # identity whether or not the check reads the term at all, which is
                         # the vacuous direction: the test would pass against a check that had
                         # dropped the new bucket. 204 = 4 + 0 + 180 + 17 + 3.
                         "n_health_not_scored": 3, "n_health_not_scored_shallow": 1,
                         "dip_source": "precomputed",
                         "rows": [{"t": i} for i in range(4)]})
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertIn("204 qualifying = 4 rows", self._line(rep))
        self.assertIn("3 health-not-scored", self._line(rep))

    def test_THE_LIVE_BROKEN_STATE_FAILS(self):
        """The exact payload the old check passed on. This is the regression."""
        rep = self._run({"n_eligible": 240, "n_qualified_on_depth": 218, "n_measured": 12,
                         "capped": 206, "n_unmeasured": 0, "rejected_health": 8,
                         "rejected_shallow": 2, "rejected_checks": 4, "n_health_not_scored": 0,
                         "dip_source": "live",
                         "rows": [{"t": 1}, {"t": 2}]})
        self.assertEqual(rep.failed, 1, rep.lines)
        self.assertIn("CAPPED", self._line(rep))

    def test_counts_that_do_not_add_up_fail(self):
        """The identity is arithmetic, so a screen that loses names somewhere else is caught."""
        rep = self._run({"n_eligible": 242, "n_qualified_on_depth": 204, "n_measured": 204,
                         "capped": 0, "n_unmeasured": 0, "rejected_health": 100,
                         "rejected_shallow": 0, "rejected_checks": 0, "n_health_not_scored": 0,
                         "dip_source": "precomputed",
                         "rows": [{"t": 1}]})
        self.assertEqual(rep.failed, 1, rep.lines)
        self.assertIn("do not add up", self._line(rep))

    def test_a_payload_missing_a_counter_cannot_be_checked_and_says_so(self):
        """Absent is not zero. Treating a missing counter as 0 would make the identity hold by
        accident on a payload that cannot support it."""
        rep = self._run({"n_eligible": 242, "n_qualified_on_depth": 204, "n_measured": 204,
                         "capped": 0, "rejected_health": 1, "rows": [{"t": 1}]})
        # TWO checks fail here and that is right: the identity cannot be computed, AND the
        # unmeasured counter is absent. Asserting a TOTAL of 1 would have made this test depend
        # on the other check's behaviour.
        self.assertIn("cannot be checked", self._line(rep))
        self.assertIn("FAIL", self._line(rep))

    def test_rejected_checks_is_NOT_in_the_identity(self):
        """It is the ROW-LEVEL site -- rows the snapshot refused, counted while the eligible set
        is formed and before anything qualifies on depth. The task's wording includes it; adding
        it would make the identity wrong by exactly its value and fail a correct screen."""
        rep = self._run({"n_eligible": 242, "n_qualified_on_depth": 10, "n_measured": 10,
                         "capped": 0, "n_unmeasured": 0, "rejected_health": 6,
                         "rejected_shallow": 2, "rejected_checks": 999,
                         "n_health_not_scored": 0,
                         "dip_source": "precomputed", "rows": [{"t": 1}, {"t": 2}]})
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertIn("999 rejected earlier", self._line(rep))

    def test_zero_rows_still_fails_its_own_check(self):
        """Separate from the identity: a screen can serve every qualifier and still show
        nothing, and that is a different failure the page must not hide."""
        rep = self._run({"n_eligible": 242, "n_qualified_on_depth": 204, "n_measured": 204,
                         "capped": 0, "n_unmeasured": 0, "rejected_health": 204,
                         "rejected_shallow": 0, "rejected_checks": 0,
                         "n_health_not_scored": 0,
                         "dip_source": "precomputed", "rows": []})
        self.assertTrue(any("FAIL" in ln and "returns rows" in ln for ln in rep.lines),
                        rep.lines)

    def test_SOME_unmeasured_names_are_reported_rather_than_failed(self):
        """REPOINTED 2026-10-07. This demanded `n_unmeasured` be ZERO, and that passed only
        because the screen valued 12 names per request and those 12 happened to carry a 52-week
        high. Serving the whole qualifying set makes the real figure visible: 90 of 210 on the
        2026-10-06 scan carry no drawdown, 59 of them the names whose snapshot has no
        `high_prox` either. Demanding zero demands the upstream feed be complete.
        """
        rep = self._run({"n_eligible": 10, "n_qualified_on_depth": 10, "n_measured": 10,
                         "capped": 0, "n_unmeasured": 3, "rejected_health": 0,
                         "rejected_shallow": 0, "rejected_checks": 0,
                         "n_health_not_scored": 0,
                         "dip_source": "precomputed", "rows": [{"t": i} for i in range(7)]})
        line = self._unmeasured_line(rep)
        self.assertIn("PASS", line)
        self.assertIn("3 of 10", line)
        # AND THE IDENTITY STILL HOLDS -- 10 = 7 + 3 + 0 + 0. An unmeasured name is counted,
        # not lost, so the accounting is provable even where the feed has gaps.
        self.assertIn("PASS", self._line(rep))

    def test_EVERYTHING_unmeasured_still_FAILS(self):
        """The partial-wiring failure the zero-demand was really for: 229 names once raised the
        same error and each was counted 'unmeasured', which read as a data gap."""
        rep = self._run({"n_eligible": 10, "n_qualified_on_depth": 10, "n_measured": 10,
                         "capped": 0, "n_unmeasured": 10, "rejected_health": 0,
                         "rejected_shallow": 0, "rejected_checks": 0,
                         "n_health_not_scored": 0,
                         "dip_source": "precomputed", "rows": []})
        line = self._unmeasured_line(rep)
        self.assertIn("FAIL", line)
        self.assertIn("wiring failure", line)

    def test_an_ABSENT_unmeasured_counter_fails(self):
        """Absent is not zero: without it an unmeasured name cannot be told from a name that is
        not in a drawdown, which is the whole distinction."""
        rep = self._run({"n_eligible": 10, "n_qualified_on_depth": 10, "n_measured": 10,
                         "capped": 0, "rejected_health": 3, "rejected_shallow": 0,
                         "rejected_checks": 0, "n_health_not_scored": 0,
                         "dip_source": "precomputed",
                         "rows": [{"t": 1}]})
        self.assertTrue(any("FAIL" in ln and "unmeasured" in ln for ln in rep.lines), rep.lines)


class TheThirdGroupIsPartOfTheAccounting(unittest.TestCase):
    """Don's 2026-10-07 ruling, from the check's side.

    The hazard a new display group introduces is not a wrong number on the page -- it is a name
    that stops being counted. `rejected_health` going DOWN is what an improvement looks like,
    so the only thing that can tell the two apart is the identity, and the identity can only do
    it if the new bucket is REQUIRED rather than defaulted to zero.
    """

    def _run(self, payload):
        rep = LC.Report()
        with _Net({("GET", "/api/dip"): _j(payload)}):
            LC.check_dip("https://x", rep)
        return rep

    def _line(self, rep):
        return [ln for ln in rep.lines if "every qualifying name" in ln][0]

    BASE = {"n_eligible": 50, "n_qualified_on_depth": 20, "n_measured": 20, "capped": 0,
            "n_unmeasured": 0, "rejected_health": 10, "rejected_shallow": 4,
            "rejected_checks": 0, "n_health_not_scored": 4,
            "n_health_not_scored_shallow": 2, "dip_source": "precomputed",
            "rows": [{"t": 1}, {"t": 2}]}

    def test_a_payload_with_an_excused_group_adds_up(self):
        rep = self._run(dict(self.BASE))              # 20 = 2 + 0 + 10 + 4 + 4
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_an_ABSENT_group_counter_cannot_be_checked(self):
        """ABSENT IS NOT ZERO, and this is the live state on the day of the deploy.

        The stored precompute predates the field, so the group is empty -- but a check that
        READ the absence as zero would also pass on a deployed screen that had the group and
        was not reporting it, which is the failure that matters.
        """
        p = dict(self.BASE)
        del p["n_health_not_scored"]
        p["rejected_health"] = 14                     # the OLD accounting: 20 = 2+0+14+4
        rep = self._run(p)
        self.assertIn("cannot be checked", self._line(rep))
        self.assertIn("n_health_not_scored", self._line(rep))

    def test_a_group_the_identity_does_not_account_for_FAILS(self):
        """The silent drop, simulated: names left `rejected_health` and nothing counted them."""
        p = dict(self.BASE)
        p["rejected_health"] = 14                     # as if the move had not been accounted
        rep = self._run(p)
        self.assertEqual(rep.failed, 1, rep.lines)
        self.assertIn("do not add up", self._line(rep))

    def test_the_shallow_subcount_is_printed_and_NOT_added(self):
        """It is a SUBSET of `rejected_shallow`; adding it would fail a correct screen -- the
        same trap `rejected_checks` sprang on the previous version of this check."""
        rep = self._run(dict(self.BASE))
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertIn("2 of the shallow were health-not-scored", self._line(rep))


class TheTrackRowIsNotMissingUntilItIsDue(unittest.TestCase):
    """`PT-GAPDUE` in a new place, and the third mis-specified assertion in this item.

    `track-row.yml` runs at 03:07 and 04:37 UTC Tue-Sat -- the MORNING AFTER a session, since
    a row needs that session's close. Run at 02:05 UTC this check reported FAIL for a session
    whose writer had not been scheduled yet. That is exactly what `gap_report` did before
    `PT-GAPDUE`: counted the current day as due from midnight, so a writer holding every row
    it could possibly have written still read false on 11 of 11 trading-day mornings.
    """

    def _run(self, series_dates, session, now):
        import datetime as dt
        rep = LC.Report()
        payload = _j({"series": [{"date": d} for d in series_dates]})
        real = LC._utcnow
        LC._utcnow = lambda: now
        try:
            with _Net({("GET", "/api/index-track"): payload}):
                LC.check_index_track("https://x", rep, dt.date.fromisoformat(session))
        finally:
            LC._utcnow = real
        return rep

    def test_a_row_that_is_present_passes(self):
        import datetime as dt
        rep = self._run(["2026-10-05", "2026-10-06"], "2026-10-06",
                        dt.datetime(2026, 10, 7, 2, 5, tzinfo=dt.timezone.utc))
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_before_the_deadline_it_requires_the_session_BEFORE_rather_than_skipping(self):
        """ITEM 35(b). The first cut SKIPPED here, and a skip asserts nothing.

        `track-row.yml` is delivered 09:00-11:00 UTC, so the last session's row is genuinely
        not due at 02:15. But the one before it IS, so there is always something to assert --
        and a writer that died a week ago must not pass a check just because it ran early.
        """
        import datetime as dt
        rep = self._run(["2026-10-02", "2026-10-05"], "2026-10-06",
                        dt.datetime(2026, 10, 7, 2, 5, tzinfo=dt.timezone.utc))
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.skipped, 0, "a skip here asserts nothing: %s" % rep.lines)
        line = [ln for ln in rep.lines if "last session" in ln][0]
        self.assertIn("PASS", line)
        self.assertIn("row for 2026-10-05", line)
        self.assertIn("not due until", line)

    def test_a_WRITER_THAT_STOPPED_A_WEEK_AGO_FAILS_EVEN_BEFORE_THE_DEADLINE(self):
        """The half the skip version could not catch, and the reason the fallback exists."""
        import datetime as dt
        rep = self._run(["2026-09-25"], "2026-10-06",
                        dt.datetime(2026, 10, 7, 2, 5, tzinfo=dt.timezone.utc))
        self.assertEqual(rep.failed, 1, rep.lines)
        line = [ln for ln in rep.lines if "last session" in ln][0]
        self.assertIn("no row for 2026-10-05 EITHER", line)

    def test_an_absent_row_AFTER_the_writer_runs_still_FAILS(self):
        """The half that matters: the deadline must not make the check unfailable."""
        import datetime as dt
        rep = self._run(["2026-10-05"], "2026-10-06",
                        dt.datetime(2026, 10, 7, 13, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(rep.failed, 1, rep.lines)
        line = [ln for ln in rep.lines if "last session" in ln][0]
        self.assertIn("FAIL", line)
        self.assertIn("no row for 2026-10-06", line)

    def test_the_deadline_is_after_the_backup_cron_rather_than_the_first_one(self):
        """A deadline set to the FIRST cron would fail whenever GitHub delays a free run --
        which is the reason that workflow carries a backup cron in the first place."""
        import datetime as dt
        due = LC._track_row_due_after(dt.date(2026, 10, 6))
        self.assertEqual(due.date(), dt.date(2026, 10, 7), "due the morning AFTER the session")
        # PAST THE DELIVERY WINDOW, NOT THE CRON TIME. The crons are 03:07 and 04:37 UTC and
        # GitHub's free scheduler delivers them 09:00-11:00; a deadline at the cron time fires
        # most mornings on a writer that is working, which is what the first cut (05:30) did.
        self.assertGreaterEqual((due.hour, due.minute), (12, 0))


class TheExportCheckJudgesTheFileType(unittest.TestCase):
    """A 200 carrying a JSON error is non-empty, so length alone would pass a broken export."""

    def _table(self, xlsx, pdf):
        return {("GET", "/api/export/excel"): xlsx, ("GET", "/api/export/pdf"): pdf}

    def test_real_files_pass(self):
        xlsx = (200, b"PK\x03\x04" + b"x" * 5000, "application/octet-stream")
        pdf = (200, b"%PDF-1.7" + b"x" * 5000, "application/pdf")
        rep = LC.Report()
        with _Net(self._table(xlsx, pdf)):
            LC.check_exports("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_a_json_error_served_with_200_FAILS(self):
        """THE WHOLE POINT. `{"error": ...}` is non-empty and is not a spreadsheet."""
        err = (200, json.dumps({"error": "boom"}).encode("utf-8") + b" " * 5000,
               "application/json")
        rep = LC.Report()
        with _Net(self._table(err, err)):
            LC.check_exports("https://x", rep)
        self.assertEqual(rep.failed, 2, rep.lines)

    def test_a_truncated_file_fails(self):
        """A 40-byte xlsx has the right magic and is not a workbook."""
        tiny = (200, b"PK\x03\x04tiny", "application/octet-stream")
        rep = LC.Report()
        with _Net(self._table(tiny, tiny)):
            LC.check_exports("https://x", rep)
        self.assertEqual(rep.failed, 2, rep.lines)


class TheValuationChecks(unittest.TestCase):
    def _ok(self, fv, regime="mature"):
        return _j({"base_fair_value": fv, "classification": {"regime": regime}})

    def _table(self, zzzzq):
        t = {}
        for tk in ("MSFT", "O", "NEE", "BRK.B"):
            t[("POST", "/api/value", json.dumps({"ticker": tk}, sort_keys=True))] = \
                self._ok(100.0)
        t[("POST", "/api/value", json.dumps({"ticker": "ZZZZQ"}, sort_keys=True))] = zzzzq
        return t

    def test_four_real_names_and_a_refused_one_pass(self):
        rep = LC.Report()
        with _Net(self._table(_j({"error": "ticker not found"}, code=404))):
            LC.check_valuations("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.passed, 5)

    def test_a_200_with_a_score_for_a_nonexistent_ticker_FAILS(self):
        """THE DEFECT: HTTP 200, score 40, recommendation "Reduce", for no company at all."""
        bad = _j({"score": {"score": 40, "recommendation": "Reduce"}})
        rep = LC.Report()
        with _Net(self._table(bad)):
            LC.check_valuations("https://x", rep)
        line = [ln for ln in rep.lines if "ZZZZQ" in ln][0]
        self.assertIn("FAIL", line)

    def test_a_missing_fair_value_fails(self):
        t = self._table(_j({"error": "x"}, code=404))
        t[("POST", "/api/value", json.dumps({"ticker": "O"}, sort_keys=True))] = \
            _j({"base_fair_value": None})
        rep = LC.Report()
        with _Net(t):
            LC.check_valuations("https://x", rep)
        self.assertTrue(any("FAIL" in ln and " O " in ln for ln in rep.lines), rep.lines)


class TheAlertSurfacesAreComparedToEachOther(unittest.TestCase):
    def test_agreement_passes(self):
        rep = LC.Report()
        with _Net({("GET", "/api/scream-track"): _j({"n_live": 15}),
                   ("GET", "/api/options-scorecard"): _j({"n_open": 15})}):
            LC.check_alert_surfaces("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_the_live_disagreement_fails(self):
        """23 vs 15 — exactly the 8 rows one surface was mis-classifying."""
        rep = LC.Report()
        with _Net({("GET", "/api/scream-track"): _j({"n_live": 23}),
                   ("GET", "/api/options-scorecard"): _j({"n_open": 15})}):
            LC.check_alert_surfaces("https://x", rep)
        line = [ln for ln in rep.lines if "agrees" in ln][0]
        self.assertIn("FAIL", line)
        self.assertIn("23", line)
        self.assertIn("15", line)

    def test_it_compares_rather_than_asserting_a_constant(self):
        """Both surfaces moving together must PASS, or the checker goes stale the first time a
        real alert closes and somebody edits a number in here instead of reading the site."""
        rep = LC.Report()
        with _Net({("GET", "/api/scream-track"): _j({"n_live": 4}),
                   ("GET", "/api/options-scorecard"): _j({"n_open": 4})}):
            LC.check_alert_surfaces("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)


class TheIndexChecks(unittest.TestCase):
    def _payload(self, n=85, weights=None):
        ws = weights if weights is not None else [1.0 / 86] * 86
        return {"is_preview": False, "n_positions": n,
                "card": {"is_tracked_construction": True, "construction": "taxable"},
                "positions": [{"ticker": "T%d" % i, "weight": w} for i, w in enumerate(ws)]}

    def test_a_preview_payload_fails(self):
        d = self._payload()
        d["is_preview"] = True
        d["card"]["is_tracked_construction"] = False
        rep = LC.Report()
        with _Net({("GET", "/api/valquo-index"): _j(d)}):
            LC.check_index("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "book in force" in ln for ln in rep.lines),
                        rep.lines)

    def test_a_short_book_fails(self):
        rep = LC.Report()
        with _Net({("GET", "/api/valquo-index"): _j(self._payload(n=10))}):
            LC.check_index("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "85+" in ln for ln in rep.lines), rep.lines)

    def test_weights_that_do_not_sum_to_one_fail(self):
        rep = LC.Report()
        with _Net({("GET", "/api/valquo-index"): _j(self._payload(weights=[0.1] * 3))}):
            LC.check_index("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "sum to 1" in ln for ln in rep.lines), rep.lines)


class TheFreshnessUsesTheMarketCalendar(unittest.TestCase):
    def test_a_holiday_is_not_a_trading_day(self):
        """So the signals check SKIPS rather than failing on Thanksgiving."""
        from valuation.screener import market_session as MS
        # US Thanksgiving 2026.
        self.assertFalse(MS.is_trading_day(_dt.date(2026, 11, 26)))

    def test_the_signals_check_skips_on_a_non_trading_day(self):
        rep = LC.Report()
        sunday = _dt.datetime(2026, 10, 4, 18, 0)
        with _Net({("GET", "/api/signals"): _j({"run_time": "2026-10-02 23:08",
                                                "rows": [{"t": 1}]})}):
            LC.check_signals("https://x", rep, sunday)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.skipped, 1, rep.lines)

    def test_a_stale_run_time_fails_during_a_session(self):
        rep = LC.Report()
        # A Monday, inside the UTC band the checker uses.
        monday = _dt.datetime(2026, 10, 5, 13, 45)
        with _Net({("GET", "/api/signals"): _j({"run_time": "2026-10-02 23:08",
                                                "rows": [{"t": 1}]})}):
            LC.check_signals("https://x", rep, monday)
        self.assertTrue(any("FAIL" in ln and "today's session" in ln for ln in rep.lines),
                        rep.lines)

    def test_a_fresh_run_time_passes_during_a_session(self):
        rep = LC.Report()
        monday = _dt.datetime(2026, 10, 5, 13, 45)
        with _Net({("GET", "/api/signals"): _j({"run_time": "2026-10-05 13:23",
                                                "rows": [{"t": 1}]})}):
            LC.check_signals("https://x", rep, monday)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.skipped, 0, rep.lines)

    def test_an_empty_feed_fails_rather_than_skipping(self):
        """`empty: True` is the feed saying it has never run, which is a failure and not a
        reason to stand down."""
        rep = LC.Report()
        with _Net({("GET", "/api/signals"): _j({"empty": True, "message": "no scan yet"})}):
            LC.check_signals("https://x", rep, _dt.datetime(2026, 10, 5, 13, 45))
        self.assertEqual(rep.failed, 1, rep.lines)


class AnUnreachableSiteFailsRatherThanRaising(unittest.TestCase):
    """A connection error must produce a FAIL line, not a traceback — a crashed checker and a
    broken site look the same in a scheduler, and only one of them is actionable."""

    def test_every_check_survives_a_dead_host(self):
        rep = LC.Report()
        dead = (0, b"URLError: refused", "")
        table = {("GET", p): dead for p in
                 ("/api/hotstocks", "/api/dip", "/api/valquo-index", "/api/index-track",
                  "/api/scream-track", "/api/options-scorecard", "/api/signals",
                  "/api/export/excel", "/api/export/pdf", "/proof", "/methodology")}
        with _Net(table):
            LC.check_hot_list("https://x", rep, SESSION)
            LC.check_dip("https://x", rep)
            LC.check_index("https://x", rep)
            LC.check_index_track("https://x", rep, SESSION)
            LC.check_alert_surfaces("https://x", rep)
            LC.check_exports("https://x", rep)
            LC.check_pages("https://x", rep)
        self.assertGreater(rep.failed, 5, rep.lines)
        self.assertEqual(rep.finish(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
