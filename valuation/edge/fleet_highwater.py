"""THE HIGH-WATER MARK — make the loss of a fleet record stream VISIBLE.  [Audit #5 H3]

**THE DEFECT THIS EXISTS FOR, AND IT IS THE REASON A BACKUP ALONE DOES NOT CLOSE `H3`.**
Audit #5 measured that **whole-file loss is not a chain break**. Delete `data/fleet/<book>.csv`
and the book does not fail: it re-certifies, resumes at `seq 1`, and every subsequent row
chains correctly from the declaration hash. `verify_chain` returns `ok` on the survivors
because the survivors really are internally consistent. **A tamper-evident record that silently
heals over its own data loss is worse than one that fails loudly**, because the healing is
indistinguishable from a book that simply started today.

The chain proves that the rows PRESENT are in the order they were written. It cannot prove that
rows are MISSING, and it never could: every fact it uses to check itself lives in the file that
was lost. So the counter-fact has to live somewhere else. That is all this module is — the
highest `seq` ever observed for a book, kept **outside the file it describes**, and compared on
every write.

    records                     high-water          verdict
    seq 1..40 present           40                  fine, and 40 is re-affirmed
    seq 1..41 present           40                  fine, high-water advances to 41
    file deleted, seq 1..2      40                  REFUSED, loudly, and it cannot heal

**BACKUP AND HIGH-WATER ARE DIFFERENT JOBS AND BOTH ARE NEEDED.** The weekly export protects
against loss; this makes loss VISIBLE. Neither substitutes for the other: a backup nobody
notices they need is restored a year late, and a high-water mark with no backup tells you
precisely what you can no longer recover.

**WHY A SIBLING FILE, AND THE HONEST LIMIT OF IT.** `data/fleet/_highwater.json` sits beside
the streams rather than inside any of them, so it survives the deletion, truncation or
re-creation of any single book's CSV — which is the failure the audit actually measured. It
does **not** survive the loss of the whole directory or the whole disk, and this module does not
pretend otherwise: `state()` reports `ABSENT` distinctly from `OK` so a vanished mark can never
read as a clean one. The layer that covers a whole-disk loss is the export and the weekly
backup, which carry these marks off the service into git.

**IT REFUSES EVERY KIND, INCLUDING A REFUSAL.** `fleet.record` is the only write door and the
check sits there, so nothing — not a fill, not a self-check, not a refusal row — can be appended
to a stream that has gone backwards. Letting a refusal through would append it to the very
stream whose integrity is in question and continue the false chain with an official-looking row.

**THERE IS NO RESET FUNCTION, ON PURPOSE.** Recovering from a real loss is a human decision
about evidence — restore from the backup, or accept the gap and say so in the record — and a
one-call `reset()` in this module is exactly the affordance that turns that decision into a
reflex. The refusal names the file and the two numbers; a person resolves it.
"""
from __future__ import annotations

import json
import os
import time as _time
from typing import Optional

SCHEMA = "fleet_highwater/1"
MARK_FILENAME = "_highwater.json"

#: The states, and `ABSENT` is the one that matters: a mark that is missing is not a mark that
#: is satisfied. `O21-D2`'s `C5` rule — a check that never ran and a check that passed must not
#: read the same.
OK = "OK"
ABSENT = "ABSENT"
UNREADABLE = "UNREADABLE"
FIRST_SIGHT = "FIRST_SIGHT"
REGRESSED = "REGRESSED"


def mark_path(fleet_dir: str) -> str:
    """Beside the streams, never inside one of them."""
    return os.path.join(fleet_dir, MARK_FILENAME)


def _read(fleet_dir: str) -> dict:
    path = mark_path(fleet_dir)
    if not os.path.exists(path):
        return {"ok": False, "state": ABSENT, "books": {},
                "reason": "no high-water mark on disk at " + path}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
            return {"ok": False, "state": UNREADABLE, "books": {},
                    "reason": "high-water mark has schema %r, expected %r"
                              % ((raw or {}).get("schema"), SCHEMA)}
        books = raw.get("books")
        if not isinstance(books, dict):
            return {"ok": False, "state": UNREADABLE, "books": {},
                    "reason": "high-water mark carries no books object"}
        return {"ok": True, "state": OK, "books": books, "reason": ""}
    except Exception as e:                                             # noqa: BLE001
        return {"ok": False, "state": UNREADABLE, "books": {},
                "reason": "high-water mark unreadable (%s)" % type(e).__name__}


def read(fleet_dir: str) -> dict:
    """The whole mark, or an explicit absence. Never raises."""
    return _read(fleet_dir)


def observed_max(rows) -> int:
    """The highest `seq` actually present in a stream. 0 for an empty one."""
    n = 0
    for r in (rows or []):
        try:
            n = max(n, int(str((r or {}).get("seq") or "0").strip()))
        except (TypeError, ValueError):
            continue
    return n


def state(book: str, rows, fleet_dir: str) -> dict:
    """Compare a stream against the mark. THE WHOLE POINT: a regression is loud.

    Returns `{"ok", "state", "observed", "mark", "reason"}`. `ok` is False for exactly two
    states — `REGRESSED`, the failure this module exists for, and `UNREADABLE`, because a mark
    that cannot be parsed may hold a HIGHER number than the stream does and treating it as
    absent would erase the only evidence of a loss.
    """
    obs = observed_max(rows)
    m = _read(fleet_dir)
    out = {"ok": False, "state": m["state"], "observed": obs, "mark": None,
           "reason": m.get("reason", ""), "path": mark_path(fleet_dir)}

    if m["state"] == UNREADABLE:
        return out
    if m["state"] == ABSENT:
        # A stream with rows and NO mark is REPORTED and does not block, and the reasoning is
        # worth stating because it bounds what this module claims. The failure the audit
        # measured is a stream that RESTARTS -- rows up to 40, then a file holding 1..2 -- and
        # that is caught by `obs < mark` below, because the mark is a different file and
        # survives. "Rows but no mark at all" is the whole-DIRECTORY loss, which takes the mark
        # with it; refusing here would buy nothing against that (the evidence is equally gone)
        # while bricking every legitimately hand-built stream. So it is surfaced as its own
        # state with `rows_present` set, and the layer that actually covers a directory loss is
        # the export and the weekly backup.
        out.update(ok=True, state=FIRST_SIGHT, rows_present=obs > 0)
        out["reason"] = (
            "no high-water mark yet; this stream is empty, so the next write establishes one"
            if obs == 0 else
            "stream %r holds rows up to seq %d and no high-water mark exists yet at %s. It is "
            "established on the next write. A directory restored without its mark reads like "
            "this, and this module cannot tell that apart from a first run -- the export and "
            "the weekly backup are what cover a whole-directory loss."
            % (book, obs, mark_path(fleet_dir)))
        return out

    entry = (m["books"] or {}).get(str(book))
    if not isinstance(entry, dict) or entry.get("max_seq") is None:
        out.update(ok=True, state=FIRST_SIGHT, mark=None,
                   reason="no high-water mark recorded for %r yet" % book)
        return out
    try:
        mark = int(entry["max_seq"])
    except (TypeError, ValueError):
        out.update(state=UNREADABLE,
                   reason="high-water mark for %r is not an integer" % book)
        return out

    out["mark"] = mark
    if obs < mark:
        out["reason"] = (
            "REFUSED: %r holds rows only up to seq %d but %d was already recorded. The chain "
            "cannot see this — every fact it checks itself with lived in the file that was "
            "lost, so a truncated stream re-chains cleanly and reads as a book that started "
            "today. Restore the stream from the backup, or accept the gap deliberately and "
            "say so in the record; do not delete %s to make this go away."
            % (book, obs, mark, mark_path(fleet_dir)))
        out["state"] = REGRESSED
        return out
    out.update(ok=True, state=OK)
    return out


def advance(book: str, seq, fleet_dir: str, *, ts: str = None) -> dict:
    """Raise the mark for `book` to `seq`. MONOTONIC: it never lowers one.

    Written after a successful append, so a write that failed does not move the mark forward
    past rows that are not on disk. The file is rewritten whole and atomically — it is a
    handful of integers, not a stream, so it has no append-only obligation of its own.
    """
    try:
        n = int(str(seq).strip())
    except (TypeError, ValueError):
        return {"ok": False, "reason": "seq %r is not an integer" % (seq,)}

    m = _read(fleet_dir)
    books = dict(m["books"]) if m["state"] in (OK,) else {}
    if m["state"] == UNREADABLE:
        # Refuse rather than overwrite: a mark we cannot parse may hold a HIGHER number than
        # the one we are about to write, and clobbering it would erase the only evidence of a
        # loss. `MA6`'s direction rule — the safe error is the one that over-reports.
        return {"ok": False, "reason": m["reason"], "state": UNREADABLE}

    prev = books.get(str(book)) or {}
    try:
        prev_max = int(prev.get("max_seq"))
    except (TypeError, ValueError):
        prev_max = 0
    books[str(book)] = {"max_seq": max(prev_max, n), "last_seen": ts or prev.get("last_seen")}

    path = mark_path(fleet_dir)
    tmp = path + ".tmp"
    # A BOUNDED RETRY ON THE RENAME, AND ONLY HERE. This module adds one extra small write per
    # append, and `CLAUDE.md` already records two independent sightings of `os.replace` losing
    # to sustained concurrent %TEMP% I/O on Windows -- suites that build real artifacts there
    # "wrap no I/O in a retry". Adding a write without absorbing its own share of that would
    # make a known flake more likely and leave the next lane to be blamed for it. This suite
    # hit exactly that on its first run.
    #
    # It is deliberately NOT added to `append_only`: that is the shared, safety-critical record
    # writer and is another lane's to change. Three attempts over ~300ms, then the honest
    # failure -- a retry that never gives up is a hang, not a fix.
    err = None
    for attempt in range(3):
        try:
            os.makedirs(fleet_dir, exist_ok=True)
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"schema": SCHEMA, "books": books}, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, path)
            return {"ok": True, "reason": "", "max_seq": books[str(book)]["max_seq"],
                    "path": path, "attempts": attempt + 1}
        except Exception as e:                                         # noqa: BLE001
            err = e
            _time.sleep(0.05 * (attempt + 1))
    return {"ok": False, "reason": "could not write %s after 3 attempts (%s)"
                                   % (path, type(err).__name__)}


def summary(fleet_dir: str) -> dict:
    """Every mark, for an export or a status body to carry. Read-only."""
    m = _read(fleet_dir)
    return {"ok": m["ok"], "state": m["state"], "reason": m.get("reason", ""),
            "path": mark_path(fleet_dir),
            "books": {k: v for k, v in sorted((m["books"] or {}).items())}}
