"""AUDIT #5 H3 — the high-water mark, and the backup that carries it off the service.

THE DEFECT THIS SUITE EXISTS FOR IS MEASURED, NOT ASSUMED. `test_the_audit_s_exact_scenario_
whole_file_loss_is_caught` deletes a book's stream, asserts that `verify_chain` STILL RETURNS
OK — which is the audit's finding, and the reason a chain alone is not enough — and then
asserts that the write is refused anyway. A tamper-evident record that silently heals over its
own data loss is worse than one that fails loudly.

The rest is written against the ways a counter-fact stops being one:

  * IT MUST LIVE OUTSIDE THE FILE IT DESCRIBES (`test_the_mark_is_not_inside_the_stream_it_
    describes`), or it is lost by the same event.
  * IT MUST BE MONOTONIC (`test_the_mark_never_goes_DOWN`). A mark that follows the stream
    down is a mark that agrees with the loss.
  * IT MUST REFUSE EVERY KIND, INCLUDING A REFUSAL (`test_even_a_REFUSAL_row_cannot_be_
    appended_to_a_regressed_stream`) — otherwise the first thing written to a truncated stream
    is an official-looking row that continues the false chain.
  * AN UNREADABLE MARK MUST NOT BE TREATED AS AN ABSENT ONE (`test_an_UNREADABLE_mark_is_
    refused_and_never_clobbered`), because it may hold a HIGHER number than the stream does.
  * AND THE LIMIT IS PINNED TOO (`test_the_honest_limit_a_whole_directory_loss_is_NOT_caught`),
    so nobody reads this as protection it does not give.

Run: python tests/test_fleet_highwater.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                     # noqa: E402
from valuation.edge import fleet_export as EX             # noqa: E402
from valuation.edge import fleet_highwater as HW          # noqa: E402

BOOK = "hwbook"
SHA = "a" * 64


class _Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="hw_")
        os.makedirs(F.fleet_dir(self.root), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _rows(self, n, book=BOOK):
        for i in range(n):
            r = F.record(book, "refusal", {"refusal_code": "X", "detail": str(i)},
                         decl_sha=SHA, root=self.root)
            self.assertTrue(r.get("wrote"), r)

    @property
    def fdir(self):
        return F.fleet_dir(self.root)


class TheMarkItself(_Base):

    def test_observed_max_reads_the_stream_and_an_empty_one_is_zero(self):
        self.assertEqual(HW.observed_max([]), 0)
        self.assertEqual(HW.observed_max([{"seq": "003"}, {"seq": "011"}, {"seq": "007"}]), 11)
        # A junk seq is skipped rather than crashing or counting as zero-and-highest.
        self.assertEqual(HW.observed_max([{"seq": "x"}, {"seq": "4"}]), 4)

    def test_the_mark_is_not_inside_the_stream_it_describes(self):
        """The whole design. A counter-fact stored in the file it is a counter-fact ABOUT is
        lost by the same event that makes it necessary."""
        self._rows(2)
        self.assertNotEqual(HW.mark_path(self.fdir), F.records_path(BOOK, self.root))
        self.assertTrue(os.path.exists(HW.mark_path(self.fdir)))
        # ...and deleting the stream leaves the mark standing.
        os.remove(F.records_path(BOOK, self.root))
        self.assertTrue(os.path.exists(HW.mark_path(self.fdir)))

    def test_the_mark_never_goes_DOWN(self):
        """A mark that follows the stream down is a mark that agrees with the loss."""
        self._rows(3)
        HW.advance(BOOK, 1, self.fdir)
        self.assertEqual(HW.read(self.fdir)["books"][BOOK]["max_seq"], 3)
        HW.advance(BOOK, 9, self.fdir)
        self.assertEqual(HW.read(self.fdir)["books"][BOOK]["max_seq"], 9)

    def test_an_empty_stream_with_no_mark_is_FIRST_SIGHT_and_not_a_failure(self):
        st = HW.state(BOOK, [], self.fdir)
        self.assertTrue(st["ok"])
        self.assertEqual(st["state"], HW.FIRST_SIGHT)

    def test_an_UNREADABLE_mark_is_refused_and_never_clobbered(self):
        """It may hold a HIGHER number than the stream does, so overwriting it would erase the
        only evidence of a loss. `MA6`'s direction rule: the safe error over-reports."""
        with open(HW.mark_path(self.fdir), "w", encoding="utf-8") as f:
            f.write("{ not json")
        st = HW.state(BOOK, [{"seq": "001"}], self.fdir)
        self.assertFalse(st["ok"])
        self.assertEqual(st["state"], HW.UNREADABLE)
        adv = HW.advance(BOOK, 5, self.fdir)
        self.assertFalse(adv["ok"])
        with open(HW.mark_path(self.fdir), encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ not json")

    def test_a_wrong_schema_is_refused_rather_than_read_optimistically(self):
        with open(HW.mark_path(self.fdir), "w", encoding="utf-8") as f:
            json.dump({"schema": "something/9", "books": {}}, f)
        self.assertEqual(HW.read(self.fdir)["state"], HW.UNREADABLE)

    def test_there_is_no_reset_function_on_purpose(self):
        """Recovering from a real loss is a human decision about evidence. A one-call reset is
        the affordance that turns it into a reflex."""
        for name in ("reset", "clear", "forget", "lower", "delete"):
            self.assertFalse(hasattr(HW, name), name)


class TheRefusal(_Base):

    def test_the_audit_s_exact_scenario_whole_file_loss_is_caught(self):
        """AUDIT #5 H3, reproduced. The chain cannot see the loss; the mark can."""
        self._rows(3)
        self.assertEqual(F.verify_chain(BOOK, self.root, SHA)["ok"], True)
        os.remove(F.records_path(BOOK, self.root))

        # THE FINDING, asserted rather than described: the chain is BLIND to this.
        chain = F.verify_chain(BOOK, self.root, SHA)
        self.assertTrue(chain["ok"], "the audit's premise no longer holds — re-read H3")
        self.assertTrue(chain.get("vacuous"))

        st = HW.state(BOOK, F.read_records(BOOK, self.root)["rows"], self.fdir)
        self.assertEqual(st["state"], HW.REGRESSED)
        self.assertEqual((st["observed"], st["mark"]), (0, 3))

        r = F.record(BOOK, "refusal", {"refusal_code": "Y"}, decl_sha=SHA, root=self.root)
        self.assertFalse(r.get("wrote"), r)
        self.assertIn("3 was already recorded", r["reason"])
        # ...and it did not quietly create the file it refused to append to.
        self.assertFalse(os.path.exists(F.records_path(BOOK, self.root)))

    def test_a_TRUNCATED_stream_is_caught_too_not_only_a_deleted_one(self):
        """Truncation re-chains cleanly from row 1, which is the same blindness."""
        self._rows(3)
        rows = F.read_records(BOOK, self.root)["rows"]
        path = F.records_path(BOOK, self.root)
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines(True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines[:3])            # header + 2 rows
        self.assertLess(len(F.read_records(BOOK, self.root)["rows"]), len(rows))
        r = F.record(BOOK, "refusal", {"refusal_code": "Y"}, decl_sha=SHA, root=self.root)
        self.assertFalse(r.get("wrote"), r)
        self.assertEqual(r["highwater"]["state"], HW.REGRESSED)

    def test_even_a_REFUSAL_row_cannot_be_appended_to_a_regressed_stream(self):
        """Letting one through appends it to the very stream whose integrity is in question."""
        self._rows(3)
        os.remove(F.records_path(BOOK, self.root))
        for kind in ("refusal", "selfcheck", "fill", "meter_read", "close"):
            r = F.record(BOOK, kind, {"detail": "x"}, decl_sha=SHA, root=self.root)
            self.assertFalse(r.get("wrote"), kind)

    def test_an_ordinary_append_is_completely_unaffected(self):
        """The negative control. A guard that blocks the normal path is not a guard."""
        self._rows(3)
        r = F.record(BOOK, "refusal", {"refusal_code": "X"}, decl_sha=SHA, root=self.root)
        self.assertTrue(r.get("wrote"), r)
        self.assertEqual(len(F.read_records(BOOK, self.root)["rows"]), 4)
        self.assertEqual(HW.read(self.fdir)["books"][BOOK]["max_seq"], 4)

    def test_one_book_s_loss_does_not_block_another_book(self):
        self._rows(2, book=BOOK)
        self._rows(2, book="other")
        os.remove(F.records_path(BOOK, self.root))
        self.assertFalse(F.record(BOOK, "refusal", {}, decl_sha=SHA,
                                  root=self.root).get("wrote"))
        self.assertTrue(F.record("other", "refusal", {}, decl_sha=SHA,
                                 root=self.root).get("wrote"))

    def test_the_mark_is_not_advanced_by_a_write_that_did_not_happen(self):
        """Advancing on a failed append would move the mark past rows that are not on disk.

        TWO CASES, AND THE SECOND IS THE ONE THAT MATTERS. An unknown kind returns before the
        writer is reached at all, so it exercises nothing about the guard — a tripwire run
        caught that flipping `if res.get("wrote")` to `if True` left this test green. The
        second case drives the real branch: the append itself declines while `record` runs to
        completion.
        """
        self._rows(2)
        before = HW.read(self.fdir)["books"][BOOK]["max_seq"]

        r = F.record(BOOK, "not_a_kind", {}, decl_sha=SHA, root=self.root)
        self.assertFalse(r.get("wrote"))
        self.assertEqual(HW.read(self.fdir)["books"][BOOK]["max_seq"], before)

        # The append DECLINES (an idempotent no-op is the live shape of this) and the mark
        # must stay where it is.
        import valuation.edge.append_only as AO

        real = AO.append
        AO.append = lambda *a, **k: {"ok": True, "wrote": False, "already_present": True}
        try:
            r2 = F.record(BOOK, "refusal", {"refusal_code": "X"}, decl_sha=SHA, root=self.root)
            self.assertFalse(r2.get("wrote"), r2)
        finally:
            AO.append = real
        self.assertEqual(HW.read(self.fdir)["books"][BOOK]["max_seq"], before,
                         "the mark advanced past a row that was never written")

    def test_the_backup_guard_refuses_a_payload_that_lost_rows(self):
        """`LA2`'s lesson applied in advance: a backup that comes back SHORTER than the
        committed copy must fail the step, not overwrite it. Proved through the CLI the
        workflow actually calls, rather than through the helper it happens to use."""
        self._rows(3)
        full = EX.payload(self.root)
        committed = tempfile.mkdtemp(prefix="hwguard_")
        fresh = tempfile.mkdtemp(prefix="hwguard2_")
        try:
            EX.write(full, committed)
            short = {"schema": full["schema"], "highwater": full["highwater"],
                     "books": {BOOK: dict(full["books"][BOOK],
                                          rows=full["books"][BOOK]["rows"][:1])}}
            pj = os.path.join(committed, "short.json")
            with open(pj, "w", encoding="utf-8") as f:
                json.dump({"export": short}, f)
            rc = EX.main(["--from-json", pj, "--out", fresh, "--guard-against", committed])
            self.assertEqual(rc, 1, "a shorter backup was accepted")

            # ...and the negative control: the FULL payload passes the same guard.
            pj2 = os.path.join(committed, "full.json")
            with open(pj2, "w", encoding="utf-8") as f:
                json.dump({"export": full}, f)
            self.assertEqual(
                EX.main(["--from-json", pj2, "--out", fresh, "--guard-against", committed]), 0)
        finally:
            shutil.rmtree(committed, ignore_errors=True)
            shutil.rmtree(fresh, ignore_errors=True)

    def test_the_honest_limit_a_whole_directory_loss_is_NOT_caught(self):
        """Pinned so nobody reads this as protection it does not give. The mark is a SIBLING,
        so it dies with the directory — which is precisely why the export exists."""
        self._rows(3)
        shutil.rmtree(self.fdir)
        os.makedirs(self.fdir, exist_ok=True)
        st = HW.state(BOOK, [], self.fdir)
        self.assertTrue(st["ok"])
        self.assertEqual(st["state"], HW.FIRST_SIGHT)
        self.assertTrue(F.record(BOOK, "refusal", {}, decl_sha=SHA,
                                 root=self.root).get("wrote"))

    def test_rows_with_no_mark_are_reported_even_though_they_do_not_block(self):
        self._rows(3)
        os.remove(HW.mark_path(self.fdir))
        st = HW.state(BOOK, F.read_records(BOOK, self.root)["rows"], self.fdir)
        self.assertTrue(st["ok"])
        self.assertTrue(st["rows_present"])
        self.assertIn("no high-water mark exists yet", st["reason"])


class TheBackup(_Base):

    def test_the_export_carries_every_book_its_rows_and_the_marks(self):
        self._rows(2, book=BOOK)
        self._rows(2, book="other")
        p = EX.payload(self.root)
        self.assertEqual(p["schema"], EX.SCHEMA)
        self.assertEqual(p["n_books"], 2)
        self.assertEqual(p["n_rows_total"], 4)
        self.assertEqual(p["books"][BOOK]["max_seq"], 2)
        self.assertEqual(p["highwater"]["books"][BOOK]["max_seq"], 2)
        # The rows themselves travel, or it is not a backup.
        self.assertEqual(len(p["books"][BOOK]["rows"]), 2)
        self.assertIn("row_hash", p["books"][BOOK]["columns"])

    def test_the_export_records_a_BROKEN_chain_rather_than_hiding_it(self):
        """A restore that silently reinstates a break as sound is worse than no restore."""
        self._rows(3)
        path = F.records_path(BOOK, self.root)
        with open(path, encoding="utf-8") as f:
            body = f.read()
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(body.replace("refusal", "fill", 1))
        p = EX.payload(self.root)
        self.assertFalse(p["books"][BOOK]["chain"]["ok"])
        self.assertIsNotNone(p["books"][BOOK]["chain"]["reason"])

    def test_the_export_is_a_PURE_READ(self):
        """A backup route that mutated what it backs up is `PT-WRITER`'s defect in a new place."""
        self._rows(3)
        rec, mark = F.records_path(BOOK, self.root), HW.mark_path(self.fdir)
        before = (open(rec, "rb").read(), open(mark, "rb").read())
        EX.payload(self.root)
        EX.payload(self.root)
        self.assertEqual((open(rec, "rb").read(), open(mark, "rb").read()), before)

    def test_the_payload_shape_is_stable_when_there_is_nothing_to_export(self):
        """An unattended backup job cannot ask whether a missing key means zero."""
        empty = tempfile.mkdtemp(prefix="hwempty_")
        try:
            p = EX.payload(empty)
            for k in ("schema", "books", "highwater", "n_books", "n_rows_total", "reason"):
                self.assertIn(k, p, k)
            self.assertEqual((p["n_books"], p["n_rows_total"]), (0, 0))
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_the_admin_route_exists_and_is_token_gated_like_its_precedent(self):
        """Asserted on the SOURCE, because the route needs a service this test does not have."""
        import ast

        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "valuation", "saas", "app_saas.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                   and n.name == "admin_export_fleet"), None)
        self.assertIsNotNone(fn, "/admin/export-fleet is gone")
        names = {n.func.id for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertIn("_admin_ok", names, "the export route is not token-gated")
        # It must not write. The precedent it copies is read-only and so is this.
        attrs = {n.func.attr for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for writer in ("record", "advance", "append", "write", "seed"):
            self.assertNotIn(writer, attrs, writer)


class TheImage(unittest.TestCase):
    """WHAT REACHES THE DEPLOYED IMAGE, applied from `.dockerignore` rather than assumed.

    `fleet_gates` already records why this matters: a rule that reads a licensed export passes
    in a worktree and FAILS on the service, which is the worst place to find out. The same
    trap applies in reverse here — a backup route whose module did not ship would 500 on the
    one machine that holds the data.

    THE HONEST LIMIT: Docker is not installed on the machine this was written on, so the image
    was NOT built. These assert the image's SHAPE from its own exclusion rules; the deployed
    process reports the rest itself through `fleet_gates.image_audit()`.
    """

    REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _patterns(self):
        pats = []
        with open(os.path.join(self.REPO, ".dockerignore"), encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith("#"):
                    pats.append(t)
        return pats

    def _excluded(self, rel):
        """True if `.dockerignore` keeps `rel` out of the build context."""
        import fnmatch

        parts = rel.replace("\\", "/").split("/")
        out = False
        for pat in self._patterns():
            neg = pat.startswith("!")
            body = pat[1:] if neg else pat
            body = body.rstrip("/")
            hit = any(fnmatch.fnmatch(c, body) for c in parts) or \
                fnmatch.fnmatch(rel.replace("\\", "/"), body)
            if hit:
                out = not neg
        return out

    def test_the_new_modules_SHIP(self):
        """A backup route whose module is excluded 500s on the only machine holding the data."""
        for rel in ("valuation/edge/fleet_highwater.py",
                    "valuation/edge/fleet_export.py",
                    "valuation/saas/app_saas.py"):
            self.assertFalse(self._excluded(rel), rel + " would not reach the image")
            self.assertTrue(os.path.exists(os.path.join(self.REPO, rel)), rel)

    def test_the_record_streams_do_NOT_ship_and_that_is_correct(self):
        """`data/` is excluded wholesale. The streams are runtime state on the persistent
        disk, not build artifacts — baking a snapshot into the image would put a stale copy of
        an append-only record where a reader could mistake it for the record."""
        self.assertTrue(self._excluded("data/fleet/f1_fill_ab.csv"))
        self.assertTrue(self._excluded("data/fleet/_highwater.json"))

    def test_the_rendered_BACKUP_does_ship_because_data_export_is_tracked(self):
        """`data_export/` is where this project publishes things derived out of the ignored
        data root, and `.dockerignore` excludes `data/` and not it."""
        self.assertFalse(self._excluded("data_export/fleet_records/f1_fill_ab.csv"))
        self.assertFalse(self._excluded("data_export/fleet_highwater.json"))

    def test_the_exclusion_probe_is_not_vacuous(self):
        """A probe that returned False for everything would pass all three above by seeing
        nothing. Two known exclusions and two known inclusions, both directions."""
        self.assertTrue(self._excluded("data/raw/anything.csv"))
        self.assertTrue(self._excluded(".env"))
        self.assertFalse(self._excluded("valuation/edge/fleet.py"))
        self.assertFalse(self._excluded("requirements.txt"))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
