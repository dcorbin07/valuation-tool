# -*- coding: utf-8 -*-
"""Item 33 (a) and (b): the Form 4 crawl's refusals, and the dip screen's own rejections.

TWO DEFECTS, ONE SHAPE -- a refusal recorded as an answer.

  * `fetch4` fetched with `requests.get(...).text` and never read a status code, so SEC's 403
    body went to an XML parser, raised, and was banked as a parse failure. A name whose every
    document took one is left unwritten and the next step reads "no insider data". Measured on
    the 2026-10-06 themes run: 1,116 names crawled, **153** written, insider coverage 0.1547.
  * `screen` treated a withheld VALUATION as a rejected NAME, and the withhold fires on
    `fair_value / price > 5.0` -- a ratio whose denominator is the crashed price -- so the
    screen rejected its deepest names for being deep. Live, `rejected_checks` read 16 at every
    threshold with `rejected_health` 0 and `n_unmeasured` 0, and the page showed nothing.

Every test here fails against the pre-fix sources; the mutation block at the end proves the
guards bite rather than merely pass.
"""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from scripts import live_theme_sources as M                              # noqa: E402
from valuation.web import dip                                            # noqa: E402


# --------------------------------------------------------------------------------------- #
# (a) the guard paces what it says it paces
# --------------------------------------------------------------------------------------- #

class GuardIsThreadSafe(unittest.TestCase):

    def test_four_threads_do_not_collapse_into_one_interval(self):
        """The defect, reproduced: without a lock, N threads fire N requests per interval.

        `wait` is a read-modify-write on `_last`. Unsynchronised, four threads read the same
        value, each computes the same `need`, each sleeps it, and all four then proceed -- so
        the advertised 1/min_interval becomes 4/min_interval.

        THE ASSERTION IS WALL CLOCK, because that is the quantity SEC sees. Counting sleeps
        would not discriminate: all four threads DO sleep in the broken version, they simply
        sleep at the same time. Four serialised calls at 0.05s take >= ~0.15s (the first does
        not wait -- `_last` starts at 0, so its gap is the whole uptime); the unsynchronised
        version finishes in ~0.05s.
        """
        g = M.Guard(min_interval=0.05, sleeper=time.sleep)
        t0 = time.monotonic()

        def worker():
            g.wait()

        ts = [threading.Thread(target=worker) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        elapsed = time.monotonic() - t0

        self.assertEqual(g.calls, 4, "every call must be counted exactly once")
        self.assertGreaterEqual(
            elapsed, 3 * 0.05,
            "four paced calls collapsed into one interval -- the guard is not serialising")

    def test_calls_are_not_lost_under_contention(self):
        """`self.calls += 1` is itself a read-modify-write and was outside any lock."""
        g = M.Guard(min_interval=0.0, sleeper=lambda _s: None)

        def worker():
            for _ in range(200):
                g.wait()

        ts = [threading.Thread(target=worker) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(g.calls, 800, "a dropped increment means the counter under-reports")

    def test_single_threaded_behaviour_is_unchanged(self):
        """An uncontended lock changes nothing, which is what makes the fix safe to land."""
        slept = []
        g = M.Guard(min_interval=0.01, sleeper=slept.append)
        g.wait()
        g.wait()
        self.assertEqual(g.calls, 2)
        self.assertTrue(all(x <= 0.01 + M.SEC_JITTER_S + 1e-9 for x in slept))


class ThrottleStatusHasOneDefinition(unittest.TestCase):

    def test_the_codes_are_a_named_constant(self):
        self.assertEqual(tuple(sorted(M.THROTTLE_STATUS)), (403, 429, 503))

    def test_no_module_spells_the_tuple_out_again(self):
        """B7: it was written out four times and `fetch4` was about to make it five."""
        import io
        src = io.open(M.__file__, encoding="utf-8").read()
        self.assertEqual(src.count("(429, 403, 503)"), 1,
                         "the literal may appear only where THROTTLE_STATUS is defined")


# --------------------------------------------------------------------------------------- #
# (a) the parser reads the panel's row set
# --------------------------------------------------------------------------------------- #

# NO DEFAULT NAMESPACE -- real Form 4 XML carries none, which is why the shipped parser's
# `findtext(".//transactionCoding/transactionCode")` resolves at all. A namespaced fixture
# would be testing a document SEC does not publish, and the parser would correctly read
# nothing from it.
DOC = ('<ownershipDocument>'
       '<nonDerivativeTable>'
       '<nonDerivativeTransaction>'
       '<transactionCoding><transactionCode>P</transactionCode></transactionCoding>'
       '<transactionAmounts>'
       '<transactionShares><value>100</value></transactionShares>'
       '<transactionPricePerShare><value>10</value></transactionPricePerShare>'
       '<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>'
       '</transactionAmounts></nonDerivativeTransaction>'
       '<nonDerivativeTransaction>'
       '<transactionCoding><transactionCode>A</transactionCode></transactionCoding>'
       '<transactionAmounts>'
       '<transactionShares><value>500</value></transactionShares>'
       '<transactionPricePerShare><value>0</value></transactionPricePerShare>'
       '<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>'
       '</transactionAmounts></nonDerivativeTransaction>'
       '</nonDerivativeTable>'
       '<derivativeTable>'
       '<derivativeTransaction>'
       '<transactionCoding><transactionCode>M</transactionCode></transactionCoding>'
       '<transactionAmounts>'
       '<transactionShares><value>200</value></transactionShares>'
       '<transactionPricePerShare><value>3</value></transactionPricePerShare>'
       '<transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>'
       '</transactionAmounts></derivativeTransaction>'
       '</derivativeTable>'
       '</ownershipDocument>')


class ParserMatchesThePanelsRowSet(unittest.TestCase):

    def setUp(self):
        from scripts import fidelity2_rebuild as F2
        self.F2 = F2
        self.out = F2.parse_form4_signed(DOC)

    def test_the_open_market_purchase_is_read_and_signed(self):
        self.assertIn(("P", 1000.0), self.out)

    def test_a_derivative_transaction_is_read(self):
        """SF2 is 22.3% derivative-shaped and 532,710 of its valuable rows are derivative."""
        self.assertIn(("M", -600.0), self.out)

    def test_a_zero_valued_row_is_KEPT_not_dropped(self):
        """`_prep_insider` keeps `val is not None`; `if not val: continue` collapsed two cases.

        A window of zeros scores `_insider_formula(0, 0)` = 50 in the panel. An EMPTY window
        is `None`. Dropping zeros turned the first into the second.
        """
        self.assertIn(("A", 0.0), self.out)

    def test_a_window_of_only_zeros_scores_fifty_rather_than_none(self):
        """The panel's semantics, which is the reason the zeros have to survive the parser."""
        zeros = [{"code": "A", "raw": 0.0}, {"code": "F", "raw": 0.0}]
        self.assertEqual(self.F2.insider_score_from_txns(zeros), 50.0)

    def test_an_empty_window_is_still_none(self):
        """`FIDELITY-2`'s load-bearing rule: no opinion is not a neutral opinion."""
        self.assertIsNone(self.F2.insider_score_from_txns([]))

    def test_the_crawl_has_its_own_throttle_budget(self):
        """The module default of 40 would kill the themes job on a transient hiccup.

        `Guard`'s budget stops a run BANKING A PARTIAL CENSUS. This crawl banks no census --
        an unreadable name is left unwritten and retried -- so exhausting 40 across ~11,000
        documents would discard the 13F legs that already downloaded, which is the expensive
        half, to recover from something the next run would have picked up for free.
        """
        self.assertGreater(self.F2.FORM4_THROTTLE_BUDGET, M.THROTTLE_BUDGET)
        self.assertGreaterEqual(self.F2.FORM4_MAX_ATTEMPTS, 2,
                                "one attempt is not a retry")

    def test_the_tag_match_is_exact_rather_than_a_suffix(self):
        """`nonDerivativeTransaction` ends with a CAPITAL D, so a lowercase suffix test
        happens to work and hides that it was never deliberate."""
        self.assertEqual(self.F2.PARSED_TRANSACTION_TAGS,
                         ("nonDerivativeTransaction", "derivativeTransaction"))


# --------------------------------------------------------------------------------------- #
# (b) a withheld valuation is not a rejected name
# --------------------------------------------------------------------------------------- #

def _row(ticker, high_prox):
    """`high_prox` is the RATIO price/52-week-high, which is what `cheap_drawdown` reads.

    `extra.high_prox` and `extra.numbers.high_prox` are DIFFERENT fields -- the first is the
    raw ratio the preselector needs, the second the within-date z-score that is an ordering
    key only. Writing the fixture against the second gives `preselect_available` False and a
    test that measures the fallback path instead of the one it names.
    """
    return {"ticker": ticker, "name": ticker, "sector": "Tech", "price": 10.0,
            "market_cap": 5e9, "hot_score": 50, "rank": 1,
            "extra": {"high_prox": high_prox}}


def _measure_withheld(r):
    """A valuation the model refused to publish -- the live case on every deep name."""
    return {"drawdown": 0.62, "price": 10.0, "high_52w": 26.0,
            # EVERY floor in `HEALTH_FLOORS`, by name. A missing sub-score is a FAIL, so a
            # fixture that omits `growth` tests the health rejection rather than the subject.
            "subs": {"health": 70, "quality": 70, "growth": 70},
            "score": 61, "confidence": "medium",
            "fair_value": 80.0, "upside": 7.0,
            "fair_value_low": 60.0, "fair_value_high": 100.0,
            "fair_value_withheld_reason": "fair value is more than 5x the price",
            "checks": {"withheld": dip.FAIL,
                       "beta_provenance": dip.PASS,
                       "terminal_share": dip.PASS}}


class AWithheldValuationKeepsTheName(unittest.TestCase):

    def setUp(self):
        rows = [_row("AAA", 0.38), _row("BBB", 0.40)]
        self.p = dip.screen(rows, min_drawdown=0.10, measure=_measure_withheld, shortlist=2)

    def test_the_rows_are_returned(self):
        """The defect: all twelve valued names were dropped and the page showed nothing."""
        self.assertEqual(len(self.p["rows"]), 2,
                         "a refused valuation must not remove a name that is genuinely down")

    def test_the_drawdown_and_health_survive(self):
        r = self.p["rows"][0]
        self.assertAlmostEqual(r["drawdown"], 0.62)
        self.assertTrue(r["health"])

    def test_every_published_valuation_field_is_nulled_together(self):
        r = self.p["rows"][0]
        for k in ("fair_value", "upside", "fair_value_low", "fair_value_high", "score",
                  "confidence"):
            self.assertIsNone(r[k], "%s outlived the refusal" % k)

    def test_the_reason_travels_with_the_row(self):
        self.assertIn("5x", self.p["rows"][0]["fair_value_withheld_reason"])

    def test_the_row_says_it_is_withheld_and_which_check_did_it(self):
        r = self.p["rows"][0]
        self.assertTrue(r["valuation_withheld"])
        self.assertEqual(r["valuation_withheld_checks"], ["withheld"])

    def test_the_count_is_reported_separately_from_row_level_rejections(self):
        """One counter served two different events and could not be read without arithmetic."""
        self.assertEqual(self.p["withheld_valuation"], 2)
        self.assertEqual(self.p["rejected_checks"], 0)

    def test_the_note_states_the_withheld_count(self):
        self.assertIn("WITHHELD", self.p["preselect_note"])
        self.assertIn("2 of those", self.p["preselect_note"])


class TheMeasurementBudgetIsTheMeasuredKnee(unittest.TestCase):
    """`DEFAULT_SHORTLIST` 12 -> 18, and the number is measured rather than preferred.

    The old comment justified 12 by the exact ordering -- "the N MOST drawn-down eligible
    names, not a sample of them" -- and item 33 changed the allocation to SPREAD the budget
    across the qualifying range so the rows span what the caller asked for. Spread over 223
    qualifiers, 12 IS a sample. Live at `min_drawdown` 0.10 on the 2026-10-06 scan:
    12 -> 0 rows, 18 -> 4 rows (18.1s cold), 25 -> 4 rows (17.9s cold).
    """

    def test_the_default_is_the_measured_knee(self):
        self.assertEqual(dip.DEFAULT_SHORTLIST, 18)

    def test_the_default_never_exceeds_the_ceiling(self):
        """A default above `MAX_SHORTLIST` would be silently clamped by the route, so the
        module and the surface would disagree about what the page asked for."""
        self.assertLessEqual(dip.DEFAULT_SHORTLIST, dip.MAX_SHORTLIST)

    def test_the_reason_travels_with_the_constant(self):
        """The measurement is the justification, so it has to be readable where the number is.

        A bare `DEFAULT_SHORTLIST = 18` invites the next reader to lower it for latency
        without knowing that 12 returned nothing at the setting the page opens on.
        """
        import io
        src = io.open(dip.__file__, encoding="utf-8").read()
        head = src[:src.index("DEFAULT_SHORTLIST = 18")]
        for needle in ("shortlist 12 ->  0 rows", "shortlist 18 ->  4 rows", "warm"):
            self.assertIn(needle, head, needle)


class ThePublishableCaseIsUnchanged(unittest.TestCase):
    """The fix must not publish anything it did not publish before."""

    def test_a_clean_valuation_still_carries_its_numbers(self):
        def ok(r):
            m = _measure_withheld(r)
            m["checks"] = {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                           "terminal_share": dip.PASS}
            return m
        p = dip.screen([_row("AAA", 0.38)], min_drawdown=0.10, measure=ok, shortlist=1)
        r = p["rows"][0]
        self.assertFalse(r["valuation_withheld"])
        self.assertEqual(r["fair_value"], 80.0)
        self.assertEqual(p["withheld_valuation"], 0)

    def test_health_still_rejects(self):
        def sick(r):
            m = _measure_withheld(r)
            m["checks"] = {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                           "terminal_share": dip.PASS}
            m["subs"] = {"health": 1, "quality": 1, "growth": 1}
            return m
        p = dip.screen([_row("AAA", 0.38)], min_drawdown=0.10, measure=sick, shortlist=1)
        self.assertEqual(len(p["rows"]), 0)
        self.assertEqual(p["rejected_health"], 1)

    def test_a_shallow_name_is_still_rejected(self):
        def shallow(r):
            m = _measure_withheld(r)
            m["checks"] = {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                           "terminal_share": dip.PASS}
            m["drawdown"] = 0.01
            return m
        p = dip.screen([_row("AAA", 0.38)], min_drawdown=0.10, measure=shallow, shortlist=1)
        self.assertEqual(len(p["rows"]), 0)
        self.assertEqual(p["rejected_shallow"], 1)

    def test_a_row_the_SNAPSHOT_refused_is_still_rejected_before_measurement(self):
        """Unchanged on purpose: that site is a row-level fact with no valuation to suppress."""
        r = _row("AAA", 0.38)
        r[dip.ROW_WITHHELD] = True
        p = dip.screen([r], min_drawdown=0.10, measure=_measure_withheld, shortlist=1)
        self.assertEqual(len(p["rows"]), 0)
        self.assertEqual(p["rejected_checks"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
