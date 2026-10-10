# -*- coding: utf-8 -*-
"""ITEM 46 - why the fleet never recorded a fill, and the reconciliation that records it.

THREE DIFFERENT CAUSES, NOT ONE, and the diagnosis is worth more than the fix:

  * **14 books have no entry rule implemented** (`fleet_books.RULES` registers four). Declared
    and un-armed, and `cycle()` has said so on every run. NOT a defect.
  * **`f1_fill_ab` is a RIDER** -- its own declaration says it never sends an order. NOT a
    defect either.
  * **ALL EIGHTEEN, including the three armed ones, are blocked at the gate** on
    `ALL_BOOKS_BLOCKED_AT_GATE:SELFCHECK_STALE`: `harness_fingerprint()` covers eight modules,
    so any change to one invalidates every day-1 certificate, re-certifying places a real
    sandbox order, and **nothing renews it**. That is the certificate working and the renewal
    missing.

AND THE FOURTH FINDING IS THE ONE THAT NEEDED FIXING: **f3's orders DID fill.** The sandbox
reports ZERO open orders and a position in 37 of the 44 contracts f3 ordered, while all 72
record rows still read `fate=working` -- because a row is written ONCE at submission, from a
status read moments later when a market order is legitimately `pending`, and **nothing ever
polls the order again.** `submit()` obtains the broker's order id and discards it, because
`RECORD_COLUMNS` has nowhere to put it.

WHY THE FIX APPENDS A NEW `kind` AND NOT A NEW COLUMN. `append_only.append` REFUSES a widened
header on an append-only write, so adding a base column would make all 18 live streams refuse
every future write. `reconcile` is a new VALUE in the existing `kind` column, which widens
nothing.
"""
from __future__ import annotations

import csv
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.edge import fleet as F                                      # noqa: E402
from scripts import fleet_diagnose as D                                    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(REPO, "data_export", "fleet_records")

#: MA13's committed-literal idiom: the measured figures, written down so a change has to move
#: this line too and shows in the diff.
F3_ORDER_ROWS = 72
F3_DISTINCT_CONTRACTS = 44
BOOKS_DECLARED = 18
RULES_IMPLEMENTED = 4


class _Positions:
    """A stand-in broker. Read-only by construction: it has no order-placing method at all."""

    def __init__(self, held, open_orders=0):
        self._held = dict(held)
        self._open = open_orders

    def positions(self):
        return [{"symbol": s, "quantity": q, "cost_basis": 100.0}
                for s, q in self._held.items()]

    def orders(self):
        return [{"id": i} for i in range(self._open)]


class TheDiagnosisSeparatesThreeCauses(unittest.TestCase):

    def test_the_census_is_three_states_and_not_one_number(self):
        """"16 books placed nothing" lumps a book with no rule, a rider, and an armed book
        that found no candidate. Only the third is a question."""
        got = D.why_no_orders()
        c = got["census"]
        self.assertEqual(sum(c.values()), BOOKS_DECLARED)
        self.assertEqual(c.get("NO_ENTRY_RULE"), 14)
        self.assertEqual(c.get("RIDER"), 1)
        self.assertEqual(c.get("ARMED_NO_ORDERS"), 2)
        self.assertEqual(c.get("ARMED_WITH_ORDERS"), 1)

    def test_only_four_rules_are_implemented_and_one_cannot_order(self):
        from valuation.edge.fleet_books import RULES
        self.assertEqual(len(RULES), RULES_IMPLEMENTED)
        self.assertEqual(sorted(k for k, (fn, places) in RULES.items() if not places),
                         ["f1_fill_ab"], "a rider is not a silent book")

    def test_f3s_rows_are_MARKET_orders_with_no_outcome(self):
        """Market, not limit -- so "the sandbox never fills a limit" is refuted, not assumed."""
        got = D.unfilled("f3_bear_puts")
        self.assertEqual(got["order_rows"], F3_ORDER_ROWS)
        self.assertEqual(got["without_an_outcome"], F3_ORDER_ROWS)
        self.assertEqual(got["order_type"], {"market": F3_ORDER_ROWS})
        self.assertEqual(got["fate"], {"working": F3_ORDER_ROWS})
        self.assertEqual(got["distinct_contracts"], F3_DISTINCT_CONTRACTS)

    def test_no_broker_order_id_is_stored_which_is_WHY_nothing_could_poll(self):
        self.assertFalse(D.unfilled("f3_bear_puts")["has_order_id_column"])
        self.assertNotIn("broker_order_id", F.RECORD_COLUMNS)

    def test_the_diagnosis_runs_offline(self):
        """It must not need the vendor to answer: a diagnosis that only works when the broker
        is up cannot be run on the day the broker is the problem."""
        got = D.main(["--no-broker", "--json"])
        self.assertEqual(got, 0)


class WhyANewColumnWasNotTheFix(unittest.TestCase):

    def test_an_append_only_write_REFUSES_a_widened_header(self):
        """The constraint that chose the design, driven rather than quoted.

        Adding `broker_order_id` to `RECORD_COLUMNS` would make every one of the 18 live
        streams refuse every future write.
        """
        from valuation.edge import append_only as AO
        d = tempfile.mkdtemp(prefix="i46-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "s.csv")
        r1 = AO.append({"seq": "1", "a": "x"}, p, key="seq", columns=["seq", "a"],
                       append_only=True)
        self.assertTrue(r1["wrote"])
        r2 = AO.append({"seq": "2", "a": "y", "b": "z"}, p, key="seq",
                       columns=["seq", "a", "b"], append_only=True)
        self.assertFalse(r2["wrote"])
        self.assertIn("refusing to widen the header", r2["reason"])

    def test_reconcile_is_a_new_KIND_and_widens_nothing(self):
        self.assertIn("reconcile", F.EVENT_KINDS)
        self.assertIn("kind", F.RECORD_COLUMNS)


class TheReconciliationRecordsWithoutClaiming(unittest.TestCase):
    """Driven against a COPY of the real stream, so the rows are real and the write is not."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="i46-")
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "data", "fleet"))
        self.src = os.path.join(BACKUP, "f3_bear_puts.csv")
        self.dst = os.path.join(self.d, "data", "fleet", "f3_bear_puts.csv")
        shutil.copy(self.src, self.dst)
        rows = list(csv.DictReader(io.open(self.src, newline="", encoding="utf-8")))
        self.occ = sorted({r["occ"] for r in rows if r.get("kind") == "fill" and r.get("occ")})

    def _rows(self, kind=None):
        with io.open(self.dst, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        return [r for r in rows if kind is None or r.get("kind") == kind]

    def test_it_finds_exactly_the_rows_with_no_outcome(self):
        self.assertEqual(len(F.outcome_unknown("f3_bear_puts", root=self.d)), F3_ORDER_ROWS)

    def test_a_held_contract_gets_ONE_row_and_it_claims_NO_fill(self):
        """The restraint is the design: a fabricated fill price would be worse than silence."""
        b = _Positions({self.occ[0]: 3.0}, open_orders=0)
        got = F.reconcile_outcomes("f3_bear_puts", broker=b, root=self.d)
        self.assertEqual(got["wrote"], 1)
        rec = self._rows("reconcile")
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]["occ"], self.occ[0])
        self.assertEqual(rec[0]["fate"], "unknown",
                         "it cannot attribute the fill, so it must not claim one")
        self.assertEqual((rec[0]["fill_price"] or ""), "",
                         "no fill_price it cannot attribute")
        self.assertIn("position-level evidence", rec[0]["detail"])
        self.assertIn("NOT attributable", rec[0]["detail"])

    def test_a_contract_with_NO_position_is_counted_not_asserted(self):
        """An expired or already-closed contract has no position either, so absence of a
        position is not evidence the order failed."""
        got = F.reconcile_outcomes("f3_bear_puts", broker=_Positions({}), root=self.d)
        self.assertEqual(got["wrote"], 0)
        self.assertEqual(got["skipped_no_position"], F3_DISTINCT_CONTRACTS)
        self.assertEqual(self._rows("reconcile"), [])

    def test_one_row_per_CONTRACT_not_per_order_row(self):
        """f3 ordered the same contract up to seven times; seven identical reconcile rows
        would say the same thing seven times and imply seven observations."""
        b = _Positions({o: 1.0 for o in self.occ})
        got = F.reconcile_outcomes("f3_bear_puts", broker=b, root=self.d)
        self.assertEqual(got["wrote"], F3_DISTINCT_CONTRACTS)
        self.assertEqual(len(self._rows("reconcile")), F3_DISTINCT_CONTRACTS)

    def test_the_byte_prefix_and_the_chain_both_survive(self):
        """The append-only guarantee is byte-level, and the chain is what makes the record
        tamper-evident. A reconciliation that broke either would be worse than none."""
        before = io.open(self.src, "rb").read()
        F.reconcile_outcomes("f3_bear_puts", broker=_Positions({self.occ[0]: 1.0}),
                             root=self.d)
        after = io.open(self.dst, "rb").read()
        self.assertTrue(after.startswith(before),
                        "the previous bytes must still be an exact prefix")
        self.assertTrue(F.verify_chain("f3_bear_puts", root=self.d).get("ok"))

    def test_no_existing_row_is_touched(self):
        """Append-only: a past row is not editable, which is also why the 72 `working` rows
        STAY `working` -- they were true when they were written."""
        before = self._rows("fill")
        F.reconcile_outcomes("f3_bear_puts", broker=_Positions({self.occ[0]: 1.0}),
                             root=self.d)
        self.assertEqual(self._rows("fill"), before)

    def test_write_False_plans_without_writing(self):
        plan = F.reconcile_outcomes("f3_bear_puts", broker=_Positions({self.occ[0]: 1.0}),
                                    root=self.d, write=False)
        self.assertEqual(plan["wrote"], 0)
        self.assertEqual(len(plan["rows"]), 1)
        self.assertEqual(self._rows("reconcile"), [])

    def test_a_broker_that_cannot_be_read_is_reported_not_guessed(self):
        class _Dead:
            def positions(self):
                raise ConnectionError("down")

            def orders(self):
                return []

        got = F.reconcile_outcomes("f3_bear_puts", broker=_Dead(), root=self.d)
        self.assertEqual(got["wrote"], 0)
        self.assertTrue(any("broker read failed" in e for e in got["errors"]))
        self.assertEqual(self._rows("reconcile"), [])

    def test_it_is_idempotent_in_substance(self):
        """Run twice and the second pass must not re-assert the same observation: the rows it
        reconciles no longer lack an outcome... except they DO, because a past row cannot be
        edited. So the honest property is that it writes NEW seqs and never duplicates a
        contract within one pass -- and a reader can tell the passes apart by timestamp."""
        b = _Positions({self.occ[0]: 1.0})
        F.reconcile_outcomes("f3_bear_puts", broker=b, root=self.d)
        n1 = len(self._rows("reconcile"))
        F.reconcile_outcomes("f3_bear_puts", broker=b, root=self.d)
        n2 = len(self._rows("reconcile"))
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 2, "a second observation is a second row, not an edit")
        seqs = [r["seq"] for r in self._rows("reconcile")]
        self.assertEqual(len(set(seqs)), len(seqs), "every row gets its own seq")


class TheCycleRunsItAndSaysSo(unittest.TestCase):

    def test_the_cycle_reports_a_reconciled_block(self):
        got = F.cycle(write=False)
        self.assertIn("reconciled", got)
        self.assertIn("books", got["reconciled"])

    def test_it_is_not_gated_on_the_self_check(self):
        """Deliberate: `may_fill` stops a book TRADING on an uncertified harness. This places
        nothing. Gating a record of history behind a trading gate is how the history came to
        be missing."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        body = src[src.index("def reconcile_outcomes"):]
        body = body[:body.index("\ndef ")]
        self.assertNotIn("may_fill(", body,
                         "reconciliation must not be gated on the trading gate")

    def test_a_reconciliation_failure_cannot_kill_the_cycle(self):
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        i = src.index("RECONCILE ORDER ROWS THAT NEVER GOT AN OUTCOME")
        block = src[i:i + 2200]
        self.assertIn("except Exception", block,
                      "a cycle whose job is to place fills must not die on a reconciliation")


class WhatDonMustInstall(unittest.TestCase):
    """`.github/` is refused to lanes, so both go through `data/pending_workflows/`."""

    def _read(self, name):
        from scripts import propose_workflow as PW
        return PW.read(name)

    def test_the_selfcheck_workflow_is_dispatch_only(self):
        y = self._read("fleet-selfcheck.yml")
        from scripts import workflow_source as WS
        code = WS.strip_comments(y)
        self.assertIn("workflow_dispatch", code)
        self.assertEqual(WS.crons(y), [],
                         "automatic re-certification would make the certificate worthless")
        self.assertIn("selfcheck=1", code)
        self.assertIn("Run workflow", y)

    def test_it_allows_more_time_than_the_cycle_because_it_places_orders(self):
        y = self._read("fleet-selfcheck.yml")
        self.assertIn("--max-time 900", y)
        self.assertIn("timeout-minutes: 30", y)

    def test_it_warns_to_run_AFTER_the_deploy(self):
        """Items 45 and 46 both changed fingerprinted modules, so a certificate renewed before
        they reach the service goes stale again the moment they do."""
        self.assertIn("AFTER THE DEPLOY", self._read("fleet-selfcheck.yml"))

    def test_the_cycle_warning_now_names_the_measured_cause(self):
        y = self._read("fleet-cycle.yml")
        self.assertIn("not_breathing_reason", y)
        self.assertIn("SELFCHECK_STALE", y)
        from scripts import workflow_source as WS
        code = WS.strip_comments(y)
        self.assertNotIn("(no entry rule implemented)", code,
                         "the old warning named a cause that was not the cause")


if __name__ == "__main__":
    unittest.main(verbosity=2)
