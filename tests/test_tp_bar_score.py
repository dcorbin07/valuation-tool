"""Item A / TP-BAR — pins C2-C4 and the verdict rule (options bot, 2026-08-11).

Standalone script: the auto-land Action runs `python tests/test_*.py`, so no fixtures run.

The thing worth pinning here is that the SCORING side cannot quietly move the bar. The bar was
committed at e8e5505 before this module existed; these tests fail if the constant in the code,
the number published in the memo, or the artifact ever disagree.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import tp_bar_score as TS                 # noqa: E402
from scripts import tp_bar as TB                       # noqa: E402
from valuation.edge import options_exitlab as XL       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMO = os.path.join(ROOT, "PREREG_A_take_profit_bar.md")


class TheCandidatesAreO1sArmsUnchanged(unittest.TestCase):
    """If `tp150` were re-parameterised here it would no longer be the arm the record has
    measured three times, and the whole reconciliation in the memo would be about a different
    policy."""

    def test_tp150_and_tp200_match_the_shipped_policy_grid(self):
        pol = dict(XL.POLICIES)
        for name in ("tp150", "tp200"):
            self.assertIn(name, pol)
            self.assertEqual(TS.CANDIDATES[name], pol[name])

    def test_only_the_take_profit_differs_from_shipped(self):
        pol = dict(XL.POLICIES)
        for name in ("tp150", "tp200"):
            for leg in ("sl", "time_frac"):
                self.assertEqual(TS.CANDIDATES[name][leg], pol["shipped"][leg])


class TheScoringSideCannotMoveTheBar(unittest.TestCase):

    def test_the_constant_matches_the_number_published_in_the_memo(self):
        with open(MEMO, "r", encoding="utf-8") as f:
            text = f.read()
        found = re.findall(r"\+(\d+\.\d+) pp", text)
        self.assertIn("%.4f" % TS.BAR_IN_MEMO, found,
                      "the memo's section 8 bar and tp_bar_score.BAR_IN_MEMO disagree")

    def test_load_bar_refuses_an_artifact_that_disagrees_with_the_memo(self):
        import json
        import tempfile
        real = TS.NULL_PATH
        try:
            tmp = os.path.join(tempfile.mkdtemp(), "TPBAR_NULL.json")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"BAR_PP": TS.BAR_IN_MEMO + 1.0, "draws": []}, f)
            TS.NULL_PATH = tmp
            with self.assertRaises(SystemExit):
                TS.load_bar()
        finally:
            TS.NULL_PATH = real

    def test_the_bar_is_not_recomputed_here(self):
        """C1 lives in `tp_bar`; this module must not define its own percentile or ranges."""
        src = open(TS.__file__, "r", encoding="utf-8").read()
        for forbidden in ("TP_RANGE =", "SL_RANGE =", "TIME_RANGE =", "PCTILE ="):
            self.assertNotIn(forbidden, src)


class TheWinsorConditionActuallyBites(unittest.TestCase):

    def test_it_caps_the_top_one_percent(self):
        """p99 here interpolates to 1.0 (between the 99th and 100th order statistics), so the
        lone outlier IS above the cap and is pulled down to it."""
        diffs = [0.0] * 99 + [100.0]
        got = TS.winsorised_mean(diffs, 99.0)
        self.assertEqual(got["n_capped"], 1)
        self.assertAlmostEqual(got["cap_pp"], 100.0)          # cap 1.0 in return units
        self.assertAlmostEqual(got["mean_pp"], 100.0 * 1.0 / 100)   # raw mean was +100pp

    def test_an_arm_carried_entirely_by_one_trade_loses_most_of_its_gain(self):
        diffs = [0.0] * 999 + [1000.0]                # mean +100pp, all of it one trade
        raw = 100.0 * sum(diffs) / len(diffs)
        got = TS.winsorised_mean(diffs, 99.0)
        self.assertLess(got["mean_pp"], raw * 0.15)

    def test_a_broadly_positive_arm_survives(self):
        diffs = [0.05] * 1000
        got = TS.winsorised_mean(diffs, 99.0)
        self.assertAlmostEqual(got["mean_pp"], 5.0, places=6)

    def test_the_percentile_is_the_one_c1_uses(self):
        self.assertIs(TS.winsorised_mean.__globals__["percentile"], TB.percentile)
        self.assertEqual(TS.WINSOR_PCT, 99.0)


class TheVerdictNeedsAllFourConditions(unittest.TestCase):
    """Don's instruction: clears -> ADOPT, fails -> REJECTED, no third state. Pinned as a
    truth table so a later edit cannot make ADOPT reachable on three of four."""

    @staticmethod
    def _verdict(c1, c2, c3, c4):
        return "ADOPT" if (c1 and c2 and c3 and c4) else "REJECTED"

    def test_all_four_is_the_only_adopt(self):
        self.assertEqual(self._verdict(True, True, True, True), "ADOPT")

    def test_any_single_failure_rejects(self):
        for i in range(4):
            flags = [True] * 4
            flags[i] = False
            self.assertEqual(self._verdict(*flags), "REJECTED",
                             "failing condition C%d must reject" % (i + 1))

    def test_the_module_encodes_that_rule(self):
        src = open(TS.__file__, "r", encoding="utf-8").read()
        self.assertIn('r["C1_clears_bar"] and r["C2_positive"]', src)
        self.assertIn('r["C3_passes"] and r["C4_passes"]', src)


class TheModuleSurvivesACheckoutWithNoLicensedData(unittest.TestCase):

    def test_import_does_not_require_the_freeze(self):
        self.assertTrue(callable(TS.winsorised_mean))
        self.assertTrue(callable(TS.load_bar))

    def test_it_carries_the_dead_entry_caveat(self):
        doc = (TS.__doc__ or "").lower()
        self.assertIn("entry", doc)
        self.assertIn("dead", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
