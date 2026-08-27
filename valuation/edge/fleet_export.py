"""BACK UP THE FLEET RECORD STREAMS — the second dataset here that cannot be rebuilt.

    python -m valuation.edge.fleet_export            # print the payload
    GET/POST /admin/export-fleet                     # the same payload, off the service

**WHY THIS EXISTS, AND IT IS `track_export`'s ARGUMENT WORD FOR WORD.** This project holds two
datasets that cannot be re-derived from anything: the contract-bound forward track, and the
fleet's append-only record streams. Until now **only the first was protected.** The second is
the one about to accrue five years of evidence, and it lives on a Render disk that no GitHub
runner can read and that cannot itself commit to git. So the backup crosses the gap exactly the
way the track's does: a weekly workflow GETs an admin-token endpoint and commits what it
renders.

**DELIBERATELY RAW.** Rows as they are on disk, per book, with the header they were written
under — not a summary. A summary cannot be un-summarised later, and the point of a backup is to
be able to reconstruct the record. The hash chain is *included as data*, so a restored stream
can be re-verified against the declaration rather than trusted.

**THE HIGH-WATER MARKS TRAVEL WITH IT, AND THAT IS THE HALF THAT MAKES A RESTORE HONEST.**
`fleet_highwater` keeps the highest `seq` ever seen for each book beside the streams, so a
single lost CSV is caught on the next write. A lost DIRECTORY takes the marks with it — and
then this export is the only remaining evidence that the books ever had more rows than the disk
now shows. Backup protects against loss; the mark makes loss visible; each covers the other's
blind spot and neither is sufficient alone.

**IT IS A PURE READ.** It writes nothing, records nothing, and advances no mark. A backup route
that mutated the thing it is backing up would be the `PT-WRITER` side-effecting-GET defect in a
new place.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys

SCHEMA = "fleet_export/1"


def payload(root: str = None, generated_at: str = None) -> dict:
    """Every book's stream, its chain verdict, and the high-water marks. Pure read."""
    from . import fleet as F
    from . import fleet_highwater as HW

    fdir = F.fleet_dir(root)
    out = {
        "schema": SCHEMA,
        "generated_at": generated_at or _dt.datetime.now(_dt.timezone.utc).replace(
            tzinfo=None).isoformat(timespec="seconds"),
        "what_this_is": (
            "Append-only record streams for the declared fleet books, plus the high-water "
            "marks that make a lost stream visible. Paper only - Tradier sandbox, no real "
            "money. This file exists because these streams cannot be reconstructed if they "
            "are lost."),
        "fleet_dir": fdir,
        "books": {},
        "highwater": HW.summary(fdir),
    }

    # A STABLE SHAPE EVEN WHEN THERE IS NOTHING TO EXPORT. A consumer that has to distinguish
    # "no books" from "the key was missing" will eventually get it wrong, and a backup job is
    # exactly the unattended consumer that cannot ask.
    out["n_books"] = 0
    out["n_rows_total"] = 0
    out["reason"] = ""
    if not os.path.isdir(fdir):
        out["reason"] = "no fleet directory at " + fdir
        return out

    for fn in sorted(os.listdir(fdir)):
        if not fn.endswith(".csv"):
            continue
        book = fn[:-len(".csv")]
        rd = F.read_records(book, root)
        if not rd["ok"]:
            out["books"][book] = {"ok": False, "reason": rd["reason"]}
            continue
        # The chain verdict is RECORDED, not asserted: a backup of a stream that was already
        # broken must say so, or a restore silently reinstates the break as if it were sound.
        chain = F.verify_chain(book, root)
        out["books"][book] = {
            "ok": True,
            "columns": rd["columns"],
            "rows": rd["rows"],
            "n_rows": len(rd["rows"]),
            "max_seq": HW.observed_max(rd["rows"]),
            "chain": {k: chain.get(k) for k in
                      ("ok", "vacuous", "n", "broken_at", "reason", "head")},
        }
    out["n_books"] = len(out["books"])
    out["n_rows_total"] = sum(b.get("n_rows") or 0 for b in out["books"].values())
    return out


OUT_DIR = "data_export"
RECORDS_SUBDIR = "fleet_records"
MARKS_FILE = "fleet_highwater.json"


def write(pay: dict, out_dir: str = OUT_DIR) -> dict:
    """Render a payload into plain files under `out_dir`. Deterministic.

    One CSV per book plus the marks, rather than one big JSON: a CSV diffs, and a restore is a
    file copy. The track's backup makes the same choice for the same reason.
    """
    import csv

    rec_dir = os.path.join(out_dir, RECORDS_SUBDIR)
    os.makedirs(rec_dir, exist_ok=True)
    written = []
    for book, b in sorted((pay.get("books") or {}).items()):
        if not b.get("ok"):
            continue
        cols = list(b.get("columns") or [])
        path = os.path.join(rec_dir, "%s.csv" % book)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in (b.get("rows") or []):
                w.writerow({c: r.get(c, "") for c in cols})
        written.append(path)

    marks = os.path.join(out_dir, MARKS_FILE)
    with open(marks, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pay.get("highwater") or {}, f, indent=2, sort_keys=True)
        f.write("\n")
    written.append(marks)
    return {"ok": True, "written": written, "n_books": len(written) - 1}


def guard_counts(out_dir: str = OUT_DIR) -> dict:
    """Rows per book in a RENDERED backup, for the workflow's anti-regression check.

    Counted from the files on disk rather than from the payload, because what the guard must
    compare is what would be COMMITTED.
    """
    rec_dir = os.path.join(out_dir, RECORDS_SUBDIR)
    out = {"books": {}, "n_books": 0, "n_rows_total": 0}
    if not os.path.isdir(rec_dir):
        return out
    for fn in sorted(os.listdir(rec_dir)):
        if not fn.endswith(".csv"):
            continue
        path = os.path.join(rec_dir, fn)
        with open(path, encoding="utf-8", newline="") as f:
            n = max(0, sum(1 for _ in f) - 1)          # minus the header
        out["books"][fn[:-4]] = n
        out["n_rows_total"] += n
    out["n_books"] = len(out["books"])
    return out


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-json", dest="from_json",
                    help="a payload previously fetched from /admin/export-fleet")
    ap.add_argument("--out", default=None, help="render into this directory")
    ap.add_argument("--guard-against", dest="guard",
                    help="a directory holding the previously committed backup; the render "
                         "REFUSES if any book comes back with fewer rows than it has there")
    a = ap.parse_args(argv)

    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            body = json.load(f)
        pay = body.get("export") if isinstance(body, dict) and "export" in body else body
    else:
        pay = payload()

    if not a.out:
        print(json.dumps(pay, indent=2, sort_keys=True))
        return 0

    # THE GUARD IS RELATIVE AND IS NOT THE ONLY DEFENCE. `LA2` measured what a relative guard
    # alone misses: zero is never fewer than zero, so a series that had never been backed up at
    # all stayed green for months. The workflow pairs this with an ABSOLUTE presence check.
    before = guard_counts(a.guard) if a.guard else {"books": {}}
    res = write(pay, a.out)
    after = guard_counts(a.out)
    lost = {b: (n, after["books"].get(b, 0)) for b, n in (before["books"] or {}).items()
            if after["books"].get(b, 0) < n}
    if lost:
        print("::error::the fleet backup came back SHORTER than the committed copy: "
              + ", ".join("%s %d -> %d" % (b, was, now) for b, (was, now) in sorted(lost.items())))
        return 1
    print("fleet backup rendered: %d book(s), %d row(s)"
          % (after["n_books"], after["n_rows_total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
