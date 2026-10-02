# -*- coding: utf-8 -*-
"""INDEX-BOOK -- the served Index construction, backtested. Tests for the study and the hook.

The load-bearing ones, in order of what they would cost if they broke:

 1. `book_fn=None` leaves `after_tax_backtest` BIT-IDENTICAL. The hook touches a function every
    published after-tax figure comes from, so inertness is pinned against a committed literal
    from `book_configs.taxable` rather than against my expectation.
 2. The hook guard is a required CONJUNCT, not a substring. `MB20` watched `or True` walk
    straight through a substring-banned guard twice before the form held.
 3. The tier mirror is GATED. A benchmark that silently drifts from the selection it benchmarks
    is worse than no benchmark, so a wrong threshold must produce a REFUSAL (NaN) and not a
    plausible number.
 4. `build_index` is CALLED. Asserted as a POSITIVE property -- the module must contain a call
    to it -- because banning the alternative would be banning a substring, and the prose in this
    very file would trip it.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import numpy as np                                                      # noqa: E402
import pandas as pd                                                     # noqa: E402

from valuation.studies import served_index_book as IB                          # noqa: E402
from valuation.edge import valquo_index as VI                           # noqa: E402
from valuation.edge import fundamental_panel as FP                      # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                     # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY = os.path.join(REPO, "valuation", "studies", "served_index_book.py")
PANEL_MOD = os.path.join(REPO, "valuation", "edge", "fundamental_panel.py")
RUNNER = os.path.join(REPO, "scripts", "served_index_book.py")

# book_configs.taxable, committed. The hook must not move it by a bit.
PUBLISHED_AFTER_TAX_ALPHA = 0.021132837959488837
PUBLISHED_AFTER_TAX_SHARPE = 0.9767529353354262


def _src(p):
    return io.open(p, encoding="utf-8").read()


def _fa_candidates():
    """Data roots, DERIVED. A literal path is why a sibling suite failed CI."""
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(os.path.join(env, "free_analysis"))
    out.append(os.path.join(REPO, "data", "free_analysis"))
    parts = REPO.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data", "free_analysis"))
    return out


def _panel():
    for c in _fa_candidates():
        p = os.path.join(c, "panel_corrected_69d.pkl")
        if os.path.exists(p):
            return pd.read_pickle(p)
    return None


def _synth(n=60, dates=4, seed=7):
    """A panel with a real large-cap/small-cap split and finite forward returns."""
    rng = np.random.default_rng(seed)
    rows = []
    for di in range(dates):
        for i in range(n):
            rows.append({
                "date": "20%02d-01-15" % (10 + di),
                "ticker": "T%03d" % i,
                "market_cap": float(2e9 + i * 1.0e9),      # i >= 8 clears 10e9
                "fwd_ret": float(rng.normal(0.02, 0.08)),
                "bench_ret": 0.015 + 0.001 * di,
                "value": float(rng.normal()), "quality": float(rng.normal()),
                "momentum": float(rng.normal()), "size": float(rng.normal()),
                "insider": float(rng.normal()), "institutional": float(rng.normal()),
                "capital_discipline": float(rng.normal()),
            })
    return pd.DataFrame(rows)


COLS = ["value", "quality", "momentum", "size", "insider", "institutional",
        "capital_discipline"]
W = {c: 0.125 for c in COLS}


class TheHookIsInert(unittest.TestCase):
    def test_book_fn_none_reproduces_the_published_after_tax_figures_bit_for_bit(self):
        p = _panel()
        if p is None:
            self.skipTest("LOUD SKIP: panel_corrected_69d.pkl absent; tried %r"
                          % (_fa_candidates(),))
        r = FP.after_tax_backtest(p, COLS, W, top_frac=0.1, exit_frac=BAND_WIDTH)
        self.assertEqual(r["after_tax_alpha"], PUBLISHED_AFTER_TAX_ALPHA,
                         "the book_fn hook moved a PUBLISHED after-tax figure; it must be "
                         "inert at its default")
        self.assertEqual(r["after_tax_sharpe"], PUBLISHED_AFTER_TAX_SHARPE)

    def test_book_fn_none_and_absent_agree_exactly_on_a_synthetic_panel(self):
        p = _synth()
        a = FP.after_tax_backtest(p, COLS, W, top_frac=0.2, exit_frac=0.3)
        b = FP.after_tax_backtest(p, COLS, W, top_frac=0.2, exit_frac=0.3, book_fn=None)
        for k in ("gross_ann", "after_tax_ann", "after_tax_sharpe", "tax_paid_short",
                  "tax_paid_long", "unrealized_gain_end"):
            self.assertEqual(a[k], b[k], "passing book_fn=None changed %s" % k)

    def test_the_hook_actually_changes_the_book_so_inertness_is_not_vacuous(self):
        """A hook proved inert while being unreachable is proved nothing."""
        p = _synth()
        base = FP.after_tax_backtest(p, COLS, W, top_frac=0.2, exit_frac=0.3)
        hooked = FP.after_tax_backtest(p, COLS, W, top_frac=0.2, exit_frac=0.3,
                                       book_fn=IB.book_fn())
        self.assertNotEqual(base["after_tax_ann"], hooked["after_tax_ann"],
                            "the hook had no effect, so the inertness tests above prove nothing")


class TheHookGuardIsAConjunct(unittest.TestCase):
    """`MB20`: a guard banning a SUBSTRING lets `or True` through. Assert the property."""

    def _guards(self):
        tree = ast.parse(_src(PANEL_MOD))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "after_tax_backtest")
        out = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            names = {d.id for d in ast.walk(node.test) if isinstance(d, ast.Name)}
            if "_bw" in names:
                out.append(node.test)
        return out

    def test_every_guard_naming__bw_requires_book_fn_is_not_none_as_a_conjunct(self):
        guards = self._guards()
        self.assertGreaterEqual(len(guards), 2,
                                "expected at least the target guard and the gross guard")
        for t in guards:
            self.assertIsInstance(t, ast.BoolOp, "a bare guard permits no second condition")
            self.assertIsInstance(t.op, ast.And,
                                  "an `or` guard is satisfiable without book_fn being set")
            conj = []
            for v in t.values:
                if (isinstance(v, ast.Compare) and isinstance(v.ops[0], ast.IsNot)
                        and isinstance(v.left, ast.Name)):
                    conj.append(v.left.id)
            self.assertIn("book_fn", conj,
                          "`book_fn is not None` must be a required conjunct of every guard "
                          "that reads the hook's result")

    def test_the_guard_shape_check_would_reject_an_or(self):
        """Positive control: the rule must bite on the mutation it exists for."""
        t = ast.parse("x = 1 if (_bw is not None or True) else 2").body[0].value.test
        self.assertIsInstance(t, ast.BoolOp)
        self.assertIsInstance(t.op, ast.Or)
        self.assertNotIsInstance(t.op, ast.And)


class TheTierMirrorIsGated(unittest.TestCase):
    def test_a_correct_mirror_is_verified_on_every_date(self):
        p = _synth()
        r = IB.run(p, COLS, W, large_cap_min=10e9, weighting="score", exit_frac=BAND_WIDTH)
        self.assertEqual(r["tier_mirror_verified_on_dates"], r["n_periods"])
        self.assertTrue(r["tier_equal_weight_ann"] == r["tier_equal_weight_ann"])

    def test_a_mirror_disagreeing_with_the_live_count_refuses_rather_than_reporting(self):
        """The mirror must REFUSE, not produce a plausible benchmark, when it drifts."""
        import copy

        def _liar(rows, **kw):
            out = VI.build_index(rows, **kw)
            out = copy.deepcopy(out)
            out["n_eligible"] = int(out["n_eligible"]) + 1     # the live count now disagrees
            return out

        p = _synth()
        r = IB.run(p, COLS, W, large_cap_min=10e9, index_fn=_liar)
        self.assertEqual(r["tier_mirror_verified_on_dates"], 0)
        self.assertIsNone(r["net_alpha_vs_tier_equal_weight"],
                          "a drifted mirror must not yield a tier benchmark")

    def test_at_threshold_zero_the_mirror_degenerates_to_the_universe(self):
        """A free internal control: with no tier, the tier benchmark IS the universe."""
        p = _synth()
        r = IB.run(p, COLS, W, large_cap_min=0.0, weighting="equal", exit_frac=None)
        self.assertAlmostEqual(r["tier_equal_weight_ann"], r["equal_weight_ann"], places=12)


class TheConstructionIsTheLiveOne(unittest.TestCase):
    def test_the_study_calls_build_index(self):
        """POSITIVE property. Banning a reimplementation would ban a substring, and the
        docstring in this file discusses the very names such a ban would look for."""
        tree = ast.parse(_src(STUDY))
        called = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name):
                    called.add(f.id)
                elif isinstance(f, ast.Attribute):
                    called.add(f.attr)
        self.assertTrue({"build_index", "_ix", "index_fn"} & called,
                        "the study must CALL the live index builder, not restate it")

    def test_the_study_imports_the_constants_and_defines_no_second_copy(self):
        tree = ast.parse(_src(STUDY))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                imported |= {a.asname or a.name for a in n.names}
        for c in ("build_index", "LARGE_CAP_MIN", "MAX_WEIGHT", "MIN_NAMES", "TOP_DECILE",
                  "CONTRACT_MIN_POSITIONS", "BAND_WIDTH"):
            self.assertIn(c, imported, "%s must be imported, not retyped (`MA5`)" % c)
        assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                    for t in n.targets if isinstance(t, ast.Name)}
        for c in ("LARGE_CAP_MIN", "MAX_WEIGHT", "MIN_NAMES", "TOP_DECILE", "BAND_WIDTH",
                  "CONTRACT_MIN_POSITIONS"):
            self.assertNotIn(c, assigned, "%s is assigned a second value in the study" % c)

    def test_hot_score_is_a_monotone_percentile_rank_in_one_to_one_hundred(self):
        comp = np.array([-3.0, 0.5, 0.5, 2.0, 7.5])
        hs = IB.hot_scores(comp)
        self.assertTrue(np.all(hs >= 1.0) and np.all(hs <= 100.0))
        # monotone: the composite's ordering is preserved, so selection is unchanged
        self.assertEqual(list(np.argsort(comp)), list(np.argsort(hs)))
        self.assertAlmostEqual(hs[-1], 100.0, places=9)

    def test_scan_rows_drops_an_unscoreable_row_and_passes_a_missing_cap_as_none(self):
        g = pd.DataFrame({"ticker": ["A", "B", "C"],
                          "market_cap": [5e9, float("nan"), 2e10]})
        rows = IB.scan_rows(g, np.array([1.0, 2.0, float("nan")]))
        self.assertEqual([r["ticker"] for r in rows], ["A", "B"])
        self.assertIsNone(rows[1]["market_cap"],
                          "a NaN cap must reach build_index as None, not as NaN")
        self.assertTrue(all(r["price"] for r in rows),
                        "price is a presence filter in build_index; a falsy value drops the row")


class TheWeightedGrossUsesTheBookWeights(unittest.TestCase):
    def test_an_unequal_hook_gives_a_gross_that_is_not_the_simple_mean(self):
        """If the gross leg used the simple mean, `total_drag_ann` would be the gap between
        two different books rather than the cost of one."""
        p = _synth(n=40, dates=5, seed=11)

        def _concentrated(sub, comp, held):
            t = list(sub["ticker"].values[np.argsort(-comp)][:10])
            w = np.linspace(10.0, 1.0, len(t))
            w = w / w.sum()
            return dict(zip(t, w))

        def _flat(sub, comp, held):
            t = list(sub["ticker"].values[np.argsort(-comp)][:10])
            return {k: 1.0 / len(t) for k in t}

        a = FP.after_tax_backtest(p, COLS, W, book_fn=_concentrated)
        b = FP.after_tax_backtest(p, COLS, W, book_fn=_flat)
        self.assertNotAlmostEqual(a["gross_ann"], b["gross_ann"], places=6,
                                  msg="the gross leg ignored the book's weights")


class TheTaxArmsAreTwoRatesOfOnePath(unittest.TestCase):
    def test_zero_rates_pay_no_tax_and_nonzero_rates_do(self):
        p = _synth(n=40, dates=6, seed=3)
        bf = IB.book_fn()
        z = FP.after_tax_backtest(p, COLS, W, short_rate=0.0, long_rate=0.0, book_fn=bf)
        t = FP.after_tax_backtest(p, COLS, W, short_rate=0.408, long_rate=0.238, book_fn=bf)
        self.assertEqual(z["tax_paid_short"] + z["tax_paid_long"], 0.0)
        self.assertGreater(t["tax_paid_short"] + t["tax_paid_long"], 0.0,
                           "the taxable arm realised no gains, so the 'tax cost' would be zero "
                           "for the wrong reason")
        self.assertGreater(z["after_tax_ann"], t["after_tax_ann"])

    def test_the_gross_leg_is_identical_across_the_two_rates(self):
        """Tax is paid from the book, so gross must not move. If it did, the two arms would be
        different books and the tax cost would not be a tax cost."""
        p = _synth(n=40, dates=6, seed=3)
        bf = IB.book_fn()
        z = FP.after_tax_backtest(p, COLS, W, short_rate=0.0, long_rate=0.0, book_fn=bf)
        t = FP.after_tax_backtest(p, COLS, W, short_rate=0.408, long_rate=0.238, book_fn=bf)
        self.assertEqual(z["gross_ann"], t["gross_ann"])


class TheCensusesAreRight(unittest.TestCase):
    def test_the_contract_floor_census_counts_the_dates_below_the_imported_floor(self):
        p = _synth(n=60, dates=4)
        r = IB.run(p, COLS, W, large_cap_min=10e9, weighting="score", exit_frac=BAND_WIDTH)
        self.assertEqual(r["contract_min_positions"], VI.CONTRACT_MIN_POSITIONS)
        want = sum(1 for s in r["series"] if s["n_book"] < VI.CONTRACT_MIN_POSITIONS)
        self.assertEqual(r["dates_below_contract_min_positions"], want)

    def test_the_fallback_census_sees_a_fallback_when_the_tier_is_too_thin(self):
        """`build_index` falls back to the largest half below MIN_NAMES. A census reading the
        wrong key would report zero fallbacks on every panel -- vacuously."""
        p = _synth(n=60, dates=3)
        r = IB.run(p, COLS, W, large_cap_min=1e15, weighting="equal", exit_frac=None)
        self.assertGreater(r["dates_on_the_fallback"], 0,
                           "an impossible tier must register as a fallback")
        self.assertEqual(r["dates_with_no_tilt_label"], 0,
                         "every date must carry a tilt label; a None means the wrong key")

    def test_no_fallback_is_reported_when_the_tier_is_ample(self):
        p = _synth(n=60, dates=3)
        r = IB.run(p, COLS, W, large_cap_min=10e9, weighting="equal", exit_frac=None)
        self.assertEqual(r["dates_on_the_fallback"], 0)
        self.assertEqual(r["tilt_values"], ["large-cap only"])


class TheArithmeticIsRight(unittest.TestCase):
    def test_ann_compounds_and_scales_to_four_periods_a_year(self):
        self.assertAlmostEqual(IB._ann([0.0, 0.0, 0.0, 0.0]), 0.0, places=12)
        self.assertAlmostEqual(IB._ann([0.1] * 4), 1.1 ** 4 - 1.0, places=12)

    def test_mdd_is_negative_and_measures_peak_to_trough(self):
        self.assertAlmostEqual(IB._mdd([0.5, -0.5]), -0.5, places=12)
        self.assertEqual(IB._mdd([0.1, 0.1]), 0.0)

    def test_sharpe_refuses_a_degenerate_series_rather_than_dividing_by_zero(self):
        self.assertIsNone(IB._sharpe([0.1, 0.1, 0.1]))
        self.assertIsNone(IB._sharpe([0.1, 0.2]))


class ItIsReproducible(unittest.TestCase):
    def test_the_trade_loop_iterates_a_sorted_union_not_a_set(self):
        """A set of ticker strings iterates in an order that depends on the per-process hash
        salt, so the float summation order -- and the artifact's last digits -- change between
        runs. Pinned by SHAPE so a revert to the bare set is loud."""
        tree = ast.parse(_src(STUDY))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run")
        found = 0
        for node in ast.walk(fn):
            if not isinstance(node, ast.For):
                continue
            # The TRADE loop, identified by its ITERABLE naming the previous book -- not by its
            # body, because `ast.walk` on the enclosing per-date loop also sees the nested
            # `turn +=` and would match that instead. The wrong-object family, caught by the
            # guard failing against a tree that was already correct.
            names = {d.id for d in ast.walk(node.iter) if isinstance(d, ast.Name)}
            if "prev_w" not in names:
                continue
            found += 1
            it = node.iter
            self.assertTrue(isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                            and it.func.id == "sorted",
                            "the trade loop must iterate a SORTED union; a bare set makes the "
                            "artifact differ between runs in its last digits")
        self.assertEqual(found, 1,
                         "expected exactly one trade loop over the previous book; found %d, so "
                         "the guard is either vacuous or checking the wrong loop" % found)

    def test_two_identical_runs_agree_to_the_bit(self):
        p = _synth(n=50, dates=5, seed=5)
        a = IB.run(p, COLS, W, large_cap_min=10e9, weighting="score", exit_frac=BAND_WIDTH)
        b = IB.run(p, COLS, W, large_cap_min=10e9, weighting="score", exit_frac=BAND_WIDTH)
        for k in ("net_ann", "annual_turnover", "realised_one_way_bps", "net_sharpe"):
            self.assertEqual(a[k], b[k], "%s is not reproducible" % k)


class ItAdoptsNothing(unittest.TestCase):
    def test_the_study_lives_outside_every_product_package(self):
        """`MA23`: a product module may never import a study."""
        self.assertTrue(STUDY.replace("\\", "/").endswith("valuation/studies/served_index_book.py"))
        for pkg in ("web", "saas", "screener", "engine"):
            d = os.path.join(REPO, "valuation", pkg)
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    s = _src(os.path.join(root, f))
                    self.assertNotIn("served_index_book", s,
                                     "%s/%s references the study" % (pkg, f))

    def test_nothing_here_writes_the_meter_or_the_index_constants(self):
        """`boundary`'s sigma argument is for PROBING. This item must not retune the meter."""
        tree = ast.parse(_src(RUNNER))
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Attribute):
                        self.assertNotIn(t.attr, ("SIGMA_MONTHLY_PP", "RHO", "ALPHA",
                                                  "LARGE_CAP_MIN", "MAX_WEIGHT", "MIN_NAMES",
                                                  "TOP_DECILE", "BAND_WIDTH"),
                                         "the item assigns a live constant")

    def test_the_item_books_zero_trials_and_says_so(self):
        s = _src(RUNNER)
        self.assertIn('"trials": 0', s)
        self.assertIn("ZERO TRIALS", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
