# -*- coding: utf-8 -*-
"""D9 STEP 0 (c) — THE NOISE CEILING, measured before any bar is written.

ZERO TRIALS. `MB1-SEL`: a fidelity control can only ever BLOCK, never produce a finding, so it
adds no degree of freedom and charges nothing.

WHAT A CEILING IS FOR. The question D9 asks is whether the free live path ranks the large-cap
tier *closely enough to the Sharadar panel*. "Closely enough" is meaningless without knowing how
much the SAME path disagrees with ITSELF over the same elapsed time -- a cross-vendor Spearman of
0.70 is excellent if the vendor-free ceiling is 0.72 and worthless if it is 0.98. `W-28` died on
a bar its account could not reach and `W-1`'s own `K2` was set from the wrong arm's figure, so
the ceiling is measured FIRST and the bars are written against it.

THIS MEASURES THE WITHIN-VENDOR HALF ONLY, and that is not a choice. The live half of the
ceiling -- the live path against itself across the same gap -- is UNOBTAINABLE, measured rather
than assumed: see `D9_STORE_CENSUS.json`.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge.fundamental_panel import composite_from_frame      # noqa: E402
from valuation.screener.cross_sectional import zscore                  # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT         # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
OUT = os.path.join(FA, "D9_NOISE_CEILING.json")

#: The large-cap floor the live book uses (`valquo_index.LARGE_CAP_MIN`, confirmed live at
#: 1e10 in the served payload's `criteria`).
LARGE_CAP_MIN = 1e10
#: The live book's decile fraction.
TOP_DECILE = 0.10


def main() -> int:
    panel = pd.read_pickle(PANEL)
    panel["_d"] = panel["date"].astype(str).str[:10]
    cols = [c for c in DEPLOYED if c in panel.columns]
    w = {c: BASE_WEIGHT for c in cols}

    # composite + large-cap tier per date, exactly as the live book defines the tier
    by_date = {}
    for d0, g in panel.groupby("_d"):
        comp = composite_from_frame(g, cols, w, zscore)
        mc = pd.to_numeric(g["market_cap"], errors="coerce").to_numpy()
        tk = g["ticker"].astype(str).str.upper().to_numpy()
        ok = np.isfinite(comp) & np.isfinite(mc) & (mc >= LARGE_CAP_MIN)
        if int(ok.sum()) < 50:
            continue
        s = pd.Series(np.asarray(comp)[ok], index=tk[ok])
        by_date[d0] = s[~s.index.duplicated()]

    dates = sorted(by_date)
    out = {"item": "D9", "step": "0c noise ceiling", "trials": 0,
           "large_cap_min": LARGE_CAP_MIN, "n_dates": len(dates),
           "mean_tier_size": float(np.mean([len(by_date[d]) for d in dates])),
           "note": ("WITHIN-VENDOR only. The live half of the ceiling is unobtainable -- the "
                    "public API serves `latest_scan_date()` and no endpoint takes a date, and "
                    "every local scan store is self-labelled synthetic."),
           "by_lag": {}}

    # lag k = k rebalances = k * 63 trading days
    for k in (1, 2, 3):
        rhos, ovl = [], []
        for i in range(len(dates) - k):
            a, b = by_date[dates[i]], by_date[dates[i + k]]
            both = a.index.intersection(b.index)
            if len(both) < 50:
                continue
            rhos.append(float(pd.Series(a[both]).corr(pd.Series(b[both]), method="spearman")))
            na = max(1, int(round(len(a) * TOP_DECILE)))
            nb = max(1, int(round(len(b) * TOP_DECILE)))
            ta = set(a.nlargest(na).index)
            tb = set(b.nlargest(nb).index)
            ovl.append(len(ta & tb) / max(1, len(ta)))
        out["by_lag"]["%d_rebalances_%d_trading_days" % (k, 63 * k)] = {
            "pairs": len(rhos),
            "composite_spearman_mean": float(np.mean(rhos)) if rhos else None,
            "composite_spearman_p05": float(np.percentile(rhos, 5)) if rhos else None,
            "composite_spearman_median": float(np.median(rhos)) if rhos else None,
            "top_decile_overlap_mean": float(np.mean(ovl)) if ovl else None,
            "top_decile_overlap_p05": float(np.percentile(ovl, 5)) if ovl else None,
        }

    # THE GAP THAT ACTUALLY APPLIES: 2026-07-31 (last Sharadar) -> 2026-09-29 (only live), which
    # is 41 trading days. Interpolated between the measured lag-1 (63d) and a notional lag-0
    # (identity, rho = 1) LINEARLY IN TRADING DAYS, and LABELLED an interpolation rather than a
    # measurement -- the panel is quarterly and has no 41-day pair to read.
    l1 = out["by_lag"]["1_rebalances_63_trading_days"]
    if l1["composite_spearman_mean"] is not None:
        f = 41.0 / 63.0
        out["applicable_gap"] = {
            "trading_days": 41,
            "from": "2026-07-31 (last Sharadar date on the freeze)",
            "to": "2026-09-29 (the only obtainable live snapshot)",
            "interpolated_composite_spearman_ceiling":
                1.0 - f * (1.0 - l1["composite_spearman_mean"]),
            "interpolated_top_decile_overlap_ceiling":
                1.0 - f * (1.0 - l1["top_decile_overlap_mean"]),
            "LABEL": ("INTERPOLATION, not a measurement. The panel is quarterly, so no 41-day "
                      "pair exists to read directly. Linear in trading days between the "
                      "measured 63-day pair and the identity at lag 0; rank persistence decays "
                      "faster than linearly at short lags, so this OVERSTATES the ceiling and "
                      "is therefore the conservative direction for a GO."),
        }

    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
