# -*- coding: utf-8 -*-
"""ITEM 65 — the auditor's last blocker, the wash-trade rejection, and a readable cycle.

**THE BLOCKER, IN THE AUDITOR'S OWN WORDS:** a duplicate full buy-in is reachable when the state
record is lost, `/v2/orders` is unreadable and `/v2/positions` is readable. `slot_symbols` is
DERIVED from reconcile's symbols, the recorded holdings and the recorded intent, and all three
are empty in exactly that state -- so `preflight`'s reverse check runs with an empty scope, skips
every broker position, and a full buy-in transmits on top of a book the account already holds.

**ALL 236 EXISTING TESTS PASS THROUGH IT, AND THE REASON IS THE POINT OF THIS FILE.**
`test_an_EMPTY_record_against_a_holding_broker_REFUSES` passes `slot_symbols=["AAPL"]` BY HAND, so
it proves `preflight` refuses *given* a scope; `test_END_TO_END_the_second_full_buy_in_does_not_
transmit` supplies readable orders, so `reconcile` succeeds and it refuses by a different path.
**Neither exercises a failed `reconcile`, which is the only state in which the scope is empty.**
That is the original blocker's shape repeated: the unit test supplies by hand the thing the
production path derives. So every test here drives `run_cycle` end to end with the REAL client
class and recorded HTTP replies, and passes no `slot_symbols` anywhere.
"""
from __future__ import annotations

import datetime as dt
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

from valuation.data import alpaca_data as AD       # noqa: E402
from valuation.data import alpaca_seam as S        # noqa: E402
from valuation.edge import alpaca_broker as AB      # noqa: E402
from valuation.edge import live_cycle as LC         # noqa: E402

BOOK = {"ok": True, "formed_on": "2026-10-22", "reason": "",
        "positions": [{"ticker": "AAPL", "status": "held", "weight": 0.6},
                      {"ticker": "MSFT", "status": "held", "weight": 0.4}]}

#: The account already holds the whole book, which is what makes a second buy-in a DUPLICATE.
HOLDS_THE_BOOK = [
    {"symbol": "AAPL", "qty": "6", "avg_entry_price": "100", "market_value": "600",
     "side": "long"},
    {"symbol": "MSFT", "qty": "2", "avg_entry_price": "200", "market_value": "400",
     "side": "long"},
]

ORDERS_THAT_BOUGHT_IT = [
    {"client_order_id": "valquo-paper-rebalance:2026-10-22-AAPL-a1", "symbol": "AAPL",
     "filled_qty": "6", "side": "buy", "status": "filled", "limit_price": "100",
     "filled_avg_price": "100"},
    {"client_order_id": "valquo-paper-rebalance:2026-10-22-MSFT-a1", "symbol": "MSFT",
     "filled_qty": "2", "side": "buy", "status": "filled", "limit_price": "200",
     "filled_avg_price": "200"},
]


#: THE BROKER'S ACCOUNT REPLY, consistent with the equity these fixtures already pass:
#: `multiplier` 1 and a no-borrow figure equal to the cash, which is what Alpaca documents a
#: limited-margin account as reporting. **Deliberately NOT generous** -- an account with more
#: spendable than the book costs would never exercise item 67's deferral at all, and a budget
#: that is never binding is a budget that is never tested.
ACCOUNT = {"cash": "1000.00", "buying_power": "1000.00",
           "non_marginable_buying_power": "1000.00", "multiplier": "1"}


class Reply:
    def __init__(self, payload, status=200):
        self.status_code, self._p, self.headers, self.text = status, payload, {}, ""

    def json(self):
        return self._p


class Alpaca:
    """Alpaca's HTTP shapes, replayed, with each endpoint independently breakable.

    `orders_status=500` is the auditor's leg: one endpoint 5xx-ing or rate-limiting while
    another succeeds is ordinary, and `data/` living on Render's disk makes a lost state file a
    demonstrated state in this project rather than a hypothetical.
    """

    def __init__(self, positions=None, orders=None, orders_status=200,
                 positions_status=200, account_id="acct-paper-1", reject_orders=None):
        self.positions, self.orders = list(positions or []), list(orders or [])
        self.orders_status, self.positions_status = orders_status, positions_status
        self.account_id, self.reject_orders = account_id, reject_orders
        self.placed, self.cancelled, self.calls = [], [], []

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account"):
            return Reply({"id": self.account_id, "account_number": "PA1", "equity": "1000",
                          "cash": "1000", "buying_power": "1000", "status": "ACTIVE",
                          "multiplier": "1"})
        if url.endswith("/v2/positions"):
            if self.positions_status >= 400:
                return Reply({"message": "positions are down"}, status=self.positions_status)
            return Reply(self.positions)
        if "quotes/latest" in url:
            return Reply({"quotes": {"AAPL": {"bp": 99.0, "ap": 101.0, "t": "x"},
                                     "MSFT": {"bp": 199.0, "ap": 201.0, "t": "x"}}})
        if url.endswith("/v2/orders") and method == "GET":
            if self.orders_status >= 400:
                return Reply({"message": "orders are down"}, status=self.orders_status)
            return Reply(self.orders)
        if url.endswith("/v2/orders") and method == "POST":
            body = json.loads(data or "{}")
            self.placed.append(body)
            if self.reject_orders:
                return Reply({"message": self.reject_orders}, status=403)
            return Reply(dict(body, id="srv-%d" % len(self.placed), status="new",
                              filled_qty="0"))
        if "/v2/orders/" in url and method == "DELETE":
            self.cancelled.append(url.rsplit("/", 1)[-1])
            return Reply({}, status=204)
        return Reply({}, status=404)


def paper(sess):
    return AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24, session=sess)


OPEN_NOW = __import__("datetime").datetime(2026, 10, 16, 13, 36)


class _Cycle(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def cycle(self, sess):
        """A real `run_cycle`, paper mode, with the REAL broker class on a recorded session.

        **NO `slot_symbols` IS PASSED ANYWHERE IN THIS FILE.** That is the whole point: the
        auditor's route runs through the DERIVATION, and supplying the scope by hand is exactly
        how 236 tests missed it.
        """
        out = LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root, book=BOOK,
                           paper_client=paper(sess), notify_send=(lambda cfg, b: True))
        return out, (out.get("paper") or {})


class TheAuditorsLastBlockerIsClosed(_Cycle):
    """**THE TEST THE BRIEF ASKS FOR, and it fails on the old code.**"""

    def test_orders_UNREADABLE_plus_a_lost_record_plus_readable_positions_SENDS_NOTHING(self):
        """The auditor's exact state. `slot_symbols` derives to `[]`, so before item 65 every
        broker position was skipped, preflight and parity passed, and a full buy-in went out."""
        sess = Alpaca(positions=HOLDS_THE_BOOK, orders_status=500)
        self.assertFalse(os.path.exists(LC.state_path(LC.PAPER_SLOT, self.root)),
                         "the fixture must start with NO state file")
        _, p = self.cycle(sess)
        self.assertEqual(sess.placed, [], "A SECOND FULL BUY-IN WAS TRANSMITTED")
        self.assertEqual(p["reconcile"]["order_read"], "failed")
        self.assertIn("order_read_failed", [a["kind"] for a in p["alerts"]])

    def test_the_derived_scope_really_IS_empty_in_that_state(self):
        """Proving the test exercises the route rather than refusing for some other reason --
        otherwise it would pass against the old code too, for the wrong reason."""
        sess = Alpaca(positions=HOLDS_THE_BOOK, orders_status=500)
        _, p = self.cycle(sess)
        self.assertEqual(p["reconcile"]["symbols"], [])
        self.assertEqual(p["reconcile"]["holdings"], {})
        self.assertIsNone(LC.read_state(LC.PAPER_SLOT, self.root).get("intent"))

    def test_it_refuses_BEFORE_preflight_rather_than_relying_on_it(self):
        """The refusal is upstream of the scope, so it holds whatever the scope derives to."""
        sess = Alpaca(positions=HOLDS_THE_BOOK, orders_status=500)
        _, p = self.cycle(sess)
        self.assertIsNone(p.get("preflight"),
                          "preflight ran, so the refusal is still downstream of the scope")

    def test_a_TRUNCATED_page_still_refuses(self):
        """The half item 63 already closed must not have regressed."""
        sess = Alpaca(positions=HOLDS_THE_BOOK,
                      orders=ORDERS_THAT_BOUGHT_IT * (LC.ORDERS_PAGE_LIMIT // 2 + 1))
        _, p = self.cycle(sess)
        self.assertEqual(sess.placed, [])
        self.assertEqual(p["reconcile"]["order_read"], "truncated")
        self.assertIn("reconcile_truncated", [a["kind"] for a in p["alerts"]])

    def test_READABLE_orders_still_refuse_by_the_targets_already_met_path(self):
        """The state the auditor confirmed already worked. It must keep working, or the test
        above would pass because the slot can never trade at all."""
        sess = Alpaca(positions=HOLDS_THE_BOOK, orders=ORDERS_THAT_BOUGHT_IT)
        # **THE FIRST CYCLE REFUSES ON ITEM 67's FRESH-RECORD AMBIGUITY and the second heals.**
        # This fixture has no state file and a non-empty account, which is precisely the state
        # the auditor's recommendation 2 asks to be refused once. Nothing transmits on either,
        # which is what this test is for -- and the second cycle proving the self-healing route
        # still works is what stops the refusal becoming an outage.
        _, first = self.cycle(sess)
        self.assertEqual(sess.placed, [])
        self.assertIn("brand new", first["reason"])

        _, p = self.cycle(sess)
        self.assertEqual(sess.placed, [])
        self.assertEqual(p["reconcile"]["order_read"], "ok")
        self.assertIn("targets are already met", p["reason"])

    def test_A_CLEAN_SLOT_STILL_BUYS_IN(self):
        """**THE POSITIVE CONTROL, and without it every test above passes vacuously.** A fresh
        account with readable endpoints must still place its orders."""
        sess = Alpaca(positions=[], orders=[])
        _, p = self.cycle(sess)
        self.assertEqual(len(sess.placed), 2, p.get("reason"))
        self.assertTrue(p["acted"])

    def test_a_DRY_cycle_with_no_client_still_computes_a_plan(self):
        """`not_attempted` is a THIRD state. Collapsing it into `failed` would refuse every dry
        run -- the positions sentinel's lesson one function over, and item 63 made exactly that
        mistake on its first attempt."""
        got = LC.run_slot("1", pct=10.0, armed_state={"armed": True, "reason": "fixture"},
                          book=BOOK, client=None, equity=1000.0,
                          marks={"AAPL": {"mid": 100.0}, "MSFT": {"mid": 200.0}},
                          root=self.root, send=False,
                          paper_targets={"AAPL": 60.0, "MSFT": 40.0}, paper_value=100.0, account=ACCOUNT)
        self.assertEqual(got["reconcile"]["order_read"], "not_attempted")
        self.assertTrue(got["orders"], got["reason"])

    def test_the_four_states_are_distinct_and_only_two_refuse(self):
        """Stated as a property so a future fifth state has to decide which side it is on."""
        seen = {}
        for label, sess in (("failed", Alpaca(positions=HOLDS_THE_BOOK, orders_status=500)),
                            ("ok", Alpaca(positions=[], orders=[]))):
            _, p = self.cycle(sess)
            seen[label] = p["reconcile"]["order_read"]
            shutil.rmtree(self.root, True)
            os.makedirs(self.root, exist_ok=True)
        self.assertEqual(seen, {"failed": "failed", "ok": "ok"})


class TheAccountIdPinReportsWhenItDidNotEngage(_Cycle):
    """The auditor's note 2: `if acct_id:` skips the whole block, so a 200 carrying an equity
    and no `id` leaves the slot unpinned **with nothing saying so.**"""

    def test_a_broker_reply_with_no_id_is_reported_rather_than_silent(self):
        class NoId(Alpaca):
            def request(self, method, url, **k):
                if url.endswith("/v2/account"):
                    return Reply({"account_number": "PA1", "equity": "1000", "cash": "1000",
                                  "buying_power": "1000", "status": "ACTIVE"})
                return super().request(method, url, **k)
        _, p = self.cycle(NoId(positions=[], orders=[]))
        self.assertIs(p.get("account_id_recorded"), False)
        self.assertIn("no account id", (p.get("account_id_note") or "").lower())

    def test_an_id_that_IS_returned_reports_recorded(self):
        _, p = self.cycle(Alpaca(positions=[], orders=[], account_id="acct-xyz"))
        self.assertIs(p.get("account_id_recorded"), True)
        self.assertEqual(p.get("account_id"), "acct-xyz")

    def test_it_still_refuses_on_a_CHANGED_id(self):
        """The pin's own job must be intact: reporting its absence is not weakening it."""
        self.cycle(Alpaca(positions=[], orders=[], account_id="acct-A"))
        sess = Alpaca(positions=[], orders=[], account_id="acct-B")
        _, p = self.cycle(sess)
        self.assertEqual(sess.placed, [])
        self.assertIn("account_changed", [a["kind"] for a in p["alerts"]])


class TheRestingOppositeOrderIsCancelledFirst(_Cycle):
    """**PART 2. "Potential wash trade detected. Use complex orders."**

    Alpaca refuses one side of a name while an order rests on the other, and a book that
    re-prices a remainder hits it on real rebalances -- it hit the paper book twice on item 64's
    fifth cycle. The rule: cancel the resting opposite order, CONFIRM the cancel, and if it
    cannot be confirmed that name does not trade this cycle. **No complex orders.**
    """

    def _resting(self, side, symbol="AAPL", qty="6"):
        # **`qty` IS PART OF EVERY REAL ALPACA ORDER AND THIS FIXTURE OMITTED IT [item 67].**
        # Item 67 subtracts a resting order's OPEN quantity from the plan, so an order of
        # unknown size now withholds that name -- and two tests below went red on a recording
        # that was missing a field the API always sends. The same family as the auditor's own
        # question-7 miss: a double that is not the real thing.
        return {"id": "resting-1", "client_order_id": "valquo-paper-rebalance:2026-10-22-%s-a1"
                                                      % symbol,
                "symbol": symbol, "side": side, "status": "new", "filled_qty": "0",
                "qty": qty, "limit_price": "100"}

    def test_a_resting_OPPOSITE_order_is_cancelled_before_the_send(self):
        sess = Alpaca(positions=[], orders=[self._resting("sell")])
        _, p = self.cycle(sess)
        self.assertIn("resting-1", sess.cancelled, p.get("reason"))
        self.assertTrue([o for o in sess.placed if o["symbol"] == "AAPL"],
                        "AAPL never traded after a successful cancel")

    def test_a_resting_SAME_side_order_is_NOT_cancelled(self):
        """Only the opposite side causes the refusal, and cancelling a same-side order would
        throw away a working order for nothing."""
        sess = Alpaca(positions=[], orders=[self._resting("buy")])
        self.cycle(sess)
        self.assertEqual(sess.cancelled, [])

    def test_AND_IT_IS_SUBTRACTED_FROM_THE_PLAN_INSTEAD(self):
        """**THE CONSEQUENT QUESTION, which the auditor named this test for not asking.**

        *"It documents the decision not to cancel and never asks the consequent question -- if
        the working order is kept, must it be subtracted from the plan?"* It must: holdings
        count fills only, so without the subtraction the planner re-plans the whole remainder
        every cycle and the orders STACK. The auditor reproduced five full orders against a
        one-order target.

        AAPL's target is 6 shares at 100 and 6 are already resting, so the correct plan for
        AAPL this cycle is NOTHING.
        """
        sess = Alpaca(positions=[], orders=[self._resting("buy", qty="6")])
        _, p = self.cycle(sess)
        aapl = [o for o in sess.placed if o["symbol"] == "AAPL"]
        self.assertEqual(aapl, [], "the whole remainder was re-sent on top of a resting order")
        self.assertTrue([o for o in sess.placed if o["symbol"] == "MSFT"],
                        "the other names must still trade")

    def test_an_UNCONFIRMED_cancel_means_that_name_does_not_trade(self):
        class CancelFails(Alpaca):
            def request(self, method, url, **k):
                if "/v2/orders/" in url and method == "DELETE":
                    self.cancelled.append("attempted")
                    return Reply({"message": "could not cancel"}, status=500)
                return super().request(method, url, **k)
        sess = CancelFails(positions=[], orders=[self._resting("sell")])
        _, p = self.cycle(sess)
        self.assertEqual([o for o in sess.placed if o["symbol"] == "AAPL"], [],
                         "AAPL traded with an unconfirmed cancel on the opposite side")
        self.assertIn("cancel_unconfirmed", [a["kind"] for a in p["alerts"]])

    def test_the_OTHER_names_still_trade(self):
        """One name's unconfirmed cancel must not stop the book: §8's rule is that a broken
        input stops that trade, and the slot's other names are not broken."""
        class CancelFails(Alpaca):
            def request(self, method, url, **k):
                if "/v2/orders/" in url and method == "DELETE":
                    return Reply({"message": "no"}, status=500)
                return super().request(method, url, **k)
        sess = CancelFails(positions=[], orders=[self._resting("sell", "AAPL")])
        self.cycle(sess)
        self.assertTrue([o for o in sess.placed if o["symbol"] == "MSFT"],
                        "MSFT was stopped by AAPL's problem")

    def test_NO_COMPLEX_ORDER_IS_EVER_SENT(self):
        """Alpaca's own suggestion is "use complex orders"; the brief forbids it, and §8 permits
        a plain limit only. Asserted on the code, not on one fixture's traffic."""
        src = open(LC.__file__, encoding="utf-8").read()
        code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
        for banned in ("order_class", "legs", "bracket", "oco", "oto"):
            self.assertNotIn(banned, code, "a complex-order field appears: %s" % banned)

    def test_a_filled_or_closed_opposite_order_is_not_cancelled(self):
        """Only RESTING orders can cause the refusal. Cancelling a filled one is a pointless
        call that can only fail."""
        done = dict(self._resting("sell"), status="filled", filled_qty="6")
        sess = Alpaca(positions=[], orders=[done])
        self.cycle(sess)
        self.assertEqual(sess.cancelled, [])


class TheWashTradeCountFromItem64(unittest.TestCase):
    """The brief asks how many of item 64's rejections were this. **84 rejections, 2 known to be
    wash trades, 60 unattributable** -- and the unattributable ones are the point.

    | cycle | rejected | reasons |
    |---|---|---|
    | 2 | 60 | **UNATTRIBUTABLE** -- the reason was being discarded, which is the defect item 64 fixed |
    | 3 | 0 | — |
    | 4 | 0 | — |
    | 5 | 24 | **22** `client_order_id must be unique`, **2** `potential wash trade detected` |

    Cycle 2's 60 cannot be split after the fact and are **not** inferred from cycle 5's mix,
    even though both cycles were remainder cycles on the same event and the duplicate-id defect
    was live in both. *"They were probably the same"* is a guess, and the whole reason the
    number is knowable for cycle 5 is that the reporting was fixed in between.

    So the honest answer to the brief: **2 confirmed wash-trade rejections**, both on cycle 5,
    out of 24 legible rejections; 60 earlier ones are unknown and will stay unknown.
    """

    #: Rejections per cycle, from the run logs. Cycle 6's body never arrived, so it is absent
    #: rather than recorded as zero.
    ITEM_64_REJECTIONS = {2: 60, 3: 0, 4: 0, 5: 24}
    #: Of cycle 5's 24, by reason.
    CYCLE_5_BY_REASON = {"client_order_id must be unique": 22,
                         "potential wash trade detected": 2}

    def test_the_counts_add_up(self):
        self.assertEqual(sum(self.CYCLE_5_BY_REASON.values()), self.ITEM_64_REJECTIONS[5])

    def test_two_were_wash_trades_and_sixty_are_unattributable(self):
        self.assertEqual(self.CYCLE_5_BY_REASON["potential wash trade detected"], 2)
        self.assertEqual(self.ITEM_64_REJECTIONS[2], 60)

    def test_cycle_6_is_ABSENT_rather_than_recorded_as_zero(self):
        """`C5`'s rule. Its body never reached the run log, so what it did is unknown -- and
        writing 0 would make an unreadable cycle look like a clean one."""
        self.assertNotIn(6, self.ITEM_64_REJECTIONS)

    def test_the_reason_reader_handles_the_wash_trade_shape(self):
        """The 2 are known only because item 64 made the reason legible; this pins that the
        exact Alpaca shape they arrived in still reads."""
        from valuation.edge import live_cycle as _LC
        got = _LC._rejection_reason(
            {"ok": False, "reason": "the broker rejected the order",
             "detail": {"status": 403,
                        "error": {"message": "potential wash trade detected. use complex "
                                             "orders"}}})
        self.assertIn("potential wash trade detected", got)


class TheCycleLogIsReadable(unittest.TestCase):
    """**PART 3.** Cycle 6's body was lost because GitHub dropped the single ~35KB line -- and
    the three summary lines that existed so nobody would have to parse it were in the same step
    and went with it. So: one short line per field, in a step that runs BEFORE the HTTP check,
    and the body uploaded as an artifact."""

    @classmethod
    def setUpClass(cls):
        """**PARSED AS TEXT, BECAUSE PyYAML IS NOT IN THE CI ENVIRONMENT.**

        My first cut imported `yaml` and the gate returned `ModuleNotFoundError` --
        item 64's own schedule test uses `re.findall` for exactly that reason, and I wrote a new
        one instead of reading the neighbouring test. Doing the YAML block dedent by hand is the
        better version anyway: the whole point of `test_the_embedded_python_parses` is that the
        heredoc body lands at column 0, so performing the dedent here means the test verifies it
        rather than trusting a library to have done it.
        """
        p = os.path.join(REPO, "pending_workflows", "live-cycle.yml")
        cls.src = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")
        lines = cls.src.split("\n")
        # The `run: |` block, dedented exactly as YAML would.
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "run: |")
        indent = len(lines[start]) - len(lines[start].lstrip()) + 2
        body = []
        for ln in lines[start + 1:]:
            if ln.strip() and not ln.startswith(" " * indent):
                break
            body.append(ln[indent:] if len(ln) >= indent else ln.strip())
        # **NOT `cls.run` -- THAT SHADOWS `TestCase.run` AND UNITTEST THEN CALLS A STRING.**
        # The whole suite died with `TypeError: 'str' object is not callable` from inside
        # unittest's own machinery, which points nowhere near the cause.
        cls.script = "\n".join(body)
        heredoc = cls.script.split("<<'PYEOF'", 1)[1].split("PYEOF", 1)[0]
        cls.summary = heredoc.split("\n", 1)[1]

    def test_the_embedded_python_parses(self):
        """**THE FILE'S OWN WARNING IS ABOUT EXACTLY THIS**: an earlier version indented a
        heredoc body and its terminator, and indented Python is an `IndentationError` -- which
        would have gone red on every run AFTER the cycle had already succeeded. YAML's block
        dedent puts both at column 0; this asserts it rather than trusting it."""
        import ast
        ast.parse(self.summary)
        self.assertTrue(self.summary.startswith("import json, sys"), self.summary[:60])

    def test_the_35KB_line_is_GONE(self):
        """`cat "$BODY"` is what produced the line GitHub dropped."""
        code = "\n".join(ln.split("#", 1)[0] for ln in self.script.splitlines())
        self.assertNotIn('cat "$BODY"', code)

    def test_one_line_per_field(self):
        for field in ("mode", "session", "event", "priced", "sent", "accepted", "rejected",
                      "filled", "held", "order_read", "cancelled", "blocked", "send_seq",
                      "no_progress", "account_pinned", "refusal"):
            self.assertIn('print("%s' % field, self.summary,
                          "no line prints %s" % field)

    def test_the_summary_runs_BEFORE_the_http_check(self):
        """A 4xx/5xx cycle is the one most worth reading, and the first cut checked the status
        first -- so the only outcome that mattered printed nothing."""
        code = self.script
        self.assertLess(code.index("<<'PYEOF'"), code.index('[ "$CODE" = "200" ]'))

    def test_the_body_is_uploaded_as_an_artifact_even_on_failure(self):
        """Asserted on the text, for the same reason as `setUpClass`. The `if: always()` is the
        load-bearing part: a FAILED cycle's body is the one most worth having, and that is
        exactly the run where the step before it exits non-zero."""
        self.assertIn("upload-artifact", self.src)
        step = self.src[self.src.index("Keep the cycle's full body"):]
        self.assertIn("if: always()", step.split("- name:")[0])
        self.assertIn("live-cycle-body.json", step.split("- name:")[0])
        # **ITEM 67 ADDED A SECOND ARTIFACT STEP** (the fractional census), so the property
        # is no longer "there is exactly one" -- it is that EVERY upload runs on failure too,
        # which is what the original count was standing in for. A count was the weaker test.
        blocks = [b for b in self.src.split("      - name:") if "upload-artifact" in b]
        self.assertGreaterEqual(len(blocks), 2, "the artifact steps moved")
        for b in blocks:
            self.assertIn("if: always()", b,
                          "an artifact step would be skipped on a failed cycle")

    def test_it_runs_on_a_REAL_cycle_body(self):
        """Exercised against the recorded body of item 64's fifth cycle rather than a fixture,
        because that body is the shape that defeated the old logging."""
        import subprocess
        import sys as _sys
        body = {
            "mode": "paper", "session": {"ok": True, "local_time": "15:03"},
            "alerts": [{"slot": "paper", "kind": "broker_error",
                        "reason": "order for %s was rejected: the broker rejected the order; "
                                  "client_order_id must be unique; HTTP 422" % t}
                       for t in ("AAPL", "MSFT", "NVDA")],
            "slots": [],
            "reason": "no live slot has a key pair configured",
            "paper": {"event": "remainder", "event_key": "rebalance:2026-07-30",
                      "marks_coverage": {"n_priced": 85, "n_needed": 85},
                      "sent": ([{"ok": True}] * 43
                               + [{"ok": False, "detail": "client_order_id must be unique"}]
                               * 22),
                      "reconcile": {"n_filled": 161, "n_orders": 239,
                                    "holdings": {str(i): 1.0 for i in range(81)},
                                    "order_read": "ok"},
                      "cancelled": [], "blocked_by_cancel": [], "send_seq": 5,
                      "attempts_without_progress": 1, "account_id_recorded": True,
                      "reason": "sent 65 order(s)"},
        }
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        bp = os.path.join(d, "body.json")
        sp = os.path.join(d, "summ.py")
        with open(bp, "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        with open(sp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(self.summary)
        r = subprocess.run([_sys.executable, sp, bp], capture_output=True)
        out = r.stdout.decode("utf-8", "replace")
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-400:])
        self.assertIn("priced        : 85 of 85", out)
        self.assertIn("rejected      : 22", out)
        self.assertIn("held          : 81 names", out)
        self.assertIn("reject x22", out)
        # DEDUPED: three alerts with the same cause and different tickers are ONE line.
        self.assertEqual(out.count("broker_error"), 1, out)
        self.assertIn("AAPL", out)
        # AND EVERY LINE IS SHORT, which is the whole point.
        worst = max(len(ln) for ln in out.splitlines())
        self.assertLess(worst, 400, "a line is %d chars long" % worst)

    def test_no_silent_cap(self):
        """The project's own rule: a report that bounds its coverage says what it dropped."""
        self.assertIn("further group(s) covering", self.summary)
        self.assertIn("further DISTINCT reason(s) not shown", self.summary)


class TheScheduleAndTheLoggingShipTogether(unittest.TestCase):
    """The brief: if the schedule change is still pending, fold this in so Don installs once.
    Measured -- the installed copy still carries the single `40 14` cron, so it is."""

    @classmethod
    def setUpClass(cls):
        cls.src = io.open(os.path.join(REPO, "pending_workflows", "live-cycle.yml"),
                          encoding="utf-8").read()

    def test_the_item_64_schedule_is_still_in_the_pending_file(self):
        import re
        crons = re.findall(r'cron:\s*"([^"]+)"', self.src)
        self.assertIn("30 11 * * 1-5", crons)
        self.assertIn("0 12 * * 1-5", crons)
        self.assertEqual(len(crons), 5, crons)

    def test_one_install_covers_both(self):
        self.assertIn("PENDING INSTALL", self.src)
        self.assertIn("install_workflows.bat", self.src)

    def test_the_send_token_is_still_paper(self):
        code = "\n".join(ln.split("#", 1)[0] for ln in self.src.splitlines())
        self.assertIn("run=paper", code)
        self.assertNotIn("run=1", code)


class TheSixUnpricedExitsAreRestated(unittest.TestCase):
    """**PART 4.** CNA, ABCL, BEAM, HIVE, IDYA and NUVB were closed "left coverage" at their own
    entry price, because the scan's coverage churns and the `price_fn` re-pricing did not exist
    until 2026-09-30. `positions.summary` already excludes them -- *an exit that was never
    re-priced is UNKNOWN, not zero* -- so the published figure is honest and six closes carry no
    return. This supplies the prices, as a DATED restatement that keeps the old value."""

    NAMES = ("CNA", "ABCL", "BEAM", "HIVE", "IDYA", "NUVB")

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        from valuation.screener.store import Store
        self.store = Store(os.path.join(self.d, "t.db"))
        for i, t in enumerate(self.NAMES):
            entry = 100.0 + i
            self.store.open_position("hotstocks", t, "2026-08-10", entry)
            # CLOSED AT THE ENTRY PRICE -- the defect, reproduced.
            self.store.close_position("hotstocks", t, "2026-08-10", "2026-09-01", entry,
                                      "left coverage")

    def _hist(self, moves=None, missing=()):
        """A price vendor whose close on the exit date moves each name by a known amount."""
        import pandas as pd
        moves = moves or {t: 0.10 for t in self.NAMES}

        def history(ticker, days=None):
            if ticker in missing:
                return pd.DataFrame({"Date": ["2026-08-29"], "close": [1.0]})
            i = self.NAMES.index(ticker) if ticker in self.NAMES else 0
            entry = 100.0 + i
            return pd.DataFrame({"Date": ["2026-08-10", "2026-09-01"],
                                 "close": [entry, entry * (1.0 + moves.get(ticker, 0.0))]})
        return history

    def test_all_six_are_found_as_candidates(self):
        from valuation.edge import exit_restate as RX
        rows = self.store.all_positions("hotstocks")
        got = RX.unpriced_exits(rows)
        self.assertEqual(sorted(p["ticker"] for p in got), sorted(self.NAMES))

    def test_the_plan_prices_each_from_ITS_OWN_exit_date(self):
        """Not the last close, not today's: the close on the day it was recorded closed, so the
        restated return is the one the book actually experienced."""
        from valuation.edge import exit_restate as RX
        got = RX.plan(self.store.all_positions("hotstocks"),
                      history=self._hist({"CNA": -0.045, "ABCL": 0.208, "BEAM": 0.064,
                                          "HIVE": 0.015, "IDYA": 0.087, "NUVB": 0.006}))
        self.assertEqual(got["n_candidates"], 6)
        self.assertEqual(got["n_priceable"], 6)
        by = {r["ticker"]: r for r in got["rows"]}
        self.assertAlmostEqual(by["ABCL"]["ret_gross"], 0.208, places=6)
        self.assertAlmostEqual(by["CNA"]["ret_gross"], -0.045, places=6)

    def test_the_managers_figures_are_a_CONTROL_and_not_a_source(self):
        """The brief supplies them and says not to copy them. So they are compared against, and
        the gap is reported -- two vendors agreeing is evidence; copying manufactures it."""
        from valuation.edge import exit_restate as RX
        got = RX.plan(self.store.all_positions("hotstocks"),
                      history=self._hist({"CNA": -0.045, "ABCL": 0.208, "BEAM": 0.064,
                                          "HIVE": 0.015, "IDYA": 0.087, "NUVB": 0.006}))
        for r in got["rows"]:
            self.assertIn("control_gap_pp", r, r["ticker"])
            self.assertLess(abs(r["control_gap_pp"]), 0.01, r)
        self.assertIn("CONTROL rather than a source", got["control_note"])

    def test_a_DISAGREEMENT_with_the_control_is_reported_not_hidden(self):
        """THE POSITIVE CONTROL for the test above: if the gap were never computed, perfect
        agreement would prove nothing."""
        from valuation.edge import exit_restate as RX
        got = RX.plan(self.store.all_positions("hotstocks"),
                      history=self._hist({"CNA": 0.50}))
        by = {r["ticker"]: r for r in got["rows"]}
        self.assertGreater(abs(by["CNA"]["control_gap_pp"]), 50.0, by["CNA"])

    def test_a_name_with_NO_close_on_its_exit_date_is_LEFT_UNRESTATED(self):
        """**NO FALLBACK.** A neighbouring day's close under this day's label is a wrong number,
        and an unpriced exit is already handled honestly by being excluded -- so replacing it
        with a wrong price would turn an acknowledged gap into a silent error."""
        from valuation.edge import exit_restate as RX
        planned = RX.plan(self.store.all_positions("hotstocks"),
                          history=self._hist(missing=("HIVE",)))
        self.assertEqual(planned["n_unpriceable"], 1)
        bad = [r for r in planned["rows"] if not r["ok"]]
        self.assertEqual(bad[0]["ticker"], "HIVE")
        self.assertIn("no close on 2026-09-01", bad[0]["reason"])
        wrote = RX.apply_plan(self.store, planned)
        self.assertEqual([x["ticker"] for x in wrote["skipped"]], ["HIVE"])
        self.assertEqual(len(wrote["restated"]), 5)

    def test_the_tolerance_is_declared_as_ZERO(self):
        from valuation.edge import exit_restate as RX
        self.assertEqual(RX.EXIT_DATE_TOLERANCE_DAYS, 0)

    def test_the_old_value_is_KEPT_beside_the_new_one(self):
        from valuation.edge import exit_restate as RX
        planned = RX.plan(self.store.all_positions("hotstocks"), history=self._hist())
        RX.apply_plan(self.store, planned, on_date="2026-10-16")
        rows = {p["ticker"]: p for p in self.store.all_positions("hotstocks")}
        cna = rows["CNA"]
        self.assertEqual(cna["exit_price_original"], 100.0)
        self.assertAlmostEqual(cna["exit_price"], 110.0)
        self.assertEqual(cna["restated_on"], "2026-10-16")
        self.assertIn("2026-09-01", cna["restated_source"])

    def test_RESTATING_TWICE_REFUSES_and_keeps_the_FIRST_original(self):
        """A second run must not overwrite the original with the first restatement's value --
        that would lose what was actually published, which is the whole point of keeping it."""
        from valuation.edge import exit_restate as RX
        planned = RX.plan(self.store.all_positions("hotstocks"), history=self._hist())
        RX.apply_plan(self.store, planned, on_date="2026-10-16")
        again = RX.plan(self.store.all_positions("hotstocks"),
                        history=self._hist({t: 0.99 for t in self.NAMES}))
        self.assertEqual(again["n_candidates"], 0,
                         "an already-restated row is still a candidate")
        rows = {p["ticker"]: p for p in self.store.all_positions("hotstocks")}
        self.assertEqual(rows["CNA"]["exit_price_original"], 100.0)

    def test_it_refuses_to_restate_an_OPEN_position(self):
        self.store.open_position("hotstocks", "OPENX", "2026-10-01", 10.0)
        got = self.store.restate_exit_price("hotstocks", "OPENX", "2026-10-01", 12.0,
                                            "2026-10-16", "x")
        self.assertFalse(got["ok"])
        self.assertIn("still open", got["reason"])

    def test_it_refuses_a_position_that_does_not_exist(self):
        got = self.store.restate_exit_price("hotstocks", "NOPE", "2026-01-01", 1.0, "x", "y")
        self.assertFalse(got["ok"])

    def test_the_restated_exits_REJOIN_the_realised_average(self):
        """The point of the whole exercise: before, six closes carried no return at all."""
        from valuation.edge import exit_restate as RX
        from valuation.edge import positions as POS
        before = POS.paper_summary(self.store, "hotstocks")["summary"]
        self.assertEqual(before["n_unpriced_exits"], 6)
        self.assertIsNone(before["avg_return_closed"])
        planned = RX.plan(self.store.all_positions("hotstocks"), history=self._hist())
        RX.apply_plan(self.store, planned, on_date="2026-10-16")
        after = POS.paper_summary(self.store, "hotstocks")["summary"]
        self.assertEqual(after["n_unpriced_exits"], 0)
        self.assertAlmostEqual(after["avg_return_closed"], 0.10, places=2)
        self.assertEqual(after["n_restated_exits"], 6)

    def test_the_restatement_RAISES_the_figure_as_the_brief_predicts(self):
        """The brief: including them should raise the realised figure, not lower it -- five of
        the six rose. A check on the DIRECTION, computed from our own vendor."""
        from valuation.edge import exit_restate as RX
        from valuation.edge import positions as POS
        planned = RX.plan(self.store.all_positions("hotstocks"),
                          history=self._hist({"CNA": -0.045, "ABCL": 0.208, "BEAM": 0.064,
                                              "HIVE": 0.015, "IDYA": 0.087, "NUVB": 0.006}))
        RX.apply_plan(self.store, planned, on_date="2026-10-16")
        after = POS.paper_summary(self.store, "hotstocks")["summary"]
        self.assertGreater(after["avg_return_closed"], 0.0,
                           "the restated average is not positive")


class LeftCoverageIsShownApartFromTheSellRule(unittest.TestCase):
    """**PART 4b.** 19 of the 29 closes are coverage-gap closes, and they say NOTHING about the
    sell rule -- pooling them makes the rule look like it produced returns it never chose."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        from valuation.screener.store import Store
        self.store = Store(os.path.join(self.d, "t.db"))
        # Two coverage closes that LOST, and one sell-rule close that WON -- so pooling and
        # splitting give visibly different answers and a test cannot pass by them agreeing.
        for t, px, out_px, why in (("AAA", 100.0, 80.0, "left coverage"),
                                   ("BBB", 100.0, 90.0, "left coverage"),
                                   ("CCC", 100.0, 150.0, "hit fair value")):
            self.store.open_position("hotstocks", t, "2026-08-10", px)
            self.store.close_position("hotstocks", t, "2026-08-10", "2026-09-01", out_px, why)

    def test_the_two_groups_are_reported_separately(self):
        from valuation.edge import positions as POS
        got = POS.paper_summary(self.store, "hotstocks")["summary"]
        self.assertEqual(got["n_closed_left_coverage"], 2)
        self.assertEqual(got["n_closed_sell_rule"], 1)
        self.assertLess(got["avg_return_left_coverage"], 0)
        self.assertGreater(got["avg_return_sell_rule"], 0)

    def test_the_POOLED_figure_is_still_reported(self):
        """Neither group replaces it: the pooled number is what the book actually did."""
        from valuation.edge import positions as POS
        got = POS.paper_summary(self.store, "hotstocks")["summary"]
        self.assertIsNotNone(got["avg_return_closed"])
        self.assertNotEqual(got["avg_return_closed"], got["avg_return_sell_rule"])

    def test_the_split_says_in_words_which_one_is_evidence_about_the_rule(self):
        from valuation.edge import positions as POS
        note = POS.paper_summary(self.store, "hotstocks")["summary"]["split_note"]
        self.assertIn("NOTHING about the", note)
        self.assertIn("gap clock", note)

    def test_each_closed_row_says_which_kind_it_is(self):
        from valuation.edge import positions as POS
        rows = POS.paper_summary(self.store, "hotstocks")["closed"]
        by = {r["ticker"]: r for r in rows}
        self.assertTrue(by["AAA"]["left_coverage"])
        self.assertFalse(by["AAA"]["sell_rule"])
        self.assertTrue(by["CCC"]["sell_rule"])

    def test_an_unpriced_exit_is_in_NEITHER_group(self):
        """They were never observed again, so they carry no return either way."""
        from valuation.edge import positions as POS
        self.store.open_position("hotstocks", "DDD", "2026-08-10", 50.0)
        self.store.close_position("hotstocks", "DDD", "2026-08-10", "2026-09-01", 50.0,
                                  "left coverage")
        got = POS.paper_summary(self.store, "hotstocks")["summary"]
        self.assertEqual(got["n_unpriced_exits"], 1)
        self.assertEqual(got["n_closed_left_coverage"], 2, "the unpriced one was counted in")


class TheRestatementDoorPlansBeforeItWrites(unittest.TestCase):
    def setUp(self):
        # **THE TOKEN COMES FROM `CONFIG` AT APP-CREATION TIME, NOT FROM THE ENVIRONMENT AT
        # CALL TIME.** Setting `os.environ["ADMIN_TOKEN"]` after import authenticated nothing
        # and every door test got a 401 -- and `tests/test_item62.py` already had this right.
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        CONFIG.admin_token = "test-token-item65"
        app = create_saas_app(CONFIG)
        app.config["TESTING"] = True
        self.c, self.h = app.test_client(), {"X-Admin-Token": CONFIG.admin_token}

    def test_it_is_owner_only(self):
        for verb in ("get", "post"):
            r = getattr(self.c, verb)("/admin/restate-exits")
            self.assertEqual(r.status_code, 401, verb)

    def test_a_GET_carrying_run_1_is_405_rather_than_downgraded(self):
        """The `/admin/track-row` lesson: a side-effecting GET on a record that cannot be
        re-derived is reachable by a retry, a prefetch or a pasted link."""
        r = self.c.get("/admin/restate-exits?run=1", headers=self.h)
        self.assertEqual(r.status_code, 405)
        self.assertIn("requires POST", r.get_data(as_text=True))

    def test_a_plain_GET_plans_and_writes_nothing(self):
        r = self.c.get("/admin/restate-exits", headers=self.h)
        self.assertEqual(r.status_code, 200)
        got = json.loads(r.get_data(as_text=True))
        self.assertIsNone(got["wrote"])
        self.assertIn("plan", got)
        self.assertIn("GET plans and writes nothing", got["how"])

    def test_the_payload_explains_what_an_unpriceable_name_means(self):
        got = json.loads(self.c.get("/admin/restate-exits",
                                    headers=self.h).get_data(as_text=True))
        self.assertIn("LEFT UNRESTATED", got["unpriceable_note"])
        self.assertIn("no fallback", got["unpriceable_note"])


class _SipGatedAlpaca:
    """**ALPACA'S DOCUMENTED RULE, IMPLEMENTED AS A FIXTURE.** [item 65 part 5]

    This is the thing item 64's tests did not have. They verified the window *"at every
    quarter-hour of a week against the rule's own definition"* -- that the end's session close is
    more than the delay in the past -- and **that test could not fail, because it asserted the
    rule against itself.** It never asked what the rule's output means to the VENDOR, which is
    the only thing that decides whether the request is served.

    So this refuses exactly as Alpaca's FAQ says it does: *"the `end` parameter must be at least
    15 minutes old to query SIP data without a subscription"*, with the real payload
    `{"code":42210000,"message":"subscription does not permit querying recent SIP data"}`.

    **`date_means` IS A PARAMETER BECAUSE THE EXPANSION IS NOT DOCUMENTED.** Alpaca's docs show
    bare dates in examples and say nothing about whether one becomes 00:00:00 or 23:59:59. Both
    readings are tested, and the fix has to hold under either -- which is the whole reason the
    fix sends an explicit instant rather than reasoning about the expansion.
    """

    def __init__(self, now, date_means="end_of_day", delay_minutes=15):
        self.now, self.date_means, self.delay = now, date_means, delay_minutes
        self.ends, self.served = [], 0

    def _instant(self, raw):
        import datetime as _dt
        txt = str(raw or "")
        if "T" in txt:
            return _dt.datetime.strptime(txt[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=_dt.timezone.utc)
        if not txt:
            return None
        d = _dt.date.fromisoformat(txt[:10])
        if self.date_means == "start_of_day":
            return _dt.datetime(d.year, d.month, d.day, 0, 0, tzinfo=_dt.timezone.utc)
        return _dt.datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=_dt.timezone.utc)

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        import datetime as _dt
        end = (params or {}).get("end")
        self.ends.append(end)
        inst = self._instant(end)
        # NO `end` AT ALL IS SAFE: the FAQ records that a subscription-less default is set to 15
        # minutes ago, which is item 62's own observation from the other side -- that run got
        # served and returned one bar because it also sent no `start`.
        if inst is not None:
            age = (self.now - inst).total_seconds() / 60.0
            if age < self.delay:
                return Reply({"code": 42210000,
                              "message": "subscription does not permit querying recent "
                                         "SIP data"}, status=403)
        self.served += 1
        syms = str((params or {}).get("symbols") or "").split(",")
        bars = {}
        for sym in [x for x in syms if x]:
            bars[sym] = [{"t": "2026-10-%02dT00:00:00Z" % d, "o": 1, "h": 1, "l": 1,
                          "c": 100.0 + d, "v": 1} for d in range(1, 16)]
        return Reply({"bars": bars})


class TheWindowsEndIsSentAsAnInstant(unittest.TestCase):
    """**PART 5.** Don ran the door at ~22:00Z on 2026-10-16, after item 64 deployed. The new
    code worked -- its own "RE-RUNNING WILL NOT HELP" note came back -- and the pull still got
    nothing, because the bare date it sent was TODAY."""

    import datetime as _dt
    EVENING = _dt.datetime(2026, 10, 16, 22, 0, tzinfo=_dt.timezone.utc)

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _noyf(self, t, days=None):
        return {"adj": {}, "asof": {}, "error": "fixture"}

    def test_our_side_reproduces_DONS_EXACT_WINDOW(self):
        """Before diagnosing anything: the observation is reproduced, so the rest is about the
        same request Don made and not a lookalike."""
        w = S.window(now=self.EVENING)
        self.assertEqual((w["start"], w["end"]), ("2025-09-11", "2026-10-16"))

    def test_the_date_is_STILL_today_and_that_is_correct_by_the_rule(self):
        """The rule is not wrong: today's 21:00Z close IS more than 16 minutes before the
        21:44Z cutoff. The date was right and the WIRE VALUE was the problem."""
        self.assertEqual(S.sip_safe_end(self.EVENING)["end"].isoformat(), "2026-10-16")

    def test_the_wire_value_is_an_RFC_3339_INSTANT_in_the_past(self):
        w = S.window(now=self.EVENING)
        self.assertEqual(w["end_param"], "2026-10-16T21:00:00Z")
        inst = dt.datetime.strptime(w["end_param"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc)
        age = (self.EVENING - inst).total_seconds() / 60.0
        self.assertGreaterEqual(age, S.SIP_DELAY_MINUTES)

    def test_THE_EVENING_CASE_IS_SERVED_against_a_recorded_Alpaca(self):
        """**THE TEST THE BRIEF ASKS FOR**, and it is against the vendor's rule rather than
        ours."""
        for means in ("end_of_day", "start_of_day"):
            sess = _SipGatedAlpaca(self.EVENING, date_means=means)
            c = AD.AlpacaData("k" * 12, "s" * 12, session=sess)
            root = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, root, True)
            got = S.pull(client=c, names=["AAPL", "MSFT"], root=root, end=None,
                         yf_fetch=self._noyf, now=self.EVENING)
            self.assertGreater(got["n_alpaca"], 0,
                               "the evening pull got nothing under date_means=%s: %s"
                               % (means, got.get("reason")))
            self.assertTrue(all("T" in str(e) for e in sess.ends), sess.ends)

    def test_THE_OLD_BARE_DATE_IS_REFUSED_by_the_same_fixture(self):
        """**THE CONTROL that makes the test above mean something.** If the fixture served
        everything, "it is served now" would prove nothing. A bare TODAY date is refused under
        the end-of-day reading, which is what Don observed."""
        sess = _SipGatedAlpaca(self.EVENING, date_means="end_of_day")
        c = AD.AlpacaData("k" * 12, "s" * 12, session=sess)
        got = c.bars(["AAPL"], adjustment=AD.ADJ_ALL, start="2025-09-11", end="2026-10-16")
        self.assertFalse(got.get("ok"), "the fixture served a bare today-date")
        self.assertIn("recent SIP data", str(got.get("error")))
        self.assertEqual(sess.served, 0)

    def test_the_BRIEFS_PREDICTION_holds_a_bare_date_is_fine_once_it_is_YESTERDAY(self):
        """The brief predicts the old code works *"before about 21:16Z on a weekday, and all
        weekend"*, because then the end rolls back to a finished day. Checked -- and it is why
        this went unnoticed through item 64's own in-session runs."""
        midday = dt.datetime(2026, 10, 16, 17, 36, tzinfo=dt.timezone.utc)
        self.assertEqual(S.window(now=midday)["end"], "2026-10-15")
        sess = _SipGatedAlpaca(midday, date_means="end_of_day")
        c = AD.AlpacaData("k" * 12, "s" * 12, session=sess)
        got = c.bars(["AAPL"], adjustment=AD.ADJ_ALL, start="2025-09-11", end="2026-10-15")
        self.assertTrue(got.get("ok"), "a bare YESTERDAY date was refused")

    def test_a_caller_supplied_end_is_sent_AS_GIVEN(self):
        """Reproducing a recorded window means reproducing the REQUEST; silently converting it
        would make a reproduction a different request."""
        w = S.window(end=dt.date(2026, 1, 2))
        self.assertEqual(w["end_param"], "2026-01-02")
        self.assertEqual(w["end_param_bound"], "supplied_by_the_caller")

    def test_the_instant_is_the_EARLIER_of_the_close_and_now_minus_the_delay(self):
        """Both candidates are instants here, so unlike the DATE version there is no unit
        mismatch -- which is the defect item 64 found in the brief's own first suggestion."""
        just_after = dt.datetime(2026, 10, 19, 21, 10, tzinfo=dt.timezone.utc)
        got = S.sip_safe_end_instant(just_after)
        inst = dt.datetime.strptime(got["param"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc)
        self.assertLessEqual((just_after - inst).total_seconds() / 60.0 * -1,
                             -S.SIP_DELAY_MINUTES)

    def test_the_wire_value_is_NEVER_too_recent_across_a_full_week(self):
        """The sweep item 64 ran, pointed at the thing that actually decides the outcome: not
        "does my rule obey my rule" but "is what I send old enough"."""
        n = dt.datetime(2026, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
        for _ in range(7 * 24 * 4):
            w = S.window(now=n)
            self.assertIn("T", w["end_param"], w)
            inst = dt.datetime.strptime(w["end_param"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=dt.timezone.utc)
            age = (n - inst).total_seconds() / 60.0
            self.assertGreaterEqual(age, S.SIP_DELAY_MINUTES,
                                    "at %s the end sent is only %.1f minutes old" % (n, age))
            n += dt.timedelta(minutes=15)

    def test_the_note_no_longer_names_a_cause_THAT_CANNOT_HAPPEN(self):
        """It said *"an explicit end= was probably supplied"*, and `/admin/alpaca-seam` calls
        `pull(root=None, budget_names=...)` and accepts no `end` at all. **A diagnosis naming an
        impossible cause is worse than none**, because it sends the reader looking for something
        that is not there."""
        sess = _SipGatedAlpaca(self.EVENING, date_means="end_of_day")
        c = AD.AlpacaData("k" * 12, "s" * 12, session=sess)
        got = S.pull(client=c, names=["AAPL"], root=self.root, end=dt.date(2026, 10, 16),
                     yf_fetch=self._noyf, now=self.EVENING)
        self.assertFalse(got["advanced"])
        self.assertNotIn("explicit end= was probably supplied", got["rerun_note"])
        self.assertIn("42210000", got["rerun_note"])
        self.assertIn("2026-10-16", got["rerun_note"])

    def test_the_door_cannot_supply_an_end_so_the_old_note_was_unreachable(self):
        """Asserted on the door's source, because that is what made the old wording false."""
        import inspect
        from valuation.saas import app_saas
        src = inspect.getsource(app_saas)
        door = src[src.index("def admin_alpaca_seam("):]
        door = door[:door.index("def admin_live_slots(")]
        code = chr(10).join(ln.split("#", 1)[0] for ln in door.splitlines())
        self.assertIn("SEAM.pull(", code)
        self.assertNotIn("end=", code, "the door now accepts an end, so the note's old cause "
                                       "is reachable again and should be restored")

    def test_WHY_ITEM_64_MISSED_IT_is_recorded(self):
        """The brief asks for this explicitly, and it is the portable part: item 64's sweep
        asserted the rule against its own definition, so it could not fail."""
        doc = (S.sip_safe_end_instant.__doc__ or "") + (S.__doc__ or "")
        self.assertIn("not an instant", doc.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
