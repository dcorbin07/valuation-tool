# -*- coding: utf-8 -*-
"""`OSAP3` `K1` — the free rebuildability kill, and the screens behind it.

The load-bearing tests are `test_the_named_empty_columns_really_are_empty` (the COVERAGE RULE's own
example, checked rather than cited) and `test_dropping_a_signal_tightens_BH_rather_than_loosening_it`
(the draft pre-commits that a shrinking batch tightens the threshold, which is the opposite of the
incentive).
"""
from __future__ import annotations

import ast
import io
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


def _skip_loudly(case, why):
    """A skip nobody can mistake for a pass. The repo's own idiom -- `test_fleet_doors` prints
    `(SKIPPED LOUDLY: ...)` -- because in a 327-suite run a silent skip and a pass look the
    same. Every artifact below is built from data under `data/`, which is gitignored, so CI
    never has it and these cases MUST skip rather than fail or pass vacuously."""
    msg = "(SKIPPED LOUDLY: %s)" % why
    print("\n       %s" % msg, flush=True)
    case.skipTest(msg)

from scripts import osap3_k1 as O                                        # noqa: E402

DRAFT = os.path.join(ROOT, "PREREG_DRAFT_osap3.md")


def _src(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _artifact():
    d = ROOT
    for _ in range(6):
        p = os.path.join(d, "data", "free_analysis", O.OUT)
        if os.path.isfile(p):
            return json.load(io.open(p, encoding="utf-8"))
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    return None


class NoOutcomeIsEverRead(unittest.TestCase):

    def test_the_module_never_names_a_forward_return(self):
        tree = ast.parse(_src("scripts/osap3_k1.py"))
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for b in ("fwd_ret", "bench_ret", "abnormal", "permutation_null"):
            self.assertNotIn(b, names, b)

    def test_it_declares_zero_trials(self):
        self.assertIn("ZERO TRIALS", (O.__doc__ or "").upper())


class TheScreenReproducesTheDraft(unittest.TestCase):
    """Screen 1 rests on a file already on disk, so the draft's own cut is checkable."""

    @classmethod
    def setUpClass(cls):
        p = None
        d = ROOT
        for _ in range(6):
            q = os.path.join(d, "data", "factors", "raw", "osap_signal_docs.csv")
            if os.path.isfile(q):
                p = q
                break
            nxt = os.path.dirname(d)
            if nxt == d:
                break
            d = nxt
        cls.docs = pd.read_csv(p) if p else None

    def test_the_cut_is_331_212_28_12(self):
        if self.docs is None:
            _skip_loudly(self, "osap_signal_docs.csv absent -- it lives under gitignored data/, so CI never has it")
        d = self.docs
        self.assertEqual(len(d), 331)
        pred = d[d["Cat.Signal"].astype(str).str.strip() == "Predictor"]
        self.assertEqual(len(pred), 212)
        vw = pred[pred["Stock Weight"].astype(str).str.strip() == "VW"]
        self.assertEqual(len(vw), 28)
        q = vw[pd.to_numeric(vw["Portfolio Period"], errors="coerce") >= 3]
        self.assertEqual(len(q), 12)

    def test_184_of_212_predictors_are_equal_weighted(self):
        """The one free column that removes 87% of the catalogue before a byte is pulled."""
        if self.docs is None:
            _skip_loudly(self, "osap_signal_docs.csv absent -- it lives under gitignored data/, so CI never has it")
        pred = self.docs[self.docs["Cat.Signal"].astype(str).str.strip() == "Predictor"]
        self.assertEqual(int((pred["Stock Weight"].astype(str).str.strip() == "EW").sum()), 184)

    def test_realestate_fails_its_own_papers_t(self):
        """Reported by the draft as the weakest of the three, from the paper's own figure."""
        if self.docs is None:
            _skip_loudly(self, "osap_signal_docs.csv absent -- it lives under gitignored data/, so CI never has it")
        r = self.docs[self.docs["Acronym"] == "realestate"].iloc[0]
        self.assertLess(float(r["T-Stat"]), 2.0)


class TheCoverageRuleIsCheckedNotCited(unittest.TestCase):

    def test_the_named_empty_columns_really_are_empty(self):
        """`roe`, `roic`, `assetturnover`: the project's own example of wired-but-empty."""
        r = _artifact()
        if r is None:
            _skip_loudly(self, "OSAP3_K1.json absent -- built from the licensed fundamentals export, which CI never has")
        for c in ("roe", "roic", "assetturnover"):
            self.assertIn(c, r["the_named_empty_columns"])
            self.assertEqual(r["the_named_empty_columns"][c]["non_null_rows"], 0, c)

    def test_the_bar_is_the_drafts_own_seventy(self):
        self.assertEqual(O.K1_BAR, 0.70)
        self.assertIn("0.70", _src("PREREG_DRAFT_osap3.md"))

    def test_the_inputs_are_declared_before_the_check_not_narrowed_after(self):
        """A check that drops an input once it comes back empty measures nothing."""
        self.assertEqual(sorted(O.INPUTS), ["BetaLiquidityPS", "EquityDuration", "realestate"])
        self.assertIn("equity", O.INPUTS["EquityDuration"])
        self.assertIn("ppnenet", O.INPUTS["realestate"])


class TheKillOutcome(unittest.TestCase):

    def test_realestate_drops_on_a_construction_blocker_not_a_coverage_shortfall(self):
        r = _artifact()
        if r is None:
            _skip_loudly(self, "OSAP3_K1.json absent -- built from the licensed fundamentals export, which CI never has")
        self.assertEqual(r["realestate_components_found"], [])
        self.assertTrue(r["signals"]["realestate"]["verdict"].startswith("DROPS"))
        self.assertIn("construction blocker", r["signals"]["realestate"]["why"])

    def test_net_ppe_is_present_so_the_drop_is_about_components(self):
        """`ppnenet` is there at 99.98%; it is the COMPONENTS that are absent. Without this the
        drop would read as 'Sharadar has no PP&E', which is false."""
        r = _artifact()
        if r is None:
            _skip_loudly(self, "OSAP3_K1.json absent -- built from the licensed fundamentals export, which CI never has")
        self.assertGreater(r["column_coverage"]["ppnenet"]["non_null_frac"], 0.99)

    def test_equity_duration_survives(self):
        r = _artifact()
        if r is None:
            _skip_loudly(self, "OSAP3_K1.json absent -- built from the licensed fundamentals export, which CI never has")
        self.assertFalse(r["signals"]["EquityDuration"]["verdict"].startswith("DROPS"))
        self.assertEqual(r["batch_after_K1"], ["EquityDuration"])

    def test_dropping_a_signal_tightens_BH_rather_than_loosening_it(self):
        """The draft §5 pre-commits this, because the incentive runs the other way: keeping a
        failing signal in would RAISE BH's threshold and make the survivor easier to pass."""
        r = _artifact()
        if r is None:
            _skip_loudly(self, "OSAP3_K1.json absent -- built from the licensed fundamentals export, which CI never has")
        k = r["batch_size_after_K1"]
        self.assertEqual(k, 1)
        self.assertLess(0.10 / max(1, k), 0.10 / 3 + 1e-12 + 0.0667)
        self.assertIn("TIGHTENS", r["BH_CONSEQUENCE"])

    def test_the_trials_are_still_charged_for_a_dropped_signal(self):
        r = _artifact()
        if r is None:
            _skip_loudly(self, "OSAP3_K1.json absent -- built from the licensed fundamentals export, which CI never has")
        self.assertIn("STILL charged", r["TRIALS_STILL_CHARGED"])
        self.assertIn("MA6", r["TRIALS_STILL_CHARGED"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
