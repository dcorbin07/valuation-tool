# -*- coding: utf-8 -*-
"""ITEM 63 — the auditor's two blockers, two failed questions, and its recommendations.

The auditor's verdict on the §8 live path was **do not enter a live key yet**, on two blockers
that 167 existing tests all missed. Both misses have the same shape and it is the shape these
tests are built around:

  * **BLOCKER 1** — `run_slot` transmits by calling `client.place_limit(...)` and the real paper
    broker had only `place_equity`, so every paper order raised `AttributeError`. Every suite
    missed it because every suite hands `run_slot` a **stub that defines `place_limit`**. The
    suite modelled the clients' reply SHAPES (`LiveShaped` exists for exactly that) and never
    their METHOD NAMES. So the tests here use the **real classes** -- the real
    `AlpacaPaperBroker` driven by recorded HTTP replies -- and derive the required interface
    from `live_cycle`'s own source rather than from a list somebody typed.
  * **BLOCKER 2** — a duplicate buy-in, reachable through an empty record plus a discarded
    state write. `TheDuplicateBuyInIsClosed` reproduces the auditor's own three cases.

Nothing here touches a network or a credential: the broker takes an injectable session, and the
keys are fixtures.
"""
from __future__ import annotations

import ast
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
from valuation.edge import live_slots as LS         # noqa: E402

BOOK = {"ok": True, "formed_on": "2026-10-22", "reason": "",
        "positions": [{"ticker": "AAPL", "status": "held", "weight": 0.6},
                      {"ticker": "MSFT", "status": "held", "weight": 0.4}]}
MARKS = {"AAPL": {"mid": 100.0}, "MSFT": {"mid": 200.0}}
ARMED = {"armed": True, "reason": "fixture"}


# ----------------------------------------------------------------------------------------- #
# a RECORDED Alpaca, not a stub of our own interface
# ----------------------------------------------------------------------------------------- #
class Reply:
    def __init__(self, payload, status=200):
        self.status_code, self._p, self.text = status, payload, ""

    def json(self):
        return self._p


class RecordedAlpaca:
    """Alpaca's own HTTP shapes, replayed. The broker under test is the REAL one.

    **THE POINT OF THIS CLASS IS WHAT IT DOES NOT DEFINE.** It implements `requests`' one
    `request(...)` entry point and nothing else -- no `place_limit`, no `place_equity`, no
    knowledge of this project's interface at all. So the only way an order reaches it is
    through `AlpacaPaperBroker`'s real method resolution, which is precisely the step every
    existing suite skipped by handing `run_slot` a stub.
    """

    def __init__(self, positions=None, orders=None, reject=False, account_id="acct-paper-1"):
        self.positions, self.orders = list(positions or []), list(orders or [])
        self.reject, self.account_id = reject, account_id
        self.placed, self.calls = [], []

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account"):
            return Reply({"id": self.account_id, "account_number": "PA123456",
                          "equity": "1000", "cash": "1000", "buying_power": "1000",
                          "status": "ACTIVE", "multiplier": "1"})
        if url.endswith("/v2/positions"):
            return Reply(self.positions)
        if url.endswith("/v2/orders") and method == "GET":
            return Reply(self.orders)
        if url.endswith("/v2/orders") and method == "POST":
            body = json.loads(data or "{}")
            self.placed.append(body)
            if self.reject:
                return Reply({"message": "insufficient buying power"}, status=403)
            return Reply(dict(body, id="srv-%d" % len(self.placed),
                              status="new", filled_qty="0"))
        if "/v2/stocks/" in url or "snapshots" in url:
            return Reply({"snapshots": {}})
        return Reply({}, status=404)


def broker(sess, **kw):
    """The REAL AlpacaPaperBroker on a recorded session, with fixture keys."""
    return AB.AlpacaPaperBroker(key_id="PKFIXTURE", secret_key="s" * 24, session=sess, **kw)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)


# ----------------------------------------------------------------------------------------- #
# BLOCKER 1
# ----------------------------------------------------------------------------------------- #
class TheInterfaceRunSlotNeedsIsSatisfiedByBothRealClients(unittest.TestCase):
    """**THE TEST THE BRIEF ASKS FOR, AND IT IS DERIVED RATHER THAN TYPED.**

    A hand-written list of required methods is the same defect one level up: it would have said
    `place_limit` only if somebody remembered, and the thing that went wrong is that nobody
    did. So the list comes out of `live_cycle`'s own AST -- every `client.X(...)` call in the
    module -- and is then required of both REAL classes.
    """

    #: Names a client object goes by in `live_cycle`.
    HOLDERS = ("client", "pc", "paper_client")

    @classmethod
    def setUpClass(cls):
        cls.src = open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(cls.src)
        wanted = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                    and f.value.id in cls.HOLDERS):
                wanted.add(f.attr)
        cls.wanted = wanted
        # **A GUARDED CALL IS AN OPTIONAL CAPABILITY, AN UNGUARDED ONE IS THE INTERFACE.**
        # `_LiveClient` has no `quotes` and must not grow one: Alpaca's market data lives on
        # `data.alpaca.markets` and that class is pinned to exactly `api.alpaca.markets`, so a
        # second host would spend the single-host guarantee. `run_cycle` guards it with
        # `hasattr` and prices live slots from the paper client instead. So the rule is not
        # "every method is on both clients" -- it is the two-part property below, which still
        # catches blocker 1 and needs nobody to maintain a list of exceptions.
        cls.guarded = {m for m in wanted
                       if all(('hasattr(%s, "%s")' % (h, m)) in cls.src
                              for h in cls.HOLDERS
                              if ("%s.%s(" % (h, m)) in cls.src)}
        cls.required = wanted - cls.guarded

    def test_the_derivation_is_not_vacuous(self):
        """A POSITIVE CONTROL: an empty set would make every assertion below pass by seeing
        nothing, which is how this whole class of defect survives."""
        self.assertIn("place_limit", self.wanted,
                      "the AST walk found no place_limit call -- the derivation is broken")
        self.assertIn("orders", self.wanted)
        self.assertGreaterEqual(len(self.wanted), 3)
        self.assertIn("place_limit", self.required,
                      "place_limit must be REQUIRED, not optional: it is the line that "
                      "transmits and nothing guards it")

    def test_every_REQUIRED_method_exists_on_the_REAL_paper_broker(self):
        missing = sorted(m for m in self.required if not hasattr(AB.AlpacaPaperBroker, m))
        self.assertEqual(missing, [],
                         "live_cycle calls %r unguarded and AlpacaPaperBroker has no such "
                         "method; this is blocker 1 exactly" % (missing,))

    def test_every_REQUIRED_method_exists_on_the_REAL_live_client(self):
        missing = sorted(m for m in self.required if not hasattr(LS._LiveClient, m))
        self.assertEqual(missing, [],
                         "live_cycle calls %r unguarded on no live client" % (missing,))

    def test_any_method_MISSING_from_either_client_is_guarded_at_every_site(self):
        """The other half, and it is what makes the rule above safe to narrow: an optional
        capability must be optional EVERYWHERE, or one unguarded site reintroduces blocker 1."""
        for m in sorted(self.wanted):
            on_both = (hasattr(AB.AlpacaPaperBroker, m) and hasattr(LS._LiveClient, m))
            if not on_both:
                self.assertIn(m, self.guarded,
                              "%r is missing from a real client and is called without a "
                              "hasattr guard somewhere" % m)

    def test_quotes_is_the_one_optional_capability_and_it_is_deliberate(self):
        """Recorded rather than left to be rediscovered: the asymmetry is real, it is handled,
        and the live client must NOT grow the method."""
        self.assertIn("quotes", self.guarded)
        self.assertFalse(hasattr(LS._LiveClient, "quotes"),
                         "a live client grew a quotes method; Alpaca's data host is not "
                         "api.alpaca.markets and that class is pinned to one host")
        self.assertTrue(hasattr(AB.AlpacaPaperBroker, "quotes"))

    def test_the_two_clients_agree_on_the_transmitting_method(self):
        """The asymmetry ran the WRONG way: the only client that worked through the one line
        that spends money was the one spending real money."""
        for cls in (AB.AlpacaPaperBroker, LS._LiveClient):
            self.assertTrue(callable(getattr(cls, "place_limit", None)), cls.__name__)

    def test_place_limit_DELEGATES_and_does_not_reimplement(self):
        """`B7`. Two copies of the order-body rules drift, and the drift is silent -- a paper
        order would start passing validation a live order fails, or the reverse."""
        import io as _io
        import tokenize
        src = open(AB.__file__, encoding="utf-8").read()
        fn = src[src.index("    def place_limit("):]
        fn = fn[:fn.index("    def cancel(")]
        # **THE CODE, NOT THE PROSE.** My first cut banned the substring `time_in_force` and
        # fired against the correct tree, because the docstring explains that
        # `place_equity`'s `time_in_force` rule applies unchanged. A guard that cannot tell
        # code from prose about code is not measuring the tree -- this project's most
        # repeated test defect, committed here in the same change that documents it.
        code = []
        try:
            for tok in tokenize.generate_tokens(_io.StringIO(fn.strip()).readline):
                if tok.type not in (tokenize.COMMENT, tokenize.STRING):
                    code.append(tok.string)
        except (tokenize.TokenError, IndentationError):
            pass
        code = " ".join(code)
        self.assertIn("place_equity", code, "place_limit does not delegate at all")
        self.assertNotIn("time_in_force", code,
                         "place_limit re-implements the fractional rule instead of delegating")
        self.assertNotIn("FRACTIONAL_TIF", code)

    def test_that_stripper_is_not_vacuous(self):
        """A POSITIVE CONTROL for the tokenizer above: an empty string would make the two
        `assertNotIn`s pass by seeing nothing."""
        import io as _io
        import tokenize
        src = open(AB.__file__, encoding="utf-8").read()
        fn = src[src.index("    def place_equity("):]
        fn = fn[:fn.index("    def place_limit(")]
        code = []
        for tok in tokenize.generate_tokens(_io.StringIO(fn.strip()).readline):
            if tok.type not in (tokenize.COMMENT, tokenize.STRING):
                code.append(tok.string)
        self.assertIn("time_in_force", " ".join(code),
                      "the stripper removed real code, so the check above sees nothing")

    def test_the_call_site_does_NOT_use_a_getattr_fallback(self):
        """The auditor is explicit: a `getattr(client, 'place_limit', client.place_equity)`
        would fix today's symptom and reintroduce the silent-divergence class, so the next
        method to diverge would be absorbed the same way and the suite would stay green."""
        src = open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "getattr":
                args = [a for a in node.args if isinstance(a, ast.Constant)]
                for a in args:
                    self.assertNotIn("place", str(a.value),
                                     "the transmit call resolves a method by getattr")


class ARealPaperOrderReachesTheRealBroker(_Tmp):
    """**THE INTEGRATION TEST, ON RECORDED HTTP.** No stub of our own interface anywhere: the
    class under test is the real `AlpacaPaperBroker` and the only thing faked is Alpaca."""

    def test_run_slot_PLACES_an_order_through_the_real_paper_broker(self):
        sess = RecordedAlpaca()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True)
        self.assertTrue(got["acted"], got["reason"])
        self.assertEqual(len(sess.placed), 2, sess.placed)
        self.assertTrue(all(o["ok"] for o in got["sent"]), got["sent"])
        self.assertEqual([a for a in got["alerts"] if a["kind"] == "broker_error"], [])

    def test_the_old_code_path_FAILED_here_and_the_failure_is_pinned(self):
        """**THE BLOCKER, RECONSTRUCTED.** A client with the paper broker's OLD interface --
        `place_equity` and no `place_limit` -- must still be caught loudly rather than
        silently, in case some future client regresses the same way."""
        class OldInterface:
            def orders(self, **k):
                return []

            def positions(self):
                return []

            def place_equity(self, *a, **k):
                return {"ok": True}
        got = LC.run_slot("1", pct=10.0, armed_state=ARMED, book=BOOK,
                          client=OldInterface(), equity=1000.0, marks=MARKS, root=self.root,
                          send=True, paper_targets={"AAPL": 60.0, "MSFT": 40.0},
                          paper_value=100.0)
        kinds = [a["kind"] for a in got["alerts"]]
        self.assertIn("broker_error", kinds, got)
        self.assertIn("AttributeError", json.dumps(got["alerts"]))

    def test_the_orders_carry_the_owned_namespace(self):
        sess = RecordedAlpaca()
        LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                    client=broker(sess), equity=1000.0, marks=MARKS, root=self.root, send=True)
        for body in sess.placed:
            self.assertTrue(body["client_order_id"].startswith("valquo-paper-"), body)

    def test_a_rejection_is_an_alert_and_not_a_crash(self):
        sess = RecordedAlpaca(reject=True)
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True)
        self.assertIn("broker_error", [a["kind"] for a in got["alerts"]])
        self.assertEqual(len(sess.placed), 2, "both orders should still be attempted")

    def test_the_real_broker_still_refuses_a_market_order(self):
        """Delegation must not have widened anything: `place_equity`'s limit-only rule is §8's
        and it applies to the new name unchanged."""
        res = broker(RecordedAlpaca()).place_limit("AAPL", "buy", 1.0, None)
        self.assertFalse(res["ok"])
        self.assertIn("limit price is required", res["reason"])

    def test_the_real_broker_still_refuses_a_bad_side(self):
        res = broker(RecordedAlpaca()).place_limit("AAPL", "sideways", 1.0, 10.0)
        self.assertFalse(res["ok"])


# ----------------------------------------------------------------------------------------- #
# BLOCKER 2
# ----------------------------------------------------------------------------------------- #
class TheDuplicateBuyInIsClosed(_Tmp):
    """**THE AUDITOR'S OWN REPRODUCTION, AS A TEST.** Each of these failed on the old code.

        slot_record={}            vs broker AAPL=100 -> ok: True   problems: []   <- the hole
        slot_record={AAPL: 50.0}  vs broker AAPL=100 -> ok: False  problems: [...]
    """

    def _pf(self, **kw):
        base = dict(book=BOOK, equity=1000.0, marks=MARKS, pct=10.0)
        base.update(kw)
        return LS.preflight(**base)

    def test_an_EMPTY_record_against_a_holding_broker_REFUSES(self):
        got = self._pf(slot_record={},
                       broker_positions=[{"ticker": "AAPL", "qty": 100.0}],
                       slot_symbols=["AAPL"])
        self.assertFalse(got["ok"], "THE DUPLICATE BUY-IN IS STILL REACHABLE")
        self.assertIn("buy the position a second time", got["reason"])

    def test_a_WRONG_record_still_refuses(self):
        """The direction that already worked must keep working."""
        got = self._pf(slot_record={"AAPL": 50.0},
                       broker_positions=[{"ticker": "AAPL", "qty": 100.0}],
                       slot_symbols=["AAPL"])
        self.assertFalse(got["ok"])

    def test_DONS_OWN_UNRELATED_HOLDINGS_DO_NOT_REFUSE(self):
        """**THE SCOPE, AND WITHOUT IT THE FIX WOULD BRICK THE SLOT.** `reconcile` promises
        Don's other holdings are never read into the record and therefore can never be traded.
        Refusing on them would mean a slot never trades in an account that holds anything
        else -- `MA21`'s cry-wolf direction, and the fix would be switched off within a week."""
        got = self._pf(slot_record={}, slot_symbols=["AAPL"],
                       broker_positions=[{"ticker": "TSLA", "qty": 500.0},
                                         {"ticker": "BRK.B", "qty": 3.0}])
        self.assertTrue(got["ok"], got["reason"])

    def test_an_agreeing_record_passes(self):
        got = self._pf(slot_record={"AAPL": 100.0},
                       broker_positions=[{"ticker": "AAPL", "qty": 100.0}],
                       slot_symbols=["AAPL"])
        self.assertTrue(got["ok"], got["reason"])

    def test_a_ZERO_broker_position_is_not_a_problem(self):
        """A closed position reads as qty 0 rather than vanishing on some paths."""
        got = self._pf(slot_record={}, slot_symbols=["AAPL"],
                       broker_positions=[{"ticker": "AAPL", "qty": 0.0}])
        self.assertTrue(got["ok"], got["reason"])

    def test_END_TO_END_the_second_full_buy_in_does_not_transmit(self):
        """**THE AUDITOR'S END-TO-END CASE.** The broker holds the whole book, the state file is
        absent, and the old code transmitted a second full buy-in."""
        sess = RecordedAlpaca(
            positions=[{"symbol": "AAPL", "qty": "6", "avg_entry_price": "100",
                        "market_value": "600", "side": "long"},
                       {"symbol": "MSFT", "qty": "2", "avg_entry_price": "200",
                        "market_value": "400", "side": "long"}],
            orders=[{"client_order_id": "valquo-paper-rebalance:2026-10-22-AAPL",
                     "symbol": "AAPL", "filled_qty": "6", "side": "buy", "status": "filled",
                     "limit_price": "100", "filled_avg_price": "100"},
                    {"client_order_id": "valquo-paper-rebalance:2026-10-22-MSFT",
                     "symbol": "MSFT", "filled_qty": "2", "side": "buy", "status": "filled",
                     "limit_price": "200", "filled_avg_price": "200"}])
        self.assertFalse(os.path.exists(LC.state_path(LC.PAPER_SLOT, self.root)),
                         "the fixture must start with NO state file")
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True)
        self.assertEqual(sess.placed, [], "A SECOND FULL BUY-IN WAS TRANSMITTED")
        self.assertIn("targets are already met", got["reason"])


class EveryStateWriteIsRead(_Tmp):
    """`write_state`'s return was discarded at both call sites, and a failed write produces
    exactly the empty record the hole above needs."""

    def test_a_failed_write_BEFORE_sending_means_NO_ORDERS(self):
        sess = RecordedAlpaca()
        orig = LC.write_state
        LC.write_state = lambda *a, **k: {"ok": False, "reason": "the disk is read-only"}
        try:
            got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                              client=broker(sess), equity=1000.0, marks=MARKS,
                              root=self.root, send=True)
        finally:
            LC.write_state = orig
        self.assertEqual(sess.placed, [], "orders went out with no record of them")
        self.assertIn("state_write_failed", [a["kind"] for a in got["alerts"]])
        self.assertIn("bought twice", json.dumps(got["alerts"]))

    def test_the_INTENT_is_written_before_the_orders_are_sent(self):
        """Order matters, not merely presence: a record written afterwards is no record at all
        if the process dies mid-send."""
        sess = RecordedAlpaca()
        seen = {}
        orig = LC.write_state

        def spy(slot, state, root=None):
            seen.setdefault("placed_at_write", len(sess.placed))
            seen["intent"] = (state.get("intent") or {}).get("orders")
            return orig(slot, state, root)
        LC.write_state = spy
        try:
            LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                        client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                        send=True)
        finally:
            LC.write_state = orig
        self.assertEqual(seen.get("placed_at_write"), 0,
                         "the first state write happened AFTER an order was sent")
        self.assertEqual(len(seen.get("intent") or []), 2, seen)

    def test_a_failed_write_AFTER_sending_alerts(self):
        """There is nothing to undo once an order is out, so this cannot refuse -- it must be
        loud instead, naming what could not be recorded."""
        out = {}
        LC._note_write(out, {"ok": False, "reason": "disk full"}, "1", "recording a send")
        self.assertIn("state_write_failed", [a["kind"] for a in out["alerts"]])
        self.assertTrue(out["state_write_failed"])

    def test_the_intent_survives_into_the_slot_symbol_scope(self):
        """An intent recorded and then a crash is the case the scope must cover: the slot may
        have sent those names, so a broker position in one of them is attributable to it."""
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"slot": LC.PAPER_SLOT, "holdings": {}, "processed": [],
                       "intent": {"event": "rebalance:2026-10-22",
                                  "orders": [{"ticker": "AAPL"}]}}, fh)
        sess = RecordedAlpaca(positions=[{"symbol": "AAPL", "qty": "6",
                                          "avg_entry_price": "100", "side": "long"}])
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True)
        self.assertIn("AAPL", got["slot_symbols"])
        self.assertEqual(sess.placed, [], "it sent orders despite an unrecorded position")
        self.assertFalse(got["preflight"]["ok"])


# ----------------------------------------------------------------------------------------- #
# FAILED QUESTION 7
# ----------------------------------------------------------------------------------------- #
class AnUnreadablePositionListRefuses(_Tmp):
    def test_positions_that_could_not_be_read_REFUSE(self):
        got = LS.preflight(book=BOOK, equity=1000.0, marks=MARKS, pct=10.0,
                           slot_record={}, broker_positions=None)
        self.assertFalse(got["ok"])
        self.assertIn("could not be read", got["reason"])

    def test_NOT_SUPPLIED_is_a_different_fact_and_does_not_refuse(self):
        """`None` cannot carry both "no broker was consulted" and "the broker would not
        answer". A dry run has no client at all and must still be able to compute a plan."""
        got = LS.preflight(book=BOOK, equity=1000.0, marks=MARKS, pct=10.0, slot_record={})
        self.assertTrue(got["ok"], got["reason"])
        self.assertFalse(got["positions_checked"])

    def test_END_TO_END_a_broker_whose_positions_raise_sends_nothing(self):
        class Blind(RecordedAlpaca):
            pass
        sess = Blind()
        b = broker(sess)
        b.positions = lambda: (_ for _ in ()).throw(RuntimeError("positions are down"))
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=b, equity=1000.0, marks=MARKS, root=self.root, send=True)
        self.assertEqual(sess.placed, [])
        self.assertIsNone(got["broker_positions_read"])
        self.assertIn("could not be read", got["reason"])

    def test_a_dry_run_still_computes_its_plan(self):
        """THE POSITIVE CONTROL for the two above: if a no-client slot refused, every one of
        them would pass while measuring nothing."""
        got = LC.run_slot("1", pct=10.0, armed_state=ARMED, book=BOOK, client=None,
                          equity=1000.0, marks=MARKS, root=self.root, send=False,
                          paper_targets={"AAPL": 60.0, "MSFT": 40.0}, paper_value=100.0)
        self.assertTrue(got["orders"], got["reason"])
        self.assertEqual(got["broker_positions_read"], "not_supplied")


# ----------------------------------------------------------------------------------------- #
# FAILED QUESTION 2
# ----------------------------------------------------------------------------------------- #
class ParityBlocksALiveSend(_Tmp):
    def _live(self, **kw):
        base = dict(pct=10.0, armed_state=ARMED, book=BOOK, equity=1000.0, marks=MARKS,
                    root=self.root, send=True)
        base.update(kw)
        return LC.run_slot("1", **base)

    def test_a_MISMATCH_sends_nothing(self):
        sess = RecordedAlpaca()
        got = self._live(client=broker(sess),
                         paper_targets={"AAPL": 10.0, "MSFT": 90.0}, paper_value=100.0)
        self.assertEqual(sess.placed, [], "a parity mismatch still transmitted")
        self.assertFalse(got["parity"]["ok"])
        self.assertIn("parity_mismatch", [a["kind"] for a in got["alerts"]])
        self.assertIn("sends NOTHING", got["reason"])

    def test_an_ABSENT_parity_sends_nothing(self):
        """The cycle where the paper side is down was the cycle with no comparison at all."""
        sess = RecordedAlpaca()
        got = self._live(client=broker(sess), paper_targets=None, paper_value=None)
        self.assertEqual(sess.placed, [])
        self.assertFalse(got["parity"]["measured"])
        self.assertIn("parity_absent", [a["kind"] for a in got["alerts"]])

    def test_a_MATCH_does_send(self):
        """THE POSITIVE CONTROL. Two refusals above prove nothing if the slot can never send."""
        sess = RecordedAlpaca()
        got = self._live(client=broker(sess),
                         paper_targets={"AAPL": 60.0, "MSFT": 40.0}, paper_value=100.0)
        self.assertTrue(got["parity"]["ok"], got["parity"]["reason"])
        self.assertEqual(len(sess.placed), 2, got["reason"])

    def test_THE_PAPER_SLOT_IS_NEVER_GATED_ON_PARITY(self):
        """It is the thing being compared against. Gating it would stop the mechanism that
        produces the comparison, and §8's whole premise is that the paper slot runs first."""
        sess = RecordedAlpaca()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True, paper_targets=None)
        self.assertTrue(got["acted"], got["reason"])
        self.assertEqual(len(sess.placed), 2)

    def test_parity_compares_TARGETS_and_the_source_says_so(self):
        src = open(LC.__file__, encoding="utf-8").read()
        fn = src[src.index("def parity("):]
        fn = fn[:fn.index("def reconcile(")]
        self.assertIn("live_targets", fn)
        self.assertNotIn("live_plan", fn, "parity still diffs order plans")


# ----------------------------------------------------------------------------------------- #
# the recommendations
# ----------------------------------------------------------------------------------------- #
class TheAccountIdIsRecordedAndPinned(_Tmp):
    """The host check cannot see the real residual risk: THE WRONG KEYS BEHIND THE RIGHT HOST."""

    def test_the_first_armed_cycle_records_it(self):
        sess = RecordedAlpaca()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True, account_id="acct-A")
        self.assertEqual(got["account_id"], "acct-A")
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertEqual(st["account_id"], "acct-A")

    def test_a_CHANGED_account_id_refuses_and_overwrites_nothing(self):
        sess = RecordedAlpaca()
        LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                    client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                    send=True, account_id="acct-A")
        sess2 = RecordedAlpaca()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess2), equity=1000.0, marks=MARKS, root=self.root,
                          send=True, account_id="acct-B")
        self.assertEqual(sess2.placed, [], "it traded an account it has no record of")
        self.assertIn("account_changed", [a["kind"] for a in got["alerts"]])
        self.assertEqual(LC.read_state(LC.PAPER_SLOT, self.root)["account_id"], "acct-A")

    def test_no_account_id_supplied_changes_nothing(self):
        """Backwards compatible: a caller that cannot read an id is not thereby blocked."""
        sess = RecordedAlpaca()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True)
        self.assertTrue(got["acted"], got["reason"])

    def test_the_paper_broker_reports_its_account_id(self):
        acct = broker(RecordedAlpaca(account_id="acct-paper-9")).account()
        self.assertEqual(acct["account_id"], "acct-paper-9")
        self.assertEqual(acct["account_number"], "PA123456")


class TheRetryCeilingStopsASilentLoop(_Tmp):
    """`live_notify` dedupes on `(kind, slot, event, reason[:120])`, so a permanently-rejecting
    condition is announced ONCE and retried into silence for ever."""

    def test_it_stops_after_the_declared_number_of_attempts(self):
        self.assertEqual(LC.MAX_EVENT_ATTEMPTS, 5)
        placed_each = []
        for _ in range(LC.MAX_EVENT_ATTEMPTS + 2):
            sess = RecordedAlpaca(reject=True)
            got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                              client=broker(sess), equity=1000.0, marks=MARKS,
                              root=self.root, send=True)
            placed_each.append(len(sess.placed))
        self.assertEqual(placed_each[:LC.MAX_EVENT_ATTEMPTS],
                         [2] * LC.MAX_EVENT_ATTEMPTS, placed_each)
        self.assertEqual(placed_each[LC.MAX_EVENT_ATTEMPTS:], [0, 0], placed_each)
        self.assertIn("event_attempts_exhausted", [a["kind"] for a in got["alerts"]])
        self.assertTrue(got["attempts_exhausted"])

    def test_the_alert_says_WHY_it_stopped(self):
        st = {"slot": LC.PAPER_SLOT, "holdings": {}, "processed": [],
              "event_attempts": {"rebalance:2026-10-22": 99}}
        p = LC.state_path(LC.PAPER_SLOT, self.root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(RecordedAlpaca()), equity=1000.0, marks=MARKS,
                          root=self.root, send=True)
        self.assertIn("deduped into silence", got["reason"])


class TheFeedGapHasADenominator(_Tmp):
    def test_an_unfilled_count_with_no_attempts_is_NOT_a_rate_of_zero(self):
        LC.record_feed_gap([], self.root, unfilled=3, attempts=0)
        rep = LC.feed_gap_report(self.root)
        self.assertEqual(rep["n_unfilled"], 3)
        self.assertIsNone(rep["unfilled_rate"])
        self.assertIn("NOT a rate of zero", rep["unfilled_rate_note"])

    def test_with_attempts_it_is_a_rate(self):
        LC.record_feed_gap([], self.root, unfilled=3, attempts=12)
        rep = LC.feed_gap_report(self.root)
        self.assertAlmostEqual(rep["unfilled_rate"], 0.25)
        self.assertIn("3 of 12", rep["unfilled_rate_note"])

    def test_the_underlying_question_is_reported_NOT_MEASURED(self):
        LC.record_feed_gap([{"ticker": "A", "kind": "stock", "mid": 10.0, "fill": 9.9,
                             "side": "buy", "order_id": "x"}], self.root, attempts=1)
        cen = LC.feed_gap_report(self.root)["censoring"]
        self.assertIn("NOT MEASURED", cen["underlying_question"])
        self.assertTrue(cen["price_gap_is_one_sided"])


class TheOrderIdNamespaceIsOwned(unittest.TestCase):
    def test_one_definition_for_the_writer_and_the_reader(self):
        self.assertTrue(LC.client_order_id(1, "e", "AAPL").startswith(LC.coid_prefix(1)))

    def test_a_manual_order_cannot_be_absorbed(self):
        """Before this the prefix was `"1-"`, safe against Alpaca's UUID ids only by accident
        -- an order a human tagged `1-whatever` would have been absorbed into the slot's
        holdings and could then have been SOLD by it."""
        class C:
            def orders(self, **k):
                return [{"client_order_id": "1-handplaced-AAPL", "symbol": "AAPL",
                         "filled_qty": "5", "side": "buy", "status": "filled"}]
        got = LC.reconcile(C(), {"slot": "1"})
        self.assertEqual(got["holdings"], {}, "a manual order was absorbed")

    def test_slot_1_does_not_match_slot_11(self):
        self.assertFalse(LC.client_order_id(11, "e", "A").startswith(LC.coid_prefix(1)))

    def test_the_paper_slot_cannot_collide_with_a_numbered_slot(self):
        self.assertFalse(LC.coid_prefix("paper")[len("valquo-")].isdigit())

    def test_a_state_with_no_slot_REFUSES_rather_than_reconciling_nothing(self):
        """The old prefix was the bare `"-"`, which matches no id -- so it returned an EMPTY
        book and reported success, indistinguishable from "this slot holds nothing"."""
        class C:
            def orders(self, **k):
                return [{"client_order_id": "valquo-1-e-AAPL", "symbol": "AAPL",
                         "filled_qty": "5", "side": "buy", "status": "filled"}]
        got = LC.reconcile(C(), {})
        self.assertFalse(got["ok"])
        self.assertIn("no slot number", got["reason"])


class TheOrderWindowCannotSilentlyTruncate(_Tmp):
    """86 names exceeds the 100-order default from the second rebalance on. The auditor
    measured 172 orders at the broker, 100 seen, 72 of 86 names under-counted by half."""

    def test_the_page_limit_is_raised_and_declared(self):
        self.assertEqual(LC.ORDERS_PAGE_LIMIT, 500)

    def test_a_FULL_page_is_a_refusal_and_not_an_under_count(self):
        class Full:
            def orders(self, limit=100, **k):
                return [{"client_order_id": "valquo-1-e-A", "symbol": "A",
                         "filled_qty": "1", "side": "buy", "status": "filled"}] * limit
        got = LC.reconcile(Full(), {"slot": "1"})
        self.assertTrue(got["truncated"])
        self.assertFalse(got["ok"])

    def test_a_truncated_reconcile_stops_the_cycle(self):
        class Full(RecordedAlpaca):
            def request(self, method, url, **k):
                if url.endswith("/v2/orders") and method == "GET":
                    return Reply([{"client_order_id": "valquo-paper-e-A", "symbol": "A",
                                   "filled_qty": "1", "side": "buy", "status": "filled"}]
                                 * LC.ORDERS_PAGE_LIMIT)
                return super().request(method, url, **k)
        sess = Full()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=ARMED, book=BOOK,
                          client=broker(sess), equity=1000.0, marks=MARKS, root=self.root,
                          send=True)
        self.assertEqual(sess.placed, [])
        self.assertIn("reconcile_truncated", [a["kind"] for a in got["alerts"]])

    def test_a_SHORT_page_is_not_truncated(self):
        """THE POSITIVE CONTROL: if every page read as truncated the slot would never trade."""
        class Few:
            def orders(self, limit=100, **k):
                return [{"client_order_id": "valquo-1-e-A", "symbol": "A",
                         "filled_qty": "1", "side": "buy", "status": "filled"}]
        got = LC.reconcile(Few(), {"slot": "1"})
        self.assertFalse(got["truncated"])
        self.assertTrue(got["ok"])


class TheScheduledWorkflowCannotCarryTheLiveToken(unittest.TestCase):
    """The auditor's #12. An installed copy now exists beside the pending one and they drift."""

    def _copies(self):
        out = {}
        for rel in ("pending_workflows/live-cycle.yml", ".github/workflows/live-cycle.yml"):
            p = os.path.join(REPO, rel)
            if os.path.exists(p):
                out[rel] = open(p, encoding="utf-8", errors="replace").read()
        return out

    def test_at_least_one_copy_is_present(self):
        self.assertTrue(self._copies(), "neither copy of live-cycle.yml was found")

    def test_no_copy_requests_the_LIVE_token(self):
        for rel, body in self._copies().items():
            code = "\n".join(ln.split("#", 1)[0] for ln in body.splitlines())
            self.assertNotIn("run=1", code, "%s requests a LIVE send" % rel)
            self.assertIn("run=paper", code, "%s does not request a paper send" % rel)

    def test_the_two_copies_do_not_drift(self):
        c = self._copies()
        if len(c) == 2:
            a, b = list(c.values())
            self.assertEqual(a.replace("\r\n", "\n"), b.replace("\r\n", "\n"),
                             "the installed workflow differs from the reviewed one")

    def test_the_credential_guard_reads_a_SHAPE_and_not_the_vendor_name(self):
        """Confirming item 62's repair, which the auditor asked to be verified: the guard must
        not fire on a comment that merely names Alpaca."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "t58_for_63", os.path.join(REPO, "tests", "test_item58.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        g = m.B_Separation._names_a_credential
        self.assertFalse(g("# the Alpaca PAPER client places this order\n"))
        self.assertTrue(g("  value: ${{ secrets.ALPACA_API_KEY_ID }}\n"))


class TheDocstringOverstatementsAreCorrected(unittest.TestCase):
    """The auditor's #13. A false docstring is worse than none: the empty-record default was
    defended by a claim about `preflight` that was not true when it was written."""

    def test_read_state_no_longer_claims_preflight_catches_an_empty_record(self):
        doc = LC.read_state.__doc__ or ""
        self.assertIn("CORRECTED", doc)
        self.assertIn("FALSE", doc)

    def test_the_mark_is_described_as_setting_the_SIZE_too(self):
        for mod in (LC, LS):
            src = open(mod.__file__, encoding="utf-8").read()
            self.assertNotIn("A price is read to set a limit, never to decide.", src,
                             "%s still says the mark only sets the limit" % mod.__name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
