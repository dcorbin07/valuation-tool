# -*- coding: utf-8 -*-
"""INDEX-CHOICE item 3 -- how much of arms 2 and 3 is a size/momentum TILT rather than
selection? Executes PREREG_index_choice.md section 3. 1 of the item's 3 equity trials.

`R1`'s MACHINERY IS CALLED, NOT REIMPLEMENTED (`B7`): `ols_nw`, `regress`, `factor_windows` and
`FF_MODEL` all come from `scripts/factor_alpha.py`. Newey-West at lag 1, which is `R1`'s own
choice on non-overlapping 63-day windows.

TWO OBJECTS PER ARM, because Don's question has two readings and they answer different things:

  * the arm IN EXCESS OF RF -- what the book is made of. This is `R1`'s long-only object.
  * the arm MINUS THE INCUMBENT -- what the CHANGE is made of. This is the decision-relevant
    one: Don is choosing whether to move, so the question is what the MOVE loads on. It is a
    spread, so no RF subtraction is needed or applied.

NO ALPHA VERDICT IS TAKEN, AND THE REASON IS PRE-COMMITTED IN SECTION 3 OF THE REGISTER RATHER
THAN DISCOVERED HERE. `R1` pre-registered *"'alpha' only if the FF5+MOM intercept is positive
with NW t > 2.0"* and earned the word on the full panel. This item does not inherit that
licence: these are NEW constructions whose selection `INDEX-BEST` already measured as not
separable from the incumbent's, `INDEX-BEST` found EVERY arm's advantage carried by the late
half (which a full-sample intercept cannot see), and `R1`'s own fragility work found a ~10-year
window at t 1.39 with 8 of 70 rolling windows insignificant. **A positive intercept here is a
DECOMPOSITION and the write-up may not call it alpha.**
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

from valuation.studies import served_index_book as IB                     # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                       # noqa: E402
from valuation.edge.fundamental_panel import after_tax_backtest as at_bt  # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT            # noqa: E402
# R1's own estimator, report packaging, factor windows and model -- imported, not restated.
from scripts import factor_alpha as FAC                                   # noqa: E402
from scripts.index_best import (ARMS, data_candidates, _data_root)        # noqa: E402

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "INDEX_CHOICE_FACTORS.json") if FA else None
FACTOR_DIR = os.path.join(DATA, "factors", "parsed") if DATA else None
LAG = 1                                  # R1's own choice
CHOICE = ("1_incumbent_10bn", "2_liquid_decile", "3_liquid_top25")


def _net_series(panel, cols, weights, kw):
    bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
    r = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
              short_rate=0.0, long_rate=0.0, return_series=True)
    return list(r["series"]["net"])


def main(choice=CHOICE, out=None, item="INDEX-CHOICE", part="3 factor loadings",
         register="PREREG_index_choice.md section 3") -> int:
    """`choice`/`out`/`item` DEFAULT TO THIS ITEM'S OWN, so every existing caller is
    bit-identical and `INDEX-CHOICE`'s void condition 2 is untouched. They are
    parameters so `INDEX-CHOICE-ARM4` can run THE SAME decomposition on a different arm
    set, writing its OWN artifact -- reusing the path would CLOBBER a landed one."""
    out = out or OUT
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    FAC.set_factor_dir(FACTOR_DIR)       # a worktree carries no data/; R1 built this hook
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    grid = sorted(panel["date"].unique())

    F = FAC.factor_windows(grid)
    print("factor windows: %d for %d rebalance dates | cols %s"
          % (len(F), len(grid), [c for c in F.columns][:9]), flush=True)

    series = {k: _net_series(panel, cols, weights, kw)
              for k, kw, _l, _b in ARMS if k in choice}
    m = min(len(F), min(len(v) for v in series.values()))
    F = F.iloc[:m].reset_index(drop=True)
    print("aligned on %d windows (the last rebalance date closes no window)" % m, flush=True)

    res = {"item": item, "part": part, "trials": 1,
           "register": register,
           "model": list(FAC.FF_MODEL), "lag": LAG, "n_windows": int(m),
           "machinery": "scripts/factor_alpha.py -- ols_nw, regress, factor_windows, FF_MODEL "
                        "IMPORTED and called (B7)",
           "no_alpha_verdict": "pre-committed in register section 3: a positive intercept here "
                               "is a DECOMPOSITION, never alpha",
           "arms": {}}

    # ---- R1's OWN ALIGNMENT CONTROL: SPY's excess on MKT should give beta ~1, R2 ~1 --------
    bench = [float(panel[panel["date"] == d]["bench_ret"].iloc[0]) for d in grid][:m]
    v = pd.DataFrame({"bench": bench, "MKT": F["MKT"].values, "RF": F["RF"].values}).dropna()
    b = FAC.ols_nw((v["bench"] - v["RF"]).values, v[["MKT"]].values, lag=LAG)
    res["alignment_control"] = {"spy_on_mkt_beta": float(b["beta"][1]), "r2": float(b["r2"]),
                                "n": int(b["n"]),
                                "note": "R1's own control. A beta far from 1 or a low R2 would "
                                        "mean the factor windows do not line up with this "
                                        "panel's grid, and every loading below would be noise."}
    print("ALIGNMENT SPY excess ~ MKT: beta %.4f  R2 %.4f  n %d"
          % (b["beta"][1], b["r2"], b["n"]), flush=True)

    inc = np.asarray(series["1_incumbent_10bn"][:m], dtype=float)
    for name in choice:
        y = np.asarray(series[name][:m], dtype=float)
        a = {}
        # (a) the book itself, in excess of RF -- R1's long-only object
        a["excess_of_rf"] = FAC.regress(y - F["RF"].values, F, list(FAC.FF_MODEL),
                                        "%s in excess of RF" % name, lag=LAG)
        # (b) the CHANGE from the incumbent -- a spread, so no RF
        if name != "1_incumbent_10bn":
            a["minus_incumbent"] = FAC.regress(y - inc, F, list(FAC.FF_MODEL),
                                               "%s minus incumbent" % name, lag=LAG)
        res["arms"][name] = a
        r = a["excess_of_rf"]
        print("\n%s  (in excess of RF)" % name, flush=True)
        print("  intercept %+.4f/yr  t %+.3f  R2 %.4f" % (r["alpha_ann"], r["alpha_t_nw"],
                                                           r["r2"]), flush=True)
        print("  " + "  ".join("%s %+.3f(t%+.2f)" % (c, r["loadings"][c]["beta"],
                                                      r["loadings"][c]["t"])
                               for c in FAC.FF_MODEL), flush=True)
        if "minus_incumbent" in a:
            q = a["minus_incumbent"]
            print("  MINUS INCUMBENT: intercept %+.4f/yr t %+.3f R2 %.4f"
                  % (q["alpha_ann"], q["alpha_t_nw"], q["r2"]), flush=True)
            print("  " + "  ".join("%s %+.3f(t%+.2f)" % (c, q["loadings"][c]["beta"],
                                                          q["loadings"][c]["t"])
                                   for c in FAC.FF_MODEL), flush=True)

    # How much of each arm's RAW excess the factors explain, which is Don's question in one
    # number. Reported for the spread, because that is the object a MOVE would buy.
    for name in choice:
        if "minus_incumbent" not in res["arms"][name]:
            continue
        q = res["arms"][name]["minus_incumbent"]
        res["arms"][name]["tilt_share_of_the_move"] = {
            "raw_ann": q["raw_ann"], "intercept_ann": q["alpha_ann"],
            "explained_by_factors_ann": q["raw_ann"] - q["alpha_ann"],
            "share_explained": (None if q["raw_ann"] == 0 else
                                (q["raw_ann"] - q["alpha_ann"]) / q["raw_ann"]),
            "note": "raw minus intercept is what the FACTOR LOADINGS account for; the "
                    "intercept is what is left. NOT an alpha claim (register section 3).",
        }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
