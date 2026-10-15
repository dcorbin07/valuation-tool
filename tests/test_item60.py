# -*- coding: utf-8 -*-
"""ITEM 60 — the valuation-verdict headline, and the page ordered most to least relevant.

THE TEST THAT MATTERS MOST is `AFiredWarningOutranksAVerdict`. It exists because my own live
check caught the defect: AAPL, TSLA and NVDA all carry *"Do not use the fair value below to
decide on this company"*, and the first cut of this card printed a 26px verdict computed from
exactly that value directly above it. That is item 52's defect re-created at larger type.

THE BANNED VOCABULARY IS CHECKED AGAINST THE RENDERED PAYLOAD, never against a source file --
`dip_posture.py`'s design, for its reason: rendering is where copy leaks, and a source-level ban
passes happily while a template builds "price target" out of two permitted words.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.web import valuation_verdict as V   # noqa: E402

TPL = os.path.join(REPO, "valuation", "web", "templates", "index.html")
APPJS = os.path.join(REPO, "valuation", "web", "static", "app.js")


def _tpl():
    with open(TPL, encoding="utf-8") as fh:
        return fh.read()


def _js():
    with open(APPJS, encoding="utf-8") as fh:
        return fh.read()


class TheRule(unittest.TestCase):
    """Price against the model's own bear/base/bull range, and nothing else."""

    def test_below_bear_is_undervalued(self):
        self.assertEqual(V.classify(90, 100, 200), V.UNDER)

    def test_above_bull_is_overvalued(self):
        self.assertEqual(V.classify(210, 100, 200), V.OVER)

    def test_between_is_fairly_valued(self):
        self.assertEqual(V.classify(150, 100, 200), V.FAIR)

    def test_exactly_on_a_boundary_is_FAIR_on_both_sides(self):
        """A price exactly at the bear value is INSIDE the range, not below it -- so a name
        sitting on a boundary does not flip verdict on the last cent."""
        self.assertEqual(V.classify(100, 100, 200), V.FAIR)
        self.assertEqual(V.classify(200, 100, 200), V.FAIR)

    def test_a_missing_leg_refuses_rather_than_guessing(self):
        for args in ((None, 100, 200), (150, None, 200), (150, 100, None), (0, 100, 200)):
            self.assertIsNone(V.classify(*args), args)

    def test_a_MALFORMED_range_refuses_instead_of_swapping_the_legs(self):
        """bear above bull is a broken input. Silently swapping would turn a bug into a
        confident verdict, which is the direction that cannot be noticed."""
        self.assertIsNone(V.classify(150, 300, 100))

    def test_the_rule_is_ON_the_card(self):
        """A verdict whose rule is hidden is a recommendation wearing a measurement's clothes."""
        h = V.headline(ticker="X", price=150, bear=100, base=150, bull=200, confidence="high")
        self.assertIn("below the bear value", h["rule"])
        self.assertIn("not advice", h["rule"])

    def test_every_verdict_string_says_VS_OUR_MODEL(self):
        """It is not decoration: it is the whole claim. The model is one model and it has been
        wrong, and the phrase is what keeps the sentence honest."""
        for key in (V.UNDER, V.FAIR, V.OVER):
            self.assertIn("vs our model", V.LABEL[key])


class TheRangeText(unittest.TestCase):
    def test_it_reads_as_the_brief_asks(self):
        self.assertEqual(V.range_text(247.86916, 323.89722, 424.70621),
                         "$248–$425 (base $324)")

    def test_whole_dollars_because_a_range_has_no_cents_of_precision(self):
        self.assertEqual(V.money0(838.804), "$839")
        self.assertEqual(V.money0(1234567), "$1,234,567")
        self.assertEqual(V.money0(None), "—")

    def test_an_en_dash_and_not_a_hyphen(self):
        """It is a range, not a subtraction."""
        self.assertIn("–", V.range_text(1, 2, 3))

    def test_a_missing_base_still_gives_a_range(self):
        self.assertEqual(V.range_text(100, None, 200), "$100–$200")


class TheFiveNoVerdictCauses(unittest.TestCase):
    """Each fires alone, and each gives its OWN reason -- "we withheld the value" and "we could
    not value it" are different facts for a reader."""

    BASE = dict(ticker="X", price=150, bear=100, base=150, bull=200, confidence="high")

    def test_withheld(self):
        h = V.headline(withheld=999.0, **self.BASE)
        self.assertEqual(h["verdict"], V.NONE)
        self.assertEqual(h["no_verdict_cause"], "withheld")
        self.assertIn("do not trust it", h["no_verdict_reason"])

    def test_not_valuable(self):
        h = V.headline(valuable=False, **self.BASE)
        self.assertEqual(h["no_verdict_cause"], "not_valuable")

    def test_low_reliability(self):
        h = V.headline(dcf_reliability="low", **self.BASE)
        self.assertEqual(h["no_verdict_cause"], "low_reliability")

    def test_a_fired_model_warning(self):
        h = V.headline(warning={"warn": True, "why": ["the price already assumes far more "
                                                      "growth than this business has shown"]},
                       **self.BASE)
        self.assertEqual(h["no_verdict_cause"], "model_warns")

    def test_no_price(self):
        h = V.headline(ticker="X", price=None, bear=100, base=150, bull=200)
        self.assertEqual(h["no_verdict_cause"], "no_price")

    def test_no_range(self):
        h = V.headline(ticker="X", price=150, bear=None, base=150, bull=None)
        self.assertEqual(h["no_verdict_cause"], "no_range")

    def test_the_label_is_the_same_card_and_not_a_hidden_one(self):
        """"We are not publishing a verdict, and here is why" IS a read. An absent card is
        indistinguishable from a page that failed to load."""
        h = V.headline(valuable=False, **self.BASE)
        self.assertEqual(h["label"], "No valuation verdict")
        self.assertTrue(h["no_verdict_reason"])

    def test_a_financials_reason_does_not_claim_a_DCF_was_used(self):
        """KNSL's regime is `financial` and a financial is valued on justified price-to-book
        from ROE -- NOT a cash-flow model. A reason saying "DCF reliability is low" would
        misdescribe the method, and a reason that misdescribes is worse than a shorter one."""
        h = V.headline(dcf_reliability="low", regime="financial", **self.BASE)
        r = h["no_verdict_reason"]
        self.assertIn("justified price-to-book", r)
        self.assertIn("not a cash-flow model", r)


class AFiredWarningOutranksAVerdict(unittest.TestCase):
    """**THE DEFECT MY OWN LIVE CHECK FOUND, AND THE MOST IMPORTANT TEST HERE.**

    Measured live 2026-10-14: AAPL, TSLA and NVDA all carry
    `price_assumes.warning.warn = True`, whose headline is "Do not use the fair value below to
    decide on this company." The first cut of this card published a verdict computed from
    exactly that value -- NVDA read "Fairly valued vs our model" in 26px directly above the box
    disclaiming it. Item 52's own note on this page records the shape it repeats: a correct
    number, a correct badge, and the three together telling a reader to trust a number at -94%
    of the price.
    """

    def test_a_warning_beats_a_computable_verdict(self):
        h = V.headline(ticker="NVDA", price=221.3, bear=93, base=146, bull=232,
                       confidence="medium",
                       warning={"warn": True, "headline": "Do not use the fair value below "
                                                          "to decide on this company.",
                                "why": ["Almost all of this company's value is growth that "
                                        "has not happened yet"]})
        self.assertEqual(h["verdict"], V.NONE,
                         "a verdict was published off a value the page disclaims")
        self.assertNotIn("Fairly valued", h["label"])

    def test_without_the_warning_the_same_numbers_DO_get_a_verdict(self):
        """The positive control. Without it the test above would pass on any always-no-verdict
        card and prove nothing."""
        h = V.headline(ticker="NVDA", price=221.3, bear=93, base=146, bull=232,
                       confidence="medium", warning={"warn": False})
        self.assertEqual(h["verdict"], V.FAIR)

    def test_the_reason_carries_the_TRIGGERS_own_words(self):
        """`dcf_warning` already composes a per-trigger `why`, so the reader learns WHICH rule
        fired and the wording is not duplicated here."""
        h = V.headline(ticker="X", price=150, bear=100, base=150, bull=200,
                       warning={"warn": True,
                                "why": ["the price already assumes far more growth than this "
                                        "business has shown"]})
        self.assertIn("far more growth than this business has shown",
                      h["no_verdict_reason"])

    def test_the_range_is_STILL_shown_when_the_verdict_is_withheld(self):
        """Withholding the verdict is not a reason to withhold numbers a reader can judge for
        themselves."""
        h = V.headline(ticker="X", price=150, bear=100, base=150, bull=200,
                       warning={"warn": True, "why": ["x"]})
        self.assertEqual(h["range_text"], "$100–$200 (base $150)")


class TheBriefsOwnWorkedExamples(unittest.TestCase):
    """Committed literals (`MA13`), from the LIVE payloads measured 2026-10-14. A change to any
    of these numbers is a change to what the page says, and it must show in a diff."""

    #: MSFT, live 2026-10-14. `warn` is False, which is WHY it still gets a verdict -- measured
    #: before the warning rule was added rather than hoped for afterwards.
    MSFT = dict(price=533.69, bear=247.86916311878696, base=323.89721935305124,
                bull=424.70620644744474, confidence="high", dcf_reliability="high",
                regime="growth", warn=False)

    #: KNSL, live 2026-10-14. valuable=True and NOT withheld -- so a withheld-only rule would
    #: have read "Fairly valued". It is `dcf_reliability: low` that makes it a no-verdict name.
    KNSL = dict(price=349.07, bear=230.81073746084826, base=298.3714846179234,
                bull=365.9322317749986, confidence="medium", dcf_reliability="low",
                regime="financial", warn=True)

    def test_MSFT_reads_exactly_what_the_brief_requires(self):
        m = self.MSFT
        h = V.headline(ticker="MSFT", price=m["price"], bear=m["bear"], base=m["base"],
                       bull=m["bull"], confidence=m["confidence"],
                       dcf_reliability=m["dcf_reliability"], regime=m["regime"],
                       warning={"warn": m["warn"]})
        line = "%s · %s · confidence %s" % (h["label"], h["range_text"],
                                                      h["confidence"])
        self.assertEqual(line, "Overvalued vs our model · $248–$425 (base $324) "
                               "· confidence high")

    def test_KNSL_reads_no_valuation_verdict_with_the_reason(self):
        k = self.KNSL
        h = V.headline(ticker="KNSL", price=k["price"], bear=k["bear"], base=k["base"],
                       bull=k["bull"], confidence=k["confidence"],
                       dcf_reliability=k["dcf_reliability"], regime=k["regime"],
                       warning={"warn": k["warn"]})
        self.assertEqual(h["label"], "No valuation verdict")
        self.assertTrue(h["no_verdict_reason"])

    def test_KNSL_is_NOT_a_withheld_name_which_is_why_the_rule_needs_three_limbs(self):
        """A withheld-only rule gets KNSL wrong: on the range alone its price sits INSIDE the
        range, so it would have read "Fairly valued"."""
        k = self.KNSL
        self.assertEqual(V.classify(k["price"], k["bear"], k["bull"]), V.FAIR)


class TheBannedVocabulary(unittest.TestCase):
    """**ASSERTED AGAINST THE RENDERED PAYLOAD.** Don's 2026-10-13 removal of Buy/Hold/Reduce
    and the site being educational."""

    def _cards(self):
        out = []
        for kw in (dict(price=150, bear=100, base=150, bull=200, confidence="high"),
                   dict(price=90, bear=100, base=150, bull=200, confidence="medium"),
                   dict(price=250, bear=100, base=150, bull=200, confidence="low"),
                   dict(price=150, bear=100, base=150, bull=200, withheld=9e9),
                   dict(price=150, bear=100, base=150, bull=200, dcf_reliability="low",
                        regime="financial"),
                   dict(price=150, bear=100, base=150, bull=200,
                        warning={"warn": True, "headline": "Do not use the fair value below "
                                                           "to decide on this company.",
                                 "why": ["x"]})):
            out.append(V.headline(ticker="X", name="Example Inc",
                                  business_quality="Outstanding business",
                                  price_vs_model="Priced 65% above our base value.",
                                  assumes_sentence="The price assumes 23% growth a year.",
                                  **kw))
        return out

    def test_no_card_in_any_state_carries_a_banned_word(self):
        for card in self._cards():
            bad = V.contains_banned(json.dumps(card))
            self.assertEqual(bad, [], "%r in %r" % (bad, card["label"]))

    def test_the_ban_is_on_WORDS_and_tolerates_legitimate_prose(self):
        """A substring ban on "buy" flags "buyback"; on "hold" it flags "shareholder". This
        project's most repeated test defect is a substring ban firing on correct prose, so the
        exceptions are NAMED rather than the ban loosened.

        **MY FIRST EXPECTATION HERE WAS WRONG AND THE CODE WAS RIGHT.** I asserted that
        "buybacks reduced the shareholder count" would flag `reduce`. It does not, and it
        should not: `reduce` is banned as the RATING WORD -- one of the three Don removed on
        2026-10-13 -- and "reduced the share count" is ordinary prose about a buyback. A
        word-boundary match does not fire on "reduced", which is the whole point of matching on
        boundaries.
        """
        self.assertEqual(V.contains_banned("buybacks reduced the shareholder count"), [])
        self.assertEqual(V.contains_banned("holdings of buyers and households"), [])
        self.assertEqual(V.contains_banned("selling, general and administrative costs"), [])

    def test_and_the_RATING_words_themselves_still_fire(self):
        """The companion to the test above, and without it that one is just a list of things
        that do not fire. These are the three labels Don removed on 2026-10-13."""
        self.assertEqual(V.contains_banned("Rating: Reduce"), ["reduce"])
        self.assertEqual(V.contains_banned("Rating: Hold"), ["hold"])
        self.assertIn("buy", V.contains_banned("Strong Buy"))

    def test_the_ban_CATCHES_a_real_leak(self):
        """The positive control. Without it the sweep above passes by matching nothing."""
        hits = V.contains_banned("Our price target is $400 and you should buy it now")
        self.assertIn("buy", hits)
        self.assertIn("price target", hits)

    def test_it_catches_a_leak_composed_across_the_payload(self):
        """The reason the ban is on the RENDERED payload: a template can build a forbidden
        phrase out of two permitted halves, and no source-level check sees that."""
        card = {"a": "our price", "b": "target is $400"}
        self.assertIn("price target", V.contains_banned(" ".join(card.values())))

    def test_the_module_states_the_source_of_its_wording(self):
        self.assertIn("2026-10-14", V.SOURCE)
        self.assertIn("not", V.SOURCE.lower())


class TheModuleOnlyRenders(unittest.TestCase):
    def test_it_imports_no_engine_module(self):
        """Item 60 is layout and wording only. A card that could value anything would be a
        second valuation path, and the two would drift."""
        with open(V.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        mods = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods += [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                mods.append(n.module or "")
        bad = [m for m in mods if "engine" in (m or "") or "pipeline" in (m or "")]
        self.assertEqual(bad, [])

    def test_it_does_not_recompute_the_assumes_sentence(self):
        """`price_assumes()` already composes it, including the financial branch. A second copy
        is two definitions of one sentence (`B7`)."""
        with open(V.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("assumes_sentence", src)
        self.assertNotIn("The price assumes this company earns", src)


class TheConfidenceIsTheBlendsAndNotTheScores(unittest.TestCase):
    """They genuinely differ. Measured live on KNSL: `score.confidence` is "low" while
    `fair_value_blend.confidence` is "medium". The card's range IS the blend's range, so
    labelling it with the confidence in a DIFFERENT quantity is the wrong-object family."""

    def test_the_payload_builder_prefers_the_blend(self):
        with open(os.path.join(REPO, "valuation", "web", "app.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("def _headline_block(")
        body = src[i:i + 4000]
        self.assertIn('getattr(blend, "confidence", "")', body)
        self.assertIn("NOT THE SCORE'S", body)

    def test_each_confidence_label_is_explained(self):
        for label in ("high", "medium", "low"):
            self.assertTrue(V.CONFIDENCE_MEANS[label])
        h = V.headline(ticker="X", price=150, bear=100, base=150, bull=200, confidence="medium")
        self.assertIn("estimated", h["confidence_means"])

    def test_an_unknown_confidence_explains_nothing_rather_than_guessing(self):
        h = V.headline(ticker="X", price=150, bear=100, base=150, bull=200, confidence="??")
        self.assertEqual(h["confidence_means"], "")


class ThePageOrder(unittest.TestCase):
    """Item 60 part 2. Asserted on POSITION IN THE TEMPLATE, which is what decides what a
    reader sees first."""

    def setUp(self):
        self.src = _tpl()

    def _at(self, needle):
        self.assertIn(needle, self.src, needle)
        return self.src.index(needle)

    def test_the_headline_card_is_first(self):
        first = self._at('id="headlineCard"')
        for later in ('id="coProfile"', 'id="scoreBars"', 'id="aiCard"', 'id="earnCard"',
                      'id="hotTop"', 'id="sensBox"', 'id="assumEditor"'):
            self.assertLess(first, self._at(later), "%s precedes the headline card" % later)

    def test_the_range_bar_comes_second(self):
        self.assertLess(self._at('id="rangebar"'), self._at('id="coProfile"'))

    def test_what_the_company_does_precedes_the_score_bars(self):
        self.assertLess(self._at('id="coProfile"'), self._at('id="scoreBars"'))

    def test_the_score_bars_precede_the_AI_analysis(self):
        self.assertLess(self._at('id="scoreBars"'), self._at('id="aiCard"'))

    def test_the_AI_analysis_precedes_the_earnings_card(self):
        self.assertLess(self._at('id="aiCard"'), self._at('id="earnCard"'))

    def test_the_earnings_card_precedes_the_hot_list(self):
        self.assertLess(self._at('id="earnCard"'), self._at('id="hotTop"'))

    def test_announcements_sit_WITH_the_earnings_card(self):
        """The brief's item 6 is earnings, the company's own announcements and headlines --
        which is `earnBox` plus `recentBox`, and they sat in two different cards."""
        self.assertLess(self._at('id="earnBox"'), self._at('id="recentBox"'))
        self.assertLess(self._at('id="recentBox"'), self._at('id="hotTop"'))

    def test_recentBox_is_no_longer_inside_the_hero(self):
        hero = self._at('id="coName"')
        metrics = self._at('id="heroMetrics"')
        between = self.src[hero:metrics]
        self.assertNotIn('id="recentBox"', between)

    def test_the_disclaimer_is_last(self):
        self.assertLess(self._at('id="sourcesBox"'), self._at('class="disclaimer"'))


class TheFullModelControl(unittest.TestCase):
    def setUp(self):
        self.src, self.js = _tpl(), _js()

    def _inside_full_model(self, needle):
        i = self.src.index('id="fullModel"')
        j = self.src.index('class="disclaimer"')
        return needle in self.src[i:j]

    def test_items_8_to_10_sit_behind_it(self):
        for needle in ('id="mcChart"', 'id="fcfChart"', 'id="compsBox"', 'id="reverseBox"',
                       'id="sensBox"', 'id="assumEditor"', 'id="sourcesBox"',
                       'id="warnBox"'):
            self.assertTrue(self._inside_full_model(needle), needle)

    def test_items_1_to_7_do_NOT(self):
        for needle in ('id="headlineCard"', 'id="rangebar"', 'id="coProfile"',
                       'id="scoreBars"', 'id="aiCard"', 'id="earnCard"', 'id="hotTop"'):
            self.assertFalse(self._inside_full_model(needle), needle)

    def test_it_starts_collapsed(self):
        self.assertIn('id="fullModel" style="display:none"', self.src)

    def test_it_REMEMBERS_its_state(self):
        """The brief asks for this. `localStorage` rather than a session flag, so the choice
        survives a reload and a new tab: re-collapsing on every search is the behaviour that
        makes a control abandoned."""
        self.assertIn("FULL_MODEL_KEY", self.js)
        self.assertIn("localStorage.setItem(FULL_MODEL_KEY", self.js)
        self.assertIn("localStorage.getItem(FULL_MODEL_KEY)", self.js)

    def _function_body(self, name):
        """A function's WHOLE body, found by brace depth.

        **NOT A CHARACTER WINDOW.** My first version of the test below searched 2,500
        characters from the start of `render()` and failed against correct code because the
        call sits further in. A window is a guess about length that rots the moment anything
        above it grows, and this project has paid for that guess repeatedly -- including once
        already this session, in `test_item57a`.
        """
        i = self.js.index("function %s(" % name)
        j = self.js.index("{", i)
        depth, k = 0, j
        while k < len(self.js):
            if self.js[k] == "{":
                depth += 1
            elif self.js[k] == "}":
                depth -= 1
                if depth == 0:
                    return self.js[i:k + 1]
            k += 1
        raise AssertionError("unbalanced braces reading %s()" % name)

    def test_the_body_reader_is_not_vacuous(self):
        """A POSITIVE CONTROL for the reader above: if it returned the whole file, every
        assertion built on it would pass by seeing everything."""
        body = self._function_body("applyFullModel")
        self.assertIn("FULL_MODEL_KEY", self.js)
        self.assertNotIn("function render(d)", body)
        self.assertLess(len(body), len(self.js) // 4)

    def test_the_remembered_state_is_RE_APPLIED_on_every_render(self):
        """`render()` replaces the cards inside the box, so without this a reader who had
        opened it finds it shut again after every search."""
        self.assertIn("applyFullModel(fullModelOpen())", self._function_body("render"))

    def test_a_private_window_does_not_break_it(self):
        """`localStorage` throws in some privacy modes. The control must still open."""
        self.assertIn("catch (e) { return false; }", self.js)

    def test_the_button_is_bound_and_labelled_for_a_screen_reader(self):
        self.assertIn('onclick="toggleFullModel()"', self.src)
        self.assertIn('aria-expanded="false"', self.src)
        self.assertIn('aria-controls="fullModel"', self.src)
        self.assertIn('aria-expanded', self.js)

    def test_opening_it_recomputes_nothing(self):
        """A control that deferred rendering would make the charts appear empty on first open --
        a bug this page has already had once, which is why `mcChart` has an empty-histogram
        branch at all. Read on the FUNCTION, not a byte window."""
        body = self._function_body("applyFullModel") + self._function_body("toggleFullModel")
        for recompute in ("runValue(", "fcfChart(", "mcChart(", "fetch("):
            self.assertNotIn(recompute, body)


class TheCardRendersFromThePayloadOnly(unittest.TestCase):
    def test_the_verdict_strings_are_not_retyped_in_javascript(self):
        """The `score_confidence` pattern: a surface that writes its own version of a sentence
        is how one claim comes to have two wordings on one page."""
        js = _js()
        i = js.index("function headlineCard(")
        body = js[i:js.index("function fullModelOpen(")]
        for owned in ("Undervalued vs our model", "Fairly valued vs our model",
                      "Overvalued vs our model", "No valuation verdict"):
            self.assertNotIn(owned, body, "%r is retyped in app.js" % owned)

    def test_it_renders_the_rule_the_payload_supplies(self):
        js = _js()
        self.assertIn("h.rule", js)

    def test_a_no_verdict_name_still_gets_a_card(self):
        js = _js()
        i = js.index("function headlineCard(")
        body = js[i:i + 3000]
        self.assertIn("h.no_verdict_reason", body)

    def test_every_third_party_string_is_escaped(self):
        """Company names are third-party strings dropped into innerHTML."""
        js = _js()
        i = js.index("function headlineCard(")
        body = js[i:js.index("function fullModelOpen(")]
        self.assertIn("esc(name)", body)
        self.assertIn("esc(h.label)", body)
        # And no un-escaped interpolation of a payload string.
        bad = re.findall(r"\$\{h\.(label|name|gap|rule|price_assumes|warning)\}", body)
        self.assertEqual(bad, [], "un-escaped payload strings: %r" % bad)


if __name__ == "__main__":
    unittest.main()
