# -*- coding: utf-8 -*-
"""E-6 / S-SEED-2 -- the temporal axis. `PREREG_e6_temporal_axis.md`.

The pins here guard the two things that would let this item be wrong in a way nobody notices:

* **§0's DECLARATION.** The burn-in is an OBSERVATION COUNT and `min_history_years` is `None`
  for the primary. Both are pinned as literals against the register, because §0 resolved a
  contamination on an external anchor and a later edit that quietly swapped the reading would
  undo that resolution without leaving a trace.
* **§1's boundary.** This adds an AXIS and swaps nothing. `S20`/`S21` are the graveyard for a
  standardiser swap, so an AST guard fails if the arm path can reach a book statistic, a
  weighting routine or a standardiser.

Plus the ordinary ones: the declared POSITIVE sign makes a negative incremental IC a
CONTRADICTION; the two-pass refusal is exercised and proved not unconditional; and
`history_years` reaches the artifact so "five years" is checkable rather than promised.

AST guards read the syntax tree, never the source text -- the runner's docstring names the
things they forbid, so a substring search would go red on a clean file.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
_SCRIPTS = os.path.join(REPO, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from valuation.studies import incremental_ic as II         # noqa: E402
from valuation.studies import name_percentile as NP        # noqa: E402
import e6_temporal_axis as E6                              # noqa: E402

_SKIPS = []
RUNNER = os.path.join(REPO, "scripts", "e6_temporal_axis.py")
REGISTER = os.path.join(REPO, "PREREG_e6_temporal_axis.md")
TIDEMARK = r"C:\Users\donni\Downloads\Market Rotation\tidemark\tidemark\stats\percentile.py"


def _src(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _tree(p):
    return ast.parse(_src(p))


def _named(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _defs(tree):
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


# =============================================================================================
class TestTheDeclaration(unittest.TestCase):
    """§0.8. The contamination was resolved by DECLARING a reading; these pin the declaration."""

    def test_the_burn_in_is_an_OBSERVATION_COUNT_and_the_calendar_filter_is_declined(self):
        self.assertEqual(E6.BURN_IN, 20)
        self.assertIsNone(E6.MIN_HISTORY_YEARS,
                          "the primary must NOT impose the calendar filter -- §0.8")
        self.assertEqual(E6.SENSITIVITY_YEARS, 5.0)

    def test_both_census_readings_are_carried_in_the_source(self):
        """§0.1: both numbers travel with every statement of the result. If only the favourable
        one were present, a reader could not audit the resolution."""
        self.assertIn("observations_20", E6.I2_PUBLISHED)
        self.assertIn("observations_20_AND_calendar_5y", E6.I2_PUBLISHED)
        self.assertGreater(E6.I2_PUBLISHED["observations_20"], E6.KILL_SHARE)
        self.assertLess(E6.I2_PUBLISHED["observations_20_AND_calendar_5y"], E6.KILL_SHARE)

    def test_the_external_anchor_says_what_the_register_says_it_says(self):
        """The provenance is VERIFIED rather than cited. `SC-1`'s lesson applied to another
        repository: assert the source exists and carries the claim."""
        if not os.path.isfile(TIDEMARK):
            _SKIPS.append("TIDEMARK source not present on this machine")
            self.skipTest("TIDEMARK source absent")
        src = _src(TIDEMARK)
        self.assertIn("BURN_IN_ANNUAL = 30", src)
        self.assertIn("360", src)
        self.assertIn("observations exist", src,
                      "the engine no longer defines burn-in by observation count; §0 rests on it")

    def test_the_register_declares_the_reading_and_discloses_the_other(self):
        txt = _src(REGISTER)
        for needed in ("60.607", "58.886", "76fa895", "2026-08-16", "observation count",
                       "VOID-BY-CONTAMINATION", "counterfactual"):
            self.assertIn(needed, txt, f"the register no longer contains {needed!r}")

    def test_the_kill_bar_and_sign_are_the_seeds_own(self):
        self.assertEqual(E6.KILL_SHARE, 0.60)
        self.assertEqual(E6.DECLARED_SIGN, "positive")
        self.assertEqual(E6.BAR, 2.71)
        self.assertFalse(E6.INVERT)
        self.assertEqual(E6.LAG_DAYS, 0)


# =============================================================================================
class TestTheObject(unittest.TestCase):

    def _panel(self, n_dates=40, n_names=40, seed=5):
        rng = np.random.default_rng(seed)
        rows = []
        for di in range(n_dates):
            d = pd.Timestamp("2009-01-15") + pd.DateOffset(months=3 * di)
            for i in range(n_names):
                rows.append({"ticker": f"T{i:03d}", "date": d,
                             "value": float(rng.normal()), "fwd_ret": float(rng.normal(0, .1))})
        return pd.DataFrame(rows)

    def test_the_burn_in_is_counted_in_OBSERVATIONS_not_calendar_time(self):
        """The distinction §0 turns on, exercised: a name with GAPS reaches the burn-in on its
        Nth observation however long that took."""
        p = self._panel(n_dates=30, n_names=1)
        gappy = p.iloc[::2].copy()                     # half the dates -> twice the span
        out = NP.name_percentiles(gappy, "value", burn_in=5, invert=False)
        ok = out["value_pct"].notna()
        self.assertEqual(int(ok.sum()), len(gappy) - 4,
                         "eligibility did not begin on the 5th OBSERVATION")
        first = out.loc[ok, "history_years"].iloc[0]
        self.assertGreater(first, 1.0, "the gappy name should have taken longer in calendar time")

    def test_twenty_quarterly_observations_buy_4_75_years_not_5(self):
        """The one-quarter step the whole of §0 is about, as arithmetic rather than prose."""
        p = self._panel(n_dates=25, n_names=1)
        out = NP.name_percentiles(p, "value", burn_in=20, invert=False)
        first = out.loc[out["value_pct"].notna(), "history_years"].iloc[0]
        self.assertAlmostEqual(float(first), 4.75, delta=0.05)
        self.assertLess(float(first), 5.0,
                        "if 20 observations bought 5.0 years the two readings would not differ")

    def test_history_years_is_carried_on_every_scored_row(self):
        """The task's own requirement: 'five years' must be checkable, not promised."""
        p = self._panel()
        built = E6.build(p, None)
        self.assertIn("history_years", built.columns)
        self.assertIn("n_history", built.columns)
        scored = built[built["_eligible"]]
        self.assertTrue(scored["history_years"].notna().all())

    def test_the_calendar_filter_is_a_STRICT_SUBSET_of_the_observation_reading(self):
        """§0.4(2): the calendar figure is the engine PLUS a filter, not a second reading of it.
        If it were not nested, the two would be different objects and §0's argument would fail."""
        p = self._panel()
        a = E6.build(p, None)["_eligible"].to_numpy(dtype=bool)
        b = E6.build(p, 5.0)["_eligible"].to_numpy(dtype=bool)
        self.assertTrue(bool((b <= a).all()), "the calendar reading admitted a row the other did not")
        self.assertGreater(int(a.sum()), int(b.sum()), "the filter removed nothing; it is inert")

    def test_ineligible_rows_are_NaN_and_never_scored(self):
        p = self._panel(n_dates=25, n_names=3)
        built = E6.build(p, None)
        self.assertTrue(built.loc[~built["_eligible"], "value_pct"].isna().all())


# =============================================================================================
class TestRegisterDiscipline(unittest.TestCase):

    def test_this_adds_an_AXIS_and_swaps_nothing(self):
        """§1 and §6.3. `S20`/`S21` are the graveyard for a standardiser swap; the arm path may
        not reach a book statistic, a weighting routine or a standardiser."""
        names = _named(_tree(RUNNER))
        for banned in ("quantile_backtest", "run_backtest", "_backtest_hold", "cpcv_validate",
                       "_weighted_optimize", "walk_forward", "top_decile_alpha",
                       "composite_from_frame", "zscore", "rank_score", "zscore_nowinsor"):
            self.assertNotIn(banned, names, f"{banned} is reachable from the arm path")

    def test_the_shipped_engine_scorer_and_gate_are_used_and_none_re_implemented(self):
        tree = _tree(RUNNER)
        names, defs = _named(tree), _defs(tree)
        for required in ("name_percentiles", "eligible_rows", "burn_in_census", "arm_ic",
                         "arm_verdict", "effective_coverage", "require_effective_coverage",
                         "effective_dates"):
            self.assertIn(required, names, f"{required} is not called")
        for banned in ("name_percentiles", "expanding_percentile", "eligible_rows", "arm_ic",
                       "arm_verdict", "halves", "burn_in_census", "residualise"):
            self.assertNotIn(banned, defs, f"{banned} is DEFINED here; it is shipped")

    def test_the_guard_is_not_vacuous(self):
        """A guard that sees nothing passes everything.

        E-3's version of this leaned on the runner's docstring happening to name a banned
        token; THIS runner's docstring does not, and a guard proved non-vacuous by an accident
        of prose is not proved at all. So the extractor is shown to DISCRIMINATE instead:
        it finds what is called and does not find what is not."""
        names = _named(_tree(RUNNER))
        self.assertIn("name_percentiles", names)
        self.assertIn("arm_ic", names)
        self.assertNotIn("a_name_that_is_definitely_not_in_this_file", names)
        self.assertGreater(len(names), 50, "the extractor returned almost nothing")

    def test_a_negative_incremental_IC_is_a_CONTRADICTION_not_a_pass(self):
        """§3, declared sign POSITIVE."""
        src = _src(RUNNER)
        self.assertIn("CONTRADICTION", src)
        tree = _tree(RUNNER)
        # the sign test must compare > 0, never < 0, for a POSITIVE declaration
        cmps = [n for n in ast.walk(tree) if isinstance(n, ast.Compare)]
        gt = [c for c in cmps if any(isinstance(o, ast.Gt) for o in c.ops)
              and isinstance(c.left, ast.Subscript)]
        self.assertTrue(gt, "no `> 0` sign check on the median incremental IC")

    def test_both_bases_are_co_primary(self):
        self.assertEqual(E6.BASES, ("six", "seven"))
        with self.assertRaises(Exception):
            II.basis_for("eight")

    def test_the_arms_pass_refuses_without_a_passing_controls_artifact(self):
        import tempfile
        saved = E6.CTRL_JSON
        try:
            with tempfile.TemporaryDirectory() as td:
                args = type("A", (), {"panel": "x", "out_dir": td})()
                E6.CTRL_JSON = "absent.json"
                self.assertEqual(E6.run_arms(args), 2, "a MISSING controls file must refuse")
                E6.CTRL_JSON = "failing.json"
                with io.open(os.path.join(td, "failing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": false}')
                self.assertEqual(E6.run_arms(args), 2, "a FAILING controls file must refuse")
                E6.CTRL_JSON = "passing.json"
                with io.open(os.path.join(td, "passing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": true, "declaration": {}}')
                with self.assertRaises(Exception):
                    E6.run_arms(args)          # not unconditional: dies on the absent panel
        finally:
            E6.CTRL_JSON = saved


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
