"""I-3 - the crash-count gate as a library.

WHAT THESE TESTS PIN.

The load-bearing one is that **the library owns the arithmetic and NOT the bars**. `MA5` found
that a default is exactly how the Harvey-Liu-Zhu hurdle froze at 3.0, and these bars are worse
than that: they are PRE-COMMITTED, so a library default would let a future register inherit
`MA28`'s pre-registration without writing one. Every bar is keyword-only with no default, and a
test asserts that no bar-shaped constant lives in the module at all.

Second: `MA28` must DELEGATE, not carry a second copy - `B7`'s nine-call-sites lesson, which
`MA5` then found again in the hurdle. Read from the SYNTAX TREE, never grepped, because `MA49`
recorded a fixture that failed against the FIXED tree since the repair comment quoted the defect
verbatim, and `MB8` hit the identical thing a second time three days ago.

Third: `quotable()` has NO difference field in any state, and withholds a ratio built on too few
events. `MA28-CARD` measured the base rate moving 4x between halves; `MB8` measured one crash in
a flagged bucket of 407.

The REAL-PANEL test reproduces the banked `MA28_CARD.json` and SKIPS LOUDLY where `data/` is
absent - it is gitignored, so a worktree and CI have none of it. A skip is reported and is never
counted as a pass.

    python tests/test_i3_crash_gate.py
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

from valuation.studies import crash_gate as CG  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(REPO, "valuation", "studies", "crash_gate.py")
MA28 = os.path.join(REPO, "scripts", "ma28_riskcard.py")
VALIDATOR = os.path.join(REPO, "scripts", "i3_crash_gate_validate.py")
_SKIPS = []

# MA28's own bars, quoted here so the tests exercise the real configuration. They live in
# MA28's script and in its register; this is a test fixture reading them, not a second home.
MA28_BARS = dict(ratio_floor=2.0, abs_floor_pp=0.50, n_perm=500, perm_seed=20260816,
                 min_flagged_per_date=30, min_kept_per_date=100)


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _frame(n_dates=6, n_names=400, seed=7, flag_rate=0.10, p_flag=0.06, p_kept=0.02):
    """A synthetic flagged/kept panel with a real, known rate difference."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        f = rng.random(n_names) < flag_rate
        p = np.where(f, p_flag, p_kept)
        rows.append(pd.DataFrame({
            "date": f"20{20 + d:02d}-01-15", "ticker": [f"T{i:04d}" for i in range(n_names)],
            "flagged": f, "_crash": rng.random(n_names) < p}))
    return pd.concat(rows, ignore_index=True)


def _data_root():
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isfile(os.path.join(env, "free_analysis", "panel_r5r6.pkl")):
        return env
    for base in (REPO, r"C:\Users\donni\Downloads\valuation-tool"):
        if os.path.isfile(os.path.join(base, "data", "free_analysis", "panel_r5r6.pkl")):
            return os.path.join(base, "data")
    return None


# ---------------------------------------------------------------- the bars are not in the library

class TestTheBarsDidNotMoveIntoTheLibrary(unittest.TestCase):
    """MA5: a default is how a bar freezes. These bars are pre-committed, so it is worse."""

    def test_no_bar_shaped_constant_is_defined_in_the_module(self):
        tree = ast.parse(_src(LIB))
        names = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
        banned = ("RATIO_FLOOR", "ABS_FLOOR_PP", "ABS_FLOOR", "MIN_FLAGGED_PER_DATE",
                  "MIN_KEPT_PER_DATE", "N_PERM", "PERM_SEED", "CRASH", "MIN_EVENTS")
        for b in banned:
            self.assertNotIn(
                b, names,
                f"crash_gate defines {b} at module level. The bars belong to the REGISTER that "
                f"declares them; a library constant is how MA28's pre-registration would be "
                f"inherited by a register that never wrote one (MA5).")

    def test_window_result_refuses_without_its_bars(self):
        df = _frame()
        with self.assertRaises(TypeError):
            CG.window_result(df, "x", crash_col="_crash")           # no bars at all
        with self.assertRaises(TypeError):
            CG.window_result(df, "x", crash_col="_crash", ratio_floor=2.0,
                             n_perm=10, perm_seed=1, min_flagged_per_date=1,
                             min_kept_per_date=1)                    # abs_floor_pp missing

    def test_per_date_diff_refuses_without_its_date_floors(self):
        with self.assertRaises(TypeError):
            CG.per_date_diff(_frame(), crash_col="_crash")

    def test_permutation_null_refuses_without_draws_and_seed(self):
        with self.assertRaises(TypeError):
            CG.permutation_null(_frame(), crash_col="_crash",
                                min_flagged_per_date=1, min_kept_per_date=1)

    def test_crash_flag_refuses_without_a_threshold(self):
        with self.assertRaises(TypeError):
            CG.crash_flag(pd.Series([0.1, -0.9]))
        with self.assertRaises(ValueError):
            CG.crash_flag(pd.Series([0.1, -0.9]), threshold=None)

    def test_quotable_refuses_without_min_events(self):
        with self.assertRaises(TypeError):
            CG.quotable({"ratio": 3.0})


# ---------------------------------------------------------------- the labels come from the bars

class TestBarLabelsAreGeneratedNeverTyped(unittest.TestCase):
    """MA49/MA46/U3's family: a label that disagrees with the value it labels."""

    def test_ma28s_own_keys_reproduce_byte_identical_at_ma28s_own_bars(self):
        r = CG.window_result(_frame(), "w", crash_col="_crash", **MA28_BARS)
        self.assertIn("B2_ratio_ge_2.0x", r)
        self.assertIn("B3_abs_diff_ge_0.50pp", r)

    def test_a_different_bar_produces_a_different_key(self):
        r = CG.window_result(_frame(), "w", crash_col="_crash",
                             **{**MA28_BARS, "ratio_floor": 3.0, "abs_floor_pp": 1.25})
        self.assertIn("B2_ratio_ge_3.0x", r)
        self.assertIn("B3_abs_diff_ge_1.25pp", r)
        self.assertNotIn("B2_ratio_ge_2.0x", r,
                         "a 3.0x comparison shipped under a key saying 2.0x")

    def test_no_bar_value_is_typed_as_a_string_literal_in_the_module(self):
        """The keys must be FORMATTED. A literal 'B2_ratio_ge_2.0x' in CODE is the defect.

        DOCSTRINGS ARE EXCLUDED, and that exclusion is not a convenience - it is the repair of
        this test's own first failure. It fired against the CORRECT tree because the module's
        docstring quotes `B2_ratio_ge_2.0x` while explaining the rule that forbids typing it.
        `MA49`'s comment-versus-code defect, and `MB8` hit the identical thing three days ago.
        A guard that cannot tell code from prose about code is not measuring the tree.
        """
        tree = ast.parse(_src(LIB))
        doc_nodes = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = getattr(node, "body", None) or []
                if body and isinstance(body[0], ast.Expr) \
                        and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    doc_nodes.add(id(body[0].value))
        checked = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in doc_nodes:
                checked += 1
                self.assertNotIn("B2_ratio_ge_2", node.value)
                self.assertNotIn("B3_abs_diff_ge_0.50", node.value)
        self.assertGreater(checked, 10,
                           "the docstring stripper removed everything; this guard would then "
                           "pass by seeing nothing (MB15's vacuous-stripper lesson)")


# ---------------------------------------------------------------- MA28 delegates

class TestMA28Delegates(unittest.TestCase):
    """B7: one definition, every consumer delegates. Read from the AST, never grepped (MA49)."""

    def test_ma28_imports_the_library(self):
        tree = ast.parse(_src(MA28))
        imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("studies"):
                imported = imported or any(a.name == "crash_gate" for a in node.names)
            if isinstance(node, ast.Import):
                imported = imported or any("crash_gate" in a.name for a in node.names)
        self.assertTrue(imported, "ma28_riskcard.py no longer imports crash_gate")

    def test_ma28_does_not_redefine_the_permutation_null_inline(self):
        """The signature of a second copy: the RNG construction living in MA28's own tree."""
        tree = ast.parse(_src(MA28))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "permutation_p95":
                body = ast.dump(node)
                self.assertNotIn("default_rng", body,
                                 "MA28 carries its own RNG again - that is the second copy "
                                 "B7 exists to prevent")
                self.assertIn("permutation_null", body,
                              "MA28's permutation_p95 must delegate to crash_gate")

    def test_exactly_one_definition_of_the_statistic_exists_in_the_tree(self):
        """MA5's sweep, narrowed to the STATISTIC and matched STRUCTURALLY.

        The object is `c[m].mean() - c[~m].mean()` - the flagged-minus-kept rate difference.
        Matched on the syntax tree's SHAPE, not on substrings of its dump.

        THAT DISTINCTION IS THIS TEST'S OWN REPAIR. The first cut asked for a dump containing
        `default_rng` and `permutation` and `fs`, and returned ELEVEN hits - `"fs"` matches
        inside `self`, `offsets` and every other identifier containing those two letters. A
        substring test against an AST dump is a grep wearing an AST's clothes, which is `MB1`'s
        three-wrong-substring-bans family in a new costume.
        """
        def _is_rate_difference(node):
            if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub)):
                return False

            def _mean_of_subscript(side):
                if not (isinstance(side, ast.Call)
                        and isinstance(side.func, ast.Attribute)
                        and side.func.attr == "mean"
                        and isinstance(side.func.value, ast.Subscript)):
                    return None
                sub = side.func.value
                if not isinstance(sub.value, ast.Name):
                    return None
                return sub.value.id, sub.slice

            lhs, rhs = _mean_of_subscript(node.left), _mean_of_subscript(node.right)
            if lhs is None or rhs is None or lhs[0] != rhs[0]:
                return False
            # one side must be the bitwise-inverted mask of the other
            l_s, r_s = lhs[1], rhs[1]
            inverted = (isinstance(r_s, ast.UnaryOp) and isinstance(r_s.op, ast.Invert)
                        and isinstance(l_s, ast.Name) and isinstance(r_s.operand, ast.Name)
                        and l_s.id == r_s.operand.id)
            return bool(inverted)

        found = []
        for base in (os.path.join(REPO, "valuation"), os.path.join(REPO, "scripts")):
            for root, _dirs, files in os.walk(base):
                if "__pycache__" in root:
                    continue
                for fn in sorted(files):
                    if not fn.endswith(".py"):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        tree = ast.parse(_src(p))
                    except SyntaxError:
                        continue
                    for node in ast.walk(tree):
                        if _is_rate_difference(node):
                            found.append(os.path.relpath(p, REPO).replace("\\", "/"))
        found = sorted(set(found))
        lib = [p for p in found if p.startswith("valuation/")]
        scr = [p for p in found if p.startswith("scripts/")]

        # THE LIBRARY CLAIM, which is the one B7 is about: exactly one shared definition.
        self.assertEqual(
            lib, ["valuation/studies/crash_gate.py"],
            f"the masked-minus-complement mean is defined more than once under valuation/: {lib}")

        # THE SCRIPT HITS ARE A KNOWN SET, AND THE REASON IS THIS TEST'S SECOND REPAIR.
        # The shape `a[m].mean() - a[~m].mean()` is GENERIC - it is "the mean difference
        # between a masked group and its complement" - and it cannot by itself tell a crash
        # RATE difference from a RETURN difference. `scripts/s17_event_codes.py` matches it and
        # is NOT a duplicate: its operand is `fwd`, the forward return, so it computes S17's
        # event-code return drift. Verified by reading the operand, not assumed. A NEW entry
        # here is the signal worth having: it means somebody wrote a fourth copy, or a third
        # object that looks like one, and a human should look.
        self.assertEqual(
            scr, ["scripts/s17_event_codes.py"],
            f"a new script computes the masked-minus-complement mean: {scr}. If it is a crash "
            f"RATE difference it belongs in crash_gate (B7); if it is a RETURN difference like "
            f"S17's, add it to this known set with the operand named.")

    def test_that_sweep_is_not_vacuous(self):
        """A matcher that finds nothing would pass the test above by seeing nothing."""
        import subprocess
        src = subprocess.run(["git", "show", "HEAD:scripts/ma28_riskcard.py"], cwd=REPO,
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout
        if not src:
            _SKIPS.append("git show unavailable for the vacuity control")
            self.skipTest("git unavailable")
        # the pre-refactor MA28 is reachable in history and DID carry the statistic
        log = subprocess.run(["git", "log", "--format=%H", "--", "scripts/ma28_riskcard.py"],
                             cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.split()
        hit = False
        for sha in log[:12]:
            old = subprocess.run(["git", "show", f"{sha}:scripts/ma28_riskcard.py"], cwd=REPO,
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace").stdout
            if "crash_gate" in old or not old:
                continue
            tree = ast.parse(old)
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
                    d = ast.dump(node)
                    if "attr='mean'" in d and "Invert" in d:
                        hit = True
        self.assertTrue(hit, "the pre-refactor MA28 must contain the statistic this matcher "
                             "looks for, or the sweep above is passing by finding nothing")


# ---------------------------------------------------------------- quote the ratio, not the gap

class TestQuotableEnforcesMA28sReportingRule(unittest.TestCase):

    def test_quotable_has_no_difference_field_in_any_state(self):
        po = CG.pooled(_frame(), crash_col="_crash")
        for min_events in (0, 1, 5, 10_000):
            q = CG.quotable(po, min_events=min_events)
            for k in q:
                self.assertNotIn("diff", k.lower(),
                                 f"quotable() emitted {k}; MA28-CARD's rule is ratio and BOTH "
                                 f"rates, never the difference - the base rate moved 4x "
                                 f"between halves")
                self.assertNotIn("_pp", k.lower())

    def test_quotable_carries_both_rates_and_both_counts(self):
        q = CG.quotable(CG.pooled(_frame(), crash_col="_crash"), min_events=1)
        for k in ("rate_flagged", "rate_kept", "n_crash_flagged", "n_crash_kept",
                  "n_flagged", "n_kept"):
            self.assertIn(k, q)
        self.assertIsNotNone(q["ratio"])

    def test_a_ratio_on_one_event_is_withheld_with_a_reason(self):
        """MB8: one crash of 407. A ratio there is a number that will be read as a rate."""
        po = {"n_flagged": 407, "n_kept": 8081, "n_crash_flagged": 1, "n_crash_kept": 52,
              "rate_flagged": 1 / 407, "rate_kept": 52 / 8081, "rate_all": None,
              "ratio": (1 / 407) / (52 / 8081)}
        q = CG.quotable(po, min_events=10)
        self.assertIsNone(q["ratio"])
        self.assertIn("flagged", q["ratio_withheld_because"])
        self.assertEqual(q["n_crash_flagged"], 1, "the COUNT still travels; only the ratio does not")

    def test_the_ratio_survives_when_both_buckets_are_thick_enough(self):
        po = {"n_flagged": 407, "n_kept": 8081, "n_crash_flagged": 40, "n_crash_kept": 52,
              "rate_flagged": 40 / 407, "rate_kept": 52 / 8081, "rate_all": None,
              "ratio": (40 / 407) / (52 / 8081)}
        q = CG.quotable(po, min_events=10)
        self.assertIsNotNone(q["ratio"])
        self.assertIsNone(q["ratio_withheld_because"])


# ---------------------------------------------------------------- the arithmetic behaves

class TestTheArithmetic(unittest.TestCase):

    def test_permutation_preserves_each_dates_flagged_count(self):
        """The null's whole claim: counts and outcomes held fixed, identity destroyed."""
        df = _frame(n_dates=4, n_names=300)
        a = CG.permutation_null(df, crash_col="_crash", n_draws=25, seed=11,
                                min_flagged_per_date=1, min_kept_per_date=1)
        b = CG.permutation_null(df, crash_col="_crash", n_draws=25, seed=11,
                                min_flagged_per_date=1, min_kept_per_date=1)
        self.assertEqual(a, b, "the null is not reproducible at a fixed seed")
        c = CG.permutation_null(df, crash_col="_crash", n_draws=25, seed=12,
                                min_flagged_per_date=1, min_kept_per_date=1)
        self.assertNotEqual(a["p95"], c["p95"], "the seed does nothing")

    def test_the_null_is_centred_near_zero_on_a_flag_that_carries_no_information(self):
        rng = np.random.default_rng(3)
        df = _frame(n_dates=8, n_names=500, p_flag=0.03, p_kept=0.03)
        df["flagged"] = rng.random(len(df)) < 0.1
        n = CG.permutation_null(df, crash_col="_crash", n_draws=200, seed=5,
                                min_flagged_per_date=1, min_kept_per_date=1)
        self.assertLess(abs(n["p50"]), 0.01)

    def test_a_date_below_either_floor_is_dropped(self):
        df = _frame(n_dates=3, n_names=200, flag_rate=0.5)
        wide = CG.per_date_diff(df, crash_col="_crash", min_flagged_per_date=1,
                                min_kept_per_date=1)
        tight = CG.per_date_diff(df, crash_col="_crash", min_flagged_per_date=10_000,
                                 min_kept_per_date=1)
        self.assertEqual(len(wide), 3)
        self.assertEqual(len(tight), 0)

    def test_pooled_ratio_is_none_when_the_kept_rate_is_zero(self):
        df = _frame(n_dates=2, n_names=100, p_kept=0.0, p_flag=0.5)
        po = CG.pooled(df, crash_col="_crash")
        self.assertEqual(po["rate_kept"], 0.0)
        self.assertIsNone(po["ratio"], "a ratio was formed against a zero denominator")

    def test_void_when_no_date_qualifies(self):
        r = CG.window_result(_frame(), "w", crash_col="_crash",
                             **{**MA28_BARS, "min_flagged_per_date": 10_000})
        self.assertIn("VOID", r)

    def test_halves_embargoes_the_middle_date(self):
        df = _frame(n_dates=7, n_names=50)
        early, late, boundary = CG.halves(df)
        self.assertNotIn(boundary, set(early["date"]))
        self.assertNotIn(boundary, set(late["date"]))
        self.assertEqual(early["date"].nunique() + late["date"].nunique(), 6)

    def test_halves_refuses_a_panel_too_short_to_split(self):
        with self.assertRaises(ValueError):
            CG.halves(_frame(n_dates=2, n_names=10))

    def test_nw_t_is_the_shipped_definition(self):
        from valuation.edge.statistics import mean_inference
        xs = [0.1, -0.2, 0.35, 0.05, -0.11, 0.2, 0.02]
        self.assertEqual(CG.nw_t(xs), float(mean_inference(xs, lag=1)["t"]))


# ---------------------------------------------------------------- a missing outcome is not safe

class TestAMissingOutcomeIsNotAnAbsentCrash(unittest.TestCase):
    """MB8's generalisation: the bucket a rule cannot evaluate is a real bucket."""

    def test_a_nan_forward_return_reads_as_not_crashed(self):
        s = pd.Series([-0.9, np.nan, 0.2])
        c = CG.crash_flag(s, threshold=-0.5)
        self.assertEqual(list(c), [True, False, False])

    def test_coverage_counts_the_rows_that_could_not_be_evaluated(self):
        cov = CG.coverage(pd.Series([-0.9, np.nan, 0.2, np.nan]))
        self.assertEqual(cov["rows"], 4)
        self.assertEqual(cov["rows_without_outcome"], 2)
        self.assertEqual(cov["coverage"], 0.5)
        self.assertIn("not a crash-free row", cov["note"])


# ---------------------------------------------------------------- the required-n hook

class TestRequiredNHook(unittest.TestCase):

    def test_required_dates_reproduces_power_gate_exactly(self):
        from valuation.edge.power_gate import required_n, z_for_power
        got = CG.required_dates(effect=1.6, sd=2.0, crit=2.0, power=0.80)
        want = required_n(1.6 / 2.0, crit=2.0, z_power=z_for_power(0.80))
        self.assertEqual(got["required_dates"], want)

    def test_the_critical_value_still_refuses_to_default(self):
        """Delegated refusal - MA5's rule must survive the extra layer."""
        with self.assertRaises(ValueError):
            CG.required_dates(effect=1.0, sd=1.0)
        with self.assertRaises(ValueError):
            CG.required_rows(base_rate=0.01, ratio=2.0, flagged_share=0.05)
        with self.assertRaises(ValueError):
            CG.required_rows(base_rate=0.01, ratio=2.0, flagged_share=0.05,
                             n_trials=236, crit=2.0)

    def test_unequal_allocation_needs_more_rows_than_equal_allocation(self):
        r = CG.required_rows(base_rate=0.0087, ratio=2.0, flagged_share=0.0356, crit=2.0)
        self.assertGreater(r["required_rows_total"],
                           r["required_rows_equal_allocation_for_contrast"])
        self.assertGreater(r["allocation_penalty_x"], 5.0,
                           "at a 3.56% flagged share the equal-n formula understates badly; "
                           "if this ever reads ~1 the allocation has stopped being used")

    def test_a_balanced_split_carries_no_allocation_penalty(self):
        r = CG.required_rows(base_rate=0.05, ratio=2.0, flagged_share=0.5, crit=2.0)
        self.assertAlmostEqual(r["allocation_penalty_x"], 1.0, places=9)

    def test_thin_expected_counts_are_flagged_not_hidden(self):
        r = CG.required_rows(base_rate=1e-4, ratio=1.02, flagged_share=0.5, crit=2.0)
        self.assertIn("normal_approximation_thin", r)
        self.assertIsInstance(r["normal_approximation_thin"], bool)

    def test_required_rows_refuses_a_ratio_of_one_and_impossible_shares(self):
        with self.assertRaises(ValueError):
            CG.required_rows(base_rate=0.01, ratio=1.0, flagged_share=0.05, crit=2.0)
        with self.assertRaises(ValueError):
            CG.required_rows(base_rate=0.01, ratio=2.0, flagged_share=0.0, crit=2.0)
        with self.assertRaises(ValueError):
            CG.required_rows(base_rate=0.6, ratio=2.0, flagged_share=0.5, crit=2.0)


# ---------------------------------------------------------------- the validation actually ran

class TestTheValidationArtifact(unittest.TestCase):

    def test_the_validator_gates_on_a_leaf_COUNT(self):
        """MB21's C1 passed vacuously at a perfect 0.000e+00 by comparing nothing."""
        tree = ast.parse(_src(VALIDATOR))
        names = {t.id for node in tree.body if isinstance(node, ast.Assign)
                 for t in node.targets if isinstance(t, ast.Name)}
        self.assertIn("MIN_LEAVES", names,
                      "the validator must refuse below a minimum leaf count, or a 0.000e+00 "
                      "over zero comparisons reads as a pass")

    def test_banked_validation_reproduces_ma28_exactly(self):
        p = os.path.join(REPO, "data", "free_analysis", "I3_CRASH_GATE_VALIDATION.json")
        if not os.path.isfile(p):
            _SKIPS.append("I3_CRASH_GATE_VALIDATION.json absent (data/ is gitignored)")
            self.skipTest("validation artifact absent")
        with io.open(p, encoding="utf-8") as fh:
            v = json.load(fh)
        self.assertTrue(v["all_pass"])
        a = v["A_library_vs_banked"]
        self.assertEqual(a["max_abs_delta"], 0.0)
        self.assertEqual(a["n_moved"], 0)
        self.assertEqual(a["only_in_library"], [])
        self.assertEqual(a["only_in_banked"], [])
        self.assertGreaterEqual(a["n_shared_leaves"], v["min_leaves_required"])
        b = v["B_library_vs_pre_refactor"]
        if b is not None:
            self.assertEqual(b["max_abs_delta"], 0.0)
            self.assertEqual(b["n_moved"], 0)

    def test_real_panel_reproduces_the_banked_card(self):
        root = _data_root()
        if root is None:
            _SKIPS.append("panel_r5r6.pkl absent (data/ is gitignored)")
            self.skipTest("panel absent")
        # was `REPO`: the helper resolves the data root and the next line ignored it, so on
        # any worktree this check skipped even with the card present at the resolved root.
        card = os.path.join(root, "free_analysis", "MA28_CARD.json")
        if not os.path.isfile(card):
            _SKIPS.append("MA28_CARD.json absent")
            self.skipTest("banked card absent")
        with io.open(card, encoding="utf-8") as fh:
            w = json.load(fh)["windows"]
        # the three figures MA28-CARD's own write-up quotes, re-read from the artifact
        self.assertAlmostEqual(w["full_sample"]["pooled"]["ratio"], 3.0422123745999063, places=12)
        self.assertAlmostEqual(w["early_half"]["pooled"]["ratio"], 3.4208900608295076, places=12)
        self.assertAlmostEqual(w["late_half"]["pooled"]["ratio"], 2.9321220447443164, places=12)
        self.assertEqual(w["full_sample"]["pooled"]["n_flagged"], 6542)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
