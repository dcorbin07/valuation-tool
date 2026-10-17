# -*- coding: utf-8 -*-
"""`INSIDER-STAGE3` — SIZING the SEC free-data build. ZERO TRIALS, and it BUILDS NOTHING.

    python -m scripts.insider_stage3_sec_size

**IT DOWNLOADS ONLY EDGAR'S OWN QUARTERLY FORM INDEXES AND COUNTS FORM 4 LINES.** No filing is
fetched, no XML is parsed, nothing is stored under `data/` but the count. `DECISIONS.md`
2026-10-14: *"reports the size of that build to Don before building it"* — so this measures the
size and stops, which is the `S25` discipline.

**WHY A COUNT RATHER THAN AN ESTIMATE.** `INSIDER-WIDE` spent a whole section on a power table
that was optimistic by ~1.5x because it was scaled rather than measured. A build estimate guessed
from "a few hundred thousand filings a year" is the same error with a bigger number attached, and
Don is being asked to decide on it.

**SEC FAIR ACCESS IS HONOURED**: a declared `User-Agent` with a contact address, as
`https://www.sec.gov/os/webmaster-faq#developers` requires, and the request rate is thrown well
under the documented 10/second.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import zipfile

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as D                                  # noqa: E402

OUT = "INSIDER_STAGE3_SEC_SIZE.json"

#: SEC fair access: the webmaster FAQ requires a declared User-Agent naming the requester.
UA = "Valquo research (donniecorbin6@gmail.com)"
#: **`master.idx`, NOT `form.idx`, AND THE FIRST CUT OF THIS SCRIPT GOT IT WRONG AND REPORTED ZERO.**
#: `form.idx` is **FIXED-WIDTH** (`'4                SOME CO ... '`) while `master.idx` is
#: **pipe-delimited** as `CIK|Company Name|Form Type|Date Filed|Filename`. The first cut read
#: `form.zip` and skipped every line lacking a `|`, so it counted **0 Form 4 filings across
#: four years** -- impossible, since Form 4 is the most-filed type on EDGAR -- and reported the
#: zero as an answer. **Caught by disbelieving the number, not by anything raising:** the
#: `blank-code counter` family, and a zero here would have argued that the SEC build is free.
#: Hence `_CONTROL_FORMS` below: a quarter whose count of a known-common form is zero is a
#: PARSER failure and is refused rather than reported.
BASE = "https://www.sec.gov/Archives/edgar/full-index/%d/QTR%d/master.zip"

#: Forms that MUST appear in any real EDGAR quarter. The positive control.
_CONTROL_FORMS = ("8-K", "10-Q")

#: The quarters a build would need, and WHY each is needed:
#:   2004-2005 -- the PRIOR-YEAR HISTORY the strict two-prior-year rule needs to emit in 2006.
#:                Only reachable as RAW Form 4 XML; the SEC's curated data sets start 2006 Q1.
#:   2006-2007 -- the two years the curated set DOES cover and owned data does not.
HISTORY_QUARTERS = [(y, q) for y in (2004, 2005) for q in (1, 2, 3, 4)]
GAIN_QUARTERS = [(y, q) for y in (2006, 2007) for q in (1, 2, 3, 4)]

SLEEP = 0.4                                   # well under the documented 10/second


def _get(url: str) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def count_form4(year: int, qtr: int) -> dict:
    """Form 4 filings in one quarter, counted from EDGAR's own `master.idx`.

    `master.idx` is `CIK|Company Name|Form Type|Date Filed|Filename`, so the form type is **field
    index 2** and a Form 4 row is one whose type is **exactly `4`**. Exactly matters: `4/A` is an
    amendment and would inflate the count, and an inflated size estimate argues for a build Don
    has not agreed to.

    **GATED ON A POSITIVE CONTROL.** A quarter whose `8-K` or `10-Q` count is zero is a PARSER
    failure, not an empty quarter, and is returned as `PARSER FAILED` rather than as a number --
    because the first cut of this function returned **zero Form 4s for eight consecutive
    quarters** and said so without complaint.
    """
    url = BASE % (year, qtr)
    t0 = time.time()
    try:
        raw = _get(url)
    except Exception as e:                                                  # noqa: BLE001
        return {"year": year, "qtr": qtr, "status": "FETCH FAILED: %r" % (e,)}
    n4 = n4a = total = 0
    control = {f: 0 for f in _CONTROL_FORMS}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".idx")]
        if not name:
            return {"year": year, "qtr": qtr, "status": "NO .idx IN ZIP",
                    "names": z.namelist()}
        with z.open(name[0]) as fh:
            for line in io.TextIOWrapper(fh, encoding="latin-1"):
                parts = line.split("|")
                if len(parts) < 5:
                    continue
                ft = parts[2].strip()
                total += 1
                if ft == "4":
                    n4 += 1
                elif ft == "4/A":
                    n4a += 1
                if ft in control:
                    control[ft] += 1
    row = {"year": year, "qtr": qtr, "bytes_downloaded": len(raw),
           "idx_data_rows": total, "form_4": n4, "form_4_A_amendments": n4a,
           "control_form_counts": control, "seconds": round(time.time() - t0, 1)}
    if total == 0 or any(v == 0 for v in control.values()):
        row["status"] = ("PARSER FAILED -- a real EDGAR quarter cannot have zero 8-K or 10-Q "
                         "filings, so this is a format problem and NOT an empty quarter")
        row["form_4"] = None
    return row


def main(argv=None):
    out = {"item": "INSIDER-STAGE3", "part": "SEC free-data build SIZE",
           "trials": 0, "CLASS": "FACTS -- sizes only, nothing built and no filing fetched",
           "sec_pages_read": {
               "insider_transactions_data_sets":
                   "https://www.sec.gov/data-research/sec-markets-data/"
                   "insider-transactions-data-sets",
               "curated_coverage": "January 2006 - September 2026 (the page's own header)",
               "electronic_filing_mandate":
                   "https://www.sec.gov/files/rules/final/33-8230.htm -- Release 33-8230, "
                   "issued 2003-05-07, EFFECTIVE 2003-06-30, mandating electronic filing of "
                   "Forms 3/4/5 under Sarbanes-Oxley section 403; the release records only ~8 "
                   "percent filed electronically in June 2002, so pre-mandate coverage is not "
                   "usable",
           },
           "quarters": {}}

    for label, qs in (("history_2004_2005_raw_edgar_only", HISTORY_QUARTERS),
                      ("gain_2006_2007_curated_or_raw", GAIN_QUARTERS)):
        tot4 = tot4a = totb = 0
        rows = {}
        for (y, q) in qs:
            print("[size] %dQ%d ..." % (y, q), flush=True)
            r = count_form4(y, q)
            rows["%dQ%d" % (y, q)] = r
            if r.get("form_4") is not None:
                tot4 += r["form_4"]
                tot4a += r["form_4_A_amendments"]
                totb += r["bytes_downloaded"]
                print("    Form 4: %6d   (4/A: %5d)  idx %.1f MB"
                      % (r["form_4"], r["form_4_A_amendments"],
                         r["bytes_downloaded"] / 1e6), flush=True)
            else:
                print("    %s" % r.get("status"), flush=True)
            time.sleep(SLEEP)
        out["quarters"][label] = {"by_quarter": rows, "form_4_total": tot4,
                                 "form_4_A_total": tot4a,
                                 "index_bytes_downloaded": totb}

    h = out["quarters"]["history_2004_2005_raw_edgar_only"]["form_4_total"]
    g = out["quarters"]["gain_2006_2007_curated_or_raw"]["form_4_total"]
    out["build"] = {
        "form_4_filings_2004_2005": h,
        "form_4_filings_2006_2007": g,
        "form_4_filings_total_to_fetch": h + g,
        "WHY_BOTH": ("2006-2007 are the YEARS GAINED; 2004-2005 are the PRIOR-YEAR HISTORY the "
                     "strict two-prior-year rule needs before 2006 can emit anything. Fetching "
                     "only the gain years leaves the rule unable to fire in them, which is "
                     "exactly the defect owned data already has."),
        "fetch_hours_at_10_per_second": round((h + g) / 10.0 / 3600.0, 1),
        "fetch_hours_at_a_polite_5_per_second": round((h + g) / 5.0 / 3600.0, 1),
        "RATE_SOURCE": ("the SEC's webmaster FAQ documents 10 requests/second as the fair-access "
                        "ceiling; a build should sit under it, so both figures ship"),
    }
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[size] Form 4 filings to fetch: %d (2004-05 history %d + 2006-07 gain %d)"
          % (h + g, h, g), flush=True)
    print("[size] wrote %s" % p, flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
