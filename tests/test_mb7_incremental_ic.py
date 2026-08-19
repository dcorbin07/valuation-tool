"""MB7 - the effective-coverage rule for the incremental-IC gate.

WHAT THESE TESTS PIN, and the split is deliberate.

The SYNTHETIC tests carry the mechanism and run anywhere, including CI: a late-starting
incumbent costs dates, `halves()` passes on the raw geometry while the residualised statistic
would be scored on a cell below the shipped floor, and the gate refuses exactly that case.
They are the tripwires and they are mutation-tested.

The REAL-PANEL tests reproduce the measured figures MB7 rests on. `data/` is gitignored, so a
worktree and CI have none of it. They SKIP LOUDLY - the suite prints what it skipped and why,
because a data-dependent test that skips quietly is the vacuous pass this project has caught
five times, and MB42 records a gate suite that is green in CI and red on the machine that owns
the data. Skipping is reported; it is never silent and never counted as a pass.

NOTHING HERE RE-RUNS OR RE-SCORES A LANDED REGISTER. The MA31/MA32 test READS the banked
artifact to establish that those registers did NOT inherit the defect - which is a correction
to MB7's own consequence (3), measured rather than argued.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from valuation.studies import incremental_ic as II  # noqa: E402
from valuation.studies import surface_stock as SS  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKIPS = []


def _data_root():
    """`data/` is gitignored, so a worktree has none. S17's walk-up, not a junction."""
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env and os.path.isdir(env):
        return env
    p = REPO
    for _ in range(6):
        cand = os.path.join(p, "data")
        if os.path.exists(os.path.join(cand, "free_analysis",
                                       "panel_corrected_69d.pkl")):
            return cand
        p = os.path.dirname(p)
    return os.path.join(REPO, "data")


DATA = _data_root()
PANEL = os.path.join(DATA, "free_analysis", "panel_corrected_69d.pkl")
MA3132 = os.path.join(DATA, "free_analysis", "MA31_MA32.json")


def _skip(name, why):
    _SKIPS.append("%s (%s)" % (name, why))
    return True


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _panel():
    p = pd.read_pickle(PANEL)
    p["date"] = pd.to_datetime(p["date"])
    return p


# --------------------------------------------------------------------------- #
#  A synthetic panel carrying the exact shape of the real defect
# --------------------------------------------------------------------------- #
def _synthetic(n_dates=69, n_names=60, late_from=30, seed=7):
    """`institutional` absent on the first `late_from` dates - the real shape, in miniature.

    The REAL incumbent names are used deliberately: a synthetic column set would resolve to
    basis "custom" and the gate would refuse on the naming rule before ever reaching the
    geometry rule, so the test would pass for the wrong reason.

    `late_from` is chosen so the EFFECTIVE dates can still be split at the floor (39 -> 19/19)
    while the raw split leaves a thin effective cell (4/34). That isolates the one leg under
    test: the only thing wrong is WHICH date list was halved.
    """
    rng = np.random.default_rng(seed)
    late = II.LATE_STARTING_INCUMBENT
    full = [c for c in SS.INCUMBENTS if c != late]
    rows = []
    dates = pd.date_range("2009-01-15", periods=n_dates, freq="91D")
    for i, d in enumerate(dates):
        for j in range(n_names):
            r = {"date": d, "ticker": "T%03d" % j,
                 "cand": rng.normal(), "fwd_ret": rng.normal()}
            for c in full:
                r[c] = rng.normal()
            r[late] = rng.normal() if i >= late_from else np.nan
            rows.append(r)
    return pd.DataFrame(rows), tuple(SS.INCUMBENTS), tuple(full)


class TestBasisMustBeChosen(unittest.TestCase):
    """TRIPWIRE. MA5's lesson: a shared primitive with a default is how a bar freezes."""

    def test_basis_for_refuses_an_unnamed_choice(self):
        for bad in ("all", "", "SEVEN", "7", None):
            with self.assertRaises(SS.RegisterViolation):
                II.basis_for(bad)

    def test_basis_for_has_no_default_argument(self):
        """A default would let a register inherit a window it never chose."""
        src = _read(os.path.join(REPO, "valuation", "studies", "incremental_ic.py"))
        fn = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "basis_for"][0]
        self.assertEqual(fn.args.defaults, [],
                         "basis_for must have no default - the register must choose")

    def test_the_two_bases_differ_by_exactly_one_named_column(self):
        self.assertEqual(set(II.BASIS_SEVEN) - set(II.BASIS_SIX),
                         {II.LATE_STARTING_INCUMBENT})
        self.assertEqual(len(II.BASIS_SEVEN), 7)
        self.assertEqual(len(II.BASIS_SIX), 6)

    def test_the_incumbents_are_imported_not_restated(self):
        """One definition. A second copy of the tuple is audit B7's defect class."""
        self.assertEqual(tuple(II.BASIS_SEVEN), tuple(SS.INCUMBENTS))
        src = _read(os.path.join(REPO, "valuation", "studies", "incremental_ic.py"))
        body = src.split('"""', 2)[2]          # strip the module docstring's prose
        self.assertNotIn('"value", "quality"', body,
                         "incremental_ic must import INCUMBENTS, never restate it")
        self.assertIn("from .surface_stock import", src)


class TestTheDefectMechanism(unittest.TestCase):
    """TRIPWIRE. The raw split passes its own guard and the statistic runs on a thin cell."""

    def setUp(self):
        self.frame, self.seven, self.six = _synthetic()

    def test_a_late_starting_incumbent_costs_dates(self):
        raw = II.raw_dates(self.frame, "cand")
        eff7 = II.effective_dates(self.frame, "cand", self.seven)
        eff6 = II.effective_dates(self.frame, "cand", self.six)
        self.assertEqual(len(raw), 69)
        self.assertEqual(len(eff7), 39, "the late column must cost exactly the early dates")
        self.assertEqual(len(eff6), 69, "dropping it must restore every date")

    def test_halves_passes_on_raw_while_the_effective_cell_is_below_the_floor(self):
        """The whole defect in one assertion."""
        raw = II.raw_dates(self.frame, "cand")
        early, late, _ = SS.halves(raw)                     # does NOT raise
        self.assertGreaterEqual(len(early), SS.MIN_DATES)
        self.assertGreaterEqual(len(late), SS.MIN_DATES)
        eff = set(II.effective_dates(self.frame, "cand", self.seven))
        n_early = len([d for d in early if d in eff])
        self.assertLess(n_early, SS.MIN_DATES,
                        "the effective early cell must fall below the floor that just passed")

    def test_splitting_the_effective_dates_is_the_repair(self):
        eff = II.effective_dates(self.frame, "cand", self.seven)
        early, late, boundary = SS.halves(eff)
        self.assertGreaterEqual(len(early), SS.MIN_DATES)
        self.assertGreaterEqual(len(late), SS.MIN_DATES)
        raw_boundary = SS.halves(II.raw_dates(self.frame, "cand"))[2]
        self.assertNotEqual(boundary, raw_boundary,
                            "the boundary must move - the corrected early half is a "
                            "different object and the register must say so")


class TestTheGate(unittest.TestCase):
    """TRIPWIRE. `require_effective_coverage` refuses the silent case and only that case."""

    def setUp(self):
        self.frame, self.seven, self.six = _synthetic()

    def test_it_refuses_the_seven_basis_raw_split(self):
        blk = II.effective_coverage(self.frame, "cand", self.seven)
        with self.assertRaises(SS.RegisterViolation) as cm:
            II.require_effective_coverage(blk)
        msg = str(cm.exception)
        self.assertIn("MB7 defect", msg)
        self.assertIn("Split the EFFECTIVE dates", msg)

    def test_it_passes_the_six_basis_and_is_therefore_not_vacuous(self):
        """POSITIVE CONTROL. A gate that refuses everything measures nothing."""
        blk = II.effective_coverage(self.frame, "cand", self.six)
        II.require_effective_coverage(blk)                  # must not raise
        self.assertEqual(blk["n_dates_lost_to_incumbent_dropna"], 0)
        self.assertTrue(blk["split_on_effective"]["ok"])

    def test_it_refuses_an_absent_or_incomplete_block(self):
        with self.assertRaises(SS.RegisterViolation):
            II.require_effective_coverage(None)
        with self.assertRaises(SS.RegisterViolation):
            II.require_effective_coverage({})
        blk = II.effective_coverage(self.frame, "cand", self.six)
        blk.pop("n_dates_effective")
        with self.assertRaises(SS.RegisterViolation):
            II.require_effective_coverage(blk)

    def test_it_refuses_an_unnamed_custom_basis(self):
        """A bare tuple hides WHICH window was tested, which is the thing being disclosed."""
        blk = II.effective_coverage(self.frame, "cand", (SS.INCUMBENTS[0],))
        self.assertEqual(blk["basis"], "custom")
        with self.assertRaises(SS.RegisterViolation):
            II.require_effective_coverage(blk)

    def test_the_block_reports_both_geometries(self):
        blk = II.effective_coverage(self.frame, "cand", self.seven)
        self.assertEqual(blk["n_dates_raw"], 69)
        self.assertEqual(blk["n_dates_effective"], 39)
        self.assertEqual(blk["n_dates_lost_to_incumbent_dropna"], 30)
        self.assertEqual(blk["split_on_raw_then_intersect"]["n_early"], 4)
        self.assertTrue(blk["split_on_effective"]["ok"])
        self.assertFalse(blk["split_on_raw_then_intersect"]["ok"])

    def test_the_rendering_is_ascii_so_a_register_can_print_it(self):
        """A cp1252 console raises on an em-dash, and this block is printed by every register."""
        blk = II.effective_coverage(self.frame, "cand", self.six)
        txt = II.format_coverage(blk)
        txt.encode("ascii")                                  # must not raise
        self.assertIn("effective", txt)

    def test_the_coverage_rule_names_all_four_requirements(self):
        rule = II.COVERAGE_RULE
        for token in ("basis_for", "effective_coverage", "EFFECTIVE dates", "power controls"):
            self.assertIn(token, rule, "the stated rule must name %r" % token)


class TestRealPanel(unittest.TestCase):
    """MB7's measured figures. SKIPS LOUDLY without the licensed export."""

    def test_the_two_basis_table_reproduces(self):
        if not os.path.exists(PANEL):
            return _skip("two_basis_table", "panel_corrected_69d.pkl absent")
        p = _panel()
        n = len(p)
        seven = p.dropna(subset=list(SS.INCUMBENTS))
        six = p.dropna(subset=list(II.BASIS_SIX))
        self.assertEqual(len(seven), 66444)
        self.assertAlmostEqual(100.0 * len(seven) / n, 58.31, places=2)
        self.assertEqual(len(six), 92540)
        self.assertAlmostEqual(100.0 * len(six) / n, 81.21, places=2)

    def test_only_institutional_costs_dates(self):
        """LEAVE-ONE-OUT. MB7 asserts the cause is one column; this proves no other shares it."""
        if not os.path.exists(PANEL):
            return _skip("leave_one_out", "panel absent")
        p = _panel()

        def n_dates(cols):
            q = p.dropna(subset=list(cols))
            g = q.groupby("date").size()
            return len([d for d, k in g.items() if k >= SS.MIN_NAMES])

        for c in SS.INCUMBENTS:
            rest = [x for x in SS.INCUMBENTS if x != c]
            expected = 69 if c == II.LATE_STARTING_INCUMBENT else 49
            self.assertEqual(n_dates(rest), expected,
                             "dropping %s should leave %d dates" % (c, expected))

    def test_institutional_is_the_only_theme_that_starts_late(self):
        if not os.path.exists(PANEL):
            return _skip("late_start", "panel absent")
        p = _panel()
        for c in SS.INCUMBENTS:
            g = p.dropna(subset=[c]).groupby("date").size()
            ok = sorted(d for d, k in g.items() if k >= SS.MIN_NAMES)
            first = str(ok[0])[:10]
            if c == II.LATE_STARTING_INCUMBENT:
                self.assertEqual(len(ok), 49)
                self.assertEqual(first, "2014-01-17")
            else:
                self.assertEqual(len(ok), 69, "%s should cover every date" % c)
                self.assertEqual(first, "2009-01-15")

    def test_the_silent_thin_half_is_real_on_the_shipped_panel(self):
        if not os.path.exists(PANEL):
            return _skip("thin_half", "panel absent")
        p = _panel()
        blk = II.effective_coverage(p, "z_gp_on_capital", II.basis_for("seven"))
        self.assertEqual(blk["n_dates_raw"], 69)
        self.assertEqual(blk["n_dates_effective"], 49)
        self.assertEqual(blk["first_date_effective"], "2014-01-17")
        self.assertEqual(blk["n_dates_effective_pre_2021"], 28)
        self.assertEqual(blk["split_on_raw_then_intersect"]["n_early"], 14)
        self.assertFalse(blk["split_on_raw_then_intersect"]["ok"])
        self.assertEqual(blk["split_on_effective"]["n_early"], 24)
        self.assertEqual(blk["split_on_effective"]["n_late"], 24)
        self.assertTrue(blk["split_on_effective"]["ok"])
        self.assertEqual(blk["split_on_raw_then_intersect"]["boundary"], "2017-07-20")
        self.assertEqual(blk["split_on_effective"]["boundary"], "2020-01-22")

    def test_the_six_basis_restores_the_full_window(self):
        if not os.path.exists(PANEL):
            return _skip("six_basis", "panel absent")
        p = _panel()
        blk = II.effective_coverage(p, "z_gp_on_capital", II.basis_for("six"))
        self.assertEqual(blk["n_dates_effective"], 69)
        self.assertEqual(blk["first_date_effective"], "2009-01-15")
        II.require_effective_coverage(blk)                   # must not raise


class TestWhoActuallyInheritedIt(unittest.TestCase):
    """MB7's consequence (3) is too broad, and the banked artifact says so."""

    def test_ma31_ma32_did_not_inherit_the_defect(self):
        if not os.path.exists(MA3132):
            return _skip("ma31_ma32_immunity", "MA31_MA32.json absent")
        import json
        d = json.loads(_read(MA3132))
        checked = 0
        for arm, blocks in d.get("arms", {}).items():
            for cell in ("full", "early", "late"):
                b = blocks.get(cell) or {}
                if "n_dates_raw" in b and "n_dates_incremental" in b:
                    self.assertEqual(
                        b["n_dates_raw"], b["n_dates_incremental"],
                        "%s/%s: a shortfall here would mean MA31/MA32 DID inherit it"
                        % (arm, cell))
                    checked += 1
        self.assertGreaterEqual(checked, 9, "must actually check every arm x cell")

    def test_arm_ic_has_always_reported_both_counts(self):
        """The disclosure existed; MA58 rolled its own residualiser and so lacked it."""
        src = _read(os.path.join(REPO, "valuation", "studies", "surface_stock.py"))
        self.assertIn('"n_dates_raw"', src)
        self.assertIn('"n_dates_incremental"', src)


class TestBoundary(unittest.TestCase):
    def test_this_module_is_research_only(self):
        """It imports an ARCHIVED study, so it must never become reachable from the product."""
        src = _read(os.path.join(REPO, "valuation", "studies", "incremental_ic.py"))
        tree = ast.parse(src)
        bad = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                if "screener" in n.module or "web" in n.module or "saas" in n.module:
                    bad.append(n.module)
        self.assertEqual(bad, [], "the spec module must not reach the live product")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (licensed export absent) - NOT counted as passes:")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
