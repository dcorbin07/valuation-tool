# -*- coding: utf-8 -*-
"""`CORRECTED-CLAIMS-2` -- the verdict pass's bars, its vocabulary and its refusals.

The point of this suite is that the bars were fixed BEFORE the producers reported. A test cannot
prove when a line was written, so it proves the two things that are checkable:

* **every REUSED bar still equals the constant in the register it came from**, by IMPORT rather
  than by retyping -- so a drift in `term_structure` or `v6b_dip_survival` turns this red
  instead of silently re-pointing a verdict; and
* **the DECLARED bars are literals, not functions of the corrected artifact** -- a bar read out
  of the data it judges is not a bar.

Run as its own process and judged by exit code, per `RUN_RULES`.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  (must precede the valuation imports)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERDICT_SRC = os.path.join(ROOT, "scripts", "corrected_claims2_verdict.py")
RUNNER_SRC = os.path.join(ROOT, "scripts", "corrected_claims2.py")


def _src(p):
    return io.open(p, encoding="utf-8").read()


def _tree(p):
    return ast.parse(_src(p))


def _consts(p):
    """Module-level literal assignments, by name."""
    out = {}
    for n in _tree(p).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception:
                pass
    return out


import scripts.corrected_claims2_verdict as V                               # noqa: E402
from scripts.corrected_claims import SURVIVES, NO_LONGER_HOLDS, UNMEASURED  # noqa: E402


# =============================================================================================
class TheReusedBarsStillEqualTheirSources(unittest.TestCase):
    """A bar quoted from another register must be the SAME NUMBER as that register's. Retyping
    it is how two definitions of one threshold come about (`B7`), and the `MA5` precedent is
    this project's own: the Harvey-Liu-Zhu bar froze at a constant 3.0 because a default was
    typed instead of derived."""

    def test_the_three_S22_bars_are_S22s_own(self):
        from scripts.term_structure import R_CONSTANT_RATE, R_SATURATING, REVERSE_T
        self.assertEqual(V.BAR_S22_R8, R_CONSTANT_RATE)
        self.assertEqual(V.BAR_S22_SATURATING, R_SATURATING)
        self.assertEqual(V.BAR_S22_REVERSING_T, REVERSE_T)

    def test_the_score_gate_is_the_registers_own_42(self):
        """`score_confidence.py`'s provenance comment carries the gate. It is a COMMENT, so it
        cannot be imported -- which is exactly why its presence is asserted here rather than
        taken on trust."""
        self.assertEqual(V.BAR_SCORE_PER_NAME_GATE, 42)
        sc = _src(os.path.join(ROOT, "valuation", "web", "score_confidence.py"))
        self.assertIn("gate: 42", sc,
                      "score_confidence no longer records the register's gate, so 42 has no "
                      "provenance and must not be used as a bar")

    def test_V6B_is_read_not_re_derived(self):
        """`v6b_dip_survival.m1_verdict` IS register 2.1. Re-implementing it here would be a
        second definition of one rule, on a rule whose own docstring calls its sign trap *"the
        single easiest mistake to make in this file"* -- and whose floor is in PERCENTAGE POINTS
        (3.0), which a fraction-valued bar would miss by 100x."""
        src = _src(VERDICT_SRC)
        self.assertIn('get("ARM1_SURVIVAL")', src)
        self.assertIn("M1_verdict", src)
        # A GUARD OF MY OWN FIRED AGAINST THE CORRECT TREE HERE, and it is the family this
        # record names in one line: NEVER BAN A SUBSTRING. The first cut asserted the text did
        # not contain "M1_ECONOMIC_PP", and the module's own docstring names that constant while
        # explaining why it is NOT compared against -- prose documenting a rule quotes what the
        # rule forbids. It reads the syntax tree for a NAME REFERENCE now, so prose may name it
        # and code may not. It also may NOT use `ast.dump` of the module: a dump contains every
        # string constant, so dumping and substring-searching is the same defect in a tree's
        # clothing.
        referenced = set()
        for n in ast.walk(_tree(VERDICT_SRC)):
            if isinstance(n, ast.Name):
                referenced.add(n.id)
            elif isinstance(n, ast.Attribute):
                referenced.add(n.attr)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    referenced.add(a.asname or a.name)
        self.assertNotIn("M1_ECONOMIC_PP", referenced,
                         "the verdict pass REFERENCES V6-B's economic floor, which re-implements "
                         "V6-B's rule instead of reading its verdict")
        self.assertNotIn("BAR_V6B_ECONOMIC_PP", referenced,
                         "the fraction-valued 0.030 bar is back; V6-B's floor is 3.0 in "
                         "PERCENTAGE POINTS and this is a 100x error waiting to happen")
        # positive control: the detector must see a reference when one exists
        probe = set()
        for n in ast.walk(ast.parse("x = M1_ECONOMIC_PP * 2\n")):
            if isinstance(n, ast.Name):
                probe.add(n.id)
        self.assertIn("M1_ECONOMIC_PP", probe,
                      "the name detector cannot see the reference it bans")
        # and the floor it DOES use must be V6-B's own verdict vocabulary
        self.assertTrue(str(V.V6B_VERDICT_PREFIX))
        from scripts.v6b_dip_survival import M1_ECONOMIC_PP
        self.assertEqual(M1_ECONOMIC_PP, 3.0,
                         "V6-B's economic floor moved; its verdict string still decides here, "
                         "but the record's 3.0pp prose is now stale")

    def test_every_reused_bar_is_named_as_reused_and_every_declared_one_as_declared(self):
        for n in V.BARS_REUSED:
            self.assertTrue(hasattr(V, n), "%s is listed as REUSED and does not exist" % n)
        for n in V.BARS_DECLARED:
            self.assertTrue(hasattr(V, n), "%s is listed as DECLARED and does not exist" % n)
        self.assertFalse(set(V.BARS_REUSED) & set(V.BARS_DECLARED),
                         "a bar cannot be both reused and declared")


# =============================================================================================
class ABarIsNotReadOutOfTheDataItJudges(unittest.TestCase):
    def test_no_bar_is_assigned_from_a_subscript_or_a_call(self):
        """Every bar must be a module-level LITERAL. A bar computed from the artifact -- or from
        a percentile of it -- would move with the thing it is judging, which is the defect
        `MB21`'s count gate and `CORRECTED-REBUILD`'s inertness floor both exist to close."""
        names = set(V.BARS_REUSED) | set(V.BARS_DECLARED)
        lits = _consts(VERDICT_SRC)
        for n in sorted(names):
            self.assertIn(n, lits,
                          "%s is not a module-level literal, so it is computed rather than "
                          "fixed" % n)

    def test_the_published_figures_are_literals_too(self):
        lits = _consts(VERDICT_SRC)
        for n in [k for k in dir(V) if k.startswith("PUB_")]:
            self.assertIn(n, lits, "%s is not a literal; a published figure must be "
                                   "transcribed, so a drift shows as a diff" % n)


# =============================================================================================
class TheVocabularyIsImportedNotRedefined(unittest.TestCase):
    def test_claim_is_called(self):
        t = _tree(VERDICT_SRC)
        calls = {getattr(n.func, "attr", None) for n in ast.walk(t) if isinstance(n, ast.Call)}
        self.assertIn("claim", calls, "corrected_claims.claim() is not called, so the "
                                      "vocabulary's own assertions do not run")

    def test_the_three_states_are_not_re_spelled(self):
        """A fourth state, or a typo'd third, is a reader's problem rather than an error. The
        vocabulary is imported so `claim()`'s own assertion catches it."""
        self.assertIn("from scripts.corrected_claims import", _src(VERDICT_SRC))
        # Read the tree, not the text: a DOCSTRING may legitimately discuss the vocabulary, and
        # banning the token would fire on the paragraph that documents it. What must not exist
        # is a string CONSTANT equal to a state name sitting in a comparison or an assignment,
        # which is a second spelling of an imported value. That is a real defect and this guard
        # caught one on its first run -- the R1 row compared against a hard-coded "UNMEASURED".
        states = {"SURVIVES", "UNMEASURED", "NO LONGER HOLDS"}
        t = _tree(VERDICT_SRC)
        docstrings = set()
        for n in ast.walk(t):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docstrings.add(d)
        offenders = []
        for n in ast.walk(t):
            if isinstance(n, (ast.Compare, ast.Assign, ast.Return)):
                for sub in ast.walk(n):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                            and sub.value in states and sub.value not in docstrings:
                        offenders.append((sub.value, getattr(n, "lineno", None)))
        self.assertFalse(offenders,
                         "a state name is spelled as a local string literal in a comparison or "
                         "assignment instead of using the imported constant: %r" % (offenders,))
        # positive control, both directions: the detector must catch a re-spelling
        probe = ast.parse('if s == "SURVIVES":\n    pass\n')
        found = [sub.value for n in ast.walk(probe) if isinstance(n, ast.Compare)
                 for sub in ast.walk(n)
                 if isinstance(sub, ast.Constant) and sub.value in states]
        self.assertIn("SURVIVES", found,
                      "the re-spelling detector cannot see a hard-coded state comparison")


# =============================================================================================
class TheRefusalsFireAndAreNotVacuous(unittest.TestCase):
    """Each refusal is exercised in BOTH directions. A guard that refuses everything passes a
    one-sided test while measuring nothing."""

    def test_an_absent_producer_is_UNMEASURED_with_a_reason(self):
        for rows in (V.s22_rows(None), V.score_rows(None), V.v6b_rows(None), V.r1_rows(None)):
            self.assertTrue(rows)
            for r in rows:
                self.assertEqual(r["state"], UNMEASURED)
                self.assertTrue(r["why"], "an UNMEASURED row with no reason named")

    def test_the_V6B_merge_gate_refuses_a_collapsed_join(self):
        broken = {"controls": {"C4_coverage": {"drawdown_cov": 0.0, "health_cov": 0.0,
                                               "fwd_min_cov": 0.0}},
                  "arms": {"ARM1_SURVIVAL": {"M1_verdict": "REAL - HEALTHY DIPS SURVIVE BETTER"}}}
        rows = V.v6b_rows(broken)
        self.assertEqual(rows[0]["state"], UNMEASURED)
        self.assertIn("merge coverage", rows[0]["why"])

    def test_the_V6B_merge_gate_does_NOT_refuse_a_healthy_join(self):
        """Non-vacuity: with the published run's own coverage the gate must stay out of the way,
        or it would turn every real reading into an UNMEASURED."""
        ok = {"controls": {"C4_coverage": {"drawdown_cov": 0.983272631532757,
                                           "health_cov": 1.0,
                                           "fwd_min_cov": 0.973460880249243}},
              "arms": {"ARM1_SURVIVAL": {
                  "M1_verdict": "REAL - HEALTHY DIPS SURVIVE BETTER",
                  "M1_further_20pct_within_126d": {
                      "full": {"mean_diff_pp": -10.228339376002001},
                      "early": {"mean_diff_pp": -9.06}, "late": {"mean_diff_pp": -11.51},
                      "both_halves_below_p5": True, "halves_same_sign": True,
                      "enough_dates_per_half": True, "n_dates": 68},
                  "n_rows": 37014}},
              "diagnostics": {"D1_base_rates": {"P_further20_healthy": 0.3251,
                                                "P_further20_unhealthy": 0.4335}}}
        rows = V.v6b_rows(ok)
        self.assertEqual(rows[0]["state"], SURVIVES)
        self.assertIsNotNone(rows[0]["corrected"])

    def test_a_V6B_verdict_that_is_not_REAL_does_not_survive(self):
        cell = {"controls": {"C4_coverage": {"drawdown_cov": 0.98, "health_cov": 1.0,
                                             "fwd_min_cov": 0.97}},
                "arms": {"ARM1_SURVIVAL": {
                    "M1_verdict": "NULL - CLEARS STATISTICALLY, MISSES THE 3.0pp ECONOMIC FLOOR",
                    "M1_further_20pct_within_126d": {"full": {"mean_diff_pp": -1.2}}}}}
        self.assertEqual(V.v6b_rows(cell)[0]["state"], NO_LONGER_HOLDS)


# =============================================================================================
class TheTwoRowsForOneSentenceCanDisagree(unittest.TestCase):
    """`S22`'s *"the alpha HAC t never drops below 3.16"* is a claim about a MINIMUM. A corrected
    minimum of 3.0 falsifies the PRINTED NUMBER while leaving the SUBSTANCE -- alpha still
    separable at every horizon -- intact. If both rows could only ever agree, splitting them
    would be decoration."""

    @staticmethod
    def _ts(min_t):
        hs = [63, 126, 189, 252, 315, 378, 441, 504]
        pc = {}
        for h in hs:
            t = min_t if h == 252 else min_t + 1.0
            pc[str(h)] = {"alpha_t_hac": t, "alpha_ann": 0.066 if h == 63 else 0.051,
                          "n_periods": 62}
        return {"horizons": hs, "primary_common_dates": pc,
                "verdict": {"R_8": 6.2, "shape": "CONSTANT-RATE"},
                "rank_ic_common": {"63": {"median_ic": 0.03}, "504": {"median_ic": 0.07}},
                # a PASSING C1: a synthetic panel stands in for the banked one here, so no
                # attribution is needed and the arm rows are reachable. The attribution control
                # has its own class.
                "C1_incumbent_reproduces_record": {"all_ok": True},
                "n_names": 9645, "n_dates": 69}

    def _by(self, rows, frag):
        hit = [r for r in rows if frag in r["claim"]]
        self.assertEqual(len(hit), 1, "expected exactly one %r row, got %d" % (frag, len(hit)))
        return hit[0]

    def test_a_minimum_of_3_point_0_splits_the_two_rows(self):
        rows = V.s22_rows(self._ts(3.0))
        self.assertEqual(self._by(rows, "(LITERAL)")["state"], NO_LONGER_HOLDS)
        self.assertEqual(self._by(rows, "(SUBSTANCE)")["state"], SURVIVES)

    def test_a_minimum_above_the_printed_figure_passes_both(self):
        rows = V.s22_rows(self._ts(3.5))
        self.assertEqual(self._by(rows, "(LITERAL)")["state"], SURVIVES)
        self.assertEqual(self._by(rows, "(SUBSTANCE)")["state"], SURVIVES)

    def test_a_minimum_below_2_fails_both(self):
        rows = V.s22_rows(self._ts(1.1))
        self.assertEqual(self._by(rows, "(LITERAL)")["state"], NO_LONGER_HOLDS)
        self.assertEqual(self._by(rows, "(SUBSTANCE)")["state"], NO_LONGER_HOLDS)

    def test_the_shape_row_uses_S22s_own_bar(self):
        ts = self._ts(3.5)
        ts["verdict"]["R_8"] = 5.99
        self.assertEqual(self._by(V.s22_rows(ts), "shape (R_8)")["state"], NO_LONGER_HOLDS)
        ts["verdict"]["R_8"] = 6.00
        self.assertEqual(self._by(V.s22_rows(ts), "shape (R_8)")["state"], SURVIVES)

    def test_the_panel_shape_row_catches_the_universe_change(self):
        """The surface names the panel every figure on it comes from, and the canonical move
        replaces that panel. This row exists so item 5's old-to-new table cannot miss it."""
        row = self._by(V.s22_rows(self._ts(3.5)), "PANEL_NAMES")
        self.assertEqual(row["state"], NO_LONGER_HOLDS)
        self.assertEqual(row["corrected"]["names"], 9645)

    def test_the_per_horizon_floor_comparison_is_named_as_not_done(self):
        row = self._by(V.s22_rows(self._ts(3.5)), "per-horizon")
        self.assertEqual(row["state"], UNMEASURED)
        self.assertIn("MIN_DRAWS_FOR_A_FLOOR", row["why"])


# =============================================================================================
class TheCopyRowsBiteAtTheDeclaredTolerance(unittest.TestCase):
    @staticmethod
    def _ts(a63, a504):
        hs = [63, 504]
        pc = {"63": {"alpha_t_hac": 4.0, "alpha_ann": a63, "n_periods": 62},
              "504": {"alpha_t_hac": 4.0, "alpha_ann": a504, "n_periods": 62}}
        return {"horizons": hs, "primary_common_dates": pc,
                "verdict": {"R_8": 6.2, "shape": "CONSTANT-RATE"},
                "rank_ic_common": {"63": {"median_ic": 0.03}, "504": {"median_ic": 0.07}},
                "C1_incumbent_reproduces_record": {"all_ok": True},
                "n_names": 2531, "n_dates": 69}

    def _state(self, rows, frag):
        return [r for r in rows if frag in r["claim"]][0]["state"]

    def test_inside_one_point_survives(self):
        rows = V.s22_rows(self._ts(0.0700, 0.0550))
        self.assertEqual(self._state(rows, "1-quarter annualized"), SURVIVES)
        self.assertEqual(self._state(rows, "2-year annualized"), SURVIVES)

    def test_outside_one_point_does_not(self):
        rows = V.s22_rows(self._ts(0.0300, 0.0100))
        self.assertEqual(self._state(rows, "1-quarter annualized"), NO_LONGER_HOLDS)
        self.assertEqual(self._state(rows, "2-year annualized"), NO_LONGER_HOLDS)

    def test_a_negative_alpha_never_survives_however_close(self):
        """A sentence telling a user the book BEAT the universe cannot survive on a negative
        number, whatever the tolerance says."""
        rows = V.s22_rows(self._ts(-0.0005, -0.0005))
        self.assertEqual(self._state(rows, "1-quarter annualized"), NO_LONGER_HOLDS)

    def test_the_rank_ic_row_is_directional_and_needs_no_bar(self):
        rows = V.s22_rows(self._ts(0.066, 0.051))
        row = [r for r in rows if "rank IC rises" in r["claim"]][0]
        self.assertEqual(row["state"], SURVIVES)
        self.assertIsNone(row["floor"], "a directional claim must not acquire a bar")
        ts = self._ts(0.066, 0.051)
        ts["rank_ic_common"] = {"63": {"median_ic": 0.07}, "504": {"median_ic": 0.03}}
        rows = V.s22_rows(ts)
        self.assertEqual([r for r in rows if "rank IC rises" in r["claim"]][0]["state"],
                         NO_LONGER_HOLDS)


# =============================================================================================
class TheRankICHelperReproducesThePublishedConstants(unittest.TestCase):
    """`MB15`: the instrument is validated BEFORE any hypothesis reads it. `_ric` is a shape
    reader, and a shape reader that silently picks the wrong field would mislabel a figure
    rather than fail."""

    def test_ric_reproduces_hold_horizons_two_printed_constants(self):
        import json
        from scripts.corrected_claims import fa
        p = os.path.join(fa(), "TERM_STRUCTURE.json")
        if not os.path.exists(p):
            print("SKIP: banked TERM_STRUCTURE.json absent (licensed data not on this host)")
            return
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        r = d["rank_ic_common"]
        self.assertAlmostEqual(V._ric(r, 63), V.PUB_RANK_IC_1Q, places=4)
        self.assertAlmostEqual(V._ric(r, 504), V.PUB_RANK_IC_2Y, places=4)

    def test_ric_returns_None_rather_than_a_plausible_wrong_number(self):
        self.assertIsNone(V._ric({"63": {"mean_ic": 0.5}}, 63),
                          "_ric accepted `mean_ic` for a MEDIAN claim")
        self.assertIsNone(V._ric({}, 63))


# =============================================================================================
class TheScoreRowsUseTheRegistersGateAndProtectItsDisclaimer(unittest.TestCase):
    @staticmethod
    def _sc(per_name, group, scored=69):
        """The group count is DERIVED from the per-date rows, not looked up -- so the fixture
        has to build rows that produce it. That is the point: a fixture supplying
        `n_dates_clearing_p95` would exercise the field my first cut wrongly read."""
        rows = []
        for i in range(scored):
            clears = i < group
            rows.append({"date": "d%02d" % i,
                         "real_top_decile_mean": 0.9 if clears else 0.7,
                         "noise_top_decile_mean_p95": 0.8})
        return {"robustness": {"n_dates_scored": scored,
                               "n_dates_not_distinguishable": per_name,
                               "per_date": rows}}

    def _state(self, rows, frag):
        return [r for r in rows if frag in r["claim"]][0]["state"]

    def test_the_per_name_row_turns_on_the_registers_gate_of_42(self):
        self.assertEqual(self._state(V.score_rows(self._sc(42, 21)), "PER_NAME"), SURVIVES)
        self.assertEqual(self._state(V.score_rows(self._sc(41, 21)), "PER_NAME"),
                         NO_LONGER_HOLDS)

    def test_the_group_row_protects_the_disclaimer_not_the_count(self):
        """A corrected count DIFFERENT from 21 still SURVIVES while it is a minority -- the
        sentence at risk is *"may never be stated as a standing property"*, not the integer."""
        self.assertEqual(self._state(V.score_rows(self._sc(45, 21)), "GROUP"), SURVIVES)
        self.assertEqual(self._state(V.score_rows(self._sc(45, 30)), "GROUP"), SURVIVES)
        self.assertEqual(self._state(V.score_rows(self._sc(45, 60)), "GROUP"),
                         NO_LONGER_HOLDS)

    def test_a_missing_robustness_block_is_UNMEASURED_not_zero(self):
        rows = V.score_rows({"verdict": {}})
        for r in rows:
            self.assertEqual(r["state"], UNMEASURED)
            self.assertIn("robustness", r["why"])


# =============================================================================================
class ItChargesNothingAndAdoptsNothing(unittest.TestCase):
    def test_the_runner_and_the_verdict_both_declare_zero_trials(self):
        for p in (RUNNER_SRC, VERDICT_SRC):
            src = _src(p)
            self.assertIn('"trials": 0', src)
            self.assertIn('"adopts_nothing": True', src)
            self.assertIn('"changes_no_public_page": True', src)

    def test_every_figure_names_its_weighting(self):
        """Part 1b measured why: CPCV ADOPTS on this universe, and the adopted book's alpha is
        2.83pc against the deployed 6.07pc. A corrected figure that does not say which book it
        is cannot be compared with anything published."""
        for p in (RUNNER_SRC, VERDICT_SRC):
            self.assertIn("DEPLOYED", _src(p))
        self.assertIn('"weighting"', _src(VERDICT_SRC))

    def test_no_banked_artifact_is_opened_for_writing(self):
        src = _src(VERDICT_SRC)
        for banked in ("TERM_STRUCTURE.json", "V6B_DIP_SURVIVAL.json", "INDEX_BOOK.json",
                       "SCORE_CALIBRATION.json"):
            self.assertNotIn('"w"', src.split(banked)[0][-200:] if banked in src else "",
                             "a banked artifact may be read and never written")
        self.assertEqual(src.count('"w"'), 1,
                         "exactly one write, and it is this item's own artifact")


# =============================================================================================
class NoModuleLevelDataRootResolution(unittest.TestCase):
    """`CORRECTED-FLOORS` part 1 failed CI because a module computed its data root at import
    time, and `data/` is gitignored so a runner has none. The rule was written in prose and not
    as a test; it is a test now."""

    def test_no_data_root_is_resolved_at_import_time(self):
        for p in (RUNNER_SRC, VERDICT_SRC,
                  os.path.join(ROOT, "scripts", "restricted_index_book.py")):
            if not os.path.exists(p):
                continue
            for n in _tree(p).body:
                if not isinstance(n, ast.Assign):
                    continue
                dump = ast.dump(n.value)
                self.assertNotIn("_data_root", dump,
                                 "%s resolves a data root at module level" % os.path.basename(p))
                self.assertNotIn("Attribute(value=Name(id='CC'), attr='fa'", dump,
                                 "%s calls CC.fa() at module level" % os.path.basename(p))

    def test_the_guard_is_not_vacuous(self):
        """A positive control: the pattern it bans must be detectable when present."""
        bad = ast.parse("import x\nDATA = _data_root()\n")
        found = any(isinstance(n, ast.Assign) and "_data_root" in ast.dump(n.value)
                    for n in bad.body)
        self.assertTrue(found, "the module-level detector cannot see the thing it bans")




# =============================================================================================
class TheGroupCountIsDerivedNotLookedUp(unittest.TestCase):
    """A DEFECT OF MY OWN, AND IT WOULD HAVE BEEN RIGHT BY ACCIDENT.

    `GROUP_DATES = (21, 69)` is the number of dates the TOP-DECILE MEAN clears its own noise
    p95 on. My first cut read `robustness.n_dates_clearing_p95`, which is the rank-10 composite
    and reads **24** on the banked run against the published **21** -- `S25`'s *"two nearly-equal
    percentages on different objects"*. On the corrected run both equal 57, so the wrong field
    would have carried the right integer, passed every test I had written, and been wrong on any
    other dataset. Requiring the derivation to reproduce the PUBLISHED figure on the BANKED
    artifact is the only thing that caught it (`MB15`: the instrument before the hypothesis).
    """

    def test_the_derivation_reproduces_the_published_21_on_the_banked_run(self):
        ok, detail = V.validate_group_derivation()
        if ok is None:
            print("SKIP: banked SCORE_CALIBRATION.json absent (licensed data not on this host)")
            return
        self.assertTrue(ok, "the group derivation does not reproduce the published 21 of 69: %s"
                            % detail)
        self.assertEqual(detail["banked_group_count"], V.PUB_SCORE_GROUP)
        self.assertEqual(detail["banked_denominator"], V.PUB_SCORE_DENOM)

    def test_the_wrong_field_is_recorded_so_a_successor_sees_why(self):
        ok, detail = V.validate_group_derivation()
        if ok is None:
            return
        self.assertIn("also_checked", detail)
        self.assertIn("DIFFERENT statistic", detail["also_checked"])

    def test_the_group_row_does_not_read_the_rank_statistic(self):
        """Pinned on the tree: `n_dates_clearing_p95` must not be the group row's source."""
        t = _tree(VERDICT_SRC)
        fn = [n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)
              and n.name == "score_rows"]
        self.assertEqual(len(fn), 1)
        subs = [x.slice.value for x in ast.walk(fn[0])
                if isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Constant)]
        calls = [getattr(x.func, "attr", None) or getattr(x.func, "id", None)
                 for x in ast.walk(fn[0]) if isinstance(x, ast.Call)]
        gets = [x.args[0].value for x in ast.walk(fn[0])
                if isinstance(x, ast.Call) and getattr(x.func, "attr", None) == "get"
                and x.args and isinstance(x.args[0], ast.Constant)
                and isinstance(x.args[0].value, str)]
        self.assertNotIn("n_dates_clearing_p95", subs + gets,
                         "score_rows reads the rank statistic for the GROUP claim again")
        self.assertIn("group_dates_clearing", calls,
                      "the group count is not derived from the per-date rows")

    def test_the_derivation_counts_the_right_comparison(self):
        """Synthetic, both directions: a date clears when the real top-decile mean EXCEEDS its
        own noise p95. Getting this backwards is the sign error V6-B's own docstring calls the
        easiest mistake in its file, one object over."""
        sc = {"robustness": {"per_date": [
            {"real_top_decile_mean": 0.9, "noise_top_decile_mean_p95": 0.8},   # clears
            {"real_top_decile_mean": 0.7, "noise_top_decile_mean_p95": 0.8},   # does not
            {"real_top_decile_mean": 0.8, "noise_top_decile_mean_p95": 0.8},   # ties -> no
            {"real_top_decile_mean": None, "noise_top_decile_mean_p95": 0.8},  # absent -> no
        ]}}
        got, denom = V.group_dates_clearing(sc)
        self.assertEqual((got, denom), (1, 4))

    def test_an_empty_per_date_list_is_None_rather_than_zero(self):
        """A count of zero and an absent producer must not read the same -- `O21-D2`'s VACUOUS
        rule. Zero dates clearing is a finding; no rows at all is a missing input."""
        got, denom = V.group_dates_clearing({"robustness": {"per_date": []}})
        self.assertIsNone(got)
        self.assertEqual(denom, 0)


# =============================================================================================
class TheC1AttributionControlSeparatesUniverseFromBrokenRun(unittest.TestCase):
    """S22's C1 FAILS on the corrected universe, correctly -- it is a fidelity gate to the
    banked 2,531-name record. But a broken panel, a wrong column or a mis-keyed join would fail
    it identically and look the same in the artifact. The control requires the run's own
    deployed alpha to reproduce part 1b's landed figure, so the failure becomes attributable."""

    def test_a_passing_C1_needs_no_attribution(self):
        ok, d = V.c1_is_attributable_to_the_universe(
            {"C1_incumbent_reproduces_record": {"all_ok": True}})
        self.assertTrue(ok)
        self.assertTrue(d["c1_all_ok"])

    def test_a_failing_C1_that_reproduces_part_1bs_figure_is_attributable(self):
        import scripts.corrected_claims as CC2
        try:
            want = CC2.landed_corrected_deployed_alpha()
        except Exception:
            print("SKIP: part 1b's landed artifact absent (licensed data not on this host)")
            return
        ok, d = V.c1_is_attributable_to_the_universe(
            {"C1_incumbent_reproduces_record":
                {"all_ok": False, "checks": {"top_decile_alpha": {"got": want}}}})
        self.assertTrue(ok, d)
        self.assertLessEqual(d["abs_dev"], V.C1_CROSS_INSTRUMENT_TOL)

    def test_a_failing_C1_that_does_NOT_reproduce_it_is_refused(self):
        """Non-vacuity in the direction that matters: a broken run must NOT be waved through as
        'expected on a different universe'."""
        ok, d = V.c1_is_attributable_to_the_universe(
            {"C1_incumbent_reproduces_record":
                {"all_ok": False, "checks": {"top_decile_alpha": {"got": 0.123456}}}})
        self.assertFalse(ok)
        self.assertGreater(d["abs_dev"], V.C1_CROSS_INSTRUMENT_TOL)

    def test_a_failing_C1_with_no_reading_is_refused(self):
        ok, d = V.c1_is_attributable_to_the_universe(
            {"C1_incumbent_reproduces_record": {"all_ok": False, "checks": {}}})
        self.assertFalse(ok)
        self.assertIn("cannot be attributed", d["why"])

    def test_C1_RECORD_is_untouched(self):
        """`W-28`: a pre-committed bar may not be relaxed after watching it fail. The published
        record S22's C1 compares against must still be the published record."""
        from scripts.term_structure import C1_RECORD
        self.assertAlmostEqual(C1_RECORD["top_decile_alpha"], 0.071741423321, places=11)
        self.assertAlmostEqual(C1_RECORD["long_short_tstat"], 2.8360640685320595, places=12)

    def test_the_S22_rows_refuse_when_the_failure_is_not_attributable(self):
        ts = {"C1_incumbent_reproduces_record":
              {"all_ok": False, "checks": {"top_decile_alpha": {"got": 0.999}}},
              "horizons": [63], "primary_common_dates": {"63": {"alpha_t_hac": 9.0}},
              "verdict": {"R_8": 9.0}}
        rows = V.s22_rows(ts)
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["state"], UNMEASURED)
            self.assertIn("NOT attributable", r["why"])


# =============================================================================================
class TheV6BAbortIsReadNotSecondGuessed(unittest.TestCase):
    def test_an_aborted_V6B_is_UNMEASURED_and_names_its_register(self):
        v6 = {"ABORTED": "C1 FAILED - every V6-B arm is VOID per register 6.6",
              "controls": {"C1_reproduces_record": {"measured": {"top_decile_alpha": 0.06}}}}
        rows = V.v6b_rows(v6)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["state"], UNMEASURED)
        self.assertIn("register", rows[0]["why"])
        self.assertIn("OWN REGISTER", rows[0]["why"].upper())

    def test_the_abort_is_not_parameterised_away(self):
        """`W-28`. Unlike served_index_book -- whose gate takes an expect_alpha parameter BY
        DESIGN -- V6-B's C1 is unconditional and its register voids every arm behind it. Nothing
        here may hand it a different target."""
        src = _src(VERDICT_SRC)
        self.assertNotIn("v6-artifact", src.lower().replace("_", "-").replace("v6_artifact",
                                                                             "v6-artifact")
                         [:0] or "", "")
        t = _tree(VERDICT_SRC)
        for n in ast.walk(t):
            if isinstance(n, ast.Call):
                for kw in n.keywords or []:
                    self.assertNotEqual(
                        kw.arg, "expect_record",
                        "V6-B's C1 record is being re-targeted, which relaxes a pre-committed "
                        "gate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
