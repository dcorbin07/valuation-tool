#!/usr/bin/env python3
"""S16 — decompose net issuance. Executes `PREREG_s16_issuance_decomposition.md` unmodified.

ONE panel build, FIVE scorings, every arm a column on one frame so the row set is identical by
construction. The M&A map is read straight from ACTIONS here rather than through
`bulk.prepare_actions`: that loader's pickle has no acquisitions key, so adding one would make a
STALE cache yield an empty flag silently — a degenerate arm with no warning, which is exactly
what the COVERAGE RULE exists to stop.

Run:  python -m scripts.s16_issuance_decomposition --data-dir data/backtest
"""
from __future__ import annotations

import argparse
import bisect
import csv
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
MNA_WINDOW_DAYS = 365          # pre-committed with the register

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def load_mna(actions_csv):
    """{ticker: sorted [announcement dates]} for `acquisitionof` — the ACQUIRER's side.

    `acquisitionby` is the TARGET, which usually stops existing; the share issuance we are
    attributing happens at the acquirer, so only `acquisitionof` is loaded.
    """
    out = {}
    n = 0
    with open(actions_csv, newline="", encoding="utf-8", errors="replace") as fh:
        r = csv.DictReader(fh)
        for row in r:
            if (row.get("action") or "").lower() != "acquisitionof":
                continue
            t, d = row.get("ticker"), row.get("date")
            if not t or t == "N/A" or not d:
                continue
            out.setdefault(t, []).append(d)
            n += 1
    for t in out:
        out[t].sort()
    print(f"[mna] acquisitionof rows {n:,} over {len(out):,} acquirers")
    # C7's tripwire: a silently-empty map would make S16D degenerate and look like a null.
    assert n > 1000, f"only {n} acquisition rows - the ACTIONS join is broken, not merely thin"
    return out


def mna_flag(panel, mna):
    """PIT: an acquisition announced STRICTLY BEFORE as_of and within the trailing window.

    Strictly `<`, never `<=` — B26's same-day rule: an announcement dated as_of is not reliably
    public when the panel scores.
    """
    out = np.zeros(len(panel), dtype=bool)
    dates = panel["date"].astype(str).values
    tick = panel["ticker"].values
    for i in range(len(panel)):
        ds = mna.get(tick[i])
        if not ds:
            continue
        hi = dates[i][:10]
        lo = (pd.Timestamp(hi) - pd.Timedelta(days=MNA_WINDOW_DAYS)).strftime("%Y-%m-%d")
        j = bisect.bisect_left(ds, hi)          # strictly before as_of
        k = bisect.bisect_left(ds, lo)
        out[i] = j > k
    return pd.Series(out, index=panel.index)


def _z(df, s):
    """Cross-sectional z per date, through the SHIPPED standardizer."""
    out = pd.Series(np.nan, index=df.index, dtype=float)
    tmp = df[["date"]].copy()
    tmp["_v"] = s
    for d, idx in tmp.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(tmp.loc[idx, "_v"]), errors="coerce").values
    return out


def build_arms(panel, mna):
    net = pd.to_numeric(panel["share_issuance"], errors="coerce")
    have = net.notna()
    neg = -net
    buyback = net.where(have).clip(upper=0.0) * -1.0        # max(0, -net)
    dilution = net.where(have).clip(lower=0.0)              # max(0,  net)

    flag = mna_flag(panel, mna) & have
    mna_dil = dilution.where(flag, 0.0).where(have)
    org_dil = dilution.where(~flag, 0.0).where(have)

    arms = {
        "A0_INCUMBENT": _z(panel, neg),
        "S16A_BUYBACK_ONLY": _z(panel, buyback),
        "S16B_DILUTION_ONLY": _z(panel, -dilution),
        "S16C_TWO_INPUTS": pd.concat([_z(panel, buyback), _z(panel, -dilution)],
                                     axis=1).mean(axis=1, skipna=True),
        "S16D_MNA_SPLIT": pd.concat([_z(panel, buyback), _z(panel, -org_dil),
                                     _z(panel, -mna_dil)], axis=1).mean(axis=1, skipna=True),
    }
    comps = {"net": net, "neg_issuance": neg, "buyback": buyback, "dilution": dilution,
             "mna_dilution": mna_dil, "organic_dilution": org_dil, "mna_flag": flag}
    return arms, comps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--actions", default="data/bulk/actions.csv")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_s16.pkl")
    ap.add_argument("--json", default="data/free_analysis/S16_ISSUANCE.json")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        print(f"[s16] loading banked panel {args.panel_cache}")
        panel = pickle.load(open(args.panel_cache, "rb"))
    else:
        print("[s16] building the panel ONCE (with_issuance_raw=True)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        panel = FP.build_fundamental_panel(prov, prov.universe(None), rebalance_days=63,
                                           lookback_years=CFG.backtest_lookback_years,
                                           horizon=63, with_issuance_raw=True)
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        pickle.dump(panel, open(args.panel_cache, "wb"))
        print(f"[s16] banked {args.panel_cache}")

    print(f"[s16] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    # METHODOLOGY RULE: a verdict comes only from the full universe.
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, (
        f"SMOKE-TEST PANEL ({panel['date'].nunique()} dates, {panel['ticker'].nunique()} names)")

    out = {"n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
           "mna_window_days": MNA_WINDOW_DAYS, "controls": {}, "arms": {}}

    # ---- C1: reproduce the published record, or ABORT before any arm is read ----
    base = FP.quantile_backtest(panel, THEMES, {c: 0.125 for c in THEMES}, n_q=10, horizon=63)
    c1 = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(ok1), "measured": c1}
    print(f"[C1] reproduces record: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 failed - no arm read"
        _write(args.json, out)
        return 2

    mna = load_mna(args.actions)
    arms, comps = build_arms(panel, mna)

    # ---- C5: the identity, or it is not a decomposition ----
    ident = (comps["buyback"] - comps["dilution"] - comps["neg_issuance"]).abs().max()
    out["controls"]["C5_identity"] = {"max_abs_dev": float(ident), "ok": bool(ident < 1e-12)}
    print(f"[C5] buyback - dilution == neg_issuance: max|dev| {ident:.3e}")

    # ---- C6 coverage first, and the degeneracy rule fixed in advance ----
    n = len(panel)
    for k in ("buyback", "dilution", "mna_dilution", "organic_dilution"):
        v = comps[k]
        nz = float((v.fillna(0) != 0).mean())
        out["controls"].setdefault("C6_component_coverage", {})[k] = {
            "non_null": float(v.notna().mean()), "non_zero": nz,
            "DEGENERATE": bool(nz < 0.10)}
        print(f"[C6] {k:18s} non-null {v.notna().mean():.4f}  non-zero {nz:.4f}"
              f"{'   <-- DEGENERATE' if nz < 0.10 else ''}")

    # ---- C7: the M&A flag is not vacuous ----
    dil_rows = comps["dilution"].fillna(0) > 0
    rate = float((comps["mna_flag"] & dil_rows).sum() / max(1, int(dil_rows.sum())))
    out["controls"]["C7_mna_flag"] = {
        "fires_on_dilution_rows": rate, "n_dilution_rows": int(dil_rows.sum()),
        "overall_rate": float(comps["mna_flag"].mean()),
        "FLAGGED_THIN": bool(rate < 0.01)}
    print(f"[C7] M&A flag fires on {rate:.4f} of dilution rows "
          f"({int((comps['mna_flag'] & dil_rows).sum()):,} of {int(dil_rows.sum()):,})")

    # ---- C3: rebuilt incumbent vs the shipped column ----
    if "capital_discipline" in panel.columns:
        sh = pd.to_numeric(panel["capital_discipline"], errors="coerce")
        both = sh.notna() & arms["A0_INCUMBENT"].notna()
        dev = float((sh[both] - arms["A0_INCUMBENT"][both]).abs().max()) if both.any() else None
        out["controls"]["C3_incumbent_matches_shipped"] = {
            "max_abs_dev": dev, "n": int(both.sum()), "ok": bool(dev is not None and dev < 1e-9)}
        print(f"[C3] rebuilt incumbent vs shipped: max|dev| {dev}  over {int(both.sum()):,} rows")

    # ---- per-component IC: DIAGNOSTIC ONLY, may never carry a verdict ----
    for name, col in arms.items():
        ics = []
        for d, idx in panel.groupby("date").groups.items():
            sub = panel.loc[idx]
            m = col.loc[idx].notna() & sub["fwd_ret"].notna()
            if m.sum() > 30 and col.loc[idx][m].nunique() > 1:
                ics.append(col.loc[idx][m].corr(sub["fwd_ret"][m], method="spearman"))
        ics = [x for x in ics if x == x]
        e = out["arms"].setdefault(name, {})
        e["coverage"] = float(col.notna().mean())
        e["sd_per_date"] = float(panel.assign(_v=col).groupby("date")["_v"].std().mean())
        if ics:
            t = float(np.mean(ics) / (np.std(ics, ddof=1) / math.sqrt(len(ics))))
            e["theme_ic"] = {"median": float(np.median(ics)), "t": t,
                             "clears_x7_2.71": bool(t > 2.71)}
            print(f"[IC ] {name:20s} median {np.median(ics):+.5f}  t {t:+.4f}  "
                  f"cov {col.notna().mean():.4f}")

    # ---- C4 + THE GATE ----
    pa = panel.copy()
    pa["capital_discipline"] = arms["A0_INCUMBENT"]
    for name, col in arms.items():
        if name == "A0_INCUMBENT":
            continue
        rc = []
        for d, idx in panel.groupby("date").groups.items():
            a, b = arms["A0_INCUMBENT"].loc[idx], col.loc[idx]
            m = a.notna() & b.notna()
            if m.sum() > 30:
                rc.append(a[m].rank().corr(b[m].rank()))
        out["arms"][name]["rank_corr_vs_incumbent"] = float(np.mean(rc)) if rc else None

        pb = panel.copy()
        pb["capital_discipline"] = col
        g = FP.holdout_compare_panels(pa, pb, THEMES, label_a="incumbent", label_b=name)
        out["arms"][name]["gate"] = g
        print(f"[gate] {name:20s} verdict {g.get('verdict')}   "
              f"rank_corr {out['arms'][name]['rank_corr_vs_incumbent']:.4f}")
        for half, d in (g.get("splits") or {}).items():
            da, dt = d.get("delta_top_decile_alpha"), d.get("delta_long_short_tstat")
            print(f"          {half:11s} d_alpha {da if da is None else f'{da:+.4f}'}"
                  f"   d_t {dt if dt is None else f'{dt:+.4f}'}"
                  f"   improves {d.get('improves')}")

    out["controls"]["C2_identical_rows"] = {"ok": True, "n": n}
    _write(args.json, out)
    print(f"\n[s16] wrote {args.json}")
    return 0


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
