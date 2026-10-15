# -*- coding: utf-8 -*-
"""ITEM 58b — the cycle runner, the paper slot, parity, alerts, the feed gap, dividends.

**THE TEST THAT MATTERS MOST IS THE IDEMPOTENCY ONE**, and it exists because my own first cut
failed it: the second cycle re-sent both orders. Two causes, both repaired and both pinned here
— the remainder path keyed its event as `"none"` (never recorded as processed), and the slot's
holdings were never reconciled from fills, so every cycle planned the full buy-in again.

Nothing here touches a network. Every broker is a stub, and a test asserts the module places an
order through exactly one call so a stub cannot miss a second path.
"""
import ast
import datetime as _dt
import json
import os
import shutil
import tempfile
import unittest

import state_isolation  # noqa: F401

from valuation.edge import live_cycle as LC
from valuation.edge import live_notify as LN
from valuation.edge import live_slots as LS

#: A FIXED TIME INSIDE THE ORDERS WINDOW, injected into every cycle below.
#:
#: **THIS SUITE USED TO READ THE WALL CLOCK AND ITS VERDICT CHANGED AT MIDNIGHT.** It passed at
#: 21:30 ET and failed at 00:26 ET the next day, because `run_cycle` gated sending on the
#: session state and the session state depends on the hour. A suite that is green every evening
#: and red every morning is the shape that gets re-run until it passes instead of diagnosed --
#: and diagnosing it is what found the product defect this file now pins.
#:
#: 2026-10-15 is a Thursday and 10:40 ET is the scheduled cycle's own summer minute, so the
#: tests run at the time the thing under test actually runs.
OPEN_NOW = _dt.datetime(2026, 10, 15, 10, 40)

#: And one outside it, for the refusal direction.
CLOSED_NOW = _dt.datetime(2026, 10, 15, 20, 15)

BOOK = {"ok": True, "formed_on": "2026-07-30",
        "positions": [{"ticker": "A", "status": "held", "weight": 0.6},
                      {"ticker": "B", "status": "held", "weight": 0.4},
                      {"ticker": "GONE", "status": "exited", "weight": 0.0}]}


class Stub:
    """A broker that fills whatever share of each order it is told to, and remembers all of it.

    It is deliberately NOT a mock of `AlpacaPaperBroker`: it implements the four methods the
    runner uses, so a runner that reached for a fifth would fail here rather than pass against
    a mock that answers everything.
    """

    def __init__(self, fill=1.0, equity=1000.0, improve=0.003, reject=False):
        self.sent, self.fill, self.equity = [], fill, equity
        self.improve, self.reject = improve, reject

    def account(self):
        return {"equity": self.equity}

    def quotes(self, tickers):
        return {t: {"mid": 10.0, "bid": 9.99, "ask": 10.01} for t in tickers}

    def positions(self):
        agg = {}
        for o in self.sent:
            agg[o["symbol"]] = agg.get(o["symbol"], 0.0) + o["filled_qty"]
        return [{"ticker": k, "qty": v} for k, v in agg.items() if v > 0]

    def orders(self, status="all", limit=100):
        return list(self.sent)

    def place_limit(self, ticker, side, qty, limit_price, client_order_id=None):
        if self.reject:
            return {"ok": False, "error": "the stub broker refuses this order"}
        self.sent.append({"symbol": ticker, "side": side, "qty": qty,
                          "limit_price": limit_price,
                          "filled_avg_price": round(limit_price * (1 - self.improve), 4),
                          "filled_qty": round(qty * self.fill, 9),
                          "status": "filled" if self.fill >= 1 else "partially_filled",
                          "client_order_id": client_order_id or ""})
        return {"ok": True, "id": "stub-%d" % len(self.sent)}


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def cycle(self, client, **kw):
        """Every cycle runs at an INJECTED time inside the orders window. See `OPEN_NOW`."""
        kw.setdefault("send", True)
        kw.setdefault("now", OPEN_NOW)
        return LC.run_cycle(env={}, root=self.root, book=BOOK, paper_client=client,
                            notify_send=(lambda cfg, body: True), **kw)


class ARestartNeverRepeatsAnOrder(_Tmp):
    """Item 58b step 2's own words. **MY FIRST CUT FAILED THIS AND IT COST TWO REAL BUGS.**"""

    def test_a_second_cycle_on_the_same_event_sends_nothing(self):
        c = Stub(fill=1.0)
        first = self.cycle(c)["paper"]
        self.assertTrue(first["acted"])
        self.assertEqual(len(c.sent), 2)
        again = self.cycle(c)["paper"]
        self.assertEqual(len(c.sent), 2, "A RESTART REPEATED AN ORDER")
        self.assertFalse(again["acted"])
        self.assertIn("already met", again["reason"])

    def test_three_further_cycles_still_send_nothing(self):
        c = Stub(fill=1.0)
        self.cycle(c)
        for _ in range(3):
            self.cycle(c)
        self.assertEqual(len(c.sent), 2)

    def test_the_event_is_recorded_as_processed_and_stays_OPEN_until_it_is_met(self):
        """MY OWN EXPECTATION WAS WRONG HERE AND THE CODE IS RIGHT. Right after sending, the
        runner has no fill to read -- an order it submitted a second ago has not been
        reconciled -- so the event is correctly still OPEN. It closes on the NEXT cycle, when
        the reconciled holdings meet the targets. Asserting closure immediately would have
        demanded the runner believe its own submissions, which is the second of the two bugs
        this class exists to pin."""
        c = Stub(fill=1.0)
        self.cycle(c)
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual(st["processed"], ["rebalance:2026-07-30"])
        self.assertEqual(st["open_event"], "rebalance:2026-07-30")
        self.cycle(c)
        self.assertIsNone(LC.read_state(LC.PAPER_SLOT, self.root)["open_event"],
                          "the event stayed open after its targets were met")

    def test_the_remainder_is_never_keyed_none(self):
        """THE FIRST BUG, PINNED. `event_for` returns `"none"` once the slot has acted, so the
        remainder path used to compute `key = "none"` -- a key never written to `processed`,
        which is why it could never recognise itself as done."""
        c = Stub(fill=0.5)
        self.cycle(c)
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual(st["open_event"], "rebalance:2026-07-30")
        self.assertNotIn("none", st["processed"])
        r = self.cycle(c)["paper"]
        self.assertEqual(r["event"], "remainder")
        self.assertEqual(r.get("event_key"), "rebalance:2026-07-30")


class LiveShaped(Stub):
    """A stub with the LIVE client's reply shape.

    `_LiveClient._request` wraps every reply in `{ok, status, data}` and `AlpacaPaperBroker`
    unwraps it, so the runner reads a live account's equity one level deeper. A live-slot test
    handed the paper shape reads `equity = None`, refuses at preflight, and then passes or fails
    for a reason unrelated to whatever it was testing.
    """

    def account(self):
        return {"ok": True, "status": 200, "data": {"equity": self.equity}}

    def positions(self):
        return {"ok": True, "data": [{"symbol": k, "qty": v}
                                     for k, v in self._agg().items() if v > 0]}

    def _agg(self):
        agg = {}
        for o in self.sent:
            agg[o["symbol"]] = agg.get(o["symbol"], 0.0) + o["filled_qty"]
        return agg


class TheTwoClientsReplyDifferentlyAndTheRunnerKnows(unittest.TestCase):
    """PINNED BECAUSE A REFACTOR WOULD UNIFY IT BY ACCIDENT, and because it already cost a
    confusing test failure: the live reader is one level deeper than the paper one."""

    def test_the_runner_reads_the_live_equity_out_of_data(self):
        import inspect
        src = inspect.getsource(LC.run_cycle)
        self.assertIn('((acct or {}).get("data") or {}).get("equity")', src)

    def test_and_the_paper_equity_directly(self):
        import inspect
        src = inspect.getsource(LC.run_cycle)
        self.assertIn('eq = (acct or {}).get("equity")', src)

    def test_an_unreadable_live_equity_REFUSES_rather_than_sizing_on_nothing(self):
        """The safe direction, and the one that made the fixture bug harmless."""
        got = LS.preflight(book=BOOK, equity=None,
                           marks={"A": {"mid": 10}, "B": {"mid": 10}},
                           slot_record={}, pct=5.0)
        self.assertFalse(got["ok"])
        self.assertTrue(any("equity" in p for p in got["problems"]))


class ThePaperOnlySendMode(_Tmp):
    """ITEM 2b. The paper slot has to be able to actually trade paper, and no live slot may
    transmit while it does.

    **WHY THIS MODE EXISTS.** The scheduled workflow first shipped with no run token at all,
    which made the cycle a dry run for EVERY slot including the paper one -- so the paper slot
    would never have placed an order and the 2026-10-22 rebalance could not have been watched
    on paper, which is the paper slot's whole purpose. The dry-run default was right for the
    live slots and wrong for the paper one.
    """

    def _armed_live_env(self):
        """A FULLY ARMED live slot: pilot on, a non-zero percentage, an authorized holder and a
        key pair. This is the hostile case -- a slot that WOULD trade under `run=1`."""
        return {"LIVE_PILOT_ENABLED": "1",
                "ALPACA_ACCOUNT_1_KEY_ID": "fake-key-id",
                "ALPACA_ACCOUNT_1_SECRET_KEY": "fake-secret",
                "ALPACA_ACCOUNT_1_LIVE_PCT": "5",
                "ALPACA_ACCOUNT_1_HOLDER": LS.holder(1, {}) or "Don"}

    def test_run_paper_SENDS_for_the_paper_slot(self):
        c = Stub(fill=1.0)
        r = LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=BOOK, paper_client=c,
                         notify_send=(lambda cfg, b: True))
        self.assertEqual(r["mode"], "paper")
        self.assertTrue(r["paper"]["acted"])
        self.assertEqual(len(c.sent), 2)

    def test_run_paper_CANNOT_REACH_THE_LIVE_CLIENT(self):
        """2b's first required pin. The factory is the only way a live client could be built in
        a test, so if it is never called no live client exists -- and the production path's one
        construction site sits behind the same gate."""
        built = []
        env = self._armed_live_env()
        a = LS.armed(1, env)
        self.assertTrue(a["armed"], "the fixture is not actually armed: %r" % a)
        LC.run_cycle(env=env, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=BOOK,
                     paper_client=Stub(), notify_send=(lambda cfg, b: True),
                     live_client_factory=lambda n: built.append(n) or LiveShaped())
        self.assertEqual(built, [], "a PAPER cycle constructed a live client")

    def test_run_paper_SENDS_NOTHING_for_a_fully_armed_live_slot(self):
        """2b's second required pin. The slot still computes its plan and still diffs against
        the paper slot -- it just transmits nothing."""
        env = self._armed_live_env()
        sent = []

        class Spy(LiveShaped):
            def place_limit(self, *a, **k):
                sent.append(a)
                return super().place_limit(*a, **k)

        r = LC.run_cycle(env=env, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=BOOK,
                         paper_client=Stub(), notify_send=(lambda cfg, b: True),
                         live_client_factory=lambda n: Spy())
        self.assertEqual(sent, [], "an armed live slot transmitted during a PAPER cycle")
        rows = [x for x in r["slots"] if str(x["slot"]) == "1"]
        self.assertEqual(len(rows), 1, r["slots"])
        self.assertEqual(rows[0]["sent"], [])
        self.assertTrue(rows[0]["armed"], "the slot was not armed, so this proves nothing")
        self.assertIn("PAPER-ONLY", rows[0].get("paper_mode_note") or "")

    def test_the_armed_live_slot_STILL_COMPUTES_so_the_pin_is_not_vacuous(self):
        """A POSITIVE CONTROL. If the slot were refused for some unrelated reason it would
        send nothing either, and the two tests above would pass while measuring nothing."""
        env = self._armed_live_env()
        r = LC.run_cycle(env=env, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=BOOK,
                         paper_client=Stub(), notify_send=(lambda cfg, b: True),
                         live_client_factory=lambda n: LiveShaped())
        row = [x for x in r["slots"] if str(x["slot"]) == "1"][0]
        self.assertTrue(row["orders"], "the slot computed no plan, so nothing was proven")
        self.assertIsNotNone(row.get("parity"), "no parity diff was computed")

    def test_run_1_behaves_exactly_as_before(self):
        """2b's third required pin: live mode is unchanged. An armed slot transmits."""
        env = self._armed_live_env()
        sent = []

        class Spy(LiveShaped):
            def place_limit(self, t, side, qty, lp, client_order_id=None):
                sent.append((t, side))
                return super().place_limit(t, side, qty, lp, client_order_id)

        r = LC.run_cycle(env=env, mode=LC.LIVE, now=OPEN_NOW, root=self.root, book=BOOK,
                         paper_client=Stub(), notify_send=(lambda cfg, b: True),
                         live_client_factory=lambda n: Spy())
        self.assertEqual(r["mode"], "live")
        self.assertTrue(sent, "an armed live slot sent nothing in LIVE mode")
        self.assertTrue(r["send_requested"])

    def test_live_mode_still_refuses_an_UNARMED_slot(self):
        """`run=1` is a permission, never an instruction. At 0% the slot is not armed and
        nothing is sent -- every slot ships at 0%."""
        env = dict(self._armed_live_env(), ALPACA_ACCOUNT_1_LIVE_PCT="0")
        sent = []

        class Spy(LiveShaped):
            def place_limit(self, *a, **k):
                sent.append(a)
                return super().place_limit(*a, **k)

        LC.run_cycle(env=env, mode=LC.LIVE, now=OPEN_NOW, root=self.root, book=BOOK, paper_client=Stub(),
                     notify_send=(lambda cfg, b: True), live_client_factory=lambda n: Spy())
        self.assertEqual(sent, [])

    def test_DRY_sends_nothing_anywhere(self):
        c = Stub()
        env = self._armed_live_env()
        r = LC.run_cycle(env=env, mode=LC.DRY, now=OPEN_NOW, root=self.root, book=BOOK,
                         paper_client=c,
                         notify_send=(lambda cfg, b: True),
                         live_client_factory=lambda n: LiveShaped())
        self.assertEqual(len(c.sent), 0)
        self.assertEqual(r["mode"], "dry")

    def test_an_unrecognised_token_is_DRY_and_never_live(self):
        """`MA6`'s direction. The old door used `bool(request.args.get("run"))`, so `?run=0`
        was truthy and would have placed LIVE orders."""
        for tok in ("0", "no", "false", "", None, "dryrun", "yes", "LIVE_PLEASE"):
            self.assertEqual(LC.send_mode(tok)["mode"], LC.DRY, repr(tok))
        for tok in ("1", "live", "LIVE", " live "):
            self.assertEqual(LC.send_mode(tok)["mode"], LC.LIVE, repr(tok))
        for tok in ("paper", "PAPER", " paper"):
            self.assertEqual(LC.send_mode(tok)["mode"], LC.PAPER, repr(tok))

    def test_an_unrecognised_token_SAYS_nothing_was_sent(self):
        """Silence would read identically to a quiet market, so the reason has to say it."""
        self.assertIn("NOTHING was sent", LC.send_mode("0")["reason"])
        self.assertIn("truthiness", LC.send_mode("no")["reason"])

    def test_the_old_send_keyword_still_resolves_the_SAFE_way(self):
        """A caller left on `send=` is not silently downgraded to dry -- `send=True` means
        LIVE, as it did before. `mode=` wins when both are given."""
        env = self._armed_live_env()
        r = LC.run_cycle(env=env, send=True, now=OPEN_NOW, root=self.root, book=BOOK,
                         paper_client=Stub(),
                         notify_send=(lambda cfg, b: True),
                         live_client_factory=lambda n: LiveShaped())
        self.assertEqual(r["mode"], "live")
        r2 = LC.run_cycle(env=env, send=False, now=OPEN_NOW, root=self.root, book=BOOK,
                          paper_client=Stub(),
                          notify_send=(lambda cfg, b: True))
        self.assertEqual(r2["mode"], "dry")


class TheRemainderIsTheShortfall(_Tmp):
    """THE SECOND BUG, PINNED: holdings are reconciled from FILLS, so a part fill leaves a
    smaller order and never the whole plan again."""

    def test_a_part_fill_leaves_a_strictly_smaller_order(self):
        c = Stub(fill=0.4)
        first = sorted((o["ticker"], o["qty"]) for o in self.cycle(c)["paper"]["orders"])
        second = sorted((o["ticker"], o["qty"]) for o in self.cycle(c)["paper"]["orders"])
        self.assertEqual([t for t, _ in first], [t for t, _ in second])
        for (t, a), (_, b) in zip(first, second):
            self.assertLess(b, a, "the remainder for %s is not smaller than the first plan" % t)

    def test_holdings_come_from_fills_and_not_from_submissions(self):
        """A record built from what was SENT would claim the full quantity and plan no
        remainder -- leaving the event half-done and looking complete."""
        c = Stub(fill=0.4)
        self.cycle(c)
        self.cycle(c)
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertAlmostEqual(st["holdings"]["A"], 24.0, places=6)   # 0.4 x 60, not 60

    def test_a_rejected_order_records_no_holding(self):
        c = Stub(reject=True)
        r = self.cycle(c)["paper"]
        self.assertTrue(r["acted"])
        self.assertTrue(all(not s["ok"] for s in r["sent"]))
        self.assertEqual(LC.read_state(LC.PAPER_SLOT, self.root)["holdings"], {})
        self.assertTrue(any(a["kind"] == "broker_error" for a in r["alerts"]))

    def test_reconcile_never_records_a_negative_holding(self):
        """A short is not a position this path is authorised to take, so a sell larger than the
        record reduces to zero rather than going through it."""
        got = LC.reconcile(_Orders([{"symbol": "A", "side": "sell", "filled_qty": 5.0,
                                     "status": "filled", "client_order_id": "paper-x-A"}]),
                           {"slot": "paper", "holdings": {"A": 1.0}})
        self.assertTrue(got["ok"])
        self.assertNotIn("A", got["holdings"])


class _Orders:
    def __init__(self, rows):
        self._rows = rows

    def orders(self, status="all", limit=100):
        return list(self._rows)


class OnlyThisSlotsOwnOrdersAreRead(unittest.TestCase):
    def test_another_slots_orders_are_ignored(self):
        """Don's own holdings, and any other slot's, are never read into this slot's record --
        so the planner can only ever sell what this slot itself bought."""
        rows = [{"symbol": "A", "side": "buy", "filled_qty": 5.0, "status": "filled",
                 "client_order_id": "paper-rebalance:2026-07-30-A"},
                {"symbol": "Z", "side": "buy", "filled_qty": 99.0, "status": "filled",
                 "client_order_id": "1-rebalance:2026-07-30-Z"},
                {"symbol": "Y", "side": "buy", "filled_qty": 77.0, "status": "filled",
                 "client_order_id": ""}]
        got = LC.reconcile(_Orders(rows), {"slot": "paper"})
        self.assertEqual(sorted(got["holdings"]), ["A"])
        self.assertEqual(got["n_orders"], 1)

    def test_a_client_that_cannot_list_orders_leaves_the_record_alone(self):
        got = LC.reconcile(object(), {"slot": "paper", "holdings": {"A": 3.0}})
        self.assertFalse(got["ok"])
        self.assertEqual(got["holdings"], {"A": 3.0})
        self.assertIn("cannot list orders", got["reason"])


class OnlyTheThreeEvents(_Tmp):
    def test_a_day_with_no_event_sends_nothing(self):
        c = Stub(fill=1.0)
        self.cycle(c)
        n = len(c.sent)
        self.assertEqual(len(self.cycle(c)["paper"]["orders"]), 0)
        self.assertEqual(len(c.sent), n)

    def test_a_percentage_change_is_an_event(self):
        ev = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 0.0}, BOOK, 1.0)
        self.assertTrue(ev["act"])
        self.assertEqual(ev["event"], "pct_change")

    def test_a_new_rebalance_is_an_event(self):
        ev = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 1.0},
                          dict(BOOK, formed_on="2026-10-22"), 1.0)
        self.assertTrue(ev["act"])
        self.assertEqual(ev["event"], "rebalance")

    def test_nothing_in_this_module_reads_a_RETURN(self):
        """No loss stops, no drawdown rule, no drift rebalance -- §8a. Walked on the AST so a
        docstring saying the words cannot trip it, which is the substring-ban family this
        project has paid for repeatedly.
        """
        with open(LC.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        banned = {"stop_loss", "stoploss", "drawdown", "trailing_stop", "take_profit",
                  "pnl", "unrealized_pl", "unrealized_plpc", "drift_rebalance"}
        seen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                seen.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                seen.add(node.attr.lower())
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.lower() in banned:
                    seen.add(node.value.lower())
        self.assertEqual(sorted(seen & banned), [])

    def test_the_guard_can_fire(self):
        """A POSITIVE CONTROL for the AST walk above, because a guard that matches nothing
        reads exactly like a clean tree."""
        tree = ast.parse("x = account.unrealized_pl\nif x < drawdown: pass\n")
        attrs = {n.attr.lower() for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names = {n.id.lower() for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertIn("unrealized_pl", attrs)
        self.assertIn("drawdown", names)


class ABrokenInputMeansNoOrdersPlusAnAlert(_Tmp):
    def test_a_missing_price_sends_nothing_and_alerts(self):
        class NoQuotes(Stub):
            def quotes(self, tickers):
                return {}

        c = NoQuotes()
        r = self.cycle(c)["paper"]
        self.assertEqual(len(c.sent), 0)
        self.assertFalse(r["preflight"]["ok"])
        self.assertTrue(any(a["kind"] == "preflight_failed" for a in r["alerts"]))

    def test_a_failed_preflight_changes_no_holding(self):
        class NoQuotes(Stub):
            def quotes(self, tickers):
                return {}

        self.cycle(NoQuotes())
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual(st["holdings"], {})
        self.assertEqual(st["processed"], [])

    def test_the_record_versus_broker_check_is_not_vacuous(self):
        """IT WAS. The first cut passed `None` for the broker's positions, so the one check
        standing between a stale record and a sale of something the slot does not hold could
        never fire. `MA21`'s converse."""
        r = self.cycle(Stub(), send=False)["paper"]
        self.assertIsNotNone(r.get("broker_positions_read"))

    def test_a_disagreeing_record_refuses_in_both_shapes(self):
        """The caller sends a list and a mapping is the obvious thing to build; iterating a
        mapping yields its KEYS, which used to raise `AttributeError` on a string and be
        reported as "this slot failed" rather than "the shapes disagree"."""
        kw = dict(book=BOOK, equity=1000.0, marks={"A": {"mid": 10}, "B": {"mid": 10}},
                  slot_record={"A": 6.0}, pct=100.0)
        a = LS.preflight(broker_positions={"A": 2.0}, **kw)
        b = LS.preflight(broker_positions=[{"ticker": "A", "qty": 2.0}], **kw)
        self.assertFalse(a["ok"])
        self.assertEqual(a["problems"], b["problems"])


class ZeroPercentConstructsNoClient(_Tmp):
    def test_an_unconfigured_live_slot_is_shown_as_having_no_keys(self):
        """Item 58b's Done list: "Without them, shown as 'no keys yet'"."""
        r = self.cycle(Stub(), send=False)
        self.assertEqual(r["slots"], [])
        self.assertIn("no live slot has a key pair configured", r["reason"])

    def test_the_paper_slot_is_pinned_at_a_hundred_percent(self):
        self.assertEqual(LC.PAPER_PCT, 100.0)
        self.assertEqual(LC.PAPER_SLOT, "paper")
        self.assertIsInstance(LC.PAPER_SLOT, str)   # cannot collide with an integer slot


class TheParityDiff(unittest.TestCase):
    def test_identical_plans_at_the_same_value_agree(self):
        p = [{"ticker": "A", "side": "buy", "qty": 6.0, "limit_price": 10.0}]
        got = LC.parity(p, p, live_value=1000.0, paper_value=1000.0)
        self.assertTrue(got["ok"])

    def test_a_missing_name_is_a_mismatch(self):
        live = [{"ticker": "A", "side": "buy", "qty": 6.0, "limit_price": 10.0}]
        paper = live + [{"ticker": "B", "side": "buy", "qty": 4.0, "limit_price": 10.0}]
        got = LC.parity(live, paper, live_value=1000.0, paper_value=1000.0)
        self.assertFalse(got["ok"])

    def test_it_scales_to_the_same_equity(self):
        """A live slot at a different account size must still agree in SHAPE, or the diff would
        report a mismatch on every slot whose account is not the paper account's size."""
        live = [{"ticker": "A", "side": "buy", "qty": 0.6, "limit_price": 10.0}]
        paper = [{"ticker": "A", "side": "buy", "qty": 6.0, "limit_price": 10.0}]
        got = LC.parity(live, paper, live_value=100.0, paper_value=1000.0)
        self.assertTrue(got["ok"], got.get("reason"))


class TheFeedGapMeasurement(_Tmp):
    def test_absent_is_not_zero(self):
        """`V6`/`O21-D2`'s `C5`: a measurement not yet taken and a measured gap of nothing must
        not read the same."""
        rep = LC.feed_gap_report(self.root)
        self.assertFalse(rep["complete"])
        self.assertEqual(rep["n"], 0)
        self.assertIn("no paper fill", rep["reason"])

    def test_option_stays_unmeasured_while_stock_is_measured(self):
        LC.record_feed_gap([{"ticker": "A", "kind": "stock", "mid": 10.0, "fill": 9.97,
                             "side": "buy"}], self.root)
        rep = LC.feed_gap_report(self.root)
        self.assertTrue(rep["stock"]["measured"])
        self.assertFalse(rep["option"]["measured"])
        self.assertIn("no option fill", rep["option"]["reason"])

    def test_it_is_incomplete_until_thirty(self):
        self.assertEqual(LC.FEED_GAP_N, 30)
        LC.record_feed_gap([{"ticker": "A", "kind": "stock", "mid": 10.0, "fill": 9.9,
                             "side": "buy"}], self.root)
        self.assertIn("1 of 30", LC.feed_gap_report(self.root)["reason"])

    def test_the_window_never_exceeds_thirty(self):
        rows = [{"ticker": "A", "kind": "stock", "mid": 10.0, "fill": 9.9, "side": "buy",
                 "order_id": "o%d" % i} for i in range(50)]
        LC.record_feed_gap(rows, self.root)
        self.assertEqual(LC.feed_gap_report(self.root)["n"], 30)

    def test_one_fill_is_counted_once_however_often_it_is_re_read(self):
        """`reconcile` re-reads the same filled orders on EVERY cycle, so without an
        idempotence key the window would fill up with one execution counted thirty times."""
        c = Stub(fill=1.0)
        for _ in range(5):
            self.cycle(c)
        self.assertEqual(LC.feed_gap_report(self.root)["n"], 2)

    def test_the_censoring_ships_with_the_measurement(self):
        """THE BINDING LIMITATION. Every order is a limit at the mid and a limit order never
        fills worse than its limit, so the price gap is one-sided BY CONSTRUCTION."""
        LC.record_feed_gap([{"ticker": "A", "kind": "stock", "mid": 10.0, "fill": 9.97,
                             "side": "buy"}], self.root)
        cen = LC.feed_gap_report(self.root)["censoring"]
        self.assertTrue(cen["price_gap_is_one_sided"])
        self.assertIn("never fills worse", cen["why"])
        self.assertIn("unfilled count", cen["uncensored_companion"])

    def test_a_measured_gap_is_never_unfavourable(self):
        c = Stub(fill=1.0, improve=0.003)
        self.cycle(c)
        self.cycle(c)
        self.assertLessEqual(LC.feed_gap_report(self.root)["stock"]["median_gap_frac"], 0)

    def test_only_the_paper_slot_feeds_it(self):
        """Pooling a live fill in would mix two accounts' executions into one figure about the
        free feed."""
        import inspect
        self.assertIn("if str(slot) == PAPER_SLOT:", inspect.getsource(LC.run_slot))


class Dividends(unittest.TestCase):
    def test_the_omission_is_stated_rather_than_filled_in(self):
        d = LC.DIVIDEND_STATEMENT
        self.assertFalse(d["paid_by_paper"])
        self.assertIn("does not pay dividends", d["statement"])
        self.assertIn("understates", d["statement"])

    def test_it_says_why_a_credit_would_be_worse_than_the_statement(self):
        self.assertIn("overwritten", LC.DIVIDEND_STATEMENT["why_not_credited"])

    def test_nothing_credits_a_dividend_anywhere_in_the_cycle(self):
        with open(LC.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        calls = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertEqual(sorted(c for c in calls if "dividend" in c.lower()), [])


class TheAnnouncementDiscipline(_Tmp):
    """`fleet_notify`'s rules, reused verbatim because they were paid for."""

    def setUp(self):
        super().setUp()
        self.bodies = []
        self.send = lambda cfg, body: (self.bodies.append(body) or True)

    def test_an_order_is_announced_once(self):
        a = [{"kind": "live_order_sent", "slot": "paper", "event": "rebalance:x",
              "reason": "buy A 6.000000 @ 10.00"}]
        self.assertTrue(LN.announce(a, root=self.root, send=self.send)["sent"])
        self.assertFalse(LN.announce(a, root=self.root, send=self.send)["sent"])
        self.assertEqual(len(self.bodies), 1)

    def test_a_re_priced_remainder_IS_a_new_line(self):
        """It is a new order at a new limit for a smaller quantity, so it earns a line. Only a
        byte-identical retry is suppressed."""
        base = {"kind": "live_order_sent", "slot": "paper", "event": "rebalance:x"}
        LN.announce([dict(base, reason="buy A 6.000000 @ 10.00")], root=self.root,
                    send=self.send)
        got = LN.announce([dict(base, reason="buy A 3.600000 @ 10.02")], root=self.root,
                          send=self.send)
        self.assertTrue(got["sent"])
        self.assertEqual(got["n_events"], 1)

    def test_a_repeating_condition_is_announced_once(self):
        """A slot whose price map is short a name is short it every cycle. Announcing each one
        posts the same line daily until nobody reads it, and then the day it changes nobody
        notices."""
        cond = [{"kind": "preflight_failed", "slot": "1", "reason": "no usable price for AAA"}]
        self.assertTrue(LN.announce(cond, root=self.root, send=self.send)["sent"])
        self.assertFalse(LN.announce(cond, root=self.root, send=self.send)["sent"])

    def test_a_DIFFERENT_condition_on_the_same_slot_is_news(self):
        LN.announce([{"kind": "preflight_failed", "slot": "1", "reason": "no price for AAA"}],
                    root=self.root, send=self.send)
        got = LN.announce([{"kind": "parity_mismatch", "slot": "1", "reason": "B differs"}],
                          root=self.root, send=self.send)
        self.assertTrue(got["sent"])

    def test_a_condition_clearing_is_one_line(self):
        cond = [{"kind": "preflight_failed", "slot": "1", "reason": "no usable price"}]
        LN.announce(cond, root=self.root, send=self.send)
        got = LN.announce([], root=self.root, send=self.send)
        self.assertTrue(got["sent"])
        self.assertEqual(got["n_cleared"], 1)
        self.assertIn("has cleared", self.bodies[-1])

    def test_a_quiet_cycle_stays_quiet(self):
        got = LN.announce([], root=self.root, send=self.send)
        self.assertFalse(got["sent"])
        self.assertTrue(got["quiet"])
        self.assertEqual(self.bodies, [])

    def test_a_failed_post_does_not_advance_the_record(self):
        """A failed post that moved the watermark would lose the very order it failed to
        announce, silently and permanently."""
        a = [{"kind": "live_order_sent", "slot": "paper", "event": "e", "reason": "buy A"}]
        self.assertFalse(LN.announce(a, root=self.root,
                                     send=lambda cfg, b: False)["sent"])
        self.assertTrue(LN.announce(a, root=self.root, send=self.send)["sent"])

    def test_a_webhook_that_raises_never_raises_out(self):
        def boom(cfg, body):
            raise RuntimeError("discord is down")

        got = LN.announce([{"kind": "broker_error", "slot": "1", "reason": "x"}],
                          root=self.root, send=boom)
        self.assertFalse(got["sent"])
        self.assertIn("webhook failed", got["reason"])

    def test_a_notifier_failure_is_never_the_cycles(self):
        def boom(cfg, body):
            raise RuntimeError("discord is down")

        r = LC.run_cycle(env={}, root=self.root, book=BOOK, send=True,
                         now=OPEN_NOW, paper_client=Stub(), notify_send=boom)
        self.assertTrue(r["ok"])
        self.assertFalse(r["announced"]["sent"])

    def test_the_body_carries_no_return_figure(self):
        """§8's horizon is pre-committed and a Discord line is not where a figure gets read
        early -- `fleet_notify`'s prohibition, same words."""
        body = LN.compose(LN.pending([{"kind": "live_order_sent", "slot": "paper",
                                       "event": "e", "reason": "buy A 6.0 @ 10.00"}],
                                     self.root))
        low = body.lower()
        for word in ("p&l", "pnl", "profit", "return", "gain", "up ", "down ", "%"):
            self.assertNotIn(word, low, "the body carries %r" % word)


class OneSlotsFailureNeverStopsAnother(_Tmp):
    """The module docstring's own promise, and the code used to break it on one line."""

    def test_a_paper_account_that_raises_does_not_take_the_cycle_down(self):
        """`pc.account()` sat outside any `try`, so a blip on the paper side raised into the
        outer handler and returned having run NOTHING -- costing every live slot its dry run
        and its parity diff, in an account the live slots do not even use."""
        class Blip(Stub):
            def account(self):
                raise RuntimeError("the broker timed out")

        r = self.cycle(Blip())
        self.assertTrue(r["ok"], r.get("reason"))
        self.assertTrue(any(a["kind"] == "paper_account_unreadable" for a in r["alerts"]))

    def test_an_unbuildable_paper_client_still_lets_the_cycle_report(self):
        """The ordinary state before Don's keys exist: no client, every slot still runs, and
        the reason says which one could not."""
        r = LC.run_cycle(env={}, root=self.root, book=BOOK, send=False,
                         now=OPEN_NOW, notify_send=(lambda cfg, b: True))
        self.assertTrue(r["ok"])
        self.assertIsNotNone(r["paper"])

    def test_a_quote_failure_refuses_rather_than_trading_at_any_price(self):
        """A missing price is a BROKEN INPUT, never a reason to trade -- so the slot refuses
        at preflight. The direction matters: the alternative is an order at a guessed mid."""
        class NoQuotes(Stub):
            def quotes(self, tickers):
                raise RuntimeError("the quote feed is down")

        r = self.cycle(NoQuotes())
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["paper"]["orders"]), 0)


class TheRecordSurvivesAGarbageFile(_Tmp):
    def test_an_unreadable_state_file_reads_as_empty_and_never_raises(self):
        os.makedirs(LC.live_dir(self.root), exist_ok=True)
        with open(LC.state_path(LC.PAPER_SLOT, self.root), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual(st["processed"], [])

    def test_an_unreadable_notify_file_reads_as_empty(self):
        os.makedirs(LC.live_dir(self.root), exist_ok=True)
        with open(LN.state_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("[]")
        self.assertEqual(LN._read(self.root)["announced"], [])

    def test_a_record_from_a_different_schema_is_not_trusted(self):
        os.makedirs(LC.live_dir(self.root), exist_ok=True)
        with open(LN.state_path(self.root), "w", encoding="utf-8") as fh:
            json.dump({"schema": "live_notify/0", "announced": ["x"]}, fh)
        self.assertEqual(LN._read(self.root)["announced"], [])


class TheGateIsTheORDERSWindowAndNotTheClose(unittest.TestCase):
    """**THE SHIPPED CONTRADICTION, PINNED. THE SCHEDULED CYCLE COULD NEVER HAVE SENT.**

    `run_slot` gated sending on `market_session.session_state().ok`, which answers *"has today's
    session CLOSED"* and is true only from 16:15 ET -- it exists to decide when the Index may be
    MARKED. The cycle is scheduled at 14:40 UTC, which is 10:40 ET in summer and 09:40 ET in
    winter, chosen precisely BECAUSE a fractional order must be a `day` limit order and a `day`
    order placed outside market hours is not worked.

    So the gate and the schedule were picked for opposite reasons, and together they meant the
    paper slot would compute a plan every weekday and transmit nothing, for ever, while
    reporting "the session is closed" -- which reads as a sensible refusal rather than as a
    contradiction. Don would have watched the 2026-10-22 rebalance not happen.

    Found because this suite's own verdict changed at midnight.
    """

    def test_the_orders_window_is_OPEN_at_the_scheduled_minute_in_both_regimes(self):
        from valuation.screener.market_session import orders_window
        for et in (_dt.datetime(2026, 7, 16, 10, 40),     # 14:40 UTC in EDT
                   _dt.datetime(2026, 1, 15, 9, 40)):     # 14:40 UTC in EST
            self.assertTrue(orders_window(et)["ok"], et)

    def test_and_session_state_is_SHUT_at_that_same_minute(self):
        """The sharp form: the old gate was closed exactly when the cycle runs."""
        from valuation.screener.market_session import session_state
        for et in (_dt.datetime(2026, 7, 16, 10, 40), _dt.datetime(2026, 1, 15, 9, 40)):
            self.assertFalse(session_state(et)["ok"], et)

    def test_the_cycle_asks_the_orders_window(self):
        import inspect
        src = inspect.getsource(LC.run_cycle)
        self.assertIn("orders_window(now)", src)
        self.assertNotIn("session_ok = bool(session_state", src)

    def test_both_states_are_REPORTED_so_the_two_questions_stay_visible(self):
        """A reader comparing this against the Index mark needs both, and they are now visibly
        different questions rather than one function doing two jobs."""
        r = LC.run_cycle(env={}, now=OPEN_NOW, book=BOOK, paper_client=Stub(), send=False,
                         notify_send=(lambda cfg, b: True))
        self.assertTrue((r.get("session") or {}).get("ok"))
        self.assertFalse((r.get("session_closed_state") or {}).get("ok"))

    def test_outside_the_window_it_computes_and_sends_NOTHING(self):
        """The refusal direction, and the reason must say which window -- not "the session is
        closed", which is what made the contradiction read as sensible."""
        import shutil
        import tempfile
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        c = Stub()
        r = LC.run_cycle(env={}, now=CLOSED_NOW, root=root, book=BOOK, paper_client=c,
                         send=True, notify_send=(lambda cfg, b: True))
        self.assertEqual(len(c.sent), 0)
        self.assertTrue(r["paper"]["orders"], "it should still COMPUTE the plan")
        self.assertIn("day order", r["paper"]["reason"])


class ThisSuiteDoesNotReadTheWallClock(unittest.TestCase):
    """PINNED, BECAUSE IT DID AND THE CONSEQUENCE WAS A SHIPPED DEFECT.

    This suite passed at 21:30 ET and failed at 00:26 ET the next day. A suite that is green
    every evening and red every morning gets re-run until it passes rather than diagnosed --
    and diagnosing it is what found the gate contradiction above. So the property is a test
    now, not a habit.
    """

    def test_every_cycle_in_this_file_runs_at_an_INJECTED_time(self):
        import re
        with open(__file__, encoding="utf-8") as fh:
            src = fh.read()
        calls = re.findall(r"LC\.run_cycle\((?:[^()]|\([^()]*\))*\)", src, re.S)
        self.assertGreater(len(calls), 8, "the regex stopped matching the calls")
        # The ONE call without a literal `now=` is the shared helper, which supplies it as a
        # default two lines above -- so the helper's own default is asserted instead.
        bare = [c for c in calls if "now=" not in c]
        self.assertLessEqual(len(bare), 1, bare)
        self.assertIn('kw.setdefault("now", OPEN_NOW)', src)

    def test_the_injected_time_is_actually_inside_the_window(self):
        """A positive control: an injected time OUTSIDE the window would make every sending
        test fail, and an injected time that happened to be ignored would make them pass for
        the wrong reason."""
        from valuation.screener.market_session import orders_window
        self.assertTrue(orders_window(OPEN_NOW)["ok"])
        self.assertFalse(orders_window(CLOSED_NOW)["ok"])


class TheScheduledTime(unittest.TestCase):
    def test_it_is_inside_the_session_in_both_daylight_regimes(self):
        """14:40 UTC is 10:40am ET in summer and 9:40am ET in winter. A fixed UTC cron that
        drifted outside the session would leave `day` limit orders unworked -- and this repo
        has been bitten by exactly that twice a year already."""
        self.assertEqual(LC.CYCLE_UTC, "14:40")
        h, m = (int(x) for x in LC.CYCLE_UTC.split(":"))
        for offset in (4, 5):                      # EDT, EST
            et = h - offset
            self.assertGreater(et * 60 + m, 9 * 60 + 30, "before the open at UTC-%d" % offset)
            self.assertLess(et * 60 + m, 16 * 60, "after the close at UTC-%d" % offset)


class KeyPresenceIsABoolean(unittest.TestCase):
    def test_no_value_is_ever_returned(self):
        env = {"ALPACA_PAPER_KEY_ID": "PKSECRETVALUE", "ALPACA_PAPER_SECRET_KEY": "shhh"}
        got = LC.key_presence(env)
        blob = json.dumps(got)
        self.assertNotIn("PKSECRETVALUE", blob)
        self.assertNotIn("shhh", blob)

    def test_it_says_present_when_both_are_set(self):
        got = LC.key_presence({"ALPACA_PAPER_KEY_ID": "a", "ALPACA_PAPER_SECRET_KEY": "b"})
        self.assertTrue(got["paper"]["both_present"])

    def test_one_of_two_is_NOT_present(self):
        """`MA6`: err toward the state that refuses. Half a key pair cannot authenticate, so
        reporting it as present would promise a working client that does not exist."""
        got = LC.key_presence({"ALPACA_PAPER_KEY_ID": "a"})
        self.assertFalse(got["paper"]["both_present"])


if __name__ == "__main__":
    unittest.main()
