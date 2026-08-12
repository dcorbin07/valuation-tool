"""O10 + O18 — pins the passive-fill model and the spread-conditional cost measurement.

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

THE LOAD-BEARING ONES, and why each exists:

  * `test_the_fast_range_min_is_exactly_the_reference` — the fill scan is a sliding-window
    minimum done with a sparse table. A quadratic reference is obvious and correct; the fast
    version is neither, so it is held against the reference on random tapes.
  * `test_adverse_selection_is_negative_when_fills_precede_declines` — the sign convention here
    is the entire point of O10. Getting it backwards would turn a cost into a saving and would
    raise no exception.
  * `test_a_passive_fill_is_not_a_free_half_spread` — the naive answer (gross saving only) and
    the registered answer must differ on a tape built to punish patience.
  * `test_the_permutation_null_holds_the_marginals_and_bin_sizes_fixed` — the null must move
    ONLY the labels. If it resampled values it would not be the registered instrument.
  * `test_default_aggression_is_untouched` — both registers fix in advance that nothing is
    adopted in this session whatever the verdict. This fails if that is ever quietly changed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np                                    # noqa: E402
from valuation.edge import tickflow as TF             # noqa: E402
from valuation.edge import options_fill as F          # noqa: E402


def brute_window_min(t, p, horizon_s):
    """Obvious O(n^2) reference for the sliding-window minimum."""
    n = len(t)
    out = np.full(n, np.inf)
    for i in range(n):
        end = t[i] + horizon_s
        best = np.inf
        for j in range(i + 1, n):
            if t[j] > end:
                break
            best = min(best, p[j])
        out[i] = best
    return out


class TestRangeMin(unittest.TestCase):
    def test_the_fast_range_min_is_exactly_the_reference(self):
        rng = np.random.default_rng(5)
        for trial in range(25):
            n = int(rng.integers(2, 60))
            t = np.sort(rng.integers(34200, 57600, size=n)).astype(np.int64)
            p = np.round(rng.uniform(0.05, 20.0, size=n), 2)
            h = int(rng.choice([60, 300, 900, 1800]))
            hi = np.searchsorted(t, t + h, side="right")
            lo = np.arange(n, dtype=np.int64) + 1
            levels, log = TF._sparse_min(p)
            fast = TF._range_min(levels, log, lo, hi)
            ref = brute_window_min(t, p, h)
            self.assertTrue(np.allclose(fast, ref, equal_nan=True),
                            "trial %d: fast range-min disagrees with the reference" % trial)

    def test_an_empty_window_is_infinite_not_zero(self):
        p = np.array([1.0, 2.0, 3.0])
        levels, log = TF._sparse_min(p)
        out = TF._range_min(levels, log, np.array([1]), np.array([1]))
        self.assertTrue(np.isinf(out[0]), "an empty window must not look like a fill at 0.0")


class TestEligibility(unittest.TestCase):
    def test_the_two_code_groups_are_disjoint(self):
        self.assertEqual(set(TF.SINGLE_LEG_CODES) & set(TF.PACKAGE_CODES), set())

    def test_package_codes_are_not_in_the_primary_set(self):
        for c in TF.PACKAGE_CODES:
            self.assertNotIn(c, TF.SINGLE_LEG_CODES)

    def test_crossed_locked_and_one_sided_quotes_are_rejected(self):
        bid = np.array([1.0, 1.0, 0.0, 1.0, 2.0])
        ask = np.array([1.2, 1.0, 1.2, 0.0, 1.0])     # ok, locked, no bid, no ask, crossed
        cond = np.array([18, 18, 18, 18, 18])
        m = TF.eligible_mask(bid, ask, cond)
        self.assertTrue(m[0])
        self.assertFalse(m[1:].any())

    def test_only_the_requested_codes_survive(self):
        bid = np.full(4, 1.0)
        ask = np.full(4, 1.2)
        cond = np.array([18, 130, 35, 125])
        m = TF.eligible_mask(bid, ask, cond)
        self.assertTrue(bool(m[0]) and bool(m[2]))
        self.assertFalse(bool(m[1]) or bool(m[3]))


class TestSignedAggression(unittest.TestCase):
    def test_plus_one_at_the_ask_minus_one_at_the_bid_zero_at_mid(self):
        bid = np.array([1.0, 1.0, 1.0])
        ask = np.array([1.4, 1.4, 1.4])
        px = np.array([1.4, 1.0, 1.2])
        e = TF.signed_aggression(px, bid, ask)
        self.assertAlmostEqual(e[0], +1.0, places=9)
        self.assertAlmostEqual(e[1], -1.0, places=9)
        self.assertAlmostEqual(e[2], 0.0, places=9)

    def test_a_print_outside_the_nbbo_exceeds_one_rather_than_being_clipped(self):
        e = TF.signed_aggression(np.array([1.6]), np.array([1.0]), np.array([1.4]))
        self.assertGreater(e[0], 1.0)


class TestPassiveStats(unittest.TestCase):
    def _tape(self, prices, t0=34200, step=60, bid_off=0.10):
        t = np.arange(len(prices), dtype=np.int64) * step + t0
        p = np.asarray(prices, dtype=np.float64)
        bid = p - bid_off
        ask = p + bid_off
        return t, p, bid, ask

    def test_the_marketable_baseline_fills_everywhere_except_the_final_reference(self):
        """C3 as a unit invariant, stated exactly rather than as `~1.0`.

        At lam=+1 the limit IS the ask, so every reference moment fills against any later print.
        The LAST reference moment has no later print by construction, so the fill rate is
        (n-1)/n and not 1.0. That is a boundary property of the tape, not a model failure -- and
        the marketable BASELINE itself never depends on this row, because it enters the
        arithmetic through `E_all[delta]`, which is taken over every reference moment.
        """
        t, p, bid, ask = self._tape([2.0] * 20)
        r = TF.passive_stats(t, p, bid, ask, lam=1.0, horizon_min=30, entry_premium=2.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["n_ref"], 20)
        self.assertEqual(r["n_fill"], 19)
        self.assertAlmostEqual(r["fill_rate"], 19.0 / 20.0, places=12)

    def test_a_resting_bid_does_not_fill_on_a_tape_that_only_rises(self):
        t, p, bid, ask = self._tape([2.0 + 0.05 * i for i in range(20)])
        r = TF.passive_stats(t, p, bid, ask, lam=-1.0, horizon_min=30, entry_premium=2.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["n_fill"], 0, "a bid cannot be hit by a strictly rising tape")

    def test_gross_saving_is_zero_at_the_incumbent_and_a_full_half_spread_at_the_mid(self):
        t, p, bid, ask = self._tape([2.0] * 20, bid_off=0.10)   # half = 0.10
        top = TF.passive_stats(t, p, bid, ask, lam=1.0, horizon_min=30, entry_premium=2.0)
        mid = TF.passive_stats(t, p, bid, ask, lam=0.0, horizon_min=30, entry_premium=2.0)
        self.assertAlmostEqual(top["gross_pp"], 0.0, places=9)
        # half=0.10 on a 2.00 premium = 5.00pp
        self.assertAlmostEqual(mid["gross_pp"], 5.0, places=6)

    def test_adverse_selection_is_negative_when_fills_precede_declines(self):
        """Flat, then a one-way collapse. A resting bid is hit only into the collapse."""
        prices = [3.0] * 15 + [3.0 - 0.10 * i for i in range(1, 16)]
        t, p, bid, ask = self._tape(prices)
        r = TF.passive_stats(t, p, bid, ask, lam=-1.0, horizon_min=30, entry_premium=3.0)
        self.assertIsNotNone(r)
        self.assertGreater(r["n_fill"], 0)
        self.assertLess(r["adverse_pp"], 0.0,
                        "fills that precede a decline must score as a COST, not a saving")

    def test_a_passive_fill_is_not_a_free_half_spread(self):
        prices = [3.0] * 15 + [3.0 - 0.10 * i for i in range(1, 16)]
        t, p, bid, ask = self._tape(prices)
        r = TF.passive_stats(t, p, bid, ask, lam=-1.0, horizon_min=30, entry_premium=3.0)
        self.assertLess(r["npa_pp"], r["gross_pp"],
                        "the registered NPA must be strictly below the naive gross saving here")

    def test_no_drift_means_npa_equals_the_gross_saving(self):
        t, p, bid, ask = self._tape([2.0] * 40)
        r = TF.passive_stats(t, p, bid, ask, lam=0.0, horizon_min=30, entry_premium=2.0)
        self.assertAlmostEqual(r["adverse_pp"], 0.0, places=9)
        self.assertAlmostEqual(r["npa_pp"], r["gross_pp"], places=9)

    def test_reference_points_past_the_close_are_dropped_not_truncated(self):
        # last print at 15:59; a 30-minute horizon runs past 16:00 for every late reference
        n = 20
        t = np.arange(n, dtype=np.int64) * 60 + (SESSION := TF.SESSION_CLOSE_S) - n * 60 + 60
        p = np.full(n, 2.0)
        r = TF.passive_stats(t, p, p - 0.1, p + 0.1, lam=0.0, horizon_min=30, entry_premium=2.0)
        self.assertIsNone(r, "every reference moment runs past the close, so the cell is empty")
        self.assertEqual(SESSION, 16 * 3600)

    def test_rest_of_session_drops_nothing(self):
        t, p, bid, ask = self._tape([2.0] * 20, t0=TF.SESSION_CLOSE_S - 3600)
        r = TF.passive_stats(t, p, bid, ask, lam=0.0, horizon_min=None, entry_premium=2.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["n_ref"], 20)

    def test_a_single_print_day_returns_none_rather_than_a_fake_zero(self):
        t = np.array([34200], dtype=np.int64)
        p = np.array([2.0])
        self.assertIsNone(TF.passive_stats(t, p, p - 0.1, p + 0.1, 0.0, 30, 2.0))

    def test_fill_rate_is_monotone_in_the_limit_level(self):
        rng = np.random.default_rng(11)
        p = np.round(2.0 + np.cumsum(rng.normal(0, 0.03, 200)), 2)
        p = np.clip(p, 0.20, None)
        t = np.arange(200, dtype=np.int64) * 10 + 34200
        rates = []
        for lam in TF.LAMBDA_GRID:                      # +1.0 down to -1.0
            r = TF.passive_stats(t, p, p - 0.08, p + 0.08, lam, 30, 2.0)
            rates.append(r["fill_rate"])
        self.assertTrue(all(rates[i] >= rates[i + 1] - 1e-12 for i in range(len(rates) - 1)),
                        "a lower limit can never be easier to fill: %r" % (rates,))


class TestRho(unittest.TestCase):
    def test_rho_is_one_when_every_print_is_at_the_touch(self):
        bid = np.full(6, 1.0)
        ask = np.full(6, 1.4)
        px = np.array([1.4, 1.0, 1.4, 1.0, 1.4, 1.0])
        r = TF.rho_contract_day(px, bid, ask)
        self.assertAlmostEqual(r["rho_u"], 1.0, places=9)

    def test_rho_is_zero_when_every_print_is_at_mid(self):
        bid = np.full(4, 1.0)
        ask = np.full(4, 1.4)
        r = TF.rho_contract_day(np.full(4, 1.2), bid, ask)
        self.assertAlmostEqual(r["rho_u"], 0.0, places=9)

    def test_size_weighting_actually_weights(self):
        bid = np.array([1.0, 1.0])
        ask = np.array([1.4, 1.4])
        px = np.array([1.4, 1.2])                     # rho = 1 and 0
        r = TF.rho_contract_day(px, bid, ask, size=np.array([99.0, 1.0]))
        self.assertGreater(r["rho_w"], 0.9)
        self.assertAlmostEqual(r["rho_u"], 0.5, places=9)

    def test_zero_and_negative_sizes_fall_back_rather_than_dividing_by_zero(self):
        bid = np.array([1.0, 1.0])
        ask = np.array([1.4, 1.4])
        px = np.array([1.4, 1.2])
        r = TF.rho_contract_day(px, bid, ask, size=np.array([0.0, 0.0]))
        self.assertAlmostEqual(r["rho_w"], 0.5, places=9)


class TestQuantilesAndRange(unittest.TestCase):
    def test_quintiles_are_roughly_equal_sized_on_a_continuum(self):
        lb = TF.quintile_labels(np.arange(1000, dtype=float))
        counts = [int((lb == j).sum()) for j in range(5)]
        self.assertTrue(all(abs(c - 200) <= 2 for c in counts), counts)

    def test_r_range_is_zero_on_a_flat_signal(self):
        v = np.ones(500)
        lb = TF.quintile_labels(np.arange(500, dtype=float))
        self.assertAlmostEqual(TF.r_range(v, lb), 0.0, places=12)

    def test_r_range_recovers_a_planted_gradient(self):
        lb = np.repeat(np.arange(5), 100)
        v = lb.astype(float) * 2.0
        self.assertAlmostEqual(TF.r_range(v, lb), 8.0, places=9)

    def test_a_single_populated_bin_returns_none_rather_than_zero(self):
        self.assertIsNone(TF.r_range(np.ones(10), np.zeros(10, dtype=np.int64)))


class TestPermutationNull(unittest.TestCase):
    def test_the_permutation_null_holds_the_marginals_and_bin_sizes_fixed(self):
        rng = np.random.default_rng(2)
        v = rng.normal(size=300)
        lb = np.repeat(np.arange(5), 60)
        before_vals = np.sort(v.copy())
        before_sizes = sorted(int((lb == j).sum()) for j in range(5))
        TF.perm_null_r_range(v, lb, draws=50, seed=1)
        self.assertTrue(np.allclose(np.sort(v), before_vals), "values must not be resampled")
        self.assertEqual(sorted(int((lb == j).sum()) for j in range(5)), before_sizes)

    def test_a_planted_gradient_beats_its_own_null(self):
        lb = np.repeat(np.arange(5), 80)
        v = lb.astype(float) + np.random.default_rng(4).normal(0, 0.05, 400)
        null = TF.perm_null_r_range(v, lb, draws=300, seed=7)
        self.assertGreater(TF.r_range(v, lb), null["p95"])

    def test_pure_noise_does_not_beat_its_own_null_on_average(self):
        rng = np.random.default_rng(9)
        beat = 0
        for s in range(20):
            v = rng.normal(size=400)
            lb = np.repeat(np.arange(5), 80)
            rng.shuffle(lb)
            null = TF.perm_null_r_range(v, lb, draws=200, seed=100 + s)
            if TF.r_range(v, lb) > null["p95"]:
                beat += 1
        self.assertLessEqual(beat, 4, "a 5%% bar should not fire on %d of 20 noise draws" % beat)


class TestSpearman(unittest.TestCase):
    def test_perfect_monotone_is_plus_one_and_reversed_is_minus_one(self):
        x = np.arange(10, dtype=float)
        self.assertAlmostEqual(TF.spearman(x, x * 3 + 1), 1.0, places=9)
        self.assertAlmostEqual(TF.spearman(x, -x), -1.0, places=9)

    def test_a_constant_returns_none_rather_than_zero(self):
        self.assertIsNone(TF.spearman(np.arange(10, dtype=float), np.ones(10)))


class TestVerdicts(unittest.TestCase):
    def test_material_needs_both_halves_on_both_bars(self):
        self.assertEqual(TF.o10_verdict(1.5, 0.6, 1.5, 0.6), "MATERIAL")
        self.assertEqual(TF.o10_verdict(1.5, 0.6, 0.4, 0.6), "NULL")   # late half fails NPA
        self.assertEqual(TF.o10_verdict(1.5, 0.6, 1.5, 0.3), "PARTIAL")

    def test_exactly_at_the_bar_clears_and_a_hair_under_does_not(self):
        self.assertEqual(TF.o10_verdict(TF.NPA_BAR_PP, TF.FILL_RATE_BAR,
                                        TF.NPA_BAR_PP, TF.FILL_RATE_BAR), "MATERIAL")
        self.assertEqual(TF.o10_verdict(TF.NPA_BAR_PP - 1e-9, 0.9,
                                        TF.NPA_BAR_PP, 0.9), "NULL")

    def test_a_missing_half_is_a_null_not_a_pass(self):
        self.assertEqual(TF.o10_verdict(None, 0.9, 2.0, 0.9), "NULL")
        self.assertEqual(TF.o10_verdict(float("nan"), 0.9, 2.0, 0.9), "NULL")

    def test_o18_needs_both_halves_to_clear_and_to_agree_in_sign(self):
        self.assertEqual(TF.o18_family_verdict(0.5, 0.2, +0.9, 0.6, 0.3, +0.8), "WARRANTED")
        self.assertEqual(TF.o18_family_verdict(0.5, 0.2, +0.9, 0.6, 0.3, -0.8), "NULL")
        self.assertEqual(TF.o18_family_verdict(0.1, 0.2, +0.9, 0.6, 0.3, +0.8), "NULL")


class TestBootstrap(unittest.TestCase):
    def test_the_bootstrap_resamples_months_not_trades(self):
        v = np.concatenate([np.zeros(50), np.ones(50) * 10])
        b = np.array(["2020-01"] * 50 + ["2020-02"] * 50)
        r = TF.block_bootstrap_mean(v, b, draws=400, seed=3)
        self.assertEqual(r["n_blocks"], 2)
        # with 2 blocks the mean can only be 0, 5 or 10 -> the interval must span that
        self.assertLessEqual(r["lo"], 0.001)
        self.assertGreaterEqual(r["hi"], 9.999)

    def test_month_blocks_are_calendar_months(self):
        b = TF.month_blocks(["2020-01-15", "2020-01-31", "2020-02-01"])
        self.assertEqual(list(b), ["2020-01", "2020-01", "2020-02"])


class TestNonChangePins(unittest.TestCase):
    def test_default_aggression_is_untouched(self):
        """Both registers fix in advance that nothing is adopted in this session."""
        self.assertEqual(F.DEFAULT_AGGRESSION, 1.0,
                         "O10/O18 route a policy change to Don; they do not make one")

    def test_the_registered_constants_match_the_register(self):
        self.assertEqual(TF.SINGLE_LEG_CODES, (0, 18, 35, 95, 106))
        self.assertEqual(TF.PACKAGE_CODES, (125, 130, 131))
        self.assertEqual(TF.MIN_PRINTS, 10)
        self.assertEqual(TF.LAMBDA_GRID, (1.0, 0.5, 0.0, -0.5, -1.0))
        self.assertEqual(TF.HORIZONS_MIN, (5, 15, 30, 60, None))
        self.assertEqual(TF.PRIMARY_LAMBDA, 0.0)
        self.assertEqual(TF.PRIMARY_HORIZON_MIN, 30)
        self.assertEqual(TF.NPA_BAR_PP, 1.00)
        self.assertEqual(TF.FILL_RATE_BAR, 0.50)
        self.assertEqual(TF.SPLIT_DATE, "2021-03-08")
        self.assertEqual(TF.N_PERM_DRAWS, 2000)
        self.assertEqual(TF.PERM_SEED, 20260811)


if __name__ == "__main__":
    unittest.main(verbosity=2)
