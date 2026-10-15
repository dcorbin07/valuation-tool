"""TELL DON WHAT THE LIVE CYCLE DID — and say the repeating things once.  [item 58b step 6]

WHY THIS IS NOT `fleet_notify.announce`
---------------------------------------
Its **discipline** is reused verbatim and deliberately: discrete events always, repeating
conditions only when they change, a quiet cycle stays quiet, the watermark moves only on a
successful send, and it never raises. Those rules were paid for — the fleet's own note records
that eighteen books blocked on one self-check would have posted the same eighteen lines every
evening until nobody read them.

Its **code** is not reused, because the two watermarks are keyed on different things.
`fleet_notify` dedupes fills by an integer `seq` per book, which a fleet record supplies and a
slot has no analogue of: a live cycle's discrete event is an ORDER, identified by
`(slot, event_key, ticker, side, quantity)`. Bending the fleet's `seq` floor around that would
mean inventing a sequence number for something that has none, and the `MA6` direction matters
here — a watermark that mis-keys an order announces it twice, or never.

The one thing that IS shared is the webhook: both call `saas.notify.send_discord`, so there is
one path out and one place a webhook is configured.

WHAT IS AN EVENT AND WHAT IS A CONDITION
----------------------------------------
**EVENTS (always announced, deduped by identity):** an order sent, an order rejected by the
broker. Each is a thing that happened once and is worth exactly one line.

**CONDITIONS (announced only when they change):** a preflight failure, a parity mismatch, a
missing paper client, a cycle crash. These persist across cycles by their nature — a slot whose
price map is short a name is short it every cycle until the data returns — so the signature is
`(slot, kind, first 120 chars of the reason)` and a slot sitting in the same condition says
nothing. **A condition CLEARING is also one line**, because a gate that was closed and has
opened is the good half of the same fact and exactly as worth knowing.

WHAT IT NEVER SAYS
------------------
No P&L, no running total, no return, no verdict — the same prohibition `fleet_notify` carries,
for the same reason: §8's horizon is pre-committed and a Discord line is not where a figure gets
read early. An order line says side, ticker, quantity and limit price, which are logbook facts.
A test asserts no return-shaped word reaches the body.
"""
from __future__ import annotations

import json
import os

SCHEMA = "live_notify/1"
STATE_FILENAME = "_notified.json"

#: The alert kinds that are DISCRETE EVENTS. Everything else is treated as a condition.
#: Declared as a literal rather than inferred from the string, because "which of these repeats"
#: is a judgement about each kind and not a property of its name.
EVENT_KINDS = ("live_order_sent", "broker_error")

#: How much of a reason participates in a condition's signature. Enough to tell two different
#: failures apart, short enough that two phrasings of one failure do not each get a line.
SIG_CHARS = 120

#: The identity list is append-only and an order path runs for years. Keeping the last 500 is
#: far more than any plausible window of repeated dispatches and stops the file growing forever.
MAX_REMEMBERED = 500


def state_path(root: str = None) -> str:
    from . import live_cycle as LC
    return os.path.join(LC.live_dir(root), STATE_FILENAME)


def _read(root: str = None) -> dict:
    try:
        with open(state_path(root), encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and raw.get("schema") == SCHEMA:
            return raw
    except Exception:                                                  # noqa: BLE001
        pass
    return {"schema": SCHEMA, "announced": [], "conditions": {}}


def _write(state: dict, root: str = None) -> bool:
    p = state_path(root)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(p + ".tmp", p)
        return True
    except Exception:                                                  # noqa: BLE001
        return False


def event_id(a: dict) -> str:
    """The identity of a discrete event.

    **A RE-PRICED REMAINDER IS A NEW LINE, AND THAT IS CORRECT.** It is a new order at a new
    limit for a smaller quantity, carrying the same event key — so the identity has to include
    the reason text, which holds the quantity and price, to tell "the remainder was re-sent"
    from "the same order announced twice". A retry of the identical cycle produces the identical
    quantity and is suppressed; a genuine re-send after a part fill produces a smaller one and
    is announced.
    """
    return "|".join([str(a.get("kind") or ""), str(a.get("slot") or ""),
                     str(a.get("event") or ""), str(a.get("reason") or "")[:SIG_CHARS]])


def condition_sig(a: dict) -> str:
    return "%s|%s" % (str(a.get("kind") or ""), str(a.get("reason") or "")[:SIG_CHARS])


def pending(alerts, root: str = None) -> dict:
    """What is NEW. Pure — reads the record, writes nothing."""
    st = _read(root)
    seen = set(st.get("announced") or [])
    known = dict(st.get("conditions") or {})

    events, conditions, by_slot = [], [], {}
    for a in (alerts or []):
        slot = str((a or {}).get("slot") or "-")
        kind = str((a or {}).get("kind") or "")
        if kind in EVENT_KINDS:
            if event_id(a) not in seen:
                events.append(dict(a))
            continue
        by_slot.setdefault(slot, set()).add(condition_sig(a))
        if condition_sig(a) not in set(known.get(slot) or []):
            conditions.append(dict(a))

    # A CONDITION THAT HAS CLEARED. One line, for the reason in the module docstring.
    cleared = []
    for slot, sigs in sorted(known.items()):
        now = by_slot.get(slot) or set()
        for s in sorted(set(sigs) - now):
            cleared.append({"slot": slot, "was": s.split("|", 1)[0]})

    return {"events": events, "conditions": conditions, "cleared": cleared,
            "by_slot": {k: sorted(v) for k, v in by_slot.items()},
            "quiet": not (events or conditions or cleared)}


def compose(p: dict) -> str:
    """The message. Facts only."""
    lines = ["**Live path cycle**"]
    for a in p["events"]:
        tag = "order" if a.get("kind") == "live_order_sent" else "REJECTED"
        lines.append("- slot %s %s: %s" % (a.get("slot"), tag, a.get("reason")))
    for a in p["conditions"]:
        lines.append("- slot %s **%s**: %s" % (a.get("slot"), a.get("kind"), a.get("reason")))
    for c in p["cleared"]:
        lines.append("- slot %s: %s has cleared" % (c.get("slot"), c.get("was")))
    return "\n".join(lines)


def announce(alerts, *, root: str = None, cfg=None, send=None) -> dict:
    """Send if anything is new, then remember it. NEVER RAISES.

    Its failure is never the cycle's: a missing webhook, a Discord outage or an unwritable
    record all return a reason and leave the slot records untouched. An order being placed and
    recorded is what matters; telling someone is strictly secondary, and a notifier that could
    take the cycle down with it would have inverted that.
    """
    p = pending(alerts, root)
    out = {"sent": False, "quiet": p["quiet"], "reason": "", "n_events": len(p["events"]),
           "n_conditions": len(p["conditions"]), "n_cleared": len(p["cleared"])}
    if p["quiet"]:
        out["reason"] = "nothing new to announce"
        return out
    try:
        if send is None:
            from ..saas.notify import send_discord as send
        ok = bool(send(cfg, compose(p)))
    except Exception as e:                                             # noqa: BLE001
        ok, out["reason"] = False, "the webhook failed (%s)" % type(e).__name__
    out["sent"] = ok
    if not ok and not out["reason"]:
        out["reason"] = "no webhook configured, or it declined"

    # THE RECORD MOVES ONLY ON A SUCCESSFUL SEND. A failed post that advanced it would lose the
    # very order it failed to announce, silently and permanently -- `fleet_notify`'s rule, and
    # it matters more here because the thing lost would be a real order.
    if ok:
        st = _read(root)
        seen = list(st.get("announced") or [])
        for a in p["events"]:
            i = event_id(a)
            if i not in seen:
                seen.append(i)
        st["announced"] = seen[-MAX_REMEMBERED:]
        st["conditions"] = p["by_slot"]
        out["remembered"] = _write(st, root)
    return out
