"""SELL-PREMIUM-2 STAGE 2 - what these tests pin, and why each one exists.

The ONE rationed read of the check quadrant. `RESEARCH_CHARTER.md` Stage 2 and
`PREREG_sellpremium2.md` `T11`. There is no second read, so every guard here is about making a
silent change to the construction impossible after the fact rather than about catching a crash.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **THE BUILD QUADRANT IS BYTE-UNTOUCHED.** Adding `ERA_CHECK` must not move `ERA_BUILD` by a
   field, or every landed stage-1 figure silently describes a different population and the two
   stages stop being comparable. Pinned on the dict itself, not on a date string in prose.

2. **THE CHECK CELL IS THE CHARTER'S CELL.** 2020-2026 and ticker half **1** - the OTHER half.
   If a future edit pointed it at half 0 the "out-of-sample" read would be re-reading the build
   names, which is the one failure this stage exists to prevent and which nothing downstream
   could detect.

3. **THE SIZING LOOP CANNOT REPORT AN IMPOSSIBLE NUMBER.** The first loop returned
   **-$217,426** on a $250,000 cash-secured account by sizing from the STARTING equity forever
   and trading past ruin. **The direction was the UNSAFE one for a rejection** - it made a
   failing leg look worse than it is. Pinned as a PROPERTY (terminal equity is never negative,
   and a book that ruins stops) on a synthetic book built to ruin, with a positive control that
   the loop still trades at all - a loop that refused everything would pass the first half.

4. **THE REPAIR IS INERT ON STAGE 1.** The repaired instrument must be applied to both stages
   or they are not comparable, and stage 1's verdict must not move. Pinned against the
   PUBLISHED artifact rather than against my expectation.

5. **STAGE 3 IS UNAVAILABLE, NOT UNDONE.** Zero chain files before 2016. A future session must
   not read "the proxy was not run" as "the proxy was skipped" - it cannot be run on owned data,
   and the guard carries a positive control so it cannot pass by finding no files at all.

6. **THE STAGE-2 SCRIPT IMPORTS ITS SCORING.** `B7`. At the one look that cannot be repeated, a
   second settlement or sign-test implementation would be unrecoverable. Read from the SYNTAX
   TREE, because a docstring naming the stage-1 module satisfies a grep (`MA49`).

    python tests/test_sellpremium2_stage2.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import re
import sys
import unittest

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import dipcall as D  # noqa: E402

_SKIPS = []


def _art(name):
    p = D.out_path(name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


class TestTheQuadrants(unittest.TestCase):
    """(1) and (2). The two cells, pinned on the dict rather than on prose."""

    def test_the_build_quadrant_is_untouched_by_adding_the_check_one(self):
        b = D.ERAS[D.ERA_BUILD]
        self.assertEqual(b["lo"], "2009-01-01")
        self.assertEqual(b["hi"], "2019-12-31")
        self.assertEqual(b["ticker_half"], 0)

    def test_the_check_cell_is_the_charters_cell_and_is_the_other_half(self):
        c = D.ERAS[D.ERA_CHECK]
        self.assertEqual(c["lo"], "2020-01-01")
        self.assertEqual(c["hi"], "2026-12-31")
        self.assertEqual(c["ticker_half"], 1,
                         "the check read must use the OTHER ticker half or it re-reads build")
        self.assertNotEqual(c["ticker_half"], D.ERAS[D.ERA_BUILD]["ticker_half"])
        self.assertEqual(c["tier_panel"], D.ERAS[D.ERA_BUILD]["tier_panel"],
                         "same tier panel - only the window and the half may move")


class TestTheSizingLoop(unittest.TestCase):
    """(3). The defect that exaggerated a rejection, pinned as a property."""

    @staticmethod
    def _grid(*a, **k):
        from scripts.sellpremium2_sizing_fix import grid
        return grid(*a, **k)

    @staticmethod
    def _book(rets):
        return pd.DataFrame({
            "date": ["2020-01-%02d" % (i + 1) for i in range(len(rets))],
            "expiration": ["2020-01-%02d" % (i + 2) for i in range(len(rets))],
            "secured": [1000.0] * len(rets),
            "ret_pct": list(rets),
        })

    def test_a_cash_secured_book_can_never_report_negative_equity(self):
        # every trade a total loss of the strike, far more of them than the account can fund
        c = self._grid(self._book([-100.0] * 400), 10000.0, 10)
        self.assertGreaterEqual(c["terminal_equity"], 0.0,
                                "a cash-secured book cannot owe money it never borrowed")
        self.assertFalse(c["survives"])

    def test_a_book_that_runs_out_of_money_stops_trading(self):
        c = self._grid(self._book([-100.0] * 400), 10000.0, 10)
        # sizing from CURRENT equity makes the position shrink, so it cannot take all 400
        self.assertLess(c["taken"], 400)
        self.assertGreater(c["affordability_skips"] + c["concurrency_skips"], 0)

    def test_positive_control_the_loop_does_trade(self):
        # or the first two tests would pass on a loop that refuses everything
        c = self._grid(self._book([+5.0] * 50), 100000.0, 50)
        self.assertGreater(c["taken"], 0)
        self.assertTrue(c["survives"])
        self.assertGreater(c["terminal_equity"], 100000.0)

    def test_ruin_is_its_own_recorded_state_beside_mb3s_two_skip_reasons(self):
        c = self._grid(self._book([+5.0] * 5), 100000.0, 50)
        for k in ("ruined", "ruined_on", "affordability_skips", "concurrency_skips"):
            self.assertIn(k, c, "an affordability skip is never a concurrency skip, and "
                                "neither is ruin")


class TestTheRepairIsInertOnStageOne(unittest.TestCase):
    """(4). Against the PUBLISHED artifact, not against my expectation."""

    def test_stage_one_still_survives_every_cell_on_the_repaired_loop(self):
        fix = _art("SELLPREMIUM2_SIZING_FIX.json")
        pub = _art("SELLPREMIUM2_ARM.json")
        if fix is None or pub is None or "stage1" not in fix:
            _SKIPS.append("stage-1 sizing artifacts absent (licensed data); not a pass")
            self.skipTest("artifacts absent")
        self.assertTrue(fix["stage1_all_survive"],
                        "the repair must not move stage 1's verdict")
        published = pub["survivability_clause_c"]
        self.assertEqual(sorted(fix["stage1"]), sorted(published),
                         "the repaired grid must cover the same eight cells")
        for k, v in published.items():
            self.assertTrue(v["survives"])
            self.assertTrue(fix["stage1"][k]["survives"], k)


class TestStageThreeIsUnavailableNotUndone(unittest.TestCase):
    """(5). With a positive control, or it passes by finding nothing at all."""

    def test_there_are_no_option_chains_before_2016(self):
        from valuation.studies import sellpremium as SP
        root = SP.chain_dir()
        if not os.path.isdir(root):
            _SKIPS.append("options chain cache absent (licensed data); not a pass")
            self.skipTest("cache absent")
        years = set()
        for t in os.listdir(root):
            d = os.path.join(root, t)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                m = re.match(r"^.+-(\d{4})\.pkl$", f)
                if m:
                    years.add(int(m.group(1)))
        self.assertTrue(years, "positive control: the cache must contain SOME years, or this "
                               "guard passes by looking at an empty directory")
        self.assertFalse([y for y in years if y < 2016],
                         "an option cannot be priced where no chain exists, so the 1999-2008 "
                         "proxy is UNAVAILABLE to an options construction rather than skipped")


class TestTheStageTwoScriptImportsItsScoring(unittest.TestCase):
    """(6). From the syntax tree, never from a grep."""

    def test_settlement_and_the_sign_test_are_imported_not_reimplemented(self):
        p = os.path.join(REPO, "scripts", "sellpremium2_stage2.py")
        with io.open(p, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                if isinstance(n, ast.ImportFrom) and n.module:
                    imported.add(n.module.split(".")[-1])
                for a in n.names:
                    imported.add(a.name.split(".")[-1])
        self.assertIn("sellpremium2_arm", imported,
                      "B7: stage 2 must score with stage 1's own primitives")
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("settle", "sign_test", "spot_maps"):
            self.assertNotIn(banned, defined,
                             "%s is stage 1's; a second implementation at the one look that "
                             "cannot be repeated would be unrecoverable" % banned)


class TestTheVerdictAsMeasured(unittest.TestCase):
    """The artifact says what the record says. `MA13`'s committed-literal idiom."""

    def test_stage_two_is_not_confirmed_and_names_which_clauses_failed(self):
        a = _art("SELLPREMIUM2_STAGE2_ARM.json")
        if a is None:
            _SKIPS.append("stage-2 arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        self.assertIn("NOT CONFIRMED", a["label"].upper())
        c = a["verdict_checks"]
        self.assertFalse(c["clause_a_profitable_both_halves"])
        self.assertFalse(c["clause_c_survives_sizing"])
        self.assertTrue(c["clause_b_beats_random_day"])
        self.assertTrue(c["clause_d_K3_crash_stress"])

    def test_the_crash_stress_passed_while_the_window_held_a_real_crash(self):
        # void condition 7 of the register, as an assertion rather than as prose
        a = _art("SELLPREMIUM2_STAGE2_ARM.json")
        if a is None:
            _SKIPS.append("stage-2 arm artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        self.assertTrue(a["verdict_checks"]["clause_d_K3_crash_stress"])
        crash = a["crash_in_the_scored_window"]
        self.assertTrue(crash["contains_a_30pc_crash"],
                        "the ELIGIBLE-BUT-UNRESOLVED label's own reason is resolved here")
        self.assertLess(crash["worst_32_session_spy_return_in_the_scored_window"], -0.30)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
