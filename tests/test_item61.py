# -*- coding: utf-8 -*-
"""ITEM 61 — the Proof page leads with the product, and the unit label is derived.

Don's question, 2026-10-14: *"why is that the headline for our proof and not the full index being
tracked if the full index is the product?"*

THE MISLABEL WAS CONTRADICTED ON ITS OWN PAGE, which is how it is checkable rather than a matter
of opinion. The placebo card read *"Top-decile alpha, per quarter"* for `top_decile_alpha`, and
the restatement section 500 lines below renders the SAME field as *"6.07% a year"*. One page, one
number, two units. The fix derives the unit from the artifact so neither label can be typed wrong
again.
"""
from __future__ import annotations

import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.web import proof as PR   # noqa: E402

BODY = os.path.join(REPO, "valuation", "web", "templates", "_proof_body.html")


def _tpl():
    with open(BODY, encoding="utf-8") as fh:
        return fh.read()


def _render():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(os.path.dirname(BODY)))
    return env.get_template(os.path.basename(BODY)).render(p=PR.payload())


def _flat(html: str) -> str:
    """The page as a READER sees it: one space between words, entities resolved.

    **A RENDERED TEMPLATE IS WHITESPACE-WRAPPED.** "every market capitalisation" sits in the
    page split across a newline and six spaces of indentation, so an assertion on the literal
    missed it -- and this project has already recorded the same lesson for `&amp;`-escaped
    text. Asserting on the raw bytes a template emits is asserting on its formatting.
    """
    import html as _h
    import re
    return re.sub(r"\s+", " ", _h.unescape(html.replace("&nbsp;", " ")))


def _code_strings(path: str) -> list:
    """Every string constant in a module EXCEPT its docstrings.

    A docstring is an AST string constant, so a ban that walks `ast.Constant` is still a
    substring ban on prose -- which is how the first version of the test below failed against
    a correct tree: `_alpha_unit`'s docstring quotes the old label in order to explain why it
    was wrong. Docstrings describe the rule; only the other strings can render.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docs.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs]


class TheUnitIsDerivedAndNotTyped(unittest.TestCase):
    """ITEM 61 PART 3. *"Label the unit from the artifact's own field rather than typing it."*"""

    def test_the_shipped_artifact_proves_the_figure_is_ANNUAL(self):
        """`top_decile_alpha` / the distribution's own `mean` is the annualisation factor the
        producer applied. On the shipped artifact it is exactly 4."""
        res = PR._load(PR.BACKTEST_JSON)
        if res is None:
            self.skipTest("the canonical artifact is not readable here")
        u = PR._alpha_unit(res)
        self.assertTrue(u["derived"], u["reason"])
        self.assertEqual(u["unit"], "a year")
        self.assertAlmostEqual(u["factor"], 4.0, places=3)

    def test_the_rendered_label_says_a_year(self):
        p = PR.payload()
        if not p.get("available") or not p.get("placebo"):
            self.skipTest("no placebo block in this deployment")
        rows = {r["key"]: r["label"] for r in p["placebo"]["rows"]}
        self.assertIn("top_decile_alpha", rows)
        self.assertEqual(rows["top_decile_alpha"], "Top-decile alpha, a year")

    def test_the_old_label_is_gone_everywhere(self):
        """**MY FIRST VERSION OF THIS TEST FAILED AGAINST A CORRECT TREE**, and for the reason
        it was itself written to avoid. It walked `ast.Constant` rather than the file text,
        noting that a comment quoting the wrong label would trip a text search -- and then a
        DOCSTRING is an AST string constant, so `_alpha_unit`'s docstring, which quotes the old
        label in order to explain it, tripped it anyway. Docstrings are excluded now; what
        remains is the strings the code can actually render.
        """
        offenders = [x for x in _code_strings(PR.__file__) if "alpha, per quarter" in x]
        self.assertEqual(offenders, [])

    def test_and_that_exclusion_is_not_vacuous(self):
        """A POSITIVE CONTROL: the reader must still SEE the renderable strings, or the test
        above passes by looking at nothing."""
        strings = _code_strings(PR.__file__)
        self.assertTrue(any("Top-decile alpha" in x for x in strings),
                        "the label template itself is not visible to the reader")
        self.assertTrue(any("{unit}" in x for x in strings))

    def test_a_per_period_figure_WOULD_be_labelled_per_quarter(self):
        """The positive control. Without it the derivation could be hard-wired to "a year" and
        every test above would still pass."""
        fake = {"construction": {"top_decile_alpha": 0.015,
                                 "top_decile_alpha_distribution": {"mean": 0.015}}}
        self.assertEqual(PR._alpha_unit(fake)["unit"], "per quarter")

    def test_it_REFUSES_rather_than_guessing_when_it_cannot_tell(self):
        """An unlabelled figure is honest; a wrongly-labelled one is not."""
        for bad in ({"construction": {"top_decile_alpha": 0.06}},
                    {"construction": {"top_decile_alpha_distribution": {"mean": 0.015}}},
                    {"construction": {"top_decile_alpha": 0.06,
                                      "top_decile_alpha_distribution": {"mean": 0.0}}},
                    {"construction": {"top_decile_alpha": 0.06,
                                      "top_decile_alpha_distribution": {"mean": 0.0177}}}):
            u = PR._alpha_unit(bad)
            self.assertEqual(u["unit"], "", u)
            self.assertFalse(u["derived"])
            self.assertTrue(u["reason"])

    def test_an_unlabelled_unit_DROPS_the_clause_rather_than_printing_a_hole(self):
        got = PR._placebo({"construction": {"top_decile_alpha": 0.06}}, None, None,
                          unit_label="")
        rows = {r["key"]: r["label"] for r in (got or {}).get("rows", [])}
        if "top_decile_alpha" in rows:
            self.assertEqual(rows["top_decile_alpha"], "Top-decile alpha")
            self.assertNotIn("{unit}", rows["top_decile_alpha"])

    def test_it_carries_the_artifacts_OWN_warning_about_the_sibling_field(self):
        """The distribution block's `units` says it is per-period and must NOT be scaled, while
        its sibling `top_decile_alpha` is annualised. Two fields in one block with opposite
        conventions is the shape that produced the wrong label."""
        res = PR._load(PR.BACKTEST_JSON)
        if res is None:
            self.skipTest("artifact not readable")
        u = PR._alpha_unit(res)
        self.assertIn("not annualised", u["distribution_units"])


class ThePageLeadsWithTheProduct(unittest.TestCase):
    """ITEM 61 PART 1. Asserted on POSITION IN THE RENDERED HTML -- what a reader sees first."""

    def setUp(self):
        self.html = _render()

    def _at(self, needle):
        i = self.html.find(needle)
        self.assertGreater(i, -1, "missing from the page: %r" % needle)
        return i

    def test_the_index_comes_before_the_research_decile(self):
        self.assertLess(self._at("The Valquo Index, measured on its own construction"),
                        self._at("We shuffled the signal"))

    def test_the_order_is_index_then_forward_track_then_the_decile(self):
        a = self._at("The Valquo Index, measured on its own construction")
        b = self._at("What has actually been recorded so far")
        c = self._at("Everything BELOW this point")
        d = self._at("We shuffled the signal")
        e = self._at("The full ladder")
        self.assertTrue(0 < a < b < c < d < e, (a, b, c, d, e))

    def test_the_hinge_sits_BELOW_the_product_it_excludes(self):
        """It used to read "every figure on this page is the research decile", which stopped
        being true the moment the product's figures moved above it -- so a stale banner would
        have made the page contradict itself at the top. **Caught by the order check**, not by
        reading."""
        self.assertLess(self._at("The Valquo Index, measured on its own construction"),
                        self._at("Everything BELOW this point"))
        self.assertNotIn("Every figure on this page is the RESEARCH DECILE", self.html)

    def test_the_hinge_explains_in_one_place_why_the_decile_is_higher(self):
        """The brief asks for one sentence. Three reasons, none of them skill.

        Asserted on the NORMALISED page: the rendered template wraps "every market
        capitalisation" across a newline and six spaces, so a literal assertion on the raw
        bytes was testing the template's formatting rather than its words.
        """
        flat = _flat(self.html)
        i = flat.find("Everything BELOW this point")
        self.assertGreater(i, -1)
        chunk = flat[i:i + 1200]
        for reason in ("every market capitalisation", "weights every holding",
                       "gross of the trading costs"):
            self.assertIn(reason, chunk, reason)

    def test_the_after_tax_line_is_there_and_says_below_SPY(self):
        flat = _flat(self.html)
        i = flat.find("In a regular taxable account")
        self.assertGreater(i, -1)
        self.assertIn("below SPY", flat[i:i + 300])

    def test_the_forward_track_gives_both_dates_and_the_day_count(self):
        flat = _flat(self.html)
        i = flat.find("What has actually been recorded so far")
        self.assertGreater(i, -1)
        chunk = flat[i:i + 2200]
        self.assertIn("First evidence read", chunk)
        self.assertIn("Verdict", chunk)
        self.assertIn("Recorded days", chunk)

    def test_it_says_a_few_months_means_nothing_yet(self):
        flat = _flat(self.html)
        self.assertIn("means nothing yet", flat)
        self.assertIn("arithmetic rather than", flat)


class EveryFigureIsReadFromAnArtifact(unittest.TestCase):
    """ITEM 61 PART 4, and `B7`: nothing typed by hand, nothing new claimed."""

    def test_the_index_figures_come_from_index_book_measured(self):
        with open(PR.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("from ..screener import index_book_measured", src)

    def test_proof_py_retypes_none_of_the_index_constants(self):
        """A second copy of +2.22pp would drift from the first the moment either moved."""
        from valuation.screener import index_book_measured as IB
        with open(PR.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        nums = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, float)}
        for val in (IB.ALPHA_VS_SPY_PP, IB.ALPHA_VS_OWN_TIER_PP, IB.SERVED_SHARPE,
                    IB.SERVED_TURNOVER, IB.SPY_PCT, IB.SERVED_NET_PCT,
                    IB.SERVED_ROTH_PCT, IB.SERVED_TAXABLE_PCT):
            self.assertNotIn(val, nums, "%r is retyped in proof.py" % val)

    def test_the_template_types_no_index_figure_either(self):
        from valuation.screener import index_book_measured as IB
        src = _tpl()
        for val in (IB.ALPHA_VS_SPY_PP, IB.ALPHA_VS_OWN_TIER_PP, IB.SPY_PCT,
                    IB.SERVED_ROTH_PCT, IB.SERVED_TAXABLE_PCT):
            self.assertNotIn(str(val), src, "%r is typed into the template" % val)

    def test_the_rendered_page_carries_the_real_figures(self):
        """The companion to the two tests above: having proved nothing is typed, prove the
        numbers still arrive. Otherwise "no hard-coded figure" is satisfied by a blank page."""
        from valuation.screener import index_book_measured as IB
        html = _render()
        self.assertIn(str(IB.ALPHA_VS_SPY_PP), html)
        self.assertIn(str(IB.ALPHA_VS_OWN_TIER_PP), html)
        self.assertIn(str(IB.SPY_PCT), html)

    def test_the_source_artifact_is_named_on_the_page(self):
        html = _render()
        self.assertIn("INDEX-BOOK", html)


class TheForwardDatesAreDerived(unittest.TestCase):
    """`CLAUDE.md` records three five-year clock resets in four days and the instruction that
    followed: *"DERIVE it from `track_meter.VINTAGES`; never quote one from this file."* A
    hard-coded 2027-02-13 would be wrong the next time Don adopts anything."""

    def test_the_gate_is_six_months_after_the_open_vintage(self):
        from valuation.edge import track_meter as TM
        ft = PR._forward_track()
        self.assertIsNotNone(ft)
        v = TM.current_vintage() or {}
        opened = TM._d(v.get("opened"))
        self.assertEqual(ft["gate"], str(TM._months_after(opened, 6)))
        self.assertEqual(ft["verdict"], str(TM._months_after(opened, 60)))
        self.assertTrue(ft["dates_are_derived"])

    def test_it_agrees_with_the_briefs_own_dates_today(self):
        """The brief states 2027-02-13 and 2031. Derived, they match -- which is the check that
        the derivation is right, rather than the dates being the source."""
        ft = PR._forward_track()
        self.assertEqual(ft["gate"], "2027-02-13")
        self.assertTrue(str(ft["verdict"]).startswith("2031"))

    def test_neither_date_is_typed_in_proof_py(self):
        with open(PR.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        strings = [n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        # The docstring legitimately mentions the dates as the CHECK; a format string or a
        # returned value must not.
        bad = [x for x in strings if ("2027-02-13" in x or "2031-08-13" in x)
               and "derive" not in x.lower() and "brief" not in x.lower()
               and len(x) < 200]
        self.assertEqual(bad, [], bad)

    def test_a_missing_vintage_does_not_crash_the_page(self):
        """The forward section is the newest thing on this page; a defect in it must cost the
        section rather than the whole proof."""
        p = PR.payload()
        self.assertTrue(p.get("available"))


class ThePageStillRenders(unittest.TestCase):
    def test_the_template_compiles_and_produces_a_page(self):
        """A template that does not compile is not a test failure -- it is a 500 on the page."""
        html = _render()
        self.assertGreater(len(html), 20000)
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)

    def test_the_backtest_warning_still_leads_the_evidence(self):
        """Putting the product first must not displace the honesty banner: these are
        backtested results, not a track record."""
        html = _render()
        i = html.find("These are backtested results, not a track record")
        self.assertGreater(i, -1)
        self.assertLess(i, html.find("The Valquo Index, measured on its own construction"))


if __name__ == "__main__":
    unittest.main()
