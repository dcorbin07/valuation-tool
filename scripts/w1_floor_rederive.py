# -*- coding: utf-8 -*-
"""W-1 — the BOUNDED placebo-floor re-derivation owed at equity N = 247.

Booking W-1's 2 equity trials takes `N` 245 -> 247, and `MB31`'s map names 247 as the point where
seed **1003** flips OFF the CPCV adopt gate. `MA19`'s mechanism is the reason that matters: `N`
reaches a placebo floor ONLY through that gate, because an ADOPTING draw is scored under the
CHALLENGER's weights and a non-adopting one under the BASE weights.

**THIS IS BOUNDED, NOT A SWEEP.** `MA19` re-scored three draws in ~400s rather than re-running a
100-draw placebo. Exactly ONE draw newly flips at 247, so exactly one is re-scored here.

**AND IT IS NOT SKIPPABLE, WHICH THE RANK CHECK ESTABLISHED FIRST.** `MA19`'s lesson is that
*"whether a floor moves depends not on HOW MANY draws flip but on WHERE THEY SAT"* -- a p95 over
100 draws is set by the 5th-and-6th largest values. Seed 1003 sits at **rank 4 / 4 / 6** in the
three floor-defining statistics and IS the #6 draw on top-decile alpha HAC, so it is squarely in
the band that sets the percentile. Had it ranked, say, 40th, no re-score would have been needed.

`MA19`'s own machinery is IMPORTED, never re-implemented (`B7`): `rescore`, `adopters_at`,
`haircut_at` and its `KEYS`/substitution convention all come from `scripts/ma19_recalibrate`.

**ZERO TRIALS.** This computes no outcome statistic on the real book; it re-derives a calibration.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import fundamental_panel as FP            # noqa: E402
from valuation.edge import research_log as RL                 # noqa: E402
from valuation.screener import settings as S                  # noqa: E402
from scripts.ma19_recalibrate import (                        # noqa: E402
    rescore, adopters_at, haircut_at, BANK_PLACEBO, BANK_RECON, PANEL, BUCKET)

FA = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data", "free_analysis")
OUT = os.path.join(FA, "W1_FLOORS.json")
MA19 = os.path.join(FA, "MA19_RECALIBRATION.json")

N_BEFORE, N_AFTER = 245, 247
#: The floors W-1's gate reads, with the values the record publishes today (MA19 at N=224, which
#: `MB31` proved unmoved at every N below 247 -- which is precisely why 247 is owed a re-check).
FLOOR_KEYS = [("long_short_tstat", "long-short naive", 2.1437),
              ("long_short_tstat_nw", "long-short HAC", 2.2837),
              ("top_decile_alpha_tstat_nw", "top-decile alpha HAC", 2.0540)]


def _p95(draws, key):
    v = np.array([float(d[key]) for d in draws if d.get(key) is not None], dtype=float)
    return float(np.percentile(v, 95)), v


def main() -> int:
    live = int(RL.trial_count(domain="equity"))
    print("[w1] live equity N = %d ; this register books 2 -> %d" % (live, live + 2))
    if live != N_BEFORE:
        print("[w1] NOTE: live N is %d, not the %d this re-derivation was written for."
              % (live, N_BEFORE))

    bank = json.load(open(BANK_PLACEBO))
    recon = json.load(open(BANK_RECON))
    draws = {d["seed"]: d for d in bank["draws"]}
    rows = recon["rows"]

    a_before, a_after = adopters_at(rows, N_BEFORE), adopters_at(rows, N_AFTER)
    newly_off = sorted(a_before - a_after)
    newly_on = sorted(a_after - a_before)
    print("[w1] adopters %d (N=%d) -> %d (N=%d); newly OFF %s ; newly ON %s"
          % (len(a_before), N_BEFORE, len(a_after), N_AFTER, newly_off, newly_on))
    if newly_on:
        raise RuntimeError("adoption must be monotone decreasing in N; got newly-ON %s" % newly_on)

    # MA19 already re-scored the draws that flipped at or before N=224. Reuse them; only the
    # NEWLY flipped seed needs the ~150s re-score.
    prior = json.load(open(MA19)).get("rescored", {}) if os.path.isfile(MA19) else {}
    have = {int(k): v for k, v in prior.items()}
    a_asrun = adopters_at(rows, 129)
    all_off = sorted(a_asrun - a_after)          # every draw scored under BASE at N=247
    need = [s for s in all_off if s not in have]
    print("[w1] draws scored under BASE weights at N=%d: %s" % (N_AFTER, all_off))
    print("[w1] already re-scored by MA19: %s ; needing a re-score now: %s"
          % (sorted(have), need))

    panel = pd.read_pickle(PANEL)
    cols = [c for c in S.BUCKET_FACTORS[BUCKET]
            if c in panel.columns and panel[c].notna().any()]
    base = FP._base_weights(cols, BUCKET)
    for seed in need:
        t0 = time.time()
        have[seed] = rescore(panel, cols, base, seed)
        print("[w1] re-scored seed %d in %.1fs · adopt_live=%s · base ls_t=%.6f chal ls_t=%.6f"
              % (seed, time.time() - t0, have[seed]["cpcv_adopt_live"],
                 have[seed]["base"]["long_short_tstat"],
                 have[seed]["challenger"]["long_short_tstat"]))

    # ---- rebuild the distribution at each N, MA19's substitution convention
    def dist(off_set):
        out = []
        for seed, d in sorted(draws.items()):
            if seed in off_set and seed in have:
                nd = dict(d)
                nd.update({k: v for k, v in have[seed]["base"].items() if k in nd})
                out.append(nd)
            else:
                out.append(d)
        return out

    d_before = dist(sorted(a_asrun - a_before))
    d_after = dist(all_off)

    print("\n=== FLOORS: N=%d vs N=%d ===" % (N_BEFORE, N_AFTER))
    floors = {}
    for key, label, published in FLOOR_KEYS:
        f0, _ = _p95(d_before, key)
        f1, _ = _p95(d_after, key)
        moved = abs(f1 - f0) > 1e-12
        floors[key] = {"label": label, "published_today": published,
                       "floor_at_%d" % N_BEFORE: f0, "floor_at_%d" % N_AFTER: f1,
                       "moved": bool(moved), "delta": f1 - f0}
        print("  %-22s  N=%d %.6f  ->  N=%d %.6f   %s"
              % (label, N_BEFORE, f0, N_AFTER, f1,
                 "MOVED by %+.6f" % (f1 - f0) if moved else "UNMOVED"))

    out = {"item": "W-1", "purpose": "bounded floor re-derivation owed at N=247",
           "trials": 0, "N_before": N_BEFORE, "N_after": N_AFTER,
           "hurdle_before": haircut_at(N_BEFORE), "hurdle_after": haircut_at(N_AFTER),
           "adopters_before": len(a_before), "adopters_after": len(a_after),
           "newly_off": newly_off, "rescored_here": need,
           "reused_from_MA19": sorted(set(have) - set(need)),
           "floors": floors,
           "any_floor_moves": any(v["moved"] for v in floors.values())}
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("\nany floor moves at N=247: %s" % out["any_floor_moves"])
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
