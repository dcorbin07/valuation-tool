# -*- coding: utf-8 -*-
"""ITEM 72 — the auditor's seventh-review leftovers. None of them can move a share.

**THE STALE `open_event`, AND IT IS MY OWN DEFECT FROM ITEM 71.** That item made the close
require `open_event == key` — correct — and wrote ONE reason for two different states:

* another event is open **and this slot has orders resting for it** — the sentence is true;
* another event is open **and nothing is resting** — the sentence is false, and this is the state
  every real event is in the morning after its `day` orders expired unfilled.

`open_remainder: False` sat in the same payload as a reason asserting that orders ARE working at
the broker. **The eighth message on this path to claim a property the code does not have, written
by the item fixing the seventh.** And the branch returned before the no-progress ceiling, so it
could not escalate — breaking item 70's own rule that *"a branch that keeps an event open and
cannot reach the ceiling has swapped a silent close for a SILENT HOLD, which is not an
improvement."*

**THE PAPER SLOT IS IN THIS STATE TODAY**: `open_event: rebalance:2026-07-30` with that key
already in `processed_events`.

**AND WHY THE SLOT HOLDS 82 NAMES AND NOT THE BOOK'S 86.** The record is a FILL count, not a
selection count — `reconcile` builds it from this slot's own filled orders, deliberately, because
a record built from submissions is what made the duplicate buy-in reachable (item 63). Five
things can leave a held book name out of it and **two of them were reported nowhere**: the dust
case was a bare `continue`, and "ordered before and never filled" had no column at all. Both are
reported now, per name, on every cycle.
"""
from __future__ import annotations

import ast
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.edge import live_cycle as LC            # noqa: E402
from valuation.edge import live_slots as LS            # noqa: E402
import tests.test_item71 as T71                        # noqa: E402
import tests.test_item71_table as TT                   # noqa: E402

FORMED = TT.FORMED
EVENT = "rebalance:" + FORMED
OLD_EVENT = "rebalance:2026-08-01"


# ----------------------------------------------------------------------------------------- #
# 1. THE STALE `open_event`
# ----------------------------------------------------------------------------------------- #
class AStaleOpenEventNoLongerClaimsOrdersAreWorking(T71._Live):
    """The auditor's reproduction: three consecutive cycles, record on target, nothing working
    at the broker, and `blocked_by_open_event` naming an event that has nothing resting."""

    def _stale(self, **kw):
        """On target for 5%, with an OLD event left open and NOTHING resting for it."""
        self.seed(holdings={"AAPL": 2.5, "BBB": 2.5}, last_pct=5.0,
                  last_event_date="2026-08-01", open_event=OLD_EVENT,
                  processed=[OLD_EVENT], **kw)
        return self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5})

    def test_the_reason_does_NOT_say_orders_are_working(self):
        slot, live, st = self._stale()
        blob = (slot.get("reason") or "")
        self.assertNotIn("working at the broker", blob,
                         "it still claims orders are working: %s" % blob[:200])

    def test_and_open_remainder_agrees_with_it(self):
        """The two facts that sat in one payload contradicting each other."""
        slot, live, st = self._stale()
        self.assertFalse(slot["open_remainder"])
        self.assertTrue(slot["open_event_is_stale"])
        self.assertEqual(slot["open_event_of_record"], OLD_EVENT)

    def test_the_stale_event_is_CLEARED_rather_than_refused_on_for_ever(self):
        slot, live, st = self._stale()
        self.assertEqual(slot["cleared_stale_open_event"]["event"], OLD_EVENT)
        self.assertIsNone(st.get("open_event"), "the stale key survived")

    def test_and_the_arriving_event_then_CLOSES(self):
        """The point of clearing it: before this, every later cycle refused for ever."""
        slot, live, st = self._stale()
        self.assertTrue(slot["event_closed"], slot.get("reason"))
        self.assertIn(EVENT, st.get("processed") or [])

    def test_a_stale_event_that_WAS_recorded_complete_does_not_alert(self):
        """Only the SEND path appends to `processed` before setting `open_event`, so a stale key
        IN `processed` is residue from orders that expired. **This is the paper slot's shape
        today** — `open_event: rebalance:2026-07-30` with that key in `processed_events` — and
        alerting on it would alert on bookkeeping."""
        slot, live, st = self._stale()
        self.assertTrue(slot["cleared_stale_open_event"]["was_recorded_complete"])
        self.assertNotIn("stale_open_event_never_completed",
                         [a["kind"] for a in slot["alerts"]])

    def test_a_stale_event_that_was_NEVER_completed_DOES_alert(self):
        """`PLAN_BLOCKED` and `PLAN_RESTING` set `open_event` WITHOUT appending to `processed`,
        so a stale key absent from it was planned and never finished. That is a fact Don should
        hear, and it is a different fact from the one above."""
        self.seed(holdings={"AAPL": 2.5, "BBB": 2.5}, last_pct=5.0,
                  last_event_date="2026-08-01", open_event=OLD_EVENT, processed=[])
        slot, live, st = self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5})
        self.assertFalse(slot["cleared_stale_open_event"]["was_recorded_complete"])
        self.assertIn("stale_open_event_never_completed",
                      [a["kind"] for a in slot["alerts"]])

    def test_the_CONTROL_a_REAL_open_event_still_blocks_and_still_says_so(self):
        """Without this, "clear anything foreign" would be a licence to discard a live
        remainder — which is blocker B, in reverse."""
        self.seed(holdings={}, last_pct=0.0, last_event_date=FORMED, open_event=EVENT,
                  processed=[])
        resting = (("AAPL", "buy", 2.5, 0.0, EVENT), ("BBB", "buy", 2.5, 0.0, EVENT))
        slot, live, st = self.cycle(pct=5, holdings={}, resting=resting)
        self.assertFalse(slot["open_event_is_stale"])
        self.assertEqual(slot.get("blocked_by_open_event"), EVENT)
        self.assertIn("working at the broker", slot.get("reason") or "")
        self.assertEqual(st.get("open_event"), EVENT, "it discarded a LIVE remainder")

    def test_and_a_REAL_open_event_now_REACHES_THE_CEILING(self):
        """Item 70's own rule: *"a branch that keeps an event open and cannot reach the ceiling
        has swapped a silent close for a SILENT HOLD."* This branch returned before it."""
        self.seed(holdings={}, last_pct=0.0, last_event_date=FORMED, open_event=EVENT,
                  processed=[])
        resting = (("AAPL", "buy", 2.5, 0.0, EVENT), ("BBB", "buy", 2.5, 0.0, EVENT))
        slot, live, st = self.cycle(pct=5, holdings={}, resting=resting)
        self.assertEqual(slot.get("attempts_counted_in"), "trading days")
        self.assertTrue(slot.get("attempt_days"), "no day was counted, so it cannot escalate")

    def test_EVERY_branch_that_holds_an_event_open_calls_the_ceiling(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        calls = [n for n in ast.walk(ast.parse(src))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "note_no_progress"]
        self.assertEqual(len(calls), 4,
                         "the blocked, resting, send and open-event branches: found %d"
                         % len(calls))


class TheEventScopedStateIsOneList(unittest.TestCase):
    """My stale-clearing listed four bags and the close branch six, and item 64's own guard
    caught the divergence. Two lists of "the state scoped to one event" would drift, and the
    cost of missing one is residue attributed to the NEXT event — item 64's own subject."""

    def test_both_sites_iterate_the_constant(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        loops = [n for n in ast.walk(ast.parse(src))
                 if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
                 and n.target.id == "bag"]
        self.assertGreaterEqual(len(loops), 2)
        for n in loops:
            self.assertTrue(isinstance(n.iter, ast.Name)
                            and n.iter.id == "EVENT_SCOPED_STATE",
                            "hand-written list: %s" % ast.unparse(n.iter)[:60])

    def test_the_retired_counters_are_on_it(self):
        """`event_attempts` and `event_progress` are item 64's retired counters, read nowhere.
        They stay on the list because a bag cleared in one place and not the other is the drift
        the constant exists to prevent."""
        for bag in ("event_attempts", "event_progress", "send_seq", "event_fingerprint",
                    "event_attempt_days", "awaiting_settlement"):
            self.assertIn(bag, LC.EVENT_SCOPED_STATE)


class IntentIsClearedByItsOwnEventKey(unittest.TestCase):
    """Item 71 put `intent` and `open_event` behind one condition, and they are two facts.
    `intent` carries the event it belongs to; `open_event` is the remainder marker."""

    def test_the_close_branch_tests_intents_OWN_event(self):
        import inspect
        src = inspect.getsource(LC.run_slot)
        self.assertIn('if (st.get("intent") or {}).get("event") == key:', src)


# ----------------------------------------------------------------------------------------- #
# 1c. WHY 82 AND NOT 86
# ----------------------------------------------------------------------------------------- #
class WhyTheSlotHoldsFewerNamesThanTheBook(unittest.TestCase):
    """**THE RECORD IS A FILL COUNT, NOT A SELECTION COUNT.** Answered on every cycle rather
    than once, because the bound book and the slot's record both live on the service."""

    BOOK = {"ok": True, "formed_on": FORMED, "positions": [
        {"ticker": t, "status": "held", "weight": 0.2}
        for t in ("AAA", "BBB", "CCC", "DDD", "EEE")]}

    def test_each_cause_gets_its_OWN_reason(self):
        plan = {"orders": [{"ticker": "AAA"}],
                "skipped": [{"ticker": "BBB", "reason": "no usable mark"}],
                "dust": [{"ticker": "CCC", "gap_value": 0.4, "min_order_value": 1.0}]}
        got = LC.book_vs_record(self.BOOK, {"EEE": 1.0}, plan,
                                resting=[{"ticker": "DDD"}])
        self.assertEqual(got["n_book_held"], 5)
        self.assertEqual(got["n_recorded"], 1)
        why = {r["ticker"]: r["why"] for r in got["not_held"]}
        self.assertEqual(why, {"AAA": "planned_this_cycle", "BBB": "skipped",
                               "CCC": "dust", "DDD": "resting"})

    def test_the_RESIDUAL_class_is_named_and_says_it_is_TWO_things(self):
        """A name with none of the four known reasons was ordered before and never filled, OR
        never accepted by the account — and a rejected order leaves nothing in the orders list,
        so this cycle cannot tell them apart. Naming one would be a guess."""
        got = LC.book_vs_record(self.BOOK, {}, {"orders": [], "skipped": [], "dust": []})
        self.assertEqual(got["by_reason"], {"unfilled_or_rejected": 5})
        detail = got["not_held"][0]["detail"]
        self.assertIn("never filled", detail)
        self.assertIn("never accepted", detail)

    def test_a_name_the_book_does_not_HOLD_is_not_counted_as_missing(self):
        """A zero-weight or non-held position is not something the slot ought to hold, so
        counting it would overstate the gap on every cycle."""
        book = {"positions": [{"ticker": "AAA", "status": "held", "weight": 0.5},
                              {"ticker": "ZZZ", "status": "exited", "weight": 0.0},
                              {"ticker": "YYY", "status": "held", "weight": 0.0}]}
        got = LC.book_vs_record(book, {}, {"orders": [], "skipped": [], "dust": []})
        self.assertEqual(got["n_book_held"], 1)
        self.assertEqual([r["ticker"] for r in got["not_held"]], ["AAA"])

    def test_the_planner_REPORTS_its_dust_instead_of_a_bare_continue(self):
        """The one way a held book name could get no order and appear in NO list: not in
        `orders`, not in `skipped`, just absent. The auditor named it as the residual."""
        p = LS.order_plan({"AAPL": 100.5, "BBB": 150.0}, {"AAPL": 1.0, "BBB": 1.0},
                          {"AAPL": {"mid": 100.0}, "BBB": {"mid": 100.0}})
        self.assertEqual([o["ticker"] for o in p["orders"]], ["BBB"])
        self.assertEqual([d["ticker"] for d in p["dust"]], ["AAPL"])
        self.assertAlmostEqual(p["dust"][0]["gap_value"], 0.5, places=6)

    def test_dust_is_NOT_a_skip_which_would_refuse_the_cycle(self):
        """`skipped` means "could not be planned" and drives `PLAN_BLOCKED`; dust is "correctly
        nothing to do". Conflating them would refuse a whole rebalance over a 40-cent gap."""
        p = LS.order_plan({"AAPL": 100.5}, {"AAPL": 1.0}, {"AAPL": {"mid": 100.0}})
        self.assertEqual(p["skipped"], [])
        self.assertEqual(LC.plan_outcome(p), LC.PLAN_TARGETS_MET)

    def test_the_census_is_READ_ONLY(self):
        """It decides nothing: no caller branches on it, and a failure inside it must not cost
        the cycle its orders — item 67's rule for the fractional report."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        reads = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                 and n.slice.value == "book_vs_record"]
        # Only the assignment into `out`, never a read that decides anything.
        self.assertLessEqual(len(reads), 2, "something branches on the census")
        self.assertIn('out["book_vs_record"] = {"error"', src)


# ----------------------------------------------------------------------------------------- #
# 2. THE FIVE COMBINATIONS NOBODY HAD CHECKED
# ----------------------------------------------------------------------------------------- #
class TheTableNowReachesTheAuditorsFiveOmissions(unittest.TestCase):
    """*"Still unchecked by anyone: an exhausted event crossed with modes and reads, a quiet
    cycle, an UPWARD resize, a brand-new record, and a new book superseding an open pct
    event."*"""

    def test_all_five_are_axes_now(self):
        self.assertIn("exhausted", TT.STATES)
        self.assertIn("brand_new", TT.STATES)
        self.assertIn("stale_open", TT.STATES)
        self.assertIn("quiet", TT.EVENTS)
        self.assertIn("resize_up", TT.EVENTS)
        self.assertIn("book_over_pct", TT.EVENTS)

    def test_the_table_grew_by_ITEM_72s_OWN_four_states_and_three_events(self):
        """Four states and three events: a brand-new record, the same against a NON-EMPTY
        account, an exhausted event, a stale `open_event`, a quiet cycle, an upward resize, and
        a new book superseding an open percentage event. 7 x 5 -> 11 x 8, so 2,240 -> 5,632.

        **IT USED TO ASSERT THE TOTAL AND THAT WAS A SECOND COPY OF THE TABLE'S SIZE
        [repointed item 73].** `test_item71_table` already pins the row count with `MA13`'s
        committed-literal idiom; a second literal in a second suite fires on the next item to
        add a row whatever it adds, which is item 73 (two cash states, 5,632 -> 6,656) and will
        be item 75 or whoever follows. The same clock-shaped guard this path has now repointed
        four times.

        So this asserts ITEM 72's OWN contribution -- that its four states and three events are
        present and that the table is at least the size they imply -- and leaves the exact total
        to the one suite whose subject it is.
        """
        for s in ("brand_new", "brand_new_dirty", "exhausted", "stale_open"):
            self.assertIn(s, TT.STATES)
        for e in ("quiet", "resize_up", "book_over_pct"):
            self.assertIn(e, TT.EVENTS)
        self.assertGreaterEqual(len(TT.STATES), 11)
        self.assertGreaterEqual(len(TT.EVENTS), 8)
        self.assertGreaterEqual(len(TT.all_rows()), 5632)
        # AND THE ARITHMETIC IS STILL THE PRODUCT OF ITS AXES, which is what would break if an
        # axis quietly lost a value while another gained one.
        self.assertEqual(len(TT.all_rows()),
                         len(TT.STATES) * len(TT.EVENTS) * len(TT.READS)
                         * len(TT.MODES) * len(TT.PILOTS))

    def test_the_UPWARD_resize_plans_BUYS_which_every_other_resize_did_not(self):
        """Every resize in the table went DOWN, so every one planned sells — and buys are the
        side that spends money and the side the budget bounds."""
        self.assertEqual(TT.EVENTS["resize_up"]["last_pct"], 2.0)
        self.assertEqual(TT.EVENTS["resize_up"]["pct"], 5.0)
        # **`off_target` HOLDS 1.0 OF ONE NAME, so going 2% -> 5% genuinely buys.**
        # `on_target` holds 2.5 of each, which already IS the 5% target -- so my
        # first cut asserted buys on the one state that has nothing to buy.
        got = TT.run_row("off_target", "resize_up", TT.READS[0], "live", "1")
        self.assertTrue(got["placed"])
        self.assertEqual(sorted({s for _, s in got["placed"]}), ["buy"])

    def test_a_QUIET_cycle_does_NOTHING_and_that_is_the_whole_point(self):
        got = TT.run_row("on_target", "quiet", TT.READS[0], "live", "1")
        self.assertEqual(got["placed"], [])
        self.assertIn("the whole point", got["reason"])

    def test_a_BRAND_NEW_record_against_an_EMPTY_account_proceeds(self):
        """Item 67's fresh-record check refuses only when the record is new AND the account is
        not empty, so this is the correct behaviour and worth pinning: a genuinely new slot
        buys in."""
        got = TT.run_row("brand_new", "rebalance", TT.READS[0], "live", "1")
        self.assertTrue(got["placed"])

    def test_a_BRAND_NEW_record_against_a_NON_EMPTY_account_refuses_ONE_cycle(self):
        """**Item 67's fresh-record check, reachable in no row until item 72.** My first cut
        asserted this of `brand_new` and it bought in -- because the fixture DERIVES the
        broker's positions from the record, so a brand-new row always had an empty account.
        That derivation is also the auditor's own noted gap: no foreign position appeared in
        any of the 2,240 rows. `brand_new_dirty` carries one."""
        got = TT.run_row("brand_new_dirty", "rebalance", TT.READS[0], "live", "1")
        self.assertEqual(got["placed"], [])
        self.assertIn("brand new", (got["reason"] or ""))

    def test_and_a_FOREIGN_broker_position_is_never_traded(self):
        """The dangerous direction -- the broker holding MORE than the record -- which the
        auditor could only check by hand. Now a row."""
        got = TT.run_row("on_target", "quiet", TT.READS[0], "live", "1")
        self.assertEqual(got["placed"], [])

    def test_an_EXHAUSTED_event_stops_and_alerts(self):
        got = TT.run_row("exhausted", "rebalance", TT.READS[0], "live", "1")
        self.assertEqual(got["placed"], [])
        self.assertIn("event_attempts_exhausted", got["alerts"])

    def test_a_NEW_BOOK_supersedes_an_open_percentage_event(self):
        """`event_for` prefers the rebalance, so the pct event is overtaken — blocker B from
        the other direction."""
        got = TT.run_row("on_target", "book_over_pct", TT.READS[0], "live", "1")
        self.assertEqual(got["key"], EVENT)

    def test_the_36_way_read_control_has_a_POSITIVE_direction_now(self):
        """The review's third request. Without it the control asserted only that forbidden
        things do not happen, so a tree that did nothing would have satisfied all 36."""
        src = io.open(TT.__file__, encoding="utf-8").read()
        self.assertIn("is CLEAN with work to do and sent NOTHING", src)
        self.assertIn("exactly one of the 36 is all-ok and it must have traded", src)


# ----------------------------------------------------------------------------------------- #
# 3. THE 2026-10-22 REBALANCE — NOT WATCHED, AND WHY
# ----------------------------------------------------------------------------------------- #
class TheRebalanceWatchHasNotHappened(unittest.TestCase):
    """**PART 3 OF THE BRIEF IS NOT DONE AND CANNOT BE**, and saying so is the deliverable.

    The brief asks for the paper slot's 2026-10-22 rebalance to be watched *"on the first
    in-hours cycles after the event is appended on the evening of 10-23"*. Today is **2026-10-18**.
    The book has not moved, the event does not exist, and no cycle has run on it.

    What a lane CAN do before then is make sure the four things the brief asks to be read are
    actually readable on that cycle, and they are — each has a field and each is asserted here
    rather than promised. That is the preparation; the observation is the week after.
    """

    def test_SELLS_FIRST_is_reported_on_the_plan(self):
        p = LS.order_plan({"AAPL": 0.0, "BBB": 500.0}, {"AAPL": 5.0},
                          {"AAPL": {"mid": 100.0}, "BBB": {"mid": 100.0}})
        self.assertTrue(p["sells_first"])
        self.assertEqual([o["side"] for o in p["orders"]], ["sell", "buy"])

    def test_SETTLEMENT_WAITS_have_a_field(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn('out["awaiting_settlement"]', src)
        self.assertIn("settlement_wait_overdue", src)

    def test_EXITS_PRICED_AND_SOLD_have_fields(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn('out["exits_planned"]', src)
        self.assertIn('"missing_exits"', src)

    def test_WHETHER_THE_EVENT_CLOSES_ONLY_WHEN_THE_HOLDINGS_MATCH_has_a_field(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn('out["event_closed"]', src)
        self.assertIn('out["book_vs_record"]', src)

    def test_and_the_census_answers_the_82_question_on_that_cycle(self):
        """Which is the part of the brief that CAN be prepared: the reason each unheld name is
        unheld is now a field, so the rebalance cycle will say it without anybody digging."""
        self.assertTrue(callable(LC.book_vs_record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
