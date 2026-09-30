"""A FRACTIONAL QUANTITY IS REFUSED, NEVER ROUNDED — settled against the live sandbox.

**MEASURED, NOT READ.** Tradier's API reference says equity `quantity` is "in whole numbers"
while the brokerage advertises fractional shares, and both readings were defensible. It was
settled on 2026-09-15 by sending `preview=true` validations to the SANDBOX — full order
validation, no order placed — for a liquid name:

    quantity 0.5  ->  HTTP 400  "Invalid parameter, quantity: decimal places are not allowed."
    quantity 1.5  ->  HTTP 400  same
    quantity 1    ->  HTTP 200  previewed cleanly, quantity 1

**So the API rejects fractional outright and does NOT silently truncate — the safe answer.**

**THE DANGER WAS ON OUR SIDE OF THE WIRE.** Both order methods built their payload with
`str(int(quantity))`, so a caller passing 0.5 sent `"0"` and 1.5 sent `"1"` — and the API
accepts a whole number happily. A book that thinks it bought 0.5 and bought 1 is worse than one
that was refused, and neither failure is visible in the order record afterwards. That is what
makes truncation the dangerous answer rather than merely the wrong one.

These tests pin the refusal. They make NO network call: the truncation was a payload-building
defect and is tested where it lived.

Run: python tests/test_fractional_refusal.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import paper_broker as PB                            # noqa: E402

PASSED = FAILED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def test_a_fractional_quantity_is_refused_rather_than_rounded():
    for bad in (0.5, 1.5, 2.25, 0.999, 10.0001):
        try:
            PB._whole_shares(bad)
        except ValueError as e:
            assert "fractional" in str(e), (bad, str(e))
        else:
            raise AssertionError("%r was accepted; it must be refused" % bad)


def test_the_refusal_names_the_consequence_not_just_the_rule():
    """An operator who sees this must understand why it is not simply rounded for them."""
    try:
        PB._whole_shares(0.5)
    except ValueError as e:
        msg = str(e).lower()
        assert "whole shares only" in msg, msg
        assert "did not trade" in msg or "record" in msg, (
            "the refusal does not say what the silent alternative would have cost: %s" % msg)


def test_whole_quantities_still_pass_through_unchanged():
    """The fix must not be a blanket refusal — real orders are whole-share orders."""
    for good, want in ((1, "1"), (1.0, "1"), (25, "25"), (100.0, "100")):
        assert PB._whole_shares(good) == want, (good, PB._whole_shares(good))


def test_zero_is_not_quietly_treated_as_valid():
    """`int(0.5)` was 0, which Tradier rejects only because zero is invalid — the RIGHT
    outcome for the WRONG reason, and it would have read as an API refusal rather than as a
    client bug. Zero passes this helper (it is a whole number); it is the FRACTION that must
    never reach the wire."""
    assert PB._whole_shares(0) == "0"
    try:
        PB._whole_shares(0.5)
    except ValueError:
        pass
    else:
        raise AssertionError("0.5 still becomes something")


def test_neither_order_method_truncates_any_more():
    """Pinned on the SOURCE, because the defect was one call in a payload literal.

    READ FROM THE SYNTAX TREE, not grepped. The first cut banned the substring
    `str(int(quantity))` and fired three times: once on a genuine third truncation site in
    `place_multileg` that this test FOUND, and twice on prose and on `_whole_shares`'s own
    validated internals — a guard tripping on the comment documenting its own rule, which is a
    family this repository has now paid for repeatedly. The AST sees the calls and not the
    words about them, and `_whole_shares` is exempted by IDENTITY rather than by wording.
    """
    import ast
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "edge", "paper_broker.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    converter = next((n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name == "_whole_shares"), None)
    assert converter is not None, "the refusing converter is gone"
    inside = {id(n) for n in ast.walk(converter)}

    bad = []
    for node in ast.walk(tree):
        if id(node) in inside:
            continue
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "str" and len(node.args) == 1
                and isinstance(node.args[0], ast.Call)
                and isinstance(node.args[0].func, ast.Name)
                and node.args[0].func.id == "int"):
            bad.append(node.lineno)
    assert not bad, ("a truncating str(int(...)) conversion survives outside the refusing "
                     "converter, at line(s) %s" % bad)
    assert src.count("_whole_shares(") >= 4, (
        "all three order paths plus the definition must reference the refusing converter")


def test_the_guard_can_actually_fire():
    """A positive control: the helper must reject something, or these tests prove nothing."""
    raised = False
    try:
        PB._whole_shares(0.5)
    except ValueError:
        raised = True
    assert raised, "the refusal never fires; this suite would be vacuous"


def run():
    global PASSED, FAILED
    print("FRACTIONAL QUANTITY REFUSAL")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
