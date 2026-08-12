#!/usr/bin/env python3
"""S7 + S18 — pre-registered interactions, and short interest as one.

Executes `PREREG_s7_s18_interactions.md` unmodified. NO panel rebuild: every input is already on
the banked corrected 69-date panel, and short interest joins from the cache point-in-time.

Run:  python -m scripts.s7_s18_interactions
"""
from __future__ import annotations

import argparse
import bisect
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
MIN_ALPHA_GAIN, MIN_TSTAT_GAIN = 0.01, 0.25
SI_TOP_PCT = 0.05          # A6: drop the top 5% most-shorted, pre-committed
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def zt(panel, col):
    out = pd.Series(np.nan, index=panel.index, dtype=float)
    for d, idx in panel.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(panel.loc[idx, col]), errors="coerce").values
    return out


def z_of(panel, s):
    out = pd.Series(np.nan, index=panel.index, dtype=float)
    tmp = panel[["date"]].copy()
    tmp["_v"] = s
    for d, idx in tmp.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(tmp.loc[idx, "_v"]), errors="coerce").values
    return out


def composite(z, w):
    """Shipped convention: weighted sum renormalised by the PRESENT-weight mass (audit B7)."""
    idx = next(iter(z.values())).index
    num, den = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    for c, wi in w.items():
        v = z[c]
        ok = v.notna()
        num[ok] += wi * v[ok]
        den[ok] += wi
    return (num / den).where(den > 0)


def market_vol_regime(panel):
    """Trailing realised volatility of the BENCHMARK, strictly from dates before each date."""
    per = panel.groupby("date")["bench_ret"].first().sort_index()
    dates = list(per.index)
    out = {}
    for i, d in enumerate(dates):
        prior = per.iloc[max(0, i - 8):i]          # up to 8 prior periods, STRICTLY before
        out[d] = float(np.std(prior.values, ddof=1)) if len(prior) >= 3 else np.nan
    return pd.Series([out[d] for d in panel["date"]], index=panel.index, dtype=float)


def load_si():
    p = r"C:/Users/donni/Downloads/valuation-tool/data/bulk/prepared/short_interest.pkl"
    si = pickle.load(open(p, "rb"))
    return {t: sorted(v) for t, v in si.items()}


def join_si(panel, si):
    """days_to_cover from the latest settlement STRICTLY BEFORE the scoring date (C5)."""
    vals = np.full(len(panel), np.nan)
    used = [None] * len(panel)
    tick = panel["ticker"].values
    dts = panel["date"].astype(str).values
    cache = {t: [r[0] for r in rows] for t, rows in si.items()}
    for i in range(len(panel)):
        rows = si.get(tick[i])
        if not rows:
            continue
        j = bisect.bisect_left(cache[tick[i]], dts[i][:10])   # strictly before
        if j > 0:
            vals[i] = rows[j - 1][1]
            used[i] = rows[j - 1][0]
    return (pd.Series(vals, index=panel.index),
            pd.Series(used, index=panel.index, dtype=object))


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


def gate(panel, base, arm, dates, label):
    mid = len(dates) // 2
    out = {"label": label, "boundary_date_embargoed": str(dates[mid]),
           "n_dates_total": len(dates), "splits": {}}
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
        out["splits"][name] = {"n_dates": len(ds), "delta_top_decile_alpha": da,
                               "delta_long_short_tstat": dt, "improves": ok}
    out["verdict"] = ("ADOPT-ELIGIBLE" if all(improves)
                      else "REJECTED" if not any(improves) else "NOT_REPLICATED")
    return out


def _dd(a):
    """Max drawdown, NEGATIVE. S10: improvement is `arm - base`, never `base - arm`."""
    lvl = np.cumprod(1.0 + np.asarray(a, dtype=float))
    return float((lvl / np.maximum.accumulate(lvl) - 1.0).min())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=r"C:/Users/donni/Downloads/valuation-tool/data/"
                                       r"free_analysis/panel_corrected_69d.pkl")
    ap.add_argument("--json", default="data/free_analysis/S7_S18_INTERACTIONS.json")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel, "rb"))
    print(f"[i] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"
    out = {"n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
           "si_top_pct_excluded": SI_TOP_PCT, "controls": {}, "arms": {},
           "NOT_TESTED": {"size_x_liquidity":
                          "UNBUILDABLE - the price export carries date+close only, so "
                          "avg_dollar_volume cannot be computed on this path (audit B13). "
                          "Reported, not replaced with a proxy. Charges no trial."}}

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

    # ---- the interaction columns ----
    si = load_si()
    si_dtc, si_used = join_si(panel, si)
    # C5: the join must be strictly point-in-time. Type-safe: `si_used` carries None for rows
    # with no settlement, and pandas will happily coerce those to NaN, so compare only where the
    # entry is actually a date string rather than trusting `is not None`.
    _sd = panel["date"].astype(str).str[:10].values
    bad = [(_sd[i], si_used.iloc[i]) for i in range(len(panel))
           if isinstance(si_used.iloc[i], str) and si_used.iloc[i] >= _sd[i]]
    out["controls"]["C5_short_interest_join_is_pit"] = {
        "violations": len(bad), "ok": len(bad) == 0, "examples": bad[:3]}
    print(f"[C5] short-interest PIT join violations: {len(bad)}")

    z_si = z_of(panel, -si_dtc)          # NEGATED: high days-to-cover = crowded = the bad side
    regime = market_vol_regime(panel)
    z_reg = z_of(panel, regime)

    raw = {
        "A1_VALUE_x_QUALITY": z["value"] * z["quality"],
        "A2_MOM_x_VOLREGIME": z["momentum"] * z_reg,
        "A3_VALUE_x_INST": z["value"] * z["institutional"],
        "A4_VALUE_x_SHORTINT": z["value"] * z_si,
        "A5_MOM_x_SHORTINT": z["momentum"] * z_si,
    }
    parents = {"A1_VALUE_x_QUALITY": ("value", "quality"),
               "A2_MOM_x_VOLREGIME": ("momentum", None),
               "A3_VALUE_x_INST": ("value", "institutional"),
               "A4_VALUE_x_SHORTINT": ("value", None),
               "A5_MOM_x_SHORTINT": ("momentum", None)}

    si_dates = sorted({d for d in dates if si_dtc[panel["date"] == d].notna().any()})
    out["short_interest_coverage"] = {
        "dates_covered": len(si_dates), "dates_total": len(dates),
        "date_coverage": len(si_dates) / len(dates),
        "first_covered": str(si_dates[0])[:10] if si_dates else None,
        "row_coverage_on_covered_dates": float(
            si_dtc[panel["date"].isin(si_dates)].notna().mean()) if si_dates else 0.0}
    print(f"[cov] short interest: {len(si_dates)}/{len(dates)} dates "
          f"({len(si_dates)/len(dates):.1%}), first {out['short_interest_coverage']['first_covered']}")

    # ---- C7: the dilution control (a CONSTANT eighth column) ----
    zc = dict(z)
    zc["_const"] = pd.Series(0.0, index=panel.index)
    diluted = composite(zc, {**{c: W for c in THEMES}, "_const": W})
    out["controls"]["C7_dilution"] = {}
    for half_name, ds in (("early_half", dates[:len(dates)//2]),
                          ("late_half", dates[len(dates)//2+1:])):
        rb, ra = evaluate(panel, diluted, ds), evaluate(panel, deployed, ds)
        out["controls"]["C7_dilution"][half_name] = {
            "delta_top_decile_alpha": rb["top_decile_alpha"] - ra["top_decile_alpha"],
            "delta_long_short_tstat": rb["long_short_tstat"] - ra["long_short_tstat"]}
    print(f"[C7] dilution alone: early "
          f"{out['controls']['C7_dilution']['early_half']['delta_top_decile_alpha']:+.4f}  late "
          f"{out['controls']['C7_dilution']['late_half']['delta_top_decile_alpha']:+.4f}")

    # ---- A1..A5 ----
    for name, col in raw.items():
        zi = z_of(panel, col)
        arm_score = composite({**z, name: zi}, {**{c: W for c in THEMES}, name: W})
        e = out["arms"].setdefault(name, {})
        e["coverage"] = float(zi.notna().mean())
        # C6: is the interaction just a parent?
        e["corr_with_parents"] = {}
        for p in [x for x in parents[name] if x]:
            m = zi.notna() & z[p].notna()
            e["corr_with_parents"][p] = float(zi[m].corr(z[p][m])) if m.sum() > 100 else None
        rc = []
        for d, idx in panel.groupby("date").groups.items():
            a, b = deployed.loc[idx], arm_score.loc[idx]
            m = a.notna() & b.notna()
            if m.sum() > 30:
                rc.append(a[m].rank().corr(b[m].rank()))
        e["rank_corr_vs_deployed"] = float(np.mean(rc)) if rc else None
        use = si_dates if "SHORTINT" in name else dates
        e["gated_on"] = ("COVERED SUBSAMPLE (S18, partial-sample per register 4.1)"
                         if "SHORTINT" in name else "full panel")
        e["gate"] = gate(panel, deployed, arm_score, use, name)
        print(f"[gate] {name:22s} {e['gate']['verdict']:15s} rank_corr "
              f"{e['rank_corr_vs_deployed']:.4f} cov {e['coverage']:.4f} "
              f"({len(use)} dates)")
        for h, s in e["gate"]["splits"].items():
            if "delta_top_decile_alpha" in s:
                print(f"          {h:11s} d_alpha {s['delta_top_decile_alpha']:+.4f}"
                      f"  d_t {s['delta_long_short_tstat']:+.4f}  improves {s['improves']}")

    # ---- A6: the exclusion ----
    out["arms"]["A6_SHORTINT_EXCLUSION"] = exclusion_arm(panel, deployed, si_dtc, si_dates)

    _write(args.json, out)
    print(f"\n[i] wrote {args.json}")
    return 0


def exclusion_arm(panel, deployed, si_dtc, si_dates):
    """Drop the top 5% most-shorted from the top decile. S10's two caveats apply verbatim."""
    base_r, arm_r = [], []
    dropped = 0
    total = 0
    for d in si_dates:
        idx = panel.index[panel["date"] == d]
        sub = panel.loc[idx]
        s, f = deployed.loc[idx], sub["fwd_ret"]
        m = s.notna() & f.notna()
        if m.sum() < 50:
            continue
        q = s[m].rank(pct=True)
        top = m[m].index[q >= 0.9]
        if len(top) < 10:
            continue
        dtc = si_dtc.loc[top]
        base_r.append(float(panel.loc[top, "fwd_ret"].mean()))
        # the most-shorted 5% BY days-to-cover; names with no reading are KEPT, never excluded
        thresh = dtc.quantile(1.0 - SI_TOP_PCT)
        keep = top[~((dtc.notna()) & (dtc >= thresh))]
        dropped += len(top) - len(keep)
        total += len(top)
        arm_r.append(float(panel.loc[keep, "fwd_ret"].mean()) if len(keep) else np.nan)

    b, a = np.array(base_r), np.array(arm_r)
    ok = ~np.isnan(a)
    b, a = b[ok], a[ok]
    res = {
        "n_periods": int(len(a)), "dropped_rate": dropped / max(1, total),
        "base_ann": float(b.mean() * 4.0), "arm_ann": float(a.mean() * 4.0),
        "delta_ann": float((a.mean() - b.mean()) * 4.0),
        "base_max_drawdown": _dd(b), "arm_max_drawdown": _dd(a),
        # S10: max_drawdown is NEGATIVE; the gain is arm - base, never base - arm.
        "drawdown_gain_pp": (_dd(a) - _dd(b)) * 100.0,
        "CAVEAT_no_calibrated_floor": ("X7 calibrates NO drawdown floor anywhere, so this is a "
                                       "measurement and carries no verdict; S10 also measured "
                                       "that this book's worst drawdown spans a SINGLE quarter."),
    }
    print(f"[A6 ] dropped {res['dropped_rate']:.4f} of top-decile rows; ann "
          f"{res['base_ann']:+.4f} -> {res['arm_ann']:+.4f} ({res['delta_ann']:+.4f}); "
          f"maxDD {res['base_max_drawdown']:+.4f} -> {res['arm_max_drawdown']:+.4f} "
          f"(gain {res['drawdown_gain_pp']:+.4f}pp)")
    return res


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
