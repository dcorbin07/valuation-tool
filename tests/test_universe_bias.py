# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` — the correction, and the things that would make it meaningless.

`POOL-SIZE` found that `data/backtest`'s universe is the top ~3,000 by **2026** market cap plus
the live set. That is a present-day property, so it can flatter small-cap and wider-pool results
**for 2009-2026 too**. This item measures the bias and re-measures the registered arms on a
corrected universe.

**THE DESIGN IS THE CLAIM, so most of this file pins the design.** A corrected-universe
comparison is worthless if anything other than the universe moved:

  * **ONE VINTAGE.** Both panels come from the 2026-10 freeze and both are cut at
    `data/backtest`'s own newest close. Comparing against the BANKED panel instead would
    conflate the universe with a rolled window, which `SHARADAR-REFRESH` measured.
  * **ONE BUILDER.** The shipped `build_fundamental_panel`, same parameters both sides.
  * **ONE EXPORT WRITER.** The readers are reused from `pool_size_oos_prep`, never copied.
  * **ZERO TRIALS**, because every arm is already registered and the decision rule was fixed
    before any number -- and the item must not quietly become a search.
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


def _src(name):
    return io.open(os.path.join(REPO, "scripts", name), encoding="utf-8").read()


class TheComparisonVariesONLYTheUniverse(unittest.TestCase):
    def test_both_sides_are_cut_at_the_same_vintage(self):
        """`SHARADAR-REFRESH` measured the confound: 2,531 names at 2026-07-24 against 3,049 at
        2026-10-02. Cutting the full export at `data/backtest`'s own newest close removes it."""
        s = _src("universe_bias_prep.py")
        self.assertIn('CUT = "2026-10-02"', s)
        self.assertIn("share a vintage", s)

    def test_the_restricted_side_is_data_backtest_itself(self):
        s = _src("universe_bias_arms.py")
        self.assertIn('"restricted", os.path.join(data, "backtest")', s)

    def test_the_full_side_is_the_raw_built_export(self):
        s = _src("universe_bias_arms.py")
        self.assertIn("full2009", s)

    def test_both_sides_use_the_SHIPPED_builder_with_the_same_parameters(self):
        """One builder, one parameter set -- or the difference is not the universe."""
        tree = ast.parse(_src("universe_bias_arms.py"))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and getattr(n.func, "id", "")
                 == "build_fundamental_panel"]
        self.assertEqual(len(calls), 1,
                         "there must be exactly ONE build call, shared by both sides")

    def test_the_export_writers_are_REUSED_not_copied(self):
        """`B7`. A second copy of an export writer is how two panels come to be built on
        quietly different rules."""
        s = _src("universe_bias_prep.py")
        self.assertIn("import scripts.pool_size_oos_prep as P", s)
        for fn in ("prep_prices", "prep_fundamentals", "prep_benchmark"):
            self.assertIn("P.%s(" % fn, s)
            self.assertNotIn("def %s(" % fn, s, "%s is COPIED, not reused" % fn)

    def test_the_prep_restores_the_shared_constants_it_borrows(self):
        """It sets the other module's CUT/WINDOW_FROM for the run; leaving them changed would
        silently alter a later 1999-2008 prep."""
        s = _src("universe_bias_prep.py")
        self.assertIn("finally:", s)
        self.assertIn("P.CUT, P.WINDOW_FROM = old_cut, old_from", s)


class ItChargesNothingAndSaysWhy(unittest.TestCase):
    def test_both_scripts_declare_zero_trials(self):
        for f in ("universe_bias.py", "universe_bias_prep.py", "universe_bias_arms.py"):
            self.assertIn("ZERO TRIALS", _src(f).upper().replace("ZERO TRIALS.", "ZERO TRIALS"))

    def test_the_arms_runner_names_the_correction_class(self):
        s = _src("universe_bias_arms.py")
        self.assertIn("RE-MEASUREMENT", s)
        self.assertIn("X7RECON", s)
        self.assertIn("no new degree of freedom", s)

    def test_the_arms_and_the_rule_are_INHERITED_not_invented(self):
        """The rule must come from the committed register, or this becomes a search."""
        s = _src("universe_bias_arms.py")
        self.assertIn("from scripts.pool_size import decide", s)
        self.assertIn("PREREG_pool_size.md", s)
        tree = ast.parse(s)
        # no bar-shaped float constant may be introduced here
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, float):
                self.assertNotEqual(n.value, 0.03,
                                    "the 3pp allowance must be inherited, never restated")


class ThePublishedFigureIsTreatedAsADifferentVintage(unittest.TestCase):
    def test_the_published_incumbent_is_quoted_with_its_vintage(self):
        from scripts import universe_bias_arms as A
        self.assertEqual(A.PUBLISHED_INCUMBENT_ROTH, 0.1716188056513155)
        self.assertIn("2026-07-24", A.PUBLISHED_VINTAGE)

    def test_the_quoted_figure_matches_the_banked_artifact(self):
        fa = _fa()
        p = os.path.join(fa or "", "INDEX_BEST.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: INDEX_BEST.json is not on this machine")
        from scripts import universe_bias_arms as A
        arm = json.load(io.open(p, encoding="utf-8"))["arms"]["1_incumbent_10bn"]
        self.assertEqual(float(arm["roth_net_ann"]), A.PUBLISHED_INCUMBENT_ROTH)

    def test_the_runner_does_not_claim_to_REPRODUCE_the_published_figure(self):
        """It is a near-neighbour at a different vintage, so a 0.000e+00 gate would be wrong
        and claiming reproduction would be worse."""
        s = _src("universe_bias_arms.py")
        self.assertIn("near-neighbour", s)
        self.assertIn("not assumed", s)


class TheCensusMeasuresTheBiasAndNotJustTheGap(unittest.TestCase):
    def test_it_compares_the_small_and_DEAD_rate_against_the_small_and_ALIVE_rate(self):
        """A gap in counts is not a bias. What makes it one is the missing rate being higher
        among names that DIED than among names that survived -- so the ALIVE leg is the
        comparator and the dead leg alone is not quotable.

        Read from the artifact's own dict LITERAL rather than by substring, so it holds on a
        machine with no artifact on disk, and so a guard documenting the rule cannot satisfy it.
        """
        tree = ast.parse(_src("universe_bias.py"))
        keys = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Dict):
                for k in n.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        keys.add(k.value)
        self.assertIn("small_2009_and_died", keys)
        self.assertIn("small_2009_and_alive", keys,
                      "the dead leg ships without its comparator, so the missing rate reads as "
                      "a bias when it may just be the base rate")
        # non-vacuity: the stripper really does see this file's keys
        self.assertIn("names_per_date", keys)

    def test_it_applies_the_SAME_filter_to_both_universes(self):
        s = _src("universe_bias.py")
        self.assertIn("sf1_covered", s)
        self.assertIn("in_win & covered", s)

    def test_the_census_artifact_records_a_non_random_direction(self):
        fa = _fa()
        p = os.path.join(fa or "", "UNIVERSE_BIAS_CENSUS.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: census artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        dead = d["small_2009_and_died"]["missing_share"]
        alive = d["small_2009_and_alive"]["missing_share"]
        self.assertGreater(dead, alive,
                           "if the missing rate were not higher among dead names there would "
                           "be no bias to report in this direction")
        self.assertGreater(d["delisted_full"]["share"], d["delisted_restricted"]["share"])
        self.assertEqual(d["trials"], 0)


class NoAlphaClaimAndNoX7Floor(unittest.TestCase):
    def test_no_calibrated_floor_is_quoted(self):
        for f in ("universe_bias.py", "universe_bias_prep.py", "universe_bias_arms.py"):
            s = _src(f)
            for fl in ("2.2837", "2.0540", "2.7072", "19.667", "1.8629"):
                self.assertNotIn(fl, s, "%s quotes the X7 floor %s" % (f, fl))

    def test_the_alpha_prohibition_is_carried_forward(self):
        self.assertIn("no_alpha_claim", _src("universe_bias_arms.py"))


class TheSharedCachesAreNotTouched(unittest.TestCase):
    def test_neither_script_writes_a_bulk_pickle_cache(self):
        """Overwriting the shared `daily.pkl` / `actions.pkl` would break every 2009-2026 panel
        build in the repo."""
        for f in ("universe_bias.py", "universe_bias_prep.py"):
            tree = ast.parse(_src(f))
            lits = [n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and n.value.endswith(".pkl")]
            self.assertEqual(lits, [], "%s writes a pickle cache" % f)

    def test_the_arms_runner_points_bulk_dir_at_the_existing_cache(self):
        s = _src("universe_bias_arms.py")
        self.assertIn("prov._bulk_dir = bulk_dir", s)
        self.assertIn("NOT rebuilt, NOT overwritten", s)


class TheCensusAndTheRegressionAreCALLEDNotCopied(unittest.TestCase):
    """`B7`. Both were parameterised with defaults equal to the original, so POOL-SIZE's own
    callers are bit-identical and both universes are measured by the SAME code."""

    def test_the_census_runner_delegates(self):
        s = _src("universe_bias_diag.py")
        self.assertIn("import scripts.pool_size_diag as D", s)
        self.assertIn("D.main(", s)
        self.assertNotIn("def books_per_date(", s)
        self.assertNotIn("BUCKETS = [", s)

    def test_the_factors_runner_delegates(self):
        s = _src("universe_bias_factors.py")
        self.assertIn("import scripts.pool_size_factors as PF", s)
        self.assertIn("PF.main(", s)
        self.assertNotIn("FF_MODEL", s.replace("FF5+MOM", ""))
        self.assertNotIn("ols_nw", s)

    def test_both_parameterised_defaults_equal_the_ORIGINAL_object(self):
        """A parameterisation that changes an existing caller's behaviour is a rewrite. The
        defaults must resolve to POOL-SIZE's own panel and POOL-SIZE's own artifact."""
        import inspect
        from scripts import pool_size_diag as D
        from scripts import pool_size_factors as PF
        for mod in (D, PF):
            sig = inspect.signature(mod.main)
            for name in ("panel_path", "out"):
                self.assertIn(name, sig.parameters, "%s.main lacks %s" % (mod.__name__, name))
                self.assertIsNone(sig.parameters[name].default,
                                  "%s.main's %s must default to None so the original path "
                                  "is unchanged" % (mod.__name__, name))
            src = inspect.getsource(mod.main)
            self.assertIn('panel_path or os.path.join(FA, "panel_corrected_69d.pkl")', src)
            self.assertIn("out or OUT", src)

    def test_the_write_destination_is_the_one_that_is_REPORTED(self):
        """A print naming one path while the write goes to another is not a cosmetic defect: it
        is how a reader comes to believe an artifact was clobbered when it was not, and acts on
        it. This cost a correct artifact in this very item."""
        for f in ("pool_size_diag.py", "pool_size_factors.py"):
            s = _src(f)
            self.assertIn('wrote %s" % dest', s,
                          "%s reports OUT while writing to dest" % f)

    def test_the_factors_runner_refuses_rather_than_re_forming_the_books(self):
        s = _src("universe_bias_factors.py")
        self.assertIn("REFUSING", s)
        self.assertIn("net_series", s)
        self.assertNotIn("book_fn", s)

    def test_the_arms_runner_banks_the_series_the_regression_reads(self):
        s = _src("universe_bias_arms.py")
        self.assertIn('r["net_series"] = [float(x) for x in ns]', s)

    def test_the_factors_runner_charges_zero_and_makes_no_alpha_claim(self):
        s = _src("universe_bias_factors.py")
        self.assertIn("trials=0", s)
        self.assertIn("NO ALPHA CLAIM", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
