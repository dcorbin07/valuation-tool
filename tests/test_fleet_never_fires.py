"""RULE_ARMED_NEVER_FIRES — the Frontier Scout's third harness state (session 9).

**THE DEFECT, ONE LEVEL FURTHER OUT THAN THE TWO ALREADY CAUGHT.** `cycle()` separates *"no
rule is built"* from *"the rule ran and nobody qualified"*. It does NOT separate the second
from **"the rule CANNOT qualify anybody, ever"** — and F-4 is exactly that: its event-free
clause asks a backward filing record for a forward date, so it **arms cleanly, runs every
cycle, places nothing, and reports a skip rate of 1.0**, which is indistinguishable from a
quiet market in the records. F-13's version refuses loudly at arming; **F-4's is
satisfiable-looking and always false, which is worse because it is quiet.**

**IT CANNOT CRY WOLF, and that is the property that makes it shippable** rather than a warning
switched off in week one (`MA21`'s standard, and the reason that one was declined). A rule that
has selected nothing across many consecutive cycles is a FACT ABOUT THE RULE — the alarm says
*"this has never fired"*, which is true, and says nothing about whether it should have.

    python tests/test_fleet_never_fires.py
"""
from __future__ import annotations

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                          # noqa: E402
from test_fleet_harness import _repo, _seed_selfcheck, BOOK, _sha   # noqa: E402


def _fill(sym="AAA"):
    return F.fill_fields(symbol=sym, occ=sym + "1", side="buy_to_open", qty=1,
                         order_type="market", quote={"bid": 1.0, "ask": 1.2},
                         order={"status": "filled", "avg_fill_price": 1.2,
                                "exec_quantity": 1, "quantity": 1},
                         submitted_ts="2026-08-25T15:00:00")


class TheThirdState(unittest.TestCase):

    def setUp(self):
        self.root = _repo(book=BOOK)
        _seed_selfcheck(self.root, BOOK)
        self.sha = _sha(self.root, BOOK)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _skip(self, n):
        for i in range(n):
            F.record(BOOK, "skip",
                     F.skip_fields(symbol="S%d" % i, skip_reason="next event UNKNOWN"),
                     decl_sha=self.sha, root=self.root)

    def test_a_brand_new_book_is_OK_and_not_accused(self):
        """Zero observations is not evidence of anything. An alarm that fires on day one is
        an alarm nobody keeps."""
        nf = F.never_fires(BOOK, self.root)
        self.assertEqual(nf["state"], "OK")
        self.assertEqual(nf["observations"], 0)
        self.assertIsNone(nf["skip_rate"])

    def test_a_few_empty_cycles_are_still_OK(self):
        """A quiet week is a quiet week. The state is about MANY cycles, not a slow one."""
        self._skip(F.NEVER_FIRES_AFTER - 1)
        self.assertEqual(F.never_fires(BOOK, self.root)["state"], "OK")

    def test_enough_cycles_with_ZERO_fills_raises_the_state(self):
        self._skip(F.NEVER_FIRES_AFTER)
        nf = F.never_fires(BOOK, self.root)
        self.assertEqual(nf["state"], "RULE_ARMED_NEVER_FIRES")
        self.assertEqual(nf["fired"], 0)
        self.assertEqual(nf["skip_rate"], 1.0)
        self.assertIn("NEVER FILLED", nf["reason"])

    def test_ONE_fill_clears_it_however_many_skips_surround_it(self):
        """The claim is 'this rule has never fired', so a single fill refutes it outright.
        A rule that fires RARELY must not be accused of being unable to fire."""
        self._skip(F.NEVER_FIRES_AFTER * 3)
        F.record(BOOK, "fill", _fill(), decl_sha=self.sha, root=self.root)
        self._skip(F.NEVER_FIRES_AFTER * 3)
        nf = F.never_fires(BOOK, self.root)
        self.assertEqual(nf["state"], "OK")
        self.assertEqual(nf["fired"], 1)
        self.assertLess(nf["skip_rate"], 1.0)

    def test_the_threshold_is_a_named_convention_and_a_caller_may_RAISE_it(self):
        """No bar-shaped default hidden at a call site (`MA5`); the module constant IS the
        declaration of the convention."""
        self._skip(F.NEVER_FIRES_AFTER)
        self.assertEqual(F.never_fires(BOOK, self.root)["state"], "RULE_ARMED_NEVER_FIRES")
        self.assertEqual(F.never_fires(BOOK, self.root, after=10_000)["state"], "OK")

    def test_selfchecks_and_refusals_are_NOT_counted_as_observations(self):
        """Only what the RULE produced counts. Counting a self-check row would accuse a book
        of never firing on the strength of the harness having verified itself."""
        for _ in range(F.NEVER_FIRES_AFTER * 2):
            F.record(BOOK, "refusal", {"refusal_code": "X", "detail": "y"},
                     decl_sha=self.sha, root=self.root)
        nf = F.never_fires(BOOK, self.root)
        self.assertEqual(nf["observations"], 0)
        self.assertEqual(nf["state"], "OK")


class TheCycleSurfacesIt(unittest.TestCase):

    def setUp(self):
        F._ENTRY_RULES.clear()
        self.root = _repo(book=BOOK)
        _seed_selfcheck(self.root, BOOK)
        self.sha = _sha(self.root, BOOK)

    def tearDown(self):
        F._ENTRY_RULES.clear()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_state_reaches_the_cycle_body_and_the_top_level_list(self):
        for i in range(F.NEVER_FIRES_AFTER):
            F.record(BOOK, "skip",
                     F.skip_fields(symbol="S%d" % i, skip_reason="never satisfiable"),
                     decl_sha=self.sha, root=self.root)
        F.register_entry_rule(BOOK, lambda decl, root: [], places_orders=True)
        out = F.cycle(self.root, write=False, books=[BOOK])
        row = [r for r in out["books"] if r.get("is_book")][0]
        self.assertEqual(row["never_fires"], "RULE_ARMED_NEVER_FIRES")
        self.assertIn(BOOK, out["never_fires"])
        self.assertIn("quiet market", row["never_fires_reason"])

    def test_a_healthy_book_is_absent_from_the_list(self):
        F.register_entry_rule(BOOK, lambda decl, root: [], places_orders=True)
        out = F.cycle(self.root, write=False, books=[BOOK])
        self.assertEqual(out["never_fires"], [])


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
