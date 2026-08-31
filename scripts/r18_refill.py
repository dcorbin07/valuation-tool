"""EMERGENCY RE-PULL — the alphabetically truncated chain store (R18).

The ThetaData Pro window closes 2026-09-01. **ZERO TRIALS: collection only.**

THE DEFECT, as R18 measured it: `D:\\thetadata\\chains` has a symbol DIRECTORY for the full
alphabet, but the per-year FILES stop around "M" for 2019-2024. A top-level `ls` shows A..Z and
looks complete, which is exactly what hid it -- **the census must count FILES, never
directories.** Confirmed here: `MSFT` holds 2016, 2017, 2018 and nothing else, while `AAPL` runs
to 2025.

**The cut is economically non-neutral** -- R18 measured N-Z spreads at a 3.41% median against
3.05% for A-M -- so every spread statistic built on the store inherits a bias that is not noise.

**A NEW FREEZE, NEVER A MUTATION.** `D:\\thetadata\\chains` and its pinned freezes are a faithful
record of what the store WAS and are not touched: the refill lands in
`D:\\thetadata\\freeze_r18_refill_2026-08-31`. A census that was true when it was taken stays
true.

**IF THE CLOCK RUNS OUT MID-PULL, THE MANIFEST IS THE DELIVERABLE** -- it says exactly which
(symbol, year) units were captured and which were not, so a successor inherits a fact rather than
a guess.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import pickle
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW = r"D:\thetadata"
STORE = os.path.join(RAW, "chains")
FREEZE = os.path.join(RAW, "freeze_r18_refill_2026-08-31")
MAX_DTE = 1200

#: The years the store is truncated across. 2016-2018 are present for every name; the vendor's
#: own history starts 2012-07-17 (measured in the O-1 pull) but this refill repairs the
#: TRUNCATION rather than extending the store's declared span.
YEARS = list(range(2019, 2027))

FILE_RE = re.compile(r"^(?P<sym>.+)-(?P<year>\d{4})\.pkl$")


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def census() -> dict:
    """What the store actually HOLDS, counted from FILES.

    A directory listing is what hid this defect: every symbol has a directory, and the top-level
    view therefore shows a complete alphabet. The years live in the filenames.
    """
    have = collections.defaultdict(set)
    syms = sorted(d for d in os.listdir(STORE)
                  if os.path.isdir(os.path.join(STORE, d)))
    for s in syms:
        for f in os.listdir(os.path.join(STORE, s)):
            m = FILE_RE.match(f)
            if m and m.group("sym").upper() == s.upper():
                have[s.upper()].add(int(m.group("year")))
    return {"symbols": syms, "have": have}


def missing(have, years=YEARS):
    """(symbol, year) pairs absent from the store, plus the empty/exhausted markers honoured.

    A `.empty` or `.exhausted` marker means the vendor was ASKED and had nothing -- re-asking
    buys nothing and spends a window that closes tomorrow.
    """
    out = []
    for s in sorted(have):
        d = os.path.join(STORE, s)
        marks = set()
        for f in os.listdir(d):
            m = re.match(r"^(?P<sym>.+)-(?P<year>\d{4})\.pkl\.(empty|exhausted)$", f)
            if m:
                marks.add(int(m.group("year")))
        for y in years:
            if y not in have[s] and y not in marks:
                out.append((s, y))
    return out


def manifest_path() -> str:
    return os.path.join(FREEZE, "MANIFEST.jsonl")


def load_manifest() -> dict:
    p = manifest_path()
    out = {}
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue        # a torn final line costs that unit, never the file
        out[r["unit"]] = r
    return out


def append_manifest(rec: dict) -> None:
    os.makedirs(FREEZE, exist_ok=True)
    with open(manifest_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def unit_path(sym: str, year: int) -> str:
    return os.path.join(FREEZE, "chains", sym[:1].upper(), sym, f"{sym}-{year}.pkl")


def _replace_retry(tmp: str, dst: str, tries: int = 8) -> None:
    for k in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(0.25 * (k + 1))


def priority(pairs, have):
    """Highest-value first, because the window may not fit everything.

    Ordered by (1) the names R18 named and the most option-active N-Z names, then (2) how much
    of the store's own 2016-2018 depth the symbol already shows -- a name the store already
    carries deeply is one the rest of the project is most likely to be reading.
    """
    named = ["MSFT", "NVDA", "TSLA", "WMT", "XOM", "ZTS", "META", "NFLX", "ORCL", "PG",
             "PEP", "PFE", "QCOM", "T", "UNH", "V", "VZ", "WFC", "TXN", "TMO",
             "SPY", "QQQ", "NKE", "MRK", "MCD", "MA", "LLY", "SBUX", "RTX", "PYPL"]
    rank = {s: i for i, s in enumerate(named)}

    def depth(sym):
        return -len(have.get(sym, ()))

    return sorted(pairs, key=lambda p: (rank.get(p[0], 10_000), depth(p[0]), p[0], p[1]))


def pull_unit(tb, sym: str, year: int) -> dict:
    import pandas as pd
    cli = tb._cli()
    unit = f"{sym}|{year}"
    t0 = time.time()
    start, end = dt.date(year, 1, 1), dt.date(year, 12, 31)
    # `_fetch_year` -- NOT `_fetch_span`. It assembles the year from ADAPTIVE chunks and
    # remembers the working chunk size per name, which is what the original harvest used and
    # what stops a wide-ladder name (BKNG: 396,240 rows a quarter) failing the same way every
    # run.
    #
    # AND IT RETURNS A TUPLE `(frame, failed)`. The first cut of this function pickled the tuple
    # and reported **`rows` = 2 on a 14.7 MB payload** -- `len()` of a 2-tuple. Caught by
    # disbelieving the numbers rather than by anything raising, which is `MA31`'s failure mode:
    # it wrote a real 14.7 MB of real data under a row count that was arithmetic on the wrong
    # object, and every downstream census would have read the store as two rows a year.
    got = tb._fetch_year(sym, year)
    df, failed = got if isinstance(got, tuple) else (got, False)
    el = time.time() - t0
    if isinstance(df, str):
        return {"unit": unit, "symbol": sym, "year": year, "status": "fault",
                "seconds": round(el, 1), "utc": _utc()}
    if df is None or not len(df):
        # ASKED AND EMPTY is a fact about the vendor, recorded as its own state so a later
        # reader can tell it from "we never got to this unit before the window closed".
        return {"unit": unit, "symbol": sym, "year": year, "status": "empty_vendor",
                "rows": 0, "seconds": round(el, 1), "utc": _utc()}
    p = unit_path(sym, year)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "wb") as fh:
        pickle.dump(df, fh, protocol=4)
        fh.flush()
        os.fsync(fh.fileno())
    _replace_retry(tmp, p)                       # payload lands BEFORE its manifest line
    # A year assembled from chunks where SOME chunk failed is `ok_partial`, never `ok`. The
    # original harvest recorded 145 such years, and collapsing them into `ok` is how a short
    # year comes to look complete to every later reader.
    return {"unit": unit, "symbol": sym, "year": year,
            "status": "ok_partial" if failed else "ok",
            "rows": int(len(df)), "bytes": os.path.getsize(p), "sha256": sha256(p),
            "seconds": round(el, 1), "utc": _utc()}


def run(limit: int = 0, deadline_min: int = 0) -> dict:
    from valuation.edge import theta_bulk as TB
    c = census()
    miss = missing(c["have"])
    ordered = priority(miss, c["have"])
    man = load_manifest()
    todo = [(s, y) for s, y in ordered
            if man.get(f"{s}|{y}", {}).get("status") not in ("ok", "ok_partial", "empty_vendor")]
    if limit:
        todo = todo[:limit]
    print(f"[r18] store: {len(c['symbols']):,} symbol dirs, "
          f"{sum(len(v) for v in c['have'].values()):,} year FILES", flush=True)
    print(f"[r18] missing (symbol, year) pairs {YEARS[0]}-{YEARS[-1]}: {len(miss):,}", flush=True)
    print(f"[r18] to pull now: {len(todo):,} (resume: {len(man):,} recorded)", flush=True)

    tb = TB.ThetaBulk(root=STORE, max_dte=MAX_DTE)
    if tb._cli() is None:
        print("[r18] THE WINDOW IS CLOSED -- no vendor client. Recorded and stopping.")
        return {"window": "closed"}

    t0, done, nb, nrows = time.time(), 0, 0, 0
    for sym, year in todo:
        if deadline_min and (time.time() - t0) / 60 >= deadline_min:
            print(f"[r18] DEADLINE {deadline_min}m reached -- stopping cleanly. "
                  f"The manifest is the deliverable.", flush=True)
            break
        rec = pull_unit(tb, sym, year)
        append_manifest(rec)
        done += 1
        nb += rec.get("bytes", 0)
        nrows += rec.get("rows", 0)
        el = time.time() - t0
        if done % 10 == 0 or done == len(todo):
            eta = (len(todo) - done) * el / max(1, done)
            print(f"[r18] {done:,}/{len(todo):,} {nrows:,} rows {nb/1e9:.2f}GB "
                  f"{el/60:.0f}m elapsed {eta/60:.0f}m left", flush=True)
    print(f"[r18] stopped after {done:,} units, {nrows:,} rows, {nb/1e9:.2f} GB, "
          f"{(time.time()-t0)/60:.0f} min", flush=True)
    return {"units": done, "rows": nrows, "bytes": nb}


def report() -> dict:
    c = census()
    miss = missing(c["have"])
    man = load_manifest()
    got = {k for k, v in man.items() if v.get("status") in ("ok", "ok_partial")}
    empt = {k for k, v in man.items() if v.get("status") == "empty_vendor"}
    still = [f"{s}|{y}" for s, y in miss if f"{s}|{y}" not in got and f"{s}|{y}" not in empt]
    out = {"generated_utc": _utc(), "trials": 0, "freeze": FREEZE,
           "store_symbol_dirs": len(c["symbols"]),
           "store_year_files": sum(len(v) for v in c["have"].values()),
           "missing_pairs_at_census": len(miss),
           "captured": len(got), "empty_at_vendor": len(empt),
           "still_missing": len(still),
           "rows": sum(v.get("rows", 0) for v in man.values()),
           "bytes": sum(v.get("bytes", 0) for v in man.values()),
           "still_missing_sample": sorted(still)[:40]}
    out["gb"] = round(out["bytes"] / 1e9, 3)
    print(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="R18 emergency refill (collection only)")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--deadline-min", type=int, default=0)
    a = ap.parse_args(argv)
    if a.report:
        report()
        return
    if a.census:
        c = census()
        miss = missing(c["have"])
        by_year = collections.Counter(y for _, y in miss)
        by_letter = collections.Counter(s[0] for s, _ in miss)
        print(f"symbol dirs: {len(c['symbols']):,}")
        print(f"year files : {sum(len(v) for v in c['have'].values()):,}")
        print(f"missing    : {len(miss):,} (symbol, year) pairs over {YEARS[0]}-{YEARS[-1]}")
        print(f"  by year  : {dict(sorted(by_year.items()))}")
        print(f"  by letter: {dict(sorted(by_letter.items()))}")
        json.dump({"missing": [f"{s}|{y}" for s, y in miss],
                   "by_year": {str(k): v for k, v in sorted(by_year.items())},
                   "by_letter": dict(sorted(by_letter.items()))},
                  open(os.path.join(RAW, "R18_MISSING.json"), "w", encoding="utf-8"), indent=1)
        print(f"wrote {os.path.join(RAW, 'R18_MISSING.json')}")
        return
    run(a.limit, a.deadline_min)
    report()


if __name__ == "__main__":
    main()
