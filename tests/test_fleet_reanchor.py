"""Re-anchoring a fleet stream - Don's remedy (b), 2026-10-17.

**THE DEFECT.** The chain anchors at the DECLARATION's content hash, so amending a declaration
after the stream's first row breaks row 0 forever. `F-21` and `F-22` read `CHAIN_BROKEN` from
2026-10-13, when an amendment landed between the cycle that wrote their self-check rows and
their arming - *"before the arming"*, which was true, and irrelevant, because the chain anchors
on the FIRST RECORD.

**WHY THE FIRST ATTEMPT FAILED AND WHAT THESE TESTS EXIST TO STOP RECURRING.** It archived the
stream and let it restart at seq 1; `fleet_highwater` then refused the NEXT write with *"holds
rows only up to seq 0 but 2 was already recorded"* - correct, because a restarted stream is
indistinguishable from the whole-file loss that module exists to catch. **So the load-bearing
test here is not that the re-anchor returns ok. It is that an ORDINARY WRITE SUCCEEDS
AFTERWARDS**, through the real door, which is the step that was never exercised.

WHAT EACH GROUP PINS
--------------------
1. **The real write path, end to end**, including the next ordinary append and the sequence
   continuing above the mark rather than restarting.
2. **Four refusals**, each from the wrong side: a stream with a fill or close, a tampered
   chain, an anchor that has not moved, a book with no declaration.
3. **The high-water guard still holds, and clears only ON EVIDENCE.** Delete the archive and
   the book goes straight back to `REGRESSED` - which is what separates this from an exemption.
4. **`advance` must not eat the note.** It rewrote the whole book entry, so the next ordinary
   append would have dropped `reanchors` and the book would have gone `REGRESSED` with nothing
   to explain why.
5. **The allowlist is two books and the cycle's step is self-extinguishing.**
6. **The amendment is made LOUD**: a moved anchor is diagnosed by name and the remedy is named.

    python tests/test_fleet_reanchor.py
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet as F  # noqa: E402
from valuation.edge import fleet_highwater as HW  # noqa: E402

BOOK = "reanchor_probe"
BODY = """# DECL reanchor_probe

```json
{"declaration": {"book": "reanchor_probe", "side": "long", "sells_premium": false}}
```
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="reanchor_")
        os.makedirs(os.path.join(self.root, "data"), exist_ok=True)
        self.decl = os.path.join(self.root, "DECL_%s.md" % BOOK)
        with open(self.decl, "w", encoding="utf-8") as fh:
            fh.write(BODY)
        self.sha = F.decl_sha_for(BOOK, self.root)
        self.assertTrue(self.sha)
        self.fd = F.fleet_dir(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, kind="selfcheck", n=1, sha=None):
        for _ in range(n):
            r = F.record(BOOK, kind, {}, decl_sha=(sha or self.sha), root=self.root)
            self.assertTrue(r.get("wrote"), r.get("reason"))

    def _amend(self):
        with open(self.decl, "a", encoding="utf-8") as fh:
            fh.write("\nan amendment after the stream started\n")
        new = F.decl_sha_for(BOOK, self.root)
        self.assertNotEqual(new, self.sha)
        return new


class TestTheRealWritePath(Base):
    """(1) - and the second test is the one the first attempt failed."""

    def test_a_moved_anchor_is_repaired_and_the_chain_verifies_again(self):
        self._write(n=3)
        with open(F.records_path(BOOK, self.root), "rb") as fh:
            before = fh.read()
        new = self._amend()
        self.assertFalse(F.verify_chain(BOOK, self.root, decl_sha=new)["ok"],
                         "the premise: the amendment breaks row 0")

        res = F.reanchor_stream(BOOK, self.root)
        self.assertTrue(res["ok"], res["reason"])
        self.assertEqual(res["rows_archived"], 3)
        self.assertEqual(res["archive_max_seq"], 3)
        self.assertTrue(F.verify_chain(BOOK, self.root, decl_sha=new)["ok"])

        arc = os.path.join(self.fd, res["archived_to"])
        with open(arc, "rb") as fh:
            self.assertEqual(fh.read(), before, "archived BYTE-FOR-BYTE")

    def test_THE_NEXT_ORDINARY_WRITE_SUCCEEDS(self):
        """**The step the first attempt never reached.** It is the whole point of remedy (b)."""
        self._write(n=2)
        new = self._amend()
        self.assertTrue(F.reanchor_stream(BOOK, self.root)["ok"])
        r = F.record(BOOK, "selfcheck", {}, decl_sha=new, root=self.root)
        self.assertTrue(r.get("wrote"), r.get("reason"))

    def test_the_sequence_CONTINUES_above_the_mark_and_never_restarts(self):
        self._write(n=4)
        new = self._amend()
        F.reanchor_stream(BOOK, self.root)
        F.record(BOOK, "selfcheck", {}, decl_sha=new, root=self.root)
        seqs = [int(r["seq"]) for r in F.read_records(BOOK, self.root)["rows"]]
        self.assertEqual(seqs, [5, 6], "4 rows were archived, so the new stream starts at 5")
        self.assertGreaterEqual(min(seqs), 5, "no sequence number may ever be reused")

    def test_the_first_row_of_the_new_stream_is_a_dated_visible_reanchor_event(self):
        self._write(n=2)
        self._amend()
        F.reanchor_stream(BOOK, self.root)
        first = F.read_records(BOOK, self.root)["rows"][0]
        self.assertEqual(first["kind"], "reanchor")
        self.assertTrue(first["ts"], "it must be dated")
        self.assertIn("superseded", first["detail"], "and it must name the archive")

    def test_a_reader_of_the_RECORDS_ALONE_can_see_it_happened(self):
        """The mark file is a sibling; a records-only reader must not be blind to the split."""
        self._write(n=2)
        self._amend()
        F.reanchor_stream(BOOK, self.root)
        kinds = [r["kind"] for r in F.read_records(BOOK, self.root)["rows"]]
        self.assertIn("reanchor", kinds)


class TestTheRefusals(Base):
    """(2)."""

    def test_it_refuses_a_stream_carrying_a_FILL(self):
        self._write("selfcheck", 1)
        self._write("fill", 1)
        self._amend()
        res = F.reanchor_stream(BOOK, self.root)
        self.assertFalse(res["ok"])
        self.assertIn("orphan real trades", res["reason"])
        self.assertTrue(os.path.exists(F.records_path(BOOK, self.root)),
                        "and it leaves the stream exactly where it was")

    def test_it_refuses_a_stream_carrying_a_CLOSE(self):
        self._write("selfcheck", 1)
        self._write("close", 1)
        self._amend()
        self.assertFalse(F.reanchor_stream(BOOK, self.root)["ok"])

    def test_it_refuses_when_the_anchor_has_NOT_moved(self):
        self._write(n=2)
        res = F.reanchor_stream(BOOK, self.root)
        self.assertFalse(res["ok"])
        self.assertIn("moved anchor is NOT the fault", res["reason"])

    def test_it_refuses_a_TAMPERED_chain_rather_than_treating_it_as_a_moved_one(self):
        self._write(n=3)
        p = F.records_path(BOOK, self.root)
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        # corrupt a STORED field on an interior row (`note` is not a column; `kind` is)
        i = txt.index(",selfcheck,", txt.index(",selfcheck,") + 1)
        txt = txt[:i] + ",meter_read," + txt[i + len(",selfcheck,"):]
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(txt)
        self._amend()
        res = F.reanchor_stream(BOOK, self.root)
        self.assertFalse(res["ok"])
        self.assertIn("tampered or corrupt", res["reason"])
        self.assertTrue(os.path.exists(p), "a corrupt stream is never archived away")

    def test_it_refuses_a_book_with_no_declaration_to_re_anchor_TO(self):
        self._write(n=1)
        os.remove(self.decl)
        self.assertIn("nothing to re-anchor TO", F.reanchor_stream(BOOK, self.root)["reason"])

    def test_an_absent_stream_is_a_no_op_rather_than_an_error(self):
        res = F.reanchor_stream(BOOK, self.root)
        self.assertTrue(res["ok"])
        self.assertFalse(res["reanchored"])


class TestTheGuardStillHolds(Base):
    """(3) - the property that makes this evidence rather than an exemption."""

    def _mid_reanchor(self):
        """The state `record` actually sees INSIDE a re-anchor: file archived, note written,
        live stream not yet started. My first cut of these two tests asked about an empty
        stream AFTER the marker row had been written, which is a state that never occurs -
        by then the mark has advanced past the archive and the archive correctly stops
        accounting for all of it. Built here from public API only."""
        self._write(n=3)
        src = F.records_path(BOOK, self.root)
        arc = src[:-4] + ".1.superseded.csv"
        os.replace(src, arc)
        n = HW.note_reanchor(BOOK, self.fd, archive=os.path.basename(arc),
                             old_anchor="old", new_anchor="new", archive_max_seq=3)
        self.assertTrue(n["ok"], n.get("reason"))
        return arc

    def test_deleting_the_archive_puts_the_book_straight_back_to_REGRESSED(self):
        arc = self._mid_reanchor()
        os.remove(arc)
        st = HW.state(BOOK, [], self.fd)
        self.assertFalse(st["ok"])
        self.assertEqual(st["state"], HW.REGRESSED)
        self.assertIn("GONE", st.get("reanchor_check", ""))
        # and the write door refuses too, which is where it actually matters
        self.assertFalse(F.record(BOOK, "selfcheck", {}, decl_sha=self.sha,
                                  root=self.root).get("wrote"))

    def test_an_empty_stream_with_an_intact_archive_reads_REANCHORED_not_OK(self):
        """A re-anchored book and an untouched one must not read the same."""
        self._mid_reanchor()
        st = HW.state(BOOK, [], self.fd)
        self.assertTrue(st["ok"])
        self.assertEqual(st["state"], HW.REANCHORED)
        self.assertIn("RE-ANCHORED", st["reason"])

    def test_an_archive_that_does_NOT_account_for_the_whole_gap_is_refused(self):
        """The note claims less than the mark remembers, so rows are still unexplained."""
        self._write(n=5)
        src = F.records_path(BOOK, self.root)
        arc = src[:-4] + ".1.superseded.csv"
        os.replace(src, arc)
        HW.note_reanchor(BOOK, self.fd, archive=os.path.basename(arc),
                         old_anchor="o", new_anchor="n", archive_max_seq=2)
        # the FILE is what is checked, and it holds 5 -- so this one passes on evidence even
        # though the note understated it. The refusal case is a SHORT archive:
        with open(arc, "w", encoding="utf-8", newline="") as fh:
            fh.write("seq,ts,kind,book,decl_sha,prev_hash,row_hash\n")
            fh.write("00000001,t,selfcheck,%s,a,b,c\n" % BOOK)
        st = HW.state(BOOK, [], self.fd)
        self.assertFalse(st["ok"])
        self.assertIn("does NOT account for the gap", st.get("reanchor_check", ""))

    def test_a_TRUNCATED_stream_with_no_reanchor_is_still_refused(self):
        """The positive control: the original guard must still bite."""
        self._write(n=5)
        st = HW.state(BOOK, [], self.fd)
        self.assertFalse(st["ok"])
        self.assertEqual(st["state"], HW.REGRESSED)
        self.assertIn("no re-anchor recorded", st.get("reanchor_check", ""))


class TestAdvanceDoesNotEatTheNote(Base):
    """(4) - a defect I introduced and the suite caught."""

    def test_an_ordinary_append_preserves_the_reanchor_note(self):
        self._write(n=2)
        new = self._amend()
        F.reanchor_stream(BOOK, self.root)
        self.assertEqual(len(HW.reanchors(BOOK, self.fd)), 1)
        F.record(BOOK, "selfcheck", {}, decl_sha=new, root=self.root)
        self.assertEqual(len(HW.reanchors(BOOK, self.fd)), 1,
                         "advance rewrote the whole entry and dropped it")

    def test_the_mark_is_never_lowered_by_a_reanchor(self):
        self._write(n=6)
        before = HW.mark_for(BOOK, self.fd)
        self._amend()
        F.reanchor_stream(BOOK, self.root)
        self.assertGreaterEqual(HW.mark_for(BOOK, self.fd), before)


class TestTheAllowlistAndTheDiagnosis(Base):
    """(5) and (6)."""

    def test_the_allowlist_is_exactly_the_two_books_don_named(self):
        self.assertEqual(tuple(F.REANCHOR_ALLOWLIST),
                         ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin"))

    def test_the_allowlist_is_a_committed_literal_and_not_read_from_the_environment(self):
        """A capability would let a third book be re-anchored without a diff."""
        with open(os.path.join(REPO, "valuation", "edge", "fleet.py"), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and any(
                    getattr(t, "id", "") == "REANCHOR_ALLOWLIST" for t in n.targets):
                self.assertIsInstance(n.value, ast.Tuple)
                for e in n.value.elts:
                    self.assertIsInstance(e, ast.Constant)
                return
        self.fail("REANCHOR_ALLOWLIST is not a literal assignment")

    def test_a_moved_anchor_is_diagnosed_by_name_and_names_the_remedy(self):
        self._write(n=2)
        new = self._amend()
        m = F.moved_anchor(BOOK, self.root, new)
        self.assertTrue(m["moved"])
        txt = F._chain_broken_reason(BOOK, self.root, new,
                                     F.verify_chain(BOOK, self.root, decl_sha=new))
        self.assertIn("AMENDED AFTER THIS STREAM'S FIRST ROW", txt)
        self.assertIn("reanchor_stream", txt)
        self.assertIn("before the arming", txt)

    def test_an_UNmoved_anchor_is_not_diagnosed_as_moved(self):
        """The positive control: the diagnosis must not fire on every break."""
        self._write(n=2)
        self.assertFalse(F.moved_anchor(BOOK, self.root, self.sha)["moved"])
        ch = {"ok": False, "reason": "row_hash mismatch at row 1"}
        self.assertEqual(F._chain_broken_reason(BOOK, self.root, self.sha, ch),
                         "row_hash mismatch at row 1")

    def test_the_cycle_step_is_self_extinguishing(self):
        """Once repaired, a second call does nothing - so it cannot loop on the service."""
        self._write(n=2)
        self._amend()
        self.assertTrue(F.reanchor_stream(BOOK, self.root)["ok"])
        again = F.reanchor_stream(BOOK, self.root)
        self.assertFalse(again["ok"])
        self.assertIn("moved anchor is NOT the fault", again["reason"])

    def test_a_dry_run_cycle_reanchors_nothing(self):
        with open(os.path.join(REPO, "valuation", "edge", "fleet.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("if not write:", src.split("reanchored = {}")[1][:800],
                      "the step must be gated on `write`")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
