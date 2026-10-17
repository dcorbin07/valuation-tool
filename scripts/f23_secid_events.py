# -*- coding: utf-8 -*-
"""`F23-SECID` — build BOTH arms' cluster events from the SEC's own data. No outcome is read.

    python -m scripts.f23_secid_events

Register: `PREREG_f23_secid.md`, committed **ALONE at `fba290e`**; **one equity trial booked at
`8191309` BEFORE this file existed**.

**BOTH ARMS COME OUT OF ONE PASS OVER ONE SOURCE, AND THAT IS THE REGISTER'S §1 DESIGN RATHER THAN
A CONVENIENCE.** Sourcing the ID arm from the SEC while leaving the name arm on SF2 would change
the **feed** and the **key** at once, so neither could be attributed. Here the rows are identical
and only the identity column differs:

* **ARM A (NAME):** distinct insiders counted by normalised `RPTOWNERNAME`.
* **ARM B (ID):** distinct insiders counted by `RPTOWNERCIK`.

**NOTHING HERE READS A FORWARD RETURN** — it emits event sets and an identity census. The arm that
scores them is a separate invocation (`O10`'s process defect).

**THE CLUSTER RULE IS THE SHIPPED ONE, PARAMETERISED ON ITS IDENTITY COLUMN RATHER THAN COPIED.**
`valuation/studies/insider_cluster.py` keys on `ownername` throughout, so this module feeds it a
frame whose identity column is whichever key the arm declares — the rule's own `K_PRIMARY`,
`WINDOW_DAYS`, `PURCHASE_CODE`, cooldown and strict two-prior-year condition are **imported and
called**, never restated (`B7`).
"""
from __future__ import annotations

import argparse
import io
import json
import os
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
from valuation.studies import insider_routine as IR                         # noqa: E402
from valuation.studies import sec_ticker_join as SJ                         # noqa: E402

OUT = "F23_SECID_EVENTS.json"
EVENTS_CSV = "F23_SECID_EVENTS_%s.csv"           # %s = arm key
CACHE = "f23_secid_sec_rows.pkl"

UA = "Valquo research (donniecorbin6@gmail.com)"

#: **TWO PATH PREFIXES, MEASURED.** The SEC moved recent quarters; older ones stayed put. A
#: quarter reachable under NEITHER is a REFUSAL and never a silently empty quarter — that is the
#: register's §1b and it is the `blank-code counter` family avoided rather than repeated.
PREFIXES = ("https://www.sec.gov/files/structureddata/data/"
            "insider-transactions-data-sets/%s_form345.zip",
            "https://www.sec.gov/files/datastandardsinnovation/data/"
            "insider-transactions-data-sets/%s_form345.zip")

#: The build era is 2009-2019. The strict rule needs each pair's TWO PRIOR calendar years, so the
#: pull starts 2007Q1 — derived from `IC.prior_year_presence`'s own condition, not chosen.
PULL_LO_YEAR, PULL_HI_YEAR = 2007, 2019
SLEEP = 0.35


def quarters():
    return [(y, q) for y in range(PULL_LO_YEAR, PULL_HI_YEAR + 1) for q in (1, 2, 3, 4)]


def _get(tag: str) -> bytes:
    last = []
    for pre in PREFIXES:
        url = pre % tag
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=240) as r:
                return r.read()
        except Exception as e:                                              # noqa: BLE001
            last.append("%s -> %r" % (url.split("/")[-2], e))
    raise SystemExit("REFUSING: %s unreachable under either prefix (%s). A quarter that cannot "
                     "be fetched is a refusal, not an empty quarter." % (tag, "; ".join(last)))


def quarter_rows(year: int, qtr: int) -> pd.DataFrame:
    """Open-market PURCHASE rows for one quarter, carrying BOTH identity columns.

    A positive control is applied per quarter: a real quarter cannot have zero Form 4 submissions,
    so a zero is a PARSER failure and refuses rather than contributing an empty frame.
    """
    tag = "%dq%d" % (year, qtr)
    raw = _get(tag)
    z = zipfile.ZipFile(io.BytesIO(raw))

    def tsv(name, cols):
        with z.open(name) as fh:
            return pd.read_csv(fh, sep="\t", usecols=cols, dtype=str, low_memory=False)

    sub = tsv("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL",
                                 "DOCUMENT_TYPE"])
    own = tsv("REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME"])
    tr = tsv("NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE"])

    n_f4 = int((sub["DOCUMENT_TYPE"].astype(str).str.strip() == "4").sum())
    if n_f4 == 0:
        raise SystemExit("REFUSING: %s parsed ZERO Form 4 submissions. A real EDGAR quarter cannot "
                         "have none, so this is a format problem and not an empty quarter." % tag)

    sub = sub[sub["DOCUMENT_TYPE"].astype(str).str.strip() == "4"]
    # THE SKIP IS EXPLICIT: a missing code is COUNTED and never read as not-a-purchase.
    code = tr["TRANS_CODE"].astype(str).str.strip()
    tr = tr[(code == IC.PURCHASE_CODE).fillna(False)]
    df = tr.merge(sub, on="ACCESSION_NUMBER").merge(own, on="ACCESSION_NUMBER")
    if df.empty:
        return pd.DataFrame(columns=["ticker", "name_key", "cik", "filingdate",
                                     "transactiondate", "quarter"])
    df["ticker"] = df["ISSUERTRADINGSYMBOL"].astype(str).str.strip().str.upper()
    df["name_key"] = df["RPTOWNERNAME"].map(_norm_name)
    df["cik"] = df["RPTOWNERCIK"].astype(str).str.strip()
    df["filingdate"] = pd.to_datetime(df["FILING_DATE"], format="mixed",
                                      errors="coerce").dt.strftime("%Y-%m-%d")
    df["transactiondate"] = pd.to_datetime(df["TRANS_DATE"], format="mixed",
                                           errors="coerce").dt.strftime("%Y-%m-%d")
    df["quarter"] = tag
    keep = (df["ticker"].notna() & (df["ticker"] != "") & df["filingdate"].notna()
            & df["transactiondate"].notna() & df["cik"].notna() & (df["cik"] != ""))
    return df.loc[keep, ["ticker", "name_key", "cik", "filingdate", "transactiondate",
                         "quarter"]].reset_index(drop=True)


def _norm_name(s) -> str:
    """The key `INSIDER-LIVE-FEED` already uses — upper-cased, punctuation dropped, whitespace
    collapsed. **Deliberately not a fuzzy match**: a threshold would make the comparison a tunable
    parameter and the register forbids that."""
    import re
    t = re.sub(r"[^A-Za-z0-9 ]", " ", str(s or "").upper())
    return " ".join(t.split())


def pull(force: bool = False) -> pd.DataFrame:
    p = D.out_path(CACHE)
    if os.path.isfile(p) and not force:
        df = pd.read_pickle(p)
        print("[events] cache: %d purchase rows over %d quarters"
              % (len(df), df["quarter"].nunique()), flush=True)
        return df
    t0 = time.time()
    frames, meta = [], []
    for (y, q) in quarters():
        f = quarter_rows(y, q)
        frames.append(f)
        meta.append({"quarter": "%dq%d" % (y, q), "purchase_rows": int(len(f))})
        print("    %dq%d  P-rows %6d   (%.0fs)" % (y, q, len(f), time.time() - t0), flush=True)
        time.sleep(SLEEP)
    df = pd.concat(frames, ignore_index=True)
    df.to_pickle(p)
    with io.open(D.out_path("F23_SECID_PULL.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"quarters": meta, "rows": int(len(df)),
                             "seconds": round(time.time() - t0, 1)}, indent=1))
    print("[events] pulled %d purchase rows over %d quarters in %.0fs"
          % (len(df), len(meta), time.time() - t0), flush=True)
    return df


def clusters(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """The SHIPPED cluster rule, fed a frame whose `ownername` column is `key`.

    `insider_cluster` keys on `ownername` by name, so the one honest way to vary the identity
    without a second implementation is to RENAME the chosen column into that slot and call the
    shipped functions. The rule's own `K_PRIMARY`, `WINDOW_DAYS`, cooldown and strict
    two-prior-year condition are untouched.
    """
    f = df.rename(columns={key: "ownername"})[
        ["ticker", "ownername", "filingdate", "transactiondate"]].copy()
    f["transactioncode"] = IC.PURCHASE_CODE

    # **THE LABELS ARE COMPUTED BY THE SHIPPED CLASSIFIER, AND THE FIRST CUT OF THIS FUNCTION
    # PASSED A PLACEHOLDER.** `opportunistic_purchases` keeps a row only where
    # `labels == IR.OPPORTUNISTIC`, so an empty-string Series would have kept **ZERO ROWS** and
    # both arms would have reported zero events without raising — the vacuous-pass family, caught
    # by reading the predicate rather than by anything failing.
    #
    # `insider_routine.classify` takes an `owner_col`, so the identity key varies HERE TOO, which
    # is correct and is part of what the register changes: whether a pair looks ROUTINE depends on
    # whose history you are looking at, so an ID-keyed arm must also classify by ID.
    labels = IR.classify(f, owner_col="ownername")
    opp = IC.opportunistic_purchases(f, labels, strict=True)
    ev = IC.cluster_events(opp)

    # A GATE, NOT A HOPE: a build era with no qualifying purchase is impossible on this data, so
    # an empty result is an instrument failure and refuses rather than scoring zero.
    if not len(opp):
        raise SystemExit("REFUSING: ARM keyed on %r produced ZERO opportunistic purchase rows "
                         "from %d input rows. On 13 years of SEC filings that is an instrument "
                         "failure, not an empty population." % (key, len(f)))
    return ev



def _label_mix(df: pd.DataFrame, key: str) -> dict:
    """The ROUTINE / OPPORTUNISTIC / UNCLASSIFIABLE split under this arm's identity key.

    Reported because the arm's population rests on it, and because the key changes it: a pair's
    routineness is a property of whose history you attribute the trades to.
    """
    f = df.rename(columns={key: "ownername"})
    lab = IR.classify(f, owner_col="ownername")
    vc = lab.value_counts()
    tot = int(len(lab)) or 1
    return {str(k): {"rows": int(v), "share": float(v) / tot} for k, v in vc.items()}


def identity_census(df: pd.DataFrame) -> dict:
    """What the ID key says about the NAME key — DECOMPOSED, per the register's §4.4.

    * a name carrying MORE THAN ONE cik  -> the name MERGED two people, so the name rule
      UNDER-counted distinct insiders and MISSED clusters;
    * a cik appearing under MORE THAN ONE name -> the name SPLIT one person, so the name rule
      OVER-counted and could fire a cluster that was ONE insider filing twice. **That is the
      false-trigger direction and the more serious one for a book.**
    """
    g = df.groupby("name_key")["cik"].nunique()
    h = df.groupby("cik")["name_key"].nunique()
    merged = g[g > 1]
    split = h[h > 1]
    # Per TICKER, which is the unit the rule counts within.
    gt = df.groupby(["ticker", "name_key"])["cik"].nunique()
    ht = df.groupby(["ticker", "cik"])["name_key"].nunique()
    return {
        "distinct_names": int(df["name_key"].nunique()),
        "distinct_ciks": int(df["cik"].nunique()),
        "names_carrying_more_than_one_cik": int(len(merged)),
        "names_carrying_more_than_one_cik_share": float(len(merged) / max(1, len(g))),
        "rows_under_a_merged_name": int(df["name_key"].isin(merged.index).sum()),
        "ciks_under_more_than_one_name": int(len(split)),
        "ciks_under_more_than_one_name_share": float(len(split) / max(1, len(h))),
        "rows_under_a_split_cik": int(df["cik"].isin(split.index).sum()),
        "within_ticker": {
            "ticker_name_pairs_with_multiple_ciks": int((gt > 1).sum()),
            "ticker_cik_pairs_with_multiple_names": int((ht > 1).sum()),
            "WHY_WITHIN_TICKER": ("the rule counts distinct insiders WITHIN one ticker, so the "
                                  "per-ticker figures are the ones that can change a cluster; the "
                                  "global figures include collisions across unrelated companies"),
        },
        "DIRECTION": ("names MERGING two people means the NAME rule UNDER-counted and MISSED "
                      "clusters; a cik under several names means it OVER-counted and could fire a "
                      "cluster that was ONE insider filing twice -- the false-trigger direction"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-pull", action="store_true")
    a = ap.parse_args(argv)

    df = pull(force=a.force_pull)

    # ----------------------------------------------------------------- THE TICKER JOIN, REPAIRED
    # **THIS IS THE ONE THING THAT CHANGED SINCE THE FIRST READ, AND IT IS A CORRECTNESS REPAIR
    # OF THE INSTRUMENT RATHER THAN A NEW CONSTRUCTION** (`U1-SPLIT` and `SELL-PREMIUM-2`'s
    # precedent, so the re-run charges no trial). `ISSUERTRADINGSYMBOL` is FREE TEXT: the first
    # read joined it to the panel verbatim and resolved 61.60% of build-era purchase rows, so the
    # arms were scored on a population the register never described.
    #
    # `sec_ticker_join.repair` substitutes the panel's own ticker, resolved from the filer's CIK at
    # the FILING DATE, and leaves an unresolved row carrying the symbol as filed — so the row set
    # is comparable and only newly-resolved rows move. Everything downstream of this line is
    # byte-identical to the first read: same rule, same `K_PRIMARY`, same classifier, same cell.
    pan = {str(t).upper() for t in pd.read_pickle(D.panel_path())["ticker"].unique()}
    raw_rate = float(df["ticker"].isin(pan).mean())
    df = SJ.repair(df, pan)
    rep_rate = float(df["ticker"].isin(pan).mean())
    if rep_rate < raw_rate:
        raise SystemExit("REFUSING: the repair resolved FEWER rows (%.4f -> %.4f). It can only "
                         "ever add a mapping, so a fall means the join is wired wrong."
                         % (raw_rate, rep_rate))
    print("[events] ticker join repaired: %.4f -> %.4f of rows resolve a panel ticker"
          % (raw_rate, rep_rate), flush=True)

    out = {"item": "F23-SECID", "part": "event sets for both arms, from ONE source",
           "ticker_join": {"module": "valuation/studies/sec_ticker_join.py",
                           "row_resolution_as_filed": raw_rate,
                           "row_resolution_repaired": rep_rate,
                           "WHAT_IT_IS": ("a CIK-to-panel-ticker map valid at each filing date; a "
                                          "correctness repair of the same read, not a new "
                                          "construction, so it charges no trial"),
                           "FIRST_READ_WAS_ON_THE_AS_FILED_SYMBOL": True},
           "register": "PREREG_f23_secid.md", "register_commit": "fba290e",
           "trial_booked_at": "8191309",
           "pull": {"quarters": int(df["quarter"].nunique()), "purchase_rows": int(len(df)),
                    "filing_date_min": str(df["filingdate"].min()),
                    "filing_date_max": str(df["filingdate"].max())},
           "NO_OUTCOME_READ": ("this module emits event sets and an identity census; no forward "
                               "return is loaded anywhere in it"),
           "arms": {}}

    print("[events] identity census ...", flush=True)
    out["identity_census"] = identity_census(df)
    ic = out["identity_census"]
    print("    distinct names %d vs ciks %d | names with >1 cik %d (%.4f) | ciks with >1 name %d "
          "(%.4f)" % (ic["distinct_names"], ic["distinct_ciks"],
                      ic["names_carrying_more_than_one_cik"],
                      ic["names_carrying_more_than_one_cik_share"],
                      ic["ciks_under_more_than_one_name"],
                      ic["ciks_under_more_than_one_name_share"]), flush=True)
    print("    WITHIN TICKER: name-pairs with >1 cik %d | cik-pairs with >1 name %d"
          % (ic["within_ticker"]["ticker_name_pairs_with_multiple_ciks"],
             ic["within_ticker"]["ticker_cik_pairs_with_multiple_names"]), flush=True)

    sets = {}
    for arm, key in (("name", "name_key"), ("id", "cik")):
        print("[events] ARM %s: clustering on %s ..." % (arm.upper(), key), flush=True)
        ev = clusters(df, key)
        ev.to_csv(D.out_path(EVENTS_CSV % arm), index=False)
        sets[arm] = set(zip(ev["ticker"].astype(str), ev["date"].astype(str)))
        out["arms"][arm] = {"identity_column": key, "n_events": int(len(ev)),
                            "label_mix": _label_mix(df, key),
                            "n_tickers": int(ev["ticker"].nunique()) if len(ev) else 0,
                            "date_min": str(ev["date"].min()) if len(ev) else None,
                            "date_max": str(ev["date"].max()) if len(ev) else None,
                            "csv": EVENTS_CSV % arm}
        print("    %d events over %d tickers" % (len(ev), out["arms"][arm]["n_tickers"]),
              flush=True)

    a_, b_ = sets["name"], sets["id"]
    both, union = a_ & b_, a_ | b_
    out["overlap"] = {"shared": len(both), "union": len(union),
                      "jaccard": (len(both) / len(union)) if union else None,
                      "only_name": len(a_ - b_), "only_id": len(b_ - a_),
                      "share_of_name_events_surviving_under_id":
                          (len(both) / len(a_)) if a_ else None,
                      "NOT_THE_83_PERCENT": ("the ~83% figure is INSIDER-LIVE-FEED's SEC-vs-SF2 "
                                             "event overlap on a 2026 window -- a FEED "
                                             "comparison. This is a KEY comparison on one feed "
                                             "and the two may not be conflated.")}
    print("[events] overlap: shared %d / union %d -> jaccard %.4f (only-name %d, only-id %d)"
          % (len(both), len(union), out["overlap"]["jaccard"] or 0,
             out["overlap"]["only_name"], out["overlap"]["only_id"]), flush=True)

    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[events] wrote %s" % p, flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
