#!/usr/bin/env python3
"""V6 addendum — ADDITIVE ONLY. This never recomputes an arm.

Two things the arm pass does not carry:

  D1  the MDE at THIS REGISTER'S OWN BAR. `mde_at_t2` is the conventional |t| = 2
      reference, and the register's bar is each leg's permutation p95, which sits near
      t 1.44-1.86. Quoting a t=2 MDE against a p95 bar overstates how coarse the design
      is; quoting no MDE at all understates it. Both are reported.

  D2  which floor does the filtering - quality, health, or both. Expectation 3 named
      this in advance and it is a fact about the screen, not about a return.

Run:  python -m scripts.v6_addendum
"""
from __future__ import annotations

import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.v6_dip_detector import (DEPTHS, HEALTH_FLOOR, QUALITY_FLOOR,   # noqa: E402
                                     health_panel, trailing_drawdown)

ART = r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis/V6_DIP_DETECTOR.json"
PANEL = r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_v6.pkl"
DATA = r"C:/Users/donni/Downloads/valuation-tool/data/backtest"


def main():
    d = json.load(open(ART))
    assert "arms" in d and len(d["arms"]) == 4, "arm pass must have run first"

    # ---- D1: MDE at the register's OWN bar ----
    d1 = {}
    for tag, a in d["arms"].items():
        d1[tag] = {}
        for leg in ("L1", "L2"):
            blk = {}
            for win in ("full", "early", "late"):
                x = a["legs"][leg][win]
                se_ann = (x["mde_ann_pp"] / 2.0) if x["mde_ann_pp"] is not None else None
                bar = x["perm_p95"]
                blk[win] = {
                    "observed_ann_pp": x["ann_pp"],
                    "t": x["t"],
                    "bar_p95": bar,
                    "mde_at_t2_ann_pp": x["mde_ann_pp"],
                    "mde_at_own_bar_ann_pp": (se_ann * bar if (se_ann is not None
                                                               and bar is not None) else None),
                    "observed_above_own_mde": bool(
                        se_ann is not None and bar is not None
                        and x["ann_pp"] > se_ann * bar),
                }
            d1[tag][leg] = blk
    d.setdefault("diagnostics", {})["D1_mde_at_the_registers_own_bar"] = {
        "by_arm": d1,
        "note": ("`mde_at_t2` is the CONVENTIONAL reference; this register's bar is each "
                 "leg's own permutation p95 (t 1.44-1.86), which is LOWER, so the "
                 "detection threshold at the actual bar is correspondingly lower. Both "
                 "are reported so neither over- nor under-states the design's resolution."),
    }

    # ---- D2: which floor does the filtering ----
    panel = pickle.load(open(PANEL, "rb"))
    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())
    dd = trailing_drawdown(os.path.join(DATA, "prices"), tickers, dates)
    hp = health_panel(DATA, tickers, dates)
    p = panel.merge(dd, on=["date", "ticker"], how="left").merge(
        hp, on=["date", "ticker"], how="left")

    q = pd.to_numeric(p["quality"], errors="coerce")
    h = pd.to_numeric(p["health"], errors="coerce")
    d2 = {}
    for depth in DEPTHS:
        dip = pd.to_numeric(p["drawdown"], errors="coerce") <= -depth
        n_dip = int(dip.sum())
        qk = dip & (q > QUALITY_FLOOR)
        hk = dip & (h >= HEALTH_FLOOR)
        both = qk & hk
        d2[f"depth_{int(depth * 100)}"] = {
            "n_dipped": n_dip,
            "kept_by_quality_alone": round(float(qk.sum() / max(1, n_dip)), 4),
            "kept_by_health_alone": round(float(hk.sum() / max(1, n_dip)), 4),
            "kept_by_both": round(float(both.sum() / max(1, n_dip)), 4),
            "quality_is_the_binding_floor": bool(qk.sum() < hk.sum()),
        }
    d.setdefault("diagnostics", {})["D2_which_floor_binds"] = d2

    with open(ART, "w") as f:
        json.dump(d, f, indent=2, default=float)
    print(json.dumps({"D2": d2}, indent=2))
    for tag in ("A1", "A2", "A3", "A4"):
        for leg in ("L1", "L2"):
            x = d1[tag][leg]["full"]
            print(f"{tag} {leg} full: obs {x['observed_ann_pp']:+.3f}pp  "
                  f"MDE@bar {x['mde_at_own_bar_ann_pp']:+.3f}pp  "
                  f"MDE@t2 {x['mde_at_t2_ann_pp']:+.3f}pp  "
                  f"above_own_mde {x['observed_above_own_mde']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
