"""F-11 — DIP-REJECT PUTS. The screen exists; what did not exist was a caller that kept it.

**A CORRECTION THIS SUITE EXISTS TO PIN.** Audit #5's `H2` repair left `dip_rejects` refusing
every cycle, and the note beside it said no dip screen existed in this repository. **That was
wrong.** `valuation/web/dip.py` runs the screen and publishes `health_check` and
`clamp_drawdown` — the two functions F-11's frozen declaration names. What did not exist was a
caller that KEPT the rejected names: `screen()` counted them as `rejected_health` and discarded
the identities.

**THE DECLARATION IS FROZEN AND THE CODE MATCHES IT, NOT WHAT WAS CONVENIENT.** Two places that
mattered:

  * **`dte_rule` is "nearest above 91", which is NOT nearest-in-absolute-terms.** An 85-DTE
    expiry is closer to 91 than a 98-DTE one and is the wrong side of the declared tenor. The
    one contract picker gained an `expiry_rule` parameter rather than F-11 getting a second
    picker, and the default keeps F-3 and F-8 bit-identical.
  * **`dte_rule` and `right` are READ FROM THE DECLARATION**, not hard-coded here. A rule that
    hard-codes what the declaration states makes the code the authority instead of the frozen
    text.

**THE VOID CONDITIONS ARE PINNED AS TESTS, because they are the book's own kill switches:**
entering HEALTHY dips, re-entry within a quarter, any exit rule, delta-targeting.

**AND THE HONEST LIMIT IS PINNED TOO.** `screen` measures only its SHORTLIST, so the reject
list is bounded by the measurement budget: a name absent from it is *"not measured"*, never
*"healthy"*.
"""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet_books as B   # noqa: E402
from valuation.web import dip as D            # noqa: E402

TODAY = dt.date(2026, 8, 26)


def _row(t, dd, ok=False, price=100.0):
    return {"ticker": t, "drawdown": dd, "price": price,
            "below": [] if ok else ["quality"], "missing": [], "scores": {}}


def _hist(days):
    """`[{date, payload, invalid}]` oldest first, as `fleet_history.read` returns."""
    return [{"date": d, "payload": names, "invalid": bad}
            for d, names, bad in days]


class TestTheScreenExistsAndPublishesTheClassifier(unittest.TestCase):
    def test_the_two_functions_the_declaration_names_are_real(self):
        self.assertTrue(callable(D.health_check))
        self.assertTrue(callable(D.clamp_drawdown))

    def test_a_missing_sub_score_is_not_a_pass(self):
        """The screen's own rule, and F-11 inherits it: a name whose growth could not be
        computed has DECLINED TO ANSWER, it has not demonstrated healthy growth."""
        self.assertFalse(D.health_check({"quality": 90, "health": 90})["ok"])
        self.assertTrue(D.health_check({"quality": 90, "health": 90, "growth": 90})["ok"])


class TestDipRejectsIsTheDeclaredConjunction(unittest.TestCase):
    def test_it_needs_BOTH_deep_enough_AND_failing_health(self):
        payload = {"health_rejects": [_row("DEEP", 0.35), _row("SHALLOW", 0.05)]}
        got = [r["ticker"] for r in D.dip_rejects(payload)]
        self.assertEqual(got, ["DEEP"], "a shallow health-failure is not a dip reject")

    def test_the_threshold_goes_through_clamp_drawdown(self):
        """The book is held to the same CLAMPED value the live screen used, not a literal."""
        payload = {"health_rejects": [_row("A", 0.12)]}
        # 5% is below the floor, so clamp raises it to MIN_DRAWDOWN_FLOOR (0.10) and A clears
        self.assertEqual([r["ticker"] for r in D.dip_rejects(payload, 0.05)], ["A"])
        self.assertEqual(D.dip_rejects(payload, 0.05)[0]["min_drawdown_used"],
                         D.MIN_DRAWDOWN_FLOOR)
        # 40 as a slider value means 0.40, above A's drawdown
        self.assertEqual(D.dip_rejects(payload, 40), [])

    def test_an_unmeasured_drawdown_is_dropped_not_treated_as_shallow(self):
        payload = {"health_rejects": [{"ticker": "X", "drawdown": None}]}
        self.assertEqual(D.dip_rejects(payload), [])

    def test_an_absent_key_yields_nothing_rather_than_raising(self):
        self.assertEqual(D.dip_rejects({}), [])
        self.assertEqual(D.dip_rejects(None), [])

    def test_it_is_deepest_first_and_deterministic(self):
        payload = {"health_rejects": [_row("B", 0.30), _row("A", 0.50), _row("C", 0.30)]}
        self.assertEqual([r["ticker"] for r in D.dip_rejects(payload)], ["A", "B", "C"])


class TestScreenNowKeepsTheRejects(unittest.TestCase):
    """The identities were computed and discarded. Collected, not re-classified."""

    def _rows(self):
        return [{"ticker": "SICK", "price": 10.0}, {"ticker": "WELL", "price": 10.0}]

    def _measure(self, r):
        t = r["ticker"]
        subs = ({"quality": 90, "health": 90, "growth": 90} if t == "WELL"
                else {"quality": 10, "health": 90, "growth": 90})
        return {"drawdown": 0.40, "subs": subs, "checks": {}, "price": 10.0}

    def test_a_health_failure_appears_in_health_rejects_with_its_drawdown(self):
        out = D.screen(self._rows(), min_drawdown=0.20, measure=self._measure)
        names = [r["ticker"] for r in out["health_rejects"]]
        self.assertIn("SICK", names)
        self.assertNotIn("WELL", names)
        self.assertEqual(out["health_rejects"][0]["drawdown"], 0.40)
        self.assertEqual(out["health_rejects"][0]["below"], ["quality"])

    def test_the_count_and_the_list_agree(self):
        out = D.screen(self._rows(), min_drawdown=0.20, measure=self._measure)
        self.assertEqual(out["rejected_health"], len(out["health_rejects"]))

    def test_the_passing_name_still_reaches_rows_unchanged(self):
        out = D.screen(self._rows(), min_drawdown=0.20, measure=self._measure)
        self.assertEqual([r["ticker"] for r in out["rows"]], ["WELL"])


class TestFirstAppearance(unittest.TestCase):
    """F-11's hypothesis. First-ness is only decidable against a DATED history."""

    def test_a_name_first_seen_in_the_last_two_sessions_qualifies(self):
        h = _hist([("2026-08-24", ["OLD"], False),
                   ("2026-08-25", ["OLD", "NEW"], False),
                   ("2026-08-26", ["OLD", "NEW"], False)])
        got = B.f11_first_appearances(h, TODAY, sessions=2)
        self.assertIn("NEW", got)
        self.assertNotIn("OLD", got, "OLD's first appearance was three sessions ago")

    def test_INVALID_ROWS_CANNOT_DATE_A_FIRST_APPEARANCE(self):
        """Audit #5 H2's fabricated span must not make a name look long-standing."""
        h = _hist([("2026-08-25", ["X"], True),        # fabricated, marked invalid
                   ("2026-08-26", ["X"], False)])
        got = B.f11_first_appearances(h, TODAY, sessions=2)
        self.assertEqual(got.get("X"), "2026-08-26",
                         "the invalid row must not count as X's first appearance")

    def test_the_quarter_boundary_resets_it(self):
        h = _hist([("2026-06-30", ["X"], False),       # Q2
                   ("2026-08-26", ["X"], False)])      # Q3
        self.assertEqual(B.f11_first_appearances(h, TODAY, sessions=2).get("X"),
                         "2026-08-26")

    def test_sessions_are_RECORDED_days_not_calendar_days(self):
        """A Friday appearance must not expire over a weekend on which nothing was observed."""
        h = _hist([("2026-08-21", ["FRI"], False), ("2026-08-26", ["FRI"], False)])
        # only two recorded days exist, so the older one is still within 2 sessions
        self.assertIn("FRI", B.f11_first_appearances(h, TODAY, sessions=2))

    def test_no_history_means_no_first_appearances(self):
        self.assertEqual(B.f11_first_appearances([], TODAY), {})


class TestSelection(unittest.TestCase):
    def test_a_name_must_be_on_TODAYS_list_AND_be_a_recent_first_appearance(self):
        """Entering a name that has since recovered off the list would be trading a memory."""
        h = _hist([("2026-08-26", ["A", "GONE"], False)])
        picks = B.f11_select([_row("A", 0.30)], h, TODAY, set(), cap=10)
        self.assertEqual([p["ticker"] for p in picks], ["A"])

    def test_a_held_name_is_skipped_which_is_the_quarter_re_entry_ban(self):
        h = _hist([("2026-08-26", ["A"], False)])
        self.assertEqual(B.f11_select([_row("A", 0.30)], h, TODAY, {"A"}, cap=10), [])

    def test_the_cap_is_applied_to_a_defined_order(self):
        h = _hist([("2026-08-26", ["A", "B", "C"], False)])
        rows = [_row("A", 0.30), _row("B", 0.50), _row("C", 0.40)]
        picks = B.f11_select(rows, h, TODAY, set(), cap=2)
        self.assertEqual([p["ticker"] for p in picks], ["B", "C"], "deepest first")

    def test_it_carries_the_first_appearance_date(self):
        h = _hist([("2026-08-26", ["A"], False)])
        self.assertEqual(B.f11_select([_row("A", 0.30)], h, TODAY, set(),
                                      cap=10)[0]["first_appearance"], "2026-08-26")


class TestTheContractMatchesTheFrozenStructure(unittest.TestCase):
    def _chain(self):
        def c(k, days):
            return {"option_type": "put", "strike": k,
                    "expiration_date": (TODAY + dt.timedelta(days=days)).isoformat(),
                    "symbol": "OCC%s_%s" % (k, days)}
        return [c(80, 85), c(80, 98), c(75, 98), c(85, 98), c(80, 120)]

    def test_nearest_ABOVE_91_is_not_nearest_in_absolute_terms(self):
        """85 DTE is closer to 91 than 98 is, and is the wrong side of the declared tenor."""
        got = B.f3_pick_contract(self._chain(), 100.0, TODAY, moneyness=0.8, dte=91,
                                 expiry_rule="nearest_above")
        self.assertEqual(got["dte"], 98)
        near = B.f3_pick_contract(self._chain(), 100.0, TODAY, moneyness=0.8, dte=91)
        self.assertEqual(near["dte"], 85, "the default rule is unchanged for F-3 and F-8")

    def test_the_strike_is_nearest_to_0_80_x_as_traded_spot(self):
        got = B.f3_pick_contract(self._chain(), 100.0, TODAY, moneyness=0.8, dte=91,
                                 expiry_rule="nearest_above")
        self.assertEqual(got["strike"], 80)
        self.assertEqual(got["target_strike"], 80.0)

    def test_ties_go_to_the_LOWER_strike(self):
        chain = [{"option_type": "put", "strike": 75,
                  "expiration_date": (TODAY + dt.timedelta(days=98)).isoformat(),
                  "symbol": "L"},
                 {"option_type": "put", "strike": 85,
                  "expiration_date": (TODAY + dt.timedelta(days=98)).isoformat(),
                  "symbol": "H"}]
        got = B.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.8, dte=91,
                                 expiry_rule="nearest_above")
        self.assertEqual(got["strike"], 75)

    def test_no_expiry_at_or_beyond_the_tenor_REFUSES(self):
        chain = [{"option_type": "put", "strike": 80,
                  "expiration_date": (TODAY + dt.timedelta(days=30)).isoformat(),
                  "symbol": "S"}]
        self.assertIsNone(B.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.8, dte=91,
                                             expiry_rule="nearest_above"))


class TestVoidConditions(unittest.TestCase):
    """The book's own kill switches, pinned so a later change trips a test rather than a book."""

    def test_a_HEALTHY_dip_can_never_enter(self):
        """That is the V6-OPT corpse's side. `health_rejects` only ever holds failures."""
        rows = [{"ticker": "WELL", "price": 10.0}]

        def measure(r):
            return {"drawdown": 0.5, "subs": {"quality": 90, "health": 90, "growth": 90},
                    "checks": {}, "price": 10.0}
        out = D.screen(rows, min_drawdown=0.20, measure=measure)
        self.assertEqual(out["health_rejects"], [])
        self.assertEqual(D.dip_rejects(out), [])

    def test_no_exit_rule_exists_anywhere_in_the_book(self):
        import inspect
        src = inspect.getsource(B.f11_dip_reject_puts) + inspect.getsource(B.f11_select)
        for banned in ("stop_loss", "take_profit", "target_pct", "stop_pct", "trailing"):
            self.assertNotIn(banned, src, "any exit rule is a VOID condition")

    def test_no_delta_is_solved_or_targeted(self):
        """**CODE ONLY, NEVER PROSE.** The first cut of this test banned the substring and
        FAILED AGAINST THE CORRECT TREE, because both docstrings say "no delta is solved or
        targeted" — a comment documenting the rule quotes the word the rule forbids. That is
        this record's substring-ban family, hit a sixth time, in the test written to honour a
        void condition. It reads the syntax tree instead, and carries a POSITIVE CONTROL so it
        cannot pass by seeing nothing."""
        import ast
        import inspect
        import textwrap

        def _code_names(fn):
            tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
            names = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Name):
                    names.add(n.id.lower())
                elif isinstance(n, ast.Attribute):
                    names.add(n.attr.lower())
                elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                    names.add(n.value.lower())      # a dict key like c["delta"] is code
            return names

        for fn in (B.f11_dip_reject_puts, B.f3_pick_contract):
            hits = [n for n in _code_names(fn) if "delta" in n and len(n) < 40]
            self.assertEqual(hits, [], "delta-targeting is a VOID condition")

        # POSITIVE CONTROL: the check must still catch a real one.
        def _bad(chain):
            return [c for c in chain if c["delta"] < -0.3]
        self.assertTrue([n for n in _code_names(_bad) if "delta" in n],
                        "the AST check cannot see a real delta reference")

    def test_the_strike_comes_from_MONEYNESS_which_is_the_positive_property(self):
        """Banning a word proves nothing on its own; this asserts what the rule DOES."""
        got = B.f3_pick_contract(
            [{"option_type": "put", "strike": 80,
              "expiration_date": (TODAY + dt.timedelta(days=98)).isoformat(),
              "symbol": "X"}],
            100.0, TODAY, moneyness=0.8, dte=91, expiry_rule="nearest_above")
        self.assertEqual(got["target_strike"], 80.0, "0.80 x as-traded spot, not a delta")

    def test_the_rule_refuses_a_right_it_cannot_execute(self):
        decl = {"structure": {"right": "call", "moneyness": 0.8, "dte": 91},
                "concurrency_cap": 10}
        self.assertEqual(B.f11_dip_reject_puts(decl, rejects=[_row("A", 0.3)],
                                               history=[], today=TODAY), [])


class TestTheSourceIsNeverFabricated(unittest.TestCase):
    def test_None_propagates_through_the_ticker_helper(self):
        """`None` (not consulted) and `[]` (ran, found nothing) must stay distinct all the way
        to the recorder -- collapsing them here puts audit #5's fabricated zero straight back."""
        orig = B.f11_live_rejects
        try:
            B.f11_live_rejects = lambda: None
            self.assertIsNone(B.f11_live_rejects_tickers())
            B.f11_live_rejects = lambda: []
            self.assertEqual(B.f11_live_rejects_tickers(), [])
            B.f11_live_rejects = lambda: [_row("A", 0.3), _row("b", 0.4)]
            self.assertEqual(B.f11_live_rejects_tickers(), ["A", "B"])
        finally:
            B.f11_live_rejects = orig

    def test_the_rule_selects_NOBODY_when_the_screen_could_not_be_consulted(self):
        orig = B.f11_live_rejects
        try:
            B.f11_live_rejects = lambda: None
            decl = {"structure": {"right": "put", "moneyness": 0.8, "dte": 91},
                    "concurrency_cap": 10}
            self.assertEqual(B.f11_dip_reject_puts(decl, history=[], today=TODAY), [])
        finally:
            B.f11_live_rejects = orig


class TestItIsRegistered(unittest.TestCase):
    def test_the_book_is_in_the_registry_and_places_orders(self):
        self.assertIn("f11_dip_reject_puts", B.RULES)
        self.assertTrue(B.RULES["f11_dip_reject_puts"][1])

    def test_registration_is_still_an_explicit_call(self):
        reg = B.register_all()
        self.assertIn("f11_dip_reject_puts", str(reg))


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    raise SystemExit(0 if r.wasSuccessful() else 1)
