# -*- coding: utf-8 -*-
"""ITEM 25 — five ways the single-stock valuation answered confidently about the wrong thing.

EVERY NUMBER BELOW WAS READ OFF THE LIVE SERVICE ON 2026-10-03, so the fixtures are those
companies and not hypothetical ones.

| ticker | sector / industry | regime it got | fair value | price |
|---|---|---|---|---|
| O | Real Estate / `REIT - Retail` | **growth**, reliability **high** | $9.46 | $54.13 |
| PLD | Real Estate / `REIT - Industrial` | **mature**, reliability **high** | $20.39 | $128.91 |
| NEE | Utilities / `Utilities - Regulated Electric` | **growth**, **confidence high** | $15.89 | $76.83 |
| DUK | Utilities / `Utilities - Regulated Electric` | **mature** + "~0.1 yrs of runway" | $43.50 | $114.13 |
| TSLA | Consumer Cyclical / Auto Manufacturers | **mature** | $23.42 | $370.59 |
| MRNA | Healthcare / Biotechnology | **mature, "stable profile"** | $21.85 | $190.01 |
| BRK.B | '' / '' | **unknown**, price None | — | — |
| ZZZZQ | '' / '' | **unknown**, price None | — | — |

1. **THE REIT HINT WAS AN EM DASH.** `FINANCIAL_INDUSTRY_HINTS` carried `"reit—"` (U+2014)
   against live data reading `"REIT - Retail"` with a hyphen-minus, so it had NEVER matched.
   **A typographic character in a matcher is not a typo, it is a predicate that cannot fire** —
   and it fails SILENTLY, because the fall-through produces a confident number rather than an
   error. O's DCF came out at **$0.7455 a share carrying 75% of the blend**; a REIT's capex IS
   its business, so unlevered free cash flow after capex is near zero for a healthy company.

2. **REGULATED UTILITIES, TWO WRONG ANSWERS FROM ONE CAUSE.** NEE cleared the 0.10 growth bar
   (0.1045) and DUK did not (0.0469), so one got `growth` and the other `mature` — and DUK also
   got *"Cash-burning: ~0.1 yrs of runway at the current burn."* **A regulated utility reading
   as five weeks from insolvency is a category error**: its capex is rate-base investment the
   regulator allows a return on.

3. **`mature` IS THE DEFAULT BRANCH, so it asserts stability about everything the other tests
   declined.** MRNA at **−16.05%** revenue growth while burning cash was labelled *"Mature,
   stable profile"*. TSLA at **+7.84%**, FCF-positive and profitable, is a defensible `mature`
   and is deliberately NOT re-routed — its $23.42 comes from ROIC 5% against a **WACC of 14%**,
   which item 25 states plainly is the 5.28% Treasury and the model working as written.

4. **`BRK.B` AND `BRK-B` ARE THE SAME COMPANY** and only one of them worked.

5. **AND BOTH `BRK.B` AND A NONEXISTENT `ZZZZQ` RETURNED HTTP 200 WITH SCORE 40 AND
   "Reduce"** — the 40 being `health: 40.0` standing alone after the valuation was withheld and
   the weights renormalised. **One sub-score of a company nobody identified, rendered as a
   recommendation.** Every honest caveat downstream is about the VALUATION; none of them can
   say the company was not found.

WHAT THIS SUITE DOES NOT ASSERT
-------------------------------
Any fair value. The point of items 1 and 2 is that the engine should stop publishing an
intrinsic value it cannot compute, so pinning a NEW number would re-create the thing being
fixed one step along. What is pinned is WHICH LENS CARRIES WEIGHT, and that a refusal happens
when none can.
"""
import dataclasses
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.data.models import CompanyData                      # noqa: E402
from valuation.engine import classify as CL                        # noqa: E402
from valuation.engine.blend import blended_fair_value              # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cd(**kw):
    """A `CompanyData` with only the fields this suite needs, by name."""
    fields = {f.name for f in dataclasses.fields(CompanyData)}
    unknown = set(kw) - fields
    assert not unknown, "CompanyData has no such field(s): %r" % sorted(unknown)
    return CompanyData(**kw)


def company(ticker, sector, industry, growth, fcf=1.0e9):
    """Growth is set through `analyst_rev_growth_next`, which is a FIELD.

    `rev_cagr_3y` and `rev_growth_ttm` are read-only PROPERTIES computed from
    `revenue_history`, so passing them to the constructor raises -- which is how the first cut
    of this suite failed 26 tests for a reason that had nothing to do with its subject.
    `_blended_growth` takes the analyst figure at weight 0.5 and the other two at 0.3 and 0.2,
    so with only the analyst value present the blend IS that value exactly, which is the
    control this suite wants.
    """
    assert CL._PLAUSIBLE_GROWTH[0] <= growth <= CL._PLAUSIBLE_GROWTH[1], (
        "%r is outside the plausible band, so `_blended_growth` DISCARDS it and the fixture "
        "would be testing a None growth rather than the value it names" % growth)
    return cd(ticker=ticker, sector=sector, industry=industry,
              analyst_rev_growth_next=growth, fcf=fcf)


# ==========================================================================================
# 1. THE EM DASH
# ==========================================================================================
class TheReitHintCouldNotFire(unittest.TestCase):
    def test_the_old_hint_is_gone_from_the_financial_tuple(self):
        """A REIT is not a financial: routing it there hands it justified-P/B-from-ROE, which
        is a bank's model. It gets its own regime instead."""
        for h in CL.FINANCIAL_INDUSTRY_HINTS:
            self.assertNotIn("reit", h.lower())

    def test_no_matcher_in_this_module_contains_an_em_dash(self):
        """THE DEFECT CLASS, not just the instance. A typographic character in a predicate
        matched against vendor data cannot fire, and fails silently."""
        for name in ("FINANCIAL_INDUSTRY_HINTS", "REIT_INDUSTRY_HINTS",
                     "REGULATED_INDUSTRY_HINTS"):
            for h in getattr(CL, name):
                with self.subTest("%s: %r" % (name, h)):
                    self.assertNotIn("—", h, "em dash")
                    self.assertNotIn("–", h, "en dash")
                    self.assertNotIn("−", h, "minus sign")

    def test_the_live_industry_strings_match(self):
        """The two strings the service actually returned."""
        for ind in ("REIT - Retail", "REIT - Industrial"):
            self.assertTrue(any(h in ind.lower() for h in CL.REIT_INDUSTRY_HINTS), ind)

    def test_a_separator_is_not_required(self):
        """Requiring one is how the em dash came to be load-bearing: the hint was `reit` plus a
        dash, so the dash had to be right. These match on the word."""
        for ind in ("REIT—Diversified", "Reit Office", "REIT-Hotel",
                    "Real Estate Investment Trust"):
            self.assertTrue(any(h in ind.lower() for h in CL.REIT_INDUSTRY_HINTS), ind)

    def test_an_ordinary_company_is_not_caught(self):
        """The positive control. A word-substring rule has to be checked for over-reach."""
        for ind in ("Software - Infrastructure", "Auto Manufacturers", "Biotechnology",
                    "Insurance - Diversified", "Banks - Regional"):
            self.assertFalse(any(h in ind.lower() for h in CL.REIT_INDUSTRY_HINTS), ind)


# ==========================================================================================
# 1b + 2. THE TWO REGIMES
# ==========================================================================================
class TheTwoCapexIsTheBusinessRegimes(unittest.TestCase):
    """O and PLD landed in DIFFERENT regimes, and so did NEE and DUK, purely on which side of
    the 0.10 growth bar they fell. One cause, four wrong answers."""

    def test_both_reits_route_to_reit_regardless_of_growth(self):
        for t, ind, g in (("O", "REIT - Retail", 0.1116),
                          ("PLD", "REIT - Industrial", 0.0884)):
            c = CL.classify(company(t, "Real Estate", ind, g))
            self.assertEqual(c.regime, "reit", t)
            self.assertEqual(c.dcf_reliability, "low", t)

    def test_both_utilities_route_to_regulated_regardless_of_growth(self):
        for t, g in (("NEE", 0.1045), ("DUK", 0.0469)):
            c = CL.classify(company(t, "Utilities", "Utilities - Regulated Electric", g))
            self.assertEqual(c.regime, "regulated", t)
            self.assertEqual(c.dcf_reliability, "low", t)

    def test_the_sector_is_tested_BEFORE_the_growth_branches(self):
        """THE ORDERING IS THE FIX. A REIT growing at 40% is still a REIT, and testing the
        sector after the growth branches is exactly how O got `growth` and PLD got `mature`."""
        c = CL.classify(company("FAST-REIT", "Real Estate", "REIT - Retail", 0.40))
        self.assertEqual(c.regime, "reit")
        c = CL.classify(company("FAST-UTIL", "Utilities", "Utilities - Regulated Electric",
                                0.40))
        self.assertEqual(c.regime, "regulated")

    def test_the_reason_says_capex_is_the_business(self):
        c = CL.classify(company("O", "Real Estate", "REIT - Retail", 0.1116))
        joined = " ".join(c.reasons)
        self.assertIn("capex", joined.lower())
        self.assertIn("FFO", joined)

    def test_the_utility_reason_names_the_rate_base(self):
        c = CL.classify(company("DUK", "Utilities", "Utilities - Regulated Electric", 0.0469))
        self.assertIn("rate-base", " ".join(c.reasons))


class TheFcffLensIsRefusedNotDownWeighted(unittest.TestCase):
    """REFUSED, and that is the load-bearing choice: `DCF_QUALITY` at `low` is 0.35, which
    would still have left a $0.75 figure about a THIRD of the blend. "Unreliable" and
    "inapplicable" are different states and a weight vector can only express the first."""

    def _blend(self, ticker, sector, industry, growth, dcf, mult):
        c = company(ticker, sector, industry, growth)
        return c, CL.classify(c), blended_fair_value(
            c, CL.classify(c), dcf_per_share=dcf, comps_fair_value=mult, growth_value=None)

    def test_the_reit_blend_carries_multiples_alone(self):
        """O's real figures: a $0.7455 DCF that used to carry 75%, and a $35.62 comps value."""
        _, _, b = self._blend("O", "Real Estate", "REIT - Retail", 0.1116, 0.7455, 35.6214)
        self.assertEqual(set(b.lenses), {"multiples"})
        self.assertAlmostEqual(b.lenses["multiples"]["weight"], 1.0, places=9)
        self.assertAlmostEqual(b.value, 35.6214, places=4)

    def test_the_dcf_figure_does_not_reach_the_value_at_any_weight(self):
        """THE SHARPEST FORM: feed an absurd DCF and the blend must not move at all."""
        _, _, a = self._blend("O", "Real Estate", "REIT - Retail", 0.1116, 0.0001, 35.6214)
        _, _, b = self._blend("O", "Real Estate", "REIT - Retail", 0.1116, 9999.0, 35.6214)
        self.assertEqual(a.value, b.value)

    def test_the_utility_blend_carries_multiples_alone(self):
        _, _, b = self._blend("NEE", "Utilities", "Utilities - Regulated Electric",
                              0.1045, 2.0, 42.67)
        self.assertEqual(set(b.lenses), {"multiples"})

    def test_confidence_is_never_high(self):
        """NEE was published at `confidence: high`. The right lenses are not built here, so a
        multiples-only figure is the best available rather than a good one."""
        for t, sec, ind in (("O", "Real Estate", "REIT - Retail"),
                            ("NEE", "Utilities", "Utilities - Regulated Electric")):
            _, _, b = self._blend(t, sec, ind, 0.10, 1.0, 40.0)
            self.assertEqual(b.confidence, "low", t)

    def test_no_multiple_means_NOT_VALUABLE_rather_than_the_wrong_lens(self):
        """`UNKNOWN`'s principle one layer along: publishing nothing is a claim about our own
        knowledge, and publishing $9.46 is a claim about Realty Income."""
        _, _, b = self._blend("NOCOMPS", "Real Estate", "REIT - Office", 0.05, 0.90, None)
        self.assertFalse(b.valuable)
        self.assertIsNone(b.value)
        self.assertIn("capex is the business", b.reason)

    def test_the_method_string_says_which_lens(self):
        _, _, b = self._blend("O", "Real Estate", "REIT - Retail", 0.1116, 0.7455, 35.6214)
        self.assertEqual(b.method, "peer multiples")

    def test_an_ordinary_company_still_blends_the_dcf(self):
        """The positive control: this refusal must not have leaked into the default path."""
        _, cls, b = self._blend("MSFT", "Technology", "Software - Infrastructure",
                                0.12, 400.0, 380.0)
        self.assertNotIn(cls.regime, ("reit", "regulated"))
        self.assertIn("dcf", b.lenses)


class TheFcffDerivedSurfacesFollowAutomatically(unittest.TestCase):
    """`lens_applicability` READS the blend's weights, so it needed no change -- it was
    answering `fcff_applies: True` for a REIT only because the blend had given the DCF 75%."""

    def test_fcff_applies_is_False_for_a_reit(self):
        from valuation.engine.pipeline import lens_applicability
        c = company("O", "Real Estate", "REIT - Retail", 0.1116)
        b = blended_fair_value(c, CL.classify(c), dcf_per_share=0.7455,
                               comps_fair_value=35.6214, growth_value=None)
        app = lens_applicability(b)
        self.assertIs(app["fcff_applies"], False)
        self.assertIn("DO NOT apply", app["note"])

    def test_and_True_for_an_ordinary_company(self):
        from valuation.engine.pipeline import lens_applicability
        c = company("MSFT", "Technology", "Software - Infrastructure", 0.12)
        b = blended_fair_value(c, CL.classify(c), dcf_per_share=400.0,
                               comps_fair_value=380.0, growth_value=None)
        self.assertIs(lens_applicability(b)["fcff_applies"], True)


# ==========================================================================================
# 3. THE DEFAULT BRANCH
# ==========================================================================================
class MatureIsADefaultAndMustNotClaimStability(unittest.TestCase):
    def test_a_shrinking_cash_burner_is_not_mature(self):
        """MRNA's own inputs: -16.05% blended growth, FCF negative."""
        c = CL.classify(cd(ticker="MRNA", sector="Healthcare", industry="Biotechnology",
                           analyst_rev_growth_next=-0.1605, fcf=-1.0e9))
        self.assertEqual(c.regime, "declining")
        # A BAN ON THE WORD "stable" FIRED ON MY OWN PROSE DENYING IT -- the reason reads "this
        # is not a mature, stable profile and is not modelled as one". The substring-ban family,
        # in this suite's first cut, and the project's most repeated test defect. The property
        # is that the `mature` branch's CLAIM is absent, so assert that sentence, not a word
        # that appears in both the claim and its denial.
        joined = " ".join(c.reasons)
        self.assertNotIn("Mature, stable profile: standard 5-year FCFF DCF.", joined)
        self.assertIn("is not a mature, stable profile", joined)
        self.assertEqual(c.dcf_reliability, "low")

    def test_a_shrinking_but_cash_generative_company_is_declining_too(self):
        c = CL.classify(company("SHRINK", "Technology", "Software - Infrastructure", -0.20))
        self.assertEqual(c.regime, "declining")
        self.assertEqual(c.dcf_reliability, "medium")

    def test_TSLA_IS_LEFT_IN_MATURE_AND_THAT_IS_DELIBERATE(self):
        """THE POSITIVE CONTROL, and the half of item 25 that is NOT a defect.

        TSLA's blended growth is +0.0784, it is FCF-positive and profitable. Its $23.42 comes
        from ROIC 5% against a WACC of 14% -- a high beta discounted at the real 5.28% 10-year
        yield, which item 25 states plainly is the model working as written. Routing it out of
        `mature` to make its number look better would be choosing the regime on the output.
        """
        c = CL.classify(company("TSLA", "Consumer Cyclical", "Auto Manufacturers", 0.0784))
        self.assertEqual(c.regime, "mature")

    def test_a_slow_grower_is_not_relabelled_on_noise(self):
        """The threshold is -5% rather than 0% because `_blended_growth` mixes a 3-year CAGR
        with the latest year-on-year, so a flat business with one soft year lands slightly
        negative and a 0% bar would relabel it as declining on sampling."""
        for g in (0.0, -0.01, -0.04):
            c = CL.classify(company("FLAT", "Technology", "Software - Infrastructure", g))
            self.assertEqual(c.regime, "mature", g)

    def test_the_threshold_is_named_and_not_typed_twice(self):
        self.assertEqual(CL.DECLINING_GROWTH, -0.05)
        src = open(os.path.join(REPO, "valuation", "engine", "classify.py"),
                   encoding="utf-8").read()
        import ast
        n = sum(1 for node in ast.walk(ast.parse(src))
                if isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "DECLINING_GROWTH")
        self.assertEqual(n, 1)

    def test_the_declining_reason_says_what_is_NOT_estimated(self):
        c = CL.classify(cd(ticker="MRNA", sector="Healthcare", industry="Biotechnology",
                           analyst_rev_growth_next=-0.1605, fcf=-1.0e9))
        joined = " ".join(c.reasons)
        self.assertIn("where the decline stops", joined)
        self.assertIn("burning cash", joined)


# ==========================================================================================
# THE HEALTH SUB-SCORE
# ==========================================================================================
class NegativeFreeCashFlowIsNotARunwayHere(unittest.TestCase):
    """DUK's driver read *"Cash-burning: ~0.1 yrs of runway at the current burn."*"""

    def _health(self, ticker, sector, industry, growth):
        """THE UNDERLYING FIELDS, so the REAL properties compute.

        `net_debt_to_ebitda`, `interest_coverage` and `cash_runway_years` are all read-only
        PROPERTIES, and the first cut of this helper passed them to the constructor -- which
        raised, and failed five tests for a reason unrelated to any of their subjects. The
        second temptation was a stand-in object with just the attributes `_health_score`
        touches; that is the wrong-object family, because the suite would then be testing the
        fixture's idea of how leverage is computed rather than the model's.

        So the fields are set and the properties are left to do their own arithmetic:
        net debt 58bn over EBITDA 10bn gives 5.8x, EBIT 6bn over interest 2bn gives 3.0x, and
        cash 200m against a 2bn burn gives the 0.1 years DUK's live driver reported.
        """
        from valuation.engine.scoring import _health_score
        c = cd(ticker=ticker, sector=sector, industry=industry,
               analyst_rev_growth_next=growth, fcf=-2.0e9,
               cash_sti=2.0e8,                       # -> cash_runway_years 0.1
               total_debt=5.8e10,                    # -> net_debt 57.8bn
               ebit=6.0e9, da=4.0e9,                 # -> EBITDA 10bn, leverage ~5.78x
               interest_expense=2.0e9)               # -> coverage 3.0x
        # The fixture is checked against the properties it means to drive, or a later model
        # change could silently leave these tests measuring None.
        assert c.net_debt_to_ebitda is not None and 5.0 < c.net_debt_to_ebitda < 6.5, \
            c.net_debt_to_ebitda
        assert c.interest_coverage == 3.0, c.interest_coverage
        assert abs(c.cash_runway_years - 0.1) < 1e-9, c.cash_runway_years
        return _health_score(c, CL.classify(c))

    def test_a_utility_gets_no_runway_sentence(self):
        _, drivers = self._health("DUK", "Utilities", "Utilities - Regulated Electric", 0.0469)
        joined = " ".join(drivers)
        # THE CLAIM, not the word. The explanatory driver legitimately contains "cash-runway
        # warning" while SAYING IT DOES NOT APPLY -- banning the word would fire on the
        # sentence that fixes the defect, which is the same trap as the `stable` ban above.
        self.assertNotIn("Cash-burning:", joined)
        self.assertNotIn("yrs of runway", joined)
        self.assertNotIn("at the current burn", joined)

    def test_it_SAYS_why_the_check_does_not_apply(self):
        """A dropped term that is silent looks identical to one that scored in the middle."""
        _, drivers = self._health("DUK", "Utilities", "Utilities - Regulated Electric", 0.0469)
        joined = " ".join(drivers)
        self.assertIn("capex IS the business", joined)
        self.assertIn("is not scored for a", joined)
        self.assertIn("redistributed", joined)

    def test_the_sub_score_is_WITHHELD_exactly_as_the_financial_regime_does(self):
        """ITEM 26(a) REVERSED ITEM 25's CHOICE HERE, AND THE REVERSAL WAS MEASURED.

        This test used to assert the opposite -- that leverage and coverage still carried the
        sub-score -- on item 25's reasoning that *"withholding the whole sub-score would throw
        away two valid measurements to remove one invalid one"*. Checked against the live
        service after the land, that reasoning is wrong in the direction that matters: health
        went **O 35.7 -> 20.4** and **NEE 36.6 -> 21.5**, DOWN, because the surviving drivers
        read net debt/EBITDA 6.0x and 5.8x -- ordinary for a property trust or a rate-regulated
        utility, alarming for an industrial. The reweighting concentrated the sub-score on the
        metric these regimes structurally score worst on.

        So the assertion is inverted because the BEHAVIOUR was changed by instruction, not
        because it was inconvenient: the sub-score is now withheld as NOT APPLICABLE, and the
        0.20 is redistributed by `compute_score`'s existing renormalisation -- the same
        mechanism, in the same shape, as the `financial` branch.
        """
        score, drivers = self._health("DUK", "Utilities",
                                      "Utilities - Regulated Electric", 0.0469)
        self.assertIsNone(score, "health must be WITHHELD, not scored, for a regulated utility")
        self.assertTrue(drivers, "a withheld sub-score that is silent looks identical to one "
                                 "that scored in the middle")

    def test_it_is_withheld_in_the_SAME_FORM_as_the_financial_regime(self):
        """`B7` in spirit: one withholding mechanism, not two that can drift apart.

        Both branches return `(None, [one reason line])`, so the redistribution and the
        NOT-APPLICABLE-rather-than-MISSING confidence treatment are the existing ones rather
        than a parallel arrangement for these two regimes.
        """
        from valuation.engine.scoring import _health_score
        fin = cd(ticker="JPM", sector="Financial Services", industry="Banks - Diversified",
                 analyst_rev_growth_next=0.04, fcf=1.0e9, total_debt=1.0e11,
                 ebit=5.0e10, da=1.0e9, interest_expense=1.0e10)
        fin_score, fin_drivers = _health_score(fin, CL.classify(fin))
        reit_score, reit_drivers = self._health("O", "Real Estate", "REIT - Retail", 0.1116)
        self.assertIsNone(fin_score)
        self.assertIsNone(reit_score)
        self.assertEqual(len(fin_drivers), 1)
        self.assertEqual(len(reit_drivers), 1)
        for d in (fin_drivers[0], reit_drivers[0]):
            self.assertIn("is not scored for a", d)
            self.assertIn("redistributed", d)

    def test_a_reit_is_treated_the_same_way(self):
        _, drivers = self._health("O", "Real Estate", "REIT - Retail", 0.1116)
        self.assertIn("capex IS the business", " ".join(drivers))

    def test_a_real_cash_burner_STILL_gets_its_runway_warning(self):
        """THE POSITIVE CONTROL. The runway sentence exists for a reason and this must not have
        removed it from the companies it is about."""
        from valuation.engine.scoring import _health_score
        c = cd(ticker="BURN", sector="Healthcare", industry="Biotechnology",
               analyst_rev_growth_next=0.30, fcf=-5.0e8,
               cash_sti=4.0e8,                       # -> 0.8 years of runway
               total_debt=1.0e9, ebit=1.0e9, da=0.0,
               interest_expense=5.0e8)
        _, drivers = _health_score(c, CL.classify(c))
        self.assertIn("runway", " ".join(drivers).lower())

    def test_is_cash_burning_still_reports_the_measured_fact(self):
        """The FACT is true; the INFERENCE is what does not follow. The distinction has to
        survive or the classification starts lying about the financials."""
        c = cd(ticker="DUK", sector="Utilities", industry="Utilities - Regulated Electric",
               analyst_rev_growth_next=0.0469, fcf=-2.0e9)
        self.assertIs(CL.classify(c).is_cash_burning, True)


# ==========================================================================================
# 4. THE SHARE-CLASS DOT
# ==========================================================================================
class ShareClassDots(unittest.TestCase):
    def setUp(self):
        from valuation.data.fetcher import normalise_ticker
        self.n = normalise_ticker

    def test_the_live_case(self):
        self.assertEqual(self.n("BRK.B"), "BRK-B")

    def test_it_is_idempotent(self):
        self.assertEqual(self.n("BRK-B"), "BRK-B")
        self.assertEqual(self.n(self.n("BRK.B")), "BRK-B")

    def test_other_share_classes(self):
        for a, b in (("BF.B", "BF-B"), ("LEN.B", "LEN-B"), ("HEI.A", "HEI-A")):
            self.assertEqual(self.n(a), b)

    def test_lowercase_and_whitespace(self):
        self.assertEqual(self.n(" brk.b "), "BRK-B")

    def test_it_touches_NOTHING_ELSE(self):
        """NARROW BY DESIGN. Widening it to "any dot" would start rewriting symbols nobody
        asked about, and the failure direction there is a silent lookup of the WRONG company
        rather than a clean miss."""
        for t in ("AAPL", "^GSPC", "BTC-USD", "BRK.BB", "A.B.C", "TSLA.", ".X",
                  "TOOLONGX.B", "1.A", ""):
            self.assertEqual(self.n(t), t.strip().upper(), t)

    def test_real_world_exchange_suffixes_are_left_alone(self):
        """The synthetic shapes above are not the cases a reader will worry about.

        These are the actual foreign-listing spellings, and every one carries either a digit
        before the dot or more than one letter after it, which is why the pattern misses them.
        """
        for t in ("0700.HK", "7203.T", "SAN.PA", "RY.TO", "005930.KS"):
            self.assertEqual(self.n(t), t.upper(), t)

    def test_a_single_letter_EXCHANGE_suffix_collides_and_fails_SAFE(self):
        """THE KNOWN FALSE POSITIVE, PINNED SO IT IS A DECISION RATHER THAN A SURPRISE.

        `VOD.L` is Vodafone on the London exchange and `.F`/`.V` collide the same way: a venue
        letter is syntactically identical to a class letter, and **no regex can separate them**
        because the distinguishing information is not in the string. This asserts the collision
        happens (so nobody "fixes" it by accident and widens the pattern instead) AND that the
        result is unresolvable rather than a different real company -- which is what makes the
        failure safe: `VOD-L` fetches nothing, trips `looks_not_found`, and the route returns the
        404. Before this change the same input produced a fabricated `score 40, "Reduce"`.
        """
        self.assertEqual(self.n("VOD.L"), "VOD-L")
        # THIS LIST GOT LONGER BY BEING TESTED. The first cut of the sibling test above
        # asserted `BABA.N` was left alone and FAILED against correct code: `.N` is the
        # Reuters venue code for NYSE and `.O` for Nasdaq, so the family is not just the
        # European single letters I first named. An over-claim about my own predicate, caught
        # by driving it rather than by reading it.
        self.assertEqual(self.n("BABA.N"), "BABA-N")
        # The safe part: the rewrite cannot land on a DIFFERENT listed company, because the
        # only thing it ever does is swap one separator for another within one symbol.
        self.assertEqual(self.n("VOD.L").replace("-", "."), "VOD.L")


class TheNormalisationIsSaidOutLoud(unittest.TestCase):
    def test_a_rewritten_symbol_leaves_a_note(self):
        """A reader who typed `BRK.B` and gets a page headed `BRK-B` is owed the reason."""
        import ast
        src = open(os.path.join(REPO, "valuation", "data", "fetcher.py"),
                   encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "get_company")
        body = ast.unparse(fn)
        self.assertIn("Symbol normalised from", body)

    def test_it_normalises_before_the_first_fetch(self):
        """Retrying on failure would work and would be worse: it makes the hyphen form a
        FALLBACK, so the two spellings take different code paths and only one is exercised."""
        import ast
        src = open(os.path.join(REPO, "valuation", "data", "fetcher.py"),
                   encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "get_company")
        lines = ast.unparse(fn).split("\n")
        norm = next(i for i, L in enumerate(lines) if "normalise_ticker" in L)
        fetch = next(i for i, L in enumerate(lines) if "yahoo.fetch" in L)
        self.assertLess(norm, fetch, "the symbol is normalised after the first fetch")


# ==========================================================================================
# 5. NOT FOUND
# ==========================================================================================
class TheNotFoundPredicateIsAConjunction(unittest.TestCase):
    """A MUTATION WALKED THROUGH THIS AND THE REASON IS THE LESSON.

    The rule was inline in `get_company` and the suite's positive control used AAPL. Changing
    the `and` to an `or` -- which refuses any real company missing any ONE of the three fields
    -- was caught by NOTHING, because AAPL has all three and the disjunction is INERT for it.
    **A control that cannot distinguish the two versions is not a control.**

    So the predicate was given a name and is driven here with the cases that separate them.
    Each of these is a real company shape, which is why the direction matters: a pre-revenue
    biotech has a price and no revenue; a thin ADR can have revenue and no usable share count;
    a company mid-halt has revenue and shares and no live quote. An `or` would call all three
    "not found", turning a data gap into a claim that the company does not exist -- the one
    direction this refusal must never fail in.
    """

    def setUp(self):
        from valuation.data.fetcher import looks_not_found
        self.f = looks_not_found

    class _C(object):
        def __init__(self, **kw):
            self.price = self.revenue = self.shares_diluted = None
            for k, v in kw.items():
                setattr(self, k, v)

    def test_all_three_absent_is_not_found(self):
        self.assertIs(self.f(self._C()), True)

    def test_a_price_alone_is_ENOUGH_to_say_something_was_found(self):
        """A pre-revenue biotech, or a fresh listing with no filed statements yet."""
        self.assertIs(self.f(self._C(price=10.0)), False)

    def test_a_revenue_alone_is_enough(self):
        """A company mid-halt, or one the quote feed dropped."""
        self.assertIs(self.f(self._C(revenue=1.0e9)), False)

    def test_a_share_count_alone_is_enough(self):
        self.assertIs(self.f(self._C(shares_diluted=1.0e8)), False)

    def test_all_three_present_is_obviously_found(self):
        self.assertIs(self.f(self._C(price=10.0, revenue=1.0e9,
                                     shares_diluted=1.0e8)), False)

    def test_a_missing_attribute_entirely_is_treated_as_absent(self):
        """A caller's hand-built object need not carry every field."""
        class Bare(object):
            pass
        self.assertIs(self.f(Bare()), True)

    def test_the_flag_is_set_by_THIS_predicate_and_not_an_inline_copy(self):
        """Or the named rule is decoration and the inline one is what ships.

        ASSERTED ON THE `if` THAT GUARDS THE ASSIGNMENT, not on a substring. My first cut banned
        `"cd.shares_diluted is None"` anywhere in `get_company` and **failed against the correct
        tree**: line 86 is the pre-existing EDGAR gap-fill condition, which legitimately tests
        the same field for an entirely different reason. The substring-ban family, third time in
        this item alone -- and the cure is the same each time, which is to assert the PROPERTY.
        """
        import ast
        src = open(os.path.join(REPO, "valuation", "data", "fetcher.py"),
                   encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "get_company")
        guards = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            if any("fetch_failed" in ast.unparse(st) for st in node.body):
                guards.append(ast.unparse(node.test))
        self.assertEqual(len(guards), 1,
                         "expected exactly one `if` setting `fetch_failed`: %r" % guards)
        self.assertEqual(guards[0].replace(" ", ""), "looks_not_found(cd)",
                         "the flag is set by an inline condition rather than the named rule, "
                         "so the two can drift: %r" % guards[0])


class ANotFoundTickerGetsNoScore(unittest.TestCase):
    def test_the_flag_is_set_where_the_fact_is_known(self):
        import ast
        src = open(os.path.join(REPO, "valuation", "data", "fetcher.py"),
                   encoding="utf-8").read()
        self.assertIn("cd.fetch_failed = True", src)

    def test_the_route_refuses_with_404_and_no_score(self):
        from valuation.web.app import app
        app.config["TESTING"] = True
        c = app.test_client()
        r = c.post("/api/value", json={"ticker": "ZZZZQ"})
        self.assertEqual(r.status_code, 404, r.data[:300])
        import json
        d = json.loads(r.data.decode("utf-8"))
        self.assertEqual(d["error"], "ticker not found")
        for banned in ("score", "recommendation", "base_fair_value", "verdict"):
            self.assertNotIn(banned, d,
                             "a not-found response carries %r" % banned)

    def test_the_hint_names_the_share_class_form(self):
        from valuation.web.app import app
        app.config["TESTING"] = True
        import json
        d = json.loads(app.test_client().post(
            "/api/value", json={"ticker": "ZZZZQ"}).data.decode("utf-8"))
        self.assertIn("BRK-B", d["hint"])

    def test_a_real_company_is_not_refused(self):
        """THE POSITIVE CONTROL AND IT NEEDS THE NETWORK, so it skips LOUDLY rather than
        passing: a refusal that fires on everything would satisfy every assertion above."""
        from valuation.data import fetcher
        try:
            cd_ = fetcher.get_company("AAPL")
        except Exception as e:                                       # noqa: BLE001
            self.skipTest("no network for the positive control: %s" % type(e).__name__)
        if getattr(cd_, "fetch_failed", False):
            print("       (NOTE: AAPL could not be fetched either - the vendor is down, so "
                  "this control is UNMEASURED rather than passing.)")
            self.skipTest("the vendor returned nothing for AAPL, so the control cannot run")
        self.assertIsNotNone(cd_.price)

    def test_the_refusal_is_not_cached(self):
        """A cache entry for a symbol that does not exist would answer the next request from
        memory, and the refusal would then depend on cache state."""
        import ast
        src = open(os.path.join(REPO, "valuation", "web", "app.py"),
                   encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "api_value")
        body = ast.unparse(fn)
        i_refuse = body.index("ticker not found")
        i_cache = body.index("_RESULTS.put")
        self.assertLess(i_refuse, i_cache, "the result is cached before the refusal")


# ==========================================================================================
# THE WARNING NAMED THE WRONG CAUSE
# ==========================================================================================
class TheImplausibilityWarningNamesTheModelNotTheData(unittest.TestCase):
    def test_a_third_branch_exists_for_the_refused_regimes(self):
        import ast
        src = open(os.path.join(REPO, "valuation", "engine", "pipeline.py"),
                   encoding="utf-8").read()
        self.assertIn("_refused_fcff", src)
        tree = ast.parse(src)
        self.assertTrue(any(isinstance(n, ast.Assign) and "regime" in ast.unparse(n)
                            and "_refused_fcff" in ast.unparse(n)
                            for n in ast.walk(tree)))

    def test_the_old_message_survives_for_an_ordinary_company(self):
        """It is the right message THERE -- a 0.2x ratio on an industrial really is usually a
        currency or share-count problem. Only the refused regimes get the new branch."""
        src = open(os.path.join(REPO, "valuation", "engine", "pipeline.py"),
                   encoding="utf-8").read()
        self.assertIn("almost", src)
        self.assertIn("certainly a data problem (currency or share count)", src)

    def test_the_new_message_says_peer_comparison_and_not_data_problem(self):
        src = open(os.path.join(REPO, "valuation", "engine", "pipeline.py"),
                   encoding="utf-8").read()
        i = src.index("_refused_fcff and (ratio")
        window = src[i:i + 1200]
        self.assertIn("NOT a data problem", window)
        self.assertIn("peer comparison", window)
        self.assertIn("NOT an", window)


if __name__ == "__main__":
    unittest.main(verbosity=2)
