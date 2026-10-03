# -*- coding: utf-8 -*-
"""The per-run price memo: one vendor call per ticker, and the SAME closes as before.

WHY IT EXISTS. `/admin/track-reconstruct` was unreachable behind a `NameError` (it called
`_store()`, which lives in `web/app.py`). With that fixed the door executes -- and then never
answers: `reconstruct` and `validate_against_record` each call `index_mark.contract_row` once
per DATE, and each of those prices the ~86 Index names plus the benchmark. Measured on
2026-10-02, one `contract_row` takes 102.4s and a 42-date run derives to ~67 min, against the
600s timeout in `scripts/reconstruct_track.py`. The door returned nothing in 600s, confirmed.

Of that 102.4s, 45s -- 44% -- is ONE name (WBS) whose yfinance frame is stale, falling through
to a Stooq that is dead and costs 3 attempts x a 15s connect timeout. Per date, that 45s is
paid again: the same name failing the same way on every date of the run.

THE SCOPE IS THE WHOLE POINT. `index_mark` is NOT edited and the writer's route is NOT
touched. The memo is handed in through `contract_row`'s existing `fetch=` hook, and the daily
writer still passes `fetch=None`, which resolves to `prices.get_history_df` per date exactly
as before -- so nothing here can reach the recorded track. The validation is NOT capped and
no days limit is added: the memo makes the FULL validation affordable rather than smaller,
which matters because its own docstring makes it the precondition that licenses drawing any
reconstructed point.
"""
from __future__ import annotations

import datetime as dt
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

from valuation.screener import index_mark as IM           # noqa: E402
from valuation.screener import track_reconstruct as TR    # noqa: E402

INCEPTION = "2026-07-30"

#: A 42-session run, the size the live door actually faces, MEASURED rather than assumed:
#: against the 24-row live record there are 18 missing sessions in the span, so the door makes
#: 18 + 24 = 42 `contract_row` calls. (An earlier cut used 39, which was the brief's estimate.)
#:
#: REAL TRADING DAYS, from `market_session` -- the same authority `missing_dates` uses. A
#: weekday-only run includes 2026-09-07 (Labor Day), which `contract_row` refuses as a
#: non-trading day, so the first cut of this fixture carried a refusal that had nothing to do
#: with prices and made `n_compared` read 38 of 39.
def _sessions(n: int, start: str = "2026-07-31") -> list:
    from valuation.screener import market_session as _ms
    out, d = [], dt.date.fromisoformat(start)
    while len(out) < n:
        if _ms.is_trading_day(d):
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


RUN = _sessions(42)


def _book(tmpdir, positions=None, benchmark="SPY"):
    """Shaped exactly like the real `valquo_track.json`."""
    # WBS at 2% ON PURPOSE. `contract_row` refuses a row when under MIN_COVERAGE = 0.95 of
    # the book's WEIGHT can be priced, so a 20% WBS made every post-staleness row refuse and
    # the comparison this suite exists for was never reached. At 2% the row still prices and
    # `n_priced` falls from 3 to 2, which is the divergence worth testing.
    positions = positions if positions is not None else [
        {"ticker": "AAA", "weight": 0.49},
        {"ticker": "BBB", "weight": 0.49},
        {"ticker": "WBS", "weight": 0.02}]
    p = os.path.join(tmpdir, "valquo_track.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"inception_date": INCEPTION, "scan_date": "2026-07-24",
                   "benchmark": benchmark, "positions": positions}, f)
    return p


class _CountingTape:
    """A price vendor that COUNTS its calls, per ticker.

    `stale_through` reproduces the WBS shape that costs 44% of the real runtime: a frame whose
    newest row stops partway through the run. It carries `as_of` so the real staleness rule
    applies, and it RAISES for a ticker in `dead` so the dead-fallback case is exercised too.
    """

    def __init__(self, series: dict, *, stale_through: dict = None, dead=()):
        self.series = {k.upper(): v for k, v in series.items()}
        self.stale_through = {k.upper(): v for k, v in (stale_through or {}).items()}
        self.dead = {t.upper() for t in dead}
        self.calls = []

    def __call__(self, ticker, days=400, as_of=None):
        t = ticker.upper()
        self.calls.append(t)
        if t in self.dead:
            raise RuntimeError("vendor timed out for %s" % t)
        s = self.series.get(t)
        if s is None:
            return None
        cut = self.stale_through.get(t)
        if cut:
            s = {d: v for d, v in s.items() if d <= cut}
        if not s:
            return None
        # THE REAL FRESHNESS RULE, imported rather than reimplemented: a frame whose newest
        # row predates the date the caller needs is a FAILURE, not a success.
        import pandas as pd
        df = pd.DataFrame({"Date": list(s.keys()), "Close": list(s.values())})
        if as_of and max(s) < str(as_of)[:10]:
            return None
        return df

    def count(self, ticker) -> int:
        return self.calls.count(ticker.upper())

    @property
    def max_per_ticker(self) -> int:
        return max((self.calls.count(t) for t in set(self.calls)), default=0)


def _tape_for(run, *, stale_through=None, dead=()):
    """AAA rises, BBB falls, WBS is the stale one, SPY is the benchmark."""
    series = {"AAA": {}, "BBB": {}, "WBS": {}, "SPY": {}}
    series["AAA"][INCEPTION] = 100.0
    series["BBB"][INCEPTION] = 50.0
    series["WBS"][INCEPTION] = 20.0
    series["SPY"][INCEPTION] = 400.0
    for i, d in enumerate(run):
        series["AAA"][d] = 100.0 + i
        series["BBB"][d] = 50.0 - i * 0.1
        series["WBS"][d] = 20.0 + i * 0.05
        series["SPY"][d] = 400.0 + i * 0.5
    return _CountingTape(series, stale_through=stale_through, dead=dead)


# =======================================================================================
# PROOF 2 — at most ONE vendor call per ticker across a full 42-date run
# =======================================================================================
class OneVendorCallPerTicker(unittest.TestCase):

    def test_a_42_date_reconstruct_calls_each_ticker_ONCE(self):
        """Four tickers (three positions + the benchmark) over 42 dates is 168 calls
        unmemoised. The memo must make FOUR."""
        tape = _tape_for(RUN)
        with tempfile.TemporaryDirectory() as d:
            res = TR.reconstruct(RUN, meta_path=_book(d), fetch=tape)
        self.assertEqual(res["n_requested"], 42)
        self.assertEqual(tape.max_per_ticker, 1,
                         "a ticker was fetched more than once: %s"
                         % {t: tape.count(t) for t in set(tape.calls)})
        self.assertEqual(len(tape.calls), 4, tape.calls)
        self.assertEqual(res["prices"]["max_calls_per_ticker"], 1, res["prices"])
        self.assertEqual(res["prices"]["vendor_calls"], 4, res["prices"])
        # NON-VACUOUS: the run must actually have priced days, or "one call per ticker" is
        # satisfied by a run that fetched nothing.
        self.assertGreater(res["n_computed"], 30, res["refused"][:3])

    def test_WBS_the_STALE_name_is_fetched_ONCE_not_42_times(self):
        """The 44% of real runtime. WBS's frame stops at date 10 of 42, so a per-date call
        is judged stale on the other 32 and pays the dead fallback 32 times over."""
        cut = RUN[9]
        tape = _tape_for(RUN, stale_through={"WBS": cut})
        with tempfile.TemporaryDirectory() as d:
            res = TR.reconstruct(RUN, meta_path=_book(d), fetch=tape)
        self.assertEqual(tape.count("WBS"), 1,
                         "the stale name was re-fetched per date: %d times"
                         % tape.count("WBS"))
        self.assertGreater(res["n_computed"], 30, res["refused"][:3])

    def test_a_DEAD_vendor_fails_ONCE_per_ticker_and_not_once_per_date(self):
        """A raising vendor is cached as a failure. Otherwise the timeout is paid 42 times --
        which is the shape that made the door exceed 600s."""
        tape = _tape_for(RUN, dead=["WBS"])
        with tempfile.TemporaryDirectory() as d:
            res = TR.reconstruct(RUN, meta_path=_book(d), fetch=tape)
        self.assertEqual(tape.count("WBS"), 1,
                         "a dead vendor was retried per date: %d times" % tape.count("WBS"))
        self.assertGreater(res["n_computed"], 30,
                           "the dead name took the whole run down: %s" % res["refused"][:3])

    def test_the_FULL_validation_is_also_one_call_per_ticker_and_is_NOT_capped(self):
        """`validate_against_record` is the expensive half on a real record and it must get
        cheaper WITHOUT getting smaller -- it is the precondition that licenses a point."""
        tape = _tape_for(RUN)
        rec = [{"date": d, "valquo_pct": 1.0, "spy_pct": 1.0, "n_priced": 3} for d in RUN]
        with tempfile.TemporaryDirectory() as d:
            res = TR.validate_against_record(rec, meta_path=_book(d), fetch=tape)
        self.assertEqual(tape.max_per_ticker, 1, tape.calls)
        self.assertEqual(res["prices"]["max_calls_per_ticker"], 1, res["prices"])
        # NOT CAPPED: every recorded row was compared, not a prefix of them.
        self.assertEqual(res["n_compared"] + res["n_refused"], 42,
                         "the validation silently shrank: %r" % res["n_compared"])
        self.assertEqual(res["n_refused"], 0, res["days"])
        self.assertEqual(res["n_compared"], 42, res["n_compared"])

    def test_no_caller_in_this_module_passes_a_days_LIMIT(self):
        """`limit` stays available and unused. Read from the syntax tree, because the
        docstrings necessarily discuss it."""
        import ast
        src = open(os.path.join(REPO, "valuation/screener/track_reconstruct.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            name = getattr(call.func, "attr", getattr(call.func, "id", ""))
            if name == "validate_against_record":
                for kw in call.keywords:
                    self.assertNotEqual(kw.arg, "limit",
                                        "a days limit was wired into the validation")
        # And the parameter still exists, so this is "unused" and not "removed".
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "validate_against_record")
        self.assertIn("limit", [a.arg for a in fn.args.kwonlyargs])


# =======================================================================================
# PROOF 3 — memoised frames give the SAME close as unmemoised calls, on every date
# =======================================================================================
class MemoisedClosesMatchUnmemoised(unittest.TestCase):

    def _unmemoised(self, run, tape_factory, book):
        """What the per-date route produces: a fresh `contract_row` per date, `fetch` passed
        straight through, no memo anywhere."""
        rows = {}
        for d in run:
            tape = tape_factory()
            r = IM.contract_row(as_of=d, meta_path=book, fetch=tape,
                                refuse_before_close=False)
            rows[d] = r.get("row") if r.get("ok") else {"refused": r.get("reason")}
        return rows

    def test_every_date_matches_the_unmemoised_route_exactly(self):
        """The whole point: one call per ticker must not change a single number."""
        book_dir = tempfile.mkdtemp()
        book = _book(book_dir)
        unmemo = self._unmemoised(RUN, lambda: _tape_for(RUN), book)

        memo_tape = _tape_for(RUN)
        res = TR.reconstruct(RUN, meta_path=book, fetch=memo_tape)
        got = {p["date"]: p for p in res["points"]}

        self.assertEqual(sorted(got), sorted(d for d in RUN if "refused" not in unmemo[d]),
                         "the memoised run priced a different SET of dates")
        for d in got:
            for k in ("valquo_pct", "spy_pct", "excess_pp", "n_priced"):
                self.assertEqual(got[d][k], unmemo[d][k],
                                 "%s differs on %s: memo %r vs per-date %r"
                                 % (k, d, got[d][k], unmemo[d][k]))

    def test_it_matches_WHERE_STALENESS_BITES_which_is_the_case_that_could_diverge(self):
        """NON-VACUOUS, and the one comparison that can actually fail.

        `as_of` does not truncate a frame -- it only decides accept/reject via `_stale`
        (`last < as_of`). So the anchor choice is the whole risk: anchored on the LATEST date
        a stale frame is rejected, the memo caches the failure, and the name reads UNPRICED on
        the EARLY dates a per-date call PRICES. Anchored on the EARLIEST it is accepted and the
        map simply has no entry after its last row -- which is what per-date produces.

        WBS stops at date 10 of 42 here, so `n_priced` MUST fall partway through the run. That
        is asserted, because if it never fell this test would be comparing two routes on a
        case where staleness never bit.
        """
        cut = RUN[9]
        book_dir = tempfile.mkdtemp()
        book = _book(book_dir)
        unmemo = self._unmemoised(RUN, lambda: _tape_for(RUN, stale_through={"WBS": cut}),
                                  book)
        memo_tape = _tape_for(RUN, stale_through={"WBS": cut})
        res = TR.reconstruct(RUN, meta_path=book, fetch=memo_tape)
        got = {p["date"]: p for p in res["points"]}

        counts = {d: unmemo[d].get("n_priced") for d in RUN if "refused" not in unmemo[d]}
        self.assertEqual(set(counts.values()), {3, 2},
                         "staleness never bit, so this comparison proves nothing: %r"
                         % sorted(set(counts.values())))

        for d in got:
            for k in ("valquo_pct", "spy_pct", "excess_pp", "n_priced"):
                self.assertEqual(got[d][k], unmemo[d][k],
                                 "%s differs on %s (stale case): memo %r vs per-date %r"
                                 % (k, d, got[d][k], unmemo[d][k]))
        self.assertEqual(memo_tape.count("WBS"), 1)

    def test_the_anchor_is_the_EARLIEST_date_and_the_window_reaches_it(self):
        """Both halves of the anchor argument, stated as assertions rather than prose."""
        memo = TR._PriceMemo(RUN)
        self.assertEqual(memo.anchor, RUN[0])
        self.assertEqual(memo.last, RUN[-1])
        need = (dt.date.today() - dt.date.fromisoformat(RUN[0])).days
        self.assertGreaterEqual(memo.days, need,
                                "the window does not reach the earliest date in the run")

    def test_the_memo_makes_NO_call_until_it_is_asked(self):
        """Constructed in both callers on every invocation, including for an empty record --
        `validate_against_record([])` must not touch a vendor."""
        tape = _tape_for(RUN)
        TR._PriceMemo(RUN, base=tape)
        self.assertEqual(tape.calls, [], "the memo fetched at construction time")
        self.assertEqual(TR.validate_against_record([])["prices"]["vendor_calls"], 0)

    def test_a_two_argument_fetcher_is_NOT_handed_an_as_of_keyword(self):
        """The defect this nearly shipped with. Several suites inject `fetch(ticker, days)`;
        passing one an unexpected keyword raises TypeError, which the memo would cache as a
        failure and EVERY name would read unpriced. `index_mark._accepts_as_of` is imported
        rather than re-implemented, and this pins that the narrow path still works."""
        seen = {}

        def two_arg(ticker, days=400):
            seen[ticker] = days
            import pandas as pd
            return pd.DataFrame({"Date": [INCEPTION, RUN[0]], "Close": [100.0, 110.0]})

        memo = TR._PriceMemo(RUN, base=two_arg)
        self.assertFalse(memo._base_takes_as_of)
        df = memo("AAA")
        self.assertIsNotNone(df, "a two-argument fetcher was broken by an as_of keyword")
        self.assertIn("AAA", seen)


# =======================================================================================
# THE WRITER'S ROUTE IS UNTOUCHED
# =======================================================================================
class TheWritersDailyPathIsUnchanged(unittest.TestCase):

    def test_index_mark_contains_no_memo_and_defaults_to_the_vendor_per_date(self):
        """`index_mark` is not edited. `contract_row`'s own default is still
        `prices.get_history_df`, so the daily write is byte-identical."""
        src = open(os.path.join(REPO, "valuation/screener/index_mark.py"),
                   encoding="utf-8").read()
        self.assertIn("fetch = fetch or _prices.get_history_df", src)
        self.assertNotIn("_PriceMemo", src,
                         "the memo leaked into the writer's own module")

    def test_the_memo_lives_in_the_RECONSTRUCTION_module_only(self):
        import ast
        for mod in ("valuation/screener/index_mark.py", "valuation/screener/prices.py"):
            src = open(os.path.join(REPO, mod), encoding="utf-8").read()
            names = {n.name for n in ast.walk(ast.parse(src))
                     if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            self.assertNotIn("_PriceMemo", names, mod)

    def test_a_contract_row_with_fetch_None_still_resolves_the_vendor_itself(self):
        """The writer's path. Proved by signature rather than by a live call: `fetch` defaults
        to None and `contract_row` resolves it internally, so nothing the reconstruction does
        can reach it."""
        import inspect
        self.assertIsNone(inspect.signature(IM.contract_row).parameters["fetch"].default)


if __name__ == "__main__":
    unittest.main(verbosity=2)
