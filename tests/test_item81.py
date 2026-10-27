"""Item 81 — the January rebalance without October's workarounds.

FOUR DEFECTS, EACH OF WHICH ALONE PRODUCED A BOOK NOBODY COULD TELL WAS WRONG:

  1. nothing ever refreshed the bulk caches the build reads, so the 2026-10-22 book was about
     to be ranked on 2026-07-29 market caps -- 60 trading days stale, on the number that
     decides which names clear the $10B floor;
  2. a second refresh into the same freeze directory KEPT the first one's prepared caches, so
     even the hand-patched build scored 2026-10-02 caps while labelled 2026-10-22;
  3. month-end down-sampling threw away the as-of's own row -- a fresh export taken on the
     evening of the 23rd made October's only kept row the 23rd, LATER than an as-of of the
     22nd, so `_daily_at` fell back to 09-30;
  4. `--limit`'s 3,000 default had become a market-cap-ranked SUBSET of a 3,520-name export,
     and the one-off script that built the recorded book did not pass the flag the runbook
     carried in bold.

Every test here is written against the behaviour, not the diff. Several fail against the
pre-change tree; `scripts/i81_before.py` measures which.
"""
import ast
import csv
import datetime as dt
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from valuation.edge import bulk as B                      # noqa: E402
from valuation.edge import sharadar_freeze as F           # noqa: E402
from valuation.edge import valquo_index as V              # noqa: E402
from valuation.edge.data_providers import WRDSProvider    # noqa: E402
from valuation.edge.fundamental_panel import _daily_at    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOK = os.path.join(REPO, "REBALANCE_RUNBOOK_2027-01-25.md")


def _daily_csv(path, ticker="AAA"):
    """A September month plus 23 October sessions, SHUFFLED, so arrival order cannot matter."""
    rows = []
    for d in range(1, 31):
        rows.append([ticker, "2026-09-%02d" % d, 100 + d, 1, 1, 1, 1])
    for d in range(1, 24):
        rows.append([ticker, "2026-10-%02d" % d, 200 + d, 1, 1, 1, 1])
    rows.append([ticker, "2026-01-15", 5, 1, 1, 1, 1])
    rows = rows[::3] + rows[1::3] + rows[2::3]          # deterministic shuffle
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "date", "marketcap", "pe", "pb", "ps", "evebitda"])
        w.writerows(rows)


class TheMonthEndBlindSpot(unittest.TestCase):
    """DEFECT 3. The cache must carry the as-of's own row, not the month before's."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.csv = os.path.join(self.d, "daily.csv")
        _daily_csv(self.csv)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_an_as_of_before_the_months_last_row_used_to_fall_back_a_whole_month(self):
        """The defect, reproduced, and then the fix -- on ONE input, so the two are comparable.

        ASSERTED ON THE MARKET CAP, NOT THE DATE, because `_daily_at` returns `rec[1:]` and
        drops the date -- which is exactly why the defect was invisible downstream. The
        fixture's caps are 100+day in September and 200+day in October, so the value names
        the row that was used.
        """
        old = B.prepare_daily(self.csv, cache_dir=os.path.join(self.d, "old"), tail_rows=0)
        new = B.prepare_daily(self.csv, cache_dir=os.path.join(self.d, "new"))
        # Pure month-end: October's only row is the 23rd, so the 22nd resolves to 2026-09-30.
        self.assertEqual(_daily_at(old["AAA"], "2026-10-22")[0], 130.0)   # 2026-09-30
        self.assertEqual(self._date_of(old["AAA"], "2026-10-22"), "2026-09-30")
        # With the tail: the 22nd resolves to the 22nd.
        self.assertEqual(_daily_at(new["AAA"], "2026-10-22")[0], 222.0)   # 2026-10-22
        self.assertEqual(self._date_of(new["AAA"], "2026-10-22"), "2026-10-22")

    @staticmethod
    def _date_of(rows, as_of):
        """Which DATE `_daily_at` picked, recovered from the cache rather than re-walked.

        Re-implementing the walk here would test the re-implementation. This matches the
        returned values back against the cache's own rows instead.
        """
        got = _daily_at(rows, as_of)
        return next(r[0] for r in rows if tuple(r[1:]) == tuple(got))

    def test_the_tail_never_reaches_past_the_as_of(self):
        """It can only make an answer MORE precise. A row after the as-of must not be used."""
        new = B.prepare_daily(self.csv, cache_dir=os.path.join(self.d, "c"))
        for as_of in ("2026-10-22", "2026-10-15", "2026-09-30", "2026-02-01"):
            self.assertLessEqual(self._date_of(new["AAA"], as_of), as_of)

    def test_the_month_end_rows_are_still_there(self):
        """The tail ADDS; it must not replace. An old month must keep its own row."""
        new = B.prepare_daily(self.csv, cache_dir=os.path.join(self.d, "c"))
        dates = [r[0] for r in new["AAA"]]
        self.assertIn("2026-01-15", dates)
        self.assertIn("2026-09-30", dates)
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(len(dates), len(set(dates)), "a date must appear once, not twice")

    def test_the_tail_is_bounded_per_ticker(self):
        """Unbounded would put 2.5GB of daily rows in memory -- the thing this module avoids."""
        new = B.prepare_daily(self.csv, cache_dir=os.path.join(self.d, "c"), tail_rows=3)
        dates = [r[0] for r in new["AAA"]]
        # 3 month-ends + at most 3 tail rows, and the tail must be the NEWEST three.
        self.assertLessEqual(len(dates), 6)
        self.assertEqual(dates[-3:], ["2026-10-21", "2026-10-22", "2026-10-23"])

    def test_tail_rows_zero_restores_the_behaviour_every_cache_on_disk_was_built_with(self):
        old = B.prepare_daily(self.csv, cache_dir=os.path.join(self.d, "z"), tail_rows=0)
        self.assertEqual([r[0] for r in old["AAA"]],
                         ["2026-01-15", "2026-09-30", "2026-10-23"])

    def test_the_tail_default_is_a_committed_literal(self):
        """`MA13`. A default that silently becomes 0 reinstates the defect and nothing says so."""
        self.assertEqual(B.DAILY_TAIL_ROWS, 25)
        self.assertGreater(B.DAILY_TAIL_ROWS, 5,
                           "must cover more sessions than the staleness bar allows")


class _FakeProv(WRDSProvider):
    def __init__(self, bulk_dir):
        self._bulk_dir = bulk_dir
        self.dir = bulk_dir


class ThePerCacheOverlay(unittest.TestCase):
    """DEFECT 1. Fresh caches without touching the pinned ones -- and per cache, not wholesale."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.live = os.path.join(self.d, "live")
        self.fresh = os.path.join(self.d, "fresh")
        os.makedirs(self.live)
        os.makedirs(self.fresh)
        # live carries nine-ish caches; the freeze carries five.
        for n in ("daily", "sf3", "actions", "events", "tickers", "congress", "edgar13d"):
            B._save_cache(n, self.live, {"LIVE_" + n.upper(): [("2026-07-29", 1.0, 1, 1, 1, 1)]})
        for n in ("daily", "sf3", "actions", "events", "tickers"):
            B._save_cache(n, self.fresh, {"FRESH_" + n.upper(): [("2026-10-23", 2.0, 1, 1, 1, 1)]})

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_the_named_caches_come_from_the_overlay_and_the_rest_do_not(self):
        p = _FakeProv(self.live)
        p.bulk_overlay(self.fresh)
        self.assertIn("FRESH_DAILY", p._bulk("daily"))
        self.assertIn("FRESH_SF3", p._bulk("sf3"))
        self.assertIn("LIVE_ACTIONS", p._bulk("actions"))
        self.assertIn("LIVE_TICKERS", p._bulk("tickers"))

    def test_a_cache_the_overlay_does_not_have_still_resolves(self):
        """`C5`: a wholesale directory swap reads four absent caches as a measured zero.

        `_bulk` degrades a missing cache to `{}` and raises nothing, so `congress`,
        `edgar13d`, `elite_conv` and `short_interest` would all silently read "no data".
        """
        p = _FakeProv(self.live)
        p.bulk_overlay(self.fresh)
        self.assertIn("LIVE_CONGRESS", p._bulk("congress"))
        self.assertIn("LIVE_EDGAR13D", p._bulk("edgar13d"))

    def test_the_manifest_reports_what_it_did_not_use(self):
        """No silent caps. An omission has to be visible in the build log."""
        p = _FakeProv(self.live)
        man = p.bulk_overlay(self.fresh)
        self.assertTrue(man["daily"]["used"])
        self.assertTrue(man["sf3"]["used"])
        self.assertFalse(man["actions"]["used"])
        self.assertFalse(man["tickers"]["used"])
        self.assertEqual(man["actions"]["source"], self.live)
        self.assertEqual(man["daily"]["source"], self.fresh)
        self.assertEqual(man["daily"]["entries"], 1)

    def test_the_default_set_excludes_the_caches_that_are_narrower_in_a_freeze(self):
        """Measured: a freeze's `actions` is missing 1,181 names and `tickers` 5,234."""
        self.assertEqual(tuple(WRDSProvider.BULK_OVERLAY_DEFAULT), ("daily", "sf3"))
        for n in ("actions", "tickers"):
            self.assertNotIn(n, WRDSProvider.BULK_OVERLAY_DEFAULT)

    def test_it_refuses_once_a_cache_has_been_read(self):
        """Half-applied is the worst outcome: July caps with October 13F, and nothing says so."""
        p = _FakeProv(self.live)
        p._bulk("daily")
        with self.assertRaises(RuntimeError) as cm:
            p.bulk_overlay(self.fresh)
        self.assertIn("already read", str(cm.exception))

    def test_it_refuses_a_directory_that_has_no_daily_cache(self):
        empty = os.path.join(self.d, "empty")
        os.makedirs(empty)
        with self.assertRaises(RuntimeError) as cm:
            _FakeProv(self.live).bulk_overlay(empty)
        self.assertIn("daily", str(cm.exception))

    def test_it_refuses_a_path_that_is_not_a_directory(self):
        with self.assertRaises(RuntimeError):
            _FakeProv(self.live).bulk_overlay(os.path.join(self.d, "nope"))

    def test_an_explicit_name_set_is_honoured(self):
        p = _FakeProv(self.live)
        p.bulk_overlay(self.fresh, ["daily"])
        self.assertIn("FRESH_DAILY", p._bulk("daily"))
        self.assertIn("LIVE_SF3", p._bulk("sf3"))

    def test_the_vintage_is_read_through_the_overlay_not_off_the_disk(self):
        """Reading the directory would describe a file that may not be the one in play."""
        p = _FakeProv(self.live)
        self.assertEqual(V.daily_cache_vintage(p)["newest_row"], "2026-07-29")
        q = _FakeProv(self.live)
        q.bulk_overlay(self.fresh)
        v = V.daily_cache_vintage(q)
        self.assertEqual(v["newest_row"], "2026-10-23")
        self.assertEqual(v["source"], self.fresh)


class TheStalenessRefusal(unittest.TestCase):
    """DEFECT 1 and 2's shared consequence: a stale market cap must not pass silently again."""

    def _v(self, newest):
        return {"newest_row": newest, "tickers": 10, "source": "D"}

    def test_the_october_defect_refuses(self):
        """2026-07-29 caps against a 2026-10-22 as-of: 60 trading days."""
        msg = V.refuse_stale_daily_cache(self._v("2026-07-29"), "2026-10-22")
        self.assertIsNotNone(msg)
        self.assertIn("2026-07-29", msg)
        self.assertIn("60 trading days", msg)
        self.assertIn("--bulk-overlay", msg, "the refusal must name the remedy")

    def test_the_worked_around_build_also_refuses(self):
        """2026-10-02 caps, 14 sessions. The patch improved it and did not fix it."""
        msg = V.refuse_stale_daily_cache(self._v("2026-10-02"), "2026-10-22")
        self.assertIsNotNone(msg)
        self.assertIn("14 trading days", msg)

    def test_a_cache_inside_the_bar_passes(self):
        self.assertIsNone(V.refuse_stale_daily_cache(self._v("2026-10-15"), "2026-10-22"))
        self.assertIsNone(V.refuse_stale_daily_cache(self._v("2026-10-22"), "2026-10-22"))
        self.assertIsNone(V.refuse_stale_daily_cache(self._v("2026-10-23"), "2026-10-22"))

    def test_the_bar_is_exactly_at_the_constant(self):
        """Derived, not retyped: 2026-10-15 is five sessions before 2026-10-22."""
        from valuation.screener.market_session import trading_days_between
        self.assertEqual(trading_days_between(dt.date(2026, 10, 15), dt.date(2026, 10, 22),
                                              inclusive_start=False),
                         V.MAX_DAILY_CACHE_STALE_DAYS)

    def test_it_cannot_fire_on_a_historical_build(self):
        """A backtest as of 2009 reads a cache that reaches far past it. Not stale."""
        self.assertIsNone(V.refuse_stale_daily_cache(self._v("2026-07-29"), "2009-01-15"))

    def test_it_is_counted_in_trading_days_not_calendar_days(self):
        """`MA21`: a build delayed over a holiday weekend must not be refused for the holiday."""
        # 2026-12-25 is a Friday holiday; 2026-12-21 -> 2026-12-29 is 9 calendar days and
        # fewer than 6 sessions, so a calendar-day bar of 5 would refuse and this must not.
        self.assertIsNone(V.refuse_stale_daily_cache(self._v("2026-12-21"), "2026-12-29"))

    def test_an_absent_cache_is_not_stale_and_must_not_be_refused(self):
        """MY OWN DEFECT, caught by `tests/test_item75.py` going red in CI.

        The first cut refused an empty `daily` cache as well. `_bulk` degrades a missing cache
        to `{}` BY DESIGN, so building with no bulk caches is a configuration this project has
        always supported -- item 75's fixtures do exactly that -- and the refusal also
        pre-empted item 75's own, more specific, as-of refusals. Turning a tolerated absence
        into a hard stop is the mirror image of `C5`, and `MA21`'s cry-wolf rule besides.

        It is not the October defect either: that cache had a newest row of 2026-07-29 and is
        still refused. An absent cache cannot produce a silently WRONG market cap.
        """
        self.assertIsNone(
            V.refuse_stale_daily_cache({"newest_row": None, "source": "D"}, "2026-10-22"))
        self.assertIsNone(V.refuse_stale_daily_cache({}, "2026-10-22"))
        # and the dated defect still refuses, so this did not weaken the gate
        self.assertIsNotNone(V.refuse_stale_daily_cache(self._v("2026-07-29"), "2026-10-22"))

    def test_no_as_of_defers_to_the_second_check(self):
        """With no `--as-of` the effective date is unknown until the export is loaded."""
        self.assertIsNone(V.refuse_stale_daily_cache(self._v("2026-07-29"), None))

    def test_the_check_runs_before_the_scoring_and_again_after_it(self):
        """Cheap first (a quarter of an hour saved on a typo), then against the resolved date.

        Read off the AST rather than by eye: the order is the whole point of the first call.
        """
        src = io.open(os.path.join(REPO, "valuation", "edge", "valquo_index.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_full_universe_rows")
        seq = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("refuse_stale_daily_cache", "score_universe_now"):
                    seq.append((node.lineno, node.func.id))
        seq.sort()
        names = [n for _, n in seq]
        self.assertEqual(names, ["refuse_stale_daily_cache", "score_universe_now",
                                 "refuse_stale_daily_cache"], seq)


class TheRefreshRebuildsStaleCaches(unittest.TestCase):
    """DEFECT 2. A cache whose source CSV is newer than it is must be rebuilt, not reused."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.bulk = os.path.join(self.d, "bulk")
        self.cache = os.path.join(self.bulk, "prepared")
        os.makedirs(self.cache)
        self.src = os.path.join(self.bulk, "daily.csv")
        _daily_csv(self.src)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _stale(self):
        return F._prepare_stale(self.cache, self.bulk, "daily", "daily.csv")

    def test_a_cache_older_than_its_source_is_stale(self):
        B._save_cache("daily", self.cache, {"A": []})
        old = dt.datetime(2026, 10, 4).timestamp()
        os.utime(os.path.join(self.cache, "daily.pkl"), (old, old))
        self.assertTrue(self._stale())

    def test_a_cache_newer_than_its_source_is_not(self):
        B._save_cache("daily", self.cache, {"A": []})
        self.assertFalse(self._stale())

    def test_an_absent_cache_is_not_called_stale(self):
        """It is absent, not stale; `prepare_*` builds it either way."""
        self.assertFalse(self._stale())

    def test_an_absent_source_is_not_stale(self):
        """Nothing newer to rebuild from, and `prepare_*` already degrades to skipping."""
        B._save_cache("daily", self.cache, {"A": []})
        os.remove(self.src)
        self.assertFalse(self._stale())

    def test_tickers_is_excluded_and_the_reason_is_named(self):
        """It is the one table fetched from the API, so there is no source mtime to compare."""
        self.assertNotIn("tickers", F.STALE_IF_SOURCE_NEWER)
        for n in ("daily", "sf3", "actions", "events"):
            self.assertIn(n, F.STALE_IF_SOURCE_NEWER)


class TheCliRefusals(unittest.TestCase):
    def test_the_overlay_needs_the_full_universe_path(self):
        rc = V.main(["--bulk-overlay", ".", "--out", os.devnull])
        self.assertEqual(rc, 1)

    def test_overlay_names_need_an_overlay(self):
        rc = V.main(["--bulk-overlay-names", "daily", "--out", os.devnull])
        self.assertEqual(rc, 1)

    def test_the_limit_default_is_the_whole_export(self):
        """DEFECT 4. 3,000 was the whole export at 2,827 names and a ranked subset at 3,520."""
        import argparse
        src = io.open(os.path.join(REPO, "valuation", "edge", "valquo_index.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        found = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument" and node.args
                    and getattr(node.args[0], "value", None) == "--limit"):
                for kw in node.keywords:
                    if kw.arg == "default":
                        found.append(ast.literal_eval(kw.value))
        self.assertEqual(found, [None],
                         "--limit must default to the whole export, not to a ranked subset")
        self.assertTrue(argparse)  # the flag is still parsed, not removed

    def test_the_help_text_names_the_default_set_without_retyping_it(self):
        """`MA5`. `--config`'s help said 20% for weeks after 0.30 was adopted."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "valquo_index.py"),
                      encoding="utf-8").read()
        self.assertNotIn('default: daily,sf3', src,
                         "the default set must be derived from BULK_OVERLAY_DEFAULT")
        self.assertIn("BULK_OVERLAY_DEFAULT", src)


class TheRunbook(unittest.TestCase):
    """A runbook is read once a quarter, at speed, by one person. It has to be right."""

    @classmethod
    def setUpClass(cls):
        cls.txt = io.open(RUNBOOK, encoding="utf-8").read()

    def test_it_exists_and_is_dated_for_the_next_rebalance(self):
        from valuation.screener.index_in_force import next_rebalance
        nxt = next_rebalance("2026-10-22")
        self.assertEqual(nxt, "2027-01-25")
        self.assertIn(nxt, self.txt)
        self.assertTrue(RUNBOOK.endswith("REBALANCE_RUNBOOK_%s.md" % nxt))

    def test_every_command_it_tells_don_to_type_resolves(self):
        """The defect this test exists for was in this very file's first draft.

        It told Don to run `from valuation.screener.index_mark import next_rebalance`, and
        that function lives in `index_in_force` -- so the command raised ImportError. A
        runbook command that does not resolve is worse than no command, and a grep for the
        module name would not have caught it because the WRONG module also exists.

        So this parses every `python -c` snippet the runbook contains and actually imports
        what it imports, checking each name is really there.
        """
        import importlib
        snippets = re.findall(r'python -c "(.+?)"\n', self.txt, re.S)
        self.assertGreaterEqual(len(snippets), 3, "the runbook should carry its own checks")
        checked = 0
        for code in snippets:
            tree = ast.parse(code.replace("\\n", "\n"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = importlib.import_module(node.module)
                    for al in node.names:
                        # `from X import Y` resolves if Y is an attribute OR a submodule.
                        if not hasattr(mod, al.name):
                            importlib.import_module("%s.%s" % (node.module, al.name))
                        checked += 1
                elif isinstance(node, ast.Import):
                    for al in node.names:
                        importlib.import_module(al.name)
                        checked += 1
        self.assertGreaterEqual(checked, 3, "nothing was actually imported")
    def test_it_says_what_happens_when_sharadar_lapses(self):
        """REPOINTED BY ITEM 84, in the commit that changed what the runbook should say.

        It asserted the runbook calls renewal "Don's purchase" and a "decision" -- which was
        right when written and FIRED once Don ruled on 2026-10-24: access lapses around
        2026-11-03 and that is fine, he renews around January only if the rebalance needs it,
        **and the lanes do not raise renewal again before then.** That entry says in terms
        that "the January runbook's §0 is settled by this entry", so a runbook still pressing
        him for the decision would be disobeying a standing ruling.

        The PROPERTY this test stood for is unchanged and is what it asserts now: the runbook
        states the date, and says what happens on the night in each case.
        """
        self.assertIn("2026-11-03", self.txt)
        low = self.txt.lower()
        self.assertIn("renew", low)
        self.assertIn("settled", low, "the ruling settles it; the runbook must say so")
        self.assertIn("authorisation error", low, "and what a lapsed pull looks like")

    def test_it_carries_the_steps_that_worked_on_the_night(self):
        for s in ("refresh_sharadar.bat", "--as-of 2027-01-25", "--config taxable",
                  "--bulk-overlay", "--out data/valquo_index.json",
                  "seed_track", "--pull", "--send"):
            self.assertIn(s, self.txt, s)

    def test_the_dry_run_comes_before_the_send(self):
        """It caught both door bugs on 2026-10-23 before anything was written."""
        self.assertLess(self.txt.index("--rebalance-date 2027-01-25 --pull\n"),
                        self.txt.index("--pull --send"))

    def test_it_states_the_market_cap_vintage_line_to_read(self):
        self.assertIn("market caps from", self.txt)
        self.assertIn("newest row", self.txt)

    def test_it_says_this_is_not_a_vintage_event(self):
        self.assertIn("not a vintage event", self.txt.lower())

    def test_it_contains_no_secret(self):
        """Standing rule: no key, no token, nothing private, in any document."""
        low = self.txt.lower()
        for bad in ("api_key=", "admin_token=", "sharadar_api_key=", "bearer ",
                    "x-admin-token:"):
            self.assertNotIn(bad, low, bad)


class TheRefreshScript(unittest.TestCase):
    """The double-click. It has to hand the operator the one path step 2 needs."""

    @classmethod
    def setUpClass(cls):
        cls.txt = io.open(os.path.join(REPO, "refresh_sharadar.bat"),
                          encoding="utf-8").read()

    def test_it_points_at_the_current_runbook(self):
        """It pointed at REBALANCE_RUNBOOK_2026-10-22.md, which is spent."""
        self.assertIn("REBALANCE_RUNBOOK_2027-01-25.md", self.txt)
        self.assertNotIn("REBALANCE_RUNBOOK_2026-10-22.md Path B", self.txt)

    def test_it_prints_the_overlay_path_on_success(self):
        """Derived from the freeze it just wrote, so the operator cannot mistype a date."""
        self.assertIn("--bulk-overlay !FREEZE!", self.txt)
        i = self.txt.index("SUCCESS: data")
        self.assertLess(i, self.txt.index("--bulk-overlay !FREEZE!"),
                        "the path belongs in the success block, after the freeze is known")

    def test_it_still_never_echoes_the_key(self):
        low = self.txt.lower()
        self.assertNotIn("api_key", low)
        self.assertNotIn("sharadar_api_key", low)
        self.assertIn("THE API KEY IS NEVER PRINTED", self.txt)

class WhatThisDidNotDo(unittest.TestCase):
    def test_decisions_md_is_not_edited_by_this_item(self):
        """The manager's file. A lane edit to it blocks Don's fast-forward."""
        import subprocess
        out = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "DECISIONS.md"],
                             capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "", "DECISIONS.md must not be modified")

    def test_the_pinned_july_caches_are_never_written_by_the_overlay_path(self):
        """The overlay READS. Nothing in it opens a cache for writing."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "data_providers.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "bulk_overlay")
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("_save_cache", "open"),
                                 "the overlay must never write a cache")


if __name__ == "__main__":
    unittest.main(verbosity=2)
