"""Pins for W-6. Register: `PREREG_w6_crsp_delist_xcheck.md`.

    python tests/test_w6_crsp_delist_xcheck.py

Every bar is the register's. A silent change to one shows up here rather than inside a verdict.
The join guards are the load-bearing ones, because W-6's whole method is a dated join and its
one real defect was a key mismatch.
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "scripts", "w6_crsp_delist_xcheck.py")

sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


class Bars(unittest.TestCase):
    def test_bars_match_the_register(self):
        import w6_crsp_delist_xcheck as W
        self.assertEqual(W.V1_BAR, 0.95)
        self.assertEqual(W.V2_BAR, 0.95)
        self.assertEqual(W.V2_DAYS, 3)
        self.assertEqual(W.V3_BAR, 0.90)
        self.assertEqual(W.V3_TOL, 0.01)
        self.assertEqual(W.K1_BAR, 0.80)
        self.assertEqual(W.K2_MIN_DATES, 16)

    def test_the_crsp_cut_is_the_declared_one(self):
        import w6_crsp_delist_xcheck as W
        self.assertEqual(W.CRSP_CUT, "2024-12-31")
        self.assertEqual(W.PANEL_START, "2009-01-15")

    def test_the_fidelity_target_is_the_published_record(self):
        import w6_crsp_delist_xcheck as W
        self.assertEqual(W.REC["top_decile_alpha"], 0.07174142332098163)
        self.assertEqual(W.REC["long_short_tstat"], 2.8360640685320595)
        self.assertEqual(W.REC["long_short_tstat_nw"], 2.6199121240414884)
        self.assertEqual(W.REC["monotonicity"], -0.8909090909090909)


class TheJoinIsDated(unittest.TestCase):
    """Void condition 4: no undated ticker-to-permno map anywhere in the join path."""

    def test_the_scoping_is_imported_and_not_reimplemented(self):
        """`B7`. A second implementation of a dated join is a second definition of the panel's
        own identity mapping."""
        tree = ast.parse(io.open(SRC, encoding="utf-8").read())
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("adv"):
                imported |= {a.name for a in n.names}
        self.assertIn("ticker_permno_intervals", imported)
        self.assertIn("permno_on", imported)
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("ticker_permno_intervals", defined,
                         "the dated scoping is reimplemented here rather than imported")
        self.assertNotIn("permno_on", defined)

    def test_every_permno_lookup_passes_a_date(self):
        """`permno_on(intervals, ticker, date)` takes three arguments; a two-argument call would
        be an undated lookup, which is what void condition 4 forbids."""
        tree = ast.parse(io.open(SRC, encoding="utf-8").read())
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "permno_on"]
        self.assertGreater(len(calls), 0, "no permno_on call found -- has the join changed?")
        for c in calls:
            self.assertEqual(len(c.args), 3,
                             "a permno_on call is missing its date argument, which makes the "
                             "lookup undated")

    def test_the_suffix_fallback_is_a_fallback(self):
        """It may only run where the RAW lookup already failed, or it is not a fallback."""
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("if p is None:", src)
        self.assertIn("_strip_vendor_suffix", src)


class TheSuffixRepair(unittest.TestCase):
    """The one real defect this instrument had, pinned in both directions."""

    def test_it_strips_the_two_vendor_conventions(self):
        import w6_crsp_delist_xcheck as W
        self.assertEqual(W._strip_vendor_suffix("ADCT1"), "ADCT")     # ticker reuse
        self.assertEqual(W._strip_vendor_suffix("AGN1"), "AGN")
        self.assertEqual(W._strip_vendor_suffix("AKRXQ"), "AKRX")     # bankruptcy
        self.assertEqual(W._strip_vendor_suffix("AAMRQ"), "AAMR")

    def test_it_leaves_an_ordinary_ticker_alone(self):
        """POSITIVE CONTROL in the other direction. Over-stripping would match a DIFFERENT
        company, which is `W-28`'s contamination shape."""
        import w6_crsp_delist_xcheck as W
        for t in ("AAPL", "IBM", "T", "F", "BRK.B", "SPY"):
            self.assertIsNone(W._strip_vendor_suffix(t),
                              "%r was stripped and it carries no vendor suffix" % t)

    def test_a_single_letter_is_never_reduced_to_nothing(self):
        import w6_crsp_delist_xcheck as W
        self.assertIsNone(W._strip_vendor_suffix("Q"))
        self.assertIsNone(W._strip_vendor_suffix("A1"))


class VacuityAndCounts(unittest.TestCase):
    """C3: every rate carries what it compared, and a rate over nothing is VACUOUS."""

    def test_every_bar_reports_an_event_count(self):
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn('"n_compared"', src)
        self.assertIn('"vacuous"', src)

    def test_a_zero_event_rate_is_reported_vacuous_never_passing(self):
        """`MB21`'s C1 once scored a perfect 0.000e+00 on an empty frame by comparing nothing."""
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn('"vacuous": True', src)
        self.assertIn("VACUOUS", src)


class ScopeRefusals(unittest.TestCase):
    def test_the_post_cut_dates_are_listed_and_not_scored(self):
        """Void condition 3."""
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("UNVERIFIABLE_rebalance_dates_past_the_cut", src)
        self.assertIn("actions_delist_events_PAST_CUT_not_scored", src)

    def test_c1_aborts_rather_than_warning(self):
        """A gate that cannot stop the run is not a gate."""
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("raise SystemExit", src)
        self.assertIn("ABORT", src)

    def test_agreement_is_not_proof_is_stated_in_the_artifact(self):
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("agreement_is_not_proof", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
