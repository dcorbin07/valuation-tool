# -*- coding: utf-8 -*-
"""ITEM 71 — the auditor's sixth review: three blockers, driven with `armed_state` DERIVED.

**A. THE X→0 SELL-OUT COULD NOT EXECUTE ON A LIVE SLOT**, which is Don's documented way out.
`armed()` refuses at `pct <= 0`, no live client is built for an unarmed slot, so a slot holding
positions at a declared 0% could never sell them. `pct == 0` meant both *"never traded, holds
nothing"* and *"still holding, must get out"*. Item 70 found the parity half of this and
attributed it to parity alone; the auditor applied exactly that fix and **nothing transmitted**,
because parity is the THIRD of four gates.

**B. A SECOND EVENT CLOSED THE FIRST EVENT'S REMAINDER.** `st["open_event"] = None` ran
unconditionally. The buy-in is sent and unfilled, Don sets 0% in the same session, the
sell-out's targets genuinely are met at that instant, it closes — and takes the rebalance's
remainder with it. The buys then fill: fully invested at a declared 0%, both events recorded
complete, no alert.

**C. THE CLOSE FIRED ON A READ THAT WAS NEVER ATTEMPTED.** In `?run=paper` — the installed
schedule, five times a day — no live client is built, so `order_read` is `not_attempted` and the
resting list is empty. Same state: `mode=live` holds the event open, `mode=paper` and `mode=dry`
closed it. And a GET of `/admin/live-cycle` wrote state.

**WHY `armed_state` IS DERIVED HERE AND NOT SUPPLIED.** Item 70's suite could see only the third
gate because its fixture passed `armed_state={"armed": True}` and a client — the two things
production withholds at 0%. That is item 65's own lesson one level up: *"all 236 tests passed
through it, because each supplied by hand the scope the production path derives."* Every cycle in
this file goes through `run_cycle` with the percentage in an environment dict, so `armed` is
called by the code under test.

The whole state space is in `tests/test_item71_table.py`; this file is the three blockers and
the two further defects that table found.
"""
from __future__ import annotations

import datetime as _dt
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
import tests.test_item71_table as TT                   # noqa: E402

FORMED = TT.FORMED
EVENT = "rebalance:" + FORMED


def env(pct, enabled="1"):
    """A live slot's environment. **`ALPACA_ACCOUNT_1_LIVE_PCT` is the real variable name** --
    the auditor's fifth review measured `ALPACA_ACCOUNT_1_PCT` and every value fell through to
    the "no percentage is set" branch, which is how a control of theirs came back 0 when it had
    been set to 2."""
    return {"LIVE_PILOT_ENABLED": enabled, "ALPACA_ACCOUNT_1_KEY_ID": "k",
            "ALPACA_ACCOUNT_1_SECRET_KEY": "s" * 24,
            "ALPACA_ACCOUNT_1_LIVE_PCT": str(pct)}


class _Live(unittest.TestCase):
    """A live slot, through `run_cycle`, with the real `_LiveClient` over recorded HTTP."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def seed(self, **st):
        base = {"slot": "1", "account_id": "acct-live-1", "processed": [], "holdings": {}}
        base.update(st)
        p = LC.state_path("1", self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(base, fh)

    def cycle(self, *, pct, holdings=None, resting=(), mode="live", enabled="1",
              book=None, may_write=True, paper_holdings=None, paper_account=None):
        live = TT.Rec(holdings=(holdings or {}), resting=resting)
        paper = TT.Rec(holdings=(paper_holdings or {}),
                       account=(paper_account or TT.PAPER_ACCOUNT), slot="paper")
        from valuation.edge import alpaca_broker as AB
        got = LC.run_cycle(
            env=env(pct, enabled), mode=mode, may_write=may_write,
            now=TT.OPEN_NOW, root=self.root, book=(book or TT.BOOK),
            paper_client=AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24,
                                              session=paper),
            live_client_factory=(lambda n: LS._LiveClient(n, "k", "s" * 24, session=live)),
            notify_send=(lambda cfg, b: True))
        slot = next((x for x in (got.get("slots") or [])
                     if str(x.get("slot")) == "1"), {}) or {}
        return slot, live, LC.read_state("1", self.root)


# ----------------------------------------------------------------------------------------- #
# BLOCKER A — the wind-down
# ----------------------------------------------------------------------------------------- #
class TheSellOutCanNowExecuteOnALiveSlot(_Live):
    """**`DECISIONS.md` 2026-10-14: *"0 to X buys in, and X to 0 sells out"*, and
    `LIVE_PILOT_ENABLED=0` *"pauses every slot without selling"* — so pausing was not an exit
    either. Don's documented way out did not exist.**"""

    def test_X_to_0_PLACES_THE_SELLS_on_the_live_host(self):
        self.seed(holdings={"AAPL": 5.0, "BBB": 5.0}, last_pct=5.0,
                  last_event_date=FORMED, processed=[EVENT])
        slot, live, _ = self.cycle(pct=0, holdings={"AAPL": 5.0, "BBB": 5.0})
        self.assertTrue(slot["armed"], slot.get("reason"))
        self.assertTrue(slot["sell_only"])
        self.assertEqual(sorted((o["symbol"], o["side"]) for o in live.placed),
                         [("AAPL", "sell"), ("BBB", "sell")], slot.get("reason"))

    def test_and_it_sells_EXACTLY_what_this_slots_own_record_holds(self):
        """The property that makes a wind-down safe: `reconcile` builds the record from THIS
        slot's own fills, so Don's other positions in the same account are not in it and
        cannot be sold. Here he holds 999 TSLA by hand."""
        self.seed(holdings={"AAPL": 5.0}, last_pct=5.0, last_event_date=FORMED,
                  processed=[EVENT])
        live = TT.Rec(holdings={"AAPL": 5.0})
        real_positions = live.request

        def with_tsla(method, url, *a, **kw):
            rep = real_positions(method, url, *a, **kw)
            if url.endswith("/v2/positions"):
                rows = list(rep.json())
                rows.append({"symbol": "TSLA", "qty": "999", "avg_entry_price": "1",
                             "side": "long"})
                return TT.T63.Reply(rows)
            return rep
        live.request = with_tsla
        from valuation.edge import alpaca_broker as AB
        paper = TT.Rec(holdings={}, account=TT.PAPER_ACCOUNT, slot="paper")
        LC.run_cycle(env=env(0), mode="live", now=TT.OPEN_NOW, root=self.root,
                     book=TT.BOOK,
                     paper_client=AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24,
                                                       session=paper),
                     live_client_factory=(lambda n: LS._LiveClient(n, "k", "s" * 24,
                                                                   session=live)),
                     notify_send=(lambda cfg, b: True))
        sold = sorted(o["symbol"] for o in live.placed)
        self.assertEqual(sold, ["AAPL"], "it reached Don's own position: %r" % (sold,))

    def test_a_slot_at_0_percent_HOLDING_NOTHING_still_does_nothing(self):
        """The other half of the two states that shared one value. Nothing to sell, and a 0%
        target licenses no buy."""
        self.seed(holdings={}, last_pct=5.0, last_event_date=FORMED, processed=[EVENT])
        slot, live, _ = self.cycle(pct=0, holdings={})
        self.assertFalse(slot["armed"], slot.get("reason"))
        self.assertFalse(slot["sell_only"])
        self.assertEqual(live.placed, [])

    def test_THE_PAUSE_STILL_PAUSES_WITHOUT_SELLING(self):
        """`LIVE_PILOT_ENABLED=0` is a different instruction from 0% and must stay one. The
        order of `armed`'s conditions is the whole of what keeps them different."""
        self.seed(holdings={"AAPL": 5.0, "BBB": 5.0}, last_pct=5.0,
                  last_event_date=FORMED, processed=[EVENT])
        slot, live, _ = self.cycle(pct=0, holdings={"AAPL": 5.0, "BBB": 5.0}, enabled="0")
        self.assertFalse(slot["armed"], slot.get("reason"))
        self.assertFalse(slot["sell_only"])
        self.assertEqual(live.placed, [])
        self.assertIn("PAUSED", slot.get("reason") or "")

    def test_a_WIND_DOWN_TRANSMITS_NO_BUY(self):
        """Every target is zero, so the planner should produce sales alone -- and "should" is
        not a safety property when the thing prevented is spending real money in an account its
        owner has just told to hold nothing. Asserted on the filter AND at the broker's door."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn("buy_withheld_in_wind_down", src)
        self.assertIn("buy_blocked_at_the_broker_door", src)
        self.seed(holdings={"AAPL": 5.0}, last_pct=5.0, last_event_date=FORMED,
                  processed=[EVENT])
        slot, live, _ = self.cycle(pct=0, holdings={"AAPL": 5.0})
        self.assertEqual([o["side"] for o in live.placed], ["sell"])
        self.assertEqual(slot["withheld_buys"], [])

    def test_the_refusal_NO_LONGER_claims_the_slot_holds_nothing(self):
        """*"slot 1 is at 0%, so it holds nothing"* was false of the only slot that needs a
        sell-out, and it reached the cycle's own `reason` -- where a reader would most
        reasonably trust it. The seventh message on this path to assert a property the code did
        not have."""
        self.assertNotIn("so it holds nothing", LS.armed(1, env(0), holds=True)["reason"])
        self.assertNotIn("so it holds nothing", LS.armed(1, env(0), holds=False)["reason"])

    def test_the_BUY_IN_and_the_RESIZE_still_work(self):
        """The auditor's own control: buy-in and resize transmitted before this change, so the
        fix must not be a change to what the other two events do."""
        self.seed(holdings={}, last_pct=0.0, last_event_date=FORMED, processed=[EVENT])
        slot, live, _ = self.cycle(pct=5, holdings={})
        self.assertEqual(sorted(o["side"] for o in live.placed), ["buy", "buy"])
        self.assertFalse(slot["sell_only"])


class TheWindDownIsNotBlockedByAParityComparisonItCannotHave(_Live):
    """**THE FOURTH GATE, which nobody had named.** `armed` was the first and parity's
    zero-target case the third; `parity_absent` is the fourth, and the paper slot runs at
    `PAPER_PCT = 100`, so the comparison it waits for can never exist for a wind-down."""

    def test_with_NO_paper_comparison_a_wind_down_still_sells(self):
        """**NO PAPER TARGETS, which is what an unreadable paper equity produces.** My first
        cut used an EMPTY BOOK and that is refused earlier and for a different reason -- *"the
        book in force carries no held positions"* at preflight, which is correct behaviour and
        not this gate."""
        self.seed(holdings={"AAPL": 5.0, "BBB": 5.0}, last_pct=5.0,
                  last_event_date=FORMED, processed=[EVENT])
        slot, live, _ = self.cycle(
            pct=0, holdings={"AAPL": 5.0, "BBB": 5.0},
            paper_account=dict(TT.PAPER_ACCOUNT, equity="0"))
        self.assertTrue(slot["armed"], slot.get("reason"))
        self.assertIsNotNone(slot.get("parity"))
        self.assertTrue(slot["parity"]["ok"], slot["parity"]["reason"])
        self.assertFalse(slot["parity"]["measured"])
        self.assertEqual(sorted(o["side"] for o in live.placed), ["sell", "sell"],
                         slot.get("reason"))

    def test_and_an_EMPTY_BOOK_is_still_refused_which_is_a_different_thing(self):
        """Recorded because my own fixture confused the two: a book with no held positions is
        refused at preflight whatever the event, and that is not the gate this class is about.
        """
        self.seed(holdings={"AAPL": 5.0, "BBB": 5.0}, last_pct=5.0,
                  last_event_date=FORMED, processed=[EVENT])
        slot, live, _ = self.cycle(pct=0, holdings={"AAPL": 5.0, "BBB": 5.0},
                                   book={"ok": True, "formed_on": FORMED, "reason": "",
                                         "positions": []})
        self.assertEqual(live.placed, [])
        self.assertIn("no held positions", slot.get("reason") or "")

    def test_and_a_NON_wind_down_with_no_comparison_STILL_REFUSES(self):
        """`C5` intact for every event that HAS weights to compare."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn("parity_absent", src)
        self.assertIn("ABSENT IS NOT A PASS", src)


# ----------------------------------------------------------------------------------------- #
# BLOCKER B — a second event must not discard the first event's remainder
# ----------------------------------------------------------------------------------------- #
class ASecondEventDoesNotDiscardTheFirstEventsRemainder(_Live):
    """The auditor's route, exactly: the buy-in is sent, nothing has filled, and Don sets 0% in
    the same session."""

    def test_the_rebalances_remainder_SURVIVES_the_sell_out(self):
        self.seed(holdings={}, last_pct=5.0, last_event_date=FORMED, open_event=EVENT,
                  processed=[])
        resting = (("AAPL", "buy", 2.5, 0.0, EVENT), ("BBB", "buy", 2.5, 0.0, EVENT))
        slot, live, st = self.cycle(pct=0, holdings={}, resting=resting)
        self.assertEqual(st.get("open_event"), EVENT,
                         "the rebalance's remainder was discarded")

    def test_the_sell_out_route_is_ALSO_stopped_by_the_write_gate(self):
        """**BELT AND BRACES, and worth recording because it changes which fixture reaches the
        fifth defect.** On the auditor's own blocker-B route the slot is at 0% holding nothing,
        so after blocker A's fix it is not armed, no client is built, and blocker C's gate stops
        the write before the close branch is reached at all. Two independent fixes cover the
        same route."""
        self.seed(holdings={}, last_pct=5.0, last_event_date=FORMED, open_event=EVENT,
                  processed=[])
        resting = (("AAPL", "buy", 2.5, 0.0, EVENT), ("BBB", "buy", 2.5, 0.0, EVENT))
        slot, live, st = self.cycle(pct=0, holdings={}, resting=resting)
        self.assertNotIn("pct:5.0->0.0", st.get("processed") or [])
        self.assertFalse(slot.get("event_closed"))
        self.assertFalse(slot["writes_allowed"])

    def test_NO_EVENT_is_recorded_complete_while_ANOTHER_is_open(self):
        """**THE FIFTH DEFECT, FOUND BY THE TRANSITION TABLE.** The auditor's third condition
        reads `open_event == key`; blocker B's one-line fix stopped the close from DISCARDING
        another event's remainder and left it free to record ITSELF complete while that
        remainder was outstanding -- and the plan it read as "targets met" was empty only
        because the other event's resting orders had been subtracted from it.

        The state that reaches it: a BUY-IN arriving while the rebalance's orders are still
        working. Armed, read ok, plan empty."""
        self.seed(holdings={}, last_pct=0.0, last_event_date=FORMED, open_event=EVENT,
                  processed=[])
        resting = (("AAPL", "buy", 2.5, 0.0, EVENT), ("BBB", "buy", 2.5, 0.0, EVENT))
        slot, live, st = self.cycle(pct=5, holdings={}, resting=resting)
        self.assertEqual(slot["plan_outcome"], LC.PLAN_TARGETS_MET,
                         "the fixture no longer reaches the branch")
        self.assertTrue(slot["writes_allowed"], "the write gate stopped it first")
        self.assertFalse(slot["event_closed"])
        self.assertEqual(slot.get("blocked_by_open_event"), EVENT)
        self.assertEqual(st.get("processed") or [], [])
        self.assertEqual(st.get("open_event"), EVENT, "it discarded the remainder")
        self.assertEqual(live.placed, [])

    def test_the_CONTROL_an_event_whose_OWN_remainder_is_open_still_closes_when_it_resolves(
            self):
        """Without this, "never close while anything is open" would satisfy the two above and
        no event would ever finish."""
        self.seed(holdings={"AAPL": 2.5, "BBB": 2.5}, last_pct=5.0,
                  last_event_date="2026-08-01", open_event=EVENT, processed=[])
        slot, live, st = self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5})
        self.assertTrue(slot.get("event_closed"), slot.get("reason"))
        self.assertIn(EVENT, st.get("processed") or [])
        self.assertIsNone(st.get("open_event"))


# ----------------------------------------------------------------------------------------- #
# BLOCKER C — a cycle that could not look, or may not write, writes nothing
# ----------------------------------------------------------------------------------------- #
class ACycleThatCouldNotLookWritesNothing(_Live):
    """`reconcile` has four states so that *"I did not ask"* is distinguishable from *"nothing
    is there"*. `run_slot` refused on `truncated` and `failed` and exempted `not_attempted`
    because such a cycle *"must still compute a plan and cannot send in any case"* — both true,
    and neither covers the third thing that branch does, which is **WRITE**."""

    STATE = dict(holdings={"AAPL": 2.5, "BBB": 2.5}, last_pct=5.0,
                 last_event_date=FORMED, open_event=EVENT, processed=[])

    def _run(self, mode, **kw):
        self.seed(**dict(self.STATE))
        return self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5},
                          resting=(("AAPL", "buy", 1.0, 0.0, EVENT),), mode=mode, **kw)

    def test_the_SAME_STATE_gives_the_SAME_close_decision_in_ALL_THREE_MODES(self):
        """**THE TEST THAT WOULD HAVE CAUGHT THIS, and C is invisible to any single mode.**"""
        seen = {}
        for mode in ("live", "paper", "dry"):
            slot, live, st = self._run(mode)
            seen[mode] = (bool(slot.get("event_closed")), st.get("open_event"),
                          tuple(st.get("processed") or []))
        self.assertEqual(len(set(seen.values())), 1,
                         "the close decision depends on the MODE: %r" % (seen,))
        for mode, (closed, open_ev, processed) in seen.items():
            self.assertFalse(closed, mode)
            self.assertEqual(open_ev, EVENT, mode)
            self.assertEqual(processed, (), mode)

    def test_a_paper_cycle_leaves_a_live_slots_record_BYTE_FOR_BYTE_unchanged(self):
        self.seed(**dict(self.STATE))
        p = LC.state_path("1", self.root)
        before = io.open(p, "rb").read()
        self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5}, mode="paper")
        self.assertEqual(io.open(p, "rb").read(), before,
                         "a paper cycle wrote to a live slot's record")

    def test_a_GET_writes_NOTHING_for_any_slot(self):
        """A GET of `/admin/live-cycle` is legitimate -- it is how a reader inspects what the
        cycle WOULD do -- and it was persisting `processed`, `open_event` and
        `last_event_date`. The door's own reasoning for refusing a GET that SENDS applies word
        for word to a write: *"reachable by a retry, a prefetch, a proxy or a pasted link"*."""
        self.seed(**dict(self.STATE))
        p = LC.state_path("1", self.root)
        before = io.open(p, "rb").read()
        slot, live, _ = self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5},
                                   mode="dry", may_write=False)
        self.assertEqual(io.open(p, "rb").read(), before, "a GET wrote state")
        self.assertFalse(slot["writes_allowed"])
        self.assertIn("READ-ONLY", slot.get("writes_withheld_reason") or "")

    def test_the_door_passes_the_verb_through(self):
        """Pinned at the endpoint, because the gate is only as good as its caller."""
        src = io.open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                      encoding="utf-8").read()
        self.assertIn('may_write=(request.method == "POST")', src)

    def test_a_withheld_write_is_NOT_an_alert(self):
        """It is the correct behaviour, not a fault -- and alerting would fire on five
        scheduled cycles a day and on every GET, which is how a real alert stops being read
        (`MA21`)."""
        slot, live, st = self._run("paper")
        self.assertNotIn("state_write_failed", [a["kind"] for a in slot.get("alerts") or []])

    def test_the_reason_does_NOT_claim_the_event_closed(self):
        """With C fixed, a paper cycle computes `targets_met`, writes nothing and leaves the
        event open -- and the old text still read *"the event is closed"*, which would have
        been **the eighth message on this path asserting a property the code does not have**,
        written by the item fixing the other seven."""
        # **AN EVENT HAS TO FIRE, and my first cut had none.** `last_event_date` equal
        # to the book's `formed_on` with an unchanged percentage is the "does nothing"
        # cycle -- correct, and it computes no plan at all, so there was no reason text
        # to check and the test errored on a missing key rather than failing on a claim.
        self.seed(holdings={"AAPL": 2.5, "BBB": 2.5}, last_pct=5.0,
                  last_event_date="2026-08-01", processed=[])
        slot, live, st = self.cycle(pct=5, holdings={"AAPL": 2.5, "BBB": 2.5}, mode="paper")
        self.assertEqual(slot["plan_outcome"], LC.PLAN_TARGETS_MET)
        self.assertFalse(slot["event_closed"])
        self.assertNotIn("the event is closed", slot.get("reason") or "")
        self.assertIn("NOTHING is recorded", slot.get("reason") or "")


class OneWriteGate(unittest.TestCase):
    """Eight write sites; a condition per branch would be eight chances to miss one."""

    def test_run_slot_reaches_write_state_through_ONE_path(self):
        import inspect
        src = inspect.getsource(LC.run_slot)
        self.assertEqual(src.count("write_state(slot, st, root)"), 1,
                         "a second path to write_state exists inside run_slot")
        self.assertGreaterEqual(src.count("_write()"), 8)

    def test_the_gate_refuses_BOTH_ways(self):
        for read, may, want in ((("ok",), True, True),
                                (("ok",), False, False),
                                (("not_attempted",), True, False),
                                (("truncated",), True, False),
                                (("failed",), True, False),
                                (("",), True, False)):
            got = LC.writes_allowed({"order_read": read[0]}, may_write=may)
            self.assertEqual(got["ok"], want, "%r/%r" % (read[0], may))
            if not want:
                self.assertTrue(got["reason"])

    def test_the_last_parity_write_is_gated_on_the_SLOTS_OWN_answer(self):
        """**FOUND BY THE TRANSITION TABLE ON ITS FIRST RUN.** This write sits outside
        `run_slot` where the gate lives, and my first cut gated it on `may_write` alone -- so a
        paper cycle, a dry cycle and a PAUSED slot all still wrote to a live slot's record."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn('res.get("writes_allowed")', src)
        self.assertNotIn('if res.get("parity") is not None and may_write:', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
