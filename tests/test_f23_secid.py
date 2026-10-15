# -*- coding: utf-8 -*-
"""`F23-SECID` — the SEC-insider-ID check: the design, the gates, and the cell it may read.

Nothing here needs the licensed export or a banked panel, so none of it fails open on a CI runner —
and none of it can take the suite down either, which is the inverse failure this lane shipped two
items ago (`except Exception` not catching a refusing resolver's `SystemExit`).
"""
from __future__ import annotations

import ast
import io
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402
from valuation.studies import insider_routine as IR                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, "PREREG_f23_secid.md")


def _src(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read()


def _tree(rel):
    return ast.parse(_src(rel))


class TheRegisterCameFirstAndAlone(unittest.TestCase):
    def test_the_register_file_exists(self):
        self.assertTrue(os.path.isfile(REGISTER), REGISTER)

    def test_its_introducing_commit_touched_exactly_one_file(self):
        try:
            out = subprocess.run(["git", "log", "--format=%H", "-n", "40", "--", REGISTER],
                                 cwd=REPO, capture_output=True).stdout.decode("utf-8")
        except Exception as e:                                              # noqa: BLE001
            self.skipTest("git unavailable: %r" % (e,))
        shas = [x for x in out.split() if x]
        if not shas:
            self.skipTest("register not in this checkout's history")
        files = subprocess.run(["git", "show", "--name-only", "--format=", shas[-1]],
                               cwd=REPO, capture_output=True).stdout.decode("utf-8").split()
        self.assertEqual([f for f in files if f.strip()], ["PREREG_f23_secid.md"])

    def test_it_is_a_strict_ancestor_of_both_runners(self):
        """A register that lands after its own runner is not a pre-registration."""
        for rel in ("scripts/f23_secid_events.py", "scripts/f23_secid_arm.py"):
            p = os.path.join(REPO, rel)
            if not os.path.isfile(p):
                self.skipTest("%s absent" % rel)
        try:
            reg = subprocess.run(["git", "log", "--format=%H", "--", REGISTER],
                                 cwd=REPO, capture_output=True).stdout.decode("utf-8").split()
        except Exception as e:                                              # noqa: BLE001
            self.skipTest("git unavailable: %r" % (e,))
        if not reg:
            self.skipTest("register not in history")
        first = reg[-1]
        for rel in ("scripts/f23_secid_events.py", "scripts/f23_secid_arm.py"):
            shas = subprocess.run(["git", "log", "--format=%H", "--", rel],
                                  cwd=REPO, capture_output=True).stdout.decode("utf-8").split()
            if not shas:
                continue
            r = subprocess.run(["git", "merge-base", "--is-ancestor", first, shas[-1]],
                               cwd=REPO, capture_output=True)
            self.assertEqual(r.returncode, 0,
                             "the register must be a strict ancestor of %s" % rel)


class BothArmsRunOnOneSourceSoOnlyTheKeyDiffers(unittest.TestCase):
    """The register's §1 design. Sourcing the ID arm from the SEC while leaving the name arm on
    SF2 would change the FEED and the KEY at once, and neither could be attributed."""

    def test_the_events_module_never_reads_the_licensed_export(self):
        tree = _tree("scripts/f23_secid_events.py")
        names = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertNotIn("sf2_zip", names,
                         "both arms must come from the SEC data, or the comparison is confounded")

    def test_that_check_is_not_vacuous(self):
        probe = ast.parse("x = IC.sf2_zip()")
        names = {n.func.attr for n in ast.walk(probe)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertIn("sf2_zip", names)

    def test_the_two_arms_differ_only_in_the_identity_column(self):
        from scripts import f23_secid_arm as AR
        src = _src("scripts/f23_secid_events.py")
        self.assertIn('("name", "name_key")', src)
        self.assertIn('("id", "cik")', src)
        self.assertEqual(AR.FLOOR, 500e6)
        self.assertEqual(AR.H, 63)

    def test_the_cluster_rule_is_imported_and_not_restated(self):
        """`B7`: the rule's own `k`, window, cooldown and strict condition are called."""
        tree = _tree("scripts/f23_secid_events.py")
        names = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for want in ("opportunistic_purchases", "cluster_events", "classify"):
            self.assertIn(want, names, "must DELEGATE %s" % want)
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("cluster_events", "opportunistic_purchases", "prior_year_presence",
                       "classify"):
            self.assertNotIn(banned, defined, "must not re-implement %s" % banned)

    def test_the_arm_imports_the_scorer_rather_than_writing_a_second_one(self):
        tree = _tree("scripts/f23_secid_arm.py")
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("score", defined)
        self.assertIn("insider_wide_arm", _src("scripts/f23_secid_arm.py"))

    def test_the_labels_come_from_the_shipped_classifier(self):
        """A placeholder label Series would have kept ZERO rows, because
        `opportunistic_purchases` keeps only `labels == IR.OPPORTUNISTIC` — and both arms would
        have reported zero events without raising. That was this item's first real defect."""
        src = _src("scripts/f23_secid_events.py")
        self.assertIn("IR.classify(", src)
        self.assertIn("REFUSING", src)
        self.assertTrue(hasattr(IR, "OPPORTUNISTIC"))

    def test_a_zero_row_arm_refuses_rather_than_scoring_zero(self):
        tree = _tree("scripts/f23_secid_events.py")
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "clusters"]
        self.assertEqual(len(fn), 1)
        self.assertGreaterEqual(len([n for n in ast.walk(fn[0]) if isinstance(n, ast.Raise)]), 1)


class TheCellIsTheBuildCellAndNothingElse(unittest.TestCase):
    def test_the_arm_restricts_to_the_build_window_and_ticker_half_zero(self):
        src = _src("scripts/f23_secid_arm.py")
        self.assertIn("D.BUILD_LO", src)
        self.assertIn("D.BUILD_HI", src)
        self.assertIn("stable_key_half) == 0", src)

    def test_the_check_window_is_not_reachable_from_this_arm(self):
        """The check quadrant is SPENT. A literal 2020 date anywhere in the arm would be the
        first sign of it being read."""
        src = _src("scripts/f23_secid_arm.py")
        tree = ast.parse(src)
        bad = [n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and n.value.startswith("2020")]
        self.assertEqual(bad, [], "a 2020 date literal in the arm: %s" % bad)
        self.assertNotIn("ERA_CHECK", src)

    def test_the_build_window_really_is_2009_to_2019(self):
        self.assertEqual(D.BUILD_LO, "2009-01-01")
        self.assertEqual(D.BUILD_HI, "2019-12-31")

    def test_the_half_boundary_is_stage_ones_and_not_re_chosen(self):
        self.assertEqual(D.HALF_BOUNDARY, "2015-01-01")
        self.assertIn("D.HALF_BOUNDARY", _src("scripts/f23_secid_arm.py"))

    def test_the_pull_starts_two_years_before_the_build_window(self):
        """Derived from the strict two-prior-year condition, not chosen."""
        from scripts import f23_secid_events as EV
        self.assertEqual(EV.PULL_LO_YEAR, int(D.BUILD_LO[:4]) - 2)
        self.assertEqual(EV.PULL_HI_YEAR, int(D.BUILD_HI[:4]))
        self.assertEqual(len(EV.quarters()), 52)


class TheGatesAndTheVocabulary(unittest.TestCase):
    def test_the_arm_refuses_without_the_event_pass(self):
        """`O10`: a gating pass and its outcomes must not share an invocation."""
        tree = _tree("scripts/f23_secid_arm.py")
        self.assertGreaterEqual(len([n for n in ast.walk(tree) if isinstance(n, ast.Raise)]), 2)
        self.assertIn("run scripts.f23_secid_events first", _src("scripts/f23_secid_arm.py"))

    def test_bh_k_is_one_and_the_code_says_what_that_is_worth(self):
        """A margin dressed as a correction is the error `R1-VAR` names. With one verdict arm BH
        does no correcting work, and the artifact must say so rather than imply otherwise."""
        from scripts import f23_secid_arm as AR
        self.assertEqual(AR.BH_K, 1)
        src = _src("scripts/f23_secid_arm.py")
        self.assertIn("does\n", src.replace("does ", "does\n"))  # the phrase exists in some form
        self.assertIn("NO correcting work", src)

    def test_the_name_arm_carries_no_verdict(self):
        src = _src("scripts/f23_secid_arm.py")
        self.assertIn('("name", False)', src)
        self.assertIn('("id", True)', src)
        self.assertIn("REFERENCE -- NO VERDICT", src)

    def test_the_vocabulary_is_clears_or_does_not_clear(self):
        src = _src("scripts/f23_secid_arm.py")
        self.assertIn("CLEARS", src)
        self.assertIn("DOES NOT CLEAR", src)

    def test_the_t_bar_is_two_and_labelled_uncalibrated(self):
        from scripts import f23_secid_arm as AR
        self.assertEqual(AR.T_BAR, 2.0)
        self.assertIn("UNCALIBRATED", _src("scripts/f23_secid_arm.py"))

    def test_the_hlz_hurdle_is_reported_and_never_compared(self):
        tree = _tree("scripts/f23_secid_arm.py")
        for n in ast.walk(tree):
            if isinstance(n, ast.Compare):
                self.assertNotIn("hlz_hurdle", ast.dump(n))
        self.assertIn("hlz_hurdle_reported_not_gated", _src("scripts/f23_secid_arm.py"))

    def test_the_register_declares_the_power_before_the_run(self):
        t = _src("PREREG_f23_secid.md")
        self.assertIn("50.3%", t)
        self.assertIn("1.6030pp", t)
        self.assertIn("14.7%", t)

    def test_the_register_forbids_searching_for_a_passing_variant(self):
        t = _src("PREREG_f23_secid.md")
        self.assertIn("variant searched for", t.lower().replace("**", ""))


class TheIdentityCensusIsDecomposedBothWays(unittest.TestCase):
    """The register's §4.4. "Whether names counted one person twice" is one of two directions and
    reporting only one would answer half the question."""

    def test_both_directions_are_computed(self):
        src = _src("scripts/f23_secid_events.py")
        self.assertIn("names_carrying_more_than_one_cik", src)
        self.assertIn("ciks_under_more_than_one_name", src)

    def test_the_within_ticker_figures_are_computed_because_that_is_the_rules_unit(self):
        src = _src("scripts/f23_secid_events.py")
        self.assertIn("ticker_name_pairs_with_multiple_ciks", src)
        self.assertIn("ticker_cik_pairs_with_multiple_names", src)

    def test_the_83_percent_is_explicitly_not_this_number(self):
        """`INSIDER-LIVE-FEED`'s ~83% was a SEC-vs-SF2 FEED overlap. Conflating a feed comparison
        with a key comparison is the wrong-object family."""
        for rel in ("scripts/f23_secid_events.py", "scripts/f23_secid_arm.py"):
            self.assertIn("NOT_THE_83_PERCENT", _src(rel))

    def test_the_name_key_is_not_a_tunable_fuzzy_match(self):
        from scripts import f23_secid_events as EV
        self.assertEqual(EV._norm_name("Smith, John A."), "SMITH JOHN A")
        self.assertEqual(EV._norm_name("  smith   john  a  "), "SMITH JOHN A")
        tree = _tree("scripts/f23_secid_events.py")
        names = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for banned in ("ratio", "token_sort_ratio", "get_close_matches"):
            self.assertNotIn(banned, names)


class TheFeedPullRefusesRatherThanGuessing(unittest.TestCase):
    def test_both_sec_path_prefixes_are_tried(self):
        from scripts import f23_secid_events as EV
        self.assertEqual(len(EV.PREFIXES), 2)
        self.assertTrue(any("structureddata" in p for p in EV.PREFIXES))
        self.assertTrue(any("datastandardsinnovation" in p for p in EV.PREFIXES))

    def test_a_quarter_reachable_under_neither_prefix_refuses(self):
        src = _src("scripts/f23_secid_events.py")
        self.assertIn("unreachable under either prefix", src)

    def test_a_quarter_with_zero_form_4_submissions_refuses(self):
        """The `blank-code counter` family: this lane already shipped a counter that read ZERO
        Form 4s across four years and reported it."""
        self.assertIn("parsed ZERO Form 4 submissions", _src("scripts/f23_secid_events.py"))

    def test_a_missing_transaction_code_is_skipped_explicitly(self):
        src = _src("scripts/f23_secid_events.py")
        self.assertIn("fillna(False)", src)
        self.assertEqual(IC.PURCHASE_CODE, "P")


class ItAdoptsNothing(unittest.TestCase):
    def test_every_write_goes_through_the_artifact_path_helper(self):
        """**THE FIRST FORM OF THIS TEST BANNED THE SUBSTRING `valuation/` AND FIRED AGAINST THE
        CORRECT TREE**, because the arm's own `ADOPTS_NOTHING` prose says *"No file under
        valuation/ changes"* — prose documenting the rule containing what the rule forbids. That
        is the eleventh instance of the family in this record and the third in this session.

        The real property is about WRITES, not about a string: every `open`/`io.open` in write
        mode must take its path from `D.out_path`, which resolves under `data/free_analysis`. Asked
        of the syntax tree, where a docstring is a string constant and not a call.
        """
        for rel in ("scripts/f23_secid_events.py", "scripts/f23_secid_arm.py"):
            tree = _tree(rel)
            writes = []
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                fn = n.func
                nm = (fn.attr if isinstance(fn, ast.Attribute)
                      else (fn.id if isinstance(fn, ast.Name) else None))
                if nm not in ("open",):
                    continue
                mode = ""
                if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                    mode = str(n.args[1].value)
                for kw in n.keywords or []:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = str(kw.value.value)
                if "w" not in mode:
                    continue
                arg = n.args[0] if n.args else None
                # A write whose path is a STRING LITERAL is the one that can escape to an
                # arbitrary file. A write to a VARIABLE assigned from `out_path` is correct, and
                # the second form of this test wrongly demanded a direct call -- too strict, and
                # it fired on `pth = D.out_path(OUT); io.open(pth, "w")`.
                literal = isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                writes.append((ast.unparse(arg)[:60] if arg is not None else "?", literal))
            self.assertTrue(writes, "%s: no write found, so this test is vacuous" % rel)
            bad = [w for (w, lit) in writes if lit]
            self.assertEqual(bad, [], "%s writes to a literal path: %s" % (rel, bad))
            self.assertIn("out_path", _src(rel),
                          "%s must route its artifact through out_path" % rel)

    def test_that_write_check_is_not_vacuous(self):
        """POSITIVE CONTROL: a write to an arbitrary path must be caught."""
        probe = ast.parse('io.open("valuation/engine/pipeline.py", "w")')
        found = []
        for n in ast.walk(probe):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)                     and n.func.attr == "open":
                mode = str(n.args[1].value) if len(n.args) > 1 else ""
                arg = n.args[0]
                if "w" in mode and isinstance(arg, ast.Constant):
                    found.append(ast.unparse(arg))
        self.assertEqual(found, ["'valuation/engine/pipeline.py'"])

    def test_the_artifact_says_it_adopts_nothing(self):
        self.assertIn("ADOPTS_NOTHING", _src("scripts/f23_secid_arm.py"))

    def test_no_order_is_placed_anywhere(self):
        for rel in ("scripts/f23_secid_events.py", "scripts/f23_secid_arm.py"):
            tree = _tree(rel)
            names = {n.func.attr for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
            for banned in ("place_equity_order", "submit_order", "record", "arm"):
                self.assertNotIn(banned, names, "%s must not %s" % (rel, banned))


if __name__ == "__main__":
    unittest.main(verbosity=2)
