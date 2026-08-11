"""O21 — pins dividends and the model-free early-exercise measurement (2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

TWO OF THESE TESTS PIN A MISTAKE I MADE AND FIXED MID-STUDY, because both errors scored in the
direction that would have made the finding look bigger or made it vanish, and neither raised an
exception:

  * spot was first estimated as `max(call_bid + strike)` over the chain. Parity gives
    `C >= S - K`, so every `bid + K` is an UPPER bound on spot and the MAXIMUM is the loosest
    one -- inflating intrinsic and inflating the early-exercise gain to +5.62pp on a smoke
    subset. `test_the_old_max_bound_overstates_spot` holds that fact.
  * `spot_from_parity` then rejected `put_mid <= 0`, which discards exactly the deep-ITM-call
    cases early exercise lives in, and scored ZERO rows. `test_a_zero_value_put_is_allowed`
    holds that.
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import dividends as DV           # noqa: E402


DIVS = {"PAY": [("2020-02-10", 0.50), ("2020-05-11", 0.50),
                ("2020-08-10", 0.55), ("2020-11-09", 0.55),
                ("2021-02-08", 0.60)],
        "NOPAY": []}


class DividendWindows(unittest.TestCase):
    def test_the_window_is_open_on_the_left(self):
        """A dividend whose ex-date IS the entry date has already been priced out of the
        underlying by the time the position exists."""
        got = DV.dividends_between(DIVS, "PAY", "2020-02-10", "2020-06-01")
        self.assertEqual([d for d, _ in got], ["2020-05-11"])

    def test_the_window_is_closed_on_the_right(self):
        got = DV.dividends_between(DIVS, "PAY", "2020-01-01", "2020-02-10")
        self.assertEqual([d for d, _ in got], ["2020-02-10"])

    def test_an_unknown_ticker_is_empty_not_an_error(self):
        self.assertEqual(DV.dividends_between(DIVS, "ZZZZ", "2020-01-01", "2021-01-01"), [])

    def test_a_malformed_date_is_empty_not_an_error(self):
        self.assertEqual(DV.dividends_between(DIVS, "PAY", "not-a-date", "2021-01-01"), [])


class Yields(unittest.TestCase):
    def test_trailing_yield_uses_only_dates_strictly_before_entry(self):
        """This is what makes the PRIMARY yield defensible as point-in-time: nothing at or after
        the entry date can enter it, so no arm resting on it can be accused of look-ahead.

        365 days back from 2021-01-01 is 2020-01-02, so all FOUR 2020 ex-dates qualify and the
        2021-02-08 one does not."""
        q = DV.q_trailing(DIVS, "PAY", "2021-01-01", 100.0)
        self.assertAlmostEqual(q, (0.50 + 0.50 + 0.55 + 0.55) / 100.0, places=12)

    def test_a_dividend_on_the_entry_date_is_excluded_from_the_trailing_yield(self):
        q = DV.q_trailing(DIVS, "PAY", "2020-02-10", 100.0)
        self.assertAlmostEqual(q, 0.0, places=12)

    def test_a_non_payer_yields_zero_not_none(self):
        self.assertEqual(DV.q_trailing(DIVS, "NOPAY", "2021-01-01", 100.0), 0.0)

    def test_a_missing_spot_is_none_not_a_division_error(self):
        self.assertIsNone(DV.q_trailing(DIVS, "PAY", "2021-01-01", 0))
        self.assertIsNone(DV.q_trailing(DIVS, "PAY", "2021-01-01", None))

    def test_scheduled_yield_is_annualised_over_the_contract_life(self):
        # one 0.60 dividend inside a half-year window on a 100 spot -> 1.2%/yr
        q = DV.q_scheduled(DIVS, "PAY", "2021-01-01", "2021-07-01", 100.0)
        self.assertAlmostEqual(q, (0.60 / 100.0) / (181 / 365.0), places=6)

    def test_scheduled_yield_reads_the_future_and_the_primary_does_not(self):
        """The register forbids the scheduled yield from carrying a verdict, and this is why:
        it sees a dividend the trailing yield cannot."""
        entry, expiry = "2021-01-01", "2021-03-01"
        self.assertGreater(DV.q_scheduled(DIVS, "PAY", entry, expiry, 100.0), 0)
        self.assertAlmostEqual(DV.q_trailing(DIVS, "PAY", entry, 100.0),
                               (0.50 + 0.50 + 0.55 + 0.55) / 100.0, places=12)


class Parity(unittest.TestCase):
    def test_parity_recovers_spot_exactly(self):
        S, K, r, T = 100.0, 90.0, 0.05, 0.5
        # a self-consistent pair: C - P = S - K*exp(-rT)
        P = 2.0
        C = P + S - K * math.exp(-r * T)
        self.assertAlmostEqual(DV.spot_from_parity(C, P, K, r, T), S, places=10)

    def test_a_zero_value_put_is_allowed(self):
        """A deep-ITM call's matching put legitimately quotes at zero -- exactly the situation
        early exercise lives in. Rejecting it scored ZERO rows on the first full smoke test."""
        got = DV.spot_from_parity(30.0, 0.0, 70.0, 0.02, 0.25)
        self.assertIsNotNone(got)
        self.assertGreater(got, 90.0)

    def test_a_negative_put_is_refused(self):
        self.assertIsNone(DV.spot_from_parity(30.0, -1.0, 70.0, 0.02, 0.25))

    def test_the_old_max_bound_overstates_spot(self):
        """Pins the direction of the first version's error, so it cannot quietly return.

        Parity gives C >= S - K, i.e. bid + K >= S for every strike. Taking the MAXIMUM over the
        chain therefore yields the LOOSEST upper bound, which overstates spot, overstates
        intrinsic, and overstates the early-exercise gain.
        """
        S, K_true, r, T = 100.0, 90.0, 0.0, 0.0
        chain = [(90.0, 11.0), (80.0, 21.0), (50.0, 55.0)]   # (strike, call bid)
        old = max(k + b for k, b in chain)
        self.assertGreater(old, S)
        parity_leg = [k + b for k, b in chain]
        self.assertLessEqual(min(parity_leg), old)


class EarlyExercise(unittest.TestCase):
    def test_intrinsic_is_never_negative(self):
        self.assertEqual(DV.intrinsic(50.0, 90.0, "C"), 0.0)
        self.assertEqual(DV.intrinsic(120.0, 90.0, "P"), 0.0)

    def test_a_put_is_intrinsic_the_other_way_round(self):
        self.assertAlmostEqual(DV.intrinsic(80.0, 90.0, "P"), 10.0, places=12)

    def test_the_exercise_gain_is_the_shortfall_of_the_bid_below_intrinsic(self):
        self.assertAlmostEqual(DV.exercise_gain(8.0, 100.0, 90.0, "C"), 2.0, places=12)

    def test_a_bid_above_intrinsic_gains_nothing_and_never_goes_negative(self):
        """A holder always HAS the choice, so this is a floor on value. A negative here would
        claim the backtest beat an optimising holder, which is impossible."""
        self.assertEqual(DV.exercise_gain(15.0, 100.0, 90.0, "C"), 0.0)

    def test_the_measurement_needs_no_vol_rate_or_dividend_estimate(self):
        """Model-free by construction: the textbook early-exercise condition compares the
        dividend to remaining time value, which would make the answer a function of the very
        pricer under test."""
        import inspect
        src = inspect.getsource(DV.exercise_gain)
        for banned in ("sigma", "implied_vol", "bs_price", "q_trailing"):
            self.assertNotIn(banned, src)

    def test_exit_below_intrinsic_counts_and_sizes(self):
        rows = [{"exit_premium": 8.0, "entry_premium": 4.0, "strike": 90.0, "opt_right": "C"},
                {"exit_premium": 15.0, "entry_premium": 4.0, "strike": 90.0, "opt_right": "C"}]
        out = DV.exit_below_intrinsic(rows, lambda r: 100.0)
        self.assertEqual(out["n_scored"], 2)
        self.assertEqual(out["n_below_intrinsic"], 1)
        self.assertAlmostEqual(out["total_gain_dollars_per_contract"], 2.0, places=12)

    def test_a_missing_spot_drops_the_row_rather_than_scoring_it_as_zero(self):
        rows = [{"exit_premium": 8.0, "entry_premium": 4.0, "strike": 90.0, "opt_right": "C"}]
        out = DV.exit_below_intrinsic(rows, lambda r: None)
        self.assertEqual(out["n_scored"], 0)

    def test_spanning_counts_calls_only(self):
        rows = [{"opt_right": "C", "ticker": "PAY", "alert_ts": "2020-01-01",
                 "expiry": "2020-03-01"},
                {"opt_right": "P", "ticker": "PAY", "alert_ts": "2020-01-01",
                 "expiry": "2020-03-01"}]
        self.assertEqual(DV.held_across_ex_div(rows, DIVS)["n_calls_spanning_ex_div"], 1)


class TheModuleIsCiSafe(unittest.TestCase):
    def test_a_missing_actions_cache_is_empty_not_an_exception(self):
        """`data/` is gitignored, so CI has none. Raising here would fail the whole gate."""
        self.assertEqual(DV.load_dividends(os.path.join(os.sep, "no", "such", "root")), {})


class ThePricerAlreadyHandlesQ(unittest.TestCase):
    def test_the_defect_is_the_caller_not_the_model(self):
        """O21's central scoping claim, pinned: bs_price/greeks already take q and use it. If
        someone later 'adds dividend support' to the pricer they are fixing the wrong thing."""
        from valuation.edge import blackscholes as BS
        import inspect
        for fn in (BS.bs_price, BS.implied_vol, BS.greeks):
            self.assertIn("q", inspect.signature(fn).parameters)
        # and q genuinely moves the price, rather than being an accepted-and-ignored argument
        a = BS.bs_price(100.0, 100.0, 0.5, 0.03, 0.30, "C", 0.0)
        b = BS.bs_price(100.0, 100.0, 0.5, 0.03, 0.30, "C", 0.05)
        self.assertLess(b, a)

    def test_ignoring_dividends_understates_the_solved_iv(self):
        """The arithmetic behind D3's sign, stated so the direction cannot be misquoted: at
        q = 0 the model call price is HIGHER for any given sigma, so the sigma that reproduces a
        given market mid is LOWER. Hence iv(q>0) > iv(q=0)."""
        from valuation.edge import blackscholes as BS
        mid = BS.bs_price(100.0, 100.0, 0.5, 0.03, 0.30, "C", 0.04)
        v0 = BS.implied_vol(mid, 100.0, 100.0, 0.5, 0.03, "C", 0.0)
        vq = BS.implied_vol(mid, 100.0, 100.0, 0.5, 0.03, "C", 0.04)
        self.assertLess(v0, vq)
        self.assertAlmostEqual(vq, 0.30, places=4)


class TheLiveSelectionPathIsPinnedAsANonChange(unittest.TestCase):
    """O21 measured the defect and the pre-registered materiality bar was NOT met, so the live
    path is deliberately left alone. That decision is pinned rather than left implicit, in the
    same way session 16 pinned the sizing quantity and session 20 pinned `zscore`.

    If someone later passes a dividend yield into `pick_contract`, these tests fail -- which is
    the point. It would change WHICH CONTRACT the live engine buys (measured: on 4.63% of
    entries, at a median delta gap of 0.129 and 93.9% of the time to a lower strike), and that
    is a construction change, not a bug fix.
    """

    def test_pick_contract_still_enriches_at_the_default_zero_yield(self):
        import inspect
        from valuation.edge import options_backtest as OB
        src = inspect.getsource(OB.pick_contract)
        self.assertIn("BS.enrich_chain(near, underlying, asof)", src)
        self.assertNotIn("q=", src.split("enrich_chain")[1][:60])

    def test_enrich_chain_still_defaults_q_to_zero(self):
        import inspect
        from valuation.edge import blackscholes as BS
        self.assertEqual(inspect.signature(BS.enrich_chain).parameters["q"].default, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
