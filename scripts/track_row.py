"""
Print (or append) today's contract row for the bound Valquo Index forward track.

THIS IS THE ANSWER TO `PT-WRITER`. The recorder lane's dated refusal of 2026-08-10 said it
could not write a row without "a documented price-fetching mechanism", and would not guess
at a vendor. `valuation/screener/index_mark.py` is that mechanism; this is its command line.

    python -m scripts.track_row                 # print today's row as JSON
    python -m scripts.track_row --csv           # print it as the CSV line the recorder wants
    python -m scripts.track_row --append        # write it into data/valquo_track_history.csv
    python -m scripts.track_row --date 2026-08-12   # backfill one past trading day

EXIT CODES ARE THE POINT, because this is meant to run unattended:

    0  a row was produced (and appended, if asked)
    2  REFUSED — no row exists for this date and the reason is on stderr and in the JSON

Exit 2 is not an error to retry blindly; it is the mechanism declining to invent data. The
common and entirely normal case is "the session has not closed yet". A scheduler that
treats 2 as a hard failure will page somebody every weekend.

NOTHING HERE DECIDES POLICY. It does not schedule itself, and `--append` is opt-in — whether
the bound series gets written, and when, is the recorder lane's call under
PAPER_TRACK_CONTRACT.md section 7.2.
"""
from __future__ import annotations

import argparse
import json
import sys

from valuation.screener import index_mark


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--date", default=None,
                    help="mark this trading day instead of today (YYYY-MM-DD)")
    ap.add_argument("--append", action="store_true",
                    help="write the row into the recorded CSV (idempotent: rewrites its date)")
    ap.add_argument("--csv", action="store_true", help="print the CSV line instead of JSON")
    ap.add_argument("--book", default=None,
                    help=("override the book/meta path (default: data/valquo_track.json). "
                          "Needed when the recorder runs from a git worktree or any checkout "
                          "whose data/ is not the one holding the bound track — data/ is "
                          "gitignored, so that is the normal case, not the exception."))
    ap.add_argument("--history", default=None, help="override the history CSV path")
    ap.add_argument("--allow-open-session", action="store_true",
                    help=("do not refuse before the close. Marking an unclosed session writes "
                          "an intraday quote under a closing-price column; only use this to "
                          "backfill a day that has already ended."))
    a = ap.parse_args(argv)

    res = index_mark.contract_row(a.date, meta_path=a.book,
                                  refuse_before_close=not a.allow_open_session)
    if not res.get("ok"):
        print("REFUSED: " + str(res.get("reason")), file=sys.stderr)
        print(json.dumps(res, indent=2, default=str))
        return 2

    row = res["row"]
    if a.csv:
        print(",".join(index_mark.ROW_COLUMNS))
        print(",".join(str(row.get(k)) for k in index_mark.ROW_COLUMNS))
    else:
        print(json.dumps(res, indent=2, default=str))

    if a.append:
        wrote = index_mark.append_row(row, a.history)
        if not wrote.get("ok"):
            print("APPEND FAILED: " + str(wrote.get("reason")), file=sys.stderr)
            return 2
        verb = "replaced" if wrote.get("replaced") else "appended"
        print(verb + " " + row["date"] + " -> " + str(wrote.get("path")), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
