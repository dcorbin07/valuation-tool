"""
Tests for cold-audit findings LA1 and LA3 (`VALQUO_LIVE_AUDIT.md`).

LA1 — the live hot list's #1 name published a +204% fair value the engine refuses, because the
DCF pass's documented fail-open left NO TRACE: no counter, no log, no key on the row. The row
then read as "no DCF computed yet" and got a peer estimate.

LA3 — `index_track.summarize` annualised on rows recorded rather than trading days elapsed, so a
71%-gapped recorder over-annualised alpha by the ratio of the two and inflated Sharpe by ~sqrt(k).

Pre-registered in `PREREG_la1_la3_repair.md`, committed at `b4c2a1a` before any code moved.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import index_track as IT           # noqa: E402
from valuation.screener import screen as SC                # noqa: E402
from valuation.screener.market_session import (            # noqa: E402
    is_trading_day, trading_days_between)
from valuation.engine.publication import FV_BAND_HIGH      # noqa: E402


# ==========================================================================================
# LA1
# ==========================================================================================

class TestPublicationAuditD1(unittest.TestCase):
    """D1 `asked_but_silent` — the rule that actually catches the LA1 class."""

    def test_ksps_exact_state_is_caught(self):
        """The row as it was actually served on 2026-08-08: rank 1, a peer-estimated
        `blended` fair value, no refusal recorded, and nothing anywhere saying the DCF pass
        had failed on it."""
        rows = [{"ticker": "KSPI", "price": 90.30, "fair_value": None,
                 "fair_value_method": None}]
        out = SC.publication_audit(rows, dcf_window=12)
        self.assertEqual(out["asked_but_silent"], ["KSPI"])
        self.assertFalse(out["clean"])

    def test_a_row_with_a_recorded_error_is_NOT_silent(self):
        """A counted fail-open is a known unknown. The defect was the UNcounted one, so once
        the failure is stamped on the row the detector must stop calling it silent — otherwise
        it fires on every bad upstream day and gets ignored."""
        rows = [{"ticker": "KSPI", "price": 90.30, "fair_value": None,
                 "dcf_error": "HTTPError: 429"}]
        self.assertEqual(SC.publication_audit(rows, dcf_window=12)["asked_but_silent"], [])

    def test_a_recorded_refusal_is_not_silent(self):
        rows = [{"ticker": "KSPI", "price": 90.30, "fair_value": None,
                 "fair_value_withheld": True,
                 "fair_value_withheld_reason": "Cannot value this name: ..."}]
        self.assertEqual(SC.publication_audit(rows, dcf_window=12)["asked_but_silent"], [])

    def test_a_row_with_a_real_dcf_value_is_not_silent(self):
        """Both forms: the SERVED row (method 'dcf') and the SCAN-time row, which carries the
        value but no method yet because `estimate_fair_values` has not run. Testing only one
        of these is how a detector ends up firing on all twelve rows or on none."""
        served = [{"ticker": "SYF", "price": 78.59, "fair_value": 204.375,
                   "fair_value_method": "dcf"}]
        self.assertEqual(SC.publication_audit(served, dcf_window=12)["asked_but_silent"], [])
        scan_time = [{"ticker": "SYF", "price": 78.59, "fair_value": 204.375}]
        self.assertEqual(SC.publication_audit(scan_time, dcf_window=12)["asked_but_silent"], [])

    def test_rows_outside_the_dcf_window_are_not_expected_to_have_one(self):
        """Only the DCF window is ASKED for a value, so only it can be silent. Flagging the
        other ~480 served names would make the detector useless on its first run."""
        rows = [{"ticker": "A", "price": 10.0, "fair_value": None} for _ in range(20)]
        self.assertEqual(SC.publication_audit(rows, dcf_window=3)["asked_but_silent_count"], 3)


class TestPublicationAuditD2(unittest.TestCase):
    """D2 `band_breach` — the invariant the audit says is missing."""

    def test_a_served_row_outside_the_band_and_not_withheld_is_caught(self):
        rows = [{"ticker": "BAD", "price": 10.0, "fair_value": 60.0,
                 "fair_value_method": "blended"}]
        out = SC.publication_audit(rows, dcf_window=0)
        self.assertEqual(out["band_breach_count"], 1)
        self.assertEqual(out["band_breach"][0]["ticker"], "BAD")
        self.assertAlmostEqual(out["band_breach"][0]["ratio"], 6.0)
        self.assertFalse(out["clean"])

    def test_a_withheld_row_is_not_a_breach_however_large_the_model_was(self):
        """A recorded refusal is the system working. Flagging it would punish the fix."""
        rows = [{"ticker": "KSPI", "price": 90.3, "fair_value": None,
                 "fair_value_withheld": True}]
        self.assertEqual(SC.publication_audit(rows, dcf_window=0)["band_breach_count"], 0)

    def test_the_band_boundary_publishes_rather_than_refuses(self):
        """`ratio > band` breaches; `ratio == band` does not. Pinned so the comparison cannot
        silently flip to >=, which would start refusing a value publication.decide allows."""
        rows = [{"ticker": "EDGE", "price": 10.0, "fair_value": 10.0 * FV_BAND_HIGH}]
        self.assertEqual(SC.publication_audit(rows, dcf_window=0)["band_breach_count"], 0)

    def test_D2_WOULD_NOT_HAVE_CAUGHT_KSPI(self):
        """THE POINT OF KEEPING THE TWO RULES SEPARATE, pinned as a test rather than left in
        prose. KSPI's SERVED ratio is 274.13/90.30 = 3.04x — comfortably inside the 5.0 band —
        because the refused 5.6x model was replaced by a plausible-looking peer estimate. A
        reader who takes a green `band_breach` as evidence that the LA1 class cannot recur has
        been misled, and this test fails if anyone ever rewrites the detector on that belief."""
        served = [{"ticker": "KSPI", "price": 90.30, "fair_value": 274.1343244549422,
                   "fair_value_method": "blended"}]
        out = SC.publication_audit(served, dcf_window=12)
        self.assertEqual(out["band_breach_count"], 0, "D2 cannot see this class")
        self.assertLess(274.1343244549422 / 90.30, FV_BAND_HIGH)
        # ...and D1 catches it anyway, which is the whole design. A DCF-window row wearing a
        # PEER method is a row the DCF pass was asked about and answered nothing for.
        self.assertEqual(out["asked_but_silent"], ["KSPI"])
        self.assertFalse(out["clean"])

    def test_the_payload_says_in_words_that_D2_cannot_catch_the_LA1_class(self):
        out = SC.publication_audit([], dcf_window=0)
        self.assertIn("band_breach", out["note"])
        self.assertIn("asked_but_silent", out["note"])


class TestFailOpenIsCounted(unittest.TestCase):
    """The mechanism itself: a swallowed raise must leave a trace."""

    def _patch(self, fn):
        import valuation.engine.pipeline as P
        orig = P.value_ticker
        P.value_ticker = fn
        return orig

    def test_a_raising_engine_is_counted_not_silently_skipped(self):
        import valuation.engine.pipeline as P
        calls = []

        def boom(t, cfg, **kw):
            calls.append(t)
            raise RuntimeError("upstream 429")

        orig = self._patch(boom)
        try:
            rows = [{"ticker": "KSPI", "price": 90.3}]
            errors = SC._enrich_with_dcf(rows, cfg=None)
        finally:
            P.value_ticker = orig
        self.assertIn("KSPI", errors)
        self.assertIn("RuntimeError", errors["KSPI"])
        # FAIL OPEN is unchanged: the row is not blanked and not refused.
        self.assertIsNone(rows[0].get("fair_value"))
        self.assertFalse(rows[0].get("fair_value_withheld"))

    def test_a_transient_failure_is_retried_before_failing_open(self):
        """KSPI is the one name in the top three needing an extra network hop (KZT->USD)
        against a free rate-limited feed. One retry is what that is for."""
        import valuation.engine.pipeline as P
        calls = []

        def boom(t, cfg, **kw):
            calls.append(t)
            raise RuntimeError("transient")

        orig = self._patch(boom)
        try:
            SC._enrich_with_dcf([{"ticker": "KSPI"}], cfg=None)
        finally:
            P.value_ticker = orig
        self.assertEqual(len(calls), SC.DCF_ATTEMPTS)
        self.assertGreaterEqual(SC.DCF_ATTEMPTS, 2)

    def test_a_name_that_succeeds_on_the_retry_is_not_reported_as_an_error(self):
        import valuation.engine.pipeline as P
        from valuation.engine.publication import decide

        state = {"n": 0}

        class _Blend:
            value = None
            withheld_value = 530.23
            growth_led = False

        class _Res:
            fair_value_blend = _Blend()
            base_fair_value = None
            upside = None

            class company:
                price = 94.0
                financial_currency = "USD"
                currency = "USD"
                fx_unresolved = False
                fx_rate = None

        def flaky(t, cfg, **kw):
            state["n"] += 1
            if state["n"] == 1:
                raise RuntimeError("transient")
            return _Res()

        orig = self._patch(flaky)
        try:
            rows = [{"ticker": "KSPI", "price": 94.0}]
            errors = SC._enrich_with_dcf(rows, cfg=None)
        finally:
            P.value_ticker = orig
        self.assertEqual(errors, {})
        # 530.23 / 94.00 = 5.64x -> refused, exactly as the live engine does today.
        self.assertTrue(rows[0]["fair_value_withheld"])
        self.assertIn("5.6x", rows[0]["fair_value_withheld_reason"])
        self.assertGreater(decide(530.23, 94.0).ratio, FV_BAND_HIGH)

    def test_screen_refusals_reports_the_error_count(self):
        import valuation.engine.pipeline as P

        def boom(t, cfg, **kw):
            raise RuntimeError("nope")

        orig = self._patch(boom)
        try:
            out = SC._screen_refusals([{"ticker": "A"}, {"ticker": "B"}], cfg=None, workers=1)
        finally:
            P.value_ticker = orig
        self.assertEqual(out["screened"], 2)
        self.assertEqual(out["errors"], 2)
        self.assertEqual(sorted(out["error_tickers"]), ["A", "B"])

    def test_an_empty_screen_still_reports_the_error_key(self):
        """`screened: 0, refused: 0` with no `errors` key reads as a clean bill of health.
        Callers must always be able to tell those apart."""
        self.assertIn("errors", SC._screen_refusals([], cfg=None))



class TestTheSecondDoorNoDataWithNoException(unittest.TestCase):
    """LA1's second door, found by RE-RUNNING the scan after fixing the first.

    KSPI passed the refusal screen at rank 97 with `errors: 0` and was served a peer estimate
    again, while refusing at 5.6x when asked on its own. Under 8 workers over 488 names against
    a free rate-limited feed the fetch returns PARTIAL DATA rather than raising: `had` is None,
    `publication.decide(None, price)` returns publish=False with an EMPTY reason by design, and
    the row falls through. Counting only exceptions cannot see this.
    """

    class _Blend:
        value = None
        withheld_value = None
        growth_led = False

    def _res(self, revenue):
        blend = self._Blend()

        class _C:
            price = 94.0
            financial_currency = "USD"
            currency = "USD"
            fx_unresolved = False
            fx_rate = None

        _C.revenue = revenue

        class _R:
            fair_value_blend = blend
            base_fair_value = None
            upside = None
            company = _C()
        return _R()

    def _run(self, revenue):
        import valuation.engine.pipeline as P
        orig = P.value_ticker
        P.value_ticker = lambda t, cfg, **kw: self._res(revenue)
        try:
            rows = [{"ticker": "KSPI", "price": 94.0}]
            errs = SC._enrich_with_dcf(rows, cfg=None, refusal_only=True)
        finally:
            P.value_ticker = orig
        return rows[0], errs

    def test_no_statements_is_recorded_as_no_data_and_flagged_unverified(self):
        row, errs = self._run(revenue=None)
        self.assertEqual(errs, {}, "it did not raise — that is the whole problem")
        self.assertEqual(row["dcf_probe"], "no_data")
        out = SC.publication_audit([row], dcf_window=0)
        self.assertEqual(out["unverified"], ["KSPI"])
        self.assertFalse(out["clean"])

    def test_a_name_the_model_simply_cannot_value_is_NOT_flagged(self):
        """An ADR bank with no free cash flow is a legitimate peer-multiple name. Flagging it
        would fire on hundreds of rows and the signal would be ignored within a week."""
        row, _ = self._run(revenue=1.0e10)
        self.assertEqual(row["dcf_probe"], "no_value")
        self.assertEqual(SC.publication_audit([row], dcf_window=0)["unverified"], [])

    def test_a_no_data_row_is_retried_before_being_recorded(self):
        import valuation.engine.pipeline as P
        calls = []
        orig = P.value_ticker

        def counting(t, cfg, **kw):
            calls.append(t)
            return self._res(revenue=None)

        P.value_ticker = counting
        try:
            SC._enrich_with_dcf([{"ticker": "KSPI", "price": 94.0}], cfg=None, refusal_only=True)
        finally:
            P.value_ticker = orig
        self.assertEqual(len(calls), SC.DCF_ATTEMPTS, "a throttled fetch is transient")

    def test_a_refusal_still_wins_over_every_probe_label(self):
        import valuation.engine.pipeline as P
        blend = self._Blend()
        blend.withheld_value = 530.08

        class _C:
            price, revenue = 94.0, 1.0e9
            financial_currency = currency = "USD"
            fx_unresolved, fx_rate = False, None

        class _R:
            fair_value_blend = blend
            base_fair_value = None
            upside = None
            company = _C()

        orig = P.value_ticker
        P.value_ticker = lambda t, cfg, **kw: _R()
        try:
            rows = [{"ticker": "KSPI", "price": 94.0}]
            SC._enrich_with_dcf(rows, cfg=None, refusal_only=True)
        finally:
            P.value_ticker = orig
        self.assertEqual(rows[0]["dcf_probe"], "refused")
        self.assertTrue(rows[0]["fair_value_withheld"])
        self.assertEqual(SC.publication_audit(rows, dcf_window=1)["unverified"], [])

    def test_the_probe_distribution_ships_so_a_bad_feed_day_is_visible(self):
        rows = [{"ticker": "A", "dcf_probe": "valued"},
                {"ticker": "B", "dcf_probe": "no_data"},
                {"ticker": "C", "dcf_probe": "no_data"}]
        out = SC.publication_audit(rows, dcf_window=0)
        self.assertEqual(out["probe"], {"no_data": 2, "valued": 1})



class TestMergeScreen(unittest.TestCase):
    """The mop-up pass must ADD to the first pass's counts, never replace them."""

    def test_counts_add_and_errors_are_not_lost(self):
        a = {"screened": 488, "refused": 3, "errors": 2, "error_tickers": ["A"]}
        b = {"screened": 13, "refused": 1, "errors": 0, "error_tickers": ["B"]}
        out = SC._merge_screen(a, b, no_data_rescreened=13)
        self.assertEqual(out["screened"], 501)
        self.assertEqual(out["refused"], 4)
        self.assertEqual(out["errors"], 2, "a clean second pass cannot erase the first's errors")
        self.assertEqual(out["error_tickers"], ["A", "B"])
        self.assertEqual(out["no_data_rescreened"], 13)

    def test_the_mopup_uses_low_concurrency_because_the_leak_was_our_own_request_rate(self):
        """13 of 500 came back with no statements at 8 workers; all 13 returned data at 2,
        including the refusal this finding is about."""
        self.assertLessEqual(SC.NO_DATA_RETRY_WORKERS, 2)


# ==========================================================================================
# LA3
# ==========================================================================================

def _year(n=252, start=dt.date(2025, 1, 2)):
    d, out = start, []
    while len(out) < n:
        if is_trading_day(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def _series(days, drift_v=0.0006, drift_s=0.0004):
    """Deterministic cumulative-since-inception levels — no RNG, so this pins exactly."""
    out, cv, cs = [], 1.0, 1.0
    for i, day in enumerate(days):
        cv *= (1 + drift_v + 0.0001 * ((i % 7) - 3))
        cs *= (1 + drift_s + 0.0001 * ((i % 5) - 2))
        out.append({"date": day.isoformat(), "valquo": (cv - 1) * 100, "spy": (cs - 1) * 100})
    return out


def _summarize(series, meta):
    orig = IT.load
    IT.load = lambda *a, **k: {"series": series, "meta": meta}
    try:
        return IT.summarize(store=None)
    finally:
        IT.load = orig


class TestElapsedTradingDays(unittest.TestCase):
    def test_a_gapless_series_has_elapsed_equal_to_its_row_count(self):
        """What makes the fix backwards compatible rather than a re-basing of every figure."""
        days = _year(60)
        meta = {"inception_date": (days[0] - dt.timedelta(days=1)).isoformat()}
        self.assertEqual(IT._elapsed_trading_days(_series(days), meta), 60)

    def test_both_definitions_coincide_on_a_gapless_series(self):
        days = _year(60)
        with_inception = IT._elapsed_trading_days(
            _series(days), {"inception_date": (days[0] - dt.timedelta(days=1)).isoformat()})
        without = IT._elapsed_trading_days(_series(days), {})
        self.assertEqual(with_inception, without, 60)

    def test_a_gapped_series_reports_the_elapsed_window_not_the_row_count(self):
        days = _year(252)
        thinned = [r for i, r in enumerate(_series(days)) if i % 3 == 0]
        meta = {"inception_date": (days[0] - dt.timedelta(days=1)).isoformat()}
        self.assertEqual(len(thinned), 84)
        self.assertEqual(IT._elapsed_trading_days(thinned, meta), 250)

    def test_the_elapsed_primitive_agrees_with_track_meters_own_calendar_walk(self):
        """ANTI-DRIFT. `track_meter._trading_days` walks the same calendar to decide which days
        should have a row. Two implementations of that is the two-sources-of-truth class this
        whole audit is about, so they are pinned to agree."""
        from valuation.edge import track_meter as TM
        a, b = dt.date(2025, 1, 2), dt.date(2025, 12, 31)
        self.assertEqual(trading_days_between(a, b, inclusive_start=True),
                         len(TM._trading_days(a, b)))
        self.assertEqual(trading_days_between(a, b, inclusive_start=False),
                         len([d for d in TM._trading_days(a, b) if d > a]))

    def test_a_reversed_or_missing_range_is_zero_not_an_exception(self):
        self.assertEqual(trading_days_between(dt.date(2025, 6, 1), dt.date(2025, 1, 1)), 0)
        self.assertEqual(trading_days_between(None, dt.date(2025, 1, 1)), 0)


class TestAnnualisationDenominator(unittest.TestCase):
    """The audit's own construction: identical final cumulative levels, thinned three ways."""

    def setUp(self):
        self.days = _year(252)
        self.meta = {"inception_date": (self.days[0] - dt.timedelta(days=1)).isoformat(),
                     "benchmark": "SPY"}
        self.full = _series(self.days)

    def _thin(self, k):
        out = [r for i, r in enumerate(self.full) if i % k == 0]
        if out[-1] is not self.full[-1]:
            out.append(self.full[-1])
        return out

    def test_a_gapped_year_annualises_to_the_SAME_alpha_as_the_complete_year(self):
        """THE FINDING. All three end at the same cumulative level over the same elapsed
        window, so the corrected exponent must reproduce the complete series EXACTLY.
        Pre-committed bar: 1e-9."""
        base = _summarize(self.full, self.meta)["live"]["ann_alpha"]
        for k in (2, 3):
            got = _summarize(self._thin(k), self.meta)["live"]["ann_alpha"]
            self.assertAlmostEqual(got, base, delta=1e-9, msg=f"thinning 1-in-{k}")

    def test_the_old_row_count_denominator_would_have_failed_this(self):
        """Proves the test has teeth: the pre-fix arithmetic on the same thinned series."""
        thin = self._thin(3)
        cum_v, cum_s = thin[-1]["valquo"], thin[-1]["spy"]
        old = ((1 + cum_v / 100) ** (IT.TRADING_DAYS / len(thin)) - 1) - \
              ((1 + cum_s / 100) ** (IT.TRADING_DAYS / len(thin)) - 1)
        base = _summarize(self.full, self.meta)["live"]["ann_alpha"]
        self.assertGreater(abs(old - base), 0.10, "old denominator inflates by >10pp here")

    def test_the_complete_series_is_unchanged_by_the_fix(self):
        """No published figure moves on a track that was recorded properly."""
        live = _summarize(self.full, self.meta)["live"]
        cum_v, cum_s = self.full[-1]["valquo"], self.full[-1]["spy"]
        old = ((1 + cum_v / 100) ** (IT.TRADING_DAYS / 252) - 1) - \
              ((1 + cum_s / 100) ** (IT.TRADING_DAYS / 252) - 1)
        self.assertAlmostEqual(live["ann_alpha"], old, delta=1e-12)

    def test_coverage_and_elapsed_ship_beside_the_figures(self):
        live = _summarize(self._thin(3), self.meta)["live"]
        self.assertEqual(live["days"], 85)
        self.assertEqual(live["elapsed_trading_days"], 252)
        self.assertAlmostEqual(live["coverage"], 85 / 252, places=6)


def _noisy_series(days, seed=11):
    """A seeded pseudo-random walk. The deterministic ramp in `_series` has almost no
    dispersion, so its excess Sharpe blows past MAX_PLAUSIBLE_SHARPE and is suppressed -
    which makes it useless for testing the Sharpe path."""
    import random
    rng = random.Random(seed)
    out, cv, cs = [], 1.0, 1.0
    for day in days:
        cv *= (1 + rng.gauss(0.0006, 0.010))
        cs *= (1 + rng.gauss(0.0004, 0.009))
        out.append({"date": day.isoformat(), "valquo": (cv - 1) * 100, "spy": (cs - 1) * 100})
    return out


class TestSharpeDenominator(unittest.TestCase):
    def setUp(self):
        self.days = _year(252)
        self.meta = {"inception_date": (self.days[0] - dt.timedelta(days=1)).isoformat()}
        self.full = _noisy_series(self.days)

    def test_a_half_recorded_year_is_corrected_not_inflated(self):
        thin = [r for i, r in enumerate(self.full) if i % 2 == 0]
        base = _summarize(self.full, self.meta)["live"]["sharpe"]
        got = _summarize(thin, self.meta)["live"]["sharpe"]
        self.assertIsNotNone(got)
        self.assertLessEqual(abs(got - base), 0.15, "pre-committed bar")

    def test_below_the_coverage_floor_the_sharpe_is_WITHHELD_with_a_reason(self):
        thin = [r for i, r in enumerate(self.full) if i % 3 == 0]
        live = _summarize(thin, self.meta)["live"]
        self.assertIsNone(live["sharpe"])
        self.assertIn("recorded", live["sharpe_withheld_reason"])
        self.assertLess(live["coverage"], IT.MIN_COVERAGE_FOR_SHARPE)

    def test_the_coverage_floor_is_the_pre_committed_constant(self):
        self.assertEqual(IT.MIN_COVERAGE_FOR_SHARPE, 0.5)

    def test_a_complete_series_sharpe_is_unchanged_by_the_fix(self):
        live = _summarize(self.full, self.meta)["live"]
        rv = IT._daily_returns(self.full, "valquo")
        rs = IT._daily_returns(self.full, "spy")
        ex = [a - b for a, b in zip(rv, rs)]
        old = (sum(ex) / len(ex)) / IT._stdev(ex) * (IT.TRADING_DAYS ** 0.5)
        self.assertAlmostEqual(live["sharpe"], old, delta=1e-9)


class TestTheGateStaysOnRecordedRows(unittest.TestCase):
    """The deliberate non-change, and the one that protects the public posture."""

    def test_a_gappy_track_does_not_reach_the_live_floor_early(self):
        """Moving MIN_LIVE_DAYS onto elapsed time would let a track with 30 recorded rows over
        60 elapsed days call itself 60 days old — the flattering direction, advancing the
        'backtested -> live' posture on the strength of days nobody recorded."""
        days = _year(120)
        full = _series(days)
        thin = [r for i, r in enumerate(full) if i % 2 == 0]      # 60 rows, 120 elapsed
        meta = {"inception_date": (days[0] - dt.timedelta(days=1)).isoformat()}
        out = _summarize(thin, meta)
        self.assertEqual(out["days"], 60)
        self.assertEqual(out["live"]["elapsed_trading_days"], 119)
        self.assertGreaterEqual(out["days"], IT.MIN_LIVE_DAYS)
        # ...and the headline is STILL backtested, because the contract gate has not passed.
        self.assertEqual(out["headline"], "backtested")

    def test_annualisation_is_withheld_below_the_row_gate_however_long_the_window(self):
        days = _year(252)
        full = _series(days)
        thin = [r for i, r in enumerate(full) if i % 20 == 0]     # 13 rows over a year
        meta = {"inception_date": (days[0] - dt.timedelta(days=1)).isoformat()}
        live = _summarize(thin, meta)["live"]
        self.assertLess(live["days"], IT.MIN_LIVE_DAYS)
        self.assertIsNone(live["ann_alpha"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
