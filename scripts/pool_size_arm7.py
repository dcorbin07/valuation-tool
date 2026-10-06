# -*- coding: utf-8 -*-
"""`POOL-SIZE` arm 7 — what removing the penny/nano floor costs. Register §2b.

**IT IS A PAIRED DIFFERENCE, NOT A RUNG LEVEL, and §2b fixed that before any number.** The floor
(`factors.prefilter`: penny below `PRICE_FLOOR`, nano below `MIN_MARKET_CAP_MM`) is applied at
**panel build** time, so this arm needs its own panel — and any panel built today lands on the
**2026-10 export**, whose universe is **3,049 names against the banked panel's 2,531**
(`SHARADAR-REFRESH`). Comparing arm 7's LEVEL against rungs 1-6 would conflate removing the floor
with a wider export and a rolled window.

So: **two panels from ONE export**, prefilter ON and OFF, and the reported figure is the
difference. Placing its level on the main ladder is a void condition.

**THE EXPORT IS PINNED TO THE 2026-08 FREEZE**, not to the live `data/backtest`, because the live
directory has since been refreshed to 2026-10 — pinning both legs to one frozen vintage is what
makes the pair a pair.

Long run: two full panel builds. Launch detached.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

ENV = "EDGE_AUDIT_B13_PREFILTER"


def _build(data_dir, prefilter_on, cache):
    """One panel. `EDGE_AUDIT_B13_PREFILTER=off` disables the floor; `_B13_OFF` is read INSIDE
    `build_fundamental_panel` per call, so toggling between calls is sound (checked, not
    assumed: the read is at fundamental_panel.py's `_B13_OFF` assignment inside the builder)."""
    if os.path.exists(cache):
        print("  reusing %s" % cache, flush=True)
        return pd.read_pickle(cache)

    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _C:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready on %s: %s" % (data_dir, msg))

    if prefilter_on:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = "off"
    print("  building with prefilter %s (%s=%r) ..."
          % ("ON" if prefilter_on else "OFF", ENV, os.environ.get(ENV)), flush=True)

    tickers = prov.universe(limit=None)
    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=63,
    )
    os.environ.pop(ENV, None)
    print("  built %s in %.0fs (%d names, %d dates)"
          % (panel.shape, time.time() - t0, panel["ticker"].nunique(),
             panel["date"].nunique()), flush=True)
    panel.to_pickle(cache)
    return panel


def main(argv=None) -> int:
    from scripts.index_best import data_candidates, _data_root, _ann
    from scripts.pool_size import _roth, _mdd, _sharpe
    from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT

    data = _data_root(required=False)
    if not data:
        raise SystemExit("the licensed data root is absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")
    export = os.path.join(data, "backtest_freeze_2026-08", "backtest")
    if not os.path.isdir(export):
        print("REFUSING: the pinned 2026-08 export is not at %s. Arm 7 needs ONE frozen "
              "vintage for both legs; using the live data/backtest would conflate the floor "
              "with the 2026-10 refresh." % export)
        return 2

    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    full = {"large_cap_min": 0.0, "universe_rank": None, "top_n": None}

    legs = {}
    for tag, on in (("prefilter_on", True), ("prefilter_off", False)):
        cache = os.path.join(fa, "POOL_SIZE_ARM7_PANEL_%s.pkl" % tag)
        panel = _build(export, on, cache)
        r = _roth(panel, cols, weights, full)
        if r is None:
            print("REFUSING: %s produced no result" % tag)
            return 2
        spy = [float(panel[panel["date"] == d]["bench_ret"].iloc[0])
               for d in sorted(panel["date"].unique())]
        r["roth_max_drawdown"] = _mdd(r["net_series"])
        r["roth_sharpe"] = _sharpe(r["net_series"])
        r["spy_ann"] = _ann(spy)
        r["n_names"] = int(panel["ticker"].nunique())
        r["n_dates"] = int(panel["date"].nunique())
        r.pop("net_series", None)
        r.pop("gross_series", None)
        legs[tag] = r
        print("  %-14s roth %.4f  dd %.4f  names %d  dates %d"
              % (tag, r["roth_net_ann"], r["roth_max_drawdown"], r["n_names"], r["n_dates"]),
              flush=True)

    a, b = legs["prefilter_off"], legs["prefilter_on"]
    paired = {
        "d_return_pp": (a["roth_net_ann"] - b["roth_net_ann"]) * 100.0,
        "d_drawdown_pp": (a["roth_max_drawdown"] - b["roth_max_drawdown"]) * 100.0,
        "d_turnover": ((a["annual_turnover"] or 0) - (b["annual_turnover"] or 0)),
        "d_cost_bps": ((a["realised_one_way_bps"] or 0) - (b["realised_one_way_bps"] or 0)),
        "d_names": a["n_names"] - b["n_names"],
        "same_vintage": True,
        "vintage": "backtest_freeze_2026-08",
    }
    res = {"item": "POOL-SIZE", "part": "arm 7 -- penny/nano floor removed (PAIRED DELTA)",
           "trials": 0,
           "register": "PREREG_pool_size.md section 2b",
           "class": "PAIRED DIFFERENCE. Its LEVEL is NOT on the main ladder -- placing it there "
                    "is a void condition, because both legs are built on the 2026-08 export "
                    "while rungs 1-6 use the banked panel.",
           "legs": legs, "paired": paired}
    json.dump(res, io.open(os.path.join(fa, "POOL_SIZE_ARM7.json"), "w", encoding="utf-8"),
              indent=2, default=str)

    print("\n=== ARM 7, PAIRED (floor OFF minus floor ON, one vintage) ===")
    print("  return   %+.2fpp" % paired["d_return_pp"])
    print("  drawdown %+.2fpp" % paired["d_drawdown_pp"])
    print("  turnover %+.3f" % paired["d_turnover"])
    print("  cost     %+.1f bps" % paired["d_cost_bps"])
    print("  names    %+d" % paired["d_names"])
    print("\nwrote %s" % os.path.join(fa, "POOL_SIZE_ARM7.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
