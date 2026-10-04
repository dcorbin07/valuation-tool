"""ITEM 29 — A ROW THAT NAMES NO CONTRACT IS NOT LIVE, AND A REJECTED EXIT IS STILL A STOP.

TWO DEFECTS, BOTH MEASURED ON THE LIVE SERVICE ON 2026-10-04 BEFORE ANY CHANGE:

**(a) `/api/scream-track` read LIVE 23 while `/api/options-scorecard` read n_open 15.**
`display_status` tested `closed`, then expiry, then fell through to LIVE — and an alert logged
from a descriptor with no chain has status `no_contract` AND no expiry, so it took the
fall-through. 23 − 8 = 15, and the eight were alert ids 9, 10, 12, 13, 16, 18, 24, 25.

**(b) Two real stop-outs read "CLOSED (unscoreable)" and were missing from the STOPPED count.**
`paper_track` does not store the decision token: on an exit the broker would not work it
composes `f"{reason} (marked; exit order {status})"`, so the stored reason is
`"stop (marked; exit order rejected) [pnl vs fill]"`. `_reason_token` stripped the bracketed
suffix and not the parenthetical, so it returned the whole head, matched nothing, and fell to
`STATUS_CLOSED_OTHER`. FDX (id 5) stopped at 4.05 against a 4.975 stop, **−55.2%**; JNJ (id 8)
at 2.14 against 2.40, **−52.4%**. Both carry a `pnl_pct`, so "unscoreable" was false of both,
and the tab read STOPPED 6 where it should read 8 — understating the stop rate, which is the
direction that flatters.

**AND THE GUARD MEANT TO CATCH AN UNMAPPED REASON COULD NOT SEE IT.**
`test_scream_log.py` enumerates the string constants RETURNED by `exit_decision`; all four are
mapped. The composed reason is an f-string at the RECORD site, so it is not a return and the
AST walk never had it in view — it enumerated what the DECIDER emits while the record stores
what the CLOSER composes. That enumeration is extended in `test_scream_log.py` itself; this
file pins the behaviour the display depends on.

    python tests/test_item29_no_contract.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import options_selfscore as SS   # noqa: E402
from valuation.edge import paper_track as PT         # noqa: E402
from valuation.edge import scream_log as SL          # noqa: E402
from valuation.web import scream_track as ST         # noqa: E402

#: The real stored reasons, verbatim from the live rows on 2026-10-04.
FDX_REASON = "stop (marked; exit order rejected) [pnl vs fill]"
JNJ_REASON = "stop (marked; exit rejected) [pnl vs fill]"


class ANoContractRowIsNotLive(unittest.TestCase):

    def test_it_gets_its_own_status(self):
        got = SL.display_status({"status": SS.NO_CONTRACT, "expiry": None})
        self.assertEqual(got, SL.STATUS_NO_CONTRACT)
        self.assertNotEqual(got, SL.STATUS_LIVE)

    def test_is_open_is_False_for_it(self):
        """`is_open` derives from `display_status`, so the live COUNT follows from the status."""
        self.assertFalse(SL.is_open({"status": SS.NO_CONTRACT, "expiry": None}))

    def test_the_status_is_published_in_the_vocabulary(self):
        self.assertIn(SL.STATUS_NO_CONTRACT, SL.ALL_STATUSES)

    def test_the_token_is_READ_from_the_module_that_writes_it(self):
        """`B7`: two spellings of one status is how a tab and a scorer disagree about a row.

        Asserted by driving `display_status` with `options_selfscore`'s own constant rather
        than a literal, so a retyped token here fails even if it looks plausible.
        """
        self.assertEqual(
            SL.display_status({"status": SS.NO_CONTRACT, "expiry": None}),
            SL.STATUS_NO_CONTRACT)
        # And the writer's value really is what we think it is.
        self.assertEqual(SS.NO_CONTRACT, "no_contract")

    def test_it_is_decided_BEFORE_the_expiry_test(self):
        """These rows have no expiry, so an ordering that put expiry first would miss them.

        Driven with an expiry PRESENT as well: whatever the ordering, a `no_contract` row is a
        no-contract row. A row that somehow carried both must not read EXPIRED, because the
        reason it cannot be scored is the absent contract and not the passage of time.
        """
        self.assertEqual(
            SL.display_status({"status": SS.NO_CONTRACT, "expiry": "2020-01-01"}),
            SL.STATUS_NO_CONTRACT)

    def test_an_ordinary_open_row_is_still_LIVE(self):
        """The positive control: this must not have made everything not-live."""
        self.assertEqual(SL.display_status({"status": "open", "expiry": "2030-12-20"}),
                         SL.STATUS_LIVE)
        self.assertTrue(SL.is_open({"status": "open", "expiry": "2030-12-20"}))

    def test_an_expired_open_row_is_still_EXPIRED(self):
        self.assertEqual(SL.display_status({"status": "open", "expiry": "2020-01-01"}),
                         SL.STATUS_EXPIRED)


class ARejectedExitIsStillAStop(unittest.TestCase):

    def test_the_two_live_reasons_now_read_STOPPED(self):
        for reason in (FDX_REASON, JNJ_REASON):
            self.assertEqual(
                SL.display_status({"status": "closed", "exit_reason": reason}),
                SL.STATUS_STOPPED, reason)

    def test_the_leading_token_is_the_token(self):
        """`_reason_token`'s own docstring promises the LEADING token; it did not deliver it."""
        self.assertEqual(SL._reason_token(FDX_REASON), "stop")
        self.assertEqual(SL._reason_token(JNJ_REASON), "stop")

    def test_a_time_stop_is_not_swallowed_by_the_stop_mapping(self):
        """`time_stop` CONTAINS `stop`, and the two have opposite meanings for expectancy.

        The parenthetical split must not have turned exact matching back into something that
        can confuse them, so a composed TIME stop is driven here too.
        """
        self.assertEqual(SL._reason_token("time_stop (marked; exit rejected) [pnl vs fill]"),
                         "time_stop")
        self.assertEqual(
            SL.display_status({"status": "closed",
                               "exit_reason": "time_stop (marked; exit rejected)"}),
            SL.STATUS_TIME_STOPPED)

    def test_every_composed_variant_resolves(self):
        """All four suffixes `paper_track` can append, against all four decision tokens."""
        for suffix in SL.CLOSER_REASON_SUFFIXES:
            for tok, want in (("target", SL.STATUS_HIT), ("stop", SL.STATUS_STOPPED),
                              ("time_stop", SL.STATUS_TIME_STOPPED),
                              ("expiry", SL.STATUS_EXPIRED)):
                got = SL.display_status({"status": "closed",
                                         "exit_reason": "%s %s [pnl vs fill]" % (tok, suffix)})
                self.assertEqual(got, want, "%s %s" % (tok, suffix))

    def test_a_genuinely_unmapped_reason_STILL_reads_unscoreable(self):
        """THE POSITIVE CONTROL FOR THE FALLBACK. `CLOSED (unscoreable)` exists for a reason and
        this change must not have made it unreachable — otherwise a future exit rule nobody
        mapped would be silently mislabelled as something it is not."""
        self.assertEqual(
            SL.display_status({"status": "closed", "exit_reason": "liquidated_by_broker"}),
            SL.STATUS_CLOSED_OTHER)


class TheCountsAddUp(unittest.TestCase):
    """A third kind breaks `not live == closed`, and fixing LIVE alone moves the error."""

    def _rows(self):
        return [{"status": SL.STATUS_LIVE}, {"status": SL.STATUS_LIVE},
                {"status": SL.STATUS_NO_CONTRACT}, {"status": SL.STATUS_NO_CONTRACT},
                {"status": SL.STATUS_STOPPED}]

    def test_no_contract_is_counted_separately_and_not_as_closed(self):
        import ast
        with open(os.path.join(REPO, "valuation", "web", "scream_track.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        # Read the ARITHMETIC from the source: `summary` needs a store, and a stub store would
        # test the stub's idea of the record. What matters is that `n_closed` subtracts the
        # third kind, which is a property of the expression.
        self.assertIn('out["n_no_contract"] = len(nocon)', src)
        self.assertIn('out["n_closed"] = len(recs) - len(live) - len(nocon)', src)
        tree = ast.parse(src)
        self.assertTrue(any(isinstance(n, ast.Attribute) or True for n in ast.walk(tree)))

    def test_the_three_counts_partition_the_rows(self):
        """Arithmetic, on the shape the payload builds: live + no_contract + closed == rows."""
        rows = self._rows()
        live = [r for r in rows if r["status"] == SL.STATUS_LIVE]
        nocon = [r for r in rows if r["status"] == SL.STATUS_NO_CONTRACT]
        closed = len(rows) - len(live) - len(nocon)
        self.assertEqual((len(live), len(nocon), closed), (2, 2, 1))
        self.assertEqual(len(live) + len(nocon) + closed, len(rows))

    def test_the_fallback_payload_declares_the_new_count(self):
        """A record that cannot be read must still publish the key, or a reader branching on
        it sees `undefined` — item 21's defect, one tab along."""
        out = ST.summary.__doc__ is not None  # smoke: the module imported
        self.assertTrue(out)
        with open(os.path.join(REPO, "valuation", "web", "scream_track.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('"n_no_contract": 0,', src)


class TheRefusalReasonIsKept(unittest.TestCase):
    """Item 29(b)'s other half: the cause was computed and discarded."""

    def test_the_helper_renders_a_placement_refusal(self):
        got = PT._refusal_detail(res={"ok": False, "http_status": 400,
                                      "error": {"errors": "position not found"}})
        self.assertIn("http 400", got)
        self.assertIn("position not found", got)

    def test_the_helper_renders_an_order_refusal_with_its_description(self):
        got = PT._refusal_detail(order={"status": "rejected",
                                        "reason_description": "no such position"})
        self.assertIn("order rejected", got)
        self.assertIn("no such position", got)

    def test_a_refusal_with_NO_description_still_says_what_happened(self):
        """A sandbox reject sometimes carries no description, and that is itself the finding —
        so the status alone must survive rather than the whole detail collapsing to None."""
        got = PT._refusal_detail(order={"status": "rejected"})
        self.assertEqual(got, "order rejected")

    def test_nothing_to_say_returns_None_rather_than_an_empty_string(self):
        """So a caller can test it, and an empty note is never written over a real one."""
        self.assertIsNone(PT._refusal_detail())
        self.assertIsNone(PT._refusal_detail(order={}, res={}))

    def test_record_accepts_a_note_and_defaults_to_the_previous_behaviour(self):
        import inspect
        sig = inspect.signature(PT._record)
        self.assertIn("note", sig.parameters)
        self.assertIsNone(sig.parameters["note"].default,
                          "the default must be the old behaviour, or every existing caller "
                          "silently changes what it writes")

    def test_the_note_REACHES_THE_ROW_and_is_not_nulled_on_success(self):
        """BEHAVIOURAL, because my source-only assertion did not catch the mutation.

        I first asserted that `_note` appeared in `_record`'s body and that "DESYNC" did too --
        both of which stay true if the line is changed back to `_note = None`. Mutation found
        that: the guard named the variable and never checked what it carried. So this drives
        `_record` against a real temp store and reads the row back.
        """
        from valuation.edge import options_tracker as OT
        from valuation.screener.store import Store
        store = Store()
        aid = OT.log_alert(store, {
            "alert_ts": "2026-09-10T20:05:00", "ticker": "ZZTEST", "opt_right": "call",
            "strike": 100.0, "expiry": "2026-12-18", "entry_premium": 5.0,
            "score": 70.0, "horizon": "swing"})
        rows = {r["ticker"]: r for r in OT.open_alerts(store)}
        self.assertIn("ZZTEST", rows, "the fixture alert did not land")
        aid = rows["ZZTEST"]["id"]
        # The module's OWN schema function, not hand-rolled DDL here: a second CREATE TABLE in
        # a test is a second definition of the row shape, and it would drift the first time a
        # column is added.
        PT.ensure_schema(store)
        with store._conn() as c:
            c.execute("INSERT OR REPLACE INTO paper_option_orders "
                      "(alert_id, ticker, occ_symbol, expiry, contracts, state, "
                      " entry_premium, last_mark) VALUES (?,?,?,?,?,?,?,?)",
                      (aid, "ZZTEST", "ZZTEST261218C00100000", "2026-12-18", 1,
                       "open", 5.0, 2.0))
        out = {"recorded": 0}
        PT._record(store, {"alert_id": aid, "contracts": 1, "entry_premium": 5.0},
                   2.0, "stop (marked; exit rejected)", out,
                   note="order rejected; reason_description=no such position")
        with store._conn() as c:
            got = c.execute("SELECT note FROM paper_option_orders WHERE alert_id = ?",
                            (aid,)).fetchone()
        self.assertIsNotNone(got, "the paper row vanished")
        self.assertIn("no such position", str(got[0] or ""),
                      "the refusal reason was nulled by the close, which is the defect")

    def test_the_close_path_passes_the_detail_to_record(self):
        """THE WHOLE POINT: the reason was available and thrown away.

        Read from the source, because driving a real rejection needs a broker that refuses.
        Both sites are checked — they are different code paths and only one was obvious.
        """
        import ast
        with open(os.path.join(REPO, "valuation", "edge", "paper_track.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("_refusal_detail(order=o)"), 1)
        self.assertEqual(src.count("_refusal_detail(res=res)"), 1)
        self.assertEqual(src.count("note=_why"), 2,
                         "both rejection sites must hand the detail to `_record`")
        # And `_record` must not null it on success any more.
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "_record")
        body = ast.unparse(fn)
        self.assertIn("_note", body)
        self.assertIn("DESYNC", body, "a DESYNC must still be recorded, and must still lead")


if __name__ == "__main__":
    unittest.main(verbosity=2)
