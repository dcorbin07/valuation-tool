"""Tests for O11 + O19 + O22 + O25 (PREREG_o11_o19_o22_o25_portfolio.md).

The load-bearing ones are the split-guard tests. `assert_raw_spot` must RAISE, must not pass
vacuously on an empty overlap, and must not be downgradable to a warning - the register makes
that a void condition, because this defect class has now appeared twice and is silent by nature.
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import portfolio_capacity as PC  # noqa: E402


def _book(n=50, spot=100.0):
    return [{"ticker": "AAA", "alert_ts": "2020-01-%02d" % (i + 1),
             "underlying_entry": spot, "entry_premium": 5.0, "pnl_pct": 0.1}
            for i in range(n)]


class TestTheSplitGuardRaises(unittest.TestCase):
    """§2 of the register. This is the third-recurrence stopper."""

    def test_a_matching_series_passes_and_reports(self):
        b = _book()
        px = {"AAA": {r["alert_ts"]: 100.0 for r in b}}
        rep = PC.assert_raw_spot(b, px)
        self.assertEqual(rep["checked"], 50)
        self.assertLess(rep["median_rel_err"], PC.SPOT_TOL)

    def test_an_adjusted_series_RAISES_rather_than_warning(self):
        b = _book()
        # a 40x cumulative split factor, the NVDA-shaped case
        px = {"AAA": {r["alert_ts"]: 100.0 / 40.0 for r in b}}
        with self.assertRaises(PC.SpotBasisError):
            PC.assert_raw_spot(b, px)

    def test_the_error_names_the_defect_so_the_next_reader_knows_the_fix(self):
        b = _book()
        px = {"AAA": {r["alert_ts"]: 2.5 for r in b}}
        try:
            PC.assert_raw_spot(b, px)
            self.fail("expected SpotBasisError")
        except PC.SpotBasisError as e:
            self.assertIn("raw_close", str(e))

    def test_an_empty_overlap_RAISES_rather_than_passing_vacuously(self):
        # a guard that checks nothing must not report success - that is the failure mode it
        # exists to prevent, and it is how a bound passes while measuring nothing
        b = _book()
        with self.assertRaises(PC.SpotBasisError):
            PC.assert_raw_spot(b, {"ZZZ": {"2020-01-01": 100.0}})

    def test_a_small_drift_within_tolerance_still_passes(self):
        b = _book()
        px = {"AAA": {r["alert_ts"]: 100.0 * (1 + 1e-9) for r in b}}
        PC.assert_raw_spot(b, px)

    def test_the_guard_is_an_exception_type_not_a_return_flag(self):
        # if this ever becomes a bool return, the runner will silently continue
        self.assertTrue(issubclass(PC.SpotBasisError, Exception))


class TestO19Weighting(unittest.TestCase):
    def test_cheap_contracts_get_more_contracts(self):
        self.assertGreater(PC.contracts_for(0.50), PC.contracts_for(5.00))

    def test_contract_weighting_leans_toward_the_cheap_population(self):
        rows = [{"entry_premium": 0.50, "pnl_pct": -1.0},
                {"entry_premium": 5.00, "pnl_pct": +1.0}]
        w = PC.weighted_expectancy(rows)
        self.assertAlmostEqual(w["equal_weighted"], 0.0)
        # the cheap loser carries ~10x the contracts, so contract-weighting must be negative
        self.assertLess(w["contract_weighted"], 0.0)

    def test_dollar_weighting_is_closer_to_equal_than_contract_weighting(self):
        rows = [{"entry_premium": 0.50, "pnl_pct": -1.0},
                {"entry_premium": 5.00, "pnl_pct": +1.0}]
        w = PC.weighted_expectancy(rows)
        self.assertLessEqual(abs(w["dollar_weighted"]), abs(w["contract_weighted"]) + 1e-9)

    def test_rows_without_a_premium_are_skipped_not_defaulted(self):
        rows = [{"entry_premium": None, "pnl_pct": 5.0}, {"entry_premium": 2.0, "pnl_pct": 0.1}]
        self.assertEqual(PC.weighted_expectancy(rows)["n"], 1)

    def test_artefact_when_equal_and_dollar_disagree_in_sign(self):
        self.assertEqual(PC.o19_verdict(0.05, -0.02, []), "ARTEFACT")

    def test_not_an_artefact_when_they_agree(self):
        self.assertEqual(PC.o19_verdict(0.05, 0.03, []), "NOT-AN-ARTEFACT")

    def test_a_large_floor_move_with_a_clean_interval_is_an_artefact(self):
        self.assertEqual(PC.o19_verdict(0.05, 0.04, [(3.0, 1.0, 5.0)]), "ARTEFACT")

    def test_a_large_floor_move_whose_interval_straddles_zero_is_not(self):
        self.assertEqual(PC.o19_verdict(0.05, 0.04, [(3.0, -1.0, 7.0)]), "NOT-AN-ARTEFACT")

    def test_a_small_floor_move_is_not_an_artefact_however_clean(self):
        self.assertEqual(PC.o19_verdict(0.05, 0.04, [(1.0, 0.5, 1.5)]), "NOT-AN-ARTEFACT")


class TestDrawdownGeometry(unittest.TestCase):
    def test_drawdown_is_a_fraction_of_PEAK_not_of_initial_capital(self):
        # doubles to 200 then halves to 100: that is a 50% drawdown, not 0%
        self.assertAlmostEqual(PC.max_drawdown_frac([100, 200, 100]), 0.5)

    def test_a_monotone_curve_has_no_drawdown(self):
        self.assertAlmostEqual(PC.max_drawdown_frac([1, 2, 3, 4]), 0.0)

    def test_the_worst_drawdown_is_taken_not_the_last(self):
        self.assertAlmostEqual(PC.max_drawdown_frac([100, 50, 100, 90]), 0.5)

    def test_longest_duration_counts_observations_under_water(self):
        s = PC.drawdown_spans([100, 90, 80, 95, 105])
        self.assertEqual(s["longest_duration"], 3)
        self.assertTrue(s["recovered"])

    def test_an_unrecovered_drawdown_reports_recovered_false(self):
        s = PC.drawdown_spans([100, 90, 80, 70])
        self.assertFalse(s["recovered"])
        self.assertIsNone(s["time_to_recovery"])

    def test_o11_verdict_thresholds(self):
        self.assertEqual(PC.o11_verdict(0.10, 0.20), "SURVIVABLE")
        self.assertEqual(PC.o11_verdict(0.60, 0.10), "UNSURVIVABLE")
        self.assertEqual(PC.o11_verdict(0.30, 0.10), "MARGINAL")

    def test_o11_needs_both_halves_and_defaults_to_marginal(self):
        self.assertEqual(PC.o11_verdict(0.10, None), "MARGINAL")

    def test_o11_boundaries_are_the_registered_values(self):
        self.assertEqual(PC.o11_verdict(PC.DD_UNSURVIVABLE, 0.01), "UNSURVIVABLE")
        self.assertEqual(PC.o11_verdict(PC.DD_SURVIVABLE, 0.01), "MARGINAL")


class TestTheLongLegMapping(unittest.TestCase):
    """The shipped portfolio layer marks `(credit_ps - mark)` - the P&L of something SOLD.
    A long call is the opposite sign, so this mapping is where an error would hide silently:
    it would not raise, it would just report the equity curve upside down."""

    def _row(self):
        return {"ticker": "AAA", "alert_ts": "2020-01-02", "held_days": 5,
                "entry_premium": 2.00, "pnl_dollars": 300.0, "iv": 0.3}

    def test_the_layers_own_expression_recovers_long_pnl(self):
        t = PC.long_leg_as_book_trade(self._row(), [("2020-01-03", 3.00)])
        mark = dict(t["marks"])["2020-01-03"]
        # this is verbatim what simulate_book computes, per share
        unreal_ps = t["credit_ps"] - mark
        self.assertAlmostEqual(unreal_ps, 3.00 - 2.00)

    def test_a_losing_mark_is_negative_not_positive(self):
        t = PC.long_leg_as_book_trade(self._row(), [("2020-01-03", 1.20)])
        mark = dict(t["marks"])["2020-01-03"]
        self.assertAlmostEqual(t["credit_ps"] - mark, 1.20 - 2.00)
        self.assertLess(t["credit_ps"] - mark, 0.0)

    def test_the_opening_mark_books_zero_pnl_not_the_whole_premium(self):
        t = PC.long_leg_as_book_trade(self._row(), [("2020-01-02", 2.00)])
        self.assertAlmostEqual(t["credit_ps"] - dict(t["marks"])["2020-01-02"], 0.0)

    def test_max_risk_is_the_whole_debit(self):
        t = PC.long_leg_as_book_trade(self._row(), [])
        self.assertAlmostEqual(t["max_risk_dollars"], 200.0)

    def test_exit_date_is_derived_from_held_days_when_absent(self):
        t = PC.long_leg_as_book_trade(self._row(), [])
        self.assertEqual(t["exit_date"], "2020-01-07")

    def test_a_row_without_a_premium_is_refused(self):
        r = self._row()
        r["entry_premium"] = 0.0
        self.assertIsNone(PC.long_leg_as_book_trade(r, []))


class TestCapacity(unittest.TestCase):
    def test_participation_rises_with_position_size(self):
        self.assertLess(PC.participation(1e4, 1e6), PC.participation(1e5, 1e6))

    def test_zero_depth_is_refused_rather_than_infinite(self):
        self.assertIsNone(PC.participation(1e4, 0.0))

    def test_cost_is_monotone_in_participation(self):
        a = PC.modelled_cost_bps(0.01)
        b = PC.modelled_cost_bps(0.10)
        self.assertLess(a, b)

    def test_cost_scales_with_lambda(self):
        self.assertAlmostEqual(PC.modelled_cost_bps(0.05, lam=2.0),
                               2.0 * PC.modelled_cost_bps(0.05, lam=1.0))

    def test_capacity_falls_as_lambda_rises(self):
        d = [1e6] * 50
        c1 = PC.capacity_aum(d, edge_bps=300.0, position_share=0.02, lam=0.5)
        c2 = PC.capacity_aum(d, edge_bps=300.0, position_share=0.02, lam=2.0)
        self.assertIsNotNone(c1)
        self.assertIsNotNone(c2)
        self.assertGreater(c1, c2)

    def test_capacity_is_none_when_the_edge_is_never_crossed(self):
        self.assertIsNone(PC.capacity_aum([1e12] * 10, edge_bps=1e9, position_share=1e-9))

    def test_cost_at_capacity_equals_the_edge(self):
        d = [5e5] * 40
        cap = PC.capacity_aum(d, edge_bps=250.0, position_share=0.02)
        parts = (cap * 0.02) / np.asarray(d)
        med = float(np.median([PC.modelled_cost_bps(p) for p in parts]))
        self.assertAlmostEqual(med, 250.0, places=2)


class TestWing(unittest.TestCase):
    def test_first_crossing_takes_the_FIRST_not_the_best(self):
        marks = [("d1", 1.0), ("d2", 1.8), ("d3", 3.0)]
        self.assertEqual(PC.first_crossing(marks, 1.0, 0.75), 1)

    def test_no_crossing_returns_none(self):
        marks = [("d1", 1.0), ("d2", 1.2)]
        self.assertIsNone(PC.first_crossing(marks, 1.0, 0.75))

    def test_the_threshold_is_inclusive(self):
        marks = [("d1", 1.75)]
        self.assertEqual(PC.first_crossing(marks, 1.0, 0.75), 0)

    def test_the_wing_caps_the_upside_it_was_predicted_to_cap(self):
        # long runs 1.00 -> 5.00; wing sold for 0.40 and bought back at 2.00
        capped = PC.wing_pnl_pct(1.0, 5.0, 0.40, 2.00)
        naked = (5.0 - 1.0) / 1.0
        self.assertLess(capped, naked)

    def test_the_wing_helps_when_the_move_stalls(self):
        stalled = PC.wing_pnl_pct(1.0, 1.8, 0.40, 0.05)
        naked = (1.8 - 1.0) / 1.0
        self.assertGreater(stalled, naked)

    def test_the_short_leg_is_charged_both_ways(self):
        # credit at the bid, buyback at the ask: a zero-move wing must not be free money
        v = PC.wing_pnl_pct(1.0, 1.0, 0.40, 0.40)
        self.assertAlmostEqual(v, 0.0)

    def test_paired_verdict_needs_both_comparators_in_both_halves(self):
        ok = (0.05, (0.01, 0.09))
        bad = (0.05, (-0.01, 0.09))
        self.assertEqual(PC.paired_verdict(*ok, *ok, *ok, *ok), "CANDIDATE")
        self.assertEqual(PC.paired_verdict(*ok, *ok, *ok, *bad), "NULL")

    def test_paired_verdict_rejects_a_negative_mean_even_with_a_clean_interval(self):
        self.assertEqual(
            PC.paired_verdict(-0.05, (-0.09, -0.01), -0.05, (-0.09, -0.01),
                              -0.05, (-0.09, -0.01), -0.05, (-0.09, -0.01)), "NULL")


class TestRegisteredConstants(unittest.TestCase):
    def test_constants_match_the_register(self):
        self.assertEqual(PC.SEED, 20260812)
        self.assertEqual(PC.O19_FLOORS, (1.0, 2.0))
        self.assertEqual(PC.O19_ARTEFACT_PP, 2.00)
        self.assertEqual(PC.O11_CELLS,
                         ((50000.0, 10), (50000.0, 50), (250000.0, 10), (250000.0, 50)))
        self.assertEqual((PC.DD_UNSURVIVABLE, PC.DD_SURVIVABLE), (0.50, 0.25))
        self.assertEqual(PC.O22_LAMBDAS, (0.5, 1.0, 2.0))
        self.assertEqual(PC.O22_LAMBDA_HEADLINE, 1.0)
        self.assertEqual(PC.O25_THRESHOLDS, (0.75, 1.00))
        self.assertEqual(PC.WING_DELTA, 0.15)
        self.assertEqual(PC.SPOT_TOL, 1e-6)

    def test_the_shipped_sizer_is_imported_not_reimplemented(self):
        from valuation.edge import options_sizing as OSZ
        self.assertIs(PC.contracts_for, OSZ.contracts_for)
        self.assertEqual(PC.RISK_PER_TRADE, OSZ.RISK_PER_TRADE)

    def test_nothing_is_adopted(self):
        from valuation.edge import options_fill as OF
        from valuation.edge import options_sizing as OSZ
        self.assertEqual(OF.DEFAULT_AGGRESSION, 1.0)
        self.assertEqual(OSZ.RISK_PER_TRADE, 1000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
