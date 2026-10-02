# -*- coding: utf-8 -*-
"""IC1 (closed at K2, zero trials) and IC7 (rejected, 1 trial).

WHAT THESE PIN, and the two items need different things.

IC1 closed at a free kill, so the load-bearing pins are ABSENCES — an item closed at its own
gate is easy to "finish" later by quietly running the arm. And the `grid_dates` extension it
needed must stay inert, because `book_configs` and every banked panel depend on the shipped
grid.

IC7 ran, so what matters is that the thing it scored is the thing it claims: the two weightings
must actually DIFFER (a second check that cannot differ is not a second check — the defect this
item shipped and repaired), the gate must get a column SET rather than a weights dict in the
label slot, and the verdict must travel with its MDE.
"""
from __future__ import annotations

import ast
import io
import json
import os
import unittest

import state_isolation  # noqa: F401  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _candidates():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(ROOT, "data"))
    parts = ROOT.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    return out


def _art(name):
    for d in _candidates():
        p = os.path.join(d, "free_analysis", name)
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as fh:
                return json.load(fh)
    return None


class TestIC1ClosedAtItsKill(unittest.TestCase):
    """Absences, because an item closed at its gate is easy to quietly finish."""

    def test_no_ic1_register_exists(self):
        for f in os.listdir(ROOT):
            self.assertFalse(f.lower().startswith("prereg_ic1"),
                             "an IC1 register exists but K2 fired: %s" % f)

    def test_ic1_booked_no_trial(self):
        self.assertNotIn("| IC1 |", _read("RESEARCH_LOG.md"),
                         "IC1 booked a trial, but it closed at a free kill")

    def test_no_ic1_arm_runner_exists(self):
        for f in os.listdir(os.path.join(ROOT, "scripts")):
            if f.startswith("ic1_"):
                self.assertIn(f, ("ic1_kills.py", "ic1_build.py"),
                              "an IC1 arm runner exists: %s" % f)

    def test_k2_really_fired(self):
        a = _art("IC1_K2.json")
        if a is None:
            self.skipTest("IC1_K2.json absent")
        self.assertFalse(a["K2_pass"], "K2 no longer fires; the IC1 handoff is stale")
        self.assertLess(a["cross_section"]["min"], a["K2_bar"]["min"])

    def test_the_bar_was_not_relaxed(self):
        """`W-28`: a bar may not be relaxed after watching it fail."""
        tree = ast.parse(_read("scripts", "ic1_build.py"))
        got = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                    isinstance(n.targets[0], ast.Tuple):
                names = [t.id for t in n.targets[0].elts if isinstance(t, ast.Name)]
                if names == ["PANEL_MIN_XS", "PANEL_MAX_XS"]:
                    got = {k: v.value for k, v in zip(names, n.value.elts)}
        self.assertEqual(got, {"PANEL_MIN_XS": 1471, "PANEL_MAX_XS": 1954},
                         "the K2 bar moved -- W-28 forbids relaxing one after it fails")


class TestTheGridExtensionIsInert(unittest.TestCase):

    def test_grid_dates_defaults_to_none(self):
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build_fundamental_panel"]
        self.assertEqual(len(fn), 1)
        names = [a.arg for a in fn[0].args.args]
        self.assertIn("grid_dates", names)
        off = len(names) - len(fn[0].args.defaults)
        d = fn[0].args.defaults[names.index("grid_dates") - off]
        self.assertIsInstance(d, ast.Constant)
        self.assertIsNone(d.value)

    def test_grid_dates_and_grid_offset_are_mutually_exclusive(self):
        """Shifting an already-absolute grid would silently re-phase it."""
        src = _read("valuation", "edge", "fundamental_panel.py")
        self.assertIn("pass grid_dates OR grid_offset, not both", src)

    def test_the_shipped_grid_is_still_the_default_path(self):
        """The `else` branch must still build the TD+offset range, or every banked panel moves."""
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build_fundamental_panel"][0]
        calls = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "range"
                 and any(isinstance(a, ast.Name) and a.id == "_GRID_START" for a in n.args)]
        self.assertTrue(calls, "the default TD+offset grid is gone")


class TestIC7ScoredTheThingItClaims(unittest.TestCase):

    def test_the_two_weightings_actually_differ(self):
        """THE DEFECT THIS ITEM SHIPPED AND REPAIRED. A second check that cannot differ is not
        a second check: both scorings once used the same `cols` and returned identical splits."""
        # SOURCE first, because the artifact is stale under a source mutation and an
        # artifact-only guard cannot see one. The loop must score two DIFFERENT column sets.
        tree = ast.parse(_read("scripts", "ic7_arm.py"))
        sets = []
        for n in ast.walk(tree):
            if isinstance(n, ast.For) and isinstance(n.iter, ast.Tuple)                     and len(n.iter.elts) == 2                     and all(isinstance(e, ast.Tuple) and len(e.elts) == 2
                            for e in n.iter.elts):
                names = [e.elts[1].id for e in n.iter.elts
                         if isinstance(e.elts[1], ast.Name)]
                if len(names) == 2:
                    sets.append(names)
        self.assertTrue(sets, "the two-weighting loop is gone")
        for a_, b_ in sets:
            self.assertNotEqual(a_, b_,
                                "both weightings score the SAME column set -- a second check "
                                "that cannot differ is not a second check")
        # then the artifact, which is what the claim in the handoff rests on
        a = _art("IC7_ARM.json")
        if a is None:
            self.skipTest("IC7_ARM.json absent")
        self.assertNotEqual(a["deployed"]["splits"], a["flat"]["splits"],
                            "the two weightings returned identical splits -- vacuous")

    def test_the_gate_gets_a_column_set_not_a_weights_dict(self):
        """`holdout_compare_panels`' 4th positional parameter is `label_a`, not weights."""
        a = _art("IC7_ARM.json")
        if a is None:
            self.skipTest("IC7_ARM.json absent")
        self.assertIsInstance(a["deployed"]["label_a"], str,
                              "a weights dict landed in the LABEL slot again -- the composite "
                              "is being built from `cols`, not from those weights")

    def test_the_arm_runner_refuses_without_its_kills(self):
        """The refusal must be REACHABLE, which a substring cannot tell you.

        A first cut asserted `"REFUSING" in src` and MISSED the mutation that replaces the
        guard with `if False:` -- the string is still there, just unreachable. Asserted on the
        AST instead: the `if` guarding the raise must test something real, and `ast.Constant`
        is structurally not that.
        """
        tree = ast.parse(_read("scripts", "ic7_arm.py"))
        guards = []
        for n in ast.walk(tree):
            if not isinstance(n, ast.If):
                continue
            raises = [c for c in ast.walk(n)
                      if isinstance(c, ast.Raise) and isinstance(c.exc, ast.Call)
                      and isinstance(c.exc.func, ast.Name) and c.exc.func.id == "SystemExit"]
            if raises:
                guards.append(n)
        self.assertTrue(guards, "no SystemExit refusal remains in the arm runner")
        for g in guards:
            self.assertNotIsInstance(
                g.test, ast.Constant,
                "a refusal is guarded by a constant, so it can never fire")
        # and one of them must actually consult the kills artifact
        consults = [g for g in guards
                    if any(isinstance(c, ast.Name) and c.id == "KILLS" for c in ast.walk(g))]
        self.assertTrue(consults,
                        "no refusal reads the kills artifact; the arm could run without it")

    def test_the_margins_are_the_registered_ones(self):
        tree = ast.parse(_read("scripts", "ic7_arm.py"))
        got = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                    isinstance(n.targets[0], ast.Name) and \
                    n.targets[0].id in ("MARGIN_ALPHA", "MARGIN_TSTAT") and \
                    isinstance(n.value, ast.Constant):
                got[n.targets[0].id] = n.value.value
        self.assertEqual(got, {"MARGIN_ALPHA": 0.01, "MARGIN_TSTAT": 0.25})

    def test_the_verdict_is_rejected_and_ships_its_mde(self):
        a = _art("IC7_ARM.json")
        if a is None:
            self.skipTest("IC7_ARM.json absent")
        self.assertEqual(a["deployed"]["verdict"], "reject")
        self.assertEqual(a["flat"]["verdict"], "reject")
        p = a["paired"]
        for k in ("hac_se", "hac_t", "mde_80_ann_pp", "mde_80_at_hurdle_ann_pp"):
            self.assertIn(k, p)
        self.assertLess(abs(p["mean_ann_pp"]), p["mde_80_ann_pp"],
                        "the effect now exceeds its own 80%-power threshold; the 'bounded "
                        "null' reading in the handoff is stale")

    def test_the_row_set_is_identical(self):
        a = _art("IC7_ARM.json")
        if a is None:
            self.skipTest("IC7_ARM.json absent")
        c = a["C_identical_rows"]
        self.assertTrue(c["same_shape"] and c["same_keys"])
        self.assertTrue(all(c["untouched_themes_bit_identical"].values()),
                        "a theme with no holes changed -- the arm is doing more than imputing")

    def test_nothing_was_adopted(self):
        import valuation.screener.settings as S
        self.assertEqual(S.WEIGHTS_ESTABLISHED["institutional"], 0.125)
        self.assertEqual(S.BOOK_CONFIGS["taxable"]["exit_frac"], 0.3)


class TestTheFreeKillsAreOnTheRecord(unittest.TestCase):

    def test_ic7_kills_all_passed_and_none_fired(self):
        k = _art("IC7_KILLS.json")
        if k is None:
            self.skipTest("IC7_KILLS.json absent")
        self.assertEqual(k["any_kill_fired"], [])
        self.assertTrue(k["K4_fidelity"]["pass"])
        self.assertEqual(k["K4_fidelity"]["worst"], 0.0)
        self.assertEqual(k["K4_fidelity"]["fields_compared"], 4)

    def test_the_exposure_is_the_measured_one_not_the_drafts(self):
        """Amendment 1: the draft said ~28%, the union of five holes is ~42%."""
        k = _art("IC7_KILLS.json")
        if k is None:
            self.skipTest("IC7_KILLS.json absent")
        s = k["K1_exposure_census"]["share_of_rows_missing_at_least_one_weighted_theme"]
        self.assertGreater(s, 0.35, "the exposure fell below the measured 41.69%")

    def test_no_date_is_uniform_only(self):
        """Amendment 2: the hypothesis that the early half is provably inert was REFUTED."""
        a = _art("IC7_INERTNESS.json")
        if a is None:
            self.skipTest("IC7_INERTNESS.json absent")
        self.assertEqual(a["uniform_only_dates"], 0,
                         "a uniform-only date appeared; the arm would be provably inert there "
                         "and the handoff's refutation is stale")
        self.assertEqual(a["dates_with_a_partial_hole"], a["dates_total"])

    def test_ic1_k3_is_one_quarter_step(self):
        q = _art("IC1_K3_QUARTERLAG.json")
        if q is None:
            self.skipTest("IC1_K3_QUARTERLAG.json absent")
        self.assertAlmostEqual(q["mean_step_quarters"], 1.0, places=9)
        self.assertEqual(q["shipped_mean"], 2.0)
        self.assertEqual(q["aligned_mean"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
