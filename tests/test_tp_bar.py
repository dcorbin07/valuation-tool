"""Item A / TP-BAR — pins C1, the calibrated bar (options bot, 2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

What these pin is the part that is easy to fudge later: that the jitter ranges are READ OFF
O1's own tested grid rather than chosen, that the draws are reproducible and seeded by the
project's convention, and that the module imports on a checkout with no licensed data (the
gate has no `data/`, and an import-time failure here fails the whole land).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import tp_bar as TB                       # noqa: E402
from valuation.edge import options_exitlab as XL       # noqa: E402


class TheJitterRangesComeFromO1sTestedGridNotFromMe(unittest.TestCase):
    """The memo says 'jittered within their TESTED ranges'. If these ever drift away from the
    grid O1 actually ran, the bar stops being calibrated against this family and becomes a
    number someone picked."""

    def setUp(self):
        self.pol = dict(XL.POLICIES)

    def test_the_target_range_is_the_tp_arms_endpoints(self):
        tps = [p["tp"] for p in self.pol.values() if p.get("tp") is not None]
        self.assertEqual(TB.TP_RANGE, (min(tps), max(tps)))
        self.assertEqual(TB.TP_RANGE, (0.50, 2.00))

    def test_the_stop_range_is_the_sl_arms_endpoints(self):
        sls = [p["sl"] for p in self.pol.values() if p.get("sl") is not None]
        self.assertEqual(TB.SL_RANGE, (min(sls), max(sls)))
        self.assertEqual(TB.SL_RANGE, (-0.70, -0.30))

    def test_the_time_stop_range_is_the_time_arms_endpoints(self):
        ts = [p["time_frac"] for p in self.pol.values() if p.get("time_frac") is not None]
        self.assertEqual(TB.TIME_RANGE, (min(ts), max(ts)))
        self.assertEqual(TB.TIME_RANGE, (0.25, 1.00))

    def test_the_grid_is_not_vacuous(self):
        """If POLICIES were ever emptied or renamed, the three tests above would compare
        min() of an empty list and blow up rather than pass — but pin the count too."""
        self.assertGreaterEqual(len(self.pol), 20)
        for name in ("shipped", "tp50", "tp200", "sl30", "sl70", "time25", "time100"):
            self.assertIn(name, self.pol)


class TheDrawsAreSeededAndBounded(unittest.TestCase):

    def test_one_hundred_draws_on_the_projects_seed_convention(self):
        self.assertEqual(TB.N_DRAWS, 100)
        self.assertEqual(len(TB.SEEDS), 100)
        self.assertEqual((TB.SEEDS[0], TB.SEEDS[-1]), (1000, 1099))
        self.assertEqual(len(set(TB.SEEDS)), 100)

    def test_a_draw_is_reproducible_from_its_seed_alone(self):
        for s in (1000, 1042, 1099):
            self.assertEqual(TB.draw(s), TB.draw(s))

    def test_draws_differ_between_seeds(self):
        got = [tuple(sorted(TB.draw(s).items())) for s in TB.SEEDS]
        self.assertEqual(len(set(got)), 100)

    def test_every_draw_lands_inside_the_tested_ranges(self):
        for s in TB.SEEDS:
            d = TB.draw(s)
            self.assertGreaterEqual(d["tp"], TB.TP_RANGE[0])
            self.assertLessEqual(d["tp"], TB.TP_RANGE[1])
            self.assertGreaterEqual(d["sl"], TB.SL_RANGE[0])
            self.assertLessEqual(d["sl"], TB.SL_RANGE[1])
            self.assertGreaterEqual(d["time_frac"], TB.TIME_RANGE[0])
            self.assertLessEqual(d["time_frac"], TB.TIME_RANGE[1])

    def test_a_draw_is_a_policy_apply_arm_understands(self):
        """The draw must be scoreable by the SAME function the real arms go through, or the
        null is not measuring the same object."""
        from scripts.path_arms import ARMS
        self.assertEqual(set(TB.draw(1000)), set(ARMS["shipped"]))

    def test_no_leg_is_ever_switched_off(self):
        """`None` is a categorical change, not a jitter. Pinned because drawing `tp: None`
        would smuggle `tp_none` — an already-tested arm — into the null."""
        for s in TB.SEEDS:
            for v in TB.draw(s).values():
                self.assertIsNotNone(v)


class ThePercentileIsTheOneTheBarQuotes(unittest.TestCase):

    def test_it_interpolates_linearly(self):
        self.assertAlmostEqual(TB.percentile(list(range(100)), 95), 94.05)
        self.assertAlmostEqual(TB.percentile([0.0, 1.0], 50), 0.5)

    def test_endpoints(self):
        xs = [3.0, 1.0, 2.0]
        self.assertEqual(TB.percentile(xs, 0), 1.0)
        self.assertEqual(TB.percentile(xs, 100), 3.0)
        self.assertEqual(TB.percentile([7.0], 95), 7.0)

    def test_the_bar_is_the_p95(self):
        self.assertEqual(TB.PCTILE, 95)


class TheModuleSurvivesACheckoutWithNoLicensedData(unittest.TestCase):
    """`data/` is gitignored, so the auto-land gate has no freeze at all. An import-time
    failure here would fail every suite in this file. Learned on 2026-08-10, when
    `scripts/path_study.py` raised SystemExit at import and only a worktree's lookup to the
    primary checkout hid it."""

    def test_import_does_not_require_the_freeze(self):
        self.assertTrue(callable(TB.draw))
        self.assertTrue(callable(TB.score))

    def test_the_module_carries_the_dead_entry_caveat(self):
        self.assertIn("entry", (TB.__doc__ or "").lower())
        self.assertIn("dead", (TB.__doc__ or "").lower())

    def test_the_docstring_says_what_the_null_is_not(self):
        """The null is not a no-effect null and the write-up must not imply it is."""
        self.assertIn("NOT a no-effect null", TB.__doc__ or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
