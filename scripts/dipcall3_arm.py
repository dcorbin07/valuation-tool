"""DIP-CALL-3 — THE ARM. Refuses without a passing kill artifact AND per-cell.

Register: `PREREG_dipcall3.md`, committed ALONE at `4d50597`. Trials booked at `6c40cb4`
(equity 293 -> 297) BEFORE any runner existed.

**EVERY SCORING PRIMITIVE IS IMPORTED FROM `scripts/dipcall_arm.py` AND NEVER RE-IMPLEMENTED**
(`B7`): the forward/abnormal-return construction, the cluster-robust standard error of a mean,
the vectorised within-date permutation null and the two-sided p. Only the ERA ASSEMBLY differs —
which universe, which window, which cells — and that is what this file is. Two scoring paths are
how two registers come to report two different numbers for one question.

**`K1` IS A PER-CELL REFUSAL AND THIS FILE ENFORCES IT MECHANICALLY.** The kill pass published
`cells_cleared_for_the_arm`; any cell absent from that list is NOT RUN and `k` stays 4 (§4). On
the 2026-10-10 pass that cleared `pooled|h63` and `pooled|h126` and REFUSED `no_news|h63` and
`no_news|h126` — so **the faithful out-of-sample replication of `DIP-CALL-2`'s no-news arm DID NOT
RUN**, and whatever the pooled cells say, that is a different object (§5 void condition 3).

Usage:  python -m scripts.dipcall3_arm [--k 2.5] [--draws 500]
"""
import argparse
import io
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import power_gate, research_log                           # noqa: E402
from valuation.edge.statistics import hlz_hurdle                              # noqa: E402
from valuation.studies import dipcall as D                                    # noqa: E402
from scripts import dipcall_arm as ARM                                        # noqa: E402

PREFIX = "DIPCALL3"
ERA = D.ERA_OOS9908


def require_kills() -> dict:
    """REFUSES without a passing kill artifact. THE TWO REFUSAL STATES ARE DISTINCT (`E-1`), and
    a THIRD state exists here: the pass ran, some cells cleared and some did not."""
    p = D.out_path("%s_KILLS.json" % PREFIX)
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: %s is ABSENT. The free pre-outcome kill pass has not been run, which is a "
            "different state from it having fired. Run `python -m scripts.dipcall3_kills` first "
            "and READ it." % p)
    with io.open(p, encoding="utf-8") as fh:
        k = json.load(fh)
    cleared = k.get("cells_cleared_for_the_arm") or []
    if not cleared:
        fired = [g for g, v in (k.get("gates") or {}).items() if not v]
        raise SystemExit(
            "REFUSING: the kill pass RAN and cleared NO cell (gates fired: %s). A kill firing "
            "stops the program at zero further trials and is the cheapest good outcome available "
            "to it. The bars may not be relaxed after watching them fail (W-28)."
            % ", ".join(fired))
    # K0/K2/K3/K4 are PROGRAM-level and must all pass even when K1 is per-cell.
    for g in ("K0_tier_size", "K2_news_coverage", "K3_not_a_volatility_sort", "K4_power_table"):
        if not (k.get("gates") or {}).get(g):
            raise SystemExit("REFUSING: the program-level gate %s FIRED. Only K1 is a per-cell "
                             "refusal; the rest stop everything." % g)
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=float, default=D.K_PRIMARY)
    ap.add_argument("--draws", type=int, default=D.PERMUTATION_DRAWS)
    a = ap.parse_args()

    kills = require_kills()
    cleared = set(kills["cells_cleared_for_the_arm"])
    refused = set(kills["K1_design_effect"]["cells_refused"])
    cfg = D.era(ERA)
    n_eq = research_log.trial_count(domain="equity")
    crit = hlz_hurdle(n_eq)
    print("DIP-CALL-3 ARM  era %s..%s  k = %.1f  draws %d"
          % (cfg["lo"], cfg["hi"], a.k, a.draws))
    print("equity N = %d ; hurdle %.7f ; EVERY CRITICAL VALUE LABELLED UNCALIBRATED"
          % (n_eq, crit))
    print("cells CLEARED: %s" % sorted(cleared))
    print("cells REFUSED by K1 and NOT RUN: %s   <-- the faithful replication of DIP-CALL-2's\n"
          "    no-news arm is in this list, so it is NOT TESTED here (section 5 void cond. 3)\n"
          % sorted(refused))

    sched, universe = D.tier_schedule_era(ERA)
    ever_tier = sorted(t for t, v in sched.items()
                       if v and max(c for _, c in v) >= D.TIER_FLOOR)
    names = [t for t in ever_tier
             if os.path.isfile(os.path.join(D.prices_dir(), "%s.csv" % t))]
    print("pass 1 of 2 - the era's cap-weighted market (A8/B8), %d tier names ..." % len(names))
    market = ARM.build_market(names, sched, a.k, lo=cfg["lo"], hi=cfg["hi"])
    mdates = market["dates"]
    print("  market: %d sessions %s..%s\n" % (len(mdates), mdates[0], mdates[-1]))

    last = len(mdates) - 1
    cutoff = {h: max(0, last - h) for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]}
    is_early = np.array([d < cfg["half_boundary"] for d in mdates])
    emb = {}
    for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]:
        j2 = np.minimum(np.arange(len(mdates)) + h, last)
        emb[h] = is_early & (~is_early[j2])
    print("  horizon cutoff dates: %s"
          % {("h%d" % h): mdates[cutoff[h]] for h in sorted(cutoff)})
    print("  embargoed sessions:   %s\n" % {("h%d" % h): int(emb[h].sum()) for h in sorted(emb)})

    term = ARM.terminal_names()
    print("pass 2 of 2 - abnormal returns, arm rows and the permutation pools ...")
    pool = {h: {"d": [], "own": [], "mkt": [], "tier": []} for h in cfg["horizons_primary"]}
    rows = {h: {"d": [], "t": [], "own": [], "mkt": [], "tier": []}
            for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]}
    cens = {"administrative_dropped": 0, "terminal_used": 0}
    t0 = time.time()
    for i, t in enumerate(names):
        s = D.name_frame(t, sched.get(t, []), k=a.k)
        if s is None:
            continue
        dates = s["date"].tolist()
        dcode = np.array([market["index"].get(d, -1) for d in dates], dtype=np.int64)
        close = s["close"].to_numpy(dtype=float)
        ret = s["ret"].to_numpy(dtype=float)
        sc = s["scoreable"].to_numpy()
        tr = s["tier"].to_numpy()
        evf = s["event"].to_numpy()
        inb = dcode >= 0
        is_term = t in term
        for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]:
            ar_own, ar_mkt, usable, tu = ARM.abnormal(close, ret, dcode, market, h, is_term)
            elig = inb & sc & (dcode <= cutoff[h]) & ~emb[h][np.clip(dcode, 0, None)]
            good = elig & usable & np.isfinite(ar_own) & np.isfinite(ar_mkt)
            cens["administrative_dropped"] += int((elig & ~usable).sum())
            cens["terminal_used"] += int((good & tu).sum())
            if h in cfg["horizons_primary"] and good.any():
                pool[h]["d"].append(dcode[good].astype(np.int32))
                pool[h]["own"].append((ar_own[good] * 100.0).astype(np.float32))
                pool[h]["mkt"].append((ar_mkt[good] * 100.0).astype(np.float32))
                pool[h]["tier"].append(tr[good])
            m = good & evf
            if m.any():
                rows[h]["d"].append(dcode[m].astype(np.int32))
                rows[h]["t"].append(np.full(int(m.sum()), i, dtype=np.int32))
                rows[h]["own"].append((ar_own[m] * 100.0).astype(np.float32))
                rows[h]["mkt"].append((ar_mkt[m] * 100.0).astype(np.float32))
                rows[h]["tier"].append(tr[m])
        if i and i % 150 == 0:
            print("  %d/%d names, %.0fs" % (i, len(names), time.time() - t0))

    def cat(dd, key):
        return np.concatenate(dd[key]) if dd[key] else np.array([])
    for h in list(pool):
        for key in list(pool[h]):
            pool[h][key] = cat(pool[h], key)
    for h in list(rows):
        for key in list(rows[h]):
            rows[h][key] = cat(rows[h], key)
    print("  built in %.0fs ; pool sizes %s\n"
          % (time.time() - t0, {("h%d" % h): int(len(pool[h]["d"])) for h in pool}))

    # ------------------------------------------------------------------------------- score
    cells, halves = {}, {}
    for pop in ("tier", "full"):
        for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]:
            R = rows[h]
            if not len(R["d"]):
                continue
            pm = R["tier"].astype(bool) if pop == "tier" else np.ones(len(R["d"]), bool)
            if pm.sum() < 10:
                continue
            key = "%s|pooled|h%d" % (pop, h)
            entry = {"n": int(pm.sum()),
                     "RUN": bool(("pooled|h%d" % h) in cleared) or h not in
                     cfg["horizons_primary"]}
            for defn in ("own", "mkt"):
                y = R[defn][pm].astype(np.float64)
                dcl, tcl = R["d"][pm], R["t"][pm]
                m_d, se_d, t_d, g_d = ARM.clustered(y, dcl)
                m_n, se_n, t_n, g_n = ARM.clustered(y, tcl)
                rec = {"mean_pp": m_d, "median_pp": float(np.median(y)),
                       "realised_sd_pp": float(np.std(y, ddof=1)),
                       "date_clustered": {"se_pp": se_d, "t": t_d, "clusters": g_d,
                                          "p_two_sided": ARM.two_sided_p(t_d)},
                       "name_clustered": {"se_pp": se_n, "t": t_n, "clusters": g_n,
                                          "p_two_sided": ARM.two_sided_p(t_n)}}
                for lbl, se in (("date", se_d), ("name", se_n)):
                    if se and np.isfinite(se) and se > 0:
                        rec["mde_%s_clustered" % lbl] = {
                            "detection_threshold_50pc_power":
                                power_gate.detection_threshold(se, n_trials=n_eq),
                            "mde_80pc_power": (crit + power_gate.Z_POWER_CONVENTION) * se,
                            "power_against_economic_floor":
                                power_gate.power_at(D.ECONOMIC_FLOOR_PP, se, n_trials=n_eq)}
                if h in cfg["horizons_primary"]:
                    P = pool[h]
                    ppm = P["tier"].astype(bool) if pop == "tier" else \
                        np.ones(len(P["d"]), bool)
                    perm = ARM.permutation_null(P[defn][ppm].astype(np.float64), P["d"][ppm],
                                                dcl, a.draws, 0)
                    perm["clears_p95"] = bool(np.isfinite(perm["p95"]) and m_d > perm["p95"])
                    rec["permutation"] = perm
                entry[defn] = rec
            cells[key] = entry
            for half in ("early", "late"):
                hm = pm & (is_early[R["d"]] if half == "early" else ~is_early[R["d"]])
                if hm.sum() < 10:
                    halves["%s|%s" % (key, half)] = {"n": int(hm.sum())}
                    continue
                hc = {"n": int(hm.sum())}
                for defn in ("own", "mkt"):
                    y = R[defn][hm].astype(np.float64)
                    m_d, se_d, t_d, _ = ARM.clustered(y, R["d"][hm])
                    m_n, se_n, t_n, _ = ARM.clustered(y, R["t"][hm])
                    hc[defn] = {"mean_pp": m_d, "median_pp": float(np.median(y)),
                                "date_clustered": {"se_pp": se_d, "t": t_d},
                                "name_clustered": {"se_pp": se_n, "t": t_n}}
                halves["%s|%s" % (key, half)] = hc

    # ------------------------------------------------------------------- section 2 verdict
    # EVERY REGISTERED CELL GETS A VERDICT ROW, including the ones `K1` refused. A refused cell
    # that is simply absent from this dict reads as a design that never had the arm, which is
    # `DIP-CALL-2`'s `C2` failure in a new costume -- and here the refused cells are precisely
    # the faithful replication, so their absence would be the most misleading thing in the file.
    verdicts, bh_in = {}, []
    for label in sorted(cleared | refused):
        if label not in cleared:
            verdicts[label] = {"verdict": "NOT RUN - K1 REFUSED",
                               "why": "effective n below max(1865, the era's own re-derived "
                                      "requirement); PREREG_dipcall3.md B3/K1. NOT a null: this "
                                      "cell is UNTESTED and carries no number in either "
                                      "direction.",
                               "n": kills["K1_design_effect"]["by_cell"].get(label, {}).get("n"),
                               "n_eff": kills["K1_design_effect"]["by_cell"].get(label, {})
                               .get("n_eff_applied"),
                               "bar": kills["K1_design_effect"]["by_cell"].get(label, {})
                               .get("bar")}
            continue
        fc = cells.get("tier|%s" % label)
        if not fc:
            verdicts[label] = {"verdict": "NOT ASSESSABLE", "why": "no tier rows"}
            continue
        checks = {}
        for defn in ("own", "mkt"):
            r = fc[defn]
            e = {"positive": bool(r["mean_pp"] > 0),
                 "economic_floor": bool(r["mean_pp"] >= D.ECONOMIC_FLOOR_PP),
                 "date_clustered_t": bool(abs(r["date_clustered"]["t"]) > crit),
                 "name_clustered_t": bool(abs(r["name_clustered"]["t"]) > crit),
                 "permutation": bool(r.get("permutation", {}).get("clears_p95"))}
            hv = {x: halves.get("tier|%s|%s" % (label, x)) for x in ("early", "late")}
            e["both_halves_same_sign"] = bool(all(
                hv[x] and defn in hv[x] and hv[x][defn]["mean_pp"] > 0
                for x in ("early", "late")))
            e["both_halves_clear_floor"] = bool(all(
                hv[x] and defn in hv[x]
                and hv[x][defn]["mean_pp"] >= D.ECONOMIC_FLOOR_PP
                for x in ("early", "late")))
            checks[defn] = e
        passed = all(all(v.values()) for v in checks.values())
        p_bh = max(fc["own"]["date_clustered"]["p_two_sided"],
                   fc["own"]["name_clustered"]["p_two_sided"])
        bh_in.append((label, p_bh))
        verdicts[label] = {"verdict": "PASSES SECTION 2 PRE-BH" if passed else "FAILS",
                           "checks": checks, "p_for_bh": p_bh,
                           "halves": {x: halves.get("tier|%s|%s" % (label, x))
                                      for x in ("early", "late")}}

    bh_in.sort(key=lambda x: (x[1] if x[1] == x[1] else 1.0))
    bh = []
    for i, (label, p) in enumerate(bh_in, start=1):
        thr = i * D.BH_Q / 4.0                      # k = 4 FIXED (section 4)
        bh.append({"rank": i, "arm": label, "p_two_sided": p, "bh_threshold": thr,
                   "survives": bool(p == p and p <= thr)})
    surv = {x["arm"]: x["survives"] for x in bh}
    for label, v in verdicts.items():
        if v.get("verdict") == "PASSES SECTION 2 PRE-BH":
            v["bh_survives"] = surv.get(label, False)
            v["verdict"] = "PASSES" if v["bh_survives"] else "FAILS (BH)"
    passing = [k for k, v in verdicts.items() if v.get("verdict") == "PASSES"]

    art = {"item": "DIP-CALL-3 arm (1999-2008, SHARES)",
           "register": "PREREG_dipcall3.md committed ALONE at 4d50597",
           "trials_booked_at": "6c40cb4 (equity 293 -> 297)",
           "era": ERA, "era_window": [cfg["lo"], cfg["hi"]],
           "cells_cleared": sorted(cleared), "cells_refused_by_K1_and_NOT_RUN": sorted(refused),
           "equity_N": n_eq, "hlz_hurdle_equity": crit,
           "critical_values": "EVERY ONE LABELLED UNCALIBRATED (V2G, R1-VAR)",
           "k": a.k, "permutation_draws": a.draws, "p_is_two_sided": True,
           "economic_floor_pp": D.ECONOMIC_FLOOR_PP,
           "bh": {"q": D.BH_Q, "k": 4, "rows": bh,
                  "note": "k is FIXED at 4; a cell NOT RUN does not shrink it (W-28)"},
           "market_leg": {"construction": "cap-weighted daily return of the era's own panel tier "
                                          "names with price files, 1999-2008, weights from the "
                                          "most recent PRIOR quarterly market_cap (A8/B8)",
                          "sessions": len(mdates), "first": mdates[0], "last": mdates[-1],
                          "ken_french_used": False},
           "horizon_cutoff_dates": {("h%d" % h): mdates[cutoff[h]] for h in sorted(cutoff)},
           "embargoed_sessions": {("h%d" % h): int(emb[h].sum()) for h in sorted(emb)},
           "censoring": cens, "full_sample_cells": cells, "half_cells": halves,
           "verdicts": verdicts, "passing_cells": passing, "step1_pass": bool(passing),
           "sensitivity_horizons_carry_no_verdict": list(cfg["horizons_sensitivity"])}
    with io.open(D.out_path("%s_ARM.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)

    print("=" * 108)
    print("CELLS - the $10B TIER GOVERNS; the full universe is a REPORTED SURFACE")
    print("=" * 108)
    for key in sorted(cells):
        e = cells[key]
        for defn in ("own", "mkt"):
            if defn not in e:
                continue
            r = e[defn]
            p95 = (r.get("permutation") or {}).get("p95")
            print("%-22s %-4s n %6d  mean %+8.4fpp  med %+8.4fpp  t_d %+7.3f  t_n %+7.3f  "
                  "perm95 %s  sd %7.3f"
                  % (key, defn, e["n"], r["mean_pp"], r["median_pp"],
                     r["date_clustered"]["t"], r["name_clustered"]["t"],
                     ("%+8.4f" % p95) if isinstance(p95, float) and p95 == p95 else "     n/a",
                     r["realised_sd_pp"]))
    print()
    print("=" * 108)
    print("HALVES (tier, primary horizons)  boundary %s" % cfg["half_boundary"])
    print("=" * 108)
    for key in sorted(halves):
        if not key.startswith("tier|") or "h5|" in key or "h21|" in key:
            continue
        c = halves[key]
        if "own" not in c:
            print("%-34s n %6d  (too thin)" % (key, c["n"]))
            continue
        print("%-34s n %6d  own %+8.4fpp (t_d %+7.3f)  mkt %+8.4fpp (t_d %+7.3f)"
              % (key, c["n"], c["own"]["mean_pp"], c["own"]["date_clustered"]["t"],
                 c["mkt"]["mean_pp"], c["mkt"]["date_clustered"]["t"]))
    print()
    print("=" * 108)
    print("VERDICTS - hurdle %.4f (UNCALIBRATED), economic floor +%.2fpp/window"
          % (crit, D.ECONOMIC_FLOOR_PP))
    print("=" * 108)
    for label in sorted(verdicts):
        v = verdicts[label]
        print("%-16s %s" % (label, v["verdict"]))
        for defn, c in (v.get("checks") or {}).items():
            bad = [kk for kk, vv in c.items() if not vv]
            print("     %-4s %s" % (defn, "all met" if not bad else "FAILS: " + ", ".join(bad)))
    print("\nBH q=%.2f k=4 (TWO-SIDED p):" % D.BH_Q)
    for x in bh:
        print("  rank %d  %-16s p %.6g vs %.5f -> %s"
              % (x["rank"], x["arm"], x["p_two_sided"], x["bh_threshold"],
                 "survives" if x["survives"] else "does not survive"))
    print("\nPASSING CELLS: %s" % (passing or "NONE"))
    print("wrote %s" % D.out_path("%s_ARM.json" % PREFIX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
