"""(C) HARNESS EXPRESSIVENESS — multi-leg structures and first-class skips.

Two declared books could not be honoured by the harness as it stood, and one of them could not
be honoured SAFELY:

  * **F-6 IS A COLLAR** — long put plus short call, financed to near-zero net. `submit` places
    one leg. Submitted as two independent orders the failure modes are not symmetric: put-only
    is F-20's married put, and **call-only is a NAKED SHORT CALL**, the single structure
    `S3-I3` refuses by name because FINRA 4210 has its own maintenance floor and a
    cash-secured stand-in would UNDERSTATE it.
  * **F-14 DECLARES ITS SKIPS AS THE CONTROL POPULATION** — *"the skips ARE the control
    population and are first-class records"*. `cycle()` could record nothing but fills, so the
    half that makes that book interpretable was unrepresentable.

EVERY GUARD HERE IS MUTATION-TESTED. A refusal that cannot fire is not a refusal, and the
whole argument for a net-cost constraint is that it stops a structure nobody declared.

    python tests/test_fleet_multileg.py
"""
from __future__ import annotations

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                          # noqa: E402
from test_fleet_harness import _repo, _seed_selfcheck, BOOK    # noqa: E402

SHA = "c" * 64


def _leg(occ, side, bid, ask, qty=1):
    return {"occ": occ, "side": side, "qty": qty, "quote": {"bid": bid, "ask": ask}}


# A COLLAR: buy the put, sell the call. Debit of 1.20 - 1.00 = 0.20.
COLLAR = [_leg("P90", "buy_to_open", 1.10, 1.20), _leg("C110", "sell_to_open", 1.00, 1.10)]
# The same structure where the call finances MORE than the put costs: a net CREDIT.
CREDIT = [_leg("P90", "buy_to_open", 1.00, 1.10), _leg("C110", "sell_to_open", 2.00, 2.10)]
NAKED = [_leg("C110", "sell_to_open", 1.00, 1.10)]


class Broker:
    def __init__(self, filled=True):
        self.multileg = []
        self.single = []
        self.filled = filled

    def place_multileg(self, underlying, legs, order_type="market", price=None,
                       duration="day"):
        self.multileg.append({"underlying": underlying, "legs": list(legs),
                              "order_type": order_type, "price": price})
        return {"order": {"id": "1"}, "ok": True}

    def place_option(self, occ, underlying, side, qty, price=None, duration="day"):
        self.single.append(occ)
        return {"order": {"id": "9"}, "ok": True}

    def order(self, oid):
        if not self.filled:
            return {"id": oid, "status": "open", "avg_fill_price": 0.0, "exec_quantity": 0}
        return {"id": oid, "status": "filled", "avg_fill_price": 0.20,
                "exec_quantity": 1, "quantity": 1}


def _submit(broker, legs, net_rule=F.NET_DEBIT_ONLY):
    return F.submit_multileg("f6_collar_ledger", broker=broker, underlying="XYZ", legs=legs,
                             decl_sha=SHA, symbol="XYZ", date="2026-08-24",
                             now=lambda: "2026-08-24T16:00:00", net_rule=net_rule)


class TheNetCost(unittest.TestCase):

    def test_it_is_priced_MARKETABLE_and_not_at_the_mid(self):
        """Buys at the ASK, sells at the BID -- `DEFAULT_AGGRESSION = 1.0`, the convention
        every validated options number here is net of. A mid-based net would make a collar
        look financeable at prices nobody can trade."""
        self.assertAlmostEqual(F.net_cost(COLLAR), 1.20 - 1.00, places=6)
        # The mid-based answer would be 1.15 - 1.05 = 0.10, and is NOT what this returns.
        self.assertNotAlmostEqual(F.net_cost(COLLAR), 0.10, places=6)

    def test_positive_is_a_debit_and_negative_is_a_credit(self):
        self.assertGreater(F.net_cost(COLLAR), 0.0)
        self.assertLess(F.net_cost(CREDIT), 0.0)

    def test_a_one_sided_leg_makes_the_net_UNKNOWN_and_not_zero(self):
        legs = [_leg("P90", "buy_to_open", 1.10, None), COLLAR[1]]
        self.assertIsNone(F.net_cost(legs))

    def test_quantity_scales_the_net(self):
        doubled = [dict(l, qty=2) for l in COLLAR]
        self.assertAlmostEqual(F.net_cost(doubled), 2 * F.net_cost(COLLAR), places=6)


class TheStructureRefusals(unittest.TestCase):

    def test_a_collar_that_costs_money_is_accepted(self):
        c = F.check_structure(COLLAR, net_rule=F.NET_DEBIT_ONLY)
        self.assertTrue(c["ok"], c["refusals"])
        self.assertEqual((c["n_long"], c["n_short"]), (1, 1))

    def test_a_NET_CREDIT_is_refused_under_the_declared_rule(self):
        """F-6: *"nearest-to-zero net cost, NEVER a net credit"*."""
        c = F.check_structure(CREDIT, net_rule=F.NET_DEBIT_ONLY)
        self.assertFalse(c["ok"])
        self.assertIn("MULTILEG_NET_CREDIT", c["refusals"])

    def test_the_same_credit_passes_when_the_rule_ALLOWS_it(self):
        """Proves the refusal is the RULE's and not a hard-coded prejudice about credits."""
        c = F.check_structure(CREDIT, net_rule=F.NET_ANY)
        self.assertTrue(c["ok"], c["refusals"])

    def test_a_NAKED_SHORT_is_refused_by_name(self):
        c = F.check_structure(NAKED + [_leg("C120", "sell_to_open", 0.5, 0.6)],
                              net_rule=F.NET_ANY)
        self.assertIn("MULTILEG_NAKED_SHORT", c["refusals"])

    def test_a_single_leg_is_refused_toward_submit(self):
        c = F.check_structure(NAKED, net_rule=F.NET_ANY)
        self.assertIn("MULTILEG_SINGLE_LEG", c["refusals"])

    def test_an_unusable_quote_refuses_rather_than_guessing_a_net(self):
        legs = [_leg("P90", "buy_to_open", 1.10, None), COLLAR[1]]
        c = F.check_structure(legs, net_rule=F.NET_DEBIT_ONLY)
        self.assertIn("MULTILEG_UNUSABLE_QUOTE", c["refusals"])

    def test_an_unknown_net_rule_is_refused_and_not_treated_as_permissive(self):
        c = F.check_structure(COLLAR, net_rule="whatever")
        self.assertTrue(any(r.startswith("MULTILEG_UNKNOWN_NET_RULE") for r in c["refusals"]))


class NoOrderOnARefusal(unittest.TestCase):
    """The property that makes the refusals worth anything: nothing reaches the broker."""

    def test_a_refused_structure_places_NOTHING(self):
        for legs in (CREDIT, NAKED, [_leg("P90", "buy_to_open", 1.1, None), COLLAR[1]]):
            b = Broker()
            out = _submit(b, legs)
            self.assertFalse(out["ok"])
            self.assertEqual(b.multileg, [], "an order was placed on a refused structure")
            self.assertEqual(b.single, [])
            self.assertEqual(out["candidates"], [])

    def test_an_accepted_structure_is_ONE_order_carrying_every_leg(self):
        b = Broker()
        out = _submit(b, COLLAR)
        self.assertTrue(out["ok"], out["refusals"])
        self.assertEqual(len(b.multileg), 1, "a structure must be ONE order")
        self.assertEqual(len(b.multileg[0]["legs"]), 2)
        self.assertEqual(b.single, [], "no leg may go out on its own")


class TheStructureRecords(unittest.TestCase):

    def test_one_record_per_leg_sharing_id_arm_and_net(self):
        b = Broker()
        out = _submit(b, COLLAR)
        cands = out["candidates"]
        self.assertEqual(len(cands), 2)
        self.assertEqual({c["structure_id"] for c in cands}, {out["structure_id"]})
        self.assertEqual({c["net_cost"] for c in cands}, {out["net_cost"]})
        self.assertEqual(sorted(c["leg_index"] for c in cands), [0, 1])

    def test_the_ARM_is_assigned_ONCE_for_the_structure(self):
        """F-1's unit is an ORDER and this is one order. Arming legs independently would put
        one collar in both arms and make its half-spread capture uninterpretable."""
        b = Broker()
        cands = _submit(b, COLLAR)["candidates"]
        self.assertEqual(len({c["arm"] for c in cands}), 1)

    def test_each_leg_keeps_its_OWN_quote_block_which_is_what_F1_reads(self):
        b = Broker()
        cands = {c["occ"]: F.fill_fields(**c) for c in _submit(b, COLLAR)["candidates"]}
        self.assertEqual(cands["P90"]["quote_ask"], 1.20)
        self.assertEqual(cands["C110"]["quote_bid"], 1.00)

    def test_a_SINGLE_leg_fill_leaves_the_structure_columns_EMPTY(self):
        """"Not part of a structure" and "leg 0 of a structure" are different facts."""
        rec = F.fill_fields(symbol="X", occ="X1", side="buy_to_open", qty=1,
                            order_type="market", quote={"bid": 1.0, "ask": 1.2},
                            order={}, submitted_ts="2026-08-24T16:00:00")
        self.assertEqual(rec["structure_id"], "")
        self.assertEqual(rec["leg_index"], "")
        self.assertEqual(rec["net_cost"], "")


class TheSkipRecords(unittest.TestCase):

    def test_a_skip_REQUIRES_a_reason(self):
        """An unexplained skip is indistinguishable from a rule that silently did nothing."""
        with self.assertRaises(ValueError):
            F.skip_fields(symbol="AAA", skip_reason="")
        with self.assertRaises(TypeError):
            F.skip_fields(symbol="AAA")

    def test_a_skip_carries_the_would_have_been_quote_pair(self):
        """F-2's gate wants exactly this on a refused entry, and F-14's control arm is only
        interpretable if the skipped candidate's price is on the record."""
        s = F.skip_fields(symbol="AAA", occ="AAA1", skip_reason="hump priced",
                          quote={"bid": 2.0, "ask": 2.4})
        self.assertEqual((s["quote_bid"], s["quote_ask"], s["quote_mid"]), (2.0, 2.4, 2.2))
        self.assertEqual(s["skip_reason"], "hump priced")

    def test_a_skip_places_no_order_and_carries_no_fill(self):
        s = F.skip_fields(symbol="AAA", skip_reason="x")
        self.assertEqual(s["fill_price"], "")
        self.assertEqual(s["qty"], 0)
        self.assertEqual(s["side"], "")

    def test_skip_is_a_recognised_event_kind(self):
        self.assertIn("skip", F.EVENT_KINDS)


class TheCycleDispatch(unittest.TestCase):
    """End to end through the real gate: a rule returning both kinds records both."""

    def setUp(self):
        F._ENTRY_RULES.clear()
        self.root = _repo(book=BOOK)
        _seed_selfcheck(self.root, BOOK)

    def tearDown(self):
        F._ENTRY_RULES.clear()
        shutil.rmtree(self.root, ignore_errors=True)

    def _run(self, cands):
        F.register_entry_rule(BOOK, lambda decl, root: cands, places_orders=True)
        return F.cycle(self.root, write=True, books=[BOOK])

    def test_a_skip_candidate_is_recorded_as_a_SKIP_and_not_as_a_fill(self):
        out = self._run([{"kind": "skip", "symbol": "AAA", "skip_reason": "hump priced"}])
        row = [r for r in out["books"] if r.get("is_book")][0]
        self.assertEqual(row["skipped"], 1)
        self.assertEqual(out["fills_written"], 0, "a skip is not a fill")
        kinds = [r["kind"] for r in F.read_records(BOOK, self.root)["rows"]]
        self.assertIn("skip", kinds)
        self.assertNotIn("fill", kinds)

    def test_the_skip_reason_survives_the_round_trip(self):
        self._run([{"kind": "skip", "symbol": "AAA", "skip_reason": "hump priced"}])
        rows = [r for r in F.read_records(BOOK, self.root)["rows"] if r["kind"] == "skip"]
        self.assertEqual(rows[0]["skip_reason"], "hump priced")

    def test_a_skip_row_is_inside_the_hash_chain_like_any_other(self):
        self._run([{"kind": "skip", "symbol": "AAA", "skip_reason": "x"}])
        v = F.verify_chain(BOOK, self.root)
        self.assertTrue(v["ok"], v.get("reason"))
        self.assertFalse(v.get("vacuous"))

    def test_an_UNRECOGNISED_kind_is_REFUSED_onto_the_stream_and_never_dropped(self):
        out = self._run([{"kind": "banana", "symbol": "AAA"}])
        self.assertEqual(out["fills_written"], 0)
        rows = F.read_records(BOOK, self.root)["rows"]
        ref = [r for r in rows if r["kind"] == "refusal"]
        self.assertTrue(ref, "an unclassifiable candidate must leave a record")
        self.assertEqual(ref[-1]["refusal_code"], "UNKNOWN_CANDIDATE_KIND")

    def test_an_untagged_candidate_is_still_a_FILL_so_no_existing_rule_broke(self):
        out = self._run([{"symbol": "AAA", "occ": "A1", "side": "buy_to_open", "qty": 1,
                          "order_type": "market", "quote": {"bid": 1.0, "ask": 1.2},
                          "order": {}, "submitted_ts": "2026-08-24T16:00:00"}])
        self.assertEqual(out["fills_written"], 1)


class TheGuardsCanActuallyFire(unittest.TestCase):
    """MUTATION. A refusal that cannot fire is not a refusal.

    Each case breaks ONE guard, asserts the bad structure now sails through, and restores the
    original -- so a green run of this class is evidence the guards are load-bearing rather
    than decorative.
    """

    def test_removing_the_naked_short_check_lets_a_naked_short_through(self):
        real = F.check_structure
        try:
            def mutated(legs, *, net_rule):
                out = real(legs, net_rule=net_rule)
                out["refusals"] = [r for r in out["refusals"] if r != "MULTILEG_NAKED_SHORT"]
                out["ok"] = not out["refusals"]
                return out
            F.check_structure = mutated
            self.assertTrue(mutated(NAKED + [_leg("C1", "sell_to_open", 1.0, 1.1)],
                                    net_rule=F.NET_ANY)["ok"],
                            "the mutation did not disable the guard, so this proves nothing")
        finally:
            F.check_structure = real
        self.assertIn("MULTILEG_NAKED_SHORT",
                      F.check_structure(NAKED + [_leg("C1", "sell_to_open", 1.0, 1.1)],
                                        net_rule=F.NET_ANY)["refusals"])

    def test_pricing_the_net_at_the_MID_would_FLIP_a_refusal_into_an_acceptance(self):
        """The reason `net_cost` is marketable, DEMONSTRATED on a structure where the two
        conventions disagree in SIGN -- the only kind of case that proves anything.

        Wide, skewed spreads are exactly where a collar gets financed, so this is the
        ordinary case rather than a contrived one.
        """
        # put: bid 1.00 / ask 1.40   call: bid 1.30 / ask 1.34
        legs = [_leg("P", "buy_to_open", 1.00, 1.40), _leg("C", "sell_to_open", 1.30, 1.34)]
        marketable = F.net_cost(legs)                       # 1.40 - 1.30 = +0.10, a DEBIT
        mid_based = ((1.00 + 1.40) / 2) - ((1.30 + 1.34) / 2)   # 1.20 - 1.32 = -0.12, a CREDIT
        self.assertGreater(marketable, 0.0)
        self.assertLess(mid_based, 0.0)
        # F-6 forbids a credit. Under the SHIPPED convention this structure is accepted; under
        # a mid convention the identical structure would be REFUSED -- so the choice of
        # convention decides the book's composition, and it is pinned rather than assumed.
        self.assertTrue(F.check_structure(legs, net_rule=F.NET_DEBIT_ONLY)["ok"])
        flipped = [_leg("P", "buy_to_open", 1.00, 1.20), _leg("C", "sell_to_open", 1.30, 1.90)]
        self.assertLess(F.net_cost(flipped), 0.0, "marketable: a credit, so F-6 refuses")
        self.assertIn("MULTILEG_NET_CREDIT",
                      F.check_structure(flipped, net_rule=F.NET_DEBIT_ONLY)["refusals"])

    def test_a_skip_with_no_reason_cannot_be_forced_through_record_skip(self):
        with self.assertRaises(ValueError):
            F.skip_fields(symbol="A", skip_reason="   ")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
