# -*- coding: utf-8 -*-
"""`F23-SECID` — THE ARM. Scores both arms on the BUILD quadrant's `$500M+` cell.

    python -m scripts.f23_secid_events      # FIRST, its own pass
    python -m scripts.f23_secid_arm         # then this

Register: `PREREG_f23_secid.md`, committed **ALONE at `fba290e`**; one equity trial booked at
`8191309` before any runner existed.

**THE CHECK QUADRANT IS NOT TOUCHED.** This reads **2009-2019 x ticker half 0** only — the BUILD
cell, which `RESEARCH_CHARTER.md` §5 licenses reusing. A test asserts the window and half.

**THE SCORING FUNCTION IS `insider_wide_arm.score`, IMPORTED AND CALLED.** That function is
era-parameterised and `INSIDER-WIDE`'s `C1` proved it reproduces stage 1's published build-cell
figures at deviation **exactly 0.0** on all six fields. Writing a second scorer here would be the
`B7` split at the one place the comparison has to be trustworthy.

**ARM A CARRIES NO VERDICT** (register §1). It is the reference the ID rule is read against.
"""
from __future__ import annotations

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
from scripts import dipcall_arm as DA                                       # noqa: E402
from scripts import insider_wide_arm as WA                                  # noqa: E402
from scripts import insider_wide_tier_choice as TC                          # noqa: E402

OUT = "F23_SECID_ARM.json"
EVENTS = "F23_SECID_EVENTS.json"

FLOOR = 500e6                    # register: the cap-over-500M tier
H = 63                           # register: h=63
T_BAR = 2.0                      # register A3, LABELLED UNCALIBRATED
BH_Q = 0.10                      # register A5
BH_K = 1                         # register A5, and §2 states what k=1 is worth


def arm_events(arm: str) -> pd.DataFrame:
    """This arm's events, restricted to the BUILD cell — era window AND ticker half 0.

    Both restrictions are applied HERE and asserted, because the event CSVs span 2007-2019 and
    both ticker halves; scoring them unrestricted would read the cell the charter rations.
    """
    p = D.out_path("F23_SECID_EVENTS_%s.csv" % arm)
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: no event set at %s -- run scripts.f23_secid_events first "
                         "(O10: a gating pass and its outcomes must not share an invocation)." % p)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    ev = ev[(ev["date"] >= D.BUILD_LO) & (ev["date"] <= D.BUILD_HI)]
    ev = ev[ev["ticker"].map(D.stable_key_half) == 0]
    return ev.reset_index(drop=True)


def main(argv=None):
    t0 = time.time()
    ep = D.out_path(EVENTS)
    if not os.path.isfile(ep):
        raise SystemExit("REFUSING: no event artifact at %s" % ep)
    ev_meta = json.load(io.open(ep, encoding="utf-8"))

    sched = D.tier_schedule()
    names = DA.half0_names()
    cap_sched = TC.cap_schedule(0)
    print("[arm] half-0 cap-weighted market over %d names ..." % len(names), flush=True)
    market = DA.build_market(names, sched, D.K_PRIMARY)
    terminal = DA.terminal_names()
    print("[arm] market built in %.0fs, %d sessions"
          % (time.time() - t0, len(market["dates"])), flush=True)

    out = {"item": "F23-SECID", "part": "the arm, BUILD quadrant only",
           "register": "PREREG_f23_secid.md", "register_commit": "fba290e",
           "trial_booked_at": "8191309",
           "cell": {"era": "build", "lo": D.BUILD_LO, "hi": D.BUILD_HI, "ticker_half": 0,
                    "cap_floor_usd": FLOOR, "h": H,
                    "half_boundary": D.HALF_BOUNDARY},
           "CHECK_QUADRANT": "NOT TOUCHED -- spent by INSIDER-WIDE on 2026-10-13",
           "bars": {"t_bar": T_BAR,
                    "t_bar_LABEL": "UNCALIBRATED (V2G, R1-VAR) -- no X7 or CORRECTED-FLOORS "
                                   "figure transfers to a clustered event-time mean",
                    "bh_q": BH_Q, "bh_k": BH_K,
                    "bh_k_WORTH": ("with ONE verdict arm BH at k=1 reduces to p <= 0.10 and does "
                                   "NO correcting work; it is carried for continuity with stage "
                                   "1's clause list and is not evidence of multiplicity control"),
                    "permutation_draws": WA.PERMUTATION_DRAWS},
           "events_from": {"artifact": EVENTS,
                           "identity_census": ev_meta.get("identity_census"),
                           "overlap_all_eras": ev_meta.get("overlap")},
           "arms": {}}

    scored = {}
    for arm, verdicts in (("name", False), ("id", True)):
        ev = arm_events(arm)
        print("[arm] ARM %s: %d build-cell events over %d tickers -> scoring ..."
              % (arm.upper(), len(ev), ev["ticker"].nunique()), flush=True)
        c = WA.score(ev, market, sched, terminal, names, D.BUILD_LO, D.BUILD_HI, H, FLOOR,
                     D.HALF_BOUNDARY, cap_sched, "secid_%s" % arm)
        c["identity_column"] = "cik" if arm == "id" else "name_key"
        c["carries_a_verdict"] = bool(verdicts)
        c["build_cell_events_before_cap_filter"] = int(len(ev))
        scored[arm] = c
        out["arms"][arm] = c
        if "mean_pp" in c:
            print("    n %-5d | mkt %+.4fpp t %+.3f/%+.3f | null p95 %.4f | cost %.3f -> NET "
                  "%+.4fpp | A1-A4 %s"
                  % (c["n_events_scored"], c["mean_pp"], c["t_date"], c["t_ticker"],
                     c["null_p95_pp"], c["roundtrip_cost_pp_mean"], c["net_of_cost_pp"],
                     c["A1_A4_all_pass"]), flush=True)

    # --------------------------------------------------- the BUILD-CELL overlap, per register §4
    ka = set(zip(arm_events("name")["ticker"], arm_events("name")["date"]))
    kb = set(zip(arm_events("id")["ticker"], arm_events("id")["date"]))
    both, union = ka & kb, ka | kb
    out["build_cell_overlap"] = {
        "name_events": len(ka), "id_events": len(kb), "shared": len(both),
        "jaccard": (len(both) / len(union)) if union else None,
        "only_name": len(ka - kb), "only_id": len(kb - ka),
        "share_of_name_events_surviving_under_id": (len(both) / len(ka)) if ka else None,
        "NOT_THE_83_PERCENT": ("the ~83% figure is INSIDER-LIVE-FEED's SEC-vs-SF2 event overlap "
                               "on a 2026 window, a FEED comparison. This is a KEY comparison on "
                               "one feed."),
    }

    # ------------------------------------------------------------------------- A5 and the verdict
    idc = scored["id"]
    p = idc.get("p_two_sided_worst")
    out["A5_bh"] = {"q": BH_Q, "k_fixed": BH_K, "p": p,
                    "threshold": BH_Q, "survives": bool(p is not None and p <= BH_Q),
                    "NOTE": out["bars"]["bh_k_WORTH"]}
    clears = bool(idc.get("A1_A4_all_pass") and out["A5_bh"]["survives"])
    idc["verdict"] = "CLEARS" if clears else "DOES NOT CLEAR"
    idc["verdict_note"] = (
        "all four clauses of the register's section 2 plus BH at k=1"
        if clears else
        "at least one of the register's four clauses failed; the register makes any other "
        "outcome a DOES NOT CLEAR, and section 3 declared IN ADVANCE that a DOES NOT CLEAR at "
        "this cell's ~50% power is NOT evidence that counting by ID is wrong")
    scored["name"]["verdict"] = "REFERENCE -- NO VERDICT"

    # the MDE travels with the verdict, on this arm's own se (MB8)
    if "se_worst_pp" in idc:
        se = float(idc["se_worst_pp"]) / 100.0
        m = float(idc["mean_pp"]) / 100.0
        net = float(idc["net_of_cost_pp"]) / 100.0
        out["power_realised"] = {
            "se_worst_pp": idc["se_worst_pp"],
            "mde80_pp": (T_BAR + PG.z_for_power(0.80)) * se * 100.0,
            "power_vs_own_gross": PG.power_at(m, se, crit=T_BAR),
            "power_vs_own_net": PG.power_at(net, se, crit=T_BAR) if net > 0 else 0.0,
            "declared_in_register": {"power_gross": 0.503, "power_net": 0.147,
                                     "mde80_pp": 1.6030, "se_pp": 0.5641,
                                     "basis": "the NAME rule's own realised build-cell se on "
                                              "SF2 at n 1,378"},
        }

    n_eq = 0
    try:
        from valuation.edge import research_log as RL
        n_eq = RL.detail()["by_domain"]["equity"]
    except Exception:                                                       # noqa: BLE001
        pass
    out["hlz_hurdle_reported_not_gated"] = {
        "equity_N": n_eq, "hurdle": (ST.hlz_hurdle(n_eq) if n_eq else None),
        "WHY_NOT_GATED": ("R4's measured reason, and the register's A3 says so in advance: HLZ "
                          "prices the BEST OF N draws and this is one pre-registered "
                          "re-measurement of one published rule."),
    }
    out["ADOPTS_NOTHING"] = ("No file under valuation/ changes. F-23 moves to the ID rule only if "
                             "this CLEARS, and that move is a declaration change rather than an "
                             "adoption of anything into the live product.")
    out["seconds"] = round(time.time() - t0, 1)

    pth = D.out_path(OUT)
    with io.open(pth, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[arm] build-cell overlap: jaccard %.4f (name %d, id %d, shared %d)"
          % (out["build_cell_overlap"]["jaccard"] or 0,
             out["build_cell_overlap"]["name_events"], out["build_cell_overlap"]["id_events"],
             out["build_cell_overlap"]["shared"]), flush=True)
    print("[arm] VERDICT (ID rule): %s" % idc["verdict"], flush=True)
    print("[arm] wrote %s in %.0fs" % (pth, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
