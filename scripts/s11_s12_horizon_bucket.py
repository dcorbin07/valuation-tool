#!/usr/bin/env python3
"""S11 + S12 — horizon ensemble, and ranking within bucket.

Executes `PREREG_s11_s12_horizon_bucket.md` unmodified. ONE panel build emitting both
bucket-relative arms and the 252-day forward return; every arm a column on that one frame.

Run:  python -m scripts.s11_s12_horizon_bucket --data-dir data/backtest
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

from valuation.config import CONFIG as CFG                  # noqa: E402
from valuation.edge import fundamental_panel as FP          # noqa: E402
from valuation.edge.data_providers import WRDSProvider      # noqa: E402
from valuation.screener import cross_sectional as CS        # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
H_LONG = 252                       # the audit's own second horizon; no sweep
MIN_ALPHA_GAIN, MIN_TSTAT_GAIN = 0.01, 0.25
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


def ic_weights(panel, z, dates, ret_col):
    """IC-proportional weights from the theme ICs measured on `dates` against `ret_col`.

    Non-negative and normalised. Used ONLY with `dates` = the DECIDE half (C5).
    """
    out = {}
    for c in THEMES:
        ics = []
        for d in dates:
            idx = panel.index[panel["date"] == d]
            v, f = z[c].loc[idx], panel.loc[idx, ret_col]
            m = v.notna() & f.notna()
            if m.sum() > 30:
                ics.append(v[m].corr(f[m], method="spearman"))
        ics = [x for x in ics if x == x]
        out[c] = float(np.mean(ics)) if ics else 0.0
    s = sum(max(0.0, v) for v in out.values())
    return ({c: max(0.0, v) / s for c, v in out.items()} if s > 0
            else {c: 1.0 / len(THEMES) for c in THEMES})


def pct_rank(panel, s):
    out = pd.Series(np.nan, index=panel.index, dtype=float)
    for d, idx in panel.groupby("date").groups.items():
        out.loc[idx] = s.loc[idx].rank(pct=True)
    return out


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


def turnover(panel, score, dates):
    """Mean one-way turnover of the top decile between consecutive rebalances."""
    prev, tos = None, []
    for d in dates:
        idx = panel.index[panel["date"] == d]
        s, f = score.loc[idx], panel.loc[idx, "fwd_ret"]
        m = s.notna() & f.notna()
        if m.sum() < 50:
            continue
        q = s[m].rank(pct=True)
        cur = set(panel.loc[m[m].index[q >= 0.9], "ticker"])
        if prev is not None and cur:
            tos.append(1.0 - len(cur & prev) / len(cur))
        prev = cur
    return float(np.mean(tos)) if tos else None


def top25(panel, score, date):
    idx = panel.index[panel["date"] == date]
    s = score.loc[idx].dropna()
    return list(panel.loc[s.sort_values(ascending=False).index[:25], "ticker"])


def gate(panel, base, arm, dates, label, alpha_decides=False):
    mid = len(dates) // 2
    out = {"label": label, "boundary_date_embargoed": str(dates[mid]), "splits": {},
           "alpha_decides": alpha_decides}
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
            # The audit's own metric priority for S12: "top-decile alpha decides, not the
            # t-statistic". This is the sector-neutral shape - buy t, sell alpha - and it is a
            # REJECT regardless of the t, fixed before the numbers existed.
            cell["bought_t_sold_alpha"] = True
        out["splits"][name] = cell
    out["verdict"] = ("ADOPT-ELIGIBLE" if all(improves)
                      else "REJECTED" if not any(improves) else "NOT_REPLICATED")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_s11s12.pkl")
    ap.add_argument("--json", default="data/free_analysis/S11_S12.json")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        print(f"[hb] loading banked panel {args.panel_cache}")
        panel = pickle.load(open(args.panel_cache, "rb"))
    else:
        print("[hb] building the panel ONCE (bucket_relative_arms + h252)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        panel = FP.build_fundamental_panel(
            prov, prov.universe(None), rebalance_days=63,
            lookback_years=CFG.backtest_lookback_years, horizon=63,
            extra_horizons=[H_LONG],
            bucket_relative_arms={"br": "bucket", "cr": "cap_tier"})
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        pickle.dump(panel, open(args.panel_cache, "wb"))
        print(f"[hb] banked {args.panel_cache}")

    print(f"[hb] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"

    out = {"n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
           "h_long": H_LONG, "controls": {}, "arms": {}}

    # ---- C1 ----
    base_r = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    c1 = {k: float(base_r.get(k)) for k in REC if base_r.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": c1}
    print(f"[C1] reproduces record: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 failed"
        _write(args.json, out)
        return 2

    z = {c: zt(panel, c) for c in THEMES}
    deployed = composite(z, {c: W for c in THEMES})
    dates = sorted(panel["date"].unique())
    mid = len(dates) // 2
    halves = {"early_half": dates[:mid], "late_half": dates[mid + 1:]}
    hcol = f"fwd_ret_h{H_LONG}"
    out["controls"]["C4_h252_present"] = {"ok": hcol in panel.columns,
                                          "coverage": float(pd.to_numeric(
                                              panel.get(hcol), errors="coerce").notna().mean())
                                          if hcol in panel.columns else 0.0}
    print(f"[C4] {hcol} coverage "
          f"{out['controls']['C4_h252_present']['coverage']:.4f}")

    # ---- A1: the horizon ensemble. Weights fitted on the DECIDE half only (C5). ----
    a1 = pd.Series(np.nan, index=panel.index, dtype=float)
    wdetail = {}
    for decide, measure in (("early_half", "late_half"), ("late_half", "early_half")):
        dd, dm = halves[decide], halves[measure]
        w63 = ic_weights(panel, z, dd, "fwd_ret")
        w252 = ic_weights(panel, z, dd, hcol)
        wdetail[f"decide_{decide}"] = {"w63": w63, f"w{H_LONG}": w252,
                                       "weight_corr": float(np.corrcoef(
                                           [w63[c] for c in THEMES],
                                           [w252[c] for c in THEMES])[0, 1])}
        c63, c252 = composite(z, w63), composite(z, w252)
        blend = (pct_rank(panel, c63) + pct_rank(panel, c252)) / 2.0
        sel = panel["date"].isin(dm)
        a1[sel] = blend[sel]
    out["controls"]["C5_weights_fitted_on_decide_half_only"] = wdetail
    out["controls"]["C6_horizons_differ"] = {
        k: v["weight_corr"] for k, v in wdetail.items()}
    for k, v in wdetail.items():
        print(f"[C5/C6] {k}: weight corr h63 vs h{H_LONG} = {v['weight_corr']:+.4f}")

    panel = panel.copy()
    panel["_deployed"] = deployed
    panel["A1_HORIZON_BLEND"] = a1

    # ---- A2/A3: the bucket-relative arms, from the panel's own paired columns ----
    arms = {"A1_HORIZON_BLEND": a1}
    for pfx, name in (("br", "A2_VALUATION_BUCKET"), ("cr", "A3_CAP_TIER")):
        cols = {c: f"{pfx}_{c}" for c in THEMES}
        if not all(v in panel.columns for v in cols.values()):
            out["arms"][name] = {"status": f"columns missing for prefix {pfx}"}
            continue
        zb = {c: zt(panel, cols[c]) for c in THEMES}
        arms[name] = composite(zb, {c: W for c in THEMES})

    # ---- C7: group sizes ----
    for gcol in ("bucket", "cap_tier"):
        if gcol in panel.columns:
            g = panel.groupby(["date", gcol]).size().groupby(gcol).mean()
            out["controls"].setdefault("C7_group_sizes", {})[gcol] = {
                str(k): float(v) for k, v in g.items()}
            print(f"[C7] {gcol} mean per-date group sizes: "
                  + " ".join(f"{k}={v:.0f}" for k, v in g.items()))

    last = dates[-1]
    out["top25_deployed"] = top25(panel, deployed, last)
    out["top25_date"] = str(last)

    for name, sc in arms.items():
        panel[name] = sc
        e = out["arms"].setdefault(name, {})
        e["coverage"] = float(sc.notna().mean())
        rc = []
        for d, idx in panel.groupby("date").groups.items():
            a, b = deployed.loc[idx], sc.loc[idx]
            m = a.notna() & b.notna()
            if m.sum() > 30:
                rc.append(a[m].rank().corr(b[m].rank()))
        e["rank_corr_vs_deployed"] = float(np.mean(rc)) if rc else None
        e["turnover"] = turnover(panel, sc, dates)
        e["top25"] = top25(panel, sc, last)
        e["top25_changed_vs_deployed"] = len(set(out["top25_deployed"]) - set(e["top25"]))
        e["gate"] = gate(panel, deployed, sc, dates, name,
                         alpha_decides=name.startswith(("A2", "A3")))
        print(f"[gate] {name:22s} {e['gate']['verdict']:15s} rank_corr "
              f"{e['rank_corr_vs_deployed']:.4f} turnover {e['turnover']:.4f} "
              f"top25_changed {e['top25_changed_vs_deployed']}/25")
        for h, s in e["gate"]["splits"].items():
            if "delta_top_decile_alpha" in s:
                flag = "  <-- bought t, sold alpha" if s.get("bought_t_sold_alpha") else ""
                print(f"          {h:11s} d_alpha {s['delta_top_decile_alpha']:+.4f}"
                      f"  d_t {s['delta_long_short_tstat']:+.4f}"
                      f"  improves {s['improves']}{flag}")

    out["arms"].setdefault("A1_HORIZON_BLEND", {})["turnover_deployed"] = turnover(
        panel, deployed, dates)
    print(f"[trn] deployed turnover {out['arms']['A1_HORIZON_BLEND']['turnover_deployed']:.4f}")

    # ---- C8: does the cap-tier arm shrink the book's size exposure? ----
    if "A3_CAP_TIER" in arms:
        out["controls"]["C8_size_exposure"] = size_exposure(panel, deployed,
                                                            arms["A3_CAP_TIER"], z, dates)

    _write(args.json, out)
    print(f"\n[hb] wrote {args.json}")
    return 0


def size_exposure(panel, deployed, arm, z, dates):
    """C8 — the book's mean `size` z-score, before and after. X3 says `size` carries the
    composite's entire significance, so this is the direct test of the mechanism."""
    def mean_size(score):
        vals = []
        for d in dates:
            idx = panel.index[panel["date"] == d]
            s, f = score.loc[idx], panel.loc[idx, "fwd_ret"]
            m = s.notna() & f.notna()
            if m.sum() < 50:
                continue
            q = s[m].rank(pct=True)
            top = m[m].index[q >= 0.9]
            v = z["size"].loc[top]
            if v.notna().any():
                vals.append(float(v.mean(skipna=True)))
        return float(np.mean(vals)) if vals else None

    a, b = mean_size(deployed), mean_size(arm)
    res = {"deployed_mean_size_z": a, "cap_tier_mean_size_z": b,
           "shrinkage": (None if a is None or b is None or a == 0 else 1.0 - b / a)}
    print(f"[C8 ] book mean size z: deployed {a:+.4f} -> cap-tier {b:+.4f}"
          + (f"  ({res['shrinkage']:.1%} shrink)" if res["shrinkage"] is not None else ""))
    return res


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
