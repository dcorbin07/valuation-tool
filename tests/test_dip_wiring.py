# -*- coding: utf-8 -*-
"""ITEM 19 — the Dip Detector measured ZERO names from the day it shipped, and 46 tests passed.

THE DEFECT
----------
`dip.engine_measure` calls `measurement_from(get_result(ticker))`, and every caller passes
`web/app._get_or_compute`, which returns a **`resultcache.Entry`** — its own docstring says
*"Returns the cache entry rather than the result, because the caller has to stamp the document
with when the numbers were made"* — and has done since `42597e2` on 2026-08-06, **a week before
the Dip Detector was built on 2026-08-13**. So `measurement_from` did
`getattr(result, "company")` on an `Entry`, got `None`, computed no drawdown, and counted every
name unmeasured.

Measured on the service 2026-10-03: `n_universe` 1489, `n_eligible` 241, `n_measured` 12,
`n_unmeasured` 12 — **every examined name unmeasured** — while the page said *"No name cleared a
20% fall"*. `POST /api/value` returns NKE at 33.87 against a 52-week high of 69.63, so the data
was present throughout.

WHY 46 TESTS PASSED, WHICH IS THE PART WORTH CARRYING
-----------------------------------------------------
`measurement_from`'s docstring states the design: *"Pure — no network, no cache — so the mapping
from a valuation to a screened row is testable against a stub result, which is where the
interesting mistakes live."* The stub was result-SHAPED, so the MAPPING was tested thoroughly
and the WIRING was never tested at all. **A pure function tested only against a hand-built input
cannot catch a caller passing the wrong type** — and the whole point of injecting `get_result`
was to make the path testable with a dict, which is precisely what made the real path untested.

So this suite drives `screen_snapshot` through the **REAL `_get_or_compute`**, with only
`value_ticker` stubbed. Nothing between the route and the measurement is replaced.

THE SECOND DEFECT THE SAME WRAPPER CAUSED
-----------------------------------------
`measurement_from` also calls `withhold.is_withheld_result(result)`. On an `Entry` that reads
`getattr(entry, "fair_value_blend", None)` → `None` → returns **False**, so every name was
treated as NOT withheld. It had no observable effect ONLY because nothing was ever measured —
the two defects masked each other, and fixing the first alone would have made the second live.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.web import dip as DIP                          # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: NKE as the service reports it, so the number this suite asserts is the one Don saw.
NKE_PRICE, NKE_HIGH = 33.87, 69.63
NKE_DRAWDOWN = 1.0 - NKE_PRICE / NKE_HIGH          # 0.5136


class _CD(object):
    def __init__(self, price, high):
        self.price = price
        self.price_52w_high = high
        self.ticker = "X"
        self.name = "X Co"
        self.sector = "Tech"


class _Blend(object):
    valuable = True


class _Score(object):
    """Subscores clearing `dip.HEALTH_FLOORS` (quality / health / growth, each >= 66), so a
    measured row actually reaches the result rather than being filtered as unhealthy. Taken
    from the module's own constant rather than typed, or the fixture drifts when it moves."""

    def __init__(self):
        from valuation.web.dip import HEALTH_FLOORS
        self.subscores = {k: float(v) + 10.0 for k, v in HEALTH_FLOORS.items()}


class _Result(object):
    """The minimum a `ValuationResult` needs to be measurable here."""

    def __init__(self, price=NKE_PRICE, high=NKE_HIGH):
        self.company = _CD(price, high)
        self.score = _Score()
        self.base_fair_value = price * 1.4
        self.fair_value_blend = _Blend()
        self.fair_value_scenarios = {"bear": price * 1.1, "bull": price * 1.8}
        self.warnings = []
        self.ai = None


class _Store(object):
    """A snapshot store with enough rows that the pre-filter leaves work to do."""

    def __init__(self, n=24):
        self._rows = [{"ticker": "T%02d" % i, "name": "Name %02d" % i, "sector": "Tech",
                       "price": NKE_PRICE, "market_cap": 2.0e10 + i * 1e9,
                       "hot_score": 70.0, "score": 70.0, "rank": i + 1,
                       "price_52w_high": NKE_HIGH}
                      for i in range(n)]

    def latest_scan_date(self):
        return "2026-10-02"

    def load_snapshot(self, date):
        return [dict(r) for r in self._rows]


def _through_the_real_wiring(store=None, min_drawdown=0.10, shortlist=12):
    """`screen_snapshot` driven through the REAL `_get_or_compute`. Only `value_ticker` is
    stubbed, so the Entry wrapper is in the path exactly as it is in production."""
    from valuation.web import app as W
    real = W.value_ticker
    W.value_ticker = lambda t, cfg, overrides=None, peers=None: _Result()
    try:
        # A fresh cache, so a previous test's entries cannot change what this one exercises.
        W._RESULTS.clear() if hasattr(W._RESULTS, "clear") else None
        return DIP.screen_snapshot(store or _Store(), W._get_or_compute,
                                   min_drawdown=min_drawdown, shortlist=shortlist)
    finally:
        W.value_ticker = real


class TheRealWiringMeasuresSomething(unittest.TestCase):
    """THE TEST THAT WOULD HAVE CAUGHT IT. It asserts the two things the service contradicted."""

    def test_it_measures_more_than_zero_names(self):
        out = _through_the_real_wiring()
        self.assertGreater(out.get("n_measured") or 0, 0,
                           "the screen examined nothing: %r"
                           % {k: out.get(k) for k in ("n_universe", "n_eligible", "n_measured")})

    def test_NOT_every_examined_name_is_unmeasured(self):
        """The service's exact signature: n_measured 12, n_unmeasured 12."""
        out = _through_the_real_wiring()
        self.assertLess(out.get("n_unmeasured") or 0, out.get("n_measured") or 0,
                        "every examined name failed to measure, which is the defect's "
                        "signature: measured=%r unmeasured=%r"
                        % (out.get("n_measured"), out.get("n_unmeasured")))

    def test_every_measured_row_carries_a_drawdown(self):
        out = _through_the_real_wiring()
        rows = out.get("rows") or []
        self.assertTrue(rows, "no row survived the screen")
        for r in rows:
            self.assertIsNotNone(r.get("drawdown"),
                                 "%s is in the result with no drawdown" % r.get("ticker"))

    def test_the_drawdown_is_the_RIGHT_number(self):
        """Not merely present. Against the service's own NKE figures."""
        rows = _through_the_real_wiring().get("rows") or []
        self.assertTrue(rows)
        self.assertAlmostEqual(rows[0]["drawdown"], NKE_DRAWDOWN, places=6)

    def test_it_holds_at_every_threshold_the_item_asks_about(self):
        for md in (0.10, 0.20, 0.30):
            out = _through_the_real_wiring(min_drawdown=md)
            self.assertGreater(out.get("n_measured") or 0, 0, "nothing measured at %s" % md)
            self.assertTrue(out.get("rows"),
                            "a 51%% drawdown did not clear a %s bar" % md)


class TheUnwrapperIsTheOnePlace(unittest.TestCase):
    def test_a_cache_entry_measures_identically_to_a_bare_result(self):
        from valuation.web import resultcache
        r = _Result()
        direct = DIP.measurement_from(r)
        entry = resultcache.Entry(result=r, computed_at=0.0, key="k")
        wrapped = DIP.measurement_from(entry)
        self.assertIsNotNone(direct)
        self.assertEqual(direct.get("drawdown"), wrapped.get("drawdown"))
        self.assertEqual(direct.get("price"), wrapped.get("price"))

    def test_a_result_is_preferred_when_an_object_has_BOTH_attributes(self):
        """Order matters: `.company` is checked first, so a result that happens to carry a
        `.result` attribute is still treated as a result."""
        r = _Result()
        r.result = "not a result"
        self.assertIs(DIP.unwrap_result(r), r)

    def test_an_object_with_neither_is_REFUSED_rather_than_measured_as_empty(self):
        """Returning None here is what made the defect invisible: it is indistinguishable
        from "this name has no data"."""
        with self.assertRaises(DIP.DipWiringError):
            DIP.unwrap_result(object())

    def test_an_entry_holding_a_non_result_is_refused_rather_than_unwrapped_twice(self):
        class Wrap(object):
            def __init__(self, inner):
                self.result = inner
        with self.assertRaises(DIP.DipWiringError):
            DIP.unwrap_result(Wrap(Wrap(_Result())))

    def test_None_is_still_None_and_not_an_error(self):
        """A name with no result is a legitimate state and must stay cheap."""
        self.assertIsNone(DIP.unwrap_result(None))
        self.assertIsNone(DIP.measurement_from(None))


class AWiringErrorIsNotSWALLOWED(unittest.TestCase):
    """The second half of why it was silent. `engine_measure`'s `except Exception` is correct
    for a per-name failure and is exactly how 229 identical wiring errors read as a data gap."""

    def test_a_wiring_error_propagates(self):
        m = DIP.engine_measure(lambda t: object(), budget=5)
        with self.assertRaises(DIP.DipWiringError):
            m({"ticker": "AAA"})

    def test_a_PER_NAME_failure_is_still_tolerated(self):
        """The positive control: a guard that refuses everything is not a guard. One name
        raising an ordinary error must still become an unmeasured row."""
        def boom(t):
            raise ValueError("this one name will not value")
        m = DIP.engine_measure(boom, budget=5)
        self.assertIsNone(m({"ticker": "AAA"}))


class TheWithholdingWasAlsoBypassed(unittest.TestCase):
    """The second defect from the same wrapper, now fixed by the same unwrap."""

    def test_a_withheld_result_is_recognised_through_the_entry(self):
        from valuation.web import resultcache
        r = _Result()
        r.fair_value_blend = type("B", (), {"valuable": False})()
        r.base_fair_value = None
        out = DIP.measurement_from(resultcache.Entry(result=r, computed_at=0.0, key="k"))
        self.assertIsNotNone(out)
        self.assertIsNone(out.get("fair_value"),
                          "a withheld valuation was published through the cache entry")

    def test_the_bypass_really_was_a_bypass(self):
        """The positive control, so this class is not passing for an unrelated reason: asked
        of the ENTRY directly, the predicate still says 'not withheld'."""
        from valuation.web import withhold, resultcache
        r = _Result()
        r.fair_value_blend = type("B", (), {"valuable": False})()
        r.base_fair_value = None
        self.assertTrue(withhold.is_withheld_result(r))
        self.assertFalse(withhold.is_withheld_result(
            resultcache.Entry(result=r, computed_at=0.0, key="k")))


class F11NeverRecordsAFabricatedZeroAgain(unittest.TestCase):
    """THE DAMAGE, AND ITS REMEDY IN THE SERIES' OWN VOCABULARY.

    Audit #5's `H2` established that for `dip_rejects`, `[]` means *the screen ran and rejected
    nobody* and `None` means *no screen was consulted* -- and `f11_live_rejects`'s own docstring
    warns that returning `[]` wrongly "would put a fabricated zero back into the one series
    that was just repaired for exactly that".

    H2 guarded the UNREACHABLE STORE. It did not guard a screen that runs, reaches every name
    and measures none of them -- which is what happened from 2026-08-13, so `[]` was recorded
    as an observation every cycle into the series F-11's hypothesis reads for FIRST appearances.
    `f11_first_appearances` cannot tell a day nobody was rejected from a day nobody was looked
    at.
    """

    @staticmethod
    def _with_payload(payload):
        import valuation.web.dip as D
        from valuation.edge import fleet_books as FB
        real = D.screen_snapshot
        D.screen_snapshot = lambda *a, **k: payload
        try:
            return FB.f11_live_rejects()
        finally:
            D.screen_snapshot = real

    def test_nothing_measured_returns_None_and_not_an_empty_list(self):
        self.assertIsNone(self._with_payload(
            {"n_measured": 0, "n_unmeasured": 0, "rows": [], "health_rejects": []}))

    def test_EVERY_examined_name_failing_returns_None(self):
        """The live state: n_measured 12, n_unmeasured 12. A guard on zero alone misses it."""
        self.assertIsNone(self._with_payload(
            {"n_measured": 12, "n_unmeasured": 12, "rows": [], "health_rejects": []}))

    def test_a_GENUINE_empty_reject_population_still_returns_a_list(self):
        """The positive control, and it is the one that matters: a screen that really did
        measure names and reject nobody must still record `[]`. A guard that returned `None`
        for both would destroy the distinction it exists to protect."""
        got = self._with_payload({"n_measured": 12, "n_unmeasured": 0, "rows": [],
                                  "health_rejects": []})
        self.assertIsNotNone(got, "a real observation of zero rejects was discarded")
        self.assertEqual(list(got), [])

    def test_an_absent_scan_still_returns_None(self):
        self.assertIsNone(self._with_payload({"empty": True, "rows": []}))

    def test_the_ticker_form_propagates_None(self):
        from valuation.edge import fleet_books as FB
        real = FB.f11_live_rejects
        FB.f11_live_rejects = lambda: None
        try:
            self.assertIsNone(FB.f11_live_rejects_tickers())
        finally:
            FB.f11_live_rejects = real

    def test_first_appearances_already_skips_invalidated_rows(self):
        """The remedy for the rows ALREADY recorded is the series' own `invalid` flag, which
        `f11_first_appearances` honours -- so marking the span neutralises it WITHOUT deleting
        a record. Asserted here because the repair on the service depends on it."""
        from valuation.edge import fleet_books as FB
        hist = [{"date": "2026-09-01", "payload": ["AAA"], "invalid": True},
                {"date": "2026-09-02", "payload": ["BBB"], "invalid": False}]
        # A Fri Oct  2 22:39:50 EDT 2026, not a string:  reads , so a string raises rather
        # than being parsed. Found by this test erroring on its own fixture.
        import datetime as _d
        got = FB.f11_first_appearances(hist, _d.date(2026, 9, 2), sessions=5)
        self.assertNotIn("AAA", got, "an invalidated row dated a first appearance")
        self.assertIn("BBB", got)


class TheEmptyScreenNeverClaimsNothingQualified(unittest.TestCase):
    """The page said "No name cleared a 20% fall" while nothing had been measured. That is a
    claim about the market standing in for a claim about the wiring, and the two are
    opposites a reader cannot tell apart."""

    def _renderer(self):
        import re
        src = open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                   encoding="utf-8").read()
        i = src.index("No name cleared a")
        body = src[max(0, i - 2600):i + 3000]
        body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
        return "\n".join(re.sub(r"//.*$", "", ln) for ln in body.splitlines())

    def test_the_branch_distinguishes_nothing_measured_from_nothing_qualified(self):
        b = self._renderer()
        self.assertIn("n_measured", b)
        self.assertIn("could not measure anything", b)
        self.assertIn("not saying no name qualified", b)

    def test_the_branch_is_REACHABLE_and_not_merely_present(self):
        """FOUND BY MUTATION. The assertions above all pass against `if (false) {` -- the
        strings stay in the source while every request falls through to the sentence they
        exist to replace. That is the structural-guard family this session has now met three
        times: assert the CONDITION, not the presence of the code it guards."""
        import re
        b = self._renderer()
        # Anchored on the branch's OWN copy and searched BACKWARDS, because several `if`s in
        # this function write `dipResults` and the first cut matched the `d.empty` one -- which
        # failed against a correct tree and proved the regex was pointing at the wrong branch.
        i = b.index("could not measure anything")
        before = b[:i]
        ms = list(re.finditer(r"if\s*\(([^)]*)\)\s*\{", before))
        self.assertTrue(ms, "could not find the empty-screen branch's own `if`")
        cond = ms[-1].group(1)
        self.assertIn("nMeas", cond,
                      "the branch does not test the measured count: %r" % cond)
        self.assertIn("allFailed", cond,
                      "the branch does not test the all-failed case: %r" % cond)

    def test_it_detects_the_all_failed_case_and_not_only_the_zero_case(self):
        """The service's state was n_measured 12 / n_unmeasured 12 -- NOT zero measured. A
        branch keyed only on zero would have printed the wrong sentence on the exact payload
        that prompted this."""
        b = self._renderer()
        self.assertIn("allFailed", b)
        self.assertIn("nUn >= nMeas", b)

    def test_the_surviving_no_name_cleared_sentence_is_SCOPED(self):
        b = self._renderer()
        self.assertIn("that could be measured", b)


class TheSpecCarriesTheClass(unittest.TestCase):
    """Item 19: add the class to PRODUCT_SPEC's end-to-end tests, so the next screen inherits
    the rule rather than the defect."""

    def _spec(self):
        return open(os.path.join(REPO, "PRODUCT_SPEC.md"), encoding="utf-8").read()

    def test_the_rule_is_stated(self):
        t = self._spec()
        self.assertIn("EVERY SCREEN MUST SHOW IT MEASURED SOMETHING", t)
        self.assertIn("may not render a sentence about the market", t)

    def test_it_records_why_46_tests_passed(self):
        """The transferable half. Without it the rule reads as bureaucracy."""
        t = self._spec()
        self.assertIn("cannot catch a caller passing the wrong type", t)
        self.assertIn("46", t)

    def test_it_names_all_four_obligations(self):
        t = self._spec()
        for frag in ("end-to-end test through the real injected dependency",
                     "wiring error must be LOUD",
                     "states which of the two things it means",
                     "never takes an artefact as an observation"):
            self.assertIn(frag, t, "the spec is missing: %s" % frag)

    def test_it_says_records_are_marked_and_not_deleted(self):
        t = self._spec()
        self.assertIn("MARKED, NEVER DELETED", t)
        self.assertIn("fleet_history.invalidate", t)

    def test_the_measured_service_figures_are_in_the_spec(self):
        """So the rule carries its evidence rather than an assertion."""
        t = self._spec()
        for n in ("241", "12", "2026-08-13", "42597e2"):
            self.assertIn(n, t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
