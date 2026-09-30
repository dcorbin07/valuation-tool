"""
THE HOT LIST VALUED BANKS AND INSURERS WITH INDUSTRIAL LENSES.

`/api/hotstocks`, scan 2026-09-29: **23 Financial Services rows, methods `dcf` / `blended` /
`multiples`, not one P/B-ROE.** `fairvalue._growth_value` projects revenue to
`SECTOR_TARGET_MARGIN` — a target OPERATING margin — which `classify.py` refuses outright for a
financial ("unlevered FCF DCF is unreliable; debt is raw material"). The published gaps were not
marginal:

    ALL  $729 vs $253      TRV  $753 vs $369
    EG   $972 vs $375      MKL  $3,547 vs $1,740

**NO VINTAGE OPENS**, and it is pinned below: `hot_score` is computed from the theme composite
at `screen.py:344` and `estimate_fair_values` runs afterwards, so the score cannot read the
number being changed.

Run:  python -m pytest tests/test_hotlist_financial_fv.py
      python tests/test_hotlist_financial_fv.py
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402

from valuation.screener import fairvalue as FV                          # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fin(**kw):
    row = {"ticker": "ALL", "sector": "Financial Services", "price": 253.0,
           "book_to_price": 0.45, "roe": 0.18}
    row.update(kw)
    return row


class TestTheFinancialLens(unittest.TestCase):

    def test_a_financial_row_is_valued_by_PB_ROE_and_SAYS_so(self):
        rows = [_fin()]
        FV.estimate_fair_values(rows, peer_rows=rows)
        self.assertEqual(rows[0]["fair_value_method"], "pb_roe")
        self.assertIsNotNone(rows[0]["fair_value"])

    def test_the_published_gap_CLOSES_rather_than_merely_changing(self):
        """The point is not that the number moves — it is that it stops being absurd. ALL was
        published at $729 against a $253 price, a 188% upside on an insurer."""
        rows = [_fin()]
        FV.estimate_fair_values(rows, peer_rows=rows)
        fv = rows[0]["fair_value"]
        self.assertLess(fv, 253.0 * 2.0, "the financial lens still implies a >100% upside")
        self.assertGreater(fv, 253.0 * 0.3, "the financial lens collapsed to nearly nothing")

    def test_a_financial_is_NEVER_BLENDED_with_the_industrial_lenses(self):
        """Blending a model the regime REFUSES with one it accepts still publishes a number the
        refused model moved. The row carries revenue and margins precisely so that a blend
        WOULD be reachable if the branch were not exclusive."""
        rows = [_fin(revenue=50000.0, gross_margin=0.30, op_margin=0.12,
                     ev_sales=1.2, ev_ebitda=9.0, pe=11.0, revenue_growth=0.08)]
        FV.estimate_fair_values(rows, peer_rows=rows)
        self.assertEqual(rows[0]["fair_value_method"], "pb_roe")

    def test_MISSING_book_or_ROE_is_WITHHELD_with_a_label_not_fallen_back(self):
        """Falling back to the industrial lenses on missing inputs would reinstate the defect
        for exactly the names whose data is thinnest."""
        for missing in ("book_to_price", "roe"):
            with self.subTest(missing=missing):
                rows = [_fin(revenue=50000.0, ev_sales=1.2, pe=11.0, **{missing: None})]
                FV.estimate_fair_values(rows, peer_rows=rows)
                self.assertEqual(rows[0]["fair_value_method"], "withheld_financial_inputs")
                self.assertIsNone(rows[0].get("fair_value"))
                self.assertIn("does not apply", rows[0]["fair_value_note"])

    def test_a_NON_financial_row_is_UNTOUCHED_by_this_change(self):
        """The inertness control. Without it, 'financials use P/B-ROE' would be satisfied by a
        function that routed everything there."""
        rows = [{"ticker": "AAPL", "sector": "Technology", "price": 200.0,
                 "book_to_price": 0.05, "roe": 1.5, "pe": 30.0, "revenue": 400000.0,
                 "ev_ebitda": 22.0, "op_margin": 0.30, "revenue_growth": 0.06}]
        FV.estimate_fair_values(rows, peer_rows=rows)
        self.assertNotEqual(rows[0].get("fair_value_method"), "pb_roe")

    def test_an_EXISTING_dcf_still_wins_for_a_financial(self):
        """A row that already carries a published pipeline valuation must keep it — otherwise
        the hot list would silently overwrite the stock page's own answer with an approximation
        that uses a beta of 1."""
        rows = [_fin(fair_value=291.0)]
        FV.estimate_fair_values(rows, peer_rows=rows)
        self.assertEqual(rows[0]["fair_value"], 291.0)
        self.assertEqual(rows[0]["fair_value_method"], "dcf")


class TestItDelegatesRatherThanReDerives(unittest.TestCase):

    def test_the_lens_CALLS_the_engine_and_does_not_restate_the_formula(self):
        """B7. `financial_fair_value` caps `g` below BOTH `ke` and the ROE and bounds the
        multiple; a second copy here would produce a number the stock page cannot reach."""
        src = io.open(os.path.join(REPO, "valuation/screener/fairvalue.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_financial_value")
        calls = {getattr(c.func, "id", None) for c in ast.walk(fn) if isinstance(c, ast.Call)}
        self.assertIn("financial_fair_value", calls, "the lens no longer delegates")
        self.assertNotIn("justified_pb", calls,
                         "the lens reaches past the engine's own capping into the raw formula")

    def test_it_matches_the_engine_CALLED_DIRECTLY_on_the_same_inputs(self):
        """Delegation proved by SUBSTITUTION rather than by reading the import."""
        from valuation.engine.financials import financial_fair_value
        from valuation.data.models import CompanyData
        from valuation.config import CONFIG
        rf = float(getattr(CONFIG, "risk_free_rate", None) or 0.04)
        erp = float(getattr(CONFIG, "equity_risk_premium", None) or 0.05)
        bvps = 0.45 * 253.0
        cd = CompanyData(ticker="ALL")
        cd.total_equity, cd.shares_diluted, cd.net_income = bvps, 1.0, 0.18 * bvps
        want = financial_fair_value(cd, rf + erp, min(rf, 0.025))
        got, _ke = FV._financial_value(_fin(), 253.0)
        self.assertAlmostEqual(got, want, places=9)

    def test_only_the_RATIO_of_equity_to_shares_is_used_so_the_stub_is_legitimate(self):
        """The scan has no share count, so the engine is handed an equity/share pair that
        reproduces BVPS rather than the real totals. That is only sound if the function uses
        their ratio — asserted, not assumed."""
        from valuation.engine.financials import financial_fair_value
        from valuation.data.models import CompanyData

        def mk(eq, sh):
            cd = CompanyData(ticker="X")
            cd.total_equity, cd.shares_diluted = eq, sh
            cd.net_income = 0.18 * eq
            return cd
        a = financial_fair_value(mk(113.85, 1.0), 0.09, 0.025)
        b = financial_fair_value(mk(113850.0, 1000.0), 0.09, 0.025)
        self.assertAlmostEqual(a, b, places=9)


class TestNoVintageOpens(unittest.TestCase):

    def test_the_hot_score_is_computed_BEFORE_any_fair_value_exists(self):
        """`hot_score` ranks the theme composite; `estimate_fair_values` runs afterwards and
        only fills a display field. Asserted by ORDER in the source, because "it does not read
        it" is a property of the sequence, not of a name."""
        src = io.open(os.path.join(REPO, "valuation/screener/screen.py"),
                      encoding="utf-8").read()
        i_score = src.index('scored["hot_score"] = scored["composite"].rank')
        i_fv = src.index("estimate_fair_values")
        self.assertLess(i_score, i_fv,
                        "fair value is now computed before the hot score - a change there "
                        "WOULD be a vintage event and this test must be re-decided")

    def test_the_composite_does_not_reference_fair_value_at_all(self):
        src = io.open(os.path.join(REPO, "valuation/screener/screen.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_decompose")
        names = {getattr(n, "id", None) for n in ast.walk(fn)}
        consts = {n.value for n in ast.walk(fn)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertNotIn("fair_value", names | consts)


if __name__ == "__main__":
    unittest.main(verbosity=1)
