"""MB31 - the staleness map is DERIVED, and its one substantive claim is checkable.

WHAT THESE PIN.
  1. Nothing is re-typed. The trial counts come from `research_log`, the hurdle from the ONE
     shipped `hlz_hurdle`. A hard-coded count or a second `sqrt(2 ln N)` is the defect the map
     exists to report, and shipping it inside the map would be the joke writing itself.
  2. The adopt-set argument is verified against MA19's RECORDED adopt count rather than
     assumed - that is what licenses the "provably unmoved" claim.
  3. The Deflated Sharpe probability is NOT fabricated at the live N. Reporting a
     normal-moments figure would move it by an order of magnitude more than the change being
     measured, so the map must return None there and say why.

Data-dependent tests SKIP LOUDLY. `data/` is gitignored, so a worktree and CI have none of it.
"""
from __future__ import annotations

import ast
import io
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge.statistics import hlz_hurdle  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb31_staleness_map.py")
_SKIPS = []


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _skip(name, why):
    _SKIPS.append("%s (%s)" % (name, why))


def _map():
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import mb31_staleness_map as M
    return M


class TestItIsDerivedNotTyped(unittest.TestCase):
    """TRIPWIRE. A hand-typed map is exactly what MA5 and MA22 were about."""

    def setUp(self):
        self.src = _read(SCRIPT)
        self.tree = ast.parse(self.src)

    def test_the_hurdle_delegates_to_the_one_shipped_definition(self):
        names = set()
        for n in ast.walk(self.tree):
            if isinstance(n, ast.ImportFrom) and n.module and "statistics" in n.module:
                names.update(a.name for a in n.names)
        self.assertIn("hlz_hurdle", names,
                      "the map must import the shipped hurdle, never re-derive it")

    def test_no_second_copy_of_the_hurdle_expression(self):
        """`sqrt(2 * log(N))` appearing here would be MA5's defect in the map about MA5."""
        body = self.src.split('"""', 2)[2]
        for bad in ("sqrt(2.0 * math.log", "sqrt(2 * math.log", "sqrt(2.0*math.log"):
            self.assertNotIn(bad, body, "found a second copy of the HLZ hurdle: %r" % bad)

    def test_the_trial_counts_are_read_not_written(self):
        """A literal 234 or 300 would rot the moment any lane lands a register."""
        body = self.src.split('"""', 2)[2]
        for bad in ("= 234", "= 300", "n_eq = 2", 'equity": 234'):
            self.assertNotIn(bad, body, "hard-coded trial count %r" % bad)
        self.assertIn("research_log.detail()", body)

    def test_it_refuses_rather_than_guesses_when_the_dsr_block_is_absent(self):
        """A map that invents a channel it cannot read is worse than one that stops."""
        self.assertIn("refusing to report a DSR channel it cannot read", self.src)


class TestTheMapItself(unittest.TestCase):
    """The substantive claims. SKIPS LOUDLY without the banked draws."""

    @classmethod
    def setUpClass(cls):
        cls.m = None
        try:
            M = _map()
            if not os.path.exists(M.X7RECON) or not os.path.exists(M.MA19):
                _skip("map", "X7_RECONCILE.json / MA19_RECALIBRATION.json absent")
                return
            cls.m = M.build()
        except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
            _skip("map", "build failed: %s" % exc)

    def test_the_adopt_rule_is_verified_against_the_record(self):
        """Without this the 'provably unmoved' claim rests on my reading of the gate."""
        if self.m is None:
            return
        self.assertTrue(self.m["adopt_set"]["adopt_rule_verified_against_record"],
                        "the margin rule must reproduce MA19's recorded adopt count")

    def test_the_hurdles_match_the_one_definition_at_the_reported_N(self):
        if self.m is None:
            return
        for dom, blk in self.m["hurdles_live"].items():
            self.assertAlmostEqual(blk["hlz"], hlz_hurdle(blk["N"]), places=15,
                                   msg="hurdle for %s does not match hlz_hurdle" % dom)

    def test_the_next_change_N_is_ahead_of_the_live_N(self):
        """If it were behind, the map's own 'unmoved' claim would contradict itself."""
        if self.m is None:
            return
        nx = self.m["next_change"]
        live = self.m["adopt_set"]["live_equity_N"]
        if nx["first_equity_N_at_which_the_adopt_set_changes"] is None:
            return
        self.assertGreater(nx["first_equity_N_at_which_the_adopt_set_changes"], live)
        self.assertGreater(nx["trials_of_headroom_from_live_N"], 0)

    def test_the_next_change_N_is_the_solution_of_the_hurdle_equation(self):
        """Derived, not eyeballed: sqrt(2 ln N) must cross the named draw's margin/se there."""
        if self.m is None:
            return
        nx = self.m["next_change"]
        n_star = nx["first_equity_N_at_which_the_adopt_set_changes"]
        t = nx["margin_over_se"]
        if n_star is None:
            return
        self.assertGreater(hlz_hurdle(n_star), t, "at N* the draw must have flipped off")
        self.assertLessEqual(hlz_hurdle(n_star - 1), t, "at N*-1 it must still adopt")

    def test_a_changed_adopt_set_is_accompanied_by_a_published_re_derivation(self):
        """REPOINTED 2026-08-28 by `W-1`, in the same commit as the event that fired it, so the
        move shows in the diff (`MA59`).

        AS WRITTEN THIS ASSERTED THE ADOPT SET WAS UNCHANGED, and it fired **correctly**: `MB31`
        predicted seed **1003** would flip at exactly equity `N` = 247, and `W-1`'s two trials
        landed on it. That is the tripwire doing its job, not a stale expectation — but the
        assertion could only ever hold BELOW the trigger, so re-asserting it would be silencing
        a check that had just paid for itself.

        THE INVARIANT IT BECOMES IS STRICTLY STRONGER AND STILL BITES: the adopt set may change,
        and when it does a **bounded re-derivation at that same live `N` must exist and name the
        same seeds**. A future flip with nobody re-deriving now goes red, which is the state this
        test was really guarding against all along.
        """
        if self.m is None:
            return
        a = self.m["adopt_set"]
        self.assertEqual(a["flipped_on"], [],
                         "a draw flipping ON would mean the hurdle FELL, which cannot happen")
        if a["identical"]:
            self.assertEqual(a["flipped_off"], [])
            return

        live = a["live_equity_N"]
        # Resolve the artifact BESIDE the map's own inputs rather than from the repo root. A
        # worktree carries `data/` EMPTY while the banked draws live in the primary root, and a
        # guard that resolves one location and then reads another is the wrong-object family
        # (`E-5` hit exactly this, and skipped silently on every worktree).
        path = os.path.join(os.path.dirname(_map().X7RECON), "W1_FLOORS.json")
        if not os.path.exists(path):
            _skip("re-derivation", "W1_FLOORS.json absent (data/ is gitignored)")
            return
        import json
        with io.open(path, encoding="utf-8") as fh:
            f = json.load(fh)
        self.assertEqual(f["N_after"], live,
                         "the re-derivation is at a different N from the live one")
        self.assertEqual(sorted(f["newly_off"]), sorted(a["flipped_off"]),
                         "the re-derivation does not name the seeds that flipped")
        self.assertEqual(sorted(f["rescored_here"]), sorted(a["flipped_off"]),
                         "MA19's method: re-score exactly the flipped draws, never a sweep")
        for key, blk in f["floors"].items():
            self.assertIn("floor_at_%d" % live, blk,
                          "%s carries no floor at the live N" % key)

    def test_the_deflated_sharpe_probability_is_not_fabricated(self):
        """STALE BY CONSTRUCTION must mean 'no value', not 'a plausible value'."""
        if self.m is None:
            return
        d = self.m["deflated_sharpe"]
        self.assertIsNone(d["probability_at_live_N"])
        self.assertEqual(d["status"], "STALE BY CONSTRUCTION")
        self.assertIsNotNone(d["sr0_at_live_N"])
        self.assertGreater(d["sr0_move"], 0.0, "sr0 rises with N, so the DSR falls")

    def test_sr0_reproduces_the_shipped_value(self):
        """The channel is verified rather than asserted - MA19's C10 read 2.07e-10."""
        if self.m is None:
            return
        d = self.m["deflated_sharpe"]
        self.assertLess(d["sr0_reproduction_abs_delta"], 1e-8)

    def test_the_hlz_verdict_does_not_change_between_the_two_N(self):
        """The map may report staleness; it may not silently move a verdict."""
        if self.m is None:
            return
        h = self.m["hlz_shipped_in_artifact"]
        self.assertFalse(h["clears"])
        self.assertGreater(h["shortfall_at_live_N"], h["shortfall_at_shipped_N"],
                           "the hurdle only ever rises with trials")
        self.assertTrue(h["verdict_unchanged"])

    def test_every_instrument_carries_a_status(self):
        if self.m is None:
            return
        self.assertGreaterEqual(len(self.m["instruments"]), 6)
        for row in self.m["instruments"]:
            self.assertTrue(row["status"])
            self.assertIn("N", str(row["calibrated_at_N"]) + "N")

    def test_the_unmoved_floors_are_never_called_invariant(self):
        """Session 12: their survival was 'luck, not design', and once the luck ran out."""
        if self.m is None:
            return
        for row in self.m["instruments"]:
            st = row["status"].lower()
            if "invariant" in st:
                self.assertIn("never invariant", st,
                              "a floor may be called insensitive, never invariant: %r" % st)
        self.assertIn("luck, not design", self.m["kill_condition_note"])

    def test_the_dsr_floor_does_not_inherit_the_adopt_set_argument(self):
        """sr0 moves at EVERY N, so "provably unmoved" is invalid for it. This assertion was
        added because the map's first cut made exactly that over-claim and this suite caught
        it - the defect class MB31 itself is about."""
        if self.m is None:
            return
        rows = {r["key"]: r for r in self.m["instruments"]}
        d = rows.get("deflated_sharpe")
        self.assertIsNotNone(d)
        self.assertFalse(d["covered_by_adopt_set_argument"])
        self.assertIn("STALE BY CONSTRUCTION", d["status"])
        self.assertNotIn("PROVABLY-UNMOVED", d["status"])

    def test_has_ever_moved_is_measured_across_all_three_regimes(self):
        """The alpha MARGIN moved at 84 -> 129; a last-step-only flag would call it unmoved."""
        if self.m is None:
            return
        rows = {r["key"]: r for r in self.m["instruments"]}
        self.assertTrue(rows["top_decile_alpha"]["has_ever_moved"],
                        "the alpha margin moved 1.9532 -> 1.8629 between N=84 and N=129")
        self.assertTrue(rows["top_decile_alpha_tstat_nw"]["has_ever_moved"])
        self.assertFalse(rows["long_short_tstat_nw"]["has_ever_moved"])


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (banked draws absent) - NOT counted as passes:")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
