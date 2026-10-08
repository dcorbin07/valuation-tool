# -*- coding: utf-8 -*-
"""`STAGE1-BATCH2` — the kill pass's bars, its borrowed machinery and its refusals.

The load-bearing pin is that **no forward return is touched anywhere in the kill module**. Every
kill is a census of the panel's own inputs or of a scaling factor, which is what makes it free
under `MB1-SEL` — a control that can only BLOCK adds no degree of freedom. A kill that peeked at
`fwd_ret` would be an arm wearing a control's name.

Run as its own process and judged by exit code, per `RUN_RULES`.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "stage1_batch2_kills.py")
REGISTER = os.path.join(ROOT, "PREREG_stage1_batch2.md")


def _src():
    return io.open(SRC, encoding="utf-8").read()


def _tree():
    return ast.parse(_src())


def _consts():
    out = {}
    for n in _tree().body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception:
                pass
    return out


def _names_referenced():
    out = set()
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add(a.asname or a.name)
    return out


def _string_constants():
    return {n.value for n in ast.walk(_tree())
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


import scripts.stage1_batch2_kills as K                                     # noqa: E402


# =============================================================================================
class NoForwardReturnIsTouched(unittest.TestCase):
    """The whole reason the kills are FREE. Read off the tree and off the subscript keys, not as
    a banned substring — the module legitimately DISCUSSES forward returns in its own prose, and
    a substring ban would fire on the paragraph that documents the rule."""

    def test_no_subscript_or_get_names_a_forward_return(self):
        banned = {"fwd_ret", "fwd_ret_h63", "fwd_ret_h126", "fwd_ret_h189", "fwd_ret_h252",
                  "fwd_ret_h315", "fwd_ret_h378", "fwd_ret_h441", "fwd_ret_h504",
                  "forward_return", "bench_ret"}
        hits = []
        for n in ast.walk(_tree()):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                    and n.slice.value in banned:
                hits.append((n.slice.value, n.lineno))
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) in ("get", "__getitem__") \
                    and n.args and isinstance(n.args[0], ast.Constant) \
                    and n.args[0].value in banned:
                hits.append((n.args[0].value, n.lineno))
        self.assertFalse(hits, "the kill pass reads a forward return: %r" % (hits,))

    def test_the_detector_is_not_vacuous(self):
        """A positive control: the pattern it bans must be visible when present."""
        probe = ast.parse('y = g["fwd_ret"]\n')
        found = [n.slice.value for n in ast.walk(probe)
                 if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)]
        self.assertIn("fwd_ret", found,
                      "the forward-return detector cannot see the thing it bans")

    def test_no_scoring_function_is_imported(self):
        """`incremental_ic`, `quantile_backtest` and `hac_t` all consume an outcome. None belongs
        in a pass that claims to charge nothing."""
        ref = _names_referenced()
        for bad in ("incremental_ic", "quantile_backtest", "hac_t", "benjamini_hochberg",
                    "stage1_verdict"):
            self.assertNotIn(bad, ref,
                             "%s is reachable from the kill pass, which consumes an outcome" % bad)


# =============================================================================================
class EveryBarIsTheRegistersAndIsALiteral(unittest.TestCase):
    def test_the_bars_are_module_level_literals(self):
        c = _consts()
        for n in ("K0_IBES_FLOOR", "B1_INERT_MEDIAN", "B2_LEVERAGE_SHARE", "B3_COSTUME_BAR",
                  "B3_MOMENTUM_ONLY_AT", "B4_COSTUME_BAR", "B5_NONIDENTITY_BAR",
                  "CONTRACT_MIN_POSITIONS", "TIER_FLOOR_USD"):
            self.assertIn(n, c, "%s is computed rather than fixed, so it could move with the "
                                "data it judges" % n)

    def test_the_values_match_the_register(self):
        self.assertEqual(K.K0_IBES_FLOOR, 0.70)
        self.assertEqual(K.B1_INERT_MEDIAN, 0.02)
        self.assertEqual(K.B2_LEVERAGE_SHARE, 0.50)
        self.assertEqual(K.B3_COSTUME_BAR, 0.60)
        self.assertEqual(K.B3_MOMENTUM_ONLY_AT, 0.50)
        self.assertEqual(K.B4_COSTUME_BAR, 0.60)
        self.assertEqual(K.B5_NONIDENTITY_BAR, 0.99)
        self.assertEqual(K.CONTRACT_MIN_POSITIONS, 50)
        self.assertEqual(K.TIER_FLOOR_USD, 10e9)

    def test_the_register_exists_and_names_every_bar(self):
        """A bar whose register does not mention it is a bar chosen here."""
        self.assertTrue(os.path.exists(REGISTER))
        reg = io.open(REGISTER, encoding="utf-8").read()
        for frag in ("0.70", "2%", "0.50", "0.60", "0.99", "50"):
            self.assertIn(frag, reg, "the register does not state the bar %r" % frag)

    def test_the_full_universe_IBES_figure_is_recorded_for_contrast(self):
        """0.6999955119640681 must travel beside the tier reading, or the two get confused — and
        the full-universe figure is NOT a pass at any point."""
        self.assertAlmostEqual(K.FULL_UNIVERSE_IBES_CELLS, 0.6999955119640681, places=15)
        self.assertLess(K.FULL_UNIVERSE_IBES_CELLS, K.K0_IBES_FLOOR,
                        "the full-universe figure must remain BELOW the floor; if it ever reads "
                        "as clearing, something has been relaxed")


# =============================================================================================
class TheTierIsAThresholdNotARank(unittest.TestCase):
    """`INDEX-CHOICE-ARM4`'s own distinction. A RANK is a property of the POPULATION and changes
    meaning the moment the universe is halved, so `X1`'s split cannot evaluate it. A market-cap
    THRESHOLD is a property of the NAME and is invariant under the split."""

    def test_the_tier_is_selected_on_market_cap_and_not_on_a_rank(self):
        ref = _names_referenced()
        for bad in ("universe_rank", "nlargest", "rank"):
            self.assertNotIn(bad, ref,
                             "the tier is selected by %s, which is a property of the POPULATION "
                             "and is not invariant under X1's split" % bad)

    def test_the_tier_floor_is_absolute_dollars(self):
        self.assertEqual(K.TIER_FLOOR_USD, 10e9)

    def test_the_tier_ships_its_per_date_count(self):
        """A nominal $10bn floor drifts in real terms across 2009-2019, so a reader must see the
        tier's size moving rather than assume it fixed."""
        self.assertIn("names_per_date", _string_constants())
        self.assertIn("why_the_count_ships", _string_constants())

    def test_the_50_floor_is_checked_on_the_FILTERED_tier_too(self):
        """Checking it on the unfiltered tier would miss exactly the case that matters: a filter
        that leaves the tier assessable in principle and unassessable in practice."""
        self.assertIn("filtered_tier_dates_below_50", _string_constants())


# =============================================================================================
class TheBorrowedMachineryIsCalledNotReimplemented(unittest.TestCase):
    def test_it_calls_the_shipped_helpers(self):
        ref = _names_referenced()
        for n in ("build_quadrant", "costume_rho", "junk_ok", "_ttm_free_or_called",
                  "resolve_route_b", "_hist"):
            if n == "_ttm_free_or_called":
                continue
            self.assertIn(n, ref, "%s is not called; a second implementation is B7's defect" % n)

    def test_it_does_not_redefine_them(self):
        defined = {n.name for n in _tree().body if isinstance(n, ast.FunctionDef)}
        for n in ("build_quadrant", "costume_rho", "junk_ok", "stable_key_half",
                  "resolve_route_b", "incremental_ic"):
            self.assertNotIn(n, defined, "%s is re-implemented in the kill pass" % n)

    def test_the_three_junk_screens_are_TIERED_POOLs(self):
        """The register says 'reused verbatim'. If this module ever grows its own TTM sum, `_ttm`'s
        restatement collapse and span refusal are lost, and a partial sum reads as a junk company
        — the direction that FLATTERS the arm."""
        defined = {n.name for n in _tree().body if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("_ttm", defined)
        self.assertIn("junk_ok", _names_referenced())


# =============================================================================================
class TheHistoryIsPreSorted(unittest.TestCase):
    """A DEFECT OF MY OWN, PINNED SO IT CANNOT COME BACK.

    `_ttm` BREAKS at the first row whose datekey exceeds `as_of` and its docstring says *"rows
    are pre-sorted by datekey"*. `_indexed()` does NOT sort — `fundamentals_pit` sorts for
    itself, which is the tell. On raw order `_ttm` takes a truncated arbitrary prefix and returns
    None for having fewer than four quarters.

    The first kill pass handed it `_indexed("fundamentals")` and read an evaluable share of
    **0.4654** on $10B names, with AAPL and MSFT both failing on 129 and 133 rows and four clean
    quarters inside a 272-day span. Sorted, the share is **0.9148** and the median failure share
    moves 0.7458 → 0.4670. **None of the first figures was reported.**
    """

    def test_it_does_not_use_the_unsorted_index(self):
        ref = _names_referenced()
        self.assertNotIn("_indexed", ref,
                         "the kill pass reads prov._indexed(), which does NOT sort -- `_ttm` "
                         "breaks early on raw order and returns None for a truncated window")

    def test_it_calls_TIERED_POOLs_own_sorted_builder(self):
        self.assertIn("_hist", _names_referenced(),
                      "tiered_pool_run._hist builds the history 'pre-sorted exactly as the panel "
                      "builder sorts it'; a second sort is a second chance to get the key wrong, "
                      "and the key is `datekey or date` rather than `datekey`")

    def test_ttm_really_does_need_the_sort(self):
        """Non-vacuity, and it is the whole point: feed `_ttm` the SAME rows in raw and sorted
        order and the two must DISAGREE, or this guard is protecting nothing."""
        from valuation.edge.fundamental_panel import _ttm
        # THE MECHANISM IS THE `break`, SO A POST-`as_of` ROW MUST APPEAR EARLY. My first
        # fixture listed the future row LAST, where the loop reaches it only after picking all
        # four valid quarters -- so raw order happened to work and the test fired against a
        # correct guard. A fixture that does not exhibit the defect proves nothing about it.
        rows = [
            {"datekey": "2015-01-27", "reportperiod": "2014-12-27", "netinc": 9.0},
            {"datekey": "2014-10-27", "reportperiod": "2014-09-27", "netinc": 4.0},
            {"datekey": "2014-01-28", "reportperiod": "2013-12-28", "netinc": 1.0},
            {"datekey": "2014-04-24", "reportperiod": "2014-03-29", "netinc": 2.0},
            {"datekey": "2014-07-23", "reportperiod": "2014-06-28", "netinc": 3.0},
        ]
        srt = sorted(rows, key=lambda r: r["datekey"])
        self.assertIsNotNone(_ttm(srt, "2015-01-20", ("netinc",)),
                             "sorted rows must resolve, or the fixture is wrong")
        self.assertIsNone(_ttm(rows, "2015-01-20", ("netinc",)),
                          "raw order must FAIL, or the pre-sort guard is protecting nothing")


# =============================================================================================
class ItChargesNothing(unittest.TestCase):
    def test_zero_trials_declared(self):
        s = _src()
        self.assertIn('"trials": 0', s)
        self.assertIn("MB1-SEL", s)

    def test_k_stays_6(self):
        self.assertIn('"k_stays": 6', _src())

    def test_B6_is_recorded_as_withdrawn(self):
        """It carries no verdict in either direction, and `k` does not shrink for it."""
        self.assertIn("WITHDRAWN", _src())


# =============================================================================================
class TheArtifactIsReadableOnItsOwn(unittest.TestCase):
    def test_the_kill_artifact_records_every_arm_and_its_bar(self):
        import json
        from scripts.corrected_claims import fa
        p = os.path.join(fa(), "STAGE1_BATCH2_KILLS.json")
        if not os.path.exists(p):
            print("SKIP: STAGE1_BATCH2_KILLS.json absent (licensed data not on this host)")
            return
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        self.assertEqual(d["trials"], 0)
        self.assertEqual(d["k_stays"], 6)
        self.assertIn("bars_are_the_registers", d)
        for arm in ("B4_K0_tier_ibes", "B1_K1_inertness", "B2_K1_leverage",
                    "B3_K1_costume", "B5_K1_nonidentity"):
            self.assertIn(arm, d["kills"])
            self.assertIn("kill_passes", d["kills"][arm])

    def test_the_tier_clears_the_contract_floor_or_says_so(self):
        import json
        from scripts.corrected_claims import fa
        p = os.path.join(fa(), "STAGE1_BATCH2_KILLS.json")
        if not os.path.exists(p):
            return
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        t = d["tier"]
        self.assertIn("clears_50_on_every_date", t)
        self.assertIn("names_per_date_min", t)
        if not t["clears_50_on_every_date"]:
            self.assertTrue(t["dates_below_contract_min_positions"],
                            "the tier is recorded as failing the floor with no dates named")


if __name__ == "__main__":
    unittest.main(verbosity=2)
