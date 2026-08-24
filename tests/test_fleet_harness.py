"""S3-I1 - the fleet harness. The two guards the register exists to make mechanical.

WHAT THESE TESTS PIN, and both are named in the task rather than inferred.

**THE APPEND-ONLY GUARD.** A fleet record stream is append-only by construction, keyed on a
monotone sequence rather than a date, because a book records many orders per day and
`index_mark.append_row`'s date key would silently swallow every fill after the first each day
(register section E2). What is pinned: a duplicate key is a NO-OP that returns the row ALREADY
ON DISK, an out-of-order key is REFUSED, a schema widening is REFUSED, a ragged file is REFUSED
rather than normalised, and the previous bytes survive as an exact PREFIX of the new file.

**THE DECLARATION-BEFORE-FILL GUARD.** The commit is the tamper-evidence, so it is checked
against git and not against a claim: the declaration's introducing commit must EXIST, be an
ANCESTOR of HEAD, and have touched EXACTLY ONE file. Every one of those is tested against a
REAL temporary repository, because checking a commit rule against a stub checks the stub.

Third, and it is the one a reader will most want to distrust: `verify_chain` is proved to FIRE
by tampering, to report an empty stream as VACUOUS rather than PASSING (`O21-D2`'s C5), and to
hash WHAT IS PERSISTED -- the first cut hashed native types against a CSV that stores strings
and could not verify a single row it had just written.

Fourth: the trial convention is mechanical. Reading a meter WRITES a record, so "nobody peeked"
is a dated fact rather than a memory (register section E4), and the first read is flagged as
the one that books the charge.

Fifth: the S3-I3 seam refuses in BOTH directions and this module builds no assignment model.

    python tests/test_fleet_harness.py
"""
from __future__ import annotations

import ast
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import append_only as AO      # noqa: E402
from valuation.edge import fleet as F             # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = "t1"


def _decl_text(book=BOOK, **over):
    d = {
        "book": book, "domain": "options", "hypothesis_class": "cost",
        "entry_rule": "fixture", "structure": {"strike_selection": "moneyness"},
        "universe": "fixture", "sizing": "1", "concurrency_cap": 10, "side": "long",
        # `sells_premium` is MANDATORY on every book -- r1's S3-I3 rule, adopted whole: an
        # absent field would let a short book pass by OMISSION.
        "sells_premium": False,
        "records_schema": [],
        "verdict_horizon": {"expected_fills_per_month": 30, "min_effect": 0.1, "sigma": 1.0,
                            "rho": 3.0, "alpha": 0.05, "fills_needed": 60,
                            "earliest_honest_read": "2026-10-23"},
        "verdict_grammar": ["SUPPORTED", "NO CONCLUSION"],
        "trial": {"domain": "options", "charged_at": "first_verdict_read"},
        "o11_sentence": F.O11_SENTENCE,
    }
    d.update(over)
    return "# DECL\n\n```json\n" + json.dumps(d, indent=2) + "\n```\n"


def _git(root, *a):
    return subprocess.run(["git", "-C", root] + list(a), capture_output=True, text=True)


def _repo(alone=True, book=BOOK, text=None):
    root = tempfile.mkdtemp(prefix="fleet_t_")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.local")
    _git(root, "config", "user.name", "t")
    io.open(os.path.join(root, "README.md"), "w").write("x\n")
    _git(root, "add", "README.md")
    _git(root, "commit", "-q", "-m", "base")
    io.open(os.path.join(root, "DECL_" + book + ".md"), "w", encoding="utf-8",
            newline="\n").write(text if text is not None else _decl_text(book))
    _git(root, "add", "DECL_" + book + ".md")
    if not alone:
        io.open(os.path.join(root, "other.py"), "w").write("# alongside\n")
        _git(root, "add", "other.py")
    _git(root, "commit", "-q", "-m", "declare")
    return root


def _sha(root, book=BOOK):
    return F.declaration_sha(io.open(os.path.join(root, "DECL_" + book + ".md"),
                                     encoding="utf-8").read())


def _seed_selfcheck(root, book=BOOK):
    F.record(book, "selfcheck", {"fate": "pass", "detail": F.harness_fingerprint()},
             decl_sha=_sha(root, book), root=root)


# =======================================================================================
# THE APPEND-ONLY GUARD
# =======================================================================================
class AppendOnly(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ao_")
        self.p = os.path.join(self.d, "b.csv")
        self.cols = ("seq", "kind", "note")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _add(self, seq, **kw):
        row = {"seq": seq, "kind": "fill", "note": ""}
        row.update(kw)
        return AO.append(row, self.p, key="seq", columns=self.cols, append_only=True)

    def test_a_duplicate_key_is_a_noop_returning_the_row_already_on_disk(self):
        self._add("00000001", note="first")
        r = self._add("00000001", note="RECOMPUTED")
        self.assertTrue(r["ok"])
        self.assertFalse(r["wrote"])
        self.assertTrue(r["already_present"])
        # THE POINT: the row on disk, never the freshly computed one. They differ here on
        # purpose -- returning the recomputed row would report a value the file does not hold.
        self.assertEqual(r["existing"]["note"], "first")

    def test_an_out_of_order_key_is_refused(self):
        self._add("00000002")
        r = self._add("00000001")
        self.assertFalse(r["ok"])
        self.assertFalse(r["wrote"])
        self.assertTrue(r["would_modify"])

    def test_widening_the_schema_on_an_append_only_write_is_refused(self):
        self._add("00000001")
        r = AO.append({"seq": "00000002", "kind": "fill", "note": "", "extra": "x"},
                      self.p, key="seq", columns=tuple(self.cols) + ("extra",),
                      append_only=True)
        self.assertFalse(r["ok"])
        self.assertIn("refusing to widen the header", r["reason"])

    def test_a_ragged_file_is_refused_and_never_normalised(self):
        self._add("00000001")
        with io.open(self.p, "a", encoding="utf-8", newline="") as fh:
            fh.write("00000002,fill,note,SURPLUS\n")
        before = open(self.p, "rb").read()
        r = self._add("00000003")
        self.assertFalse(r["ok"])
        self.assertIn("does not match its header", r["reason"])
        self.assertEqual(open(self.p, "rb").read(), before, "a refusal must not rewrite")

    def test_the_previous_bytes_remain_an_exact_prefix(self):
        self._add("00000001")
        before = open(self.p, "rb").read()
        self._add("00000002")
        after = open(self.p, "rb").read()
        self.assertTrue(after.startswith(before))
        self.assertGreater(len(after), len(before))

    def test_a_key_absent_from_the_row_is_refused_rather_than_written_blank(self):
        r = AO.append({"kind": "fill"}, self.p, key="seq", columns=self.cols)
        self.assertFalse(r["ok"])
        self.assertFalse(os.path.exists(self.p))

    def test_a_column_in_neither_the_file_nor_columns_is_reported_not_silently_dropped(self):
        r = AO.append({"seq": "00000001", "kind": "fill", "note": "", "typo": "x"},
                      self.p, key="seq", columns=self.cols)
        self.assertTrue(r["ok"])
        self.assertEqual(r["ignored_fields"], ["typo"])

    def test_index_mark_and_the_fleet_share_ONE_implementation(self):
        """B7: `append_row` must DELEGATE, read from the syntax tree and not grepped."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "index_mark.py"),
                      encoding="utf-8").read()
        fn = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "append_row"]
        self.assertEqual(len(fn), 1)
        calls = [n for n in ast.walk(fn[0])
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "append"]
        self.assertTrue(calls, "append_row no longer delegates; that is the B7 split")
        # And the fleet reaches the same door.
        fsrc = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                       encoding="utf-8").read()
        names = {a.name for n in ast.walk(ast.parse(fsrc))
                 if isinstance(n, ast.ImportFrom) for a in n.names}
        self.assertIn("append_only", names)

    def test_append_row_honours_a_CALLER_S_columns_and_does_not_hard_code_its_own(self):
        """The regression the full gate caught and my own 200-case sweep could not.

        `append_row` takes `columns=` so the SPMO sibling can reuse this writer with its own
        schema. The first cut of the delegation hard-coded `ROW_COLUMNS`, so the argument was
        ACCEPTED AND SILENTLY DROPPED and a correct write came back refused for widening a
        header nobody had asked to widen. A branch sweep varies the DATA; this defect lived in
        the SIGNATURE, which is why `tests/test_reported_benchmark.py` found it and the
        differential harness did not.
        """
        from valuation.screener import index_mark as IM
        sib = ("date", "day_n", "valquo_pct", "valquo_src", "spmo_pct", "excess_pp")
        p = os.path.join(self.d, "sibling.csv")
        first = {"date": "2026-08-17", "day_n": 12, "valquo_pct": 6.97,
                 "valquo_src": "computed", "spmo_pct": 8.7, "excess_pp": -1.7}
        r1 = IM.append_row(first, p, append_only=True, columns=sib)
        self.assertTrue(r1["ok"] and r1["wrote"], r1)
        self.assertEqual(tuple(r1["columns"]), sib, "the caller's schema was not honoured")
        fwd = dict(first, date="2026-08-18", day_n=13)
        r2 = IM.append_row(fwd, p, append_only=True, columns=sib)
        self.assertTrue(r2["ok"] and r2["wrote"], r2)
        self.assertNotIn("spy_pct", r2["columns"], "the bound series' schema leaked in")

    def test_the_fleet_defines_no_second_csv_writer(self):
        """A `csv.DictWriter` inside `fleet.py` would be exactly the copy E2 refuses."""
        fsrc = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                       encoding="utf-8").read()
        bad = [n for n in ast.walk(ast.parse(fsrc))
               if isinstance(n, ast.Attribute) and n.attr in ("DictWriter", "writer")]
        self.assertEqual(bad, [], "fleet.py writes CSV itself instead of delegating")


# =======================================================================================
# THE DECLARATION-BEFORE-FILL GUARD -- against a REAL repository
# =======================================================================================
class DeclarationBeforeFill(unittest.TestCase):

    def test_a_declaration_committed_alone_and_landed_is_accepted(self):
        root = _repo(alone=True)
        try:
            c = F.declaration_commit(BOOK, root)
            self.assertTrue(c["ok"], c)
            self.assertEqual(c["touched"], ["DECL_" + BOOK + ".md"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_uncommitted_declaration_is_refused(self):
        root = tempfile.mkdtemp(prefix="fleet_t_")
        try:
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@t.local")
            _git(root, "config", "user.name", "t")
            io.open(os.path.join(root, "README.md"), "w").write("x\n")
            _git(root, "add", "README.md")
            _git(root, "commit", "-q", "-m", "base")
            io.open(os.path.join(root, "DECL_" + BOOK + ".md"), "w",
                    encoding="utf-8").write(_decl_text())
            c = F.declaration_commit(BOOK, root)
            self.assertFalse(c["ok"])
            self.assertEqual(c["code"], "DECLARATION_NOT_COMMITTED")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_declaration_committed_on_an_unmerged_branch_is_refused_as_NOT_LANDED(self):
        """The condition mutation found unreachable, now reachable and pinned.

        `declaration_commit` searched only HEAD's history, so a declaration on an unmerged
        branch was never SEEN and the ancestor check was dead code -- and the refusal a reader
        got said "not committed" when the truth was "committed, but not landed here".
        """
        root = tempfile.mkdtemp(prefix="fleet_t_")
        try:
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@t.local")
            _git(root, "config", "user.name", "t")
            io.open(os.path.join(root, "README.md"), "w").write("x\n")
            _git(root, "add", "README.md")
            _git(root, "commit", "-q", "-m", "base")
            base = _git(root, "rev-parse", "HEAD").stdout.strip()
            _git(root, "checkout", "-q", "-b", "side")
            io.open(os.path.join(root, "DECL_" + BOOK + ".md"), "w", encoding="utf-8",
                    newline="\n").write(_decl_text())
            _git(root, "add", "DECL_" + BOOK + ".md")
            _git(root, "commit", "-q", "-m", "declare on a branch")
            _git(root, "checkout", "-q", base)          # HEAD no longer contains it
            c = F.declaration_commit(BOOK, root)
            self.assertFalse(c["ok"])
            self.assertEqual(c["code"], "DECLARATION_NOT_ANCESTOR")
            self.assertIn("not landed", c["reason"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_declaration_landed_alongside_another_file_is_refused(self):
        root = _repo(alone=False)
        try:
            c = F.declaration_commit(BOOK, root)
            self.assertFalse(c["ok"])
            self.assertEqual(c["code"], "DECLARATION_NOT_COMMITTED_ALONE")
            self.assertIn("other.py", c["touched"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_may_fill_refuses_before_the_selfcheck_and_permits_after(self):
        root = _repo()
        try:
            g = F.may_fill(BOOK, root)
            self.assertFalse(g["ok"])
            self.assertEqual(g["code"], "SELFCHECK_ABSENT")
            _seed_selfcheck(root)
            self.assertTrue(F.may_fill(BOOK, root)["ok"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_selfcheck_goes_STALE_when_the_harness_changes(self):
        root = _repo()
        try:
            F.record(BOOK, "selfcheck", {"fate": "pass", "detail": "an-older-fingerprint"},
                     decl_sha=_sha(root), root=root)
            s = F.selfcheck_state(BOOK, root)
            self.assertFalse(s["ok"])
            self.assertEqual(s["state"], "STALE")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_absent_stale_and_failing_are_three_states_not_one(self):
        """"No check has run" and "a check ran and failed" are different facts."""
        root = _repo()
        try:
            self.assertEqual(F.selfcheck_state(BOOK, root)["state"], "ABSENT")
            F.record(BOOK, "selfcheck", {"fate": "fail", "detail": F.harness_fingerprint()},
                     decl_sha=_sha(root), root=root)
            self.assertEqual(F.selfcheck_state(BOOK, root)["state"], "FAILING")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_refusal_is_a_record_and_not_a_crash(self):
        root = _repo()
        try:
            _seed_selfcheck(root)
            F.refuse(BOOK, "MENU_TOO_THIN", "fillable menu 2 < 4", decl_sha=_sha(root),
                     root=root)
            rows = F.read_records(BOOK, root)["rows"]
            ref = [r for r in rows if r["kind"] == "refusal"]
            self.assertEqual(len(ref), 1)
            self.assertEqual(ref[0]["refusal_code"], "MENU_TOO_THIN")
        finally:
            shutil.rmtree(root, ignore_errors=True)


# =======================================================================================
# THE CHAIN -- proved to FIRE, and proved not to pass on nothing
# =======================================================================================
class Chain(unittest.TestCase):

    def test_an_empty_stream_is_VACUOUS_not_PASSING(self):
        root = _repo()
        try:
            c = F.verify_chain(BOOK, root)
            self.assertTrue(c["ok"])
            self.assertTrue(c["vacuous"], "an empty chain must not read as a verified one")
            self.assertEqual(c["n"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_chain_verifies_what_was_written_and_fires_on_a_tamper(self):
        root = _repo()
        try:
            _seed_selfcheck(root)
            sha = _sha(root)
            for i in range(3):
                F.record(BOOK, "fill", {"symbol": "S%d" % i, "fill_price": 1.5 + i,
                                        "qty": 1}, decl_sha=sha, root=root)
            good = F.verify_chain(BOOK, root, decl_sha=sha)
            self.assertTrue(good["ok"], good)
            self.assertFalse(good["vacuous"])
            self.assertEqual(good["n"], 4)

            p = F.records_path(BOOK, root)
            rows, header, err = AO.read_rows(p)
            self.assertIsNone(err)
            rows[2]["fill_price"] = "999.99"
            with io.open(p, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=header)
                w.writeheader()
                for r in rows:
                    w.writerow({k: r.get(k) for k in header})
            bad = F.verify_chain(BOOK, root, decl_sha=sha)
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["broken_at"], 2)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_hash_is_over_what_is_PERSISTED(self):
        """The defect this test exists for: hashing native types against a CSV of strings.

        The first cut hashed `2.5` and stored `"2.5"`, so `verify_chain` reproduced nothing it
        had just written and the whole stream read as broken on its own first run.
        """
        self.assertEqual(F.row_hash("x", {"a": 2.5, "b": 1}),
                         F.row_hash("x", {"a": "2.5", "b": "1"}))
        self.assertEqual(F.row_hash("x", {"a": None}), F.row_hash("x", {"a": ""}))
        self.assertNotEqual(F.row_hash("x", {"a": "1"}), F.row_hash("y", {"a": "1"}))

    def test_the_chain_bound_is_stated_and_not_overclaimed(self):
        """Register E3: the draft says "a tampered row is DETECTED" without its bound."""
        self.assertIn("NOT tamper-proof", F.CHAIN_BOUND)
        root = _repo()
        try:
            _seed_selfcheck(root)
            self.assertIn("NOT tamper-proof", F.verify_chain(BOOK, root)["bound"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


# =======================================================================================
# DECLARATION VALIDATION
# =======================================================================================
class Declarations(unittest.TestCase):

    def _v(self, **over):
        d = F.parse_declaration(_decl_text(**over))["declaration"]
        return F.validate_declaration(d, book=BOOK)

    def test_a_book_declaring_no_extra_columns_is_valid(self):
        """An empty `records_schema` is an ANSWER, not a missing field."""
        self.assertTrue(self._v()["ok"], self._v()["refusals"])

    def test_two_json_blocks_are_refused_rather_than_merged(self):
        t = _decl_text() + "\n```json\n{\"book\": \"other\"}\n```\n"
        r = F.parse_declaration(t)
        self.assertFalse(r["ok"])
        self.assertIn("exactly one", r["reason"])

    def test_the_o11_sentence_must_be_verbatim(self):
        r = self._v(o11_sentence="O11 binds this book, roughly.")
        self.assertIn("O11_SENTENCE_NOT_VERBATIM", r["refusals"])

    def test_a_delta_targeted_strike_must_argue_past_v6opt(self):
        r = self._v(structure={"strike_selection": "delta", "delta": 0.35})
        self.assertIn("DELTA_STRIKE_WITHOUT_V6OPT_ARGUMENT", r["refusals"])
        ok = self._v(structure={"strike_selection": "delta", "delta": 0.35,
                                "v6opt_argument": "moneyness is held fixed within each bucket"})
        self.assertTrue(ok["ok"], ok["refusals"])

    def test_the_verdict_horizon_is_mandatory_field_by_field(self):
        h = {"expected_fills_per_month": 30, "min_effect": 0.1, "sigma": 1.0, "rho": 3.0,
             "alpha": 0.05, "fills_needed": 60, "earliest_honest_read": "2026-10-23"}
        for f in F.REQUIRED_HORIZON_FIELDS:
            bad = dict(h)
            bad.pop(f)
            self.assertIn("MISSING_HORIZON_FIELD:" + f, self._v(verdict_horizon=bad)["refusals"])

    def test_the_trial_must_be_charged_at_first_verdict_read(self):
        r = self._v(trial={"domain": "options", "charged_at": "declaration"})
        self.assertIn("TRIAL_NOT_CHARGED_AT_FIRST_VERDICT_READ", r["refusals"])

    def test_a_utility_book_may_not_charge_a_trial(self):
        r = self._v(hypothesis_class="utility",
                    trial={"domain": "options", "charged_at": "first_verdict_read"})
        self.assertIn("UTILITY_BOOK_CHARGES_A_TRIAL", r["refusals"])
        ok = self._v(hypothesis_class="utility",
                     trial={"domain": "none", "charged_at": "first_verdict_read"})
        self.assertTrue(ok["ok"], ok["refusals"])

    def test_the_book_id_must_match_the_filename(self):
        self.assertIn("BOOK_ID_DOES_NOT_MATCH_FILENAME", self._v(book="somethingelse")["refusals"])


# =======================================================================================
# THE S3-I3 SEAM -- interface only; this module builds no assignment model
# =======================================================================================
class AssignmentSeam(unittest.TestCase):
    """SETTLED WITH r1 2026-08-24, after moving TWICE -- and the middle version was wrong.

    `S3-I1` froze three duck-typed callables before any model existed. Mid-ceremony this
    harness was "reconciled to the landed module": repointed at `short_book.py`'s own five
    function names and importing it at module scope. **That was reverted**, because r1 had
    already built `_AssignmentProvider`, an ADAPTER exposing exactly the three frozen names --
    the interface never needed changing, which is what a published interface is for -- and
    because `assignment.py` states the dependency direction outright: *"fleet does not import
    this module (its check is duck-typed on purpose), so the dependency runs one way only"*,
    with registration *"an explicit CALL and never an import side effect."*

    So what these pin is the CONTRACT BETWEEN TWO LANES, not either lane's vocabulary:
    the harness refuses every short book until something registers a provider, the provider
    r1 ships satisfies the frozen interface, and neither module imports the other in
    production code.
    """

    SHORT = {"sells_premium": True, "side": "short",
             "assignment_model": "at expiry per moneyness",
             "margin_method": "cash_secured_put", "spot_basis": "as_traded",
             "early_assignment_flag": "O21 q-machinery", "return_denominator": "secured_cash"}

    def setUp(self):
        self._saved = F._PROVIDER

    def tearDown(self):
        F._PROVIDER = self._saved

    def test_the_harness_does_NOT_import_the_assignment_model(self):
        """r1's rule, and this file yields to it. Checked on the SYNTAX TREE, not by grep.

        An import-time registration means any path that imports the model to read one number
        -- a script, a test, a notebook -- silently unblocks every short book in the fleet.
        Refusing by default is the safe direction.
        """
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                for a in n.names:
                    imported.add(a.name)
                if n.module:
                    imported.add(n.module)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    imported.add(a.name)
        self.assertIn("append_only", imported, "the import scan saw nothing")
        self.assertNotIn("assignment", imported)
        self.assertNotIn("short_book", imported)

    def test_nothing_is_registered_at_import_and_short_books_are_refused_by_default(self):
        """The consequence, named rather than discovered: F-4/6/8/10/17/18 do not fill."""
        self.assertFalse(hasattr(F, "_S3I3_REGISTRATION"),
                         "an import-time registration is back")
        F._PROVIDER = None
        d = F.parse_declaration(_decl_text(**self.SHORT))["declaration"]
        r = F.validate_declaration(d, book=BOOK)
        self.assertIn("SHORT_BOOK_WITHOUT_ASSIGNMENT", r["refusals"])
        self.assertIn("assignment_interface", r["detail"])

    def test_r1s_provider_satisfies_the_FROZEN_interface_without_either_side_aliasing(self):
        """The seam's actual test: r1 adapted to the published names and it fits."""
        from valuation.edge import assignment as A
        reg = A.register()
        self.assertTrue(reg["ok"], reg)
        self.assertEqual(reg["missing"], [])
        for name in F.ASSIGNMENT_INTERFACE["callables"]:
            self.assertTrue(callable(getattr(A.PROVIDER, name, None)),
                            "the interface names %r and r1's provider does not" % name)

    def test_the_required_short_fields_LITERAL_matches_r1s_and_drift_fails_here(self):
        """`MA13`'s idiom: production holds the literal, the TEST holds the comparison.

        `tuple(assignment.REQUIRED_SHORT_FIELDS)` in `fleet` would have inverted the
        dependency direction r1 documented, so the list is a literal there and this is the
        only place the two are ever compared.
        """
        from valuation.edge import assignment as A
        self.assertEqual(tuple(F.REQUIRED_SHORT_FIELDS), tuple(A.REQUIRED_SHORT_FIELDS))

    def test_a_complete_short_book_validates_once_a_provider_is_registered(self):
        from valuation.edge import assignment as A
        A.register()
        d = F.parse_declaration(_decl_text(**self.SHORT))["declaration"]
        r = F.validate_declaration(d, book=BOOK)
        self.assertTrue(r["ok"], r["refusals"])

    def test_sells_premium_is_mandatory_on_EVERY_book_including_long_ones(self):
        """r1's rule, adopted whole: an absent field lets a short book pass by OMISSION."""
        d = F.parse_declaration(_decl_text())["declaration"]
        d.pop("sells_premium")
        r = F.validate_declaration(d, book=BOOK)
        self.assertIn("MISSING_FIELD:sells_premium", r["refusals"])

    def test_side_and_sells_premium_must_AGREE(self):
        """Two sources for one fact is a split; requiring agreement makes it tamper-evidence."""
        d = F.parse_declaration(_decl_text(side="long", sells_premium=True))["declaration"]
        r = F.validate_declaration(d, book=BOOK)
        self.assertIn("SIDE_AND_SELLS_PREMIUM_DISAGREE", r["refusals"])

    def test_a_provider_missing_a_callable_is_refused_and_does_not_EVICT_a_working_one(self):
        """A typo in a new module must not silently stop every short book in the fleet."""
        from valuation.edge import assignment as A
        A.register()
        good = F.assignment_provider()

        class Half:
            def assign_at_expiry(self, *a, **k):
                return None
        half = Half()
        r = F.register_assignment_provider(half)
        self.assertFalse(r["ok"])
        self.assertEqual(sorted(r["missing"]), ["early_assignment_flag", "secured_cash"])
        self.assertIsNot(F.assignment_provider(), half)
        self.assertIs(F.assignment_provider(), good)

    def test_this_module_computes_no_assignment_and_no_margin(self):
        """`S3-I3` is r1's. A model here would be two implementations of one thing."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):                       # blank docstrings: MA49's family
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    node.body[0].value.value = ""
        defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("assign_at_expiry", defs)
        self.assertNotIn("secured_cash", defs)
        code = ast.unparse(tree)
        self.assertIn("ASSIGNMENT_INTERFACE", code, "the stripper saw nothing")
        self.assertNotIn("intrinsic", code.lower())

# =======================================================================================
class TrialConvention(unittest.TestCase):

    def test_reading_a_meter_writes_a_record_and_flags_the_first_read(self):
        root = _repo()
        try:
            _seed_selfcheck(root)
            sha = _sha(root)
            m1 = F.read_meter(BOOK, [0.2, -0.1], decl_sha=sha, root=root, why="first")
            self.assertTrue(m1["is_first_verdict_read"])
            self.assertIn("CHARGE ONE TRIAL NOW", m1["trial_charge"])
            m2 = F.read_meter(BOOK, [0.2, -0.1, 0.3], decl_sha=sha, root=root, why="second")
            self.assertFalse(m2["is_first_verdict_read"])
            self.assertEqual(m2["trial_charge"], "already charged")
            reads = [r for r in F.read_records(BOOK, root)["rows"]
                     if r["kind"] == "meter_read"]
            self.assertEqual(len(reads), 2, "a peek that leaves no record is an honour system")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_read_before_the_horizon_is_marked_early(self):
        root = _repo()
        try:
            _seed_selfcheck(root)
            m = F.read_meter(BOOK, [0.1] * 3, decl_sha=_sha(root), root=root)
            self.assertTrue(m["early"])
            self.assertFalse(m["horizon_reached"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_meter_delegates_to_track_meter_and_re_derives_no_boundary(self):
        from valuation.edge import track_meter as TM
        m = F.book_meter([1.0] * 10, sigma=2.0, rho=3.0, alpha=0.05, min_effect=0.5,
                         fills_needed=60)
        self.assertAlmostEqual(m["boundary_sum"], TM.boundary(10, sigma=2.0, rho=3.0,
                                                              alpha=0.05), places=12)
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        self.assertNotIn("math.log(v / (rho", src, "the boundary formula is re-derived here")

    def test_a_NO_CONCLUSION_state_ships_its_own_non_absence_sentence(self):
        m = F.book_meter([0.0] * 5, sigma=1.0, rho=3.0, alpha=0.05, min_effect=0.3,
                         fills_needed=60)
        self.assertEqual(m["state"], "NO CONCLUSION")
        self.assertIn("not", m["not_evidence_of_absence"].lower())
        self.assertEqual(m["min_effect"], 0.3)
        self.assertEqual(m["fills_needed"], 60)

    def test_the_meter_has_no_defaults_for_its_frozen_parameters(self):
        """`MA5`: a default is exactly how a bar freezes. These are declaration-frozen."""
        import inspect
        sig = inspect.signature(F.book_meter)
        for p in ("sigma", "rho", "alpha", "min_effect", "fills_needed"):
            self.assertIs(sig.parameters[p].default, inspect.Parameter.empty, p)
            self.assertEqual(sig.parameters[p].kind, inspect.Parameter.KEYWORD_ONLY, p)

    def test_a_cross_book_aggregate_is_not_offered(self):
        with self.assertRaises(NotImplementedError):
            F.fleet_aggregate()


# =======================================================================================
# THE RANDOMIZER
# =======================================================================================
class Randomizer(unittest.TestCase):

    def test_it_is_deterministic_and_salted_by_the_declaration(self):
        a = [F.arm("b", "2026-08-24", "S%03d" % i, "sha-one") for i in range(200)]
        self.assertEqual(a, [F.arm("b", "2026-08-24", "S%03d" % i, "sha-one")
                             for i in range(200)])
        self.assertNotEqual(a, [F.arm("b", "2026-08-24", "S%03d" % i, "sha-two")
                                for i in range(200)])

    def test_it_is_roughly_balanced(self):
        a = [F.arm("b", "2026-08-%02d" % (1 + i % 28), "S%03d" % i, "sha") for i in range(2000)]
        share = a.count("B") / float(len(a))
        self.assertTrue(0.45 <= share <= 0.55, share)

    def test_no_quote_or_outcome_can_enter_the_split(self):
        """The arm is fixed by (book, date, symbol, declaration). Nothing about the trade."""
        import inspect
        self.assertEqual(list(inspect.signature(F.arm).parameters),
                         ["book", "date", "symbol", "decl_sha"])


# =======================================================================================
# THE TRADIER SEAM, THE LEDGER ROW AND THE TEMPLATE
# =======================================================================================
class FillRecording(unittest.TestCase):

    def test_the_bid_ask_and_mid_at_submission_are_stored(self):
        """The columns V5 ROUTED and nobody took. `F-1` cannot be run without them."""
        f = F.fill_fields(symbol="AAPL", occ="A", side="buy", qty=1, order_type="limit_mid",
                          quote={"bid": 2.50, "ask": 2.70},
                          order={"status": "filled", "avg_fill_price": 2.70,
                                 "exec_quantity": 1.0, "quantity": 1.0},
                          submitted_ts="2026-08-24T15:00:00",
                          filled_ts="2026-08-24T15:00:02", limit_price=2.60, arm="B")
        self.assertEqual((f["quote_bid"], f["quote_ask"], f["quote_mid"]), (2.50, 2.70, 2.60))
        self.assertEqual(f["time_to_fill_s"], 2)
        self.assertEqual(f["fate"], "filled")
        self.assertIn("delayed", f["detail"])          # the sandbox caveat travels

    def test_a_one_sided_quote_records_NO_mid_and_never_falls_back_to_last(self):
        """A stale `last` under the name `quote_mid` is the wrong-object family.

        A missing mid is a FACT about the quote that `F-1` has to see; substituting `last`
        would hand it a half-spread computed against a price from another day.
        """
        f = F.fill_fields(symbol="X", occ="X", side="buy", qty=1, order_type="market",
                          quote={"bid": 1.0, "ask": None, "last": 9.99},
                          submitted_ts="2026-08-24T15:00:00")
        self.assertEqual(f["quote_mid"], "")
        self.assertEqual(f["fate"], "unknown")          # no order at all: not "unfilled"

    def test_no_derived_outcome_statistic_is_stored_on_a_fill(self):
        """`F-1`'s own rule: capture is computed at READ time, not stored."""
        f = F.fill_fields(symbol="X", occ="X", side="buy", qty=1, order_type="market",
                          quote={"bid": 1.0, "ask": 2.0},
                          order={"status": "filled", "avg_fill_price": 2.0,
                                 "exec_quantity": 1.0, "quantity": 1.0},
                          submitted_ts="2026-08-24T15:00:00", filled_ts="2026-08-24T15:00:01")
        for k in f:
            self.assertNotIn("capture", k)
            self.assertNotIn("slippage", k)
            self.assertNotIn("pnl", k)

    def test_a_PENDING_order_is_never_recorded_as_a_FILL(self):
        """The defect the live leg caught on its first real order, pinned.

        Tradier reports an unfilled limit as `status: pending, avg_fill_price: 0.0,
        exec_quantity: 0.0, price: <the limit>`. The first cut read `avg_fill_price or price`
        -- and **0.0 is falsy**, so the fallback took the LIMIT and recorded a pending order as
        FILLED at the price it had asked for. On `F-1`, whose whole subject is fill quality and
        which reads every other book's fills, that turns every unfilled order into a perfect
        one. Silent, and in the flattering direction.
        """
        pending = {"status": "pending", "type": "limit", "price": 11.06,
                   "avg_fill_price": 0.0, "exec_quantity": 0.0, "quantity": 1.0}
        f = F.fill_fields(symbol="SPY", occ="SPY260918C00766000", side="buy_to_open", qty=1,
                          order_type="limit", quote={"bid": 11.01, "ask": 11.06},
                          order=pending, submitted_ts="2026-08-24T10:00:00", limit_price=11.06)
        self.assertEqual(f["fate"], "working")
        self.assertEqual(f["fill_price"], "", "the LIMIT price was recorded as a FILL")

    def test_the_fate_comes_from_the_broker_and_not_from_a_number_being_present(self):
        for order, want in (
                ({"status": "filled", "avg_fill_price": 2.0, "exec_quantity": 1.0,
                  "quantity": 1.0}, "filled"),
                ({"status": "partially_filled", "avg_fill_price": 2.0, "exec_quantity": 1.0,
                  "quantity": 5.0}, "partial"),
                ({"status": "rejected", "avg_fill_price": 0.0, "exec_quantity": 0.0}, "rejected"),
                ({"status": "expired", "avg_fill_price": 0.0, "exec_quantity": 0.0}, "expired"),
                ({"status": "open", "avg_fill_price": 0.0, "exec_quantity": 0.0}, "working")):
            f = F.fill_fields(symbol="X", occ="X", side="buy", qty=1, order_type="limit",
                              quote={"bid": 1.0, "ask": 2.0}, order=order,
                              submitted_ts="2026-08-24T10:00:00", limit_price=2.0)
            self.assertEqual(f["fate"], want, order)
            self.assertIn(f["fate"], F.FATES)

    def test_the_fill_price_delegates_to_the_brokers_own_helper(self):
        """B7: `PaperBroker.fill_price` already gates on `exec_quantity`. One definition."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "fleet.py"),
                      encoding="utf-8").read()
        fn = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "fill_fields"]
        self.assertEqual(len(fn), 1)
        code = ast.unparse(fn[0])
        self.assertIn("fill_price(order)", code, "fill_fields re-derives the fill price")
        self.assertNotIn("avg_fill_price", code, "fill_fields reads the raw field again")

    def test_record_fill_re_checks_the_gate_and_a_refusal_becomes_a_record(self):
        root = _repo()
        try:
            # No self-check yet, so the gate must refuse -- and log the refusal.
            r = F.record_fill(BOOK, {"symbol": "X"}, root=root)
            self.assertFalse(r["ok"])
            self.assertEqual(r["code"], "SELFCHECK_ABSENT")
            self.assertTrue(r["refusal_recorded"])
            rows = F.read_records(BOOK, root)["rows"]
            self.assertEqual([x["kind"] for x in rows], ["refusal"])
            # And it permits once the gate passes.
            _seed_selfcheck(root)
            ok = F.record_fill(BOOK, {"symbol": "X", "fill_price": 1.0}, root=root)
            self.assertTrue(ok["ok"] and ok["wrote"], ok)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class LedgerRowAndTemplate(unittest.TestCase):

    def test_the_ledger_row_has_the_ledger_s_own_cell_count(self):
        d = F.parse_declaration(_decl_text())["declaration"]
        row = F.ledger_row(d)
        hdr = [l for l in io.open(os.path.join(REPO, "VALQUO_LEDGER.md"),
                                  encoding="utf-8").read().splitlines()
               if l.startswith("| id | series |")][0]
        self.assertEqual(row.count("|"), hdr.count("|"))

    def test_a_raw_pipe_in_the_prose_is_REFUSED_because_no_escape_exists(self):
        """`M1-PARSE`. `E-2` hit this three days ago writing an absolute value in prose."""
        d = F.parse_declaration(_decl_text())["declaration"]
        d["entry_rule"] = "fires when |z| exceeds 2"
        with self.assertRaises(ValueError) as cm:
            F.ledger_row(d)
        self.assertIn("M1-PARSE", str(cm.exception))

    def test_the_ceremony_can_supply_the_map_tag_and_the_real_commit(self):
        """Both were hard-coded, and both were wrong the moment a book was actually accepted.

        The id defaulted to `"F-" + book`, which yields `F-f13_second_event` where the map and
        every human reference say **F-13**; the commit defaulted to the literal `PENDING`,
        which was honest while nothing was committed and false afterwards.
        """
        d = F.parse_declaration(_decl_text())["declaration"]
        row = F.ledger_row(d, tag="F-13", commit="bcf8af3")
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        self.assertEqual(cells[0], "F-13")
        self.assertEqual(cells[5], "bcf8af3")

    def test_the_defaults_are_UNCHANGED_so_every_prior_caller_is_bit_identical(self):
        """The new keywords must be additive: a caller passing neither gets the old row."""
        d = F.parse_declaration(_decl_text())["declaration"]
        cells = [c.strip() for c in F.ledger_row(d).strip().strip("|").split("|")]
        self.assertEqual(cells[0], "F-" + str(d["book"]))
        self.assertEqual(cells[5], "PENDING")

    def test_a_horizon_of_zero_point_three_years_is_NOT_truncated_to_zero(self):
        """Splitting a sentence on a bare period truncates at the DECIMAL POINT.

        `"0.3 years at the projected 45.00 fills/month"` became `"0"` -- which reads as a
        horizon of zero, i.e. *readable now*, the precise misreading the horizon field exists
        to prevent. It ran the UNSAFE direction, so it is pinned rather than merely fixed.
        """
        self.assertEqual(F._first_sentence("0.3 years at 45.00 a month. Next."),
                         "0.3 years at 45.00 a month")
        self.assertEqual(F._first_sentence("no trailing period"), "no trailing period")

    def test_the_horizon_note_names_every_field_and_says_whether_sigma_was_MEASURED(self):
        """`MB8` borrowed an SE measured on a different perturbation and was wrong six-fold.

        An assumed sigma and a measured one are different objects, so the row says which.
        """
        d = F.parse_declaration(_decl_text())["declaration"]
        d["verdict_horizon"] = dict(d["verdict_horizon"])
        d["verdict_horizon"]["sigma_provenance"] = "PRIOR, not measured: a guess"
        note = F.horizon_note(d)
        for field in ("min_effect", "sigma", "rho", "alpha", "fills_needed",
                      "expected_fills_per_month", "years_to_horizon_at_projected_rate",
                      "earliest_honest_read"):
            self.assertIn(field, note)
        self.assertIn("PRIOR, not measured", note)
        d["verdict_horizon"]["sigma_provenance"] = "MEASURED: O12 reports sd 0.9251"
        self.assertIn("MEASURED", F.horizon_note(d))

    def test_a_utility_book_charges_ZERO_TRIALS_in_its_own_ledger_row(self):
        """F-6 measures the COST of a service, not a hypothesis, so no meter is ever read."""
        d = F.parse_declaration(_decl_text())["declaration"]
        d["hypothesis_class"] = "utility"
        d["trial"] = {"domain": "none"}
        self.assertIn("ZERO TRIALS", F.horizon_note(d))

    def test_the_template_parses_and_is_REFUSED_until_its_placeholders_are_filled(self):
        """A skeleton that validated would be a book declared with no horizon."""
        t = F.declaration_template("fX")
        p = F.parse_declaration(t)
        self.assertTrue(p["ok"], p.get("reason"))
        v = F.validate_declaration(p["declaration"], book="fX")
        self.assertFalse(v["ok"])
        self.assertIn("FILLS_NEEDED_BELOW_ONE", v["refusals"])
        self.assertIn("NON_POSITIVE_HORIZON_FIELD:sigma", v["refusals"])

    def test_a_short_template_carries_the_assignment_clauses(self):
        d = F.parse_declaration(F.declaration_template("fY", side="short"))["declaration"]
        for f in F.REQUIRED_SHORT_FIELDS:
            self.assertIn(f, d)

    def test_the_scout_s_prose_drafts_are_refused_and_that_is_the_machinery_working(self):
        """Prose cannot be validated, so the format is a fenced json block. Stated, not hidden.

        The four `DECL_DRAFT_*` files on the scout branch are prose and will be refused as they
        stand -- which is why `declaration_template` exists, so Don's ~18-book wave is cheap.
        """
        self.assertFalse(F.parse_declaration("# DECL f1\n\nSome prose, no block.\n")["ok"])


class TheDailyCycle(unittest.TestCase):
    """`cycle()` -- what the runner kicks, and the distinction it must never collapse."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fleetcycle_")
        F._ENTRY_RULES.clear()

    def tearDown(self):
        F._ENTRY_RULES.clear()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_file_that_is_not_a_declaration_is_REPORTED_and_never_silently_skipped(self):
        """`DECL_CEREMONY_RUNBOOK.md` is not a book. Neither is a prose draft.

        Skipping both silently would make *"not a book"* and *"a book whose declaration is
        broken"* indistinguishable -- and the second is the one that must be loud.
        """
        io.open(os.path.join(self.root, "DECL_CEREMONY_RUNBOOK.md"), "w",
                encoding="utf-8").write("# a runbook, not a book\n")
        io.open(os.path.join(self.root, "DECL_DRAFT_fZ.md"), "w",
                encoding="utf-8").write("# prose only, no fenced block\n")
        got = {d["book"]: d for d in F.declared_books(self.root)}
        self.assertIn("CEREMONY_RUNBOOK", got)
        self.assertFalse(got["CEREMONY_RUNBOOK"]["parses"])
        self.assertTrue(got["CEREMONY_RUNBOOK"]["reason"])
        res = F.cycle(self.root)
        states = {r["book"]: r["state"] for r in res["books"]}
        self.assertEqual(states["CEREMONY_RUNBOOK"], "NOT_A_DECLARATION")
        self.assertEqual(res["books_declared"], 0)

    def test_an_UNIMPLEMENTED_entry_rule_is_never_reported_as_no_candidates_today(self):
        """THE DISTINCTION THE WHOLE FUNCTION EXISTS FOR.

        A declaration FREEZES a rule in prose; it does not execute one. *"The rule ran and
        nobody qualified"* is a market observation. *"No code exists to decide"* is a build
        gap. Collapsing them is how a paper fleet reports a cycle that placed nothing as a
        cycle that found nothing.
        """
        self.assertIsNone(F.entry_rule("fQ"))
        ran = []
        F.register_entry_rule("fQ", lambda decl, root: ran.append(1) or [])
        self.assertIsNotNone(F.entry_rule("fQ"))
        self.assertEqual(F.entry_rule("fQ")({}, None), [])
        self.assertEqual(len(ran), 1)

    def test_registering_a_non_callable_is_REFUSED(self):
        with self.assertRaises(TypeError):
            F.register_entry_rule("fQ", "not a function")

    def test_the_dry_run_is_the_DEFAULT_and_writes_nothing(self):
        """A side-effecting default on an append-only chained record is the `track-row` defect."""
        res = F.cycle(self.root)
        self.assertFalse(res["wrote"])
        self.assertEqual(res["fills_written"], 0)

    def test_the_implemented_count_is_COUNTED_and_not_derived_by_subtraction(self):
        """The first cut computed it as `declared - unscheduled - blocked`.

        That is right only while no book is both blocked AND unimplemented -- true on the day
        it was written, by accident, and false the moment one self-check lands. A number that
        is only coincidentally correct is `MB8`'s family.
        """
        res = F.cycle(self.root)
        self.assertEqual(res["entry_rules_implemented"], 0)
        self.assertIn("entry_rules_implemented", res)

    def test_a_fleet_with_no_running_book_reports_NOT_BREATHING_in_its_own_body(self):
        res = F.cycle(self.root)
        self.assertFalse(res["breathing"])
        self.assertIn("DECLARED-BUT-NOT-BREATHING", res["note"])

    def test_the_real_repo_cycle_reports_every_accepted_book_and_fills_nothing(self):
        """Against the REAL tree, because a cycle checked only against a fixture checks a fixture."""
        res = F.cycle()
        self.assertGreaterEqual(res["books_declared"], 17)
        self.assertEqual(res["fills_written"], 0)
        self.assertFalse(res["breathing"])
        for r in res["books"]:
            if r.get("is_book"):
                self.assertIn("entry_rule_implemented", r)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
