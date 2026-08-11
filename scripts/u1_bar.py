#!/usr/bin/env python3
"""u1_bar.py — the two calibrated bars for U1, computed BEFORE any arm is scored.  [AUDIT U1]

    python -m scripts.u1_bar

Pre-registered in `PREREG_u1_composite_entry.md` section 5, committed alone at `7d7c414`. This
script is the U1 analogue of `scripts/tp_bar.py`: it derives the bars and stops. **It never
computes an arm's mean P&L, and that is enforced rather than intended** — it calls
`composite_entry.arm_shape`, which returns per-date counts and an optional cap-tier histogram
and nothing else, and it does not import `mean_pnl` for the arms at all.

WHY A BAR AT ALL. A gain over the grid looks impressive until you learn how large a gain an
arbitrary selection rule of the same size earns on the same dates. TP-BAR was decided entirely by
that question: `tp150` beat the shipped exit by +3.19pp and still failed, because 53 of 100
arbitrary jitters also beat it. U1 gets the same treatment before it gets a verdict.

TWO BARS, AND THE SECOND IS THE LEDGER'S CONDITION.

  * **NULL-PLAIN** — 200 draws, each taking the arm's exact per-date count uniformly at random
    from that date's surviving cells.
  * **NULL-CAPMATCHED** — 200 draws matched additionally on the arm's own market-cap tier
    histogram per date. `VALQUO_LEDGER.md:300` permits U1 to reopen only with a composite built
    within the options universe **or with size neutralised**; this is the second, and U7's
    mechanism finding — that inside 187 megacaps the composite decile is largely a cap sort — is
    what it subtracts.

THE NULL IS NOT A NO-EFFECT NULL. Every draw is a real book of real trades on the real grid, so
the null contains whatever the grid earns and its median gain is ~0 by construction. The p95
answers "is this rule distinguished among rules of its own size?" It does not answer, and may
never be quoted as answering, "does selecting names on the composite do anything".
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.u1_entry import GRID_PATH, OUT_DIR          # noqa: E402
from valuation.edge import composite_entry as CE         # noqa: E402

N_DRAWS = 200
SEED0 = 2000                       # the project's placebo convention: a fixed contiguous block
PCTILE = 95
NULL_PATH = os.path.join(OUT_DIR, "U1_NULL.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U1 — the calibrated bars, before any scoring.")
    ap.add_argument("--grid", default=GRID_PATH)
    ap.add_argument("--data-root", default=os.path.dirname(os.path.dirname(OUT_DIR)))
    ap.add_argument("--draws", type=int, default=N_DRAWS)
    ap.add_argument("--json", default=NULL_PATH)
    args = ap.parse_args(argv)

    with open(args.grid, "rb") as f:
        blob = pickle.load(f)
    raw = blob["rows"]

    # U1-SPLIT, found during this calibration and BEFORE any arm was scored. See
    # `PREREG_u1_composite_entry.md` section 10 and `composite_entry.spans_split`.
    splits = CE.load_splits(args.data_root)
    grid, dropped = CE.drop_split_spanners(raw, splits)
    print("[U1-BAR] U1-SPLIT: dropped %d of %d trades whose contract life crosses a split"
          % (len(dropped), len(raw)), flush=True)
    for r in sorted(dropped, key=lambda x: -abs(float(x.get("pnl_pct") or 0)))[:5]:
        print("[U1-BAR]    %-6s %s  pnl %+.1f%%" % (r["ticker"], r["alert_ts"],
                                                     100 * float(r["pnl_pct"])), flush=True)

    dates = sorted({r["asof"] for r in grid})
    print("[U1-BAR] grid %d trades over %d dates, %d names"
          % (len(grid), len(dates), len({r["ticker"] for r in grid})), flush=True)

    out = {"item": "U1", "stage": "calibration_only",
           "n_draws": args.draws, "seed0": SEED0, "pctile": PCTILE,
           "verdict_basis": "SPLIT_CLEAN",
           "u1_split": {"n_raw": len(raw), "n_clean": len(grid), "n_dropped": len(dropped),
                        "dropped": [{"ticker": r["ticker"], "entry": r["alert_ts"],
                                     "expiry": str(r.get("expiry"))[:10],
                                     "pnl_pct": r.get("pnl_pct")} for r in dropped],
                        "note": ("Option chains are as-traded and unadjusted for splits while "
                                 "bars are adjusted. Excluded by an EXTERNAL table and a date "
                                 "comparison, never by the size of a return - a rule that "
                                 "dropped 'implausibly large' P&L would select on the outcome.")},
           "grid": {"n_trades": len(grid), "n_dates": len(dates),
                    "n_names": len({r["ticker"] for r in grid}),
                    "dates": dates},
           "note": ("Bars only. No arm is scored in this file and no arm P&L is reachable from "
                    "it: arm_shape returns per-date counts and a cap-tier histogram, never a "
                    "return. The null is NOT a no-effect null - every draw is a real book on "
                    "the real grid - so its p95 answers whether a rule is distinguished among "
                    "rules of its own size, never whether selection works at all. BOTH the "
                    "split-clean and the raw bars are retained; the verdict uses SPLIT_CLEAN "
                    "and that was fixed before any arm was scored."),
           "bars": {}, "bars_raw_uncorrected": {}}

    for basis, rows_src, sink in (("SPLIT_CLEAN", grid, out["bars"]),
                                  ("RAW", raw, out["bars_raw_uncorrected"])):
        for arm, (lo, hi) in sorted(CE.ARMS.items()):
            rows = CE.select(rows_src, lo, hi)
            # SHAPE ONLY. `rows` is never reduced to a mean anywhere in this script.
            for match in (False, True):
                counts, tiers = CE.arm_shape(rows, match_tier=match)
                got = CE.null_gains(rows_src, counts, tiers,
                                    n_draws=args.draws, seed0=SEED0)
                key = "%s_%s" % (arm, "CAPMATCHED" if match else "PLAIN")
                sink[key] = {k: v for k, v in got.items() if k != "gains_pp"}
                sink[key]["arm_n_trades"] = len(rows)
                sink[key]["arm_n_dates"] = len(counts)
                sink[key]["draws_pp"] = got["gains_pp"]
                print("[U1-BAR] %-11s %-18s n=%4d  bar(p95) %+8.4fpp  median %+7.4f  "
                      "p5 %+7.4f  max %+8.4f  shortfall=%d"
                      % (basis, key, len(rows), got["bar_pp"], got["median_pp"],
                         got["p5_pp"], got["max_pp"], got["tier_shortfall_cells"]), flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("[U1-BAR] -> %s" % args.json, flush=True)
    print("[U1-BAR] THE BARS ARE NOW FIXED. Nothing above scored an arm.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
