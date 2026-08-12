#!/usr/bin/env python3
"""S8 + S9 — signal freshness and data staleness.

Executes `PREREG_s8_s9_freshness.md` unmodified. ONE panel build with `with_freshness=True`;
every arm a column on that one frame.

Run:  python -m scripts.s8_s9_freshness --data-dir data/backtest
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
# PRE-COMMITTED with the register. No half-life is fitted.
HL_FUND = 90.0            # one reporting quarter; a convention, labelled one
HL_13F = 180.0            # from the project's OWN measured 13F decay (alive Q-2, dead Q-3)
FUND_THEMES = ["value", "quality", "capital_discipline"]     # SF1-derived only
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


def z_of(panel, s):
    out = pd.Series(np.nan, index=panel.index, dtype=float)
    tmp = panel[["date"]].copy()
    tmp["_v"] = s
    for d, idx in tmp.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(tmp.loc[idx, "_v"]), errors="coerce").values
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


def decay(age, hl):
    """exp(-age/hl). A row with NO age is left UNDECAYED (multiplier 1.0), never punished."""
    a = pd.to_numeric(age, errors="coerce")
    return np.exp(-a.clip(lower=0.0) / hl).fillna(1.0)


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
        out["splits"][name] = {"n_dates": len(ds), "delta_top_decile_alpha": da,
                               "delta_long_short_tstat": dt, "improves": ok}
    out["verdict"] = ("ADOPT-ELIGIBLE" if all(improves)
                      else "REJECTED" if not any(improves) else "NOT_REPLICATED")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_s8s9.pkl")
    ap.add_argument("--json", default="data/free_analysis/S8_S9_FRESHNESS.json")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        print(f"[f] loading banked panel {args.panel_cache}")
        panel = pickle.load(open(args.panel_cache, "rb"))
    else:
        print("[f] building the panel ONCE (with_freshness=True)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        panel = FP.build_fundamental_panel(prov, prov.universe(None), rebalance_days=63,
                                           lookback_years=CFG.backtest_lookback_years,
                                           horizon=63, with_freshness=True)
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        pickle.dump(panel, open(args.panel_cache, "wb"))
        print(f"[f] banked {args.panel_cache}")

    print(f"[f] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"

    out = {"n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
           "hl_fund_days": HL_FUND, "hl_13f_days": HL_13F, "fund_themes": FUND_THEMES,
           "controls": {}, "arms": {}}

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

    dsf = pd.to_numeric(panel.get("days_since_filing"), errors="coerce")
    d13 = pd.to_numeric(panel.get("days_since_13f"), errors="coerce")

    # ---- C5: ages must be sane. A NEGATIVE age is a look-ahead and ABORTS. ----
    neg_f = int((dsf < 0).sum())
    neg_i = int((d13 < 0).sum())
    out["controls"]["C5_ages_sane"] = {
        "days_since_filing": {"non_null": float(dsf.notna().mean()), "negative": neg_f,
                              "p05": float(dsf.quantile(0.05)), "median": float(dsf.median()),
                              "p95": float(dsf.quantile(0.95)), "max": float(dsf.max())},
        "days_since_13f": {"non_null": float(d13.notna().mean()), "negative": neg_i,
                           "p05": float(d13.quantile(0.05)), "median": float(d13.median()),
                           "p95": float(d13.quantile(0.95)), "max": float(d13.max())},
        "ok": bool(neg_f == 0 and neg_i == 0)}
    print(f"[C5] days_since_filing cov {dsf.notna().mean():.4f} median {dsf.median():.1f} "
          f"p95 {dsf.quantile(0.95):.1f} negatives {neg_f}")
    print(f"[C5] days_since_13f    cov {d13.notna().mean():.4f} median {d13.median():.1f} "
          f"p95 {d13.quantile(0.95):.1f} negatives {neg_i}")
    if neg_f or neg_i:
        out["ABORTED"] = "C5 failed - a NEGATIVE age is a look-ahead"
        _write(args.json, out)
        return 3

    z = {c: zt(panel, c) for c in THEMES}
    deployed = composite(z, {c: W for c in THEMES})
    dates = sorted(panel["date"].unique())
    panel = panel.copy()
    panel["_deployed"] = deployed

    # ---- A1: the DIAGNOSTIC (no verdict, charges nothing) ----
    out["arms"]["A1_DIAGNOSTIC"] = diagnostic(panel, deployed, dsf, d13)

    # ---- the four verdict arms ----
    mult_f = decay(dsf, HL_FUND)
    mult_i = decay(d13, HL_13F)
    out["controls"]["C7_decay_bites"] = {
        "fund_multiplier": {"mean": float(mult_f.mean()), "min": float(mult_f.min()),
                            "p05": float(mult_f.quantile(0.05))},
        "inst_multiplier": {"mean": float(mult_i.mean()), "min": float(mult_i.min()),
                            "p05": float(mult_i.quantile(0.05))}}
    print(f"[C7] fund multiplier mean {mult_f.mean():.4f} p05 {mult_f.quantile(0.05):.4f}; "
          f"inst mean {mult_i.mean():.4f} p05 {mult_i.quantile(0.05):.4f}")

    z_a3 = {c: (z[c] * mult_f if c in FUND_THEMES else z[c]) for c in THEMES}
    z_a4 = {c: (z[c] * mult_i if c == "institutional" else z[c]) for c in THEMES}
    z_a5 = {c: (z[c] * mult_f if c in FUND_THEMES
                else z[c] * mult_i if c == "institutional" else z[c]) for c in THEMES}

    fresh = z_of(panel, -dsf)
    arms = {
        "A2_FRESHNESS_INPUT": composite({**z, "_fresh": fresh},
                                        {**{c: W for c in THEMES}, "_fresh": W}),
        "A3_FUND_DECAY_90D": composite(z_a3, {c: W for c in THEMES}),
        "A4_13F_DECAY_180D": composite(z_a4, {c: W for c in THEMES}),
        "A5_COMBINED": composite(z_a5, {c: W for c in THEMES}),
    }

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
        e["gate"] = gate(panel, deployed, sc, dates, name)
        print(f"[gate] {name:22s} {e['gate']['verdict']:15s} rank_corr "
              f"{e['rank_corr_vs_deployed']:.4f} cov {e['coverage']:.4f}")
        for h, s in e["gate"]["splits"].items():
            if "delta_top_decile_alpha" in s:
                print(f"          {h:11s} d_alpha {s['delta_top_decile_alpha']:+.4f}"
                      f"  d_t {s['delta_long_short_tstat']:+.4f}  improves {s['improves']}")

    out["controls"]["C2_identical_rows"] = {"ok": True, "n": int(len(panel))}
    _write(args.json, out)
    print(f"\n[f] wrote {args.json}")
    return 0


def diagnostic(panel, deployed, dsf, d13):
    """A1 — the audit's own method: top-decile forward return by staleness QUARTILE.

    No threshold, no verdict, charges no trial. C6 (the sector composition of each quartile) is
    reported here too, because a gradient that is really a sector bet is U7's failure mode.
    """
    res = {"note": "measurement only - no threshold, no verdict, charges no trial"}
    for tag, age in (("days_since_filing", dsf), ("days_since_13f", d13)):
        rows = []
        for d, idx in panel.groupby("date").groups.items():
            sub = panel.loc[idx]
            s, f = deployed.loc[idx], sub["fwd_ret"]
            m = s.notna() & f.notna()
            if m.sum() < 50:
                continue
            q = s[m].rank(pct=True)
            top = m[m].index[q >= 0.9]
            a = age.loc[top]
            if a.notna().sum() < 20:
                continue
            qs = pd.qcut(a.rank(method="first"), 4, labels=[1, 2, 3, 4])
            for lab in (1, 2, 3, 4):
                sel = top[(qs == lab).values]
                if len(sel):
                    rows.append({"q": int(lab),
                                 "ret": float(panel.loc[sel, "fwd_ret"].mean()),
                                 "age": float(age.loc[sel].mean()),
                                 "sectors": panel.loc[sel, "sector"].tolist()
                                 if "sector" in panel.columns else []})
        if not rows:
            res[tag] = {"status": "no data"}
            continue
        df = pd.DataFrame([{k: r[k] for k in ("q", "ret", "age")} for r in rows])
        g = df.groupby("q").agg(mean_ret=("ret", "mean"), mean_age=("age", "mean"),
                                n=("ret", "size"))
        res[tag] = {
            "by_quartile": {int(k): {"mean_fwd_ret": float(v["mean_ret"]),
                                     "mean_age_days": float(v["mean_age"]),
                                     "n_periods": int(v["n"])}
                            for k, v in g.iterrows()},
            "q1_minus_q4_ann": float((g.loc[1, "mean_ret"] - g.loc[4, "mean_ret"]) * 4.0),
            "monotone_fresh_better": bool(g["mean_ret"].is_monotonic_decreasing)}
        print(f"[A1 ] {tag}: " + "  ".join(
            f"Q{int(k)} {v['mean_ret']:+.4f}@{v['mean_age']:.0f}d" for k, v in g.iterrows())
            + f"   Q1-Q4 {res[tag]['q1_minus_q4_ann']:+.4f}/yr")

        # C6 — is the stale quartile a sector bet?
        if "sector" in panel.columns:
            from collections import Counter
            q1 = Counter(s for r in rows if r["q"] == 1 for s in r["sectors"] if s)
            q4 = Counter(s for r in rows if r["q"] == 4 for s in r["sectors"] if s)
            t1, t4 = sum(q1.values()) or 1, sum(q4.values()) or 1
            skew = {s: {"q1": q1.get(s, 0) / t1, "q4": q4.get(s, 0) / t4}
                    for s in set(q1) | set(q4)}
            worst = max(skew.items(), key=lambda kv: abs(kv[1]["q1"] - kv[1]["q4"]),
                        default=(None, None))
            res[tag]["C6_sector_skew"] = {"by_sector": skew,
                                          "largest_gap_sector": worst[0],
                                          "largest_gap": (abs(worst[1]["q1"] - worst[1]["q4"])
                                                          if worst[1] else None)}
            print(f"[C6 ] {tag}: largest fresh-vs-stale sector gap "
                  f"{worst[0]} {res[tag]['C6_sector_skew']['largest_gap']:.4f}")
    return res


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
