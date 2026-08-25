# -*- coding: utf-8 -*-
"""D6/D7 — pins for the analyst estimate-revision construction.

The properties asserted here are the ones the register FIXES, so a future edit that quietly moves
a parameter goes red rather than producing a different number under the same name.

Data-dependent checks SKIP LOUDLY and are never counted as passes: `MB42` recorded a gate suite
green in CI and red on the only machine holding the data it guards, and this project has caught
the vacuous pass five times.
"""
import ast
import datetime as dt
import io
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.studies import revisions as REV                        # noqa: E402
from valuation.edge.ibes_events import MaskedCusip                    # noqa: E402

REG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "PREREG_d6_analyst_revisions.md")
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "valuation", "studies", "revisions.py")


def _panel(rows):
    return pd.DataFrame(rows, columns=["ticker", "date"])


class TheRegisteredConstants(unittest.TestCase):
    """MA13's committed-literal idiom: pin the VALUES, not a re-read of the module's own tuple.

    The required-field test in `S3-I3` ITERATED the very constant it was meant to pin, so deleting
    a field deleted its test too. These are literals for that reason.
    """

    def test_the_four_parameters_the_register_fixes(self):
        self.assertEqual(REV.FPI_FY1, "1")            # FY1; a naive SELECT mixes horizons
        self.assertEqual(REV.WINDOW_DAYS, 91)         # one quarterly rebalance interval
        self.assertEqual(REV.MIN_REVISIONS, 3)        # the declared floor
        self.assertEqual(REV.MEASURE, "EPS")
        self.assertEqual(REV.USFIRM, "1")

    def test_the_register_names_the_same_numbers(self):
        """A constant that drifts from the register it claims to implement is the whole hazard."""
        if not os.path.isfile(REG):
            self.skipTest("register absent")
        t = io.open(REG, encoding="utf-8").read()
        self.assertIn("`fpi = '1'`", t)
        self.assertIn("91", t)
        self.assertIn("U + D >= 3", t)

    def test_sweeping_the_window_or_the_floor_is_REFUSED_by_name(self):
        """Void condition 7. A second window is a NEW hypothesis, not a robustness check."""
        p = _panel([("AAA", "2020-01-15")])
        rev = pd.DataFrame([("AAA", "2020-01-01", 1)],
                           columns=["ticker", "actdats", "sign"])
        for kw in ({"window_days": 63}, {"min_revisions": 2}, {"min_revisions": 5}):
            with self.assertRaises(REV.RegisterViolation):
                REV.signal_on_panel(p, rev, **kw)
        # and the registered values are accepted
        REV.signal_on_panel(p, rev)


class ThePointInTimeGate(unittest.TestCase):

    def test_a_revision_activated_AFTER_the_rebalance_date_never_enters(self):
        """K4, from the side that matters. Zero tolerance, and a single violation voids the item."""
        p = _panel([("AAA", "2020-01-15")])
        after = pd.DataFrame(
            [("AAA", "2020-01-16", 1), ("AAA", "2020-02-01", 1), ("AAA", "2020-06-01", 1)],
            columns=["ticker", "actdats", "sign"])
        s = REV.signal_on_panel(p, after)
        self.assertTrue(pd.isna(s.iloc[0]), "a future revision reached the signal")

    def test_the_window_is_half_open_so_a_revision_ON_the_date_counts(self):
        p = _panel([("AAA", "2020-01-15")])
        on = pd.DataFrame([("AAA", "2020-01-15", 1)] * 3,
                          columns=["ticker", "actdats", "sign"])
        self.assertEqual(REV.signal_on_panel(p, on).iloc[0], 1.0)

    def test_a_revision_older_than_the_window_falls_out(self):
        p = _panel([("AAA", "2020-01-15")])
        old = str(dt.date(2020, 1, 15) - dt.timedelta(days=REV.WINDOW_DAYS))
        rev = pd.DataFrame([("AAA", old, 1)] * 3, columns=["ticker", "actdats", "sign"])
        self.assertTrue(pd.isna(REV.signal_on_panel(p, rev).iloc[0]),
                        "the window is (t - 91, t], so exactly 91 days back is OUTSIDE it")

    def test_the_floor_makes_a_thin_name_NaN_rather_than_zero(self):
        """A missing signal and a balanced signal must not read the same. `O21-D2`'s C5 rule:
        a filter that never ran and a filter that ran and found nothing are different states."""
        p = _panel([("AAA", "2020-01-15")])
        two = pd.DataFrame([("AAA", "2020-01-02", 1), ("AAA", "2020-01-03", -1)],
                           columns=["ticker", "actdats", "sign"])
        self.assertTrue(pd.isna(REV.signal_on_panel(p, two).iloc[0]))
        three = pd.DataFrame([("AAA", "2020-01-02", 1), ("AAA", "2020-01-03", -1),
                              ("AAA", "2020-01-04", 1)], columns=["ticker", "actdats", "sign"])
        self.assertAlmostEqual(REV.signal_on_panel(p, three).iloc[0], 1.0 / 3.0)


class WhatCountsAsARevision(unittest.TestCase):

    def test_an_unchanged_reconfirmation_is_NOT_a_revision(self):
        est = pd.DataFrame(
            [("AAA", "2020-01-02", 1, 9, "2020-12-31", 1.00),
             ("AAA", "2020-01-09", 1, 9, "2020-12-31", 1.00),
             ("AAA", "2020-01-16", 1, 9, "2020-12-31", 1.10)],
            columns=["ticker", "actdats", "analys", "estimator", "fpedats", "value"])
        r = REV.revisions(est)
        self.assertEqual(len(r), 1, "an unchanged re-confirmation was counted as a revision")
        self.assertEqual(int(r.iloc[0]["sign"]), 1)

    def test_a_different_analyst_does_not_revise_another_analysts_estimate(self):
        est = pd.DataFrame(
            [("AAA", "2020-01-02", 1, 9, "2020-12-31", 1.00),
             ("AAA", "2020-01-09", 2, 9, "2020-12-31", 2.00)],
            columns=["ticker", "actdats", "analys", "estimator", "fpedats", "value"])
        self.assertEqual(len(REV.revisions(est)), 0)

    def test_a_different_fiscal_period_is_not_a_revision(self):
        est = pd.DataFrame(
            [("AAA", "2020-01-02", 1, 9, "2020-12-31", 1.00),
             ("AAA", "2020-01-09", 1, 9, "2021-12-31", 2.00)],
            columns=["ticker", "actdats", "analys", "estimator", "fpedats", "value"])
        self.assertEqual(len(REV.revisions(est)), 0)

    def test_the_sign_is_the_direction_of_the_change(self):
        est = pd.DataFrame(
            [("AAA", "2020-01-02", 1, 9, "2020-12-31", 2.00),
             ("AAA", "2020-01-09", 1, 9, "2020-12-31", 1.00)],
            columns=["ticker", "actdats", "analys", "estimator", "fpedats", "value"])
        self.assertEqual(int(REV.revisions(est).iloc[0]["sign"]), -1)


class TheJoinIsW3bs(unittest.TestCase):
    """`B7`: the cusip route is imported, never re-implemented. Its traps are inherited."""

    def test_the_X_mask_is_POSITIONAL_and_not_a_prefix(self):
        self.assertTrue(MaskedCusip.matches("0028931X", "00289310"))
        # 328 seven-character prefixes in this file are shared by more than one distinct cusip
        self.assertFalse(MaskedCusip.matches("00108281", "00108282"))

    def test_the_module_does_not_reimplement_the_match_and_does_not_use_oftic(self):
        src = io.open(SRC, encoding="utf-8").read()
        tree = ast.parse(src)
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertIn("matches", called, "MaskedCusip.matches is not CALLED")
        self.assertNotIn("startswith", called, "a prefix match would merge distinct cusips")
        # `oftic` is a LEASE -- 17.7% of the rows it offers are a different company. It may be
        # DISCUSSED in the docstring; it may not be READ. Read the AST, not the prose (MA49).
        names = {n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        loaded = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "keep" for t in n.targets):
                loaded = {e.value for e in getattr(n.value, "elts", [])
                          if isinstance(e, ast.Constant)}
        self.assertTrue(loaded, "the loader's allowlist could not be read")
        self.assertNotIn("oftic", loaded)

    def test_the_forbidden_columns_are_not_in_the_loader_allowlist(self):
        """The arm path cannot reference what is not in the frame -- MB18's structural pin."""
        src = io.open(SRC, encoding="utf-8").read()
        loaded = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "keep" for t in n.targets):
                loaded = {e.value for e in getattr(n.value, "elts", [])
                          if isinstance(e, ast.Constant)}
        self.assertEqual(loaded & set(REV.FORBIDDEN_COLUMNS), set())
        # and the positive control: the allowlist is not empty and carries the PIT gate
        self.assertIn("actdats", loaded)

    def test_the_forbidden_tuple_names_the_realised_outcome_and_the_rejected_gates(self):
        for c in ("actual", "anndats", "revdats"):
            self.assertIn(c, REV.FORBIDDEN_COLUMNS)

    def test_the_open_end_extension_exists_because_CRSP_is_cut(self):
        """Left unextended, every 2025-2026 estimate falls outside every interval and is dropped
        silently -- the vendor's cut-off masquerading as a coverage gap (`W-3b` measured it)."""
        self.assertEqual(REV.OPEN_END, "9999-12-31")


class TheRunnerRefusesProperly(unittest.TestCase):

    def test_the_arm_refuses_without_a_controls_artifact_and_says_WHICH_state(self):
        """`S3-I1`: a recorder that cannot tell ABSENT from FAILING reports a clean bill of health
        from a check that never ran. Read the source rather than deleting the real artifact."""
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "scripts", "d6_revisions.py")
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("is ABSENT", src)
        self.assertIn("all_gating_pass=false", src)
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "arm")
        raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(len(raises), 2, "the refusal must distinguish two states")

    def test_the_two_passes_cannot_be_run_together(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "scripts", "d6_revisions.py")
        self.assertIn("exactly one of --controls or --arm",
                      io.open(p, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
