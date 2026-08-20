"""
Build the SPMO reported-benchmark sibling series from the recorded bound track.  [`PT-SPMO`]

    python -m scripts.spmo_backfill                      # dry run: print what it would write
    python -m scripts.spmo_backfill --write              # write data/valquo_vs_spmo.csv
    python -m scripts.spmo_backfill --data <dir>         # point at another data directory

DRY RUN IS THE DEFAULT, deliberately. `scripts/track_row.py` makes `--append` opt-in for the
bound series and this is the same shape for its sibling: a command that writes by default is
one a reader runs to see what it does.

IT NEVER TOUCHES THE BOUND FILE. The Valquo leg is COPIED out of `valquo_track_history.csv`
as raw cell text and nothing is written back to it -- `valuation/screener/reported_benchmark.py`
explains why the sibling is a separate file rather than an extra column, and a test
byte-compares the bound file across a full backfill.

THIS IS NOT THE SERVICE'S COPY. `data/` is gitignored, so a local run produces a local file;
the authority is whatever the running service holds, exactly as it is for the bound series
after a seed. The live door backfills the sibling itself on first use, so this command is for
inspecting the derivation rather than for feeding production.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.screener import reported_benchmark as rb   # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--write", action="store_true",
                    help="actually write the sibling CSV and its derivation note")
    ap.add_argument("--data", default=None,
                    help="directory holding valquo_track.json and valquo_track_history.csv")
    a = ap.parse_args(argv)

    meta = hist = None
    if a.data:
        meta = os.path.join(a.data, "valquo_track.json")
        hist = os.path.join(a.data, "valquo_track_history.csv")

    res = rb.backfill(meta_path=meta, bound_history_path=hist, write=a.write)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2, default=str))
    for r in res.get("rows") or []:
        print(json.dumps(r, default=str))
    if not res.get("ok"):
        print("REFUSED: " + str(res.get("reason")), file=sys.stderr)
        return 1
    if not a.write:
        print("\n(dry run — nothing written. Re-run with --write.)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
