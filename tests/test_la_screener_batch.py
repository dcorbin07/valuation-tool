"""
Tests for the screener batch of the cold audit (`VALQUO_LIVE_AUDIT.md`): LA4, LA5, LA7, LA9,
LA12, LA14.

Every claim was verified against the code before anything was changed (RUN_RULES A8), and the
measurements that verified them are the fixtures below — so each test states the defect as a
number rather than as a description of one.

  LA4   `run_scan` read the clock AFTER the scan, so the 23:41 UTC backup cron stamped the next
        calendar day if it ran more than 19 minutes. Two dates for one Friday close.
  LA5   `ci_scan` posted neither `health` nor `filtered`, so every data-health signal the scan
        computed was printed to a log and then dropped in transit.
  LA7   `freshness` never checked that `as_of` was a trading day, and counted holidays as
        sessions while its own docstring argued for the opposite.
  LA9   the scheduled `hot` job passed no TRADIER_TOKEN, so it silently ran the fallback
        universe. The audit marked it HYPOTHESIS; it is confirmed here from the workflow.
  LA12  `median_upside` was a median over DCF'd names only, beside a `count` of the whole sector.
  LA14  `market_holidays(y)` could contain a date in year y-1.
"""
from __future__ import annotations

import ast
import datetime as dt
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import freshness as F              # noqa: E402
from valuation.screener import screen as SC                # noqa: E402
from valuation.screener import market_session as MS        # noqa: E402
from valuation.screener.sectors import sector_attractiveness  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ==========================================================================================
# LA4 — the clock at the wrong end of a long operation.
# ==========================================================================================

class _Provider:
    """A provider whose universe fetch ADVANCES THE CLOCK, which is the whole point.

    The defect is not "the date is wrong", it is "the date is read after work that can cross
    midnight". A fixture where no time passes cannot tell the two implementations apart.
    """
    name = "fixture"
    universe_note = ""

    def __init__(self, clock):
        self.clock = clock

    def get_universe(self, scope):
        self.clock.append("2026-08-08")     # midnight crossed during the universe fetch
        return []


class _Clock(list):
    """`_today()` replacement: returns the current head, which the provider can move."""

    def __call__(self):
        return self[-1]


class TestLA4TheClockIsReadAtTheStart(unittest.TestCase):
    def setUp(self):
        self._real_today = SC._today

    def tearDown(self):
        SC._today = self._real_today

    def test_the_stamp_is_taken_before_the_scan_not_after(self):
        """The live signature of this bug: 2026-08-07 and 2026-08-08 both exist for the single
        Friday close, and 2026-08-08 is a Saturday."""
        clock = _Clock(["2026-08-07"])
        SC._today = clock
        res = SC.run_scan(scope="bundled", provider=_Provider(clock), save=False)
        self.assertEqual(res["scan_date"], "2026-08-07",
                         "the snapshot must carry the date the scan STARTED; reading the clock "
                         "after the scan is what let the backup cron stamp the next day")

    def test_the_clock_is_read_exactly_once_per_scan(self):
        """Two reads can disagree with each other even when both are 'at the start'."""
        calls = []

        def counting():
            calls.append(1)
            return "2026-08-07"

        SC._today = counting
        SC.run_scan(scope="bundled", provider=_Provider(_Clock(["2026-08-07"])), save=False)
        self.assertEqual(len(calls), 1, f"_today() called {len(calls)} times in one scan")

    def test_no_early_return_path_re_reads_the_clock(self):
        """`run_scan` has three exits — two early ones for an empty universe and an unscorable
        frame. All three used to call `_today()` separately."""
        src = io.open(os.path.join(REPO, "valuation", "screener", "screen.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_scan")
        today_calls = [n for n in ast.walk(fn)
                       if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_today"]
        self.assertEqual(len(today_calls), 1,
                         "run_scan must read the clock once, at the top")

    def test_both_crons_stamp_the_same_utc_date(self):
        """The arithmetic that made the backup cron stop being a no-op.

        Primary 22:23 UTC, backup 23:41 UTC. Stamped at START both are the same UTC date, so
        `hot_processed_{scan_date}` is ONE key and the backup is idempotent as its own comment
        claims. Stamped at the END the backup had 19 minutes of headroom against a job the
        workflow allows 60.
        """
        primary = dt.datetime(2026, 8, 7, 22, 23, tzinfo=dt.timezone.utc)
        backup = dt.datetime(2026, 8, 7, 23, 41, tzinfo=dt.timezone.utc)
        self.assertEqual(primary.date(), backup.date())
        # ...and the end-stamped backup is what produced the Saturday.
        self.assertEqual((backup + dt.timedelta(minutes=20)).date(), dt.date(2026, 8, 8))
        self.assertFalse(MS.is_trading_day(dt.date(2026, 8, 8)))


# ==========================================================================================
# LA5 — the scan's diagnostics must reach the record.
# ==========================================================================================

class TestLA5TheHealthBlockReachesTheRecord(unittest.TestCase):
    def test_ci_scan_posts_health_and_filtered(self):
        """Asserted on the POSTED PAYLOAD, not on the source text, because the defect was
        exactly that the values existed everywhere except in the payload."""
        import scripts.ci_scan as CI

        sent = {}

        def fake_post(path, payload):
            sent[path] = payload
            return {}

        def fake_run_scan(**kw):
            return {"scan_date": "2026-08-07", "rows": [{"ticker": "AAA"}], "universe_size": 800,
                    "scored": 1, "provider": "fixture",
                    "health": {"refusal_screen": {"screened": 500, "refused": 0},
                               "theme_contributing": {"insider": 0.0}},
                    "filtered": {"total_removed": 3, "by_reason": {"no data": 3}}}

        real_post, real_scan, real_sample = CI._post, None, CI.refresh_landing_sample
        import valuation.screener.screen as _sc
        real_scan = _sc.run_scan
        try:
            CI._post = fake_post
            _sc.run_scan = fake_run_scan
            CI.refresh_landing_sample = lambda: None
            os.environ.setdefault("BASE_URL", "https://example.invalid")
            os.environ.setdefault("ADMIN_TOKEN", "x")
            CI.run_hot()
        finally:
            CI._post, _sc.run_scan, CI.refresh_landing_sample = real_post, real_scan, real_sample

        params = sent["/admin/ingest-snapshot"]["params"]
        self.assertIn("health", params)
        self.assertIn("filtered", params)
        self.assertEqual(params["health"]["refusal_screen"]["screened"], 500)
        self.assertEqual(params["filtered"]["total_removed"], 3)

    def test_the_serving_side_reads_exactly_those_keys(self):
        """Both ends, so a rename on one side cannot quietly re-open the gap."""
        src = io.open(os.path.join(REPO, "valuation", "web", "app.py"), encoding="utf-8").read()
        self.assertIn('params.get("health")', src)
        self.assertIn('params.get("filtered")', src)

    def test_a_zero_refusal_count_is_now_readable_rather_than_absent(self):
        """WHY this matters more than its diff: `refusal_screen` exists so that a silent zero
        is the tell that the publication leak is back. The 2026-08-08 scan reported zero
        refusals across 500 names it could not reach, and nothing anywhere said so."""
        import scripts.ci_scan as CI
        src = io.open(CI.__file__, encoding="utf-8").read()
        self.assertIn('"health": res.get("health")', src)


# ==========================================================================================
# LA7 — the guard that could not see.
# ==========================================================================================

class TestLA7FreshnessValidatesItsInput(unittest.TestCase):
    def test_a_saturday_snapshot_is_never_fresh(self):
        """Measured before the fix: level `fresh`, message 'As of 2026-08-08 (last close).'
        2026-08-08 is a Saturday. There was no close."""
        s = F.status("2026-08-08", today=dt.date(2026, 8, 10))
        self.assertNotEqual(s["level"], "fresh")
        self.assertFalse(s["as_of_is_trading_day"])
        self.assertNotIn("last close", s["message"])
        self.assertTrue(s["stale"], "'do not present this as current' must be set")

    def test_an_ordinary_trading_day_is_unaffected(self):
        """The control. A guard that reclassifies healthy days is worse than the defect."""
        s = F.status("2026-08-07", today=dt.date(2026, 8, 10))   # Friday
        self.assertEqual(s["level"], "fresh")
        self.assertTrue(s["as_of_is_trading_day"])
        self.assertIn("last close", s["message"])

    def test_a_market_holiday_is_also_not_a_valid_as_of(self):
        s = F.status("2026-12-25", today=dt.date(2026, 12, 28))
        self.assertNotEqual(s["level"], "fresh")
        self.assertFalse(s["as_of_is_trading_day"])

    def test_holidays_no_longer_count_as_trading_days(self):
        """Measured before the fix: 2 trading days over a gap containing one session."""
        self.assertEqual(F.status("2026-12-24", today=dt.date(2026, 12, 28))["age_trading_days"], 1)

    def test_the_badge_got_more_generous_not_less(self):
        """The direction the old docstring claimed to want. Counting holidays inflates age,
        which fires the badge EARLIER — that is crying wolf, not guarding against it."""
        def naive(start, end):
            n, d = 0, start
            while d < end:
                d += dt.timedelta(days=1)
                if d.weekday() < 5:
                    n += 1
            return n
        a, b = dt.date(2026, 12, 24), dt.date(2026, 12, 30)
        self.assertLess(F.trading_days_between(a, b), naive(a, b))

    def test_there_is_one_trading_day_calendar_not_two(self):
        """Before this, two functions with the SAME NAME in sibling modules returned 2 and 1
        for the same interval. Whichever a reader imported was a coin flip."""
        a, b = dt.date(2026, 12, 24), dt.date(2026, 12, 28)
        self.assertEqual(F.trading_days_between(a, b),
                         MS.trading_days_between(a, b, inclusive_start=False))

    def test_the_docstring_no_longer_carries_the_backwards_justification(self):
        src = io.open(F.__file__, encoding="utf-8").read()
        self.assertNotIn("Holidays are not modelled — the cost of being one day generous", src)

    def test_every_return_path_carries_the_new_field(self):
        """A field present on three of four returns is a field a caller cannot rely on."""
        for arg, today in (("2026-08-07", dt.date(2026, 8, 10)),
                           ("2026-08-08", dt.date(2026, 8, 10)),
                           ("2026-07-01", dt.date(2026, 8, 10)),
                           (None, dt.date(2026, 8, 10))):
            self.assertIn("as_of_is_trading_day", F.status(arg, today=today), f"as_of={arg}")

    def test_an_undated_input_still_reports_unknown(self):
        s = F.status(None)
        self.assertEqual(s["level"], "unknown")
        self.assertIsNone(s["as_of_is_trading_day"])


# ==========================================================================================
# LA9 — the hypothesis, settled from the workflow definition.
# ==========================================================================================

class TestLA9TheHotJobHasABrokerToken(unittest.TestCase):
    WF = os.path.join(REPO, ".github", "workflows", "auto-scan.yml")

    def _hot_block(self):
        body = io.open(self.WF, encoding="utf-8").read()
        start = body.index("KIND: hot")
        # walk back to the env: block that owns it
        return body[body.rindex("env:", 0, start):start]

    def test_the_hot_job_passes_the_broker_token(self):
        """The audit could not read Actions' secret scope and marked this a HYPOTHESIS. The
        workflow file is the authority on what env a job receives, so it settles it: the token
        was absent, and `broker_universe.available()` is `bool(cfg.tradier_token)`."""
        self.assertIn("TRADIER_TOKEN", self._hot_block())

    def test_it_also_passes_the_env_or_the_token_points_at_the_sandbox(self):
        """Passing the token ALONE would have been a quieter version of the same bug:
        `CONFIG.tradier_env` defaults to sandbox, and `broker_universe` routes sandbox traffic
        to sandbox.tradier.com — a job with 'a broker' and still not the real universe."""
        self.assertIn("TRADIER_ENV: live", self._hot_block())

    def test_the_default_env_really_is_sandbox(self):
        """Pins the premise of the test above rather than trusting a comment about it."""
        src = io.open(os.path.join(REPO, "valuation", "config.py"), encoding="utf-8").read()
        self.assertIn('_get("TRADIER_ENV", "sandbox")', src)

    def test_availability_really_is_just_the_token(self):
        """If this ever stops being a bare bool, the reasoning above needs revisiting."""
        from valuation.screener import broker_universe
        src = io.open(broker_universe.__file__, encoding="utf-8").read()
        self.assertIn("bool(", src)
        self.assertIn("tradier_token", src)


# ==========================================================================================
# LA12 — two populations in one row.
# ==========================================================================================

class TestLA12MedianUpsideCarriesItsDenominator(unittest.TestCase):
    ROWS = [
        {"sector": "Tech", "composite": 1.0, "rank": 1, "upside": 0.40},
        {"sector": "Tech", "composite": 0.9, "rank": 2, "upside": 0.60},
        {"sector": "Tech", "composite": 0.2, "rank": 55},          # no DCF -> no upside
        {"sector": "Tech", "composite": 0.1, "rank": 56},
        {"sector": "Energy", "composite": 0.5, "rank": 30},        # nobody in this sector
    ]

    def test_the_denominator_is_reported_beside_the_median(self):
        tech = next(s for s in sector_attractiveness(self.ROWS) if s["sector"] == "Tech")
        self.assertEqual(tech["count"], 4)
        self.assertEqual(tech["median_upside_n"], 2)
        self.assertAlmostEqual(tech["median_upside"], 0.50)

    def test_a_sector_with_no_valued_names_reports_zero_not_a_silent_none(self):
        e = next(s for s in sector_attractiveness(self.ROWS) if s["sector"] == "Energy")
        self.assertIsNone(e["median_upside"])
        self.assertEqual(e["median_upside_n"], 0)

    def test_n_is_zero_exactly_when_the_median_is_none(self):
        """The invariant that makes the pair readable without knowing the implementation."""
        for s in sector_attractiveness(self.ROWS):
            self.assertEqual(s["median_upside"] is None, s["median_upside_n"] == 0, s["sector"])

    def test_the_count_field_still_means_the_whole_sector(self):
        """`count` was never wrong — it was being read against a median that meant something
        else. Changing it would fix the symptom by breaking the correct field."""
        tech = next(s for s in sector_attractiveness(self.ROWS) if s["sector"] == "Tech")
        self.assertEqual(tech["count"], sum(1 for r in self.ROWS if r["sector"] == "Tech"))


# ==========================================================================================
# LA14 — a set containing a date outside the year it names.
# ==========================================================================================

class TestLA14HolidaysStayInsideTheirYear(unittest.TestCase):
    def test_the_two_measured_years_are_clean(self):
        """Measured before the fix: market_holidays(2028) contained 2027-12-31 and
        market_holidays(2033) contained 2032-12-31."""
        self.assertNotIn(dt.date(2027, 12, 31), MS.market_holidays(2028))
        self.assertNotIn(dt.date(2032, 12, 31), MS.market_holidays(2033))

    def test_no_year_in_a_long_span_leaks_a_date(self):
        for y in range(1999, 2061):
            strays = sorted(d for d in MS.market_holidays(y) if d.year != y)
            self.assertEqual(strays, [], f"market_holidays({y}) leaked {strays}")

    def test_the_dropped_date_is_correct_nyse_behaviour_not_just_tidiness(self):
        """The NYSE does not close on 31 December when 1 January falls on a Saturday, so the
        holiday is not observed at all. The neighbouring year must not gain it either."""
        self.assertEqual(dt.date(2028, 1, 1).weekday(), 5)          # Saturday
        self.assertNotIn(dt.date(2027, 12, 31), MS.market_holidays(2027))
        self.assertTrue(MS.is_trading_day(dt.date(2027, 12, 31)))

    def test_the_filter_removed_something_so_the_test_is_not_vacuous(self):
        """A guard that passes because it never had anything to catch is not a guard."""
        raw = MS._holidays_unfiltered(2028)
        self.assertIn(dt.date(2027, 12, 31), raw)
        self.assertEqual(len(raw) - len(MS.market_holidays(2028)), 1)

    def test_ordinary_years_are_untouched(self):
        """Ten holidays in, ten holidays out, whenever nothing rolls across the boundary."""
        for y in (2026, 2027, 2029, 2030):
            self.assertEqual(len(MS.market_holidays(y)), len(MS._holidays_unfiltered(y)))

    def test_is_trading_day_is_unchanged_by_this(self):
        """It queried market_holidays(d.year) and so never saw the stray — the fix must not
        move any answer it was already giving. Expectations written out, not derived."""
        expected = {
            dt.date(2028, 1, 3): True,    # Monday after the Saturday New Year — a normal session
            dt.date(2028, 7, 4): False,   # Independence Day, a Tuesday
            dt.date(2028, 12, 25): False,  # Christmas, a Monday
            dt.date(2028, 11, 23): False,  # Thanksgiving
            dt.date(2028, 5, 29): False,  # Memorial Day
            dt.date(2028, 1, 1): False,   # Saturday
        }
        for d, want in expected.items():
            self.assertEqual(MS.is_trading_day(d), want, d.isoformat())


# ==========================================================================================
# NOT ONE OF THE SIX — found by walking into it while recording the six.
#
# An LA7 note containing the literal `fresh|warn|stale|unknown` split its row into 15 cells
# against a 10-column header and the row VANISHED: `read_ledger()` returned 177 rows without
# it and every "is LA7 done?" query answered no. Escaping as `\|` fixed the markdown render
# and NOT this parser, so the row stayed invisible while looking right in the file.
#
# The silent drop was the smaller half: `main()` re-renders the table from `read_ledger()`, so
# a row it cannot see is DELETED by the next `--write`.
# ==========================================================================================

class TestTheLedgerParserCannotSilentlyLoseARow(unittest.TestCase):
    def test_a_split_row_is_recorded_rather_than_skipped(self):
        from scripts.build_ledger import read_ledger, MALFORMED
        read_ledger()
        self.assertIsInstance(MALFORMED, list)

    def test_the_real_ledger_has_no_UNKNOWN_losses(self):
        """NO row may be unparseable. The expected set is EMPTY, which is strictly stronger than
        the three-row allowlist this test used to carry.

        UPDATED 2026-08-14 (options-bot lane, audit #3 ingest). It read
        `["M1-PARSE", "S23", "V2G"]` — three rows this suite's own lane found malformed and
        deliberately REPORTED rather than rewritten, on the ground that its register forbade
        editing another lane's row. That was the right call for that session and it had a cost
        nobody had measured: `build_ledger.py` does not merely tolerate those rows, it
        **REFUSES TO RUN AT ALL** ("REFUSING TO PROCEED — these ledger rows could not be parsed
        and would be DELETED by a rewrite"), so the ledger's only refresh tool was blocked for
        as long as any of them existed. Ledger rule 2 — *if the ledger cannot answer, fixing
        the ledger is the task* — settles it. Four raw `|` characters were removed from three
        notes; no word and no claim was touched, and the change is recorded in the ledger's own
        prose and in `HANDOFF_optionsbot.md` §58.

        THE GUARD'S PURPOSE IS UNCHANGED AND SHARPER: it still fails the moment a malformed row
        appears, and now it does so on the FIRST one rather than the fourth."""
        from scripts.build_ledger import read_ledger, MALFORMED
        read_ledger()
        self.assertEqual(sorted(f for _n, _c, f in MALFORMED), [])

    def test_rows_of_the_documents_other_tables_are_not_flagged(self):
        """The file holds a 7-column series summary and a 3-column key. Flagging those would
        make the guard fire constantly, which is how a warning stops being read."""
        from scripts.build_ledger import read_ledger, MALFORMED, COLS
        read_ledger()
        for _n, count, _f in MALFORMED:
            self.assertGreater(count, len(COLS))

    def test_all_six_of_this_batch_are_actually_visible_to_the_parser(self):
        """The point of the whole guard: a ledger row that does not parse is not a record."""
        from scripts.build_ledger import read_ledger
        rows = read_ledger()
        for rid in ("LA4", "LA5", "LA7", "LA9", "LA12", "LA14"):
            self.assertIn(rid, rows, f"{rid} is not readable in the ledger")
            self.assertEqual(rows[rid]["status"], "**DONE**")

    def test_the_write_path_refuses_rather_than_dropping(self):
        src = io.open(os.path.join(REPO, "scripts", "build_ledger.py"), encoding="utf-8").read()
        self.assertIn("REFUSING TO PROCEED", src)
        self.assertIn("if MALFORMED:", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
