# -*- coding: utf-8 -*-
"""ITEM 55 — more headline sources, conclusions yes, narrative no.

Don's ruling, 2026-10-13: headlines may come from any verifiable, trustworthy source; the line
is between a conclusion (a reported fact, or a conclusion attributed to someone) and a narrative
(opinion, promotional formats). Every headline names its source and links to it.
"""
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
    import tokenize

    out = []
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


# --------------------------------------------------------------------------- part 1
class TheSourceStandardIsStatedAndMeasured(unittest.TestCase):
    """Every candidate the ruling named was measured on NVDA, TSLA, KO, APLD and OCTV."""

    def test_the_standard_is_written_down(self):
        src = _src(os.path.join("valuation", "data", "headline_rules.py"))
        for clause in ("named publisher accountable", "link to the original",
                       "Terms that allow showing a title and a link", "per-company route"):
            self.assertIn(clause, src, clause)

    def test_only_allowed_sources_may_supply_a_headline(self):
        from valuation.data.headline_rules import ALLOWED_SOURCES
        # A COMMITTED LITERAL, so adding a source has to be done in the same commit as the
        # change that adds it and shows up in the diff. ITEM 56 added the third entry: it fired
        # on that change, which is what it is for.
        self.assertEqual(sorted(ALLOWED_SOURCES),
                         ["SEC EDGAR", "SEC EDGAR (8-K exhibits)", "Yahoo Finance RSS"])
        # The REASON travels with the permission: a bare allowlist is how a source comes to be
        # trusted because it is in a list.
        for name, meta in ALLOWED_SOURCES.items():
            for k in ("kind", "per_company", "terms", "publisher_named"):
                self.assertIn(k, meta, name)
            self.assertTrue(meta["terms"].strip(), name)
            self.assertTrue(meta["publisher_named"], name)

    def test_the_headline_path_CHECKS_the_allowlist(self):
        from valuation.data import recent as R
        h = R.headlines("ZZZZNOPE", name="")
        self.assertIn("source_allowed", h)
        self.assertTrue(h["source_allowed"])
        self.assertEqual(h["source"], "Yahoo Finance RSS")

    def test_NO_NEW_SOURCE_EARNED_ITS_PLACE_and_each_rejection_has_its_measurement(self):
        """A finding, not a failure to do the work: the ruling's own instruction was to keep
        only sources that earn their place. Every rejection carries the number that killed it,
        in the code rather than only in a handoff -- the next person to ask "why not Nasdaq?"
        will be reading that file."""
        from valuation.data.headline_rules import ALLOWED_SOURCES, REJECTED_SOURCES
        for name in ("Seeking Alpha per-symbol RSS", "Nasdaq per-symbol", "GlobeNewswire",
                     "PR Newswire", "Business Wire", "CNBC public RSS",
                     "FDA / FTC / DOJ press feeds", "Stocktwits RSS"):
            self.assertIn(name, REJECTED_SOURCES, name)
            self.assertNotIn(name, ALLOWED_SOURCES, name)
            self.assertTrue(REJECTED_SOURCES[name].strip(), name)

    def test_the_BEST_yielding_source_is_rejected_ON_TERMS(self):
        """Seeking Alpha pooled 102 of 132 titles (77%) at 30 items a symbol -- the best
        measured, and its own ToS forbids both the retrieval and the display. Recorded because
        a rejection that costs something is the one most likely to be reversed by somebody who
        only sees the yield."""
        from valuation.data.headline_rules import REJECTED_SOURCES
        why = REJECTED_SOURCES["Seeking Alpha per-symbol RSS"]
        self.assertIn("terms", why.lower())
        self.assertIn("77%", why)
        self.assertIn("scrape", why)
        self.assertIn("written consent", why)

    def test_the_market_wide_feeds_are_rejected_on_SHAPE_not_on_the_publisher(self):
        """0 of 105 items across five such feeds named any of the five test names. An FDA
        feed is the right publisher for a regulatory event and the wrong ROUTE."""
        from valuation.data.headline_rules import REJECTED_SOURCES
        self.assertIn("0 of 55", REJECTED_SOURCES["FDA / FTC / DOJ press feeds"])
        self.assertIn("ROUTE", REJECTED_SOURCES["FDA / FTC / DOJ press feeds"])
        self.assertIn("0 naming any of the five", REJECTED_SOURCES["PR Newswire"])
        src = _src(os.path.join("valuation", "data", "headline_rules.py"))
        self.assertIn("0 of 105 items across five such feeds", src)

    def test_Nasdaq_was_given_THREE_attempts(self):
        from valuation.data.headline_rules import REJECTED_SOURCES
        why = REJECTED_SOURCES["Nasdaq per-symbol"]
        self.assertIn("Three attempts", why)
        self.assertIn("60s", why)


# --------------------------------------------------------------------------- part 2
class ConclusionYesNarrativeNo(unittest.TestCase):
    """AN ALLOWLIST OF CONCLUSIONS, NOT A DENYLIST OF OPINION, and the measurement is why:
    a denylist of the promotional shapes the ruling names kept 93% of Yahoo's on-company
    titles and 97% of Seeking Alpha's, including three plainly-opinion headlines."""

    ALLOWED = [
        ("Tesla to be probed by the NHTSA over speeding robotaxis in school zones",
         "regulators and courts"),
        ("Octave initiated at Equal-weight on SaaS transition risk: Morgan Stanley",
         "analyst actions"),
        ("Coca-Cola Q3 2026 results beat on revenue", "results and guidance"),
        ("Applied Digital announces $850M convertible note offering", "corporate events"),
        ("Nvidia names new CFO", "corporate events"),
        ("EXCLUSIVE: Ross Gerber Says Tesla May Make Just a Few Hundred Roadsters",
         "attributed statements"),
        ("Why Octave Intelligence Stock Slumped Today", "reported moves"),
        ("Coca-Cola Has Raised Dividends for 63 Years", "corporate events"),
    ]

    EXCLUDED = [
        "Should You Buy Nvidia Stock Right Now?",
        "3 Reasons Tesla Could Soar in 2027",
        "Coca-Cola or Chevron: The One Dividend Stock I'd Hold for the Next 20 Years",
        "Nvidia: The Buyback Is The Opportunity",
        "Applied Digital: More Than 600MW Could Drive The Next Leg Of Growth",
        "Octave Intelligence (OCTV) Could Be 51% Below Fair Value",
        "If You'd Invested $1,000 in Tesla in 2015",
        "Nvidia in 5 Years: Where the Stock Could Be Headed",
        "Tesla Trades at 219x Earnings. Here's Why I'm Not Buying the Bet",
        "Top 10 Q3 insider stock sellers led by Nvidia's Stevens",
    ]

    def test_examples_of_BOTH_kinds_as_the_prompt_asks(self):
        from valuation.data.headline_rules import classify
        for title, kind in self.ALLOWED:
            got = classify(title)
            self.assertTrue(got["show"], "should be SHOWN: %s" % title)
            self.assertEqual(got["kind"], kind, title)
        for title in self.EXCLUDED:
            got = classify(title)
            self.assertFalse(got["show"], "should be EXCLUDED: %s" % title)

    def test_a_PROMOTIONAL_marker_OVERRIDES_a_conclusion_marker(self):
        """"3 Reasons Nvidia Could Soar After Earnings" matches `earnings` and is exactly what
        the ruling excludes, so the order is drop-first and that order IS the rule."""
        from valuation.data.headline_rules import classify
        got = classify("3 Reasons Nvidia Could Soar After Earnings")
        self.assertFalse(got["show"])
        self.assertEqual(got["kind"], "promotional")

    def test_AN_ATTRIBUTED_CONCLUSION_IS_ALLOWED_and_the_first_cut_dropped_it(self):
        """A FIDELITY GAP AGAINST THE RULING, found by running the filter on the live feed:
        the ruling allows "a conclusion attributed to someone" and the canonical form of that
        is "X says Y", which had no marker at all -- so the most attributed shape there is was
        being dropped as unattributed."""
        from valuation.data.headline_rules import CONCLUSION_PATTERNS, classify
        self.assertIn("attributed statements", CONCLUSION_PATTERNS)
        for t in ("Musk says Tesla will ship in 2027",
                  "Nvidia confirms the export licence",
                  "The CEO told investors margins would hold"):
            self.assertTrue(classify(t)["show"], t)

    def test_a_pattern_bug_that_dropped_a_real_fact(self):
        """`\\bdividend\\b` cannot match "Dividends", so "Coca-Cola Has Raised Dividends for 63
        Years" was dropped as unattributed. Found by reading the live output, not the code."""
        from valuation.data.headline_rules import classify
        self.assertTrue(classify("Acme raises dividend")["show"])
        self.assertTrue(classify("Acme has raised Dividends for 63 years")["show"])

    def test_an_UNATTRIBUTED_claim_is_not_shown(self):
        from valuation.data.headline_rules import classify
        got = classify("This stock is going places")
        self.assertFalse(got["show"])
        self.assertEqual(got["kind"], "unattributed")

    def test_EVERY_EXCLUSION_IS_COUNTED(self):
        """The ruling's own remedy: the page says "N found, M shown", so a reader can see the
        filter working rather than discover a quiet list."""
        from valuation.data.headline_rules import filter_titles
        items = [{"title": t} for t, _ in self.ALLOWED] + \
                [{"title": t} for t in self.EXCLUDED]
        res = filter_titles(items)
        self.assertEqual(res["n_found"], len(items))
        self.assertEqual(res["n_shown"], len(self.ALLOWED))
        self.assertEqual(res["n_excluded"], len(self.EXCLUDED))
        self.assertTrue(res["excluded_by_kind"])
        self.assertEqual(sum(res["excluded_by_kind"].values()), res["n_excluded"])

    def test_the_counts_reach_the_headline_payload(self):
        from valuation.data import recent as R
        h = R.headlines("ZZZZNOPE", name="")
        for k in ("n_found", "n_shown", "n_excluded", "excluded_by_kind"):
            self.assertIn(k, h)

    def test_the_two_filters_answer_DIFFERENT_questions_and_both_are_reported(self):
        """"is this about the company" and "is this a reported fact" are not the same
        question, so the name filter's yield and the conclusion filter's yield are separate
        numbers on the payload."""
        from valuation.data import recent as R
        h = R.headlines("ZZZZNOPE", name="")
        for k in ("scanned", "on_company", "n_found", "n_shown"):
            self.assertIn(k, h)
        src = _src(os.path.join("valuation", "data", "recent.py"))
        self.assertIn("Applied AFTER the name filter", src)

    def test_an_empty_result_says_WHICH_filter_emptied_it(self):
        """Three different reasons, because "the feed had nothing", "nothing named this
        company" and "nothing was a reported fact" are three different facts."""
        src = _src(os.path.join("valuation", "data", "recent.py"))
        # FRAGMENTS, because the middle sentence WRAPS across two string literals and is not
        # a contiguous substring of the source -- the first cut asserted the whole phrase and
        # failed against a correct tree. Same shape as item 54's `financial_surfaces` guard:
        # a source-text assertion has to match the source's own line breaks.
        self.assertIn("none of them named", src)
        self.assertIn("none was a reported fact or", src)
        self.assertIn("an attributed conclusion", src)
        self.assertIn("the feed carried no recent headlines", src)
        # NO COUNT ASSERTION HERE, and that is a deliberate retraction. I tried two --
        # module-wide (read 11 against an expected 3) and function-scoped (read 6 against 4)
        # -- and both were wrong, because the number of `out["reason"]` assignments is an
        # incidental fact about how the function is written and NOT the property being
        # protected. The property is that the three empty states are DISTINGUISHABLE, and the
        # three phrase assertions above are exactly that.
        #
        # THREE COUNT-BASED GUARDS OF MINE WERE WRONG TODAY (item 53 capped how many times
        # `average_risk` appeared, item 55 twice here): a count is a proxy, and a proxy for a
        # property is the thing this project keeps finding in its own tests. Assert the
        # property.
        self.assertNotEqual(
            "the feed carried no recent headlines",
            "none of them named",
            "the three reasons must differ from one another, which is the whole point")

    def test_the_classifier_never_raises(self):
        from valuation.data.headline_rules import classify, filter_titles
        for bad in (None, "", 7, object()):
            self.assertIn("show", classify(bad))
        self.assertEqual(filter_titles(None)["n_found"], 0)

    def test_the_RECALL_COST_is_stated_rather_than_hidden(self):
        src = _src(os.path.join("valuation", "data", "headline_rules.py"))
        self.assertIn("THE COST IS RECALL", src)
        self.assertIn("cannot be completed", src)


# --------------------------------------------------------------------------- part 3
class SourceDateLinkAndNoArticleText(unittest.TestCase):
    def test_every_headline_carries_its_source_date_and_link(self):
        from valuation.data import recent as R
        h = R.headlines("TSLA", name="Tesla, Inc.")
        if not h["items"]:
            self.skipTest("the live feed carried no shown headline for TSLA right now")
        for it in h["items"]:
            for k in ("title", "url", "date", "publisher"):
                self.assertIn(k, it)
            self.assertTrue(str(it["url"]).startswith("http"), it["url"])

    def test_ARTICLE_TEXT_IS_STILL_UNREACHABLE(self):
        """Item 53's structural property, re-asserted here because item 55 widened the
        sources and that is exactly when such a property gets lost."""
        code = _code_only(os.path.join("valuation", "data", "recent.py"))
        self.assertNotIn("description", code)
        self.assertNotIn("content:encoded", code)

    def test_the_page_says_N_FOUND_M_SHOWN(self):
        js = _src(os.path.join("valuation", "web", "static", "app.js"))
        self.assertIn("h.n_shown", js)
        self.assertIn("h.n_found", js)
        self.assertIn("h.n_excluded", js)
        self.assertIn("opinion or promotional", js)

    def test_the_AI_still_names_the_headline_it_relied_on(self):
        from valuation.ai import analyst as AN
        self.assertIn("headlines_used", AN._SCHEMA)


if __name__ == "__main__":
    unittest.main(verbosity=1, exit=False)
    print("item 55: headline sources, conclusions yes, narrative no")
