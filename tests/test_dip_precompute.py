# -*- coding: utf-8 -*-
"""ITEM 35(a) — the dip screen serves a NIGHTLY PRECOMPUTE instead of a per-request budget.

THE DEFECT, AND WHY RAISING THE BUDGET WAS NOT THE FIX. `/api/dip` valued `DEFAULT_SHORTLIST`
names per request out of ~220 qualifying -- about 5% of what it was eligible to serve -- and the
page reported the result as though it had looked at the market. Raising the per-request budget
was tried and MEASURED to buy nothing: 12 -> 18 valued the same 10 rows across four thresholds,
at 18-28s of cold latency, because the cost is per request and the cap has to stay.

Precomputing moves the cost to the scan job, which took 21m21s of a 90-minute budget on
2026-10-06, and lets a request serve the WHOLE qualifying set from a dict.

THE FOUR PROPERTIES THAT MAKE IT SAFE, each with a way it goes wrong:

  * **THE PRECOMPUTE ASKS `screen` WHICH NAMES IT WOULD VALUE** rather than re-deriving the
    rule. A second copy would drift and the drift would be INVISIBLE -- the cache would miss
    names, and a miss is reported as `n_unmeasured`, which reads as a data gap.
  * **THE FLOOR'S QUALIFYING SET IS A SUPERSET OF EVERY HIGHER THRESHOLD'S.** One pass serves
    the whole slider; if that failed, the deeper settings would quietly lose names.
  * **A CACHE FROM ANOTHER SCAN IS REFUSED.** Serving it would return measurements at a
    different date's prices with nothing in the payload saying so.
  * **A CACHE MISS IS NEVER A LIVE VALUATION.** A request that quietly values a miss can spend
    an unbounded budget on a cold cache, which is the thing this path removes.

    python tests/test_dip_precompute.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.web import dip                                            # noqa: E402


# --------------------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------------------- #

def _row(ticker, high_prox, z=1.0):
    """`extra.high_prox` is the RAW ratio `cheap_drawdown` reads; `extra.numbers.high_prox` is
    the within-date z-score and is an ordering key only. Writing the fixture against the
    second gives `preselect_available` False and tests the fallback path by accident."""
    return {"ticker": ticker, "name": ticker, "sector": "Tech", "price": 10.0,
            "market_cap": 5e9, "hot_score": 50, "rank": 1,
            "z_quality": z, "z_growth": z,
            "extra": {"high_prox": high_prox, "numbers": {"high_prox": -z}}}


def _healthy(dd):
    return {"drawdown": dd, "price": 10.0, "high_52w": 10.0 / max(1e-9, 1.0 - dd),
            "subs": {"health": 80, "quality": 80, "growth": 80},
            "score": 70, "confidence": "medium", "fair_value": 20.0, "upside": 1.0,
            "fair_value_low": 15.0, "fair_value_high": 25.0,
            "fair_value_withheld_reason": None,
            "checks": {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                       "terminal_share": dip.PASS}}


class _Result:
    """The shape `measurement_from` reads, so `precompute` is driven end to end."""

    class _C:
        price = 10.0
        price_52w_high = 20.0

    class _S:
        subscores = {"health": 80, "quality": 80, "growth": 80}
        score = 70
        confidence = "medium"

    class _B:
        tv_share = 0.5
        confidence = "medium"
        value = 20.0
        withheld_value = None
        growth_led = False

    def __init__(self):
        self.company = self._C()
        self.score = self._S()
        self.fair_value_blend = self._B()
        self.base_fair_value = 20.0
        self.fair_value_scenarios = {"bear": 15.0, "bull": 25.0}
        self.classification = type("K", (), {"is_cash_burning": False})()
        self.wacc = type("W", (), {"beta_provenance": type(
            "P", (), {"substituted": False})()})()


# --------------------------------------------------------------------------------------- #
# 1. the precompute asks the screen, and does not re-derive the rule
# --------------------------------------------------------------------------------------- #

class TheSelectionHasOneDefinition(unittest.TestCase):

    def setUp(self):
        # Depths 0.40, 0.25, 0.12 and 0.02 from the ratio; the last is below the floor.
        self.rows = [_row("DEEP", 0.60), _row("MID", 0.75), _row("SHALLOW", 0.88),
                     _row("FLAT", 0.98)]

    def test_the_dry_run_names_exactly_what_the_screen_would_value(self):
        want = dip.qualifying_tickers(self.rows, min_drawdown=0.10)
        got = dip.screen(self.rows, min_drawdown=0.10, measure=lambda _r: None,
                         shortlist=0)["measured_tickers"]
        self.assertEqual(want, got)

    def test_the_dry_run_costs_nothing(self):
        """It must not reach a company: `measure` is the only door to one and it returns None."""
        calls = []

        def spy(t):
            calls.append(t)
            return _Result()

        dip.qualifying_tickers(self.rows, min_drawdown=0.10)
        self.assertEqual(calls, [])
        # And the real precompute DOES reach one, so the test above is not vacuous.
        dip.precompute(self.rows, spy, min_drawdown=0.10, workers=1)
        self.assertTrue(calls)

    def test_the_floor_set_is_a_SUPERSET_of_every_higher_threshold(self):
        """One pass at the floor serves the whole slider, or the deep settings lose names."""
        base = set(dip.qualifying_tickers(self.rows, min_drawdown=dip.MIN_DRAWDOWN_FLOOR))
        for th in (0.15, 0.20, 0.25, 0.30, 0.35, dip.MIN_DRAWDOWN_CEIL):
            higher = set(dip.qualifying_tickers(self.rows, min_drawdown=th))
            self.assertTrue(higher <= base,
                            "%.2f qualifies names the floor does not: %s"
                            % (th, sorted(higher - base)))

    def test_a_name_below_the_floor_minus_slack_is_not_precomputed(self):
        """Otherwise the nightly pass pays for names that can never appear."""
        got = dip.qualifying_tickers(self.rows, min_drawdown=0.10)
        self.assertNotIn("FLAT", got)
        self.assertIn("DEEP", got)


# --------------------------------------------------------------------------------------- #
# 2. the cache
# --------------------------------------------------------------------------------------- #

class ThePrecomputedCache(unittest.TestCase):

    def setUp(self):
        self.rows = [_row("DEEP", 0.60), _row("MID", 0.75)]

    def test_it_values_every_qualifier_and_reports_its_shape(self):
        c = dip.precompute(self.rows, lambda t: _Result(), min_drawdown=0.10, workers=1,
                           scan_date="2026-10-07")
        self.assertEqual(c["scan_date"], "2026-10-07")
        self.assertEqual(c["min_drawdown"], 0.10)
        self.assertEqual(set(c["measurements"]), {"DEEP", "MID"})
        self.assertEqual(c["shape"]["qualifying"], 2)
        self.assertEqual(c["shape"]["valued"], 2)
        self.assertEqual(c["shape"]["failed"], 0)
        self.assertEqual(c["shape"]["with_drawdown"], 2)
        self.assertEqual(c["shape"]["no_drawdown"], 0)
        self.assertIn("seconds", c["shape"])

    def test_valued_is_NOT_the_same_as_usable_and_both_are_reported(self):
        """`measurement_from` returns a dict for any real result, with `drawdown: None` when the
        company has no 52-week high -- and `screen` counts that as `n_unmeasured`, because a name
        whose drawdown nobody can compute is not a name in a drawdown.

        Measured live on 2026-10-06: 210 of 210 valued and **90 of those carry no drawdown**.
        Reporting only `valued` made "210 valued" read as 210 usable, which is the COVERAGE
        RULE's own shape -- a number with no denominator beside it.
        """
        class _NoHigh(_Result):
            def __init__(self):
                super().__init__()
                self.company.price_52w_high = None

        def mixed(t):
            return _Result() if t == "DEEP" else _NoHigh()

        c = dip.precompute(self.rows, mixed, min_drawdown=0.10, workers=1)
        self.assertEqual(c["shape"]["valued"], 2, "both produced a measurement")
        self.assertEqual(c["shape"]["failed"], 0, "neither FAILED to value")
        self.assertEqual(c["shape"]["with_drawdown"], 1)
        self.assertEqual(c["shape"]["no_drawdown"], 1)

    def test_a_name_that_will_not_value_is_COUNTED_not_dropped_silently(self):
        def flaky(t):
            if t == "MID":
                raise RuntimeError("upstream")
            return _Result()

        c = dip.precompute(self.rows, flaky, min_drawdown=0.10, workers=1)
        self.assertEqual(c["shape"]["valued"], 1)
        self.assertEqual(c["shape"]["failed"], 1)
        self.assertIn("MID", c["shape"]["failed_tickers"])

    def test_a_WIRING_error_is_not_swallowed(self):
        """`engine_measure`'s own rule: 229 names once raised the identical wiring error and
        each was counted as unmeasured, which read as a data gap rather than a bug."""
        def broken(t):
            raise dip.DipWiringError("handed back a cache entry")

        with self.assertRaises(dip.DipWiringError):
            dip.precompute(self.rows, broken, min_drawdown=0.10, workers=1)

    def test_the_threaded_and_serial_paths_agree(self):
        a = dip.precompute(self.rows, lambda t: _Result(), min_drawdown=0.10, workers=1)
        b = dip.precompute(self.rows, lambda t: _Result(), min_drawdown=0.10, workers=4)
        self.assertEqual(set(a["measurements"]), set(b["measurements"]))


class TheCacheIsCheckedBeforeItIsServed(unittest.TestCase):

    def test_a_cache_from_another_scan_is_refused(self):
        c = {"scan_date": "2026-10-06", "measurements": {"A": {}}}
        self.assertFalse(dip.usable_cache(c, "2026-10-07"))
        self.assertTrue(dip.usable_cache(c, "2026-10-06"))

    def test_an_empty_cache_is_refused(self):
        """Serving one reports every name as unmeasured, which looks identical to a screen that
        could not measure anything -- the sentence item 19 exists to stop."""
        self.assertFalse(dip.usable_cache({"scan_date": "d", "measurements": {}}, "d"))

    def test_a_non_dict_is_refused_rather_than_raising(self):
        for junk in (None, [], "", 0, "a string"):
            self.assertFalse(dip.usable_cache(junk, "d"))

    def test_a_cache_MISS_is_never_a_live_valuation(self):
        """A request that values a miss can spend an unbounded budget on a cold cache."""
        m = dip.cached_measure({"measurements": {"DEEP": _healthy(0.4)}})
        self.assertIsNotNone(m({"ticker": "DEEP"}))
        self.assertIsNone(m({"ticker": "NOTINCACHE"}))

    def test_the_meta_key_has_one_definition(self):
        self.assertEqual(dip.DIP_CACHE_META_KEY, "dip_cache")


# --------------------------------------------------------------------------------------- #
# 3. serving it: nothing capped, every qualifier measured
# --------------------------------------------------------------------------------------- #

class _Store:
    def __init__(self, rows, scan_date="2026-10-07", meta=None):
        self._rows = rows
        self._d = scan_date
        self._meta = dict(meta or {})

    def latest_scan_date(self):
        return self._d

    def load_snapshot(self, scan_date=None, top=None):
        return [dict(r) for r in self._rows]

    def get_meta(self, key, default=None):
        return self._meta.get(key, default)


class ServingFromTheCache(unittest.TestCase):

    def setUp(self):
        self.rows = [_row(t, hp) for t, hp in
                     (("A", 0.50), ("B", 0.60), ("C", 0.70), ("D", 0.80), ("E", 0.85))]
        self.cache = {"scan_date": "2026-10-07", "min_drawdown": 0.10,
                      "measurements": {t: _healthy(round(1.0 - hp, 4)) for t, hp in
                                       (("A", 0.50), ("B", 0.60), ("C", 0.70),
                                        ("D", 0.80), ("E", 0.85))},
                      "shape": {"qualifying": 5, "valued": 5}}

    def _run(self, min_dd=0.10, meta=None):
        st = _Store(self.rows, meta=meta if meta is not None
                    else {dip.DIP_CACHE_META_KEY: self.cache})

        def _boom(t):
            raise AssertionError("a cached request must not value anything: %s" % t)

        return dip.screen_snapshot(st, _boom, min_drawdown=min_dd)

    def test_nothing_is_capped_and_the_source_says_precomputed(self):
        out = self._run()
        self.assertEqual(out["capped"], 0)
        self.assertEqual(out["dip_source"], "precomputed")

    def test_every_qualifying_name_is_measured(self):
        out = self._run()
        self.assertEqual(out["n_measured"], out["n_qualified_on_depth"])

    def test_the_identity_the_live_check_asserts_holds(self):
        """n_qualified == rows + unmeasured + health + shallow, which is what item 35 asks the
        live check to assert. Pinned here too, so a change to `screen`'s accounting breaks a
        unit test rather than only the daily live run."""
        for th in (0.10, 0.20, 0.30, 0.40):
            out = self._run(th)
            total = (len(out["rows"]) + out["n_unmeasured"] + out["rejected_health"]
                     + out["rejected_shallow"])
            self.assertEqual(total, out["n_qualified_on_depth"],
                             "threshold %.2f: %s" % (th, out))

    def test_a_cached_request_values_NOTHING(self):
        """`_boom` raises if `get_result` is called at all, so this is the whole claim."""
        self._run()            # would raise

    def test_no_cache_falls_back_to_the_bounded_live_path_and_SAYS_SO(self):
        st = _Store(self.rows, meta={})
        out = dip.screen_snapshot(st, lambda t: _Result(), min_drawdown=0.10)
        self.assertEqual(out["dip_source"], "live")
        self.assertIn("no precomputed cache stored", out["dip_cache_absent_reason"])

    def test_a_stale_cache_falls_back_AND_NAMES_THE_SCAN_IT_DESCRIBES(self):
        stale = dict(self.cache, scan_date="2026-10-01")
        st = _Store(self.rows, meta={dip.DIP_CACHE_META_KEY: stale})
        out = dip.screen_snapshot(st, lambda t: _Result(), min_drawdown=0.10)
        self.assertEqual(out["dip_source"], "live")
        self.assertIn("2026-10-01", out["dip_cache_absent_reason"])

    def test_every_caller_gets_the_cache_not_just_the_route(self):
        """`screen_snapshot` has four callers -- the page, the Discord digest, the SaaS worker
        and a fleet book. A digest pushing the bounded 12-name screen while the page served 220
        is the Index-versus-hot-list disagreement again, outbound."""
        import inspect
        src = inspect.getsource(dip.screen_snapshot)
        self.assertIn("stored_cache(store)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
