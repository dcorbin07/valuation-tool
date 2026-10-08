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
V2 = "UNIVERSE_BIAS_PANEL_full_v3.pkl"
OUT = "CORRECTED_REBUILD_INERT.json"

#: the v2->v3 horizon repair. v2 omitted `fwd_ret_h63` on the reasoning that 63 duplicates
#: the panel's own `horizon`; it does not -- `fundamental_panel`'s own comment reads *"the
#: BASE horizon is allowed here and is the study's C0 control: fwd_ret_h63 must equal
#: fwd_ret exactly"*, and `term_structure.main` reads it directly. Every ARM was unaffected
#: (`ret_col(63)` returns `fwd_ret`), so the CONTROL was the only casualty.
V2_OLD = "UNIVERSE_BIAS_PANEL_full_v2.pkl"
OUT_V2_V3 = "CORRECTED_REBUILD_V2_V3.json"
#: the repair must add EXACTLY this and nothing else.
V3_ADDS = ["fwd_ret_h63"]

#: the keys a successor joins on, and the columns whose values must not have moved.
KEYS = ["date", "ticker"]
#: at least this many cells must be compared, or the result is vacuous.
MIN_CELLS = 100000


def fa():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis")


def compare_shared(A, B, shared):
    """Cell-for-cell comparison of `shared` columns on two key-aligned frames.

    Returns `(moved, cells)` -- `moved` maps a column to why it moved, `cells` is the number of
    cells actually compared, which the caller MUST gate on (`MB21`: a perfect zero over an empty
    intersection is not a pass).

    **COERCE TO NUMERIC AND COMPARE THE NULL MASKS. NEVER `astype(str)`.** Under pandas 3
    `astype(str)` on an all-`None` object column yields `pd.NA`, and `pd.NA == pd.NA` is not
    True -- so a string fallback reports provably identical empty columns as moved on every row.
    A scratch implementation of this function did exactly that and made a bit-identical pair
    read NOT ADDITIVE; `MA_FINAL_BATCH` hit the same language feature from the other side, with
    a blank counter reading 0 on 1.5M blanks. An all-empty column compares as EQUAL here because
    neither side has a value to disagree about, and the null COUNTS are checked separately so a
    column that gained or lost values still shows up.

    One definition, two callers (`B7`): the lean->v3 inertness proof and the v2->v3 repair.
    """
    moved, cells = {}, 0
    for c in shared:
        x = pd.to_numeric(A[c], errors="coerce")
        y = pd.to_numeric(B[c], errors="coerce")
        both = x.notna() & y.notna()
        n = int(both.sum())
        cells += n
        if n:
            # CAST TO FLOAT BEFORE SUBTRACTING. `to_numeric` leaves a boolean column
            # boolean, and numpy refuses `-` on bools -- which only surfaced once a
            # BOOLEAN column entered the shared set (the lean panel has none, so the
            # lean->v3 proof never exercised this path). A comparison that raises on a
            # dtype it has not met is a comparison that has not been exercised.
            dev = float(np.max(np.abs(x[both].values.astype(float)
                                      - y[both].values.astype(float))))
        else:
            dev = None
        nn = (int(x.isna().sum()), int(y.isna().sum()))
        if (dev is not None and dev != 0.0) or nn[0] != nn[1]:
            moved[c] = {"max_abs_dev": dev, "nulls_v1": nn[0], "nulls_v2": nn[1],
                        "cells_compared": n}
    return moved, cells


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

    moved, cells = compare_shared(A, B, shared)

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


def v2_v3():
    """The horizon repair: v3 must be v2 plus `fwd_ret_h63` and nothing else.

    Uses `compare_shared` -- the SAME function the lean->v3 proof uses (`B7`). A scratch second
    implementation of it fell back to `astype(str)` and reported four provably identical EMPTY
    columns as moved, because under pandas 3 `astype(str)` on an all-`None` object column yields
    `pd.NA` and `pd.NA == pd.NA` is not True. One definition, two callers.
    """
    f = fa()
    pa, pb = os.path.join(f, V2_OLD), os.path.join(f, V2)
    for q in (pa, pb):
        if not os.path.exists(q):
            raise SystemExit("REFUSING: %s is absent, so the repair cannot be proved additive"
                             % q)
    a, b = pd.read_pickle(pa), pd.read_pickle(pb)
    print("v2 %s | v3 %s" % (a.shape, b.shape), flush=True)

    sca, scb = set(a.columns), set(b.columns)
    added, removed = sorted(scb - sca), sorted(sca - scb)
    shared = sorted(sca & scb)
    print("shared %d | added %s | removed %s" % (len(shared), added, removed), flush=True)

    A = a.assign(_d=a["date"].astype(str)).set_index(["_d", "ticker"]).sort_index()
    B = b.assign(_d=b["date"].astype(str)).set_index(["_d", "ticker"]).sort_index()
    ka = set(map(tuple, a.assign(_d=a["date"].astype(str))[["_d", "ticker"]].values))
    kb = set(map(tuple, b.assign(_d=b["date"].astype(str))[["_d", "ticker"]].values))
    common = A.index.intersection(B.index)
    A, B = A.loc[common], B.loc[common]

    moved, cells = compare_shared(A, B, [c for c in shared if c not in KEYS])
    ok = ((ka == kb) and not removed and not moved and cells >= MIN_CELLS
          and added == V3_ADDS)
    print("\ncells compared %d (floor %d)" % (cells, MIN_CELLS), flush=True)
    print("columns whose values MOVED: %d" % len(moved), flush=True)
    for c, d in list(moved.items())[:12]:
        print("   %-28s %s" % (c, d), flush=True)
    print("\n-> %s" % ("ADDITIVE: v3 is v2 plus fwd_ret_h63 and nothing else" if ok
                        else "NOT ADDITIVE -- investigate before anything reads v3"), flush=True)

    res = {
        "item": "CORRECTED-REBUILD -- the v2 -> v3 horizon repair",
        "trials": 0,
        "trial_class": "CONTROL -- can only BLOCK (MB1-SEL)",
        "v2": V2_OLD, "v3": V2,
        "shape_v2": list(a.shape), "shape_v3": list(b.shape),
        "shared_columns": len(shared), "added_columns": added, "removed_columns": removed,
        "added_must_equal": V3_ADDS,
        "key_sets_identical": bool(ka == kb),
        "cells_compared": cells, "min_cells_gate": MIN_CELLS,
        "columns_moved": moved,
        "additive": bool(ok),
        "why_the_repair_exists": (
            "v2 set extra_horizons to S22's grid MINUS its base, on the reasoning that 63 "
            "duplicates the panel's own `horizon`. It does not duplicate it: it is the input to "
            "S22's own C0 control, and fundamental_panel's comment says so in terms. Every ARM "
            "was unaffected because ret_col(63) returns `fwd_ret`, so the CONTROL was the only "
            "casualty -- which is why a test asserting every S22 horizon column exists PASSED "
            "while S22 raised KeyError. Copying fwd_ret into fwd_ret_h63 would have made C0 "
            "pass BY CONSTRUCTION, which is worse than the crash."),
        "what_this_licenses": (
            "a measurement reading only columns the two panels share is IDENTICAL BY PROOF on "
            "either, so score_calibration's v2-era artifact stands without a re-run"),
        "C0_exactness_is_reported_by_S22_itself": (
            "not re-derived here -- a second definition of one control is how two numbers for "
            "one question come about (B7)"),
    }
    with io.open(os.path.join(f, OUT_V2_V3), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("wrote %s" % os.path.join(f, OUT_V2_V3), flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    if "--v2-v3" in sys.argv:
        sys.exit(v2_v3())
    sys.exit(main())
