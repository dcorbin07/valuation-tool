# -*- coding: utf-8 -*-
"""ITEM 41 — the SIC map that stops ~460 names a bad day having no sector at all.

THE DEFECT, measured rather than inherited. The prompt's premise is "507 names a scan"; that is
the **2026-10-07** scan, the day Yahoo refused the runner outright (item 39), so every name
needed the resolve chain. On **2026-10-08**, with Yahoo answering, the same count is **10**. So
507 is a WORST CASE, not a steady state — and the worst case happens, which is why the fix is
worth having.

`sector_from_sic` mapped ONLY SIC 6000-6799 and returned `None` for everything else, with a
stated reason: *"inventing a mapping for them would trade a known-missing sector for a
plausible-but-wrong one."* **That caution was half right.** Measured on the 460 names that were
unresolved on the bad day (459 carrying a filed SIC, 0 without a CIK, 0 fetch failures):

* the full map resolves **413 of 460 (89.8%)**;
* where the product already has an opinion it **agrees on 134 of 138 (97.1%)** — a **2.9%**
  taxonomy cost, against the **11.37%** `S25` measured for its GICS crosswalk onto these same
  eleven strings;
* SIC's MANUFACTURING, EXTRACTIVE and UTILITY codes map cleanly; its SERVICE codes do not, and
  those are left `None` by a stated rule rather than by taste.

WHAT THESE TESTS PIN:

* every sector the map can emit is a key the ENGINE HAS A MARGIN FOR — `.get(sector, 0.12)`
  fails open in the middle of a 0.100-0.270 range, so a typo would be a silent default;
* the finance range is SPLIT: real estate and REITs are `Real Estate`, not `Financial Services`,
  because `classify.py` turns the sector into a regime and the old label valued a REIT by the
  bank method;
* an unmappable code returns `None` — never a guess;
* the SEC rung caches, paces, and tells a transport failure apart from a real `None`.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.data import sector_resolve as SR                            # noqa: E402
from tests.source_bounds import code_only, function_source                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "valuation", "data", "sector_resolve.py")


def read(path):
    """Closed, or every suite importing this one carries a ResourceWarning."""
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class TheMapSpeaksTheEnginesVocabulary(unittest.TestCase):

    def test_every_emitted_sector_is_a_key_the_engine_has_a_margin_for(self):
        from valuation.engine.assumptions import SECTOR_TARGET_MARGIN
        emitted = set(SR.SIC_EXACT.values()) | {s for _lo, _hi, s in SR.SIC_RANGES}
        self.assertTrue(emitted, "the map emits nothing, so this guard proves nothing")
        self.assertEqual(emitted - set(SECTOR_TARGET_MARGIN), set())

    def test_the_keys_are_IMPORTED_and_not_retyped(self):
        """`S25`/`MA5`'s rule. A second copy of the eleven strings drifts, and the drift is
        invisible because `.get` fails open rather than raising."""
        body = code_only(function_source(MOD, "_engine_sector_keys"))
        self.assertIn("SECTOR_TARGET_MARGIN", body)
        self.assertIn("import", body)

    def test_the_import_time_check_is_not_vacuous(self):
        """It must be able to FAIL. Feed it a bad sector and require the refusal."""
        real = SR.SIC_EXACT
        try:
            SR.SIC_EXACT = dict(real)
            SR.SIC_EXACT["0001"] = "Fintech Unicorns"
            with self.assertRaises(RuntimeError):
                SR._check_map_against_the_engine()
        finally:
            SR.SIC_EXACT = real
        # ...and it passes on the real map, or the test above proves only that it can raise.
        SR._check_map_against_the_engine()

    def test_all_eleven_sectors_are_reachable(self):
        """A map that only ever emits three of eleven would pass every other test here while
        silently funnelling the market into a corner of the margin range."""
        emitted = set(SR.SIC_EXACT.values()) | {s for _lo, _hi, s in SR.SIC_RANGES}
        from valuation.engine.assumptions import SECTOR_TARGET_MARGIN
        missing = set(SECTOR_TARGET_MARGIN) - emitted
        self.assertEqual(missing, set(), "no SIC code maps to %s" % sorted(missing))


class RealEstateIsNotFinancialServices(unittest.TestCase):
    """The mislabel the old range shipped, and the reason it mattered."""

    def test_real_estate_and_REITs_map_to_Real_Estate(self):
        for sic in ("6500", "6512", "6798", 6500, 6798):
            with self.subTest(sic=sic):
                self.assertEqual(SR.sector_from_sic(sic), "Real Estate")

    def test_banks_and_insurers_still_map_to_Financial_Services(self):
        from valuation.engine.classify import FINANCIAL_SECTORS
        for sic in ("6022", "6199", "6311", "6799", 6000):
            with self.subTest(sic=sic):
                self.assertIn(SR.sector_from_sic(sic), FINANCIAL_SECTORS)

    def test_the_regime_actually_changes_which_is_the_whole_point(self):
        """A sector is not cosmetic: `classify` turns it into a REGIME, and the regime decides
        the valuation METHOD and — since item 38 — which group the Dip Detector shows it in."""
        from valuation.engine.classify import REIT_SECTORS, FINANCIAL_SECTORS
        self.assertIn(SR.sector_from_sic("6798"), REIT_SECTORS)
        self.assertNotIn(SR.sector_from_sic("6798"), FINANCIAL_SECTORS)


class AnUnmappableCodeRefuses(unittest.TestCase):

    def test_the_heterogeneous_service_codes_return_None(self):
        """7389 holds MA, PYPL, GPN (payments), UBER, DASH, ETSY, MELI (consumer), AKAM
        (technology) and CBZ, MMS (industrials): four sectors in one code."""
        for sic in ("7389", "7370", "9995", "6770"):
            with self.subTest(sic=sic):
                self.assertIsNone(SR.sector_from_sic(sic))

    def test_the_ambiguous_RANGES_return_None(self):
        """Water transport spans Energy (tankers), Consumer Cyclical (cruise) and Industrials
        (dry bulk). A hull is not a sector."""
        for sic in ("4400", "4412", "4424", "6794", "6795"):
            with self.subTest(sic=sic):
                self.assertIsNone(SR.sector_from_sic(sic))

    def test_no_ambiguous_code_is_also_COVERED_BY_A_RANGE(self):
        """THE INVARIANT MUTATION COULD NOT SEE, and the reason it could not.

        Removing 7389 from `SIC_AMBIGUOUS`, or emptying `SIC_AMBIGUOUS_RANGES`, changes NOTHING
        today: 7389, 4400-4499 and 6794-6795 sit in gaps between `SIC_RANGES` entries, so the
        refusal is achieved twice. That belt-and-braces is deliberate -- but it means the
        refusal SETS are documentation unless something holds the ranges off them.

        This is that something. Widen 7374-7379 to 7374-7389 and this goes red, which is the
        change that would actually reintroduce the defect.
        """
        covered = []
        for code in sorted(int(c) for c in SR.SIC_AMBIGUOUS if str(c).isdigit()):
            for lo, hi, sector in SR.SIC_RANGES:
                if lo <= code <= hi:
                    covered.append((code, sector))
        for lo_a, hi_a in SR.SIC_AMBIGUOUS_RANGES:
            for code in range(lo_a, hi_a + 1):
                for lo, hi, sector in SR.SIC_RANGES:
                    if lo <= code <= hi:
                        covered.append((code, sector))
        self.assertEqual(covered, [],
                         "a range now covers a code the map is supposed to refuse: %r"
                         % covered[:6])
        # ...and the sets are not empty, or this guard passes by having nothing to check.
        self.assertTrue(SR.SIC_AMBIGUOUS)
        self.assertTrue(SR.SIC_AMBIGUOUS_RANGES)

    def test_junk_input_returns_None_and_never_raises(self):
        for sic in (None, "", "   ", "n/a", "abcd", 0, 99999, -1, 3.7):
            with self.subTest(sic=sic):
                self.assertIsNone(SR.sector_from_sic(sic))

    def test_a_STRING_sic_is_accepted_because_SEC_SERVES_ONE(self):
        """`submissions` returns `"sic": "6331"`. An int-only map would decline every real
        answer and the SEC rung would be dead code that looks alive."""
        self.assertEqual(SR.sector_from_sic("6331"), "Financial Services")
        self.assertEqual(SR.sector_from_sic("831"), SR.sector_from_sic("0831"))

    def test_None_is_a_named_state_and_the_module_says_WHY(self):
        """The refusal has to be documented where the map is, or the next reader adds a default.

        `SECTOR_TARGET_MARGIN.get(sector, 0.12)` fails OPEN in the middle of a 0.100-0.270
        range, so returning a guess is a vote for a margin rather than an absence of one.
        """
        src = read(MOD)
        self.assertIn("0.12", src)
        self.assertIn("fails", src.lower())


class TheMapResolvesTheRealPopulation(unittest.TestCase):
    """Spot checks drawn from the measured census, so the cells have names behind them."""

    CASES = (
        ("3674", "Technology", "semiconductors -- ADI, ALGM, AMKR, ARM"),
        ("2834", "Healthcare", "pharmaceutical preparations -- ACAD, ALKS, ALNY"),
        ("7372", "Technology", "prepackaged software -- ADBE, ADSK, CHKP"),
        ("1311", "Energy", "crude petroleum and natural gas -- AR, CHRD, CNQ"),
        ("1040", "Basic Materials", "gold and silver ores -- AEM, AG, AGI, AU"),
        ("2911", "Energy", "petroleum refining -- DK, EQNR, PBF, SU"),
        ("4922", "Energy", "natural gas transmission (midstream) -- AM, DTM, WES"),
        ("4911", "Utilities", "electric services"),
        ("4813", "Communication Services", "telephone -- T, VZ, BCE, AMX"),
        ("3714", "Consumer Cyclical", "motor vehicle parts -- ALV, DAN, LEA"),
        ("2080", "Consumer Defensive", "beverages -- KO, PEP, ABEV"),
        ("5411", "Consumer Defensive", "grocery stores -- ACI, SFM, TBBB"),
        ("5812", "Consumer Cyclical", "eating places -- CAKE, CAVA, EAT"),
        ("8071", "Healthcare", "medical laboratories -- CDNA, VCYT"),
        ("3559", "Technology", "semiconductor equipment -- ASML, LRCX, ACMR"),
        ("3826", "Healthcare", "laboratory analytical instruments -- WAT, BIO, TXG"),
        ("3312", "Basic Materials", "steel works -- CMC, CRS, MT, STLD"),
        ("1531", "Consumer Cyclical", "operative builders -- KBH, MTH, GRBK"),
        ("1600", "Industrials", "heavy construction -- KBR, STRL"),
        ("7011", "Consumer Cyclical", "hotels -- LVS, MGM, PENN, PK"),
        ("8200", "Consumer Cyclical", "educational services -- EDU, LOPE, TAL"),
        ("3841", "Healthcare", "surgical and medical instruments -- BSX, DXCM"),
        ("3823", "Technology", "industrial instruments -- CGNX, KEYS, MKSI"),
        ("4512", "Industrials", "scheduled air transport -- UAL, ALGT, CPA"),
    )

    def test_each_measured_cell_maps_where_the_census_says(self):
        for sic, expect, why in self.CASES:
            with self.subTest(sic=sic, why=why):
                self.assertEqual(SR.sector_from_sic(sic), expect, why)

    def test_the_overrides_beat_the_range_they_sit_inside(self):
        """Each `SIC_EXACT` entry exists because a range would be wrong there; if the range won,
        the override would be dead code that looks alive."""
        # 2834 sits inside 2800-2899 "Basic Materials"...
        self.assertEqual(SR.sector_from_sic("2834"), "Healthcare")
        self.assertEqual(SR.sector_from_sic("2821"), "Basic Materials")
        # ...3559 inside 3500-3569 "Industrials"...
        self.assertEqual(SR.sector_from_sic("3559"), "Technology")
        self.assertEqual(SR.sector_from_sic("3561"), "Industrials")
        # ...and 3826 inside 3800-3825/3830-3859.
        self.assertEqual(SR.sector_from_sic("3826"), "Healthcare")
        self.assertEqual(SR.sector_from_sic("3825"), "Technology")


class TheSECRungIsCachedAndPaced(unittest.TestCase):

    def setUp(self):
        SR._SEC_CACHE.clear()

    def tearDown(self):
        SR._SEC_CACHE.clear()

    def test_the_pacing_interval_is_the_projects_OWN_sec_number(self):
        """0.13s is `scripts/live_theme_sources.py`'s `SEC_MIN_INTERVAL_S`. Two constants for
        one rate limit drift, and the one that drifts upward is the one that gets us blocked."""
        self.assertEqual(SR.SEC_MIN_INTERVAL_S, 0.13)
        src = read(os.path.join(REPO, "scripts", "live_theme_sources.py"))
        self.assertIn("SEC_MIN_INTERVAL_S = 0.13", src,
                      "the number this one is supposed to match moved")

    def test_a_resolved_sector_is_cached_so_the_second_ask_costs_nothing(self):
        """Not a micro-optimisation: the hot pass values its DCF set and item 35's dip
        precompute then re-values every qualifying name, so ~230 names reach this chain twice."""
        calls = {"n": 0}

        class Cfg(object):
            sec_user_agent = "test test@example.com"

        import valuation.data.edgar as E
        real_cik = E.resolve_cik
        import requests
        real_get = requests.get

        class R(object):
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"sic": "3674"}

        try:
            E.resolve_cik = lambda t, c: 320193
            requests.get = lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1), R())[1]
            self.assertEqual(SR._from_sec("AAPL", Cfg()), "Technology")
            self.assertEqual(SR._from_sec("AAPL", Cfg()), "Technology")
        finally:
            E.resolve_cik, requests.get = real_cik, real_get
        self.assertEqual(calls["n"], 1, "the second ask hit the network again")

    def test_an_UNMAPPED_answer_is_cached_too(self):
        """A name SEC cannot classify is not worth re-asking in the same process, and re-asking
        would spend the fair-access budget on a question already answered."""
        calls = {"n": 0}

        class Cfg(object):
            sec_user_agent = "test test@example.com"

        import valuation.data.edgar as E
        real_cik = E.resolve_cik
        import requests
        real_get = requests.get

        class R(object):
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"sic": "7389"}        # the four-sector code

        try:
            E.resolve_cik = lambda t, c: 1
            requests.get = lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1), R())[1]
            self.assertIsNone(SR._from_sec("MA", Cfg()))
            self.assertIsNone(SR._from_sec("MA", Cfg()))
        finally:
            E.resolve_cik, requests.get = real_cik, real_get
        self.assertEqual(calls["n"], 1)

    def test_a_TRANSPORT_failure_is_NOT_cached(self):
        """One timeout must not become a process-long refusal for that name. A real `None` from
        the map and a `None` from a dropped connection are different facts."""
        calls = {"n": 0}

        class Cfg(object):
            sec_user_agent = "test test@example.com"

        import valuation.data.edgar as E
        real_cik = E.resolve_cik
        import requests
        real_get = requests.get

        def boom(*a, **k):
            calls["n"] += 1
            raise RuntimeError("connection reset")

        try:
            E.resolve_cik = lambda t, c: 1
            requests.get = boom
            self.assertIsNone(SR._from_sec("AAPL", Cfg()))
            self.assertIsNone(SR._from_sec("AAPL", Cfg()))
        finally:
            E.resolve_cik, requests.get = real_cik, real_get
        self.assertEqual(calls["n"], 2, "a transport failure was cached as an answer")

    def test_a_ticker_with_no_CIK_is_cached_as_not_an_SEC_filer(self):
        calls = {"n": 0}

        class Cfg(object):
            sec_user_agent = "test test@example.com"

        import valuation.data.edgar as E
        real_cik = E.resolve_cik
        try:
            def no_cik(t, c):
                calls["n"] += 1
                return None
            E.resolve_cik = no_cik
            self.assertIsNone(SR._from_sec("NOTATICKER", Cfg()))
            self.assertIsNone(SR._from_sec("NOTATICKER", Cfg()))
        finally:
            E.resolve_cik = real_cik
        self.assertEqual(calls["n"], 1)

    def test_the_SEC_pacing_is_actually_APPLIED_and_not_merely_defined(self):
        """MISSED BY MUTATION UNTIL THIS EXISTED: replacing `_sec_wait()` with `pass` passed
        the whole suite, because the interval was asserted as a CONSTANT and never as a call.

        A fair-access limit that is defined and not applied is the same as no limit, and the
        consequence lands on the SEC rather than on us -- which is the kind of failure a vendor
        answers with a block.
        """
        body = code_only(function_source(MOD, "_from_sec"))
        self.assertIn("_sec_wait", body, "the rung no longer paces its SEC calls")

    def test_the_pacing_actually_WAITS_between_two_different_names(self):
        """The behaviour, not only the call: two uncached names must be separated by the
        interval. A `_sec_wait` that returned immediately would satisfy the source check."""
        import time

        class Cfg(object):
            sec_user_agent = "test test@example.com"

        import valuation.data.edgar as E
        real_cik = E.resolve_cik
        import requests
        real_get = requests.get

        class R(object):
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"sic": "3674"}

        try:
            E.resolve_cik = lambda t, c: 1
            requests.get = lambda *a, **k: R()
            t0 = time.monotonic()
            SR._from_sec("AAA", Cfg())
            SR._from_sec("BBB", Cfg())
            elapsed = time.monotonic() - t0
        finally:
            E.resolve_cik, requests.get = real_cik, real_get
        self.assertGreaterEqual(elapsed, SR.SEC_MIN_INTERVAL_S * 0.9,
                                "two SEC calls were not paced (%.3fs for two)" % elapsed)

    def test_the_declared_user_agent_is_sent(self):
        """SEC fair access asks for one, and `edgar._headers` already supplies it."""
        body = code_only(function_source(MOD, "_from_sec"))
        self.assertIn("_headers", body)

    def test_the_rung_says_why_todays_classification_is_point_in_time(self):
        """For a valuation dated TODAY, today's filing IS the point-in-time classification —
        which is what makes this rung legitimate where `S25` needed a dated map for a panel."""
        doc = (SR._from_sec.__doc__ or "").lower()
        self.assertIn("point-in-time", doc)


class TheTradierSeamIsWrittenAndNotRun(unittest.TestCase):
    """ITEM 41(b). The measurement exists; the token this lane holds cannot run it."""

    SEAM = os.path.join(REPO, "scripts", "tradier_seam.py")

    def test_it_uses_the_SAME_stated_sample_as_the_fmp_measurement(self):
        """Two vendors measured against DIFFERENT samples give two coverage numbers that cannot
        be compared, which is the entire question."""
        body = read(self.SEAM)
        self.assertIn("from scripts.fmp_seam import sample", body)

    def test_it_touches_market_data_and_NOTHING_that_places_an_order(self):
        """A LIVE token makes "no real trades, ever" a property of the code, not an intention."""
        code = code_only(read(self.SEAM))
        for banned in ("orders", "accounts/", "/positions"):
            self.assertNotIn(banned, code, "the Tradier measurement reaches %r" % banned)
        self.assertIn("markets/history", read(self.SEAM))

    def test_the_token_is_scrubbed_from_everything_printed(self):
        body = function_source(self.SEAM, "scrub")
        self.assertIn("replace(token", body)

    def test_an_AUTH_failure_is_not_reported_as_a_COVERAGE_fact(self):
        """THE DEFECT THIS TEST EXISTS FOR, found by running it: the first cut checked the BODY
        before the STATUS, so a 401 printed as `history: null (symbol not covered)` — item 39's
        own defect (a vendor's refusal read as a data gap) committed inside the tool written to
        measure it."""
        src = read(self.SEAM)
        i_status = src.index("if r.status_code != 200:")
        i_null = src.index('if hist in (None, "null")')
        self.assertLess(i_status, i_null,
                        "the body is inspected before the status code again")


if __name__ == "__main__":
    unittest.main(verbosity=2)
