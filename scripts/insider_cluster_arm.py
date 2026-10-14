# -*- coding: utf-8 -*-
"""`INSIDER-CLUSTER` — THE ARM. The only pass in this item that reads a forward return.

    python -m scripts.insider_cluster_arm

Register: `PREREG_insider_cluster.md`, committed **ALONE at `fd87870`**; **Amendment 1 ALONE at
`826d0b5`**, both markdown only and both strict git ancestors of this file. Trials booked at
`4a34a00` (equity 297 -> 301) **before this file existed**.

**IT REFUSES WITHOUT A PASSING KILL ARTIFACT.** `O10`'s process defect was a gating control and
its outcomes running in one pass; `scripts/insider_cluster_kills.py` is a separate invocation and
its artifact is read here, never recomputed.

**EVERY BAR IS THE REGISTER'S AND NONE IS DEFINED HERE.** §6's five clauses, §5's co-primary
horizons, §7's assessable-cell list. `MA28`'s rule: changing a constant after a measurement voids
the item. `W-28`'s: a bar may be RAISED and never LOWERED once watched.

**EVERY STATISTIC IS DELEGATED** to `scripts/dipcall_arm.py` — the cap-weighted market, the
abnormal-return pair, the two-way clustered standard errors, the within-date permutation null and
the two-sided *p*. A second implementation of any of those would be the `B7` split, and the whole
point of reusing them is that `DIP-CALL` already validated them.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import power_gate as PG                                 # noqa: E402
from valuation.edge import statistics as ST                                 # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402
from scripts import dipcall_arm as DA                                       # noqa: E402

#: THE CO-PRIMARY ARTIFACT, and the sensitivity horizons write ELSEWHERE. A run at `--horizons
#: 5,21` would otherwise overwrite the canonical file with cells the register gives NO VERDICT,
#: and a later reader would find a verdict-free artifact under the verdict's own name. Caught by
#: noticing the hazard rather than by losing the file; the `W-1` family, where a harness that
#: cannot put something back is worse than none.
OUT = "INSIDER_CLUSTER_ARM.json"
OUT_SENSITIVITY = "INSIDER_CLUSTER_ARM_sensitivity.json"

HORIZONS_PRIMARY = (63, 126)                 # register §5, Amendment 1
HORIZONS_SENSITIVITY = (5, 21)               # §5, NO VERDICT
COST_FLOOR_PP = 0.67                         # §6 A4
PERMUTATION_DRAWS = 500                      # §4
BH_Q = 0.10                                  # §6 A5
BH_K = 2                                     # §6 A5, FIXED, never shrunk
T_BAR = 2.0                                  # §6 A3, LABELLED UNCALIBRATED


def _kills() -> dict:
    p = D.out_path("INSIDER_CLUSTER_KILLS.json")
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: no kill artifact at %s. The register's section 7 kills are FREE and are "
            "read in their own pass before any outcome -- run `python -m "
            "scripts.insider_cluster_kills` first (O10's process defect)." % p)
    k = json.load(io.open(p, encoding="utf-8"))
    if not k.get("all_stopping_kills_pass"):
        raise SystemExit(
            "REFUSING: a STOPPING kill fired (K2 dip overlap / K3 costume / K4 look-ahead). The "
            "register stops the item; the arm does not run.")
    return k


def build_events() -> pd.DataFrame:
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % IC.K_PRIMARY)
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: no banked event set at %s" % p)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    return ev[(ev["era"] == "build") & (ev["half"] == 0)].reset_index(drop=True)


def score(ev: pd.DataFrame, market: dict, sched: dict, terminal: set,
          h: int, tier_only: bool) -> dict:
    """One cell: mean abnormal return at horizon `h`, both legs, with the pool for the null.

    The POOL is every scoreable session of every half-0 name inside the build window — the same
    population the permutation shuffles the event flag across. `A9`'s entry convention: the
    horizon runs over sessions `t+1 … t+h`, so the event session's own return is never inside it.
    """
    by_tk = {t: set(g["date"].astype(str)) for t, g in ev.groupby("ticker")}
    rows = {"own": [], "mkt": [], "date": [], "ticker": []}
    pool = {"own": [], "mkt": [], "date": []}
    n_terminal = 0
    # One pass over every half-0 name with a price file: the ARM rows come from the event dates
    # and the POOL from every scoreable session, so both come from one read of each series.
    names = sorted(set(ev["ticker"].tolist()))
    for i, tk in enumerate(names):
        f = D.name_frame(tk, sched.get(tk, []), k=D.K_PRIMARY)
        if f is None:
            continue
        dates = f["date"].astype(str).to_numpy()
        close = f["close"].to_numpy(dtype=float)
        ret = f["ret"].to_numpy(dtype=float)
        dcode = np.array([market["index"].get(d, -1) for d in dates], dtype=np.int64)
        ar_own, ar_mkt, ok, term = DA.abnormal(close, ret, dcode, market, h,
                                               tk in terminal)
        inb = np.array([D.BUILD_LO <= d <= D.BUILD_HI for d in dates])
        tier = f["tier"].to_numpy(dtype=bool)
        keep = ok & inb & np.isfinite(ar_own) & np.isfinite(ar_mkt)
        if tier_only:
            keep = keep & tier
        evset = by_tk.get(tk, set())
        is_ev = np.array([d in evset for d in dates])
        n_terminal += int((term & keep & is_ev).sum())
        for j in np.flatnonzero(keep):
            pool["own"].append(ar_own[j]); pool["mkt"].append(ar_mkt[j])
            pool["date"].append(dates[j])
            if is_ev[j]:
                rows["own"].append(ar_own[j]); rows["mkt"].append(ar_mkt[j])
                rows["date"].append(dates[j]); rows["ticker"].append(tk)
        if i and i % 400 == 0:
            print("      %d/%d names, %d event rows" % (i, len(names), len(rows["own"])),
                  flush=True)

    # RULE 9: STORE THE DRAWS, NOT JUST THE SUMMARY -- and bank the INPUTS to every derived
    # statistic, not only the derived number. X7 kept 100 placebo draws as five summary rates and
    # an 8%-vs-7% mismatch sat undiagnosable for two sessions. This item needed it within the
    # hour: the late half's permutation p95 came back 0.0923pp against the full sample's 0.8589pp,
    # which is backwards, and diagnosing it from the summary alone would have meant a 5-minute
    # re-run per question.
    tag = "%s_h%d" % ("tier" if tier_only else "full", h)
    pd.DataFrame(rows).to_pickle(D.out_path("INSIDER_CLUSTER_ROWS_%s.pkl" % tag))
    pd.DataFrame(pool).to_pickle(D.out_path("INSIDER_CLUSTER_POOL_%s.pkl" % tag))

    out = {"h": h, "tier_only": bool(tier_only), "n_events_scored": len(rows["own"]),
           "n_pool": len(pool["own"]), "n_terminal_used": n_terminal,
           "rows_pkl": "INSIDER_CLUSTER_ROWS_%s.pkl" % tag,
           "pool_pkl": "INSIDER_CLUSTER_POOL_%s.pkl" % tag}
    if len(rows["own"]) < 3:
        out["status"] = "NO ROWS"
        return out

    d_arr = np.asarray(rows["date"], dtype=object)
    t_arr = np.asarray(rows["ticker"], dtype=object)
    early = d_arr < D.HALF_BOUNDARY
    out["halves"] = {"early": int(early.sum()), "late": int((~early).sum())}

    for leg in ("own", "mkt"):
        y = np.asarray(rows[leg], dtype=float)
        blk = {}
        m, se_d, t_d, g_d = DA.clustered(y, d_arr)
        _m, se_t, t_t, g_t = DA.clustered(y, t_arr)
        blk["mean_pp"] = m * 100.0
        blk["se_date_pp"], blk["t_date"], blk["n_date_clusters"] = se_d * 100.0, t_d, g_d
        blk["se_ticker_pp"], blk["t_ticker"], blk["n_ticker_clusters"] = se_t * 100.0, t_t, g_t
        blk["t_min_abs"] = float(min(abs(t_d), abs(t_t)))
        blk["p_two_sided_worst"] = DA.two_sided_p(blk["t_min_abs"])
        # §4's permutation null, on the same pool
        nul = DA.permutation_null(np.asarray(pool[leg], dtype=float),
                                  np.asarray(pool["date"], dtype=object),
                                  d_arr, PERMUTATION_DRAWS, seed=1000 + h)
        blk["null_p95_pp"] = nul["p95"] * 100.0
        blk["null_mean_pp"] = nul["null_mean"] * 100.0
        blk["null_events_used"] = nul.get("events_used")
        blk["null_draws"] = nul.get("draws")
        blk["clears_own_null"] = bool(np.isfinite(nul["p95"]) and m > nul["p95"])
        # halves, each against ITS OWN null
        hv = {}
        for nm, msk in (("early", early), ("late", ~early)):
            yy, dd = y[msk], d_arr[msk]
            if len(yy) < 3:
                hv[nm] = {"status": "too few rows"}
                continue
            mm, sse, tt, gg = DA.clustered(yy, dd)
            n2 = DA.permutation_null(np.asarray(pool[leg], dtype=float),
                                     np.asarray(pool["date"], dtype=object),
                                     dd, PERMUTATION_DRAWS, seed=2000 + h)
            hv[nm] = {"n": int(len(yy)), "mean_pp": mm * 100.0, "t": tt,
                      "se_pp": sse * 100.0, "n_date_clusters": gg,
                      "null_p95_pp": n2["p95"] * 100.0,
                      "null_mean_pp": n2["null_mean"] * 100.0,
                      "null_events_used": n2.get("events_used"),
                      "n_event_dates": int(len(set(dd.tolist()))),
                      "clears": bool(np.isfinite(n2["p95"]) and mm > n2["p95"])}
        blk["halves"] = hv
        signs = [hv.get(x, {}).get("mean_pp") for x in ("early", "late")]
        blk["halves_same_sign"] = bool(all(s is not None and np.isfinite(s) for s in signs)
                                       and (signs[0] > 0) == (signs[1] > 0))
        blk["both_halves_clear"] = bool(hv.get("early", {}).get("clears")
                                        and hv.get("late", {}).get("clears"))
        # THE MDE THAT TRAVELS WITH THE VERDICT IS THE ARM'S OWN (MB8: never borrow an se), and
        # it is taken on the WORSE of the two clusterings because the register requires clearing
        # under both.
        se_worst = max(se_d, se_t)
        blk["mde80_pp_own_se"] = (T_BAR + PG.z_for_power(0.80)) * se_worst * 100.0
        blk["power_state_own_se"] = PG.state(m, se_worst, crit=T_BAR)
        # §6's five clauses
        blk["A1_sign_positive"] = bool(m > 0)
        blk["A2_own_null_and_both_halves"] = bool(blk["clears_own_null"]
                                                  and blk["both_halves_clear"]
                                                  and blk["halves_same_sign"])
        blk["A3_t_over_bar_both_clusterings"] = bool(blk["t_min_abs"] > T_BAR and m > 0)
        blk["A4_economic"] = bool(blk["mean_pp"] > COST_FLOOR_PP)
        out[leg] = blk

    # QUOTING ONE LEG ALONE IS FORBIDDEN (§4), so the cell's clause verdicts require BOTH legs.
    out["clauses_both_legs"] = {
        c: bool(out["own"].get(c) and out["mkt"].get(c))
        for c in ("A1_sign_positive", "A2_own_null_and_both_halves",
                  "A3_t_over_bar_both_clusterings", "A4_economic")
    }
    out["A1_A4_all_pass"] = all(out["clauses_both_legs"].values())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", default=",".join(str(x) for x in HORIZONS_PRIMARY))
    a = ap.parse_args(argv)
    t0 = time.time()

    kills = _kills()
    assessable = set(kills["assessable_cells"])
    print("[arm] kill artifact read: assessable cells %s" % sorted(assessable), flush=True)

    ev = build_events()
    sched = D.tier_schedule()
    names = DA.half0_names()
    print("[arm] pass 1 of 2 -- the half-0 cap-weighted market (A8) over %d names ..."
          % len(names), flush=True)
    market = DA.build_market(names, sched, D.K_PRIMARY)
    terminal = DA.terminal_names()
    print("[arm] market built in %.0fs, %d sessions" % (time.time() - t0,
                                                        len(market["dates"])), flush=True)

    out = {"item": "INSIDER-CLUSTER", "part": "the arm",
           "register": "PREREG_insider_cluster.md",
           "register_commit": "fd87870", "amendment_commit": "826d0b5",
           "trials_booked_at": "4a34a00",
           "kills": {"all_stopping_kills_pass": True,
                     "assessable_cells": sorted(assessable),
                     "K2_dip_overlap_share": kills["K2_dip_overlap"]["share"],
                     "K3_worst_costume": kills["K3_costume"]["worst"]},
           "bars": {"t_bar": T_BAR, "t_bar_LABEL": "UNCALIBRATED (V2G, R1-VAR) -- no X7 or "
                                                   "CORRECTED-FLOORS figure transfers here",
                    "cost_floor_pp": COST_FLOOR_PP, "bh_q": BH_Q, "bh_k": BH_K,
                    "permutation_draws": PERMUTATION_DRAWS},
           "cells": {}}

    horizons = [int(x) for x in a.horizons.split(",") if x.strip()]
    for h in horizons:
        for tier_only in (False, True):
            name = "%s_h%d" % ("tier_cap_ge_10bn" if tier_only else "full_universe", h)
            print("[arm] scoring %s ..." % name, flush=True)
            cell = score(ev, market, sched, terminal, h, tier_only)
            cell["assessable_per_K1"] = bool(name in assessable)
            if not cell["assessable_per_K1"]:
                # DECLARED IN ADVANCE (register section 7 K1). A tier null is NOT a null.
                cell["verdict"] = "UNDERPOWERED-BY-CONSTRUCTION"
                cell["verdict_note"] = (
                    "K1 fired on this cell BEFORE any outcome: its event count is below the "
                    "register's derived required n, and the register declared the power (7.4 "
                    "percent at h=63, 10.4 at h=126 on the clustered bound) in advance. The "
                    "numbers below are reported because Stage 1b makes the tier reading GOVERN "
                    "advancement and a population nobody looks at cannot govern anything -- they "
                    "are NOT a null and may not be read as absence.")
            out["cells"][name] = cell
            if "own" in cell:
                print("    own %+.4fpp t %.3f/%.3f | mkt %+.4fpp t %.3f/%.3f | A1-A4 %s"
                      % (cell["own"]["mean_pp"], cell["own"]["t_date"], cell["own"]["t_ticker"],
                         cell["mkt"]["mean_pp"], cell["mkt"]["t_date"], cell["mkt"]["t_ticker"],
                         cell["A1_A4_all_pass"]), flush=True)

    # ---------------------------------------------------------------- §6 A5, Benjamini-Hochberg
    batch = [(n, c) for n, c in out["cells"].items() if c.get("assessable_per_K1")]
    ps = sorted(((c["own"]["p_two_sided_worst"] + c["mkt"]["p_two_sided_worst"]) / 2.0, n)
                for n, c in batch if "own" in c)
    bh = {"q": BH_Q, "k_fixed": BH_K, "k_in_batch": len(ps), "cells": {}}
    if len(ps) != BH_K:
        bh["NOTE"] = ("k is FIXED at %d in the register and is never shrunk; %d assessable cells "
                      "were scored. A smaller batch is reported, never used to lower the "
                      "threshold." % (BH_K, len(ps)))
    for i, (p, n) in enumerate(ps, 1):
        thr = i * BH_Q / BH_K
        bh["cells"][n] = {"p": p, "threshold": thr, "survives": bool(p <= thr)}
    out["A5_bh"] = bh
    out["excluded_from_bh"] = {
        "cells": sorted(n for n, c in out["cells"].items() if not c.get("assessable_per_K1")),
        "WHY": ("K1 fires on them before any outcome, so they carry no p to correct -- charter "
                "Stage 1a's rule that an arm without a calibrated p is excluded WITH the "
                "exclusion declared in the register (section 6 A5 does declare it)"),
    }

    # ---------------------------------------------------------------------------- the verdicts
    for n, c in out["cells"].items():
        if not c.get("assessable_per_K1"):
            continue
        a5 = out["A5_bh"]["cells"].get(n, {}).get("survives", False)
        c["A5_bh_survives"] = bool(a5)
        c["verdict"] = "CLEARS" if (c.get("A1_A4_all_pass") and a5) else "NULL"
        c["verdict_note"] = ("all five clauses of section 6 under BOTH return definitions"
                             if c["verdict"] == "CLEARS" else
                             "at least one of section 6's five clauses failed; the register makes "
                             "any other outcome a NULL, and the MDE travels with it")

    n_eq = 0
    try:
        from valuation.edge import research_log as RL
        n_eq = RL.detail()["by_domain"]["equity"]
    except Exception:                                                       # noqa: BLE001
        pass
    out["hlz_hurdle_reported_not_gated"] = {
        "equity_N": n_eq, "hurdle": (ST.hlz_hurdle(n_eq) if n_eq else None),
        "WHY_NOT_GATED": ("R4's measured reason: HLZ prices the BEST OF N draws, and these five "
                          "reads are what the literature already published -- they were not "
                          "selected out of this record. Reported beside every cell."),
    }
    out["seconds"] = round(time.time() - t0, 1)

    primary = set(HORIZONS_PRIMARY)
    is_primary = set(horizons) == primary
    out["is_co_primary_run"] = bool(is_primary)
    if not is_primary:
        out["NOT_THE_VERDICT"] = (
            "these horizons are the register's declared SENSITIVITY and carry NO VERDICT "
            "(section 5: their hypothesised effect is below the round-trip cost of trading it, "
            "so they could not pass clause A4 even if exactly true). Written to a separate "
            "artifact so the co-primary file keeps the verdict's own name.")
        for c in out["cells"].values():
            c["verdict"] = "SENSITIVITY -- NO VERDICT"
    p = D.out_path(OUT if is_primary else OUT_SENSITIVITY)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[arm] verdicts: %s"
          % json.dumps({n: c.get("verdict") for n, c in out["cells"].items()}), flush=True)
    print("[arm] wrote %s in %.0fs" % (p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
