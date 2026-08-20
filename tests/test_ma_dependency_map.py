#!/usr/bin/env python3
"""Tests for scripts/ma_dependency_map.py and the artifacts it generates.

The point of these is the first one: the map is generated, so it can go stale
silently the moment the items file moves. Audit #1's map closed by warning about
exactly that and had no check. This one has a check, and the check is tested.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.ma_dependency_map import (  # noqa: E402
    LANE_OVERRIDE, LANES, SEVERITY_OVERRIDE, TIE_ORDER, lane_of_file, main, norm,
)

EDGES = ROOT / "ma_dependency_edges.json"
MD = ROOT / "MA_DEPENDENCY_MAP.md"
PASSED = FAILED = 0


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(EDGES.read_text(encoding="utf-8"))
        cls.n = cls.d["nodes"]

    # ------------------------------------------------------------ freshness
    def test_the_committed_artifacts_are_current_against_the_items_file(self):
        """If this fails the items file moved and the map was not regenerated:
            python scripts/ma_dependency_map.py"""
        self.assertEqual(main(["--check"]), 0)

    def test_both_artifacts_exist(self):
        self.assertTrue(EDGES.exists() and MD.exists())

    # ------------------------------------------------------------ completeness
    def test_every_item_has_a_lane_a_wave_and_a_reason(self):
        for k, v in self.n.items():
            self.assertIn(v["lane"], LANES, k)
            self.assertIn(v["wave"], (0, 1, 2, 3), k)
            self.assertTrue(v["wave_reason"], k)

    def test_the_waves_partition_the_catalogue(self):
        """Every item in exactly one wave - the failure mode the brief's own rule had,
        where a CRITICAL item with a dependency belonged to no wave at all."""
        seen = [k for w in (0, 1, 2, 3) for k in self.n if self.n[k]["wave"] == w]
        self.assertEqual(sorted(seen), sorted(self.n))
        self.assertEqual(len(seen), len(set(seen)))

    def test_wave_one_is_top_severity_only(self):
        for k, v in self.n.items():
            if v["wave"] == 1:
                self.assertIn(v["severity"], ("CRITICAL", "HIGH"), k)

    def test_no_wave_one_item_waits_on_anything_except_a_deploy_edge(self):
        deploy = {(e["from"], e["needs"]) for e in self.d["edges"]
                  if e.get("scope") == "deploy"}
        for k, v in self.n.items():
            if v["wave"] == 1:
                for need in v["needs_first"]:
                    self.assertIn((k, need), deploy,
                                  f"{k} is in wave 1 but waits on {need}")

    # ------------------------------------------------------------ the deploy edge
    def test_a_deploy_edge_does_not_gate_a_wave(self):
        """MA15/MA16 need MA20 only for the code to REACH Don's machine. Letting that
        gate the wave would say the backup fix cannot be written until the checkout is
        synced, which is backwards - it is written, and syncing is what deploys it."""
        for k in ("MA15", "MA16"):
            self.assertEqual(self.n[k]["wave"], 1, k)
            self.assertIn("MA20", self.n[k]["needs_first"], k)

    def test_edges_never_point_at_an_item_that_does_not_exist(self):
        for e in self.d["edges"]:
            self.assertIn(e["from"], self.n)
            self.assertIn(e["needs"], self.n)
            self.assertTrue(e["reason"])

    def test_no_item_depends_on_itself_and_there_is_no_two_cycle(self):
        pairs = {(e["from"], e["needs"]) for e in self.d["edges"]}
        for a, b in pairs:
            self.assertNotEqual(a, b)
            self.assertNotIn((b, a), pairs, f"{a} and {b} each wait on the other")

    # ------------------------------------------------------------ collisions
    def test_collisions_are_computed_from_files_not_modifies(self):
        """All 25 Pass B items ship an empty `modifies`. Using it would report zero
        collisions for nearly half the catalogue and read as a clean map."""
        passb = [k for k in self.n if int(k[2:]) >= 36]
        self.assertTrue(passb)
        involved = {c["a"] for c in self.d["collisions"]} | {c["b"] for c in self.d["collisions"]}
        self.assertTrue(involved & set(passb),
                        "no Pass B item collides with anything - collisions came from modifies")

    def test_every_collision_names_the_files_that_cause_it(self):
        for c in self.d["collisions"]:
            self.assertIn(c["kind"], ("hard-file", "soft-import"))
            self.assertTrue(c["files"])

    def test_the_panel_is_still_the_bottleneck(self):
        """Not a style check: if this stops being true, the lane design changes."""
        panel = [k for k, v in self.n.items()
                 if "valuation/edge/fundamental_panel.py" in v["files"]]
        self.assertGreaterEqual(len(panel), 8)

    # ------------------------------------------------------------ overrides visible
    def test_every_severity_override_records_what_it_overrode(self):
        for k in SEVERITY_OVERRIDE:
            self.assertIn(k, self.d["severity_overrides"])
            row = self.d["severity_overrides"][k]
            self.assertNotEqual(row["applied"], row["was"])
            self.assertTrue(row["why"])
            self.assertEqual(self.n[k]["severity"], row["applied"])
            self.assertEqual(self.n[k]["severity_as_written"], row["was"])

    def test_lane_overrides_are_applied_and_carry_a_reason(self):
        for k, (lane, why) in LANE_OVERRIDE.items():
            if k in self.n:
                self.assertEqual(self.n[k]["lane"], lane, k)
                self.assertEqual(self.n[k]["lane_evidence"], why, k)

    def test_the_backup_items_are_infra_not_pipeline(self):
        """They were mis-assigned by file count: the scripts/ paths in their `files` are
        where the DATA is read, not where the change is made."""
        for k in ("MA15", "MA16"):
            self.assertEqual(self.n[k]["lane"], "infra", k)

    # ------------------------------------------------------------ helpers
    def test_norm_strips_line_numbers_and_parentheticals(self):
        self.assertEqual(norm("valuation/web/app.py:519"), "valuation/web/app.py")
        self.assertEqual(norm("valuation/screener/screen.py:51-55,305"),
                         "valuation/screener/screen.py")
        self.assertEqual(norm("data/options (raw chains)"), "data/options")
        self.assertEqual(norm("backup_to_D.ps1 ($KEEP, $SKIP)"), "backup_to_D.ps1")

    def test_norm_drops_a_trailing_field_reference(self):
        """A false NEGATIVE in a collision map is the dangerous direction. Three items name
        BACKTEST_RESULTS.json and two qualify it with the block they mean; unnormalised they
        become three distinct strings and the map reports no collision at all."""
        self.assertEqual(norm("BACKTEST_RESULTS.json cpcv.adopt_detail"),
                         "BACKTEST_RESULTS.json")
        self.assertEqual(norm("BACKTEST_RESULTS.json multiple_testing.hlz"),
                         "BACKTEST_RESULTS.json")
        # ...but a prose entry that is not a path must survive intact.
        self.assertEqual(norm("owned daily closes (screener/prices)"), "owned daily closes")

    def test_the_items_that_share_a_results_file_do_collide(self):
        for f, expect in (("BACKTEST_RESULTS.json", {"MA5", "MA19", "MA21"}),
                          ("RESEARCH_LOG.md", {"MA6", "MA13", "MA54", "MA56"})):
            who = {k for k, v in self.n.items() if f in v["files"]}
            self.assertEqual(who, expect, f)
            pairs = {frozenset((c["a"], c["b"])) for c in self.d["collisions"]
                     if c["kind"] == "hard-file" and f in c["files"]}
            self.assertGreaterEqual(len(pairs), 3, f"{f} collisions not reported")

    def test_an_options_file_under_edge_belongs_to_the_options_lane(self):
        """Path prefix alone would file every options module under the edge lane."""
        self.assertEqual(lane_of_file("valuation/edge/options_tracker.py"), "options-bot")
        self.assertEqual(lane_of_file("valuation/edge/blackscholes.py"), "options-bot")
        self.assertEqual(lane_of_file("valuation/edge/fundamental_panel.py"), "pipeline")

    def test_research_log_is_the_edge_lanes_not_a_doc(self):
        """It is the trial counter. Filing it under docs sent two research items to infra."""
        self.assertEqual(lane_of_file("RESEARCH_LOG.md"), "pipeline")
        self.assertEqual(lane_of_file("CLAUDE.md"), "infra")

    def test_tie_order_covers_every_lane(self):
        self.assertEqual(sorted(TIE_ORDER), sorted(LANES))

    # ------------------------------------------------------------ in-flight
    #
    # THESE TWO TESTS USED TO READ `ma_in_flight.json` AND ASSERT THE MAP FLAGGED EVERY
    # CLAIMED ITEM. MB27 (2026-08-19) retired that file -- measured five days stale and
    # wrong on 8 of 8 items -- and the retirement immediately staled this map's committed
    # artifact, which is how the coupling was found at all. That is the finding, not an
    # inconvenience: **a committed artifact cannot carry live board state**, because a
    # branch moving makes it wrong and the staleness check then fires on ordinary work.
    #
    # Left as-is they would have passed VACUOUSLY: the retired stub's only non-`_meta` key
    # is `_retired_2026_08_14`, which is not an MA id, so both loops iterate nothing. A
    # green test that inspects nothing is the failure mode this repo keeps finding, so they
    # are replaced by two that pin the new contract and cannot go stale.

    def test_the_map_embeds_no_live_board_state(self):
        """The artifact is derived from the items file and the import graph, and nothing
        that moves when a branch moves."""
        for k, v in self.n.items():
            self.assertNotIn("in_flight", v, f"{k} still carries embedded board state")
        self.assertNotIn("IN FLIGHT]**", MD.read_text(encoding="utf-8"))

    def test_the_map_points_at_the_derivation_and_records_the_correction(self):
        """A map that routes a claimed item to a second lane is worse than no map -- so
        the guarantee moves to a COMMAND that cannot be stale, and the map must say so."""
        txt = MD.read_text(encoding="utf-8")
        self.assertIn("Corrections this map makes to its own brief", txt)
        self.assertIn("scripts/board_state.py", txt)
        # And it must not go on advertising the retired file as the live authority.
        flat = " ".join(txt.split())
        self.assertNotIn("`ma_in_flight.json` | what is being worked RIGHT NOW", flat)

    def test_the_retired_board_file_is_not_read_by_the_generator(self):
        """One copy of the fact, and it is git."""
        src = (ROOT / "scripts" / "ma_dependency_map.py").read_text(encoding="utf-8")
        # NAME THE READ, NOT THE FILENAME. A first cut stripped comment lines and asserted
        # the bare filename was absent -- and failed against the FIXED tree, because the
        # generator now emits a paragraph of prose ABOUT the retired file into the map. That
        # is the comment-versus-code family inverted: documentation inside a string literal
        # reads as code to a line filter. The only thing that matters is whether it opens it.
        self.assertNotIn('ROOT / "ma_in_flight.json"', src)
        self.assertNotIn("ROOT / 'ma_in_flight.json'", src)


def run():
    global PASSED, FAILED
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestLoader().loadTestsFromTestCase(T))
    PASSED = r.testsRun - len(r.failures) - len(r.errors)
    FAILED = len(r.failures) + len(r.errors)
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
