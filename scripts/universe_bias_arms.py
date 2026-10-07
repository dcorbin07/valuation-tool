# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 2b — the POOL-SIZE ladder on the CORRECTED 2009-2026 universe.

**ZERO TRIALS.** Every arm here is already registered: the incumbent is `INDEX-BEST`'s, the
rungs and the decision rule are `PREREG_pool_size.md`'s, and the decision rule was fixed before
any number was read. This re-measures those arms on a corrected universe — the
`S25` / `X7RECON` / `PANEL-EXT-RECHECK` correction class, which charges nothing because it adds
no hypothesis, no bar and no degree of freedom. **A correction that moves a published figure is
still a correction, not a search.**

**TWO PANELS, ONE VINTAGE, ONE DIFFERENCE.** Both are built by the SHIPPED
`build_fundamental_panel` from the **2026-10** freeze with identical parameters:

  * **restricted** — `data/backtest`, the top-3,000-by-**2026**-cap universe the published
    figure uses;
  * **full** — `data/full2009/backtest`, every name with an in-window close and SF1 coverage.

So the universe is the only thing that varies. Comparing the full panel against the **banked**
`panel_corrected_69d.pkl` instead would conflate it with a rolled window
(`SHARADAR-REFRESH`: 2,531 names at 2026-07-24 against 3,049 at 2026-10-02), and that confound
is exactly what this item exists to remove rather than add.

**ALL SEVEN THEMES**, unlike the 1999-2008 proxy — this window has `institutional` and `insider`.

**THE PUBLISHED 17.16% IS THE REFERENCE, AND IT CARRIES ITS OWN VINTAGE.** It was measured on the
banked panel at the 2026-07-24 vintage, so the restricted panel here is its near-neighbour and
not its reproduction; the gap between them is reported rather than assumed to be zero.
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

#: `INDEX-BEST`'s published incumbent, for reference only -- a DIFFERENT vintage (2026-07-24).
PUBLISHED_INCUMBENT_ROTH = 0.1716188056513155
PUBLISHED_VINTAGE = "banked panel_corrected_69d.pkl, available_end 2026-07-24, 2,531 names"

#: The ladder the user asked for: incumbent plus 500 / 1,000 / 1,500 / full.
ARMS = [
    ("1_incumbent_10bn", {"large_cap_min": 1e10, "universe_rank": None, "top_n": None}),
    ("2_top500",         {"large_cap_min": 0.0, "universe_rank": 500, "top_n": None}),
    ("3_top1000",        {"large_cap_min": 0.0, "universe_rank": 1000, "top_n": None}),
    ("4_top1500",        {"large_cap_min": 0.0, "universe_rank": 1500, "top_n": None}),
    ("5_full",           {"large_cap_min": 0.0, "universe_rank": None, "top_n": None}),
]


def build(export, bulk_dir, cache, label):
    if os.path.exists(cache):
        print("  reusing %s" % cache, flush=True)
        return pd.read_pickle(cache)
    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _C:
        wrds_data_dir = export

    prov = WRDSProvider(_C())
    prov._bulk_dir = bulk_dir            # already full-universe; NOT rebuilt, NOT overwritten
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready on %s: %s" % (export, msg))
    tickers = prov.universe(limit=None)
    print("  [%s] universe from the export's own fundamentals index: %d names"
          % (label, len(tickers)), flush=True)
    t0 = time.time()
    panel = build_fundamental_panel(prov, tickers,
                                    rebalance_days=CONFIG.backtest_rebalance_days,
                                    lookback_years=CONFIG.backtest_lookback_years,
                                    horizon=63)
    print("  [%s] built %s in %.0fs (%d names, %d dates)"
          % (label, panel.shape, time.time() - t0, panel["ticker"].nunique(),
             panel["date"].nunique()), flush=True)
    panel.to_pickle(cache)
    return panel


def score(panel, label):
    from scripts.index_best import _ann
    from scripts.pool_size import _roth, _mdd, _sharpe
    from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT

    cols = [c for c in DEPLOYED if c in panel.columns]
    missing = [c for c in DEPLOYED if c not in panel.columns]
    weights = {c: BASE_WEIGHT for c in cols}
    grid = sorted(panel["date"].unique())
    spy = [float(panel[panel["date"] == d]["bench_ret"].iloc[0]) for d in grid]
    mid = len(grid) // 2
    early, late = set(grid[:mid]), set(grid[mid + 1:])

    out = {"themes": cols, "themes_missing": missing, "n_dates": len(grid),
           "n_names": int(panel["ticker"].nunique()),
           "first": str(grid[0])[:10], "last": str(grid[-1])[:10],
           "spy_ann": _ann(spy), "arms": {}}
    print("  [%s] %d names, %d dates, %s .. %s, themes %d%s"
          % (label, out["n_names"], len(grid), out["first"], out["last"], len(cols),
             (" MISSING %r" % missing) if missing else ""), flush=True)

    for name, kw in ARMS:
        r = _roth(panel, cols, weights, kw)
        if r is None:
            print("    %-18s no result" % name, flush=True)
            continue
        ns = r["net_series"]
        e = [ns[i] for i, d in enumerate(grid[:len(ns)]) if d in early]
        l = [ns[i] for i, d in enumerate(grid[:len(ns)]) if d in late]
        r["knobs"] = kw
        r["roth_max_drawdown"] = _mdd(ns)
        r["roth_sharpe"] = _sharpe(ns)
        r["roth_excess_vs_spy"] = r["roth_net_ann"] - out["spy_ann"]
        r["early_roth_ann"] = _ann(e) if e else None
        r["late_roth_ann"] = _ann(l) if l else None
        # the net series is KEPT so the factor loadings can be read off this same object
        # rather than re-forming the books a second time (`B7`).
        r["net_series"] = [float(x) for x in ns]
        r.pop("gross_series", None)
        out["arms"][name] = r
        print("    %-18s roth %.4f  dd %.4f  turn %s  cost %s"
              % (name, r["roth_net_ann"], r["roth_max_drawdown"],
                 ("%.3f" % r["annual_turnover"]) if r["annual_turnover"] else "n/a",
                 ("%.1f" % r["realised_one_way_bps"]) if r["realised_one_way_bps"] else "n/a"),
              flush=True)
    return out


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    from scripts.pool_size import decide

    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")
    bulk = os.path.join(data, "bulk", "prepared")
    full_export = os.path.join(data, "full2009", "backtest")
    if not os.path.isdir(full_export):
        print("REFUSING: no full-universe export at %s. Run scripts.universe_bias_prep first."
              % full_export)
        return 2

    sides = {}
    for label, export, cache in (
            ("restricted", os.path.join(data, "backtest"),
             os.path.join(fa, "UNIVERSE_BIAS_PANEL_restricted.pkl")),
            ("full", full_export,
             os.path.join(fa, "UNIVERSE_BIAS_PANEL_full.pkl"))):
        panel = build(export, bulk, cache, label)
        sides[label] = score(panel, label)

    # the decision rule, applied to BOTH sides. It is PREREG_pool_size.md's, unchanged.
    for label in sides:
        a = sides[label]["arms"]
        order = [n for n, _ in ARMS if n in a]
        sides[label]["decision"] = decide(order, a) if len(order) > 1 else None

    r, f = sides["restricted"], sides["full"]
    comp = {}
    for name, _kw in ARMS:
        ra, fah = r["arms"].get(name), f["arms"].get(name)
        if not ra or not fah:
            continue
        comp[name] = {
            "restricted_roth": ra["roth_net_ann"], "full_roth": fah["roth_net_ann"],
            "d_roth_pp": (fah["roth_net_ann"] - ra["roth_net_ann"]) * 100.0,
            "restricted_dd": ra["roth_max_drawdown"], "full_dd": fah["roth_max_drawdown"],
            "d_dd_pp": (fah["roth_max_drawdown"] - ra["roth_max_drawdown"]) * 100.0,
            "restricted_cost_bps": ra["realised_one_way_bps"],
            "full_cost_bps": fah["realised_one_way_bps"],
        }

    def spread(side):
        a = side["arms"]
        if "1_incumbent_10bn" not in a or "5_full" not in a:
            return None
        return (a["5_full"]["roth_net_ann"] - a["1_incumbent_10bn"]["roth_net_ann"]) * 100.0

    res = {
        "item": "UNIVERSE-BIAS", "part": "2b corrected-universe ladder", "trials": 0,
        "class": "RE-MEASUREMENT of already-registered arms on a corrected universe "
                 "(S25 / X7RECON / PANEL-EXT-RECHECK class). The incumbent is INDEX-BEST's, the "
                 "rungs and the decision rule are PREREG_pool_size.md's, and the rule was fixed "
                 "before any number. No hypothesis, no bar, no new degree of freedom.",
        "published_reference": {"incumbent_roth": PUBLISHED_INCUMBENT_ROTH,
                                "vintage": PUBLISHED_VINTAGE,
                                "note": "a DIFFERENT vintage from either panel here, so the "
                                        "restricted side is its near-neighbour and not its "
                                        "reproduction; the gap is reported, not assumed zero"},
        "restricted": r, "full": f, "per_arm": comp,
        "wider_pool_advantage_pp": {"restricted": spread(r), "full": spread(f)},
        "no_alpha_claim": "inherited from INDEX-CHOICE via PREREG_pool_size.md; an intercept or "
                          "a margin here is a decomposition, never alpha",
    }
    json.dump(res, io.open(os.path.join(fa, "UNIVERSE_BIAS_ARMS.json"), "w", encoding="utf-8"),
              indent=2, default=str)

    print("\n=== SIDE BY SIDE (net Roth, 2009-2026, one vintage) ===")
    print("%-18s %12s %12s %10s   %10s %10s %9s"
          % ("arm", "restricted", "full", "d pp", "rest dd", "full dd", "d dd pp"))
    for name, _kw in ARMS:
        c = comp.get(name)
        if not c:
            continue
        print("%-18s %11.2f%% %11.2f%% %+9.2f   %9.2f%% %9.2f%% %+8.2f"
              % (name, c["restricted_roth"] * 100, c["full_roth"] * 100, c["d_roth_pp"],
                 c["restricted_dd"] * 100, c["full_dd"] * 100, c["d_dd_pp"]))
    print("\nwider-pool advantage (full rung minus incumbent): restricted %+.2fpp | full %+.2fpp"
          % (spread(r) or float("nan"), spread(f) or float("nan")))
    for label in ("restricted", "full"):
        d = sides[label].get("decision")
        if d:
            print("  %-10s rule -> literal %s | cumulative %s | agree %s"
                  % (label, d["recommended_LITERAL_primary"],
                     d["recommended_CUMULATIVE_sensitivity"], d["readings_agree"]))
    print("\nwrote %s" % os.path.join(fa, "UNIVERSE_BIAS_ARMS.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
