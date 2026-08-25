"""O-1 coverage pull — collection discipline, pinned.

The load-bearing test is the first one: the tenors must come from the REGISTER, not from what
the vendor happened to return. Choosing a tenor from the data is the defect `O-1` itself caught
and refused to commit, and a pull is exactly where it would recur unnoticed.
"""
import ast
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "o1_coverage_pull.py")
REGISTER = os.path.join(ROOT, "PREREG_o1_long_puts_accounting_flags.md")


def _mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location("o1pull", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TenorsComeFromTheRegister(unittest.TestCase):
    """`O-1` section 4 fixes 150-210 primary and 330-400 secondary, and section 7's void
    condition 3 forbids reporting the 45-75 band as an arm. A pull that chose its tenor from the
    chain depth the vendor happened to return would be selecting the design on the data."""

    def setUp(self):
        self.m = _mod()
        with open(REGISTER, encoding="utf-8") as fh:
            self.reg = fh.read()

    def test_the_primary_tenor_is_the_registered_one(self):
        self.assertEqual(self.m.PRIMARY_TENOR, (150, 210))
        self.assertIn("150–210 DTE", self.reg)

    def test_the_secondary_tenor_is_the_registered_one(self):
        self.assertEqual(self.m.SECONDARY_TENOR, (330, 400))
        self.assertIn("330–400 DTE", self.reg)

    def test_the_register_still_forbids_the_45_75_band_as_an_arm(self):
        """If the register ever stops saying this, the pull's scope claim is stale and this
        test should fail loudly rather than the scope drifting in silence."""
        self.assertIn("45–75 DTE band is NOT run", self.reg)

    def test_the_45_75_band_is_not_a_constant_in_the_puller(self):
        tree = ast.parse(open(SRC, encoding="utf-8").read())
        nums = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, int)]
        self.assertNotIn(45, nums, "a 45 DTE bound appears in the puller")
        self.assertNotIn(75, nums, "a 75 DTE bound appears in the puller")


class CollectionDoesNotSelect(unittest.TestCase):
    """The pull stores whole chains. Filtering to puts, or to a moneyness band, would bake a
    selection rule into the collection -- and the vendor window closes 2026-09-01, so a rule that
    later moved could not be re-pulled against."""

    def setUp(self):
        self.src = open(SRC, encoding="utf-8").read()
        self.tree = ast.parse(self.src)

    def test_the_stored_frame_is_not_filtered_to_puts(self):
        """`puts` is computed for the manifest COUNT only; the frame written to disk is `df`."""
        fn = next(n for n in ast.walk(self.tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "pull_cell")
        dumped = [n for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "dump"]
        self.assertTrue(dumped, "pull_cell never writes a payload")
        for call in dumped:
            self.assertEqual(getattr(call.args[0], "id", None), "df",
                             "the payload written is not the unfiltered frame")

    #: Selection concepts that must not appear as CODE. Checked as identifiers in the syntax
    #: tree, never as substrings of the source.
    BANNED_IDENTS = ("moneyness", "delta_target", "atm_strike", "pick_contract",
                     "choose_contract", "select_strike")

    @staticmethod
    def _identifiers(tree):
        """Every name the code actually uses. Docstrings and string literals are NOT names, so
        prose describing a rule cannot trip a guard about the rule."""
        got = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name):
                got.add(n.id.lower())
            elif isinstance(n, ast.Attribute):
                got.add(n.attr.lower())
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                got.add(n.name.lower())
            elif isinstance(n, ast.keyword) and n.arg:
                got.add(n.arg.lower())
        return got

    def test_no_moneyness_or_delta_selection_in_the_puller(self):
        """A DEFECT IN THIS TEST'S OWN FIRST CUT, and it is the substring-ban family this project
        has now hit seven times: it banned the SUBSTRING "moneyness" and then fired against the
        CORRECT tree, because the module docstring says the pull does *not* filter to a moneyness
        band. Prose documenting a rule quotes what the rule forbids. Identifiers, not text."""
        idents = self._identifiers(self.tree)
        for word in self.BANNED_IDENTS:
            self.assertNotIn(word, idents, f"the pull performs a selection: {word}")

    def test_the_selection_guard_still_bites(self):
        """The positive control the narrowed rule needs: a module that genuinely selects a strike
        must still be caught, or the repair has simply switched the guard off."""
        bad = ast.parse("def pick_contract(chain, moneyness):\n"
                        "    return chain[chain.moneyness < moneyness]\n")
        idents = self._identifiers(bad)
        hits = [w for w in self.BANNED_IDENTS if w in idents]
        self.assertTrue(hits, "the narrowed guard no longer catches a real selection")

    def test_the_guard_ignores_prose_about_selection(self):
        """The other direction, so the rule is pinned on both sides rather than merely loosened."""
        prose = ast.parse('"""This module does not filter to a moneyness band."""\nX = 1\n')
        self.assertNotIn("moneyness", self._identifiers(prose))

    def test_max_dte_reaches_the_secondary_tenor(self):
        m = _mod()
        self.assertGreaterEqual(m.MAX_DTE, m.SECONDARY_TENOR[1],
                                "chains are truncated below the declared secondary tenor")


class ResumeAndAtomicity(unittest.TestCase):
    def setUp(self):
        self.m = _mod()
        self.tmp = tempfile.TemporaryDirectory()
        self.m.FREEZE = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_torn_final_manifest_line_costs_one_unit_not_the_file(self):
        with open(self.m.manifest_path(), "w", encoding="utf-8") as fh:
            fh.write('{"unit":"flagged|AAA|2020-01-01","status":"ok"}\n')
            fh.write('{"unit":"flagged|BBB|2020-01-01","stat')      # torn by a hard kill
        man = self.m.load_manifest()
        self.assertIn("flagged|AAA|2020-01-01", man)
        self.assertNotIn("flagged|BBB|2020-01-01", man)

    def test_empty_vendor_is_a_distinct_state_from_a_fault(self):
        """'no chain existed' and 'the call broke' must not both read as absence -- one is a
        fact about the vendor and the other is a unit to retry."""
        src = open(SRC, encoding="utf-8").read()
        self.assertIn('"status": "empty_vendor"', src)
        self.assertIn('"status": "fault"', src)

    def test_a_recorded_ok_or_empty_unit_is_not_re_pulled_and_a_fault_is(self):
        src = open(SRC, encoding="utf-8").read()
        self.assertIn('("ok", "empty_vendor")', src,
                      "the resume rule does not distinguish a fault from a completed unit")

    def test_the_replace_retry_gives_up_rather_than_skipping(self):
        """A DEFECT IN THIS TEST'S OWN FIRST CUT, found by mutation and not by reading: it passed
        a nonexistent tmp and asserted "something raises". `os.replace` raises FileNotFoundError
        for that regardless of the retry logic, so the test passed against a `_replace_retry`
        mutated to RETURN instead of raise -- i.e. against a writer that silently skips a unit
        and leaves the manifest calling it complete. The property is: after the last attempt
        still fails, it must RAISE."""
        import unittest.mock as mock
        calls = {"n": 0}

        def always_busy(a, b):
            calls["n"] += 1
            raise PermissionError(32, "being used by another process")

        with mock.patch.object(self.m.os, "replace", always_busy):
            with self.assertRaises(PermissionError):
                self.m._replace_retry("a.tmp", "a.pkl", tries=3)
        self.assertEqual(calls["n"], 3, "it did not use every attempt before giving up")

    def test_the_replace_retry_succeeds_once_the_scanner_lets_go(self):
        """The other direction: a transient hold must NOT become a failure."""
        import unittest.mock as mock
        calls = {"n": 0}

        def busy_then_ok(a, b):
            calls["n"] += 1
            if calls["n"] < 3:
                raise PermissionError(32, "being used by another process")

        with mock.patch.object(self.m.os, "replace", busy_then_ok):
            self.m._replace_retry("a.tmp", "a.pkl", tries=8)
        self.assertEqual(calls["n"], 3)


class FencesAndFreeze(unittest.TestCase):
    def test_the_freeze_is_new_and_not_a_mutation_of_an_existing_one(self):
        m = _mod()
        self.assertIn("freeze_o1_coverage", m.FREEZE)
        for old in ("freeze_options_2026-08-17", "freeze_rawpull_2026-08-18"):
            self.assertNotIn(old, m.FREEZE)

    def test_raw_payload_stays_off_the_checkout(self):
        m = _mod()
        self.assertTrue(m.RAW.upper().startswith("D:"))
        self.assertNotIn("valuation-tool", m.FREEZE)

    def test_the_vendor_start_is_recorded_rather_than_assumed(self):
        """2012-07-17, measured on the panel's own rebalance dates. The handoff's '2016' is this
        project's own STORE start, not the vendor's, and using it would have discarded three
        years of obtainable flagged rows."""
        m = _mod()
        self.assertEqual(str(m.VENDOR_START), "2012-07-17")

    def test_the_pull_charges_no_trials(self):
        m = _mod()
        self.assertEqual(m.census.__module__, m.__name__)
        src = open(SRC, encoding="utf-8").read()
        self.assertIn("ZERO TRIALS", src)
        self.assertIn('"trials": 0', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
