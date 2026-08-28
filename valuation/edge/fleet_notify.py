"""ANNOUNCE A FILL, AND A REFUSAL THAT IS NEW — the fleet was invisible until it spoke.

Eighteen books accrue records and nothing announced anything: Don learned what the fleet did
by opening JSON, which means in practice he did not learn it. This is the Discord path the
other workflows already use (`saas.notify.send_discord`), reused rather than rebuilt.

**FILLS ALWAYS, AND DEDUPED BY `seq`.** A fill is a discrete event and every one is worth a
line. The cycle door can legitimately run twice — a retry, a manual dispatch — so the last
announced sequence number is remembered per book and only rows past it are announced. Without
that, the second run of a quiet day re-announces the same fill and the alert starts lying.

**REFUSALS ONLY WHEN THEY CHANGE, AND THAT IS NOT A SOFTENING OF THE RULE.** A book that
cannot fill is the failure worth knowing about the same day — so a book that BECOMES blocked,
or becomes blocked for a NEW reason, announces immediately. What must not announce is the
steady state: today eighteen books are blocked on the same self-check, so a cycle that
announced every refusal would post the same eighteen lines every evening, and an alert that
says the same thing every day is one you stop reading. Then the day it changes, nobody
notices. The signature is `(book, code)`, so a book that moves from one refusal to another is
news and a book sitting in the same one is not.

**A QUIET CYCLE STAYS QUIET.** No fills and no changed refusals sends nothing at all — not a
"nothing to report" line, which is the same noise wearing a politer hat.

**IT NEVER RAISES AND ITS FAILURE IS NEVER THE CYCLE'S.** A missing webhook, a Discord outage
or an unwritable state file all return a reason and leave the records untouched. The fleet
recording a fill is the thing that matters; telling someone about it is strictly secondary, and
a notifier that could take the cycle down with it would have inverted that.

**IT ANNOUNCES WHAT HAPPENED, NEVER HOW IT IS GOING.** No P&L, no running total, no verdict —
those have pre-committed horizons and a Discord line is not where they get read early.
"""
from __future__ import annotations

import json
import os
from typing import Optional

SCHEMA = "fleet_notify/1"
STATE_FILENAME = "_notified.json"

#: Never a figure that could read as performance. A fill line says what was bought or sold and
#: at what price -- the logbook facts -- and nothing about what it is worth now.
FILL_FIELDS = ("book", "seq", "symbol", "occ", "side", "qty", "fill_price", "arm")


def state_path(fleet_dir: str) -> str:
    return os.path.join(fleet_dir, STATE_FILENAME)


def _read(fleet_dir: str) -> dict:
    try:
        with open(state_path(fleet_dir), encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and raw.get("schema") == SCHEMA:
            return raw
    except Exception:                                                  # noqa: BLE001
        pass
    return {"schema": SCHEMA, "last_seq": {}, "refusals": {}}


def _write(fleet_dir: str, state: dict) -> bool:
    tmp = state_path(fleet_dir) + ".tmp"
    try:
        os.makedirs(fleet_dir, exist_ok=True)
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, state_path(fleet_dir))
        return True
    except Exception:                                                  # noqa: BLE001
        return False


def _seq(row) -> int:
    try:
        return int(str((row or {}).get("seq") or "0").strip())
    except (TypeError, ValueError):
        return 0


def pending(rows_by_book: dict, refusals: dict, fleet_dir: str) -> dict:
    """What is NEW since the last announcement. Pure — reads state, writes none.

    `rows_by_book`: {book: [record rows]}.  `refusals`: {book: code} for books that cannot
    fill right now.
    """
    st = _read(fleet_dir)
    last, known = st.get("last_seq") or {}, st.get("refusals") or {}

    fills = []
    for book, rows in sorted((rows_by_book or {}).items()):
        try:
            floor = int(last.get(book) or 0)
        except (TypeError, ValueError):
            floor = 0
        for r in (rows or []):
            if (r.get("kind") or "") != "fill" or _seq(r) <= floor:
                continue
            item = {k: r.get(k) for k in FILL_FIELDS if k != "book"}
            item["book"] = book
            item["seq"] = _seq(r)
            fills.append(item)

    new_refusals = []
    for book, code in sorted((refusals or {}).items()):
        if known.get(book) != code:
            new_refusals.append({"book": book, "code": code})
    # A book that STOPS being refused is also a change worth one line: it means a gate that
    # was closed has opened, which is the good half of the same fact.
    cleared = [{"book": b} for b in sorted(known) if b not in (refusals or {})]

    return {"fills": fills, "new_refusals": new_refusals, "cleared": cleared,
            "quiet": not (fills or new_refusals or cleared)}


def compose(p: dict) -> str:
    """The message. Facts only — no total, no P&L, no verdict."""
    lines = []
    if p["fills"]:
        lines.append("**Fleet fills** (paper, sandbox — a logbook entry, not a result)")
        for f in p["fills"][:20]:
            bits = [x for x in (f.get("side"), str(f.get("qty") or ""), f.get("occ")
                                or f.get("symbol")) if x]
            px = f.get("fill_price")
            lines.append("- `%s` %s%s" % (f["book"], " ".join(bits),
                                          (" @ %s" % px) if px else ""))
        if len(p["fills"]) > 20:
            lines.append("- ...and %d more" % (len(p["fills"]) - 20))
    if p["new_refusals"]:
        lines.append("**Newly unable to fill**")
        for r in p["new_refusals"]:
            lines.append("- `%s` — %s" % (r["book"], r["code"]))
    if p["cleared"]:
        lines.append("**No longer blocked**: " + ", ".join("`%s`" % c["book"]
                                                           for c in p["cleared"]))
    return "\n".join(lines)


def announce(rows_by_book: dict, refusals: dict, fleet_dir: str, *, cfg=None,
             send=None) -> dict:
    """Send if there is something new, then remember what was said. Never raises."""
    p = pending(rows_by_book, refusals, fleet_dir)
    out = {"sent": False, "quiet": p["quiet"], "reason": "",
           "n_fills": len(p["fills"]), "n_new_refusals": len(p["new_refusals"]),
           "n_cleared": len(p["cleared"])}
    if p["quiet"]:
        out["reason"] = "nothing new to announce"
        return out

    body = compose(p)
    try:
        if send is None:
            from ..saas.notify import send_discord as send
        ok = bool(send(cfg, body))
    except Exception as e:                                             # noqa: BLE001
        ok, out["reason"] = False, "the webhook failed (%s)" % type(e).__name__
    out["sent"] = ok
    if not ok and not out["reason"]:
        out["reason"] = "no webhook configured, or it declined"

    # STATE MOVES ONLY ON A SUCCESSFUL SEND. A failed post that advanced the watermark would
    # lose the very fill it failed to announce, silently and permanently.
    if ok:
        st = _read(fleet_dir)
        last = dict(st.get("last_seq") or {})
        for f in p["fills"]:
            last[f["book"]] = max(int(last.get(f["book"]) or 0), int(f["seq"]))
        st["last_seq"] = last
        st["refusals"] = dict(refusals or {})
        out["remembered"] = _write(fleet_dir, st)
    return out
