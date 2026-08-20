"""E-2 / S-SEED-3 - Δcomposite, fundamental momentum of the score itself.

WHAT THESE TESTS PIN.

The load-bearing one is `C-FIDELITY`: **the composite being differenced must BE the shipped
one**, reproducing the published record exactly. That control is the register's own D2, added
because `MB18` re-derived a construction two items ago and its probe appeared to refute a
mechanism it in fact confirmed, and because `MA28`'s equivalent control FIRED on its own first
run against a nine-theme composite wearing a seven-theme name.

Second: **the Δ is taken across CONSECUTIVE rebalance dates only.** A name absent for a quarter
must not silently difference across a two-quarter gap - that is a longer lookback, and §6 void
condition 1 forbids one. Pinned on a synthetic panel with a deliberate hole.

Third: **the declared sign is POSITIVE and a cell clears only in that direction**, and the
register's D4 scope sentence (the object is a change in RELATIVE standing) travels in the
artifact.

The REAL-PANEL tests SKIP LOUDLY where `data/` is absent - it is gitignored, so a worktree and
CI have none of it. A skip is reported and is never counted as a pass.

    python tests/test_e2_delta_composite.py
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
SCRIPT = os.path.join(REPO, "scripts", "e2_delta_composite.py")
REGISTER = os.path.join(REPO, "PREREG_e2_delta_composite.md")
DRAFT = os.path.join(REPO, "PREREG_DRAFT_s3_delta_composite.md")
KILLS = os.path.join(REPO, "data", "free_analysis", "E2_KILLS.json")
ARM = os.path.join(REPO, "data", "free_analysis", "E2_ARM.json")
_SKIPS = []


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _fn(name):
    for node in ast.walk(ast.parse(_src(SCRIPT))):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def _load(p):
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ the object

class TestTheDeltaIsConsecutiveOnly(unittest.TestCase):
    """§6 void condition 1: no lookback longer than one rebalance."""

    def test_a_gap_produces_NaN_not_a_two_quarter_difference(self):
        import scripts.e2_delta_composite as E2
        # T0 present on all four dates; T1 MISSING on the second, so its third-date Δ must be
        # NaN rather than a silent difference across the hole.
        rows = []
        for i, d in enumerate(["2010-01-15", "2010-04-15", "2010-07-15", "2010-10-15"]):
            for t, val in (("T0", float(i)), ("T1", float(i) * 10)):
                if t == "T1" and i == 1:
                    continue
                rows.append({"date": d, "ticker": t, "composite": val})
        p = pd.DataFrame(rows)
        dc, consec = E2.add_delta(p)
        p = p.assign(dc=dc)
        t1 = p[p["ticker"] == "T1"].sort_values("date")
        # T1's rows are dates 0, 2, 3. Date 2 has no immediate predecessor -> NaN.
        self.assertTrue(np.isnan(t1[t1["date"] == "2010-07-15"]["dc"].iloc[0]),
                        "a Δ was taken across a missing quarter; that is a longer lookback")
        self.assertFalse(np.isnan(t1[t1["date"] == "2010-10-15"]["dc"].iloc[0]),
                         "the consecutive pair after the hole must still difference")
        t0 = p[p["ticker"] == "T0"].sort_values("date")
        self.assertTrue(np.isnan(t0["dc"].iloc[0]), "the first date has no predecessor")
        self.assertTrue(np.allclose(t0["dc"].iloc[1:].to_numpy(), [1.0, 1.0, 1.0]))

    def test_one_names_gap_cannot_affect_another_names_delta(self):
        import scripts.e2_delta_composite as E2
        rows = []
        for i, d in enumerate(["2010-01-15", "2010-04-15", "2010-07-15"]):
            for t in ("A", "B"):
                if t == "B" and i == 1:
                    continue
                rows.append({"date": d, "ticker": t, "composite": float(i)})
        dc, _ = E2.add_delta(pd.DataFrame(rows))
        got = pd.DataFrame(rows).assign(dc=dc)
        a = got[got["ticker"] == "A"].sort_values("date")["dc"].to_numpy()
        self.assertTrue(np.isnan(a[0]))
        self.assertTrue(np.allclose(a[1:], [1.0, 1.0]))

    def test_the_composite_is_CALLED_not_re_derived(self):
        """MB18's defect: re-deriving a construction instead of calling the shipped one."""
        node = _fn("add_composite")
        d = ast.dump(node)
        self.assertIn("composite_from_frame", d,
                      "add_composite must call the shipped composite_from_frame")


# ------------------------------------------------------------------ C-FIDELITY

class TestCFidelity(unittest.TestCase):
    """Register D2. A CONTROL: it can only BLOCK, never produce (MB1-SEL)."""

    def test_the_published_record_is_the_target_and_is_not_retyped_loosely(self):
        import scripts.e2_delta_composite as E2
        self.assertEqual(E2.REC["top_decile_alpha"], 0.07174142332098163)
        self.assertEqual(E2.REC["long_short_tstat"], 2.8360640685320595)
        self.assertEqual(E2.REC["long_short_tstat_nw"], 2.6199121240414884)
        self.assertEqual(E2.REC["monotonicity"], -0.8909090909090909)

    def test_the_banked_control_is_EXACT(self):
        k = _load(KILLS)
        if k is None:
            _SKIPS.append("E2_KILLS.json absent (data/ is gitignored)")
            self.skipTest("kills artifact absent")
        c = k["C_FIDELITY"]
        self.assertTrue(c["pass"])
        self.assertEqual(c["max_abs_delta"], 0.0,
                         "the composite being differenced is not the published object")

    def test_the_control_gates_the_run(self):
        node = _fn("run_kills")
        d = ast.dump(node)
        self.assertIn("fid_pass", d)
        self.assertIn("all_kills_pass", d)


# ------------------------------------------------------------------ the kills

class TestTheKills(unittest.TestCase):

    def test_K2_is_taken_against_BOTH_banked_pead_columns(self):
        """Register D1: the draft's singular is ambiguous; BOTH, firing if EITHER exceeds."""
        import scripts.e2_delta_composite as E2
        self.assertEqual(tuple(E2.PEAD_COLS), ("z_pead_car", "z_pead_drift"))
        k = _load(KILLS)
        if k is None:
            _SKIPS.append("E2_KILLS.json absent")
            self.skipTest("kills artifact absent")
        cols = k["kills"]["K2_vs_banked_pead"]["columns"]
        self.assertEqual(sorted(cols), ["z_pead_car", "z_pead_drift"])
        got = [v["rho"] for v in cols.values() if v["rho"] is not None]
        self.assertEqual(k["kills"]["K2_vs_banked_pead"]["max_rho"], max(got),
                         "K2 must fire on the MAXIMUM over both columns, not one of them")

    def test_all_three_kills_and_the_control_pass_on_the_banked_run(self):
        k = _load(KILLS)
        if k is None:
            _SKIPS.append("E2_KILLS.json absent")
            self.skipTest("kills artifact absent")
        self.assertTrue(k["all_kills_pass"])
        for name, v in k["kills"].items():
            self.assertTrue(v["pass"], f"{name} fired on the banked run")

    def test_the_survivor_tilt_is_PRINTED_not_assumed(self):
        """§2 requires it. It is material: the kept rows are markedly larger-cap."""
        k = _load(KILLS)
        if k is None:
            _SKIPS.append("E2_KILLS.json absent")
            self.skipTest("kills artifact absent")
        t = k["survivor_tilt"]
        for key in ("median_market_cap_kept", "median_market_cap_dropped",
                    "ratio_kept_over_dropped"):
            self.assertIn(key, t)
        self.assertGreater(t["ratio_kept_over_dropped"], 1.0)

    def test_the_arm_refuses_without_a_passing_kills_artifact(self):
        """Proved WITHOUT running the arm - E-1's lesson from an hour ago, where the obvious
        mutation (flip the pass flag) executed a WITHDRAWN arm and wrote its artifact."""
        if _load(KILLS) is None:
            _SKIPS.append("E2_KILLS.json absent")
            self.skipTest("kills artifact absent")
        raw = io.open(KILLS, "rb").read()
        try:
            os.remove(KILLS)
            r = subprocess.run([sys.executable, "-m", "scripts.e2_delta_composite", "--arm"],
                               cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=600)
        finally:
            io.open(KILLS, "wb").write(raw)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no kills artifact", (r.stdout + r.stderr).lower())

    def test_the_gate_is_conditional_in_the_syntax_tree(self):
        arm = _fn("run_arm")
        found = any(isinstance(s, ast.If) and "all_kills_pass" in ast.dump(s)
                    and "SystemExit" in ast.dump(s) for s in ast.walk(arm))
        self.assertTrue(found, "run_arm's refusal is not conditional on all_kills_pass")


# ------------------------------------------------------------------ the verdict

class TestTheVerdict(unittest.TestCase):

    def test_the_declared_sign_is_POSITIVE_and_only_that_direction_clears(self):
        import scripts.e2_delta_composite as E2
        self.assertEqual(E2.DECLARED_SIGN, "POSITIVE")
        arm = _fn("run_arm")
        src = ast.dump(arm)
        self.assertIn("GtE", src, "the clears test must be one-sided at the declared sign")

    def test_the_banked_verdict_is_NULL_on_both_bases(self):
        a = _load(ARM)
        if a is None:
            _SKIPS.append("E2_ARM.json absent")
            self.skipTest("arm artifact absent")
        self.assertEqual(a["verdict"], "NULL")
        for b, v in a["bases"].items():
            self.assertFalse(v["both_halves_clear"], f"basis {b} cleared unexpectedly")

    def test_a_two_sided_reading_would_ALSO_be_null(self):
        """Forecloses the obvious objection: the declared sign is not what produced the null.

        Basis six's halves DISAGREE IN SIGN, so the both-halves rule fails in either direction;
        basis seven's halves agree in sign and neither reaches the bar's magnitude.
        """
        a = _load(ARM)
        if a is None:
            _SKIPS.append("E2_ARM.json absent")
            self.skipTest("arm artifact absent")
        six = a["bases"]["six"]["cells"]
        self.assertLess(six["early"]["t"] * six["late"]["t"], 0.0,
                        "basis six's halves must disagree in sign for this argument to hold")
        seven = a["bases"]["seven"]["cells"]
        self.assertLess(max(abs(seven["early"]["t"]), abs(seven["late"]["t"])), 2.71,
                        "basis seven must fail on magnitude in either direction")

    def test_the_scope_sentence_travels_with_the_verdict(self):
        """Register D4: the object is a change in RELATIVE standing."""
        a = _load(ARM)
        if a is None:
            _SKIPS.append("E2_ARM.json absent")
            self.skipTest("arm artifact absent")
        self.assertIn("RELATIVE", a["scope"])
        self.assertIn("within", a["scope"].lower())
        self.assertIn("never 'no effect'", a["null_sentence"])

    def test_the_A11_power_line_is_present_on_every_basis(self):
        a = _load(ARM)
        if a is None:
            _SKIPS.append("E2_ARM.json absent")
            self.skipTest("arm artifact absent")
        for b, v in a["bases"].items():
            for k in ("mde_80pct_sd", "mde_50pct_sd", "strongest_raw_anchor_sd"):
                self.assertIn(k, v["power"], f"basis {b} is missing {k}")


# ------------------------------------------------------------------ the register

class TestTheRegister(unittest.TestCase):

    def test_the_register_adopted_the_draft_byte_identically(self):
        if not os.path.isfile(DRAFT):
            _SKIPS.append("the scout's draft is absent")
            self.skipTest("draft absent")
        self.assertTrue(_src(REGISTER).endswith(_src(DRAFT)),
                        "the register's tail is not byte-identical to the scout's draft")

    def test_the_register_commit_carried_markdown_only(self):
        out = subprocess.run(["git", "show", "--name-only", "--format=", "c93ffc8"], cwd=REPO,
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.split()
        if not out:
            _SKIPS.append("register commit c93ffc8 unreachable")
            self.skipTest("commit unreachable")
        self.assertEqual(out, ["PREREG_e2_delta_composite.md"])

    def test_the_register_is_a_strict_ancestor_of_the_script(self):
        reg = subprocess.run(["git", "log", "--format=%H", "-1", "--",
                              "PREREG_e2_delta_composite.md"], cwd=REPO, capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout.strip()
        scr = subprocess.run(["git", "log", "--format=%H", "-1", "--",
                              "scripts/e2_delta_composite.py"], cwd=REPO, capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout.strip()
        if not reg or not scr:
            _SKIPS.append("git history unavailable for the ancestry check")
            self.skipTest("git unavailable")
        self.assertEqual(subprocess.run(["git", "merge-base", "--is-ancestor", reg, scr],
                                        cwd=REPO).returncode, 0)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
