#!/usr/bin/env python3
"""U2 — the options surface as a STOCK signal. Executes PREREG_u2_surface_stock_signals.md.

No panel rebuild: the corrected 69-date panel is banked, and the surface features join to it
point-in-time from the derived layer.

Run:  python -m scripts.u2_surface_stock
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

from valuation.edge import fundamental_panel as FP        # noqa: E402
from valuation.studies import surface_stock as SS            # noqa: E402
from valuation.screener import cross_sectional as CS      # noqa: E402

PANEL = (r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis/"
         r"panel_corrected_69d.pkl")
W = 0.125
POWER_COLS = ("z_gp_on_capital", "z_ret_6_1")

#: C1 — the published record. If the harness cannot reproduce this, no arm is read.
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def zt_within(frame, col, dates):
    """Z-score `col` within each covered cross-section (register §2.3)."""
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    sub = frame[frame["date"].isin(list(dates))]
    for _d, idx in sub.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(frame.loc[idx, col]), errors="coerce").values
    return out


def _load_derived(tickers, derived_dir):
    arms = {}
    for t in sorted(tickers):
        p = os.path.join(derived_dir, t, f"{t}-daily.pkl")
        if not os.path.exists(p):
            continue
        try:
            df = pickle.load(open(p, "rb"))
        except Exception:
            continue
        if isinstance(df, pd.DataFrame) and "date" in df.columns:
            arms[t] = SS.build_arm_columns(df)
    return arms


def _raw_ts6030(tickers, derived_dir, limit=150):
    """C4 — the SHIPPED term_slope_60_30, loaded ONLY to report how far it is from the O16 one."""
    rows = []
    for t in sorted(tickers)[:limit]:
        p = os.path.join(derived_dir, t, f"{t}-daily.pkl")
        if not os.path.exists(p):
            continue
        try:
            df = pickle.load(open(p, "rb"))
        except Exception:
            continue
        if "term_slope_60_30" not in df.columns:
            continue
        a = pd.to_numeric(df.get("atm_iv_60"), errors="coerce").astype(float)
        b = pd.to_numeric(df.get("atm_iv_front"), errors="coerce").astype(float)
        rows.append(pd.DataFrame({"o16": a - b,
                                  "shipped": pd.to_numeric(df["term_slope_60_30"],
                                                           errors="coerce").astype(float)}))
    if not rows:
        return None
    big = pd.concat(rows, ignore_index=True).dropna()
    if len(big) < 100:
        return None
    return {"n": int(len(big)),
            "spearman_o16_vs_shipped": float(big["o16"].corr(big["shipped"], method="spearman")),
            "pearson_o16_vs_shipped": float(big["o16"].corr(big["shipped"]))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=PANEL)
    ap.add_argument("--derived", default=SS.DERIVED_DIR)
    ap.add_argument("--json", default="data/free_analysis/U2_SURFACE_STOCK.json")
    args = ap.parse_args()

    out = {"register": "PREREG_u2_surface_stock_signals.md", "controls": {}, "arms": {},
           "NOT_TESTED": {
               "put_call_parity_deviation_matched_strikes":
                   "Cremers-Weinbaum's ACTUAL measure and the largest effect the audit cites "
                   "(51bps/week). Needs matched call/put pairs at the same strike and expiry, "
                   "which live in the raw chains, not the derived layer. Building it is a new "
                   "feature and the register declines it (§0.5). NOT a null - untested.",
               "twenty_one_day_changes":
                   "A change is a different hypothesis from a level (surface momentum, not "
                   "surface). Declined by §0.5. NOT a null - untested.",
               "consequence": "The U2 ledger row closes PARTIAL, not DONE."}}

    panel = pickle.load(open(args.panel, "rb"))
    print(f"[i] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"])

    # ---------------- C1 — harness reproduction, a GATE ----------------
    base = FP.quantile_backtest(panel, list(SS.INCUMBENTS),
                                {c: W for c in SS.INCUMBENTS}, n_q=10, horizon=63)
    c1 = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": c1}
    print(f"[C1] reproduces record: {ok1}  {c1}")
    if not ok1:
        out["ABORTED"] = "C1 failed - the harness does not reproduce the published record"
        _write(args.json, out)
        return 2

    # ---------------- the join ----------------
    arms_by_ticker = _load_derived(set(panel["ticker"].unique()), args.derived)
    print(f"[i] derived frames for {len(arms_by_ticker)} panel names")
    joined, c3 = SS.join_pit(panel, arms_by_ticker)
    out["controls"]["C3_point_in_time"] = c3
    print(f"[C3] joined {c3['n_joined']} cells, PIT violations {c3['pit_violations']}")
    if not c3["ok"]:
        out["ABORTED"] = "C3 found point-in-time violations"
        _write(args.json, out)
        return 2

    cdates = SS.covered_dates(joined)
    early, late, boundary = SS.halves(cdates)
    out["covered"] = {"n_dates": len(cdates), "first": str(cdates[0]), "last": str(cdates[-1]),
                      "n_early": len(early), "n_late": len(late),
                      "boundary_embargoed": str(boundary),
                      "n_panel_dates": int(panel["date"].nunique()),
                      "note": "Halves are of the COVERED SUBSAMPLE. 29 of 69 panel dates carry "
                              "ZERO coverage and all are early, so a full-panel both-halves "
                              "gate is impossible, not merely weak (register §0.4)."}
    print(f"[i] covered {len(cdates)} dates {cdates[0]}..{cdates[-1]}; "
          f"halves {len(early)}/{len(late)}, boundary {boundary} embargoed")

    cov_rows = joined[joined["date"].isin(cdates)].copy()

    # ---------------- C5 — no negated duplicate ----------------
    try:
        out["controls"]["C5_no_negated_duplicate"] = SS.assert_no_negated_duplicate(
            cov_rows, list(SS.COMPONENT_ARMS))
    except SS.RegisterViolation as e:
        out["ABORTED"] = f"C5: {e}"
        _write(args.json, out)
        return 2
    print("[C5] no arm is another arm's negation")

    # ---------------- C4 — the O16 construction is the one used ----------------
    c4 = _raw_ts6030(set(cov_rows["ticker"].unique()), args.derived) or {}
    c4["arm_built_from"] = "atm_iv_60 - atm_iv_front"
    c4["shipped_column_used"] = False
    out["controls"]["C4_o16_construction"] = c4
    print(f"[C4] O16 ctor vs shipped term_slope_60_30: {c4.get('spearman_o16_vs_shipped')}")

    # ---------------- standardise within the covered cross-sections ----------------
    for c in SS.COMPONENT_ARMS:
        cov_rows[f"z_{c}"] = zt_within(cov_rows, c, cdates)
    inc_z = []
    for c in SS.INCUMBENTS:
        cov_rows[f"zi_{c}"] = zt_within(cov_rows, c, cdates)
        inc_z.append(f"zi_{c}")

    # ---------------- C2 — the audit's own POWER control ----------------
    pc = {}
    for col in POWER_COLS:
        if col not in cov_rows.columns:
            pc[col] = {"raw_ic_tstat": None, "why": "column absent from the panel"}
            continue
        cov_rows[f"zp_{col}"] = zt_within(cov_rows, col, cdates)
        pc[col] = SS.arm_ic(cov_rows, f"zp_{col}", cdates, inc_z)
    power = SS.power_verdict(pc)
    out["controls"]["C2_power"] = {"per_control": pc, **power}
    print(f"[C2] power: {power['detail']}  any_cleared={power['any_cleared']}")

    # ---------------- C8 coverage, C6 is-this-an-incumbent ----------------
    c8 = {}
    for c in SS.COMPONENT_ARMS:
        c8[c] = {"full": float(cov_rows[c].notna().mean()),
                 "early": float(cov_rows[cov_rows["date"].isin(early)][c].notna().mean()),
                 "late": float(cov_rows[cov_rows["date"].isin(late)][c].notna().mean())}
    out["controls"]["C8_coverage"] = c8
    print(f"[C8] coverage {[(k, round(v['full'], 4)) for k, v in c8.items()]}")

    c6 = {}
    for c in SS.COMPONENT_ARMS:
        c6[c] = {}
        for other in ("low_risk", "z_neg_log_mktcap", "momentum", "size"):
            if other not in cov_rows.columns:
                continue
            per = []
            for _d, g in cov_rows.groupby("date"):
                ss = g[[c, other]].dropna()
                if len(ss) >= SS.MIN_NAMES:
                    r = ss[c].corr(ss[other], method="spearman")
                    if r == r:
                        per.append(float(r))
            c6[c][other] = float(np.mean(per)) if per else None
    out["controls"]["C6_incumbent_proxy"] = {
        "mean_per_date_spearman": c6,
        "note": "Diagnostic, NO verdict. |corr| > 0.8 against low_risk or size would mean the "
                "arm is substantially an incumbent exposure and must be quoted with that."}
    print(f"[C6] vs low_risk: {[(k, None if v.get('low_risk') is None else round(v['low_risk'], 4)) for k, v in c6.items()]}")

    # ---------------- ARMS A1-A3 ----------------
    for c in SS.COMPONENT_ARMS:
        zc = f"z_{c}"
        full = SS.arm_ic(cov_rows, zc, cdates, inc_z)
        e = SS.arm_ic(cov_rows, zc, early, inc_z)
        l = SS.arm_ic(cov_rows, zc, late, inc_z)
        v = SS.arm_verdict(e.get("incremental_ic_tstat"), l.get("incremental_ic_tstat"), c,
                           power_ok=power["any_cleared"],
                           degenerate_early=bool(e.get("incremental_degenerate")),
                           degenerate_late=bool(l.get("incremental_degenerate")))
        out["arms"][c] = {"full_sample": full, "early_half": e, "late_half": l, "verdict": v}
        print(f"[{c:11s}] incr t  full {_f(full.get('incremental_ic_tstat'))}  "
              f"early {_f(e.get('incremental_ic_tstat'))}  late {_f(l.get('incremental_ic_tstat'))}"
              f"   raw t full {_f(full.get('raw_ic_tstat'))}  -> {v['verdict']}")

    # ---------------- ARM A4 — the composite, decide-then-measure ----------------
    a4 = {"directions": {}}
    for name, (dec, mea) in {"decide_early_measure_late": (early, late),
                             "decide_late_measure_early": (late, early)}.items():
        try:
            blend, meta = SS.orient_and_blend(cov_rows, dec, [f"z_{c}" for c in SS.COMPONENT_ARMS],
                                              inc_z)
        except SS.RegisterViolation as ex:
            a4["directions"][name] = {"error": str(ex)}
            continue
        cov_rows["_surface"] = blend
        cov_rows["z_surface"] = zt_within(cov_rows, "_surface", cdates)
        r = SS.arm_ic(cov_rows, "z_surface", mea, inc_z)
        a4["directions"][name] = {"orientation": {k: float(v) for k, v in meta["signs"].items()},
                                  "dropped": meta["dropped"], "measured": r}
        print(f"[surface   ] {name}: incr t {_f(r.get('incremental_ic_tstat'))} "
              f"signs {meta['signs']}")

    ts = [d.get("measured", {}).get("incremental_ic_tstat")
          for d in a4["directions"].values() if "measured" in d]
    degen = [bool(d.get("measured", {}).get("incremental_degenerate"))
             for d in a4["directions"].values() if "measured" in d]
    a4["verdict"] = SS.arm_verdict(ts[0] if len(ts) > 0 else None,
                                   ts[1] if len(ts) > 1 else None, "surface",
                                   power_ok=power["any_cleared"],
                                   degenerate_early=bool(degen and degen[0]),
                                   degenerate_late=bool(len(degen) > 1 and degen[1]))
    a4["note"] = ("Both 'halves' for this arm are the two MEASURE halves of the two "
                  "decide-then-measure directions; no sign is declared and the orientation is "
                  "fitted where the verdict is not read.")
    out["arms"]["surface"] = a4
    print(f"[surface   ] -> {a4['verdict']['verdict']}")

    # ---------------- the book gate, only if A4 is eligible ----------------
    if a4["verdict"]["verdict"] == "ADOPT-ELIGIBLE":
        out["book_gate"] = _book_gate(cov_rows, cdates)
    else:
        out["book_gate"] = {
            "run": False,
            "why": f"register §4.3 runs the book gate only on an eligible A4; A4 is "
                   f"{a4['verdict']['verdict']}. The long-short HAC floor {SS.LS_HAC_FLOOR} is "
                   f"therefore NOT quoted for this item."}
        print(f"[book] not run - A4 is {a4['verdict']['verdict']}")

    out["bars"] = {"ic_bar": SS.IC_BAR, "ls_hac_floor": SS.LS_HAC_FLOOR,
                   "power_bar": SS.POWER_BAR,
                   "EXTRAPOLATION": "Both calibrated bars were measured on the FULL 69-date "
                                    "2,531-name panel at h63 lag 1. This item runs on a 40-date "
                                    "~437-name covered subsample, so both are EXTRAPOLATIONS and "
                                    "must be labelled so wherever quoted."}
    _write(args.json, out)
    print(f"\n[i] wrote {args.json}")
    return 0


def _book_gate(cov_rows, cdates):
    """Register §4.3 — the shipped held-out gate, plus C7's eighth-column dilution control.

    `holdout_compare_panels` scores BOTH panels with the SAME `cols`, so the eight-theme
    comparison is made by holding the column list fixed at eight and changing only the VALUES of
    the eighth: constant in A, the real surface blend in B. That isolates the surface's
    information from the 1/7 -> 1/8 reweighting, which is the compound-change trap S7/S18 named.

    C7 then measures the reweighting on its own: seven columns against eight-with-a-constant,
    per half, through the shipped `quantile_backtest`.
    """
    base = cov_rows[cov_rows["date"].isin(cdates)].copy()
    cols8 = list(SS.INCUMBENTS) + ["surface"]

    a = base.copy()
    a["surface"] = 0.0                      # exactly-zero variance (SECTOR-NEUTRAL-B6 safe list)
    b = base.copy()
    b["surface"] = b["z_surface"]

    w7 = {c: W for c in SS.INCUMBENTS}
    w8 = {c: W for c in cols8}
    early, late, boundary = SS.halves(cdates)

    dilution = {}
    for nm, ds in {"early_half": early, "late_half": late}.items():
        r7 = FP.quantile_backtest(base[base["date"].isin(ds)], list(SS.INCUMBENTS), w7,
                                  n_q=10, horizon=63) or {}
        r8 = FP.quantile_backtest(a[a["date"].isin(ds)], cols8, w8, n_q=10, horizon=63) or {}
        dilution[nm] = {
            "seven_top_decile_alpha": r7.get("top_decile_alpha"),
            "eight_constant_top_decile_alpha": r8.get("top_decile_alpha"),
            "delta_top_decile_alpha": (
                None if r7.get("top_decile_alpha") is None or r8.get("top_decile_alpha") is None
                else r8["top_decile_alpha"] - r7["top_decile_alpha"]),
            "seven_long_short_tstat": r7.get("long_short_tstat"),
            "eight_constant_long_short_tstat": r8.get("long_short_tstat")}

    gate = FP.holdout_compare_panels(a, b, cols8, label_a="eight_with_constant",
                                     label_b="eight_with_surface")
    hac = {}
    for nm, ds in {"early_half": early, "late_half": late}.items():
        rb = FP.quantile_backtest(b[b["date"].isin(ds)], cols8, w8, n_q=10, horizon=63) or {}
        hac[nm] = rb.get("long_short_tstat_nw")

    return {"holdout_gate": gate,
            "C7_eighth_column_dilution": {
                "per_half": dilution,
                "note": "The composite renormalises by PRESENT weight mass (audit B7), so an "
                        "eighth column that z-scores to all-NaN is a mathematical no-op. This "
                        "measures whether that is what happens rather than assuming it."},
            "long_short_tstat_nw_with_surface": hac,
            "ls_hac_floor": SS.LS_HAC_FLOOR,
            "floor_is_an_extrapolation":
                "2.2837 was calibrated on the full 69-date 2,531-name panel. Quoted here against "
                "a 40-date covered subsample it is an EXTRAPOLATION and is labelled so."}


def _f(x):
    return "None" if x is None else f"{x:+.4f}"


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), indent=1, default=str)


if __name__ == "__main__":
    raise SystemExit(main())
