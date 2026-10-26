"""Item 83 — the paper account borrowed on the rebalance. A buy may never spend more than cash.

WHAT HAPPENED, measured from the two cycles' own saved bodies rather than reasoned about:

  * the paper account's `multiplier` is **4.0** -- it is a margin account;
  * the 17:30Z cycle sized a buy budget of **$50,060.26** from `non_marginable_buying_power`
    and the 17:46Z cycle **$41,831.33**, both from that same field;
  * the second cycle bought the whole **$12,603.48** remaining gap while **38 orders from the
    first cycle were still resting**;
  * the account finished at `cash` **-$4,759.68** on `equity` $100,220.70 -- about **4.75%
    borrowed** -- and the arithmetic closes: spending $12,603.48 and landing at -$4,759.68
    implies about **+$7,844** of cash when a $41,831.33 budget was handed out.

THE PREMISE THAT FAILED IS THE FIELD'S NAME. `non_marginable_buying_power` is buying power for
securities that cannot be MARGINED; it is not the cash on hand. Alpaca's own documented sample
account reads `cash` **-23,140.20** with `non_marginable_buying_power` **+7,386.56** at
`multiplier` 4 -- a positive "no-borrow" figure on an account thousands of dollars overdrawn.

THE RULE NOW: the budget is `cash`, less the cash already committed to open buy orders, and a
negative cash reads as zero. No buying-power field is consulted for the amount at any
multiplier. One definition, in `settlement.py`.
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

from valuation.edge import live_cycle as LC        # noqa: E402
from valuation.edge import settlement as SETTLE    # noqa: E402

#: **ALPACA'S OWN DOCUMENTED SAMPLE ACCOUNT**, from the account-plans page, and the whole reason
#: this item exists: a POSITIVE `non_marginable_buying_power` on an account whose cash is
#: thousands of dollars negative. A committed literal (`MA13`) -- if a future reader doubts the
#: premise, this is the vendor's own number to check it against.
ALPACA_DOC_SAMPLE = {"cash": "-23140.20", "non_marginable_buying_power": "7386.56",
                     "buying_power": "92560.80", "regt_buying_power": "92560.80",
                     "multiplier": "4", "equity": "100000.00"}

#: THE PAPER ACCOUNT AS THE 17:46Z CYCLE FOUND IT. `cash` is derived, not observed -- the saved
#: body recorded the budget and NOT the balances behind it, which is its own finding and is
#: fixed by `account_figures`. The derivation: it spent 12,603.48 and ended at -4,759.68.
PAPER_1746Z = {"cash": "7843.80", "non_marginable_buying_power": "41831.33",
               "buying_power": "267096.84", "multiplier": "4", "equity": "100220.70"}


class TheDocumentedSampleMustBudgetZero(unittest.TestCase):
    """The brief's own required case."""

    def test_alpacas_sample_account_budgets_ZERO_not_7386_56(self):
        got = SETTLE.spendable(ALPACA_DOC_SAMPLE)
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["amount"], 0.0, got)
        self.assertNotEqual(got["amount"], 7386.56)

    def test_a_negative_cash_balance_reads_as_zero_rather_than_as_a_negative_budget(self):
        """An overdrawn account buys nothing, and cannot deepen the debit."""
        got = SETTLE.spendable({"cash": "-4759.68", "multiplier": "4"})
        self.assertEqual(got["amount"], 0.0, got)
        self.assertTrue(got["ok"], "zero is a real answer, not a broken input")

    def test_a_multiplier_one_account_where_the_two_fields_agree(self):
        """The brief's second required case. At multiplier 1 nothing is levered and the answer
        is the same either way -- so the change cannot be a loss of function on a cash account."""
        a = {"cash": "1000.00", "non_marginable_buying_power": "1000.00",
             "buying_power": "1000.00", "multiplier": "1"}
        got = SETTLE.spendable(a)
        self.assertEqual((got["ok"], got["amount"], got["field"]), (True, 1000.0, "cash"))

    def test_the_real_event_would_have_been_bounded_at_cash(self):
        """THE REGRESSION. The budget that produced the debit, against the rule that prevents it.

        $41,831.33 was handed out; cash was about $7,843.80. The cycle spent $12,603.48, which
        is $4,759.68 more than cash -- the debit Don saw, to the cent.
        """
        got = SETTLE.spendable(PAPER_1746Z)
        self.assertEqual(got["amount"], 7843.80, got)
        self.assertLess(got["amount"], 12603.48,
                        "the budget must be below what the cycle actually spent")
        self.assertLess(got["amount"], 41831.33)


class OpenBuysAreCashAlreadySpokenFor(unittest.TestCase):
    """`cash` does not fall when an order is placed, only when it fills."""

    def test_an_open_buy_is_subtracted_from_the_budget(self):
        resting = [{"ticker": "AAA", "side": "buy", "qty_open": 10.0, "limit_price": 100.0}]
        res = SETTLE.open_buy_value(resting)
        self.assertEqual((res["ok"], res["amount"], res["n"]), (True, 1000.0, 1))
        got = SETTLE.spendable({"cash": "2500.00"}, reserved=res)
        self.assertEqual(got["amount"], 1500.0, got)
        self.assertIn("open buy", got["field"])

    def test_open_SELLS_are_not_reserved_because_a_sell_releases_cash(self):
        resting = [{"ticker": "AAA", "side": "sell", "qty_open": 10.0, "limit_price": 100.0}]
        self.assertEqual(SETTLE.open_buy_value(resting)["amount"], 0.0)
        self.assertEqual(SETTLE.spendable({"cash": "2500.00"},
                                          reserved=SETTLE.open_buy_value(resting))["amount"],
                         2500.0)

    def test_reserving_more_than_cash_gives_zero_and_not_a_negative_budget(self):
        resting = [{"ticker": "AAA", "side": "buy", "qty_open": 100.0, "limit_price": 100.0}]
        got = SETTLE.spendable({"cash": "2500.00"},
                               reserved=SETTLE.open_buy_value(resting))
        self.assertEqual(got["amount"], 0.0, got)

    def test_an_open_buy_it_cannot_VALUE_refuses_rather_than_counting_it_as_zero(self):
        """`MA6`'s refusing direction. Reading an unvaluable order as $0 is the direction that
        borrows, and it is the call `live_slots.order_plan` already makes for the quantity."""
        for bad in ({"ticker": "AAA", "side": "buy", "qty_open": None, "limit_price": 100.0},
                    {"ticker": "AAA", "side": "buy", "qty_open": 10.0, "limit_price": None},
                    {"ticker": "AAA", "side": "buy", "qty_open": 10.0, "limit_price": 0.0}):
            res = SETTLE.open_buy_value([bad])
            self.assertFalse(res["ok"], res)
            self.assertIn("AAA", res["unpriced"])
            got = SETTLE.spendable({"cash": "2500.00"}, reserved=res)
            self.assertFalse(got["ok"], got)
            self.assertIsNone(got["amount"])

    def test_nothing_open_is_not_a_refusal(self):
        res = SETTLE.open_buy_value([])
        self.assertTrue(res["ok"])
        self.assertEqual(res["amount"], 0.0)
        self.assertEqual(SETTLE.spendable({"cash": "40.00"}, reserved=res)["amount"], 40.0)

    def test_a_bare_number_is_accepted_as_a_reservation(self):
        self.assertEqual(SETTLE.spendable({"cash": "100.00"}, reserved=25.0)["amount"], 75.0)
        self.assertEqual(SETTLE.spendable({"cash": "100.00"}, reserved=None)["amount"], 100.0)
        # A NEGATIVE reservation cannot widen the budget.
        self.assertEqual(SETTLE.spendable({"cash": "100.00"}, reserved=-500.0)["amount"], 100.0)


class NoLeveredFieldCanMoveTheAnswer(unittest.TestCase):
    """The property, asserted as invariance rather than as a field name."""

    def test_inflating_every_buying_power_field_cannot_widen_the_budget(self):
        base = SETTLE.spendable({"cash": "100.00", "multiplier": "1"})["amount"]
        fat = {"cash": "100.00", "multiplier": "4", "buying_power": "9e9",
               "regt_buying_power": "9e9", "daytrading_buying_power": "9e9",
               "non_marginable_buying_power": "9e9"}
        self.assertEqual(SETTLE.spendable(fat)["amount"], base)

    def test_an_absent_cash_balance_refuses_and_does_not_fall_back_to_buying_power(self):
        """`C5`: an unreported balance is not a measured zero, and no levered field stands in."""
        got = SETTLE.spendable({"equity": "1000", "non_marginable_buying_power": "50000",
                                "buying_power": "200000", "multiplier": "4"})
        self.assertFalse(got["ok"], got)
        self.assertIsNone(got["amount"])

    def test_the_figures_behind_the_budget_are_RECORDED(self):
        """The 2026-10-26 bodies saved the amount, the field and the multiplier and NOT the
        balances -- so nobody could tell from the record whether a budget had exceeded cash."""
        got = SETTLE.spendable(PAPER_1746Z)
        fig = got.get("account_figures") or {}
        self.assertEqual(fig.get("cash"), 7843.80)
        self.assertEqual(fig.get("non_marginable_buying_power"), 41831.33)
        self.assertEqual(fig.get("multiplier"), 4.0)
        for f in SETTLE.LEVERED_FIELDS:
            self.assertIn(f, fig, "every refused field is recorded, so a reader can check it")

    def test_settlement_is_the_only_module_that_sizes_from_an_account_field(self):
        """The existing AST guard lives in `tests/test_item67.py` and must still hold.

        Run here too, narrowly: no module on the live path may name a buying-power key outside
        `settlement.py` and the two read-only reports. Item 67 proves it over the whole tree;
        this asserts that item 83 did not add one.
        """
        from valuation.edge import live_slots as LS
        for mod in (LC, LS):
            src = io.open(mod.__file__, encoding="utf-8").read()
            tree = ast.parse(src)
            prose = {id(n.value) for n in ast.walk(tree)
                     if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
            allowed = set()
            for node in ast.walk(tree):
                if (isinstance(node, ast.FunctionDef)
                        and node.name in ("account_report", "account_settlement_report")):
                    for inner in ast.walk(node):
                        if hasattr(inner, "lineno"):
                            allowed.add(inner.lineno)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in prose and "buying_power" in node.value
                        and node.lineno not in allowed):
                    self.fail("%s:%d names %r outside settlement.py"
                              % (os.path.basename(mod.__file__), node.lineno, node.value))


class TheCycleSuppliesTheReservation(unittest.TestCase):
    """The rule is only worth anything if the cycle actually passes the open buys in."""

    def test_a_resting_entry_carries_its_limit_price(self):
        """Without a price, `qty_open` cannot say how much cash an open buy has spoken for.

        Asserted on the SOURCE of `reconcile`, because building a fake Alpaca order list here
        would test the fake. The key is read from the order object at the one place it exists.
        """
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "reconcile")
        keys = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Dict):
                keys += [k.value for k in node.keys
                         if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        self.assertIn("qty_open", keys)
        self.assertIn("limit_price", keys,
                      "a resting entry must carry the price its cash commitment is computed "
                      "from, or the reservation cannot be derived from it")

    def test_run_slot_reserves_open_buys_before_it_takes_the_budget(self):
        """ORDER MATTERS AND IS READ OFF THE AST. A reservation computed after the budget would
        be a report rather than a bound."""
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_slot")
        seq = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name in ("SETTLE.open_buy_value", "SETTLE.spendable"):
                    seq.append((node.lineno, name))
        seq.sort()
        self.assertEqual([n for _, n in seq],
                         ["SETTLE.open_buy_value", "SETTLE.spendable"], seq)

    def test_the_budget_call_passes_the_reservation(self):
        src = io.open(LC.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_slot")
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call)
                    and ast.unparse(node.func) == "SETTLE.spendable"):
                self.assertIn("reserved", [k.arg for k in node.keywords],
                              "run_slot sizes a buy without reserving its open buys")
                return
        self.fail("run_slot no longer calls SETTLE.spendable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
