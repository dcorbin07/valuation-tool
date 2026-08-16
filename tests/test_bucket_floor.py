"""O26 — pins the per-bucket floor study (2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

The statistic under test is the literal reading of the constant's own comment -- "enough that one
lucky contract cannot flip the verdict" -- so these tests mostly pin that the statistic really
measures that, and that the verdict rule fails toward KEEPING the shipped value.
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import bucket_floor as BF        # noqa: E402


class TheStatistic(unittest.TestCase):
    def test_the_removed_trade_is_the_most_extreme_not_the_best(self):
        """Removing the BEST trade would build the answer's direction into its own definition
        and would push every draw the same way. `argmax |R - mean|` is chosen without reference
        to which way it moves the mean."""
        rs = [-5.0, 0.1, 0.1, 0.1]
        self.assertEqual(BF.most_extreme_index(rs), 0)      # the big LOSER, not the best trade
        rs2 = [5.0, 0.1, 0.1, 0.1]
        self.assertEqual(BF.most_extreme_index(rs2), 0)

    def test_a_single_dominant_winner_flips_a_positive_mean(self):
        rs = [10.0] + [-0.5] * 9                            # mean +0.55, without the winner -0.5
        self.assertTrue(BF.flips_sign(rs))

    def test_a_balanced_bucket_does_not_flip(self):
        rs = [0.5] * 20
        self.assertFalse(BF.flips_sign(rs))

    def test_an_exactly_zero_mean_is_not_scored_either_way(self):
        """No sign to flip. Counting it as a flip inflates the statistic and counting it as a
        non-flip deflates it, so it is excluded and the exclusion is visible in `draws`."""
        self.assertIsNone(BF.flips_sign([1.0, -1.0]))

    def test_ties_break_deterministically(self):
        rs = [1.0, -1.0, 1.0, -1.0]
        self.assertEqual(BF.most_extreme_index(rs), BF.most_extreme_index(list(rs)))

    def test_p_flip_is_seeded_and_reproducible(self):
        rng = random.Random(0)
        rs = [rng.gauss(0.03, 1.0) for _ in range(300)]
        a = BF.p_flip(rs, 30, draws=200, seed=7)
        b = BF.p_flip(rs, 30, draws=200, seed=7)
        self.assertEqual(a, b)

    def test_p_flip_falls_as_the_bucket_grows(self):
        """The whole premise of a floor: bigger buckets must be harder to flip."""
        rng = random.Random(1)
        rs = [rng.gauss(0.03, 1.0) for _ in range(600)]
        small = BF.p_flip(rs, 10, draws=600, seed=3)["p_flip"]
        big = BF.p_flip(rs, 200, draws=600, seed=3)["p_flip"]
        self.assertGreater(small, big)

    def test_a_heavy_tail_flips_more_often_AT_THE_SAME_MEAN(self):
        """The constant's comment blames heavy tails, and the statistic does see that -- but
        ONLY when the mean is held fixed.

        WHAT THIS TEST CORRECTS. The first version compared a light distribution of mean 0.05
        against a heavy one whose mean worked out to +1.16, and the heavy one flipped LESS often
        (0.021 vs 0.105). That is not a defect in the statistic: `P_flip` is governed by how
        close the bucket mean sits to zero RELATIVE to one trade's influence, and a mean far
        from zero is hard to flip however fat the tail. Both arms below are built to mean 0.05
        exactly, and then the tail weight is the only thing that differs.
        """
        rng = random.Random(2)
        light = [0.05 + rng.gauss(0, 0.2) for _ in range(2000)]
        # 10% at +5.0 and 90% at -0.5 also averages 0.05, with one trade carrying far more.
        heavy = [(5.0 if rng.random() < 0.10 else -0.5) for _ in range(2000)]
        self.assertAlmostEqual(sum(light) / len(light), 0.05, places=1)
        self.assertAlmostEqual(sum(heavy) / len(heavy), 0.05, places=1)
        pl = BF.p_flip(light, 30, draws=1500, seed=5)["p_flip"]
        ph = BF.p_flip(heavy, 30, draws=1500, seed=5)["p_flip"]
        self.assertGreater(ph, pl)

    def test_p_flip_is_governed_by_distance_from_zero_not_tail_weight_alone(self):
        """The corollary, pinned because it qualifies what O26's result means: the same shape
        shifted away from zero flips far less often."""
        rng = random.Random(9)
        base = [rng.gauss(0.0, 1.0) for _ in range(1000)]
        near_zero = [x + 0.02 for x in base]
        far = [x + 1.50 for x in base]
        self.assertGreater(BF.p_flip(near_zero, 30, draws=1000, seed=4)["p_flip"],
                           BF.p_flip(far, 30, draws=1000, seed=4)["p_flip"])


class TheFloorAndVerdict(unittest.TestCase):
    def test_the_floor_is_the_smallest_n_clearing_the_bar(self):
        rows = [{"n": 10, "p_flip": 0.30}, {"n": 30, "p_flip": 0.10},
                {"n": 50, "p_flip": 0.04}, {"n": 100, "p_flip": 0.01}]
        self.assertEqual(BF.floor_from_curve(rows), 50)

    def test_no_n_clearing_the_bar_returns_none(self):
        rows = [{"n": 10, "p_flip": 0.30}, {"n": 300, "p_flip": 0.11}]
        self.assertIsNone(BF.floor_from_curve(rows))

    def test_a_missing_floor_on_either_half_is_a_null(self):
        self.assertEqual(BF.verdict(None, 50), "NULL")
        self.assertEqual(BF.verdict(50, None), "NULL")

    def test_halves_more_than_one_grid_step_apart_are_a_null(self):
        self.assertEqual(BF.verdict(30, 150), "NULL")

    def test_halves_within_one_grid_step_raise(self):
        self.assertEqual(BF.verdict(75, 100), "RAISE")
        self.assertEqual(BF.verdict(100, 100), "RAISE")

    def test_a_floor_at_or_below_the_shipped_value_keeps_thirty(self):
        self.assertEqual(BF.verdict(20, 30), "KEEP_30")

    def test_a_null_keeps_the_shipped_value(self):
        """The failure direction must always be 'keep 30', never 'adopt an unvalidated number'."""
        for v in (BF.verdict(None, None), BF.verdict(10, 300)):
            self.assertEqual(v, "NULL")

    def test_a_floor_off_the_grid_is_a_null_not_an_index_error(self):
        self.assertEqual(BF.verdict(37, 50), "NULL")


class TheRegisterIsHonoured(unittest.TestCase):
    def test_the_grid_and_bar_are_the_registered_ones(self):
        self.assertEqual(BF.N_GRID, (10, 20, 30, 40, 50, 75, 100, 150, 200, 300))
        self.assertEqual(BF.FLIP_BAR, 0.05)
        self.assertEqual(BF.DRAWS, 5000)

    def test_the_shipped_floor_constant_matches_options_tracker(self):
        """If the live constant ever moves, this study's baseline must move with it."""
        from valuation.edge.options_tracker import MIN_CLOSED_PER_BUCKET
        self.assertEqual(BF.SHIPPED_FLOOR, MIN_CLOSED_PER_BUCKET)


if __name__ == "__main__":
    unittest.main(verbosity=2)
