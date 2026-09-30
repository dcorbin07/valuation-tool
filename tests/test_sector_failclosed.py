"""
AN EMPTY SECTOR USED TO READ AS "NOT A FINANCIAL", AND A BANK GOT AN UNLEVERED DCF.

Measured on valquo.co, `POST /api/value`, 2026-09-30 ~13:45 ET — **four of four financials**:

    KNSL  sector ""  -> hypergrowth  FV ~$625  88 Strong Buy
    TRV   sector ""  -> mature       FV ~$702  89 Strong Buy
    PGR   sector ""  -> growth                 87 Strong Buy
    JPM   sector ""  -> growth                 49 Hold

The same service read KNSL as `financial` at ~03:48 ET ($291 P/B-ROE, 67 Buy), so `yfinance`'s
`info` fails **intermittently** from Render. **An intermittent fail-open is worse than a
permanent one** — invisible in any single local run, and the same ticker gets a different
valuation MODEL depending on which request happened to reach Yahoo.

`classify` tested `sector in FINANCIAL_SECTORS or any(hint in industry)`; `""` matches neither,
so the name fell through to the growth branch. Nothing downstream was wrong — the DCF was a
correct DCF — which is exactly why it survived. **The error was upstream of every number.**

Run:  python -m pytest tests/test_sector_failclosed.py
      python tests/test_sector_failclosed.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402  (above every valuation import, audit LA15)

from valuation.data import sector_resolve as SR                         # noqa: E402
from valuation.data.models import CompanyData                           # noqa: E402
from valuation.engine.classify import classify, UNKNOWN                  # noqa: E402


class _Cfg:
    sec_user_agent = "valuation-tool test@example.com"
    fmp_api_key = None


class TestTheChainOrder(unittest.TestCase):

    def setUp(self):
        SR.reset_census()

    def test_a_WORKING_primary_short_circuits_every_fallback(self):
        """The fallbacks exist for the failure, not to second-guess a working fetch. If the
        primary's answer were ever overridden, the chain would be a silent re-classifier."""
        calls = []
        for name in ("_from_scan", "_from_sec", "_from_fmp"):
            setattr(SR, name, lambda *a, **k: calls.append(name))
        sector, src = SR.resolve_sector("KNSL", _Cfg(), current="Financial Services")
        self.assertEqual(sector, "Financial Services")
        self.assertEqual(src, SR.SRC_PRIMARY)
        self.assertEqual(calls, [], "a fallback ran while the primary had an answer")

    def test_the_order_is_scan_then_SEC_then_FMP_and_it_STOPS_at_the_first_hit(self):
        """Order is not cosmetic: the scan costs no network call, SEC costs one free call, FMP
        costs money. Running a later rung after an earlier one answered is pure waste."""
        seen = []

        def mk(name, ret):
            def f(*a, **k):
                seen.append(name)
                return ret
            return f
        SR._from_scan = mk("scan", None)
        SR._from_sec = mk("sec", "Financial Services")
        SR._from_fmp = mk("fmp", "Technology")
        sector, src = SR.resolve_sector("KNSL", _Cfg(), current="")
        self.assertEqual((sector, src), ("Financial Services", SR.SRC_SEC))
        self.assertEqual(seen, ["scan", "sec"], "the chain did not stop at the first hit")

    def test_EVERY_rung_failing_is_UNRESOLVED_and_never_a_guess(self):
        """FAIL CLOSED. The defect was not that the sector was missing — it was that missing
        read as 'not a financial'."""
        SR._from_scan = lambda *a, **k: None
        SR._from_sec = lambda *a, **k: None
        SR._from_fmp = lambda *a, **k: None
        sector, src = SR.resolve_sector("KNSL", _Cfg(), current="")
        self.assertIsNone(sector, "the chain invented a sector")
        self.assertEqual(src, SR.SRC_NONE)

    def test_a_FAILING_rung_does_not_abort_the_chain(self):
        """A rung that raises must be a rung that declines. Otherwise one flaky source takes
        down the two behind it — which is how a fallback chain becomes a single point."""
        def boom(*a, **k):
            raise RuntimeError("vendor down")
        SR._from_scan = boom
        SR._from_sec = lambda *a, **k: "Financial Services"
        sector, src = SR.resolve_sector("KNSL", _Cfg(), current="")
        self.assertEqual((sector, src), ("Financial Services", SR.SRC_SEC))


class TestTheSICMap(unittest.TestCase):

    def test_the_finance_range_maps_to_the_vocabulary_the_engine_ALREADY_speaks(self):
        """`Financial Services` is the string `FINANCIAL_SECTORS` already holds. A new synonym
        would mean every downstream test of "is this a financial" had to learn a second name."""
        from valuation.engine.classify import FINANCIAL_SECTORS
        for sic in (6000, 6199, 6311, 6500, 6799):
            with self.subTest(sic=sic):
                got = SR.sector_from_sic(sic)
                self.assertIn(got, FINANCIAL_SECTORS, "SIC %s did not map" % sic)

    def test_OUTSIDE_the_range_returns_None_so_the_chain_CONTINUES(self):
        """Only finance is mapped, on purpose: inventing a map for the other SIC divisions
        would trade a known-missing sector for a plausible-but-wrong one — the failure being
        repaired, in a new costume."""
        for sic in (5999, 6800, 3711, 7372, None, "", "n/a"):
            with self.subTest(sic=sic):
                self.assertIsNone(SR.sector_from_sic(sic))

    def test_a_STRING_sic_is_accepted_because_SEC_returns_one(self):
        """`submissions` serves `"sic": "6331"` as a string. An int-only map would decline every
        real answer and the SEC rung would be dead code that looks alive."""
        self.assertEqual(SR.sector_from_sic("6331"), "Financial Services")


class TestTheUnknownRegime(unittest.TestCase):

    def _cd(self, **kw):
        cd = CompanyData(ticker="X")
        cd.revenue = 1000.0
        cd.revenue_history = [1000.0, 790.0, 620.0]      # ~26% growth, KNSL's live reading
        cd.fiscal_years = [2025, 2024, 2023]
        for k, v in kw.items():
            setattr(cd, k, v)
        return cd

    def test_an_UNRESOLVED_sector_is_UNKNOWN_not_hypergrowth(self):
        """THE defect. 26% revenue growth and no sector used to mean 'hypergrowth'."""
        c = classify(self._cd(sector_source=SR.SRC_NONE))
        self.assertEqual(c.regime, UNKNOWN)
        self.assertEqual(c.dcf_reliability, "low")
        self.assertTrue(any("could not be determined" in r for r in c.reasons))

    def test_the_SAME_company_with_a_RESOLVED_financial_sector_is_financial(self):
        """The positive control. Without it, `unknown` everywhere would pass this file."""
        c = classify(self._cd(sector="Financial Services", sector_source=SR.SRC_SEC))
        self.assertEqual(c.regime, "financial")

    def test_a_BLANK_source_keeps_the_OLD_behaviour_exactly(self):
        """Offline and batch callers build a `CompanyData` by hand and never run the chain. If
        a blank source meant UNKNOWN, every one of them would silently stop being valued — a
        far larger change than the one intended, arriving as a side effect."""
        c = classify(self._cd(sector="", sector_source=""))
        self.assertNotEqual(c.regime, UNKNOWN)

    def test_the_classification_NAMES_the_source_so_decision_and_disclosure_SIT_TOGETHER(self):
        """The live defect disclosed itself in `quality_notes` — *"Yahoo `info` unavailable"* —
        while `classification.reasons` gave a confident *"High revenue growth (~26%)"*. **A
        disclosure in a different object from the decision it qualifies is one a reader of the
        decision never sees.**"""
        for src, needle in ((SR.SRC_SEC, "SEC"), (SR.SRC_SCAN, "scan"),
                            (SR.SRC_FMP, "profile API")):
            with self.subTest(src=src):
                c = classify(self._cd(sector="Financial Services", sector_source=src))
                self.assertTrue(any(needle in r for r in c.reasons),
                                "the classification does not say where the sector came from")

    def test_a_PRIMARY_sourced_sector_adds_NO_note(self):
        """Non-vacuity for the test above: if every path added a note, 'it names the source'
        would be true of a function that always appends the same string."""
        c = classify(self._cd(sector="Financial Services", sector_source=SR.SRC_PRIMARY))
        self.assertFalse(any("resolved from" in r for r in c.reasons))


class TestTheValuationIsWithheld(unittest.TestCase):

    def test_an_unknown_regime_REFUSES_before_the_plausibility_guard(self):
        """`publication_guard` asks whether a fair value is CREDIBLE; it cannot ask whether the
        MODEL was the right one, because by the time it sees a number the model is chosen. The
        live $907 DCF was entirely plausible — that is why it shipped."""
        from valuation.engine.pipeline import _unknown_regime_refusal, UNKNOWN_REGIME_REFUSAL

        class _C:
            regime = UNKNOWN
        self.assertEqual(_unknown_regime_refusal(_C()), UNKNOWN_REGIME_REFUSAL)

        class _F:
            regime = "financial"
        self.assertIsNone(_unknown_regime_refusal(_F()))

    def test_the_refusal_text_says_WHY_rather_than_only_THAT(self):
        """A page reading 'unavailable' teaches a user nothing; this one has to say the industry
        could not be determined, which is a different and checkable claim."""
        from valuation.engine.pipeline import UNKNOWN_REGIME_REFUSAL
        low = UNKNOWN_REGIME_REFUSAL.lower()
        self.assertIn("industry could not be determined", low)
        self.assertIn("bank or insurer", low)

    def test_the_refusal_is_wired_AT_THE_CALL_SITE_and_runs_FIRST(self):
        """The helper being right is not the product being right — the MC8 shape, and it has
        cost this project three separate misses. Read off the syntax tree so the ORDER is
        asserted too: a refusal that runs after the plausibility guard lets a plausible number
        from the wrong model through."""
        import ast
        import io as _io
        src = _io.open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "valuation/engine/pipeline.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "value_from_company")
        found = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "refusal":
                self.assertIsInstance(node.value, ast.BoolOp, "the two guards are not combined")
                self.assertIsInstance(node.value.op, ast.Or)
                first = node.value.values[0]
                self.assertEqual(getattr(first.func, "id", None), "_unknown_regime_refusal",
                                 "the provenance refusal does not run FIRST")
                found = True
        self.assertTrue(found, "the refusal assignment is no longer where this guard looks")


class TestTheCensus(unittest.TestCase):

    def test_every_outcome_is_counted_including_the_primary_and_the_failure(self):
        """A service quietly living on the SEC rung looks identical to one whose primary is
        healthy. Counting only the fallbacks would hide exactly that."""
        SR.reset_census()
        SR._from_scan = lambda *a, **k: None
        SR._from_sec = lambda *a, **k: None
        SR._from_fmp = lambda *a, **k: None
        SR.resolve_sector("A", _Cfg(), current="Technology")
        SR.resolve_sector("B", _Cfg(), current="")
        c = SR.source_census()
        self.assertEqual(c["by_source"].get(SR.SRC_PRIMARY), 1)
        self.assertEqual(c["by_source"].get(SR.SRC_NONE), 1)
        self.assertEqual(c["n"], 2)
        self.assertAlmostEqual(c["share"][SR.SRC_PRIMARY], 0.5)

    def test_the_census_SAYS_its_scope_rather_than_implying_a_history(self):
        """It is process-local and Render runs several workers and recycles them. A share
        presented without that reads as a complete history of the service."""
        self.assertIn("worker", SR.source_census()["scope"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
