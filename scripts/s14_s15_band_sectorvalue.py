#!/usr/bin/env python3
"""S14 + S15 — the no-trade band decided on NET alpha, and sector-relative value only.

Executes `PREREG_s14_s15_band_sectorvalue.md` unmodified.

S14 needs no rebuild: `turnover_and_costs` already returns gross alpha, net alpha, turnover and
the measured cost drag. S15 reads the `sv_*` columns from a panel built with `sector_value_arm`.

Run:  python -m scripts.s14_s15_band_sectorvalue
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP          # noqa: E402
from valuation.screener import cross_sectional as CS        # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
WIDTHS = (0.12, 0.15, 0.20, 0.25, 0.30)      # the SHIPPED grid; no width invented here
ENTER_FRAC = 0.10                            # shipped, not swept
MIN_ALPHA_GAIN, MIN_TSTAT_GAIN = 0.01, 0.25
AUDIT_GROSS_ALLOWANCE = 0.015                # the audit's own 1.5pp, reported beside ours
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def zt(panel, col):
    out = pd.Series(np.nan, index=panel.index, dtype=float)
    for d, idx in panel.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(panel.loc[idx, col]), errors="coerce").values
    return out


def composite(z, w):
    idx = next(iter(z.values())).index
    num, den = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    for c, wi in w.items():
        v = z[c]
        ok = v.notna()
        num[ok] += wi * v[ok]
        den[ok] += wi
    return (num / den).where(den > 0)


def evaluate(panel, score, dates_subset):
    sub = panel[panel["date"].isin(dates_subset)]
    s = score.loc[sub.index]
    alpha, ls = [], []
    for d, idx in sub.groupby("date").groups.items():
        v, f = s.loc[idx], sub.loc[idx, "fwd_ret"]
        m = v.notna() & f.notna()
        if m.sum() < 50:
            continue
        vv, ff = v[m], f[m]
        q = vv.rank(pct=True)
        alpha.append(float(ff[q >= 0.9].mean() - ff.mean()))
        ls.append(float(ff[q >= 0.9].mean() - ff[q <= 0.1].mean()))
    if not alpha:
        return None
    a, l = np.array(alpha), np.array(ls)
    sd = l.std(ddof=1)
    return {"n_periods": len(a), "top_decile_alpha": float(a.mean() * 4.0),
            "long_short_tstat": float(l.mean() / (sd / math.sqrt(len(l)))) if sd > 0 else None}


def gate(panel, base, arm, dates, label, alpha_decides=True):
    mid = len(dates) // 2
    out = {"label": label, "boundary_date_embargoed": str(dates[mid]), "splits": {}}
    improves = []
    for name, ds in (("early_half", dates[:mid]), ("late_half", dates[mid + 1:])):
        ra, rb = evaluate(panel, base, ds), evaluate(panel, arm, ds)
        if not ra or not rb:
            out["splits"][name] = {"status": "insufficient"}
            improves.append(False)
            continue
        da = rb["top_decile_alpha"] - ra["top_decile_alpha"]
        dt = ((rb["long_short_tstat"] - ra["long_short_tstat"])
              if ra["long_short_tstat"] is not None and rb["long_short_tstat"] is not None
              else None)
        ok = bool(dt is not None and da >= MIN_ALPHA_GAIN and dt >= MIN_TSTAT_GAIN)
        improves.append(ok)
        cell = {"n_dates": len(ds), "delta_top_decile_alpha": da,
                "delta_long_short_tstat": dt, "improves": ok}
        if alpha_decides and dt is not None and da < 0 < dt:
            cell["bought_t_sold_alpha"] = True
        out["splits"][name] = cell
    out["verdict"] = ("ADOPT-ELIGIBLE" if all(improves)
                      else "REJECTED" if not any(improves) else "NOT_REPLICATED")
    return out


# ------------------------------------------------------------------ S14
def band_sweep(panel, dates_subset):
    """Every width on one set of dates, through the SHIPPED cost machinery."""
    sub = panel[panel["date"].isin(dates_subset)]
    rows = {}
    for xf in (None,) + WIDTHS:
        c = FP.turnover_and_costs(sub, THEMES, {k: W for k in THEMES}, top_frac=0.10,
                                  horizon=63, exit_frac=xf) or {}
        rows["none" if xf is None else f"{xf:.2f}"] = {
            "annual_turnover": c.get("annual_turnover"),
            "gross_alpha": c.get("gross_alpha"),
            "net_alpha": c.get("net_alpha"),
            "cost_drag_ann": c.get("cost_drag_ann")}
    return rows


def s14(panel, dates):
    """Sweep on the DECIDE half, measure the argmax width on the HELD-OUT half, both ways."""
    mid = len(dates) // 2
    halves = {"early_half": dates[:mid], "late_half": dates[mid + 1:]}
    res = {"widths_grid": list(WIDTHS), "enter_frac": ENTER_FRAC,
           "audit_gross_allowance": AUDIT_GROSS_ALLOWANCE, "directions": {}}
    verdicts = []
    for decide, measure in (("early_half", "late_half"), ("late_half", "early_half")):
        dsw = band_sweep(panel, halves[decide])
        # argmax NET alpha over the WIDTHS only (the incumbent is the comparator, not a candidate)
        cands = {k: v for k, v in dsw.items() if k != "none" and v.get("net_alpha") is not None}
        if not cands:
            res["directions"][decide] = {"status": "no candidate widths"}
            verdicts.append(False)
            continue
        pick = max(cands, key=lambda k: cands[k]["net_alpha"])
        msw = band_sweep(panel, halves[measure])
        base, arm = msw.get("none") or {}, msw.get(pick) or {}
        d_net = ((arm.get("net_alpha") or 0) - (base.get("net_alpha") or 0))
        d_gross = ((arm.get("gross_alpha") or 0) - (base.get("gross_alpha") or 0))
        saving = ((base.get("cost_drag_ann") or 0) - (arm.get("cost_drag_ann") or 0))
        # Register 3.1: net alpha must improve at all, AND gross given up must not exceed the
        # MEASURED cost saving - the tightened guard replacing the audit's 1.5pp allowance.
        ok = bool(d_net > 0 and (-d_gross) <= saving)
        verdicts.append(ok)
        res["directions"][decide] = {
            "decide_sweep": dsw, "picked_width": pick, "measure_sweep": msw,
            "delta_net_alpha": d_net, "delta_gross_alpha": d_gross,
            "measured_cost_saving": saving,
            "passes_tightened_guard": bool((-d_gross) <= saving),
            "passes_audits_own_allowance": bool((-d_gross) <= AUDIT_GROSS_ALLOWANCE),
            "improves": ok,
            # C6: is the width surface monotone on this half?
            "decide_surface_monotone_in_net": _monotone(
                [cands[f"{w:.2f}"]["net_alpha"] for w in WIDTHS
                 if f"{w:.2f}" in cands])}
        print(f"[S14] decide {decide:11s} -> width {pick}   measure: d_net {d_net:+.4f}  "
              f"d_gross {d_gross:+.4f}  saving {saving:+.4f}  improves {ok}")
    res["verdict"] = ("ADOPT-ELIGIBLE" if all(verdicts)
                      else "REJECTED" if not any(verdicts) else "NOT_REPLICATED")
    return res


def _monotone(v):
    if len(v) < 3:
        return None
    return bool(all(a <= b for a, b in zip(v, v[1:])) or all(a >= b for a, b in zip(v, v[1:])))


def top25(panel, score, date):
    idx = panel.index[panel["date"] == date]
    s = score.loc[idx].dropna()
    return list(panel.loc[s.sort_values(ascending=False).index[:25], "ticker"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=r"C:/Users/donni/Downloads/valuation-tool/data/"
                                       r"free_analysis/panel_corrected_69d.pkl")
    ap.add_argument("--sv-panel", default="")
    ap.add_argument("--json", default="data/free_analysis/S14_S15.json")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel, "rb"))
    print(f"[bs] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"
    out = {"n_rows": int(len(panel)), "controls": {}, "arms": {}}

    base_r = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    c1 = {k: float(base_r.get(k)) for k in REC if base_r.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": c1}
    print(f"[C1] reproduces record: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 failed"
        _write(args.json, out)
        return 2

    dates = sorted(panel["date"].unique())
    out["arms"]["A1_NO_TRADE_BAND"] = s14(panel, dates)

    # ---- A2 needs the sector-value panel ----
    if args.sv_panel and os.path.exists(args.sv_panel):
        sv = pickle.load(open(args.sv_panel, "rb"))
        out["arms"]["A2_SECTOR_RELATIVE_VALUE"] = s15(sv)
    else:
        out["arms"]["A2_SECTOR_RELATIVE_VALUE"] = {"status": "sv panel not supplied yet"}

    _write(args.json, out)
    print(f"\n[bs] wrote {args.json}")
    return 0


def s15(sv):
    z = {c: zt(sv, c) for c in THEMES}
    dep = composite(z, {c: W for c in THEMES})
    cols = {c: f"sv_{c}" for c in THEMES}
    if not all(v in sv.columns for v in cols.values()):
        return {"status": "sv_* columns missing"}
    zs = {c: zt(sv, cols[c]) for c in THEMES}
    arm = composite(zs, {c: W for c in THEMES})
    dates = sorted(sv["date"].unique())

    # C4 — every NON-value theme must be bit-identical
    devs = {}
    for c in THEMES:
        a = pd.to_numeric(sv[c], errors="coerce")
        b = pd.to_numeric(sv[cols[c]], errors="coerce")
        both = a.notna() & b.notna()
        devs[c] = float((a[both] - b[both]).abs().max()) if both.any() else None
    non_value_max = max(v for k, v in devs.items() if k != "value" and v is not None)
    res = {"C4_theme_max_abs_dev": devs,
           "C4_non_value_max_dev": non_value_max,
           "C4_ok": bool(non_value_max < 1e-12),
           "C4_value_moved": bool((devs.get("value") or 0) > 1e-12)}
    print(f"[C4 ] non-value max |dev| {non_value_max:.3e}  (value moved "
          f"{devs.get('value'):.4f})")

    rc = []
    for d, idx in sv.groupby("date").groups.items():
        a, b = dep.loc[idx], arm.loc[idx]
        m = a.notna() & b.notna()
        if m.sum() > 30:
            rc.append(a[m].rank().corr(b[m].rank()))
    res["rank_corr_vs_deployed"] = float(np.mean(rc)) if rc else None
    res["coverage"] = float(arm.notna().mean())
    if "sector" in sv.columns:
        res["C7_sector_coverage"] = float((sv["sector"].astype(str).str.len() > 0).mean())
        res["C7_sectors_per_date"] = float(sv.groupby("date")["sector"].nunique().mean())
    res["top25_deployed"] = top25(sv, dep, dates[-1])
    res["top25_arm"] = top25(sv, arm, dates[-1])
    res["top25_changed"] = len(set(res["top25_deployed"]) - set(res["top25_arm"]))
    res["gate"] = gate(sv, dep, arm, dates, "A2_SECTOR_RELATIVE_VALUE", alpha_decides=True)
    print(f"[gate] A2_SECTOR_RELATIVE_VALUE {res['gate']['verdict']:15s} rank_corr "
          f"{res['rank_corr_vs_deployed']:.4f}  top25_changed {res['top25_changed']}/25")
    for h, s in res["gate"]["splits"].items():
        if "delta_top_decile_alpha" in s:
            flag = "  <-- bought t, sold alpha" if s.get("bought_t_sold_alpha") else ""
            print(f"          {h:11s} d_alpha {s['delta_top_decile_alpha']:+.4f}"
                  f"  d_t {s['delta_long_short_tstat']:+.4f}"
                  f"  improves {s['improves']}{flag}")
    return res


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
