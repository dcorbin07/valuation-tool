# -*- coding: utf-8 -*-
"""REBAL-CADENCE — the cadence extension, and the control that may not leak an outcome.

WHAT THESE PIN, and the first group is the one that licenses the register being blind:

* **THE CONTROL PASS EMITS DISPERSION AND NOTHING ELSE.** `R1-VAR` licenses measuring a paired
  `se` before the register only because a control can only BLOCK. That is true only if the pass
  really cannot reveal which way an arm came out, so no mean, alpha level, *t* or verdict may
  reach its artifact — checked on the artifact's KEYS and on the script's AST, because a
  docstring promising it is not a check.
* **`cadence=1, offset=0, return_series=False` IS INERT.** Three opt-in parameters on a shipped
  function that `book_configs`, `no_trade_band` and `cost_breakeven_bps` all call. Proved by
  reproducing the published contract book, not asserted (`C3`).
* **THE HELD-PERIOD RETURN IS WEIGHT-WEIGHTED.** The defect this would otherwise have shipped:
  an unweighted mean on a drifted book reports the return of a book that *was* rebalanced,
  handing the long-hold arms the incumbent's rebalancing for free — in the direction that
  flatters the hypothesis.
* **A HELD PERIOD TRADES NOTHING.** If a non-formation period charged cost, the whole point of
  the arm would be gone.
* **`B7`: the study DELEGATES.** The band, the cost table and the drift stay in
  `turnover_and_costs`; re-implementing any of them is the defect `B7` exists to prevent.
* **`MA23`: nothing under `web/`, `saas/` or `screener/` imports the study.**
"""
from __future__ import annotations

import ast
import io
import json
import os
import unittest

import state_isolation  # noqa: F401  (must precede any `valuation` import)

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PUBLISHED = {
    "net_alpha": 0.07752019016178369,
    "net_sharpe": 1.2095691568179565,
    "net_max_drawdown": -0.2754830109769675,
    "annual_turnover": 1.374714037832626,
}


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _data_candidates():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(ROOT, "data"))
    parts = ROOT.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    return out


def _data_file(*rel):
    for c in _data_candidates():
        p = os.path.join(c, *rel)
        if os.path.exists(p):
            return p
    return None


def _panel():
    p = _data_file("free_analysis", "panel_corrected_69d.pkl")
    return None if p is None else pd.read_pickle(p)


def _weights(panel):
    import valuation.screener.settings as S
    cols = [c for c in S.FACTORS_ALL if c in panel.columns]
    return cols, {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if k in cols}


class TestTheControlCannotLeakAnOutcome(unittest.TestCase):
    """The register's blindness rests entirely on this."""

    BANNED_SUBSTR = ("mean", "alpha", "tstat", "t_stat", "verdict", "eligible",
                     "net_ann", "gross_ann", "diff")

    def test_the_control_artifact_carries_no_outcome_key(self):
        p = _data_file("free_analysis", "REBAL_CADENCE_CONTROL.json")
        if p is None:
            self.skipTest("REBAL_CADENCE_CONTROL.json absent (no populated data root here)")
        with io.open(p, encoding="utf-8") as fh:
            art = json.load(fh)

        bad = []

        def walk(node, path):
            if isinstance(node, dict):
                for k, v in node.items():
                    kl = str(k).lower()
                    # `C1`/`C2` legitimately compare the incumbent to the PUBLISHED record,
                    # which is already public, so those subtrees are exempt BY NAME rather
                    # than by a substring that would also exempt an arm.
                    if path[:1] and path[0].startswith(("C1_", "C2_")):
                        continue
                    for b in self.BANNED_SUBSTR:
                        if b in kl:
                            bad.append(".".join(path + [str(k)]))
                    walk(v, path + [str(k)])
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, path + [str(i)])

        walk(art, [])
        self.assertEqual(bad, [],
                         "the control artifact carries outcome-shaped keys, so running it "
                         "could have revealed an arm's direction: %r" % (bad,))

    def test_the_control_declares_zero_trials_and_names_its_licence(self):
        p = _data_file("free_analysis", "REBAL_CADENCE_CONTROL.json")
        if p is None:
            self.skipTest("REBAL_CADENCE_CONTROL.json absent")
        with io.open(p, encoding="utf-8") as fh:
            art = json.load(fh)
        self.assertEqual(art["trials"], 0)
        self.assertIn("MB1-SEL", art["licence"])
        self.assertIn("R1-VAR", art["licence"])

    def test_the_control_script_computes_no_t_statistic(self):
        """AST, not a grep: the docstring says "no t" and the code must contain none.

        A `se` is a dispersion; a `t` is `mean / se` and is an outcome. The division is what
        would have to appear, so this looks for a BinOp dividing by anything named like a
        standard error rather than banning the letter t.
        """
        tree = ast.parse(_read("scripts", "rebal_cadence_control.py"))
        for n in ast.walk(tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                r = n.right
                name = (r.id if isinstance(r, ast.Name)
                        else r.attr if isinstance(r, ast.Attribute) else "")
                self.assertNotIn("se", str(name).lower().split("_"),
                                 "the control divides by a standard error -- that is a t")


class TestTheExtensionIsInert(unittest.TestCase):

    def test_the_three_parameters_default_to_the_shipped_behaviour(self):
        tree = ast.parse(_read("valuation", "edge", "fundamental_panel.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "turnover_and_costs"]
        self.assertEqual(len(fn), 1, "turnover_and_costs is not defined exactly once")
        names = [a.arg for a in fn[0].args.args]
        defaults = fn[0].args.defaults
        off = len(names) - len(defaults)
        got = {}
        for want in ("cadence", "offset", "return_series"):
            self.assertIn(want, names, "%s is not a parameter" % want)
            d = defaults[names.index(want) - off]
            self.assertIsInstance(d, ast.Constant, "%s has a non-literal default" % want)
            got[want] = d.value
        self.assertEqual(got, {"cadence": 1, "offset": 0, "return_series": False})

    def test_cadence_1_reproduces_the_published_contract_book(self):
        panel = _panel()
        if panel is None:
            self.skipTest("panel_corrected_69d.pkl absent (no populated data root here)")
        from valuation.edge.fundamental_panel import turnover_and_costs
        cols, rec = _weights(panel)
        base = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3)
        for k, v in PUBLISHED.items():
            self.assertAlmostEqual(
                float(base[k]), v, places=12,
                msg="%s drifted from the published contract book" % k)

    def test_the_default_payload_gains_no_keys(self):
        panel = _panel()
        if panel is None:
            self.skipTest("panel_corrected_69d.pkl absent")
        from valuation.edge.fundamental_panel import turnover_and_costs
        cols, rec = _weights(panel)
        base = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3)
        for k in ("cadence", "cadence_offset", "formation_dates", "held_only_periods",
                  "dropped_held_name_periods", "series"):
            self.assertNotIn(k, base,
                             "the default payload gained %r -- not inert (`C3`)" % k)

    def test_explicit_cadence_1_equals_the_default_exactly(self):
        panel = _panel()
        if panel is None:
            self.skipTest("panel_corrected_69d.pkl absent")
        from valuation.edge.fundamental_panel import turnover_and_costs
        cols, rec = _weights(panel)
        a = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3)
        b = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3,
                               cadence=1, offset=0)
        for k in ("net_alpha", "gross_ann", "net_ann", "annual_turnover",
                  "realised_one_way_bps"):
            self.assertEqual(float(a[k]), float(b[k]),
                             "%s differs between the default and explicit cadence=1" % k)


class TestTheHeldPeriodArithmetic(unittest.TestCase):
    """The two things a long-hold arm could silently get wrong."""

    def test_a_weighted_mean_equals_np_mean_under_equal_weights(self):
        """The property that makes cadence=1 unaffected -- and it is NOT bit-equality.

        A first cut of this test asserted exact equality and FAILED, correctly: `np.mean` sums
        pairwise and `np.dot` does not, so they agree to floating point rather than to the bit.
        The real property is closeness in general PLUS bit-identity on the actual panel, and
        the latter is measured by `test_cadence_1_reproduces_the_published_contract_book`
        reading 0.000e+00 rather than inferred from the algebra.
        """
        rng = np.random.default_rng(11)
        for n in (1, 2, 5, 37, 160, 1601):
            r = rng.normal(0, 0.2, n)
            w = np.full(n, 1.0 / n)
            got, want = float(np.dot(w, r) / w.sum()), float(np.mean(r))
            self.assertAlmostEqual(got, want, places=15)
            # and the difference must be at the ULP scale, not merely "close"
            self.assertLessEqual(abs(got - want), 8 * np.finfo(float).eps * max(1.0, abs(want)))

    def test_the_source_takes_a_weighted_book_return_not_a_bare_mean(self):
        """AST shape: the gross return must come from a dot product, not `np.mean(rets)`.

        Banning the string `np.mean` would fire on the equal-weight BENCHMARK two lines below,
        which legitimately is a mean -- so this asserts the POSITIVE property instead.
        """
        src = _read("valuation", "edge", "fundamental_panel.py")
        tree = ast.parse(src)
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "turnover_and_costs"]
        dots = [n for n in ast.walk(fn[0])
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "dot"]
        self.assertTrue(dots,
                        "the book return is no longer weight-weighted; a drifted book scored "
                        "with an unweighted mean reports a book that was rebalanced")

    def test_a_held_period_trades_nothing(self):
        panel = _panel()
        if panel is None:
            self.skipTest("panel_corrected_69d.pkl absent")
        from valuation.edge.fundamental_panel import turnover_and_costs
        cols, rec = _weights(panel)
        r = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3,
                               cadence=4, offset=0, return_series=True)
        s = r["series"]
        held = [t for t, f in zip(s["turnover_two_way"], s["formed"]) if not f]
        self.assertTrue(held, "cadence=4 produced no held-only periods")
        self.assertEqual(max(held), 0.0,
                         "a non-formation period charged turnover -- the arm is paying to hold. "
                         "This fired for real: the renormalisation after a held name left the "
                         "panel was being priced as a purchase, at 0.066 two-way per period.")
        self.assertIn("dropped_held_weight_total", r,
                      "the dropped weight is not reported, so K4 cannot read the hole")

    def test_a_slower_cadence_forms_the_book_fewer_times(self):
        panel = _panel()
        if panel is None:
            self.skipTest("panel_corrected_69d.pkl absent")
        from valuation.edge.fundamental_panel import turnover_and_costs
        cols, rec = _weights(panel)
        counts = {}
        for cad in (1, 2, 4):
            r = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3,
                                   cadence=cad, offset=0, return_series=True)
            counts[cad] = sum(1 for f in r["series"]["formed"] if f)
        self.assertGreater(counts[1], counts[2])
        self.assertGreater(counts[2], counts[4])


class TestTheStudyDelegates(unittest.TestCase):
    """`B7` and `MA23`."""

    def test_the_study_calls_turnover_and_costs_and_reimplements_nothing(self):
        src = _read("valuation", "studies", "rebal_cadence.py")
        self.assertIn("turnover_and_costs", src)
        tree = ast.parse(src)
        # it must not define its own band, cost table or sector cap
        banned = {"_band_select", "one_way_cost_bps", "_exit_rank_for", "_sector_capped",
                  "composite_from_frame"}
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertEqual(defined & banned, set(),
                         "the study re-implements shipped machinery (`B7`): %r"
                         % (defined & banned,))

    def test_build_arm_really_delegates(self):
        """Injected fake: if the study computed anything itself, this would not be exercised."""
        from valuation.studies import rebal_cadence as rc
        calls = []

        def fake(panel, cols, weights, **kw):
            calls.append(kw)
            return {"annual_turnover": 1.0, "formation_dates": 1, "held_only_periods": 0,
                    "dropped_held_name_periods": 0, "realised_one_way_bps": 33.4,
                    "series": {"dates": ["d1", "d2"], "net": [0.01, 0.02],
                               "gross": [0.011, 0.021], "equal_weight": [0.005, 0.006],
                               "turnover_two_way": [0.5, 0.0], "formed": [True, False]}}

        out = rc.build_arm(None, None, None, [(4, 0)], turnover_fn=fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["cadence"], 4)
        self.assertEqual(calls[0]["offset"], 0)
        self.assertTrue(calls[0]["return_series"])
        self.assertEqual(out["dates"], ["d1", "d2"])

    def test_the_staggered_spec_is_four_sub_books_one_per_quarter(self):
        from valuation.studies import rebal_cadence as rc
        self.assertEqual(rc.SPEC["staggered"], [(4, 0), (4, 1), (4, 2), (4, 3)])
        self.assertEqual(rc.SPEC["quarterly"], [(1, 0)])
        self.assertEqual(set(rc.ARMS), {"quarterly", "semiannual", "annual", "staggered"})
        self.assertEqual(rc.INCUMBENT, "quarterly")

    def test_legs_must_agree_on_the_equal_weight_universe(self):
        """A disagreement means the legs are not on one panel, and must RAISE not average."""
        from valuation.studies import rebal_cadence as rc
        seq = iter([
            {"series": {"dates": ["d1"], "net": [0.01], "gross": [0.01],
                        "equal_weight": [0.005], "turnover_two_way": [0.0], "formed": [True]}},
            {"series": {"dates": ["d1"], "net": [0.02], "gross": [0.02],
                        "equal_weight": [0.999], "turnover_two_way": [0.0], "formed": [True]}},
        ])

        def fake(*a, **kw):
            return next(seq)

        with self.assertRaises(RuntimeError) as cm:
            rc.build_arm(None, None, None, [(4, 0), (4, 1)], turnover_fn=fake)
        self.assertIn("equal-weight", str(cm.exception))

    def test_no_product_module_imports_the_study(self):
        """`MA23`: a study may not be reachable from the live product."""
        import pathlib
        hits = []
        for d in ("web", "saas", "screener", "engine"):
            base = pathlib.Path(ROOT, "valuation", d)
            if not base.is_dir():
                continue
            for p in base.rglob("*.py"):
                src = p.read_text(encoding="utf-8", errors="ignore")
                if "rebal_cadence" in src:
                    hits.append(str(p.relative_to(ROOT)))
        self.assertEqual(hits, [],
                         "a product module imports the cadence study (`MA23`): %r" % (hits,))


class TestThePairedDifferenceIsNotDoubleBenchmarked(unittest.TestCase):

    def test_the_paired_difference_is_net_minus_net(self):
        """The equal-weight benchmark cancels, so subtracting it again would double-count."""
        from valuation.studies import rebal_cadence as rc
        arms = {
            "quarterly": {"dates": ["a", "b"], "net": [0.10, 0.20],
                          "gross": [0, 0], "equal_weight": [0.05, 0.05],
                          "turnover_two_way": [0, 0], "n_periods": 2},
            "annual": {"dates": ["a", "b"], "net": [0.12, 0.19],
                       "gross": [0, 0], "equal_weight": [0.05, 0.05],
                       "turnover_two_way": [0, 0], "n_periods": 2},
        }
        d = rc.paired_difference(arms, "annual")
        self.assertEqual(d["n"], 2)
        np.testing.assert_allclose(d["diff"], [0.02, -0.01], atol=1e-15)

    def test_common_dates_is_the_intersection(self):
        from valuation.studies import rebal_cadence as rc
        arms = {"a": {"dates": ["1", "2", "3"]}, "b": {"dates": ["2", "3", "4"]},
                "c": {"dates": ["2", "3"]}}
        self.assertEqual(rc.common_dates(arms), ["2", "3"])


class TestTheArmRunnerRefusesWithoutItsControl(unittest.TestCase):
    """`O10`'s process defect: the kills must be read in their OWN pass, not alongside the arms."""

    def test_the_runner_refuses_when_the_control_artifact_is_absent(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "rc_arms_probe", os.path.join(ROOT, "scripts", "rebal_cadence_arms.py"))
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except FileNotFoundError:
            self.skipTest("no populated data root here")
        mod.CONTROL = os.path.join(ROOT, "_no_such_control_.json")
        with self.assertRaises(SystemExit) as cm:
            mod.main()
        self.assertIn("REFUSING", str(cm.exception))
        self.assertIn("control artifact", str(cm.exception))

    def test_the_runner_refuses_a_failing_control(self):
        """A failing K1 means the incumbent is a lookalike; scoring against it is meaningless."""
        import importlib.util
        import json as _json
        import tempfile
        spec = importlib.util.spec_from_file_location(
            "rc_arms_probe2", os.path.join(ROOT, "scripts", "rebal_cadence_arms.py"))
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except FileNotFoundError:
            self.skipTest("no populated data root here")
        fd, tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with io.open(tmp, "w", encoding="utf-8") as fh:
                _json.dump({"C1_incumbent_reproduces_published_contract_book": {"pass": False},
                            "C2_cadence_1_is_bit_identical_to_the_shipped_default":
                                {"pass": True}}, fh)
            mod.CONTROL = tmp
            with self.assertRaises(SystemExit) as cm:
                mod.main()
            self.assertIn("REFUSING", str(cm.exception))
            self.assertIn("lookalike", str(cm.exception))
        finally:
            os.remove(tmp)

    def test_the_margins_are_the_registered_ones_and_are_not_relaxed(self):
        """`W-28`: a successor may not relax a pre-committed bar after watching it fail."""
        tree = ast.parse(_read("scripts", "rebal_cadence_arms.py"))
        got = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and len(n.targets) == 1                     and isinstance(n.targets[0], ast.Name):
                nm = n.targets[0].id
                if nm in ("MARGIN_ALPHA_PP", "MARGIN_TSTAT", "K3_TURNOVER_RATIO_MAX",
                          "K4_DROPPED_SHARE_MAX", "K5_LEGS_REQUIRED")                         and isinstance(n.value, ast.Constant):
                    got[nm] = n.value.value
        self.assertEqual(got, {"MARGIN_ALPHA_PP": 1.00, "MARGIN_TSTAT": 0.25,
                               "K3_TURNOVER_RATIO_MAX": 0.70,
                               "K4_DROPPED_SHARE_MAX": 0.05,
                               "K5_LEGS_REQUIRED": 4},
                         "a registered bar moved -- W-28 forbids relaxing one after the fact")


class TestTheResultIsOnTheRecord(unittest.TestCase):
    """The claims a reader would act on, asserted against the banked artifact."""

    def _art(self):
        p = _data_file("free_analysis", "REBAL_CADENCE_ARMS.json")
        if p is None:
            return None
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh)

    def test_all_three_arms_are_rejected(self):
        a = self._art()
        if a is None:
            self.skipTest("REBAL_CADENCE_ARMS.json absent")
        for name in ("semiannual", "annual", "staggered"):
            self.assertEqual(a["primary"][name]["verdict"], "REJECTED", name)

    def test_nothing_was_adopted(self):
        """ADOPTS NOTHING -- the shipped config must still be the quarterly contract book."""
        import valuation.screener.settings as S
        self.assertEqual(S.BOOK_CONFIGS["taxable"]["rebalance_days"], 63,
                         "the live cadence changed -- that is a vintage event and Don's call")
        self.assertEqual(S.BOOK_CONFIGS["taxable"]["exit_frac"], 0.3)

    def test_slowing_down_costs_alpha_monotonically(self):
        a = self._art()
        if a is None:
            self.skipTest("REBAL_CADENCE_ARMS.json absent")
        L = a["levels"]
        q, s, an = (L["quarterly"]["net_alpha_ann"], L["semiannual"]["net_alpha_ann"],
                    L["annual"]["net_alpha_ann"])
        self.assertGreater(q, s, "the monotone ordering in the handoff is stale")
        self.assertGreater(s, an, "the monotone ordering in the handoff is stale")

    def test_the_timing_luck_spread_exceeds_the_cadence_effect(self):
        """The item's actual finding, pinned so a successor cannot quote one without the other."""
        a = self._art()
        if a is None:
            self.skipTest("REBAL_CADENCE_ARMS.json absent")
        sp = a["diagnostic_offset_sweep_NO_VERDICT"]["spread"]
        sp4 = sp["cadence4"]["window_matched_to_the_primary"]["spread_pp"]
        eff = abs(a["primary"]["annual"]["cells"]["full"]["delta_net_alpha_pp"])
        self.assertGreater(sp4, eff,
                           "the offset spread no longer exceeds the cadence effect; the "
                           "handoff's central finding is stale")

    def test_the_offset_sweep_carries_no_verdict(self):
        a = self._art()
        if a is None:
            self.skipTest("REBAL_CADENCE_ARMS.json absent")
        sw = a["diagnostic_offset_sweep_NO_VERDICT"]
        self.assertIn("NO VERDICT", sw["why"])
        blob = json.dumps(sw).lower()
        for banned in ("eligible", "adopt", "\"verdict\""):
            self.assertNotIn(banned, blob,
                             "the offset sweep acquired a verdict -- a void condition")

    def test_every_verdict_ships_its_mde(self):
        """`RUN_RULES` A11 / the register's void condition 6."""
        a = self._art()
        if a is None:
            self.skipTest("REBAL_CADENCE_ARMS.json absent")
        for name in ("semiannual", "annual", "staggered"):
            p = a["primary"][name]
            for k in ("mde_50_ann_pp", "mde_80_ann_pp", "observed_over_mde80", "bound"):
                self.assertIn(k, p, "%s ships no %s" % (name, k))
            self.assertLess(p["observed_over_mde80"], 1.0,
                            "%s now exceeds its own 80%%-power threshold; the 'bounded null' "
                            "reading in the handoff is stale" % name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
