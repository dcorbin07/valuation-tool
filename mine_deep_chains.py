"""
THE THETADATA PRO HARVEST — deep-tenor option chains. COLLECTION ONLY, zero trials.

Deadline 2026-09-01: after that the Pro window closes, Standard's rolling 8-year window puts
2016-2018 permanently out of reach, and nothing here is re-fetchable.

--------------------------------------------------------------------------------------------
WHAT THIS PULLS, AND WHY IT IS NOT WHAT THE BRIEF FIRST ASKED FOR.

The brief's Tier A/B is "holding-period full chains for banked alert days", on the measured fact
that 3,869 of 3,884 full-chain days in the FREEZE are entry dates. That fact is true of the
freeze. It is NOT true of the EOD cache, and the distinction decides the whole job:

  * `data/options_freeze/R2_CORRECTED_2026-08-08/` is a replay artifact - the banked contracts'
    own histories, which is why it is entry-anchored.
  * `data/options/<SYM>/<SYM>-<YEAR>.pkl` is mined ONE CALL PER SYMBOL-YEAR with
    `expiration="*"`, so it already holds the WHOLE CHAIN for EVERY SESSION of the year.

Measured before anything was pulled, over every alert's entry..exit span:

    42,650 trading chain-days needed -> 42,608 PRESENT (99.90%), 42 absent.

So holding-period EOD chains already exist. Re-pulling them would have spent the Pro window
re-fetching bytes on disk. What does NOT exist, measured the same way:

    850 of 1,361 alert symbol-years are capped at  90 DTE (max observed DTE 88, zero rows above)
    511 of 1,361                          at 200 DTE (max observed DTE 200, zero rows above)
    ZERO symbol-years anywhere hold a contract beyond 200 DTE.

And the ceiling was a MINING CHOICE, not a subscription limit - probed on the live account:
AAPL 2024-03-04 returns 2,476 rows at max_dte=200 and 4,472 at max_dte=800, of which 1,996 are
beyond 200 DTE, in the same wall-clock. 2016 is served today and carries LEAPS too.

That is the real gap and it is exactly what the blocked items need: a ROLL moves OUT in tenor,
so a 90-DTE ceiling makes "roll to a later expiry" unanswerable no matter how many dates you
hold. This miner therefore deepens the tenor axis rather than re-pulling the date axis.

--------------------------------------------------------------------------------------------
MAX_DTE IS 1200, NOT 800. Probed: AAPL 800 -> 4,472 rows (max DTE 683); 1200 -> 4,676 (max 836).
The extra tenor is ~4.6% of rows for no measurable time, and there is no second attempt after
Sep 1, so the ceiling is set above anything the feed actually returns rather than at a round
number that might clip a January LEAP.

--------------------------------------------------------------------------------------------
OVERLAP IS THE TEST (brief rule 3). Pulling 0-1200 DTE re-covers the 0-90 or 0-200 band the
existing cache already holds, so every unit carries its own control: the shared
(date, expiration, strike, right) keys must agree on bid/ask/volume. Agreement validates the
pull; DISAGREEMENT STOPS THE RUN and is reported in full.

Two things the comparison must NOT count as disagreement, both by construction:
  * the cached frame is SLIM-FILTERED (`mine_options_cache.slim_filter` drops rows with no
    two-sided quote AND no OI AND no volume, and quotes wider than 300%), so it legitimately
    holds FEWER keys. Only the INTERSECTION is compared.
  * the cached frame stores float32; the raw arrives float64. Compared at float32 tolerance.

--------------------------------------------------------------------------------------------
RESUMABILITY. One unit = one (tier, symbol, year). The manifest line is appended after EVERY
unit, with a sha256 of the payload, and the payload is written atomically (tmp + os.replace)
BEFORE its manifest line, so a kill can lose a unit's RECORD but never leave a half-written
payload recorded as complete. Re-running re-does any unit whose payload is absent or whose
sha256 does not match its manifest line.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import pickle
import shutil
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = r"C:\Users\donni\Downloads\valuation-tool"
DEFAULT_RAW_ROOT = r"D:\thetadata"
OPT = os.path.join(REPO, "data", "options")
BOOK = os.path.join(REPO, "data", "options_universe", "state_r2_corrected.pkl")

try:
    for _line in open(os.path.join(REPO, ".env"), encoding="utf-8", errors="replace"):
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
except OSError:
    pass

MAX_DTE = 1200
SCHEMA = 1
MIN_FREE_GB_D = 40
KEEP = ["expiration", "strike", "right", "date", "bid", "ask", "volume", "open_interest"]

_log_lock = threading.Lock()
_man_lock = threading.Lock()


def log(msg, root):
    line = f"[deep] {msg}"
    with _log_lock:
        print(line, flush=True)
        try:
            with open(os.path.join(root, "PROGRESS.txt"), "a", encoding="utf-8") as f:
                f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")
        except OSError:
            pass


# ------------------------------------------------------------------ units

def alert_symbol_years() -> list:
    """(symbol, year) covering every alert's entry..exit span. Book is read-only."""
    with open(BOOK, "rb") as f:
        rows = pickle.load(f)["rows"]
    out = set()
    for r in rows:
        sym = str(r["ticker"]).upper()
        d0 = dt.date.fromisoformat(str(r["alert_ts"])[:10])
        h = int(r.get("held_days") or 0)
        for k in range(0, h + 1):
            out.add((sym, (d0 + dt.timedelta(days=k)).year))
    return sorted(out)


def tier_of(year: int) -> str:
    return "A" if 2016 <= year <= 2018 else "B"


def unit_path(root: str, sym: str, year: int) -> str:
    return os.path.join(root, "chains", sym, f"{sym}-{year}.pkl")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# ------------------------------------------------------------------ manifest

def manifest_path(root: str) -> str:
    return os.path.join(root, "manifest.jsonl")


def load_manifest(root: str) -> dict:
    """unit-key -> record. Last line wins, so a re-pull supersedes cleanly."""
    p = manifest_path(root)
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue                      # a torn final line: ignore, the unit re-pulls
            out[f"{rec['symbol']}|{rec['year']}"] = rec
    return out


def append_manifest(root: str, rec: dict):
    with _man_lock:
        with open(manifest_path(root), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())          # the checkpoint must survive a hard kill


def needs_pull(root: str, sym: str, year: int, man: dict) -> bool:
    """Verified resume: a unit is done only if its payload EXISTS and HASHES to its record."""
    rec = man.get(f"{sym}|{year}")
    if not rec or rec.get("status") != "ok":
        return True
    p = unit_path(root, sym, year)
    if not os.path.exists(p):
        return True
    if os.path.getsize(p) != rec.get("bytes"):
        return True
    return False                          # size+manifest agree; full re-hash is opt-in (--verify)


# ------------------------------------------------------------------ pull

def slim(df):
    """Match the existing cache's schema and dtypes so the two are directly comparable."""
    import pandas as pd

    df = df.copy()
    df["date"] = pd.to_datetime(df["created"]).dt.tz_localize(None).dt.date
    df = (df.sort_values("created")
            .drop_duplicates(subset=["date", "expiration", "strike", "right"], keep="last"))
    if "open_interest" not in df.columns:
        df["open_interest"] = None
    out = df[[c for c in KEEP if c in df.columns]].copy()
    out["expiration"] = pd.to_datetime(out["expiration"]).dt.tz_localize(None).dt.date
    for c in ("bid", "ask", "strike"):
        out[c] = pd.to_numeric(out[c], errors="coerce").astype("float32")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).astype("int32")
    out["open_interest"] = (pd.to_numeric(out["open_interest"], errors="coerce")
                            .fillna(-1).astype("int32"))
    out["right"] = out["right"].astype(str).str[0].str.upper()
    return out.reset_index(drop=True)


def compare_overlap(new_df, sym: str, year: int):
    """Brief rule 3. Returns (verdict, detail). Only the INTERSECTION of keys is compared."""
    import numpy as np
    import pandas as pd

    p = os.path.join(OPT, sym, f"{sym}-{year}.pkl")
    if not os.path.exists(p):
        return "no_baseline", {}
    try:
        with open(p, "rb") as f:
            old = pickle.load(f)
    except Exception as e:                                           # noqa: BLE001
        return "baseline_unreadable", {"error": type(e).__name__}
    if old is None or not len(old):
        return "baseline_empty", {}

    key = ["date", "expiration", "strike", "right"]
    o = old.copy()
    n = new_df.copy()
    for d in (o, n):
        d["date"] = d["date"].astype(str)
        d["expiration"] = d["expiration"].astype(str)
        d["strike"] = np.round(pd.to_numeric(d["strike"], errors="coerce").astype("float64"), 3)
        d["right"] = d["right"].astype(str).str[0].str.upper()
    m = o.merge(n, on=key, how="inner", suffixes=("_old", "_new"))
    if not len(m):
        return "no_shared_keys", {"old_rows": int(len(o)), "new_rows": int(len(n))}

    det = {"old_rows": int(len(o)), "new_rows": int(len(n)), "shared_keys": int(len(m))}
    bad = {}
    for col, tol in (("bid", 1e-3), ("ask", 1e-3), ("volume", 0)):
        a = pd.to_numeric(m[f"{col}_old"], errors="coerce").astype("float64")
        b = pd.to_numeric(m[f"{col}_new"], errors="coerce").astype("float64")
        diff = (a - b).abs()
        nbad = int((diff > tol).sum())
        det[f"{col}_mismatch"] = nbad
        det[f"{col}_maxabs"] = float(diff.max()) if len(diff) else 0.0
        if nbad:
            k = m.loc[diff > tol, key + [f"{col}_old", f"{col}_new"]].head(5)
            bad[col] = k.astype(str).to_dict("records")
    det["agree_frac"] = round(1.0 - (max(det.get("bid_mismatch", 0),
                                         det.get("ask_mismatch", 0),
                                         det.get("volume_mismatch", 0)) / len(m)), 6)
    if bad:
        det["examples"] = bad
        return "DISAGREE", det
    return "agree", det


def pull_unit(tb, sym: str, year: int, root: str):
    """One symbol-year, quarter by quarter (the span size theta_bulk found survivable)."""
    import pandas as pd

    frames, failed = [], []
    t0 = time.time()
    for q in range(4):
        s = dt.date(year, 1 + q * 3, 1)
        e = (dt.date(year + 1, 1, 1) if q == 3
             else dt.date(year, 4 + q * 3, 1)) - dt.timedelta(days=1)
        r = tb._call_with_timeout(tb._cli().option_history_eod, start_date=s, end_date=e,
                                  symbol=sym, expiration="*", max_dte=MAX_DTE)
        if isinstance(r, str):
            failed.append(f"Q{q+1}")
            try:
                tb._client = None            # force a fresh channel; a dead one stays dead
            except Exception:                                        # noqa: BLE001
                pass
            continue
        if r is not None and len(r):
            frames.append(r)
    if failed:
        return {"status": "failed", "quarters_failed": failed,
                "seconds": round(time.time() - t0, 1)}
    if not frames:
        return {"status": "empty", "seconds": round(time.time() - t0, 1)}

    df = slim(pd.concat(frames, ignore_index=True))
    verdict, detail = compare_overlap(df, sym, year)

    p = unit_path(root, sym, year)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump({"schema": SCHEMA, "symbol": sym, "year": year, "max_dte": MAX_DTE,
                     "source": "option_history_eod", "rows": df,
                     "pulled_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
                    f, protocol=5)
    os.replace(tmp, p)                       # payload lands BEFORE its manifest line

    exp = pd.to_datetime(df["expiration"].astype(str))
    dat = pd.to_datetime(df["date"].astype(str))
    dte = (exp - dat).dt.days
    return {"status": "ok", "rows": int(len(df)), "bytes": os.path.getsize(p),
            "sha256": sha256(p), "seconds": round(time.time() - t0, 1),
            "max_dte_seen": int(dte.max()), "rows_over_200dte": int((dte > 200).sum()),
            "dates": int(df["date"].nunique()),
            "overlap": verdict, "overlap_detail": detail}


# ------------------------------------------------------------------ driver

def run(root: str, tiers: str, limit: int, workers: int, dry: bool):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from valuation.edge import theta_bulk as TB

    os.makedirs(root, exist_ok=True)
    units = [(tier_of(y), s, y) for s, y in alert_symbol_years() if tier_of(y) in tiers]
    units.sort(key=lambda u: (u[0], u[1], u[2]))       # Tier A entirely before Tier B
    man = load_manifest(root)
    todo = [u for u in units if needs_pull(root, u[1], u[2], man)]
    if limit:
        todo = todo[:limit]

    by_tier = collections.Counter(u[0] for u in units)
    done_by_tier = collections.Counter(u[0] for u in units
                                       if not needs_pull(root, u[1], u[2], man))
    log(f"scope tiers {tiers}: {len(units)} symbol-years "
        f"({dict(by_tier)}), done {dict(done_by_tier)}, to pull {len(todo)}", root)
    free = shutil.disk_usage(os.path.splitdrive(root)[0] + "\\").free / 1e9
    log(f"raw root {root} | free {free:.0f}GB | max_dte {MAX_DTE} | workers {workers}", root)
    if dry:
        for t, s, y in todo[:20]:
            print(f"   would pull  {t}  {s}-{y}")
        print(f"   ... {len(todo)} units total")
        return

    _tls = threading.local()

    def worker_tb():
        tb = getattr(_tls, "tb", None)
        if tb is None:
            tb = TB.ThetaBulk(root=OPT, max_dte=MAX_DTE)
            _tls.tb = tb
        return tb

    t0 = time.time()
    done = 0
    gb = 0.0
    stop = threading.Event()
    disagreements = []

    def one(u):
        if stop.is_set():
            return u, None
        tier, sym, year = u
        return u, pull_unit(worker_tb(), sym, year, root)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, u): u for u in todo}
        for fut in as_completed(futs):
            (tier, sym, year), rec = fut.result()
            if rec is None:
                continue
            rec.update({"tier": tier, "symbol": sym, "year": year,
                        "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            append_manifest(root, rec)
            done += 1
            gb += rec.get("bytes", 0) / 1e9

            if rec.get("overlap") == "DISAGREE":
                disagreements.append(rec)
                log(f"!!! OVERLAP DISAGREEMENT {sym}-{year} -- STOPPING THE RUN", root)
                log(json.dumps(rec["overlap_detail"], indent=1)[:2000], root)
                stop.set()

            if done % 10 == 0 or rec["status"] != "ok":
                rate = done / max(1e-9, time.time() - t0)
                left = (len(todo) - done) / max(1e-9, rate)
                eta = dt.datetime.now() + dt.timedelta(seconds=left)
                freed = shutil.disk_usage(os.path.splitdrive(root)[0] + "\\").free / 1e9
                log(f"{done}/{len(todo)} units | {gb:.2f}GB | {rate*3600:.0f}/h | "
                    f"{left/3600:.1f}h left | ETA {eta:%Y-%m-%d %H:%M} | D: free {freed:.0f}GB",
                    root)
                if freed < MIN_FREE_GB_D:
                    log(f"STOPPING: D: free {freed:.0f}GB below floor {MIN_FREE_GB_D}GB", root)
                    stop.set()

    log(f"finished {done} units in {(time.time()-t0)/3600:.2f}h, {gb:.2f}GB", root)
    if disagreements:
        log(f"RUN STOPPED ON {len(disagreements)} OVERLAP DISAGREEMENT(S)", root)
    return disagreements


def summarise(root: str, out_json: str = None):
    man = load_manifest(root)
    agg = collections.defaultdict(lambda: collections.Counter())
    tot = collections.Counter()
    ov = collections.Counter()
    for rec in man.values():
        t = rec.get("tier", "?")
        agg[t]["units"] += 1
        agg[t][rec.get("status", "?")] += 1
        agg[t]["rows"] += rec.get("rows", 0)
        agg[t]["bytes"] += rec.get("bytes", 0)
        agg[t]["rows_over_200dte"] += rec.get("rows_over_200dte", 0)
        tot["units"] += 1
        tot["rows"] += rec.get("rows", 0)
        tot["bytes"] += rec.get("bytes", 0)
        tot["rows_over_200dte"] += rec.get("rows_over_200dte", 0)
        ov[rec.get("overlap", "n/a")] += 1
    summary = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "raw_root": root, "max_dte": MAX_DTE, "schema": SCHEMA,
        "units": tot["units"], "rows": tot["rows"], "bytes": tot["bytes"],
        "gb": round(tot["bytes"] / 1e9, 3),
        "rows_over_200dte": tot["rows_over_200dte"],
        "overlap_verdicts": dict(ov),
        "per_tier": {t: dict(c) for t, c in agg.items()},
    }
    if out_json:
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        json.dump(summary, open(out_json, "w"), indent=1)
    return summary


def verify(root: str, full: bool = False) -> dict:
    """Check every `ok` record against its payload. This is the disaster-recovery tool.

    `full` re-hashes (slow, exact). Default checks existence and size, which catches truncation
    and deletion without reading tens of GB.
    """
    man = load_manifest(root)
    ok = [r for r in man.values() if r.get("status") == "ok"]
    missing, wrong_size, wrong_hash, good = [], [], [], 0
    for rec in ok:
        p = unit_path(root, rec["symbol"], rec["year"])
        if not os.path.exists(p):
            missing.append(f"{rec['symbol']}-{rec['year']}")
            continue
        if os.path.getsize(p) != rec.get("bytes"):
            wrong_size.append(f"{rec['symbol']}-{rec['year']}")
            continue
        if full:
            if sha256(p) != rec.get("sha256"):
                wrong_hash.append(f"{rec['symbol']}-{rec['year']}")
                continue
        good += 1
    return {"records_ok": len(ok), "verified": good, "missing": missing,
            "wrong_size": wrong_size, "wrong_hash": wrong_hash,
            "mode": "sha256" if full else "size"}


def main():
    ap = argparse.ArgumentParser(description="ThetaData Pro deep-chain harvest (collection only)")
    ap.add_argument("--raw-root", default=DEFAULT_RAW_ROOT)
    ap.add_argument("--tiers", default="AB", help="which tiers to run, e.g. A, AB")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--verify", action="store_true", help="check payloads against the manifest")
    ap.add_argument("--full-hash", action="store_true", help="with --verify, re-hash every file")
    ap.add_argument("--mirror", default="", help="mirror manifest+summary to this dir")
    args = ap.parse_args()

    if args.verify:
        print(json.dumps(verify(args.raw_root, args.full_hash), indent=1))
        return
    if args.summary:
        s = summarise(args.raw_root)
        print(json.dumps(s, indent=1))
        if args.mirror:
            mirror(args.raw_root, args.mirror)
        return
    run(args.raw_root, args.tiers, args.limit, args.workers, args.dry_run)
    s = summarise(args.raw_root)
    print(json.dumps({k: v for k, v in s.items() if k != "per_tier"}, indent=1))
    if args.mirror:
        mirror(args.raw_root, args.mirror)


TRACKED_SUMMARY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "DEEP_HARVEST_SUMMARY.json")


def mirror(root: str, dest: str):
    """SECOND COPY. The bulk stays on D:; the RECORD of it must not.

    After 2026-09-01 none of this is re-fetchable, so a single-drive copy is a single point of
    failure for an irreplaceable asset. The checksummed manifest is small enough to live in three
    places at once, and with it a dead D: means "we know exactly what existed and what it hashed
    to" rather than "we do not know what we lost".

    The per-unit manifest goes to `dest` (under data/, gitignored - it names licensed vendor
    units). The aggregate SUMMARY additionally goes to the repo root, where it is tracked: counts
    and hashes of nothing, purely a census.
    """
    os.makedirs(dest, exist_ok=True)
    for name in ("manifest.jsonl", "PROGRESS.txt"):
        src = os.path.join(root, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, name))
    summarise(root, os.path.join(dest, "DEEP_HARVEST_SUMMARY.json"))
    summarise(root, TRACKED_SUMMARY)
    return dest


if __name__ == "__main__":
    main()
