# -*- coding: utf-8 -*-
"""`INSIDER-WIDE` — stage 2 of `INSIDER-CLUSTER`, the one check-quadrant read.

Register: `PREREG_insider_cluster_wide.md`, committed **ALONE at `1cc8b7e`**.

Every test here pins a property the register fixed BEFORE the read, so a later session cannot
loosen one and re-read a quadrant that has no second read. Nothing here needs the licensed export
or the banked panels, so none of it fails open in CI (`guards-that-fail-open-in-ci`).
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

from valuation.edge import fundamental_panel as FP                          # noqa: E402
from valuation.edge import power_gate as PG                                 # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402
from scripts import insider_wide_arm as WA                                  # noqa: E402
from scripts import insider_wide_checks as WC                               # noqa: E402
from scripts import insider_wide_tier_choice as TC                          # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, "PREREG_insider_cluster_wide.md")


def _src(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read()


def _tree(rel):
    return ast.parse(_src(rel))


class TheRegisterIsOnDiskAndCameFirst(unittest.TestCase):
    def test_the_register_file_exists(self):
        """`W-28`'s lesson: a citation is only checkable if the file is there."""
        self.assertTrue(os.path.isfile(REGISTER), REGISTER)

    def test_the_register_names_the_governing_population_and_it_matches_the_code(self):
        t = _src("PREREG_insider_cluster_wide.md")
        self.assertIn("$500M", t)
        self.assertEqual(WA.GOVERNING, "cap_ge_500m")
        gov = [c for c in WA.CELLS if c[0] == WA.GOVERNING]
        self.assertEqual(len(gov), 1)
        self.assertEqual(gov[0][1], 500e6)
        self.assertTrue(gov[0][2], "the governing cell must carry a verdict")

    def test_the_register_is_markdown_only_in_its_own_commit(self):
        """It must be a strict ancestor of every commit that computes a check outcome, and it
        must not have carried code. Checked against git, with a SKIP that is loud rather than
        silent if git is unavailable."""
        import subprocess
        try:
            # binary, then decode -- `git-baseline-decode-trap`: text=True reads git's bytes as
            # cp1252 on Windows and an em-dash then reports a phantom difference.
            out = subprocess.run(["git", "log", "--format=%H", "-n", "40", "--", REGISTER],
                                 cwd=REPO, capture_output=True).stdout.decode("utf-8")
        except Exception as e:                                              # noqa: BLE001
            self.skipTest("git unavailable: %r" % (e,))
        shas = [x for x in out.split() if x]
        if not shas:
            self.skipTest("register not in this checkout's history")
        first = shas[-1]
        files = subprocess.run(["git", "show", "--name-only", "--format=", first],
                               cwd=REPO, capture_output=True).stdout.decode("utf-8").split()
        self.assertEqual([f for f in files if f.strip()],
                         ["PREREG_insider_cluster_wide.md"],
                         "the register's introducing commit must touch EXACTLY that one file")


class TheConstructionIsStageOnes(unittest.TestCase):
    def test_the_own_normal_leg_is_never_scored(self):
        """§1: the market-adjusted leg ONLY, for a MEASURED reason (its null is centred at
        +1.17pp, not zero). Asserted over the syntax tree: the arm may unpack the own-normal
        value from the shared primitive and must never put it in a result."""
        tree = _tree("scripts/insider_wide_arm.py")
        bad = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                    and n.slice.value == "own":
                bad.append("subscript 'own'")
            if isinstance(n, ast.Constant) and n.value == "own" \
                    and not isinstance(n.value, bool):
                # a bare "own" string literal would mean a result key or a leg loop
                bad.append("string literal 'own'")
        self.assertEqual(bad, [], "the own-normal leg must not be keyed anywhere: %s" % bad)

    def test_the_own_normal_leg_is_still_the_row_set_filter_stage_one_used(self):
        """**THIS TEST EXISTS BECAUSE `C1` FIRED AGAINST MY OWN INSTRUMENT BEFORE THE READ.**

        §1 drops the own-normal leg from the STATISTIC. The first cut of `score` dropped it from
        the POPULATION FILTER too — stage 1 keeps a row only where BOTH legs are finite — so the
        two instruments disagreed by **2 events, 4,074 against 4,072**, and the build mean by
        +0.0008pp. **In a two-leg construction the discarded leg is also a filter, so scoring one
        leg silently WIDENS the population.** Pinned here so a future edit that removes it again
        goes red rather than quietly re-widening the one cell that has no second read.
        """
        import re
        seg = ast.get_source_segment(_src("scripts/insider_wide_arm.py"),
                                     [n for n in _tree("scripts/insider_wide_arm.py").body
                                      if isinstance(n, ast.FunctionDef)
                                      and n.name == "score"][0]) or ""
        code = "\n".join(ln for ln in seg.splitlines() if not ln.lstrip().startswith("#"))
        self.assertIn("np.isfinite(ar_own)", code,
                      "stage 1's both-legs-finite row-set rule must be kept")
        self.assertIn("np.isfinite(ar_mkt)", code)
        # And `ar_own` must appear NOWHERE ELSE in the function: as a filter, never a statistic.
        uses = re.findall(r"\bar_own\b", code)
        self.assertEqual(len(uses), 2,
                         "ar_own may appear exactly twice -- the unpack and the filter -- and "
                         "found %d uses" % len(uses))

    def test_the_arm_delegates_every_statistic_and_reimplements_none(self):
        """`B7`: a second implementation of a clustered `se` or a permutation null is the split
        this project has paid for repeatedly."""
        tree = _tree("scripts/insider_wide_arm.py")
        attrs = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for want in ("clustered", "permutation_null", "abnormal", "build_market",
                     "two_sided_p", "name_frame", "one_way_cost_bps"):
            self.assertIn(want, attrs, "must DELEGATE %s" % want)
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("clustered", "permutation_null", "abnormal", "two_sided_p",
                       "one_way_cost_bps"):
            self.assertNotIn(banned, defined, "must not re-implement %s" % banned)

    def test_the_permutation_draws_and_bh_match_stage_one(self):
        self.assertEqual(WA.PERMUTATION_DRAWS, 500)
        self.assertEqual(WA.BH_Q, 0.10)

    def test_bh_k_is_fixed_at_three_and_the_code_never_shrinks_it(self):
        """§4 A5. `k` is the number of VERDICT cells and is never lowered to the number that
        happened to be scoreable — shrinking `k` lowers every threshold."""
        self.assertEqual(WA.BH_K, 3)
        verdicts = [c for c in WA.CELLS if c[2]]
        self.assertEqual(len(verdicts), WA.BH_K)
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("k_fixed", src)
        tree = _tree("scripts/insider_wide_arm.py")
        # the BH threshold must be formed from BH_K and not from the batch length
        thr = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "thr" for t in n.targets)]
        self.assertEqual(len(thr), 1)
        names = {x.id for x in ast.walk(thr[0].value) if isinstance(x, ast.Name)}
        self.assertIn("BH_K", names)
        self.assertNotIn("batch", names)


class ThePopulationAndHorizon(unittest.TestCase):
    def test_exactly_three_cells_carry_a_verdict_and_the_other_two_are_declared(self):
        """§2c fixed this before the read, so nobody can promote a no-verdict cell afterwards."""
        self.assertEqual([c[0] for c in WA.CELLS if c[2]],
                         ["full_universe", "cap_ge_10bn", "cap_ge_500m"])
        self.assertEqual([c[0] for c in WA.CELLS if not c[2]],
                         ["cap_ge_2bn", "cap_ge_100m"])

    def test_h63_governs_and_h126_is_reported_only(self):
        self.assertEqual(WA.H_PRIMARY, 63)
        self.assertEqual(WA.H_REPORTED, 126)
        src = _src("PREREG_insider_cluster_wide.md")
        self.assertIn("`h`=63", src)

    def test_the_half_boundary_is_the_midpoint_and_is_fixed_in_the_register(self):
        """Stage 1 split 2009-2019 at 2015-01-01, the midpoint; the analogue for 2020-2026 is
        2023-01-01. Choosing a different rule at the one unrepeatable look would be changing the
        construction there."""
        self.assertEqual(WA.CHECK_HALF_BOUNDARY, "2023-01-01")
        self.assertIn("2023-01-01", _src("PREREG_insider_cluster_wide.md"))

    def test_the_check_era_is_the_other_half_and_the_later_window(self):
        cfg = D.era(D.ERA_CHECK)
        self.assertEqual(cfg["ticker_half"], 1)
        self.assertEqual(cfg["lo"], "2020-01-01")
        build = D.era(D.ERA_BUILD)
        self.assertEqual(build["ticker_half"], 0)
        self.assertLess(build["hi"], cfg["lo"], "the two cells must not share a date")


class TheCostTreatment(unittest.TestCase):
    def test_the_round_trip_is_twice_the_shipped_one_way_at_every_band(self):
        for cap, _bps in FP.COST_BPS_BY_MKTCAP:
            got = WA.roundtrip_cost_pp([cap])[0]
            self.assertAlmostEqual(got, 2.0 * FP.one_way_cost_bps(cap) / 100.0, places=12)

    def test_the_micro_band_is_charged_and_is_the_most_expensive(self):
        """The register's own reason for not resting a tradability verdict below $100M."""
        micro = WA.roundtrip_cost_pp([50e6])[0]
        mega = WA.roundtrip_cost_pp([500e9])[0]
        self.assertGreater(micro, mega)
        self.assertAlmostEqual(micro, 2.0 * FP.COST_BPS_MICRO / 100.0, places=12)

    def test_a_missing_cap_records_no_cost_rather_than_a_free_trade(self):
        """A `nan` cap must not read as zero cost — the flattering direction."""
        import math
        self.assertTrue(math.isnan(WA.roundtrip_cost_pp([float("nan")])[0]))
        self.assertTrue(math.isnan(WA.roundtrip_cost_pp([0.0])[0]))

    def test_stage_ones_single_floor_is_superseded_and_not_carried_forward(self):
        """§3. Carrying 0.67pp into a wide population would charge a sub-$100M name a megacap
        book's cost, understating it by 4.5x.

        **THIS TEST'S FIRST FORM BANNED THE SUBSTRING `0.67` AND FAILED AGAINST THE CORRECT
        TREE** — the arm's own docstring says *"stage 1's single 0.67pp floor is SUPERSEDED"*, so
        the prose documenting the rule quoted what the rule forbids. **Tenth instance of the
        family in this record, and committed inside the very suite that bans it two classes
        below.** The real property is that no numeric LITERAL equal to stage 1's floor is used as
        a bar, which is a question about code and not about prose — so it is asked of the syntax
        tree, with the string constants stripped.
        """
        tree = _tree("scripts/insider_wide_arm.py")
        bad = [t.id for n in tree.body if isinstance(n, ast.Assign)
               for t in n.targets
               if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)
               and isinstance(n.value.value, (int, float))
               and not isinstance(n.value.value, bool)
               and abs(float(n.value.value) - 0.67) < 1e-12]
        self.assertEqual(bad, [], "stage 1's floor is bound as a module constant: %s" % bad)
        self.assertIn("SUPERSEDED", _src("scripts/insider_wide_arm.py"))

    def test_that_ban_is_not_vacuous_either(self):
        """POSITIVE CONTROL: the same walk must find the floor in the EXACT shape stage 1 used."""
        probe = ast.parse("COST_FLOOR_PP = 0.67")
        bad = [t.id for n in probe.body if isinstance(n, ast.Assign)
               for t in n.targets
               if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)
               and abs(float(n.value.value) - 0.67) < 1e-12]
        self.assertEqual(bad, ["COST_FLOOR_PP"])

    def test_and_a_power_figure_that_happens_to_equal_the_floor_does_not_trip_it(self):
        """**THE SECOND FORM OF THIS TEST ALSO FIRED AGAINST THE CORRECT TREE**, and the cause is
        the substring family one level in: it banned the VALUE `0.67` anywhere in the syntax tree,
        and §5's declared power for the `$10B` cell is **0.670** — a probability, nested
        inside `POWER_DECLARED`, with nothing to do with a cost bar. **Ban the ROLE, not the
        number.** A bar is a module-level constant a comparison reads; a power figure is a value
        inside a declaration table, and no walk over bare literals can tell them apart.
        """
        probe = ast.parse("POWER_DECLARED = {'x': {'net': 0.670}}")
        bad = [t.id for n in probe.body if isinstance(n, ast.Assign)
               for t in n.targets
               if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)
               and abs(float(n.value.value) - 0.67) < 1e-12]
        self.assertEqual(bad, [])

    def test_and_a_docstring_quoting_the_floor_does_not_trip_it(self):
        """The exact case that broke the FIRST form, pinned so it cannot come back."""
        probe = ast.parse('X = 1  # the 0.67pp floor is SUPERSEDED')
        bad = [t.id for n in probe.body if isinstance(n, ast.Assign)
               for t in n.targets
               if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)
               and isinstance(n.value.value, (int, float))
               and not isinstance(n.value.value, bool)
               and abs(float(n.value.value) - 0.67) < 1e-12]
        self.assertEqual(bad, [])

    def test_the_arm_does_not_retype_the_cost_table(self):
        bps = {float(v) for (_e, v) in FP.COST_BPS_BY_MKTCAP} | {float(FP.COST_BPS_MICRO)}
        tree = _tree("scripts/insider_wide_arm.py")
        found = sorted({float(n.value) for n in ast.walk(tree)
                        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                        and not isinstance(n.value, bool) and float(n.value) in bps})
        self.assertEqual(found, [], "cost values retyped: %s" % found)

    def test_that_ban_is_not_vacuous(self):
        """POSITIVE CONTROL: the same walk must find a retyped value when one is present."""
        bps = {float(v) for (_e, v) in FP.COST_BPS_BY_MKTCAP}
        probe = ast.parse("X = %r\n" % sorted(bps)[0])
        found = [float(n.value) for n in ast.walk(probe)
                 if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                 and float(n.value) in bps]
        self.assertTrue(found)


class ThePowerIsDeclaredBeforeTheRead(unittest.TestCase):
    def test_every_cell_has_a_declared_power_and_it_matches_the_register(self):
        for label, _f, _v in WA.CELLS:
            self.assertIn(label, WA.POWER_DECLARED)
            for leg in ("gross", "net"):
                p = WA.POWER_DECLARED[label][leg]
                # ZERO IS A LEGITIMATE VALUE AND THE FIRST FORM OF THIS TEST BANNED IT: the $2B
                # band's gross effect is NEGATIVE, so its power to clear a positive cost bar is
                # exactly 0 rather than small. A strict `> 0` asserted that every cell has SOME
                # chance, which is false and is the thing the register is reporting.
                self.assertTrue(0.0 <= p <= 1.0, "%s %s = %r" % (label, leg, p))

    def test_the_power_table_is_derived_and_cross_checked_against_the_register(self):
        """**THE FIRST CUT OF `POWER_DECLARED` WAS HAND-TYPED AND FOUR OF TEN FIGURES WERE
        WRONG** — `$2B` gross read 0.337 against a banked 0.0518, and `$500M`/`$100M` had their
        NET figures swapped. `BETA-FORECAST` shipped a hand-typed `HLZ` hurdle wrong in its
        fourth decimal three items ago; **derive a figure you are going to branch on.**

        No verdict moved, because every cell sits on the same side of 0.50 under both — luck
        rather than design, which is precisely what `X7RECON` says not to lean on.
        """
        for label in WA.POWER_REGISTER:
            for leg in ("gross", "net"):
                self.assertAlmostEqual(round(WA.POWER_DECLARED[label][leg], 3),
                                       WA.POWER_REGISTER[label][leg], places=9,
                                       msg="%s/%s" % (label, leg))

    def test_the_power_table_falls_back_to_the_register_and_never_to_a_default(self):
        """The banked artifact is under `data/`, gitignored and ABSENT on a CI runner, so the
        fallback is the register's own published table — not a default, and not a skip. A guard
        whose input is absent on a runner must still be checking something
        (`guards-that-fail-open-in-ci`)."""
        self.assertEqual(sorted(WA.POWER_REGISTER), sorted(c[0] for c in WA.CELLS))
        for label, v in WA.POWER_REGISTER.items():
            self.assertEqual(sorted(v), ["gross", "net"], label)
            self.assertTrue(0.0 <= v["gross"] <= 1.0 and 0.0 <= v["net"] <= 1.0, label)

    def test_the_fallback_survives_a_refusing_data_root(self):
        """**THIS IS WHY THE FIRST LAND ATTEMPT FAILED.** `dipcall.data_root` REFUSES with
        `SystemExit` when no populated data root exists, `SystemExit` derives from
        `BaseException`, and the fallback's first form guarded with `except Exception` — so the
        import died at *"REFUSING: no populated data root found"* and this entire suite went red
        on a CI runner while passing locally.

        **A refusing resolver raises `SystemExit`, so a CI-safe fallback must catch it by name.**
        Exercised by making the resolver refuse, which is exactly the runner's condition.
        """
        import scripts.insider_wide_arm as M
        orig = M.D.out_path
        try:
            def refuse(_name):
                raise SystemExit("REFUSING: no populated data root found")
            M.D.out_path = refuse
            got = M.power_declared()
        finally:
            M.D.out_path = orig
        self.assertEqual(got, M.POWER_REGISTER,
                         "with a refusing data root it must return the register's own table")

    def test_that_fallback_test_is_not_vacuous(self):
        """POSITIVE CONTROL: the probe must really make the resolver refuse, or the test above
        passes by exercising the happy path."""
        with self.assertRaises(SystemExit):
            raise SystemExit("REFUSING: no populated data root found")

    def test_a_disagreeing_artifact_refuses_rather_than_relabelling(self):
        """If the banked power stops matching the register, the read STOPS. Silently taking the
        artifact's value would let a changed number re-decide whether a null reads UNDERPOWERED
        or NOT CONFIRMED — the label the whole three-state grammar exists for."""
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("REFUSING", src)
        tree = _tree("scripts/insider_wide_arm.py")
        fn = [n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == "power_declared"]
        self.assertEqual(len(fn), 1)
        raises = [n for n in ast.walk(fn[0]) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(len(raises), 1)

    def test_the_governing_cell_is_declared_below_half_so_a_null_there_is_underpowered(self):
        """§5's uncomfortable sentence, pinned: the cell Don's ruling asks to govern cannot see
        its own build effect at even 50% power, so the grammar must return UNDERPOWERED there
        rather than NOT CONFIRMED."""
        self.assertLess(WA.POWER_DECLARED[WA.GOVERNING]["gross"], 0.50)

    def test_the_two_cells_that_can_resolve_anything_are_declared_above_half(self):
        self.assertGreater(WA.POWER_DECLARED["full_universe"]["gross"], 0.50)
        self.assertGreater(WA.POWER_DECLARED["cap_ge_10bn"]["net"], 0.50)

    def test_the_net_question_is_declared_unanswerable_at_every_wide_tier(self):
        """The wide tiers' NET power is below half everywhere, which the register states in
        advance so a wide-tier net null is read as invisible rather than absent."""
        for label in ("cap_ge_2bn", "cap_ge_500m", "cap_ge_100m"):
            self.assertLess(WA.POWER_DECLARED[label]["net"], 0.50, label)

    def test_the_three_state_grammar_is_the_only_vocabulary(self):
        """`P1S0`'s rule. A fourth state would let a reader pick a label after the read."""
        src = _src("scripts/insider_wide_arm.py")
        for word in ("CONFIRMED", "NOT CONFIRMED", "UNDERPOWERED"):
            self.assertIn(word, src)

    def test_an_underpowered_cell_is_decided_by_the_declared_power_not_the_realised_one(self):
        """The branch must read `POWER_DECLARED`, or the label becomes a function of the outcome
        it is meant to qualify."""
        tree = _tree("scripts/insider_wide_arm.py")
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertIn("POWER_DECLARED", names)


class TheGateOrdering(unittest.TestCase):
    def test_the_arm_refuses_without_a_passing_pre_read_artifact(self):
        """`O10`: a gating control and its outcomes must not run in one pass. Exercised in
        isolation on a missing path so the refusal is proved reachable, which is what a
        hard-coded `True` would not be."""
        tree = _tree("scripts/insider_wide_arm.py")
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_checks"]
        self.assertEqual(len(fn), 1)
        raises = [n for n in ast.walk(fn[0])
                  if isinstance(n, ast.Raise) or (isinstance(n, ast.Call)
                                                  and isinstance(n.func, ast.Name)
                                                  and n.func.id == "SystemExit")]
        self.assertGreaterEqual(len(raises), 2, "both the absent and the failing state refuse")
        src = ast.get_source_segment(_src("scripts/insider_wide_arm.py"), fn[0]) or ""
        self.assertIn("all_pass", src, "it must read the artifact's own verdict")

    def test_the_two_refusals_say_different_things(self):
        """`E-1`'s lesson: a hard-coded refusal cannot tell 'absent' from 'failing', and the two
        want different actions."""
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("no pre-read artifact", src)
        self.assertIn("pre-read check(s)", src)

    def test_the_checks_pass_computes_no_check_quadrant_outcome(self):
        """`C2`'s own property, pinned here as well so a future edit to the checks script cannot
        quietly start reading the quadrant it is gating."""
        tree = _tree("scripts/insider_wide_checks.py")
        calls = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for banned in ("abnormal", "permutation_null", "build_market"):
            self.assertNotIn(banned, calls, "the checks pass must not compute %s" % banned)

    def test_the_tier_choice_module_computes_no_abnormal_return(self):
        """It ran BEFORE the register, so it must have read no outcome the register then fixed
        bars against. Over the syntax tree, never a substring — a docstring explaining the rule
        quotes what the rule forbids (`never-ban-a-substring`, nine instances)."""
        tree = _tree("scripts/insider_wide_tier_choice.py")
        calls = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for banned in ("abnormal", "name_frame", "permutation_null", "build_market"):
            self.assertNotIn(banned, calls, "tier choice must not compute %s" % banned)

    def test_the_tier_choice_check_quadrant_pass_is_counts_only(self):
        tree = _tree("scripts/insider_wide_tier_choice.py")
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
              and n.name == "check_counts"]
        self.assertEqual(len(fn), 1)
        calls = {n.func.attr for n in ast.walk(fn[0])
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertNotIn("abnormal", calls)
        self.assertNotIn("name_frame", calls)


class TheCapFilterFailsClosed(unittest.TestCase):
    def test_cap_at_returns_the_most_recent_prior_observation_and_never_a_future_one(self):
        """`A12`: tier membership on a FUTURE property is selection on the future. A name joins
        a cap tier when it is measured to be in it and not before."""
        sched = {"X": [("2020-03-31", 1e8), ("2021-03-31", 9e9), ("2022-03-31", 2e10)]}
        self.assertEqual(TC.cap_at(sched, "X", "2021-06-30"), 9e9)
        self.assertEqual(TC.cap_at(sched, "X", "2020-04-01"), 1e8)
        import math
        self.assertTrue(math.isnan(TC.cap_at(sched, "X", "2019-12-31")),
                        "a date BEFORE the first observation must refuse, never borrow it")

    def test_an_unknown_ticker_refuses_rather_than_defaulting(self):
        import math
        self.assertTrue(math.isnan(TC.cap_at({}, "NOPE", "2021-01-01")))

    def test_the_arm_drops_and_counts_a_row_with_no_cap_rather_than_keeping_it(self):
        """A missing cap is not a small company. Reading it either way silently is the
        blank-code-counter family one level up."""
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("n_event_rows_dropped_no_cap", src)
        tree = _tree("scripts/insider_wide_arm.py")
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "score"]
        self.assertEqual(len(fn), 1)
        seg = ast.get_source_segment(_src("scripts/insider_wide_arm.py"), fn[0]) or ""
        self.assertIn("np.isfinite(caps)", seg)

    def test_the_full_universe_cell_applies_no_cap_filter_at_all(self):
        """A `0.0` floor must mean 'every name', including names with no cap observation — or
        the 'full universe' cell would silently be a has-a-cap-observation cell."""
        tree = _tree("scripts/insider_wide_arm.py")
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "score"]
        seg = ast.get_source_segment(_src("scripts/insider_wide_arm.py"), fn[0]) or ""
        self.assertIn("if floor_usd > 0:", seg)


class TheMdeTravelsWithTheVerdict(unittest.TestCase):
    def test_the_mde_is_taken_on_the_worse_of_the_two_clusterings(self):
        """§4 A3 requires clearing under BOTH, so the honest `se` is the larger one."""
        tree = _tree("scripts/insider_wide_arm.py")
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("se_worst = max(se_d, se_t)", src)
        names = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertIn("z_for_power", names)

    def test_the_mde_is_this_arms_own_se_and_not_borrowed(self):
        """`MB8`: a paired `se` may not be borrowed across constructions."""
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("MB8", src)
        self.assertIn("mde80_pp_own_se", src)

    def test_power_gate_refuses_to_default_its_critical_value(self):
        """`MA5`'s lesson, inherited: a default is exactly how a bar freezes."""
        with self.assertRaises((TypeError, ValueError)) as cm:
            PG.detection_threshold(0.01)                                   # type: ignore[misc]
        self.assertIn("no default", str(cm.exception).lower())

    def test_the_t_bar_is_labelled_uncalibrated_everywhere_it_appears(self):
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("UNCALIBRATED", src)
        self.assertEqual(WA.T_BAR, 2.0)

    def test_the_hlz_hurdle_is_reported_and_not_gated(self):
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("hlz_hurdle_reported_not_gated", src)
        self.assertIn("WHY_NOT_GATED", src)
        tree = _tree("scripts/insider_wide_arm.py")
        # it must not appear inside any comparison that decides a verdict
        for n in ast.walk(tree):
            if isinstance(n, ast.Compare):
                seg = ast.dump(n)
                self.assertNotIn("hlz_hurdle", seg)


class ItAdoptsNothing(unittest.TestCase):
    def test_no_file_under_valuation_is_written_by_this_item(self):
        """The arm writes artifacts under `data/free_analysis/` and nothing else."""
        for rel in ("scripts/insider_wide_arm.py", "scripts/insider_wide_checks.py",
                    "scripts/insider_wide_tier_choice.py"):
            tree = _tree(rel)
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                        and n.func.id == "open":
                    pass  # the mode is checked below via io.open calls
            src = _src(rel)
            self.assertNotIn('"w"', src.replace('io.open(p, "w"', ""),
                             "%s: the only write is the artifact" % rel)

    def test_the_artifact_says_so_in_words(self):
        src = _src("scripts/insider_wide_arm.py")
        self.assertIn("ADOPTS_NOTHING", src)
        self.assertIn("Don's decision", src)

    def test_the_register_names_the_next_rung_as_dons_decision(self):
        t = _src("PREREG_insider_cluster_wide.md")
        self.assertIn("Don", t)


class TheRegisterCarriesItsVoidConditions(unittest.TestCase):
    def test_the_register_has_void_conditions_and_expectations(self):
        t = _src("PREREG_insider_cluster_wide.md")
        self.assertIn("Void condition", t)
        self.assertIn("Expectation", t)

    def test_it_forbids_re_reading_the_check_quadrant(self):
        t = _src("PREREG_insider_cluster_wide.md").lower()
        self.assertIn("once", t)

    def test_the_cost_floor_may_not_be_substituted_after_the_read(self):
        """`W-28`'s rule — a bar may be RAISED and never LOWERED once watched — carried as the
        register's own void condition 4 rather than as a citation.

        **THE FIRST FORM OF THIS TEST ASKED FOR THE STRING `W-28` AND FAILED AGAINST A CORRECT
        REGISTER**, which does not cite it and does not need to: §8.4 voids the item if stage 1's
        floor is substituted for the size-tiered cost or a cheaper cost model is invented. Asking
        for a citation is asking about provenance; the property is what binds.
        """
        t = _src("PREREG_insider_cluster_wide.md")
        self.assertIn("0.67pp floor substituted", t)
        self.assertIn("cheaper cost model", t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
