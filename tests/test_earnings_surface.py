"""Tests for O6 + O7 + O17 (PREREG_o6_o7_o17_earnings_surface.md).

The load-bearing ones are the fail-open tests: a name with no earnings coverage must never be
scored as "no announcement". That is the failure mode the register exists to prevent and the
one a future refactor is most likely to reintroduce, because returning False is more convenient
than returning None everywhere.
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import earnings_surface as ES  # noqa: E402


class TestUnknownIsNeverSafe(unittest.TestCase):
    """The register's §0.2 rule, enforced rather than intended."""

    def test_no_earnings_coverage_returns_unknown_not_safe(self):
        for w in ES.O17_WINDOWS:
            self.assertIsNone(ES.refuse_within("2023-05-08", [], w))
            self.assertIsNone(ES.refuse_within("2023-05-08", None, w))

    def test_unknown_is_distinguishable_from_a_genuine_no(self):
        # A name WITH coverage whose next announcement is far away is a genuine False.
        self.assertIs(ES.refuse_within("2023-05-08", ["2023-09-01"], 5), False)
        # A name WITHOUT coverage is None. If these ever compare equal the guard is gone.
        self.assertIsNone(ES.refuse_within("2023-05-08", [], 5))
        self.assertNotEqual(ES.refuse_within("2023-05-08", [], 5),
                            ES.refuse_within("2023-05-08", ["2023-09-01"], 5))

    def test_owns_the_event_is_unknown_without_coverage(self):
        self.assertIsNone(ES.owns_the_event("2023-05-08", "2023-07-21", []))
        # and unknown when there is no NEXT announcement, not False
        self.assertIsNone(ES.owns_the_event("2023-05-08", "2023-07-21", ["2023-01-02"]))

    def test_partition_keeps_unknown_in_its_own_bucket(self):
        rows = [{"t": "covered_no"}, {"t": "covered_yes"}, {"t": "unknown"}]

        def decide(r):
            return {"covered_no": False, "covered_yes": True, "unknown": None}[r["t"]]

        p = ES.partition(rows, decide)
        self.assertEqual(len(p["kept"]), 1)
        self.assertEqual(len(p["refused"]), 1)
        self.assertEqual(len(p["unknown"]), 1)
        # the buckets must be disjoint and complete
        self.assertEqual(len(p["kept"]) + len(p["refused"]) + len(p["unknown"]), len(rows))


class TestRefuseWindow(unittest.TestCase):
    def test_announcement_inside_the_window_refuses(self):
        self.assertIs(ES.refuse_within("2023-05-08", ["2023-05-10"], 5), True)

    def test_announcement_outside_the_window_does_not(self):
        self.assertIs(ES.refuse_within("2023-05-08", ["2023-05-20"], 5), False)

    def test_the_window_is_inclusive_at_its_edge(self):
        self.assertIs(ES.refuse_within("2023-05-08", ["2023-05-13"], 5), True)
        self.assertIs(ES.refuse_within("2023-05-08", ["2023-05-14"], 5), False)

    def test_a_PAST_announcement_does_not_refuse(self):
        # the rule is "within N days BEFORE an announcement", so an announcement already
        # behind the entry is irrelevant; reading it as a refusal would filter on the past
        self.assertIs(ES.refuse_within("2023-05-08", ["2023-05-01"], 15), False)

    def test_windows_nest(self):
        e, a = "2023-05-08", ["2023-05-18"]
        self.assertIs(ES.refuse_within(e, a, 5), False)
        self.assertIs(ES.refuse_within(e, a, 10), True)
        self.assertIs(ES.refuse_within(e, a, 15), True)

    def test_owns_the_event_true_and_false(self):
        self.assertIs(ES.owns_the_event("2023-05-08", "2023-07-21", ["2023-06-01"]), True)
        self.assertIs(ES.owns_the_event("2023-05-08", "2023-05-19", ["2023-06-01"]), False)


class TestMoneynessBand(unittest.TestCase):
    def test_band_edges_are_inclusive(self):
        self.assertTrue(ES.in_band(90.0, 100.0))
        self.assertTrue(ES.in_band(120.0, 100.0))

    def test_outside_the_band_is_rejected(self):
        self.assertFalse(ES.in_band(89.9, 100.0))
        self.assertFalse(ES.in_band(120.1, 100.0))

    def test_a_bad_spot_is_rejected_rather_than_dividing_by_zero(self):
        self.assertFalse(ES.in_band(100.0, 0.0))
        self.assertFalse(ES.in_band(100.0, None))


class TestIvRank(unittest.TestCase):
    def test_rank_is_the_share_at_or_below(self):
        self.assertAlmostEqual(ES.iv_rank([0.1, 0.2, 0.3, 0.4], 0.25), 0.5)

    def test_an_empty_history_is_None_not_a_neutral_half(self):
        # returning 0.5 would silently score a no-history name as median cheapness
        self.assertIsNone(ES.iv_rank([], 0.3))
        self.assertIsNone(ES.iv_rank([0.1, 0.2], None))

    def test_extremes(self):
        self.assertAlmostEqual(ES.iv_rank([0.2, 0.3], 0.9), 1.0)
        self.assertAlmostEqual(ES.iv_rank([0.2, 0.3], 0.01), 0.0)


class TestSmile(unittest.TestCase):
    def test_a_known_quadratic_is_recovered_and_residuals_vanish(self):
        x = np.linspace(-0.3, 0.3, 11)
        y = 0.20 + 0.5 * x ** 2 - 0.1 * x
        r = ES.smile_residuals(x, y)
        self.assertIsNotNone(r)
        self.assertLess(float(np.max(np.abs(r))), 1e-9)

    def test_a_cheap_contract_has_the_most_negative_residual(self):
        x = np.linspace(-0.3, 0.3, 11)
        y = 0.20 + 0.5 * x ** 2 - 0.1 * x
        y[4] -= 0.05                      # one contract genuinely cheap on the surface
        r = ES.smile_residuals(x, y)
        self.assertEqual(int(np.argmin(r)), 4)

    def test_too_few_points_refuses_rather_than_overfitting(self):
        self.assertIsNone(ES.fit_smile([0.0, 0.1], [0.2, 0.3]))
        self.assertIsNone(ES.smile_residuals([0.0, 0.1, 0.2], [0.2, 0.3, 0.25]))

    def test_degenerate_x_refuses(self):
        self.assertIsNone(ES.fit_smile([0.1] * 8, [0.2] * 8))


class TestPickers(unittest.TestCase):
    def test_pick_extreme_lowest_and_highest(self):
        self.assertEqual(ES.pick_extreme([0.3, 0.1, 0.2]), 1)
        self.assertEqual(ES.pick_extreme([0.3, 0.1, 0.2], lowest=False), 0)

    def test_pick_extreme_skips_none_and_nan(self):
        self.assertEqual(ES.pick_extreme([None, float("nan"), 0.4, 0.2]), 3)

    def test_pick_extreme_returns_none_when_nothing_is_scoreable(self):
        self.assertIsNone(ES.pick_extreme([None, float("nan")]))

    def test_delta_band_is_inclusive_and_symmetric(self):
        m = ES.delta_eligible([0.30, 0.35, 0.40, 0.41], target=0.35)
        self.assertTrue(bool(m[0]) and bool(m[1]) and bool(m[2]))
        self.assertFalse(bool(m[3]))

    def test_delta_band_with_no_target_selects_nothing(self):
        self.assertFalse(ES.delta_eligible([0.3, 0.35], target=None).any())

    def test_vega_per_spread_refuses_a_zero_spread(self):
        self.assertIsNone(ES.vega_per_spread(0.5, 0.0))
        self.assertAlmostEqual(ES.vega_per_spread(0.5, 0.25), 2.0)


class TestTailConcentration(unittest.TestCase):
    def test_one_trade_carrying_everything_reads_one(self):
        self.assertAlmostEqual(ES.tail_concentration([10.0, 0.0, 0.0], k=5), 1.0)

    def test_even_positives_spread_the_concentration(self):
        v = [1.0] * 10
        self.assertAlmostEqual(ES.tail_concentration(v, k=5), 0.5)

    def test_it_is_measured_on_the_positive_side_only(self):
        # with a barbell payoff the SIGNED total can approach zero and explode a ratio; the
        # register's definition avoids flagging that as tail concentration
        v = [10.0, -9.99, 1.0]
        c = ES.tail_concentration(v, k=1)
        self.assertIsNotNone(c)
        self.assertLessEqual(c, 1.0)
        self.assertAlmostEqual(c, 10.0 / 11.0)

    def test_all_losses_returns_none_rather_than_zero(self):
        self.assertIsNone(ES.tail_concentration([-1.0, -2.0]))


class TestNulls(unittest.TestCase):
    def test_random_removal_null_is_centred_on_zero(self):
        rng = np.random.default_rng(0)
        v = rng.normal(0.05, 1.0, 400)
        r = ES.perm_null_removal(v, n_remove=80, draws=400)
        self.assertLess(abs(r["median"]), 0.05)
        self.assertGreater(r["p95"], 0.0)

    def test_removing_the_worst_trades_beats_the_random_null(self):
        rng = np.random.default_rng(1)
        v = np.concatenate([rng.normal(0.0, 0.1, 380), np.full(20, -5.0)])
        r = ES.perm_null_removal(v, n_remove=20, draws=400)
        real_gain = float(np.sort(v)[20:].mean() - v.mean())
        self.assertGreater(real_gain, r["p95"])

    def test_removal_null_refuses_degenerate_sizes(self):
        self.assertIsNone(ES.perm_null_removal([1.0, 2.0], n_remove=0)["p95"])
        self.assertIsNone(ES.perm_null_removal([1.0, 2.0], n_remove=2)["p95"])

    def test_switch_null_is_centred_on_zero_when_alternatives_match_the_base(self):
        rng = np.random.default_rng(2)
        base = rng.normal(0.0, 1.0, 200)
        alts = [rng.normal(0.0, 1.0, 6) for _ in range(200)]
        r = ES.perm_null_switch(alts, base, draws=300)
        self.assertLess(abs(r["median"]), 0.25)

    def test_switch_null_detects_a_genuinely_better_alternative_pool(self):
        rng = np.random.default_rng(3)
        base = rng.normal(0.0, 0.5, 200)
        alts = [rng.normal(2.0, 0.5, 6) for _ in range(200)]
        r = ES.perm_null_switch(alts, base, draws=300)
        self.assertGreater(r["median"], 1.0)

    def test_nulls_are_reproducible_under_the_registered_seed(self):
        v = np.linspace(-1, 1, 200)
        a = ES.perm_null_removal(v, 40, draws=200, seed=ES.SEED)
        b = ES.perm_null_removal(v, 40, draws=200, seed=ES.SEED)
        self.assertEqual(a["p95"], b["p95"])


class TestVerdicts(unittest.TestCase):
    def test_o6_candidate_needs_both_halves(self):
        self.assertEqual(ES.o6_verdict(0.5, 0.2, 0.4, 0.4, 0.5, 0.2, 0.4, 0.4), "CANDIDATE")
        self.assertEqual(ES.o6_verdict(0.5, 0.2, 0.4, 0.4, 0.1, 0.2, 0.4, 0.4), "NULL")

    def test_o6_rejects_when_tail_concentration_rises(self):
        self.assertEqual(ES.o6_verdict(0.5, 0.2, 0.4, 0.9, 0.5, 0.2, 0.4, 0.4), "NULL")

    def test_o6_ambiguous_against_the_bar_is_a_null(self):
        # exactly equal to the p95 is NOT a pass (RUN_RULES A6)
        self.assertEqual(ES.o6_verdict(0.2, 0.2, 0.4, 0.4, 0.5, 0.2, 0.4, 0.4), "NULL")

    def test_o17_enforces_the_retention_floor(self):
        self.assertEqual(ES.o17_verdict(0.5, 0.2, 0.95, 0.5, 0.2, 0.95), "CANDIDATE")
        self.assertEqual(ES.o17_verdict(0.5, 0.2, 0.50, 0.5, 0.2, 0.95), "NULL")

    def test_o17_retention_floor_boundary_is_the_registered_value(self):
        self.assertEqual(ES.o17_verdict(0.5, 0.2, ES.RETENTION_FLOOR, 0.5, 0.2, 0.95),
                         "CANDIDATE")
        self.assertEqual(ES.o17_verdict(0.5, 0.2, ES.RETENTION_FLOOR - 1e-9, 0.5, 0.2, 0.95),
                         "NULL")

    def test_o7_direction_reads_both_signs_and_the_null(self):
        self.assertEqual(ES.o7_direction(0.01, 0.002, 0.02), "CHEAP")
        self.assertEqual(ES.o7_direction(-0.01, -0.02, -0.002), "RICH")
        self.assertEqual(ES.o7_direction(0.01, -0.002, 0.02), "NULL")

    def test_o7_published_sign_is_cheap_and_is_not_silently_flipped(self):
        # Gao-Xing-Zhang say realised EXCEEDS implied, i.e. straddles are underpriced.
        # A positive interval must therefore read CHEAP, never RICH.
        self.assertEqual(ES.o7_direction(0.05, 0.01, 0.09), "CHEAP")


class TestSplitAdjustedSpotIsNotUsedAgainstAsTradedStrikes(unittest.TestCase):
    """The U1-SPLIT defect class, pinned in the place it recurred.

    Option chains are as-traded and unadjusted; the bars cache's `close` is adjusted. Matching an
    as-traded strike against an adjusted spot picks a contract nowhere near the money, and the
    error is silent: the straddle still prices, it is simply mostly intrinsic. These tests fail
    if the default source ever goes back to the adjusted series.
    """

    def test_the_default_price_field_is_the_raw_one(self):
        import inspect
        from scripts import o6_o7_o17_earnings as R
        sig = inspect.signature(R.load_close)
        self.assertEqual(sig.parameters["field"].default, "raw_close")

    def test_an_adjusted_spot_moves_the_atm_strike_far_off_the_money(self):
        # NVDA-shaped: a 40x cumulative split factor between trade date and today.
        strikes = [100.0, 110.0, 120.0, 130.0]
        raw_spot, adjusted_spot = 120.0, 120.0 / 40.0
        atm_raw = min(strikes, key=lambda k: abs(k - raw_spot))
        atm_adj = min(strikes, key=lambda k: abs(k - adjusted_spot))
        self.assertEqual(atm_raw, 120.0)
        self.assertEqual(atm_adj, 100.0)          # the lowest strike, deep in the money
        self.assertGreater(abs(atm_adj / raw_spot - 1.0), 0.15)

    def test_the_moneyness_band_silently_empties_under_an_adjusted_spot(self):
        # in_band is the gate O6 uses to build its candidate set; an adjusted spot does not
        # raise, it just returns an empty set, which is the dangerous failure mode
        strikes = [100.0, 110.0, 120.0, 130.0]
        raw_spot = 120.0
        self.assertTrue(any(ES.in_band(k, raw_spot) for k in strikes))
        self.assertFalse(any(ES.in_band(k, raw_spot / 40.0) for k in strikes))


class TestRegisteredConstants(unittest.TestCase):
    """Pinned so a silent edit to a pre-committed number is loud."""

    def test_constants_match_the_register(self):
        self.assertEqual(ES.SEED, 20260812)
        self.assertEqual(ES.N_PERM_DRAWS, 2000)
        self.assertEqual((ES.MONEYNESS_LO, ES.MONEYNESS_HI), (0.90, 1.20))
        self.assertEqual(ES.DELTA_BAND, 0.05)
        self.assertEqual(ES.IV_RANK_WINDOW, 252)
        self.assertEqual(ES.O17_WINDOWS, (5, 10, 15))
        self.assertEqual(ES.RETENTION_FLOOR, 0.70)
        self.assertEqual((ES.O7_PRE_DAYS, ES.O7_POST_DAYS), (3, 1))
        self.assertEqual(ES.O7_COVERAGE_FLOOR, 0.40)
        self.assertEqual(ES.TAIL_K, 5)

    def test_default_aggression_is_untouched(self):
        from valuation.edge import options_fill as OF
        self.assertEqual(OF.DEFAULT_AGGRESSION, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
