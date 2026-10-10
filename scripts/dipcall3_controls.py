"""DIP-CALL-3 — CONTROLS on the era arm's first run. Zero trials, and they can only BLOCK.

Under `MB1-SEL` a control can only ever BLOCK a finding, never produce one, so it adds no degree
of freedom and charges nothing. `scripts/dipcall3_arm.py` runs a scoring path landed and
validated under `PREREG_dipcall2.md` against a DIFFERENT ERA, so what needs validating is the
ERA ASSEMBLY -- the market leg, the universe, the window -- and not the arithmetic.

  C1  THE ERA'S MARKET LEG IS SANE, against an EXTERNAL yardstick rather than my own
      expectation: SPY's own daily series over the same sessions. A market leg that is wrong
      makes every `mkt` abnormal return wrong in a way nothing else in the arm would notice.
      1999-2008 contains two bear markets, so the LEVEL is expected to be poor; the CORRELATION
      is the check.
  C2  THE ABNORMAL RETURNS RE-DERIVE BY HAND on named cells at h63, from the raw CSV and the
      market series, by arithmetic that is NOT how the arm computes them.
  C3  THE PERMUTATION NULL BRACKETS ITS OWN MEAN on every scored cell.
  C4  WHY THE TWO DEFINITIONS DISAGREE, decomposed on the arm's own rows. The gap is an
      IDENTITY: own - mkt = r_market(window) - h * mu_prior(name). Over 1999-2008 the market's
      own window return is near zero or NEGATIVE, so -- unlike the 2009-2019 build era -- the
      own-normal leg does NOT credit the strategy with a decade-long bull market. That is the
      sentence a reader needs before comparing the two eras' own-normal numbers.
  C5  THE $10B FLOOR IS A NOMINAL FLOOR AND THIS ERA IS EARLIER, so the same number selects a
      LARGER slice of the market. Measured, not asserted.

Usage:  python -m scripts.dipcall3_controls
"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                    # noqa: E402
from scripts import dipcall_arm as ARM                                        # noqa: E402

OUT = "DIPCALL3_CONTROLS.json"
ERA = D.ERA_OOS9908


def main():
    cfg = D.era(ERA)
    lo, hi = cfg["lo"], cfg["hi"]
    art = {"item": "DIP-CALL-3 arm controls", "trials": 0, "era": ERA, "era_window": [lo, hi],
           "note": "a control can only BLOCK a finding, never produce one (MB1-SEL)"}
    sched, _ = D.tier_schedule_era(ERA)
    ever = sorted(t for t, v in sched.items()
                  if v and max(c for _, c in v) >= D.TIER_FLOOR)
    names = [t for t in ever
             if os.path.isfile(os.path.join(D.prices_dir(), "%s.csv" % t))]

    print("rebuilding the era's cap-weighted market for the controls (%d names) ..." % len(names))
    market = ARM.build_market(names, sched, D.K_PRIMARY, lo=lo, hi=hi)
    mdates, mret = market["dates"], market["ret"]

    # ------------------------------------------------------------------ C1 vs SPY (external)
    spy = D.read_prices("SPY")
    spy = spy[(spy["date"] >= lo) & (spy["date"] <= hi)].reset_index(drop=True)
    sr = spy["close"].pct_change().to_numpy(dtype=float)
    sidx = {d: j for j, d in enumerate(spy["date"].tolist())}
    pr = [(mret[j], sr[sidx[d]]) for j, d in enumerate(mdates)
          if d in sidx and np.isfinite(sr[sidx[d]])]
    a = np.array([p[0] for p in pr])
    b = np.array([p[1] for p in pr])
    yrs = len(a) / 252.0
    c1 = {"sessions_compared": len(a), "corr_daily": float(np.corrcoef(a, b)[0, 1]),
          "era_market_ann_pct": float((np.prod(1.0 + a) ** (1.0 / yrs) - 1.0) * 100.0),
          "spy_ann_pct": float((np.prod(1.0 + b) ** (1.0 / yrs) - 1.0) * 100.0),
          "era_market_daily_sd_pp": float(np.std(a, ddof=1) * 100.0),
          "spy_daily_sd_pp": float(np.std(b, ddof=1) * 100.0),
          "bar_corr": 0.90,
          "note": "the LEVEL is expected to be poor -- 1999-2008 holds the dot-com unwind and "
                  "the GFC -- so the CORRELATION is the check, not the return"}
    c1["pass"] = bool(c1["corr_daily"] >= c1["bar_corr"])
    art["C1_market_vs_spy"] = c1
    print("C1  era market vs SPY: corr %.4f (bar %.2f) ; ann %.2f%% vs %.2f%% ; "
          "daily sd %.4fpp vs %.4fpp -> %s"
          % (c1["corr_daily"], c1["bar_corr"], c1["era_market_ann_pct"], c1["spy_ann_pct"],
             c1["era_market_daily_sd_pp"], c1["spy_daily_sd_pp"],
             "PASS" if c1["pass"] else "FIRES"))

    # ------------------------------------------------- C2 hand re-derivation on named cells
    ev = pd.read_pickle(D.out_path("DIPCALL3_EVENTS.pkl"))
    ev["ticker"] = ev["ticker"].astype(str)
    tier_ev = ev[ev["tier"].astype(bool)].reset_index(drop=True)
    rng = np.random.default_rng(11)
    pick = rng.choice(len(tier_ev), size=min(40, len(tier_ev)), replace=False)
    term = ARM.terminal_names()
    checks, w_own, w_mkt = [], 0.0, 0.0
    h = 63
    for i in pick:
        r = tier_ev.iloc[int(i)]
        t, d = r["ticker"], r["date"]
        s = D.read_prices(t)
        if s is None:
            continue
        dates = s["date"].tolist()
        if d not in dates:
            continue
        j = dates.index(d)
        close = s["close"].to_numpy(dtype=float)
        ret = s["close"].pct_change().to_numpy(dtype=float)
        if j + h >= len(close) or j < D.VOL_WIN:
            continue
        fwd = close[j + h] / close[j] - 1.0
        mu = float(np.mean(ret[j - D.VOL_WIN:j]))
        hand_own = fwd - h * mu
        mj = market["index"].get(d)
        if mj is None or mj + h >= len(mdates):
            continue
        rm = float(np.prod(1.0 + mret[mj + 1:mj + h + 1]) - 1.0)
        hand_mkt = fwd - rm
        dcode = np.array([market["index"].get(x, -1) for x in dates], dtype=np.int64)
        ar_own, ar_mkt, _u, _tu = ARM.abnormal(close, ret, dcode, market, h, t in term)
        w_own = max(w_own, abs(float(ar_own[j]) - hand_own))
        w_mkt = max(w_mkt, abs(float(ar_mkt[j]) - hand_mkt))
        checks.append({"ticker": t, "date": d, "hand_own_pp": hand_own * 100.0,
                       "arm_own_pp": float(ar_own[j]) * 100.0,
                       "hand_mkt_pp": hand_mkt * 100.0,
                       "arm_mkt_pp": float(ar_mkt[j]) * 100.0})
    c2 = {"horizon": h, "cells_checked": len(checks), "max_abs_dev_own": w_own,
          "max_abs_dev_mkt": w_mkt, "tolerance": 1e-9, "sample": checks[:8],
          "note": "the own-normal leg is re-derived with a PLAIN 60-session mean and the market "
                  "leg by COMPOUNDING the daily series, neither of which is how the arm computes "
                  "them, so an agreement is two routes meeting rather than one route repeated"}
    c2["pass"] = bool(len(checks) >= 10 and w_own < 1e-9 and w_mkt < 1e-9)
    art["C2_hand_rederivation"] = c2
    print("C2  hand re-derivation on %d cells at h%d: max |dev| own %.3e  mkt %.3e -> %s"
          % (c2["cells_checked"], h, w_own, w_mkt, "PASS" if c2["pass"] else "FIRES"))

    # --------------------------------------------------------------- C3 permutation sampler
    with io.open(D.out_path("DIPCALL3_ARM.json"), encoding="utf-8") as fh:
        arm = json.load(fh)
    c3 = {"cells": {}}
    for key, cell in sorted(arm["full_sample_cells"].items()):
        for defn in ("own", "mkt"):
            p = (cell.get(defn) or {}).get("permutation")
            if p and p.get("draws"):
                c3["cells"]["%s|%s" % (key, defn)] = {
                    "null_mean": p["null_mean"], "p05": p["p05"], "p95": p["p95"],
                    "events_used": p.get("events_used"),
                    "brackets_its_mean": bool(p["p05"] <= p["null_mean"] <= p["p95"])}
    c3["pass"] = bool(c3["cells"]) and all(v["brackets_its_mean"] for v in c3["cells"].values())
    art["C3_permutation_sampler"] = c3
    print("C3  permutation null: %d cells, every p05 <= mean <= p95 -> %s"
          % (len(c3["cells"]), "PASS" if c3["pass"] else "FIRES"))

    # ----------------------------------------- C4 own-minus-market, decomposed on this era
    print("\nC4  decomposing own-minus-market on the arm's own rows (this is the sentence a\n"
          "    cross-era comparison needs) ...")
    c4 = {}
    for hh in cfg["horizons_primary"]:
        rm_acc, mu_acc, n_acc = [], [], 0
        for t, g in tier_ev.groupby("ticker", sort=False):
            s2 = D.read_prices(t)
            if s2 is None:
                continue
            dates = s2["date"].tolist()
            pos = {d: j for j, d in enumerate(dates)}
            ret2 = s2["close"].pct_change().to_numpy(dtype=float)
            mu_s = pd.Series(ret2).rolling(
                D.VOL_WIN, min_periods=D.MIN_VOL_OBS).mean().shift(1).to_numpy()
            for d in g["date"].tolist():
                j = pos.get(d)
                mj = market["index"].get(d)
                if j is None or mj is None or mj + hh >= len(mdates):
                    continue
                if not np.isfinite(mu_s[j]):
                    continue
                rm_acc.append(float(np.prod(1.0 + mret[mj + 1:mj + hh + 1]) - 1.0))
                mu_acc.append(hh * float(mu_s[j]))
                n_acc += 1
        rm_m = float(np.mean(rm_acc)) * 100.0 if rm_acc else float("nan")
        mu_m = float(np.mean(mu_acc)) * 100.0 if mu_acc else float("nan")
        c4["h%d" % hh] = {"n_rows": n_acc, "mean_market_window_return_pp": rm_m,
                          "mean_h_times_own_trailing_mean_pp": mu_m,
                          "implied_own_minus_mkt_pp": rm_m - mu_m,
                          "market_annualised_pct_over_same_windows": rm_m / hh * 252.0,
                          "own_trailing_mean_annualised_pct": mu_m / hh * 252.0}
        print("    h%-4d n %6d  market window %+8.4fpp (%+7.2f%%/yr)  h*mu_prior %+8.4fpp "
              "(%+7.2f%%/yr)  implied own-mkt %+8.4fpp"
              % (hh, n_acc, rm_m, rm_m / hh * 252.0, mu_m, mu_m / hh * 252.0, rm_m - mu_m))
    art["C4_own_minus_market_decomposition"] = c4

    # --------------------------------- C5 the $10B floor is NOMINAL and this era is earlier
    with io.open(D.out_path("DIPCALL3_KILLS.json"), encoding="utf-8") as fh:
        k3 = json.load(fh)
    tsz = k3["tier_size_per_date"]
    caps = []
    for t, v in sched.items():
        for _d, c in v:
            if c and c >= D.TIER_FLOOR:
                caps.append(c)
    c5 = {"floor_usd": D.TIER_FLOOR,
          "tier_names_per_date": {"min": tsz["per_date_min"], "median": tsz["per_date_median"],
                                  "max": tsz["per_date_max"]},
          "panel_names": k3["summary"]["panel_names"],
          "tier_median_market_cap_usd": float(np.median(caps)) if caps else None,
          "tier_p90_market_cap_usd": float(np.percentile(caps, 90)) if caps else None,
          "disclosure": "the floor is NOMINAL and was kept at $10B for comparability with "
                        "DIP-CALL and DIP-CALL-2 rather than deflated; changing it would change "
                        "the object. 1999-2008 is EARLIER, so the same nominal number selects a "
                        "LARGER slice of the market than it does in 2009-2019 -- on US CPI the "
                        "1999 dollar is worth roughly 1.5 of a 2019 dollar. Read every tier "
                        "figure here as 'companies above $10bn of NOMINAL market cap at the "
                        "time', never as 'the same companies DIP-CALL-2 looked at'."}
    art["C5_nominal_floor_disclosure"] = c5
    print("\nC5  tier/date min %d median %d max %d of %s panel names ; tier median cap $%.1fbn"
          % (c5["tier_names_per_date"]["min"], c5["tier_names_per_date"]["median"],
             c5["tier_names_per_date"]["max"], "{:,}".format(c5["panel_names"]),
             (c5["tier_median_market_cap_usd"] or 0) / 1e9))
    print("    the $10B floor is NOMINAL and was NOT deflated -- see the disclosure field")

    gates = {"C1_market_vs_spy": c1["pass"], "C2_hand_rederivation": c2["pass"],
             "C3_permutation_sampler": c3["pass"]}
    art["gates"] = gates
    art["all_blocking_controls_pass"] = bool(all(gates.values()))
    with io.open(D.out_path(OUT), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\ngates: %s" % gates)
    print("wrote %s" % D.out_path(OUT))
    return 0 if art["all_blocking_controls_pass"] else 4


if __name__ == "__main__":
    sys.exit(main())
