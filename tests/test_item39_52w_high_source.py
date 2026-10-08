# -*- coding: utf-8 -*-
"""ITEM 39(a) — the engine's 52-week high stops being silently losable.

THE DEFECT, measured from the 2026-10-07 hot scan's own log rather than inferred:

* the dip precompute reported **`valued: 218, failed: 0, no_drawdown: 218`** — every word true,
  and not one of them said the engine's price history had returned **nothing for every single
  name**;
* because the block that sets `price_52w_high` sat under a bare `except Exception: pass`, and
  the FUNDAMENTALS are gap-filled from EDGAR (which Yahoo's refusal does not touch), so every
  valuation still succeeded;
* item 36's scan-ratio fallback then carried the entire screen. Correctly — without it the run
  returns zero rows — and invisibly, which is the half this item repairs.

THE CAUSE: Yahoo refusing the runner. **99 × `HTTP Error 401: ... "Invalid Crumb"`** in that
log, plus **87 names** classified as genuine rate limits by `prices.py`. It is NOT a yfinance
version change: 1.6.0, the version the runner installs, returns 251 rows and a real high from a
residential IP (tested 2026-10-08).

WHAT THESE TESTS PIN, in order of what it would cost to lose:

* **The three states must be distinguishable.** Primary served it / fallback served it / nobody
  did. Two of those three used to look identical.
* **The basis must be read, never assumed.** This high is divided into an AS-TRADED `price`;
  measured at yfinance 1.6.0, the as-traded 52-week high is **+3.15% above** the adjusted one
  for O. Stooq's basis is `unverified` and that word is not rounded to a guess.
* **`auto_adjust` is STATED.** The value is unchanged — `True` is what the inherited default
  already gave — so no published drawdown moves. What changes is that a yfinance release can no
  longer move it without a diff.
* **The window is 52 weeks** even though the fallback pulls 400 days.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

import pandas as pd                                                        # noqa: E402

from valuation.data import yahoo                                           # noqa: E402
from valuation.data.models import CompanyData                              # noqa: E402
from valuation.screener import prices                                      # noqa: E402
from valuation.web import dip                                              # noqa: E402
from tests.source_bounds import code_only, function_source                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def labelled(high=123.45, low=100.0, vendor=prices.SRC_YFINANCE, n=300, spike=None):
    """A price frame carrying the vendor LABEL, so the basis is read from `prices.py`."""
    closes = [low] * (n - 1) + [high]
    df = pd.DataFrame({"Close": closes},
                      index=pd.date_range("2025-01-01", periods=n, freq="D"))
    if spike is not None:
        df.iloc[0, df.columns.get_loc("Close")] = spike
    return prices._label(df, "KO", vendor)


class Boom(object):
    """A Ticker whose `history` raises the LIVE failure and whose everything else is real."""

    def __init__(self, inner=None):
        self._inner = inner

    def history(self, *a, **k):
        raise RuntimeError("HTTP Error 401: Invalid Crumb")

    def __getattr__(self, k):
        if self._inner is None:
            raise AttributeError(k)
        return getattr(self._inner, k)


#: A sentinel, NOT the string "unset". `self.frame != "unset"` raises
#: `ValueError: The truth value of a DataFrame is ambiguous` the moment a frame is passed --
#: pandas refuses `==` against a scalar in a boolean context, which is the correct behaviour
#: and the reason a sentinel is compared with `is`.
_UNSET = object()


class _Patched(object):
    """Break the primary, and optionally hand the fallback a frame."""

    def __init__(self, frame=_UNSET):
        self.frame = frame

    def __enter__(self):
        import yfinance as yf
        self._yf, self._ticker = yf, yf.Ticker
        self._hist = prices.get_history_df
        yf.Ticker = lambda t, *a, **k: Boom()
        if self.frame is not _UNSET:
            prices.get_history_df = lambda *a, **k: self.frame
        return self

    def __exit__(self, *e):
        self._yf.Ticker = self._ticker
        prices.get_history_df = self._hist
        return False


class ThreeStatesNotTwo(unittest.TestCase):
    """The whole defect was that "the fallback saved it" and "the primary worked" looked alike."""

    def test_the_fallback_serves_the_high_and_says_which_rung_did(self):
        with _Patched(labelled()):
            cd = yahoo.fetch("KO")
        self.assertEqual(cd.price_52w_high, 123.45)
        self.assertEqual(cd.price_52w_high_source, "prices:yfinance")
        self.assertEqual(cd.price_52w_high_basis, "adjusted")
        # ...and the primary's failure is KEPT, not overwritten by the rescue.
        self.assertIn("Invalid Crumb", cd.price_52w_high_reason or "")

    def test_the_ORDINARY_path_records_its_source_and_basis_too(self):
        """MISSED BY MUTATION UNTIL THIS EXISTED.

        Every provenance assertion was on the FALLBACK path, so blanking the primary's own
        label -- `price_52w_high_source = None` on the success branch -- passed the whole
        suite. The state that matters most is the common one, and it was the untested one.
        """
        cd = yahoo.fetch("KO")
        self.assertIsNotNone(cd.price_52w_high)
        self.assertEqual(cd.price_52w_high_source, "yahoo")
        self.assertEqual(cd.price_52w_high_basis, "adjusted")
        self.assertIsNone(cd.price_52w_high_reason,
                          "a working primary must leave no failure reason behind")

    def test_the_rescue_is_written_into_the_quality_notes(self):
        with _Patched(labelled()):
            cd = yahoo.fetch("KO")
        notes = [n for n in cd.quality_notes if "52-week high from" in n]
        self.assertTrue(notes, "a rescued high must say so on the company itself")
        self.assertIn("prices:yfinance", notes[0])

    def test_both_dead_leaves_NO_high_and_a_reason_that_names_the_failure(self):
        """A missing high must never be confusable with a name that is not in a drawdown."""
        with _Patched(None):
            cd = yahoo.fetch("KO")
        self.assertIsNone(cd.price_52w_high)
        self.assertIsNone(cd.price_52w_high_source)
        self.assertIn("Invalid Crumb", cd.price_52w_high_reason or "")

    def test_a_fallback_that_itself_RAISES_still_leaves_a_reason(self):
        """The rescue failing must not erase the diagnosis of what it was rescuing."""
        def boom(*a, **k):
            raise RuntimeError("fallback exploded")

        with _Patched():
            prices_real = prices.get_history_df
            prices.get_history_df = boom
            try:
                cd = yahoo.fetch("KO")
            finally:
                prices.get_history_df = prices_real
        self.assertIsNone(cd.price_52w_high)
        self.assertIn("Invalid Crumb", cd.price_52w_high_reason or "")
        self.assertIn("fallback also failed", cd.price_52w_high_reason or "")

    def test_an_EMPTY_primary_frame_is_a_reason_and_not_an_exception(self):
        """yfinance returns an empty frame rather than raising for an unknown symbol, and the
        old code treated that identically to success-with-no-high: silently."""
        import yfinance as yf
        real = yf.Ticker

        class Empty(object):
            def history(self, *a, **k):
                return pd.DataFrame()

            def __getattr__(self, k):
                raise AttributeError(k)

        yf.Ticker = lambda t, *a, **k: Empty()
        real_hist = prices.get_history_df
        prices.get_history_df = lambda *a, **k: None
        try:
            cd = yahoo.fetch("KO")
        finally:
            yf.Ticker, prices.get_history_df = real, real_hist
        self.assertIsNone(cd.price_52w_high)
        self.assertIn("empty frame", (cd.price_52w_high_reason or "").lower())


class TheBasisIsReadNeverGuessed(unittest.TestCase):

    def test_an_unverified_vendor_reports_unverified(self):
        """`prices.py` refuses to round `unverified` to a guess and neither may this.

        Stooq serves an as-traded close and yfinance an adjusted one. Calling both "adjusted"
        would make the drawdown's basis a function of which vendor happened to answer.
        """
        with _Patched(labelled(vendor=prices.SRC_STOOQ)):
            cd = yahoo.fetch("KO")
        self.assertEqual(cd.price_52w_high_source, "prices:stooq")
        self.assertEqual(cd.price_52w_high_basis, "unverified")

    def test_the_vocabulary_matches_the_one_prices_py_publishes(self):
        """Only the ONE known value is translated; anything else travels verbatim.

        The first cut mapped a third value (`as_traded`) that `VENDOR_ADJUSTMENT` does not
        contain — a branch that could never fire, which is the vacuous direction.
        """
        self.assertEqual(set(prices.VENDOR_ADJUSTMENT.values()),
                         {"auto_adjusted", "unverified"})
        body = code_only(function_source(
            os.path.join(REPO, "valuation", "data", "yahoo.py"), "fetch"))
        self.assertNotIn("as_traded", body)

    def test_auto_adjust_is_STATED_and_not_inherited(self):
        """`prices.py`'s own reason, applied here: *"inheriting a vendor library's default is
        how a convention silently changes between releases."*

        The VALUE is deliberately unchanged — `True` is what the inherited default already gave
        at yfinance 1.6.0 — so no published drawdown moves. What changes is that a release can
        no longer move it without a diff.
        """
        body = function_source(os.path.join(REPO, "valuation", "data", "yahoo.py"), "fetch")
        self.assertIn('t.history(period="1y", interval="1d", auto_adjust=True)', body)


class TheWindowIsFiftyTwoWeeks(unittest.TestCase):

    def test_a_spike_older_than_the_window_is_not_the_52_week_high(self):
        """The fallback pulls 400 days so one short frame cannot miss the window; the CLAIM is
        52 weeks, so the last 252 sessions are what the maximum is taken over."""
        with _Patched(labelled(spike=9999.0)):
            cd = yahoo.fetch("KO")
        self.assertEqual(cd.price_52w_high, 123.45)

    def test_a_shorter_frame_still_yields_a_high(self):
        """A name with 90 sessions of history has a 52-week high; it is just a shorter window.
        Requiring 252 would refuse every recent listing."""
        with _Patched(labelled(n=90)):
            cd = yahoo.fetch("KO")
        self.assertEqual(cd.price_52w_high, 123.45)


class TheScreenCountsThePrimarysPulse(unittest.TestCase):

    OK_SUBS = {"quality": 80.0, "health": 80.0, "growth": 80.0}

    def row(self, t, prox=0.70):
        return {"ticker": t, "name": t, "price": 50.0, "market_cap": 5e9, "hot_score": 60,
                "rank": 1, "z_quality": 0.5,
                "extra": ({} if prox is None else {"high_prox": prox})}

    def meas(self, high=70.0, source="yahoo", basis="adjusted", reason=None, dd=0.30):
        return {"drawdown": dd, "price": 50.0, "high_52w": high, "subs": dict(self.OK_SUBS),
                "cash_burning": False, "score": 70, "confidence": "high", "fair_value": 80.0,
                "upside": 0.6, "fair_value_low": 60.0, "fair_value_high": 100.0,
                "fair_value_withheld_reason": None, "regime": "mature",
                "health_not_scored": False, "high_source": source, "high_basis": basis,
                "high_reason": reason,
                "checks": {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                           "terminal_share": dip.PASS}}

    def run_screen(self, cases, min_drawdown=0.20):
        rows = [self.row(t, p) for t, p, _m in cases]
        by_t = {t: m for t, _p, m in cases}
        return dip.screen(rows, min_drawdown=min_drawdown,
                          measure=lambda r: by_t.get(r["ticker"]), shortlist=0)

    def test_a_live_primary_is_counted_with_its_source_and_basis(self):
        out = self.run_screen([("A", 0.70, self.meas()), ("B", 0.70, self.meas())])
        self.assertEqual(out["n_high_from_engine"], 2)
        self.assertEqual(out["high_by_source"], {"yahoo": 2})
        self.assertEqual(out["high_by_basis"], {"adjusted": 2})
        self.assertEqual(out["high_reasons"], {})

    def test_the_2026_10_07_STATE_reports_ZERO_AND_THE_REASON(self):
        """The screen still serves rows off item 36's fallback, and now says the primary died."""
        out = self.run_screen([
            ("A", 0.70, self.meas(high=None, source=None, basis=None,
                                  reason="HTTPError: HTTP Error 401: Invalid Crumb", dd=None)),
            ("B", 0.70, self.meas(high=None, source=None, basis=None,
                                  reason="HTTPError: HTTP Error 401: Invalid Crumb", dd=None))])
        self.assertEqual(out["n_high_from_engine"], 0)
        self.assertEqual(out["high_by_source"], {})
        self.assertIn("HTTPError: HTTP Error 401: Invalid Crumb", out["high_reasons"])
        self.assertEqual(out["high_reasons"]["HTTPError: HTTP Error 401: Invalid Crumb"], 2)
        # AND THE ROWS STILL COME, from the scan ratio -- which is the whole hazard.
        self.assertTrue(out["rows"], "item 36's fallback should still be serving rows")
        self.assertEqual(out["n_drawdown_from_scan"], len(out["rows"]))

    def test_a_name_dropped_for_depth_still_counts_toward_the_pulse(self):
        """Counted BEFORE any `continue`, or the census becomes a property of what survived the
        screen rather than of the feed."""
        out = self.run_screen([("DEEP", 0.70, self.meas()),
                               ("SHALLOW", 0.83, self.meas(dd=0.17))])
        self.assertEqual(len(out["rows"]), 1)
        self.assertEqual(out["rejected_shallow"], 1)
        self.assertEqual(out["n_high_from_engine"], 2)

    def test_the_reason_census_is_bounded(self):
        """It rides in the ingest payload and on every request; an unbounded dict of 218
        distinct reasons is how a disclosure becomes a denial of service."""
        cases = [("T%03d" % i, 0.70,
                  self.meas(high=None, source=None, basis=None,
                            reason="reason number %d" % i, dd=None))
                 for i in range(12)]
        out = self.run_screen(cases)
        self.assertLessEqual(len(out["high_reasons"]), 5)

    def test_the_precompute_shape_carries_the_pulse(self):
        """The CACHE has to say it too, not only the request that reads it: the nightly scan is
        where the figure is observable and the ingest payload is what travels."""
        rows = [self.row("A"), self.row("B")]
        got = {"A": self.meas(), "B": self.meas(high=None, source=None, basis=None,
                                                reason="401 Invalid Crumb", dd=None)}
        cache = dip.precompute(rows, lambda t: None, min_drawdown=0.10,
                               scan_date="2026-10-08", workers=1)
        self.assertIn("with_high", cache["shape"])

        # Now with real measurements, through the documented seam.
        import valuation.web.dip as D
        real = D.measurement_from
        D.measurement_from = lambda res: got.get(res)
        try:
            cache = D.precompute(rows, lambda t: t, min_drawdown=0.10,
                                 scan_date="2026-10-08", workers=1)
        finally:
            D.measurement_from = real
        self.assertEqual(cache["shape"]["with_high"], 1)
        self.assertEqual(cache["shape"]["high_by_source"], {"yahoo": 1})
        self.assertIn("401 Invalid Crumb", cache["shape"]["high_reasons"])


class TheScanAndTheCheckSayIt(unittest.TestCase):

    def test_the_scan_prints_the_engine_high_count_unconditionally(self):
        """A line that appears only when something is wrong cannot establish what normal is."""
        body = function_source(os.path.join(REPO, "scripts", "ci_scan.py"), "run_hot")
        self.assertIn("52-week high FROM THE ENGINE", body)
        # AGAINST THE FUNCTION-BOUNDED SOURCE, not `code_only`: the needle IS a string literal
        # (a dict key), and the stripper removes string literals -- so the first cut of this
        # assertion could never have passed. Bounding by the function is what stops the
        # character-window defect; the stripper is for needles that could appear in prose, and
        # an exact call expression cannot.
        self.assertIn('sh.get("with_high")', body)
        # ...and it is PRINTED, not merely present. MISSED BY MUTATION UNTIL THIS LINE:
        # replacing `print(` with `_unused = (` left both assertions above true, because they
        # test that a string EXISTS rather than that anything does something with it. The
        # exact call shape is the property.
        self.assertIn('print("    52-week high FROM THE ENGINE', body)
        # ...and on the ordinary path, not only inside the alarm branch.
        head = body[:body.index("if _wh == 0")]
        self.assertIn('print("    52-week high FROM THE ENGINE', head)

    def test_the_live_check_fails_on_zero_while_qualifying(self):
        src = io.open(os.path.join(REPO, "scripts", "live_check.py"),
                      encoding="utf-8").read()
        body = function_source(os.path.join(REPO, "scripts", "live_check.py"), "check_dip")
        self.assertIn('d.get("n_high_from_engine")', body)
        # The condition is ZERO-WHILE-QUALIFYING, not a fraction: coverage varies with the
        # vendor's mood daily (114 of 236 one run, 0 the next), so a fractional bar would be a
        # bar on the weather and would be switched off inside a week. Asserted over `code_only`
        # because this needle is CODE, so prose quoting the rule cannot satisfy it.
        self.assertIn("qual and not n_high", code_only(body))
        self.assertIn("52-week-high source", src)


class TheStripperItselfIsPinned(unittest.TestCase):
    """`code_only` is shared machinery and this item changed it, so its contract is pinned.

    `tests/source_bounds.py` has no suite of its own; these three cases are the ones item 39
    paid for. The others (`function_source`, `js_function_source`) are exercised by every
    caller, but the token SEPARATOR is the sort of property nobody notices until a guard reads
    the wrong thing.
    """

    SRC = "\n".join(['def f(x):',
                     '    # a comment mentioning secret',
                     '    key = "secret"',
                     '    if x and not key:',
                     '        return 1',
                     ''])

    def test_prose_and_literals_are_removed(self):
        code = code_only(self.SRC)
        self.assertNotIn("secret", code,
                         "a comment or a literal reached a guard that bans a token")

    def test_the_code_survives_so_a_ban_cannot_pass_by_seeing_nothing(self):
        code = code_only(self.SRC)
        self.assertIn("def", code)
        self.assertIn("key", code)

    def test_tokens_are_SEPARATED_and_not_fused(self):
        """THE DEFECT ITEM 39 HIT, in both directions.

        Joined with nothing, `if x and not key` became `ifxandnotkey`: a multi-token needle
        could never match (the assertion that caught it), and adjacent tokens FUSE, so a needle
        could match text that does not exist -- a guard passing on the wrong evidence.
        """
        code = code_only(self.SRC)
        self.assertIn("x and not key", code)
        self.assertNotIn("xandnotkey", code)

    def test_unparseable_input_RAISES_rather_than_returning_the_prose(self):
        with self.assertRaises(AssertionError):
            code_only("def f(:\n  this is not python\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
