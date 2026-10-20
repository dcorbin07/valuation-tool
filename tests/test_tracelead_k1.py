# -*- coding: utf-8 -*-
"""`TRACELEAD` — the collection pass and `K1`'s provable bound.

The load-bearing tests are `test_a_clearing_bound_is_UNRESOLVED_and_never_a_pass` (a bound that
clears must not be readable as a pass) and `test_the_bound_really_is_an_upper_bound` (the
most-present-names assignment must dominate every other assignment, or the "provably" in the
verdict is a lie).
"""
from __future__ import annotations

import ast
import io
import itertools
import json
import os
import sys
import unittest

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import state_isolation  # noqa: F401,E402

from scripts import edge_drafts_collect as C                             # noqa: E402
from scripts import tracelead_k1_bound as K                             # noqa: E402

DRAFT = os.path.join(ROOT, "PREREG_DRAFT_tracelead.md")


def _src(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class NoOutcomeIsEverRead(unittest.TestCase):
    """Both modules are collection and control. A forward return must not appear."""

    BANNED = ("fwd_ret", "bench_ret", "abnormal", "permutation_null")

    def test_neither_module_names_a_forward_return(self):
        for rel in ("scripts/edge_drafts_collect.py", "scripts/tracelead_k1_bound.py"):
            tree = ast.parse(_src(rel))
            names = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute):
                    names.add(n.attr)
                elif isinstance(n, ast.Name):
                    names.add(n.id)
                elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                    names.add(n.value)
            for b in self.BANNED:
                self.assertNotIn(b, names, "%s reaches an outcome (%s)" % (rel, b))

    def test_the_banned_scan_is_not_vacuous(self):
        """Positive control: the same scan DOES find them where they legitimately live."""
        tree = ast.parse(_src("scripts/insider_wide_arm.py"))
        found = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        found |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        found |= {n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertTrue({"fwd_ret", "abnormal", "permutation_null"} & found)

    def test_both_declare_zero_trials(self):
        for mod, rel in ((C, "collect"), (K, "k1")):
            self.assertIn("ZERO TRIALS", (mod.__doc__ or "").upper(), rel)


class TheBarIsTheDraftsAndIsNotRechosen(unittest.TestCase):

    def test_the_draft_file_exists(self):
        """A citation a reader can check, rather than taken on trust."""
        self.assertTrue(os.path.isfile(DRAFT))

    def test_the_cell_bar_and_floor_are_the_drafts_own_numbers(self):
        txt = _src("PREREG_DRAFT_tracelead.md")
        self.assertEqual(K.K1_CELL_BAR, 0.70)
        self.assertEqual(K.K1_PER_DATE_FLOOR, 0.50)
        self.assertIn("0.70", txt)
        self.assertIn("0.50", txt)

    def test_the_window_and_lag_are_the_drafts_construction(self):
        """63-session window, change from t-126. Section 2, fixed before any measurement."""
        self.assertEqual(C.WIN, 63)
        self.assertEqual(C.LAG, 126)


class TheBoundIsReallyABound(unittest.TestCase):

    @staticmethod
    def _cell_cov(per_name, chosen):
        tot = sum(per_name.values())
        return sum(v for k, v in per_name.items() if k in chosen) / tot

    def test_the_bound_really_is_an_upper_bound(self):
        """THE LOAD-BEARING TEST. Taking the N most-present names must beat, or tie, every other
        choice of N names — checked exhaustively on a small case rather than argued."""
        per_name = {"A": 9, "B": 7, "C": 4, "D": 2, "E": 1}
        for n in range(1, 5):
            top = set(sorted(per_name, key=lambda k: -per_name[k])[:n])
            best = self._cell_cov(per_name, top)
            for combo in itertools.combinations(per_name, n):
                self.assertLessEqual(self._cell_cov(per_name, set(combo)), best + 1e-12,
                                     "a non-top set beat the bound at n=%d" % n)

    def test_a_clearing_bound_is_UNRESOLVED_and_never_a_pass(self):
        """A bound that clears says nothing about the real figure. If this ever reports a pass,
        a candidate could be waved through on an upper bound."""
        root = _data_root()
        p = os.path.join(root, "free_analysis", K.OUT) if root else ""
        if not p or not os.path.isfile(p):
            _skip_loudly(self, "%s absent - it is built from LICENSED payload under D:\\wrds, "
                               "which CI never has" % K.OUT)
        r = json.load(io.open(p, encoding="utf-8"))
        # THE VERDICT IS A CLOSED VOCABULARY, NOT PROSE TO GREP.
        #
        # My first cut banned the substring "PASS" and FIRED AGAINST THE CORRECT ARTIFACT,
        # because the verdict's own words are "which is NOT a pass" -- the substring-ban family
        # this record names a dozen times, committed with the warning in view. The property is
        # that the verdict opens with exactly one of two declared stems, so no prose about
        # passing can ever satisfy or break it.
        stem = r["verdict"].split(".")[0].strip()
        if r["K1_FIRES_PROVABLY"]:
            self.assertTrue(stem.startswith("K1 FIRES"), stem)
        else:
            self.assertTrue(stem.startswith("K1 UNRESOLVED"), stem)
            self.assertFalse(stem.startswith("K1 FIRES"), stem)

    def test_the_verdict_vocabulary_is_closed(self):
        src = _src("scripts/tracelead_k1_bound.py")
        self.assertIn("K1 FIRES", src)
        self.assertIn("K1 UNRESOLVED", src)


class TheLicenceRulesHold(unittest.TestCase):

    def test_the_raw_root_is_not_inside_the_repository_tree(self):
        """Licensed payload must not be reachable by a commit.

        **THIS TEST FAILED IN CI AND THE DEFECT WAS MINE.** It used
        `os.path.abspath(RAW_ROOT).startswith(abspath(ROOT))` — and on **Linux a Windows path is
        not absolute at all**, so `abspath(r"D:\\wrds")` resolves to
        `/home/runner/.../valuation-tool/D:\\wrds`, which *is* under the repo, and "outside the
        repo" came back False. That is `MA42`'s family: a backslash is an ordinary filename
        character on POSIX, so a path written in one flavour may only be compared in that flavour.

        Compared with `ntpath` explicitly, which is the flavour the constant is written in.
        """
        import ntpath
        self.assertTrue(ntpath.isabs(C.RAW_ROOT), C.RAW_ROOT)
        drive = ntpath.splitdrive(C.RAW_ROOT)[0].upper()
        self.assertTrue(drive and drive != "C:",
                        "payload must not sit on the volume holding the checkout: %r"
                        % C.RAW_ROOT)
        # And it must be the client's own constant rather than a second copy (`MA5`).
        from valuation.edge import wrds_client as W
        self.assertEqual(C.RAW_ROOT, W.DEFAULT_RAW_ROOT)

    def test_the_raw_root_check_is_not_vacuous(self):
        """A positive control: the comparison must REJECT a repo-relative root, or the test above
        passes by looking at nothing."""
        import ntpath
        for bad in ("wrds_local", r".\wrds", "data/wrds"):
            self.assertFalse(ntpath.isabs(bad), bad)

    def test_this_sessions_spine_cannot_overwrite_another_sessions(self):
        """Round 3 wrote `stocknames.pkl` to the same root with a column this pass does not
        request. A collision there would destroy another session's payload."""
        self.assertNotEqual(C.SPINE_PKL, "stocknames.pkl")
        self.assertIn("EDGE_DRAFTS", C.SPINE_PKL)

    def test_no_credential_is_ever_printed(self):
        """The client returns a path and never a password; this module must not print either."""
        tree = ast.parse(_src("scripts/edge_drafts_collect.py"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print":
                for a in ast.walk(n):
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        low = a.value.lower()
                        self.assertNotIn("password", low)
                        self.assertNotIn("passwd", low)

    def test_the_licence_note_travels_in_the_artifact(self):
        src = _src("scripts/edge_drafts_collect.py")
        self.assertIn("ACADEMIC RESEARCH ONLY", src)
        self.assertIn("may NEVER feed the live score", src)


class TheCollectionProbesBeforeAggregating(unittest.TestCase):

    def test_every_column_is_resolved_rather_than_assumed(self):
        """The scout's defect: `mgrno` is Thomson's column applied to WRDS's own product."""
        src = _src("scripts/edge_drafts_collect.py")
        self.assertIn("entitlement is not schema", src)
        self.assertIn("_pick(", src)

    def test_pick_names_what_was_actually_there_when_it_fails(self):
        """A refusal that does not say what the table HAS costs another connection."""
        with self.assertRaises(KeyError) as cm:
            C._pick(["alpha", "beta"], ("gamma",), "manager-id")
        self.assertIn("alpha", str(cm.exception))

    def test_pick_is_case_insensitive_and_returns_the_real_spelling(self):
        self.assertEqual(C._pick(["CUSIP_ID"], ("cusip_id",), "cusip"), "CUSIP_ID")

    def test_the_manager_candidates_include_the_column_that_actually_worked(self):
        """Measured 2026-10-19: the real column is `cik`, not `mgrno`."""
        self.assertIn("cik", C.MGR_CANDIDATES)
        self.assertIn("mgrno", C.MGR_CANDIDATES)


def _data_root():
    """ASKS without committing. `dipcall.data_root(required=True)` RAISES when there is no
    populated root, and its own docstring records that the raising form "broke this item's own
    suite in CI" — `data/` is gitignored, so a runner has no populated root at all."""
    from valuation.studies import dipcall as D
    return D.data_root(required=False)


def _skip_loudly(case, why):
    """A skip nobody can mistake for a pass. The repo's own idiom — `test_fleet_doors` prints
    `(SKIPPED LOUDLY: ...)` — because a silent skip and a pass look identical in a 327-suite run."""
    msg = "(SKIPPED LOUDLY: %s)" % why
    print("\n       %s" % msg, flush=True)
    case.skipTest(msg)


class TheTierIsTheCorrectedRawUniverse(unittest.TestCase):

    def test_the_tier_is_built_from_the_corrected_raw_panel(self):
        """Asks for the root without committing, so CI skips loudly instead of aborting."""
        if _data_root() is None:
            _skip_loudly(self, "no populated data/ root on this machine - gitignored, so CI "
                               "never has it")
        from valuation.studies import dipcall as D
        self.assertIn("UNIVERSE_BIAS_PANEL_full", os.path.basename(D.panel_path()))

    def test_the_floor_is_ten_billion(self):
        self.assertEqual(C.TIER_FLOOR, 10e9)
        self.assertEqual(K.TIER_FLOOR, 10e9)

    def test_the_round_3_join_figure_is_not_inherited(self):
        """`O-1` applied a coverage figure from one population to another and was ~17x wrong."""
        self.assertIn("NOT_THE_81_65", _src("scripts/edge_drafts_collect.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
