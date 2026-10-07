# -*- coding: utf-8 -*-
"""`POOL-SIZE` part (b) STAGE 1 — can a FULL-UNIVERSE 1999-2008 panel be built? ZERO TRIALS.

Register `PREREG_pool_size.md` §4 requires part (b) to be built from the freeze's **full raw**
`SEP` / `SF1` / `DAILY` / `ACTIONS` and **explicitly not** from `data/backtest`, which
`PANEL-EXT-RECHECK` measured to be selected on **2026** size. This stage measures, from the raw
zips, whether each input the shipped builder needs actually exists at full-universe scale for
1999-2008 — **before** anything is scored.

**WHY A CENSUS COMES FIRST.** §4 says *"a failure to build correctly is reported as a failure,
not worked around"*, and the shipped builder reads **three** separate objects, not one:

  * `fundamentals.csv` — the provider derives its **universe** from this file's ticker index, so
    whatever it contains IS the universe.
  * `prices/<TICKER>.csv` — one file per name.
  * the **bulk `daily.pkl` cache** for point-in-time market cap, which is a *different* object
    from the backtest export and is what `size` and the re-priced EV legs read.

If any one of the three cannot be formed for the pre-2009 window at full universe, part (b) is
not buildable as specified and that is the result.

Streams the zips; nothing is extracted and nothing licensed leaves `data/`.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import zipfile
from collections import Counter

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

WINDOW = ("1999-01-01", "2008-12-31")
#: the builder needs price history BEFORE the first rebalance (momentum is 252 trading days)
LOOKBACK_FROM = "1997-12-31"


def _zip_csv(path):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    fh = z.open(name)
    return z, csv.reader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))


def census_sep(raw):
    """Distinct tickers with a close in the window, and how many delist inside it."""
    p = [os.path.join(raw, f) for f in os.listdir(raw) if f.startswith("SHARADAR_SEP_")][0]
    z, r = _zip_csv(p)
    head = next(r)
    ti, di = head.index("ticker"), head.index("date")
    first, last, rows = {}, {}, 0
    t0 = time.time()
    for row in r:
        rows += 1
        t, d = row[ti], row[di][:10]
        if t not in first or d < first[t]:
            first[t] = d
        if t not in last or d > last[t]:
            last[t] = d
        if rows % 10_000_000 == 0:
            print("    sep %dM rows, %d tickers, %.0fs"
                  % (rows / 1e6, len(first), time.time() - t0), flush=True)
    z.close()
    in_win = [t for t in first if first[t] <= WINDOW[1] and last[t] >= WINDOW[0]]
    gone = [t for t in in_win if last[t] < "2009-01-01"]
    have_lookback = [t for t in in_win if first[t] <= LOOKBACK_FROM]
    return {"rows": rows, "tickers_total": len(first), "tickers_in_window": len(in_win),
            "delisted_in_window": len(gone),
            "delisted_share": len(gone) / max(1, len(in_win)),
            "with_full_lookback": len(have_lookback)}, set(in_win)


def census_sf1(raw, want):
    """ARQ rows dated inside the window, per ticker -- the provider's universe comes from here."""
    p = [os.path.join(raw, f) for f in os.listdir(raw) if f.startswith("SHARADAR_SF1_")][0]
    z, r = _zip_csv(p)
    head = next(r)
    ti, di = head.index("ticker"), head.index("datekey")
    dim = head.index("dimension") if "dimension" in head else None
    per, rows, arq = Counter(), 0, 0
    for row in r:
        rows += 1
        if dim is not None and row[dim] != "ARQ":
            continue
        arq += 1
        d = row[di][:10]
        if LOOKBACK_FROM <= d <= WINDOW[1]:
            per[row[ti]] += 1
    z.close()
    enough = [t for t, n in per.items() if n >= 8]        # ~2 years of quarters
    return {"rows": rows, "arq_rows": arq, "tickers_with_any": len(per),
            "tickers_with_8plus_quarters": len(enough),
            "overlap_with_sep": len(set(per) & want),
            "overlap_8plus_with_sep": len(set(enough) & want)}


def census_daily(raw, want):
    """Point-in-time market cap. A DIFFERENT object from the export, and `size` reads it."""
    p = [os.path.join(raw, f) for f in os.listdir(raw) if f.startswith("SHARADAR_DAILY_")][0]
    z, r = _zip_csv(p)
    head = next(r)
    ti, di = head.index("ticker"), head.index("date")
    mi = head.index("marketcap") if "marketcap" in head else None
    per, rows, first = Counter(), 0, {}
    for row in r:
        rows += 1
        d = row[di][:10]
        if d > WINDOW[1]:
            continue
        t = row[ti]
        if t not in first or d < first[t]:
            first[t] = d
        if d >= WINDOW[0] and (mi is None or row[mi] not in ("", None)):
            per[t] += 1
    z.close()
    return {"rows": rows, "tickers_in_window": len(per),
            "overlap_with_sep": len(set(per) & want),
            "earliest_date_seen": (min(first.values()) if first else None),
            "has_marketcap_column": mi is not None}


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    raw = os.path.join(data, "backtest_freeze_2026-10", "raw")
    if not os.path.isdir(raw):
        print("REFUSING: no raw freeze at %s" % raw)
        return 2
    fa = os.path.join(data, "free_analysis")

    print("STAGE 1 census, window %s .. %s (lookback from %s)"
          % (WINDOW[0], WINDOW[1], LOOKBACK_FROM), flush=True)
    print("  scanning SEP ...", flush=True)
    sep, want = census_sep(raw)
    print("    %s" % json.dumps(sep), flush=True)
    print("  scanning SF1 ...", flush=True)
    sf1 = census_sf1(raw, want)
    print("    %s" % json.dumps(sf1), flush=True)
    print("  scanning DAILY ...", flush=True)
    dly = census_daily(raw, want)
    print("    %s" % json.dumps(dly), flush=True)

    buildable = (sep["tickers_in_window"] > 2000 and sf1["overlap_8plus_with_sep"] > 1000
                 and dly["overlap_with_sep"] > 1000)
    res = {"item": "POOL-SIZE", "part": "b stage 1 census", "trials": 0,
           "register": "PREREG_pool_size.md section 4",
           "window": list(WINDOW), "lookback_from": LOOKBACK_FROM,
           "sep": sep, "sf1": sf1, "daily": dly,
           "themes_available_pre_2009": ["value", "quality", "momentum",
                                         "capital_discipline", "size"],
           "themes_absent_pre_2009": {"institutional": "sf3 starts 2013-06-30 (PANEL-EXT-RECHECK)",
                                      "insider": "sf2 filingdate starts 2008-01-02; the census "
                                                 "measured coverage at 0.307 by 2008 against "
                                                 "the 70% rule"},
           "buildable": bool(buildable)}
    json.dump(res, io.open(os.path.join(fa, "POOL_SIZE_OOS_CENSUS.json"), "w",
                           encoding="utf-8"), indent=2)
    print("\nBUILDABLE: %s" % buildable)
    print("wrote %s" % os.path.join(fa, "POOL_SIZE_OOS_CENSUS.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
