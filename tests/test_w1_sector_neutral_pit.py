# -*- coding: utf-8 -*-
"""W-1 — the sector-neutral re-run on `S25`'s point-in-time map.

These are TRIPWIRES on the properties that decided the item, not a re-run of it. Each one pins a
defect this register actually hit, or a rule it would have broken silently:

* `K4` FIRED ON ITS FIRST RUN against a correct panel because the arm scored the **nine** bucket
  themes at 0.125 when the deployed composite is **seven** — `MA28`'s C1 defect. The repair was
  `B7`'s: IMPORT `SECTOR-NEUTRAL-B6`'s own constants rather than retype them, so the pin is on the
  import, not on a copied literal.
* The new `sector_at` hook is a PRODUCTION change to `build_fundamental_panel`, so its default
  must be provably inert and the engine must not acquire a dependency on `valuation/edge/`.
* `MB16`: the log carries ONE `W-1` row whose verdict was edited in place. A second row would
  double-charge the trial.
* `M1-PARSE`: a raw `|` anywhere in the prose shifts every column after it, and `\\|` does not help.
"""
from __future__ import annotations

import ast
import io
import os
import unittest

import state_isolation  # noqa: F401  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _tree(*parts):
    return ast.parse(_read(*parts))


class TestTheHookIsInertByDefault(unittest.TestCase):
    """`sector_at=None` must leave the builder bit-identical, and be provably guarded."""

    def test_the_keyword_exists_and_defaults_to_none(self):
        tree = _tree("valuation", "edge", "fundamental_panel.py")
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "build_fundamental_panel")
        names = [a.arg for a in fn.args.kwonlyargs] + [a.arg for a in fn.args.args]
        self.assertIn("sector_at", names, "the opt-in hook is gone")
        # Locate its default and require it to be a literal None. A default of anything else
        # would make every existing caller take the override path without asking for it.
        if "sector_at" in [a.arg for a in fn.args.kwonlyargs]:
            i = [a.arg for a in fn.args.kwonlyargs].index("sector_at")
            default = fn.args.kw_defaults[i]
        else:
            i = [a.arg for a in fn.args.args].index("sector_at")
            j = i - (len(fn.args.args) - len(fn.args.defaults))
            self.assertGreaterEqual(j, 0, "sector_at has no default at all")
            default = fn.args.defaults[j]
        self.assertIsInstance(default, ast.Constant)
        self.assertIsNone(default.value, "sector_at must default to None")

    def test_the_override_is_guarded_on_sector_at_being_supplied(self):
        """The assignment must sit under EXACTLY `if sector_at is not None`, so the default path
        is unreachable rather than merely equal. An unguarded call would raise on every legacy
        caller instead of being inert.

        The node SHAPE is matched, not a substring of the unparsed test — a first cut here asked
        only that `sector_at` and `is not None` both appeared, and a mutation widening the guard
        to `... or True` passed it. That is this record's own substring-ban family, caught by
        mutation rather than by reading, and the repair is to assert the structure.
        """
        tree = _tree("valuation", "edge", "fundamental_panel.py")
        guarded = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            t = node.test
            if not isinstance(t, ast.Compare):          # a BoolOp is NOT this guard
                continue
            if not (isinstance(t.left, ast.Name) and t.left.id == "sector_at"):
                continue
            if len(t.ops) != 1 or not isinstance(t.ops[0], ast.IsNot):
                continue
            rhs = t.comparators[0]
            if not (isinstance(rhs, ast.Constant) and rhs.value is None):
                continue
            body = ast.unparse(node.body)
            if "sector_at(" in body and "sector" in body:
                guarded = True
        self.assertTrue(guarded,
                        "the sector override is not guarded on exactly "
                        "`sector_at is not None`")


    def test_sector_at_is_read_nowhere_outside_its_own_guard(self):
        """The source comment PROMISES this, so it is asserted rather than trusted — a docstring
        claiming a pin that does not exist is the wrong-object family.

        `sector_at` may appear exactly three times in the whole module: the parameter, the guard's
        test, and the call inside it. A fourth reference means the name has leaked into a code
        path the default cannot switch off, and `sector_at=None` would stop being inert.
        """
        tree = _tree("valuation", "edge", "fundamental_panel.py")
        refs = [n for n in ast.walk(tree)
                if isinstance(n, ast.Name) and n.id == "sector_at"]
        args = [a for n in ast.walk(tree) if isinstance(n, ast.arg) and n.arg == "sector_at"
                for a in (n,)]
        self.assertEqual(len(args), 1, "sector_at is declared on more than one function")
        self.assertEqual(len(refs), 2,
                         "sector_at is read %d times outside its declaration; exactly 2 "
                         "(the guard's test and the call it guards) keeps the default inert"
                         % len(refs))


class TestTheEngineDoesNotDependOnTheStudyMap(unittest.TestCase):
    """`S25-REPAIR`'s rule: the map is DUCK-TYPED in, never imported by the engine.

    An engine module importing `valuation/edge/` would put a study-side dependency on the live
    valuation path — the boundary `MA23` exists to hold.
    """

    def test_calibration_does_not_import_the_edge_sector_map(self):
        tree = _tree("valuation", "engine", "calibration.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertNotIn("valuation.edge", a.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn("valuation.edge", node.module,
                                 "engine acquired a study-side dependency")

    def test_the_positive_control_the_guard_is_not_vacuous(self):
        """The guard above passes trivially if `calibration.py` has no imports at all. Require
        that it does import something, so a passing run means the tree was really read."""
        tree = _tree("valuation", "engine", "calibration.py")
        n = sum(1 for x in ast.walk(tree) if isinstance(x, (ast.Import, ast.ImportFrom)))
        self.assertGreater(n, 3, "no imports found — the boundary check would pass vacuously")


class TestTheWeightsAreImportedAndNotRetyped(unittest.TestCase):
    """`K4` fired against a correct panel because nine themes were scored at 0.125 when the
    deployed composite is seven. The fix is `B7`'s and the pin is on the IMPORT."""

    def test_the_arm_imports_b6s_own_constants(self):
        tree = _tree("scripts", "w1_sector_neutral_pit.py")
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(
                    "sector_neutral_rerun"):
                found.update(a.name for a in node.names)
        for name in ("DEPLOYED", "FLAT", "BASE_WEIGHT"):
            self.assertIn(name, found,
                          "%s must be imported from SECTOR-NEUTRAL-B6, never retyped" % name)

    def test_the_deployed_set_is_seven_themes_not_nine(self):
        import sys
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT
        self.assertEqual(len(DEPLOYED), 7,
                         "the deployed composite is SEVEN themes — MA28's C1 defect")
        self.assertAlmostEqual(BASE_WEIGHT, 0.125, places=12)

    def test_no_bare_theme_list_is_retyped_in_the_arm(self):
        """A literal list of nine theme names in the arm source is the defect returning. Read the
        AST rather than grepping, because the docstring names the themes it forbids."""
        tree = _tree("scripts", "w1_sector_neutral_pit.py")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                continue
            strs = [e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            zs = [s for s in strs if s.startswith("z_") or s in (
                "value", "quality", "momentum", "size", "insider", "institutional",
                "capital_discipline", "growth", "low_risk")]
            self.assertLess(len(zs), 7,
                            "a theme list is retyped in the arm: %r" % (zs,))


class TestTheResearchLogRow(unittest.TestCase):
    """`MB16`: one row, verdict edited in place. `M1-PARSE`: no raw pipe in the prose."""

    def _rows(self):
        return [l for l in _read("RESEARCH_LOG.md").split("\n") if l.startswith("| W-1 |")]

    def test_exactly_one_w1_row(self):
        self.assertEqual(len(self._rows()), 1,
                         "a second row double-charges the trial (MB16 — no dedup by id)")

    def test_the_row_has_the_nine_cells_the_parser_expects(self):
        row = self._rows()[0]
        self.assertEqual(row.count("|") - 1, 9,
                         "a raw pipe in the prose shifts every column after it (M1-PARSE)")

    def test_the_verdict_cell_is_no_longer_the_pre_registered_placeholder(self):
        cells = self._rows()[0].split("|")
        self.assertFalse(cells[7].strip().startswith("PRE-REGISTERED"),
                         "the verdict was never written back into the booked row")
        self.assertIn("REJECT", cells[7].upper())

    def test_the_row_charges_two_equity_trials(self):
        cells = self._rows()[0].split("|")
        self.assertEqual(cells[3].strip(), "equity")
        self.assertEqual(cells[8].strip(), "n=2")


class TestTheRegisterIsAStrictAncestor(unittest.TestCase):
    """The register is markdown only and predates every measurement. Checked against the file
    on disk rather than against git, so this suite stays runnable in CI where the worktree may
    be shallow — the git ancestry itself is asserted in the handoff and the commit graph."""

    def test_the_register_exists_and_names_repair_a_as_the_primary(self):
        t = _read("PREREG_w1_sector_neutral_pit.md")
        self.assertIn("REPAIR-A", t)
        self.assertIn("AMENDMENT 1", t,
                      "the correction from the CONFOUNDED arm must stay on the record")

    def test_the_amendment_records_the_k2_bar_the_instrument_could_not_clear(self):
        t = _read("PREREG_w1_sector_neutral_pit.md")
        self.assertIn("13.21", t, "REPAIR-B's bite, the figure the wrong bar came from")
        self.assertIn("4.43", t, "REPAIR-A's own bite, which a 5% bar could not clear")


if __name__ == "__main__":
    unittest.main(verbosity=2)
