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

#: The LIVE record, appended to by the fleet-backup bot. Read only by the one test that
#: asserts the diagnosis still RUNS on it, and never for a count.
BACKUP = os.path.join(REPO, "data_export", "fleet_records")

#: The FROZEN copy every snapshot assertion below is written against: all 18 streams as they
#: stood at `3d48813`, item 46's own measurement commit, extracted as raw blobs so the bytes
#: are byte-identical to what the repository stores. It is NOT under `tests/fixtures/`
#: on purpose: `tests/fixtures.py` is an existing module that four suites import, and a
#: sibling directory of the same name would shadow it the day anyone added an
#: `__init__.py` to it.
#:
#: REPOINTED 2026-10-19. The snapshot assertions used to read `BACKUP`, so the fleet-backup
#: bot's own commit (`69c39d4`, 2026-10-18) turned this suite red against a correct tree --
#: f3 order rows 72 -> 90, distinct contracts 44 -> 45, declared books 18 -> 24, and 328
#: `reconcile` rows appearing where three tests assert there are none. `MB31`'s family, and
#: this file had already been bitten by it once (see
#: `test_the_implemented_rules_are_a_declared_subset_and_one_cannot_order`).
#:
#: THE RULE THIS ENCODES: a test may read a directory a bot writes to, or it may assert an
#: exact count, but not both. Re-typing the numbers would go red again at the next backup.
FIXTURE = os.path.join(REPO, "tests", "frozen_records", "fleet_records_item46")

#: `MA13`'s committed-literal idiom, now safe because it describes the FROZEN fixture: these
#: cannot move unless someone edits the fixture, and that shows in the diff.
F3_ORDER_ROWS = 72
F3_DISTINCT_CONTRACTS = 44

#: Counts that GROW BY DESIGN are floors, never equalities. A floor still fires on the
#: dangerous direction -- a book un-declared, a rule silently disarmed -- and tolerates the
#: safe one, which is exactly what an equality could not do.
BOOKS_DECLARED_FLOOR = 18
RULES_IMPLEMENTED_FLOOR = 6    # 2026-10-13: F-21 and F-22 armed

#: The four states `why_no_orders` may assign. A fifth is a real change and must go red.
CENSUS_STATES = {"NO_ENTRY_RULE", "RIDER", "ARMED_NO_ORDERS", "ARMED_WITH_ORDERS"}


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
        that found no candidate. Only the third is a question.

        REPOINTED 2026-10-19 from four frozen integers (14/1/2/1 summing to 18) to the
        PARTITION PROPERTY they stood in for. Every one of those integers moves BY DESIGN --
        declaring a book moves the sum, arming one moves a book out of `NO_ENTRY_RULE` -- and
        the live census is already 24 books. What follows is what the four numbers were
        really asserting, and it does not move with fleet size.
        """
        from valuation.edge.fleet_books import RULES
        got = D.why_no_orders(root=FIXTURE)
        c = got["census"]
        books = got["books"]

        # It PARTITIONS: every book lands in exactly one state and nothing is dropped.
        self.assertTrue(books, "the fixture is empty -- the census would prove nothing")
        self.assertEqual(sum(c.values()), len(books))
        self.assertEqual(len(books), len({b["book"] for b in books}))

        # No fifth state appears unnoticed.
        self.assertEqual(set(c) - CENSUS_STATES, set())

        # And each state is exactly what RULES and the record imply, book by book. This is
        # the function's whole contract and what the frozen counts were a proxy for.
        for b in books:
            rule = RULES.get(b["book"])
            if rule is None:
                want = "NO_ENTRY_RULE"
            elif not rule[1]:
                want = "RIDER"
            elif b["kinds"].get("fill"):
                want = "ARMED_WITH_ORDERS"
            else:
                want = "ARMED_NO_ORDERS"
            self.assertEqual(b["state"], want, b["book"])

        # Non-vacuous: this suite exists to prove the causes are not lumped, so it must see
        # more than one of them.
        self.assertGreaterEqual(len(set(c)), 3,
                                "fewer than three states present on the fixture")

    def test_the_census_still_runs_on_the_LIVE_record(self):
        """The fixture buys determinism and would silently cost live coverage, so this keeps
        it: the diagnosis must still read the real bot-appended streams and return a
        well-formed partition. NO COUNT IS ASSERTED, which is the whole point."""
        got = D.why_no_orders()
        books = got["books"]
        self.assertGreaterEqual(len(books), BOOKS_DECLARED_FLOOR,
                                "books are never un-declared; a fall is a real regression")
        self.assertEqual(sum(got["census"].values()), len(books))
        self.assertEqual(set(got["census"]) - CENSUS_STATES, set())

    def test_the_implemented_rules_are_a_declared_subset_and_one_cannot_order(self):
        """REPOINTED 2026-10-13, `MB31`'s family: this asserted `len(RULES) == 4` and fired
        on the CLOCK the moment F-21 and F-22 were armed, against a correct tree. The count
        stays as a committed literal so arming a book still shows in this diff (`MA13`), but
        the load-bearing assertions are now PROPERTIES that do not move when the fleet grows:
        every implemented rule is a DECLARED book, and `f1_fill_ab` is the only rider."""
        from valuation.edge.fleet_books import RULES
        self.assertGreaterEqual(len(RULES), RULES_IMPLEMENTED_FLOOR,
                                "a rule is never un-implemented; arming only adds, so this "
                                "is a FLOOR -- the equality fired on the clock once already")
        declared = {d["book"] for d in F.declared_books() if d.get("parses")}
        self.assertFalse(sorted(set(RULES) - declared),
                         "an implemented rule with no declaration can never be armed")
        self.assertEqual(sorted(k for k, (fn, places) in RULES.items() if not places),
                         ["f1_fill_ab"], "a rider is not a silent book")

    def test_f3s_rows_are_MARKET_orders_with_no_outcome(self):
        """Market, not limit -- so "the sandbox never fills a limit" is refuted, not assumed."""
        got = D.unfilled("f3_bear_puts", root=FIXTURE)
        self.assertEqual(got["order_rows"], F3_ORDER_ROWS)
        self.assertEqual(got["without_an_outcome"], F3_ORDER_ROWS)
        self.assertEqual(got["order_type"], {"market": F3_ORDER_ROWS})
        self.assertEqual(got["fate"], {"working": F3_ORDER_ROWS})
        self.assertEqual(got["distinct_contracts"], F3_DISTINCT_CONTRACTS)

    def test_no_broker_order_id_is_stored_which_is_WHY_nothing_could_poll(self):
        self.assertFalse(D.unfilled("f3_bear_puts", root=FIXTURE)["has_order_id_column"])
        self.assertNotIn("broker_order_id", F.RECORD_COLUMNS)

    def test_the_diagnosis_runs_offline(self):
        """It must not need the vendor to answer: a diagnosis that only works when the broker
        is up cannot be run on the day the broker is the problem."""
        got = D.main(["--no-broker", "--json"])
        self.assertEqual(got, 0)


class TheFrozenFixtureStaysFrozen(unittest.TestCase):
    """The guard that protects the repoint, and it is the one this fix most needs.

    The failure mode is not someone re-typing 72 as 90 -- it is someone "refreshing" the
    fixture from `data_export/` to make a diff go away, which silently reintroduces the exact
    bug the fixture exists to remove and leaves every snapshot assertion below reading the
    bot's output again. A digest over the whole directory catches that, and it cannot cry
    wolf: nothing but an edit to the fixture can move it.
    """

    #: `MA13`'s committed-literal idiom over the FROZEN bytes. Legitimately changing the
    #: fixture means moving this line in the same commit, which shows in the diff.
    N_FILES = 18
    TOTAL_BYTES = 92618
    DIGEST = "e3ec0249ac1cf99246bc7107ae55f9fe4528728c3789eac46fd91329fbf1f0d5"

    def test_the_fixture_is_byte_for_byte_what_was_frozen(self):
        import hashlib
        names = sorted(os.listdir(FIXTURE))
        h, total = hashlib.sha256(), 0
        for n in names:
            with io.open(os.path.join(FIXTURE, n), "rb") as fh:
                b = fh.read()
            h.update(n.encode("utf-8"))
            h.update(b)
            total += len(b)
        # GATED, or an empty directory digests to a constant and passes by comparing nothing
        # (`MB21`'s C1, which scored a perfect zero on an empty frame).
        self.assertEqual(len(names), self.N_FILES, names)
        self.assertEqual(total, self.TOTAL_BYTES)
        self.assertEqual(h.hexdigest(), self.DIGEST,
                         "the frozen fixture has changed. If that was deliberate, move the "
                         "literals above in the same commit. If it was a refresh from "
                         "data_export/, it has just reintroduced the bug this fixture removes.")

    def test_the_fixture_is_NOT_the_live_record(self):
        """Non-vacuous: if the two ever coincide, the fixture froze nothing and every
        snapshot assertion in this file is back on the bot's growing stream."""
        live = os.path.join(BACKUP, "f3_bear_puts.csv")
        if not os.path.exists(live):
            self.skipTest("no committed fleet backup in this checkout")
        with io.open(live, "rb") as fh:
            a = fh.read()
        with io.open(os.path.join(FIXTURE, "f3_bear_puts.csv"), "rb") as fh:
            b = fh.read()
        self.assertNotEqual(a, b, "the fixture is a copy of the live record, not a freeze")
        self.assertGreater(len(a), len(b),
                           "the live record only ever grows; a shorter live file means it was "
                           "truncated, which is a far worse problem than this suite's")


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
    """Driven against a COPY of the FROZEN stream, so the rows are real and the write is not.

    It read `BACKUP` until 2026-10-19. Those rows are still real, but the bot has since
    appended 328 `reconcile` rows to them -- so three tests below, which assert that no
    `reconcile` row exists until this code writes one, were reading the bot's own output as
    though it were theirs. The fixture restores the pre-reconciliation state they describe.
    """

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="i46-")
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "data", "fleet"))
        self.src = os.path.join(FIXTURE, "f3_bear_puts.csv")
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
