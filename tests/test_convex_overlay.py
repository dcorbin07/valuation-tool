"""Tests for U3 (PREREG_u3_convex_overlay.md).

The load-bearing ones are:

(a) `max_drawdown` is NEGATIVE and a gain is `arm - base`. Pinned with S10's REAL measured pair
    (-0.2809 base, -0.2863 arm), because that is the pair on which a previous session's first
    cut reported a worsening as an improvement.
(b) `combine` at X=100 reproduces the equity book EXACTLY, not to within a tolerance. C8: a
    sweep whose endpoint does not reproduce its own baseline is measuring something else.
(c) A POSITIVE conditional correlation reads as "not insurance". The intuitive reading of a high
    correlation as a good thing is backwards for a hedge, and the payload must say so in words.
(d) Costs may only make an arm WEAKLY WORSE. A cost model that improves an arm is a bug.
(e) `top = alpha + equal_weight` is an identity of the SHIPPED code, verified against
    `fundamental_panel.quantile_backtest` itself rather than against a second copy of it.
(f) The Sharpe guard is an explicit tolerance, NOT `if sd > 0` — the U2 / SECTOR-NEUTRAL-B6
    value-dependent zero-variance defect must not be reproduced in a third location.
"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import convex_overlay as CO  # noqa: E402


# --------------------------------------------------------------------------- #
#  (a) the drawdown sign — S10's defect, pinned with S10's own numbers
# --------------------------------------------------------------------------- #
class TestDrawdownSign(unittest.TestCase):
    def test_max_drawdown_is_negative(self):
        self.assertLess(CO.max_drawdown([0.1, -0.5, 0.2]), 0.0)

    def test_a_series_that_never_falls_has_zero_drawdown(self):
        self.assertAlmostEqual(CO.max_drawdown([0.01, 0.02, 0.03]), 0.0, places=12)

    def test_S10s_real_measured_pair_is_a_WORSENING_not_an_improvement(self):
        """base -0.2809, arm -0.2863. The arm is MORE negative, so it is WORSE.

        S10's first cut computed `base - arm` and reported this exact pair as a 2.61pp
        improvement when it is a worsening. The gain is `arm - base`.
        """
        base, arm = -0.2809, -0.2863
        gain = arm - base
        self.assertLess(gain, 0.0, "arm - base must be NEGATIVE for a deeper drawdown")
        self.assertAlmostEqual(gain, -0.0054, places=6)
        # and the inverted convention would have called it a gain
        self.assertGreater(base - arm, 0.0)

    def test_a_deeper_drawdown_compares_as_worse_through_the_shipped_helper(self):
        shallow = CO.max_drawdown([0.05, -0.10, 0.05])
        deep = CO.max_drawdown([0.05, -0.40, 0.05])
        self.assertGreater(shallow - deep, 0.0, "shallow must beat deep under arm - base")


class TestDrawdownEpisodes(unittest.TestCase):
    def test_one_crash_counts_once(self):
        r = [0.02] * 5 + [-0.30] + [0.05] * 10
        self.assertEqual(CO.drawdown_episodes(r), 1)

    def test_two_separated_crashes_count_twice(self):
        r = [0.02] * 3 + [-0.30] + [0.30] * 4 + [0.05] * 3 + [-0.25] + [0.05] * 3
        self.assertGreaterEqual(CO.drawdown_episodes(r), 2)

    def test_a_flat_series_has_no_episode(self):
        self.assertEqual(CO.drawdown_episodes([0.0] * 10), 0)


# --------------------------------------------------------------------------- #
#  (b) C8 — the sweep endpoint must reproduce its own baseline EXACTLY
# --------------------------------------------------------------------------- #
class TestCombineEndpoint(unittest.TestCase):
    def test_x100_is_the_equity_book_EXACTLY(self):
        eq = [0.031, -0.017, 0.223, -0.0004]
        sl = [1.5, -0.9, 0.4, -0.77]
        out = CO.combine(eq, sl, 100)
        for a, b in zip(out, eq):
            self.assertEqual(a, b, "X=100 must be exact, not merely close")

    def test_x100_is_exact_even_when_the_sleeve_is_missing(self):
        out = CO.combine([0.01, 0.02], [np.nan, np.nan], 100)
        self.assertEqual(out, [0.01, 0.02])

    def test_below_100_the_sleeve_actually_enters(self):
        out = CO.combine([0.0, 0.0], [1.0, 1.0], 95)
        self.assertAlmostEqual(out[0], 0.05, places=12)

    def test_an_out_of_range_weight_raises(self):
        with self.assertRaises(CO.RegisterViolation):
            CO.combine([0.01], [0.02], 101)

    def test_a_missing_sleeve_quarter_does_not_silently_become_zero(self):
        out = CO.combine([0.10], [np.nan], 95)
        self.assertTrue(np.isnan(out[0]), "a missing sleeve mark must not read as a flat sleeve")


# --------------------------------------------------------------------------- #
#  (c) the correlation sign convention — backwards for a hedge
# --------------------------------------------------------------------------- #
class TestInsuranceReading(unittest.TestCase):
    def _run(self, sleeve):
        eq = [-0.30, -0.10, 0.02, 0.08, 0.15, -0.05, 0.11, 0.03]
        return CO.arm_a2(eq, sleeve, [0.3] * 8)

    def test_a_positive_correlation_is_NOT_insurance(self):
        r = self._run([-0.60, -0.20, 0.05, 0.15, 0.30, -0.10, 0.22, 0.06])
        self.assertGreater(r["correlation_unconditional"], 0.0)
        self.assertFalse(r["is_insurance"])
        self.assertIn("NOT insurance", r["reading"])

    def test_a_negative_correlation_IS_consistent_with_insurance(self):
        r = self._run([0.60, 0.20, -0.05, -0.15, -0.30, 0.10, -0.22, -0.06])
        self.assertLess(r["correlation_unconditional"], 0.0)
        self.assertTrue(r["is_insurance"])

    def test_even_a_negative_correlation_does_not_claim_the_benefit_is_measured(self):
        r = self._run([0.60, 0.20, -0.05, -0.15, -0.30, 0.10, -0.22, -0.06])
        self.assertIn("rests on the crash count", r["reading"])

    def test_the_return_conditioned_split_is_LABELLED_as_such(self):
        r = self._run([-0.6, -0.2, 0.05, 0.15, 0.3, -0.1, 0.22, 0.06])
        self.assertIn("correlation_equity_worst_decile_RETURN_CONDITIONED", r)
        self.assertIn("correlation_high_iv", r)

    def test_the_worst_decile_selects_the_equity_books_worst_quarters(self):
        r = self._run([-0.6, -0.2, 0.05, 0.15, 0.3, -0.1, 0.22, 0.06])
        self.assertLess(r["equity_mean_worst_decile"], 0.0)


# --------------------------------------------------------------------------- #
#  (d) C5 — costs may only make an arm weakly worse
# --------------------------------------------------------------------------- #
class TestCostsOnlyHurt(unittest.TestCase):
    def test_round_trip_cost_rises_with_rho(self):
        self.assertLess(CO._round_trip_cost(0.04, 0.6743), CO._round_trip_cost(0.04, 1.0))

    def test_round_trip_cost_is_never_negative(self):
        self.assertGreaterEqual(CO._round_trip_cost(-0.5, 1.0), 0.0)
        self.assertGreaterEqual(CO._round_trip_cost(float("nan"), 1.0), 0.0)

    def test_rho_is_O18s_MEASURED_ratio_not_an_assumption(self):
        self.assertAlmostEqual(CO.COST_RHO, 0.6743, places=6)
        self.assertGreater(CO.COST_RHO, 0.6617)   # O18 CI95 low
        self.assertLess(CO.COST_RHO, 0.6871)      # O18 CI95 high

    def test_a_wider_spread_costs_more(self):
        self.assertLess(CO._round_trip_cost(0.01, 0.6743), CO._round_trip_cost(0.09, 0.6743))


# --------------------------------------------------------------------------- #
#  (e) the identity, verified against the SHIPPED quantile_backtest
# --------------------------------------------------------------------------- #
class TestTopDecileIdentity(unittest.TestCase):
    def test_top_equals_alpha_plus_equal_weight_on_a_real_quantile_backtest(self):
        from valuation.edge import fundamental_panel as FP
        rng = np.random.default_rng(11)
        rows = []
        for di in range(12):
            for ni in range(60):
                rows.append({"date": pd.Timestamp("2015-01-01") + pd.Timedelta(days=63 * di),
                             "ticker": f"T{ni:03d}",
                             "value": float(rng.normal()),
                             "fwd_ret": float(rng.normal(0.01, 0.08))})
        panel = pd.DataFrame(rows)
        qb = FP.quantile_backtest(panel, ["value"], {"value": 1.0}, n_q=10, horizon=63,
                                  return_series=True)
        self.assertIn("series", qb)
        self.assertIn("equal_weight", qb["series"],
                      "the U3 addition must be present in the shipped payload")
        df = CO.top_decile_series(qb)
        # the identity, against the shipped arithmetic rather than a second copy of it
        for a, e, t in zip(qb["series"]["alpha"], qb["series"]["equal_weight"], df["top"]):
            self.assertAlmostEqual(a + e, t, places=12)

    def test_the_addition_is_gated_and_does_not_change_a_default_payload(self):
        from valuation.edge import fundamental_panel as FP
        rng = np.random.default_rng(12)
        rows = []
        for di in range(12):
            for ni in range(60):
                rows.append({"date": pd.Timestamp("2015-01-01") + pd.Timedelta(days=63 * di),
                             "ticker": f"T{ni:03d}", "value": float(rng.normal()),
                             "fwd_ret": float(rng.normal(0.01, 0.08))})
        panel = pd.DataFrame(rows)
        qb = FP.quantile_backtest(panel, ["value"], {"value": 1.0}, n_q=10, horizon=63)
        self.assertNotIn("series", qb, "return_series=False must carry no series at all")

    def test_a_payload_without_return_series_raises_rather_than_guessing(self):
        with self.assertRaises(CO.RegisterViolation):
            CO.top_decile_series({"n_periods": 4})

    def test_a_payload_from_an_older_build_raises_rather_than_reconstructing(self):
        stale = {"series": {"dates": ["2015-01-01"], "alpha": [0.01], "long_short": [0.02],
                            "n_scored": [100]}}
        with self.assertRaises(CO.RegisterViolation):
            CO.top_decile_series(stale)


# --------------------------------------------------------------------------- #
#  (f) the zero-variance guard must NOT be the value-dependent `if sd > 0`
# --------------------------------------------------------------------------- #
class TestDegenerateGuard(unittest.TestCase):
    def test_a_constant_series_returns_None_not_an_absurd_sharpe(self):
        """`[0.1, 0.1, 0.1]` has floating-point sd ~5.8e-17, so `if sd > 0` PASSES on it.

        That is the SECTOR-NEUTRAL-B6 defect, found again in `theme_ic` by U2. It must not
        appear a third time here.
        """
        self.assertIsNotNone(np.std([0.1, 0.1, 0.1], ddof=1))
        self.assertIsNone(CO.sharpe([0.1, 0.1, 0.1]))
        self.assertIsNone(CO.sharpe([0.9] * 8))
        self.assertIsNone(CO.sharpe([1.0 / 3.0] * 5))

    def test_a_real_series_still_returns_a_number(self):
        self.assertIsNotNone(CO.sharpe([0.05, -0.02, 0.08, 0.01, -0.04]))

    def test_too_short_a_series_returns_None(self):
        self.assertIsNone(CO.sharpe([0.05]))


# --------------------------------------------------------------------------- #
#  the halves guard and the concurrency cap
# --------------------------------------------------------------------------- #
class TestHalves(unittest.TestCase):
    def test_forty_quarters_split_20_and_19_with_the_boundary_embargoed(self):
        e, l, b = CO.halves(40)
        self.assertEqual(len(e), 20)
        self.assertEqual(len(l), 19)
        self.assertNotIn(b, e)
        self.assertNotIn(b, l)

    def test_a_thin_split_RAISES_rather_than_quietly_returning_one(self):
        with self.assertRaises(CO.RegisterViolation):
            CO.halves(30)

    def test_the_floor_is_the_shipped_min_dates(self):
        self.assertEqual(CO.MIN_DATES, 16)


class TestSleeveCurve(unittest.TestCase):
    def _fixture(self, n_trades, cap):
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        marks, rows = {}, []
        for i in range(n_trades):
            entry = dates[i * 2]
            seq = [(d, 5.0 + 0.1 * j) for j, d in enumerate(dates[i * 2:i * 2 + 20])]
            marks[(f"T{i}", str(entry.date()), "2020-12-31", 100.0)] = seq
            rows.append({"ticker": f"T{i}", "alert_ts": str(entry.date()),
                         "entry_spread_pct": 0.04})
        book = pd.DataFrame(rows)
        bd = [dates[0], dates[60], dates[120], dates[180]]
        return CO.sleeve_curve(book, marks, bd, cap=cap)

    def test_a_full_book_refuses_trades_at_the_cap(self):
        tight = self._fixture(20, cap=2)
        loose = self._fixture(20, cap=20)
        self.assertGreater(tight.attrs["refused"], 0)
        self.assertEqual(loose.attrs["refused"], 0)

    def test_the_cap_is_recorded_on_the_result(self):
        self.assertEqual(self._fixture(6, cap=3).attrs["cap"], 3)

    def test_a_zero_cap_raises(self):
        with self.assertRaises(CO.RegisterViolation):
            self._fixture(4, cap=0)

    def test_costs_make_the_sleeve_weakly_worse(self):
        dates = pd.date_range("2020-01-01", periods=60, freq="B")
        marks = {("A", "2020-01-01", "2020-06-30", 100.0):
                 [(d, 5.0 + 0.05 * j) for j, d in enumerate(dates[:40])]}
        book = pd.DataFrame([{"ticker": "A", "alert_ts": "2020-01-01",
                              "entry_spread_pct": 0.10}])
        bd = [dates[0], dates[50]]
        cheap = CO.sleeve_curve(book, marks, bd, cap=1, rho=0.0)
        dear = CO.sleeve_curve(book, marks, bd, cap=1, rho=1.0)
        self.assertLessEqual(dear["sleeve"].iloc[0], cheap["sleeve"].iloc[0] + 1e-12)


# --------------------------------------------------------------------------- #
#  A1's verdict rule
# --------------------------------------------------------------------------- #
class TestA1Verdict(unittest.TestCase):
    def _series(self, n=41):
        rng = np.random.default_rng(7)
        return list(rng.normal(0.02, 0.06, n)), list(rng.normal(0.03, 0.35, n))

    def test_a_sleeve_that_helps_in_only_one_half_is_REJECTED(self):
        eq, _ = self._series()
        sl = [(-3.0 * e if i < 20 else 3.0 * e) for i, e in enumerate(eq)]
        e_idx, l_idx, _ = CO.halves(len(eq))
        r = CO.arm_a1(eq, sl, e_idx, l_idx)
        self.assertEqual(r["verdict"], "REJECTED")

    def test_a_clearing_arm_is_ELIGIBLE_BUT_UNRESOLVED_and_never_ADOPTED(self):
        eq, _ = self._series()
        sl = [-4.0 * e for e in eq]          # a genuine hedge, by construction
        e_idx, l_idx, _ = CO.halves(len(eq))
        r = CO.arm_a1(eq, sl, e_idx, l_idx)
        if r["x_clearing_both_halves"]:
            self.assertEqual(r["verdict"], "ELIGIBLE-BUT-UNRESOLVED")
            self.assertNotEqual(r["verdict"], "ADOPTED")
            self.assertIn("ONE drawdown episode", r["unresolved_note"])

    def test_the_bar_is_labelled_UNCALIBRATED(self):
        eq, sl = self._series()
        e_idx, l_idx, _ = CO.halves(len(eq))
        r = CO.arm_a1(eq, sl, e_idx, l_idx)
        self.assertFalse(r["bar_calibrated"])
        self.assertIn("X7 calibrates NO floor", r["bar_note"])

    def test_the_whole_grid_is_reported_not_only_the_winner(self):
        eq, sl = self._series()
        e_idx, l_idx, _ = CO.halves(len(eq))
        r = CO.arm_a1(eq, sl, e_idx, l_idx)
        self.assertEqual(len(r["cells"]["full"]), len(CO.X_GRID))
        self.assertEqual(tuple(sorted(r["cells"]["full"])), CO.X_GRID)

    def test_improving_sharpe_ALONE_does_not_clear(self):
        """The audit is explicit: a sleeve that improves Sharpe by raising RETURN is not doing
        the job it is hired for. Both legs must hold."""
        eq = [0.01] * 10 + [0.02] * 10 + [0.015] * 21
        sl = [0.5] * 41                       # pure return, zero extra risk, no hedge
        e_idx, l_idx, _ = CO.halves(len(eq))
        r = CO.arm_a1(eq, sl, e_idx, l_idx)
        self.assertEqual(r["verdict"], "REJECTED",
                         "a return-adding sleeve with no drawdown benefit must not clear")


class TestRegisterConstants(unittest.TestCase):
    def test_the_x_grid_is_the_audits_own(self):
        self.assertEqual(CO.X_GRID, (90, 91, 92, 93, 94, 95, 96, 97, 98, 99))

    def test_both_O11_caps_are_carried(self):
        self.assertEqual(CO.CONCURRENCY_CAPS, (10, 50))

    def test_the_record_the_harness_must_reproduce_is_the_published_one(self):
        self.assertAlmostEqual(CO.RECORD["top_decile_alpha"], 0.071741, places=6)
        self.assertAlmostEqual(CO.RECORD["equal_weight_ann"], 0.181371, places=6)
        self.assertAlmostEqual(CO.BOOK_MEAN_PNL, 0.032702, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
