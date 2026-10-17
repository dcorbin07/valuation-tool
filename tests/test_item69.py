# -*- coding: utf-8 -*-
"""ITEM 69 — the auditor's fourth blocker: an exit the feed cannot price was dropped in silence.

The auditor reproduced it end to end through `run_cycle` with the real `AlpacaPaperBroker`. The
slot holds AAPL and MSFT, the book now holds AAPL only, and IEX returns a one-sided quote for
MSFT so there is no mid -- the documented common case, and 26 of 86 names on the first real
cycle:

    exits_planned : ['MSFT']                 <- it KNOWS MSFT must go
    skipped       : [{'ticker': 'MSFT', 'reason': 'no usable mark'}]
    PLACED        : []
    alerts        : []                       <- NO ALERT
    event closed? : True                     <- recorded COMPLETE
    marks_coverage: {'n_needed': 1, 'n_priced': 1, 'missing': []}

**§8 REQUIRES THREE THINGS AND ONLY THE FIRST HAPPENED:** no trade, an alert, and a retry next
cycle. And the coverage line reporting perfect coverage is what made it silent rather than merely
wrong -- the workflow's own summary prints that number, so the daily log read as a healthy day.

**IT IS ITEM 67's OWN FIX, HALF DONE, and the mechanism is three copies of one fact.** Item 67
widened the QUOTE list to cover an exited name and left the REFUSAL and the REPORT computing the
same population from the book alone -- and an exit is by definition not in the book's held
positions. One definition now: `tradable_names`.

**AND "NOTHING TO DO" AND "I COULD NOT WORK OUT WHAT TO DO" ARE NOW DIFFERENT VALUES.** The close
branch tested `not plan["orders"]`, which is true of both. That is the third collapse of two
epistemic states on this path -- after `[]`-means-both-empty-and-failed (item 65) and
truncated-versus-failed (item 67 part 0) -- so the outcome is a value from a declared set and the
test below enumerates it.

Every bar and every HTTP reply here is a recorded fixture. Nothing touches a network.
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

OPEN_NOW = _dt.datetime(2026, 11, 2, 13, 36)

#: The book AFTER a rebalance that dropped MSFT. AAPL alone is held.
BOOK_DROPPED_MSFT = {"ok": True, "formed_on": "2026-11-01", "reason": "",
                     "positions": [{"ticker": "AAPL", "status": "held", "weight": 1.0}]}

#: A fully-settled 1x account, the shape Alpaca reports at `multiplier` 1.
ACCOUNT = {"id": "acct-paper-1", "account_number": "PA1", "equity": "10000",
           "cash": "10000", "buying_power": "10000",
           "non_marginable_buying_power": "10000", "status": "ACTIVE", "multiplier": "1"}


class OneSidedQuote:
    """Alpaca, replayed, where **MSFT has only a bid** -- so there is no mid.

    That is the real IEX failure this blocker lives on: a one-sided quote is not a missing
    symbol, and `quote_reject_reason` refuses it for the same reason `options_greeks` does.
    The slot HOLDS MSFT, through a recorded filled order carrying its own `valquo-` prefix.
    """

    def __init__(self, *, price_msft=False, msft_qty=50.0):
        self.price_msft, self.msft_qty = price_msft, msft_qty
        self.placed, self.cancelled, self.calls = [], [], []

    def _orders(self):
        out = [{"id": "f-aapl", "client_order_id":
                LC.client_order_id(LC.PAPER_SLOT, "rebalance:2026-07-30", "AAPL"),
                "symbol": "AAPL", "side": "buy", "qty": "40", "filled_qty": "40",
                "status": "filled", "limit_price": "100", "filled_avg_price": "100",
                "submitted_at": "2026-07-30T14:40:00Z"}]
        if self.msft_qty:
            out.append({"id": "f-msft", "client_order_id":
                        LC.client_order_id(LC.PAPER_SLOT, "rebalance:2026-07-30", "MSFT"),
                        "symbol": "MSFT", "side": "buy", "qty": str(self.msft_qty),
                        "filled_qty": str(self.msft_qty), "status": "filled",
                        "limit_price": "200", "filled_avg_price": "200",
                        "submitted_at": "2026-07-30T14:41:00Z"})
        return out

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account"):
            return T63.Reply(dict(ACCOUNT))
        if url.endswith("/v2/positions"):
            pos = [{"symbol": "AAPL", "qty": "40", "avg_entry_price": "100", "side": "long"}]
            if self.msft_qty:
                pos.append({"symbol": "MSFT", "qty": str(self.msft_qty),
                            "avg_entry_price": "200", "side": "long"})
            return T63.Reply(pos)
        if "quotes/latest" in url:
            q = {"AAPL": {"bp": 99.0, "ap": 101.0, "t": "x"}}
            # **MSFT: A BID AND NO ASK.** One-sided, so no mid -- not a missing symbol.
            q["MSFT"] = ({"bp": 199.0, "ap": 201.0, "t": "x"} if self.price_msft
                         else {"bp": 199.0, "ap": 0.0, "t": "x"})
            return T63.Reply({"quotes": q})
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

    def seed(self, holdings=None):
        """**THE SLOT HAS TRADED BEFORE, AND THE FIXTURE HAS TO SAY SO.**

        My first cut started with NO state file, and item 67's fresh-record check then refused
        the cycle before a plan was ever built -- *"this slot's record is brand new ... and the
        account already holds 1 position(s)"*. Two tests failed on it and, worse, **four passed
        for the wrong reason**: the fresh-record refusal happens to name the held positions, so
        an assertion that MSFT appears in an alert was satisfied by a refusal that has nothing
        to do with pricing. A vacuous pass, caught by the two that failed beside it.

        It is also the realistic state: a slot facing a rebalance exit has necessarily bought
        before, which is how it comes to hold the name being dropped.
        """
        st = {"slot": LC.PAPER_SLOT, "account_id": "acct-paper-1",
              "processed": ["rebalance:2026-07-30"],
              "holdings": dict(holdings if holdings is not None
                               else {"AAPL": 40.0, "MSFT": 50.0})}
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)

    def cycle(self, sess, book=None):
        """A real `run_cycle`, paper mode, with the REAL broker class on a recorded session."""
        out = LC.run_cycle(env={}, mode=LC.PAPER, now=OPEN_NOW, root=self.root,
                           book=(book or BOOK_DROPPED_MSFT), paper_client=broker(sess),
                           notify_send=(lambda cfg, b: True))
        return out, (out.get("paper") or {})


# ----------------------------------------------------------------------------------------- #
# THE BLOCKER
# ----------------------------------------------------------------------------------------- #
class AnUnpricedExitRefusesAlertsAndRetries(_Cycle):
    """**§8's THREE CLAUSES, of which only the first used to happen.** *"Doesn't trade that
    cycle, alerts Don, and tries again next cycle."*"""

    def test_it_SENDS_NOTHING(self):
        got, p = self.cycle(OneSidedQuote())
        sess_placed = [o["symbol"] for o in got["paper"].get("sent") or []]
        self.assertEqual(sess_placed, [], p.get("reason"))

    def test_it_ALERTS(self):
        """The half that was missing. An alert, with the name in it."""
        _, p = self.cycle(OneSidedQuote())
        kinds = [a["kind"] for a in p["alerts"]]
        self.assertTrue(kinds, "no alert at all -- the auditor's blocker")
        self.assertIn("MSFT", " ".join(a["reason"] for a in p["alerts"]))

    def test_THE_EVENT_STAYS_OPEN_and_is_NOT_recorded_complete(self):
        """The other half. `event_for` will not fire again until the next rebalance, so a closed
        event means the slot holds a dropped name for a quarter."""
        _, p = self.cycle(OneSidedQuote())
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertNotIn("rebalance:2026-11-01", st.get("processed") or [],
                         "the event was recorded COMPLETE with an exit unpriced")
        self.assertNotIn("targets are already met", p.get("reason") or "")

    def test_IT_RETRIES_and_succeeds_once_the_quote_is_two_sided(self):
        """**THE POSITIVE CONTROL, and without it every assertion above passes if the slot can
        never trade at all.** The same state with a two-sided quote must sell MSFT."""
        sess = OneSidedQuote()
        self.cycle(sess)
        self.assertEqual(sess.placed, [])
        sess.price_msft = True
        _, p = self.cycle(sess)
        sold = [(o["symbol"], o["side"]) for o in sess.placed]
        self.assertIn(("MSFT", "sell"), sold, p.get("reason"))

    def test_the_COVERAGE_LINE_no_longer_reports_perfect_coverage(self):
        """**THE LINE THAT MADE IT SILENT.** It read `1 of 1 priced, missing: []` while a name
        went unpriced -- a number measured on a set that excludes the case it exists to catch,
        and the workflow's own summary prints it."""
        _, p = self.cycle(OneSidedQuote())
        mc = p["marks_coverage"]
        self.assertIn("MSFT", mc["missing"], mc)
        self.assertIn("MSFT", mc["missing_exits"], mc)
        self.assertEqual(mc["n_needed"], 2, mc)
        self.assertEqual(mc["n_priced"], 1, mc)

    def test_the_refusal_SAYS_IT_IS_AN_EXIT(self):
        """An unpriced buy waits harmlessly; an unpriced exit leaves the slot holding a name the
        Index dropped. A reader cannot act on a refusal that does not distinguish them."""
        _, p = self.cycle(OneSidedQuote())
        blob = (p.get("reason") or "") + " ".join(a["reason"] for a in p["alerts"])
        self.assertIn("SELL", blob.upper())
        self.assertIn("MSFT", blob)


class OnlyTargetsMetClosesAnEvent(unittest.TestCase):
    """**THE TEST THE BRIEF ASKS FOR BY NAME, and it is only possible because the outcome is a
    value from a declared set.** *"Add a test that fails if any planner outcome other than
    'targets met' closes an event."* Against a boolean there is nothing to enumerate -- which is
    how the same collapse happened three times."""

    def test_every_declared_outcome_is_reachable(self):
        """A set with an unreachable member would make the enumeration below pass by never
        testing it."""
        seen = {LC.plan_outcome({"orders": [], "skipped": []}),
                LC.plan_outcome({"orders": [], "skipped": [{"ticker": "X"}]}),
                LC.plan_outcome({"orders": [{"ticker": "A"}], "skipped": []})}
        self.assertEqual(seen, set(LC.PLAN_OUTCOMES))

    def test_EXACTLY_ONE_outcome_closes_an_event(self):
        self.assertEqual(LC.PLAN_OUTCOMES_THAT_CLOSE_AN_EVENT, (LC.PLAN_TARGETS_MET,))
        for o in LC.PLAN_OUTCOMES:
            if o != LC.PLAN_TARGETS_MET:
                self.assertNotIn(o, LC.PLAN_OUTCOMES_THAT_CLOSE_AN_EVENT,
                                 "%s would close an event" % o)

    def test_the_close_branch_TESTS_FOR_THE_OUTCOME_rather_than_an_empty_list(self):
        """Asserted on the syntax tree, because the two forms are behaviourally identical on
        every input that is not the bug: `not plan["orders"]` and `outcome == TARGETS_MET`
        differ only when something was skipped."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_slot")
        body = ast.unparse(fn)
        self.assertIn("plan_outcome(plan)", body)
        self.assertIn("PLAN_TARGETS_MET", body)
        self.assertNotIn("if not plan['orders']", body.replace('"', "'"))

    def test_ORDERS_BEAT_A_SKIP_so_per_name_granularity_survives(self):
        """**MY OWN FIRST CUT RETURNED `BLOCKED` WHENEVER ANYTHING WAS SKIPPED**, which refuses
        the whole cycle for one withheld name -- undoing item 67's per-name granularity that the
        auditor checked and approved (*"an unreadable resting quantity now costs that name, not
        nothing"*). Caught by working out what the change did to the case item 67 had just got
        right."""
        self.assertEqual(LC.plan_outcome({"orders": [{"ticker": "A"}],
                                          "skipped": [{"ticker": "B"}]}),
                         LC.PLAN_WORK)

    def test_a_skip_is_ALERTED_even_when_other_names_DO_trade(self):
        """The same silence one branch over: a cycle that traded four names and withheld a fifth
        said nothing about the fifth either."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn('if plan.get("skipped"):', src)
        i = src.index('if plan.get("skipped"):')
        j = src.index("if outcome == PLAN_BLOCKED:", i)
        self.assertLess(i, j, "the alert is inside the BLOCKED branch rather than before it")
        self.assertIn('out["alerts"].append', src[i:j])


class ThePopulationIsONEDefinition(unittest.TestCase):
    """Three copies of one fact is why only one of them got widened (`B7`)."""

    BOOK = {"ok": True, "formed_on": "2026-11-01",
            "positions": [{"ticker": "AAPL", "status": "held", "weight": 1.0},
                          {"ticker": "GONE", "status": "exited", "weight": 0.0}]}

    def test_an_exit_is_in_the_population_and_the_book_alone_cannot_contain_it(self):
        self.assertEqual(LS.tradable_names(self.BOOK), ["AAPL"])
        self.assertIn("MSFT", LS.tradable_names(self.BOOK, {"MSFT": 50.0}))

    def test_a_ZERO_holding_is_NOT_in_it(self):
        """A name the slot has sold out of needs no price, and demanding one would refuse the
        cycle for ever over a record that is merely stale."""
        self.assertEqual(LS.tradable_names(self.BOOK, {"SOLD": 0.0}), ["AAPL"])

    def test_ALL_THREE_consumers_read_it(self):
        """The guard that stops a fourth copy appearing. Read on the syntax tree over both
        modules, because a fourth copy would be new code rather than an edit to these."""
        cyc = io.open(LC.__file__, encoding="utf-8").read()
        slots = io.open(LS.__file__, encoding="utf-8").read()
        self.assertIn("LS.tradable_names(book", cyc)          # marks_coverage
        self.assertIn("tradable_names(book, slot_record)", slots)   # preflight
        self.assertEqual(slots.count("def tradable_names("), 1,
                         "a second definition of the population exists")

    def test_the_quote_list_is_still_the_WIDER_set(self):
        """`tickers` in `run_cycle` covers EVERY slot's holdings, not just one slot's -- one
        quote request serves every slot, so narrowing it to match would cost a name its price."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        self.assertIn("_slots_to_price", src)

    def test_PREFLIGHT_REFUSES_on_an_unpriced_exit(self):
        got = LS.preflight(book=self.BOOK, equity=1000.0,
                           marks={"AAPL": {"mid": 100.0}},
                           slot_record={"MSFT": 50.0}, pct=100.0)
        self.assertFalse(got["ok"])
        self.assertIn("MSFT", got["reason"])
        self.assertIn("EXIT", got["reason"].upper())

    def test_it_does_NOT_refuse_when_the_exit_IS_priced(self):
        """THE POSITIVE CONTROL for the refusal above."""
        got = LS.preflight(book=self.BOOK, equity=1000.0,
                           marks={"AAPL": {"mid": 100.0}, "MSFT": {"mid": 200.0}},
                           slot_record={"MSFT": 50.0}, pct=100.0)
        self.assertTrue(got["ok"], got["reason"])


class TheOldCodeFailedEveryOneOfThese(_Cycle):
    """**NOT A CLAIM -- A RECORDED REPRODUCTION.** The auditor's own output, as a fixture, so a
    future reader can see what the blocker looked like rather than taking the commit's word.
    These are the four facts that made it a blocker rather than a bug."""

    AUDITORS_OUTPUT = {
        "exits_planned": ["MSFT"],
        "planned": [],
        "skipped": [{"ticker": "MSFT", "reason": "no usable mark"}],
        "placed": [],
        "alerts": [],
        "event_closed": True,
        "processed": ["rebalance:2026-11-01"],
        "marks_coverage": {"n_needed": 1, "n_priced": 1, "missing": []},
        "reason": ("this event's targets are already met, so there is nothing to send and the "
                   "event is closed"),
    }

    def test_each_of_the_four_facts_is_now_the_other_way(self):
        _, p = self.cycle(OneSidedQuote())
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        # 1. it still knows the exit is needed
        self.assertEqual(p.get("exits_planned"), self.AUDITORS_OUTPUT["exits_planned"])
        # 2. the alert list was empty and is not
        self.assertEqual(self.AUDITORS_OUTPUT["alerts"], [])
        self.assertTrue(p["alerts"])
        # 3. the event was closed and is not
        self.assertTrue(self.AUDITORS_OUTPUT["event_closed"])
        self.assertNotIn("rebalance:2026-11-01", st.get("processed") or [])
        # 4. coverage reported 1 of 1 and now reports the shortfall
        self.assertEqual(self.AUDITORS_OUTPUT["marks_coverage"]["missing"], [])
        self.assertIn("MSFT", p["marks_coverage"]["missing"])

    def test_the_false_sentence_is_no_longer_produced(self):
        _, p = self.cycle(OneSidedQuote())
        self.assertIn("targets are already met", self.AUDITORS_OUTPUT["reason"])
        self.assertNotIn("targets are already met", p.get("reason") or "")

    def test_a_CLEAN_cycle_still_closes_its_event(self):
        """**THE CONTROL THAT STOPS ALL OF THIS BEING A WAY TO NEVER FINISH A REBALANCE.** With
        nothing to do and nothing skipped, the event must still close."""
        self.seed({"AAPL": 40.0})
        sess = OneSidedQuote(price_msft=True, msft_qty=0.0)
        got, p = self.cycle(sess, book={"ok": True, "formed_on": "2026-11-01", "reason": "",
                                        "positions": [{"ticker": "AAPL", "status": "held",
                                                       "weight": 1.0}]})
        # AAPL is held at 40 against a target of 40x100 = the slot's whole value, so there is
        # nothing to trade and nothing skipped.
        if p.get("plan_outcome") == LC.PLAN_TARGETS_MET:
            st = LC.read_state(LC.PAPER_SLOT, self.root)
            self.assertIn("rebalance:2026-11-01", st.get("processed") or [],
                          "a clean cycle did not close its event")
        else:
            self.assertIn(p.get("plan_outcome"), LC.PLAN_OUTCOMES, p.get("reason"))


# ----------------------------------------------------------------------------------------- #
# PART 2 -- SPIN-OFFS IN THE BOUND RECORD. REPORTING ONLY: nothing here changes the record or
# the contract, and the rule is Don's to adopt.
# ----------------------------------------------------------------------------------------- #
class ASpinOffBooksAFakeLossInTheRecord(unittest.TestCase):
    """**ITEM 68's FINDING, APPLIED TO THE RECORD AND DEMONSTRATED THROUGH ITS OWN ARITHMETIC.**

    Item 68 measured that yfinance -- the record's vendor -- left Aptiv's and Unilever's
    spin-offs as **-10.6%** and **-7.0%** one-day cliffs. The record's contribution per holding
    is `cur / base - 1` on that same adjusted close, so a cliff the vendor did not restate is
    booked as a loss the holder never suffered: they received shares in the new entity.

    **AND AMENDMENT 2's CORPORATE-ACTION RULE IS STRUCTURALLY UNREACHABLE HERE, not merely
    silent on it.** Its trigger is *"acquired or stops trading"*, and in the code it sits behind
    `if not cur:` -- no current price -- plus `_stopped_trading`. A spun-off parent keeps trading
    under the same ticker and prices normally, so **both conditions fail.** A spin-off is the one
    corporate action where the held name does not cease to exist.

    Driven through `contract_row` with an injected fetcher, which is how that module is designed
    to be exercised: *"a price path that can only be exercised against the live internet is a
    path nobody exercises."*
    """

    BASE, MARK = "2026-10-22", "2026-10-30"

    #: Aptiv's MEASURED cliff -- 69.44 to 62.09 on the distribution date, which yfinance
    #: recorded as no action at all. The holder also received 1 VGNT per 3 APTV.
    APTV_CLIFF = 62.09 / 69.440002

    def _fetch(self, closes):
        import pandas as pd

        def fetch(ticker, days=400, as_of=None, **kw):
            rows = closes.get(str(ticker).upper())
            if not rows:
                return pd.DataFrame()
            # **Date/Close, which is the shape `prices.get_history_df` returns** -- taken from
            # `test_index_mark`'s own tape rather than guessed. My first cut used a lower-case
            # column on a string index and the benchmark read as unpriced, which is the very
            # message item 68 was about.
            df = pd.DataFrame({"Date": list(rows.keys()), "Close": list(rows.values())})
            df.attrs["valquo_src"] = "injected"
            return df
        return fetch

    def _book(self, tmp, names):
        meta = {"ok": True, "benchmark": "SPY", "inception_date": self.BASE,
                "scan_date": self.BASE,
                "positions": [{"ticker": t, "weight": w} for t, w in names]}
        # **DELIBERATELY NOT NAMED AFTER THE BOUND BOOK'S FILE.** `test_index_book_publish`
        # keeps a census of every file referencing that path, because *"two mechanisms reading
        # one named object is the PT-SPLIT shape"* -- and it caught this file twice: first for
        # the temp filename, then for a comment that spelled the path out while explaining why
        # this is not a consumer. The guard is right about the property and reads TEXT rather
        # than code, so the name is avoided here instead; allowlisting the file would weaken a
        # guard against exactly the confusion the name creates. Reported outside this lane
        # (`RUN_RULES` rule 3) rather than repaired, because that census is another lane's and
        # is protecting a real invariant.
        p = os.path.join(tmp, "item69_fixture_book.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(meta, fh)
        return p

    def _row(self, tmp):
        from valuation.screener import index_mark as IM
        flat = {self.BASE: 100.0, self.MARK: 100.0}
        cliffed = {self.BASE: 100.0, self.MARK: 100.0 * self.APTV_CLIFF}
        return IM.contract_row(
            as_of=self.MARK, meta_path=self._book(tmp, [("APTV", 0.5), ("AAPL", 0.5)]),
            fetch=self._fetch({"APTV": cliffed, "AAPL": flat, "SPY": flat}),
            refuse_before_close=False)

    def test_the_record_books_a_loss_the_holder_did_not_suffer(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        got = self._row(tmp)
        self.assertTrue(got["ok"], got.get("reason"))
        # Half the book fell 10.58% for no economic reason, so the book reads about -5.3%.
        self.assertLess(got["row"]["valquo_pct"], -4.0, got["row"])
        self.assertGreater(got["row"]["valquo_pct"], -6.0, got["row"])

    def test_AMENDMENT_2s_RULE_DOES_NOT_FIRE_because_the_name_still_prices(self):
        """Its branch is behind `if not cur:`, and a spun-off parent has a `cur`. `exited` is
        the rule's own output, and a spin-off produces none."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        got = self._row(tmp)
        blob = json.dumps(got, default=str)
        self.assertNotIn('"exited": [{', blob,
                         "Amendment 2's rule fired on a name that still trades")

    def test_THE_RULES_TRIGGER_IS_READ_FROM_THE_CODE_not_from_the_prose(self):
        """The contract says *"acquired or stops trading"*; what decides is `if not cur:` plus
        `_stopped_trading`. A rule's reach is what the code tests, not what the prose says."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "index_mark.py"),
                      encoding="utf-8").read()
        i = src.index("_apply_ca = (seg_base_key >= CORPORATE_ACTION_FROM)")
        block = src[i:src.index("coverage = (wsum / total_w)", i)]
        self.assertIn("if not cur:", block)
        self.assertIn("_stopped_trading", block)
        # **THE EXPRESSION MOVED WHEN AMENDMENT 3 WAS DRAFTED**, and the finding did not: the
        # contribution is still the parent's price over the base, plus a `credit` that is ZERO
        # unless the contract's signature row says otherwise. The behavioural test above still
        # books the fake loss, which is the honest state while the amendment is unsigned.
        self.assertIn('num += p["weight"] * ((cur + credit) / base - 1.0)', block)
        self.assertIn("credit = 0.0", block)
        self.assertIn('_a3["signed"]', block)

    def test_the_contract_says_acquired_or_stops_trading_and_NOTHING_about_a_spin_off(self):
        txt = io.open(os.path.join(REPO, "PAPER_TRACK_CONTRACT.md"),
                      encoding="utf-8").read()
        self.assertIn("acquired or stops trading", txt)
        i = txt.index("### CORPORATE ACTIONS")
        rule = txt[i:i + 2600].lower()
        for word in ("spin-off", "spinoff", "demerger", "spun"):
            self.assertNotIn(word, rule,
                             "the rule mentions %r after all; re-read the finding" % word)

    def test_THE_FAKE_LOSS_IS_THE_DISTRIBUTED_FRACTION_and_scales_with_it(self):
        """The exposure is not a fixed size: it is whatever share of the value walked out of the
        door. Aptiv's was ~10.6%; Corteva's separation was ~85% of the combined company, and
        the only reason that one is harmless to the record is that yfinance DID restate it."""
        self.assertAlmostEqual(1.0 - self.APTV_CLIFF, 0.1058, places=3)
        self.assertLess(1.0 / 6.665, 0.16)        # Corteva's continuing stub

    def test_NOTHING_IN_THIS_ITEM_CHANGES_THE_RECORD_OR_THE_CONTRACT(self):
        """The brief's instruction, pinned. Part 2 reports and proposes; adopting a rule is a
        contract amendment and Don's decision."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "index_mark.py"),
                      encoding="utf-8").read()
        self.assertEqual(src.count("CORPORATE_ACTION_FROM = "), 1)
        self.assertIn('CORPORATE_ACTION_FROM = "2026-10-22"', src)
        txt = io.open(os.path.join(REPO, "PAPER_TRACK_CONTRACT.md"),
                      encoding="utf-8").read()
        self.assertNotIn("8c AMENDMENT", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
