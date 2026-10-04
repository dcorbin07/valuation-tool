# -*- coding: utf-8 -*-
"""SHARADAR RENAMED SF3's COLUMNS BETWEEN THE 2026-08 AND 2026-10 EXPORTS. Pinned here.

Measured on the two freezes on disk:

    2026-08  ticker,investorname,securitytype,calendardate,value,units,price
    2026-10  ticker,investorid,  securitytype,date,        value,units

The manager column was renamed (its contents were already 6-char codes in BOTH, so nothing about
the data changed), the quarter column was renamed, and `price` was dropped.

**IT CRASHED THE FREEZE, AND THAT IS THE SAFE DIRECTION** -- `h.index("investorname")` raises
`ValueError`, so the failure was loud. The dangerous version of the same event is the one these
tests exist to prevent: a rename that makes a column read as ABSENT, so a 13F signal contributes
nothing to a theme mean and raises nothing. That is the COVERAGE-RULE family, and this project
has been bitten by it four times.

**A SECOND, QUIETER DEFECT CAME WITH IT.** `sharadar_freeze`'s own integrity report hard-coded
`calendardate` in its date probe, so the first 2026-10 manifest reported `date_col: None` and NO
DATE RANGE AT ALL for SF3, SF3A and the derived institutional.csv. **The report went SILENT on
three tables rather than failing**, which is strictly worse than a crash.
"""
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from valuation.edge import bulk as B                                    # noqa: E402
from valuation.edge import sharadar_freeze as SF                        # noqa: E402

OLD = ["ticker", "investorname", "securitytype", "calendardate", "value", "units", "price"]
NEW = ["ticker", "investorid", "securitytype", "date", "value", "units"]


class BothSchemasResolve(unittest.TestCase):
    def test_the_manager_and_quarter_columns_resolve_under_both_spellings(self):
        for h in (OLD, NEW):
            self.assertEqual(B._first_index(h, B.SF3_MANAGER_COLS, "manager"), 1)
            self.assertEqual(B._first_index(h, B.SF3_QUARTER_COLS, "quarter"), 3)

    def test_the_old_spelling_is_still_FIRST_so_the_2026_08_freeze_is_unaffected(self):
        """Neither spelling is preferred on merit, but the old one must keep working: a freeze
        already on disk is the only copy of data that cannot be re-pulled."""
        self.assertEqual(B.SF3_MANAGER_COLS[0], "investorname")
        self.assertEqual(B.SF3_QUARTER_COLS[0], "calendardate")

    def test_an_absent_column_RAISES_and_names_what_it_tried(self):
        """The whole point. A rename must never degrade to 'no data'."""
        with self.assertRaises(ValueError) as cm:
            B._first_index(["ticker", "value"], B.SF3_MANAGER_COLS, "manager")
        msg = str(cm.exception)
        self.assertIn("manager", msg)
        self.assertIn("investorname", msg)
        self.assertIn("investorid", msg)

    def test_a_THIRD_rename_would_still_raise_rather_than_pass(self):
        """A positive control on the guard itself: tolerance of two names is not tolerance of
        anything, so a future third rename is still loud."""
        with self.assertRaises(ValueError):
            B._first_index(["ticker", "manager_code", "securitytype", "quarter", "value"],
                           B.SF3_MANAGER_COLS, "manager")


class OneDefinitionOfTheTolerance(unittest.TestCase):
    @staticmethod
    def _indexed_literals(path):
        """Every string literal passed to a `.index(...)` call, read from the SYNTAX TREE.

        THE FIRST CUT OF THIS GREPPED THE RAW SOURCE AND FAILED AGAINST A CORRECT TREE, because
        `bulk.py`'s new comment QUOTES `h.index("investorname")` while explaining why not to
        write it. That is the comment-versus-code family this record has hit repeatedly, and the
        fix is the one it already landed twice: read the AST, which sees code and not prose
        about code.
        """
        import ast
        tree = ast.parse(io.open(path, encoding="utf-8").read())
        out = set()
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "index"):
                for a in n.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        out.add(a.value)
        return out

    def _edge(self, name):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "edge", name)

    def test_elite13f_imports_bulks_tolerance_rather_than_restating_it(self):
        """`B7`. Two readers of one file must not disagree about what its columns are called."""
        src = io.open(self._edge("elite13f.py"), encoding="utf-8").read()
        self.assertIn("from .bulk import SF3_MANAGER_COLS, SF3_QUARTER_COLS, _first_index", src)
        lits = self._indexed_literals(self._edge("elite13f.py"))
        self.assertNotIn("investorname", lits, "elite13f still hard-codes the old spelling")
        self.assertNotIn("calendardate", lits)

    def test_bulk_does_not_hard_code_the_old_spelling_in_an_index_call(self):
        lits = self._indexed_literals(self._edge("bulk.py"))
        self.assertNotIn("investorname", lits)
        self.assertNotIn("calendardate", lits)
        # the AST half must be NON-VACUOUS: it has to see the index calls that ARE there
        self.assertIn("securitytype", lits,
                      "the AST scan found no index literals at all, so it proves nothing")
        src = io.open(self._edge("bulk.py"), encoding="utf-8").read()
        self.assertEqual(src.count("SF3_MANAGER_COLS = "), 1)


class TheFreezeDateProbeCannotGoSilent(unittest.TestCase):
    def test_the_13f_tables_carry_ALTERNATIVE_date_columns(self):
        for k in ("sf3.csv", "sf3a.csv"):
            v = SF.DATE_COL[k]
            self.assertIsInstance(v, tuple, "%s must try alternatives" % k)
            self.assertIn("calendardate", v)
            self.assertIn("date", v)

    def test_a_single_name_still_works_for_every_other_table(self):
        self.assertEqual(SF.DATE_COL["sep.csv"], "date")
        self.assertEqual(SF.DATE_COL["sf1.csv"], "datekey")

    def test_scan_csv_finds_the_date_under_either_spelling(self):
        import tempfile
        for header, want in ((OLD, "calendardate"), (NEW, "date")):
            d = tempfile.mkdtemp()
            p = os.path.join(d, "x.csv")
            with io.open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(",".join(header) + "\n")
                row = ["AAA"] * len(header)
                row[header.index(want)] = "2020-03-31"
                fh.write(",".join(row) + "\n")
            r = SF._scan_csv(p, ("calendardate", "date"))
            self.assertEqual(r["date_col"], want)
            self.assertEqual(r["date_min"], "2020-03-31")
            self.assertEqual(r["date_max"], "2020-03-31")

    def test_scan_csv_RECORDS_what_it_tried_when_it_finds_nothing(self):
        """A silent `None` is what shipped. The names tried must be in the record."""
        import tempfile
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.csv")
        with io.open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("ticker,value\nAAA,1\n")
        r = SF._scan_csv(p, ("calendardate", "date"))
        self.assertIsNone(r["date_col"])
        self.assertEqual(r["date_col_tried"], ["calendardate", "date"])


class TheFrozenManifestReportsEveryDate(unittest.TestCase):
    """The outcome on the real 2026-10 freeze, which is the only proof that matters."""

    def _manifest(self):
        for c in (os.environ.get("VALQUO_DATA_ROOT"),
                  os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data"),
                  r"C:\Users\donni\Downloads\valuation-tool\data"):
            if not c:
                continue
            p = os.path.join(c, "backtest_freeze_2026-10", "MANIFEST.json")
            if os.path.exists(p):
                return json.load(io.open(p, encoding="utf-8"))
        return None

    def test_no_object_in_the_freeze_reports_a_missing_date_column(self):
        m = self._manifest()
        if m is None:
            self.skipTest("LOUD SKIP: the 2026-10 freeze manifest is not on this machine")
        silent = [k for k, v in list(m["tables"].items()) + list(m["derived"].items())
                  if isinstance(v, dict) and v.get("rows") and not v.get("date_col")]
        self.assertEqual(silent, [],
                         "these objects report no date range, so the integrity report is blind "
                         "to them: %r" % (silent,))

    def test_the_13f_tables_report_the_2013_start_the_record_expects(self):
        m = self._manifest()
        if m is None:
            self.skipTest("LOUD SKIP: the 2026-10 freeze manifest is not on this machine")
        for k in ("SF3", "SF3A"):
            self.assertEqual(m["tables"][k]["date_min"], "2013-06-30",
                             "13F coverage starting in 2013 is load-bearing for any pre-2013 "
                             "panel: `institutional` cannot be built before it")

    def test_no_checkpoint_failed(self):
        m = self._manifest()
        if m is None:
            self.skipTest("LOUD SKIP: the 2026-10 freeze manifest is not on this machine")
        self.assertEqual(m["verdict"]["checkpoints_failed"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
