# -*- coding: utf-8 -*-
"""COLLECTION AND FREE PRE-OUTCOME KILLS for the three edge-data drafts. ZERO TRIALS.

    python -m scripts.edge_drafts_collect

**NO FORWARD RETURN IS LOADED ANYWHERE IN THIS MODULE** and no verdict is computed; a test asserts
it. Under `MB1-SEL` a control can only ever BLOCK a finding, so the kills here cost zero trials and
may run **before** any register is committed — which `PREREG_DRAFT_tracelead.md` §3 states
explicitly and the 2026-10-19 brief requires for `f13skill` ("run that census first, as a free
pre-outcome kill, before any trial is booked").

--------------------------------------------------------------------------------------------
ONE CONNECTION ATTEMPT, MANY QUERIES — and that distinction is the reason this file exists.

`DECISIONS.md` 2026-10-04 permits one connection attempt per session. The scout's round-3 session
spent its connection and lost the 13F census to `column "mgrno" does not exist`: `mgrno` is
**Thomson's** `s34` column applied to **WRDS's own** 13F product. So:

  * **every table's COLUMNS are probed before anything is aggregated** — "entitlement is not
    schema", the portable rule that error bought;
  * **every query is wrapped**, and a failure is a recorded fact rather than the end of the
    session. A failed statement aborts its transaction, so each step issues a ROLLBACK before the
    next — which is what turns one connection into many chances;
  * **each step's result is written to disk as it completes**, so a later failure cannot lose an
    earlier measurement.

--------------------------------------------------------------------------------------------
THE RAW ROOT, AND A DECLARED DEVIATION FROM THE BRIEF'S OWN PATH.

The brief says raw WRDS rows stay in `D:\\wrds` because the repo is public. **Measured today: the
D: volume does not exist on this machine** — `Get-PSDrive` shows C: only — so the brief's path is
unavailable, and round 3's `stocknames.pkl` and `WRDS_CENSUS3.json` are gone with the drive.

Licensed payload is therefore written under `C:\\wrds_local`, which is **outside the repository
tree entirely** — so it cannot be committed even by accident, which is a stronger guarantee than
the `.gitignore` that protects `data/`. The rule's stated purpose is fully preserved and only its
location moves. **Reported rather than decided silently**, and the payload is minimised: wherever
a question can be answered by a server-side aggregate, it is, so most of what comes back is derived
statistics rather than vendor rows.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import wrds_client as W                              # noqa: E402
from valuation.studies import dipcall as D                               # noqa: E402

#: Outside the repo tree. See the module docstring for why this is not `D:\wrds`.
RAW_ROOT = r"C:\wrds_local"
OUT_JSON = "EDGE_DRAFTS_COLLECT.json"

TIER_FLOOR = 10e9
#: `PREREG_DRAFT_tracelead.md` §2: a 63-session window before t, and the change from t-126.
WIN = 63
LAG = 126

#: Candidate column names, probed in order. The scout's defect was assuming one.
CUSIP_CANDIDATES = ("cusip_id", "cusip", "cusip9")
TRADE_DATE_CANDIDATES = ("trd_exctn_dt", "trans_dt", "date")
YIELD_CANDIDATES = ("yld_pt", "yield", "yld")
VOLUME_CANDIDATES = ("entrd_vol_qt", "volume", "qty")
MATURITY_CANDIDATES = ("maturity", "mtrty_dt", "maturity_dt")
MGR_CANDIDATES = ("mgrno", "mgrno_fund", "cik", "mgrcik", "managerid", "mgr_cik", "filerid")
RDATE_CANDIDATES = ("rdate", "report_date", "reportdate", "fdate", "period")


def _save(out, path):
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)


def _pick(cols, candidates, label):
    """The first candidate present, or a recorded refusal naming what WAS there."""
    low = {str(c).lower(): str(c) for c in cols}
    for c in candidates:
        if c in low:
            return low[c]
    raise KeyError("no %s column among %r; the table has %r"
                   % (label, list(candidates), sorted(low)[:40]))


def tier_cells() -> pd.DataFrame:
    """The $10B tier of the CORRECTED RAW universe on the build quadrant.

    `dipcall.panel_path()` is the corrected raw universe (9,645 names) every recent register has
    scored on. **It is NOT `panel_corrected_69d.pkl`**, which is what `WRDS_CENSUS.md` round 3
    measured its 38,540-cell / 81.65% join figure on — so that figure describes a DIFFERENT
    population and is re-measured here rather than inherited (`O-1` applied a coverage figure from
    one population to another and was ~17x wrong).
    """
    p = pd.read_pickle(D.panel_path())[["date", "ticker", "market_cap"]].copy()
    p["date"] = p["date"].astype(str)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["cap"] = pd.to_numeric(p["market_cap"], errors="coerce")
    t = p[p["cap"] >= TIER_FLOOR]
    t = t[(t["date"] >= D.BUILD_LO) & (t["date"] <= D.BUILD_HI)]
    t = t[t["ticker"].map(D.stable_key_half) == 0]
    return t[["date", "ticker"]].reset_index(drop=True)


def main(argv=None):
    t0 = time.time()
    os.makedirs(RAW_ROOT, exist_ok=True)
    out_path = os.path.join(RAW_ROOT, OUT_JSON)

    tier = tier_cells()
    tickers = sorted(tier["ticker"].unique())
    dates = sorted(tier["date"].unique())
    out = {"generated_utc": W.stamp(), "trials": 0,
           "class": "collection-and-free-kills",
           "forward_return_touched": False,
           "raw_root": RAW_ROOT,
           "raw_root_DEVIATION": ("the brief says D:\\wrds; that volume does not exist on this "
                                  "machine, so payload goes outside the repo tree instead. The "
                                  "rule's purpose (licensed rows never reach a public repo) is "
                                  "preserved; only the location moves."),
           "licence_note": ("WRDS is licensed for ACADEMIC RESEARCH ONLY and this repo is public "
                            "and MIT. A WRDS-sourced input can establish whether an idea WORKS "
                            "and may NEVER feed the live score or a public page."),
           "tier": {"floor_usd": TIER_FLOOR, "panel": os.path.basename(D.panel_path()),
                    "cells": int(len(tier)), "tickers": len(tickers), "dates": len(dates),
                    "build_lo": D.BUILD_LO, "build_hi": D.BUILD_HI,
                    "half_boundary": D.HALF_BOUNDARY}}
    print("[collect] $10B build-quadrant tier: %d cells, %d tickers, %d dates"
          % (len(tier), len(tickers), len(dates)), flush=True)
    _save(out, out_path)

    print("[collect] connecting -- ONE attempt, credentials never printed", flush=True)
    db = W.connect()
    out["connected"] = True
    _save(out, out_path)

    def step(name, fn):
        print("\n[collect] === %s ===" % name, flush=True)
        s = time.time()
        try:
            out[name] = fn()
            out[name]["ok"] = True
        except Exception as e:                                           # noqa: BLE001
            out[name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:400])}
            print("[collect] %s FAILED: %s" % (name, out[name]["error"]), flush=True)
            # A failed statement aborts its transaction. Roll back so the NEXT step can run on
            # this same connection -- the whole point of the design.
            try:
                db.connection.rollback()
            except Exception:                                            # noqa: BLE001
                pass
        out[name]["seconds"] = round(time.time() - s, 1)
        _save(out, out_path)
        return out[name]

    # ------------------------------------------------------------------ 1. COLUMN PROBES
    schema = {}

    def probes():
        res = {}
        for key, lib, tbl in (("trace", "trace", "trace_enhanced"),
                              ("f13", "wrdssec_all", "wrds_13f_holdings"),
                              ("stocknames", "crsp", "stocknames"),
                              ("frb_h15", "frb", "rates_daily"),
                              ("crsp_treas", "crsp", "tfz_dly_ft")):
            try:
                r = db.raw_sql("select * from %s.%s limit 1" % (lib, tbl))
                schema[key] = list(r.columns)
                res[key] = {"table": "%s.%s" % (lib, tbl), "present": True,
                            "n_columns": len(r.columns), "columns": list(r.columns)}
                print("  %-11s %-34s %d cols" % (key, "%s.%s" % (lib, tbl), len(r.columns)),
                      flush=True)
            except Exception as e:                                       # noqa: BLE001
                res[key] = {"table": "%s.%s" % (lib, tbl), "present": False,
                            "error": str(e)[:200]}
                print("  %-11s %-34s ABSENT/DENIED" % (key, "%s.%s" % (lib, tbl)), flush=True)
                try:
                    db.connection.rollback()
                except Exception:                                        # noqa: BLE001
                    pass
        res["WHY_PROBE_FIRST"] = ("entitlement is not schema -- round 3 spent its connection on "
                                  "`column mgrno does not exist`, Thomson's s34 column applied "
                                  "to WRDS's own 13F product")
        return res

    step("column_probes", probes)

    # ------------------------------------------------------------------ 2. THE JOIN SPINE
    cusip_map = {"rows": pd.DataFrame()}

    def spine():
        cols = schema.get("stocknames") or []
        if not cols:
            raise KeyError("crsp.stocknames did not probe; no join spine is possible")
        sn = db.raw_sql("select permno, ticker, ncusip, cusip, namedt, nameenddt, shrcd, exchcd "
                        "from crsp.stocknames where ticker is not null")
        raw = os.path.join(RAW_ROOT, "stocknames.pkl")
        sn.to_pickle(raw)
        sn["ticker"] = sn["ticker"].astype(str).str.strip().str.upper()
        ours = sn[sn["ticker"].isin(tickers)].copy()
        j = tier.merge(ours[["ticker", "permno", "ncusip", "namedt", "nameenddt"]],
                       on="ticker", how="left")
        d = pd.to_datetime(j["date"], errors="coerce")
        lo = pd.to_datetime(j["namedt"], errors="coerce")
        hi = pd.to_datetime(j["nameenddt"], errors="coerce")
        hit = j[(d >= lo) & (d <= hi)].copy()
        per_cell = hit.groupby(["date", "ticker"])["permno"].nunique()
        cusip_map["rows"] = hit[["date", "ticker", "permno", "ncusip"]].reset_index(drop=True)
        c6 = sorted({str(c)[:6] for c in hit["ncusip"].dropna().astype(str)
                     if len(str(c)) >= 6})
        cusip_map["cusip6"] = c6
        res = {"stocknames_rows": int(len(sn)),
               "tier_cells": int(len(tier)),
               "tier_cells_resolved_DATED": int(per_cell.shape[0]),
               "tier_cells_resolved_frac": round(per_cell.shape[0] / max(1, len(tier)), 6),
               "cells_AMBIGUOUS_multi_permno": int((per_cell > 1).sum()),
               "undated_would_resolve": int(j.groupby(["date", "ticker"]).ngroups),
               "tier_cusip6": len(c6),
               "NOT_THE_81_65": ("round 3's 81.65% was measured on panel_corrected_69d.pkl's "
                                 "38,540 tier cells; this is the corrected RAW universe's build "
                                 "quadrant and is a different population"),
               "raw_payload": raw, "raw_bytes": int(os.path.getsize(raw))}
        print("  DATED resolve %d of %d = %.4f | ambiguous %d | cusip6 %d"
              % (res["tier_cells_resolved_DATED"], res["tier_cells"],
                 res["tier_cells_resolved_frac"], res["cells_AMBIGUOUS_multi_permno"],
                 res["tier_cusip6"]), flush=True)
        return res

    step("join_spine", spine)

    # ------------------------------------------------------------------ 3. f13skill K0
    def f13_k0():
        cols = schema.get("f13") or []
        if not cols:
            raise KeyError("wrdssec_all.wrds_13f_holdings did not probe")
        mgr = _pick(cols, MGR_CANDIDATES, "manager-id")
        rdt = _pick(cols, RDATE_CANDIDATES, "report-date")
        q = db.raw_sql(
            "select extract(year from %s) as yr, count(distinct %s) as managers, "
            "count(*) as rows from wrdssec_all.wrds_13f_holdings "
            "where %s is not null group by 1 order by 1" % (rdt, mgr, rdt))
        recs = q.to_dict("records")
        res = {"manager_column": mgr, "report_date_column": rdt,
               "by_year": recs,
               "K0_BAR": 1000,
               "WHY": ("the draft's K0: a per-manager signal on 71 managers is not the "
                       "hypothesis; the census recorded 71 filing managers in 2012 stepping to "
                       "3,457 in 2013")}
        for r in recs:
            print("    %s  managers %-7s rows %s" % (r.get("yr"), r.get("managers"),
                                                     r.get("rows")), flush=True)
        return res

    step("f13_K0_managers_by_year", f13_k0)

    # ------------------------------------------------------------------ 4. TRACE coverage
    def trace_cov():
        cols = schema.get("trace") or []
        if not cols:
            raise KeyError("trace.trace_enhanced did not probe")
        cc = _pick(cols, CUSIP_CANDIDATES, "cusip")
        dc = _pick(cols, TRADE_DATE_CANDIDATES, "trade-date")
        yc = _pick(cols, YIELD_CANDIDATES, "yield")
        vc = _pick(cols, VOLUME_CANDIDATES, "volume")
        res = {"cusip_column": cc, "date_column": dc, "yield_column": yc,
               "volume_column": vc, "columns_available": cols}
        try:
            res["maturity_column"] = _pick(cols, MATURITY_CANDIDATES, "maturity")
        except KeyError as e:
            res["maturity_column"] = None
            res["maturity_note"] = str(e)[:240]
        c6 = cusip_map.get("cusip6") or []
        if not c6:
            raise KeyError("no tier cusip6 from the join spine; TRACE coverage is unmeasurable")
        inlist = ",".join("'%s'" % c for c in c6)
        # Trade-report status: cancellations and corrections must not be averaged in. Probe the
        # codes rather than assuming them (Dick-Nielsen's cleaning is elaborate and the register
        # declares which filter it used).
        try:
            st = db.raw_sql("select trc_st, count(*) as n from trace.trace_enhanced "
                            "where %s between '2012-01-01' and '2012-03-31' "
                            "group by 1 order by 2 desc" % dc)
            res["trc_st_codes_2012q1"] = st.to_dict("records")
        except Exception as e:                                           # noqa: BLE001
            res["trc_st_codes_2012q1"] = {"error": str(e)[:200]}
            try:
                db.connection.rollback()
            except Exception:                                            # noqa: BLE001
                pass
        # Per-year issuer/bond/trade counts for OUR tier, and how many carry a usable yield.
        res["by_year"] = {}
        for yr in range(2009, 2020):
            try:
                r = db.raw_sql(
                    "select count(distinct substring(%s from 1 for 6)) as our_issuers, "
                    "count(distinct %s) as our_bonds, count(*) as our_trades, "
                    "sum(case when %s is not null then 1 else 0 end) as trades_with_yield "
                    "from trace.trace_enhanced "
                    "where %s between '%d-01-01' and '%d-12-31' "
                    "and substring(%s from 1 for 6) in (%s)"
                    % (cc, cc, yc, dc, yr, yr, cc, inlist))
                res["by_year"][yr] = r.to_dict("records")[0]
                print("    %d  issuers %-5s bonds %-6s trades %-9s with-yield %s"
                      % (yr, r.iloc[0]["our_issuers"], r.iloc[0]["our_bonds"],
                         r.iloc[0]["our_trades"], r.iloc[0]["trades_with_yield"]), flush=True)
            except Exception as e:                                       # noqa: BLE001
                res["by_year"][yr] = {"error": str(e)[:200]}
                print("    %d FAILED: %s" % (yr, str(e)[:160]), flush=True)
                try:
                    db.connection.rollback()
                except Exception:                                        # noqa: BLE001
                    pass
        return res

    step("trace_coverage", trace_cov)

    out["seconds"] = round(time.time() - t0, 1)
    _save(out, out_path)
    print("\n[collect] wrote %s in %.0fs" % (out_path, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
