"""S25 - the point-in-time sector map.

WHAT THESE TESTS PIN, and why each one is here rather than being obvious.

**THE LOAD-BEARING ONE IS THE LOOK-AHEAD REFUSAL.** This module exists to remove a look-ahead,
so the single way it could fail catastrophically is by re-introducing one quietly: returning a
name's FIRST classification for a date that PREDATES it. That reads as coverage, produces a
plausible sector, and nothing downstream could detect it. Pinned with a positive control -
the same lookup one day later must succeed - so the guard cannot pass by refusing everything.

**SECOND: THE CROSSWALK IS THE REGISTER'S, AND ITS TARGET IS THE ENGINE'S.** `GICS_TO_PANEL` is
pinned against a COMMITTED LITERAL (`MA13`'s idiom - a test that iterates the constant it is
meant to pin deletes its own coverage, which is how `S3-I3`'s required-field test failed), and
its VALUES are required to equal the engine's own dict keys, IMPORTED rather than retyped
(`MA5`: four copies of one fact and only one of them saw the floor).

**THIRD: A TAXONOMY REVISION NEEDS BOTH CONDITIONS.** `classify_transition` requires the date
window AND the destination code, and both one-sided cases are pinned as negative controls -
a move into Real Estate outside 2016 is a firm event, and a move into Technology inside the
2016 window is a firm event. Either condition alone over-claims, which would relabel ordinary
reclassifications as an index provider's paperwork or vice versa.

**FOURTH: UNMAPPED IS A NAMED STATE BECAUSE BOTH ENGINE DICTS FAIL OPEN.** That is asserted
here against the real dicts, not assumed: `.get(sector, 0.12)` and `.get(sector, _DEFAULT)`
mean a blank sector is silently given the middle of a 2.70x range. A crosswalk returning
nothing is a VOTE, not an abstention.

The REAL-ARTIFACT tests SKIP LOUDLY where the built map is absent, never pass vacuously
(`O21-D2`'s `C5`: a filter that never ran and a filter that ran and found nothing must not
read the same).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import sector_map as SM  # noqa: E402

_SKIPS = []


def _artifact():
    p = SM.default_path()
    return p if os.path.exists(p) else None


# The register's table, retyped ONCE, here, on purpose. If the module's dict is edited without
# a dated amendment to PREREG_s25_sector_crosswalk.md, this fails.
REGISTERED_CROSSWALK = {
    "10": "Energy",
    "15": "Basic Materials",
    "20": "Industrials",
    "25": "Consumer Cyclical",
    "30": "Consumer Defensive",
    "35": "Healthcare",
    "40": "Financial Services",
    "45": "Technology",
    "50": "Communication Services",
    "55": "Utilities",
    "60": "Real Estate",
}


def _map(spans, ambiguous=None):
    return SM.SectorMap(spans, ambiguous or {}, source="test", built_utc="2026-08-25T00:00:00")


class TestCrosswalkIsTheRegisters(unittest.TestCase):
    def test_matches_the_committed_literal_cell_for_cell(self):
        self.assertEqual(SM.GICS_TO_PANEL, REGISTERED_CROSSWALK)

    def test_every_target_is_a_key_the_engine_actually_uses(self):
        # IMPORTED, never retyped. A crosswalk onto a string the engine does not key on is
        # silently a vote for the fail-open default.
        keys = SM.engine_sector_keys()
        self.assertEqual(set(SM.GICS_TO_PANEL.values()), keys)

    def test_it_is_one_to_one(self):
        self.assertEqual(len(set(SM.GICS_TO_PANEL.values())), len(SM.GICS_TO_PANEL))

    def test_an_unknown_code_is_named_not_blanked(self):
        self.assertEqual(SM.crosswalk("99"), SM.UNMAPPED)
        self.assertEqual(SM.crosswalk(""), SM.UNMAPPED)
        self.assertEqual(SM.crosswalk(None), SM.UNMAPPED)

    def test_a_float_shaped_code_still_maps(self):
        # pandas reads gsector as 45.0 given half a chance; a silent UNMAPPED there would be
        # a vote for 0.12 on every technology row.
        self.assertEqual(SM.crosswalk("45.0"), "Technology")
        self.assertEqual(SM.crosswalk(" 45 "), "Technology")

    def test_both_engine_dicts_really_do_fail_open(self):
        # The premise of naming UNMAPPED at all. Asserted against the real dicts.
        from valuation.engine.assumptions import SECTOR_TARGET_MARGIN
        from valuation.engine.comps import SECTOR_MULTIPLES, _DEFAULT
        self.assertEqual(SECTOR_TARGET_MARGIN.get("", 0.12), 0.12)
        self.assertEqual(SECTOR_MULTIPLES.get("", _DEFAULT), _DEFAULT)
        lo, hi = min(SECTOR_TARGET_MARGIN.values()), max(SECTOR_TARGET_MARGIN.values())
        self.assertGreater(hi / lo, 2.0, "the spread the look-ahead is being read against")


class TestTheLookAheadRefusal(unittest.TestCase):
    """The property the module exists for."""

    def setUp(self):
        self.m = _map({"AAA": [("2010-01-01", None, "45", "Technology")]})

    def test_a_date_before_the_first_span_is_not_covered(self):
        got = self.m.at("AAA", "2009-06-30")
        self.assertEqual(got["state"], SM.NOT_COVERED)
        self.assertIsNone(got["sector"])

    def test_positive_control_the_guard_is_not_refusing_everything(self):
        got = self.m.at("AAA", "2010-01-01")
        self.assertEqual(got["state"], "OK")
        self.assertEqual(got["sector"], "Technology")

    def test_a_gap_between_spans_is_not_carried_forward(self):
        m = _map({"BBB": [("2010-01-01", "2012-12-31", "45", "Technology"),
                          ("2015-01-01", None, "35", "Healthcare")]})
        self.assertEqual(m.at("BBB", "2013-06-01")["state"], SM.NOT_COVERED)
        self.assertEqual(m.at("BBB", "2012-12-31")["sector"], "Technology")
        self.assertEqual(m.at("BBB", "2015-01-02")["sector"], "Healthcare")

    def test_the_right_span_is_chosen_at_every_boundary(self):
        m = _map({"CCC": [("2010-01-01", "2015-12-31", "40", "Financial Services"),
                          ("2016-01-01", None, "60", "Real Estate")]})
        self.assertEqual(m.at("CCC", "2015-12-31")["sector"], "Financial Services")
        self.assertEqual(m.at("CCC", "2016-01-01")["sector"], "Real Estate")

    def test_before_gics_existed_is_its_own_state(self):
        got = self.m.at("AAA", "1998-06-30")
        self.assertEqual(got["state"], SM.BEFORE_GICS)
        self.assertIsNone(got["sector"])

    def test_an_unmapped_code_yields_no_sector_and_says_so(self):
        m = _map({"DDD": [("2010-01-01", None, "99", SM.UNMAPPED)]})
        got = m.at("DDD", "2012-01-01")
        self.assertEqual(got["state"], SM.UNMAPPED)
        self.assertIsNone(got["sector"])

    def test_an_unknown_ticker_is_not_covered(self):
        self.assertEqual(self.m.at("ZZZ", "2012-01-01")["state"], SM.NOT_COVERED)

    def test_a_malformed_date_refuses(self):
        self.assertEqual(self.m.at("AAA", "not-a-date")["state"], SM.NOT_COVERED)


class TestAmbiguousTickersAreRefusedNotPicked(unittest.TestCase):
    def test_refused_with_its_candidates(self):
        m = _map({"XYZ": [("2010-01-01", None, "45", "Technology")]},
                 ambiguous={"XYZ": ["001234", "005678"]})
        got = m.at("XYZ", "2012-01-01")
        self.assertEqual(got["state"], SM.AMBIGUOUS_TICKER)
        self.assertIsNone(got["sector"])
        self.assertEqual(got["candidates"], ["001234", "005678"])

    def test_the_refusal_beats_a_present_span(self):
        # The hazard is a wrong company's history wearing the right ticker. Having spans must
        # not rescue an ambiguous name.
        m = _map({"XYZ": [("2010-01-01", None, "45", "Technology")]},
                 ambiguous={"XYZ": ["1", "2"]})
        self.assertNotEqual(m.at("XYZ", "2012-01-01")["sector"], "Technology")


class TestTaxonomyRevisionNeedsBothConditions(unittest.TestCase):
    def test_real_estate_2016_in_window_and_into_60(self):
        self.assertEqual(SM.classify_transition("2016-09-16", "60"),
                         "TAXONOMY_REVISION:REAL_ESTATE_2016")

    def test_comm_services_2018_in_window_and_into_50(self):
        self.assertEqual(SM.classify_transition("2018-09-28", "50"),
                         "TAXONOMY_REVISION:COMM_SERVICES_2018")

    def test_negative_control_right_code_wrong_date_is_a_firm_event(self):
        self.assertEqual(SM.classify_transition("2021-03-01", "60"), "FIRM_RECLASSIFICATION")

    def test_negative_control_right_date_wrong_code_is_a_firm_event(self):
        self.assertEqual(SM.classify_transition("2016-09-16", "45"), "FIRM_RECLASSIFICATION")

    def test_a_malformed_date_does_not_claim_a_revision(self):
        self.assertEqual(SM.classify_transition(None, "60"), "FIRM_RECLASSIFICATION")

    def test_transitions_carry_the_label_and_both_ends(self):
        m = _map({"EEE": [("2010-01-01", "2016-09-15", "40", "Financial Services"),
                          ("2016-09-16", None, "60", "Real Estate")]})
        t = m.transitions("EEE")
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]["from_sector"], "Financial Services")
        self.assertEqual(t[0]["to_sector"], "Real Estate")
        self.assertEqual(t[0]["revision"], "TAXONOMY_REVISION:REAL_ESTATE_2016")

    def test_a_single_span_produces_no_transition(self):
        self.assertEqual(_map({"FFF": [("2010-01-01", None, "45", "Technology")]})
                         .transitions("FFF"), [])


class TestTaxonomyDisagreement(unittest.TestCase):
    def test_it_counts_disagreement_and_is_not_vacuous(self):
        m = _map({"AAA": [("2010-01-01", None, "45", "Technology")],
                  "BBB": [("2010-01-01", None, "50", "Communication Services")]})
        d = SM.taxonomy_disagreement(m, {"AAA": "Technology", "BBB": "Technology"})
        self.assertEqual(d["compared"], 2)
        self.assertEqual(d["agree"], 1)
        self.assertEqual(d["disagree"], 1)
        self.assertAlmostEqual(d["disagreement_rate"], 0.5)

    def test_uncovered_names_are_excluded_not_counted_as_agreement(self):
        m = _map({"AAA": [("2010-01-01", None, "45", "Technology")]})
        d = SM.taxonomy_disagreement(m, {"AAA": "Technology", "ZZZ": "Energy"})
        self.assertEqual(d["compared"], 1)
        self.assertEqual(d["uncovered"], 1)

    def test_an_empty_comparison_reports_none_rather_than_a_perfect_zero(self):
        d = SM.taxonomy_disagreement(_map({}), {})
        self.assertIsNone(d["disagreement_rate"])


class TestCoverageAndRoundTrip(unittest.TestCase):
    def test_coverage_counts_reclassified_names(self):
        m = _map({"AAA": [("2010-01-01", None, "45", "Technology")],
                  "BBB": [("2010-01-01", "2015-12-31", "40", "Financial Services"),
                          ("2016-01-01", None, "60", "Real Estate")]})
        c = m.coverage()
        self.assertEqual(c["tickers"], 2)
        self.assertEqual(c["reclassified"], 1)
        self.assertEqual(c["rows"], 3)

    def test_spans_are_sorted_even_if_handed_in_backwards(self):
        m = _map({"GGG": [("2016-01-01", None, "60", "Real Estate"),
                          ("2010-01-01", "2015-12-31", "40", "Financial Services")]})
        self.assertEqual(m.at("GGG", "2012-01-01")["sector"], "Financial Services")


class TestTheBuiltArtifact(unittest.TestCase):
    """Real-map checks. SKIP LOUDLY where the artifact is absent - never a vacuous pass."""

    @classmethod
    def setUpClass(cls):
        cls.path = _artifact()
        if not cls.path:
            _SKIPS.append("S25_SECTOR_MAP.json absent - build it with "
                          "`python -m scripts.s25_sector_map --build`")
            raise unittest.SkipTest("S25_SECTOR_MAP.json absent")
        cls.m = SM.load(cls.path)

    def test_it_loads_and_is_not_empty(self):
        self.assertGreater(len(self.m.spans), 1000)

    def test_the_artifacts_crosswalk_is_the_registered_one(self):
        import json
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["crosswalk"], REGISTERED_CROSSWALK)

    def test_no_span_predates_gics(self):
        for t, rows in self.m.spans.items():
            self.assertGreaterEqual(rows[0][0], SM.GICS_EPOCH, t)

    def test_every_span_carries_a_mapped_or_named_sector(self):
        for t, rows in self.m.spans.items():
            for _frm, _thru, gs, panel in rows:
                self.assertEqual(panel, SM.crosswalk(gs), t)

    def test_both_revisions_are_actually_present(self):
        # If neither fires, the flag is untested against the real data and the
        # revision-vs-firm split is decorative.
        kinds = {t["revision"] for t in self.m.transitions()}
        self.assertIn("TAXONOMY_REVISION:REAL_ESTATE_2016", kinds)
        self.assertIn("TAXONOMY_REVISION:COMM_SERVICES_2018", kinds)
        self.assertIn("FIRM_RECLASSIFICATION", kinds)

    def test_a_2009_lookup_is_not_silently_todays_answer(self):
        # The whole point, on real rows: at least one covered name must disagree with itself
        # across the window, or the map carries no point-in-time information at all.
        moved = 0
        for t in list(self.m.spans)[:4000]:
            a = self.m.at(t, "2009-01-15")
            b = self.m.current(t)
            if a["state"] == "OK" and b["state"] == "OK" and a["sector"] != b["sector"]:
                moved += 1
        self.assertGreater(moved, 0, "no name changed sector - the map is a snapshot")


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
