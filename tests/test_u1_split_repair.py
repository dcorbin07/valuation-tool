"""U1-SPLIT — pins the source guard against corporate actions (options bot, 2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

The defect: option chains are AS-TRADED and unadjusted for splits while `bars` ARE adjusted, so
`simulate_trade` settled a GE call at `max(0, raw_close − strike)` with the close post-split and
the strike pre-split, booking +31,921% against a true value of zero.

What these pin is the set of properties that make the repair a repair rather than a second bug:
that the guard is keyed on a DATE and never on a return, that it is judged at ENTRY so it cannot
depend on the outcome, that `splits=None` leaves the historical path bit-identical, and that the
project has exactly ONE split table.
"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import composite_entry as CE           # noqa: E402
from valuation.edge import options_backtest as OB          # noqa: E402
from valuation.edge import options_universe as U           # noqa: E402

SPL = {"GE": [("2021-08-02", 0.125)], "AAPL": [("2020-08-31", 4.0)]}
D = dt.date


class TheWindowIsTheContractLifeAndItIsKeyedOnDates(unittest.TestCase):
    def test_a_split_inside_the_life_is_caught(self):
        self.assertTrue(OB.split_in_window(SPL, "GE", D(2021, 7, 23), D(2021, 9, 17)))

    def test_a_contract_that_expires_before_the_split_is_clean(self):
        self.assertFalse(OB.split_in_window(SPL, "GE", D(2021, 6, 1), D(2021, 7, 16)))

    def test_a_contract_that_starts_after_the_split_is_clean(self):
        self.assertFalse(OB.split_in_window(SPL, "GE", D(2021, 8, 3), D(2021, 10, 15)))

    def test_the_split_day_is_inside_the_window_and_the_entry_day_is_not(self):
        """`(entry, expiry]` — half-open at the entry end. A split ON the entry day is already
        reflected in the quote that was bought."""
        self.assertTrue(OB.split_in_window(SPL, "GE", D(2021, 7, 30), D(2021, 8, 2)))
        self.assertFalse(OB.split_in_window(SPL, "GE", D(2021, 8, 2), D(2021, 9, 17)))

    def test_a_name_with_no_split_is_never_caught(self):
        self.assertFalse(OB.split_in_window(SPL, "ZZZZ", D(2016, 1, 1), D(2026, 1, 1)))

    def test_it_accepts_iso_strings_as_well_as_dates(self):
        self.assertTrue(OB.split_in_window(SPL, "GE", "2021-07-23", "2021-09-17"))

    def test_an_empty_or_missing_split_table_is_inert(self):
        self.assertFalse(OB.split_in_window({}, "GE", D(2021, 7, 23), D(2021, 9, 17)))
        self.assertFalse(OB.split_in_window(None, "GE", D(2021, 7, 23), D(2021, 9, 17)))


class TheGuardIsBlindToThePayoff(unittest.TestCase):
    """The decisive property. A rule keyed on the SIZE of a return would be selecting on the
    outcome, which is what the whole exercise exists to forbid."""

    def test_the_predicate_takes_no_pnl_argument_at_all(self):
        import inspect
        sig = list(inspect.signature(OB.split_in_window).parameters)
        self.assertEqual(sig, ["splits", "ticker", "entry_date", "expiry"])

    def test_it_is_judged_before_simulation_not_after(self):
        """Dropping only trades whose EXIT lands after the split would be keyed on exit timing,
        which is determined by the payoff. The guard sits above the walk-forward loop."""
        import inspect
        src = inspect.getsource(OB.simulate_trade)
        head = src[:src.index("hist = provider.contract_history")]
        self.assertIn("split_in_window", head)
        self.assertIn("split_in_contract_life", head)

    def test_a_split_free_name_survives_however_extreme_its_return(self):
        self.assertFalse(OB.split_in_window(SPL, "ZZZZ", D(2021, 7, 23), D(2021, 9, 17)))


class TheDefaultIsTheHistoricalBehaviourExactly(unittest.TestCase):
    """`splits=None` must leave every existing caller bit-identical. A repair that silently
    changed unrelated books would be worse than the defect."""

    def test_simulate_trade_defaults_splits_to_none(self):
        import inspect
        p = inspect.signature(OB.simulate_trade).parameters
        self.assertIn("splits", p)
        self.assertIsNone(p["splits"].default)

    def test_the_book_builders_default_to_none_too(self):
        import inspect
        for fn in (U.run_name, U.random_entry_control):
            p = inspect.signature(fn).parameters
            self.assertIn("splits", p, "%s must accept splits" % fn.__name__)
            self.assertIsNone(p["splits"].default)

    def test_both_arms_are_guarded_or_neither(self):
        """Guarding the real book and not the control would turn a corporate-action repair into
        a comparison between two different universes — O20's own lesson."""
        import inspect
        self.assertIn("splits=splits", inspect.getsource(U.run_name))
        self.assertIn("splits=splits", inspect.getsource(U.random_entry_control))


class ThereIsExactlyOneSplitTableInTheProject(unittest.TestCase):
    """`composite_entry` used to carry its own copy. A project with two split tables ends up
    with two answers."""

    def test_composite_entry_delegates_rather_than_reimplementing(self):
        import inspect
        src = inspect.getsource(CE.load_splits)
        self.assertIn("from .options_backtest import load_splits", src)
        self.assertNotIn("actions.pkl", src)

    def test_spans_split_delegates_its_window_test(self):
        import inspect
        src = inspect.getsource(CE.spans_split)
        self.assertIn("split_in_window", src)

    def test_the_two_entry_points_agree_on_the_same_trade(self):
        row = {"ticker": "GE", "alert_ts": "2021-07-23", "expiry": "2021-09-17"}
        self.assertEqual(CE.spans_split(row, SPL),
                         OB.split_in_window(SPL, "GE", "2021-07-23", "2021-09-17"))

    def test_a_row_missing_its_expiry_is_not_silently_dropped(self):
        self.assertFalse(CE.spans_split({"ticker": "GE", "alert_ts": "2021-07-23"}, SPL))


class TheGuardNamesItselfRatherThanVanishingIntoAGenericCounter(unittest.TestCase):
    """Found by the equivalence check, not by reading the code: `u1_entry._mine_cell` collapsed
    every simulation failure to "no_trade", hiding the guard's own rejections. The register
    promised these would be counted AND named."""

    def test_the_miner_propagates_the_reason(self):
        import inspect
        from scripts import u1_entry as E
        src = inspect.getsource(E._mine_cell)
        self.assertIn('(t or {}).get("reason")', src)
        self.assertNotIn('return {"reject": "no_trade"}', src)


class TheModuleSurvivesACheckoutWithNoLicensedData(unittest.TestCase):
    def test_the_predicate_needs_no_actions_table(self):
        self.assertFalse(OB.split_in_window({}, "X", D(2020, 1, 1), D(2020, 2, 1)))

    def test_load_splits_raises_rather_than_returning_a_silent_empty_table(self):
        """A missing table must be loud where it is loaded. An empty dict returned here would
        make the guard inert with no way to tell."""
        with self.assertRaises(OSError):
            OB.load_splits(os.path.join(os.path.dirname(__file__), "no_such_data_root"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
