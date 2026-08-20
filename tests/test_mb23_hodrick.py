"""MB23 - Hodrick 1B, verified against PRINTED numbers. Register:
PREREG_mb22_mb23_power_and_hodrick.md.

WHY IT IS VERIFIED THIS WAY. TIDEMARK's first implementation of this estimator summed the
regressors while keeping the h-period residual - which is neither Hodrick nor anything else -
and returned `t ~ 0.3` at every horizon while a bootstrap against the same null returned
`p ~ 0.018`. It looked like "no evidence" and was believed. **Verifying an estimator against
your own expectation is exactly that failure mode**, so everything here is checked against a
published table or an exact algebraic identity.

  Wei and Wright, FEDS 2009-27 (published as Wei and Wright (2013), JAE).
  Formula: section 2, p.3.  Coverage: Table 1, p.21.

WHAT THESE PIN.
  1. `overlapping_sums` is exact and STRICTLY forward-looking. An off-by-one makes the
     regression partly contemporaneous and every t built on it meaningless.
  2. At h=1 1B collapses to the White sandwich - an identity, checked to 1e-12, no tolerance.
  3. Published coverage at alpha=0, the only case 1B is valid for.
  4. The published DEGRADATION away from that null. This is the discriminating half: an
     estimator returning ~0.95 everywhere passes (3) and fails here.
  5. THE DEFECT IS RECONSTRUCTED and pinned, so a future session reintroducing the h-period
     residual goes red instead of quietly shipping "no evidence".
  6. The cross-check compares against the SHIPPED `statistics.hac_tstat`, not a second copy.
  7. `horizon_sweep` returns no verdict, ever.

The Monte-Carlo cells run at reduced draws HERE (the registered verification is the runner,
`scripts/mb22_mb23_power_and_hodrick.py`); tolerances are widened to match, and the
discriminating power is preserved because the defective estimator scores 1.000 on the same
cells. Nothing here touches `data/`.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import hodrick as HD                # noqa: E402
from valuation.edge import statistics as ST             # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def simulate(T, phi, rho, alpha, rng):
    """Wei-Wright section 3, exactly. x starts from its stationary distribution."""
    L = np.linalg.cholesky(np.array([[1.0, rho], [rho, 1.0]]))
    e = rng.standard_normal((T + 1, 2)) @ L.T
    x = np.empty(T + 1)
    r = np.empty(T + 1)
    x[0] = rng.standard_normal() / np.sqrt(1 - phi ** 2)
    r[0] = 0.0
    for t in range(1, T + 1):
        r[t] = alpha * x[t - 1] + e[t, 0]
        x[t] = phi * x[t - 1] + e[t, 1]
    return r[1:], x[1:]


def long_horizon_beta(alpha, phi, h):
    return alpha * (1 - phi ** h) / (1 - phi)


def coverage(phi, rho, alpha, h, reps, T=500, seed=7):
    rng = np.random.default_rng(seed)
    b_true = long_horizon_beta(alpha, phi, h)
    hits = 0
    for _ in range(reps):
        r, x = simulate(T, phi, rho, alpha, rng)
        f = HD.hodrick_1b(r, x, h)
        if abs((f["beta"] - b_true) / f["se"]) < 1.96:
            hits += 1
    return hits / reps


class ExactNoSimulation(unittest.TestCase):
    def test_overlapping_sums_is_exact_and_strictly_forward_looking(self):
        r = np.arange(1.0, 8.0)
        self.assertTrue(np.allclose(HD.overlapping_sums(r, 1), [2, 3, 4, 5, 6, 7]))
        self.assertTrue(np.allclose(HD.overlapping_sums(r, 2), [5, 7, 9, 11, 13]))
        self.assertTrue(np.allclose(HD.overlapping_sums(r, 3), [9, 12, 15, 18]))
        self.assertEqual(len(HD.overlapping_sums(r, 3)), len(r) - 3)

    def test_the_regressor_date_never_leaks_into_the_dependent_variable(self):
        """Changing r_t alone must not move y_t. If it does, the regression is partly
        contemporaneous and every t-statistic built on it is meaningless."""
        r = np.arange(1.0, 21.0)
        base = HD.overlapping_sums(r, 4)
        bumped = r.copy()
        bumped[7] += 1000.0
        moved = HD.overlapping_sums(bumped, 4) - base
        self.assertEqual(moved[7], 0.0, "r_t leaked into y_t")
        self.assertEqual(moved[3], 1000.0, "r_t should enter y_{t-4} .. y_{t-1}")

    def test_h1_reduces_exactly_to_the_white_sandwich(self):
        """An algebraic identity to machine precision - no tolerance, no simulation."""
        rng = np.random.default_rng(1)
        T = 300
        x = rng.standard_normal(T)
        r = 0.3 * np.roll(x, 1) + rng.standard_normal(T)
        r[0] = rng.standard_normal()
        got = HD.hodrick_1b(r, x, 1)["se"]
        X = HD._design(x)[:T - 1]
        y = HD.overlapping_sums(r, 1)
        _, XtX_inv = HD.ols(y, X)
        u = X * (r[1:] - r.mean())[:, None]
        want = float(np.sqrt((XtX_inv @ (u.T @ u) @ XtX_inv)[1, 1]))
        self.assertTrue(np.isclose(got, want, rtol=1e-12), f"{got} != {want}")

    def test_the_mean_form_is_the_same_sandwich_with_a_constant_regressor(self):
        """`hodrick_1b_mean` must not be a second implementation - one `_sandwich`, two
        entry points. At h=1 it is the White standard error of the mean over the rows it
        scores, exactly."""
        rng = np.random.default_rng(3)
        r = rng.standard_normal(200) + 0.1
        m = HD.hodrick_1b_mean(r, 1)
        eps = r[1:] - r.mean()
        self.assertTrue(np.isclose(m["se"], float(np.sqrt(eps @ eps)) / 199, rtol=1e-12))
        self.assertEqual(m["n_overlapping"], 199)

    def test_it_refuses_a_sample_too_short_for_the_horizon(self):
        for h in (1, 5):
            with self.assertRaises(ValueError):
                HD.hodrick_1b_mean(np.arange(2.0 * h), h)
        with self.assertRaises(ValueError):
            HD.overlapping_sums(np.arange(3.0), 5)


class AgainstPublishedNumbers(unittest.TestCase):
    def test_reproduces_published_coverage_under_the_null(self):
        """Wei-Wright Table 1, the alpha = 0 column - the only case 1B is valid for."""
        for phi, rho, h, published in [(0.98, -0.5, 12, 0.95), (0.99, 0.0, 12, 0.95),
                                       (0.98, 0.5, 48, 0.94)]:
            got = coverage(phi, rho, 0.0, h, reps=250)
            self.assertLessEqual(abs(got - published), 0.045,
                                 f"phi={phi} rho={rho} h={h}: {got:.3f} vs {published}")

    def test_reproduces_the_published_degradation_away_from_the_null(self):
        """The discriminating half. Table 1 Panel A, phi=0.98 rho=+0.5 h=48:
        alpha 0.00 -> 0.94, 0.05 -> 0.71, 0.10 -> 0.53.

        An estimator merely returning ~0.95 everywhere passes the null test and fails this
        one, so this is what stops a conservative-but-wrong implementation slipping through.
        It is also why `hodrick_1b` refuses to be described as giving an interval for a
        non-zero coefficient."""
        for alpha, published in [(0.05, 0.71), (0.10, 0.53)]:
            got = coverage(0.98, 0.5, alpha, 48, reps=250)
            self.assertLessEqual(abs(got - published), 0.08,
                                 f"alpha={alpha}: {got:.3f} vs {published}")

    def test_the_alpha_reading_of_table_1_is_settled_by_the_DGP_alone(self):
        """Table 1's headings print "beta"; the values are the DGP's `alpha`. The implied
        long-horizon slope is alpha(1-phi^h)/(1-phi), confirmed here against simulated OLS -
        which uses only the DGP and the OLS point estimate, no standard error, so it settles
        the reading independently of the estimator under test."""
        rng = np.random.default_rng(5)
        phi, alpha, h = 0.98, 0.05, 12
        want = long_horizon_beta(alpha, phi, h)
        got = np.mean([HD.ols_se(*simulate(500, phi, 0.0, alpha, rng), h)["beta"]
                       for _ in range(200)])
        self.assertLess(abs(got - want), 0.12 * abs(want))


class TheKnownDefectIsPinned(unittest.TestCase):
    """The h-period residual bug, reconstructed. If it ever returns, this goes red."""

    @staticmethod
    def _defective(r, x, h):
        T = len(r)
        X = HD._design(x)[:T - h]
        y = HD.overlapping_sums(r, h)
        b, XtX_inv = HD.ols(y, X)
        e_h = y - X @ b                       # <-- the h-period residual: the bug
        Xa = HD._design(x)
        cum = np.vstack([np.zeros((1, 2)), np.cumsum(Xa, axis=0)])
        Xsum = (cum[h:] - cum[:-h])[:len(y)]
        W = Xsum * e_h[:, None]
        V = XtX_inv @ (W.T @ W) @ XtX_inv
        return b[1], float(np.sqrt(V[1, 1]))

    def test_the_defect_can_never_reject_anything_and_the_shipped_one_can(self):
        rng = np.random.default_rng(0)
        ts_bad, ts_good = [], []
        for _ in range(150):
            r, x = simulate(500, 0.98, 0.0, 0.0, rng)
            b, se = self._defective(r, x, 12)
            ts_bad.append(abs(b / se))
            ts_good.append(abs(HD.hodrick_1b(r, x, 12)["t"]))
        self.assertLess(float(np.median(ts_bad)), 0.30,
                        "the reconstructed defect no longer reproduces 't ~ 0.3'")
        self.assertGreater(float(np.median(ts_good)), 0.45,
                           "the shipped estimator should give median |t| near 0.674")
        self.assertEqual(float(np.mean(np.array(ts_bad) > 1.96)), 0.0,
                         "the defect must be unable to reject at all")


class TheCriterionCorrection(unittest.TestCase):
    """POWER_GATE.md 5.2, reproduced INDEPENDENTLY on this implementation."""

    def test_the_as_committed_criterion_fails_on_the_verified_cell(self):
        """A rule that flags a known-good case is broken, not a finding about the data.
        Ported as the CORRECTION - the rejection rate against its nominal 0.05 - with the
        misspecified quantile carried beside it, marked.

        REPS ARE 1200 AND THE NUMBER IS DERIVED, NOT PICKED. The corrected criterion's
        tolerance is +/-0.015 around 0.05, and the Monte-Carlo standard error of a rejection
        rate is sqrt(0.05*0.95/reps): 0.0138 at 250 draws, so the window would be **1.1 MC
        standard errors wide** and a correctly-sized estimator would fail it by chance
        roughly a quarter of the time. It did, on the first run of this suite. That is
        MB22's own subject committed inside MB23's tests - an assertion made at a sample
        size that cannot resolve what it asserts - and it is recorded rather than fixed by
        loosening the criterion, which would have been silencing the check (RUN_RULES A5).
        At 1200 draws the window is 2.4 MC standard errors and the run costs ~0.9s.
        """
        c = HD.null_calibration(phi=0.98, sd=1.0, n=500, h=12, reps=1200, seed=11)
        self.assertLess(abs(c["var_t_hodrick"] - 1.0), 0.15, "estimator is not unit-variance")
        self.assertLess(abs(c["rejection_rate_at_1_96"] - 0.05), 0.025)
        self.assertTrue(c["agrees"], "the CORRECTED criterion should pass on a verified cell")
        self.assertFalse(c["agrees_criterion_as_committed"],
                         "the misspecified criterion should FAIL here - that is the point")
        self.assertGreater(c["q975_abs_t_hodrick"], 2.1,
                           "q97.5 of |t| for a standard normal is ~2.24, not 1.96")


class TheCrossCheck(unittest.TestCase):
    def test_it_compares_against_the_SHIPPED_hac_tstat_not_a_second_copy(self):
        """Audit B7's defect class. A reimplementation would make this a check on my own
        arithmetic rather than on the number this project publishes."""
        rng = np.random.default_rng(9)
        s = rng.standard_normal(69) + 0.3
        c = HD.cross_check(s, lag=1, h=1)
        self.assertEqual(c["t_newey_west_shipped"], ST.hac_tstat(s, lag=1))
        self.assertEqual(c["t_newey_west_same_rows"], ST.hac_tstat(s[1:], lag=1))
        self.assertEqual(c["t_naive"], ST.naive_tstat(s))

    def test_it_reports_BOTH_comparators_and_requires_BOTH_to_agree(self):
        """Stricter than the register's own bar, and it cannot be accused of picking the
        flattering comparator."""
        rng = np.random.default_rng(4)
        s = rng.standard_normal(69) + 0.4
        c = HD.cross_check(s, lag=1, h=1, tol=0.10)
        self.assertEqual(c["agrees"], c["agrees_vs_shipped"] and c["agrees_vs_same_rows"])
        tight = HD.cross_check(s, lag=1, h=1, tol=0.0)
        self.assertFalse(tight["agrees"], "a zero tolerance must never report agreement")

    def test_the_tolerance_is_the_registered_one(self):
        self.assertEqual(HD.AGREEMENT_TOL, 0.10)

    def test_nan_entries_are_dropped_rather_than_poisoning_the_statistic(self):
        rng = np.random.default_rng(2)
        s = list(rng.standard_normal(40) + 0.2)
        c = HD.cross_check(s + [float("nan")], lag=1, h=1)
        self.assertEqual(c["n"], 40)


class TheSweepCarriesNoVerdict(unittest.TestCase):
    def test_every_row_returns_a_null_verdict_and_says_why(self):
        rng = np.random.default_rng(6)
        rows = HD.horizon_sweep(rng.standard_normal(69) + 0.3)
        self.assertEqual(len(rows), 8)
        for r in rows:
            self.assertIsNone(r["verdict"])
            self.assertIn("no verdict", r["note"])
            self.assertIn("S22", r["note"])

    def test_an_insufficient_sample_is_labelled_rather_than_silently_dropped(self):
        rows = HD.horizon_sweep(np.arange(9.0), horizons=(1, 4, 8))
        self.assertTrue(rows[-1].get("insufficient_sample"))

    def test_the_module_never_writes_a_verdict_string_into_the_sweep(self):
        """AST, not a grep: the docstrings legitimately discuss verdicts."""
        with io.open(os.path.join(HERE, "valuation", "edge", "hodrick.py"),
                     encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "horizon_sweep")
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn("VALIDATED", node.value)
                self.assertNotIn("REJECT", node.value)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if r.wasSuccessful() else 1)
