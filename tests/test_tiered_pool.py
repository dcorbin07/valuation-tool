# -*- coding: utf-8 -*-
"""`TIERED-POOL` — Don's stricter-bar-by-size idea, and the things that would make it a
different experiment from the one registered.

`PREREG_tiered_pool.md` fixed every band boundary, percentile, floor, kill and the pass rule
before any number. Most of this file pins that the code implements **that** register, because the
ways a tiered arm goes wrong are specific:

  * a percentile taken across the whole cross-section instead of within band is a single global
    cutoff in disguise, and it would look like a tiered rule;
  * a drawdown clause written without its sign reads a WORSENING as an improvement (`S10`);
  * a junk filter that treats an unresolvable input as PASSING flatters the arm;
  * and a size-neutral diagnostic that can be promoted on sight will be.
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fa():
    for c in (os.environ.get("VALQUO_DATA_ROOT"), os.path.join(REPO, "data"),
              r"C:\Users\donni\Downloads\valuation-tool\data"):
        if c and os.path.isdir(os.path.join(c, "free_analysis")):
            return os.path.join(c, "free_analysis")
    return None


def _src(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read()


def _rows(n_big=60, n_mid=120, n_small=120, tiny=True):
    rows = []
    for i in range(n_big):
        rows.append({"ticker": "B%03d" % i, "hot_score": 100.0 - i, "market_cap": 5e10,
                     "price": 10.0})
    for i in range(n_mid):
        rows.append({"ticker": "M%03d" % i, "hot_score": 90.0 - i, "market_cap": 5e9,
                     "price": 10.0})
    for i in range(n_small):
        rows.append({"ticker": "S%03d" % i, "hot_score": 80.0 - i, "market_cap": 1e9,
                     "price": 10.0})
    if tiny:
        rows.append({"ticker": "TINY", "hot_score": 999.0, "market_cap": 1e8, "price": 10.0})
    return rows


class TheBandsAreTheRegistersBands(unittest.TestCase):
    def test_the_boundaries_and_percentiles_are_the_registered_ones(self):
        from scripts.tiered_pool import BANDS, MICRO_CAP
        self.assertEqual([(n, lo, hi, p) for n, lo, hi, p in BANDS],
                         [("ge_10bn", 1e10, float("inf"), 0.10),
                          ("2bn_10bn", 2e9, 1e10, 0.05),
                          ("300M_2bn", 300e6, 2e9, 0.025)])
        self.assertEqual(MICRO_CAP, 300e6)

    def test_a_name_at_exactly_a_boundary_sits_in_the_HIGHER_band(self):
        """Half-open, as the register says. A closed interval would put a $10B name in two
        bands and the selection would depend on iteration order."""
        from scripts.tiered_pool import band_of
        self.assertEqual(band_of(1e10), "ge_10bn")
        self.assertEqual(band_of(1e10 - 1), "2bn_10bn")
        self.assertEqual(band_of(2e9), "2bn_10bn")
        self.assertEqual(band_of(2e9 - 1), "300M_2bn")
        self.assertEqual(band_of(300e6), "300M_2bn")

    def test_below_the_micro_cap_line_is_EXCLUDED_and_not_a_fourth_band(self):
        from scripts.tiered_pool import band_of
        self.assertIsNone(band_of(300e6 - 1))
        self.assertIsNone(band_of(1e8))
        self.assertIsNone(band_of(None))
        self.assertIsNone(band_of(float("nan")))


class ThePercentileIsWithinBandAndWithinDate(unittest.TestCase):
    """THE DEFECT THIS PINS: a percentile taken across the whole cross-section is a single
    global cutoff wearing a tiered rule's name, and it would still produce three band counts."""

    def test_each_band_gets_its_OWN_percentile_of_its_OWN_population(self):
        from scripts.tiered_pool import tiered_index_fn
        sink = []
        bk = tiered_index_fn(per_band_sink=sink)(_rows(60, 120, 120), held=None)
        self.assertEqual(sink[-1]["ge_10bn"], 6)        # 10% of 60
        self.assertEqual(sink[-1]["2bn_10bn"], 6)       # 5%  of 120
        self.assertEqual(sink[-1]["300M_2bn"], 3)       # 2.5% of 120
        self.assertTrue(bk["positions"])

    def test_a_global_cutoff_would_NOT_reproduce_those_counts(self):
        """Non-vacuity in the direction that matters: a single global percentile produces a
        DIFFERENT book, and the per-band counts are the check.

        **A DEFECT IN MY OWN FIRST FIXTURE, and it is worth keeping as the reason this test is
        phrased as counts rather than as band membership:** the scores overlapped across bands,
        so the global top 10% was NOT all large-cap and the stronger-looking claim was simply
        false. The property that actually distinguishes the two rules is the per-band split.
        """
        from scripts.tiered_pool import band_of, BANDS
        rows = _rows(60, 120, 120, tiny=False)
        rows.sort(key=lambda r: r["hot_score"], reverse=True)
        global_top = rows[:int(round(len(rows) * 0.10))]
        self.assertEqual(len(global_top), 30)
        got = {}
        for r in global_top:
            got[band_of(r["market_cap"])] = got.get(band_of(r["market_cap"]), 0) + 1
        tiered = {"ge_10bn": 6, "2bn_10bn": 6, "300M_2bn": 3}
        self.assertNotEqual(got, tiered,
                            "a global cutoff must not reproduce the tiered per-band counts")
        # and it is skewed toward the biggest band, which is the whole point of a stricter bar
        self.assertGreater(got.get("ge_10bn", 0), tiered["ge_10bn"])
        self.assertEqual(len(BANDS), 3)

    def test_the_micro_cap_name_never_enters_however_high_it_scores(self):
        from scripts.tiered_pool import tiered_index_fn
        bk = tiered_index_fn()(_rows(), held=None)
        self.assertNotIn("TINY", {p["ticker"] for p in bk["positions"]},
                         "a $100M name scoring 999 must still be excluded")


class TheNoTradeBandIsAppliedWithinEachBand(unittest.TestCase):
    def test_a_held_name_just_past_the_entry_rank_survives(self):
        from scripts.tiered_pool import tiered_index_fn
        rows = _rows(60, 120, 120, tiny=False)
        # B006 is rank 7 of 60 in the top band -- outside the top 6, inside the exit rank
        base = {p["ticker"] for p in tiered_index_fn()(rows, held=None)["positions"]}
        self.assertNotIn("B006", base)
        kept = {p["ticker"] for p in tiered_index_fn()(rows, held={"B006"})["positions"]}
        self.assertIn("B006", kept, "the band must keep a held name inside the exit rank")

    def test_a_held_name_far_down_its_band_does_NOT_survive(self):
        """A band that keeps anything held is not a band."""
        from scripts.tiered_pool import tiered_index_fn
        rows = _rows(60, 120, 120, tiny=False)
        kept = {p["ticker"] for p in tiered_index_fn()(rows, held={"B059"})["positions"]}
        self.assertNotIn("B059", kept)

    def test_the_band_is_the_SHIPPED_width_and_not_a_number_chosen_here(self):
        from valuation.edge.no_trade_band import BAND_WIDTH
        s = _src("scripts/tiered_pool.py")
        self.assertIn("from valuation.edge.no_trade_band import BAND_WIDTH", s)
        self.assertIn("BAND_WIDTH", s)
        self.assertNotIn("0.30", s.replace("0.300", ""), "the width must be imported, not typed")
        self.assertGreater(BAND_WIDTH, 0.0)


class TheWeightingIsTheShippedFunctionsAndNotThisRegisters(unittest.TestCase):
    def test_build_index_is_CALLED_with_the_tier_logic_switched_off(self):
        """`B7`. Re-implementing the 8% cap would make it a second definition."""
        s = _src("scripts/tiered_pool.py")
        self.assertIn("from valuation.edge.valquo_index import build_index", s)
        self.assertIn("build_index(chosen, large_cap_min=0.0, top_decile=1.0", s)
        self.assertIn("exit_frac=None", s)

    def test_no_weighting_arithmetic_is_implemented_here(self):
        """No `/ total`-shaped renormalisation and no 0.08 literal anywhere in the module."""
        s = _src("scripts/tiered_pool.py")
        self.assertNotIn("0.08", s)
        tree = ast.parse(s)
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("build_index", names, "build_index must be imported, never redefined")


class TheJunkFilterIsConservativeAndItsInputsArePointInTime(unittest.TestCase):
    def _hist(self, netinc, fcf, debt, equity, dk="2009-01-01"):
        row = {"datekey": dk, "netinc": netinc, "fcf": fcf, "debt": debt, "equity": equity,
               "reportperiod": dk}
        # four distinct quarters so `_ttm` can form a year
        out = []
        for i, d in enumerate(("2008-04-01", "2008-07-01", "2008-10-01", dk)):
            r = dict(row)
            r["datekey"] = d
            r["reportperiod"] = d
            out.append(r)
        return out

    def test_all_three_conditions_must_hold(self):
        from scripts.tiered_pool import junk_ok
        hist = {"GOOD": self._hist(10.0, 5.0, 1.0, 10.0),
                "LOSS": self._hist(-10.0, 5.0, 1.0, 10.0),
                "BURN": self._hist(10.0, -5.0, 1.0, 10.0),
                "LEVERED": self._hist(10.0, 5.0, 99.0, 1.0)}
        ok, st = junk_ok(list(hist), hist, "2009-06-30")
        self.assertTrue(ok["GOOD"])
        self.assertFalse(ok["LOSS"])
        self.assertFalse(ok["BURN"])
        self.assertFalse(ok["LEVERED"])
        self.assertEqual(st["removed_by_condition"]["netinc"], 1)
        self.assertEqual(st["removed_by_condition"]["fcf"], 1)

    def test_an_UNRESOLVABLE_input_FAILS_rather_than_passes(self):
        """The conservative direction. Treating a missing input as passing would let the arm
        hold exactly the names it cannot evaluate -- which flatters it."""
        from scripts.tiered_pool import junk_ok
        hist = {"NODATA": []}
        ok, st = junk_ok(["NODATA"], hist, "2009-06-30")
        self.assertFalse(ok["NODATA"])
        self.assertEqual(st["evaluable"], 0)

    def test_EACH_condition_fails_independently_when_its_OWN_input_is_absent(self):
        """A MUTATION MISS CLOSED. The test above passes a name with NOTHING resolvable, so all
        three conditions fail and flipping any ONE of them to pass-on-missing is invisible. Each
        condition needs a case where only ITS input is absent.
        """
        from scripts.tiered_pool import junk_ok
        base = {"netinc": 10.0, "fcf": 5.0, "debt": 1.0, "equity": 10.0}

        def hist_with(**over):
            rows = []
            for d in ("2008-04-01", "2008-07-01", "2008-10-01", "2009-01-01"):
                r = dict(base)
                r.update(over)
                r["datekey"] = d
                r["reportperiod"] = d
                rows.append(r)
            return rows

        # three otherwise-fine names so the leverage quantile can be formed at all
        for missing in ("netinc", "fcf"):
            hist = {"FILL1": hist_with(), "FILL2": hist_with(), "GAP": hist_with(**{missing: ""})}
            ok, _st = junk_ok(list(hist), hist, "2009-06-30")
            self.assertTrue(ok["FILL1"], "the control name must pass")
            self.assertFalse(ok["GAP"],
                             "a name with %s absent must FAIL, not pass on missing" % missing)
        # and leverage: equity absent -> no ratio -> fail
        hist = {"FILL1": hist_with(), "FILL2": hist_with(), "GAP": hist_with(equity="")}
        ok, _st = junk_ok(list(hist), hist, "2009-06-30")
        self.assertFalse(ok["GAP"], "a name with no leverage ratio must FAIL")

    def test_a_boundary_name_is_selected_by_exactly_ONE_band(self):
        """A MUTATION MISS CLOSED, and the fix was to the CODE rather than the test: the band
        test existed TWICE, in `band_of` and inside `tiered_index_fn`. Flipping one copy to a
        CLOSED interval was INERT in `band_of` -- it returns the FIRST matching band -- while
        being live in the selector, so a $10B name could be picked by two bands with both halves
        correct in isolation. `tiered_index_fn` now calls `band_of`, so there is one definition.
        """
        from scripts.tiered_pool import tiered_index_fn
        rows = [{"ticker": "EDGE", "hot_score": 100.0, "market_cap": 1e10, "price": 10.0}]
        for i in range(9):
            rows.append({"ticker": "P%d" % i, "hot_score": 50.0 - i, "market_cap": 5e10,
                         "price": 10.0})
        sink = []
        bk = tiered_index_fn(per_band_sink=sink)(rows, held=None)
        picked = [p["ticker"] for p in bk["positions"]]
        self.assertEqual(picked.count("EDGE"), 1 if "EDGE" in picked else 0,
                         "a boundary name must never appear twice in the book")
        self.assertEqual(sink[-1].get("2bn_10bn", 0), 0,
                         "a $10B name must not also be selected by the $2-10B band")

    def test_the_evaluable_share_is_reported_so_the_kill_can_read_it(self):
        from scripts.tiered_pool import junk_ok
        hist = {"A": self._hist(10.0, 5.0, 1.0, 10.0),
                "B": self._hist(10.0, 5.0, 1.0, 10.0),
                "C": self._hist(10.0, 5.0, 1.0, 10.0),
                "D": []}
        _ok, st = junk_ok(list(hist), hist, "2009-06-30")
        self.assertEqual(st["rows"], 4)
        self.assertEqual(st["evaluable"], 3)
        self.assertAlmostEqual(st["evaluable_share"], 0.75)

    def test_the_TTM_accessor_is_the_SHIPPED_one(self):
        """`_ttm` already collapses restatements (`D10-a`) and refuses a partial sum. A
        hand-rolled sum would understate a flow and read as a JUNK company -- the direction
        that would flatter this arm."""
        s = _src("scripts/tiered_pool.py")
        self.assertIn("from valuation.edge.fundamental_panel import _ttm", s)
        tree = ast.parse(s)
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertNotIn("_ttm", names, "_ttm must be imported, never redefined")

    def test_the_leverage_direction_is_the_PAPERS_and_the_cut_is_the_registered_quantile(self):
        from scripts.tiered_pool import LEVERAGE_WORST_THIRD_Q, junk_ok
        self.assertAlmostEqual(LEVERAGE_WORST_THIRD_Q, 2.0 / 3.0)
        # five names: the two most levered must fail, the three least must pass
        hist = {}
        for i, lv in enumerate((0.1, 0.2, 0.3, 5.0, 9.0)):
            hist["N%d" % i] = self._hist(10.0, 5.0, lv, 1.0)
        ok, st = junk_ok(list(hist), hist, "2009-06-30")
        self.assertTrue(ok["N0"] and ok["N1"] and ok["N2"])
        self.assertFalse(ok["N4"], "the most levered name must fail")
        self.assertIsNotNone(st["leverage_cut"])

    def test_the_currency_argument_is_recorded_rather_than_hoped_for(self):
        """`P7` is this project's most expensive bug. All three conditions are
        currency-invariant and the module says why."""
        s = _src("scripts/tiered_pool.py")
        self.assertIn("P7", s)
        self.assertIn("currency-invariant", s)
        self.assertNotIn("fxusd", s.replace("`fxusd > 0`", ""),
                         "no conversion is applied, so no fx divisor should be read")

    def test_the_filter_touches_only_the_bands_below_10bn(self):
        """Arm B is 'arm A PLUS a filter'. Filtering the top band too would make it a third
        arm, which the register's void condition 3 forbids."""
        from scripts.tiered_pool import junk_universe_filter, UNFILTERED_BAND
        self.assertEqual(UNFILTERED_BAND, "ge_10bn")
        rows = _rows(3, 3, 3, tiny=False)
        ok = {}                                  # nothing passes the filter
        f = junk_universe_filter({"2009-01-15": ok})
        out = f(rows, "2009-01-15")
        kept = {r["ticker"][0] for r in out}
        self.assertEqual(kept, {"B"}, "only the >= $10B band survives an all-fail filter")


class TheCoverageKillIsInheritedAndReadFirst(unittest.TestCase):
    def test_the_floor_is_the_inherited_0_70_and_says_so(self):
        from scripts.tiered_pool import JUNK_COVERAGE_FLOOR
        self.assertEqual(JUNK_COVERAGE_FLOOR, 0.70)
        self.assertIn("INHERITED", _src("scripts/tiered_pool.py"))

    def test_the_arms_pass_REFUSES_without_a_kill_artifact(self):
        """`O10`'s process defect: a gating control computed in the same pass as the outcomes
        cannot be claimed to have been read first."""
        s = _src("scripts/tiered_pool_run.py")
        self.assertIn("REFUSING: no coverage-kill artifact", s)
        self.assertIn("def kill_pass", s)
        self.assertLess(s.index("def kill_pass"), s.index("def arms_pass"))

    def test_a_fired_kill_means_arm_B_does_not_run_rather_than_running_degraded(self):
        s = _src("scripts/tiered_pool_run.py")
        self.assertIn('run_b = bool(kill.get("all_pass"))', s)
        self.assertIn("arm_b_not_run_reason", s)

    def test_the_landed_kill_artifact_passed_non_vacuously(self):
        fa = _fa()
        p = os.path.join(fa or "", "TIERED_POOL_KILL.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: kill artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertEqual(d["floor"], 0.70)
        for label, v in d["periods"].items():
            self.assertGreater(v["sub_10bn_rows"], 0, "%s compared nothing" % label)
            self.assertGreaterEqual(v["evaluable_share"], 0.70)


class DonsRuleIsImplementedAsWritten(unittest.TestCase):
    def _inc(self):
        return {"full": 0.18, "early": 0.19, "late": 0.16, "oos": 0.08,
                "mdd_full": -0.29, "mdd_oos": -0.42}

    def test_an_arm_must_beat_the_incumbent_in_ALL_FOUR_windows(self):
        from scripts.tiered_pool import decide
        inc = self._inc()
        arm = dict(inc)
        for k in ("full", "early", "late", "oos"):
            arm[k] = inc[k] + 0.01
        self.assertTrue(decide(arm, inc)["PASSES"])
        for k in ("full", "early", "late", "oos"):
            bad = dict(arm)
            bad[k] = inc[k] - 0.0001
            self.assertFalse(decide(bad, inc)["PASSES"], "%s must be required" % k)

    def test_beats_is_STRICT_and_a_tie_FAILS(self):
        from scripts.tiered_pool import decide
        inc = self._inc()
        arm = dict(inc)
        arm["mdd_full"] = inc["mdd_full"]
        arm["mdd_oos"] = inc["mdd_oos"]
        self.assertFalse(decide(arm, inc)["PASSES"], "equal returns must not pass")

    def test_the_drawdown_clause_is_written_WITH_ITS_SIGN_both_ways(self):
        """`S10`'s first cut reported a 2.61pp WORSENING as an improvement. Drawdowns are
        negative, so 'no more than 3pp worse' is `arm >= inc - 0.03`."""
        from scripts.tiered_pool import decide, DD_ALLOWANCE
        self.assertEqual(DD_ALLOWANCE, 0.03)
        inc = self._inc()
        arm = {k: (v + 0.01 if k in ("full", "early", "late", "oos") else v)
               for k, v in inc.items()}
        arm["mdd_full"] = inc["mdd_full"] - 0.0299          # 2.99pp worse -> inside
        self.assertTrue(decide(arm, inc)["PASSES"])
        arm["mdd_full"] = inc["mdd_full"] - 0.0301          # 3.01pp worse -> outside
        self.assertFalse(decide(arm, inc)["PASSES"])
        arm["mdd_full"] = inc["mdd_full"] + 0.10            # BETTER drawdown -> inside
        self.assertTrue(decide(arm, inc)["PASSES"])

    def test_the_rule_CAN_fail_everything_and_says_it_is_not_a_significance_test(self):
        from scripts.tiered_pool import decide
        inc = self._inc()
        d = decide({k: (v - 0.05 if not k.startswith("mdd") else v - 0.5)
                    for k, v in inc.items()}, inc)
        self.assertFalse(d["PASSES"])
        self.assertIn("not a significance test", d["not_significance"])

    def test_a_missing_figure_does_not_silently_pass(self):
        from scripts.tiered_pool import decide
        inc = self._inc()
        arm = dict(inc)
        arm["oos"] = None
        self.assertFalse(decide(arm, inc)["PASSES"])


class TheSizeNeutralDiagnosticCannotAcquireAVerdict(unittest.TestCase):
    def test_it_is_reported_with_the_literal_NO_VERDICT(self):
        """A MUTATION MISS CLOSED. The first cut only asked that the STRING appear somewhere in
        the file, and the file contains it twice -- so changing the one that actually lands on
        the diagnostic was invisible. Read the ASSIGNMENT off the AST instead."""
        src = _src("scripts/tiered_pool_addendum.py")
        tree = ast.parse(src)
        found = []
        for n in ast.walk(tree):
            if not isinstance(n, ast.Assign):
                continue
            for t in n.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and t.slice.value == "verdict"):
                    found.append(n.value)
        self.assertTrue(found, "nothing assigns a `verdict` key at all")
        for v in found:
            self.assertIsInstance(v, ast.Constant)
            self.assertEqual(v.value, "NO-VERDICT",
                             "the diagnostic's verdict must be the literal NO-VERDICT")

    def test_it_never_reaches_the_decision(self):
        """`E-3`/`MB21`: a number that COULD be promoted on sight WILL be."""
        s = _src("scripts/tiered_pool_run.py")
        self.assertNotIn("size_neutral", s,
                         "the runner that applies Don's rule must not see the diagnostic")

    def test_the_registers_own_degeneracy_is_REPORTED_not_swapped(self):
        """§3 as registered IS arm A, because arm A's percentile is already within band. The
        honest handling is `E-3`'s: report it, do not quietly substitute a different control
        after seeing the arms."""
        s = _src("scripts/tiered_pool_addendum.py")
        self.assertIn("DEGENERATE", s)
        self.assertIn("degenerate_vs_arm_A", s)
        self.assertIn("non_degenerate_version_NOT_run", s)

    def test_the_degeneracy_is_MEASURED_in_the_landed_artifact(self):
        fa = _fa()
        p = os.path.join(fa or "", "TIERED_POOL_ADDENDUM.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: addendum artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        for label, v in d["periods"].items():
            sn = v.get("size_neutral")
            self.assertIsNotNone(sn, "%s has no diagnostic" % label)
            self.assertEqual(sn["verdict"], "NO-VERDICT")
            self.assertEqual(sn["degenerate_vs_arm_A"]["max_abs_dev_roth"], 0.0,
                             "%s: the degeneracy is asserted rather than measured" % label)


class NoAlphaClaimAndNoCalibratedFloor(unittest.TestCase):
    def test_no_X7_floor_is_quoted_anywhere(self):
        for f in ("tiered_pool.py", "tiered_pool_run.py", "tiered_pool_addendum.py"):
            s = _src("scripts/" + f)
            for fl in ("2.2837", "2.0540", "2.7072", "19.667", "1.8629", "0.6637",
                       "2.070231", "2.056680", "1.826210"):
                self.assertNotIn(fl, s, "%s quotes the X7 floor %s" % (f, fl))

    def test_every_margin_ships_with_its_own_MDE_and_an_UNCALIBRATED_label(self):
        from scripts.tiered_pool import mde
        m = mde([0.01, 0.02, -0.01, 0.00, 0.03])
        self.assertIn("mde_50pc", m)
        self.assertIn("mde_80pc", m)
        self.assertGreater(m["mde_80pc"], m["mde_50pc"])
        self.assertIn("UNCALIBRATED", m["crit_label"])

    def test_the_80_percent_MDE_is_MB22s_formula_and_not_the_retired_convention(self):
        from scripts.tiered_pool import mde
        m = mde([0.01, 0.02, -0.01, 0.00, 0.03])
        self.assertAlmostEqual(m["mde_50pc"], 2.0 * m["paired_se"])
        self.assertAlmostEqual(m["mde_80pc"], (2.0 + 0.84) * m["paired_se"])

    def test_the_alpha_prohibition_is_carried_in_every_script(self):
        for f in ("tiered_pool.py", "tiered_pool_run.py", "tiered_pool_addendum.py"):
            self.assertIn("NO ALPHA CLAIM", _src("scripts/" + f).upper())


class TheArmsRunOnTheCorrectedUniverseAndThePartBLabelTravels(unittest.TestCase):
    def test_neither_period_reads_data_backtest(self):
        """A tiered-pool arm is a claim about the SMALL END, and `data/backtest` is missing
        80.61% of the names that were small in 2009 and later died -- running it there would be
        measuring the defect."""
        from scripts.tiered_pool_run import PERIODS
        for _label, _pkl, exp, _themes, _note in PERIODS:
            self.assertNotEqual(tuple(exp), ("backtest",))
            self.assertNotIn("backtest", exp[0])

    def test_part_b_is_labelled_a_five_theme_proxy_wherever_it_is_quoted(self):
        from scripts.tiered_pool_run import PERIODS
        note = [n for lbl, _p, _e, _t, n in PERIODS if lbl == "1999_2008"][0]
        self.assertIn("FIVE-THEME", note.upper())
        self.assertIn("PROXY", note.upper())
        self.assertIn("NOT comparable", note)

    def test_part_b_uses_the_pre_2009_theme_set_and_not_the_deployed_seven(self):
        from scripts.tiered_pool_run import PERIODS
        from scripts.pool_size_oos import THEMES_PRE2009
        themes = [t for lbl, _p, _e, t, _n in PERIODS if lbl == "1999_2008"][0]
        self.assertEqual(tuple(themes), tuple(THEMES_PRE2009))
        self.assertEqual(len(THEMES_PRE2009), 5)

    def test_the_live_theme_check_is_REUSED_and_not_a_column_count(self):
        """`UNIVERSE-BIAS` lost a whole pass to counting columns PRESENT: a constant column is
        present and dead."""
        s = _src("scripts/tiered_pool_run.py")
        self.assertIn("from scripts.universe_bias_arms import live_themes", s)
        self.assertNotIn("c in panel.columns]", s)

    def test_the_incumbent_is_INDEX_BESTs_and_not_re_specified(self):
        from scripts.tiered_pool_run import INCUMBENT_KW
        self.assertEqual(INCUMBENT_KW["large_cap_min"], 1e10)
        self.assertIsNone(INCUMBENT_KW["universe_rank"])
        self.assertIsNone(INCUMBENT_KW["top_n"])


class TheLandedResultIsInternallyConsistent(unittest.TestCase):
    def test_both_arms_failed_and_the_artifact_says_why(self):
        fa = _fa()
        p = os.path.join(fa or "", "TIERED_POOL.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: arms artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertEqual(d["trials"], 2)
        for arm in ("A_tiered", "B_tiered_junk"):
            dec = d["decision"][arm]
            self.assertFalse(dec["PASSES"])
            # the 1999-2008 leg is the one both arms WIN, so the failure must come from 2009-2026
            self.assertTrue(dec["return_steps"]["1999-2008 proxy"]["beats"])
            self.assertFalse(dec["return_steps"]["2009-2026 full"]["beats"])

    def test_the_micro_cap_exclusion_shows_as_zero_weight_on_every_arm(self):
        fa = _fa()
        p = os.path.join(fa or "", "TIERED_POOL_ADDENDUM.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: addendum artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        for label, v in d["periods"].items():
            for arm, c in (v.get("composition") or {}).items():
                self.assertEqual(c["weight_below"]["300M"]["max"], 0.0,
                                 "%s/%s holds weight below the excluded line" % (label, arm))


if __name__ == "__main__":
    unittest.main(verbosity=2)
