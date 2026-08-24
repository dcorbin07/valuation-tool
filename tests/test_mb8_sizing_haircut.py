"""MB8 - MA28's crash flags as a position-SIZING haircut.

WHAT THESE TESTS PIN.

The load-bearing one is that the arm is JUDGED ON CRASH COUNT AND NEVER ON ALPHA: the alpha leg
exists only as a NON-INFERIORITY guard rail that can REJECT, and it can never make the arm pass.
That is read from the SYNTAX TREE rather than grepped, because MA49 recorded a fixture that failed
against the FIXED tree since the comment documenting the repair quoted the defect verbatim.

Also pinned: the haircut is 0.5x and is not swept; the flags are IMPORTED from MA28's own source
and the thresholds -1.78 / 1.81 are never retyped; the 20% bar and the 1.8629pp margin are the
registered ones; and adoption is never taken.

The REAL-PANEL tests reproduce the measured figures and SKIP LOUDLY where `data/` is absent -
gitignored, so a worktree and CI have none of it. Skipping is reported and never counted as a pass.

    python tests/test_mb8_sizing_haircut.py
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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb8_sizing_haircut.py")
REGISTER = os.path.join(REPO, "PREREG_mb8_sizing_haircut.md")
_SKIPS = []


def _src():
    with io.open(SCRIPT, encoding="utf-8") as fh:
        return fh.read()


def _data_root():
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isfile(os.path.join(env, "free_analysis", "panel_r5r6.pkl")):
        return env
    p = REPO
    for _ in range(6):
        cand = os.path.join(p, "data")
        if os.path.isfile(os.path.join(cand, "free_analysis", "panel_r5r6.pkl")):
            return cand
        p = os.path.dirname(p)
    return None


def _artifact(name):
    """MB8's outputs land in the resolved data root; MA28's own sit in the worktree. Probe both."""
    for base in (_data_root(), os.path.join(REPO, "data")):
        if not base:
            continue
        p = os.path.join(base, "free_analysis", name)
        if os.path.isfile(p):
            with io.open(p, encoding="utf-8") as fh:
                return json.load(fh)
    return None


def _skip(msg):
    _SKIPS.append(msg)
    raise unittest.SkipTest(msg)


# --------------------------------------------------------------------------- the design


class TestJudgedOnCrashCountNeverOnAlpha(unittest.TestCase):
    """THE tripwire. The audit's whole framing is that this is judged on crash count."""

    def test_alpha_can_only_reject_never_pass(self):
        """Read the SYNTAX TREE. The verdict branch must reach an ELIGIBLE outcome only when the
        crash bar is cleared; alpha may only gate a REJECT."""
        tree = ast.parse(_src())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_arm")
        # find the assignments to `verdict`
        eligible_guards = []
        for node in ast.walk(fn):
            if isinstance(node, ast.If):
                assigned = [t.id for s in ast.walk(node) if isinstance(s, ast.Assign)
                            for t in s.targets if isinstance(t, ast.Name)]
                if "verdict" not in assigned:
                    continue
                consts = [c.value for c in ast.walk(node)
                          if isinstance(c, ast.Constant) and isinstance(c.value, str)]
                if any("ELIGIBLE" in c for c in consts):
                    names = {m.id for m in ast.walk(node.test) if isinstance(m, ast.Name)}
                    eligible_guards.append(names)
        self.assertTrue(eligible_guards, "no ELIGIBLE branch found in run_arm")
        # the ELIGIBLE branch must be guarded by the crash bar, not by the alpha leg
        self.assertTrue(any("both" in g for g in eligible_guards),
                        "the ELIGIBLE branch is not guarded by the crash-count bar: %r"
                        % eligible_guards)

    def test_the_guard_rail_is_non_inferiority_not_improvement(self):
        import scripts.mb8_sizing_haircut as M
        self.assertEqual(M.ALPHA_MARGIN_PP, 1.8629)
        src = _src()
        self.assertIn("alpha_noninferior", src)
        # non-inferiority compares the LOSS to the margin, so the comparison must be <=
        self.assertIn("<= ALPHA_MARGIN_PP", src)


class TestTheRegisteredConstants(unittest.TestCase):

    def test_the_haircut_is_half_and_is_not_swept(self):
        import scripts.mb8_sizing_haircut as M
        self.assertEqual(M.HAIRCUT, 0.5)
        tree = ast.parse(_src())
        # no loop anywhere may iterate over a set of haircut values
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                consts = [c.value for c in ast.walk(node.iter)
                          if isinstance(c, ast.Constant) and isinstance(c.value, float)]
                self.assertNotIn(0.5, consts, "a loop sweeps the haircut; register 10.1 forbids it")

    def test_the_bars_are_the_registered_ones(self):
        import scripts.mb8_sizing_haircut as M
        self.assertEqual(M.REDUCTION_BAR, 0.20)
        self.assertEqual(M.CRASH, -0.50)
        self.assertEqual(M.N_Q, 10)

    def test_the_flags_are_imported_and_the_thresholds_are_never_retyped(self):
        """MA28's own suite bans redefining these; the ban is inherited.

        READ THE SYNTAX TREE, NOT THE TEXT. The first cut of this test grepped the source and
        FAILED against the correct tree, because this script's own docstring says "the thresholds
        -1.78 and 1.81 are never retyped" -- a comment documenting the rule, quoting the values
        the rule forbids. That is MA49's comment-versus-code defect, and it is now the fifth time
        this project has hit it. The AST sees code; it does not see prose about code.
        """
        tree = ast.parse(_src())

        # (a) the flags are IMPORTED
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                    and n.module == "scripts.s10_accounting_veto" for a in n.names}
        self.assertIn("build_flags", imported)

        # (b) none of them is REDEFINED
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("build_flags", "beneish_m", "altman_z"):
            self.assertNotIn(banned, defined, "MB8 redefines %r" % banned)

        # (c) neither threshold appears as a NUMERIC LITERAL in the code
        nums = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))                     and not isinstance(n.value, bool):
                nums.add(float(n.value))
        for banned in (1.78, 1.81):
            self.assertNotIn(banned, nums, "MB8 retypes the threshold %r as a literal" % banned)

    def test_the_deployed_composite_is_seven_at_one_eighth(self):
        """MA28 records C1 firing on exactly this: nine themes at 1/7 gave a different book."""
        import scripts.mb8_sizing_haircut as M
        self.assertEqual(len(M.THEMES), 7)
        self.assertEqual(M.W, 0.125)
        self.assertNotIn("growth", M.THEMES)
        self.assertNotIn("low_risk", M.THEMES)


class TestTheHaircutMechanics(unittest.TestCase):

    def _book(self, flags, rets):
        return [{"date": "2020-01-01", "rows": np.arange(len(rets)),
                 "fwd_top": np.array(rets, dtype=float),
                 "fwd_all_mean": 0.0, "n_all": len(rets)}], dict(enumerate(flags))

    def test_a_flagged_crash_contributes_less_than_an_unflagged_one(self):
        import scripts.mb8_sizing_haircut as M
        book, fl = self._book([True, False], [-0.9, -0.9])
        df = M._exposure(book, fl, 0.5)
        # un-renormalised: 0.5 + 1.0 = 1.5 against a base count of 2
        self.assertAlmostEqual(df["crash_exposure_plain"].iloc[0], 1.5, places=12)
        self.assertAlmostEqual(df["crash_count_base"].iloc[0], 2.0, places=12)

    def test_at_a_1x_haircut_the_arm_is_the_base_book(self):
        """C4. A sizing arm that moves something at 1.0x is not measuring the haircut."""
        import scripts.mb8_sizing_haircut as M
        book, fl = self._book([True, False, True], [-0.9, 0.2, -0.6])
        df = M._exposure(book, fl, 1.0)
        self.assertAlmostEqual(df["crash_exposure_renorm"].iloc[0],
                               df["crash_count_base"].iloc[0], places=12)
        self.assertAlmostEqual(df["ret_renorm"].iloc[0], df["ret_base"].iloc[0], places=15)

    def test_renormalising_keeps_the_book_fully_invested(self):
        import scripts.mb8_sizing_haircut as M
        book, fl = self._book([True, True, False, False], [0.1, -0.9, 0.2, 0.3])
        df = M._exposure(book, fl, 0.5)
        # mean weight 1 => a flat-return book returns that return exactly
        book2, fl2 = self._book([True, True, False, False], [0.1, 0.1, 0.1, 0.1])
        d2 = M._exposure(book2, fl2, 0.5)
        self.assertAlmostEqual(d2["ret_renorm"].iloc[0], 0.1, places=12)
        self.assertGreater(df["n_holdings"].iloc[0], 0)

    def test_the_unrenormalised_form_holds_cash_and_says_so(self):
        import scripts.mb8_sizing_haircut as M
        book, fl = self._book([True, True, False, False], [0.1, 0.1, 0.1, 0.1])
        df = M._exposure(book, fl, 0.5)
        # plain divides by n, so haircutting half the names to 0.5x drags the return
        self.assertLess(df["ret_plain"].iloc[0], 0.1)


class TestRegisterDiscipline(unittest.TestCase):

    def test_the_register_file_exists_on_disk(self):
        self.assertTrue(os.path.isfile(REGISTER), "register missing: %s" % REGISTER)

    def test_the_arm_refuses_without_passing_controls(self):
        import tempfile
        import scripts.mb8_sizing_haircut as M
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(SystemExit):
                M.run_arm(REPO, os.path.join(td, "absent.json"), os.path.join(td, "o.json"))
            p = os.path.join(td, "c.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"all_gating_pass": False, "gating": {"C1_record": False}}, fh)
            with self.assertRaises(SystemExit):
                M.run_arm(REPO, p, os.path.join(td, "o.json"))

    #: Resolved from the item's own files rather than written down, so a rebase or a re-land
    #: cannot make this check quietly stop looking.
    LANE_FILES = ("scripts/mb8_sizing_haircut.py", "PREREG_mb8_sizing_haircut.md")
    LIVE_PATHS = ("valuation/screener", "valuation/web", "valuation/engine", "valuation/edge")

    def test_this_lane_touched_no_live_scoring_path(self):
        """MB8's OWN commits, not the working tree.

        CORRECTED 2026-08-20 (SC-4's lane, reported under RUN_RULES rule 3). The first cut ran
        `git diff --name-only origin/main -- <live paths>` and required EMPTY. That compares
        `origin/main` against WHATEVER IS CHECKED OUT, so it never measured MB8 at all: it
        fails for any lane that touches one of those four directories again, FOREVER. It
        failed the land gate for an app-fixer change to the public research page — a change
        with no relationship to MB8 whatever.

        THE SAME DEFECT WAS IN `test_mb18_expectations_gap.py` AND IS FIXED THE SAME WAY. Two
        copies means this is a TEMPLATE being carried between lanes, not an accident, which is
        why a repo-wide convention check now forbids the working-tree form outright.


        MERGE-BLINDNESS REPAIRED 2026-08-23 (S3-I3's lane, reported under RUN_RULES rule 3).
        `git show --name-only` returns NOTHING for a merge commit unless asked, while
        `git log -- <paths>` will hand one over whenever the merge is treesame to neither
        parent for those paths -- which is what a lane produces by adding a file under one live
        path and merging main's changes to another. The mechanism could therefore be given a
        commit it could not describe, and the check would pass by seeing nothing.
        `--diff-merges=first-parent` fixes it; non-merge behaviour is bit-identical.

        Scoped to the commits that actually carry MB8's files. That is what the test's own name
        says, it stays true however the tree moves afterwards, and it is STRICTER in the
        direction that matters: a working-tree diff goes green the moment such a change is
        committed and merged, whereas reading the commit cannot.
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
        self.assertTrue(shas, "no commit carries MB8's own files — this check sees nothing")

        touched = set()
        for sha in shas:
            out = _git("show", "--diff-merges=first-parent", "--name-only", "--format=",
                        sha, "--", *self.LIVE_PATHS)
            if out:
                touched.update(l for l in out.split("\n") if l.strip())
        self.assertEqual(sorted(touched), [],
                         "MB8's own commits touched a live path: %r" % sorted(touched))

    def test_the_live_path_check_can_actually_fail(self):
        """Positive control: the check above passes by finding NOTHING, which is also what a
        broken lookup returns. The commit is FOUND rather than typed, so it cannot go vacuous
        while the repository has any history."""
        import subprocess

        def _git(*args):
            r = subprocess.run(("git",) + args, capture_output=True, text=True, cwd=REPO)
            return r.stdout.strip() if r.returncode == 0 else None

        out = _git("log", "--format=%H", "-n", "1", "--", *self.LIVE_PATHS)
        self.assertTrue(out, "no commit in history touches a live path — history unreadable")
        sha = out.split("\n")[0]
        shown = _git("show", "--diff-merges=first-parent", "--name-only", "--format=",
                        sha, "--", *self.LIVE_PATHS)
        touched = [l for l in (shown or "").split("\n") if l.strip()]
        self.assertTrue(touched,
                        "the mechanism returned nothing for a commit that touches a live "
                        "path (%s) — the check above passes by seeing nothing" % sha[:8])

    def test_adoption_is_routed_never_taken(self):
        src = _src()
        self.assertIn("ROUTED TO DON", src)
        self.assertIn("VINTAGE EVENT", src)


# --------------------------------------------------------------------------- artifacts


class TestControlsArtifact(unittest.TestCase):

    def setUp(self):
        self.a = _artifact("MB8_CONTROLS.json")
        if self.a is None:
            _skip("MB8_CONTROLS.json absent (data/ is gitignored) - controls not verified here")

    def test_all_gating_controls_pass(self):
        self.assertTrue(self.a["all_gating_pass"], self.a.get("gating"))

    def test_c1_reproduces_the_published_record_exactly(self):
        self.assertLess(self.a["C1_record"]["max_abs_delta"], 1e-9)

    def test_c2_proves_my_membership_is_the_shipped_one(self):
        """The control MB18 taught this lane to build: a re-derived construction must be PROVED
        identical, not assumed."""
        c2 = self.a["C2_membership"]
        self.assertEqual(c2["n_dates_mine"], c2["n_dates_shipped"])
        self.assertLess(c2["max_abs_delta_per_date_alpha"], 1e-12)

    def test_c3_reproduces_ma28s_flag_counts(self):
        c3 = self.a["C3_flags"]
        self.assertEqual(c3["flagged_rows"], c3["ma28_flagged_rows"])
        self.assertLess(abs(c3["flagged_share"] - c3["ma28_flagged_share"]), 5e-4)
        self.assertLess(abs(c3["unflaggable_share"] - c3["ma28_unflaggable_share"]), 1e-3)

    def test_c4_is_bit_identical_at_a_1x_haircut(self):
        self.assertEqual(self.a["C4_inert_at_1x"]["max_abs_delta_exposure"], 0.0)


class TestArmArtifact(unittest.TestCase):

    def setUp(self):
        self.a = _artifact("MB8_SIZING_HAIRCUT.json")
        if self.a is None:
            _skip("MB8_SIZING_HAIRCUT.json absent - the arm is not verified here")

    def test_the_verdict_follows_the_pre_committed_rule(self):
        both = self.a["crash_bar_cleared_both_halves"]
        guard = self.a["guard_rail_passed"]
        if not guard:
            self.assertIn("REJECTED", self.a["verdict"])
        elif both:
            self.assertIn("ELIGIBLE", self.a["verdict"])
        else:
            self.assertIn("KILL", self.a["verdict"])

    def test_the_reduction_never_exceeds_its_arithmetic_ceiling(self):
        """register 1: reduction <= 0.5 x flagged share of crash exposure. The un-renormalised
        form must satisfy it exactly; the renormalised one is bounded above by it."""
        for w, c in self.a["windows"].items():
            if c["implied_max_reduction"] is None:
                continue
            self.assertLessEqual(c["reduction_plain"], c["implied_max_reduction"] + 1e-12, w)
            self.assertLessEqual(c["reduction_renorm"], c["implied_max_reduction"] + 1e-12, w)

    def test_the_fail_open_census_is_reported_in_the_book(self):
        """register 8 C5, and the half that matters is the crash RATE, not just the count."""
        cen = self.a["C5_fail_open_census_in_book"]
        for k in ("flagged", "flaggable_kept", "unflaggable"):
            self.assertIn(k, cen)
            self.assertIn("crash_rate", cen[k])
        self.assertGreater(cen["unflaggable"]["holdings"], 0)

    def test_adoption_was_not_taken(self):
        self.assertNotIn("ADOPTED", self.a["verdict"])

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
