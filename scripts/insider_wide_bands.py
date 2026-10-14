# -*- coding: utf-8 -*-
"""`INSIDER-WIDE` — A DIAGNOSTIC, NO VERDICT: the check cell's `h`=63 rows by DISJOINT cap band.

    python -m scripts.insider_wide_bands

**IT IS A DECOMPOSITION OF A READ, NOT A SECOND READ.** It reads the rows
`scripts/insider_wide_arm.py` already banked for a cell the register has read once, and the
register's §2a reported exactly this decomposition for the BUILD quadrant — so reporting it for
the check cell is symmetric rather than a new look.

**IT CARRIES NO VERDICT, and that is a rule rather than a modesty.** No band was declared in the
register, no band has a bar, and promoting a band after seeing it is choosing a population on an
outcome — the thing §2c exists to prevent. **The registered verdict is the `cap ≥ $500M` CELL.**
These bands explain where it comes from and may not be quoted as results.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as DC                                 # noqa: E402
from scripts import dipcall_arm as DA                                       # noqa: E402

OUT = "INSIDER_WIDE_BANDS.json"

#: The register's own §2a edges, so the check table lines up with the build table row for row.
EDGES = [(10e9, None), (2e9, 10e9), (500e6, 2e9), (100e6, 500e6), (0.0, 100e6)]

LATE = "2023-01-01"


def main(argv=None):
    r = pd.read_pickle(DC.out_path("INSIDER_WIDE_ROWS_full_universe_h63.pkl"))
    r["cap"] = pd.to_numeric(r["cap"], errors="coerce")
    bands = {}
    print("CHECK quadrant, h=63, DISJOINT cap bands -- DIAGNOSTIC, NO VERDICT")
    print("%-20s %6s %6s %11s %8s %8s %8s %11s %11s" %
          ("band", "n", "tick", "gross", "t_date", "t_tick", "cost", "NET", "late"))
    for lo, hi in EDGES:
        m = r["cap"].notna() & (r["cap"] >= lo)
        if hi is not None:
            m = m & (r["cap"] < hi)
        g = r[m]
        if len(g) < 3:
            print("%-20s %6d  (too few rows)" % ("$%.0fM" % (lo / 1e6), len(g)))
            continue
        y = g["mkt"].to_numpy(dtype=float)
        # DELEGATED, never re-implemented (`B7`): one clustered `se` in this repository.
        _m1, _s1, td, _g1 = DA.clustered(y, g["date"].to_numpy(dtype=object))
        _m2, _s2, tt, _g2 = DA.clustered(y, g["ticker"].to_numpy(dtype=object))
        cost = float(np.nanmean(g["cost_pp"].to_numpy(dtype=float)))
        late = float(g[g["date"] >= LATE]["mkt"].mean() * 100.0)
        key = "%.0f_%s" % (lo, "inf" if hi is None else "%.0f" % hi)
        bands[key] = {"lo_usd": lo, "hi_usd": hi, "n_events": int(len(g)),
                      "n_tickers": int(g["ticker"].nunique()),
                      "gross_pp": float(y.mean() * 100.0), "t_date": td, "t_ticker": tt,
                      "roundtrip_cost_pp_mean": cost,
                      "net_of_cost_pp": float(y.mean() * 100.0 - cost),
                      "late_half_gross_pp": late, "late_half_net_pp": late - cost}
        print("%-20s %6d %6d %+10.4fpp %+8.2f %+8.2f %8.3f %+10.4fpp %+10.4fpp" %
              ("$%.0fM..%s" % (lo / 1e6, "inf" if hi is None else "$%.0fM" % (hi / 1e6)),
               len(g), g["ticker"].nunique(), y.mean() * 100.0, td, tt, cost,
               y.mean() * 100.0 - cost, late))

    n_nocap = int(r["cap"].isna().sum())
    print("\nrows with NO cap observation (in the FULL cell, excluded from every band): %d"
          % n_nocap)
    out = {"item": "INSIDER-WIDE", "part": "disjoint cap bands of the ALREADY-READ check cell",
           "VERDICT": "DIAGNOSTIC -- NO VERDICT",
           "WHY_NO_VERDICT": ("no band was declared in the register, no band has a bar, and "
                              "promoting one after the read is choosing a population on an "
                              "outcome. The registered verdict is the cap>=500M CELL; these "
                              "bands explain where it comes from and may not be quoted as "
                              "results."),
           "late_half_boundary": LATE,
           "rows_with_no_cap_excluded_from_every_band": n_nocap, "bands": bands}
    p = DC.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("wrote %s" % p)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
