"""Item 82 — the daily LIVE CHECK failed a correct 81-name book.

`LIVE CHECK` run #31 (2026-10-26 19:32 UTC, run `40387659164`) came back **30 passed, 1 failed,
0 skipped**, and the one failure was:

    FAIL  Index holds 85+ names                        n_positions 81

The 2026-10-22 rebalance formed **81** names, it conforms, and the rebalance door accepted it.
The contract floor is **50** (`CONTRACT_MIN_POSITIONS`). So the checker was asserting the size of
the PREVIOUS book -- 86 names formed 2026-07-30 -- as though that were the rule, and a rebalance
is precisely the event that moves it. It would have fired on both weekday runs until changed,
which is how an alert channel teaches its reader to ignore it (`MA21`).

THE FIX IS THE DOOR'S OWN RULE, CALLED RATHER THAN RESTATED: `valquo_index.conformance`, on the
two inputs `index_mark.append_rebalance` derives -- the position count and the largest weight
normalised by the weights' own sum. Neither 50 nor 8% is typed in the checker, and neither is 81.

These tests drive the REAL `check_index` against synthetic payloads, so they exercise the shipped
function rather than a restatement of it. `scripts/i82_before.py` measures which fail against the
pre-change tree.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import live_check as LC                                    # noqa: E402
from valuation.edge.valquo_index import (CONTRACT_MIN_POSITIONS,   # noqa: E402
                                         MAX_WEIGHT, conformance)

LIVE_CHECK_PY = os.path.join(REPO, "scripts", "live_check.py")


def _book(n, max_w=None, total=1.0):
    """A conforming-shaped payload of `n` equal-weighted names, optionally with one fat name."""
    if n <= 0:
        return {"n_positions": 0, "is_preview": False, "positions": [],
                "card": {"is_tracked_construction": True, "construction": "taxable"}}
    w = total / n
    pos = [{"ticker": "T%03d" % i, "weight": w} for i in range(n)]
    if max_w is not None:
        # One fat name, with the rest sharing what is left, so the weights still sum to `total`.
        rest = (total - max_w) / (n - 1) if n > 1 else 0.0
        pos = [{"ticker": "T000", "weight": max_w}] + \
              [{"ticker": "T%03d" % i, "weight": rest} for i in range(1, n)]
    return {"n_positions": n, "is_preview": False, "positions": pos,
            "card": {"is_tracked_construction": True, "construction": "taxable"}}


class _Harness:
    """Drive the real `check_index` with a payload of our choosing.

    Patches only the two functions that reach outside the process -- the HTTP fetch and the node
    card renderer -- so every line of the verdict logic under test is the shipped one.
    """

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        self._get, self._render = LC.get_json, LC._render_card
        LC.get_json = lambda base, path, **kw: (200, self.payload)
        LC._render_card = lambda d: ""          # renders clean, nothing banned
        self.rep = LC.Report()
        return self

    def __exit__(self, *a):
        LC.get_json, LC._render_card = self._get, self._render
        return False

    def run(self):
        LC.check_index("http://x", self.rep)
        return self.rep

    def line(self, needle):
        return next((ln for ln in self.rep.lines if needle in ln), None)

    def verdict(self, needle):
        ln = self.line(needle)
        return ln.split()[0] if ln else None


class TheBookInForceIsNotEightySix(unittest.TestCase):
    """THE DEFECT. 81 conforming names must pass."""

    def test_todays_eighty_one_name_book_passes(self):
        """FAILS against the pre-change tree, where the rule is `n >= 85`.

        81 names at the live book's own largest weight (0.0196, measured on
        `/api/valquo-index` on 2026-10-26) is exactly what run #31 rejected.
        """
        with _Harness(_book(81, max_w=0.019639)) as h:
            h.run()
            # THE BEHAVIOUR FIRST, AND DELIBERATELY BEFORE THE LABEL. `failed == 0` is what
            # run #31 got wrong and is independent of what the line is called, so this test
            # cannot be satisfied by a rename -- it fails pre-fix because the VERDICT was
            # wrong, not because the wording changed.
            self.assertEqual(h.rep.failed, 0, h.rep.lines)
            self.assertEqual(h.verdict("contract-bound book"), "PASS", h.rep.lines)

    def test_the_old_eighty_six_name_book_still_passes(self):
        """The change must not be a swap of one book's size for another's."""
        with _Harness(_book(86)) as h:
            h.run()
            self.assertEqual(h.verdict("contract-bound book"), "PASS", h.rep.lines)

    def test_every_size_from_the_floor_up_passes_and_below_it_fails(self):
        """The boundary is the CONTRACT's, and it is walked rather than asserted at one point."""
        for n in (CONTRACT_MIN_POSITIONS, CONTRACT_MIN_POSITIONS + 1, 81, 86, 200):
            with _Harness(_book(n)) as h:
                h.run()
                self.assertEqual(h.verdict("contract-bound book"), "PASS", (n, h.rep.lines))
        for n in (CONTRACT_MIN_POSITIONS - 1, 25, 10, 1):
            with _Harness(_book(n)) as h:
                h.run()
                self.assertEqual(h.verdict("contract-bound book"), "FAIL", (n, h.rep.lines))


class ATruncatedBookStillFails(unittest.TestCase):
    """The check must not have been loosened into one that cannot fail."""

    def test_a_book_below_the_contract_floor_fails_and_says_why(self):
        with _Harness(_book(25)) as h:
            h.run()
            ln = h.line("contract-bound book")
            self.assertTrue(ln.startswith("FAIL"), ln)
            self.assertIn("below the contract floor", ln)

    def test_an_empty_book_fails(self):
        with _Harness(_book(0)) as h:
            h.run()
            self.assertEqual(h.verdict("contract-bound book"), "FAIL", h.rep.lines)

    def test_a_runaway_weight_fails_which_the_old_count_could_never_see(self):
        """STRICTLY STRONGER than `n >= 85`: 90 names, one holding 30%.

        The old rule passed this outright. It is the second half of the door's rule and the
        reason the fix is not merely a looser threshold.
        """
        with _Harness(_book(90, max_w=0.30)) as h:
            h.run()
            ln = h.line("contract-bound book")
            self.assertTrue(ln.startswith("FAIL"), ln)
            self.assertIn("cap does not bind", ln)

    def test_a_payload_with_no_numeric_weights_fails_rather_than_certifying_nothing(self):
        """An absent input read as a passing one is how a check comes to check nothing (`C5`)."""
        bad = _book(81)
        for p in bad["positions"]:
            p["weight"] = None
        with _Harness(bad) as h:
            h.run()
            ln = h.line("contract-bound book")
            self.assertTrue(ln.startswith("FAIL"), ln)
            self.assertIn("NO numeric weights", ln)


class OneDefinitionOfTheRule(unittest.TestCase):
    """`B7`. The checker may not carry its own copy of either threshold."""

    @classmethod
    def setUpClass(cls):
        cls.src = io.open(LIVE_CHECK_PY, encoding="utf-8").read()
        cls.tree = ast.parse(cls.src)

    def _check_index_numbers(self):
        fn = next(n for n in ast.walk(self.tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "check_index")
        return [n.value for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                and not isinstance(n.value, bool)]

    def test_check_index_types_neither_threshold_nor_todays_book_size(self):
        """Read off the AST, so a comment quoting a number cannot trip it or hide one.

        85 is the defect. 50 and 0.08 would be the `MA5` family -- a second copy that fixes
        today and breaks at the next change. 81 would be this check re-pointed at today's book
        instead of at the rule.
        """
        nums = self._check_index_numbers()
        for banned in (85, 86, 81, CONTRACT_MIN_POSITIONS, MAX_WEIGHT):
            self.assertNotIn(banned, nums,
                             "check_index must not hard-code %r; it reads the rule" % (banned,))

    def test_it_calls_the_door_s_own_conformance_function(self):
        fn = next(n for n in ast.walk(self.tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "check_index")
        calls = [ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)]
        self.assertIn("VI.conformance", calls, calls)

    def test_the_rule_is_the_one_the_rebalance_door_refuses_on(self):
        """Not "a function with a similar name": the same object, reached the same way."""
        from valuation.screener import index_mark as IM            # noqa: F401
        import inspect
        door = inspect.getsource(IM.append_rebalance)
        self.assertIn("_vi.conformance", door,
                      "the door no longer delegates to conformance; this check is now a "
                      "DIFFERENT rule from the door's and must be re-reconciled")
        self.assertIs(LC.VI.conformance, conformance)

    def test_the_checker_still_adds_no_third_party_dependency(self):
        """RULE 3 is about `pip install`, and the new import is measured against it.

        Not asserted from the import list -- the module is imported here and the loaded set is
        compared with the stdlib's own, so a future top-level `import pandas` in
        `valquo_index.py` turns this red rather than turning a public runner red.
        """
        import importlib
        import sys as _sys
        for m in [k for k in list(_sys.modules) if k.startswith("valuation.edge.valquo_index")]:
            del _sys.modules[m]
        before = set(_sys.modules)
        importlib.import_module("valuation.edge.valquo_index")
        third = sorted(m for m in (set(_sys.modules) - before)
                       if m.split(".")[0] not in _sys.stdlib_module_names
                       and not m.startswith("valuation")
                       and not m.startswith("_"))
        self.assertEqual(third, [], "live_check must stay installable-free: %r" % third)


class NoOtherMonitorCarriesTheOldBookSize(unittest.TestCase):
    """Step 4 of the brief, pinned so it cannot creep back."""

    MONITORS = ("scripts/live_check.py",
                "valuation/screener/rebalance_watch.py",
                "valuation/saas/index_book.py",
                "valuation/screener/index_in_force.py")

    def test_no_monitor_compares_a_position_count_against_a_literal(self):
        """Measured 2026-10-26: `live_check.py:405` was the ONLY such comparison in the tree.

        `index_book.py` mentions 86 twice, both in PROSE recording history ("the published book
        held 86"), which is correct as history and is why this reads the AST rather than
        grepping.
        """
        for rel in self.MONITORS:
            p = os.path.join(REPO, rel)
            if not os.path.exists(p):
                continue
            tree = ast.parse(io.open(p, encoding="utf-8").read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                txt = ast.unparse(node)
                if not any(k in txt for k in ("n_positions", "n_held", "n_book", "len(positions")):
                    continue
                for cmp_ in node.comparators:
                    if (isinstance(cmp_, ast.Constant)
                            and isinstance(cmp_.value, int) and cmp_.value > 1):
                        self.fail("%s compares a position count against the literal %r: %s"
                                  % (rel, cmp_.value, txt))


if __name__ == "__main__":
    unittest.main(verbosity=2)
