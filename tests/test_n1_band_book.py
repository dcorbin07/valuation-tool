# -*- coding: utf-8 -*-
"""N1 -- the band book DESCRIPTION. Tests for the universe predicate and its controls.

The load-bearing ones:

 1. **The band is READ from the census, not retyped.** Both knobs were frozen before any return
    was scored; a local copy would let a successor move one after seeing a number (`W-28`).
 2. **The ADV lookup is the EXACT CELL, not an unbounded walk-back.** `pit_adv_at` walks back
    with no limit, and past CRSP's 2024-10-23 cut that silently returns ADV up to fifteen months
    stale -- which is what made the control refuse on the first run.
 3. **A name with no observable ADV is EXCLUDED, never admitted.** Admitting it makes the floor
    a data-availability screen that fails OPEN (`S10`, `D6`).
 4. **The control reproduces the census's own published counts**, which is what makes this
    universe builder the census's rather than a lookalike.
 5. **No verdict**: this is a description, so nothing here may compare a return to a bar.
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import pandas as pd                                                     # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N1 = os.path.join(REPO, "scripts", "n1_band_book.py")
CENSUS = os.path.join(REPO, "FREE_KILLS_CENSUS.json")
MEMO = os.path.join(REPO, "DECISION_index_choice.md")


def _src(p):
    return io.open(p, encoding="utf-8").read()


class TheBandIsReadFromTheCensus(unittest.TestCase):
    def test_the_knobs_come_from_the_artifact_and_are_the_frozen_ones(self):
        from scripts.n1_band_book import frozen_band
        ceiling, floor = frozen_band()
        self.assertEqual(ceiling, 5_000_000_000.0)
        self.assertEqual(floor, 5_000_000.0)

    def test_the_band_key_is_asserted_against_the_census(self):
        """If the census's chosen band ever changes, this must FAIL rather than silently score a
        different universe."""
        from scripts.n1_band_book import frozen_band
        j = json.load(open(CENSUS, encoding="utf-8"))
        real = j["N1"]["band_used"]
        j["N1"]["band_used"] = "cap<2B_adv>20M"
        tmp = os.path.join(os.path.dirname(CENSUS), "_tmp_census_probe.json")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(j, fh)
            import scripts.n1_band_book as M
            keep = M.CENSUS
            M.CENSUS = tmp
            try:
                with self.assertRaises(AssertionError):
                    M.frozen_band()
            finally:
                M.CENSUS = keep
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self.assertEqual(real, "cap<5B_adv>5M")
        self.assertEqual(frozen_band(), (5e9, 5e6))     # and the real one still reads

    def test_the_knobs_are_not_assigned_as_local_literals(self):
        tree = ast.parse(_src(N1))
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id in ("CEILING", "FLOOR",
                                                            "ADV_FLOOR", "CAP_CEILING"):
                        self.fail("%s is a local copy of a census-frozen knob" % t.id)


class TheAdvLookupIsTheExactCell(unittest.TestCase):
    def test_an_exact_hit_is_returned_and_a_miss_is_none(self):
        from scripts.n1_band_book import adv_at
        cells = {("AAA", "2020-01-15"): 7e6}
        self.assertEqual(adv_at(cells, "aaa", "2020-01-15"), 7e6)
        self.assertIsNone(adv_at(cells, "AAA", "2020-04-15"))

    def test_it_does_NOT_walk_back_to_a_stale_session(self):
        """THE DEFECT THIS ITEM SHIPPED ONCE. An unbounded walk-back past a vendor cut returns
        ADV from up to fifteen months earlier and reads as coverage."""
        from scripts.n1_band_book import adv_at
        cells = {("AAA", "2024-10-23"): 9e6}
        self.assertIsNone(adv_at(cells, "AAA", "2026-01-28"),
                          "a lookup 15 months past the vendor cut must MISS, not walk back")

    def test_the_script_does_not_call_the_unbounded_walk_back(self):
        tree = ast.parse(_src(N1))
        called = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Attribute):
                    called.add(f.attr)
                elif isinstance(f, ast.Name):
                    called.add(f.id)
        self.assertNotIn("pit_adv_at", called,
                         "pit_adv_at's walk-back is unbounded; the exact cell is the census's "
                         "definition and needs no staleness parameter")


class AMissingAdvIsExcluded(unittest.TestCase):
    def _rows(self):
        return [{"ticker": "BIG", "market_cap": 9e9, "hot_score": 50.0, "price": 1.0},
                {"ticker": "OK", "market_cap": 1e9, "hot_score": 60.0, "price": 1.0},
                {"ticker": "THIN", "market_cap": 1e9, "hot_score": 70.0, "price": 1.0},
                {"ticker": "NOADV", "market_cap": 1e9, "hot_score": 80.0, "price": 1.0}]

    def test_the_four_outcomes_are_each_counted(self):
        from scripts.n1_band_book import band_filter
        cells = {("OK", "2020-01-15"): 9e6, ("THIN", "2020-01-15"): 1e6}
        counts = []
        f = band_filter(cells, 5e9, 5e6, counts)
        kept = f(self._rows(), "2020-01-15")
        self.assertEqual([r["ticker"] for r in kept], ["OK"])
        c = counts[0]
        self.assertEqual((c["over_cap"], c["under_floor"], c["no_adv"]), (1, 1, 1))
        self.assertEqual(c["eligible"], 1)
        self.assertEqual(c["scored"], 4)

    def test_the_floor_is_STRICTLY_greater_so_a_name_at_the_floor_is_out(self):
        from scripts.n1_band_book import band_filter
        cells = {("OK", "2020-01-15"): 5e6}
        f = band_filter(cells, 5e9, 5e6)
        self.assertEqual(f([{"ticker": "OK", "market_cap": 1e9}], "2020-01-15"), [])

    def test_the_ceiling_is_STRICTLY_below_so_a_name_at_the_ceiling_is_out(self):
        from scripts.n1_band_book import band_filter
        cells = {("OK", "2020-01-15"): 9e6}
        f = band_filter(cells, 5e9, 5e6)
        self.assertEqual(f([{"ticker": "OK", "market_cap": 5e9}], "2020-01-15"), [])

    def test_a_nan_market_cap_is_excluded_rather_than_treated_as_small(self):
        from scripts.n1_band_book import band_filter
        cells = {("OK", "2020-01-15"): 9e6}
        f = band_filter(cells, 5e9, 5e6)
        self.assertEqual(f([{"ticker": "OK", "market_cap": float("nan")}], "2020-01-15"), [])


class TheCensusPopulationIsKeptSeparate(unittest.TestCase):
    def test_census_eligible_counts_RAW_rows_and_honours_skipped_dates(self):
        """THE CROSS-SECTION IS DELIBERATELY WIDER THAN ANY PLAUSIBLE TRUNCATION, and the
        eligible names sit at the END of it. The first cut of this test used 3 rows per date, so
        a mutation truncating the census population to `.head(10)` changed nothing and the guard
        could not see it -- found by mutation, not by reading. A fixture smaller than the defect
        it is meant to catch is not a fixture."""
        from scripts.n1_band_book import census_eligible
        n = 30
        ticks = ["T%02d" % i for i in range(n)]
        # only the LAST three names are small enough to qualify
        caps = [9e9] * (n - 3) + [1e9, 1e9, 1e9]
        p = pd.DataFrame({"date": ["2020-01-15"] * n + ["2020-04-15"] * n,
                          "ticker": ticks * 2, "market_cap": caps * 2})
        cells = {}
        for t in ticks[-3:]:
            cells[(t, "2020-01-15")] = 9e6
            cells[(t, "2020-04-15")] = 9e6
        cells[(ticks[-1], "2020-01-15")] = 1e6          # one below the floor on the first date
        out = census_eligible(p, cells, 5e9, 5e6)
        self.assertEqual([(o["date"], o["eligible"]) for o in out],
                         [("2020-01-15", 2), ("2020-04-15", 3)],
                         "a truncated population would read 0 here")
        out2 = census_eligible(p, cells, 5e9, 5e6, skip_dates=("2020-04-15",))
        self.assertEqual(len(out2), 1)

    def test_the_two_populations_are_reported_under_different_keys(self):
        src = _src(N1)
        self.assertIn("eligible_raw_rows", src)
        self.assertIn("eligible_scored_rows", src)
        self.assertIn("RAW panel rows -- the CENSUS's definition", src)


class ItIsADescriptionAndTakesNoVerdict(unittest.TestCase):
    def test_the_script_declares_zero_trials_and_no_verdict(self):
        src = _src(N1)
        self.assertIn('"trials": 0', src)
        self.assertIn("no_verdict", src)
        self.assertIn("ZERO TRIALS", src)

    def test_no_return_is_compared_to_a_threshold(self):
        """A description has no bar. Any `>=` or `>` against a return-shaped name would be one."""
        tree = ast.parse(_src(N1))
        for n in ast.walk(tree):
            if not isinstance(n, ast.Compare):
                continue
            s = ast.unparse(n)
            if any(k in s for k in ("roth_net_ann", "net_vs_spy", "alpha_ann", "gross_ann")):
                self.fail("a return is compared to something: %s" % s)

    def test_the_intercept_is_not_called_alpha(self):
        # NORMALISED. The phrase is hard-wrapped across two string literals in the source, so a
        # raw substring search fails against a correct tree -- the same defect this record has
        # now hit three times, twice in my own guards.
        src = " ".join(_src(N1).replace('"', " ").split())
        self.assertIn("not called alpha", src)
        self.assertIn("no_alpha_verdict", _src(N1))

    def test_the_memo_marks_N1_as_not_one_of_the_three_options(self):
        s = " ".join(_src(MEMO).split())
        self.assertIn("N1 is NOT one of the three options", s)
        self.assertIn("DESCRIPTION at zero trials", s)
        self.assertIn("not measured", s, "the un-measured cells must say so")

    def test_the_memo_carries_the_size_bet_caveat(self):
        s = " ".join(_src(MEMO).split())
        self.assertIn("SMB", s)
        self.assertIn("size bet", s.lower())
        self.assertIn("80%-power detection threshold", s)
        self.assertIn("16.78 pp/yr", s, "the tracking error must be in the memo")


class ImportingDoesNotRequireLicensedData(unittest.TestCase):
    def test_the_module_level_data_root_uses_the_non_raising_form(self):
        tree = ast.parse(_src(N1))
        found = False
        for n in tree.body:
            if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "DATA" for t in n.targets):
                found = True
                kw = {k.arg: getattr(k.value, "value", None) for k in n.value.keywords}
                self.assertIs(kw.get("required"), False)
        self.assertTrue(found)

    def test_main_refuses_loudly_when_the_panel_is_absent(self):
        s = _src(N1)
        self.assertIn("if not FA:", s)
        self.assertIn("the licensed panel is absent", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
