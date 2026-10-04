# -*- coding: utf-8 -*-
"""THE REFRESH DON RUNS ON THE EVENING OF 2026-10-23, pinned.

`refresh_sharadar.bat` is a double-click Don runs once, unattended, the night before a rebalance
he then places real money behind. The failure that matters is not a crash -- it is a **copy that
succeeds while the newest close does not move**, because the `.bat` would print SUCCESS, Don would
follow Path B, and the book would be rebalanced on stale prices with nothing anywhere saying so.
So the Python tool's contract is that it **proves the close moved** and the exit code carries it.

Two structural guards sit beside the behavioural ones:

  * **The `.bat` must not reimplement the copy.** A batch file that does its own `xcopy` is a
    second implementation of the sync that no test covers -- `B7`'s defect class, in a file nobody
    would think to look in. It must call the one definition.
  * **`if errorlevel 2` must be tested BEFORE `if errorlevel 1`.** Batch's `if errorlevel N` is
    `>= N`, so the reverse order routes EVERY failure to the first branch and the two distinct
    failure messages collapse into one. Verified by running the real thing at rc 0/1/2.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from scripts import refresh_backtest_from_freeze as R                     # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAT = os.path.join(REPO, "refresh_sharadar.bat")


def _prices(d, rows, date_first=True):
    os.makedirs(d, exist_ok=True)
    for tic, dates in rows.items():
        with io.open(os.path.join(d, tic + ".csv"), "w", encoding="utf-8", newline="") as fh:
            fh.write("date,close\n" if date_first else "close,date\n")
            for dt in dates:
                fh.write(("%s,10.0\n" % dt) if date_first else ("10.0,%s\n" % dt))


def _freeze(root, rows, date_first=True):
    bt = os.path.join(root, "backtest")
    _prices(os.path.join(bt, "prices"), rows, date_first)
    for f in R.DERIVED:
        io.open(os.path.join(bt, f), "w", encoding="utf-8").write("x\n")
    return root


class NewestCloseReadsTheHeader(unittest.TestCase):
    def test_the_date_column_is_found_by_NAME_not_by_POSITION(self):
        """A derived price file is `date,close` today. Reading column 0 unconditionally would be
        a silent wrong answer the day that order changes, which is the wrong-object family."""
        d = tempfile.mkdtemp()
        _prices(d, {"AAA": ["2026-01-01", "2026-10-02"]}, date_first=False)
        self.assertEqual(R.newest_close(d), "2026-10-02")

    def test_a_missing_directory_is_empty_rather_than_an_exception(self):
        self.assertEqual(R.newest_close(os.path.join(tempfile.mkdtemp(), "nope")), "")

    def test_it_takes_the_MAXIMUM_across_files_not_the_first_file(self):
        d = tempfile.mkdtemp()
        _prices(d, {"AAA": ["2026-07-24"], "ZZZ": ["2026-10-02"]})
        self.assertEqual(R.newest_close(d), "2026-10-02")

    def test_an_unreadable_file_is_skipped_rather_than_failing_the_whole_probe(self):
        d = tempfile.mkdtemp()
        _prices(d, {"AAA": ["2026-10-02"]})
        io.open(os.path.join(d, "BBB.csv"), "w", encoding="utf-8").write("")
        self.assertEqual(R.newest_close(d), "2026-10-02")


class ItRefusesToGoBackwards(unittest.TestCase):
    def test_an_OLDER_freeze_aborts_with_rc_2_and_touches_nothing(self):
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-01-01"]})
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-10-02"]})
        rc = R.main(["--freeze", fz, "--live", live])
        self.assertEqual(rc, 2)
        self.assertEqual(R.newest_close(os.path.join(live, "prices")), "2026-10-02",
                         "a refused sync must leave the live data exactly as it was")
        for f in R.DERIVED:
            self.assertFalse(os.path.exists(os.path.join(live, f)))

    def test_allow_older_permits_a_deliberate_rollback(self):
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-01-01"]})
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-10-02"]})
        rc = R.main(["--freeze", fz, "--live", live, "--allow-older"])
        self.assertEqual(rc, 0)
        self.assertEqual(R.newest_close(os.path.join(live, "prices")), "2026-01-01")


class AStaleSuccessIsAFailure(unittest.TestCase):
    """The defect this file exists for."""

    def test_a_copy_that_does_not_move_the_close_returns_rc_1(self):
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-07-24"]})
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-07-24"]})
        self.assertEqual(R.main(["--freeze", fz, "--live", live]), 1)

    def test_rc_1_is_DISTINCT_from_rc_2_so_the_bat_can_tell_them_apart(self):
        """Two different sentences for Don: 'the vendor published nothing newer' and 'the sync
        broke'. One exit code for both would make the message a guess."""
        fz = tempfile.mkdtemp()                                  # no backtest/ at all
        self.assertEqual(R.main(["--freeze", fz, "--live", tempfile.mkdtemp()]), 2)

    def test_a_missing_derived_file_fails_before_any_price_is_copied(self):
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-10-02"]})
        os.remove(os.path.join(fz, "backtest", R.DERIVED[0]))
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-07-24"]})
        self.assertEqual(R.main(["--freeze", fz, "--live", live]), 2)
        self.assertEqual(R.newest_close(os.path.join(live, "prices")), "2026-07-24")


class ItWillNotMixTwoVintages(unittest.TestCase):
    def test_a_name_the_new_export_dropped_is_PRUNED_and_NAMED(self):
        """A leftover price file looks point-in-time and is stale forever. Removing it silently
        would be nearly as bad: the run has to say which names went."""
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-10-02"]})
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-07-24"], "GONE": ["2026-07-24"]})
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = R.main(["--freeze", fz, "--live", live])
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(os.path.join(live, "prices", "GONE.csv")))
        self.assertIn("GONE.csv", buf.getvalue())
        self.assertIn("pruned 1 price file", buf.getvalue())

    def test_the_happy_path_reports_both_the_before_and_the_after(self):
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-10-02"]})
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-07-24"]})
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(R.main(["--freeze", fz, "--live", live]), 0)
        out = buf.getvalue()
        self.assertIn("2026-07-24", out)
        self.assertIn("2026-10-02", out)
        self.assertIn("SUCCESS", out)

    def test_dry_run_changes_nothing(self):
        fz = _freeze(tempfile.mkdtemp(), {"AAA": ["2026-10-02"]})
        live = tempfile.mkdtemp()
        _prices(os.path.join(live, "prices"), {"AAA": ["2026-07-24"]})
        self.assertEqual(R.main(["--freeze", fz, "--live", live, "--dry-run"]), 0)
        self.assertEqual(R.newest_close(os.path.join(live, "prices")), "2026-07-24")


class TheBatIsThin(unittest.TestCase):
    """It must ORCHESTRATE, never reimplement. Comments are stripped first: a guard that reads
    prose about code is the family this record has been bitten by repeatedly."""

    @staticmethod
    def _code():
        src = io.open(BAT, encoding="utf-8", errors="replace").read()
        keep = []
        for ln in src.splitlines():
            s = ln.strip().lower()
            if s.startswith("rem ") or s == "rem" or s.startswith("::"):
                continue
            keep.append(ln)
        return "\n".join(keep)

    def test_the_bat_exists_where_don_will_double_click_it(self):
        self.assertTrue(os.path.exists(BAT), "refresh_sharadar.bat must sit in the repo root")

    def test_it_calls_the_one_definition_of_the_sync(self):
        self.assertIn("python -m scripts.refresh_backtest_from_freeze", self._code())

    def test_it_does_NOT_copy_prices_itself(self):
        code = self._code().lower()
        for banned in ("xcopy", "robocopy", "copy data\\", "move data\\"):
            self.assertNotIn(banned, code,
                             "the .bat must not reimplement the sync; %r is a second, untested "
                             "implementation of it" % banned)
        # NON-VACUOUS: the stripper must still be able to see the orchestration it does do
        self.assertIn("python -m valuation.edge.sharadar_freeze", code)

    def test_errorlevel_2_is_tested_before_errorlevel_1(self):
        """Batch's `if errorlevel N` means `>= N`. Reversed, every failure takes the first
        branch and the two distinct messages collapse into one."""
        code = self._code().lower()
        i2, i1 = code.find("if errorlevel 2"), code.find("if errorlevel 1 goto notnewer")
        self.assertGreater(i2, -1)
        self.assertGreater(i1, -1)
        self.assertLess(i2, i1, "errorlevel 2 must be checked first or rc=2 reads as rc=1")

    def test_every_exit_path_prints_SUCCESS_or_FAILURE(self):
        """Don reads one line. Each labelled branch must carry a verdict word."""
        code = self._code()
        labels = [ln.strip() for ln in code.splitlines() if ln.strip().startswith(":")]
        self.assertIn(":PULLFAIL", labels)
        self.assertIn(":NOFREEZE", labels)
        self.assertIn(":NOTNEWER", labels)
        self.assertIn(":SYNCFAIL", labels)
        self.assertEqual(code.count("FAILURE:"), 5,
                         "four failure branches plus the missing-.env check")
        self.assertEqual(code.count("SUCCESS:"), 1)

    def test_it_checks_for_the_env_file_rather_than_failing_deep_in_a_download(self):
        self.assertIn('if not exist ".env"', self._code())

    def test_it_never_echoes_anything_key_shaped(self):
        """The constraint is absolute: the key is read from .env by Python and never printed."""
        code = self._code()
        for bad in ("SHARADAR_API_KEY", "%SHARADAR", "api_key", "apikey"):
            self.assertNotIn(bad.lower(), code.lower())

    def test_every_goto_resolves_to_a_real_label(self):
        """THE FIRST CUT OF THIS ASSERTED CRLF LINE ENDINGS AND WAS WRONG TWICE OVER.

        Wrong as a test: `.gitattributes` deliberately refuses `* text=auto` (renormalising the
        tree would conflict with every open branch), so line endings here are a property of the
        CHECKOUT, not of the file -- the assertion would pass on Windows and fail on a Linux
        runner. That is the guards-fail-in-CI family with the sign flipped.

        Wrong as a requirement: both throwaway `.bat` files used to verify the locator and the
        errorlevel ordering were LF-only, with labels, `goto` and a `for /f`, and cmd.exe ran
        them correctly. The CRLF belief was folklore.

        What IS a property of the file is that a `goto` names a label that exists. cmd.exe
        reports an unresolved one and keeps going, so a typo'd label skips straight past the
        verdict line Don is supposed to read.

        AND THE FIRST CUT OF *THAT* GUARD MISSED ITS OWN MUTATION, for the family this
        record keeps hitting: it collected `goto` only where it STARTS a line, and three of this
        file's gotos are the tail of an `if` -- `if not defined FREEZE goto NOFREEZE` and both
        errorlevel branches. So it was checking the bare `goto END` lines and was blind to every
        conditional one, which is the half more likely to be wrong. Found by mutation, not by
        reading. It now matches `goto` anywhere on the line.
        """
        import re

        code = self._code()
        gotos, labels = set(), {":eof"}
        for ln in code.splitlines():
            low = ln.strip().lower()
            for m in re.finditer(r"\bgoto\s+(:?[a-z0-9_]+)", low):
                gotos.add(m.group(1).lstrip(":"))
            if low.startswith(":"):
                labels.add(low.rstrip())
        self.assertGreaterEqual(len(gotos), 5, "this file has conditional gotos too; a guard "
                                               "seeing fewer than 5 is reading one form only")
        for g in sorted(gotos):
            self.assertIn(":" + g, labels, "goto %s has no matching label" % g)

    def test_it_runs_from_its_own_folder(self):
        """Double-clicked from Explorer the working directory is not guaranteed; every relative
        path below depends on this line."""
        self.assertIn('cd /d "%~dp0"', self._code())

    def test_the_freeze_locator_orders_by_NAME_not_by_TIME(self):
        """`backtest_freeze_YYYY-MM` sorts lexicographically into chronological order, and
        unlike an mtime order nothing can promote an older freeze by touching a file in it."""
        code = self._code()
        self.assertIn("/o-n", code)
        self.assertNotIn("/o-d", code)


class TheRunbookPointsAtIt(unittest.TestCase):
    def test_path_B_names_the_script_don_is_told_to_run(self):
        p = os.path.join(REPO, "REBALANCE_RUNBOOK_2026-10-22.md")
        if not os.path.exists(p):
            self.skipTest("LOUD SKIP: the runbook is not in this tree")
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("refresh_sharadar.bat", src,
                      "Path B's refresh step must name the script, or Don has a script and no "
                      "instruction telling him to run it")


if __name__ == "__main__":
    unittest.main(verbosity=2)
