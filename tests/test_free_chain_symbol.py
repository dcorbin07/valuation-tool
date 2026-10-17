"""The free option chain must carry the OCC symbol - the field whose absence broke the orders.

**THE DEFECT, AND IT WAS INVISIBLE UNTIL THE VENUE MOVED.** `FreeProvider.get_option_chain`'s
docstring said *"Same shape from yfinance"* and it was not the same shape: Tradier's chain rows
carry `symbol`, the OCC id every order path needs, and these rows carried every other field and
not that one. Nothing noticed while Tradier served the chain. When the account closed on
2026-10-08 `get_provider` correctly fell through to `FreeProvider`, and the first book to reach
a broker afterwards raised:

    f3_bear_puts  ENTRY_RULE_RAISED  "not an OCC symbol: 'None'"

**`str(None)` IS THE FOUR-CHARACTER STRING `"None"`**, so a missing key was not a missing key by
the time it reached the venue - it was a plausible-looking symbol. The refusal named the string
instead of the field.

WHAT THESE PIN
--------------
1. **The key sets of the two providers agree**, so "same shape" is an obligation a test holds
   rather than a sentence in a docstring.
2. **The symbol round-trips**: `parse_occ` of it must agree with the row's own strike, expiry
   and right. A symbol that parses to a DIFFERENT contract is worse than none.
3. **A missing symbol becomes `""`, never `"None"`**, so the refusal names the real fault.

    python tests/test_free_chain_symbol.py
"""
from __future__ import annotations

import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet_books as FB  # noqa: E402
from valuation.edge.alpaca_options import parse_occ  # noqa: E402

PROVIDERS = os.path.join(REPO, "valuation", "intraday", "providers.py")


def _free_row_keys():
    """The literal dict `FreeProvider.get_option_chain` appends, read from the SOURCE.

    Read statically so the test needs no network and still fails if the field is removed --
    a network-gated guard is one that silently skips on a runner (`guards that fail open`).
    """
    with open(PROVIDERS, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == "FreeProvider"):
            continue
        for fn in node.body:
            if not (isinstance(fn, ast.FunctionDef) and fn.name == "get_option_chain"):
                continue
            for n in ast.walk(fn):
                if isinstance(n, ast.Dict) and any(
                        isinstance(k, ast.Constant) and k.value == "strike" for k in n.keys):
                    return {k.value for k in n.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    return set()


class TestTheShapeObligation(unittest.TestCase):
    """(1)."""

    def test_the_free_row_carries_symbol(self):
        self.assertIn("symbol", _free_row_keys(),
                      "the OCC id is the field the order path needs")

    def test_it_also_still_carries_everything_it_carried_before(self):
        """The positive control: adding a key must not have dropped one."""
        keys = _free_row_keys()
        for k in ("option_type", "expiration_date", "strike", "bid", "ask",
                  "volume", "open_interest", "greeks"):
            self.assertIn(k, keys)

    def test_the_docstring_states_the_obligation_rather_than_assuming_it(self):
        from valuation.intraday.providers import FreeProvider
        d = FreeProvider.get_option_chain.__doc__ or ""
        self.assertIn("same shape", d.lower())
        self.assertIn("symbol", d)


class TestTheSymbolRoundTrips(unittest.TestCase):
    """(2) - a symbol that parses to a DIFFERENT contract is worse than no symbol."""

    def test_a_built_symbol_agrees_with_its_own_row(self):
        row = {"symbol": "AAPL261106C00110000", "option_type": "call",
               "expiration_date": "2026-11-06", "strike": 110.0}
        got = parse_occ(row["symbol"])
        self.assertEqual(got["underlying"], "AAPL")
        self.assertEqual(got["expiration"], row["expiration_date"])
        self.assertEqual(got["right"], "C")
        self.assertEqual(got["strike"], row["strike"])

    def test_a_put_round_trips_too(self):
        got = parse_occ("NKE261016P00032500")
        self.assertEqual(got["right"], "P")
        self.assertEqual(got["strike"], 32.5)
        self.assertEqual(got["expiration"], "2026-10-16")


class TestAMissingSymbolIsNeverTheStringNone(unittest.TestCase):
    """(3)."""

    def test_missing_and_none_both_give_empty(self):
        self.assertEqual(FB._occ_or_refuse({}), "")
        self.assertEqual(FB._occ_or_refuse({"symbol": None}), "")
        self.assertEqual(FB._occ_or_refuse(None), "")

    def test_it_never_returns_the_literal_None(self):
        for bad in ({}, {"symbol": None}, {"symbol": ""}):
            self.assertNotEqual(FB._occ_or_refuse(bad), "None")

    def test_a_real_symbol_is_kept_verbatim_apart_from_whitespace(self):
        """Stripped, NOT case-folded: the record must carry what the chain returned."""
        self.assertEqual(FB._occ_or_refuse({"symbol": " AAPL261120P00280000 "}),
                         "AAPL261120P00280000")
        self.assertEqual(FB._occ_or_refuse({"symbol": "aaa260ct80"}), "aaa260ct80")

    def test_no_book_builds_its_order_symbol_with_str_of_a_get(self):
        """The construction that produced "None" must not come back anywhere.

        **READ FROM THE SYNTAX TREE, NOT THE TEXT.** My first cut grepped for the literal
        `str(c.get("symbol"))` and FAILED against the fixed tree, because `_occ_or_refuse`'s
        own docstring quotes the construction it exists to replace -- `MA49`'s substring-ban
        family, in the very commit that fixes a `str(None)`. The AST sees code.
        """
        with open(os.path.join(REPO, "valuation", "edge", "fleet_books.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        bad = []
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "str" and len(n.args) == 1):
                continue
            a = n.args[0]
            if (isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
                    and a.func.attr == "get" and a.args
                    and isinstance(a.args[0], ast.Constant)
                    and a.args[0].value == "symbol"):
                bad.append(getattr(n, "lineno", "?"))
        self.assertEqual(bad, [], "str(...get('symbol')) is back at line(s) %r" % (bad,))
        self.assertGreaterEqual(src.count("_occ_or_refuse(c)"), 5,
                                "every order site must go through the helper")

    def test_that_guard_would_have_caught_the_real_defect(self):
        """The positive control: the AST check must bite on the construction it bans."""
        tree = ast.parse('out.append(F.submit("b", occ=str(c.get("symbol")), qty=1))')
        hits = [n for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "str" and len(n.args) == 1
                and isinstance(n.args[0], ast.Call)
                and getattr(n.args[0].func, "attr", "") == "get"]
        self.assertEqual(len(hits), 1, "the guard must see the shape it bans")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
