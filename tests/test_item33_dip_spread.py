# -*- coding: utf-8 -*-
"""The dip screen spent its whole budget on the deepest tail, and reported an impossible count.

    python tests/test_item33_dip_spread.py

MEASURED ON THE LIVE SERVICE, 2026-10-06 (scan 2026-10-05). At `min_drawdown=0.10` the screen
found **204** qualifying names, valued **12**, and showed **2** -- APP and PODD, both about 60%
down. So a user asking for "down 10%" was shown only the most extreme crashes in the market, and
nothing on the page said the other 192 qualifiers had never been looked at.

TWO DEFECTS, AND THEY ARE INDEPENDENT.

 1. **AN IMPOSSIBLE COUNT.** The note read *"the 204-of-163 eligible names"*. `n_qualified` (204)
    counts names kept on depth PLUS names kept because their depth is UNKNOWN; `n_with_cheap`
    (163) counts only names a depth could be read for. The two are not nested, so the ratio was
    two different denominators -- the kind of number a reader stops trusting the whole payload
    over.
 2. **THE BUDGET BOUGHT THE TAIL.** `qualified[:shortlist]` on a deepest-first ordering is the
    12 most extreme names, every time.

RAISING THE CAP IS NOT THE FIX, AND THAT WAS MEASURED RATHER THAN ASSUMED: `_get_or_compute`
falls through to a full `value_ticker` on a cache miss, so 204 qualifiers is 204 valuations
inside one request on a 512 MB instance. The budget stays and now buys a SAMPLE OF THE WHOLE
RANGE.

AND THE OTHER OPTION -- "use the scan's own fair values and health" -- IS ONLY HALF AVAILABLE,
which is a premise correction worth recording. Measured on the live snapshot: rows carry
`fair_value` (77 of 100) and `extra.high_prox` (82 of 100), but **no sub-scores**. `health_check`
scores against `HEALTH_FLOORS` on a valuation's `subs`, so health cannot be decided from the
snapshot at all. Skipping the valuation would mean dropping the health gate, which is the thing
this screen exists to apply.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from valuation.web import dip  # noqa: E402


def _row(t, high_prox=None, **kw):
    r = {"ticker": t, "name": t + " Inc", "price": 100.0,
         "z_quality": 1.0, "z_growth": 1.0, "extra": {"numbers": {}}}
    if high_prox is not None:
        r["extra"]["high_prox"] = high_prox
    r.update(kw)
    return r


def _healthy(dd, **kw):
    m = {"drawdown": dd, "subs": {"quality": 80.0, "health": 75.0, "growth": 70.0},
         "checks": {"withheld": "pass", "beta_provenance": "pass", "terminal_share": "pass"}}
    m.update(kw)
    return m


class TheSpreadHelper(unittest.TestCase):
    def test_it_keeps_both_ENDS(self):
        """The deepest name is the one the page is most likely to be asked about; the shallowest
        qualifier is what makes the result span the request."""
        got = dip.spread_across(list(range(204)), 12)
        self.assertEqual(got[0], 0)
        self.assertEqual(got[-1], 203)

    def test_it_spends_the_WHOLE_budget(self):
        """Rounding collisions must be topped up, or the screen quietly under-uses its cap."""
        for n in (13, 20, 47, 204, 1000):
            for k in (2, 5, 12, 25):
                got = dip.spread_across(list(range(n)), k)
                self.assertEqual(len(got), min(n, k), "n=%d k=%d" % (n, k))
                self.assertEqual(len(set(got)), len(got), "duplicates at n=%d k=%d" % (n, k))

    def test_it_is_ordered_and_deterministic(self):
        a = dip.spread_across(list(range(204)), 12)
        self.assertEqual(a, dip.spread_across(list(range(204)), 12))
        self.assertEqual(a, sorted(a))

    def test_the_degenerate_cases_do_not_raise(self):
        self.assertEqual(dip.spread_across([], 12), [])
        self.assertEqual(dip.spread_across(list(range(5)), 12), list(range(5)))
        self.assertEqual(dip.spread_across(list(range(10)), 1), [0])
        self.assertEqual(dip.spread_across(list(range(10)), 0), [])
        self.assertEqual(dip.spread_across(list(range(10)), None), [])

    def test_it_is_NOT_the_first_k(self):
        """The whole point. If this ever reverts to a prefix the page goes back to showing only
        the deepest crashes for every threshold."""
        got = dip.spread_across(list(range(204)), 12)
        self.assertNotEqual(got, list(range(12)))


class TheScreenSpansTheRequestedRange(unittest.TestCase):
    def _rows(self, n=60):
        """`n` names from 60% down to 10% down, deepest first -- the live shape."""
        out = []
        for i in range(n):
            dd = 0.60 - (0.50 * i / float(n - 1))        # 0.60 .. 0.10
            out.append(_row("T%03d" % i, high_prox=1.0 - dd))
        return out

    def test_the_valued_names_span_the_range_rather_than_the_deep_tail(self):
        rows = self._rows()
        seen = []

        def _m(r):
            dd = 1.0 - (r.get("extra") or {}).get("high_prox")
            seen.append(dd)
            return _healthy(dd)

        out = dip.screen(rows, 0.10, measure=_m, shortlist=12)
        self.assertEqual(len(seen), 12, "the budget was not fully spent")
        self.assertGreater(max(seen), 0.55, "the deepest name was dropped")
        self.assertLess(min(seen), 0.20,
                        "every valued name was from the deep end -- the defect this fixes; "
                        "shallowest valued was %.3f" % min(seen))
        self.assertGreaterEqual(len(out["rows"]), 10)

    def test_a_small_qualifying_set_is_valued_WHOLE(self):
        rows = self._rows(n=8)
        out = dip.screen(rows, 0.10, measure=lambda r: _healthy(
            1.0 - (r.get("extra") or {}).get("high_prox")), shortlist=12)
        self.assertEqual(out["n_measured"], 8)
        self.assertEqual(out["capped"], 0)


class TheCountsNestAndTheNoteIsPossible(unittest.TestCase):
    def _mixed(self):
        """Deep names WITH a depth reading, plus names with NO reading -- the live mix that
        produced 204-of-163."""
        rows = [_row("D%02d" % i, high_prox=0.40) for i in range(20)]
        rows += [_row("U%02d" % i) for i in range(10)]          # no high_prox at all
        return rows

    def test_qualified_equals_depth_pass_plus_depth_unknown(self):
        out = dip.screen(self._mixed(), 0.10,
                         measure=lambda r: _healthy(0.60), shortlist=5)
        self.assertTrue(out["preselect_available"])
        self.assertEqual(out["n_qualified_on_depth"],
                         out["n_depth_pass"] + out["n_depth_unknown_kept"],
                         "the three counts do not add up, which is how 204-of-163 happened")

    def test_the_note_ratio_is_POSSIBLE(self):
        """`n_qualified` can exceed `n_checked_for_depth`; it can never exceed `n_eligible`."""
        out = dip.screen(self._mixed(), 0.10,
                         measure=lambda r: _healthy(0.60), shortlist=5)
        self.assertLessEqual(out["n_qualified_on_depth"], out["n_eligible"])
        self.assertIn("of the %d eligible" % out["n_eligible"], out["preselect_note"])

    def test_the_old_impossible_phrasing_is_gone(self):
        out = dip.screen(self._mixed(), 0.10,
                         measure=lambda r: _healthy(0.60), shortlist=5)
        note = out["preselect_note"]
        self.assertNotIn("%d-of-%d" % (out["n_qualified_on_depth"],
                                       out["n_checked_for_depth"]), note)

    def test_the_note_states_how_many_qualified_and_how_many_were_valued(self):
        out = dip.screen(self._mixed(), 0.10,
                         measure=lambda r: _healthy(0.60), shortlist=5)
        self.assertIn(str(out["n_qualified_on_depth"]), out["preselect_note"])
        self.assertIn(str(out["n_measured"]), out["preselect_note"])
        self.assertIn("SPREAD ACROSS", out["preselect_note"])

    def test_the_selection_field_says_which_mode_it_used(self):
        wide = dip.screen(self._mixed(), 0.10, measure=lambda r: _healthy(0.60), shortlist=5)
        self.assertEqual(wide["selection"], "spread across the qualifying range")
        narrow = dip.screen(self._mixed(), 0.10, measure=lambda r: _healthy(0.60), shortlist=99)
        self.assertEqual(narrow["selection"], "all qualifiers")


class TheScanCannotSupplyHealth(unittest.TestCase):
    """The premise correction, pinned so a later change does not quietly drop the health gate on
    the strength of 'the scan already has it'."""

    def test_health_needs_subscores_which_a_snapshot_row_does_not_carry(self):
        self.assertFalse(dip.health_check({})["ok"],
                         "an empty sub-score dict passed the health floors")
        self.assertTrue(dip.health_check(
            {k: 99.0 for k in dip.HEALTH_FLOORS})["ok"])

    def test_a_missing_subscore_is_not_a_pass(self):
        subs = {k: 99.0 for k in dip.HEALTH_FLOORS}
        subs.pop(sorted(dip.HEALTH_FLOORS)[0])
        self.assertFalse(dip.health_check(subs)["ok"])


class TheBudgetGoesToNamesKnownToQualify(unittest.TestCase):
    """THE DEFECT MY OWN FIRST CUT SHIPPED, measured on the live service and pinned here.

    Spreading across ALL qualifiers sampled the depth-UNKNOWN names too -- 64 of 204, about a
    third of the budget -- and those are precisely the names least likely to clear the threshold
    once measured. Live at `min_drawdown=0.10`: 12 valued, `rejected_health` 0, `n_unmeasured`
    0, and **0 rows returned**, where the old deepest-first behaviour returned 2. That is item
    23's defect reintroduced by the fix for a different one.

    The unknowns stay REACHABLE -- they take whatever budget the known set does not use -- so a
    snapshot with little depth coverage still measures them rather than dropping them silently.
    """

    def _rows(self, n_known=40, n_unknown=40):
        rows = []
        for i in range(n_known):
            dd = 0.60 - (0.45 * i / float(n_known - 1))     # 0.60 .. 0.15, all qualifying
            rows.append(_row("K%03d" % i, high_prox=1.0 - dd))
        rows += [_row("U%03d" % i) for i in range(n_unknown)]
        return rows

    def test_the_budget_is_not_spent_on_depth_unknown_names_when_known_ones_exist(self):
        seen = []

        def _m(r):
            seen.append(r["ticker"])
            hp = (r.get("extra") or {}).get("high_prox")
            return _healthy(1.0 - hp if hp else 0.02)

        dip.screen(self._rows(), 0.10, measure=_m, shortlist=12)
        self.assertEqual(len(seen), 12)
        self.assertFalse([t for t in seen if t.startswith("U")],
                         "budget spent on names with no known depth: %r" % (seen,))

    def test_the_unknowns_are_still_reachable_when_budget_remains(self):
        """They must not become unmeasurable -- a snapshot with little depth coverage is exactly
        when they matter."""
        seen = []

        def _m(r):
            seen.append(r["ticker"])
            hp = (r.get("extra") or {}).get("high_prox")
            return _healthy(1.0 - hp if hp else 0.50)

        dip.screen(self._rows(n_known=3, n_unknown=20), 0.10, measure=_m, shortlist=12)
        self.assertEqual(len([t for t in seen if t.startswith("K")]), 3)
        self.assertTrue([t for t in seen if t.startswith("U")],
                        "spare budget did not reach the unknowns: %r" % (seen,))

    def test_a_shallow_measurement_is_COUNTED_rather_than_vanishing(self):
        """With `rejected_health` 0 and `n_unmeasured` 0 and no rows, there was no way to tell
        where twelve valuations had gone without reasoning about it."""
        # All twelve clear the FREE depth floor (0.50 against a 0.30 request) and all twelve
        # measure shallow, so the count is unambiguous. A fixture whose names did not all
        # qualify would make this assert the qualifier count instead.
        rows = [_row("K%02d" % i, high_prox=0.50) for i in range(12)]
        out = dip.screen(rows, 0.30, measure=lambda r: _healthy(0.05), shortlist=12)
        self.assertEqual(out["n_measured"], 12)
        self.assertEqual(out["rejected_shallow"], 12)
        self.assertEqual(out["rows"], [])

    def test_the_counts_still_include_the_unknowns_as_qualified(self):
        """The split changes which names BUY a valuation, not what `qualified` means."""
        out = dip.screen(self._rows(n_known=40, n_unknown=40), 0.10,
                         measure=lambda r: _healthy(0.50), shortlist=12)
        self.assertEqual(out["n_qualified_on_depth"],
                         out["n_depth_pass"] + out["n_depth_unknown_kept"])
        self.assertEqual(out["n_depth_unknown_kept"], 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
