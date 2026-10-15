# -*- coding: utf-8 -*-
"""ITEM 59 — Alpaca market data, measured before anything switches.

**NOTHING HERE TOUCHES A NETWORK OR A KEY.** The client takes an injectable session, the seam
takes injectable inputs, and the gate is read from a temporary artifact. That is not a
convenience: the keys exist only on Render, so a lane that needed one could not test this at
all, and a test that reached the real vendor would spend a 200-per-minute allowance shared with
the live service.

THE TEST THAT MATTERS MOST is `TheSwitchIsInertUntilItIsLicensed`. With no recorded measurement
the vendor order must be bit-identical to what it was, and that is asserted by watching the
CALL SEQUENCE rather than by trusting a docstring.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — temp state only. Import BEFORE `valuation`.

from valuation.data import alpaca_data as AD        # noqa: E402
from valuation.data import alpaca_seam as SEAM      # noqa: E402

KEY, SEC = "PKFAKEKEYID0001", "FAKESECRETVALUE0001"


class _Resp:
    def __init__(self, status=200, payload=None, headers=None, text=""):
        self.status_code, self._p = status, (payload if payload is not None else {})
        self.headers, self.text = headers or {}, text

    def json(self):
        if self._p is None:
            raise ValueError("not json")
        return self._p


class _Session:
    """Records every request and replays scripted replies. No network."""

    def __init__(self, replies=None):
        self.calls, self._replies = [], list(replies or [])

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": dict(params or {}),
                           "headers": dict(headers or {})})
        return self._replies.pop(0) if self._replies else _Resp(200, {"bars": {}})


def _bar(day, close):
    return {"t": "%sT00:00:00Z" % day, "o": close, "h": close, "l": close, "c": close,
            "v": 1000}


def _client(replies=None):
    return AD.AlpacaData(KEY, SEC, session=_Session(replies))


# ----------------------------------------------------------------------------------------- #
class TheAdjustmentCannotBeDefaulted(unittest.TestCase):
    """THE ONE THING MOST LIKELY TO GO WRONG, AND THE REASON IT IS A REQUIRED KEYWORD.

    Alpaca's own `adjustment` default is `raw`. The bound Index basis is ADJUSTED — `prices.py`
    records the measurement: of the 6 recorded rows that can discriminate, 6 match adjusted and
    0 match plain. A caller who omitted the parameter would silently change the basis of the one
    series that cannot be rebuilt, which is the split-trap that cost items 36 and 39.
    """

    def test_omitting_it_is_a_TypeError_and_not_a_silent_raw(self):
        with self.assertRaises(TypeError):
            _client().bars(["AAPL"])

    def test_an_unknown_value_is_refused_with_the_reason(self):
        with self.assertRaises(AD.AlpacaDataError) as cm:
            _client().bars(["AAPL"], adjustment="auto_adjust")
        msg = str(cm.exception)
        self.assertIn("raw", msg)
        self.assertIn("cannot be rebuilt", msg)

    def test_the_recorded_basis_constant_is_all(self):
        self.assertEqual(AD.ADJ_FOR_RECORDED_BASIS, "all")
        self.assertIn("all", AD.ADJUSTMENTS)

    def test_it_is_actually_sent_on_the_wire(self):
        c = _client([_Resp(200, {"bars": {"AAPL": [_bar("2026-10-13", 10.0)]}})])
        c.bars(["AAPL"], adjustment=AD.ADJ_ALL)
        self.assertEqual(c._session.calls[0]["params"]["adjustment"], "all")

    def test_snapshots_do_not_pretend_to_be_adjustable(self):
        """Alpaca's own note: trades and quotes are only ever raw; only BARS are adjusted. A
        snapshot carrying an `adjustment` parameter would be inventing a convention."""
        c = _client([_Resp(200, {"snapshots": {"AAPL": {"latestTrade": {"p": 1.0}}}})])
        got = c.snapshots(["AAPL"])
        self.assertNotIn("adjustment", c._session.calls[0]["params"])
        self.assertIn("as-traded", got["basis"])


class TheClientIsReadOnly(unittest.TestCase):
    def test_it_defines_no_write_method(self):
        """Deliberately NOT part of `alpaca_broker`: that module's whole job is refusing to
        point at the live trading host. Keeping data separate means this path cannot acquire an
        order method by proximity."""
        with open(AD.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("place_limit", "place_equity", "cancel", "submit_order", "close_position"):
            self.assertNotIn(banned, names)

    def test_every_request_it_makes_is_a_GET(self):
        c = _client([_Resp(200, {"bars": {}}), _Resp(200, {"snapshots": {}})])
        c.bars(["AAPL"], adjustment=AD.ADJ_RAW)
        c.snapshots(["AAPL"])
        self.assertEqual({x["method"] for x in c._session.calls}, {"GET"})


class CredentialsAndSecrecy(unittest.TestCase):
    def test_half_a_pair_is_not_usable(self):
        """`MA6`: half a key pair cannot authenticate, so reporting it present would promise a
        client that does not exist."""
        self.assertEqual(AD.credentials({AD.KEY_ID_VAR: "x"}), ("", ""))
        self.assertEqual(AD.credentials({AD.SECRET_VAR: "y"}), ("", ""))
        self.assertEqual(AD.credentials({AD.KEY_ID_VAR: "x", AD.SECRET_VAR: "y"}), ("x", "y"))
        self.assertFalse(AD.have_keys({AD.KEY_ID_VAR: "x"}))

    def test_no_keys_refuses_to_construct(self):
        with self.assertRaises(AD.AlpacaDataError):
            AD.AlpacaData(env={})

    def test_the_key_travels_in_headers_and_never_in_the_query(self):
        c = _client([_Resp(200, {"bars": {}})])
        c.bars(["AAPL"], adjustment=AD.ADJ_RAW)
        call = c._session.calls[0]
        self.assertIn("APCA-API-KEY-ID", call["headers"])
        self.assertNotIn(KEY, json.dumps(call["params"]))

    def test_an_echoed_key_is_scrubbed_out_of_an_error(self):
        """Unlikely rather than impossible, and 'unlikely' is not a reason to print one."""
        c = _client([_Resp(403, {"message": "bad key %s" % KEY})])
        got = c.bars(["AAPL"], adjustment=AD.ADJ_RAW)
        self.assertFalse(got["ok"])
        self.assertNotIn(KEY, got["error"])
        self.assertIn("***", got["error"])

    def test_scrub_ignores_a_short_string_so_it_cannot_blank_everything(self):
        self.assertEqual(AD.scrub("hello", "a"), "hello")


class ManySymbolsPerCall(unittest.TestCase):
    """Item 59's instruction: the multi-symbol endpoints, not one call per name."""

    def test_222_names_do_not_cost_222_requests(self):
        c = _client([_Resp(200, {"bars": {}}) for _ in range(5)])
        names = ["T%03d" % i for i in range(222)]
        got = c.bars(names, adjustment=AD.ADJ_ALL)
        self.assertLessEqual(got["requests"], 3)
        self.assertEqual(len(c._session.calls[0]["params"]["symbols"].split(",")),
                         AD.SYMBOLS_PER_CALL)

    def test_pagination_is_followed_and_merged(self):
        c = _client([
            _Resp(200, {"bars": {"AAPL": [_bar("2026-10-01", 1.0)]}, "next_page_token": "p2"}),
            _Resp(200, {"bars": {"AAPL": [_bar("2026-10-02", 2.0)]}}),
        ])
        got = c.bars(["AAPL"], adjustment=AD.ADJ_ALL)
        self.assertEqual(len(got["bars"]["AAPL"]), 2)
        self.assertEqual(got["pages"], 2)
        self.assertEqual(c._session.calls[1]["params"]["page_token"], "p2")

    def test_a_truncated_series_SAYS_it_was_truncated(self):
        """Silently stopping at a page cap is how a short history reads as a complete one."""
        c = _client([_Resp(200, {"bars": {"AAPL": [_bar("2026-10-01", 1.0)]},
                                 "next_page_token": "more"})])
        got = c.bars(["AAPL"], adjustment=AD.ADJ_ALL, max_pages=1)
        self.assertIn("TRUNCATED", got["error"])

    def test_a_symbol_alpaca_does_not_return_is_MISSING_not_empty(self):
        """`V6`'s `C5`. "No bars" and "not covered" are different facts, and item 40's FMP
        measurement died on the second one."""
        c = _client([_Resp(200, {"bars": {"AAPL": [_bar("2026-10-01", 1.0)]}})])
        got = c.bars(["AAPL", "NOPE"], adjustment=AD.ADJ_ALL)
        self.assertEqual(got["missing"], ["NOPE"])
        self.assertNotIn("NOPE", got["bars"])

    def test_the_rate_budget_is_READ_not_counted(self):
        c = _client([_Resp(200, {"bars": {}},
                           headers={"x-ratelimit-remaining": "137",
                                    "x-ratelimit-limit": "200"})])
        c.bars(["AAPL"], adjustment=AD.ADJ_ALL)
        b = c.rate_budget()
        self.assertEqual(b["headers"]["x-ratelimit-remaining"], "137")
        self.assertEqual(b["published_per_min"], 200)
        self.assertIn("drifts", b["note"])


class TheFeedQuestionIsAskedNotInferred(unittest.TestCase):
    """Alpaca's own pages claim "100% market coverage" beside "IEX exchange only", and the
    15-minute delay's feed is not named. So the plan question is not answerable from the
    documentation and this does not guess."""

    def test_the_probe_records_a_refusal_as_a_refusal(self):
        replies = []
        for f in AD.FEEDS:
            if f == "iex":
                replies.append(_Resp(200, {"bars": {"AAPL": [_bar("2026-10-01", 1.0)]}}))
            else:
                replies.append(_Resp(403, {"message": "subscription does not permit %s" % f}))
        got = AD.AlpacaData(KEY, SEC, session=_Session(replies)).feed_probe()
        self.assertEqual(got["readable"], ["iex"])
        self.assertIn("sip", got["refused"])
        self.assertEqual(got["feeds"]["sip"]["status"], 403)

    def test_a_200_with_no_bars_is_NOT_readable(self):
        """A feed that answers politely and returns nothing has not been shown to work -- the
        `stooq-is-dead` shape, where the primary returned a clean response for every symbol."""
        replies = [_Resp(200, {"bars": {}}) for _ in AD.FEEDS]
        got = AD.AlpacaData(KEY, SEC, session=_Session(replies)).feed_probe()
        self.assertEqual(got["readable"], [])

    def test_the_probe_uses_a_CONTROL_name(self):
        c = _client([_Resp(200, {"bars": {}}) for _ in AD.FEEDS])
        got = c.feed_probe()
        self.assertEqual(got["symbol"], "AAPL")


class WhatAlpacaDoesAndDoesNotCarry(unittest.TestCase):
    def test_fundamentals_are_declared_absent(self):
        """Item 59: company fundamentals, descriptions and earnings dates stay on Yahoo with
        item 57's SEC fallback. Declared so the summary's claim is checkable."""
        blob = " ".join(AD.NOT_CARRIED).lower()
        for want in ("financial statements", "descriptions", "earnings dates"):
            self.assertIn(want, blob)

    def test_the_options_feed_is_declared_indicative_with_what_that_costs(self):
        blob = " ".join(AD.CARRIED_FREE).lower()
        self.assertIn("indicative", blob)
        self.assertIn("not for", blob)
        self.assertIn("half-spread", blob)


class TheComparatorDistinguishesAbsentFromZero(unittest.TestCase):
    def test_no_shared_dates_is_UNMEASURED(self):
        got = SEAM.compare_closes({"2026-10-01": 1.0}, {"2026-10-02": 1.0})
        self.assertFalse(got["measured"])
        self.assertIn("nothing to compare", got["reason"])
        self.assertNotIn("agree_rate", got)

    def test_a_real_disagreement_is_measured_and_the_worst_is_named(self):
        got = SEAM.compare_closes({"a": 10.0, "b": 20.0, "c": 30.0},
                                  {"a": 10.01, "b": 20.0, "c": 60.0})
        self.assertTrue(got["measured"])
        self.assertAlmostEqual(got["agree_rate"], 2 / 3.0, places=6)
        self.assertEqual(got["worst"][0]["date"], "c")

    def test_the_tolerance_separates_rounding_from_a_split(self):
        """20 bps absorbs a rounding difference and nothing larger: a basis difference is
        percent, not basis points, so the two questions stay apart."""
        self.assertTrue(SEAM.compare_closes({"a": 100.0}, {"a": 100.1})["agree_rate"] == 1.0)
        self.assertTrue(SEAM.compare_closes({"a": 100.0}, {"a": 50.0})["agree_rate"] == 0.0)


class TheGateHasThreeConditionsAndEachFailsAlone(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "data_export"), exist_ok=True)

    def _write(self, passed=True, schema=SEAM.SCHEMA):
        with open(SEAM.artifact_path(self.root), "w", encoding="utf-8") as fh:
            json.dump({"schema": schema, "at": "2026-10-14T00:00:00Z",
                       "closes": {"passed": passed, "agree_rate": 0.999,
                                  "reason": "fixture"},
                       "coverage": {"sample_rate": 0.99}}, fh)

    def test_no_artifact_is_NOT_a_pass(self):
        got = SEAM.switch_allowed(self.root, {"PRICES_PRIMARY_ALPACA": "1"})
        self.assertFalse(got["allowed"])
        self.assertFalse(got["measured"])
        self.assertIn("no seam measurement is recorded", got["reason"])

    def test_a_FAILING_measurement_is_not_a_pass_however_the_opt_in_is_set(self):
        self._write(passed=False)
        got = SEAM.switch_allowed(self.root, {"PRICES_PRIMARY_ALPACA": "1"})
        self.assertFalse(got["allowed"])
        self.assertTrue(got["measured"])
        self.assertIn("did NOT pass", got["reason"])

    def test_a_PASSING_measurement_without_the_opt_in_is_AVAILABLE_not_taken(self):
        """`ALPACA_SETUP.md`'s own closing line: changing what prices the bound record is Don's
        call, not a lane's, because inside a segment base and mark must come from one vendor."""
        self._write(passed=True)
        got = SEAM.switch_allowed(self.root, {})
        self.assertFalse(got["allowed"])
        self.assertTrue(got["closes_passed"])
        self.assertIn("AVAILABLE and has not been taken", got["reason"])
        self.assertIn("Don's call", got["reason"])

    def test_all_three_together_allow_it(self):
        self._write(passed=True)
        got = SEAM.switch_allowed(self.root, {"PRICES_PRIMARY_ALPACA": "1"})
        self.assertTrue(got["allowed"])

    def test_a_foreign_schema_is_not_trusted(self):
        self._write(passed=True, schema="alpaca_seam/0")
        self.assertFalse(SEAM.switch_allowed(self.root,
                                             {"PRICES_PRIMARY_ALPACA": "1"})["allowed"])

    def test_a_garbage_artifact_reads_as_absent_and_never_raises(self):
        with open(SEAM.artifact_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(SEAM.read_artifact(self.root))

    def test_the_bars_were_declared_before_any_number_existed(self):
        """A bar chosen after seeing the result is not a bar. They are module constants, so a
        change shows in a diff."""
        self.assertEqual(SEAM.PASS_AGREE_RATE, 0.98)
        self.assertEqual(SEAM.PASS_COVERAGE, 0.95)
        self.assertEqual(SEAM.PASS_INDEX_COVERAGE, 1.0)


class TheSwitchIsInertUntilItIsLicensed(unittest.TestCase):
    """**THE TEST THAT MATTERS MOST.** Landing item 59 must not change what prices anything.

    Asserted by watching the CALL SEQUENCE rather than by trusting a docstring: with the gate
    shut, `get_history_df` must try yfinance, then Stooq, then FMP, which is exactly what it
    tried before item 59.
    """

    def _sequence(self):
        from valuation.screener import prices as PR
        seen = []
        orig = {}
        for name in ("_alpaca_history", "_yf_history", "_stooq_history", "_fmp_history"):
            orig[name] = getattr(PR, name)

        def mk(name):
            def f(ticker, days=400, as_of=None, *a, **k):
                seen.append(name)
                return orig[name](ticker, days, as_of=as_of) if name == "_alpaca_history" \
                    else None
            return f

        try:
            for name in orig:
                setattr(PR, name, mk(name))
            PR.get_history_df("AAPL", days=5)
        finally:
            for name, fn in orig.items():
                setattr(PR, name, fn)
        return seen

    def test_the_alpaca_leg_returns_None_immediately_with_no_artifact(self):
        from valuation.screener import prices as PR
        self.assertIsNone(PR._alpaca_history("AAPL", 5))

    def test_the_vendor_order_is_unchanged_when_the_gate_is_shut(self):
        seq = self._sequence()
        self.assertEqual(seq, ["_alpaca_history", "_yf_history", "_stooq_history",
                               "_fmp_history"])

    def test_the_basis_is_declared_and_is_not_unverified(self):
        """Every other gated vendor here is `unverified`. Alpaca's is not, because the
        parameter is passed explicitly rather than left at the vendor's `raw` default."""
        from valuation.screener import prices as PR
        self.assertEqual(PR.VENDOR_ADJUSTMENT[PR.SRC_ALPACA], "all_adjustment")
        self.assertNotEqual(PR.VENDOR_ADJUSTMENT[PR.SRC_ALPACA], "unverified")

    def test_the_stale_opening_line_is_corrected(self):
        """It said "Stooq primary, yfinance fallback" while the function's own docstring 250
        lines below recorded the REVERSAL and the 0.4s-vs-30.1s measurement behind it. A
        reader of the first line got the opposite of the truth."""
        from valuation.screener import prices as PR
        head = (PR.__doc__ or "")[:400]
        self.assertNotIn("Stooq primary", head)
        self.assertIn("yfinance primary", head)


class TheSeamRunsOnFixturesWithNoNetwork(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _stub_client(self, names, splitter_raw_differs=True):
        class C:
            last_rate = {"x-ratelimit-remaining": "190"}

            def feed_probe(self, **k):
                return {"symbol": "AAPL", "feeds": {"iex": {"ok": True, "bars": 1}},
                        "readable": ["iex"], "refused": ["sip"], "note": "fixture"}

            def bars(self, syms, *, adjustment, **k):
                out = {}
                for s in syms:
                    base = 100.0
                    if adjustment == AD.ADJ_RAW and splitter_raw_differs and s == "NVDA":
                        base = 1000.0        # pre-split, as-traded
                    out[s] = [_bar("2026-10-%02d" % d, base + d) for d in (1, 2, 3)]
                return {"ok": True, "bars": out, "missing": [], "pages": 1,
                        "rate": self.last_rate, "requests": 1}

            def snapshots(self, syms, **k):
                return {"ok": True, "snapshots": {}, "missing": list(syms)}
        return C()

    def test_it_produces_a_PASSING_artifact_when_the_vendors_agree(self):
        names = ["AAPL", "MSFT", "NVDA", "O", "NEE"]
        yf = {s: {"2026-10-%02d" % d: 100.0 + d for d in (1, 2, 3)} for s in names}
        got = SEAM.measure(client=self._stub_client(names), names=names, yf_closes=yf,
                           root=self.root)
        self.assertTrue(got["ok"], got.get("reason"))
        self.assertTrue(got["closes"]["passed"], got["closes"]["reason"])
        self.assertEqual(got["coverage"]["sample_rate"], 1.0)
        self.assertEqual(got["closes"]["basis_used"], "all")
        self.assertTrue(os.path.exists(SEAM.artifact_path(self.root)))
        self.assertTrue(SEAM.switch_allowed(self.root,
                                            {"PRICES_PRIMARY_ALPACA": "1"})["allowed"])

    def test_it_FAILS_when_the_adjusted_closes_disagree(self):
        names = ["AAPL", "MSFT"]
        yf = {s: {"2026-10-%02d" % d: 200.0 + d for d in (1, 2, 3)} for s in names}
        got = SEAM.measure(client=self._stub_client(names), names=names, yf_closes=yf,
                           root=self.root)
        self.assertFalse(got["closes"]["passed"])
        self.assertIn("below the declared", got["closes"]["reason"])

    def test_an_UNMEASURED_comparison_is_not_a_pass(self):
        """The direction that matters: no yfinance leg at all must not read as agreement."""
        names = ["AAPL"]
        got = SEAM.measure(client=self._stub_client(names), names=names, yf_closes={},
                           root=self.root)
        self.assertFalse(got["closes"]["passed"])
        self.assertIn("UNMEASURED", got["closes"]["reason"])

    def test_both_bases_are_pulled_so_the_split_question_is_answerable(self):
        names = ["NVDA", "AAPL"]
        yf = {s: {"2026-10-%02d" % d: 100.0 + d for d in (1, 2, 3)} for s in names}
        got = SEAM.measure(client=self._stub_client(names), names=names, yf_closes=yf,
                           root=self.root)
        per = got["closes"]["vs_yfinance"]["per_name"]["NVDA"]
        self.assertIn("all", per)
        self.assertIn("raw", per)
        self.assertEqual(per["all"]["agree_rate"], 1.0)
        self.assertEqual(per["raw"]["agree_rate"], 0.0)

    def test_the_52_week_high_gap_between_bases_is_reported(self):
        names = ["NVDA", "AAPL"]
        got = SEAM.measure(client=self._stub_client(names), names=names,
                           yf_closes={"AAPL": {"2026-10-01": 101.0}}, root=self.root)
        f = got["fifty_two_week"]
        self.assertGreaterEqual(f["n"], 2)
        self.assertGreaterEqual(f["n_over_1pct"], 1)
        self.assertIn("Dip Detector", f["why"])

    def test_the_named_gaps_are_probed_by_name(self):
        """ET is the live case -- unpriced on the current route since 2026-10-05."""
        got = SEAM.measure(client=self._stub_client(["AAPL"]), names=["AAPL"],
                           yf_closes={}, root=self.root)
        self.assertIn("ET", got["named_gaps"])
        self.assertIn("2026-10-05", got["named_gaps"]["ET"]["why_asked"])
        self.assertTrue(got["named_gaps"]["ET"]["covered"])

    def test_coverage_is_reported_BY_CATEGORY(self):
        """Item 40's FMP measurement died on coverage -- ~12%, zero REITs, zero utilities -- so
        the categories are where the answer was last time."""
        from scripts import fmp_seam as FS
        names = ["O", "SPG", "NEE", "JPM"]
        got = SEAM.measure(client=self._stub_client(names), names=names, yf_closes={},
                           root=self.root)
        self.assertIn("reit", got["coverage"]["by_category"])
        self.assertEqual(got["coverage"]["by_category"]["reit"]["rate"], 1.0)
        self.assertEqual(FS.CATEGORY["O"], "reit")

    def test_no_keys_is_a_refusal_rather_than_a_crash(self):
        got = SEAM.measure(env={}, names=["AAPL"], root=self.root, write=False)
        self.assertFalse(got["ok"])
        self.assertIn("no Alpaca key pair", got["reason"])


class TheSampleIsImportedNotRetyped(unittest.TestCase):
    def test_the_seam_imports_the_stated_sample(self):
        """`B7`. A second copy of the 222-name list would drift, and then the three vendors
        would be compared on different populations -- which is the one thing the sample exists
        to prevent."""
        with open(SEAM.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("from scripts import fmp_seam", src)
        tree = ast.parse(src)
        lists = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Assign) and isinstance(n.value, ast.List)
                 and len(n.value.elts) > 12]
        self.assertEqual(lists, [], "a long ticker list is retyped in the seam module")

    def test_the_stated_blocks_are_all_present_upstream(self):
        from scripts import fmp_seam as FS
        self.assertEqual(len(FS.BANKS), 16)
        self.assertEqual(len(FS.REITS), 16)
        self.assertEqual(len(FS.ADRS), 16)
        self.assertEqual(len(FS.UTILITIES), 10)
        self.assertEqual(len(FS.SPLITTERS), 12)


class TheContractNamesWhatPricesTheRecord(unittest.TestCase):
    """Item 59 asks for a dated note naming the source. It also exposed a stale claim IN the
    contract: it said prices come from `prices.py` "Stooq primary, yfinance fallback", which was
    reversed on 2026-09-30 -- so the document binding the one series that cannot be rebuilt
    named the wrong vendor as pricing it."""

    def setUp(self):
        with open(os.path.join(REPO, "PAPER_TRACK_CONTRACT.md"), encoding="utf-8") as fh:
            self.src = fh.read()

    def test_the_current_primary_is_named_with_its_basis(self):
        self.assertIn("auto_adjust=True", self.src)
        self.assertIn("ADJUSTED", self.src)

    def test_the_stale_order_is_corrected_beneath_its_own_quote(self):
        """The quotation is LEFT INTACT -- it is dated and says what was true then, and this
        project's convention is that quoting a stale figure to record it is fine. What must
        exist is a correction a reader cannot pass without seeing."""
        self.assertIn("Stooq primary, yfinance fallback", self.src)   # the dated quote
        self.assertIn("THE QUOTED VENDOR ORDER IS REVERSED", self.src)
        i_quote = self.src.index("Stooq primary, yfinance fallback")
        i_fix = self.src.index("THE QUOTED VENDOR ORDER IS REVERSED")
        self.assertGreater(i_fix, i_quote, "the correction sits ABOVE the claim it corrects")

    def test_it_records_that_alpaca_defaults_to_raw(self):
        """The single most consequential fact for this record, so it is in the record's own
        document rather than only in a module docstring."""
        self.assertIn("defaults to `raw`", self.src)

    def test_it_names_all_three_switch_conditions(self):
        for want in ("/admin/alpaca-seam", "PRICES_PRIMARY_ALPACA", "98%", "95% coverage"):
            self.assertIn(want, self.src, want)

    def test_it_says_a_vendor_change_is_NOT_a_vintage_event(self):
        """Item 59's own wording: the rules are unchanged, only the price vendor -- so the
        five-year clock does not reset. Saying so matters, because every OTHER change to this
        record's scoring does reset it."""
        self.assertIn("A VENDOR CHANGE IS NOT A VINTAGE EVENT", self.src)

    def test_it_says_the_switch_happens_at_a_segment_boundary(self):
        self.assertIn("segment boundary", self.src)
        self.assertIn("2026-10-22", self.src)


class TheDoor(unittest.TestCase):
    def _client(self):
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        CONFIG.admin_token = "test-token-alpaca-seam"
        app = create_saas_app(CONFIG)
        app.config["TESTING"] = True
        return app.test_client(), {"X-Admin-Token": CONFIG.admin_token}

    def test_it_is_owner_only(self):
        c, _ = self._client()
        self.assertEqual(c.get("/admin/alpaca-seam").status_code, 401)
        self.assertEqual(c.post("/admin/alpaca-seam?run=1").status_code, 401)

    def test_a_GET_cannot_take_the_measurement(self):
        """The pull spends requests against a 200-per-minute allowance shared with the rest of
        the service, and a prefetch or a retry is not a decision to spend it."""
        c, h = self._client()
        r = c.get("/admin/alpaca-seam?run=1", headers=h)
        self.assertEqual(r.status_code, 405)
        self.assertIn("POST", json.loads(r.get_data(as_text=True))["detail"])

    def test_a_GET_reports_and_names_the_render_steps_when_the_keys_are_absent(self):
        c, h = self._client()
        keep = {k: os.environ.pop(k, None) for k in (AD.KEY_ID_VAR, AD.SECRET_VAR)}
        try:
            got = json.loads(c.get("/admin/alpaca-seam", headers=h).get_data(as_text=True))
        finally:
            for k, v in keep.items():
                if v is not None:
                    os.environ[k] = v
        self.assertFalse(got["keys_present"])
        self.assertIn("Environment", got["reason"])
        self.assertIn(AD.KEY_ID_VAR, got["reason"])

    def test_it_reports_the_declared_bars_so_they_can_be_checked_before_the_run(self):
        c, h = self._client()
        got = json.loads(c.get("/admin/alpaca-seam", headers=h).get_data(as_text=True))
        self.assertEqual(got["declared_bars"]["agree_rate"], SEAM.PASS_AGREE_RATE)

    def test_no_credential_appears_in_the_payload(self):
        c, h = self._client()
        os.environ[AD.KEY_ID_VAR] = "PK-FAKE-FOR-THE-DOOR-TEST"
        os.environ[AD.SECRET_VAR] = "SECRET-FAKE-FOR-THE-DOOR-TEST"
        try:
            body = c.get("/admin/alpaca-seam", headers=h).get_data(as_text=True)
        finally:
            os.environ.pop(AD.KEY_ID_VAR, None)
            os.environ.pop(AD.SECRET_VAR, None)
        self.assertNotIn("PK-FAKE-FOR-THE-DOOR-TEST", body)
        self.assertNotIn("SECRET-FAKE-FOR-THE-DOOR-TEST", body)


if __name__ == "__main__":
    unittest.main()
