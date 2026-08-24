"""
S3-I2 — run the catalyst-calendar scraper and APPEND one observation.

    python -m scripts.s3i2_catalyst_scrape [--out <json>] [--dry-run]

Collection-and-provenance, zero trials. Safe to run on a schedule: it appends, never rewrites,
so running it twice a day costs two snapshots and loses nothing. Running it never is the only
way to lose data, because the free surfaces do not keep history either.

The store is APPEND-ONLY on purpose. What makes this table worth anything later is not the
current calendar -- anyone can reload the website -- it is the record of WHAT WAS PUBLISHED ON
WHICH DAY, which is the only form of it that can support a point-in-time study. Rewriting a
snapshot to "correct" it would destroy exactly the thing being accrued.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import catalyst_calendar as CC                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO, "data", "catalysts", "CATALYST_CALENDAR.json")


def main(argv=None):
    ap = argparse.ArgumentParser(description="S3-I2 catalyst calendar (forward-only)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    ap.add_argument("--mirror", default=r"D:\thetadata\catalysts",
                    help="second copy of the store; '' to skip")
    ap.add_argument("--summary", default=os.path.join(REPO, "CATALYST_CALENDAR_SUMMARY.json"),
                    help="TRACKED provenance summary (counts only, no vendor rows)")
    a = ap.parse_args(argv)

    fetches, rows = [], []
    for sid in CC.SOURCES:
        f = CC.fetch(sid)
        print(f"[s3i2] {sid:26s} {f['status']:12s} "
              f"{f.get('http') or '-'} {f.get('error', '')[:60]}", flush=True)
        if f["status"] == CC.STATUS_OK and sid in CC.PARSERS:
            try:
                r, meta = CC.PARSERS[sid](f.pop("_body"))
                f["parsed_rows"] = len(r)
                f["source_meta"] = meta
                if not r:
                    f["status"] = CC.STATUS_EMPTY      # reached and empty is a real observation
                rows.extend(r)
            except Exception as e:                                      # noqa: BLE001
                f["status"] = CC.STATUS_UNREACHABLE
                f["error"] = f"parse failed: {type(e).__name__}: {str(e)[:160]}"
        f.pop("_body", None)
        fetches.append(f)

    cal = CC.CatalystCalendar.load(a.out)
    prior = len(cal.snapshots)
    cal.add_snapshot(fetches, rows)
    cov = cal.coverage()

    print()
    print(json.dumps(cov, indent=1))
    if a.dry_run:
        print("[s3i2] --dry-run: nothing written")
        return cov
    cal.save(a.out)
    print(f"\n[s3i2] snapshot {prior} -> {len(cal.snapshots)} appended, wrote {a.out}")
    print(f"[s3i2] forward day-precision rows: {len(cal.forward_rows())}")

    # SECOND COPY + TRACKED SUMMARY. This store CANNOT BE REBUILT: the free surfaces publish a
    # current calendar and keep no history, so a lost snapshot is lost permanently -- unlike the
    # chain harvest, which was at least re-fetchable until a deadline. `data/` is gitignored, so
    # left alone the only copy of an irreplaceable record would sit on one drive.
    #
    # The payload stays out of git deliberately: it is third-party content under an
    # attribution licence, and a growing daily dump does not belong in a source repo. What IS
    # tracked is the provenance summary -- counts, source states, snapshot dates and the store's
    # sha256 -- which contains no vendor rows and makes a lost or silently-truncated store loud.
    import hashlib
    import shutil
    with open(a.out, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    if a.mirror:
        try:
            os.makedirs(a.mirror, exist_ok=True)
            shutil.copy2(a.out, os.path.join(a.mirror, os.path.basename(a.out)))
            print(f"[s3i2] mirrored to {a.mirror}")
        except OSError as e:
            print(f"[s3i2] MIRROR FAILED ({type(e).__name__}) -- the store has ONE copy", flush=True)
    if a.summary:
        summ = {
            "instrument": "S3-I2",
            "trials": 0,
            "store": os.path.relpath(a.out, REPO).replace("\\", "/"),
            "store_sha256": digest,
            "store_bytes": os.path.getsize(a.out),
            "mirror": a.mirror or None,
            "n_snapshots": len(cal.snapshots),
            "first_observed_utc": cal.snapshots[0]["observed_utc"],
            "latest_observed_utc": cal.snapshots[-1]["observed_utc"],
            "coverage": cov,
            "sources": {k: {"url": v["url"], "kind": v["kind"], "robots": v.get("robots"),
                            "license": v.get("license")} for k, v in CC.SOURCES.items()},
            "history_note": ("Forward-only. No history exists or can be created; the record "
                             "accrues one day per day from the first snapshot."),
        }
        with open(a.summary, "w", encoding="utf-8") as fh:
            json.dump(summ, fh, indent=1)
        print(f"[s3i2] wrote tracked summary {a.summary}")
    return cov


if __name__ == "__main__":
    main()
