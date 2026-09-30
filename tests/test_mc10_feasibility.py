# -*- coding: utf-8 -*-
"""MC10 — the STEP 0 gate fired, so the register does not exist and no trial was booked.

THE LOAD-BEARING PINS ARE ABSENCES. An item that closes at its own gate is easy to "finish"
later by quietly running the arm anyway, so what needs guarding is that nothing downstream of
the gate exists: no `PREREG_mc10_*.md`, no research-log row, no arm runner, and no mean
difference anywhere in the feasibility pass.

`MB15` separation is the rule: the feasibility pass measures DISPERSION, and the mean of the
paired difference is the OUTCOME. A standard error says how precisely a thing could be measured;
computing the thing is the arm.
"""
from __future__ import annotations

import ast
import io
import json
import os
import unittest

import state_isolation  # noqa: F401  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FA = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data", "free_analysis")
ART = os.path.join(FA, "MC10_FEASIBILITY.json")


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _art():
    if not os.path.exists(ART):
        return None
    with io.open(ART, encoding="utf-8") as fh:
        return json.load(fh)


class TestNothingDownstreamOfTheGateExists(unittest.TestCase):

    def test_no_register_was_committed(self):
        """STEP 1 is gated on STEP 0 passing. It did not pass."""
        for f in os.listdir(ROOT):
            self.assertFalse(f.lower().startswith("prereg_mc10"),
                             "a MC10 register exists but the STEP 0 gate fired: %s" % f)

    def test_no_research_log_row_and_no_trial(self):
        log = _read("RESEARCH_LOG.md")
        self.assertNotIn("| MC10 |", log,
                         "MC10 booked a trial, but the gate closes it at zero")

    def test_the_equity_count_is_unchanged_at_248(self):
        """The stamp is the tamper-evidence; MC10 must not have moved it."""
        src = _read("tests", "test_research_log_integrity.py")
        self.assertIn('"equity": 248', src)

    def test_no_arm_runner_exists(self):
        for f in os.listdir(os.path.join(ROOT, "scripts")):
            if f.startswith("mc10_"):
                self.assertEqual(f, "mc10_feasibility.py",
                                 "a second MC10 script exists: %s" % f)


class TestTheFeasibilityPassComputesNoOutcome(unittest.TestCase):
    """`MB15`: the mean of the paired difference is the outcome and must not survive the pass."""

    def test_the_artifact_banks_no_mean_difference(self):
        a = _art()
        if a is None:
            self.skipTest("MC10_FEASIBILITY.json absent (data/ is gitignored)")
        flat = json.dumps(a).lower()
        for bad in ("mean_diff", "diff_mean", "net_difference", "delta_net"):
            self.assertNotIn(bad, flat, "the artifact banks an outcome: %r" % bad)
        self.assertIn("paired_se", a)
        self.assertIsNotNone(a["paired_se"]["annualised"])

    def test_the_mean_is_deleted_in_the_source(self):
        """Asserted against the syntax tree: the local holding the mean must be `del`-ed, so it
        cannot reach a print or an artifact by a later edit that forgets why."""
        tree = ast.parse(_read("scripts", "mc10_feasibility.py"))
        deleted = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Delete):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        deleted.add(t.id)
        self.assertIn("_m", deleted,
                      "the mean of the paired difference is not deleted; MB15 separation "
                      "depends on it not surviving the expression that consumes it")


class TestTheGateFiredAndWhy(unittest.TestCase):

    def test_the_gate_fired(self):
        a = _art()
        if a is None:
            self.skipTest("MC10_FEASIBILITY.json absent (data/ is gitignored)")
        g = a["GATE"]
        self.assertTrue(g["fires"])
        self.assertGreater(g["mde80_crit2"], g["threshold"])
        self.assertAlmostEqual(g["threshold"], 0.0083, places=12,
                               msg="the gate threshold is the brief's, not one chosen here")

    def test_the_two_books_are_nearly_the_same_series(self):
        """The mechanism behind the gate: a correlation this high is a property of the RULE,
        so more dates cannot rescue the design."""
        a = _art()
        if a is None:
            self.skipTest("artifact absent")
        self.assertGreater(a["rho_net_ew_sw"], 0.99)

    def test_the_eight_percent_cap_never_binds(self):
        a = _art()
        if a is None:
            self.skipTest("artifact absent")
        self.assertFalse(a["cap"]["ever_binds"])
        self.assertLess(a["cap"]["max_weight_seen"], 0.08)

    def test_C5_direction_is_reported_not_assumed(self):
        """SW turnover >= EW turnover. Measured, and the brief says REPORT it."""
        a = _art()
        if a is None:
            self.skipTest("artifact absent")
        self.assertGreaterEqual(a["turnover"]["sw_annual"], a["turnover"]["ew_annual"])


class TestTheThreeWeightingsAreDistinct(unittest.TestCase):
    """`C2`'s relabel. These are source facts and hold with no data present."""

    def test_the_artifact_rule_is_level_proportional_and_uncapped(self):
        src = _read("valuation", "edge", "fundamental_panel.py")
        self.assertIn("np.clip(comp[top], 0.0, None)", src,
                      "the artifact's signal weighting changed; the MC10 relabel is stale")

    def test_the_served_rule_is_rank_based(self):
        """`hot_score` is the composite's PERCENTILE RANK, so the served weight cannot be a
        function of the composite's level."""
        self.assertIn('rank(pct=True) * 99 + 1', _read("valuation", "screener", "screen.py"))

    def test_the_served_rule_subtracts_a_cohort_floor_and_caps(self):
        src = _read("valuation", "edge", "valquo_index.py")
        self.assertIn("MAX_WEIGHT = 0.08", src)
        self.assertIn("- floor + 1.0", src,
                      "the served weighting no longer subtracts the cohort floor")


class TestTheTwoDecileDefinitionsDiffer(unittest.TestCase):
    """Reported, not reconciled: `construction.*` and `costs.*` are measured on books that
    differ by one name on most dates."""

    def test_both_definitions_are_still_in_the_tree(self):
        src = _read("valuation", "edge", "fundamental_panel.py")
        self.assertIn("np.array_split(order, n_q)", src)
        self.assertIn("int(len(sub) * top_frac)", src)

    def test_they_really_do_differ_on_a_realistic_cross_section(self):
        import numpy as np
        n = 1655
        self.assertEqual(len(np.array_split(np.arange(n), 10)[0]), 166)
        self.assertEqual(int(n * 0.1), 165)


if __name__ == "__main__":
    unittest.main(verbosity=2)
