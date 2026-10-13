"""ITEM 50 — WHEN A RE-CERTIFICATION IS OWED, EVERY SURFACE SAYS SO AND NAMES THE ACTION.

**THE DEFECT THIS PINS IS NOT A MISSING WARNING. IT IS A WARNING THAT WAS TRUE AND WAS NOT AN
INSTRUCTION.** The fleet sat refusing every fill for weeks. The cycle reported
`ALL_BOOKS_BLOCKED_AT_GATE:SELFCHECK_STALE`; the public shelf said *"the harness changed since
the last self-check; re-run it"* on each of eighteen rows; the Action printed the cause. Not
one of them said **which workflow to run**, and the one surface Don actually reads without
opening anything — the Discord line — would have posted eighteen near-identical code lines
with no fix sentence anywhere.

So the three properties asserted here are:

  1. **ONE DEFINITION OF THE REMEDY** (`B7`). `fleet.SELFCHECK_REMEDY` is the only copy, and
     the notifier imports it rather than wording its own. Three surfaces that can drift about
     what to do is the same defect one level on.
  2. **THE MESSAGE IS ONE LINE AND IT CARRIES THE ACTION.** Eighteen books stale is one fact,
     not eighteen, and a fix sentence under a wall of noise is the same as no fix sentence.
  3. **A REMEDY IS NOT OFFERED WHERE IT CANNOT WORK.** `SELFCHECK_FAILING` means the harness
     is broken: a re-run fails again, and an instruction that cannot work spends the reader's
     trust — which is how a surface stops being read.

Plus the cry-wolf repair the same item found: **`f1_fill_ab` places no orders by declaration
and its record stream stays empty by design, so `RULE_ARMED_NEVER_FIRES` is permanently true
of it** and the alarm whose docstring says it *"cannot cry wolf"* lights on every cycle for the
rest of the project. A lamp that is always lit is how the fleet came to be shut with every
warning technically correct. It is reported as its own state, never dropped (`V6`'s rule).

    python tests/test_item50_selfcheck_visible.py
"""
from __future__ import annotations

import ast
import io
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                               # noqa: E402
from valuation.edge import fleet_notify as FN                       # noqa: E402
from test_fleet_harness import _repo, _seed_selfcheck, BOOK, _sha   # noqa: E402


def _stale_rows(n, code="SELFCHECK_STALE"):
    return [{"book": "f%02d_book" % i, "code": code} for i in range(n)]


def _p(refusals, fills=(), cleared=()):
    return {"fills": list(fills), "cleared": list(cleared),
            "new_refusals": list(refusals), "quiet": False}


class TheRemedyExistsOnce(unittest.TestCase):
    """`B7`: one sentence, one home, and the surfaces read it."""

    def test_the_remedy_names_the_workflow_by_its_real_name(self):
        # The name is the actionable part: "re-run the self-check" sends a reader looking for
        # a button that is labelled something else.
        self.assertIn("FLEET SELF-CHECK (re-certify)", F.SELFCHECK_REMEDY)
        self.assertIn("Run workflow", F.SELFCHECK_REMEDY)

    def test_the_notifier_IMPORTS_the_remedy_and_does_not_carry_a_second_copy(self):
        with io.open(os.path.join(REPO, "valuation", "edge", "fleet_notify.py"),
                     encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        imported = any(isinstance(n, ast.ImportFrom)
                       and any(a.name == "SELFCHECK_REMEDY" for a in n.names)
                       for n in ast.walk(tree))
        self.assertTrue(imported, "the notifier must import the one definition")
        # POSITIVE CONTROL ON THE BAN: the needle is a phrase from the remedy, and the only
        # legitimate way for it to appear here is through the import.
        self.assertNotIn("FLEET SELF-CHECK (re-certify) -> Run workflow", src)

    def test_the_notifier_DERIVES_its_code_list_from_the_one_state_list(self):
        # Two lists of "which states a re-run fixes" can drift, and a surface offering a
        # remedy the gate no longer honours is worse than none. `may_fill` builds its code as
        # `"SELFCHECK_" + state`, so the mapping is derived here rather than typed twice.
        self.assertEqual(sorted(FN.FIXED_BY_RECERTIFY),
                         sorted("SELFCHECK_" + s for s in F.RECERTIFY_FIXES))
        self.assertNotIn("SELFCHECK_FAILING", FN.FIXED_BY_RECERTIFY)

    def test_the_public_shelf_reads_the_same_object_rather_than_wording_its_own(self):
        with io.open(os.path.join(REPO, "valuation", "web", "fleet_public.py"),
                     encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("selfcheck_action", src)
        self.assertNotIn("Run workflow", src)


class TheMessageCarriesTheAction(unittest.TestCase):

    def test_eighteen_stale_books_compose_to_ONE_line_plus_the_fix(self):
        body = FN.compose(_p(_stale_rows(18)))
        # One grouped line, not eighteen. Counted on the bullet, which is what a reader scans.
        bullets = [L for L in body.split("\n") if L.startswith("- ")]
        self.assertEqual(len(bullets), 1, body)
        self.assertIn("18 books", body)
        self.assertIn("SELFCHECK_STALE", body)
        self.assertIn(F.SELFCHECK_REMEDY, body)

    def test_two_books_are_still_named_individually(self):
        # Grouping must not cost the detail where the detail fits: a code with one or two
        # books names them, because "2 books — CHAIN_BROKEN" hides which two.
        body = FN.compose(_p(_stale_rows(2, code="CHAIN_BROKEN")))
        self.assertIn("f00_book", body)
        self.assertIn("f01_book", body)
        self.assertNotIn("2 books", body)

    def test_a_FAILING_selfcheck_gets_NO_remedy_because_a_rerun_cannot_fix_it(self):
        body = FN.compose(_p([{"book": "f3", "code": "SELFCHECK_FAILING"}]))
        self.assertIn("SELFCHECK_FAILING", body)
        self.assertNotIn(F.SELFCHECK_REMEDY, body)
        self.assertNotIn("What to do", body)

    def test_a_mixed_day_names_both_codes_and_offers_the_fix_once(self):
        body = FN.compose(_p(_stale_rows(5) + [{"book": "zz", "code": "CHAIN_BROKEN"}]))
        self.assertIn("SELFCHECK_STALE", body)
        self.assertIn("CHAIN_BROKEN", body)
        self.assertEqual(body.count(F.SELFCHECK_REMEDY), 1, body)

    def test_a_quiet_day_still_says_nothing_at_all(self):
        self.assertEqual(FN.compose(_p([])), "")


class TheFleetWideFact(unittest.TestCase):

    def setUp(self):
        F._ENTRY_RULES.clear()
        self.root = _repo(book=BOOK)
        self.sha = _sha(self.root, BOOK)

    def tearDown(self):
        F._ENTRY_RULES.clear()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_an_uncertified_book_makes_the_action_NEEDED_and_names_the_remedy(self):
        a = F.selfcheck_action(self.root)
        self.assertTrue(a["needed"])
        self.assertEqual(a["states"][BOOK], "ABSENT")
        self.assertEqual(a["remedy"], F.SELFCHECK_REMEDY)
        self.assertIn("cannot fill", a["reason"])

    def test_a_certified_book_makes_it_NOT_needed_and_carries_no_remedy(self):
        _seed_selfcheck(self.root, BOOK)
        a = F.selfcheck_action(self.root)
        self.assertFalse(a["needed"])
        self.assertEqual(a["remedy"], "")
        self.assertEqual(a["n_books"], 0)

    def test_the_why_explains_that_a_harness_change_is_the_cause_not_a_fault(self):
        a = F.selfcheck_action(self.root)
        self.assertIn("hash of the harness", a["why"])

    def test_the_cycle_body_carries_the_object_so_a_reader_need_not_match_a_SUBSTRING(self):
        # `fleet-cycle.yml` had to glob `*SELFCHECK_STALE*` out of a code to guess a fix.
        # This is the field that replaces the guess.
        F.register_entry_rule(BOOK, lambda decl, root: [], places_orders=True)
        out = F.cycle(self.root, write=False, books=[BOOK])
        self.assertIn("selfcheck_action", out)
        self.assertTrue(out["selfcheck_action"]["needed"])
        self.assertEqual(out["selfcheck_action"]["remedy"], F.SELFCHECK_REMEDY)

    def test_it_is_a_READ_and_the_gate_itself_is_unchanged(self):
        # The point of a notice is that it changes nothing about who may fill.
        self.assertFalse(F.may_fill(BOOK, self.root)["ok"])
        F.selfcheck_action(self.root)
        self.assertFalse(F.may_fill(BOOK, self.root)["ok"])


class ARiderCannotFireAndThatIsNotNews(unittest.TestCase):

    def setUp(self):
        F._ENTRY_RULES.clear()
        self.root = _repo(book=BOOK)
        _seed_selfcheck(self.root, BOOK)
        self.sha = _sha(self.root, BOOK)
        for i in range(F.NEVER_FIRES_AFTER):
            F.record(BOOK, "skip",
                     F.skip_fields(symbol="S%d" % i, skip_reason="rides the others"),
                     decl_sha=self.sha, root=self.root)

    def tearDown(self):
        F._ENTRY_RULES.clear()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_rider_gets_its_OWN_state_rather_than_the_alarm(self):
        F.register_entry_rule(BOOK, lambda decl, root: [], places_orders=False)
        nf = F.never_fires(BOOK, self.root)
        self.assertEqual(nf["state"], "RIDER_PLACES_NO_ORDERS")
        self.assertIn("places no orders", nf["reason"])

    def test_a_rider_is_absent_from_the_list_a_reader_CHECKS_and_present_in_its_own(self):
        F.register_entry_rule(BOOK, lambda decl, root: [], places_orders=False)
        out = F.cycle(self.root, write=False, books=[BOOK])
        self.assertNotIn(BOOK, out["never_fires"])
        self.assertIn(BOOK, out["riders_place_no_orders"])

    def test_POSITIVE_CONTROL_an_order_placing_rule_still_raises_the_alarm(self):
        # The exemption must be about placing orders and nothing else, or it is a way to
        # silence the alarm on a book that really has never fired.
        F.register_entry_rule(BOOK, lambda decl, root: [], places_orders=True)
        nf = F.never_fires(BOOK, self.root)
        self.assertEqual(nf["state"], "RULE_ARMED_NEVER_FIRES")
        out = F.cycle(self.root, write=False, books=[BOOK])
        self.assertIn(BOOK, out["never_fires"])
        self.assertEqual(out["riders_place_no_orders"], [])


class TheShelfShowsItOnlyWhileItIsTrue(unittest.TestCase):

    def test_the_template_renders_the_banner_behind_the_payload_flag(self):
        with io.open(os.path.join(REPO, "valuation", "web", "templates",
                                  "research.html"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("declared.ops.action_needed", src)
        # NOT a permanent notice: the block is conditional, which is what stops the shelf
        # carrying a standing warning nobody reads.
        self.assertIn("{% if declared.ops and declared.ops.action_needed %}", src)
        self.assertIn("The fleet is not filling.", src)

    def test_the_payload_reports_None_rather_than_an_all_clear_when_it_cannot_read(self):
        from valuation.web import fleet_public as FP
        self.assertIsNone(FP._action("C:/nonexistent-root-for-item-50"))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    print("\nitem 50 self-check visibility: %d run, %d failures, %d errors"
          % (r.testsRun, len(r.failures), len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
