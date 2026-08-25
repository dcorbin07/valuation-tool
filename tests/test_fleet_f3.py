"""F-3 ARMED — bear-scanner puts, and the three places its frozen prose had to be amended.

**THE LAW THESE ENFORCE: the code matches the declaration, not the better rule.** F-3's
selection and contract choice are two PURE functions precisely so the frozen rule can be
pinned without a broker, a network or a market — the live wrapper is plumbing, and plumbing
is not what a pre-registration froze.

  * **NO DEFAULTS ON `n` OR `cap`.** A default is exactly how a pre-committed bar freezes and
    then drifts from the declaration that set it. Pinned by calling without them.
  * **EXPIRY BEFORE STRIKE**, and the fixture is built so the two orders disagree — a test
    where they agree pins nothing.
  * **THE EVENT-SKIP CLAUSE IS INERT BY MEASUREMENT, NOT BY ASSUMPTION.** The scanner's label
    vocabulary is derived from its own source and compared against a COMMITTED LITERAL
    (`MA13`'s idiom). A new label fails this and someone decides; nothing is substring-banned,
    which is the family that fires against correct text.

    python tests/test_fleet_f3.py
"""
from __future__ import annotations

import ast
import datetime as dt
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet_books as FB      # noqa: E402

TODAY = dt.date(2026, 8, 24)


def _row(t, score, labels=(), price=100.0):
    return {"ticker": t, "bear_score": score, "labels_bear": list(labels), "price": price}


def _opt(strike, exp, right="put", sym=None):
    return {"symbol": sym or ("X%s%s" % (exp.replace("-", ""), int(strike))),
            "strike": strike, "option_type": right, "expiration_date": exp,
            "bid": 1.0, "ask": 1.2}


class TheSelection(unittest.TestCase):

    def test_it_takes_the_top_three_by_score(self):
        rows = [_row("AAA", 60), _row("BBB", 90), _row("CCC", 80), _row("DDD", 70)]
        got = [p["ticker"] for p in FB.f3_select(rows, set(), n=3, cap=10)]
        self.assertEqual(got, ["BBB", "CCC", "DDD"])

    def test_ties_break_alphabetically(self):
        """Amendment 1. The score is rounded to one decimal, so ties are ordinary."""
        rows = [_row("ZZZ", 80), _row("AAA", 80), _row("MMM", 80)]
        got = [p["ticker"] for p in FB.f3_select(rows, set(), n=3, cap=10)]
        self.assertEqual(got, ["AAA", "MMM", "ZZZ"])

    def test_a_name_already_held_is_not_re_entered(self):
        rows = [_row("AAA", 90), _row("BBB", 80)]
        got = [p["ticker"] for p in FB.f3_select(rows, {"AAA"}, n=3, cap=10)]
        self.assertEqual(got, ["BBB"])

    def test_the_concurrency_cap_limits_the_take_and_can_reach_zero(self):
        rows = [_row("A%d" % i, 90 - i) for i in range(6)]
        self.assertEqual(len(FB.f3_select(rows, set(), n=3, cap=10)), 3)
        # 8 held against a cap of 10 leaves room for 2, not 3.
        self.assertEqual(len(FB.f3_select(rows, {"H%d" % i for i in range(8)}, n=3, cap=10)), 2)
        self.assertEqual(FB.f3_select(rows, {"H%d" % i for i in range(10)}, n=3, cap=10), [])

    def test_a_name_with_no_bear_score_is_skipped_not_scored_as_zero(self):
        """A missing score is an absent observation. Reading it as 0 would rank a name the
        scanner could not score BELOW every name it could, which is a decision nobody made."""
        rows = [_row("AAA", None), _row("BBB", 10)]
        self.assertEqual([p["ticker"] for p in FB.f3_select(rows, set(), n=3, cap=10)], ["BBB"])

    def test_n_and_cap_have_NO_defaults(self):
        """`MA5`'s measured lesson: a default is how a pre-committed number freezes."""
        with self.assertRaises(TypeError):
            FB.f3_select([], set())
        with self.assertRaises(TypeError):
            FB.f3_select([], set(), n=3)


class TheContractChoice(unittest.TestCase):

    def test_expiry_is_chosen_BEFORE_strike(self):
        """Amendment 2, on a fixture where the two orders DISAGREE.

        The far expiry lists a strike exactly on target; the 60-DTE expiry does not. A
        strike-first rule takes the far month and lets the declared tenor drift, which is the
        parameter this book's theta bleed is measured against.
        """
        near = (TODAY + dt.timedelta(days=60)).isoformat()     # exactly 60 DTE
        far = (TODAY + dt.timedelta(days=200)).isoformat()
        chain = [_opt(80.0, near), _opt(90.0, near), _opt(85.0, far)]
        got = FB.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.85, dte=60)
        self.assertEqual(got["expiration"], near, "tenor must win")
        self.assertEqual(got["strike"], 80.0)
        self.assertEqual(got["target_strike"], 85.0)
        self.assertEqual(got["dte"], 60)

    def test_within_the_chosen_expiry_it_takes_the_strike_nearest_the_target(self):
        exp = (TODAY + dt.timedelta(days=58)).isoformat()
        chain = [_opt(70.0, exp), _opt(84.0, exp), _opt(95.0, exp)]
        got = FB.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.85, dte=60)
        self.assertEqual(got["strike"], 84.0)

    def test_calls_are_never_selected(self):
        exp = (TODAY + dt.timedelta(days=60)).isoformat()
        chain = [_opt(85.0, exp, right="call"), _opt(70.0, exp, right="put")]
        got = FB.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.85, dte=60)
        self.assertEqual(got["strike"], 70.0)
        self.assertEqual(str(got["contract"]["option_type"]), "put")

    def test_no_puts_or_no_spot_returns_None_rather_than_guessing(self):
        exp = (TODAY + dt.timedelta(days=60)).isoformat()
        self.assertIsNone(FB.f3_pick_contract([_opt(85.0, exp, right="call")], 100.0, TODAY,
                                              moneyness=0.85, dte=60))
        self.assertIsNone(FB.f3_pick_contract([], 100.0, TODAY, moneyness=0.85, dte=60))
        self.assertIsNone(FB.f3_pick_contract([_opt(85.0, exp)], None, TODAY,
                                              moneyness=0.85, dte=60))

    def test_the_moneyness_and_dte_come_from_the_DECLARATION(self):
        """Not from this module. Changing the declaration must change the contract."""
        exp60 = (TODAY + dt.timedelta(days=60)).isoformat()
        exp30 = (TODAY + dt.timedelta(days=30)).isoformat()
        chain = [_opt(70.0, exp60), _opt(85.0, exp60), _opt(70.0, exp30), _opt(85.0, exp30)]
        a = FB.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.85, dte=60)
        b = FB.f3_pick_contract(chain, 100.0, TODAY, moneyness=0.70, dte=30)
        self.assertEqual((a["expiration"], a["strike"]), (exp60, 85.0))
        self.assertEqual((b["expiration"], b["strike"]), (exp30, 70.0))


class TheEventClauseIsInertByMeasurement(unittest.TestCase):

    # DERIVED from the two source files below and pinned here as a COMMITTED LITERAL
    # (`MA13`'s idiom: the test holds the comparison, the source holds the fact). A test that
    # re-derived the vocabulary and compared it to itself would pass against any tree.
    VOCABULARY = {
        "Downtrend (<50 & <200 DMA)",
        "Near 52-wk low",
        "Breakdown (lower band)",
        "Death cross",
        "Overbought (RSI {})",
        "MACD bearish cross",
        "Put-heavy flow (P/C {})",
    }

    @staticmethod
    def _labels():
        out = set()
        for f in ("valuation/intraday/bearish.py", "valuation/intraday/signals.py"):
            with io.open(os.path.join(REPO, f), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for n in ast.walk(tree):
                if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "append"):
                    continue
                if "label" not in getattr(n.func.value, "id", ""):
                    continue
                for a in n.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        out.add(a.value)
                    elif isinstance(a, ast.JoinedStr):
                        out.add("".join(v.value if isinstance(v, ast.Constant) else "{}"
                                        for v in a.values))
        return out

    def test_the_scanner_still_emits_exactly_the_labels_this_amendment_was_written_against(self):
        """If this fails the clause may have become LIVE. Decide, do not re-pin blindly."""
        self.assertEqual(self._labels(), self.VOCABULARY)

    def test_none_of_them_is_an_event_label_so_the_skip_clause_never_fires(self):
        self.assertEqual(FB.F3_EVENT_LABELS, ())
        rows = [_row("AAA", 90, labels=sorted(self.VOCABULARY))]
        self.assertEqual([p["ticker"] for p in FB.f3_select(rows, set(), n=3, cap=10)], ["AAA"])

    def test_the_clause_is_WIRED_and_would_bite_if_a_label_ever_qualified(self):
        """A guard that cannot fire is not a guard. Proved on a temporary vocabulary."""
        old = FB.F3_EVENT_LABELS
        try:
            FB.F3_EVENT_LABELS = ("Death cross",)
            rows = [_row("AAA", 90, labels=["Death cross"]), _row("BBB", 10)]
            self.assertEqual([p["ticker"] for p in FB.f3_select(rows, set(), n=3, cap=10)],
                             ["BBB"])
        finally:
            FB.F3_EVENT_LABELS = old


class TheLiveWrapper(unittest.TestCase):

    class Store:
        def load_intraday(self, run_time=None, top=None):
            exp = (TODAY + dt.timedelta(days=60)).isoformat()
            self.exp = exp
            return [{"ticker": "AAA", "detail": {"scores_bear": {"swing": 90.0},
                                                 "labels_bear": ["Death cross"],
                                                 "price": 100.0}},
                    {"ticker": "BBB", "detail": {"scores_bear": {"swing": None},
                                                 "labels_bear": [], "price": 50.0}}]

    class Provider:
        def get_option_chain(self, ticker, dte_range=(45, 75)):
            exp = (TODAY + dt.timedelta(days=60)).isoformat()
            return [_opt(80.0, exp, sym="AAA260ct80"), _opt(95.0, exp, sym="AAA260ct95")]

    class Broker:
        def __init__(self):
            self.placed = []

        def place_option(self, occ, underlying, side, qty, price=None, duration="day"):
            self.placed.append({"occ": occ, "side": side, "qty": qty, "price": price})
            return {"order": {"id": "1"}, "ok": True}

        def order(self, oid):
            return {"id": oid, "status": "filled", "avg_fill_price": 1.2,
                    "exec_quantity": 1, "quantity": 1}

        def cancel(self, oid):
            return {"ok": True}

        def quotes(self, syms):
            return {}

    DECL = {"structure": {"moneyness": 0.85, "dte": 60}, "concurrency_cap": 10}

    def test_it_buys_the_declared_put_on_the_top_scoring_name(self):
        b = self.Broker()
        out = FB.f3_bear_puts(self.DECL, REPO, store=self.Store(), provider=self.Provider(),
                              broker=b, today=TODAY)
        self.assertEqual(len(out), 1, "BBB has no score and must not be entered")
        self.assertEqual(out[0]["symbol"], "AAA")
        self.assertEqual(out[0]["side"], "buy_to_open")
        self.assertEqual(out[0]["qty"], FB.F3_QTY)
        self.assertEqual(out[0]["occ"], "AAA260ct80", "0.85 x 100 = 85, nearest listed is 80")
        self.assertIn(out[0]["arm"], ("A", "B"), "every fleet order carries an F-1 arm")

    def test_a_cap_of_zero_places_nothing_and_does_not_touch_the_broker(self):
        b = self.Broker()
        out = FB.f3_bear_puts({"structure": {"moneyness": 0.85, "dte": 60},
                               "concurrency_cap": 0},
                              REPO, store=self.Store(), provider=self.Provider(),
                              broker=b, today=TODAY)
        self.assertEqual(out, [])
        self.assertEqual(b.placed, [], "no order may reach a broker when the rule selects none")

    def test_the_rule_is_registered_and_PLACES_orders(self):
        FB.register_all()
        from valuation.edge import fleet as F
        self.assertIsNotNone(F.entry_rule("f3_bear_puts"))
        self.assertTrue(F.places_orders("f3_bear_puts"), "F-3 is not a rider")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
