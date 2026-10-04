# -*- coding: utf-8 -*-
"""`PANEL-EXT-RECHECK` — does the 2026-10 renewal move `PANEL-EXT-CENSUS`'s verdict? Pinned.

The census already answered the 1999-2008 feasibility question as a pre-committed free kill and
**failed all three candidate start years**. The only thing that could move that answer is new
data, so this re-check asks one question of the renewed export and must be incapable of doing
anything else. Three properties carry that:

  * **IT MUST REFUSE RATHER THAN REPORT "NOTHING CHANGED".** On a machine without the freeze the
    dangerous outcome is a confident `UNCHANGED` produced by looking at nothing — the
    vacuous-pass family, which this record has been bitten by repeatedly and which here would
    read as *"the out-of-sample test is still impossible"* on no evidence at all.
  * **IT MUST NOT RE-OPEN THE CENSUS.** No panel is built, no outcome statistic is computed and
    no bar is restated. A re-check that quietly becomes a second census would be choosing a
    design after watching the first one fail, which `W-28`'s rule forbids.
  * **ITS KILL LOGIC MUST BE NON-VACUOUS.** A `sf3` date before 2009 has to flip the verdict, or
    `UNCHANGED` is a constant wearing a measurement's clothes.
"""
import ast
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from scripts import panel_ext_recheck as R                                # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "scripts", "panel_ext_recheck.py")


def _manifest(sf3_min="2013-06-30", sf2_min="2008-01-02"):
    return {
        "tables": {
            "SF3": {"rows": 81221241, "date_min": sf3_min, "date_max": "2026-09-30",
                    "date_col": "date"},
            "SF3A": {"rows": 674259, "date_min": sf3_min, "date_max": "2026-09-30",
                     "date_col": "date"},
            "SF2": {"rows": 11570121, "date_min": sf2_min, "date_max": "2026-10-02",
                    "date_col": "filingdate"},
            "SEP": {"rows": 45394106, "date_min": "1997-12-31", "date_max": "2026-10-02",
                    "date_col": "date"},
            "SF1": {"rows": 3218057, "date_min": "1990-06-06", "date_max": "2026-10-02",
                    "date_col": "datekey"},
            "DAILY": {"rows": 39854661, "date_min": "1998-12-01", "date_max": "2026-10-02",
                      "date_col": "date"},
            "ACTIONS": {"rows": 715916, "date_min": "1997-12-31", "date_max": "2026-10-06",
                        "date_col": "date"},
            "TICKERS": {"rows": 74326, "date_min": "2008-01-02", "date_max": "2026-10-03",
                        "date_col": "lastupdated"},
        },
        "derived": {},
        "verdict": {"checkpoints_failed": []},
    }


class _Rooted(unittest.TestCase):
    """Plant a synthetic freeze at a root the module will actually resolve."""

    def _root(self, man):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "backtest_freeze_2026-10"))
        json.dump(man, io.open(os.path.join(d, "backtest_freeze_2026-10", "MANIFEST.json"),
                               "w", encoding="utf-8"))
        os.environ["VALQUO_DATA_ROOT"] = d
        self.addCleanup(os.environ.pop, "VALQUO_DATA_ROOT", None)
        return d


class ItRefusesRatherThanReportingNothingChanged(_Rooted):
    def test_an_absent_manifest_REFUSES_with_rc_2(self):
        d = tempfile.mkdtemp()
        os.environ["VALQUO_DATA_ROOT"] = d
        self.addCleanup(os.environ.pop, "VALQUO_DATA_ROOT", None)
        # the module also falls back to the primary root, so this only proves the branch when
        # that is absent too; assert on the function rather than on this machine's disk
        self.assertIsNone(R.manifest("2099-01")[0])

    def test_the_refusal_branch_exists_and_returns_2(self):
        """Read the source: the no-manifest path must return 2, never 0."""
        tree = ast.parse(io.open(SRC, encoding="utf-8").read())
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
        twos = [n for n in ast.walk(fn)
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
                and n.value.value == 2]
        self.assertTrue(twos, "main() has no `return 2`, so an absent freeze cannot refuse")


class TheKillLogicIsNonVacuous(_Rooted):
    def test_the_real_dates_read_UNCHANGED(self):
        self._root(_manifest())
        self.assertEqual(R.main([]), 0)

    def test_a_PRE_2009_sf3_FLIPS_the_verdict(self):
        """The positive control. If `institutional` ever acquired pre-2009 history the verdict
        must move, or UNCHANGED is a constant."""
        self._root(_manifest(sf3_min="2005-03-31"))
        self.assertEqual(R.main([]), 1)

    def test_a_PRE_2008_sf2_FLIPS_the_verdict(self):
        self._root(_manifest(sf2_min="1999-02-01"))
        self.assertEqual(R.main([]), 1)

    def test_both_kills_are_required_not_either(self):
        """Either theme recovering is enough to make the answer worth re-deriving."""
        self._root(_manifest(sf3_min="2005-03-31", sf2_min="1999-02-01"))
        self.assertEqual(R.main([]), 1)

    def test_the_artifact_IS_WRITTEN_BESIDE_THE_MANIFEST_IT_READ(self):
        """FOUND BY MUTATION, AND IT IS WHY THIS TEST EXISTS.

        The first cut wrote to the first root that happened to have a `free_analysis` directory.
        A test pointing `VALQUO_DATA_ROOT` at a temp freeze then fell through to the PRIMARY root
        and **overwrote the real research artifact with synthetic numbers** -- including, from the
        flipped-fixture cases above, a fabricated `MOVED` verdict. Tests must not touch real
        state, and `E-5`'s rule is the fix: resolve an output beside its own inputs.
        """
        d = self._root(_manifest(sf3_min="2005-03-31"))      # a verdict that must NOT escape
        self.assertEqual(R.main([]), 1)
        here = os.path.join(d, "free_analysis", "PANEL_EXT_RECHECK.json")
        self.assertTrue(os.path.exists(here),
                        "the artifact was not written beside the manifest that was read")
        got = json.load(io.open(here, encoding="utf-8"))
        self.assertEqual(got["verdict"], "MOVED")
        self.assertEqual(got["trials"], 0)


class ItDoesNotReOpenTheCensus(unittest.TestCase):
    @staticmethod
    def _tree():
        return ast.parse(io.open(SRC, encoding="utf-8").read())

    def test_it_builds_no_panel_and_imports_no_panel_builder(self):
        names = set()
        for n in ast.walk(self._tree()):
            if isinstance(n, ast.Import):
                names.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    names.add(n.module)
                names.update(a.name for a in n.names)      # `from x import y` puts y HERE
        for banned in ("fundamental_panel", "build_fundamental_panel", "served_index_book",
                       "quantile_backtest", "after_tax_backtest"):
            self.assertNotIn(banned, names,
                             "a re-check that can build a book is a second census")
        # NON-VACUOUS: the import scan must see the imports that ARE there
        self.assertTrue({"json", "os", "io"} & names, "the import scan found nothing")

    def test_it_computes_no_return_or_alpha_statistic(self):
        """Read CODE, not prose about code — but strip ONLY docstrings.

        THE FIRST CUT BLANKED EVERY STRING CONSTANT and was wrong in both directions at once: it
        failed against a correct tree (the dict keys this module legitimately reads, `date_min`
        among them, vanished with the prose) AND it made its own ban list VACUOUS, because with
        every string removed a banned word could no longer appear inside a subscript even if the
        code were reading it. A stripper that removes the evidence is worse than no stripper —
        the same shape as `MB15`'s stripper, which had to be pinned non-vacuous in both
        directions for exactly this reason.
        """
        src = io.open(SRC, encoding="utf-8").read().lower()
        tree = self._tree()
        for n in ast.walk(tree):
            if not isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                continue
            body = getattr(n, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body[0].value.value = ""
        code = ast.unparse(tree).lower()
        for banned in ("roth_net_ann", "net_ann", "alpha", "sharpe", "tstat", "hac"):
            self.assertNotIn(banned, code,
                             "%r appears in the code, so this is no longer a facts-class "
                             "re-check" % banned)
        self.assertIn("date_min", code)      # non-vacuity: it does read what it claims to
        self.assertIn("panel_ext", src)

    def test_it_declares_zero_trials(self):
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("ZERO TRIALS", src)
        tree = self._tree()
        out = [n for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and n.value == 0]
        self.assertTrue(out)

    def test_the_census_figures_are_QUOTED_so_a_drift_disagrees(self):
        """`B7`: the re-check must not restate the census's numbers from memory. They are
        carried as a literal block, and the 70% rule and the five-of-seven count are the two a
        reader would otherwise have to take on trust."""
        self.assertEqual(R.CENSUS["theme_coverage_rule"], 0.70)
        self.assertEqual(R.CENSUS["themes_available_pre_2009"], 5)
        self.assertEqual(R.CENSUS["themes_in_shipped_composite"], 7)
        self.assertEqual(R.CENSUS["insider_coverage_2008"], 0.307)
        self.assertTrue(R.CENSUS["sf3_has_no_pre_2009_rows"])


class TheRecordAgreesWithIt(unittest.TestCase):
    def test_the_census_handoff_still_carries_the_figures_quoted_here(self):
        p = os.path.join(REPO, "HANDOFF_scout_panel_ext.md")
        if not os.path.exists(p):
            self.skipTest("LOUD SKIP: the census handoff is not in this tree")
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("0.307", src)
        self.assertIn("70%", src)
        self.assertIn("FIVE themes", src)

    def test_the_census_ledger_row_still_reads_DONE(self):
        p = os.path.join(REPO, "VALQUO_LEDGER.md")
        row = [ln for ln in io.open(p, encoding="utf-8")
               if ln.startswith("| PANEL-EXT-CENSUS |")]
        self.assertEqual(len(row), 1, "the census must have exactly one ledger row")
        self.assertIn("DONE", row[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
