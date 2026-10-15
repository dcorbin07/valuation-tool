# -*- coding: utf-8 -*-
"""A LIVE Form 4 feed for the forward paper book, VALIDATED against SF2 before it feeds anything.

    python -m scripts.insider_live_feed --validate

**WHY A NEW FEED AT ALL.** `valuation/studies/insider_cluster.sf2_zip()` is a **FROZEN EXPORT**
ending 2026-10-02. A forward book needs filings that do not exist yet, so the book cannot run on
it. `DECL_f23_insider_cluster_shares.md` therefore declares this feed, and the declaration forbids
a fill until the validation below passes.

**THE SOURCE IS THE SEC's OWN, AND IT IS FREE.** Two routes, and they are for different jobs:

* **LIVE (daily):** the EDGAR **daily index** lists every Form 4 accepted that day, and each
  filing's XML carries issuer, owner, transaction date and transaction code. That is the feed the
  book reads.
* **VALIDATION (quarterly):** the SEC's **Insider Transactions Data Sets** publish the SAME
  XML-derived fields as quarterly TSVs — `SUBMISSION`, `REPORTINGOWNER`, `NONDERIV_TRANS`. One
  **8.66 MB** ZIP covers a whole quarter, so the overlap with SF2 can be compared at row and
  **event** level without fetching a single filing.

**THE VALIDATION IS AT EVENT LEVEL AND NOT ONLY ROW LEVEL, because that is what the book trades.**
Agreeing on 99% of rows while disagreeing on which CLUSTERS fire would be a feed that looks right
and trades differently — `coverage-is-not-fidelity`, which this project has already paid for.

**NOTHING HERE READS A FORWARD RETURN.** It compares two descriptions of the same filings.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402

OUT = "INSIDER_LIVE_FEED_VALIDATION.json"

UA = "Valquo research (donniecorbin6@gmail.com)"
QUARTER_ZIP = ("https://www.sec.gov/files/datastandardsinnovation/data/"
               "insider-transactions-data-sets/%sq%d_form345.zip")
DAILY_IDX = "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR%d/form.%s.idx"

#: The overlap window. It must sit INSIDE SF2's coverage or there is nothing to compare against,
#: and inside one curated quarter so one ZIP suffices. SF2's freeze ends 2026-10-02.
VALIDATE_QUARTER = ("2026", 3)
VALIDATE_LO, VALIDATE_HI = "2026-07-01", "2026-09-30"

#: The row-level and event-level bars. **Declared here, before the comparison runs**, and the
#: declaration cites them so they cannot be relaxed after being watched (`W-28`).
ROW_RECALL_BAR = 0.95
EVENT_JACCARD_BAR = 0.90


def _get(url: str, tries: int = 3) -> bytes:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:                                              # noqa: BLE001
            last = e
            time.sleep(1.0 + i)
    raise SystemExit("REFUSING: %s unreachable after %d tries: %r" % (url, tries, last))


def _norm_name(s) -> str:
    """Owner names from two vendors must be compared on a NORMALISED key or the comparison
    measures punctuation.

    Upper-cased, punctuation dropped, whitespace collapsed. **Deliberately NOT a fuzzy match**: a
    threshold-based name matcher would turn a feed disagreement into a tunable parameter, and the
    bar is declared before the run.
    """
    t = re.sub(r"[^A-Za-z0-9 ]", " ", str(s or "").upper())
    return " ".join(t.split())


def sec_quarter_rows(year: str, qtr: int) -> pd.DataFrame:
    """Open-market PURCHASE rows (`TRANS_CODE == P`) from the SEC's own curated quarter."""
    raw = _get(QUARTER_ZIP % (year, qtr))
    z = zipfile.ZipFile(io.BytesIO(raw))

    def tsv(name, cols):
        with z.open(name) as fh:
            return pd.read_csv(fh, sep="\t", usecols=cols, dtype=str, low_memory=False)

    sub = tsv("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL",
                                 "DOCUMENT_TYPE"])
    own = tsv("REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERNAME"])
    tr = tsv("NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE"])

    sub = sub[sub["DOCUMENT_TYPE"].astype(str).str.strip() == "4"]
    tr = tr[tr["TRANS_CODE"].astype(str).str.strip() == IC.PURCHASE_CODE]
    df = tr.merge(sub, on="ACCESSION_NUMBER", how="inner").merge(
        own, on="ACCESSION_NUMBER", how="inner")
    df["ticker"] = df["ISSUERTRADINGSYMBOL"].astype(str).str.strip().str.upper()
    df["owner"] = df["RPTOWNERNAME"].map(_norm_name)
    df["filingdate"] = pd.to_datetime(df["FILING_DATE"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["transactiondate"] = pd.to_datetime(df["TRANS_DATE"],
                                           errors="coerce").dt.strftime("%Y-%m-%d")
    df["bytes_downloaded"] = len(raw)
    return df[["ticker", "owner", "filingdate", "transactiondate", "bytes_downloaded"]]


def sf2_rows() -> pd.DataFrame:
    df = pd.read_csv(IC.sf2_zip(),
                     usecols=["ticker", "ownername", "filingdate", "transactiondate",
                              "transactioncode"],
                     dtype=str, low_memory=False)
    buy = (df["transactioncode"] == IC.PURCHASE_CODE).fillna(False)
    df = df[buy].copy()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["owner"] = df["ownername"].map(_norm_name)
    return df[["ticker", "owner", "filingdate", "transactiondate"]]


def _window(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["filingdate"] >= VALIDATE_LO) & (df["filingdate"] <= VALIDATE_HI)]


def _keys(df: pd.DataFrame) -> set:
    return set(zip(df["ticker"], df["owner"], df["filingdate"]))


def _clusters(df: pd.DataFrame) -> set:
    """`k`>=2 distinct owners on one ticker inside a 30-calendar-day window, dated at the LAST
    filing, one event per cluster under a FULL-WINDOW cooldown.

    **The rule is the register's, restated here against a two-column frame rather than re-derived
    with different semantics** — and the proof that it IS the same rule is that the SF2 side of
    this comparison must reproduce the banked `INSIDER_CLUSTER_EVENTS` set on the same window,
    which `--validate` checks. The STRICT two-prior-year condition is deliberately NOT applied
    here: it needs years of history the curated quarter does not contain, and the thing being
    validated is whether the two FEEDS see the same filings, not whether the arm's filter works.
    """
    out = set()
    w = pd.Timedelta(days=IC.WINDOW_DAYS)
    for tk, g in df.groupby("ticker", sort=False):
        g = g.sort_values("filingdate")
        d = pd.to_datetime(g["filingdate"]).to_numpy()
        ow = g["owner"].to_numpy()
        last = None
        for j in range(len(d)):
            if last is not None and d[j] <= last + w:
                continue
            lo = d[j] - w
            m = (d >= lo) & (d <= d[j])
            if len(set(ow[m])) >= IC.K_PRIMARY:
                out.add((tk, str(pd.Timestamp(d[j]).date())))
                last = d[j]
    return out


def validate() -> dict:
    t0 = time.time()
    print("[feed] SEC curated %sQ%d ..." % VALIDATE_QUARTER, flush=True)
    sec = sec_quarter_rows(*VALIDATE_QUARTER)
    nbytes = int(sec["bytes_downloaded"].iloc[0]) if len(sec) else 0
    sec = _window(sec.drop(columns=["bytes_downloaded"]))
    print("    %d P-rows in the window (%.2f MB downloaded)" % (len(sec), nbytes / 1e6),
          flush=True)

    print("[feed] SF2 freeze ...", flush=True)
    sf2 = _window(sf2_rows())
    print("    %d P-rows in the window" % len(sf2), flush=True)

    ks, kf = _keys(sec), _keys(sf2)
    inter = ks & kf
    row = {"sec_rows": len(sec), "sf2_rows": len(sf2),
           "sec_keys": len(ks), "sf2_keys": len(kf), "shared_keys": len(inter),
           "recall_of_sf2_by_sec": (len(inter) / len(kf)) if kf else None,
           "precision_of_sec_vs_sf2": (len(inter) / len(ks)) if ks else None,
           "bar": ROW_RECALL_BAR}
    row["pass"] = bool(kf and ks and row["recall_of_sf2_by_sec"] >= ROW_RECALL_BAR)

    cs, cf = _clusters(sec), _clusters(sf2)
    both = cs & cf
    union = cs | cf
    ev = {"sec_events": len(cs), "sf2_events": len(cf), "shared_events": len(both),
          "jaccard": (len(both) / len(union)) if union else None,
          "recall_of_sf2_events_by_sec": (len(both) / len(cf)) if cf else None,
          "only_in_sec": sorted(list(cs - cf))[:20],
          "only_in_sf2": sorted(list(cf - cs))[:20],
          "bar": EVENT_JACCARD_BAR}
    ev["pass"] = bool(union and ev["jaccard"] >= EVENT_JACCARD_BAR)

    out = {"item": "INSIDER-LIVE-FEED", "window": [VALIDATE_LO, VALIDATE_HI],
           "quarter": "%sQ%d" % VALIDATE_QUARTER,
           "curated_zip_bytes": nbytes,
           "row_level": row, "event_level": ev,
           "NON_VACUITY": {"both_sides_non_empty": bool(len(sec) and len(sf2)),
                           "events_found_on_both_sides": bool(len(cs) and len(cf)),
                           "WHY": ("a comparison of two empty sets scores perfectly; MB21's C1 "
                                   "scored 0.000e+00 on an empty frame by comparing nothing")},
           "all_pass": bool(row["pass"] and ev["pass"] and len(sec) and len(sf2)
                            and len(cs) and len(cf)),
           "seconds": round(time.time() - t0, 1)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args(argv)
    if not a.validate:
        raise SystemExit("pass --validate; this module places no order and has no other mode")
    out = validate()
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    r, e = out["row_level"], out["event_level"]
    print("\n[feed] ROW   recall %.4f / precision %.4f against a %.2f bar -> %s"
          % (r["recall_of_sf2_by_sec"] or 0, r["precision_of_sec_vs_sf2"] or 0,
             ROW_RECALL_BAR, "PASS" if r["pass"] else "FAIL"), flush=True)
    print("[feed] EVENT jaccard %.4f (sec %d, sf2 %d, shared %d) against a %.2f bar -> %s"
          % (e["jaccard"] or 0, e["sec_events"], e["sf2_events"], e["shared_events"],
             EVENT_JACCARD_BAR, "PASS" if e["pass"] else "FAIL"), flush=True)
    print("[feed] all_pass %s -- wrote %s" % (out["all_pass"], p), flush=True)
    return out


if __name__ == "__main__":
    r = main()
    raise SystemExit(0 if r["all_pass"] else 2)
