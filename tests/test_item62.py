# -*- coding: utf-8 -*-
"""ITEM 62 — the Alpaca seam "passed" on three bars; this is the test that fails on that pass.

Don ran the measurement on 2026-10-15 at 22:27Z. It reported the daily-close leg PASSED at
`agree_rate 1.000` "across 3 names" — ET, GBTC and TSM, **one bar each, all dated 2026-10-15**,
on six requests. The agreement bar was 0.98 and three bars at 100% cleared it.

**THE BRIEF ASKS FOR A TEST THAT FAILS ON THAT PASS**, and `TheThreeBarPassIsImpossibleNow`
reconstructs it exactly. Everything else here exists because a rate without a quantity beside it
is not evidence, so the floors are on evidence too.

Nothing here touches a network or a key: the Alpaca client takes an injectable session, the
analysis reads a stored pull written by hand, and `vs_recorded` takes an injected `contract_row`.
"""
from __future__ import annotations

import ast
import datetime as _dt
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.data import alpaca_data as AD      # noqa: E402
from valuation.data import alpaca_seam as S       # noqa: E402

BULK = ["T%03d" % i for i in range(220)]


# ----------------------------------------------------------------------------------------- #
# a stored pull, written by hand
# ----------------------------------------------------------------------------------------- #
def seed(root, names, n_bars, *, agree=True, with_div=True, window=None):
    raw = {"schema": S.SCHEMA, "alpaca": {}, "yf": {},
           "window": window or S.window(_dt.date(2026, 10, 15)), "requests": 1}
    base = _dt.date(2026, 10, 15)
    allnames = list(names) + [t for t in S.DIVIDEND_CONTROL if t not in names]
    for t in allnames:
        days = [str(base - _dt.timedelta(days=d)) for d in range(n_bars)]
        a_all = {d: 100.0 + j for j, d in enumerate(days)}
        mult = 1.02 if with_div else 1.0
        a_raw = {d: v * mult for d, v in a_all.items()}
        raw["alpaca"][t] = {AD.ADJ_ALL: a_all, AD.ADJ_RAW: a_raw}
        raw["yf"][t] = {"adj": (dict(a_all) if agree
                                else {d: v * 1.5 for d, v in a_all.items()}),
                        "asof": dict(a_raw), "error": ""}
    os.makedirs(os.path.join(root, "data_export"), exist_ok=True)
    S._write_json(S.raw_path(root), raw)
    return sorted(set(allnames))


class _Root(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def analyse(self, names, n_bars, **kw):
        series = kw.pop("series", [])
        all_names = seed(self.root, names, n_bars, **kw)
        return S.analyse(root=self.root, names=all_names, series=series, write=False)


class TheThreeBarPassIsImpossibleNow(_Root):
    """**THE TEST THE BRIEF ASKS FOR.** It reconstructs the run that actually happened."""

    def test_item_59s_own_run_does_NOT_pass(self):
        """Three names, one bar each, 100% agreement -- which is what was reported as a pass."""
        got = self.analyse(["ET", "GBTC", "TSM"], 1)
        c = got["closes"]
        self.assertEqual(c["agree_rate"], 1.0, "the fixture should still agree perfectly")
        self.assertFalse(c["passed"], "THE THREE-BAR PASS SURVIVED")
        self.assertIn("below the declared floor", c["reason"])

    def test_the_reason_names_BOTH_floors_it_misses(self):
        """A reader must be able to tell which floor stopped it, and here it is both."""
        r = self.analyse(["ET", "GBTC", "TSM"], 1)["closes"]["reason"]
        self.assertIn("names could be compared", r)
        self.assertIn("comparable bars", r)

    def test_a_100_percent_rate_is_not_sufficient_on_its_own(self):
        """The whole lesson in one assertion: agreement is necessary and nowhere near enough."""
        c = self.analyse(["ET", "GBTC", "TSM"], 1)["closes"]
        self.assertGreaterEqual(c["agree_rate"], S.PASS_AGREE_RATE)
        self.assertFalse(c["passed"])


class NeitherFloorCanBeSatisfiedByTheOther(_Root):
    """The two floors are not one floor twice. A bar count alone admits three names with deep
    history; a name count alone admits the whole sample at one bar each."""

    def test_three_names_with_deep_history_still_fails_on_names(self):
        c = self.analyse(["ET", "GBTC", "TSM"], 14000)["closes"]
        self.assertGreater(c["n_bars"], S.MIN_BARS_FOR_PASS)
        self.assertLess(c["n_names"], S.MIN_NAMES_FOR_PASS)
        self.assertFalse(c["passed"])

    def test_the_whole_sample_at_one_bar_each_still_fails_on_bars(self):
        c = self.analyse(BULK, 1)["closes"]
        self.assertGreaterEqual(c["n_names"], S.MIN_NAMES_FOR_PASS)
        self.assertLess(c["n_bars"], S.MIN_BARS_FOR_PASS)
        self.assertFalse(c["passed"])

    def test_a_short_window_across_the_whole_sample_still_fails(self):
        """150 bars x 230 names is 34,500 -- more than enough names, not enough history."""
        c = self.analyse(BULK, 150)["closes"]
        self.assertFalse(c["passed"])
        self.assertIn("comparable bars", c["reason"])

    def test_the_floors_are_declared_with_their_reasons(self):
        self.assertEqual(S.MIN_NAMES_FOR_PASS, 200)
        self.assertEqual(S.MIN_BARS_FOR_PASS, 40000)
        self.assertEqual(S.MIN_BARS_PER_NAME, 200)
        self.assertEqual(S.WINDOW_TRADING_DAYS, 250)
        got = self.analyse(BULK, 250)
        self.assertIn("THREE BARS", got["floors"]["why"])


class ARealSizedPullPassesAndDisagreementStillFails(_Root):
    def test_220_names_over_250_days_passes(self):
        c = self.analyse(BULK, 250)["closes"]
        self.assertTrue(c["passed"], c["reason"])
        self.assertGreater(c["n_bars"], S.MIN_BARS_FOR_PASS)
        self.assertIn("comparable bars across", c["reason"])

    def test_the_window_is_named_in_the_passing_reason(self):
        """A pass that does not say over what period is not a quotable figure."""
        r = self.analyse(BULK, 250)["closes"]["reason"]
        self.assertIn("2026-10-15", r)

    def test_a_vendor_disagreement_fails_it(self):
        c = self.analyse(BULK, 250, agree=False)["closes"]
        self.assertFalse(c["passed"])
        self.assertIn("below the declared", c["reason"])


class AgreementIsBarWeighted(_Root):
    """A MEAN OF PER-NAME RATES is how three single-bar names produced 1.000 beside names that
    would have dominated any honest weighting."""

    def test_one_bad_deep_name_moves_the_rate(self):
        all_names = seed(self.root, BULK, 250)
        raw = S.read_raw(self.root)
        # One name wrong on every bar. Bar-weighted this is ~1/230 of the evidence; a mean of
        # per-name rates would give the same answer here, so the sharper check is below.
        raw["yf"]["T000"]["adj"] = {d: v * 1.5
                                    for d, v in raw["alpaca"]["T000"][AD.ADJ_ALL].items()}
        S._write_json(S.raw_path(self.root), raw)
        c = S.analyse(root=self.root, names=all_names, series=[], write=False)["closes"]
        self.assertLess(c["agree_rate"], 1.0)
        self.assertGreater(c["agree_rate"], 0.99)

    def test_a_single_bar_name_cannot_outweigh_a_deep_one(self):
        """THE SHAPE THAT PRODUCED THE DEFECT. One perfect 1-bar name beside one wrong 250-bar
        name: bar-weighted that is ~0.4% agreement, and a mean of per-name rates would call it
        50%."""
        raw = {"schema": S.SCHEMA, "alpaca": {}, "yf": {},
               "window": S.window(_dt.date(2026, 10, 15)), "requests": 1}
        base = _dt.date(2026, 10, 15)
        deep = {str(base - _dt.timedelta(days=d)): 100.0 + d for d in range(250)}
        raw["alpaca"]["DEEP"] = {AD.ADJ_ALL: deep, AD.ADJ_RAW: deep}
        raw["yf"]["DEEP"] = {"adj": {d: v * 1.5 for d, v in deep.items()}, "asof": {},
                             "error": ""}
        one = {"2026-10-15": 10.0}
        raw["alpaca"]["ONE"] = {AD.ADJ_ALL: one, AD.ADJ_RAW: one}
        raw["yf"]["ONE"] = {"adj": dict(one), "asof": {}, "error": ""}
        os.makedirs(os.path.join(self.root, "data_export"), exist_ok=True)
        S._write_json(S.raw_path(self.root), raw)
        c = S.analyse(root=self.root, names=["DEEP", "ONE"], series=[],
                      write=False)["closes"]
        self.assertLess(c["agree_rate"], 0.01, "the rate is a mean of per-name rates")
        self.assertIn("BAR-WEIGHTED", c["aggregation"])


class CoverageCountsBarsAndNotNames(_Root):
    def test_a_one_bar_name_is_NOT_covered(self):
        """Which is exactly what made the first run's 96.4% untrustworthy."""
        got = self.analyse(BULK, 1)
        self.assertEqual(got["coverage"]["sample_covered"], 0)
        self.assertEqual(got["coverage"]["sample_rate"], 0.0)

    def test_THIN_is_reported_separately_from_MISSING(self):
        """`C5` one level down: a name with some bars but not enough is a different fact from a
        name the vendor does not carry, and the first run collapsed them."""
        got = self.analyse(BULK, 5)
        self.assertGreater(len(got["coverage"]["thin"]), 0)
        self.assertEqual(got["coverage"]["missing"], [])
        self.assertIn("reported separately", got["coverage"]["thin_note"])

    def test_coverage_is_reported_BY_CATEGORY(self):
        """Item 40's FMP measurement died at ~12% with ZERO REITs and ZERO utilities, which a
        name-count floor would not have caught."""
        got = self.analyse(["O", "SPG", "NEE", "JPM"], 250)
        by = got["coverage"]["by_category"]
        self.assertIn("reit", by)
        self.assertEqual(by["reit"]["rate"], 1.0)

    def test_the_three_NYSE_names_the_first_run_missed_are_probed_BY_NAME(self):
        """So the next run answers it rather than leaving the figure untrustworthy."""
        got = self.analyse(["AVB", "BK", "EQR"], 250)
        for t in ("AVB", "BK", "EQR"):
            self.assertIn(t, got["named_gaps"])
            self.assertIn("item 62", got["named_gaps"][t]["why_asked"])
            self.assertEqual(got["named_gaps"][t]["bars"], 250)


class TheTwoBasesMustBeProvablyDifferent(_Root):
    """ITEM 62 PART 5. The first run reported every 52-week high identical on both bases and
    could not tell "the splits are old" from "both parameters returned one series"."""

    def test_a_dividend_payer_separates_them(self):
        got = self.analyse(BULK, 250, with_div=True)
        self.assertTrue(got["bases"]["distinct"])
        self.assertGreater(len(got["bases"]["distinct_on"]), 0)

    def test_ONE_series_under_two_parameters_is_caught(self):
        """The failure the control exists for, and the fixture can actually produce it."""
        got = self.analyse(BULK, 250, with_div=False)
        self.assertFalse(got["bases"]["distinct"])
        self.assertIn("NOT DISTINGUISHABLE", got["bases"]["reason"])

    def test_the_control_names_are_dividend_payers(self):
        for t in ("KO", "JNJ", "PG", "XOM"):
            self.assertIn(t, S.DIVIDEND_CONTROL)


class VsRecordedIsMeasuredAndRequiresEveryRow(unittest.TestCase):
    """ITEM 62 PART 2. The leg that gates the Index switch, and it was UNMEASURED while the
    switch reported "available"."""

    RECORDED = [{"date": "2026-07-31", "valquo_pct": 0.776, "spy_pct": 1.2,
                 "excess_pp": -0.424},
                {"date": "2026-08-06", "valquo_pct": 3.6228, "spy_pct": 3.6228,
                 "excess_pp": 0.0},
                {"date": "2026-08-13", "valquo_pct": 4.25, "spy_pct": 4.88,
                 "excess_pp": -0.63}]
    ALP = {"AAPL": {AD.ADJ_ALL: {"2026-07-31": 100.0, "2026-08-06": 101.0,
                                 "2026-08-13": 102.0}}}

    def _row(self, offset_bps=0.0, refuse=()):
        def contract_row(as_of=None, *, fetch=None, refuse_before_close=True, **kw):
            d = str(as_of)[:10]
            if d in refuse:
                return {"ok": False, "reason": "no price on %s" % d, "row": None}
            probe = fetch("AAPL", days=400, as_of=d) if fetch else None
            if probe is None or getattr(probe, "empty", True):
                return {"ok": False, "reason": "the injected fetch priced nothing",
                        "row": None}
            src = next(r for r in self.RECORDED if r["date"] == d)
            off = offset_bps / 100.0
            return {"ok": True, "row": {"date": d, "valquo_pct": src["valquo_pct"] + off,
                                        "spy_pct": src["spy_pct"],
                                        "excess_pp": src["excess_pp"] + off,
                                        "n_priced": 85}}
        return contract_row

    def test_it_passes_when_every_row_reproduces(self):
        got = S.measure_vs_recorded(raw_by_symbol=self.ALP, series=self.RECORDED,
                                    contract_row=self._row())
        self.assertTrue(got["passed"], got["reason"])
        self.assertEqual(got["n_compared"], 3)
        self.assertEqual(got["worst_bps"], 0.0)

    def test_the_gap_is_reported_in_BASIS_POINTS(self):
        got = S.measure_vs_recorded(raw_by_symbol=self.ALP, series=self.RECORDED,
                                    contract_row=self._row(12.0))
        self.assertFalse(got["passed"])
        self.assertAlmostEqual(got["worst_bps"], 12.0, places=6)
        self.assertIn("bps", got["reason"])

    def test_a_gap_inside_the_declared_tolerance_passes(self):
        got = S.measure_vs_recorded(raw_by_symbol=self.ALP, series=self.RECORDED,
                                    contract_row=self._row(3.0))
        self.assertTrue(got["passed"])

    def test_ONE_unreproducible_row_fails_the_whole_leg(self):
        """No percentage floor here on purpose: the bound record is the one series that cannot
        be rebuilt, and a vendor that reproduces two rows of three says nothing about the
        third."""
        got = S.measure_vs_recorded(raw_by_symbol=self.ALP, series=self.RECORDED,
                                    contract_row=self._row(refuse=("2026-08-06",)))
        self.assertFalse(got["passed"])
        self.assertEqual(got["n_compared"], 2)
        self.assertEqual(got["n_rows"], 3)
        self.assertIn("requires EVERY row", got["reason"])
        self.assertTrue(S.RECORDED_REQUIRE_ALL_ROWS)

    def test_no_alpaca_prices_is_UNMEASURED_and_not_a_pass(self):
        got = S.measure_vs_recorded(raw_by_symbol={}, series=self.RECORDED,
                                    contract_row=self._row())
        self.assertFalse(got["passed"])
        self.assertFalse(got["measured"])

    def test_an_empty_record_is_UNMEASURED_and_says_where_it_can_be_measured(self):
        got = S.measure_vs_recorded(raw_by_symbol=self.ALP, series=[],
                                    contract_row=self._row())
        self.assertFalse(got["passed"])
        self.assertIn("only be measured on the service", got["reason"])

    def test_it_uses_CONTRACT_ROWS_OWN_ARITHMETIC_rather_than_a_second_copy(self):
        """`B7`. Re-deriving the Index's renormalisation, its coverage floor and its
        segment-base rule here would be a second definition of the one series that cannot be
        rebuilt. `contract_row` already takes an injectable `fetch`, so only the price source
        changes."""
        with open(S.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn("alpaca_fetch", names)
        for reimplemented in ("renormalise", "build_index", "_weights", "segment_base"):
            self.assertNotIn(reimplemented, names)

    def test_the_fetch_adapter_honours_as_of_and_never_looks_ahead(self):
        f = S.alpaca_fetch(self.ALP, AD.ADJ_ALL)
        df = f("AAPL", days=400, as_of="2026-08-06")
        self.assertEqual(len(df), 2)
        self.assertEqual(df["Date"].iloc[-1], "2026-08-06")

    def test_an_unknown_symbol_returns_None_rather_than_an_empty_frame(self):
        """`contract_row` counts a name UNPRICED on None; an empty frame could read as a priced
        name with no history."""
        self.assertIsNone(S.alpaca_fetch(self.ALP, AD.ADJ_ALL)("NOPE"))


class TheSwitchNeedsBothLegs(_Root):
    """ITEM 62 PART 3's last sentence: `switch.allowed` stays false unless BOTH legs pass."""

    def _write_artifact(self, closes_ok, rec_ok):
        doc = {"schema": S.SCHEMA, "at": "2026-10-15T22:27:00Z",
               "closes": {"passed": closes_ok, "agree_rate": 0.999, "n_bars": 57500,
                          "n_names": 220, "reason": "fixture"},
               "vs_recorded": {"passed": rec_ok, "reason": "fixture"},
               "coverage": {"sample_rate": 0.99}}
        os.makedirs(os.path.join(self.root, "data_export"), exist_ok=True)
        S._write_json(S.artifact_path(self.root), doc)

    def test_closes_alone_is_not_enough(self):
        """THE EXACT STATE THE FIRST RUN REPORTED: closes "passed", recorded UNMEASURED, and
        the switch said AVAILABLE."""
        self._write_artifact(True, False)
        got = S.switch_allowed(self.root, {"PRICES_PRIMARY_ALPACA": "1"})
        self.assertFalse(got["allowed"])
        self.assertIn("against the recorded Index series", got["reason"])

    def test_recorded_alone_is_not_enough(self):
        self._write_artifact(False, True)
        self.assertFalse(S.switch_allowed(self.root,
                                          {"PRICES_PRIMARY_ALPACA": "1"})["allowed"])

    def test_both_legs_plus_the_opt_in(self):
        self._write_artifact(True, True)
        self.assertFalse(S.switch_allowed(self.root, {})["allowed"])
        self.assertTrue(S.switch_allowed(self.root,
                                         {"PRICES_PRIMARY_ALPACA": "1"})["allowed"])

    def test_the_available_wording_still_says_it_is_DONS_call(self):
        self._write_artifact(True, True)
        r = S.switch_allowed(self.root, {})["reason"]
        self.assertIn("AVAILABLE", r)
        self.assertIn("Don's call", r)

    def test_ITEM_59s_ARTIFACT_LICENSES_NOTHING(self):
        """It was written as `alpaca_seam/1`. A schema bump is what stops a three-bar pass that
        is already on disk from licensing the switch after this code lands."""
        os.makedirs(os.path.join(self.root, "data_export"), exist_ok=True)
        S._write_json(S.artifact_path(self.root),
                      {"schema": "alpaca_seam/1", "closes": {"passed": True},
                       "vs_recorded": {"passed": True}})
        got = S.switch_allowed(self.root, {"PRICES_PRIMARY_ALPACA": "1"})
        self.assertFalse(got["allowed"])
        self.assertIn("three bars", got["reason"])
        self.assertIsNone(S.read_artifact(self.root))


class ThePullIsStoredResumableAndRefusesWhileIncomplete(_Root):
    """250 trading days across 222 names does not finish inside one HTTP request, and a
    measurement that half-finishes and reports a rate over whatever it got is the defect."""

    class Sess:
        def __init__(self):
            self.calls = []

        def request(self, method, url, headers=None, params=None, data=None, timeout=None):
            self.calls.append(dict(params or {}))

            class R:
                status_code, headers, text = 200, {}, ""

                @staticmethod
                def json():
                    syms = (params or {}).get("symbols", "").split(",")
                    return {"bars": {s: [{"t": "2026-10-%02dT00:00:00Z" % (1 + d),
                                          "c": 100.0 + d, "o": 1, "h": 1, "l": 1, "v": 1}
                                         for d in range(5)] for s in syms}}
            return R()

    def _client(self):
        self.sess = self.Sess()
        return AD.AlpacaData("k" * 12, "s" * 12, session=self.sess)

    def _yf(self, t):
        return {"adj": {"2026-10-%02d" % (1 + d): 100.0 + d for d in range(5)},
                "asof": {}, "error": ""}

    def test_the_window_IS_SENT(self):
        """The root cause. The first run sent no `start` and no `end`, so Alpaca chose the
        window and returned one bar per name."""
        S.pull(client=self._client(), names=["A", "B"], root=self.root, budget_names=2,
               yf_fetch=self._yf, end=_dt.date(2026, 10, 15))
        p = self.sess.calls[0]
        self.assertIn("start", p)
        self.assertIn("end", p)
        self.assertEqual(p["end"], "2026-10-15")
        self.assertEqual(p["adjustment"], "all")

    def test_BOTH_bases_are_pulled(self):
        S.pull(client=self._client(), names=["A"], root=self.root, budget_names=1,
               yf_fetch=self._yf)
        self.assertEqual({c["adjustment"] for c in self.sess.calls
                          if "adjustment" in c}, {"all", "raw"})

    def test_a_budget_stops_part_way_and_SAYS_what_is_owed(self):
        got = S.pull(client=self._client(), names=["A", "B", "C", "D"], root=self.root,
                     budget_names=2, yf_fetch=self._yf)
        self.assertFalse(got["complete"])
        self.assertEqual(len(got["owed"]), 2)
        self.assertIn("still owed", got["reason"])

    def test_a_second_call_CONTINUES_rather_than_restarting(self):
        S.pull(client=self._client(), names=["A", "B", "C", "D"], root=self.root,
               budget_names=2, yf_fetch=self._yf)
        again = S.pull(client=self._client(), names=["A", "B", "C", "D"], root=self.root,
                       budget_names=2, yf_fetch=self._yf)
        self.assertTrue(again["complete"])
        self.assertEqual(sorted(again["newly_pulled"]), ["C", "D"])

    def test_the_analysis_REFUSES_while_the_pull_is_incomplete(self):
        """The thing that makes the resumability honest rather than cosmetic."""
        S.pull(client=self._client(), names=["A", "B", "C", "D"], root=self.root,
               budget_names=2, yf_fetch=self._yf)
        got = S.analyse(root=self.root, names=["A", "B", "C", "D"], series=[], write=False)
        self.assertFalse(got["closes"]["passed"])
        self.assertIn("INCOMPLETE", got["closes"]["reason"])
        self.assertFalse(got["pull"]["complete"])

    def test_a_moved_window_discards_the_store_rather_than_mixing_two_windows(self):
        """Mixing bars from two windows makes the bar count meaningless, and the bar count is
        the quantity the floor is on."""
        S.pull(client=self._client(), names=["A"], root=self.root, budget_names=1,
               yf_fetch=self._yf, end=_dt.date(2026, 10, 15))
        got = S.pull(client=self._client(), names=["A"], root=self.root, budget_names=1,
                     yf_fetch=self._yf, end=_dt.date(2026, 11, 20))
        self.assertIn("the window moved", got["reason"])

    def test_no_keys_is_a_refusal_rather_than_a_crash(self):
        got = S.pull(env={}, names=["A"], root=self.root)
        self.assertFalse(got["ok"])
        self.assertIn("no Alpaca key pair", got["reason"])


class PaginationChunkingAndSymbolFormAreNotTheCause(unittest.TestCase):
    """THE AVB / BK / EQR DIAGNOSIS, PINNED. [item 62 part 4]

    The brief names three candidates for those three NYSE-listed names reading as missing:
    pagination not followed, a batch cut off, or a symbol-format issue. Two of those are in our
    code and are ruled out here; the third is a fact about Alpaca that only a real pull settles,
    and the measurement now probes those names by name with their bar counts so the next run
    answers it.
    """

    class Paged:
        def __init__(self, days=250, per_page=10000):
            self.days, self.per_page, self.calls = days, per_page, []

        def request(self, method, url, headers=None, params=None, data=None, timeout=None):
            self.calls.append(dict(params or {}))
            syms = (params or {}).get("symbols", "").split(",")
            tok = (params or {}).get("page_token")
            flat = [(s, d) for s in syms for d in range(self.days)]
            start = int(tok) if tok else 0
            page = flat[start:start + self.per_page]
            bars = {}
            for s, d in page:
                bars.setdefault(s, []).append({"t": "2026-01-%02dT00:00:00Z" % (1 + d % 28),
                                               "c": 100.0 + d, "o": 1, "h": 1, "l": 1,
                                               "v": 1})
            out = {"bars": bars}
            if start + self.per_page < len(flat):
                out["next_page_token"] = str(start + self.per_page)

            class R:
                status_code, headers, text = 200, {}, ""
                json = staticmethod(lambda: out)
            return R()

    NAMES = sorted(["AVB", "BK", "EQR", "AAPL", "BRK.B"] + ["T%03d" % i for i in range(220)])

    def test_a_226_name_250_day_pull_loses_no_symbol(self):
        sess = self.Paged(days=250)
        got = AD.AlpacaData("k" * 12, "s" * 12, session=sess).bars(
            self.NAMES, adjustment=AD.ADJ_ALL, start="2025-09-10", end="2026-10-15")
        self.assertEqual(got["missing"], [], "chunking or pagination loses symbols")
        self.assertEqual(len(got["bars"]), len(self.NAMES))
        short = [s for s, rows in got["bars"].items() if len(rows) < 250]
        self.assertEqual(short, [], "pagination stopped early for %r" % short[:5])

    def test_a_dotted_class_share_survives_the_round_trip(self):
        c = AD.AlpacaData("k" * 12, "s" * 12, session=self.Paged(days=3))
        got = c.bars(["BRK.B", "AVB", "BK", "EQR"], adjustment=AD.ADJ_ALL, start="a", end="b")
        self.assertIn("BRK.B", got["bars"])
        self.assertIn("BRK.B", c._session.calls[0]["symbols"])

    def test_a_page_cap_is_REPORTED_and_the_pull_refuses_to_store_it(self):
        c = AD.AlpacaData("k" * 12, "s" * 12, session=self.Paged(days=250, per_page=500))
        got = c.bars(self.NAMES, adjustment=AD.ADJ_ALL, start="a", end="b", max_pages=2)
        self.assertIn("TRUNCATED", got["error"])
        with open(S.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('out["truncated"] = True', src)
        self.assertIn("TRUNCATED and is not stored", src)


class TheDoorPullsThenAnalyses(unittest.TestCase):
    def setUp(self):
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        CONFIG.admin_token = "test-token-item62"
        app = create_saas_app(CONFIG)
        app.config["TESTING"] = True
        self.c, self.h = app.test_client(), {"X-Admin-Token": CONFIG.admin_token}

    def _src(self):
        import inspect

        from valuation.saas import app_saas
        src = inspect.getsource(app_saas)
        i = src.index("def admin_alpaca_seam(")
        return src[i:src.index("def admin_live_slots(")]

    def _code(self):
        """The door's CODE, with comments and string literals stripped.

        **MY FIRST VERSION OF THE TEST BELOW BANNED THE SUBSTRING `[:0]` AND FAILED AGAINST
        THE FIXED TREE**, because the comment explaining what the dead slice WAS quotes it.
        The substring-ban family, in my own test, in the same change that documents it. A
        tokenizer sees code and not prose about code.
        """
        import io as _io
        import tokenize
        out = []
        try:
            for tok in tokenize.generate_tokens(_io.StringIO(self._src()).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                out.append(tok.string)
        except (tokenize.TokenError, IndentationError):
            # A fragment of a method is not a complete program; whatever tokenized before the
            # error is still code, and the assertions below only need the statements.
            pass
        return " ".join(out)

    def test_the_stripper_is_not_vacuous(self):
        """A POSITIVE CONTROL: a stripper returning "" would make every assertion below pass
        by seeing nothing."""
        code = self._code()
        self.assertIn("SEAM", code)
        self.assertIn("pull", code)
        self.assertNotIn("dead", code, "a comment survived the stripper")

    def test_it_is_owner_only_and_a_GET_cannot_spend_a_request(self):
        self.assertEqual(self.c.get("/admin/alpaca-seam").status_code, 401)
        self.assertEqual(self.c.get("/admin/alpaca-seam?run=1",
                                    headers=self.h).status_code, 405)

    def test_the_dead_slice_that_limited_the_yfinance_leg_is_GONE(self):
        """`probe = (missing)[:0] or list(NAMED_GAPS)` -- a dead slice that always fell through
        to five names."""
        code = self._code()
        self.assertNotIn("[:0]", code)
        self.assertNotIn("probe", code, "the five-name probe list is still built")

    def test_measure_is_not_called_twice(self):
        code = self._code()
        self.assertLessEqual(code.count("SEAM . analyse"), 1)
        self.assertEqual(code.count("SEAM . measure"), 0)

    def test_it_pulls_before_it_analyses(self):
        code = self._code()
        self.assertLess(code.index("SEAM . pull"), code.index("SEAM . analyse"))

    def test_it_reports_the_declared_floors_so_they_can_be_checked_first(self):
        got = json.loads(self.c.get("/admin/alpaca-seam",
                                    headers=self.h).get_data(as_text=True))
        b = got["declared_bars"]
        self.assertEqual(b["min_names"], S.MIN_NAMES_FOR_PASS)
        self.assertEqual(b["min_comparable_bars"], S.MIN_BARS_FOR_PASS)
        self.assertEqual(b["window_trading_days"], S.WINDOW_TRADING_DAYS)
        self.assertTrue(b["recorded_requires_every_row"])

    def test_it_hands_over_the_re_run_command(self):
        """**REPOINTED BY ITEM 64, WHICH FIRED THIS CORRECTLY.** It asserted the GET payload
        carries a `rerun_note` containing "again" -- and that note used to be a STATIC sentence
        printed in every state, which is exactly why Don ran the door ten times against a
        request that could never succeed. It is computed from the pull now, so a GET (which
        pulls nothing) has no advice to give, and the advice that does exist sometimes says
        the opposite. The curl command is still handed over and is still checked here; the
        advice is checked where it is produced, in `tests/test_item64.py`."""
        got = json.loads(self.c.get("/admin/alpaca-seam",
                                    headers=self.h).get_data(as_text=True))
        self.assertIn("POST", got["curl"])
        self.assertIn("/admin/alpaca-seam?run=1", got["curl"])
        self.assertIn("ADMIN_TOKEN", got["curl"])

    def test_the_door_no_longer_prints_UNCONDITIONAL_re_run_advice(self):
        """The property the test above was really protecting, in the direction that matters:
        advice that is right in one state and wrong in the other must come from the state."""
        import inspect
        from valuation.saas import app_saas
        src = inspect.getsource(app_saas)
        door = src[src.index("def admin_alpaca_seam("):]
        door = door[:door.index("def admin_live_slots(")]
        code = chr(10).join(ln.split("#", 1)[0] for ln in door.splitlines())
        self.assertNotIn("Run it again until", code)
        self.assertIn('prog.get("rerun_note")', code)

    def test_no_credential_reaches_the_payload(self):
        os.environ[AD.KEY_ID_VAR] = "PK-FAKE-ITEM62"
        os.environ[AD.SECRET_VAR] = "SECRET-FAKE-ITEM62"
        try:
            body = self.c.get("/admin/alpaca-seam",
                              headers=self.h).get_data(as_text=True)
        finally:
            os.environ.pop(AD.KEY_ID_VAR, None)
            os.environ.pop(AD.SECRET_VAR, None)
        self.assertNotIn("PK-FAKE-ITEM62", body)
        self.assertNotIn("SECRET-FAKE-ITEM62", body)


class TheProductPathIsUntouched(unittest.TestCase):
    def test_the_price_leg_is_still_inert(self):
        """Item 62 changes what it takes to PASS; it switches nothing."""
        from valuation.screener import prices as PR
        self.assertIsNone(PR._alpaca_history("AAPL", 5))

    def test_no_product_module_imports_the_seam(self):
        """It is measurement code. `yf_both_bases` asks yfinance directly with
        `auto_adjust=False`, which `prices` deliberately never does -- so it must not become a
        second vendor path on a product surface."""
        import valuation
        root = os.path.dirname(os.path.abspath(valuation.__file__))
        offenders = []
        for sub in ("web", "screener", "engine", "saas"):
            base = os.path.join(root, sub)
            for dirpath, _d, files in os.walk(base):
                if "__pycache__" in dirpath:
                    continue
                for fn in files:
                    if not fn.endswith(".py"):
                        continue
                    p = os.path.join(dirpath, fn)
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        tree = ast.parse(fh.read())
                    for node in ast.walk(tree):
                        mods = []
                        if isinstance(node, ast.Import):
                            mods = [a.name for a in node.names]
                        elif isinstance(node, ast.ImportFrom):
                            mods = [node.module or ""] + [a.name for a in node.names]
                        if any("alpaca_seam" in (m or "") for m in mods):
                            offenders.append(os.path.relpath(p, root).replace("\\", "/"))
        # The seam DOOR and the gated price leg are the two legitimate importers, each named.
        allowed = {"saas/app_saas.py", "screener/prices.py"}
        self.assertEqual(sorted(set(offenders) - allowed), [])


class TheThreeMissingNamesAreExplainedInTheArtifact(_Root):
    """PART 4. A coverage figure nobody can interpret is not a measurement, and the next person
    to read one will be reading the JSON rather than a handoff."""

    def test_all_three_are_asked_by_name(self):
        for t in ("AVB", "BK", "EQR"):
            self.assertIn(t, S.NAMED_GAPS, t)
            self.assertIn("item 62", S.NAMED_GAPS[t])

    def test_the_note_names_the_cause_and_rules_out_the_others(self):
        note = self.analyse(BULK, 250)["named_gaps_note"]
        self.assertIn("NO `start` and NO `end`", note)
        self.assertIn("ONE", note)
        for ruled_out in ("pagination", "chunked", "BRK.B"):
            self.assertIn(ruled_out, note, ruled_out)

    def test_NOT_COVERED_and_NOT_ASKED_are_distinguished(self):
        """The distinction that makes the figure readable, and `C5`'s rule: a name nobody asked
        about must not read as a name the vendor could not price."""
        self.assertIn("NOT ASKED", self.analyse(BULK, 250)["named_gaps_note"])

    def test_every_gap_carries_its_bar_count_and_yahoo_error(self):
        got = self.analyse(BULK, 250)["named_gaps"]
        for t, row in got.items():
            for k in ("why_asked", "bars", "covered", "yf_bars", "yf_error"):
                self.assertIn(k, row, "%s is missing %s" % (t, k))

    def test_coverage_separates_THIN_from_MISSING(self):
        """A name with some bars but under the floor is a different fact from one with none --
        and conflating them is how one bar per name read as coverage."""
        cov = self.analyse(BULK, 250)["coverage"]
        for k in ("thin", "thin_note", "missing", "min_bars_per_name", "by_category"):
            self.assertIn(k, cov, k)
        self.assertIn("item 59", cov["thin_note"])


class DonsInstructionsSayWhatBothAnSWERS_MEAN(unittest.TestCase):
    """PART 5. The document is the deliverable, so it is pinned like one."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "ALPACA_SETUP.md"), encoding="utf-8") as fh:
            cls.src = fh.read()

    def test_it_carries_the_one_command(self):
        self.assertIn('curl -sS -X POST -H "X-Admin-Token: $ADMIN_TOKEN"', self.src)
        self.assertIn("/admin/alpaca-seam?run=1", self.src)

    def test_the_token_is_never_typed_into_a_url_or_a_history_line(self):
        """`DECISIONS.md`: the admin token is entered masked. A command that puts it in the URL
        would put it in a shell history file and in the service's own access log."""
        self.assertIn("read -rs ADMIN_TOKEN", self.src)
        self.assertIn("unset ADMIN_TOKEN", self.src)
        self.assertNotIn("alpaca-seam?run=1&token=", self.src)

    def test_it_says_the_command_is_run_more_than_once(self):
        """The property the whole resumable pull exists for: an incomplete reply is NORMAL."""
        self.assertIn("pull.complete", self.src)
        self.assertIn("RUN IT MORE THAN ONCE", self.src)

    def test_it_records_that_the_first_run_passed_on_three_bars(self):
        self.assertIn("three bars", self.src.lower())
        self.assertIn("2026-10-15", self.src)

    def test_it_names_all_four_conditions_for_a_pass(self):
        for want in ("98%", "40,000", "PRICES_PRIMARY_ALPACA=1", "basis points"):
            self.assertIn(want, self.src, want)

    def test_it_says_what_a_pass_means_for_the_rebalance(self):
        self.assertIn("2026-10-22", self.src)
        self.assertIn("segment", self.src)

    def test_it_says_a_FAIL_does_not_hold_up_the_rebalance(self):
        """The sentence most likely to be needed and least likely to be written: a failed
        measurement changes nothing and postpones nothing."""
        low = self.src.lower()
        self.assertIn("nothing to do, and nothing to postpone", low)
        self.assertIn("goes ahead on the current vendor", low)

    def test_it_distinguishes_UNMEASURED_from_FAILED(self):
        self.assertIn("**UNMEASURED**", self.src)
        self.assertIn("**FAILED**", self.src)

    def test_it_says_the_switch_is_still_Dons_separate_step(self):
        self.assertIn("your call and still a", self.src)


if __name__ == "__main__":
    unittest.main()
