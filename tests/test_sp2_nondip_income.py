"""F-4 / F-10's non-dip income - what these tests pin, and why each one exists.

Zero trials, no register, no hypothesis. `K3` is the predecessor's pre-committed arithmetic,
imported. So the risk here is not a wrong verdict; it is a number quoted about the wrong
object.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **EACH BOOK IS MEASURED AT ITS OWN DECLARED TENOR, READ FROM ITS DECLARATION.** `K3`'s
   income is `premium_fraction x 252/dte`, so the tenor is half the denominator. My first cut
   measured both books at `SELL-PREMIUM-2`'s 37-DTE median and would have reported **0.89
   years of headroom for F-10 where the truth is 0.14** - a six-fold overstatement in the
   flattering direction. The tenors are READ, never retyped (`MA5`), so a declaration that
   changes its tenor cannot leave this measuring the old one.

2. **THE PREMIUM FRACTION IS RE-MEASURED AT THE TENOR, NEVER RESCALED.** Holding the fraction
   fixed and changing only `turns` invents income, because a longer-dated put collects more
   premium. Pinned by requiring the two bands to carry DIFFERENT measured premium fractions on
   the real picks - a rescaling would make them identical.

3. **`K3` IS IMPORTED, NOT REIMPLEMENTED** (`B7`). A second crash arithmetic at the one place
   two retired books are judged would be unrecoverable.

4. **TOO FEW PICKS IS NOT A FIRED GATE** (`MB3`'s separation of reasons). A tenor band with no
   rows must say so rather than return a verdict.

5. **THE ARTIFACT SAYS WHAT POPULATION IT MEASURED.** The whole item is an `MB8` hazard: these
   are random-day entries in the DIP book's universe, not F-4's event-free set nor F-10's
   published book, and an artifact that omitted that could be quoted as either.

    python tests/test_sp2_nondip_income.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import dipcall as D  # noqa: E402

_SKIPS = []


def _art(name):
    p = D.out_path(name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


class TestTheTenorIsEachBooksOwn(unittest.TestCase):
    """(1). The correction that changed the answer."""

    def test_the_declared_tenors_are_read_from_the_declarations(self):
        from scripts.sp2_nondip_tenor import declared_dte
        self.assertEqual(declared_dte("f4_eventfree_premium"), 30)
        self.assertEqual(declared_dte("f10_clean_csp"), 52)

    def test_the_two_books_are_not_measured_at_the_same_tenor(self):
        a = _art("SP2_NONDIP_TENOR.json")
        if a is None:
            _SKIPS.append("tenor artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        self.assertNotEqual(a["declared_dte"]["f4_eventfree_premium"],
                            a["declared_dte"]["f10_clean_csp"])

    def test_f10s_build_cell_is_reported_as_the_knife_edge_it_is(self):
        a = _art("SP2_NONDIP_TENOR.json")
        if a is None:
            _SKIPS.append("tenor artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        cell = a["stages"]["build_2016_2019_half0"]["f10_clean_csp"]["k3"]
        self.assertTrue(cell["pass"])
        headroom = cell["bar"] - cell["worst_years_of_premium"]
        self.assertLess(headroom, 0.5,
                        "if this stops being a knife edge the record above is stale and "
                        "should be restated rather than quietly improved")
        self.assertGreater(headroom, 0.0)


class TestThePremiumIsMeasuredNotRescaled(unittest.TestCase):
    """(2). A rescaling would make the two bands identical."""

    def test_the_two_tenor_bands_carry_different_measured_premium_fractions(self):
        a = _art("SP2_NONDIP_TENOR.json")
        if a is None:
            _SKIPS.append("tenor artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        st = a["stages"]["build_2016_2019_half0"]
        p4 = st["f4_eventfree_premium"]["k3"]["median_premium_frac_of_strike"]
        p10 = st["f10_clean_csp"]["k3"]["median_premium_frac_of_strike"]
        self.assertNotAlmostEqual(p4, p10, places=5,
                                  msg="a longer-dated put collects MORE premium; equal "
                                      "fractions would mean the income was rescaled from one "
                                      "band rather than measured on the other")
        self.assertGreater(p10, p4, "52 DTE must collect more of the strike than 30 DTE")


class TestK3IsImported(unittest.TestCase):
    """(3). From the syntax tree, not a grep."""

    def test_neither_script_defines_its_own_crash_arithmetic(self):
        import ast
        for name in ("sp2_nondip_income.py", "sp2_nondip_tenor.py"):
            with io.open(os.path.join(REPO, "scripts", name), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            imported = set()
            for n in ast.walk(tree):
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    if isinstance(n, ast.ImportFrom) and n.module:
                        imported.add(n.module.split(".")[-1])
                    for al in n.names:
                        imported.add(al.name.split(".")[-1])
            self.assertIn("sellpremium2_kills", imported, name)
            defined = {d.name for d in ast.walk(tree) if isinstance(d, ast.FunctionDef)}
            self.assertNotIn("k3_from_picks", defined, name)
            self.assertNotIn("years_of_premium", defined, name)


class TestTooFewPicksIsNotAFiredGate(unittest.TestCase):
    """(4). `MB3`'s separation of reasons."""

    def test_a_thin_tenor_band_reports_NOT_MEASURED_rather_than_a_verdict(self):
        import pandas as pd
        from scripts import sp2_nondip_tenor as T
        self.assertGreaterEqual(T.MIN_PICKS, 1)
        # the shape the script emits for a thin band carries no k3 key at all
        a = _art("SP2_NONDIP_TENOR.json")
        if a is None:
            _SKIPS.append("tenor artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        for stage in a["stages"].values():
            for book in ("f4_eventfree_premium", "f10_clean_csp"):
                cell = stage.get(book)
                if isinstance(cell, dict) and "k3" not in cell:
                    self.assertIn("NOT a measurement", cell.get("verdict", ""))
        del pd


class TestTheArtifactNamesItsPopulation(unittest.TestCase):
    """(5). The `MB8` hazard, written into the artifact rather than only the handoff."""

    def test_both_artifacts_say_whose_names_these_are(self):
        for name in ("SP2_NONDIP_INCOME.json", "SP2_NONDIP_TENOR.json"):
            a = _art(name)
            if a is None:
                _SKIPS.append("%s absent (licensed data); not a pass" % name)
                continue
            # STRUCTURAL, not phrase-matching. The first cut of this test asserted the
            # literal "random days" and FAILED against a correct artifact that says
            # "ordinary days" -- the substring family, in the assert-present direction.
            # What matters is that a DEDICATED caveat field exists and names BOTH books as
            # not-this, so a reader of either file alone cannot quote it as either book's own.
            caveat = " ".join(str(a.get(k, "")) for k in
                              ("caveat", "what_this_is_not", "what_this_is")).lower()
            self.assertTrue(caveat.strip(), "%s carries no population caveat at all" % name)
            self.assertIn("f-4", caveat)
            self.assertIn("f-10", caveat)
            self.assertIn("not", caveat)
            self.assertEqual(a["trials"], 0, "a control charges nothing (MB1-SEL)")


class TestTheNonDipAnswer(unittest.TestCase):
    """The verdict as measured, so a later edit to the record shows up here."""

    def test_both_books_clear_in_both_quadrants(self):
        a = _art("SP2_NONDIP_TENOR.json")
        if a is None:
            _SKIPS.append("tenor artifact absent (licensed data); not a pass")
            self.skipTest("artifact absent")
        for book in ("f4_eventfree_premium", "f10_clean_csp"):
            v = a["verdicts"][book]
            self.assertEqual(v["measured_quadrants"], 2)
            self.assertTrue(v["clears_everywhere"])

    def test_the_bar_is_the_predecessors_unrelaxed_6_point_0(self):
        from valuation.studies import sellpremium as SP
        self.assertEqual(SP.K3_MAX_YEARS_OF_PREMIUM, 6.0)
        a = _art("SP2_NONDIP_TENOR.json")
        if a is not None:
            self.assertEqual(a["bar"], 6.0)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
