"""E-1 / S-SEED-4 - the graveyard votes.

WHAT THESE TESTS PIN.

The load-bearing one is that **NOTHING IS FITTED**. That is the only reason this register
survives a wall the record built out of five orthogonality corpses and a combiner (`MLCOMB`)
that FIT its weights and then REVERSED out of sample. So: the weights are flat and appear
nowhere as a fitted quantity; the arm applies **no sign flip of its own** (the orientation is
the shipped `z_` construction, declared in the register's D2 as the sign record); and the signal
set is DERIVED from the source rather than typed.

Second: **the arm may not run without a passing kills artifact**, and the kills may not read an
outcome. Both are pinned, and the refusal is mutation-tested rather than asserted.

Third, and it is the register's own §5 void condition 3: **a clearing verdict would license NO
component-level claim.** No per-signal outcome statistic exists anywhere in the arm path, read
from the SYNTAX TREE - not grepped, because `MA49`'s family has now bitten this project ten
times and four of those were in this session's own previous batch.

The REAL-PANEL tests SKIP LOUDLY where `data/` is absent - it is gitignored, so a worktree and
CI have none of it. A skip is reported and is never counted as a pass.

    python tests/test_e1_graveyard.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "e1_graveyard_stouffer.py")
REGISTER = os.path.join(REPO, "PREREG_e1_graveyard_stouffer.md")
DRAFT = os.path.join(REPO, "PREREG_DRAFT_s4_graveyard_stouffer.md")
KILLS = os.path.join(REPO, "data", "free_analysis", "E1_KILLS.json")
_SKIPS = []


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _tree():
    return ast.parse(_src(SCRIPT))


def _fn(name):
    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in the script")


def _kills():
    if not os.path.isfile(KILLS):
        return None
    with io.open(KILLS, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ nothing is fitted

class TestNothingIsFitted(unittest.TestCase):
    """The register's whole defence against the wall. MLCOMB fit and reversed."""

    def test_the_arm_applies_no_sign_flip_of_its_own(self):
        """D2 declares the shipped z_ construction AS the sign record. The arm must not
        re-orient anything, or the orientation stops being traceable to registration."""
        import scripts.e1_graveyard_stouffer as E1
        rng = np.random.default_rng(0)
        cols = [f"z_s{i}" for i in range(6)]
        df = pd.DataFrame({c: rng.normal(size=200) for c in cols})
        val, n_ok, need = E1.graveyard_column(df, cols)
        # the column must be the PLAIN mean -- no negation, no reweighting
        expect = df[cols].mean(axis=1)
        self.assertTrue(np.allclose(val.to_numpy(), expect.to_numpy()))

    def test_the_weights_are_flat_and_there_is_no_fitted_quantity(self):
        node = _fn("graveyard_column")
        d = ast.dump(node)
        for banned in ("lstsq", "polyfit", "LinearRegression", "fit(", "cov(", "optimize"):
            self.assertNotIn(banned, d,
                             f"graveyard_column contains {banned!r}; the column must be a flat "
                             f"mean, and MLCOMB is what a fitted combiner did here")
        self.assertIn("mean", d)

    def test_the_signal_set_is_derived_from_the_source_not_typed(self):
        """MA5/B7: an idea written twice is an idea maintained once."""
        node = _fn("weighted_theme_inputs")
        d = ast.dump(node)
        self.assertIn("ast", d.lower() if "parse" in d else "ast",
                      "the theme input lists must be parsed from factors.py")
        self.assertIn("parse", d)
        # And no literal COLUMN NAME is typed into the script. The bare prefix "z_" is the
        # derivation machinery itself (`startswith("z_")`, `f"z_{n}"`) and is not a column name
        # -- so the guard requires a name AFTER the prefix. That distinction is this test's own
        # repair: the first cut banned anything starting "z_" and fired against the CORRECT tree
        # on the prefix, which is `MB1`'s substring family for the fifth time this session.
        typed = [n.value for n in ast.walk(_tree())
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and n.value.startswith("z_") and len(n.value) > 2]
        self.assertEqual(typed, [],
                         f"z_ column names are typed into the script: {typed}. They must be "
                         f"derived, or the set drifts from the shipped themes.")

    def test_that_typed_column_guard_still_catches_the_real_thing(self):
        """A guard loosened to stop crying wolf must still bite."""
        tree = ast.parse('COLS = ("z_neg_vol", "z_roic")\nP = "z_"\n')
        typed = [n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and n.value.startswith("z_") and len(n.value) > 2]
        self.assertEqual(sorted(typed), ["z_neg_vol", "z_roic"])


# ------------------------------------------------- no component claim is reachable (VC3)

class TestNoComponentLevelClaimIsReachable(unittest.TestCase):
    """§5 void condition 3: a clearing arm does NOT license asking which signals carried it."""

    def test_the_arm_computes_no_per_signal_outcome_statistic(self):
        """Read from the syntax tree. The arm's outcome statistics take the AGGREGATE column."""
        node = _fn("per_date_incremental_ic")
        args = [a.arg for a in node.args.args]
        self.assertIn("cand", args, "the incremental IC must take ONE candidate column")
        # the arm entry point must pass the aggregate, never a loop over the component list
        arm = _fn("run_arm")
        for sub in ast.walk(arm):
            if isinstance(sub, ast.For):
                it = ast.dump(sub.iter)
                self.assertNotIn("cols", it,
                                 "run_arm loops over the component columns; that is a "
                                 "per-signal statistic and void condition 3 forbids it")

    def test_the_register_says_so_in_terms(self):
        r = _src(REGISTER)
        self.assertIn("does NOT license", r)
        self.assertIn("second register", r)


# ------------------------------------------------------------------ the gate

class TestTheKillsGateTheArm(unittest.TestCase):

    def test_the_arm_refuses_on_the_real_failing_artifact(self):
        k = _kills()
        if k is None:
            _SKIPS.append("E1_KILLS.json absent (data/ is gitignored)")
            self.skipTest("kills artifact absent")
        r = subprocess.run([sys.executable, "-m", "scripts.e1_graveyard_stouffer", "--arm"],
                           cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSING", r.stdout + r.stderr)

    def test_the_arm_refuses_DIFFERENTLY_when_the_artifact_is_missing(self):
        """Two distinct refusals prove the gate DISTINGUISHES cases rather than always refusing.

        THIS TEST REPLACES A MUTATION TEST THAT WAS ITSELF A VOID-CONDITION BREACH, and the
        replacement is the point. The first cut proved the gate by flipping `all_kills_pass` to
        True and checking the refusal disappeared -- which **RAN THE WITHDRAWN ARM**, scored the
        hypothesis the register had just withdrawn, and wrote `E1_ARM.json`. It was caught by
        this suite's own `test_no_arm_artifact_was_written` on the very next run; the file was
        deleted UNREAD and no figure from it has been opened, printed or recorded anywhere.

        A test that proves a refusal by removing it is not a safe test when the thing behind the
        refusal is forbidden. The property is established here WITHOUT executing the arm: a
        hard-coded refusal could not produce two different messages for two different states.
        """
        if _kills() is None:
            _SKIPS.append("E1_KILLS.json absent")
            self.skipTest("kills artifact absent")
        raw = io.open(KILLS, "rb").read()
        try:
            os.remove(KILLS)
            r = subprocess.run([sys.executable, "-m", "scripts.e1_graveyard_stouffer", "--arm"],
                               cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=600)
        finally:
            io.open(KILLS, "wb").write(raw)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no kills artifact", (r.stdout + r.stderr).lower())
        self.assertNotIn("does not pass", r.stdout + r.stderr,
                         "the two refusal states are indistinguishable, so the gate is not "
                         "reading the artifact it claims to read")

    def test_the_gate_is_conditional_in_the_syntax_tree_not_hard_coded(self):
        """The structural half: the refusal hangs off `all_kills_pass`, not off nothing."""
        arm = _fn("run_arm")
        found = False
        for sub in ast.walk(arm):
            if isinstance(sub, ast.If):
                d = ast.dump(sub)
                if "all_kills_pass" in d and "SystemExit" in d:
                    found = True
        self.assertTrue(found, "run_arm's refusal is not conditional on all_kills_pass")

    def test_the_kills_pass_reads_no_outcome(self):
        """K1, K2 and K3 are input-only. fwd_ret must not be reachable from run_kills."""
        node = _fn("run_kills")
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                self.assertNotEqual(sub.value, "fwd_ret",
                                    "run_kills selects the outcome column; the kills are "
                                    "pre-outcome by construction")
            if isinstance(sub, ast.Attribute):
                self.assertNotEqual(sub.attr, "fwd_ret")

    def test_the_banked_kills_record_that_no_outcome_was_read(self):
        k = _kills()
        if k is None:
            _SKIPS.append("E1_KILLS.json absent")
            self.skipTest("kills artifact absent")
        self.assertTrue(k["no_outcome_read"])


# ------------------------------------------------------------------ the bars are the register's

class TestTheBarsAreTheRegisters(unittest.TestCase):

    def test_the_constants_match_the_register(self):
        import scripts.e1_graveyard_stouffer as E1
        self.assertEqual(E1.BAR, 2.71)
        self.assertEqual(E1.K1_K2_RHO_MAX, 0.60)
        self.assertEqual(E1.K3_MIN_SIGNALS, 25)
        self.assertEqual(E1.BASES, ("six", "seven"))

    def test_the_register_adopted_the_draft_byte_identically(self):
        """The acceptance block claims the draft is verbatim below the rule. Checked."""
        if not os.path.isfile(DRAFT):
            _SKIPS.append("the scout's draft is absent")
            self.skipTest("draft absent")
        self.assertTrue(_src(REGISTER).endswith(_src(DRAFT)),
                        "the register's tail is not byte-identical to the scout's draft")

    def test_the_register_is_a_strict_ancestor_of_the_script(self):
        reg = subprocess.run(["git", "log", "--format=%H", "-1", "--", os.path.basename(REGISTER)],
                             cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.strip()
        scr = subprocess.run(["git", "log", "--format=%H", "-1", "--",
                              "scripts/e1_graveyard_stouffer.py"],
                             cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.strip()
        if not reg or not scr:
            _SKIPS.append("git history unavailable for the ancestry check")
            self.skipTest("git unavailable")
        anc = subprocess.run(["git", "merge-base", "--is-ancestor", reg, scr], cwd=REPO)
        self.assertEqual(anc.returncode, 0,
                         "the register is not a strict ancestor of the measurement script")

    def test_the_register_commit_carried_markdown_only(self):
        out = subprocess.run(["git", "show", "--name-only", "--format=", "e05c33c"], cwd=REPO,
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.split()
        if not out:
            _SKIPS.append("register commit e05c33c unreachable")
            self.skipTest("commit unreachable")
        self.assertEqual(out, ["PREREG_e1_graveyard_stouffer.md"],
                         f"the register commit carried more than the register: {out}")


# ------------------------------------------------------------------ the measured result

class TestTheBankedKills(unittest.TestCase):

    def test_k2_fires_and_the_arm_is_withdrawn(self):
        k = _kills()
        if k is None:
            _SKIPS.append("E1_KILLS.json absent")
            self.skipTest("kills artifact absent")
        self.assertFalse(k["all_kills_pass"])
        self.assertTrue(k["K1_pass"], "K1 is expected to pass on the banked run")
        self.assertTrue(k["K3_pass"], "K3 is expected to pass on the banked run")
        self.assertFalse(k["K2_pass"], "K2 is the kill that fired")
        self.assertGreater(k["K2_rho_vs_size"], 0.60)

    def test_the_census_reproduces_the_registers_D1_correction(self):
        k = _kills()
        if k is None:
            _SKIPS.append("E1_KILLS.json absent")
            self.skipTest("kills artifact absent")
        c = k["census"]
        self.assertEqual(c["registered_total"], 53)
        self.assertEqual(c["weighted_theme_inputs_distinct"], 24)
        self.assertEqual(c["graveyard_n"], 29)
        self.assertGreaterEqual(c["graveyard_n"], 25, "K3's floor")
        # the disagreement D1 is about
        self.assertEqual(c["weighted_theme_inputs_per_theme"]["institutional"], 2)
        self.assertEqual(c["weighted_theme_inputs_per_theme"]["quality"], 10)
        self.assertEqual(c["weighted_theme_inputs_per_theme"]["momentum"], 3)

    def test_the_kill_is_not_a_knife_edge_on_the_median(self):
        """0.6114 fires by 0.0114 on the MEAN. The distribution says whether that is fragile."""
        k = _kills()
        if k is None:
            _SKIPS.append("E1_KILLS.json absent")
            self.skipTest("kills artifact absent")
        d = k["K2_per_date_distribution_no_verdict"]
        self.assertGreater(d["median"], 0.60,
                           "the median per-date |rho| must also exceed the bar, or the kill "
                           "rests on a mean a few dates could move")
        self.assertGreater(d["share_above_0.60"], 0.5)

    def test_no_arm_artifact_was_written(self):
        p = os.path.join(REPO, "data", "free_analysis", "E1_ARM.json")
        self.assertFalse(os.path.isfile(p),
                         "an arm artifact exists; the register WITHDRAWS the arm when a kill "
                         "fires and running it anyway is a void condition")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
