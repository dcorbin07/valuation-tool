"""
WRDS CENSUS — what THIS account can actually reach. Zero trials, facts about what exists.

    python -m scripts.wrds_census [--out WRDS_CENSUS.md] [--json <path>]

COLLECTION-AND-PROVENANCE. Nothing here is a research result and nothing here may be quoted as
one. It pulls no payload: it asks the catalogue what tables exist, then SAMPLES each target for
its date span and row count.

--------------------------------------------------------------------------------------------
ENTITLEMENT IS MEASURED, NEVER INFERRED, AND THE DISTINCTION HAS THREE STATES NOT TWO.

A WRDS account sees a library in `list_libraries()` whether or not it may read the tables inside
it -- the catalogue is broader than the entitlement. So "the library is listed" is not evidence,
and a census built on it would confidently report products this account cannot touch. Each
target is therefore probed with a real query, and lands in one of:

  * ``ENTITLED``    -- a SELECT returned rows.
  * ``EMPTY``       -- a SELECT succeeded and returned nothing. Reached, and genuinely empty.
  * ``DENIED``      -- permission error. The table exists and this account may not read it.
  * ``ABSENT``      -- the table does not exist under that name here.
  * ``ERROR``       -- anything else, with the exception recorded rather than swallowed.

DENIED and ABSENT are different facts and a plan built on confusing them wastes a subscription
window chasing a table that was never there. EMPTY and DENIED are different again -- one is a
statement about the data, the other about us.

--------------------------------------------------------------------------------------------
COUNTS ARE SAMPLED AND SAID TO BE.

`SELECT count(*)` on a WRDS table can run for many minutes and some are billions of rows, so
this uses the planner's estimate (`pg_class.reltuples`) where it can and labels it ESTIMATED.
A number that is really an estimate, printed as if it were exact, is how a plan gets sized
wrong -- this harvest has already scored two projections that missed by 4x and 34%.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import wrds_client as W                            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENTITLED, EMPTY, DENIED, ABSENT, ERROR = "ENTITLED", "EMPTY", "DENIED", "ABSENT", "ERROR"

#: The prioritised pull plan's targets, in the brief's order. `date_col` is what a span is
#: measured on; None means "no natural date axis, report rows only".
TARGETS = [
    # (key, priority, library, table, date_col, what it unlocks)
    ("optionmetrics_secprd", "a", "optionm_all", "secprd", "date",
     "OptionMetrics security prices — the spine of the IvyDB join"),
    ("optionmetrics_opprcd", "a", "optionm_all", "opprcd", "date",
     "OptionMetrics option prices + greeks, per contract"),
    ("optionmetrics_vsurfd", "a", "optionm_all", "vsurfd", "date",
     "IvyDB STANDARDISED volatility surface — the single biggest upgrade if entitled"),
    ("optionmetrics_stdopd", "a", "optionm_all", "stdopd", "date",
     "IvyDB standardised options (fixed 30/60/91d tenors)"),
    ("ibes_det_epsus", "b", "ibes", "det_epsus", "anndats",
     "IBES DETAIL estimates — per-analyst, per-revision, with announce dates"),
    ("ibes_statsum_epsus", "b", "ibes", "statsum_epsus", "statpers",
     "IBES summary statistics by statistical period"),
    ("ibes_actu_epsus", "b", "ibes", "actu_epsus", "anndats",
     "IBES actuals — the realised number behind a surprise"),
    ("crsp_dsedelist", "c", "crsp", "dsedelist", "dlstdt",
     "CRSP delisting returns — the survivorship cross-check against our ACTIONS mask"),
    ("crsp_dsf", "c", "crsp", "dsf", "date",
     "CRSP daily stock file"),
    ("crsp_msf", "c", "crsp", "msf", "date",
     "CRSP monthly stock file"),
    ("comp_fundq", "d", "comp", "fundq", "datadate",
     "Compustat quarterly fundamentals"),
    ("comp_pit_fundq", "d", "comp", "co_ifndq", "datadate",
     "Compustat point-in-time quarterly (preliminary vs final)"),
    ("comp_adsprate", "d", "comp", "adsprate", "datadate",
     "Compustat ratings/PIT adjunct"),
    ("tfn_table1", "e", "tfn", "table1", "fdate",
     "Thomson 13F holdings — intra-quarter filing detail vs our SF3"),
    ("tfn_table2", "e", "tfn", "table2", "fdate",
     "Thomson 13F manager-level"),
    ("tfn_insiders", "e", "tfn", "table1", None,
     "Thomson insider filings"),
    ("comp_shortint", "f", "comp", "secshort", "datadate",
     "Short interest history — extends the S18 cache backward"),
    ("taq_master", "g", "taqmsec", "ctm_2020", "date",
     "TAQ intraday — FLAG SIZE ONLY, do not bulk-pull"),
]

#: Extra library-level sweeps: which of these libraries are visible at all.
LIBRARY_INTEREST = ["optionm_all", "optionm", "ibes", "crsp", "crsp_a_stock", "comp",
                    "compa", "tfn", "taqmsec", "taq", "wrdsapps", "crspa", "ff", "markit"]


def _one(db, key, prio, lib, tbl, date_col, why, sample_rows=3):
    """Probe one target. Never raises -- every outcome is a recorded fact."""
    rec = {"key": key, "priority": prio, "library": lib, "table": tbl,
           "date_col": date_col, "unlocks": why, "checked_utc": W.stamp()}
    t0 = time.time()
    try:
        head = db.raw_sql(f"select * from {lib}.{tbl} limit {sample_rows}")
    except Exception as e:                                              # noqa: BLE001
        msg = str(e)
        low = msg.lower()
        if "permission denied" in low or "not authorized" in low:
            rec["status"] = DENIED
        elif "does not exist" in low or "undefined table" in low:
            rec["status"] = ABSENT
        else:
            rec["status"] = ERROR
        rec["error"] = msg[:220]
        rec["seconds"] = round(time.time() - t0, 1)
        return rec

    rec["status"] = ENTITLED if len(head) else EMPTY
    rec["n_columns"] = int(head.shape[1])
    rec["columns"] = [str(c) for c in head.columns][:60]
    rec["seconds"] = round(time.time() - t0, 1)

    # ESTIMATED row count from the planner -- exact count(*) can run for minutes here.
    try:
        est = db.raw_sql(
            "select c.reltuples::bigint as n from pg_class c "
            "join pg_namespace ns on ns.oid = c.relnamespace "
            f"where ns.nspname = '{lib}' and c.relname = '{tbl}'")
        if len(est):
            rec["rows_estimated"] = int(est["n"].iloc[0])
            rec["rows_are_estimated"] = True
    except Exception as e:                                              # noqa: BLE001
        rec["rows_estimate_error"] = f"{type(e).__name__}: {str(e)[:120]}"

    if date_col and date_col in [str(c) for c in head.columns]:
        try:
            sp = db.raw_sql(f"select min({date_col}) as lo, max({date_col}) as hi "
                            f"from {lib}.{tbl}")
            rec["span"] = {"from": str(sp["lo"].iloc[0]), "to": str(sp["hi"].iloc[0])}
        except Exception as e:                                          # noqa: BLE001
            rec["span_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    elif date_col:
        rec["span_note"] = f"date_col '{date_col}' not among this table's columns"
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="WRDS census — entitlements, spans, sizes")
    ap.add_argument("--out", default=os.path.join(REPO, "WRDS_CENSUS.md"))
    ap.add_argument("--json", default=os.path.join(W.DEFAULT_RAW_ROOT, "WRDS_CENSUS.json"))
    ap.add_argument("--limit", type=int, default=0, help="probe only the first N targets")
    a = ap.parse_args(argv)

    print("[census] connecting (credentials from .env, never printed)", flush=True)
    db = W.connect()
    libs = sorted(db.list_libraries())
    print(f"[census] {len(libs)} libraries visible in the catalogue", flush=True)

    out = {"generated_utc": W.stamp(), "trials": 0,
           "class": "collection-and-provenance",
           "n_libraries_visible": len(libs),
           "libraries_of_interest": {L: (L in libs) for L in LIBRARY_INTEREST},
           "libraries": libs,
           "note": ("A library appearing in list_libraries() is NOT evidence of entitlement -- "
                    "the catalogue is broader than the grant. Every target below was probed "
                    "with a real SELECT."),
           "targets": []}

    tgts = TARGETS[:a.limit] if a.limit else TARGETS
    for key, prio, lib, tbl, dc, why in tgts:
        if lib not in libs:
            rec = {"key": key, "priority": prio, "library": lib, "table": tbl,
                   "status": ABSENT, "error": "library not in catalogue for this account",
                   "unlocks": why, "checked_utc": W.stamp()}
        else:
            rec = _one(db, key, prio, lib, tbl, dc, why)
        span = rec.get("span")
        print(f"[census] {prio} {key:26s} {rec['status']:9s} "
              f"rows~{rec.get('rows_estimated', '-')!s:>14s} "
              f"{(span['from'] + '..' + span['to']) if span else ''}", flush=True)
        out["targets"].append(rec)

    os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n[census] wrote {a.json}")
    return out


if __name__ == "__main__":
    main()
