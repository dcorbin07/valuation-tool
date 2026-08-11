"""U1 — pins the calibration script, which must derive bars and nothing else (2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

`PREREG_u1_composite_entry.md` section 5 says the bars are "computed and committed in their own
commit, with the scoring module not yet written". That claim is only worth making if the bar
script genuinely cannot compute an arm's outcome — otherwise the ordering is theatre. These tests
read the script's own source and its behaviour to hold it to that.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import u1_bar as UB                    # noqa: E402
from valuation.edge import composite_entry as CE    # noqa: E402


def _src(mod):
    import inspect
    return inspect.getsource(mod)


def _code(mod):
    """The module's source with its docstring removed.

    The docstring legitimately NAMES the things the code must not do ("it does not import
    `mean_pnl` for the arms at all"), so a search over the raw source matches its own
    explanation. The property worth pinning is about executable code, so the prose is stripped
    before looking — a test that failed on its own documentation would only teach the next
    author to delete the documentation.
    """
    import ast
    src = _src(mod)
    tree = ast.parse(src)
    if not (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        return src
    node = tree.body[0]
    lines = src.splitlines(keepends=True)
    # Line numbers, not string replacement: `ast.get_docstring` returns the CLEANED text
    # (dedented, escapes processed), so matching it against the raw source silently fails and
    # every assertion built on it passes vacuously. That is what the guard test below caught.
    del lines[node.lineno - 1:node.end_lineno]
    return "".join(lines)


class TheCalibrationScriptCannotScoreAnArm(unittest.TestCase):
    """The load-bearing property. If any of these fail, the bar could be a function of the answer
    it is supposed to be judged against, and committing it first proves nothing."""

    def test_it_never_calls_mean_pnl(self):
        self.assertNotIn("mean_pnl", _code(UB))

    def test_the_docstring_is_what_was_stripped_not_the_code(self):
        """Guards the guard: if `_code` ever silently returned an empty string, every
        assertNotIn above would pass vacuously."""
        body = _code(UB)
        self.assertIn("def main(", body)
        self.assertIn("arm_shape", body)
        self.assertLess(len(body), len(_src(UB)))

    def test_it_never_calls_arm_position(self):
        """`arm_position` is where an arm meets a null. It belongs to the scorer, not here."""
        self.assertNotIn("arm_position", _code(UB))

    def test_the_only_thing_it_takes_from_an_arm_is_its_shape(self):
        src = _src(UB)
        self.assertIn("arm_shape", src)
        self.assertIn("SHAPE ONLY", src)

    def test_it_declares_the_stage_in_the_artifact_it_writes(self):
        self.assertIn('"stage": "calibration_only"', _src(UB))


class TheDrawCountAndPercentileAreTheRegisteredOnes(unittest.TestCase):
    def test_two_hundred_draws_at_the_ninety_fifth_percentile(self):
        self.assertEqual(UB.N_DRAWS, 200)
        self.assertEqual(UB.PCTILE, 95)

    def test_the_seed_block_is_fixed_and_contiguous(self):
        self.assertEqual(UB.SEED0, 2000)

    def test_it_calibrates_every_arm_in_both_flavours(self):
        """Three arms x {plain, cap-matched} = six bars. A missing cap-matched bar would leave
        the ledger's reopen condition unmeasured for that arm."""
        src = _src(UB)
        self.assertIn("for match in (False, True)", src)
        self.assertIn("CE.ARMS.items()", src)


class TheBarsBehaveTheWayTheRegisterSaysTheyDo(unittest.TestCase):
    """Run the real `null_gains` on a synthetic grid — no licensed data — and check the shape of
    the answer rather than trusting the prose."""

    def setUp(self):
        rows = []
        for d in ("D1", "D2", "D3", "D4"):
            for i in range(30):
                rows.append({"asof": d, "ticker": "T%02d" % i,
                             "u1_pct_univ": i / 29.0, "pnl_pct": (i - 15) * 0.05,
                             "cap_tier": ("mega" if i % 3 == 0 else "large"),
                             "alert_ts": "2020-01-0%d" % (1 + int(d[1]))})
        self.grid = rows

    def test_the_bar_sits_above_the_median_and_the_median_sits_near_zero(self):
        counts = {d: 3 for d in ("D1", "D2", "D3", "D4")}
        got = CE.null_gains(self.grid, counts, None, n_draws=200, seed0=UB.SEED0)
        self.assertGreater(got["bar_pp"], got["median_pp"])
        self.assertLess(abs(got["median_pp"]), 15.0)
        self.assertEqual(got["n_draws"], 200)

    def test_the_bar_is_reproducible_from_the_same_seed_block(self):
        counts = {d: 3 for d in ("D1", "D2", "D3", "D4")}
        a = CE.null_gains(self.grid, counts, None, n_draws=50, seed0=UB.SEED0)
        b = CE.null_gains(self.grid, counts, None, n_draws=50, seed0=UB.SEED0)
        self.assertEqual(a["bar_pp"], b["bar_pp"])

    def test_a_wider_selection_gives_a_tighter_bar(self):
        """Sanity on the machinery, not a finding: a draw of 20 of 30 per date averages more of
        the same pool than a draw of 3, so its gains must be less dispersed. If this ever
        inverted, the null would not be doing what the register describes."""
        wide = CE.null_gains(self.grid, {d: 20 for d in ("D1", "D2", "D3", "D4")},
                             None, n_draws=200, seed0=UB.SEED0)
        narrow = CE.null_gains(self.grid, {d: 3 for d in ("D1", "D2", "D3", "D4")},
                               None, n_draws=200, seed0=UB.SEED0)
        self.assertLess(wide["bar_pp"], narrow["bar_pp"])


class TheModuleSurvivesACheckoutWithNoLicensedData(unittest.TestCase):
    def test_import_does_not_need_the_grid(self):
        import importlib
        m = importlib.import_module("scripts.u1_bar")
        self.assertTrue(m.NULL_PATH.endswith("U1_NULL.json"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
