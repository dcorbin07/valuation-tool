#!/usr/bin/env python3
"""ml_combiner.py — execute PREREG_ml_combiner.md, blind.  [roadmap #16]

Does a shallow gradient-boosted tree over the seven deployed theme z-scores beat the flat 1/7
linear composite out-of-sample, by the calibrated bars?

THE REGISTER IS THE SPEC. This file implements `PREREG_ml_combiner.md` (committed blind at
`ec6c01d`) and `PREREG_session11_execution_protocol.md`, and adds nothing to either. Every
constant below is quoted from the register rather than chosen here.

THE LOAD-BEARING PROPERTY: selection never touches the set the verdict is read from. All eight
grid points are scored by CPCV *within a decide half*; the single winner is refit on that half and
measured EXACTLY ONCE on the held-out half. This is the direct answer to X7's finding that CPCV
adoption manufactures ~+1.4 of long-short t out of nothing -- firing on 27% of pure-noise draws --
when selection and measurement share a panel.

    python -m scripts.ml_combiner --panel <panel.pkl> --json <out.json>
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP

# ---- everything below is quoted from PREREG_ml_combiner.md, not chosen here ----
THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]                      # seven; low_risk and sentiment excluded on record
HORIZON = 63
N_Q = 10
N_GROUPS, K_TEST, EMBARGO = 6, 2, 1             # _cpcv_paths, reused unchanged
GRID = [{"max_depth": d, "learning_rate": lr, "max_iter": it}
        for d in (2, 3) for lr in (0.03, 0.10) for it in (100, 300)]     # 8 points, frozen
FIXED = {"min_samples_leaf": 200, "l2_regularization": 1.0, "max_bins": 64,
         "early_stopping": False, "random_state": 0}
# calibrated bars (session 10 item 1 / X7), HAC-consistent
LS_HAC_FLOOR = 2.2837
MIN_ALPHA_MARGIN = 0.0195                        # 1.95pp, X7 calibrated
MIN_T_MARGIN = 0.25                              # standing MIN_HOLDOUT t-margin


def build_features(panel):
    """z_<theme> per rebalance date, built identically to cpcv_validate's own construction, plus
    the cross-sectional rank of fwd_ret in [0,1] as the target. No imputation -- NaN is passed to
    the learner, which handles it natively; imputing would give the tree information the linear
    composite does not have."""
    from valuation.screener.cross_sectional import zscore
    df = panel.copy()
    for c in THEMES:
        df["z_" + c] = df.groupby("date")[c].transform(lambda s: zscore(s))
    df["_y"] = df.groupby("date")["fwd_ret"].transform(
        lambda s: s.rank(pct=True, na_option="keep"))
    return df


def fit_predict(train, test, params):
    from sklearn.ensemble import HistGradientBoostingRegressor
    cols = ["z_" + c for c in THEMES]
    tr = train[np.isfinite(train["_y"].values)]
    if len(tr) < 100:
        return None
    m = HistGradientBoostingRegressor(**params, **FIXED)
    m.fit(tr[cols].values, tr["_y"].values)
    return m.predict(test[cols].values)


def rank_ic(pred, fwd):
    ok = np.isfinite(pred) & np.isfinite(fwd)
    if ok.sum() < 10:
        return np.nan
    return FP._spearman(pred[ok], fwd[ok])


def score_grid_on_decide(df, decide_dates, params):
    """Mean OOS rank IC across the decide half's CPCV paths -- ic_score's own convention:
    per-test-date Spearman, averaged over the path's test dates, then over paths."""
    paths = FP._cpcv_paths(decide_dates, N_GROUPS, K_TEST, embargo=EMBARGO)
    per_path = []
    for tr_dates, te_dates in paths:
        train = df[df["date"].isin(tr_dates)]
        test = df[df["date"].isin(te_dates)]
        pred = fit_predict(train, test, params)
        if pred is None:
            continue
        test = test.assign(_p=pred)
        ics = [rank_ic(g["_p"].values, g["fwd_ret"].values) for _, g in test.groupby("date")]
        ics = [x for x in ics if x == x]
        if ics:
            per_path.append(float(np.mean(ics)))
    return (float(np.mean(per_path)) if per_path else np.nan), len(paths), len(per_path)


def measure(df, decide_dates, verdict_dates, params):
    """THE ONE MEASUREMENT. Refit the winner on the whole decide half, score the verdict half
    once, and run both arms through the identical quantile_backtest construction."""
    train = df[df["date"].isin(decide_dates)]
    test = df[df["date"].isin(verdict_dates)].copy()
    pred = fit_predict(train, test, params)
    test["ml_score"] = pred
    # one col at weight 1.0 -> composite_from_frame returns zscore(ml_score), a monotone
    # transform, so the deciles are the model's own ranking under the SAME construction the
    # linear arm gets.
    tree = FP.quantile_backtest(test, ["ml_score"], {"ml_score": 1.0}, n_q=N_Q, horizon=HORIZON)
    lin = FP.quantile_backtest(test, THEMES, {c: 1.0 / len(THEMES) for c in THEMES},
                               n_q=N_Q, horizon=HORIZON)
    return tree, lin


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--json", default="data/free_analysis/ML_COMBINER.json")
    ap.add_argument("--decide-only", action="store_true",
                    help="dry run: exercise the pipeline on decide-half dates ONLY and touch no "
                         "verdict row (execution-protocol step 1)")
    args = ap.parse_args(argv)

    panel = pd.read_pickle(args.panel)
    missing = [c for c in THEMES if c not in panel.columns]
    if missing:
        print(f"FATAL: panel is missing {missing}")
        return 2
    df = build_features(panel)
    dates = sorted(df["date"].unique())
    n = len(dates)
    cut = n // 2
    early, boundary, late = dates[:cut], dates[cut], dates[cut + 1:]
    print(f"panel {len(df):,} rows, {n} dates -> early {len(early)}, "
          f"DROPPED boundary {pd.Timestamp(boundary).date()}, late {len(late)}")
    print(f"features: {['z_' + c for c in THEMES]}")
    print(f"grid: {len(GRID)} points\n")

    out = {"item": "MLCOMB", "prereg": "PREREG_ml_combiner.md",
           "protocol": "PREREG_session11_execution_protocol.md",
           "panel": args.panel, "themes": THEMES, "horizon": HORIZON,
           "grid": GRID, "fixed": FIXED, "n_dates": n,
           "boundary_date_dropped": str(pd.Timestamp(boundary).date()),
           "bars": {"ls_hac_floor": LS_HAC_FLOOR, "min_alpha_margin": MIN_ALPHA_MARGIN,
                    "min_t_margin": MIN_T_MARGIN},
           "directions": {}}

    for name, dec, ver in (("decide_early_measure_late", early, late),
                           ("decide_late_measure_early", late, early)):
        print(f"=== {name}: decide {len(dec)} dates, verdict {len(ver)} dates ===")
        scores = []
        for gp in GRID:
            ic, n_paths, n_ok = score_grid_on_decide(df, dec, gp)
            scores.append({"params": gp, "decide_mean_oos_rank_ic": ic,
                           "paths": n_paths, "paths_scored": n_ok})
            print(f"  d{gp['max_depth']} lr{gp['learning_rate']:.2f} it{gp['max_iter']:<4d}"
                  f"  mean OOS rank IC {ic:+.5f}  ({n_ok}/{n_paths} paths)")
        valid = [s for s in scores if s["decide_mean_oos_rank_ic"] == s["decide_mean_oos_rank_ic"]]
        if not valid:
            print("  FATAL: no grid point produced a score")
            return 3
        # ties -> first in registered enumeration order (the lowest-capacity model)
        best = max(valid, key=lambda s: s["decide_mean_oos_rank_ic"])
        best = next(s for s in valid
                    if s["decide_mean_oos_rank_ic"] == best["decide_mean_oos_rank_ic"])
        print(f"  SELECTED {best['params']}  (decide IC {best['decide_mean_oos_rank_ic']:+.5f})")

        rec = {"decide_dates": len(dec), "verdict_dates": len(ver),
               "grid_scores": scores, "selected": best["params"],
               "selected_decide_ic": best["decide_mean_oos_rank_ic"]}

        if args.decide_only:
            print("  [--decide-only] verdict half NOT touched\n")
            out["directions"][name] = rec
            continue

        tree, lin = measure(df, dec, ver, best["params"])
        d_alpha = tree["top_decile_alpha"] - lin["top_decile_alpha"]
        d_t = tree["long_short_tstat_nw"] - lin["long_short_tstat_nw"]
        rec.update({
            "tree": {k: tree.get(k) for k in ("top_decile_alpha", "long_short_tstat",
                                              "long_short_tstat_nw", "monotonicity",
                                              "n_periods", "equal_weight_ann")},
            "linear": {k: lin.get(k) for k in ("top_decile_alpha", "long_short_tstat",
                                               "long_short_tstat_nw", "monotonicity",
                                               "n_periods", "equal_weight_ann")},
            "d_top_decile_alpha": d_alpha, "d_long_short_tstat_nw": d_t,
            "c1_alpha_margin": bool(d_alpha >= MIN_ALPHA_MARGIN),
            "c2_t_margin": bool(d_t >= MIN_T_MARGIN),
            "c3_tree_clears_floor": bool((tree.get("long_short_tstat_nw") or -9) >= LS_HAC_FLOOR),
            "worse_on_alpha": bool(d_alpha < 0),
        })
        print(f"  tree   alpha {tree['top_decile_alpha']:+.4f}  LS HAC t "
              f"{tree['long_short_tstat_nw']:+.4f}  mono {tree['monotonicity']:+.3f}")
        print(f"  linear alpha {lin['top_decile_alpha']:+.4f}  LS HAC t "
              f"{lin['long_short_tstat_nw']:+.4f}  mono {lin['monotonicity']:+.3f}")
        print(f"  delta  alpha {d_alpha:+.4f} (need >= {MIN_ALPHA_MARGIN:+.4f})   "
              f"LS HAC t {d_t:+.4f} (need >= {MIN_T_MARGIN:+.2f})")
        print(f"  C1 {rec['c1_alpha_margin']}  C2 {rec['c2_t_margin']}  "
              f"C3 {rec['c3_tree_clears_floor']}\n")
        out["directions"][name] = rec

    if not args.decide_only:
        ds = list(out["directions"].values())
        adopted = all(d["c1_alpha_margin"] and d["c2_t_margin"] and d["c3_tree_clears_floor"]
                      for d in ds)
        rejected = all(d["worse_on_alpha"] for d in ds)
        out["verdict"] = "ADOPTED" if adopted else ("REJECTED" if rejected else "NULL")
        sel = [tuple(sorted(d["selected"].items())) for d in ds]
        out["same_grid_point_selected"] = bool(sel[0] == sel[1])
        print(f"VERDICT: {out['verdict']}")
        print(f"both directions selected the same grid point: {out['same_grid_point_selected']}")

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
