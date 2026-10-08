# -*- coding: utf-8 -*-
"""`CORRECTED-REBUILD` item 3 -- the Index book's third column, and the identity that makes the
decomposition checkable.

The whole value of a third column is that `published -> corrected` stops being one number. That
only works if the two legs are measured on the SAME construction and if their sum is checked --
so this suite pins the identity's membership (additive figures only), the gate's strength, and
that nothing banked is overwritten.

Run as its own process and judged by exit code, per `RUN_RULES`.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  (must precede the valuation imports)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "restricted_index_book.py")


def _src():
    return io.open(SRC, encoding="utf-8").read()


def _tree():
    return ast.parse(_src())


import scripts.restricted_index_book as R                                   # noqa: E402


# =============================================================================================
class TheIdentityIsTheWholePoint(unittest.TestCase):
    """`(published->restricted) + (restricted->corrected) == (published->corrected)` is exact in
    real arithmetic. Checking it is what turns a three-column table into a decomposition rather
    than three readings side by side -- and a violation is a bug in the script, not a finding."""

    def test_only_additive_figures_are_in_the_identity(self):
        """A RATIO's legs do not sum. Putting a Sharpe in the identity would manufacture a
        mismatch out of arithmetic and then invite someone to widen the tolerance until it
        passed -- which is how a real wiring bug gets hidden."""
        self.assertIn("net_sharpe", R.TABLE_KEYS,
                      "the Sharpe must still be REPORTED; it is only excluded from the sum")
        self.assertNotIn("net_sharpe", R.IDENTITY_KEYS)
        self.assertIn("annual_turnover", R.TABLE_KEYS)
        self.assertNotIn("annual_turnover", R.IDENTITY_KEYS)
        self.assertIn("after_tax_sharpe", R.TAX_KEYS)
        self.assertNotIn("after_tax_sharpe", R.TAX_IDENTITY_KEYS)

    def test_the_identity_set_is_a_subset_of_the_table(self):
        self.assertTrue(set(R.IDENTITY_KEYS) <= set(R.TABLE_KEYS),
                        "a key is checked in the identity and never printed")
        self.assertTrue(set(R.TAX_IDENTITY_KEYS) <= set(R.TAX_KEYS))

    def test_the_figures_the_question_is_about_are_in_the_identity(self):
        """Don asked about the drawdown and the return. Both must be decomposed, or the third
        column does not answer the question it was built for."""
        self.assertIn("net_max_drawdown", R.IDENTITY_KEYS)
        self.assertIn("net_ann", R.IDENTITY_KEYS)
        self.assertIn("after_tax_max_drawdown", R.TAX_IDENTITY_KEYS)
        self.assertIn("after_tax_ann", R.TAX_IDENTITY_KEYS)

    def test_the_tolerance_is_a_tiny_literal(self):
        """A tolerance loose enough to absorb a real mis-wiring is not a check. The legs are
        percentages of order 1e-1; a genuine bug moves one by 1e-2 or more."""
        self.assertIsInstance(R.IDENTITY_TOL, float)
        self.assertLessEqual(R.IDENTITY_TOL, 1e-9)
        lits = {}
        for n in _tree().body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                    and isinstance(n.targets[0], ast.Name):
                try:
                    lits[n.targets[0].id] = ast.literal_eval(n.value)
                except Exception:
                    pass
        self.assertIn("IDENTITY_TOL", lits, "the tolerance is computed rather than fixed")

    def test_a_violation_is_reported_as_a_bug_and_exits_non_zero(self):
        src = _src()
        self.assertIn("return 3", src, "an identity violation must not exit 0")
        self.assertIn("bug in this script, not a finding", src,
                      "a violation must be labelled a bug, or a reader will quote it as a "
                      "finding about the book")


# =============================================================================================
class TheGateKeepsItsFullStrength(unittest.TestCase):
    def test_the_target_is_measured_not_typed(self):
        """`served_index_book`'s `C1` demands EXACT reproduction and ABORTS otherwise. For a
        third panel there is no landed figure, so one is MEASURED first -- by a DIFFERENT code
        path from the one being gated. Part 2a's first pass handed the gate an ADOPTED alpha
        while the scorer computed the DEPLOYED composite; the gate caught it, twice."""
        t = _tree()
        calls = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                 for n in ast.walk(t) if isinstance(n, ast.Call)}
        self.assertIn("deployed_statistics", calls,
                      "the gate target is not measured by corrected_deployed's instrument")
        # and it must not be a hard-coded float handed to expect_alpha
        for n in ast.walk(t):
            if isinstance(n, ast.Call):
                for kw in n.keywords or []:
                    if kw.arg == "expect_alpha":
                        self.assertNotIsInstance(
                            kw.value, ast.Constant,
                            "expect_alpha is a typed literal, so the gate targets a transcribed "
                            "number rather than a measured one")

    def test_it_refuses_without_a_measurable_target(self):
        self.assertIn("would have no target", _src())

    def test_served_index_book_is_called_not_reimplemented(self):
        """`B7`. `served_index_book` is ~150 lines of arms, tax treatments and the one-knob
        decomposition; a second implementation is two measurements of one object, free to
        drift."""
        t = _tree()
        attrs = {getattr(n.func, "attr", None) for n in ast.walk(t) if isinstance(n, ast.Call)}
        self.assertIn("main", attrs)
        self.assertIn("served_index_book", _src())
        for banned in ("def _quantile_backtest", "def _after_tax", "def _one_knob"):
            self.assertNotIn(banned, _src(),
                             "a second implementation of served_index_book's own machinery")


# =============================================================================================
class NothingBankedIsOverwritten(unittest.TestCase):
    def test_it_writes_only_its_own_two_artifacts(self):
        src = _src()
        self.assertIn('OUT = "INDEX_BOOK_RESTRICTED.json"', src)
        self.assertIn("INDEX_BOOK_THREE_WAY.json", src)

    def test_the_published_and_corrected_books_are_read_only(self):
        """A string appearing in the file is not enough -- what matters is that neither name is
        ever the target of a write. Checked on the tree: every `io.open(..., "w")` call's path
        must not mention them."""
        t = _tree()
        for n in ast.walk(t):
            if not isinstance(n, ast.Call):
                continue
            if getattr(n.func, "attr", None) != "open":
                continue
            mode = None
            for a in n.args[1:]:
                if isinstance(a, ast.Constant):
                    mode = a.value
            for kw in n.keywords or []:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if mode and "w" in str(mode):
                dump = ast.dump(n.args[0]) if n.args else ""
                for banked in ("INDEX_BOOK.json", "INDEX_BOOK_CORRECTED.json"):
                    self.assertNotIn(banked, dump,
                                     "a banked Index book is opened for writing")

    def test_it_refuses_when_an_input_column_is_absent(self):
        """A two-column table answers a different question, so a missing input is a refusal
        rather than a partial run."""
        src = _src()
        self.assertIn("a two-column table would answer a different question", src)
        self.assertIn("REFUSING", src)

    def test_the_panel_it_reads_is_the_restricted_one(self):
        self.assertEqual(R.PANEL, "UNIVERSE_BIAS_PANEL_restricted.pkl")


# =============================================================================================
class TheCaveatTravelsWithTheVintageLeg(unittest.TestCase):
    """The restricted panel carries 3,049 names against the published book's 2,531 -- the same
    export's universe RULE, richer at the newer vintage. So the vintage leg is NOT a pure
    data-vintage change. Quoting it as one is the misreading this item most invites."""

    def test_the_caveat_is_in_the_artifact_and_not_only_in_a_handoff(self):
        src = _src()
        self.assertIn("THE_CAVEAT_THAT_TRAVELS_WITH_THE_VINTAGE_LEG", src,
                      "the caveat must ship in the artifact: a reader of the JSON alone must "
                      "not be able to quote the vintage leg as a pure data change")
        self.assertIn("NOT a pure data-vintage change", src)

    def test_it_cites_UNIVERSE_BIAS_rather_than_re_deriving_the_point(self):
        self.assertIn("UNIVERSE_BIAS_ARMS.json", _src())
        self.assertIn("near-neighbour", _src())

    def test_the_name_counts_ship_beside_every_figure(self):
        self.assertIn('"panels"', _src())


# =============================================================================================
class ItChargesNothingAndAdoptsNothing(unittest.TestCase):
    def test_zero_trials_and_no_adoption(self):
        src = _src()
        self.assertIn('"trials": 0', src)
        self.assertIn('"adopts_nothing": True', src)
        self.assertIn('"changes_no_public_page": True', src)

    def test_every_figure_names_its_weighting(self):
        src = _src()
        self.assertIn("DEPLOYED", src)
        self.assertIn('"weighting"', src)
        self.assertIn("CPCV never consulted", src)


# =============================================================================================
class NoModuleLevelDataRootResolution(unittest.TestCase):
    """`CORRECTED-FLOORS` part 1 failed CI because a module computed its data root at import
    time, and `data/` is gitignored so a runner has none."""

    def test_no_data_root_at_import_time(self):
        for n in _tree().body:
            if not isinstance(n, ast.Assign):
                continue
            dump = ast.dump(n.value)
            self.assertNotIn("_data_root", dump)
            self.assertNotIn("attr='fa'", dump)

    def test_served_index_book_is_imported_LAZILY(self):
        """It resolves its own data root at module level and RAISES without the banked panel, so
        a top-level import would make every test touching this module error on a runner."""
        top = {a.name for n in _tree().body if isinstance(n, ast.ImportFrom)
               for a in n.names}
        self.assertNotIn("served_index_book", top,
                         "served_index_book is imported at module level, which errors on CI")

    def test_the_guard_is_not_vacuous(self):
        bad = ast.parse("DATA = _data_root()\n")
        self.assertTrue(any(isinstance(n, ast.Assign) and "_data_root" in ast.dump(n.value)
                            for n in bad.body),
                        "the module-level detector cannot see the thing it bans")


if __name__ == "__main__":
    unittest.main(verbosity=2)
