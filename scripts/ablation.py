#!/usr/bin/env python3
"""ablation.py — does the seven-theme composite beat its own best single signal?  [X3]

The most uncomfortable test in the catalogue. If one signal delivers most of the composite's
alpha, the multi-theme architecture is decoration — expensive decoration, since it carries
`insider` at t ~ -0.34 and `book_to_price` at ~ +0.15.

Runs, all on the SAME panel, horizon and universe, varying only what is scored:

  (a) `gp_on_capital` alone      — the strongest single number in the model
  (b) the `quality` theme alone  — the strongest theme
  (c) an ablation curve          — themes added one at a time in descending theme-IC t order
  (d) the full deployed composite (WEIGHTS_ESTABLISHED)

Thresholds are pre-registered in PREREG_free_analysis.md and are NOT restated from results:

  EARNS ITS COMPLEXITY  full - best_single >= 2.0pp  AND  full - best_3_prefix >= 1.0pp
  FLAT AFTER THREE      full - best_3_prefix < 1.0pp        -> simplify
  DECORATION            full - best_single   < 2.0pp

Anything between those bars is a NULL: "complexity not demonstrated".

Modifies no existing file. Reads a panel pickle from scripts/dump_panel.py.

    python -m scripts.ablation --panel data/free_analysis/panel.pkl \
        --json data/free_analysis/ABLATION_RESULTS.json
"""
from __future__ import annotations

import argparse
import json
import os

MIN_GAIN_VS_SINGLE = 0.020      # 2.0pp — structural claim, twice the project's own margin
MIN_GAIN_VS_THREE = 0.010       # 1.0pp — the project's own holdout min_alpha_gain


def _fmt(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ablate the composite to its best single signal (X3).")
    ap.add_argument("--panel", default="data/free_analysis/panel.pkl")
    ap.add_argument("--json", default="data/free_analysis/ABLATION_RESULTS.json")
    ap.add_argument("--single", default="gp_on_capital")
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.edge.fundamental_panel import quantile_backtest, theme_ic
    from valuation.screener import settings as S

    panel = pd.read_pickle(args.panel)
    print(f"[X3] panel {len(panel):,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names", flush=True)

    out = {"item": "X3", "panel": {"rows": int(len(panel)),
                                   "dates": int(panel["date"].nunique()),
                                   "names": int(panel["ticker"].nunique())},
           "thresholds": {"min_gain_vs_best_single": MIN_GAIN_VS_SINGLE,
                          "min_gain_vs_best_3_prefix": MIN_GAIN_VS_THREE,
                          "prereg": "PREREG_free_analysis.md"},
           "runs": {}}

    def run(label, cols, weights):
        r = quantile_backtest(panel, cols, weights, n_q=10, horizon=63)
        out["runs"][label] = {"cols": list(cols), "weights": weights,
                              "top_decile_alpha": r.get("top_decile_alpha"),
                              "long_short_tstat": r.get("long_short_tstat"),
                              "long_short_ann": r.get("long_short_ann"),
                              "monotonicity": r.get("monotonicity"),
                              "n_periods": r.get("n_periods"),
                              "equal_weight_ann": r.get("equal_weight_ann"),
                              "decile_ann_return": r.get("decile_ann_return")}
        print(f"  {label:34s} alpha={_fmt(r.get('top_decile_alpha')):>8s}  "
              f"LS t={_fmt(r.get('long_short_tstat'), '.3f'):>7s}  "
              f"mono={_fmt(r.get('monotonicity'), '+.3f'):>7s}", flush=True)
        return r.get("top_decile_alpha")

    # ---- (a) the single strongest NUMBER -------------------------------------------------
    zcol = "z_" + args.single
    single_col = zcol if zcol in panel.columns else args.single
    if single_col not in panel.columns:
        print(f"[X3] {args.single} not in panel — cannot run the single-signal arm", flush=True)
        a_single = None
    else:
        a_single = run(f"(a) {args.single} alone", [single_col], {single_col: 1.0})

    # ---- (b) the single strongest THEME --------------------------------------------------
    a_quality = run("(b) quality theme alone", ["quality"], {"quality": 1.0})

    # ---- theme ordering, by theme-IC t on THIS panel --------------------------------------
    tic = theme_ic(panel)
    ranked = sorted(
        [(k, v.get("ic_tstat")) for k, v in tic.items()
         if v.get("ic_tstat") is not None and k in panel.columns],
        key=lambda kv: -kv[1])
    out["theme_ic_ranking"] = [{"theme": k, "ic_tstat": t} for k, t in ranked]
    print(f"[X3] theme order: {', '.join(f'{k}({t:+.2f})' for k, t in ranked)}", flush=True)

    # ---- (c) the ablation curve, equal-weighted within each prefix ------------------------
    curve = []
    for k in range(1, len(ranked) + 1):
        cols = [t for t, _ in ranked[:k]]
        w = {c: 1.0 / k for c in cols}
        a = run(f"(c) top-{k} themes", cols, w)
        curve.append({"k": k, "themes": cols, "top_decile_alpha": a})
    out["ablation_curve"] = curve

    # ---- (d) the deployed composite ------------------------------------------------------
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}
    a_full = run("(d) full deployed composite", list(dep), dep)

    # ---- verdict, against the pre-registered bars ONLY ------------------------------------
    best3 = max([c["top_decile_alpha"] for c in curve[:3]
                 if c["top_decile_alpha"] is not None], default=None)
    best_single = max([x for x in (a_single, a_quality) if x is not None], default=None)

    v = {"full_composite_alpha": a_full, "best_single_signal_alpha": a_single,
         "quality_theme_alpha": a_quality, "best_of_first_three_prefixes": best3,
         "gain_vs_best_single": (None if a_full is None or best_single is None
                                 else a_full - best_single),
         "gain_vs_best_3_prefix": (None if a_full is None or best3 is None else a_full - best3)}

    g1, g3 = v["gain_vs_best_single"], v["gain_vs_best_3_prefix"]
    if g1 is None or g3 is None:
        v["verdict"] = "INCONCLUSIVE — a required arm did not compute"
    elif g1 >= MIN_GAIN_VS_SINGLE and g3 >= MIN_GAIN_VS_THREE:
        v["verdict"] = "EARNS ITS COMPLEXITY"
    elif g1 < MIN_GAIN_VS_SINGLE:
        v["verdict"] = "DECORATION — the composite does not beat its best single signal"
    elif g3 < MIN_GAIN_VS_THREE:
        v["verdict"] = "FLAT AFTER THREE THEMES — simplify"
    else:
        v["verdict"] = "NULL — complexity not demonstrated"
    out["verdict"] = v

    print(f"\n[X3] full={_fmt(a_full)}  best_single={_fmt(best_single)}  best3={_fmt(best3)}")
    print(f"[X3] gain vs single={_fmt(g1)} (bar +2.00%)  gain vs 3-prefix={_fmt(g3)} (bar +1.00%)")
    print(f"[X3] VERDICT: {v['verdict']}")

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"[X3] -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
