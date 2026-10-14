"""ITEM 56 -- two more free headline sources: SEC 8-K press releases, and GDELT.

Route 1 is KEPT (18 found, 17 shown, items on 5 of 5 names). Route 2 is REJECTED on two
independent grounds. The tests below pin the extraction rules that every one of the five
measured defects came out of, the declared filter departure, and the structural promise that
nothing but a heading is ever kept.

EVERY FIXTURE IS REAL TEXT FROM A REAL FILED EXHIBIT, in the shape EDGAR actually serves it --
including EDGAR's own document header above the document, which is what the first cut tripped on.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  must precede any `valuation` import

from tests.source_bounds import js_function_source                    # noqa: E402
from valuation.data import press_releases as PR                       # noqa: E402
from valuation.data.headline_rules import (ALLOWED_SOURCES,           # noqa: E402
                                           REJECTED_SOURCES, classify,
                                           classify_filed, filter_titles)

# --------------------------------------------------------------------------- #
# Real exhibit text, as EDGAR serves it
# --------------------------------------------------------------------------- #
#: KO's 2026-06-25 EX-99.1. Note the four header lines ABOVE the heading: that is EDGAR's own
#: document header, and the first cut captured the FILENAME from it as the title.
KO_LEADERSHIP = """<html><body>
<p>EX-99.1</p><p>3</p><p>e26287_ex99-1.htm</p><p>Exhibit 99.1</p><p>News Release</p>
<p><b>The Coca-Cola Company Announces Leadership Transition</b></p>
<p><b>for North America Operating Unit</b></p>
<p>ATLANTA, June 25, 2026 &ndash; The Coca-Cola Company today announced that Jennifer Mann
will step down from her role as EVP and President.</p>
</body></html>"""

#: KO's CEO succession release: the two-line heading joined by a SEMICOLON.
KO_CEO = """<html><body><p>Exhibit 99.1</p>
<p>The Coca-Cola Company Announces CEO Succession Plan;</p>
<p>Chief Operating Officer Henrique Braun to Succeed James Quincey as CEO in 2026</p>
<p>ATLANTA, Dec. 10, 2025 &ndash; The Coca-Cola Company today announced that its board has
elected Henrique Braun.</p></body></html>"""

#: NVDA's earnings release. The BULLET HIGHLIGHTS SIT ABOVE THE DATELINE, which is why reading
#: to the dateline ran four of five titles into the body.
NVDA_EARNINGS = """<html><body><p>EX-99.1</p><p>2</p><p>q2fy27pr.htm</p>
<p>NVIDIA Announces Financial Results for Second Quarter Fiscal 2027</p>
<p>&#8226; Revenue of $96.0 billion, up 56% from a year ago</p>
<p>&#8226; Data Center revenue of $88.0 billion</p>
<p>SANTA CLARA, Calif., Aug. 26, 2026 &#8212; NVIDIA today reported revenue.</p>
</body></html>"""

#: APLD's lease release: the company's own NAME is split on to its own line.
APLD_LEASE = """<html><body><p>EX-99.1</p><p>2</p><p>ex99-1.htm</p><p>EX-99.1</p>
<p>Exhibit 99.1</p><p>Applied</p>
<p>Digital Signs 210 MW Lease at Delta Forge 2, Expanding Its AI Factory Franchise Model</p>
<p>New Long-Term Agreement with a Hyperscaler Brings Total Contracted Portfolio Higher</p>
</body></html>"""

#: A legal exhibit that reached a title before the all-caps rule existed.
NVDA_CERT = """<html><body><p>EX-99.1</p><p>3</p><p>ex99-1.htm</p>
<p>OFFICERS&#8217; CERTIFICATE</p>
<p>The undersigned, NVIDIA Corporation, a Delaware corporation, hereby certifies.</p>
</body></html>"""

#: Tesla's quarterly-update DECK, whose first page is a contents list.
TSLA_DECK = """<html><body><p>EX-99.1</p><p>2</p><p>exhibit991.htm</p>
<p>Q2 2026 Update 1 Exhibit 99.1</p><p>Highlights 03</p><p>Financial Summary 04</p>
</body></html>"""


class ExhibitCandidates(unittest.TestCase):
    """The filename cannot identify the press release -- the defect that returned 0 for 3 of 5."""

    def test_the_real_filenames_of_all_five_measured_companies_are_candidates(self):
        """THE DEFECT THAT MADE ROUTE 1 LOOK WORTHLESS. An `EX-99`-shaped pattern finds nothing
        for NVDA, APLD or OCTV, because the exhibit NUMBER is not in the FILENAME."""
        real = {
            "NVDA": ["nvda-20260826.htm", "q2fy27pr.htm", "q2fy27cfocommentary.htm", "R1.htm"],
            "APLD": ["apld-20261007.htm", "apldq127earningsrelease.htm", "R1.htm"],
            "KO": ["ko-20260728.htm", "a2026q2earningsreleaseex-9.htm", "R1.htm"],
            "TSLA": ["tsla-20261002.htm", "exhibit991.htm", "R1.htm"],
            "OCTV": ["octv-20260812.htm", "exhibit991q2fy26.htm", "R1.htm"],
        }
        for tkr, names in real.items():
            got = PR.exhibit_candidates(names)
            self.assertTrue(got, "no candidate for %s" % tkr)
            # The 8-K body, the index pages and the XBRL render are never candidates.
            self.assertNotIn("R1.htm", got, tkr)
            self.assertFalse([g for g in got if g.startswith(tkr.lower() + "-")], tkr)

    def test_edgar_index_pages_and_xbrl_renders_are_never_candidates(self):
        got = PR.exhibit_candidates([
            "0001045810-26-000073-index.html", "0001045810-26-000073-index-headers.html",
            "R1.htm", "R7.htm", "Financial_Report.xlsx", "q2fy27pr.htm"])
        self.assertEqual(got, ["q2fy27pr.htm"])

    def test_a_filename_tell_only_ORDERS_the_candidates_it_does_not_decide(self):
        """The heading read is the filter; the tells exist to spend the request budget well."""
        got = PR.exhibit_candidates(["ex10-1.htm", "someotherdoc.htm", "ex99-1.htm"])
        self.assertEqual(got[0], "ex99-1.htm")
        self.assertIn("ex10-1.htm", got, "a non-99 exhibit must still be a candidate")

    def test_non_html_documents_are_skipped(self):
        self.assertEqual(PR.exhibit_candidates(["ex99-1.pdf", "ex99-1.txt", "a.jpg"]), [])


class HeadingExtraction(unittest.TestCase):
    """Every case here is a defect the five-name measurement found."""

    def test_edgars_own_document_header_is_not_the_title(self):
        """THE SECOND DEFECT: `e26287_ex99-1.htm` was captured as the heading."""
        got = PR.extract_heading(KO_LEADERSHIP)
        self.assertEqual(
            got["title"],
            "The Coca-Cola Company Announces Leadership Transition for North America "
            "Operating Unit")
        self.assertNotIn(".htm", got["title"])

    def test_a_lowercase_continuation_line_joins_the_heading(self):
        self.assertIn("for North America", PR.extract_heading(KO_LEADERSHIP)["title"])

    def test_a_semicolon_continuation_line_joins_the_heading(self):
        got = PR.extract_heading(KO_CEO)["title"]
        self.assertIn("CEO Succession Plan", got)
        self.assertIn("Henrique Braun", got)

    def test_bullet_highlights_above_the_dateline_do_NOT_join_the_heading(self):
        """THE THIRD DEFECT, which hit four of five names: NVIDIA puts its highlights above the
        dateline, so "read to the dateline" ran the title into the body."""
        got = PR.extract_heading(NVDA_EARNINGS)["title"]
        self.assertEqual(
            got, "NVIDIA Announces Financial Results for Second Quarter Fiscal 2027")
        self.assertNotIn("Revenue of", got)
        self.assertNotIn("96.0", got)

    def test_html_entities_are_decoded_including_numeric_ones(self):
        """Titles shipped with a literal `&#8226;` in them until this was fixed."""
        for html in (NVDA_EARNINGS, KO_LEADERSHIP, KO_CEO):
            got = PR.extract_heading(html)["title"]
            self.assertNotIn("&#", got)
            self.assertNotIn("&ndash;", got)
            self.assertNotIn("&nbsp;", got)

    def test_a_heading_split_mid_phrase_is_read_whole(self):
        """THE WORST DEFECT: rejecting the one-word fragment `Applied` made the module fall
        through to a DIFFERENT exhibit, so it silently showed the wrong release."""
        got = PR.extract_heading(APLD_LEASE)["title"]
        self.assertTrue(got.startswith("Applied Digital Signs 210 MW Lease"), got)

    def test_an_all_caps_heading_is_a_legal_exhibit_and_is_refused(self):
        got = PR.extract_heading(NVDA_CERT)
        self.assertEqual(got["title"], "")
        self.assertIn("capitals", got["reason"])

    def test_a_single_capitalised_company_name_is_NOT_an_all_caps_heading(self):
        """The rule reads the first TWO words, because NVIDIA and KO are legitimately caps."""
        self.assertFalse(PR._opens_in_caps(
            "NVIDIA Announces Financial Results for Second Quarter Fiscal 2027"))
        self.assertTrue(PR._opens_in_caps("INCREMENTAL ASSUMPTION AGREEMENT NO. 1"))

    def test_a_slide_decks_contents_list_is_refused(self):
        got = PR.extract_heading(TSLA_DECK)
        self.assertEqual(got["title"], "")
        self.assertTrue(got["reason"])

    def test_a_filing_with_no_readable_heading_is_dropped_and_never_guessed(self):
        got = PR.extract_heading("<html><body><p>Exhibit 99.1</p></body></html>")
        self.assertEqual(got["title"], "")
        self.assertIn("not shown", got["reason"])

    def test_an_empty_document_reports_a_reason_rather_than_raising(self):
        self.assertEqual(PR.extract_heading("")["title"], "")
        self.assertEqual(PR.extract_heading(None)["title"], "")

    def test_a_title_is_capped_in_length(self):
        long_line = "Company Announces " + ("Something Very Important " * 40)
        got = PR.extract_heading("<html><body><p>x.htm</p><p>%s</p></body></html>" % long_line)
        self.assertLessEqual(len(got["title"]), PR._MAX_TITLE_CHARS + 4)


class TheFilterDeparture(unittest.TestCase):
    """One filter, two declared modes -- and the departure is measured, not preferred."""

    def test_the_news_filter_drops_real_company_announcements(self):
        """THE MEASUREMENT THAT LICENSES THE DEPARTURE. Both of these are real corporate events
        and the conclusion list does not contain the verbs a company uses about itself."""
        for title in ("NVIDIA Guarantees SB Energy's PORTS-Pike Technology Campus in Ohio",
                      "Octave Intelligence Plc Listed on Nasdaq Stockholm"):
            self.assertFalse(classify(title)["show"], title)
            self.assertTrue(classify_filed(title)["show"], title)

    def test_the_promotional_test_still_applies_to_a_filed_document(self):
        """The departure is ONE HALF of ONE test. Promotional still falls."""
        for title in ("3 Reasons Nvidia Could Soar After Earnings",
                      "Why Tesla Stock Is A Buy Right Now"):
            self.assertFalse(classify_filed(title)["show"], title)
            self.assertEqual(classify_filed(title)["kind"], "promotional")

    def test_a_letter_heading_falls_under_both_classifiers(self):
        for c in (classify, classify_filed):
            self.assertFalse(c("Dear Hexagon Shareholders")["show"])

    def test_filed_mode_must_be_asked_for_explicitly(self):
        """A caller gets the NEWS filter unless it says otherwise, so the looser mode cannot be
        reached by accident."""
        items = [{"title": "Octave Intelligence Plc Listed on Nasdaq Stockholm"}]
        self.assertEqual(filter_titles(items)["n_shown"], 0)
        self.assertEqual(filter_titles(items, filed_by_the_company=True)["n_shown"], 1)

    def test_an_empty_title_is_refused_in_filed_mode_too(self):
        self.assertFalse(classify_filed("")["show"])
        self.assertFalse(classify_filed(None)["show"])


class TheWalk(unittest.TestCase):
    """The whole route, with EDGAR injected -- no network."""

    def _edgar(self, docs):
        class R(object):
            def __init__(self, status, payload=None, text=""):
                self.status_code, self._p, self.text = status, payload, text

            def json(self):
                return self._p

        def get(url):
            for key, val in docs.items():
                if url.endswith(key):
                    return val if isinstance(val, R) else R(200, None, val)
            if "submissions" in url:
                return R(200, docs["__sub__"])
            if url.endswith("index.json"):
                return R(200, docs["__idx__"])
            return R(404, None, "")
        self._R = R
        return get

    def _docs(self, items="2.02,9.01", exhibit=NVDA_EARNINGS, form="8-K"):
        return {
            "__sub__": {"filings": {"recent": {
                "form": [form], "filingDate": ["2026-08-26"],
                "accessionNumber": ["0001045810-26-000073"], "items": [items]}}},
            "__idx__": {"directory": {"item": [
                {"name": "nvda-20260826.htm"}, {"name": "q2fy27pr.htm"}, {"name": "R1.htm"}]}},
            "q2fy27pr.htm": exhibit,
        }

    def test_a_release_is_found_dated_linked_and_labelled(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs()))
        self.assertTrue(d["available"])
        self.assertEqual(len(d["items"]), 1)
        it = d["items"][0]
        self.assertEqual(
            it["title"], "NVIDIA Announces Financial Results for Second Quarter Fiscal 2027")
        self.assertEqual(it["date"], "2026-08-26")
        self.assertEqual(it["sec_item"], "2.02,9.01")
        self.assertEqual(it["sec_item_label"], "reported results")
        self.assertTrue(it["url"].startswith("https://www.sec.gov/Archives/edgar/data/1045810/"))

    def test_the_link_is_the_FILING_not_the_raw_exhibit(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs()))
        self.assertFalse(d["items"][0]["url"].endswith(".htm"))

    def test_nothing_but_the_heading_is_kept(self):
        """THE STRUCTURAL PROMISE. The body is fetched because that is where the heading is, so
        the guarantee has to be about what is RETURNED."""
        d = PR.press_releases(1045810, get=self._edgar(self._docs()))
        allowed = {"title", "url", "date", "publisher", "form", "sec_item", "sec_item_label"}
        for it in d["items"]:
            self.assertEqual(set(it) - {"kind"}, allowed)
            for v in it.values():
                self.assertNotIn("Data Center revenue", str(v))
                self.assertNotIn("today reported", str(v))

    def test_a_filing_with_no_readable_heading_yields_nothing_and_says_why(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs(exhibit=NVDA_CERT)))
        self.assertFalse(d["available"])
        self.assertEqual(d["items"], [])
        self.assertTrue(d["reason"])

    def test_a_non_8k_form_is_not_scanned(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs(form="10-Q")))
        self.assertEqual(d["filings_scanned"], 0)
        self.assertIn("no 8-K", d["reason"])

    def test_a_missing_cik_refuses_rather_than_guessing(self):
        for bad in (None, "", "   ", "abc"):
            d = PR.press_releases(bad)
            self.assertFalse(d["available"])
            self.assertIn("CIK", d["reason"])
            self.assertEqual(d["requests_spent"], 0)

    def test_an_edgar_failure_is_reported_not_raised(self):
        class Bad(object):
            status_code = 503

            def json(self):
                return {}
        d = PR.press_releases(1045810, get=lambda u: Bad())
        self.assertFalse(d["available"])
        self.assertIn("503", d["reason"])

    def test_the_request_budget_is_bounded(self):
        """A filing whose documents never yield a heading must not be read without limit."""
        docs = self._docs(exhibit=NVDA_CERT)
        docs["__idx__"] = {"directory": {"item": [
            {"name": "ex99-%d.htm" % i} for i in range(1, 9)]}}
        for i in range(1, 9):
            docs["ex99-%d.htm" % i] = NVDA_CERT
        d = PR.press_releases(1045810, get=self._edgar(docs))
        self.assertLessEqual(d["requests_spent"], 2 + PR.MAX_TRIES_PER_FILING)

    def test_the_yield_counts_are_reported_in_the_item_55_shape(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs()))
        for k in ("n_found", "on_company", "n_shown", "n_excluded", "filings_scanned",
                  "exhibits_found", "headings_read", "requests_spent"):
            self.assertIsInstance(d[k], int, k)
        # On-company is equal to found BY CONSTRUCTION, which is this source's whole advantage.
        self.assertEqual(d["on_company"], d["n_found"])

    def test_the_declared_filter_mode_travels_with_the_result(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs()))
        self.assertEqual(d["filter_mode"], "filed_by_the_company")
        self.assertIn("attribution test does not", d["filter_note"])

    def test_an_unknown_8k_item_is_reported_by_its_number_not_dropped(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs(items="6.03")))
        self.assertIn("6.03", d["items"][0]["sec_item_label"])

    def test_the_terms_travel_with_the_result(self):
        d = PR.press_releases(1045810, get=self._edgar(self._docs()))
        self.assertIn("free to access and reuse", d["terms"])
        self.assertIn("User-Agent", d["terms"])


class TheSourceRegistry(unittest.TestCase):
    """Both verdicts are recorded where the next session will look for them."""

    def test_route_1_is_on_the_allowlist_with_its_measured_yield(self):
        e = ALLOWED_SOURCES["SEC EDGAR (8-K exhibits)"]
        self.assertIn("own CIK", e["per_company"])
        self.assertIn("free to access and reuse", e["terms"])
        self.assertTrue(e["publisher_named"])

    def test_route_2_is_on_the_rejected_list_for_reasons_that_are_NOT_its_terms(self):
        """GDELT's terms are the most permissive of any source looked at, so the record has to
        say that the rejection is about reachability and yield -- or a future session will
        re-litigate the terms and re-reject it for the wrong reason."""
        why = REJECTED_SOURCES["GDELT DOC 2.0 API"]
        self.assertIn("PERMISSIVE", why)
        self.assertIn("429", why)
        self.assertIn("4 of 5", why)
        self.assertIn("ZERO named the company", why)

    def test_no_gdelt_code_ships(self):
        """A rejected source must not be half-built: there is nothing to switch on later."""
        import valuation
        root = os.path.dirname(os.path.abspath(valuation.__file__))
        hits = []
        for dirpath, _dirs, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8") as fh:
                    body = fh.read()
                if "api.gdeltproject.org" in body or "gdelt" in body.lower().replace(
                        "gdeltproject.org/", "@"):
                    # The rejection record names it; a REQUEST to it is the thing banned.
                    if "requests.get" in body and "gdelt" in body.lower():
                        hits.append(os.path.relpath(p, root))
        self.assertEqual(hits, [])


class TheCacheSchema(unittest.TestCase):
    """Adding a field to a cached payload must invalidate the cache, or a day's visitors see
    the old shape. Found live: NVDA served a pre-deploy block while KO served the new one."""

    def test_the_schema_was_bumped_when_the_block_gained_a_field(self):
        from valuation.web.ai_auto import RECENT_SCHEMA
        self.assertNotEqual(RECENT_SCHEMA, "ai_recent/1",
                            "the block gained `press_releases`, so the cache version must move")

    def test_a_block_stored_under_the_old_schema_is_refused(self):
        import tempfile

        from valuation.web import ai_auto as AA
        with tempfile.TemporaryDirectory() as root:
            AA.store_recent("NVDA", {"headlines": {}}, root=root)
            self.assertIsNotNone(AA.cached_recent("NVDA", root=root))
            # Rewrite it as the OLD shape, exactly as the live service had it.
            import json
            with open(AA.recent_path("NVDA", root=root), "w", encoding="utf-8") as fh:
                json.dump({"schema": "ai_recent/1", "headlines": {}}, fh)
            self.assertIsNone(AA.cached_recent("NVDA", root=root),
                              "a pre-deploy block must not be served")


class TheEndpointIsBounded(unittest.TestCase):
    """An endpoint that walks EDGAR per call needs a bucket; three free feeds did not."""

    def test_api_recent_is_rate_limited(self):
        from valuation.saas.ratelimit import LIMITS, buckets_for
        self.assertIn("/api/recent", LIMITS)
        n, window = LIMITS["/api/recent"]
        self.assertGreaterEqual(n, 30, "too tight to browse normally")
        self.assertLessEqual(n, 120, "too loose to bound enumeration")
        self.assertEqual(window, 3600)
        self.assertEqual(buckets_for("/api/recent", None), (("/api/recent", 1),))

    def test_it_does_NOT_share_the_ai_budget(self):
        """A visitor reading headlines must not be able to exhaust the owner's analysis cap."""
        from valuation.saas.ratelimit import buckets_for
        names = [b for b, _c in buckets_for("/api/recent", None)]
        self.assertNotIn("ai:value", names)

    def test_it_does_NOT_share_the_vendor_valuation_budget(self):
        from valuation.saas.ratelimit import VENDOR_BUCKET, buckets_for
        names = [b for b, _c in buckets_for("/api/recent", None)]
        self.assertNotIn(VENDOR_BUCKET, names)


class TheRecentBlockAndThePrompt(unittest.TestCase):

    def test_the_recent_block_carries_the_press_releases(self):
        from valuation.data import recent as RC
        import valuation.data.press_releases as prmod

        real = prmod.press_releases
        prmod.press_releases = lambda cik, **kw: {"available": True, "items": [
            {"title": "T", "url": "u", "date": "2026-01-01"}], "reason": ""}
        try:
            RC.headlines = lambda *a, **k: {"available": False, "items": [], "reason": "x"}
            RC.last_reported_quarter = lambda *a, **k: {"available": False}
            RC.filings = lambda *a, **k: {"available": False, "items": []}
            block = RC.recent_block("NVDA", name="NVIDIA", cik=1045810)
        finally:
            prmod.press_releases = real
        self.assertIn("press_releases", block)
        self.assertEqual(len(block["press_releases"]["items"]), 1)

    def test_the_pre_filter_list_never_reaches_the_payload(self):
        """`_all` exists for the measurement script. The counts belong on the page; the
        excluded titles do not, and a debug key that gets JSON-serialised is not a debug key."""
        from valuation.data import recent as RC
        import valuation.data.press_releases as prmod

        real = prmod.press_releases
        prmod.press_releases = lambda cik, **kw: {
            "available": True, "items": [{"title": "T", "url": "u", "date": "d"}],
            "_all": [{"title": "T"}, {"title": "dropped"}], "reason": ""}
        try:
            RC.headlines = lambda *a, **k: {"available": False, "items": [], "reason": "x"}
            RC.last_reported_quarter = lambda *a, **k: {"available": False}
            RC.filings = lambda *a, **k: {"available": False, "items": []}
            block = RC.recent_block("NVDA", name="NVIDIA", cik=1045810)
        finally:
            prmod.press_releases = real
        self.assertNotIn("_all", block["press_releases"])

    def test_the_prompt_puts_the_companys_own_words_first_and_labels_them(self):
        from valuation.ai.analyst import _recent_facts
        txt = _recent_facts({
            "press_releases": {"items": [{"date": "2026-08-26", "title": "NVIDIA Announces X",
                                          "sec_item_label": "reported results"}]},
            "headlines": {"items": [{"date": "2026-08-25", "title": "Some wire story",
                                     "publisher": "Reuters"}], "scanned": 10, "on_company": 1}})
        self.assertIn("OWN announcements", txt)
        self.assertIn("attributed by construction", txt)
        self.assertLess(txt.index("OWN announcements"), txt.index("Recent headlines"))
        # The model is told it has NOT read the releases.
        self.assertIn("do not describe their contents", txt)

    def test_an_absent_source_and_an_empty_one_do_not_read_the_same(self):
        """`V6`'s rule: a measured nothing and an unmeasured nothing must be distinguishable."""
        from valuation.ai.analyst import _recent_facts
        absent = _recent_facts({"headlines": {"items": []}})
        measured = _recent_facts({"press_releases": {
            "items": [], "reason": "this company has filed no 8-K in its recent filing history"},
            "headlines": {"items": []}})
        self.assertNotIn("filed announcements", absent)
        self.assertIn("filed no 8-K", measured)


class ThePage(unittest.TestCase):
    """BOUNDED BY THE FUNCTION'S OWN BRACES, not by a character count.

    `tests/source_bounds.py` was written because character-window guards over `app.js` "were
    the worst offenders" in this project's own census -- one read 4,000 characters from a
    landmark and "went red the day a comment moved". Three new windows would have repeated it.
    """

    def _fn(self):
        import valuation
        p = os.path.join(os.path.dirname(os.path.abspath(valuation.__file__)),
                         "web", "static", "app.js")
        return js_function_source(p, "loadRecent")

    def test_the_page_renders_the_companys_own_announcements(self):
        fn = self._fn()
        self.assertIn("The company's own announcements", fn)
        self.assertIn("d.press_releases", fn)

    def test_the_page_says_where_they_came_from_and_that_it_keeps_no_text(self):
        fn = self._fn()
        self.assertIn("filed with the SEC", fn)
        self.assertIn("8-K", fn)
        self.assertIn("keeps nothing else", fn)

    def test_every_item_shows_a_date_and_a_link(self):
        fn = self._fn()
        for needle in ("it.url", "it.date", "it.title", 'rel="noopener nofollow"'):
            self.assertIn(needle, fn, needle)

    def test_an_absent_block_shows_its_reason_rather_than_nothing(self):
        self.assertIn("pr.reason", self._fn())

    def test_the_bound_is_not_vacuous(self):
        """A guard that reads an empty segment passes by seeing nothing."""
        fn = self._fn()
        self.assertGreater(len(fn), 2000)
        self.assertIn("const pri = pr.items", fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
