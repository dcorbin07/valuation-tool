# -*- coding: utf-8 -*-
"""`CORRECTED-REBUILD` — prove the three declared changes are ADDITIVE.

    python -m scripts.corrected_rebuild_inert

The rebuild claims exactly three differences from `UNIVERSE-BIAS`'s build: `keep_numbers=True`,
`extra_horizons`, and two new `_KEEP` columns. **If any theme VALUE moved, that claim is false**
and every figure the successors read would be measured on a different object than the one
`CORRECTED-FLOORS` calibrated its floors on.

So the shared columns are compared cell-for-cell on the shared `(date, ticker)` keys. `MB21`'s
rule applies: the compared-cell COUNT is gated, because a perfect 0.000e+00 over an empty
intersection is not a pass.

**ZERO TRIALS** — a control can only BLOCK (`MB1-SEL`).
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

V1 = "UNIVERSE_BIAS_PANEL_full.pkl"
V2 = "UNIVERSE_BIAS_PANEL_full_v2.pkl"
OUT = "CORRECTED_REBUILD_INERT.json"

#: the keys a successor joins on, and the columns whose values must not have moved.
KEYS = ["date", "ticker"]
#: at least this many cells must be compared, or the result is vacuous.
MIN_CELLS = 100000


def fa():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis")


def main(argv=None):
    a = pd.read_pickle(os.path.join(fa(), V1))
    b = pd.read_pickle(os.path.join(fa(), V2))
    print("v1 %s (%d cols) | v2 %s (%d cols)"
          % (a.shape, len(a.columns), b.shape, len(b.columns)), flush=True)

    shared = [c for c in a.columns if c in b.columns and c not in KEYS]
    added = sorted(set(b.columns) - set(a.columns))
    removed = sorted(set(a.columns) - set(b.columns))
    print("shared %d | added %d | removed %d" % (len(shared), len(added), len(removed)),
          flush=True)
    if removed:
        print("  REMOVED: %s" % removed, flush=True)

    ka = a.assign(_d=a["date"].astype(str))[["_d", "ticker"]]
    kb = b.assign(_d=b["date"].astype(str))[["_d", "ticker"]]
    sa = set(map(tuple, ka.values))
    sb = set(map(tuple, kb.values))
    print("keys v1 %d | v2 %d | identical %s" % (len(sa), len(sb), sa == sb), flush=True)

    A = a.assign(_d=a["date"].astype(str)).set_index(["_d", "ticker"]).sort_index()
    B = b.assign(_d=b["date"].astype(str)).set_index(["_d", "ticker"]).sort_index()
    common = A.index.intersection(B.index)
    A, B = A.loc[common], B.loc[common]

    moved, cells = {}, 0
    for c in shared:
        x = pd.to_numeric(A[c], errors="coerce")
        y = pd.to_numeric(B[c], errors="coerce")
        both = x.notna() & y.notna()
        n = int(both.sum())
        cells += n
        if n:
            dev = float(np.max(np.abs(x[both].values - y[both].values)))
        else:
            dev = None
        nn = (int(x.isna().sum()), int(y.isna().sum()))
        if (dev is not None and dev != 0.0) or nn[0] != nn[1]:
            moved[c] = {"max_abs_dev": dev, "nulls_v1": nn[0], "nulls_v2": nn[1],
                        "cells_compared": n}

    ok = (sa == sb) and not removed and not moved and cells >= MIN_CELLS
    print("\ncells compared %d (floor %d)" % (cells, MIN_CELLS), flush=True)
    print("columns whose values MOVED: %d" % len(moved), flush=True)
    for c, d in list(moved.items())[:12]:
        print("   %-24s %s" % (c, d), flush=True)
    print("\n-> %s" % ("ADDITIVE: the three changes moved no shared value" if ok
                       else "*** NOT ADDITIVE ***"), flush=True)

    res = {
        "item": "CORRECTED-REBUILD", "part": "inertness control", "trials": 0,
        "trial_class": "CONTROL -- can only BLOCK (MB1-SEL)",
        "v1": V1, "v2": V2,
        "shape_v1": list(a.shape), "shape_v2": list(b.shape),
        "shared_columns": len(shared), "added_columns": added, "removed_columns": removed,
        "key_sets_identical": bool(sa == sb),
        "cells_compared": cells, "min_cells_gate": MIN_CELLS,
        "columns_moved": moved,
        "additive": bool(ok),
        "note": "the three declared changes are keep_numbers=True, extra_horizons and two new "
                "_KEEP columns. If any shared theme value had moved, the successors would be "
                "reading a different object than the one CORRECTED-FLOORS calibrated on. The "
                "cell COUNT is gated because a perfect zero over an empty intersection is not a "
                "pass (MB21).",
    }
    with io.open(os.path.join(fa(), OUT), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("wrote %s" % os.path.join(fa(), OUT), flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
