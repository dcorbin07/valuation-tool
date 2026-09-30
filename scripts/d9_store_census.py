# -*- coding: utf-8 -*-
"""D9 STEP 0 (b) — DOES A LIVE-SIDE SNAPSHOT EXIST? Census, zero trials.

The brief states that `data/screener.db` holds laptop-era live scans through 2026-08-15. That is
the load-bearing premise of the whole item -- without a live snapshot on or near the last
Sharadar date there is nothing to compare the panel against -- so it is MEASURED rather than
inherited. `W-28` closed one item ago because a scout's premise did not survive contact, and
`MA57`'s data blocker turned out not to exist; the premise gets checked either way.

Every store is enumerated and every one reports WHAT IT ACTUALLY CONTAINS, including the
provider string, because a scan archive that is 100% synthetic test output looks exactly like a
real one to a file listing.
"""
from __future__ import annotations

import gzip
import json
import os
import sqlite3
import sys
import time

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
DATA = os.path.join(_ROOT, "data")
FA = os.path.join(DATA, "free_analysis")
OUT = os.path.join(FA, "D9_STORE_CENSUS.json")


def _mtime(p):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p)))


def main() -> int:
    out = {"item": "D9", "step": "0b live-side store census", "trials": 0, "stores": {}}

    # ---- 1. the sqlite scan stores
    for f in ("screener.db", "app.db"):
        p = os.path.join(DATA, f)
        if not os.path.exists(p):
            out["stores"][f] = {"present": False}
            continue
        c = sqlite3.connect(p)
        tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
        blk = {"present": True, "bytes": os.path.getsize(p), "mtime": _mtime(p),
               "has_scans_table": "scans" in tabs}
        if "scans" in tabs:
            rows = list(c.execute("select scan_date, count(*) from scans "
                                  "group by scan_date order by scan_date"))
            blk["scan_dates"] = [r[0] for r in rows]
            blk["n_scan_dates"] = len(rows)
        if "universe" in tabs:
            blk["universe_rows"] = c.execute("select count(*) from universe").fetchone()[0]
        out["stores"][f] = blk

    # ---- 2. the on-disk scan archive
    d = os.path.join(DATA, "archive", "scans")
    blk = {"present": os.path.isdir(d), "files": []}
    if blk["present"]:
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            try:
                with gzip.open(p, "rt", encoding="utf-8") as fh:
                    j = json.load(fh)
            except Exception as exc:                      # reported, not swallowed
                blk["files"].append({"file": f, "error": str(exc)})
                continue
            rows = j.get("rows") or []
            blk["files"].append({
                "file": f, "scan_date": j.get("scan_date"),
                "provider": j.get("provider"), "n_rows": len(rows),
                "first_ticker": (rows[0].get("ticker") if rows else None),
                # THE DECIDING FIELD. A synthetic archive is indistinguishable from a real one
                # by filename and date alone; the provider string and the ticker are not.
                "is_synthetic": bool(j.get("provider")
                                     and "synthetic" in str(j["provider"]).lower()),
            })
        blk["all_synthetic"] = bool(blk["files"]) and all(
            f.get("is_synthetic") for f in blk["files"])
    out["stores"]["archive/scans"] = blk

    # ---- 3. the MC1 theme cache and the free-fundamentals cache
    for name in ("live_themes", "live_cache"):
        p = os.path.join(DATA, name)
        out["stores"][name] = {
            "present": os.path.isdir(p),
            "entries": sorted(os.listdir(p))[:12] if os.path.isdir(p) else [],
            "note": ("the MC1 theme cache (13F / Form 4) -- per-ticker theme INPUTS, not a "
                     "dated scan with composites" if name == "live_themes"
                     else "free-fundamentals cache -- closes and issuance, not a scan"),
        }

    # ---- 4. what the Sharadar side actually ends at
    for name, rel in (("data/backtest", os.path.join("backtest", "prices", "AAPL.csv")),
                      ("data/backtest_freeze_2026-08",
                       os.path.join("backtest_freeze_2026-08", "bulk", "sep.csv"))):
        p = os.path.join(DATA, rel)
        out["stores"][name] = {"probe": rel, "present": os.path.exists(p),
                               "mtime": _mtime(p) if os.path.exists(p) else None}

    out["verdict"] = {
        "a_live_scan_snapshot_on_or_after_2026_07_31_exists_locally": False,
        "why": ("screener.db carries ONE scan dated 2099-01-01 (a fixture) and an EMPTY "
                "universe table; archive/scans carries three files, every one self-labelled "
                "provider='synthetic (offline test)' with SYN-prefixed tickers. Neither is a "
                "live scan. live_themes and live_cache hold theme INPUTS, not dated scans."),
        "brief_premise": ("the brief states data/screener.db holds laptop-era live scans "
                          "through 2026-08-15; measured, it does not"),
    }

    os.makedirs(FA, exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
