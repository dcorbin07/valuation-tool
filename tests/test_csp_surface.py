"""Tests for V6-OPT's post-dip surface instrument (`valuation/edge/csp_surface.py`).

Every convention this project has previously got wrong is pinned here with a REAL measured
pair where one exists, so a regression fails against history rather than against a toy.
"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import csp_surface as CS  # noqa: E402
from valuation.edge.options_fill import Quote, fill_price  # noqa: E402


def _daily(dates, iv, col="atm_iv_30"):
    return pd.DataFrame({"date": pd.to_datetime(dates), col: iv})


class TestPointInTime(unittest.TestCase):
    def test_as_of_takes_the_last_row_on_or_before_and_never_after(self):
        d = _daily(["2020-01-02", "2020-01-06", "2020-01-08"], [0.30, 0.40, 0.50])
        self.assertAlmostEqual(float(CS.as_of(d, "2020-01-06")["atm_iv_30"]), 0.40)
        # a date the market was shut: takes the PRIOR row, never the next one
        self.assertAlmostEqual(float(CS.as_of(d, "2020-01-07")["atm_iv_30"]), 0.40)

    def test_as_of_returns_None_before_the_series_starts(self):
        d = _daily(["2020-01-02", "2020-01-06"], [0.30, 0.40])
        self.assertIsNone(CS.as_of(d, "2019-12-31"))

    def test_baseline_is_STRICTLY_before_and_excludes_the_dip_day_itself(self):
        # 60 quiet days then one huge spike ON the observation date.
        dates = pd.bdate_range("2020-01-01", periods=61)
        iv = [0.20] * 60 + [5.00]
        d = _daily(dates, iv)
        b = CS.baseline(d, dates[-1], min_obs=60)
        # If the spike leaked in, the median would move off 0.20.
        self.assertAlmostEqual(b, 0.20, places=9)

    def test_forward_path_starts_STRICTLY_after_the_observation_date(self):
        dates = pd.bdate_range("2020-01-01", periods=10)
        d = _daily(dates, [float(i) for i in range(10)])
        p = CS.forward_path(d, dates[3], n=3)
        self.assertEqual(p, [4.0, 5.0, 6.0])

    def test_a_short_forward_path_is_padded_with_None_not_silently_shortened(self):
        dates = pd.bdate_range("2020-01-01", periods=5)
        d = _daily(dates, [1.0, 2.0, 3.0, 4.0, 5.0])
        p = CS.forward_path(d, dates[3], n=4)
        self.assertEqual(len(p), 4)
        self.assertEqual(p[0], 5.0)
        self.assertTrue(all(x is None for x in p[1:]))


class TestGuardsCarryTolerances(unittest.TestCase):
    def test_a_constant_series_does_not_produce_an_absurd_statistic(self):
        # `[0.1]*n` has a floating-point sd of ~5.8e-17, so `if sd > 0` PASSES on it.
        # That is the SECTOR-NEUTRAL-B6 defect and U2 met it again in theme_ic.
        s = CS.summarise([0.1] * 25)
        self.assertEqual(s["sd"], 0.0)

    def test_realised_vol_on_a_flat_path_is_None_not_zero_dressed_as_a_measurement(self):
        self.assertIsNone(CS.realised_vol([100.0] * 30))

    def test_realised_vol_refuses_a_path_too_short_to_measure(self):
        self.assertIsNone(CS.realised_vol([100.0, 101.0, 99.0]))

    def test_realised_vol_reproduces_a_hand_computed_value(self):
        rng = np.random.default_rng(0)
        r = rng.normal(0.0, 0.02, 250)
        c = 100.0 * np.exp(np.cumsum(r))
        got = CS.realised_vol(c)
        want = float(np.std(np.diff(np.log(c)), ddof=1)) * np.sqrt(252.0)
        self.assertAlmostEqual(got, want, places=12)

    def test_elevation_refuses_a_zero_baseline_rather_than_dividing_by_it(self):
        self.assertIsNone(CS.elevation(0.5, 0.0))
        self.assertIsNone(CS.elevation(0.5, None))


class TestTheContract(unittest.TestCase):
    def _chain(self):
        return pd.DataFrame({
            "right": ["P", "P", "P", "C", "P"],
            "dte": [35, 35, 35, 35, 10],
            "delta": [-0.24, -0.50, -0.10, 0.25, -0.25],
            "mid": [1.00, 3.00, 0.40, 1.00, 1.00],
            "spread_frac": [0.10, 0.10, 0.10, 0.10, 0.10],
            "open_interest": [500, 500, 500, 500, 500],
            "strike": [90.0, 100.0, 80.0, 110.0, 90.0],
            "expiration": ["2020-03-20"] * 5,
            "iv": [0.4] * 5, "spot": [100.0] * 5,
        })

    def test_it_picks_the_put_nearest_the_target_delta_inside_the_dte_band(self):
        r = CS.pick_csp(self._chain())
        self.assertAlmostEqual(r["delta"], -0.24)
        self.assertEqual(r["dte"], 35)

    def test_it_never_returns_a_CALL(self):
        c = self._chain()
        c = c[c["right"] == "C"]
        self.assertIsNone(CS.pick_csp(c))

    def test_it_returns_None_rather_than_a_near_miss_outside_the_dte_band(self):
        c = self._chain()
        c["dte"] = 90
        self.assertIsNone(CS.pick_csp(c))

    def test_the_liquidity_gate_actually_rejects(self):
        c = self._chain()
        c["open_interest"] = 10
        self.assertIsNone(CS.pick_csp(c))
        c = self._chain()
        c["spread_frac"] = 0.90
        self.assertIsNone(CS.pick_csp(c))

    def test_selling_at_aggression_1_hits_the_BID_and_agrees_with_the_shipped_engine(self):
        mid, sf = 1.00, 0.10
        got = CS.sell_credit(mid, sf)
        q = Quote(bid=0.95, ask=1.05)
        self.assertAlmostEqual(got, fill_price(q, "sell", 1.0), places=12)
        self.assertAlmostEqual(got, 0.95, places=12)

    def test_the_reconstructed_quotes_mid_is_the_mid_it_was_built_from(self):
        q = CS.reconstruct_quote(2.40, 0.20)
        self.assertAlmostEqual(q.mid, 2.40, places=12)
        self.assertAlmostEqual(q.ask - q.bid, 0.20 * 2.40, places=12)

    def test_the_rho_diagnostic_is_STRICTLY_BETTER_than_the_headline_and_is_not_it(self):
        # O18: a real trade pays ~2/3 of the quoted half-spread, so the diagnostic credit is
        # higher than the touch. It is a DIAGNOSTIC (void condition 9) and the two must differ,
        # or nobody could tell which number they were reading.
        head = CS.sell_credit(1.00, 0.10)
        diag = CS._rho_credit(1.00, 0.10)
        self.assertGreater(diag, head)
        self.assertLess(diag, 1.00)

    def test_annualisation_scales_with_dte_and_refuses_a_nonpositive_one(self):
        self.assertIsNone(CS.annualise_credit(0.01, 0))
        self.assertAlmostEqual(CS.annualise_credit(0.01, 365), 0.01, places=12)
        self.assertAlmostEqual(CS.annualise_credit(0.01, 36.5), 0.10, places=12)


class TestTheGate(unittest.TestCase):
    def test_a_clean_pass(self):
        g = CS.gate(0.010, 0.50, 0.60, 0.05)
        self.assertTrue(g["open"])
        self.assertAlmostEqual(g["elevation_ratio"], 0.50 / 0.60)

    def test_G1_fails_on_a_credit_below_the_floor(self):
        g = CS.gate(0.004, 0.50, 0.60, 0.05)
        self.assertFalse(g["G1_credit"])
        self.assertFalse(g["open"])

    def test_G2_fails_when_the_market_HAS_priced_the_distinction(self):
        # healthy vol much cheaper than unhealthy => the asymmetry is already paid for
        g = CS.gate(0.010, 0.20, 0.60, 0.05)
        self.assertFalse(g["G2_not_priced"])
        self.assertFalse(g["open"])

    def test_G3_fails_when_the_premium_is_merely_fair(self):
        g = CS.gate(0.010, 0.50, 0.60, -0.01)
        self.assertFalse(g["G3_vrp"])
        self.assertFalse(g["open"])

    def test_a_MISSING_input_FAILS_the_gate_and_never_passes_it(self):
        # `oos_directions_tested = 0` is not a negative result, and a gate that opens because a
        # number could not be computed is that error in a different hat.
        for args in [(None, 0.5, 0.6, 0.05), (0.01, None, 0.6, 0.05),
                     (0.01, 0.5, None, 0.05), (0.01, 0.5, 0.6, None)]:
            self.assertFalse(CS.gate(*args)["open"], msg=str(args))

    def test_the_gate_reports_itself_UNCALIBRATED(self):
        self.assertTrue(CS.gate(0.01, 0.5, 0.6, 0.05)["uncalibrated"])


class TestDrawdownSign(unittest.TestCase):
    def test_S10s_REAL_measured_pair_is_a_WORSENING_not_an_improvement(self):
        # S10 measured base -0.2809 and arm -0.2863. max_drawdown is NEGATIVE, so the gain is
        # `arm - base` = -0.0054, a WORSENING. The first cut of S10 computed `base - arm` and
        # reported that 2.61pp worsening as an improvement.
        base, arm = -0.2809, -0.2863
        self.assertLess(arm - base, 0.0)
        self.assertGreater(base - arm, 0.0)   # the WRONG convention would read positive

    def test_max_drawdown_is_negative_and_zero_only_on_a_never_losing_path(self):
        self.assertLess(CS.max_drawdown([0.1, -0.5, 0.2]), 0.0)
        self.assertAlmostEqual(CS.max_drawdown([0.01, 0.01, 0.01]), 0.0, places=12)


class TestHalves(unittest.TestCase):
    def test_the_boundary_date_is_EMBARGOED_so_the_halves_do_not_sum_to_the_total(self):
        ds = pd.bdate_range("2020-01-01", periods=40)
        e, l, b = CS.halves(ds)
        self.assertEqual(len(e), 20)
        self.assertEqual(len(l), 19)
        self.assertNotIn(b, e)
        self.assertNotIn(b, l)

    def test_a_too_thin_date_list_RAISES_rather_than_returning_a_thin_split(self):
        with self.assertRaises(CS.RegisterViolation):
            CS.halves(pd.bdate_range("2020-01-01", periods=10))


class TestSettlement(unittest.TestCase):
    def test_an_unassigned_put_keeps_exactly_the_credit(self):
        r = CS.settle_put(strike=100.0, credit=2.50, spot_at_expiry=105.0)
        self.assertFalse(r["assigned"])
        self.assertAlmostEqual(r["pnl_per_share"], 2.50, places=12)
        self.assertAlmostEqual(r["ret_on_strike"], 0.025, places=12)

    def test_an_assigned_put_loses_the_intrinsic_net_of_the_credit(self):
        r = CS.settle_put(strike=100.0, credit=2.50, spot_at_expiry=80.0)
        self.assertTrue(r["assigned"])
        self.assertAlmostEqual(r["pnl_per_share"], 2.50 - 20.0, places=12)
        self.assertAlmostEqual(r["ret_on_strike"], -0.175, places=12)

    def test_the_return_is_on_the_CASH_SECURED_amount_not_the_premium(self):
        # A CSP's capital at risk is the strike, not the credit. Dividing by the credit would
        # report a -17.5% trade as a -700% one and make every summary meaningless.
        r = CS.settle_put(strike=100.0, credit=2.50, spot_at_expiry=80.0)
        self.assertAlmostEqual(r["ret_on_strike"], r["pnl_per_share"] / 100.0, places=12)

    def test_a_missing_settlement_spot_returns_None_and_never_a_free_win(self):
        self.assertIsNone(CS.settle_put(100.0, 2.5, None))

    def test_spot_on_reads_the_AS_TRADED_spot_and_not_an_adjusted_close(self):
        # The measured AAPL case: as-traded 300.35 against an adjusted 72.34 on 2020-01-02.
        # A settlement basis that returned the adjusted number would book a fake assignment.
        d = pd.DataFrame({"date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
                          "spot": [300.35, 297.43]})
        self.assertAlmostEqual(CS.spot_on(d, "2020-01-02"), 300.35, places=6)

    def test_spot_on_refuses_a_nonpositive_or_missing_spot(self):
        d = pd.DataFrame({"date": pd.to_datetime(["2020-01-02"]), "spot": [0.0]})
        self.assertIsNone(CS.spot_on(d, "2020-01-02"))


class TestConcurrency(unittest.TestCase):
    def _t(self, entry, expiry, ret):
        return {"entry": entry, "expiry": expiry, "ret_on_strike": ret, "assigned": ret < 0}

    def test_a_cap_of_one_refuses_the_overlapping_trade(self):
        ts = [self._t("2020-01-02", "2020-02-20", 0.02),
              self._t("2020-01-10", "2020-02-20", 0.03)]
        b = CS.concurrency_book(ts, cap=1)
        self.assertEqual(b["taken"], 1)
        self.assertEqual(b["skipped"], 1)

    def test_a_cap_large_enough_takes_everything(self):
        ts = [self._t("2020-01-02", "2020-02-20", 0.02),
              self._t("2020-01-10", "2020-02-20", 0.03)]
        b = CS.concurrency_book(ts, cap=50)
        self.assertEqual(b["taken"], 2)
        self.assertEqual(b["skipped"], 0)

    def test_a_slot_is_RELEASED_at_expiry_so_a_later_trade_can_fill(self):
        ts = [self._t("2020-01-02", "2020-02-20", 0.02),
              self._t("2020-03-02", "2020-04-20", 0.03)]
        b = CS.concurrency_book(ts, cap=1)
        self.assertEqual(b["taken"], 2)
        self.assertEqual(b["skipped"], 0)


class TestSignTest(unittest.TestCase):
    def test_all_positive_cells_give_a_large_positive_z(self):
        r = CS.paired_sign_test([(0.05, 0.01)] * 16)
        self.assertEqual(r["n_positive"], 16)
        self.assertGreater(r["z"], 3.0)
        self.assertLess(r["p"], 0.01)

    def test_a_coin_flip_is_not_significant(self):
        cells = [(0.05, 0.01)] * 8 + [(0.01, 0.05)] * 8
        r = CS.paired_sign_test(cells)
        self.assertAlmostEqual(r["z"], 0.0, places=12)
        self.assertGreater(r["p"], 0.9)

    def test_exact_ties_are_dropped_rather_than_counted_as_wins(self):
        r = CS.paired_sign_test([(0.02, 0.02)] * 10 + [(0.05, 0.01)] * 4)
        self.assertEqual(r["n_cells"], 4)


class TestRegisterConstants(unittest.TestCase):
    def test_the_preregistered_constants_are_what_the_register_says(self):
        self.assertEqual(CS.TARGET_DELTA, -0.25)
        self.assertEqual((CS.DTE_LO, CS.DTE_HI), (30, 45))
        self.assertEqual(CS.MIN_OI, 100)
        self.assertEqual(CS.MAX_SPREAD_FRAC, 0.25)
        self.assertEqual(CS.SELL_AGGRESSION, 1.0)
        self.assertEqual(CS.COST_RHO, 0.6743)
        self.assertEqual(CS.G1_MIN_CREDIT_FRAC, 0.005)
        self.assertEqual(CS.G2_MIN_ELEVATION_RATIO, 0.75)
        self.assertEqual(CS.BASELINE_WINDOW, 252)
        self.assertEqual(CS.FORWARD_DAYS, 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
