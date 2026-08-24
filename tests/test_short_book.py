# -*- coding: utf-8 -*-
"""S3-I3 — the short-book assignment and margin model.

THE TWO TRAPS THE TASK NAMED ARE THE FIRST TWO CLASSES BELOW, and both are the kind that
produce a plausible number rather than an error:

* **as-traded vs adjusted spot at assignment.** A split makes the two bases disagree by the
  split ratio, and the trade still prices either way. The test does not merely assert the
  refusal -- it first proves the two bases reach OPPOSITE verdicts on the same contract, so the
  refusal is demonstrably load-bearing rather than decorative.
* **a worthless-expiry short settles at exactly its intrinsic obligation.** MA36 settles the
  LONG side of that event at -100%. The short's is the mirror and the sign is the whole point.

Every guard below has a non-vacuity companion, because `MB21`'s C1 scored a perfect 0.000e+00
by comparing nothing and `MB15`'s stripper would have passed by seeing nothing.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  MUST precede the valuation imports

from valuation.edge import short_book as SB                                        # noqa: E402
from valuation.edge.csp_surface import settle_put                                  # noqa: E402
from valuation.edge.options_fill import CONTRACT_MULTIPLIER                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "valuation", "edge", "short_book.py")

_SKIPS = []


def _tree():
    with io.open(SRC, encoding="utf-8") as fh:
        return ast.parse(fh.read())


# =========================================================================================== #
# TRAP 1 -- as-traded vs adjusted spot at assignment (U1-SPLIT)
# =========================================================================================== #
class TestSplitTrap(unittest.TestCase):
    """`raw_close` for anything touching a STRIKE, `close` only for a RETURN."""

    # A 4-for-1 split, the NVDA/AAPL shape session 30 measured. The strike is as-traded.
    STRIKE = 280.0
    AS_TRADED_SPOT = 300.0      # finished ABOVE the strike -> a short put expires worthless
    ADJUSTED_SPOT = 75.0        # the same day on the adjusted series -> looks catastrophically ITM

    def test_the_two_bases_reach_opposite_verdicts_so_the_guard_is_load_bearing(self):
        """FIRST prove the trap is real on these numbers; a guard against nothing is nothing."""
        good = SB.assignment_at_expiry(spot_at_expiry=self.AS_TRADED_SPOT, strike=self.STRIKE,
                                       right="put", spot_basis=SB.AS_TRADED)
        self.assertFalse(good["assigned"])
        self.assertEqual(good["intrinsic_obligation"], 0.0)

        # The same call with the adjusted number smuggled in as if it were as-traded. This is
        # what the defect looks like from inside: it computes, it does not raise, it is wrong.
        bad = SB.assignment_at_expiry(spot_at_expiry=self.ADJUSTED_SPOT, strike=self.STRIKE,
                                      right="put", spot_basis=SB.AS_TRADED)
        self.assertTrue(bad["assigned"])
        self.assertAlmostEqual(bad["intrinsic_obligation"], 205.0, places=9)
        # 205 per share on a 280 strike is a 73% loss booked on a trade that never happened.
        self.assertGreater(bad["intrinsic_obligation"] / self.STRIKE, 0.70)

    def test_the_adjusted_basis_is_refused_by_name(self):
        for fn, kw in (
            (SB.assignment_at_expiry, dict(spot_at_expiry=self.ADJUSTED_SPOT,
                                           strike=self.STRIKE, right="put")),
            (SB.early_assignment_flag, dict(spot=self.ADJUSTED_SPOT, strike=self.STRIKE,
                                            right="put", option_bid=1.0)),
        ):
            with self.assertRaises(SB.ShortBookError) as cm:
                fn(spot_basis=SB.ADJUSTED, **kw)
            self.assertIn("U1-SPLIT", str(cm.exception))

    def test_an_undeclared_basis_is_refused_because_omission_is_how_it_happens(self):
        for basis in (None, "", "close", "raw", True):
            with self.assertRaises(SB.ShortBookError):
                SB.assignment_at_expiry(spot_at_expiry=300.0, strike=280.0, right="put",
                                        spot_basis=basis)

    def test_there_is_no_default_basis_anywhere(self):
        """A default is how the adjusted series gets used by accident (MA5's lesson)."""
        checked = 0
        for node in ast.walk(_tree()):
            if not isinstance(node, ast.FunctionDef):
                continue
            names = [a.arg for a in node.args.kwonlyargs]
            if "spot_basis" not in names:
                continue
            checked += 1
            default = node.args.kw_defaults[names.index("spot_basis")]
            self.assertIsNone(default,
                              "%s gives spot_basis a default" % node.name)
        self.assertGreaterEqual(checked, 2, "the walk found no spot_basis argument at all")


# =========================================================================================== #
# TRAP 2 -- a worthless-expiry short settles at exactly its intrinsic obligation
# =========================================================================================== #
class TestWorthlessExpiryIsTheMirrorOfMA36(unittest.TestCase):
    """MA36 posts -100% for a long. For a short the identical event is the best outcome."""

    def test_the_obligation_is_exactly_zero_not_approximately(self):
        for strike, spot in ((100.0, 100.01), (100.0, 250.0), (7.5, 7.51)):
            r = SB.settle_short(strike=strike, credit=2.0, spot_at_expiry=spot, right="put",
                                spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
            self.assertEqual(r["intrinsic_obligation"], 0.0)   # exact, not almost
            self.assertEqual(r["obligation_total"], 0.0)
            self.assertTrue(r["expired_worthless"])
            self.assertFalse(r["assigned"])

    def test_the_full_credit_is_retained_and_the_return_is_positive(self):
        r = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                            spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        self.assertEqual(r["pnl_per_share"], 2.5)
        self.assertEqual(r["pnl_total"], 2.5 * CONTRACT_MULTIPLIER)
        self.assertGreater(r["ret_on_secured"], 0.0)

    def test_it_is_NOT_minus_one_hundred_percent(self):
        """The single line this module exists for. MA36's rule inherited unchanged would make a
        short book's winners read as total losses."""
        r = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                            spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        self.assertNotAlmostEqual(r["ret_on_secured"], -1.0, places=6)
        self.assertAlmostEqual(r["ret_on_secured"], 0.025, places=12)

    def test_a_worthless_short_call_is_the_same_mirror(self):
        r = SB.settle_short(strike=110.0, credit=1.8, spot_at_expiry=100.0, right="call",
                            spot_basis=SB.AS_TRADED, method=SB.COVERED_CALL,
                            underlying_at_entry=100.0)
        self.assertEqual(r["intrinsic_obligation"], 0.0)
        self.assertEqual(r["shares_delta"], 0)       # nothing called away
        self.assertEqual(r["pnl_per_share"], 1.8)

    def test_exactly_at_the_money_owes_exactly_zero_and_is_not_assigned(self):
        """Strict inequality, matching settle_put's `s < k` and MA36's guard."""
        for right in ("put", "call"):
            r = SB.assignment_at_expiry(spot_at_expiry=100.0, strike=100.0, right=right,
                                        spot_basis=SB.AS_TRADED)
            self.assertFalse(r["assigned"], right)
            self.assertEqual(r["intrinsic_obligation"], 0.0)

    def test_an_assigned_short_owes_its_intrinsic_and_the_companion_proves_the_test_bites(self):
        """Non-vacuity: the zero cases above must not be zero for a reason unrelated to expiry."""
        r = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=90.0, right="put",
                            spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        self.assertEqual(r["intrinsic_obligation"], 10.0)
        self.assertEqual(r["pnl_per_share"], -7.5)
        self.assertEqual(r["shares_delta"], CONTRACT_MULTIPLIER)     # a put BUYS stock
        self.assertEqual(r["cash_delta"], -100.0 * CONTRACT_MULTIPLIER)


# =========================================================================================== #
# B7 -- one definition of a settled put
# =========================================================================================== #
class TestB7Fidelity(unittest.TestCase):

    # THE FIRST SIX WERE ALL ROUND NUMBERS AND THAT HID A REAL DEFECT. On values like these,
    # `(pnl * 100) / (k * 100)` happens to equal `pnl / k` bit-for-bit, so the fidelity test
    # passed while the module was doing different arithmetic from `settle_put`. The FIRST REAL
    # ROW of V6-OPT's book -- an untidy strike and a credit with fifteen significant figures --
    # broke it immediately, at the last digit. The messy cases below are the ones that bite, and
    # the lesson generalises: a float identity tested only on round numbers is untested.
    CASES = [(100.0, 2.5, 90.0), (100.0, 2.5, 105.0), (50.0, 1.0, 49.99),
             (280.0, 9.25, 300.0), (7.5, 0.35, 6.0), (1000.0, 40.0, 1000.0),
             (47.5, 1.0499999506641995, 48.529998779296875),      # the row that caught it
             (33.33, 0.4166666666666667, 31.115000000000002),
             (129.87, 3.7300000190734863, 130.0099945068359),
             (6.13, 0.20999999344348907, 5.899999618530273)]

    def test_settle_short_reproduces_settle_put_exactly(self):
        n = 0
        for k, c, s in self.CASES:
            mine = SB.settle_short(strike=k, credit=c, spot_at_expiry=s, right="put",
                                   spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
            ref = settle_put(k, c, s)
            self.assertEqual(mine["assigned"], ref["assigned"])
            self.assertEqual(mine["pnl_per_share"], ref["pnl_per_share"])      # exact
            self.assertEqual(mine["ret_on_secured"], ref["ret_on_strike"])     # exact
            n += 1
        self.assertEqual(n, len(self.CASES))
        self.assertGreater(n, 4, "the comparison ran on too few cases to mean anything")

    def test_the_fidelity_check_is_live_at_call_time_not_only_in_this_file(self):
        """Perturb settle_put and settle_short must REFUSE, proving the in-function assertion is
        not dead code. MB21's C1 is why: a check that cannot fail is not a check."""
        import valuation.edge.short_book as mod
        original = mod.settle_put
        try:
            mod.settle_put = lambda k, c, s: {"assigned": True, "intrinsic_loss": 0.0,
                                              "pnl_per_share": 999.0, "ret_on_strike": 999.0}
            with self.assertRaises(SB.ShortBookError) as cm:
                mod.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                                 spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
            self.assertIn("B7", str(cm.exception))
        finally:
            mod.settle_put = original
        # and the module still works after restoration -- the tamper left nothing behind
        SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                        spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)

    def test_the_return_is_taken_per_share_so_the_identity_is_exact_by_construction(self):
        """The defect the B7 gate caught on real data, pinned so it cannot come back.

        Scaling numerator and denominator by the contract multiplier and then dividing is
        gratuitous arithmetic that loses a bit. `secured_per_share` exists so the ratio is
        literally `pnl / k` for a gross cash-secured put -- the same operation `settle_put`
        performs -- rather than merely equal to it within a tolerance.
        """
        k, c, s = 47.5, 1.0499999506641995, 48.529998779296875
        mine = SB.settle_short(strike=k, credit=c, spot_at_expiry=s, right="put",
                               spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        self.assertEqual(mine["ret_on_secured"], settle_put(k, c, s)["ret_on_strike"])
        # and the scaled form really is different, so the test is not asserting a tautology
        scaled = (mine["pnl_total"]) / (k * CONTRACT_MULTIPLIER)
        self.assertNotEqual(scaled, mine["ret_on_secured"])

    def test_secured_cash_and_secured_per_share_agree_up_to_the_multiplier(self):
        for method, kw in ((SB.CASH_SECURED_PUT, dict(strike=47.5, right="put", credit=1.05)),
                           (SB.CASH_SECURED_PUT_NET, dict(strike=47.5, right="put", credit=1.05)),
                           (SB.COVERED_CALL, dict(strike=110.0, right="call", credit=1.8,
                                                  underlying_at_entry=99.37))):
            for n in (1, 3):
                r = SB.secured_cash(method=method, contracts=n, **kw)
                self.assertAlmostEqual(r["secured_cash"],
                                       r["secured_per_share"] * CONTRACT_MULTIPLIER * n,
                                       places=9)

    def test_the_multiplier_is_imported_and_not_a_third_definition(self):
        """options_fill and options_sizing each define CONTRACT_MULTIPLIER = 100 already; this
        module must not make a third (MA5's four-copies-of-one-idea shape)."""
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("from valuation.edge.options_fill import CONTRACT_MULTIPLIER", src)
        for node in ast.walk(_tree()):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.assertNotEqual(t.id, "CONTRACT_MULTIPLIER",
                                            "a third CONTRACT_MULTIPLIER was defined here")

    def test_o21s_machinery_is_imported_and_never_re_derived(self):
        """`intrinsic` and `exercise_gain` are O21's. Re-typing either is the B7 defect.

        THIS TEST'S FIRST VERSION MISSED ITS OWN MUTATION and the miss is the instructive part:
        it banned the NAME (no local `def intrinsic`) while the defect that actually happens is
        an INLINE re-derivation -- `max(0.0, k - s)` written in place, which defines nothing and
        slipped through untouched. Banning a name is the substring-ban family in a new costume.
        The repair asserts the POSITIVE property instead: O21's functions must be CALLED.
        """
        src = io.open(SRC, encoding="utf-8").read()
        self.assertIn("from valuation.edge import dividends as DIV", src)
        tree = _tree()

        called = set()
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "DIV"):
                called.add(n.func.attr)
        for required in ("intrinsic", "exercise_gain", "dividends_between",
                         "q_trailing", "q_scheduled"):
            self.assertIn(required, called,
                          "DIV.%s is not called; O21's definition has been re-derived or "
                          "dropped" % required)

        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("intrinsic", "exercise_gain", "q_trailing", "q_scheduled",
                       "dividends_between"):
            self.assertNotIn(banned, defined,
                             "%s is O21's and must be imported, not defined here" % banned)
        # non-vacuity: the walk really did find this module's own functions
        self.assertIn("settle_short", defined)
        self.assertIn("early_assignment_flag", defined)

    def test_the_obligation_comes_from_O21_rather_than_arithmetic_written_here(self):
        """The specific call site the mutation attacked, pinned on its own."""
        fn = next(n for n in ast.walk(_tree())
                  if isinstance(n, ast.FunctionDef) and n.name == "assignment_at_expiry")
        uses = [n for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "intrinsic"]
        self.assertEqual(len(uses), 1,
                         "assignment_at_expiry must obtain the obligation from DIV.intrinsic "
                         "exactly once; found %d call sites" % len(uses))


# =========================================================================================== #
# Margin / secured cash -- S3-I1's return denominator
# =========================================================================================== #
class TestSecuredCash(unittest.TestCase):

    def test_the_gross_cash_secured_put_is_the_full_strike(self):
        s = SB.secured_cash(method=SB.CASH_SECURED_PUT, strike=100.0, right="put", credit=2.5)
        self.assertEqual(s["secured_cash"], 100.0 * CONTRACT_MULTIPLIER)
        self.assertFalse(s["credit_netted"])

    def test_the_net_variant_differs_by_exactly_the_credit_and_flatters_the_return(self):
        gross = SB.secured_cash(method=SB.CASH_SECURED_PUT, strike=100.0, right="put", credit=2.5)
        net = SB.secured_cash(method=SB.CASH_SECURED_PUT_NET, strike=100.0, right="put",
                              credit=2.5)
        self.assertEqual(gross["secured_cash"] - net["secured_cash"], 2.5 * CONTRACT_MULTIPLIER)
        a = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                            spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        b = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                            spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT_NET)
        self.assertGreater(b["ret_on_secured"], a["ret_on_secured"])   # it flatters, as stated

    def test_scaling_with_contracts_is_linear_in_both_legs(self):
        one = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=90.0, right="put",
                              spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT, contracts=1)
        five = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=90.0, right="put",
                               spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT, contracts=5)
        self.assertEqual(five["secured_cash"], 5 * one["secured_cash"])
        self.assertEqual(five["pnl_total"], 5 * one["pnl_total"])
        self.assertEqual(five["ret_on_secured"], one["ret_on_secured"])   # a ratio is invariant

    def test_a_naked_short_is_refused_by_name_rather_than_approximated(self):
        with self.assertRaises(SB.ShortBookError) as cm:
            SB.secured_cash(method=SB.NAKED, strike=100.0, right="put", credit=2.5)
        msg = str(cm.exception)
        self.assertIn("4210", msg)
        self.assertIn("UNDERSTATES", msg)      # the direction is stated, not just the refusal

    def test_the_method_must_match_the_right(self):
        with self.assertRaises(SB.ShortBookError):
            SB.secured_cash(method=SB.CASH_SECURED_PUT, strike=100.0, right="call", credit=2.5)
        with self.assertRaises(SB.ShortBookError):
            SB.secured_cash(method=SB.COVERED_CALL, strike=100.0, right="put", credit=2.5,
                            underlying_at_entry=100.0)

    def test_a_covered_calls_pnl_is_labelled_as_the_option_leg_only(self):
        """It looks like a loss exactly when the position did well, so the row says so."""
        cc = SB.settle_short(strike=110.0, credit=1.8, spot_at_expiry=130.0, right="call",
                             spot_basis=SB.AS_TRADED, method=SB.COVERED_CALL,
                             underlying_at_entry=100.0)
        self.assertLess(cc["pnl_per_share"], 0.0)          # the overlay alone reads negative
        self.assertIn("option_leg_only", cc["pnl_scope"])
        csp = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                              spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        self.assertEqual(csp["pnl_scope"], "whole_position")

    def test_a_covered_call_is_secured_by_the_stock_and_needs_its_price(self):
        with self.assertRaises(SB.ShortBookError):
            SB.secured_cash(method=SB.COVERED_CALL, strike=110.0, right="call", credit=1.8)
        s = SB.secured_cash(method=SB.COVERED_CALL, strike=110.0, right="call", credit=1.8,
                            underlying_at_entry=100.0)
        self.assertEqual(s["secured_cash"], 100.0 * CONTRACT_MULTIPLIER)

    def test_a_short_return_on_premium_would_overstate_by_orders_of_magnitude(self):
        """Why S3-I1 makes the secured cash the denominator, shown rather than asserted."""
        r = SB.settle_short(strike=100.0, credit=2.5, spot_at_expiry=105.0, right="put",
                            spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        on_premium = r["pnl_per_share"] / 2.5
        self.assertAlmostEqual(on_premium / r["ret_on_secured"], 40.0, places=9)


# =========================================================================================== #
# Early assignment -- O21's machinery and the right-asymmetry
# =========================================================================================== #
class TestEarlyAssignment(unittest.TestCase):

    DIVS = {"XYZ": [("2026-03-10", 0.75)]}

    def test_the_model_free_trigger_fires_when_exercising_beats_selling(self):
        f = SB.early_assignment_flag(right="call", spot=120.0, strike=100.0, option_bid=18.0,
                                     spot_basis=SB.AS_TRADED)
        self.assertTrue(f["model_free_trigger"])          # intrinsic 20 > bid 18
        self.assertAlmostEqual(f["exercise_gain"], 2.0, places=9)
        self.assertTrue(f["flagged"])

    def test_it_does_not_fire_when_the_bid_is_at_or_above_intrinsic(self):
        f = SB.early_assignment_flag(right="call", spot=120.0, strike=100.0, option_bid=22.0,
                                     spot_basis=SB.AS_TRADED)
        self.assertFalse(f["model_free_trigger"])
        self.assertEqual(f["exercise_gain"], 0.0)
        self.assertFalse(f["flagged"])

    def test_an_itm_short_call_with_an_ex_date_inside_the_window_is_flagged(self):
        f = SB.early_assignment_flag(right="call", spot=120.0, strike=100.0, option_bid=25.0,
                                     spot_basis=SB.AS_TRADED, divs=self.DIVS, ticker="XYZ",
                                     as_of="2026-02-01", expiry="2026-04-17")
        self.assertFalse(f["model_free_trigger"])         # the bid is generous
        self.assertTrue(f["dividend_trigger"])            # but the ex-date carries it
        self.assertTrue(f["flagged"])
        self.assertEqual(f["ex_dates_in_window"], ["2026-03-10"])

    def test_a_short_PUT_is_never_dividend_flagged_because_the_sign_runs_the_other_way(self):
        """A dividend DISCOURAGES early put exercise. Flagging it would be a sign error."""
        f = SB.early_assignment_flag(right="put", spot=80.0, strike=100.0, option_bid=21.0,
                                     spot_basis=SB.AS_TRADED, divs=self.DIVS, ticker="XYZ",
                                     as_of="2026-02-01", expiry="2026-04-17")
        self.assertTrue(f["in_the_money"])
        self.assertEqual(f["ex_dates_in_window"], ["2026-03-10"])   # the dividend IS there
        self.assertFalse(f["dividend_trigger"])                     # and is deliberately not used
        self.assertIn("DISCOURAGES", f["note"])

    def test_an_out_of_the_money_call_is_not_dividend_flagged(self):
        f = SB.early_assignment_flag(right="call", spot=90.0, strike=100.0, option_bid=1.0,
                                     spot_basis=SB.AS_TRADED, divs=self.DIVS, ticker="XYZ",
                                     as_of="2026-02-01", expiry="2026-04-17")
        self.assertFalse(f["dividend_trigger"])
        self.assertFalse(f["flagged"])

    def test_both_yields_are_reported_and_the_secondary_is_labelled_as_O21_requires(self):
        f = SB.early_assignment_flag(right="call", spot=100.0, strike=90.0, option_bid=11.0,
                                     spot_basis=SB.AS_TRADED, divs=self.DIVS, ticker="XYZ",
                                     as_of="2026-04-01", expiry="2026-06-19")
        self.assertIsNotNone(f["q_trailing"])          # ex-date is now in the trailing window
        self.assertIsNotNone(f["q_scheduled"])
        self.assertTrue(f["q_scheduled_is_secondary"])

    def test_no_dividend_table_degrades_to_the_model_free_trigger_and_says_so(self):
        f = SB.early_assignment_flag(right="call", spot=120.0, strike=100.0, option_bid=18.0,
                                     spot_basis=SB.AS_TRADED)
        self.assertEqual(f["ex_dates_in_window"], [])
        self.assertIsNone(f["q_trailing"])
        self.assertTrue(f["flagged"])                  # the model-free half still works


# =========================================================================================== #
# The declaration validator -- S3-I1 section 4's refusal
# =========================================================================================== #
GOOD = {
    "sells_premium": True,
    "assignment_model": "valuation.edge.short_book.assignment_at_expiry",
    "margin_method": SB.CASH_SECURED_PUT,
    "spot_basis": SB.AS_TRADED,
    "early_assignment_flag": "valuation.edge.short_book.early_assignment_flag",
    "return_denominator": "secured_cash",
}


class TestDeclarationValidator(unittest.TestCase):

    def test_a_complete_short_declaration_passes(self):
        r = SB.validate_declaration(dict(GOOD))
        self.assertTrue(r["ok"])
        self.assertTrue(r["short_module_required"])

    # MA13's committed-literal idiom. The first version of the test below iterated
    # `SB.REQUIRED_SHORT_FIELDS` -- i.e. it read the very constant it was supposed to pin -- so
    # deleting a field from the tuple silently deleted its test too. A guard that resolves its
    # expectation from the thing under test cannot detect a change to it.
    EXPECTED_REQUIRED_FIELDS = ("assignment_model", "margin_method", "spot_basis",
                                "early_assignment_flag", "return_denominator")

    def test_the_required_field_list_is_pinned_and_cannot_shrink_silently(self):
        self.assertEqual(tuple(SB.REQUIRED_SHORT_FIELDS), self.EXPECTED_REQUIRED_FIELDS,
                         "the short-book requirement changed; Don's ruling #1 fixes what a "
                         "short declaration must carry, so this literal moves in the same "
                         "commit or not at all")

    def test_a_short_book_missing_ANY_required_field_is_refused(self):
        """S3-I1 section 4's own test, and every field is load-bearing individually."""
        for field in self.EXPECTED_REQUIRED_FIELDS:
            d = dict(GOOD)
            d.pop(field)
            with self.assertRaises(SB.ShortBookError, msg="%s was not required" % field) as cm:
                SB.validate_declaration(d)
            self.assertIn("REFUSED", str(cm.exception))

    def test_a_long_only_book_passes_without_the_module(self):
        r = SB.validate_declaration({"sells_premium": False})
        self.assertTrue(r["ok"])
        self.assertFalse(r["short_module_required"])

    def test_an_absent_sells_premium_is_refused_because_omission_must_not_pass(self):
        with self.assertRaises(SB.ShortBookError) as cm:
            SB.validate_declaration({"margin_method": SB.CASH_SECURED_PUT})
        self.assertIn("sells_premium", str(cm.exception))

    def test_a_naked_declaration_is_refused(self):
        d = dict(GOOD, margin_method=SB.NAKED)
        with self.assertRaises(SB.ShortBookError):
            SB.validate_declaration(d)

    def test_an_adjusted_basis_declaration_is_refused(self):
        d = dict(GOOD, spot_basis=SB.ADJUSTED)
        with self.assertRaises(SB.ShortBookError) as cm:
            SB.validate_declaration(d)
        self.assertIn("U1-SPLIT", str(cm.exception))

    def test_a_return_quoted_on_the_premium_is_refused(self):
        d = dict(GOOD, return_denominator="premium")
        with self.assertRaises(SB.ShortBookError) as cm:
            SB.validate_declaration(d)
        self.assertIn("secured cash", str(cm.exception))

    def test_sells_premium_is_read_as_a_field_and_never_inferred_from_prose(self):
        """A book whose structure string reads oddly must not slip the gate."""
        d = dict(GOOD)
        d["structure"] = "long call 60 DTE"          # contradicts the flag, deliberately
        self.assertTrue(SB.is_short_book(d))          # the FIELD decides, not the prose
        with self.assertRaises(SB.ShortBookError):
            SB.is_short_book({"sells_premium": "yes"})   # a truthy string is not a bool


# =========================================================================================== #
# Refusals that keep the instrument honest
# =========================================================================================== #
class TestRefusals(unittest.TestCase):

    def test_a_missing_expiry_spot_raises_and_is_never_guessed(self):
        with self.assertRaises(SB.ShortBookError) as cm:
            SB.assignment_at_expiry(spot_at_expiry=None, strike=100.0, right="put",
                                    spot_basis=SB.AS_TRADED)
        self.assertIn("flattering", str(cm.exception))

    def test_non_positive_inputs_raise(self):
        for kw in (dict(spot_at_expiry=0.0, strike=100.0), dict(spot_at_expiry=100.0, strike=0.0),
                   dict(spot_at_expiry=-1.0, strike=100.0)):
            with self.assertRaises(SB.ShortBookError):
                SB.assignment_at_expiry(right="put", spot_basis=SB.AS_TRADED, **kw)

    def test_a_negative_credit_raises_because_a_short_receives(self):
        with self.assertRaises(SB.ShortBookError):
            SB.secured_cash(method=SB.CASH_SECURED_PUT, strike=100.0, right="put", credit=-1.0)

    def test_zero_or_negative_contracts_raise(self):
        for n in (0, -1):
            with self.assertRaises(SB.ShortBookError):
                SB.assignment_at_expiry(spot_at_expiry=100.0, strike=90.0, right="put",
                                        spot_basis=SB.AS_TRADED, contracts=n)

    def test_an_unknown_right_raises(self):
        for r in ("straddle", "", None, "cal"):
            with self.assertRaises(SB.ShortBookError):
                SB.assignment_at_expiry(spot_at_expiry=100.0, strike=90.0, right=r,
                                        spot_basis=SB.AS_TRADED)

    def test_no_threshold_shaped_constant_lives_in_the_module(self):
        """I-3's design decision: a library default is exactly how a bar freezes (MA5)."""
        allowed = {0, 1, 0.0}
        offenders, seen = [], 0
        for node in ast.walk(_tree()):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                    and not isinstance(node.value, bool):
                seen += 1
                if node.value not in allowed:
                    offenders.append(node.value)
        self.assertFalse(offenders,
                         "threshold-shaped literals in short_book.py: %s" % offenders)
        # non-vacuity: a scan that finds no constants at all passes by seeing nothing
        self.assertGreater(seen, 5, "the literal scan found only %d constants; it is not "
                                    "reading the module" % seen)


# =========================================================================================== #
# The lane boundary -- this had to live in edge/, and the reason is testable
# =========================================================================================== #
class TestPlacement(unittest.TestCase):

    def test_it_lives_in_edge_because_the_recorder_must_import_it(self):
        """MA23 forbids any non-study module importing valuation.studies. The S3-I1 recorder is
        paper_track lineage, i.e. engine, so a studies/ placement would have been unimportable
        by the one caller that must call it."""
        self.assertTrue(os.path.isfile(SRC))
        self.assertFalse(os.path.exists(
            os.path.join(REPO, "valuation", "studies", "short_book.py")))

    def test_it_imports_no_study(self):
        for node in ast.walk(_tree()):
            mod = None
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
            elif isinstance(node, ast.Import):
                mod = ",".join(a.name for a in node.names)
            if mod and "valuation.studies" in mod:
                self.fail("short_book.py imports a study: %s" % mod)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
