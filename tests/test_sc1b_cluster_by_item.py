# -*- coding: utf-8 -*-
"""SC-1b -- clustering the prior-calibration gap by ITEM. `PREREG_sc1b_cluster_by_item.md`.

The pins that matter are the ones protecting the claim *"only the clustering key changed"*:

* **the bars are SC-1's BY IMPORT**, never re-typed here -- an AST guard fails if this module
  contains a literal copy of the 0.15 ceiling, the draw count or the seed, because a re-typed
  bar is a re-chosen bar and that is the one thing the register exists to prevent;
* **the double-entry control reproduces SC-1's PREDICATE**, including the class-agreement half
  that the first cut dropped -- without it the check returns a confident 0.0000 and cannot fail;
* **the item key is level 1-2 only**, with its declared failure direction (a mis-levelled
  heading MERGES items, widening the interval) exercised rather than asserted;
* **a suspect interval carries no verdict** -- G3 failing forces CANNOT-TELL whatever the
  half-width says.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
_SCRIPTS = os.path.join(REPO, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import sc1_prior_calibration as SC1                     # noqa: E402
import sc1b_cluster_by_item as B                        # noqa: E402

_SKIPS = []
RUNNER = os.path.join(REPO, "scripts", "sc1b_cluster_by_item.py")
REGISTER = os.path.join(REPO, "PREREG_sc1b_cluster_by_item.md")


def _src(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _tree(p):
    return ast.parse(_src(p))


def _named(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _numeric_literals(t):
    return {n.value for n in ast.walk(t)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)}


# =============================================================================================
class TestTheBarsAreSC1s(unittest.TestCase):
    """§0 and §3: the bars are reused VERBATIM, which here means BY IMPORT."""

    def test_no_bar_is_re_typed_in_this_module(self):
        lits = _numeric_literals(_tree(RUNNER))
        for banned, what in ((SC1.CALIBRATED_MAX_HALFWIDTH, "the 0.15 half-width ceiling"),
                             (SC1.BOOT, "the bootstrap draw count"),
                             (SC1.SEED, "the seed"),
                             (SC1.KILL_MIN_PAIRS, "the pair-count kill"),
                             (SC1.KILL_MAX_DISAGREE, "the double-entry kill")):
            self.assertNotIn(banned, lits,
                             f"{what} is re-typed here; a re-typed bar is a re-chosen bar")

    def test_the_bars_are_reached_through_SC1(self):
        names = _named(_tree(RUNNER))
        for required in ("CALIBRATED_MAX_HALFWIDTH", "KILL_MIN_PAIRS", "KILL_MAX_DISAGREE",
                         "cluster_bootstrap", "naive_bootstrap", "gap", "brier", "murphy",
                         "scoring_rows", "adjudicate", "extract_primary"):
            self.assertIn(required, names, f"{required} is not reached through SC-1")

    def test_the_guard_is_not_vacuous(self):
        """It must find the literals that ARE here, or it proves nothing about the ones that
        are not."""
        lits = _numeric_literals(_tree(RUNNER))
        self.assertIn(2.0, lits, "crit 2.0 is used for the MDE and should be found")
        self.assertGreater(len(lits), 3)

    def test_no_statistic_is_re_implemented(self):
        defs = {n.name for n in ast.walk(_tree(RUNNER))
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for banned in ("gap", "brier", "murphy", "cluster_bootstrap", "naive_bootstrap",
                       "scoring_rows", "adjudicate", "extract_primary", "classify"):
            self.assertNotIn(banned, defs, f"{banned} is DEFINED here; it is SC-1's")


# =============================================================================================
class TestTheItemKey(unittest.TestCase):

    def _write(self, td, name, body):
        p = os.path.join(td, name)
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        return p

    def test_level_1_and_2_headings_split_items(self):
        import tempfile
        body = ("## MB18 - a thing\n"
                "| it happened | 60/40 | **RIGHT** |\n"
                "## MB21 - another thing\n"
                "| it did not | 30/70 | **WRONG** |\n")
        with tempfile.TemporaryDirectory() as td:
            rows = B.heading_rows(self._write(td, "HANDOFF_x.md", body))
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0][3], rows[1][3], "two items shared a cluster")

    def test_a_level_3_heading_does_NOT_split_and_that_is_the_declared_direction(self):
        """§2: a mis-levelled heading MERGES items -- fewer, larger clusters, a WIDER interval,
        a push toward CANNOT-TELL. The heuristic can cost a verdict; it cannot manufacture one."""
        import tempfile
        body = ("## One item\n"
                "### Expectations, scored\n"
                "| a | 60/40 | **RIGHT** |\n"
                "### Something else\n"
                "| b | 30/70 | **WRONG** |\n")
        with tempfile.TemporaryDirectory() as td:
            rows = B.heading_rows(self._write(td, "HANDOFF_y.md", body))
        self.assertEqual(len({r[3] for r in rows}), 1,
                         "a level-3 heading split the item; the failure direction is inverted")

    def test_identically_titled_sections_in_DIFFERENT_files_do_not_merge(self):
        import tempfile
        body = "## Expectations\n| a | 60/40 | **RIGHT** |\n"
        with tempfile.TemporaryDirectory() as td:
            a = B.heading_rows(self._write(td, "HANDOFF_a.md", body))
            b = B.heading_rows(self._write(td, "HANDOFF_b.md", body))
        self.assertNotEqual(a[0][3], b[0][3], "the file is not part of the key")

    def test_the_rescan_uses_SC1s_own_regexes(self):
        names = _named(_tree(RUNNER))
        self.assertIn("MARK", names)
        self.assertIn("ODDS", names)

    def test_alignment_refuses_when_the_two_scans_disagree(self):
        """G1b. If the re-scan and SC-1's own extraction ever drift, the item key is attached to
        the wrong rows and every cluster is wrong -- so it must REFUSE, not proceed."""
        out = B.attach_items([{"source_file": "x", "p": 0.6, "marker": "RIGHT"}], [])
        self.assertFalse(out["aligned"])
        self.assertEqual(out["rows_rescanned"], 0)


# =============================================================================================
class TestControls(unittest.TestCase):

    def test_double_entry_requires_the_CLASS_to_agree_as_well_as_the_value(self):
        """The defect this suite exists to keep fixed. Matching the odds VALUE alone returns a
        confident 0.0000 -- the class is the discriminating half. Caught by disbelieving a zero
        that disagreed with SC-1's published 11.7%."""
        src = _src(RUNNER)
        self.assertIn('c["class"] == r["class"]', src,
                      "the class-agreement half of SC-1's predicate is gone; the check cannot "
                      "fail without it")

    def test_a_suspect_interval_carries_no_verdict(self):
        """§4 G3: an interval NARROWER than naive voids §1's bound, and a bootstrap that tightens
        when you add structure is a symptom, not a sharper answer."""
        m = {"item_ci95": [-0.01, -0.001], "item_half_width": 0.0045}
        self.assertEqual(B.verdict_for(m, g3_ok=False), "CANNOT-TELL")
        # and it is NOT unconditional -- with G3 holding, the same numbers resolve
        self.assertEqual(B.verdict_for(m, g3_ok=True), "OVERCONFIDENT-PESSIMISTIC")

    def test_the_verdict_grammar_is_SC1s(self):
        wide = {"item_ci95": [-0.30, 0.20], "item_half_width": 0.25}
        self.assertEqual(B.verdict_for(wide, True), "CANNOT-TELL",
                         "a wide interval containing zero is never CALIBRATED")
        tight = {"item_ci95": [-0.10, 0.10], "item_half_width": 0.10}
        self.assertEqual(B.verdict_for(tight, True), "CALIBRATED-IN-THE-LARGE")
        self.assertEqual(B.verdict_for({"item_ci95": [0.01, 0.20],
                                        "item_half_width": 0.095}, True),
                         "OVERCONFIDENT-OPTIMISTIC")

    def test_the_ceiling_is_exactly_SC1s(self):
        m = {"item_ci95": [-0.15, 0.15], "item_half_width": SC1.CALIBRATED_MAX_HALFWIDTH}
        self.assertEqual(B.verdict_for(m, True), "CALIBRATED-IN-THE-LARGE",
                         "the bar is `<=`, as SC-1 wrote it")


# =============================================================================================
class TestDiscipline(unittest.TestCase):

    def test_no_market_data_is_opened(self):
        """Inherited from SC-1's C3. The corpus is markdown; nothing else may be reached."""
        imported = set()
        for n in ast.walk(_tree(RUNNER)):
            if isinstance(n, ast.Import):
                imported.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add(n.module or "")
        joined = " ".join(sorted(imported))
        for banned in ("pandas", "numpy", "fundamental_panel", "options", "yfinance",
                       "thetadata", "screener", "surface_stock", "crash_gate"):
            self.assertNotIn(banned, joined, f"{banned} is imported; no market data may be read")

    def test_this_register_does_not_supply_priors_to_its_own_study(self):
        """SC-1 excluded itself and its draft; the same principle excludes this one."""
        self.assertEqual(B.SELF, os.path.basename(REGISTER))
        src = _src(RUNNER)
        self.assertIn("SC1.SELF", src)
        self.assertIn("SC1.DRAFT", src)

    def test_the_corpus_is_pinned_to_SC1s_measurement_commit(self):
        self.assertEqual(B.SC1_COMMIT, "8e2e9fe")
        self.assertIn("8e2e9fe", _src(REGISTER) + _src(RUNNER))

    def test_the_register_is_on_disk_and_states_the_structural_bound(self):
        self.assertTrue(os.path.isfile(REGISTER))
        txt = _src(REGISTER)
        # NOTE: an earlier cut of this list asserted the word "counterfactual", copied from a
        # sibling register whose licence WAS a counterfactual argument. SC-1b's licence is
        # stronger and different in kind -- SC-1 named this successor IN WRITING before its own
        # interval existed -- so the assertion was mis-specified and is replaced by the quote
        # that actually does the work. Correcting a guard that tests the wrong property is not
        # loosening it.
        for needed in ("UNREACHABLE", "0.11919", "0.19167", "RECURSION IS NOTICED",
                       "named here as the obvious successor",
                       "CALIBRATED-IN-THE-LARGE", "CANNOT-TELL"):
            self.assertIn(needed, txt, f"the register no longer contains {needed!r}")

    def test_the_arms_pass_refuses_without_a_passing_controls_artifact(self):
        import tempfile
        saved = B.CTRL_JSON
        try:
            with tempfile.TemporaryDirectory() as td:
                args = type("A", (), {"out_dir": td})()
                B.CTRL_JSON = "absent.json"
                self.assertEqual(B.run_arms(args), 2, "a MISSING controls file must refuse")
                B.CTRL_JSON = "failing.json"
                with io.open(os.path.join(td, "failing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": false}')
                self.assertEqual(B.run_arms(args), 2, "a FAILING controls file must refuse")
        finally:
            B.CTRL_JSON = saved


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
