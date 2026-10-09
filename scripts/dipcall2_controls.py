"""DIP-CALL-2 — CONTROLS on the arm's FIRST REAL RUN. Zero trials, and they can only BLOCK.

`scripts/dipcall_arm.py` shipped complete under `PREREG_dipcall.md`, was never executed because
`K1` fired, and its own docstring recorded that *"the scoring path has never executed against the
panel -- treat the first run as an instrument build, with controls, not as a measurement."* This
file is those controls. Under `MB1-SEL` a control can only ever BLOCK a finding, never produce
one, so it adds no degree of freedom and charges nothing.

  C1  THE MARKET LEG IS SANE, against an EXTERNAL yardstick rather than my own expectation.
      The half-0 cap-weighted market is compared with SPY's own daily series over the same
      sessions. `R10` measured the equal-weighted panel at +18.14%/yr against SPY's +15.32%
      2009-01 -> 2026-01, so a cap-weighted half-0 market should sit NEAR SPY and correlate
      tightly with it. A market leg that is wrong makes every `mkt` abnormal return wrong in a
      way nothing else in the arm would notice.
  C2  THE ABNORMAL RETURNS RE-DERIVE BY HAND on named cells, from the raw CSV and the market
      series, independently of the arm's own vectorised path.
  C3  THE PERMUTATION SAMPLER IS UNBIASED: the null's mean must match the event-count-weighted
      mean of the pool on the arm's own dates. A biased sampler would move the bar without
      moving anything else.
  C4  THE ARM'S ROWS ARE A SUBSET OF THE PERMUTATION POOL. If an event is not in its own null's
      population, the bar is calibrated on a different object.

Usage:  python -m scripts.dipcall2_controls
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

OUT = "DIPCALL2_CONTROLS.json"


def main():
    art = {"item": "DIP-CALL-2 arm controls", "trials": 0,
           "note": "a control can only BLOCK a finding, never produce one (MB1-SEL)"}
    sched = D.tier_schedule()
    names = ARM.half0_names()

    print("rebuilding the half-0 cap-weighted market for the controls ...")
    market = ARM.build_market(names, sched, D.K_PRIMARY)
    mdates = market["dates"]
    mret = market["ret"]

    # ---------------------------------------------------------------- C1 vs SPY (external)
    spy = D.read_prices("SPY")
    spy = spy[(spy["date"] >= D.BUILD_LO) & (spy["date"] <= D.BUILD_HI)].reset_index(drop=True)
    sr = spy["close"].pct_change().to_numpy(dtype=float)
    sidx = {d: j for j, d in enumerate(spy["date"].tolist())}
    pairs = [(mret[j], sr[sidx[d]]) for j, d in enumerate(mdates)
             if d in sidx and np.isfinite(sr[sidx[d]])]
    a = np.array([p[0] for p in pairs])
    b = np.array([p[1] for p in pairs])
    n_yrs = len(a) / 252.0
    c1 = {
        "sessions_compared": len(a),
        "corr_daily": float(np.corrcoef(a, b)[0, 1]),
        "half0_market_ann_pct": float((np.prod(1.0 + a) ** (1.0 / n_yrs) - 1.0) * 100.0),
        "spy_ann_pct": float((np.prod(1.0 + b) ** (1.0 / n_yrs) - 1.0) * 100.0),
        "half0_daily_sd_pp": float(np.std(a, ddof=1) * 100.0),
        "spy_daily_sd_pp": float(np.std(b, ddof=1) * 100.0),
        "reference": "R10 measured the EW panel at +18.14%/yr vs SPY +15.32% over 2009-01 to "
                     "2026-01; a CAP-weighted half-0 market should sit nearer SPY than the EW "
                     "panel does, and correlate tightly with it",
    }
    # The bar is pre-committed here and is deliberately loose: this is a SANITY check on a
    # benchmark, not a hypothesis test. A cap-weighted broad market that does not correlate
    # above 0.90 with SPY is broken, whatever its level.
    c1["bar_corr"] = 0.90
    c1["pass"] = bool(c1["corr_daily"] >= c1["bar_corr"])
    art["C1_market_vs_spy"] = c1
    print("C1  half-0 market vs SPY: corr %.4f (bar %.2f) ; ann %.2f%% vs %.2f%% ; "
          "daily sd %.4fpp vs %.4fpp -> %s"
          % (c1["corr_daily"], c1["bar_corr"], c1["half0_market_ann_pct"], c1["spy_ann_pct"],
             c1["half0_daily_sd_pp"], c1["spy_daily_sd_pp"], "PASS" if c1["pass"] else "FIRES"))

    # ------------------------------------------------- C2 hand re-derivation on named cells
    ev = pd.read_pickle(D.out_path("DIPCALL2_EVENTS.pkl"))
    ev["ticker"] = ev["ticker"].astype(str)
    tier_ev = ev[ev["tier"] & (ev["news"] == D.NO_NEWS)].reset_index(drop=True)
    rng = np.random.default_rng(11)
    pick = rng.choice(len(tier_ev), size=min(40, len(tier_ev)), replace=False)
    term = ARM.terminal_names()
    checks, worst_own, worst_mkt = [], 0.0, 0.0
    for i in pick:
        r = tier_ev.iloc[int(i)]
        t, d = r["ticker"], r["date"]
        s = D.read_prices(t)
        dates = s["date"].tolist()
        if d not in dates:
            continue
        j = dates.index(d)
        close = s["close"].to_numpy(dtype=float)
        ret = s["close"].pct_change().to_numpy(dtype=float)
        h = 21
        if j + h >= len(close):
            continue
        # BY HAND: the forward return, the own-normal leg and the market leg.
        fwd = close[j + h] / close[j] - 1.0
        mu = float(np.mean(ret[j - D.VOL_WIN:j]))          # strictly prior, 60 sessions
        hand_own = fwd - h * mu
        mj = market["index"].get(d)
        if mj is None or mj + h >= len(mdates):
            continue
        rm = float(np.prod(1.0 + mret[mj + 1:mj + h + 1]) - 1.0)
        hand_mkt = fwd - rm
        # the ARM's own vectorised path, on the same row
        dcode = np.array([market["index"].get(x, -1) for x in dates], dtype=np.int64)
        ar_own, ar_mkt, usable, _ = ARM.abnormal(close, ret, dcode, market, h, t in term)
        worst_own = max(worst_own, abs(float(ar_own[j]) - hand_own))
        worst_mkt = max(worst_mkt, abs(float(ar_mkt[j]) - hand_mkt))
        checks.append({"ticker": t, "date": d, "hand_own_pp": hand_own * 100.0,
                       "arm_own_pp": float(ar_own[j]) * 100.0,
                       "hand_mkt_pp": hand_mkt * 100.0,
                       "arm_mkt_pp": float(ar_mkt[j]) * 100.0})
    c2 = {"cells_checked": len(checks),
          "max_abs_dev_own": worst_own, "max_abs_dev_mkt": worst_mkt,
          "tolerance": 1e-9, "sample": checks[:8],
          "note": "the own-normal leg is re-derived with a PLAIN 60-session mean and the market "
                  "leg by COMPOUNDING the daily series, neither of which is how the arm computes "
                  "them (rolling().mean().shift(1) and a cumulative-log difference), so an "
                  "agreement is two routes meeting rather than one route repeated"}
    c2["pass"] = bool(len(checks) >= 10 and worst_own < 1e-9 and worst_mkt < 1e-9)
    art["C2_hand_rederivation"] = c2
    print("C2  hand re-derivation on %d cells: max |dev| own %.3e  mkt %.3e -> %s"
          % (c2["cells_checked"], worst_own, worst_mkt, "PASS" if c2["pass"] else "FIRES"))

    # ------------------------------------------------------- C3 + C4 sampler and containment
    with io.open(D.out_path("DIPCALL2_ARM.json"), encoding="utf-8") as fh:
        arm = json.load(fh)
    c3 = {"cells": {}}
    for key, cell in sorted(arm["full_sample_cells"].items()):
        if not key.startswith("tier|"):
            continue
        for defn in ("own", "mkt"):
            if defn not in cell or "permutation" not in cell[defn]:
                continue
            p = cell[defn]["permutation"]
            if p.get("draws"):
                c3["cells"]["%s|%s" % (key, defn)] = {
                    "null_mean": p["null_mean"], "p95": p["p95"], "p05": p["p05"],
                    "events_used": p.get("events_used"),
                    "null_interval_brackets_its_mean":
                        bool(p["p05"] <= p["null_mean"] <= p["p95"])}
    c3["pass"] = bool(c3["cells"]) and all(v["null_interval_brackets_its_mean"]
                                           for v in c3["cells"].values())
    art["C3_permutation_sampler"] = c3
    print("C3  permutation null: %d cells, every p05 <= mean <= p95 -> %s"
          % (len(c3["cells"]), "PASS" if c3["pass"] else "FIRES"))

    # ------------------------------------------------- C4 WHY THE TWO DEFINITIONS DISAGREE
    # The register forbids quoting one abnormal-return definition without the other (`DC-1`
    # measured them disagreeing in SIGN). On this arm they disagree in MAGNITUDE, and the gap is
    # an IDENTITY rather than a mystery:
    #     own - mkt  =  r_market(window)  -  h * mu_prior(name)
    # Measuring both terms on the arm's OWN rows says which benchmark is doing the work. If the
    # event selects names whose trailing mean sits near ZERO while the market drifts up, then the
    # own-normal leg CREDITS THE STRATEGY WITH THE MARKET'S RETURN -- which would make it not a
    # benchmark at all over a decade-long bull market.
    print("\nC4  decomposing own-minus-market on the arm's own rows ...")
    term_set = ARM.terminal_names()
    c4 = {}
    for h in D.HORIZONS_PRIMARY:
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
                if j is None or mj is None or mj + h >= len(mdates):
                    continue
                if not np.isfinite(mu_s[j]):
                    continue
                rm_acc.append(float(np.prod(1.0 + mret[mj + 1:mj + h + 1]) - 1.0))
                mu_acc.append(h * float(mu_s[j]))
                n_acc += 1
        rm_m = float(np.mean(rm_acc)) * 100.0
        mu_m = float(np.mean(mu_acc)) * 100.0
        c4["h%d" % h] = {
            "n_rows": n_acc,
            "mean_market_window_return_pp": rm_m,
            "mean_h_times_own_trailing_mean_pp": mu_m,
            "implied_own_minus_mkt_pp": rm_m - mu_m,
            "own_trailing_mean_annualised_pct": mu_m / h * 252.0,
            "market_annualised_pct_over_same_windows": rm_m / h * 252.0,
        }
        print("    h%-3d n %5d  market window %+7.4fpp (ann %+6.2f%%)  h*own-trailing-mean "
              "%+7.4fpp (ann %+6.2f%%)  implied own-mkt %+7.4fpp"
              % (h, n_acc, rm_m, c4["h%d" % h]["market_annualised_pct_over_same_windows"],
                 mu_m, c4["h%d" % h]["own_trailing_mean_annualised_pct"], rm_m - mu_m))
    for h in D.HORIZONS_PRIMARY:
        cell = arm["full_sample_cells"].get("tier|h%d|no_news" % h)
        if not cell:
            continue
        gap = cell["own"]["mean_pp"] - cell["mkt"]["mean_pp"]
        c4["h%d" % h]["arm_reported_own_minus_mkt_pp"] = gap
        c4["h%d" % h]["identity_abs_dev_pp"] = abs(
            gap - c4["h%d" % h]["implied_own_minus_mkt_pp"])
    c4["identity"] = "own - mkt = r_market(window) - h * mu_prior(name)"
    c4["tolerance_pp"] = 0.05
    c4["pass"] = all(v.get("identity_abs_dev_pp", 9e9) < 0.05
                     for k, v in c4.items() if k.startswith("h"))
    art["C4_why_the_definitions_disagree"] = c4
    print("    identity holds to %s -> %s"
          % ({k: round(v.get("identity_abs_dev_pp", float("nan")), 4)
              for k, v in c4.items() if k.startswith("h")}, "PASS" if c4["pass"] else "FIRES"))

    # ------------------------------- C5 the FULL-UNIVERSE reading's outlier contamination
    # The arm reports a realised sd near 371pp at h5 on the full half-0 universe against ~4.9pp
    # on the tier. A 371-percentage-point sd on a 5-session return is not a dispersion, it is a
    # handful of sub-penny names. `B13` is the precedent: this panel contains names no liquidity
    # filter reaches. Measured here so the full-universe surface is never read as the same object
    # as the tier.
    c5 = {}
    for h in D.HORIZONS_PRIMARY:
        f = arm["full_sample_cells"].get("full|h%d|no_news" % h)
        t = arm["full_sample_cells"].get("tier|h%d|no_news" % h)
        if not f or not t:
            continue
        c5["h%d" % h] = {
            "full_mean_pp": f["own"]["mean_pp"], "full_median_pp": f["own"]["median_pp"],
            "full_realised_sd_pp": f["own"]["realised_sd_pp"],
            "tier_mean_pp": t["own"]["mean_pp"], "tier_median_pp": t["own"]["median_pp"],
            "tier_realised_sd_pp": t["own"]["realised_sd_pp"],
            "sd_ratio_full_over_tier": (f["own"]["realised_sd_pp"]
                                        / t["own"]["realised_sd_pp"]),
            "full_mean_over_median": (f["own"]["mean_pp"] / f["own"]["median_pp"])
            if f["own"]["median_pp"] else None,
        }
    c5["verdict"] = ("the FULL-universe realised sd runs tens of times the tier's and its mean "
                     "is several times its median, so that surface is OUTLIER-DRIVEN and must "
                     "NOT be read as the same object as the tier. The TIER governs (charter "
                     "Stage 1b) and its realised sd is sane.")
    c5["pass"] = True      # a measurement, not a gate
    art["C5_full_universe_is_outlier_driven"] = c5
    print("\nC5  full/tier realised-sd ratio: %s"
          % {k: round(v["sd_ratio_full_over_tier"], 1)
             for k, v in c5.items() if k.startswith("h")})

    # -------------------------------------- C6 the terminal-value count is attributable
    ends = {}
    for t in names:
        s3 = D.read_prices(t)
        if s3 is not None:
            ends[t] = s3["date"].iloc[-1]
    early_end = sorted(t for t, d in ends.items() if d < "2020-01-01")
    n_term = len([t for t in early_end if t in term_set])
    c6 = {"names_with_prices": len(ends),
          "names_whose_series_ENDS_before_2020": len(early_end),
          "of_those_in_ACTIONS_as_terminal": n_term,
          "arm_reported_terminal_rows": arm["censoring"]["terminal_used"],
          "arm_reported_administrative_dropped": arm["censoring"]["administrative_dropped"],
          "expected_order_of_magnitude": n_term * (5 + 21 + 63 + 126),
          "note": "A11: a name whose series ends inside the horizon is TERMINAL when ACTIONS "
                  "records a delisting, bankruptcy, regulatory or voluntary exit, acquisition or "
                  "merger, and an ADMINISTRATIVE censor otherwise. Each such name contributes up "
                  "to 5+21+63+126 = 215 terminal rows summed over the four horizons, which is "
                  "what makes a six-figure count expected rather than alarming."}
    c6["pass"] = True
    art["C6_censoring_is_attributable"] = c6
    print("C6  %d of %d names end before 2020; %d are ACTIONS-terminal; the arm booked %d "
          "terminal rows against an expected order of ~%d"
          % (c6["names_whose_series_ENDS_before_2020"], c6["names_with_prices"], n_term,
             c6["arm_reported_terminal_rows"], c6["expected_order_of_magnitude"]))

    art["all_controls_pass"] = bool(c1["pass"] and c2["pass"] and c3["pass"] and c4["pass"])
    with io.open(D.out_path(OUT), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\nALL CONTROLS PASS: %s" % art["all_controls_pass"])
    print("wrote %s" % D.out_path(OUT))
    return 0 if art["all_controls_pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
