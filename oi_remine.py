"""Re-mine the symbol-years whose open interest is mostly the -1 unknown sentinel (audit B4).

Reads `OI_COVERAGE.json` (written by `oi_coverage_audit.py`), takes every symbol-year below the
coverage floor worst-first, re-pulls it, and keeps whichever version has MORE known open
interest. The old frame is never discarded until the new one is proven better, so a bad network
day cannot destroy 16GB of valid EOD data.

The point of the exercise is to separate two causes that looked identical on disk:

  * **the OI CALL faulted**      -> retryable; the data exists at source
  * **no OI at source**          -> not retryable; marked `.oi_nosource` and never retried again

Run:

    python oi_remine.py                     # every span below the floor, worst first
    python oi_remine.py --limit 50          # just the worst 50
    python oi_remine.py --dry-run           # show what it would do
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge.theta_bulk import (  # noqa: E402
    CACHE_ROOT, OI_COVERAGE_FLOOR, REPO_ROOT, ThetaBulk, oi_coverage, year_path,
)

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE_JSON = os.path.join(HERE, "OI_COVERAGE.json")
RESULT_JSON = os.path.join(HERE, "OI_REMINE_RESULT.json")
PROGRESS = os.path.join(CACHE_ROOT, "OI_REMINE_PROGRESS.txt")


def log(m):
    line = f"[oi-remine] {m}"
    print(line, flush=True)
    try:
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_frame(path):
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:                                                    # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--floor", type=float, default=OI_COVERAGE_FLOOR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(COVERAGE_JSON, encoding="utf-8") as f:
        cov = json.load(f)
    targets = list(cov["below_floor"].items())          # already sorted worst-first
    if args.limit:
        targets = targets[: args.limit]
    log(f"{len(targets)} symbol-years below {args.floor:.0%} to re-mine (worst first)")
    if args.dry_run:
        for k, v in targets[:60]:
            print(f"  {k:20s} {v:.2%}")
        return

    prior = {}
    if os.path.exists(RESULT_JSON):
        try:
            with open(RESULT_JSON, encoding="utf-8") as f:
                prior = json.load(f).get("spans", {})
        except (OSError, ValueError):
            prior = {}

    tb = ThetaBulk()
    if not tb._key:
        log("NO THETADATA KEY - refusing to run (would mark everything as unrecoverable)")
        return

    results = dict(prior)
    t0 = time.time()
    for i, (key, before) in enumerate(targets, 1):
        if key in prior and prior[key].get("status") in ("recovered", "no_source"):
            continue
        sym, year = key.rsplit("-", 1)
        year = int(year)
        path = year_path(sym, year, CACHE_ROOT)
        nosrc = path + ".oi_nosource"
        if os.path.exists(nosrc):
            results[key] = {"before": before, "after": before, "status": "no_source",
                            "note": "already marked; not retried"}
            continue

        bak = path + ".bak_oi"
        had_old = os.path.exists(path)
        if had_old:
            try:
                os.replace(path, bak)
            except OSError as e:
                log(f"{key}: cannot set old frame aside ({e}); skipping")
                continue
        for extra in (path + ".missing", path + ".empty", path + ".exhausted"):
            if os.path.exists(extra):
                try:
                    os.remove(extra)
                except OSError:
                    pass

        t1 = time.time()
        try:
            tb.ensure_year(sym, year)
        except Exception as e:                                           # noqa: BLE001
            log(f"{key}: ensure_year raised {type(e).__name__}: {e}")
        new_df = load_frame(path) if os.path.exists(path) else None
        after = oi_coverage(new_df) if new_df is not None else 0.0
        faults = int(getattr(tb._tl, "oi_faults", 0))

        # Keep whichever frame has more KNOWN open interest. Never trade rows for coverage:
        # if the new pull is thinner in rows it is only kept when coverage genuinely improves.
        old_df = load_frame(bak) if had_old else None
        keep_new = new_df is not None and (old_df is None or after > before)
        if keep_new:
            if had_old and os.path.exists(bak):
                try:
                    os.remove(bak)
                except OSError:
                    pass
            status = "recovered" if after >= args.floor else "improved"
            if after <= before and faults == 0:
                status = "no_source"
        else:
            if had_old:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                    os.replace(bak, path)
                except OSError as e:
                    log(f"{key}: RESTORE FAILED ({e}) - frame is at {bak}")
            after = before
            status = "no_source" if faults == 0 else "still_failing"

        if status == "no_source":
            try:
                with open(nosrc, "w", encoding="utf-8") as f:
                    f.write(f"coverage {after:.6f} after re-mine, 0 OI-call faults - the feed "
                            f"has no open interest for this span. Not retried again. "
                            f"{time.strftime('%Y-%m-%d')}\n")
            except OSError:
                pass

        rows_old = 0 if old_df is None else len(old_df)
        rows_new = 0 if new_df is None else len(new_df)
        results[key] = {"before": round(before, 6), "after": round(after, 6),
                        "status": status, "oi_call_faults": faults,
                        "rows_before": rows_old, "rows_after": rows_new,
                        "seconds": round(time.time() - t1, 1)}
        log(f"[{i}/{len(targets)}] {key}: {before:.1%} -> {after:.1%} {status} "
            f"(rows {rows_old:,} -> {rows_new:,}, {time.time() - t1:.0f}s, "
            f"{time.time() - t0:.0f}s total)")

        with open(RESULT_JSON, "w", encoding="utf-8") as f:
            json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "floor": args.floor, "spans": results}, f, indent=1)

    n = {"recovered": 0, "improved": 0, "no_source": 0, "still_failing": 0}
    for v in results.values():
        n[v.get("status", "still_failing")] = n.get(v.get("status", "still_failing"), 0) + 1
    log(f"DONE  recovered {n['recovered']}  improved {n['improved']}  "
        f"no_source {n['no_source']}  still_failing {n['still_failing']}")


if __name__ == "__main__":
    main()
