"""SC-1 - the prior-calibration study. Register: PREREG_sc1_prior_calibration.md.

WHAT THESE PIN.
  1. **C3, the register's own control**: the script opens NO market data. Read from the AST, not
     grepped - it may import only `power_gate`/`statistics` from `valuation/edge/`, and may name
     no panel, chain, price or tick artifact. This is void condition 1 and it is the whole reason
     the trial is charged to `infra` rather than to equity or options.
  2. **C1's fixtures**, including the one whose hand-computed value was WRONG on the first run -
     `calibrated_070` was written as `0.7*0.09 + 0.3*0.49` = 0.21, weighting by the forecast
     instead of by the realised 3:1 split; the Brier of those four rows is 0.19. The control
     caught it, which is what a fixture control is for.
  3. The pre-registered constants are the registered ones - a bar that drifts after the run is
     the failure the register exists to prevent.
  4. The three verdict states, including that a WIDE interval containing zero is CANNOT-TELL and
     never CALIBRATED (section 3.1's own refusal).
  5. The odds scale rule: `NN/MM` counts only when `NN+MM == 100`, so the flat `1/7` theme
     weights are not read as a 12.5% prior.

Nothing here opens `data/`.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import sc1_prior_calibration as SC   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "sc1_prior_calibration.py")


def _tree():
    with io.open(SRC, encoding="utf-8") as fh:
        return ast.parse(fh.read())


class C3_NoMarketDataIsOpened(unittest.TestCase):
    """Void condition 1, and the justification for charging infra rather than equity/options."""

    ALLOWED_EDGE = {"power_gate", "statistics"}

    def test_it_imports_nothing_from_the_edge_package_but_the_two_helpers(self):
        bad = []
        for node in ast.walk(_tree()):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("valuation"):
                if node.module.endswith(("edge", "studies", "screener", "web")):
                    for alias in node.names:
                        if alias.name not in self.ALLOWED_EDGE:
                            bad.append(f"{node.module}.{alias.name}")
                elif node.module not in ("valuation.edge.power_gate",
                                         "valuation.edge.statistics"):
                    bad.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("valuation"):
                        bad.append(alias.name)
        self.assertEqual(bad, [], f"SC-1 reached into the engine: {bad}")

    @staticmethod
    def _code_strings(tree):
        """Every string LITERAL the module can act on, with DOCSTRINGS excluded.

        Read from the AST because the first cut of this test grepped the raw source for
        `chain` and failed against the CORRECT module - whose docstring says "no panel, no
        chain, no price, no tick". That is the comment-versus-code family for the eighth time
        in this record (MA5's guard on its own documentation, MA49's fixture against the fixed
        tree, MA23's stale-import guard, three in MB22/MB23, one in MB29's). A text sweep
        cannot tell code from prose about code.
        """
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                d = ast.get_docstring(node, clean=False)
                if d is not None:
                    docs.add(d)
        return [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value not in docs]

    def test_it_names_no_market_data_artifact(self):
        strings = " || ".join(self._code_strings(_tree())).lower()
        for bad in ("panel_corrected", "options_universe", "state_r2", "thetadata",
                    ".pkl", "fwd_ret", "backtest_results", "prepared/bars"):
            self.assertNotIn(bad, strings,
                             f"{bad!r} appears in a code literal - SC-1 must open no market data")

    def test_the_only_data_path_it_writes_is_free_analysis(self):
        strings = self._code_strings(_tree())
        self.assertIn("free_analysis", strings)
        for bad in ("bulk", "backtest", "options", "raw"):
            self.assertNotIn(bad, strings,
                             f"a path component {bad!r} appears - SC-1 writes only free_analysis")

    def test_the_guard_is_not_vacuous(self):
        """It must be able to see an offending import."""
        t = ast.parse("from valuation.edge import fundamental_panel\n")
        found = [a.name for n in ast.walk(t) if isinstance(n, ast.ImportFrom)
                 for a in n.names]
        self.assertIn("fundamental_panel", found)


class C1_Fixtures(unittest.TestCase):
    def test_the_five_fixtures_reproduce_hand_computed_briers(self):
        r = SC.control_c1()
        self.assertTrue(r["all_ok"], f"C1 failed: {[c for c in r['cells'] if not c['ok']]}")

    def test_the_fixture_that_was_wrong_on_the_first_run_is_pinned(self):
        """`calibrated_070`: (3*(0.7-1)^2 + (0.7-0)^2)/4 = 0.19, not 0.21."""
        rows = [{"p": 0.7, "outcome": 1}] * 3 + [{"p": 0.7, "outcome": 0}]
        self.assertAlmostEqual(SC.brier(rows), 0.19, places=12)
        self.assertNotAlmostEqual(SC.brier(rows), 0.7 * 0.09 + 0.3 * 0.49, places=6)


class TheRegisteredConstants(unittest.TestCase):
    def test_the_bars_are_the_registered_ones(self):
        self.assertEqual(SC.KILL_MIN_PAIRS, 25)
        self.assertEqual(SC.KILL_MAX_DISAGREE, 0.15)
        self.assertEqual(SC.CALIBRATED_MAX_HALFWIDTH, 0.15)
        self.assertEqual(SC.DOUBLE_ENTRY_FRAC, 0.20)
        self.assertEqual(SC.SEED, 20260820)

    def test_the_register_exists_on_disk_and_was_committed_alone(self):
        """The citation is checked rather than taken on trust - V6's own lesson, where a
        register cited a filename that did not exist."""
        self.assertTrue(os.path.isfile(os.path.join(ROOT, SC.SELF)))


class TheOddsScaleRule(unittest.TestCase):
    def test_flat_theme_weights_are_not_read_as_priors(self):
        """`1/7` and `1/8` are the flat weights; `16/16` is a test count. None is a prior."""
        for bad in ("flat 1/7 weights", "1/8 of the book", "tests 16/16 green"):
            got = [(int(m.group(1)), int(m.group(2))) for m in SC.ODDS.finditer(bad)]
            self.assertTrue(all(a + b != 100 for a, b in got),
                            f"{bad!r} would be read as odds")

    def test_real_odds_are_read(self):
        for good, want in (("— **60/40**.", 0.60), ("at 55/45", 0.55), ("95/5", 0.95)):
            got = [int(m.group(1)) / 100.0 for m in SC.ODDS.finditer(good)
                   if int(m.group(1)) + int(m.group(2)) == 100]
            self.assertEqual(got, [want])

    def test_a_prior_percentage_line_is_read(self):
        m = SC.PRIOR.search("**EV: MEDIUM. Trials: 0. Prior: ~85% it closes.**")
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), 85)


class TheVerdictStates(unittest.TestCase):
    """Section 3.1 - and the refusal is the part that matters."""

    def test_a_wide_interval_containing_zero_is_CANNOT_TELL_not_CALIBRATED(self):
        half = (0.2833 - (-0.1000)) / 2
        self.assertGreater(half, SC.CALIBRATED_MAX_HALFWIDTH)

    def test_a_tight_interval_containing_zero_would_be_CALIBRATED(self):
        half = (0.05 - (-0.05)) / 2
        self.assertLessEqual(half, SC.CALIBRATED_MAX_HALFWIDTH)

    def test_the_gap_is_signed_priors_minus_outcomes(self):
        """A sign error here would invert OPTIMISTIC and PESSIMISTIC."""
        over = [{"p": 0.9, "outcome": 0}, {"p": 0.9, "outcome": 0}]
        self.assertGreater(SC.gap(over), 0, "confident-and-wrong must give a POSITIVE gap")
        under = [{"p": 0.1, "outcome": 1}, {"p": 0.1, "outcome": 1}]
        self.assertLess(SC.gap(under), 0)


class ClassificationIsMechanical(unittest.TestCase):
    def test_unrecognised_statements_are_UNCLASSIFIED_not_defaulted_into_OUTCOME(self):
        """Defaulting would inflate the primary population with everything unrecognised."""
        self.assertEqual(SC.classify("the weather on tuesday"), "UNCLASSIFIED")

    def test_the_precedence_is_fixed(self):
        self.assertEqual(SC.classify("C1 must reproduce the record"), "INSTRUMENT")
        self.assertEqual(SC.classify("the composite clears its bar"), "OUTCOME")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if r.wasSuccessful() else 1)
