"""
THE INSIDER COMPONENT WAS A CONSTANT. This pins the fix.

`filings.recent.primaryDocument` for a Form 4 is almost always EDGAR's
XSL-RENDERED view — `xslF345X03/ownership.xml` — which serves **HTML**, not XML.
Measured over the 370,681 Form 4 filings indexed for the C1 backtest, **99.3%**
carry an `xsl...` prefix.

`edgar.get_insider_txns` built exactly that URL. `_parse_form4_xml` called
`ET.fromstring` on the HTML, raised `ParseError`, caught it, and returned `[]`.
`scoring.insider_score([])` is documented to mean "fetched, nothing qualifying"
and returns a NEUTRAL 50.0.

So every name, on every run, scored exactly 50 on insider — a component carrying
20% of the Established weight and 30% of the Speculative weight. Measured
directly: 597 documents fetched through the old URL, 597 parsed to zero
transactions.

This is the same defect as the `dcf_upside` bug already in this project's
record — "a 35% weight that is a constant is not a factor, it is a rounding
error with extra steps" — except this one hid behind an exception handler
instead of behind a missing computation.

    cd screener && python -m unittest tests.test_form4_url -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import edgar
import scoring as S


class RawDocPath(unittest.TestCase):
    def test_every_observed_xsl_prefix_is_stripped(self):
        """All six renderer versions seen across 370,681 real filings."""
        for pref, n in (("xslF345X01", 1903), ("xslF345X02", 63225),
                        ("xslF345X03", 232281), ("xslF345X04", 6508),
                        ("xslF345X05", 56144), ("xslF345X06", 8025)):
            self.assertEqual(edgar.raw_form4_doc(f"{pref}/ownership.xml"),
                             "ownership.xml",
                             f"{pref} ({n:,} filings) not stripped")

    def test_case_insensitive(self):
        self.assertEqual(edgar.raw_form4_doc("XSLF345X03/doc4.xml"), "doc4.xml")

    def test_an_unprefixed_document_is_left_alone(self):
        """0.7% of filings already point at the raw XML."""
        self.assertEqual(edgar.raw_form4_doc("ownership.xml"), "ownership.xml")
        self.assertEqual(edgar.raw_form4_doc("wf-form4_1234.xml"),
                         "wf-form4_1234.xml")

    def test_a_non_xsl_directory_is_not_stripped(self):
        """Only the renderer prefix goes. Anything else is a real path."""
        self.assertEqual(edgar.raw_form4_doc("subdir/ownership.xml"),
                         "subdir/ownership.xml")

    def test_empty_and_none_survive(self):
        self.assertIsNone(edgar.raw_form4_doc(None))
        self.assertEqual(edgar.raw_form4_doc(""), "")


class HtmlIsNotAnEmptyFiling(unittest.TestCase):
    """
    The parse failure must be distinguishable from a genuinely empty filing.
    Returning [] for both is what let this survive: `insider_score` maps [] to a
    confident, neutral 50 — a real observation — so a total fetch failure was
    indistinguishable from "we looked and there was nothing".
    """

    XSL_BODY = ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'
                '<html><body><table><tr><td>Reporting Owner</td></tr></table>'
                '</body></html>')

    RAW_BODY = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <rptOwnerName>DOE JANE</rptOwnerName>
    <reportingOwnerRelationship><isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTransaction>
    <transactionDate><value>2024-05-01</value></transactionDate>
    <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
    <transactionAmounts>
      <transactionShares><value>1000</value></transactionShares>
      <transactionPricePerShare><value>25.5</value></transactionPricePerShare>
    </transactionAmounts>
  </nonDerivativeTransaction>
</ownershipDocument>"""

    def test_the_rendered_html_yields_nothing(self):
        self.assertEqual(edgar._parse_form4_xml(self.XSL_BODY), [],
                         "characterisation: the HTML view carries no parseable "
                         "transactions, which is why the URL matters")

    def test_the_raw_xml_yields_a_real_transaction(self):
        txns = edgar._parse_form4_xml(self.RAW_BODY)
        self.assertEqual(len(txns), 1)
        t = txns[0]
        self.assertEqual(t["code"], "P")
        self.assertEqual(t["role"], "CEO")
        self.assertEqual(t["person"], "DOE JANE")
        self.assertAlmostEqual(t["value_usd"], 25_500.0)


class TheScoreWasAConstant(unittest.TestCase):
    """
    Why this was worth chasing rather than filing as a data nit: show that the
    broken path and the working path produce different SCORES, not just
    different parse results.
    """

    def test_empty_scores_exactly_neutral(self):
        self.assertEqual(S.insider_score([]), 50.0)

    def test_a_real_ceo_purchase_does_not(self):
        txns = edgar._parse_form4_xml(HtmlIsNotAnEmptyFiling.RAW_BODY)
        score = S.insider_score(txns)
        self.assertNotEqual(score, 50.0)
        self.assertGreater(score, 50.0, "an open-market CEO buy must score above neutral")

    def test_the_whole_component_collapses_when_every_filing_fails_to_parse(self):
        """
        The live behaviour, reconstructed: parse each of several DIFFERENT
        filings through the HTML path and every one scores 50 — no dispersion
        at all across names, which is what a constant looks like in a
        cross-section.
        """
        bodies = [HtmlIsNotAnEmptyFiling.XSL_BODY] * 5
        scores = {S.insider_score(edgar._parse_form4_xml(b)) for b in bodies}
        self.assertEqual(scores, {50.0},
                         "every name scoring 50 IS the bug — a 20-30% weight "
                         "with zero cross-sectional dispersion")


if __name__ == "__main__":
    unittest.main()
