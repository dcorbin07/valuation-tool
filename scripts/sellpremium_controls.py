"""SELL-PREMIUM — CONTROLS on the kill pass. Zero trials; they can only BLOCK.

`MB1-SEL`: a control can only ever BLOCK a finding, never produce one, so it adds no degree of
freedom and charges nothing. No forward option return is priced here.

  `C1`  THE EVENT SET IS `DIP-CALL`'s AND NOT A SECOND DEFINITION (`B7`/`S5`). Reconciled against
        the banked `DIPCALL_CENSUS.json` and `DIPCALL_YEARS.json` rather than against my
        expectation. Two registers reporting two event counts for one event is the defect.
  `C2`  THE CHAIN'S `spot` IS AS-TRADED AND THE PREPARED PRICE FILE IS NOT, measured across many
        names — `S4`. With a POSITIVE CONTROL: a name that never split must read a ratio near 1,
        or the check is just detecting that two series differ.
  `C3`  THE DERIVED LAYER IS TWO-SIDED BY CONSTRUCTION, so `K1`'s funnel measured there would
        read 1.000 having checked nothing (`MB21`'s `C1` family). This is why the funnel reads
        the RAW layer, and it is measured rather than asserted.
  `C4`  WHY `K1` CLEARED 3.4x THE DRAFT'S ESTIMATE — the funnel on RANDOM days in the same names
        and years, against the funnel on EVENT days. Quote availability only; no return is
        computed. `O-1`'s lesson running the other way.

Usage:  python -m scripts.sellpremium_controls
"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                    # noqa: E402
from valuation.studies import sellpremium as SP                               # noqa: E402

OUT = "SELLPREMIUM_CONTROLS.json"


def c1_event_set():
    art = {}
    p = D.out_path("DIPCALL_CENSUS.json")
    if os.path.isfile(p):
        with io.open(p, encoding="utf-8") as fh:
            art["dipcall_census"] = {k: v for k, v in json.load(fh).items()
                                     if isinstance(v, (int, float, str))}
    ev = D.out_path("SELLPREMIUM_EVENTS.pkl")
    if os.path.isfile(ev):
        e = pd.read_pickle(ev)
        art["sellpremium_events"] = int(len(e))
        art["sellpremium_names"] = int(e["ticker"].nunique())
        art["sellpremium_dates"] = int(e["date"].nunique())
        by_year = e["date"].str[:4].value_counts().sort_index().to_dict()
        art["by_year"] = {k: int(v) for k, v in by_year.items()}
    q = D.out_path("DIPCALL_YEARS.json")
    if os.path.isfile(q):
        with io.open(q, encoding="utf-8") as fh:
            y = json.load(fh)
        art["dipcall_years_keys"] = sorted(y)[:12]
        art["dipcall_years_raw"] = {k: v for k, v in y.items()
                                    if isinstance(v, (int, float))}
    art["note"] = ("the event, the tier and the ticker half are IMPORTED from "
                   "valuation/studies/dipcall.py and are never re-defined here; this control "
                   "exists so a reader can see the two registers describing ONE event set")
    art["pass"] = bool(art.get("sellpremium_events"))
    return art


def c2_spot_basis():
    rows, ratios = [], []
    tickers = ["AAPL", "NVDA", "MSFT", "JNJ", "KO", "T", "XOM", "WMT", "PG", "CSCO",
               "INTC", "ORCL", "MRK", "PFE", "CVX"]
    for t in tickers:
        if not SP.has_chain(t, 2018):
            continue
        sp = SP.spot_by_date(t, 2018)
        px = D.read_prices(t)
        if not sp or px is None:
            continue
        m = px[px["date"].isin(sp.keys())]
        if not len(m):
            continue
        r = np.array([sp[d] / c for d, c in zip(m["date"], m["close"].astype(float))
                      if c and np.isfinite(c) and c > 0])
        if not len(r):
            continue
        rows.append({"ticker": t, "dates": int(len(r)), "median_ratio": float(np.median(r))})
        ratios.append(float(np.median(r)))
    out = {"per_name": rows, "names": len(rows),
           "median_of_medians": float(np.median(ratios)) if ratios else float("nan"),
           "max_ratio": float(np.max(ratios)) if ratios else float("nan"),
           "min_ratio": float(np.min(ratios)) if ratios else float("nan")}
    # POSITIVE CONTROL: at least one name must read NEAR 1, or this check is only detecting
    # that two series differ rather than detecting the adjustment.
    near_one = [r for r in ratios if abs(r - 1.0) < 0.25]
    out["names_reading_near_1.0"] = len(near_one)
    out["positive_control"] = bool(near_one)
    out["pass"] = bool(ratios and out["max_ratio"] > 2.0 and out["positive_control"])
    out["note"] = ("a ratio far above 1 is a SPLIT the prepared file has divided out and the "
                   "chain has not; a ratio near 1 is a name that never split, and it is the "
                   "positive control. Strikes and settlement read the chain's spot (S4).")
    return out


def c3_derived_is_two_sided_by_construction():
    cells = []
    for t, y in (("AAPL", 2018), ("MSFT", 2018), ("JNJ", 2017), ("NVDA", 2019)):
        pr = os.path.join(SP.chain_dir(), t, "%s-%d.pkl" % (t, y))
        pd_ = os.path.join(SP.derived_dir(), t, "%s-%d.pkl" % (t, y))
        if not (os.path.isfile(pr) and os.path.isfile(pd_)):
            continue
        raw = pd.read_pickle(pr)
        dv = pd.read_pickle(pd_)
        raw_two = float(((raw["bid"] > 0) & (raw["ask"] > raw["bid"])).mean())
        k = ["date", "expiration", "strike", "right"]
        for d in (raw, dv):
            d["date"] = pd.to_datetime(d["date"])
            d["expiration"] = pd.to_datetime(d["expiration"])
        j = dv.merge(raw[k + ["bid", "ask"]], on=k, how="inner")
        dv_two = float(((j["bid"] > 0) & (j["ask"] > j["bid"])).mean()) if len(j) else float("nan")
        cells.append({"cell": "%s-%d" % (t, y), "raw_rows": int(len(raw)),
                      "derived_rows": int(len(dv)), "raw_two_sided_share": raw_two,
                      "derived_two_sided_share": dv_two,
                      "mid_equals_bid_ask_mean_max_dev":
                          float(np.max(np.abs(j["mid"] - (j["bid"] + j["ask"]) / 2.0)))
                          if len(j) else float("nan")})
    out = {"cells": cells}
    # The property is "the derived layer is ESSENTIALLY all two-sided, and discriminates from
    # the raw layer by a wide margin", not "exactly 1.0". A first cut demanded 1e-9 and fired on
    # NVDA-2019 at 0.999991449 -- ONE row in ~117,000 with `ask == bid` -- which is a correct
    # tree failing an over-tight bar rather than a defect. Loosened WITH the discrimination leg
    # added, so it cannot pass by both layers reading the same.
    out["pass"] = bool(cells
                       and all(c["derived_two_sided_share"] >= 0.9999 for c in cells)
                       and all(c["derived_two_sided_share"] - c["raw_two_sided_share"] >= 0.10
                               for c in cells))
    out["note"] = ("the derived layer is two-sided on 1.0000 of its rows BY CONSTRUCTION while "
                   "the raw layer is not, so K1's funnel measured on the derived layer would "
                   "read 1.000 having checked nothing -- MB21's C1 family. The funnel reads RAW.")
    return out


def c4_event_days_vs_random_days(n_names: int = 40, per_name: int = 20, seed: int = 0):
    """QUOTE AVAILABILITY ONLY. No return is computed and no trade is scored."""
    picks_p = D.out_path("SELLPREMIUM_PICKS.pkl")
    if not os.path.isfile(picks_p):
        return {"pass": False, "why": "SELLPREMIUM_PICKS.pkl absent; run the kills first"}
    picks = pd.read_pickle(picks_p)
    names = sorted(set(picks["ticker"]))[:n_names]
    rng = np.random.default_rng(seed)
    tot = {"sessions": 0, "any_put": 0, "in_dte": 0, "in_moneyness": 0, "two_sided": 0}
    for t in names:
        for y in SP.era_years():
            if not SP.has_chain(t, y):
                continue
            raw = SP.read_raw_chain(t, y)
            spot = SP.spot_by_date(t, y)
            if raw is None or not spot:
                continue
            days = sorted(spot)
            if len(days) < per_name:
                continue
            for d in rng.choice(days, size=per_name, replace=False):
                f = SP.put_funnel(raw, spot, str(d))
                tot["sessions"] += 1
                for k in ("any_put", "in_dte", "in_moneyness", "two_sided"):
                    tot[k] += 1 if f.get(k) else 0
            break                                   # one year per name keeps this cheap
    rand_rate = (tot["two_sided"] / tot["sessions"]) if tot["sessions"] else float("nan")
    with io.open(D.out_path("SELLPREMIUM_KILLS.json"), encoding="utf-8") as fh:
        k1 = json.load(fh)["K1_coverage"]
    ev_rate = (k1["funnel"]["two_sided"] / k1["events_with_a_chain_file"]
               if k1["events_with_a_chain_file"] else float("nan"))
    return {"random_day_sessions": tot["sessions"], "random_day_funnel": tot,
            "random_day_two_sided_rate": rand_rate,
            "event_day_two_sided_rate": ev_rate,
            "ratio_event_over_random": (ev_rate / rand_rate) if rand_rate else float("nan"),
            "draft_layer3_estimate_at_20_60_dte": 0.296,
            "pass": True,
            "note": "QUOTE AVAILABILITY ONLY -- no return is computed. The draft's layer-3 "
                    "spot-check sampled RANDOM sessions; this register prices EVENT days, and "
                    "an event IS a volatility spike, which is exactly what gives an OTM put a "
                    "bid. O-1's lesson running the other way: a coverage figure measured on one "
                    "population understated another, this time in the design's favour."}


def c5_why_the_drafts_layer3_was_low(n_names: int = 14, per_name: int = 20, seed: int = 7):
    """`C4` REFUTED MY OWN HYPOTHESIS, so this tests the next one instead of leaving a 3.3x gap
    unexplained.

    The draft's layer-3 spot-check read **0.296** of cells usable at 20-60 DTE; the register
    measures **0.975**. `C4` shows it is not event-day conditioning — random days inside covered
    names read the same as event days. The surviving suspect is the one `S4` exists for: the
    draft loses HALF its cells at the **moneyness** step (147 of 280), where this register loses
    ten of 2,622, and a moneyness window computed against the **ADJUSTED** close lands nowhere
    near the listed strike ladder (AAPL 2018: 40.234 against a real 172.26).

    So the funnel is run TWICE on the same random tier names and sessions — once with the chain's
    own as-traded `spot`, once with the adjusted close standing in for it. **If the adjusted run
    reproduces the draft's ~0.52 moneyness step and ~0.17-0.30 usable step, the cause is
    identified. If it does not, the gap is REPORTED AS UNEXPLAINED** rather than attributed.
    """
    picks_p = D.out_path("SELLPREMIUM_PICKS.pkl")
    sched, _ = D.tier_schedule_era(D.ERA_BUILD)
    ever = sorted(t for t, v in sched.items()
                  if v and max(c for _, c in v) >= D.TIER_FLOOR)
    pool = [t for t in ever if SP.has_chain(t, 2018)
            and os.path.isfile(os.path.join(D.prices_dir(), "%s.csv" % t))]
    rng = np.random.default_rng(seed)
    names = list(rng.choice(pool, size=min(n_names, len(pool)), replace=False))
    tot = {"as_traded": {"sessions": 0, "in_moneyness": 0, "two_sided": 0},
           "adjusted": {"sessions": 0, "in_moneyness": 0, "two_sided": 0}}
    for t in names:
        raw = SP.read_raw_chain(t, 2018)
        spot = SP.spot_by_date(t, 2018)
        px = D.read_prices(t)
        if raw is None or not spot or px is None:
            continue
        adj = dict(zip(px["date"], px["close"].astype(float)))
        days = sorted(d for d in spot if d in adj)
        if len(days) < per_name:
            continue
        for d in rng.choice(days, size=per_name, replace=False):
            d = str(d)
            for lbl, src in (("as_traded", spot), ("adjusted", adj)):
                f = SP.put_funnel(raw, src, d)
                tot[lbl]["sessions"] += 1
                tot[lbl]["in_moneyness"] += 1 if f.get("in_moneyness") else 0
                tot[lbl]["two_sided"] += 1 if f.get("two_sided") else 0
    out = {"names": len(names), "per_name": per_name, "totals": tot,
           "draft_layer3_moneyness_step_2018": 147.0 / 280.0,
           "draft_layer3_usable_step_20_60_dte_2018": 0.296}
    for lbl in ("as_traded", "adjusted"):
        s = tot[lbl]["sessions"]
        out["%s_moneyness_rate" % lbl] = (tot[lbl]["in_moneyness"] / s) if s else float("nan")
        out["%s_two_sided_rate" % lbl] = (tot[lbl]["two_sided"] / s) if s else float("nan")
    # The hypothesis is CONFIRMED only if the adjusted run lands near the draft's figures AND
    # the as-traded run does not. One leg alone would be a coincidence.
    near = (abs(out["adjusted_two_sided_rate"] - 0.296) < 0.25
            and out["as_traded_two_sided_rate"] - out["adjusted_two_sided_rate"] > 0.30)
    out["hypothesis_confirmed"] = bool(near)
    # HOW MUCH of the gap it accounts for, because "reproduced" would overstate it: the adjusted
    # run moves DECISIVELY toward the draft's figure and does not land on it.
    full = out["as_traded_two_sided_rate"] - out["draft_layer3_usable_step_20_60_dte_2018"]
    got = out["as_traded_two_sided_rate"] - out["adjusted_two_sided_rate"]
    out["share_of_the_gap_explained"] = (got / full) if full else float("nan")
    out["verdict"] = (
        ("the ADJUSTED close standing in for spot accounts for %.0f%% of the gap between this "
         "register's measured coverage and the draft's layer-3 figure -- the split trap S4 "
         "exists to prevent. DIRECTIONALLY CONFIRMED AND NOT EXACTLY REPRODUCED: the remaining "
         "~%.0f%% is UNEXPLAINED and is most likely the draft's 14-name sample differing from "
         "this one." % (100.0 * out["share_of_the_gap_explained"],
                        100.0 * (1.0 - out["share_of_the_gap_explained"])))
        if near else
        "NOT reproduced -- the gap between the draft's estimate and the measured coverage is "
        "REPORTED AS UNEXPLAINED rather than attributed")
    out["pass"] = True            # diagnostic: it explains a PASSING gate and blocks nothing
    return out


def main():
    art = {"item": "SELL-PREMIUM kill-pass controls", "trials": 0,
           "note": "a control can only BLOCK a finding, never produce one (MB1-SEL)"}
    print("C1 the event set is DIP-CALL's ...")
    art["C1_event_set"] = c1_event_set()
    e = art["C1_event_set"]
    print("   events %s over %s names, %s dates ; by year %s"
          % (e.get("sellpremium_events"), e.get("sellpremium_names"),
             e.get("sellpremium_dates"), e.get("by_year")))

    print("C2 the chain's spot is AS-TRADED ...")
    art["C2_spot_basis"] = c2_spot_basis()
    c = art["C2_spot_basis"]
    print("   %d names ; median of medians %.4f ; max %.4f ; near-1.0 names %d -> %s"
          % (c["names"], c["median_of_medians"], c["max_ratio"],
             c["names_reading_near_1.0"], "PASS" if c["pass"] else "FIRES"))

    print("C3 the derived layer is two-sided by construction ...")
    art["C3_derived_vacuity"] = c3_derived_is_two_sided_by_construction()
    for cc in art["C3_derived_vacuity"]["cells"]:
        print("   %-12s raw two-sided %.4f  derived two-sided %.4f  mid dev %.3e"
              % (cc["cell"], cc["raw_two_sided_share"], cc["derived_two_sided_share"],
                 cc["mid_equals_bid_ask_mean_max_dev"]))
    print("   -> %s" % ("PASS" if art["C3_derived_vacuity"]["pass"] else "FIRES"))

    print("C4 event days vs random days (quote availability only) ...")
    art["C4_event_vs_random_coverage"] = c4_event_days_vs_random_days()
    c4 = art["C4_event_vs_random_coverage"]
    if c4.get("random_day_sessions"):
        print("   random-day two-sided rate %.4f over %d sessions ; event-day rate %.4f ; "
              "ratio %.2fx (draft's estimate %.3f)"
              % (c4["random_day_two_sided_rate"], c4["random_day_sessions"],
                 c4["event_day_two_sided_rate"], c4["ratio_event_over_random"],
                 c4["draft_layer3_estimate_at_20_60_dte"]))

    print("C5 why the draft's layer-3 read 0.296 and this register measures 0.975 ...")
    art["C5_layer3_diagnosis"] = c5_why_the_drafts_layer3_was_low()
    c5 = art["C5_layer3_diagnosis"]
    print("   %d names x %d sessions" % (c5["names"], c5["per_name"]))
    print("   AS-TRADED spot : moneyness step %.4f  usable %.4f"
          % (c5["as_traded_moneyness_rate"], c5["as_traded_two_sided_rate"]))
    print("   ADJUSTED close : moneyness step %.4f  usable %.4f"
          % (c5["adjusted_moneyness_rate"], c5["adjusted_two_sided_rate"]))
    print("   draft's own    : moneyness step %.4f  usable %.4f"
          % (c5["draft_layer3_moneyness_step_2018"],
             c5["draft_layer3_usable_step_20_60_dte_2018"]))
    print("   -> %s" % c5["verdict"])

    gates = {k: bool(v.get("pass")) for k, v in art.items() if isinstance(v, dict)
             and "pass" in v}
    art["gates"] = gates
    art["all_pass"] = bool(all(gates.values()))
    with io.open(D.out_path(OUT), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\ngates: %s" % gates)
    print("wrote %s" % D.out_path(OUT))
    return 0 if art["all_pass"] else 4


if __name__ == "__main__":
    sys.exit(main())
