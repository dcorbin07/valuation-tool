"""MB21 - the persistence-preserving null for S22.

WHAT THESE TESTS PIN, and the split is deliberate.

The SYNTHETIC tests carry the mechanism and run anywhere, including CI: one permutation applied
at every date inherits the real signal's memory, an independent permutation per date destroys it,
a row whose donor is absent goes NaN rather than keeping its own value, and the coverage-
preserving variant is refused as a primary. They are the tripwires and they are mutation-tested.

The REAL-PANEL and ARTIFACT tests reproduce the figures MB21 rests on. `data/` is gitignored, so
a worktree and CI have none of it. They SKIP LOUDLY - the suite prints what it skipped and why -
because a data-dependent test that skips quietly is the vacuous pass this project has now caught
six times. MB21's own first run is the sixth: the panel's `date` column is `str`, coercing S22's
stored dates to Timestamp matched ZERO rows, and C1 reported a perfect 0.000e+00 by comparing
nothing. `test_c1_counts_the_cells_it_compared` exists because of that.

NOTHING HERE RE-RUNS S22, WRITES TERM_STRUCTURE.json, OR EDITS PRODUCT COPY. The withdrawal the
register commits to in section 6 is the app lane's to make; this suite only pins that this lane
did not make it.

    python tests/test_mb21_persistence_null.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from valuation.edge.fundamental_panel import placebo_panel  # noqa: E402
from valuation.studies import persistence_null as PN  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb21_persistence_null.py")
REGISTER = os.path.join(REPO, "PREREG_mb21_persistence_null.md")
_SKIPS = []


def _data_root():
    """`data/` is gitignored, so a worktree has none. Probe for the FILE, never the directory --
    the worktree HAS an empty data/free_analysis, and existence is not population."""
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isfile(os.path.join(env, "free_analysis", "panel_s22_h504.pkl")):
        return env
    p = REPO
    for _ in range(6):
        cand = os.path.join(p, "data")
        if os.path.isfile(os.path.join(cand, "free_analysis", "panel_s22_h504.pkl")):
            return cand
        p = os.path.dirname(p)
    return None


def _artifact(name):
    root = _data_root()
    if root is None:
        return None
    p = os.path.join(root, "free_analysis", name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _skip(msg):
    _SKIPS.append(msg)
    raise unittest.SkipTest(msg)


# --------------------------------------------------------------------------- fixture


SEVEN = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
         "institutional"]
FLAT = {c: 0.125 for c in SEVEN}


def synthetic(n_names=120, n_dates=16, rho=0.9, seed=7, drop_frac=0.0):
    """A panel whose signal is genuinely PERSISTENT per name, which is the whole point.

    Each name gets an AR(1) path with autocorrelation `rho`, so a null that keeps a name's path
    intact keeps the memory and a null that reshuffles within dates destroys it. `fwd_ret` is
    built to CORRELATE with the signal, so a working null has to be seen to remove that.
    """
    rng = np.random.default_rng(seed)
    names = ["N%03d" % i for i in range(n_names)]
    dates = ["2010-%02d-15" % (i + 1) if i < 12 else "2011-%02d-15" % (i - 11)
             for i in range(n_dates)]
    lvl = {t: rng.normal() for t in names}
    rows = []
    for d in dates:
        for t in names:
            lvl[t] = rho * lvl[t] + np.sqrt(1 - rho ** 2) * rng.normal()
            if drop_frac and rng.random() < drop_frac:
                continue
            base = lvl[t]
            r = {"date": d, "ticker": t,
                 "fwd_ret": 0.02 * base + rng.normal(scale=0.05),
                 "bench_ret": rng.normal(scale=0.01),
                 "marketcap": float(abs(rng.normal(1e9, 2e8))),
                 "sector": "Tech"}
            for c in SEVEN:
                r[c] = base + rng.normal(scale=0.15)
            rows.append(r)
    return pd.DataFrame(rows)


def autocorr_mean(panel, lag):
    cbd = PN.composite_by_date(panel, SEVEN, FLAT)
    a = PN.rank_autocorrelation(cbd, lag)
    return a.get("mean")


def median_ic(panel):
    return PN.association_ic(panel, SEVEN, FLAT, "fwd_ret").get("median_ic")


# --------------------------------------------------------------------------- mechanism


class TestMechanism(unittest.TestCase):

    def test_one_permutation_is_used_at_every_date(self):
        """THE tripwire. `placebo_panel` draws an independent permutation per date; this draws
        ONE and applies it everywhere. Checked by identity of the inherited value, not by
        reading the code."""
        p = synthetic()
        pp, _ = PN.persistence_panel(p, seed=1, cols=SEVEN)
        donor = PN.donor_map(pd.unique(p["ticker"].to_numpy()), 1)
        checked = 0
        for d in sorted(p["date"].unique()):
            real = p[p["date"] == d].set_index("ticker")
            plac = pp[pp["date"] == d].set_index("ticker")
            for t in plac.index:
                src = donor[t]
                if src in real.index:
                    self.assertAlmostEqual(float(plac.loc[t, "value"]),
                                           float(real.loc[src, "value"]), places=12)
                    checked += 1
        self.assertGreater(checked, 500, "vacuous: almost nothing was actually compared")

    def test_persistence_is_retained(self):
        p = synthetic()
        real1, real8 = autocorr_mean(p, 1), autocorr_mean(p, 4)
        for seed in (1, 2, 3):
            pp, _ = PN.persistence_panel(p, seed=seed, cols=SEVEN)
            self.assertLess(abs(autocorr_mean(pp, 1) - real1), 0.15)
            self.assertLess(abs(autocorr_mean(pp, 4) - real8), 0.15)

    def test_the_within_date_null_destroys_persistence(self):
        """The positive control. Without it, 'persistence retained' could be true of any null
        and the whole item would have no premise."""
        p = synthetic()
        self.assertGreater(autocorr_mean(p, 1), 0.5)
        for seed in (1, 2, 3):
            self.assertLess(abs(autocorr_mean(placebo_panel(p, seed=seed, cols=SEVEN), 1)), 0.25)

    def test_association_with_forward_returns_is_destroyed(self):
        p = synthetic()
        self.assertGreater(median_ic(p), 0.20, "fixture is not predictive; test is vacuous")
        for seed in (1, 2, 3, 4, 5):
            pp, _ = PN.persistence_panel(p, seed=seed, cols=SEVEN)
            self.assertLess(abs(median_ic(pp)), 0.20)

    def test_a_row_whose_donor_is_absent_goes_nan_and_is_not_left_at_its_own_value(self):
        """The leak that would matter most: leaving an unmoved row at its own value keeps the
        real signal-return association for exactly the rows the permutation failed to move."""
        p = synthetic(drop_frac=0.35, seed=11)
        pp, info = PN.persistence_panel(p, seed=3, cols=SEVEN)
        self.assertLess(info["rows_kept_frac"], 1.0, "fixture has no absent donors")
        miss = pp[SEVEN].isna().all(axis=1).to_numpy()
        self.assertTrue(miss.any())
        # every unmoved row is NaN across ALL permuted columns, never partially filled
        self.assertTrue((pp.loc[miss, SEVEN].isna()).all().all())
        # and it is not equal to its own real value anywhere it was filled
        self.assertEqual(int((~miss).sum()), info["rows_kept"])

    def test_determinism_in_seed(self):
        p = synthetic()
        a, _ = PN.persistence_panel(p, seed=42, cols=SEVEN)
        b, _ = PN.persistence_panel(p, seed=42, cols=SEVEN)
        c, _ = PN.persistence_panel(p, seed=43, cols=SEVEN)
        self.assertTrue(np.allclose(a["value"].to_numpy(dtype=float),
                                    b["value"].to_numpy(dtype=float), equal_nan=True))
        self.assertFalse(np.allclose(a["value"].to_numpy(dtype=float),
                                     c["value"].to_numpy(dtype=float), equal_nan=True))

    def test_a_forward_return_can_never_be_permuted(self):
        for bad in ("fwd_ret", "fwd_ret_h504", "bench_ret"):
            with self.assertRaises(PN.RegisterViolation):
                PN.assert_no_forward_return_permuted(SEVEN + [bad])
        PN.assert_no_forward_return_permuted(SEVEN)   # the clean case must NOT raise


class TestThinningControl(unittest.TestCase):

    def test_the_thinning_control_carries_the_same_mask(self):
        """C5 is only an attribution if its coverage matches the primary's exactly."""
        p = synthetic(drop_frac=0.3, seed=5)
        pp, ip = PN.persistence_panel(p, seed=9, cols=SEVEN)
        tt, it = PN.thinned_within_date_panel(p, seed=9, cols=SEVEN)
        self.assertEqual(ip["rows_kept"], it["rows_kept"])
        np.testing.assert_array_equal(pp[SEVEN].isna().all(axis=1).to_numpy(),
                                      tt[SEVEN].isna().all(axis=1).to_numpy())

    def test_the_thinning_control_has_no_persistence(self):
        """If it did, it would not isolate coverage and the decomposition would be meaningless."""
        p = synthetic()
        tt, _ = PN.thinned_within_date_panel(p, seed=9, cols=SEVEN)
        self.assertLess(abs(autocorr_mean(tt, 1)), 0.25)


class TestStratifiedIsDisqualified(unittest.TestCase):

    def test_assert_not_primary_refuses_it(self):
        with self.assertRaises(PN.RegisterViolation):
            PN.assert_not_primary(PN.STRATIFIED)
        PN.assert_not_primary(PN.PRIMARY)      # the primary must NOT raise

    def test_it_is_marked_disqualified_and_says_why(self):
        p = synthetic(drop_frac=0.3, seed=5)
        _, info = PN.stratified_panel(p, seed=1, cols=SEVEN)
        self.assertTrue(info["disqualified"])
        self.assertIn("themselves", info["why"])

    def test_it_really_does_leave_fixed_points(self):
        """Pins the measured reason for the disqualification rather than asserting it."""
        p = synthetic(n_names=60, n_dates=10, drop_frac=0.4, seed=13)
        fps = [PN.stratified_panel(p, seed=s, cols=SEVEN)[1]["fixed_points"] for s in range(6)]
        self.assertGreater(max(fps), 0)


class TestCoverageDisclosure(unittest.TestCase):

    def test_effective_coverage_is_reported_below_real(self):
        p = synthetic(drop_frac=0.3, seed=5)
        pp, _ = PN.persistence_panel(p, seed=2, cols=SEVEN)
        b = PN.coverage_block(p, pp, SEVEN)
        self.assertLess(b["effective_rows_with_signal"], b["real_rows_with_signal"])
        self.assertLess(b["effective_cross_section"]["median"],
                        b["real_cross_section"]["median"])
        self.assertIn("clears_cross_section_floor", b)

    def test_format_coverage_is_ascii_only(self):
        """It prints to a cp1252 console. O21-D2 lost an artifact write to a formatting
        character after every statistic had been computed."""
        p = synthetic(drop_frac=0.2, seed=5)
        pp, _ = PN.persistence_panel(p, seed=2, cols=SEVEN)
        s = PN.format_coverage(PN.coverage_block(p, pp, SEVEN))
        s.encode("ascii")
        self.assertIn("EFFECTIVE COVERAGE", s)


# --------------------------------------------------------------------------- the register


class TestRegisterDiscipline(unittest.TestCase):

    def test_the_register_file_exists_on_disk(self):
        """V6's lesson: assert the file is THERE, not that the citation starts with PREREG_.
        Two lanes once named the same unbuilt register differently."""
        self.assertTrue(os.path.isfile(REGISTER), "register missing: %s" % REGISTER)

    def test_the_kill_threshold_is_read_from_the_artifact_not_typed_into_the_script(self):
        """Register void condition 2. If 3.830087 were a literal here, a later edit could move
        the target after the floors were known. Read the SYNTAX TREE, not a grep - MA49's
        comment-versus-code defect, which this project has now hit four times."""
        tree = ast.parse(io.open(SCRIPT, encoding="utf-8").read())
        bad = [n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, float)
               and 3.5 < n.value < 4.5]
        self.assertEqual(bad, [], "the observed H=504 value appears as a literal: %r" % bad)

    def test_the_kill_tolerance_resolves_ambiguity_against_the_claim(self):
        """Register 6: a floor landing within +/-0.05 of the observed is NOT SUPPORTED, never a
        pass. Pinned as arithmetic so the direction cannot be flipped by an edit."""
        import scripts.mb21_persistence_null as M
        observed, tol = 3.830087, M.KILL_TOLERANCE
        for floor in (observed - tol / 2.0, observed, observed + 1.0):
            self.assertTrue(floor >= observed - tol,
                            "a floor of %r must resolve AGAINST the claim" % floor)
        self.assertFalse(observed - 1.0 >= observed - tol)

    def test_this_lane_did_not_edit_the_product_copy(self):
        """Register 6 routes the withdrawal to the app lane. This pins that the routing was
        real: the shipped copy still carries its S22 constants, unedited by MB21."""
        src = io.open(os.path.join(REPO, "valuation", "web", "hold_horizon.py"),
                      encoding="utf-8").read()
        self.assertIn("ALPHA_ANN_TWO_YEARS", src)
        self.assertNotIn("MB21", src, "MB21 edited product copy; the register routes it instead")

    def test_the_floors_pass_refuses_without_passing_controls(self):
        """The two-pass gate, exercised rather than promised."""
        import scripts.mb21_persistence_null as M
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            missing = os.path.join(td, "nope.json")
            with self.assertRaises(SystemExit):
                M.run_floors(_data_root() and os.path.dirname(_data_root()) or REPO,
                             missing, 0, 1, td)
            failing = os.path.join(td, "ctrl.json")
            with io.open(failing, "w", encoding="utf-8") as fh:
                json.dump({"all_gating_pass": False, "gating": {"C1": False}}, fh)
            with self.assertRaises(SystemExit):
                M.run_floors(_data_root() and os.path.dirname(_data_root()) or REPO,
                             failing, 0, 1, td)


# --------------------------------------------------------------------------- artifacts


class TestControlsArtifact(unittest.TestCase):

    def setUp(self):
        self.a = _artifact("MB21_CONTROLS.json")
        if self.a is None:
            _skip("MB21_CONTROLS.json absent (data/ is gitignored) - controls not verified here")

    def test_c1_counts_the_cells_it_compared(self):
        """THE non-vacuity guard, and it exists because the first run of this control scored a
        perfect 0.000e+00 on an EMPTY panel by comparing nothing."""
        c1 = self.a["C1_harness_identity"]
        self.assertEqual(c1["cells_compared"], c1["cells_expected"])
        self.assertGreater(c1["cells_compared"], 0)

    def test_c1_reproduces_s22_exactly(self):
        self.assertLess(self.a["C1_harness_identity"]["max_abs_delta"], 1e-9)

    def test_the_gating_controls_pass(self):
        self.assertTrue(self.a["all_gating_pass"], self.a.get("gating"))

    def test_the_null_remembers(self):
        for k, v in self.a["C2_persistence_retained"]["by_lag"].items():
            self.assertLess(v["abs_delta_vs_real"], self.a["C2_persistence_retained"]["tolerance"],
                            "lag %s" % k)
            self.assertGreater(v["placebo_mean"], 0.2, "lag %s has no memory at all" % k)

    def test_the_stratified_variant_is_recorded_as_disqualified(self):
        rows = self.a["register_2b_stratified_disqualified"]
        self.assertTrue(all(r["disqualified"] for r in rows))
        self.assertGreater(max(r["fixed_points"] for r in rows), 0)


class TestFloorsArtifact(unittest.TestCase):

    def setUp(self):
        self.a = _artifact("MB21_PERSISTENCE_NULL.json")
        if self.a is None:
            _skip("MB21_PERSISTENCE_NULL.json absent - floors not verified here")

    def test_the_draw_count_is_the_registered_one(self):
        self.assertEqual(self.a["draws"], 200)

    def test_the_verdict_follows_the_pre_committed_rule(self):
        k = self.a["kill"]
        expect = ("NOT SUPPORTED" if k["persistence_floor"] >= k["observed_pinned_in_register"]
                  - k["tolerance"] else "STANDS")
        self.assertEqual(k["verdict"], expect)

    def test_the_kill_cell_is_h504_alpha_t_hac(self):
        self.assertEqual(self.a["kill"]["horizon"], 504)
        self.assertEqual(self.a["kill"]["statistic"], "alpha_t_hac")

    def test_the_observed_value_matches_the_shipped_s22_artifact(self):
        s22 = _artifact("TERM_STRUCTURE.json")
        if s22 is None:
            _skip("TERM_STRUCTURE.json absent")
        self.assertAlmostEqual(self.a["kill"]["observed_pinned_in_register"],
                               s22["primary_common_dates"]["504"]["alpha_t_hac"], places=12)

    def test_the_floors_carry_a_not_comparable_with_label(self):
        """A floor quoted against a bar it was not calibrated on is register void condition 9,
        and it is this project's single most repeated reporting error."""
        n = self.a["not_comparable_with"]
        self.assertIn("CPCV", n)
        self.assertIn("fixed_weights_null", n)

    def test_the_attribution_decomposes_exactly(self):
        for h, r in self.a["per_horizon"].items():
            self.assertAlmostEqual(r["coverage_effect"] + r["memory_effect"],
                                   r["total_effect"], places=9, msg="horizon %s" % h)

    def test_no_equity_or_options_trial_is_charged(self):
        self.assertEqual(self.a["trials"]["domain"], "infra")
        self.assertEqual(self.a["trials"]["charged"], 1)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
