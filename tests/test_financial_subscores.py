"""
TWO SUB-SCORES STILL USED INDUSTRIAL MEASURES ON BANKS AND INSURERS.

879cda6 set the rule -- an input that does not apply to the regime does not contribute -- and
applied it to the VALUATION sub-score. Measured live on 2026-09-30, two more were still running
FCFF-model concepts on a financial, and together they are **45% of a financial's score**:

  * **quality (0.25)** led with ROIC vs WACC, plus gross margin and EBIT margin.
  * **health (0.20)** read net debt / EBITDA, interest coverage and a free-cash-flow check.
    KNSL scored **100 of 100** on health because its net debt / EBITDA is **-3.8x**, which the
    curve reads as deep net cash -- for an insurer that is largely **policyholder float and
    reserves**, the same fact that made 879cda6 stop the narrative claiming net cash.

MEASURED, PAIRED ON ONE FETCH PER NAME (`FIN_SCORE_BEFORE_AFTER.json`): KNSL **67 Buy -> 59
Hold**, and its whole move is the health withdrawal -- the quality substitution is worth
**0.08 of a point** on that name (91.9523 -> 92.0346), because its ROIC-vs-WACC and ROE-vs-Ke
spreads happen to land close and it reports no gross margin at all. Saying so matters: the
quality change is a CORRECTNESS fix whose effect on this particular name is nearly nil.

THIS IS THE 1-100 OPPORTUNITY SCORE (`engine.scoring.compute_score`). The hot-list composite,
the Valquo Index and the forward track do not read it -- pinned below -- so no vintage opens.

Run:  python -m pytest tests/test_financial_subscores.py
      python tests/test_financial_subscores.py
"""
from __future__ import annotations

import ast
import io
import os
import subprocess
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.data.models import CompanyData                           # noqa: E402
from valuation.engine import scoring as S                               # noqa: E402
from valuation.engine.classify import Classification                    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cd(**kw) -> CompanyData:
    cd = CompanyData(ticker=kw.pop("ticker", "TEST"))
    for k, v in kw.items():
        setattr(cd, k, v)
    return cd


def _insurer(**over) -> CompanyData:
    """KNSL's MEASURED shape, 2026-09-30, so the fixture is the real thing's arithmetic."""
    # `da` and `interest_expense` are present ON PURPOSE: without them
    # `net_debt_to_ebitda` and `interest_coverage` are None, the industrial health score
    # collapses to its FCF term, and the fixture would exercise neither of the two inputs this
    # change exists to withdraw. A fixture that cannot reach the defect proves nothing.
    # net_debt = 100 - 1500 = -1400; ebitda = 329.1 + 42.0 = 371.1 -> -3.77x, KNSL's measured
    # reading and the whole reason its health scored 100 of 100.
    base = dict(net_income=257.0, total_equity=1000.0, revenue=956.3,
                total_debt=100.0, cash_sti=1500.0, ebit=329.1, da=42.0,
                interest_expense=12.0, fcf=180.0,
                effective_tax_rate=0.21, gross_profit=None)
    base.update(over)
    return _cd(**base)


def _cls(regime="financial", **kw) -> Classification:
    c = Classification()
    c.regime = regime
    for k, v in kw.items():
        setattr(c, k, v)
    return c


class TestQualityUsesTheRightReturnMeasure(unittest.TestCase):

    def test_a_financial_is_scored_on_ROE_vs_COST_OF_EQUITY_not_ROIC_vs_WACC(self):
        """Invested capital and a WACC describe a firm that raises debt to fund operating
        assets. For a bank or insurer debt (and float, and reserves) is the RAW MATERIAL --
        `classify.py`'s own stated reason for refusing the unlevered model on these names."""
        cd = _insurer(invested_capital=1110.0)      # gives a ROIC well clear of WACC
        self.assertIsNotNone(cd.roic, "the fixture must exercise the ROIC path at all")
        _, drivers = S._quality_score(cd, 0.0955, regime="financial", ke=0.0970)
        blob = " ".join(drivers)
        self.assertIn("cost of equity", blob)
        self.assertIn("ROE", blob)
        # NOT a substring ban on "WACC": the driver names it in a NEGATION ("ROIC vs WACC does
        # not apply to a bank or insurer"), so banning the token would ban the explanation --
        # the guard-fires-on-its-own-prose family this project has hit repeatedly. The real
        # property is that the SCORE does not depend on the WACC, asserted by moving it.
        self.assertIn("does not apply", blob)
        lo, _ = S._quality_score(cd, 0.02, regime="financial", ke=0.0970)
        hi, _ = S._quality_score(cd, 0.40, regime="financial", ke=0.0970)
        self.assertAlmostEqual(lo, hi, places=9,
                               msg="a financial's quality still moves with the WACC")

    def test_the_SPREAD_MOVES_WITH_ke_which_is_what_makes_it_the_right_hurdle(self):
        """A driver that merely says the right words is not the same as a score that uses the
        right number. Raising the cost of equity must lower the sub-score."""
        cd = _insurer(invested_capital=1110.0)
        cheap, _ = S._quality_score(cd, 0.0955, regime="financial", ke=0.05)
        dear, _ = S._quality_score(cd, 0.0955, regime="financial", ke=0.20)
        self.assertGreater(cheap, dear, "ke does not move the financial quality score")

    def test_GROSS_and_EBIT_MARGIN_DO_NOT_CONTRIBUTE_for_a_financial(self):
        """A bank has no cost of goods sold, and interest is operating REVENUE for a lender, so
        EBIT is not a measure of operating profitability. Both are dropped -- asserted by
        moving them wildly and requiring the score not to budge."""
        a = _insurer(invested_capital=1110.0, gross_profit=10.0, ebit=10.0)
        b = _insurer(invested_capital=1110.0, gross_profit=900.0, ebit=900.0)
        qa, _ = S._quality_score(a, 0.0955, regime="financial", ke=0.0970)
        qb, _ = S._quality_score(b, 0.0955, regime="financial", ke=0.0970)
        self.assertAlmostEqual(qa, qb, places=9,
                               msg="gross or EBIT margin still moves a financial's quality")

    def test_NET_MARGIN_REPLACES_THEM_and_DOES_move_the_score(self):
        """The replacement has to be live, or "dropped two terms" is just a narrower score.

        REVENUE is what varies, NOT net income. An earlier cut moved `net_income`, which drives
        ROE as well -- so the score moved through the OTHER term and the test passed with net
        margin's weight set to ZERO (mutation f6, MISSED). Revenue moves net margin and leaves
        ROE untouched, which is the only way to isolate the term under test.
        """
        thin = _insurer(invested_capital=1110.0, revenue=257.0 / 0.02)    # 2% net margin
        fat = _insurer(invested_capital=1110.0, revenue=257.0 / 0.35)     # 35% net margin
        self.assertAlmostEqual(thin.net_income / thin.total_equity,
                               fat.net_income / fat.total_equity, places=12,
                               msg="the fixture moved ROE too, so it cannot isolate net margin")
        qt, _ = S._quality_score(thin, 0.0955, regime="financial", ke=0.0970)
        qf, _ = S._quality_score(fat, 0.0955, regime="financial", ke=0.0970)
        self.assertGreater(qf, qt, "net margin does not contribute to a financial's quality")

    def test_a_financial_with_NO_cost_of_equity_falls_back_to_RAW_ROE_and_SAYS_SO(self):
        """Failing to a plain ROE is right; failing to ROIC-vs-WACC would not be."""
        cd = _insurer(invested_capital=1110.0)
        q, drivers = S._quality_score(cd, 0.0955, regime="financial", ke=None)
        self.assertIsNotNone(q)
        blob = " ".join(drivers)
        self.assertIn("Return on equity", blob)
        self.assertIn("no cost of equity", blob)
        self.assertNotIn("WACC", blob)


class TestHealthIsWithheldForAFinancial(unittest.TestCase):

    def test_health_is_NOT_SCORED_and_the_reason_is_SAID(self):
        """A withheld sub-score that is silent looks identical to one that scored in the
        middle. KNSL's -3.8x net debt/EBITDA read as 100 of 100."""
        cd = _insurer()
        self.assertLess(cd.net_debt_to_ebitda, -1.0,
                        "the fixture must reproduce the net-cash-looking balance sheet")
        h, drivers = S._health_score(cd, _cls("financial"))
        self.assertIsNone(h, "a financial is still being scored on industrial leverage")
        self.assertTrue(drivers, "the sub-score was withheld silently")
        blob = " ".join(drivers).lower()
        self.assertIn("float", blob)
        self.assertIn("redistributed", blob)

    def test_the_SAME_BALANCE_SHEET_still_scores_100_on_a_NON_financial(self):
        """The positive control. Without it, a health score of None would be consistent with
        the function simply having stopped working."""
        cd = _insurer()
        h, _ = S._health_score(cd, _cls("mature", is_cash_burning=False))
        self.assertIsNotNone(h)
        self.assertGreater(h, 90.0)

    def test_assets_over_equity_is_NOT_silently_substituted(self):
        """The obvious financial measure is balance-sheet leverage -- and `CompanyData` HAS NO
        `total_assets`. `assets` exists only in the edge lane's Sharadar panel, a different
        object on a different path. A proxy built from `total_debt` would re-introduce the very
        confusion being removed, since a bank's big liability is deposits and an insurer's is
        reserves. This pins that nobody quietly adds one without adding the field."""
        self.assertFalse(hasattr(CompanyData(ticker="X"), "total_assets"),
                         "CompanyData grew a total_assets field -- health can now be scored "
                         "for a financial, and this test should be replaced by one that does")


class TestTheCompositeAndConfidence(unittest.TestCase):

    def _score(self, regime):
        cd = _insurer(invested_capital=1110.0)
        cls = _cls(regime, dcf_reliability="high", blended_growth=0.10)
        return S.compute_score(cd, cls, 0.0955, 100.0, None, None, ke=0.0970)

    def test_the_withheld_weight_is_REDISTRIBUTED_not_treated_as_zero(self):
        """`compute_score` renormalises over the available sub-scores. Treating a withheld
        health as 0 would savage every financial; treating it as 50 would invent a number."""
        r = self._score("financial")
        subs = dict(r.subscores)
        self.assertIsNone(subs["health"])
        w = dict(S._WEIGHTS["financial"])
        num = sum(subs[k] * w[k] for k in subs if subs[k] is not None)
        den = sum(w[k] for k in subs if subs[k] is not None)
        self.assertAlmostEqual(r.composite_raw if hasattr(r, "composite_raw") else r.score,
                               round(max(1, min(100, num / den))), delta=1)

    def test_NOT_APPLICABLE_does_not_degrade_the_CONFIDENCE_label(self):
        """A sub-score withheld by design is not a data gap. Counting it as missing would
        downgrade every financial's confidence and report a hole that is not there.

        HEALTH MUST BE THE ONLY `None`, and that is asserted rather than hoped. An earlier cut
        left the VALUATION sub-score None as well (no price, so no margin of safety), which
        pins both arms at the same degraded label whatever the rule does -- the mutation that
        counts a not-applicable sub-score as missing was MISSED (f7). A test whose subject is
        masked by a second defect in its own fixture measures nothing.
        """
        cd = _insurer(invested_capital=1110.0, price=90.0, shares_out=10.0,
                      ma_200=80.0, ret_6m=0.12)
        cls = _cls("financial", dcf_reliability="high", blended_growth=0.10)
        r = S.compute_score(cd, cls, 0.0955, 100.0, None, None, ke=0.0970)
        subs = dict(r.subscores)
        self.assertIsNone(subs["health"])
        self.assertEqual([k for k, v in subs.items() if v is None], ["health"],
                         "another sub-score is also None, so this cannot isolate the rule")
        cls2 = _cls("mature", dcf_reliability="high", blended_growth=0.10,
                    is_cash_burning=False)
        r2 = S.compute_score(cd, cls2, 0.0955, 100.0, None, None, ke=0.0970)
        self.assertEqual(r.confidence, r2.confidence,
                         "withholding health by REGIME changed the confidence label")


class TestInertnessOnEveryOtherRegime(unittest.TestCase):
    """THE CHANGE MUST BE INVISIBLE OUTSIDE `financial`, compared against the REAL old code."""

    @classmethod
    def setUpClass(cls):
        src = subprocess.run(["git", "show", "HEAD:valuation/engine/scoring.py"],
                             capture_output=True, encoding="utf-8", cwd=REPO).stdout
        cls.old = None
        if not src.strip():
            return
        if "_not_applicable" in src:
            return                       # HEAD already carries the change; nothing to compare
        mod = types.ModuleType("scoring_head")
        mod.__package__ = "valuation.engine"
        mod.__dict__["__package__"] = "valuation.engine"
        sys.modules["scoring_head"] = mod
        exec(compile(src, "scoring_head.py", "exec"), mod.__dict__)
        cls.old = mod

    def test_every_non_financial_regime_scores_BIT_IDENTICALLY(self):
        if self.old is None:
            self.skipTest("the pre-change scorer is not reachable from git (already landed)")
        cd = _insurer(invested_capital=1110.0)
        for regime in ("mature", "growth", "hypergrowth", "cyclical"):
            with self.subTest(regime=regime):
                cls = _cls(regime, dcf_reliability="high", blended_growth=0.10,
                           is_cash_burning=False, rule_of_40=45.0)
                a = self.old.compute_score(cd, cls, 0.0955, 100.0, None, None)
                b = S.compute_score(cd, cls, 0.0955, 100.0, None, None, ke=0.0970)
                self.assertEqual(a.score, b.score)
                self.assertEqual(a.recommendation, b.recommendation)
                self.assertEqual(a.confidence, b.confidence)
                self.assertEqual(dict(a.subscores), dict(b.subscores))

    def test_the_FINANCIAL_regime_is_NOT_identical_so_the_control_is_not_vacuous(self):
        """If every regime matched, the inertness test would be passing by doing nothing."""
        if self.old is None:
            self.skipTest("the pre-change scorer is not reachable from git (already landed)")
        cd = _insurer(invested_capital=1110.0)
        cls = _cls("financial", dcf_reliability="high", blended_growth=0.10)
        a = self.old.compute_score(cd, cls, 0.0955, 100.0, None, None)
        b = S.compute_score(cd, cls, 0.0955, 100.0, None, None, ke=0.0970)
        self.assertNotEqual(dict(a.subscores)["health"], dict(b.subscores)["health"])


class TestTheCallSitePassesTheCostOfEquity(unittest.TestCase):
    """THE HELPER BEING RIGHT IS NOT THE PRODUCT BEING RIGHT.

    Every test above calls `compute_score` directly, so replacing the pipeline's
    `ke=wacc.cost_of_equity` with `ke=None` left all of them green (mutation f8, MISSED) while
    every financial silently lost its hurdle and fell back to raw ROE. This is the third time
    this session that a helper was tested and its call site was not.
    """

    def test_the_pipeline_passes_ke_from_the_SAME_wacc_object_the_fair_value_uses(self):
        src = io.open(os.path.join(REPO, "valuation/engine/pipeline.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "compute_score"]
        self.assertEqual(len(calls), 1, "expected exactly one call site")
        kw = {k.arg: k.value for k in calls[0].keywords}
        self.assertIn("ke", kw, "the call site no longer passes a cost of equity")
        v = kw["ke"]
        self.assertIsInstance(v, ast.Attribute, "ke is not read off an object")
        self.assertEqual(v.attr, "cost_of_equity")
        self.assertEqual(getattr(v.value, "id", None), "wacc",
                         "ke is not the SAME wacc object the P/B-ROE fair value is built on")


class TestNoVintageOpens(unittest.TestCase):
    """THE OPPORTUNITY SCORE IS NOT AN INPUT TO ANYTHING THE VINTAGE RULE BINDS."""

    def test_the_hot_list_composite_is_built_from_THEME_Z_SCORES_not_from_this_score(self):
        src = io.open(os.path.join(REPO, "valuation/screener/screen.py"),
                      encoding="utf-8").read()
        self.assertIn('scored["hot_score"] = scored["composite"].rank', src)
        self.assertNotIn("compute_score", src,
                         "the screener now reads the opportunity score -- a change here would "
                         "be a VINTAGE EVENT and this test must be re-decided, not deleted")

    def test_the_index_ranks_on_hot_score(self):
        src = io.open(os.path.join(REPO, "valuation/edge/valquo_index.py"),
                      encoding="utf-8").read()
        self.assertIn("hot_score", src)
        self.assertNotIn("compute_score", src)

    def test_the_forward_track_scores_picks_from_PRICES_only(self):
        src = io.open(os.path.join(REPO, "valuation/edge/track.py"), encoding="utf-8").read()
        self.assertNotIn("compute_score", src)
        self.assertNotIn("subscores", src)

    def test_the_only_caller_of_compute_score_is_the_valuation_pipeline(self):
        """Measured across the tree rather than asserted, so a second caller appearing in a
        surface the vintage rule DOES bind cannot land quietly."""
        callers = set()
        for root, _dirs, files in os.walk(os.path.join(REPO, "valuation")):
            for f in files:
                if not f.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(root, f), REPO).replace("\\", "/")
                if rel == "valuation/engine/scoring.py":
                    continue
                body = io.open(os.path.join(root, f), encoding="utf-8").read()
                for node in ast.walk(ast.parse(body)):
                    if isinstance(node, ast.Call) and \
                            getattr(node.func, "id", None) == "compute_score":
                        callers.add(rel)
        self.assertEqual(callers, {"valuation/engine/pipeline.py"},
                         "compute_score gained a caller: %s" % sorted(callers))


if __name__ == "__main__":
    unittest.main(verbosity=1)
