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
                          paper_targets={"AAPL": 60.0, "MSFT": 40.0}, paper_value=100.0)
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

    def _resting(self, side, symbol="AAPL"):
        return {"id": "resting-1", "client_order_id": "valquo-paper-rebalance:2026-10-22-%s-a1"
                                                      % symbol,
                "symbol": symbol, "side": side, "status": "new", "filled_qty": "0",
                "limit_price": "100"}

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
        import yaml
        p = os.path.join(REPO, "pending_workflows", "live-cycle.yml")
        cls.src = io.open(p, encoding="utf-8").read()
        cls.doc = yaml.safe_load(cls.src)
        cls.steps = cls.doc["jobs"]["cycle"]["steps"]
        # **NOT `cls.run` -- THAT SHADOWS `TestCase.run` AND UNITTEST THEN CALLS A STRING.**
        # The whole suite died with `TypeError: 'str' object is not callable` from inside
        # unittest's own machinery, which points nowhere near the cause.
        cls.script = cls.steps[0]["run"]
        body = cls.script.split("<<'PYEOF'", 1)[1].split("PYEOF", 1)[0]
        cls.summary = body.split("\n", 1)[1]

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
        up = [st for st in self.steps if "upload-artifact" in str(st.get("uses") or "")]
        self.assertEqual(len(up), 1, "no artifact step")
        self.assertTrue(up[0].get("if") in (True, "always()", "${{ always() }}"),
                        "the artifact is not kept on a failed cycle: %r" % up[0].get("if"))
        self.assertIn("live-cycle-body", up[0]["with"]["path"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
