#!/usr/bin/env python3
"""factor_alpha.py — is the top-decile excess return alpha, or the factor premia?  [R1]

`top_decile_alpha = 4 * (mean top-decile 63d return - mean equal-weighted universe 63d return)`
and nothing else: no beta adjustment, no factor model, no t-statistic on the headline anywhere
in the repo. The composite is roughly one-seventh each of value, quality, momentum, size,
capital discipline and institutional ownership -- very nearly Fama-French five factors plus
momentum. So the headline cannot currently distinguish "we found something" from "we assembled
the standard factor premia". This settles it.

    r_t = a + b1*MKT + b2*SMB + b3*HML + b4*RMW + b5*CMA + b6*UMD + e

reported with the intercept, its Newey-West t (lag 1), the R^2 and every loading; then repeated
against the Hou-Xue-Zhang q-factor model (MKT, ME, I/A, ROE), which is a harder test for a
quality-heavy book; then repeated on the long-short series.

Thresholds are pre-registered in HANDOFF_r1.md section 1 and are NOT restated from results.

Inputs already exist and are NOT rebuilt here:
  data/free_analysis/panel.pkl                              (X4's shipped panel)
  data/free_analysis/ETF_BENCHMARK_RESULTS_strategy_series.csv  (X4's shipped top/ew series)
  data/factors/parsed/{ff5_daily,mom_daily,q5_daily}.csv    (D3's fetched + verified factors)

Modifies no existing file: the panel modules are owned by another lane.

    python -m scripts.factor_alpha
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

PANEL = "data/free_analysis/panel.pkl"
STRAT = "data/free_analysis/ETF_BENCHMARK_RESULTS_strategy_series.csv"
FF5 = "data/factors/parsed/ff5_daily.csv"
MOM = "data/factors/parsed/mom_daily.csv"
Q5 = "data/factors/parsed/q5_daily.csv"

PPY = 252.0 / 63.0                      # four 63-trading-day windows a year
B6_CONTAMINATED = 37                    # audit B6: the panel's first 37 dates have an
                                        # inverted universe (each ticker keeps its own last
                                        # 18.5y, so a 2001 cross-section is names that DIED)

FF_MODEL = ["MKT", "SMB", "HML", "RMW", "CMA", "UMD"]
Q4_MODEL = ["MKT", "ME", "IA", "ROE"]
Q5_MODEL = ["MKT", "ME", "IA", "ROE", "EG"]


# --------------------------------------------------------------------------- regression
def ols_nw(y, X, lag=1):
    """OLS with Newey-West (Bartlett) HAC standard errors.

    statsmodels is not installed in this environment, so this is written out. It is pinned
    against a closed-form check in tests/test_factor_alpha.py.

    y : (n,) ; X : (n, k) WITHOUT the intercept column -- one is prepended here.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n = len(y)
    Z = np.column_stack([np.ones(n), X])            # intercept first
    k = Z.shape[1]
    # A rank-deficient design silently produces garbage loadings and understated standard
    # errors -- exactly what a duplicated market column did to the q-factor block on the
    # first run of this script. Refuse to report a regression that cannot be identified.
    if np.linalg.matrix_rank(Z) < k:
        raise ValueError(f"rank-deficient design: rank {np.linalg.matrix_rank(Z)} < {k} "
                         "columns (duplicated or collinear regressor)")
    XtX_inv = np.linalg.pinv(Z.T @ Z)
    beta = XtX_inv @ (Z.T @ y)
    resid = y - Z @ beta

    # Newey-West meat: S = G0 + sum_{l=1..lag} w_l (Gl + Gl'), w_l = 1 - l/(lag+1)
    u = Z * resid[:, None]
    S = u.T @ u
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        G = u[l:].T @ u[:-l]
        S = S + w * (G + G.T)
    # small-sample correction n/(n-k), the usual convention
    cov = XtX_inv @ S @ XtX_inv * (n / max(1, n - k))
    se = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    t = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)

    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    adj = 1.0 - (1.0 - r2) * (n - 1) / max(1, n - k) if ss_tot > 0 else np.nan
    return {"beta": beta, "se": se, "t": t, "r2": r2, "adj_r2": adj, "n": n,
            "resid_std": float(resid.std(ddof=k))}


def regress(y, F, cols, label, lag=1):
    """Run one factor regression and package it for the report."""
    r = ols_nw(y, F[cols].values, lag=lag)
    a = float(r["beta"][0])
    return {
        "label": label,
        "n_periods": int(r["n"]),
        "mean_63d": float(np.mean(y)),
        "raw_ann": float(np.mean(y) * PPY),                 # same arithmetic the headline uses
        "alpha_63d": a,
        "alpha_ann": a * PPY,
        "alpha_t_nw": float(r["t"][0]),
        "alpha_se_63d": float(r["se"][0]),
        "r2": float(r["r2"]),
        "adj_r2": float(r["adj_r2"]),
        "loadings": {c: {"beta": float(r["beta"][i + 1]), "t": float(r["t"][i + 1])}
                     for i, c in enumerate(cols)},
    }


# --------------------------------------------------------------------------- factor data
def _load_daily():
    ff = pd.read_csv(FF5, parse_dates=["date"]).rename(columns={"Mkt-RF": "MKT_RF"})
    mo = pd.read_csv(MOM, parse_dates=["date"]).rename(columns={"Mom": "UMD"})
    q = pd.read_csv(Q5, parse_dates=["date"]).rename(columns={
        "R_MKT": "qMKT", "R_ME": "ME", "R_IA": "IA", "R_ROE": "ROE",
        "R_EG": "EG", "R_F": "qRF"})
    d = ff.merge(mo, on="date", how="outer").merge(q, on="date", how="outer")
    return d.sort_values("date").reset_index(drop=True)


def _agg(vals, how):
    """Aggregate a daily factor return series to one window return."""
    v = np.asarray(vals, dtype=float)
    if not len(v) or np.isnan(v).any():
        return np.nan
    return float(np.prod(1.0 + v) - 1.0) if how == "compound" else float(v.sum())


def factor_windows(grid, how="compound"):
    """Compound daily factors onto the panel's own (d_i, d_i+1] 63-trading-day windows.

    The panel's rebalance step EQUALS its holding horizon (63 == 63), so window i ends exactly
    on rebalance date i+1. Nothing is interpolated and no factor day outside the window is
    touched -- there is no look-ahead available in this construction.
    """
    d = _load_daily()
    grid = [pd.Timestamp(x) for x in sorted(pd.to_datetime(pd.Series(grid)).unique())]
    rows = []
    for a, b in zip(grid[:-1], grid[1:]):
        w = d[(d["date"] > a) & (d["date"] <= b)]
        if w.empty:
            continue
        rf = _agg(w["RF"], how)
        mkt_tot = _agg(w["MKT_RF"] + w["RF"], how)
        qrf = _agg(w["qRF"], how)
        qmkt_tot = _agg(w["qMKT"] + w["qRF"], how)
        rows.append({
            "date": a, "end": b, "n_days": int(len(w)),
            "RF": rf,
            # market EXCESS return: compound the total return, then subtract compounded RF
            "MKT": (mkt_tot - rf) if (mkt_tot == mkt_tot and rf == rf) else np.nan,
            "SMB": _agg(w["SMB"], how), "HML": _agg(w["HML"], how),
            "RMW": _agg(w["RMW"], how), "CMA": _agg(w["CMA"], how),
            "UMD": _agg(w["UMD"], how),
            "qRF": qrf,
            "qMKT_x": (qmkt_tot - qrf) if (qmkt_tot == qmkt_tot and qrf == qrf) else np.nan,
            "ME": _agg(w["ME"], how), "IA": _agg(w["IA"], how),
            "ROE": _agg(w["ROE"], how), "EG": _agg(w["EG"], how),
        })
    return pd.DataFrame(rows).set_index("date")


# --------------------------------------------------------------------------- strategy data
def decile_series(panel, weights, frac=0.1):
    """Per-date top-decile, bottom-decile and equal-weight returns.

    `top` and `ew` reproduce X4's shipped series exactly (asserted in main()); `bot` is the
    extra column R1 needs for the long-short object and is the only thing computed here that
    X4 did not already ship.
    """
    from valuation.screener.cross_sectional import zscore

    rows = []
    for d, sub in panel.groupby("date"):
        comp = np.zeros(len(sub))
        for c, w in weights.items():
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * w
        ok = np.isfinite(comp) & np.isfinite(sub["fwd_ret"].values)
        s = sub[ok].assign(_c=comp[ok]).sort_values("_c", ascending=False)
        if len(s) < 30:
            continue
        k = max(1, int(len(s) * frac))
        rows.append({"date": d,
                     "top": float(s.head(k)["fwd_ret"].mean()),
                     "bot": float(s.tail(k)["fwd_ret"].mean()),
                     "ew": float(s["fwd_ret"].mean()),
                     # the panel's own SPY 63d return over the same window -- used only to
                     # validate that this script's date alignment is right (see main())
                     "bench": float(sub["bench_ret"].iloc[0]),
                     "n": int(k)})
    return pd.DataFrame(rows).set_index("date")


# --------------------------------------------------------------------------- reporting
def _pct(x, p=2):
    return "n/a" if x is None or x != x else f"{x * 100:+.{p}f}%"


def _table(res):
    out = [f"  {res['label']}",
           f"    n = {res['n_periods']} periods   raw (unadjusted, annualised) = "
           f"{_pct(res['raw_ann'])}",
           f"    ALPHA = {_pct(res['alpha_ann'])}/yr   NW t(lag1) = {res['alpha_t_nw']:+.3f}"
           f"   R2 = {res['r2']:.3f}"]
    load = "  ".join(f"{c} {v['beta']:+.3f} (t {v['t']:+.2f})"
                     for c, v in res["loadings"].items())
    out.append(f"    loadings: {load}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Factor-adjusted alpha (R1).")
    ap.add_argument("--panel", default=PANEL)
    ap.add_argument("--strategy-series", default=STRAT)
    ap.add_argument("--json", default="data/free_analysis/FACTOR_ALPHA_RESULTS.json")
    ap.add_argument("--lag", type=int, default=1)
    args = ap.parse_args(argv)

    from valuation.screener import settings as S

    panel = pd.read_pickle(args.panel)
    panel["date"] = pd.to_datetime(panel["date"])
    dep = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if v and k in panel.columns}
    print(f"[R1] deployed weights: {dep}", flush=True)

    strat = decile_series(panel, dep)
    print(f"[R1] strategy series: {len(strat)} periods "
          f"{strat.index.min().date()} -> {strat.index.max().date()}", flush=True)

    # --- reproduce X4's shipped series exactly, so this lane is measuring the SAME object
    shipped = pd.read_csv(args.strategy_series, parse_dates=["date"]).set_index("date")
    j = strat.join(shipped[["top", "ew"]], rsuffix="_x4", how="inner")
    dtop = float(np.max(np.abs(j["top"] - j["top_x4"])))
    dew = float(np.max(np.abs(j["ew"] - j["ew_x4"])))
    print(f"[R1] reproduces X4's shipped series on {len(j)} periods "
          f"(max |dtop| {dtop:.2e}, max |dew| {dew:.2e})", flush=True)
    assert len(j) == len(shipped), "did not line up with X4's shipped series"
    assert dtop < 1e-9 and dew < 1e-9, "does not reproduce X4's shipped top/ew series"

    # --- ALIGNMENT VALIDATION -------------------------------------------------------
    # The panel carries SPY's own return over each 63-day window (`bench_ret`). If this
    # script's factor windows are aligned to the same calendar, regressing SPY's excess
    # return on MKT alone must give beta ~ 1, alpha ~ 0 and R^2 ~ 1. A date-alignment or
    # aggregation error would show up here as a beta away from 1 and a collapsed R^2.
    _f = factor_windows(list(strat.index), how="compound")
    _v = strat.join(_f, how="inner").dropna(subset=["MKT", "RF", "bench"])
    _b = ols_nw((_v["bench"] - _v["RF"]).values, _v[["MKT"]].values, lag=args.lag)
    validation = {"spy_on_mkt_beta": float(_b["beta"][1]),
                  "spy_on_mkt_alpha_ann": float(_b["beta"][0] * PPY),
                  "spy_on_mkt_alpha_t": float(_b["t"][0]),
                  "spy_on_mkt_r2": float(_b["r2"]), "n": int(_b["n"])}
    print(f"[R1] ALIGNMENT CHECK  SPY excess ~ MKT:  beta {validation['spy_on_mkt_beta']:.4f}"
          f"  R2 {validation['spy_on_mkt_r2']:.4f}"
          f"  alpha {validation['spy_on_mkt_alpha_ann'] * 100:+.2f}%/yr"
          f" (t {validation['spy_on_mkt_alpha_t']:+.2f})", flush=True)
    assert 0.90 < validation["spy_on_mkt_beta"] < 1.10, "SPY does not load ~1 on MKT — misaligned"
    assert validation["spy_on_mkt_r2"] > 0.95, "SPY/MKT R2 too low — windows are misaligned"

    results = {"item": "R1",
               "alignment_validation": validation,
               "prereg": "HANDOFF_r1.md section 1",
               "threshold": "FF5+MOM intercept positive with Newey-West t > 2.0",
               "nw_lag": args.lag,
               "weights": dep,
               "specs": {}}

    for how in ("compound", "sum"):
        fac = factor_windows(list(strat.index), how=how)
        df = strat.join(fac, how="inner").dropna(
            subset=["MKT", "SMB", "HML", "RMW", "CMA", "UMD", "RF"])
        dfq = strat.join(fac, how="inner").dropna(subset=["qMKT_x", "ME", "IA", "ROE", "EG"])

        for cut, lo in (("full", 0), (f"ex_b6_first_{B6_CONTAMINATED}", B6_CONTAMINATED)):
            d = df.iloc[lo:] if lo else df
            # Build the q design in its OWN frame. Renaming qMKT_x -> MKT in place would leave
            # two columns called MKT (the q market and the FF market, correlated 1.000), and
            # pandas would hand both to the regression under one label.
            dq = (dfq.iloc[lo:] if lo else dfq)
            dq = dq.assign(MKT=dq["qMKT_x"]).drop(columns=["qMKT_x"])
            assert not dq.columns.duplicated().any(), "duplicate column in the q design"

            objs = {
                # the headline's own object: 4 * mean(top - ew) IS top_decile_alpha
                "top_minus_ew": (d["top"] - d["ew"]).values,
                # the long-only book a user actually holds, in excess of the risk-free rate
                "top_excess_rf": (d["top"] - d["RF"]).values,
                # the cleaner statistical object (R1 method step 6)
                "long_short": (d["top"] - d["bot"]).values,
                # context: is the UNIVERSE itself unexplained? the headline is measured
                # against this benchmark, so its own alpha is part of reading the result
                "universe_excess_rf": (d["ew"] - d["RF"]).values,
            }
            objsq = {
                "top_minus_ew": (dq["top"] - dq["ew"]).values,
                "top_excess_rf": (dq["top"] - dq["qRF"]).values,
                "long_short": (dq["top"] - dq["bot"]).values,
                "universe_excess_rf": (dq["ew"] - dq["qRF"]).values,
            }

            key = f"{how}/{cut}"
            block = {"window": [str(d.index.min().date()), str(d.index.max().date())],
                     "window_q": [str(dq.index.min().date()), str(dq.index.max().date())],
                     "mean_days_per_window": float(d["n_days"].mean()),
                     "ff5_mom": {}, "q4": {}, "q5": {}}
            for name, y in objs.items():
                block["ff5_mom"][name] = regress(y, d, FF_MODEL, name, lag=args.lag)
            for name, y in objsq.items():
                block["q4"][name] = regress(y, dq, Q4_MODEL, name, lag=args.lag)
                block["q5"][name] = regress(y, dq, Q5_MODEL, name, lag=args.lag)
            results["specs"][key] = block

    # ---------------------------------------------------------------- extra reporting
    # NOT part of the pre-registered verdict rule (that is settled by the four specs above).
    # Reported because a single full-sample intercept says nothing about stability, and
    # because X4 measured a null over 2014-2026 that has to be reconciled rather than ignored.
    fac = factor_windows(list(strat.index), how="compound")
    d = strat.join(fac, how="inner").dropna(subset=FF_MODEL + ["RF"])
    y_all = (d["top"] - d["ew"]).values
    half = len(d) // 2
    subs = {
        "full": np.ones(len(d), dtype=bool),
        f"ex_b6_first_{B6_CONTAMINATED}": np.arange(len(d)) >= B6_CONTAMINATED,
        "first_half": np.arange(len(d)) < half,
        "second_half": np.arange(len(d)) >= half,
        "from_2014_x4_window": np.asarray(d.index >= "2014-01-01"),
        "from_2000": np.asarray(d.index >= "2000-01-01"),
        "to_2013": np.asarray(d.index < "2014-01-01"),
    }
    results["subperiods_top_minus_ew_ff5_mom"] = {}
    for name, m in subs.items():
        if m.sum() < 25:
            continue
        r = regress(y_all[m], d[m], FF_MODEL, name, lag=args.lag)
        results["subperiods_top_minus_ew_ff5_mom"][name] = {
            "n": r["n_periods"], "window": [str(d.index[m].min().date()),
                                            str(d.index[m].max().date())],
            "raw_ann": r["raw_ann"], "alpha_ann": r["alpha_ann"],
            "t_nw": r["alpha_t_nw"], "r2": r["r2"]}

    # --- Does the spread survive the strategy's own trading costs?
    # X4's formula, on X4's own shipped turnover/cost_bps columns: one-way bps charged on the
    # fraction of the book that turned over. The raw +12% headline is GROSS; the alpha above
    # inherits that, so it has to be charged before any product claim rests on it.
    sh = pd.read_csv(args.strategy_series, parse_dates=["date"]).set_index("date")
    dc = d.join(sh[["turnover", "cost_bps"]], how="left")
    cost = (dc["cost_bps"] / 1e4) * dc["turnover"]
    results["net_of_cost"] = {
        "cost_drag_ann": float(cost.mean() * PPY),
        "top_minus_ew": regress((dc["top"] - dc["ew"] - cost).values, dc, FF_MODEL,
                                "top_minus_ew_net", lag=args.lag),
        "top_excess_rf": regress((dc["top"] - dc["RF"] - cost).values, dc, FF_MODEL,
                                 "top_excess_rf_net", lag=args.lag),
    }

    # --- Spanning test: is the spread just the universe's OWN unexplained return?
    # FF5+MOM leaves a large positive intercept on the equal-weighted universe itself, which
    # means the factor model does not price this universe well (equal-weighted micro/small caps
    # are not spanned by SMB). Adding the universe's excess return as a seventh regressor asks
    # whether the top-decile spread is anything more than extra loading on that same
    # unexplained thing. If the intercept dies here, the "alpha" is a benchmark artifact.
    dspan = d.assign(EWUNIV=(d["ew"] - d["RF"]).values)
    results["spanning_vs_ew_universe"] = regress(
        (d["top"] - d["ew"]).values, dspan, FF_MODEL + ["EWUNIV"], "top_minus_ew_plus_ewuniv",
        lag=args.lag)

    # --- Where the raw headline actually goes, factor by factor.
    # OLS identity: alpha = mean(y) - sum_i beta_i * mean(f_i). Splitting the second term names
    # the premium each factor is worth to this book in annualised percentage points, which is a
    # more direct statement of the R1 question than the loadings are.
    rr = results["specs"]["compound/full"]["ff5_mom"]["top_minus_ew"]
    betas = np.array([rr["loadings"][c]["beta"] for c in FF_MODEL])
    means = d[FF_MODEL].values.mean(axis=0)
    contrib = {c: float(b * m * PPY) for c, b, m in zip(FF_MODEL, betas, means)}
    results["factor_contributions_top_minus_ew"] = {
        "raw_ann": float(y_all.mean() * PPY),
        "factor_explained_ann": float(betas @ means * PPY),
        "alpha_ann_via_identity": float((y_all.mean() - betas @ means) * PPY),
        "per_factor_pp": contrib,
        "factor_mean_ann": {c: float(m * PPY) for c, m in zip(FF_MODEL, means)},
    }
    # the identity must agree with the regression to machine precision, or something is wrong
    assert abs(results["factor_contributions_top_minus_ew"]["alpha_ann_via_identity"]
               - rr["alpha_ann"]) < 1e-9, "OLS identity disagrees with the fitted intercept"

    results["nw_lag_sensitivity_top_minus_ew_ff5_mom"] = {}
    for L in (0, 1, 2, 4, 8):
        r = regress(y_all, d, FF_MODEL, "lag", lag=L)
        results["nw_lag_sensitivity_top_minus_ew_ff5_mom"][f"lag_{L}"] = {
            "alpha_ann": r["alpha_ann"], "t_nw": r["alpha_t_nw"]}

    # ---------------------------------------------------------------- verdict
    pre = results["specs"]["compound/full"]["ff5_mom"]["top_minus_ew"]
    checks = []
    for key in results["specs"]:
        r = results["specs"][key]["ff5_mom"]["top_minus_ew"]
        checks.append({"spec": key, "alpha_ann": r["alpha_ann"], "t": r["alpha_t_nw"],
                       "passes": bool(r["alpha_ann"] > 0 and r["alpha_t_nw"] > 2.0)})
    all_pass = all(c["passes"] for c in checks)
    any_pass = any(c["passes"] for c in checks)
    verdict = ("ALPHA" if all_pass else
               "NULL - efficient factor exposure")
    results["verdict"] = {
        "primary_spec": "compound/full",
        "primary_alpha_ann": pre["alpha_ann"],
        "primary_t_nw": pre["alpha_t_nw"],
        "robustness": checks,
        "all_specs_pass": all_pass,
        "some_but_not_all_pass": bool(any_pass and not all_pass),
        "verdict": verdict,
        "claim": "A" if all_pass else "B",
    }

    # ---------------------------------------------------------------- print
    print()
    for key, block in results["specs"].items():
        print(f"=== {key}   [{block['window'][0]} -> {block['window'][1]}]"
              f"   {block['mean_days_per_window']:.1f} factor days/window")
        for model in ("ff5_mom", "q4", "q5"):
            print(f"  -- {model.upper()}")
            for name in ("top_minus_ew", "top_excess_rf", "long_short",
                         "universe_excess_rf"):
                print(_table(block[model][name]))
        print()

    print("=== SUBPERIODS  (top - ew, FF5+MOM)  -- context, not part of the verdict rule")
    for name, r in results["subperiods_top_minus_ew_ff5_mom"].items():
        print(f"  {name:>24}  n {r['n']:>3}  [{r['window'][0]} -> {r['window'][1]}]  "
              f"raw {_pct(r['raw_ann'])}  alpha {_pct(r['alpha_ann'])}  t {r['t_nw']:+.3f}")
    print(f"\n=== NET OF THE STRATEGY'S OWN COSTS  (drag "
          f"{_pct(results['net_of_cost']['cost_drag_ann'])}/yr, X4's formula)")
    for k2 in ("top_minus_ew", "top_excess_rf"):
        r = results["net_of_cost"][k2]
        print(_table(r))
    print("\n=== SPANNING TEST  (top - ew on FF5+MOM *plus* the EW universe's own excess return)")
    print(_table(results["spanning_vs_ew_universe"]))

    fc = results["factor_contributions_top_minus_ew"]
    print(f"\n=== WHERE THE RAW {_pct(fc['raw_ann'])}/yr GOES  (OLS identity, FF5+MOM)")
    for c, v in fc["per_factor_pp"].items():
        print(f"  {c:4s}  beta {rr['loadings'][c]['beta']:+.3f}  x  premium "
              f"{_pct(fc['factor_mean_ann'][c])}/yr  =  {v * 100:+.3f} pp")
    print(f"  {'':4s}  factor-explained total {_pct(fc['factor_explained_ann'])}"
          f"   ->  UNEXPLAINED {_pct(fc['alpha_ann_via_identity'])}")

    print("\n=== NEWEY-WEST LAG SENSITIVITY  (top - ew, FF5+MOM)")
    for name, r in results["nw_lag_sensitivity_top_minus_ew_ff5_mom"].items():
        print(f"  {name:>8}  alpha {_pct(r['alpha_ann'])}  t {r['t_nw']:+.3f}")

    print("\n=== VERDICT (against the pre-registered threshold, HANDOFF_r1.md section 1)")
    for c in checks:
        print(f"  {c['spec']:>28}  alpha {_pct(c['alpha_ann'])}/yr  "
              f"t {c['t']:+.3f}  {'PASS' if c['passes'] else 'fail'}")
    print(f"  -> {verdict}   (claim {results['verdict']['claim']})")

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n[R1] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
