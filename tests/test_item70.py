# -*- coding: utf-8 -*-
"""ITEM 70 — the auditor's fifth blocker: an event closed while this slot's orders were resting.

Item 67 taught the planner to subtract this slot's own resting same-side quantity so a remainder
could not stack. That was right, and it **changed what an empty plan means**. Before item 67 an
empty plan meant *"the reconciled holdings match the targets"*; afterwards it can also mean
*"the gap is already covered by an order that has not filled."* The close branch kept reading the
first and getting the second, and its own comment still claimed the property it had lost:

    exits_planned            : ['MSFT']
    reconcile.open_remainder : True          <- computed every cycle, READ NOWHERE
    reconcile.resting        : [{'ticker': 'MSFT', 'side': 'sell', 'qty_open': 5.0}]
    plan_outcome             : targets_met   <- the holdings are MSFT: 5 against a target of 0
    alerts                   : []
    EVENT CLOSED?            : True
    reason                   : "this event's targets are already met ... the event is closed"

The `day` order then expires unfilled and nothing retries: the event is closed, so `event_for`
returns nothing until the next rebalance.

**THE WORST CASE IS THE SELL-OUT, which is the one action Don would take in a hurry.** At 0% the
sells go out, the next cycle closes the event and writes `last_pct = 0.0`, the orders expire, and
`event_for` sees no percentage change ever again — **the slot stays fully invested at a declared
0%, silently and for good.**

Every HTTP reply here is a recorded fixture and the client is the shipped `AlpacaPaperBroker`.
Nothing touches a network, and nothing places a real order.
"""
from __future__ import annotations

import ast
import datetime as _dt
import inspect
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

import tests.test_item63 as T63                        # noqa: E402
from valuation.edge import alpaca_broker as AB         # noqa: E402
from valuation.edge import live_cycle as LC            # noqa: E402
from valuation.edge import live_slots as LS            # noqa: E402

OPEN_NOW = _dt.datetime(2026, 11, 2, 13, 36)
EVENT = "rebalance:2026-11-01"

#: The book AFTER a rebalance that dropped MSFT. AAPL alone is held.
BOOK = {"ok": True, "formed_on": "2026-11-01", "reason": "",
        "positions": [{"ticker": "AAPL", "status": "held", "weight": 1.0}]}

#: AAPL and BBB both held, for the buy cases.
BOOK_TWO = {"ok": True, "formed_on": "2026-11-01", "reason": "",
            "positions": [{"ticker": "AAPL", "status": "held", "weight": 0.5},
                           {"ticker": "BBB", "status": "held", "weight": 0.5}]}

ACCOUNT = {"id": "acct-paper-1", "account_number": "PA1", "equity": "10000",
           "cash": "10000", "buying_power": "10000",
           "non_marginable_buying_power": "10000", "status": "ACTIVE", "multiplier": "1"}


class Recorded:
    """Alpaca, replayed, with ARBITRARY resting and filled orders.

    `resting` entries are `(ticker, side, qty, filled_qty)`; set `expired=True` to replay the
    state after the `day` order has lapsed — Alpaca then reports it `expired` with the filled
    quantity it managed, which is how a partial fill that is never completed actually looks.
    """

    def __init__(self, *, holdings, resting=(), expired=False, quote=(99.0, 101.0),
                 positions=None):
        self.holdings = dict(holdings)
        self.resting = list(resting)
        self.expired = bool(expired)
        self.quote = quote
        self.positions = positions
        self.placed, self.cancelled, self.calls = [], [], []

    # -- the orders the broker would list ---------------------------------------------------
    def _orders(self):
        out = []
        for i, (t, q) in enumerate(sorted(self.holdings.items())):
            # The ORIGINAL buy-in, a different event, fully filled. This is what makes the
            # slot hold anything at all.
            out.append({"id": "f-%s" % t.lower(),
                        "client_order_id": LC.client_order_id(
                            LC.PAPER_SLOT, "rebalance:2026-07-30", t),
                        "symbol": t, "side": "buy", "qty": str(q), "filled_qty": str(q),
                        "status": "filled", "limit_price": "100",
                        "filled_avg_price": "100",
                        "submitted_at": "2026-07-30T14:4%d:00Z" % i})
        for i, (t, side, qty, fq) in enumerate(self.resting):
            out.append({"id": "r-%d" % i,
                        "client_order_id": LC.client_order_id(
                            LC.PAPER_SLOT, EVENT, t, attempt=1),
                        "symbol": t, "side": side, "qty": str(qty),
                        "filled_qty": str(fq),
                        # **THE TWO STATES THIS FIXTURE EXISTS TO TELL APART.** `new` is the
                        # order still working; `expired` is the same order after the `day`
                        # session ended, which is when the retry has to happen.
                        "status": ("expired" if self.expired else "new"),
                        "limit_price": "100",
                        "filled_avg_price": ("100" if float(fq) else None),
                        "submitted_at": "2026-11-02T14:30:00Z"})
        return out

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account"):
            return T63.Reply(dict(ACCOUNT))
        if url.endswith("/v2/positions"):
            if self.positions is not None:
                return T63.Reply(list(self.positions))
            # **A PARTIAL FILL IS A POSITION, and my first cut left it out of this list.**
            # `preflight` then refused -- "this slot's record holds BBB and the broker reports
            # no such position" -- which is that check doing its job on a fixture that was
            # lying, and it is the empty-record hole item 63 built it for.
            eff = dict(self.holdings)
            for t, side, qty, fq in self.resting:
                if float(fq or 0):
                    eff[t] = eff.get(t, 0.0) + (float(fq) if side == "buy" else -float(fq))
            pos = [{"symbol": t, "qty": str(q), "avg_entry_price": "100", "side": "long"}
                   for t, q in sorted(eff.items()) if float(q) > 0]
            return T63.Reply(pos)
        if "quotes/latest" in url:
            bp, ap = self.quote
            syms = sorted(set(list(self.holdings) + ["AAPL", "BBB", "MSFT"]))
            return T63.Reply({"quotes": {s: {"bp": bp, "ap": ap, "t": "x"} for s in syms}})
        if url.endswith("/v2/orders") and method == "GET":
            return T63.Reply(self._orders())
        if url.endswith("/v2/orders") and method == "POST":
            body = json.loads(data or "{}")
            self.placed.append(body)
            return T63.Reply(dict(body, id="srv-%d" % len(self.placed), status="new",
                                  filled_qty="0"))
        if "/v2/orders/" in url and method == "DELETE":
            self.cancelled.append(url.rsplit("/", 1)[-1])
            return T63.Reply({}, status=204)
        return T63.Reply({}, status=404)


def broker(sess):
    return AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24, session=sess)


class _Cycle(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.seed()

    def seed(self, holdings=None, **extra):
        """The slot has traded before, which is the only way it comes to hold an exit — and
        without it item 67's fresh-record check refuses the cycle before a plan exists, which
        is how four of item 69's tests once passed for the wrong reason."""
        st = {"slot": LC.PAPER_SLOT, "account_id": "acct-paper-1",
              "processed": ["rebalance:2026-07-30"],
              # **AAPL's TARGET IS ALREADY MET: 100 shares at $100 is the whole $10,000
              # slot.** My first cut held 40, so the plan had a genuine 60-share buy in it and
              # the outcome was correctly `work` -- a fixture that could not reach the state it
              # was written to test.
              "holdings": dict(holdings if holdings is not None
                               else {"AAPL": 100.0, "MSFT": 5.0})}
        st.update(extra)
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)

    def cycle(self, sess, book=None, now=None, day=None):
        """A real `run_cycle`, paper mode, with the REAL broker class on a recorded session.

        **`day` OVERRIDES `_stamp`, WHICH IS WHAT THE CEILING READS.** Passing a different
        `now` is not enough: the ceiling records `_stamp()` -- the wall clock -- so a test that
        only moved `now` would spend one real date over and over and the count would never
        rise. Item 67's suite overrides `_stamp` for the same reason, and the underlying
        mismatch is the auditor's own non-blocking item 7.
        """
        real = LC._stamp
        try:
            if day:
                LC._stamp = (lambda d=day: "%sT14:40:00Z" % d)
            out = LC.run_cycle(env={}, mode=LC.PAPER, now=(now or OPEN_NOW), root=self.root,
                               book=(book or BOOK), paper_client=broker(sess),
                               notify_send=(lambda cfg, b, ch=None: True))
        finally:
            LC._stamp = real
        return out, (out.get("paper") or {})

    def state(self):
        return LC.read_state(LC.PAPER_SLOT, self.root)


# ----------------------------------------------------------------------------------------- #
# THE THREE CASES THE AUDITOR REPRODUCED
# ----------------------------------------------------------------------------------------- #
class AnEventDoesNotCloseWhileMyOwnOrdersAreResting(_Cycle):
    """**All three returned `plan_outcome=targets_met`, closed the event, raised no alert, and
    were never retried once the `day` order expired.**"""

    # -- CASE A: a resting SELL covering a whole exit ---------------------------------------
    def test_CASE_A_a_resting_sell_covering_an_exit_does_NOT_close_the_event(self):
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        _, p = self.cycle(sess)
        self.assertEqual(p["plan_outcome"], LC.PLAN_RESTING, p.get("reason"))
        self.assertNotIn(EVENT, self.state().get("processed") or [],
                         "the event was recorded COMPLETE with the sell still resting")
        self.assertEqual(self.state().get("open_event"), EVENT,
                         "the event is not open, so nothing will retry")
        self.assertNotIn("targets are already met", p.get("reason") or "")

    def test_CASE_A_it_sends_NOTHING_so_the_subtraction_still_holds(self):
        """**THE OTHER HALF OF THE FIX, and the reason leaving the event open is safe.** Item
        67's subtraction must keep applying, or holding the event open would re-send the sale
        every cycle and stack five sell orders against five shares."""
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        self.cycle(sess)
        self.assertEqual(sess.placed, [], "it re-sent an order that is already working")

    def test_CASE_A_IT_RETRIES_once_the_order_has_gone(self):
        """**THE POSITIVE CONTROL. Without it every assertion above is satisfied by a slot that
        has simply stopped acting** — which is exactly how item 67's day-boundary test came to
        pass through this blocker."""
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        self.cycle(sess)
        self.assertEqual(sess.placed, [])
        sess.expired = True          # the `day` order lapsed at the close
        _, p = self.cycle(sess)
        sold = [(o["symbol"], o["side"]) for o in sess.placed]
        self.assertIn(("MSFT", "sell"), sold, "the exit was never retried: %r" % (sold,))

    # -- CASE B: a resting BUY covering a whole target --------------------------------------
    def test_CASE_B_a_resting_buy_covering_a_target_does_NOT_close_the_event(self):
        """*"a buy, which is what the first live event is."*"""
        self.seed(holdings={"AAPL": 50.0})
        sess = Recorded(holdings={"AAPL": 50.0}, resting=[("BBB", "buy", 50.0, 0.0)])
        _, p = self.cycle(sess, book=BOOK_TWO)
        self.assertEqual(p["plan_outcome"], LC.PLAN_RESTING, p.get("reason"))
        self.assertEqual(self.state().get("open_event"), EVENT)
        self.assertNotIn(EVENT, self.state().get("processed") or [])

    def test_CASE_B_IT_RETRIES_and_BBB_is_eventually_bought(self):
        self.seed(holdings={"AAPL": 50.0})
        sess = Recorded(holdings={"AAPL": 50.0}, resting=[("BBB", "buy", 50.0, 0.0)])
        self.cycle(sess, book=BOOK_TWO)
        self.assertEqual(sess.placed, [])
        sess.expired = True
        _, p = self.cycle(sess, book=BOOK_TWO)
        bought = [(o["symbol"], o["side"]) for o in sess.placed]
        self.assertIn(("BBB", "buy"), bought, "BBB was never bought: %r" % (bought,))

    # -- CASE C: a PARTIAL fill --------------------------------------------------------------
    def test_CASE_C_a_partial_fill_does_NOT_close_the_event(self):
        """*"3 of 5 filled, 2 resting, targets_met, closed, and the 2 are never completed."*"""
        self.seed(holdings={"AAPL": 50.0})
        sess = Recorded(holdings={"AAPL": 50.0}, resting=[("BBB", "buy", 50.0, 30.0)])
        _, p = self.cycle(sess, book=BOOK_TWO)
        self.assertEqual(p["plan_outcome"], LC.PLAN_RESTING, p.get("reason"))
        self.assertEqual(self.state().get("open_event"), EVENT)

    def test_CASE_C_the_REMAINDER_is_completed_once_the_order_has_gone(self):
        """And the remainder is what the next cycle must send — not the whole target, which is
        item 67's blocker, and not nothing, which is this one."""
        self.seed(holdings={"AAPL": 50.0})
        sess = Recorded(holdings={"AAPL": 50.0}, resting=[("BBB", "buy", 50.0, 30.0)])
        self.cycle(sess, book=BOOK_TWO)
        self.assertEqual(sess.placed, [])
        sess.expired = True
        _, p = self.cycle(sess, book=BOOK_TWO)
        bbb = [o for o in sess.placed if o["symbol"] == "BBB"]
        self.assertTrue(bbb, "the remainder was never sent")
        # 30 of 50 filled, so the slot now holds 30 and the remainder is 20.
        self.assertAlmostEqual(float(bbb[0]["qty"]), 20.0, places=6,
                               msg="the remainder was not 20: %r" % (bbb[0],))


# ----------------------------------------------------------------------------------------- #
# THE 0% SELL-OUT — the case that decides the severity
# ----------------------------------------------------------------------------------------- #
class TheSellOutIsNotLeftHalfDone(unittest.TestCase):
    """**`last_pct` IS WRITTEN TO 0.0, SO THE SELL-OUT CANNOT RE-FIRE.** Once the event closes,
    `event_for` sees no rebalance and no percentage change, and the slot holds everything it was
    told to sell at a declared 0% — with no alert, for good.

    **Driven through `run_slot` rather than `run_cycle`, and the reason is structural rather
    than convenience:** `run_cycle`'s paper leg is pinned at `PAPER_PCT = 100.0`, so a
    percentage change to zero is not reachable through it at all. `run_slot` is the shipped
    function the paper leg calls, with the shipped `AlpacaPaperBroker` on a recorded session.

    **AND IT RUNS AS THE PAPER SLOT, BECAUSE A LIVE SLOT AT 0% CANNOT GET PAST PARITY --
    a SEPARATE defect, reported and NOT fixed here (see `ALiveSlotAtZeroCannotPassParity`).**
    A parity mismatch alerts on the paper slot and refuses on a live one, which is §8's own
    precondition and the right default; it means this suite demonstrates item 70's mechanism
    rather than papering over that gate.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    SLOT = LC.PAPER_SLOT

    def seed(self, **extra):
        st = {"slot": self.SLOT, "account_id": "acct-paper-1", "last_pct": 100.0,
              "last_event_date": "2026-11-01",
              "processed": ["rebalance:2026-11-01"],
              "holdings": {"AAPL": 5.0, "BBB": 5.0}}
        st.update(extra)
        p = LC.state_path(self.SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)

    def slot(self, sess, *, pct, day="2026-11-02", send=True):
        cl = broker(sess)
        marks = {t: {"mid": 100.0} for t in ("AAPL", "BBB")}
        return LC.run_slot(
            self.SLOT, pct=pct,
            armed_state={"armed": True, "reason": "fixture"},
            book=BOOK_TWO, client=cl, equity=1000.0, account=dict(ACCOUNT),
            marks=marks, root=self.root, session_ok=True, send=send,
            paper_targets=None, paper_value=None, account_id="acct-paper-1")

    def test_the_sell_out_with_orders_RESTING_does_not_close_the_event(self):
        self.seed()
        sess = Recorded(holdings={"AAPL": 5.0, "BBB": 5.0},
                        resting=[("AAPL", "sell", 5.0, 0.0), ("BBB", "sell", 5.0, 0.0)])
        # The resting coids carry the pct event, not the rebalance.
        sess.resting = [("AAPL", "sell", 5.0, 0.0), ("BBB", "sell", 5.0, 0.0)]
        got = self._pct_cycle(sess)
        self.assertEqual(got["plan_outcome"], LC.PLAN_RESTING, got.get("reason"))
        st = LC.read_state(self.SLOT, self.root)
        self.assertEqual(st.get("open_event"), "pct:100.0->0.0")
        self.assertNotIn("pct:100.0->0.0", st.get("processed") or [])

    def test_the_SLOT_IS_NOT_LEFT_FULLY_INVESTED_AT_A_DECLARED_ZERO(self):
        """**THE WHOLE POINT.** Cycle 1 rests, the order expires overnight, and cycle 2 on the
        NEXT DAY must still sell — even though `last_pct` has moved to 0 and `event_for` is
        silent. The remainder path is what carries it, and it only runs if `open_event` is set.
        """
        self.seed()
        sess = Recorded(holdings={"AAPL": 5.0, "BBB": 5.0},
                        resting=[("AAPL", "sell", 5.0, 0.0), ("BBB", "sell", 5.0, 0.0)])
        self._pct_cycle(sess)
        self.assertEqual(sess.placed, [], "it re-stacked the sells")
        # ---- A DAY BOUNDARY, and the `day` orders have lapsed ----------------------------
        sess.expired = True
        got = self._pct_cycle(sess, pct=0.0)
        sold = sorted((o["symbol"], o["side"]) for o in sess.placed)
        self.assertEqual(sold, [("AAPL", "sell"), ("BBB", "sell")],
                         "the slot stayed fully invested at a declared 0%%: %r" % (sold,))

    def test_event_for_IS_silent_by_then_which_is_why_open_event_has_to_carry_it(self):
        """The mechanism, asserted directly so the test above cannot be mistaken for luck:
        after `last_pct` is 0.0 the three events are all absent, and the ONLY thing that makes
        the slot act is `open_event`."""
        st = {"last_event_date": "2026-11-01", "last_pct": 0.0}
        ev = LS.event_for(st, BOOK_TWO, 0.0)
        self.assertFalse(ev["act"], ev["reason"])

    def _pct_cycle(self, sess, pct=0.0):
        """One `run_slot` at 0%, with the resting coids rewritten to the pct event's key."""
        key = "pct:100.0->%s" % pct
        orig = sess._orders

        def patched():
            rows = orig()
            for r in rows:
                if r["id"].startswith("r-"):
                    r["client_order_id"] = LC.client_order_id(self.SLOT, key,
                                                              r["symbol"], attempt=1)
                else:
                    r["client_order_id"] = LC.client_order_id(
                        self.SLOT, "rebalance:2026-07-30", r["symbol"])
            return rows
        sess._orders = patched
        return self.slot(sess, pct=pct)


# ----------------------------------------------------------------------------------------- #
# A NEW DEFECT, FOUND BY THIS SUITE'S OWN FIXTURE AND REPORTED RATHER THAN FIXED
# ----------------------------------------------------------------------------------------- #
class TheLiveSellOutWasUnreachableAndIsNowFixed(unittest.TestCase):
    """**ITEM 70 REPORTED THIS AND DECLINED TO FIX IT; ITEM 71 FIXED IT -- and the auditor
    corrected item 70's diagnosis on the way, which is the part worth keeping.**

    Item 70's own note read: *"Pinned here as a TEST OF CURRENT BEHAVIOUR so it cannot be
    lost... The shape of a fix, for whoever takes it: when every target is zero there are no
    weights to diff, so parity is VACUOUS rather than FAILED."* That fix was **necessary and
    not sufficient**: the auditor applied exactly it and nothing transmitted, because
    **parity is the THIRD of four gates**. In order: `armed()` refuses at `pct <= 0`; no live
    client is built for an unarmed slot; parity refuses a non-positive side; and the send gate
    requires both `armed` and a client.

    **Item 70's suite could see only the third because its fixture passed
    `armed_state={"armed": True}` and a client -- the two things production withholds at 0%.**
    That is item 65's lesson one level up, and item 71's tests derive `armed_state` from the
    environment for exactly this reason.

    A FOURTH gate turned up when the auditor's question was asked again of the fix:
    `parity_absent` would have blocked the wind-down on any day the paper book was
    unavailable. See `test_an_ABSENT_paper_book_does_not_block_a_wind_down`.
    """

    def test_parity_is_VACUOUS_when_every_target_is_zero(self):
        """Item 70's own proposed shape, now shipped."""
        got = LC.parity({"AAPL": 0.0}, {"AAPL": 0.0}, live_value=0.0, paper_value=1000.0)
        self.assertTrue(got["ok"], got["reason"])
        self.assertFalse(got["measured"], "a vacuous parity must not claim to be MEASURED")
        self.assertIn("no weights to diff", got["reason"])

    def test_and_it_did_NOT_widen_to_any_other_case(self):
        """The reason the change is safe, and it is structural rather than careful: a positive
        percentage with a positive equity always gives a positive slot value, and `targets`
        refuses a non-positive equity before parity is called -- so "every target is zero" is
        reachable only from a zero percentage."""
        # a zero value with REAL targets still refuses
        g = LC.parity({"AAPL": 500.0}, {"AAPL": 500.0}, live_value=0.0, paper_value=1000.0)
        self.assertFalse(g["ok"], g["reason"])
        # an EMPTY target map is not a wind-down -- it is a book that failed to load
        g = LC.parity({}, {"AAPL": 500.0}, live_value=0.0, paper_value=1000.0)
        self.assertFalse(g["ok"], g["reason"])
        # and a real mismatch still fails
        g = LC.parity({"AAPL": 900.0, "BBB": 100.0}, {"AAPL": 500.0, "BBB": 500.0},
                      live_value=1000.0, paper_value=1000.0)
        self.assertFalse(g["ok"], g["reason"])

    def test_a_live_slot_at_zero_WITH_HOLDINGS_now_SELLS(self):
        """**THE PROPERTY, and it is measured through the production arming path in
        `tests/test_item71.py` rather than here** -- this suite's harness supplies
        `armed_state`, which is precisely why it could not see the defect. Kept here as the
        narrow statement that `armed` itself now distinguishes the two states, with the
        end-to-end version next door."""
        e = {"LIVE_PILOT_ENABLED": "1", "ALPACA_ACCOUNT_1_KEY_ID": "k",
             "ALPACA_ACCOUNT_1_SECRET_KEY": "s", "ALPACA_ACCOUNT_1_LIVE_PCT": "0"}
        flat = LS.armed(1, e, holds=False)
        self.assertFalse(flat["armed"], flat["reason"])
        self.assertFalse(flat["sell_only"])
        held = LS.armed(1, e, holds=True)
        self.assertTrue(held["armed"], held["reason"])
        self.assertTrue(held["sell_only"])

    def test_the_refusal_NO_LONGER_asserts_that_it_holds_nothing(self):
        """*"slot 1 is at 0%, so it holds nothing"* was false of the only slot that needs a
        sell-out, and it reached the cycle's own `reason`."""
        e = {"LIVE_PILOT_ENABLED": "1", "ALPACA_ACCOUNT_1_KEY_ID": "k",
             "ALPACA_ACCOUNT_1_SECRET_KEY": "s", "ALPACA_ACCOUNT_1_LIVE_PCT": "0"}
        self.assertNotIn("so it holds nothing", LS.armed(1, e, holds=True)["reason"])
        self.assertNotIn("so it holds nothing", LS.armed(1, e, holds=False)["reason"])

    def test_the_PAUSE_still_pauses_WITHOUT_selling(self):
        """`LIVE_PILOT_ENABLED=0` is a different instruction from 0% and must stay one. The
        order of `armed`'s conditions is what keeps them different."""
        e = {"LIVE_PILOT_ENABLED": "0", "ALPACA_ACCOUNT_1_KEY_ID": "k",
             "ALPACA_ACCOUNT_1_SECRET_KEY": "s", "ALPACA_ACCOUNT_1_LIVE_PCT": "0"}
        a = LS.armed(1, e, holds=True)
        self.assertFalse(a["armed"], a["reason"])
        self.assertFalse(a["sell_only"])
        self.assertIn("PAUSED", a["reason"])

    def test_an_ABSENT_paper_book_does_not_block_a_wind_down(self):
        """**THE FOURTH GATE, which nobody had named.** Fixing `armed` and parity's zero-target
        case still left `parity_absent` refusing a live slot with no paper comparison -- and the
        paper slot runs at 100%, so the comparison this branch waits for cannot exist for a
        wind-down. Waiting for evidence that cannot exist is a refusal with no condition that
        lifts it."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn("elif is_live_slot and sell_only:", src)
        self.assertIn("parity_vacuous_wind_down", src)
        # and the ordinary absent case is untouched for every event that HAS weights
        self.assertIn("parity_absent", src)

    def test_a_WIND_DOWN_with_a_paper_comparison_SELLS(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        st = {"slot": "1", "account_id": "acct-paper-1", "last_pct": 100.0,
              "last_event_date": "2026-11-01", "processed": ["rebalance:2026-11-01"],
              "holdings": {"AAPL": 5.0, "BBB": 5.0}}
        p = LC.state_path("1", root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        sess = Recorded(holdings={"AAPL": 5.0, "BBB": 5.0})
        for t in sess._orders():
            pass
        got = LC.run_slot(
            "1", pct=0.0, armed_state={"armed": True, "reason": "fixture"},
            book=BOOK_TWO, client=broker(sess), equity=1000.0, account=dict(ACCOUNT),
            marks={t: {"mid": 100.0} for t in ("AAPL", "BBB")}, root=root,
            session_ok=True, send=True,
            paper_targets={"AAPL": 0.0, "BBB": 0.0}, paper_value=1000.0,
            account_id="acct-paper-1", sell_only=True)
        # It plans both sells AND transmits them. Before item 71 it planned both and sent
        # neither, with the reason naming parity.
        self.assertEqual(sorted(o["ticker"] for o in got["orders"]), ["AAPL", "BBB"])
        self.assertEqual(sorted((o["symbol"], o["side"]) for o in sess.placed),
                         [("AAPL", "sell"), ("BBB", "sell")])
        self.assertTrue(got["parity"]["ok"])
        self.assertFalse(got["parity"]["measured"], "vacuous must not claim to be measured")

    def test_a_WIND_DOWN_with_NO_paper_comparison_STILL_SELLS(self):
        """**THE FOURTH GATE, end to end.** With no paper targets at all a live slot used to
        refuse on `parity_absent` -- correct for any event that HAS weights, and a refusal with
        no condition that lifts it for a wind-down, because the paper slot runs at 100% and so
        the comparison can never exist for this event."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        st = {"slot": "1", "account_id": "acct-paper-1", "last_pct": 100.0,
              "last_event_date": "2026-11-01", "processed": ["rebalance:2026-11-01"],
              "holdings": {"AAPL": 5.0, "BBB": 5.0}}
        p = LC.state_path("1", root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        sess = Recorded(holdings={"AAPL": 5.0, "BBB": 5.0})
        got = LC.run_slot(
            "1", pct=0.0, armed_state={"armed": True, "reason": "fixture"},
            book=BOOK_TWO, client=broker(sess), equity=1000.0, account=dict(ACCOUNT),
            marks={t: {"mid": 100.0} for t in ("AAPL", "BBB")}, root=root,
            session_ok=True, send=True, paper_targets=None, paper_value=None,
            account_id="acct-paper-1", sell_only=True)
        self.assertEqual(sorted((o["symbol"], o["side"]) for o in sess.placed),
                         [("AAPL", "sell"), ("BBB", "sell")])
        self.assertIn("vacuous", (got["parity"]["reason"] or "").lower())

    def test_and_a_NON_wind_down_with_no_paper_comparison_STILL_REFUSES(self):
        """The control that stops the above being a hole: `C5` is intact for every event that
        has weights to compare."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        st = {"slot": "1", "account_id": "acct-paper-1", "last_pct": 100.0,
              "last_event_date": "2026-11-01", "processed": ["rebalance:2026-11-01"],
              "holdings": {"AAPL": 5.0, "BBB": 5.0}}
        p = LC.state_path("1", root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        sess = Recorded(holdings={"AAPL": 5.0, "BBB": 5.0})
        got = LC.run_slot(
            "1", pct=50.0, armed_state={"armed": True, "reason": "fixture"},
            book=BOOK_TWO, client=broker(sess), equity=1000.0, account=dict(ACCOUNT),
            marks={t: {"mid": 100.0} for t in ("AAPL", "BBB")}, root=root,
            session_ok=True, send=True, paper_targets=None, paper_value=None,
            account_id="acct-paper-1", sell_only=False)
        self.assertEqual(sess.placed, [])
        self.assertIn("parity", (got.get("reason") or ""))

    def test_the_PAPER_slot_is_NOT_blocked_which_is_why_this_suite_can_demonstrate_the_fix(self):
        """The paper slot alerts on a parity mismatch and sends anyway -- correctly, since it IS
        the comparison and gating it would stop the mechanism that produces one."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn("if is_live_slot:", src)
        self.assertIn("is_live_slot = (str(slot) != PAPER_SLOT)", src)


# ----------------------------------------------------------------------------------------- #
# ITEM 67's OWN DAY-BOUNDARY TEST, RE-CHECKED
# ----------------------------------------------------------------------------------------- #
class Item67sDayBoundaryTestPassedForTheWrongReason(_Cycle):
    """The auditor: *"driving its fixture directly leaves `open_event=None` and
    `processed=['rebalance:2026-10-22']` — the assertion is satisfied by the slot having stopped
    acting, which is not the property it names."*

    Its own assertion (nothing was re-sent) is TRUE and remains true; what it could not see is
    the close. So the property it names is now asserted as well, here rather than by weakening
    it — the subtraction it was written for is tested in its own suite and still passes.
    """

    def test_the_event_IS_STILL_OPEN_across_a_day_boundary(self):
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        self.cycle(sess)
        self.assertEqual(self.state().get("open_event"), EVENT,
                         "day 1 closed the event with the order still resting")
        # The next calendar day, same resting order, still working.
        self.cycle(sess, now=_dt.datetime(2026, 11, 3, 13, 36))
        self.assertEqual(sess.placed, [], "it re-sent across the boundary")
        self.assertEqual(self.state().get("open_event"), EVENT,
                         "day 2 closed the event with the order still resting")

    def test_and_it_is_NOT_a_slot_that_has_stopped_acting(self):
        """The distinction the auditor drew, asserted: once the order is gone it trades."""
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        self.cycle(sess)
        self.cycle(sess, now=_dt.datetime(2026, 11, 3, 13, 36))
        sess.expired = True
        self.cycle(sess, now=_dt.datetime(2026, 11, 4, 13, 36))
        self.assertTrue(sess.placed, "the slot had genuinely stopped acting")


# ----------------------------------------------------------------------------------------- #
# A RESTING ORDER FROM A *DIFFERENT* EVENT IS NOT A REASON TO HOLD THIS ONE OPEN
# ----------------------------------------------------------------------------------------- #
class TheEventIsReadFromTheOrderId(unittest.TestCase):
    """`reconcile`'s resting list is scoped to the SLOT and not to the event, which is correct
    for item 67's subtraction — a leftover from the previous event must still be subtracted. But
    holding THIS event open on a leftover nobody is waiting for would stall every subsequent
    rebalance behind it."""

    def test_this_events_order_counts(self):
        r = [{"coid": LC.client_order_id("1", EVENT, "AAPL", attempt=1), "ticker": "AAPL"}]
        self.assertEqual(len(LC.resting_for_event(r, "1", EVENT)), 1)

    def test_a_PREVIOUS_events_order_does_NOT(self):
        r = [{"coid": LC.client_order_id("1", "rebalance:2026-07-30", "AAPL", attempt=1),
              "ticker": "AAPL"}]
        self.assertEqual(LC.resting_for_event(r, "1", EVENT), [])

    def test_a_PREFIX_of_another_pct_key_does_NOT_match(self):
        """`pct:100.0->0.0` is a string prefix of `pct:100.0->0.05`, and a naive `startswith`
        on the key alone would match it. The separator the writer emits is what prevents it."""
        r = [{"coid": LC.client_order_id("1", "pct:100.0->0.05", "AAPL", attempt=1),
              "ticker": "AAPL"}]
        self.assertEqual(LC.resting_for_event(r, "1", "pct:100.0->0.0"), [])

    def test_a_TICKER_CARRYING_A_DASH_still_matches(self):
        """The other side of the same hazard: splitting a coid on `-` would mis-parse `BRK-B`
        as well as a dated event key, which is why the prefix is DERIVED from the writer."""
        r = [{"coid": LC.client_order_id("1", EVENT, "BRK-B", attempt=1), "ticker": "BRK-B"}]
        self.assertEqual(len(LC.resting_for_event(r, "1", EVENT)), 1)

    def test_the_prefix_is_DERIVED_from_the_generator_and_not_typed(self):
        """`MA5`. A second format string for the same id is a second format."""
        src = inspect.getsource(LC.resting_for_event)
        self.assertIn("client_order_id(slot", src)
        self.assertNotIn('"%s-%s-"', src)
        self.assertNotIn('.split("-")', src)

    def test_the_none_key_matches_nothing(self):
        """A cycle with no event has no orders of its own to wait for, and `"none"` is a real
        key the writer can emit — so matching on it would hold an eventless cycle open."""
        r = [{"coid": LC.client_order_id("1", "none", "AAPL", attempt=1), "ticker": "AAPL"}]
        self.assertEqual(LC.resting_for_event(r, "1", "none"), [])


# ----------------------------------------------------------------------------------------- #
# THE LATENT SECOND INSTANCE: PLAN_BLOCKED promised the event stayed open and closed it
# ----------------------------------------------------------------------------------------- #
class PlanBlockedNowKeepsItsOwnPromise(_Cycle):
    """Its alert says *"The event stays OPEN and the next cycle tries again."* It then wrote
    `last_event_date` — the one field `event_for` keys on — and left `open_event` unset, which
    is the one field the remainder path reads. One alert, then silence, with the rebalance
    abandoned at half the target.
    """

    def blocked(self):
        """A resting order whose open quantity the broker did not report — the one route to
        `PLAN_BLOCKED` that item 69 left reachable, and the auditor's own fixture shape."""
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        orig = sess._orders

        def patched():
            rows = orig()
            for r in rows:
                if r["id"].startswith("r-"):
                    r.pop("qty", None)          # no open quantity to subtract
            return rows
        sess._orders = patched
        return sess

    def test_the_outcome_IS_blocked(self):
        _, p = self.cycle(self.blocked())
        self.assertEqual(p["plan_outcome"], LC.PLAN_BLOCKED, p.get("reason"))

    def test_the_event_IS_ACTUALLY_OPEN(self):
        _, p = self.cycle(self.blocked())
        self.assertEqual(self.state().get("open_event"), "rebalance:2026-11-01",
                         "the branch promised the event stays open and closed it")

    def test_THE_NEXT_CYCLE_ACTS(self):
        """The property the promise is about, and the one the auditor measured as false: cycle 2
        found no event and no remainder and returned early."""
        sess = self.blocked()
        self.cycle(sess)
        # Same book, same day: `event_for` is silent now that `last_event_date` is written, so
        # anything that happens on cycle 2 happens through the remainder path.
        got2, p2 = self.cycle(sess)
        self.assertNotEqual(p2.get("reason") or "", "")
        self.assertNotIn("and no percentage change, so the slot does nothing",
                         p2.get("reason") or "",
                         "the rebalance was abandoned after one alert")

    def test_AND_IT_ESCALATES_rather_than_stalling_for_ever(self):
        """**KEEPING IT OPEN IS ONLY SAFE IF IT CAN END.** A permanently blocked event that
        stays open for ever would queue every later rebalance behind it — a silent hold in place
        of a silent close. The branch's own old comment claimed it escalated through the ceiling
        and could not reach it: the ceiling sits 100 lines below and the branch returns first.
        """
        sess = self.blocked()
        kinds, days = [], ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05",
                           "2026-11-06", "2026-11-09", "2026-11-10")
        for d in days:
            _, p = self.cycle(sess, day=d)
            kinds.extend(a["kind"] for a in p["alerts"])
        # **ACCUMULATED ACROSS THE LOOP RATHER THAN READ OFF THE LAST CYCLE.** My first cut
        # read the final cycle, which is the one AFTER the ceiling fired -- by then the event
        # is closed and the slot correctly does nothing, so an empty alert list reported "it
        # never escalates" about a path that had escalated the cycle before.
        self.assertIn("event_attempts_exhausted", kinds,
                      "a permanent block never escalates: %r" % (kinds,))
        self.assertIsNone(self.state().get("open_event"),
                          "an exhausted event stays open for ever and blocks the next one")

    def test_it_escalates_on_the_SIXTH_trading_day_and_not_the_sixth_CYCLE(self):
        """`MAX_EVENT_TRADING_DAYS = 5` and the test is `len(days) > 5`, so five days of
        blockage are tolerated and the sixth stops it. **Pinned against the CYCLE count because
        there are now five scheduled cycles a day**, which is the false alarm item 64 removed
        and then reintroduced by adding four more schedules."""
        sess = self.blocked()
        fired = None
        for n, d in enumerate(("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05",
                               "2026-11-06", "2026-11-09"), start=1):
            # Two cycles on each date: a day must cost one day however many times it runs.
            for _ in range(2):
                _, p = self.cycle(sess, day=d)
                if any(a["kind"] == "event_attempts_exhausted" for a in p["alerts"]):
                    fired = fired or n
        self.assertEqual(fired, LC.SETTLE.MAX_EVENT_TRADING_DAYS + 1,
                         "it stopped on day %r rather than on day %d"
                         % (fired, LC.SETTLE.MAX_EVENT_TRADING_DAYS + 1))


# ----------------------------------------------------------------------------------------- #
# WHAT THE OLD CODE DID — every case above, against the shipped behaviour before this item
# ----------------------------------------------------------------------------------------- #
class TheOldCodeFailedEveryOneOfThese(_Cycle):
    """**THE CONTROL THAT MAKES THE SUITE EVIDENCE RATHER THAN DECORATION.** Each assertion
    above is re-run with `plan_outcome` restored to its pre-item-70 definition — which is
    exactly `(orders → WORK, skipped → BLOCKED, else TARGETS_MET)` — and must come back the
    other way."""

    def setUp(self):
        super().setUp()
        self.real = LC.plan_outcome

        def old(plan, *, resting=None):             # the pre-item-70 body, verbatim
            if (plan or {}).get("orders"):
                return LC.PLAN_WORK
            return (LC.PLAN_BLOCKED if (plan or {}).get("skipped")
                    else LC.PLAN_TARGETS_MET)
        LC.plan_outcome = old
        self.addCleanup(setattr, LC, "plan_outcome", self.real)

    def test_the_resting_sell_CLOSED_the_event(self):
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        _, p = self.cycle(sess)
        self.assertEqual(p["plan_outcome"], LC.PLAN_TARGETS_MET)
        self.assertIn(EVENT, self.state().get("processed") or [])
        self.assertIsNone(self.state().get("open_event"))
        self.assertIn("targets are already met", p.get("reason") or "")

    def test_and_it_raised_NO_alert(self):
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        _, p = self.cycle(sess)
        self.assertEqual([a["kind"] for a in p["alerts"]], [])

    def test_and_NOTHING_RETRIED_once_the_order_expired(self):
        """The half that costs money: the slot keeps a name the Index dropped."""
        sess = Recorded(holdings={"AAPL": 100.0, "MSFT": 5.0},
                        resting=[("MSFT", "sell", 5.0, 0.0)])
        self.cycle(sess)
        sess.expired = True
        _, p = self.cycle(sess)
        self.assertEqual(sess.placed, [], "fixture mismatch: the old code DID retry")
        self.assertIn("so the slot does nothing", p.get("reason") or "")

    def test_the_partial_fill_CLOSED_the_event_too(self):
        self.seed(holdings={"AAPL": 50.0})
        sess = Recorded(holdings={"AAPL": 50.0}, resting=[("BBB", "buy", 50.0, 30.0)])
        _, p = self.cycle(sess, book=BOOK_TWO)
        self.assertEqual(p["plan_outcome"], LC.PLAN_TARGETS_MET)
        self.assertIn(EVENT, self.state().get("processed") or [])


# ----------------------------------------------------------------------------------------- #
# THE SHAPE OF THE FIX
# ----------------------------------------------------------------------------------------- #
class OnlyTargetsMetStillClosesAnEvent(unittest.TestCase):
    def test_the_fourth_outcome_is_DECLARED(self):
        self.assertIn(LC.PLAN_RESTING, LC.PLAN_OUTCOMES)
        self.assertEqual(len(set(LC.PLAN_OUTCOMES)), 4)

    def test_it_does_NOT_close_an_event(self):
        self.assertEqual(LC.PLAN_OUTCOMES_THAT_CLOSE_AN_EVENT, (LC.PLAN_TARGETS_MET,))
        self.assertNotIn(LC.PLAN_RESTING, LC.PLAN_OUTCOMES_THAT_CLOSE_AN_EVENT)

    def test_ORDERS_STILL_BEAT_A_REST(self):
        """Item 67's per-name granularity, which the auditor checked and approved: a cycle with
        work to do sends it even while something else of its own is resting."""
        self.assertEqual(
            LC.plan_outcome({"orders": [{"ticker": "A"}], "skipped": []},
                            resting=[{"ticker": "B"}]), LC.PLAN_WORK)

    def test_A_SKIP_BEATS_A_REST(self):
        """Both keep the event open, so the precedence decides only which one a reader is told
        about — and "I could not work out what to do" needs a human while "my order has not
        filled yet" does not."""
        self.assertEqual(
            LC.plan_outcome({"orders": [], "skipped": [{"ticker": "A"}]},
                            resting=[{"ticker": "B"}]), LC.PLAN_BLOCKED)

    def test_an_OMITTED_resting_argument_is_the_OLD_behaviour(self):
        """So a call site that was not updated gets exactly what it got before — which is why
        every call site is checked by test rather than assumed."""
        self.assertEqual(LC.plan_outcome({"orders": [], "skipped": []}),
                         LC.PLAN_TARGETS_MET)

    def test_EVERY_call_site_passes_resting(self):
        """`MA21`'s converse: a default that silently restores the defect is worse than no
        default, so the default is checked AND every real caller is required to override it."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "plan_outcome"]
        self.assertEqual(len(calls), 1, "a second call site appeared: %d" % len(calls))
        self.assertIn("resting", [k.arg for k in calls[0].keywords])


class TheCeilingIsOneDefinition(unittest.TestCase):
    """`B7`. Three branches need it and two of them could not reach it, so a copy would have
    been a second set of reset rules — and those took items 64 and 67 to get right."""

    def test_the_fingerprint_is_built_ONCE(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertEqual(src.count("sorted(held_map)"), 1)
        self.assertEqual(src.count("event_fingerprint\"] = prints_seen"), 1)

    def test_EVERY_branch_that_holds_an_event_open_calls_it(self):
        """**FIVE CALLERS SINCE ITEM 77, and this guard going red is it working.** Item 70
        made the ceiling one definition for three branches; item 72 added the fourth -- the
        branch that refuses while ANOTHER event's orders are working, which returned before the
        ceiling and so was item 70's own silent hold in a new place.

        **THE FIFTH IS ITEM 77's, AND IT IS THE SAME SHAPE A THIRD TIME: the CASH-WAIT branch,
        which holds the event open and returned above the ceiling.** That is correct for the
        cash wait itself -- Don: *"Waiting for cash ... does not burn the ceiling"* -- and the
        same ruling's next sentence is *"The ceiling still applies to orders that are sent and
        never fill."* A resting order on one name alongside a cash gap on another took the
        early return, so it could never escalate. The new call is conditional on this slot
        having its own resting orders, which is exactly the half of the ruling that was
        missing.

        The number is asserted because the property is "every branch that holds an event open
        can escalate", and a branch added without a ceiling call is the defect. If a sixth
        appears, this is where it has to be acknowledged."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "note_no_progress"]
        self.assertEqual(len(calls), 5, "expected five callers, found %d" % len(calls))

    def test_a_branch_that_may_run_OUT_OF_SESSION_does_not_spend_a_trading_day(self):
        """`note_trading_day`'s own precondition is that every date reaching it is one the
        orders window was open on. The resting and blocked branches can both run outside it, so
        a Saturday manual cycle must not spend a day off a ceiling whose alert says TRADING
        DAYS — item 64's false-alarm family, which item 64 itself reintroduced."""
        st, out = {"holdings": {"AAPL": 1.0}}, {}
        LC.note_no_progress(st, out, "k", counts_a_day=False, on_date="2026-11-07")
        self.assertEqual(st["event_attempt_days"]["k"], [])
        self.assertFalse(out["attempt_day_counted"])
        LC.note_no_progress(st, out, "k", counts_a_day=True, on_date="2026-11-09")
        self.assertEqual(st["event_attempt_days"]["k"], ["2026-11-09"])
        self.assertTrue(out["attempt_day_counted"])

    def test_progress_RESETS_the_count(self):
        """Carried from item 64, re-asserted here because the code moved: the counter resets
        whenever the holdings change, so a rebalance that is filling normally cannot stop
        itself."""
        st, out = {"holdings": {"AAPL": 1.0}}, {}
        for d in ("2026-11-02", "2026-11-03", "2026-11-04"):
            LC.note_no_progress(st, out, "k", counts_a_day=True, on_date=d)
        self.assertEqual(len(st["event_attempt_days"]["k"]), 3)
        st["holdings"] = {"AAPL": 2.0}                      # a fill
        LC.note_no_progress(st, out, "k", counts_a_day=True, on_date="2026-11-05")
        self.assertEqual(st["event_attempt_days"]["k"], ["2026-11-05"])

    def test_a_SELL_counts_as_progress(self):
        """Item 67's fix, re-asserted: the old test was `held_now > baseline`, which a sell can
        never satisfy, and the sells go first."""
        st, out = {"holdings": {"AAPL": 5.0}}, {}
        LC.note_no_progress(st, out, "k", counts_a_day=True, on_date="2026-11-02")
        st["holdings"] = {"AAPL": 2.0}                      # a partial sale
        LC.note_no_progress(st, out, "k", counts_a_day=True, on_date="2026-11-03")
        self.assertEqual(st["event_attempt_days"]["k"], ["2026-11-03"])


class OpenRemainderIsNowRead(unittest.TestCase):
    """The auditor's non-blocking item 5: *"`reconcile.open_remainder` should either be read or
    removed."* It was computed on every cycle and read nowhere."""

    def test_it_reaches_the_cycle_output(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn('out["open_remainder"] = bool(rec.get("open_remainder"))', src)

    def test_it_is_a_DIFFERENT_fact_from_this_events_resting_orders(self):
        """And both ship, because conflating them is what would stall a later rebalance behind
        a leftover order nobody is waiting for."""
        self.assertIn("resting_this_event", io.open(LC.__file__, encoding="utf-8").read())


class TheFalseCommentIsGone(unittest.TestCase):
    """*"'met' is a property of the reconciled holdings and not of whether this particular cycle
    transmitted anything."* True when written, false as of item 67 — and the auditor records
    nearly trusting it. Sixth time on this path that a docstring asserted a property the code
    had lost."""

    def test_the_claim_is_not_in_the_tree(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertNotIn("not of whether this particular cycle", src)

    def test_and_the_correction_says_WHY(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn("made it false", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
