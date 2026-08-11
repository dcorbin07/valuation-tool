#!/usr/bin/env python3
"""sector_neutral_rerun.py — sector-neutral ranking, re-run on the corrected panel.  [B6]

Sector-neutral ranking was rejected twice (P10 2026-07-31; 2026-08-02), in both held-out
directions, under both weightings. BOTH rejections ran on the pre-B6 110-date / 2,710-name panel
the project has since declared void: the decision turned on a -1.58pp top-decile alpha difference,
measured inside a panel whose alpha LEVEL moved -4.18pp when the defect was removed.

This re-runs THE SAME pre-committed gate on the corrected 69-date panel and closes the item
either way. Everything about the design - the gate, its two weightings, the verdict rule, the
calibrated bars, the controls, the trial cost and the expectations - is fixed in
PREREG_sector_neutral_b6.md, committed ALONE at 1bdb7e0 BEFORE this file existed. Nothing here
restates a threshold from a result.

Adopts nothing. Adoption is a VINTAGE EVENT and Don's call.

    python -m scripts.sector_neutral_rerun \
        --data-dir C:/Users/donni/Downloads/valuation-tool/data/backtest \
        --panel    C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_sn_b6.pkl \
        --json     C:/Users/donni/Downloads/valuation-tool/data/free_analysis/SECTOR_NEUTRAL_B6.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

# ---- everything below is PRE-REGISTERED; see PREREG_sector_neutral_b6.md --------------------

# prereg 3 - the two weightings, both fixed in advance. DEPLOYED carries the verdict.
DEPLOYED = ["value", "quality", "momentum", "insider",
            "capital_discipline", "size", "institutional"]
# `sentiment` is excluded because it is empty (control C7); `growth` and `low_risk` are the two
# themes the deployed vector zeroes, and the FLAT arm is what tests whether the answer depends on
# the weighting at all.
FLAT = DEPLOYED + ["growth", "low_risk"]
BASE_WEIGHT = 0.125

# prereg 4 - valid at THIS configuration: the full-universe decile book, 69 dates, H=63, lag 1.
# Quoted without caveat for the flat arm; an EXTRAPOLATION for the sector-neutral arm, and
# labelled one everywhere it appears.
LS_HAC_FLOOR = 2.2837
ALPHA_HAC_FLOOR = 2.2913
LS_NAIVE_FLOOR = 2.1437
HAC_LAG = 1

# prereg 4a - UNCALIBRATED, and labelled so everywhere. It cannot overturn the primary gate.
PAIRED_T_UNCALIBRATED = 2.0

# prereg 7 - C3, the published record the flat arm must reproduce to the digit.
C3_RECORD = {"top_decile_alpha": 0.071741423321,
             "long_short_tstat": 2.8360640685320595,
             "long_short_tstat_nw": 2.6199,
             "top_decile_alpha_tstat_nw": 4.3762,
             "monotonicity": -0.8909090909090909,
             "equal_weight_ann": 0.18137118752419476}

# prereg 7 - C4. Coverage below this is a FINDING and the verdict is withheld.
MIN_SECTOR_COVERAGE = 0.95

# The void panel's numbers, quoted from HANDOFF_sector_neutral.md so the comparison is explicit.
# Reference only - nothing is scored against them.
VOID_PANEL = {"n_dates": 110, "n_names": 2710,
              "deployed": {"ls_t_off": 3.396, "ls_t_on": 3.896,
                           "alpha_off": 0.1182, "alpha_on": 0.1024,
                           "early_d_ls_t": 0.948, "early_d_alpha": -0.0197,
                           "late_d_ls_t": -0.505, "late_d_alpha": -0.0126}}


def _f(x, p="+.4f"):
    return "n/a" if x is None else format(x, p)


# --------------------------------------------------------------------------- panel


def load_panel(path, data_dir):
    """ONE build. Both arms are scored from the same `metrics` list in the same pass."""
    import pandas as pd
    if os.path.exists(path):
        print(f"[snb6] reading cached panel {path}", flush=True)
        return pd.read_pickle(path)

    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    class _C:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit(f"[snb6] provider not ready: {msg}")
    tickers = prov.universe(limit=CONFIG.backtest_universe_limit)
    print(f"[snb6] {len(tickers)} names; ONE build with sector_neutral_pair=True "
          f"(prereg 2 - both arms share the metrics list)", flush=True)
    t0 = time.time()
    panel = build_fundamental_panel(
        prov, tickers,
        rebalance_days=CONFIG.backtest_rebalance_days,
        lookback_years=CONFIG.backtest_lookback_years,
        horizon=63,
        sector_neutral_pair=True,
    )
    print(f"[snb6] built {len(panel):,} rows x {len(panel.columns)} cols in "
          f"{time.time()-t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    panel.to_pickle(path)
    return panel


def split_arms(panel):
    """The two arms as two frames over an IDENTICAL row set (prereg 2)."""
    from valuation.screener import settings as S
    flat = panel.copy()
    sn = panel.copy()
    for theme in S.FACTORS_ALL:
        src = "sn_" + theme
        if src in sn.columns:
            sn[theme] = sn[src]
    drop = [c for c in sn.columns if c.startswith("sn_")]
    return flat.drop(columns=drop, errors="ignore"), sn.drop(columns=drop, errors="ignore")


# --------------------------------------------------------------------------- arms


def arm(panel, cols, label):
    """Full-sample levels for one arm, scored by the SHIPPED quantile_backtest."""
    from valuation.edge.fundamental_panel import quantile_backtest, _nw_tstat, _tstat
    w = {c: BASE_WEIGHT for c in cols}
    r = quantile_backtest(panel, cols, w, n_q=10, horizon=63, return_series=True)
    if not r or "series" not in r:
        return {"label": label, "status": "no series"}
    a, ls = r["series"]["alpha"], r["series"]["long_short"]
    return {
        "label": label, "n_cols": len(cols), "cols": list(cols),
        "n_periods": r["n_periods"], "dates": r["series"]["dates"],
        "top_decile_alpha": r["top_decile_alpha"],
        "long_short_ann": r["long_short_ann"],
        "long_short_tstat": r["long_short_tstat"],
        "ls_t_hac": _nw_tstat(ls, lag=HAC_LAG),
        "alpha_t_naive": _tstat(a), "alpha_t_hac": _nw_tstat(a, lag=HAC_LAG),
        "monotonicity": r["monotonicity"],
        "equal_weight_ann": r["equal_weight_ann"],
        "decile_ann_return": r["decile_ann_return"],
        "alpha_hit": r["top_decile_alpha_hit"], "ls_hit": r["long_short_hit"],
        "clears_ls_hac_floor": (r["long_short_tstat"] is not None
                                and _nw_tstat(ls, lag=HAC_LAG) >= LS_HAC_FLOOR),
        "clears_alpha_hac_floor": _nw_tstat(a, lag=HAC_LAG) >= ALPHA_HAC_FLOOR,
        "clears_ls_naive_floor": r["long_short_tstat"] >= LS_NAIVE_FLOOR,
        "alpha_series": a, "ls_series": ls,
    }


def paired(a_flat, a_sn, dates=None, label="full"):
    """prereg 4a - the paired within-panel difference (the V2G construction).

    The two arms score the SAME dates, so differencing per date cancels the market move. Far
    better powered than differencing two half-sample level statistics. The 2.0 bar is
    UNCALIBRATED and cannot overturn the primary gate.
    """
    from valuation.edge.fundamental_panel import _nw_tstat, _tstat
    da = dict(zip(a_flat["dates"], a_flat["alpha_series"]))
    db = dict(zip(a_sn["dates"], a_sn["alpha_series"]))
    la = dict(zip(a_flat["dates"], a_flat["ls_series"]))
    lb = dict(zip(a_sn["dates"], a_sn["ls_series"]))
    keys = [d for d in a_flat["dates"] if d in db and (dates is None or d in set(dates))]
    d_alpha = [db[d] - da[d] for d in keys]
    d_ls = [lb[d] - la[d] for d in keys]
    if len(keys) < 4:
        return {"label": label, "n_paired_dates": len(keys), "status": "too few dates"}
    n = len(keys)

    def block(v):
        m = float(np.mean(v))
        se = float(np.std(v, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
        return {"mean_period": m, "ann": m * 4.0, "se_period": se, "se_ann": se * 4.0,
                "t_naive": _tstat(v), "t_hac": _nw_tstat(v, lag=HAC_LAG)}

    return {"label": label, "n_paired_dates": n, "bar_uncalibrated": PAIRED_T_UNCALIBRATED,
            "alpha": block(d_alpha), "long_short": block(d_ls),
            "d_alpha_series": d_alpha, "d_ls_series": d_ls, "dates": keys}


# --------------------------------------------------------------------------- controls


def controls(panel, flat, sn, a_flat_dep):
    """prereg 7 - each control is a named way for this study to fail."""
    import pandas as pd
    from valuation.screener import settings as S
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    out = {}

    # C1 - identical row sets.
    ka = set(zip(flat["date"].astype(str), flat["ticker"].astype(str)))
    kb = set(zip(sn["date"].astype(str), sn["ticker"].astype(str)))
    dates = sorted(panel["date"].astype(str).unique())
    out["C1_identical_rows"] = {
        "n_rows_flat": len(flat), "n_rows_sn": len(sn),
        "key_sets_identical": ka == kb, "n_only_flat": len(ka - kb), "n_only_sn": len(kb - ka),
        "n_dates": len(dates), "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "n_names": int(panel["ticker"].nunique()),
    }

    # C2 - the toggle is NOT inert. This feature was silently inert for years.
    moves = {}
    for theme in S.FACTORS_ALL:
        src = "sn_" + theme
        if src not in panel.columns:
            continue
        x = pd.to_numeric(panel[theme], errors="coerce")
        y = pd.to_numeric(panel[src], errors="coerce")
        ok = x.notna() & y.notna()
        moves[theme] = float((y[ok] - x[ok]).abs().mean()) if ok.any() else None
    comp_moves, comp_corr = [], []
    for d in dates[:8]:
        sub_a = flat[flat["date"].astype(str) == d]
        sub_b = sn[sn["date"].astype(str) == d]
        ca = composite_from_frame(sub_a, DEPLOYED, {c: BASE_WEIGHT for c in DEPLOYED}, zscore)
        cb = composite_from_frame(sub_b, DEPLOYED, {c: BASE_WEIGHT for c in DEPLOYED}, zscore)
        m = np.isfinite(ca) & np.isfinite(cb)
        if m.sum() > 30:
            comp_moves.append(float(np.mean(np.abs(cb[m] - ca[m]))))
            comp_corr.append(float(np.corrcoef(ca[m], cb[m])[0, 1]))
    out["C2_toggle_not_inert"] = {
        "mean_abs_theme_change": moves,
        "n_themes_that_move": sum(1 for v in moves.values() if v and v > 1e-9),
        "composite_mean_abs_change_first8dates": (float(np.mean(comp_moves))
                                                  if comp_moves else None),
        "composite_corr_first8dates": float(np.mean(comp_corr)) if comp_corr else None,
        "not_inert": bool(comp_moves and np.mean(comp_moves) > 1e-9),
    }

    # C3 - the flat arm reproduces the published record to the digit.
    got = {"top_decile_alpha": a_flat_dep.get("top_decile_alpha"),
           "long_short_tstat": a_flat_dep.get("long_short_tstat"),
           "long_short_tstat_nw": a_flat_dep.get("ls_t_hac"),
           "top_decile_alpha_tstat_nw": a_flat_dep.get("alpha_t_hac"),
           "monotonicity": a_flat_dep.get("monotonicity"),
           "equal_weight_ann": a_flat_dep.get("equal_weight_ann")}
    checks = {}
    for k, exp in C3_RECORD.items():
        v = got.get(k)
        tol = 5e-5 if k in ("long_short_tstat_nw", "top_decile_alpha_tstat_nw") else 1e-9
        checks[k] = {"expected": exp, "got": v,
                     "ok": v is not None and abs(v - exp) <= max(tol, abs(exp) * 1e-9)}
    out["C3_reproduces_record"] = {"checks": checks,
                                   "all_ok": all(c["ok"] for c in checks.values())}

    # C4 - COVERAGE RULE. 100% was measured on the VOID panel and may not be assumed.
    sec = panel["sector"].astype(str).fillna("")
    nonblank = sec.str.strip() != ""
    per_date = []
    for d in dates:
        s = panel.loc[panel["date"].astype(str) == d, "sector"].astype(str)
        vc = s[s.str.strip() != ""].value_counts()
        if len(vc):
            per_date.append({"date": d, "n_sectors": int(len(vc)),
                             "min_group": int(vc.min()), "max_group": int(vc.max()),
                             "n_singletons": int((vc == 1).sum())})
    out["C4_sector_coverage"] = {
        "rows_with_sector": float(nonblank.mean()),
        "names_with_sector": float(panel.loc[nonblank, "ticker"].nunique()
                                   / max(1, panel["ticker"].nunique())),
        "n_distinct_sectors": int(sec[nonblank].nunique()),
        "min_group_any_date": min((p["min_group"] for p in per_date), default=None),
        "total_singleton_sector_dates": sum(p["n_singletons"] for p in per_date),
        "per_date": per_date,
        "meets_floor": bool(nonblank.mean() >= MIN_SECTOR_COVERAGE),
        "floor": MIN_SECTOR_COVERAGE,
    }

    # C5 - `insider` is a rescaled percentile, not a z-scored input, so the toggle must not
    # touch it. The 2026-08-02 run measured exactly 0.000.
    out["C5_insider_unchanged"] = {
        "mean_abs_change": moves.get("insider"),
        "unchanged": (moves.get("insider") is not None and moves["insider"] < 1e-9),
    }

    # C6 - median-subtraction must create no NEW missing values.
    miss = {}
    for theme in S.FACTORS_ALL:
        src = "sn_" + theme
        if src not in panel.columns:
            continue
        na_a = int(pd.to_numeric(panel[theme], errors="coerce").isna().sum())
        na_b = int(pd.to_numeric(panel[src], errors="coerce").isna().sum())
        miss[theme] = {"flat": na_a, "sn": na_b, "new_missing": na_b - na_a}
    out["C6_same_missingness"] = {
        "per_theme": miss,
        "no_new_missing": all(v["new_missing"] <= 0 for v in miss.values()),
    }

    # C7 - `sentiment` is empty, so excluding it from FLAT is correct.
    import pandas as _pd
    out["C7_sentiment_empty"] = {
        "n_non_null": int(_pd.to_numeric(panel["sentiment"], errors="coerce").notna().sum())
        if "sentiment" in panel.columns else None}
    return out


# --------------------------------------------------------------------------- main


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel", default="data/free_analysis/panel_sn_b6.pkl")
    ap.add_argument("--json", default="data/free_analysis/SECTOR_NEUTRAL_B6.json")
    args = ap.parse_args(argv)

    from valuation.edge.fundamental_panel import (holdout_compare_panels,
                                                  MIN_HOLDOUT_ALPHA_GAIN,
                                                  MIN_HOLDOUT_TSTAT_GAIN)
    from valuation.edge.research_log import detail as rl_detail

    panel = load_panel(args.panel, args.data_dir)
    flat, sn = split_arms(panel)
    print(f"[snb6] arms: flat {len(flat):,} rows, sn {len(sn):,} rows", flush=True)

    out = {
        "study": "SECTOR-NEUTRAL-B6",
        "prereg": "PREREG_sector_neutral_b6.md",
        "prereg_commit": "1bdb7e0",
        "question": ("Does sector-neutral ranking clear the SAME pre-committed held-out gate "
                     "on the corrected 69-date panel that it failed twice on the void one?"),
        "params": {"deployed_cols": DEPLOYED, "flat_cols": FLAT, "base_weight": BASE_WEIGHT,
                   "hac_lag": HAC_LAG, "n_q": 10, "horizon": 63,
                   "min_holdout_tstat_gain": MIN_HOLDOUT_TSTAT_GAIN,
                   "min_holdout_alpha_gain": MIN_HOLDOUT_ALPHA_GAIN},
        "floors": {"ls_hac": LS_HAC_FLOOR, "alpha_hac": ALPHA_HAC_FLOOR,
                   "ls_naive": LS_NAIVE_FLOOR,
                   "note": ("calibrated at THIS configuration (full-universe decile book, 69 "
                            "dates, H=63, lag 1); quoted without caveat for the FLAT arm and as "
                            "an EXTRAPOLATION for the sector-neutral arm")},
        "void_panel_reference": VOID_PANEL,
        "arms": {}, "gate": {}, "paired": {}, "controls": {},
    }

    # ---- full-sample levels, both arms, both weightings -----------------------------------
    for wname, cols in (("deployed", DEPLOYED), ("flat", FLAT)):
        for aname, p in (("OFF_flat", flat), ("ON_sector_neutral", sn)):
            key = f"{wname}/{aname}"
            t0 = time.time()
            out["arms"][key] = arm(p, cols, key)
            print(f"[snb6] arm {key}: alpha {_f(out['arms'][key].get('top_decile_alpha'))} "
                  f"ls_t {_f(out['arms'][key].get('long_short_tstat'))} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    # ---- the PRIMARY gate, unchanged --------------------------------------------------
    for wname, cols in (("deployed", DEPLOYED), ("flat", FLAT)):
        g = holdout_compare_panels(flat, sn, cols, label_a="OFF_flat",
                                   label_b="ON_sector_neutral", base_weight=BASE_WEIGHT)
        out["gate"][wname] = g
        print(f"[snb6] GATE {wname}: {g.get('verdict')}", flush=True)

    # ---- paired within-panel difference (secondary, uncalibrated) ----------------------
    for wname in ("deployed", "flat"):
        af = out["arms"][f"{wname}/OFF_flat"]
        an = out["arms"][f"{wname}/ON_sector_neutral"]
        if "dates" not in af or "dates" not in an:
            continue
        ds = af["dates"]
        mid = len(ds) // 2
        out["paired"][wname] = {
            "full": paired(af, an, None, "full"),
            "early_half": paired(af, an, ds[:mid], "early_half"),
            "late_half": paired(af, an, ds[mid + 1:], "late_half"),
            "boundary_date_embargoed": ds[mid] if ds else None,
        }

    # ---- controls ----------------------------------------------------------------------
    out["controls"] = controls(panel, flat, sn, out["arms"]["deployed/OFF_flat"])

    # ---- the verdict, by the rule fixed in prereg 3a ------------------------------------
    gd = out["gate"]["deployed"].get("verdict")
    gf = out["gate"]["flat"].get("verdict")
    c = out["controls"]
    blocked = []
    if not c["C1_identical_rows"]["key_sets_identical"]:
        blocked.append("C1 row sets differ")
    if not c["C2_toggle_not_inert"]["not_inert"]:
        blocked.append("C2 the toggle is INERT")
    if not c["C3_reproduces_record"]["all_ok"]:
        blocked.append("C3 the flat arm does not reproduce the record")
    if not c["C4_sector_coverage"]["meets_floor"]:
        blocked.append("C4 sector coverage below the 95% floor")

    if blocked:
        verdict = "NO VERDICT - CONTROL FAILED"
    elif gd == "adopt" and gf != "reject":
        verdict = "ADOPTED"
    elif gd == "reject":
        verdict = "REJECTED"
    else:
        verdict = "NOT REPLICATED"
    out["verdict"] = verdict
    out["verdict_detail"] = {"deployed_gate": gd, "flat_gate": gf,
                             "controls_blocking": blocked,
                             "rule": ("ADOPTED iff deployed gate == adopt AND flat gate != "
                                      "reject; REJECTED iff deployed gate == reject; else NOT "
                                      "REPLICATED (prereg 3a)")}
    out["closes_item"] = True
    out["adopts"] = False
    out["vintage_event_if_adopted"] = True
    out["trial_cost"] = {"n": 2, "equity_N_before": 149, "equity_N_after": 151,
                         "charged_even_if_rejected": True}
    out["research_log_N_at_run"] = rl_detail()["by_domain"]

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\n[snb6] VERDICT: {verdict}  (deployed gate {gd}, flat gate {gf})", flush=True)
    print(f"[snb6] wrote {args.json}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
