"""Deepen the most liquid names from 90 to 200 DTE (audit O15).

WHY. `MAX_DTE = 90` foreclosed a whole strategy space and, more concretely, blocked U1: the
equity composite's horizon is 63 TRADING days, which is ~92 CALENDAR days, so the natural option
tenor for testing the stock signal as an options entry sat two days past the ceiling. It also
left `atm_iv_180` 100% empty and put LEAPS, calendars and diagonals out of reach.

WHAT IT COSTS. Measured on identical spans (March 2023) before this was run, not assumed:

    name    rows x   bytes x   wall-clock x
    AAPL     1.30     1.30      0.96
    KO       1.23     1.23      1.10
    BKNG     1.19     1.19      0.90

So ~1.2-1.3x the data for the SAME wall-clock, not the 2-3x that was budgeted. Past 90 DTE there
are no weeklies, only monthlies and quarterlies, so the extra tenor is sparse; and the call is
dominated by the server-side scan rather than by payload size.

WHICH NAMES. Ranked by MEASURED option volume from `cache_manifest.json` (`daily_option_volume`,
recorded when each name's probe year was screened), not by market cap. Only `complete` names are
eligible: deepening a name whose history has gaps buys nothing.

SAFETY. `ThetaBulk(upgrade_depth=True)` re-pulls a shallow year, but `ensure_year` refuses to
replace a cached frame with a SMALLER one -- a 200-DTE pull is a strict superset of the 90-DTE
pull of the same span, so fewer rows means the pull was partial and the shallow frame is kept.
Every kept frame gets a `.dte` sidecar, so a half-finished run leaves a cache whose depth is
readable per symbol-year rather than silently mixed.

Run:

    python dte_extend.py                  # top 100 by measured option volume
    python dte_extend.py --limit 25       # the most liquid 25
    python dte_extend.py --dry-run        # the plan and the projected cost, no network
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge.theta_bulk import (  # noqa: E402
    CACHE_ROOT, LEGACY_MAX_DTE, MAX_DTE, ThetaBulk, cached_dte, depth_report,
)

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(CACHE_ROOT, "cache_manifest.json")
RESULT_JSON = os.path.join(HERE, "DTE_EXTEND_RESULT.json")
PROGRESS = os.path.join(CACHE_ROOT, "DTE_EXTEND_PROGRESS.txt")

# Refuse to start, and stop mid-run, below this much free space. The projection says the whole
# job adds 1.3-2.0GB, so hitting this floor means something else is filling the disk and the
# right move is to stop rather than to wedge the machine.
MIN_FREE_GB = 20.0


def log(m):
    line = f"[dte-extend] {m}"
    print(line, flush=True)
    try:
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def free_gb() -> float:
    return shutil.disk_usage(os.path.splitdrive(CACHE_ROOT)[0] + os.sep).free / 1e9


def name_bytes_rows(sym: str):
    d = os.path.join(CACHE_ROOT, sym.upper())
    if not os.path.isdir(d):
        return 0, []
    b, years = 0, []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".pkl") and "-" in fn:
            b += os.path.getsize(os.path.join(d, fn))
            try:
                years.append(int(fn.rsplit("-", 1)[1][:-4]))
            except ValueError:
                pass
    return b, sorted(years)


def ranked_names(limit: int):
    """The most liquid COMPLETE names, by measured daily option volume."""
    with open(MANIFEST, encoding="utf-8") as f:
        man = json.load(f)
    ok = [(k, v) for k, v in man.items()
          if isinstance(v, dict) and v.get("status") == "complete"]
    ok.sort(key=lambda kv: -(kv[1].get("daily_option_volume") or 0))
    return [(k, float(v.get("daily_option_volume") or 0)) for k, v in ok[:limit]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    names = ranked_names(args.limit)
    plan = [(s, vol) + name_bytes_rows(s) for s, vol in names]
    tot_b = sum(p[2] for p in plan)
    tot_y = sum(len(p[3]) for p in plan)
    todo_y = sum(1 for s, _, _, yrs in plan for y in yrs if cached_dte(s, y) < MAX_DTE)

    log(f"{len(plan)} names, {tot_y} cached symbol-years, {todo_y} still at "
        f"<{MAX_DTE} DTE; {tot_b/1e9:.2f}GB on disk today")
    log(f"projected net added: {tot_b*0.19/1e9:.2f}-{tot_b*0.30/1e9:.2f}GB "
        f"(measured x1.19-1.30); free now {free_gb():.0f}GB")
    if args.dry_run:
        for s, vol, b, yrs in plan[:25]:
            shallow = [y for y in yrs if cached_dte(s, y) < MAX_DTE]
            print(f"  {s:6s} vol {vol:>10,.0f}  {b/1e6:>7.0f}MB  "
                  f"{len(yrs)} yrs, {len(shallow)} to deepen")
        return
    if free_gb() < MIN_FREE_GB:
        log(f"REFUSING TO START: only {free_gb():.1f}GB free (< {MIN_FREE_GB})")
        return

    results = {}
    if os.path.exists(RESULT_JSON):
        try:
            with open(RESULT_JSON, encoding="utf-8") as f:
                results = json.load(f).get("names", {})
        except (OSError, ValueError):
            results = {}

    tb = ThetaBulk(max_dte=MAX_DTE, upgrade_depth=True)
    if not tb._key:
        log("NO THETADATA KEY - refusing to run")
        return

    t0 = time.time()
    for i, (sym, vol, b_before, yrs) in enumerate(plan, 1):
        shallow = [y for y in yrs if cached_dte(sym, y) < MAX_DTE]
        if not shallow:
            results.setdefault(sym, {"status": "already_deep", "years": len(yrs)})
            continue
        if free_gb() < MIN_FREE_GB:
            log(f"STOPPING at {sym}: only {free_gb():.1f}GB free (< {MIN_FREE_GB})")
            break
        t1 = time.time()
        res = tb.prefetch([sym], shallow)
        b_after, _ = name_bytes_rows(sym)
        deep_now = [y for y in yrs if cached_dte(sym, y) >= MAX_DTE]
        results[sym] = {
            "status": "deep" if len(deep_now) == len(yrs) else "partial",
            "daily_option_volume": vol,
            "years_total": len(yrs), "years_shallow_before": len(shallow),
            "years_deep_after": len(deep_now),
            "mb_before": round(b_before / 1e6, 1), "mb_after": round(b_after / 1e6, 1),
            "fetched": res.get("fetched"), "missing": res.get("missing"),
            "seconds": round(time.time() - t1, 1),
        }
        log(f"[{i}/{len(plan)}] {sym}: {len(deep_now)}/{len(yrs)} years deep, "
            f"{b_before/1e6:.0f} -> {b_after/1e6:.0f}MB, {time.time()-t1:.0f}s "
            f"({(time.time()-t0)/60:.0f}m total, {free_gb():.0f}GB free)")
        with open(RESULT_JSON, "w", encoding="utf-8") as f:
            json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "max_dte": MAX_DTE, "legacy_max_dte": LEGACY_MAX_DTE,
                       "names": results}, f, indent=1)

    rep = depth_report()
    n_deep = sum(1 for v in results.values() if v.get("status") in ("deep", "already_deep"))
    log(f"DONE {n_deep}/{len(plan)} names fully at {MAX_DTE} DTE in "
        f"{(time.time()-t0)/60:.0f}m; cache depth {rep['by_depth']}")
    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "max_dte": MAX_DTE, "legacy_max_dte": LEGACY_MAX_DTE,
                   "depth_report": {k: v for k, v in rep.items() if k != "names_fully_deep"},
                   "n_names_fully_deep": len(rep["names_fully_deep"]),
                   "names": results}, f, indent=1)


if __name__ == "__main__":
    main()
