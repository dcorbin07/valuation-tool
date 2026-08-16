#!/usr/bin/env python3
"""x3_ablation_rerun.py — X3 re-run on the corrected panel, against X7's calibrated bars.

`scripts/ablation.py` ran X3 on 2026-08-03 and the ledger records it DONE ("EARNS ITS
COMPLEXITY"). That run is void twice over — it used the pre-B6 110-date panel whose first 41
dates carried an inverted universe, and it scored against a 1.0pp three-theme bar that X7 later
measured to be BELOW the noise floor (placebo p95 = 1.95pp). This is the re-run. The old script
is left exactly as it is: it is another lane's file and its own pre-registration is a matter of
record, so it is superseded rather than edited.

Eight arms, fixed before the run (session-6 pre-commitment, `HANDOFF_edge_audit.md`):
arm 1 is `z_gp_on_capital` alone; arms 2-8 are the cumulative theme curve in descending theme-IC
order over the seven deployed themes, ending at the deployed composite itself.

    python -m scripts.x3_ablation_rerun --panel <panel.pkl> --json X3_RERUN_RESULTS.json
"""
from __future__ import annotations

import argparse
import json
import os


def _fmt(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="X3 re-run — ablation against X7's bars.")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--json", default="X3_RERUN_RESULTS.json")
    ap.add_argument("--single", default="gp_on_capital")
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--leave-one-out", action="store_true",
                    help="EXPLORATORY ONLY. Drop each theme from the full composite in turn. "
                         "Not in the session-6 pre-registration, generated after seeing the "
                         "prefix curve, and therefore CARRIES NO VERDICT and earns no "
                         "RESEARCH_LOG row -- the log's own schema: exploratory looks get no "
                         "claim. It exists to let session 7 pre-register the right test.")
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.edge import ablation as A
    from valuation.edge.fundamental_panel import _base_weights, theme_ic
    from valuation.screener import settings as S

    panel = pd.read_pickle(args.panel)
    print(f"[X3] panel {len(panel):,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names", flush=True)

    deployed = [c for c in S.BUCKET_FACTORS["established"]
                if c in panel.columns and panel[c].notna().any()
                and S.WEIGHTS_ESTABLISHED.get(c, 0.0) > 0]
    out = {"item": "X3", "status": "re-run on the corrected panel",
           "supersedes": {"file": "data/free_analysis/ABLATION_RESULTS.json",
                          "date": "2026-08-03",
                          "why": ["pre-B6 panel: 110 dates, 136,478 rows, alpha +11.88%",
                                  "scored against retired 2.0pp/1.0pp bars; X7's calibrated "
                                  "top-decile alpha margin is 1.95pp, so the 1.0pp "
                                  "three-theme bar sat below the noise floor"]},
           "panel": {"rows": int(len(panel)), "dates": int(panel["date"].nunique()),
                     "names": int(panel["ticker"].nunique())},
           "calibrated_bars": {"top_decile_alpha_margin": A.X7_ALPHA_MARGIN,
                               "long_short_t_naive": A.X7_LS_T_NAIVE,
                               "theme_ic_t": A.X7_THEME_IC_T,
                               "pbo_max": A.X7_PBO_MAX,
                               "deflated_sharpe": A.X7_DEFLATED_SHARPE,
                               "source": A.X7_SOURCE},
           "deployed_themes": deployed, "arms": []}

    # ---- theme order on THIS panel, measured not quoted -------------------------------------
    tic = theme_ic(panel)
    ranked = sorted([(k, v.get("ic_tstat")) for k, v in tic.items()
                     if v.get("ic_tstat") is not None and k in deployed],
                    key=lambda kv: -kv[1])
    out["theme_ic_ranking"] = [{"theme": k, "ic_tstat": t,
                                "clears_x7_theme_ic_bar": bool(t > A.X7_THEME_IC_T)}
                               for k, t in ranked]
    print("[X3] theme order (X7 bar t>2.71): "
          + ", ".join(f"{k}({t:+.2f}{'*' if t > A.X7_THEME_IC_T else ''})" for k, t in ranked),
          flush=True)

    def add(label, cols, weights):
        r = A.arm_result(panel, label, cols, weights)
        out["arms"].append(r)
        print(f"  {label:38s} alpha={_fmt(r['top_decile_alpha']):>8s} "
              f"LSt={_fmt(r['long_short_tstat'], '.3f'):>7s} "
              f"NWt={_fmt(r['long_short_tstat_nw'], '.3f'):>7s} "
              f"mono={_fmt(r['monotonicity'], '+.3f'):>7s} "
              f"[alpha>1.95pp={r['clears_x7_alpha_margin']}]", flush=True)
        return r

    zc = "z_" + args.single
    single_col = zc if zc in panel.columns else args.single
    arm1 = add(f"1. {args.single} alone", [single_col], {single_col: 1.0})

    for k in range(1, len(ranked) + 1):
        cols = [t for t, _ in ranked[:k]]
        add(f"{k + 1}. themes 1-{k}: {'+'.join(c[:4] for c in cols)}",
            cols, {c: 1.0 / k for c in cols})

    full = out["arms"][-1]
    # The last cumulative arm IS the deployed composite (all seven themes, flat) — asserted
    # rather than assumed, because a silent mismatch would make the whole curve compare
    # against something the product does not run.
    dep_w = _base_weights(deployed, "established")
    out["last_arm_is_deployed_composite"] = bool(
        sorted(full["cols"]) == sorted(deployed)
        and all(abs(full["weights"][c] - dep_w[c]) < 1e-9 for c in deployed))

    # ---- paired nested differences: does the FULL composite beat each shorter arm? -----------
    out["paired_vs_full"] = []
    for arm in out["arms"][:-1]:
        d = A.paired_diff(full["_series"]["alpha"], arm["_series"]["alpha"],
                          draws=args.draws,
                          dates_a=full["_series"]["dates"],
                          dates_b=arm["_series"]["dates"])
        d["arm"] = arm["label"]
        out["paired_vs_full"].append(d)
        if d.get("ok"):
            print(f"  full - [{arm['label'][:30]:30s}] = {_fmt(d['mean_diff_ann']):>8s}/yr "
                  f"CI95 [{_fmt(d['ci95_ann'][0])}, {_fmt(d['ci95_ann'][1])}] "
                  f"excl0={d['excludes_zero']}", flush=True)

    # ---- the flattening point, by the pre-registered rule -------------------------------------
    flat_from = None
    for i, d in enumerate(out["paired_vs_full"]):
        if d.get("ok") and not d.get("positive_at_significance"):
            flat_from = out["arms"][i]["label"]
            break
    out["first_arm_the_full_composite_does_not_beat"] = flat_from

    # ---- EXPLORATORY, no verdict: what does each theme contribute AT THE MARGIN? ------------
    # The prefix curve orders themes by IC, and IC turned out not to predict marginal
    # contribution at all. This answers the question the prefix curve raised. It was written
    # after seeing that result, so it is a look and not a test, and it is labelled as one
    # everywhere it appears.
    if args.leave_one_out:
        print("\n[X3] EXPLORATORY leave-one-out (NO VERDICT, no RESEARCH_LOG row):", flush=True)
        out["exploratory_leave_one_out"] = {
            "status": "EXPLORATORY — not pre-registered, generated after seeing the prefix "
                      "curve, carries no verdict and earns no trial row",
            "arms": []}
        for drop in deployed:
            rest = [c for c in deployed if c != drop]
            r = A.arm_result(panel, f"full minus {drop}", rest,
                             {c: 1.0 / len(rest) for c in rest})
            d = A.paired_diff(full["_series"]["alpha"], r["_series"]["alpha"],
                              draws=args.draws,
                              dates_a=full["_series"]["dates"],
                              dates_b=r["_series"]["dates"])
            r.pop("_series", None)
            out["exploratory_leave_one_out"]["arms"].append(
                {"dropped": drop, "arm": r, "paired_vs_full": d})
            print(f"   drop {drop:20s} alpha={_fmt(r['top_decile_alpha']):>8s} "
                  f"LSt={_fmt(r['long_short_tstat'], '.3f'):>7s}  "
                  f"full-arm={_fmt(d.get('mean_diff_ann')):>8s}/yr excl0={d.get('excludes_zero')}",
                  flush=True)

    for arm in out["arms"]:
        arm.pop("_series", None)

    os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\n[X3] first arm the full composite does NOT beat: {flat_from}")
    print(f"[X3] -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
