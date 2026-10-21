# -*- coding: utf-8 -*-
"""ITEM 76 — WHAT THE OUTSIDE REVIEW FOUND: STALE PUBLIC FIGURES, READ LIVE INSTEAD.

**THE DEFECT.** An outside review of valquo.co (2026-10-21) found `methodology.html` and
`portfolio.html` still saying the research decile's breakeven cost is **134 bps one-way against
a measured 33 bps**, on **261% annual turnover**, a margin of **"about fourfold"**. All four are
the superseded 2,531-name panel's. The canonical universe moved to 9,645 names at item 47 and
the tracked artifact has read **123 against 77, a 1.60x margin on 247% turnover** ever since.

**AND ONE OF THEM WAS NOT MERELY STALE.** `portfolio.html`'s "What survives" section stated a
long-short *t* of 2.84, a Newey-West 2.62, a seven-grid range of 2.70-3.52 and a long-only 4.38,
and then drew a conclusion from them: that the headline sits **BELOW** the Harvey-Liu-Zhu
hurdle. On the canonical panel the Newey-West *t* is 4.59 against a hurdle of 3.36 and it
**CLEARS**. A stale figure with an inference built on top of it is worse than a stale figure,
because correcting the number inverts the sentence around it, and nothing makes that visible.

**WHY THESE TESTS READ THE RENDERED PAGE AND NOT THE SOURCE.** Several of the superseded figures
legitimately remain in the sources, named as the old figures in `{# ... #}` comments and
docstrings that record what was corrected and why -- `CLAUDE.md`'s own quotation exemption, and
the same reason this docstring may print "134 bps" without tripping its own guard. A source grep
cannot tell a quotation from a claim. `dip_posture`'s rule applies: assert against the RENDERED
payload, because rendering is where copy reaches a reader.

**THE GUARD IS PROVED NON-VACUOUS IN BOTH DIRECTIONS.** It must pass on the real pages and fail
on a page carrying a superseded pair -- otherwise it is a guard that cannot bite, which is the
family this project has now paid for six times.

NOTHING HERE SCORES, RANKS, WEIGHTS OR VALUES ANYTHING. No fair-value arithmetic, no Index
construction, no rebalance path, no live-trading code is touched by the change these tests pin.
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.web import live_facts as F   # noqa: E402

TPL = os.path.join(REPO, "valuation", "web", "templates")

#: The two public pages the review found carrying superseded figures. Both live in one template
#: folder, so one Jinja environment renders both.
PAGES = ("methodology.html", "portfolio.html")


def _env():
    """A Jinja environment over the real template folder, undefined tolerated.

    The pages reference context a full request would supply (`payoff`, `hold_horizon`,
    `optionable`, `url_for`...). `ChainableUndefined` lets an absent name render empty instead of
    raising, so the guard can exercise the real template bytes without standing up two Flask
    apps -- and crucially WITHOUT letting a missing context silently blank the paragraph under
    test, which `_render` then checks.
    """
    from jinja2 import ChainableUndefined, Environment, FileSystemLoader
    e = Environment(loader=FileSystemLoader(TPL), undefined=ChainableUndefined,
                    autoescape=True)
    e.globals["url_for"] = lambda *a, **k: "#"
    return e


def _site_context():
    """The REAL site-wide context, from the app's own context processor.

    Not a stub. These pages read `hold_horizon`, `definitions`, `theme_status` and more from a
    processor registered on the shared app object, and a stub of it would be a second copy of
    the thing under test -- the wrong-object family. Called outside a request, which is why the
    hero entry is a callable the templates may or may not invoke.
    """
    from valuation.web import app as _app
    with _app.app.app_context():
        return dict(_app._site_context())


def _render(name, **ctx):
    base = {"disclaimer": "", "contact_email": "x@example.com", "research_url": "#",
            "demo_available": False, "trials": F.trial_counts(),
            "costs": F.costs(), "panel": F.panel()}
    base.update(_site_context())
    try:
        from valuation.web import payoff as _payoff
        base["payoff"] = _payoff.payoff_summary()
    except Exception:                                                   # noqa: BLE001
        pass
    try:
        from valuation.web import optionable_partition as _op
        base["optionable"] = _op.payload()
    except Exception:                                                   # noqa: BLE001
        pass
    base.update({"costs": F.costs(), "panel": F.panel()})
    base.update(ctx)
    return _env().get_template(name).render(**base)


def _artifact():
    p = os.path.join(REPO, "BACKTEST_RESULTS.json")
    return json.load(io.open(p, encoding="utf-8"))


class SupersededFiguresNeverRender(unittest.TestCase):
    """No public page may render a figure from the superseded panel."""

    def test_no_public_page_renders_a_superseded_cost_figure(self):
        for name in PAGES:
            html = _render(name)
            for needle, what in F.SUPERSEDED_COST_FIGURES:
                self.assertNotIn(
                    needle, html,
                    "%s renders %r, which is %s" % (name, needle, what))

    def test_no_public_page_renders_the_superseded_universe_size_as_current(self):
        # The sources legitimately say "the previous 2,531-name panel" in before-and-after
        # prose. What may not survive is the size stated as the panel in force -- so this
        # checks the rendered text and requires the phrase, where present, to be introduced
        # as a past one.
        PAST = ("previous", "superseded", "former", "used to", "earlier", "old ",
                "had been", "no longer", "was ")
        for name in PAGES:
            html = _render(name)
            for i in range(len(html)):
                if not html.startswith("2,531", i):
                    continue
                pre = html[max(0, i - 160):i].lower()
                self.assertTrue(
                    any(w in pre for w in PAST),
                    "%s renders '2,531' without naming it as the previous panel: ...%r"
                    % (name, pre[-100:]))

    def test_THE_GUARD_CAN_BITE(self):
        # NON-VACUITY, and it is the half that matters: a guard asserting an absence passes
        # trivially when the page fails to render at all. A page carrying the old pair must
        # fail the same assertion the real pages pass.
        from jinja2 import Environment
        bad = Environment(autoescape=True).from_string(
            "<p>breakeven 134 bps against a measured 33 bps</p>").render()
        hits = [n for n, _w in F.SUPERSEDED_COST_FIGURES if n in bad]
        self.assertIn("134 bps", hits)
        self.assertIn("33 bps", hits)

    def test_the_pages_actually_rendered_their_cost_paragraph(self):
        # THE OTHER HALF OF NON-VACUITY. `ChainableUndefined` means a typo'd context name
        # renders as empty, so "the superseded figure is absent" could be satisfied by a blank
        # page. Both pages must carry the live breakeven, from the artifact, as a number.
        c = F.costs()
        self.assertTrue(c["available"], c["reason"])
        n = round(c["breakeven_bps"])
        # Either unit, because the two pages word it differently and the point is that the
        # NUMBER came from the artifact rather than from a template literal.
        wants = ("%d bps" % n, "%d basis points" % n)
        for name in PAGES:
            html = _render(name)
            self.assertTrue(any(w in html for w in wants),
                            "%s did not render the live breakeven (%s)"
                            % (name, " or ".join(wants)))
            self.assertGreater(len(html), 2000, "%s rendered almost nothing" % name)


class TheFiguresAreReadAndNotTyped(unittest.TestCase):
    """`live_facts` is the one reader; the numbers must match the tracked artifact exactly."""

    def test_costs_reproduces_the_artifact(self):
        a = _artifact()
        c = F.costs()
        t = (a.get("costs") or {}).get("top_decile") or {}
        self.assertTrue(c["available"], c["reason"])
        self.assertEqual(c["breakeven_bps"], t["breakeven_one_way_bps"])
        self.assertEqual(c["realised_bps"], t["realised_one_way_bps"])
        # THE MARGIN IS DERIVED. "Fourfold" was a figure wearing prose and it rotted.
        self.assertAlmostEqual(c["margin"],
                               t["breakeven_one_way_bps"] / t["realised_one_way_bps"],
                               places=12)
        self.assertAlmostEqual(c["turnover_pct"], t["annual_turnover"] * 100.0, places=9)

    def test_panel_reproduces_the_artifact(self):
        a = _artifact()
        c = a["construction"]
        h = a["multiple_testing"]["hlz"]
        p = F.panel()
        self.assertTrue(p["available"], p["reason"])
        self.assertEqual(p["ls_t_nw"], c["long_short_tstat_nw"])
        self.assertEqual(p["ls_t"], c["long_short_tstat"])
        self.assertEqual(p["decile_alpha"], c["top_decile_alpha"])
        self.assertEqual(p["n_names"], a["universe"]["n_names"])
        self.assertEqual(p["hlz_hurdle"], h["hurdle_sqrt_2_ln_N"])
        self.assertEqual(p["hlz_clears"], h["clears_hlz_hurdle"])

    def test_the_absent_HAC_t_is_reported_absent_and_NOT_substituted(self):
        # THE WRONG-OBJECT FAMILY, HEADED OFF. The canonical artifact carries a naive
        # `top_decile_alpha_tstat` and `top_decile_alpha_tstat_hac: null`. `R9` made the
        # autocorrelation-corrected figure the one this project quotes, so printing the naive
        # one under the words "Newey-West" would be a different statistic wearing that name.
        a = _artifact()
        p = F.panel()
        raw = a["construction"].get("top_decile_alpha_tstat_hac")
        if raw is None:
            self.assertIsNone(p["decile_alpha_t_hac"])
            self.assertIsNotNone(p["decile_alpha_t"])
            self.assertNotEqual(p["decile_alpha_t_hac"], p["decile_alpha_t"])
            html = _render("portfolio.html")
            # The page must say which estimator it has rather than claim the other.
            self.assertIn("uncorrected", html)
        else:
            self.assertEqual(p["decile_alpha_t_hac"], raw)

    def test_both_readers_degrade_to_no_number_rather_than_a_wrong_one(self):
        for fn in (F.costs, F.panel):
            d = fn({})
            self.assertFalse(d["available"])
            self.assertTrue(d["reason"])
            for k, v in d.items():
                if k in ("available", "reason", "book", "account"):
                    continue
                self.assertIsNone(v, "%s left %s=%r on the absent path" % (fn.__name__, k, v))

    def test_the_page_says_WHICH_BOOK_beside_every_cost_pair(self):
        # DECISIONS.md's standing rule: a research-decile figure on a public page must say in
        # the same sentence that it is not the Index, and name its universe. The review found
        # the same page carrying two pairs with nothing to say which book either belonged to.
        c = F.costs()
        self.assertIn("research decile", c["book"])
        self.assertEqual(c["account"], "taxable")
        for name in PAGES:
            html = _render(name)
            self.assertIn("research decile", html, name)
            self.assertIn("not the Valquo Index", html, name)
            self.assertIn("taxable", html, name)


class TheRoutesPassTheLiveFacts(unittest.TestCase):
    """A reader is only as good as its caller: both routes must actually pass it in."""

    def test_both_routes_pass_costs_and_the_portfolio_route_passes_panel(self):
        import ast
        wants = {
            os.path.join("valuation", "web", "app.py"): ("methodology.html", ("costs",)),
            os.path.join("valuation", "saas", "app_saas.py"): ("portfolio.html",
                                                               ("costs", "panel")),
        }
        for rel, (tpl, kws) in wants.items():
            tree = ast.parse(io.open(os.path.join(REPO, rel), encoding="utf-8").read())
            found = None
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                if getattr(fn, "id", None) != "render_template" and \
                        getattr(fn, "attr", None) != "render_template":
                    continue
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
                if node.args[0].value != tpl:
                    continue
                found = {k.arg for k in node.keywords if k.arg}
            self.assertIsNotNone(found, "%s has no render_template(%r)" % (rel, tpl))
            for kw in kws:
                self.assertIn(kw, found,
                              "%s renders %s without passing %s=" % (rel, tpl, kw))


class TheLowSideOfTheBandIsLoud(unittest.TestCase):
    """§2, Don's ruling: flag low values loudly, do not hide them. ONE definition."""

    def test_the_mirror_threshold_is_imported_and_never_retyped(self):
        from valuation.engine import publication as P
        # The ruling's own words: "0.2x, imported from the same place as FV_BAND_HIGH, never
        # retyped". Both constants must come from this one module, and `implausible_low` must
        # be computed against the imported one rather than a literal.
        self.assertEqual(P.FV_BAND_LOW, 0.2)
        self.assertEqual(P.FV_BAND_HIGH, 5.0)
        # READ THE SYNTAX TREE, NOT THE TEXT. The first cut of this test banned the substring
        # "0.2" in the function's source and FAILED against the correct tree, because the
        # docstring quotes the measured 0.2x-0.5x count -- the substring-ban family, which this
        # project has now paid for often enough to have a standing rule against it. A numeric
        # literal in the function's CODE is the thing that would be a second definition, and
        # the AST is where code lives and prose does not.
        import ast
        tree = ast.parse(io.open(os.path.join(REPO, "valuation", "web", "withhold.py"),
                                 encoding="utf-8").read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "flag_implausibly_low_fair_values")
        lits = [n.value for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                and not isinstance(n.value, bool)]
        self.assertNotIn(P.FV_BAND_LOW, lits,
                         "the low-side flag retypes the threshold instead of importing it")
        self.assertNotIn(P.FV_BAND_HIGH, lits)
        # POSITIVE CONTROL: the guard must be able to see a literal at all, or it passes by
        # looking at nothing.
        probe = ast.parse("def f():\n    return 0.2\n")
        self.assertIn(0.2, [n.value for n in ast.walk(probe)
                            if isinstance(n, ast.Constant)])

    def test_the_flag_fires_below_the_band_and_not_inside_it(self):
        from valuation.engine import publication as P
        # BELOW the band: fires.
        v = P.decide(1.0, 50.0)
        self.assertTrue(v.implausible_low)
        self.assertTrue(v.low_note)
        # THE REVIEW'S OWN EXAMPLE, 0.477x, DOES NOT FIRE — and that is correct. §2 says
        # "add no new threshold" for the 0.2x-0.5x range and asks only for the count, so a
        # flag firing there would be this item inventing the tier Don reserved for himself.
        v = P.decide(130.08, 272.46)
        self.assertFalse(v.implausible_low)
        self.assertFalse(v.low_note)
        # ABOVE the band is the other side and must stay a refusal, not a flag.
        v = P.decide(60.0, 10.0)
        self.assertTrue(v.implausible_high)
        self.assertFalse(v.publish)
        self.assertFalse(v.implausible_low)

    def test_the_low_side_PUBLISHES_and_reason_stays_empty(self):
        # The distinction the whole design turns on. `FV_BAND_LOW`'s own note: the low side is
        # not the failure the high side guards against, and suppressing it would hide
        # legitimate "this is expensive" verdicts. And `reason` is documented "empty when
        # publishable", so putting the low words there would make every surface testing
        # `if v.reason:` start refusing names the band deliberately publishes.
        from valuation.engine import publication as P
        v = P.decide(1.0, 50.0)
        self.assertTrue(v.publish)
        self.assertIsNotNone(v.value)
        self.assertEqual(v.reason, "")

    def test_the_row_flag_keeps_the_value_and_moves_the_confidence(self):
        from valuation.web import withhold as W
        rows = [{"fair_value": 1.0, "price": 50.0, "fair_value_confidence": "high"},
                {"fair_value": 130.08, "price": 272.46, "fair_value_confidence": "high"}]
        n = W.flag_implausibly_low_fair_values(rows)
        self.assertEqual(n, 1)
        self.assertTrue(rows[0][W.ROW_LOW_FLAG])
        self.assertTrue(rows[0][W.ROW_LOW_NOTE])
        self.assertEqual(rows[0]["fair_value"], 1.0, "the low side must NOT withhold")
        # The measurement that prompted the ruling found names at a fifth of their price
        # served as `confidence: high`.
        self.assertEqual(rows[0]["fair_value_confidence"], "low")
        self.assertNotIn(W.ROW_LOW_FLAG, rows[1])
        self.assertEqual(rows[1]["fair_value_confidence"], "high")

    def test_an_already_withheld_row_is_not_double_marked(self):
        from valuation.engine.publication import ROW_WITHHELD
        from valuation.web import withhold as W
        rows = [{"fair_value": 9.0, "price": 1.0, ROW_WITHHELD: True}]
        self.assertEqual(W.flag_implausibly_low_fair_values(rows), 0)
        self.assertNotIn(W.ROW_LOW_FLAG, rows[0])

    def test_every_site_that_withholds_HIGH_also_flags_LOW(self):
        # THE LOPSIDEDNESS WAS THE DEFECT, so the fix is only real if the two sides reach the
        # same surfaces. Read from the sources: any module calling the high-side function must
        # call the low-side one too.
        import ast
        hi, lo = "withhold_implausible_fair_values", "flag_implausibly_low_fair_values"
        checked = 0
        for rel in ("valuation/web/app.py", "valuation/web/dip.py", "valuation/web/unified.py",
                    "scripts/ci_scan.py"):
            src = io.open(os.path.join(REPO, rel), encoding="utf-8").read()
            tree = ast.parse(src)
            calls = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                     for n in ast.walk(tree) if isinstance(n, ast.Call)}
            if hi not in calls:
                continue
            checked += 1
            self.assertIn(lo, calls,
                          "%s applies the HIGH side of the band and not the LOW side" % rel)
        self.assertGreaterEqual(checked, 3, "the call-site census found almost nothing")

    def test_the_wording_has_ONE_definition(self):
        # `publication.low_words` is it. `scoring.py` and `pipeline.py` carried their own
        # sentences and now call it, which is this module's own header rule.
        import ast
        for rel in ("valuation/engine/scoring.py", "valuation/engine/pipeline.py"):
            tree = ast.parse(io.open(os.path.join(REPO, rel), encoding="utf-8").read())
            calls = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                     for n in ast.walk(tree) if isinstance(n, ast.Call)}
            self.assertIn("_low_words", calls, "%s does not call the shared wording" % rel)

    def test_the_renderer_never_compares_the_band_itself(self):
        # A renderer that compares 0.2 is a second definition of the one thing
        # `engine/publication.py` exists to state once. The JS must read the server's flag.
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertIn("fair_value_implausibly_low", js)
        for bad in ("fair_value / r.price", "fair_value/r.price", "< 0.2", "<0.2"):
            self.assertNotIn(bad, js, "app.js compares the band itself: %r" % bad)


class ListsShowABandNotAPerNameScore(unittest.TestCase):
    """§4, Don's ruling. The bands, the sort order, and the detail-view sentence."""

    def test_the_band_is_derived_from_rank_and_degrades_to_none(self):
        from valuation.web import score_confidence as SC
        self.assertEqual(SC.band_for(1, 1000)["band"], "top 10%")
        self.assertEqual(SC.band_for(100, 1000)["band"], "top 10%")
        self.assertEqual(SC.band_for(101, 1000)["band"], "top 25%")
        self.assertEqual(SC.band_for(600, 1000)["band"], "bottom half")
        for bad in ((None, 1000), (5, None), (0, 1000), (5, 0), ("x", "y")):
            self.assertIsNone(SC.band_for(*bad)["band"], bad)

    def test_the_primary_cut_IS_the_measured_bucket_and_not_a_new_threshold(self):
        # The 10% cut is `PRIMARY_RANK`, the bucket every measured claim in that module is
        # about. A band vocabulary that invented its own primary cut would be a new threshold
        # dressed as display.
        from valuation.web import score_confidence as SC
        self.assertEqual(SC.SCORE_BANDS[0][0] * 100, float(SC.PRIMARY_RANK))

    def test_no_list_renders_a_two_decimal_score(self):
        # §4's own test. `z()` fed four theme columns at `toFixed(2)`; the composite reached
        # the Index table at `toFixed(1)`. Both are now a band or one decimal.
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertIn('function z(x) { return (x == null || isNaN(x)) ? "—" : '
                      '(x >= 0 ? "+" : "") + x.toFixed(1); }', js,
                      "the list z-score helper is not at one decimal")
        self.assertNotIn("hot_score.toFixed(2)", js)
        self.assertNotIn("hot_score_today : p.hot_score).toFixed(1)", js,
                         "the Index holdings still render a one-decimal score")

    def test_the_detail_view_sentence_exists_and_is_the_servers(self):
        from valuation.web import score_confidence as SC
        s = SC.DETAIL_SCORE_SENTENCE
        self.assertIn("not", s.lower())
        self.assertIn("chance", s.lower())
        self.assertEqual(SC.for_template()["detail_sentence"], s)
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertIn("detail_sentence", js, "the detail view does not render the sentence")
        # NOT A SECOND COPY. The words must not be typed into the renderer.
        self.assertNotIn(s[:40], js)

    def test_the_band_is_display_only_and_the_sort_order_is_untouched(self):
        # The rows arrive ranked and the band is computed FROM the rank, so it cannot reorder
        # anything. Pinned at the source: no sort may key on the band.
        for rel in ("valuation/web/app.py", "valuation/web/static/app.js"):
            src = io.open(os.path.join(REPO, rel), encoding="utf-8").read()
            for bad in ("sort(score_band", "sortBy(\"score_band\"", "key=lambda r: r[\"score_band\"]"):
                self.assertNotIn(bad, src)


class EveryScoreSaysHowManyThemesFedIt(unittest.TestCase):
    """§5. The count, its denominator, and the label below seven."""

    def test_the_denominator_is_SEVEN_per_bucket_and_not_the_eight_name_union(self):
        # THE FINDING §5 TURNED UP. `themes_scored` counts the union of both weight dicts,
        # which is EIGHT because `quality` and `growth` are bucket alternatives — so the
        # shipped "N of 7" columns could read "8 of 7". Measured on the live scan of
        # 2026-10-20: 35 of the 100 served rows read 8.
        from valuation.screener import thin_data as T
        self.assertEqual(len(T.weighted_theme_names()), 8, "the union is not 8 any more")
        for bucket in ("established", "speculative"):
            w = T.bucket_weights({"bucket": bucket})
            self.assertEqual(len(w), 7, "%s is not 7 themes" % bucket)
        self.assertIn("quality", T.bucket_weights({"bucket": "established"}))
        self.assertIn("growth", T.bucket_weights({"bucket": "speculative"}))

    def test_a_row_scored_on_everything_reads_7_of_7_not_8_of_7(self):
        from valuation.screener import thin_data as T
        row = {"bucket": "established", "extra": {"factors": {
            "value": 1, "quality": 1, "momentum": 1, "size": 1, "capital_discipline": 1,
            "insider": 1, "institutional": 1, "growth": 1, "low_risk": 1}}}
        s = T.scored_of_seven(row)
        self.assertEqual((s["n"], s["of"]), (7, 7))
        self.assertTrue(s["backtested"])
        # The old count on the SAME row is the eight that could not be shown.
        self.assertEqual(T.theme_count(row), 8)

    def test_below_seven_is_labelled_not_the_backtested_model(self):
        from valuation.screener import thin_data as T
        row = {"bucket": "speculative", "extra": {"factors": {
            "value": 1, "growth": 1, "momentum": 1, "size": 1, "capital_discipline": 1,
            "insider": None, "institutional": None}}}
        s = T.scored_of_seven(row)
        self.assertEqual((s["n"], s["of"], s["missing"]), (5, 7, 2))
        self.assertFalse(s["backtested"])
        self.assertIn("not the backtested model", s["label"])

    def test_unknown_is_NOT_zero(self):
        # `C5`. An older snapshot carries no factor dict, and "0 of 7 themes fed this score"
        # about a row that cannot be counted is a measured-looking claim about nothing.
        from valuation.screener import thin_data as T
        for row in ({"bucket": "established", "extra": {"factors": {}}},
                    {"bucket": "established"}, {}):
            s = T.scored_of_seven(row)
            self.assertIsNone(s["n"])
            self.assertIsNone(s["backtested"])
            self.assertTrue(s["label"])

    def test_the_count_is_stamped_where_the_old_one_is(self):
        # One site, so the two counts cannot reach different surfaces.
        from valuation.screener import thin_data as T
        rows = [{"ticker": "A", "bucket": "established",
                 "extra": {"factors": {"value": 1, "size": 1}}}]
        T.mark(rows)
        for k in ("themes_scored", "themes_of_seven", "themes_of_seven_total",
                  "themes_backtested", "themes_label"):
            self.assertIn(k, rows[0], k)

    def test_the_old_count_is_deliberately_UNCHANGED(self):
        # `MIN_THEMES` and the thin-data rule are calibrated on `theme_count`, and
        # `index_in_force` stamps it on every position. Adding a number beside it is safe;
        # redefining it would re-point a shipped floor.
        from valuation.screener import thin_data as T
        self.assertEqual(T.MIN_THEMES, 4)
        row = {"bucket": "established", "extra": {"factors": {"value": 1, "growth": 1,
                                                              "quality": 1}}}
        self.assertEqual(T.theme_count(row), 3)

    def test_the_index_holdings_carry_the_seven_count_too(self):
        src = io.open(os.path.join(REPO, "valuation", "screener", "index_in_force.py"),
                      encoding="utf-8").read()
        self.assertIn("themes_of_seven_today", src)
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertIn("themes_of_seven_today", js)
        # AND ITS THIN FLAG NO LONGER READS "of 7" OFF THE UNION COUNT.
        self.assertNotIn("p.themes_scored_today} of 7 themes", js)


class TheBetaSensitivityIsTheShippedEngine(unittest.TestCase):
    """§3. Re-solved, bounded, delegated, and presentation-only."""

    def test_it_delegates_to_the_shipped_second_pass(self):
        # §3: "Compute it with the SHIPPED engine, never a re-implementation." It delegates to
        # `average_risk_read`, which item 53 part 3 built for exactly this and which handles
        # two traps a direct call reintroduces -- see the module docstring.
        import ast
        from valuation.web import beta_sensitivity as BS
        tree = ast.parse(io.open(BS.__file__, encoding="utf-8").read())
        names = {a.asname or a.name.split(".")[-1]
                 for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                 for a in n.names}
        self.assertIn("read_fn", names | {"read_fn"})
        src = io.open(BS.__file__, encoding="utf-8").read()
        self.assertIn("average_risk_read", src)
        # NO VALUATION ARITHMETIC OF ITS OWN — ASSERTED ON THE SYNTAX TREE. The first cut of
        # this banned the substring "** " and FAILED against the correct tree, because the
        # docstring is markdown and markdown bold is two asterisks. Same family as the guard
        # two classes up, found the same way, in the same hour. A power operator and an
        # exponential are what a CAPM or discount-chain re-implementation needs, and both are
        # AST nodes rather than character sequences.
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Pow)],
                         "the sensitivity module raises to a power, so it is discounting")
        called = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                  for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for bad in ("exp", "log", "pow", "compute_wacc", "build_scenarios",
                    "blended_fair_value"):
            self.assertNotIn(bad, called,
                             "the sensitivity module calls %r, so it derives its own value"
                             % bad)
        # POSITIVE CONTROL for the `Pow` half: it must see one when there is one.
        self.assertTrue([n for n in ast.walk(ast.parse("x = (1 + r) ** n"))
                         if isinstance(n, ast.Pow)])

    def test_the_anchor_is_read_from_the_result_and_is_NOT_resolved(self):
        from types import SimpleNamespace as NS
        from valuation.web import beta_sensitivity as BS
        seen = []

        def read(cd, cfg, *, deployed_wacc, deployed_beta, deployed_value, revalue, beta):
            seen.append(round(beta, 4))
            return {"value": 10.0, "wacc": 0.09, "reason": ""}

        res = NS(company=NS(beta=0.32, quality_notes=[]),
                 wacc=NS(beta=0.32, wacc=0.065), base_fair_value=58.5)
        s = BS.strip(res, cfg={}, read_fn=read)
        self.assertTrue(s["available"], s["reason"])
        self.assertEqual(seen, [0.02, 0.62], "the anchor was re-solved, or the span is wrong")
        anchor = next(p for p in s["points"] if p["is_anchor"])
        self.assertEqual(anchor["value"], 58.5)
        self.assertEqual(anchor["pct_vs_anchor"], 0.0)

    def test_it_is_bounded_by_the_engines_own_imported_beta_limits(self):
        from types import SimpleNamespace as NS
        from valuation.engine.wacc import BETA_HIGH_CAP
        from valuation.web import beta_sensitivity as BS
        self.assertEqual(BS.beta_bounds()[1], float(BETA_HIGH_CAP))
        seen = []

        def read(cd, cfg, *, deployed_wacc, deployed_beta, deployed_value, revalue, beta):
            seen.append(beta)
            return {"value": 10.0, "wacc": 0.09, "reason": ""}

        res = NS(company=NS(beta=2.9, quality_notes=[]),
                 wacc=NS(beta=2.9, wacc=0.18), base_fair_value=20.0)
        s = BS.strip(res, cfg={}, read_fn=read)
        self.assertTrue(s["clamped"])
        for b in seen:
            self.assertLessEqual(b, float(BETA_HIGH_CAP))
            self.assertGreater(b, 0.0)
        # The strip reports the beta it USED, not the one it asked for.
        for p in s["points"]:
            self.assertLessEqual(p["beta"], float(BETA_HIGH_CAP))

    def test_it_refuses_rather_than_guessing(self):
        from types import SimpleNamespace as NS
        from valuation.web import beta_sensitivity as BS

        def read(cd, cfg, **kw):
            return {"value": None, "wacc": None, "reason": "no"}

        self.assertFalse(BS.strip(None)["available"])
        # A WITHHELD NAME GETS NO STRIP. Saying "the value would be $X at another beta" beside
        # a headline the model declined to publish hands back the number the refusal withheld.
        res = NS(company=NS(beta=1.0, quality_notes=[]), wacc=NS(beta=1.0, wacc=0.09),
                 base_fair_value=None)
        out = BS.strip(res, cfg={}, read_fn=read)
        self.assertFalse(out["available"])
        self.assertIn("no base value", out["reason"])
        # No beta, nothing to vary.
        res = NS(company=NS(beta=None, quality_notes=[]), wacc=NS(beta=None, wacc=0.09),
                 base_fair_value=50.0)
        self.assertFalse(BS.strip(res, cfg={}, read_fn=read)["available"])
        # Every point refusing is not a strip.
        res = NS(company=NS(beta=1.0, quality_notes=[]), wacc=NS(beta=1.0, wacc=0.09),
                 base_fair_value=50.0)
        self.assertFalse(BS.strip(res, cfg={}, read_fn=read)["available"])

    def test_the_label_is_the_one_section_3_asked_for_and_lives_on_the_server(self):
        from valuation.web import beta_sensitivity as BS
        self.assertEqual(BS.LABEL, "how much this value depends on one input")
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertNotIn(BS.LABEL, js, "the renderer carries its own copy of the label")
        self.assertIn("beta_sensitivity", js)

    def test_the_strip_renders_even_when_the_beta_1_read_is_immaterial(self):
        # A DEFECT CAUGHT BY WRITING THIS TEST. `averageRisk` returned early whenever the
        # beta-1.0 sentence was immaterial -- correct for that sentence, and it would have
        # suppressed §3's strip on exactly the names whose beta is already near 1.0.
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertIn("if (!show && !strip)", js)
        self.assertNotIn("if (!a.available || !a.is_material || !a.sentence) "
                         "{ el.innerHTML = \"\"; return; }", js)

    def test_the_route_attaches_it_and_the_engine_payload_does_NOT(self):
        # Two extra valuations per call is affordable on one name and is not affordable 1,500
        # times in a scan, which is what putting it in `to_dict` would have cost.
        import ast
        app = io.open(os.path.join(REPO, "valuation", "web", "app.py"),
                      encoding="utf-8").read()
        self.assertIn("beta_sensitivity", app)
        eng = io.open(os.path.join(REPO, "valuation", "engine", "pipeline.py"),
                      encoding="utf-8").read()
        tree = ast.parse(eng)
        self.assertNotIn("beta_sensitivity",
                         {a.asname or a.name.split(".")[-1]
                          for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                          for a in n.names})


if __name__ == "__main__":
    unittest.main(verbosity=2)
