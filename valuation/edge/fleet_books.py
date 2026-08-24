"""THE DECLARED FLEET BOOKS' ENTRY RULES -- the code a declaration froze in prose.

**A DECLARATION FREEZES AN ENTRY RULE. IT DOES NOT EXECUTE ONE.** Seventeen books were
declared on 2026-08-24 and `cycle()` measured `entry_rules_implemented: 0`; every cycle would
have placed nothing, forever, and reported it honestly as `ARMED_NO_ENTRY_RULE`. This module
is the other half: the rules as code.

THE LAW THIS MODULE IS WRITTEN UNDER, and it is narrower than "make it work":

  * **THE CODE MATCHES THE FROZEN PROSE EXACTLY.** No improvement, no tuning, no parameter
    the declaration does not state. Where a declaration says "the 3 largest by market cap,
    alphabetical tie-break", that is the rule -- not the better rule, and not the rule with a
    sensible extra filter. A book's declaration is its pre-registration; code that quietly
    improves on it is measuring something nobody registered.
  * **AMBIGUITY IS AMENDED IN THE OPEN OR REFUSED BACK, NEVER INTERPRETED SILENTLY.** Every
    place the prose could not be executed as written carries a dated AMENDMENT section in the
    declaration file itself, and the amendment is a NEW section -- never an edit -- on
    `PT-AMEND1`'s rule: a correction that leaves no record of what it replaced is
    indistinguishable from the text having always said so.
  * **REGISTRATION IS AN EXPLICIT CALL, NEVER AN IMPORT SIDE EFFECT.** `register_all()` has to
    be invoked by whatever process drives a cycle. Importing this module registers nothing,
    so a test, a script and the runner all get the same empty seam until they ask -- `S3-I3`'s
    own convention, and the reason a stray import cannot silently arm a fleet.

WHAT A RULE RETURNS. `fn(decl, root) -> list[dict]`, each dict being kwargs for
`fleet.fill_fields`. **Returning `[]` means the rule ran and today qualifies nobody, which is
a market observation.** Not being registered at all means the rule was never built, which is
not. `cycle()` keeps those apart and so must this module.
"""
from __future__ import annotations

from . import fleet as F


# ---------------------------------------------------------------------------------------
# F-1 -- THE FILL A/B
# ---------------------------------------------------------------------------------------
def f1_fill_ab(decl: dict, root: str = None) -> list:
    """F-1 places no orders. Its evidence is every OTHER book's fill row.

    **THIS RULE RETURNS `[]` AND THAT IS THE IMPLEMENTATION, NOT A STUB.** The declaration's
    frozen entry rule opens *"No entries of its own"*, and its universe is *"whatever the
    other fleet books trade"*. A rule that manufactured F-1 orders would be trading a book
    that declared it does not trade.

    **THE WORK F-1 ACTUALLY NEEDED IS IN `fleet.submit`**, which is where the frozen sentence
    puts it: *"**Every order any fleet book submits** is assigned by the harness's
    deterministic randomizer to arm A or arm B."* The assignment is a property of the
    harness's submission path, so no per-book callable could implement it -- F-1's callable
    cannot reach the orders of books that are not F-1. Registering it here with
    `places_orders=False` is what stops `cycle()` counting a rider as a breathing fleet.

    ITS RECORD STREAM STAYS EMPTY BY DESIGN. `records_schema` is `[]` in its own declaration
    and the draft says the per-order capture is *"computed at read time, not stored"*, so the
    verdict is read from the union of the other books' `arm`-stamped fill rows. Nothing is
    mirrored into F-1's own chain: a mirror would be a second copy of a fact, and the first
    copy is already hash-chained on the host's stream.
    """
    return []


# ---------------------------------------------------------------------------------------
# THE REGISTRY
# ---------------------------------------------------------------------------------------
# book -> (callable, places_orders). `places_orders=False` marks a RIDER: a book whose own
# declaration says it never sends an order, so a cycle in which only riders ran is NOT a
# breathing fleet and `cycle()` must not report one.
RULES = {
    "f1_fill_ab": (f1_fill_ab, False),
}


def register_all() -> dict:
    """Register every implemented rule. Explicit, idempotent, and never an import side effect.

    Returns the registered book names so a caller can assert what it armed rather than assume
    it. A book absent from `RULES` is still declared and still un-armed, and `cycle()` will
    keep saying so.
    """
    for book, (fn, places) in sorted(RULES.items()):
        F.register_entry_rule(book, fn, places_orders=places)
    return {"ok": True, "registered": sorted(RULES), "count": len(RULES)}
