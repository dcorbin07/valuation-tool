# -*- coding: utf-8 -*-
"""(F) ONE VALQUO INDEX, EVERYWHERE — the end-to-end guard.

WHAT WENT WRONG, AND WHY A SPEC WAS THE ANSWER. A Cowork scrub on 2026-10-02 found the Index tab
showing a 25-name book rebuilt from each day's scan while the forward record beneath it tracked
an 86-name quarterly book -- and `PAPER_TRACK_CONTRACT.md` §5 defines the tracked book as "the
Valquo Index exactly as the site shows it", so the contract's own premise was false. The same
scrub found a backtest of ONE construction printed beside the live curve of ANOTHER on three
surfaces, and eleven wrong statements of cadence or mechanism.

Every one of those is a surface disagreeing with another surface about which object it shows. No
single unit test catches that, because each surface is individually self-consistent. So this
suite asserts the three things the spec says must agree:

  1. the Index tab's holdings ARE the bound book,
  2. the backtest block's construction IS the tracked one,
  3. no public page states a cadence contradicting the spec.

PLUS the thresholds and the paper/sandbox distinction, which are the two places the copy drifted
twice.
"""
from __future__ import annotations

import io
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

SPEC = os.path.join(REPO, "PRODUCT_SPEC.md")
TPL = os.path.join(REPO, "valuation", "web", "templates")
JS = os.path.join(REPO, "valuation", "web", "static", "app.js")


def _read(p):
    return io.open(p, encoding="utf-8").read()


def _flat(p):
    """Whitespace-normalised, because every sentence in these files is line-wrapped and a
    literal containing a newline cannot match -- a test that fails against correct prose."""
    return " ".join(_read(p).split())


PUBLIC_PAGES = ["index.html", "methodology.html", "landing.html", "portfolio.html"]


class TheSpecExistsAndNamesTheObjects(unittest.TestCase):

    def test_the_spec_is_present_and_names_every_object(self):
        t = _flat(SPEC)
        for obj in ("Hot Stocks", "Options signals", "The Valquo Index",
                    "The forward record", "The backtest beside it"):
            self.assertIn(obj, t, obj)

    def test_the_spec_names_the_tracked_construction_and_it_MATCHES_the_code(self):
        """The spec is only worth anything if it cannot drift from the code it describes."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        t = _flat(SPEC)
        # ITEM 18 -- THE SPEC NOW NAMES THE SERVED BOOK, AND EVERY FIGURE IN IT IS CHECKED
        # AGAINST `index_book_measured` RATHER THAN AGAINST PROSE. This used to assert the spec
        # named `BOOK_CONFIGS["taxable"]`, which was right while that was the nearest measured
        # construction and is now the research decile. The check is strictly STRONGER: a
        # re-run of INDEX-BOOK that moved any figure would leave the spec red.
        from valuation.screener import index_book_measured as M
        self.assertIn("index_book_measured", t, "the spec does not name its authority")
        self.assertIn("INDEX-BOOK", t)
        self.assertIn(M.STUDY_COMMIT, t, "the spec does not cite the measuring commit")
        # TYPOGRAPHY NORMALISED BEFORE COMPARING, because the spec writes a negative with a
        # real minus sign (U+2212) and `%.4f` emits an ASCII hyphen. The first cut of this
        # test failed on -0.0576 for that reason alone -- a test asserting a NUMBER in prose
        # must compare the number, not the glyph, or it reports a missing figure that is
        # present and correct.
        flat = t.replace("−", "-").replace("–", "-")
        for num in ("%.4f" % M.SERVED_ROTH_PCT, "%.4f" % M.SERVED_TAXABLE_PCT,
                    "%.4f" % M.TAX_COST_PP, "%.4f" % M.ALPHA_VS_OWN_TIER_PP,
                    "%.4f" % M.ALPHA_VS_ALL_CAP_EW_PP, "%.4f" % M.ALPHA_VS_SPY_PP,
                    "%.4f" % M.ALPHA_VS_SPY_EARLY_PP, "%.4f" % M.ALPHA_VS_SPY_LATE_PP,
                    "%.4f" % M.SERVED_TE_VS_SPY, "{:,}".format(M.SERVED_MONTHS_TO_DETECT)):
            self.assertIn(num, flat,
                          "the spec is missing the measured figure %s" % num)
        # The tracked CONFIG is still what the next rebalance is BUILT with, and the spec
        # still has to describe that correctly -- it is just no longer what the Index's
        # backtest block reports.
        self.assertEqual(IT.TRACKED_CONFIG, "taxable",
                         "the code's tracked construction is not the spec's")
        cfg = (S.BOOK_CONFIGS or {})[IT.TRACKED_CONFIG]
        # DECILE, QUARTERLY, 30% BAND -- checked against the config, not the prose, so renaming
        # or re-tuning the config cannot leave the spec describing a book nobody builds.
        self.assertEqual(cfg.get("top_frac"), 0.1, "the tracked config is not the decile")
        self.assertEqual(cfg.get("rebalance_days"), 63, "the tracked config is not quarterly")
        self.assertEqual(cfg.get("exit_frac"), 0.3, "the tracked config has no 30% band")
        self.assertIsNone(cfg.get("top_n"), "the tracked config is a fixed-N book")

    def test_the_spec_names_the_one_rule_that_was_broken(self):
        t = _flat(SPEC)
        self.assertIn("THE HOLDINGS, THE CURVE AND THE BACKTEST ARE ALL THE SAME BOOK", t)


class TheIndexTabShowsTheBoundBook(unittest.TestCase):
    """(1) The holdings a reader sees must come from the record, not from a scan."""

    def test_the_route_reads_the_book_in_force_and_never_a_scan_by_default(self):
        import ast
        src = _read(os.path.join(REPO, "valuation", "web", "app.py"))
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "api_valquo_index")
        # THE DOCSTRING IS DROPPED FIRST, and that is not tidiness. The route's docstring
        # QUOTES the defect it fixed -- "It called `build_index(st.load_snapshot(...))` on
        # every request" -- so an order check over the unparsed function found that quotation
        # at offset 465 and failed against a CORRECT route. Prose documenting a rule contains
        # what the rule forbids; this project has paid for that shape repeatedly.
        fn = ast.FunctionDef(
            name=fn.name, args=fn.args, decorator_list=[], returns=None, type_params=[],
            body=[st for st in fn.body
                  if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)
                          and isinstance(st.value.value, str))] or [ast.Pass()])
        ast.fix_missing_locations(fn)
        body = ast.unparse(fn)
        self.assertIn("book_in_force", body,
                      "the Index route does not read the bound book at all")
        # THE ORDER MATTERS: the book-in-force branch must come BEFORE any build_index
        # CALL, or the default would still be a rebuild.
        #
        # MEASURED ON THE CALL, NOT THE NAME. My first cut compared `body.index("build_index")`
        # against the same for `book_in_force` and failed against a CORRECT route, because the
        # `from ..edge.valquo_index import build_index` line is hoisted to the top of the
        # function -- so it was comparing an import's position with a call's. The import says
        # nothing about which branch runs first.
        self.assertLess(body.index("book_in_force("), body.index("build_index("),
                        "the route builds a book from a scan before it reads the record")
        self.assertIn("preview", body, "there is no labelled preview branch")

    def test_the_DEFAULT_request_really_RETURNS_the_book_in_force(self):
        """BEHAVIOURAL, and the structural check above is not enough on its own: disabling the
        branch with `if False:` leaves both calls in the source in the same order, so the
        order assertion still passed while every request fell through to the preview. Caught by
        mutation, not by reading."""
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        from valuation.screener import index_in_force as IF
        prior = CONFIG.owner_split
        CONFIG.owner_split = False
        real = IF.book_in_force
        IF.book_in_force = lambda **k: {
            "ok": True, "formed_on": "2026-07-30", "scan_date": "2026-07-24",
            "next_rebalance": "2026-10-22", "n_positions": 1, "n_exited": 0,
            "positions": [{"ticker": "A", "weight": 1.0, "status": "held"}]}
        try:
            app = create_saas_app()
            app.config.update(TESTING=True)
            d = app.test_client().get("/api/valquo-index").get_json() or {}
        finally:
            IF.book_in_force = real
            CONFIG.owner_split = prior
        self.assertIs(d.get("is_preview"), False,
                      "the default request returned a preview, not the book in force")
        self.assertEqual(d.get("formed_on"), "2026-07-30",
                         "the default payload carries no formation date, so it is not the book")

    def test_the_tab_sends_NO_construction_and_cannot_fall_back_to_roth(self):
        """The dropdown is gone AND the `|| "roth"` fallback is gone. Removing the element
        alone would have left the page asking for the 25-name book with nothing on screen to
        say so -- which is why both are asserted."""
        js = _read(JS)
        self.assertNotIn("bookConfig", js, "the account-type dropdown is still read")
        self.assertNotIn('/api/valquo-index?config=', js,
                         "the holdings request still names a construction")
        self.assertNotIn('/api/index-track?config=', js,
                         "the performance request still names a construction")
        self.assertNotIn('bookConfig', _read(os.path.join(TPL, "index.html")),
                         "the dropdown is still in the template")

    def test_roth_is_unreachable_from_every_public_page(self):
        """Pending Don's answer on keeping it at all, it stays in BOOK_CONFIGS for the owner
        preview and the research scripts, and is reachable from no public surface."""
        for name in PUBLIC_PAGES:
            t = _read(os.path.join(TPL, name))
            self.assertNotIn('value="roth"', t, "%s offers the roth construction" % name)
            self.assertNotIn("Roth / IRA", t, "%s names the roth book" % name)


class TheBacktestBesideTheRecordIsTheServedBook(unittest.TestCase):
    """ITEM 18. These assertions are the INVERSE of the ones they replace, and that is the
    point rather than a loosening.

    Session 74 made the block the TRACKED CONFIG's -- `book_configs.taxable` -- which was the
    nearest measured construction at the time and was labelled PROVISIONAL on r1's measurement
    of the exact served book. That measurement landed (`INDEX-BOOK`, `ceffd04`, 2026-10-02) and
    it is materially lower: the config path publishes +26.15% gross and +19.35% net for an
    all-cap EQUAL-WEIGHTED decile, where the served $10B score-weighted tier earns +17.1619%
    in a Roth and +12.2033% after tax.

    So the old tests asserted the block equals `S.measured(TRACKED_CONFIG)`. These assert it
    does NOT, and comes from `index_book_measured` instead.
    """

    def test_the_default_block_is_the_SERVED_book(self):
        from valuation.screener import index_track as IT
        got = IT.summarize().get("backtested") or {}
        self.assertIs(got.get("is_the_served_book"), True)
        self.assertIsNotNone(got.get("served"), "the served measurement is absent")

    def test_it_is_NOT_the_config_derived_measurement_any_more(self):
        """The strict inverse of what this class used to assert."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        got = IT.summarize().get("backtested") or {}
        cfg = S.measured(IT.TRACKED_CONFIG) or {}
        self.assertIsNotNone(cfg.get("annual_turnover"), "fixture: the config has a turnover")
        self.assertNotEqual(got.get("annual_turnover"), cfg.get("annual_turnover"),
                            "the block is still the config's book, not the served one")

    def test_every_served_figure_comes_from_the_one_authority(self):
        """Not retyped here and not recomputed there -- `index_book_measured` is the only
        place these numbers are written down."""
        from valuation.screener import index_track as IT
        from valuation.screener import index_book_measured as M
        got = IT.summarize().get("backtested") or {}
        self.assertEqual(got.get("net_sharpe"), M.SERVED_ROTH_SHARPE)
        self.assertEqual(got.get("annual_turnover"), M.SERVED_TURNOVER)
        self.assertAlmostEqual(got.get("net_alpha"), M.ALPHA_VS_ALL_CAP_EW_PP / 100.0, places=12)
        self.assertEqual((got.get("served") or {}).get("study"), M.STUDY)

    def test_the_card_the_tab_renders_is_the_served_one(self):
        from valuation.screener import index_track as IT
        card = (IT.summarize().get("backtested") or {}).get("card") or {}
        self.assertTrue(card.get("available"))
        self.assertEqual(card.get("mode"), "served")

    def test_a_NAMED_config_is_a_PREVIEW_and_says_so(self):
        """The owner preview must keep getting the book it asked for.
        `test_backtest_card` guards this from the other side and it caught the first cut of
        this change: serving the SERVED card to everyone is the same defect as serving roth's
        to everyone, pointed the other way."""
        from valuation.screener import index_track as IT
        got = IT.summarize(config="roth").get("backtested") or {}
        self.assertIs(got.get("is_the_served_book"), False)
        self.assertEqual(got.get("preview_of"), "roth")
        self.assertIn("not the Valquo Index", got.get("preview_note") or "")
        self.assertEqual((got.get("card") or {}).get("config"), "roth")

    def test_it_does_NOT_default_to_the_sites_account_type_preference(self):
        import ast
        src = _read(os.path.join(REPO, "valuation", "screener", "index_track.py"))
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "summarize")
        body = ast.unparse(fn)
        self.assertIn("TRACKED_CONFIG", body)
        self.assertNotIn("DEFAULT_BOOK_CONFIG", body,
                         "summarize still reads the site's account-type preference")

    def test_the_hero_and_the_landing_page_do_not_pin_a_construction(self):
        for mod in ("hero.py", "showcase.py"):
            src = _read(os.path.join(REPO, "valuation", "web", mod))
            self.assertNotIn('summarize("roth"', src, "%s pins roth" % mod)

    def test_the_MEASURED_BASIS_caveat_MOVES_rather_than_vanishing(self):
        """It says the config book is "not the served score-weighted large-cap book", which is
        still TRUE of the research decile and is now FALSE of the Index's own block. So it must
        no longer be the Index's `basis` -- and it must still be carried where it applies, or
        the research decile loses the sentence that distinguishes it."""
        from valuation.screener import index_track as IT
        from valuation.screener import settings as S
        got = IT.summarize().get("backtested") or {}
        self.assertNotEqual(got.get("basis"), S.MEASURED_BASIS,
                            "the Index's block still carries the config book's caveat")
        self.assertIn("large-cap tier", got.get("basis") or "",
                      "the Index's basis does not name the served construction")
        rd = got.get("research_decile") or {}
        self.assertEqual(rd.get("config_basis"), S.MEASURED_BASIS,
                         "the caveat vanished instead of moving")
        self.assertIn("not the served", S.MEASURED_BASIS)

    def test_the_tab_no_longer_claims_the_forward_column_is_the_same_BOOK(self):
        t = _flat(os.path.join(TPL, "index.html"))
        self.assertNotIn("The forward column is the same model book", t,
                         "the tab still claims the backtest and the record are one book")
        self.assertIn("same", t)


class TheResearchDecileIsNeverTheIndex(unittest.TestCase):
    """ITEM 18. The all-cap equal-weighted decile is a real published measurement and `/proof`
    reports it legitimately -- as the RESEARCH decile. It may not appear as the Index's."""

    def test_the_research_decile_is_kept_and_labelled(self):
        from valuation.screener import index_track as IT
        rd = ((IT.summarize().get("backtested") or {}).get("research_decile") or {})
        self.assertIn("RESEARCH DECILE", rd.get("label") or "")
        self.assertIs(rd.get("is_the_served_book"), False)
        self.assertIn("NOT the Valquo Index", rd.get("not_the_index") or "")

    def test_its_figures_differ_from_the_served_books(self):
        """If these ever coincided the separation would be pointless, so the test says so."""
        from valuation.screener import index_book_measured as M
        self.assertNotAlmostEqual(M.RESEARCH_NET_PCT, M.SERVED_ROTH_PCT, places=2)
        self.assertNotAlmostEqual(M.RESEARCH_ALPHA_VS_SPY_PP, M.ALPHA_VS_SPY_PP, places=2)

    def test_proof_says_the_decile_is_NOT_the_index(self):
        """`/proof` legitimately reports the research decile, and already said "equally
        weighted". What it never said is that the Index is a DIFFERENT BOOK -- so a reader
        taking that table's +8.1pp vs SPY as the Index's would be out by most of it."""
        t = _flat(os.path.join(TPL, "_proof_body.html"))
        self.assertIn("RESEARCH DECILE", t)
        self.assertIn("not the Valquo Index", t)
        self.assertIn("large-cap tier", t)

    def test_proof_still_reports_the_decile_rather_than_hiding_it(self):
        """The label is the fix, not deletion: it is a real published measurement."""
        t = _flat(os.path.join(TPL, "_proof_body.html"))
        self.assertIn("Top decile", t)
        self.assertIn("equally weighted", t)

    def test_the_two_blocks_are_separate_calls(self):
        """`block()` and `research_block()` are distinct, so a surface cannot reach both
        through one call and render them interchangeably -- which is how the research decile
        came to be published as the Index."""
        from valuation.screener import index_book_measured as M
        self.assertIsNot(M.block, M.research_block)
        self.assertNotIn("net_pct", M.block())
        self.assertNotIn("roth", M.research_block())


class NoPublicSurfaceQuotesAResearchFigureUnlabelled(unittest.TestCase):
    """ITEM 22, BROADENING ITEM 18 FROM ONE CARD TO EVERY SURFACE.

    Item 18 corrected the Index tab. The survey item 22 asked for found the same figures still
    presented as the product in three more places, each of which had been correct about its
    arithmetic and silent about its object:

      * the landing page and `/methodology` on S22's registered sentence -- "the top decile of
        the hot list beat the equal-weighted universe by about 6.6% annualized";
      * `/methodology` and the portfolio page on R1's factor intercept, "+6.99%/yr (t = 3.98)";
      * `/proof` on the decile ladder and the quarterly distribution, where only the
        benchmarks table carried a label.

    None of those is a wrong number. Every one is the RESEARCH DECILE -- the ranking across all
    ~2,500 companies, equally weighted, top 10% -- and INDEX-BOOK measured how differently the
    served book earns: +4.1209pp against an equal-weighted basket of its own large-cap tier and
    MINUS 0.0576pp against the all-cap equal-weighted universe those figures are measured
    against. A reader lifting one of them as the Index's is out by most of it.

    THE RULE THIS PINS: if a public surface quotes a research-decile figure, that surface must
    also say which book it is. The guard is at PAGE level, not sentence level, and deliberately:
    a sentence-level rule would require the clause to be pasted beside every figure, which is
    four hand-maintained copies of one fact. A page-level rule is also the honest scope -- the
    object is a property of the page, not of any one card.
    """

    #: (relative path, the figures that make it a research-decile surface). Figures as the
    #: STRINGS the page prints, because that is what a reader sees.
    SURFACES = (
        (os.path.join("valuation", "web", "hold_horizon.py"), ("6.6", "5.1")),
        (os.path.join("valuation", "web", "templates", "methodology.html"), ("6.99",)),
        (os.path.join("valuation", "web", "templates", "portfolio.html"), ("6.99",)),
        (os.path.join("valuation", "web", "templates", "_proof_body.html"), ()),
    )

    #: Any ONE of these, present on the page, discharges the obligation. Several spellings
    #: because the four surfaces are prose, template and Python, and forcing one wording on
    #: all three would be a style rule masquerading as a safety rule.
    LABELS = ("not the Valquo Index", "NOT the Valquo Index",
              "not the Valquo\u00a0Index", "RESEARCH DECILE", "research decile")

    @staticmethod
    def _rendered(path):
        """The text a READER sees: comments stripped.

        A DEFECT IN THIS SWEEP'S OWN FIRST CUT, found by driving it rather than reading it.
        It searched the raw file, and the item-22 change had added a Jinja comment to each
        template EXPLAINING the rule -- which quotes the label. So deleting the user-visible
        label left the comment behind and the guard passed. Three of seven mutations walked
        through.

        That is this project's most repeated test defect in its inverted form: not a ban
        tripped by prose, but a POSITIVE assertion satisfied by prose. A guard that cannot
        tell code from comments about code is not measuring the page.
        """
        txt = io.open(path, encoding="utf-8").read()
        if path.endswith(".py"):
            out = []
            for line in txt.split("\n"):
                i = line.find("#")
                # Crude but sound in the only direction that matters: a `#` inside a string
                # loses text from the RENDERED side, so the guard can only get STRICTER.
                out.append(line if i < 0 else line[:i])
            return "\n".join(out)
        # Jinja and HTML comments.
        txt = re.sub(r"\{#.*?#\}", " ", txt, flags=re.S)
        txt = re.sub(r"<!--.*?-->", " ", txt, flags=re.S)
        return txt

    @staticmethod
    def _depths(txt):
        """`{% if %}` nesting depth at every character position, as a list of (pos, depth).

        WHY DEPTH AND NOT "IS IT CONDITIONAL AT ALL" -- a correction to this test's own first
        cut, which asserted the label was outside every `{% if %}` and FAILED against the
        correct tree. The whole of `_proof_body.html` sits in the `{% else %}` branch of
        `{% if not p.available %}`, and that is right: when the evidence file cannot be read
        the page shows nothing rather than numbers from memory. So "unconditional" is
        unreachable and was the wrong property.

        The property that matters is RELATIVE. Each figure-bearing section is its own
        `{% if p.deciles %}` / `{% if p.benchmarks %}` / `{% if p.distribution %}`, all at the
        same depth. A label must sit at that depth or shallower, so that it renders whenever
        any one of them does. The label that used to be inside the benchmarks block was one
        level DEEPER than the sections, which is exactly how a deploy missing that one block
        would have printed a decile ladder with nothing naming the book.
        """
        marks, depth, pos = [], 0, 0
        for m in re.finditer(r"\{%-?\s*(if|else|endif)\b", txt):
            marks.append((pos, m.start(), depth))
            kind = m.group(1)
            if kind == "if":
                depth += 1
            elif kind == "endif":
                depth = max(0, depth - 1)
            pos = m.end()
        marks.append((pos, len(txt), depth))
        return marks

    @classmethod
    def _min_depth_of(cls, txt, needles):
        """The shallowest `{% if %}` depth at which any of `needles` appears, or None."""
        best = None
        for a, b, depth in cls._depths(txt):
            chunk = txt[a:b]
            if any(n in chunk for n in needles):
                best = depth if best is None else min(best, depth)
        return best

    @staticmethod
    def _opener_depth(txt, conds):
        """The shallowest depth at which any `{% if <cond> %}` TAG itself sits.

        A SEPARATE FUNCTION, and the reason is a defect in this test's second cut: `_depths`
        slices the template AT the tags, so a tag's own text is never inside any slice and
        `_min_depth_of(txt, ("{% if p.deciles %}",))` returned `None` for a section that is
        plainly there. A section's depth is a property of its OPENER, not of its contents --
        its contents are one level deeper, which is the off-by-one that makes the comparison
        wrong rather than merely unanswerable.
        """
        best, depth = None, 0
        for m in re.finditer(r"\{%-?\s*(if|endif)\b([^%]*)%\}", txt):
            kind, rest = m.group(1), m.group(2)
            if kind == "if":
                if any(c in rest for c in conds):
                    best = depth if best is None else min(best, depth)
                depth += 1
            else:
                depth = max(0, depth - 1)
        return best

    def test_every_surface_quoting_a_research_figure_names_the_book(self):
        for rel, figures in self.SURFACES:
            path = os.path.join(REPO, rel)
            with self.subTest(rel):
                self.assertTrue(os.path.exists(path), rel)
                raw = io.open(path, encoding="utf-8").read()
                for f in figures:
                    self.assertIn(f, raw,
                                  "%s no longer carries the figure %s. If it was removed this "
                                  "entry should go; if it moved, point this at the new "
                                  "surface." % (rel, f))
                vis = self._rendered(path)
                self.assertTrue(any(l in vis for l in self.LABELS),
                                "%s quotes a research-decile figure and never says which book "
                                "it is, outside of comments. One of %r must appear in text the "
                                "reader sees." % (rel, self.LABELS))

    def test_proofs_label_is_no_deeper_than_the_sections_it_must_cover(self):
        """THE STRONGER FORM, and the mutation that exposed the need for it.

        `/proof` prints research figures from four independent `{% if %}` blocks -- the
        placebo, the benchmarks table, the decile ladder and the quarterly distribution. Its
        only label used to live inside the BENCHMARKS block, one level deeper than the
        sections, so a payload missing that one section would have rendered the ladder and the
        distribution with nothing saying which book they describe. A sweep that only asks
        "does the label appear in this file" cannot see that, and the mutation walked through.
        """
        vis = self._rendered(os.path.join(TPL, "_proof_body.html"))
        sections = ("p.deciles", "p.benchmarks", "p.distribution")
        sec_depth = self._opener_depth(vis, sections)
        self.assertIsNotNone(sec_depth,
                             "no figure-bearing section found; has /proof been rewritten?")
        lab_depth = self._min_depth_of(vis, self.LABELS)
        self.assertIsNotNone(lab_depth, "/proof carries no visible research-decile label")
        self.assertLessEqual(
            lab_depth, sec_depth,
            "/proof's label sits at {%% if %%} depth %r while its figure sections sit at %r, "
            "so a deploy missing one section would print research figures with the label gone."
            % (lab_depth, sec_depth))

    def test_the_comment_stripper_is_not_vacuous(self):
        """A stripper that returned "" would make every assertion above pass by seeing
        nothing, so prove it keeps the text and drops the comments."""
        path = os.path.join(TPL, "_proof_body.html")
        vis = self._rendered(path)
        self.assertIn("RESEARCH DECILE", vis, "the stripper removed the visible label too")
        self.assertNotIn("the B7 disease", vis,
                         "the stripper left a Jinja comment in the visible text")
        # And on the Python surface.
        hh = self._rendered(os.path.join(REPO, "valuation", "web", "hold_horizon.py"))
        self.assertIn("not the Valquo Index", hh)
        self.assertNotIn("IT IS NOT SPLICED INTO", hh,
                         "the stripper left a Python comment in the visible text")

    def test_the_depth_measure_is_not_vacuous(self):
        """Driven on a synthetic template, including the shape the real defect had."""
        t = "TOP {% if a %}ONE {% if b %}TWO{% endif %}{% endif %} ALSO-TOP"
        self.assertEqual(self._min_depth_of(t, ("TOP",)), 0)
        self.assertEqual(self._min_depth_of(t, ("ALSO-TOP",)), 0)
        self.assertEqual(self._min_depth_of(t, ("ONE",)), 1)
        self.assertEqual(self._min_depth_of(t, ("TWO",)), 2)
        self.assertIsNone(self._min_depth_of(t, ("ABSENT",)))
        # An `{% else %}` branch is at its `{% if %}`'s own inner depth, not shallower --
        # otherwise the whole of /proof would read as depth 0 and the measure would be inert.
        e = "{% if x %}A{% else %}B{% endif %}"
        self.assertEqual(self._min_depth_of(e, ("A",)), 1)
        self.assertEqual(self._min_depth_of(e, ("B",)), 1)
        # THE REAL DEFECT'S SHAPE: a label one level deeper than the sections must be refused.
        bad = ("{% if avail %}{% if p.deciles %}LADDER{% endif %}"
               "{% if p.benchmarks %}not the Valquo Index{% endif %}{% endif %}")
        self.assertEqual(self._opener_depth(bad, ("p.deciles",)), 1)
        self.assertEqual(self._min_depth_of(bad, self.LABELS), 2)
        self.assertGreater(self._min_depth_of(bad, self.LABELS),
                           self._opener_depth(bad, ("p.deciles",)),
                           "the depth measure cannot see the defect it exists for")
        # AND THE FIXED SHAPE MUST PASS, or the guard is unsatisfiable.
        good = ("{% if avail %}not the Valquo Index{% if p.deciles %}LADDER{% endif %}"
                "{% endif %}")
        self.assertLessEqual(self._min_depth_of(good, self.LABELS),
                             self._opener_depth(good, ("p.deciles",)))

    def test_the_label_is_in_the_rendered_caveat_and_not_only_in_a_comment(self):
        """A comment explaining the rule is not the rule. `hold_horizon` is Python, so the
        figure's own page reaches the reader through `caveat()` -- assert the returned string.
        """
        from valuation.web import hold_horizon as H
        cav = H.caveat()
        self.assertIn("not the Valquo Index", cav,
                      "the mandatory caveat does not name the book: " + cav[:200])
        self.assertIn("~2,500", cav)
        self.assertIn("top 10%", cav)

    def test_the_registered_research_sentence_is_NOT_rewritten(self):
        """THE OTHER HALF, and it is why the label is appended rather than spliced.

        `DEFENSIBLE` is quoted verbatim from the handoff and `tests/test_hold_horizon.py` pins
        it. Editing it to fix a PRODUCT problem would silently restate a RESEARCH claim, which
        is the thing this project treats as most serious. So the research sentence is untouched
        and the label travels beside it.
        """
        from valuation.web import hold_horizon as H
        self.assertNotIn("Valquo Index", H.DEFENSIBLE)
        self.assertNotIn("~2,500", H.DEFENSIBLE)
        self.assertIn("the top decile of the hot list beat the equal-weighted universe",
                      H.DEFENSIBLE)

    def test_the_label_travels_with_the_sentence_in_one_payload(self):
        """A label in a different template from the figure is a label nobody reads."""
        from valuation.web import hold_horizon as H
        t = H.for_template()
        self.assertIn("defensible", t)
        self.assertIn("caveat", t)
        self.assertIn("research_object", t)
        self.assertIn("not the Valquo Index", t["research_object"])

    def test_the_vacuity_control_the_label_sweep_can_fail(self):
        """A sweep whose obligation nothing could violate measures nothing.

        Driven rather than asserted: a surface quoting a figure with no label must be refused.
        """
        raw = "the top decile returned 6.99%/yr and nothing else is said"
        self.assertFalse(any(l in raw for l in self.LABELS),
                         "the label set matches text that names no book, so the sweep would "
                         "pass on an unlabelled page")


class DonsStandingRulesOnWhatMayBeClaimed(unittest.TestCase):
    """Two claims Don has ruled out by name, pinned so they cannot drift back in.

    Both are about the INDEX, which is the product, and both were reachable from figures that
    are individually true -- which is exactly why a rule rather than a judgement is wanted.
    """

    #: Every public surface. The portfolio page is mounted at a configurable path and the
    #: others are fixed, but all four are rendered to people who are not Don.
    PUBLIC = ("index.html", "landing.html", "methodology.html", "portfolio.html",
              "_proof_body.html")

    def _public_text(self):
        out = {}
        for name in self.PUBLIC:
            p = os.path.join(TPL, name)
            if os.path.exists(p):
                out[name] = io.open(p, encoding="utf-8").read()
        p = os.path.join(REPO, "valuation", "web", "static", "app.js")
        out["app.js"] = io.open(p, encoding="utf-8").read()
        return out

    def test_no_surface_claims_32_percent(self):
        """Don's rule, by name. The figure is reachable -- it is roughly the research decile's
        gross top-decile return in some windows -- and it is not the Index's and not net."""
        for name, txt in self._public_text().items():
            with self.subTest(name):
                for banned in ("+32%", "32%/yr", "32% a year", "32% per year"):
                    self.assertNotIn(banned, txt,
                                     "%s claims %r, which Don has ruled out" % (name, banned))

    def test_no_surface_claims_the_index_beats_spy(self):
        """The honest line is "about 2 points a year ahead of SPY in a Roth over 2009-2026,
        almost all of it in the first half" -- a dated, halved, account-type-qualified
        statement. "The Index beats SPY" is the unqualified version of it."""
        banned = ("Index beats SPY", "Index beats the S&P", "beats SPY",
                  "outperforms SPY", "beat SPY")
        for name, txt in self._public_text().items():
            with self.subTest(name):
                for b in banned:
                    self.assertNotIn(b, txt,
                                     "%s claims %r. The qualified form is required: ahead by "
                                     "about 2 points a year in a Roth over 2009-2026, with "
                                     "almost all of it in the first half." % (name, b))

    def test_the_vacuity_control_these_bans_can_fire(self):
        """The ban strings must actually match the sentences they forbid."""
        self.assertIn("+32%", "the book returned +32% a year")
        self.assertIn("beats SPY", "the Valquo Index beats SPY over the sample")

    def test_the_sentence_that_IS_allowed_is_available_to_a_surface(self):
        """Refusing a claim is only half of it: the qualified version has to exist somewhere a
        page can render, or a writer reaches for the banned one."""
        from valuation.screener import index_book_measured as M
        card = M.card()
        halves = (card.get("halves_note") or "")
        self.assertTrue(halves, "the card carries no halves note, so the 'almost all of it in "
                                "the first half' qualification has no source")
        self.assertIn("3.7", halves)
        self.assertIn("0.2", halves)


class BothAlphaSentencesTravelTogether(unittest.TestCase):
    """`INDEX-BOOK`'s ledger row states it as a void condition: "BOTH ALPHA SENTENCES ARE TRUE
    AND NEITHER MAY TRAVEL ALONE." Against its own large-cap tier the served book earns
    +4.1209pp, stable across halves; against the all-cap equal-weighted universe -- the
    benchmark every older published figure used -- it earns -0.0576pp, i.e. nothing. Roughly
    70% of the gap is the small-cap premium a large-cap tier declines to hold."""

    def _alpha(self):
        from valuation.screener import index_track as IT
        return (((IT.summarize().get("backtested") or {}).get("served") or {}).get("alpha") or {})

    def test_both_legs_are_present(self):
        a = self._alpha()
        self.assertIsNotNone(a.get("vs_own_tier_pp"))
        self.assertIsNotNone(a.get("vs_all_cap_ew_pp"))

    def test_one_sentence_carries_BOTH_figures(self):
        """So a surface cannot render the favourable leg and drop the other."""
        s = self._alpha().get("both_sentence") or ""
        self.assertIn("+4.1209", s)
        self.assertIn("-0.0576", s)
        self.assertIn("small-cap premium", s)

    def test_the_vs_SPY_halves_are_shown_and_not_averaged(self):
        a = self._alpha()
        self.assertAlmostEqual(a.get("vs_spy_early_pp"), 3.7202, places=4)
        self.assertAlmostEqual(a.get("vs_spy_late_pp"), 0.2702, places=4)
        s = a.get("vs_spy_sentence") or ""
        self.assertIn("+3.7202", s)
        self.assertIn("+0.2702", s)
        self.assertIn("rather than averaged", s)

    def test_the_own_tier_halves_are_shown_as_stable(self):
        a = self._alpha()
        self.assertAlmostEqual(a.get("vs_own_tier_early_pp"), 4.0615, places=4)
        self.assertAlmostEqual(a.get("vs_own_tier_late_pp"), 4.1746, places=4)
        self.assertIn("stable", a.get("both_sentence") or "")


class TheIndexIsARothProduct(unittest.TestCase):
    """18-AMEND, Don 2026-10-03. Every backtest figure leads with the Roth/IRA treatment; the
    taxable figure sits beside it for a regular brokerage account, shown for transparency --
    and transparency has a cost that must be stated, not left to be derived."""

    def _served(self):
        from valuation.screener import index_track as IT
        return ((IT.summarize().get("backtested") or {}).get("served") or {})

    def test_roth_LEADS(self):
        sv = self._served()
        self.assertEqual(sv.get("lead"), "roth")
        self.assertIn("Roth", sv["roth"]["label"])

    def test_the_card_puts_roth_FIRST(self):
        """The order on the page, not only in the payload."""
        from valuation.screener import index_track as IT
        lines = ((IT.summarize().get("backtested") or {}).get("card") or {}).get("lines") or []
        levels = [l for l in lines if l.get("kind") == "level"]
        self.assertGreaterEqual(len(levels), 2)
        self.assertEqual(levels[0].get("key"), "roth")
        self.assertEqual(levels[1].get("key"), "taxable")

    def test_the_taxable_leg_carries_Dons_wording(self):
        lbl = self._served()["taxable"]["label"]
        self.assertIn("regular brokerage account", lbl)
        self.assertIn("transparency", lbl)

    def test_the_taxable_leg_says_it_lands_BELOW_spy(self):
        """The cost of transparency. A reader must not have to difference two fields to find
        that the after-tax book underperforms the benchmark the site quotes."""
        t = self._served()["taxable"]
        self.assertAlmostEqual(t.get("vs_spy_pp"), -3.03, places=2)
        s = t.get("below_spy_sentence") or ""
        self.assertIn("BELOW SPY", s)
        self.assertIn("3.03", s)
        self.assertIn("short-term", s)

    def test_the_tax_cost_is_a_clean_difference_on_ONE_lot_path(self):
        from valuation.screener import index_book_measured as M
        sv = self._served()
        self.assertAlmostEqual(sv.get("tax_cost_pp"), M.TAX_COST_PP, places=4)
        self.assertAlmostEqual(
            sv["roth"]["return_pct"] - sv["taxable"]["return_pct"], M.TAX_COST_PP, places=3,
            msg="the stated tax cost is not the difference between the two legs")
        self.assertIn("only knob", sv.get("tax_cost_sentence") or "")

    def test_the_dividend_caveat_runs_against_the_taxable_arm_and_travels(self):
        sv = self._served()
        c = sv.get("dividend_caveat") or ""
        self.assertIn("no dividends", c)
        self.assertIn("understates", c)

    def test_PROVISIONAL_is_gone_and_the_study_is_named_instead(self):
        """The label existed only until r1's measurement landed. It has, so the block must now
        cite it rather than promise it."""
        from valuation.screener import index_track as IT
        bt = IT.summarize().get("backtested") or {}
        sv = bt.get("served") or {}
        self.assertEqual(sv.get("study"), "INDEX-BOOK")
        self.assertTrue(sv.get("study_commit"))
        self.assertNotIn("PROVISIONAL", str(bt.get("served")))
        # And what WOULD replace these is named, so the next change is not a surprise.
        self.assertIn("INDEX-BEST", sv.get("pending") or "")

    def test_the_spec_describes_the_served_measurement(self):
        spec = _read(os.path.join(REPO, "PRODUCT_SPEC.md"))
        self.assertIn("INDEX-BOOK", spec)
        self.assertIn("17.1619", spec)
        self.assertIn("12.2033", spec)
        self.assertIn("Roth", spec)


class NoPublicPageStatesAContradictoryCadence(unittest.TestCase):
    """(3) The cadence claims, which is where eleven of the wrong sentences lived."""

    def test_no_page_says_the_INDEX_holdings_are_rebuilt_daily(self):
        for name in PUBLIC_PAGES:
            t = _flat(os.path.join(TPL, name))
            for bad in ("The holdings are rebuilt from each day's scan",
                        "separate, fixed book"):
                self.assertNotIn(bad, t, "%s: %r" % (name, bad))

    def test_no_page_says_the_LIVE_LIST_re_ranks_quarterly(self):
        """E1. The live list re-ranks every close; the BACKTEST re-ranked quarterly. One
        sentence giving the quarterly cadence for the live list is wrong."""
        from valuation.web import hold_horizon as HH
        t = HH.NOT_A_HOLD_RULE
        # THE QUOTED RESEARCH CLAUSE STAYS -- `tests/test_hold_horizon.py` pins that this
        # opens with §7's registered sentence verbatim, and rewriting a research sentence to
        # fix a product one is not the repair. What must be present is the SCOPE that was
        # missing: whose cadence that is, and what the other two are.
        self.assertIn("That quarterly cadence is the BACKTEST's", t)
        self.assertIn("re-ranked after every market close", t)
        self.assertIn("only at a quarterly rebalance", t)

    def test_the_index_tab_states_the_held_cadence(self):
        t = _flat(os.path.join(TPL, "index.html"))
        self.assertIn("ONE FIXED BOOK, HELD FOR THE QUARTER", t)
        self.assertIn("not a daily pick", t)

    def test_the_INDEX_record_is_not_described_as_a_broker_sandbox(self):
        """E4. Only the options book is in a sandbox. Both pages conflated them."""
        for name in ("methodology.html", "portfolio.html"):
            t = _flat(os.path.join(TPL, name))
            self.assertIn("sandbox", t, "fixture assumption: the page discusses the sandbox")
            self.assertIn("options", t.lower())
            # The giveaway phrasing: one list of "every one of them" ending in a sandbox.
            self.assertNotIn("every one of them is a paper record: a model book priced at "
                             "closing marks, and a broker sandbox", t, name)


class ThresholdsAreStatedOnce(unittest.TestCase):

    def test_the_sharpe_gate_defers_to_the_headline_gate(self):
        """E6. 20 against 60 put a Sharpe on the same card as a sentence withholding
        annualised figures."""
        from valuation.screener import index_track as IT
        self.assertEqual(IT.MIN_SHARPE_DAYS, IT.MIN_LIVE_DAYS,
                         "there are two day-count gates on one card again")

    def test_the_spec_states_the_gates_and_they_match_the_code(self):
        from valuation.screener import index_track as IT
        from valuation.screener import index_in_force as IF
        t = _flat(SPEC)
        self.assertIn("%d trading days" % IT.MIN_LIVE_DAYS, t)
        self.assertIn("%d trading days" % IF.REBALANCE_TRADING_DAYS, t)

    def test_the_recorded_series_is_described_as_GROSS(self):
        """E5. The chart said "net of modelled costs"; the record subtracts none."""
        js = _read(JS)
        self.assertIn("GROSS of costs", js)
        self.assertIn("0.14529", js, "the drag the verdict subtracts is not named")
        self.assertNotIn("net of modelled costs. No capital is invested", js)


class NumbersArePulledNotTyped(unittest.TestCase):
    """E9, E12 -- the literal-figure class."""

    def test_no_public_page_hard_codes_a_trial_count_or_the_universe_size(self):
        for name in PUBLIC_PAGES + ["_saas_base.html"]:
            t = _read(os.path.join(TPL, name))
            self.assertNotIn("~800", t, "%s hard-codes the universe size" % name)
            for n in ("248", "578", "252", "582"):
                self.assertNotIn(">%s<" % n, t,
                                 "%s hard-codes a trial count (%s)" % (name, n))

    def test_the_live_facts_degrade_to_no_number_rather_than_a_wrong_one(self):
        from valuation.web import live_facts as LF
        got = LF.universe_size(store=object())      # a store with no methods
        self.assertFalse(got["available"])
        self.assertIsNone(got["n"])
        self.assertTrue(got["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
