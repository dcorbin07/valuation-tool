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
from valuation.web import dip                      # noqa: E402

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


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    print("\nitem 52 part 1 (no label): %d run, %d failures, %d errors"
          % (r.testsRun, len(r.failures), len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
