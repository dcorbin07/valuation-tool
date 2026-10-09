# -*- coding: utf-8 -*-
"""`STAGE1-BATCH1` — the quadrant, the kills, the BH ladder, and the things that would make any
of it meaningless.

The dominant risk in a staged protocol is **spending the check quadrant**, which cannot be
replaced. Most of this file pins that it is never opened. The rest pins the three ways a free
kill stops being free: a parser that cannot see its data (which returned a confident
`spine_coverage = 0.0000` here), a bar relaxed after it fires, and a half too thin to carry a
verdict being reported as though it were a half.
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fa():
    for c in (os.environ.get("VALQUO_DATA_ROOT"), os.path.join(REPO, "data"),
              r"C:\Users\donni\Downloads\valuation-tool\data"):
        if c and os.path.isdir(os.path.join(c, "free_analysis")):
            return os.path.join(c, "free_analysis")
    return None


def _src(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read()


#: the subscript form of a check-half selection -- `t["_half"] == 1`. Kept as a
#: module constant so the test body needs no nested quoting, which is how the
#: first attempt at this fixture came to be unparseable.
_SUBSCRIPT_PROBE = 't = t[t["_half"] == 1]' + chr(10)


class TheCheckQuadrantIsNeverOpened(unittest.TestCase):
    """It cannot be replaced. Looking at it to choose among these arms would spend it."""

    def test_the_build_half_is_half_zero_and_the_cut_is_2019(self):
        import scripts.stage1_kills as K
        self.assertEqual(K.BUILD_HALF, 0)
        self.assertEqual(K.BUILD_END, "2019-12-31")
        self.assertEqual(K.BUILD_HALF_SPLIT, "2014-12-31")

    def test_the_quadrant_helper_returns_only_2009_2019_and_only_half_zero(self):
        import pandas as pd
        import scripts.stage1_kills as K
        from scripts.r4_x1_accounting_universe import stable_key_half
        rows = []
        for t in ("AAPL", "MSFT", "JNJ", "KO", "XOM", "WMT", "T", "PFE"):
            for d in ("2010-06-30", "2015-06-30", "2021-06-30", "2025-06-30"):
                rows.append({"date": d, "ticker": t, "fwd_ret": 0.0})
        p = pd.DataFrame(rows)
        b, cen = K.build_quadrant(p)
        self.assertTrue(all(str(x) <= "2019-12-31" for x in b["date"]))
        self.assertTrue(all(stable_key_half(t) == 0 for t in b["ticker"]))
        self.assertEqual(cen["dates"], len({str(x) for x in b["date"]}))

    def test_no_script_filters_to_the_CHECK_side(self):
        """A script that ever selects half 1, or dates after 2019, is opening it.

        **REPOINTED AFTER FIRING ON A COMMENT.** The first form was
        `assertNotIn("== 1", src)`, and it matched `# average UNCAPPED exposure == 1.0` in
        `stage1_batch2_kills.py` -- prose describing a normalisation, not a half selection. That
        is the substring-ban family, and a guard that cannot tell code from prose about code is
        not measuring the tree. The property it protects is real and load-bearing, so it is
        STRENGTHENED rather than loosened: the half check now reads the AST for a comparison
        against the literal 1 whose subject is a half-valued name, which is the actual defect.
        """
        import tokenize

        def _code_only(src):
            """The source with comments and string literals removed, so prose may name what the
            rule forbids and CODE may not."""
            out = []
            try:
                for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                    if tok.type in (tokenize.COMMENT, tokenize.STRING):
                        continue
                    out.append(tok.string)
            except (tokenize.TokenError, IndentationError):      # pragma: no cover
                return src
            return " ".join(out)

        def _selects_half_one(tree):
            """A comparison against the literal 1 whose subject is a HALF-valued name."""
            names = ("stable_key_half", "_half", "BUILD_HALF", "half")
            hits = []
            for n in ast.walk(tree):
                if not isinstance(n, ast.Compare):
                    continue
                parts = [n.left] + list(n.comparators)
                has_one = any(isinstance(x, ast.Constant) and x.value == 1 for x in parts)
                if not has_one:
                    continue
                for x in parts:
                    for sub in ast.walk(x):
                        nm = (getattr(sub, "id", None) or getattr(sub, "attr", None)
                              or (getattr(getattr(sub, "func", None), "id", None)
                                  if isinstance(sub, ast.Call) else None))
                        # A SUBSCRIPT STRING KEY IS THE LIKELIEST REAL FORM, and the first cut
                        # MISSED it: `t["_half"] == 1` is a Subscript carrying a string constant,
                        # not a Name, so a detector reading only ids and attrs cannot see the way
                        # this defect would actually appear in pandas code. Found by MUTATION,
                        # not by reading -- one of two mutations got through.
                        if nm is None and isinstance(sub, ast.Subscript) \
                                and isinstance(sub.slice, ast.Constant) \
                                and isinstance(sub.slice.value, str):
                            nm = sub.slice.value
                        if nm in names:
                            hits.append(getattr(n, "lineno", None))
            return hits

        # the stripper must be non-vacuous in BOTH directions, or it could pass by seeing nothing
        probe = "x = 1  # the comment says == 1\ny = '== 1'\nif _half == 1:\n    pass\n"
        stripped = _code_only(probe)
        self.assertIn("_half", stripped, "the stripper removed real code")
        self.assertNotIn("the comment says", stripped, "the stripper kept a comment")
        self.assertTrue(_selects_half_one(ast.parse(probe)),
                        "the AST half-detector cannot see `_half == 1`")
        self.assertTrue(_selects_half_one(ast.parse(_SUBSCRIPT_PROBE)),
                        "the AST half-detector cannot see the SUBSCRIPT form, which is the "
                        "likeliest real one in pandas code")
        self.assertFalse(_selects_half_one(ast.parse("c = 1.0 / n  # exposure == 1.0\n")),
                         "the AST half-detector fires on an unrelated comparison")

        for f in sorted(os.listdir(os.path.join(REPO, "scripts"))):
            if not f.startswith("stage1_"):
                continue
            s = _src("scripts/" + f)
            hits = _selects_half_one(ast.parse(s))
            self.assertFalse(hits, "%s selects the check half (lines %r)" % (f, hits))
            # the DATE bans stay literal and are applied to the WHOLE source: a date string IS
            # the thing banned, and a Stage-1 script naming the check window even in a comment
            # is worth refusing.
            for bad in ("2020-01-01", "2026-04-09", "BUILD_HALF + 1"):
                self.assertNotIn(bad, s, "%s names the check quadrant (%s)" % (f, bad))

    def test_the_scoring_artifact_records_that_it_was_not_opened(self):
        fa = _fa()
        p = os.path.join(fa or "", "STAGE1_SCORE.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: scoring artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertFalse(d["check_quadrant_opened"])
        self.assertEqual(d["quadrant"]["last"], "2019-12-31")


class TheKillsAreFreeAndRunFirst(unittest.TestCase):
    def test_no_kill_reads_a_forward_return(self):
        """What makes a pre-outcome control free is that it cannot see the outcome. `MB1-SEL`."""
        for f in ("stage1_kills.py", "stage1_kills_run.py"):
            tree = ast.parse(_src("scripts/" + f))
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    self.assertNotEqual(n.value, "fwd_ret",
                                        "%s reads the outcome column" % f)

    def test_the_scorer_REFUSES_without_the_kill_artifacts(self):
        """`O10`: a gating control computed in the same pass as the outcomes cannot be claimed
        to have been read first.

        **A MUTATION MISS CLOSED.** The first cut only grepped for the refusal STRING, which
        survives turning its `if` into `if False` -- a guard that cannot fire still contains its
        own message. So the CONDITION is read off the AST: the refusal must be reached from a
        real `os.path.exists` test, never from a constant.
        """
        src = _src("scripts/stage1_score_run.py")
        self.assertIn("REFUSING: no kill artifact", src)
        tree = ast.parse(src)
        guarded = False
        for n in ast.walk(tree):
            if not isinstance(n, ast.If):
                continue
            body = ast.dump(ast.Module(body=n.body, type_ignores=[]))
            if "REFUSING: no kill artifact" not in body:
                continue
            test = ast.dump(n.test)
            self.assertNotIn("Constant(value=False)", test,
                             "the refusal is guarded by a constant, so it can never fire")
            self.assertIn("exists", test,
                          "the refusal must be guarded by a real existence check")
            guarded = True
        self.assertTrue(guarded, "no `if` guards the refusal at all")

    def test_only_arms_whose_kill_PASSED_are_scored(self):
        s = _src("scripts/stage1_score_run.py")
        self.assertIn('kill_passes") is True', s)

    def test_the_inherited_bars_are_the_projects_own_numbers(self):
        import scripts.stage1_kills as K
        self.assertEqual(K.COVERAGE_FLOOR, 0.70)       # the non-null rule
        self.assertEqual(K.COSTUME_BAR, 0.60)          # N6's bar
        self.assertEqual(K.INERT_BAR, 0.995)           # SECTOR-NEUTRAL-B6 / S15
        self.assertEqual(K.MIN_DAILY_OBS, 200)
        self.assertEqual(tuple(K.ANN_PER_YEAR_BAND), (3.0, 5.0))


class TheEventCodeParserCanSeeItsData(unittest.TestCase):
    """THE DEFECT THIS PINS, and it is mine: the EVENTS cache is `[(date, [codes])]`, a LIST of
    code strings, and my first parser did `str(codes).split(",")` -- which turns
    `['22','71','91']` into `"['22'"`, `" '71'"`, `" '91']"` and can NEVER match `"22"`. It
    returned a confident **spine coverage of exactly 0.0000** against a cache holding 17,779
    names, when `O6`/`O7` measured ~4 code-22 dates per ticker-year from that same cache. Caught
    by disbelieving the zero, which is the only way this class surfaces.
    """

    def test_a_list_of_codes_is_matched(self):
        s = _src("scripts/stage1_kills_run.py")
        self.assertIn("isinstance(codes, (list, tuple, set))", s)

    def test_the_two_shapes_both_resolve(self):
        for codes, want in ((["22", "71"], True), (["81"], False),
                            ("22,71", True), ("81", False), (None, False)):
            if isinstance(codes, (list, tuple, set)):
                have = {str(x).strip() for x in codes}
            else:
                have = {x.strip() for x in str(codes or "").replace("|", ",").split(",")}
            self.assertEqual("22" in have, want, "codes=%r" % (codes,))

    def test_a_string_shape_would_also_have_worked(self):
        """Non-vacuity: the fix must not have replaced one blind branch with another."""
        have = {x.strip() for x in "22,71,91".replace("|", ",").split(",")}
        self.assertIn("22", have)


class NoBarIsRelaxedAfterItFires(unittest.TestCase):
    def test_A8s_band_is_still_the_registered_one(self):
        """`W-28`: a pre-committed bar may not be relaxed after watching it fail. A8's measured
        2.6945 falls BELOW [3.0, 5.0] and the band is NOT widened."""
        import scripts.stage1_kills as K
        self.assertEqual(tuple(K.ANN_PER_YEAR_BAND), (3.0, 5.0))

    def test_A6s_coverage_bar_is_still_0_70(self):
        import scripts.stage1_kills as K
        self.assertEqual(K.COVERAGE_FLOOR, 0.70)

    def test_A1s_burn_in_verdict_is_read_at_an_ANCHOR_that_predates_the_register(self):
        """The register under-specified the burn-in and the coverage is NOT invariant across a
        plausible range -- so the verdict would otherwise be decided by a parameter chosen after
        the register. `W-28`'s draft froze this construction at >= 10 fiscal years."""
        from scripts.stage1_kills_run import A1_VERDICT_BURN_IN, A1_BURN_IN_YEARS
        self.assertEqual(A1_VERDICT_BURN_IN, 10)
        self.assertIn(10, A1_BURN_IN_YEARS)
        s = _src("scripts/stage1_kills_run.py")
        self.assertIn("PREREG_DRAFT_w28_total_q.md", s)
        self.assertIn("would have PASSED", s, "the counterfactual must be recorded")

    def test_that_anchor_is_really_in_W28s_draft(self):
        p = os.path.join(REPO, "PREREG_DRAFT_w28_total_q.md")
        if not os.path.exists(p):
            self.skipTest("LOUD SKIP: W-28 draft absent")
        s = io.open(p, encoding="utf-8").read()
        self.assertIn("10 fiscal years", s)

    def test_A1_reports_THREE_numbers_and_not_one_coverage_figure(self):
        """R&D is LEGITIMATELY zero for most firms. Counting a true zero as missing understates
        coverage; counting missing as zero asserts a fact."""
        s = _src("scripts/stage1_kills_run.py")
        for k in ("truly_non_null", "structurally_zero", "absent"):
            self.assertIn(k, s)
        self.assertIn("share_nonnull_plus_zero", s)


class AThinHalfIsNotAHalf(unittest.TestCase):
    """`MA58`'s finding, reproduced here and WORSE: complete-case residualisation on the seven
    themes leaves 25 of 44 quadrant dates and a FIVE-date early half, because `institutional` is
    non-null on 56.85% of the quadrant and empty before 2013-12-27."""

    def test_the_floor_is_the_shipped_min_dates(self):
        from scripts.stage1_score_run import MIN_HALF_DATES
        self.assertEqual(MIN_HALF_DATES, 16)

    def test_a_thin_half_is_reported_NOT_ASSESSABLE_rather_than_scored(self):
        """The rule now lives in `stage1_score.stage1_verdict` -- ONE definition of the verdict
        and its floor, which is what made it exercisable at all."""
        from scripts.stage1_score import stage1_verdict
        state, words = stage1_verdict({"n": 5, "t": 9.9}, {"n": 20, "t": 9.9}, True)
        self.assertEqual(state, "NOT_ASSESSABLE")
        self.assertIn("BOTH-HALVES NOT ASSESSABLE", words)
        self.assertIn("halves_assessable", _src("scripts/stage1_score_run.py"))
        self.assertIn("S.stage1_verdict(", _src("scripts/stage1_score_run.py"))

    def test_the_restriction_is_MEASURED_and_lands_in_the_artifact(self):
        s = _src("scripts/stage1_score_run.py")
        self.assertIn("def template_restriction", s)
        self.assertIn("binding_theme", s)

    def test_the_landed_artifact_records_a_thin_half_and_no_pass_from_it(self):
        fa = _fa()
        p = os.path.join(fa or "", "STAGE1_SCORE.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: scoring artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        tr = d["template_restriction"]
        self.assertLess(tr["usable_dates"], tr["quadrant_dates"])
        self.assertEqual(tr["binding_theme"], "institutional")
        for name, v in d["arms"].items():
            if not v.get("halves_assessable"):
                self.assertIn("NOT ASSESSABLE", v["stage1_verdict"],
                              "%s reports a verdict from a half that is too thin" % name)

    def test_NO_arm_is_recorded_as_clearing_stage_1(self):
        fa = _fa()
        p = os.path.join(fa or "", "STAGE1_SCORE.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: scoring artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        cleared = [n for n, v in d["arms"].items()
                   if str(v.get("stage1_verdict", "")).startswith("CLEARS")]
        self.assertEqual(cleared, [], "an arm is recorded as clearing Stage 1: %r" % cleared)

    def test_the_verdict_RULE_is_exercised_directly_in_all_THREE_states(self):
        """A MUTATION MISS CLOSED, and the fix was to the CODE: the rule was inlined in a loop,
        so prefixing its string with "CLEARS" was invisible to a source grep AND to an artifact
        check (the artifact on disk does not change when the source does). Extracted, it can be
        called."""
        from scripts.stage1_score import stage1_verdict, MIN_HALF_DATES
        thin = ({"n": 5, "t": 9.9}, {"n": 20, "t": 9.9})
        state, words = stage1_verdict(thin[0], thin[1], True)
        self.assertEqual(state, "NOT_ASSESSABLE")
        self.assertFalse(words.startswith("CLEARS"),
                         "a half below the floor must NEVER read as clearing")
        both = ({"n": MIN_HALF_DATES, "t": 2.5}, {"n": MIN_HALF_DATES, "t": 2.5})
        state, words = stage1_verdict(both[0], both[1], True)
        self.assertEqual(state, "CLEARS")
        self.assertTrue(words.startswith("CLEARS"))
        one = ({"n": MIN_HALF_DATES, "t": 1.4}, {"n": MIN_HALF_DATES, "t": 2.5})
        self.assertEqual(stage1_verdict(one[0], one[1], True)[0], "NOT_REPLICATED")
        # a sign disagreement also fails, even with both halves strong
        flip = ({"n": MIN_HALF_DATES, "t": 2.5}, {"n": MIN_HALF_DATES, "t": 2.5})
        self.assertEqual(stage1_verdict(flip[0], flip[1], False)[0], "NOT_REPLICATED")

    def test_a_non_assessable_verdict_can_never_begin_with_CLEARS(self):
        from scripts.stage1_score import stage1_verdict
        for ne in (0, 1, 5, 15):
            _st, w = stage1_verdict({"n": ne, "t": 99.0}, {"n": 20, "t": 99.0}, True)
            self.assertFalse(w.startswith("CLEARS"), "early n=%d" % ne)


class TheBHLadderIsTheRegistersAndKStaysTwelve(unittest.TestCase):
    def test_k_is_twelve_and_q_is_a_tenth(self):
        import scripts.stage1_score as S
        self.assertEqual(S.BH_K, 12)
        self.assertEqual(S.BH_Q, 0.10)

    def test_the_ladder_is_i_times_q_over_k(self):
        from scripts.stage1_score import benjamini_hochberg
        r = benjamini_hochberg({"a": 0.001, "b": 0.02, "c": 0.5}, k=12, q=0.10)
        self.assertAlmostEqual(r["arms"]["a"]["threshold"], 1 * 0.10 / 12)
        self.assertAlmostEqual(r["arms"]["b"]["threshold"], 2 * 0.10 / 12)
        self.assertAlmostEqual(r["arms"]["c"]["threshold"], 3 * 0.10 / 12)

    def test_it_uses_the_STEP_UP_rule_and_not_a_per_test_comparison(self):
        """BH rejects everything up to the LARGEST rank that clears, which is not the same as
        rejecting each test that happens to clear its own threshold."""
        from scripts.stage1_score import benjamini_hochberg
        # b clears its threshold, a does not: step-up must still reject BOTH
        r = benjamini_hochberg({"a": 0.009, "b": 0.016}, k=12, q=0.10)
        self.assertFalse(r["arms"]["a"]["p_below_threshold"])
        self.assertTrue(r["arms"]["b"]["p_below_threshold"])
        self.assertTrue(r["arms"]["a"]["survives_bh"])
        self.assertTrue(r["arms"]["b"]["survives_bh"])

    def test_k_is_NOT_shrunk_when_fewer_arms_are_scored(self):
        """Shrinking `k` after a build failure makes every surviving threshold easier."""
        from scripts.stage1_score import benjamini_hochberg
        r = benjamini_hochberg({"a": 0.009, "b": None, "c": None}, k=12, q=0.10)
        self.assertEqual(r["k"], 12)
        self.assertAlmostEqual(r["arms"]["a"]["threshold"], 0.10 / 12)

    def test_an_unscorable_arm_is_recorded_rather_than_dropped(self):
        from scripts.stage1_score import benjamini_hochberg
        r = benjamini_hochberg({"a": 0.009, "b": None}, k=12, q=0.10)
        self.assertIsNone(r["arms"]["b"]["p"])
        self.assertIsNone(r["arms"]["b"]["survives_bh"])
        self.assertIn("why", r["arms"]["b"])

    def test_the_BH_set_excludes_the_arms_judged_on_a_margin(self):
        """§0c: this project's bars are mostly MARGINS, and §6 forbids inventing a `p` so a
        method applies. `R1-VAR` is the precedent."""
        import scripts.stage1_score as S
        for a in ("A4", "A5", "A8"):
            self.assertNotIn(a, S.BH_SET)
        for a in ("A1", "A3", "A7", "A11"):
            self.assertIn(a, S.BH_SET)


class NoAlphaClaimAndNoCalibratedFloor(unittest.TestCase):
    def test_no_X7_floor_is_quoted_anywhere(self):
        for f in sorted(os.listdir(os.path.join(REPO, "scripts"))):
            if not f.startswith("stage1_"):
                continue
            s = _src("scripts/" + f)
            for fl in ("2.2837", "2.0540", "2.7072", "19.667", "1.8629", "0.6637",
                       "2.070231", "2.056680", "1.826210"):
                self.assertNotIn(fl, s, "%s quotes the X7 floor %s" % (f, fl))

    def test_every_critical_value_is_labelled_uncalibrated(self):
        s = _src("scripts/stage1_score_run.py")
        self.assertIn("UNCALIBRATED", s)
        self.assertIn("crit_label", s)

    def test_the_normal_approximation_for_p_is_NAMED_rather_than_presented_as_exact(self):
        """§6 forbids inventing a `p` so a method applies; the approximation is declared and
        its size bounded."""
        import inspect
        from scripts.stage1_score import two_sided_p
        src = inspect.getsource(two_sided_p)
        self.assertIn("normal approximation", src)
        self.assertIn("third decimal", src)


class TheResidualisationIsPlainLeastSquares(unittest.TestCase):
    def test_the_residual_removes_the_themes_exactly_on_a_synthetic_case(self):
        import numpy as np
        from scripts.stage1_score import _ols_resid
        x = np.linspace(-1, 1, 50)
        y = 3.0 + 2.0 * x
        r = _ols_resid(y, x.reshape(-1, 1))
        self.assertLess(float(np.abs(r).max()), 1e-9)

    def test_a_signal_orthogonal_to_the_themes_survives_residualisation(self):
        """Non-vacuity in the other direction: residualisation must not null everything."""
        import numpy as np
        from scripts.stage1_score import _ols_resid
        x = np.linspace(-1, 1, 50)
        y = np.sin(7.0 * x)
        r = _ols_resid(y, x.reshape(-1, 1))
        self.assertGreater(float(np.std(r)), 0.1)

    def test_the_HAC_t_is_newey_west_at_lag_one(self):
        from scripts.stage1_score import hac_t
        r = hac_t([0.01] * 10)
        self.assertIsNone(r, "a zero-variance series must not return a t")
        r = hac_t([0.01, -0.01, 0.02, 0.0, 0.03, -0.02, 0.01, 0.02])
        self.assertIsNotNone(r)
        self.assertEqual(r["n"], 8)


class TheShippedBuilderGainedAParameterAndItsDefaultIsTheOldBehaviour(unittest.TestCase):
    """A2a needed the shipped `residual_momentum` toggle REACHABLE -- it was hard-coded False at
    the one `build_frame` call the panel's own composite comes from, so the toggle had never been
    scored and could not be. Parameterising a SHIPPED builder is exactly where a silent default
    change hides (`B7`: one definition, and a default equal to the original), so the default is
    pinned by the AST rather than by running a 20-minute build."""

    def _fn(self):
        src = io.open(os.path.join(REPO, "valuation", "edge", "fundamental_panel.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == "build_fundamental_panel":
                return n
        self.fail("build_fundamental_panel not found")

    def test_the_new_parameter_exists_and_DEFAULTS_TO_FALSE(self):
        fn = self._fn()
        names = [a.arg for a in fn.args.args]
        self.assertIn("residual_momentum", names,
                      "A2a's kill cannot build the toggled panel without it")
        # defaults align to the TAIL of args
        off = len(names) - len(fn.args.defaults)
        d = fn.args.defaults[names.index("residual_momentum") - off]
        self.assertIsInstance(d, ast.Constant)
        self.assertIs(d.value, False,
                      "the default MUST be False or every existing caller silently changes")

    def test_the_OTHER_frames_in_the_same_build_stay_False(self):
        """One build must not vary two things. The standardiser arms and the sector-neutral pair
        are OTHER arms' frames; toggling them too would confound this toggle with those."""
        fn = self._fn()
        passed, hard_false = 0, 0
        for n in ast.walk(fn):
            if not isinstance(n, ast.Call):
                continue
            if getattr(n.func, "id", getattr(n.func, "attr", None)) != "build_frame":
                continue
            for kw in n.keywords:
                if kw.arg != "residual_momentum":
                    continue
                if isinstance(kw.value, ast.Name) and kw.value.id == "residual_momentum":
                    passed += 1
                elif isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    hard_false += 1
                else:
                    self.fail("a build_frame call passes something else for residual_momentum")
        self.assertEqual(passed, 1,
                         "EXACTLY ONE frame -- the composite's own -- may see the parameter")
        self.assertGreater(hard_false, 0,
                           "the other arms' frames must stay pinned False, or this is vacuous")


if __name__ == "__main__":
    unittest.main(verbosity=2)
