"""Per-symbol-year open-interest coverage audit for the mined options cache (audit item B4).

WHY THIS EXISTS. `-1` is the ThetaData feed's *unknown* open-interest sentinel. `theta_bulk`
writes it whenever the separate open-interest call faults or a contract has no OI record, and
until now it did so silently: the year was cached looking exactly like a clean one. B4 fixed the
two CONSUMERS of the sentinel; this is the coverage layer for the DATA, in the same spirit as
`signal_coverage()` on the equity side -- coverage says a factor is PRESENT, this says the open
interest in it is KNOWN.

Run it after any mining session:

    python oi_coverage_audit.py                 # scan, write OI_COVERAGE.json + .md
    python oi_coverage_audit.py --floor 0.95    # override the coverage floor
    python oi_coverage_audit.py --rescan        # ignore the checkpoint and redo every file

The JSON is committed so the -1 problem can never again be invisible.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge.theta_bulk import CACHE_ROOT, OI_COVERAGE_FLOOR, REPO_ROOT  # noqa: E402

# The CACHE lives in the primary checkout (gitignored, shared); the REPORT is committed code
# and must land beside this script, which may be a worktree.
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_JSON = os.path.join(HERE, "OI_COVERAGE.json")
REPORT_MD = os.path.join(HERE, "OI_COVERAGE.md")
CHECKPOINT = os.path.join(CACHE_ROOT, "_oi_audit_checkpoint.json")


def scan_one(path):
    """(key, rows, known_frac, min_oi, err). Runs in a worker process."""
    key = os.path.basename(path)[:-4]           # SYM-YYYY
    try:
        with open(path, "rb") as f:
            df = pickle.load(f)
    except Exception as e:                                               # noqa: BLE001
        return key, 0, None, None, f"{type(e).__name__}: {e}"
    if df is None or len(df) == 0:
        return key, 0, None, None, "empty frame"
    if "open_interest" not in df.columns:
        return key, int(len(df)), 0.0, None, "no open_interest column"
    oi = df["open_interest"]
    known = float((oi >= 0).mean())
    return key, int(len(df)), known, int(oi.min()), None


def year_files(root):
    out = []
    for sym in sorted(os.listdir(root)):
        d = os.path.join(root, sym)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".pkl") and "-" in fn:
                out.append(os.path.join(d, fn))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", type=float, default=OI_COVERAGE_FLOOR)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--rescan", action="store_true")
    args = ap.parse_args()

    files = year_files(CACHE_ROOT)
    print(f"[oi-audit] {len(files)} symbol-year files under {CACHE_ROOT}")

    done = {}
    if os.path.exists(CHECKPOINT) and not args.rescan:
        try:
            with open(CHECKPOINT, encoding="utf-8") as f:
                done = json.load(f)
            print(f"[oi-audit] resuming: {len(done)} already scanned")
        except (OSError, ValueError):
            done = {}

    todo = [p for p in files if os.path.basename(p)[:-4] not in done]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(scan_one, p): p for p in todo}
        for i, fu in enumerate(as_completed(futs), 1):
            key, rows, known, mn, err = fu.result()
            done[key] = {"rows": rows, "known": known, "min_oi": mn, "err": err}
            if i % 200 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"[oi-audit] {i}/{len(todo)}  {el:.0f}s", flush=True)
                with open(CHECKPOINT, "w", encoding="utf-8") as f:
                    json.dump(done, f)
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(done, f)

    # ---- aggregate -------------------------------------------------------------------------
    scored = {k: v for k, v in done.items() if v.get("known") is not None and v["rows"]}
    total_rows = sum(v["rows"] for v in scored.values())
    known_rows = sum(int(round(v["rows"] * v["known"])) for v in scored.values())
    bad = {k: v for k, v in scored.items() if v["known"] < args.floor}
    zero = {k: v for k, v in scored.items() if v["known"] == 0.0}

    by_name = {}
    for k, v in scored.items():
        sym = k.rsplit("-", 1)[0]
        a = by_name.setdefault(sym, {"rows": 0, "known_rows": 0, "years": 0, "bad_years": 0})
        a["rows"] += v["rows"]
        a["known_rows"] += int(round(v["rows"] * v["known"]))
        a["years"] += 1
        a["bad_years"] += 1 if v["known"] < args.floor else 0
    for a in by_name.values():
        a["known"] = (a["known_rows"] / a["rows"]) if a["rows"] else 0.0

    names_affected = sum(1 for a in by_name.values() if a["bad_years"])
    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cache_root": CACHE_ROOT,
        "floor": args.floor,
        "totals": {
            "symbol_years": len(scored),
            "names": len(by_name),
            "rows": total_rows,
            "rows_with_known_oi": known_rows,
            "rows_unknown_oi": total_rows - known_rows,
            "known_fraction": (known_rows / total_rows) if total_rows else 0.0,
            "symbol_years_below_floor": len(bad),
            "symbol_years_wholly_unknown": len(zero),
            "names_affected": names_affected,
        },
        "below_floor": {k: round(v["known"], 6) for k, v in
                        sorted(bad.items(), key=lambda kv: kv[1]["known"])},
        "by_name": {k: round(v["known"], 6) for k, v in sorted(by_name.items())},
        "errors": {k: v["err"] for k, v in done.items() if v.get("err")},
    }
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    t = report["totals"]
    lines = [
        "# OI_COVERAGE — open-interest coverage of the mined options cache",
        "",
        "Generated by `oi_coverage_audit.py` (audit item **B4**, writer side). `-1` is the feed's",
        "*unknown* sentinel, not an open interest. Coverage below says how much of the cache has",
        "a KNOWN open interest.",
        "",
        f"**Generated:** {report['generated']}  ",
        f"**Floor:** {args.floor:.0%} (pre-committed in `theta_bulk.OI_COVERAGE_FLOOR`)",
        "",
        "| | |",
        "|---|---|",
        f"| symbol-years scanned | {t['symbol_years']:,} across {t['names']:,} names |",
        f"| rows | {t['rows']:,} |",
        f"| rows with KNOWN open interest | {t['rows_with_known_oi']:,} "
        f"(**{t['known_fraction']:.2%}**) |",
        f"| rows with UNKNOWN open interest (-1) | {t['rows_unknown_oi']:,} "
        f"(**{1 - t['known_fraction']:.2%}**) |",
        f"| symbol-years below the {args.floor:.0%} floor | {t['symbol_years_below_floor']:,} |",
        f"| symbol-years with NO known OI at all | {t['symbol_years_wholly_unknown']:,} |",
        f"| names with at least one bad year | {t['names_affected']:,} |",
        "",
        "## Worst symbol-years",
        "",
        "| symbol-year | known OI |",
        "|---|---|",
    ]
    for k, v in list(report["below_floor"].items())[:40]:
        lines.append(f"| {k} | {v:.2%} |")
    if len(report["below_floor"]) > 40:
        lines.append(f"| ... | {len(report['below_floor']) - 40:,} more in OI_COVERAGE.json |")
    lines.append("")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[oi-audit] rows {t['rows']:,}  known {t['known_fraction']:.2%}  "
          f"below floor {t['symbol_years_below_floor']:,}/{t['symbol_years']:,}  "
          f"wholly unknown {t['symbol_years_wholly_unknown']:,}")
    print(f"[oi-audit] wrote {REPORT_JSON} and {REPORT_MD}")


if __name__ == "__main__":
    main()
