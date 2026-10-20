# -*- coding: utf-8 -*-
"""`TRACELEAD` `K1` — a PROVABLE UPPER BOUND on bond coverage of the $10B tier. ZERO TRIALS.

    python -m scripts.tracelead_k1_bound

**NO FORWARD RETURN IS LOADED AND NO VERDICT ABOUT RETURNS IS COMPUTED.** This is
`PREREG_DRAFT_tracelead.md`'s `K1`, which is a free pre-outcome kill: under `MB1-SEL` a control can
only ever BLOCK a finding, so it costs zero trials and may run before any register exists.

**WHY A BOUND RATHER THAN THE FIGURE ITSELF, AND WHY THE BOUND IS ENOUGH.** The one WRDS connection
this session permits (`DECISIONS.md` 2026-10-04) returned per-YEAR counts of how many of the tier's
issuers traded any bond, not the per-window issuer LISTS the exact `K1` needs. But an issuer that
trades no bond in a whole calendar year cannot be trading one inside a 63-session window inside that
year, so:

    per-window cell coverage  <=  per-year cell coverage  <=  THE BOUND COMPUTED HERE

The bound is computed by giving the data **every possible benefit**: it assumes the `N` issuers that
did trade in year `y` are exactly the `N` tier names appearing in the MOST cells that year. No real
assignment can beat that. **So if the bound fails `K1`'s bar, `K1` fires provably**, and relaxing a
bar after watching it fail is what `W-28` §6 forbids.

**THE BOUND IS NOT THE MEASUREMENT AND IS NEVER QUOTED AS ONE.** If the bound CLEARS the bar, `K1`
is UNRESOLVED and needs the per-window lists — the honest outcome, not a pass.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as D                               # noqa: E402
from scripts import edge_drafts_collect as EC                            # noqa: E402

#: Derived from the collection pass rather than retyped, so the two cannot point at different
#: roots. The payload is licensed and lives under `D:\wrds`; CI never has it, which is why the
#: entry point REFUSES loudly rather than computing a bound from nothing.
COLLECT = os.path.join(EC.RAW_ROOT, EC.OUT_JSON)
OUT = "TRACELEAD_K1_BOUND.json"

#: `PREREG_DRAFT_tracelead.md` §3, verbatim and NOT re-chosen here.
K1_CELL_BAR = 0.70
K1_PER_DATE_FLOOR = 0.50
TIER_FLOOR = 10e9


def tier_cells() -> pd.DataFrame:
    p = pd.read_pickle(D.panel_path())[["date", "ticker", "market_cap"]].copy()
    p["date"] = p["date"].astype(str)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["cap"] = pd.to_numeric(p["market_cap"], errors="coerce")
    t = p[p["cap"] >= TIER_FLOOR]
    t = t[(t["date"] >= D.BUILD_LO) & (t["date"] <= D.BUILD_HI)]
    return t[t["ticker"].map(D.stable_key_half) == 0][["date", "ticker"]].reset_index(drop=True)


def main(argv=None):
    if not os.path.isfile(COLLECT):
        raise SystemExit("REFUSING: %s absent -- the collection pass must run first (O10: a "
                         "gating pass and its outcomes must not share an invocation)." % COLLECT)
    col = json.load(io.open(COLLECT, encoding="utf-8"))
    tr = col.get("trace_coverage") or {}
    sp = col.get("join_spine") or {}
    if not tr.get("ok") or not sp.get("ok"):
        raise SystemExit("REFUSING: the collection pass did not complete its TRACE or spine step")

    n_cusip6 = int(sp["tier_cusip6"])
    tier = tier_cells()
    tier["year"] = tier["date"].str.slice(0, 4)

    res = {"item": "TRACELEAD-K1", "trials": 0, "forward_return_touched": False,
           "bar": {"cell_share": K1_CELL_BAR, "per_date_floor": K1_PER_DATE_FLOOR,
                   "source": "PREREG_DRAFT_tracelead.md section 3, reused verbatim"},
           "tier": {"cells": int(len(tier)), "tickers": int(tier["ticker"].nunique()),
                    "dates": int(tier["date"].nunique()),
                    "cusip6_resolved": n_cusip6,
                    "cells_resolved_dated": sp["tier_cells_resolved_DATED"],
                    "cells_resolved_frac": sp["tier_cells_resolved_frac"]},
           "WHAT_A_BOUND_IS": ("an issuer trading no bond in a whole year cannot trade one in a "
                               "63-session window inside it, so the per-year figure bounds the "
                               "per-window one from above; and the covered set is assumed to be "
                               "the most-present names, which no real assignment can beat"),
           "by_year": {}}

    # The ISSUER-level bound first, which needs no assumption at all.
    worst_year, worst_frac = None, 1.0
    for yr, rec in sorted(tr["by_year"].items()):
        if not isinstance(rec, dict) or "our_issuers" not in rec:
            continue
        n_tr = int(rec["our_issuers"])
        issuer_frac = n_tr / max(1, n_cusip6)

        # THE CELL-WEIGHTED UPPER BOUND: give the data the best possible covered set.
        ty = tier[tier["year"] == str(yr)]
        if not len(ty):
            continue
        per_name = ty.groupby("ticker").size().sort_values(ascending=False)
        best = int(per_name.head(n_tr).sum())
        cell_bound = best / max(1, len(ty))

        # And the per-date floor, under the same maximally-favourable assignment.
        keep = set(per_name.head(n_tr).index)
        by_date = ty.assign(hit=ty["ticker"].isin(keep)).groupby("date")["hit"].mean()
        res["by_year"][str(yr)] = {
            "issuers_trading": n_tr, "tier_cusip6": n_cusip6,
            "issuer_coverage": round(issuer_frac, 6),
            "cell_coverage_UPPER_BOUND": round(cell_bound, 6),
            "per_date_min_UPPER_BOUND": round(float(by_date.min()), 6),
            "tier_cells_this_year": int(len(ty)),
            "tier_names_this_year": int(ty["ticker"].nunique()),
            "bonds": rec.get("our_bonds"), "trades": rec.get("our_trades"),
            "trades_with_yield": rec.get("trades_with_yield"),
        }
        if cell_bound < worst_frac:
            worst_year, worst_frac = str(yr), cell_bound
        print("  %s  issuers %3d/%3d = %.3f | CELL BOUND %.4f | per-date min bound %.4f"
              % (yr, n_tr, n_cusip6, issuer_frac, cell_bound, float(by_date.min())), flush=True)

    bounds = [v["cell_coverage_UPPER_BOUND"] for v in res["by_year"].values()]
    mins = [v["per_date_min_UPPER_BOUND"] for v in res["by_year"].values()]
    res["summary"] = {
        "years": len(bounds),
        "cell_bound_min": min(bounds) if bounds else None,
        "cell_bound_max": max(bounds) if bounds else None,
        "worst_year": worst_year,
        "years_whose_BOUND_fails_the_cell_bar": sorted(
            y for y, v in res["by_year"].items() if v["cell_coverage_UPPER_BOUND"] < K1_CELL_BAR),
        "years_whose_BOUND_fails_the_per_date_floor": sorted(
            y for y, v in res["by_year"].items()
            if v["per_date_min_UPPER_BOUND"] < K1_PER_DATE_FLOOR),
        "per_date_min_bound_overall": min(mins) if mins else None,
    }
    s = res["summary"]
    fires = bool(s["years_whose_BOUND_fails_the_cell_bar"])
    res["K1_FIRES_PROVABLY"] = fires
    res["verdict"] = (
        "K1 FIRES. Even under the most favourable possible assignment of which issuers traded, "
        "the tier's cell coverage cannot reach the pre-committed 0.70 in the years listed, so no "
        "per-window measurement can rescue it. The arm does not run and no trial is booked."
        if fires else
        "K1 UNRESOLVED -- the bound CLEARS the bar, which is not a pass. The exact figure needs "
        "the per-window issuer lists, i.e. one more WRDS connection in a later session.")
    print("\n  cell-coverage upper bound: %.4f .. %.4f (worst year %s)"
          % (s["cell_bound_min"], s["cell_bound_max"], s["worst_year"]), flush=True)
    print("  K1 FIRES PROVABLY: %s" % fires, flush=True)

    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, indent=1, default=str))
    print("  wrote %s" % p, flush=True)
    return res


if __name__ == "__main__":
    main()
    raise SystemExit(0)
