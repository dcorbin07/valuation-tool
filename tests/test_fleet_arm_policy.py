"""F-1 ARMED — the harness's order door, and the frozen arm policy it executes.

F-1's declaration says *"No entries of its own. **Every order any fleet book submits** is
assigned by the harness's deterministic randomizer to arm A (marketable) or arm B (limit at
mid, worked 60s, then cancel-and-market ...)"*. So the policy is a property of the SUBMISSION
PATH, not of a per-book callable — F-1's own rule could never reach the orders of books that
are not F-1 — and these pin it there.

WHAT EACH GROUP EXISTS FOR:

  * **THE ARMS DO WHAT THEY SAY.** A is marketable, B is a limit priced at the mid. If arm B
    ever placed a market order the book would measure nothing and still report a verdict.
  * **THE FALLBACK VOCABULARY STAYS SEPARATE.** `""`, `B-fallback`, `B-nomid` and
    `B-cancel-failed` are four different observations. The draft's own rule is that a
    fallback fill is *"never silently pooled"*, and the fallback-drag term is what decides the
    `B-COSTS` verdict — pooling any two of them biases exactly that.
  * **THE DOUBLE POSITION IS THE ONE THAT CORRUPTS THE MEASUREMENT.** If the cancel fails and
    the market leg goes anyway, the book holds twice the size it recorded, on the one book
    whose entire subject is fill quality. Pinned hard: the broker must see NO second order.
  * **A RIDER IS NOT A BREATHING FLEET.** `cycle()` must not report the fleet as trading on
    the strength of a book that declared it never trades.

    python tests/test_fleet_arm_policy.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F              # noqa: E402
from valuation.edge import fleet_books as FB       # noqa: E402
# The real temp-git-repo fixtures, reused rather than rebuilt: a second copy of a fixture
# drifts from the first exactly as a second copy of a fact does (`MA5`).
from test_fleet_harness import _repo, _seed_selfcheck   # noqa: E402

_F1_TEXT = io.open(os.path.join(REPO, "DECL_f1_fill_ab.md"), encoding="utf-8").read()

SHA = "a" * 64
TWO_SIDED = {"bid": 1.00, "ask": 1.20}          # mid 1.10
ONE_SIDED = {"bid": 1.00, "ask": None}


def _order(status="filled", avg=1.10, execd=1, qty=1, oid="1"):
    return {"id": oid, "status": status, "avg_fill_price": avg,
            "exec_quantity": execd, "quantity": qty}


class FakeBroker:
    """Records what was asked of it. A test that cannot see the SECOND order cannot pin
    the double-position case, which is the one failure that silently corrupts the book."""

    def __init__(self, order_seq):
        self.order_seq = list(order_seq)      # what broker.order(oid) returns, in turn
        self.placed = []                      # (occ, side, qty, price)
        self.cancels = []
        self.cancel_ok = True
        self._i = 0

    def place_option(self, occ, underlying, side, qty, price=None, duration="day"):
        self.placed.append({"occ": occ, "side": side, "qty": qty, "price": price})
        return {"order": {"id": str(len(self.placed))}, "ok": True}

    def order(self, oid):
        o = self.order_seq[min(self._i, len(self.order_seq) - 1)]
        self._i += 1
        return o

    def cancel(self, oid):
        self.cancels.append(oid)
        return {"ok": bool(self.cancel_ok)}

    def quotes(self, syms):
        return {s: TWO_SIDED for s in syms}


def _arm_forcing(want):
    """A (book, symbol) pair that `fleet.arm` puts in the wanted arm. Found, never faked:
    the randomizer is the object under test and stubbing it would test the stub."""
    for i in range(2000):
        sym = "T%d" % i
        if F.arm("bk", "2026-08-24", sym, SHA) == want:
            return sym
    raise AssertionError("no symbol landed in arm " + want)


def _submit(broker, *, want_arm, quote=TWO_SIDED, work=60, clock=None):
    sym = _arm_forcing(want_arm)
    return F.submit("bk", broker=broker, occ=sym + "260101C00001000", underlying=sym,
                    side="buy_to_open", qty=1, decl_sha=SHA, symbol=sym,
                    date="2026-08-24", quote=quote, work_seconds=work,
                    clock=clock, sleep=lambda s: None,
                    now=lambda: "2026-08-24T16:00:00")


class TheArms(unittest.TestCase):

    def test_arm_A_is_marketable(self):
        b = FakeBroker([_order()])
        kw = _submit(b, want_arm="A")
        self.assertEqual(kw["arm"], "A")
        self.assertEqual(kw["order_type"], "market")
        self.assertEqual(len(b.placed), 1)
        self.assertIsNone(b.placed[0]["price"], "arm A must not carry a limit price")
        self.assertEqual(kw["fallback"], "")

    def test_arm_B_is_a_limit_priced_at_the_mid(self):
        b = FakeBroker([_order()])
        kw = _submit(b, want_arm="B")
        self.assertEqual(kw["arm"], "B")
        self.assertEqual(kw["order_type"], "limit")
        self.assertEqual(b.placed[0]["price"], 1.10)
        self.assertEqual(kw["limit_price"], 1.10)
        self.assertEqual(kw["fallback"], "", "a clean B fill carries no fallback flag")
        self.assertEqual(b.cancels, [], "a filled limit is never cancelled")

    def test_the_limit_price_IS_the_recorded_mid(self):
        """B7. A book measuring half-spread capture cannot price by one convention and
        record by another, so both come from `quote_mid` and this pins them equal."""
        b = FakeBroker([_order()])
        kw = _submit(b, want_arm="B")
        rec = F.fill_fields(**kw)
        self.assertEqual(rec["quote_mid"], F.quote_mid(TWO_SIDED))
        self.assertEqual(kw["limit_price"], rec["quote_mid"])


class TheFallbackVocabulary(unittest.TestCase):

    def test_an_unfilled_B_is_cancelled_then_marketed_and_FLAGGED(self):
        b = FakeBroker([_order(status="open", avg=0.0, execd=0),
                        _order(status="open", avg=0.0, execd=0),
                        _order()])
        ticks = iter([0.0, 100.0, 100.0, 100.0])
        kw = _submit(b, want_arm="B", clock=lambda: next(ticks))
        self.assertEqual(kw["fallback"], "B-fallback")
        self.assertEqual(len(b.cancels), 1, "the limit must be withdrawn before the market leg")
        self.assertEqual(len(b.placed), 2)
        self.assertIsNone(b.placed[1]["price"], "the fallback leg is marketable")
        self.assertEqual(kw["limit_price"], 1.10, "the limit it worked stays on the record")

    def test_a_one_sided_quote_gets_its_OWN_fallback_value(self):
        """Amendment 1. "B could not be attempted" and "B did not fill" are different
        observations, and only the second is evidence about working a limit."""
        b = FakeBroker([_order()])
        kw = _submit(b, want_arm="B", quote=ONE_SIDED)
        self.assertEqual(kw["fallback"], "B-nomid")
        self.assertEqual(kw["order_type"], "market")
        self.assertIsNone(b.placed[0]["price"])
        self.assertNotEqual(kw["fallback"], "B-fallback", "the two must never pool")

    def test_the_four_fallback_values_are_distinct(self):
        seen = set()
        b = FakeBroker([_order()])
        seen.add(_submit(b, want_arm="A")["fallback"])
        b = FakeBroker([_order()])
        seen.add(_submit(b, want_arm="B")["fallback"])
        b = FakeBroker([_order()])
        seen.add(_submit(b, want_arm="B", quote=ONE_SIDED)["fallback"])
        b = FakeBroker([_order(status="open", avg=0.0, execd=0)] * 3)
        ticks = iter([0.0, 100.0, 100.0, 100.0])
        seen.add(_submit(b, want_arm="B", clock=lambda: next(ticks))["fallback"])
        b = FakeBroker([_order(status="open", avg=0.0, execd=0)] * 3)
        b.cancel_ok = False
        ticks = iter([0.0, 100.0, 100.0, 100.0])
        seen.add(_submit(b, want_arm="B", clock=lambda: next(ticks))["fallback"])
        self.assertEqual(len(seen), 4, sorted(seen))


class TheDoublePosition(unittest.TestCase):

    def test_a_FAILED_cancel_sends_NO_market_leg(self):
        """The one failure that corrupts rather than merely misses.

        A live limit plus a market order beside it is twice the declared size, on the book
        whose subject is fill quality. An unfilled order is an observation; a doubled one is
        a corrupted measurement.
        """
        b = FakeBroker([_order(status="open", avg=0.0, execd=0)] * 3)
        b.cancel_ok = False
        ticks = iter([0.0, 100.0, 100.0, 100.0])
        kw = _submit(b, want_arm="B", clock=lambda: next(ticks))
        self.assertEqual(kw["fallback"], "B-cancel-failed")
        self.assertEqual(len(b.cancels), 1, "it must have TRIED to cancel")
        self.assertEqual(len(b.placed), 1, "NO second order may reach the broker")
        self.assertEqual(kw["order_type"], "limit")

    def test_the_unfilled_record_reports_an_unfilled_FATE(self):
        """`fill_fields` reads the fate from the broker's state. A pending order recorded as
        a fill at its own limit is the corruption this book could least afford."""
        b = FakeBroker([_order(status="open", avg=0.0, execd=0)] * 3)
        b.cancel_ok = False
        ticks = iter([0.0, 100.0, 100.0, 100.0])
        rec = F.fill_fields(**_submit(b, want_arm="B", clock=lambda: next(ticks)))
        self.assertEqual(rec["fill_price"], "")
        self.assertNotEqual(rec["fate"], "filled")


class TheRiderDistinction(unittest.TestCase):

    def test_f1_places_nothing_by_its_own_declaration(self):
        FB.register_all()
        self.assertEqual(FB.f1_fill_ab({}, None), [])
        self.assertFalse(F.places_orders("f1_fill_ab"))

    def test_an_unregistered_book_is_not_silently_a_rider(self):
        """Defaulting to `places_orders=False` would make every un-armed book look like a
        gate, which is the blur `ARMED_NO_ENTRY_RULE` exists to prevent one level up."""
        self.assertTrue(F.places_orders("no_such_book_at_all"))

    def test_a_cycle_in_which_only_a_RIDER_ran_is_NOT_breathing(self):
        """END TO END through the real gate, not past it.

        The first cut of this test asserted `RAN_RIDER` against the live repo root and got
        `SELFCHECK_ABSENT` -- **the harness refusing correctly**, because `cycle()` runs
        `may_fill` before it reaches any rule and no book has run its day-1 gate here. That is
        a real property worth pinning rather than stepping around: **a rider is gated too**,
        so `RAN_RIDER` is unreachable until the self-check passes, and on the live service
        every book will read `SELFCHECK_ABSENT` until day-1 runs there.
        """
        FB.register_all()
        root = _repo(book="f1_fill_ab", text=_F1_TEXT)
        try:
            blocked = F.cycle(root, write=False)
            self.assertEqual(blocked["books"][0]["state"], "SELFCHECK_ABSENT")
            self.assertFalse(blocked["breathing"])

            _seed_selfcheck(root, "f1_fill_ab")
            out = F.cycle(root, write=False)
            states = {r["book"]: r["state"] for r in out["books"] if r.get("is_book")}
            self.assertEqual(states.get("f1_fill_ab"), "RAN_RIDER")
            self.assertIn("f1_fill_ab", out["riders_ran"])
            self.assertFalse(out["breathing"],
                             "a gate that ran is not a fleet that traded")
            self.assertEqual(out["fills_written"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_rider_is_still_counted_as_IMPLEMENTED(self):
        """It is built. Reporting it as un-armed would understate the work and re-open a
        book that is finished."""
        FB.register_all()
        root = _repo(book="f1_fill_ab", text=_F1_TEXT)
        try:
            _seed_selfcheck(root, "f1_fill_ab")
            out = F.cycle(root, write=False)
            self.assertEqual(out["entry_rules_implemented"], 1)
            self.assertNotIn("f1_fill_ab", out["books_with_no_entry_rule"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TheDeterminism(unittest.TestCase):

    def test_the_same_order_always_lands_in_the_same_arm(self):
        a = [F.arm("bk", "2026-08-24", "AAPL", SHA) for _ in range(5)]
        self.assertEqual(len(set(a)), 1)

    def test_changing_the_declaration_hash_can_change_the_arm(self):
        """Salted by the declaration, so the split is fixed the moment it lands and
        re-rolling requires changing a committed file."""
        diff = sum(1 for i in range(200)
                   if F.arm("bk", "2026-08-24", "T%d" % i, SHA)
                   != F.arm("bk", "2026-08-24", "T%d" % i, "b" * 64))
        self.assertGreater(diff, 20, "the salt does not reach the assignment")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
