# -*- coding: utf-8 -*-
"""D9-DIAG — why the free route fails. ZERO TRIALS, no bar, no verdict.

WHAT THESE PIN, and it is a narrower job than a register's. A diagnostic cannot be wrong about a
verdict because it does not issue one; what it CAN do is quietly become a verdict, or lose the
one property that makes its central claim readable. So:

* **`with_numbers=False` IS INERT.** A production function grew a second parameter. Every
  existing caller's row shape must be unchanged (`C3`), and the guard is checked for VACUITY —
  it must see a real emission when the flag is on, or it passes by looking at nothing.
* **THE RAW INPUTS COME OFF THE FRAME, NOT THE METRICS DICT.** This is the defect this item
  actually shipped and repaired: `build_frame` DERIVES `neg_leverage`, `gp_on_capital`,
  `fcf_margin` and `interest_cov`, so reading the pre-derivation dict returns them absent while
  the quality theme built from them scores fine — a per-input comparison that silently omits
  four of ten inputs, in the direction that reads as "the free path lacks them".
* **THE OVERLAP HAS ONE DEFINITION** (`B7`). Q1e and Q1f both report D9's B2 and must not drift.
* **IT ISSUES NO VERDICT.** No threshold, no GO/NO-GO, no bar comparison anywhere in the
  diagnostic — pinned on the AST rather than by grepping prose, because the docstring says the
  words "NO-GO" and "bar" while the code must contain neither comparison.
* **`--same-date` MAY NOT CLOBBER `--sharadar`'s CACHE.** The renewal re-check writes its own
  artifact; a mode that overwrites another mode's output destroys the evidence the original
  comparison rests on.
"""
from __future__ import annotations

import ast
import io
import json
import os
import unittest

import state_isolation  # noqa: F401  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fa_candidates():
    """Where `data/free_analysis` might be, DERIVED rather than typed.

    Same shape as `optionable_universe._data_root`: an env override, then this repo's own
    `data/`, then the primary checkout last -- because a git worktree carries `data/` EMPTY
    (`E-5`, `S3-I3`), which is the whole reason a literal was here to begin with. A literal is
    also why land run #571 went red on a runner that has no such drive.
    """
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(os.path.join(env, "free_analysis"))
    out.append(os.path.join(ROOT, "data", "free_analysis"))
    # `<primary>/.claude/worktrees/<name>` -> `<primary>`
    parts = ROOT.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data", "free_analysis"))
    return out


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _art(name):
    """The first candidate that actually CARRIES the file -- existence of the directory is not
    population of it (`DEEPITM-FIN`). Returns None when no candidate has it, so every caller
    skips LOUDLY rather than failing on a machine that legitimately holds no artifacts."""
    for d in _fa_candidates():
        p = os.path.join(d, name)
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as fh:
                return json.load(fh)
    return None


def _art_path(name):
    for d in _fa_candidates():
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


class TestTheOptInEmissionIsInert(unittest.TestCase):
    """`with_numbers` is off by default and every existing caller is unaffected."""

    def test_with_numbers_defaults_to_false(self):
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "score_universe_now"]
        self.assertEqual(len(fn), 1, "score_universe_now is not defined exactly once")
        args = fn[0].args
        names = [a.arg for a in args.args]
        self.assertIn("with_numbers", names)
        # the default must be the literal False, not a truthy sentinel
        off = len(names) - len(args.defaults)
        default = args.defaults[names.index("with_numbers") - off]
        self.assertIsInstance(default, ast.Constant)
        self.assertIs(default.value, False)

    def test_the_emission_is_guarded_and_the_guard_is_the_flag_itself(self):
        """The `num_` keys must be reachable ONLY through `with_numbers`.

        Shape, not substring: an `if` whose test is the bare name. A `BoolOp` is structurally
        not that test, so `if with_numbers or True` cannot satisfy this — the mutation that
        walked through `W-1`'s first hook guard.
        """
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        guards = [n for n in ast.walk(tree)
                  if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                  and n.test.id == "with_numbers"]
        self.assertEqual(len(guards), 1,
                         "expected exactly one `if with_numbers:` guard, found %d" % len(guards))
        emitted = [c for c in ast.walk(guards[0])
                   if isinstance(c, ast.Constant) and c.value == "num_"]
        self.assertTrue(emitted, "the guard no longer builds the `num_` prefix")

    def test_no_num_key_is_written_outside_that_guard(self):
        """Vacuity control on the guard above: the prefix must exist NOWHERE else."""
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        guards = [n for n in ast.walk(tree)
                  if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                  and n.test.id == "with_numbers"]
        inside = {id(c) for g in guards for c in ast.walk(g)}
        stray = [c for c in ast.walk(tree)
                 if isinstance(c, ast.Constant) and c.value == "num_" and id(c) not in inside]
        self.assertEqual(stray, [], "a `num_` emission exists outside the with_numbers guard")


class TestTheInputsAreReadFromTheFrame(unittest.TestCase):
    """The defect this item shipped and repaired, pinned so it cannot come back.

    `build_frame` derives several quality inputs, so the metrics dict the row was built from
    does not carry them. Reading it returns four of ten inputs absent — and absent reads as
    "the free path lacks this input", which is a false finding, not a missing one.
    """

    DERIVED = ("neg_leverage", "gp_on_capital", "fcf_margin", "interest_cov")

    def test_the_emission_prefers_the_frame_over_the_metrics_dict(self):
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        guards = [n for n in ast.walk(tree)
                  if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                  and n.test.id == "with_numbers"]
        self.assertEqual(len(guards), 1)
        # the frame must be consulted inside the guard, by name, in a membership test against
        # its columns -- the shape `_nm in fr.columns`
        cmps = [c for c in ast.walk(guards[0]) if isinstance(c, ast.Compare)]
        frame_tests = [
            c for c in cmps
            if any(isinstance(o, ast.In) for o in c.ops)
            and any(isinstance(x, ast.Attribute) and x.attr == "columns"
                    and isinstance(x.value, ast.Name) and x.value.id == "fr"
                    for x in c.comparators)]
        self.assertTrue(frame_tests,
                        "the emission no longer tests `in fr.columns`; it is reading the "
                        "pre-derivation metrics dict, which omits the derived inputs")

    def test_the_derived_inputs_are_actually_present_in_the_banked_scores(self):
        """The measurement, not the source shape: all four must be non-empty on disk."""
        import pandas as pd
        p = _art_path("D9_SHARADAR_SCORES.pkl")
        if p is None:
            self.skipTest("D9_SHARADAR_SCORES.pkl absent (no populated data root here)")
        cache = pd.read_pickle(p)
        rows = cache["freeze_2026-07-31"]["rows"]
        for nm in self.DERIVED:
            present = sum(1 for r in rows if r.get("num_" + nm) is not None)
            self.assertGreater(
                present, 0,
                "num_%s is empty in every banked row -- the emission is reading the "
                "pre-derivation dict again" % nm)


class TestTheDiagnosticIssuesNoVerdict(unittest.TestCase):
    """`MB1-SEL` is only true if the thing really does not decide anything."""

    def test_the_diagnostic_compares_nothing_to_a_bar(self):
        """No D9 bar literal may appear as a comparison operand in the diagnostic.

        Read off the AST, not the text: the module docstring legitimately quotes 0.80 and 0.60
        while explaining what it is NOT doing, and a substring ban would fire on that prose --
        the family this project has now paid for six times.
        """
        tree = ast.parse(_read("scripts", "d9_diagnose.py"))
        bars = {0.80, 0.60, 0.70}
        for c in ast.walk(tree):
            if not isinstance(c, ast.Compare):
                continue
            for operand in [c.left] + list(c.comparators):
                if isinstance(operand, ast.Constant) and operand.value in bars:
                    self.fail("the diagnostic compares something to %r -- that is a verdict"
                              % operand.value)

    def test_the_artifact_records_zero_trials_and_says_why(self):
        d = _art("D9_DIAG.json")
        if d is None:
            self.skipTest("D9_DIAG.json absent")
        self.assertEqual(d["trials"], 0)
        self.assertIn("MB1-SEL", d["note"])


class TestTheOverlapHasOneDefinition(unittest.TestCase):
    """`B7`: Q1e and Q1f both report D9's B2 and must not drift apart on the arithmetic."""

    def test_the_decile_overlap_is_defined_exactly_once(self):
        tree = ast.parse(_read("scripts", "d9_diagnose.py"))
        defs = [n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "_decile_overlap"]
        self.assertEqual(len(defs), 1,
                         "expected one _decile_overlap definition, found %d" % len(defs))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "_decile_overlap"]
        self.assertGreaterEqual(len(calls), 2,
                                "the shared definition has fewer than two callers, so it is "
                                "not actually shared")

    def test_both_blocks_report_an_overlap(self):
        d = _art("D9_DIAG.json")
        if d is None:
            self.skipTest("D9_DIAG.json absent")
        self.assertIsNotNone(
            d["Q1e_identical_assembly"]["4_plus_complete_case"]["decile_overlap"])
        self.assertIsNotNone(d["Q1f_leave_one_theme_out"]["full_decile_overlap"])
        # and they are the SAME object, computed by the same function on the same composite
        self.assertAlmostEqual(
            d["Q1e_identical_assembly"]["4_plus_complete_case"]["decile_overlap"],
            d["Q1f_leave_one_theme_out"]["full_decile_overlap"], places=12)


class TestTheFindingsAreOnTheRecord(unittest.TestCase):
    """The claims a reader would act on, asserted against the banked artifact."""

    def test_assembly_is_the_larger_half_of_the_gap(self):
        d = _art("D9_DIAG.json")
        if d is None:
            self.skipTest("D9_DIAG.json absent")
        s = d["Q1e_identical_assembly"]
        served = s["0_as_served"]["spearman"]
        identical = s["4_plus_complete_case"]["spearman"]
        self.assertGreater(identical - served, 0.30,
                           "the identical-assembly jump is no longer the headline")
        # and it still does not reach D9's B1 -- the residual is data, which is the finding
        self.assertLess(identical, 0.80,
                        "identical assembly now clears B1; the 'residual is data' reading is "
                        "stale and the handoff must be re-read")

    def test_the_whole_recovery_is_the_dead_theme_step(self):
        d = _art("D9_DIAG.json")
        if d is None:
            self.skipTest("D9_DIAG.json absent")
        s = d["Q1e_identical_assembly"]
        step = (s["2_informative_themes_only"]["spearman"]
                - s["1_flat_weights_deployed7"]["spearman"])
        total = (s["4_plus_complete_case"]["spearman"]
                 - s["1_flat_weights_deployed7"]["spearman"])
        self.assertGreater(step / total, 0.85,
                           "dropping the dead themes is no longer the dominant step")

    def test_removing_quality_clears_b1_on_both_readings(self):
        """B1 after deleting `quality` is the part that reproduces; B2 is NOT.

        Deleting `quality` gives a top-decile overlap of 0.5854 on the freeze and 0.6341 on
        `data/backtest` -- one side of the bar each -- so this pins only the claim that
        survives BOTH stores. Asserting the B2 miss would pin a knife-edge result as though it
        were robust, which is exactly the correction this item had to make to its own handoff.
        """
        seen = 0
        for name in ("D9_DIAG.json", "D9_DIAG_SECOND.json"):
            d = _art(name)
            if d is None:
                continue
            seen += 1
            q = d["Q1f_leave_one_theme_out"]["without"]["quality"]
            self.assertGreaterEqual(q["spearman_without_it"], 0.80, name)
        # would otherwise pass having checked NOTHING on a runner with no licensed data --
        # a vacuous pass reads exactly like a real one, which is this project's oldest defect
        if not seen:
            self.skipTest("no D9_DIAG artifact on any candidate data root")

    def test_neither_reading_clears_b2_at_identical_assembly(self):
        """The form the judgement actually rests on, and it holds on both stores.

        ABSENT EVIDENCE IS A LOUD SKIP, NOT A RED TEST. A first cut asserted it had seen at
        least one artifact, which is the right vacuity guard on a machine holding them and the
        wrong failure on a runner that carries no licensed `data/` at all -- it took land run
        #571 red for a reason that says nothing about the tree. The vacuity guard is kept for
        the case that actually matters: an artifact PRESENT and its figure missing.
        """
        seen = 0
        for name in ("D9_DIAG.json", "D9_DIAG_SECOND.json"):
            d = _art(name)
            if d is None:
                continue
            seen += 1
            ov = d["Q1e_identical_assembly"]["4_plus_complete_case"]["decile_overlap"]
            self.assertIsNotNone(ov, "%s carries no decile overlap to check" % name)
            self.assertLess(ov, 0.60, name)
        if not seen:
            self.skipTest("no D9_DIAG artifact on any candidate data root")

    def test_the_ladder_reproduces_on_the_second_reading(self):
        """If it reproduces on only one store it is a property of that store, not the route."""
        a, b = _art("D9_DIAG.json"), _art("D9_DIAG_SECOND.json")
        if a is None or b is None:
            self.skipTest("both readings not banked")
        self.assertNotEqual(a["sharadar_reading"], b["sharadar_reading"])
        ia = a["Q1e_identical_assembly"]["4_plus_complete_case"]["spearman"]
        ib = b["Q1e_identical_assembly"]["4_plus_complete_case"]["spearman"]
        self.assertLess(abs(ia - ib), 0.02,
                        "identical assembly no longer agrees across the two stores (%.4f vs "
                        "%.4f); the diagnosis is store-specific and the handoff is stale"
                        % (ia, ib))

    def test_roe_and_roic_are_recorded_as_definitional(self):
        d = _art("D9_DIAG.json")
        if d is None:
            self.skipTest("D9_DIAG.json absent")
        q = d["Q2_quality_inputs"]
        for like, cross in (("roe", "CROSSDEF_sharadar_roe_ttm_vs_live_roe"),
                            ("roic", "CROSSDEF_sharadar_roic_ttm_vs_live_roic")):
            self.assertGreater(
                q[cross]["spearman"], q[like]["spearman"],
                "the TTM pairing no longer beats the like-named one for %s; the "
                "definitional/vendor split in the handoff is stale" % like)


class TestTheRenewalRecheckDoesNotClobber(unittest.TestCase):
    """A mode that overwrites another mode's artifact destroys the original comparison."""

    def test_same_date_writes_its_own_cache(self):
        tree = ast.parse(_read("scripts", "d9_fidelity.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "same_date"]
        self.assertEqual(len(fn), 1)
        writes = [n for n in ast.walk(fn[0])
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "to_pickle"]
        self.assertTrue(writes, "same_date no longer banks its Sharadar scores")
        for w in writes:
            for a in w.args:
                if isinstance(a, ast.Name):
                    self.assertNotEqual(
                        a.id, "SHAR_CACHE",
                        "same_date writes the two-reading cache, destroying --sharadar's output")

    def test_compare_takes_its_paths_as_parameters(self):
        tree = ast.parse(_read("scripts", "d9_fidelity.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "compare"]
        self.assertEqual(len(fn), 1)
        self.assertEqual([a.arg for a in fn[0].args.args], ["cache", "live_path"])

    def test_same_date_refuses_a_date_mismatch(self):
        """The refusal is the point of the mode: comparing across a gap is what D9 already did.

        Asserted on the MESSAGE, not merely that something raised -- a mode that refused for an
        unrelated reason would satisfy a bare `assertRaises`.
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "d9f_probe", os.path.join(ROOT, "scripts", "d9_fidelity.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tmp = os.path.join(os.environ.get("TEMP", "."), "d9_diag_live_probe.json")
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"scan_date": "2026-08-08", "stocks": []}, fh)
        try:
            # The root is deliberately one that need not exist: the date refusal is now the
            # FIRST thing `same_date` does, so this exercises the refusal it names on any
            # machine rather than dying on a missing export.
            with self.assertRaises(SystemExit) as cm:
                mod.same_date(os.path.join(ROOT, "data", "backtest"), "2026-07-31", tmp)
            self.assertIn("REFUSING", str(cm.exception))
            self.assertIn("SAME date", str(cm.exception))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
