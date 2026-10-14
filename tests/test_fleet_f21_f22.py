"""F-21 and F-22 - what these tests pin, and why each one exists.

Both books are ARMED with a precondition their data cannot yet meet. That is only safe if a
refusal is a RECORD, so most of this file is about the difference between *"nobody qualified"*
and *"the source could not be consulted"*.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **A THIN SOURCE WRITES A NAMED REFUSAL ROW.** If it returned `[]` the book's own stream
   would be indistinguishable from a quiet market, which is the one reading the declaration's
   `arming_precondition` forbids and the reason the harness has `fleet.refuse` at all.
   Asserted on the ROW, in a temp root, not on the return value.

2. **F-22's GATE IS F-21's, ONE IMPLEMENTATION.** Its declaration says the twin refuses
   whenever the arm refuses *"so the twin can never accrue fills the arm had no chance to
   accrue"*. Two copies is exactly how the twin acquires entry opportunities the arm did not
   have - `MB1-SEL`'s confound, which ran twice the size of the effect and in the same
   direction. Pinned from the SYNTAX TREE.

3. **F-22 REFUSES ON ITS UNDECLARED DRAW PARAMETERS RATHER THAN DEFAULTING.** The declaration
   names `F22_SALT` and `p` as *"declared below"* and declares neither. A default `p` of 0
   arms a book that can never fire; any other default makes the code the authority over a
   frozen parameter (`MA5`). Pinned in both directions, so a later amendment that DOES declare
   them is not blocked by this test.

4. **THE DELTA PICKER NEVER APPROXIMATES A MISSING DELTA.** Falling back to moneyness would
   silently run F-3's rule under F-21's name, on exactly the illiquid rows where the two
   differ most, and nothing downstream could tell. Positive control included, or the guard
   passes by rejecting everything.

5. **THE DTE BAND IS HARD.** A chain offering nothing in 30-45 returns `None`, never the
   nearest thing outside it - the declared tenor is what the crash gate's income was measured
   against.

6. **NEITHER BOOK IS RETIRED AND BOTH ARE REGISTERED.** A book built and left out of `RULES`
   reports `ARMED_NO_ENTRY_RULE` forever, which reads as "the work was not done".

    python tests/test_fleet_f21_f22.py
"""
from __future__ import annotations

import ast
import datetime as dt
import inspect
import io
import os
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import fleet as F              # noqa: E402
from valuation.edge import fleet_books as B        # noqa: E402
from valuation.edge import fleet_history as FH     # noqa: E402

TODAY = dt.date(2026, 10, 13)
_SKIPS = []


def _decl(book):
    p = os.path.join(REPO, "DECL_%s.md" % book)
    with io.open(p, encoding="utf-8") as fh:
        return F.parse_declaration(fh.read())["declaration"]


class TestBothBooksAreArmed(unittest.TestCase):
    """(6)."""

    def test_both_are_in_RULES_and_place_orders(self):
        for b in ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin"):
            self.assertIn(b, B.RULES)
            self.assertTrue(B.RULES[b][1], "%s sells a put; it places orders" % b)

    def test_register_all_registers_them(self):
        got = B.register_all()
        for b in ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin"):
            self.assertIn(b, got["registered"])
            self.assertIsNotNone(F.entry_rule(b))

    def test_the_declarations_are_valid_once_s3i3_is_registered(self):
        from valuation.edge import assignment as A
        A.register()
        for b in ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin"):
            v = F.validate_declaration(_decl(b))
            self.assertTrue(v["ok"], "%s: %s" % (b, v["refusals"]))


class TestAThinSourceIsRecordedAsARefusal(unittest.TestCase):
    """(1). The whole reason arming now is safe."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def _rows_of(self, book):
        return (F.read_records(book, self.root) or {}).get("rows") or []

    def test_a_thin_series_writes_a_named_refusal_row_and_not_an_empty_day(self):
        FH.record_dip_healthy(date="2026-10-01", healthy=["AAA"], root=self.root)
        rows, why = B._f21_source_gate("f21_v6opt_dip_csp", _decl("f21_v6opt_dip_csp"),
                                       self.root, TODAY)
        self.assertIsNone(rows)
        self.assertIn("SOURCE TOO THIN", why)
        recs = [r for r in self._rows_of("f21_v6opt_dip_csp")
                if str(r.get("kind")) == "refusal"]
        self.assertTrue(recs, "a refusal must be a RECORD, not a silent empty return")
        self.assertEqual(str(recs[-1].get("refusal_code")), "DIP_HEALTHY_UNFIT")

    def test_an_absent_stream_is_NOT_CONSULTED_and_says_so_by_a_different_code(self):
        rows, why = B._f21_source_gate("f21_v6opt_dip_csp", _decl("f21_v6opt_dip_csp"),
                                       self.root, TODAY)
        self.assertIsNone(rows)
        self.assertIn("NOT CONSULTED", why)
        recs = [r for r in self._rows_of("f21_v6opt_dip_csp")
                if str(r.get("kind")) == "refusal"]
        self.assertTrue(recs)
        self.assertEqual(str(recs[-1].get("refusal_code")), "DIP_HEALTHY_ABSENT",
                         "an absent stream and a thin one are different facts and a "
                         "hard-coded single refusal could not tell them apart (E-1)")

    def test_positive_control_a_fit_series_passes_the_gate_and_records_nothing(self):
        for i in range(1, 25):
            FH.record_dip_healthy(date="2026-10-%02d" % i, healthy=["AAA"], root=self.root)
        rows, why = B._f21_source_gate("f21_v6opt_dip_csp", _decl("f21_v6opt_dip_csp"),
                                       self.root, dt.date(2026, 10, 25))
        self.assertIsNotNone(rows, why)
        self.assertIsNone(why)
        self.assertFalse([r for r in self._rows_of("f21_v6opt_dip_csp")
                          if str(r.get("kind")) == "refusal"],
                         "a passing gate must not write a refusal, or the stream fills with "
                         "noise and the real ones stop being read")


class TestTheTwinSharesTheArmsGate(unittest.TestCase):
    """(2). From the syntax tree."""

    def test_f22_calls_the_same_source_gate_function_as_f21(self):
        for fn in (B.f21_v6opt_dip_csp, B.f22_dip_csp_random_twin):
            src = textwrap.dedent(inspect.getsource(fn))
            calls = {n.func.id for n in ast.walk(ast.parse(src))
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            self.assertIn("_f21_source_gate", calls,
                          "%s must share the arm's gate, not carry a copy" % fn.__name__)

    def test_there_is_exactly_one_implementation_of_the_gate(self):
        with io.open(os.path.join(REPO, "valuation", "edge", "fleet_books.py"),
                     encoding="utf-8") as fh:
            src = fh.read()
        n = sum(1 for d in ast.walk(ast.parse(src))
                if isinstance(d, ast.FunctionDef) and d.name == "_f21_source_gate")
        self.assertEqual(n, 1)


class TestTheUndeclaredDrawParameters(unittest.TestCase):
    """(3). Both directions, so a later amendment is not blocked by this test."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for i in range(1, 25):
            FH.record_dip_healthy(date="2026-10-%02d" % i, healthy=["AAA", "BBB"],
                                  root=self.root)
        self.hist = (FH.read("dip_healthy", self.root) or {}).get("rows") or []

    def test_the_declaration_still_does_not_declare_p_or_the_salt(self):
        st = _decl("f22_dip_csp_random_twin").get("structure") or {}
        self.assertNotIn("draw_probability", st)
        self.assertNotIn("salt", st)
        self.assertIn("p is the threshold declared below",
                      str((_decl("f22_dip_csp_random_twin") or {}).get("entry_rule") or ""),
                      "this test exists because the declaration promises a value it never "
                      "gives; if that is amended, amend this test in the same commit")

    def test_it_refuses_by_name_rather_than_drawing_at_p_equals_zero(self):
        from valuation.edge import assignment as A
        A.register()
        out = B.f22_dip_csp_random_twin(_decl("f22_dip_csp_random_twin"), self.root,
                                        today=dt.date(2026, 10, 25), history=self.hist)
        self.assertEqual(out, [])
        recs = [r for r in ((F.read_records("f22_dip_csp_random_twin", self.root) or {})
                            .get("rows") or []) if str(r.get("kind")) == "refusal"]
        self.assertTrue(recs, "a book that cannot draw must say so on its own stream")
        self.assertEqual(str(recs[-1].get("refusal_code")), "DRAW_PARAMS_UNDECLARED")

    def test_positive_control_the_draw_itself_works_when_given_parameters(self):
        # f22_draws is pure and is NOT what refuses; proving it works isolates the refusal
        # to the missing declaration rather than to a broken draw.
        got = B.f22_draws(["AAA", "BBB", "CCC"], "2026-10-13", salt="s", p=1.0)
        self.assertEqual(got, ["AAA", "BBB", "CCC"])
        self.assertEqual(B.f22_draws(["AAA", "BBB"], "2026-10-13", salt="s", p=0.0), [])


class TestTheDeltaPicker(unittest.TestCase):
    """(4) and (5)."""

    @staticmethod
    def _c(sym, strike, exp, delta, kind="put"):
        row = {"symbol": sym, "strike": strike, "expiration_date": exp,
               "option_type": kind}
        if delta is not None:
            row["greeks"] = {"delta": delta}
        return row

    def test_it_picks_the_put_nearest_the_target_delta(self):
        exp = "2026-11-17"            # 35 days from 2026-10-13
        chain = [self._c("A", 90, exp, -0.10), self._c("B", 95, exp, -0.26),
                 self._c("C", 100, exp, -0.48)]
        got = B.pick_by_delta(chain, TODAY, target=0.25, dte=37, dte_lo=30, dte_hi=45)
        self.assertEqual(got["contract"]["symbol"], "B")

    def test_a_row_with_no_delta_is_skipped_and_never_approximated(self):
        exp = "2026-11-17"
        chain = [self._c("NODELTA", 95, exp, None), self._c("HAS", 90, exp, -0.44)]
        got = B.pick_by_delta(chain, TODAY, target=0.25, dte=37, dte_lo=30, dte_hi=45)
        self.assertEqual(got["contract"]["symbol"], "HAS",
                         "the nearer strike has no delta; approximating it from moneyness "
                         "would run F-3's rule under F-21's name")

    def test_a_chain_with_no_deltas_at_all_returns_None(self):
        exp = "2026-11-17"
        chain = [self._c("X", 95, exp, None), self._c("Y", 90, exp, None)]
        self.assertIsNone(B.pick_by_delta(chain, TODAY, target=0.25, dte=37,
                                          dte_lo=30, dte_hi=45))

    def test_the_dte_band_is_hard(self):
        near = self._c("NEAR", 95, "2026-10-20", -0.25)      # 7 days
        far = self._c("FAR", 95, "2027-03-19", -0.25)        # ~157 days
        self.assertIsNone(B.pick_by_delta([near, far], TODAY, target=0.25, dte=37,
                                          dte_lo=30, dte_hi=45),
                          "nothing inside 30-45 means no trade, not the nearest thing "
                          "outside it")

    def test_calls_are_never_picked(self):
        exp = "2026-11-17"
        chain = [self._c("CALL", 95, exp, 0.25, kind="call")]
        self.assertIsNone(B.pick_by_delta(chain, TODAY, target=0.25, dte=37,
                                          dte_lo=30, dte_hi=45))

    def test_expiry_is_chosen_before_delta(self):
        a = self._c("CLOSE_EXP_FAR_DELTA", 90, "2026-11-17", -0.40)   # 35d
        b = self._c("FAR_EXP_CLOSE_DELTA", 95, "2026-11-13", -0.25)   # 31d
        got = B.pick_by_delta([a, b], TODAY, target=0.25, dte=37, dte_lo=30, dte_hi=45)
        self.assertEqual(got["contract"]["symbol"], "CLOSE_EXP_FAR_DELTA",
                         "the declared tenor is what the crash gate's income was measured "
                         "against, so expiry wins the tie-break")


class TestTheQuarantineCommentIsNoLongerFalse(unittest.TestCase):
    """The stale comment that nearly cost a session its conclusion about the short half."""

    def test_assignments_closure_reaches_no_archived_module(self):
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import import_graph
        import test_ma59_quarantine as Q
        g = import_graph.graph()
        seen, stack = set(), ["valuation/edge/assignment.py"]
        while stack:
            m = stack.pop()
            if m in seen:
                continue
            seen.add(m)
            stack.extend(g.get(m, ()))
        self.assertFalse(sorted(seen & set(Q.ARCHIVED)))
        self.assertIn("valuation/edge/dividends.py", seen,
                      "positive control: the closure really does reach dividends, which is "
                      "why the old comment sounded right")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
