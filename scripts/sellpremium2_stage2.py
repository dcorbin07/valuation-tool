"""SELL-PREMIUM-2 — STAGE 2. The ONE read of the check quadrant. 2020-2026 x ticker half 1.

`PREREG_sellpremium2.md`, committed ALONE at `541e466`, fixed every bar BEFORE stage 1 ran, and
`T11` pre-specified this population: *"the crash question is answered at Stage 2 -- one read of
2020-2026 x half 1."* `RESEARCH_CHARTER.md` Stage 2: *"Only Stage-1 survivors, with the bar fixed
in the register before the look, get ONE read of the CHECK quadrant ... Each read is logged, and
a construction gets one."*

**NOTHING ABOUT THE CONSTRUCTION CHANGES.** Same event (`-2.5 sigma`, 60-session strictly-prior
vol, adjusted basis), same point-in-time $10B tier, same 25-delta rule solved on the put leg, same
20-60 DTE band, same hold-to-expiry, same single touch crossing at the BID, same `K1` floors, same
**6.0-year** crash bar with the **same synthetic row**, same half rule (median covered event date,
boundary embargoed), same clustering on BOTH date and ticker, same BH at q = 0.10 / k = 4. Only
the WINDOW and the HALF move, and those were fixed by the charter before anything ran.

**EVERY SCORING PRIMITIVE IS IMPORTED (`B7`)** from `scripts/sellpremium2_arm.py` and
`scripts/sellpremium2_kills.py`. A second scoring path is how one construction comes to report two
numbers, and at the one look that cannot be repeated that would be unrecoverable.

Usage:  python -m scripts.sellpremium2_stage2 --kills      # own pass, written first
        python -m scripts.sellpremium2_stage2 --arms       # REFUSES without the above
"""
import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import research_log                                      # noqa: E402
from valuation.edge.statistics import hlz_hurdle                             # noqa: E402
from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402
from scripts import sellpremium2_arm as A2M                                  # noqa: E402
from scripts import sellpremium2_kills as K                                  # noqa: E402

PREFIX = "SELLPREMIUM2_STAGE2"
ERA = D.ERA_CHECK


def build_events():
    """The check quadrant's event set. `dipcall`'s event and tier, era-switched (`B7`)."""
    sched, _u = D.tier_schedule_era(ERA)
    cfg = D.era(ERA)
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
             & (s["date"] >= cfg["lo"]).to_numpy() & (s["date"] <= cfg["hi"]).to_numpy())
        if not m.any():
            continue
        for d in s["date"].to_numpy()[m]:
            rows.append({"ticker": t, "date": str(d)})
        if i and i % 200 == 0:
            print("    %d/%d names, %.0fs" % (i, len(names), time.time() - t0))
    return pd.DataFrame(rows), names


def price(ev):
    """One chain read, the 25-delta pick. Identical selection code to stage 1."""
    agg = {"events": 0, "no_chain_file": 0, "no_spot": 0, "two_sided": 0, "no_delta": 0,
           "no_chain_year": {}}
    out, t0 = [], time.time()
    for n, (t, g) in enumerate(ev.groupby("ticker", sort=True)):
        cache = {}
        for d in sorted(set(g["date"])):
            y = int(d[:4])
            if y not in cache:
                cache[y] = ((SP.index_by_date(SP.read_raw_chain(t, y)),
                             SP.spot_by_date(t, y), SP.greeks_by_key(t, y))
                            if SP.has_chain(t, y) else None)
            agg["events"] += 1
            pack = cache[y]
            if pack is None:
                agg["no_chain_file"] += 1
                agg["no_chain_year"][str(y)] = agg["no_chain_year"].get(str(y), 0) + 1
                continue
            byd, spot, grk = pack
            day = byd.get(d)
            if day is None:
                continue
            f = SP.put_funnel(None, spot, d, mon_band=None, day=day)
            if f.get("no_spot"):
                agg["no_spot"] += 1
                continue
            agg["two_sided"] += 1 if f["two_sided"] else 0
            if f["cands"] is None or not len(f["cands"]):
                continue
            r = SP.pick_put_by_delta(f["cands"], grk, d)
            agg["no_delta"] += r["no_delta"]
            if r["pick"]:
                r["pick"].update({"ticker": t, "date": d, "year": y})
                out.append(r["pick"])
        if n and n % 50 == 0:
            print("    %d names priced, %.0fs" % (n, time.time() - t0))
    return pd.DataFrame(out), agg


def run_kills():
    t0 = time.time()
    cfg = D.era(ERA)
    print("STAGE 2 kills -- check quadrant %s..%s x ticker half %s"
          % (cfg["lo"], cfg["hi"], cfg["ticker_half"]))
    print("bars are STAGE 1's, unchanged: K1 >= %d events / >= %d days ; K3 bar %.1f years\n"
          % (SP.K1_MIN_EVENTS, SP.K1_MIN_COVERED_DAYS, SP.K3_MAX_YEARS_OF_PREMIUM))

    print("pass 1 - the event set ...")
    ev, names = build_events()
    print("  %d tier events over %d names / %d dates\n"
          % (len(ev), ev["ticker"].nunique(), ev["date"].nunique()))

    print("pass 2 - pricing the 25-delta rule ...")
    picks, agg = price(ev)
    days = int(picks["date"].nunique()) if len(picks) else 0
    k1 = {"events_total": int(len(ev)), "funnel": agg,
          "priceable_events": int(len(picks)), "covered_event_days": days,
          "covered_names": int(picks["ticker"].nunique()) if len(picks) else 0,
          "floor_events": SP.K1_MIN_EVENTS, "floor_covered_days": SP.K1_MIN_COVERED_DAYS,
          "stage1_priceable_events": 2610, "stage1_covered_days": 620}
    k1["pass"] = bool(len(picks) >= SP.K1_MIN_EVENTS and days >= SP.K1_MIN_COVERED_DAYS)
    print("  K1 priceable %d (floor %d) ; covered days %d (floor %d) -> %s"
          % (len(picks), SP.K1_MIN_EVENTS, days, SP.K1_MIN_COVERED_DAYS,
             "PASS" if k1["pass"] else "FIRES"))
    print("  chain-file misses by year: %s" % agg["no_chain_year"])

    k3 = K.k3_from_picks(picks, "stage 2, 25-delta on the check quadrant")
    print("\n  K3 income %.4f%%/yr ; worst %.4f years against %.1f -> %s"
          % (100 * k3["annual_income_frac_of_secured_cash"], k3["worst_years_of_premium"],
             k3["bar"], "PASS" if k3["pass"] else "FIRES"))
    for nm, r in sorted(k3["table"].items(), key=lambda kv: -kv[1]["years_of_premium"])[:4]:
        print("    %-44s fall %+7.2f%%  years %6.2f"
              % (nm, 100 * r["worst_32_session_return"], r["years_of_premium"]))

    gates = {"K1_coverage": k1["pass"], "K3_crash_stress": k3["pass"]}
    art = {"item": "SELL-PREMIUM-2 stage 2 kills (check quadrant)", "era": ERA,
           "window": [cfg["lo"], cfg["hi"]], "ticker_half": cfg["ticker_half"],
           "register": "PREREG_sellpremium2.md ALONE at 541e466; bars UNCHANGED from stage 1",
           "K1_coverage": k1, "K3_crash": k3, "gates": gates,
           "all_pass": bool(all(gates.values()))}
    with io.open(D.out_path("%s_KILLS.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    if len(picks):
        picks.to_pickle(D.out_path("%s_PICKS.pkl" % PREFIX))
    print("\ngates: %s  (%.0fs)" % (gates, time.time() - t0))
    return 0 if art["all_pass"] else 3


def require_kills():
    p = D.out_path("%s_KILLS.json" % PREFIX)
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: %s is ABSENT -- the stage-2 kills have NOT BEEN RUN, which "
                         "is a different state from them having fired (E-1). Run --kills." % p)
    with io.open(p, encoding="utf-8") as fh:
        k = json.load(fh)
    fired = sorted(g for g, v in (k.get("gates") or {}).items() if not v)
    if fired:
        raise SystemExit("REFUSING: stage-2 gates FIRED: %s. The bars are stage 1's and are NOT "
                         "relaxed (W-28)." % ", ".join(fired))
    return k


def run_arms(draws):
    t0 = time.time()
    kills = require_kills()
    n_opt = research_log.trial_count(domain="options")
    crit = hlz_hurdle(n_opt)
    print("STAGE 2 ARMS   options N %d  hurdle %.7f (UNCALIBRATED)\n" % (n_opt, crit))

    picks = pd.read_pickle(D.out_path("%s_PICKS.pkl" % PREFIX))
    # THE REPAIR. This read `A2M.spot_maps(tickers)`, which built STAGE 1's era (2016-2020) for
    # a book whose expiries run to 2026, so 73.02% of trades settled at their ticker's last
    # 2020 close. The years now come from the TRADES.
    map_years = A2M.years_spanning(picks)
    print("   spot maps over %d-%d (from the picks, not from an era constant)"
          % (min(map_years), max(map_years)))
    spots = A2M.spot_maps(sorted(set(picks["ticker"])), map_years)
    rows, refused = [], 0
    for _i, r in picks.iterrows():
        s = A2M.settle(r, spots.get(r["ticker"], {}))
        if s is None:
            refused += 1          # COUNTED, never dropped silently -- that silence is the bug
            continue
        rows.append({"ticker": r["ticker"], "date": r["date"], "year": r["year"],
                     "expiration": str(r["expiration"]), "ret_pct": s["ret_pct"],
                     "assigned": s["assigned"], "moneyness": r["moneyness"],
                     "delta": r["delta"], "dte": r["dte"], "strike": r["strike"],
                     "bid": r["bid"], "secured": s["secured"]})
    bk = pd.DataFrame(rows)
    print("   settled %d of %d picks; %d REFUSED for want of a settlement price"
          % (len(bk), len(picks), refused))
    dates = sorted(set(bk["date"]))
    boundary = dates[len(dates) // 2]
    early, late = bk[bk["date"] < boundary], bk[bk["date"] > boundary]
    a1 = {"full": A2M.score(bk["ret_pct"], bk["date"], bk["ticker"], crit, "s2 A1 full"),
          "early": A2M.score(early["ret_pct"], early["date"], early["ticker"], crit, "early"),
          "late": A2M.score(late["ret_pct"], late["date"], late["ticker"], crit, "late"),
          "boundary": boundary, "boundary_embargoed": True,
          "assignment_rate": float(bk["assigned"].mean()),
          "win_rate": float((bk["ret_pct"] > 0).mean()),
          "stage1": {"full_pct": 0.6709, "early_pct": 0.8799, "late_pct": 0.5286,
                     "assignment": 0.1605, "wins": 0.8747}}
    a1["clause_a_pass"] = bool(a1["early"]["mean_pct"] > 0 and a1["late"]["mean_pct"] > 0)
    print("A1  full %+.4f%% (t_d %+.3f)  early %+.4f%%  late %+.4f%%  -> clause (a) %s"
          % (a1["full"]["mean_pct"], a1["full"]["date_clustered"]["t"],
             a1["early"]["mean_pct"], a1["late"]["mean_pct"],
             "PASS" if a1["clause_a_pass"] else "FAILS"))
    print("    n %d  assignment %.4f  wins %.4f  (stage 1: %+.4f%%, %.4f, %.4f)"
          % (a1["full"]["n"], a1["assignment_rate"], a1["win_rate"],
             0.6709, 0.1605, 0.8747))

    # ---------------------------------------------------------------- A2, clause (b)
    print("\nA2 - the random-day twin, %d seeds ..." % draws)
    need = bk.groupby(["ticker", "year"]).size().to_dict()
    ctrl_rows, per_seed = [], []
    for seed in list(SP.SEEDS)[:draws]:
        rng = np.random.default_rng(1000 + seed)
        got = []
        for (t, y), n in need.items():
            if not SP.has_chain(t, int(y)):
                continue
            raw = SP.read_raw_chain(t, int(y))
            if raw is None:
                continue
            byd, spot = SP.index_by_date(raw), SP.spot_by_date(t, int(y))
            grk = SP.greeks_by_key(t, int(y))
            dd = sorted(spot)
            if len(dd) < n:
                continue
            for d in rng.choice(dd, size=n, replace=False):
                d = str(d)
                f = SP.put_funnel(None, spot, d, mon_band=None, day=byd.get(d))
                if f.get("cands") is None:
                    continue
                pk = SP.pick_put_by_delta(f["cands"], grk, d)["pick"]
                if not pk:
                    continue
                s = A2M.settle(pk, spots.get(t, {}))
                if s is None:
                    continue
                got.append({"ticker": t, "year": y, "ret_pct": s["ret_pct"], "seed": seed})
        c = pd.DataFrame(got)
        ctrl_rows.append(c)
        per_seed.append({"seed": seed, "n": int(len(c)),
                         "mean_pct": float(c["ret_pct"].mean()) if len(c) else float("nan")})
        print("    seed %d: %d control trades, mean %+.4f%%"
              % (seed, len(c), per_seed[-1]["mean_pct"]))
    ctrl = pd.concat(ctrl_rows, ignore_index=True) if ctrl_rows else pd.DataFrame()
    arm_cell = bk.groupby(["ticker", "year"])["ret_pct"].mean()
    ctl_cell = (ctrl.groupby(["ticker", "year"])["ret_pct"].mean() if len(ctrl)
                else pd.Series(dtype=float))
    common = sorted(set(arm_cell.index) & set(ctl_cell.index))
    diffs = [float(arm_cell[k] - ctl_cell[k]) for k in common]
    a2 = {"seeds": per_seed, "arm_mean_pct": float(bk["ret_pct"].mean()),
          "pooled_control_mean_pct": float(ctrl["ret_pct"].mean()) if len(ctrl) else float("nan"),
          "paired_name_year_cells": len(common), "sign_test": A2M.sign_test(diffs),
          "mean_paired_diff_pct": float(np.mean(diffs)) if diffs else float("nan"),
          "stage1_sign_test": {"cells": 657, "positive": 456, "z": 9.9485}}
    a2["clause_b_pass"] = bool(a2["sign_test"]["z"] == a2["sign_test"]["z"]
                               and a2["sign_test"]["z"] > 0
                               and a2["sign_test"]["p_two_sided"] <= 0.05)
    print("  A2 arm %+.4f%% vs control %+.4f%% ; %d cells, %d positive, z %+.4f, p %.3g -> %s"
          % (a2["arm_mean_pct"], a2["pooled_control_mean_pct"], a2["sign_test"]["n_cells"],
             a2["sign_test"]["positive"], a2["sign_test"]["z"],
             a2["sign_test"]["p_two_sided"], "PASS" if a2["clause_b_pass"] else "FAILS"))

    # ---------------------------------------------------------------- clause (c)
    print("\nsurvivability - O11's grid ...")
    # ONE implementation (`B7`). This carried its own copy of the loop, which sized every
    # position from the STARTING equity forever and never stopped at ruin -- on the VOID book
    # that reported terminal equities as low as -$217,426, which a cash-secured book cannot
    # reach. The repaired loop lives in `sellpremium2_sizing_fix.grid`; a second copy here is
    # how the two would drift apart again.
    from scripts.sellpremium2_sizing_fix import grid as _grid
    surv = {}
    for eq in SP.SIZING_EQUITY:
        for cap in SP.SIZING_CAPS:
            c = _grid(bk, eq, cap)
            surv["$%d/cap%d" % (int(eq), cap)] = c
            print("  $%-7d cap %-3d taken %5d  aff %5d  conc %5d -> $%11.0f  %s%s"
                  % (eq, cap, c["taken"], c["affordability_skips"], c["concurrency_skips"],
                     c["terminal_equity"],
                     "survives" if c["survives"] else "DOES NOT SURVIVE",
                     ("  RUINED on %s" % c["ruined_on"]) if c["ruined"] else ""))
    clause_c = all(v["survives"] for v in surv.values())

    bh = SP.benjamini_hochberg(
        [a1["full"]["date_clustered"]["p_two_sided"], a2["sign_test"]["p_two_sided"]],
        q=SP.BH_Q, k=4)
    for r, nm in zip(bh, ["A1", "A2"]):
        pass
    for r in bh:
        r["arm"] = ["A1", "A2"][r["index"]]

    verdict = {"clause_a_profitable_both_halves": a1["clause_a_pass"],
               "clause_b_beats_random_day": a2["clause_b_pass"],
               "clause_c_survives_sizing": clause_c,
               "clause_d_K3_crash_stress": bool(kills["gates"]["K3_crash_stress"]),
               "bh_A1_survives": bool(next(r for r in bh if r["arm"] == "A1")["survives"]),
               "bh_A2_survives": bool(next(r for r in bh if r["arm"] == "A2")["survives"])}
    passes = all(verdict.values())

    # DID THE CHECK QUADRANT CONTAIN A CRASH? That is the whole reason stage 1 was
    # ELIGIBLE-BUT-UNRESOLVED, and it is a property of the WINDOW rather than of the book.
    spy = D.read_prices("SPY")
    sp = spy[(spy["date"] >= min(bk["date"])) & (spy["date"] <= max(bk["date"]))]
    worst = SP.worst_rolling(sp["close"].to_numpy(dtype=float), 32)
    crash = {"worst_32_session_spy_return_in_the_scored_window": float(worst),
             "window": [min(bk["date"]), max(bk["date"])],
             "contains_a_30pc_crash": bool(worst <= -0.30)}

    art = {"item": "SELL-PREMIUM-2 stage 2 arms (check quadrant)", "era": ERA,
           "options_N": n_opt, "hlz_hurdle": crit,
           "critical_values": "EVERY ONE LABELLED UNCALIBRATED",
           "A1_clause_a": a1, "A2_clause_b": a2, "survivability_clause_c": surv,
           "bh": {"q": SP.BH_Q, "k": 4, "rows": bh},
           "verdict_checks": verdict, "passes": bool(passes),
           "crash_in_the_scored_window": crash,
           "label": ("CONFIRMED on the check quadrant" if passes
                     else "NOT CONFIRMED on the check quadrant")}
    with io.open(D.out_path("%s_ARM.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    bk.to_pickle(D.out_path("%s_BOOK.pkl" % PREFIX))

    print("\n" + "=" * 96)
    print("STAGE 2 VERDICT: %s" % art["label"])
    for k2, v in sorted(verdict.items()):
        print("   %-38s %s" % (k2, "PASS" if v else "FAILS"))
    print("\nworst 32-session SPY return inside the scored window: %+.2f%%  -> contains a 30%% "
          "crash: %s" % (100 * worst, crash["contains_a_30pc_crash"]))
    print("wrote %s  (%.0fs)" % (D.out_path("%s_ARM.json" % PREFIX), time.time() - t0))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kills", action="store_true")
    ap.add_argument("--arms", action="store_true")
    ap.add_argument("--draws", type=int, default=len(SP.SEEDS))
    a = ap.parse_args()
    if a.kills == a.arms:
        raise SystemExit("choose exactly one of --kills / --arms: the kills are READ in their "
                         "own pass before any arm (O10's process defect)")
    return run_kills() if a.kills else run_arms(a.draws)


if __name__ == "__main__":
    sys.exit(main())
