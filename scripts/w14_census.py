"""W-14 pass 0 - THE CENSUS GATE. Does a Cboe open-close product exist on THIS grant?

`PREREG_DRAFT_w14_cboe_openclose.md` is census-gated in its own words: *"nothing below runs until
`WRDS_CENSUS.md` confirms the product, fields and span."* It does not. `WRDS_CENSUS.md` probed the
OptionMetrics-REPLACEMENT shape - `optprice_2010`, `optprice_2016`, `ivlisted_2010`, `eqmaster`,
`optcontract`, `wrds_eq_opt_merged` - and found every one DENIED. It never probed open-close.

THAT DISTINCTION IS THE CENSUS'S OWN LESSON, quoted from its section 1: *"a census that probes the
names in a brief measures the brief."* The denial of six optprice-shaped tables is real evidence
about the `cboe` grant and is NOT a measurement of this product. So this runs before any register.

READ-ONLY AND SCHEMA-ONLY. It enumerates library and table NAMES, reads COLUMN NAMES, and takes
counts. No licensed row is persisted anywhere - the draft's own fence (`raw rows never leave
D:\\wrds`) is honoured by never materialising one.

    python -m scripts.w14_census
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import wrds_client as C                            # noqa: E402

OUT = "W14_CENSUS.json"

# The vocabulary an open-close product could plausibly carry. Enumerate rather than guess a single
# name - guessing one name and reporting absence is exactly how the last census measured a brief
# instead of a grant.
NEEDLES = ("opencl", "open_close", "openclose", "oc_", "_oc", "volume", "custom", "retail")

# What K3 actually requires: a CUSTOMER-vs-FIRM split on OPENING volume. A product carrying only
# total volume is not an identifier and is `MB15` again on a new axis.
K3_CUSTOMER = ("customer", "cust", "retail", "public")
K3_FIRM = ("firm", "market_maker", "marketmaker", "mm", "professional", "prof", "broker")
K3_OPEN = ("open", "opening")


def _data_root():
    for cand in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data"),
                 os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "..", "..", "..", "..", "data"))):
        if os.path.isdir(os.path.join(cand, "free_analysis")):
            return cand
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _out(name):
    return os.path.join(_data_root(), "free_analysis", name)


def main():
    creds = C.credentials_present()
    if not all(creds.values()):
        raise SystemExit("REFUSING: WRDS credentials absent %r. This is a census of a GRANT and "
                         "cannot be answered without one." % creds)

    conn = C.connect()
    rec = {"item": "W-14", "pass": "census-gate",
           "draft": "PREREG_DRAFT_w14_cboe_openclose.md",
           "why": "the draft is census-gated and WRDS_CENSUS.md probed the optprice shape, never "
                  "open-close. A denial of six optprice tables is evidence about the grant and is "
                  "NOT a measurement of this product.",
           "read_only": True, "rows_persisted": 0}

    db = conn

    def sql(q, params=None):
        return db.raw_sql(q, params=params) if params else db.raw_sql(q)

    # ---- 1. every library visible to this login -------------------------------------------
    libs = sorted(db.list_libraries())
    rec["n_libraries"] = len(libs)
    rec["cboe_like_libraries"] = sorted(l for l in libs if "cboe" in l.lower())
    print("libraries visible: %d ; cboe-like: %s"
          % (len(libs), rec["cboe_like_libraries"]), flush=True)

    # ---- 2. every table in every cboe-like library, by NAME ---------------------------------
    tables = {}
    for lib in rec["cboe_like_libraries"]:
        try:
            tables[lib] = sorted(db.list_tables(library=lib))
        except Exception as e:                                          # noqa: BLE001
            tables[lib] = []
            rec.setdefault("list_tables_errors", {})[lib] = str(e)[:120]
        print("  %-16s %d tables" % (lib, len(tables[lib])), flush=True)
    rec["cboe_tables"] = {k: len(v) for k, v in tables.items()}
    rec["cboe_table_names"] = tables

    # ---- 3. open-close candidates ANYWHERE on the account -----------------------------------
    q = ("select table_schema, table_name from information_schema.tables "
         "where lower(table_name) like '%%opencl%%' "
         "   or lower(table_name) like '%%open_close%%' "
         "   or lower(table_name) like '%%openclose%%' "
         "order by 1,2")
    try:
        df = sql(q)
        cands = [(r.table_schema, r.table_name) for r in df.itertuples()]
    except Exception as e:                                              # noqa: BLE001
        cands = []
        rec["account_wide_search_error"] = str(e)[:200]
    rec["openclose_candidates_account_wide"] = ["%s.%s" % (a, b) for a, b in cands]
    print("open-close candidates account-wide: %d" % len(cands), flush=True)
    for a, b in cands:
        print("   %s.%s" % (a, b), flush=True)

    interesting = []
    for lib, tl in tables.items():
        for t in tl:
            lt = t.lower()
            if any(nd in lt for nd in NEEDLES):
                interesting.append("%s.%s" % (lib, t))
    rec["cboe_tables_matching_vocabulary"] = sorted(interesting)
    print("cboe tables matching the open-close vocabulary: %d" % len(interesting), flush=True)
    for t in sorted(interesting)[:40]:
        print("   %s" % t, flush=True)

    # ---- 4. a REAL SELECT on each candidate. Entitlement is what a SELECT says. --------------
    probes = {}
    for full in rec["openclose_candidates_account_wide"] + rec["cboe_tables_matching_vocabulary"]:
        if full in probes:
            continue
        lib, tab = full.split(".", 1)
        try:
            head = sql("select * from %s.%s limit 1" % (lib, tab))
            cols = [str(c) for c in head.columns]
            probes[full] = {"readable": True, "n_columns": len(cols), "columns": cols}
            print("  READ  %-42s %d cols" % (full, len(cols)), flush=True)
        except Exception as e:                                          # noqa: BLE001
            msg = str(e).strip().split("\n")[0][:140]
            probes[full] = {"readable": False, "error": msg}
            print("  DENY  %-42s %s" % (full, msg), flush=True)
    rec["probes"] = probes

    # ---- 5. K3: does any READABLE candidate carry a customer/firm split on OPENING volume? ---
    k3 = {}
    for full, pr in probes.items():
        if not pr.get("readable"):
            continue
        cols = [c.lower() for c in pr["columns"]]
        k3[full] = {
            "customer_columns": sorted(c for c in cols if any(k in c for k in K3_CUSTOMER)),
            "firm_columns": sorted(c for c in cols if any(k in c for k in K3_FIRM)),
            "opening_columns": sorted(c for c in cols if any(k in c for k in K3_OPEN)),
        }
        k3[full]["separates_customer_from_firm"] = bool(
            k3[full]["customer_columns"] and k3[full]["firm_columns"])
        k3[full]["identifies_opening_volume"] = bool(k3[full]["opening_columns"])
    rec["k3_identification"] = k3

    readable = [f for f, p in probes.items() if p.get("readable")]
    rec["n_candidates"] = len(probes)
    rec["n_readable"] = len(readable)
    rec["gate"] = (
        "PASS" if any(v.get("separates_customer_from_firm") and v.get("identifies_opening_volume")
                      for v in k3.values())
        else ("NO_PRODUCT" if not probes else
              ("DENIED" if not readable else "READABLE_BUT_NO_IDENTIFIER")))

    with io.open(_out(OUT), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, default=str)
    print()
    print("candidates %d, readable %d" % (len(probes), len(readable)))
    print("GATE: %s" % rec["gate"])
    print("wrote %s" % _out(OUT))

    try:
        conn.close()
    except Exception:                                                   # noqa: BLE001
        pass


def columns_pass():
    """Does ANY table on this grant carry a customer-vs-firm split, or name opening volume?

    Table NAMES can hide a product; COLUMN names are what `K3` actually needs. This is the pass
    that makes NO_PRODUCT a measurement rather than an inference from a naming convention.
    """
    db = C.connect()
    out = {"item": "W-14", "pass": "census-gate-columns", "read_only": True, "rows_persisted": 0}

    df = db.raw_sql(
        "select table_schema, table_name, column_name from information_schema.columns "
        "where column_name ~* '(customer|firm|market.?maker|professional|retail|origin)' "
        "order by 1,2,3")
    out["n_matching_columns"] = int(len(df))
    df["k"] = df["table_schema"].astype(str) + "." + df["table_name"].astype(str)
    out["n_tables_matched"] = int(df["k"].nunique())

    both = []
    for k, g in df.groupby("k"):
        cols = [str(c).lower() for c in g["column_name"]]
        hc = [c for c in cols if any(x in c for x in K3_CUSTOMER)]
        hf = [c for c in cols if any(x in c for x in K3_FIRM)]
        if hc and hf:
            both.append({"table": k, "customer_columns": sorted(set(hc)),
                         "firm_columns": sorted(set(hf))})
    out["tables_with_customer_AND_firm_columns"] = both
    out["n_tables_with_both"] = len(both)
    out["distinct_matching_column_names"] = sorted(
        {str(c).lower() for c in df["column_name"]})[:80]

    d2 = db.raw_sql(
        "select table_schema, table_name, column_name from information_schema.columns "
        "where column_name ~* '(open.?buy|open.?sell|opening|buy.?open|sell.?open)' order by 1,2,3")
    out["n_opening_volume_columns"] = int(len(d2))
    out["opening_volume_tables"] = sorted(
        {"%s.%s" % (a, b) for a, b in zip(d2["table_schema"], d2["table_name"])})

    recheck = {}
    for t in ("cboe.optprice_2020", "cboe.optcontract", "cboe.eqmaster",
              "cboe_sample.optprice", "cboe_all.cboe"):
        lib, tab = t.split(".", 1)
        try:
            h = db.raw_sql("select * from %s.%s limit 1" % (lib, tab))
            recheck[t] = {"readable": True, "n_columns": int(len(h.columns)),
                          "columns": [str(c) for c in h.columns]}
        except Exception as e:                                          # noqa: BLE001
            recheck[t] = {"readable": False,
                          "error": str(e).strip().split("\n")[0][:140]}
    out["cboe_entitlement_recheck"] = recheck

    with io.open(_out("W14_CENSUS_COLUMNS.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("matching columns %d over %d tables; carrying BOTH customer and firm: %d"
          % (out["n_matching_columns"], out["n_tables_matched"], out["n_tables_with_both"]))
    print("columns naming OPENING volume anywhere: %d over %d tables"
          % (out["n_opening_volume_columns"], len(out["opening_volume_tables"])))
    print("wrote W14_CENSUS_COLUMNS.json")
    return out


def retail_pass():
    """Where the retail identifier on this grant actually lives, and whether it reads.

    CORRECTS `WRDS_CENSUS.md`, which searched 221 LIBRARY names for `Intraday Indicators by WRDS`
    and reported it ABSENT-ON-THIS-LOGIN. It is present as TABLES - `taqm_YYYY.wrds_iid_YYYY` -
    and returns `permission denied`, which is the STRONGER evidence that census said it lacked.
    Its conclusion stands; its reason changes. Reported, not edited: the data lane owns that file.
    """
    db = C.connect()
    out = {"item": "W-14", "pass": "census-retail-identifier",
           "read_only": True, "rows_persisted": 0}
    df = db.raw_sql("select table_schema, table_name, count(*) as n_retail_cols "
                    "from information_schema.columns where column_name ~* 'retail' "
                    "group by 1,2 order by 3 desc, 1,2")
    out["n_tables_with_retail_columns"] = int(len(df))
    top = [{"table": "%s.%s" % (a, b), "n_retail_cols": int(c)}
           for a, b, c in zip(df["table_schema"], df["table_name"], df["n_retail_cols"])][:20]
    out["top_tables"] = top

    probes = {}
    for t in [x["table"] for x in top[:6]]:
        lib, tab = t.split(".", 1)
        try:
            h = db.raw_sql("select * from %s.%s limit 1" % (lib, tab))
            probes[t] = {"readable": True, "n_columns": int(len(h.columns)),
                         "columns": [str(c) for c in h.columns][:60]}
        except Exception as e:                                          # noqa: BLE001
            probes[t] = {"readable": False,
                         "error": str(e).strip().split("\n")[0][:140]}
    out["probes"] = probes
    out["any_readable"] = any(v.get("readable") for v in probes.values())
    with io.open(_out("W14_RETAIL_IDENTIFIER.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("tables with a 'retail' column: %d ; any readable: %s"
          % (out["n_tables_with_retail_columns"], out["any_readable"]))
    print("wrote W14_RETAIL_IDENTIFIER.json")
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", action="store_true", help="pass 1: the product census")
    ap.add_argument("--columns", action="store_true", help="pass 2: the K3 identifier census")
    ap.add_argument("--retail", action="store_true", help="pass 3: where the identifier lives")
    a = ap.parse_args()
    if not (a.tables or a.columns or a.retail):
        a.tables = a.columns = a.retail = True
    if a.tables:
        main()
    if a.columns:
        columns_pass()
    if a.retail:
        retail_pass()
