# -*- coding: utf-8 -*-
"""`POOL-SIZE` — FF5+MOM loadings for every rung. Register `PREREG_pool_size.md` §3.

**IT RE-RUNS NO BOOK.** The per-period net series are already banked in
`POOL_SIZE_LADDER.json`, so this reads them and regresses. Re-forming the books would be a
second path to the same series and `B7` is exactly about not having two.

`factor_alpha`'s own machinery is CALLED: `set_factor_dir`, `factor_windows`, `ols_nw`,
`regress`, `FF_MODEL`, at `R1`'s `LAG = 1`.

**NO ALPHA CLAIM.** `INDEX-CHOICE` forbade one in advance — the arms are not separable from each
other and the whole effect is late-half — and `POOL-SIZE` inherits that prohibition rather than
re-arguing it. An intercept here is a **decomposition**.
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

from scripts import factor_alpha as FAC                                   # noqa: E402
from scripts.index_best import data_candidates, _data_root                # noqa: E402

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
LADDER = os.path.join(FA, "POOL_SIZE_LADDER.json") if FA else None
OUT = os.path.join(FA, "POOL_SIZE_FACTORS.json") if FA else None
# `parsed`, not `factors` -- `index_choice_factors` points at the same subdirectory, and
# the raw downloads one level up are not what `factor_windows` reads.
FACTOR_DIR = os.path.join(DATA, "factors", "parsed") if DATA else None

LAG = 1                                  # R1's own choice


def main(argv=None) -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    if not os.path.exists(LADDER):
        print("REFUSING: no ladder artifact at %s. Run scripts.pool_size first." % LADDER)
        return 2
    lad = json.load(io.open(LADDER, encoding="utf-8"))
    if not (lad.get("c1") or {}).get("ok"):
        print("REFUSING: the ladder artifact does not record a passing C1.")
        return 2

    FAC.set_factor_dir(FACTOR_DIR)
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    grid = sorted(panel["date"].unique())
    F = FAC.factor_windows(grid)

    rungs = lad["rungs"]
    order = [k for k, _ in __import__("scripts.pool_size", fromlist=["RUNGS"]).RUNGS
             if k in rungs]
    m = min(len(F), min(len(rungs[k]["net_series"]) for k in order))
    F = F.iloc[:m].reset_index(drop=True)
    print("factor windows %d, aligned on %d (the last rebalance closes no window)"
          % (len(F), m), flush=True)

    res = {"item": "POOL-SIZE", "part": "FF5+MOM loadings", "trials": 1,
           "register": "PREREG_pool_size.md section 3",
           "model": list(FAC.FF_MODEL), "lag": LAG, "n_windows": int(m),
           "machinery": "scripts/factor_alpha.py -- ols_nw, regress, factor_windows, FF_MODEL "
                        "IMPORTED and called (B7); the net series are READ from "
                        "POOL_SIZE_LADDER.json rather than re-formed",
           "no_alpha_verdict": "pre-committed: an intercept here is a DECOMPOSITION, never "
                               "alpha (inherited from INDEX-CHOICE)",
           "rungs": {}}

    # R1's OWN alignment control: SPY's excess on MKT must give beta ~1 and R2 ~1, or the
    # factor windows do not line up with this grid and every loading below is noise.
    bench = [float(panel[panel["date"] == d]["bench_ret"].iloc[0]) for d in grid][:m]
    v = pd.DataFrame({"bench": bench, "MKT": F["MKT"].values,
                      "RF": F["RF"].values}).dropna()
    b = FAC.ols_nw((v["bench"] - v["RF"]).values, v[["MKT"]].values, lag=LAG)
    res["alignment_control"] = {"spy_on_mkt_beta": float(b["beta"][1]), "r2": float(b["r2"]),
                                "n": int(b["n"]),
                                "note": "R1's own control; a beta far from 1 would mean the "
                                        "windows do not line up and the loadings are noise."}
    print("ALIGNMENT SPY excess ~ MKT: beta %.4f R2 %.4f n %d"
          % (b["beta"][1], b["r2"], b["n"]), flush=True)

    inc = np.asarray(rungs[order[0]]["net_series"][:m], dtype=float)
    for k in order:
        y = np.asarray(rungs[k]["net_series"][:m], dtype=float)
        a = {"excess_of_rf": FAC.regress(y - F["RF"].values, F, list(FAC.FF_MODEL),
                                         "%s in excess of RF" % k, lag=LAG)}
        if k != order[0]:
            a["minus_incumbent"] = FAC.regress(y - inc, F, list(FAC.FF_MODEL),
                                               "%s minus incumbent" % k, lag=LAG)
        res["rungs"][k] = a
        r = a["excess_of_rf"]
        print("\n%s (excess of RF)  intercept %+.4f/yr t %+.3f  R2 %.4f"
              % (k, r["alpha_ann"], r["alpha_t_nw"], r["r2"]), flush=True)
        print("  " + "  ".join("%s %+.3f(t%+.2f)" % (c, r["loadings"][c]["beta"],
                                                     r["loadings"][c]["t"])
                               for c in FAC.FF_MODEL), flush=True)

    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, default=str)
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
