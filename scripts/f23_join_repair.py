# -*- coding: utf-8 -*-
"""`F23-JOIN` — the SEC ticker join, measured BEFORE and AFTER the repair. Reads no outcome.

    python -m scripts.f23_join_repair

**THIS IS AN INSTRUMENT MEASUREMENT, NOT AN ARM.** No forward return is loaded and no verdict is
computed anywhere in this module; a test asserts that. `F23-SECID` reported its own SF2 gap as a
**join** problem and explicitly declined to attribute it; this file measures the join and the
repair, and the registered check is then re-run unchanged on the repaired key.

**WHAT IS COMPARED, AND IT IS THE SAME DEFINITION ON BOTH SIDES.** The two columns differ in the
ticker key alone — identical rows, identical cluster rule, identical build cell, identical cap
schedule — so a difference is attributable to the join. Quoting one definition for the old join and
a kinder one for the new would be the wrong-object family on the very number that licenses the
re-run.
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

from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import sec_ticker_join as SJ                         # noqa: E402
from scripts import f23_secid_events as EV                                  # noqa: E402
from scripts import insider_wide_tier_choice as TC                          # noqa: E402

OUT = "F23_JOIN_REPAIR.json"
SF2_EVENTS = "INSIDER_CLUSTER_EVENTS_k2.csv"
FLOOR = 500e6                    # the registered cell, so the counts are the registered ones


def panel_tickers() -> set:
    d = pd.read_pickle(D.panel_path())
    return {str(t).upper() for t in d["ticker"].unique()}


def sf2_build_cell_tickers() -> set:
    """SF2's own build-cell event tickers — the reference set the SEC cell is compared against.

    Restricted to the build era AND ticker half 0, because an unrestricted SF2 set would make the
    SEC side look narrower than it is for a reason that has nothing to do with the join.
    """
    p = D.out_path(SF2_EVENTS)
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: SF2 event set absent at %s -- the before/after ticker overlap "
                         "has no reference set without it, and reporting the SEC side alone would "
                         "invite reading it as a coverage figure." % p)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    ev = ev[(ev["date"] >= D.BUILD_LO) & (ev["date"] <= D.BUILD_HI)]
    ev = ev[ev["ticker"].map(D.stable_key_half) == 0]
    return {str(t).upper() for t in ev["ticker"].unique()}


def census(ev: pd.DataFrame, cap_sched: dict, sf2: set) -> dict:
    """One join's build-cell census. `ev` is already the arm's event frame."""
    e = ev[(ev["date"] >= D.BUILD_LO) & (ev["date"] <= D.BUILD_HI)]
    e = e[e["ticker"].map(D.stable_key_half) == 0]
    caps = np.array([TC.cap_at(cap_sched, t, d)
                     for t, d in zip(e["ticker"].astype(str), e["date"].astype(str))],
                    dtype=float)
    fin = np.isfinite(caps)
    tix = {str(t).upper() for t in e["ticker"].unique()}
    n = int(len(e)) or 1
    return {
        "build_cell_events": int(len(e)),
        "build_cell_tickers": int(len(tix)),
        "events_resolving_a_point_in_time_cap": int(fin.sum()),
        "cap_resolution_rate": float(fin.sum()) / n,
        "events_at_cap_floor": int((fin & (caps >= FLOOR)).sum()),
        "tickers_shared_with_sf2": int(len(tix & sf2)),
        "tickers_only_sec": int(len(tix - sf2)),
        "tickers_only_sf2": int(len(sf2 - tix)),
        "share_of_sf2_tickers_reached": float(len(tix & sf2)) / float(max(1, len(sf2))),
    }


def main(argv=None):
    t0 = time.time()
    df = EV.pull()
    build = df[(df["filingdate"] >= D.BUILD_LO) & (df["filingdate"] <= D.BUILD_HI)].copy()
    pan = panel_tickers()
    sf2 = sf2_build_cell_tickers()
    cap_sched = TC.cap_schedule(0)

    out = {"item": "F23-JOIN", "part": "the SEC ticker join, before and after",
           "NO_OUTCOME_READ": ("no forward return is loaded in this module; it reports event "
                               "counts, ticker overlap and cap resolution only"),
           "reference": {"sf2_build_cell_tickers": int(len(sf2)), "artifact": SF2_EVENTS},
           "panel_tickers": int(len(pan)),
           "sec_build_era_purchase_rows": int(len(build))}

    # ------------------------------------------------- the row-level join, before and after
    j = SJ.SecTickerJoin(df, pan)              # the FULL pull, so a CIK's history is complete
    res = j.resolve_frame(build)
    sens = j.resolve_frame_full_history(build)
    before = build["ticker"].isin(pan)
    out["row_level"] = {
        "before_rows_resolved": int(before.sum()),
        "before_rate": float(before.mean()),
        "before_distinct_panel_tickers": int(build.loc[before, "ticker"].nunique()),
        "after_rows_resolved": int((res != "").sum()),
        "after_rate": float((res != "").mean()),
        "after_distinct_panel_tickers": int(res[res != ""].nunique()),
        "ciks_with_a_dated_symbol_history": int(len(j.history)),
        "sensitivity_full_history_rows": int((sens != "").sum()),
        "sensitivity_full_history_rate": float((sens != "").mean()),
        "COST_OF_BACKWARD_LOOKING": int((sens != "").sum() - (res != "").sum()),
        "WHY_THE_SENSITIVITY": ("the full-history variant ignores the filing date and can only "
                                "resolve MORE rows; it is reported so the price of insisting on a "
                                "backward-looking map is visible rather than assumed to be zero"),
    }
    print("[join] rows %d -> %d of %d (%.4f -> %.4f)"
          % (before.sum(), (res != "").sum(), len(build), before.mean(), (res != "").mean()),
          flush=True)

    # --------------------------------------------- the EVENT-level census, both joins, one rule
    for tag, frame in (("before", df), ("after", SJ.repair(df, pan))):
        print("[join] %s: clustering on name_key ..." % tag, flush=True)
        ev = EV.clusters(frame, "name_key")
        out[tag] = census(ev, cap_sched, sf2)
        c = out[tag]
        print("    events %d over %d tickers | cap resolved %.4f | at floor %d | shared with SF2 %d"
              % (c["build_cell_events"], c["build_cell_tickers"], c["cap_resolution_rate"],
                 c["events_at_cap_floor"], c["tickers_shared_with_sf2"]), flush=True)

    out["moved"] = {
        "build_cell_tickers": out["after"]["build_cell_tickers"]
        - out["before"]["build_cell_tickers"],
        "cap_resolution_rate": out["after"]["cap_resolution_rate"]
        - out["before"]["cap_resolution_rate"],
        "events_at_cap_floor": out["after"]["events_at_cap_floor"]
        - out["before"]["events_at_cap_floor"],
        "tickers_shared_with_sf2": out["after"]["tickers_shared_with_sf2"]
        - out["before"]["tickers_shared_with_sf2"],
    }
    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[join] wrote %s in %.0fs" % (p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
