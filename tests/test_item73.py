# -*- coding: utf-8 -*-
"""ITEM 73 — Don's rulings of 2026-10-18 on how a partial buy-in is spread, and what waits.

His six words, in order:

  1. **Buys are spread PROPORTIONALLY, never filled stock by stock.** Scale every buy by the
     same fraction `f = min(1, spendable / total buy cost)`. A name whose scaled order falls
     under `min_order_value` is skipped and stays in the gap.
  2. **The shortfall stays OPEN until it is filled or the next event replaces it**, measured
     against *that event's own per-name targets, frozen when the event opened* — NOT re-derived
     from today's equity, *"otherwise this becomes daily drift trading, which Don's three-events
     rule forbids."*
  3. **No cash budget or cap.**
  4. **One universal `LIVE_MIN_TOPUP`, default $250**, applying to every live slot and the paper
     slot alike; malformed refuses and alerts as `LIVE_PCT` does; the first fill of a new event
     is not held back by it.
  5. **A declared "waiting for cash" outcome** — the event stays open, nothing is sent, Don is
     alerted once, it does not re-alert every cycle and does not burn the ceiling.
  6. No daily re-sizing when prices move between events.

**FROZEN TARGETS FIX SOMETHING WIDER THAN THE CASH CASE, AND THAT IS THE FINDING HERE.** Before
item 73 every remainder cycle re-derived targets from today's equity and today's marks. So a
price move between two cycles of ONE rebalance changed the target and the slot traded the
difference — drift trading arriving through the back door of a remainder cycle, which is exactly
what Don's ruling (2) forbids and which nothing was watching for.

Every HTTP reply is a recorded fixture driving the shipped `AlpacaPaperBroker`. Nothing touches a
network and nothing places a real order.
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

import tests.test_item63 as T63                        # noqa: E402
import tests.test_item67 as T67                        # noqa: E402
from valuation.edge import live_cycle as LC            # noqa: E402
from valuation.edge import live_slots as LS            # noqa: E402
from valuation.edge import settlement as SETTLE        # noqa: E402

#: An account with plenty, and one with almost nothing. `non_marginable_buying_power` is the
#: field the budget reads -- item 67's finding, unchanged here.
RICH = {"id": "acct-1", "account_number": "PA1", "equity": "1000", "cash": "1000",
        "buying_power": "1000", "non_marginable_buying_power": "1000",
        "status": "ACTIVE", "multiplier": "1"}
BROKE = {"id": "acct-1", "account_number": "PA1", "equity": "1000", "cash": "0",
         "buying_power": "0", "non_marginable_buying_power": "0",
         "status": "ACTIVE", "multiplier": "1"}


def _acct(**kw):
    return dict(RICH, **kw)


def _mid(marks, ticker, default=1.0) -> float:
    """The mid out of `{ticker: {"mid": price}}`.

    **THE SHAPE IS NESTED AND I ASSUMED FLAT TWICE**, which cost one vacuous test (a
    price-doubling fixture that doubled nothing) and one `TypeError`. One reader for the shape,
    so neither can come back.
    """
    row = (marks or {}).get(str(ticker).upper()) or {}
    if isinstance(row, dict):
        v = row.get("mid")
    else:
        v = row
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if f > 0 else default


def _doubled(marks) -> dict:
    """`marks` with every mid doubled, preserving the nested shape."""
    out = {}
    for k, v in (marks or {}).items():
        out[k] = (dict(v, mid=float(v["mid"]) * 2.0)
                  if isinstance(v, dict) and v.get("mid") is not None else v)
    return out


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def cycle(self, *, account=None, day=None, equity=1000.0, book=None, sess=None,
              min_topup=None, marks=None):
        sess = sess if sess is not None else T67.Recorded(
            account_fields=(account or RICH))
        real = LC._stamp
        try:
            if day:
                LC._stamp = (lambda d=day: "%sT14:40:00Z" % d)
            got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED,
                              book=(book or T63.BOOK), client=T67.broker(sess),
                              equity=equity, account=(account or RICH),
                              marks=(marks or T63.MARKS), root=self.root, send=True,
                              min_topup=min_topup)
        finally:
            LC._stamp = real
        return got, sess

    def state(self):
        return LC.read_state(LC.PAPER_SLOT, self.root)


# =============================================================================================
class TheALLOCATORIsProportional(unittest.TestCase):
    """(1) — and the worked example is Don's own, checked to the cent."""

    BUYS = [{"ticker": "AAA", "side": "buy", "qty": 10.0, "limit_price": 100.0},
            {"ticker": "BBB", "side": "buy", "qty": 10.0, "limit_price": 100.0},
            {"ticker": "CCC", "side": "buy", "qty": 1.0, "limit_price": 2.0}]

    def test_DONS_WORKED_EXAMPLE__800_dollars_against_a_2002_dollar_gap(self):
        got = SETTLE.allocate_buys(self.BUYS, 800.0)
        self.assertAlmostEqual(got["fraction"], 0.3996, places=6)
        self.assertEqual(len(got["orders"]), 2)
        for o in got["orders"]:
            self.assertAlmostEqual(float(o["qty"]), 3.996004, places=6)
            self.assertAlmostEqual(float(o["qty"]) * float(o["limit_price"]), 399.6, places=2)
        self.assertAlmostEqual(got["total_cost"], 2002.0, places=2)

    def test_EVERY_NAME_IS_SCALED_BY_THE_SAME_FRACTION__never_filled_one_by_one(self):
        """The whole content of the ruling. Filling stock by stock would buy AAA and BBB in
        full and leave CCC at nothing; proportional buys 40% of each.

        Compared to SIX places, not nine: the allocator rounds the quantity it sends, because a
        fifteen-digit fractional quantity is not a thing to put on an order. `3.996003996`
        against a sent `3.996004` is that rounding and not a scaling error -- my first cut
        asserted nine places and caught its own tolerance rather than a defect.
        """
        got = SETTLE.allocate_buys(self.BUYS, 800.0)
        f = got["fraction"]
        for o in got["orders"]:
            src = next(b for b in self.BUYS if b["ticker"] == o["ticker"])
            self.assertAlmostEqual(float(o["qty"]), float(src["qty"]) * f, places=6)
        # AND THE RATIO BETWEEN TWO NAMES IS EXACT, which is the property "the same fraction"
        # really means and which rounding cannot disturb at these sizes.
        a, b = got["orders"][0], got["orders"][1]
        want = (float(next(x for x in self.BUYS if x["ticker"] == a["ticker"])["qty"])
                / float(next(x for x in self.BUYS if x["ticker"] == b["ticker"])["qty"]))
        self.assertAlmostEqual(float(a["qty"]) / float(b["qty"]), want, places=6)

    def test_a_name_UNDER_min_order_value_is_SKIPPED_and_STAYS_IN_THE_GAP(self):
        got = SETTLE.allocate_buys(self.BUYS, 800.0)
        skipped = [o["ticker"] for o in got["skipped"]]
        self.assertEqual(skipped, ["CCC"])
        self.assertIn("under the", got["skipped"][0]["why"])
        # IT IS STILL OWED. The shortfall is the whole untransmitted gap, skipped names and all.
        self.assertAlmostEqual(got["shortfall"], 2002.0 - got["fillable_cost"], places=6)
        self.assertGreater(got["shortfall"], 1200.0)

    def test_enough_cash_buys_EVERYTHING_at_fraction_one(self):
        got = SETTLE.allocate_buys(self.BUYS, 5000.0)
        self.assertEqual(got["fraction"], 1.0)
        self.assertEqual(len(got["orders"]), 3)
        self.assertEqual(got["skipped"], [])
        self.assertAlmostEqual(got["shortfall"], 0.0, places=6)

    def test_NO_SPENDABLE_FIGURE_buys_nothing_rather_than_guessing(self):
        got = SETTLE.allocate_buys(self.BUYS, None)
        self.assertEqual(got["orders"], [])
        self.assertEqual(got["fraction"], 0.0)

    def test_THERE_IS_NO_CASH_CAP__ruling_3(self):
        """Don: *"No cash budget or cap."* The only bound is the broker's own no-borrow figure,
        so a large spendable spends it all. A cap would be a number nobody chose."""
        import inspect
        src = inspect.getsource(SETTLE.allocate_buys)
        for word in ("CAP", "max_spend", "budget_cap", "MAX_BUY"):
            self.assertNotIn(word, src, "a cash cap appeared in the allocator")
        got = SETTLE.allocate_buys(self.BUYS, 1e9)
        self.assertEqual(got["fraction"], 1.0)


# =============================================================================================
class TheTopUpThreshold(unittest.TestCase):
    """(4) — ONE universal variable, default $250, malformed refuses."""

    def test_the_default_is_250_and_it_says_it_is_a_default(self):
        got = SETTLE.min_topup({})
        self.assertTrue(got["ok"])
        self.assertEqual(got["amount"], 250.0)
        self.assertIs(got["stated"], False)

    def test_a_stated_value_is_honoured_and_says_it_was_stated(self):
        got = SETTLE.min_topup({"LIVE_MIN_TOPUP": "500"})
        self.assertEqual(got["amount"], 500.0)
        self.assertIs(got["stated"], True)

    def test_MALFORMED_REFUSES__as_LIVE_PCT_does(self):
        for bad in ("abc", "-5", "nan", "inf", "", "  "):
            got = SETTLE.min_topup({"LIVE_MIN_TOPUP": bad})
            if bad.strip() == "":
                self.assertTrue(got["ok"], "blank should fall back to the default")
                continue
            self.assertFalse(got["ok"], "%r was accepted" % bad)
            self.assertIsNone(got["amount"],
                              "a refused threshold must not also carry a number")

    def test_there_is_ONE_variable_and_NO_per_account_form(self):
        """Don, 2026-10-18: *"There is no per-account variable; Don chose one universal
        setting."* A `LIVE_MIN_TOPUP_1` would be a second definition of the same rule."""
        import inspect
        src = inspect.getsource(SETTLE)
        self.assertEqual(src.count('"LIVE_MIN_TOPUP"'), 1)
        self.assertNotIn("LIVE_MIN_TOPUP_", src)
        self.assertEqual(SETTLE.MIN_TOPUP_VAR, "LIVE_MIN_TOPUP")


# =============================================================================================
class ThreeOfDonsSixCasesEndToEnd(_Tmp):
    """(1), (4) and (5) through the real cycle rather than through the allocator alone."""

    def test_A_PARTIAL_CASH_BUY_IN_IS_SPREAD_PROPORTIONALLY(self):
        """Don's case one. A quarter of the money buys a quarter of every name."""
        got, sess = self.cycle(account=_acct(cash="250", buying_power="250",
                                             non_marginable_buying_power="250"))
        alloc = got.get("allocation") or {}
        self.assertAlmostEqual(alloc.get("fraction") or 0, 0.25, places=4)
        sent = [(o["symbol"], float(o["qty"])) for o in sess.placed]
        self.assertTrue(sent, "nothing was sent at a quarter of the gap")
        spend = sum(float(o["qty"]) * float(o["limit_price"]) for o in sess.placed)
        self.assertLessEqual(spend, 250.0 + 1e-6,
                             "it planned to spend %.2f of a 250 budget" % spend)
        # PROPORTIONAL, not one-by-one: every name sent, each at a quarter.
        planned = {o["ticker"]: float(o["qty"]) for o in got["orders"]
                   if str(o["side"]).lower() == "buy"}
        for sym, q in sent:
            self.assertAlmostEqual(q, planned[sym] * 0.25, places=6)

    def test_A_DEPOSIT_UNDER_THE_THRESHOLD_WAITS(self):
        """Don's case three, and the event stays open while it waits."""
        # First fill goes in at a quarter -- the first fill of an event is exempt.
        self.cycle(account=_acct(cash="250", buying_power="250",
                                 non_marginable_buying_power="250"), day="2026-10-22")
        # Then a trickle: $40 against a $250 threshold.
        got, sess = self.cycle(account=_acct(cash="40", buying_power="40",
                                             non_marginable_buying_power="40"),
                               day="2026-10-23")
        self.assertEqual(got["send_outcome"], LC.SEND_TOPUP_TOO_SMALL, got.get("reason"))
        self.assertEqual(sess.placed, [], "a sub-threshold trickle was transmitted")
        self.assertIn("minimum top-up", got["reason"])
        st = self.state()
        self.assertTrue(st.get("open_event"), "the gap stopped being open")
        self.assertTrue(st.get("cash_wait"))

    def test_WAITING_FOR_CASH_ALERTS_ONCE_AND_DOES_NOT_BURN_THE_CEILING(self):
        """Don's case five, in full: the event stays open, nothing is sent, one alert ever, and
        the no-progress ceiling is not spent -- five of those would stop the event."""
        seen, got = [], None
        for d in ("2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28",
                  "2026-10-29"):
            got, sess = self.cycle(account=BROKE, day=d)
            seen.extend(a["kind"] for a in got["alerts"])
            self.assertEqual(sess.placed, [], "a buy went out with no cash, on %s" % d)
        self.assertEqual(seen.count("waiting_for_cash"), 1,
                         "one post when it starts and nothing after: %r" % (seen,))
        self.assertNotIn("event_attempts_exhausted", seen,
                         "six days of waiting for a deposit stopped the event")
        self.assertFalse(got.get("attempt_days"),
                         "a cash wait spent ceiling days: %r" % (got.get("attempt_days"),))
        self.assertEqual(got["send_outcome"], LC.SEND_WAITING_CASH)

    def test_the_FIRST_FILL_of_an_event_is_NOT_held_back_by_the_threshold(self):
        """Don: *"The first fill of a new event is not held back by the threshold."* A rebalance
        must go in on the day it arrives whatever its size."""
        got, sess = self.cycle(account=_acct(cash="40", buying_power="40",
                                             non_marginable_buying_power="40"))
        self.assertTrue(got.get("is_first_fill_of_event"))
        self.assertTrue(sess.placed, "the first fill of a rebalance was held back")

    def test_a_MALFORMED_threshold_refuses_the_cycle_and_alerts(self):
        got, sess = self.cycle(min_topup=SETTLE.min_topup({"LIVE_MIN_TOPUP": "abc"}))
        self.assertEqual(got["send_outcome"], LC.SEND_WITHHELD)
        self.assertEqual(sess.placed, [])
        self.assertIn("min_topup_invalid", [a["kind"] for a in got["alerts"]])


# =============================================================================================
class TheTargetsAreFROZENWhenTheEventOpens(_Tmp):
    """(2) and (6) — the ruling that stops this becoming daily drift trading."""

    def test_NO_DAILY_RE_SIZING_WHEN_PRICES_MOVE_BETWEEN_EVENTS(self):
        """Don's case six, and the defect it closes is wider than the cash case.

        Before item 73 every remainder cycle re-derived targets from today's equity and today's
        marks, so a price move between two cycles of ONE rebalance changed the target and the
        slot traded the difference. Here the marks DOUBLE between two cycles of the same event
        and the frozen targets must not move.
        """
        self.cycle(account=_acct(cash="250", buying_power="250",
                                 non_marginable_buying_power="250"), day="2026-10-22")
        frozen = dict(self.state().get("frozen_targets") or {})
        self.assertTrue(frozen, "nothing was frozen when the event opened")
        key = sorted(frozen)[0]
        first = dict(frozen[key])

        # **`MARKS` IS `{ticker: {"mid": price}}`, NOT A FLAT MAP, AND MY FIRST CUT ASSUMED
        # FLAT.** `isinstance(v, (int, float))` was False for every entry, so the "doubled"
        # marks were the original marks and this test passed while changing nothing -- the
        # vacuous-fixture family. `_doubled` is asserted to have actually moved below.
        doubled = _doubled(T63.MARKS)
        self.assertNotEqual(doubled, T63.MARKS, "the fixture did not move the prices")
        self.assertAlmostEqual(_mid(doubled, "AAPL"), 2.0 * _mid(T63.MARKS, "AAPL"))
        self.cycle(account=_acct(cash="250", buying_power="250",
                                 non_marginable_buying_power="250"),
                   day="2026-10-23", marks=doubled, equity=2000.0)
        after = dict((self.state().get("frozen_targets") or {}).get(key) or {})
        self.assertEqual(first, after,
                         "the targets moved when the marks did -- that is drift trading "
                         "arriving through a remainder cycle")

    def test_the_second_cycle_REPORTS_that_its_targets_are_frozen(self):
        self.cycle(account=_acct(cash="250", buying_power="250",
                                 non_marginable_buying_power="250"), day="2026-10-22")
        got, _s = self.cycle(account=_acct(cash="250", buying_power="250",
                                           non_marginable_buying_power="250"),
                             day="2026-10-23")
        self.assertIs(got.get("targets_are_frozen"), True)
        self.assertTrue(got.get("targets_frozen_for"))

    def test_A_LATER_DEPOSIT_TOPS_UP_TO_THE_FROZEN_TARGETS_AND_NO_FURTHER(self):
        """Don's case two. The gap is measured against the event's own frozen targets, so a
        deposit large enough to finish the job finishes it and stops.

        **THE FILL HAS TO BE REPLAYED OR THIS TEST CANNOT TELL TWO THINGS APART.** My first cut
        ran three cycles on a fixture whose position list never changes, so every cycle saw the
        same gap and bought again -- and the assertion "it kept buying past the targets" was
        satisfied by "the fixture never reported a fill", which is a statement about the
        fixture. So the third cycle is driven with the broker reporting the filled quantities,
        which is the state a real account would be in.
        """
        self.cycle(account=_acct(cash="250", buying_power="250",
                                 non_marginable_buying_power="250"), day="2026-10-22")
        rich = _acct(cash="100000", buying_power="100000",
                     non_marginable_buying_power="100000")
        got, sess = self.cycle(account=rich, day="2026-10-23")
        self.assertTrue(sess.placed, "the deposit bought nothing")

        # Everything ordered across both cycles, as FILLED positions.
        filled = {}
        for o in sess.placed:
            filled[o["symbol"]] = filled.get(o["symbol"], 0.0) + float(o["qty"])
        frozen = dict((self.state().get("frozen_targets") or {}))
        key = sorted(frozen)[0]
        for tkr, val in (frozen[key] or {}).items():
            filled[tkr] = max(filled.get(tkr, 0.0), float(val) / _mid(T63.MARKS, tkr))
        done = T67.Recorded(
            account_fields=rich,
            positions=[{"symbol": t, "qty": "%.6f" % q,
                        "avg_entry_price": "%.2f" % _mid(T63.MARKS, t),
                        "side": "long"} for t, q in sorted(filled.items())],
            orders=[{"id": "f-%s" % t, "client_order_id":
                     LC.client_order_id(LC.PAPER_SLOT, key, t),
                     "symbol": t, "side": "buy", "qty": "%.6f" % q,
                     "filled_qty": "%.6f" % q, "status": "filled",
                     "limit_price": "%.2f" % _mid(T63.MARKS, t),
                     "filled_avg_price": "%.2f" % _mid(T63.MARKS, t),
                     "submitted_at": "2026-10-23T14:40:00Z"}
                    for t, q in sorted(filled.items())])
        got3, sess3 = self.cycle(account=rich, sess=done, day="2026-10-26")
        self.assertEqual(sess3.placed, [],
                         "it kept buying past the frozen targets: %r" % (sess3.placed,))

    def test_A_NEW_EVENT_REPLACES_AN_OPEN_GAP(self):
        """Don's case four. The frozen targets belong to the event; a new book is a new event
        with its own, and the old gap is not carried into it."""
        self.cycle(account=BROKE, day="2026-10-22")
        first = dict(self.state().get("frozen_targets") or {})
        self.assertTrue(first)
        newer = json.loads(json.dumps(T63.BOOK))
        newer["formed_on"] = "2026-11-02"
        got, _s = self.cycle(account=BROKE, day="2026-11-03", book=newer)
        frozen = dict(self.state().get("frozen_targets") or {})
        self.assertNotEqual(sorted(frozen), sorted(first),
                            "a new event did not get its own frozen targets")

    def test_the_FROZEN_bag_is_EVENT_SCOPED_so_a_close_clears_it(self):
        """`EVENT_SCOPED_STATE` is the one list of per-event bags, and item 64's own guard
        asserts every `for bag in` iterates it -- so adding a bag outside it would be caught."""
        self.assertIn("frozen_targets", LC.EVENT_SCOPED_STATE)
        self.assertIn("cash_wait", LC.EVENT_SCOPED_STATE)


# =============================================================================================
class AnETFDonHoldsByHandIsNeverSoldOrCounted(_Tmp):
    """Don's case five of six in his list, and both halves are structural rather than lucky."""

    #: A name that is NOT in the Index book and IS in the broker account.
    HAND_HELD = "SCHD"

    def test_IT_IS_NEVER_SOLD__because_the_planner_only_sells_the_slots_OWN_record(self):
        sess = T67.Recorded(account_fields=RICH,
                            positions=[{"symbol": self.HAND_HELD, "qty": "40",
                                        "avg_entry_price": "80", "side": "long"}])
        got, sess = self.cycle(sess=sess)
        for o in sess.placed:
            self.assertNotEqual(o["symbol"], self.HAND_HELD,
                                "a hand-held ETF was traded")
        for o in (got.get("orders") or []):
            self.assertNotEqual(o["ticker"], self.HAND_HELD)

    def test_IT_IS_NEVER_COUNTED_as_an_Index_holding(self):
        """`order_plan` reads the slot's OWN record, not the broker's position list, so a name
        the slot never bought cannot reduce or satisfy a target. Asserted on the plan rather
        than on intention."""
        sess = T67.Recorded(account_fields=RICH,
                            positions=[{"symbol": self.HAND_HELD, "qty": "40",
                                        "avg_entry_price": "80", "side": "long"}])
        got, _s = self.cycle(sess=sess)
        self.assertNotIn(self.HAND_HELD, (got.get("targets") or {}))
        st = self.state()
        self.assertNotIn(self.HAND_HELD, (st.get("holdings") or {}))

    def test_AND_THE_HONEST_LIMIT_IS_STATED__equity_is_the_ACCOUNT_S(self):
        """**REPORTED RATHER THAN SILENTLY FIXED.** `targets` sizes on the account's `equity`,
        which on a real account INCLUDES a hand-held ETF — so at a live percentage below 100 the
        ETF inflates the slot's target. It is moot today (the paper slot is 100% of its own
        account and every live slot ships at 0%), and changing what `equity` means is a sizing
        change that needs its own item. This test pins the behaviour so the question is dated
        rather than discovered later.
        """
        a = LS.targets(5.0, 1000.0, T63.BOOK["positions"])
        b = LS.targets(5.0, 4200.0, T63.BOOK["positions"])     # as if an ETF added 3,200
        self.assertTrue(a["ok"] and b["ok"])
        self.assertGreater(b["slot_value"], a["slot_value"],
                           "equity is NOT the account's, so this note is stale -- re-read it")
        # At 100% -- the paper slot -- the whole account IS the slot, so there is nothing to
        # separate and the behaviour is correct as it stands.
        self.assertAlmostEqual(LS.targets(100.0, 1000.0,
                                          T63.BOOK["positions"])["slot_value"], 1000.0)


# =============================================================================================
class TheTwoWAITSAreDifferentSituations(_Tmp):
    """Item 73 supersedes PART of item 67, and only part — kept apart on a principled basis.

    | | what happened | how long is normal | how it escalates |
    |---|---|---|---|
    | settlement wait | the slot SOLD and the broker refused a buy for funds | T+1, so >3 days is abnormal | item 67's 3-trading-day alert |
    | cash wait | the target exceeds the money and NO sale is pending | as long as Don takes to deposit | ONE alert, no ceiling day |

    The distinguishing fact is in the plan: a cycle WITH sells may be waiting on its own
    proceeds; a buy-only gap is waiting on outside cash, which is Don's business and not a
    fault. `_cash_wait` requires `not _has_sells` for exactly that reason.
    """

    def test_a_BUY_ONLY_gap_with_no_cash_is_a_CASH_wait(self):
        got, _s = self.cycle(account=BROKE, day="2026-10-22")
        self.assertEqual(got["send_outcome"], LC.SEND_WAITING_CASH)
        self.assertTrue(self.state().get("cash_wait"))

    def test_a_POST_SEND_BROKER_REFUSAL_is_still_a_SETTLEMENT_wait_and_still_escalates(self):
        """Item 67's positive control, relocated to the case it describes: *"a wait that never
        resolves must escalate, or the whole mechanism is a way of losing a rebalance
        quietly."*"""
        got = None
        for d in ("2026-10-22", "2026-10-23", "2026-10-26"):
            sess = T67.Recorded(account_fields=T67.LIMITED,
                                reject_message="insufficient buying power")
            got, _s = self.cycle(account=T67.LIMITED, sess=sess, day=d)
        self.assertIn("settlement_wait_overdue", [a["kind"] for a in got["alerts"]],
                      got.get("reason"))

    def test_BOTH_OUTCOMES_ARE_DECLARED_and_neither_spends_a_ceiling_day(self):
        self.assertIn(LC.SEND_WAITING_CASH, LC.SEND_OUTCOMES)
        self.assertIn(LC.SEND_TOPUP_TOO_SMALL, LC.SEND_OUTCOMES)
        for o in (LC.SEND_WAITING_CASH, LC.SEND_TOPUP_TOO_SMALL):
            self.assertIn(o, LC.SEND_OUTCOMES_THAT_DO_NOT_SPEND_A_CEILING_DAY)
        # AND THE ONES THAT DO SEND ARE NOT IN THAT LIST -- the positive control.
        self.assertNotIn(LC.SEND_SENT, LC.SEND_OUTCOMES_THAT_DO_NOT_SPEND_A_CEILING_DAY)

    def test_the_cash_wait_CLEARS_and_says_so(self):
        self.cycle(account=BROKE, day="2026-10-22")
        got, sess = self.cycle(account=RICH, day="2026-10-23")
        self.assertTrue(sess.placed, "the money arrived and nothing was bought")
        self.assertIn("cash_wait_cleared", got)
        self.assertNotIn(got.get("event_key") or "",
                         (self.state().get("cash_wait") or {}))


# =============================================================================================
class TheBUDGETSitsAboveTheCEILING(unittest.TestCase):
    """The structural change the ruling forced, asserted on the source.

    Until item 73 the order was: ceiling -> budget -> fill-until-budget. So a gap waiting for a
    deposit counted a trading day FIRST, and five of those stop the event and alert. Don's rule
    is the opposite, so the budget and the proportional spread moved above the ceiling and a
    pure cash wait returns before it.
    """

    def test_the_budget_is_resolved_BEFORE_the_ceiling_in_the_source(self):
        """REPOINTED BY ITEM 83, in the commit that moved the call (`MA59`).

        It searched for the literal `"SETTLE.spendable(account)"` and RAISED `ValueError:
        substring not found` when item 83 added a `reserved=` argument -- so a guard whose
        subject is an ORDERING identified its call by the exact text of its arguments. The
        ordering it protects never changed. Matched on `SETTLE.spendable(` now, which is the
        call rather than one spelling of it, and survives the next argument too.
        """
        import inspect
        src = inspect.getsource(LC.run_slot)
        i_budget = src.index("SETTLE.spendable(")
        i_alloc = src.index("SETTLE.allocate_buys(")
        i_ceiling = src.index("THE CEILING COUNTS ATTEMPTS")
        self.assertLess(i_budget, i_ceiling,
                        "the budget is still resolved after the ceiling, so a cash wait burns "
                        "a trading day")
        self.assertLess(i_alloc, i_ceiling)

    def test_run_slot_READS_NO_ENVIRONMENT__the_threshold_arrives_as_an_argument(self):
        """My first cut wrote `SETTLE.min_topup(env)` inside `run_slot`, which has no `env` --
        a `NameError` waiting on the one function that can send a real order. `run_slot` reads
        no environment at all, and everything it acts on arrives as an argument, which is what
        makes it testable through `run_cycle` with a dict."""
        import inspect
        src = inspect.getsource(LC.run_slot)
        self.assertNotIn("os.environ", src)
        self.assertIn("min_topup", inspect.signature(LC.run_slot).parameters)

    def test_run_cycle_resolves_it_ONCE_for_every_slot(self):
        """Don chose a single universal variable, so resolving it per slot would be one
        definition pretending to be several."""
        import inspect
        src = inspect.getsource(LC.run_cycle)
        self.assertEqual(src.count("SETTLE.min_topup("), 1)
        self.assertIn("min_topup=_min_topup", src)


if __name__ == "__main__":
    import sys as _s
    _s.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
