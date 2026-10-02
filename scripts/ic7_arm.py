# -*- coding: utf-8 -*-
"""IC7 pass 1 — the arm. 1 EQUITY TRIAL, booked at 1a0acbb before this file existed.

`PREREG_ic7_coverage_renormalisation.md` at `df619d8` is a strict git ancestor of this commit,
and this script REFUSES to run without a passing kills artifact, so the five free kills were
computed AND READ in their own pass (`O10`'s process defect, not repeated).

ONE PANEL, TWO SCORINGS. The arm differs from the incumbent in the imputation alone, so the row
set is provably identical and a difference cannot be a difference of rows.

THE GATE IS THE SHIPPED `holdout_compare_panels`, VERBATIM. Its own defaults
(`min_alpha_gain=0.01`, `min_tstat_gain=0.25`) ARE the registered margins and are passed
explicitly so a future change to the defaults cannot silently re-bar this result.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

EQUITY_N = 252
MARGIN_ALPHA = 0.01          # +100 bps -- SECTOR-NEUTRAL-B6, verbatim
MARGIN_TSTAT = 0.25          # +0.25 t  -- SECTOR-NEUTRAL-B6, verbatim


def _data_root():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(_HERE, "data"))
    parts = _HERE.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    for c in out:
        if os.path.exists(os.path.join(c, "free_analysis", "panel_corrected_69d.pkl")):
            return c
    raise FileNotFoundError("no data root; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
KILLS = os.path.join(FA, "IC7_KILLS.json")
OUT = os.path.join(FA, "IC7_ARM.json")
ROWS = os.path.join(FA, "IC7_ARM_ROWS.pkl")


def impute_panel(panel, weighted):
    """The arm: fill a missing weighted theme with the date's OWN cross-sectional median.

    K5 by construction -- the fill reads only rows sharing the same `date`, so it cannot reach
    a later one. A theme wholly absent on a date has no median to take, and is filled with 0.0
    (the z-scale's own centre), which is the same assumption stated one level down.
    """
    out = panel.copy()
    filled = 0
    for c in weighted:
        med = out.groupby("date")[c].transform("median")
        miss = out[c].isna()
        filled += int(miss.sum())
        out[c] = out[c].where(~miss, med.where(med.notna(), 0.0))
    return out, filled


def _hac(x, lag=1):
    x = np.asarray([v for v in x if v == v], dtype=float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    m = float(x.mean())
    e = x - m
    s = float(np.dot(e, e) / n)
    for L in range(1, lag + 1):
        if L < n:
            s += 2.0 * (1.0 - L / (lag + 1.0)) * float(np.dot(e[L:], e[:-L]) / n)
    se = float(np.sqrt(max(s, 1e-30) / n))
    return m, se, (m / se if se > 0 else float("nan"))


def main() -> int:
    if not os.path.exists(KILLS):
        raise SystemExit(
            "REFUSING: no kills artifact at %s. The five free kills must be computed AND READ "
            "in their own pass before the arm is scored. Run scripts/ic7_kills.py." % KILLS)
    with open(KILLS, encoding="utf-8") as fh:
        k = json.load(fh)
    if k.get("any_kill_fired"):
        raise SystemExit("REFUSING: a kill fired (%r); the arm does not run."
                         % (k["any_kill_fired"],))

    import valuation.screener.settings as S
    from valuation.edge.fundamental_panel import (holdout_compare_panels, quantile_backtest,
                                                  composite_from_frame)
    from valuation.screener.cross_sectional import zscore

    # SECTOR-NEUTRAL-B6's OWN two column sets, IMPORTED rather than retyped (`B7`, `MA5`).
    # A FIRST CUT OF THIS SCRIPT BUILT ITS OWN "flat" AND IT WAS VACUOUS: WEIGHTS_ESTABLISHED
    # is already flat 1/7 after renormalisation, so "deployed" and "flat" returned IDENTICAL
    # numbers -- a second weighting that cannot differ is not a second check. W-1's K4 fired on
    # exactly this (nine bucket themes scored at a seven-theme weight) and its fix was to import
    # these constants; this is that fix applied one item later.
    from scripts.sector_neutral_rerun import DEPLOYED, FLAT, BASE_WEIGHT
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    weighted = [c for c in DEPLOYED if c in panel.columns]
    cols = [c for c in S.FACTORS_ALL if c in panel.columns]
    # AND THE WEIGHTING IS THE COLUMN SET, NOT A DICT. `holdout_compare_panels`'s fourth
    # positional parameter is `label_a`, NOT weights -- it builds the composite from `cols` at
    # `base_weight`. A first cut passed a weights dict there, so it landed in the LABEL slot
    # (visible in the artifact as `"label_a": {"value": 0.125, ...}`) and BOTH scorings used the
    # same `cols` -- every column of FACTORS_ALL present in the panel, which includes `growth`
    # and `low_risk`. So both runs scored a NINE-theme composite when the deployed one is SEVEN
    # and returned identical numbers for what were supposed to be two different weightings.
    # That is `W-1`'s K4 defect and `MA28`'s C1 before it, in a third costume, and the identical
    # numbers are what exposed it.
    assert list(DEPLOYED) != list(FLAT), "the two column sets are identical -- vacuous"
    dep_cols = [c for c in DEPLOYED if c in panel.columns]
    flat_cols = [c for c in FLAT if c in panel.columns]
    assert len(dep_cols) == 7 and len(flat_cols) == 9, (dep_cols, flat_cols)

    arm, filled = impute_panel(panel, weighted)
    out = {"item": "IC7", "pass": "1 arm", "trials": 1,
           "register": "PREREG_ic7_coverage_renormalisation.md @ df619d8",
           "trials_booked_at": "1a0acbb (before this runner existed)",
           "equity_n": EQUITY_N,
           "gate": {"min_alpha_gain": MARGIN_ALPHA, "min_tstat_gain": MARGIN_TSTAT,
                    "source": "SECTOR-NEUTRAL-B6, reused verbatim", "both_halves": True},
           "uncalibrated": ("V2G and R1-VAR: no calibrated floor exists for a paired "
                            "within-panel difference; X7 calibrates LEVELS"),
           "kills_read_first": True,
           "cells_imputed": filled,
           "rows": int(len(panel)),
           "share_of_cells_imputed": filled / float(len(panel) * len(weighted))}

    # ---- C: the row set is identical and only the imputation differs
    out["C_identical_rows"] = {
        "same_shape": bool(arm.shape == panel.shape),
        "same_keys": bool((arm["date"].values == panel["date"].values).all()
                          and (arm["ticker"].values == panel["ticker"].values).all()),
        "untouched_themes_bit_identical": {
            c: bool(np.array_equal(arm[c].values, panel[c].values, equal_nan=True))
            for c in ("value", "size")}}

    # ---- the gate, both weightings
    for label, cset in (("deployed", dep_cols), ("flat", flat_cols)):
        out[label] = holdout_compare_panels(
            panel, arm, cset, label_a="incumbent", label_b="imputed",
            horizon=63, base_weight=BASE_WEIGHT,
            min_alpha_gain=MARGIN_ALPHA, min_tstat_gain=MARGIN_TSTAT)
    assert out["deployed"]["splits"] != out["flat"]["splits"], (
        "the two weightings returned identical splits -- the second is vacuous")

    # ---- levels and the paired difference, per period
    def series(p, w):
        o = []
        for d, g in p.groupby("date"):
            q = quantile_backtest(g.assign(_x=1), cols, w, n_q=10, horizon=63,
                                  return_series=True)
            o.append(q)
        return o

    # per-date top-decile alpha from the shipped primitive, for the paired se
    def per_date_alpha(p, w):
        vals = []
        for d, g in p.groupby("date"):
            c = composite_from_frame(g, list(w), w, zscore)
            fr = g["fwd_ret"].values
            ok = np.isfinite(c) & np.isfinite(fr)
            if int(ok.sum()) < 30:
                continue
            cc, ff = c[ok], fr[ok]
            k = max(1, int(len(cc) * 0.10))
            top = np.argsort(-cc)[:k]
            vals.append((str(d), float(ff[top].mean() - ff.mean())))
        return vals

    _dep_w = {c: BASE_WEIGHT for c in dep_cols}
    a_inc = per_date_alpha(panel, _dep_w)
    a_arm = per_date_alpha(arm, _dep_w)
    m = {d: v for d, v in a_inc}
    pairs = [(d, v - m[d]) for d, v in a_arm if d in m]
    diff = [v for _, v in pairs]
    mean, se, tt = _hac(diff)
    crit_h = __import__("valuation.edge.power_gate", fromlist=["x"]).critical_value(
        n_trials=EQUITY_N)
    out["paired"] = {
        "n": len(diff), "mean_per_period": mean, "hac_se": se, "hac_t": tt,
        "mean_ann_pp": mean * 4.0 * 100.0,
        "mde_50_ann_pp": 2.0 * se * 4.0 * 100.0,
        "mde_80_ann_pp": (2.0 + 0.84) * se * 4.0 * 100.0,
        "mde_80_at_hurdle_ann_pp": (crit_h + 0.84) * se * 4.0 * 100.0,
        "hurdle": crit_h,
        "note": "UNCALIBRATED critical values; the se is MEASURED on this arm (MB8)"}

    # ---- how much does the ranking actually move?
    rhos, overlaps = [], []
    for d, g in panel.groupby("date"):
        ga = arm[arm["date"] == d]
        c1 = pd.Series(composite_from_frame(g, dep_cols, _dep_w, zscore),
                       index=g["ticker"].values)
        c2 = pd.Series(composite_from_frame(ga, dep_cols, _dep_w, zscore),
                       index=ga["ticker"].values)
        j = c1.index.intersection(c2.index)
        if len(j) < 30:
            continue
        rhos.append(float(c1[j].corr(c2[j], method="spearman")))
        k = max(1, int(len(j) * 0.10))
        overlaps.append(len(set(c1[j].nlargest(k).index) & set(c2[j].nlargest(k).index)) / k)
    out["movement"] = {"per_date_spearman_median": float(np.median(rhos)),
                       "per_date_spearman_min": float(np.min(rhos)),
                       "top_decile_overlap_median": float(np.median(overlaps))}

    pd.to_pickle({"paired": pairs, "incumbent": a_inc, "arm": a_arm}, ROWS)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    print("cells imputed: %d (%.4f of weighted cells)"
          % (filled, out["share_of_cells_imputed"]))
    print("ranking movement: per-date spearman median %.6f (min %.6f), top-decile overlap %.4f"
          % (out["movement"]["per_date_spearman_median"],
             out["movement"]["per_date_spearman_min"],
             out["movement"]["top_decile_overlap_median"]))
    for label in ("deployed", "flat"):
        v = out[label]
        print("\n%s: verdict %s" % (label.upper(), v.get("verdict")))
        for half in ("early_half", "late_half"):
            h = (v.get("splits") or {}).get(half) or {}
            print("   %-11s n %s  dAlpha %+.6f (%+.4fpp)  dt %+.6f"
                  % (half, h.get("n_dates"), h.get("delta_top_decile_alpha", float("nan")),
                     100 * (h.get("delta_top_decile_alpha") or 0.0),
                     h.get("delta_long_short_tstat", float("nan"))))
    p = out["paired"]
    print("\npaired: n %d  mean %+.6f/period (%+.4fpp ann)  HAC t %+.4f"
          % (p["n"], p["mean_per_period"], p["mean_ann_pp"], p["hac_t"]))
    print("        MDE80 %.4fpp (crit 2.0) / %.4fpp (hurdle %.4f)  -- UNCALIBRATED"
          % (p["mde_80_ann_pp"], p["mde_80_at_hurdle_ann_pp"], p["hurdle"]))
    print("\nwrote", OUT, "and", ROWS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
