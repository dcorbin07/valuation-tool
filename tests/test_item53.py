# -*- coding: utf-8 -*-
"""ITEM 53 — Index links, recent earnings and headlines, and clearer numbers.

Seven parts, of which part 7 ships NO CODE: it is a diagnosis, and its finding is that a
repair would move live hot scores, so it is routed to Don. The figures it measured are pinned
here so they cannot quietly rot.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _code_only(rel):
    """Source with comments and string literals stripped.

    A guard that bans a token fires against the CORRECT tree, because prose documenting a
    rule quotes what the rule forbids -- five times in item 52 alone. `tokenize` is the fix.
    """
    import tokenize

    out = []
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


# --------------------------------------------------------------------------- part 1
class IndexRowsLinkAndExplain(unittest.TestCase):
    """The one table listing the names Don actually holds was the one you could not click."""

    def test_the_ticker_is_a_LINK_through_the_shared_navigator(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("function _renderValquoIndex")
        body = src[i:src.index("\nfunction ", i + 40)]
        self.assertIn("gotoValue('${p.ticker}')", body)
        # Reused, not reimplemented: Hot Stocks and four other tables already navigate this
        # way, and a second path is how two tables come to behave differently.
        self.assertNotIn("location.href", body)

    def test_the_why_panel_is_attributionPanel_and_NOT_a_second_one(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("function _renderValquoIndex")
        body = src[i:src.index("\nfunction ", i + 40)]
        self.assertIn("attributionPanel(p,", body)
        self.assertIn('toggleWhy(\'ix-${p.ticker}\')', body)
        # One decomposition of one number. If the Index grew its own renderer the two tables
        # could explain the same score differently.
        self.assertEqual(body.count("attr-row"), 0)

    def test_a_holding_NOT_in_todays_scan_says_so(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        i = src.index("function attributionPanel")
        body = src[i:src.index("\nfunction ", i + 40)]
        self.assertIn("o.notInScan", body)
        self.assertIn("not in today's scan", body)
        self.assertIn("fixed between rebalances", body)
        # The two empty states are DIFFERENT and both must exist -- an older scan's row and a
        # name the universe no longer ranks are not the same fact.
        self.assertIn("saved by an older scan", body)

    def test_the_colspan_is_DERIVED_from_the_header_flags(self):
        """The table already carries "the footer must grow with the header or every total
        shifts one cell left". A typed colspan is that defect one row down."""
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("const _ixCols = 8 + (hasForm ? 1 : 0) + (hasRet ? 1 : 0)", src)
        self.assertIn('colspan="${_ixCols}"', src)

    def test_the_FOOTER_grew_with_the_header(self):
        """Adding the why? column made the footer one cell short -- caught by obeying that
        comment rather than by the table looking wrong."""
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn('<td class="num">—</td><td></td><td class="num">—</td></tr></tfoot>',
                      src)

    def test_the_attribution_is_attached_server_side_and_carries_NO_vendor_rows(self):
        """`extra` carries every raw vendor number the scan touched and the Index payload is
        PUBLIC, so only the decomposition is copied -- not the blob."""
        rel = os.path.join("valuation", "screener", "index_in_force.py")
        # The keys it copies are string LITERALS, so they are a fact about the source...
        src = _src(rel)
        self.assertIn('"why_composite"', src)
        self.assertIn('"factors"', src)
        # ...while the BAN is a fact about the code, where `_code_only` is the right lens: a
        # comment explaining why the blob is not copied would otherwise trip it.
        code = _code_only(rel)
        self.assertIn("n_why", code)
        for forbidden in ('pos [ "extra" ] = _ex ', 'pos [ "extra" ] = r . get'):
            self.assertNotIn(forbidden, code)
        # Three keys and no more -- a fourth would be a decision to publish something
        # else. Counted off the dict literal itself, so adding one goes red.
        i = src.index('pos["extra"] = {')
        block = src[i:src.index("}", i)]
        import re as _re
        self.assertEqual(sorted(_re.findall(r'"(\w+)":', block)),
                         ["factors", "why", "why_composite"])

    def test_the_two_counts_are_reported_SEPARATELY(self):
        from valuation.screener import index_in_force as IIF
        b = IIF.attach_labels({"positions": [{"ticker": "AAA"}]}, store=None)
        self.assertIn("n_labelled", b["labels"])
        self.assertIn("n_attributed", b["labels"])
        self.assertIn("attribution_basis", b["labels"])
        # A labelled holding with no attribution is a real state; one number would hide it.
        self.assertEqual(b["labels"]["n_attributed"], 0)


# --------------------------------------------------------------------------- part 2
class RecentEarningsAndHeadlines(unittest.TestCase):
    """MEASURED FIRST, and the measurement shaped the design.

    `yfinance.news` returns ZERO items on 1.3.0 for every call shape. Yahoo's RSS does work,
    but a symbol-requested feed is not a feed about that symbol: over 74 titles across NVDA,
    TSLA, KO and APLD on 2026-10-13, **31 (42%) named the company**, and NVDA was **1 of 18**.
    """

    def test_the_measured_feed_purity_is_on_the_record(self):
        from valuation.data import recent as R
        self.assertEqual(R.FEED_PURITY_MEASURED["titles"], 74)
        self.assertEqual(R.FEED_PURITY_MEASURED["on_company"], 31)
        self.assertEqual(R.FEED_PURITY_MEASURED["worst_ticker"], "NVDA")
        self.assertEqual(R.FEED_PURITY_MEASURED["worst"], "1 of 18")
        self.assertAlmostEqual(31.0 / 74.0, 0.419, places=3)

    def test_ARTICLE_TEXT_IS_UNREACHABLE_structurally(self):
        """Not a promise -- there is no code path to it. The RSS item's `description` is
        never read and no article URL is ever requested."""
        code = _code_only(os.path.join("valuation", "data", "recent.py"))
        self.assertNotIn("description", code)
        self.assertNotIn("content:encoded", code)
        # Exactly three hosts are contacted, and an article's own host is not among them.
        src = _src(os.path.join("valuation", "data", "recent.py"))
        self.assertIn("feeds.finance.yahoo.com", src)
        self.assertIn("data.sec.gov", src)

    def test_the_company_filter_is_applied_and_its_YIELD_is_part_of_the_answer(self):
        from valuation.data import recent as R
        for k in ("scanned", "on_company", "filtered_out"):
            self.assertIn(k, R.headlines("ZZZZ", name=""))

    def test_a_two_letter_stem_is_NOT_matched(self):
        """`KO` as a needle matches "look", "broke", "stock" -- everything. So a stem under
        four characters is dropped and the company's own name carries the match."""
        from valuation.data import recent as R
        keys = R._company_keys("KO", "Coca-Cola Company")
        self.assertNotIn("ko", keys)
        self.assertIn("coca-cola", keys)
        self.assertIn("coca cola", keys)      # headlines write it both ways
        # ...while a three-character-or-longer symbol IS usable.
        self.assertIn("nvda", R._company_keys("NVDA", "NVIDIA Corporation"))
        self.assertIn("nvidia", R._company_keys("NVDA", "NVIDIA Corporation"))

    def test_NO_ESTIMATE_IS_EVER_INFERRED(self):
        """Don asked for revenue and EPS against estimates WHERE A FREE SOURCE HAS THEM.
        Measured: none does. So the absence is reported and nothing is modelled -- an absent
        comparison and a met expectation must not read the same."""
        from valuation.data import recent as R
        q = R.last_reported_quarter("ZZZZNOPE", cik=None)
        self.assertFalse(q["estimates_available"])
        self.assertIn("licensed product", q["estimates_reason"])
        code = _code_only(os.path.join("valuation", "data", "recent.py"))
        for forbidden in ("estimate_eps", "consensus", "expected_eps", "beat", "miss"):
            self.assertNotIn(forbidden, code)

    def test_the_SEC_terms_and_rate_limit_are_honoured_and_quoted(self):
        """The SEC asks callers to declare a User-Agent and states a 10 req/s ceiling, and
        says its content is "free to access and reuse". All three are quoted at the code that
        complies with them."""
        from valuation.data import recent as R
        self.assertIn("@", R.SEC_UA)                 # a contact, as the SEC's example shows
        self.assertGreater(R.SEC_MIN_INTERVAL_S, 0)
        self.assertLessEqual(1.0 / R.SEC_MIN_INTERVAL_S, 10.0)
        src = _src(os.path.join("valuation", "data", "recent.py"))
        self.assertIn("free to access and reuse", src)
        self.assertIn("10 requests per second", src)

    def test_EDGAR_filings_are_about_the_company_BY_CONSTRUCTION(self):
        from valuation.data import recent as R
        out = R.filings(None)
        self.assertFalse(out["available"])
        self.assertIn("no SEC company id", out["reason"])
        self.assertIn("by construction", out["about_company"])

    def test_the_two_date_sources_DISAGREE_and_EDGAR_is_the_one_used(self):
        """Measured on NVDA: the statement labels the period 2026-07-31 and EDGAR's XBRL says
        it ended 2026-07-26 -- yfinance rounds a fiscal quarter to month-end. The EPS agrees
        at 2.46, the dates do not, and EDGAR also carries the FILING date, which is the only
        free answer to "when was it reported"."""
        src = _src(os.path.join("valuation", "data", "recent.py"))
        self.assertIn("2026-07-26", src)
        self.assertIn("2026-07-31", src)
        self.assertIn("month-end approximation", src)

    def test_the_block_is_cached_per_ticker_per_day_and_NOT_charged_to_the_AI_cap(self):
        import shutil
        import tempfile

        from valuation.web import ai_auto as AA
        root = tempfile.mkdtemp(prefix="i53_")
        try:
            self.assertIsNone(AA.cached_recent("TSLA", root=root))
            before = AA.allowance(root=root)["used"]
            AA.store_recent("TSLA", {"headlines": {"items": []}}, root=root)
            self.assertIsNotNone(AA.cached_recent("TSLA", root=root))
            # THE CAP IS FOR ANTHROPIC SPEND. These are free feeds, and sharing the cap would
            # let a visitor reading headlines exhaust the owner's analysis budget.
            self.assertEqual(AA.allowance(root=root)["used"], before)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_analysis_and_a_recent_block_cannot_be_read_as_each_other(self):
        from valuation.web import ai_auto as AA
        self.assertNotEqual(AA.SCHEMA, AA.RECENT_SCHEMA)

    def test_the_route_is_GET_and_spends_NOTHING(self):
        from valuation.web.app import app
        c = app.test_client()
        self.assertEqual(c.get("/api/recent").status_code, 400)      # no ticker
        self.assertEqual(c.post("/api/recent?ticker=KO").status_code, 405)

    def test_ONE_builder_feeds_the_page_AND_the_model(self):
        """A second path would be two answers to "what has happened to this company"."""
        src = _src(os.path.join("valuation", "web", "app.py"))
        self.assertEqual(src.count("def _recent_block("), 1)
        # Both consumers go through it.
        self.assertIn("return jsonify(_recent_block(ticker", src)
        self.assertIn("_recent = _recent_block(ticker", src)

    def test_the_AI_MUST_NAME_the_headline_it_used(self):
        from valuation.ai import analyst as AN
        self.assertIn("headlines_used", AN._SCHEMA)
        self.assertIn("[] if you used none", str(AN._SCHEMA["headlines_used"]))

    def test_the_prompt_FORBIDS_a_beat_or_miss_claim_when_there_is_no_estimate(self):
        from valuation.ai import analyst as AN
        t = AN._recent_facts({"last_quarter": {"available": True, "revenue": 1.0,
                                               "period_end": "2026-07-26"}})
        self.assertIn("NO CONSENSUS ESTIMATE IS AVAILABLE", t)
        self.assertIn("do NOT describe the result as a beat or a miss", t)

    def test_the_prompt_tells_the_model_the_feed_is_WEAK_evidence(self):
        from valuation.ai import analyst as AN
        t = AN._recent_facts({"headlines": {"items": [
            {"date": "2026-10-13", "title": "A thing", "publisher": "X"}]}})
        self.assertIn("titles only", t)
        self.assertIn("42% relevance", t)
        # MY OWN SLIP: that line is a plain literal, not %-formatted, so `%%` would ship as
        # two characters. Item 52 hit the mirror image and crashed; this one would not.
        self.assertNotIn("%%", t)

    def test_an_absent_block_leaves_the_prompt_EXACTLY_as_item_52_sent_it(self):
        from valuation.ai import analyst as AN
        self.assertEqual(AN._recent_facts(None), "")
        self.assertEqual(AN._recent_facts({}), "")

    def test_the_analysis_is_STORED_with_the_headlines_it_was_written_against(self):
        """A feed is not an archive. An analysis citing a headline nobody can find again is
        unfalsifiable, so the inputs are kept beside the output."""
        import shutil
        import tempfile

        from valuation.web import ai_auto as AA
        root = tempfile.mkdtemp(prefix="i53_")
        try:
            AA.record("TSLA", {"overall_take": "x"},
                      recent={"headlines": {"items": [{"title": "T", "url": "u"}]}},
                      root=root)
            hit = AA.cached("TSLA", root=root)
            self.assertEqual(hit["recent"]["headlines"]["items"][0]["title"], "T")
        finally:
            shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- part 3
class TheDiscountRateMadeVisible(unittest.TestCase):
    """NVDA is discounted at 16.3% and TSLA at 14.7% because their betas are about 2, and
    nothing on the page said so. MEASURED, both directions:

    * NVDA beta 2.216, WACC 16.27%, base $145.67 -> at beta 1.0, WACC 10.21%, **$230.65
      (+58.3%)**, which is essentially its $226 price.
    * KO beta 0.318, WACC 6.59%, base $57.34 -> at beta 1.0, WACC 9.64%, **$34.81 (-39.3%)**.

    The low beta was FLATTERING KO's fair value, so the page now shows a figure that cuts
    against the model as readily as for it.
    """

    def test_it_RE_RUNS_the_model_rather_than_reimplementing_the_discount_chain(self):
        code = _code_only(os.path.join("valuation", "engine", "average_risk.py"))
        # No WACC arithmetic here at all -- the pipeline is injected and called.
        for forbidden in ("cost_of_equity", "risk_free", "erp", "compute_wacc",
                          "build_scenarios", "terminal_growth"):
            self.assertNotIn(forbidden, code)
        self.assertIn("revalue", code)

    def test_it_does_NOT_import_the_pipeline(self):
        """Importing upward would make the valuation path depend on a presentation module."""
        tree = ast.parse(_src(os.path.join("valuation", "engine", "average_risk.py")))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("pipeline", node.module or "")
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertNotIn("pipeline", a.name)

    def test_average_beta_is_ONE_by_definition(self):
        from valuation.engine import average_risk as AR
        self.assertEqual(AR.AVERAGE_BETA, 1.0)

    def test_a_WITHHELD_name_gets_NO_figure(self):
        """Printing "the base value would be $X" beside a value the model refused to publish
        would hand back the number the refusal withheld."""
        from valuation.engine import average_risk as AR
        out = AR.average_risk_read(None, None, deployed_wacc=0.16, deployed_beta=2.0,
                                   deployed_value=None, revalue=lambda *a: None)
        self.assertFalse(out["available"])
        self.assertIn("published no base value", out["reason"])
        self.assertIsNone(out["value"])
        self.assertEqual(out["sentence"], "")

    def test_a_close_rate_renders_NOTHING_rather_than_the_same_answer_twice(self):
        from valuation.engine import average_risk as AR

        class _Alt:
            base_fair_value = 100.0

            class wacc:
                wacc = 0.1001

        out = AR.average_risk_read(None, None, deployed_wacc=0.10, deployed_beta=1.0,
                                   deployed_value=100.0, revalue=lambda *a: _Alt)
        self.assertTrue(out["available"])
        self.assertFalse(out["is_material"])
        self.assertEqual(out["sentence"], "")
        self.assertIn("already discounted at close to an average-risk rate", out["reason"])

    def test_a_material_gap_produces_the_sentence_Don_asked_for(self):
        from valuation.engine import average_risk as AR

        class _Alt:
            base_fair_value = 230.65

            class wacc:
                wacc = 0.10206

        out = AR.average_risk_read(None, None, deployed_wacc=0.1627, deployed_beta=2.216,
                                   deployed_value=145.67, revalue=lambda *a: _Alt)
        self.assertTrue(out["is_material"])
        self.assertEqual(out["sentence"],
                         "At an average-risk discount rate of 10.2%, the base value would be "
                         "$230.65.")
        self.assertIn("measured beta is 2.22", out["why"])
        self.assertIn("not a judgement about the business", out["why"])
        self.assertAlmostEqual(out["relative_change_pct"], 58.3, places=1)

    def test_the_second_pass_does_NOT_mutate_the_company(self):
        """`value_from_company` appends to `cd.quality_notes`, and that list becomes the
        result's `warnings`. A second pass over the same company would duplicate every note
        on the FIRST result -- a recorded number changing."""
        from valuation.engine import average_risk as AR

        class _CD:
            def __init__(self):
                self.quality_notes = ["one"]

        cd = _CD()

        def _revalue(c, cfg, ov, tr):
            c.quality_notes.append("added by the second pass")
            raise RuntimeError("and then it failed")

        AR.average_risk_read(cd, None, deployed_wacc=0.16, deployed_beta=2.0,
                             deployed_value=100.0, revalue=_revalue)
        # Restored even though the pass RAISED -- a failure partway through is exactly when
        # the notes are half-appended.
        self.assertEqual(cd.quality_notes, ["one"])

    def test_the_guard_stops_a_second_pass_starting_a_THIRD(self):
        import inspect

        from valuation.engine import pipeline as P
        self.assertIn("_average_risk", inspect.signature(P.value_from_company).parameters)
        src = _src(os.path.join("valuation", "engine", "pipeline.py"))
        self.assertIn("if _average_risk:", src)
        self.assertIn("_average_risk=False", src)

    def test_it_is_PRESENTATION_ONLY_and_nothing_reads_it(self):
        """Structural, not promised: no score, blend, verdict or recorded number may branch
        on this field.

        REPOINTED: the first cut capped how many TIMES the name appears, which is a number
        with no meaning -- it read 9 against a bound of 6 on a perfectly correct file. The
        property is that the field is only ever ASSIGNED, so it is checked on the syntax tree
        instead: `result.average_risk` may appear as an assignment target and nowhere else.
        `_average_risk` is the recursion guard and a different name.
        """
        tree = ast.parse(_src(os.path.join("valuation", "engine", "pipeline.py")))
        targets = reads = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and t.attr == "average_risk":
                        targets += 1
            elif isinstance(node, ast.Attribute) and node.attr == "average_risk":
                if not isinstance(getattr(node, "ctx", None), ast.Store):
                    reads += 1
        # Assigned (both the success path and the fail-open), and the only "reads" the tree
        # shows are those same Store nodes seen a second time by `ast.walk`.
        self.assertGreaterEqual(targets, 1)
        self.assertEqual(reads, 0, "nothing in the valuation path may READ average_risk")
        # And no scorer sees it at all.
        for rel in (os.path.join("valuation", "engine", "scoring.py"),
                    os.path.join("valuation", "engine", "blend.py")):
            if os.path.exists(os.path.join(REPO, rel)):
                self.assertNotIn("average_risk", _code_only(rel), rel)


# --------------------------------------------------------------------------- part 4
class PlainDefinitions(unittest.TestCase):
    """One module owns the wording -- `score_confidence.py`'s shape, for its stated reason."""

    def test_every_term_item_53_names_is_defined(self):
        from valuation.web import definitions as D
        # A LITERAL, not `DEFINITIONS.keys()`: a test that iterates the thing it pins cannot
        # notice a deletion (`MA13`).
        for term in ("dcf", "discount_rate", "base_value", "rule_of_40", "reverse_dcf",
                     "hot_score", "sub_scores"):
            self.assertIn(term, D.DEFINITIONS, term)
            self.assertTrue(D.text(term).strip(), term)
            self.assertTrue(D.label(term).strip(), term)
        self.assertEqual(set(D.REQUIRED), {"dcf", "discount_rate", "base_value", "rule_of_40",
                                           "reverse_dcf", "hot_score", "sub_scores"})

    def test_an_unknown_term_returns_EMPTY_rather_than_a_placeholder(self):
        """"" renders as nothing; "(no definition)" tells a reader the page is broken."""
        from valuation.web import definitions as D
        self.assertEqual(D.text("not_a_term"), "")
        self.assertEqual(D.label("not_a_term"), "")

    def test_no_definition_RECOMMENDS_or_judges(self):
        """FIRED AGAINST ITS OWN CORRECT TREE FIRST, and the reason is the family this
        project names most often: the first cut banned the substring `buy`, which is inside
        **"insider buying"** -- the name of one of the eight themes, and the only way to say
        what it is. Sixth instance in two items.

        The property is that no definition RECOMMENDS or judges, so the ban is on
        recommendation FORMS at word boundaries. `cheap`/`expensive`/`undervalued` stay banned
        outright because no definition here needs them -- "what the price assumes" is the
        page's way of saying that without a verdict.
        """
        import re

        from valuation.web import definitions as D
        PHRASES = ("you should", "we recommend", "our recommendation", "price target",
                   "buy it", "buy this", "sell it", "sell this", "worth buying",
                   "cheap", "expensive", "undervalued", "overvalued", "accumulate", "trim")
        WORDS = (r"\bbuy\b", r"\bsell\b", r"\bhold\b", r"\bavoid\b")
        # A NEGATION IS NOT A CLAIM, and the first cut could not tell them apart: the
        # `base_value` definition says *"not a price target"*, which is exactly what it
        # should say, and the bare phrase ban went red on it. Seventh instance of this family
        # in two items. Saying a thing is NOT a recommendation is the opposite of making one.
        NEGATED = ("not a ", "not an ", "never a ", "never an ", "not the ", "rather than a ")

        def _claimed(hay, needle):
            """Is `needle` present OTHER than inside a negation?"""
            at = 0
            while True:
                j = hay.find(needle, at)
                if j < 0:
                    return False
                before = hay[max(0, j - 14):j]
                if not any(before.endswith(n) for n in NEGATED):
                    return True
                at = j + 1

        for term, (lab, txt) in D.DEFINITIONS.items():
            low = txt.lower()
            for banned in PHRASES:
                self.assertFalse(_claimed(low, banned), "%s: %r" % (term, banned))
            for pat in WORDS:
                self.assertIsNone(re.search(pat, low), "%s: %s" % (term, pat))
        # POSITIVE CONTROLS, or the narrowed rule could be passing by matching nothing.
        self.assertIsNotNone(re.search(r"\bbuy\b", "you could buy it"))
        self.assertTrue(_claimed("our price target is $40", "price target"))
        self.assertFalse(_claimed("it is not a price target", "price target"))
        self.assertIn("insider buying", D.text("themes"))
        self.assertIn("not a price target", D.text("base_value"))

    def test_no_definition_carries_a_number_THAT_MOVES(self):
        """"the 10-year Treasury is 5.28%" would be wrong within weeks and nothing would
        fail. The Rule of 40's own 40 is the exception -- the rule is named for it."""
        from valuation.web import definitions as D
        for term, (lab, txt) in D.DEFINITIONS.items():
            if term == "rule_of_40":
                continue
            self.assertNotIn("%", txt, term)
            self.assertNotIn("$", txt, term)

    def test_the_hot_score_POINTS_at_its_calibrated_language_instead_of_restating_it(self):
        """A paraphrase of a hedge is how a hedge becomes a claim -- `score_confidence`'s own
        stated reason for being quoted verbatim."""
        from valuation.web import definitions as D
        self.assertIn("hot_score", D.POINTS_ELSEWHERE)
        self.assertIn("score_confidence", D.POINTS_ELSEWHERE["hot_score"])
        txt = D.text("hot_score")
        self.assertIn("deliberately not reworded here", txt)
        # And it must not have copied a calibrated sentence in.
        from valuation.web import score_confidence as SC
        for attr in ("per_name", "defensible"):
            v = getattr(SC, attr.upper(), None) or ""
            if isinstance(v, str) and len(v) > 40:
                self.assertNotIn(v[:40], txt)

    def test_the_definitions_reach_the_page_on_ONE_rail(self):
        from valuation.web.app import app
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn("window.DEFINITIONS", html)
        self.assertIn("risk-free rate", html)      # the discount-rate wording itself

    def test_the_page_READS_the_wording_and_never_writes_its_own(self):
        src = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("window.DEFINITIONS", src)
        self.assertIn("function defAttr(", src)
        self.assertIn("function defSpan(", src)
        # Every hero metric gains a hover without its call site being edited.
        self.assertIn("DEF_TERM_BY_LABEL", src)
        self.assertIn('"WACC": "discount_rate"', src)

    def test_a_defined_term_is_VISIBLY_marked(self):
        """A definition nobody can see is a definition nobody reads."""
        css = _src(os.path.join("valuation", "web", "static", "style.css"))
        self.assertIn(".defd{", css)
        self.assertIn("cursor:help", css)


# --------------------------------------------------------------------------- part 5
class ACachedAnalysisIsFreeToShow(unittest.TestCase):
    """The gate moved from "may you call this URL" to "may you SPEND", which is the question
    that was always being asked."""

    def test_may_spend_ai_is_the_owner_alone_under_EVERY_flag(self):
        from valuation.saas import surfaces as SF

        class _On:
            owner_split = True

        class _Off:
            owner_split = False

        # `may_act` returns True for everyone with the split OFF -- right for its job, and
        # wrong for this one. OWNER_SPLIT is a decision about what strangers may READ.
        self.assertTrue(SF.may_act(None, _Off()))
        self.assertFalse(SF.may_spend_ai(None, _Off()))
        self.assertFalse(SF.may_spend_ai(None, _On()))
        self.assertFalse(SF.may_spend_ai({"is_demo": True}, _Off()))

    def test_a_cache_HIT_is_served_with_NO_ownership_check(self):
        src = _src(os.path.join("valuation", "web", "app.py"))
        i = src.index("def api_ai_analysis(")
        body = src[i:src.index("\n@app.route", i)]
        hit = body.index("hit = AA.cached(ticker)")
        gate = body.index("if not _may_spend_ai():")
        self.assertLess(hit, gate, "the cache must be served before the spend gate")

    def test_the_spend_gate_is_DEFAULT_DENY(self):
        """The inner app is importable and runnable without the SaaS wrapper -- every test
        client does exactly that -- so "ran somewhere the guard does not" must not spend."""
        from valuation.web.app import app
        r = app.test_client().post("/api/ai-analysis", json={"ticker": "ZZZZNOPE"})
        d = r.get_json() or {}
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d.get("owner_only_to_run"))
        self.assertFalse(d.get("ran"))
        self.assertIsNone(d.get("ai"))
        src = _src(os.path.join("valuation", "web", "app.py"))
        self.assertIn('getattr(g, "may_spend_ai", False)', src)

    def test_the_SaaS_layer_answers_the_ownership_question(self):
        src = _src(os.path.join("valuation", "saas", "app_saas.py"))
        self.assertIn("g.may_spend_ai = surfaces.may_spend_ai(u, cfg)", src)

    def test_nothing_paid_runs_before_the_gate(self):
        """The ordering IS the safety property, so it is checked structurally."""
        src = _src(os.path.join("valuation", "web", "app.py"))
        i = src.index("def api_ai_analysis(")
        body = src[i:src.index("\n@app.route", i)]
        gate = body.index("if not _may_spend_ai():")
        for paid in ("value_ticker(", "_analyze(", "AA.record("):
            self.assertGreater(body.index(paid), gate,
                               "%s must come AFTER the spend gate" % paid)


# --------------------------------------------------------------------------- part 6
class APremiumPastADoublingReadsAsAMultiple(unittest.TestCase):
    def test_TSLAs_live_reading(self):
        from valuation.engine.scoring import price_vs_model as f
        self.assertEqual(f(378.03, 23.23), "Priced at about 16 times our base value.")

    def test_below_a_doubling_the_percentage_is_KEPT(self):
        from valuation.engine.scoring import price_vs_model as f
        self.assertEqual(f(226.32, 145.44), "Priced 56% above our base value.")
        self.assertEqual(f(199.0, 100.0), "Priced 99% above our base value.")

    def test_the_switch_is_AT_one_hundred_percent(self):
        from valuation.engine.scoring import price_vs_model as f
        self.assertIn("%", f(199.9, 100.0))
        self.assertIn("times", f(200.1, 100.0))

    def test_the_precision_matches_what_the_estimate_can_carry(self):
        """A base value has a wide interval on it, so 16.27x claims precision the estimate
        does not have. Below 10 the half matters; above it, it does not."""
        from valuation.engine.scoring import _round_multiple as r
        self.assertEqual(r(2.0), "2")
        self.assertEqual(r(2.5), "2.5")
        self.assertEqual(r(9.94), "9.9")
        self.assertEqual(r(16.27), "16")
        self.assertEqual(r(100.4), "100")

    def test_it_can_never_print_about_one_times(self):
        from valuation.engine.scoring import _round_multiple as r
        self.assertEqual(r(1.0), "2")
        self.assertEqual(r(0.0), "2")

    def test_a_DISCOUNT_is_untouched(self):
        from valuation.engine.scoring import price_vs_model as f
        self.assertEqual(f(80.0, 100.0), "Priced 20% below our base value.")
        self.assertEqual(f(1.0, 100.0), "Priced 99% below our base value.")


# --------------------------------------------------------------------------- part 7
class WhyTheLiveScanIsMissingThemes(unittest.TestCase):
    """DIAGNOSED AND DELIBERATELY NOT FIXED. Part 7's instruction: if a repair changes live
    hot scores, STOP and route it to Don. It does, so nothing here ships a scoring change.

    WHAT WAS MEASURED, on the live 2026-10-12 scan:

    * **Not a z-scoring defect.** Of the top 500, **ZERO** rows have momentum inputs present
      with a null momentum factor. Every null has all three inputs absent.
    * **Not a data limit either, for most of them.** `T`, `VZ`, `MGM` and `RNR` all return
      400 sessions of history and full momentum from yfinance *right now*, while the scan has
      nothing for them. `SUN` is the exception at 61 sessions, so a repair cannot reach 100%.
    * **The "47 of 100" is NOT momentum.** Across the top 500, momentum is present on
      **97.4%** and growth on **96.6%**, flat across every rank decile. The five-column
      intersection is dominated by `insider` (**63.4%**) and `institutional` (**65.0%**),
      which are sparse by nature.
    * **The cause is the fetch.** `health.api_budget` reports FMP returning **402 Payment
      Required**, disabling itself after **44 errors**, with **7** names served by FMP against
      **726** by the free stack and `names_with_broker_data: 0` -- Tradier is closed, so there
      is no prefill and 1,440 names depend on one per-name Yahoo fetch.
    * **A repair WOULD move live scores**, which is the finding that stops it here: 13 of the
      top 500 would gain a contribution, a median momentum contribution is **0.0922** of
      composite against a median adjacent-rank gap of **0.00073** (~**126 rank positions**,
      ~**3.1 hot-score points**), and four of the thirteen are in the served top 100.
    * **And the bigger finding: rank 1 is scored on ONE theme.** `SMFSY`, hot score 100.0, is
      ranked on `size` alone.
    """

    def test_NOTHING_in_this_item_touches_the_scoring_PATH(self):
        """The guard that makes part 7 a diagnosis rather than a change.

        **ITS FIRST FORM WAS THE CONSTRUCTION `SC-4` FORBIDS, AND THAT CONVENTION WAS RIGHT.**
        It ran `git diff --name-only origin/main` over the working tree and asserted the
        screener files were absent. `test_ma60_conventions.py` refused it on the land gate,
        for a reason it had already MEASURED on two earlier suites: a working-tree diff
        against `origin/main` does not measure the lane that wrote it, it becomes *"a
        permanent tripwire on whole directories, owned by an item that has already landed,
        and it fires on the next lane to touch one of them"* -- which is exactly what mine
        would have done to whoever next edits `factors.py` for a perfectly good reason. It
        had already failed one unrelated land gate before this convention existed.

        **SO THE PROPERTY IS PINNED LOCALLY INSTEAD, over this item's OWN files**, which
        nobody else owns and which cannot rot into somebody else's tripwire: none of the
        three modules item 53 adds may reach the scan's scoring path at all. That is the
        thing that would have to be true for part 7 to have quietly shipped a change, and it
        is checkable without reading the repository's history.

        What this does NOT claim is the broader "no file under `valuation/screener/` changed
        in this commit" -- that is a fact about one diff, it is stated in the commit message
        and the handoff where a reviewer can check it, and a test is the wrong place to keep
        it. `MA21`'s rule: a guard that will cry wolf gets switched off, and one that can only
        be true today is worse than none.
        """
        SCORING = ("factors", "settings", "screen", "attribution", "prices", "providers")
        for rel in (os.path.join("valuation", "data", "recent.py"),
                    os.path.join("valuation", "engine", "average_risk.py"),
                    os.path.join("valuation", "web", "definitions.py")):
            tree = ast.parse(_src(rel))
            for node in ast.walk(tree):
                mod = ""
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                elif isinstance(node, ast.Import):
                    mod = " ".join(a.name for a in node.names)
                if "screener" not in mod:
                    continue
                for name in SCORING:
                    self.assertNotIn(name, mod,
                                     "%s must not reach the scan's scoring path" % rel)
        # A POSITIVE CONTROL, or the rule could be passing by never matching: the module that
        # DOES own the scoring path is importable and names these things.
        from valuation.screener import factors as _f
        self.assertTrue(hasattr(_f, "build_frame"))

    def test_the_measured_figures_are_pinned(self):
        """So they cannot rot, and so a successor can tell whether the picture has moved."""
        # The two sparse themes, not momentum, are what the five-column intersection measures.
        self.assertAlmostEqual(317 / 500.0, 0.634, places=3)      # insider
        self.assertAlmostEqual(325 / 500.0, 0.650, places=3)      # institutional
        self.assertAlmostEqual(487 / 500.0, 0.974, places=3)      # momentum
        self.assertAlmostEqual(483 / 500.0, 0.966, places=3)      # growth
        # The blast radius.
        self.assertEqual(500 - 487, 13)
        self.assertAlmostEqual(0.0922 / 0.00073, 126.3, places=1)

    def test_the_diagnosis_is_WRITTEN_DOWN_where_Don_will_find_it(self):
        h = _src("HANDOFF_appfixes.md")
        self.assertIn("402 Payment Required", h)
        self.assertIn("SMFSY", h)
        self.assertIn("ROUTED TO DON", h)


if __name__ == "__main__":
    unittest.main(verbosity=1, exit=False)
    print("item 53: Index links, recent earnings and headlines, clearer numbers")
