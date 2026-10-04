"""ITEM 30 — THE LIVE CHECKER'S VERDICT LOGIC, WITH THE NETWORK BLOCKED.

**THIS SUITE MUST NEVER REACH valquo.co, AND THAT IS NOT A STYLE PREFERENCE.** The gate runs
every suite on every land; a suite that called the live site would make the land depend on the
site being up, so a deploy outage would read as a code failure and a code failure could be
dismissed as an outage. Worse, the checker's whole value is that it is the ONLY thing that talks
to production — if its own tests did too, a green suite would stop meaning the logic is right.

So `live_check.fetch` is replaced outright and `urllib.request.urlopen` is blocked, with a test
that the block bites. What is under test is the VERDICT: given a payload, does the checker call it
a pass or a fail, and does the process exit non-zero.

WHAT THESE PIN, each one a way this class of checker goes wrong:

  * **A SKIP IS NEVER A PASS.** Counted separately, and the exit code ignores it. The opposite
    convention is how `/api/signals` would quietly stop being checked every weekend.
  * **AN EXPORT IS JUDGED BY ITS MAGIC BYTES.** This app answers `200` with a JSON error body
    when an export fails, and a JSON error is "non-empty" — so a length check would pass on a
    broken export. Driven with exactly that payload.
  * **A NOT-FOUND TICKER IS JUDGED BY ITS STATUS.** The defect was a `200` carrying a score of 40
    and a recommendation of "Reduce" for a company nobody identified, so a checker that only
    looked for an error key would have passed it.
  * **THE TWO ALERT SURFACES ARE COMPARED TO EACH OTHER**, not to a number typed into the
    checker. They disagreed by exactly the 8 rows one of them was mis-classifying, and a
    hard-coded 15 would have gone stale the first time a real alert closed.
  * **FRESHNESS COMES FROM THE MARKET CALENDAR**, so it does not fail on a holiday.

    python tests/test_live_check.py
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.


def _load():
    """Import `scripts/live_check.py` by path — it is a script, not a package module."""
    p = os.path.join(REPO, "scripts", "live_check.py")
    spec = importlib.util.spec_from_file_location("live_check_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LC = _load()

SESSION = _dt.date(2026, 10, 2)

GOOD_HOT = {"scan_date": "2026-10-02", "rows": [{"ticker": "A"}] * 100,
            "health": {"theme_contributing": {"institutional": 0.9, "insider": 0.8,
                                              "capital_discipline": 0.96}}}


class _Net:
    """Replaces `live_check.fetch` with a table, and blocks the transport underneath it."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def __enter__(self):
        self._fetch = LC.fetch
        import urllib.request
        self._urlopen = urllib.request.urlopen
        self._build = urllib.request.build_opener

        def _no_net(*a, **k):
            raise AssertionError("this suite must not touch the network")

        urllib.request.urlopen = _no_net
        urllib.request.build_opener = _no_net
        self._ur = urllib.request

        def fake(base, path, *, method="GET", body=None, timeout=240):
            key = (method, path.split("?")[0]) if method != "POST" else \
                  (method, path, json.dumps(body, sort_keys=True))
            self.calls.append(key)
            for k, v in self.table.items():
                if k == key or (len(k) == 2 and k == (method, path.split("?")[0])):
                    return v
            return 404, b"{}", "application/json"

        LC.fetch = fake
        return self

    def __exit__(self, *exc):
        LC.fetch = self._fetch
        self._ur.urlopen = self._urlopen
        self._ur.build_opener = self._build
        return False


def _j(obj, code=200):
    return code, json.dumps(obj).encode("utf-8"), "application/json"


class TheNetworkIsBlocked(unittest.TestCase):
    def test_the_block_bites(self):
        with _Net({}):
            import urllib.request
            with self.assertRaises(AssertionError):
                urllib.request.urlopen("https://valquo.co/")

    def test_and_is_restored(self):
        """A harness that left urllib broken would poison every later suite in the process."""
        with _Net({}):
            pass
        import urllib.request
        self.assertNotEqual(getattr(urllib.request.urlopen, "__name__", ""), "_no_net")


class ASkipIsNeverAPass(unittest.TestCase):
    def test_counts_are_separate(self):
        rep = LC.Report()
        rep.ok("a", "1")
        rep.skip("b", "why")
        rep.bad("c", "2")
        self.assertEqual((rep.passed, rep.failed, rep.skipped), (1, 1, 1))

    def test_a_skip_alone_does_not_fail_the_run(self):
        rep = LC.Report()
        rep.ok("a", "1")
        rep.skip("b", "why")
        self.assertEqual(rep.finish(), 0)

    def test_one_fail_fails_the_run(self):
        rep = LC.Report()
        for _ in range(20):
            rep.ok("a", "1")
        rep.bad("b", "2")
        self.assertEqual(rep.finish(), 1)


class TheHotListChecks(unittest.TestCase):
    def test_a_fresh_list_with_live_themes_passes(self):
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(GOOD_HOT)}):
            LC.check_hot_list("https://x", rep, SESSION)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.passed, 5)

    def test_a_stale_scan_date_fails(self):
        d = dict(GOOD_HOT, scan_date="2026-09-25")
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(d)}):
            LC.check_hot_list("https://x", rep, SESSION)
        self.assertTrue(any("FAIL" in ln and "fresh" in ln for ln in rep.lines), rep.lines)

    def test_a_dead_theme_fails_and_names_the_number(self):
        """THE LIVE STATE ON 2026-10-04: institutional and insider both 0.00."""
        d = json.loads(json.dumps(GOOD_HOT))
        d["health"]["theme_contributing"]["institutional"] = 0.0
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(d)}):
            LC.check_hot_list("https://x", rep, SESSION)
        line = [ln for ln in rep.lines if "institutional" in ln][0]
        self.assertIn("FAIL", line)
        self.assertIn("0.00", line, "the number must be on the line, pass or fail")

    def test_a_missing_theme_fails_rather_than_passing_on_None(self):
        """A theme the payload omits is not a theme that is contributing."""
        d = json.loads(json.dumps(GOOD_HOT))
        del d["health"]["theme_contributing"]["insider"]
        rep = LC.Report()
        with _Net({("GET", "/api/hotstocks"): _j(d)}):
            LC.check_hot_list("https://x", rep, SESSION)
        self.assertTrue(any("FAIL" in ln and "insider" in ln for ln in rep.lines), rep.lines)


class TheDipChecks(unittest.TestCase):
    def test_measuring_every_eligible_name_passes(self):
        rep = LC.Report()
        with _Net({("GET", "/api/dip"): _j({"n_eligible": 242, "n_measured": 242,
                                            "n_unmeasured": 0, "rows": [{"t": 1}]})}):
            LC.check_dip("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_the_live_shortfall_fails_and_prints_both_numbers(self):
        """THE LIVE STATE: 12 of 242 measured, 230 capped."""
        rep = LC.Report()
        with _Net({("GET", "/api/dip"): _j({"n_eligible": 242, "n_measured": 12,
                                            "n_unmeasured": 0, "capped": 230,
                                            "rows": [{"t": 1}]})}):
            LC.check_dip("https://x", rep)
        line = [ln for ln in rep.lines if "every eligible" in ln][0]
        self.assertIn("FAIL", line)
        self.assertIn("12 of 242", line)

    def test_zero_rows_fails_even_when_coverage_is_complete(self):
        """Full coverage and no rows is a different failure from partial coverage, and both
        matter: the first says the screen could not look, the second that it looked and the
        page has nothing to show."""
        rep = LC.Report()
        with _Net({("GET", "/api/dip"): _j({"n_eligible": 242, "n_measured": 242,
                                            "n_unmeasured": 0, "rows": []})}):
            LC.check_dip("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "returns rows" in ln for ln in rep.lines),
                        rep.lines)

    def test_unmeasured_names_fail(self):
        rep = LC.Report()
        with _Net({("GET", "/api/dip"): _j({"n_eligible": 10, "n_measured": 10,
                                            "n_unmeasured": 3, "rows": [{"t": 1}]})}):
            LC.check_dip("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "unmeasured" in ln for ln in rep.lines), rep.lines)


class TheExportCheckJudgesTheFileType(unittest.TestCase):
    """A 200 carrying a JSON error is non-empty, so length alone would pass a broken export."""

    def _table(self, xlsx, pdf):
        return {("GET", "/api/export/excel"): xlsx, ("GET", "/api/export/pdf"): pdf}

    def test_real_files_pass(self):
        xlsx = (200, b"PK\x03\x04" + b"x" * 5000, "application/octet-stream")
        pdf = (200, b"%PDF-1.7" + b"x" * 5000, "application/pdf")
        rep = LC.Report()
        with _Net(self._table(xlsx, pdf)):
            LC.check_exports("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_a_json_error_served_with_200_FAILS(self):
        """THE WHOLE POINT. `{"error": ...}` is non-empty and is not a spreadsheet."""
        err = (200, json.dumps({"error": "boom"}).encode("utf-8") + b" " * 5000,
               "application/json")
        rep = LC.Report()
        with _Net(self._table(err, err)):
            LC.check_exports("https://x", rep)
        self.assertEqual(rep.failed, 2, rep.lines)

    def test_a_truncated_file_fails(self):
        """A 40-byte xlsx has the right magic and is not a workbook."""
        tiny = (200, b"PK\x03\x04tiny", "application/octet-stream")
        rep = LC.Report()
        with _Net(self._table(tiny, tiny)):
            LC.check_exports("https://x", rep)
        self.assertEqual(rep.failed, 2, rep.lines)


class TheValuationChecks(unittest.TestCase):
    def _ok(self, fv, regime="mature"):
        return _j({"base_fair_value": fv, "classification": {"regime": regime}})

    def _table(self, zzzzq):
        t = {}
        for tk in ("MSFT", "O", "NEE", "BRK.B"):
            t[("POST", "/api/value", json.dumps({"ticker": tk}, sort_keys=True))] = \
                self._ok(100.0)
        t[("POST", "/api/value", json.dumps({"ticker": "ZZZZQ"}, sort_keys=True))] = zzzzq
        return t

    def test_four_real_names_and_a_refused_one_pass(self):
        rep = LC.Report()
        with _Net(self._table(_j({"error": "ticker not found"}, code=404))):
            LC.check_valuations("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.passed, 5)

    def test_a_200_with_a_score_for_a_nonexistent_ticker_FAILS(self):
        """THE DEFECT: HTTP 200, score 40, recommendation "Reduce", for no company at all."""
        bad = _j({"score": {"score": 40, "recommendation": "Reduce"}})
        rep = LC.Report()
        with _Net(self._table(bad)):
            LC.check_valuations("https://x", rep)
        line = [ln for ln in rep.lines if "ZZZZQ" in ln][0]
        self.assertIn("FAIL", line)

    def test_a_missing_fair_value_fails(self):
        t = self._table(_j({"error": "x"}, code=404))
        t[("POST", "/api/value", json.dumps({"ticker": "O"}, sort_keys=True))] = \
            _j({"base_fair_value": None})
        rep = LC.Report()
        with _Net(t):
            LC.check_valuations("https://x", rep)
        self.assertTrue(any("FAIL" in ln and " O " in ln for ln in rep.lines), rep.lines)


class TheAlertSurfacesAreComparedToEachOther(unittest.TestCase):
    def test_agreement_passes(self):
        rep = LC.Report()
        with _Net({("GET", "/api/scream-track"): _j({"n_live": 15}),
                   ("GET", "/api/options-scorecard"): _j({"n_open": 15})}):
            LC.check_alert_surfaces("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)

    def test_the_live_disagreement_fails(self):
        """23 vs 15 — exactly the 8 rows one surface was mis-classifying."""
        rep = LC.Report()
        with _Net({("GET", "/api/scream-track"): _j({"n_live": 23}),
                   ("GET", "/api/options-scorecard"): _j({"n_open": 15})}):
            LC.check_alert_surfaces("https://x", rep)
        line = [ln for ln in rep.lines if "agrees" in ln][0]
        self.assertIn("FAIL", line)
        self.assertIn("23", line)
        self.assertIn("15", line)

    def test_it_compares_rather_than_asserting_a_constant(self):
        """Both surfaces moving together must PASS, or the checker goes stale the first time a
        real alert closes and somebody edits a number in here instead of reading the site."""
        rep = LC.Report()
        with _Net({("GET", "/api/scream-track"): _j({"n_live": 4}),
                   ("GET", "/api/options-scorecard"): _j({"n_open": 4})}):
            LC.check_alert_surfaces("https://x", rep)
        self.assertEqual(rep.failed, 0, rep.lines)


class TheIndexChecks(unittest.TestCase):
    def _payload(self, n=85, weights=None):
        ws = weights if weights is not None else [1.0 / 86] * 86
        return {"is_preview": False, "n_positions": n,
                "card": {"is_tracked_construction": True, "construction": "taxable"},
                "positions": [{"ticker": "T%d" % i, "weight": w} for i, w in enumerate(ws)]}

    def test_a_preview_payload_fails(self):
        d = self._payload()
        d["is_preview"] = True
        d["card"]["is_tracked_construction"] = False
        rep = LC.Report()
        with _Net({("GET", "/api/valquo-index"): _j(d)}):
            LC.check_index("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "book in force" in ln for ln in rep.lines),
                        rep.lines)

    def test_a_short_book_fails(self):
        rep = LC.Report()
        with _Net({("GET", "/api/valquo-index"): _j(self._payload(n=10))}):
            LC.check_index("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "85+" in ln for ln in rep.lines), rep.lines)

    def test_weights_that_do_not_sum_to_one_fail(self):
        rep = LC.Report()
        with _Net({("GET", "/api/valquo-index"): _j(self._payload(weights=[0.1] * 3))}):
            LC.check_index("https://x", rep)
        self.assertTrue(any("FAIL" in ln and "sum to 1" in ln for ln in rep.lines), rep.lines)


class TheFreshnessUsesTheMarketCalendar(unittest.TestCase):
    def test_a_holiday_is_not_a_trading_day(self):
        """So the signals check SKIPS rather than failing on Thanksgiving."""
        from valuation.screener import market_session as MS
        # US Thanksgiving 2026.
        self.assertFalse(MS.is_trading_day(_dt.date(2026, 11, 26)))

    def test_the_signals_check_skips_on_a_non_trading_day(self):
        rep = LC.Report()
        sunday = _dt.datetime(2026, 10, 4, 18, 0)
        with _Net({("GET", "/api/signals"): _j({"run_time": "2026-10-02 23:08",
                                                "rows": [{"t": 1}]})}):
            LC.check_signals("https://x", rep, sunday)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.skipped, 1, rep.lines)

    def test_a_stale_run_time_fails_during_a_session(self):
        rep = LC.Report()
        # A Monday, inside the UTC band the checker uses.
        monday = _dt.datetime(2026, 10, 5, 13, 45)
        with _Net({("GET", "/api/signals"): _j({"run_time": "2026-10-02 23:08",
                                                "rows": [{"t": 1}]})}):
            LC.check_signals("https://x", rep, monday)
        self.assertTrue(any("FAIL" in ln and "today's session" in ln for ln in rep.lines),
                        rep.lines)

    def test_a_fresh_run_time_passes_during_a_session(self):
        rep = LC.Report()
        monday = _dt.datetime(2026, 10, 5, 13, 45)
        with _Net({("GET", "/api/signals"): _j({"run_time": "2026-10-05 13:23",
                                                "rows": [{"t": 1}]})}):
            LC.check_signals("https://x", rep, monday)
        self.assertEqual(rep.failed, 0, rep.lines)
        self.assertEqual(rep.skipped, 0, rep.lines)

    def test_an_empty_feed_fails_rather_than_skipping(self):
        """`empty: True` is the feed saying it has never run, which is a failure and not a
        reason to stand down."""
        rep = LC.Report()
        with _Net({("GET", "/api/signals"): _j({"empty": True, "message": "no scan yet"})}):
            LC.check_signals("https://x", rep, _dt.datetime(2026, 10, 5, 13, 45))
        self.assertEqual(rep.failed, 1, rep.lines)


class AnUnreachableSiteFailsRatherThanRaising(unittest.TestCase):
    """A connection error must produce a FAIL line, not a traceback — a crashed checker and a
    broken site look the same in a scheduler, and only one of them is actionable."""

    def test_every_check_survives_a_dead_host(self):
        rep = LC.Report()
        dead = (0, b"URLError: refused", "")
        table = {("GET", p): dead for p in
                 ("/api/hotstocks", "/api/dip", "/api/valquo-index", "/api/index-track",
                  "/api/scream-track", "/api/options-scorecard", "/api/signals",
                  "/api/export/excel", "/api/export/pdf", "/proof", "/methodology")}
        with _Net(table):
            LC.check_hot_list("https://x", rep, SESSION)
            LC.check_dip("https://x", rep)
            LC.check_index("https://x", rep)
            LC.check_index_track("https://x", rep, SESSION)
            LC.check_alert_surfaces("https://x", rep)
            LC.check_exports("https://x", rep)
            LC.check_pages("https://x", rep)
        self.assertGreater(rep.failed, 5, rep.lines)
        self.assertEqual(rep.finish(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
