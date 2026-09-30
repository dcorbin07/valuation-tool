# -*- coding: utf-8 -*-
"""D9 — the free-route fidelity check.

WHAT THESE PIN. The verdict is a NO-GO, so what needs guarding is that nothing quietly turns it
into a GO: the bars must stay where the register put them, the degenerate-theme repair must stay
reported rather than substituted, and the opt-in theme emission must stay inert by default.

* **`with_themes=False` IS INERT.** A production function grew a parameter; every existing
  caller's row shape must be unchanged (`C3`).
* **THE BARS ARE THE REGISTER'S.** `W-28`'s rule: a successor may not relax a pre-committed bar
  after watching it fail.
* **EXPOSURE IS NOT INFORMATION.** The live `insider` theme is constant, and a constant must
  never be scored as agreement. That is the defect the addendum exists to report.
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


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _art(name):
    p = os.path.join(FA, name)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


class TestTheOptInEmissionIsInert(unittest.TestCase):

    def test_with_themes_exists_and_defaults_to_false(self):
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "score_universe_now")
        args = [a.arg for a in fn.args.args]
        self.assertIn("with_themes", args)
        i = args.index("with_themes")
        j = i - (len(fn.args.args) - len(fn.args.defaults))
        self.assertGreaterEqual(j, 0, "with_themes has no default")
        d = fn.args.defaults[j]
        self.assertIsInstance(d, ast.Constant)
        self.assertIs(d.value, False, "with_themes must default to False")

    def test_every_use_requires_with_themes(self):
        """The emission must sit under `if with_themes:` and nothing else, or the default row
        shape changes and `C3` breaks for every existing caller."""
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        seen = 0
        for n in ast.walk(tree):
            if isinstance(n, ast.If) and "with_themes" in ast.unparse(n.test):
                seen += 1
                self.assertIsInstance(n.test, ast.Name,
                                      "the guard is not a bare `if with_themes:`: %s"
                                      % ast.unparse(n.test))
        self.assertEqual(seen, 1, "expected exactly one with_themes guard, found %d" % seen)

    def test_it_emits_the_canonical_theme_list_rather_than_a_retyped_one(self):
        """`MA5`: a second list of theme names is a second definition of the theme set."""
        src = _read("valuation", "edge", "fundamental_panel.py")
        self.assertIn("for _th in S.FACTORS_ALL:", src,
                      "the emission retypes the theme list instead of importing it")


class TestTheBarsAreTheRegisters(unittest.TestCase):

    BARS = {"B1_COMPOSITE_SPEARMAN": 0.80, "B2_DECILE_OVERLAP": 0.60,
            "B3_THEME_SPEARMAN": 0.70}

    def test_the_runner_still_carries_the_registered_bars(self):
        src = _read("scripts", "d9_fidelity.py")
        tree = ast.parse(src)
        got = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
                if n.targets[0].id in self.BARS and isinstance(n.value, ast.Constant):
                    got[n.targets[0].id] = n.value.value
        self.assertEqual(got, self.BARS,
                         "a D9 bar moved; W-28's rule forbids relaxing one after it fails")

    def test_the_register_is_on_disk_and_names_the_bars(self):
        t = _read("PREREG_d9_free_route_fidelity.md")
        for v in ("0.80", "0.60", "0.70"):
            self.assertIn(v, t)
        self.assertIn("0.9190", t, "FIDELITY-2's cited figure is missing")
        self.assertIn("0.8726", t)

    def test_fidelity2_is_cited_not_recomputed(self):
        """B4 says cited. A re-derivation here would spend a second measurement on a settled
        question and could disagree with the published figure."""
        src = _read("scripts", "d9_fidelity.py")
        self.assertIn("FIDELITY2 = {", src)
        self.assertIn("CITED", src)


class TestExposureIsNotInformation(unittest.TestCase):

    def test_the_live_insider_theme_was_constant_and_is_recorded_as_such(self):
        a = _art("D9_FIDELITY.json")
        if a is None:
            self.skipTest("D9_FIDELITY.json absent (data/ is gitignored)")
        add = a.get("addendum_insider_degeneracy", {}).get("freeze_2026-07-31")
        self.assertIsNotNone(add, "the insider diagnostic is missing")
        self.assertEqual(add["live_insider_distinct_values"], 1)
        self.assertIsNone(add["insider_spearman"],
                          "a constant must not be scored as a correlation")

    def test_both_readings_are_banked_and_the_repair_did_not_change_the_verdict(self):
        a = _art("D9_FIDELITY.json")
        if a is None:
            self.skipTest("artifact absent")
        add = a["addendum_insider_degeneracy"]["freeze_2026-07-31"]
        self.assertIn("as_registered_5_theme", add)
        self.assertIn("repaired_4_theme_insider_dropped", add)
        self.assertTrue(add["verdict_unchanged_by_the_repair"],
                        "the verdict now hinges on a post-hoc construction change; A6 makes "
                        "that a NO-GO regardless")

    def test_the_verdict_is_no_go(self):
        a = _art("D9_FIDELITY.json")
        if a is None:
            self.skipTest("artifact absent")
        self.assertEqual(a["VERDICT"], "NO-GO")
        self.assertEqual(sorted(a["readings"]["freeze_2026-07-31"]["failing"]),
                         ["B1", "B2", "B3"])


class TestTheCeilingCameFirst(unittest.TestCase):

    def test_the_ceiling_is_banked_and_is_within_vendor(self):
        c = _art("D9_NOISE_CEILING.json")
        if c is None:
            self.skipTest("D9_NOISE_CEILING.json absent")
        self.assertIn("1_rebalances_63_trading_days", c["by_lag"])
        self.assertLess(c["by_lag"]["1_rebalances_63_trading_days"]
                        ["composite_spearman_mean"], 1.0)

    def test_the_interpolation_is_labelled_as_one(self):
        """Quoting the interpolated ceiling as a measurement is a void condition."""
        c = _art("D9_NOISE_CEILING.json")
        if c is None:
            self.skipTest("artifact absent")
        self.assertIn("INTERPOLATION", c["applicable_gap"]["LABEL"])


class TestTheStoreCensusRecordsTheSyntheticFinding(unittest.TestCase):

    def test_the_local_scan_stores_are_recorded_as_carrying_no_live_scans(self):
        c = _art("D9_STORE_CENSUS.json")
        if c is None:
            self.skipTest("D9_STORE_CENSUS.json absent")
        self.assertFalse(
            c["verdict"]["a_live_scan_snapshot_on_or_after_2026_07_31_exists_locally"])
        self.assertTrue(c["stores"]["archive/scans"]["all_synthetic"],
                        "the archive is no longer all-synthetic; the census note is stale")


if __name__ == "__main__":
    unittest.main(verbosity=2)
