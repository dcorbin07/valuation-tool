"""
THE FREE ROUTE, PART 2: the production build's real blockers, and the copy that was a literal.

Four things this file pins, every one of them found by a real run failing rather than by reading:

1. **SEC'S DERIVED 13F WINDOW DOES NOT EXIST YET.** `latest_complete_periods(2026-09-30)` asks
   for period **30-JUN-2026**, window `01jun2026-31aug2026`, and SEC returns **404**. HEAD
   probes: `01sep2025-30nov2025` 200 (85.6 MB), `01dec2025-28feb2026` 200 (90.3 MB),
   `01mar2026-31may2026` 200 (99.4 MB), `01jun2026-31aug2026` **404**, `01sep2026-30nov2026`
   **404**. The build died **after the first window had downloaded and aggregated** — the
   expensive half. And it corrects the builder's own warning: it prints `<-- STALE` when the
   pinned constants differ from the derived pair, but today the **pinned** pair is what SEC
   publishes and the **derived** pair is the missing one.
2. **THE LOCAL STORE HOLDS ONLY THE 2099-01-01 TEST FIXTURE**, so the scan route builds a
   ONE-NAME cache and reports it as a build.
3. **A MONKEYPATCHED MODULE CONSTANT DOES NOT REACH AN ALREADY-BOUND DEFAULT ARGUMENT.**
   `M.SNAPSHOT = path` printed "served file ..." and the crawl still used the pinned path,
   because `load_served(snapshot=SNAPSHOT)` binds its default at definition time.
4. **A SHARD MUST NOT ASSEMBLE.** It has fetched a third of the universe, and a cache written
   from that would cover a third with nothing on it saying so.

Run:  python -m pytest tests/test_free_route_p2.py
      python tests/test_free_route_p2.py
"""
from __future__ import annotations

import ast
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestThePublishedWindowProbe(unittest.TestCase):

    def _mod(self):
        from scripts import theme_cache_build as TCB
        return TCB

    def test_it_STEPS_BACK_when_the_derived_window_is_not_published(self):
        """The whole point. A 404 halfway through is not a build."""
        TCB = self._mod()
        import requests

        class _R:
            def __init__(self, code):
                self.status_code = code

        seen = []

        def head(url, **kw):
            seen.append(url)
            # The newest window 404s; anything older is published.
            return _R(404 if "01jun2026-31aug2026" in url else 200)

        real = requests.head
        try:
            requests.head = head
            per = TCB.newest_published_periods(__import__("datetime").date(2026, 9, 30))
        finally:
            requests.head = real
        self.assertGreaterEqual(per.get("stepped_back", 0), 1,
                                "it did not step back off the unpublished window")
        self.assertFalse(per.get("unpublished"), per.get("probed"))
        self.assertTrue(any("01jun2026-31aug2026" in u for u in seen),
                        "it never probed the derived window, so the step-back is untested")

    def test_it_REFUSES_rather_than_walking_back_for_ever(self):
        """Stepping back past a year would silently build a cache from genuinely old holdings.
        `max_back` is small on purpose, and exhausting it is reported."""
        TCB = self._mod()
        import requests

        class _R:
            status_code = 404

        real = requests.head
        try:
            requests.head = lambda url, **kw: _R()
            per = TCB.newest_published_periods(__import__("datetime").date(2026, 9, 30))
        finally:
            requests.head = real
        self.assertTrue(per.get("unpublished"), "exhausting the step-back was not reported")

    def test_the_probe_uses_the_DOWNLOADERS_OWN_url_constant(self):
        """B7. A second copy of SEC's path would let the probe say "published" about a URL the
        downloader never fetches."""
        src = io.open(os.path.join(REPO, "scripts/theme_cache_build.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "newest_published_periods")
        body = ast.unparse(fn)
        self.assertIn("M.DATASET_URL", body, "the probe builds its own URL")
        self.assertNotIn("sec.gov/files/structureddata", body,
                         "the probe hard-codes SEC's path alongside the downloader's")


class TestTheUniverseOverride(unittest.TestCase):

    def test_a_TICKER_FILE_is_accepted_and_reports_its_source(self):
        """`scan_date` names the SOURCE, because a cache is only meaningful beside a statement
        of which population it covers."""
        import tempfile
        from scripts import theme_cache_build as TCB
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "u.txt")
            io.open(p, "w", encoding="utf-8").write("aapl\nMSFT\n\njpm\n")
            su = TCB.served_from_universe(p)
        # DICTS, not bare tickers. THIS ASSERTION USED TO READ `["AAPL", "JPM", "MSFT"]` and
        # that is why it never caught the shape bug: the test encoded the broken shape, so it
        # PROTECTED the defect instead of finding it. `served_from_universe`'s own docstring
        # claimed "SAME SHAPE" as `served_from_store` while returning strings, the crawl ran two
        # hours over 1,500 names, and `join_13f` then died on `row["ticker"]`.
        self.assertEqual([r["ticker"] for r in su["served"]], ["AAPL", "JPM", "MSFT"])
        self.assertEqual(sorted(su["served"][0].keys()),
                         ["market_cap", "name", "sector", "ticker"])
        self.assertIn("file:", su["scan_date"])

    def test_an_UNREADABLE_file_is_a_refusal_with_a_reason_not_an_empty_build(self):
        from scripts import theme_cache_build as TCB
        su = TCB.served_from_universe(os.path.join("nope", "nope.txt"))
        self.assertEqual(su["served"], [])
        self.assertIn("could not read", su["reason"])

    def test_the_SHAPE_matches_the_store_route_so_nothing_downstream_learns_a_second_one(self):
        import tempfile
        from scripts import theme_cache_build as TCB
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "u.txt")
            io.open(p, "w", encoding="utf-8").write("AAPL\n")
            a = set(TCB.served_from_universe(p))
        b = set(TCB.served_from_store())
        self.assertEqual(a, b, "the two universe routes return different shapes")

    def test_BOTH_universe_sources_return_the_SAME_shape(self):
        """The property `served_from_universe`'s docstring asserts, which nothing checked.

        Two sources hand the builder a universe and two consumers read it -- `fetch_all` through
        `load_served`, and `join_13f` directly. All four have to agree, and a docstring saying so
        is not a check. It is asserted against `served_from_store`'s own output rather than
        against a literal key list, so the two cannot drift apart without this failing.
        """
        class Fake:
            def latest_scan_date(self):
                return "2026-09-29"

            def load_snapshot(self, d=None, top=None):
                return [{"ticker": "aapl", "name": "Apple", "market_cap": 1.0,
                         "sector": "Tech"}]

        from scripts import theme_cache_build as TCB
        from_store = TCB.served_from_store(Fake())["served"]
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "u.txt")
            with io.open(fp, "w", encoding="utf-8") as fh:
                fh.write("AAPL\n")
            from_file = TCB.served_from_universe(fp)["served"]
        self.assertEqual(sorted(from_store[0].keys()), sorted(from_file[0].keys()),
                         "the two universe sources disagree about the row shape")
        self.assertTrue(all(isinstance(r["ticker"], str) for r in from_file))

    def test_the_served_file_ROUND_TRIPS_through_load_served(self):
        """Both consumers read it through `load_served`, so that is the contract to pin.

        The second crash came from the WRITER: it wrapped each element as `{"ticker": t}` on the
        assumption it was a bare string, so once the shape was fixed it produced
        `{"ticker": {...dict...}}` and `fetch_all` died on `tkr.upper()`. The two crashes were one
        defect surfacing at two depths.
        """
        from scripts import theme_cache_build as TCB
        from scripts import live_theme_sources as M
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "u.txt")
            with io.open(fp, "w", encoding="utf-8") as fh:
                fh.write("AAPL\nJPM\n")
            su = TCB.served_from_universe(fp)
            # THE PRODUCTION WRITER, not a hand-rolled copy. A first cut of this test built the
            # file itself with its own `json.dump`, so it tested the TEST and the writer stayed
            # uncovered -- a mutation that re-wrapped every row as `{"ticker": t}` went
            # undetected. B7, inside a test that existed to pin the shape.
            sp = TCB.write_served_file(su, os.path.join(d, "served.json"))
            got = M.load_served(sp)
        self.assertEqual([r["ticker"] for r in got], ["AAPL", "JPM"])
        self.assertTrue(all(isinstance(r["ticker"], str) for r in got),
                        "a ticker came back as something other than a string")

    def test_the_BROKER_path_returns_the_same_rows_as_the_file_path(self):
        """s1: the broker branch was untested, and it is the one the Action uses.

        `broker_universe.build` is stubbed so this needs no network and no broker token -- the
        property under test is the SHAPE the branch produces, not the ranking it produces.
        """
        from scripts import theme_cache_build as TCB
        from valuation.screener import broker_universe
        orig = broker_universe.build
        broker_universe.build = lambda cfg, limit=None: [
            {"ticker": "aapl", "name": "Apple Inc", "market_cap": None, "sector": "",
             "price": 1.0},
            {"ticker": "JPM", "name": "JPMorgan", "market_cap": 2.0, "sector": "Financials"}]
        self.addCleanup(lambda: setattr(broker_universe, "build", orig))
        su = TCB.served_from_universe("broker", limit=2)
        self.assertEqual([r["ticker"] for r in su["served"]], ["AAPL", "JPM"])
        self.assertEqual(sorted(su["served"][0].keys()),
                         ["market_cap", "name", "sector", "ticker"])
        self.assertTrue(all(isinstance(r["ticker"], str) for r in su["served"]))
        self.assertEqual(su["scan_date"], "broker_top_2")

    def test_a_REPEATED_name_is_not_crawled_twice(self):
        """s4: the crawl is ~5 seconds per name, so a duplicate is real wasted wall clock."""
        from scripts import theme_cache_build as TCB
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "u.txt")
            with io.open(fp, "w", encoding="utf-8") as fh:
                fh.write("AAPL\naapl\n  AAPL  \nJPM\n")
            su = TCB.served_from_universe(fp)
        self.assertEqual([r["ticker"] for r in su["served"]], ["AAPL", "JPM"])

    def test_an_ABSENT_market_cap_stays_absent_rather_than_becoming_zero(self):
        """s5: and this one is load-bearing, because market_cap feeds a VALIDATION GUARD.

        `join_13f`'s anchor is institutional dollars over market cap, required in
        `(0, ANCHOR_MAX]`. A market cap of 0.0 is not "unknown" -- it makes the division either
        blow up or produce a number, and a guard that exists so a fuzzy name match cannot fake a
        company must not be handed a filled-in denominator. `None` makes the anchor refuse, which
        is the correct and measured behaviour (1,329 of 1,500 `anchor_failed` on the broker
        universe).
        """
        from scripts import theme_cache_build as TCB
        from valuation.screener import broker_universe
        orig = broker_universe.build
        broker_universe.build = lambda cfg, limit=None: [
            {"ticker": "AAPL", "name": "Apple", "market_cap": None, "sector": ""}]
        self.addCleanup(lambda: setattr(broker_universe, "build", orig))
        su = TCB.served_from_universe("broker", limit=1)
        self.assertIsNone(su["served"][0]["market_cap"],
                          "an unknown market cap was filled in, and it feeds the anchor guard")


class TestTheShardRefusesToAssemble(unittest.TestCase):

    def test_a_shard_returns_BEFORE_the_cache_is_written(self):
        """A cache built from a third of the universe would cover a third with nothing on it
        saying so -- and a thin cache is indistinguishable from a complete one once written."""
        src = io.open(os.path.join(REPO, "scripts/theme_cache_build.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        body = ast.unparse(fn)
        # READ THE STATEMENT TREE, NOT A CHARACTER WINDOW. A first cut looked for `return 0`
        # within 400 characters of the word SHARD and found an UNRELATED one, so deleting the
        # shard's own return left it green (mutation p5, MISSED). The property is that the
        # `if a.slice:` block AFTER the crawl contains a Return.
        i_fetch = body.index("fetch_all")
        i_shard = body.index("SHARD")
        self.assertLess(i_fetch, i_shard, "the shard guard runs before the crawl")
        after_crawl = [n for n in ast.walk(fn)
                       if isinstance(n, ast.If)
                       and "SHARD" in ast.unparse(n)
                       and any(isinstance(x, ast.Return) for x in ast.walk(n))]
        self.assertTrue(after_crawl,
                        "the shard branch prints and then falls through to assembly")

    def test_a_MALFORMED_slice_is_refused(self):
        from scripts import theme_cache_build as TCB
        # `-1/3` is argparse's to reject (it reads as a flag), not this code's -- so it is
        # not in the list. Testing it here would be testing argparse.
        for bad in ("3/3", "4/3", "x/3", "1"):
            with self.subTest(slice=bad):
                # A VALID universe path is deliberately NOT supplied: the point is that the
                # argument check fires BEFORE any universe resolution, so a nonsense shard is
                # reported even when everything else is also wrong.
                self.assertEqual(TCB.main(["--universe", "nope.txt", "--slice", bad]), 4,
                                 "the slice check is unreachable behind another refusal")


class TestTheSnapshotIsPassedNotMonkeypatched(unittest.TestCase):

    def test_fetch_all_TAKES_a_snapshot(self):
        """The defect: `load_served(snapshot=SNAPSHOT)` binds its default at DEFINITION time, so
        reassigning the module constant after import does not reach it. The build printed that
        it had set a new path and then failed on the old one."""
        import inspect
        from scripts import live_theme_sources as M
        self.assertIn("snapshot", inspect.signature(M.fetch_all).parameters,
                      "fetch_all cannot be told which snapshot to read")

    def test_fetch_all_actually_READS_the_snapshot_it_is_handed(self):
        """A parameter that is accepted and ignored is worse than none -- it reads as fixed.

        An earlier cut asserted only that the parameter EXISTS and that the builder passes it,
        so dropping the use inside `fetch_all` left both green (mutation p7, MISSED) and the
        crawl would silently go back to the pinned path. Asserted behaviourally: a bogus
        snapshot path must produce the refusal naming THAT path.
        """
        from scripts import live_theme_sources as M
        bogus = os.path.join("nope", "definitely-not-here.json")
        try:
            M.fetch_all(snapshot=bogus)
        except SystemExit as e:
            self.assertIn("definitely-not-here", str(e),
                          "the snapshot argument was ignored: %s" % e)
            return
        except Exception as e:                                          # noqa: BLE001
            self.fail("expected the served-snapshot refusal, got %s" % type(e).__name__)
        self.fail("a missing snapshot did not refuse")

    def test_the_builder_PASSES_it_rather_than_assigning_the_constant(self):
        src = io.open(os.path.join(REPO, "scripts/theme_cache_build.py"),
                      encoding="utf-8").read()
        self.assertIn("fetch_all(snapshot=", src)
        self.assertNotIn("M.SNAPSHOT =", src,
                         "the builder is back to reassigning a constant that cannot be reached")


class TestTheThemeCountCopy(unittest.TestCase):
    """(11c) The contradiction, resolved by NAMING the two facts rather than collapsing them."""

    def _live(self, **over):
        base = {"value": 1.0, "quality": 1.0, "momentum": 0.99, "size": 1.0,
                "capital_discipline": 0.97, "insider": 0.0, "institutional": 0.0}
        base.update(over)
        return base

    def test_the_denominator_is_the_DEPLOYED_SEVEN_not_the_union_of_two_buckets(self):
        """A first cut unioned the bucket weight sets and got EIGHT, because `growth` carries
        weight in the speculative bucket only -- the same MEMBERSHIP difference session 67
        measured. The copy's "of seven" refers to the deployed composite."""
        from valuation.web import theme_status as TS
        from valuation.edge.valquo_index import FLAT_SEVEN
        c = TS.counts()
        self.assertEqual(c["n_weighted"], 7, c["weighted"])
        self.assertEqual(set(c["weighted"]), set(FLAT_SEVEN) & set(TS.THEMES))
        self.assertNotIn("growth", c["weighted"])

    def test_WIRED_and_CONTRIBUTING_are_reported_SEPARATELY(self):
        """Both sides of the contradiction were TRUE: `insider`/`institutional` are wired (not
        dormant) and contributed 0.0. Collapsing them would lose one of the two facts."""
        from valuation.web import theme_status as TS
        c = TS.counts(self._live())
        self.assertNotIn("insider", c["dormant"], "a wired theme is reported dormant")
        self.assertIn("insider", c["not_contributing_now"])
        self.assertEqual(c["n_contributing_now"], 5)

    def test_the_SENTENCE_is_derived_and_flips_when_the_cache_lands(self):
        """The literal had already been wrong twice in OPPOSITE directions."""
        from valuation.web import theme_status as TS
        today = TS.sentence(self._live())
        self.assertIn("5 of the backtest's 7", today)
        self.assertIn("insider", today)
        landed = TS.sentence(self._live(insider=0.9, institutional=0.9))
        self.assertIn("all 7", landed)
        self.assertNotIn("5 of", landed)

    def test_UNAVAILABLE_health_is_its_own_branch_not_zero_themes(self):
        """An empty dict would make every theme read as contributing nothing, so the copy would
        claim the ranking runs on ZERO themes on a day the store was merely unreachable."""
        from valuation.web import theme_status as TS
        s = TS.sentence(None)
        self.assertIn("not available", s)
        self.assertNotIn("0 of", s)

    def test_the_TEMPLATE_reads_it_rather_than_holding_a_literal(self):
        src = io.open(os.path.join(REPO, "valuation/web/templates/methodology.html"),
                      encoding="utf-8").read()
        self.assertIn("theme_sentence", src)

    def test_the_context_passes_None_rather_than_an_empty_dict_when_it_cannot_read(self):
        src = io.open(os.path.join(REPO, "valuation/web/app.py"), encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "_theme_contributing")
        body = ast.unparse(fn)
        self.assertIn("return None", body)
        self.assertNotIn("return {}", body, "an empty dict would read as zero themes live")


class TestTheReconstructionComputation(unittest.TestCase):
    """(13) The computation, which must refuse rather than guess."""

    def test_it_DELEGATES_to_the_writers_own_row_function(self):
        """B7, and here it is the entire argument for trusting the output: `contract_row`
        already resolves the book in force, prices on the same routing and the same adjusted
        basis, and refuses rather than returning a partial number.

        READ OFF THE CALL NODE, NOT THE UNPARSED TEXT. A first cut asserted
        `assertIn("refuse_before_close=False", ast.unparse(fn))` -- and `unparse` includes the
        DOCSTRING, which explains why that argument is False. So flipping the real argument to
        True left the assertion satisfied **by the prose** (mutation r2, MISSED). This is the
        substring family INVERTED: I have been careful that a BAN must not match prose, and a
        positive assertion has exactly the same failure mode.
        """
        src = io.open(os.path.join(REPO, "valuation/screener/track_reconstruct.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "reconstruct")
        calls = [c for c in ast.walk(fn)
                 if isinstance(c, ast.Call) and getattr(c.func, "attr", None) == "contract_row"]
        self.assertEqual(len(calls), 1, "the reconstruction no longer delegates")
        kw = {k.arg: k.value for k in calls[0].keywords}
        self.assertIn("refuse_before_close", kw, "it cannot compute a past day at all")
        self.assertIs(kw["refuse_before_close"].value, False,
                      "it would refuse every past day, or mark an unclosed session")

    def test_a_day_it_cannot_price_is_a_REFUSAL_never_a_gap_filled_guess(self):
        """Measured against this checkout, where the bound book is absent: two dates in, zero
        computed, two refusals naming the missing book."""
        from valuation.screener import track_reconstruct as TR
        r = TR.reconstruct(["2026-08-14", "2026-09-02"],
                           meta_path=os.path.join("nope", "book.json"))
        self.assertEqual(r["n_requested"], 2)
        self.assertEqual(r["n_computed"], 0)
        self.assertEqual(len(r["refused"]), 2)
        for x in r["refused"]:
            self.assertTrue(x["reason"], "a refusal carried no reason")
        self.assertEqual(r["points"], [])

    def test_the_chart_keeps_the_RECORD_datasets_on_the_records_own_rows(self):
        """The union axis gives a reconstructed day an x position; the record's three datasets
        are re-indexed onto it with NULLS, so a recorded point is never invented for a day the
        record does not hold."""
        js = io.open(os.path.join(REPO, "valuation/web/static/app.js"),
                     encoding="utf-8").read()
        self.assertIn("const recon = ((d && d.reconstructed) || {}).points || []", js)
        self.assertIn('onAxis(s, "valquo")', js)
        self.assertIn('onAxis(s, "spy")', js)
        self.assertIn('onAxis(s, "spmo")', js)
        self.assertNotIn("data: s.map(", js,
                         "a record dataset still indexes off `series` while the axis is the "
                         "union, so its points would be shifted")

    def test_the_reconstruction_is_drawn_as_MARKERS_with_no_line(self):
        """A line asserts continuity between its ends. These days are exactly the ones the
        record does NOT hold, so joining them would draw the claim the label exists to deny."""
        js = io.open(os.path.join(REPO, "valuation/web/static/app.js"),
                     encoding="utf-8").read()
        i = js.index("reconstructed — not part of the record")
        block = js[i:i + 600]
        self.assertIn("showLine: false", block)
        self.assertIn("pointRadius: 4", block)
        self.assertIn('pointBackgroundColor: "#ffffff"', block)


class BuildDateIsNotPeriodDate(unittest.TestCase):
    """`status()` measured when the cache was BUILT and never which period it DESCRIBES.

    `MAX_AGE_DAYS = 120` carries a comment saying a cache not rebuilt in a quarter "is describing
    a period that has rolled" -- which assumes the two track each other. THEY DO NOT when SEC has
    not published the latest window: the builder correctly steps back a quarter, so a cache built
    TODAY can describe a period that ended six months ago and still read `age_days: 0`.

    AND THIS IS A CONSEQUENCE OF THIS SESSION'S OWN STEP-BACK FIX. Before it the builder 404ed
    and wrote nothing -- a loud failure. After it the build succeeds with an older period, which
    is a QUIET staleness, and that is the direction this project warns about hardest. So the
    number has to travel.

    REPORTED, NOT REFUSED: measured 2026-09-30, SEC had not published the 30-JUN-2026 window about
    six weeks past the filing deadline, so the freshest buildable cache is 183 days behind.
    Refusing would switch two themes off for a reason outside anyone's control.
    """

    def _cache(self, built, periods):
        import json as _json
        d = tempfile.mkdtemp()
        path = os.path.join(d, "tc.json")
        # `with`, because an unclosed handle leaves the fixture UNFLUSHED and `status()` then
        # reports "no readable cache" -- which reads as the feature being broken rather than the
        # test being broken. Four of these five tests failed that way first.
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(_json.dumps(
                {"built": built, "periods": periods, "periods_source": "derived",
                 "rows": {"AAPL": {"inst_accum": 0.5}}}))
        from valuation.screener import live_themes as LT
        self._prev = getattr(LT, "CACHE")
        LT.CACHE = path
        # `_loaded` IS THE MEMO, NOT `_cache`. Clearing `_cache` alone LOOKS like a reset and is
        # not -- `_load` returns early on `_loaded`, so the second fixture in a process reads the
        # first one's miss and `status()` reports "no readable cache". Four of these five tests
        # failed that way, and the first passed only because `_loaded` starts False. The same
        # shape as a default bound at definition time: the knob that looks like the state isn't.
        LT._cache = None
        LT._loaded = False
        self.addCleanup(lambda: (setattr(LT, "CACHE", self._prev),
                                 setattr(LT, "_cache", None),
                                 setattr(LT, "_loaded", False)))
        return LT

    def test_a_cache_built_TODAY_can_be_half_a_year_behind_and_says_so(self):
        import datetime as dt
        LT = self._cache(dt.date.today().isoformat(), ["31-DEC-2025", "31-MAR-2026"])
        st = LT.status()
        self.assertEqual(st["age_days"], 0, "the fixture is not a fresh build")
        self.assertTrue(st["available"], "build-age behaviour changed; that was not the fix")
        self.assertEqual(st["period_curr"], "31-MAR-2026")
        self.assertGreater(st["period_age_days"], 150,
                           "the period age is not reported, so a fresh-looking cache can "
                           "silently describe a rolled quarter")

    def test_the_two_ages_are_SEPARATE_fields_and_neither_stands_in_for_the_other(self):
        """One combined "age" is how the conflation came about in the first place."""
        import datetime as dt
        LT = self._cache(dt.date.today().isoformat(), ["31-DEC-2025", "31-MAR-2026"])
        st = LT.status()
        self.assertIn("age_days", st)
        self.assertIn("period_age_days", st)
        self.assertNotEqual(st["age_days"], st["period_age_days"])

    def test_an_UNDATED_period_reports_None_rather_than_zero(self):
        """Zero would read as "the period ended today", the most flattering possible answer."""
        import datetime as dt
        LT = self._cache(dt.date.today().isoformat(), ["", "not-a-date"])
        st = LT.status()
        self.assertIsNone(st["period_age_days"])

    def test_a_cache_with_NO_periods_key_still_reports_rather_than_raising(self):
        """Old caches predate the field; a missing one must not take the health block down."""
        import datetime as dt
        LT = self._cache(dt.date.today().isoformat(), [])
        st = LT.status()
        self.assertIsNone(st["period_curr"])
        self.assertIsNone(st["period_age_days"])
        self.assertTrue(st["available"])

    def test_the_build_age_still_decides_availability(self):
        """The period age REPORTS; it must not have quietly become a second gate."""
        LT = self._cache("2020-01-01", ["31-DEC-2025", "31-MAR-2026"])
        st = LT.status()
        self.assertFalse(st["available"], "the build-age gate stopped working")
        LT2 = self._cache("2026-09-30", ["31-DEC-1999", "31-MAR-2000"])
        st2 = LT2.status()
        self.assertTrue(st2["available"],
                        "the period age became a refusal, which was explicitly not the fix")
        self.assertGreater(st2["period_age_days"], 9000)


class AZeroRowCacheIsRefused(unittest.TestCase):
    """A zero-row cache reads as a HEALTHY cache that happens to know nothing about anybody.

    MEASURED on a real one written 2026-09-30: `live_themes.status()` returns
    `available: true, rows: 0, reason: ""` and `columns_for()` returns `{}` for every ticker. So
    it would have REPLACED A LOUD ABSENT-FILE STATE WITH A QUIET PRESENT-BUT-EMPTY ONE, which is
    strictly worse — the absent file is the condition the whole item exists to fix, and it is at
    least visible.

    The reasoning was already written down twice in this codebase and applied to neither place
    that needed it: the missing-period guard says such a cache "would look like a clean build of a
    universe with no institutional data", and `served_from_store` refuses an empty INPUT for the
    same reason. Nothing refused an empty OUTPUT.
    """

    def test_build_live_REFUSES_rather_than_writing_an_empty_cache(self):
        import ast as _ast
        src = io.open(os.path.join(REPO, "scripts/fidelity2_rebuild.py"),
                      encoding="utf-8").read()
        fn = next(n for n in _ast.walk(_ast.parse(src))
                  if isinstance(n, _ast.FunctionDef) and n.name == "build_live")
        # The refusal must be a RAISE, not a warning, and it must sit BEFORE the payload is
        # assembled -- a refusal after the write is not a refusal.
        raises = [n for n in _ast.walk(fn)
                  if isinstance(n, _ast.Raise)
                  and "zero-row" in _ast.unparse(n)]
        self.assertEqual(len(raises), 1, "the zero-row refusal is gone or duplicated")
        body = _ast.unparse(fn)
        i_guard = body.index("zero-row")
        i_write = body.index("json.dump") if "json.dump" in body else len(body)
        self.assertLess(i_guard, i_write, "it writes the file and then refuses")

    def test_the_refusal_NAMES_the_likely_cause(self):
        """An empty result has one dominant cause here and the message should say it.

        Measured: 1,329 of 1,500 rows came back `anchor_failed` because the broker universe
        carries `market_cap: None`, so the anchor (institutional dollars over market cap) could
        not be computed. A refusal that says only "zero rows" sends the next reader to the crawl,
        which is the expensive and correct part.
        """
        # SCOPED TO THE RAISE NODE. A first cut asserted these strings were somewhere in the
        # FILE -- and `anchor_failed` appears in two unrelated rung checks, so stripping them out
        # of the MESSAGE left it green. The same wrong-object slip as every other guard repaired
        # in this session: assert on the object, not on the file that contains it.
        import ast as _ast
        src = io.open(os.path.join(REPO, "scripts/fidelity2_rebuild.py"),
                      encoding="utf-8").read()
        fn = next(n for n in _ast.walk(_ast.parse(src))
                  if isinstance(n, _ast.FunctionDef) and n.name == "build_live")
        raises = [_ast.unparse(n) for n in _ast.walk(fn)
                  if isinstance(n, _ast.Raise) and "zero-row" in _ast.unparse(n)]
        self.assertEqual(len(raises), 1)
        msg = raises[0]
        self.assertIn("anchor_failed", msg,
                      "the refusal no longer names the rung that explains an empty build")
        self.assertIn("market_cap", msg,
                      "the refusal no longer names the missing field")

    def test_a_cache_with_rows_still_writes(self):
        """The refusal must not have become "refuse any build"."""
        import ast as _ast
        src = io.open(os.path.join(REPO, "scripts/fidelity2_rebuild.py"),
                      encoding="utf-8").read()
        fn = next(n for n in _ast.walk(_ast.parse(src))
                  if isinstance(n, _ast.FunctionDef) and n.name == "build_live")
        # Guarded on emptiness, not on a constant: `if not rows:` and nothing stronger.
        tests_on_rows = [n for n in _ast.walk(fn)
                         if isinstance(n, _ast.If)
                         and "zero-row" in _ast.unparse(n)]
        self.assertEqual(len(tests_on_rows), 1)
        cond = _ast.unparse(tests_on_rows[0].test)
        self.assertEqual(cond, "not rows",
                         "the refusal condition is no longer simply an empty result: %s" % cond)


if __name__ == "__main__":
    unittest.main(verbosity=1)
