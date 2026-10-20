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

WHICH CHANNEL [item 74]
-----------------------
Don's ruling of 2026-10-18 splits the two: problems go to `#valquo-alerts`, and the routine
posts -- an order sent, an order filled -- stay where they are. **The channel is read from
`saas.alert_routing`, never inferred from the kind's name**, because no name rule works in both
directions on the kinds this module already emits: `account_changed` and
`stale_open_event_never_completed` are the two most serious things it can say and neither
contains a word a rule could key on, while `live_order_sent` is the most routine.

A still-broken condition is also reminded **once a day** -- the third of Don's three noise rules
(one post when it starts, one when it clears, one reminder per day while it stays broken).

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

from ..saas import alert_routing as AR

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


def conditions_of(st: dict) -> dict:
    """The conditions record as `{slot: {sig: last_posted_date}}`, migrating the old shape.

    **THE SCHEMA STRING IS DELIBERATELY NOT BUMPED [item 74].** A daily reminder needs a date
    per signature, which the old `{slot: [sig, ...]}` cannot hold -- but `_read` refuses an
    unknown schema and returns an empty record, so bumping it would discard `announced` and
    RE-ANNOUNCE every order every slot has ever sent. On a real-money order path that is the
    worse failure by a distance, so the old shape is migrated here instead.

    A migrated signature gets NO date, which reads as "due a reminder" -- the loud direction,
    and it costs exactly one extra line per open condition on the first cycle after this ships.
    """
    out = {}
    for slot, sigs in (st.get("conditions") or {}).items():
        if isinstance(sigs, dict):
            out[str(slot)] = {str(k): (str(v) if v else "") for k, v in sigs.items()}
        else:
            out[str(slot)] = {str(x): "" for x in (sigs or [])}
    return out


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


def pending(alerts, root: str = None, now=None) -> dict:
    """What is NEW, split by channel. Pure -- reads the record, writes nothing.

    Four buckets now rather than three, and the new one is Don's third noise rule:

      * `events`     -- discrete, deduped by identity, always said once;
      * `conditions` -- newly appeared, or appeared with a new reason;
      * `reminders`  -- still present, and last said on an earlier DAY [item 74];
      * `cleared`    -- gone since the last cycle.

    `unclassified` holds any kind `alert_routing` does not classify. **Collected, never routed**:
    a single unclassified kind must not cost the cycle every other line it was about to send,
    and the registry's own test is what stops one existing in the first place.
    """
    st = _read(root)
    seen = set(st.get("announced") or [])
    known = conditions_of(st)
    today = AR.today_stamp(now)

    events, conditions, reminders, by_slot, unclassified = [], [], [], {}, []
    for a in (alerts or []):
        slot = str((a or {}).get("slot") or "-")
        kind = str((a or {}).get("kind") or "")
        try:
            AR.channel_for(kind)
        except AR.UnclassifiedAlert:
            unclassified.append(dict(a))
            continue
        if kind in EVENT_KINDS:
            if event_id(a) not in seen:
                events.append(dict(a))
            continue
        sig = condition_sig(a)
        prior = (known.get(slot) or {}).get(sig)
        if prior is None:
            conditions.append(dict(a))
            by_slot.setdefault(slot, {})[sig] = today
        elif AR.needs_reminder(prior, today):
            # STILL BROKEN, AND LAST SAID YESTERDAY OR EARLIER. Don: "one reminder per day
            # while it stays broken."
            reminders.append(dict(a))
            by_slot.setdefault(slot, {})[sig] = today
        else:
            by_slot.setdefault(slot, {})[sig] = prior

    # A CONDITION THAT HAS CLEARED. One line, for the reason in the module docstring. The full
    # signature and its date travel with it, so a FAILED clearing post can be put back in the
    # record and retried rather than lost.
    cleared = []
    for slot, sigs in sorted(known.items()):
        live = by_slot.get(slot) or {}
        for sig in sorted(set(sigs) - set(live)):
            cleared.append({"slot": slot, "was": sig.split("|", 1)[0], "sig": sig,
                            "since": sigs.get(sig) or ""})

    return {"events": events, "conditions": conditions, "reminders": reminders,
            "cleared": cleared, "by_slot": by_slot, "unclassified": unclassified,
            "today": today,
            "quiet": not (events or conditions or reminders or cleared)}


def _channel(a) -> str:
    """The channel for an alert dict or a cleared entry. Registry only, never the name."""
    return AR.channel_for(str((a or {}).get("kind") or (a or {}).get("was") or ""))


def for_channel(p: dict, channel: str) -> dict:
    """`p`, restricted to one channel. The split is the registry's, not this module's."""
    def keep(xs):
        return [x for x in xs if _channel(x) == channel]
    return {"events": keep(p["events"]), "conditions": keep(p["conditions"]),
            "reminders": keep(p["reminders"]), "cleared": keep(p["cleared"])}


def compose(p: dict, channel: str = None) -> str:
    """The message. Facts only. Empty string when this channel has nothing to say.

    `channel=None` composes EVERYTHING, which is what `tests/test_item58b.py` reads and what a
    caller wanting the whole picture in one string gets. The two-channel send path uses
    `for_channel` first.
    """
    q = p if channel is None else for_channel(p, channel)
    if not (q["events"] or q["conditions"] or q["reminders"] or q["cleared"]):
        return ""
    head = {AR.ALERTS: "**Live path cycle — PROBLEMS**",
            AR.ROUTINE: "**Live path cycle**"}.get(channel, "**Live path cycle**")
    lines = [head]
    for a in q["events"]:
        tag = "order" if a.get("kind") == "live_order_sent" else "REJECTED"
        lines.append("- slot %s %s: %s" % (a.get("slot"), tag, a.get("reason")))
    for a in q["conditions"]:
        lines.append("- slot %s **%s**: %s" % (a.get("slot"), a.get("kind"), a.get("reason")))
    for a in q["reminders"]:
        # NAMED AS A REMINDER, so a reader can tell "this started today" from "this is day
        # four". Without that the daily post is indistinguishable from a new failure.
        lines.append("- slot %s **%s** (still, since the last post): %s"
                     % (a.get("slot"), a.get("kind"), a.get("reason")))
    for c in q["cleared"]:
        lines.append("- slot %s: %s has cleared" % (c.get("slot"), c.get("was")))
    return "\n".join(lines)


def announce(alerts, *, root: str = None, cfg=None, send=None, now=None) -> dict:
    """Send what is new, per channel, then remember it. NEVER RAISES.

    Its failure is never the cycle's: a missing webhook, a Discord outage or an unwritable
    record all return a reason and leave the slot records untouched. An order being placed and
    recorded is what matters; telling someone is strictly secondary, and a notifier that could
    take the cycle down with it would have inverted that.

    **THE WATERMARK IS PER CHANNEL [item 74], and that is a correctness fix rather than a
    tidying.** The record used to advance wholesale on one successful send. With two channels
    that would mean a successful ROUTINE post discarding the alert lines that failed to post --
    losing exactly the message Don asked to be told about. So each signature's record advances
    only if the channel carrying it succeeded; a NEW condition whose post failed is left unknown
    so it is retried next cycle; and a CLEARED condition whose post failed is put back in the
    record so the clearing is announced again.

    `send(cfg, body, channel)` -- the seam takes the channel because the real function does.
    A seam whose signature differs from the thing it stands in for is how a fixture comes to
    pass against behaviour that could not happen.
    """
    p = pending(alerts, root, now)
    out = {"sent": False, "quiet": p["quiet"], "reason": "",
           "n_events": len(p["events"]), "n_conditions": len(p["conditions"]),
           "n_reminders": len(p["reminders"]), "n_cleared": len(p["cleared"]),
           "by_channel": {}}
    if p["unclassified"]:
        # LOUD, AND IT DOES NOT STOP THE REST. The kinds are named; nothing is guessed at.
        out["unclassified"] = sorted({str(a.get("kind") or "") for a in p["unclassified"]})
        out["reason"] = ("%d alert kind(s) are in no channel and were NOT sent: %s"
                         % (len(out["unclassified"]), ", ".join(out["unclassified"])))
    if p["quiet"]:
        out["reason"] = out["reason"] or "nothing new to announce"
        return out
    if send is None:
        try:
            from ..saas.notify import send_discord as send
        except Exception as e:                                         # noqa: BLE001
            out["reason"] = "the notifier could not be imported (%s)" % type(e).__name__
            return out

    ok_ch, reasons = {}, []
    for ch in (AR.ALERTS, AR.ROUTINE):
        body = compose(p, ch)
        if not body:
            continue
        try:
            ok = bool(send(cfg, body, ch))
        except Exception as e:                                         # noqa: BLE001
            ok, why = False, "the webhook failed (%s)" % type(e).__name__
            reasons.append("%s: %s" % (ch, why))
        else:
            if not ok:
                reasons.append("%s: no webhook configured, or it declined" % ch)
        ok_ch[ch] = ok
        out["by_channel"][ch] = {"sent": ok, "lines": body.count("\n")}
    out["sent"] = any(ok_ch.values())
    if reasons:
        out["reason"] = "; ".join([out["reason"]] + reasons) if out["reason"] \
            else "; ".join(reasons)

    if not any(ok_ch.values()):
        return out

    st = _read(root)
    known = conditions_of(st)
    seen = list(st.get("announced") or [])
    for a in p["events"]:
        if not ok_ch.get(_channel(a)):
            continue                                  # retried next cycle, by design
        i = event_id(a)
        if i not in seen:
            seen.append(i)
    st["announced"] = seen[-MAX_REMEMBERED:]

    kept = {}
    for slot, sigs in p["by_slot"].items():
        for sig, date in sigs.items():
            ch = AR.channel_for(sig.split("|", 1)[0])
            if ok_ch.get(ch):
                kept.setdefault(slot, {})[sig] = date
            else:
                prior = (known.get(slot) or {}).get(sig)
                if prior is not None:
                    kept.setdefault(slot, {})[sig] = prior
    for c in p["cleared"]:
        if not ok_ch.get(_channel(c)):
            # THE CLEARING MUST BE RETRIED, so the signature goes back in. Dropping it would
            # make the good half of the fact disappear for good.
            kept.setdefault(c["slot"], {})[c["sig"]] = c["since"]
    st["conditions"] = kept
    out["remembered"] = _write(st, root)
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
