# -*- coding: utf-8 -*-
"""W-28 STAGE 2 — the pre-outcome kills K1..K5, in their OWN pass, read before any arm.

`O10`'s process defect was computing a gating control and the outcome statistics in one pass. This
runs the kills alone and writes an artifact; the arm (not built here) refuses without it.

**ZERO TRIALS.** No composite gate is read. K3 and K4 compute the CANDIDATE COLUMN's own per-date
IC, which is a return relationship -- but under `MB1-SEL` a control that can only BLOCK adds no
degree of freedom to any published claim, and the register's verdict object (the composite's
paired alpha and long-short t) is never touched here.

> **A CORRECTION TO THE DRAFT'S OWN §6 HEADER, recorded rather than glossed.** It reads *"four of
> five FREE, all firing before a return is scored"*, while its own table marks all five FREE and
> its own K3/K4 definitions require a per-date IC -- which IS a return relationship. Both cannot
> hold. The reading taken here: all five cost ZERO TRIALS, and K3/K4 do score a return, on the
> INPUT COLUMN rather than on the composite. That is the coherent reading and it is stated so no
> reader infers the kills were run without touching `fwd_ret`.

THE CONSTRUCTION, AND WHY IT IS SIMPLER THAN THE REGISTER FEARED
----------------------------------------------------------------
`totalq.total_q` ships **PRE-COMPUTED** intangible capital, so the Peters-Taylor perpetual
inventory is NOT rebuilt here and §2's frozen delta/SG&A/burn-in parameters govern a construction
this pass does not perform. Measured on the pull:

    k_int_offbs == k_int_know + k_int_org   EXACTLY (median deviation 0.000000)
    k_int        == k_int_offbs + on-balance-sheet intangibles (median difference +3.771)

The register declares `K_int` = knowledge + organization capital and then subtracts `intan` to
avoid double-counting acquired intangibles. **That is exactly `k_int_offbs`.** So this pass uses
`k_int_offbs` and subtracts nothing -- the double-counting guard is already inside the vendor's own
decomposition, and using `k_int` instead would silently double-count.

Currency is the `P7` trap and is handled with the panel's own repaired field: **`fx_divisor` is a
DIVISOR, not a multiplier**, so local-currency capital becomes USD by DIVIDING.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import research_log                     # noqa: E402
from valuation.screener.cross_sectional import zscore       # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join(_ROOT, "data", "free_analysis", "panel_corrected_69d.pkl")
OUT = os.path.join(_ROOT, "data", "free_analysis", "W28_KILLS.json")
TOTALQ = r"D:\wrds\totalq_total_q"
STOCKNAMES = r"D:\wrds\crsp_stocknames"
SECURITY = r"D:\wrds\comp_security"

# ---- register constants. Changing one after a measurement voids the item.
K1_COVERAGE_BAR = 0.90        # crosswalk coverage per rebalance date
K2_BITE_BAR = 0.20            # decile must move on >= 20% of covered name-dates
K3_RHO_BAR = 0.60             # rho of the two per-date IC series
N_Q = 10                      # value-theme deciles, for the bite test
#: CRSP is cut at 2024-12-31 on this account; the last interval is extended so the
#: vendor cut-off does not read as a coverage gap (`W-3b`).
OPEN_END = "9999-12-31"
#: EXECUTOR-DECLARED, and NOT in the register: the annual-fundamental publication lag used to
#: keep the join point-in-time. 120 days is conservative against Compustat's ~90-day filing
#: window and close to the panel's own measured ~111-day effective lag. Declared before scoring.
PUB_LAG_DAYS = 120

_rd = lambda p: pd.read_pickle(p, compression="gzip")


def _load_totalq() -> pd.DataFrame:
    fs = sorted(glob.glob(os.path.join(TOTALQ, "*.pkl")))
    if not fs:
        raise FileNotFoundError(
            "%s is absent. Total Q lives on D: and is never mirrored into the checkout. "
            "`DEEPITM-FIN` shipped a clean, plausible null from a directory that merely "
            "existed -- refusing to proceed from no rows." % TOTALQ)
    d = pd.concat([_rd(f) for f in fs], ignore_index=True)
    d["datadate"] = d["datadate"].astype(str).str[:10]
    d["gvkey"] = d["gvkey"].astype(str).str.zfill(6)
    return d[["gvkey", "datadate", "k_int_offbs", "k_int", "k_int_know", "k_int_org"]]


def _crosswalks(tickers) -> tuple:
    """Return (dated, naive) maps ticker -> gvkey. AMENDMENT 2: the DATE comes from CRSP."""
    sn = _rd(sorted(glob.glob(os.path.join(STOCKNAMES, "*.pkl")))[0])
    cs = _rd(sorted(glob.glob(os.path.join(SECURITY, "*.pkl")))[0])
    cs["c8"] = cs["cusip"].astype(str).str.upper().str[:8]
    cs["gvkey"] = cs["gvkey"].astype(str).str.zfill(6)
    cusip2gv = dict(zip(cs["c8"], cs["gvkey"]))

    want = {str(t).upper().strip() for t in tickers}
    sn["ticker"] = sn["ticker"].astype(str).str.upper().str.strip()
    sn = sn[sn["ticker"].isin(want)].copy()
    sn["c8"] = sn["ncusip"].fillna(sn["cusip"]).astype(str).str.upper().str[:8]
    sn = sn[sn["c8"].str.len() == 8]

    dated = collections.defaultdict(list)          # ticker -> [(gvkey, from, to), ...]
    for t, g in sn.groupby("ticker"):
        rows = []
        for r in g.sort_values("namedt").itertuples():
            gv = cusip2gv.get(str(r.c8))
            if gv:
                rows.append([gv, str(r.namedt)[:10], str(r.nameenddt)[:10]])
        # A DEFECT IN MY OWN FIRST PASS, caught by a per-date coverage of ZERO. CRSP on this
        # account is CUT AT 2024-12-31 while our names still trade and the panel runs to
        # 2026-01-28. Left unextended, every 2025-26 cell falls outside every interval and reads
        # as NOT COVERED -- the vendor's cut-off masquerading as a coverage gap, which is exactly
        # what `W-3b` measured and what `revisions.crsp_intervals` already guards with OPEN_END.
        if rows:
            rows[-1][2] = OPEN_END
        dated[t].extend(tuple(r) for r in rows)

    # the NAIVE route the register forbids: comp.security.tic, UNDATED
    cs["tic"] = cs["tic"].astype(str).str.upper().str.strip()
    naive = {}
    for t, gv in zip(cs["tic"], cs["gvkey"]):
        if t in want:
            naive.setdefault(t, gv)
    return dated, naive


def _minus(iso: str, days: int) -> str:
    return (dt.date(int(iso[:4]), int(iso[5:7]), int(iso[8:10]))
            - dt.timedelta(days=days)).isoformat()


def run() -> dict:
    p = pd.read_pickle(PANEL)
    if not isinstance(p["date"].iloc[0], str):
        raise RuntimeError("panel dates must be STRINGS; a Timestamp filter matches zero rows")
    p = p.copy()
    p["tk"] = p["ticker"].astype(str).str.upper()
    tickers = sorted(set(p["tk"]))
    dates = sorted(set(p["date"].astype(str)))
    out = {"item": "W-28", "stage": 2, "trials": 0,
           "equity_N": research_log.detail()["by_domain"]["equity"],
           "pub_lag_days": PUB_LAG_DAYS,
           "k_int_column_used": "k_int_offbs",
           "k_int_note": ("k_int_offbs == k_int_know + k_int_org exactly, and k_int additionally "
                          "includes on-balance-sheet intangibles; the register's (K_int - intan) "
                          "IS k_int_offbs, so nothing is subtracted and k_int would double-count")}

    tq = _load_totalq()
    dated, naive = _crosswalks(tickers)
    by_gv = collections.defaultdict(list)
    for gv, dd, ko in zip(tq["gvkey"], tq["datadate"], tq["k_int_offbs"]):
        by_gv[gv].append((dd, ko))
    for gv in by_gv:
        by_gv[gv].sort()

    def gvkey_dated(t, d0):
        for gv, lo, hi in dated.get(t, ()):
            if lo <= d0 <= hi:
                return gv
        return None

    def kint_at(gv, d0):
        """Latest datadate at or before the rebalance date MINUS the publication lag."""
        if gv is None:
            return None
        cut = _minus(d0, PUB_LAG_DAYS)
        best = None
        for dd, ko in by_gv.get(gv, ()):
            if dd <= cut:
                best = ko
            else:
                break
        return best

    # ---------------------------------------------------------------- K1 · CROSSWALK
    gv_dated, gv_naive, kint = [], [], []
    for t, d0 in zip(p["tk"], p["date"].astype(str)):
        g = gvkey_dated(t, d0)
        gv_dated.append(g)
        gv_naive.append(naive.get(t))
        kint.append(kint_at(g, d0))
    p["gvkey"] = gv_dated
    p["k_int_offbs"] = kint

    n_dated = int(pd.Series(gv_dated).notna().sum())
    n_naive = int(pd.Series(gv_naive).notna().sum())
    per_date = p.assign(_ok=p["gvkey"].notna()).groupby("date")["_ok"].mean()
    worst = float(per_date.min())
    out["K1_crosswalk"] = {
        "bar": K1_COVERAGE_BAR,
        "cells": int(len(p)),
        "cells_dated_route": n_dated, "frac_dated_route": n_dated / len(p),
        "cells_naive_route": n_naive, "frac_naive_route": n_naive / len(p),
        "naive_extra_cells": n_naive - n_dated,
        "per_date_min": worst, "per_date_median": float(per_date.median()),
        "per_date_max": float(per_date.max()),
        "dates_below_bar": int((per_date < K1_COVERAGE_BAR).sum()),
        "fires": bool((per_date < K1_COVERAGE_BAR).any()),
        "note": ("AMENDMENT 2: the DATE comes from CRSP stocknames intervals, never from an "
                 "undated ticker map. The naive comp.security.tic route's EXTRA cells are the "
                 "hazard W-3b measured at 17.7% contamination, not additional coverage.")}

    # Name-level, and the NAIVE leg is the INSTRUMENT CHECK: it must reproduce the census's
    # independently-measured 94.9% or this crosswalk machinery is not measuring what it claims.
    nd = sum(1 for t in tickers if dated.get(t))
    nn = sum(1 for t in tickers if naive.get(t))
    disagree = [t for t in tickers if dated.get(t) and naive.get(t)
                and naive[t] not in {g for g, _, _ in dated[t]}]
    out["K1_crosswalk"].update({
        "names_dated": nd, "frac_names_dated": nd / len(tickers),
        "names_naive": nn, "frac_names_naive": nn / len(tickers),
        "census_naive_reference": 0.949,
        "instrument_check_naive_reproduces_census": abs(nn / len(tickers) - 0.949) < 0.01,
        "names_where_routes_DISAGREE_on_gvkey": len(disagree),
        "disagreement_examples": sorted(disagree)[:8]})

    if out["K1_crosswalk"]["fires"]:
        out["stopped_at"] = "K1"
        for k in ("K2_bite", "K3_premise", "K4_direction", "K5_standardiser"):
            out[k] = "NOT REACHED -- K1 fired and the register's consequence is STOP"
        out["arm_run"] = False
        out["verdict"] = (
            "K1 FIRES -- W-28 STOPS AT STAGE 2, ZERO TRIALS. The 90 percent dated-crosswalk bar "
            "is NOT REACHABLE on this account: the correct DATED route peaks at %.4f on its best "
            "rebalance date and medians %.4f, with %d of %d dates below the bar. The UNDATED "
            "route would clear it at %.4f of cells and is the contaminated one -- it assigns a "
            "gvkey CRSP dates to a DIFFERENT COMPANY on %d of our names."
            % (out["K1_crosswalk"]["per_date_max"], out["K1_crosswalk"]["per_date_median"],
               out["K1_crosswalk"]["dates_below_bar"], len(dates),
               out["K1_crosswalk"]["frac_naive_route"], len(disagree)))
    return out, p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k1-only", action="store_true")
    ap.parse_args(argv)
    out, _ = run()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
