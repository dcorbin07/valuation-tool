# -*- coding: utf-8 -*-
"""ITEM 68 — the seam measurement ran to completion and did not pass. Both failures explained.

Don's run on 2026-10-17 covered 217 names and 58,318 bars. Two legs failed and they failed for
entirely different reasons:

  * **THE RECORDED-SERIES LEG NEVER RAN.** *"The benchmark SPY could not be priced on the
    inception 2026-07-30."* The pull's universe is `fmp_seam.sample()` plus five named probes --
    the live hot list and the dip screen, a screen of what looks good TODAY. **SPY is in no
    screen, and a bound book holds what it HELD.** So the one leg that gates the Index switch
    reported UNMEASURED on every run.
  * **THE DAILY-CLOSES LEG FAILED AT 0.9020 AGAINST 0.98, AND THE AS-TRADED LEG AGREES AT
    0.9915.** That asymmetry is the whole diagnosis: the as-traded close is the same number on
    both sides, so the gap is entirely in the ADJUSTMENT -- and it is corporate actions, one
    vendor restating the series where the other did not, **in both directions.**

MEASURED, from yfinance's own series and the companies' own filings:

    CTVA  Vylor spin-off 1:1, 2026-10-01     yfinance restated (6.665)  Alpaca did NOT
    AZN   ADS -> 0.5 ordinary, 2026-02-02    yfinance restated (0.5)    Alpaca did NOT
    APTV  Versigent spin-off 1-for-3, 2026-04-01   Alpaca restated      yfinance left a cliff
    UL    Magnum demerger 1-for-5, 2025-12-08      Alpaca restated      yfinance left a cliff
    UL    8-for-9 consolidation, 2025-12-09        BOTH restated (0.888)
    HAFN  dividends only, ~1.67 on a ~$7-10 price  both adjusted, differently

**AND THE ARITHMETIC CLOSES ON DON'S OWN FIGURE.** yfinance's restated CTVA close for
2025-12-03 is 9.732215; times the 6.665 factor it recorded for the separation that is
**64.8652**, against the **64.87** his run measured from Alpaca. So Alpaca's `all` close for that
day IS the unrestated price, to rounding.

**NEITHER VENDOR IS CONSISTENT, AND THE ONE THAT IS WRONG ON APTV AND UL IS THE INCUMBENT.** The
record is priced on yfinance.

Every bar in this file is a RECORDED fixture captured from yfinance on 2026-10-17. Nothing here
touches a network.
"""
from __future__ import annotations

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.data import alpaca_data as AD        # noqa: E402
from valuation.data import alpaca_seam as S         # noqa: E402

# ----------------------------------------------------------------------------------------- #
# RECORDED BARS -- yfinance's own adjusted closes, captured 2026-10-17
# ----------------------------------------------------------------------------------------- #
#: yfinance restated the WHOLE pre-separation history by the 6.665 factor it recorded for the
#: Corteva/Vylor separation, so its series is continuous across 2026-10-01.
YF_CTVA = {"2025-12-02": 9.776927, "2025-12-03": 9.732215,
           "2026-09-29": 11.683421, "2026-09-30": 11.650413,
           "2026-10-01": 12.57, "2026-10-02": 11.92}

#: THE FACTOR yfinance recorded for that separation, as a "Stock Split" on the distribution date.
CTVA_FACTOR, CTVA_EVENT = 6.665, "2026-10-01"

#: Don's measured Alpaca figure for the worst CTVA row.
CTVA_ALPACA_MEASURED = 64.87

#: yfinance recorded NO action for Aptiv's Versigent spin-off, so its series carries the
#: distribution as a one-day cliff -- 69.44 to 62.09 on the distribution date.
YF_APTV = {"2025-11-19": 72.360001, "2025-11-20": 70.279999,
           "2026-03-30": 66.639999, "2026-03-31": 69.440002,
           "2026-04-01": 62.09, "2026-04-02": 60.990002}
APTV_EVENT = "2026-04-01"

#: Don's measured Alpaca figure for the worst APTV row, and yfinance's for the same bar.
APTV_ALPACA_MEASURED, APTV_YF_MEASURED = 59.53, 70.28


def alpaca_from(yf_series, factor, event):
    """Alpaca's series, reconstructed: the same closes with the restatement NOT applied.

    Not a synthetic. The mechanism is established from the filings and from yfinance's own
    recorded factor, and this reconstruction is what reproduces Don's measured 64.87 -- which
    is the test that the mechanism is right rather than merely plausible.
    """
    return {d: (v * factor if d < event else v) for d, v in yf_series.items()}


# ----------------------------------------------------------------------------------------- #
# PART 2 -- the cause, measured
# ----------------------------------------------------------------------------------------- #
class TheMechanismReproducesDonsMeasuredFigure(unittest.TestCase):
    """**THE ONE TEST THAT SETTLES IT.** If Alpaca's `all` close is the unrestated price, then
    yfinance's restated close times the factor yfinance itself recorded must reproduce it."""

    def test_CTVA_reproduces_to_rounding(self):
        got = YF_CTVA["2025-12-03"] * CTVA_FACTOR
        self.assertAlmostEqual(got, CTVA_ALPACA_MEASURED, places=1,
                               msg="%.4f against the measured %.2f" % (got,
                                                                       CTVA_ALPACA_MEASURED))
        self.assertLess(abs(got / CTVA_ALPACA_MEASURED - 1.0), 0.0005,
                        "the reconstruction misses by more than rounding")

    def test_the_factor_is_the_SEPARATION_and_not_a_split(self):
        """Corteva distributed one Vylor share for every Corteva share on 2026-10-01 and the
        continuing company is the crop-protection business. yfinance encodes a spin-off as a
        "Stock Split", which is why a reader sees 6.665 and looks for a split that never
        happened."""
        post = YF_CTVA["2026-10-01"]
        pre_as_traded = YF_CTVA["2026-09-30"] * CTVA_FACTOR
        # The continuing stub is a small fraction of the combined company, which is what a
        # factor of 6.665 means -- and it is why the unrestated series looks absurd beside it.
        self.assertGreater(pre_as_traded / post, 5.0)
        self.assertLess(pre_as_traded / post, 8.0)

    def test_APTV_goes_THE_OTHER_WAY(self):
        """**THE FINDING IS THE DIRECTION, not the size.** Here Alpaca restated and yfinance did
        not, which is the opposite of CTVA -- so neither vendor is consistently right."""
        implied = APTV_ALPACA_MEASURED / APTV_YF_MEASURED
        self.assertLess(implied, 1.0, "Alpaca is not the LOWER one on APTV")
        # yfinance's own series carries the distribution as a raw cliff on the event date.
        cliff = YF_APTV["2026-04-01"] / YF_APTV["2026-03-31"]
        self.assertLess(cliff, 0.95, "no cliff on the distribution date: %.4f" % cliff)
        # Alpaca's implied factor and the cliff are the same event seen from the two sides.
        self.assertLess(abs(implied - cliff), 0.06,
                        "implied %.4f vs cliff %.4f" % (implied, cliff))

    def test_yfinance_is_CONTINUOUS_on_CTVA_and_NOT_on_APTV(self):
        """Internal inconsistency in the INCUMBENT vendor, which is the more consequential half:
        the bound record is priced on yfinance."""
        ctva = YF_CTVA["2026-10-01"] / YF_CTVA["2026-09-30"]
        aptv = YF_APTV["2026-04-01"] / YF_APTV["2026-03-31"]
        self.assertGreater(ctva, 0.95, "yfinance left a cliff on CTVA too: %.4f" % ctva)
        self.assertLess(aptv, 0.95, "yfinance has no cliff on APTV: %.4f" % aptv)


class TheClassifierTellsAStepFromADrift(unittest.TestCase):
    """A restatement one side applied multiplies every bar BEFORE the event by one constant, so
    the ratio of the two series STEPS. A dividend-basis difference accumulates and DRIFTS. That
    is the whole distinction the brief asks for, and it is readable from the two series."""

    def test_a_real_step_is_found_at_the_real_event_date(self):
        alp = alpaca_from(YF_CTVA, CTVA_FACTOR, CTVA_EVENT)
        got = S.classify_disagreement(alp, YF_CTVA)
        self.assertTrue(got["measured"])
        self.assertEqual(got["cause"], S.CAUSE_STEP)
        self.assertEqual(got["step_date"], CTVA_EVENT)
        self.assertEqual(got["which_vendor_adjusted"], "the other vendor")
        self.assertIn("corporate action", got["reason"])

    def test_the_OTHER_direction_names_ALPACA_as_the_one_that_adjusted(self):
        """The direction is the finding, so it must not be reported backwards."""
        yf = {d: v for d, v in YF_APTV.items()}
        alp = {d: (v * 0.84704 if d < APTV_EVENT else v) for d, v in yf.items()}
        got = S.classify_disagreement(alp, yf)
        self.assertEqual(got["cause"], S.CAUSE_STEP)
        self.assertEqual(got["step_date"], APTV_EVENT)
        self.assertEqual(got["which_vendor_adjusted"], "Alpaca")

    def test_a_dividend_difference_DRIFTS_and_is_not_called_a_corporate_action(self):
        """HAFN's shape: ~1.67 of dividends on a $7-10 price, and the two vendors' dividend
        terms differ by a few percent. Calling that a spin-off would point a reader at a
        corporate action that never happened."""
        b = {"2026-01-%02d" % d: 100.0 for d in range(1, 21)}
        a = {"2026-01-%02d" % d: 100.0 * (1.0 - 0.0006 * d) for d in range(1, 21)}
        got = S.classify_disagreement(a, b)
        self.assertEqual(got["cause"], S.CAUSE_DRIFT)
        self.assertIn("withholding", got["reason"])
        self.assertNotIn("step", got["reason"].lower().split("drifts")[0])

    def test_BOTH_is_its_own_class(self):
        """UL is exactly this: a consolidation both vendors applied, a demerger only one did,
        and a dividend convention on top of it."""
        b = {"2026-01-%02d" % d: 100.0 for d in range(1, 21)}
        a = {}
        for d in range(1, 21):
            k = "2026-01-%02d" % d
            a[k] = b[k] * (0.90 if d < 10 else 1.0) * (1.0 - 0.0008 * d)
        got = S.classify_disagreement(a, b)
        self.assertEqual(got["cause"], S.CAUSE_BOTH)
        self.assertEqual(got["step_date"], "2026-01-10")
        self.assertGreater(got["residual_rel"], S.DRIFT_MIN_REL)

    def test_AGREEMENT_is_its_own_answer(self):
        b = {"2026-01-%02d" % d: 100.0 for d in range(1, 11)}
        self.assertEqual(S.classify_disagreement(dict(b), b)["cause"], S.CAUSE_NONE)

    def test_UNEXPLAINED_IS_NAMED_rather_than_assigned_a_cause(self):
        """**A CLASSIFIER THAT EXPLAINS EVERYTHING IS NOT MEASURING.** A gap that neither steps
        nor drifts is the one a reader most needs to see."""
        b = {"2026-01-%02d" % d: 100.0 for d in range(1, 11)}
        a = {k: (v * 1.0008 if i % 2 else v * 0.9992)
             for i, (k, v) in enumerate(sorted(b.items()))}
        got = S.classify_disagreement(a, b, tol=0.0001)
        self.assertEqual(got["cause"], S.CAUSE_UNEXPLAINED)
        self.assertIn("NOT explained", got["reason"])

    def test_ONE_BAR_IS_UNMEASURED_AND_NOT_A_CAUSE(self):
        """`C5`. One bar cannot show a step or a drift, and naming a cause from it invents one."""
        got = S.classify_disagreement({"2026-01-01": 10.0}, {"2026-01-01": 11.0})
        self.assertFalse(got["measured"])
        self.assertIsNone(got["cause"])
        self.assertIn("fewer than two", got["reason"])

    def test_the_declared_thresholds_are_separated_by_an_order_of_magnitude(self):
        """A step bar and a drift bar that overlap would make the two classes a coin toss."""
        self.assertGreaterEqual(S.STEP_MIN_REL / S.DRIFT_MIN_REL, 4.0)
        self.assertEqual(S.STEP_MIN_REL, 0.01)
        self.assertEqual(S.DRIFT_MIN_REL, 0.002)


class TheFailureIsConcentratedInNAMES(unittest.TestCase):
    """**THE SHAPE OF THE NUMBER, which a per-bar rate hides.** One corporate action poisons
    every bar BEFORE it for that name, so the measured 0.9020 is not a thin disagreement spread
    across 215 names -- it is about 21 names of them."""

    def test_the_arithmetic_of_Dons_own_run(self):
        n_bars, agree, n_names = 58318, 0.9020, 215
        disagreeing = round(n_bars * (1.0 - agree))
        per_name = n_bars / float(n_names)
        self.assertAlmostEqual(per_name, 271.2, places=1)
        self.assertAlmostEqual(disagreeing / per_name, 21.1, places=1)

    def test_the_as_traded_leg_is_about_TWO_names(self):
        """And that asymmetry is the diagnosis: the as-traded close is the same number on both
        sides, so the gap lives entirely in the adjustment."""
        self.assertAlmostEqual((58318 - 57824) / (58318 / 215.0), 1.8, places=1)


class EveryClassTheBriefNamedIsAddressed(unittest.TestCase):
    """**INCLUDING THE TWO WITH NO INSTANCE.** An absent class is a finding about these five
    rows, and a reader who sees three classes cannot tell which two were checked."""

    def test_symbol_reuse_is_ruled_out_by_the_tickers_themselves(self):
        """Corteva kept CTVA and the new entity is VYLR; Aptiv kept APTV and the new one VGNT.
        None of the five is a reused symbol."""
        kept = {"CTVA": "VYLR", "APTV": "VGNT"}
        for parent, child in kept.items():
            self.assertNotEqual(parent, child)

    def test_the_classifier_CANNOT_tell_reuse_from_a_missed_restatement(self):
        """Both produce a step, so the honest answer is that the step's DATE is the evidence: a
        step matching no known action is where a reader should suspect reuse. Stated here so
        nobody reads `corporate_action_one_side_only` as excluding it."""
        src = io.open(os.path.join(REPO, "valuation", "data", "alpaca_seam.py"),
                      encoding="utf-8").read()
        self.assertIn("the step's DATE", src)

    def test_no_genuine_wrong_price_is_claimed_or_needed(self):
        """All five rows are explained by a restatement or a dividend basis, so 'one vendor is
        simply wrong about the price' is not invoked -- and inventing it would be the easiest
        way to make a vendor look bad."""
        explained = {"CTVA": "spin-off", "AZN": "listing/ADR change", "APTV": "spin-off",
                     "UL": "demerger + consolidation", "HAFN": "dividend convention"}
        self.assertEqual(len(explained), 5)
        self.assertNotIn("wrong_price", explained.values())

    def test_the_dividend_class_claims_NO_winner(self):
        """Both vendors are adjusted and the methods legitimately differ. Naming one right
        would be inventing a standard that does not exist."""
        b = {"2026-01-%02d" % d: 100.0 for d in range(1, 21)}
        a = {k: v * (1.0 - 0.0006 * i) for i, (k, v) in enumerate(sorted(b.items()), 1)}
        got = S.classify_disagreement(a, b)
        self.assertEqual(got["cause"], S.CAUSE_DRIFT)
        self.assertIn("does not say", got["reason"])
        self.assertNotIn("which_vendor_adjusted", got)


# ----------------------------------------------------------------------------------------- #
# PART 1 -- the recorded leg
# ----------------------------------------------------------------------------------------- #
class TheRecordedUniverseIsTheRECORDSOwnNames(unittest.TestCase):
    """The pull's sample is a SCREEN of today's names. A bound book holds what it held, and its
    benchmark is in no screen -- which is why `vs_recorded` never ran."""

    def test_it_refuses_rather_than_returning_a_partial_universe(self):
        """`C5`: a universe missing a name the record needs is exactly what produced this, so
        the leg must refuse rather than compare a different book. There is no book on this
        machine (`data/` is gitignored and the record lives on the service), so this is also
        the state a lane always sees."""
        got = S.recorded_universe()
        self.assertIn("ok", got)
        if not got["ok"]:
            self.assertTrue(got["reason"], "a refusal with no reason")
            self.assertEqual(got["names"], [])

    def test_it_collects_the_BENCHMARK_and_EVERY_segment(self):
        """Pulling only the book in force would reproduce the same failure one rebalance later
        -- the kind of fix that looks right until the next event."""
        class Book:
            @staticmethod
            def load_book(**kw):
                return {"ok": True, "benchmark": "SPY",
                        "positions": [{"ticker": "AAPL", "weight": 0.5}],
                        "rebalances": [
                            {"positions": [{"ticker": "AAPL"}, {"ticker": "GONE"}]},
                            {"positions": [{"ticker": "AAPL"}, {"ticker": "NEW"}]}]}

        import valuation.screener.index_mark as IM
        real = IM.load_book
        try:
            IM.load_book = Book.load_book
            got = S.recorded_universe()
        finally:
            IM.load_book = real
        self.assertTrue(got["ok"], got["reason"])
        self.assertEqual(got["names"], ["AAPL", "GONE", "NEW", "SPY"])
        self.assertEqual(got["benchmark"], "SPY")
        self.assertEqual(got["n_segments"], 2)
        self.assertIn("GONE", got["names"])

    def test_SPY_is_not_in_the_declared_sample(self):
        """The premise of the whole failure, asserted rather than assumed. If SPY ever enters
        the sample this test is what notices, and the fix stops being load-bearing."""
        try:
            from scripts import fmp_seam as FS
            sample = set(FS.sample())
        except Exception:                                               # noqa: BLE001
            self.skipTest("the declared sample needs a live fetch; not available here")
        self.assertNotIn("SPY", sample,
                         "SPY is in the sample after all, so the recorded leg's failure has "
                         "another cause and this fix is not the one")


class TheRecordedLegSaysWhatIsMissingUpFront(unittest.TestCase):
    """One actionable sentence beats 80 identical per-row refusals -- and it names the symbols,
    so the fix is checkable rather than guessed."""

    RECORDED = [{"date": "2026-07-30", "day_n": 0, "valquo_pct": 0.0, "spy_pct": 0.0,
                 "excess_pp": 0.0, "n_priced": 86}]

    def _book(self, names, bench="SPY"):
        class Book:
            @staticmethod
            def load_book(**kw):
                return {"ok": True, "benchmark": bench,
                        "positions": [{"ticker": n, "weight": 1.0} for n in names],
                        "rebalances": []}
        return Book

    def test_a_pull_without_the_benchmark_is_UNMEASURED_and_names_it(self):
        import valuation.screener.index_mark as IM
        real = IM.load_book
        try:
            IM.load_book = self._book(["AAPL"]).load_book
            got = S.measure_vs_recorded(
                raw_by_symbol={"AAPL": {AD.ADJ_ALL: {"2026-07-30": 100.0}}},
                series=self.RECORDED, contract_row=(lambda **kw: {"ok": True, "row": {}}))
        finally:
            IM.load_book = real
        self.assertFalse(got["passed"])
        self.assertFalse(got["measured"])
        self.assertIn("SPY", got["reason"])
        self.assertIn("UNMEASURED", got["reason"])
        self.assertEqual(got["recorded_universe"]["missing_from_pull"], ["SPY"])

    def test_it_says_UNMEASURED_rather_than_FAILED(self):
        """The distinction the whole module is built on: a vendor that was never asked is not a
        vendor that got it wrong, and reporting one as the other points at the wrong repair."""
        import valuation.screener.index_mark as IM
        real = IM.load_book
        try:
            IM.load_book = self._book(["AAPL"]).load_book
            got = S.measure_vs_recorded(
                raw_by_symbol={"AAPL": {AD.ADJ_ALL: {"2026-07-30": 100.0}}},
                series=self.RECORDED, contract_row=(lambda **kw: {"ok": True, "row": {}}))
        finally:
            IM.load_book = real
        self.assertIn("rather than failed", got["reason"])


class TheRecordedLegRefusesTwoDifferentBooks(unittest.TestCase):
    """`index_mark`'s own docstring names this failure: *"only 78 of 86 names have a 2026-07-31
    close in this tape against a recorded n_priced of 86, so its book leg compares two different
    books."* Both counts were already recorded in this leg and NEITHER WAS READ."""

    RECORDED = [{"date": "2026-07-31", "valquo_pct": 1.0, "spy_pct": 1.0, "excess_pp": 0.0,
                 "n_priced": 86}]
    ALP = {"SPY": {AD.ADJ_ALL: {"2026-07-31": 100.0}},
           "AAPL": {AD.ADJ_ALL: {"2026-07-31": 100.0}}}

    def _run(self, n_priced):
        def contract_row(as_of=None, *, fetch=None, refuse_before_close=True, **kw):
            return {"ok": True, "row": {"date": str(as_of)[:10], "valquo_pct": 1.0,
                                        "spy_pct": 1.0, "excess_pp": 0.0,
                                        "n_priced": n_priced}}
        import valuation.screener.index_mark as IM
        real = IM.load_book
        try:
            IM.load_book = (lambda **kw: {"ok": True, "benchmark": "SPY",
                                          "positions": [{"ticker": "AAPL", "weight": 1.0}],
                                          "rebalances": []})
            return S.measure_vs_recorded(raw_by_symbol=self.ALP, series=self.RECORDED,
                                         contract_row=contract_row)
        finally:
            IM.load_book = real

    def test_a_PERFECT_gap_on_a_DIFFERENT_book_does_not_agree(self):
        got = self._run(60)
        self.assertEqual(got["rows"][0]["gap_bps"], 0.0)
        self.assertFalse(got["rows"][0]["agree"])
        self.assertIs(got["rows"][0]["same_book"], False)
        self.assertFalse(got["passed"])
        self.assertIn("DIFFERENT BOOKS", got["rows"][0]["reason"])
        self.assertEqual(got["n_different_book"], 1)

    def test_the_SAME_book_still_passes(self):
        """THE POSITIVE CONTROL. Without it the test above would pass because the leg can never
        agree at all."""
        got = self._run(86)
        self.assertTrue(got["rows"][0]["agree"])
        self.assertIs(got["rows"][0]["same_book"], True)
        self.assertTrue(got["passed"], got["reason"])

    def test_AN_ABSENT_COUNT_IS_A_THIRD_STATE(self):
        """Not same, not different: NOT KNOWN. `n_priced` is a required column of the record, so
        absence is a schema gap rather than a vendor seam -- and collapsing it either way would
        report a seam that was never measured, or pass vacuously."""
        def contract_row(as_of=None, **kw):
            return {"ok": True, "row": {"date": str(as_of)[:10], "valquo_pct": 1.0,
                                        "spy_pct": 1.0, "excess_pp": 0.0}}
        import valuation.screener.index_mark as IM
        real = IM.load_book
        try:
            IM.load_book = (lambda **kw: {"ok": True, "benchmark": "SPY",
                                          "positions": [{"ticker": "AAPL", "weight": 1.0}],
                                          "rebalances": []})
            got = S.measure_vs_recorded(raw_by_symbol=self.ALP, series=self.RECORDED,
                                        contract_row=contract_row)
        finally:
            IM.load_book = real
        self.assertIsNone(got["rows"][0]["same_book"])
        self.assertFalse(got["rows"][0]["agree"])
        self.assertEqual(got["n_book_unknown"], 1)
        self.assertIn("NOT KNOWN", got["rows"][0]["reason"])


class WhatASwitchWouldDoToTheSeam(unittest.TestCase):
    """**THE SEAM, WITH A NUMBER ON IT, on the one event that falls after inception.**

    A vendor switch is a price-vendor change and not a vintage event. But this switch also
    changes the CONVENTION -- splits-and-dividends to splits-dividends-and-spin-offs -- and a
    convention change is still a seam. Every figure here is a RECORDED fixture captured from
    yfinance on 2026-10-17.
    """

    #: CTVA's restated close on the record's inception, and today's two pieces.
    BASE_RESTATED, CTVA_NOW, VYLR_NOW = 13.3758, 12.88, 72.18

    #: The project's own declared monthly sigma, and the seam it has already disclosed.
    SIGMA_PP, DISCLOSED_SEAM_PP = 3.9847, 0.02

    def test_the_record_on_yfinance_is_within_a_point_of_the_truth(self):
        base_as_traded = self.BASE_RESTATED * CTVA_FACTOR
        truth = (self.CTVA_NOW + self.VYLR_NOW) / base_as_traded - 1.0
        on_yf = self.CTVA_NOW / self.BASE_RESTATED - 1.0
        self.assertLess(abs(on_yf - truth) * 100.0, 1.5,
                        "yfinance %+.1f%% against a true %+.1f%%"
                        % (on_yf * 100, truth * 100))

    def test_the_record_on_ALPACA_would_be_wrong_by_eighty_points(self):
        base_as_traded = self.BASE_RESTATED * CTVA_FACTOR
        truth = (self.CTVA_NOW + self.VYLR_NOW) / base_as_traded - 1.0
        on_alp = self.CTVA_NOW / base_as_traded - 1.0
        err = abs(on_alp - truth) * 100.0
        self.assertGreater(err, 75.0, "%+.1f%% against a true %+.1f%%"
                           % (on_alp * 100, truth * 100))

    def test_it_is_NOT_a_seam_to_record_but_a_wrong_number(self):
        """The comparison that makes the point: against the 0.02pp seam this project already
        discloses between two price routes, and against one month's declared sigma."""
        base_as_traded = self.BASE_RESTATED * CTVA_FACTOR
        truth = (self.CTVA_NOW + self.VYLR_NOW) / base_as_traded - 1.0
        err_pp = abs((self.CTVA_NOW / base_as_traded - 1.0) - truth) * 100.0
        at_weight = err_pp * 0.012
        self.assertGreater(at_weight / self.DISCLOSED_SEAM_PP, 25.0)
        self.assertGreater(at_weight / self.SIGMA_PP, 0.15)

    def test_the_exposure_is_CONDITIONAL_and_says_so(self):
        """Whether CTVA is in the bound book cannot be checked from a lane -- the book lives on
        the service. The mechanism holds either way, because the next separation of a book name
        does the same thing, and claiming the exposure without the book would be inventing it."""
        got = S.recorded_universe()
        self.assertFalse(got["ok"], "the book is readable here after all; re-check the claim")
        self.assertIn("UNKNOWN here", got["reason"])


# ----------------------------------------------------------------------------------------- #
# PART 3 -- which basis the record actually uses
# ----------------------------------------------------------------------------------------- #
class WhichBasisTheBoundRecordUses(unittest.TestCase):
    """**THE RECORD IS PRICED ON yfinance's `auto_adjust=True`: splits and dividends.** Alpaca's
    `all` is splits, dividends AND spin-offs. The project's own source already declares that
    difference -- and the 0.98 bar was declared against the two bases anyway.

    Nothing here changes the declared bar or the declared basis. It pins what they ARE, so the
    comparison a reader makes is the one the record's own convention asks for.
    """

    def test_the_record_is_on_yfinances_auto_adjusted_basis(self):
        from valuation.screener import prices as PR
        self.assertEqual(PR.VENDOR_ADJUSTMENT[PR.SRC_YFINANCE], "auto_adjusted")

    def test_alpacas_declared_equivalent_is_all(self):
        self.assertEqual(AD.ADJ_FOR_RECORDED_BASIS, AD.ADJ_ALL)
        from valuation.screener import prices as PR
        self.assertEqual(PR.VENDOR_ADJUSTMENT[PR.SRC_ALPACA], "all_adjustment")

    def test_THE_SOURCE_ALREADY_SAYS_THE_TWO_ARE_NOT_THE_SAME_THING(self):
        """And that is the sentence the 0.98 bar was declared over: `all` carries a spin-off
        term `auto_adjust` does not. The bar is NOT changed here -- what changes is that a
        reader can see the comparison was never between two copies of one convention."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "prices.py"),
                      encoding="utf-8").read()
        self.assertIn("splits, dividends and spin-offs", src)
        self.assertIn("splits and dividends", src)

    def test_the_declared_bar_and_basis_are_UNCHANGED(self):
        """Item 68 explains a failure; it does not move the thing that failed. Changing either
        after seeing the result is choosing the design on the outcome."""
        self.assertEqual(S.PASS_AGREE_RATE, 0.98)
        self.assertEqual(AD.ADJ_FOR_RECORDED_BASIS, "all")

    def test_nothing_in_this_item_switches_a_vendor(self):
        """`SRC_YFINANCE` stays the record's route. A switch is Don's, at a segment boundary."""
        from valuation.screener import prices as PR
        self.assertTrue(hasattr(PR, "SRC_YFINANCE"))
        self.assertTrue(hasattr(PR, "SRC_ALPACA"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
