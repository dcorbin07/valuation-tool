"""SELL-PREMIUM-2 — the pre-outcome kills. Zero trials; they can only BLOCK.

`PREREG_sellpremium2.md`, committed ALONE at `541e466`; 4 options trials booked at `b376ff7`
BEFORE this file existed.

**RUN AND READ IN THEIR OWN PASS, BEFORE ANY ARM** (`O10`). `sellpremium2_arm.py` REFUSES without
a passing artifact.

  `K1`  COVERAGE, re-measured on THIS register's own strike rule (`T8`, `O-1`'s lesson). Floors
        unchanged and unrelaxed: >= 400 priceable events AND >= 150 distinct covered event days.
  `K3`  THE CRASH STRESS, bar **6.0 UNRELAXED**, synthetic single-name row **RETAINED**, computed
        on the register's OWN measured net income at its OWN picks and never from the draft's
        mid-based table (`T5`, void condition 4).
  `C-K3`  **GATING**: this register's own `K3` code path, run at the PREDECESSOR's 0.90-moneyness
        picks, must reproduce **8.900816**. If it does not, the two registers' `K3` figures are
        not the same statistic and the comparison that justifies this successor is withdrawn.
  `C-EV`  **GATING** (`T6`): the event set is RE-DERIVED from `dipcall` and must equal the banked
        `SELLPREMIUM_EVENTS.pkl` exactly. A register that reads its predecessor's pickle cannot
        tell a shared definition from a shared file.

Usage:  python -m scripts.sellpremium2_kills
"""
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                    # noqa: E402
from valuation.studies import sellpremium as SP                               # noqa: E402
from scripts import sellpremium_kills as SP1                                  # noqa: E402

PREFIX = "SELLPREMIUM2"
PREDECESSOR_K3_YEARS = 8.900816          # SELL-PREMIUM's landed figure; C-K3 must reproduce it


def k3_from_picks(picks: pd.DataFrame, label: str) -> dict:
    """`K3`, with EVERY part identical to the predecessor's so the two are commensurable (`T5`).

    median premium/strike at the PICKED contract, median DTE, turns = 252/median DTE, loss
    `(x - (1 - m))/m` at the median moneyness, the same 6.0 bar and the same synthetic row.
    """
    if picks is None or not len(picks):
        return {"label": label, "pass": False, "why": "no picks"}
    spy = D.read_prices("SPY")
    worst = {}
    for y in (2016, 2017, 2018, 2019, 2020, 2022, 2025):
        s = spy[(spy["date"] >= "%d-01-01" % y) & (spy["date"] <= "%d-12-31" % y)]
        if len(s) > 32:
            worst["%d" % y] = SP.worst_rolling(s["close"].to_numpy(dtype=float), 32)
    mon = float(np.median(picks["moneyness"]))
    prem = float(np.median(picks["bid"].astype(float) / picks["strike"].astype(float)))
    dte = float(np.median(picks["dte"]))
    turns = 252.0 / dte
    tab = {}
    for nm, fall in worst.items():
        if np.isfinite(fall):
            tab[nm] = {"worst_32_session_return": fall,
                       "loss_on_secured_cash": max(0.0, (-fall - (1.0 - mon)) / mon),
                       "years_of_premium": SP.years_of_premium(-fall, mon, prem, turns)}
    w = min([v for v in worst.values() if np.isfinite(v)] or [float("nan")])
    tab["single_name_at_1.4x_the_worst_index_episode"] = {
        "worst_32_session_return": w * 1.4,
        "loss_on_secured_cash": max(0.0, (-w * 1.4 - (1.0 - mon)) / mon),
        "years_of_premium": SP.years_of_premium(-w * 1.4, mon, prem, turns)}
    vals = [v["years_of_premium"] for v in tab.values()
            if np.isfinite(v.get("years_of_premium", float("nan")))]
    worst_years = max(vals) if vals else float("inf")
    return {"label": label, "n_picks": int(len(picks)), "median_moneyness": mon,
            "median_premium_frac_of_strike": prem, "median_dte": dte, "turns_per_year": turns,
            "annual_income_frac_of_secured_cash": prem * turns,
            "table": tab, "worst_years_of_premium": worst_years,
            "bar": SP.K3_MAX_YEARS_OF_PREMIUM,
            "pass": bool(np.isfinite(worst_years)
                         and worst_years <= SP.K3_MAX_YEARS_OF_PREMIUM)}


def main():
    t0 = time.time()
    print("SELL-PREMIUM-2 kills  delta target %.2f  DTE %s  moneyness band for the delta rule: %s"
          % (SP.DELTA_TARGET, SP.DTE_BAND, SP.DELTA_MON_BAND))

    # ------------------------------------------------- C-EV: the event set, re-derived (T6)
    print("\npass 1 - the event set, RE-DERIVED from dipcall (B7/T6) ...")
    ev, names = SP1.build_events()
    banked_p = D.out_path("SELLPREMIUM_EVENTS.pkl")
    c_ev = {"re_derived": int(len(ev)), "names": int(ev["ticker"].nunique()),
            "dates": int(ev["date"].nunique())}
    if os.path.isfile(banked_p):
        b = pd.read_pickle(banked_p)
        a_keys = set(zip(ev["ticker"].astype(str), ev["date"].astype(str)))
        b_keys = set(zip(b["ticker"].astype(str), b["date"].astype(str)))
        c_ev.update({"banked": int(len(b)), "identical": bool(a_keys == b_keys),
                     "only_here": len(a_keys - b_keys), "only_banked": len(b_keys - a_keys)})
    else:
        c_ev.update({"banked": None, "identical": None})
    c_ev["pass"] = bool(c_ev.get("identical") is True)
    print("  %d events over %d names / %d dates ; identical to the banked set: %s"
          % (c_ev["re_derived"], c_ev["names"], c_ev["dates"], c_ev.get("identical")))

    # -------------------------------------- pass 2: ONE chain read, TWO picks per event (T7)
    print("\npass 2 - pricing BOTH rules on the SAME chain read (T7) ...")
    agg = {"events": 0, "no_chain_file": 0, "no_spot": 0, "any_put": 0, "in_dte": 0,
           "two_sided_noband": 0, "no_delta": 0}
    d25, d90 = [], []
    for n, (t, g) in enumerate(ev.groupby("ticker", sort=True)):
        cache = {}
        for d in sorted(set(g["date"])):
            y = int(d[:4])
            if y not in cache:
                if not SP.has_chain(t, y):
                    cache[y] = None
                else:
                    raw = SP.read_raw_chain(t, y)
                    cache[y] = (SP.index_by_date(raw), SP.spot_by_date(t, y),
                                SP.greeks_by_key(t, y))
            agg["events"] += 1
            pack = cache[y]
            if pack is None:
                agg["no_chain_file"] += 1
                continue
            byd, spot, grk = pack
            day = byd.get(d)
            if day is None:
                continue
            # ONE funnel, NO moneyness band -- the 0.90 pick is derived by filtering the same
            # candidate set, so the two rules see a provably identical row set.
            f = SP.put_funnel(None, spot, d, mon_band=None, day=day)
            if f.get("no_spot"):
                agg["no_spot"] += 1
                continue
            for k in ("any_put", "in_dte"):
                agg[k] += 1 if f[k] else 0
            agg["two_sided_noband"] += 1 if f["two_sided"] else 0
            c = f["cands"]
            if c is None or not len(c):
                continue
            r25 = SP.pick_put_by_delta(c, grk, d)
            agg["no_delta"] += r25["no_delta"]
            if r25["pick"]:
                r25["pick"].update({"ticker": t, "date": d, "year": y})
                d25.append(r25["pick"])
            inband = c[(c["moneyness"] >= SP.MONEYNESS_BAND[0])
                       & (c["moneyness"] <= SP.MONEYNESS_BAND[1])]
            p90 = SP.pick_put(inband)
            if p90:
                p90.update({"ticker": t, "date": d, "year": y})
                d90.append(p90)
        if n and n % 50 == 0:
            print("    %d names priced, %.0fs" % (n, time.time() - t0))
    p25 = pd.DataFrame(d25)
    p90 = pd.DataFrame(d90)
    print("  25-delta picks %d ; 0.90-moneyness picks %d ; join loss (no delta) %d rows"
          % (len(p25), len(p90), agg["no_delta"]))

    # ----------------------------------------------------------------------------------- K1
    covered_days = int(p25["date"].nunique()) if len(p25) else 0
    k1 = {"events_total": int(len(ev)), "funnel": agg,
          "priceable_events": int(len(p25)), "covered_event_days": covered_days,
          "covered_names": int(p25["ticker"].nunique()) if len(p25) else 0,
          "floor_events": SP.K1_MIN_EVENTS, "floor_covered_days": SP.K1_MIN_COVERED_DAYS,
          "predecessor_priceable_events": 2557, "predecessor_covered_days": 612,
          "note": "re-measured on THIS register's own strike rule (T8). The predecessor's "
                  "figures are a DIFFERENT filter - band-then-pick against delta-search - and "
                  "the two coverages may not be quoted against each other without saying so."}
    k1["pass"] = bool(len(p25) >= SP.K1_MIN_EVENTS
                      and covered_days >= SP.K1_MIN_COVERED_DAYS)
    print("  K1 priceable %d (floor %d) ; covered days %d (floor %d) -> %s"
          % (len(p25), SP.K1_MIN_EVENTS, covered_days, SP.K1_MIN_COVERED_DAYS,
             "PASS" if k1["pass"] else "FIRES"))

    # ---------------------------------------------------- T3's reported cost of the old band
    band = {}
    if len(p25):
        out = ((p25["moneyness"] < SP.MONEYNESS_BAND[0])
               | (p25["moneyness"] > SP.MONEYNESS_BAND[1]))
        band = {"share_outside_0.85_0.95": float(out.mean()),
                "n_outside": int(out.sum()),
                "moneyness_p05": float(np.percentile(p25["moneyness"], 5)),
                "moneyness_median": float(np.median(p25["moneyness"])),
                "moneyness_p95": float(np.percentile(p25["moneyness"], 95)),
                "delta_median": float(np.median(p25["delta"])),
                "delta_p05": float(np.percentile(p25["delta"], 5)),
                "delta_p95": float(np.percentile(p25["delta"], 95)),
                "note": "T3: the share the predecessor's 0.85-0.95 band would have DELETED from "
                        "a delta rule. Reported because widening a filter on a construction "
                        "argument before any arm runs is the opposite act from widening it "
                        "after seeing returns."}
        print("  T3 realised moneyness p05/med/p95 %.4f / %.4f / %.4f ; "
              "%.2f%% outside the old band ; median delta %.4f"
              % (band["moneyness_p05"], band["moneyness_median"], band["moneyness_p95"],
                 100 * band["share_outside_0.85_0.95"], band["delta_median"]))

    # --------------------------------------------------------------------- C-K3 then K3 (T5)
    print("\npass 3 - C-K3 (gating) then K3 ...")
    ck3 = k3_from_picks(p90, "predecessor 0.90-moneyness picks, THIS register's code path")
    ck3["expected_years"] = PREDECESSOR_K3_YEARS
    ck3["dev"] = abs(ck3.get("worst_years_of_premium", float("nan")) - PREDECESSOR_K3_YEARS)
    ck3["pass"] = bool(np.isfinite(ck3["dev"]) and ck3["dev"] < 0.02)
    print("  C-K3 reproduces the predecessor at %.6f against %.6f (dev %.6f) -> %s"
          % (ck3.get("worst_years_of_premium", float("nan")), PREDECESSOR_K3_YEARS,
             ck3["dev"], "PASS" if ck3["pass"] else "FIRES"))

    k3 = k3_from_picks(p25, "25-delta, this register's rule")
    k3["draft_forecast_at_20_delta"] = 5.64
    k3["executor_forecast_at_true_25_delta"] = 4.4385
    for nm, r in sorted(k3.get("table", {}).items(),
                        key=lambda kv: -kv[1]["years_of_premium"]):
        print("    %-44s fall %+7.2f%%  loss %6.2f%%  years %6.2f"
              % (nm, 100 * r["worst_32_session_return"],
                 100 * r["loss_on_secured_cash"], r["years_of_premium"]))
    print("  K3 income %.4f%%/yr (predecessor 4.4545%%) ; worst %.4f years against %.1f -> %s"
          % (100 * k3["annual_income_frac_of_secured_cash"], k3["worst_years_of_premium"],
             k3["bar"], "PASS" if k3["pass"] else "FIRES"))

    gates = {"C_EV_event_set": c_ev["pass"], "C_K3_reproduces_predecessor": ck3["pass"],
             "K1_coverage": k1["pass"], "K3_crash_stress": k3["pass"]}
    art = {"item": "SELL-PREMIUM-2 pre-outcome kills", "trials": 0,
           "register": "PREREG_sellpremium2.md committed ALONE at 541e466",
           "trials_booked_at": "b376ff7 (options 315 -> 319)",
           "delta_target": SP.DELTA_TARGET, "dte_band": list(SP.DTE_BAND),
           "moneyness_band_applied_to_the_delta_rule": SP.DELTA_MON_BAND,
           "C_EV_event_set": c_ev, "K1_coverage": k1, "T3_realised_moneyness": band,
           "C_K3_control": ck3, "K3_crash": k3,
           "gates": gates, "all_pass": bool(all(gates.values())),
           "note": "a control can only BLOCK a finding, never produce one (MB1-SEL)"}
    with io.open(D.out_path("%s_KILLS.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    if len(p25):
        p25.to_pickle(D.out_path("%s_PICKS25.pkl" % PREFIX))
    if len(p90):
        p90.to_pickle(D.out_path("%s_PICKS90.pkl" % PREFIX))
    print("\ngates: %s" % gates)
    print("wrote %s  (%.0fs)" % (D.out_path("%s_KILLS.json" % PREFIX), time.time() - t0))
    return 0 if art["all_pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
