"""THE DEPLOYED-IMAGE GAP, PART 2 — the declarations themselves never reached the image.

**FOUND IN PRODUCTION, NOT IN A TEST.** `fleet-cycle.yml` run #1 returned
`books_declared: 0` on a service where `entry_rules_registered` was non-empty and
`assignment_provider_registered` was true. The rules were there; the BOOKS were not.

TWO STACKED GAPS IN `.dockerignore`, and neither is fixed by the other:

  * **`*.md` is excluded** (only `!README.md` negated), so no `DECL_*.md` ships.
  * **`.git` is excluded**, so `declaration_commit` cannot run `git log` there — **shipping
    the markdown alone would have turned zero books into eighteen books that all refuse.**

So the commit EVIDENCE has to travel with the declaration. These pin that it does, that the
strong path is untouched where git exists, and that the weaker path SAYS it is weaker.

    python tests/test_fleet_manifest.py
"""
from __future__ import annotations

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
sys.path.insert(0, os.path.join(REPO, "scripts"))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet as F                  # noqa: E402
from valuation.edge import assignment as A             # noqa: E402
import fleet_export_declarations as EX                 # noqa: E402
from test_fleet_harness import _repo, _seed_selfcheck, BOOK   # noqa: E402


def _image(manifest_src=None):
    """A root shaped like the DEPLOYED IMAGE: `data_export/` and nothing else that matters.

    No `DECL_*.md` and no `.git`, which is exactly what `COPY . .` under this
    `.dockerignore` produces -- so a test that passes here is a claim about production.
    """
    root = tempfile.mkdtemp(prefix="image_")
    os.makedirs(os.path.join(root, "data_export"), exist_ok=True)
    src = manifest_src or os.path.join(REPO, F.MANIFEST_REL)
    if os.path.exists(src):
        shutil.copy(src, os.path.join(root, F.MANIFEST_REL))
    return root


class TheImageHasNoDeclarations(unittest.TestCase):

    def test_dockerignore_excludes_BOTH_markdown_and_git(self):
        """The two facts the manifest exists for. If either changes, revisit the design."""
        with io.open(os.path.join(REPO, ".dockerignore"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]
        self.assertIn("*.md", lines)
        self.assertIn(".git", lines)
        self.assertNotIn("!DECL_*.md", lines,
                         "if declarations are now shipped directly, the manifest fallback "
                         "should be re-read rather than left as the only path")

    def test_a_root_with_no_markdown_finds_the_books_via_the_manifest(self):
        root = _image()
        self.assertEqual([f for f in os.listdir(root) if f.startswith("DECL_")], [])
        got = F.declared_books(root)
        self.assertGreaterEqual(len(got), 17)
        self.assertTrue(all(d["parses"] for d in got))
        self.assertTrue(all(d.get("source") == "manifest" for d in got))
        shutil.rmtree(root, ignore_errors=True)

    def test_with_NO_manifest_and_no_markdown_it_reports_zero_and_does_not_pretend(self):
        """Production's actual state before this fix, reproduced."""
        root = tempfile.mkdtemp(prefix="image_bare_")
        self.assertEqual(F.declared_books(root), [])
        self.assertEqual(F.cycle(root)["books_declared"], 0)
        shutil.rmtree(root, ignore_errors=True)


class TheEvidenceGradeIsAlwaysReported(unittest.TestCase):

    def test_a_worktree_uses_GIT_and_never_consults_the_manifest(self):
        """The strong path is UNTOUCHED where git exists -- that is the whole point of a
        fallback rather than a replacement."""
        root = _repo(book=BOOK)
        try:
            _seed_selfcheck(root, BOOK)
            g = F.may_fill(BOOK, root)
            self.assertTrue(g["ok"], g.get("reason"))
            self.assertEqual(g["evidence"], "git")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_image_uses_MANIFEST_and_says_so(self):
        root = _image()
        try:
            A.register()
            g = F.may_fill("f1_fill_ab", root)
            self.assertEqual(g.get("evidence"), "manifest")
            # Still gated on the self-check, exactly as a worktree book is.
            self.assertEqual(g["code"], "SELFCHECK_ABSENT")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_manifest_book_still_passes_the_FULL_gate_when_the_selfcheck_lands(self):
        root = _image()
        try:
            A.register()
            sha = F.declaration_manifest(root)["books"]["f1_fill_ab"]["decl_sha"]
            F.record("f1_fill_ab", "selfcheck",
                     {"fate": "pass", "detail": F.harness_fingerprint()},
                     decl_sha=sha, root=root)
            g = F.may_fill("f1_fill_ab", root)
            self.assertTrue(g["ok"], g.get("reason"))
            self.assertEqual(g["evidence"], "manifest")
            self.assertEqual(g["decl_sha"], sha)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_book_absent_from_the_manifest_is_REFUSED_not_invented(self):
        root = _image()
        try:
            g = F.may_fill("f_not_a_book", root)
            self.assertFalse(g["ok"])
            self.assertEqual(g["code"], "DECLARATION_MISSING")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_corrupt_manifest_is_refused_rather_than_read_optimistically(self):
        root = _image()
        try:
            with io.open(os.path.join(root, F.MANIFEST_REL), "w", encoding="utf-8") as fh:
                fh.write("{not json")
            man = F.declaration_manifest(root)
            self.assertFalse(man["ok"])
            self.assertIn("not valid JSON", man["reason"])
            self.assertEqual(F.may_fill("f1_fill_ab", root)["code"], "DECLARATION_MISSING")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_wrong_schema_manifest_is_refused(self):
        root = _image()
        try:
            with io.open(os.path.join(root, F.MANIFEST_REL), "w", encoding="utf-8") as fh:
                json.dump({"schema": "other/9", "books": {"f1_fill_ab": {}}}, fh)
            self.assertFalse(F.declaration_manifest(root)["ok"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TheManifestOnlyCarriesVerifiedBooks(unittest.TestCase):

    def setUp(self):
        self.payload = EX.build(REPO)

    def test_every_exported_book_was_committed_ALONE(self):
        self.assertTrue(self.payload["books"])
        for b, v in self.payload["books"].items():
            self.assertTrue(v["committed_alone"], b)
            self.assertEqual(v["touched"], ["DECL_%s.md" % b], b)
            self.assertEqual(len(v["commit"]), 40, b)

    def test_the_prose_DRAFTS_are_SKIPPED_with_a_reason_and_never_exported(self):
        """A draft is not a declaration. Skipping it silently would make "not a book" and
        "a book whose declaration is broken" indistinguishable."""
        self.assertTrue(self.payload["skipped"])
        for b in self.payload["skipped"]:
            self.assertNotIn(b, self.payload["books"])
            self.assertTrue(self.payload["skipped"][b])

    def test_the_TEST_BOOK_is_exported_like_every_other_verified_book(self):
        """L7, decided by Don on 2026-08-24: leave it exactly as it is.

        A manifest that omits things somebody decided were uninteresting cannot be trusted
        about the things it includes. The moment one book is left out on grounds of taste,
        every absence becomes ambiguous — and the whole value of this artifact is that an
        absence means exactly one thing: the commit check failed.

        The test-book needs no special case because it declares itself: `utility` class, so it
        charges no trial in any domain and no meter is ever read on it, and CLOSED in the
        session it was declared. Visible, labelled and closed is strictly more informative than
        absent.
        """
        self.assertIn("testbook", self.payload["books"], sorted(self.payload["books"]))
        b = self.payload["books"]["testbook"]
        # Held to exactly the same bar as every other book, which is the point.
        self.assertTrue(b["committed_alone"])
        self.assertEqual(b["touched"], ["DECL_testbook.md"])
        # ...and it is self-labelling rather than filtered.
        decl = b.get("declaration") or {}
        self.assertEqual(decl.get("hypothesis_class"), "utility", decl.get("hypothesis_class"))

    def test_the_exporter_carries_no_book_name_it_could_filter_on(self):
        """The exclusion rule is MECHANICAL (verified or not) and never EDITORIAL. A book name
        appearing as a literal in the exporter's code is how an editorial filter starts.

        Read from the SYNTAX TREE with docstrings stripped, because the module's prose names
        `DECL_testbook.md` on purpose — recording the decision to keep it — and a grep would
        fire on the very sentence that documents the rule. That is this repository's most
        repeated test defect and it is not repeated here.
        """
        import ast

        tree = ast.parse(io.open(EX.__file__, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    node.body = node.body[1:]
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                low = node.value.lower()
                self.assertNotIn("testbook", low,
                                 "a book name is a literal in the exporter's CODE — an "
                                 "editorial filter starts exactly here")

    def test_the_decl_sha_matches_the_real_file_byte_for_byte(self):
        """The manifest's hash is what the chain anchors on in the image, so it has to BE the
        file's hash and not a re-serialisation of the parsed block."""
        for b, v in self.payload["books"].items():
            with io.open(os.path.join(REPO, "DECL_%s.md" % b), encoding="utf-8") as fh:
                self.assertEqual(v["decl_sha"], F.declaration_sha(fh.read()), b)

    def test_it_carries_the_evidence_note_so_the_weakening_travels_with_it(self):
        self.assertIn("WEAKER", self.payload["evidence_note"])
        self.assertIn("manifest", self.payload["evidence_note"])

    def test_it_refuses_to_write_an_EMPTY_manifest(self):
        """An empty manifest would silently disarm the whole fleet in the image."""
        real = EX.build
        try:
            EX.build = lambda root=None: {"schema": EX.SCHEMA, "books": {},
                                          "skipped": {"x": "y"}}
            self.assertEqual(EX.main([]), 1)
        finally:
            EX.build = real


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
