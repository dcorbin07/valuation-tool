"""Tests for O14 (PREREG_o14_tickflow_signals.md).

The load-bearing ones are (a) Lee-Ready's mid-price tick test, which is where an aggressor
classifier silently invents flow, and (b) the TWO-SIDED treatment: this register cannot declare
a sign, so an arm that flips sign between halves must be a NULL even when |t| clears twice.
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import tickflow_signals as T  # noqa: E402


class TestLeeReady(unittest.TestCase):
    def test_above_the_mid_is_a_buy_and_below_is_a_sell(self):
        self.assertEqual(T.lee_ready(1.10, 1.00, 1.20), 0)   # exactly at the mid -> tick test
        self.assertEqual(T.lee_ready(1.15, 1.00, 1.20), 1)
        self.assertEqual(T.lee_ready(1.05, 1.00, 1.20), -1)

    def test_at_the_mid_falls_through_to_the_tick_test(self):
        self.assertEqual(T.lee_ready(1.10, 1.00, 1.20, prev_price=1.05), 1)
        self.assertEqual(T.lee_ready(1.10, 1.00, 1.20, prev_price=1.15), -1)

    def test_at_the_mid_with_no_previous_price_is_UNCLASSIFIED_not_a_guess(self):
        # assigning a side here would manufacture flow out of nothing
        self.assertEqual(T.lee_ready(1.10, 1.00, 1.20, prev_price=None), 0)
        self.assertEqual(T.lee_ready(1.10, 1.00, 1.20, prev_price=1.10), 0)

    def test_a_crossed_or_missing_quote_is_unclassified(self):
        self.assertEqual(T.lee_ready(1.10, 1.30, 1.20), 0)   # crossed
        self.assertEqual(T.lee_ready(1.10, None, 1.20), 0)

    def test_vectorised_matches_the_scalar_rule(self):
        p = [1.15, 1.05, 1.10, 1.10]
        b = [1.00] * 4
        a = [1.20] * 4
        got = T.classify_side(p, b, a)
        self.assertEqual(list(got[:2]), [1, -1])

    def test_the_tick_test_uses_the_previous_DIFFERENT_price(self):
        # a run of identical mid prints must still classify against the last MOVE
        p = [1.05, 1.10, 1.10, 1.10]
        b, a = [1.00] * 4, [1.20] * 4
        got = T.classify_side(p, b, a)
        self.assertEqual(got[0], -1)                 # below mid
        self.assertEqual(list(got[1:]), [1, 1, 1])   # all classify up against 1.05


class TestFeatures(unittest.TestCase):
    def test_signed_volume_is_plus_one_when_everything_is_bought(self):
        self.assertAlmostEqual(T.signed_volume([1, 1, 1], [5, 5, 5]), 1.0)

    def test_signed_volume_is_minus_one_when_everything_is_sold(self):
        self.assertAlmostEqual(T.signed_volume([-1, -1], [2, 3]), -1.0)

    def test_signed_volume_ignores_unclassified_prints(self):
        self.assertAlmostEqual(T.signed_volume([1, 0, -1], [10, 999, 10]), 0.0)

    def test_signed_volume_is_none_when_nothing_is_classified(self):
        self.assertIsNone(T.signed_volume([0, 0], [5, 5]))

    def test_put_call_imbalance_is_one_when_only_puts_are_bought(self):
        v = T.pc_flow_imbalance([1, 1], [10, 10], [2.0, 2.0], ["P", "P"])
        self.assertAlmostEqual(v, 1.0)

    def test_put_call_imbalance_uses_only_BUYER_initiated_flow(self):
        # a large SOLD put must not count as put buying
        v = T.pc_flow_imbalance([1, -1], [1, 100], [2.0, 2.0], ["C", "P"])
        self.assertAlmostEqual(v, 0.0)

    def test_put_call_imbalance_is_premium_weighted_not_count_weighted(self):
        # one expensive call outweighs one cheap put
        v = T.pc_flow_imbalance([1, 1], [1, 1], [10.0, 1.0], ["C", "P"])
        self.assertLess(v, 0.5)

    def test_block_share_finds_a_print_ten_times_the_contract_average(self):
        sides = [1] * 10 + [1]
        sizes = [1] * 10 + [1000]
        prices = [1.0] * 11
        cid = ["A"] * 11
        v = T.block_share(sides, sizes, prices, cid)
        self.assertGreater(v, 0.9)

    def test_block_share_is_zero_when_every_print_is_the_same_size(self):
        v = T.block_share([1] * 5, [10] * 5, [1.0] * 5, ["A"] * 5)
        self.assertAlmostEqual(v, 0.0)

    def test_block_share_is_measured_per_contract_not_across_the_chain(self):
        # a normal print in a big-size contract must not be a block just because another
        # contract trades small
        sides = [1, 1, 1, 1]
        sizes = [100, 100, 1, 1]
        prices = [1.0] * 4
        cid = ["A", "A", "B", "B"]
        self.assertAlmostEqual(T.block_share(sides, sizes, prices, cid), 0.0)

    def test_sweep_share_detects_three_venues_inside_the_window(self):
        v = T.sweep_share([1, 1, 1], [1, 1, 1], [1.0] * 3, ["A"] * 3,
                          [0, 100, 200], [1, 2, 3])
        self.assertAlmostEqual(v, 1.0)

    def test_sweep_share_is_zero_when_the_venues_are_too_slow(self):
        v = T.sweep_share([1, 1, 1], [1, 1, 1], [1.0] * 3, ["A"] * 3,
                          [0, 5000, 10000], [1, 2, 3])
        self.assertAlmostEqual(v, 0.0)

    def test_sweep_share_is_zero_when_one_venue_repeats(self):
        v = T.sweep_share([1, 1, 1], [1, 1, 1], [1.0] * 3, ["A"] * 3,
                          [0, 10, 20], [1, 1, 1])
        self.assertAlmostEqual(v, 0.0)

    def test_sweep_share_groups_by_CONTRACT(self):
        # three venues in 20ms but on three DIFFERENT contracts is not one order working
        v = T.sweep_share([1, 1, 1], [1, 1, 1], [1.0] * 3, ["A", "B", "C"],
                          [0, 10, 20], [1, 2, 3])
        self.assertAlmostEqual(v, 0.0)

    def test_unusual_volume_is_a_ratio_to_the_trailing_median(self):
        self.assertAlmostEqual(T.unusual_volume(300, [100] * 20), 3.0)

    def test_unusual_volume_refuses_a_short_history(self):
        self.assertIsNone(T.unusual_volume(300, [100, 100]))

    def test_unusual_volume_refuses_a_zero_median(self):
        self.assertIsNone(T.unusual_volume(300, [0] * 20))


class TestBenjaminiHochberg(unittest.TestCase):
    def test_all_tiny_pvalues_survive(self):
        self.assertEqual(T.benjamini_hochberg([0.001, 0.002, 0.003], q=0.10),
                         [True, True, True])

    def test_all_large_pvalues_fail(self):
        self.assertEqual(T.benjamini_hochberg([0.5, 0.6, 0.9], q=0.10),
                         [False, False, False])

    def test_step_up_keeps_everything_below_the_largest_passing_rank(self):
        # with m=5, q=0.10: thresholds .02 .04 .06 .08 .10 -- p=0.09 at rank 5 passes,
        # so every smaller p survives even where it fails its own threshold
        got = T.benjamini_hochberg([0.03, 0.05, 0.07, 0.08, 0.09], q=0.10)
        self.assertEqual(got, [True, True, True, True, True])

    def test_bh_is_less_strict_than_bonferroni(self):
        p = [0.02, 0.03, 0.04, 0.05, 0.06]
        bh = T.benjamini_hochberg(p, q=0.10)
        bonf = [x <= 0.10 / len(p) for x in p]
        self.assertGreaterEqual(sum(bh), sum(bonf))

    def test_none_pvalues_are_skipped_rather_than_treated_as_significant(self):
        got = T.benjamini_hochberg([None, 0.001], q=0.10)
        self.assertFalse(got[0])
        self.assertTrue(got[1])


class TestTwoSidedTreatment(unittest.TestCase):
    """§1: no sign can be declared, so a sign flip between halves must be a NULL."""

    def test_a_candidate_needs_both_halves_and_an_agreeing_sign(self):
        self.assertEqual(
            T.arm_verdict(3.0, 2.0, +1, 3.0, 2.0, +1, True), "CANDIDATE")

    def test_a_sign_flip_between_halves_is_a_NULL_even_when_both_halves_clear(self):
        # this is the clause a declared sign would otherwise provide
        self.assertEqual(
            T.arm_verdict(3.0, 2.0, +1, 3.0, 2.0, -1, True), "NULL")

    def test_a_negative_long_short_can_still_be_a_candidate_if_it_is_consistent(self):
        # two-sided: a reliable FADE is as admissible as a reliable follow
        self.assertEqual(
            T.arm_verdict(-3.0, 2.0, -1, -3.0, 2.0, -1, True), "CANDIDATE")

    def test_failing_bh_kills_an_arm_that_cleared_both_bars(self):
        self.assertEqual(
            T.arm_verdict(3.0, 2.0, +1, 3.0, 2.0, +1, False), "NULL")

    def test_exactly_at_the_bar_is_a_null(self):
        self.assertEqual(T.arm_verdict(2.0, 2.0, +1, 3.0, 2.0, +1, True), "NULL")

    def test_permutation_p_never_reads_exactly_zero(self):
        p = T.permutation_p_two_sided(99.0, [0.1] * 100)
        self.assertGreater(p, 0.0)

    def test_permutation_p_is_two_sided_in_magnitude(self):
        # a large NEGATIVE t must be as significant as a large positive one
        a = T.permutation_p_two_sided(-5.0, [0.5] * 200)
        b = T.permutation_p_two_sided(+5.0, [0.5] * 200)
        self.assertAlmostEqual(a, b)


class TestRegisteredConstants(unittest.TestCase):
    def test_constants_match_the_register(self):
        self.assertEqual(T.SEED, 20260812)
        self.assertEqual(T.N_PERM_DRAWS, 2000)
        self.assertEqual(T.N_QUANTILES, 5)
        self.assertEqual(T.SWEEP_MIN_EXCHANGES, 3)
        self.assertEqual(T.SWEEP_WINDOW_MS, 500)
        self.assertEqual(T.BLOCK_SIZE_MULT, 10.0)
        self.assertEqual(T.UNUSUAL_LOOKBACK, 20)
        self.assertEqual(T.BH_Q, 0.10)
        self.assertEqual(T.MIN_MONTHS, 40)
        self.assertEqual(len(T.ARMS), 5)

    def test_nothing_is_adopted(self):
        from valuation.edge import options_fill as OF
        self.assertEqual(OF.DEFAULT_AGGRESSION, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
