"""ONE append-only CSV writer, keyed on a column the caller names.

WHY THIS MODULE EXISTS, AND IT IS NOT A TIDY-UP.
------------------------------------------------------------------------------------------
`index_mark.append_row` grew the project's append-only rules against the contract-bound track
history, and its own docstring names the hazard of a second copy: *"a second write
implementation for the strict case is the B7 split this module already warns about."*

`S3-I1`'s fleet books need exactly those rules and CANNOT use that function, because it is
keyed on `date` and a fleet book records **many orders per day**. Under `append_only=True` a
duplicate date is a NO-OP returning the row already on disk; in the default mode it is a
REPLACEMENT. Either way the second fill of a day disappears, and it disappears in the
direction that reads as a quiet book rather than as an error.

So the rules move here, once, with the key as a parameter, and both callers delegate. `MA5`'s
pattern (four copies of one hurdle, consolidated) and `I-3`'s (MA28's verdict machinery,
extracted and proved unmoved before anything new used it).

THE RULES, all of which are `MA4`'s or the PT contract's and none of which are new here:

1. **Temp file + `os.replace`, never in place.** `open(path, "w")` truncates first, so an
   interruption between truncate and flush leaves the file empty or partial. Renaming over
   the original means a failed write leaves the PREVIOUS file intact — which is also why no
   separate pre-write copy is taken: the original *is* the copy until the rename succeeds.
2. **The header is the UNION of what is on disk with `columns`, never a projection onto it.**
   Re-writing each historical row under `columns` alone would delete any column the file had
   gained, from *every row*, on the first append, silently.
3. **A key on the incoming row that is in neither the file nor `columns` is NOT written** and
   comes back in `ignored_fields` rather than being dropped in silence. Widening a schema
   should be a deliberate edit, not a caller's typo.
4. **A ragged file is REFUSED, not normalised.** `csv.DictReader` files surplus cells under a
   single key and pads short rows, so rewriting a file whose rows do not match its header
   would quietly discard or invent cells. Refusing leaves a gap, which a reader can see;
   normalising loses data that nothing can recover.
5. **`append_only=True` is the unattended writer's mode** and is strictly narrower: a
   duplicate key is a NO-OP returning the row ALREADY ON DISK (never the freshly computed
   one — they can differ); a key at or before the last recorded one is REFUSED; a schema
   change is REFUSED.
6. **The guarantee is byte-level.** After an `append_only` write the file's previous bytes are
   still an exact prefix of the new file. `.github/workflows/track-row.yml` verifies precisely
   that with `cmp` on `head -n N`, so a guarantee stated in weaker terms would be untestable
   against the check that already exists.

THE ORDERING OF THE `append_only` CHECKS IS LOAD-BEARING and is preserved exactly as
`index_mark` had it: idempotency is tested FIRST, because a key is not strictly greater than
itself, so a second write would otherwise be REFUSED as a backfill rather than answered as the
no-op a retrying scheduler needs.

WHAT THIS MODULE DOES NOT DO: it does not decide *whether* to write, it does not know what any
column means, and it computes nothing. It is a writer.
"""
from __future__ import annotations

import csv
import os
from typing import Callable, Iterable, Optional

# Surplus cells land under this key and short rows are padded with this sentinel; both are how
# a ragged file is DETECTED rather than silently normalised (rule 4).
RESTKEY = "__surplus_cells__"
RESTVAL = object()


def _identity(row: dict) -> dict:
    return row


def read_rows(path: str) -> tuple:
    """`(rows, header, error)`. A ragged file is reported, never repaired.

    Returned separately from `append` so a reader can check integrity without writing, which
    is what the fleet's chain verification and the day-1 self-check both need.
    """
    try:
        with open(path, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f, restkey=RESTKEY, restval=RESTVAL)
            rows = [r for r in rd]
            header = [c for c in (rd.fieldnames or []) if c]
    except FileNotFoundError:
        return [], [], None
    except Exception as e:                                   # noqa: BLE001
        return None, None, "could not read " + str(path) + ": " + str(e)
    for i, r in enumerate(rows):
        if RESTKEY in r or any(v is RESTVAL for v in r.values()):
            return None, None, ("refusing to rewrite " + str(path) + ": data row "
                                + str(i + 2) + " does not match its header, so a rewrite "
                                "would discard or invent cells. Repair the file by hand.")
    return rows, header, None


def append(row: dict, path: str, *, key: str, columns: Iterable[str],
           append_only: bool = False,
           typer: Optional[Callable[[dict], dict]] = None,
           backfill_hint: str = "") -> dict:
    """Append (or replace) one row, idempotently on `key`. See the module docstring.

    `backfill_hint` is appended to the append-only backward refusal so a caller can point at
    the deliberate door its own contract provides. It carries no behaviour.
    """
    typer = typer or _identity
    columns = list(columns)
    if not row or not row.get(key):
        return {"ok": False, "reason": "no row to append", "wrote": False}

    existing, on_disk, err = read_rows(path)
    if err:
        return {"ok": False, "reason": err, "wrote": False}

    fields = list(columns) + [c for c in on_disk if c not in columns]
    ignored = sorted(k for k in row if k not in fields)

    keys_on_disk = [(r.get(key) or "").strip() for r in existing]
    keys_on_disk = [k for k in keys_on_disk if k]

    if append_only:
        # Idempotency FIRST -- see the module docstring. A key is not strictly greater than
        # itself, so the reverse order turns the retry case into an error.
        if row[key] in keys_on_disk:
            was = next(r for r in existing if (r.get(key) or "").strip() == row[key])
            return {"ok": True, "wrote": False, "already_present": True,
                    "replaced": False, "reason": "",
                    "existing": typer({k: was.get(k) for k in fields}),
                    "path": path, "rows": len(existing), "columns": fields,
                    "ignored_fields": ignored}
        if keys_on_disk and row[key] <= max(keys_on_disk):
            return {"ok": False, "wrote": False, "already_present": False,
                    "would_modify": True,
                    "reason": ("refusing to write " + row[key] + " into " + str(path)
                               + ": the series already reaches " + max(keys_on_disk)
                               + ", and this door is append-only." + backfill_hint)}
        if on_disk and fields != on_disk:
            return {"ok": False, "wrote": False, "already_present": False,
                    "reason": ("refusing to widen the header of " + str(path)
                               + " on an append-only write: on disk " + ",".join(on_disk)
                               + " against " + ",".join(fields)
                               + ". Rewriting every line cannot preserve the byte prefix the "
                                 "append-only check verifies; make a schema change "
                                 "deliberately, in the repo.")}

    kept = [r for r in existing if (r.get(key) or "").strip() != row[key]]
    replaced = len(kept) != len(existing)
    kept.append({k: row.get(k) for k in fields})
    kept.sort(key=lambda r: (r.get(key) or ""))

    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in kept:
                w.writerow({k: r.get(k) for k in fields})
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception as e:                                   # noqa: BLE001
        try:
            os.remove(tmp)
        except OSError:
            pass
        return {"ok": False, "wrote": False,
                "reason": "could not write " + str(path) + ": " + str(e)}
    return {"ok": True, "reason": "", "wrote": True, "replaced": replaced,
            "path": path, "rows": len(kept), "columns": fields,
            "ignored_fields": ignored}
