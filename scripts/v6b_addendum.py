#!/usr/bin/env python3
"""V6-B addendum — ADDITIVE ONLY. This never recomputes an arm or a verdict.

M1 came back REAL, and C8 measured the healthy dipped set at 2.06x the median market cap of
the unhealthy one. C8's REGISTERED PURPOSE is that "a size sort must not be reportable as a
health finding", and the tilt alone cannot serve that purpose once an arm has cleared: you
have to know whether the effect survives size. So C8 is deepened here into a within-size
stratification.

EVERYTHING IN THIS FILE IS A POST-HOC DIAGNOSTIC AND CARRIES NO VERDICT. The registered M1
verdict stands exactly as computed by the arm pass. This can only add a caveat, never a pass.

D1  base rates - P(further -20%) per group, so the headline is quotable at all
D2  M1 within per-date market-cap QUINTILES - is it a size sort?
D3  acquisition rate by health group - the register's expectation 4, and the number that
    shows what a naive P(delisted) would have done

Run:  python -m scripts.v6b_addendum
"""
from __future__ import annotations

import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import statistics as ST                          # noqa: E402
from scripts.v6_dip_detector import (HEALTH_FLOOR, QUALITY_FLOOR,    # noqa: E402
                                     health_panel, trailing_drawdown)
from scripts.v6b_dip_survival import (ACQUIRED_ACTIONS, DEPTH, DISTRESS_CAL_DAYS,  # noqa: E402
                                      FURTHER_DROP, MIN_PER_SIDE, action_events,
                                      forward_paths, two_group_cell)

ROOT = r"C:/Users/donni/Downloads/valuation-tool"
ART = os.path.join(ROOT, "data/free_analysis/V6B_DIP_SURVIVAL.json")
DATA = os.path.join(ROOT, "data/backtest")
N_QUINTILES = 5


def main():
    d = json.load(open(ART))
    assert "arms" in d, "the arm pass must have run first"

    panel = pickle.load(open(os.path.join(ROOT, "data/free_analysis/panel_v6.pkl"), "rb"))
    dates = sorted(panel["date"].unique())
    tickers = sorted(panel["ticker"].unique())
    dd = trailing_drawdown(os.path.join(DATA, "prices"), tickers, dates)
    hp = health_panel(DATA, tickers, dates)
    fp = forward_paths(os.path.join(DATA, "prices"), tickers, dates)
    p = (panel.merge(dd, on=["date", "ticker"], how="left")
               .merge(hp, on=["date", "ticker"], how="left")
               .merge(fp, on=["date", "ticker"], how="left"))
    p["_dip"] = pd.to_numeric(p["drawdown"], errors="coerce") <= -DEPTH
    p["_healthy"] = (pd.to_numeric(p["quality"], errors="coerce") > QUALITY_FLOOR) & \
                    (pd.to_numeric(p["health"], errors="coerce") >= HEALTH_FLOOR)
    dips = p[p["_dip"] & p["fwd_min_ret"].notna()].copy()
    dips["_m1"] = (pd.to_numeric(dips["fwd_min_ret"], errors="coerce")
                   <= FURTHER_DROP).astype(float)

    out = {}

    # ---- D1: base rates, so the headline can be quoted at all ----
    h = dips["_healthy"].to_numpy(dtype=bool)
    out["D1_base_rates"] = {
        "P_further20_healthy": round(float(dips.loc[h, "_m1"].mean()), 4),
        "P_further20_unhealthy": round(float(dips.loc[~h, "_m1"].mean()), 4),
        "P_further20_all_dips": round(float(dips["_m1"].mean()), 4),
        "n_healthy": int(h.sum()), "n_unhealthy": int((~h).sum()),
        "relative_reduction": None,
    }
    a, b = out["D1_base_rates"]["P_further20_healthy"], out["D1_base_rates"]["P_further20_unhealthy"]
    out["D1_base_rates"]["relative_reduction"] = round((b - a) / b, 4) if b else None

    # ---- D2: M1 WITHIN per-date market-cap quintiles ----
    dips["_mc"] = pd.to_numeric(dips["market_cap"], errors="coerce")
    dips["_q"] = np.nan
    for dt, g in dips.groupby("date"):
        mc = g["_mc"]
        if mc.notna().sum() < N_QUINTILES * MIN_PER_SIDE * 2:
            continue
        try:
            dips.loc[g.index, "_q"] = pd.qcut(mc, N_QUINTILES, labels=False, duplicates="drop")
        except ValueError:
            continue
    rng = np.random.default_rng(20260813)
    d2 = {}
    for q in range(N_QUINTILES):
        sub = dips[dips["_q"] == q]
        if len(sub) < 200:
            d2[f"Q{q+1}"] = {"status": "too few rows", "n_rows": int(len(sub))}
            continue
        cell = two_group_cell(sub, "_m1", "_healthy", rng)
        d2[f"Q{q+1}"] = {
            "n_rows": int(len(sub)),
            "median_mcap": float(sub["_mc"].median()),
            "n_dates": cell.get("n_dates"),
            "full_diff_pp": cell.get("full", {}).get("mean_diff_pp"),
            "full_t": cell.get("full", {}).get("t"),
            "perm_p5": cell.get("full", {}).get("perm_p5"),
            "below_p5_full": cell.get("full", {}).get("below_p5"),
            "both_halves_below_p5": cell.get("both_halves_below_p5"),
            "halves_same_sign": cell.get("halves_same_sign"),
        }
    neg = [v for v in d2.values() if v.get("full_diff_pp") is not None]
    out["D2_m1_within_market_cap_quintiles"] = {
        "by_quintile": d2,
        "quintiles_scored": len(neg),
        "quintiles_with_NEGATIVE_diff": sum(1 for v in neg if v["full_diff_pp"] < 0),
        "quintiles_clearing_own_p5_full": sum(1 for v in neg if v["below_p5_full"]),
        "quintiles_clearing_BOTH_halves": sum(1 for v in neg if v["both_halves_below_p5"]),
        "min_abs_diff_pp": (min(abs(v["full_diff_pp"]) for v in neg) if neg else None),
        "STATUS": "POST-HOC DIAGNOSTIC - CARRIES NO VERDICT",
        "why_it_exists": ("C8 measured the healthy dipped set at 2.06x the median market cap "
                          "of the unhealthy one, and C8's registered purpose is that a SIZE "
                          "sort must not be reportable as a HEALTH finding. The tilt alone "
                          "cannot serve that purpose once an arm has cleared."),
        "how_to_read": ("If M1's separation survives INSIDE every size quintile, it is not a "
                        "size sort. If it vanishes, the registered verdict stands as computed "
                        "but must be reported as substantially a size effect."),
    }

    # ---- D3: acquisition rate by health group (register expectation 4) ----
    ev = action_events(os.path.join(ROOT, "data/bulk/actions.csv"), tickers)
    dt = pd.to_datetime(dips["date"]).to_numpy(dtype="datetime64[D]")
    tk = dips["ticker"].to_numpy()
    acq = np.zeros(len(dips), dtype=bool)
    for i in range(len(dips)):
        e = ev.get(tk[i], {}).get("acquired")
        if e:
            ed = np.datetime64(e)
            if ed > dt[i] and (ed - dt[i]).astype(int) <= DISTRESS_CAL_DAYS:
                acq[i] = True
    out["D3_acquisition_by_health"] = {
        "P_acquired_healthy": round(float(acq[h].mean()), 5),
        "P_acquired_unhealthy": round(float(acq[~h].mean()), 5),
        "n_acquired_healthy": int(acq[h].sum()),
        "n_acquired_unhealthy": int(acq[~h].sum()),
        "ratio_healthy_over_unhealthy": (
            round(float(acq[h].mean() / acq[~h].mean()), 3) if acq[~h].mean() else None),
        "STATUS": "POST-HOC DIAGNOSTIC - CARRIES NO VERDICT",
        "why_it_matters": ("This is what a naive P(delisted) would have counted as a DEATH. "
                           "82.63% of delistings on this universe are acquisitions."),
    }

    d.setdefault("diagnostics", {}).update(out)
    with open(ART, "w") as f:
        json.dump(d, f, indent=2, default=float)
    print(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
