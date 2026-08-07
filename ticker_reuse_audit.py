"""Adjudicate the reused-ticker screens by STRIKE RANGE, and write the evidence to disk.

WHY THIS EXISTS. `theta_bulk.reused_ticker_suspects()` and `collapsed_year_suspects()` are
cheap screens -- they read filenames and file sizes, so they run on every `mine_status.py` call
and cost nothing. What they cannot do is tell a ticker that CHANGED HANDS from a name that had
an ordinary outage or a genuinely thin year. That needs the data.

Strike range is the discriminator. It tracks the underlying's price level and cannot be faked by
a ticker string, so two companies show up as a step across the join that no single underlying
makes while its options are dark. This is the same test that confirmed the WBD/DISCA
contamination, and on the 2026-08-07 cache it cleanly separated six real reuses from two benign
hits (`DD` and `DOW`, whose 2018 hole is the DowDuPont restructuring of a continuous underlying:
0.97x and 0.88x, against 26.5x for `AXON`).

READ-ONLY. No network, no writes under `data/options/`. It only reads cached frames and writes
its findings to TICKER_REUSE_AUDIT.json beside this file.

    python ticker_reuse_audit.py            # measure, print, write the evidence file
    python ticker_reuse_audit.py --quiet    # write only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge.theta_bulk import (CACHE_ROOT, collapsed_year_suspects,  # noqa: E402
                                       reused_ticker_suspects, year_path)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TICKER_REUSE_AUDIT.json")
# A step this large across a gap is not a price move. Chosen from the measured spread: the six
# confirmed reuses run 1.89x to 26.5x and the two benign hits sit at 0.97x and 0.88x, so
# anything near 1.0 is continuous and the gap between the groups is wide.
STEP_SUSPECT = 1.5


def median_strike(sym: str, year: int) -> float | None:
    import pandas as pd

    p = year_path(sym, year, CACHE_ROOT)
    if not os.path.exists(p):
        return None
    try:
        s = pd.to_numeric(pd.read_pickle(p)["strike"], errors="coerce").dropna()
        if not len(s):
            return None
        if s.max() > 10000:            # some feeds carry strikes in 1/1000 dollars
            s = s / 1000.0
        return round(float(s.median()), 2)
    except Exception:                                                    # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    holes = reused_ticker_suspects()
    collapsed = collapsed_year_suspects()
    findings = {}

    for name, v in sorted(holes.items()):
        hole = v["hole"]
        before = [median_strike(name, y) for y in v["cached"] if y < hole[0]]
        after = [median_strike(name, y) for y in v["cached"] if y > hole[-1]]
        before = [x for x in before if x]
        after = [x for x in after if x]
        lo = sum(before) / len(before) if before else None
        hi = sum(after) / len(after) if after else None
        step = round(hi / lo, 2) if lo and hi else None
        findings[name] = {
            "screen": "interior_hole", "hole": hole,
            "median_strike_before": round(lo, 2) if lo else None,
            "median_strike_after": round(hi, 2) if hi else None,
            "step": step,
            # Deliberately "suspected", never "confirmed": the step is strong evidence, but the
            # verdict is which COMPANY held the ticker, and that is not in this cache.
            "verdict": ("suspected_two_companies"
                        if step and (step > STEP_SUSPECT or step < 1 / STEP_SUSPECT)
                        else "continuous_underlying"),
        }

    for name, rows in sorted(collapsed.items()):
        findings.setdefault(name, {"screen": "collapsed_year"})["collapsed_years"] = rows

    if not args.quiet:
        print(f"{len(holes)} interior-hole suspect(s), {len(collapsed)} collapsed-year "
              f"suspect(s)\n")
        for name, f in sorted(findings.items()):
            if f.get("step") is not None:
                print(f"  {name:6s} hole {str(f['hole']):24s} "
                      f"{f['median_strike_before']:8.1f} -> {f['median_strike_after']:8.1f}  "
                      f"step {f['step']:6.2f}x   {f['verdict']}")
            else:
                print(f"  {name:6s} collapsed {[r['year'] for r in f['collapsed_years']]}")
        print("\nA step near 1.0 is a continuous underlying (DD/DOW: the DowDuPont "
              "restructuring).\nA large step is two companies sharing a ticker. Neither screen "
              "can name the companies;\nthat takes a listing history, and the cache does not "
              "carry one.")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"generated": dt.date.today().isoformat(),
                   "step_threshold": STEP_SUSPECT, "findings": findings},
                  f, indent=1, sort_keys=True)
    if not args.quiet:
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
