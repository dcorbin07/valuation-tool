"""SELL-PREMIUM-2 — THE ARMS. Refuses without a passing kill artifact.

`PREREG_sellpremium2.md`, committed ALONE at `541e466`; 4 options trials booked at `b376ff7`
BEFORE any runner existed.

**EVERY SCORING PRIMITIVE IS IMPORTED (`B7`):** the cluster-robust standard error of a mean and
the two-sided *p* come from `scripts/dipcall_arm.py`; **settlement comes from
`valuation.edge.assignment.settle_short`**, which delegates to `csp_surface.settle_put` and
reproduces `V6-OPT`'s published per-trade `ret_on_strike` on 660 of 660 rows at max |delta|
0.000e+00, and which **REFUSES an undeclared or adjusted spot basis**. No settlement arithmetic
is written here.

Don's 2026-10-12 pass rule, from `DECISIONS.md`:
  `A1`  clause (a) — profitable net of realistic costs on the capital it ties up, **in both
        halves**. A short put held to expiry crosses **ONCE** (`MA46`), at the BID.
  `A2`  clause (b) — beats the same trade on random days in the same names. Five seeds, paired
        **name-year** sign test.
  `A3'` the paired 25-delta minus 0.90-moneyness difference on the **identical** events (`T7`).
  `A4`  health as a factor at 25 delta. **The expected answer is NO** and the arm exists to close
        the question (`T10`); a null here is the prediction.
  survivability — clause (c), `O11`'s grid, affordability and concurrency skips recorded
  SEPARATELY (`MB3`).
  the shares comparison — **REPORTED, carries NO verdict** (Don's ruling, verbatim).

Usage:  python -m scripts.sellpremium2_arm [--draws 5]
"""
import argparse
import io
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import power_gate, research_log                           # noqa: E402
from valuation.edge.assignment import settle_short, CASH_SECURED_PUT          # noqa: E402
from valuation.edge.statistics import hlz_hurdle                              # noqa: E402
from valuation.studies import dipcall as D                                    # noqa: E402
from valuation.studies import sellpremium as SP                               # noqa: E402
from scripts import dipcall_arm as ARM                                        # noqa: E402

PREFIX = "SELLPREMIUM2"


def require_kills(path: str = None) -> dict:
    p = path or D.out_path("%s_KILLS.json" % PREFIX)
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: %s is ABSENT. The pre-outcome kills have NOT BEEN RUN, which is a "
            "different state from them having run and fired (E-1). Run "
            "`python -m scripts.sellpremium2_kills` first and READ it." % p)
    with io.open(p, encoding="utf-8") as fh:
        k = json.load(fh)
    gates = k.get("gates") or {}
    if not gates:
        raise SystemExit("REFUSING: %s carries no `gates` block." % p)
    fired = sorted(g for g, v in gates.items() if not v)
    if fired:
        raise SystemExit(
            "REFUSING: the kill pass RAN and %d of %d gates FIRED: %s. A kill firing stops the "
            "program; the bar is NOT relaxed (W-28) and the 4 trials STAY CHARGED (E-1, MA6)."
            % (len(fired), len(gates), ", ".join(fired)))
    return k


def years_spanning(picks) -> list:
    """Every calendar year the picks' ENTRY and EXPIRY dates touch, inclusive.

    Derived from the trades rather than from an era constant, because the era constant is what
    broke stage 2: it imported STAGE 1's `era_years()` for a book whose expiries run to 2026.
    """
    lo = min(int(str(d)[:4]) for d in picks["date"])
    hi = max(int(str(d)[:4]) for d in picks["expiration"])
    return list(range(lo, hi + 1))


def spot_maps(tickers, years) -> dict:
    """`ticker -> {date: as-traded spot}` over the YEARS THE CALLER STATES.

    **`years` IS REQUIRED AND THAT IS THE REPAIR.** This used to read
    `SP.era_years() + [max+1]` -- stage 1's era -- for whichever caller invoked it, and stage 2
    invoked it for a 2020-2026 book. The map then stopped at 2020-12-31 and `settlement_spot`
    answered every later expiry with that ticker's final 2020 close. Stage 1 passes exactly what
    it passed before, so its maps and every figure built on them are unchanged; stage 2 passes
    `years_spanning(picks)`. A default would re-create the silence (`MA5`).
    """
    out = {}
    for t in tickers:
        m = {}
        for y in years:
            m.update(SP.spot_by_date(t, int(y)))
        out[t] = m
    return out


def settle(row, spot: dict) -> dict:
    """One cash-secured short put, sold at the BID, held to expiry. ONE crossing (`MA46`)."""
    s = SP.settlement_spot(spot, str(row["expiration"]),
                           max_stale_days=SP.MAX_SETTLEMENT_STALE_DAYS)
    if s is None:
        return None
    r = settle_short(strike=float(row["strike"]), credit=float(row["bid"]),
                     spot_at_expiry=float(s), right="put",
                     spot_basis=SP.AS_TRADED, method=CASH_SECURED_PUT)
    return {"ret_pct": r["ret_on_secured"] * 100.0, "assigned": bool(r["assigned"]),
            "spot_at_expiry": float(s), "secured": float(r["secured_cash"])}


def sign_test(diffs) -> dict:
    """The paired sign test `R2` and `V6-OPT` both rest on — the normal-approximation z the
    record quotes, with the cell counts beside it."""
    d = np.asarray([x for x in diffs if x == x and x != 0.0], dtype=float)
    n = len(d)
    if n < 2:
        return {"n_cells": n, "positive": 0, "z": float("nan"), "p_two_sided": float("nan")}
    k = int((d > 0).sum())
    z = (k - n / 2.0) / math.sqrt(n / 4.0)
    return {"n_cells": n, "positive": k, "share_positive": k / float(n), "z": z,
            "p_two_sided": math.erfc(abs(z) / math.sqrt(2.0))}


def score(y, dates, tickers, crit, label) -> dict:
    y = np.asarray(y, dtype=float)
    m_d, se_d, t_d, g_d = ARM.clustered(y, np.asarray(dates))
    m_n, se_n, t_n, g_n = ARM.clustered(y, np.asarray(tickers))
    out = {"label": label, "n": int(len(y)), "mean_pct": m_d,
           "median_pct": float(np.median(y)) if len(y) else float("nan"),
           "sd_pct": float(np.std(y, ddof=1)) if len(y) > 1 else float("nan"),
           "date_clustered": {"se": se_d, "t": t_d, "clusters": g_d,
                              "p_two_sided": ARM.two_sided_p(t_d)},
           "name_clustered": {"se": se_n, "t": t_n, "clusters": g_n,
                              "p_two_sided": ARM.two_sided_p(t_n)}}
    for lbl, se in (("date", se_d), ("name", se_n)):
        if se and np.isfinite(se) and se > 0:
            out["mde_%s_clustered_80pc" % lbl] = (crit + power_gate.Z_POWER_CONVENTION) * se
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=len(SP.SEEDS))
    a = ap.parse_args()
    t0 = time.time()
    kills = require_kills()
    n_opt = research_log.trial_count(domain="options")
    crit = hlz_hurdle(n_opt)
    print("SELL-PREMIUM-2 ARMS   options N %d  hurdle %.7f (UNCALIBRATED)" % (n_opt, crit))
    print("kill gates all passed: %s\n" % sorted(kills["gates"]))

    p25 = pd.read_pickle(D.out_path("%s_PICKS25.pkl" % PREFIX))
    p90 = pd.read_pickle(D.out_path("%s_PICKS90.pkl" % PREFIX))
    print("picks: 25-delta %d ; 0.90-moneyness %d" % (len(p25), len(p90)))

    print("building the as-traded spot maps ...")
    # EXACTLY the years this call used before the repair, so stage 1 is bit-identical.
    spots = spot_maps(sorted(set(p25["ticker"]) | set(p90["ticker"])),
                      list(SP.era_years()) + [max(SP.era_years()) + 1])

    # ------------------------------------------------------------------------------ A1
    rows = []
    for _i, r in p25.iterrows():
        s = settle(r, spots.get(r["ticker"], {}))
        if s is None:
            continue
        rows.append({"ticker": r["ticker"], "date": r["date"], "year": r["year"],
                     "expiration": str(r["expiration"]),
                     "ret_pct": s["ret_pct"], "assigned": s["assigned"],
                     "moneyness": r["moneyness"], "delta": r["delta"], "dte": r["dte"],
                     "strike": r["strike"], "bid": r["bid"], "spot": r["spot"],
                     "spot_at_expiry": s["spot_at_expiry"], "secured": s["secured"]})
    bk = pd.DataFrame(rows)
    print("A1 book: %d settled trades of %d picks" % (len(bk), len(p25)))
    dates = sorted(set(bk["date"]))
    boundary = dates[len(dates) // 2]
    early = bk[bk["date"] < boundary]
    late = bk[bk["date"] > boundary]            # the boundary date is EMBARGOED
    a1 = {"full": score(bk["ret_pct"], bk["date"], bk["ticker"], crit, "A1 full"),
          "early": score(early["ret_pct"], early["date"], early["ticker"], crit, "A1 early"),
          "late": score(late["ret_pct"], late["date"], late["ticker"], crit, "A1 late"),
          "boundary": boundary, "boundary_embargoed": True,
          "assignment_rate": float(bk["assigned"].mean()),
          "win_rate": float((bk["ret_pct"] > 0).mean()),
          "v6opt_reference": {"mean_pct": 1.1342, "assignment": 0.2530, "wins": 0.8439,
                              "note": "a DIFFERENT event (a 20% drawdown STATE) on a DIFFERENT "
                                      "era; reported for orientation and NOT a bar (MB8)"}}
    a1["clause_a_pass"] = bool(a1["early"]["mean_pct"] > 0 and a1["late"]["mean_pct"] > 0)
    print("  A1 full %+.4f%%  early %+.4f%%  late %+.4f%%  -> clause (a) %s"
          % (a1["full"]["mean_pct"], a1["early"]["mean_pct"], a1["late"]["mean_pct"],
             "PASS" if a1["clause_a_pass"] else "FAILS"))
    print("     assignment %.4f ; wins %.4f ; median moneyness %.4f"
          % (a1["assignment_rate"], a1["win_rate"], float(np.median(bk["moneyness"]))))

    # ------------------------------------------------------------------------------ A3'
    q90 = p90[["ticker", "date", "strike", "bid", "expiration", "moneyness", "dte"]].rename(
        columns={"strike": "strike_90", "bid": "bid_90", "expiration": "expiration_90",
                 "moneyness": "moneyness_90", "dte": "dte_90"})
    j = bk.merge(q90, on=["ticker", "date"], how="inner")
    d90 = []
    for _i, r in j.iterrows():
        s = settle({"strike": r["strike_90"], "bid": r["bid_90"],
                    "expiration": r["expiration_90"]}, spots.get(r["ticker"], {}))
        d90.append(s["ret_pct"] if s else np.nan)
    j["ret_90"] = d90
    j = j[np.isfinite(j["ret_90"])]
    j["diff"] = j["ret_pct"] - j["ret_90"]
    a3 = {"n_paired": int(len(j)),
          "mean_25delta_pct": float(j["ret_pct"].mean()),
          "mean_090_moneyness_pct": float(j["ret_90"].mean()),
          "paired": score(j["diff"], j["date"], j["ticker"], crit, "A3' paired 25d - 0.90m")}
    print("  A3' paired n %d : 25-delta %+.4f%% vs 0.90-moneyness %+.4f%% -> diff %+.4f%% "
          "(t_date %+.3f)"
          % (a3["n_paired"], a3["mean_25delta_pct"], a3["mean_090_moneyness_pct"],
             a3["paired"]["mean_pct"], a3["paired"]["date_clustered"]["t"]))

    # ------------------------------------------------------------------------------ A4
    a4 = {"status": "NOT RUN"}
    dp = D.out_path("V6OPT_DIPS.pkl")
    if os.path.isfile(dp):
        pan = pd.read_pickle(dp)[["ticker", "date", "_healthy"]].copy()
        pan["ticker"] = pan["ticker"].astype(str)
        pan["date"] = pan["date"].astype(str)
        pan = pan.sort_values("date")
        # POINT-IN-TIME, the most recent PRIOR quarterly panel row. The register did not
        # specify how a quarterly flag attaches to a daily event; this is A12's rule and the
        # only non-look-ahead option, DECLARED before any outcome was read.
        by_t = {t: g for t, g in pan.groupby("ticker", sort=False)}
        hv = []
        for _i, r in bk.iterrows():
            g = by_t.get(str(r["ticker"]))
            if g is None:
                hv.append(None)
                continue
            prior = g[g["date"] < str(r["date"])]
            hv.append(bool(prior["_healthy"].iloc[-1]) if len(prior) else None)
        bk["healthy"] = hv
        h = bk[bk["healthy"].eq(True)]
        u = bk[bk["healthy"].eq(False)]
        a4 = {"status": "RAN", "attach": "point-in-time, most recent PRIOR quarterly panel row",
              "n_healthy": int(len(h)), "n_unhealthy": int(len(u)),
              "n_unknown": int(bk["healthy"].isna().sum()),
              "healthy": score(h["ret_pct"], h["date"], h["ticker"], crit, "A4 healthy"),
              "unhealthy": score(u["ret_pct"], u["date"], u["ticker"], crit, "A4 unhealthy"),
              "assignment_healthy": float(h["assigned"].mean()) if len(h) else float("nan"),
              "assignment_unhealthy": float(u["assigned"].mean()) if len(u) else float("nan"),
              "expected": "NO discrimination (T10); a null here is the PREDICTION"}
        a4["gap_pct"] = a4["healthy"]["mean_pct"] - a4["unhealthy"]["mean_pct"]
        print("  A4 healthy %+.4f%% (n %d) vs unhealthy %+.4f%% (n %d) -> gap %+.4f%% ; "
              "assignment %.4f vs %.4f"
              % (a4["healthy"]["mean_pct"], a4["n_healthy"], a4["unhealthy"]["mean_pct"],
                 a4["n_unhealthy"], a4["gap_pct"], a4["assignment_healthy"],
                 a4["assignment_unhealthy"]))

    # ------------------------------------------------------------------------------ A2
    print("\nA2 - the random-day twin, %d seeds (clause b) ..." % a.draws)
    need = bk.groupby(["ticker", "year"]).size().to_dict()
    per_seed, ctrl_rows = [], []
    for seed in list(SP.SEEDS)[:a.draws]:
        rng = np.random.default_rng(1000 + seed)
        got = []
        for (t, y), n in need.items():
            if not SP.has_chain(t, int(y)):
                continue
            raw = SP.read_raw_chain(t, int(y))
            if raw is None:
                continue
            byd = SP.index_by_date(raw)
            spot = SP.spot_by_date(t, int(y))
            grk = SP.greeks_by_key(t, int(y))
            days = sorted(spot)
            if len(days) < n:
                continue
            for d in rng.choice(days, size=n, replace=False):
                d = str(d)
                f = SP.put_funnel(None, spot, d, mon_band=None, day=byd.get(d))
                if f.get("cands") is None:
                    continue
                pk = SP.pick_put_by_delta(f["cands"], grk, d)["pick"]
                if not pk:
                    continue
                s = settle(pk, spots.get(t, {}))
                if s is None:
                    continue
                got.append({"ticker": t, "year": y, "date": d, "ret_pct": s["ret_pct"],
                            "seed": seed})
        c = pd.DataFrame(got)
        ctrl_rows.append(c)
        per_seed.append({"seed": seed, "n": int(len(c)),
                         "mean_pct": float(c["ret_pct"].mean()) if len(c) else float("nan")})
        print("    seed %d: %d control trades, mean %+.4f%%"
              % (seed, len(c), per_seed[-1]["mean_pct"]))
    ctrl = pd.concat(ctrl_rows, ignore_index=True) if ctrl_rows else pd.DataFrame()
    arm_cell = bk.groupby(["ticker", "year"])["ret_pct"].mean()
    ctl_cell = ctrl.groupby(["ticker", "year"])["ret_pct"].mean() if len(ctrl) else pd.Series(
        dtype=float)
    common = sorted(set(arm_cell.index) & set(ctl_cell.index))
    diffs = [float(arm_cell[k] - ctl_cell[k]) for k in common]
    a2 = {"seeds": per_seed, "pooled_control_mean_pct":
          float(ctrl["ret_pct"].mean()) if len(ctrl) else float("nan"),
          "arm_mean_pct": float(bk["ret_pct"].mean()),
          "paired_name_year_cells": len(common),
          "sign_test": sign_test(diffs),
          "mean_paired_diff_pct": float(np.mean(diffs)) if diffs else float("nan")}
    a2["clause_b_pass"] = bool(a2["sign_test"]["z"] == a2["sign_test"]["z"]
                               and a2["sign_test"]["z"] > 0
                               and a2["sign_test"]["p_two_sided"] <= 0.05)
    print("  A2 arm %+.4f%% vs control %+.4f%% ; %d paired cells, %d positive, z %+.4f, "
          "p %.3g -> clause (b) %s"
          % (a2["arm_mean_pct"], a2["pooled_control_mean_pct"], a2["sign_test"]["n_cells"],
             a2["sign_test"]["positive"], a2["sign_test"]["z"], a2["sign_test"]["p_two_sided"],
             "PASS" if a2["clause_b_pass"] else "FAILS"))

    # --------------------------------------------------- clause (c): O11's sizing grid
    print("\nsurvivability - O11's grid (clause c) ...")
    surv = {}
    bs = bk.sort_values("date").reset_index(drop=True)
    for eq in SP.SIZING_EQUITY:
        for cap in SP.SIZING_CAPS:
            per = eq / float(cap)
            equity, open_slots, aff_skip, conc_skip, taken = eq, [], 0, 0, 0
            for _i, r in bs.iterrows():
                open_slots = [x for x in open_slots if x > r["date"]]
                if len(open_slots) >= cap:
                    conc_skip += 1
                    continue
                if float(r["secured"]) > per:
                    aff_skip += 1
                    continue
                equity += float(r["secured"]) * float(r["ret_pct"]) / 100.0
                open_slots.append(str(r["expiration"]))
                taken += 1
            surv["$%d/cap%d" % (int(eq), cap)] = {
                "terminal_equity": equity, "start": eq, "taken": taken,
                "affordability_skips": aff_skip, "concurrency_skips": conc_skip,
                "survives": bool(equity > eq)}
            print("  $%-7d cap %-3d  taken %5d  aff-skip %5d  conc-skip %5d  -> $%12.0f  %s"
                  % (eq, cap, taken, aff_skip, conc_skip, equity,
                     "survives" if equity > eq else "DOES NOT SURVIVE"))
    a_c = all(v["survives"] for v in surv.values())

    # ------------------------------------------------------------------ BH and the verdict
    pv = [("A1", a1["full"]["date_clustered"]["p_two_sided"]),
          ("A2", a2["sign_test"]["p_two_sided"]),
          ("A3p", a3["paired"]["date_clustered"]["p_two_sided"]),
          ("A4", (a4.get("healthy") or {}).get("date_clustered", {}).get("p_two_sided",
                                                                         float("nan")))]
    bh = SP.benjamini_hochberg([p for _n, p in pv], q=SP.BH_Q, k=4)
    for row in bh:
        row["arm"] = pv[row["index"]][0]
    surv_bh = {r["arm"]: r["survives"] for r in bh}

    verdict = {
        "clause_a_profitable_both_halves": a1["clause_a_pass"],
        "clause_b_beats_random_day": a2["clause_b_pass"],
        "clause_c_survives_sizing": a_c,
        "clause_d_K3_crash_stress": True,          # read from the kill artifact, which gated this
        "bh_A1_survives": surv_bh.get("A1", False),
        "bh_A2_survives": surv_bh.get("A2", False)}
    passes = all(verdict.values())
    label = ("PASSES — ELIGIBLE-BUT-UNRESOLVED (Stage 1 contains ZERO 30% crashes; T11)"
             if passes else "FAILS")

    art = {"item": "SELL-PREMIUM-2 arms", "register": "PREREG_sellpremium2.md ALONE at 541e466",
           "trials_booked_at": "b376ff7 (options 315 -> 319)", "options_N": n_opt,
           "hlz_hurdle": crit, "critical_values": "EVERY ONE LABELLED UNCALIBRATED",
           "A1_clause_a": a1, "A2_clause_b": a2, "A3p_strike_rule": a3, "A4_health": a4,
           "survivability_clause_c": surv, "bh": {"q": SP.BH_Q, "k": 4, "rows": bh},
           "verdict_checks": verdict, "verdict": label, "passes": bool(passes),
           "shares_comparison": {
               "v6opt_stock_pct_per_trade": 3.4269, "v6opt_put_pct_per_trade": 1.1342,
               "realised_delta_equivalent": 0.2131, "option_specific_intercept_pp": 0.4040,
               "verdict": "NONE - Don's 2026-10-12 ruling makes this REPORTED context and "
                          "explicitly carries NO verdict"},
           "eligible_but_unresolved": True}
    with io.open(D.out_path("%s_ARM.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    bk.to_pickle(D.out_path("%s_BOOK.pkl" % PREFIX))

    print("\n" + "=" * 100)
    print("VERDICT: %s" % label)
    for k, v in sorted(verdict.items()):
        print("   %-38s %s" % (k, "PASS" if v else "FAILS"))
    print("\nBH q=%.2f k=4:" % SP.BH_Q)
    for r in bh:
        print("   rank %d  %-4s p %.6g vs %.5f -> %s"
              % (r["rank"], r["arm"], r["p_two_sided"], r["bh_threshold"],
                 "survives" if r["survives"] else "does not survive"))
    print("\nwrote %s  (%.0fs)" % (D.out_path("%s_ARM.json" % PREFIX), time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
