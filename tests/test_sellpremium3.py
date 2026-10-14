"""SELL-PREMIUM-3 - what these tests pin, and why each one exists.

Register: `PREREG_sellpremium3.md`, committed ALONE at `5f61820`, trials booked at `b31e2a6`.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **THE SETTLEMENT IS THE REPAIRED ONE, ON BOTH LEGS** (amendment `A1`). A spread settles two
   legs, so the stale-map defect that VOIDED `SELL-PREMIUM-2`'s stage 2 would be inherited
   twice over. Pinned from the SYNTAX TREE: no era constant reaches the spot maps, and every
   `settlement_spot` call states its limit.

2. **THE WIDTH BAND IS A REFUSAL, NEVER A SUBSTITUTION.** Outside 5%-12.5% the trade does not
   happen. If a future edit made it clamp to the nearest available strike instead, the book
   would silently acquire the 2.5%-wide spreads the draft measured as NEGATIVE before costs.

3. **THE LONG LEG IS AT OR BELOW THE TARGET, NEVER ABOVE IT.** A strike above `K_short - 7.5%`
   is a NARROWER spread than declared, which is the losing direction; the rule's own asymmetry.

4. **EXERCISING THE LONG PUT IS REFUSED - THE SHARES ARE SOLD.** Void condition 4. Pinned on
   the arithmetic: in the assignment band the loss must be `K_short - S` plus the equity cost,
   never the full width.

5. **THE HURDLE IS DERIVED AT RUN TIME, NEVER THE DRAFT'S 319** (`A2`, `MA19`). Pinned by
   requiring the artifact's own `options_N` to match the live log and its hurdle to match
   `hlz_hurdle` of that N.

6. **THE 100%-DEPLOYMENT ROWS ARE NEVER OFFERED** (void 9), and the account table says so per
   row rather than in prose somewhere else.

    python tests/test_sellpremium3.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import dipcall as D  # noqa: E402

_SKIPS = []


def _art(name):
    if D.data_root(required=False) is None:
        return None
    p = D.out_path(name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class TestTheRepairedSettlementOnBothLegs(unittest.TestCase):
    """(1). From the syntax tree, because a docstring explaining the rule satisfies a grep."""

    def test_no_era_constant_reaches_the_spot_maps(self):
        for rel in ("scripts/sellpremium3.py", "scripts/sellpremium3_arms.py"):
            tree = ast.parse(_src(rel))
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "spot_maps":
                    self.assertEqual(len(n.args), 2,
                                     "%s must pass its years explicitly" % rel)
                    # and the years must come from the trades
                    self.assertTrue(
                        any(isinstance(a, ast.Call)
                            and getattr(a.func, "attr", "") == "years_spanning"
                            or (isinstance(a, ast.Name) and "year" in a.id)
                            for a in n.args[1:]),
                        "%s must derive its years from the trades" % rel)

    def test_every_settlement_call_states_its_limit(self):
        for rel in ("scripts/sellpremium3.py", "scripts/sellpremium3_arms.py"):
            for n in ast.walk(ast.parse(_src(rel))):
                if (isinstance(n, ast.Call)
                        and getattr(n.func, "attr", None) == "settlement_spot"):
                    self.assertIn("max_stale_days", {k.arg for k in n.keywords}, rel)

    def test_the_arm_counts_its_settlement_refusals(self):
        self.assertIn("refused", _src("scripts/sellpremium3_arms.py"),
                      "a refusal that is not counted is the defect that voided stage 2")


class TestTheWidthBandIsARefusal(unittest.TestCase):
    """(2) and (3)."""

    @staticmethod
    def _rows(strikes):
        import pandas as pd
        return pd.DataFrame({"expiration": ["2018-03-16"] * len(strikes),
                             "strike": [float(s) for s in strikes],
                             "bid": [1.0] * len(strikes),
                             "ask": [1.2] * len(strikes)})

    def test_a_strike_only_outside_the_band_is_REFUSED_not_substituted(self):
        from scripts.sellpremium3 import long_leg
        # spot 100, K_short 95, target 87.5; the only lower strike is 60 -> width 35% -> refuse
        self.assertIsNone(long_leg(self._rows([60.0]), "2018-03-16", 95.0, 100.0))
        # and one just 2% below -> too NARROW -> also refused
        self.assertIsNone(long_leg(self._rows([93.0]), "2018-03-16", 95.0, 100.0))

    def test_positive_control_a_strike_inside_the_band_is_taken(self):
        from scripts.sellpremium3 import long_leg
        got = long_leg(self._rows([87.0]), "2018-03-16", 95.0, 100.0)
        self.assertIsNotNone(got)
        self.assertAlmostEqual(got["strike"], 87.0)
        self.assertAlmostEqual(got["width_frac"], 0.08)

    def test_the_long_strike_is_AT_OR_BELOW_the_target_never_above(self):
        from scripts.sellpremium3 import long_leg
        # 88 is ABOVE the 87.5 target and 87 is below; the rule must take 87
        got = long_leg(self._rows([87.0, 88.0]), "2018-03-16", 95.0, 100.0)
        self.assertAlmostEqual(got["strike"], 87.0,
                               msg="a strike above the target is a NARROWER spread than "
                                   "declared, which is the losing direction")

    def test_a_one_sided_quote_on_the_long_leg_is_refused(self):
        import pandas as pd
        from scripts.sellpremium3 import long_leg
        d = pd.DataFrame({"expiration": ["2018-03-16"], "strike": [87.0],
                          "bid": [0.0], "ask": [1.2]})
        self.assertIsNone(long_leg(d, "2018-03-16", 95.0, 100.0))


class TestTheAssignmentBandSellsTheShares(unittest.TestCase):
    """(4). Void condition 4, pinned on the arithmetic rather than on a comment."""

    SHORT = {"strike": 95.0, "bid": 2.00}
    LONG = {"strike": 87.0, "ask": 0.50}

    def test_both_worthless_keeps_the_whole_credit(self):
        from scripts.sellpremium3 import settle_spread
        g = settle_spread(self.SHORT, self.LONG, 99.0)
        self.assertEqual(g["band"], "both_worthless")
        self.assertAlmostEqual(g["pnl"], 1.50)
        self.assertAlmostEqual(g["equity_cost"], 0.0)

    def test_the_middle_band_loses_only_to_the_spot_and_pays_the_equity_cost(self):
        from scripts.sellpremium3 import settle_spread, EQUITY_BPS_ONE_WAY, EQUITY_CROSSINGS
        g = settle_spread(self.SHORT, self.LONG, 91.0)
        self.assertEqual(g["band"], "assigned_long_worthless")
        expect_cost = EQUITY_CROSSINGS * EQUITY_BPS_ONE_WAY * 95.0
        self.assertAlmostEqual(g["equity_cost"], expect_cost)
        self.assertAlmostEqual(g["pnl"], 1.50 - 4.0 - expect_cost)
        self.assertGreater(g["pnl"], 1.50 - g["width"],
                           "exercising the long put would lock the FULL width here; selling "
                           "the shares must be strictly better (void 4)")

    def test_below_the_long_strike_the_loss_is_capped_at_the_width(self):
        from scripts.sellpremium3 import settle_spread
        g = settle_spread(self.SHORT, self.LONG, 50.0)
        self.assertEqual(g["band"], "both_exercise")
        self.assertAlmostEqual(g["pnl"], 1.50 - 8.0)
        self.assertAlmostEqual(g["equity_cost"], 0.0,
                               msg="nothing is assigned-and-sold when both legs exercise")

    def test_both_capital_denominators_are_reported(self):
        from scripts.sellpremium3 import settle_spread
        g = settle_spread(self.SHORT, self.LONG, 99.0)
        self.assertAlmostEqual(g["capital_draft"], (8.0 - 1.50) * 100.0)
        self.assertAlmostEqual(g["capital_broker"], 8.0 * 100.0)
        self.assertGreater(g["capital_broker"], g["capital_draft"],
                           "Fidelity nets no credit, so its requirement is the larger (A4)")


class TestTheHurdleIsDerived(unittest.TestCase):
    """(5)."""

    def test_the_artifact_carries_a_hurdle_derived_from_its_own_N(self):
        a = _art("SELLPREMIUM3_ARM.json")
        if a is None:
            _SKIPS.append("arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        from valuation.edge.statistics import hlz_hurdle
        self.assertAlmostEqual(a["hlz_hurdle"], hlz_hurdle(a["options_N"]), places=9)
        self.assertNotEqual(a["options_N"], 319,
                            "319 is the DRAFT's figure and A2 forbids quoting it")

    def test_no_script_hard_codes_the_drafts_hurdle(self):
        for rel in ("scripts/sellpremium3.py", "scripts/sellpremium3_arms.py"):
            for n in ast.walk(ast.parse(_src(rel))):
                if isinstance(n, ast.Constant) and isinstance(n.value, float):
                    self.assertNotAlmostEqual(n.value, 3.3956416, places=5,
                                              msg="%s retypes the draft's hurdle" % rel)


class TestTheAccountTableRefusesTheUnofferedRows(unittest.TestCase):
    """(6). Void condition 9, per row."""

    def test_only_the_35pc_cap_rows_are_marked_offered(self):
        a = _art("SELLPREMIUM3_ARM.json")
        if a is None:
            _SKIPS.append("arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        tbl = a["account_table"]
        self.assertTrue(tbl)
        for k, v in tbl.items():
            self.assertIn("offered", v, k)
            self.assertEqual(v["offered"], "35pc_cap" in k, k)
        self.assertTrue(any(v["offered"] for v in tbl.values()),
                        "positive control: some row must be offered, or this passes vacuously")


class TestTheVerdictAsMeasured(unittest.TestCase):
    """The record and the artifact must not drift apart."""

    def test_stage_one_is_not_confirmed_and_underpowered(self):
        a = _art("SELLPREMIUM3_ARM.json")
        if a is None:
            _SKIPS.append("arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        self.assertFalse(a["passes"])
        self.assertIn("NOT CONFIRMED", a["label"].upper())
        self.assertIn("UNDERPOWERED", a["label"].upper())
        self.assertEqual(a["B1_clause_a"]["three_state"], "UNDERPOWERED")
        self.assertEqual(a["B2_clause_b"]["three_state"], "CLEARS")

    def test_no_B1_cell_reaches_its_own_detection_threshold(self):
        a = _art("SELLPREMIUM3_ARM.json")
        if a is None:
            _SKIPS.append("arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        for k, v in a["B1_clause_a"]["mde_ratios"].items():
            self.assertLess(v["observed_over_mde80"], 1.0, k)

    def test_the_check_quadrant_was_not_opened(self):
        a = _art("SELLPREMIUM3_ARM.json")
        if a is None:
            _SKIPS.append("arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        self.assertIn("NOT TAKEN", a["stage2_read"])
        self.assertIsNone(_art("SELLPREMIUM3_STAGE2_ARM.json"),
                          "stage 1 did not pass, so no stage-2 artifact may exist")

    def test_the_kills_floor_is_the_registers_and_was_cleared_on_the_two_leg_rule(self):
        k = _art("SELLPREMIUM3_KILLS.json")
        if k is None:
            _SKIPS.append("kills artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        self.assertEqual(k["K1"]["floor_events"], 1200)
        self.assertEqual(k["K1"]["floor_days"], 300)
        self.assertTrue(k["K1"]["pass"])
        self.assertTrue(k["all_kills_pass"])
        self.assertEqual(k["K3_POS"]["bar"], 6.0, "the 6.0 bar is unrelaxed (void 2)")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
