"""O3 + O4 + O5 — pins the delta-hedged instrument and the cross-sectional sort.

Standalone script, like every suite here.

THE LOAD-BEARING ONES:
  * `test_the_published_signs_are_declared_and_pinned` — the whole point of declaring signs first
    is that they cannot move after the sort is seen.
  * `test_a_flat_underlying_loses_theta` and `test_a_hedged_call_beats_an_unhedged_one_on_a_trend`
    — the instrument must actually be delta-hedged. An unhedged call on a trending underlying
    makes money for a reason that has nothing to do with the surface.
  * `test_carrying_the_last_delta_is_not_the_same_as_dropping_it` — the terminal-day treatment is
    a registered choice; dropping the hedge leaves the position unhedged over the final move.
  * `test_quintiles_are_assigned_within_date_not_pooled` — a pooled sort compares across regimes
    and is not a cross-section.
  * `test_a_sign_reversed_clear_is_not_a_candidate` — an arm that works backwards is not a find.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np                                    # noqa: E402
from valuation.edge import surface_xsec as SX         # noqa: E402


def mkdays(spots, marks, deltas, dt_=1 / 365.0, entry=None, exit_=None):
    n = len(spots)
    out = []
    for i in range(n):
        out.append({"s": float(spots[i]), "mark": float(marks[i]),
                    "delta": (None if deltas[i] is None else float(deltas[i])),
                    "dt": dt_})
    if entry is not None:
        out[0]["entry_px"] = entry
    if exit_ is not None:
        out[-1]["exit_px"] = exit_
    return out


class TestSigns(unittest.TestCase):
    def test_the_published_signs_are_declared_and_pinned(self):
        self.assertEqual(SX.PUBLISHED_SIGNS,
                         {"idio_vol": +1, "exp_idio_skew": +1, "vol_of_vol": +1})
        self.assertEqual(SX.ARMS, ("idio_vol", "exp_idio_skew", "vol_of_vol"))

    def test_the_registered_constants_match_the_register(self):
        self.assertEqual((SX.DTE_LO, SX.DTE_HI), (20, 45))
        self.assertEqual(SX.DIV_YIELD, 0.0)
        self.assertEqual(SX.HEDGE_BPS, 5.0)
        self.assertEqual(SX.MIN_HEDGE_DAYS, 10)
        self.assertEqual(SX.MONO_BAR, 0.6)
        self.assertEqual(SX.N_PERM_DRAWS, 2000)
        self.assertEqual(SX.SEED, 20260812)
        self.assertEqual((SX.MIN_NAMES_PER_DATE, SX.MIN_DATES), (15, 50))


class TestInstrument(unittest.TestCase):
    def test_a_flat_underlying_loses_theta(self):
        n = 15
        spots = [100.0] * n
        marks = [5.0 - 0.1 * i for i in range(n)]      # pure decay
        deltas = [0.5] * n
        r = SX.delta_hedged_return(mkdays(spots, marks, deltas), hedge_bps=0.0)
        self.assertIsNotNone(r)
        self.assertLess(r["dh"], 0.0, "a decaying option on a flat underlying must lose")

    def test_a_hedged_call_beats_an_unhedged_one_on_a_trend(self):
        """A rising underlying makes an UNHEDGED call look brilliant. The hedge must remove it."""
        n = 15
        spots = [100.0 + i for i in range(n)]
        deltas = [0.5] * n
        marks = [5.0 + 0.5 * i for i in range(n)]      # option tracks delta*move
        # rate=0 isolates the hedge mechanics from the financing term, which is tested separately.
        r = SX.delta_hedged_return(mkdays(spots, marks, deltas), hedge_bps=0.0, rate=0.0)
        unhedged = (marks[-1] - marks[0]) / abs(deltas[0] * spots[0] - marks[0])
        self.assertIsNotNone(r)
        self.assertGreater(unhedged, 0.05)
        self.assertLess(abs(r["dh"]), abs(unhedged),
                        "the hedge must remove the directional component")
        self.assertAlmostEqual(r["dh"], 0.0, places=6)

    def test_carrying_the_last_delta_is_not_the_same_as_dropping_it(self):
        n = 14
        spots = [100.0] * (n - 1) + [110.0]            # the whole move is on the last step
        marks = [5.0] * (n - 1) + [10.0]
        deltas = [0.5] * (n - 1) + [None]              # terminal day unsolvable
        r = SX.delta_hedged_return(mkdays(spots, marks, deltas), hedge_bps=0.0, rate=0.0)
        self.assertIsNotNone(r)
        # carried: pi = (10-5) - 0.5*(110-100) = 0. Dropping the hedge would leave +5.
        self.assertAlmostEqual(r["pi"], 0.0, places=6)

    def test_the_financing_term_is_charged_and_is_signed_correctly(self):
        """A long call financed at r: the position (C - Delta*S) is NEGATIVE for a call whose
        delta*S exceeds its premium, so financing that short stock position EARNS carry. The
        formula subtracts r*(C - Delta*S)*dt, so the gain must RISE with the rate here."""
        n = 15
        days = mkdays([100.0] * n, [5.0] * n, [0.5] * n)
        lo = SX.delta_hedged_return(days, hedge_bps=0.0, rate=0.0)
        hi = SX.delta_hedged_return(days, hedge_bps=0.0, rate=0.05)
        self.assertGreater(hi["pi"], lo["pi"])

    def test_an_event_with_too_few_solvable_days_is_refused(self):
        n = 12
        deltas = [0.5] * 3 + [None] * (n - 3)          # only 3 solvable
        r = SX.delta_hedged_return(mkdays([100.0] * n, [5.0] * n, deltas))
        self.assertIsNone(r)

    def test_the_hedge_charge_can_only_hurt(self):
        n = 15
        spots = [100.0 + (i % 3) for i in range(n)]
        marks = [5.0] * n
        deltas = [0.5] * n
        free = SX.delta_hedged_return(mkdays(spots, marks, deltas), hedge_bps=0.0)
        paid = SX.delta_hedged_return(mkdays(spots, marks, deltas), hedge_bps=5.0)
        self.assertLess(paid["dh"], free["dh"])
        self.assertGreater(paid["hedge_cost"], 0.0)

    def test_crossing_the_spread_at_the_ends_lowers_the_return(self):
        n = 15
        days_mid = mkdays([100.0] * n, [5.0] * n, [0.5] * n)
        days_cross = mkdays([100.0] * n, [5.0] * n, [0.5] * n, entry=5.10, exit_=4.90)
        a = SX.delta_hedged_return(days_mid, hedge_bps=0.0)
        b = SX.delta_hedged_return(days_cross, hedge_bps=0.0)
        self.assertLess(b["pi"], a["pi"])


class TestSort(unittest.TestCase):
    def test_quintiles_are_assigned_within_date_not_pooled(self):
        # date A values are all below date B's; a pooled sort would put all of A in Q1.
        vals = list(range(10)) + list(range(100, 110))
        dates = ["2020-01-31"] * 10 + ["2020-02-28"] * 10
        lb = SX.quintiles_within_date(vals, dates)
        self.assertEqual(sorted(set(lb[:10])), [0, 1, 2, 3, 4])
        self.assertEqual(sorted(set(lb[10:])), [0, 1, 2, 3, 4])

    def test_a_date_with_too_few_names_is_dropped(self):
        lb = SX.quintiles_within_date([1.0, 2.0, 3.0], ["d"] * 3)
        self.assertTrue((lb == -1).all())

    def test_long_short_is_q1_minus_q5(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        dates = ["d"] * 5
        lb = SX.quintiles_within_date(vals, dates)
        rets = [10.0, 0.0, 0.0, 0.0, 2.0]
        days, ls, q = SX.long_short_series(rets, lb, dates)
        self.assertEqual(len(ls), 1)
        self.assertAlmostEqual(ls[0], 8.0, places=9)

    def test_monotonicity_is_negative_when_returns_fall_with_the_characteristic(self):
        q = np.array([[5.0, 4.0, 3.0, 2.0, 1.0]])
        self.assertAlmostEqual(SX.monotonicity(q), -1.0, places=9)
        q2 = np.array([[1.0, 2.0, 3.0, 4.0, 5.0]])
        self.assertAlmostEqual(SX.monotonicity(q2), +1.0, places=9)


class TestNullAndBootstrap(unittest.TestCase):
    def test_the_permutation_null_holds_returns_and_bin_sizes_fixed(self):
        rng = np.random.default_rng(3)
        n = 200
        rets = rng.normal(size=n)
        dates = np.repeat(["2020-01-31", "2020-02-28", "2020-03-31", "2020-04-30"], n // 4)
        vals = rng.normal(size=n)
        lb = SX.quintiles_within_date(vals, dates)
        before = np.sort(rets.copy())
        sizes = sorted(int((lb == j).sum()) for j in range(5))
        SX.perm_null_ls_t(rets, lb, dates, draws=8, seed=1)
        self.assertTrue(np.allclose(np.sort(rets), before))
        self.assertEqual(sorted(int((lb == j).sum()) for j in range(5)), sizes)

    def test_the_bootstrap_resamples_months(self):
        ls = np.array([0.0] * 10 + [10.0] * 10)
        days = ["2020-01-%02d" % (i + 1) for i in range(10)] + \
               ["2020-02-%02d" % (i + 1) for i in range(10)]
        r = SX.month_block_t(ls, days, draws=400, seed=2)
        self.assertEqual(r["n_blocks"], 2)
        self.assertAlmostEqual(r["mean"], 5.0, places=9)


class TestVerdict(unittest.TestCase):
    def test_a_confirming_arm_in_both_halves_is_a_candidate(self):
        v = SX.arm_verdict(-0.9, 3.0, 2.0, +0.02,
                           -0.8, 3.1, 2.0, +0.03, sign=+1)
        self.assertEqual(v, "CANDIDATE")

    def test_one_half_failing_is_a_null(self):
        v = SX.arm_verdict(-0.9, 3.0, 2.0, +0.02,
                           -0.1, 3.1, 2.0, +0.03, sign=+1)
        self.assertEqual(v, "NULL")

    def test_a_sign_reversed_clear_is_not_a_candidate(self):
        v = SX.arm_verdict(+0.9, 3.0, 2.0, -0.02,
                           +0.8, 3.1, 2.0, -0.03, sign=+1)
        self.assertEqual(v, "CONTRADICTS-PUBLISHED-SIGN")

    def test_failing_the_calibrated_bar_is_a_null_even_when_monotone(self):
        v = SX.arm_verdict(-0.95, 1.0, 2.0, +0.02,
                           -0.95, 1.1, 2.0, +0.03, sign=+1)
        self.assertEqual(v, "NULL")

    def test_a_missing_half_is_a_null(self):
        self.assertEqual(SX.arm_verdict(None, 3.0, 2.0, 0.02,
                                        -0.8, 3.0, 2.0, 0.02), "NULL")


class TestExpectedSkew(unittest.TestCase):
    def test_the_fit_recovers_a_planted_relationship(self):
        rng = np.random.default_rng(5)
        train = []
        for _ in range(300):
            s, v, m = rng.normal(), abs(rng.normal()) + 0.1, rng.normal()
            train.append({"idio_skew": s, "idio_vol": v, "mom6": m,
                          "target": 2.0 + 0.5 * s - 0.3 * v + 0.1 * m})
        beta = SX.fit_expected_skew(train)
        self.assertIsNotNone(beta)
        self.assertAlmostEqual(beta[1], 0.5, places=4)
        self.assertAlmostEqual(beta[2], -0.3, places=4)

    def test_too_little_training_data_returns_none_rather_than_a_fit(self):
        self.assertIsNone(SX.fit_expected_skew(
            [{"idio_skew": 1.0, "idio_vol": 1.0, "mom6": 0.0, "target": 1.0}] * 5))

    def test_prediction_refuses_a_row_with_a_missing_predictor(self):
        beta = np.array([1.0, 1.0, 1.0, 1.0])
        self.assertIsNone(SX.predict_expected_skew(beta, {"idio_skew": None,
                                                          "idio_vol": 1.0, "mom6": 0.0}))


class TestVolOfVol(unittest.TestCase):
    def test_a_constant_iv_series_has_zero_vol_of_vol(self):
        s = {"2020-01-%02d" % (i + 1) for i in range(30)}
        iv = {d: 0.30 for d in s}
        self.assertAlmostEqual(SX.vol_of_vol_from_series(iv, "2020-02-01"), 0.0, places=12)

    def test_it_never_reads_on_or_after_the_formation_date(self):
        iv = {"2020-01-%02d" % (i + 1) for i in range(25)}
        iv = {d: 0.30 for d in iv}
        iv["2020-01-25"] = 99.0                      # a spike ON the formation date
        v = SX.vol_of_vol_from_series(iv, "2020-01-25")
        self.assertAlmostEqual(v, 0.0, places=12)

    def test_too_few_observations_returns_none(self):
        iv = {"2020-01-0%d" % (i + 1) for i in range(5)}
        iv = {d: 0.3 for d in iv}
        self.assertIsNone(SX.vol_of_vol_from_series(iv, "2020-02-01"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
