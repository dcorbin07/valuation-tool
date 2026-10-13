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


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    print("\nitem 52 part 1 (no label): %d run, %d failures, %d errors"
          % (r.testsRun, len(r.failures), len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
