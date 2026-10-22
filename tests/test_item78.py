# -*- coding: utf-8 -*-
"""ITEM 78 — WHAT DON'S RUN #25 SHOWED, AND WHY EACH OF IT WAS WRONG.

Don replaced the Index paper keys on Render on 2026-10-21 and ran LIVE PATH CYCLE #25 by hand.
It succeeded, with two warnings and a Discord line, and every one of the three was a defect:

  1. the paper slot refused its own order history as TRUNCATED when it had been read in full;
  2. the privacy filter silently refused to post the warning saying so;
  3. a 0% slot holding nothing listed 31 names it "would trade".

Plus two from the 4:54pm REBALANCE WATCH an hour earlier: it declared two slot conditions
CLEARED without having evaluated either, and it reminds Don daily about eleven missed record
days that cannot be repaired.

**EVERY TEST HERE FAILS ON THE PRE-ITEM-78 TREE**, which is measured rather than claimed:
`python -m scripts.i78_before` restores the sources from git and runs them.

Every HTTP reply is a recorded fixture. Nothing touches a network and nothing places an order.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import alpaca_broker as AB      # noqa: E402
from valuation.edge import live_cycle as LC         # noqa: E402
from valuation.edge import live_notify as LN        # noqa: E402
from valuation.edge import live_slots as LS         # noqa: E402
from valuation.edge import settlement as SETTLE     # noqa: E402
from valuation.saas import alert_routing as AR      # noqa: E402
from valuation.screener import rebalance_watch as RW  # noqa: E402

PAGE = LC.ORDERS_PAGE_LIMIT          # 500, imported rather than retyped
COID = LC.client_order_id("paper", "rebalance:2026-07-30", "AAPL")


class Reply:
    def __init__(self, payload, status=200):
        self.status_code, self._p, self.text = status, payload, ""

    def json(self):
        return self._p


def order(i, stamp=None, qty="1"):
    """One filled order of this slot's own, with a distinct submission timestamp."""
    return {"id": "o-%d" % i, "client_order_id": COID, "symbol": "AAPL", "side": "buy",
            "qty": qty, "filled_qty": qty, "status": "filled", "limit_price": "100",
            "filled_avg_price": "100",
            "submitted_at": stamp if stamp is not None else
            "2026-10-01T%02d:%02d:%02dZ" % ((i // 3600) % 24, (i // 60) % 60, i % 60)}


class RecordedOrders:
    """Alpaca's `/v2/orders` paging, replayed against the REAL `AlpacaPaperBroker`.

    `after` is honoured the way Alpaca documents it -- EXCLUSIVE on the submission timestamp --
    so the fixture reproduces the cursor semantics the pager has to be correct about rather
    than a convenient approximation of them.
    """

    def __init__(self, rows, *, fail_after_page=None, inclusive_after=False):
        self.rows = list(rows)
        self.fail_after_page = fail_after_page
        self.inclusive_after = inclusive_after
        self.pages_served = 0
        self.params_seen = []

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        if url.endswith("/v2/account"):
            return Reply({"id": "acct-paper-1", "account_number": "PA1", "equity": "10000",
                          "cash": "10000", "buying_power": "10000",
                          "non_marginable_buying_power": "10000", "status": "ACTIVE",
                          "multiplier": "1"})
        if url.endswith("/v2/positions"):
            return Reply([])
        if url.endswith("/v2/orders") and method == "GET":
            self.pages_served += 1
            self.params_seen.append(dict(params or {}))
            if self.fail_after_page and self.pages_served > self.fail_after_page:
                return Reply({"message": "server error"}, status=500)
            rows, after = self.rows, (params or {}).get("after")
            if after:
                rows = [r for r in rows
                        if (r["submitted_at"] >= after if self.inclusive_after
                            else r["submitted_at"] > after)]
            return Reply(rows[:int((params or {}).get("limit") or PAGE)])
        return Reply({}, status=404)


def _broker(session):
    return AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24, session=session)


def _reconcile(session, slot="paper"):
    return LC.reconcile(_broker(session), {"slot": slot, "holdings": {}})


class TheWholeOrderHistoryIsRead(unittest.TestCase):
    """§1. The paper slot refused a history it had read in full, and Monday's rebalance with it."""

    def test_DONS_OWN_510_IS_READ_AND_NOT_REFUSED(self):
        # THE EXACT SHAPE OF RUN #25: 510 orders, which is 500 + 10 across two pages.
        s = RecordedOrders([order(i) for i in range(510)])
        rec = _reconcile(s)
        self.assertEqual(rec["order_read"], "ok", rec.get("reason"))
        self.assertFalse(rec["truncated"], rec.get("reason"))
        self.assertEqual(s.pages_served, 2)
        # AND EVERY ONE OF THEM WAS COUNTED: 510 of this slot's own orders.
        self.assertEqual(rec["n_orders"], 510)

    def test_the_510_IS_NOT_NESTING_AND_NO_nested_PARAMETER_IS_SENT(self):
        # The brief asks whether nesting explains 510 > the 500 requested. It does not: the
        # request carries status/limit/direction/after and nothing else, and 510 is the TOTAL
        # across two pages rather than one page's length.
        s = RecordedOrders([order(i) for i in range(510)])
        _reconcile(s)
        for p in s.params_seen:
            self.assertNotIn("nested", p)
            self.assertEqual(int(p["limit"]), PAGE)
        self.assertEqual([int(p["limit"]) for p in s.params_seen], [PAGE, PAGE])

    def test_EXACTLY_500_then_an_empty_page_is_complete(self):
        # The boundary the brief names. A full page is not evidence of more; an empty NEXT page
        # is evidence of no more.
        s = RecordedOrders([order(i) for i in range(PAGE)])
        rec = _reconcile(s)
        self.assertEqual(rec["order_read"], "ok", rec.get("reason"))
        self.assertEqual(rec["n_orders"], PAGE)
        self.assertEqual(s.pages_served, 2)

    def test_a_FAILED_second_page_still_REFUSES(self):
        # The refusal is kept for a read that is genuinely incomplete -- the brief's own rule.
        s = RecordedOrders([order(i) for i in range(510)], fail_after_page=1)
        rec = _reconcile(s)
        self.assertEqual(rec["order_read"], "failed")
        self.assertIn("could not be read", rec["reason"])

    def test_pages_that_OVERLAP_are_deduped_rather_than_double_counted(self):
        s = RecordedOrders([order(i) for i in range(510)], inclusive_after=True)
        rec = _reconcile(s)
        self.assertEqual(rec["order_read"], "ok", rec.get("reason"))
        self.assertEqual(rec["n_orders"], 510)

    def test_A_TIE_STRADDLING_THE_PAGE_BOUNDARY_LOSES_NOTHING(self):
        # **THE DEFECT THIS TEST FOUND.** The tie guard counted twins WITHIN a page, and the
        # dangerous twin is on the NEXT one: with `after` exclusive, advancing past the last
        # stamp skipped it. Measured before the fix: 501 submitted, 500 returned, `ok=True`,
        # `truncated=False` -- a silently under-counted holding, which is the precise harm the
        # pager's refusal exists to prevent.
        rows = ([order(i) for i in range(PAGE - 1)]
                + [order(PAGE - 1, "2026-10-02T00:00:00Z"),
                   order(PAGE, "2026-10-02T00:00:00Z")])
        s = RecordedOrders(rows)
        rec = _reconcile(s)
        self.assertEqual(rec["order_read"], "ok", rec.get("reason"))
        self.assertEqual(rec["n_orders"], PAGE + 1)

    def test_a_MIXED_UTC_OFFSET_page_still_loses_nothing(self):
        """A stamp whose offset is not `Z` must not disturb the cursor.

        **THIS TEST IS NARROWER THAN THE ONE I SET OUT TO WRITE, AND THE CORRECTION IS THE
        USEFUL PART.** I had claimed the back-off must come from ROW ORDER rather than from a
        sort of the stamps, because a mixed offset could make a sort SKIP rows. It cannot: the
        request carries `direction=asc`, so a stamp earlier in the page is at an instant no
        later than the last one, and a sort can therefore only ever resume EARLIER -- which
        re-reads more and skips nothing. Mutating the implementation to `sorted({...})` passes
        every case here, which is how that claim was retired instead of shipped.

        What is left is still worth pinning: `2026-10-02T19:00:00+05:00` is 14:00Z, so this
        page is ascending in TIME while not ascending as STRINGS, and the read completes with
        nothing lost and nothing doubled. Taken on `paged_orders` directly, because the fixture
        has to compare stamps as instants -- which is what Alpaca does and what a
        string-comparing stub cannot.
        """
        tie = "2026-10-02T16:00:00Z"
        rows = [order(0, "2026-10-01T09:00:00Z"),
                order(1, "2026-10-02T19:00:00+05:00"),      # 14:00Z -- earlier, sorts higher
                order(2, tie), order(3, tie)]

        def fetch(params):
            after = params.get("after")
            avail = rows
            if after:
                cut = _dt.datetime.fromisoformat(after.replace("Z", "+00:00"))
                avail = [r for r in rows
                         if _dt.datetime.fromisoformat(
                             r["submitted_at"].replace("Z", "+00:00")) > cut]
            return {"ok": True, "data": avail[:int(params["limit"])]}

        got = SETTLE.paged_orders(fetch, page_limit=3)
        self.assertTrue(got["ok"])
        self.assertFalse(got["truncated"], got["reason"])
        self.assertEqual(len(got["data"]), 4, "an order sharing the boundary stamp was lost")
        self.assertEqual(len({o["id"] for o in got["data"]}), 4, "an order was counted twice")

    def test_a_whole_page_sharing_ONE_timestamp_still_refuses(self):
        # The one case that genuinely cannot be resumed from: there is no earlier point to
        # back off to, so skipping is the only way forward and the read refuses instead.
        #
        # **A CONTROL, which is why it asserts the SHARED wording and not the new wording.**
        # The old cursor refused any tie on the last timestamp; the new one backs off to the
        # previous distinct stamp and refuses only when there is none. This case is the
        # intersection, so it must pass on both trees -- and asserting item 78's own sentence
        # here would have turned a control into a second copy of the implementation.
        rows = [order(i, "2026-10-02T00:00:00Z") for i in range(600)]
        rec = _reconcile(RecordedOrders(rows))
        self.assertEqual(rec["order_read"], "truncated")
        self.assertIn("submission timestamp", rec["reason"])

    def test_an_UNPAGED_client_keeps_the_full_page_refusal(self):
        # The length check still means what it says where it is still true: a client that
        # cannot page gets one page, and a full one may be hiding more.
        class OnePage:
            def orders(self, status="all", limit=100):
                return [order(i) for i in range(PAGE)]

            def positions(self):
                return []
        rec = LC.reconcile(OnePage(), {"slot": "paper", "holdings": {}})
        self.assertEqual(rec["order_read"], "truncated")
        # The shared wording, for the same reason as the case above: this refusal is the half
        # item 78 KEPT, so the control has to be satisfiable by both trees.
        self.assertIn("FULL page", rec["reason"])


class TheFilterBlocksValuesAndNeverNames(unittest.TestCase):
    """§2. The privacy filter silently withheld the alert that the slot was broken."""

    #: The message run #25 composed and did not post, verbatim from Don's own warning.
    RUN25 = ("the broker returned a FULL page of 510 orders, so older fills may be outside "
             "the window and this slot's holdings cannot be totalled reliably")

    def test_RUN_25s_OWN_WARNING_POSTS(self):
        # The rule that fired was `return_violations`, matching the substring "return" inside
        # "returned". Not the `paper_client_absent` line the brief guessed at -- that one is
        # clean on both trees, which `test_a_variable_NAME_is_never_blocked` pins.
        r = AR.safe_body(self.RUN25, env={}, check_returns=True)
        self.assertFalse(r["blocked"], r["why"])
        self.assertEqual(r["text"], self.RUN25)

    def test_the_cleared_line_and_item_77s_line_both_post(self):
        for t in ("slot paper: reconcile_truncated has cleared",
                  "slot 1 has keys but no ALPACA_ACCOUNT_1_LIVE_PCT, so the slot is at an "
                  "ASSUMED 0% while its own record still holds position(s); nothing will "
                  "trade until it is set."):
            r = AR.safe_body(t, env={}, check_returns=True)
            self.assertFalse(r["blocked"], (t[:40], r["why"]))

    def test_a_variable_NAME_is_never_blocked(self):
        t = ("ALPACA_PAPER_KEY_ID and ALPACA_PAPER_SECRET_KEY are not both set. The paper "
             "books will NOT fall back to any other Alpaca credential.")
        r = AR.safe_body(t, env={"ALPACA_PAPER_KEY_ID": "PKREALKEY1234567"},
                         check_returns=True)
        self.assertFalse(r["blocked"], r["why"])
        self.assertIn("ALPACA_PAPER_KEY_ID", r["text"])

    def test_a_REAL_return_claim_is_still_blocked(self):
        # THE CONTROL. Word boundaries must not become "anything goes".
        for t in ("the book returns 5.2% this quarter",
                  "unrealized P&L is +$412",
                  "the excess vs SPY is +1.1pp",
                  "drawdown of 12% since inception"):
            r = AR.safe_body(t, env={}, check_returns=True)
            self.assertTrue(r["blocked"], "not blocked: %r" % t)

    def test_secret_VALUES_are_redacted_in_place_rather_than_blocking_the_message(self):
        env = {"DISCORD_WEBHOOK_URL":
               "https://discord.com/api/webhooks/123456789/AbCdEf-ghIJklMNopQRstUV"}
        cases = [
            ("posting to %s failed" % env["DISCORD_WEBHOOK_URL"], "a configured webhook"),
            ("the broker rejected key PKABCDEF123456789 for this slot", "a key SHAPE"),
            ("auth failed for aB3dEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGh", "an opaque run"),
            ("Authorization: Bearer abcDEF123456ghiJKL789mno", "a bearer token"),
        ]
        for text, what in cases:
            r = AR.safe_body(text, env=env, check_returns=True)
            self.assertFalse(r["blocked"], (what, r["why"]))
            self.assertTrue(r["scrubbed"], what)
            self.assertIn(AR.REDACTED, r["text"], what)
            # AND THE MESSAGE SURVIVES: a redaction keeps the words either side of it.
            self.assertGreater(len(r["text"].replace(AR.REDACTED, "")), 10, what)

    def test_the_shape_check_never_reports_the_value_it_found(self):
        spans = AR.shape_spans("key PKABCDEF123456789 here")
        self.assertTrue(spans)
        for _s, _e, why in spans:
            self.assertNotIn("PKABCDEF123456789", why)


class AZeroPercentSlotNeedsNoPrices(unittest.TestCase):
    """§3. Don's IRA is at 0%, paused, holds nothing -- and alerted on 31 unpriced names."""

    BOOK = {"ok": True, "formed_on": "2026-11-01",
            "positions": [{"ticker": "AAPL", "status": "held", "weight": 0.5},
                          {"ticker": "BBB", "status": "held", "weight": 0.5}]}

    def test_a_0pct_slot_holding_nothing_would_trade_NOTHING(self):
        self.assertEqual(LS.tradable_names(self.BOOK, {}, 0.0), [])

    def test_and_therefore_preflight_does_not_refuse_on_prices(self):
        pf = LS.preflight(book=self.BOOK, equity=10000, marks={}, slot_record={}, pct=0.0,
                          broker_positions=[])
        self.assertTrue(pf["ok"], pf["problems"])

    def test_a_0pct_slot_that_DOES_hold_needs_only_ITS_OWN_names(self):
        # The wind-down tightening: an exit must not be blocked by a quote for a book name
        # this slot does not own.
        self.assertEqual(LS.tradable_names(self.BOOK, {"BBB": 3.0}, 0.0), ["BBB"])

    def test_a_POSITIVE_percentage_is_unchanged(self):
        self.assertEqual(sorted(LS.tradable_names(self.BOOK, {}, 5.0)), ["AAPL", "BBB"])
        # ... and an unstated percentage keeps every pre-item-78 caller as it was.
        self.assertEqual(sorted(LS.tradable_names(self.BOOK, {})), ["AAPL", "BBB"])

    def test_an_unpriced_cycle_is_TAGGED_so_the_caller_need_not_read_the_prose(self):
        pf = LS.preflight(book=self.BOOK, equity=10000, marks={}, slot_record={}, pct=5.0,
                          broker_positions=[])
        self.assertFalse(pf["ok"])
        self.assertTrue(pf["price_only"])
        self.assertEqual(sorted(pf["unpriced"]), ["AAPL", "BBB"])

    def test_price_only_is_FALSE_when_anything_else_is_also_wrong(self):
        # So the softening below can never swallow a real defect.
        pf = LS.preflight(book={"ok": False, "reason": "unreadable"}, equity=10000, marks={},
                          slot_record={}, pct=5.0, broker_positions=[])
        self.assertFalse(pf["price_only"])

    def test_the_caller_stays_quiet_OUTSIDE_the_window_and_alerts_INSIDE_it(self):
        src = io.open(os.path.join(REPO, "valuation", "edge", "live_cycle.py"),
                      encoding="utf-8").read()
        self.assertIn('_quiet_price_gap = bool(pf.get("price_only")) and not session_ok', src)
        # AND THE REFUSAL IS UNCHANGED EITHER WAY: the softening sits on the alert, never on
        # `out["reason"]` or on whether anything is sent.
        head = src.split("_quiet_price_gap", 1)[1][:900]
        self.assertIn('out["reason"] = pf["reason"]', head)


class AClearedLineNeedsEvidence(unittest.TestCase):
    """§4. The watch declared two slot conditions cleared without evaluating either."""

    OPEN = {"1": {"preflight_failed|no usable price": "2026-10-20"},
            "paper": {"reconcile_truncated|a FULL page": "2026-10-20"}}

    def _root(self, conditions):
        root = tempfile.mkdtemp()
        p = LN.state_path(root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"schema": LN.SCHEMA, "announced": [], "conditions": conditions}, fh)
        return root

    def test_a_WATCH_ONLY_run_says_nothing_about_a_slot_condition(self):
        root = self._root(self.OPEN)
        try:
            watch = [{"kind": "rebalance_overdue", "slot": "-", "reason": "overdue"}]
            p = LN.pending(watch, root, evaluated={"-"})
            self.assertEqual(p["cleared"], [], p["cleared"])
        finally:
            __import__("shutil").rmtree(root, True)

    def test_and_the_record_KEEPS_them_so_they_are_not_re_announced_as_new(self):
        # Without this the pair would ping-pong: cleared by the watch, new on the next cycle.
        root = self._root(self.OPEN)
        try:
            p = LN.pending([{"kind": "rebalance_overdue", "slot": "-", "reason": "o"}],
                           root, evaluated={"-"})
            self.assertIn("preflight_failed|no usable price", p["by_slot"].get("1") or {})
            self.assertIn("reconcile_truncated|a FULL page", p["by_slot"].get("paper") or {})
        finally:
            __import__("shutil").rmtree(root, True)

    def test_an_UNSTATED_scope_clears_nothing(self):
        # **THIS IS THE BRIEF'S WATCH-ONLY CASE IN ITS BEHAVIOUR-GRADE FORM.** The two tests
        # above name the scope explicitly, so on the pre-item-78 tree they fail on the keyword
        # rather than on the behaviour -- which proves the test is new, not that the old code
        # was wrong. The old watch door passed no scope at all, so this call is exactly what it
        # did: on that tree it cleared both slot conditions, and here it clears neither.
        root = self._root(self.OPEN)
        try:
            self.assertEqual(LN.pending([], root)["cleared"], [])
        finally:
            __import__("shutil").rmtree(root, True)

    def test_a_run_that_DID_evaluate_still_clears(self):
        # THE POSITIVE CONTROL. A fix that simply stopped clearing would satisfy the three
        # above and break the good half of Don's noise rule.
        root = self._root(self.OPEN)
        try:
            still = [{"kind": "reconcile_truncated", "slot": "paper", "reason": "a FULL page"}]
            p = LN.pending(still, root, evaluated={"1", "paper", "-"})
            self.assertEqual([(c["slot"], c["was"]) for c in p["cleared"]],
                             [("1", "preflight_failed")])
        finally:
            __import__("shutil").rmtree(root, True)

    def test_BOTH_callers_declare_what_they_evaluated(self):
        import ast
        for rel, want in (("valuation/edge/live_cycle.py", "_evaluated"),
                          ("valuation/saas/app_saas.py", "evaluated")):
            src = io.open(os.path.join(REPO, rel), encoding="utf-8").read()
            tree = ast.parse(src)
            # **SCOPED TO `live_notify`'s OWN DOOR, AND THAT IS NOT FUSSINESS.** The first cut
            # matched any call named `announce` and fired on `app_saas`'s unrelated
            # `_fn.announce(rows_by_book, refusals, ...)` -- the fleet notifier, a different
            # function with a different signature. The wrong-object family: a check that reads
            # the right word on the wrong object.
            calls = [n for n in ast.walk(tree)
                     if isinstance(n, ast.Call)
                     and getattr(n.func, "attr", None) == "announce"
                     and getattr(getattr(n.func, "value", None), "id", None)
                     in ("LN", "live_notify")]
            self.assertTrue(calls, "%s: no live_notify.announce call found at all" % rel)
            for c in calls:
                self.assertIn("evaluated", [k.arg for k in c.keywords],
                              "%s calls announce without declaring its scope" % rel)
            self.assertIn(want, src)


class APermanentGapIsAnnouncedOnce(unittest.TestCase):
    """§5. Eleven missed record days that cannot be repaired were reminding Don daily."""

    DAYS = (["2026-08-%02d" % d for d in (3, 4, 5, 7, 10, 11, 12, 14)]
            + ["2026-09-%02d" % d for d in (2, 3, 8)])

    def _detail(self, days):
        return {"recording_ok": False,
                "per_vintage_recording": [{"status": "OPEN", "missing_dates": list(days)}]}

    def _say(self, root, days):
        alerts = RW.record_status(detail=self._detail(days))["alerts"]
        p = LN.pending(alerts, root, evaluated={"-"})
        st = LN._read(root)
        st["conditions"] = p["by_slot"]
        LN._write(st, root)
        return [a["kind"] for a in p["conditions"]] + [a["kind"] for a in p["reminders"]]

    def test_said_once_then_silent_however_many_cycles_a_day(self):
        root = tempfile.mkdtemp()
        try:
            first = self._say(root, self.DAYS)
            self.assertIn("record_row_missing", first)
            self.assertIn("recording_not_ok", first)
            for _ in range(4):
                self.assertEqual(self._say(root, self.DAYS), [])
        finally:
            __import__("shutil").rmtree(root, True)

    def test_a_NEW_missing_day_alerts_on_the_day_it_happens(self):
        root = tempfile.mkdtemp()
        try:
            self._say(root, self.DAYS)
            self.assertEqual(self._say(root, self.DAYS), [])
            again = self._say(root, self.DAYS + ["2026-10-22"])
            self.assertIn("record_row_missing", again)
            # AND `recording_not_ok` RE-ANNOUNCES because its CAUSE changed -- which only
            # works because the count is in its reason.
            self.assertIn("recording_not_ok", again)
            self.assertEqual(self._say(root, self.DAYS + ["2026-10-22"]), [])
        finally:
            __import__("shutil").rmtree(root, True)

    def test_the_exemption_is_declared_and_narrow(self):
        self.assertEqual(set(AR.NO_DAILY_REMINDER),
                         {"record_row_missing", "recording_not_ok"})
        # EVERY OTHER CONDITION STILL REMINDS DAILY -- the exemption must not widen by default.
        root = tempfile.mkdtemp()
        try:
            a = [{"kind": "preflight_failed", "slot": "1", "reason": "broken"}]
            LN.pending(a, root, evaluated={"1"})
            st = LN._read(root)
            st["conditions"] = {"1": {LN.condition_sig(a[0]): "2026-10-01"}}
            LN._write(st, root)
            p = LN.pending(a, root, evaluated={"1"}, now="2026-10-22")
            self.assertEqual([x["kind"] for x in p["reminders"]], ["preflight_failed"])
        finally:
            __import__("shutil").rmtree(root, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
