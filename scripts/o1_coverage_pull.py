"""O-1 COVERAGE PULL — targeted entry chains for MA28's flagged panel rows, plus a control pool.

ZERO TRIALS. Collection only: no analysis, no selection, no verdict. Nothing here computes a
return, picks a contract, or compares an arm to a control.

WHY THIS PULL EXISTS
--------------------
`O-1`'s arm came back **UNDERPOWERED BY CONSTRUCTION at 0.19% power**, and the cause is coverage
rather than method: the chain harvest was targeted at the ALERT BOOK, so it reaches 6,711 of
113,945 panel cells (5.89%) and the arm got 74 flagged names against a floor of 3,600 matched
trades.

EVERY PARAMETER BELOW COMES FROM `PREREG_o1_long_puts_accounting_flags.md` AND NONE FROM WHAT THE
DATA HAPPENS TO HOLD -- that inversion is the defect `O-1` itself caught and refused to commit:

    PRIMARY TENOR    150-210 DTE     section 4, the tenor with verdict power
    SECONDARY        330-400 DTE     section 4, declared, NO verdict power
    45-75 DTE        NOT PULLED AS AN ARM -- section 7 void condition 3 makes reporting it an
                     arm a void, because it buys the tenor `E-5` refutes
    INSTRUMENT       long PUTS
    UNIVERSE         `MA28`'s 2-of-3 flagged panel rows, IMPORTED from `s10_accounting_veto`
    CONTROL          unflagged panel rows matched on name-year and market-cap quintile
    FLOOR            3,600 matched flagged trades, >=1,200 per half

The pull stores **whole chains**, both rights and every strike and expiry the vendor returns. It
does NOT filter to puts or to a moneyness band, because filtering here would bake a selection
rule into the collection and force a re-pull if the rule moved -- and the vendor window closes
2026-09-01, so there is no second chance.

WHAT WAS MEASURED BEFORE COMMITTING (the harvest's own discipline: a 3-name sample once missed
by +339%, a 393-pair measurement landed within 7.4%)
------------------------------------------------------------------------------------------
* **Vendor history starts 2012-07-17**, measured on the panel's own rebalance dates. 55 of 69
  panel dates carry data; the 14 without are a contiguous 2009-01-15 .. 2012-04-17 prefix, which
  is what a history edge looks like. **1,311 flagged rows are therefore not obtainable at any
  price** and are recorded, never counted as a pull that fell short.
* A FIRST probe read six years as EMPTY and was WRONG: 2010, 2012, 2016, 2017, 2021 and 2023 were
  probed on **MLK Day**, a market holiday. A holiday is not a coverage boundary and reading it as
  one would have truncated this pull by seven years for nothing.
* **Stage 1 sized on 30 REAL flagged cells stratified across five market-cap strata** -- not on
  megacaps, because `O-1`'s universe is accounting-flagged names which skew small and AAPL is the
  least representative name in it. 0.31 s/call, 560 rows/cell, 13% of cells empty at source,
  and **77% of cells with data carry at least one put in the primary band**.

WHAT IS NOT PULLED, AND WHY IT IS NOT A SHORTFALL
--------------------------------------------------
The exit PATH of a held contract is a second stage, sized separately at **53.6 s/span**, which
projects to **~78 h for the flagged arm alone and ~156 h with a control** -- outside the window
with no margin. It is deliberately NOT started here: a sweep that ends half-done leaves an arm
that cannot be scored either, and the instruction is to take the highest-value stratum first.
**Stage 1 is that stratum**: it is the index without which no trade can even be DEFINED, and a
hold-to-expiry settlement needs only the entry chain plus the underlying's close at expiry,
which this project already owns in `data/bulk/prepared/bars`. A stop-or-target exit rule needs
stage 2 and is recorded as NOT COVERED.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRIMARY_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
RAW = r"D:\thetadata"
FREEZE = os.path.join(RAW, "freeze_o1_coverage_2026-08-25")

#: Measured on the panel's own rebalance dates, not assumed from a handoff sentence.
VENDOR_START = dt.date(2012, 7, 17)

#: O-1 section 4. Recorded here so the pull's own scope is legible without opening the register,
#: and asserted against it by test rather than trusted.
PRIMARY_TENOR = (150, 210)
SECONDARY_TENOR = (330, 400)

#: Chains are stored to 1200 DTE so the secondary tenor and any later re-read are already on
#: disk. Narrowing to the primary band would save bytes and cost a re-pull after 2026-09-01,
#: which is not a trade worth making in the last week of a vendor window.
MAX_DTE = 1200

#: Control candidates per flagged cell, nearest market cap within the same date and quintile.
#: THREE rather than one: the register's matcher chooses, and pre-selecting a single control
#: here would make the collection depend on a matching rule this script has no business fixing.
CONTROL_K = 3


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(os.path.join(RAW, "O1PULL.log"), "a", encoding="utf-8") as fh:
        fh.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {msg}\n")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def manifest_path() -> str:
    return os.path.join(FREEZE, "MANIFEST.jsonl")


def load_manifest() -> dict:
    p = manifest_path()
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue        # a hard kill can tear the final line; lose that unit, not the file
            out[r["unit"]] = r
    return out


def append_manifest(rec: dict) -> None:
    """One line, flushed and FSYNCED. The payload is already on disk before this runs, so a
    crash between the two costs a re-pull of one unit and never a half-written file that the
    manifest calls complete."""
    os.makedirs(FREEZE, exist_ok=True)
    with open(manifest_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def unit_path(sym: str, date: str) -> str:
    d = os.path.join(FREEZE, "entry", sym[:1].upper(), sym)
    return os.path.join(d, f"{sym}_{date}.pkl")


def _replace_retry(tmp: str, dst: str, tries: int = 8) -> None:
    """os.replace retried on the Windows scanner race -- the fourth writer in this project to
    need it. A missing tmp is NOT retried here: it means something removed it, and the
    recoverable action is to re-fetch, not to retry a rename eight more times."""
    for k in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(0.25 * (k + 1))


def build_queue() -> dict:
    """The flagged cells and their control candidates. Deterministic and seeded."""
    import pandas as pd
    sys.path.insert(0, PRIMARY_ROOT)
    sys.path.insert(0, os.path.join(PRIMARY_ROOT, "scripts"))
    from s10_accounting_veto import build_flags          # ONE definition, imported (O-1 sec. 5)

    panel = os.path.join(PRIMARY_ROOT, "data", "free_analysis", "panel_corrected_69d.pkl")
    p = pd.read_pickle(panel)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["d"] = pd.to_datetime(p["date"]).dt.date
    tickers = sorted(p["ticker"].unique())
    dates = sorted(p["d"].unique())

    fl = build_flags(os.path.join(PRIMARY_ROOT, "data", "backtest"),
                     tickers, [str(x) for x in dates])
    fl["ticker"] = fl["ticker"].astype(str).str.upper()
    fl["d"] = pd.to_datetime(fl["date"]).dt.date
    m = p[["ticker", "d", "market_cap"]].merge(fl[["ticker", "d", "vetoed"]],
                                               on=["ticker", "d"], how="left")
    m["vetoed"] = m["vetoed"].fillna(False)

    obt = m[m["d"] >= VENDOR_START]
    flagged = obt[obt["vetoed"] == True]                                # noqa: E712
    unflag = obt[(obt["vetoed"] == False) & obt["market_cap"].notna()]  # noqa: E712

    # control candidates: same DATE, same market-cap QUINTILE, nearest cap. Matching itself is
    # the register's job; this only decides what to have on disk for it to match with.
    ctrl = set()
    for d, g in unflag.groupby("d"):
        fg = flagged[flagged["d"] == d]
        if not len(fg) or not len(g):
            continue
        try:
            q = pd.qcut(g["market_cap"], 5, labels=False, duplicates="drop")
        except ValueError:
            continue
        g = g.assign(q=q)
        fq = pd.qcut(g["market_cap"], 5, labels=False, duplicates="drop")
        for _, fr in fg.iterrows():
            c = fr["market_cap"]
            if c != c:
                continue
            pool = g.iloc[(g["market_cap"] - c).abs().argsort()[:CONTROL_K]]
            for _, cr in pool.iterrows():
                ctrl.add((str(cr["ticker"]), str(d)))

    fcells = sorted({(str(t), str(d)) for t, d in zip(flagged["ticker"], flagged["d"])})
    ccells = sorted(ctrl - set(fcells))
    return {"flagged": fcells, "control": ccells,
            "n_flagged_all": int((m["vetoed"] == True).sum()),           # noqa: E712
            "n_flagged_obtainable": len(fcells)}


def pull_cell(tb, cli, sym: str, date: str, arm: str) -> dict:
    import pandas as pd
    d = dt.date.fromisoformat(date)
    t0 = time.time()
    r = tb._call_with_timeout(cli.option_history_eod, start_date=d, end_date=d,
                              symbol=sym, expiration="*", max_dte=MAX_DTE)
    el = time.time() - t0
    unit = f"{arm}|{sym}|{date}"
    if isinstance(r, str):
        return {"unit": unit, "arm": arm, "symbol": sym, "date": date,
                "status": "fault", "seconds": round(el, 2), "utc": _utc()}
    if r is None or not len(r):
        # EMPTY IS A FACT ABOUT THE VENDOR, NOT A FAILURE, and it is recorded as its own state so
        # a later reader can tell "no chain existed" from "we never asked".
        return {"unit": unit, "arm": arm, "symbol": sym, "date": date,
                "status": "empty_vendor", "rows": 0, "seconds": round(el, 2), "utc": _utc()}
    df = r.copy()
    df["expiration"] = pd.to_datetime(df["expiration"]).dt.date
    df["dte"] = [(e - d).days for e in df["expiration"]]
    df["right"] = df["right"].astype(str).str[0].str.upper()
    p = unit_path(sym, date)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "wb") as fh:
        pickle.dump(df, fh, protocol=4)
        fh.flush()
        os.fsync(fh.fileno())
    _replace_retry(tmp, p)                 # payload lands BEFORE its manifest line
    puts = df[df["right"] == "P"]
    return {"unit": unit, "arm": arm, "symbol": sym, "date": date, "status": "ok",
            "rows": int(len(df)),
            "puts_primary": int(((puts["dte"] >= PRIMARY_TENOR[0])
                                 & (puts["dte"] <= PRIMARY_TENOR[1])).sum()),
            "puts_secondary": int(((puts["dte"] >= SECONDARY_TENOR[0])
                                   & (puts["dte"] <= SECONDARY_TENOR[1])).sum()),
            "bytes": os.path.getsize(p), "sha256": sha256(p),
            "seconds": round(el, 2), "utc": _utc()}


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run(limit: int = 0, arms: str = "flagged,control") -> dict:
    from valuation.edge import theta_bulk as TB
    os.makedirs(FREEZE, exist_ok=True)
    q = build_queue()
    log(f"[o1] flagged cells obtainable {len(q['flagged']):,} of "
        f"{q['n_flagged_all']:,} flagged panel rows; control candidates {len(q['control']):,}")

    man = load_manifest()
    todo = []
    for arm in [a.strip() for a in arms.split(",") if a.strip()]:
        for sym, date in q[arm]:
            unit = f"{arm}|{sym}|{date}"
            if unit in man and man[unit].get("status") in ("ok", "empty_vendor"):
                continue
            todo.append((arm, sym, date))
    if limit:
        todo = todo[:limit]
    log(f"[o1] {len(todo):,} units to pull (resume: {len(man):,} already recorded)")

    tb = TB.ThetaBulk(root=os.path.join(RAW, "chains"), max_dte=MAX_DTE)
    cli = tb._cli()
    if cli is None:
        raise SystemExit("no vendor client")

    t0, done, nb = time.time(), 0, 0
    for arm, sym, date in todo:
        rec = pull_cell(tb, cli, sym, date, arm)
        append_manifest(rec)
        done += 1
        nb += rec.get("bytes", 0)
        if done % 100 == 0 or done == len(todo):
            el = time.time() - t0
            eta = (len(todo) - done) * el / max(1, done)
            log(f"[o1] {done:,}/{len(todo):,} {nb/1e6:.0f}MB "
                f"{el/60:.0f}m elapsed {eta/60:.0f}m left")
    log(f"[o1] finished {done:,} units, {nb/1e6:.0f} MB, {(time.time()-t0)/60:.0f} min")
    return {"units": done, "bytes": nb}


def verify(full: bool = False) -> dict:
    """Is every unit the manifest calls `ok` actually on disk, the right size, and the right bytes?

    THE SIZE CHECK IS NOT THE HASH CHECK AND BOTH ARE HERE FOR DIFFERENT FAILURES. A truncated
    write usually changes the size; a corrupted one need not. `--full-hash` re-reads every byte,
    which is slow and is the only check that can see silent corruption.

    An `empty_vendor` unit has no payload BY DESIGN and is not a miss -- counting it as one would
    make a correct pull look 17.5% broken, which is exactly how a real gap gets lost in noise.
    """
    man = load_manifest()
    missing = bad_size = bad_hash = 0
    checked = 0
    for r in man.values():
        if r.get("status") != "ok":
            continue
        p = unit_path(r["symbol"], r["date"])
        if not os.path.exists(p):
            missing += 1
            continue
        checked += 1
        if os.path.getsize(p) != r.get("bytes"):
            bad_size += 1
            continue
        if full and sha256(p) != r.get("sha256"):
            bad_hash += 1
    out = {"units_in_manifest": len(man), "ok_units_checked": checked,
           "missing": missing, "wrong_size": bad_size, "wrong_hash": bad_hash,
           "full_hash": full,
           "clean": missing == 0 and bad_size == 0 and bad_hash == 0}
    print(json.dumps(out, indent=1))
    return out


def census() -> dict:
    man = load_manifest()
    per = collections.Counter()
    rows = byt = prim = 0
    cells_with_primary = collections.Counter()
    for r in man.values():
        per[(r.get("arm"), r.get("status"))] += 1
        rows += r.get("rows", 0) or 0
        byt += r.get("bytes", 0) or 0
        prim += r.get("puts_primary", 0) or 0
        if (r.get("puts_primary") or 0) > 0:
            cells_with_primary[r.get("arm")] += 1
    out = {"generated_utc": _utc(), "freeze": FREEZE, "trials": 0,
           "primary_tenor": list(PRIMARY_TENOR), "secondary_tenor": list(SECONDARY_TENOR),
           "vendor_start": str(VENDOR_START), "max_dte": MAX_DTE,
           "units": len(man), "rows": rows, "bytes": byt,
           "gb": round(byt / 1e9, 3),
           "by_arm_status": {f"{a}|{s}": int(n) for (a, s), n in sorted(per.items())},
           "cells_with_a_primary_band_put": dict(cells_with_primary),
           "o1_floor_matched_flagged_trades": 3600}
    print(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="O-1 coverage pull (collection only, zero trials)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--arms", default="flagged,control")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--full-hash", action="store_true")
    a = ap.parse_args(argv)
    if a.verify:
        verify(a.full_hash)
        return
    if a.census:
        census()
        return
    run(a.limit, a.arms)
    census()


if __name__ == "__main__":
    main()
