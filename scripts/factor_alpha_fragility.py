#!/usr/bin/env python3
"""factor_alpha_fragility.py — try to break R1's +8.81%/yr.  [R1 fragility]

Part I of R1 found an FF5+MOM intercept of +8.81%/yr (NW(1) t +5.742) on the top-decile-minus
equal-weight spread. That result was produced BEFORE two Part I audit corrections that change
its own inputs:

  B6  the panel's first ~37 of 110 periods contain only names that stopped trading by roughly
      2019 -- an inverted universe, so part of the intercept is estimated on uninterpretable
      cross-sections.
  B7  the top-decile series comes from the MEASUREMENT composite, which does not renormalise
      for missing themes; B7 collapses three composites into one, so the object R1 measured is
      about to change.

Neither invalidates R1. Both mean R1 is PROVISIONAL until re-run. This script measures how
fragile it is, using only the already-exported series and the already-fetched factor data.

Criteria are pre-committed in HANDOFF_r1.md section 6 and are NOT restated from results:
FRAGILE if the alpha loses t > 2.0 on the stable-universe window, or flips sign in either half,
or >50% of the total alpha comes from the best 5 periods, or it survives only one factor model.

Modifies no existing file. Imports Part I's machinery rather than re-deriving it, so the two
parts cannot drift apart.

    python -m scripts.factor_alpha_fragility
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from scripts.factor_alpha import (ols_nw, regress, factor_windows, decile_series,
                                  PPY, FF_MODEL, Q4_MODEL, Q5_MODEL, STRAT)

# Pre-committed in HANDOFF_r1.md 6a, before any cut was run.
STABLE_FROM = "2008-01-01"
CONCENTRATION_LIMIT = 0.50          # >50% of alpha from the best 5 periods trips the criterion
T_BAR = 2.0

CAPM = ["MKT"]
FF3 = ["MKT", "SMB", "HML"]
FF5_NO_MOM = ["MKT", "SMB", "HML", "RMW", "CMA"]

# name -> (columns, which factor family) ; "q" frames swap in the global-q market factor
MODELS = {
    "CAPM": (CAPM, "ff"),
    "FF3": (FF3, "ff"),
    "FF5 (no momentum)": (FF5_NO_MOM, "ff"),
    "FF5+MOM": (FF_MODEL, "ff"),
    "q4": (Q4_MODEL, "q"),
    "q5": (Q5_MODEL, "q"),
}


def _pct(x, p=2):
    return "n/a" if x is None or x != x else f"{x * 100:+.{p}f}%"


def build_frames(panel_path, strat_path):
    """The Part I object, plus the two factor frames. Nothing new is estimated here."""
    from valuation.screener import settings as S

    panel = pd.read_pickle(panel_path)
    panel["date"] = pd.to_datetime(panel["date"])
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}
    strat = decile_series(panel, dep)

    # same assertion Part I makes: this must be the SAME object the headline is
    shipped = pd.read_csv(strat_path, parse_dates=["date"]).set_index("date")
    j = strat.join(shipped[["top", "ew"]], rsuffix="_x4", how="inner")
    assert len(j) == len(shipped), "did not line up with X4's shipped series"
    assert float(np.max(np.abs(j["top"] - j["top_x4"]))) < 1e-9, "not X4's series"

    fac = factor_windows(list(strat.index), how="compound")
    ff = strat.join(fac, how="inner").dropna(subset=FF_MODEL + ["RF"])
    q = strat.join(fac, how="inner").dropna(subset=["qMKT_x", "ME", "IA", "ROE", "EG"])
    q = q.assign(MKT=q["qMKT_x"]).drop(columns=["qMKT_x"])
    return strat, ff, q, dep


def _y(d):
    """The headline object: top decile minus the equal-weighted universe."""
    return (d["top"] - d["ew"]).values


def _fit(d, cols, lag=1):
    return regress(_y(d), d, cols, "top_minus_ew", lag=lag)


# --------------------------------------------------------------------- 6. overlap check
def overlap_check(strat, ff):
    """Are the 63-day windows genuinely non-overlapping on the grid actually used?

    The panel sets rebalance_days == horizon == 63, so window i is (d_i, d_i+1] and the next
    window starts where this one ends. That is the CLAIM. This measures it: every window must
    contain exactly 63 factor trading days, the grid must be strictly increasing with no
    duplicates, and consecutive windows must share no day.
    """
    g = pd.DatetimeIndex(sorted(strat.index))
    nd = ff["n_days"].values
    ends = pd.DatetimeIndex(ff["end"].values)
    starts = pd.DatetimeIndex(ff.index)
    # window i is (start_i, end_i]; non-overlap <=> end_i <= start_{i+1} for all i
    shares_a_day = int(np.sum(ends[:-1] > starts[1:]))
    return {
        "n_grid_dates": int(len(g)),
        "grid_strictly_increasing": bool((np.diff(g.values.astype("int64")) > 0).all()),
        "grid_has_duplicates": bool(len(g) != len(set(g))),
        "n_windows": int(len(ff)),
        "window_days_min": int(nd.min()), "window_days_max": int(nd.max()),
        "all_windows_exactly_63_days": bool(nd.min() == 63 and nd.max() == 63),
        "consecutive_windows_sharing_a_day": shares_a_day,
        "windows_are_non_overlapping": bool(shares_a_day == 0),
        "end_equals_next_start": bool(np.array_equal(ends[:-1].values, starts[1:].values)),
    }


# --------------------------------------------------------------------- 3. concentration
def concentration(d, cols, lag=1):
    """Per-period alpha contribution a_t = y_t - beta*f_t; these sum to n * alpha.

    Definition fixed in HANDOFF_r1.md 6a before running. Reports the share of total alpha from
    the best 1/3/5 periods, then re-estimates the regression with those periods removed, and
    -- for the asymmetry, which is the informative part -- with the WORST 5 removed.
    """
    y = _y(d)
    base = regress(y, d, cols, "base", lag=lag)
    beta = np.array([base["loadings"][c]["beta"] for c in cols])
    a_t = y - d[cols].values @ beta                     # = alpha + residual_t
    total = float(a_t.sum())
    order = np.argsort(-a_t)                            # best first

    out = {"total_alpha_sum": total,
           "alpha_ann_full": base["alpha_ann"], "t_full": base["alpha_t_nw"],
           "n_full": base["n_periods"], "share_from_best": {}, "drop_best": {},
           "per_period_alpha_ann_top5": [float(a_t[i] * PPY) for i in order[:5]],
           "top5_dates": [str(pd.Timestamp(d.index[i]).date()) for i in order[:5]]}

    for k in (1, 3, 5):
        out["share_from_best"][f"best_{k}"] = float(a_t[order[:k]].sum() / total) if total else None
        keep = np.ones(len(y), dtype=bool)
        keep[order[:k]] = False
        r = regress(y[keep], d[keep], cols, f"drop_best_{k}", lag=lag)
        out["drop_best"][f"drop_best_{k}"] = {"alpha_ann": r["alpha_ann"],
                                              "t_nw": r["alpha_t_nw"], "n": r["n_periods"]}

    keep = np.ones(len(y), dtype=bool)
    keep[order[-5:]] = False                            # worst 5
    r = regress(y[keep], d[keep], cols, "drop_worst_5", lag=lag)
    out["drop_worst_5"] = {"alpha_ann": r["alpha_ann"], "t_nw": r["alpha_t_nw"],
                           "n": r["n_periods"]}
    out["worst5_dates"] = [str(pd.Timestamp(d.index[i]).date()) for i in order[-5:]]
    out["per_period_alpha_ann_worst5"] = [float(a_t[i] * PPY) for i in order[-5:]]
    return out


# --------------------------------------------------------------------- 5. rolling alpha
def rolling_alpha(d, cols, window=40, lag=1):
    """Rolling-window intercept, so decay or a single regime is visible, not averaged away.

    40 periods is ~10 years of quarterly rebalances -- the shortest window that still leaves
    a sane number of degrees of freedom against a 6-factor model (40 obs, 7 parameters).
    """
    y = _y(d)
    rows = []
    for i in range(len(y) - window + 1):
        sl = slice(i, i + window)
        r = regress(y[sl], d.iloc[sl], cols, "roll", lag=lag)
        rows.append({"start": str(pd.Timestamp(d.index[i]).date()),
                     "end": str(pd.Timestamp(d.index[i + window - 1]).date()),
                     "alpha_ann": r["alpha_ann"], "t_nw": r["alpha_t_nw"]})
    a = np.array([r["alpha_ann"] for r in rows])
    t = np.array([r["t_nw"] for r in rows])
    return {"window_periods": window, "n_windows": len(rows),
            "alpha_min": float(a.min()), "alpha_max": float(a.max()),
            "alpha_median": float(np.median(a)),
            "share_positive": float((a > 0).mean()),
            "share_t_over_2": float((t > T_BAR).mean()),
            "min_alpha_window": rows[int(np.argmin(a))],
            "max_alpha_window": rows[int(np.argmax(a))],
            "series": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R1 fragility.")
    ap.add_argument("--panel", default="data/free_analysis/panel.pkl")
    ap.add_argument("--strategy-series", default=STRAT)
    ap.add_argument("--json", default="data/free_analysis/FACTOR_ALPHA_FRAGILITY.json")
    ap.add_argument("--lag", type=int, default=1)
    args = ap.parse_args(argv)

    strat, ff, q, dep = build_frames(args.panel, args.strategy_series)
    print(f"[R1f] series {len(strat)} periods; FF frame {len(ff)}, q frame {len(q)}", flush=True)

    frames = {"ff": ff, "q": q}
    R = {"item": "R1-fragility", "prereg": "HANDOFF_r1.md section 6",
         "stable_from": STABLE_FROM, "nw_lag": args.lag, "weights": dep}

    # ---- 6. overlap -------------------------------------------------------------
    R["overlap"] = overlap_check(strat, ff)

    # ---- 1. stable-universe window ----------------------------------------------
    stable = ff[ff.index >= STABLE_FROM]
    full_fit = _fit(ff, FF_MODEL, args.lag)
    stable_fit = _fit(stable, FF_MODEL, args.lag)
    R["stable_universe"] = {
        "full": {"alpha_ann": full_fit["alpha_ann"], "t_nw": full_fit["alpha_t_nw"],
                 "n": full_fit["n_periods"], "raw_ann": full_fit["raw_ann"],
                 "window": [str(ff.index.min().date()), str(ff.index.max().date())]},
        "stable": {"alpha_ann": stable_fit["alpha_ann"], "t_nw": stable_fit["alpha_t_nw"],
                   "n": stable_fit["n_periods"], "raw_ann": stable_fit["raw_ann"],
                   "window": [str(stable.index.min().date()), str(stable.index.max().date())]},
        "alpha_change_pp": (stable_fit["alpha_ann"] - full_fit["alpha_ann"]) * 100,
        "direction": ("LOWER on the stable window"
                      if stable_fit["alpha_ann"] < full_fit["alpha_ann"]
                      else "HIGHER on the stable window"),
    }

    # ---- 2. subperiods: halves and thirds ---------------------------------------
    def _cuts(d, k):
        n = len(d)
        return [(f"{i + 1}/{k}", d.iloc[i * n // k:(i + 1) * n // k]) for i in range(k)]

    R["subperiods"] = {}
    for label, k in (("halves", 2), ("thirds", 3)):
        R["subperiods"][label] = {}
        for name, sub in _cuts(ff, k):
            r = _fit(sub, FF_MODEL, args.lag)
            R["subperiods"][label][name] = {
                "window": [str(sub.index.min().date()), str(sub.index.max().date())],
                "n": r["n_periods"], "raw_ann": r["raw_ann"],
                "alpha_ann": r["alpha_ann"], "t_nw": r["alpha_t_nw"]}

    # ---- 3. concentration --------------------------------------------------------
    R["concentration"] = {"full": concentration(ff, FF_MODEL, args.lag),
                          "stable": concentration(stable, FF_MODEL, args.lag)}

    # ---- 4. model sensitivity ----------------------------------------------------
    R["models"] = {"full": {}, "stable": {}}
    for name, (cols, fam) in MODELS.items():
        d = frames[fam]
        r = _fit(d, cols, args.lag)
        R["models"]["full"][name] = {"alpha_ann": r["alpha_ann"], "t_nw": r["alpha_t_nw"],
                                     "n": r["n_periods"], "r2": r["r2"]}
        ds = d[d.index >= STABLE_FROM]
        rs = _fit(ds, cols, args.lag)
        R["models"]["stable"][name] = {"alpha_ann": rs["alpha_ann"], "t_nw": rs["alpha_t_nw"],
                                       "n": rs["n_periods"], "r2": rs["r2"]}

    # ---- 5. rolling --------------------------------------------------------------
    R["rolling"] = rolling_alpha(ff, FF_MODEL, window=40, lag=args.lag)

    # ---- verdict against the four pre-committed criteria -------------------------
    c1 = stable_fit["alpha_t_nw"] > T_BAR
    halves = R["subperiods"]["halves"]
    c2 = all(v["alpha_ann"] > 0 for v in halves.values())
    share5 = R["concentration"]["full"]["share_from_best"]["best_5"]
    share5_s = R["concentration"]["stable"]["share_from_best"]["best_5"]
    c3 = share5 is not None and share5 <= CONCENTRATION_LIMIT
    c4 = all(v["t_nw"] > T_BAR for v in R["models"]["full"].values())
    c4_stable = all(v["t_nw"] > T_BAR for v in R["models"]["stable"].values())

    crit = {
        "1_stable_universe_t_over_2": {"pass": bool(c1), "t": stable_fit["alpha_t_nw"],
                                       "alpha_ann": stable_fit["alpha_ann"]},
        "2_no_sign_flip_in_halves": {"pass": bool(c2),
                                     "alphas": {k: v["alpha_ann"] for k, v in halves.items()}},
        "3_best5_share_at_most_50pct": {"pass": bool(c3), "share_full": share5,
                                        "share_stable": share5_s},
        "4_every_model_t_over_2": {"pass": bool(c4), "pass_on_stable_window": bool(c4_stable),
                                   "t_by_model": {k: v["t_nw"]
                                                  for k, v in R["models"]["full"].items()}},
    }
    all_pass = all(v["pass"] for v in crit.values())
    R["verdict"] = {
        "criteria": crit,
        "verdict": "ROBUST" if all_pass else "FRAGILE",
        "note_stable_window_models": ("every model also clears t>2 on the stable window"
                                      if c4_stable else
                                      "NOT every model clears t>2 on the stable window "
                                      "— recorded as a qualification, see handoff"),
    }

    # ---------------------------------------------------------------- print
    o = R["overlap"]
    print("\n=== 6. OVERLAP CHECK")
    print(f"  grid dates {o['n_grid_dates']}, windows {o['n_windows']}, "
          f"days/window {o['window_days_min']}-{o['window_days_max']}")
    print(f"  strictly increasing {o['grid_strictly_increasing']}, duplicates "
          f"{o['grid_has_duplicates']}, consecutive windows sharing a day "
          f"{o['consecutive_windows_sharing_a_day']}")
    print(f"  -> NON-OVERLAPPING: {o['windows_are_non_overlapping']}")

    s = R["stable_universe"]
    print("\n=== 1. STABLE-UNIVERSE WINDOW (the B6 preview)")
    for k in ("full", "stable"):
        v = s[k]
        print(f"  {k:>7}  n {v['n']:>3}  [{v['window'][0]} -> {v['window'][1]}]  "
              f"raw {_pct(v['raw_ann'])}  alpha {_pct(v['alpha_ann'])}  t {v['t_nw']:+.3f}")
    print(f"  -> {s['direction']}, {s['alpha_change_pp']:+.2f} pp")

    print("\n=== 2. SUBPERIOD STABILITY")
    for label in ("halves", "thirds"):
        for name, v in R["subperiods"][label].items():
            print(f"  {label:>6} {name}  n {v['n']:>3}  [{v['window'][0]} -> {v['window'][1]}]"
                  f"  raw {_pct(v['raw_ann'])}  alpha {_pct(v['alpha_ann'])}  t {v['t_nw']:+.3f}")

    for scope in ("full", "stable"):
        c = R["concentration"][scope]
        print(f"\n=== 3. CONCENTRATION [{scope}]  (n {c['n_full']}, alpha "
              f"{_pct(c['alpha_ann_full'])}, t {c['t_full']:+.3f})")
        for k in (1, 3, 5):
            print(f"  share of total alpha from best {k}: "
                  f"{c['share_from_best'][f'best_{k}'] * 100:5.1f}%")
        for k, v in c["drop_best"].items():
            print(f"  {k:>12}  n {v['n']:>3}  alpha {_pct(v['alpha_ann'])}  t {v['t_nw']:+.3f}")
        v = c["drop_worst_5"]
        print(f"  {'drop_worst_5':>12}  n {v['n']:>3}  alpha {_pct(v['alpha_ann'])}  "
              f"t {v['t_nw']:+.3f}")
        print(f"  best 5 periods: {c['top5_dates']}")

    print("\n=== 4. MODEL SENSITIVITY  (top - ew)")
    for scope in ("full", "stable"):
        print(f"  [{scope}]")
        for name, v in R["models"][scope].items():
            print(f"    {name:>18}  n {v['n']:>3}  alpha {_pct(v['alpha_ann'])}  "
                  f"t {v['t_nw']:+.3f}  R2 {v['r2']:.3f}")

    r = R["rolling"]
    print(f"\n=== 5. ROLLING ALPHA  ({r['window_periods']}-period window, {r['n_windows']})")
    print(f"  alpha min {_pct(r['alpha_min'])}  median {_pct(r['alpha_median'])}  "
          f"max {_pct(r['alpha_max'])}")
    print(f"  share of windows positive {r['share_positive'] * 100:.0f}%   "
          f"with t>2 {r['share_t_over_2'] * 100:.0f}%")
    print(f"  weakest: {r['min_alpha_window']['start']} -> {r['min_alpha_window']['end']}  "
          f"alpha {_pct(r['min_alpha_window']['alpha_ann'])} "
          f"t {r['min_alpha_window']['t_nw']:+.2f}")

    print("\n=== VERDICT against the pre-committed criteria (HANDOFF_r1.md section 6)")
    for k, v in crit.items():
        print(f"  {'PASS' if v['pass'] else 'FAIL'}  {k}")
    print(f"  -> {R['verdict']['verdict']}")
    print(f"  {R['verdict']['note_stable_window_models']}")

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, default=float)
    print(f"\n[R1f] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
