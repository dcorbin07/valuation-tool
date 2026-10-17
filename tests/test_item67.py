# -*- coding: utf-8 -*-
"""ITEM 67 — settlement-aware rebalancing, and the fractional-share question.

Don, 2026-10-17: *"let's account for waiting for cash to settle now and try again to buy next
day when it is settled. also the whole point of us switching to alpaca from tradier was because
we could use fractional shares so lets check that now."*

Two properties carry the whole item and both are tested against **recorded Alpaca replies**
driving the **real client classes**, because item 63's blocker was that every suite modelled
this project's own interface instead of the broker's:

  * **A BUY IS NEVER SIZED OFF MARGIN BUYING POWER.** An IRA may not carry a margin debit --
    Alpaca's own words: limited margin *"does not allow for borrowing of funds, creating a
    margin debit, short selling, or selling naked options"*. So the budget is the broker's
    `non_marginable_buying_power`, and `TheBudgetNeverBorrows` drives an account whose
    `buying_power` is FOUR TIMES its cash and proves nothing above the no-borrow figure is
    transmitted.
  * **A REFUSED BUY IS A SETTLEMENT WAIT, NOT A BROKER ERROR.** The sells stand, the event
    stays open, the buys go on the next trading day, and Don is alerted only once the wait has
    outlasted T+1 by a full trading day.

Nothing here touches a network or a credential.
"""
from __future__ import annotations

import ast
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

import tests.test_item63 as T63                        # noqa: E402
from valuation.edge import alpaca_broker as AB         # noqa: E402
from valuation.edge import live_cycle as LC            # noqa: E402
from valuation.edge import live_slots as LS            # noqa: E402
from valuation.edge import settlement as SETTLE        # noqa: E402


# ----------------------------------------------------------------------------------------- #
# recorded Alpaca, extended with the two endpoints item 67 reads
# ----------------------------------------------------------------------------------------- #
class Recorded(T63.RecordedAlpaca):
    """`RecordedAlpaca` plus `/v2/assets` and `/v2/account/configurations`.

    `account_fields` replaces the account body wholesale, so a test can state the exact
    balances Alpaca reported rather than a stub of what this project would like them to be.
    """

    def __init__(self, *a, account_fields=None, assets=None, config=None,
                 reject_message=None, reject_symbols=None, **kw):
        super().__init__(*a, **kw)
        self.account_fields = account_fields
        self.assets_rows = assets
        self.config = config
        self.reject_message = reject_message
        self.reject_symbols = set(reject_symbols or ())

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account") and self.account_fields is not None:
            return T63.Reply(dict(self.account_fields))
        if url.endswith("/v2/account/configurations"):
            if self.config is None:
                return T63.Reply({}, status=404)
            return T63.Reply(dict(self.config))
        if url.endswith("/v2/assets"):
            if self.assets_rows is None:
                return T63.Reply({}, status=500)
            return T63.Reply(list(self.assets_rows))
        if url.endswith("/v2/orders") and method == "POST":
            body = json.loads(data or "{}")
            self.placed.append(body)
            sym = str(body.get("symbol") or "")
            if sym in self.reject_symbols:
                return T63.Reply({"message": "asset %s is not fractionable" % sym}, status=422)
            if self.reject_message is not None:
                return T63.Reply({"message": self.reject_message}, status=403)
            return T63.Reply(dict(body, id="srv-%d" % len(self.placed),
                                  status="new", filled_qty="0"))
        return super().request(method, url, headers=headers, params=params,
                               data=data, timeout=timeout)


def broker(sess):
    return AB.AlpacaPaperBroker(key_id="PKFIXTURE", secret_key="s" * 24, session=sess)


#: An account on 1x limited margin, which is what Alpaca documents an IRA as being.
LIMITED = {"id": "acct-1", "account_number": "PA1", "equity": "1000", "cash": "1000",
           "buying_power": "1000", "non_marginable_buying_power": "1000",
           "status": "ACTIVE", "multiplier": "1"}

#: **THE DANGEROUS ONE.** `buying_power` is 4x the cash, exactly as Alpaca documents a PDT
#: account's to be; the no-borrow figure is a quarter of it. A buy sized off `buying_power`
#: here is a margin debit.
LEVERED = {"id": "acct-1", "account_number": "PA1", "equity": "1000", "cash": "250",
           "buying_power": "4000", "regt_buying_power": "2000",
           "non_marginable_buying_power": "250", "status": "ACTIVE", "multiplier": "4"}


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def cycle(self, *, account, sess=None, day=None, equity=1000.0, book=None):
        """One slot cycle at a stated date, through the REAL paper broker."""
        sess = sess if sess is not None else Recorded(account_fields=LIMITED)
        real = LC._stamp
        try:
            if day:
                LC._stamp = (lambda d=day: "%sT14:40:00Z" % d)
            got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED,
                              book=(book or T63.BOOK), client=broker(sess), equity=equity,
                              account=account, marks=T63.MARKS, root=self.root, send=True)
        finally:
            LC._stamp = real
        return got, sess


# ----------------------------------------------------------------------------------------- #
# WHICH FIELD, AND NEVER A LEVERED ONE
# ----------------------------------------------------------------------------------------- #
class TheBudgetIsTheBrokersNoBorrowFigure(unittest.TestCase):
    """Alpaca's `/v2/account` publishes several buying-power fields with different meanings."""

    def test_the_primary_is_non_marginable_buying_power(self):
        got = SETTLE.spendable(LEVERED)
        self.assertTrue(got["ok"])
        self.assertEqual(got["field"], "non_marginable_buying_power")
        self.assertEqual(got["amount"], 250.0)

    def test_without_it_the_budget_is_the_SMALLER_of_cash_and_buying_power(self):
        """**AND THE MIN IS WHAT MAKES IT SAFE AT ANY MULTIPLIER.** Alpaca documents
        `buying_power` as equal to cash only when `multiplier` is 1, and levered above it --
        so the cash term, not a branch on the multiplier, is what bounds this. An unreported
        or wrong multiplier then cannot widen the budget."""
        a = {k: v for k, v in LEVERED.items() if k != "non_marginable_buying_power"}
        got = SETTLE.spendable(a)
        self.assertEqual(got["amount"], 250.0, got)
        self.assertIn("cash", got["field"])

    def test_cash_alone_is_usable(self):
        got = SETTLE.spendable({"cash": "40.00"})
        self.assertEqual((got["ok"], got["amount"], got["field"]), (True, 40.0, "cash"))

    def test_NO_FIGURE_IS_A_BROKEN_INPUT_AND_NOT_A_WAIT(self):
        """`MA6`'s refusing direction, and `C5`: an unreported balance is not a measured zero
        and is not evidence that funds are merely unsettled."""
        got = SETTLE.spendable({"equity": "1000"})
        self.assertFalse(got["ok"])
        self.assertIsNone(got["amount"])
        self.assertIn("no spendable figure", got["reason"])

    def test_both_client_shapes_are_accepted(self):
        """The paper broker normalises its account; `_LiveClient` returns Alpaca's raw body in
        an envelope. The two have diverged four times already."""
        self.assertEqual(SETTLE.spendable({"ok": True, "data": LIMITED})["amount"], 1000.0)
        self.assertEqual(SETTLE.spendable(LIMITED)["amount"], 1000.0)
        self.assertFalse(SETTLE.spendable({"ok": False, "data": {}})["ok"])

    def test_an_unreadable_account_sizes_nothing(self):
        for bad in (None, "nonsense", 7, []):
            self.assertFalse(SETTLE.spendable(bad)["ok"], bad)


class TheBudgetNeverBorrows(_Tmp):
    """**THE TEST THE BRIEF ASKS FOR BY NAME: it must fail if any buy is sized off margin
    buying power.**

    Driven on `LEVERED`, where `buying_power` is 4000 against 250 of cash -- so a budget that
    read `buying_power` would transmit sixteen times what the account can actually spend, and
    every penny above 250 is a margin debit in an account Alpaca says may not carry one.
    """

    def test_no_more_than_the_no_borrow_figure_is_ever_TRANSMITTED(self):
        got, sess = self.cycle(account=LEVERED, sess=Recorded(account_fields=LEVERED))
        spent = sum(float(o["qty"]) * float(o["limit_price"])
                    for o in sess.placed if o.get("side") == "buy")
        self.assertLessEqual(spent, 250.0 + 1e-9,
                             "a buy was sized above the no-borrow figure: %.2f" % spent)
        self.assertEqual(got["budget"]["field"], "non_marginable_buying_power")
        self.assertEqual(got["budget"]["amount"], 250.0)

    def test_the_rest_is_DEFERRED_rather_than_dropped(self):
        got, _ = self.cycle(account=LEVERED, sess=Recorded(account_fields=LEVERED))
        self.assertTrue(got["deferred"], "nothing was deferred on a 250-of-1000 budget")
        self.assertTrue(all(o["side"] == "buy" for o in got["deferred"]))
        self.assertIn("without borrowing", got["deferred"][0]["why"])

    def test_the_levered_fields_are_NAMED_as_refused(self):
        """Named rather than merely unread, so a reader can see they were considered."""
        self.assertIn("regt_buying_power", SETTLE.LEVERED_FIELDS)
        self.assertIn("daytrading_buying_power", SETTLE.LEVERED_FIELDS)
        self.assertEqual(SETTLE.NO_BORROW_FIELD, "non_marginable_buying_power")

    def test_ONLY_settlement_py_READS_A_BUYING_POWER_FIELD(self):
        """**ASSERTED ON THE SYNTAX TREE, over the whole live path.**

        A behavioural test proves the budget is right where it is called; it cannot prove that
        nothing ELSE in the live path reaches for a levered figure. There is one place that
        reads any buying-power key, and this is how it stays one (`B7`).
        """
        offenders = []
        for mod in (LC, LS):
            src = io.open(mod.__file__, encoding="utf-8").read()
            tree = ast.parse(src)
            # **DOCSTRINGS ARE PROSE ABOUT CODE AND ARE EXCLUDED STRUCTURALLY.** `ast.Constant`
            # covers them, and `run_slot`'s docstring names the field a buy is sized from -- so
            # the first cut of this guard fired against the correct tree. The substring-ban
            # family in an AST costume, which is the fourth time this item has hit it. A bare
            # string STATEMENT is a docstring or a comment-by-convention; excluding `Expr`
            # values catches every one without a list of exceptions to maintain.
            prose = {id(n.value) for n in ast.walk(tree)
                     if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in prose and "buying_power" in node.value):
                    offenders.append((os.path.basename(mod.__file__), node.value,
                                      node.lineno))
        # `account_report` and `account_settlement_report` REPORT the fields -- read-only, and
        # they size nothing -- so the rule is about what sizes an order. Those two are the
        # declared exception and are named rather than waved through.
        allowed_lines = set()
        for mod in (LC, LS):
            tree = ast.parse(io.open(mod.__file__, encoding="utf-8").read())
            for node in ast.walk(tree):
                if (isinstance(node, ast.FunctionDef)
                        and node.name in ("account_report", "account_settlement_report")):
                    for inner in ast.walk(node):
                        if hasattr(inner, "lineno"):
                            allowed_lines.add((os.path.basename(mod.__file__), inner.lineno))
        real = [o for o in offenders if (o[0], o[2]) not in allowed_lines]
        self.assertEqual(real, [], "the live path reads a buying-power field outside "
                                   "settlement.py and the read-only reports: %r" % real)

    def test_the_docstring_exclusion_is_not_vacuous(self):
        """A POSITIVE CONTROL. An exclusion that swallowed every string would make the guard
        above pass by seeing nothing, which is worse than not having it."""
        tree = ast.parse('"""doc buying_power."""\nx = {"buying_power": 1}\n')
        prose = {id(n.value) for n in ast.walk(tree)
                 if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
        seen = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n) not in prose and "buying_power" in n.value]
        self.assertEqual(seen, ["buying_power"], seen)

    def test_that_AST_rule_is_not_vacuous(self):
        """A POSITIVE CONTROL: the rule must be able to SEE a buying-power literal, or it
        passes by looking at nothing."""
        tree = ast.parse('x = {"buying_power": 1}\n')
        found = [n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and "buying_power" in n.value]
        self.assertEqual(found, ["buying_power"])

    def test_settlement_py_itself_never_sizes_from_a_levered_field(self):
        """It NAMES them in a constant and a docstring; it must never READ one."""
        src = io.open(SETTLE.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get" and node.args
                    and isinstance(node.args[0], ast.Constant)):
                self.assertNotIn(node.args[0].value, SETTLE.LEVERED_FIELDS,
                                 "settlement.py reads a levered field at line %d"
                                 % node.lineno)


# ----------------------------------------------------------------------------------------- #
# SELLS FIRST
# ----------------------------------------------------------------------------------------- #
class SellsGoFirst(unittest.TestCase):
    def test_the_plan_puts_every_sell_before_every_buy(self):
        plan = LS.order_plan({"AAA": 0.0, "BBB": 500.0, "CCC": 0.0, "DDD": 400.0},
                             {"AAA": 3.0, "CCC": 2.0},
                             {"AAA": {"mid": 100.0}, "BBB": {"mid": 100.0},
                              "CCC": {"mid": 100.0}, "DDD": {"mid": 100.0}})
        sides = [o["side"] for o in plan["orders"]]
        self.assertEqual(sides, ["sell", "sell", "buy", "buy"], plan["orders"])
        self.assertEqual((plan["n_sell"], plan["n_buy"]), (2, 2))
        self.assertTrue(plan["sells_first"])

    def test_it_is_deterministic(self):
        args = ({"BBB": 500.0, "AAA": 0.0}, {"AAA": 3.0},
                {"AAA": {"mid": 100.0}, "BBB": {"mid": 100.0}})
        a = [o["ticker"] for o in LS.order_plan(*args)["orders"]]
        b = [o["ticker"] for o in LS.order_plan(*args)["orders"]]
        self.assertEqual(a, b)

    def test_a_SELL_is_never_bounded_by_the_budget(self):
        """A sell RAISES cash and cannot create a debit, so no budget binds it -- which is the
        whole reason the sells go first."""
        book = {"ok": True, "formed_on": "2026-10-22", "reason": "",
                "positions": [{"ticker": "AAPL", "status": "held", "weight": 1.0}]}
        # The slot holds MSFT, which the new book does not, so the plan is a pure sell.
        st = {"slot": LC.PAPER_SLOT, "holdings": {"MSFT": 2.0}, "processed": []}
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        p = LC.state_path(LC.PAPER_SLOT, root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        sess = Recorded(account_fields={"id": "a", "account_number": "PA1",
                                        "equity": "1000", "cash": "0",
                                        "buying_power": "0",
                                        "non_marginable_buying_power": "0",
                                        "status": "ACTIVE", "multiplier": "1"},
                        positions=[{"symbol": "MSFT", "qty": "2",
                                    "avg_entry_price": "200", "side": "long"}],
                        orders=[{"client_order_id":
                                 "valquo-paper-rebalance:2026-10-22-MSFT-a1",
                                 "symbol": "MSFT", "filled_qty": "2", "side": "buy",
                                 "status": "filled", "limit_price": "200",
                                 "filled_avg_price": "200"}])
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=book,
                          client=broker(sess), equity=1000.0,
                          account={"cash": "0", "buying_power": "0",
                                   "non_marginable_buying_power": "0", "multiplier": "1"},
                          marks=T63.MARKS, root=root, send=True)
        sold = [o for o in sess.placed if o.get("side") == "sell"]
        self.assertTrue(sold, "a sell was blocked by a zero budget: %s" % got.get("reason"))


# ----------------------------------------------------------------------------------------- #
# A REFUSED BUY IS A WAIT
# ----------------------------------------------------------------------------------------- #
class ARefusedBuyIsASettlementWaitNotABrokerError(_Tmp):
    """**THE DISTINCTION DECIDES WHETHER THE SELLS STAND.** Backwards one way it cancels a
    correct rebalance; backwards the other it hides a real fault behind a daily retry."""

    def test_the_funds_message_classifies_as_a_wait(self):
        for msg in ("insufficient buying power",
                    "insufficient day trading buying power",
                    "40310000: order rejected"):
            self.assertTrue(SETTLE.is_settlement_wait(msg), msg)

    def test_other_rejections_do_NOT(self):
        """A declared vocabulary, not a loose substring -- `buying power` on its own turns up
        in refusals that are nothing to do with settlement."""
        for msg in ("asset AAPL is not fractionable",
                    "client_order_id must be unique",
                    "potential wash trade detected. use complex orders",
                    "qty must be a positive value",
                    "account is not authorized to trade"):
            self.assertFalse(SETTLE.is_settlement_wait(msg), msg)

    def test_a_broker_funds_refusal_raises_NO_broker_error(self):
        sess = Recorded(account_fields=LIMITED, reject_message="insufficient buying power")
        got, _ = self.cycle(account=LIMITED, sess=sess, day="2026-10-22")
        kinds = [a["kind"] for a in got["alerts"]]
        self.assertNotIn("broker_error", kinds, kinds)
        self.assertTrue(got["deferred"], got)
        self.assertTrue(any(r.get("awaiting_settlement") for r in got["sent"]), got["sent"])

    def test_a_NON_funds_rejection_still_raises_one(self):
        """THE POSITIVE CONTROL. A classifier that called everything a wait would silence every
        real fault, which is the worse of the two directions."""
        sess = Recorded(account_fields=LIMITED,
                        reject_message="qty must be a positive value")
        got, _ = self.cycle(account=LIMITED, sess=sess, day="2026-10-22")
        self.assertIn("broker_error", [a["kind"] for a in got["alerts"]])

    def test_a_FULLY_DEFERRED_cycle_DOES_NOT_CLOSE_THE_EVENT(self):
        """**THE DEFECT MY FIRST CUT SHIPPED, caught by item 63's parity tests.**

        The budget filter was applied to the plan itself, and the very next block closes the
        event when the plan is empty -- so a rebalance whose buys were all deferred recorded
        itself as FINISHED, dropped its counters and never re-sent. What the event still needs
        and what this cycle may send are two different lists.
        """
        broke = {"cash": "0", "buying_power": "0",
                 "non_marginable_buying_power": "0", "multiplier": "1"}
        got, sess = self.cycle(account=broke, day="2026-10-22")
        self.assertEqual(sess.placed, [], "something was transmitted on a zero budget")
        self.assertNotIn("targets are already met", got.get("reason") or "")
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual(st.get("open_event"), None,
                         "the event is not yet OPEN because nothing was sent -- but it must "
                         "also not be PROCESSED, which is the next assertion")
        self.assertNotIn("rebalance:2026-10-22", st.get("processed") or [],
                         "a fully-deferred event was recorded as processed")
        self.assertTrue(st.get("awaiting_settlement"), st)

    def test_the_INTENT_is_not_overwritten_when_nothing_is_sent(self):
        """It is one of the three sources `preflight` derives its duplicate-buy-in scope from,
        so replacing a real intent with an empty one narrows that scope -- the unsafe
        direction, and the shape of item 63's blocker 2."""
        st = {"slot": LC.PAPER_SLOT, "holdings": {}, "processed": [],
              "intent": {"event": "rebalance:2026-10-22", "at": "x",
                         "orders": [{"ticker": "AAPL", "side": "buy", "qty": 6.0,
                                     "limit_price": 100.0}]}}
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        self.cycle(account={"cash": "0", "buying_power": "0",
                            "non_marginable_buying_power": "0"}, day="2026-10-22")
        after = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual([o["ticker"] for o in (after.get("intent") or {}).get("orders") or []],
                         ["AAPL"], after.get("intent"))

    def test_the_deferred_buys_GO_on_a_later_cycle_once_cash_is_there(self):
        """The property the whole item exists for: the wait resolves by itself."""
        self.cycle(account={"cash": "0", "buying_power": "0",
                            "non_marginable_buying_power": "0"}, day="2026-10-22")
        got, sess = self.cycle(account=LIMITED, day="2026-10-23")
        self.assertEqual(len(sess.placed), 2, sess.placed)
        self.assertEqual(got["deferred"], [])
        self.assertIn("settlement_wait_cleared", got)


class TheWaitIsCountedInTradingDaysAndAlertsOnlyWhenOverdue(_Tmp):
    """US equities settle T+1, so a wait still open on the SECOND trading day after it began
    has outlasted settlement by a full trading day. That -- and only that -- is the alert."""

    def test_the_arithmetic(self):
        self.assertEqual(SETTLE.SETTLEMENT_TRADING_DAYS, 1)
        self.assertEqual(SETTLE.WAIT_ALERT_AFTER_TRADING_DAYS, 2)
        self.assertFalse(SETTLE.wait_state(["2026-10-22"])["alert"])
        self.assertFalse(SETTLE.wait_state(["2026-10-22", "2026-10-23"])["alert"])
        self.assertTrue(SETTLE.wait_state(
            ["2026-10-22", "2026-10-23", "2026-10-26"])["alert"])

    def test_a_date_is_recorded_ONCE_however_many_cycles_run(self):
        """**WHICH IS WHY IT NEEDS NO HOLIDAY CALENDAR.** A buy is only deferred inside the
        orders window, and that window is only open on a trading day -- so the dates recorded
        ARE trading days, and a weekend or a holiday contributes nothing because no cycle ran.
        """
        days = []
        for _ in range(5):
            days = SETTLE.note_trading_day(days, "2026-10-22T14:40:00Z")
        self.assertEqual(days, ["2026-10-22"])
        self.assertEqual(SETTLE.wait_state(days)["trading_days"], 1)

    def test_FIVE_CYCLES_ON_ONE_DAY_DO_NOT_ALERT(self):
        """**ITEM 64's FALSE-ALARM FAMILY, AGAINST THE REAL SCHEDULE.** Item 64 measured the
        GitHub scheduler running 3.45-7.48 hours late and added four backup crons, so
        `live-cycle.yml` now fires FIVE times a day. A wait counted in cycles would alert
        before lunch on the first day of every rebalance."""
        broke = {"cash": "0", "buying_power": "0", "non_marginable_buying_power": "0"}
        got = None
        for _ in range(5):
            got, _ = self.cycle(account=broke, day="2026-10-22")
        self.assertEqual(got["awaiting_settlement"]["trading_days"], 1)
        self.assertNotIn("settlement_wait_overdue", [a["kind"] for a in got["alerts"]])

    def test_THREE_TRADING_DAYS_DO_ALERT(self):
        """THE POSITIVE CONTROL: a wait that never resolves must escalate, or the whole
        mechanism is a way of losing a rebalance quietly."""
        broke = {"cash": "0", "buying_power": "0", "non_marginable_buying_power": "0"}
        got = None
        for d in ("2026-10-22", "2026-10-23", "2026-10-26"):
            got, _ = self.cycle(account=broke, day=d)
        self.assertIn("settlement_wait_overdue", [a["kind"] for a in got["alerts"]])
        self.assertIn("settle T+1", got["awaiting_settlement"]["reason"])

    def test_the_number_of_scheduled_cycles_a_day_is_what_the_workflow_SAYS(self):
        """Derived from the pending workflow rather than typed, so the two cannot drift --
        `MA5`. If Don's installed copy gains a sixth cron, this is what notices."""
        p = os.path.join(REPO, "pending_workflows", "live-cycle.yml")
        txt = io.open(p, encoding="utf-8").read()
        crons = [ln for ln in txt.split("\n") if ln.strip().startswith("- cron:")]
        self.assertGreaterEqual(len(crons), 5,
                                "fewer crons than item 64 installed: %r" % crons)
        # A ceiling counted in cycles would be spendable in ONE day at this schedule. That is
        # the whole argument for counting days, asserted rather than asserted-in-prose.
        self.assertGreater(len(crons), SETTLE.MAX_EVENT_TRADING_DAYS - 1)


class TheCeilingCountsTradingDays(_Tmp):
    def test_a_rebalance_that_fills_over_several_days_never_stops_itself(self):
        got = None
        for i, d in enumerate(("2026-10-22", "2026-10-23", "2026-10-26",
                               "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30")):
            qty = float(i)
            sess = Recorded(
                account_fields=LIMITED,
                orders=([{"client_order_id":
                          "valquo-paper-rebalance:2026-10-22-AAPL-a1",
                          "symbol": "AAPL", "filled_qty": str(qty), "side": "buy",
                          "status": "filled", "limit_price": "100",
                          "filled_avg_price": "100"}] if qty else []),
                positions=([{"symbol": "AAPL", "qty": str(qty),
                             "avg_entry_price": "100", "side": "long"}] if qty else []))
            got, _ = self.cycle(account=LIMITED, sess=sess, day=d)
        self.assertFalse(got.get("attempts_exhausted"), got.get("reason"))

    def test_progress_includes_a_SELL(self):
        """**THE OLD TEST WAS `held_now > baseline`, WHICH A SELL CAN NEVER SATISFY** -- and
        item 67 sends the sells first, so the sell leg of every rebalance registered as no
        progress and burned a day off the ceiling."""
        import inspect
        # REPOINTED at the function that owns the ceiling [item 70] -- see the note on the
        # sibling guard in test_item64. The property is unchanged; it moved so three branches
        # could reach one definition.
        block = inspect.getsource(LC.note_no_progress)
        self.assertIn("event_fingerprint", block)
        self.assertIn("sorted(held_map)", block)

    def test_the_counted_unit_is_reported(self):
        got, _ = self.cycle(account=LIMITED, day="2026-10-22")
        self.assertEqual(got["attempts_counted_in"], "trading days")
        self.assertEqual(got["attempt_days"], ["2026-10-22"])


# ----------------------------------------------------------------------------------------- #
# PART 2 -- FRACTIONAL SHARES
# ----------------------------------------------------------------------------------------- #
MASTER = [
    {"symbol": "AAPL", "fractionable": True, "tradable": True, "exchange": "NASDAQ",
     "status": "active", "class": "us_equity"},
    {"symbol": "MSFT", "fractionable": False, "tradable": True, "exchange": "NASDAQ",
     "status": "active", "class": "us_equity"},
    {"symbol": "XXXX", "fractionable": False, "tradable": False, "exchange": "OTC",
     "status": "active", "class": "us_equity"},
]


class WhichNamesMayBeTradedFractionally(unittest.TestCase):
    def test_the_census_counts_both_ways(self):
        sess = Recorded(account_fields=LIMITED, assets=MASTER)
        got = LC.fractional_report(broker(sess), ["AAPL", "MSFT"])
        self.assertTrue(got["ok"], got.get("reason"))
        self.assertEqual(got["n_fractionable"], 1)
        self.assertEqual(got["whole_share_only"], ["MSFT"])
        self.assertEqual(got["per_name"]["AAPL"]["fractionable"], True)
        self.assertEqual(got["n_master"], 3)

    def test_A_NAME_ABSENT_FROM_THE_MASTER_IS_NOT_REPORTED_AS_WHOLE_SHARE_ONLY(self):
        """`C5`: absent is not a measured False, and the two have different fixes -- one is a
        name Alpaca will not trade at all, the other trades in whole shares."""
        sess = Recorded(account_fields=LIMITED, assets=MASTER)
        got = LC.fractional_report(broker(sess), ["AAPL", "NOPE"])
        self.assertEqual(got["missing_from_master"], ["NOPE"])
        self.assertNotIn("NOPE", got["whole_share_only"])
        self.assertNotIn("NOPE", got["per_name"])
        self.assertIn("not in Alpaca's active US equity master", got["reason"])

    def test_an_untradable_name_is_reported_separately(self):
        sess = Recorded(account_fields=LIMITED, assets=MASTER)
        got = LC.fractional_report(broker(sess), ["XXXX"])
        self.assertEqual(got["not_tradable"], ["XXXX"])

    def test_an_UNREADABLE_master_is_unmeasured_and_says_so(self):
        sess = Recorded(account_fields=LIMITED, assets=None)   # HTTP 500
        got = LC.fractional_report(broker(sess), ["AAPL"])
        self.assertFalse(got["ok"])
        self.assertNotIn("whole_share_only", got)

    def test_no_client_is_unmeasured_and_says_so(self):
        got = LC.fractional_report(None, ["AAPL"])
        self.assertFalse(got["ok"])
        self.assertIn("UNMEASURED", got["reason"])

    def test_ONE_REQUEST_not_one_per_name(self):
        """85 names inside a web request is 85 round trips. The master is one read."""
        sess = Recorded(account_fields=LIMITED, assets=MASTER)
        LC.fractional_report(broker(sess), ["AAPL", "MSFT", "XXXX"])
        self.assertEqual(sum(1 for m, u in sess.calls if u.endswith("/v2/assets")), 1)


class WhatTheSlotDoesWithANonFractionableName(_Tmp):
    """**THE QUESTION THE BRIEF ASKS TO BE ANSWERED PLAINLY, AND THE ANSWER IS BOTH.**

    One cycle: that name does not trade and every other name does. Over several days: the
    event's targets are never met, so the ceiling eventually stops the WHOLE event -- including
    the names that would have traded. The choice between the three remedies is Don's.
    """

    def test_ONE_CYCLE_costs_only_that_name(self):
        sess = Recorded(account_fields=LIMITED, reject_symbols={"MSFT"})
        got, sess = self.cycle(account=LIMITED, sess=sess, day="2026-10-22")
        ok = [r["ticker"] for r in got["sent"] if r["ok"]]
        bad = [r["ticker"] for r in got["sent"] if not r["ok"]]
        self.assertEqual(ok, ["AAPL"], got["sent"])
        self.assertEqual(bad, ["MSFT"], got["sent"])
        self.assertIn("broker_error", [a["kind"] for a in got["alerts"]])

    def test_AND_THEN_IT_STOPS_THE_WHOLE_EVENT_after_the_ceiling(self):
        """Stated because it is the half a reader would otherwise miss, and because it is the
        reason this needs a decision rather than a note."""
        got = None
        for d in ("2026-10-%d" % n for n in (22, 23, 26, 27, 28, 29, 30)):
            sess = Recorded(account_fields=LIMITED, reject_symbols={"AAPL", "MSFT"})
            got, _ = self.cycle(account=LIMITED, sess=sess, day=d)
        self.assertTrue(got.get("attempts_exhausted"), got.get("reason"))

    def test_the_record_states_the_choice_and_does_NOT_make_it(self):
        t = LC.NON_FRACTIONABLE_TODAY
        self.assertIn("ONE name does not trade", t["what_happens"])
        self.assertIn("%d trading days" % SETTLE.MAX_EVENT_TRADING_DAYS,
                      t["and_then"] % SETTLE.MAX_EVENT_TRADING_DAYS)
        for option in ("leave it", "round", "skip"):
            self.assertIn(option, t["the_choice_is_dons"].lower())
        self.assertIn("construction changes", t["the_choice_is_dons"])


class WhatTheAccountReportsAboutFractionalTrading(unittest.TestCase):
    def test_enabled_is_reported_as_enabled(self):
        sess = Recorded(account_fields=LIMITED,
                        config={"fractional_trading": True,
                                "max_options_trading_level": 2, "no_shorting": False})
        got = LC.account_settlement_report(broker(sess))
        self.assertEqual(got["fractional_trading"], "enabled")
        self.assertEqual(got["max_options_trading_level"], 2)
        self.assertFalse(got["constructs_an_order"])

    def test_disabled_is_reported_as_disabled(self):
        sess = Recorded(account_fields=LIMITED, config={"fractional_trading": False})
        self.assertEqual(LC.account_settlement_report(broker(sess))["fractional_trading"],
                         "disabled")

    def test_AN_ABSENT_FIELD_IS_REPORTED_AS_NOT_REPORTED(self):
        """**"THE API DOES NOT SAY" IS AN ANSWER AND IS GIVEN AS ONE.** Alpaca documents
        `fractional_trading` on this endpoint, and item 65 is a fresh demonstration that the
        documentation and the wire can disagree -- so absence is not read as disabled."""
        sess = Recorded(account_fields=LIMITED, config={"no_shorting": False})
        got = LC.account_settlement_report(broker(sess))
        self.assertEqual(got["fractional_trading"], "NOT REPORTED by the API")
        self.assertIn("$1 buy placed by hand", got["fractional_trading_note"])

    def test_an_unreadable_configuration_does_not_lose_the_account(self):
        sess = Recorded(account_fields=LIMITED, config=None)   # HTTP 404
        got = LC.account_settlement_report(broker(sess))
        self.assertTrue(got["ok"])
        self.assertFalse(got["configurations_read"])
        self.assertEqual(got["fractional_trading"], "NOT REPORTED by the API")

    def test_it_reports_the_figure_a_buy_WOULD_be_sized_from(self):
        sess = Recorded(account_fields=LEVERED, config={"fractional_trading": True})
        got = LC.account_settlement_report(broker(sess))
        self.assertEqual(got["spendable_without_borrowing"]["amount"], 250.0)
        self.assertEqual(got["account"]["multiplier"], 4.0)

    def test_it_states_what_a_limited_margin_IRA_is_EXPECTED_to_report(self):
        sess = Recorded(account_fields=LIMITED, config={"fractional_trading": True})
        got = LC.account_settlement_report(broker(sess))
        self.assertIn("limited margin", got["limited_margin_expected"])
        self.assertIn("UNSETTLED", got["limited_margin_expected"])

    def test_no_client_is_unmeasured(self):
        self.assertFalse(LC.account_settlement_report(None)["ok"])


class TheCensusPlacesNothing(unittest.TestCase):
    """**THE PROPERTY THAT MATTERS MOST ABOUT PART 2: it is read-only.**

    Asserted on the WIRE rather than on intent -- every request the two report functions make
    is counted, and a POST to `/v2/orders` fails the test.
    """

    def test_not_one_POST_reaches_the_orders_endpoint(self):
        sess = Recorded(account_fields=LEVERED, assets=MASTER,
                        config={"fractional_trading": True})
        b = broker(sess)
        LC.fractional_report(b, ["AAPL", "MSFT"])
        LC.account_settlement_report(b)
        posts = [(m, u) for m, u in sess.calls if m == "POST"]
        self.assertEqual(posts, [], posts)
        self.assertEqual(sess.placed, [])

    def test_every_method_the_reports_use_is_a_GET(self):
        sess = Recorded(account_fields=LEVERED, assets=MASTER,
                        config={"fractional_trading": True})
        b = broker(sess)
        LC.fractional_report(b, ["AAPL"])
        LC.account_settlement_report(b)
        self.assertTrue(sess.calls)
        self.assertTrue(all(m == "GET" for m, _ in sess.calls), sess.calls)

    def test_the_live_client_reads_are_GET_in_its_SOURCE_too(self):
        """`_LiveClient` is the one that can reach a real account, so its three new reads are
        pinned structurally as well -- a behavioural test here would need live keys."""
        tree = ast.parse(io.open(LS.__file__, encoding="utf-8").read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name in ("assets", "configurations", "account_report")):
                verbs = [a.value for sub in ast.walk(node)
                         if isinstance(sub, ast.Call)
                         and isinstance(sub.func, ast.Attribute)
                         and sub.func.attr == "_request"
                         for a in sub.args[:1] if isinstance(a, ast.Constant)]
                self.assertTrue(verbs, "%s makes no request at all" % node.name)
                self.assertEqual(set(verbs), {"GET"},
                                 "%s is not read-only: %r" % (node.name, verbs))


class TheDoorIsOptInAndStillRefusesWithoutAToken(unittest.TestCase):
    def test_the_check_is_a_FLAG_and_the_door_BUILDS_NOTHING(self):
        """**TWO INVARIANTS PUSHED BOTH READS OUT OF THIS DOOR AND BOTH ARE WORTH MORE THAN THE
        CONVENIENCE.** A live client is constructed in exactly one gated place (item 58), and
        this door constructs no client of any kind (`test_item58b_doors.py`, asserted on its
        source). My first cut built a `_LiveClient` here for the IRA read and an
        `AlpacaPaperBroker` for the asset master; each test caught its own half. Both reads now
        happen inside the cycle, which legitimately holds a client, and the door reads records.
        """
        src = io.open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                      encoding="utf-8").read()
        block = src[src.index("def admin_live_slots"):]
        block = block[:block.index("\n    @app.route", 10)]
        self.assertIn('request.args.get("check")', block)
        self.assertIn("fractional", block)
        self.assertNotIn("_LiveClient(", block)
        self.assertNotIn("AlpacaPaperBroker(", block)
        self.assertIn("read_state", block)

    def test_a_slot_with_no_report_is_UNMEASURED_and_not_a_negative_answer(self):
        """**ASSERTED ON THE RENDERED PAYLOAD, NOT ON THE SOURCE.** The first cut grepped the
        source for a phrase that is now split across two lines by the formatter, so it could
        not be found while the value it describes was exactly right. A reflow is not a
        behaviour change and a test that cannot tell them apart is measuring the wrong thing.
        """
        from valuation.edge import live_cycle as LC2
        rep = LC2.fractional_report(None, ["AAPL"])
        self.assertFalse(rep["ok"])
        self.assertIn("UNMEASURED", rep["reason"])
        self.assertNotIn("whole_share_only", rep)
        acct = LC2.account_settlement_report(None)
        self.assertFalse(acct["ok"])
        self.assertFalse(acct["constructs_an_order"])


# ----------------------------------------------------------------------------------------- #
# PART 0 -- THE AUDITOR'S THIRD BLOCKER, REPRODUCED AND CLOSED
# ----------------------------------------------------------------------------------------- #
class Accumulating:
    """Alpaca, replayed, where **every order placed stays RESTING on the next read.**

    That is what a `day` limit at the mid does inside a session, and it is the state item 64's
    five-cron schedule now produces two or three times a session. Every existing fixture either
    filled the order or forgot it, which is why 349 tests passed through the stacking.
    """

    def __init__(self, fill=0.0, account=None):
        self.fill, self.account_fields = fill, dict(account or LIMITED)
        self.placed, self.resting, self.cancelled, self.calls = [], [], [], []

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account"):
            return T63.Reply(dict(self.account_fields))
        if url.endswith("/v2/positions"):
            agg = {}
            for o in self.resting:
                q = float(o["filled_qty"])
                if q:
                    agg[o["symbol"]] = agg.get(o["symbol"], 0.0) + q
            return T63.Reply([{"symbol": k, "qty": str(v), "avg_entry_price": "100",
                               "side": "long"} for k, v in agg.items() if v > 0])
        if "quotes/latest" in url:
            return T63.Reply({"quotes": {"AAPL": {"bp": 99.0, "ap": 101.0, "t": "x"},
                                         "MSFT": {"bp": 199.0, "ap": 201.0, "t": "x"}}})
        if url.endswith("/v2/orders") and method == "GET":
            return T63.Reply(list(self.resting))
        if url.endswith("/v2/orders") and method == "POST":
            body = json.loads(data or "{}")
            self.placed.append(body)
            qty = float(body.get("qty") or 0)
            self.resting.append({
                "id": "srv-%d" % len(self.placed),
                "client_order_id": body.get("client_order_id") or "",
                "symbol": body.get("symbol"), "side": body.get("side"),
                "qty": str(qty), "filled_qty": str(round(qty * self.fill, 9)),
                "limit_price": str(body.get("limit_price")),
                "filled_avg_price": (str(body.get("limit_price")) if self.fill else None),
                # STILL WORKING. A partial fill is `partially_filled`, not `filled`.
                "status": "partially_filled" if self.fill else "new",
                "submitted_at": "2026-10-22T14:4%d:00Z" % min(9, len(self.placed)),
            })
            return T63.Reply(dict(body, id="srv-%d" % len(self.placed), status="new"))
        if "/v2/orders/" in url and method == "DELETE":
            oid = url.rsplit("/", 1)[-1]
            self.cancelled.append(oid)
            self.resting = [o for o in self.resting if o["id"] != oid]
            return T63.Reply({}, status=204)
        return T63.Reply({}, status=404)


OPEN_NOW = _dt.datetime(2026, 10, 22, 13, 36)


class ARemainderNeverStacksOnARestingOrder(unittest.TestCase):
    """**THE AUDITOR'S THIRD BLOCKER, through `run_cycle` with the real `AlpacaPaperBroker`.**

    Reproduced by the auditor as five cycles, five full orders, 500 shares live against a
    100-share target -- and every one of 349 tests passed through it, because
    `test_a_resting_SAME_side_order_is_NOT_cancelled` reached this exact state and asked only
    whether anything had been cancelled.

    **IT TAKES SEVERAL CYCLES INSIDE ONE SESSION, which is what the pending schedule produces.**
    Item 64 measured GitHub's scheduler 3.45-7.48 hours late and added four backup crons; by
    that workflow's own delay table three of the five land inside the orders window, so two or
    three in-window cycles is the DESIGNED behaviour and `cancel-in-progress: false` makes them
    queue and run in sequence, each seeing the last one's resting order.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _cycles(self, sess, n=5):
        outs = []
        for _ in range(n):
            outs.append(LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                                     book=T63.BOOK, paper_client=broker(sess),
                                     notify_send=(lambda cfg, b: True)))
        return outs

    def test_FIVE_IN_SESSION_CYCLES_DO_NOT_SEND_FIVE_FULL_ORDERS(self):
        sess = Accumulating()
        outs = self._cycles(sess)
        self.assertTrue(outs[0]["paper"]["sent"], "the first cycle sent nothing")
        by_sym = {}
        for o in sess.placed:
            if o.get("side") == "buy":
                by_sym[o["symbol"]] = by_sym.get(o["symbol"], 0.0) + float(o["qty"])
        # The book is AAPL 60% and MSFT 40% of 1000 at marks of 100 and 200: 6 and 2 shares.
        self.assertAlmostEqual(by_sym.get("AAPL", 0.0), 6.0, places=6,
                               msg="AAPL stacked: %r" % by_sym)
        self.assertAlmostEqual(by_sym.get("MSFT", 0.0), 2.0, places=6,
                               msg="MSFT stacked: %r" % by_sym)

    def test_only_the_FIRST_cycle_transmits_while_the_orders_rest(self):
        sess = Accumulating()
        self._cycles(sess)
        self.assertEqual(len(sess.placed), 2,
                         "cycles after the first re-sent: %r"
                         % [(o["symbol"], o["qty"]) for o in sess.placed])

    def test_A_PARTIAL_FILL_LEAVES_THE_REMAINDER_WORKING_and_is_not_re_sent(self):
        """A partially-filled order is STILL WORKING, so the unfilled part is the remainder --
        re-planning it is the stacking in a subtler costume."""
        sess = Accumulating(fill=0.5)
        self._cycles(sess, n=3)
        self.assertEqual(len(sess.placed), 2,
                         "a partially-filled order's remainder was re-sent: %r"
                         % [(o["symbol"], o["qty"]) for o in sess.placed])

    def test_the_resting_quantity_is_REPORTED_on_the_plan(self):
        """So a reader can check the arithmetic rather than trust it."""
        sess = Accumulating()
        outs = self._cycles(sess, n=2)
        self.assertEqual(outs[1]["paper"]["orders"], [],
                         "the second cycle planned an order it did not need")
        rec = outs[1]["paper"]["reconcile"]
        self.assertTrue(rec["resting"], "the resting orders were not recorded at all")
        for r in rec["resting"]:
            self.assertIsNotNone(r.get("qty_open"),
                                 "a resting order carries no open quantity, so it cannot be "
                                 "subtracted: %r" % r)


class TheSettlementWaitDoesNotDOUBLE_SEND(unittest.TestCase):
    """**THE ADDENDUM'S POINT 4: the two mechanisms must not re-plan a buy on top of itself.**

    They compose correctly and the reason is worth stating, because it is the opposite of what
    it looks like:

      * a buy that was **SENT** and rests is subtracted -- it is in `reconcile`'s resting list;
      * a buy that was **DEFERRED** for settlement was never transmitted, so it is neither
        resting at the broker nor in the recorded intent, and re-planning it is CORRECT rather
        than a double-send.

    The hazard is the composition, not either half, so both are driven here.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _cycle(self, sess, day):
        real = LC._stamp
        try:
            LC._stamp = (lambda d=day: "%sT14:40:00Z" % d)
            return LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                                book=T63.BOOK, paper_client=broker(sess),
                                notify_send=(lambda cfg, b: True))
        finally:
            LC._stamp = real

    def test_a_DEFERRED_buy_is_not_resting_and_IS_re_planned(self):
        """It was never sent, so nothing is stacked by sending it later -- which is the whole
        point of a settlement wait."""
        broke = dict(LIMITED, cash="0", buying_power="0",
                     non_marginable_buying_power="0")
        sess = Accumulating(account=broke)
        p1 = self._cycle(sess, "2026-10-22")["paper"]
        self.assertEqual(sess.placed, [], "something was sent on a zero budget")
        self.assertTrue(p1["deferred"])
        self.assertEqual(p1["reconcile"]["resting"], [])

        sess.account_fields = dict(LIMITED)
        p2 = self._cycle(sess, "2026-10-23")["paper"]
        self.assertEqual(len(sess.placed), 2, sess.placed)
        self.assertEqual(p2["deferred"], [])

    def test_ACROSS_A_DAY_BOUNDARY_a_resting_buy_is_still_not_re_sent(self):
        """The addendum asks specifically about the day boundary. A `day` order that is still
        reported as working is still working, whatever the date is."""
        sess = Accumulating()
        self._cycle(sess, "2026-10-22")
        n = len(sess.placed)
        self._cycle(sess, "2026-10-23")
        self._cycle(sess, "2026-10-26")
        self.assertEqual(len(sess.placed), n,
                         "a resting buy was re-sent on a later day: %r"
                         % [(o["symbol"], o["qty"]) for o in sess.placed])


class TheOrderReadIsPagedAndStillFailsSafe(unittest.TestCase):
    """`ORDERS_PAGE_LIMIT` with no cursor refused a full page -- correct, and item 64's measured
    239 orders for ONE event makes that refusal arrive in about two events."""

    def _fetch(self, pages):
        """A fetch that serves `pages` in order, then an empty page."""
        state = {"i": 0}

        def fetch(params):
            i = state["i"]
            state["i"] += 1
            return {"ok": True, "data": (pages[i] if i < len(pages) else [])}
        return fetch

    def _orders(self, n, start=0, stamp=None):
        return [{"id": "o%d" % (start + k), "client_order_id": "c%d" % (start + k),
                 "symbol": "AAPL", "side": "buy", "qty": "1", "filled_qty": "0",
                 "status": "new",
                 "submitted_at": (stamp or "2026-10-22T14:%02d:%02dZ"
                                  % ((start + k) // 60, (start + k) % 60))}
                for k in range(n)]

    def test_a_SHORT_page_is_complete(self):
        got = SETTLE.paged_orders(self._fetch([self._orders(3)]), page_limit=5)
        self.assertTrue(got["ok"])
        self.assertFalse(got["truncated"])
        self.assertEqual(len(got["data"]), 3)

    def test_TWO_PAGES_are_walked_and_deduped(self):
        p1, p2 = self._orders(5), self._orders(3, start=5)
        got = SETTLE.paged_orders(self._fetch([p1, p2]), page_limit=5)
        self.assertTrue(got["ok"])
        self.assertFalse(got["truncated"])
        self.assertEqual(len(got["data"]), 8)
        self.assertEqual(got["pages"], 2)

    def test_AN_OVERLAP_IS_HARMLESS_because_after_is_exclusive(self):
        p1 = self._orders(5)
        p2 = p1[-1:] + self._orders(2, start=5)      # the boundary order repeats
        got = SETTLE.paged_orders(self._fetch([p1, p2]), page_limit=5)
        self.assertEqual(len({o["id"] for o in got["data"]}), 7)
        self.assertEqual(len(got["data"]), 7, "an overlapping order was counted twice")

    def test_A_SHARED_BOUNDARY_TIMESTAMP_REFUSES_rather_than_skipping(self):
        """**THE CASE THAT KEEPS THE ORIGINAL FAIL-SAFE.** `after` is exclusive on the
        timestamp, so if the page's last timestamp belongs to more than one order, asking for
        everything after it SKIPS the ones not yet read -- and a skipped fill UNDER-counts a
        holding, which makes the planner buy it again. That is the exact direction the refusal
        existed to avoid, so this comes back truncated."""
        p1 = self._orders(5, stamp="2026-10-22T14:40:00Z")
        got = SETTLE.paged_orders(self._fetch([p1, self._orders(1, start=5)]), page_limit=5)
        self.assertTrue(got["truncated"])
        self.assertIn("share this page's last submission timestamp", got["reason"])

    def test_NO_TIMESTAMP_AT_ALL_refuses(self):
        p1 = [{"id": "x%d" % k, "symbol": "A", "qty": "1", "filled_qty": "0",
               "status": "new"} for k in range(5)]
        got = SETTLE.paged_orders(self._fetch([p1]), page_limit=5)
        self.assertTrue(got["truncated"])
        self.assertIn("no submission timestamp", got["reason"])

    def test_THE_PAGE_CAP_REFUSES_rather_than_looping(self):
        pages = [self._orders(2, start=2 * k) for k in range(50)]
        got = SETTLE.paged_orders(self._fetch(pages), page_limit=2, max_pages=3)
        self.assertTrue(got["truncated"])
        self.assertIn("did not end within 3 pages", got["reason"])

    def test_a_FAILED_page_is_a_failure_and_not_a_partial(self):
        def fetch(params):
            return {"ok": False, "status": 500}
        got = SETTLE.paged_orders(fetch, page_limit=5)
        self.assertFalse(got["ok"])
        self.assertEqual(got["data"], [])

    def test_RECONCILE_HONOURS_truncated(self):
        """A reader whose refusal the caller does not read is the defect item 65 found
        underneath the auditor's own fix -- and `reconcile` read only `ok` at first."""
        class Trunc:
            # `orders` as well, because `reconcile` returns `not_attempted` for a client that
            # cannot list orders at all -- a stub missing it tests the early return instead of
            # the thing under test.
            def orders(self, limit=100, **k):
                return []

            def orders_result(self, limit=100):
                return {"ok": True, "data": [], "truncated": True, "reason": "cannot complete"}

            def positions_result(self):
                return {"ok": True, "data": []}
        rec = LC.reconcile(Trunc(), {"slot": "paper"})
        self.assertEqual(rec["order_read"], "truncated")
        self.assertIn("cannot complete", rec["reason"])

    def test_BOTH_CLIENTS_share_ONE_pager(self):
        """`B7`. Two implementations of "every order" is how the two clients came to disagree
        four times already -- and it lives in NEITHER client's module, because item 58 forbids
        a paper-side module importing the live path."""
        for mod in ("valuation/edge/alpaca_broker.py", "valuation/edge/live_slots.py"):
            src = io.open(os.path.join(REPO, mod), encoding="utf-8").read()
            self.assertIn("from .settlement import paged_orders", src, mod)
        self.assertFalse(hasattr(LS, "paged_orders"),
                         "the pager is back in the live module")


class AFreshRecordMeetingANonEmptyAccountRefusesOnce(unittest.TestCase):
    """The auditor's recommendation 2 -- the last corner of the empty-scope family."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_it_refuses(self):
        sess = Accumulating()
        sess.resting = [{"id": "x", "client_order_id": "someone-elses", "symbol": "AAPL",
                         "side": "buy", "qty": "6", "filled_qty": "6", "status": "filled",
                         "limit_price": "100", "filled_avg_price": "100",
                         "submitted_at": "2026-10-20T14:40:00Z"}]
        out = LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                           book=T63.BOOK, paper_client=broker(sess),
                           notify_send=(lambda cfg, b: True))
        p = out["paper"]
        self.assertEqual(sess.placed, [], "a full buy-in went out on top of a held account")
        self.assertTrue(p["record_is_fresh"])
        self.assertIn("brand new", p["reason"])

    def test_it_can_fire_at_most_ONCE_in_a_slots_life(self):
        """**WHICH IS THE ONLY REASON IT IS SAFE TO ADD** -- a guard that fires on the steady
        state is a guard that gets switched off (`MA21`). Any one of three markers present
        means the slot has acted before, and it never asks again."""
        for marker in ({"holdings": {"AAPL": 1.0}}, {"processed": ["x"]},
                       {"account_id": "acct-1"}, {"intent": {"event": "x", "orders": []}}):
            got = LS.preflight(book=T63.BOOK, equity=1000.0, marks=T63.MARKS,
                               slot_record={}, pct=100.0,
                               broker_positions=[{"ticker": "ZZZZ", "qty": 5.0}],
                               slot_symbols=[], record_is_fresh=False)
            self.assertTrue(got["ok"], "%r: %s" % (marker, got["reason"]))

    def test_IT_REFUSES_ONCE_AND_THE_NEXT_CYCLE_PROCEEDS(self):
        """**MY FIRST CUT REFUSED FOR EVER, WHICH IS AN OUTAGE RATHER THAN A HARDENING.**

        The auditor's wording is *"refusing ONCE there would cost one cycle"*. Refusing in
        `preflight` and writing nothing left the record brand new, so the next cycle refused
        identically -- permanently bricking a slot whose state file was lost, which is a
        demonstrated state here because `data/` lives on Render's disk. **And it blocked the
        route that HEALS a lost record**: `reconcile` rebuilding holdings from this slot's own
        fills, after which the event closes as "targets already met". Item 63's and item 65's
        end-to-end tests both went red, which is how it was found.

        The refusal now records that it ASKED -- not that the positions are the slot's.
        """
        sess = Accumulating()
        sess.resting = [{"id": "x", "client_order_id":
                         LC.client_order_id(LC.PAPER_SLOT, "rebalance:2026-07-30", "AAPL"),
                         "symbol": "AAPL", "side": "buy", "qty": "6", "filled_qty": "6",
                         "status": "filled", "limit_price": "100", "filled_avg_price": "100",
                         "submitted_at": "2026-07-30T14:40:00Z"}]

        def cycle():
            return LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                                book=T63.BOOK, paper_client=broker(sess),
                                notify_send=(lambda cfg, b: True))["paper"]

        first = cycle()
        self.assertIn("brand new", first["reason"])
        self.assertTrue(first["fresh_record_refusal_recorded"])
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertTrue(st.get("fresh_record_refusal"))
        self.assertIn("records that the question",
                      st["fresh_record_refusal"]["what_it_means"])

        second = cycle()
        self.assertNotIn("brand new", second.get("reason") or "",
                         "the refusal repeated, which bricks a slot with a lost record")
        self.assertFalse(second["record_is_fresh"])

    def test_the_marker_does_NOT_claim_the_positions(self):
        """The ambiguity is RECORDED, not resolved. Guessing "they are mine" would adopt Don's
        own holdings into the slot's record, which is the thing the scope rule exists to stop."""
        sess = Accumulating()
        sess.resting = [{"id": "x", "client_order_id": "someone-elses", "symbol": "ZZZZ",
                         "side": "buy", "qty": "9", "filled_qty": "9", "status": "filled",
                         "limit_price": "10", "filled_avg_price": "10",
                         "submitted_at": "2026-07-30T14:40:00Z"}]
        LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=T63.BOOK,
                     paper_client=broker(sess), notify_send=(lambda cfg, b: True))
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertNotIn("ZZZZ", st.get("holdings") or {},
                         "the refusal adopted a position the slot never bought")

    def test_a_fresh_record_against_an_EMPTY_account_is_fine(self):
        """THE POSITIVE CONTROL: the normal first cycle must not be refused."""
        got = LS.preflight(book=T63.BOOK, equity=1000.0, marks=T63.MARKS,
                           slot_record={}, pct=100.0, broker_positions=[],
                           slot_symbols=[], record_is_fresh=True)
        self.assertTrue(got["ok"], got["reason"])


class AnExitedNameIsSold(unittest.TestCase):
    """**NOTHING SOLD AN EXITED NAME BEFORE ITEM 67, and it has never fired.** `run_slot`
    filtered the book to `status == "held"` and `targets` drops a zero weight, so a name the
    book had dropped reached the planner in neither shape -- it was held for ever and the event
    closed as "targets met" while the slot still held it. The live path has run exactly one
    event; the first book change in its life is the 2026-10-22 rebalance."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _state(self, holdings):
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"slot": LC.PAPER_SLOT, "holdings": dict(holdings),
                       "processed": [], "account_id": "acct-paper-1"}, fh)

    def _run(self, sess, book):
        return LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=book,
                           client=broker(sess), equity=1000.0, account=LIMITED,
                           marks={"AAPL": {"mid": 100.0}, "MSFT": {"mid": 200.0},
                                  "GONE": {"mid": 50.0}},
                           root=self.root, send=True)

    def test_a_name_marked_EXITED_in_the_book_is_sold(self):
        book = {"ok": True, "formed_on": "2026-10-22", "reason": "",
                "positions": [{"ticker": "AAPL", "status": "held", "weight": 1.0},
                              {"ticker": "GONE", "status": "exited", "weight": 0.0}]}
        self._state({"GONE": 4.0})
        sess = Accumulating()
        sess.resting = [{"id": "g", "client_order_id":
                         LC.client_order_id(LC.PAPER_SLOT, "rebalance:2026-07-30", "GONE"),
                         "symbol": "GONE", "side": "buy", "qty": "4", "filled_qty": "4",
                         "status": "filled", "limit_price": "50", "filled_avg_price": "50",
                         "submitted_at": "2026-07-30T14:40:00Z"}]
        got = self._run(sess, book)
        self.assertIn("GONE", got["exits_planned"])
        sells = [(o["symbol"], float(o["qty"])) for o in sess.placed
                 if o.get("side") == "sell"]
        self.assertEqual(sells, [("GONE", 4.0)], sess.placed)

    def test_a_name_ABSENT_from_the_book_entirely_is_also_sold(self):
        """**THE SECOND SHAPE, and the one a rebalance produces.** A mid-event exit stays in
        `positions` as `status: exited`; a name dropped AT a rebalance belongs to a different
        event's book and is absent altogether."""
        book = {"ok": True, "formed_on": "2026-10-22", "reason": "",
                "positions": [{"ticker": "AAPL", "status": "held", "weight": 1.0}]}
        self._state({"GONE": 4.0})
        sess = Accumulating()
        sess.resting = [{"id": "g", "client_order_id":
                         LC.client_order_id(LC.PAPER_SLOT, "rebalance:2026-07-30", "GONE"),
                         "symbol": "GONE", "side": "buy", "qty": "4", "filled_qty": "4",
                         "status": "filled", "limit_price": "50", "filled_avg_price": "50",
                         "submitted_at": "2026-07-30T14:40:00Z"}]
        got = self._run(sess, book)
        self.assertIn("GONE", got["exits_planned"])
        self.assertTrue([o for o in sess.placed
                         if o.get("symbol") == "GONE" and o.get("side") == "sell"],
                        sess.placed)

    def test_THE_PLANNER_ITSELF_still_refuses_a_name_it_was_not_given(self):
        """**AND THE EXIT LIVES IN `run_slot` RATHER THAN IN `order_plan` BECAUSE OF THIS.**
        Item 58 pins that a name absent from the planner's targets is not in its plan at all,
        *"enforced by what the planner is GIVEN rather than by a filter it could forget"*. My
        first fix iterated the holdings inside `order_plan` and that test caught it by planning
        a sale of `DONS_OWN` -- a defensive contract catching a change that would have sold a
        holding the slot never bought."""
        plan = LS.order_plan({"A": 100.0}, {"A": 1.0, "DONS_OWN": 50.0},
                             {"A": {"mid": 100.0}, "DONS_OWN": {"mid": 10.0}})
        self.assertEqual([o["ticker"] for o in plan["orders"]], [])


class TheContractSaysWhatTheCodeDoes(unittest.TestCase):
    """**SECTION 8b IS A SIGNED SECTION AND IT CHANGED A BEHAVIOUR §8a SPECIFIED.** §8a's open
    question 2 reads *"a buy rejected for insufficient buying power is a broker error, which
    means no orders for that slot that cycle plus an alert."* Item 67 makes it a settlement
    wait, so the contract is amended openly and the superseded text left in place -- and pinned
    here, because a contract that describes behaviour the code no longer has is worse than one
    that describes none: this project has twice found a figure rotting inside a signed document.
    """

    @classmethod
    def setUpClass(cls):
        cls.txt = io.open(os.path.join(REPO, "PAPER_TRACK_CONTRACT.md"),
                          encoding="utf-8").read()
        cls.b = cls.txt[cls.txt.index("## §8b AMENDMENT"):]

    def test_the_superseded_text_is_STILL_THERE(self):
        """Nothing is edited away. §5a's convention: a dated amendment, never a silent edit."""
        # **A FRAGMENT SHORT ENOUGH TO SURVIVE A REFLOW.** The sentence is wrapped across
        # two source lines in §8a, so the whole phrase appears nowhere contiguously -- the
        # third time today a grep has failed on a line break rather than on a change.
        self.assertIn("a buy rejected for insufficient buying power is a", self.txt)
        self.assertIn("broker error, which means no orders for that slot", self.txt)
        self.assertIn("§8a AMENDMENT", self.txt)

    def test_it_names_the_field_the_code_actually_sizes_from(self):
        self.assertIn(SETTLE.NO_BORROW_FIELD, self.b)
        for levered in SETTLE.LEVERED_FIELDS[:1]:
            self.assertIn(levered, self.b)

    def test_it_states_the_T_plus_1_rule_the_code_implements(self):
        self.assertIn("T+1", self.b)
        self.assertEqual(SETTLE.WAIT_ALERT_AFTER_TRADING_DAYS, 2)

    def test_it_states_the_ceiling_in_TRADING_DAYS(self):
        self.assertIn("five trading days", self.b)
        self.assertEqual(SETTLE.MAX_EVENT_TRADING_DAYS, 5)

    def test_it_leaves_the_non_fractionable_remedy_to_DON(self):
        for word in ("leaving it", "rounding", "skipping"):
            self.assertIn(word, self.b)
        self.assertIn("own register", self.b)

    def test_it_says_the_auditor_reviews_item_67_too(self):
        """The brief requires this in the summary; it belongs in the contract as well, because
        the contract is what records that a review is still required."""
        self.assertIn("it now covers item 67", self.b)

    def test_it_is_NOT_a_vintage_event_and_says_so(self):
        self.assertIn("not a vintage event", self.b.lower())


class AnExitedNameIsPRICEDOrItCannotBeSold(unittest.TestCase):
    """**MY OWN EXIT FIX WOULD HAVE BEEN SKIPPED EVERY CYCLE, AND MY OWN TEST PASSED.**

    `tickers` was the book's HELD names, and `marks` is `_marks_for(pc, tickers)`. An exited name
    is by definition not held, so no quote was requested for it -- and `order_plan` skips a name
    with no usable mark, correctly, because the alternative is trading at any price. So every
    exit target would have been skipped silently.

    **`AnExitedNameIsSold` passed because it handed `marks` a price for `GONE` BY HAND** -- the
    auditor's question-7 lesson from the author's side: a fixture supplying what the production
    path derives proves the arithmetic and not the path. So this one asserts the QUOTE WAS
    REQUESTED, through `run_cycle`, with nothing supplied.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_run_cycle_asks_for_a_quote_on_a_name_only_a_SLOT_holds(self):
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"slot": LC.PAPER_SLOT, "holdings": {"GONE": 4.0},
                       "processed": [], "account_id": "acct-paper-1"}, fh)

        asked = []

        class Quoting(Accumulating):
            def request(self, method, url, headers=None, params=None, data=None,
                        timeout=None):
                if "quotes/latest" in url:
                    asked.append(sorted(str((params or {}).get("symbols") or "").split(",")))
                return super().request(method, url, headers=headers, params=params,
                                       data=data, timeout=timeout)

        sess = Quoting()
        LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=T63.BOOK,
                     paper_client=broker(sess), notify_send=(lambda cfg, b: True))
        self.assertTrue(asked, "no quote was requested at all")
        self.assertIn("GONE", asked[0],
                      "a name the slot HOLDS was never priced, so it could never be sold: %r"
                      % asked)

    def test_the_priced_set_is_REPORTED_with_the_extra_names_named(self):
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"slot": LC.PAPER_SLOT, "holdings": {"GONE": 4.0},
                       "processed": [], "account_id": "acct-paper-1"}, fh)
        out = LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                           book=T63.BOOK, paper_client=broker(Accumulating()),
                           notify_send=(lambda cfg, b: True))
        rep = out["priced_names"]
        self.assertEqual(rep["held_by_a_slot_and_not_in_the_book"], ["GONE"])
        self.assertGreater(rep["n"], rep["book_held"])

    def test_it_prices_ONLY_what_a_slot_itself_bought(self):
        """A quote request trades nothing -- but the names come from each slot's OWN record,
        which `reconcile` builds from `valquo-<slot>-` prefixed orders and nothing else, so this
        can never reach for a quote on one of Don's other holdings."""
        out = LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                           book=T63.BOOK, paper_client=broker(Accumulating()),
                           notify_send=(lambda cfg, b: True))
        self.assertEqual(out["priced_names"]["held_by_a_slot_and_not_in_the_book"], [],
                         "a fresh record priced a name no slot bought")


if __name__ == "__main__":
    unittest.main(verbosity=2)
