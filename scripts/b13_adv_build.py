"""Build the point-in-time dollar-ADV instrument for the panel, and census its coverage.

ZERO TRIALS. **INSTRUMENT ONLY — no ranking arm runs in this pass** (`MB15`'s ordering: the
instrument is validated before any consumer reads it). Nothing here filters the universe,
re-scores a book, or compares anything to anything.

    python -m scripts.b13_adv_build --pull      # CRSP daily rows for our permnos -> D:\\wrds
    python -m scripts.b13_adv_build             # build the ADV panel + coverage census

The coverage figure that matters is measured **on the population the arm will test** — the
panel's own (ticker, date) cells — and is stated BEFORE any arm exists. A coverage number quoted
for a different population than the one scored is worth nothing, which this project established
the expensive way in `MB8` and again in `V6-OPT`.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import adv as ADV                                   # noqa: E402

PRIMARY = r"C:\Users\donni\Downloads\valuation-tool"
RAW = r"D:\wrds"
DSF = os.path.join(RAW, "crsp_dsf_panel")
PANEL = os.path.join(PRIMARY, "data", "free_analysis", "panel_corrected_69d.pkl")
OUT = os.path.join(PRIMARY, "data", "free_analysis", "B13_ADV_COVERAGE.json")
ADV_PKL = os.path.join(PRIMARY, "data", "free_analysis", "B13_ADV_PANEL.pkl")


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def panel_cells():
    import pandas as pd
    p = pd.read_pickle(PANEL)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["d"] = pd.to_datetime(p["date"]).dt.date
    return p


def stocknames(db):
    sn = db.raw_sql("select ticker, permno, namedt, nameenddt "
                    "from crsp.stocknames where ticker is not null")
    sn["ticker"] = sn["ticker"].astype(str).str.upper().str.strip()
    return sn


def pull(limit_years: int = 0) -> dict:
    """CRSP daily rows for OUR permnos only, chunked by year, resumable.

    Filtered to our permnos server-side rather than pulled whole: `dsf` is ~100M rows a decade
    and we need 2,271 names. The unit is the YEAR, and a unit already on disk with a matching
    manifest line is not re-pulled.
    """
    import pandas as pd
    from valuation.edge import wrds_client as W

    os.makedirs(DSF, exist_ok=True)
    mp = os.path.join(DSF, "MANIFEST.jsonl")
    man = {}
    if os.path.exists(mp):
        for line in open(mp, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue        # a torn final line costs that unit, never the file
            man[str(r["year"])] = r

    db = W.connect()
    p = panel_cells()
    iv = ADV.ticker_permno_intervals(stocknames(db))
    permnos = sorted({q for t in p["ticker"].unique() for q, _, _ in iv.get(t, ())})
    print(f"[adv] our tickers resolve to {len(permnos):,} distinct permnos "
          f"(date-scoping happens at JOIN time, not here)")

    lo = min(p["d"]).year
    hi = min(max(p["d"]).year, ADV.CRSP_CUT.year)
    years = [y for y in range(lo - 1, hi + 1)]      # -1: the trailing window reaches back a year
    if limit_years:
        years = years[:limit_years]
    inlist = ",".join(str(x) for x in permnos)

    for y in years:
        key = str(y)
        path = os.path.join(DSF, f"dsf_{y}.pkl")
        if key in man and os.path.exists(path) and \
                os.path.getsize(path) == man[key].get("bytes"):
            continue
        t0 = time.time()
        df = db.raw_sql(
            f"select permno, date, prc, vol from crsp_a_stock.dsf "
            f"where permno in ({inlist}) "
            f"and date >= '{y}-01-01' and date < '{y+1}-01-01'")
        tmp = path + ".tmp"
        df.to_pickle(tmp, compression="gzip")
        with open(tmp, "rb"):
            pass
        for k in range(8):
            try:
                os.replace(tmp, path)               # payload lands BEFORE the manifest line
                break
            except PermissionError:
                if k == 7:
                    raise
                time.sleep(0.25 * (k + 1))
        rec = {"year": y, "rows": int(len(df)), "bytes": os.path.getsize(path),
               "sha256": _sha(path), "seconds": round(time.time() - t0, 1), "utc": _utc()}
        with open(mp, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print(f"[adv] {y}: {len(df):,} rows {rec['bytes']/1e6:.0f}MB "
              f"{rec['seconds']:.0f}s", flush=True)
    return {"years": len(years)}


def build() -> dict:
    import pandas as pd
    from valuation.edge import wrds_client as W

    p = panel_cells()
    db = W.connect()
    iv = ADV.ticker_permno_intervals(stocknames(db))

    files = sorted(f for f in os.listdir(DSF) if f.startswith("dsf_") and f.endswith(".pkl"))
    if not files:
        raise SystemExit(f"{DSF} holds no daily files -- run --pull first. Refusing to report "
                         "zero coverage from an empty read.")
    daily = pd.concat([pd.read_pickle(os.path.join(DSF, f), compression="gzip")
                       for f in files], ignore_index=True)
    print(f"[adv] CRSP daily rows loaded: {len(daily):,}")

    negshare = ADV.negative_price_share(daily)
    print(f"[adv] CRSP negative (bid/ask midpoint) prices: "
          f"{negshare['negative_price_rows']:,} = {negshare['pct']}% -- abs() applied")

    ser = ADV.adv_series(daily)
    print(f"[adv] point-in-time ADV observations: {len(ser):,}")
    ser["d"] = ser["date"].dt.date
    lut = {(int(pn), d): float(a) for pn, d, a in
           zip(ser["permno"], ser["d"], ser["adv"])}

    # DATE-SCOPED JOIN. A {ticker: permno} dict would attribute one company's volume to another.
    rows, unresolved, no_adv = [], 0, 0
    amb = 0
    for t, d in zip(p["ticker"], p["d"]):
        pn = ADV.permno_on(iv, t, d)
        if pn is None:
            unresolved += 1
            continue
        a = lut.get((pn, d))
        if a is None:
            no_adv += 1
            continue
        rows.append((t, d, pn, a))
    for t in set(p["ticker"]):
        if len(iv.get(t, ())) > 1:
            amb += 1

    out_df = pd.DataFrame(rows, columns=["ticker", "date", "permno", "adv"])
    out_df.to_pickle(ADV_PKL)
    have = {(t, str(d)) for t, d, _, _ in rows}

    cells = [(t, str(d)) for t, d in zip(p["ticker"], p["d"])]
    cov = ADV.coverage({c: 1 for c in have}, cells)

    after_cut = [c for c in cells if c[1] > str(ADV.CRSP_CUT)]
    dates_after = sorted({c[1] for c in after_cut})
    before = [c for c in cells if c[1] <= str(ADV.CRSP_CUT)]
    cov_before = ADV.coverage({c: 1 for c in have}, before)

    res = {
        "item": "B13-ADV", "class": "instrument", "trials": 0, "generated_utc": _utc(),
        "definition": {
            "window_sessions": ADV.ADV_WINDOW_SESSIONS,
            "min_sessions": ADV.MIN_SESSIONS,
            "formula": "mean(|prc| * vol) over the trailing window, ending the PRIOR session",
            "matched_to": "valuation/screener/prices.py:243 (the live avg_dollar_volume)",
            "why": ("MIN_AVG_DOLLAR_VOLUME is calibrated against the LIVE quantity; choosing a "
                    "different window here would silently re-scale the threshold."),
        },
        "crsp_negative_price": negshare,
        "join": {"tickers_with_more_than_one_permno": amb,
                 "rule": "date-scoped via crsp.stocknames intervals",
                 "unresolved_cells": unresolved},
        "coverage_on_the_arms_population": cov,
        "coverage_excluding_dates_after_the_crsp_cut": cov_before,
        "crsp_cut": {
            "cut": str(ADV.CRSP_CUT),
            "panel_dates_after": len(dates_after), "dates_after": dates_after,
            "panel_rows_after": len(after_cut),
            "pct_of_panel_rows": round(100.0 * len(after_cut) / max(1, len(cells)), 2),
        },
        "cells_without_adv_before_the_cut": cov_before["without_adv"],
        "current_path_for_comparison": {
            "source": "data/bulk/prepared/bars/*.pkl", "names": 502,
            "pct_of_universe": 19.8},
        "adv_panel": ADV_PKL,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("definition", "current_path_for_comparison")}, indent=1))
    print(f"[adv] wrote {OUT} and {ADV_PKL}")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="B13/S7-4 dollar-ADV instrument (zero trials)")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--limit-years", type=int, default=0)
    a = ap.parse_args(argv)
    if a.pull:
        pull(a.limit_years)
        return
    build()


if __name__ == "__main__":
    main()
