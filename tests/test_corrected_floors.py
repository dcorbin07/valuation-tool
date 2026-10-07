# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 1 -- the X7 placebo sweep calibrated on the corrected universe.

Structural tests run everywhere. Data-dependent ones SKIP LOUDLY: `data/` is gitignored, so a
worktree and a CI runner have none of it, and a guard whose input is absent passes while
checking nothing ("guards that fail open in CI").

**Nothing here imports a module that resolves a data root at IMPORT time.** `served_index_book`
computes `DATA = _data_root(required=True)` at module level, so importing it RAISES on a runner
-- which is how `UNIVERSE-BIAS`'s first suite errored three ways in CI while passing locally.
Constants and call shapes are read off the AST instead, so the checks RUN rather than skip.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

_SKIPS = []


def _skip(name, why):
    _SKIPS.append("%s (%s)" % (name, why))


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _tree(rel):
    return ast.parse(_src(rel))


def _consts(rel):
    out = {}
    for n in _tree(rel).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except (ValueError, SyntaxError):
                pass
    return out


def _bat_commands(rel):
    """A `.bat` with its COMMENTS STRIPPED.

    Both of this class's first two guards fired against a CORRECT launcher, because the
    launcher's own `REM` lines document the rules -- "Costs are MEASURED (no --no-costs)" and
    "placebo.py has no code path to BACKTEST_RESULTS.json". That is the substring-ban family
    this record names repeatedly: a guard that cannot tell code from prose ABOUT code is not
    measuring the file. Stripped, and pinned non-vacuous in BOTH directions below.
    """
    out = []
    for line in _src(rel).splitlines():
        t = line.strip()
        if not t or t.upper().startswith("REM ") or t.upper() == "REM" or t.startswith("::"):
            continue
        out.append(t)
    return "\n".join(out)


def _sweep():
    try:
        import scripts.corrected_floors as CF
        if not os.path.exists(CF.SWEEP):
            return None
        return CF.read_sweep()
    except Exception:                                    # noqa: BLE001
        return None


# =============================================================================================
class TheSweepIsX7sOwnSetupWithOneThingChanged(unittest.TestCase):
    """The whole value of the calibration is that ONLY the universe differs. If the launcher
    quietly changed the seeds, the draw count or the cost treatment, the two floor columns would
    not be comparable and the delta would mean nothing."""

    def test_the_comment_stripper_is_not_vacuous_in_either_direction(self):
        """A stripper returning "" would make every guard below pass by seeing nothing, and one
        returning the file unchanged would re-create the defect. Both directions pinned."""
        cmds = _bat_commands("scripts/placebo_corrected.bat")
        raw = _src("scripts/placebo_corrected.bat")
        self.assertIn("scripts.placebo", cmds, "the stripper dropped the command line itself")
        self.assertIn("--no-costs", raw, "the launcher no longer documents the rule, so this "
                                         "test is no longer exercising the defect it closes")
        self.assertNotIn("--no-costs", cmds, "the stripper is not removing REM prose")
        self.assertNotIn("BACKTEST_RESULTS", cmds)

    def test_the_launcher_runs_the_SHIPPED_placebo_unchanged(self):
        bat = _bat_commands("scripts/placebo_corrected.bat")
        self.assertIn("-m scripts.placebo", bat,
                      "it must call the shipped sweep, not a copy of it (B7)")
        self.assertIn("--seed0 1000", bat, "X7 and session 10 both ran seeds 1000..1099")
        self.assertIn("--n 100", bat, "a p95 over fewer draws is set by its largest value")
        self.assertNotIn("--no-costs", bat, "X7 measured costs; omitting them is a 2nd change")

    def test_the_launcher_writes_its_OWN_artifact_and_touches_nothing_canonical(self):
        bat = _bat_commands("scripts/placebo_corrected.bat")
        self.assertIn("PLACEBO_CORRECTED.json", bat)
        for banned in ("BACKTEST_RESULTS", "PLACEBO_HAC.json", "MA19_RECALIBRATION",
                       "X7_RECONCILE"):
            self.assertNotIn(banned, bat,
                             "the sweep must not write over %s" % banned)

    def test_the_panel_it_sweeps_is_the_SEVEN_theme_corrected_one(self):
        """`UNIVERSE-BIAS` shipped a SIX-theme confounded panel beside the good one, with the
        same byte size and a different hash, and `insider` constant at one distinct value. A
        sweep aimed at the wrong file would calibrate floors for a composite nobody runs."""
        bat = _bat_commands("scripts/placebo_corrected.bat")
        self.assertIn("UNIVERSE_BIAS_PANEL_full.pkl", bat)
        self.assertNotIn("SIXTHEME", bat, "that panel is the CONFOUNDED one")


# =============================================================================================
class TheComparatorIsDerivedAndNotTyped(unittest.TestCase):
    """The canonical floors are a STEP FUNCTION of `N` -- `W-1` re-derived three of them at 247
    -- so a hand-typed comparator column goes stale the next time any lane books a trial. The
    record carried a superseded 1.95pp alpha margin for nine days for exactly this reason."""

    def test_current_floors_CALLS_the_staleness_map(self):
        t = _tree("scripts/corrected_floors.py")
        fn = next((n for n in ast.walk(t)
                   if isinstance(n, ast.FunctionDef) and n.name == "current_floors"), None)
        self.assertIsNotNone(fn)
        dump = ast.dump(fn)
        self.assertIn("mb31_staleness_map", dump,
                      "the map is the one definition of 'what are the floors today'")
        self.assertIn("build", dump, "it must be CALLED, not have its table re-typed")

    def test_no_floor_value_is_a_hard_coded_literal_in_this_item(self):
        """A literal floor here is a second definition of a number that moves."""
        banned = (2.070231, 2.056680, 1.826210, 2.707234, 0.018629, 0.663664, 2.2837, 2.1437)
        for rel in ("scripts/corrected_floors.py", "scripts/corrected_floors_run.py"):
            lits = [n.value for n in ast.walk(_tree(rel))
                    if isinstance(n, ast.Constant) and isinstance(n.value, float)]
            for b in banned:
                self.assertFalse(any(abs(x - b) < 1e-6 for x in lits),
                                 "%s hard-codes the floor %r" % (rel, b))

    def test_the_seven_floors_are_X7s_own_keys_and_tails(self):
        c = _consts("scripts/corrected_floors.py")
        fl = c["FLOORS"]
        self.assertEqual(len(fl), 7, "X7 calibrated seven")
        keys = [r[0] for r in fl]
        for k in ("max_abs_theme_ic_t", "long_short_tstat", "long_short_tstat_nw",
                  "top_decile_alpha", "top_decile_alpha_tstat_nw", "pbo", "deflated_sharpe"):
            self.assertIn(k, keys)
        pbo = next(r for r in fl if r[0] == "pbo")
        self.assertEqual(pbo[2], "p05",
                         "PBO is the ONLY floor read off the low tail -- a LOW PBO is good, so "
                         "reading it off p95 would invert the bar")
        for r in fl:
            if r[0] != "pbo":
                self.assertEqual(r[2], "p95")


# =============================================================================================
class TheHarnessControlIsAGateNotAReport(unittest.TestCase):
    """`MA28`'s `C1` is the precedent: a fidelity control that is merely PRINTED lets a sweep of
    a different object be read as a calibration of this one."""

    def test_the_runner_RAISES_when_the_harness_control_fails(self):
        src = _src("scripts/corrected_floors_run.py")
        self.assertIn("HARNESS CONTROL FAILED", src)
        t = ast.parse(src)
        guarded = False
        for n in ast.walk(t):
            if not isinstance(n, ast.If):
                continue
            body = ast.dump(ast.Module(body=n.body, type_ignores=[]))
            if "HARNESS CONTROL FAILED" not in body:
                continue
            test = ast.dump(n.test)
            self.assertNotIn("Constant(value=False)", test,
                             "the gate is guarded by a constant, so it can never fire")
            self.assertIn("all_exact_excluding_dsr", test)
            guarded = True
        self.assertTrue(guarded, "no `if` guards the abort at all")

    def test_the_DSR_is_excluded_from_the_gate_and_reconciled_instead(self):
        """`sr0` is a direct function of N, so the DSR moves at EVERY N. Demanding it match
        would fail a correct sweep; ignoring the gap would hide a real disagreement. It is
        reconciled arithmetically instead."""
        t = _tree("scripts/corrected_floors.py")
        fn = next(n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == "harness_control")
        self.assertIn("deflated_sharpe", ast.dump(fn))
        self.assertIn("dsr_at_n", _src("scripts/corrected_floors.py"))

    def test_clears_returns_None_rather_than_False_on_a_missing_side(self):
        import scripts.corrected_floors as CF
        self.assertIsNone(CF.clears(None, 1.0, "higher is harder"))
        self.assertIsNone(CF.clears(1.0, None, "higher is harder"))
        self.assertTrue(CF.clears(2.0, 1.0, "higher is harder"))
        self.assertFalse(CF.clears(0.5, 1.0, "higher is harder"))
        # the PBO direction is INVERTED and must not be read the other way
        self.assertTrue(CF.clears(0.1, 0.2, "LOWER is harder"))
        self.assertFalse(CF.clears(0.3, 0.2, "LOWER is harder"))


# =============================================================================================
class APartialSweepIsNotACalibration(unittest.TestCase):
    """The 95th percentile of twenty draws is set by its largest value. Letting a part-way read
    be quoted as a floor is the knife edge `W-28` forbids."""

    def test_the_floor_requires_the_full_draw_count(self):
        c = _consts("scripts/corrected_floors.py")
        self.assertEqual(c["MIN_DRAWS_FOR_A_FLOOR"], 100)

    def test_a_short_sweep_is_reported_PARTIAL_and_exits_non_zero(self):
        src = _src("scripts/corrected_floors_run.py")
        self.assertIn("PARTIAL", src)
        self.assertIn("return 3", src, "a partial read must not exit 0")
        t = ast.parse(src)
        found = False
        for n in ast.walk(t):
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) \
                    and n.targets[0].id == "partial":
                self.assertNotIsInstance(n.value, ast.Constant,
                                         "`partial` is hard-coded, so it can never fire")
                self.assertIn("MIN_DRAWS_FOR_A_FLOOR", ast.dump(n.value))
                found = True
        self.assertTrue(found, "nothing computes `partial`")


# =============================================================================================
class ItAdoptsNothingAndChangesNoPublicPage(unittest.TestCase):
    """`DECISIONS.md`, 2026-10-07: the public-page disclosure is PENDING DON, and no lane
    touches /proof, /methodology or the landing tiles until he rules."""

    def test_nothing_in_this_item_writes_under_valuation_web_or_the_canonical_artifact(self):
        for rel in ("scripts/corrected_floors.py", "scripts/corrected_floors_run.py",
                    "scripts/placebo_corrected.bat"):
            src = _src(rel)
            for banned in ("valuation/web", "valuation\\\\web", "index_book_measured",
                           "methodology.html", "proof.html"):
                self.assertNotIn(banned, src, "%s references %s" % (rel, banned))

    def test_the_only_open_for_writing_is_this_items_own_artifact(self):
        """Read as AST write-mode `open` calls, not as a banned substring: this item
        legitimately READS several artifacts by name, and a substring ban would fire on that
        (the family this record names repeatedly)."""
        for rel in ("scripts/corrected_floors.py", "scripts/corrected_floors_run.py"):
            t = _tree(rel)
            writes = []
            for n in ast.walk(t):
                if not isinstance(n, ast.Call):
                    continue
                nm = getattr(n.func, "id", getattr(n.func, "attr", None))
                if nm != "open":
                    continue
                mode = None
                for kw in n.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = kw.value.value
                if mode is None and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant):
                    mode = n.args[1].value
                if mode and "w" in str(mode):
                    writes.append(ast.dump(n.args[0]) if n.args else "?")
            for w in writes:
                self.assertIn("OUT", w,
                              "%s writes somewhere other than this item's own artifact: %s"
                              % (rel, w))

    def test_the_trial_class_is_declared_as_a_calibration(self):
        src = _src("scripts/corrected_floors_run.py")
        self.assertIn('"trials": 0', src)
        self.assertIn("CALIBRATION", src)
        self.assertIn("adds no degree of freedom", src)


# =============================================================================================
class TheSweepOnDisk(unittest.TestCase):
    """SKIPS LOUDLY without the sweep."""

    @classmethod
    def setUpClass(cls):
        cls.s = _sweep()
        if cls.s is None:
            _skip("sweep", "PLACEBO_CORRECTED.json absent (data/ is gitignored)")

    def test_it_ran_at_the_seeds_and_panel_it_claims(self):
        if self.s is None:
            return
        self.assertEqual(self.s["seeds"], "1000..1099")
        self.assertIn("UNIVERSE_BIAS_PANEL_full.pkl", self.s["panel"])
        self.assertNotIn("SIXTHEME", self.s["panel"])
        self.assertTrue(self.s["costs_measured"])

    def test_it_stamps_the_trial_count_it_ran_at(self):
        """`MA19`: a sweep that does not record its own N cannot be read afterwards -- X7's
        first sweep was silently N=8 on both sides and had to be re-run to move one column."""
        if self.s is None:
            return
        tc = self.s.get("trial_count") or {}
        self.assertIsNotNone(tc.get("n_trials_used"))
        self.assertEqual(tc.get("source"), "RESEARCH_LOG.md (audit M1)")

    def test_every_draw_is_RETAINED_not_just_summarised(self):
        """`RUN_RULES` rule 9, and `MA19` is what happens when draws are not kept: a floor that
        needs re-deriving costs a fresh multi-hour sweep instead of arithmetic."""
        if self.s is None:
            return
        self.assertEqual(len(self.s.get("draws") or []), int(self.s["n_draws"]))
        if self.s["n_draws"]:
            d = self.s["draws"][0]
            for k in ("seed", "long_short_tstat_nw", "deflated_sharpe_detail"):
                self.assertIn(k, d)

    def test_the_real_iteration_reproduces_the_landed_corrected_record(self):
        """The substantive gate, on the real data."""
        if self.s is None:
            return
        import scripts.corrected_floors as CF
        from scripts.corrected_floors_run import landed_corrected
        hc = CF.harness_control(self.s, landed_corrected())
        self.assertTrue(hc["_gate"]["all_exact_excluding_dsr"],
                        "the sweep's real iteration does not reproduce the record: %s"
                        % {k: v for k, v in hc.items() if not k.startswith("_")})
        self.assertGreaterEqual(hc["_gate"]["keys_compared"], 5,
                                "MB21: a perfect comparison over nothing is not a pass")

    def test_the_DSR_gap_is_explained_by_N_alone(self):
        if self.s is None:
            return
        import scripts.corrected_floors as CF
        det = self.s["real"]["deflated_sharpe_detail"]
        denom = CF.implied_denominator(det)
        here = CF.dsr_at_n(det, int(det["n_trials"]), denom)
        self.assertLess(abs(here["dsr"] - float(det["probability"])), 1e-9,
                        "the re-derivation does not reproduce the sweep's own figure, so it "
                        "cannot be used to explain a gap to anything else")
        # and it must MOVE with N, or the explanation is vacuous
        other = CF.dsr_at_n(det, int(det["n_trials"]) - 12, denom)
        self.assertNotEqual(round(other["dsr"], 12), round(here["dsr"], 12))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (data absent) - NOT counted as passes:")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
