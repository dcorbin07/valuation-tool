"""SELL-PREMIUM — THE FOUR FREE PRE-OUTCOME KILLS. Zero trials; they can only BLOCK.

`PREREG_sellpremium.md`, committed ALONE at `2e9fe7b`; 5 options trials booked at `907d924`
BEFORE this file existed.

**RUN AND READ IN THEIR OWN PASS, BEFORE ANY ARM.** `O10`'s process defect — *"C2 and the outcome
statistics were computed in the SAME pass, so it cannot be claimed the control was read before the
numbers"* — is not repeated: this is a separate invocation, its artifact is written first, and
`sellpremium_arm.py` REFUSES to run without it. Under `MB1-SEL` a control can only ever BLOCK a
finding, never produce one, so none of this charges a trial — and `K2` is a kill testing the
register's PREMISE rather than its hypothesis, which is `DC-1`'s shape and `DC-1` booked zero.

  `K1`  COVERAGE, on this arm's own population (`O-1`: a figure measured on one population and
        applied to another was ~17x wrong). Floors fixed in the draft and unrelaxed: >= 400
        priceable events AND >= 150 distinct covered event days.
  `K2`  THE PREMISE. Re-price `A3`'s own banked spread trades as NAKED puts held to expiry at the
        MID, by IV-rank band, restricted to 2016-2019. If the gradient PERSISTS the moneyness arm
        is withdrawn before it runs; if it FLATTENS, `A3`'s gradient was structure and cost.
  `K3`  THE MECHANICAL CRASH STRESS, on the register's MEASURED strike distribution. Kills if one
        crash costs worse than 6 years of premium.
  `K4`  AFFORDABILITY, with the skip reason recorded as its own field (`MB3`: the low-end failures
        are AFFORDABILITY, not ruin).

Usage:  python -m scripts.sellpremium_kills
"""
import io
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                    # noqa: E402
from valuation.studies import sellpremium as SP                               # noqa: E402

PREFIX = "SELLPREMIUM"


# ------------------------------------------------------------------------------- the event set
def build_events():
    """The event set, IMPORTED from `dipcall` and never re-defined (`B7`/`S5`).

    Build quadrant intersected with the options era: 2016-2019 x ticker half 0, point-in-time
    $10B tier at the event date. The event is detected on the ADJUSTED series (`S4`).
    """
    sched, _universe = D.tier_schedule_era(D.ERA_BUILD)
    ever = sorted(t for t, v in sched.items()
                  if v and max(c for _, c in v) >= D.TIER_FLOOR)
    names = [t for t in ever
             if os.path.isfile(os.path.join(D.prices_dir(), "%s.csv" % t))]
    rows, t0 = [], time.time()
    for i, t in enumerate(names):
        s = D.name_frame(t, sched.get(t, []), k=D.K_PRIMARY)
        if s is None:
            continue
        m = (s["event"].to_numpy() & s["tier"].to_numpy()
             & (s["date"] >= SP.ERA_LO).to_numpy() & (s["date"] <= SP.ERA_HI).to_numpy())
        if not m.any():
            continue
        for d in s["date"].to_numpy()[m]:
            rows.append({"ticker": t, "date": str(d)})
        if i and i % 150 == 0:
            print("    %d/%d names, %.0fs" % (i, len(names), time.time() - t0))
    ev = pd.DataFrame(rows)
    return ev, names


def price_events(ev: pd.DataFrame) -> pd.DataFrame:
    """`K1`'s funnel, applied to every event. The picked contract is banked so the arm never
    re-derives it — one selection, one definition."""
    agg = {"any_put": 0, "in_dte": 0, "in_moneyness": 0, "two_sided": 0,
           "no_chain_file": 0, "no_spot": 0, "events": 0}
    out, t0 = [], time.time()
    for n, (t, g) in enumerate(ev.groupby("ticker", sort=True)):
        by_year = {}
        for d in sorted(set(g["date"])):
            y = int(d[:4])
            if y not in by_year:
                if not SP.has_chain(t, y):
                    by_year[y] = None
                else:
                    by_year[y] = (SP.read_raw_chain(t, y), SP.spot_by_date(t, y))
            agg["events"] += 1
            pack = by_year[y]
            if pack is None or pack[0] is None:
                agg["no_chain_file"] += 1
                continue
            raw, spot = pack
            f = SP.put_funnel(raw, spot, d)
            if f.get("no_spot"):
                agg["no_spot"] += 1
                continue
            for k in ("any_put", "in_dte", "in_moneyness", "two_sided"):
                agg[k] += 1 if f[k] else 0
            pick = SP.pick_put(f["cands"])
            if pick is None:
                continue
            pick.update({"ticker": t, "date": d, "year": y})
            out.append(pick)
        if n and n % 50 == 0:
            print("    %d names priced, %.0fs" % (n, time.time() - t0))
    return pd.DataFrame(out), agg


# ------------------------------------------------------------------------------------------ K2
def k2_reprice_a3():
    """Re-price `A3`'s own banked spread trades as NAKED puts held to expiry, at the MID.

    `S6`: `credit_ps` in `optvrp_state.pkl` is the SPREAD credit and the short leg's own premium
    is stored NOWHERE, so this is a re-pricing against the chain and not a re-read of a column.
    Its own coverage is a required field — a `K2` computed on a non-random subset of `A3`'s
    trades is a different object.
    """
    p = os.path.join(D.data_root(), "options", "optvrp_state.pkl")
    if not os.path.isfile(p):
        return {"status": "ABSENT", "path": p}
    with open(p, "rb") as fh:
        st = pickle.load(fh)
    tr = [r for r in st.get("trades", []) if r.get("ok")]
    sub = [r for r in tr if SP.ERA_LO <= str(r.get("alert_ts")) <= SP.ERA_HI]
    rows = {}
    cache = {}
    priced, no_chain, no_row, no_settle = 0, 0, 0, 0
    for r in sub:
        t, d = str(r["ticker"]), str(r["alert_ts"])
        y = int(d[:4])
        key = (t, y)
        if key not in cache:
            cache[key] = ((SP.read_raw_chain(t, y), SP.spot_by_date(t, y))
                          if SP.has_chain(t, y) else (None, {}))
        raw, spot = cache[key]
        if raw is None:
            no_chain += 1
            continue
        k, ex = float(r["short_strike"]), str(r["expiry"])
        q = raw[(raw["date"] == d) & (raw["expiration"] == ex)
                & (raw["strike"].astype(float) == k)
                & (raw["right"].astype(str).str.upper().str[0] == "P")]
        if not len(q):
            no_row += 1
            continue
        bid, ask = float(q.iloc[0]["bid"]), float(q.iloc[0]["ask"])
        if not (bid > 0 and ask > bid):
            no_row += 1
            continue
        mid = (bid + ask) / 2.0
        # Settlement needs the expiry year's spot too -- an entry in December can expire in
        # January, and reading only the entry year would silently drop those.
        ykey = (t, int(ex[:4]))
        if ykey not in cache:
            cache[ykey] = ((SP.read_raw_chain(t, int(ex[:4])), SP.spot_by_date(t, int(ex[:4])))
                           if SP.has_chain(t, int(ex[:4])) else (None, {}))
        # The predecessor keys its cache on the EXPIRY's own year, so its map always
        # reaches its expiry and this limit is inert -- verified, not assumed, by the
        # refusal count this script already reports (`skipped_no_settlement_spot`).
        s_exp = SP.settlement_spot(cache[ykey][1] or spot, ex,
                                   max_stale_days=SP.MAX_SETTLEMENT_STALE_DAYS)
        if s_exp is None:
            no_settle += 1
            continue
        from valuation.edge.assignment import settle_short, CASH_SECURED_PUT
        res = settle_short(strike=k, credit=mid, spot_at_expiry=s_exp, right="put",
                           spot_basis=SP.AS_TRADED, method=CASH_SECURED_PUT)
        band = None
        ivr = float(r.get("iv_rank") or 0.0)
        for lo, hi in SP.K2_IV_BANDS:
            if lo <= ivr < hi:
                band = "%.2f-%.2f" % (lo, hi)
                break
        if band is None:
            continue
        rows.setdefault(band, []).append(res["ret_on_secured"] * 100.0)
        priced += 1
    by_band = {}
    for b in sorted(rows):
        a = np.asarray(rows[b], dtype=float)
        by_band[b] = {"n": int(len(a)), "mean_pct_of_strike": float(a.mean()),
                      "median_pct_of_strike": float(np.median(a)),
                      "sd_pct": float(a.std(ddof=1)) if len(a) > 1 else float("nan")}
    means = [by_band[b]["mean_pct_of_strike"] for b in sorted(by_band)]
    gradient = (means[-1] - means[0]) if len(means) >= 2 else float("nan")
    return {"status": "RAN", "a3_trades_total": len(tr), "a3_trades_in_era": len(sub),
            "priced": priced, "coverage": (priced / len(sub)) if sub else 0.0,
            "skipped_no_chain_file": no_chain, "skipped_no_usable_quote": no_row,
            "skipped_no_settlement_spot": no_settle,
            "by_iv_band": by_band, "gradient_top_minus_bottom_pp": gradient,
            "a3_banked_spread_gradient_pp": -9.45 - (-6.24),
            "note": "A3's own banked SPREAD expectancies by the same bands are -6.24 / -8.16 / "
                    "-9.45 percent of MAX RISK, a gradient of -3.21pp. This re-pricing is "
                    "percent of STRIKE on a naked put held to expiry at the MID -- a different "
                    "denominator (draft 4b measured the gap at ~9.8x) and a different structure. "
                    "The LEVELS are not comparable and only the SHAPE of the gradient is."}


# ------------------------------------------------------------------------------------------ K3
def k3_crash(picks: pd.DataFrame):
    """The mechanical crash stress on the register's MEASURED strike distribution.

    SPY's worst 32-session return by year is a property of a PUBLIC benchmark and reads no
    quadrant. The moneyness and premium are design inputs known at entry, not outcomes.
    """
    spy = D.read_prices("SPY")
    out = {}
    if spy is not None and len(spy):
        for y in (2016, 2017, 2018, 2019, 2020, 2022, 2025):
            s = spy[(spy["date"] >= "%d-01-01" % y) & (spy["date"] <= "%d-12-31" % y)]
            if len(s) > 32:
                out["%d" % y] = SP.worst_rolling(s["close"].to_numpy(dtype=float), 32)
    mon = float(np.median(picks["moneyness"])) if len(picks) else float("nan")
    prem = (float(np.median(picks["bid"].astype(float) / picks["strike"].astype(float)))
            if len(picks) else float("nan"))
    dte = float(np.median(picks["dte"])) if len(picks) else float("nan")
    turns = 252.0 / dte if dte and np.isfinite(dte) and dte > 0 else float("nan")
    tab = {}
    for name, fall in sorted(out.items(), key=lambda kv: kv[1]):
        if not np.isfinite(fall):
            continue
        yrs = SP.years_of_premium(-fall, mon, prem, turns)
        tab[name] = {"worst_32_session_return": fall,
                     "loss_on_secured_cash": max(0.0, (-fall - (1.0 - mon)) / mon),
                     "years_of_premium": yrs}
    # A single name at 1.4x the index in the worst episode -- the draft's own stress row.
    worst = min([v for v in out.values() if np.isfinite(v)] or [float("nan")])
    single = SP.years_of_premium(-worst * 1.4, mon, prem, turns) if np.isfinite(worst) else \
        float("nan")
    # The loss field was MISSING on this row in the first pass, and it is the row that decides
    # the gate -- an artifact whose binding line carries a `nan` is not a record of why it fired.
    tab["single_name_at_1.4x_the_worst_index_episode"] = {
        "worst_32_session_return": worst * 1.4 if np.isfinite(worst) else float("nan"),
        "loss_on_secured_cash": (max(0.0, (-worst * 1.4 - (1.0 - mon)) / mon)
                                 if np.isfinite(worst) and np.isfinite(mon) else float("nan")),
        "years_of_premium": single}
    vals = [v["years_of_premium"] for v in tab.values()
            if np.isfinite(v.get("years_of_premium", float("nan")))]
    worst_years = max(vals) if vals else float("inf")
    return {"median_moneyness": mon, "median_premium_frac_of_strike": prem,
            "median_dte": dte, "turns_per_year": turns,
            "spy_worst_32_session_by_year": out, "table": tab,
            "worst_years_of_premium": worst_years, "bar": SP.K3_MAX_YEARS_OF_PREMIUM,
            "pass": bool(np.isfinite(worst_years)
                         and worst_years <= SP.K3_MAX_YEARS_OF_PREMIUM)}


# ------------------------------------------------------------------------------------------ K4
def k4_affordability(picks: pd.DataFrame):
    """`MB3`: an affordability skip is NOT a ruin result and must never be counted as one."""
    if not len(picks):
        return {"pass": False, "why": "no priced events"}
    sec = picks["strike"].astype(float) * 100.0
    out = {"secured_cash_per_contract": {
        "p05": float(np.percentile(sec, 5)), "p25": float(np.percentile(sec, 25)),
        "median": float(np.median(sec)), "p75": float(np.percentile(sec, 75)),
        "p95": float(np.percentile(sec, 95)), "max": float(sec.max())}, "by_equity_cap": {}}
    for eq in SP.SIZING_EQUITY:
        for cap in SP.SIZING_CAPS:
            per = eq / float(cap)
            out["by_equity_cap"]["$%d/cap%d" % (int(eq), cap)] = {
                "cash_per_slot": per,
                "share_of_events_affordable": float((sec <= per).mean())}
    out["pass"] = True
    out["note"] = ("REPORTED, not gated: MB3 measured that the low-end failures are "
                   "AFFORDABILITY and not ruin -- the book never gets on -- so this exists to "
                   "make the skip reason a recorded field in the arm, not to refuse anything.")
    return out


def main():
    t0 = time.time()
    print("SELL-PREMIUM kills  era %s..%s  moneyness %.2f band %s  DTE %s"
          % (SP.ERA_LO, SP.ERA_HI, SP.MONEYNESS_TARGET, SP.MONEYNESS_BAND, SP.DTE_BAND))
    print("pass 1 - the event set, imported from dipcall (B7) ...")
    ev, names = build_events()
    print("  %d tier events over %d names, %d distinct dates\n"
          % (len(ev), ev["ticker"].nunique() if len(ev) else 0,
             ev["date"].nunique() if len(ev) else 0))

    print("pass 2 - K1's funnel and the picked contracts ...")
    picks, agg = price_events(ev)
    covered_days = int(picks["date"].nunique()) if len(picks) else 0
    k1 = {"events_total": int(len(ev)),
          "events_with_a_chain_file": int(agg["events"] - agg["no_chain_file"]),
          "funnel": {k: agg[k] for k in ("any_put", "in_dte", "in_moneyness", "two_sided")},
          "skipped_no_chain_file": agg["no_chain_file"], "skipped_no_spot": agg["no_spot"],
          "priceable_events": int(len(picks)), "covered_event_days": covered_days,
          "covered_names": int(picks["ticker"].nunique()) if len(picks) else 0,
          "floor_events": SP.K1_MIN_EVENTS, "floor_covered_days": SP.K1_MIN_COVERED_DAYS,
          "funnel_layer": "RAW chain. The DERIVED layer is two-sided on 1.0000 of its rows BY "
                          "CONSTRUCTION, so this funnel measured there would read 1.000 having "
                          "checked nothing (MB21's C1 family)."}
    k1["pass"] = bool(len(picks) >= SP.K1_MIN_EVENTS
                      and covered_days >= SP.K1_MIN_COVERED_DAYS)
    print("  priceable events %d (floor %d) ; covered days %d (floor %d) -> %s\n"
          % (len(picks), SP.K1_MIN_EVENTS, covered_days, SP.K1_MIN_COVERED_DAYS,
             "PASS" if k1["pass"] else "FIRES"))

    print("pass 3 - K2, re-pricing A3's short leg as a naked put ...")
    k2 = k2_reprice_a3()
    if k2.get("status") == "RAN":
        for b in sorted(k2["by_iv_band"]):
            r = k2["by_iv_band"][b]
            print("  IV rank %-10s n %5d  mean %+8.4f%% of strike  median %+8.4f%%"
                  % (b, r["n"], r["mean_pct_of_strike"], r["median_pct_of_strike"]))
        print("  gradient top-minus-bottom %+0.4fpp (A3's banked SPREAD gradient %+0.2fpp)\n"
              % (k2["gradient_top_minus_bottom_pp"], k2["a3_banked_spread_gradient_pp"]))
    k2["pass"] = bool(k2.get("status") == "RAN"
                      and np.isfinite(k2.get("gradient_top_minus_bottom_pp", float("nan")))
                      and k2["gradient_top_minus_bottom_pp"] >= k2["a3_banked_spread_gradient_pp"])
    k2["pass_rule"] = ("PRE-COMMITTED: the moneyness arm is WITHDRAWN if the gradient PERSISTS "
                       "on a naked, unstopped, mid-filled structure - i.e. if it is at least as "
                       "negative as A3's own banked spread gradient. FLATTENING (a gradient "
                       "less negative than A3's) clears.")
    print("  K2 -> %s" % ("PASS" if k2["pass"] else "FIRES"))

    print("\npass 4 - K3 crash stress and K4 affordability ...")
    k3 = k3_crash(picks)
    for nm in sorted(k3["table"], key=lambda x: -k3["table"][x].get("years_of_premium", 0)):
        r = k3["table"][nm]
        print("  %-44s fall %+7.2f%%  years of premium %6.2f"
              % (nm, 100.0 * r["worst_32_session_return"], r["years_of_premium"]))
    print("  worst %.2f years against a bar of %.1f -> %s"
          % (k3["worst_years_of_premium"], k3["bar"], "PASS" if k3["pass"] else "FIRES"))
    k4 = k4_affordability(picks)

    gates = {"K1_coverage": k1["pass"], "K2_premise": k2["pass"],
             "K3_crash_stress": k3["pass"], "K4_affordability": k4["pass"]}
    art = {"item": "SELL-PREMIUM free pre-outcome kills", "trials": 0,
           "register": "PREREG_sellpremium.md committed ALONE at 2e9fe7b",
           "trials_booked_at": "907d924 (options 310 -> 315)",
           "era": [SP.ERA_LO, SP.ERA_HI], "moneyness_target": SP.MONEYNESS_TARGET,
           "moneyness_band": list(SP.MONEYNESS_BAND), "dte_band": list(SP.DTE_BAND),
           "names_considered": len(names),
           "K1_coverage": k1, "K2_premise": k2, "K3_crash": k3, "K4_affordability": k4,
           "gates": gates, "all_pass": bool(all(gates.values())),
           "note": "a control can only BLOCK a finding, never produce one (MB1-SEL)"}
    with io.open(D.out_path("%s_KILLS.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    if len(picks):
        picks.to_pickle(D.out_path("%s_PICKS.pkl" % PREFIX))
        ev.to_pickle(D.out_path("%s_EVENTS.pkl" % PREFIX))

    print("\ngates: %s" % gates)
    print("wrote %s  (%.0fs)" % (D.out_path("%s_KILLS.json" % PREFIX), time.time() - t0))
    return 0 if art["all_pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
