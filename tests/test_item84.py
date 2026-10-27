"""Item 84 — the refresh rebuilt the prices and not the fundamentals; and a dropped cron.

PART A, MEASURED ON THE 2026-10-23 FREEZE ITSELF:

  * `fundamentals.csv`, `insiders.csv` and `institutional.csv` were all stamped **2026-10-04
    15:20-15:22** while every raw source was stamped **2026-10-23 19:01-19:29**;
  * the manifest's `derive_stats` read `fundamentals_rows: null, fundamentals_tickers: 0`,
    which is the exact signature of `stage_derive` SKIPPING all three -- `f_rows`/`i_rows`/
    `n_rows` keep their initial `None` when `done()` returns True;
  * `universe.txt` IS stamped 10-23, because it is written outside that guard -- so the stage
    ran and only the derives were skipped;
  * the manifest recorded `derived["fundamentals.csv"].date_max = 2026-10-02` and
    `tables["SF1"].date_max = 2026-10-22` **side by side, and nothing compared them**;
  * `refresh_backtest_from_freeze` proved only that the newest CLOSE moved, and prices are
    rebuilt unconditionally -- so it printed SUCCESS over a stale derive.

It is item 81's defect one stage over. Item 81 fixed `prepare`'s cache-first skip; `derive` had
the identical rule and was not looked at.

PART B: GitHub delivered NEITHER hot-list cron on 2026-10-26, so the public list stayed at the
10-23 scan. Three OTHER crons were delivered that night after the close (`intraday` 23:57Z,
`paper` 00:05Z, `recap` 00:08Z), which is what the catch-up rides on.

`scripts/i84_before.py` measures which of these fail against the pre-change tree.
"""
import ast
import datetime as dt
import io
import os
import re
import shutil
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import refresh_backtest_from_freeze as RS                     # noqa: E402
from valuation.edge import sharadar_freeze as F               # noqa: E402
from valuation.edge import valquo_index as V                  # noqa: E402
from valuation.screener import scan_catchup as SC             # noqa: E402

# ITEM 74's TEXT PARSER FOR THESE FILES, REUSED RATHER THAN REBUILT -- see
# `ThePendingWorkflowIsInstallable` for the CI defect that forced it.
import test_item74 as I74                                     # noqa: E402

WORKFLOW = os.path.join(REPO, "pending_workflows", "auto-scan.yml")


def _touch(path, text="x", mtime=None):
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


OLD = dt.datetime(2026, 10, 4, 15, 20).timestamp()
NEW = dt.datetime(2026, 10, 23, 19, 3).timestamp()


# ============================================================ PART A -- the derive skip
class ADerivedFileOlderThanItsSourceIsStale(unittest.TestCase):
    """The rule, and it is ONE definition shared by `derive` and `prepare` (`B7`)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_a_source_newer_than_its_derived_file_is_stale(self):
        d, s = os.path.join(self.d, "out.csv"), os.path.join(self.d, "src.csv")
        _touch(d, mtime=OLD)
        _touch(s, mtime=NEW)
        self.assertTrue(F._stale_vs_source(d, s))

    def test_a_derived_file_newer_than_its_source_is_not(self):
        d, s = os.path.join(self.d, "out.csv"), os.path.join(self.d, "src.csv")
        _touch(s, mtime=OLD)
        _touch(d, mtime=NEW)
        self.assertFalse(F._stale_vs_source(d, s))

    def test_an_absent_file_on_either_side_is_not_stale(self):
        """Absent is absent, not stale -- every builder builds it either way."""
        d, s = os.path.join(self.d, "out.csv"), os.path.join(self.d, "src.csv")
        self.assertFalse(F._stale_vs_source(d, s))
        _touch(d, mtime=OLD)
        self.assertFalse(F._stale_vs_source(d, s), "no source means nothing newer to rebuild")
        os.remove(d)
        _touch(s, mtime=NEW)
        self.assertFalse(F._stale_vs_source(d, s))

    def test_item_81s_prepare_rule_now_delegates_to_it(self):
        """One rule, two stages. Two copies is how the second one gets missed."""
        cache, bulk = os.path.join(self.d, "c"), os.path.join(self.d, "b")
        os.makedirs(cache)
        os.makedirs(bulk)
        _touch(os.path.join(cache, "daily.pkl"), mtime=OLD)
        _touch(os.path.join(bulk, "daily.csv"), mtime=NEW)
        self.assertTrue(F._prepare_stale(cache, bulk, "daily", "daily.csv"))

    def test_the_unlock_helper_lifts_a_read_only_bit(self):
        """A freeze is locked read-only, so a rebuild needs this or it raises PermissionError."""
        p = os.path.join(self.d, "locked.csv")
        _touch(p)
        os.chmod(p, stat.S_IREAD)
        F._unlock(p)
        with io.open(p, "w", encoding="utf-8") as f:       # must not raise
            f.write("rewritten")
        self.assertEqual(io.open(p, encoding="utf-8").read(), "rewritten")


class TheDeriveStageRebuildsAStaleTable(unittest.TestCase):
    """`done()` must mean "built from the data now on disk", not merely "a file is there"."""

    def test_done_is_false_when_the_source_is_newer(self):
        """READ OFF THE SOURCE, because building a whole fake freeze would test the fake.

        What must hold is that `done()` consults `_stale_vs_source` and that the three derived
        files are mapped to the raw tables they come from. Both are structural.
        """
        src = io.open(os.path.join(REPO, "valuation", "edge", "sharadar_freeze.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "stage_derive")
        inner = [n for n in ast.walk(fn)
                 if isinstance(n, ast.FunctionDef) and n.name == "done"]
        self.assertEqual(len(inner), 1, "stage_derive should define exactly one done()")
        calls = [ast.unparse(c.func) for c in ast.walk(inner[0]) if isinstance(c, ast.Call)]
        self.assertIn("_stale_vs_source", calls,
                      "done() no longer asks whether the source is newer")
        self.assertIn("_unlock", calls, "a rebuild must lift the freeze's read-only bit")

    def test_all_three_tables_are_mapped_to_their_raw_source(self):
        src = io.open(os.path.join(REPO, "valuation", "edge", "sharadar_freeze.py"),
                      encoding="utf-8").read()
        for pair in ('"fundamentals.csv": "sf1.csv"', '"insiders.csv": "sf2.csv"',
                     '"institutional.csv": "sf3a.csv"'):
            self.assertIn(pair, src, pair)

    def test_the_unconditional_writes_unlock_first(self):
        """FOUND BY RUNNING IT: the stage could not run twice against a locked freeze.

        It died on `universe.txt` before reaching any table, and then on the price purge after
        the three tables had already rebuilt. Three unconditional writes, three lock lifts.
        """
        src = io.open(os.path.join(REPO, "valuation", "edge", "sharadar_freeze.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "stage_derive")
        unlocks = [c for c in ast.walk(fn)
                   if isinstance(c, ast.Call) and ast.unparse(c.func) == "_unlock"]
        self.assertGreaterEqual(len(unlocks), 3,
                                "universe.txt, the derived tables and the price purge each "
                                "need the read-only bit lifted; found %d" % len(unlocks))


class TheManifestComparesWhatItAlreadyRecorded(unittest.TestCase):
    """The two numbers were in the file side by side and nothing read them (`rule 9`'s shape)."""

    def _check(self, derived_max, source_max):
        """The checkpoint's own arithmetic, driven as the manifest stage drives it."""
        gap = None
        if derived_max and source_max:
            try:
                gap = (dt.date.fromisoformat(source_max)
                       - dt.date.fromisoformat(derived_max)).days
            except ValueError:
                gap = None
        return bool(derived_max and source_max and gap is not None
                    and -1 <= gap <= F.DERIVED_REACH_DAYS)

    def test_the_real_october_freeze_would_have_FAILED(self):
        """fundamentals 2026-10-02 against SF1's 2026-10-22: twenty days."""
        self.assertFalse(self._check("2026-10-02", "2026-10-22"))

    def test_a_healthy_freeze_passes(self):
        self.assertTrue(self._check("2026-10-22", "2026-10-22"))
        self.assertTrue(self._check("2026-10-20", "2026-10-22"))

    def test_the_quarterly_13f_table_passes_at_its_own_span(self):
        """MEASURED: SF3A's own date_max is also 2026-09-30, so 13F was never stale in
        substance. A bar that failed it would refuse every correct export between quarters."""
        self.assertTrue(self._check("2026-09-30", "2026-09-30"))

    def test_a_missing_date_FAILS_rather_than_passing_quietly(self):
        """`C5`. `_scan_csv` returns no `date_max` for a renamed column -- which has happened
        here -- and reading absent as "in range" makes the guard silent exactly when needed."""
        self.assertFalse(self._check(None, "2026-10-22"))
        self.assertFalse(self._check("2026-10-02", None))

    def test_the_bar_is_a_committed_literal(self):
        self.assertEqual(F.DERIVED_REACH_DAYS, 3)

    def test_the_checkpoint_is_appended_where_both_numbers_are_in_scope(self):
        """`_checkpoints(root)` takes only a path and cannot see them, so the comparison has
        to live in `stage_manifest`, after `derived` is built."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "sharadar_freeze.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "stage_manifest")
        # STRUCTURAL, ON LINE NUMBERS. My first cut searched `ast.unparse(fn)` for
        # `man["checkpoints"] = ...` and raised `ValueError: substring not found`, because
        # unparse normalises quotes to single ones -- the substring-match family again, in
        # my own test. Line numbers cannot be reformatted.
        assign = next(n.lineno for n in ast.walk(fn)
                      if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Subscript)
                              and getattr(t.slice, "value", None) == "checkpoints"
                              for t in n.targets))
        reach = next(n.lineno for n in ast.walk(fn)
                     if isinstance(n, ast.Name) and n.id == "DERIVED_REACH_DAYS")
        self.assertLess(assign, reach,
                        "the reach check must APPEND to the checkpoint list, so it has to "
                        "come after the list is built, not before it")


class TheRefreshFailsLoudlyOnAStaleDerive(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.bt = os.path.join(self.d, "backtest")
        self.bulk = os.path.join(self.d, "bulk")
        os.makedirs(self.bt)
        os.makedirs(self.bulk)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_it_names_every_stale_table_and_both_dates(self):
        for derived, src in RS.DERIVED_SOURCES.items():
            _touch(os.path.join(self.bt, derived), mtime=OLD)
            _touch(os.path.join(self.bulk, src), mtime=NEW)
        bad = RS.derived_is_stale(self.d)
        self.assertEqual(len(bad), 3, bad)
        names = sorted(b[0] for b in bad)
        self.assertEqual(names, ["fundamentals.csv", "insiders.csv", "institutional.csv"])
        for _n, _s, dstamp, sstamp in bad:
            self.assertIn("2026-10-04", dstamp)
            self.assertIn("2026-10-23", sstamp)

    def test_a_healthy_freeze_reports_nothing(self):
        for derived, src in RS.DERIVED_SOURCES.items():
            _touch(os.path.join(self.bulk, src), mtime=OLD)
            _touch(os.path.join(self.bt, derived), mtime=NEW)
        self.assertEqual(RS.derived_is_stale(self.d), [])

    def test_mtime_and_not_content_is_the_right_test(self):
        """Freeze and live were BYTE-IDENTICAL on 2026-10-23, which is exactly why a size or
        checksum comparison could not see this. The question is which pull built it."""
        same = "identical bytes"
        _touch(os.path.join(self.bt, "fundamentals.csv"), text=same, mtime=OLD)
        _touch(os.path.join(self.bulk, "sf1.csv"), text=same, mtime=NEW)
        self.assertTrue(RS.derived_is_stale(self.d))


class TheManifestVerdictGate(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _man(self, **verdict):
        import json
        with io.open(os.path.join(self.d, "MANIFEST.json"), "w", encoding="utf-8") as f:
            json.dump({"created": "2026-10-23T20:00:05", "verdict": verdict}, f)

    def test_a_failed_checkpoint_is_read(self):
        self._man(clean=False, checkpoints_failed=["fundamentals.csv reaches its source (SF1)"],
                  tables_short_vs_live=[])
        got = RS.manifest_verdict(self.d)
        self.assertEqual(got["checkpoints_failed"],
                         ["fundamentals.csv reaches its source (SF1)"])

    def test_a_size_shrink_alone_is_reported_and_not_fatal(self):
        """MEASURED ON THE REAL FREEZE: `clean` was already false, and ONLY because two bulk
        CSVs came back 0.259% and 0.099% smaller than July's. Failing on the raw flag would
        refuse a correct refresh every time the vendor trims history (`MA21`)."""
        self._man(clean=False, checkpoints_failed=[],
                  tables_short_vs_live=["bulk/events.csv size", "bulk/daily.csv size"])
        got = RS.manifest_verdict(self.d)
        self.assertEqual(got["checkpoints_failed"], [])
        self.assertEqual(len(got["tables_short_vs_live"]), 2)

    def test_an_absent_manifest_is_a_failure_and_not_a_pass(self):
        got = RS.manifest_verdict(self.d)
        self.assertFalse(got["present"])
        self.assertIn("MANIFEST.json", got["reason"])

    def test_an_unreadable_manifest_is_a_failure(self):
        with io.open(os.path.join(self.d, "MANIFEST.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        got = RS.manifest_verdict(self.d)
        self.assertIsNotNone(got["reason"])

    def test_the_sync_refuses_before_it_copies_anything(self):
        """A stale table must never be installed over the live export; order matters."""
        src = io.open(os.path.join(REPO, "scripts", "refresh_backtest_from_freeze.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        body = ast.unparse(fn)
        self.assertLess(body.index("derived_is_stale"), body.index("shutil.copy2"),
                        "the staleness gate must precede the copy")
        self.assertLess(body.index("manifest_verdict"), body.index("shutil.copy2"))


# ============================================================ PART A -- the build's refusal
class TheBuildRefusesStaleFundamentals(unittest.TestCase):
    def _v(self, date, **kw):
        rec = {"present": True, "date": date, "rows": 232636, "column": "datekey"}
        rec.update(kw)
        return {"fundamentals.csv": rec}

    def test_the_october_book_would_have_been_refused(self):
        msg = V.refuse_stale_fundamentals(self._v("2026-10-02"), "2026-10-22")
        self.assertIsNotNone(msg)
        self.assertIn("2026-10-02", msg)
        self.assertIn("refresh_sharadar.bat", msg, "the refusal must name the remedy")

    def test_a_current_export_passes(self):
        self.assertIsNone(V.refuse_stale_fundamentals(self._v("2026-10-22"), "2026-10-22"))

    def test_a_filing_lull_inside_the_bar_passes(self):
        """The bar is 10 trading days, not 5, BECAUSE A FILING ARRIVES WHEN A COMPANY CHOOSES.
        Between earnings seasons a perfectly current export's newest datekey sits a week back,
        and a five-day bar would refuse it."""
        self.assertIsNone(V.refuse_stale_fundamentals(self._v("2026-10-08"), "2026-10-22"))
        self.assertEqual(V.MAX_FUNDAMENTALS_STALE_DAYS, 10)
        self.assertGreater(V.MAX_FUNDAMENTALS_STALE_DAYS, V.MAX_DAILY_CACHE_STALE_DAYS,
                           "a filing date is lumpier than a market cap and needs more room")

    def test_it_cannot_fire_on_a_historical_build(self):
        self.assertIsNone(V.refuse_stale_fundamentals(self._v("2026-10-02"), "2009-01-15"))

    def test_no_as_of_does_not_refuse(self):
        self.assertIsNone(V.refuse_stale_fundamentals(self._v("2026-10-02"), None))

    def test_an_unreadable_date_refuses_rather_than_passing(self):
        msg = V.refuse_stale_fundamentals(self._v(None, note="no date column"), "2026-10-22")
        self.assertIsNotNone(msg)

    def test_an_absent_file_refuses(self):
        msg = V.refuse_stale_fundamentals({"fundamentals.csv": {"present": False}},
                                          "2026-10-22")
        self.assertIsNotNone(msg)

    def test_only_fundamentals_gates_and_the_reason_is_measured(self):
        """13F is QUARTERLY -- SF3A's own span ends 2026-09-30 and that export is current -- so
        gating on it would refuse every correct build outside the filing window."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "valquo_index.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "refuse_stale_fundamentals")
        body = ast.unparse(fn)
        self.assertIn("fundamentals.csv", body)
        self.assertNotIn('"institutional.csv"', body.replace(
            ast.get_docstring(fn) or "", ""), "13F must not gate the build")


class TheExportVintagesAreReported(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_it_reads_the_newest_date_from_each_table(self):
        with io.open(os.path.join(self.d, "fundamentals.csv"), "w", encoding="utf-8") as f:
            f.write("ticker,datekey\nAAA,2026-10-02\nBBB,2026-10-22\nCCC,2026-09-30\n")
        got = V.export_vintages(self.d)["fundamentals.csv"]
        self.assertEqual(got["date"], "2026-10-22")
        self.assertEqual(got["rows"], 3)
        self.assertEqual(got["column"], "datekey")

    def test_the_newest_is_not_assumed_to_be_at_the_tail(self):
        """SF1 is ordered by TICKER then date, so the newest filing is mid-file."""
        with io.open(os.path.join(self.d, "fundamentals.csv"), "w", encoding="utf-8") as f:
            f.write("ticker,datekey\nAAA,2026-10-22\nZZZ,2026-01-01\n")
        self.assertEqual(V.export_vintages(self.d)["fundamentals.csv"]["date"], "2026-10-22")

    def test_both_13f_spellings_are_accepted(self):
        """SF3A renamed `calendardate` -> `date` between exports and a single hard-coded name
        made an earlier manifest report NO DATE for three tables."""
        for col in ("calendardate", "date"):
            with io.open(os.path.join(self.d, "institutional.csv"), "w", encoding="utf-8") as f:
                f.write("ticker,%s\nAAA,2026-09-30\n" % col)
            got = V.export_vintages(self.d)["institutional.csv"]
            self.assertEqual((got["date"], got["column"]), ("2026-09-30", col))

    def test_an_absent_table_is_reported_absent_and_not_as_a_date(self):
        got = V.export_vintages(self.d)["fundamentals.csv"]
        self.assertFalse(got["present"])
        self.assertIsNone(got["date"])

    def test_a_table_with_no_date_column_says_so(self):
        with io.open(os.path.join(self.d, "fundamentals.csv"), "w", encoding="utf-8") as f:
            f.write("ticker,revenue\nAAA,5\n")
        got = V.export_vintages(self.d)["fundamentals.csv"]
        self.assertIsNone(got["date"])
        self.assertIn("no date column", got["note"])

    def test_the_payload_names_what_each_input_reached(self):
        """`data_as_of` is the session REQUESTED; on 2026-10-22 it read 2026-10-22 while the
        inputs stopped at 10-02. Both true, and the payload carried only the flattering one."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "valquo_index.py"),
                      encoding="utf-8").read()
        self.assertIn('payload["data_as_of_inputs"] = _vintages', src)
        self.assertIn("_vintages = None", src,
                      "the live-scan path reads no export and must not claim one")


# ============================================================ PART B -- the dropped cron
class TheCatchupDecision(unittest.TestCase):
    MON_EVE = dt.datetime(2026, 10, 26, 20, 8)        # 00:08Z Tue, when `recap` fired

    def test_the_real_2026_10_26_miss_runs(self):
        got = SC.catchup_decision("2026-10-23", now=self.MON_EVE)
        self.assertTrue(got["run"], got)
        self.assertEqual(got["target"], "2026-10-26")
        self.assertEqual(got["behind_trading_days"], 1)

    def test_an_already_current_list_is_not_rescanned(self):
        """IDEMPOTENT PER SESSION: ten delivered crons produce at most one scan."""
        got = SC.catchup_decision("2026-10-26", now=self.MON_EVE)
        self.assertFalse(got["run"], got)
        self.assertIn("nothing to catch up", got["reason"])

    def test_it_refuses_while_the_market_is_open(self):
        """THE CONDITION THAT CANNOT BE RELAXED. A scan now would publish live quotes as the
        previous session's closes."""
        got = SC.catchup_decision("2026-10-23", now=dt.datetime(2026, 10, 27, 11, 0))
        self.assertFalse(got["run"], got)
        self.assertIn("INTRADAY", got["reason"])
        self.assertTrue(got["market_open"])

    def test_before_the_open_is_safe(self):
        got = SC.catchup_decision("2026-10-23", now=dt.datetime(2026, 10, 27, 8, 30))
        self.assertTrue(got["run"], got)

    def test_after_the_close_is_safe(self):
        got = SC.catchup_decision("2026-10-23", now=dt.datetime(2026, 10, 27, 16, 30))
        self.assertTrue(got["run"], got)

    def test_an_unreadable_scan_date_scans(self):
        """`C5`: "the feed does not say" is not evidence that it is current. One extra scan is
        cheaper than another stale day, and the open-market guard still holds."""
        got = SC.catchup_decision(None, now=self.MON_EVE)
        self.assertTrue(got["run"], got)

    def test_a_list_ahead_of_the_last_close_is_left_alone(self):
        got = SC.catchup_decision("2026-10-27", now=self.MON_EVE)
        self.assertFalse(got["run"], got)

    def test_the_market_hours_boundaries(self):
        self.assertFalse(SC.market_is_open(dt.datetime(2026, 10, 27, 9, 29)))
        self.assertTrue(SC.market_is_open(dt.datetime(2026, 10, 27, 9, 30)))
        self.assertTrue(SC.market_is_open(dt.datetime(2026, 10, 27, 16, 14)))
        self.assertFalse(SC.market_is_open(dt.datetime(2026, 10, 27, 16, 15)))

    def test_a_weekend_is_never_open(self):
        self.assertFalse(SC.market_is_open(dt.datetime(2026, 10, 24, 12, 0)))

    def test_a_holiday_is_never_open(self):
        from valuation.screener.market_session import market_holidays
        hol = sorted(market_holidays(2026))[0]
        self.assertFalse(SC.market_is_open(dt.datetime(hol.year, hol.month, hol.day, 12, 0)))

    def test_without_a_timezone_it_refuses_rather_than_risking_an_intraday_scan(self):
        """`now_et` falls back to NAIVE UTC without tzdata, and a UTC clock against ET market
        hours is wrong by four hours -- which would permit a scan at 14:00 UTC, mid-session."""
        real = SC.MS.now_et
        try:
            SC.MS.now_et = lambda: dt.datetime(2026, 10, 27, 14, 0)     # naive == no tzdata
            got = SC.catchup_decision("2026-10-23")
            self.assertFalse(got["run"], got)
            self.assertIn("timezone", got["reason"])
        finally:
            SC.MS.now_et = real

    def test_the_cli_exits_zero_to_run_and_one_to_skip(self):
        self.assertEqual(SC.main(["--scan-date", "2026-10-23",
                                  "--now", "2026-10-26T20:08:00"]), 0)
        self.assertEqual(SC.main(["--scan-date", "2026-10-26",
                                  "--now", "2026-10-26T20:08:00"]), 1)

    def test_the_cli_reads_the_feed_on_stdin(self):
        """ONE LINE OF YAML. The first cut embedded multi-line Python in a block scalar, its
        lines de-indented to column 0, and the document stopped parsing."""
        import json
        old = sys.stdin
        try:
            sys.stdin = io.StringIO(json.dumps({"scan_date": "2026-10-23"}))
            self.assertEqual(SC.main(["--json-stdin", "--now", "2026-10-26T20:08:00"]), 0)
            sys.stdin = io.StringIO("not json at all")
            self.assertEqual(SC.main(["--json-stdin", "--now", "2026-10-26T20:08:00"]), 0,
                             "an unreadable reply must fail TOWARD scanning")
        finally:
            sys.stdin = old


class ThePendingWorkflowIsInstallable(unittest.TestCase):
    """`.github/` is refused by the land gate, so the change is handed over for Don to install.

    IN THE TRACKED `pending_workflows/`, NOT `data/pending_workflows/`, and that is the repo's
    own ruling (item 58b): a handover inside the gitignored `data/` "has existed only on this
    machine: unreviewable in the repo and unpinnable by any test". This class is the point.

    **PARSED WITH ITEM 74's OWN TEXT HELPERS AND NOT WITH PyYAML, AND THAT IS A DEFECT OF MINE
    THAT THE LAND CAUGHT.** My first cut imported `yaml`: the suite passed here and FAILED on
    the runner, because PyYAML is in neither `requirements.txt` nor `requirements.lock.txt` and
    is only incidentally installed on this machine. `wf_jobs`'s own docstring says so in terms --
    *"PyYAML IS NOT IN THE CI ENVIRONMENT, AND MY FIRST CUT IMPORTED IT ANYWAY ... I wrote a new
    one instead of reading the neighbouring suite"* -- which makes this the THIRD recorded
    instance of one mistake (item 65, item 74, this), and the lesson was already written down in
    a docstring I did not read. There is one text parser for these files and it is reused.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = I74._read_wf(WORKFLOW)
        cls.jobs = I74.wf_jobs(cls.text)
        # NON-VACUITY: a parser returning nothing would make every assertion below pass by
        # seeing nothing, which is how the version this replaces could have gone green.
        assert cls.jobs.get("hot"), "wf_jobs found no steps in the hot job"
        start = cls.text.index("\n  hot:")
        cls.hot_text = cls.text[start:cls.text.index("\n  themes:", start)]

    def test_it_is_in_the_tracked_handover_directory(self):
        self.assertTrue(os.path.exists(WORKFLOW))
        self.assertIn("pending_workflows", WORKFLOW)
        self.assertNotIn(os.path.join("data", "pending_workflows"), WORKFLOW)

    def test_every_scheduled_job_is_still_present(self):
        for job in ("hot", "intraday", "paper", "recap", "themes", "watchdog"):
            self.assertIn(job, self.jobs, sorted(self.jobs))

    def test_the_hot_job_no_longer_requires_one_of_two_cron_strings(self):
        """THE DEFECT. Gated on two exact strings, and GitHub delivered neither on 2026-10-26."""
        cond = next(ln for ln in self.hot_text.split("\n") if ln.startswith("    if:"))
        self.assertIn("github.event_name == 'schedule'", cond)
        self.assertNotIn("github.event.schedule == '23 22", cond,
                         "the job must start on any delivered schedule and then decide")

    def test_the_decision_runs_before_pip_and_gates_the_scan(self):
        steps = [n for n, _if in self.jobs["hot"]]
        dec = next(i for i, n in enumerate(steps) if "hot list behind" in n)
        self.assertLess(self.hot_text.index("hot list behind"),
                        self.hot_text.index("pip install --require-hashes"),
                        "a skip must cost seconds, not a dependency install")
        gated = [n for n, cond in self.jobs["hot"][dec + 1:]
                 if cond == "steps.decide.outputs.run == 'true'"]
        self.assertGreaterEqual(len(gated), 3, self.jobs["hot"])

    def test_the_scan_step_itself_is_gated(self):
        cond = dict(self.jobs["hot"])["Scan the market and push the daily hot list"]
        self.assertEqual(cond, "steps.decide.outputs.run == 'true'")

    def test_the_failure_notifier_keeps_its_own_condition(self):
        """A SECOND `if` ON ONE STEP IS A DUPLICATE MAPPING KEY, which a YAML loader tolerates
        by keeping the last and GitHub may reject outright."""
        cond = next(c for n, c in self.jobs["hot"] if "tell Don this failed" in n)
        self.assertEqual(cond, "failure()")

    def test_no_step_carries_two_if_keys(self):
        """Read off the TEXT, because a parser hides the duplicate it tolerated."""
        chunks = re.split(r"\n      - ", self.hot_text)
        for c in chunks[1:]:
            body = c.split("\n      - ")[0]
            self.assertLessEqual(len(re.findall(r"^        if:", body, re.M)), 1, body[:200])

    def test_the_hot_crons_still_scan_unconditionally(self):
        """This ADDS a path; it must not make the primary schedule conditional on a web read."""
        self.assertIn('"23 22 * * 1-5"|"41 23 * * 1-5")', self.hot_text)
        self.assertIn("workflow_dispatch", self.hot_text)

    def test_the_decision_calls_the_tested_module(self):
        self.assertIn("valuation.screener.scan_catchup", self.hot_text)
        self.assertIn("--json-stdin", self.hot_text)

    def test_the_hot_crons_are_still_scheduled(self):
        crons = I74.wf_crons(self.text)
        self.assertIn("23 22 * * 1-5", crons)
        self.assertIn("41 23 * * 1-5", crons)

    def test_the_installer_reads_the_tracked_directory(self):
        bat = io.open(os.path.join(REPO, "install_workflows.bat"), encoding="utf-8").read()
        self.assertIn("pending_workflows", bat)

    def test_this_suite_does_not_import_pyyaml(self):
        """THE DEFECT, PINNED. PyYAML is in neither requirements file, so a suite importing it
        passes here and fails on the runner -- which is what the land reported."""
        src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertNotEqual(a.name, "yaml", "PyYAML is not in CI")
            if isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "yaml", "PyYAML is not in CI")
        for req in ("requirements.txt", "requirements.lock.txt"):
            p = os.path.join(REPO, req)
            if os.path.exists(p):
                self.assertNotIn("pyyaml", io.open(p, encoding="utf-8").read().lower(),
                                 "%s now ships PyYAML; this guard's premise changed" % req)


class WhatThisDidNotDo(unittest.TestCase):
    def test_decisions_md_is_not_edited(self):
        import subprocess
        out = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--",
                              "DECISIONS.md"], capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "")

    def test_no_github_directory_change(self):
        """The land gate refuses it, so the handover is the only route."""
        import subprocess
        out = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", ".github"],
                             capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "")

    def test_the_catchup_module_makes_no_network_call(self):
        """A decision function that fetches is one nothing can test."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "scan_catchup.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                        else [node.module or ""])
                for m in mods:
                    self.assertNotIn(m.split(".")[0], ("requests", "urllib", "http", "socket"),
                                     "scan_catchup must not reach the network: %s" % m)


if __name__ == "__main__":
    unittest.main(verbosity=2)
