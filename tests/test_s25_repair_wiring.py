"""S25's first consumer — the look-ahead repair wired into the valuation path.

WHAT THESE TESTS PIN, and why each is here.

**THE LOAD-BEARING ONE IS THAT A REFUSAL KEEPS THE PANEL'S OWN SECTOR AND NEVER BLANKS IT.**
Both engine dicts FAIL OPEN — `SECTOR_TARGET_MARGIN.get(s, 0.12)` and `SECTOR_MULTIPLES.get(s,
_DEFAULT)` — so blanking an unknown sector does not abstain, it silently hands the row the
middle of a 2.70x range. That is asserted against the REAL dicts, and the consequence is
measured rather than described: a blank moves the target margin by a named amount.

**SECOND: THE PARAMETER IS INERT BY DEFAULT.** Adopting a repair to the live valuation path is
a VINTAGE EVENT, so `sector_map=None` must leave the builder exactly as it was. Pinned two
ways — the signature default, and an AST check that every S25 statement in the builder sits
behind the `is not None` guard.

**THIRD: THE ENGINE MUST NOT IMPORT THE MAP.** `sector_map` lives in `valuation/edge/`, and an
engine module importing it would put a study-side dependency on the live valuation path. The
map is duck-typed in; a test reads the SYNTAX TREE and fails if an import ever appears
(`MA49`: a grep fires against the correct tree, because prose documenting the rule names it).

**FOURTH: THE TWO ARMS ARE DIFFERENT OBJECTS.** REPAIR-A moves only on a reclassification;
REPAIR-B moves wherever the map is covered. The taxonomy-only case — where the map agrees with
itself across time but disagrees with the panel — is what separates them, and it is pinned in
both directions so neither arm can quietly become the other.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.engine import calibration as C  # noqa: E402

_SKIPS = []

CAL_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "valuation", "engine", "calibration.py")


def _map(at_state, at_sector, now_state, now_sector):
    class _M:
        def at(self, t, d):
            return {"state": at_state, "sector": at_sector}

        def current(self, t):
            return {"state": now_state, "sector": now_sector}
    return _M()


class TestARefusalKeepsTheSectorAndNeverBlanks(unittest.TestCase):
    """The property the user's instruction names, and the reason it matters."""

    def test_not_covered_keeps_the_panels_own_sector_in_both_arms(self):
        a, b, state, pit = C.s25_repair_sectors(
            _map("NOT_COVERED", None, "NOT_COVERED", None), "X", "2009-01-15", "Utilities")
        self.assertEqual(a, "Utilities")
        self.assertEqual(b, "Utilities")
        self.assertEqual(state, "NOT_COVERED")
        self.assertIsNone(pit)

    def test_unmapped_ambiguous_and_before_gics_all_keep_it_too(self):
        for st in ("UNMAPPED", "AMBIGUOUS_TICKER", "BEFORE_GICS"):
            a, b, state, _ = C.s25_repair_sectors(
                _map(st, None, st, None), "X", "2001-01-15", "Healthcare")
            self.assertEqual(a, "Healthcare", st)
            self.assertEqual(b, "Healthcare", st)
            self.assertEqual(state, st)

    def test_a_blank_sector_is_a_VOTE_and_this_measures_what_it_would_cost(self):
        # The premise of the rule above, asserted against the real dicts rather than described.
        from valuation.engine.assumptions import SECTOR_TARGET_MARGIN
        from valuation.engine.comps import SECTOR_MULTIPLES, _DEFAULT
        self.assertEqual(SECTOR_TARGET_MARGIN.get("", 0.12), 0.12)
        self.assertEqual(SECTOR_MULTIPLES.get("", _DEFAULT), _DEFAULT)
        # Blanking Technology would move its target margin to the middle of the range.
        tech = SECTOR_TARGET_MARGIN["Technology"]
        self.assertNotAlmostEqual(tech, 0.12)
        lo, hi = min(SECTOR_TARGET_MARGIN.values()), max(SECTOR_TARGET_MARGIN.values())
        self.assertGreater(hi / lo, 2.0)

    def test_the_state_travels_back_so_refusals_can_be_COUNTED(self):
        # A caller must not have to infer a refusal from a gap. O21-D2's C5: absent and
        # empty must not read the same.
        _a, _b, state, _p = C.s25_repair_sectors(
            _map("NOT_COVERED", None, "OK", "Energy"), "X", "2009-01-15", "Energy")
        self.assertEqual(state, "NOT_COVERED")


class TestTheTwoArmsAreDifferentObjects(unittest.TestCase):
    def test_a_reclassification_moves_both_arms(self):
        a, b, _s, _p = C.s25_repair_sectors(
            _map("OK", "Technology", "OK", "Financial Services"),
            "V", "2009-01-15", "Financial Services")
        self.assertEqual(a, "Technology")
        self.assertEqual(b, "Technology")

    def test_taxonomy_only_disagreement_moves_B_and_NOT_A(self):
        # The map agrees with ITSELF across time (no reclassification, so no look-ahead to
        # fix) but disagrees with the panel's vendor. A must not move; B must.
        a, b, _s, _p = C.s25_repair_sectors(
            _map("OK", "Technology", "OK", "Technology"), "X", "2009-01-15", "Industrials")
        self.assertEqual(a, "Industrials", "REPAIR-A must not absorb the taxonomy switch")
        self.assertEqual(b, "Technology")

    def test_no_change_anywhere_leaves_both_alone(self):
        a, b, _s, _p = C.s25_repair_sectors(
            _map("OK", "Energy", "OK", "Energy"), "X", "2009-01-15", "Energy")
        self.assertEqual((a, b), ("Energy", "Energy"))

    def test_A_needs_TODAYS_classification_too_and_refuses_without_it(self):
        # A is defined as a DIFFERENCE between as_of and today. With today unknown there is
        # no difference to measure, so A must not move on the dated value alone.
        a, b, _s, _p = C.s25_repair_sectors(
            _map("OK", "Technology", "NOT_COVERED", None), "X", "2009-01-15", "Industrials")
        self.assertEqual(a, "Industrials")
        self.assertEqual(b, "Technology")


class TestTheParameterIsInertByDefault(unittest.TestCase):
    def test_the_default_is_none(self):
        import inspect
        sig = inspect.signature(C.build_valuation_panel)
        self.assertIn("sector_map", sig.parameters)
        self.assertIsNone(sig.parameters["sector_map"].default)

    def test_every_s25_statement_sits_behind_the_guard(self):
        """Read from the SYNTAX TREE, not grepped: this file's own prose names the columns."""
        tree = ast.parse(io.open(CAL_SRC, encoding="utf-8").read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "build_valuation_panel")
        guards = [n for n in ast.walk(fn)
                  if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                  and isinstance(n.test.left, ast.Name) and n.test.left.id == "sector_map"
                  and any(isinstance(o, ast.IsNot) for o in n.test.ops)]
        self.assertEqual(len(guards), 1, "expected exactly one `sector_map is not None` guard")

        # Every call to the repair rule must sit INSIDE that guard, and there must be
        # exactly one. Compared by node identity, so a second call site anywhere in the
        # function fails even if it looks identical.
        inside = {id(n) for n in ast.walk(guards[0])}
        calls = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "s25_repair_sectors"]
        self.assertEqual(len(calls), 1, "the repair rule must have exactly one call site")
        self.assertIn(id(calls[0]), inside, "the repair rule must run only behind the guard")


class TestTheEngineDoesNotImportTheMap(unittest.TestCase):
    def test_no_import_of_valuation_edge_sector_map_anywhere_in_calibration(self):
        tree = ast.parse(io.open(CAL_SRC, encoding="utf-8").read())
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if "sector_map" in a.name or a.name.startswith("valuation.edge"):
                        bad.append(a.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "sector_map" in mod or mod.startswith("valuation.edge"):
                    bad.append(mod)
                if mod.endswith("edge") or mod == "valuation.edge":
                    bad.append(mod)
        self.assertEqual(bad, [], "calibration.py must duck-type the map, not import it")

    def test_positive_control_the_ast_check_can_actually_see_an_import(self):
        # A guard that cannot fire is not a guard.
        tree = ast.parse("from valuation.edge import sector_map\n")
        found = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertIn("valuation.edge", found)


class TestNothingIsAdopted(unittest.TestCase):
    def test_the_live_config_still_has_no_sector_map(self):
        from valuation.config import CONFIG
        for attr in dir(CONFIG):
            self.assertNotIn("sector_map", attr.lower())

    def test_the_pit_valuation_still_reads_todays_sector_by_default(self):
        """The S25 exposure pin STAYS GREEN and that is correct: measuring a repair is not
        adopting it, and the live path is unchanged until Don says otherwise."""
        src = io.open(CAL_SRC, encoding="utf-8").read()
        self.assertIn('sector=md.get("sector") or ""', src)


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
