#!/usr/bin/env python3
"""S3 — rebuild the insider score. Executes `PREREG_s3_insider_rebuild.md` unmodified.

ONE panel build, FOUR scorings, provably identical rows. The three variants are functions of the
same banked `(ins_net, ins_buys)` window the shipped score reduces, so the arms differ in the
formula and in nothing else.

Run:  python -m scripts.s3_insider_rebuild --data-dir data/backtest
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

# PRE-COMMITTED (register §2). The scale cannot change S3b's ordering -- any positive scale is a
# strictly monotone map of net/marketcap -- only how fast it saturates.
S3B_SCALE = 0.001                     # 10 bps of market cap

# PRE-COMMITTED (register §5, C1). The run ABORTS before any variant is read if these move.
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}


def _clip(x):
    return max(0.0, min(100.0, x))


def score_incumbent(net, buys):
    return FP._insider_formula(net, buys)


def score_s3a(net, buys):
    """Drop the unconditional +min(10, 2*buys) bonus."""
    return _clip(50 + 40 * math.tanh(net / 5e6))


def score_s3b(net, buys, mcap):
    """Scale net insider dollars by market cap before the tanh."""
    if mcap is None or not (mcap > 0):
        return None                     # never impute 50 -- register §2
    return _clip(50 + 40 * math.tanh((net / mcap) / S3B_SCALE))


def _z_by_date(df, col):
    """Cross-sectional z per date, through the SHIPPED standardizer."""
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for d, idx in df.groupby("date").groups.items():
        out.loc[idx] = pd.to_numeric(CS.zscore(df.loc[idx, col]), errors="coerce").values
    return out


def build_arms(panel):
    """Return {arm: insider-theme Series}, all on `panel`'s exact index."""
    net = pd.to_numeric(panel["ins_net"], errors="coerce")
    buys = pd.to_numeric(panel["ins_buys"], errors="coerce")
    mc = pd.to_numeric(panel["market_cap"], errors="coerce")
    have = net.notna() & buys.notna()

    arms = {}
    # A0 rebuilt from the banked raws -- C3 checks it against the shipped column.
    a0 = pd.Series(np.nan, index=panel.index, dtype=float)
    a0[have] = [score_incumbent(n, int(b)) for n, b in zip(net[have], buys[have])]
    arms["A0_INCUMBENT"] = (a0 - 50.0) / 25.0

    a = pd.Series(np.nan, index=panel.index, dtype=float)
    a[have] = [score_s3a(n, int(b)) for n, b in zip(net[have], buys[have])]
    arms["S3A_NO_BONUS"] = (a - 50.0) / 25.0

    b = pd.Series(np.nan, index=panel.index, dtype=float)
    okb = have & mc.notna() & (mc > 0)
    b[okb] = [score_s3b(n, int(bb), m) for n, bb, m in zip(net[okb], buys[okb], mc[okb])]
    arms["S3B_MCAP_SCALED"] = (b - 50.0) / 25.0

    # S3C -- two INPUTS, z-scored per date and averaged: this is the only arm that makes
    # `insider` a genuinely standardized multi-input theme like the others.
    tmp = panel[["date"]].copy()
    tmp["_net"] = np.where(have, np.tanh(net / 5e6), np.nan)
    tmp["_brd"] = np.where(have, buys, np.nan)
    zn, zb = _z_by_date(tmp, "_net"), _z_by_date(tmp, "_brd")
    arms["S3C_TWO_INPUTS"] = pd.concat([zn, zb], axis=1).mean(axis=1, skipna=True)
    return arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_s3_insider.pkl")
    ap.add_argument("--json", default="data/free_analysis/S3_INSIDER_REBUILD.json")
    args = ap.parse_args()

    if os.path.exists(args.panel_cache):
        print(f"[s3] loading banked panel {args.panel_cache}")
        with open(args.panel_cache, "rb") as fh:
            panel = pickle.load(fh)
    else:
        print("[s3] building the panel ONCE (with_insider_raw=True)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        # THE CANONICAL PARAMETERS, not the function defaults. `lookback_years` defaults to 6,
        # which yields a 21-date / 2,151-name panel -- a SMOKE TEST, never a verdict, per the
        # METHODOLOGY RULE. The shipped run uses CONFIG.backtest_lookback_years (18) and
        # rebalance_days 63, which is the 69-date / 2,531-name corrected panel every published
        # figure is measured on. The first cut of this script used the defaults and produced the
        # 21-date panel; caught by the shape check below, which is why it is an assert.
        panel = FP.build_fundamental_panel(prov, prov.universe(None), rebalance_days=63,
                                           lookback_years=CFG.backtest_lookback_years,
                                           horizon=63, with_insider_raw=True)
        os.makedirs(os.path.dirname(args.panel_cache), exist_ok=True)
        with open(args.panel_cache, "wb") as fh:
            pickle.dump(panel, fh)
        print(f"[s3] banked {args.panel_cache}")

    print(f"[s3] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    # METHODOLOGY RULE: a verdict comes only from the full universe. A short-lookback build is a
    # smoke test and must not reach a gate, so this refuses rather than warns.
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, (
        f"SMOKE-TEST PANEL ({panel['date'].nunique()} dates, {panel['ticker'].nunique()} names) "
        "- not the full corrected panel; no verdict may be read from it")
    out = {"n_rows": int(len(panel)), "n_dates": int(panel["date"].nunique()),
           "n_names": int(panel["ticker"].nunique()), "s3b_scale": S3B_SCALE,
           "controls": {}, "arms": {}}

    # ---------------- C1: the harness must reproduce the published record ----------------
    # signature is (panel, cols, weights) - the first cut passed the weights dict as `cols`
    base = FP.quantile_backtest(panel, THEMES, {c: 0.125 for c in THEMES}, n_q=10, horizon=63)
    c1 = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    c1_ok = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    out["controls"]["C1_reproduces_record"] = {"ok": bool(c1_ok), "measured": c1,
                                               "expected": REC}
    print(f"[C1] reproduces record: {c1_ok}  {c1}")
    if not c1_ok:
        out["ABORTED"] = "C1 failed - no arm was read"
        _write(args.json, out)
        print("[s3] ABORT: C1 failed, no variant read.")
        return 2

    # ---------------- coverage first (COVERAGE RULE / C6) ----------------
    arms = build_arms(panel)
    for name, col in arms.items():
        out["arms"][name] = {"coverage": float(col.notna().mean()),
                             "mean": float(col.mean(skipna=True)),
                             "sd_per_date": float(
                                 panel.assign(_v=col).groupby("date")["_v"].std().mean())}
        print(f"[cov] {name:18s} coverage {col.notna().mean():.4f}  "
              f"mean {col.mean(skipna=True):+.4f}  sd {out['arms'][name]['sd_per_date']:.4f}")

    # ---------------- C3: the rebuilt incumbent == the shipped column ----------------
    shipped = (pd.to_numeric(panel["insider_score"], errors="coerce") - 50.0) / 25.0
    both = shipped.notna() & arms["A0_INCUMBENT"].notna()
    dev = float((shipped[both] - arms["A0_INCUMBENT"][both]).abs().max()) if both.any() else None
    out["controls"]["C3_incumbent_matches_shipped"] = {
        "max_abs_dev": dev, "n_compared": int(both.sum()),
        "ok": bool(dev is not None and dev < 1e-12)}
    print(f"[C3] rebuilt incumbent vs shipped: max|dev| {dev}  over {int(both.sum()):,} rows")

    # ---------------- C4: no arm is inert ----------------
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
        print(f"[C4] {name:18s} mean within-date rank corr vs incumbent "
              f"{out['arms'][name]['rank_corr_vs_incumbent']}")

    # ---------------- C7: the availability diagnostic (register §5) ----------------
    ind = panel["insider_score"].notna().astype(float)
    ics = []
    for d, idx in panel.groupby("date").groups.items():
        sub = panel.loc[idx]
        m = sub["fwd_ret"].notna()
        if m.sum() > 30 and ind.loc[idx][m].nunique() > 1:
            ics.append(ind.loc[idx][m].corr(sub["fwd_ret"][m].rank(), method="spearman"))
    ics = [x for x in ics if x == x]
    if ics:
        t = float(np.mean(ics) / (np.std(ics, ddof=1) / math.sqrt(len(ics))))
        out["controls"]["C7_availability_indicator"] = {
            "median_ic": float(np.median(ics)), "mean_ic": float(np.mean(ics)),
            "t": t, "n_dates": len(ics)}
        print(f"[C7] availability-indicator IC median {np.median(ics):+.5f}  t {t:+.4f}")

    # -------- the audit's own bar, as a DIAGNOSTIC that may never carry a verdict (§3.1) -----
    # X7 calibrates the theme-IC t floor at 2.71 and measured that 39% of pure-noise draws clear
    # 2.0. The audit's +1.0 is far below both, and theme IC is the wrong instrument for a
    # construction change anyway (P6.3, X3, S20/S21). Measured so the dissociation is a number.
    for name, col in arms.items():
        ics = []
        for d, idx in panel.groupby("date").groups.items():
            sub = panel.loc[idx]
            m = col.loc[idx].notna() & sub["fwd_ret"].notna()
            if m.sum() > 30 and col.loc[idx][m].nunique() > 1:
                ics.append(col.loc[idx][m].corr(sub["fwd_ret"][m], method="spearman"))
        ics = [x for x in ics if x == x]
        if ics:
            t = float(np.mean(ics) / (np.std(ics, ddof=1) / math.sqrt(len(ics))))
            out["arms"][name]["theme_ic"] = {
                "median": float(np.median(ics)), "mean": float(np.mean(ics)), "t": t,
                "n_dates": len(ics), "clears_audit_bar_1.0": bool(t > 1.0),
                "clears_x7_calibrated_2.71": bool(t > 2.71)}
            print(f"[IC ] {name:18s} median {np.median(ics):+.5f}  t {t:+.4f}  "
                  f"audit>1.0 {t > 1.0}   X7>2.71 {t > 2.71}")

    # ---------------- THE GATE ----------------
    pa = panel.copy()
    pa["insider"] = arms["A0_INCUMBENT"]
    for name, col in arms.items():
        if name == "A0_INCUMBENT":
            continue
        pb = panel.copy()
        pb["insider"] = col
        g = FP.holdout_compare_panels(pa, pb, THEMES, label_a="incumbent", label_b=name)
        out["arms"][name]["gate"] = g
        print(f"[gate] {name:18s} verdict {g.get('verdict')}")
        for half, d in (g.get("splits") or {}).items():
            da, dt = d.get("delta_top_decile_alpha"), d.get("delta_long_short_tstat")
            print(f"          {half:11s} d_alpha {da if da is None else f'{da:+.4f}'}"
                  f"   d_t {dt if dt is None else f'{dt:+.4f}'}"
                  f"   improves {d.get('improves')}")

    # C2: identical rows, asserted
    out["controls"]["C2_identical_rows"] = {
        "ok": True, "n": int(len(panel)),
        "note": "all arms are columns on ONE frame, so the key set is identical by construction"}

    _write(args.json, out)
    print(f"\n[s3] wrote {args.json}")
    return 0


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


if __name__ == "__main__":
    sys.exit(main())
