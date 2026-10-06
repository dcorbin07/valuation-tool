# -*- coding: utf-8 -*-
"""`POOL-SIZE` part (b) — the pool-size curve on 1999-2008, a LABELLED PROXY. READ ONCE.

Register `PREREG_pool_size.md` §4.

**WHAT THIS IS AND IS NOT.** It tests **POOL WIDTH** out of sample. It does **NOT** test the
shipped seven-theme composite and may never be quoted as doing so: `institutional` has **zero**
pre-2009 source (`sf3` starts 2013-06-30) and `insider` reaches only **0.307** by 2008 against
the **70%** rule — both re-confirmed on the renewed export by `PANEL-EXT-RECHECK`. **So this
scores a FIVE-theme composite**: value, quality, momentum, capital_discipline, size.

**ONE PANEL IMPLEMENTATION.** `build_fundamental_panel` is CALLED against the full-universe
pre-2009 export `pool_size_oos_prep` wrote. The `B6` one-shared-calendar-cut rule, the terminal
value for delisted names and the SF1 publication lag are all the shipped builder's own — not
reimplemented here, which is the whole reason the export route was chosen over a bespoke panel.

**READ ONCE.** The curve is computed once and reported. No second cut, no re-ranked ladder, no
sweep. §4 says a failure to build correctly is reported as a failure, not worked around.
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

#: The five themes that exist before 2009. `insider` and `institutional` are EXCLUDED BY
#: MEASUREMENT, not by preference -- see the module docstring.
THEMES_PRE2009 = ("value", "quality", "momentum", "capital_discipline", "size")

#: The same ladder shape as part (a). The top rung is the full pre-2009 universe.
OOS_RUNGS = [
    ("1_top500",   {"large_cap_min": 0.0, "universe_rank": 500, "top_n": None}),
    ("2_top1000",  {"large_cap_min": 0.0, "universe_rank": 1000, "top_n": None}),
    ("3_top1500",  {"large_cap_min": 0.0, "universe_rank": 1500, "top_n": None}),
    ("4_top2000",  {"large_cap_min": 0.0, "universe_rank": 2000, "top_n": None}),
    ("5_full",     {"large_cap_min": 0.0, "universe_rank": None, "top_n": None}),
]


def build(export, bulk_dir, cache):
    if os.path.exists(cache):
        print("  reusing %s" % cache, flush=True)
        return pd.read_pickle(cache)
    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _C:
        wrds_data_dir = export

    prov = WRDSProvider(_C())
    # point at the EXISTING bulk cache -- it is already full-universe and already reaches
    # 1998-12-01, and overwriting the shared one would break every 2009-2026 build.
    prov._bulk_dir = bulk_dir
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready on %s: %s" % (export, msg))
    tickers = prov.universe(limit=None)
    print("  universe from the export's own fundamentals index: %d names" % len(tickers),
          flush=True)
    t0 = time.time()
    panel = build_fundamental_panel(prov, tickers,
                                    rebalance_days=CONFIG.backtest_rebalance_days,
                                    lookback_years=CONFIG.backtest_lookback_years,
                                    horizon=63)
    print("  built %s in %.0fs (%d names, %d dates)"
          % (panel.shape, time.time() - t0, panel["ticker"].nunique(),
             panel["date"].nunique()), flush=True)
    panel.to_pickle(cache)
    return panel


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates, _ann
    from scripts.pool_size import _roth, _mdd, _sharpe, DD_ALLOWANCE, decide
    from scripts.sector_neutral_rerun import BASE_WEIGHT

    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")
    export = os.path.join(data, "oos1999", "backtest")
    bulk = os.path.join(data, "bulk", "prepared")
    if not os.path.isdir(export):
        print("REFUSING: no pre-2009 export at %s. Run scripts.pool_size_oos_prep first."
              % export)
        return 2

    panel = build(export, bulk, os.path.join(fa, "POOL_SIZE_OOS_PANEL.pkl"))
    grid = sorted(panel["date"].unique())
    if not grid:
        print("REFUSING: the pre-2009 panel has no rebalance dates.")
        return 2

    cols = [c for c in THEMES_PRE2009 if c in panel.columns]
    missing = [c for c in THEMES_PRE2009 if c not in panel.columns]
    weights = {c: BASE_WEIGHT for c in cols}
    print("themes scored: %r%s" % (cols, (" MISSING %r" % missing) if missing else ""),
          flush=True)
    print("grid: %d dates, %s .. %s" % (len(grid), str(grid[0])[:10], str(grid[-1])[:10]),
          flush=True)

    spy = [float(panel[panel["date"] == d]["bench_ret"].iloc[0]) for d in grid]

    scored = {}
    for name, kw in OOS_RUNGS:
        r = _roth(panel, cols, weights, kw)
        if r is None:
            print("  %-12s no result" % name, flush=True)
            continue
        r["knobs"] = kw
        r["roth_max_drawdown"] = _mdd(r["net_series"])
        r["roth_sharpe"] = _sharpe(r["net_series"])
        r["spy_ann"] = _ann(spy)
        r["roth_excess_vs_spy"] = r["roth_net_ann"] - r["spy_ann"]
        scored[name] = r
        print("  %-12s roth %.4f  dd %.4f  turn %s  cost %s"
              % (name, r["roth_net_ann"], r["roth_max_drawdown"],
                 ("%.3f" % r["annual_turnover"]) if r["annual_turnover"] else "n/a",
                 ("%.1f" % r["realised_one_way_bps"]) if r["realised_one_way_bps"] else "n/a"),
              flush=True)

    order = [n for n, _ in OOS_RUNGS if n in scored]
    dec = decide(order, scored) if len(order) > 1 else None

    res = {
        "item": "POOL-SIZE", "part": "b 1999-2008 PROXY", "trials": 1,
        "register": "PREREG_pool_size.md section 4",
        "LABEL": "A PROXY FOR POOL WIDTH, NOT A TEST OF THE SHIPPED COMPOSITE. Five themes "
                 "only -- institutional has ZERO pre-2009 source (sf3 starts 2013-06-30) and "
                 "insider reaches 0.307 by 2008 against the 70%% rule. Quoting it as a test of "
                 "the seven-theme composite is a void condition.",
        "themes_scored": cols, "themes_missing": missing,
        "n_dates": len(grid), "first": str(grid[0])[:10], "last": str(grid[-1])[:10],
        "n_names": int(panel["ticker"].nunique()),
        "spy_ann": _ann(spy),
        "rungs": {k: {kk: vv for kk, vv in v.items() if kk != "net_series"}
                  for k, v in scored.items()},
        "decision": dec,
        "holdout_spent": "the LATE PORTION of RESEARCH_CHARTER section 4a's 1990-2008 era. The "
                         "boundary is 1990, not 1998, so 1990-1998 is left a stub of an era "
                         "meant to be read whole, out of the charter's own era order. Disclosed "
                         "in the register before the run.",
        "read_once": True,
    }
    json.dump(res, io.open(os.path.join(fa, "POOL_SIZE_OOS.json"), "w", encoding="utf-8"),
              indent=2, default=str)

    print("\n=== 1999-2008 PROXY LADDER (five themes) ===")
    print("%-12s %9s %9s %9s" % ("rung", "roth/yr", "vs SPY", "maxDD"))
    for n in order:
        r = scored[n]
        print("%-12s %8.2f%% %8.2f%% %8.2f%%"
              % (n, r["roth_net_ann"] * 100, r["roth_excess_vs_spy"] * 100,
                 r["roth_max_drawdown"] * 100))
    if dec:
        print("\n=== DON'S RULE ON THE PROXY ===")
        for st in dec["steps"]:
            if st.get("ok") is None:
                continue
            print("  %-12s vs %-12s dRet %+6.2fpp  dDD %+6.2fpp -> %s"
                  % (st["rung"], st["vs"], st["d_return_pp"], st["d_drawdown_pp"],
                     "CLEARS" if st["ok"] else "fails"))
        print("  literal: %s | cumulative: %s | agree: %s"
              % (dec["recommended_LITERAL_primary"],
                 dec["recommended_CUMULATIVE_sensitivity"], dec["readings_agree"]))
    print("\nwrote %s" % os.path.join(fa, "POOL_SIZE_OOS.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
