# -*- coding: utf-8 -*-
"""`--same-date` MUST NOT write under the published reading's name. It did, and it cost one.

**WHAT HAPPENED, 2026-10-04.** Running the renewal re-check wrote its result into the cache
under the key `freeze_2026-07-31`, so `compare` emitted it as that reading and overwrote both
`D9_FIDELITY.json` and `D9_FIDELITY_ROWS_freeze_2026-07-31.pkl`. The landed **B1 0.4321 / B2
0.2326** were destroyed by the one mode whose entire purpose is to re-check them.

**RECOVERED, AND VERIFIABLY SO.** Re-running `--compare` rebuilt the reading from the intact
`D9_SHARADAR_SCORES.pkl` and the 2026-08-08 live snapshot, reproducing both published figures at
**0.000e+00** against the constants `scripts/index_choice_buildable.py` keeps in TRACKED code.
That is the only reason the recovery is checkable rather than merely plausible — `data/` is
gitignored, so there was no git copy to fall back on.

**THE PART WORTH REMEMBERING.** `d9_fidelity`'s own comment above `compare` already names this
defect — *"`--same-date` used to overwrite the two-reading cache ... A mode that clobbers another
mode's output is a defect even when both are 'just' intermediates"* — and fixed it for the SCORES
CACHE. The OUTPUT was left keyed the old way. **A half-applied fix reads as a fixed one**, and the
comment made it look handled.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "scripts", "d9_fidelity.py")


def _tree():
    return ast.parse(io.open(SRC, encoding="utf-8").read())


def _fn(name):
    for n in ast.walk(_tree()):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError("no function %r in d9_fidelity" % name)


class SameDateKeysItsOwnReading(unittest.TestCase):
    def test_same_date_does_not_write_the_published_reading_name(self):
        """The whole defect in one assertion: read the CODE of `same_date`, with docstrings and
        the explanatory comment excluded, and require that it never names the published
        reading. The comment quotes it deliberately, which is why the AST is read and not the
        raw source -- the comment-versus-code family."""
        fn = _fn("same_date")
        for n in ast.walk(fn):
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
                continue                      # its docstring
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                self.assertNotEqual(
                    n.value, "freeze_2026-07-31",
                    "same_date is writing under the PUBLISHED reading's name again")

    def test_same_date_builds_a_label_from_the_date_it_actually_scored(self):
        src = ast.unparse(_fn("same_date"))
        self.assertIn("same_date_%s", src)
        self.assertIn("labels=", src)
        self.assertIn("out_path=", src)

    def test_same_date_writes_a_DIFFERENT_json_from_compare(self):
        src = ast.unparse(_fn("same_date"))
        self.assertIn("D9_FIDELITY_SAMEDATE.json", src)


class TheDefaultPathIsUnchanged(unittest.TestCase):
    """The fix must be inert for everyone else, or it trades one broken artifact for another."""

    def test_compare_still_defaults_to_the_two_published_readings(self):
        import inspect
        from scripts import d9_fidelity as D
        sig = inspect.signature(D.compare)
        self.assertIsNone(sig.parameters["labels"].default)
        self.assertIsNone(sig.parameters["out_path"].default)
        src = ast.unparse(_fn("compare"))
        self.assertIn("'freeze_2026-07-31', 'backtest_2026-07-24'", src.replace('"', "'"),
                      "the default reading pair must survive as the fallback")
        self.assertIn("out_path or OUT", src)


class ThePublishedReadingIsIntact(unittest.TestCase):
    """The recovery, checked against TRACKED constants rather than against another artifact."""

    def test_the_landed_figures_reproduce_exactly(self):
        import json
        from scripts.index_choice_buildable import (D9_PUBLISHED_DECILE_OVERLAP,
                                                    D9_PUBLISHED_LL_SPEARMAN)
        for c in (os.environ.get("VALQUO_DATA_ROOT"),
                  os.path.join(REPO, "data"),
                  r"C:\Users\donni\Downloads\valuation-tool\data"):
            if not c:
                continue
            p = os.path.join(c, "free_analysis", "D9_FIDELITY.json")
            if not os.path.exists(p):
                continue
            v = json.load(io.open(p, encoding="utf-8"))["readings"]["freeze_2026-07-31"]
            self.assertEqual(v["B1_like_for_like_composite_spearman"],
                             D9_PUBLISHED_LL_SPEARMAN)
            self.assertEqual(v["B2_decile_overlap"], D9_PUBLISHED_DECILE_OVERLAP)
            return
        self.skipTest("LOUD SKIP: D9_FIDELITY.json is not on this machine")


if __name__ == "__main__":
    unittest.main(verbosity=2)
