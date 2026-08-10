"""
Tests for `scripts/live_cache.py` — the rate-limit-tolerant live-input cache.

NONE OF THESE TOUCH THE NETWORK. Every vendor call is injected, which is the same discipline
`tests/test_engine.py` uses for the beta estimator: a throttled machine must not be able to turn
this suite green or red by accident. That matters more here than usual, because the thing under
test IS the throttle handling.

The load-bearing tests, in the order they would catch a real regression:
  * the tz-alignment test — without it, batching silently disables corroboration everywhere;
  * the tri-state tests — a failed fetch must never become durable, or coverage inflates on a
    quota outage, which is exactly how run 2 produced numbers it had to withdraw;
  * the circuit-breaker test — the run must stop, not grind on with degraded data.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import live_cache as LC


def _series(n=60, start="2021-09-01", tz=None, base=100.0, step=1.0):
    import pandas as pd
    idx = pd.date_range(start=start, periods=n, freq="MS", tz=tz)
    return pd.Series([base + step * i for i in range(n)], index=idx)


class TmpRoot(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="livecache_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _pin(self, tickers):
        LC._atomic_write_json(os.path.join(self.root, "universe.json"),
                              {"captured_at": "2026-08-10T00:00:00", "scan_date": "2026-08-08",
                               "n_rows": len(tickers), "tickers": list(tickers),
                               "universe_size": 800, "history": []})

    def _snapshot(self, rows, scan_date="2026-08-08"):
        LC._atomic_write_json(os.path.join(self.root, "snapshot_%s.json" % scan_date),
                              {"scan_date": scan_date, "rows": rows})


# ------------------------------------------------------------------ the silent trap
class TestIndexAlignment(TmpRoot):
    def test_a_naive_batched_index_is_aligned_to_the_market_tz(self):
        """THE test. A tz-naive batch intersects a tz-aware market in ZERO months."""
        import pandas as pd
        mkt = _series(tz="America/New_York")
        naive = _series(tz=None)
        self.assertEqual(len(naive.index.intersection(mkt.index)), 0,
                         "premise: a naive index must not intersect an aware one")
        fixed = LC._align_index(naive, mkt.index.tz)
        self.assertEqual(len(fixed.index.intersection(mkt.index)), len(mkt),
                         "after alignment every month must pair")
        self.assertIsNotNone(fixed.index.tz)

    def test_alignment_is_a_no_op_when_the_tz_already_matches(self):
        aware = _series(tz="America/New_York")
        out = LC._align_index(aware, aware.index.tz)
        self.assertTrue(out.equals(aware))

    def test_an_unaligned_series_makes_compute_beta_report_unavailable(self):
        """Proves the failure is SILENT: no exception, just `unavailable` — which the ladder
        answers by keeping the vendor beta. Nothing surfaces it."""
        from valuation.data.beta import compute_beta
        import valuation.data.beta as B
        mkt = _series(tz="America/New_York")
        saved = dict(B._MKT)
        try:
            B._MKT.update(returns=mkt.pct_change().dropna(), ts=9e18)
            est = compute_beta("X", closes=_series(tz=None))
            self.assertTrue(est.unavailable)
            self.assertEqual(est.n_observations, 0)
        finally:
            B._MKT.update(saved)


# ------------------------------------------------------------------ the tri-state rule
class TestManifest(TmpRoot):
    def test_a_failed_status_cannot_be_recorded(self):
        man = LC.Manifest(self.root)
        for bad in ("throttled", "failed", "pending", "partial"):
            with self.assertRaises(ValueError):
                man.mark("AAPL", "closes", bad)
        self.assertFalse(man.done("AAPL", "closes"))

    def test_terminal_statuses_persist_and_are_skipped_on_resume(self):
        man = LC.Manifest(self.root)
        man.mark("AAPL", "closes", "complete", n=60)
        man.mark("ZZZZ", "closes", "no_data", n=0)
        again = LC.Manifest(self.root)
        self.assertTrue(again.done("AAPL", "closes"))
        self.assertTrue(again.done("ZZZZ", "closes"))
        self.assertFalse(again.done("MSFT", "closes"))

    def test_the_manifest_is_saved_after_every_unit_not_at_the_end(self):
        man = LC.Manifest(self.root)
        man.mark("AAPL", "closes", "complete", n=60)
        on_disk = LC._read_json(man.path)
        self.assertIn("AAPL", on_disk)

    def test_a_corrupt_manifest_degrades_to_empty_rather_than_crashing(self):
        with open(os.path.join(self.root, "manifest.json"), "w") as f:
            f.write("{not json")
        self.assertEqual(LC.Manifest(self.root).data, {})


class TestSerialisationRoundTrip(TmpRoot):
    """Found by these tests, not by inspection: five years of monthly closes straddle several
    DST changes, so a naive `str(timestamp)` round trip emits mixed UTC offsets and pandas
    refuses to parse the list back. The cache would not survive its own round trip, and the
    symptom would have surfaced as an unexplained coverage hole."""

    def test_a_tz_aware_index_survives_a_dst_straddling_round_trip(self):
        s = _series(n=60, tz="America/New_York")
        offsets = {i.utcoffset() for i in s.index}
        self.assertGreater(len(offsets), 1, "premise: this window must straddle a DST change")
        back = LC._json_to_series(LC._series_to_json(s))
        self.assertTrue(back.index.equals(s.index))
        self.assertEqual(list(back.values), list(s.values))

    def test_the_reconstructed_index_still_intersects_the_market(self):
        mkt = _series(n=60, tz="America/New_York")
        back = LC._json_to_series(LC._series_to_json(mkt))
        self.assertEqual(len(back.index.intersection(mkt.index)), len(mkt))

    def test_a_naive_index_round_trips_unchanged(self):
        s = _series(n=12, tz=None)
        back = LC._json_to_series(LC._series_to_json(s))
        self.assertTrue(back.index.equals(s.index))


class TestAtomicWrite(TmpRoot):
    def test_no_tmp_file_survives_a_successful_write(self):
        p = os.path.join(self.root, "x", "y.json")
        LC._atomic_write_json(p, {"a": 1})
        self.assertTrue(os.path.exists(p))
        self.assertFalse(os.path.exists(p + ".tmp"))
        self.assertEqual(LC._read_json(p), {"a": 1})


# ------------------------------------------------------------------ throttle handling
class TestThrottleDetection(unittest.TestCase):
    def test_rate_limit_messages_are_recognised(self):
        for msg in ["Rate limited", "HTTP 429", "Too Many Requests", "quota exceeded",
                    "YFRateLimitError: rate limit"]:
            self.assertTrue(LC.is_throttle(Exception(msg)), msg)

    def test_ordinary_failures_are_not_mistaken_for_throttling(self):
        for msg in ["no data found", "symbol may be delisted", "connection reset"]:
            self.assertFalse(LC.is_throttle(Exception(msg)), msg)


class TestGuard(unittest.TestCase):
    def test_the_breaker_trips_at_the_budget(self):
        g = LC.Guard(min_interval=0, jitter=0, budget=3, sleep=lambda s: None)
        for _ in range(2):
            g.note_throttle(0)
        self.assertFalse(g.tripped)
        g.note_throttle(0)
        self.assertTrue(g.tripped)

    def test_backoff_grows_and_is_capped(self):
        g = LC.Guard(budget=99, sleep=lambda s: None)
        a, b = g.note_throttle(0), g.note_throttle(1)
        self.assertGreater(b, a)
        self.assertLessEqual(g.note_throttle(50), LC.BACKOFF_MAX_S)

    def test_pacing_actually_sleeps_between_calls(self):
        slept = []
        g = LC.Guard(min_interval=2.0, jitter=0.0, sleep=slept.append)
        g.wait()
        g.wait()
        self.assertTrue(any(s > 0 for s in slept), "second call must be paced")


class TestFetchClosesResumeAndThrottle(TmpRoot):
    def setUp(self):
        super().setUp()
        LC._atomic_write_json(LC.market_path(self.root),
                              LC._series_to_json(_series(tz="America/New_York")))

    def _guard(self, budget=5):
        return LC.Guard(min_interval=0, jitter=0, budget=budget, sleep=lambda s: None)

    def test_a_throttled_batch_records_nothing_and_is_retried(self):
        man = LC.Manifest(self.root)

        def always_throttled(batch):
            raise Exception("Rate limited. Too Many Requests")

        stats = LC.fetch_closes(["AAA", "BBB"], self.root, man, self._guard(budget=2),
                                downloader=always_throttled)
        self.assertEqual(stats["complete"], 0)
        self.assertEqual(LC.Manifest(self.root).data, {},
                         "a throttled batch must leave the ledger untouched")
        # ...and a later healthy run picks the same names up.
        ok = LC.fetch_closes(["AAA", "BBB"], self.root, LC.Manifest(self.root), self._guard(),
                             downloader=lambda b: {t: _series(tz=None) for t in b})
        self.assertEqual(ok["complete"], 2)

    def test_the_breaker_stops_the_run_rather_than_grinding_on(self):
        seen = []

        def throttling(batch):
            seen.append(list(batch))
            raise Exception("429 rate limit")

        g = self._guard(budget=2)
        LC.fetch_closes([str(i) for i in range(200)], self.root, LC.Manifest(self.root), g,
                        batch_size=10, downloader=throttling)
        self.assertTrue(g.tripped)
        self.assertLess(len(seen), 20, "must abort, not walk the whole universe")

    def test_completed_names_are_skipped_on_the_next_run(self):
        man = LC.Manifest(self.root)
        LC.fetch_closes(["AAA"], self.root, man, self._guard(),
                        downloader=lambda b: {t: _series(tz=None) for t in b})
        asked = []

        def spy(batch):
            asked.extend(batch)
            return {t: _series(tz=None) for t in batch}

        LC.fetch_closes(["AAA", "BBB"], self.root, LC.Manifest(self.root), self._guard(),
                        downloader=spy)
        self.assertEqual(asked, ["BBB"], "a cached name must not be refetched")

    def test_a_name_the_vendor_genuinely_lacks_is_durable(self):
        man = LC.Manifest(self.root)
        LC.fetch_closes(["AAA", "GONE"], self.root, man, self._guard(),
                        downloader=lambda b: {"AAA": _series(tz=None)})
        self.assertEqual(man.status("GONE", "closes"), "no_data")
        self.assertEqual(man.status("AAA", "closes"), "complete")

    def test_cached_closes_are_written_aligned(self):
        LC.fetch_closes(["AAA"], self.root, LC.Manifest(self.root), self._guard(),
                        downloader=lambda b: {t: _series(tz=None) for t in b})
        s = LC.load_closes(self.root, "AAA")
        self.assertIsNotNone(s)
        self.assertIsNotNone(s.index.tz, "must be stored aligned to the market tz")


class TestFetchVendor(TmpRoot):
    def test_a_throttled_name_is_left_unrecorded(self):
        man = LC.Manifest(self.root)

        def throttled(t):
            raise Exception("rate limit")

        LC.fetch_vendor(["AAA"], self.root, man,
                        LC.Guard(min_interval=0, jitter=0, budget=2, sleep=lambda s: None),
                        getter=throttled)
        self.assertFalse(LC.Manifest(self.root).done("AAA", "vendor"))

    def test_a_missing_vendor_beta_is_still_a_complete_fetch(self):
        """`beta` absent from a payload that ARRIVED is a fact about the company. `beta` absent
        because the call failed is not. The ladder's whole design rests on the distinction."""
        man = LC.Manifest(self.root)
        LC.fetch_vendor(["AAA"], self.root, man,
                        LC.Guard(min_interval=0, jitter=0, sleep=lambda s: None),
                        getter=lambda t: (None, True))
        self.assertTrue(man.done("AAA", "vendor"))
        self.assertIsNone(LC._read_json(LC.vendor_path(self.root, "AAA"))["beta"])

    def test_an_empty_payload_is_treated_as_a_failed_fetch(self):
        man = LC.Manifest(self.root)
        LC.fetch_vendor(["AAA"], self.root, man,
                        LC.Guard(min_interval=0, jitter=0, sleep=lambda s: None),
                        getter=lambda t: (None, False))
        self.assertFalse(man.done("AAA", "vendor"))


# ------------------------------------------------------------------ the offline report
class TestOfflineReport(TmpRoot):
    def setUp(self):
        super().setUp()
        import numpy as np
        import pandas as pd
        rng = np.random.RandomState(7)
        idx = pd.date_range("2021-09-01", periods=60, freq="MS", tz="America/New_York")
        mr = rng.normal(0.008, 0.04, 60)
        self.mkt = pd.Series(100.0 * np.cumprod(1 + mr), index=idx)
        LC._atomic_write_json(LC.market_path(self.root), LC._series_to_json(self.mkt))
        self.rng = rng

    def _plant(self, ticker, beta, vendor):
        """A close series whose true beta is `beta`, plus a cached vendor field."""
        import numpy as np
        import pandas as pd
        mr = self.mkt.pct_change().dropna()
        r = beta * mr + self.rng.normal(0, 0.001, len(mr))
        lv = [100.0]
        for x in r:
            lv.append(lv[-1] * (1 + x))
        s = pd.Series(lv, index=self.mkt.index)
        LC._atomic_write_json(LC.closes_path(self.root, ticker), LC._series_to_json(s))
        LC._atomic_write_json(LC.vendor_path(self.root, ticker),
                              {"ticker": ticker, "beta": vendor})
        man = LC.Manifest(self.root)
        man.mark(ticker, "closes", "complete", n=len(s))
        man.mark(ticker, "vendor", "complete", beta=vendor)

    def test_the_report_makes_no_network_calls(self):
        """Injects a compute_beta that fails loudly if the network path is reached."""
        self._pin(["AAA"])
        self._snapshot([{"ticker": "AAA", "extra": {"factors": {"quality": 1.0}}}])
        self._plant("AAA", 1.2, 1.2)
        import valuation.data.beta as B
        real = B.compute_beta

        def tripwire(ticker, closes=None):
            if closes is None:
                raise AssertionError("report made a network call")
            return real(ticker, closes=closes)

        B.compute_beta = tripwire
        try:
            payload = LC.report(self.root)
        finally:
            B.compute_beta = real
        self.assertEqual(payload["network_calls"], 0)
        self.assertEqual(payload["universe"]["n_covered"], 1)

    def test_the_real_ladder_is_driven_and_rungs_are_counted(self):
        self._pin(["HIGH", "LOWLONG", "NOVENDOR"])
        self._snapshot([{"ticker": t, "extra": {"factors": {}}} for t in
                        ("HIGH", "LOWLONG", "NOVENDOR")])
        self._plant("HIGH", 1.2, 1.2)          # ordinary vendor beta -> accepted untouched
        self._plant("LOWLONG", 0.2, 0.2)       # low but 59 months of history -> corroborated
        self._plant("NOVENDOR", 0.9, None)     # no vendor field -> computed from own prices
        out = LC.resolve_all(self.root, ["HIGH", "LOWLONG", "NOVENDOR"])
        by = {r["ticker"]: r["rung"] for r in out["rows"]}
        self.assertEqual(by["HIGH"], "vendor")
        self.assertEqual(by["LOWLONG"], "vendor_corroborated")
        self.assertEqual(by["NOVENDOR"], "computed")

    def test_cached_closes_reproduce_the_estimator_exactly(self):
        """B1, do-no-harm: feeding the cache must equal feeding the vendor directly."""
        self._plant("AAA", 0.77, 0.77)
        import valuation.data.beta as B
        s = LC.load_closes(self.root, "AAA")
        with LC.offline_beta(self.root):
            via_cache = B.compute_beta("AAA")
        saved = dict(B._MKT)
        try:
            B._MKT.update(returns=self.mkt.pct_change().dropna(), ts=9e18)
            direct = B.compute_beta("AAA", closes=s)
        finally:
            B._MKT.update(saved)
        self.assertAlmostEqual(via_cache.value, direct.value, places=12)
        self.assertEqual(via_cache.n_observations, direct.n_observations)

    def test_compute_beta_is_restored_after_the_context_exits(self):
        import valuation.data.beta as B
        before = B.compute_beta
        with LC.offline_beta(self.root):
            self.assertIsNot(B.compute_beta, before)
        self.assertIs(B.compute_beta, before)

    def test_coverage_counts_only_names_the_ladder_can_run_on(self):
        self._pin(["FULL", "CLOSESONLY", "VENDORONLY", "NOTHING"])
        self._snapshot([])
        self._plant("FULL", 1.0, 1.0)
        LC._atomic_write_json(LC.closes_path(self.root, "CLOSESONLY"),
                              LC._series_to_json(self.mkt))
        LC._atomic_write_json(LC.vendor_path(self.root, "VENDORONLY"),
                              {"ticker": "VENDORONLY", "beta": 1.0})
        cov = LC.coverage(self.root)
        self.assertEqual(cov["n_served"], 4)
        self.assertEqual(cov["covered"], ["FULL"])
        self.assertEqual(cov["n_covered"], 1)

    def test_a_name_the_vendor_lacks_history_for_still_counts_as_covered(self):
        """`no_data` is an answer. The ladder runs and lands on a rung; that is coverage."""
        self._pin(["GONE"])
        self._snapshot([])
        LC._atomic_write_json(LC.vendor_path(self.root, "GONE"), {"ticker": "GONE", "beta": None})
        man = LC.Manifest(self.root)
        man.mark("GONE", "vendor", "complete", beta=None)
        man.mark("GONE", "closes", "no_data", n=0)
        self.assertEqual(LC.coverage(self.root)["n_covered"], 1)

    def test_coverage_cannot_be_inflated_by_a_throttled_run(self):
        """B2. Names whose fetch was throttled leave no trace, so they cannot be counted."""
        self._pin(["AAA", "BBB", "CCC"])
        self._snapshot([])
        self._plant("AAA", 1.0, 1.0)
        LC.fetch_closes(["BBB", "CCC"], self.root, LC.Manifest(self.root),
                        LC.Guard(min_interval=0, jitter=0, budget=1, sleep=lambda s: None),
                        downloader=lambda b: (_ for _ in ()).throw(Exception("429 rate limit")))
        self.assertEqual(LC.coverage(self.root)["n_covered"], 1)


class TestThemeCoverage(TmpRoot):
    def test_a_theme_null_on_every_row_reports_zero_coverage(self):
        self._pin(["A", "B"])
        self._snapshot([
            {"ticker": "A", "extra": {"factors": {"quality": 1.0, "institutional": None}}},
            {"ticker": "B", "extra": {"factors": {"quality": 2.0, "institutional": None}}},
        ])
        t = LC.theme_coverage(self.root)
        self.assertEqual(t["themes"]["quality"]["coverage"], 1.0)
        self.assertEqual(t["themes"]["institutional"]["n_non_null"], 0)
        self.assertEqual(t["themes"]["institutional"]["coverage"], 0.0)

    def test_the_render_names_a_never_populated_theme_explicitly(self):
        self._pin(["A"])
        self._snapshot([{"ticker": "A", "extra": {"factors": {"quality": 1.0,
                                                              "sentiment": None}}}])
        text = LC.render(LC.report(self.root))
        self.assertIn("ABSENT", text)

    def test_a_constant_theme_is_flagged_despite_reading_as_fully_covered(self):
        """The live case: `insider` is 100% non-null on 500 served rows with ONE distinct
        value. Counting non-nulls alone reports it as the best-covered theme in the product."""
        self._pin(["A", "B", "C"])
        self._snapshot([{"ticker": t, "extra": {"factors": {"insider": 0.0,
                                                            "quality": float(i)}}}
                        for i, t in enumerate("ABC")])
        cov = LC.theme_coverage(self.root)
        self.assertEqual(cov["themes"]["insider"]["coverage"], 1.0)
        self.assertEqual(cov["themes"]["insider"]["n_distinct"], 1)
        self.assertTrue(cov["themes"]["insider"]["degenerate"])
        self.assertFalse(cov["themes"]["quality"]["degenerate"])
        text = LC.render(LC.report(self.root))
        self.assertIn("CONSTANT", text)
        self.assertIn("contributing nothing", text)

    def test_the_render_does_not_emit_a_literal_double_percent(self):
        self._pin(["A"])
        self._snapshot([{"ticker": "A", "extra": {"factors": {"quality": 1.0}}}])
        self.assertNotIn("%%", LC.render(LC.report(self.root)))


class TestSeedStore(TmpRoot):
    def test_captured_rows_are_written_through_the_projects_own_writer(self):
        """Replayed through `Store.save_snapshot`, so the meter reads real rows through the
        loader it already used — no second schema to drift."""
        from valuation.screener.store import Store
        self._snapshot([{"ticker": "AAA", "composite": 1.0,
                         "extra": {"factors": {"quality": 1.0, "institutional": None}}},
                        {"ticker": "BBB", "composite": 0.5,
                         "extra": {"factors": {"quality": 2.0, "institutional": None}}}])
        db = os.path.join(self.root, "served.db")
        out = LC.seed_store(self.root, db)
        self.assertEqual(out["n_rows"], 2)
        self.assertEqual(out["dates"], ["2026-08-08"])
        rows = Store(db).load_snapshot("2026-08-08")
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["ticker"] for r in rows}, {"AAA", "BBB"})

    def test_seeding_never_touches_the_real_screener_db(self):
        """The real store carries another lane's 2099-01-01 fixture; entangling the captured
        production record with it would make two bugs one."""
        self._snapshot([{"ticker": "AAA", "extra": {"factors": {}}}])
        out = LC.seed_store(self.root, None)
        self.assertTrue(out["db"].startswith(self.root))
        self.assertNotIn("screener.db", out["db"])

    def test_seeding_is_idempotent_and_carries_no_snapshot_when_none_captured(self):
        out = LC.seed_store(self.root, os.path.join(self.root, "s.db"))
        self.assertEqual(out["n_rows"], 0)
        self.assertEqual(out["dates"], [])


class TestCapture(TmpRoot):
    def test_capture_pins_the_denominator_before_any_fetch(self):
        payload = {"scan_date": "2026-08-08", "universe_size": 800, "provider": "FMP",
                   "history": ["2026-08-08", "2026-08-07"],
                   "rows": [{"ticker": "AAA", "extra": {"factors": {"quality": 1.0}}},
                            {"ticker": "BBB", "extra": {"factors": {"quality": 2.0}}}]}
        out = LC.capture(self.root, opener=lambda u: json.dumps(payload))
        self.assertEqual(out["tickers"], ["AAA", "BBB"])
        self.assertEqual(out["n_rows"], 2)
        pinned = LC.load_universe(self.root)
        self.assertEqual(pinned["scan_date"], "2026-08-08")
        self.assertTrue(os.path.exists(os.path.join(self.root, "snapshot_2026-08-08.json")))

    def test_status_reports_progress_against_the_pinned_universe(self):
        self._pin(["AAA", "BBB"])
        man = LC.Manifest(self.root)
        man.mark("AAA", "closes", "complete", n=60)
        st = LC.status(self.root)
        self.assertEqual(st["n_served"], 2)
        self.assertEqual(st["closes_done"], 1)
        self.assertEqual(st["vendor_done"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
