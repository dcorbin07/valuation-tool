"""
Tests for the O16/O24 term_slope decomposition helpers.

A separate file on purpose: `tests/test_edge.py` is edited by several lanes at once and is not
union-merged, so a new suite here cannot block anyone's landing.

What is pinned:
  * the hand-rolled statistics, against worked examples INCLUDING ties (the case a naive rank
    implementation gets wrong, and the reason these are not one-liners);
  * the committed O16/O24 verdict rules, including that ambiguous returns NULL rather than
    leaning — the rule is executable so it cannot drift to meet the numbers;
  * that `compute_signals` emits the two IV legs additively, i.e. term_slope is still exactly
    atm_mid - atm_front and no existing key changed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_signals_v2 as S2   # noqa: E402


class Statistics(unittest.TestCase):

    def test_ranks_share_the_average_position_across_a_tie(self):
        # values 10, 20, 20, 30 -> ranks 1, 2.5, 2.5, 4
        self.assertEqual(S2._ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])

    def test_ranks_handle_an_all_tied_column(self):
        self.assertEqual(S2._ranks([5, 5, 5]), [2.0, 2.0, 2.0])

    def test_pearson_is_exactly_one_on_a_line(self):
        xs = [1, 2, 3, 4, 5]
        ys = [3, 5, 7, 9, 11]                      # y = 2x + 1
        self.assertAlmostEqual(S2.pearson(xs, ys), 1.0, places=12)

    def test_pearson_is_exactly_minus_one_on_a_falling_line(self):
        self.assertAlmostEqual(S2.pearson([1, 2, 3], [6, 4, 2]), -1.0, places=12)

    def test_pearson_is_none_when_a_side_is_constant(self):
        self.assertIsNone(S2.pearson([1, 1, 1], [1, 2, 3]))

    def test_spearman_is_one_for_a_monotone_but_curved_relation(self):
        # Pearson would NOT be 1 here; Spearman must be, and that difference is the point.
        xs = [1, 2, 3, 4]
        ys = [1, 8, 27, 64]
        self.assertAlmostEqual(S2.spearman(xs, ys), 1.0, places=12)
        self.assertLess(S2.pearson(xs, ys), 0.98)

    def test_spearman_survives_ties_without_blowing_up(self):
        self.assertIsNotNone(S2.spearman([1, 2, 2, 3], [1, 2, 2, 3]))
        self.assertAlmostEqual(S2.spearman([1, 2, 2, 3], [1, 2, 2, 3]), 1.0, places=12)

    def test_none_pairs_are_dropped_not_treated_as_zero(self):
        # A None coerced to 0.0 would drag the correlation; it must be dropped instead.
        xs = [1, 2, 3, None, 5]
        ys = [2, 4, 6, 100, 10]
        self.assertAlmostEqual(S2.pearson(xs, ys), 1.0, places=12)

    def test_ols_recovers_a_known_intercept_and_slope(self):
        a, b = S2.ols_fit([7, 9, 11, 13], [1, 2, 3, 4])       # y = 2x + 5
        self.assertAlmostEqual(a, 5.0, places=10)
        self.assertAlmostEqual(b, 2.0, places=10)

    def test_residuals_of_a_perfect_fit_are_zero(self):
        r = S2.ols_residuals([7, 9, 11, 13], [1, 2, 3, 4])
        for v in r:
            self.assertAlmostEqual(v, 0.0, places=10)

    def test_residuals_keep_position_and_are_none_where_input_was_none(self):
        r = S2.ols_residuals([7, 9, None, 13], [1, 2, 3, 4])
        self.assertEqual(len(r), 4)
        self.assertIsNone(r[2])

    def test_group_mean_r2_is_one_when_groups_perfectly_separate(self):
        ys = [1, 1, 1, 5, 5, 5]
        gs = ["a", "a", "a", "b", "b", "b"]
        self.assertAlmostEqual(S2.group_mean_r2(ys, gs), 1.0, places=12)

    def test_group_mean_r2_is_zero_when_groups_carry_nothing(self):
        ys = [1, 5, 1, 5]
        gs = ["a", "a", "b", "b"]                  # both groups have the same mean
        self.assertAlmostEqual(S2.group_mean_r2(ys, gs), 0.0, places=12)

    def test_variance_decomposition_reproduces_the_identity(self):
        mid = [0.30, 0.32, 0.28, 0.35, 0.31]
        front = [0.40, 0.31, 0.55, 0.33, 0.48]
        d = S2.variance_decomposition(mid, front)
        # var(ts) must equal var(mid) + var(front) - 2cov, exactly
        self.assertAlmostEqual(
            d["var_term_slope"], d["var_atm_mid"] + d["var_atm_front"] - 2 * d["cov"],
            places=12)
        # and the three reported shares must sum to 1
        self.assertAlmostEqual(
            d["share_atm_mid"] + d["share_atm_front"] + d["share_minus_2cov"], 1.0, places=12)

    def test_variance_decomposition_matches_a_direct_variance_of_the_difference(self):
        mid = [0.30, 0.32, 0.28, 0.35, 0.31]
        front = [0.40, 0.31, 0.55, 0.33, 0.48]
        ts = [m - f for m, f in zip(mid, front)]
        n = len(ts)
        mu = sum(ts) / n
        direct = sum((t - mu) ** 2 for t in ts) / (n - 1)
        self.assertAlmostEqual(S2.variance_decomposition(mid, front)["var_term_slope"],
                               direct, places=12)


class CommittedVerdictRules(unittest.TestCase):
    """The rules as committed in the pre-registration. Changing a threshold breaks these."""

    def test_o16_thresholds_are_the_committed_ones(self):
        self.assertEqual(S2.O16_LEVEL_RHO, 0.80)
        self.assertEqual(S2.O16_LEVEL_VAR_SHARE, 0.60)
        self.assertEqual(S2.O16_DISTINCT_RHO, 0.60)
        self.assertEqual(S2.O16_REPRO_MIN_FRAC, 0.99)

    def test_o24_thresholds_are_the_committed_ones(self):
        self.assertEqual(S2.O24_CALENDAR_R2, 0.25)
        self.assertEqual(S2.O24_DISTINCT_R2, 0.10)
        self.assertEqual(S2.O24_MAX_DAYS, 120)

    def test_o16_calls_the_level_only_when_both_conditions_hold(self):
        self.assertEqual(S2.o16_verdict(-0.95, 0.75, 0.20), "IS THE LEVEL")
        # high correlation but the variance sits in the mid leg -> not the level
        self.assertNotEqual(S2.o16_verdict(-0.95, 0.30, 0.80), "IS THE LEVEL")

    def test_o16_calls_distinct_on_a_low_correlation(self):
        self.assertEqual(S2.o16_verdict(0.20, 0.10, 0.05), "IS DISTINCT")

    def test_o16_calls_distinct_when_the_mid_leg_carries_more_variance(self):
        self.assertEqual(S2.o16_verdict(-0.90, 0.40, 0.55), "IS DISTINCT")

    def test_o16_ambiguous_is_a_null_not_a_lean(self):
        # |rho| between the two bars, and the front leg still carries more variance
        self.assertEqual(S2.o16_verdict(-0.70, 0.50, 0.30), "NULL")

    def test_o16_precedence_level_is_evaluated_before_distinct(self):
        # Contrived so BOTH branches could fire; the committed order says LEVEL wins.
        self.assertEqual(S2.o16_verdict(-0.99, 0.95, 0.99), "IS THE LEVEL")

    def test_o24_needs_r2_direction_and_significance_together(self):
        self.assertEqual(S2.o24_verdict(0.40, 0.5, True), "IS THE CALENDAR")
        self.assertNotEqual(S2.o24_verdict(0.40, -0.5, True), "IS THE CALENDAR")
        self.assertNotEqual(S2.o24_verdict(0.40, 0.5, False), "IS THE CALENDAR")

    def test_o24_wrong_sign_never_confirms_however_large_r2_is(self):
        self.assertNotEqual(S2.o24_verdict(0.99, -0.9, True), "IS THE CALENDAR")

    def test_o24_calls_distinct_below_the_floor_and_null_between(self):
        self.assertEqual(S2.o24_verdict(0.02, 0.1, False), "IS DISTINCT")
        self.assertEqual(S2.o24_verdict(0.18, 0.1, False), "NULL")

    def test_verdicts_are_undecidable_rather_than_guessing_on_missing_inputs(self):
        self.assertIn("UNDECIDABLE", S2.o16_verdict(None, 0.5, 0.5))
        self.assertIn("UNDECIDABLE", S2.o24_verdict(None, 0.5, True))


class ReproductionGate(unittest.TestCase):
    """The gate that actually fired on 2026-08-07 and stopped the pre-registered O16."""

    def test_identical_inputs_pass(self):
        v = [0.1, -0.2, 0.3, 0.44]
        g = S2.reproduction_gate(v, list(v))
        self.assertTrue(g["passed"])
        self.assertEqual(g["frac"], 1.0)
        self.assertEqual(g["max_abs_diff"], 0.0)

    def test_a_single_bad_row_in_a_hundred_still_passes_at_99_percent(self):
        banked = [0.10] * 100
        recomputed = [0.10] * 99 + [0.90]
        self.assertTrue(S2.reproduction_gate(banked, recomputed)["passed"])

    def test_two_bad_rows_in_a_hundred_fail(self):
        banked = [0.10] * 100
        recomputed = [0.10] * 98 + [0.90, 0.90]
        g = S2.reproduction_gate(banked, recomputed)
        self.assertFalse(g["passed"])
        self.assertAlmostEqual(g["frac"], 0.98, places=10)

    def test_the_real_shape_of_the_2026_08_07_failure_is_a_fail(self):
        # 86.435% reproduced - what the live chain store actually produced.
        n = 3885
        good = 3358
        banked = [0.10] * n
        recomputed = [0.10] * good + [0.55] * (n - good)
        g = S2.reproduction_gate(banked, recomputed)
        self.assertFalse(g["passed"], "the gate must stop this, it is the case it exists for")
        self.assertAlmostEqual(g["frac"], good / n, places=6)

    def test_tolerance_is_inclusive_so_an_exact_tol_diff_counts_as_matched(self):
        g = S2.reproduction_gate([0.0], [S2.O16_REPRO_TOL])
        self.assertEqual(g["matched"], 1)

    def test_none_rows_are_skipped_not_counted_as_matches(self):
        g = S2.reproduction_gate([0.1, None, 0.3], [0.1, 0.9, 0.3])
        self.assertEqual(g["n"], 2)
        self.assertTrue(g["passed"])

    def test_nothing_comparable_is_a_fail_not_a_vacuous_pass(self):
        g = S2.reproduction_gate([None, None], [None, None])
        self.assertFalse(g["passed"])


class EarningsBuckets(unittest.TestCase):

    def test_every_committed_bucket_is_reachable_and_contiguous(self):
        seen = {S2.earnings_bucket(d) for d in range(0, S2.O24_MAX_DAYS + 1)}
        self.assertIsNone(None if None not in seen else None)   # no gaps inside the window
        self.assertNotIn(None, seen, "a day inside the window fell into no bucket")
        self.assertEqual(len(seen), len(S2.O24_BUCKETS))

    def test_beyond_the_window_is_unknown_not_the_far_bucket(self):
        # The whole point of the eligibility rule: a coverage hole must not read as
        # "far from earnings", which is the answer this lane would find convenient.
        self.assertIsNone(S2.earnings_bucket(S2.O24_MAX_DAYS + 1))
        self.assertIsNone(S2.earnings_bucket(3004))
        self.assertIsNone(S2.earnings_bucket(None))

    def test_negative_days_are_unknown(self):
        self.assertIsNone(S2.earnings_bucket(-1))


class LegsAreEmittedAdditively(unittest.TestCase):
    """AUDIT O16 — the legs must ship, and shipping them must not move term_slope."""

    def _chain(self, expiries=(("2026-08-21", 1.30), ("2026-09-30", 1.00))):
        import pandas as pd
        rows = []
        for exp, iv_scale in expiries:
            for k in (90.0, 100.0, 110.0):
                for right in ("C", "P"):
                    rows.append({"expiration": exp, "strike": k, "right": right,
                                 "bid": 1.0, "ask": 1.2, "open_interest": 100,
                                 "volume": 10, "iv_scale": iv_scale})
        return pd.DataFrame(rows)

    def _run(self, chain, asof):
        import pandas as pd

        def _fake_enrich(df, underlying, a, **kw):
            if df is None or len(df) == 0:
                return pd.DataFrame()
            out = df.copy()
            # IV depends only on the expiry, so both legs are known exactly.
            out["iv"] = [0.20 * s for s in out["iv_scale"]]
            out["delta"] = 0.5
            out["gamma"] = 0.01
            return out

        import valuation.edge.blackscholes as BS
        real = BS.enrich_chain
        BS.enrich_chain = _fake_enrich
        try:
            return S2.compute_signals(chain, 100.0, asof)
        finally:
            BS.enrich_chain = real

    def test_term_slope_is_still_exactly_mid_minus_front(self):
        import datetime as dt
        out = self._run(self._chain(), dt.date(2026, 8, 1))
        self.assertIn("atm_front", out)
        self.assertIn("atm_mid", out)
        self.assertAlmostEqual(out["atm_front"], 0.26, places=10)   # 0.20 * 1.30, 20 DTE
        self.assertAlmostEqual(out["atm_mid"], 0.20, places=10)     # 0.20 * 1.00, 60 DTE
        self.assertAlmostEqual(out["term_slope"], out["atm_mid"] - out["atm_front"],
                               places=12)

    def test_when_the_60_dte_pick_lands_on_the_front_expiry_the_slope_is_zero(self):
        """A construction quirk worth pinning, found by a failing fixture.

        `mid_exp` is the expiry closest to 60 DTE among those AFTER as_of. When the nearest
        expiry is itself the closest to 60 - a sparse chain, or a date deep in the cycle - the
        two legs are the SAME contract and term_slope is identically 0.0. That is a structural
        zero, not a flat term structure, and the two are indistinguishable downstream.
        """
        import datetime as dt
        out = self._run(
            self._chain(expiries=(("2026-09-18", 1.30), ("2026-11-20", 1.00))),
            dt.date(2026, 8, 1))                    # 48 DTE vs 111 DTE -> both legs = front
        self.assertEqual(out["atm_front"], out["atm_mid"])
        self.assertEqual(out["term_slope"], 0.0)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=0).result
    n = r.testsRun
    bad = len(r.failures) + len(r.errors)
    print(f"\n{n - bad}/{n} term_slope decomposition tests passed")
    sys.exit(1 if bad else 0)
