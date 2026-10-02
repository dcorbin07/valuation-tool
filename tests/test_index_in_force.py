# -*- coding: utf-8 -*-
"""THE VALQUO INDEX IS THE BOOK IN FORCE, NOT A DAILY PICK — Don's ruling, 2026-10-02.

`/api/valquo-index` called `build_index(st.load_snapshot(st.latest_scan_date()))` on every
request, so the tab's holdings were rebuilt from each day's scan and changed daily, while the
forward record beneath them tracked a fixed 86-name book formed 2026-07-30. The tab's intro said
so out loud: "The holdings are rebuilt from each day's scan. The forward record further down is a
separate, fixed book." Two books under one name, which Don read as the Index having rebalanced.

MEASURED on the bound record: 86 positions, formed 2026-07-30, scan 2026-07-24 — against a
default `roth` config serving 25 names off today's scan.

NOT A VINTAGE EVENT, and these tests are what make that checkable: nothing here scores, weights
or constructs anything, `valquo_index.build_index` is untouched, and no recorded figure moves.
"""
from __future__ import annotations

import ast
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.screener import index_in_force as IF   # noqa: E402
from valuation.screener import index_mark as IM       # noqa: E402

#: The bound record's own figures, as a committed literal. `MA13`'s idiom: a test that derives
#: its expectation from the thing under test cannot fail with it.
REAL_SCAN = "2026-07-24"
REAL_FORMED = "2026-07-30"
RUNBOOK_NEXT = "2026-10-22"          # REBALANCE_RUNBOOK_2026-10-22.md, by its own arithmetic


def _book_file(tmp, positions, *, inception=REAL_FORMED, scan=REAL_SCAN, rebalances=None):
    p = os.path.join(tmp, "valquo_track.json")
    body = {"inception_date": inception, "scan_date": scan, "benchmark": "SPY",
            "positions": positions}
    if rebalances:
        body["rebalances"] = rebalances
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    return p


def _eq(a, b, places=6):
    return round(a - b, places) == 0


class WhichBookIsInForce(unittest.TestCase):

    def test_with_no_rebalances_the_INCEPTION_book_is_in_force(self):
        with tempfile.TemporaryDirectory() as d:
            p = _book_file(d, [{"ticker": "A", "weight": 0.6},
                               {"ticker": "B", "weight": 0.4}])
            b = IF.book_in_force(meta_path=p, as_of="2026-09-01")
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["formed_on"], REAL_FORMED)
        self.assertTrue(b["is_inception_book"])
        self.assertEqual(b["n_rebalances_so_far"], 0)
        self.assertEqual([r["ticker"] for r in b["positions"]], ["A", "B"])

    def test_the_LATEST_event_on_or_before_the_date_governs(self):
        """And the rebalance DAY itself takes the new book -- `R <= M`, which is
        `index_mark.event_in_force`'s own rule, imported rather than re-derived."""
        reb = [{"date": "2026-08-20", "scan_date": "2026-08-14",
                "positions": [{"ticker": "C", "weight": 1.0}]}]
        with tempfile.TemporaryDirectory() as d:
            p = _book_file(d, [{"ticker": "A", "weight": 1.0}], rebalances=reb)
            before = IF.book_in_force(meta_path=p, as_of="2026-08-19")
            on = IF.book_in_force(meta_path=p, as_of="2026-08-20")
            after = IF.book_in_force(meta_path=p, as_of="2026-09-30")
        self.assertEqual([r["ticker"] for r in before["positions"]], ["A"])
        self.assertEqual([r["ticker"] for r in on["positions"]], ["C"],
                         "the rebalance day must take the NEW book")
        self.assertEqual([r["ticker"] for r in after["positions"]], ["C"])
        self.assertEqual(on["formed_on"], "2026-08-20")
        self.assertEqual(on["scan_date"], "2026-08-14")
        self.assertFalse(on["is_inception_book"])
        self.assertEqual(on["n_rebalances_so_far"], 1)

    def test_an_unreadable_record_REFUSES_and_returns_no_positions(self):
        """Never a partial book. A caller that cannot tell "no book" from "half a book" is how
        a thin holding list gets published as the Index."""
        b = IF.book_in_force(meta_path=os.path.join(REPO, "nope-no-book.json"))
        self.assertFalse(b["ok"])
        self.assertEqual(b["positions"], [])
        self.assertTrue(b["reason"])

    def test_a_date_BEFORE_inception_has_no_book_in_force(self):
        with tempfile.TemporaryDirectory() as d:
            p = _book_file(d, [{"ticker": "A", "weight": 1.0}])
            b = IF.book_in_force(meta_path=p, as_of="2026-07-01")
        self.assertFalse(b["ok"])
        self.assertIn("inception", b["reason"])

    def test_it_reads_the_REAL_record_and_reports_the_measured_figures(self):
        """Against the primary root, because the worktree carries `data/` without the book --
        the same resolution trap the reconstruct door hit. Skips LOUDLY rather than passing."""
        real = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data",
                            "valquo_track.json")
        if not os.path.exists(real):
            print("       (SKIPPED LOUDLY: the bound book is not on this machine at %s)" % real)
            return
        b = IF.book_in_force(meta_path=real, as_of="2026-10-02")
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["formed_on"], REAL_FORMED)
        self.assertEqual(b["scan_date"], REAL_SCAN)
        self.assertEqual(b["next_rebalance"], RUNBOOK_NEXT)
        self.assertEqual(len(b["positions"]), 86, "the bound record carries 86 positions")
        self.assertEqual(b["n_positions"], 85, "85 held after WBS's declared exit")
        self.assertEqual(b["n_exited"], 1)


class TheNextRebalanceIsDerived(unittest.TestCase):

    def test_it_reproduces_the_RUNBOOK_from_the_records_own_scan_date(self):
        """THE CONTROL. `REBALANCE_RUNBOOK_2026-10-22.md` fixes the date by its own arithmetic
        -- "63 trading days from the 2026-07-24 scan is Thursday 2026-10-22" -- and that has to
        come out of this function, or the tab and the runbook disagree about when the book
        changes."""
        self.assertEqual(IF.next_rebalance(REAL_SCAN), RUNBOOK_NEXT)

    def test_it_is_the_SCAN_date_and_not_inception(self):
        """A six-day error, and the kind that looks right. 63 trading days after inception
        (2026-07-30) is 2026-10-28, not the runbook's 2026-10-22."""
        self.assertEqual(IF.next_rebalance(REAL_FORMED), "2026-10-28")
        self.assertNotEqual(IF.next_rebalance(REAL_FORMED), RUNBOOK_NEXT)

    def test_it_counts_TRADING_days_through_market_session(self):
        """Not calendar days, and not weekdays: 2026-09-07 is Labor Day. The calendar is
        `market_session`'s, the same authority the contract's own gap report uses."""
        from valuation.screener import market_session as ms
        got = IF.next_rebalance("2026-09-01", 10)
        d, n = dt.date.fromisoformat("2026-09-01"), 0
        while n < 10:
            d += dt.timedelta(days=1)
            if ms.is_trading_day(d):
                n += 1
        self.assertEqual(got, d.isoformat())
        self.assertFalse(ms.is_trading_day(dt.date(2026, 9, 7)),
                         "fixture assumption: Labor Day is not a trading day")

    def test_an_unreadable_scan_date_gives_None_rather_than_a_guess(self):
        self.assertIsNone(IF.next_rebalance(None))
        self.assertIsNone(IF.next_rebalance("not-a-date"))


class ExitsAreDeclaredAndSpreadProRata(unittest.TestCase):

    def _with_exit(self, as_of="2026-09-01", exit_date="2026-08-20"):
        IF_EXITS = IF.EXITS
        IF.EXITS = ({"ticker": "B", "date": exit_date, "reason": "acquired",
                     "treatment": "sold at last close; weight spread pro-rata across survivors",
                     "ruling": "fixture"},)
        try:
            with tempfile.TemporaryDirectory() as d:
                p = _book_file(d, [{"ticker": "A", "weight": 0.5},
                                   {"ticker": "B", "weight": 0.2},
                                   {"ticker": "C", "weight": 0.3}])
                return IF.book_in_force(meta_path=p, as_of=as_of)
        finally:
            IF.EXITS = IF_EXITS

    def test_the_exited_name_goes_to_zero_and_survivors_absorb_it_PRO_RATA(self):
        b = self._with_exit()
        by = {r["ticker"]: r for r in b["positions"]}
        self.assertEqual(by["B"]["status"], "exited")
        self.assertEqual(by["B"]["weight"], 0.0)
        self.assertEqual(by["B"]["weight_at_formation"], 0.2,
                         "the formation weight must survive, or the book's history is lost")
        # 1/(1 - 0.2) = 1.25 on each survivor, in proportion to its own weight.
        self.assertTrue(_eq(by["A"]["weight"], 0.625), by["A"])
        self.assertTrue(_eq(by["C"]["weight"], 0.375), by["C"])
        self.assertTrue(_eq(b["prorata_scale"], 1.25), b["prorata_scale"])
        self.assertTrue(_eq(sum(r["weight"] for r in b["positions"]), 1.0),
                        "the held weights must sum to 1 after the spread")
        self.assertEqual(b["n_positions"], 2)
        self.assertEqual(b["n_exited"], 1)

    def test_an_exit_BEFORE_the_book_was_formed_is_not_this_books_exit(self):
        b = self._with_exit(exit_date="2026-07-01")
        self.assertEqual(b["n_exited"], 0)
        self.assertEqual(b["n_positions"], 3)

    def test_an_exit_AFTER_the_date_asked_about_has_not_happened_yet(self):
        b = self._with_exit(as_of="2026-08-10", exit_date="2026-08-20")
        self.assertEqual(b["n_exited"], 0,
                         "a future exit reshaped a historical view of the book")
        self.assertEqual(b["n_positions"], 3)

    def test_the_exit_carries_its_PROVENANCE(self):
        b = self._with_exit()
        ex = [r for r in b["positions"] if r["status"] == "exited"][0]["exit"]
        for k in ("date", "reason", "treatment", "ruling"):
            self.assertTrue(ex.get(k), k)

    def test_WBS_is_the_declared_exit_with_DONS_RULING_attached(self):
        got = {e["ticker"]: e for e in IF.EXITS}
        self.assertIn("WBS", got)
        self.assertEqual(got["WBS"]["date"], "2026-08-20")
        self.assertEqual(got["WBS"]["reason"], "acquired")
        self.assertIn("pro-rata", got["WBS"]["treatment"])
        self.assertIn("Don", got["WBS"]["ruling"])
        self.assertIn("PAPER_TRACK_CONTRACT", got["WBS"]["ruling"],
                      "the outstanding amendment is not named, so nobody will codify it")

    def test_an_exit_is_never_INFERRED_from_a_name_being_unpriceable(self):
        """THE LESSON `E-5` PAID FOR. An acquisition is a TERMINAL value; a gap in a vendor's
        file is CENSORING; and from here they look identical -- WBS's frame stopping on
        2026-08-19 is corroboration of the acquisition, not evidence of it. So an exit is a
        declared FACT, and nothing in this module may derive one from a missing price.

        Read from the syntax tree, because the docstrings necessarily discuss unpriceability.
        """
        src = io.open(os.path.join(REPO, "valuation/screener/index_in_force.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "book_in_force")
        body = ast.unparse(fn)
        self.assertIn("EXITS", body, "book_in_force does not read the declared list at all")
        for banned in ("unpriced", "price_now", "_closes", "get_history_df", "compute_returns"):
            self.assertNotIn(banned, body,
                             "book_in_force reaches for price data to decide an exit: %s"
                             % banned)


class ReturnsSinceFormation(unittest.TestCase):

    def _tape(self, series, calls):
        import pandas as pd

        def fetch(ticker, days=400, as_of=None):
            calls.append(ticker.upper())
            s = series.get(ticker.upper())
            if not s:
                return None
            return pd.DataFrame({"Date": list(s), "Close": list(s.values())})
        return fetch

    def test_ONE_vendor_call_per_ticker(self):
        calls = []
        series = {"A": {REAL_FORMED: 100.0, "2026-10-01": 110.0},
                  "B": {REAL_FORMED: 50.0, "2026-10-01": 45.0}}
        with tempfile.TemporaryDirectory() as d:
            p = _book_file(d, [{"ticker": "A", "weight": 0.5},
                               {"ticker": "B", "weight": 0.5}])
            b = IF.book_in_force(meta_path=p, as_of="2026-10-01")
            r = IF.compute_returns(b, fetch=self._tape(series, calls), as_of="2026-10-01")
        self.assertEqual(sorted(calls), ["A", "B"], calls)
        self.assertEqual(max(calls.count(t) for t in set(calls)), 1)
        self.assertEqual(r["prices"]["max_calls_per_ticker"], 1, r["prices"])
        self.assertTrue(_eq(r["returns"]["A"]["return_pct"], 10.0), r["returns"]["A"])
        self.assertTrue(_eq(r["returns"]["B"]["return_pct"], -10.0), r["returns"]["B"])

    def test_an_exited_name_is_priced_at_its_LAST_CLOSE_and_dated_to_that_close(self):
        """"Sold at last close" means the close, and `priced_through` must name the day the
        price came from -- not the exit date, which is a day later for WBS."""
        prior = IF.EXITS
        IF.EXITS = ({"ticker": "B", "date": "2026-08-20", "reason": "acquired",
                     "treatment": "sold at last close", "ruling": "fixture"},)
        try:
            series = {"A": {REAL_FORMED: 100.0, "2026-10-01": 110.0},
                      "B": {REAL_FORMED: 50.0, "2026-08-19": 60.0, "2026-10-01": 999.0}}
            with tempfile.TemporaryDirectory() as d:
                p = _book_file(d, [{"ticker": "A", "weight": 0.5},
                                   {"ticker": "B", "weight": 0.5}])
                b = IF.book_in_force(meta_path=p, as_of="2026-10-01")
                r = IF.compute_returns(b, fetch=self._tape(series, []), as_of="2026-10-01")
        finally:
            IF.EXITS = prior
        got = r["returns"]["B"]
        self.assertEqual(got["price_now"], 60.0,
                         "the exited name was priced AFTER its exit date")
        self.assertEqual(got["priced_through"], "2026-08-19")
        self.assertTrue(_eq(got["return_pct"], 20.0), got)

    def test_a_missing_FORMATION_price_gives_no_return_and_says_why(self):
        """MEASURED ON WBS: its yfinance frame now carries exactly ONE row, 2026-08-19 -- the
        vendor keeps the final close of an acquired name and drops the history. So the return
        since formation is not computable from a free source, and a fabricated one would land
        on the single holding whose treatment is a standing ruling."""
        prior = IF.EXITS
        IF.EXITS = ({"ticker": "B", "date": "2026-08-20", "reason": "acquired",
                     "treatment": "sold at last close", "ruling": "fixture"},)
        try:
            series = {"A": {REAL_FORMED: 100.0, "2026-10-01": 110.0},
                      "B": {"2026-08-19": 60.0}}          # the final close ONLY
            with tempfile.TemporaryDirectory() as d:
                p = _book_file(d, [{"ticker": "A", "weight": 0.5},
                                   {"ticker": "B", "weight": 0.5}])
                b = IF.book_in_force(meta_path=p, as_of="2026-10-01")
                r = IF.compute_returns(b, fetch=self._tape(series, []), as_of="2026-10-01")
        finally:
            IF.EXITS = prior
        got = r["returns"]["B"]
        self.assertIsNone(got["return_pct"])
        self.assertIsNone(got["price_at_formation"])
        self.assertEqual(got["price_now"], 60.0, "the last close it DOES have was dropped")
        self.assertIn("not computable", got["return_unavailable"])
        self.assertEqual(r["unpriced"], [], "it was counted as unpriced rather than reported")

    def test_NO_book_level_total_is_offered(self):
        """A weighted average of these would exclude any name the vendor cannot price -- WBS
        today -- and would then disagree with the RECORDED series, which is the contract's own
        number and the only thing that may be quoted as the Index's return. Two totals under
        one name is the defect this whole change exists to end."""
        with tempfile.TemporaryDirectory() as d:
            p = _book_file(d, [{"ticker": "A", "weight": 1.0}])
            b = IF.book_in_force(meta_path=p, as_of="2026-10-01")
            r = IF.compute_returns(b, fetch=self._tape({"A": {REAL_FORMED: 1.0,
                                                             "2026-10-01": 2.0}}, []),
                                   as_of="2026-10-01")
        for k in r:
            self.assertNotIn(k, ("total_return_pct", "book_return_pct", "return_pct",
                                 "cumulative_pct", "index_return_pct"),
                             "a book-level total appeared under %r" % k)
        self.assertIn("no_book_total_here", r)

    def test_a_returns_cache_for_a_DIFFERENT_book_is_refused(self):
        """Stale against another formation date is not stale, it is WRONG: it would print one
        book's returns against another book's holdings."""
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "r.json")
            with io.open(cache, "w", encoding="utf-8") as fh:
                json.dump({"formed_on": "2026-04-01", "as_of": "2026-10-01",
                           "returns": {"A": {"return_pct": 5.0}},
                           "computed_at": "2026-10-01T00:00:00"}, fh)
            p = _book_file(d, [{"ticker": "A", "weight": 1.0}])
            b = IF.attach_returns(IF.book_in_force(meta_path=p, as_of="2026-10-01"),
                                  path=cache)
        self.assertFalse(b["returns_state"]["available"])
        self.assertIn("formed", b["returns_state"]["reason"])
        self.assertNotIn("return_pct", b["positions"][0],
                         "another book's return was attached to these holdings")

    def test_an_absent_cache_is_an_explicit_absence_and_the_book_still_shows(self):
        with tempfile.TemporaryDirectory() as d:
            p = _book_file(d, [{"ticker": "A", "weight": 1.0}])
            b = IF.attach_returns(IF.book_in_force(meta_path=p, as_of="2026-10-01"),
                                  path=os.path.join(d, "nope.json"))
        self.assertTrue(b["ok"], "the holdings vanished because returns were missing")
        self.assertFalse(b["returns_state"]["available"])
        self.assertTrue(b["returns_state"]["reason"])

    def test_save_REFUSES_a_run_that_priced_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            got = IF.save_returns({"ok": True, "returns": {}},
                                  path=os.path.join(d, "r.json"))
        self.assertFalse(got["ok"])
        self.assertIn("nothing was priced", got["reason"])


class TheSectorMixSaysWhenItCouldNotLabelAnything(unittest.TestCase):
    """ALL-UNKNOWN IS NOT A MIX. The labels come from the LATEST scan while the book was formed
    from an earlier one, so a name the current universe no longer carries has no label. Measured
    on a fixture store (scan date 2099-01-01) all 85 held names came back unknown -- which would
    have drawn one 100% "unknown" wedge and read as a finding about the book."""

    class _Store:
        def __init__(self, rows):
            self._rows = rows

        def latest_scan_date(self):
            return "2026-10-01"

        def load_snapshot(self, d):
            return self._rows

    def _book(self, d):
        return IF.book_in_force(meta_path=_book_file(
            d, [{"ticker": "A", "weight": 0.5}, {"ticker": "B", "weight": 0.5}]),
            as_of="2026-10-01")

    def test_when_nothing_can_be_labelled_it_reports_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            mix = IF.sector_mix(self._book(d), self._Store([]))
        self.assertFalse(mix["available"])
        self.assertEqual(mix["n_unknown_sector"], 2)
        self.assertEqual(mix["n_held"], 2)
        self.assertIn("no sector label", mix["reason"])

    def test_when_the_snapshot_carries_the_names_it_reports_the_mix(self):
        rows = [{"ticker": "A", "sector": "Technology"},
                {"ticker": "B", "sector": "Financial Services"}]
        with tempfile.TemporaryDirectory() as d:
            mix = IF.sector_mix(self._book(d), self._Store(rows))
        self.assertTrue(mix["available"])
        self.assertEqual(mix["n_unknown_sector"], 0)
        self.assertTrue(_eq(mix["mix"]["Technology"], 0.5), mix)
        self.assertTrue(_eq(sum(mix["mix"].values()), 1.0), mix)

    def test_a_partial_label_set_is_still_available_and_counts_the_gap(self):
        """One labelled name is a mix with a hole, not an absence -- and the hole is counted
        rather than dropped, or the weights would sum to less than the book and look like a
        rounding error."""
        rows = [{"ticker": "A", "sector": "Technology"}]
        with tempfile.TemporaryDirectory() as d:
            mix = IF.sector_mix(self._book(d), self._Store(rows))
        self.assertTrue(mix["available"])
        self.assertEqual(mix["n_unknown_sector"], 1)
        self.assertTrue(_eq(sum(mix["mix"].values()), 1.0),
                        "the unlabelled name was dropped instead of counted")


class TheRouteServesTheBookAndLabelsThePreview(unittest.TestCase):

    def _client(self):
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        self._prior = CONFIG.owner_split
        CONFIG.owner_split = False          # the route is owner-only; this reaches it
        app = create_saas_app()
        app.config.update(TESTING=True)
        return app.test_client()

    def tearDown(self):
        from valuation.config import CONFIG
        if hasattr(self, "_prior"):
            CONFIG.owner_split = self._prior

    def test_the_DEFAULT_payload_is_the_book_in_force(self):
        c = self._client()
        fake = {"ok": True, "formed_on": REAL_FORMED, "scan_date": REAL_SCAN,
                "next_rebalance": RUNBOOK_NEXT, "positions": [{"ticker": "A", "weight": 1.0,
                                                               "status": "held"}],
                "n_positions": 1, "n_exited": 0}
        real = IF.book_in_force
        IF.book_in_force = lambda **k: dict(fake)
        try:
            d = c.get("/api/valquo-index").get_json()
        finally:
            IF.book_in_force = real
        self.assertIs(d.get("is_preview"), False)
        self.assertEqual(d.get("formed_on"), REAL_FORMED)
        self.assertEqual(d.get("next_rebalance"), RUNBOOK_NEXT)
        self.assertIn("held unchanged", d.get("source_note", ""))

    def test_an_unreadable_record_NEVER_falls_back_to_the_daily_pick(self):
        """The substitution this change exists to end: serving the rebuild under the Index's
        name because the record could not be read."""
        c = self._client()
        real = IF.book_in_force
        IF.book_in_force = lambda **k: {"ok": False, "reason": "fixture refusal",
                                        "positions": []}
        try:
            d = c.get("/api/valquo-index").get_json()
        finally:
            IF.book_in_force = real
        self.assertTrue(d.get("empty"))
        self.assertIs(d.get("is_preview"), False)
        self.assertIn("fixture refusal", d.get("message", ""))
        self.assertFalse(d.get("positions"),
                         "it served holdings despite the record being unreadable")

    def test_the_PREVIEW_is_labelled_and_names_itself_not_the_index(self):
        c = self._client()
        d = c.get("/api/valquo-index?preview=1").get_json()
        # It may be empty on an isolated store; what must hold is the LABEL whenever it serves.
        if d.get("empty"):
            print("       (no scan snapshot in the isolated store; label checked on the route "
                  "source instead)")
            src = io.open(os.path.join(REPO, "valuation/web/app.py"), encoding="utf-8").read()
            fn = next(n for n in ast.walk(ast.parse(src))
                      if isinstance(n, ast.FunctionDef) and n.name == "api_valquo_index")
            body = ast.unparse(fn)
            self.assertIn("not_the_index", body)
            self.assertIn("is_preview", body)
            return
        self.assertIs(d.get("is_preview"), True)
        self.assertIn("NOT the Valquo Index", d.get("not_the_index", ""))


class NothingAboutConstructionChanges(unittest.TestCase):
    """(c) Display and API only, and this is the checkable form of that claim."""

    def test_the_module_never_imports_the_BUILDER(self):
        src = io.open(os.path.join(REPO, "valuation/screener/index_in_force.py"),
                      encoding="utf-8").read()
        names = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.ImportFrom):
                names.add(n.module or "")
            elif isinstance(n, ast.Import):
                names.update(a.name for a in n.names)
        self.assertFalse([m for m in names if "valquo_index" in m],
                         "the view imports the BUILDER, so it could change construction")

    def test_the_module_writes_NOTHING_to_the_bound_record(self):
        """It writes exactly one file -- its own returns cache -- and never the record."""
        src = io.open(os.path.join(REPO, "valuation/screener/index_in_force.py"),
                      encoding="utf-8").read()
        code = []
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                continue
            if isinstance(n, ast.Name):
                code.append(n.id)
            elif isinstance(n, ast.Attribute):
                code.append(n.attr)
            elif isinstance(n, ast.FunctionDef):
                # Collected too, or the non-vacuity anchor below cannot be satisfied: a
                # def NAME is neither a Name nor an Attribute node, and my first cut looked
                # for one in a blob that could not contain it.
                code.append(n.name)
        blob = " ".join(code)
        self.assertIn("save_returns", blob, "the stripper removed the code as well as prose")
        for banned in ("append_row", "append_rebalance", "seed"):
            self.assertNotIn(banned, blob,
                             "the view reaches a WRITER of the bound record: %s" % banned)

    # THE "UNCHANGED" CLAIM IS NOT ASSERTED HERE, AND REMOVING IT WAS THE RIGHT CALL.
    #
    # My first cut ran `git diff --name-only origin/main -- index_mark.py valquo_index.py` and
    # required it empty. `tests/test_ma60_conventions.py::NoSuiteAssertsOnAWorkingTreeDiff`
    # failed it, correctly, and its reasoning is exactly right: that compares origin/main
    # against WHATEVER IS CHECKED OUT, so it does not measure the lane that wrote it. It
    # becomes a permanent tripwire on whole files, owned by an item that has already landed,
    # and it fires on the next lane to touch one of them -- which it had already done once to
    # an unrelated app-fixer change. Two suites had shipped that construction before mine;
    # this was the third.
    #
    # The durable form is the PROPERTY, not the diff, and it is the two tests above: this
    # module never imports the builder, and never reaches a writer of the bound record. That
    # the two files are byte-identical against main is verified by hand at commit time and
    # stated in the commit message, which is where a claim about a diff belongs.


class TheWordingSaysOneFixedBook(unittest.TestCase):
    """(d) Pinned forward and the old wording banned, because prose in a template does not
    stop -- someone has to remember, and this is that someone."""

    def _tpl(self, name):
        return io.open(os.path.join(REPO, "valuation/web/templates", name),
                       encoding="utf-8").read()

    def test_the_index_tab_says_one_fixed_book_held_for_the_quarter(self):
        # WHITESPACE-NORMALISED, because the copy is line-wrapped in the template and a
        # literal with a newline in it cannot match -- which is a test that fails against
        # correct prose rather than a check of the prose.
        t = " ".join(self._tpl("index.html").split())
        self.assertIn("ONE FIXED BOOK, HELD FOR THE QUARTER", t)
        self.assertIn("held unchanged since", t)
        self.assertIn("not a daily pick", t)
        self.assertIn("the one the forward record tracks", t)

    def test_the_OLD_wording_is_gone_from_every_surface(self):
        banned = "The holdings are rebuilt from\n        each day's scan"
        for name in ("index.html", "methodology.html", "landing.html"):
            t = self._tpl(name)
            self.assertNotIn(banned.replace("\n        ", " "), " ".join(t.split()),
                             "%s still says the holdings are rebuilt daily" % name)
            self.assertNotIn("separate, fixed book", t,
                             "%s still calls the tracked book SEPARATE from the holdings"
                             % name)

    def test_methodology_says_the_book_is_held_between_rebalances(self):
        t = " ".join(self._tpl("methodology.html").split())
        self.assertIn("fixed at each quarterly rebalance and held unchanged between them", t)
        # E3a reworded the clause this used to match ("the same book in both"): the Index's
        # forward record is on the INDEX tab and the hero, while the Track Record tab is the
        # options paper book. Matched on the sentence that replaced it.
        self.assertIn("holdings and its curve are the same book", t)
        self.assertIn("carries its forward record", t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
