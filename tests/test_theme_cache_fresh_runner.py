"""ITEM 28 — THE THEME-CACHE ENTRY POINTS, FROM A WORKING DIRECTORY WITH NO `data/` AT ALL.

**THE JOB HAD NEVER ONCE BEEN ABLE TO RUN ON GITHUB.** Manual run #541 (2026-10-04), all three
shards, died three seconds into "Crawl shard N" with::

    FileNotFoundError: [Errno 2] No such file or directory:
        'data/live_cache/served_broker_top_1500.json'

at `theme_cache_build.write_served_file`. The cause is a conjunction of three ordinary facts:
`data/` is gitignored so the checkout brings no directories; the workflow's cache restore lists
only `data/live_themes/*`, so nothing creates `data/live_cache/`; and that write is the FIRST of
the run, so it failed before anything else could.

**WHY NO EXISTING TEST SAW IT, which is the part worth keeping.** Every machine that has ever run
this already had a `data/live_cache/` left over from some earlier scan, so the directory was a
side effect of HISTORY rather than of the code -- and the code's dependence on it was therefore
invisible to every test that ran where that history exists. `state_isolation` does not help:
these paths are RELATIVE, so they resolve against the working directory, and the suites run from
the repo root where `data/` is populated.

So the condition under test is not "a temp data root" but **an empty working directory with no
`data/` whatever**, which is what a fresh runner is. The tests `chdir` into one.

WHAT THESE PIN:

  * `write_served_file` creates its parent, at any depth, and the file round-trips.
  * The SHARD entry point (`--universe broker --slice 0/3`) completes from an empty CWD.
  * The ASSEMBLE entry point (`--universe broker`) completes from an empty CWD.
  * The served file lands where `--snapshot` names it, which is what the assemble job passes
    to `fetch4`.

    python tests/test_theme_cache_fresh_runner.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from scripts import theme_cache_build as TCB    # noqa: E402

#: What the broker leg returns for the themes job, in `served_from_store`'s own shape. The
#: `scan_date` is the real one -- `served_from_universe` sets `"broker_top_%d" % limit` -- and it
#: is what makes the filename `served_broker_top_1500.json`, the exact path run #541 died on.
SERVED = {
    "served": [{"ticker": "AAPL", "market_cap": None, "sector": ""},
               {"ticker": "MSFT", "market_cap": None, "sector": ""}],
    "scan_date": "broker_top_1500",
    "reason": "the broker liquidity ranking",
}

#: SHARADAR-STYLE LABELS, and my first cut used `"2026Q2"` and was REFUSED -- correctly.
#: `_period_end` parses `%d-%b-%Y` or `%Y-%m-%d` and raises rather than guessing a quarter end,
#: because a label and a date that disagree would date the market cap to a quarter the 13F
#: values do not come from. The guard caught my fixture, which is the guard working.
PERIODS = {
    "curr": "30-JUN-2026", "prior": "31-MAR-2026",
    "window_curr": "2026q2", "window_prior": "2026q1",
    "as_of": "2026-10-04", "lag_days": 45,
    "stepped_back": 0, "probed": [], "unpublished": False,
}


class _EmptyCwd(object):
    """A directory with nothing in it, entered for the duration of a test.

    NOT a temp `data/` root: the point is that `data/` does not exist, so a relative write has
    no parent to land in. Creating `data/live_cache` here would reproduce the very condition
    that hid the defect for the life of the job.
    """

    def __enter__(self):
        self.prev = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="fresh-runner-")
        os.chdir(self.tmp)
        return self.tmp

    def __exit__(self, *exc):
        os.chdir(self.prev)
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False


class TheWriterCreatesItsParent(unittest.TestCase):

    def test_an_empty_cwd_really_has_no_data_directory(self):
        """The premise, asserted — or every test below passes for the wrong reason."""
        with _EmptyCwd() as tmp:
            self.assertEqual(os.listdir(tmp), [])
            self.assertFalse(os.path.exists("data"))
            self.assertFalse(os.path.exists(os.path.join("data", "live_cache")))

    def test_write_served_file_creates_the_missing_parent(self):
        with _EmptyCwd():
            path = os.path.join("data", "live_cache", "served_broker_top_1500.json")
            TCB.write_served_file(SERVED, path)
            self.assertTrue(os.path.isfile(path))

    def test_it_round_trips_the_shape_the_two_consumers_read(self):
        with _EmptyCwd():
            path = os.path.join("data", "live_cache", "served_broker_top_1500.json")
            TCB.write_served_file(SERVED, path)
            with io.open(path, encoding="utf-8") as fh:
                got = json.load(fh)
            self.assertEqual(got["scan_date"], "broker_top_1500")
            self.assertEqual([r["ticker"] for r in got["rows"]], ["AAPL", "MSFT"])
            # DICTS, not bare strings. `write_served_file`'s own docstring records the two
            # crashes that came from getting this wrong at two different depths.
            self.assertIsInstance(got["rows"][0], dict)

    def test_it_works_at_a_deeper_missing_path_too(self):
        """`makedirs` rather than `mkdir`: the workflow could point the cache anywhere."""
        with _EmptyCwd():
            path = os.path.join("a", "b", "c", "served.json")
            TCB.write_served_file(SERVED, path)
            self.assertTrue(os.path.isfile(path))

    def test_a_bare_filename_has_no_dirname_and_must_not_raise(self):
        """`os.makedirs("")` raises, which is why the `or "."` is there."""
        with _EmptyCwd():
            TCB.write_served_file(SERVED, "served.json")
            self.assertTrue(os.path.isfile("served.json"))


class _StubbedBuild(object):
    """Everything between the entry point and the write, stubbed — and nothing else.

    The three stubs are exactly the calls that need the network or a populated store:
    `newest_published_periods` probes SEC for published 13F windows, `served_from_universe`
    crawls the broker ranking, `served_from_store` reads a scan, and `M.fetch_all` is the
    ~12,400-call crawl. `F2.build_live` is stubbed for the assemble leg.

    NOTHING ABOUT THE PATHS IS STUBBED, which is the whole point: the filename, the directory
    and the write are the code under test, and a stub that supplied a path would be testing the
    stub. `cache_path()` is left alone too, so the served file lands where the real run puts it.
    """

    def __enter__(self):
        import requests
        import scripts.fidelity2_rebuild as F2
        import scripts.live_theme_sources as M
        self._saved = {
            "periods": TCB.newest_published_periods,
            "from_universe": TCB.served_from_universe,
            "from_store": TCB.served_from_store,
            "caps": TCB.period_market_caps,
            "attach": TCB.attach_period_caps,
            "build_13f": M.build_13f,
            "fetch_all": M.fetch_all,
            "build_live": F2.build_live,
            "rget": requests.get,
            "rreq": requests.Session.request,
        }
        self.calls = {"fetch_all": [], "build_live": [], "build_13f": []}

        # THE NETWORK IS BLOCKED RATHER THAN STUBBED AROUND, AND THAT IS A CORRECTION TO MY
        # FIRST CUT. I enumerated the calls to stub with
        # `grep -nE "M\.[a-z_]+\("` -- a character class that EXCLUDES DIGITS -- so it missed
        # `M.build_13f` at line 775, and the suite went to SEC and came back with a real 404 on
        # `2026q1_form13f.zip`. A test that reaches the internet is a defect whichever way it
        # resolves, and enumerating stubs is exactly the method that just failed. So the
        # transport itself raises: the NEXT unstubbed call fails loudly here instead of
        # quietly downloading 190MB on someone's runner.
        def _no_net(*a, **k):
            raise AssertionError(
                "this suite must not touch the network; something called out to %r"
                % (a[0] if a else k.get("url")))

        requests.get = _no_net
        requests.Session.request = _no_net

        TCB.newest_published_periods = lambda *a, **k: dict(PERIODS)
        TCB.served_from_universe = lambda *a, **k: dict(SERVED)
        TCB.served_from_store = lambda *a, **k: {"served": [], "scan_date": None,
                                                 "reason": "no store in this test"}
        TCB.period_market_caps = lambda served, pend: {
            r["ticker"]: {"market_cap": 1.0e12, "shares_days_stale": 3}
            for r in (served or [])}
        TCB.attach_period_caps = lambda served, caps: {
            "n_set": len(served or []), "n": len(served or []), "n_none": 0,
            "split_tape": "stubbed", "n_split_checked": len(served or [])}
        M.build_13f = lambda **k: self.calls["build_13f"].append(k)
        M.fetch_all = lambda **k: self.calls["fetch_all"].append(k)
        F2.build_live = lambda **k: (self.calls["build_live"].append(k)
                                     or {"rows": [{"ticker": "AAPL"}], "n_served": 2})
        self._M, self._F2, self._rq = M, F2, requests
        return self

    def __exit__(self, *exc):
        TCB.newest_published_periods = self._saved["periods"]
        TCB.served_from_universe = self._saved["from_universe"]
        TCB.served_from_store = self._saved["from_store"]
        TCB.period_market_caps = self._saved["caps"]
        TCB.attach_period_caps = self._saved["attach"]
        self._M.build_13f = self._saved["build_13f"]
        self._M.fetch_all = self._saved["fetch_all"]
        self._F2.build_live = self._saved["build_live"]
        self._rq.get = self._saved["rget"]
        self._rq.Session.request = self._saved["rreq"]
        return False


class TheEntryPointsRunOnAFreshRunner(unittest.TestCase):
    """Run #541's two commands, from a directory that looks like a fresh checkout."""

    def test_the_SHARD_entry_point_completes(self):
        """`python scripts/theme_cache_build.py --universe broker --slice 0/3`"""
        with _EmptyCwd(), _StubbedBuild() as st:
            rc = TCB.main(["--universe", "broker", "--slice", "0/3"])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(
                os.path.join("data", "live_cache", "served_broker_top_1500.json")),
                "the served file is not where --snapshot names it")
            # A shard must crawl and must NOT assemble.
            self.assertEqual(len(st.calls["fetch_all"]), 1)
            self.assertEqual(st.calls["build_live"], [])

    def test_the_shard_hands_the_served_PATH_to_the_crawl(self):
        """`fetch_all(snapshot=...)` is how the crawl learns the universe.

        Asserted because a write that lands in the right place and is not passed on would
        leave the crawl reading `live_theme_sources.SNAPSHOT`, the pinned file — which is the
        defect the workflow's own comment says made `form4_live` empty.
        """
        with _EmptyCwd(), _StubbedBuild() as st:
            TCB.main(["--universe", "broker", "--slice", "0/3"])
            kw = st.calls["fetch_all"][0]
            self.assertTrue(str(kw.get("snapshot") or "").endswith(
                "served_broker_top_1500.json"), kw.get("snapshot"))
            self.assertEqual((kw.get("slice_i"), kw.get("slice_n")), (0, 3))

    def test_the_ASSEMBLE_entry_point_completes(self):
        """`python scripts/theme_cache_build.py --universe broker`"""
        with _EmptyCwd(), _StubbedBuild() as st:
            rc = TCB.main(["--universe", "broker"])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(
                os.path.join("data", "live_cache", "served_broker_top_1500.json")))
            self.assertEqual(len(st.calls["build_live"]), 1)

    def test_the_assemble_leg_writes_the_cache_where_the_workflow_caches_it(self):
        """`LIVE_THEMES_CACHE=data/live_cache/theme_columns.json`, and its parent is created.

        `fidelity2_rebuild.build_live` ALREADY does `os.makedirs` before its write — measured,
        not assumed — so this asserts the path it would be given rather than re-testing a guard
        that is already there. The point is that the directory is the same one, so whichever
        leg runs first creates it for the other.
        """
        with _EmptyCwd(), _StubbedBuild() as st:
            os.environ["LIVE_THEMES_CACHE"] = os.path.join(
                "data", "live_cache", "theme_columns.json")
            try:
                TCB.main(["--universe", "broker"])
            finally:
                os.environ.pop("LIVE_THEMES_CACHE", None)
            kw = st.calls["build_live"][0]
            self.assertEqual(kw.get("cache_path"),
                             os.path.join("data", "live_cache", "theme_columns.json"))
            self.assertTrue(os.path.isdir(os.path.join("data", "live_cache")))


class TheNetworkBlockBites(unittest.TestCase):
    """The block is the reason the next unstubbed call cannot reach SEC. Proved, not assumed."""

    def test_requests_get_raises_inside_the_harness(self):
        with _EmptyCwd(), _StubbedBuild():
            import requests
            with self.assertRaises(AssertionError):
                requests.get("https://www.sec.gov/anything")

    def test_and_is_restored_afterwards(self):
        """A harness that leaves `requests` broken would poison every later suite."""
        with _EmptyCwd(), _StubbedBuild():
            pass
        import requests
        self.assertTrue(callable(requests.get))
        self.assertNotIn("_no_net", getattr(requests.get, "__name__", ""))


class TheGuardIsNotVacuous(unittest.TestCase):
    """Without the `makedirs`, these tests must fail — or they prove nothing about the fix."""

    def test_an_unprotected_write_to_a_missing_parent_really_does_raise(self):
        """The exact failure run #541 reported, reproduced so the fix has something to fix.

        If this did NOT raise, the platform would be creating the directory for us and every
        assertion above would be passing for a reason unrelated to the code.
        """
        with _EmptyCwd():
            path = os.path.join("data", "live_cache", "served_broker_top_1500.json")
            with self.assertRaises(FileNotFoundError):
                with io.open(path, "w", encoding="utf-8") as fh:
                    fh.write("{}")

    def test_the_writer_calls_makedirs(self):
        """Read from the SOURCE, because the behaviour above could be satisfied by a caller
        that happened to create the directory first. This pins the writer itself."""
        import ast
        with open(os.path.join(REPO, "scripts", "theme_cache_build.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "write_served_file")
        body = ast.unparse(fn)
        self.assertIn("makedirs", body)
        self.assertIn("exist_ok=True", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
