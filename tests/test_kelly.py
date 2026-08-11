"""O12 — pins fractional Kelly and the ruin machinery (2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

Two of these tests exist because the register named a specific way the implementation could be
silently wrong, and a check is the only thing that separates "the arithmetic is right" from "the
arithmetic looks right": `f*` must be 0 on a zero-mean distribution, and `f*` must reproduce the
closed-form Kelly fraction on a two-outcome bet where the answer is known independently.
"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import kelly as K               # noqa: E402


class TheClosedFormCheck(unittest.TestCase):
    def test_it_reproduces_the_textbook_kelly_fraction_on_a_two_outcome_bet(self):
        """The one case with an independent answer: win `b` with prob `p`, lose 1 otherwise,
        gives f* = (p*b - (1-p)) / b. If the optimiser cannot hit that, nothing else it says
        is worth reading."""
        p, b = 0.6, 1.0
        rets = [b] * 600 + [-1.0] * 400
        closed = (p * b - (1 - p)) / b          # 0.20
        got = K.kelly_fraction(rets)["f_star"]
        self.assertAlmostEqual(got, closed, places=4)

    def test_it_reproduces_a_second_two_outcome_case_at_a_different_payoff(self):
        p, b = 0.35, 3.0
        rets = [b] * 350 + [-1.0] * 650
        closed = (p * b - (1 - p)) / b
        self.assertAlmostEqual(K.kelly_fraction(rets)["f_star"], closed, places=4)


class TheVectorisedGrowth(unittest.TestCase):
    def test_the_grid_form_equals_the_reference_form_at_every_point(self):
        """The optimiser calls the vectorised path, so it -- not the readable one -- decides
        every number reported. A fast path that merely approximated the registered statistic
        would move `f*` without anything saying so."""
        rng = random.Random(21)
        rets = [rng.gauss(0.05, 0.7) for _ in range(500)]
        fs = [0.001, 0.01, 0.05, 0.2, 0.5, 0.9]
        got = K.grid_growth(rets, fs)
        checked = 0
        for f, g in zip(fs, got):
            ref = K.growth(rets, f)
            if ref is None:
                # Both paths must agree that the fraction is out of range: the reference says
                # None, the vectorised one says -inf. Agreeing on the DOMAIN matters as much as
                # agreeing on the value -- a fast path that silently scored an undefined cell
                # could win the argmax.
                self.assertEqual(float(g), float("-inf"))
            else:
                self.assertAlmostEqual(float(g), ref, places=12)
                checked += 1
        self.assertGreaterEqual(checked, 3)

    def test_out_of_range_fractions_are_minus_infinity_not_an_exception(self):
        got = K.grid_growth([-0.5, 0.5], [0.5, 2.5])
        self.assertTrue(math.isfinite(float(got[0])))
        self.assertEqual(float(got[1]), float("-inf"))


class TheZeroEdgeCheck(unittest.TestCase):
    def test_a_zero_mean_distribution_gives_exactly_zero(self):
        """G'(0) = mean(R), so a non-positive mean admits no positive optimal fraction. This is
        the register's implementation check: if it ever returns non-zero here the optimiser is
        broken, not the world."""
        rng = random.Random(1)
        rets = [rng.gauss(0, 1) for _ in range(2000)]
        z = K.zero_edge(rets)
        self.assertAlmostEqual(sum(z) / len(z), 0.0, places=12)
        # Not `== 0.0`: shifting floats leaves a residual mean around 1e-18, which is positive
        # about half the time, and the optimiser then returns a fraction near 1e-30. The register
        # says "zero to GRID RESOLUTION", and the grid step is 0.0005 -- so that is what is
        # asserted. Demanding exact equality would make this test pass or fail on float luck.
        self.assertLess(K.kelly_fraction(z)["f_star"], 1e-6)
        self.assertLess(K.kelly_fraction(z)["f_star"], K.F_STEP)

    def test_a_negative_mean_distribution_gives_exactly_zero(self):
        self.assertEqual(K.kelly_fraction([-0.5, -0.4, 1.0, -0.9])["f_star"], 0.0)

    def test_zero_edge_shifts_the_mean_and_nothing_else(self):
        rets = [0.5, -0.2, 1.0]
        z = K.zero_edge(rets)
        self.assertAlmostEqual(max(z) - min(z), max(rets) - min(rets), places=12)


class TheHardBound(unittest.TestCase):
    def test_a_worse_than_total_loss_caps_leverage_below_one(self):
        """The book's worst trade is -101.44% -- a total loss plus commission, which is correct
        accounting. So log(1 + f*R) is undefined at and above f = 1/1.0144."""
        f = K.max_fraction([0.5, -1.0144, 0.2])
        self.assertLess(f, 1.0 / 1.0144)
        self.assertAlmostEqual(f, 1.0 / 1.0144, places=6)

    def test_growth_is_none_rather_than_a_crash_outside_the_defined_range(self):
        self.assertIsNone(K.growth([-1.0144, 0.5], 0.99))

    def test_f_star_never_exceeds_the_bound(self):
        rets = [5.0] * 900 + [-1.0144] * 100        # a huge edge still cannot exceed the bound
        out = K.kelly_fraction(rets)
        self.assertLess(out["f_star"], out["f_max"])

    def test_growth_at_zero_is_zero(self):
        self.assertEqual(K.growth([0.5, -0.5], 0.0), 0.0)


class MonthBlocks(unittest.TestCase):
    def test_blocks_are_calendar_months_and_move_together(self):
        rows = [{"alert_ts": "2020-01-%02d" % d, "pnl_pct": 0.1} for d in range(1, 6)]
        rows += [{"alert_ts": "2020-02-%02d" % d, "pnl_pct": -0.2} for d in range(1, 4)]
        b = K.month_blocks(rows)
        self.assertEqual(sorted(len(x) for x in b), [3, 5])

    def test_a_resample_returns_exactly_the_requested_length(self):
        b = [[0.1, 0.2], [0.3], [0.4, 0.5, 0.6]]
        self.assertEqual(len(K.block_resample(b, 10, random.Random(0))), 10)

    def test_resampling_is_seeded_and_reproducible(self):
        b = [[0.1, 0.2], [0.3], [0.4, 0.5, 0.6]]
        self.assertEqual(K.block_resample(b, 20, random.Random(3)),
                         K.block_resample(b, 20, random.Random(3)))

    def test_a_resample_only_ever_contains_real_returns(self):
        b = [[0.1, 0.2], [0.3]]
        got = set(K.block_resample(b, 30, random.Random(1)))
        self.assertTrue(got.issubset({0.1, 0.2, 0.3}))

    def test_rows_without_a_date_or_a_return_are_dropped_not_defaulted(self):
        rows = [{"alert_ts": "2020-01-01", "pnl_pct": 0.1},
                {"alert_ts": None, "pnl_pct": 0.5},
                {"alert_ts": "2020-01-02", "pnl_pct": None}]
        self.assertEqual(K.month_blocks(rows), [[0.1]])


class Ruin(unittest.TestCase):
    def test_a_larger_fraction_is_never_less_ruinous(self):
        """Monotonicity is the one property a ruin curve must have; if it fails, the path
        construction is wrong."""
        rng = random.Random(2)
        blocks = [[rng.gauss(0.03, 0.8) for _ in range(10)] for _ in range(30)]
        lo = K.ruin_profile(blocks, 0.05, 100, n_paths=300, seed=1)
        hi = K.ruin_profile(blocks, 0.40, 100, n_paths=300, seed=1)
        self.assertLessEqual(lo["p_drawdown_over_50"], hi["p_drawdown_over_50"])

    def test_a_zero_drawdown_book_never_reports_ruin(self):
        blocks = [[0.10] * 5 for _ in range(5)]      # every trade wins
        out = K.ruin_profile(blocks, 0.5, 50, n_paths=50, seed=0)
        self.assertEqual(out["p_drawdown_over_50"], 0.0)
        self.assertGreater(out["median_terminal"], 1.0)

    def test_fractional_betting_decays_but_never_literally_ruins(self):
        """WHY RUIN IS DEFINED ON THRESHOLDS AND NOT ON "equity hits zero".

        At any fraction below the hard bound, a total-loss trade multiplies wealth by (1 - f),
        which is strictly positive. So an all-losses path decays geometrically toward zero and
        NEVER reaches it: after 10 total losses at f = 0.999, terminal wealth is 1e-30, not 0.
        Literal ruin is unreachable by construction, which is precisely why the register fixed
        threshold metrics (`< 0.2x`, drawdown `> 80%`) instead of a bankruptcy count. A ruin
        study that counted zeroes here would report that this book can never be ruined.
        """
        blocks = [[-1.0] * 3]
        out = K.ruin_profile(blocks, 0.999, 10, n_paths=20, seed=0)
        self.assertGreater(out["median_terminal"], 0.0)
        self.assertLess(out["median_terminal"], 1e-20)
        self.assertAlmostEqual(out["median_max_drawdown"], 1.0, places=12)
        self.assertEqual(out["p_terminal_below_0.2x"], 1.0)
        self.assertEqual(out["p_drawdown_over_80"], 1.0)

    def test_the_concurrency_caveat_ships_in_the_payload(self):
        """The live book holds several positions at once, so sequential compounding UNDERSTATES
        its drawdown. That has to travel with the number, not sit in a handoff."""
        out = K.ruin_profile([[0.1, -0.1]], 0.1, 10, n_paths=10, seed=0)
        self.assertIn("concurrency_caveat", out)
        self.assertIn("floor", out["concurrency_caveat"])

    def test_the_registered_thresholds_are_the_ones_reported(self):
        out = K.ruin_profile([[0.1, -0.1]], 0.1, 10, n_paths=10, seed=0)
        for t in ("p_terminal_below_0.5x", "p_terminal_below_0.2x",
                  "p_drawdown_over_50", "p_drawdown_over_80"):
            self.assertIn(t, out)


class FlatSizing(unittest.TestCase):
    def test_implied_fraction_is_contracts_times_100_times_premium_over_equity(self):
        self.assertAlmostEqual(K.implied_fraction(5.0, 1, 10000), 0.05, places=12)

    def test_the_equity_inversion_round_trips(self):
        eq = K.equity_for_fraction(5.0, 1, 0.05)
        self.assertAlmostEqual(K.implied_fraction(5.0, 1, eq), 0.05, places=12)

    def test_a_zero_or_missing_equity_is_none_not_a_division_error(self):
        self.assertIsNone(K.implied_fraction(5.0, 1, 0))
        self.assertIsNone(K.equity_for_fraction(5.0, 1, 0))


class Bootstrap(unittest.TestCase):
    def test_the_ci_is_ordered_and_seeded(self):
        rng = random.Random(5)
        blocks = [[rng.gauss(0.05, 0.6) for _ in range(8)] for _ in range(24)]
        a = K.bootstrap_f_star(blocks, 192, n_draws=40, seed=2)
        b = K.bootstrap_f_star(blocks, 192, n_draws=40, seed=2)
        self.assertEqual(a, b)
        self.assertLessEqual(a["p2_5"], a["p50"])
        self.assertLessEqual(a["p50"], a["p97_5"])

    def test_it_reoptimises_f_on_every_draw(self):
        """Reusing the point estimate's fraction on a resample would measure the wrong thing --
        the spread of growth at a fixed f, not the spread of the optimum."""
        import inspect
        src = inspect.getsource(K.bootstrap_f_star)
        self.assertIn("kelly_fraction(s)", src)


class TheRegisterIsHonoured(unittest.TestCase):
    def test_the_grid_and_thresholds_are_the_registered_ones(self):
        self.assertEqual(K.F_MIN, 0.0005)
        self.assertEqual(K.F_STEP, 0.0005)
        self.assertEqual(K.RUIN_TERMINAL, (0.5, 0.2))
        self.assertEqual(K.RUIN_DRAWDOWN, (0.5, 0.8))

    def test_the_module_carries_the_dead_edge_caveat(self):
        """Kelly needs a real edge and R2 says this one is dead. That belongs in the module."""
        self.assertIn("R2", K.__doc__)
        self.assertIn("dead", K.__doc__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
