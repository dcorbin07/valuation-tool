# -*- coding: utf-8 -*-
"""`POOL-SIZE` — the decision rule, the gates, and the four things that must not happen.

The rule came from Don and was fixed in `PREREG_pool_size.md` §1 before any number. Most of this
file pins the parts of it that have a wrong reading available:

  * **the drawdown SIGN.** Drawdowns are negative, so "not more than 3pp worse" is
    `dd(k) >= dd(k-1) - 0.03`. `S10`'s first cut reported a 2.61pp WORSENING as an IMPROVEMENT by
    flipping exactly this, so it is pinned with a case that fails under the flipped form.
  * **the 3pp allowance.** Pre-committed; `W-28` forbids moving a bar after watching it fail.
  * **both readings.** Literal (primary) and cumulative (sensitivity) are computed and reported;
    the literal one is the answer. They DISAGREED on the 2009-2026 ladder, which is exactly the
    case §1 existed for.
  * **arm 7's level stays off the ladder**, and **part (b) never claims the shipped composite.**
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from scripts import pool_size as PS                                       # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fa():
    for c in (os.environ.get("VALQUO_DATA_ROOT"), os.path.join(REPO, "data"),
              r"C:\Users\donni\Downloads\valuation-tool\data"):
        if c and os.path.isdir(os.path.join(c, "free_analysis")):
            return os.path.join(c, "free_analysis")
    return None


def _rung(ret, dd):
    return {"roth_net_ann": ret, "roth_max_drawdown": dd}


class TheDrawdownSignIsRight(unittest.TestCase):
    """`S10`'s defect, pinned from both directions."""

    def test_a_worse_drawdown_beyond_the_allowance_FAILS(self):
        sc = {"a": _rung(0.10, -0.20), "b": _rung(0.20, -0.26)}      # 6pp worse
        d = PS.decide(["a", "b"], sc)
        self.assertFalse(d["steps"][0]["drawdown_within_3pp"])
        self.assertEqual(d["recommended_LITERAL_primary"], "a")

    def test_a_worse_drawdown_INSIDE_the_allowance_clears(self):
        sc = {"a": _rung(0.10, -0.20), "b": _rung(0.20, -0.22)}      # 2pp worse
        d = PS.decide(["a", "b"], sc)
        self.assertTrue(d["steps"][0]["drawdown_within_3pp"])
        self.assertEqual(d["recommended_LITERAL_primary"], "b")

    def test_an_IMPROVED_drawdown_always_clears(self):
        sc = {"a": _rung(0.10, -0.26), "b": _rung(0.20, -0.20)}
        d = PS.decide(["a", "b"], sc)
        self.assertTrue(d["steps"][0]["drawdown_within_3pp"])

    def test_the_reported_delta_is_POSITIVE_when_the_drawdown_IMPROVES(self):
        """A sign error here is how a worsening gets written up as a gain."""
        sc = {"a": _rung(0.10, -0.26), "b": _rung(0.20, -0.20)}
        self.assertGreater(PS.decide(["a", "b"], sc)["steps"][0]["d_drawdown_pp"], 0)
        sc2 = {"a": _rung(0.10, -0.20), "b": _rung(0.20, -0.26)}
        self.assertLess(PS.decide(["a", "b"], sc2)["steps"][0]["d_drawdown_pp"], 0)

    def test_the_exact_2009_2026_step_that_failed_is_reproduced(self):
        """Measured: 500 -> 1,000 worsens drawdown by 5.50pp and is the ONLY failing step."""
        sc = {"a": _rung(0.1719, -0.2024), "b": _rung(0.1902, -0.2574)}
        st = PS.decide(["a", "b"], sc)["steps"][0]
        self.assertTrue(st["return_not_lower"])
        self.assertFalse(st["drawdown_within_3pp"])
        self.assertAlmostEqual(st["d_drawdown_pp"], -5.50, places=1)


class TheReturnClauseHasNoTolerance(unittest.TestCase):
    def test_an_exactly_equal_return_counts_as_NOT_LOWER(self):
        sc = {"a": _rung(0.20, -0.20), "b": _rung(0.20, -0.20)}
        self.assertTrue(PS.decide(["a", "b"], sc)["steps"][0]["return_not_lower"])

    def test_a_hair_lower_return_FAILS_rather_than_being_tolerated(self):
        """A tolerance would be an invented bar; V2G/R1-VAR hold that no calibrated floor
        exists for a paired within-panel difference."""
        sc = {"a": _rung(0.20, -0.20), "b": _rung(0.20 - 1e-12, -0.20)}
        self.assertFalse(PS.decide(["a", "b"], sc)["steps"][0]["return_not_lower"])


class BothReadingsAreReported(unittest.TestCase):
    def test_they_can_disagree_and_the_literal_one_is_the_answer(self):
        """The 2009-2026 shape: step 2 fails, later steps clear."""
        sc = {"a": _rung(0.10, -0.20), "b": _rung(0.11, -0.30),
              "c": _rung(0.20, -0.31)}
        d = PS.decide(["a", "b", "c"], sc)
        self.assertEqual(d["recommended_LITERAL_primary"], "c")
        self.assertEqual(d["recommended_CUMULATIVE_sensitivity"], "a")
        self.assertFalse(d["readings_agree"])

    def test_they_agree_when_every_step_clears(self):
        sc = {"a": _rung(0.10, -0.20), "b": _rung(0.15, -0.21),
              "c": _rung(0.20, -0.22)}
        d = PS.decide(["a", "b", "c"], sc)
        self.assertEqual(d["recommended_LITERAL_primary"], "c")
        self.assertTrue(d["readings_agree"])

    def test_the_rule_CAN_recommend_the_smallest_pool(self):
        """Pre-committed as reachable, so a fall-through is a result and not a bug."""
        sc = {"a": _rung(0.20, -0.20), "b": _rung(0.10, -0.40)}
        self.assertEqual(PS.decide(["a", "b"], sc)["recommended_LITERAL_primary"], "a")


class ThePreCommittedBarIsNotMoved(unittest.TestCase):
    def test_the_allowance_is_three_percentage_points(self):
        self.assertEqual(PS.DD_ALLOWANCE, 0.03)

    def test_the_register_states_it_and_exists(self):
        p = os.path.join(REPO, "PREREG_pool_size.md")
        self.assertTrue(os.path.exists(p))
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("3pp", src)
        self.assertIn("W-28", src)


class C1GatesAndCannotPassVacuously(unittest.TestCase):
    def test_an_absent_artifact_refuses_with_nothing_compared(self):
        import tempfile
        g = PS.c1_gate(tempfile.mkdtemp(), {})
        self.assertFalse(g["ok"])
        self.assertEqual(g["compared"], 0)

    def test_a_moved_banked_figure_refuses(self):
        import tempfile
        d = tempfile.mkdtemp()
        arms = {"1_incumbent_10bn": dict(PS.BANKED["1_incumbent_10bn"]),
                "2_liquid_decile": dict(PS.BANKED["4_top1500"]),
                "4_all_cap_ceiling": dict(PS.BANKED["6_full_panel"])}
        arms["1_incumbent_10bn"]["roth_net_ann"] = 0.9
        json.dump({"arms": arms}, io.open(os.path.join(d, "INDEX_BEST.json"), "w",
                                          encoding="utf-8"))
        scored = {k: dict(v) for k, v in PS.BANKED.items()}
        g = PS.c1_gate(d, scored)
        self.assertFalse(g["ok"])

    def test_an_EMPTY_comparison_refuses_rather_than_scoring_a_perfect_zero(self):
        """`MB21`'s `C1` once scored a perfect 0.000e+00 on an empty frame by comparing nothing.

        FOUND BY MUTATION: removing `compared > 0` from the gate did NOT fail this class,
        because the absent-artifact case already returns `ok: False` by another route. The
        dangerous case is a comparison that RUNS and compares nothing — `worst` stays 0.0 and a
        gate without the count reads that as a pass. Reproduced by emptying the banked set.
        """
        import tempfile
        d = tempfile.mkdtemp()
        json.dump({"arms": {}}, io.open(os.path.join(d, "INDEX_BEST.json"), "w",
                                        encoding="utf-8"))
        real = PS.BANKED
        PS.BANKED = {}
        try:
            g = PS.c1_gate(d, {})
        finally:
            PS.BANKED = real
        self.assertEqual(g["compared"], 0)
        self.assertFalse(g["ok"], "a gate that compared NOTHING must not pass")

    def test_the_quoted_literals_match_the_real_banked_artifact(self):
        """A quoted constant that has drifted from the artifact is worse than none."""
        fa = _fa()
        if not fa or not os.path.exists(os.path.join(fa, "INDEX_BEST.json")):
            self.skipTest("LOUD SKIP: INDEX_BEST.json is not on this machine")
        arms = json.load(io.open(os.path.join(fa, "INDEX_BEST.json"),
                                 encoding="utf-8"))["arms"]
        for rung, want in PS.BANKED.items():
            got = arms[PS.BANKED_AS[rung]]
            for k, v in want.items():
                self.assertEqual(float(got[k]), float(v), "%s/%s drifted" % (rung, k))


class TheLadderIsCapRankedAndSaysSo(unittest.TestCase):
    def test_the_rungs_use_universe_rank_and_the_incumbent_uses_a_tier_floor(self):
        kw = dict(PS.RUNGS)
        self.assertEqual(kw["1_incumbent_10bn"]["large_cap_min"], 1e10)
        self.assertIsNone(kw["1_incumbent_10bn"]["universe_rank"])
        self.assertEqual([kw["2_top500"]["universe_rank"], kw["3_top1000"]["universe_rank"],
                          kw["4_top1500"]["universe_rank"], kw["5_top2000"]["universe_rank"]],
                         [500, 1000, 1500, 2000])
        self.assertIsNone(kw["6_full_panel"]["universe_rank"])

    def test_the_script_records_that_most_liquid_is_really_a_CAP_rank(self):
        src = io.open(os.path.join(REPO, "scripts", "pool_size.py"), encoding="utf-8").read()
        self.assertIn("CAP-RANKED", src)
        self.assertIn("market cap", src)


class Arm7IsAPairedDeltaNotARung(unittest.TestCase):
    def test_arm_7_is_absent_from_the_main_ladder(self):
        self.assertNotIn("7", "".join(n[0] for n in PS.RUNGS))
        for name, _ in PS.RUNGS:
            self.assertNotIn("prefilter", name)

    def test_its_runner_declares_the_paired_class_and_pins_one_vintage(self):
        src = io.open(os.path.join(REPO, "scripts", "pool_size_arm7.py"),
                      encoding="utf-8").read()
        self.assertIn("PAIRED", src)
        self.assertIn("backtest_freeze_2026-08", src)
        self.assertIn("void condition", src.lower())

    def test_its_artifact_reports_the_delta_and_the_name_count(self):
        fa = _fa()
        p = os.path.join(fa or "", "POOL_SIZE_ARM7.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: arm 7 artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertIn("d_return_pp", d["paired"])
        self.assertIn("d_names", d["paired"])
        self.assertIn("PAIRED", d["class"])


class PartBIsLabelledAndNeverClaimsTheShippedComposite(unittest.TestCase):
    def test_it_scores_FIVE_themes_and_names_the_two_it_cannot(self):
        from scripts import pool_size_oos as OOS
        self.assertEqual(len(OOS.THEMES_PRE2009), 5)
        self.assertNotIn("institutional", OOS.THEMES_PRE2009)
        self.assertNotIn("insider", OOS.THEMES_PRE2009)

    def test_it_is_built_from_the_raw_freeze_and_NOT_from_data_backtest(self):
        """`data/backtest` is selected on 2026 size -- using it would be B6 in a new costume."""
        src = io.open(os.path.join(REPO, "scripts", "pool_size_oos.py"),
                      encoding="utf-8").read()
        self.assertIn("oos1999", src)
        prep = io.open(os.path.join(REPO, "scripts", "pool_size_oos_prep.py"),
                       encoding="utf-8").read()
        self.assertIn("SHARADAR_SEP_", prep)
        self.assertIn("SHARADAR_SF1_", prep)

    def test_the_prep_does_NOT_overwrite_the_shared_bulk_caches(self):
        """Rebuilding them would be a second copy; OVERWRITING them would break every
        2009-2026 panel build in the repo."""
        prep = io.open(os.path.join(REPO, "scripts", "pool_size_oos_prep.py"),
                       encoding="utf-8").read()
        tree = ast.parse(prep)
        writes = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)
                  and n.value.endswith(".pkl")]
        self.assertEqual(writes, [], "the prep must write no pickle cache at all")
        self.assertIn("NOT rebuilt and NOT overwritten", prep)

    def test_the_benchmark_comes_from_SFP_because_SPY_is_not_in_SEP(self):
        prep = io.open(os.path.join(REPO, "scripts", "pool_size_oos_prep.py"),
                       encoding="utf-8").read()
        self.assertIn("SHARADAR_SFP_", prep)
        self.assertIn("prep_benchmark", prep)

    def test_its_artifact_carries_the_five_theme_label(self):
        fa = _fa()
        p = os.path.join(fa or "", "POOL_SIZE_OOS.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: part (b) artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertIn("NOT A TEST OF THE SHIPPED COMPOSITE", d["LABEL"])
        self.assertEqual(len(d["themes_scored"]), 5)
        self.assertTrue(d["read_once"])
        self.assertIn("1990-2008", d["holdout_spent"])


class NoX7FloorIsQuoted(unittest.TestCase):
    def test_no_calibrated_floor_appears_in_any_pool_size_script(self):
        """X7 calibrates LEVELS; every comparison here is a paired within-panel difference, for
        which `V2G` and `R1-VAR` establish there is no calibrated floor."""
        floors = ("2.2837", "2.0540", "2.7072", "19.667", "1.8629")
        for f in ("pool_size.py", "pool_size_diag.py", "pool_size_factors.py",
                  "pool_size_arm7.py", "pool_size_oos.py", "pool_size_oos_prep.py"):
            src = io.open(os.path.join(REPO, "scripts", f), encoding="utf-8").read()
            for fl in floors:
                self.assertNotIn(fl, src, "%s quotes the X7 floor %s" % (f, fl))

    def test_the_paired_statistic_labels_its_critical_value_uncalibrated(self):
        out = PS._paired([0.01, 0.02, -0.01, 0.03, 0.00, 0.02],
                         [0.00, 0.01, -0.02, 0.01, 0.00, 0.01])
        self.assertIsNotNone(out)
        self.assertIn("UNCALIBRATED", out["crit_LABEL"])
        self.assertIn("mde_50pc", out)
        self.assertIn("mde_80pc", out)
        self.assertGreater(out["mde_80pc"], out["mde_50pc"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
