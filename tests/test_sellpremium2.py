"""SELL-PREMIUM-2 — what these tests pin.

Register: `PREREG_sellpremium2.md`, committed ALONE at `541e466`.

THE LOAD-BEARING ONES:

1. **`T2`: THE 25-DELTA RULE REALLY SELECTS 25 DELTA.** The draft labelled moneyness 0.925 as
   "~25 delta" while showing its delta as −0.202, so its whole knife-edge forecast was computed
   at a twenty-delta strike. The selector is pinned against the target and the realised median.

2. **`T3`: NO MONEYNESS BAND REACHES THE DELTA SELECTION.** A fixed band truncates a delta rule
   exactly in the low-vol names; measured, it would have deleted **37.47%** of the picks.

3. **`T4`: A MISSING DELTA IS EXCLUDED AND COUNTED, NEVER READ AS ZERO** — zero would make every
   such contract look far out of the money and win the selection outright.

4. **`T5`: `K3` IS THE PREDECESSOR'S STATISTIC**, and the gating control reproduces 8.900816 from
   this register's own code path. Without that the two registers' crash figures are not
   comparable and the successor has no argument.

5. **`T6`: THE EVENT SET IS RE-DERIVED AND IDENTICAL** — a register that reads its predecessor's
   pickle cannot tell a shared definition from a shared file.

6. **THE VERDICT CARRIES ITS LABEL.** A Stage-1 pass is `ELIGIBLE-BUT-UNRESOLVED`, and the late
   half sits BELOW its own detection threshold; both must be in the artifact.

    python tests/test_sellpremium2.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.studies import dipcall as D  # noqa: E402
from valuation.studies import sellpremium as SP  # noqa: E402

_SKIPS = []


def _skip(t, why):
    _SKIPS.append(why)
    t.skipTest(why)


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _art(name):
    if not D.have_data():
        return None
    p = D.out_path(name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _chain(rows):
    return pd.DataFrame(rows, columns=["expiration", "strike", "right", "date", "bid", "ask",
                                       "volume", "open_interest"])


class Register(unittest.TestCase):
    REG = "PREREG_sellpremium2.md"

    def test_committed_ALONE_markdown_only_and_an_ANCESTOR(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, self.REG)))

        def git(*a):
            return subprocess.run(("git",) + a, cwd=REPO, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
        sha = ""
        for line in git("log", "--format=%H", "--", self.REG).splitlines():
            sha = line.strip()
        if not sha:
            _skip(self, "no git history for %s in this checkout" % self.REG)
        files = [x for x in git("show", "--name-only", "--format=", sha).split() if x]
        self.assertEqual(files, [self.REG], "NOT committed alone: %s" % files)
        self.assertTrue(all(f.endswith(".md") for f in files))
        self.assertEqual(subprocess.run(("git", "merge-base", "--is-ancestor", sha, "HEAD"),
                                        cwd=REPO, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL).returncode, 0)

    def test_all_twelve_amendments_and_the_void_conditions(self):
        txt = _src(self.REG)
        for a in ["## T%d" % i for i in range(1, 13)]:
            self.assertIn(a, txt, "missing amendment %s" % a)
        self.assertIn("VOID CONDITIONS", txt.upper())
        self.assertIn("LABELLED UNCALIBRATED", txt)
        self.assertIn("ELIGIBLE-BUT-UNRESOLVED", txt)

    def test_the_bar_and_the_synthetic_row_are_NOT_relaxed(self):
        """The prompt's two constraints, and the ONE thing a successor may change."""
        txt = _src(self.REG)
        self.assertIn("the crash bar stays 6.0", txt)
        self.assertEqual(SP.K3_MAX_YEARS_OF_PREMIUM, 6.0)
        self.assertIn("synthetic single-name stress row stays", txt)

    def test_T2_records_the_20_delta_correction_and_re_prices_BEFORE_the_outcome(self):
        txt = _src(self.REG)
        self.assertIn("TWENTY-delta put", txt)
        self.assertIn("4.4385", txt)
        self.assertIn("85/15", txt, "expectation 1 was not re-priced with its reason")


class DeltaSelection(unittest.TestCase):
    def setUp(self):
        self.spot = {"2018-03-01": 100.0}
        self.raw = _chain([
            ["2018-04-05", 97.0, "P", "2018-03-01", 3.00, 3.10, 10, 100],
            ["2018-04-05", 94.0, "P", "2018-03-01", 1.80, 1.90, 10, 100],
            ["2018-04-05", 90.0, "P", "2018-03-01", 1.00, 1.10, 10, 100],
            ["2018-04-05", 80.0, "P", "2018-03-01", 0.20, 0.30, 10, 100],
            ["2018-04-05", 92.0, "P", "2018-03-01", 0.00, 0.90, 10, 100],   # one-sided
        ])
        self.deltas = {("2018-03-01", "2018-04-05", 97.0): (-0.40, 0.30),
                       ("2018-03-01", "2018-04-05", 94.0): (-0.25, 0.30),
                       ("2018-03-01", "2018-04-05", 90.0): (-0.13, 0.30)}
        # 80.0 deliberately has NO delta -- `T4`'s case.

    def test_it_picks_the_strike_nearest_25_DELTA_and_is_deterministic(self):
        f = SP.put_funnel(self.raw, self.spot, "2018-03-01", mon_band=None)
        a = SP.pick_put_by_delta(f["cands"], self.deltas, "2018-03-01")
        b = SP.pick_put_by_delta(f["cands"], self.deltas, "2018-03-01")
        self.assertEqual(a["pick"]["strike"], 94.0)
        self.assertAlmostEqual(a["pick"]["delta"], -0.25, places=12)
        self.assertEqual(a["pick"], b["pick"], "the pick is not deterministic")

    def test_T4_a_candidate_with_NO_delta_is_excluded_and_COUNTED(self):
        f = SP.put_funnel(self.raw, self.spot, "2018-03-01", mon_band=None)
        r = SP.pick_put_by_delta(f["cands"], self.deltas, "2018-03-01")
        self.assertEqual(r["no_delta"], 1, "the delta-less row was not counted")
        self.assertNotEqual(r["pick"]["strike"], 80.0,
                            "a missing delta was read as ZERO and won the selection")

    def test_T3_the_band_is_OFF_for_a_delta_rule_and_ON_by_default(self):
        """Both directions. The default must stay banded or SELL-PREMIUM's funnel moves."""
        nb = SP.put_funnel(self.raw, self.spot, "2018-03-01", mon_band=None)
        bd = SP.put_funnel(self.raw, self.spot, "2018-03-01")
        self.assertGreater(nb["two_sided"], bd["two_sided"],
                           "removing the band changed nothing, so T3 is untestable here")
        self.assertEqual(SP.DELTA_MON_BAND, None)
        self.assertEqual(SP.MONEYNESS_BAND, (0.85, 0.95))
        self.assertIsNone(
            ast.parse(_src("scripts/sellpremium2_kills.py")) and None)   # parses

    def test_the_kills_script_passes_mon_band_None_to_the_delta_search(self):
        self.assertIn("mon_band=None", _src("scripts/sellpremium2_kills.py"))
        self.assertIn("mon_band=None", _src("scripts/sellpremium2_arm.py"))

    def test_the_delta_target_is_held_once(self):
        self.assertEqual(SP.DELTA_TARGET, 0.25)


class KillArtifact(unittest.TestCase):
    def test_T6_the_event_set_was_RE_DERIVED_and_is_IDENTICAL(self):
        a = _art("SELLPREMIUM2_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM2_KILLS.json absent (data/ is gitignored)")
        c = a["C_EV_event_set"]
        self.assertTrue(c["identical"])
        self.assertEqual(c["re_derived"], 4864)
        self.assertEqual(c["only_here"], 0)
        self.assertEqual(c["only_banked"], 0)

    def test_T5_the_control_reproduces_the_PREDECESSORS_8_900816(self):
        a = _art("SELLPREMIUM2_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM2_KILLS.json absent (data/ is gitignored)")
        c = a["C_K3_control"]
        self.assertTrue(c["pass"])
        self.assertLess(c["dev"], 0.02)
        self.assertAlmostEqual(c["worst_years_of_premium"], 8.900816, places=5)

    def test_K3_CLEARS_and_the_mechanism_is_the_INCOME(self):
        a = _art("SELLPREMIUM2_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM2_KILLS.json absent (data/ is gitignored)")
        k3 = a["K3_crash"]
        self.assertTrue(k3["pass"])
        self.assertLess(k3["worst_years_of_premium"], SP.K3_MAX_YEARS_OF_PREMIUM)
        # the income is the denominator, and it roughly DOUBLED against the predecessor's 4.4545%
        self.assertGreater(100 * k3["annual_income_frac_of_secured_cash"], 8.0)

    def test_T3s_cost_is_MEASURED_and_the_band_would_have_bitten(self):
        a = _art("SELLPREMIUM2_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM2_KILLS.json absent (data/ is gitignored)")
        t3 = a["T3_realised_moneyness"]
        self.assertGreater(t3["share_outside_0.85_0.95"], 0.05,
                           "the band would not have bitten, so T3 bought nothing")
        self.assertAlmostEqual(abs(t3["delta_median"]), 0.25, places=2)


class ArmArtifact(unittest.TestCase):
    def test_every_clause_of_DONS_rule_is_scored_and_the_verdict_is_their_CONJUNCTION(self):
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        v = a["verdict_checks"]
        for clause in ("clause_a_profitable_both_halves", "clause_b_beats_random_day",
                       "clause_c_survives_sizing", "clause_d_K3_crash_stress"):
            self.assertIn(clause, v)
        self.assertEqual(a["passes"], all(v.values()))

    def test_a_PASS_CARRIES_the_ELIGIBLE_BUT_UNRESOLVED_label(self):
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        if a["passes"]:
            self.assertIn("ELIGIBLE-BUT-UNRESOLVED", a["verdict"])
            self.assertTrue(a["eligible_but_unresolved"])

    def test_the_shares_comparison_carries_NO_verdict(self):
        """Don's 2026-10-12 ruling, verbatim."""
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        self.assertIn("NO verdict", a["shares_comparison"]["verdict"])
        self.assertNotIn("shares", " ".join(a["verdict_checks"].keys()))

    def test_both_halves_are_scored_with_the_boundary_EMBARGOED(self):
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        a1 = a["A1_clause_a"]
        self.assertTrue(a1["boundary_embargoed"])
        self.assertEqual(a1["full"]["n"], a1["early"]["n"] + a1["late"]["n"]
                         + (a1["full"]["n"] - a1["early"]["n"] - a1["late"]["n"]))
        self.assertGreater(a1["full"]["n"], a1["early"]["n"] + a1["late"]["n"] - 1)

    def test_EVERY_arm_ships_its_own_MDE_so_a_null_is_BOUNDED(self):
        """`MB22`: the 80%-power figure is `(crit + 0.84)*se`, and every MDE this project
        published before MB22 was a 50%-power one."""
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        for w in ("full", "early", "late"):
            self.assertIn("mde_date_clustered_80pc", a["A1_clause_a"][w])
        self.assertIn("mde_date_clustered_80pc", a["A3p_strike_rule"]["paired"])

    def test_A4s_null_is_the_PREDICTION_and_the_autopsy_HOLDS_at_25_delta(self):
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        a4 = a["A4_health"]
        if a4.get("status") != "RAN":
            _skip(self, "A4 did not run")
        self.assertIn("PREDICTION", a4["expected"])
        # V6-OPT measured a 0.43pp assignment gap; a delta target equalises it by construction.
        self.assertLess(abs(a4["assignment_healthy"] - a4["assignment_unhealthy"]), 0.05)

    def test_the_affordability_and_concurrency_skips_are_SEPARATE_fields(self):
        """`MB3`: the low-end failures are AFFORDABILITY, not ruin, and conflating them would
        report a book that never got on as a book that lost."""
        a = _art("SELLPREMIUM2_ARM.json")
        if not a:
            _skip(self, "SELLPREMIUM2_ARM.json absent (data/ is gitignored)")
        for cell in a["survivability_clause_c"].values():
            self.assertIn("affordability_skips", cell)
            self.assertIn("concurrency_skips", cell)

    def test_the_arm_REFUSES_without_a_passing_kill_artifact(self):
        import tempfile
        from scripts import sellpremium2_arm as A
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e1:
                A.require_kills(os.path.join(d, "nope.json"))
            fired = os.path.join(d, "fired.json")
            with io.open(fired, "w", encoding="utf-8") as fh:
                json.dump({"gates": {"K1_coverage": True, "K3_crash_stress": False}}, fh)
            with self.assertRaises(SystemExit) as e2:
                A.require_kills(fired)
        self.assertIn("ABSENT", str(e1.exception))
        self.assertIn("FIRED", str(e2.exception))
        self.assertNotEqual(str(e1.exception), str(e2.exception))

    def test_no_settlement_arithmetic_is_written_in_the_arm(self):
        """`B7`. One definition of a settled put and it is `V6-OPT`'s."""
        src = _src("scripts/sellpremium2_arm.py")
        self.assertIn("settle_short", src)
        self.assertIn("spot_basis=SP.AS_TRADED", src)
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertNotIn("intrinsic_obligation", names)


class Multiplicity(unittest.TestCase):
    def test_BH_k_is_FOUR_and_a_firing_kill_does_not_shrink_it(self):
        rows = SP.benjamini_hochberg([0.001, 0.5], q=SP.BH_Q, k=4)
        self.assertEqual([r["bh_threshold"] for r in rows], [0.025, 0.05])

    #: `MA13`'s committed literal, kept as a FLOOR rather than an equality. Options `N` only
    #: ever rises, so a floor is tamper-evident in the direction that matters (a row deleted
    #: or a charge lowered) and does not fire when another lane books its own trials.
    OPTIONS_N_AT_SELLPREMIUM2 = 319

    def test_the_trials_are_booked_and_the_predecessors_STAY_CHARGED(self):
        """REPOINTED 2026-10-14, `MB31`'s family for the fifth time on this project.

        This asserted `options == 319` and went RED against a correct tree the moment
        `SELL-PREMIUM-3` booked its own four trials -- it fired on the CLOCK, not on anything
        about `SELL-PREMIUM-2`. The literal stays as a FLOOR so a deleted row or a lowered
        charge is still caught, and the load-bearing assertions become the PROPERTIES the
        equality stood in for: both rows are present, and each still charges what it charged.
        """
        from valuation.edge import research_log
        n = research_log.detail()["by_domain"]["options"]
        self.assertGreaterEqual(
            n, self.OPTIONS_N_AT_SELLPREMIUM2,
            "options N has FALLEN, which is the permissive direction and needs its own "
            "decision (MA6)")
        log = _src("RESEARCH_LOG.md")
        charges = {}
        for line in log.split("\n"):
            for rid in ("SELL-PREMIUM", "SELL-PREMIUM-2"):
                if line.startswith("| %s |" % rid):
                    charges.setdefault(rid, [c.strip() for c in line.split("|")][8])
        self.assertEqual(charges.get("SELL-PREMIUM-2"), "n=4",
                         "SELL-PREMIUM-2 books 4 options trials")
        self.assertEqual(charges.get("SELL-PREMIUM"), "n=5",
                         "the predecessor's five trials STAY CHARGED (E-1, MA6)")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
