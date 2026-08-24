"""MB18 - the implied-growth expectations gap, and the three kills that fire before any outcome.

WHAT THESE TESTS PIN.

The LOOK-AHEAD pin is the one that matters most and it is enforced structurally rather than by
inspection: `realized_growth` is FORWARD three-year growth, it is the OUTCOME, and the module
never LOADS it -- `_load` selects an explicit allowlist, so the arm path cannot reference what is
not in the frame. The AST test below reads the syntax tree rather than grepping, because MA49
recorded a fixture that failed against the FIXED tree since the comment documenting the repair
quoted the defect verbatim.

The COSTUME kill and the `gap`-column trap are pinned the same way.

The REAL-PANEL tests reproduce the measured figures and SKIP LOUDLY where `data/` is absent -
gitignored, so a worktree and CI have none of it. Skipping is reported and never counted as a
pass; MB21's own C1 passed vacuously at a perfect score on an empty frame two items ago.

This suite also pins the MB7 gate repair MB18 forced: `require_effective_coverage` refused a
register that had already done the right thing, and its own refusal message instructed that
register to do what it had just done.

    python tests/test_mb18_expectations_gap.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from valuation.edge import power_gate as PG  # noqa: E402
from valuation.studies import incremental_ic as II  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb18_expectations_gap.py")
REGISTER = os.path.join(REPO, "PREREG_mb18_expectations_gap.md")
_SKIPS = []


def _data_root():
    """Probe for the FILE, never the directory: a worktree HAS an empty data/free_analysis, and
    existence is not population."""
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isfile(os.path.join(env, "free_analysis", "panel_s23_fairvalue.pkl")):
        return env
    p = REPO
    for _ in range(6):
        cand = os.path.join(p, "data")
        if os.path.isfile(os.path.join(cand, "free_analysis", "panel_s23_fairvalue.pkl")):
            return cand
        p = os.path.dirname(p)
    return None


def _artifact(name):
    root = _data_root()
    if root is None:
        return None
    p = os.path.join(root, "free_analysis", name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _skip(msg):
    _SKIPS.append(msg)
    raise unittest.SkipTest(msg)


def _src():
    with io.open(SCRIPT, encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- the three kills


class TestLookAheadKill(unittest.TestCase):
    """register 1.1 -- realized_growth is the OUTCOME and may never enter a signal."""

    def test_realized_growth_is_not_in_the_load_allowlist(self):
        import scripts.mb18_expectations_gap as M
        self.assertNotIn("realized_growth", M.S23_KEEP)
        self.assertIn("realized_growth", M.FORBIDDEN)

    def test_realized_growth_appears_only_inside_the_guard_that_forbids_it(self):
        """THE tripwire. Read the SYNTAX TREE, not a grep: MA49's fixture failed against the
        FIXED tree because the repair comment quoted the defect verbatim."""
        tree = ast.parse(_src())
        # every string constant that is exactly the forbidden name
        holders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id in ("FORBIDDEN", "S23_KEEP"):
                        holders.append(tgt.id)
        self.assertIn("FORBIDDEN", holders, "the FORBIDDEN allowlist assignment is gone")

        # No ATTRIBUTE or SUBSCRIPT access anywhere names the column.
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "realized_growth":
                bad.append("attribute")
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                    and node.slice.value == "realized_growth":
                bad.append("subscript")
        self.assertEqual(bad, [], "the arm path indexes realized_growth: %r" % bad)

    def test_the_forbidden_columns_never_reach_the_frame(self):
        """A synthetic end-to-end check of the allowlist, so this runs without `data/`."""
        import scripts.mb18_expectations_gap as M
        for col in M.FORBIDDEN:
            self.assertNotIn(col, M.S23_KEEP)


class TestCostumeKill(unittest.TestCase):
    """register 1.2 -- |rho| vs the `value` theme above 0.60 WITHDRAWS the arm."""

    def test_the_kill_bar_is_the_audits_own(self):
        import scripts.mb18_expectations_gap as M
        self.assertEqual(M.COSTUME_KILL, 0.60)
        self.assertEqual(M.COSTUME_COL, "value")

    def test_arms_refuse_when_the_costume_control_withdrew(self):
        import tempfile
        import scripts.mb18_expectations_gap as M
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "c.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"all_gating_pass": True,
                           "C2_costume": {"withdrawn": True, "vs_value": -0.9}}, fh)
            with self.assertRaises(SystemExit):
                M.run_arms(REPO, p, os.path.join(td, "out.json"))

    def test_arms_refuse_without_passing_controls(self):
        import tempfile
        import scripts.mb18_expectations_gap as M
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(SystemExit):
                M.run_arms(REPO, os.path.join(td, "absent.json"), os.path.join(td, "o.json"))
            p = os.path.join(td, "c.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"all_gating_pass": False, "gating": {"C2": False}}, fh)
            with self.assertRaises(SystemExit):
                M.run_arms(REPO, p, os.path.join(td, "o.json"))


class TestGapColumnTrap(unittest.TestCase):
    """register 1.3 -- the panel ships a column called `gap` and it is NOT this arm."""

    def test_gap_is_forbidden_and_not_loaded(self):
        import scripts.mb18_expectations_gap as M
        self.assertIn("gap", M.FORBIDDEN)
        self.assertNotIn("gap", M.S23_KEEP)

    def test_the_candidate_is_built_from_the_two_growth_columns(self):
        import scripts.mb18_expectations_gap as M
        self.assertEqual(M.CANDIDATE, "exp_gap")
        self.assertIn("implied_growth", M.S23_KEEP)
        self.assertIn("base_growth", M.S23_KEEP)


class TestDeclaredSign(unittest.TestCase):

    def test_the_sign_is_negative_and_a_wrong_signed_clear_is_a_fail(self):
        import scripts.mb18_expectations_gap as M
        self.assertEqual(M.DECLARED_SIGN, -1)
        # a large POSITIVE t must NOT clear
        self.assertFalse(M._cell(np.full(40, 0.5))["clears_bar"])
        # a large NEGATIVE t must clear
        self.assertTrue(M._cell(np.full(40, -0.5) + np.linspace(-1e-6, 1e-6, 40))["clears_bar"])

    def test_the_bar_is_x7s_calibrated_floor(self):
        import scripts.mb18_expectations_gap as M
        self.assertEqual(M.BAR, 2.71)
        self.assertEqual(tuple(M.BASES), ("six", "seven"))


# --------------------------------------------------------------------------- the MB7 gate fix


class TestGateRepair(unittest.TestCase):
    """MB18 was the first outside caller of MB7's gate and found a real defect in it."""

    def _block(self, inter_ok):
        return {"candidate": "x", "basis": "seven", "n_dates_raw": 69, "n_dates_effective": 49,
                "min_dates": 16,
                "split_on_effective": {"ok": True, "n_early": 24, "n_late": 24,
                                       "boundary": "2020-01-22"},
                "split_on_raw_then_intersect": {"ok": inter_ok, "n_early": 14, "n_late": 34,
                                                "boundary": "2017-07-20"}}

    def test_a_raw_splitter_is_still_refused(self):
        """The guard keeps its teeth: the default is the STRICT reading."""
        with self.assertRaises(II.RegisterViolation):
            II.require_effective_coverage(self._block(False))
        with self.assertRaises(II.RegisterViolation):
            II.require_effective_coverage(self._block(False), split_used="raw")

    def test_an_effective_splitter_is_allowed_through(self):
        """THE FIX. Before it, the gate refused a register that had already done the right
        thing -- and its refusal message told that register to do what it had just done."""
        II.require_effective_coverage(self._block(False), split_used="effective")

    def test_an_effective_splitter_is_still_refused_on_a_thin_effective_split(self):
        """Refusal 2 keeps working, which is what makes exempting refusal 3 safe."""
        blk = self._block(False)
        blk["split_on_effective"] = {"ok": False, "refusal": "too thin"}
        with self.assertRaises(II.RegisterViolation):
            II.require_effective_coverage(blk, split_used="effective")

    def test_an_undeclared_split_value_is_refused(self):
        with self.assertRaises(II.RegisterViolation):
            II.require_effective_coverage(self._block(False), split_used="whatever")


# --------------------------------------------------------------------------- register discipline


class TestRegisterDiscipline(unittest.TestCase):

    def test_the_register_file_exists_on_disk(self):
        self.assertTrue(os.path.isfile(REGISTER), "register missing: %s" % REGISTER)

    def test_the_power_statement_uses_mb22s_gate(self):
        src = _src()
        self.assertIn("power_gate", src)
        self.assertIn("mde_at_power", src)

    def test_mde_at_power_is_the_eighty_percent_figure_not_the_fifty(self):
        """MB22 exists to stop the 50%-power number being quoted as the 80% one."""
        n, crit = 69, 2.71
        fifty = crit / np.sqrt(n)
        eighty = PG.mde_at_power(n, crit=crit)
        self.assertGreater(eighty, fifty)
        self.assertAlmostEqual(eighty, (crit + PG.Z_POWER_CONVENTION) / np.sqrt(n), places=12)

    #: The commits that carry MB18's own work. Resolved from the item's own files rather than
    #: written down, so a rebase or a re-land cannot make this check quietly stop looking.
    LANE_FILES = ("scripts/mb18_expectations_gap.py", "PREREG_mb18_expectations_gap.md")
    LIVE_PATHS = ("valuation/screener", "valuation/web", "valuation/engine")

    def test_this_lane_touched_no_live_scoring_path(self):
        """MB18's OWN commits, not the working tree.

        CORRECTED 2026-08-20 (SC-4's lane, reported under RUN_RULES rule 3). The first cut ran
        `git diff --name-only origin/main -- valuation/screener valuation/web
        valuation/engine` and required the result to be EMPTY. That compares `origin/main`
        against WHATEVER IS CHECKED OUT, so it does not measure MB18 at all: it fails for any
        lane that ever touches one of those three directories again, forever, and the first
        one to do so had nothing to do with MB18. It went red naming
        `valuation/web/research_record.py` — an app-fixer change to the public research page.

        A permanent tripwire on three whole directories, owned by an item that has already
        landed, is the cry-wolf failure this repository has now written down three times
        (`MA21`, `MB30`, and the sibling comment in `test_research_page.py` two days ago).

        Scoped to the commits that actually carry MB18's files. That is what the test's own
        name says, it stays true however the tree moves afterwards, and it is STRICTER in the
        direction that matters: a working-tree diff would go green the moment MB18's own live
        change was committed and merged, whereas this reads the commit itself and cannot.
        """
        import subprocess

        def _git(*args):
            r = subprocess.run(("git",) + args, capture_output=True, text=True, cwd=REPO)
            return r.stdout.strip() if r.returncode == 0 else None

        shas = set()
        for f in self.LANE_FILES:
            out = _git("log", "--format=%H", "--", f)
            if out:
                shas.update(out.split("\n"))
        self.assertTrue(shas, "no commit carries MB18's own files — this check sees nothing")

        touched = set()
        for sha in shas:
            out = _git("show", "--name-only", "--format=", sha, "--", *self.LIVE_PATHS)
            if out:
                touched.update(l for l in out.split("\n") if l.strip())
        self.assertEqual(sorted(touched), [],
                         "MB18's own commits touched a live path: %r" % sorted(touched))

    def test_the_live_path_check_can_actually_fail(self):
        """Positive control, and it must not be vacuous.

        The check above passes by finding NOTHING, which is exactly what a broken lookup also
        returns. So the same mechanism is pointed at a commit that demonstrably DID touch a
        live path and required to come back non-empty.

        The commit is FOUND, not typed: `HEAD` was the first choice and it is a merge, on which
        `git show --name-only` prints nothing, so the control skipped itself as vacuous. Asking
        the history for a qualifying commit cannot go vacuous while the repository has any
        history at all.
        """
        import subprocess

        def _git(*args):
            r = subprocess.run(("git",) + args, capture_output=True, text=True, cwd=REPO)
            return r.stdout.strip() if r.returncode == 0 else None

        # --no-merges, and it is the SAME defect `09ea4cc` repaired in MB8's identical control
        # hours earlier; that commit reported the blindness as still living elsewhere and this
        # is the elsewhere. The SELECTOR (`git log -- <paths>`) will happily return a MERGE
        # commit, but the VERIFIER (`git show`) prints no diff for a merge unless asked with
        # -m/--first-parent/-c. So the moment a merge became the most recent commit touching a
        # live path — which is what a branch touching `valuation/web` does the instant the gate
        # merges it — the control selected a subject its own mechanism structurally cannot see
        # and failed claiming the mechanism was broken.
        #
        # It does NOT weaken the check: it still finds a real commit touching a live path and
        # still demands the mechanism see it. It only stops choosing a subject with no
        # first-parent diff to show. The docstring above already recorded half of this ("HEAD
        # was the first choice and it is a merge ... so the control skipped itself as vacuous")
        # — the selector was fixed to stop picking HEAD and not to stop picking merges.
        #
        # REPORTED, NOT FIXED HERE (MB18's lane, and the repair is a design choice):
        # `test_this_lane_touched_no_live_scoring_path` above carries the SAME blindness in the
        # DANGEROUS direction — it asserts `git show` finds nothing, so a merge commit carrying
        # a live-path change passes it silently. `09ea4cc` made exactly this report about MB8's
        # copy and left it to that lane; this one is left to MB18's for the same reason.
        out = _git("log", "--no-merges", "--format=%H", "-n", "1", "--", *self.LIVE_PATHS)
        self.assertTrue(out, "no commit in history touches a live path — history unreadable")
        sha = out.split("\n")[0]

        shown = _git("show", "--name-only", "--format=", sha, "--", *self.LIVE_PATHS)
        touched = [l for l in (shown or "").split("\n") if l.strip()]
        self.assertTrue(touched,
                        "the mechanism returned nothing for a commit that touches a live "
                        "path (%s) — the check above passes by seeing nothing" % sha[:8])


# --------------------------------------------------------------------------- artifacts


class TestControlsArtifact(unittest.TestCase):

    def setUp(self):
        self.a = _artifact("MB18_CONTROLS.json")
        if self.a is None:
            _skip("MB18_CONTROLS.json absent (data/ is gitignored) - controls not verified here")

    def test_all_gating_controls_pass(self):
        self.assertTrue(self.a["all_gating_pass"], self.a.get("gating"))

    def test_the_costume_control_survived_and_value_is_the_largest_rho(self):
        c = self.a["C2_costume"]
        self.assertFalse(c["withdrawn"])
        self.assertLessEqual(abs(c["vs_value"]), c["kill_bar"])
        self.assertEqual(c["largest_abs_theme"], "value",
                         "the costume risk was real in DIRECTION even though it did not kill")

    def test_the_shipped_gap_column_is_log_fair_value_over_price(self):
        self.assertLess(self.a["C3_gap_trap"]["shipped_gap_is_log_fv_over_price_maxdev"], 1e-12)
        self.assertNotAlmostEqual(
            self.a["C3_gap_trap"]["corr_shipped_gap_vs_expectations_gap"], 1.0, places=2)

    def test_the_effective_coverage_reproduces_mb7s_defect_on_this_panel(self):
        seven = self.a["C5_effective_coverage"]["seven"]
        self.assertEqual(seven["n_dates_effective"], 49)
        self.assertEqual(seven["first_date_effective"], "2014-01-17")
        self.assertFalse(seven["split_on_raw_then_intersect"]["ok"])
        self.assertTrue(seven["split_on_effective"]["ok"])
        six = self.a["C5_effective_coverage"]["six"]
        self.assertEqual(six["n_dates_effective"], 69)

    def test_the_power_statement_was_computed_before_the_run(self):
        p = self.a["power_before_the_run"]
        self.assertIn("six", p)
        self.assertGreater(p["six"]["mde_80pct_power_sd_units"],
                           p["six"]["detection_threshold_50pct_power_sd_units"])


class TestArmsArtifact(unittest.TestCase):

    def setUp(self):
        self.a = _artifact("MB18_EXPECTATIONS_GAP.json")
        if self.a is None:
            _skip("MB18_EXPECTATIONS_GAP.json absent - arms not verified here")

    def test_the_verdict_follows_the_pre_committed_rule(self):
        both = all(self.a["by_basis"][b]["clears_both_halves"] for b in ("six", "seven"))
        self.assertEqual(both, self.a["verdict"] == "CLEARS")

    def test_no_cell_comes_close_to_the_bar(self):
        worst = max(abs(self.a["by_basis"][b][w]["t"])
                    for b in ("six", "seven")
                    for w in ("full", "early", "late", "unbounded_only")
                    if "t" in self.a["by_basis"][b][w])
        self.assertLess(worst, self.a["bar"])

    def test_the_null_ships_its_mde_caveat(self):
        """Register void condition 7: a null without its MDE may not be reported."""
        self.assertIn("MDE", self.a["mde_caveat"])
        self.assertIn("power_before_the_run", self.a)

    def test_the_trial_was_booked_before_the_run_and_charged_to_equity(self):
        t = self.a["trials"]
        self.assertEqual(t["domain"], "equity")
        self.assertEqual(t["charged"], 1)
        self.assertIn("booked_before_the_run_at", t)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
