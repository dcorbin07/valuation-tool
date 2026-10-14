# -*- coding: utf-8 -*-
"""`BETA-FORECAST` — the estimator, the windows, and the guards the verdict rests on.

Run as its own process (`RUN_RULES` 0.1 judges a suite by its EXIT CODE).

The data-dependent tests skip **loudly** via `dipcall.have_data()`; the arithmetic tests need no
data and run everywhere, which is the half that matters.
"""
import ast
import io
import os
import subprocess
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

from valuation.data import beta as SHIPPED                                 # noqa: E402
from valuation.studies import beta_forecast as BF                          # noqa: E402
from valuation.studies import dipcall as D                                 # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(HERE, "valuation", "studies", "beta_forecast.py")
REGISTER = os.path.join(HERE, "PREREG_beta_forecast.md")
CONTEST = os.path.join(HERE, "scripts", "beta_forecast_contest.py")


class TestTheRegisterCameFirst(unittest.TestCase):
    def test_the_register_exists(self):
        self.assertTrue(os.path.exists(REGISTER), REGISTER)

    def test_the_register_is_a_strict_ancestor_and_never_shares_a_commit_with_code(self):
        def shas(pathspec):
            out = subprocess.run(["git", "log", "--format=%H", "--", pathspec],
                                 cwd=HERE, capture_output=True)
            return [x for x in out.stdout.decode("utf-8", "replace").split() if x]

        reg = shas("PREREG_beta_forecast.md")
        mod = shas("valuation/studies/beta_forecast.py")
        if not reg or not mod:
            self.skipTest("one of the two files is not committed yet")
        r = subprocess.run(["git", "merge-base", "--is-ancestor", reg[-1], mod[-1]],
                           cwd=HERE, capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "register %s must precede module %s" % (reg[-1][:8], mod[-1][:8]))
        for sha in reg:
            out = subprocess.run(["git", "show", "--name-only", "--format=", sha],
                                 cwd=HERE, capture_output=True)
            files = [f for f in out.stdout.decode("utf-8", "replace").split() if f]
            self.assertFalse([f for f in files if not f.endswith(".md")],
                             "register commit %s also touched code" % sha[:8])

    def test_the_register_keeps_the_prior_rejection_standing(self):
        t = " ".join(io.open(REGISTER, encoding="utf-8").read().split())
        self.assertIn("THAT REJECTION STANDS AND IS NOT RE-OPENED", t)
        self.assertIn("2.491", t)
        # and it states the two consequences a winner must carry
        self.assertIn("IT CHANGES EVERY PUBLISHED FAIR VALUE", t)
        self.assertIn("PREREG_valuation_reads.md", t)


class TestTheEstimatorIsTheShippedConvention(unittest.TestCase):
    def test_the_window_and_minimum_match_the_shipped_module(self):
        # `MA5`: a second copy of a constant is how one freezes. These must agree with the module
        # the live path uses, and if the shipped one changes this goes red rather than drifting.
        self.assertEqual(SHIPPED.BETA_PERIOD, "5y")
        self.assertEqual(SHIPPED.BETA_INTERVAL, "1mo")
        self.assertEqual(BF.TRAIL_MONTHS, 60)
        self.assertEqual(BF.MIN_TRAIL_OBS, SHIPPED.MIN_BETA_OBSERVATIONS)
        self.assertEqual(BF.MARKET, SHIPPED.MARKET_PROXY)

    def test_beta_of_reproduces_a_known_regression(self):
        rng = np.random.default_rng(3)
        m = pd.Series(rng.normal(0, 0.04, 120), index=["%04d-%02d" % (2000 + i // 12, 1 + i % 12)
                                                       for i in range(120)])
        r = 1.7 * m + pd.Series(rng.normal(0, 0.01, 120), index=m.index)
        b = BF.beta_of(r, m, 36)
        self.assertAlmostEqual(b, 1.7, places=1)

    def test_beta_of_REFUSES_rather_than_returning_a_number(self):
        m = pd.Series([0.01] * 10, index=["2000-%02d" % (i + 1) for i in range(10)])
        self.assertIsNone(BF.beta_of(m, m, 36), "a 10-month beta is not a smaller-sample beta")
        flat = pd.Series([0.0] * 60, index=["%04d-%02d" % (2000 + i // 12, 1 + i % 12)
                                            for i in range(60)])
        self.assertIsNone(BF.beta_of(flat, flat, 36), "zero market variance must refuse")

    def test_blume_is_the_documented_weight_and_target(self):
        self.assertEqual(BF.BLUME_W, 0.67)
        self.assertEqual(BF.BLUME_TARGET, 1.0)
        self.assertAlmostEqual(BF.blume(2.0), 0.67 * 2.0 + 0.33)
        self.assertAlmostEqual(BF.blume(1.0), 1.0, places=12,
                               msg="a beta of exactly 1.0 must be a fixed point")

    def test_blume_shrinks_toward_one_from_both_sides(self):
        self.assertLess(BF.blume(2.0), 2.0)
        self.assertGreater(BF.blume(0.3), 0.3)

    def test_the_engine_constant_is_still_OFF_and_this_item_did_not_change_it(self):
        from valuation.engine import wacc as W
        self.assertIsNone(W.BETA_SHRINK,
                          "the register's section 12 says BETA_SHRINK stays None; adoption is "
                          "Don's and is a vintage event")


class TestTheWindowsCannotOverlap(unittest.TestCase):
    """The ONE way this design could leak is an off-by-one between the two windows."""

    def _idx(self, n=200):
        return ["%04d-%02d" % (2000 + i // 12, 1 + i % 12) for i in range(n)]

    def test_the_trailing_and_forward_windows_are_disjoint(self):
        idx = self._idx()
        for m in (idx[70], idx[120], idx[150]):
            tr, fw = BF.trailing_and_forward(idx, m, 60, 24)
            self.assertEqual(len(tr), 60)
            self.assertEqual(len(fw), 24)
            self.assertEqual(set(tr) & set(fw), set(), "a look-ahead: the windows overlap")
            self.assertEqual(tr[-1], m, "the trailing window ENDS at the formation month")
            self.assertGreater(fw[0], m, "the forward window starts STRICTLY after it")

    def test_the_formation_month_is_never_inside_its_own_forward_window(self):
        idx = self._idx()
        for m in (idx[60], idx[99], idx[175]):
            _tr, fw = BF.trailing_and_forward(idx, m, 60, 24)
            if fw:
                self.assertNotIn(m, fw)

    def test_formation_months_leave_room_on_both_sides(self):
        idx = self._idx(100)
        fm = BF.formation_months(idx, 60, 24)
        self.assertEqual(fm[0], idx[59])
        self.assertEqual(fm[-1], idx[75])
        for m in fm:
            tr, fw = BF.trailing_and_forward(idx, m, 60, 24)
            self.assertEqual(len(tr), 60)
            self.assertEqual(len(fw), 24)


class TestTheVectorisedPathIsGated(unittest.TestCase):
    """`B7` fidelity: a faster path that returns a DIFFERENT number is worthless.

    `rolling_betas` replaced a per-cell loop that would have taken hours on 9,645 names. It must
    reproduce the explicit `beta_of` loop cell-for-cell, and **the comparison COUNT is asserted**
    — `MB21`'s `C1` scored a perfect 0.000e+00 on an empty frame by comparing nothing.
    """

    def test_rolling_reproduces_the_explicit_loop_on_synthetic_data(self):
        rng = np.random.default_rng(11)
        idx = ["%04d-%02d" % (2000 + i // 12, 1 + i % 12) for i in range(180)]
        m = pd.Series(rng.normal(0, 0.045, 180), index=idx)
        r = pd.Series(0.8 * m.to_numpy() + rng.normal(0, 0.03, 180), index=idx)
        roll = BF.rolling_betas(r, m)
        self.assertGreater(len(roll), 50, "non-vacuous: the rolling path produced rows")
        worst, n = 0.0, 0
        for _, row in roll.iterrows():
            tr, fw = BF.trailing_and_forward(idx, row["month"], 60, 24)
            a = BF.beta_of(r.reindex(tr), m.reindex(tr), 36)
            b = BF.beta_of(r.reindex(fw), m.reindex(fw), 20)
            if a is None or b is None:
                continue
            worst = max(worst, abs(a - row["b_raw"]), abs(b - row["b_real"]))
            n += 1
        self.assertGreater(n, 50, "the gate must have COMPARED something")
        self.assertLess(worst, 1e-10, "max |delta| %.3e over %d cells" % (worst, n))

    def test_rolling_refuses_a_series_too_short_to_form_either_window(self):
        idx = ["2000-%02d" % (i + 1) for i in range(12)]
        s = pd.Series([0.01] * 12, index=idx)
        self.assertEqual(len(BF.rolling_betas(s, s)), 0)


class TestTheContestsConstruction(unittest.TestCase):
    def test_the_paired_contrast_is_candidate_minus_raw_so_NEGATIVE_means_better(self):
        src = io.open(CONTEST, encoding="utf-8").read()
        self.assertIn("diff = e_c - e_raw", src)
        self.assertIn("NEGATIVE means the candidate is CLOSER", src)

    def test_the_cluster_robust_mean_is_DELEGATED(self):
        src = io.open(CONTEST, encoding="utf-8").read()
        self.assertIn("from scripts import dipcall_arm as DA", src)
        self.assertIn("return DA.clustered", src)

    def test_the_materiality_floor_is_the_registers_and_is_derived(self):
        from scripts import beta_forecast_contest as C
        self.assertEqual(C.MATERIALITY_BETA, 0.05)
        t = " ".join(io.open(REGISTER, encoding="utf-8").read().split())
        self.assertIn("0.05 beta units", t)
        self.assertIn("0.478% per 0.01", t)

    def test_the_primary_population_is_the_incumbents_own_tier(self):
        from scripts import beta_forecast_contest as C
        self.assertEqual(C.TIER_FLOOR, 10e9)
        self.assertEqual(C.TIER_FLOOR, D.TIER_FLOOR,
                         "the same tier INSIDER-CLUSTER and the charter use")

    def test_the_panel_sector_column_is_never_used_for_the_sector_candidate(self):
        """The panel's `sector` is TODAY's classification (`S25`), so using it in a FORECASTING
        contest would hand the candidate under test knowledge of the future. Read over the AST:
        no subscript anywhere in the contest may take `sector` off the PANEL."""
        src = io.open(CONTEST, encoding="utf-8").read()
        self.assertIn("sector_map as SM", src)
        self.assertIn("smap.at(", src)
        tree = ast.parse(src)
        bad = []
        for n in ast.walk(tree):
            if (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                    and n.value.id == "panel"
                    and isinstance(n.slice, ast.Constant) and n.slice.value == "sector"):
                bad.append("panel['sector']")
        self.assertFalse(bad, bad)


class TestNoForwardReturnAnywhere(unittest.TestCase):
    def test_over_the_syntax_tree(self):
        for p in (MODULE, CONTEST):
            tree = ast.parse(io.open(p, encoding="utf-8").read())
            banned = {"fwd_ret", "forward_return", "ar_own", "ar_mkt"}
            hits, names = [], 0
            for n in ast.walk(tree):
                if isinstance(n, ast.Name):
                    names += 1
                    if n.id in banned:
                        hits.append(n.id)
                elif isinstance(n, ast.Attribute) and n.attr in banned:
                    hits.append(n.attr)
            self.assertFalse(hits, "%s reads a return: %s" % (os.path.basename(p), hits))
            self.assertGreater(names, 40, "non-vacuous")


class TestTheBanksAgreeWithTheRegister(unittest.TestCase):
    def setUp(self):
        if not D.have_data():
            self.skipTest("no populated data root (CI): skipping LOUDLY, never silently")
        import json
        p = D.out_path("BETA_FORECAST_CENSUS.json")
        if not os.path.isfile(p):
            self.skipTest("census not run here")
        self.c = json.load(io.open(p, encoding="utf-8"))

    def test_the_census_computed_no_loss(self):
        self.assertEqual(self.c["trials"], 0)
        self.assertIn("NO LOSS", self.c["part"])

    def test_the_estimator_block_matches_the_module(self):
        e = self.c["estimator"]
        self.assertEqual(e["trail_months"], BF.TRAIL_MONTHS)
        self.assertEqual(e["fwd_months"], BF.FWD_MONTHS)
        self.assertEqual(e["blume_w"], BF.BLUME_W)
        self.assertEqual(e["market"], BF.MARKET)


if __name__ == "__main__":
    unittest.main(verbosity=1)
