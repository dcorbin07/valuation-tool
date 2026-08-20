# -*- coding: utf-8 -*-
"""E-3 / S-SEED-1 -- theme dispersion. `PREREG_e3_theme_dispersion.md`.

The pins that matter here are the ones that would let a wrong answer look right:

* **C-IDENT** -- the matrix `disp` is a spread of must BE the matrix the composite is a
  weighted mean of. Proved against the SHIPPED `composite_from_frame`, and proved NON-VACUOUS
  by perturbing `Z` and requiring the identity to break.
* **§B2** -- standardising is not optional. A dispersion over the RAW theme columns is a sort
  on how many inputs a theme has; the fixture makes the two answers differ.
* **§2** -- an ineligible row is `NaN`, never `0.0`. Zero would read as "the themes agree
  perfectly", which is the fail-open the register forbids.
* **§B4** -- a degenerate kill is `structurally_absent`, not a pass. `MB21`'s C1 scored a
  perfect 0.000e+00 by comparing nothing.
* **§3** -- a POSITIVE incremental IC is a CONTRADICTION against the declared negative sign,
  however large.

The AST guards read the syntax tree, never the source text: the runner's own docstring names
the things they forbid, so a substring search would go red on a clean file (`MA49`, `MA5`,
`MB15`, `MB22`/`MB23`, `SC-1`, and `E-5` last session).
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

from valuation.edge.fundamental_panel import composite, composite_from_frame   # noqa: E402
from valuation.screener.cross_sectional import zscore                          # noqa: E402
from valuation.studies import incremental_ic as II                             # noqa: E402
import e3_theme_dispersion as E3                                              # noqa: E402

_SKIPS = []
RUNNER = os.path.join(REPO, "scripts", "e3_theme_dispersion.py")
REGISTER = os.path.join(REPO, "PREREG_e3_theme_dispersion.md")
DRAFT = os.path.join(REPO, "PREREG_DRAFT_s1_theme_dispersion.md")


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _tree(path):
    return ast.parse(_src(path))


def _named(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _defs(tree):
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef,
                                                             ast.AsyncFunctionDef))}


def _frame(n=60, seed=3):
    """One date, seven themes with DELIBERATELY DIFFERENT SPREADS -- `quality` compressed the
    way a ten-input theme is, `insider` wide the way a one-input theme is. That difference is
    the whole reason §B2 standardises."""
    rng = np.random.default_rng(seed)
    cols = list(II.BASIS_SEVEN)
    data = {"date": ["2020-01-15"] * n, "ticker": [f"T{i:03d}" for i in range(n)]}
    spreads = {"quality": 0.50, "insider": 0.96}
    for c in cols:
        data[c] = rng.normal(0.0, spreads.get(c, 0.8), n)
    data["fwd_ret"] = rng.normal(0.0, 0.1, n)
    return pd.DataFrame(data), cols


# =============================================================================================
class TestCIdent(unittest.TestCase):

    def test_the_matrix_is_the_one_the_shipped_composite_averages(self):
        g, cols = _frame()
        Z = E3.standardised(g, cols)
        r = E3.c_ident(g, cols, Z)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["max_abs_delta"], 0.0)
        self.assertEqual(r["n_compared"], len(g))

    def test_c_ident_is_NOT_vacuous(self):
        """A control that cannot fail certifies nothing. Perturb one cell of `Z` by 1e-12 and
        the identity must break -- `MB21`'s C1 passed at a perfect 0.000e+00 on an empty frame
        and certified the instrument that produced it."""
        g, cols = _frame()
        Z = E3.standardised(g, cols)
        Z[0, 0] += 1e-12
        self.assertFalse(E3.c_ident(g, cols, Z)["ok"])

    def test_c_ident_refuses_an_empty_comparison(self):
        """Zero cells compared is not a perfect match. This is the exact shape of the sixth
        instance of the vacuous-control family the record names."""
        g, cols = _frame(n=0)
        r = E3.c_ident(g, cols, np.empty((0, len(cols))))
        self.assertFalse(r["ok"])
        self.assertEqual(r["n_compared"], 0)


# =============================================================================================
class TestTheObject(unittest.TestCase):

    def test_standardising_is_not_optional_and_changes_the_answer(self):
        """§B2. On raw columns the dispersion is dominated by whichever themes happen to carry
        the widest spread; standardised it is not. If these agreed, §B2 would be decoration."""
        g, cols = _frame()
        raw = np.column_stack([g[c].to_numpy(dtype=float) for c in cols])
        z = E3.standardised(g, cols)
        d_raw, _ = E3.dispersion(raw, E3.MIN_THEMES)
        d_z, _ = E3.dispersion(z, E3.MIN_THEMES)
        rho = pd.Series(d_raw).corr(pd.Series(d_z), method="spearman")
        self.assertLess(rho, 0.999, "raw and standardised dispersion are indistinguishable")

    def test_an_ineligible_row_is_NaN_and_never_zero(self):
        """Zero would read as 'the themes agree perfectly' -- the fail-open §2 forbids."""
        Z = np.array([[1.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
                      [1.0, 2.0, 3.0, np.nan, np.nan, np.nan, np.nan],
                      [1.0, 2.0, 3.0, 4.0, np.nan, np.nan, np.nan]])
        sd, n = E3.dispersion(Z, 4)
        self.assertTrue(np.isnan(sd[0]) and np.isnan(sd[1]))
        self.assertFalse(np.isnan(sd[2]))
        self.assertEqual(list(n), [1, 3, 4])

    def test_the_dispersion_is_the_SAMPLE_sd(self):
        Z = np.array([[0.0, 2.0, 0.0, 2.0, 0.0, 2.0, 0.0]])
        sd, _ = E3.dispersion(Z, 4)
        self.assertAlmostEqual(float(sd[0]), float(np.std(Z[0], ddof=1)), places=12)
        self.assertNotAlmostEqual(float(sd[0]), float(np.std(Z[0], ddof=0)), places=6)

    def test_identical_themes_give_zero_dispersion_and_that_is_a_real_value(self):
        Z = np.full((1, 7), 1.25)
        sd, n = E3.dispersion(Z, 4)
        self.assertAlmostEqual(float(sd[0]), 0.0)
        self.assertEqual(int(n[0]), 7)

    def test_disp_is_defined_PER_BASIS(self):
        """§B3. Dispersing over seven while residualising on six would put `institutional`
        inside the statistic and outside the control."""
        g, _ = _frame()
        six, seven = list(II.BASIS_SIX), list(II.BASIS_SEVEN)
        d6, _ = E3.dispersion(E3.standardised(g, six), E3.MIN_THEMES)
        d7, _ = E3.dispersion(E3.standardised(g, seven), E3.MIN_THEMES)
        self.assertFalse(np.allclose(d6, d7), "the two bases produced the same column")


# =============================================================================================
class TestKills(unittest.TestCase):

    def test_a_degenerate_comparison_is_structurally_absent_and_not_a_pass(self):
        """§B4. On the arm's rows the complete-case rule makes the theme count CONSTANT, and a
        Spearman against a constant is undefined -- reporting it as a clean bill of health is
        the vacuous-control family."""
        g, cols = _frame()
        g["disp_seven"] = np.linspace(0.1, 1.0, len(g))
        g["n_themes_seven"] = 7                              # constant, as on the scored rows
        g["abs_composite_seven"] = np.abs(np.linspace(-1, 1, len(g)))
        out = E3.kills_for(g, "seven", "arm_scored_rows")
        self.assertTrue(out["K3_theme_count"]["structurally_absent"])
        self.assertFalse(out["K3_theme_count"]["fires"])
        self.assertIsNone(out["K3_theme_count"]["mean_rho"])

    def test_a_kill_FIRES_on_a_planted_costume(self):
        """The positive control. A `disp` that IS the size theme must trip K1 -- otherwise the
        kill could be unreachable and the register would look strict while being vacuous."""
        g, cols = _frame()
        g["disp_seven"] = g["size"].to_numpy(dtype=float)
        g["n_themes_seven"] = np.arange(len(g)) % 4 + 4
        g["abs_composite_seven"] = np.abs(np.linspace(-1, 1, len(g)))
        out = E3.kills_for(g, "seven", "eligible_population")
        self.assertTrue(out["K1_size"]["fires"])
        self.assertTrue(out["any_fires"])

    def test_a_kill_does_NOT_fire_on_an_unrelated_column(self):
        g, cols = _frame()
        rng = np.random.default_rng(11)
        g["disp_seven"] = rng.normal(0, 1, len(g))
        g["n_themes_seven"] = np.arange(len(g)) % 4 + 4
        g["abs_composite_seven"] = np.abs(rng.normal(0, 1, len(g)))
        out = E3.kills_for(g, "seven", "eligible_population")
        self.assertFalse(out["any_fires"])

    def test_undefined_dates_are_counted_rather_than_dropped(self):
        g, _ = _frame(n=5)                                    # below MIN_NAMES
        g["disp_seven"] = np.linspace(0, 1, 5)
        g["n_themes_seven"] = 7
        g["abs_composite_seven"] = np.linspace(0, 1, 5)
        r = E3.mean_per_date_rho(g, "disp_seven", "size")
        self.assertTrue(r["degenerate"])
        self.assertEqual(r["n_dates_undefined"], 1)


# =============================================================================================
class TestRegisterDiscipline(unittest.TestCase):

    def test_the_composite_is_never_re_implemented(self):
        """`B7`, and the task's own instruction. The runner may CALL `composite_from_frame`; it
        may not define a second one."""
        tree = _tree(RUNNER)
        names = _named(tree)
        self.assertIn("composite_from_frame", names)
        for banned in ("composite", "composite_from_frame", "zscore", "residualise",
                       "arm_ic", "arm_verdict", "halves", "effective_coverage"):
            self.assertNotIn(banned, _defs(tree),
                             f"{banned} is DEFINED here; it is shipped and must be imported")

    def test_the_shipped_scorer_and_gate_are_used(self):
        names = _named(_tree(RUNNER))
        for required in ("arm_ic", "arm_verdict", "effective_dates",
                         "require_effective_coverage", "effective_coverage"):
            self.assertIn(required, names, f"{required} is not called")

    def test_the_guard_is_not_vacuous(self):
        """Proves the AST route beats the substring route on this very file."""
        self.assertIn("composite_from_frame", _named(_tree(RUNNER)))
        self.assertIn("never re-implemented", _src(RUNNER).lower().replace("_", " "),
                      "the docstring no longer says it, so this no longer proves the point")

    def test_the_basis_is_named_explicitly_and_both_are_used(self):
        """`basis_for` has NO default by design (`MA5`). Both bases are co-primary."""
        self.assertEqual(E3.BASES, ("six", "seven"))
        with self.assertRaises(Exception):
            II.basis_for("eight")

    def test_the_declared_sign_makes_a_positive_result_a_CONTRADICTION(self):
        """§3, and it is the shipped `arm_verdict`'s own behaviour for a declared sign."""
        src = _src(RUNNER)
        self.assertIn("CONTRADICTION", src)
        tree = _tree(RUNNER)
        consts = {n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertIn("negative", consts)

    def test_the_register_and_the_draft_are_both_on_disk(self):
        """`SC-1`'s lesson: assert the file EXISTS rather than that a string starts with
        `PREREG_`. Two lanes once named the same unbuilt file differently."""
        self.assertTrue(os.path.isfile(REGISTER))
        self.assertTrue(os.path.isfile(DRAFT), "the accepted draft must remain readable")
        txt = _src(REGISTER)
        for bar in ("2.71", "0.60", "ddof", "six", "seven", "negative"):
            self.assertIn(bar, txt)

    def test_the_runner_constants_match_the_register(self):
        self.assertEqual(E3.MIN_THEMES, 4)
        self.assertEqual(E3.DDOF, 1)
        self.assertEqual(E3.KILL_RHO, 0.60)
        self.assertEqual(E3.BAR, 2.71)
        self.assertEqual(E3.DECLARED_SIGN, "negative")
        self.assertEqual(E3.THEME_WEIGHT, 0.125)

    def test_the_arms_pass_refuses_without_a_passing_controls_artifact(self):
        import tempfile
        saved = E3.CTRL_JSON
        try:
            with tempfile.TemporaryDirectory() as td:
                args = type("A", (), {"panel": "x", "out_dir": td})()
                E3.CTRL_JSON = "absent.json"
                self.assertEqual(E3.run_arms(args), 2, "a MISSING controls file must refuse")
                E3.CTRL_JSON = "failing.json"
                with io.open(os.path.join(td, "failing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": false}')
                self.assertEqual(E3.run_arms(args), 2, "a FAILING controls file must refuse")
                # not unconditional: a PASSING file gets past the gate and dies on the panel
                E3.CTRL_JSON = "passing.json"
                with io.open(os.path.join(td, "passing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": true}')
                with self.assertRaises(Exception):
                    E3.run_arms(args)
        finally:
            E3.CTRL_JSON = saved

    def test_no_weighting_or_book_change_is_reachable(self):
        """§6.1 -- this register tests a COLUMN and does not touch the book (`S13`)."""
        names = _named(_tree(RUNNER))
        for banned in ("quantile_backtest", "run_backtest", "_backtest_hold", "cpcv_validate",
                       "_weighted_optimize", "walk_forward", "top_decile_alpha"):
            self.assertNotIn(banned, names, f"{banned} is reachable from the arm path")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
