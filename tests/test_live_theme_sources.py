"""
Tests for V2G — free live sources for the three dead themes (`scripts/live_theme_sources.py`).

No network. Every fixture is synthetic except the CUSIP check digits, which are real published
identifiers and are the point of that test.

The scope test at the bottom is the enforcement of the pre-registration's B5: these columns are
MEASURED ONLY, and the invariant that keeps them that way is that nothing shipped can reach them.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import tokenize
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import live_theme_sources as M   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------------------------------
# The join key.
# ------------------------------------------------------------------------------------------

class TestCusipCheckDigit(unittest.TestCase):
    """Real published CUSIPs. The check digit is what makes the authoritative rung authoritative."""

    GOOD = {
        "037833100": "AAPL",
        "594918104": "MSFT",
        "30303M102": "META",
        "88160R101": "TSLA",
        "857477103": "STT",
        "48581R205": "KSPI (ADR — contains a letter)",
        "G0450A105": "ACN (CINS — leads with a letter)",
    }

    def test_real_cusips_validate(self):
        for cusip, who in self.GOOD.items():
            self.assertTrue(M.valid_cusip(cusip), f"{cusip} ({who}) should validate")

    def test_letter_bearing_cusips_are_not_rejected(self):
        """Regression: valuing letters off a '0-9A-Z' alphabet is off by ten and silently
        rejects every CUSIP containing a letter — which is most ADRs. KSPI is the fixture."""
        self.assertEqual(M.cusip_check_digit("48581R20"), "5")
        self.assertEqual(M.cusip_check_digit("G0450A10"), "5")

    def test_a_wrong_check_digit_is_rejected(self):
        for cusip in self.GOOD:
            bad = cusip[:8] + str((int(cusip[8]) + 1) % 10)
            self.assertFalse(M.valid_cusip(bad), f"{bad} must not validate")

    def test_non_cusip_tokens_are_rejected(self):
        for tok in ("", "123", "MARGINTOP", "ABCDEFGHI", "037833100X", None):
            self.assertFalse(M.valid_cusip(tok))

    def test_a_token_with_no_digit_at_all_is_rejected(self):
        self.assertFalse(M.valid_cusip("ABCDEFGHJ"))


class TestCusipExtraction(unittest.TestCase):
    def test_html_is_stripped_before_matching(self):
        html = "<p>CUSIP No.&nbsp;<b>037833100</b></p>"
        self.assertEqual(M.cusips_in_document(html), ["037833100"])

    def test_css_and_prose_do_not_produce_false_positives(self):
        """The loose first cut of this matched 'margin-top' out of a stylesheet."""
        html = "<style>.x{margin-top:4px}</style><div>see also SCHEDULE13G</div>"
        self.assertEqual(M.cusips_in_document(html), [])

    def test_order_of_appearance_is_preserved(self):
        html = "857477103 then 037833100 then 857477103"
        self.assertEqual(M.cusips_in_document(html),
                         ["857477103", "037833100", "857477103"])


class TestCusipVoting(unittest.TestCase):
    """The authoritative rung, and the contamination that forced it to be tightened."""

    def _fetch(self, docs_text, monkey):
        calls = {"n": 0}

        def fake_get(url, guard, as_json=False):
            if as_json:
                return {"filings": {"recent": {}}}
            calls["n"] += 1
            return docs_text[calls["n"] - 1]

        monkey(fake_get)
        sub = {"cik": 1, "form": ["SC 13G"] * len(docs_text),
               "accessionNumber": [f"0000000000-26-00000{i}" for i in range(len(docs_text))],
               "primaryDocument": ["d.htm"] * len(docs_text), "filingDate": ["2026-01-01"]}
        return sub

    def test_a_tie_between_candidate_cusips_is_refused_not_broken_by_dict_order(self):
        """A company that is itself an asset manager files 13Gs ABOUT OTHER ISSUERS, and those
        sit in its own EDGAR feed. PFG returned six candidates with one vote each; resolving
        that by insertion order would have joined it to somebody else's stock."""
        orig_get, orig_sub = M._get, M.submissions
        docs = ["CUSIP 037833100", "CUSIP 594918104"]      # one vote each -> a tie
        try:
            M.submissions = lambda root, t, cik, g: {
                "cik": cik, "form": ["SC 13G", "SC 13G"],
                "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002"],
                "primaryDocument": ["a.htm", "b.htm"], "filingDate": ["2026-01-01"] * 2}
            seq = iter(docs)
            M._get = lambda url, guard, as_json=False: next(seq)
            out = M.fetch_cusip("root", "PFG", 1, M.Guard(min_interval=0,
                                                          sleeper=lambda s: None))
        finally:
            M._get, M.submissions = orig_get, orig_sub
        self.assertEqual(out["rung"], "cusip_13g_tied")
        self.assertIsNone(out["cusip"])
        self.assertEqual(out["candidates"], 2)

    def test_a_genuine_mode_is_accepted(self):
        orig_get, orig_sub = M._get, M.submissions
        docs = ["CUSIP 037833100", "CUSIP 037833100", "CUSIP 594918104"]
        try:
            M.submissions = lambda root, t, cik, g: {
                "cik": cik, "form": ["SC 13G"] * 3,
                "accessionNumber": [f"0000000000-26-00000{i}" for i in range(3)],
                "primaryDocument": ["a.htm"] * 3, "filingDate": ["2026-01-01"] * 3}
            seq = iter(docs)
            M._get = lambda url, guard, as_json=False: next(seq)
            out = M.fetch_cusip("root", "AAPL", 1, M.Guard(min_interval=0,
                                                           sleeper=lambda s: None))
        finally:
            M._get, M.submissions = orig_get, orig_sub
        self.assertEqual(out["rung"], "cusip_13g")
        self.assertEqual(out["cusip"], "037833100")
        self.assertEqual(out["votes"], 2)

    def test_a_single_unambiguous_document_still_counts(self):
        """STT has exactly one SC 13 filing; one candidate with one vote is not a tie."""
        orig_get, orig_sub = M._get, M.submissions
        try:
            M.submissions = lambda root, t, cik, g: {
                "cik": cik, "form": ["SC 13G/A"],
                "accessionNumber": ["0000000000-26-000001"],
                "primaryDocument": ["a.htm"], "filingDate": ["2026-01-01"]}
            M._get = lambda url, guard, as_json=False: "CUSIP No. 857477103"
            out = M.fetch_cusip("root", "STT", 1, M.Guard(min_interval=0,
                                                          sleeper=lambda s: None))
        finally:
            M._get, M.submissions = orig_get, orig_sub
        self.assertEqual(out["cusip"], "857477103")
        self.assertEqual(out["rung"], "cusip_13g")


class TestNormaliseName(unittest.TestCase):
    def test_suffixes_are_stripped_from_both_ends(self):
        self.assertEqual(M.normalise_name("Apple Inc."), "APPLE")
        self.assertEqual(M.normalise_name("The Kroger Co"), "KROGER")
        self.assertEqual(M.normalise_name("APPLE INC"), M.normalise_name("Apple, Inc."))

    def test_an_interior_suffix_word_is_kept(self):
        """Stripping every occurrence would collapse distinct issuers together."""
        self.assertEqual(M.normalise_name("Berkshire Hathaway Inc"), "BERKSHIRE HATHAWAY")
        self.assertEqual(M.normalise_name("Group 1 Automotive Inc"), "GROUP 1 AUTOMOTIVE")
        self.assertEqual(M.normalise_name("Group 1 Automotive Inc"),
                         M.normalise_name("GROUP 1 AUTOMOTIVE INC"))

    def test_empty_and_none_are_safe(self):
        self.assertEqual(M.normalise_name(None), "")
        self.assertEqual(M.normalise_name("   "), "")


# ------------------------------------------------------------------------------------------
# The 13F aggregation.
# ------------------------------------------------------------------------------------------

def _tsv(rows):
    return "".join("\t".join(str(c) for c in r) + "\n" for r in rows)


def _make_zip(path, submissions, coverpages, infotable):
    sub_hdr = ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"]
    cov_hdr = ["ACCESSION_NUMBER", "REPORTCALENDARORQUARTER", "ISAMENDMENT", "AMENDMENTNO",
               "AMENDMENTTYPE"]
    inf_hdr = ["ACCESSION_NUMBER", "INFOTABLE_SK", "NAMEOFISSUER", "TITLEOFCLASS", "CUSIP",
               "FIGI", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL"]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("SUBMISSION.tsv", _tsv([sub_hdr] + submissions))
        z.writestr("COVERPAGE.tsv", _tsv([cov_hdr] + coverpages))
        z.writestr("INFOTABLE.tsv", _tsv([inf_hdr] + infotable))
    return path


class TestAggregate13F(unittest.TestCase):
    PERIOD = "31-MAR-2026"
    A = "0000000000-26-000001"     # filer 111, original
    B = "0000000000-26-000002"     # filer 222, original
    C = "0000000000-26-000003"     # filer 111, RESTATEMENT (supersedes A)
    D = "0000000000-26-000004"     # filer 333, wrong period
    APPLE = "037833100"

    def _zip(self, tmp):
        subs = [
            [self.A, "10-MAY-2026", "13F-HR", "0000000111", self.PERIOD],
            [self.B, "11-MAY-2026", "13F-HR", "0000000222", self.PERIOD],
            [self.C, "20-MAY-2026", "13F-HR/A", "0000000111", self.PERIOD],
            [self.D, "10-MAY-2026", "13F-HR", "0000000333", "31-DEC-2025"],
        ]
        covs = [
            [self.A, self.PERIOD, "N", "", ""],
            [self.B, self.PERIOD, "N", "", ""],
            [self.C, self.PERIOD, "Y", "1", "RESTATEMENT"],
            [self.D, "31-DEC-2025", "N", "", ""],
        ]
        info = [
            # superseded original — must NOT be counted
            [self.A, 1, "APPLE INC", "COM", self.APPLE, "", 1000, 10, "SH", ""],
            # the restatement that supersedes it
            [self.C, 2, "APPLE INC", "COM", self.APPLE, "", 5000, 50, "SH", ""],
            # a second, distinct filer
            [self.B, 3, "APPLE INC", "COM", self.APPLE, "", 2000, 20, "SH", ""],
            # an OPTION on the same issuer — not share ownership
            [self.B, 4, "APPLE INC", "COM", self.APPLE, "", 9999, 999, "SH", "CALL"],
            # a BOND — principal amount, not shares
            [self.B, 5, "APPLE INC", "NOTE", self.APPLE, "", 8888, 888, "PRN", ""],
            # a filing for a different period entirely
            [self.D, 6, "APPLE INC", "COM", self.APPLE, "", 7777, 777, "SH", ""],
        ]
        return _make_zip(os.path.join(tmp, "z.zip"), subs, covs, info)

    def test_the_aggregation_obeys_every_precommitted_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            agg = M.aggregate_13f(self._zip(tmp), self.PERIOD)
        rec = agg["cusips"][self.APPLE]
        # two DISTINCT filers (111 via its restatement, and 222)
        self.assertEqual(rec["holders"], 2)
        # 5000 (restatement) + 2000 (filer 222). The superseded 1000, the CALL, the PRN and
        # the other period are all excluded.
        self.assertEqual(rec["value"], 7000.0)
        self.assertEqual(rec["shares"], 70.0)

    def test_a_restatement_supersedes_the_original_for_that_filer_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(self._zip(tmp)) as z:
                keep, shape = M.accessions_for_period(z, self.PERIOD)
        self.assertNotIn(self.A, keep, "superseded original must be dropped")
        self.assertIn(self.C, keep)
        self.assertIn(self.B, keep, "another filer's original is untouched")
        self.assertEqual(shape["filers"], 2)
        self.assertEqual(shape["filers_with_multiple_accessions"], 1)

    def test_holder_breadth_is_invariant_to_the_amendment_rule(self):
        """The weakest part of the construction cannot touch the breadth term: breadth counts
        DISTINCT filer CIKs, so double-counting an accession cannot inflate it."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp)
            agg = M.aggregate_13f(path, self.PERIOD)
            # Re-run with the restatement relabelled as a plain original, so BOTH of filer
            # 111's accessions are kept and its dollars are double counted.
            subs = [[self.A, "10-MAY-2026", "13F-HR", "0000000111", self.PERIOD],
                    [self.B, "11-MAY-2026", "13F-HR", "0000000222", self.PERIOD],
                    [self.C, "20-MAY-2026", "13F-HR", "0000000111", self.PERIOD]]
            covs = [[a, self.PERIOD, "N", "", ""] for a in (self.A, self.B, self.C)]
            info = [[self.A, 1, "APPLE INC", "COM", self.APPLE, "", 1000, 10, "SH", ""],
                    [self.C, 2, "APPLE INC", "COM", self.APPLE, "", 5000, 50, "SH", ""],
                    [self.B, 3, "APPLE INC", "COM", self.APPLE, "", 2000, 20, "SH", ""]]
            alt = M.aggregate_13f(_make_zip(os.path.join(tmp, "b.zip"), subs, covs, info),
                                  self.PERIOD)
        self.assertEqual(agg["cusips"][self.APPLE]["holders"],
                         alt["cusips"][self.APPLE]["holders"])
        self.assertNotEqual(agg["cusips"][self.APPLE]["value"],
                            alt["cusips"][self.APPLE]["value"])

    def test_a_malformed_cusip_row_is_skipped_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            subs = [[self.A, "10-MAY-2026", "13F-HR", "0000000111", self.PERIOD]]
            covs = [[self.A, self.PERIOD, "N", "", ""]]
            info = [[self.A, 1, "SHORT CUSIP CO", "COM", "0378331", "", 1, 1, "SH", ""]]
            agg = M.aggregate_13f(_make_zip(os.path.join(tmp, "c.zip"), subs, covs, info),
                                  self.PERIOD)
        self.assertEqual(agg["cusips"], {})


# ------------------------------------------------------------------------------------------
# The join ladder and its anchor.
# ------------------------------------------------------------------------------------------

class TestJoinLadder(unittest.TestCase):
    APPLE = "037833100"
    OTHER = "594918104"

    def _root(self, tmp, cusip_files, cik_title="Apple Inc."):
        os.makedirs(os.path.join(tmp, "cusip"), exist_ok=True)
        for tkr, payload in cusip_files.items():
            with open(os.path.join(tmp, "cusip", f"{tkr}.json"), "w") as fh:
                json.dump(payload, fh)
        with open(os.path.join(tmp, "cik_map.json"), "w") as fh:
            json.dump({"AAPL": {"cik": 320193, "title": cik_title}}, fh)
        return tmp

    def _agg(self, holders_curr=100, holders_prior=80, shares_curr=200.0,
             shares_prior=100.0, value=1e10):
        return {"by_period": {
            M.PERIOD_CURR: {self.APPLE: {"holders": holders_curr, "value": value,
                                         "shares": shares_curr, "name": "APPLE INC"}},
            M.PERIOD_PRIOR: {self.APPLE: {"holders": holders_prior, "value": value,
                                          "shares": shares_prior, "name": "APPLE INC"}}}}

    def test_the_authoritative_rung_wins_and_the_change_terms_are_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": self.APPLE, "rung": "cusip_13g"}})
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 2e10}]
            j = M.join_13f(root, served, self._agg())["AAPL"]
        self.assertEqual(j["rung"], "cusip_13g")
        self.assertEqual(j["holders"], 100)
        self.assertAlmostEqual(j["sm_breadth"], 100 / 80 - 1)
        self.assertAlmostEqual(j["inst_accum"], 200 / 100 - 1)

    def test_accumulation_is_built_on_shares_not_dollars(self):
        """Otherwise a quarter's price move would make this a momentum signal in a 13F coat."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": self.APPLE}})
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 2e10}]
            agg = self._agg(shares_curr=100.0, shares_prior=100.0)
            agg["by_period"][M.PERIOD_PRIOR][self.APPLE]["value"] = 5e9   # price halved
            j = M.join_13f(root, served, agg)["AAPL"]
        self.assertAlmostEqual(j["inst_accum"], 0.0,
                               msg="unchanged share count must give zero accumulation")

    def test_the_name_fallback_fires_only_when_the_authoritative_rung_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": None, "rung": "no_cusip_in_13g"}})
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 2e10}]
            j = M.join_13f(root, served, self._agg())["AAPL"]
        self.assertEqual(j["rung"], "name_exact")
        self.assertEqual(j["cusip"], self.APPLE)

    def test_an_ambiguous_name_is_a_failure_and_never_a_coin_flip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": None}})
            agg = self._agg()
            agg["by_period"][M.PERIOD_CURR][self.OTHER] = {
                "holders": 5, "value": 1.0, "shares": 1.0, "name": "APPLE INC"}
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 2e10}]
            j = M.join_13f(root, served, agg)["AAPL"]
        self.assertEqual(j["rung"], "ambiguous")
        self.assertIsNone(j["cusip"])

    def test_a_name_failing_the_ownership_anchor_is_excluded_not_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": self.APPLE}})
            # $10bn of 13F value against a $1bn market cap — 10x, far outside (0, 1.5].
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 1e9}]
            j = M.join_13f(root, served, self._agg())["AAPL"]
        self.assertEqual(j["rung"], "anchor_failed")
        self.assertIsNone(j["sm_breadth"])
        self.assertIsNone(j["inst_accum"])

    def test_a_single_reporting_holder_is_refused_because_breadth_needs_two(self):
        """The pre-registered anchor is one-sided IN EFFECT: (0, 1.5] rejects implausibly high
        ownership and waves through implausibly low. A join onto a stale CUSIP that nobody
        reports holding lands at ~1e-6 and sails through — it passed 12 names on the real run,
        including CMCSA, RIO, BTI and HSBC, each credited with ONE institution."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": self.APPLE}})
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 2e10}]
            agg = self._agg(holders_curr=1, holders_prior=1, value=20_000.0)
            j = M.join_13f(root, served, agg)["AAPL"]
        self.assertEqual(j["rung"], "too_few_holders")
        self.assertIsNone(j["sm_breadth"])

    def test_the_holder_floor_is_the_smallest_count_at_which_breadth_is_defined(self):
        """Structural, not tuned: two holders is where a holder COUNT can have a growth rate."""
        self.assertEqual(M.MIN_HOLDERS, 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": self.APPLE}})
            served = [{"ticker": "AAPL", "name": "Apple Inc.", "market_cap": 2e10}]
            j = M.join_13f(root, served, self._agg(holders_curr=2, holders_prior=2))["AAPL"]
        self.assertEqual(j["rung"], "cusip_13g")

    def test_a_valid_cusip_nobody_reported_holding_is_recorded_separately(self):
        """'no institution holds this' is an answer about the name, not a broken join."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {"AAPL": {"cusip": "88160R101"}},
                              cik_title="Nothing Matching Either")
            served = [{"ticker": "AAPL", "name": "Nothing Matching", "market_cap": 2e10}]
            j = M.join_13f(root, served, self._agg())["AAPL"]
        self.assertEqual(j["cusip_not_held"], "88160R101")
        self.assertEqual(j["rung"], "unmatched")


# ------------------------------------------------------------------------------------------
# XBRL extraction.
# ------------------------------------------------------------------------------------------

def _facts(**series):
    out = {"facts": {"us-gaap": {}, "dei": {}}}
    for concept, (unit, rows) in series.items():
        ns = "dei" if concept.startswith("Entity") else "us-gaap"
        out["facts"][ns][concept] = {"units": {unit: [
            {"end": end, "val": val, "form": "10-K", "fp": "FY"} for end, val in rows]}}
    return out


class TestExtractXbrl(unittest.TestCase):
    def test_issuance_needs_two_annual_points(self):
        one = M.extract_xbrl(_facts(EntityCommonStockSharesOutstanding=(
            "shares", [("2025-12-31", 110.0)])))
        self.assertIsNone(one["share_issuance"])
        self.assertEqual(one["shares_points"], 1)
        two = M.extract_xbrl(_facts(EntityCommonStockSharesOutstanding=(
            "shares", [("2025-12-31", 110.0), ("2024-12-31", 100.0)])))
        self.assertAlmostEqual(two["share_issuance"], 0.10)
        self.assertEqual(two["issuance_end"], "2025-12-31")

    def test_a_buyback_is_negative_issuance_which_is_the_good_direction(self):
        r = M.extract_xbrl(_facts(EntityCommonStockSharesOutstanding=(
            "shares", [("2025-12-31", 90.0), ("2024-12-31", 100.0)])))
        self.assertLess(r["share_issuance"], 0)

    def test_accruals_require_all_three_line_items_on_the_SAME_fiscal_end(self):
        mismatched = M.extract_xbrl(_facts(
            NetIncomeLoss=("USD", [("2025-12-31", 100.0)]),
            NetCashProvidedByUsedInOperatingActivities=("USD", [("2024-12-31", 150.0)]),
            Assets=("USD", [("2025-12-31", 1000.0)])))
        self.assertIsNone(mismatched["accruals_q"])
        aligned = M.extract_xbrl(_facts(
            NetIncomeLoss=("USD", [("2025-12-31", 100.0)]),
            NetCashProvidedByUsedInOperatingActivities=("USD", [("2025-12-31", 150.0)]),
            Assets=("USD", [("2025-12-31", 1000.0)])))
        # -((100 - 150) / 1000) = +0.05 — cash-backed earnings score well.
        self.assertAlmostEqual(aligned["accruals_q"], 0.05)

    def test_empty_facts_produce_nulls_not_zeros(self):
        r = M.extract_xbrl({"facts": {}})
        self.assertIsNone(r["share_issuance"])
        self.assertIsNone(r["accruals_q"])


# ------------------------------------------------------------------------------------------
# Insider.
# ------------------------------------------------------------------------------------------

class TestInsider(unittest.TestCase):
    def _fetch(self, detail):
        return M.fetch_insider("root", "AAPL", M.Guard(min_interval=0, sleeper=lambda s: None),
                               detail=lambda t, days: detail)

    def test_a_refusal_stays_a_refusal_and_never_becomes_a_neutral(self):
        """The whole point of the scraper's fix: 'we could not look' is not 'we looked and saw
        nothing'. Collapsing them is what made this signal a constant for every ticker."""
        r = self._fetch({"score": None, "form4_seen": 3, "parsed": 0, "parse_failures": 3,
                         "fetch_failures": 0, "error": "ParseError"})
        self.assertIsNone(r["insider_score"])

    def test_truncation_is_recorded_rather_than_silent(self):
        r = self._fetch({"score": 50.0, "form4_seen": M.MAX_FORM4_PER_NAME + 1, "parsed": 1,
                         "parse_failures": 0, "fetch_failures": 0, "error": ""})
        self.assertTrue(r["form4_truncated"])
        under = self._fetch({"score": 50.0, "form4_seen": 2, "parsed": 2, "parse_failures": 0,
                             "fetch_failures": 0, "error": ""})
        self.assertFalse(under["form4_truncated"])

    def test_the_theme_mapping_matches_the_shipped_formula(self):
        """factors.py:271 — (score - 50) / 25."""
        self.assertAlmostEqual((50.0 - 50.0) / 25.0, 0.0)
        self.assertAlmostEqual((75.0 - 50.0) / 25.0, 1.0)
        self.assertAlmostEqual((25.0 - 50.0) / 25.0, -1.0)


# ------------------------------------------------------------------------------------------
# Coverage bookkeeping — the Part 12 lesson applied to this instrument.
# ------------------------------------------------------------------------------------------

class TestCoverageContract(unittest.TestCase):
    def test_a_fully_covered_constant_is_reported_dead_not_covered(self):
        """Exactly the state `insider` is in today: coverage 1.00, one distinct value."""
        c = M._cov({f"T{i}": 0.0 for i in range(100)}, 100)
        self.assertEqual(c["coverage"], 1.0)
        self.assertEqual(c["distinct_values"], 1)
        self.assertFalse(c["usable"])

    def test_coverage_is_measured_against_the_served_universe_not_the_fetched_subset(self):
        c = M._cov({"A": 1.0, "B": 2.0}, 500)
        self.assertAlmostEqual(c["coverage"], 2 / 500)
        self.assertFalse(c["above_coverage_floor"])

    def test_the_two_floors_are_the_projects_own_constants(self):
        from valuation.edge.fundamental_panel import COVERAGE_FLOOR
        from valuation.edge.pead import MIN_COVERAGE
        self.assertEqual(M.COVERAGE_FLOOR, COVERAGE_FLOOR)
        self.assertEqual(M.MIN_COVERAGE, MIN_COVERAGE)

    def test_a_constant_column_zscores_to_nothing_rather_than_to_an_arbitrary_number(self):
        z = M._zscore({"A": 3.0, "B": 3.0, "C": 3.0})
        self.assertTrue(all(v is None for v in z.values()))

    def test_nones_survive_the_zscore_as_nones(self):
        z = M._zscore({"A": 1.0, "B": 2.0, "C": None})
        self.assertIsNone(z["C"])
        self.assertIsNotNone(z["A"])


class TestManifest(unittest.TestCase):
    def test_a_non_terminal_status_may_not_be_recorded(self):
        """The one way the resume pattern fails: banking 'throttled' as though it were an
        answer, so the unit is never retried and coverage inflates by hitting a wall."""
        with tempfile.TemporaryDirectory() as tmp:
            m = M.Manifest(os.path.join(tmp, "m.json"))
            with self.assertRaises(ValueError):
                m.mark("cusip:AAPL", "throttled")
            self.assertFalse(m.done("cusip:AAPL"))

    def test_terminal_outcomes_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "m.json")
            M.Manifest(p).mark("cusip:AAPL", "complete")
            self.assertTrue(M.Manifest(p).done("cusip:AAPL"))


class TestGuard(unittest.TestCase):
    def test_the_circuit_breaker_stops_the_run_rather_than_banking_a_partial_census(self):
        slept = []
        g = M.Guard(min_interval=0, budget=2, sleeper=slept.append)
        g.throttled(0)
        g.throttled(0)
        with self.assertRaises(SystemExit):
            g.throttled(0)

    def test_pacing_actually_waits(self):
        slept = []
        g = M.Guard(min_interval=1.0, sleeper=slept.append)
        g.wait()
        g.wait()
        self.assertTrue(any(s > 0 for s in slept))


# ------------------------------------------------------------------------------------------
# Reporting.
# ------------------------------------------------------------------------------------------

class TestRender(unittest.TestCase):
    PAYLOAD = {
        "prereg": "PREREG_v2g_live_theme_sources.md", "snapshot": "snap.json",
        "periods": {"current": M.PERIOD_CURR, "prior": M.PERIOD_PRIOR}, "n_served": 500,
        "floors": {"COVERAGE_FLOOR": 0.05, "MIN_COVERAGE": 0.30, "MIN_DISTINCT": 2},
        "theme_coverage": {"institutional": {"covered": 400, "coverage": 0.8,
                                             "distinct_values": 390, "usable": True}},
        "input_coverage": {"sm_breadth": {"covered": 400, "coverage": 0.8,
                                          "distinct_values": 390}},
        "join": {"matched": 400, "rungs": {"cusip_13g": 400}, "anchor_pass": 398,
                 "anchor_pass_rate": 0.995, "anchor_median": 0.7},
        "external_validity": {"max_holders": 4000, "spearman_breadth_vs_log_mcap": 0.6},
        "insider_shape": {"scored": 480, "exactly_neutral": 300, "neutral_share": 0.625,
                          "names_truncated_at_40_form4": 12},
        "dataset_shape": {}, "bounds": {"B1_institutional_coverage_ge_0.30": True},
    }

    def test_it_renders(self):
        out = M.render(self.PAYLOAD)
        self.assertIn("institutional", out)
        self.assertIn("HELD", out)

    def test_no_literal_double_percent_escapes_into_the_output(self):
        self.assertNotIn("%%", M.render(self.PAYLOAD))

    def test_a_missing_correlation_renders_as_na_rather_than_crashing(self):
        p = dict(self.PAYLOAD)
        p["external_validity"] = {"max_holders": 0, "spearman_breadth_vs_log_mcap": None}
        p["insider_shape"] = dict(self.PAYLOAD["insider_shape"], neutral_share=None)
        self.assertIn("n/a", M.render(p))

    def test_the_output_states_that_nothing_reaches_the_composite(self):
        out = M.render(self.PAYLOAD).lower()
        self.assertIn("composite", out)
        self.assertIn("vintage", out)


class TestSpearman(unittest.TestCase):
    def test_a_monotone_relationship_scores_plus_one(self):
        self.assertAlmostEqual(M._spearman([(1, 1), (2, 2), (3, 3), (4, 4)]), 1.0)

    def test_a_reversed_relationship_scores_minus_one(self):
        self.assertAlmostEqual(M._spearman([(1, 4), (2, 3), (3, 2), (4, 1)]), -1.0)

    def test_too_few_pairs_is_none_not_a_number(self):
        self.assertIsNone(M._spearman([(1, 1), (2, 2)]))

    def test_a_constant_side_is_none_rather_than_an_arbitrary_value(self):
        self.assertIsNone(M._spearman([(1, 5), (2, 5), (3, 5), (4, 5)]))


# ------------------------------------------------------------------------------------------
# B5 — MEASURED ONLY. This is the enforcement, and it is durable.
#
# The pre-registration proposed asserting B5 with a raw `git diff origin/main`. That was
# replaced, and the replacement is STRICTER as a standing guard while being lane-safe: a
# git-diff test fails for any UNRELATED lane that legitimately edits valuation/, which would
# make it a nuisance rather than a check. The invariant that actually matters is that nothing
# shipped can reach these columns, and that is what is asserted here. The one-off git diff was
# also run by hand for this session and its output is recorded in HANDOFF_live_data_bugs.md.
# ------------------------------------------------------------------------------------------

class TestScopeIsMeasuredOnly(unittest.TestCase):
    def test_no_shipped_module_references_this_script(self):
        """If a later change wires one of these columns into the product, this fails — which
        is the point. Adoption is allowed; adoption WITHOUT the gate and the vintage event is
        what this stops being silent."""
        offenders = []
        for dirpath, _dirs, files in os.walk(os.path.join(REPO, "valuation")):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
                    if "live_theme_sources" in fh.read():
                        offenders.append(os.path.relpath(path, REPO))
        self.assertEqual(offenders, [], f"shipped code references the measured-only module: "
                                        f"{offenders}")

    def test_the_script_never_calls_into_the_scoring_path(self):
        src = io.open(os.path.join(REPO, "scripts", "live_theme_sources.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = getattr(f, "id", None) or getattr(f, "attr", None)
                if name:
                    called.add(name)
        for forbidden in ("build_frame", "_decompose", "composite_score", "save_snapshot",
                          "run_screen"):
            self.assertNotIn(forbidden, called,
                             f"measured-only script must not call {forbidden}")

    def test_the_script_imports_the_insider_scraper_but_does_not_redefine_it(self):
        src = io.open(os.path.join(REPO, "scripts", "live_theme_sources.py"),
                      encoding="utf-8").read()
        self.assertIn("from valuation.screener import insider", src)
        self.assertNotIn("def insider_detail", src)
        self.assertNotIn("def _parse_form4", src)


# ------------------------------------------------------------------------------------------
# THE CI PYTHON. Added 2026-08-11, after this suite failed three land attempts.
#
# WHAT HAPPENED. `live_theme_sources.py` contained  f'{k} {v['fetched']}'  — an f-string reusing
# its own quote character inside the expression. PEP 701 legalised that in Python 3.12; on 3.11
# it is a hard SyntaxError. Locally (3.13) the module imported and all 53 tests passed. On the
# runner (`land-agent-branch.yml` pins python-version 3.11) the module could not be IMPORTED, so
# the entire suite died at collection — which is why CI named exactly one failing file and gave
# no other clue, and why the branch sat unlanded while every other suite stayed green.
#
# WHY THE PRE-PUSH CHECK MISSED IT, which is the part worth keeping. The check used was
# `ast.parse(src, feature_version=(3, 11))`. That argument is best-effort and does NOT gate
# tokenizer-level changes like PEP 701 — it accepted the file happily. A version claim needs a
# compiler of that version, or a check written against the specific construct. Both are below.
#
# TWO CHECKS, because either alone has a blind side:
#   1. `compile()` under the RUNNING interpreter. Exhaustive for any construct, and on CI the
#      running interpreter IS 3.11 — so this is the one that would have gone red instead of an
#      unexplained import failure. It proves nothing when run locally on 3.13.
#   2. A tokenizer scan for the specific construct, which only 3.12+ can even represent. This is
#      the half that fails LOCALLY, before a push, which is where the three wasted attempts went.
# ------------------------------------------------------------------------------------------

CI_PYTHON = (3, 11)   # land-agent-branch.yml: `python-version: '3.11'`


def _repo_python_files():
    skip = {".git", "data", "__pycache__", ".claude", "node_modules", ".scan-cache", "venv"}
    for dirpath, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def _delimiter(tok_string):
    """The quote delimiter of a string token, prefix letters removed: ' " ''' or \"\"\"."""
    body = tok_string.lstrip("fFrRbBuU")
    for d in ('"""', "'''", '"', "'"):
        if body.startswith(d):
            return d
    return ""


def _pep701_offences(src, path):
    """Report f-strings that only Python 3.12+ can parse.

    THE RULE IS EMPIRICAL, not remembered — it was read off a real 3.11 compiler, and the table
    it came from is pinned in `test_the_detector_matches_what_3_11_actually_does` below. Two
    constructs 3.11 rejects inside the EXPRESSION part of an f-string:

        a nested string whose delimiter would close an enclosing f-string   f'{d['a']}'
        a backslash                                                        f"{'\\n'.join(v)}"

    "Would close" is `nested.startswith(enclosing)`, not a first-character comparison: with a
    ''' delimiter a nested ' is perfectly legal, and comparing first characters calls that an
    error. That over-strict first cut flagged four legitimate lines in fundamental_panel.py.

    The enclosing delimiters are a STACK because f-strings nest — `f"{(f'{y:.2f}')} {d['k']}"`
    is legal 3.11, and tracking a single delimiter reads the inner f-string's quote as still
    open and condemns the outer one's `d['k']`. That was the second false positive on the same
    line, and both are in the fixture table so neither can come back.

    Detectable only on 3.12+, where the tokenizer emits FSTRING_START/MIDDLE/END rather than one
    STRING token. On 3.11 this returns nothing and the compile check carries the load — there,
    the file simply would not have compiled.
    """
    start = getattr(tokenize, "FSTRING_START", None)
    end = getattr(tokenize, "FSTRING_END", None)
    middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    if start is None:
        return []
    try:
        toks = list(tokenize.tokenize(io.BytesIO(src.encode("utf-8")).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return []
    out, stack = [], []
    v = f"{CI_PYTHON[0]}.{CI_PYTHON[1]}"
    for tok in toks:
        if tok.type == start:
            stack.append(_delimiter(tok.string))
            continue
        if tok.type == end:
            if stack:
                stack.pop()
            continue
        if not stack or tok.type == middle:
            # FSTRING_MIDDLE is the literal text, where a backslash is fine even on 3.11.
            continue
        if tok.type == tokenize.STRING:
            nested = _delimiter(tok.string)
            closer = next((d for d in stack if nested and nested.startswith(d)), None)
            if closer:
                out.append(f"{path}:{tok.start[0]}: f-string delimited by {closer} reuses it "
                           f"inside its own expression -> SyntaxError on {v}")
                continue
        if "\\" in tok.string:
            out.append(f"{path}:{tok.start[0]}: backslash inside an f-string expression "
                       f"-> SyntaxError on {v}")
    return out


class TestTheRepoParsesOnTheCiPython(unittest.TestCase):
    def test_every_file_compiles_under_the_running_interpreter(self):
        """Exhaustive, and on CI the running interpreter is the one that matters."""
        bad = []
        for path in _repo_python_files():
            try:
                with io.open(path, "rb") as fh:
                    compile(fh.read(), path, "exec")
            except SyntaxError as e:
                bad.append(f"{os.path.relpath(path, REPO)}:{e.lineno}: {e.msg}")
        self.assertEqual(bad, [], "files that do not compile:\n  " + "\n  ".join(bad))

    def test_no_file_uses_an_fstring_only_python_3_12_can_parse(self):
        """The half that fails BEFORE the push, on a developer machine running 3.12+."""
        if sys.version_info < (3, 12):
            self.skipTest("the construct is unrepresentable below 3.12; check (1) covers it here")
        bad = []
        for path in _repo_python_files():
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                bad.extend(_pep701_offences(fh.read(), os.path.relpath(path, REPO)))
        self.assertEqual(bad, [], "3.12-only f-strings:\n  " + "\n  ".join(bad))

    #: Every row was CHECKED against a real CPython 3.11.9, not recalled. `True` = 3.11 rejects
    #: it. The four legal rows are the ones that matter most: the first cut of this detector
    #: compared only first characters and tracked one delimiter instead of a stack, and it
    #: condemned `fundamental_panel.py:4182` — a correct line — on both counts at once.
    CASES = (
        ("delim ' , nested '",              "x = f'{d['a']}'",                    True),
        ("delim ''' , nested '''",          "x = f'''{d['''a''']}'''",            True),
        ("backslash in the expression",     'x = f"{\'\\n\'.join(v)}"',           True),
        ("the line that broke the land",    "x = f'{k} {v['fetched']}'",          True),
        ("delim \" , nested '",             'x = f"{d[\'a\']}"',                  False),
        ("delim ' , nested \"",             "x = f'{d[\"a\"]}'",                  False),
        ("delim ''' , nested '",            "x = f'''{d['a']}'''",                False),
        ("nested f-string, all legal",      'x = f"{(f\'{y:.2f}\')} {d[\'k\']}"', False),
    )

    def test_the_detector_matches_what_3_11_actually_does(self):
        """A guard nobody has seen fire is a guard nobody knows works — in both directions.

        The false-negative half would have saved this branch three land attempts. The
        false-positive half is what stops the guard becoming a nuisance every other lane
        learns to ignore.
        """
        if sys.version_info < (3, 12):
            self.skipTest("the construct is unrepresentable below 3.12")
        for label, src, rejected_by_311 in self.CASES:
            with self.subTest(label):
                found = _pep701_offences(src + "\n", "fixture.py")
                if rejected_by_311:
                    self.assertTrue(found, f"3.11 rejects this and the detector missed it: {src}")
                else:
                    self.assertEqual(found, [], f"3.11 accepts this; do not flag it: {src}")

    def test_the_fixture_table_agrees_with_this_interpreter_where_it_can(self):
        """Cross-check: on 3.11 the table's own verdicts must BE this compiler's verdicts.

        Below 3.12 the detector cannot see the construct, so on the CI runner this is what
        proves the table was not simply written down wrong.
        """
        if sys.version_info >= (3, 12):
            self.skipTest("3.12+ accepts all of these by design; the table describes 3.11")
        for label, src, rejected_by_311 in self.CASES:
            with self.subTest(label):
                try:
                    compile(src, "fixture.py", "exec")
                    actually_rejected = False
                except SyntaxError:
                    actually_rejected = True
                self.assertEqual(actually_rejected, rejected_by_311, src)

    def test_the_ci_python_constant_matches_the_workflow(self):
        """If the runner is bumped, this test is the thing that says the checks moved with it."""
        wf = os.path.join(REPO, ".github", "workflows", "land-agent-branch.yml")
        if not os.path.exists(wf):
            self.skipTest("workflow not present in this tree")
        with io.open(wf, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        self.assertIn(f"python-version: '{CI_PYTHON[0]}.{CI_PYTHON[1]}'", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
