"""MULTI-ACCOUNT ALERT ROUTING — which account is this card for?

Don runs more than one Tradier account. The scan is market-wide, so a card's CONTENT is the
same for each; what differs is which account it is actionable in. One shared webhook posts
them all to one channel, so the label is the only thing that tells them apart — which is why
every card carries one and why the label is the deliverable rather than decoration.

**AN ACCOUNT EXISTS IFF `LABEL` AND `TOKEN` ARE BOTH NON-EMPTY.** Both, because either alone is
a half-configured account: a token with no label produces an unlabelable card on a shared
channel, and a label with no token names an account nothing can ever read. Slots are
`TRADIER_ACCOUNT_1..10`; a gap in the numbering is not an error, so deleting slot 2 does not
silently renumber slots 3 and up.

**THIS MODULE NEVER RETAINS A TOKEN, AND THAT IS THE ORDER GUARD RATHER THAN A RULE ABOUT ONE.**
The standing rule is that these credentials are data/sandbox only and no order endpoint may be
added or called. A grep-based ban on the word `orders` would fire against
`valuation/edge/paper_broker.py`, which legitimately places SANDBOX orders for the forward
paper track under its own register — the substring-ban family this project has now paid for six
times. So the guarantee is structural instead: **`TOKEN` is read as an existence predicate and
discarded on the same line.** No function here returns it, nothing here imports `requests`, and
the routing path therefore holds no credential with which an order could be placed. You cannot
call an endpoint you have no token for.

**PORTFOLIO VISIBILITY IS NOT BUILT HERE, and the constraint on it is pinned in advance.** When
it is built it is VISIBILITY ONLY and may never become an input to scoring — a position the
model can see is a position the model can be influenced by, and a screen that quietly favours
what you already hold is not a screen. `tests/test_multi_account.py` asserts no scoring module
imports this one, so the boundary fails loudly on the day somebody crosses it rather than
quietly in a backtest nobody re-ran.

**ZERO ACCOUNTS IS TODAY, EXACTLY.** `fanout()` returns `[None]` when nothing is configured, so
every call site loops exactly once with `account=None`, and `tag()` and `dedup_key()` are then
identity functions. The unchanged path is not a branch anybody has to remember to keep working
— it is the same loop running once with a label that is absent. That is why the bit-identical
guarantee is structural rather than a second code path tested alongside the first.
"""
from __future__ import annotations

import os
from typing import Optional

#: `TRADIER_ACCOUNT_1..10`. Ten is the declared ceiling; an eleventh is ignored rather than
#: silently promoted, so raising it is a visible edit.
SLOTS = tuple(range(1, 11))

#: The three env names per slot. `ID` is the broker's account identifier -- it names WHICH
#: account, and is carried so a card can be traced back to one. It is not a credential.
FIELDS = ("LABEL", "TOKEN", "ID")

_VAR = "TRADIER_ACCOUNT_%d_%s"


def var_name(slot: int, field: str) -> str:
    """The env var for a slot and field. One definition, so a test cannot drift from the reader."""
    return _VAR % (slot, field)


def _read(env, slot: int, field: str) -> str:
    return (env.get(var_name(slot, field)) or "").strip()


def accounts(env=None) -> list:
    """Configured accounts, in slot order.

    Returns `{slot, label, account_id}` and **never a token**. See the module docstring: the
    token is read here only to decide whether the account exists, and is not carried out of
    this function in any form.
    """
    env = os.environ if env is None else env
    out = []
    for slot in SLOTS:
        label = _read(env, slot, "LABEL")
        # Read, tested, discarded. It is deliberately not assigned anywhere that outlives the
        # `if` below -- the local dies with the loop iteration and is never returned or logged.
        if not label or not _read(env, slot, "TOKEN"):
            continue
        out.append({"slot": slot, "label": label, "account_id": _read(env, slot, "ID")})
    return out


def configured(env=None) -> bool:
    return bool(accounts(env))


def fanout(env=None) -> list:
    """The accounts to emit one card for — `[None]` when none is configured.

    `[None]` rather than `[]` is the whole design. A call site writes one loop and gets today's
    single unlabelled send for free when nothing is set up, so there is no second code path to
    keep in step with the first.
    """
    return accounts(env) or [None]


def tag(text: str, account: Optional[dict] = None) -> str:
    """Prefix a card with its account label. Identity when `account` is None.

    A leading line rather than an inline edit, so the card body is byte-for-byte what it was
    and no composer has to know that routing exists.
    """
    if not account:
        return text
    return "`%s`\n%s" % (account.get("label") or "", text)


def dedup_key(base: str, account: Optional[dict] = None) -> str:
    """Per-account once-a-day key. Identity when `account` is None.

    Keyed on the SLOT, not the label: renaming an account in the env would otherwise reset its
    dedup and re-post a card that had already gone out.
    """
    if not account:
        return base
    return "%s:%d" % (base, int(account.get("slot") or 0))


def describe(env=None) -> dict:
    """What is configured, for a health block. Labels and ids only — no token, by construction."""
    acc = accounts(env)
    return {"n": len(acc),
            "labels": [a["label"] for a in acc],
            "slots": [a["slot"] for a in acc],
            "routing_active": bool(acc),
            "note": ("no TRADIER_ACCOUNT_n_LABEL/TOKEN pair is set, so cards are unlabelled and "
                     "behave exactly as they did before multi-account routing existed"
                     if not acc else
                     "each digest and alert card is posted once per account and labelled; one "
                     "shared webhook, so the label is what tells them apart")}
