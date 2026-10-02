# -*- coding: utf-8 -*-
"""Task 15 — closing the free route's three wiring gaps.

GAP 1 the institutional anchor's denominator was dated TODAY while its numerator came from the
13F period end, so market drift moved every anchor at once. GAP 2 the insider score had THREE
implementations, two of them in one file, and the producer of `build_live`'s input had never been
pointed at the universe the cache is built for. TASK 10 the P/B-ROE inputs were persisted all
along and the reader looked at the wrong level.

Every one of those is the same shape: code reading an object that is not the one it means.
"""
from __future__ import annotations

import ast
import datetime as dt
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


# =======================================================================================
# GAP 1a — the shares-outstanding LEVEL at the period end
# =======================================================================================
class TheSharesLevelIsDatedAndNeverFromTheFuture(unittest.TestCase):
    """`extract_xbrl` kept a RATIO of two annual counts and discarded the levels.

    MEASURED against real SEC facts: the unfiltered dei cover-page read lands ON the period end
    for BFH and JPM (both from 10-Qs, 0 days stale) where `_annual`'s 10-K/FY restriction gave a
    figure 90 days stale and 10.2% / 3.8% too high. A market cap built on the annual number would
    have carried that error straight into the anchor.
    """

    def _facts(self, rows):
        return {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": rows}}}}}

    def test_it_takes_the_LATEST_level_at_or_before_the_target(self):
        from scripts import live_theme_sources as M
        f = self._facts([
            {"end": "2025-12-31", "val": 100.0, "form": "10-K"},
            {"end": "2026-03-31", "val": 110.0, "form": "10-Q"},
        ])
        got = M.shares_level_asof(f, "2026-03-31")
        self.assertEqual(got["shares_level"], 110.0)
        self.assertEqual(got["shares_level_end"], "2026-03-31")
        self.assertEqual(got["shares_level_days_stale"], 0)
        self.assertEqual(got["shares_level_form"], "10-Q")

    def test_a_level_dated_AFTER_the_target_is_never_used(self):
        """Look-ahead: a later share count is not knowable at the period end.

        And it is not merely wrong in principle -- using it would make the anchor's denominator
        newer than its numerator, which is the exact mismatch this whole change removes.
        """
        from scripts import live_theme_sources as M
        f = self._facts([
            {"end": "2026-03-31", "val": 110.0, "form": "10-Q"},
            {"end": "2026-06-30", "val": 999.0, "form": "10-Q"},
        ])
        got = M.shares_level_asof(f, "2026-03-31")
        self.assertEqual(got["shares_level"], 110.0,
                         "a level from after the period end was used")

    def test_the_STALENESS_travels_with_the_level(self):
        """So a caller can report the distribution instead of assuming it is small."""
        from scripts import live_theme_sources as M
        f = self._facts([{"end": "2025-09-30", "val": 7.0, "form": "10-K"}])
        got = M.shares_level_asof(f, "2026-03-31")
        self.assertEqual(got["shares_level_days_stale"], 182)

    def test_no_level_at_all_is_None_rather_than_zero(self):
        from scripts import live_theme_sources as M
        got = M.shares_level_asof({}, "2026-03-31")
        self.assertIsNone(got["shares_level"])
        self.assertIsNone(got["shares_level_days_stale"])

    def test_extract_xbrl_is_UNCHANGED_without_the_argument(self):
        """The addition must be additive: every existing caller sees the old five keys."""
        from scripts import live_theme_sources as M
        self.assertEqual(sorted(M.extract_xbrl({}).keys()),
                         ["accruals_end", "accruals_q", "issuance_end",
                          "share_issuance", "shares_points"])

    def test_an_INCOMPLETE_cached_payload_is_refetched_not_skipped(self):
        """A cache written before the field existed is incomplete, not complete.

        Without this the re-run had two outcomes and both were wrong: refetch all 1,500 and throw
        away a two-hour crawl, or skip all 1,500 and leave every level absent with the anchor
        exactly as broken as before.
        """
        from scripts import live_theme_sources as M
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "xbrl"), exist_ok=True)
            p = M.leg_path(d, "xbrl", "AAA")
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write('{"share_issuance": 0.1}')
            self.assertTrue(M.xbrl_needs_shares(d, "AAA", "2026-03-31"),
                            "a payload with no level read as complete")
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write('{"shares_level": 5.0, "shares_level_end": "2026-03-31"}')
            self.assertFalse(M.xbrl_needs_shares(d, "AAA", "2026-03-31"))
            # A level from a LATER period must also refetch -- moving to a new 13F quarter must
            # not silently reuse the prior quarter's count.
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write('{"shares_level": 5.0, "shares_level_end": "2026-06-30"}')
            self.assertTrue(M.xbrl_needs_shares(d, "AAA", "2026-03-31"))


# =======================================================================================
# GAP 1b — the close on the period end, and the split that makes it incomparable
# =======================================================================================
class TheCloseIsReadOffTheRealFrameShape(unittest.TestCase):
    """A first cut read `frame.index` for dates and a lowercase `close`.

    Both price paths return `['Date', 'Open', 'High', 'Low', 'Close', 'Volume']` with a
    POSITIONAL index, so it found no comparable date and reported "no close at or before
    2026-03-31" for **1,457 of 1,500 names** -- a total failure that imitated a coverage gap.
    """

    def _frame(self, dates, closes, dcol="Date", ccol="Close"):
        import pandas as pd
        return pd.DataFrame({dcol: dates, ccol: closes})

    def test_a_DATE_COLUMN_frame_is_read(self):
        from scripts import theme_cache_build as B
        f = self._frame(["2026-03-30", "2026-03-31", "2026-04-01"], [10.0, 11.0, 12.0])
        self.assertEqual(B._close_on_or_before(f, "2026-03-31"), (11.0, "2026-03-31"))

    def test_a_DATE_INDEX_frame_is_also_read(self):
        """Both shapes, because a reader that knows only one silently sees nothing."""
        import pandas as pd
        from scripts import theme_cache_build as B
        f = pd.DataFrame({"close": [10.0, 11.0]},
                         index=pd.to_datetime(["2026-03-30", "2026-03-31"]))
        self.assertEqual(B._close_on_or_before(f, "2026-03-31"), (11.0, "2026-03-31"))

    def test_it_NEVER_reaches_past_the_target(self):
        from scripts import theme_cache_build as B
        f = self._frame(["2026-04-01", "2026-04-02"], [10.0, 11.0])
        self.assertEqual(B._close_on_or_before(f, "2026-03-31"), (None, None))

    def test_an_Index_is_not_truthiness_tested(self):
        """`frame.columns or []` RAISES on pandas -- the empty-default idiom is a crash here."""
        from scripts import theme_cache_build as B
        f = self._frame(["2026-03-31"], [11.0])
        try:
            B._close_on_or_before(f, "2026-03-31")
        except ValueError as e:                                          # pragma: no cover
            self.fail("the Index truthiness trap is back: %s" % e)

    def test_a_SPLIT_between_the_period_end_and_today_REFUSES_the_name(self):
        """The close is back-adjusted and the share count is as-filed; they do not multiply.

        A 2-for-1 halves the cap and so DOUBLES the anchor, moving a name across the bar for a
        reason that has nothing to do with whether the CUSIP match is right. MEASURED on the real
        tape: 12 of 1,500 names split in the window, at ratios up to 25x -- so this is not a
        theoretical guard.
        """
        from scripts import theme_cache_build as B
        tab = {"AAA": [("2026-06-15", 2.0)]}
        self.assertEqual(B.split_between("AAA", "2026-03-31", "2026-10-01", actions=tab), 2.0)
        self.assertEqual(B.split_between("AAA", "2026-07-01", "2026-10-01", actions=tab), 1.0,
                         "a split BEFORE the window was counted")
        self.assertEqual(B.split_between("ZZZ", "2026-03-31", "2026-10-01", actions=tab), 1.0)

    def test_the_split_boundary_is_exclusive_at_the_period_end(self):
        """A split ON the period end is already in the as-filed count, so counting it twice
        would be the error the guard exists to prevent."""
        from scripts import theme_cache_build as B
        tab = {"AAA": [("2026-03-31", 2.0)]}
        self.assertEqual(B.split_between("AAA", "2026-03-31", "2026-10-01", actions=tab), 1.0)

    def test_period_market_caps_REFUSES_a_split_name_end_to_end(self):
        """b4: `split_between` was tested in isolation and nothing tested that the CAP refuses.

        A unit test on the helper leaves the integration unpinned, and deleting the refusal in
        `period_market_caps` stayed green. Driven through the real function with both the price
        frame and the split table injected.
        """
        import pandas as pd
        from scripts import theme_cache_build as B

        served = [{"ticker": "SPLIT", "name": "", "market_cap": None, "sector": ""},
                  {"ticker": "CLEAN", "name": "", "market_cap": None, "sector": ""}]
        frames = {t["ticker"]: pd.DataFrame({"Date": ["2026-03-31"], "Close": [10.0]})
                  for t in served}
        import tempfile as _tf
        root = _tf.mkdtemp()
        os.makedirs(os.path.join(root, "xbrl"), exist_ok=True)
        for t in ("SPLIT", "CLEAN"):
            with io.open(os.path.join(root, "xbrl", t + ".json"), "w", encoding="utf-8") as fh:
                fh.write('{"shares_level": 1000.0, "shares_level_end": "2026-03-31",'
                         ' "shares_level_days_stale": 0, "shares_level_form": "10-Q"}')
        prev = B._SPLITS
        B._SPLITS = {"SPLIT": [("2026-06-15", 2.0)]}
        try:
            caps = B.period_market_caps(served, "2026-03-31", root=root,
                                        batch=lambda t, days=None: frames)
        finally:
            B._SPLITS = prev
        self.assertIsNone(caps["SPLIT"]["market_cap"],
                          "a split name was valued, wrong by the split factor")
        self.assertIn("split", caps["SPLIT"]["reason"])
        self.assertEqual(caps["CLEAN"]["market_cap"], 10000.0,
                         "the guard refused a name that did not split")


class TheMarketCapFailsClosed(unittest.TestCase):
    """A name whose cap cannot be computed is left None so the anchor REFUSES it.

    The anchor's whole purpose is declining what it cannot verify, so filling a gap here would
    defeat the thing being repaired.
    """

    def test_no_shares_level_leaves_the_cap_None_and_says_why(self):
        from scripts import theme_cache_build as B
        served = [{"ticker": "NOPE", "name": "", "market_cap": None, "sector": ""}]
        caps = B.period_market_caps(served, "2026-03-31", root=tempfile.mkdtemp(),
                                    batch=lambda t, days=None: {})
        self.assertIsNone(caps["NOPE"]["market_cap"])
        self.assertIn("shares", caps["NOPE"]["reason"])

    def test_attach_OVERWRITES_rather_than_fills(self):
        """The scan store supplies a CURRENT cap and a current cap is the defect.

        A row left holding a live cap would PASS the guard for the wrong reason, which is worse
        than failing it -- so the attach overwrites unconditionally and sets None where the
        period cap is unknown.
        """
        from scripts import theme_cache_build as B
        served = [{"ticker": "A", "market_cap": 1.0e12}, {"ticker": "B", "market_cap": 2.0e12}]
        cen = B.attach_period_caps(served, {"A": {"market_cap": 5.0e9}, "B": {}})
        self.assertEqual(served[0]["market_cap"], 5.0e9)
        self.assertIsNone(served[1]["market_cap"], "a live cap survived the attach")
        self.assertEqual(served[0]["market_cap_basis"], "period_end")
        self.assertEqual((cen["n_set"], cen["n_none"]), (1, 1))

    def test_the_period_end_has_ONE_source(self):
        from scripts import theme_cache_build as B
        self.assertEqual(B._period_end({"curr": "31-MAR-2026"}), "2026-03-31")
        with self.assertRaises(SystemExit):
            B._period_end({"curr": "not a period"})


# =======================================================================================
# GAP 2 — one insider score, owned by the side the control measures
# =======================================================================================
class ThereIsOneInsiderScore(unittest.TestCase):
    """THREE implementations existed and two were in `fidelity2_rebuild` itself.

    `scripts/fidelity2_rebuild.py:292` was the copy the FIDELITY-2 control measured at **+0.8726**
    and `:417` was the copy that wrote the PRODUCTION cache. Textually identical, which is exactly
    how a control comes to certify a formula production has stopped using. The shipped live scorer
    in `valuation/screener/insider.py` is deliberately NOT folded in: different input
    (`pressure`), own callers, own blast radius.
    """

    def test_the_formula_appears_ONCE_in_the_file(self):
        src = io.open(os.path.join(REPO, "scripts/fidelity2_rebuild.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        # COUNT CALLS IN THE TREE, not occurrences in the text: a docstring explaining the rule
        # necessarily names `math.tanh`, and banning the token would fire on the explanation.
        n = sum(1 for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and getattr(getattr(node.func, "value", None), "id", None) == "math"
                and getattr(node.func, "attr", None) == "tanh")
        self.assertEqual(n, 1, "the insider formula is implemented %d times in one file" % n)

    def test_both_call_sites_DELEGATE(self):
        src = io.open(os.path.join(REPO, "scripts/fidelity2_rebuild.py"),
                      encoding="utf-8").read()
        tree = ast.parse(src)
        callers = set()
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            for c in ast.walk(fn):
                if (isinstance(c, ast.Call)
                        and getattr(c.func, "id", None) == "insider_score_from_txns"):
                    callers.add(fn.name)
        # `insider_column` is the control's path: `score()` calls it at fidelity2_rebuild:350
        # and compares the result against FIDELITY_FLOOR / the calibrated bar. Named explicitly
        # rather than guessed -- a first cut asserted "score" and failed against a correct tree.
        self.assertIn("insider_column", callers,
                      "the FIDELITY-2 control no longer delegates")
        self.assertIn("build_live", callers, "the production builder no longer delegates")

    def test_an_empty_window_is_None_and_never_a_neutral_fifty(self):
        """The panel's semantics, and it is load-bearing: a neutral 50 created a 179-name tie
        block, which the control's own comment records."""
        from scripts import fidelity2_rebuild as F2
        self.assertIsNone(F2.insider_score_from_txns([]))
        self.assertIsNone(F2.insider_score_from_txns(None))
        self.assertIsNone(F2.insider_score_from_txns([{"raw": None}, {}]))

    def test_the_score_is_bounded_and_oriented(self):
        from scripts import fidelity2_rebuild as F2
        buy = F2.insider_score_from_txns([{"raw": 5.0e7}])
        sell = F2.insider_score_from_txns([{"raw": -5.0e7}])
        self.assertGreater(buy, 50.0)
        self.assertLess(sell, 50.0)
        for v in (buy, sell):
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 100.0)

    def test_holes_in_the_transaction_list_are_skipped_identically(self):
        from scripts import fidelity2_rebuild as F2
        a = F2.insider_score_from_txns([{"raw": 1.0e6}, {"raw": -2.5e6}])
        b = F2.insider_score_from_txns([{"raw": None}, {"raw": 1.0e6}, {},
                                        {"raw": -2.5e6}])
        self.assertEqual(a, b)

    def test_fetch4_takes_a_SNAPSHOT_so_it_can_crawl_this_universe(self):
        """`form4_live` was empty because the producer read the PINNED snapshot.

        `M.load_served()` with no argument resolves a pinned file, so `fetch4` could only ever
        crawl the universe that file names -- never the 1,500-name broker ranking the theme cache
        is built for. `build_live` then found no payload for any served name and the insider
        column came out empty, which read as "no insider data" rather than "this producer was
        never pointed at this universe". The same bound-default shape as `fetch_all`'s snapshot.
        """
        import inspect
        from scripts import fidelity2_rebuild as F2
        self.assertIn("snapshot", inspect.signature(F2.fetch4).parameters)
        src = io.open(os.path.join(REPO, "scripts/fidelity2_rebuild.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "fetch4")
        body = ast.unparse(fn)
        self.assertIn("load_served(snapshot or M.SNAPSHOT)", body,
                      "fetch4 reads the pinned snapshot again")


# =======================================================================================
# TASK 10 — the P/B-ROE inputs, and the ke that makes the two surfaces agree
# =======================================================================================
class ThePBRoeInputsWereAlreadyThere(unittest.TestCase):
    """`_rows_from` persists `book_to_price` and `roe` into `extra` -- naming THIS reader as the
    reason -- and `_financial_value` read the TOP level.

    MEASURED on the served 2026-09-30 scan: all 29 financial rows carry both under `extra`, and
    the previous session concluded from the top-level read that the scan had to start storing
    them. It already did. The wrong-object family, costing a whole feature rather than a label.
    """

    def test_it_reads_from_EXTRA(self):
        from valuation.screener.fairvalue import _from_row
        self.assertEqual(_from_row({"extra": {"roe": 0.12}}, "roe"), 0.12)

    def test_it_still_reads_the_TOP_level(self):
        """Both shapes are real: `_enrich_with_dcf` writes at the top level and `_rows_from`
        writes into `extra`."""
        from valuation.screener.fairvalue import _from_row
        self.assertEqual(_from_row({"roe": 0.09}, "roe"), 0.09)

    def test_the_top_level_WINS_when_both_are_present(self):
        from valuation.screener.fairvalue import _from_row
        self.assertEqual(_from_row({"roe": 0.09, "extra": {"roe": 0.12}}, "roe"), 0.09)

    def test_a_missing_key_is_None_in_either_shape(self):
        from valuation.screener.fairvalue import _from_row
        self.assertIsNone(_from_row({}, "roe"))
        self.assertIsNone(_from_row({"extra": {}}, "roe"))
        self.assertIsNone(_from_row({"extra": None}, "roe"))
        self.assertIsNone(_from_row(None, "roe"))


class TheHotListUsesThePipelinesOwnKe(unittest.TestCase):
    """A beta-of-one `ke` costs **+27.06% on BFH** against the single-stock page, so a row
    without the real one is WITHHELD rather than published at an approximation.

    A hot list that shows a bank 27% above the detail page, one click apart, is worse than one
    that declines to show it.
    """

    ROW = {"ticker": "BFH", "sector": "Financial Services",
           "extra": {"book_to_price": 0.5, "roe": 0.11,
                     "pb_roe_ke": 0.102, "pb_roe_g": 0.03}}

    def test_with_a_ke_it_values(self):
        from valuation.screener.fairvalue import _financial_value
        fv, ke = _financial_value(dict(self.ROW), 100.0)
        self.assertIsNotNone(fv)
        self.assertAlmostEqual(ke, 0.102, places=9)

    def test_WITHOUT_a_ke_it_withholds_and_says_which_refusal(self):
        """Two refusals, because collapsing them hides which one is fixable.

        `no_ke` means the fundamentals are present and only the pipeline's cost of equity is
        missing -- a name that WOULD value if the DCF window reached it.
        """
        from valuation.screener.fairvalue import _financial_value
        row = {"ticker": "BFH", "sector": "Financial Services",
               "extra": {"book_to_price": 0.5, "roe": 0.11}}
        fv, why = _financial_value(row, 100.0)
        self.assertIsNone(fv)
        self.assertEqual(why, "no_ke")

    def test_it_does_NOT_fall_back_to_a_beta_of_one(self):
        """The approximation is gone, not merely deprecated -- an AST check, because a comment
        explaining the old formula necessarily quotes it."""
        src = io.open(os.path.join(REPO, "valuation/screener/fairvalue.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "_financial_value")
        for node in ast.walk(fn):
            if isinstance(node, ast.Attribute) and node.attr in (
                    "risk_free_rate", "equity_risk_premium"):
                self.fail("the beta-of-one ke is back in _financial_value")

    def test_g_is_NOT_hard_coded(self):
        """The 1.6-2.2% residual against the pipeline was `min(rf, 0.025)` where the pipeline's
        `terminal_growth` is 0.03 -- measured on XRPN's own payload."""
        src = io.open(os.path.join(REPO, "valuation/screener/fairvalue.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "_financial_value")
        body = ast.unparse(fn)
        self.assertIn("pb_roe_g", body, "g no longer comes from the pipeline")
        self.assertNotIn("min(rf, 0.025)", body)

    def test_the_scan_persists_ke_and_g_into_EXTRA(self):
        """`extra` is the one free-form field in a FIXED store column list, so a top-level key
        is dropped on the way to the record -- which is exactly how the lens label came to be
        computed every scan and never served."""
        src = io.open(os.path.join(REPO, "valuation/screener/screen.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "_enrich_with_dcf")
        body = ast.unparse(fn)
        self.assertIn("pb_roe_ke", body)
        self.assertIn("pb_roe_g", body)
        # THE ASSIGNMENT, NOT THE setdefault. A first cut asserted `setdefault('extra'` was
        # present, and deleting the line that actually WRITES into it left that intact -- the
        # test watched the container being created and never the value going in.
        stores = [n for n in ast.walk(fn)
                  if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Subscript)
                          and getattr(t.value, "id", None) == "_ex" for t in n.targets)]
        self.assertTrue(stores,
                        "nothing writes into `extra`, so ke and g are dropped by the store")

    def test_estimate_fair_values_LABELS_the_ke_refusal_distinctly(self):
        """d3: `_financial_value` returning "no_ke" was tested; the LABEL it produces was not.

        Collapsing the two refusals leaves a reader unable to tell a name that would value if
        the DCF window reached it from one whose fundamentals are absent -- and the unit test on
        the return value could not see the difference.
        """
        from valuation.screener.fairvalue import estimate_fair_values
        rows = [
            # inputs present, ke absent -> fixable
            {"ticker": "KEMISS", "sector": "Financial Services", "price": 100.0,
             "extra": {"book_to_price": 0.5, "roe": 0.11}},
            # no fundamentals at all -> not fixable from the DCF window
            {"ticker": "NOINP", "sector": "Financial Services", "price": 100.0, "extra": {}},
        ]
        estimate_fair_values(rows, peer_rows=rows)
        by = {r["ticker"]: r.get("fair_value_method") for r in rows}
        self.assertEqual(by["KEMISS"], "withheld_financial_ke", by)
        self.assertEqual(by["NOINP"], "withheld_financial_inputs", by)


class TheReconstructDoorRunsWhereTheRecordIs(unittest.TestCase):
    """`/api/index-track` served `n_reconstructed: 0` not because the computation failed but
    because it ran somewhere the record is not.

    The reconstruction needs the book in force, the recorded series to subtract, and a price
    vendor, all in one place. The service has all three; a developer machine has the book and a
    STALE copy of the record -- measured, the local history diverges from the service on 3 of its
    8 rows and carries a row (2026-09-17) the record never had.
    """

    def _app(self):
        from valuation.saas.app_saas import create_saas_app
        app = create_saas_app()
        app.config.update(TESTING=True)
        return app

    def test_the_route_EXISTS_on_both_verbs(self):
        app = self._app()
        rules = {str(r.rule): sorted(r.methods) for r in app.url_map.iter_rules()}
        self.assertIn("/admin/track-reconstruct", rules)
        for v in ("GET", "POST"):
            self.assertIn(v, rules["/admin/track-reconstruct"])

    def test_it_is_UNAUTHORIZED_without_a_token(self):
        c = self._app().test_client()
        self.assertEqual(c.get("/admin/track-reconstruct").status_code, 401)
        self.assertEqual(c.post("/admin/track-reconstruct?write=1").status_code, 401)

    def test_write_on_a_GET_is_REFUSED_before_anything_else(self):
        """A side-effecting GET is reachable by a retry, a prefetch or a pasted link, and none
        of those is a decision to store anything. 405 ahead of the auth check, so the refusal
        cannot be mistaken for a credentials problem."""
        c = self._app().test_client()
        r = c.get("/admin/track-reconstruct?write=1")
        self.assertEqual(r.status_code, 405)
        self.assertIn("POST-only", r.get_data(as_text=True))

    def test_the_token_is_read_from_the_HEADER_only(self):
        """A `?token=` query parameter puts a secret in every proxy log and referrer."""
        src = io.open(os.path.join(REPO, "valuation/saas/app_saas.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "admin_track_reconstruct")
        body = ast.unparse(fn)
        self.assertNotIn("args.get('token')", body.replace('"', "'"),
                         "the door accepts a token in the query string")
        self.assertIn("_admin_ok()", body, "it does not delegate to the shared auth gate")

    def test_it_NEVER_names_a_bound_file(self):
        """CODE only -- comments and docstrings stripped, because the docstring necessarily
        explains that the bound series is not written."""
        import tokenize
        path = os.path.join(REPO, "valuation/saas/app_saas.py")
        src = io.open(path, encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "admin_track_reconstruct")
        code = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                continue
            if isinstance(node, ast.Name):
                code.append(node.id)
            elif isinstance(node, ast.Attribute):
                code.append(node.attr)
        blob = " ".join(code)
        self.assertIn("save", blob, "the stripper removed the code as well as the prose")
        for banned in ("valquo_track_history", "valquo_track", "append_row"):
            self.assertNotIn(banned, blob,
                             "the reconstruct door names a bound writer in CODE: %s" % banned)

    def test_an_EMPTY_record_refuses_rather_than_reconstructing_everything(self):
        """With no recorded series there is nothing to subtract, so every session would look
        missing and the door would 'reconstruct' the entire history -- which is a back-fill of
        the record wearing another name."""
        src = io.open(os.path.join(REPO, "valuation/saas/app_saas.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "admin_track_reconstruct")
        body = ast.unparse(fn)
        self.assertIn("nothing to subtract", body)
        self.assertIn("422", body)

    def test_a_run_that_PRICED_NOTHING_does_not_overwrite_a_populated_store(self):
        """Otherwise one throttled run replaces 19 good points with an empty file -- the
        all-null write in a new costume."""
        src = io.open(os.path.join(REPO, "valuation/saas/app_saas.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "admin_track_reconstruct")
        body = ast.unparse(fn)
        self.assertIn("nothing was computed", body)

    def test_the_response_carries_the_VALIDATION_and_the_exclusions(self):
        """So a reader can judge the points instead of trusting them, and cannot mistake the
        store for the record."""
        src = io.open(os.path.join(REPO, "valuation/saas/app_saas.py"),
                      encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "admin_track_reconstruct")
        body = ast.unparse(fn)
        self.assertIn("validate_against_record", body)
        self.assertIn("excluded_from", body)

    # ===================================================================================
    # 16-PRE -- THE AUTHORISED PATH. Every test above this line is a route-map check, a
    # 401/405 check, or an assertion about the SOURCE TEXT, and all nine of them passed
    # against a handler body that could not execute: `summary = _it.summarize("valquo",
    # store=_store())` called a helper that lives in `web/app.py` and does not exist in
    # `saas/app_saas.py`, so the first caller to get past the gate got
    # `NameError: name '_store' is not defined`, which the handler's own `except Exception`
    # turned into a 500. Don hit it on 2026-10-01 with his real token.
    #
    # An `ast.unparse` assertion cannot see this -- `_store()` parses, unparses and reads
    # exactly like a correct call. Only RUNNING the body does, which is why the first test
    # below authorises rather than probing a refusal.
    # ===================================================================================
    def _authorised(self, fake_summary, patches):
        """Run the door with a token that passes, and nothing that touches a network.

        `cfg` defaults to the live `CONFIG` singleton and `_admin_ok` reads `cfg.admin_token`
        at REQUEST time, so setting it on CONFIG opens the gate even though `create_saas_app`
        is idempotent and the app may already have been built by an earlier test.

        `index_track.summarize` is patched and `Store()` is NOT -- constructing that argument
        is the line under test, so stubbing it away would restore the blindness this exists
        to remove.
        """
        from valuation.config import CONFIG
        from valuation.screener import index_track as _it

        prior = CONFIG.admin_token
        saved = {}
        try:
            CONFIG.admin_token = "test-admin-token-16pre"
            for mod, name, repl in list(patches) + [(_it, "summarize",
                                                     lambda *a, **k: fake_summary)]:
                saved[(mod, name)] = getattr(mod, name)
                setattr(mod, name, repl)
            c = self._app().test_client()
            return c.get("/admin/track-reconstruct",
                         headers={"X-Admin-Token": "test-admin-token-16pre"})
        finally:
            for (mod, name), orig in saved.items():
                setattr(mod, name, orig)
            CONFIG.admin_token = prior

    def test_an_AUTHORISED_GET_returns_200_and_not_a_500(self):
        """THE TEST THAT WAS MISSING. With a valid token and a recorded series present, the
        door must compute and answer -- the path no prior test reached."""
        from valuation.screener import track_reconstruct as _tr
        series = [{"date": "2026-09-01", "valquo": 1.0, "spy": 0.5},
                  {"date": "2026-09-03", "valquo": 1.2, "spy": 0.6}]
        r = self._authorised(
            {"series": series},
            [(_tr, "missing_dates", lambda *a, **k: ["2026-09-02"]),
             (_tr, "reconstruct", lambda *a, **k: {"n_computed": 0, "refused": [],
                                                   "points": []}),
             (_tr, "validate_against_record", lambda *a, **k: {"checked": 2, "max_abs": 0.0}),
             (_tr, "payload", lambda *a, **k: {"excluded_from": ["gate", "meter"]})])
        text = r.get_data(as_text=True)
        self.assertNotIn("_store", text,
                         "the authorised path raised NameError and was served as a 500: %s"
                         % text[:300])
        self.assertEqual(r.status_code, 200, text[:300])
        body = r.get_json()
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(body.get("record_rows"), 2, body)
        self.assertEqual(body.get("record_span"), ["2026-09-01", "2026-09-03"], body)
        self.assertEqual(body.get("missing"), ["2026-09-02"], body)
        self.assertFalse(body.get("written"), "a GET stored something")
        self.assertIn("validation", body)
        self.assertEqual(body.get("excluded_from"), ["gate", "meter"], body)

    def test_the_handler_names_NO_undefined_helper(self):
        """The companion, and the one that would have caught this with no request at all:
        every bare function the body CALLS must resolve to something -- a name `app_saas`
        binds somewhere, or a Python builtin.

        A positive control is required or the check is vacuous: reintroducing `_store` must
        make it fail, which is how `_store()` is told apart from `Store()`.

        SWEPT BEFORE SCOPING IT: the same walk over all 49 functions in `app_saas.py` returns
        NONE, so `_store()` was the only instance and this is a door-level guard rather than
        the first report of a family. It stays scoped to this handler because a file-wide
        version would fire on any future legitimate dynamic call in another lane's door.
        """
        import builtins
        path = os.path.join(REPO, "valuation/saas/app_saas.py")
        src = io.open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "admin_track_reconstruct")

        # Names the module binds at ANY nesting depth -- `create_saas_app` is a closure, so
        # `_admin_ok` and friends are nested defs rather than module-level ones and a
        # module-level-only sweep would flag every legitimate call in the file.
        defined = set(dir(builtins))
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(n.name)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                defined.add(n.id)
            elif isinstance(n, ast.alias):
                defined.add((n.asname or n.name).split(".")[0])
            elif isinstance(n, ast.arg):
                defined.add(n.arg)

        called = {c.func.id for c in ast.walk(fn)
                  if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        self.assertTrue(called, "the walk found no bare calls, so it checks nothing")
        missing = sorted(called - defined)
        self.assertEqual(missing, [],
                         "the reconstruct door calls names nothing defines: %s" % missing)


class TheSplitGuardSaysWhenItCheckedNothing(unittest.TestCase):
    """On a GitHub runner the ACTIONS tape does not exist, so the guard fails OPEN.

    `_split_table` reads `data/bulk/actions.csv` -- Sharadar-licensed, gitignored and UNTRACKED
    (`git ls-files` returns nothing) -- so on a fresh runner the table is empty and
    `split_between` returns 1.0 for every name. The build would look identical while checking
    nothing, and measured locally 12 of 1,500 names split in the window at ratios up to 25x, so
    what gets skipped is real.

    NOT a refusal: gating the whole free route on a licensed file would defeat its purpose.
    COUNTED instead, so "no splits found" and "no tape to look in" can never read the same --
    the distinction this project keeps paying for when a guard goes quiet.
    """

    def test_an_absent_tape_is_reported_as_absent(self):
        from scripts import theme_cache_build as B
        served = [{"ticker": "A"}, {"ticker": "B"}]
        absent = B.attach_period_caps(
            served, {"A": {"market_cap": 1.0, "split_checked": False},
                     "B": {"market_cap": 2.0, "split_checked": False}})
        self.assertEqual(absent["n_split_checked"], 0)
        self.assertIn("ABSENT", absent["split_tape"])
        self.assertIn("NOTHING", absent["split_tape"])

    def test_a_present_tape_is_reported_as_present(self):
        from scripts import theme_cache_build as B
        served = [{"ticker": "A"}, {"ticker": "B"}]
        present = B.attach_period_caps(
            served, {"A": {"market_cap": 1.0, "split_checked": True},
                     "B": {"market_cap": 2.0, "split_checked": True}})
        self.assertEqual(present["n_split_checked"], 2)
        self.assertEqual(present["split_tape"], "present")

    def test_the_build_PRINTS_the_reach(self):
        """A census nobody sees is a census nobody acts on."""
        src = io.open(os.path.join(REPO, "scripts/theme_cache_build.py"),
                      encoding="utf-8").read()
        self.assertIn("split guard", src)
        self.assertIn("n_split_checked", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
