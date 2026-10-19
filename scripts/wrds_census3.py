"""WRDS CENSUS ROUND 3 + the three coverage censuses, in ONE connection.

**ZERO TRIALS.** Every number here is a fact about what this account can reach and how much of
our own universe it covers. No forward return is read, no outcome statistic is computed, no
hypothesis is scored. The `S25`/`MB15`/`MB3` class.

**ONE CONNECTION ATTEMPT PER SESSION IS THE RULE** (`DECISIONS.md` 2026-10-04: repeated failures
disabled the account once). So this script does the WHOLE session's WRDS work in one pass:

  1. ROUND-3 ENTITLEMENT PROBES -- IBES recommendations, Compustat segment customers, Capital IQ
     transcripts and key developments, RavenPack, ISS, BoardEx, JKP characteristics, and a
     point-in-time Compustat snapshot. Status vocabulary is `wrds_census`'s, reused rather than
     redefined (`B7`): ENTITLED / EMPTY / DENIED / ABSENT / ERROR.
  2. THE JOIN SPINE -- `crsp.stocknames`, DATED. Every downstream join keys off it, so it runs
     second and everything after it is conditional on it. `W-28` measured what an UNDATED join
     costs: a `gvkey` assigned CRSP dates belonging to a DIFFERENT company on 54 names.
  3. IBES LTG COVERAGE (task B) -- `statsum_epsus` at `fpi = '0'`, linked through
     `wrdsapps_link_crsp_ibes.ibcrsphist`.
  4. PER-MANAGER 13F (task D) -- manager counts per quarter on `wrdssec_all.wrds_13f_holdings`.
  5. TRACE (task C) -- liquid-bond issuer counts on sampled quarters.

**RAW ROWS STAY IN `D:\\wrds` AND ARE NEVER COMMITTED.** What leaves this lane is derived
statistics. The repo is public (MIT since 2026-08-16) and WRDS is licensed for academic research
only, so a WRDS-only input can show whether an idea WORKS and can never feed the live score.

**IT WRITES AFTER EVERY STEP** (`RUN_RULES` rule 9). One connection means a crash in step 5 must
not lose steps 1-4.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd                                                     # noqa: E402

from valuation.edge import wrds_client as W                             # noqa: E402
from scripts import wrds_census as C3                                   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(W.DEFAULT_RAW_ROOT, "WRDS_CENSUS3.json")
TIER_FLOOR = 10e9

#: Round-3 targets. (key, priority, library, table, date_col, what it unlocks)
#: Library/table names are the WRDS-documented ones; where a product has several plausible
#: homes on this account every candidate is probed, because ABSENT-under-one-name is not
#: evidence about the product (`W-14`'s lesson: a census that probes the names in a brief
#: measures the brief).
TARGETS3 = [
    ("ibes_recommendations", "A", "ibes", "recddet", "anndats",
     "IBES analyst RECOMMENDATIONS, per-analyst detail"),
    ("ibes_rec_summary", "A", "ibes", "recdsum", "statpers",
     "IBES recommendation summary by statistical period"),
    ("comp_segment_customer", "A", "compsegd", "seg_customer", "srcdate",
     "Compustat segment CUSTOMERS -- Cohen-Frazzini customer momentum"),
    ("comp_segment_customer_alt", "A", "comp_segments_hist", "seg_customer", "srcdate",
     "same product, the historical-segments home"),
    ("ciq_transcripts", "B", "ciq", "wrds_transcript_detail", "mostimportantdateutc",
     "Capital IQ earnings-call TRANSCRIPTS"),
    ("ciq_keydev", "B", "ciq", "wrds_keydev", "announcedate",
     "Capital IQ KEY DEVELOPMENTS -- dated corporate events"),
    ("ravenpack", "B", "ravenpack", "rpa_djpr_equities_1990_2019", "rpna_date_utc",
     "RavenPack news analytics"),
    ("iss_governance", "C", "risk", "rmgovernance", "year",
     "ISS/RiskMetrics governance -- the G in a governance signal"),
    ("iss_directors", "C", "risk", "rmdirectors", "year",
     "ISS/RiskMetrics directors"),
    ("boardex_na", "C", "boardex", "na_wrds_company_profile", None,
     "BoardEx North America -- board networks"),
    ("jkp_characteristics", "D", "contrib_global_factor", "global_factor", "date",
     "JKP firm CHARACTERISTICS -- the firm-level file behind the factor returns"),
    ("jkp_char_alt", "D", "contrib", "global_factor", "date",
     "same product, the plain contrib home"),
    ("comp_pit_snapshot", "D", "comp", "snapshot_fundq", "datadate",
     "Compustat POINT-IN-TIME quarterly snapshot -- as-first-reported"),
    ("comp_pit_unrestated", "D", "comp", "co_amkt", "datadate",
     "Compustat adjunct probed as a PIT candidate"),
    ("trace_enhanced", "E", "trace", "trace_enhanced", "trd_exctn_dt",
     "TRACE corporate bond trades -- the bond-spread lead question"),
    ("trace_standard", "E", "trace", "trace_standard", "trd_exctn_dt",
     "TRACE standard, the alternative home"),
    ("wrds_bond_returns", "E", "wrdsapps_bondret", "bondret", "date",
     "WRDS computed BOND RETURNS -- a spread change without building one"),
]


def _data_root():
    """The PRIMARY populated data root, never the worktree's empty one (`E-5`).

    `E-5` recorded this twice: an artifact written by a worktree-run script does not survive
    the worktree, and a worktree carries `data/` EMPTY while the primary root holds it. A
    script that resolves `REPO/data` from inside a worktree reads nothing and says so quietly.
    """
    d = REPO
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "data", "free_analysis",
                                       "panel_corrected_69d.pkl")):
            return os.path.join(d, "data")
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    raise SystemExit("REFUSING: panel_corrected_69d.pkl not found in any parent's data/")


def _tier():
    """The $10B tier's (date, ticker) cells, from the charter's own Stage-1 panel."""
    p = pd.read_pickle(os.path.join(_data_root(), "free_analysis",
                                    "panel_corrected_69d.pkl"))[["date", "ticker",
                                                                 "market_cap"]]
    p["date"] = p["date"].astype(str)
    p["cap"] = pd.to_numeric(p["market_cap"], errors="coerce")
    t = p[p["cap"] >= TIER_FLOOR].copy()
    return t[["date", "ticker"]].reset_index(drop=True)


def _save(out):
    os.makedirs(os.path.dirname(os.path.abspath(OUT_JSON)), exist_ok=True)
    with io.open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)


def _step(out, name, fn):
    """Run one step. Never raises -- a failure is a recorded fact, and the file is written."""
    t0 = time.time()
    print("\n[census3] === %s ===" % name, flush=True)
    try:
        out[name] = fn()
        out[name]["ok"] = True
    except Exception as e:                                              # noqa: BLE001
        out[name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
        print("[census3] %s FAILED: %s" % (name, out[name]["error"]), flush=True)
    out[name]["seconds"] = round(time.time() - t0, 1)
    _save(out)
    return out[name]


def main():
    tier = _tier()
    tickers = sorted(set(tier["ticker"].astype(str)))
    out = {"generated_utc": W.stamp(), "trials": 0,
           "class": "collection-and-provenance",
           "forward_return_touched": False,
           "licence_note": ("WRDS is licensed for ACADEMIC RESEARCH ONLY. Every figure here is "
                            "a coverage or entitlement fact. A WRDS-only input can establish "
                            "whether an idea works and may NEVER feed the live score or a "
                            "public page."),
           "tier": {"floor_usd": TIER_FLOOR, "cells": int(len(tier)),
                    "distinct_tickers": len(tickers),
                    "dates": int(tier["date"].nunique())}}
    print("[census3] $10B tier: %d cells, %d tickers, %d dates"
          % (len(tier), len(tickers), tier["date"].nunique()), flush=True)
    _save(out)

    print("[census3] connecting -- ONE attempt, credentials never printed", flush=True)
    db = W.connect()
    libs = sorted(db.list_libraries())
    out["n_libraries_visible"] = len(libs)
    out["libraries_probed_present"] = {}
    print("[census3] %d libraries visible" % len(libs), flush=True)
    _save(out)

    # ---------------------------------------------------------------- 1. probes
    def probes():
        recs = []
        for key, prio, lib, tbl, dc, why in TARGETS3:
            out["libraries_probed_present"][lib] = lib in libs
            if lib not in libs:
                rec = {"key": key, "priority": prio, "library": lib, "table": tbl,
                       "status": C3.ABSENT, "unlocks": why,
                       "error": "library not in catalogue for this account",
                       "checked_utc": W.stamp()}
            else:
                rec = C3._one(db, key, prio, lib, tbl, dc, why)
            sp = rec.get("span")
            print("[census3] %s %-26s %-9s rows~%-14s %s"
                  % (prio, key, rec["status"], rec.get("rows_estimated", "-"),
                     (sp["from"] + ".." + sp["to"]) if sp else ""), flush=True)
            recs.append(rec)
        return {"targets": recs,
                "by_status": {s: sum(1 for r in recs if r["status"] == s)
                              for s in (C3.ENTITLED, C3.EMPTY, C3.DENIED, C3.ABSENT, C3.ERROR)}}

    _step(out, "round3_probes", probes)

    # ---------------------------------------------------------- 2. the join spine
    def spine():
        sn = db.raw_sql(
            "select permno, ticker, ncusip, cusip, namedt, nameenddt, shrcd, exchcd, comnam "
            "from crsp.stocknames where ticker is not null")
        raw = os.path.join(W.DEFAULT_RAW_ROOT, "stocknames.pkl")
        sn.to_pickle(raw)                      # RAW stays on D:, never committed
        sn["ticker"] = sn["ticker"].astype(str).str.strip().str.upper()
        ours = sn[sn["ticker"].isin([t.upper() for t in tickers])].copy()
        # DATED join: a (date, ticker) cell resolves only inside a name interval.
        m = tier.copy()
        m["ticker"] = m["ticker"].astype(str).str.upper()
        j = m.merge(ours[["ticker", "permno", "ncusip", "namedt", "nameenddt"]],
                    on="ticker", how="left")
        d = pd.to_datetime(j["date"], errors="coerce")
        lo = pd.to_datetime(j["namedt"], errors="coerce")
        hi = pd.to_datetime(j["nameenddt"], errors="coerce")
        j["in_window"] = (d >= lo) & (d <= hi)
        hit = j[j["in_window"]]
        per_cell = hit.groupby(["date", "ticker"])["permno"].nunique()
        amb = int((per_cell > 1).sum())
        res = {"stocknames_rows": int(len(sn)),
               "stocknames_rows_matching_our_tickers": int(len(ours)),
               "our_tickers": len(tickers),
               "tickers_with_any_stocknames_row": int(ours["ticker"].nunique()),
               "tier_cells": int(len(tier)),
               "tier_cells_resolved_DATED": int(per_cell.shape[0]),
               "tier_cells_resolved_frac": round(per_cell.shape[0] / max(len(tier), 1), 6),
               "cells_AMBIGUOUS_multi_permno": amb,
               "undated_would_resolve": int(j.groupby(["date", "ticker"]).ngroups),
               "note": ("undated_would_resolve counts cells a ticker-only join would accept; "
                        "the DATED figure is the honest one. W-28 measured an undated gvkey "
                        "route assigning one company's dates to another on 54 names."),
               "raw_payload": raw, "raw_bytes": int(os.path.getsize(raw))}
        # cusips for the TRACE overlap, derived and kept in memory only
        res["_cusip6"] = sorted(set(
            str(c)[:6] for c in hit["ncusip"].dropna().astype(str) if len(str(c)) >= 6))
        res["tier_cusip6_count"] = len(res["_cusip6"])
        print("[census3] DATED resolve %d of %d cells = %.4f ; ambiguous %d ; cusip6 %d"
              % (res["tier_cells_resolved_DATED"], res["tier_cells"],
                 res["tier_cells_resolved_frac"], amb, res["tier_cusip6_count"]), flush=True)
        return res

    sp = _step(out, "join_spine_stocknames", spine)
    cusip6 = sp.pop("_cusip6", []) if sp.get("ok") else []
    _save(out)

    # ------------------------------------------------------------- 3. IBES LTG
    def ltg():
        res = {}
        res["link_rows"] = int(db.raw_sql(
            "select count(*) as n from wrdsapps_link_crsp_ibes.ibcrsphist")["n"].iloc[0])
        fp = db.raw_sql(
            "select fpi, count(*) as n, min(statpers) as lo, max(statpers) as hi "
            "from ibes.statsum_epsus group by fpi order by fpi")
        res["by_fpi"] = fp.to_dict("records")
        yr = db.raw_sql(
            "select extract(year from statpers) as yr, count(*) as n, "
            "count(distinct ticker) as n_tickers, "
            "avg(numest) as mean_numest, avg(meanest) as mean_ltg "
            "from ibes.statsum_epsus where fpi = '0' group by 1 order by 1")
        res["ltg_by_year"] = yr.to_dict("records")
        res["ltg_rows_total"] = int(sum(int(r["n"]) for r in res["ltg_by_year"]))
        lnk = db.raw_sql(
            "select ticker, permno, sdate, edate from wrdsapps_link_crsp_ibes.ibcrsphist")
        raw = os.path.join(W.DEFAULT_RAW_ROOT, "ibcrsphist.pkl")
        lnk.to_pickle(raw)
        res["raw_payload"] = raw
        res["link_permnos"] = int(lnk["permno"].nunique())
        res["link_tickers"] = int(lnk["ticker"].nunique())
        print("[census3] LTG rows %s over %d years ; link %d rows"
              % (res["ltg_rows_total"], len(res["ltg_by_year"]), res["link_rows"]), flush=True)
        return res

    _step(out, "ibes_ltg", ltg)

    # --------------------------------------------------------- 4. per-manager 13F
    def f13():
        q = db.raw_sql(
            "select rdate, count(distinct mgrno) as n_managers, count(*) as n_rows "
            "from wrdssec_all.wrds_13f_holdings "
            "where rdate >= '2010-01-01' group by rdate order by rdate")
        res = {"by_rdate": q.to_dict("records"),
               "quarters": int(len(q)),
               "managers_min": int(q["n_managers"].min()) if len(q) else None,
               "managers_max": int(q["n_managers"].max()) if len(q) else None}
        print("[census3] 13F: %d quarters, managers %s..%s"
              % (res["quarters"], res["managers_min"], res["managers_max"]), flush=True)
        return res

    _step(out, "f13_managers", f13)

    # -------------------------------------------------------------- 5. TRACE
    def trace():
        res = {"cusip6_in_tier": len(cusip6)}
        found = None
        for lib, tbl, dcol, ccol in (("trace", "trace_enhanced", "trd_exctn_dt", "cusip_id"),
                                     ("trace", "trace_standard", "trd_exctn_dt", "cusip_id"),
                                     ("wrdsapps_bondret", "bondret", "date", "cusip")):
            try:
                db.raw_sql("select %s, %s from %s.%s limit 1" % (dcol, ccol, lib, tbl))
                found = (lib, tbl, dcol, ccol)
                break
            except Exception as e:                                      # noqa: BLE001
                res.setdefault("probe_errors", {})["%s.%s" % (lib, tbl)] = str(e)[:160]
        if not found:
            res["status"] = "NO READABLE BOND TABLE"
            return res
        lib, tbl, dcol, ccol = found
        res["table_used"] = "%s.%s" % (lib, tbl)
        # SAMPLED quarters, declared as sampling: a full group-by over 455M rows is minutes.
        res["sampled_quarters"] = {}
        for lo, hi in (("2013-01-01", "2013-03-31"), ("2016-01-01", "2016-03-31"),
                       ("2020-01-01", "2020-03-31"), ("2024-01-01", "2024-03-31")):
            try:
                r = db.raw_sql(
                    "select count(*) as n_trades, count(distinct %s) as n_bonds, "
                    "count(distinct substring(%s from 1 for 6)) as n_issuers "
                    "from %s.%s where %s between '%s' and '%s'"
                    % (ccol, ccol, lib, tbl, dcol, lo, hi))
                res["sampled_quarters"][lo] = r.to_dict("records")[0]
                if cusip6:
                    inlist = ",".join("'%s'" % c for c in cusip6[:1200])
                    r2 = db.raw_sql(
                        "select count(distinct substring(%s from 1 for 6)) as n_our_issuers, "
                        "count(distinct %s) as n_our_bonds, count(*) as n_our_trades "
                        "from %s.%s where %s between '%s' and '%s' "
                        "and substring(%s from 1 for 6) in (%s)"
                        % (ccol, ccol, lib, tbl, dcol, lo, hi, ccol, inlist))
                    res["sampled_quarters"][lo].update(r2.to_dict("records")[0])
                print("[census3] TRACE %s: %s" % (lo, res["sampled_quarters"][lo]), flush=True)
            except Exception as e:                                      # noqa: BLE001
                res["sampled_quarters"][lo] = {"error": str(e)[:200]}
        return res

    _step(out, "trace", trace)

    _save(out)
    print("\n[census3] wrote %s" % OUT_JSON)
    return out


if __name__ == "__main__":
    main()
