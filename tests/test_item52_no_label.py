"""ITEM 52 part 1 — THE BUY/HOLD/REDUCE LABEL IS GONE, AND TWO PLAIN READS REPLACE IT.

**WHAT DON SAW, AND IT IS THE WHOLE ARGUMENT.** NVDA scored **79 "Buy"** out of valuation 15.9,
quality 97.2, growth 100, health 97.4 and momentum 70.2 — on a name priced **56% above the
model's own base value**. That is a business-quality grade wearing a trading verdict. And **no
study in this project has ever tested those labels against returns**, so the one number on the
page carrying the most authority was the one with the least evidence behind it.

The replacement is not a softer label. It is the two different questions the sub-scores answer,
which the single word collapsed:

  * **Business quality** — the four non-valuation sub-scores, in words.
  * **Price vs our model** — the premium or discount to the base value, as a sentence a reader
    can check against the two numbers beside it.

NVDA now reads *"Outstanding business"* and *"Priced 56% above our base value."* Both are true,
they pull in opposite directions, and a reader can disagree with either without disagreeing
with the other.

**THIS IS PRESENTATION ONLY, AND THAT IS ASSERTED RATHER THAN PROMISED.** The composite, the
sub-scores and their weights are untouched; `compute_score` still has exactly one caller; and
the one NUMBER the label function also carried — its "Buy" boundary at 66, which `dip.py`'s
health gate uses as a floor — survives as a named constant that `dip` imports, unmoved.

    python tests/test_item52_no_label.py
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.engine import scoring as S          # noqa: E402
import types                                       # noqa: E402

from valuation.web import dip                      # noqa: E402
from valuation.web import price_assumes as PA      # noqa: E402

#: The five words the page used to print. Banned as a SET from the surfaces that render a
#: score, never as a blanket ban on the tree: "Avoid" and "Hold" are ordinary English, and a
#: ban that fires on honest prose is a ban somebody deletes.
LABELS = ("Strong Buy", "Buy", "Hold", "Reduce", "Avoid")

#: Where a label would reach a user. Each is a site the label actually occupied before this
#: item, found by tracing `ScoreResult.recommendation` rather than by grepping for the words.
RENDER_SITES = (
    os.path.join("valuation", "web", "static", "app.js"),
    os.path.join("valuation", "report", "pdf.py"),
    os.path.join("valuation", "report", "excel.py"),
    os.path.join("valuation", "web", "showcase.py"),
    os.path.join("valuation", "ai", "analyst.py"),
)


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class TheLabelIsGone(unittest.TestCase):

    def test_the_score_result_carries_no_recommendation_at_all(self):
        self.assertFalse(hasattr(S.ScoreResult, "recommendation"))
        fields = set(S.ScoreResult.__dataclass_fields__)
        self.assertNotIn("recommendation", fields)
        self.assertIn("business_quality", fields)
        self.assertIn("price_vs_model", fields)

    def test_the_label_FUNCTION_is_gone_rather_than_merely_unused(self):
        # An unused producer is a label one import away from coming back.
        self.assertFalse(hasattr(S, "_recommendation"))

    def test_no_render_site_still_reads_a_recommendation_field(self):
        offenders = []
        for rel in RENDER_SITES:
            src = _src(rel)
            for ln, line in enumerate(src.splitlines(), 1):
                if "recommendation" not in line:
                    continue
                if line.lstrip().startswith(("#", "//", "*", "/*")):
                    continue        # a comment explaining the removal is not a render
                offenders.append("%s:%d %s" % (rel, ln, line.strip()[:70]))
        self.assertEqual(offenders, [], offenders)

    def test_the_five_words_are_not_typed_into_any_render_site(self):
        offenders = []
        for rel in RENDER_SITES:
            for ln, line in enumerate(_src(rel).splitlines(), 1):
                if line.lstrip().startswith(("#", "//", "*", "/*")):
                    continue
                for w in ('"Strong Buy"', "'Strong Buy'", '"Reduce"', "'Reduce'"):
                    if w in line:
                        offenders.append("%s:%d %s" % (rel, ln, w))
        self.assertEqual(offenders, [], offenders)

    def test_POSITIVE_CONTROL_the_ban_can_actually_fire(self):
        # Or every assertion above passes by looking at nothing (`MB21`'s C1).
        line = '  html += `<span>${r.recommendation}</span>`;'
        self.assertIn("recommendation", line)
        self.assertFalse(line.lstrip().startswith(("#", "//")))


class ThePresentationChangedAndTheARITHMETICDidNot(unittest.TestCase):

    def test_compute_score_still_has_exactly_ONE_caller(self):
        """The prompt's own condition. A second caller is a second scoring path."""
        callers = []
        for base, _dirs, files in os.walk(os.path.join(REPO, "valuation")):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(base, fn)
                with io.open(p, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
                try:
                    tree = ast.parse(src)
                except SyntaxError:                                    # noqa: PERF203
                    continue
                for n in ast.walk(tree):
                    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == "compute_score"):
                        callers.append("%s:%d" % (os.path.relpath(p, REPO), n.lineno))
        self.assertEqual(len(callers), 1, callers)
        self.assertIn("pipeline.py", callers[0])

    def test_the_subscore_floor_the_label_also_carried_has_NOT_moved(self):
        self.assertEqual(S.SUBSCORE_STRONG, 66.0)
        self.assertEqual(set(dip.HEALTH_FLOORS.values()), {66.0})
        self.assertEqual(sorted(dip.HEALTH_FLOORS), ["growth", "health", "quality"])

    def test_dip_IMPORTS_the_floor_rather_than_typing_it(self):
        # The comment used to cite the label function while the line typed 66.0 itself, so
        # deleting the function would have orphaned the citation.
        src = _src(os.path.join("valuation", "web", "dip.py"))
        i = src.index("HEALTH_FLOORS: Dict[str, float]")
        decl = src[i:src.index("}", i)]
        self.assertIn("SUBSCORE_STRONG", decl)
        self.assertNotIn("66", decl)

    def test_the_valuation_subscore_is_NOT_in_the_business_read(self):
        """Mixing how good a company is with how dear it is was the defect."""
        self.assertNotIn("valuation", S.BUSINESS_SUBSCORES)
        self.assertEqual(sorted(S.BUSINESS_SUBSCORES),
                         ["growth", "health", "momentum", "quality"])


class TheBusinessRead(unittest.TestCase):

    W = {"valuation": 0.20, "quality": 0.15, "growth": 0.30, "health": 0.25, "momentum": 0.10}

    def test_NVDAs_own_subscores_read_Outstanding_business(self):
        phrase, v = S.business_quality(
            {"valuation": 15.9, "quality": 97.2, "growth": 100.0, "health": 97.4,
             "momentum": 70.2}, self.W)
        self.assertEqual(phrase, "Outstanding business")
        self.assertAlmostEqual(v, 94.9, places=1)

    def test_the_valuation_subscore_cannot_move_it(self):
        base = dict(quality=60.0, growth=60.0, health=60.0, momentum=60.0)
        a = S.business_quality(dict(base, valuation=0.0), self.W)
        b = S.business_quality(dict(base, valuation=100.0), self.W)
        self.assertEqual(a, b)

    def test_a_name_with_none_of_the_four_scored_reports_MISSING_not_average(self):
        # The COVERAGE RULE's direction: an empty field shows as missing, never as "Average".
        self.assertEqual(S.business_quality({"valuation": 80.0}, self.W), (None, None))

    def test_the_weights_are_renormalised_over_what_is_present(self):
        # One sub-score present must give that sub-score's own band, not a diluted one.
        phrase, v = S.business_quality({"quality": 90.0}, self.W)
        self.assertEqual(phrase, "Outstanding business")
        self.assertAlmostEqual(v, 90.0, places=6)

    def test_every_band_is_reachable_and_they_are_ordered(self):
        seen = []
        for q in (95.0, 70.0, 50.0, 35.0, 10.0):
            seen.append(S.business_quality({"quality": q}, self.W)[0])
        self.assertEqual(seen, ["Outstanding business", "Strong business", "Average business",
                                "Weak business", "Poor business"])

    def test_no_band_phrase_contains_a_trading_word(self):
        words = [p for _, p in S._QUALITY_BANDS] + [S._QUALITY_FLOOR]
        for p in words:
            for bad in ("buy", "sell", "hold", "reduce", "avoid", "accumulate", "trim"):
                self.assertNotIn(bad, p.lower(), p)


class ThePriceRead(unittest.TestCase):

    def test_NVDA_TSLA_and_a_discount(self):
        self.assertEqual(S.price_vs_model(226.32, 145.44),
                         "Priced 56% above our base value.")
        self.assertEqual(S.price_vs_model(378.03, 23.23),
                         "Priced 1527% above our base value.")
        self.assertEqual(S.price_vs_model(80.0, 100.0),
                         "Priced 20% below our base value.")

    def test_near_parity_says_so_rather_than_rounding_to_zero_percent(self):
        self.assertEqual(S.price_vs_model(100.0, 100.5),
                         "Priced within 2% of our base value.")

    def test_a_WITHHELD_value_is_not_a_zero_premium(self):
        s = S.price_vs_model(100.0, None, withheld=True, withheld_value=1289.68)
        self.assertIn("declined to publish", s)
        for bad in ("0%", "within 2%", "above", "below"):
            self.assertNotIn(bad, s)

    def test_no_base_value_at_all_says_there_is_nothing_to_compare(self):
        self.assertIn("no base value", S.price_vs_model(100.0, None))

    def test_no_price_says_so_rather_than_dividing(self):
        self.assertIn("No current price", S.price_vs_model(None, 50.0))

    def test_it_never_says_cheap_or_expensive_or_a_trading_word(self):
        for args in ((226.32, 145.44), (80.0, 100.0), (100.0, 100.5), (None, 50.0)):
            s = S.price_vs_model(*args).lower()
            for bad in ("cheap", "expensive", "buy", "sell", "undervalued", "overvalued",
                        "opportunity", "bargain"):
                self.assertNotIn(bad, s, s)


class TheAIPanelMayNotReinstateTheLabel(unittest.TestCase):

    def test_the_prompt_forbids_a_recommendation_in_the_forms_it_takes(self):
        src = _src(os.path.join("valuation", "ai", "analyst.py"))
        self.assertIn("DO NOT RECOMMEND BUYING, SELLING OR HOLDING", src)
        for form in ("price target", "allocation", "accumulate", "trim"):
            self.assertIn(form, src)

    def test_the_old_instruction_to_reference_the_recommendation_is_gone(self):
        """READ FROM THE VALUE, NOT THE SOURCE -- and my first cut of this test got it wrong.

        It asserted the old phrase was absent from the FILE, and failed against a correct
        tree: the comment recording the change quotes the instruction it replaced. That is
        this repository's most repeated test defect, committed here in the very suite written
        to remove a label. The schema's VALUE is the thing that reaches the model.
        """
        from valuation.ai import analyst
        take = analyst._SCHEMA["overall_take"]
        self.assertNotIn("reference the score and the main tension", take)
        self.assertIn("price-vs-model read", take)
        self.assertIn("business-quality read", take)

    def test_the_model_is_given_the_two_reads(self):
        src = _src(os.path.join("valuation", "ai", "analyst.py"))
        self.assertIn('"business_quality": result.score.business_quality', src)
        self.assertIn('"price_vs_model": result.score.price_vs_model', src)


class ThePriceAssumesLeadAndTheDCFWarning(unittest.TestCase):
    """Parts 2, 3 and 7b, on the five names the prompt names.

    The fixtures carry the figures Don measured live on 2026-10-13 (`/api/value`,
    `/api/whatdo`) rather than calling the engine: what is under test is the COPY RULE, and a
    test that fetched NVDA would be testing the network. The engine's own wiring into these
    functions is covered where it lives, in the route block.
    """

    #: (regime, dcf_reliability, implied_avg_growth, business_growth, cash_burning)
    NAMES = {
        # hypergrowth / medium, price implies 37.9%, business grew 77% -> the gap is NEGATIVE,
        # so NVDA is NOT a story stock by the stated rule and is warned on its REGIME.
        "NVDA": ("hypergrowth", "medium", 0.379, 0.77, False),
        "APLD": ("hypergrowth", "low", 0.494, 1.00, True),
        # mature / HIGH reliability, price implies 64.9% against a business growing ~10%.
        # NOTHING but the story rule catches this one -- which is why the rule exists.
        "TSLA": ("mature", "high", 0.649, 0.10, False),
        "KO":   ("mature", "high", 0.050, 0.03, False),
        "JNJ":  ("mature", "high", 0.045, 0.04, False),
    }

    def _rev(self, implied, base=0.3435):
        return types.SimpleNamespace(implied_avg_growth=implied, base_avg_growth=base,
                                     implied_growth_bounded="")

    def _warn(self, t):
        regime, rel, imp, biz, burn = self.NAMES[t]
        return PA.dcf_warning(regime=regime, dcf_reliability=rel, cash_burning=burn,
                              growth_led=False, reverse=self._rev(imp),
                              business_growth=biz)

    def test_NVDA_APLD_and_TSLA_all_get_the_warning(self):
        for t in ("NVDA", "APLD", "TSLA"):
            self.assertTrue(self._warn(t)["warn"], t)

    def test_KO_and_JNJ_do_NOT_get_the_warning(self):
        """The prompt's own condition, and the one that stops the warning being furniture."""
        for t in ("KO", "JNJ"):
            w = self._warn(t)
            self.assertFalse(w["warn"], (t, w["triggers"]))
            self.assertEqual(w["headline"], "")
            self.assertFalse(w["reliability_suppressed"])

    def test_TSLA_is_caught_ONLY_by_the_story_rule(self):
        # mature, high reliability, not cash-burning, not growth-led: every other trigger
        # passes it. Don's example is the case the rule was written for, and this is the
        # assertion that the rule is load-bearing rather than decorative.
        self.assertEqual(self._warn("TSLA")["triggers"], ["story"])

    def test_NVDA_is_caught_by_its_REGIME_and_is_not_a_story_stock(self):
        # Its price assumes LESS growth than the business showed (37.9% vs 77%), so the gap is
        # negative. Reported because the obvious assumption -- that the warning fires on NVDA
        # because it looks expensive -- is wrong, and a reader of this suite would make it.
        w = self._warn("NVDA")
        self.assertIn("hypergrowth", w["triggers"])
        self.assertNotIn("story", w["triggers"])
        self.assertLess(w["gap_pp"], 0)

    def test_the_story_rule_is_STATED_and_disclaims_itself(self):
        self.assertIn("15 percentage points", PA.STORY_RULE_TEXT)
        self.assertIn("not a finding", PA.STORY_RULE_TEXT)
        self.assertIn("never tested", PA.STORY_RULE_TEXT)

    def test_the_rule_bites_exactly_at_the_threshold(self):
        self.assertTrue(PA.is_story_stock(self._rev(0.25), 0.10))      # 15.0pp
        self.assertFalse(PA.is_story_stock(self._rev(0.249), 0.10))    # 14.9pp

    def test_an_UNKNOWN_gap_is_not_a_zero_gap(self):
        # The most reassuring possible answer to a question nobody answered.
        self.assertIsNone(PA.story_gap_pp(None, 0.10))
        self.assertIsNone(PA.story_gap_pp(self._rev(0.5), None))
        self.assertIsNone(PA.is_story_stock(None, 0.10))

    def test_every_trigger_carries_its_own_reason(self):
        w = PA.dcf_warning(regime="hypergrowth", dcf_reliability="low", cash_burning=True,
                           growth_led=True, reverse=self._rev(0.9), business_growth=0.05)
        self.assertEqual(len(w["why"]), len(w["triggers"]))
        self.assertEqual(len(w["triggers"]), 5)
        for why in w["why"]:
            self.assertGreater(len(why), 40)

    def test_the_reliability_badge_is_renamed_when_the_warning_fires(self):
        """"DCF reliability: high" beside "do not use the DCF" is resolved in favour of the
        badge, because a badge looks like a measurement."""
        self.assertEqual(self._warn("KO")["reliability_label"], "DCF reliability")
        for t in ("NVDA", "TSLA"):
            lbl = self._warn(t)["reliability_label"]
            self.assertNotEqual(lbl, "DCF reliability")
            self.assertNotIn("reliability", lbl.lower())

    def test_the_lead_sentence_carries_all_three_numbers_in_the_prompts_shape(self):
        s = PA.price_assumes(self._rev(0.379), 0.77)["sentence"]
        self.assertEqual(s, "The price assumes about 38% a year of growth; the business grew "
                            "77% over the last year and the model's base case uses 34% a year.")

    def test_a_BOUNDED_solve_says_at_least_rather_than_about(self):
        # The engine flags exactly the priced-for-perfection names where the figure matters
        # most; reporting a floor as an estimate is how the understatement goes unnoticed.
        rev = types.SimpleNamespace(implied_avg_growth=0.95, base_avg_growth=0.3435,
                                    implied_growth_bounded="above")
        self.assertIn("at least about", PA.price_assumes(rev, 0.10)["sentence"])

    def test_no_implied_figure_says_so_rather_than_rendering_a_hole(self):
        out = PA.price_assumes(None, 0.10)
        self.assertFalse(out["available"])
        self.assertIn("could not work out", out["sentence"])

    def test_a_FINANCIAL_is_asked_the_matching_question(self):
        out = PA.price_assumes(None, 0.10, is_financial=True, implied_roe=0.182, book_roe=0.121)
        self.assertTrue(out["available"])
        self.assertIn("return on equity", out["sentence"])
        self.assertIn("18.2%", out["sentence"])
        self.assertIn("12.1%", out["sentence"])
        self.assertNotIn("growth", out["sentence"])

    def test_part_7b_the_hypergrowth_base_case_is_labelled_a_TEMPLATE(self):
        """Measured: `_fade_path(0.60, 0.030, 10, 2)` has mean 0.3435 -- the 34.35% that
        appeared on BOTH NVDA's page (growth input 77%) and APLD's (100%), because both clamp
        to the same 60% cap. Without this sentence it reads as a company forecast."""
        note = PA.hypergrowth_template_note("hypergrowth", self._rev(0.379))
        self.assertIn("not a forecast about this company", note)
        self.assertIn("60%", note)
        self.assertIn("same numbers", note)

    def test_the_template_note_is_SILENT_for_a_mature_name(self):
        # A caveat about a cap that did not bind is noise, and noise is how a caveat stops
        # being read.
        self.assertEqual(PA.hypergrowth_template_note("mature", self._rev(0.05)), "")

    def test_the_cap_and_the_mean_it_produces_are_the_engines_own(self):
        """Pinned against the engine rather than transcribed, so a change to the cap fails
        here instead of silently making this page's sentence wrong."""
        from valuation.engine.assumptions import (GROWTH_CAP_BY_REGIME, N_YEARS_BY_REGIME,
                                                  PLATEAU_BY_REGIME, _fade_path)
        cap = GROWTH_CAP_BY_REGIME["hypergrowth"]
        self.assertEqual(cap, 0.60)
        path = _fade_path(cap, 0.030, N_YEARS_BY_REGIME["hypergrowth"],
                          PLATEAU_BY_REGIME["hypergrowth"])
        self.assertAlmostEqual(sum(path) / len(path), 0.3435, places=4)

    def test_nothing_in_this_module_produces_a_trading_word(self):
        texts = [PA.STORY_RULE_TEXT, PA.WARNING_HEADLINE] + list(PA._WHY.values())
        texts.append(PA.price_assumes(self._rev(0.379), 0.77)["sentence"])
        texts.append(PA.hypergrowth_template_note("hypergrowth", self._rev(0.379)))
        for t in texts:
            for bad in ("buy", "sell", "accumulate", "trim", "overweight", "price target"):
                self.assertNotIn(bad, t.lower(), t)


class TheHotScoreNamesWhatItCouldNotSee(unittest.TestCase):
    """Part 4 and part 7a. The arithmetic was fine; the EXPLANATION was the casualty."""

    def test_the_denominator_is_the_WEIGHTED_themes_and_there_are_eight(self):
        from valuation.web import unified as U
        themes = U._all_themes()
        self.assertEqual(len(themes), 8, themes)
        self.assertEqual(themes, ["capital_discipline", "growth", "insider", "institutional",
                                  "momentum", "quality", "size", "value"])

    def test_zero_weight_themes_are_NOT_counted_as_missing_for_a_name(self):
        """`low_risk` and `sentiment` are 0.0 in BOTH weight sets -- one zeroed on a held-out
        test, one never fed -- so they can never contribute to anybody. Counting them would
        turn a design decision and an empty column into a per-name gap on EVERY name, which
        is the fastest way to make the notice meaningless."""
        from valuation.web import unified as U
        self.assertNotIn("low_risk", U._all_themes())
        self.assertNotIn("sentiment", U._all_themes())
        from valuation.screener import settings as SS
        for attr in ("WEIGHTS_ESTABLISHED", "WEIGHTS_SPECULATIVE"):
            w = getattr(SS, attr)
            self.assertEqual(w.get("low_risk", 0.0), 0.0)
            self.assertEqual(w.get("sentiment", 0.0), 0.0)

    #: NVDA's live 2026-10-12 attribution -- six themes, which is what Don saw.
    NVDA_WHY = ["size", "quality", "insider", "capital_discipline", "institutional", "value"]

    def test_NVDAs_two_absent_themes_have_NO_CAUSE_without_the_factor_row(self):
        """REPOINTED IN PART 7A, AND THE OLD ASSERTION WAS THE DEFECT.

        Part 4 pinned `_why_missing(why) == ["growth", "momentum"]`, i.e. it asserted that the
        attribution list ALONE establishes the cause. It does not: `row_attribution` drops a
        theme both when its contribution is NaN and when it is under 1e-6, and those mean
        opposite things. With no factor row to separate them the honest answer is that two
        themes are unexplained and we do not know why -- so `missing` is empty, `split_ok` is
        False, and the count is still reported.
        """
        from valuation.web import unified as U
        got = U._why_split([{"theme": t} for t in self.NVDA_WHY], None)
        self.assertFalse(got["split_ok"])
        self.assertEqual(got["missing"], [])
        self.assertEqual(got["zero"], [])
        self.assertEqual(got["n_explained"], 6)
        self.assertEqual(got["n_absent_unexplained"], 2)

    def test_with_the_factor_row_the_two_causes_SEPARATE(self):
        """The same six-theme attribution, now with the per-theme z-scores beside it.

        `growth` carries a value, so it was scored and simply moved this name by nothing;
        `momentum` does not, so its input really is absent. Part 4 called both "could not be
        scored", and the page said "had no input in this scan" about an input that was there.
        """
        from valuation.web import unified as U
        fac = {t: 0.4 for t in self.NVDA_WHY}
        fac["growth"] = 0.0          # scored, contribution rounds to zero
        fac["momentum"] = None       # never scored
        got = U._why_split([{"theme": t} for t in self.NVDA_WHY], fac)
        self.assertTrue(got["split_ok"])
        self.assertEqual(got["missing"], ["momentum"])
        self.assertEqual(got["zero"], ["growth"])
        # And the one-name read returns only the genuine gaps.
        self.assertEqual(U._why_missing([{"theme": t} for t in self.NVDA_WHY], fac),
                         ["momentum"])

    def test_the_live_scan_says_18_PERCENT_of_absences_were_SCORED(self):
        """The measurement that forced the correction, recorded so it cannot quietly rot.

        Over the live top 100 on 2026-10-12, 159 (row, theme) cells are absent from the
        explanation. `extra.factors` is non-null on 29 of them -- 18% -- so those themes WERE
        scored. Of the 130 genuinely unscored, 67 also carry a null `z_` column and 63 are
        themes the row exposes no `z_` column for.

        `factors` was checked as a discriminator rather than assumed to be one: it is non-null
        on all 641 attributed cells and on exactly those 29, with zero disagreements in 800
        cells. This test pins the arithmetic and the docstring that carries it.
        """
        self.assertEqual(29 + 130, 159)
        self.assertEqual(67 + 63, 130)
        self.assertAlmostEqual(29.0 / 159.0, 0.1824, places=3)
        src = _src(os.path.join("valuation", "web", "unified.py"))
        for bit in ("159 (row, theme) cells", "29 of them -- 18%",
                    "zero disagreements in 800"):
            self.assertIn(bit, src)

    def test_APLDs_live_attribution_is_missing_NOTHING(self):
        from valuation.web import unified as U
        apld = ["growth", "capital_discipline", "insider", "size", "value", "momentum",
                "institutional", "quality"]
        got = U._why_split([{"theme": t} for t in apld], {t: 0.3 for t in apld})
        self.assertEqual(got["missing"], [])
        self.assertEqual(got["zero"], [])
        self.assertTrue(got["split_ok"])
        # Nothing absent, so the factor row cannot change the answer either way.
        self.assertEqual(U._why_missing([{"theme": t} for t in apld], None), [])

    def test_an_EMPTY_attribution_returns_empty_rather_than_every_theme(self):
        """A name with no decomposition at all has not had eight themes go missing -- it has
        no explanation, which the surface reports differently. Returning all eight here would
        print "8 of the themes could not be scored" on a row that was never decomposed."""
        from valuation.web import unified as U
        self.assertEqual(U._why_missing([]), [])
        got = U._why_split([], {"growth": None})
        self.assertEqual((got["missing"], got["zero"], got["split_ok"]), ([], [], False))

    def test_the_page_reads_the_two_lists_DIFFERENTLY(self):
        """The copy is where the false claim actually reached a reader, so it is pinned here.

        "had no input in this scan" may appear ONLY in the `why_missing` branch, and the
        scored-but-zero branch must say the opposite in as many words -- that it is not a gap.
        """
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("function hotListStrip")
        body = src[i:src.index("function ", i + 30)]
        self.assertIn("why_zero", body)
        self.assertIn("why_split_ok", body)
        self.assertIn("moved this name by nothing", body)
        self.assertIn("That is not a gap in the data", body)
        # The unknowable case says so instead of guessing.
        self.assertIn("cannot be told apart here", body)
        # ONE occurrence of the old claim, and it sits after the `miss` branch opens and
        # before the `zero` branch does -- so it cannot be the sentence the zero list renders.
        self.assertEqual(body.count("had no input in this scan"), 1)
        self.assertLess(body.index("${miss.length ?"),
                        body.index("had no input in this scan"))
        self.assertLess(body.index("had no input in this scan"),
                        body.index("${zero.length ?"))

    def test_the_short_count_is_DERIVED_from_both_lists(self):
        """`8 - miss.length` was right when `miss` was everything absent and is wrong now --
        it would claim the explanation covers themes the zero list holds."""
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("const nShort = 8 - (miss.length + zero.length);", src)
        i = src.index("function hotListStrip")
        body = src[i:src.index("function ", i + 30)]
        self.assertNotIn("8 - miss.length", body)

    def test_the_page_renders_the_gap_and_the_not_in_scan_state(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("function hotListStrip", src)
        self.assertIn("why_missing", src)
        self.assertIn("Not in today's scan", src)
        # The limits are READ from `score_confidence`, not re-worded here.
        self.assertIn("SCORE_CONFIDENCE", src)
        self.assertIn("sc.defensible", src)

    def test_the_size_caveat_is_on_the_page_because_NVDA_needs_it(self):
        # NVDA scores 94.9 on business quality and ranks 1,262 of 1,440. Without this
        # sentence those two facts look like a contradiction rather than a design choice.
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("size is one of its themes", src)

    def test_the_top_strip_reads_the_SAME_payload_as_the_panel_below(self):
        """One source. Two reads of one ranking cannot come to disagree; two fetches can."""
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("STATE.whatdo = d;")
        tail = src[i:i + 200]
        self.assertIn("renderWhatDo(d)", tail)
        self.assertIn("hotListStrip(d)", tail)
        self.assertEqual(src.count("/api/whatdo?ticker="), 1)


class TheCompanyDescriptionOpensThePage(unittest.TestCase):
    """Part 5. The page carried NO description at all -- a reader could see a fair value, a
    1-100 score and nine theme contributions for a company they had been told nothing about.

    LIVE CHECK, 2026-10-13 (the COVERAGE RULE's "confirm it is populated"):
    `longBusinessSummary` returns 1,101 chars for NVDA, 732 for APLD, 1,817 for TSLA, 1,315
    for KO and 1,454 for JNJ -- so the field is populated for every name the prompt names.
    """

    def test_the_model_carries_the_summary_AND_its_source(self):
        from valuation.data.models import CompanyData
        cd = CompanyData(ticker="X")
        self.assertEqual(cd.business_summary, "")
        self.assertEqual(cd.business_summary_source, "")

    def test_an_absent_summary_leaves_the_SOURCE_empty_too(self):
        """A source stamp on an empty field is how a missing value comes to look measured."""
        src = _src(os.path.join("valuation", "data", "yahoo.py"))
        i = src.index("cd.business_summary = _summary")
        decl = src[i:i + 260]
        self.assertIn('if _summary else ""', decl)

    def test_the_FIGURES_are_the_engines_own_and_not_the_vendors(self):
        """Measured on NVDA today: the vendor's `revenueGrowth` reads 1.059 where the engine's
        own last-year revenue growth reads 0.77 -- different windows, both defensible, and a
        page carrying one in each box is a page that disagrees with itself."""
        src = _src(os.path.join("valuation", "web", "app.py"))
        i = src.index("def _company_profile_block")
        body = src[i:src.index("def _price_assumes_block")]
        self.assertIn("cd.revenue_growth(n)", body)
        # STRIPPED OF COMMENTS AND STRING LITERALS BEFORE THE BAN, and the first cut of this
        # test is why: it failed against a CORRECT tree because the docstring explaining why
        # the vendor's fields are NOT used names them. That is this repository's most repeated
        # test defect and the third time it has fired inside this one item. `tokenize` sees
        # code, not prose about code (`MB15`'s remedy).
        import io as _io
        import tokenize as _tok
        code = []
        for tk in _tok.generate_tokens(_io.StringIO(body).readline):
            if tk.type in (_tok.COMMENT, _tok.STRING):
                continue
            code.append(tk.string)
        code = " ".join(code)
        # THE STRIPPER IS PROVED NON-VACUOUS IN BOTH DIRECTIONS, or a stripper returning ""
        # would make the ban pass by seeing nothing.
        self.assertIn("revenue_growth", code)
        self.assertNotIn("different windows", code)
        for vendor_field in ("revenueGrowth", "operatingMargins", "totalRevenue", "marketCap"):
            self.assertNotIn(vendor_field, code)

    def test_the_margin_trend_is_two_endpoints_and_a_count_not_a_direction_word(self):
        import types
        from valuation.web import app as A
        cd = types.SimpleNamespace(business_summary="", business_summary_source="",
                                   sector="", industry="", market_cap=None,
                                   revenue_history=[], ebit_margin_history=[0.1, 0.3],
                                   revenue_growth=lambda n: None)
        t = A._company_profile_block(types.SimpleNamespace(company=cd))["operating_margin_trend"]
        self.assertEqual(t, {"from": 0.1, "to": 0.3, "n_years": 2})
        for word in ("improving", "worsening", "rising", "falling"):
            self.assertNotIn(word, str(t))

    def test_one_year_of_margin_history_is_not_rendered_as_a_trend(self):
        import types
        from valuation.web import app as A
        cd = types.SimpleNamespace(business_summary="", business_summary_source="",
                                   sector="", industry="", market_cap=None,
                                   revenue_history=[], ebit_margin_history=[0.22],
                                   revenue_growth=lambda n: None)
        t = A._company_profile_block(types.SimpleNamespace(company=cd))["operating_margin_trend"]
        self.assertEqual(t, {"from": None, "to": 0.22, "n_years": 1})

    def test_NO_margin_history_is_None_rather_than_a_flat_line(self):
        import types
        from valuation.web import app as A
        cd = types.SimpleNamespace(business_summary="", business_summary_source="",
                                   sector="", industry="", market_cap=None,
                                   revenue_history=[], ebit_margin_history=[],
                                   revenue_growth=lambda n: None)
        out = A._company_profile_block(types.SimpleNamespace(company=cd))
        self.assertIsNone(out["operating_margin_trend"])

    def test_the_page_renders_not_available_rather_than_a_dash(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("function companyProfile", src)
        self.assertIn("not available", src)
        self.assertIn("their words, not ours", src)

    def test_a_broken_block_says_so_rather_than_vanishing(self):
        import types
        from valuation.web import app as A
        out = A._company_profile_block(types.SimpleNamespace(company=None))
        self.assertFalse(out["ok"])
        self.assertIn("no company data", out["reason"])


class NoSLICEDFunctionNameMayBeEXTENDED(unittest.TestCase):
    """The defect this item caused once, pinned by the property that actually matters.

    `tests/test_accounting_risk.py` gets the hot-list renderer's body with
    `src.index("function renderHot")`. Part 4 added `renderHotTop` 700 lines EARLIER, so the
    slice returned the wrong function and five of its assertions failed against a correct
    `renderHot`. **A function whose name extends another's is the substring-ban family in an
    identifier.**

    **THE BLANKET RULE WAS WRITTEN FIRST AND REJECTED BY MEASUREMENT.** "No name may be a
    prefix of another" fires on **18 pre-existing pairs** in this file -- `render` alone is a
    prefix of thirteen -- and a guard that is red on arrival is one somebody deletes
    (`MA21`'s standard). None of those eighteen is a hazard, because no suite slices on
    `render` or `toggle`.

    So the rule is keyed on what suites ACTUALLY slice: every `function <name>` literal any
    test searches for must be unextended. That is the property, it fires only on real
    hazards, and it would have caught the real defect.
    """

    def _functions(self):
        import re
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        return sorted(set(re.findall(r"^\s*function\s+([A-Za-z_$][\w$]*)\s*\(",
                                     src, flags=re.M)))

    def _sliced_names(self):
        import re
        here = os.path.dirname(os.path.abspath(__file__))
        want = set()
        for fn in sorted(os.listdir(here)):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            with io.open(os.path.join(here, fn), encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            # ONLY NEEDLES WITHOUT THE OPENING PARENTHESIS ARE HAZARDS, and my first cut of
            # this guard got that wrong too. `test_allocation` slices on
            # `"function allocationSave("` -- WITH the paren -- so `allocationSaved()` cannot
            # match it: the `d` sits where the `(` is required. Reporting that pair was a
            # guard firing on the wrong property, in the very test written about guards
            # firing on the wrong property. A needle that stops at the NAME is the one that
            # can swallow a longer name.
            want |= set(re.findall(r'["\']function ([A-Za-z_$][\w$]*)["\']', src))
        return sorted(want)

    def test_every_name_a_suite_slices_on_is_UNEXTENDED(self):
        funcs, sliced = self._functions(), self._sliced_names()
        self.assertGreater(len(funcs), 30, funcs[:5])
        self.assertGreater(len(sliced), 0, "no suite slices this file -- has the idiom moved?")
        bad = [(n, f) for n in sliced for f in funcs if f != n and f.startswith(n)]
        self.assertEqual(bad, [], (
            "a suite slices `function %s` and another function extends that name, so the "
            "slice can return the wrong body: %s" % (sliced[0] if sliced else "?", bad)))

    def test_POSITIVE_CONTROL_the_rule_would_have_caught_the_real_defect(self):
        funcs = ["renderHot", "renderHotTop", "renderDip"]
        sliced = ["renderHot"]
        bad = [(n, f) for n in sliced for f in funcs if f != n and f.startswith(n)]
        self.assertEqual(bad, [("renderHot", "renderHotTop")])

    def test_the_blanket_rule_is_recorded_as_REJECTED_rather_than_forgotten(self):
        # Measured: 18 pre-existing pairs, so the wider rule would be red on arrival.
        funcs = self._functions()
        blanket = [(a, b) for a in funcs for b in funcs if a != b and b.startswith(a)]
        self.assertGreater(len(blanket), 10, blanket)


class TheAnalysisRunsByItselfAndItsCostIsMEASURED(unittest.TestCase):
    """Part 6. The cost was measured BEFORE anything was switched on, which was the
    precondition: ONE real call on TSLA, 2026-10-13, `claude-sonnet-5` --
    **1,154 input tokens and 2,253 output tokens, 27.4 seconds, $0.0248**, response parsed as
    JSON with `stop_reason: end_turn`. About 91% of that is OUTPUT, because the schema asks
    for eight fields including four multi-sentence theses. At the 30-a-day cap that is **~75
    cents a day and roughly $22 a month** at 30 billed days.

    The published price is Anthropic's own, read on the day: Sonnet 5 at **$2 / $10** per
    million, with the page's footnote stating the introductory pricing is now standard and the
    scheduled rise to $3/$15 will not happen -- quoted because the obvious mistake is to carry
    the announced increase.
    """

    def test_the_measured_call_prices_at_two_and_a_half_cents(self):
        from valuation.ai import analyst as AN
        self.assertAlmostEqual(AN.call_cost("claude-sonnet-5", 1154, 2253), 0.024838,
                               places=6)
        self.assertEqual(AN.PRICE_PER_MTOK["claude-sonnet-5"], {"in": 2.0, "out": 10.0})
        self.assertEqual(AN.PRICE_AS_OF, "2026-10-13")

    def test_an_unpriced_model_costs_None_rather_than_zero(self):
        """Zero would read as "this call was free", and a running total built on it would be
        wrong in the direction that spends money."""
        from valuation.ai import analyst as AN
        self.assertIsNone(AN.call_cost("some-future-model", 1000, 1000))
        self.assertIsNone(AN.call_cost("claude-sonnet-5", None, 1000))

    def test_the_cap_is_thirty_until_Don_sets_a_number(self):
        from valuation.web import ai_auto as AA
        self.assertEqual(AA.DAILY_CAP, 30)

    def test_a_fresh_day_may_run_and_a_recorded_call_spends_allowance(self):
        import tempfile, shutil
        from valuation.web import ai_auto as AA
        root = tempfile.mkdtemp(prefix="i52ai_")
        try:
            self.assertEqual(AA.allowance(root=root)["left"], 30)
            AA.record("TSLA", {"overall_take": "x",
                               "usage": {"cost_usd": 0.0248, "input_tokens": 1154,
                                         "output_tokens": 2253}}, root=root)
            a = AA.allowance(root=root)
            self.assertEqual(a["used"], 1)
            self.assertEqual(a["left"], 29)
            self.assertAlmostEqual(a["cost_usd_today"], 0.0248, places=4)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_cached_analysis_is_served_and_charges_NOTHING(self):
        import tempfile, shutil
        from valuation.web import ai_auto as AA
        root = tempfile.mkdtemp(prefix="i52ai_")
        try:
            AA.record("TSLA", {"overall_take": "x", "usage": {"cost_usd": 0.02}}, root=root)
            before = AA.allowance(root=root)["used"]
            self.assertIsNotNone(AA.cached("TSLA", root=root))
            self.assertEqual(AA.allowance(root=root)["used"], before)
            self.assertIsNone(AA.cached("NVDA", root=root))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_UNREADABLE_ledger_counts_as_AT_the_cap(self):
        """A ledger we cannot read cannot rule out that today's calls already happened, and
        the direction that does not spend money is the safe one (`MA6`)."""
        import tempfile, shutil
        from valuation.web import ai_auto as AA
        root = tempfile.mkdtemp(prefix="i52ai_")
        try:
            os.makedirs(AA._dir(root), exist_ok=True)
            with io.open(AA.ledger_path(root=root), "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            a = AA.allowance(root=root)
            self.assertFalse(a["may_run"])
            self.assertEqual(a["left"], 0)
            self.assertIn("could not be read", a["reason"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_route_is_POST_only_and_refuses_an_empty_ticker(self):
        """The verb carries the SPEND. A GET that could start a 27-second paid call is
        reachable by a retry, a prefetch, a crawler or a pasted link."""
        from valuation.web.app import app
        c = app.test_client()
        self.assertEqual(c.get("/api/ai-analysis").status_code, 405)
        self.assertEqual(c.post("/api/ai-analysis", json={}).status_code, 400)

    def test_the_route_is_classified_in_BOTH_posture_lists_with_a_reason(self):
        from valuation.saas import surfaces as SF
        self.assertIn("/api/ai-analysis", SF.PUBLIC_API)
        self.assertIn("/api/ai-analysis", SF.DEMO_DENIED_PATHS)
        src = _src(os.path.join("valuation", "saas", "surfaces.py"))
        self.assertIn("MEASURED at $0.0248", src)

    def test_the_panel_label_exists_once_and_reaches_the_page(self):
        from valuation.web import ai_auto as AA
        for bit in ("Written by AI", "not from news", "can be wrong"):
            self.assertIn(bit, AA.PANEL_LABEL)
        from valuation.web.app import app
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn("AI_PANEL_LABEL", html)
        self.assertIn("not from news", html)

    def test_aiBox_APPENDS_the_label_so_a_caller_cannot_forget_it(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("function aiBox(")
        body = src[i:src.index("function warnBox(")]
        self.assertIn("AI_PANEL_LABEL", body)
        self.assertIn("meta && meta.label", body)

    def test_it_is_fired_after_the_paint_and_NEVER_awaited(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("loadAiAnalysis(ticker);")
        line = src[src.rindex("\n", 0, i) + 1:i + 30]
        self.assertNotIn("await", line)
        self.assertLess(src.index("render(data);"), i)

    def test_the_cap_OFFERS_the_button_rather_than_showing_nothing(self):
        from valuation.web import ai_auto as AA
        self.assertIn("You can still run this one", AA.CAP_REACHED)
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("Run it", src)
        self.assertIn("force: !!force", src)

    def test_THIS_MODULE_NEVER_TOUCHES_THE_KEY(self):
        """It decides WHETHER to call and records WHAT it cost. The credential stays in
        `valuation.ai.analyst`, the only place that needs it."""
        src = _src(os.path.join("valuation", "web", "ai_auto.py"))
        for forbidden in ("api_key", "anthropic_api_key", "openai_api_key", "ANTHROPIC"):
            self.assertNotIn(forbidden, src)

    def test_the_route_CHARGES_BOTH_scarce_buckets_unconditionally(self):
        """`test_vendor_quota` caught this on the gate and it was right: the route runs a FULL
        valuation on a caller-supplied symbol, so it spends the owner's market-data quota, AND
        a paid Anthropic call. It is scarce in both of the ways `ratelimit` tracks.

        It shares `ai:value` rather than taking a bucket of its own, because the scarce thing
        is the spend and not the URL -- two buckets over one budget is two caps that each think
        they are the limit. The day's 30-call cap is a DIFFERENT control (the day's money,
        across all callers) and both apply.
        """
        from valuation.saas.ratelimit import buckets_for, VENDOR_BUCKET
        got = dict(buckets_for("/api/ai-analysis", {}))
        self.assertEqual(got.get(VENDOR_BUCKET), 1)
        self.assertEqual(got.get("ai:value"), 1)
        # Unconditional: unlike /api/value, there is no opt-in flag that could leave the paid
        # call uncharged.
        self.assertEqual(dict(buckets_for("/api/ai-analysis", {"run_ai": False})), got)
        self.assertEqual(dict(buckets_for("/api/ai-analysis", None)), got)

    def test_nothing_reports_a_cost_without_saying_it_may_be_PARTIAL(self):
        src = _src(os.path.join("valuation", "web", "ai_auto.py"))
        self.assertIn("cost_is_partial", src)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    print("\nitem 52 part 1 (no label): %d run, %d failures, %d errors"
          % (r.testsRun, len(r.failures), len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
