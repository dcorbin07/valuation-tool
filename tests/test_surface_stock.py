"""Tests for U2 (PREREG_u2_surface_stock_signals.md).

The load-bearing ones are:

(a) `term_slope` is the O16 construction and NOT the shipped `term_slope_60_30`. The fixture is
    built so the two columns DISAGREE, because a fixture where they agree cannot tell them apart
    and would pass against the wrong column.
(b) The point-in-time join is STRICTLY BEFORE — a same-day derived row must not be used.
(c) The verdict rules: a sign flip between halves is a NULL even when |t| clears twice, and a
    declared-sign contradiction is never a pass however large.
(d) `ic_tstat` is the SHIPPED theme_ic arithmetic, verified against `fundamental_panel` itself
    rather than against a second copy of the formula.
"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import surface_stock as SS  # noqa: E402


def _daily(dates, atm60, atmfront, ivr=None, skew=None, ts6030=None):
    d = {"date": pd.to_datetime(dates), "atm_iv_60": atm60, "atm_iv_front": atmfront}
    d["iv_rank"] = ivr if ivr is not None else [np.nan] * len(dates)
    d["skew_25d"] = skew if skew is not None else [np.nan] * len(dates)
    if ts6030 is not None:
        d["term_slope_60_30"] = ts6030
    return pd.DataFrame(d)


# --------------------------------------------------------------------------- #
#  the O16 construction (register §0.3) — the near-miss this pins
# --------------------------------------------------------------------------- #
class TestTheO16Construction(unittest.TestCase):
    def test_term_slope_is_atm60_minus_atmfront(self):
        df = _daily(["2020-01-02", "2020-01-03"], [0.30, 0.28], [0.25, 0.31])
        out = SS.build_arm_columns(df)
        self.assertAlmostEqual(out["term_slope"].iloc[0], 0.05, places=12)
        self.assertAlmostEqual(out["term_slope"].iloc[1], -0.03, places=12)

    def test_the_shipped_term_slope_60_30_is_NOT_used_even_when_present(self):
        """The fixture makes the two constructions DISAGREE, which is the only way to tell.

        `term_slope_60_30` is `atm_iv_60 - atm_iv_30` and correlates with the O16 construction at
        only Spearman +0.5744 on the real layer. A lookup by column name computes cleanly, raises
        nothing, and answers a question O16 never validated.
        """
        df = _daily(["2020-01-02"], [0.30], [0.25], ts6030=[999.0])
        out = SS.build_arm_columns(df)
        self.assertAlmostEqual(out["term_slope"].iloc[0], 0.05, places=12)
        self.assertNotIn(999.0, list(out["term_slope"].values))
        self.assertNotIn("term_slope_60_30", out.columns)

    def test_the_forbidden_columns_are_absent_from_the_arm_frame(self):
        df = _daily(["2020-01-02"], [0.3], [0.25], ts6030=[0.01])
        df["iv_call_25d"] = 0.2
        df["iv_put_25d"] = 0.3
        df["atm_iv_30"] = 0.27
        out = SS.build_arm_columns(df)
        for c in SS.FORBIDDEN_COLUMNS:
            self.assertNotIn(c, out.columns)

    def test_a_missing_leg_yields_nan_rather_than_a_silent_zero(self):
        df = pd.DataFrame({"date": pd.to_datetime(["2020-01-02"]), "atm_iv_60": [0.3]})
        out = SS.build_arm_columns(df)
        self.assertTrue(np.isnan(out["term_slope"].iloc[0]))

    def test_a_frame_with_no_date_column_raises(self):
        with self.assertRaises(SS.RegisterViolation):
            SS.build_arm_columns(pd.DataFrame({"atm_iv_60": [0.3]}))


# --------------------------------------------------------------------------- #
#  C5 — no arm may be another arm's negation (register §0.2)
# --------------------------------------------------------------------------- #
class TestNegatedDuplicate(unittest.TestCase):
    def test_an_exact_negation_raises(self):
        n = 200
        rng = np.random.default_rng(7)
        a = rng.normal(size=n)
        f = pd.DataFrame({"skew": a, "cw": -a})
        with self.assertRaises(SS.RegisterViolation):
            SS.assert_no_negated_duplicate(f, ["skew", "cw"])

    def test_genuinely_distinct_columns_pass(self):
        rng = np.random.default_rng(8)
        f = pd.DataFrame({"a": rng.normal(size=200), "b": rng.normal(size=200)})
        self.assertTrue(SS.assert_no_negated_duplicate(f, ["a", "b"])["ok"])

    def test_a_merely_correlated_pair_is_not_flagged(self):
        """-0.99 correlated is not the same object; only an EXACT negation is."""
        rng = np.random.default_rng(9)
        a = rng.normal(size=400)
        f = pd.DataFrame({"a": a, "b": -a + rng.normal(scale=0.2, size=400)})
        self.assertTrue(SS.assert_no_negated_duplicate(f, ["a", "b"])["ok"])


# --------------------------------------------------------------------------- #
#  the point-in-time join
# --------------------------------------------------------------------------- #
class TestPointInTimeJoin(unittest.TestCase):
    def _panel(self, dates, tickers):
        rows = [{"date": pd.Timestamp(d), "ticker": t, "fwd_ret": 0.0}
                for d in dates for t in tickers]
        return pd.DataFrame(rows)

    def test_a_same_day_derived_row_is_NOT_used(self):
        panel = self._panel(["2020-03-10"], ["AAA"])
        arms = {"AAA": SS.build_arm_columns(
            _daily(["2020-03-09", "2020-03-10"], [0.30, 0.90], [0.25, 0.10]))}
        out, ctrl = SS.join_pit(panel, arms)
        self.assertAlmostEqual(out["term_slope"].iloc[0], 0.05, places=12)   # the 03-09 row
        self.assertEqual(ctrl["pit_violations"], 0)

    def test_a_future_row_is_never_reached(self):
        panel = self._panel(["2020-03-10"], ["AAA"])
        arms = {"AAA": SS.build_arm_columns(_daily(["2020-03-11"], [0.9], [0.1]))}
        out, ctrl = SS.join_pit(panel, arms)
        self.assertTrue(np.isnan(out["term_slope"].iloc[0]))
        self.assertEqual(ctrl["n_joined"], 0)

    def test_a_stale_row_beyond_the_ceiling_is_dropped(self):
        panel = self._panel(["2020-03-10"], ["AAA"])
        arms = {"AAA": SS.build_arm_columns(_daily(["2020-02-01"], [0.3], [0.25]))}
        out, ctrl = SS.join_pit(panel, arms)
        self.assertTrue(np.isnan(out["term_slope"].iloc[0]))

    def test_a_row_inside_the_ceiling_is_kept(self):
        panel = self._panel(["2020-03-10"], ["AAA"])
        arms = {"AAA": SS.build_arm_columns(_daily(["2020-03-05"], [0.3], [0.25]))}
        out, ctrl = SS.join_pit(panel, arms)
        self.assertAlmostEqual(out["term_slope"].iloc[0], 0.05, places=12)
        self.assertEqual(ctrl["n_joined"], 1)

    def test_an_unknown_ticker_joins_nothing_and_raises_nothing(self):
        panel = self._panel(["2020-03-10"], ["ZZZ"])
        out, ctrl = SS.join_pit(panel, {"AAA": SS.build_arm_columns(
            _daily(["2020-03-09"], [0.3], [0.25]))})
        self.assertEqual(ctrl["n_joined"], 0)
        self.assertTrue(np.isnan(out["term_slope"].iloc[0]))


# --------------------------------------------------------------------------- #
#  halves — register §0.4 forbids a thin split
# --------------------------------------------------------------------------- #
class TestHalves(unittest.TestCase):
    def test_forty_dates_split_twenty_and_nineteen_with_the_boundary_embargoed(self):
        ds = list(range(40))
        e, l, b = SS.halves(ds)
        self.assertEqual(len(e), 20)
        self.assertEqual(len(l), 19)
        self.assertEqual(b, 20)
        self.assertNotIn(b, e)
        self.assertNotIn(b, l)

    def test_a_split_too_thin_for_min_dates_raises_rather_than_returning_it(self):
        with self.assertRaises(SS.RegisterViolation):
            SS.halves(list(range(20)))

    def test_the_full_panel_is_not_silently_splittable_when_most_dates_are_empty(self):
        """29 of 69 panel dates carry ZERO coverage. `covered_dates` must exclude them."""
        rows = []
        for d in range(5):
            for t in range(40):
                rows.append({"date": d, "ticker": f"T{t}", "fwd_ret": 0.0,
                             "term_slope": np.nan if d < 3 else 0.1,
                             "iv_rank": np.nan, "skew_25d": np.nan})
        f = pd.DataFrame(rows)
        self.assertEqual(SS.covered_dates(f), [3, 4])


# --------------------------------------------------------------------------- #
#  ic_tstat — must BE the shipped arithmetic, not a second copy of it
# --------------------------------------------------------------------------- #
class TestICArithmetic(unittest.TestCase):
    def test_matches_fundamental_panels_theme_ic_on_a_real_panel_shape(self):
        from valuation.edge import fundamental_panel as FP
        rng = np.random.default_rng(11)
        rows = []
        for d in range(25):
            for t in range(60):
                z = rng.normal()
                rows.append({"date": f"2020-{d + 1:02d}-01", "ticker": f"T{t}",
                             "value": z, "fwd_ret": 0.3 * z + rng.normal()})
        panel = pd.DataFrame(rows)
        shipped = FP.theme_ic(panel, min_dates=8)["value"]["ic_tstat"]

        ics = []
        for _d, g in panel.groupby("date"):
            ics.append(SS._spearman(g["value"].values, g["fwd_ret"].values))
        self.assertAlmostEqual(SS.ic_tstat(ics), shipped, places=12)

    def test_an_exactly_zero_variance_series_gives_zero(self):
        """0.0 is one of the constants whose pandas/numpy sd IS exactly zero."""
        self.assertEqual(SS.ic_tstat([0.0, 0.0, 0.0]), 0.0)

    def test_the_shipped_guard_is_VALUE_DEPENDENT_and_that_is_pinned_not_repaired(self):
        """`[0.1]*3` has sd ~5.8e-17, so `sd > 0` passes and the shipped formula returns ~1e16.

        This is the SECTOR-NEUTRAL-B6 zero-variance defect in a new place. It is inherited on
        purpose so that `ic_tstat` remains the arithmetic X7's 2.71 bar was calibrated on; the
        degeneracy guard below is what stops it ever being read as a pass.
        """
        t = SS.ic_tstat([0.1, 0.1, 0.1])
        self.assertGreater(abs(t), 1e10)
        self.assertTrue(SS.ic_series_degenerate([0.1, 0.1, 0.1]))

    def test_a_degenerate_series_can_never_be_read_as_a_pass(self):
        v = SS.arm_verdict(1e16, 1e16, "term_slope", degenerate_early=True)
        self.assertEqual(v["verdict"], "DEGENERATE")
        self.assertNotEqual(v["verdict"], "ADOPT-ELIGIBLE")

    def test_a_normal_series_is_not_flagged_degenerate(self):
        self.assertFalse(SS.ic_series_degenerate([0.01, -0.02, 0.03, 0.005]))

    def test_too_few_points_returns_None(self):
        self.assertIsNone(SS.ic_tstat([0.1]))


# --------------------------------------------------------------------------- #
#  residualisation — the PEAD template
# --------------------------------------------------------------------------- #
class TestResidualise(unittest.TestCase):
    def test_a_candidate_that_is_an_exact_combination_of_incumbents_residualises_to_zero(self):
        rng = np.random.default_rng(13)
        n = 80
        g = pd.DataFrame({"value": rng.normal(size=n), "quality": rng.normal(size=n),
                          "fwd_ret": rng.normal(size=n)})
        g["cand"] = 2.0 * g["value"] - 3.0 * g["quality"] + 1.5
        resid, _fr, r2 = SS.residualise(g, "cand", ["value", "quality"])
        self.assertLess(float(np.max(np.abs(resid))), 1e-8)
        self.assertGreater(r2, 1 - 1e-10)

    def test_an_orthogonal_candidate_keeps_essentially_all_its_variance(self):
        rng = np.random.default_rng(14)
        n = 400
        g = pd.DataFrame({"value": rng.normal(size=n), "quality": rng.normal(size=n),
                          "cand": rng.normal(size=n), "fwd_ret": rng.normal(size=n)})
        _resid, _fr, r2 = SS.residualise(g, "cand", ["value", "quality"])
        self.assertLess(r2, 0.05)

    def test_too_few_names_returns_None_rather_than_a_fitted_line(self):
        g = pd.DataFrame({"value": [1.0, 2.0], "cand": [1.0, 2.0], "fwd_ret": [0.1, 0.2]})
        self.assertIsNone(SS.residualise(g, "cand", ["value"]))


# --------------------------------------------------------------------------- #
#  the verdict rules
# --------------------------------------------------------------------------- #
class TestArmVerdict(unittest.TestCase):
    def test_both_halves_clearing_with_agreeing_signs_is_eligible(self):
        v = SS.arm_verdict(3.0, 2.9, "term_slope")
        self.assertEqual(v["verdict"], "ADOPT-ELIGIBLE")

    def test_a_SIGN_FLIP_between_halves_is_a_NULL_even_when_both_clear(self):
        """The two-sided device: without a declared sign, agreement between halves does the work.

        +3.0 early and -3.0 late is two significant results pointing in opposite directions, which
        is evidence of noise, not of an effect.
        """
        v = SS.arm_verdict(3.0, -3.0, "term_slope")
        self.assertNotEqual(v["verdict"], "ADOPT-ELIGIBLE")
        self.assertFalse(v["signs_agree"])

    def test_one_half_only_is_not_replicated_and_carries_the_sibling_label(self):
        v = SS.arm_verdict(3.0, 0.4, "iv_rank")
        self.assertEqual(v["verdict"], "NOT_REPLICATED")
        self.assertEqual(v["sibling_label"], "1 of 4 sibling arms")

    def test_neither_half_is_rejected(self):
        self.assertEqual(SS.arm_verdict(0.5, -0.2, "iv_rank")["verdict"], "REJECTED")

    def test_a_miss_by_a_hair_is_a_NULL_and_is_not_rounded_into_a_pass(self):
        """RUN_RULES A6. 2.7099 against a 2.71 bar is a miss."""
        v = SS.arm_verdict(2.7099, 3.4, "term_slope")
        self.assertEqual(v["verdict"], "NOT_REPLICATED")
        self.assertFalse(v["clears_early"])

    def test_exactly_at_the_bar_clears(self):
        v = SS.arm_verdict(SS.IC_BAR, SS.IC_BAR, "term_slope")
        self.assertEqual(v["verdict"], "ADOPT-ELIGIBLE")

    def test_a_declared_sign_contradiction_is_never_a_pass_however_large(self):
        """skew_25d's sign is declared NEGATIVE from Xing-Zhang-Zhao. +9.0 is not a discovery."""
        v = SS.arm_verdict(9.0, 9.0, "skew_25d")
        self.assertNotEqual(v["verdict"], "ADOPT-ELIGIBLE")
        self.assertTrue(v["contradicts_declared_sign"])

    def test_a_declared_sign_arm_passes_only_in_its_declared_direction(self):
        v = SS.arm_verdict(-3.0, -2.8, "skew_25d")
        self.assertEqual(v["verdict"], "ADOPT-ELIGIBLE")
        self.assertEqual(v["declared_sign"], -1)

    def test_a_two_sided_arm_may_pass_negative(self):
        self.assertEqual(SS.arm_verdict(-3.0, -2.8, "term_slope")["verdict"], "ADOPT-ELIGIBLE")

    def test_no_power_makes_every_arm_UNINTERPRETABLE_rather_than_rejected(self):
        v = SS.arm_verdict(0.1, 0.1, "iv_rank", power_ok=False)
        self.assertEqual(v["verdict"], "UNINTERPRETABLE")
        self.assertNotEqual(v["verdict"], "REJECTED")

    def test_a_missing_t_is_not_computable_rather_than_rejected(self):
        self.assertEqual(SS.arm_verdict(None, 3.0, "iv_rank")["verdict"], "NOT_COMPUTABLE")


class TestPowerVerdict(unittest.TestCase):
    def test_a_clearing_control_reports_power(self):
        p = SS.power_verdict({"gp_on_capital": {"raw_ic_tstat": 3.1},
                              "ret_6_1": {"raw_ic_tstat": 0.4}})
        self.assertTrue(p["any_cleared"])

    def test_neither_clearing_reports_no_power(self):
        p = SS.power_verdict({"gp_on_capital": {"raw_ic_tstat": 1.1},
                              "ret_6_1": {"raw_ic_tstat": -0.4}})
        self.assertFalse(p["any_cleared"])

    def test_a_strongly_negative_control_still_counts_as_power(self):
        """Power is about resolution, not direction: |t| is the right quantity."""
        p = SS.power_verdict({"gp_on_capital": {"raw_ic_tstat": -3.5}})
        self.assertTrue(p["any_cleared"])


# --------------------------------------------------------------------------- #
#  the composite arm
# --------------------------------------------------------------------------- #
class TestOrientAndBlend(unittest.TestCase):
    def _frame(self, sign_for_skew=-1.0):
        rng = np.random.default_rng(21)
        rows = []
        for d in range(30):
            for t in range(40):
                a, b, c = rng.normal(), rng.normal(), rng.normal()
                rows.append({"date": d, "ticker": f"T{t}", "value": rng.normal(),
                             "quality": rng.normal(), "momentum": rng.normal(),
                             "insider": rng.normal(), "capital_discipline": rng.normal(),
                             "size": rng.normal(), "institutional": rng.normal(),
                             "term_slope": a, "iv_rank": b, "skew_25d": c,
                             "fwd_ret": 0.6 * sign_for_skew * c + 0.3 * rng.normal()})
        return pd.DataFrame(rows)

    def test_a_component_predicting_negatively_is_flipped_so_the_blend_points_one_way(self):
        f = self._frame(sign_for_skew=-1.0)
        _blend, meta = SS.orient_and_blend(f, list(range(15)))
        self.assertEqual(meta["signs"]["skew_25d"], -1.0)

    def test_the_orientation_flips_when_the_underlying_relationship_flips(self):
        f = self._frame(sign_for_skew=+1.0)
        _blend, meta = SS.orient_and_blend(f, list(range(15)))
        self.assertEqual(meta["signs"]["skew_25d"], +1.0)

    def test_the_blend_renormalises_by_the_present_components(self):
        f = self._frame()
        f.loc[f.index[:100], "iv_rank"] = np.nan
        blend, _meta = SS.orient_and_blend(f, list(range(15)))
        self.assertTrue(blend.iloc[:100].notna().any())

    def test_no_orientable_component_raises_rather_than_inventing_a_sign(self):
        f = self._frame()
        for c in SS.COMPONENT_ARMS:
            f[c] = np.nan
        with self.assertRaises(SS.RegisterViolation):
            SS.orient_and_blend(f, list(range(15)))


# --------------------------------------------------------------------------- #
#  register invariants
# --------------------------------------------------------------------------- #
class TestRegisterInvariants(unittest.TestCase):
    def test_the_incumbent_set_is_the_seven_weighted_themes(self):
        self.assertEqual(set(SS.INCUMBENTS),
                         {"value", "quality", "momentum", "insider", "capital_discipline",
                          "size", "institutional"})
        for absent in ("low_risk", "growth", "sentiment"):
            self.assertNotIn(absent, SS.INCUMBENTS)

    def test_the_bars_are_the_calibrated_equity_ones(self):
        self.assertEqual(SS.IC_BAR, 2.71)
        self.assertEqual(SS.LS_HAC_FLOOR, 2.2837)
        self.assertEqual(SS.POWER_BAR, 2.0)

    def test_only_skew_has_a_declared_sign(self):
        self.assertEqual(SS.DECLARED_SIGN, {"skew_25d": -1})

    def test_four_arms_are_registered(self):
        self.assertEqual(len(SS.ARMS), 4)
        self.assertEqual(len(SS.COMPONENT_ARMS), 3)

    def test_the_arm_path_never_names_a_forbidden_column_outside_the_forbid_list(self):
        """A source-level guard: the near-miss of §0.3 is a NAME, so pin the name.

        Checked for vacuity by requiring the forbidden names to appear at all (in the tuple and
        its comment) — a guard that inspects nothing passes trivially.
        """
        import inspect
        src = inspect.getsource(SS)
        marker = "FORBIDDEN_COLUMNS"
        self.assertIn(marker, src)
        body = src.split("def build_arm_columns", 1)[1].split("\ndef ", 1)[0]
        for c in SS.FORBIDDEN_COLUMNS:
            self.assertNotIn(f'"{c}"', body, f"{c} must not be read in the arm path")
        # vacuity: the O16 legs MUST be there, or the loop above proved nothing
        self.assertIn('"atm_iv_60"', body)
        self.assertIn('"atm_iv_front"', body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
