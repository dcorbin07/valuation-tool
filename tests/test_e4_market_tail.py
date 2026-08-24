"""E-4 -- the market-tail crash flag. Tests, tripwires and the mutation battery.

Register `PREREG_e4_market_tail_flag.md` (ALONE and BLIND at `cf7c7fc`).

SEVEN SECTIONS, in the order that makes each one mean something:
 1. the registered constants, pinned so a post-hoc edit shows in a diff
 2. the flag construction, including the two ways it can fail silently
 3. the 2x2 and the agreement statistics, against a fixture whose truth is arithmetic
 4. the MUTATION BATTERY on the flag and 2x2 arithmetic, with a baseline
 5. NEUTRALITY -- no return statistic anywhere, read from the AST
 6. the pinned-store contract
 7. the gate refusal, proved without executing the arm
"""
from __future__ import annotations

import ast
import copy
import io
import json
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts"))
import state_isolation  # noqa: F401,E402  must precede the valuation imports

from valuation.studies import market_tail as mt          # noqa: E402
from valuation.studies import crash_gate as cg           # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(REPO, "valuation", "studies", "market_tail.py")
RUNNER = os.path.join(REPO, "scripts", "e4_market_tail_flag.py")
REGISTER = os.path.join(REPO, "PREREG_e4_market_tail_flag.md")
_SKIPS = []


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _code_only(src):
    """The source with every docstring removed.

    A guard that greps raw text fires on the PROSE that documents the rule -- `MA49`'s
    comment-versus-code defect, whose instances in this record include a fixture failing against
    the FIXED tree because the repair comment quoted the defect verbatim. This module's docstring
    names `alpha`, `IC` and `long-short` in the sentence that forbids them, so the neutrality
    sweep MUST NOT see docstrings.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body[0].value.value = ""
    return ast.unparse(tree)


# ============================================================== 1. the registered constants

class TestRegisteredConstants(unittest.TestCase):
    """Every one of these is in the register. Changing one after a measurement voids the item."""

    def test_the_primary_threshold_is_070_and_not_the_050_that_matches_the_crash_event(self):
        # The whole point of the choice, and the reason is I-1's own pre-outcome extrapolation
        # census: 80.48% at 0.50 against 46.06% at 0.70.
        self.assertEqual(mt.PRIMARY_THRESHOLD, 0.70)
        self.assertIn(0.50, mt.SENSITIVITY_THRESHOLDS)
        self.assertNotIn(mt.PRIMARY_THRESHOLD, mt.SENSITIVITY_THRESHOLDS)

    def test_the_band_and_target_are_the_registered_ones(self):
        self.assertEqual(mt.TARGET_DTE, 92)
        self.assertEqual(mt.BAND, (50, 140))
        self.assertEqual(mt.QUINTILE, 0.20)
        self.assertEqual(mt.MIN_NAMES_PER_DATE, 50)

    def test_the_runner_uses_MA28s_bars_verbatim(self):
        import scripts.e4_market_tail_flag as e4
        self.assertEqual(e4.CRASH, -0.50)
        self.assertEqual(e4.RATIO_FLOOR, 2.0)
        self.assertEqual(e4.ABS_FLOOR_PP, 0.50)
        self.assertEqual(e4.N_PERM, 500)
        self.assertEqual(e4.PERM_SEED, 20260816)
        self.assertEqual(e4.MIN_FLAGGED_PER_DATE, 30)
        self.assertEqual(e4.MIN_KEPT_PER_DATE, 100)

    def test_the_register_exists_on_disk_and_is_markdown(self):
        # `V6`'s defect: two lanes named the same unbuilt register differently and the citation
        # pointed at a file that did not exist. Assert the FILE, not the string's prefix.
        self.assertTrue(os.path.isfile(REGISTER), REGISTER)
        self.assertTrue(REGISTER.endswith(".md"))

    def test_no_bar_shaped_default_leaks_into_the_gate_call(self):
        """`crash_gate`'s bars are keyword-only with NO defaults; the runner must pass all of
        them explicitly. `MA5` measured that a default is exactly how a bar freezes."""
        tree = ast.parse(_src(RUNNER))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "window_result"]
        self.assertTrue(calls, "the runner never calls crash_gate.window_result")
        for c in calls:
            kw = {k.arg for k in c.keywords}
            for need in ("ratio_floor", "abs_floor_pp", "n_perm", "perm_seed",
                         "min_flagged_per_date", "min_kept_per_date", "crash_col"):
                self.assertIn(need, kw, "window_result called without %s" % need)


# ================================================================ 2. the flag construction

def _frame(vals, date="d1"):
    return pd.DataFrame({"date": [date] * len(vals), "tail_mass": list(map(float, vals))})


class TestFlagConstruction(unittest.TestCase):

    def test_the_worst_quintile_is_the_HIGHEST_tail_mass(self):
        """Sign check. 'Worst' means most crash-prone, i.e. the biggest left-tail mass. Getting
        this backwards would invert the whole item and would still produce a plausible number."""
        f = mt.within_date_worst_quintile(_frame(range(100)), 'tail_mass')
        flagged = _frame(range(100)).loc[f.values, "tail_mass"]
        self.assertEqual(int(f.sum()), 20)
        self.assertEqual(flagged.min(), 80.0)
        self.assertEqual(flagged.max(), 99.0)

    def test_a_thin_cross_section_forms_no_quintile_at_all(self):
        """Below MIN_NAMES_PER_DATE nothing is flagged -- and the caller EXCLUDES those dates
        rather than keeping them as unflagged, which would put a date the rule could not evaluate
        into the comparison bucket. `MB8`: the bucket a rule cannot evaluate is not the safe one."""
        self.assertEqual(int(mt.within_date_worst_quintile(_frame(range(49)), 'tail_mass').sum()), 0)
        self.assertEqual(int(mt.within_date_worst_quintile(_frame(range(50)), 'tail_mass').sum()), 10)
        self.assertEqual(mt.qualifying_dates(_frame(range(49)), "tail_mass"), [])
        self.assertEqual(mt.qualifying_dates(_frame(range(50)), "tail_mass"), ["d1"])

    def test_ties_do_not_inflate_the_flagged_share(self):
        """A constant column must flag NOTHING rather than everything. `>` not `>=` is the reason,
        and a `>=` would flag 100% of a degenerate date while looking like a working rule."""
        self.assertEqual(int(mt.within_date_worst_quintile(_frame([7.0] * 60), 'tail_mass').sum()), 0)

    def test_each_date_is_sorted_independently(self):
        f = pd.concat([_frame(range(100), "d1"), _frame(np.arange(100) * -1000.0, "d2")],
                      ignore_index=True)
        flag = mt.within_date_worst_quintile(f, 'tail_mass')
        for d in ("d1", "d2"):
            self.assertEqual(int(flag[f["date"] == d].sum()), 20, d)

    def test_nan_tail_mass_is_never_flagged_and_does_not_count_toward_the_floor(self):
        v = list(range(45)) + [np.nan] * 10
        self.assertEqual(int(mt.within_date_worst_quintile(_frame(v), 'tail_mass').sum()), 0)

    def test_pick_expiry_takes_the_nearest_inside_the_band_and_refuses_outside_it(self):
        asof = pd.Timestamp("2020-01-15")
        exps = [asof + pd.Timedelta(days=d) for d in (20, 55, 95, 130, 300)]
        self.assertEqual(mt.pick_expiry(exps, asof), asof + pd.Timedelta(days=95))
        # nothing inside [50,140] -> None, never a silent nearest-overall
        self.assertIsNone(mt.pick_expiry([asof + pd.Timedelta(days=d) for d in (10, 300)], asof))

    def test_pick_expiry_prefers_92_over_a_closer_calendar_date_outside_the_target(self):
        asof = pd.Timestamp("2020-01-15")
        exps = [asof + pd.Timedelta(days=51), asof + pd.Timedelta(days=90)]
        self.assertEqual(mt.pick_expiry(exps, asof), asof + pd.Timedelta(days=90))

    def test_tail_mass_row_refuses_rather_than_raising(self):
        for spot, chain, why in ((None, pd.DataFrame(), "bad_spot"),
                                 (-1.0, pd.DataFrame(), "bad_spot"),
                                 (100.0, pd.DataFrame(), "no_chain_on_date")):
            r = mt.tail_mass_row(chain, spot, "2020-01-15", "X", 0.02)
            self.assertFalse(r["usable"])
            self.assertEqual(r["reason"], why)

    def test_tail_mass_row_refuses_when_no_expiry_lands_in_the_band(self):
        asof = pd.Timestamp("2020-01-15")
        ch = pd.DataFrame({"expiration": [asof + pd.Timedelta(days=5)] * 4,
                           "strike": [90.0, 95.0, 105.0, 110.0], "right": list("CCPP"),
                           "bid": [1.0] * 4, "ask": [1.1] * 4})
        r = mt.tail_mass_row(ch, 100.0, asof, "X", 0.02)
        self.assertFalse(r["usable"])
        self.assertEqual(r["reason"], "no_expiry_in_dte_band")


# ======================================================================= 3. the 2x2 census

def _twobytwo_fixture():
    """A fixture whose every cell is arithmetic, so the test knows the answer without the code.

    20 rows. market flag on the first 10; accounting flag on rows 5..14. Crashes placed so that
    each of the four cells has a DIFFERENT, hand-countable rate.
    """
    n = 20
    m = [i < 10 for i in range(n)]
    a = [5 <= i < 15 for i in range(n)]
    crash = [False] * n
    for i in (0, 1, 2):      # market-only  (rows 0..4): 3 of 5
        crash[i] = True
    for i in (5,):           # both         (rows 5..9): 1 of 5
        crash[i] = True
    for i in (10, 11):       # accounting-only (rows 10..14): 2 of 5
        crash[i] = True
    # neither (rows 15..19): 0 of 5
    return pd.DataFrame({"flagged": m, "acct_flag": a, "crash": crash})


class TestTwoByTwo(unittest.TestCase):

    def test_every_cell_matches_hand_arithmetic(self):
        t = mt.two_by_two(_twobytwo_fixture(), market_col="flagged", acct_col="acct_flag",
                          crash_col="crash")
        self.assertEqual(t["market_flagged_and_accounting_clean"], {"n": 5, "crashes": 3, "rate": 0.6})
        self.assertEqual(t["market_flagged_and_accounting_flagged"], {"n": 5, "crashes": 1, "rate": 0.2})
        self.assertEqual(t["market_clean_and_accounting_flagged"], {"n": 5, "crashes": 2, "rate": 0.4})
        self.assertEqual(t["market_clean_and_accounting_clean"], {"n": 5, "crashes": 0, "rate": 0.0})
        self.assertEqual(t["n_rows"], 20)

    def test_every_rate_travels_with_its_event_count(self):
        """`MB8` quoted a ratio built on ONE crash of eighty-four. A rate without its count is
        how that happens, so the structure forbids it."""
        t = mt.two_by_two(_twobytwo_fixture(), market_col="flagged", acct_col="acct_flag",
                          crash_col="crash")
        for k, v in t.items():
            if isinstance(v, dict) and "rate" in v:
                self.assertIn("crashes", v, k)
                self.assertIn("n", v, k)

    def test_an_empty_cell_reports_a_None_rate_and_not_a_zero(self):
        f = pd.DataFrame({"flagged": [True] * 4, "acct_flag": [False] * 4, "crash": [False] * 4})
        t = mt.two_by_two(f, market_col="flagged", acct_col="acct_flag", crash_col="crash")
        self.assertIsNone(t["market_clean_and_accounting_clean"]["rate"])
        self.assertEqual(t["market_clean_and_accounting_clean"]["n"], 0)

    def test_kappa_and_odds_ratio_behave_at_their_endpoints(self):
        self.assertAlmostEqual(mt.cohens_kappa([1, 1, 0, 0], [1, 1, 0, 0]), 1.0)
        self.assertAlmostEqual(mt.cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1]), -1.0)
        self.assertIsNone(mt.cohens_kappa([1, 1, 1], [1, 1, 1]))      # pe == 1, undefined
        self.assertIsNone(mt.odds_ratio([1, 1, 0], [1, 1, 0]))        # an empty cell -> not a number

    def test_the_overlap_ceiling_arithmetic_the_register_states(self):
        """The ledger's kill as literally written cannot fire, and this is the multiplication --
        `MB8`'s failure, which set a 20% bar and a 0.5x haircut without multiplying them."""
        acct_share, quintile = 0.0574, mt.QUINTILE
        self.assertLess(acct_share / quintile, 0.70)
        # and the reachable direction can attain it
        f = pd.DataFrame({"flagged": [True] * 20 + [False] * 80,
                          "acct_flag": [True] * 6 + [False] * 94})
        m = f["flagged"].values
        a = f["acct_flag"].values
        self.assertEqual(float(m[a].mean()), 1.0)


# ============================================================== 4. the mutation battery

def _accuracy_holds():
    """The property every mutation must break: the flag is the top quintile by tail mass, and
    the 2x2 cells reproduce the fixture's hand arithmetic."""
    f = mt.within_date_worst_quintile(_frame(range(100)), 'tail_mass')
    if int(f.sum()) != 20:
        return False
    if not bool(f.values[-1]) or bool(f.values[0]):
        return False
    # the TIE case: a constant column must flag NOTHING. This is the ONLY property that
    # separates `>` from `>=` at the quantile, and without it mutation m3 survives -- measured,
    # not hypothesised: the first cut of this battery let it through.
    if int(mt.within_date_worst_quintile(_frame([7.0] * 60), "tail_mass").sum()) != 0:
        return False
    t = mt.two_by_two(_twobytwo_fixture(), market_col="flagged", acct_col="acct_flag",
                      crash_col="crash")
    return (t["market_flagged_and_accounting_clean"]["rate"] == 0.6
            and t["market_clean_and_accounting_flagged"]["rate"] == 0.4
            and t["market_flagged_and_accounting_flagged"]["crashes"] == 1)


class TestMutations(unittest.TestCase):
    """A mutation battery is worthless without a baseline: if the suite were already red, every
    mutation would 'be caught' by a failure that has nothing to do with it."""

    def test_zzz_baseline_the_property_holds_before_any_mutation(self):
        self.assertTrue(_accuracy_holds())

    def _mutate(self, attr, replacement):
        original = getattr(mt, attr)
        try:
            setattr(mt, attr, replacement)
            caught = not _accuracy_holds()
        finally:
            setattr(mt, attr, original)
        self.assertIs(getattr(mt, attr), original, "the source was not restored")
        self.assertTrue(caught, "MUTATION SURVIVED: %s" % attr)

    def test_m1_flagging_the_BEST_quintile_instead_of_the_worst_is_caught(self):
        def bad(frame, value_col, *, date_col="date", q=mt.QUINTILE,
                min_names=mt.MIN_NAMES_PER_DATE):
            flag = pd.Series(False, index=frame.index)
            for _, g in frame.groupby(date_col, sort=False):
                v = pd.to_numeric(g[value_col], errors="coerce")
                if int(v.notna().sum()) < int(min_names):
                    continue
                flag.loc[g.index] = (v < float(v.quantile(float(q)))).fillna(False)
            return flag
        self._mutate("within_date_worst_quintile", bad)

    def test_m2_a_decile_instead_of_a_quintile_is_caught(self):
        orig = mt.within_date_worst_quintile
        self._mutate("within_date_worst_quintile",
                     lambda f, c, **k: orig(f, c, **{**k, "q": 0.10}))

    def test_m3_ge_instead_of_gt_at_the_quantile_is_caught(self):
        def bad(frame, value_col, *, date_col="date", q=mt.QUINTILE,
                min_names=mt.MIN_NAMES_PER_DATE):
            flag = pd.Series(False, index=frame.index)
            for _, g in frame.groupby(date_col, sort=False):
                v = pd.to_numeric(g[value_col], errors="coerce")
                if int(v.notna().sum()) < int(min_names):
                    continue
                flag.loc[g.index] = (v >= float(v.quantile(1.0 - float(q)))).fillna(False)
            return flag
        # on 0..99 this flags 21 rather than 20 -- a one-row leak that a share check would miss
        self._mutate("within_date_worst_quintile", bad)

    def test_m4_dropping_the_min_names_floor_is_caught(self):
        def bad(frame, value_col, *, date_col="date", q=mt.QUINTILE, min_names=0):
            return mt.within_date_worst_quintile(frame, value_col, date_col=date_col, q=q,
                                                 min_names=0)
        thin = _frame(range(40))
        self.assertEqual(int(mt.within_date_worst_quintile(thin, 'tail_mass').sum()), 0)
        self.assertEqual(int(bad(thin, "tail_mass").sum()), 8)

    def test_m5_a_transposed_2x2_cell_is_caught(self):
        real = mt.two_by_two

        def bad(frame, *, market_col, acct_col, crash_col):
            return real(frame, market_col=acct_col, acct_col=market_col, crash_col=crash_col)
        self._mutate("two_by_two", bad)

    def test_m6_a_rate_computed_over_the_wrong_denominator_is_caught(self):
        real = mt.two_by_two

        def bad(frame, *, market_col, acct_col, crash_col):
            out = real(frame, market_col=market_col, acct_col=acct_col, crash_col=crash_col)
            n = len(frame)
            for k, v in out.items():
                if isinstance(v, dict) and "rate" in v and v["n"]:
                    v["rate"] = v["crashes"] / n          # whole-frame denominator
            return out
        self._mutate("two_by_two", bad)

    def test_m7_counting_crashes_outside_the_cell_is_caught(self):
        real = mt.two_by_two

        def bad(frame, *, market_col, acct_col, crash_col):
            out = real(frame, market_col=market_col, acct_col=acct_col, crash_col=crash_col)
            tot = int(frame[crash_col].astype(bool).sum())
            out["market_flagged_and_accounting_clean"]["crashes"] = tot
            out["market_flagged_and_accounting_clean"]["rate"] = (
                tot / out["market_flagged_and_accounting_clean"]["n"])
            return out
        self._mutate("two_by_two", bad)

    def test_m8_a_pick_expiry_that_ignores_the_band_is_caught(self):
        asof = pd.Timestamp("2020-01-15")
        far = [asof + pd.Timedelta(days=d) for d in (10, 300)]
        self.assertIsNone(mt.pick_expiry(far, asof))
        nearest_overall = min(far, key=lambda e: abs((e - asof).days - mt.TARGET_DTE))
        self.assertNotEqual(mt.pick_expiry(far, asof), nearest_overall)


# ==================================================================== 5. NEUTRALITY (AST)

FORBIDDEN = ("fwd_ret_alpha", "top_decile_alpha", "long_short", "information_coefficient",
             "theme_ic", "expectancy", "sharpe", "quantile_backtest", "alpha")


class TestNeutrality(unittest.TestCase):
    """`E-4` is a CRASH-RATE item. Computing any relationship between an RND quantity and a
    forward RETURN voids the register (sec 8.2)."""

    def test_no_return_statistic_is_named_in_the_CODE_of_either_file(self):
        for path in (MODULE, RUNNER):
            code = _code_only(_src(path))
            for tok in FORBIDDEN:
                self.assertNotIn(tok, code,
                                 "%s: forbidden return statistic %r in code" % (path, tok))

    def test_the_stripper_is_not_vacuous_in_either_direction(self):
        """A stripper returning '' would make the sweep pass by seeing nothing -- `MB15`'s own
        defect. It must DROP prose and KEEP code."""
        code = _code_only(_src(MODULE))
        self.assertIn("def two_by_two", code)
        self.assertIn("within_date_worst_quintile", code)
        self.assertNotIn("S10 is the", code.replace("`", ""))
        self.assertGreater(len(code), 1500)

    def test_the_docstring_really_does_contain_a_forbidden_token(self):
        """Proves the AST strip is doing work rather than passing because the prose is clean."""
        self.assertIn("alpha", _src(MODULE))

    def test_no_forward_return_column_is_read_in_the_module(self):
        code = _code_only(_src(MODULE))
        for tok in ("fwd_ret", "forward_return", "realized_return", "future_return"):
            self.assertNotIn(tok, code, tok)

    def test_the_runner_reads_fwd_ret_ONLY_through_crash_flag(self):
        """The runner legitimately touches `fwd_ret` -- the crash event is defined on it -- but
        every use must go through `crash_gate.crash_flag`, never into a return statistic."""
        tree = ast.parse(_src(RUNNER))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr in ("crash_flag", "coverage")]
        self.assertTrue(calls, "the runner never forms the crash flag through crash_gate")
        # and it never computes a mean/sum of fwd_ret directly
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("mean", "sum", "prod"):
                seg = ast.unparse(node)
                self.assertNotIn("fwd_ret", seg, "a return statistic on fwd_ret: %s" % seg)


# ============================================================== 6. the pinned-store contract

class TestPinnedStore(unittest.TestCase):

    def test_the_runner_never_opens_the_mutable_store(self):
        code = _code_only(_src(RUNNER))
        self.assertNotIn("allow_mutable", code)
        self.assertNotIn("VALQUO_CHAINS", code)
        self.assertIn("resolve_chains", code)

    def test_the_runner_asserts_pinned_before_reading_anything(self):
        tree = ast.parse(_src(RUNNER))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "build")
        body = ast.unparse(fn)
        self.assertIn("pinned", body)
        self.assertIn("SystemExit", body)
        # the refusal must come BEFORE the bars/chain reads
        self.assertLess(body.index("pinned"), body.index("raw_close_series"))


# ================================================================= 7. the gate refusal

class TestArmRefusal(unittest.TestCase):
    """`E-1`'s lesson: a test that proves a refusal by REMOVING it runs the thing behind the
    refusal. Here the arm is not forbidden, but it is expensive and reads real data, so the
    refusal is proved with two DISTINCT refusal states plus an AST check -- never by flipping the
    flag to True and letting the arm run."""

    def test_the_arm_refuses_on_a_missing_artifact_and_on_a_failing_one(self):
        import scripts.e4_market_tail_flag as e4
        seen = []
        for payload in (None, {"all_gating_pass": False}, {"nothing": 1}):
            real = e4._out
            tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "_e4_refusal_probe.json")
            def fake(name, _t=tmp, _p=payload):
                return _t if name == e4.CONTROLS else _t + ".other"
            try:
                if payload is None and os.path.exists(tmp):
                    os.remove(tmp)
                elif payload is not None:
                    with io.open(tmp, "w", encoding="utf-8") as fh:
                        json.dump(payload, fh)
                e4._out = fake
                with self.assertRaises(SystemExit) as ctx:
                    e4.arm()
                seen.append(str(ctx.exception))
            finally:
                e4._out = real
                if os.path.exists(tmp):
                    os.remove(tmp)
        self.assertEqual(len(seen), 3)
        self.assertIn("absent", seen[0])
        # the MESSAGE is asserted, not merely that something raised -- a refusal for the wrong
        # reason would otherwise read as a pass
        for msg in seen[1:]:
            self.assertIn("did not pass", msg)

    def test_the_refusal_is_conditional_rather_than_hard_coded(self):
        tree = ast.parse(_src(RUNNER))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "arm")
        raises = [n for n in ast.walk(fn)
                  if isinstance(n, ast.Raise) or (isinstance(n, ast.Call)
                                                  and getattr(n.func, "id", "") == "SystemExit")]
        self.assertTrue(raises)
        ifs = [n for n in ast.walk(fn) if isinstance(n, ast.If)]
        self.assertGreaterEqual(len(ifs), 2, "the arm's refusal is not conditional")

    def test_the_verdict_grammar_has_all_three_states_reachable(self):
        """`P1S0`'s precedent. UNDERPOWERED must be a pre-defined outcome, not a thing said
        afterwards about a null."""
        src = _src(RUNNER)
        for state in ("PASS", "FAIL", "UNDERPOWERED"):
            self.assertIn('"%s"' % state, src, state)
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "arm")
        body = ast.unparse(fn)
        self.assertIn("mde80", body)
        self.assertIn("passed", body)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
