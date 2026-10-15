"""ITEM 57 PART A -- the valuation page's breakages.

Every test here fails against the pre-fix tree, and the two that cannot be written that way
(A5's sweep and A1's checker) are proved non-vacuous against git instead.
"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  must precede any `valuation` import

from tests.js_scope import app_js, strip_noncode, undefined_reads     # noqa: E402

#: The commit the brief was measured against, i.e. the tree before this item.
PREFIX_REV = "9a27a6b"


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _at_rev(path):
    """A file's bytes at `PREFIX_REV`, or None when git cannot answer."""
    try:
        r = subprocess.run(["git", "show", "%s:%s" % (PREFIX_REV, path)],
                           cwd=_repo(), capture_output=True)
    except Exception:                                                   # noqa: BLE001
        return None
    # BINARY, never text=True: git's output decoded as cp1252 on Windows manufactures diffs
    # in any file containing an em dash, and these files are full of them.
    return r.stdout if r.returncode == 0 and r.stdout else None


class A1_UndefinedVariable(unittest.TestCase):
    """`d is not defined` on every search, and a check that would have caught it."""

    def test_the_call_uses_the_variable_that_exists(self):
        with open(app_js(), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('loadRecent(ticker, (data.company && data.company.name) || "")', src)
        self.assertNotIn('loadRecent(ticker, (d.company && d.company.name)', src)

    def test_app_js_has_no_undefined_variable_reads(self):
        found = undefined_reads(app_js())
        self.assertEqual(found, [], "undefined reads in app.js: %r" % (found[:10],))

    def test_the_checker_FINDS_the_real_defect_on_the_pre_fix_file(self):
        """THE NON-VACUITY PROOF. A checker that reports nothing on a broken file is not a
        checker, and this one is hand-written, so it has to be shown to bite."""
        raw = _at_rev("valuation/web/static/app.js")
        if raw is None:
            self.skipTest("git could not produce %s:app.js" % PREFIX_REV)
        d = tempfile.mkdtemp()
        p = os.path.join(d, "app.js")
        with open(p, "wb") as fh:
            fh.write(raw)
        found = undefined_reads(p)
        self.assertTrue(found, "the checker found nothing on the file that was broken in prod")
        self.assertTrue(all(f[0] == "runValue" and f[1] == "d" for f in found),
                        "expected only runValue/d, got %r" % (found,))

    def test_the_stripper_keeps_template_expressions_and_drops_template_text(self):
        """Both halves, because the first cut dropped neither and reported 515 findings."""
        got = strip_noncode('const a = `<div class="${cls}">text</div>`;')
        self.assertIn("cls", got)          # the expression is code
        self.assertNotIn("div", got)       # the text is not
        self.assertNotIn("text", got)

    def test_the_stripper_drops_regex_literals_but_not_division(self):
        self.assertNotIn("abc", strip_noncode('s.replace(/abc/g, "")'))
        self.assertIn("max", strip_noncode("const q = total / max;"))

    def test_a_nested_declaration_is_not_swallowed_by_an_outer_one(self):
        """Failure 2 of 3: `const bars = xs.map(x => { const w = 1; ... })` hid `w`."""
        src = "function f(xs) {\n  const bars = xs.map(x => {\n    const w = 1;\n"\
              "    return w;\n  });\n  return bars;\n}\n"
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.js")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(src)
        self.assertEqual(undefined_reads(p), [])

    def test_an_object_literal_in_an_initialiser_does_not_hide_a_later_declarator(self):
        """Failure 3 of 3: `const a = (x || {}), b = (a.y || {});` hid `b`."""
        src = "function f(x) {\n  const a = (x || {}), b = (a.y || {});\n  return b;\n}\n"
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.js")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(src)
        self.assertEqual(undefined_reads(p), [])

    def test_a_genuinely_undefined_read_is_reported(self):
        """The positive control: the checker must still bite on a fresh instance."""
        src = "function f(xs) {\n  const data = xs;\n  return d.name;\n}\n"
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.js")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(src)
        found = undefined_reads(p)
        self.assertTrue(any(f[1] == "d" for f in found), found)


class A3_HistoriesAreNewestFirst(unittest.TestCase):
    """The one reader in the project that assumed oldest-first."""

    def _block(self, years, revs, margins):
        from valuation.web.app import _company_profile_block

        class CD(object):
            pass

        class R(object):
            pass
        cd = CD()
        cd.fiscal_years, cd.revenue_history, cd.ebit_margin_history = years, revs, margins
        cd.business_summary = cd.business_summary_source = ""
        cd.sector = cd.industry = ""
        cd.market_cap = 1000.0
        cd.revenue_growth = lambda n: None
        r = R()
        r.company = cd
        return _company_profile_block(r)

    def test_revenue_is_the_NEWEST_year(self):
        """NVDA printed $26.97B -- the 2023 figure -- against a true $215.94B."""
        b = self._block([2026, 2025, 2024, 2023],
                        [215938.0, 130497.0, 60922.0, 26974.0],
                        [0.6562, 0.6458, 0.5593, 0.1647])
        self.assertEqual(b["revenue"], 215938.0)
        self.assertEqual(b["revenue_year"], 2026)

    def test_the_margin_trend_runs_oldest_to_newest(self):
        """KNSL read 34.4% -> 23.8% when the margin had RISEN from 23.8% to 34.4%."""
        b = self._block([2025, 2024, 2023, 2022],
                        [1873.987, 1587.525, 1224.449, 838.804],
                        [0.3442, 0.3306, 0.322, 0.2383])
        t = b["operating_margin_trend"]
        self.assertAlmostEqual(t["from"], 0.2383)
        self.assertAlmostEqual(t["to"], 0.3442)
        self.assertLess(t["from"], t["to"], "the trend still runs backwards")

    def test_both_endpoints_carry_their_year(self):
        """The years are what make a recurrence visible rather than plausible."""
        b = self._block([2025, 2024, 2023, 2022], [4.0, 3.0, 2.0, 1.0],
                        [0.4, 0.3, 0.2, 0.1])
        t = b["operating_margin_trend"]
        self.assertEqual(t["from_year"], 2022)
        self.assertEqual(t["to_year"], 2025)

    def test_a_single_margin_reports_only_a_to(self):
        b = self._block([2025], [4.0], [0.4])
        t = b["operating_margin_trend"]
        self.assertIsNone(t["from"])
        self.assertAlmostEqual(t["to"], 0.4)
        self.assertEqual(t["n_years"], 1)

    def test_a_trailing_None_does_not_shift_the_years(self):
        """NVDA's history carries a trailing None; the year must still line up."""
        b = self._block([2026, 2025, 2024, 2023, 2022],
                        [215938.0, 130497.0, 60922.0, 26974.0, None],
                        [0.6562, 0.6458, 0.5593, 0.1647, None])
        self.assertEqual(b["revenue_year"], 2026)
        self.assertEqual(b["operating_margin_trend"]["to_year"], 2026)
        self.assertEqual(b["operating_margin_trend"]["from_year"], 2023)

    def test_every_OTHER_reader_still_honours_newest_first(self):
        """The audit that made this a one-site fix, pinned so it stays one."""
        from valuation.data.models import CompanyData
        cd = CompanyData(ticker="X")
        cd.revenue_history = [200.0, 100.0]        # newest first: doubled
        g = cd.revenue_growth(1)
        self.assertAlmostEqual(g, 1.0, places=6,
                               msg="revenue_growth read the history backwards")


class A4_CompactTwoDecimals(unittest.TestCase):

    def test_the_millions_branch_carries_two_decimals(self):
        with open(app_js(), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('(v / 1e6).toFixed(2) + "M"', src)
        self.assertNotIn('(v / 1e6).toFixed(0) + "M"', src)

    def test_all_three_branches_agree_on_the_convention(self):
        """BOUNDED BY THE FUNCTION, NOT BY A CHARACTER COUNT. The first cut of this test read
        420 characters from `const mcap =` and went red the moment the fix added a comment
        inside that window -- the exact defect `tests/source_bounds.py` exists for, written by
        me in the same change that fixed it."""
        with open(app_js(), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("const mcap =")
        fn = src[i:src.index("\n};", i)]
        for unit in ("T", "B", "M"):
            self.assertIn('.toFixed(2) + "%s"' % unit, fn, unit)
        self.assertNotIn('.toFixed(0)', fn)


class A5_DarkMode(unittest.TestCase):
    """A SWEEP, not a list -- the brief's own list named `code`, which was already themed."""

    def _css(self):
        import valuation
        p = os.path.join(os.path.dirname(os.path.abspath(valuation.__file__)),
                         "web", "static", "style.css")
        with open(p, encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _lum(hx):
        h = hx.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0

    def _offenders(self, css):
        import re
        body = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", body)
        dark = set()
        for sel, _d in rules:
            if 'data-theme="dark"' in sel:
                for part in sel.split(","):
                    dark.add(re.sub(r'^:root\[data-theme="dark"\]\s*', "",
                                    part.strip()).strip())
        bad = []
        for sel, decls in rules:
            s = sel.strip()
            if 'data-theme="dark"' in s or s.startswith("@") or ":root" in s:
                continue
            for _p, val in re.findall(r"(background(?:-color)?)\s*:\s*([^;]+)", decls):
                for hx in re.findall(r"#[0-9a-fA-F]{3,6}\b", val):
                    if self._lum(hx) > 0.75:
                        parts = [p.strip() for p in s.split(",")]
                        if not all(p in dark for p in parts):
                            bad.append((s, hx))
        return bad

    def test_no_light_background_lacks_a_dark_override(self):
        bad = self._offenders(self._css())
        self.assertEqual(bad, [], "light backgrounds with no dark override: %r" % (bad,))

    def test_the_sweep_FINDS_the_five_on_the_pre_fix_stylesheet(self):
        """NON-VACUITY. Five were measured broken; the sweep must have seen them."""
        raw = _at_rev("valuation/web/static/style.css")
        if raw is None:
            self.skipTest("git could not produce %s:style.css" % PREFIX_REV)
        bad = self._offenders(raw.decode("utf-8"))
        sels = {s for s, _hx in bad}
        self.assertGreaterEqual(len(bad), 5, bad)
        for needle in (".dcf-warn", ".avg-risk", ".thin-group", ".thin-flag"):
            self.assertTrue(any(needle in s for s in sels), "%s not seen: %r" % (needle, sels))

    def test_panel_is_actually_defined_now(self):
        """`var(--panel,#fafbfc)` shipped a white panel into dark mode because `--panel` was
        declared nowhere -- one use, zero definitions."""
        css = self._css()
        self.assertGreaterEqual(css.count("--panel:"), 2, "needs a light AND a dark value")

    def test_no_inline_light_background_remains_in_app_js(self):
        import re
        with open(app_js(), encoding="utf-8") as fh:
            js = fh.read()
        bad = [m.group(0) for m in re.finditer(r"background(?:-color)?\s*:\s*#[0-9a-fA-F]{3,6}",
                                               js)
               if self._lum(m.group(0).split("#")[1]) > 0.75]
        self.assertEqual(bad, [], bad)


class A6_MonteCarloHistogram(unittest.TestCase):

    def test_one_histogram_convention_shared_by_both_models(self):
        from valuation.engine.montecarlo import HIST_BINS, histogram_of
        edges, counts = histogram_of([float(x) for x in range(1000)])
        self.assertEqual(len(counts), HIST_BINS)
        self.assertEqual(len(edges), HIST_BINS + 1)
        self.assertEqual(sum(counts), 1000)

    def test_the_financials_module_does_not_build_its_own(self):
        """B7: two `np.histogram(..., bins=40)` calls with their own clip would be two
        conventions for one picture, and the chart cannot tell them apart."""
        import valuation.engine.financials as F
        with open(F.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("from .montecarlo import histogram_of", src)
        self.assertNotIn("np.histogram", src)

    def test_a_degenerate_distribution_reports_no_histogram_rather_than_one_fat_bin(self):
        from valuation.engine.montecarlo import histogram_of
        self.assertEqual(histogram_of([5.0] * 100), ([], []))
        self.assertEqual(histogram_of([]), ([], []))

    def test_the_view_reads_percentiles_instead_of_aliasing_them(self):
        """It used to set `p5 = p10` and `p95 = p90`, so the page showed a 5th percentile that
        was really the 10th."""
        from valuation.engine.pipeline import _PBRoeMC
        v = _PBRoeMC({"p5": 1.0, "p10": 2.0, "p25": 3.0, "p50": 4.0, "p75": 5.0,
                      "p90": 6.0, "p95": 7.0, "std": 0.5,
                      "hist_bins": [0.0, 1.0], "hist_counts": [3]})
        self.assertEqual((v.p5, v.p10, v.p25, v.median, v.p75, v.p90, v.p95),
                         (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0))
        self.assertEqual(v.std, 0.5)
        self.assertEqual(v.hist_counts, [3])

    def test_an_older_payload_without_the_new_keys_degrades_rather_than_raising(self):
        from valuation.engine.pipeline import _PBRoeMC
        v = _PBRoeMC({"p10": 2.0, "p50": 4.0, "p90": 6.0})
        self.assertIsNone(v.p5)
        self.assertEqual(v.hist_bins, [])

    def test_the_chart_shows_percentiles_when_the_histogram_is_empty(self):
        with open(app_js(), encoding="utf-8") as fh:
            js = fh.read()
        i = js.index("function mcChart(")
        fn = js[i:js.index("\n}", i)]
        self.assertIn("if (!counts.length || !bins.length)", fn)
        self.assertIn('_canvasCard("mcChart", false)', fn)


class A7_TheIndexSentence(unittest.TestCase):

    def _lines(self, idx):
        from valuation.web import unified as U
        s = {"in_scan": True, "rank": 42, "n_scored": 500, "scan_date": "2026-10-13",
             "index": idx, "book_withheld": False}
        return [ln["text"] for ln in U._action_lines({"stock": s, "options": {}})
                if ln.get("kind") == "stock"]

    def test_the_word_None_never_reaches_the_reader(self):
        txt = " ".join(self._lines({"available": True, "n_positions": None,
                                    "formed_on": None, "next_rebalance": None}))
        self.assertNotIn("None", txt)

    def test_it_describes_a_HELD_BOOK_not_a_daily_top_n(self):
        txt = " ".join(self._lines({"available": True, "n_positions": 85,
                                    "formed_on": "2026-07-30",
                                    "next_rebalance": "2026-10-22"}))
        self.assertIn("fixed book", txt)
        self.assertIn("2026-07-30", txt)
        self.assertIn("2026-10-22", txt)
        self.assertNotIn("eligible", txt)


class A2_FreeIdentityFallbacks(unittest.TestCase):

    def test_it_only_fills_an_EMPTY_field(self):
        """A fallback, not a second opinion: two sources quietly disagreeing about a company's
        industry is worse than one being absent."""
        from valuation.data import company_identity as I
        from valuation.data.models import CompanyData
        cd = CompanyData(ticker="AAPL", name="Apple Inc.")
        cd.industry = "Consumer Electronics"
        cd.business_summary = "Vendor prose."
        did = I.fill_from_free_sources(cd)
        self.assertFalse(did["used"])
        self.assertEqual(cd.industry, "Consumer Electronics")
        self.assertEqual(cd.business_summary, "Vendor prose.")

    def test_the_degraded_state_is_detected_by_the_symptom_not_the_sentence(self):
        """`name == ticker` is what `yahoo.fetch` leaves behind. Keying on the warning text
        would couple this to a sentence somebody may reword -- and item 57 reworded it."""
        import inspect

        from valuation.data import company_identity as I
        src = inspect.getsource(I.fill_from_free_sources)
        self.assertIn("str(cd.name).upper() == ticker", src)

    def test_the_lead_word_gate_rejects_a_different_company(self):
        """Measured: a shared-token gate accepted "Western Digital" for "Applied Digital
        Corp." and "X Corp." for the same name. The lead word is the identity."""
        from valuation.data.company_identity import _name_tokens
        self.assertEqual(_name_tokens("Applied Digital Corp."), {"applied", "digital"})
        # A corporate suffix is not distinctive, which is the whole reason "X Corp." matched.
        self.assertNotIn("corp", _name_tokens("X Corp."))

    def test_a_description_is_refused_rather_than_taken_from_another_company(self):
        from valuation.data.company_identity import wikipedia_description

        class R(object):
            def __init__(self, payload):
                self.status_code, self._p = 200, payload

            def json(self):
                return self._p

        def fake(url):
            if "search/page" in url:
                return R({"pages": [{"key": "X_Corp."}]})
            return R({"type": "standard", "title": "X Corp.",
                      "description": "American technology company",
                      "extract": "X Corp. is an American technology company."})
        got = wikipedia_description("Applied Digital Corp.", get=fake)
        self.assertEqual(got["text"], "")
        self.assertIn("different company", " ".join(got["rejected"]))

    def test_an_accepted_description_carries_its_source_and_link(self):
        """CC BY-SA requires attribution and a link, so neither is optional."""
        from valuation.data.company_identity import wikipedia_description

        class R(object):
            def __init__(self, payload):
                self.status_code, self._p = 200, payload

            def json(self):
                return self._p

        def fake(url):
            if "search/page" in url:
                return R({"pages": [{"key": "Apple_Inc."}]})
            return R({"type": "standard", "title": "Apple Inc.",
                      "description": "American multinational technology company",
                      "extract": "Apple Inc. is an American multinational technology company.",
                      "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/x"}}})
        got = wikipedia_description("Apple Inc.", get=fake)
        self.assertTrue(got["text"])
        self.assertEqual(got["source"], "Wikipedia")
        self.assertTrue(got["url"])
        self.assertIn("CC BY-SA", got["terms"])

    def test_ONE_note_describes_the_outage_not_two(self):
        """The provider's note is REPLACED, not joined by a second. SEC is stubbed, because a
        test that needs the network to prove a string-replacement is a test that skips."""
        from valuation.data import company_identity as I
        from valuation.data.models import CompanyData
        from valuation.data.yahoo import YAHOO_PROFILE_DOWN
        real = I.sec_identity
        I.sec_identity = lambda t, cik=None: {
            "name": "Kinsale Capital Group, Inc.",
            "industry": "Fire, Marine & Casualty Insurance", "cik": 1669162, "reason": ""}
        try:
            cd = CompanyData(ticker="KNSL", name="KNSL")
            cd.quality_notes.append(YAHOO_PROFILE_DOWN)
            did = I.fill_from_free_sources(cd, want_description=False)
        finally:
            I.sec_identity = real
        self.assertTrue(did["used"])
        self.assertEqual(cd.name, "Kinsale Capital Group, Inc.")
        self.assertEqual(cd.industry, "Fire, Marine & Casualty Insurance")
        self.assertNotIn(YAHOO_PROFILE_DOWN, cd.quality_notes)
        self.assertEqual(len(cd.quality_notes), 1, cd.quality_notes)
        self.assertIn("SEC EDGAR", cd.quality_notes[0])

    def test_a_symbol_with_no_filer_changes_nothing(self):
        from valuation.data import company_identity as I
        from valuation.data.models import CompanyData
        real = I.sec_identity
        I.sec_identity = lambda t, cik=None: {
            "name": "", "industry": "", "cik": None,
            "reason": "this symbol is not in EDGAR's ticker file"}
        try:
            cd = CompanyData(ticker="ZZZZQ", name="ZZZZQ")
            did = I.fill_from_free_sources(cd, want_description=False)
        finally:
            I.sec_identity = real
        self.assertFalse(did["used"])
        self.assertEqual(cd.name, "ZZZZQ")

    def test_the_providers_note_is_in_plain_words(self):
        """It read "Yahoo `info` unavailable; used fast_info + statements only." on every name
        -- two library attribute names and no statement of what it cost the reader."""
        from valuation.data.yahoo import YAHOO_PROFILE_DOWN
        self.assertNotIn("fast_info", YAHOO_PROFILE_DOWN)
        self.assertNotIn("`info`", YAHOO_PROFILE_DOWN)
        for word in ("name", "industry", "beta", "unaffected"):
            self.assertIn(word, YAHOO_PROFILE_DOWN.lower(), word)

    def test_live_check_flags_the_outage_only_when_it_hits_every_name(self):
        """One name missing an industry is ordinary; all of them is an outage. A per-name
        check would have to pass on the first, and did."""
        with open(os.path.join(_repo(), "scripts", "live_check.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("_n_degraded >= _n_names", src)
        self.assertIn("company profile source", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
