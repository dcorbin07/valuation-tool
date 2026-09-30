"""
CLOSING THE FREE ROUTE'S MEASURED GAPS, DELEGATING TO THE PANEL'S OWN DEFINITIONS.

`D9-FIDELITY` read **NO-GO on all three bars** and `D9-DIAG` located why. Two of the gaps are
closed here; the rest are scoped in the handoff rather than half-built.

**(a) THE PIOTROSKI F-SCORE — the live side did not compute it at all.** The panel's `quality`
theme averages it with nine other inputs, so a live `quality` without it is a mean over a
different set of columns. That is one reason B3 read `quality` **0.6256** against a 0.70 bar
while `value`, `momentum` and `size` cleared at 0.79, 0.97 and 0.98.

**(d) THE INDEX BUILD'S WEIGHTS — and D9's framing of this is measurably wrong.**
`attribution._branch` divides every contribution by `sum(present * w)`, so **multiplying all
weights by a constant changes nothing**: `1/7` and the live `0.125` are the same object, and
"flat 1/7 against bucket-specific weights" is *not* a scaling difference. What actually differs
is **membership** (established blends `quality`, speculative blends `growth`, at the same weight)
and **soft bucketing** (a borderline name is scored under both rulebooks and blended).

Run:  python -m pytest tests/test_free_route_parity.py
      python tests/test_free_route_parity.py
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402

from valuation.data import fscore_live as FS                            # noqa: E402
from valuation.edge.valquo_index import FLAT_SEVEN, rescore_flat_seven   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _facts(rows_by_concept):
    """A minimal companyfacts shape: {concept: {fy: value}} -> SEC's nested form."""
    gaap = {}
    for concept, per_year in rows_by_concept.items():
        gaap[concept] = {"units": {"USD": [
            {"fy": fy, "fp": "FY", "form": "10-K", "val": v}
            for fy, v in per_year.items()]}}
    return {"facts": {"us-gaap": gaap}}


def _two_years(**over):
    base = {
        "Assets": {2024: 1000.0, 2025: 1100.0},
        "NetIncomeLoss": {2024: 80.0, 2025: 120.0},
        "NetCashProvidedByUsedInOperatingActivities": {2024: 140.0, 2025: 190.0},
        "LongTermDebtNoncurrent": {2024: 300.0, 2025: 280.0},
        "AssetsCurrent": {2024: 400.0, 2025: 460.0},
        "LiabilitiesCurrent": {2024: 250.0, 2025: 260.0},
        "WeightedAverageNumberOfDilutedSharesOutstanding": {2024: 100.0, 2025: 99.0},
        "Revenues": {2024: 900.0, 2025: 1050.0},
        "CostOfRevenue": {2024: 600.0, 2025: 670.0},
    }
    base.update(over)
    return _facts(base)


class TestTheLiveFScore(unittest.TestCase):

    def test_it_DELEGATES_to_the_panels_own_function(self):
        """B7, and here it is load-bearing in an unusual way: the F-score is the number the two
        sides are COMPARED on, so a second implementation would make any fidelity measurement a
        comparison between two of my own functions rather than between two vendors."""
        src = io.open(os.path.join(REPO, "valuation/data/fscore_live.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        imported = {a.name for n in ast.walk(tree)
                    if isinstance(n, ast.ImportFrom) for a in n.names}
        self.assertIn("_f_score", imported, "the live F-score no longer delegates")
        # And it does not restate the nine tests: the panel's own floor phrase is absent here.
        self.assertNotIn("Piotroski F-Score (0-9) from two point-in-time", src)

    def test_a_healthy_two_year_pair_scores_HIGH_and_says_its_source(self):
        s, src = FS._rows_from_facts(_two_years())
        from valuation.edge.fundamental_panel import _f_score
        got = _f_score(s, src)
        self.assertIsNotNone(got)
        self.assertGreaterEqual(got, 7, "a clearly improving company scored low: %s" % got)

    def test_a_DETERIORATING_pair_scores_LOWER_so_the_score_is_not_a_constant(self):
        bad = _two_years(
            NetIncomeLoss={2024: 120.0, 2025: -40.0},
            NetCashProvidedByUsedInOperatingActivities={2024: 190.0, 2025: -10.0},
            LongTermDebtNoncurrent={2024: 280.0, 2025: 460.0},
            AssetsCurrent={2024: 460.0, 2025: 300.0},
            WeightedAverageNumberOfDilutedSharesOutstanding={2024: 99.0, 2025: 140.0},
            CostOfRevenue={2024: 600.0, 2025: 900.0})
        from valuation.edge.fundamental_panel import _f_score
        a, b = FS._rows_from_facts(_two_years())
        c, d = FS._rows_from_facts(bad)
        self.assertGreater(_f_score(a, b), _f_score(c, d))

    def test_NON_CONSECUTIVE_years_are_REFUSED_not_compared(self):
        """Seven of the nine tests read "improved since last year". Comparing 2025 against 2022
        answers a different question and the score would look like a real one."""
        gap = _two_years()
        gap["facts"]["us-gaap"]["Assets"]["units"]["USD"] = [
            {"fy": 2021, "fp": "FY", "form": "10-K", "val": 900.0},
            {"fy": 2025, "fp": "FY", "form": "10-K", "val": 1100.0}]
        cur, prior = FS._rows_from_facts(gap)
        self.assertIsNone(cur)
        self.assertIsNone(prior)

    def test_a_SINGLE_year_is_REFUSED(self):
        one = _facts({"Assets": {2025: 1000.0}, "NetIncomeLoss": {2025: 50.0}})
        self.assertEqual(FS._rows_from_facts(one), (None, None))

    def test_only_ANNUAL_10K_facts_are_read(self):
        """Quarterly entries carry `fp` Q1..Q4. Mixing a quarter into an annual pair would
        compare a quarter's assets to a year's and every ratio would be wrong."""
        mixed = _two_years()
        mixed["facts"]["us-gaap"]["Assets"]["units"]["USD"].append(
            {"fy": 2025, "fp": "Q3", "form": "10-Q", "val": 99999.0})
        cur, _ = FS._rows_from_facts(mixed)
        self.assertEqual(cur["assets"], 1100.0, "a quarterly fact reached the annual row")

    def test_the_DERIVED_fields_are_built_the_SAME_WAY_for_both_years(self):
        """Tests 6 and 8 compare `currentratio` and `grossmargin` across the two years. A
        definition that drifted between them would fabricate a pass."""
        cur, prior = FS._rows_from_facts(_two_years())
        self.assertAlmostEqual(cur["currentratio"], 460.0 / 260.0, places=9)
        self.assertAlmostEqual(prior["currentratio"], 400.0 / 250.0, places=9)
        self.assertAlmostEqual(cur["grossmargin"], (1050.0 - 670.0) / 1050.0, places=9)
        self.assertAlmostEqual(prior["grossmargin"], (900.0 - 600.0) / 900.0, places=9)

    def test_a_FAILURE_returns_None_with_a_REASON_never_a_low_score(self):
        """A thin row must not masquerade as a genuinely weak company -- the panel's own floor,
        and it matters more here because the live feed's coverage is what is being measured.

        BOTH FAILURE ROUTES, because an earlier cut exercised only the import one and returned
        before the scoring branch ever ran -- so "a failure returns None" was true of a path
        that never reached the code it was asserting about (mutation a6, MISSED).
        """
        class _Cfg:
            sec_user_agent = "t@e.com"

        # Route 1: the fetch itself fails.
        real = FS.edgar if hasattr(FS, "edgar") else None
        FS.edgar = None
        try:
            got, why = FS.f_score("ZZZZ", _Cfg())
        finally:
            if real is not None:
                FS.edgar = real
        self.assertIsNone(got)
        self.assertTrue(why, "a failure returned no reason")

        # Route 2: THE FETCH SUCCEEDS and `_f_score` declines the pair -- fewer than six
        # evaluable tests. It must come back None with a reason, NOT a zero.
        #
        # THIS HAS TO GO THROUGH `f_score`, NOT `_f_score`. An earlier cut asserted on the panel
        # function directly, which never touches the return path being protected -- so making
        # that path hand back a 0 instead of None left the test green (mutation a6, MISSED).
        # A test one call short of the code it protects protects nothing.
        import types
        import requests as _rq
        thin = _facts({"Assets": {2024: 1000.0, 2025: 1100.0}})

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return thin

        fake_edgar = types.SimpleNamespace(
            resolve_cik=lambda t, c: 320193,
            _FACTS_URL="https://example.invalid/{cik:010d}.json",
            _headers=lambda c: {})
        real_edgar = getattr(FS, "edgar", None)
        real_get = _rq.get
        try:
            FS.edgar = fake_edgar
            _rq.get = lambda *a, **k: _Resp()
            got2, why2 = FS.f_score("AAPL", _Cfg())
        finally:
            _rq.get = real_get
            if real_edgar is not None:
                FS.edgar = real_edgar
        self.assertIsNone(got2, "a declining pair returned a score: %r" % (got2,))
        self.assertTrue(why2, "a declining pair returned no reason")


class TestTheIndexBuildsWeights(unittest.TestCase):

    def test_the_seven_are_the_DEPLOYED_seven_and_growth_is_NOT_among_them(self):
        """`growth` carries zero weight in the deployed composite the record was built on."""
        self.assertEqual(len(FLAT_SEVEN), 7)
        self.assertNotIn("growth", FLAT_SEVEN)
        self.assertNotIn("low_risk", FLAT_SEVEN)
        self.assertNotIn("sentiment", FLAT_SEVEN)
        self.assertAlmostEqual(sum(FLAT_SEVEN.values()), 1.0, places=12)

    def test_SCALING_every_weight_changes_NOTHING_which_is_why_1_7_vs_0_125_is_not_the_gap(self):
        """THE MEASURED CORRECTION TO D9'S FRAMING. `_branch` divides by `sum(present * w)`, so
        a common factor cancels exactly. If this ever stopped holding, "flat 1/7" would become a
        real difference and (d) would need re-deciding rather than re-running."""
        import pandas as pd
        from valuation.screener.attribution import decompose
        df = pd.DataFrame(
            {"value": [1.0, -1.0, 0.2], "quality": [0.5, -0.5, 0.9],
             "momentum": [0.2, 0.1, -0.4], "insider": [0.0, 0.0, 0.1],
             "capital_discipline": [0.1, -0.1, 0.6], "size": [0.3, -0.3, 0.0],
             "institutional": [0.4, -0.4, 0.2], "bucket": ["established"] * 3},
            index=["A", "B", "C"])
        one_seventh = dict(FLAT_SEVEN)
        eighth = {k: 0.125 for k in FLAT_SEVEN}
        a, _ = decompose(df, one_seventh, one_seventh, soft=False)
        b, _ = decompose(df, eighth, eighth, soft=False)
        for t in df.index:
            self.assertAlmostEqual(a[t], b[t], places=12,
                                   msg="rescaling the weights moved %s" % t)

    def test_the_rescore_DELEGATES_to_the_same_decompose_the_screener_uses(self):
        src = io.open(os.path.join(REPO, "valuation/edge/valquo_index.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "rescore_flat_seven")
        calls = {getattr(c.func, "id", None) for c in ast.walk(fn) if isinstance(c, ast.Call)}
        self.assertIn("decompose", calls, "the rescorer no longer delegates")

    def test_it_TURNS_OFF_the_bucket_switch_which_is_what_actually_differs(self):
        """A name whose bucket score is carried by `growth` must fall, because `growth` is not
        in the deployed blend. Without this the change would be indistinguishable from a
        rescaling, which is exactly the thing measured to be inert."""
        rows = [
            {"ticker": "GROWTHY", "hot_score": 90.0, "factors": {
                "value": -1.0, "quality": -0.5, "momentum": 0.1, "insider": 0.0,
                "capital_discipline": -0.1, "size": -0.3, "institutional": -0.4,
                "growth": 3.0}},
            {"ticker": "SOLID", "hot_score": 50.0, "factors": {
                "value": 1.0, "quality": 0.5, "momentum": 0.2, "insider": 0.0,
                "capital_discipline": 0.1, "size": 0.3, "institutional": 0.4,
                "growth": -2.0}},
        ]
        rep = rescore_flat_seven(rows)
        self.assertTrue(rep["rescored"])
        by = {r["ticker"]: r["hot_score"] for r in rows}
        self.assertGreater(by["SOLID"], by["GROWTHY"],
                           "the growth-carried name still outranks the deployed-seven one")

    def test_every_rescored_row_SAYS_which_basis_it_is_on(self):
        rows = [{"ticker": t, "hot_score": 1.0,
                 "factors": {k: v for k in FLAT_SEVEN}}
                for t, v in (("A", 0.1), ("B", 0.9), ("C", -0.4))]
        rescore_flat_seven(rows)
        for r in rows:
            self.assertEqual(r["hot_score_basis"], "flat_seven")

    def test_IDENTICAL_names_cannot_be_RANKED_APART(self):
        """A CORRECTION TO MY OWN FIRST ASSERTION, which claimed a degenerate cross-section
        keeps its old score. It does not -- three identical rows all score 67.0, because
        `standardize_factors` returns the same z for each and `rank(pct=True)` ties them. That
        is the RIGHT behaviour and the wrong test: what matters is that no fabricated ORDERING
        appears, not that the old number survives. Pinned as the property it actually has.
        """
        rows = [{"ticker": t, "hot_score": 42.0,
                 "factors": {k: 0.1 for k in FLAT_SEVEN}} for t in ("A", "B", "C")]
        rescore_flat_seven(rows)
        scores = {r["hot_score"] for r in rows}
        self.assertEqual(len(scores), 1,
                         "identical names were ranked apart: %s" % sorted(scores))

    def test_rows_with_NO_factors_are_reported_not_silently_left(self):
        rep = rescore_flat_seven([{"ticker": "A", "hot_score": 1.0}])
        self.assertFalse(rep["rescored"])
        self.assertIn("factors", rep["reason"])

    def _wide(self):
        """TEN names, split five/five, carrying `value_est` and `value_spec`.

        BOTH DETAILS ARE LOAD-BEARING AND MUTATION PROVED IT. `decompose`'s hard split
        standardises WITHIN a bucket only at five or more names in it (below that it falls back
        to the whole cross-section), and the SOFT branch only engages when `value_est` and
        `value_spec` are both present. A three-row fixture without them cannot reach either, so
        leaving the bucket switch on and leaving soft bucketing on were both **inert** against
        it -- mutations d2 and d3, MISSED. A fixture that cannot reach the defect proves nothing.
        """
        rows = []
        for i in range(10):
            f = {k: (i - 4.5) / 5.0 for k in FLAT_SEVEN}
            f["growth"] = (4.5 - i) / 5.0          # anti-correlated, so membership matters
            f["value_est"] = (i - 4.5) / 5.0
            f["value_spec"] = (4.5 - i) / 5.0      # so soft blending is NOT a no-op
            rows.append({"ticker": "T%02d" % i, "hot_score": float(i + 1), "factors": f})
        return rows

    def test_the_index_ranking_is_INDEPENDENT_of_the_live_bucket_split(self):
        """The book must not inherit which rulebook a name happened to fall under. Exercised on
        a five/five split so within-bucket standardisation is actually reachable."""
        import pandas as pd
        from valuation.screener.attribution import decompose
        rows = self._wide()
        df = pd.DataFrame([r["factors"] for r in rows],
                          index=[r["ticker"] for r in rows])
        one = df.copy()
        one["bucket"] = "established"
        split = df.copy()
        split["bucket"] = ["established"] * 5 + ["speculative"] * 5
        a, _ = decompose(one, FLAT_SEVEN, FLAT_SEVEN, soft=False)
        b, _ = decompose(split, FLAT_SEVEN, FLAT_SEVEN, soft=False)
        self.assertFalse(a.equals(b),
                         "the five/five fixture does not reach within-bucket standardisation, "
                         "so this test cannot see the bucket switch at all")
        rescore_flat_seven(rows)
        got = [r["hot_score"] for r in rows]
        want = list((a.rank(pct=True) * 99 + 1).reindex([r["ticker"] for r in rows]))
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=9,
                                   msg="the index ranking is not the ONE-rulebook ranking")

    def test_SOFT_bucketing_is_OFF_for_the_index_build(self):
        """ASSERTED STRUCTURALLY, AND THE REASON IS A LIMIT WORTH STATING.

        `soft=True` engages `p_established`, which reads **`op_margin`** -- a column the row's
        `factors` dict does not carry, because `factors` holds THEME z-scores and `op_margin` is
        a raw metric. So a behavioural test built from `factors` alone cannot reach the soft
        branch at all: it raises rather than blending. Rather than ship a test that passes for
        the wrong reason, the property is read off the call: the rescorer passes `soft=False`.

        What that does NOT prove is what soft blending would have done to a real scan row, which
        does carry `op_margin`. That is a statement about a path the index build does not take.
        """
        src = io.open(os.path.join(REPO, "valuation/edge/valquo_index.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "rescore_flat_seven")
        calls = [c for c in ast.walk(fn)
                 if isinstance(c, ast.Call) and getattr(c.func, "id", None) == "decompose"]
        self.assertEqual(len(calls), 1, "expected exactly one decompose call")
        kw = {k.arg: k.value for k in calls[0].keywords}
        self.assertIn("soft", kw, "soft bucketing is left to its default (True)")
        self.assertIs(kw["soft"].value, False, "the index build is soft-bucketing")

    def test_the_HOT_LIST_score_is_NOT_changed_by_this(self):
        """`rescore_flat_seven` is for the INDEX BUILD only. The hot list keeps the score the
        site has always shown; changing that is a product decision, not a fidelity one."""
        src = io.open(os.path.join(REPO, "valuation/screener/screen.py"),
                      encoding="utf-8").read()
        self.assertNotIn("rescore_flat_seven", src,
                         "the screener now rescores -- that changes the PUBLIC hot list and is "
                         "a separate decision")


if __name__ == "__main__":
    unittest.main(verbosity=1)
