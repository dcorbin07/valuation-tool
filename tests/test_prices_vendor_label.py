"""`prices.get_history_df` — the fallback stays, and it may never be silent.

Reported out-of-lane by the app fixer. The defect: a bare `except Exception` around the whole
primary path fell through to yfinance with nothing recording it, so any price-derived figure in
the product could silently be a yfinance figure — and yfinance AUTO-ADJUSTS, which makes it a
different quantity from an as-traded close (`U1-SPLIT`: NVDA 2012 reads 0.27 adjusted against a
raw 11.97). `COVERAGE-RULE` family: the run completes, nothing raises, and the number means
something else.

**NO TEST HERE TOUCHES THE NETWORK.** Every vendor is faked, so the suite exercises the fallback
on demand rather than waiting for Stooq to have a bad afternoon — and so it still passes on the
day Stooq recovers.
"""
from __future__ import annotations

import ast
import io
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  must precede the valuation imports

import pandas as pd                                    # noqa: E402
import requests                                        # noqa: E402

from valuation.screener import prices as P             # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "valuation", "screener", "prices.py")
_SKIPS = []


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()



def _code_only(src):
    """Source with docstrings blanked. `MA49`'s family: prose that discusses a hazard is not the
    hazard, and a guard that cannot tell code from comments about code is not reading the tree."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body[0].value.value = ""
    return ast.unparse(tree)


CSV = "Date,Open,High,Low,Close,Volume\n2026-01-02,1,2,0.5,1.5,100\n2026-01-03,1,2,0.5,1.6,110\n"


class _Resp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("%d Client Error" % self.status_code, response=self)


def _fake_yf(rows=40):
    """A stand-in yfinance whose frame is distinguishable from the Stooq one."""
    import types

    idx = pd.date_range("2026-01-01", periods=rows, freq="D")

    class _T:
        def __init__(self, *a, **k):
            pass

        def history(self, period=None, auto_adjust=None):
            _T.last_auto_adjust = auto_adjust
            return pd.DataFrame({"Open": [9.0] * rows, "High": [9.0] * rows,
                                 "Low": [9.0] * rows, "Close": [9.0] * rows,
                                 "Volume": [1] * rows}, index=idx)

    mod = types.ModuleType("yfinance")
    mod.Ticker = _T
    return mod, _T


class _Patch:
    """Swap requests.get and the yfinance module for the duration of a block."""

    def __init__(self, get=None, yf=None):
        self.get, self.yf = get, yf

    def __enter__(self):
        self._real_get = requests.get
        self._real_yf = sys.modules.get("yfinance")
        if self.get is not None:
            requests.get = self.get
        if self.yf is not None:
            sys.modules["yfinance"] = self.yf
        P.reset_census()
        return self

    def __exit__(self, *a):
        requests.get = self._real_get
        if self._real_yf is None:
            sys.modules.pop("yfinance", None)
        else:
            sys.modules["yfinance"] = self._real_yf
        return False


# ================================================================== the required assertion

class TestFallbackIsLabelled(unittest.TestCase):

    def test_the_primary_succeeding_is_labelled_stooq(self):
        with _Patch(get=lambda *a, **k: _Resp(CSV)):
            df = P.get_history_df("AAPL", days=10)
        self.assertIsNotNone(df)
        self.assertEqual(P.source_of(df), P.SRC_STOOQ)

    def test_A_PRIMARY_FAILURE_PRODUCES_A_LABELLED_FALLBACK_NEVER_A_SILENT_ONE(self):
        """THE test this bug report asks for. Every way the primary can fail must produce a
        frame that SAYS it came from yfinance."""
        yf, _T = _fake_yf()
        failures = {
            "http_404": lambda *a, **k: _Resp("<html>not found</html>", 404),
            "connection": _raiser(requests.ConnectionError("no route")),
            "timeout": _raiser(requests.Timeout("slow")),
            "not_csv": lambda *a, **k: _Resp("<html>javascript challenge</html>"),
            "empty_body": lambda *a, **k: _Resp(""),
            "no_close_column": lambda *a, **k: _Resp("Date,Open\n2026-01-02,1\n"),
        }
        for name, get in failures.items():
            with self.subTest(failure=name):
                with _Patch(get=get, yf=yf):
                    df = P.get_history_df("AAPL", days=10)
                    self.assertIsNotNone(df, "%s: fell through to nothing" % name)
                    self.assertEqual(P.source_of(df), P.SRC_YFINANCE,
                                     "%s: fallback served but was NOT labelled" % name)
                    self.assertEqual(P.adjustment_of(df), "auto_adjusted")
                    self.assertEqual(P.source_census()["primary_failures"], 1)

    def test_the_fallback_is_LOUD_and_names_the_primary_exception(self):
        """A label a reader has to go looking for is better than nothing and worse than a log
        line. The warning must name the ticker, the vendor and the actual failure."""
        yf, _ = _fake_yf()
        with _Patch(get=_raiser(requests.ConnectionError("no route")), yf=yf):
            with self.assertLogs("valuation.screener.prices", level=logging.WARNING) as cm:
                P.get_history_df("AAPL", days=10)
        blob = "\n".join(cm.output)
        self.assertIn("AAPL", blob)
        self.assertIn("yfinance", blob)
        self.assertIn("ConnectionError", blob)
        self.assertIn("AUTO-ADJUSTED", blob)

    def test_the_census_records_the_vendor_per_ticker(self):
        yf, _ = _fake_yf()
        with _Patch(get=lambda *a, **k: _Resp(CSV), yf=yf):
            P.get_history_df("AAA", days=10)
            with _PatchGet(_raiser(requests.ConnectionError("x"))):
                P.get_history_df("BBB", days=10)
            c = P.source_census()
        self.assertEqual(c["last_by_ticker"]["AAA"], P.SRC_STOOQ)
        self.assertEqual(c["last_by_ticker"]["BBB"], P.SRC_YFINANCE)
        self.assertEqual(c["by_vendor"][P.SRC_STOOQ], 1)
        self.assertEqual(c["by_vendor"][P.SRC_YFINANCE], 1)


def _raiser(exc):
    def _f(*a, **k):
        raise exc
    return _f


class _PatchGet:
    def __init__(self, get):
        self.get = get

    def __enter__(self):
        self._real = requests.get
        requests.get = self.get
        return self

    def __exit__(self, *a):
        requests.get = self._real
        return False


# ============================================================ the except must be NARROW

class TestNarrowExcept(unittest.TestCase):
    """A bug in this module is a bug, not a vendor outage. The old bare `except Exception`
    could not tell the difference and routed both into the fallback."""

    def test_an_ImportError_PROPAGATES_and_does_not_read_as_a_vendor_outage(self):
        """The sharpest case: `import pandas` and `import requests` sit inside the old try, so a
        BROKEN INSTALL looked exactly like a bad afternoon at Stooq — and produced yfinance
        numbers under a healthy-looking run."""
        real = P._primary_errors

        def boom():
            raise ImportError("pandas is not installed")
        try:
            P._primary_errors = boom
            with self.assertRaises(ImportError):
                P.get_history_df("AAPL", days=10)
        finally:
            P._primary_errors = real

    def test_a_programming_error_in_the_primary_path_PROPAGATES(self):
        """An AttributeError from a typo must not silently become a yfinance figure."""
        yf, _ = _fake_yf()
        with _Patch(get=_raiser(AttributeError("typo")), yf=yf):
            with self.assertRaises(AttributeError):
                P.get_history_df("AAPL", days=10)

    def test_KeyboardInterrupt_is_not_swallowed(self):
        yf, _ = _fake_yf()
        with _Patch(get=_raiser(KeyboardInterrupt()), yf=yf):
            with self.assertRaises(KeyboardInterrupt):
                P.get_history_df("AAPL", days=10)

    def test_the_except_clause_is_not_a_bare_Exception_in_the_primary_path(self):
        """Read from the AST, not grepped — this module's docstring discusses
        `except Exception` at length and a substring guard would fire on the prose."""
        tree = ast.parse(_read(SRC))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "get_history_df")
        for h in [n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]:
            self.assertIsNotNone(h.type, "a bare `except:` is back in get_history_df")
            self.assertNotEqual(getattr(h.type, "id", None), "Exception",
                                "`except Exception` is back in get_history_df")


# ==================================================== the adjustment convention is DECLARED

class TestAdjustmentConvention(unittest.TestCase):

    def test_auto_adjust_is_passed_EXPLICITLY_and_never_inherited(self):
        """Relying on a vendor library's default is how a convention changes under you between
        releases, and yfinance has moved this one before. Checked in the AST AND at runtime."""
        tree = ast.parse(_read(SRC))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_yf_history")
        calls = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "history"]
        self.assertTrue(calls, "_yf_history no longer calls .history")
        for c in calls:
            kw = {k.arg for k in c.keywords}
            self.assertIn("auto_adjust", kw, "auto_adjust is being INHERITED, not passed")

        yf, T = _fake_yf()
        with _Patch(get=_raiser(requests.ConnectionError("x")), yf=yf):
            P.get_history_df("AAPL", days=10)
        self.assertIs(T.last_auto_adjust, True)

    def test_stooqs_convention_is_recorded_as_UNVERIFIED_and_not_guessed(self):
        """It cannot be measured from here — Stooq refuses this client entirely — and guessing
        it would invent the one fact this module exists to stop people inventing."""
        self.assertEqual(P.VENDOR_ADJUSTMENT[P.SRC_STOOQ], "unverified")
        self.assertEqual(P.VENDOR_ADJUSTMENT[P.SRC_YFINANCE], "auto_adjusted")

    def test_an_unlabelled_frame_reports_None_and_never_the_primary(self):
        """`None` means 'cannot tell'. Resolving it to the primary is the defect itself."""
        self.assertIsNone(P.source_of(pd.DataFrame({"Close": [1.0]})))
        self.assertIsNone(P.source_of(None))
        self.assertIsNone(P.adjustment_of(pd.DataFrame({"Close": [1.0]})))


# ============================================================== the label reaches consumers

class TestConsumersSeeTheLabel(unittest.TestCase):

    def test_get_quote_carries_the_source_and_the_adjustment(self):
        long_csv = "Date,Open,High,Low,Close,Volume\n" + "".join(
            "2026-01-%02d,1,2,0.5,%f,100\n" % ((i % 28) + 1, 1.0 + i * 0.01) for i in range(60))
        with _Patch(get=lambda *a, **k: _Resp(long_csv)):
            q = P.get_quote("AAPL")
        self.assertIsNotNone(q)
        self.assertEqual(q["source"], P.SRC_STOOQ)
        self.assertEqual(q["adjusted"], "unverified")

    def test_close_series_with_source_carries_it_and_plain_close_series_still_returns_a_pair(self):
        """`close_series` is what ~20 call sites use and its shape is deliberately unchanged —
        a third element would break every one of them. The labelled form is additive."""
        with _Patch(get=lambda *a, **k: _Resp(CSV)):
            pair = P.close_series("AAPL", days=10)
            trip = P.close_series_with_source("AAPL", days=10)
        self.assertEqual(len(pair), 2)
        self.assertEqual(len(trip), 3)
        self.assertEqual(trip[2], P.SRC_STOOQ)
        self.assertEqual(pair[0], trip[0])

    def test_index_mark_records_which_vendor_served_each_leg(self):
        """`index_mark`'s payload used to carry a constant naming the ROUTE. It now names what
        actually answered, and the benchmark leg is broken out because its own reproduction note
        found that leg EXACT while the book leg missed by +0.0201pp."""
        from valuation.screener import index_mark as IM

        def fetch(ticker, days=None):
            df = pd.DataFrame({"Date": ["2026-01-02", "2026-01-05"], "Close": [10.0, 11.0]})
            df.attrs["valquo_src"] = P.SRC_YFINANCE if ticker == "SPY" else P.SRC_STOOQ
            return df

        seen = {}
        IM._closes("SPY", fetch, seen)
        IM._closes("AAPL", fetch, seen)
        self.assertEqual(seen["SPY"], P.SRC_YFINANCE)
        self.assertEqual(seen["AAPL"], P.SRC_STOOQ)

        c = IM._vendor_census(seen, "SPY")
        self.assertEqual(c["benchmark_leg"], P.SRC_YFINANCE)
        self.assertEqual(c["book_leg_by_vendor"], {P.SRC_STOOQ: 1})
        self.assertFalse(c["legs_agree"], "the legs were served by DIFFERENT vendors")

    def test_index_mark_reports_an_unlabelled_fetcher_as_unlabelled_not_as_the_primary(self):
        from valuation.screener import index_mark as IM

        def bare(ticker, days=None):
            return pd.DataFrame({"Date": ["2026-01-02"], "Close": [10.0]})

        seen = {}
        IM._closes("AAPL", bare, seen)
        self.assertIsNone(seen["AAPL"])
        c = IM._vendor_census(seen, "SPY")
        self.assertEqual(c["book_leg_by_vendor"], {"unlabelled": 1})
        self.assertNotIn(P.SRC_STOOQ, c["book_leg_by_vendor"])

    def test_a_fetcher_that_raises_is_recorded_rather_than_dropped(self):
        from valuation.screener import index_mark as IM

        def bad(ticker, days=None):
            raise RuntimeError("vendor exploded")

        seen = {}
        self.assertEqual(IM._closes("AAPL", bad, seen), {})
        self.assertEqual(seen["AAPL"], "fetch_raised")


# ============================================ the strike rule, and it does NOT bite here

class TestStrikeRuleDoesNotBiteOnThisPath(unittest.TestCase):
    """`U1-SPLIT`'s rule is `raw_close` for anything touching a STRIKE, because option strikes
    are as-traded and an adjusted close is a different quantity (NVDA 2012: 0.27 against 11.97).

    Measured: the set of modules importing `screener.prices` and the set mentioning a strike are
    **DISJOINT**. The options work sources its as-traded prices from
    `data/bulk/prepared/bars`'s `raw_close` and the pinned chain freezes, never from here.

    **So the strike hazard is structurally absent on this path — and the adjusted-vs-raw
    distinction still BITES, for a different reason**: against the recorded track, where it is
    the whole +0.0201pp seam. This test exists so that wiring the two together later is a
    deliberate act with a red suite attached, rather than a quiet import.
    """

    def _scan(self):
        """Imports from the AST; strikes from code with docstrings stripped.

        A grep cannot do this job: `index_mark.py`'s docstring contains the string
        "screener/prices.py" while its actual import is `from . import prices as _prices`, so a
        pattern-based scan matched it for the wrong reason and missed it for the right one --
        found by this class's own vacuity test.
        """
        root = os.path.join(REPO, "valuation")
        imp, strike = set(), set()
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if not f.endswith(".py"):
                    continue
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, REPO)
                body = _read(full)
                try:
                    tree = ast.parse(body)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        names = {a.name for a in node.names}
                        if mod.endswith("screener.prices") or mod.endswith(".prices") \
                                or mod == "prices" or ("prices" in names
                                                       and mod.endswith("screener")) \
                                or ("prices" in names and mod == ""):
                            imp.add(rel)
                    elif isinstance(node, ast.Import):
                        for a in node.names:
                            if a.name.endswith("screener.prices"):
                                imp.add(rel)
                # docstrings stripped: prose about a strike is not a strike
                if "strike" in _code_only(body):
                    strike.add(rel)
        return imp, strike

    def test_no_module_both_imports_prices_and_touches_a_strike(self):
        imp, strike = self._scan()
        self.assertTrue(imp, "the scan found no importers at all - it is measuring nothing")
        self.assertTrue(strike, "the scan found no strike modules - it is measuring nothing")
        both = sorted(imp & strike)
        self.assertEqual(both, [], "a module now takes prices.py into a strike path: %s" % both)

    def test_the_scan_is_not_vacuous_in_either_direction(self):
        """A guard that finds nothing passes for the wrong reason. Both populations must be
        real and the intersection must be genuinely computed."""
        imp, strike = self._scan()
        self.assertGreaterEqual(len(imp), 8, "importer scan looks broken")
        self.assertGreaterEqual(len(strike), 20, "strike scan looks broken")
        # and a known member of each, so a regex that silently stopped matching is caught
        self.assertIn(os.path.join("valuation", "screener", "index_mark.py"), imp)
        self.assertIn(os.path.join("valuation", "edge", "blackscholes.py"), strike)


# ========================================================================= mutation battery

def _label_works():
    """The property every mutation must break."""
    yf, _ = _fake_yf()
    with _Patch(get=_raiser(requests.ConnectionError("x")), yf=yf):
        df = P.get_history_df("AAPL", days=10)
        if P.source_of(df) != P.SRC_YFINANCE:
            return False
    with _Patch(get=lambda *a, **k: _Resp(CSV)):
        df2 = P.get_history_df("AAPL", days=10)
        if P.source_of(df2) != P.SRC_STOOQ:
            return False
    return True


class TestMutations(unittest.TestCase):

    def test_zzz_baseline_the_property_holds_unmutated(self):
        self.assertTrue(_label_works())

    def _mutate(self, attr, repl):
        real = getattr(P, attr)
        try:
            setattr(P, attr, repl)
            caught = not _label_works()
        finally:
            setattr(P, attr, real)
        self.assertIs(getattr(P, attr), real, "source not restored")
        self.assertTrue(caught, "MUTATION SURVIVED: %s" % attr)

    def test_m1_a_label_that_does_not_stamp_is_caught(self):
        self._mutate("_label", lambda df, ticker, src: df)

    def test_m2_a_label_that_always_says_stooq_is_caught(self):
        real = P._label
        self._mutate("_label", lambda df, t, src: real(df, t, P.SRC_STOOQ))

    def test_m3_source_of_defaulting_to_the_primary_is_caught(self):
        self._mutate("source_of", lambda df: P.SRC_STOOQ)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
