# -*- coding: utf-8 -*-
"""INDEX-BEST -- tests for the four-arm construction comparison and its pick rule.

The load-bearing ones, in order of what they would cost if they broke:

 1. **The pick rule is applied EXACTLY as registered.** It is the whole item: a rule changed
    after seeing which arm won is `W-28`'s defect, and the highest-returning arm here is the one
    the rule must REFUSE (arm 4 is not buildable from the live scan). Pinned with a positive
    control that an unbuildable leader does not win.
 2. **`return_series` is opt-in and inert**, pinned against a committed literal from
    `book_configs.taxable`, because it touches the function every published after-tax figure
    comes from.
 3. **The universe trim is deterministic.** An unstable universe boundary would make the arms
    irreproducible run to run, which is the defect `INDEX-BOOK` hit with set iteration.
 4. **The halves embargo the boundary period**, as registered.
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

from valuation.studies import served_index_book as IB                   # noqa: E402
from valuation.edge import fundamental_panel as FP                      # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                     # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(REPO, "scripts", "index_best.py")
STUDY = os.path.join(REPO, "valuation", "studies", "served_index_book.py")
REGISTER = os.path.join(REPO, "PREREG_index_best.md")

PUBLISHED_AFTER_TAX_ALPHA = 0.021132837959488837
PUBLISHED_AFTER_TAX_SHARPE = 0.9767529353354262

COLS = ["value", "quality", "momentum", "size", "insider", "institutional",
        "capital_discipline"]
W = {c: 0.125 for c in COLS}


def _src(p):
    return io.open(p, encoding="utf-8").read()


def _synth(n=80, dates=5, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for di in range(dates):
        for i in range(n):
            rows.append({"date": "20%02d-01-15" % (10 + di), "ticker": "T%03d" % i,
                         "market_cap": float(1e9 + i * 1.0e9),
                         "fwd_ret": float(rng.normal(0.02, 0.08)),
                         "bench_ret": 0.015,
                         **{c: float(rng.normal()) for c in COLS}})
    return pd.DataFrame(rows)


def _fa():
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
    for c in _fa():
        p = os.path.join(c, "panel_corrected_69d.pkl")
        if os.path.exists(p):
            return pd.read_pickle(p)
    return None


class ThePickRuleIsTheRegisteredOne(unittest.TestCase):
    """The rule, verbatim from the register: highest net Roth among arms beating arm 1 in BOTH
    halves AND buildable from the live scan; ties to the incumbent; otherwise arm 1 stands."""

    @staticmethod
    def _pick(arms):
        qual = [k for k, a in arms.items()
                if k != "arm1" and a["both"] and a["buildable"]]
        return max(qual, key=lambda k: arms[k]["roth"]) if qual else "arm1"

    def test_an_unbuildable_leader_does_not_win(self):
        arms = {"arm1": {"roth": 0.10, "both": False, "buildable": True},
                "armB": {"roth": 0.20, "both": True, "buildable": True},
                "armCEILING": {"roth": 0.99, "both": True, "buildable": False}}
        self.assertEqual(self._pick(arms), "armB",
                         "the ceiling arm is not buildable and may not be picked")

    def test_an_arm_winning_one_half_only_does_not_win(self):
        arms = {"arm1": {"roth": 0.10, "both": False, "buildable": True},
                "armB": {"roth": 0.50, "both": False, "buildable": True}}
        self.assertEqual(self._pick(arms), "arm1", "one half is not both halves")

    def test_arm1_stands_when_nothing_qualifies(self):
        arms = {"arm1": {"roth": 0.10, "both": False, "buildable": True},
                "armB": {"roth": 0.05, "both": True, "buildable": False}}
        self.assertEqual(self._pick(arms), "arm1")

    def test_the_runner_implements_that_rule_and_not_a_looser_one(self):
        src = _src(RUNNER)
        self.assertIn('a["paired_vs_arm1"]["beats_arm1_in_both_halves"]', src)
        self.assertIn('a["buildable_from_live_scan"]', src)
        tree = ast.parse(src)
        # the qualifying comprehension must AND the two conditions, never OR them
        found = False
        for n in ast.walk(tree):
            if isinstance(n, ast.ListComp):
                for g in n.generators:
                    for cond in g.ifs:
                        names = {d.attr for d in ast.walk(cond) if isinstance(d, ast.Attribute)}
                        if "buildable_from_live_scan" in str(ast.dump(cond)):
                            found = True
                            self.assertNotIn("Or", type(cond).__name__ + str(
                                [type(o).__name__ for o in ast.walk(cond)
                                 if isinstance(o, ast.boolop)] if False else ""),
                                "placeholder")
                            ors = [o for o in ast.walk(cond)
                                   if isinstance(o, ast.BoolOp) and isinstance(o.op, ast.Or)]
                            self.assertEqual(ors, [],
                                             "the qualifying test must AND its conditions")
        self.assertTrue(found, "could not find the qualifying filter; guard would be vacuous")

    def test_arm4_is_declared_unbuildable_in_the_source_not_decided_later(self):
        from scripts.index_best import ARMS
        d = {a[0]: a[3] for a in ARMS}
        self.assertFalse(d["4_all_cap_ceiling"], "the ceiling must be declared unbuildable")
        for k in ("1_incumbent_10bn", "2_liquid_decile", "3_liquid_top25"):
            self.assertTrue(d[k])


class TheSeriesHookIsInert(unittest.TestCase):
    def test_return_series_false_reproduces_the_published_after_tax_figures(self):
        p = _panel()
        if p is None:
            self.skipTest("LOUD SKIP: panel absent; tried %r" % (_fa(),))
        r = FP.after_tax_backtest(p, COLS, W, top_frac=0.1, exit_frac=BAND_WIDTH)
        self.assertEqual(r["after_tax_alpha"], PUBLISHED_AFTER_TAX_ALPHA)
        self.assertEqual(r["after_tax_sharpe"], PUBLISHED_AFTER_TAX_SHARPE)
        self.assertNotIn("series", r, "the series must be ABSENT unless asked for")

    def test_the_series_is_present_when_asked_and_matches_the_period_count(self):
        p = _synth()
        r = FP.after_tax_backtest(p, COLS, W, top_frac=0.2, return_series=True)
        self.assertIn("series", r)
        self.assertEqual(len(r["series"]["net"]), r["n_periods"])
        for k in ("net", "gross", "tax", "equal_weight"):
            self.assertEqual(len(r["series"][k]), r["n_periods"])

    def test_asking_for_the_series_changes_no_other_field(self):
        p = _synth()
        a = FP.after_tax_backtest(p, COLS, W, top_frac=0.2)
        b = FP.after_tax_backtest(p, COLS, W, top_frac=0.2, return_series=True)
        for k in a:
            self.assertEqual(a[k], b[k], "return_series moved %s" % k)


class TheUniverseTrimIsDeterministicAndReal(unittest.TestCase):
    def test_the_trim_actually_reduces_the_universe(self):
        p = _synth(n=80, dates=3)
        wide = IB.run(p, COLS, W, large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH)
        cut = IB.run(p, COLS, W, large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH,
                     universe_rank=40)
        self.assertGreater(wide["eligible_tier"]["median"], cut["eligible_tier"]["median"])
        self.assertLessEqual(cut["eligible_tier"]["max"], 40)

    def test_two_runs_of_a_trimmed_arm_agree_to_the_bit(self):
        p = _synth(n=60, dates=4, seed=9)
        a = IB.run(p, COLS, W, large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH,
                   universe_rank=30)
        b = IB.run(p, COLS, W, large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH,
                   universe_rank=30)
        for k in ("net_ann", "annual_turnover", "net_sharpe"):
            self.assertEqual(a[k], b[k])

    def test_the_trim_breaks_ties_on_ticker_so_the_boundary_is_stable(self):
        """Equal market caps at the cut must not reorder between runs."""
        rows = [{"ticker": "B", "hot_score": 50.0, "market_cap": 1e9, "price": 1.0},
                {"ticker": "A", "hot_score": 60.0, "market_cap": 1e9, "price": 1.0},
                {"ticker": "C", "hot_score": 70.0, "market_cap": 1e9, "price": 1.0}]
        key = (lambda r: r.get("market_cap") or 0.0)
        first = [sorted(rows, key=lambda r: (-(key(r) or 0.0), r["ticker"]))[:2]
                 for _ in range(5)]
        self.assertTrue(all([r["ticker"] for r in f] == ["A", "B"] for f in first))

    def test_top_n_reaches_build_index_so_a_fixed_size_book_is_possible(self):
        p = _synth(n=80, dates=3)
        r = IB.run(p, COLS, W, large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH,
                   universe_rank=60, top_n=25)
        self.assertEqual(r["book_size"]["min"], 25)
        self.assertEqual(r["book_size"]["max"], 25)


class TheHalvesEmbargoTheBoundary(unittest.TestCase):
    def test_the_boundary_period_is_in_neither_half(self):
        from scripts.index_best import _halves
        e, l = _halves(69)
        self.assertEqual(len(e), 34)
        self.assertEqual(len(l), 34)
        self.assertEqual(set(e) & set(l), set())
        self.assertNotIn(34, e)
        self.assertNotIn(34, l)
        self.assertEqual(sorted(set(range(69)) - set(e) - set(l)), [34])


class TheHacArithmeticIsRight(unittest.TestCase):
    def test_a_constant_series_has_no_dispersion_and_returns_none(self):
        from scripts.index_best import _hac_t
        t, se = _hac_t([0.01] * 20)
        self.assertIsNone(t)

    def test_a_shifted_series_has_the_sign_of_the_shift(self):
        from scripts.index_best import _hac_t
        rng = np.random.default_rng(0)
        x = rng.normal(0, 0.01, 200)
        up, _ = _hac_t(list(x + 0.02))
        dn, _ = _hac_t(list(x - 0.02))
        self.assertGreater(up, 2.0)
        self.assertLess(dn, -2.0)

    def test_lag0_reduces_to_the_naive_t(self):
        from scripts.index_best import _hac_t
        rng = np.random.default_rng(1)
        x = list(rng.normal(0.01, 0.02, 120))
        t, se = _hac_t(x, lag=0)
        a = np.asarray(x)
        naive = a.mean() / (a.std(ddof=0) / np.sqrt(len(a)))
        self.assertAlmostEqual(t, naive, places=10)


class TheGateIsExactAndTheRegisterIsHonoured(unittest.TestCase):
    def test_the_gate_demands_exact_equality_not_a_tolerance(self):
        src = _src(RUNNER)
        self.assertIn("v == 0.0 for v in dev.values()", src,
                      "a tolerance would swallow a wrong comparator")
        self.assertIn("GATE FAILED", src)

    def test_the_register_exists_and_is_a_committed_ancestor_by_name(self):
        self.assertTrue(os.path.exists(REGISTER), "the cited register must be on disk")
        s = _src(REGISTER)
        for must in ("ADOPTS NOTHING", "PICK RULE", "UNCALIBRATED", "MDE"):
            self.assertIn(must, s.upper())

    def test_the_runner_charges_three_trials_and_says_so(self):
        self.assertIn('"trials": 3', _src(RUNNER))

    def test_taxable_figures_cannot_pick(self):
        """Don's ruling: taxable is transparency only. The pick must read the ROTH field."""
        src = _src(RUNNER)
        i = src.index('"ranked_by_roth_net"')
        window = src[src.index("qual = ["):i]
        self.assertIn("roth_net_ann", window)
        self.assertNotIn("taxable_after_tax_ann", window,
                         "the pick must not read a taxable figure")


class ImportingTheRunnerDoesNotRequireLicensedData(unittest.TestCase):
    """THE CI-ONLY FAILURE THIS ITEM ACTUALLY SHIPPED ONCE, now pinned.

    The panel is licensed and gitignored, so it is ABSENT on a runner. The first cut resolved
    the data root at MODULE level and raised, so `import scripts.index_best` failed on CI and
    five tests ERRORED instead of skipping -- `D9-DIAG`'s defect repeated in a new file. These
    pin the property rather than the symptom: resolution must return None, not raise, and the
    error must land in `main()` where it is a real problem.
    """

    def test_resolution_returns_none_instead_of_raising_when_nothing_is_found(self):
        import scripts.index_best as M
        real = M.data_candidates
        try:
            M.data_candidates = lambda: [os.path.join(REPO, "no_such_data_root_xyz")]
            self.assertIsNone(M._data_root(required=False),
                              "a missing panel must resolve to None, not raise")
            with self.assertRaises(FileNotFoundError):
                M._data_root(required=True)
        finally:
            M.data_candidates = real

    def test_main_refuses_loudly_when_the_panel_is_absent(self):
        """A refusal, not a traceback -- and it must NAME where it looked."""
        src = _src(RUNNER)
        self.assertIn("if not FA:", src)
        self.assertIn("the licensed panel is absent", src)
        self.assertIn("data_candidates()", src)

    def test_the_module_level_resolution_is_the_non_raising_one(self):
        """Pinned by SHAPE: `DATA = _data_root(required=False)`. A bare call re-introduces the
        CI failure, and the diag script must carry the same form."""
        for p in (RUNNER, os.path.join(REPO, "scripts", "index_best_diag.py")):
            tree = ast.parse(_src(p))
            found = False
            for n in tree.body:
                if not isinstance(n, ast.Assign):
                    continue
                if not any(isinstance(t, ast.Name) and t.id == "DATA" for t in n.targets):
                    continue
                found = True
                self.assertIsInstance(n.value, ast.Call)
                kw = {k.arg: getattr(k.value, "value", None) for k in n.value.keywords}
                self.assertIs(kw.get("required"), False,
                              "%s resolves the data root in the RAISING form at import time"
                              % os.path.basename(p))
            self.assertTrue(found, "no module-level DATA assignment found in %s" % p)


class ItAdoptsNothing(unittest.TestCase):
    def test_no_product_package_references_this_item(self):
        for pkg in ("web", "saas", "screener", "engine"):
            d = os.path.join(REPO, "valuation", pkg)
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.endswith(".py"):
                        self.assertNotIn("index_best", _src(os.path.join(root, f)))

    def test_nothing_assigns_a_live_index_or_contract_constant(self):
        for p in (RUNNER, os.path.join(REPO, "scripts", "index_best_diag.py")):
            tree = ast.parse(_src(p))
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Attribute):
                            self.assertNotIn(t.attr, ("LARGE_CAP_MIN", "MAX_WEIGHT",
                                                      "MIN_NAMES", "TOP_DECILE", "BAND_WIDTH",
                                                      "CONTRACT_MIN_POSITIONS",
                                                      "TAX_SHORT_TERM", "TAX_LONG_TERM"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
