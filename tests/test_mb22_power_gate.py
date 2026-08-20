"""MB22 - the required-n / MDE gate. Register: PREREG_mb22_mb23_power_and_hodrick.md.

WHAT THESE PIN.
  1. The EXTERNAL positive controls: TIDEMARK's charter power table and `POWER_GATE.md`'s own
     published figures, which the ported arithmetic must reproduce.
  2. The INTERNAL ones, which matter more: this project's own three recorded MDEs. If the port
     did not reproduce `S19` +0.020549, `V2G` 1.8708 pp and `V6` +4.177 pp, it would be
     computing a DIFFERENT quantity under a name Valquo already uses.
  3. The two MDE routes are ONE function - exactly equal, not close. Two definitions of one
     quantity is MA5's whole finding.
  4. `critical_value` REFUSES to default. A default is how the Harvey-Liu-Zhu bar froze at 3.0.
  5. `sqrt(2 ln N)` is not re-derived here. A second copy would be MA5's defect inside the
     module that exists to price MA5's lesson.
  6. The module warns about nothing and fails no build - MB30 / MA21's refusal.

Nothing here touches `data/`.
"""
from __future__ import annotations

import ast
import io
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import power_gate as PG            # noqa: E402
from valuation.edge import statistics as ST            # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ExternalControls(unittest.TestCase):
    """TIDEMARK's printed numbers. Read before the code was written, deliberately."""

    def test_reproduces_the_charter_power_table_at_crit_1_96(self):
        """((1.96 + 0.84)/IR)^2 against the values CHARTER.md prints."""
        for ir, printed in ((0.20, 196), (0.30, 87), (0.15, 348)):
            got = PG.required_n(ir, crit=1.96)
            self.assertLess(abs(got - printed), 0.5, f"IR {ir}: {got} vs printed {printed}")

    def test_reproduces_power_gate_s_own_ruling_arithmetic(self):
        """N=66 -> hurdle 2.8947 -> 155.0 independent years at IR 0.30."""
        self.assertAlmostEqual(ST.hlz_hurdle(66), 2.8947, places=4)
        self.assertAlmostEqual(PG.required_n(0.30, n_trials=66), 155.0, places=1)

    def test_reproduces_the_ir_needed_column(self):
        """POWER_GATE.md 3.1 - the refusal read the other way round."""
        for yrs, printed in ((82.3, 0.41), (45.8, 0.55), (25.2, 0.74), (52.4, 0.52)):
            self.assertAlmostEqual(PG.mde_at_power(yrs, n_trials=66), printed, places=2)


class InternalControls(unittest.TestCase):
    """Valquo's OWN recorded MDEs. These are the ones that prove it is the same quantity."""

    def test_reproduces_S19s_minimum_detectable_incremental_IC(self):
        """MA33 derived it as 2*IC/t from an artifact that stored no standard error."""
        got = PG.detection_threshold_from_observed(
            0.012202150018043164, 1.1876022080477582, crit=2.0)
        self.assertAlmostEqual(got, 0.020549, places=6)

    def test_reproduces_V2G_and_V6_exactly(self):
        """crit * se, to the digit. Not 'close' - these are two-figure multiplications."""
        self.assertEqual(PG.detection_threshold(0.9354, crit=2.0), 1.8708)
        self.assertEqual(PG.detection_threshold(2.0885, crit=2.0), 4.177)

    def test_reproduces_V2Gs_own_power_figure_from_the_same_two_numbers(self):
        """V2G printed 55.0% power against a true 1.95pp gap. This is the strongest internal
        control, because V2G computed it independently and by a different route: it is what
        establishes that Valquo's MDE and TIDEMARK's are one quantity at two power levels."""
        self.assertAlmostEqual(PG.power_at(1.95, 0.9354, crit=1.96) * 100, 55.0, places=1)

    def test_the_two_MDE_routes_are_EXACTLY_one_function(self):
        """Not 'agree to tolerance'. Equal. Two definitions of one quantity is MA5's finding."""
        import random
        random.seed(11)
        for _ in range(500):
            e = random.uniform(-5, 5) or 0.1
            t = random.uniform(0.05, 9)
            self.assertEqual(PG.detection_threshold_from_observed(e, t, crit=2.0),
                             PG.detection_threshold(abs(e) / t, crit=2.0))


class TheVocabularyDistinction(unittest.TestCase):
    """The finding MB22 surfaces: Valquo's published MDEs are 50%-power figures."""

    def test_the_detection_threshold_is_a_fifty_percent_power_figure(self):
        """A true effect exactly equal to crit*se is detected half the time (plus the far
        tail, which is why this is 'just above' 0.5 rather than exactly it)."""
        se = 1.3
        thr = PG.detection_threshold(se, crit=2.0)
        p = PG.power_at(thr, se, crit=2.0)
        self.assertGreater(p, 0.50)
        self.assertLess(p, 0.53)

    def test_the_eighty_percent_MDE_is_strictly_larger_and_by_the_stated_ratio(self):
        se = 1.3
        self.assertAlmostEqual(
            PG.detection_threshold(se, crit=2.0) * (2.0 + PG.Z_POWER_CONVENTION) / 2.0,
            (2.0 + PG.Z_POWER_CONVENTION) * se, places=12)
        self.assertAlmostEqual(PG.power_at((2.0 + PG.Z_POWER_CONVENTION) * se, se, crit=2.0),
                               0.80, places=2)

    def test_the_three_published_conversions_are_DERIVED_and_pinned(self):
        """The 80%-power counterparts of this project's three recorded MDEs, as quoted in
        CLAUDE.md, RUN_RULES rule 11 and the ledger.

        Pinned because I got two of the three WRONG by multiplying the rounded 50%-power
        figure by 1.42 instead of deriving from the standard error: +0.029249 for S19 against
        a true +0.029180, and 2.6567pp for V2G against 2.6565pp. Small, and precisely the kind
        of retyped arithmetic MA5 and MA22 exist to stop."""
        z = PG.Z_POWER_CONVENTION
        se19 = 0.012202150018043164 / 1.1876022080477582
        self.assertAlmostEqual((2.0 + z) * se19, 0.029180, places=6)
        self.assertAlmostEqual((2.0 + z) * 0.9354, 2.6565, places=4)
        self.assertAlmostEqual((2.0 + z) * 2.0885, 5.9313, places=4)
        self.assertAlmostEqual((2.0 + z) / 2.0, 1.42, places=10)

    def test_state_prints_BOTH_numbers_so_neither_can_be_picked_by_accident(self):
        s = PG.state(effect=1.95, se=0.9354, crit=2.0)
        self.assertIn("50% power", s)
        self.assertIn("80% power", s)
        self.assertIn("Power against the registered effect", s)


class TheGate(unittest.TestCase):
    def test_the_ambiguity_band_resolves_toward_NOT_PERMITTED(self):
        """RUN_RULES A6 - ambiguous against a pre-committed threshold is a null, and the null
        here is the conservative direction."""
        req = PG.required_n(0.30, n_trials=66)
        self.assertEqual(PG.gate(req * 1.20, 0.30, n_trials=66)["verdict"], "PERMITTED")
        self.assertEqual(PG.gate(req * 1.00, 0.30, n_trials=66)["verdict"],
                         "NULL - NOT PERMITTED")
        self.assertEqual(PG.gate(req * 0.50, 0.30, n_trials=66)["verdict"], "NOT PERMITTED")

    def test_it_reproduces_TIDEMARKs_own_NOT_PERMITTED_ruling(self):
        """The three canonical markets and the pooled figure, all NOT PERMITTED at IR 0.30."""
        for yrs, ratio in ((82.3, 0.53), (45.8, 0.30), (25.2, 0.16), (52.4, 0.34)):
            g = PG.gate(yrs, 0.30, n_trials=66)
            self.assertEqual(g["verdict"], "NOT PERMITTED")
            self.assertAlmostEqual(g["ratio"], ratio, places=2)

    def test_required_n_and_mde_at_power_are_inverses(self):
        for ir in (0.15, 0.2, 0.3, 0.45, 1.1):
            n = PG.required_n(ir, crit=2.0)
            self.assertAlmostEqual(PG.mde_at_power(n, crit=2.0), ir, places=12)


class ItRefusesRatherThanGuesses(unittest.TestCase):
    def test_critical_value_has_NO_default(self):
        """MA5: a default is precisely how the HLZ bar froze at the constant 3.0."""
        with self.assertRaises(ValueError):
            PG.critical_value()
        with self.assertRaises(ValueError):
            PG.critical_value(n_trials=66, crit=2.0)

    def test_a_zero_effect_raises_rather_than_returning_infinity(self):
        with self.assertRaises(ValueError):
            PG.required_n(0.0, crit=2.0)

    def test_nonpositive_samples_and_standard_errors_raise(self):
        for fn, arg in ((PG.mde_at_power, 0), (PG.detection_threshold, 0),
                        (PG.detection_threshold, -1)):
            with self.assertRaises(ValueError):
                fn(arg, crit=2.0)


def _calls(tree):
    """Every called name in a module, dotted. Read from the AST, NEVER grepped.

    A text sweep cannot tell code from prose about code, and this project has now paid for
    that five times - MA5's own guard fired on its own documentation, MA49's fixture failed
    against the FIXED tree because the comment recording the repair quoted the defect
    verbatim, and MA23's stale-import guard was blind to the syntax the codebase writes.
    Both guards below fired on this module's docstrings on their first run; that is the
    sixth instance and it is why they read the tree instead.
    """
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                base = f.value
                out.add(f"{base.id}.{f.attr}" if isinstance(base, ast.Name) else f".{f.attr}")
    return out


class OneDefinitionOnly(unittest.TestCase):
    def _tree(self):
        with io.open(os.path.join(HERE, "valuation", "edge", "power_gate.py"),
                     encoding="utf-8") as fh:
            src = fh.read()
        return src, ast.parse(src)

    def test_the_module_does_not_re_derive_the_hurdle(self):
        """A second sqrt(2 ln N) here would be MA5's defect inside the module that prices it.

        Read as CALLS, not as text: the docstrings legitimately quote the formula, and a grep
        cannot tell the two apart.
        """
        src, tree = self._tree()
        called = _calls(tree)
        self.assertNotIn("math.log", called, "a logarithm is computed here - use hlz_hurdle")
        self.assertNotIn("log", called)
        self.assertIn("from .statistics import hlz_hurdle", src)
        self.assertIn("hlz_hurdle", called, "hlz_hurdle must actually be CALLED, not just "
                                            "imported - an unused import is not delegation")

    def test_hlz_hurdle_is_the_object_actually_called(self):
        """Identity, not a same-shaped reimplementation."""
        for n in (8, 66, 90, 234, 304):
            self.assertEqual(PG.critical_value(n_trials=n), ST.hlz_hurdle(n))

    def test_the_guard_is_not_vacuous(self):
        """Feed it a module that DOES re-derive the hurdle and watch it be caught."""
        bad = _calls(ast.parse("import math\ndef h(n): return math.sqrt(2 * math.log(n))\n"))
        self.assertIn("math.log", bad)


class ItWarnsAboutNothing(unittest.TestCase):
    """MB30 / MA21's refusal, pinned so a later session does not helpfully add a sweep."""

    def test_the_module_performs_no_IO_and_terminates_nothing(self):
        """The real property, and it is stronger than banning a substring: a module that
        opens no file cannot scan the register corpus, and one that calls neither `warn` nor
        `exit` cannot cry wolf. Checked as CALLS - the docstring cites `PREREG_...` by name,
        as project convention requires, and a text sweep flagged exactly that."""
        with io.open(os.path.join(HERE, "valuation", "edge", "power_gate.py"),
                     encoding="utf-8") as fh:
            src = fh.read()
        called = _calls(ast.parse(src))
        for bad in ("open", "glob", "glob.glob", "warnings.warn", "sys.exit", "exit",
                    "print", ".glob", ".read_text", ".rglob"):
            self.assertNotIn(bad, called,
                             f"{bad!r} is called - MB22 ships no check that can cry wolf")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if r.wasSuccessful() else 1)
