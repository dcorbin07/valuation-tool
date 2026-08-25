"""W-3b: the IBES second source for the earnings-date spine.

Every test here pins a defect that was COMMITTED during this item and caught by measurement, not
a property imagined afterwards. The three identifier traps in particular are the whole reason the
module exists in the shape it does.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import event_spine as ES                            # noqa: E402
from valuation.edge import ibes_events as IE                            # noqa: E402


class TestMaskedCusip(unittest.TestCase):
    """IBES masks CUSIP characters with `X`. An exact match fails SILENTLY -- it returns zero
    rows, which is indistinguishable from 'this vendor does not cover the name', and it hit
    BMO, CNQ and TD: three of the very foreign issuers this module exists to recover."""

    def test_a_masked_character_matches_any_digit(self):
        self.assertTrue(IE.MaskedCusip.matches("0636711X", "06367110"))
        self.assertTrue(IE.MaskedCusip.matches("1363851X", "13638510"))
        self.assertTrue(IE.MaskedCusip.matches("8911605X", "89116050"))

    def test_an_unmasked_difference_is_still_a_difference(self):
        """The rule must NOT degrade into a prefix match. `00108281` is BOS BETTER ONLINE and
        `00108282` is TECHNOPRISES -- 328 seven-character prefixes in this file are shared by
        more than one distinct cusip, so truncating would merge different companies."""
        self.assertFalse(IE.MaskedCusip.matches("00108281", "00108282"))
        self.assertFalse(IE.MaskedCusip.matches("06367110", "06367111"))

    def test_length_mismatch_never_matches(self):
        self.assertFalse(IE.MaskedCusip.matches("0636711", "06367110"))
        self.assertFalse(IE.MaskedCusip.matches("", "06367110"))
        self.assertFalse(IE.MaskedCusip.matches("06367110", ""))

    def test_the_mask_is_directional(self):
        """`X` is IBES's convention. A CRSP cusip containing X is not licensed to match anything;
        only the IBES side may carry the wildcard, or the rule would be symmetric and far
        looser than measured."""
        self.assertTrue(IE.MaskedCusip.matches("0636711X", "06367110"))
        self.assertFalse(IE.MaskedCusip.matches("06367110", "0636711X"))


class TestIntervalScoping(unittest.TestCase):
    """A ticker is a LEASE. Both naive alternatives were committed in turn and both are wrong:
    every-cusip-ever re-imports reuse, current-cusip-only truncates continuing history."""

    def setUp(self):
        import pandas as pd
        # PanAmSat held SPOT until 2004; Spotify has it from 2018. Both are in IBES under the
        # same official ticker, which is what made the naive route look like a perfect repair.
        self.df = pd.DataFrame({
            "cusip": ["69830X10", "69830X10", "L8681T10", "L8681T10"],
            "cname": ["PANAMSAT CORP", "PANAMSAT CORP", "SPOTIFY TECH", "SPOTIFY TECH"],
            "pdicity": ["QTR", "QTR", "QTR", "QTR"],
            "anndats": ["1996-01-29", "2004-07-29", "2018-07-26", "2026-04-28"],
        })

    def test_an_interval_excludes_the_previous_holder(self):
        out = IE.dates_by_intervals(self.df, {"SPOT": [("L8681T10", "2018-04-03", "9999-12-31")]})
        self.assertEqual(out["SPOT"], ["2018-07-26", "2026-04-28"])

    def test_without_the_interval_the_previous_holder_leaks_in(self):
        """The failure this design prevents, demonstrated rather than described: hand it BOTH
        cusips with wide-open windows and PanAmSat's dates arrive under Spotify's ticker."""
        out = IE.dates_by_intervals(self.df, {
            "SPOT": [("69830X10", "1900-01-01", "9999-12-31"),
                     ("L8681T10", "1900-01-01", "9999-12-31")]})
        self.assertIn("1996-01-29", out["SPOT"])

    def test_a_continuing_company_keeps_its_earlier_cusip(self):
        """The opposite error. Taking only the CURRENT cusip left HWM unmatched on 82.9% of its
        code-22 dates, STX 79.8%, GE 79.3% -- names whose cusip changed while the company
        continued. Two intervals, both kept."""
        out = IE.dates_by_intervals(self.df, {
            "X": [("69830X10", "1990-01-01", "2005-01-01"),
                  ("L8681T10", "2018-01-01", "9999-12-31")]})
        self.assertEqual(len(out["X"]), 4)

    def test_dates_outside_every_interval_are_dropped(self):
        out = IE.dates_by_intervals(self.df, {"SPOT": [("L8681T10", "2019-01-01", "2020-01-01")]})
        self.assertNotIn("SPOT", out)


class TestMergePrecedence(unittest.TestCase):
    """The `precedence` argument was ACCEPTED AND SILENTLY IGNORED in the first cut -- validated,
    stored on the result, and then the body took the union regardless. `S3-I1`'s `columns=`
    regression in a second place, and not cosmetic: the union keeps 1,708 code-22 dates the
    precedence rule displaces."""

    def setUp(self):
        self.base = ES.EventSpine({"AAA": ["2020-01-10", "2020-04-10", "2021-01-10"]},
                                  source="code22")
        self.other = {"AAA": ["2020-01-12", "2020-07-15"]}

    def test_precedence_other_replaces_within_a_covered_year(self):
        m = self.base.merge_source(self.other, "ibes", precedence="other")
        self.assertEqual(m.by_ticker["AAA"], ["2020-01-12", "2020-07-15", "2021-01-10"])

    def test_precedence_self_keeps_ours_within_a_covered_year(self):
        m = self.base.merge_source(self.other, "ibes", precedence="self")
        self.assertEqual(m.by_ticker["AAA"], ["2020-01-10", "2020-04-10", "2021-01-10"])

    def test_union_keeps_everything_and_is_the_only_additive_rule(self):
        m = self.base.merge_source(self.other, "ibes", precedence="union")
        for d in self.base.by_ticker["AAA"]:
            self.assertIn(d, m.by_ticker["AAA"])
        self.assertEqual(len(m.by_ticker["AAA"]), 5)

    def test_the_three_rules_are_genuinely_different(self):
        """If two of them agreed on this fixture the fixture would prove nothing."""
        got = {k: tuple(self.base.merge_source(self.other, "ibes", precedence=k)
                        .by_ticker["AAA"]) for k in ("self", "other", "union")}
        self.assertEqual(len(set(got.values())), 3)

    def test_an_unknown_precedence_is_refused(self):
        with self.assertRaises(ValueError):
            self.base.merge_source(self.other, "ibes", precedence="whichever")

    def test_every_date_carries_its_source(self):
        m = self.base.merge_source({"AAA": ["2020-01-10", "2022-05-05"]}, "ibes",
                                   precedence="union")
        self.assertEqual(m.date_sources["AAA|2020-01-10"], "both")
        self.assertEqual(m.date_sources["AAA|2022-05-05"], "ibes")
        self.assertEqual(m.date_sources["AAA|2020-04-10"], "code22")

    def test_a_name_neither_source_covers_stays_fail_closed(self):
        """The register's first void condition: no date is ever imputed from cadence."""
        b = ES.EventSpine({"ZZZ": []}, source="code22")
        m = b.merge_source({}, "ibes", precedence="union")
        self.assertEqual(m.coverage("ZZZ"), ES.FAIL_CLOSED)
        with self.assertRaises(ES.UnknownCoverage):
            m.dates("ZZZ")

    def test_the_merge_does_not_mutate_the_original(self):
        before = dict(self.base.by_ticker)
        self.base.merge_source(self.other, "ibes", precedence="other")
        self.assertEqual(self.base.by_ticker, before)
        self.assertEqual(self.base.date_sources, {})


class TestFencesAndRefusals(unittest.TestCase):
    def test_an_absent_pull_directory_raises_rather_than_reporting_no_coverage(self):
        """`DEEPITM-FIN`'s existence-is-not-population defect, which bit this item for real: the
        worktree's `data/bulk/` is EMPTY, the spine built from it cleanly, and all 186 names read
        FAIL_CLOSED -- a plausible 'coverage is nil' that would have made the repair look like it
        recovered 29 names from nothing."""
        with self.assertRaises(FileNotFoundError):
            list(IE._iter_chunks(os.path.join(os.path.dirname(__file__), "no_such_dir_w3b")))

    def test_an_empty_pull_directory_also_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                list(IE._iter_chunks(d))

    def test_the_raw_ibes_root_is_the_d_drive(self):
        """Licensed rows never land inside the checkout, where a stray `git add -A` reaches."""
        self.assertTrue(IE.DEFAULT_ACT_DIR.upper().startswith("D:"))
        self.assertNotIn("valuation-tool", IE.DEFAULT_ACT_DIR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
