#!/usr/bin/env python3
"""X5 — bootstrap the pipeline.

Executes the X5 section of `PREREG_x5_m4_b23_s10acct.md` unmodified.

B = 200 resamples of the universe WITH REPLACEMENT at full size, each scored by the shipped
`quantile_backtest`. Reports the distribution of top-decile alpha, long-short HAC t and
monotonicity, and the audit's own verdict: is the 5th percentile of alpha positive?

SCOPE, from register 0c: the panel is NOT rebuilt per draw (200 x ~20 min is ~66 hours).
The resample re-does the layer-3 standardisation and the whole decile sort, because
`quantile_backtest` calls `composite_from_frame`, which re-standardises within the slice it
is given; layers 1-2 were computed once across the full universe. So the interval is a LOWER
BOUND on total name-selection uncertainty. PBO is NOT computed - declared, not dropped.

Run:  python -m scripts.x5_bootstrap_pipeline
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP            # noqa: E402
from valuation.edge import statistics as ST                   # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
B_DRAWS = 200
SEED = 20260814
STATS = ("top_decile_alpha", "long_short_tstat_nw", "monotonicity")

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


def bootstrap_frame(panel, by_ticker, uni, rng):
    """One bootstrap resample: draw len(uni) names WITH REPLACEMENT and REPEAT their rows.

    Duplicates are KEPT as duplicates - that is what a bootstrap is. A name drawn twice
    contributes two rows to its date's cross-section and is twice as likely to enter a
    decile. De-duplicating would make this a SUBSAMPLE and would understate the variance.
    """
    drawn = rng.choice(len(uni), size=len(uni), replace=True)
    counts = np.bincount(drawn, minlength=len(uni))
    parts = []
    for k in range(1, int(counts.max()) + 1):
        idx = np.flatnonzero(counts == k)
        if idx.size == 0:
            continue
        block = pd.concat([by_ticker[uni[i]] for i in idx], axis=0)
        parts.extend([block] * k)
    return pd.concat(parts, axis=0), int((counts > 0).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_r5r6.pkl")
    ap.add_argument("--json", default="data/free_analysis/X5_BOOTSTRAP.json")
    ap.add_argument("--draws", type=int, default=B_DRAWS)
    ap.add_argument("--controls-only", action="store_true")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel_cache, "rb"))
    n_d, n_t = panel["date"].nunique(), panel["ticker"].nunique()
    _log(f"[x5] panel {panel.shape}, {n_d} dates, {n_t} names")
    out = {"item": "X5", "register": "PREREG_x5_m4_b23_s10acct.md",
           "b_draws": args.draws, "seed": SEED, "statistics": list(STATS),
           "scope_limit": (
               "the panel is NOT rebuilt per draw (~66 hours); the resample re-does the "
               "layer-3 standardisation and the decile sort, not layers 1-2. The interval "
               "is a LOWER BOUND on total name-selection uncertainty."),
           "pbo_declared_absent": (
               "PBO comes from cpcv_validate, itself a multi-fit procedure; 200 of them is "
               "the same infeasibility. No PBO figure from X5 may be quoted."),
           "controls": {}, "draws": {}, "arms": {}}

    # ---- C1 (GATING), own pass ----
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(got.get(k) == v for k, v in REC.items())
    out["controls"]["C1_full_universe_headline"] = {"ok": bool(ok1), "measured": got}
    _log(f"[C1] full-universe headline reproduces: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 FAILED - every draw is VOID per register 6.6"
        _w(args.json, out)
        return 2
    if args.controls_only:
        _w(args.json, out)
        _log("[x5] controls-only pass complete; nothing resampled")
        return 0

    uni = np.array(sorted(panel["ticker"].unique()))
    by_ticker = {t: g for t, g in panel.groupby("ticker", sort=False)}
    rng = np.random.default_rng(SEED)

    vals = {k: [] for k in STATS}
    distinct = []
    for b in range(args.draws):
        frame, n_distinct = bootstrap_frame(panel, by_ticker, uni, rng)
        distinct.append(n_distinct)
        r = FP.quantile_backtest(frame, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
        if not isinstance(r, dict) or r.get("top_decile_alpha") is None:
            continue
        for k in STATS:
            v = r.get(k)
            if v is not None and np.isfinite(v):
                vals[k].append(float(v))
        if (b + 1) % 20 == 0:
            _log(f"    draw {b+1}/{args.draws}  alpha so far: "
                 f"p05 {np.percentile(vals['top_decile_alpha'], 5):+.5f}")

    # ---- C2 (GATING): these are genuine bootstraps ----
    frac = float(np.mean(distinct)) / len(uni)
    c2 = {"universe": int(len(uni)),
          "mean_distinct_names": float(np.mean(distinct)),
          "mean_distinct_fraction": frac,
          "theoretical_1_minus_1_over_e": float(1 - np.exp(-1)),
          "ok": bool(abs(frac - (1 - np.exp(-1))) < 0.02),
          "why": ("a bootstrap of size n from n names contains 1-1/e ~ 63.2% distinct names "
                  "in expectation; sampling WITHOUT replacement would read 100% and would be "
                  "a different experiment")}
    out["controls"]["C2_genuine_bootstrap"] = c2
    _log(f"[C2] mean distinct {c2['mean_distinct_fraction']:.4f} "
         f"vs 1-1/e {c2['theoretical_1_minus_1_over_e']:.4f} -> {c2['ok']}")
    if not c2["ok"]:
        out["ABORTED"] = "C2 FAILED - the resamples are not bootstraps"
        _w(args.json, out)
        return 2

    for k in STATS:
        v = vals[k]
        d = ST.distribution(v) if v else {}
        out["draws"][k] = [round(x, 8) for x in v]
        out["arms"][k] = {
            "n_draws": len(v), "full_universe": REC.get(k),
            "distribution": d,
            "p05": (float(np.percentile(v, 5)) if v else None),
            "p95": (float(np.percentile(v, 95)) if v else None),
            "median": (float(np.median(v)) if v else None),
            "frac_positive": (float(np.mean([x > 0 for x in v])) if v else None),
        }

    a_alpha, a_ls = out["arms"]["top_decile_alpha"], out["arms"]["long_short_tstat_nw"]
    out["arms"]["top_decile_alpha"]["verdict"] = (
        "STRONG - the 5th percentile is POSITIVE" if (a_alpha["p05"] or 0) > 0
        else "STRADDLES ZERO - the point estimate has been carrying more weight than it can bear")
    out["arms"]["long_short_tstat_nw"]["verdict"] = (
        "STRONG - the 5th percentile is above zero" if (a_ls["p05"] or 0) > 0
        else "STRADDLES ZERO")
    out["arms"]["monotonicity"]["verdict"] = "DESCRIPTIVE - no verdict registered"

    for k in STATS:
        a = out["arms"][k]
        _log(f"[{k}] p05 {a['p05']:+.5f}  median {a['median']:+.5f}  p95 {a['p95']:+.5f}  "
             f"full {a['full_universe']:+.5f}  {a.get('verdict','')}")

    _w(args.json, out)
    _log(f"[x5] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
