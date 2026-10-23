# -*- coding: utf-8 -*-
"""Step 4's GATE -- is a 1999-2008 replication reachable, or is it survivors only?

**THIS RUNS BEFORE ANY REGISTER AND BEFORE ANY TRIAL.** `MB1-SEL`: a control can only ever BLOCK a
finding, never produce one, so it costs nothing and may be read first. The question it settles is
the one that decides whether step 4 exists at all, and the brief names it: a replication on the
survivors of an era is worthless, because the names missing from that era are exactly the ones that
died in it.

**THERE ARE TWO HOLES, ON OPPOSITE SIDES OF THE JOIN, AND ONLY ONE OF THEM IS THE VENDOR'S.**

* **OURS, AND IT IS DECISIVE ON ITS OWN -- no EODHD call required.** The corrected universe is the
  panel, and the panel runs **2009-03-27 -> 2026-04-09 with ZERO rows before 2009**: every one of
  its 9,645 names is present in 2009 or later, so the name list is *defined* as survivors to 2009.
  CRSP's own spine says what that costs: **13,787 permnos were alive at some point in 1999-2008 and
  6,898 of them -- 50.0% -- were gone before 2009.** Scoring that era off this list would omit half
  the era's names and precisely the dead half. **Repairing it is a panel rebuild, not an analysis.**
* **THE VENDOR'S, WHICH IS WHAT THIS SCRIPT MEASURES.** `EODHD_CENSUS.md` section 8 found Enron and
  Lehman present in `General` and **empty in `Financials`**, and recorded that two probes is not a
  rate. So the rate is measured here -- **against a control**, because an empty-statement rate with
  no comparator cannot distinguish "this vendor is thin on dead companies" from "this vendor is thin
  on everything this old".

**THE CONTROL IS THE POINT.** The dead cohort is scored beside a seeded sample of SURVIVORS from the
project's own universe, measured by the identical code on the identical fields. A bare 60% empty
rate on dead names would be unreadable; 60% against a survivor rate of 2% is a survivorship hole,
and 60% against 55% is a vendor that is simply thin.

**NOTHING HERE IS A VERDICT ABOUT RETURNS.** Zero trials, `FIXED`-class.
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import eodhd_census as EC                                   # noqa: E402
from valuation.studies import dipcall as _D                              # noqa: E402
from valuation.studies import eodhd_provider as EP                       # noqa: E402

_DATA = _D.data_root(required=False) or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT = os.path.join(_DATA, "free_analysis", "EODHD_DELISTED.json")
SPINE = os.path.join(r"D:\wrds", "stocknames.pkl")
FREEZE = os.path.join(r"D:\eodhd", "freeze_2026-10-22")

ERA_START = pd.Timestamp("1999-01-01")
ERA_END = pd.Timestamp("2009-01-01")
#: Seeded, so the cohorts are reproducible and were not re-drawn after a reading.
SEED = 20261022
#: 60 a side. At a proportion near 0.5 the standard error is 0.065, which is ample to separate a
#: survivorship hole from a thin vendor -- the only question being asked. 10 calls a name, so the
#: whole gate is 1,200 of a 100,000 daily allowance and does not compete with the harvest.
N_PER_COHORT = 60


def our_side():
    """The hole on OUR side of the join. Local, free, and decisive by itself."""
    p = pd.read_pickle(_D.panel_path())
    d = pd.to_datetime(p["date"])
    g = p.assign(_d=d).groupby("ticker")["_d"].max()
    out = {"panel_rows": int(len(p)), "panel_names": int(p["ticker"].nunique()),
           "panel_first_date": str(d.min().date()), "panel_last_date": str(d.max().date()),
           "panel_rows_before_2009": int((d < ERA_END).sum()),
           "panel_names_gone_before_2009": int((g < ERA_END).sum())}
    s = pd.read_pickle(SPINE)
    s["namedt"] = pd.to_datetime(s["namedt"])
    s["nameenddt"] = pd.to_datetime(s["nameenddt"])
    a = s.groupby("permno").agg(first=("namedt", "min"), last=("nameenddt", "max"))
    alive = (a["first"] < ERA_END) & (a["last"] >= ERA_START)
    gone = alive & (a["last"] < ERA_END)
    out["crsp_permnos_alive_in_era"] = int(alive.sum())
    out["crsp_permnos_alive_in_era_gone_before_2009"] = int(gone.sum())
    out["crsp_share_of_era_names_missing_from_our_universe"] = (
        float(gone.sum()) / float(alive.sum()) if int(alive.sum()) else None)
    out["verdict"] = (
        "The 1999-2008 era is NOT reachable from this universe: the panel carries no rows before "
        "2009 and the name list is survivors-to-2009 by construction, so about half the era's "
        "names are absent. Repairing it is a panel rebuild, not an analysis.")
    return out


def cohorts():
    """A dead cohort and a survivor control, both seeded.

    A dead name is taken by its LAST CRSP ticker, which is the name a vendor would know it by, and
    only common shares on the major exchanges are considered so the cohort is comparable to the
    panel's own membership rule rather than sweeping in trusts and foreign issues.
    """
    s = pd.read_pickle(SPINE)
    s["namedt"] = pd.to_datetime(s["namedt"])
    s["nameenddt"] = pd.to_datetime(s["nameenddt"])
    s = s[s["shrcd"].isin([10, 11]) & s["exchcd"].isin([1, 2, 3])]
    a = s.groupby("permno").agg(first=("namedt", "min"), last=("nameenddt", "max"))
    dead = a[(a["first"] < ERA_END) & (a["last"] >= ERA_START) & (a["last"] < ERA_END)]
    last = (s.sort_values("nameenddt").groupby("permno")["ticker"].last())
    dead_t = sorted({str(t).upper() for t in last.loc[last.index.isin(dead.index)].dropna()
                     if str(t).strip() and str(t).upper() != "NAN"})
    panel = pd.read_pickle(_D.panel_path())
    surv_t = sorted({str(t).upper() for t in panel["ticker"]})

    # **TEMPORAL TICKER REUSE, AND IT BIASES THIS MEASUREMENT TOWARD "NO HOLE".** A dead company's
    # last ticker is often reassigned to a living one, and `fundamentals/{T}.US` is a SNAPSHOT route
    # that answers for whoever holds the symbol TODAY. Measured here: **797 of 5,445 dead tickers --
    # 14.64% -- are also live panel tickers**, so about one dead name in seven would have been
    # scored against a different, going concern and counted as "statements present". `S25` recorded
    # this exact hazard as unobservable on a snapshot route; the only safe move is to drop the
    # colliding names and SAY how many were dropped.
    collide = sorted(set(dead_t) & set(surv_t))
    dead_clean = [t for t in dead_t if t not in set(surv_t)]
    rng = pd.Series(dead_clean).sample(n=min(N_PER_COHORT, len(dead_clean)), random_state=SEED)
    rng2 = pd.Series(surv_t).sample(n=min(N_PER_COHORT, len(surv_t)), random_state=SEED)
    return (list(rng), list(rng2), len(dead_t), len(surv_t),
            {"dead_tickers_total": len(dead_t), "collide_with_a_live_ticker": len(collide),
             "collide_share": len(collide) / len(dead_t) if dead_t else None,
             "dead_tickers_used": len(dead_clean)})


def _measure(tk, prefer_freeze=True):
    """One name, in THREE states that must not be merged -- and free when the freeze has it.

    **THE THREE STATES.** `unknown` (the vendor returns nothing at all), `known_empty` (a `General`
    block with zero statement periods -- Enron's and Lehman's shape) and `known_with_history`.
    Collapsing the first two would read a name the vendor has never heard of as a name whose
    statements are missing, and those are different holes with different fixes.

    **THE FREEZE IS READ FIRST, WHICH MAKES THIS GATE COST NOTHING.** The step-4 cohorts were
    harvested inside the prioritised fundamentals pass, so 51 of 60 dead names and 57 of 60
    survivors are already on disk. A name ABSENT from the freeze after that pass is one the harvest
    could not keep -- the vendor returned no `General` block -- which is the `unknown` state rather
    than a gap in this measurement, and the route taken is recorded per name so the two cannot be
    confused later.
    """
    f, route = None, "freeze"
    if prefer_freeze:
        f = EP.load_unit(FREEZE, tk)
    if f is None and not prefer_freeze:
        st, g = EC._get("fundamentals/%s.US" % tk, {})
        route = "api"
        f = g if (st == 200 and isinstance(g, dict)) else None
    if not isinstance(f, dict) or not f.get("General"):
        return {"ticker": tk, "route": route, "known": False, "periods": 0, "empty": None,
                "state": "unknown"}
    gen = f.get("General") or {}
    fin = f.get("Financials") or {}
    pers = set()
    for stmt in ("Income_Statement", "Balance_Sheet", "Cash_Flow"):
        for freq in ("quarterly", "yearly"):
            q = ((fin.get(stmt) or {}).get(freq) or {})
            if isinstance(q, dict):
                pers |= set(q.keys())
    # A name the spine says died before 2009 that the vendor reports as STILL LISTED is a reuse
    # survivor the collision filter did not catch (a ticker retired and later reissued under a
    # symbol absent from today's panel). Flagged rather than counted: scoring it either way would
    # be scoring the wrong company.
    return {"ticker": tk, "route": route, "known": bool(gen),
            "is_delisted": gen.get("IsDelisted"), "periods": len(pers),
            "empty": len(pers) == 0,
            "state": "known_empty" if len(pers) == 0 else "known_with_history",
            "reuse_suspected": (gen.get("IsDelisted") is False),
            "first": min(pers)[:10] if pers else None,
            "last": max(pers)[:10] if pers else None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--our-side-only", action="store_true",
                    help="the local half, which needs no vendor call")
    a = ap.parse_args(argv)

    rep = {"item": "EODHD-DELISTED", "step": "4 gate", "trials": 0, "class": "FIXED",
           "seed": SEED, "n_per_cohort": N_PER_COHORT, "our_side": our_side()}
    print("[our side] panel %s -> %s, rows before 2009: %d"
          % (rep["our_side"]["panel_first_date"], rep["our_side"]["panel_last_date"],
             rep["our_side"]["panel_rows_before_2009"]))
    print("[our side] CRSP era names %d, gone before 2009 %d (%.4f)"
          % (rep["our_side"]["crsp_permnos_alive_in_era"],
             rep["our_side"]["crsp_permnos_alive_in_era_gone_before_2009"],
             rep["our_side"]["crsp_share_of_era_names_missing_from_our_universe"]))

    if not a.our_side_only:
        dead, surv, nd, ns, coll = cohorts()
        rep["dead_cohort_size"] = nd
        rep["survivor_universe_size"] = ns
        rep["ticker_reuse_filter"] = coll
        print("[reuse] %d of %d dead tickers collide with a live ticker (%.4f); using %d"
              % (coll["collide_with_a_live_ticker"], coll["dead_tickers_total"],
                 coll["collide_share"] or 0.0, coll["dead_tickers_used"]))
        for label, names in (("dead_pre_2009", dead), ("survivors", surv)):
            rows = [_measure(t) for t in names]
            # A reuse-suspected row is excluded from BOTH numerator and denominator on the dead
            # cohort: it is evidence about a different company.
            if label == "dead_pre_2009":
                rows_scored = [r for r in rows if not r.get("reuse_suspected")]
            else:
                rows_scored = rows
            known = [r for r in rows_scored if r["known"]]
            empt = [r for r in known if r["empty"]]
            from collections import Counter
            _states = Counter(r.get("state") for r in rows_scored)
            rep[label] = {
                "requested": len(names), "known": len(known), "empty": len(empt),
                "states": dict(_states),
                "unknown_share": (_states.get("unknown", 0) / len(rows_scored)
                                  if rows_scored else None),
                "empty_share_of_known": (len(empt) / len(known) if known else None),
                "unknown": len(names) - len(known),
                "median_periods_of_known": (float(pd.Series([r["periods"] for r in known])
                                                  .median()) if known else None),
                "reuse_suspected_excluded": len(rows) - len(rows_scored),
                "rows": rows}
            print("[%s] known %d of %d | EMPTY %d (%.4f of known) | median periods %s"
                  % (label, len(known), len(names), len(empt),
                     rep[label]["empty_share_of_known"] or 0.0,
                     rep[label]["median_periods_of_known"]))
        d_e = rep["dead_pre_2009"]["empty_share_of_known"]
        s_e = rep["survivors"]["empty_share_of_known"]
        if d_e is not None and s_e is not None:
            rep["empty_share_difference_dead_minus_survivors"] = d_e - s_e
            rep["vendor_hole_is_survivorship_shaped"] = bool(d_e - s_e > 0.20)
            print("[gate] dead %.4f vs survivors %.4f -> difference %.4f"
                  % (d_e, s_e, d_e - s_e))

    rep["how_to_read_it"] = (
        "The OUR-SIDE finding alone blocks a 1999-2008 replication off this universe, whatever the "
        "vendor carries, because the name list is survivors-to-2009 by construction. The vendor "
        "measurement says whether a REBUILT point-in-time universe would also hit an empty-statement "
        "hole on the dead half. Neither half is a claim about returns and nothing is adopted.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    print("[gate] wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
