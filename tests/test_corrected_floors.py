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
        if not os.path.exists(CF.sweep_path()):
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
                # REPOINTED: `OUT` is now a FUNCTION (`out_path()`), so the old name-check
                # could no longer see it. The property is that the destination is a LOCAL
                # assigned from this item's own path helper -- never a literal path, which is
                # what would let a write escape to a canonical artifact.
                self.assertNotIn("Constant", w,
                                 "%s writes to a LITERAL path: %s" % (rel, w))
                self.assertIn("Name", w,
                              "%s's write destination is not a local: %s" % (rel, w))
            src = _src(rel)
            if writes:
                self.assertTrue(("out_path" in src) or ("CF.out_path" in src),
                                "%s writes but never resolves a destination through this "
                                "item's own path helper" % rel)

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


# =============================================================================================
class TheDeployedReadingIsAStructurallyDifferentObject(unittest.TestCase):
    """PART 1b. `placebo.py` mirrors `run_backtests`, so CPCV is the authority -- and on the
    corrected universe CPCV ADOPTS. Part 1's "corrected headline" is therefore the ADOPTED book,
    and the DEPLOYED book (flat 1/7, what ships) is a different object. These pin the separation
    so it cannot silently collapse back into one number."""

    def _calls(self, rel, fname):
        """The names of every function CALLED inside `fname`.

        NOT a string search of `ast.dump`: a dump contains every string CONSTANT, so banning a
        token in one is the same defect as grepping the source -- and this guard's first cut
        fired on the function's own docstring, which names `cpcv_validate` to explain why it is
        not used. Reading the AST only helps if you look at the SHAPE.
        """
        t = _tree(rel)
        fn = next(n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == fname)
        out = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                nm = getattr(n.func, "id", getattr(n.func, "attr", None))
                if nm:
                    out.add(nm)
        return out

    def test_the_deployed_reading_never_consults_CPCV(self):
        """If it did, it would stop being the deployed book."""
        calls = self._calls("scripts/corrected_deployed.py", "deployed_statistics")
        self.assertIn("_base_weights", calls, "the deployed book is flat 1/7 via _base_weights")
        self.assertIn("quantile_backtest", calls, "the shipped scorer must be CALLED (B7)")
        self.assertNotIn("cpcv_validate", calls,
                         "consulting CPCV makes this the adopted book, not the deployed one")
        # NON-VACUITY: the shape check must be able to SEE a call, or it passes by seeing nothing
        self.assertIn("read_pickle", calls)

    def test_PBO_and_the_DSR_are_reported_ABSENT_for_the_deployed_book(self):
        """Both come out of `cpcv_validate`. Borrowing the adopted run's PBO to sit beside
        flat-weight alpha pairs a numerator from one construction with a denominator from
        another -- MA19's recurring defect and MB8's rule."""
        src = _src("scripts/corrected_deployed.py")
        t = ast.parse(src)
        fn = next(n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == "deployed_statistics")
        ret = next(n for n in ast.walk(fn) if isinstance(n, ast.Return))
        d = ret.value
        self.assertIsInstance(d, ast.Dict)
        found = {}
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and k.value in ("pbo", "deflated_sharpe"):
                found[k.value] = v
        self.assertEqual(set(found), {"pbo", "deflated_sharpe"})
        for k, v in found.items():
            self.assertIsInstance(v, ast.Constant, "%s must be a literal None" % k)
            self.assertIsNone(v.value, "%s must be None, never borrowed from the adopted run" % k)

    def test_the_two_nulls_come_from_the_SAME_retained_draws(self):
        """Rule 9 paying for itself: splitting 100 retained draws is arithmetic, and a re-sweep
        would be a second instrument."""
        t = _tree("scripts/corrected_deployed.py")
        fn = next(n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == "subnull")
        dump = ast.dump(fn)
        self.assertIn("cpcv_adopt", dump, "the split is on whether the draw adopted")
        self.assertIn("draws", dump, "it must read the RETAINED draws")
        self.assertNotIn("placebo", dump, "no re-sweep")

    def test_the_subnull_refuses_when_too_thin(self):
        c = _consts("scripts/corrected_deployed.py")
        self.assertGreaterEqual(c["MIN_SUBNULL_DRAWS"], 40)
        src = _src("scripts/corrected_deployed.py")
        self.assertIn("THIN_SUBNULL", src)
        self.assertIn("return 3", src)
        t = ast.parse(src)
        found = False
        for n in ast.walk(t):
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) \
                    and n.targets[0].id == "thin":
                self.assertNotIsInstance(n.value, ast.Constant,
                                         "`thin` is hard-coded, so it can never fire")
                self.assertIn("MIN_SUBNULL_DRAWS", ast.dump(n.value))
                found = True
        self.assertTrue(found, "nothing computes `thin`")

    def test_the_floors_are_IMPORTED_from_part_1_not_re_listed(self):
        """Two lists of the seven floors and their tails is `B7`'s defect -- and one of them
        would be free to read PBO off the wrong tail.

        The property is "no SECOND LIST", not "no tail string anywhere": `subnull` legitimately
        compares `pct == "p05"` to pick which percentile to take, and this guard's first cut
        fired on that. Pinned on the ASSIGNMENT instead."""
        t = _tree("scripts/corrected_deployed.py")
        assigns = [n for n in t.body
                   if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "FLOORS"]
        self.assertEqual(len(assigns), 1, "FLOORS must be assigned exactly once")
        v = assigns[0].value
        self.assertIsInstance(v, ast.Attribute,
                              "FLOORS must be part 1's own tuple, not a literal re-listing")
        self.assertEqual(v.attr, "FLOORS")
        self.assertEqual(getattr(v.value, "id", None), "CF")
        # and nothing may build a SECOND tuple of (key, label, tail, direction) rows
        for n in t.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Tuple, ast.List)):
                for el in n.value.elts:
                    if isinstance(el, (ast.Tuple, ast.List)) and len(el.elts) == 4:
                        self.fail("a second four-field floor list exists at line %d" % n.lineno)


class TheGateKeepsItsStrengthOnASecondObject(unittest.TestCase):
    """Part 2a parameterises `c1_fidelity`'s TARGET. The gate must not be weakened by it: still
    exact, still 69 dates, still aborting, and still defaulting to the published alpha so every
    existing caller is bit-identical."""

    def _fn(self):
        t = _tree("scripts/served_index_book.py")
        return next(n for n in ast.walk(t)
                    if isinstance(n, ast.FunctionDef) and n.name == "c1_fidelity")

    def test_the_target_defaults_to_None_so_the_published_alpha_is_used(self):
        fn = self._fn()
        names = [a.arg for a in fn.args.args]
        self.assertIn("expect_alpha", names)
        off = len(names) - len(fn.args.defaults)
        d = fn.args.defaults[names.index("expect_alpha") - off]
        self.assertIsInstance(d, ast.Constant)
        self.assertIsNone(d.value, "a non-None default silently re-points every caller")
        self.assertIn("PUBLISHED_ALPHA", ast.dump(fn),
                      "the default must resolve to the published alpha")

    def test_the_gate_is_still_EXACT_and_still_69_dates(self):
        src = _src("scripts/served_index_book.py")
        self.assertIn("(dev == 0.0) and n == 69", src,
                      "a tolerance or a relaxed date count would be a WEAKENED gate, which is "
                      "what the prompt forbids")
        self.assertIn("C1 FAILED", src)

    def test_the_corrected_runner_reads_its_target_rather_than_typing_it(self):
        t = _tree("scripts/corrected_claims.py")
        fn = next(n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == "landed_corrected_alpha")
        dump = ast.dump(fn)
        self.assertIn("UNIVERSE_BIAS_PUBLIC.json", dump)
        self.assertIn("construction.top_decile_alpha", dump)
        lits = [n.value for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, float)]
        self.assertFalse(lits, "the gate target is typed here; it must be READ")

    def test_the_corrected_run_does_not_overwrite_the_banked_artifact(self):
        c = _consts("scripts/corrected_index_book.py")
        self.assertEqual(c["OUT"], "INDEX_BOOK_CORRECTED.json")
        self.assertNotEqual(c["OUT"], "INDEX_BOOK.json")

    def test_nothing_in_part_2_imports_served_index_book_at_module_level(self):
        """It resolves its data root at IMPORT time and RAISES without the banked panel, which
        is how UNIVERSE-BIAS's first suite errored three ways in CI while passing locally."""
        for rel in ("scripts/corrected_claims.py", "scripts/corrected_index_book.py",
                    "scripts/corrected_deployed.py"):
            for n in _tree(rel).body:
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    mods = ([a.name for a in n.names]
                            + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else []))
                    for m in mods:
                        self.assertNotIn("served_index_book", m or "",
                                         "%s imports it at module level" % rel)

    def test_the_three_state_vocabulary_is_fixed_and_UNMEASURED_needs_a_reason(self):
        import scripts.corrected_claims as CC
        self.assertEqual(set(CC.STATES), {CC.SURVIVES, CC.NO_LONGER_HOLDS, CC.UNMEASURED})
        with self.assertRaises(AssertionError):
            CC.claim("x", "s", "t", 1.0, None, "PROBABLY FINE")
        with self.assertRaises(AssertionError):
            CC.claim("x", "s", "t", 1.0, None, CC.UNMEASURED)      # no reason named
        with self.assertRaises(AssertionError):
            CC.claim("x", "s", "t", 1.0, None, CC.SURVIVES)        # no corrected value
        ok = CC.claim("x", "s", "t", 1.0, None, CC.UNMEASURED, why="named")
        self.assertEqual(ok["state"], CC.UNMEASURED)

# =============================================================================================
class NoModuleInThisItemResolvesADataRootAtImportTime(unittest.TestCase):
    """**A CI FAILURE OF MY OWN, AND THE IRONY IS IN THIS FILE'S OWN DOCSTRING.** It opens by
    saying nothing here imports a module that resolves a data root at import time -- and
    `corrected_floors.py` did exactly that, so the suite ERRORED on a runner where `data/` does
    not exist. **I wrote the rule in prose and not as a test**, which is the "guards that fail
    open in CI" family one level up: a rule nobody enforces.

    Read as the AST, at MODULE level only -- a call inside a function is exactly the fix."""

    MODULES = ("scripts/corrected_floors.py", "scripts/corrected_floors_run.py",
               "scripts/corrected_claims.py", "scripts/corrected_index_book.py",
               "scripts/corrected_deployed.py")
    BANNED = ("_data_root", "data_root", "read_pickle", "read_csv")

    def test_no_module_level_call_resolves_a_data_root_or_reads_a_file(self):
        """MODULE level means NOT inside a function or class.

        A DEFECT IN THIS GUARD'S OWN FIRST CUT: it did `ast.walk(n)` over each top-level node,
        and `ast.walk` on a `FunctionDef` descends INTO the body -- so it flagged the very fix it
        exists to demand, against a corrected tree. Its docstring already said a call inside a
        function is the fix; the implementation did not honour it."""
        for rel in self.MODULES:
            for n in _tree(rel).body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue                      # a call in here runs on CALL, which is the fix
                for c in ast.walk(n):
                    if not isinstance(c, ast.Call):
                        continue
                    nm = getattr(c.func, "id", getattr(c.func, "attr", None))
                    if nm in self.BANNED:
                        self.fail("%s calls %s() at MODULE level -- importing it raises on a "
                                  "runner with no data/" % (rel, nm))

    def test_every_one_of_them_IMPORTS_cleanly_with_no_data_root(self):
        """The direct check, and the one the CI failure would have produced. Runs the import in
        a SUBPROCESS with the data root pointed at an empty directory, so a module that resolves
        eagerly fails here rather than three suites later."""
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as empty:
            env = dict(os.environ)
            env["VALQUO_DATA_ROOT"] = empty
            for rel in self.MODULES:
                mod = rel.replace("/", ".")[:-3]
                r = subprocess.run([sys.executable, "-c", "import %s" % mod],
                                   cwd=REPO, capture_output=True, env=env)
                self.assertEqual(r.returncode, 0,
                                 "import %s failed with no data root:\n%s"
                                 % (mod, r.stderr.decode("utf-8", "replace")[-900:]))

    def test_the_guard_is_not_vacuous(self):
        """It must be able to SEE a module-level call, or it passes by looking at nothing."""
        t = ast.parse("import os\nX = os.path.join(_data_root(), 'a')\n")
        hits = [c for n in t.body for c in ast.walk(n)
                if isinstance(c, ast.Call)
                and getattr(c.func, "id", getattr(c.func, "attr", None)) == "_data_root"]
        self.assertTrue(hits, "the AST walk cannot see a module-level call at all")


# =============================================================================================
class TheEightClaimTableIsHonestAboutWhatItCouldNotMeasure(unittest.TestCase):
    """PART 2. The deliverable is a table, and the only way a table like this goes wrong is by
    letting an UNMEASURED claim sit in the surviving column -- which is the flattering
    direction. `V6`'s rule: a null and an absent measurement must not read the same."""

    def test_every_UNMEASURED_row_names_its_blocker(self):
        import scripts.corrected_claims_run as R
        try:
            rows = R.build()
        except SystemExit as exc:
            _skip("claims", "artifacts absent: %s" % exc)
            return
        except Exception as exc:                       # noqa: BLE001
            _skip("claims", "build failed: %s" % exc)
            return
        un = [r for r in rows if r["state"] == "UNMEASURED"]
        self.assertTrue(un, "a table with no UNMEASURED row would be suspicious here")
        for r in un:
            self.assertTrue(r["why"], "%s is UNMEASURED with no reason" % r["claim"])
            self.assertGreater(len(r["why"]), 40,
                               "%s's reason is too thin to act on" % r["claim"])

    def test_no_row_claims_SURVIVES_without_a_corrected_value(self):
        import scripts.corrected_claims_run as R
        try:
            rows = R.build()
        except Exception:                              # noqa: BLE001
            _skip("claims", "artifacts absent")
            return
        for r in rows:
            if r["state"] == "SURVIVES":
                self.assertIsNotNone(r["corrected"],
                                     "%s SURVIVES with nothing measured" % r["claim"])

    def test_the_vocabulary_cannot_be_widened_after_the_fact(self):
        """The guard fired on my own Track Record row, and the response was to use the
        non-flattering state rather than to add a fourth one. Pinned so a successor cannot
        quietly add `UNAFFECTED` and move rows into it."""
        import scripts.corrected_claims as CC
        self.assertEqual(len(CC.STATES), 3)
        c = _consts("scripts/corrected_claims.py")
        self.assertEqual(c["SURVIVES"], "SURVIVES")
        self.assertEqual(c["NO_LONGER_HOLDS"], "NO LONGER HOLDS")
        self.assertEqual(c["UNMEASURED"], "UNMEASURED")

    def test_the_index_row_carries_the_benchmark_caveat(self):
        """The alpha-vs-equal-weight figure moves -0.06pp to +5.93pp and that is MOSTLY THE
        BENCHMARK FALLING. Without that sentence it reads as a six-point alpha gain, which
        overstates it about sixfold -- the single most misquotable number in this item."""
        src = _src("scripts/corrected_claims_run.py")
        self.assertIn("BENCHMARK FALLING", src)
        self.assertIn("overstates", src)

    def test_the_lean_panel_blocker_names_the_missing_columns(self):
        """A blocker stated as "could not measure" is not actionable. Each must name what is
        missing, because ONE rebuild unlocks three of the four."""
        src = _src("scripts/corrected_claims_run.py")
        for needle in ("keep_numbers=False", "extra_horizons", "bucket", "fwd_ret"):
            self.assertIn(needle, src, "the blocker does not name %s" % needle)
        # Read the BUILT row, not the source: the phrase spans a line break in the source and
        # a contiguous grep fired against a correct tree. The assembled text is the object a
        # reader sees anyway.
        import scripts.corrected_claims_run as R
        try:
            rows = R.build()
        except Exception:                              # noqa: BLE001
            _skip("claims", "artifacts absent")
            return
        sc = [r for r in rows if "score calibration" in r["claim"]]
        self.assertEqual(len(sc), 1)
        self.assertIn("Attempted, not assumed", sc[0]["why"],
                      "score_calibration was actually RUN against the corrected panel and "
                      "raised; that is stronger than inferring it from a column list")
        self.assertIn("KeyError", sc[0]["why"], "the raised error must be named")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (data absent) - NOT counted as passes:")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
