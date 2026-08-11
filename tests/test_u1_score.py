"""U1 — pins the scorer: it may READ a bar, never set one (options bot, 2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

The scorer was written after `scripts/u1_bar.py` had already banked and committed the bars. These
tests hold it to that arrangement — that the figures it checks against are the ones printed in
the register, that it refuses to run on a mismatch, that it defines no draw count or selection
bound of its own — and pin the verdict rule as a truth table so a later edit cannot quietly turn
a REJECTED into a NULL.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import u1_score as US                 # noqa: E402
from valuation.edge import composite_entry as CE   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, "PREREG_u1_composite_entry.md")


class TheScoringSideCannotMoveTheBar(unittest.TestCase):
    """If the scorer could set a bar, committing the bar first would prove nothing."""

    def test_the_constants_match_the_figures_printed_in_the_register(self):
        with open(REGISTER, "r", encoding="utf-8") as f:
            txt = f.read()
        row = re.search(r"SPLIT_CLEAN[^|]*\|\s*\*\*\+?([0-9.]+)pp\*\*\s*\|\s*\*\*\+?([0-9.]+)pp",
                        txt)
        self.assertIsNotNone(row, "the register no longer prints the two verdict bars")
        self.assertAlmostEqual(float(row.group(1)), US.BARS_IN_REGISTER["TOP10_PLAIN"], places=4)
        self.assertAlmostEqual(float(row.group(2)),
                               US.BARS_IN_REGISTER["TOP10_CAPMATCHED"], places=4)

    def test_it_defines_no_draw_count_or_percentile_of_its_own(self):
        import inspect
        src = inspect.getsource(US)
        for forbidden in ("N_DRAWS =", "PCTILE =", "SEED0 =", "ARMS ="):
            self.assertNotIn(forbidden, src,
                             "%s belongs to the calibration side, not the scorer" % forbidden)

    def test_it_reads_the_arms_from_the_shared_module(self):
        import inspect
        self.assertIn("CE.ARMS", inspect.getsource(US))

    def test_load_bars_refuses_when_the_artifact_disagrees_with_the_register(self):
        import json
        import tempfile
        blob = {"verdict_basis": "SPLIT_CLEAN",
                "bars": {"TOP10_PLAIN": {"bar_pp": 7.2870},
                         "TOP10_CAPMATCHED": {"bar_pp": 99.0}}}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "U1_NULL.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(blob, f)
            real = US.NULL_PATH
            try:
                US.NULL_PATH = p
                with self.assertRaises(SystemExit):
                    US.load_bars()
            finally:
                US.NULL_PATH = real

    def test_load_bars_refuses_a_raw_uncorrected_artifact(self):
        """U1-SPLIT is not optional. An artifact calibrated on the uncorrected grid carries a
        +59.96pp bar and must never be scored against."""
        import json
        import tempfile
        blob = {"verdict_basis": "RAW",
                "bars": {"TOP10_PLAIN": {"bar_pp": 7.2870},
                         "TOP10_CAPMATCHED": {"bar_pp": 9.4513}}}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "U1_NULL.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(blob, f)
            real = US.NULL_PATH
            try:
                US.NULL_PATH = p
                with self.assertRaises(SystemExit):
                    US.load_bars()
            finally:
                US.NULL_PATH = real


class TheVerdictRuleIsTheRegisteredOne(unittest.TestCase):
    """Register section 7 as a truth table. PASS needs all four; a negative gain or a backwards
    decile table is REJECTED; everything else including a near miss is NULL."""

    def test_all_four_conditions_give_pass(self):
        self.assertEqual(US.verdict_of(5.0, True, True, True, True, False), "PASS")

    def test_a_negative_gain_is_rejected(self):
        self.assertEqual(US.verdict_of(-1.19, False, False, False, False, False), "REJECTED")

    def test_a_backwards_decile_table_is_rejected_even_on_a_positive_gain(self):
        self.assertEqual(US.verdict_of(2.0, False, False, False, False, True), "REJECTED")

    def test_positive_but_short_of_a_bar_is_a_null_not_a_near_miss(self):
        self.assertEqual(US.verdict_of(1.02, False, False, False, False, False), "NULL")

    def test_three_of_four_is_still_not_a_pass(self):
        self.assertEqual(US.verdict_of(8.0, True, True, True, False, False), "NULL")
        self.assertEqual(US.verdict_of(8.0, True, False, True, True, False), "NULL")

    def test_pass_requires_the_cap_matched_bar_specifically(self):
        """V2 is the ledger's reopen condition; clearing only the plain bar is not enough."""
        self.assertEqual(US.verdict_of(8.0, True, False, True, True, False), "NULL")


class TheComparisonBooksAreTheBankedOnes(unittest.TestCase):
    def test_it_points_at_the_corrected_r2_book_and_five_control_seeds(self):
        self.assertTrue(US.SIGNAL_BOOK.endswith("state_r2_corrected.pkl"))
        self.assertEqual(len(US.CONTROL_BOOKS), 5)
        for i, p in enumerate(US.CONTROL_BOOKS):
            self.assertTrue(p.endswith("control_r2_seed%d.pkl" % i))

    def test_the_split_filter_is_applied_to_the_comparison_books_too(self):
        """Comparing a split-clean grid against an uncorrected alert book would import the very
        artifact U1-SPLIT removes, and in the direction that flatters the grid."""
        import inspect
        src = inspect.getsource(US.main)
        self.assertIn("drop_split_spanners(alert_raw", src)
        self.assertIn("drop_split_spanners(ctrl_raw", src)


class TheModuleSurvivesACheckoutWithNoLicensedData(unittest.TestCase):
    def test_import_needs_no_grid_and_no_artifact(self):
        import importlib
        m = importlib.import_module("scripts.u1_score")
        self.assertTrue(m.VERDICT_PATH.endswith("U1_VERDICT.json"))
        self.assertEqual(sorted(m.BARS_IN_REGISTER), ["TOP10_CAPMATCHED", "TOP10_PLAIN"])

    def test_the_arms_it_scores_are_the_three_registered_ones(self):
        self.assertEqual(sorted(CE.ARMS), ["BOT10", "TOP10", "TOP20"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
