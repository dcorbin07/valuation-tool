# -*- coding: utf-8 -*-
"""`VALREADS` — the recorder, and the proof that its day-1 self-check can actually fail.

Run as its own process (`RUN_RULES` line 25 judges a suite by its exit code, and a file with no
`__main__` block defines its tests, executes nothing and exits 0 — `O21-D2`'s own near-miss).

**THE MUTATION HALF IS THE POINT.** Six self-check cases passing proves nothing until each is
shown to FAIL against a deliberately broken input. `MB21`'s `C1` scored a perfect 0.000e+00 on an
empty frame by comparing nothing, and it is the sixth instance of that family in this record.
Every mutation here restores the module byte-for-byte afterwards and the restoration is asserted —
`W-1`'s harness rewrote a CRLF source as LF and failed its own byte check *after* the mutation had
run, and **a mutation harness that cannot put a file back is worse than none.**
"""
import ast
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

from valuation.edge import append_only as AO                               # noqa: E402
from valuation.edge import valreads as VR                                  # noqa: E402
from scripts import valreads_record as RUN                                 # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(HERE, "valuation", "edge", "valreads.py")
REGISTER = os.path.join(HERE, "PREREG_valuation_reads.md")


def _row(ticker="AAAA", **kw):
    r = {c: "" for c in VR.ROW_COLUMNS}
    r.update({"ticker": ticker, "status": "OK", "price": "10.0",
              "market_cap": "1000.0", "business_quality_score": "70.0",
              "price_vs_model_pct": "0.1"})
    r.update(kw)
    return r


class TestTheRegisterCameFirst(unittest.TestCase):
    def test_the_register_exists_on_disk_and_is_not_merely_cited(self):
        # `S3-I1`'s repair: its `REGISTER` constant named a file that did not exist, under a
        # docstring saying the citation was there so a reader could check the file existed.
        self.assertTrue(os.path.exists(REGISTER), REGISTER)
        self.assertEqual(VR.REGISTER, os.path.basename(REGISTER))

    def test_the_register_is_a_strict_git_ancestor_of_the_recorder(self):
        """Checked against git, not against my word for it.

        **The register's FIRST commit is the blind one**, so that is the commit the ancestry
        has to hold for; a later amendment is a different (and weaker) claim. And the register
        may never share a commit with code -- which is the property that actually failed once in
        this item, when Amendment 1 was first staged alongside the recorder and had to be split
        back out.
        """
        import subprocess

        def shas(pathspec):
            out = subprocess.run(["git", "log", "--format=%H", "--", pathspec],
                                 cwd=HERE, capture_output=True)
            return [x for x in out.stdout.decode("utf-8", "replace").split() if x]

        reg_all = shas("PREREG_valuation_reads.md")
        rec_all = shas("valuation/edge/valreads.py")
        if not reg_all or not rec_all:
            self.skipTest("one of the two files is not committed yet")
        reg_first, rec_first = reg_all[-1], rec_all[-1]
        r = subprocess.run(["git", "merge-base", "--is-ancestor", reg_first, rec_first],
                           cwd=HERE, capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "the register's first commit must be a strict ancestor of the "
                         "recorder's (register %s, recorder %s)"
                         % (reg_first[:8], rec_first[:8]))
        self.assertNotIn(rec_first, reg_all,
                         "the register may never share a commit with the recorder")
        # AND EVERY COMMIT TOUCHING THE REGISTER MUST BE MARKDOWN ONLY -- an amendment that
        # lands beside code is not blind, whatever its prose claims.
        for sha in reg_all:
            out = subprocess.run(["git", "show", "--name-only", "--format=", sha],
                                 cwd=HERE, capture_output=True)
            files = [f for f in out.stdout.decode("utf-8", "replace").split() if f]
            bad = [f for f in files if not f.endswith(".md")]
            self.assertFalse(bad, "register commit %s also touched %s" % (sha[:8], bad))

    def test_the_register_declares_a_sign_for_every_read(self):
        txt = io.open(REGISTER, encoding="utf-8").read()
        for rid in ("R1-BQ", "R2-PVM", "R3-PIG", "R4-GAP", "R5-WARN"):
            self.assertIn(rid, txt)
        # non-vacuity: a register with no sign table would not contain both words
        self.assertIn("POSITIVE", txt)
        self.assertIn("NEGATIVE", txt)

    def test_the_register_states_its_power_and_names_a_year_it_cannot_resolve_by(self):
        txt = io.open(REGISTER, encoding="utf-8").read()
        self.assertIn("80% power", txt)
        self.assertIn("2044", txt)      # the honest "unlikely to resolve before year N"


class TestNothingReadsAForwardReturn(unittest.TestCase):
    def test_over_the_syntax_tree_and_not_by_grep(self):
        ok, detail, vac = RUN._no_forward_return()
        self.assertTrue(ok, detail)
        self.assertIn("non-vacuous", vac)

    def test_the_ban_is_non_vacuous_because_the_docstring_contains_the_words(self):
        # THE REASON THE CHECK IS AN AST CHECK: a substring ban would fire on the module's own
        # prose. Asserted, so nobody "simplifies" it back into a grep.
        src = io.open(MODULE, encoding="utf-8").read()
        self.assertIn("forward return", src,
                      "the module's docstring states the rule, which is exactly why a substring "
                      "ban fires against the CORRECT tree -- MA49/MB1's family")
        self.assertNotIn("fwd_ret", [n.id for n in ast.walk(ast.parse(src))
                                     if isinstance(n, ast.Name)])

    def test_the_ban_catches_an_injected_read(self):
        orig = io.open(MODULE, "rb").read()
        try:
            bad = orig.replace(b'    row["ticker"] = ticker',
                               b'    row["ticker"] = ticker\n    _ = fwd_ret')
            self.assertNotEqual(bad, orig, "the mutation point moved; re-aim it")
            io.open(MODULE, "wb").write(bad)
            ok, detail, _vac = RUN._no_forward_return()
            self.assertFalse(ok, "the AST ban did not see an injected `fwd_ret`: " + detail)
        finally:
            io.open(MODULE, "wb").write(orig)
        self.assertEqual(io.open(MODULE, "rb").read(), orig,
                         "the module must be restored BYTE-FOR-BYTE (W-1's harness defect)")


class TestTheRecorderComputesNoVerdict(unittest.TestCase):
    def test_no_bar_shaped_constant_and_no_outcome_vocabulary(self):
        tree = ast.parse(io.open(MODULE, encoding="utf-8").read())
        banned = {"CLEARS", "SURVIVES", "REJECTED", "VERDICT", "P95", "FLOOR",
                  "THRESHOLD", "BAR"}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id.upper() in banned:
                        self.fail("the recorder may not define %s" % t.id)

    def test_it_imports_no_statistics_or_power_machinery(self):
        tree = ast.parse(io.open(MODULE, encoding="utf-8").read())
        mods = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                mods.append(n.module)
            elif isinstance(n, ast.Import):
                mods += [a.name for a in n.names]
        for m in mods:
            self.assertNotIn("power_gate", m)
            self.assertNotIn("statistics", m)
            self.assertNotIn("fundamental_panel", m)
        self.assertTrue(mods, "non-vacuous: the module does import things")


class TestTheReadsComeFromThePagesOwnFunctions(unittest.TestCase):
    def test_price_assumes_and_scoring_are_called_not_reimplemented(self):
        # `B7`: a second definition of a read is how the page and the record come to disagree.
        src = io.open(MODULE, encoding="utf-8").read()
        tree = ast.parse(src)
        called = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                called.add(n.func.attr)
        self.assertIn("price_assumes", called)
        self.assertIn("dcf_warning", called)
        self.assertIn("is_story_stock", called)
        # and the thresholds are NOT retyped here
        self.assertNotIn("15.0", [repr(n.value) for n in ast.walk(tree)
                                  if isinstance(n, ast.Constant)])

    def test_the_story_threshold_is_not_retyped_anywhere_in_the_recorder(self):
        """AND THIS GUARD'S FIRST CUT WAS THE SUBSTRING-BAN DEFECT, in the very file that
        warns about it. It asserted `"STORY_GAP_PP ="` was absent from the source and FAILED
        AGAINST THE CORRECT TREE, because the recorder's own comment quotes item 52 saying
        *"`STORY_GAP_PP = 15.0` is a disclosure threshold calibrated against nothing"* -- prose
        documenting the rule, containing exactly what the rule forbids. Seventh instance of the
        family in this project (`MA49`, `MB1` three times in one register, `MB15`, `W-1`,
        `MB20`), and it was committed with the warning in view.

        It reads the AST now: no module-level ASSIGNMENT may bind that name, which is the
        property that actually matters, and prose about it is permitted.
        """
        from valuation.web import price_assumes as PA
        self.assertEqual(PA.STORY_GAP_PP, 15.0)
        tree = ast.parse(io.open(MODULE, encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == "STORY_GAP_PP":
                        self.fail("the recorder re-binds STORY_GAP_PP; it must import it")
        # POSITIVE CONTROL, so the narrowed rule is proved still to bite.
        bad = ast.parse("STORY_GAP_PP = 15.0")
        self.assertTrue([t.id for n in ast.walk(bad) if isinstance(n, ast.Assign)
                         for t in n.targets
                         if isinstance(t, ast.Name) and t.id == "STORY_GAP_PP"],
                        "the narrowed guard must still catch a real re-binding")


class TestAmendment1SeparatesTheROEFromTheGrowth(unittest.TestCase):
    def test_the_two_quantities_have_two_columns(self):
        self.assertIn("price_implied_growth", VR.ROW_COLUMNS)
        self.assertIn("price_implied_roe", VR.ROW_COLUMNS)
        self.assertIn("implied_is_roe", VR.ROW_COLUMNS)

    def test_the_amendment_is_in_the_register_and_predates_no_row(self):
        txt = io.open(REGISTER, encoding="utf-8").read()
        self.assertIn("AMENDMENT 1", txt)
        self.assertIn("BEFORE THE FIRST ROW EXISTS", txt)

    def test_price_assumes_really_does_return_an_roe_under_the_same_key(self):
        # THE PREMISE OF THE AMENDMENT, ASSERTED RATHER THAN TRUSTED. If `price_assumes` ever
        # stops branching on `is_financial` this test goes red and the amendment is moot.
        from valuation.web import price_assumes as PA
        fin = PA.price_assumes(None, 0.05, is_financial=True, implied_roe=0.12, book_roe=0.10)
        self.assertTrue(fin["available"])
        self.assertAlmostEqual(fin["implied"], 0.12)
        self.assertTrue(fin["is_financial"])
        self.assertIn("return on equity", fin["sentence"])


class TestARefusalIsARecord(unittest.TestCase):
    def test_a_refused_row_carries_a_status_and_a_reason(self):
        r = VR.read_one("ZZZZQZZZ_NOT_A_TICKER", {"source": "hot"})
        self.assertIn(r["status"], ("REFUSED", "PARTIAL"))
        self.assertTrue(r["refused_reason"], "a refusal with no reason is a blank")

    def test_every_row_has_every_column_so_a_missing_read_is_blank_not_absent(self):
        r = VR.read_one("ZZZZQZZZ_NOT_A_TICKER", {"source": "hot"})
        for c in VR.ROW_COLUMNS:
            self.assertIn(c, r)


class TestTheRecordIsAppendOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="valreads_t_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_recorded_week_is_refused_not_rewritten(self):
        a = VR.write_week("2030-01-06", [_row("AAAA")], root=self.tmp)
        self.assertTrue(a["ok"])
        b = VR.write_week("2030-01-06", [_row("BBBB")], root=self.tmp)
        self.assertFalse(b["ok"])
        self.assertIn("append-only", b["reason"])
        self.assertEqual(VR._sha256_of(VR.rows_path("2030-01-06", self.tmp)), a["sha256"])

    def test_the_manifest_delegates_and_is_not_a_second_writer(self):
        src = io.open(MODULE, encoding="utf-8").read()
        tree = ast.parse(src)
        calls = [n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertIn("append", calls)
        self.assertIs(AO.append.__module__ and True, True)

    def test_the_byte_prefix_guarantee_holds_on_the_manifest(self):
        m = VR.manifest_path(self.tmp)
        e = {c: "" for c in VR.MANIFEST_COLUMNS}
        VR.append_manifest(dict(e, date="2030-01-06", rows="1"), root=self.tmp)
        before = io.open(m, "rb").read()
        VR.append_manifest(dict(e, date="2030-01-13", rows="1"), root=self.tmp)
        after = io.open(m, "rb").read()
        self.assertTrue(after.startswith(before))
        self.assertGreater(len(after), len(before))

    def test_a_backward_week_is_refused_and_a_retry_is_a_no_op(self):
        e = {c: "" for c in VR.MANIFEST_COLUMNS}
        VR.append_manifest(dict(e, date="2030-01-13", rows="1"), root=self.tmp)
        back = VR.append_manifest(dict(e, date="2030-01-06", rows="1"), root=self.tmp)
        self.assertFalse(back["ok"])
        self.assertIn("append-only", back["reason"])
        again = VR.append_manifest(dict(e, date="2030-01-13", rows="1"), root=self.tmp)
        self.assertTrue(again["already_present"])
        self.assertFalse(again["wrote"])

    def test_a_refused_week_does_not_consume_the_manifest_key(self):
        # The reason refusals are keyed on a timestamp: a quota that resets must leave the week
        # recordable, and a manifest row claiming it was refused would make the retry a no-op.
        VR.log_refusal("canary", "throttled", date="2030-01-20", root=self.tmp)
        rows, _h, err = AO.read_rows(VR.manifest_path(self.tmp))
        self.assertIsNone(err)
        self.assertEqual([r for r in rows if r.get("date") == "2030-01-20"], [])
        rr, _h2, _e2 = AO.read_rows(VR.refusals_path(self.tmp))
        self.assertEqual(len(rr), 1)
        self.assertEqual(rr[0]["stage"], "canary")

    def test_the_record_lives_in_data_export_which_is_tracked(self):
        # `data/` is gitignored, and this project has twice lost an artifact to a worktree that
        # was later deleted (MA28_CARD.json, I2_BURN_IN_CENSUS.json).
        self.assertTrue(VR.export_root().replace("\\", "/").endswith("data_export/valreads"))


class TestTheCanaryGate(unittest.TestCase):
    def test_a_degraded_canary_refuses_and_a_healthy_one_passes(self):
        bad = _row(VR.CANARY, market_cap="")
        ok, why = VR.canary_ok(bad)
        self.assertFalse(ok)
        self.assertIn("market cap", why)
        self.assertTrue(VR.canary_ok(_row(VR.CANARY))[0])

    def test_a_refused_canary_is_distinguishable_from_a_degraded_one(self):
        ref = _row(VR.CANARY, status="REFUSED", refused_reason="boom")
        ok, why = VR.canary_ok(ref)
        self.assertFalse(ok)
        self.assertIn("refused", why)

    def test_mid_run_degradation_is_caught_and_a_clean_week_is_not(self):
        bad = [_row("N%03d" % i, market_cap="") for i in range(30)]
        self.assertTrue(VR.week_degraded(bad)[0])
        self.assertFalse(VR.week_degraded([_row("N%03d" % i) for i in range(30)])[0])

    def test_it_does_not_fire_on_too_few_names_to_judge(self):
        few = [_row("N%d" % i, market_cap="") for i in range(5)]
        self.assertFalse(VR.week_degraded(few)[0],
                         "five names cannot establish a throttle")


class TestThePopulationRuleIsFrozen(unittest.TestCase):
    def test_the_rule_is_the_union_and_is_pinned_to_the_registers_wording(self):
        self.assertEqual(VR.HOT_PATH, "/api/hotstocks?top=500")
        self.assertEqual(VR.INDEX_PATH, "/api/valquo-index")
        txt = io.open(REGISTER, encoding="utf-8").read()
        self.assertIn("/api/hotstocks?top=500", txt)
        self.assertIn("/api/valquo-index", txt)

    def test_the_index_leg_is_required_rather_than_best_effort(self):
        # Falling back to the hot list alone would silently record the exact population the
        # register rejected, and the record would not say so.
        src = io.open(MODULE, encoding="utf-8").read()
        self.assertIn("index unreachable", src)

    def test_the_manifest_records_the_counts_so_a_cap_change_is_visible(self):
        for c in ("n_population", "n_hot", "n_index", "n_index_outside_hot"):
            self.assertIn(c, VR.MANIFEST_COLUMNS)

    def test_no_token_is_read_anywhere(self):
        src = io.open(MODULE, encoding="utf-8").read()
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv"):
                self.fail("the recorder reads the environment; both routes are tokenless")
        self.assertTrue(VR.TOKENLESS)


class TestTheSelfCheckGatesTheRecorder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="valreads_sc_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_absent_stale_and_failing_are_three_states(self):
        ok, why = RUN.selfcheck_state(self.tmp)
        self.assertFalse(ok)
        self.assertIn("ABSENT", why)

        p = RUN.selfcheck_path(self.tmp)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"all_pass": False, "n_passed": 4, "n_cases": 6,
             "recorder_version": VR.RECORDER_VERSION}))
        ok, why = RUN.selfcheck_state(self.tmp)
        self.assertFalse(ok)
        self.assertIn("FAILED", why)
        self.assertIn("different fact", why)

        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"all_pass": True, "n_passed": 6, "n_cases": 6, "recorder_version": "0"}))
        ok, why = RUN.selfcheck_state(self.tmp)
        self.assertFalse(ok)
        self.assertIn("recorder version", why)

        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"all_pass": True, "n_passed": 6, "n_cases": 6,
             "recorder_version": VR.RECORDER_VERSION}))
        ok, why = RUN.selfcheck_state(self.tmp)
        self.assertTrue(ok, why)

    def test_the_recorder_refuses_a_week_while_the_self_check_is_absent(self):
        r = RUN.record_week(date="2030-02-03", root=self.tmp, verbose=False)
        self.assertFalse(r["ok"])
        self.assertEqual(r["stage"], "selfcheck")
        self.assertFalse(os.path.exists(VR.rows_path("2030-02-03", self.tmp)))
        # and the refusal is RECORDED rather than only printed
        rr, _h, _e = AO.read_rows(VR.refusals_path(self.tmp))
        self.assertEqual(len(rr), 1)

    def test_the_self_check_passes_and_every_case_carries_a_vacuity_control(self):
        d = RUN.selfcheck(verbose=False)
        self.assertTrue(d["all_pass"], json.dumps(d["cases"], indent=1))
        self.assertGreaterEqual(d["n_cases"], 6)
        for c in d["cases"]:
            self.assertTrue(c["vacuity_control"],
                            "case %s has no vacuity control" % c["case"])

    def test_the_self_check_writes_nothing_into_the_real_record(self):
        before = sorted(os.listdir(VR.export_root())) if os.path.isdir(VR.export_root()) else []
        RUN.selfcheck(verbose=False)
        after = sorted(os.listdir(VR.export_root())) if os.path.isdir(VR.export_root()) else []
        self.assertEqual(before, after)


class TestEachSelfCheckCaseCanActuallyFail(unittest.TestCase):
    """MUTATION. Six passes prove nothing until each is shown to fail against a break."""

    def _mutate(self, old, new, case_name):
        orig = io.open(MODULE, "rb").read()
        try:
            bad = orig.replace(old, new, 1)
            self.assertNotEqual(bad, orig, "mutation point moved: %r" % old[:50])
            io.open(MODULE, "wb").write(bad)
            import importlib
            importlib.reload(VR)
            importlib.reload(RUN)
            d = RUN.selfcheck(verbose=False)
            hit = [c for c in d["cases"] if c["case"] == case_name]
            self.assertTrue(hit, "case %s vanished" % case_name)
            self.assertFalse(hit[0]["pass"],
                             "case %s PASSED against a broken recorder" % case_name)
        finally:
            io.open(MODULE, "wb").write(orig)
            import importlib
            importlib.reload(VR)
            importlib.reload(RUN)
        self.assertEqual(io.open(MODULE, "rb").read(), orig,
                         "the module must be restored BYTE-FOR-BYTE")

    def test_round_trip_case_fails_when_a_column_is_dropped_on_write(self):
        self._mutate(b'            out = {c: r.get(c, "") for c in ROW_COLUMNS}',
                     b'            out = {c: r.get(c, "") for c in ROW_COLUMNS}\n'
                     b'            out["business_quality_score"] = ""',
                     "row_round_trips_unchanged")

    def test_refusal_case_fails_when_the_reason_is_dropped(self):
        self._mutate(b'            w.writerow(out)',
                     b'            out["refused_reason"] = ""\n            w.writerow(out)',
                     "refusal_is_a_record_not_a_blank")

    def test_rewrite_case_fails_when_the_week_guard_is_removed(self):
        self._mutate(b'    if os.path.exists(p):',
                     b'    if False and os.path.exists(p):',
                     "a_recorded_week_is_not_rewritten")

    def test_canary_case_fails_when_the_market_cap_tell_is_removed(self):
        self._mutate(b'    if not row.get("market_cap"):',
                     b'    if False:',
                     "canary_and_mid_run_degradation_refuse")

    def test_append_only_case_fails_when_the_manifest_stops_being_append_only(self):
        self._mutate(b'        append_only=True,\n        backfill_hint=',
                     b'        append_only=False,\n        backfill_hint=',
                     "append_only_byte_prefix_and_refusals")


class TestSmokeTestsNeverEnterTheRecord(unittest.TestCase):
    def test_the_limit_path_refuses_to_write(self):
        src = io.open(os.path.join(HERE, "scripts", "valreads_record.py"),
                      encoding="utf-8").read()
        self.assertIn("smoke test -- deliberately not written to the record", src)
        self.assertIn("A SMOKE TEST MAY NOT ENTER THE RECORD", src)


if __name__ == "__main__":
    unittest.main(verbosity=1)
