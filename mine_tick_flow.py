"""
O14 — tick-level option FLOW for the banked alert days only. COLLECTION ONLY, no analysis.

Pure data-pull, in the same shape as `mine_options_cache.py`: skip-existing, never-destroy,
tri-state units, manifest written as work completes, coverage report at the end. Nothing here
computes a statistic, scores a signal, or reaches a verdict — that is a later, pre-registered
options-bot job (roadmap O14's analysis half). This file only puts bytes on disk.

--------------------------------------------------------------------------------------------
THE UNIT OF WORK IS A SYMBOL-DAY FROM THE BANKED BOOK, NOT A CALENDAR.

The alert days come from the R2-corrected book (`data/options_universe/state_r2_corrected.pkl`,
3,885 rows) as unique `(ticker, alert_ts)` pairs — measured, exactly 3,885 of them across 186
names and 1,574 distinct dates, 2016-01-19 to 2025-10-15. Mining the whole calendar for those
names instead would be ~186 x 2,460 trading days = 457,000 day-pulls for the same 3,885 that any
alert-day question can use: two orders of magnitude more data, more disk and more feed time to
answer nothing extra.

The book is READ, never written. The chain freeze is not touched. This is a NEW directory.

--------------------------------------------------------------------------------------------
WHY `option_history_trade_quote` AND NOT `option_history_trade`.

Flow questions are about the AGGRESSOR: was a print lifting the offer or hitting the bid? A trade
tape alone cannot answer that — it carries price and size but no reference market, so every
classification scheme (tick rule, Lee-Ready) has to guess. `option_history_trade_quote` returns
the prevailing NBBO alongside each print, which makes the side a measurement rather than an
inference. It costs no extra call and the account's Standard tier serves it (verified before
anything was built: CSCO 2023-05-08, whole chain, 3,951 prints in 0.5s).

One measured caveat, recorded because it will matter to whoever does the analysis and would be
easy to mistake for a defect: `quote_timestamp` can lag `trade_timestamp` by hours on contracts
whose quote had not updated since the morning. That is the true prevailing quote, not a
mis-join — but a side-classification that ignores quote staleness will mis-label those prints.
Staleness is left in the data; it is not this lane's job to decide what to do about it.

--------------------------------------------------------------------------------------------
NO DTE CEILING, AND THAT WAS MEASURED RATHER THAN ASSUMED.

The EOD cache is mined at max_dte=200 (audit O15), so mirroring it here was the obvious default.
Measured cost of the cap on the two ends of the size distribution:

    NVDA 2025-01-06 (largest alert-day in the book)  594,016 rows capped -> 617,458 uncapped
    CSCO 2023-05-08 (near the median)                  3,951 rows capped ->   4,757 uncapped

+3.9% and +20% of rows, and wall-clock is unchanged (the call is dominated by the server-side
scan, not the payload — the same finding that made `strike_range` not worth using in the EOD
miner). So the cap buys nothing and would have written a silent completeness bias into a cache
whose whole purpose is a later put/call and unusual-volume study. Uncapped it is, and the
ceiling actually used is recorded INSIDE every payload so a future run at a different setting
cannot be confused with this one — the failure the EOD cache needed `.dte` sidecars to prevent.

--------------------------------------------------------------------------------------------
TRI-STATE UNITS. A symbol-day lands in exactly one of three states, and the distinction between
the second and third is the one that has bitten this project repeatedly:

    <SYM>-<YYYY-MM-DD>.pkl          data. COVERED, never refetched.
    <SYM>-<YYYY-MM-DD>.pkl.empty    the feed genuinely returned nothing. COVERED, never
                                    refetched. Flagged in the coverage report anyway, because a
                                    liquid name with zero prints on an alert day is more likely
                                    a bad date than a quiet tape.
    <SYM>-<YYYY-MM-DD>.pkl.missing  the fetch FAILED. Counted as a GAP and RETRIED next run.

`.missing` must never be sticky: `needs_pull` treats it as work still to do. The EOD miner lost
AAPL 2026 permanently to a sticky marker, and that is the bug this shape exists to prevent.

NEVER-DESTROY. Every payload is written to a temp file and `os.replace`d into position, so a
kill mid-write cannot leave a truncated file that later loads as short data. Nothing in this
file deletes a `.pkl`. The only unlink is of a `.missing` marker immediately before its retry.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import shutil
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = r"C:\Users\donni\Downloads\valuation-tool"
TICKROOT = os.path.join(REPO, "data", "options_ticks")
BOOK = os.path.join(REPO, "data", "options_universe", "state_r2_corrected.pkl")

# Load .env from the MAIN checkout. `valuation.config` searches the CWD, which is the worktree
# when this runs from one, so the key is invisible and the miner exits claiming no API key.
try:
    for _line in open(os.path.join(REPO, ".env"), encoding="utf-8", errors="replace"):
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
except OSError:
    pass

MANIFEST = os.path.join(TICKROOT, "tick_manifest.json")
PROGRESS = os.path.join(TICKROOT, "TICK_PROGRESS.txt")
COVERAGE = os.path.join(TICKROOT, "TICK_COVERAGE.json")

# 2 = `alias_used` is ALWAYS present (None when the name supplied its own rows). Under schema 1
# the key was absent on units written before alias support, so its absence meant either "no
# alias" or "written before the field existed" — the same indistinguishable-on-disk defect the
# `dte_cap` field exists to prevent. The cache was migrated rather than left ambiguous.
SCHEMA_VERSION = 2
DTE_CAP = None                  # None = full chain. See the header; this was measured.
MIN_FREE_GB = 40                # same floor the EOD miner uses; an unattended job must not fill C:

# TWO WORKERS, NOT FOUR, AND A LONGER DEADLINE. BOTH MEASURED, AND THE FIRST RUN FAILED WITHOUT
# THEM. The EOD miner uses 4 because ThetaData Standard permits 4 concurrent requests — but
# permitted is not useful. These calls are 10-100x heavier than an EOD call (AAPL 2020 returns
# ~230k print-rows for ONE day), and the account's bandwidth is what binds:
#
#   workers=1   8/8 ok   266s wall   median 29.8s/call   1.8 units/min
#   workers=2   8/8 ok   193s wall   median 42.5s/call   2.5 units/min   <- best
#   workers=4   8/8 ok   247s wall   median 120.1s/call  1.9 units/min
#
# Per-call latency rises almost linearly with workers while THROUGHPUT stays flat, i.e. the
# server serialises the account. So concurrency buys nothing and costs latency — and at 4
# workers the median call (120s) sits past `theta_bulk.CALL_TIMEOUT` (75s), so calls that were
# progressing normally were abandoned as timeouts. That is what produced 18 `.missing` AAPL
# units on the first attempt, at 150s of wasted wall-clock each.
#
# The failure then FED ITSELF, which is the part worth remembering: an abandoned call counts as
# a fault, six faults rebuild the gRPC client, and the client is SHARED across the pool — so one
# slow thread's timeout tore down the channel underneath three healthy in-flight calls, making
# more faults. Standalone, the very unit that "timed out" returns 231,537 rows in 12.7s.
#
# THEN TWO WORKERS FAILED TOO, ON THE BIGGEST UNITS, AND THAT IS WHY THIS IS 1. Retrying the 18
# failed units at workers=2 recovered only 8; the other 10 died with gRPC
# `_MultiThreadedRendezvous` — a channel kill, not a timeout. The 8-unit probe above had not
# caught it because it did not contain the true giants: AAPL's 2020-21 alert-days return
# 340,811-667,796 print-rows EACH (the retail options boom), against ~231k in 2024. Two such
# streams overlapping exceed what the account is served concurrently and the server drops one.
# All three of those units then succeeded SERIALLY on a fresh channel, first try, 20.7-45.1s.
#
# Since throughput is flat in workers anyway, serial costs almost nothing and buys certainty —
# and with the deadline now at 300s a failed unit costs 600s, so reliability IS the throughput
# argument. Measured serial cost is ~1.0-1.3 s per MB of output.
WORKERS = 1
CALL_DEADLINE_S = 300           # vs theta_bulk's 75s. Headroom for a 4MB-payload day at 2 workers.


_manifest_lock = threading.Lock()
_log_lock = threading.Lock()


def log(msg):
    line = f"[ticks] {msg}"
    with _log_lock:
        print(line, flush=True)
        try:
            os.makedirs(TICKROOT, exist_ok=True)
            with open(PROGRESS, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


# ------------------------------------------------------------------ units

def alert_days(book_path: str = BOOK) -> list:
    """Unique (symbol, ISO date) alert-days from the banked book. Read-only."""
    with open(book_path, "rb") as f:
        state = pickle.load(f)
    pairs = {(str(r["ticker"]).upper(), str(r["alert_ts"])[:10]) for r in state["rows"]}
    return sorted(pairs)


def unit_path(sym: str, day: str, root: str = TICKROOT) -> str:
    return os.path.join(root, sym, f"{sym}-{day}.pkl")


def needs_pull(sym: str, day: str, root: str = TICKROOT) -> bool:
    """The ONE place that decides whether a unit is still owed.

    Both `.pkl` and `.empty` are COVERED. `.missing` is a gap and must NOT short-circuit, or a
    single transient failure becomes a permanent hole — the EOD cache's sticky-marker bug.
    """
    p = unit_path(sym, day, root)
    return not (os.path.exists(p) or os.path.exists(p + ".empty"))


# ------------------------------------------------------------------ slimming

def slim(df, day: str):
    """Downcast in place. LOSSLESS BY CONSTRUCTION — every narrowing is range-checked first.

    No column is dropped. This is a collection lane: a column dropped here cannot be recovered
    without re-paying the whole pull, while a column kept costs bytes that were measured and
    found small. `symbol` is the one exception — it is constant within a unit and lives in the
    payload header instead.

    A value that does not fit the narrow type keeps its wide type and is NAMED in the returned
    notes, so an unexpected range is a recorded fact rather than a silent overflow.
    """
    import numpy as np
    import pandas as pd

    notes = {}
    df = df.drop(columns=[c for c in ("symbol",) if c in df.columns])

    def fit(col, target, lo, hi):
        if col not in df.columns:
            return
        s = pd.to_numeric(df[col], errors="coerce")
        if s.isna().any():
            notes.setdefault("nulls", []).append(col)
            return
        if len(s) and (s.min() < lo or s.max() > hi):
            notes.setdefault("kept_wide", []).append(
                f"{col}[{int(s.min())},{int(s.max())}]")
            return
        df[col] = s.astype(target)

    for c in ("condition", "ext_condition1", "ext_condition2", "ext_condition3",
              "ext_condition4", "exchange", "bid_exchange", "ask_exchange",
              "bid_condition", "ask_condition"):
        fit(c, "uint8", 0, 255)
    for c in ("size", "bid_size", "ask_size"):
        fit(c, "int32", -2_147_483_648, 2_147_483_647)
    fit("sequence", "int32", -2_147_483_648, 2_147_483_647)
    for c in ("strike", "price", "bid", "ask"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    if "right" in df.columns:
        df["right"] = df["right"].astype(str).str[0].str.upper().astype("category")
    if "expiration" in df.columns:
        df["expiration"] = pd.to_datetime(df["expiration"]).astype("datetime64[ns]")
    return df.reset_index(drop=True), notes


# ------------------------------------------------------------------ the pull

def pull_unit(tb, cli, sym: str, day: str, root: str = TICKROOT) -> dict:
    """Fetch ONE symbol-day. Returns a manifest record. Writes atomically or not at all."""
    path = unit_path(sym, day, root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = dt.date.fromisoformat(day)

    # Clear a previous failure marker so the retry is real. This is the only unlink in the file
    # and it removes a marker, never data.
    try:
        if os.path.exists(path + ".missing"):
            os.remove(path + ".missing")
    except OSError:
        pass

    # TICKER RENAMES. Options are stored under the symbol as it was AT THE TIME, so `META`
    # returns nothing before June 2022 and `RTX` nothing before April 2020 — the rows are under
    # `FB` and `UTX`. Calling the endpoint directly bypassed `theta_bulk`'s alias handling, and
    # that is exactly what produced 31 of this cache's first 32 `.empty` units (21 META, 10 RTX),
    # every one of them dated before its own rename.
    #
    # THE ORDER IS LOAD-BearING, and it is copied from `_fetch_span_once` rather than invented:
    # the CURRENT symbol is always tried FIRST, so a fallback can only ever fill a span the name
    # itself has nothing for. That is what keeps an alias safe across years in which the old
    # ticker belonged to an unrelated live company.
    from valuation.edge.theta_bulk import ALIASES

    t0 = time.time()
    r, used = None, None
    for cand in [sym] + list(ALIASES.get(sym, [])):
        kw = dict(symbol=cand, expiration="*", start_date=d, end_date=d)
        if DTE_CAP is not None:
            kw["max_dte"] = DTE_CAP
        r = tb._call_with_timeout(cli.option_history_trade_quote, **kw)
        if isinstance(r, str):                   # a fault: stop, do not mask it as an absence
            break
        if r is not None and len(r):
            used = cand
            break
    elapsed = round(time.time() - t0, 2)

    if isinstance(r, str):                       # "FAILED" — a fault, retryable
        # Force a fresh channel for the NEXT unit rather than waiting for theta_bulk's
        # six-consecutive-faults rule. Once this feed's channel goes bad it stays bad — the
        # documented signature is a contiguous run of names failing while the feed is healthy —
        # and at a 300s deadline a failed unit costs 600s against a rebuild's ~1s. Cheap
        # insurance, and it makes a single transient fault self-healing.
        try:
            tb._client = None
        except Exception:                                            # noqa: BLE001
            pass
        _touch(path + ".missing")
        return {"status": "missing", "seconds": elapsed}
    if r is None or len(r) == 0:                 # genuinely no prints
        _touch(path + ".empty")
        return {"status": "empty", "seconds": elapsed}

    frame, notes = slim(r, day)
    payload = {"schema": SCHEMA_VERSION, "symbol": sym, "date": day,
               "dte_cap": DTE_CAP, "source": "option_history_trade_quote",
               # Provenance, on disk rather than re-derived later: when an alias supplied the
               # rows, "these are not this ticker's own rows" is a recorded fact. The EOD cache
               # needed a `.alias` sidecar for this; a self-describing payload cannot be
               # separated from its own provenance.
               "alias_used": (used if used and used != sym else None),
               "pulled_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "rows": frame}
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(payload, f, protocol=5)
    os.replace(tmp, path)                        # atomic: never a truncated .pkl on disk

    rec = {"status": "ok", "prints": int(len(frame)), "bytes": os.path.getsize(path),
           "seconds": elapsed,
           **({"alias_used": used} if used and used != sym else {}),
           "contracts": int(frame.groupby(["expiration", "strike", "right"],
                                          observed=True).ngroups) if len(frame) else 0,
           "volume": int(frame["size"].sum()) if "size" in frame.columns else None}
    if notes:
        rec["dtype_notes"] = notes
    return rec


def _touch(p):
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    except OSError:
        pass


def _save(manifest):
    with _manifest_lock:
        try:
            os.makedirs(TICKROOT, exist_ok=True)
            tmp = MANIFEST + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=0, sort_keys=True)
            os.replace(tmp, MANIFEST)
        except OSError:
            pass


def load_manifest() -> dict:
    if os.path.exists(MANIFEST):
        try:
            return json.load(open(MANIFEST, encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


# ------------------------------------------------------------------ coverage

def _prints_from_payload(path: str) -> int:
    """Read a payload's row count. Used only where the manifest has no record."""
    try:
        with open(path, "rb") as f:
            return int(len(pickle.load(f)["rows"]))
    except Exception:                                                # noqa: BLE001
        return 0


def coverage_report(units, root: str = TICKROOT) -> dict:
    """Descriptive census of what is on disk. Computes no statistic about the DATA.

    THE PAYLOADS ARE THE AUTHORITY, NOT THE MANIFEST. The manifest is written every 25 units, so
    a kill between saves leaves units whose FILE exists and whose RECORD does not — and an
    earlier version of this function took existence from the filesystem and counts from the
    manifest, which silently counted those units' prints as zero. Measured: 67,523 prints missing
    across the units the first (killed) run had written. Where a record is absent the payload is
    read instead, so the census is exact rather than merely plausible.
    """
    man = load_manifest()
    have = miss = empty = owed = 0
    prints = vol = byts = 0
    per_year, per_symbol, empties, missings = {}, {}, [], []
    for sym, day in units:
        p = unit_path(sym, day, root)
        yr = day[:4]
        y = per_year.setdefault(yr, {"units": 0, "ok": 0, "empty": 0, "missing": 0,
                                     "owed": 0, "prints": 0, "bytes": 0})
        s = per_symbol.setdefault(sym, {"units": 0, "ok": 0, "empty": 0, "missing": 0,
                                        "owed": 0, "prints": 0, "bytes": 0})
        y["units"] += 1
        s["units"] += 1
        rec = man.get(f"{sym}|{day}", {})
        if os.path.exists(p):
            have += 1
            y["ok"] += 1
            s["ok"] += 1
            b = os.path.getsize(p)
            byts += b
            y["bytes"] += b
            s["bytes"] += b
            pr = int(rec["prints"]) if rec.get("prints") is not None \
                else _prints_from_payload(p)
            prints += pr
            vol += int(rec.get("volume") or 0)
            y["prints"] += pr
            s["prints"] += pr
        elif os.path.exists(p + ".empty"):
            empty += 1
            y["empty"] += 1
            s["empty"] += 1
            empties.append(f"{sym}|{day}")
        elif os.path.exists(p + ".missing"):
            miss += 1
            y["missing"] += 1
            s["missing"] += 1
            missings.append(f"{sym}|{day}")
        else:
            owed += 1
            y["owed"] += 1
            s["owed"] += 1
    return {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "source_endpoint": "option_history_trade_quote",
        "dte_cap": DTE_CAP,
        "book": "state_r2_corrected.pkl",
        "units_total": len(units),
        "units_with_data": have,
        "units_empty": empty,
        "units_missing": miss,
        "units_not_attempted": owed,
        "coverage_frac": round((have + empty) / len(units), 4) if units else 0.0,
        "prints": prints,
        "contracts_traded": vol,
        "bytes_on_disk": byts,
        "gb_on_disk": round(byts / 1e9, 3),
        "symbols": len({s for s, _ in units}),
        "dates": len({d for _, d in units}),
        "date_range": [min(d for _, d in units), max(d for _, d in units)] if units else [],
        "per_year": per_year,
        "per_symbol": per_symbol,
        "empty_units": sorted(empties),
        "missing_units": sorted(missings),
    }


# The tracked copy. `data/` is NEVER committed (licensed exports), so the full per-unit manifest
# stays in the cache and this census — counts and bytes only, no market data — is what goes into
# the repo, the same way GREEKS_COVERAGE.json carries the derived layer's census.
TRACKED_COVERAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "TICK_FLOW_COVERAGE.json")


# ------------------------------------------------------------------ driver

_tls = threading.local()


def _worker_client():
    """A ThetaBulk (and gRPC channel) PER THREAD, not one shared across the pool.

    `theta_bulk._note_fault` rebuilds the client after six consecutive faults, and with a shared
    instance that teardown lands underneath whatever the other threads are doing — one slow
    thread's timeout becomes everyone's failure. Per-thread channels make a fault local to the
    thread that earned it.

    THE CLIENT IS RE-FETCHED EVERY CALL, AND CACHING IT WAS A REAL BUG THAT BURNED 141 UNITS.
    `_note_fault` recovers a dead gRPC channel by setting `self._client = None` so that the NEXT
    `_cli()` rebuilds it. An earlier version of this function cached the client object once and
    handed the same one back forever, so the rebuild happened inside ThetaBulk while this worker
    went on calling a bound method of the DEAD client. The result is the failure theta_bulk's own
    docstring records — a contiguous block of names failing with `_MultiThreadedRendezvous` while
    the feed itself is fine (here: GS, GSK, then HD/HLT/HON/HOOD/HWM/IBM/INTC/ISRG). Holding the
    ThetaBulk is right; holding its client defeats the only recovery path there is.
    """
    tb = getattr(_tls, "tb", None)
    if tb is None:
        from valuation.edge.theta_bulk import ThetaBulk
        tb = ThetaBulk(root=os.path.join(REPO, "data", "options"))
        _tls.tb = tb
    return tb, tb._cli()


def run(units, workers: int = WORKERS, label: str = "run") -> dict:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from valuation.edge import theta_bulk as TB

    # Widen the call deadline for THIS process only. theta_bulk's 75s is tuned for EOD calls;
    # a tick-day is far heavier and a call that is progressing normally must not be abandoned.
    # Patched here rather than in theta_bulk because that file belongs to the miner lane and the
    # EOD deadline is correct for its own job.
    TB.CALL_TIMEOUT = CALL_DEADLINE_S

    probe = TB.ThetaBulk(root=os.path.join(REPO, "data", "options"))
    if not probe.status()["available"]:
        log(f"ThetaData unavailable: {probe.status()['reason']}")
        return {}

    manifest = load_manifest()
    todo = [(s, d) for s, d in units if needs_pull(s, d)]
    log(f"{label}: {len(units)} units in scope, {len(units) - len(todo)} already covered, "
        f"{len(todo)} to pull, {workers} workers, {CALL_DEADLINE_S}s deadline, "
        f"free disk {shutil.disk_usage('C:/').free / 1e9:.0f}GB")
    if not todo:
        return manifest

    t0 = time.time()
    done = 0
    stop = threading.Event()

    def one(unit):
        sym, day = unit
        if stop.is_set():
            return unit, None
        tb, cli = _worker_client()
        return unit, pull_unit(tb, cli, sym, day)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, u): u for u in todo}
        for fut in as_completed(futs):
            (sym, day), rec = fut.result()
            if rec is None:
                continue
            with _manifest_lock:
                manifest[f"{sym}|{day}"] = rec
            done += 1
            if done % 25 == 0 or rec["status"] != "ok":
                _save(manifest)
            if done % 50 == 0 or done == len(todo):
                free = shutil.disk_usage("C:/").free / 1e9
                rate = done / max(1e-9, time.time() - t0)
                log(f"{label}: {done}/{len(todo)} units | {rate*60:.0f}/min | "
                    f"{(len(todo)-done)/max(1e-9,rate)/60:.0f}m left | free {free:.0f}GB")
                if free < MIN_FREE_GB:
                    log(f"STOPPING: only {free:.0f}GB free (floor {MIN_FREE_GB}GB). "
                        f"Cache intact; re-run resumes.")
                    stop.set()
    _save(manifest)
    log(f"{label}: finished {done} units in {(time.time()-t0)/60:.1f}m")
    return manifest


def main():
    ap = argparse.ArgumentParser(description="O14 tick-flow collection (alert days only)")
    ap.add_argument("--sample", type=int, default=0,
                    help="pull only N units, stratified across the chain-volume distribution")
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--sizes", default="",
                    help="JSON of per-alert-day chain sizes, for the stratified sample")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    units = alert_days()
    os.makedirs(TICKROOT, exist_ok=True)

    if args.report_only:
        cov = coverage_report(units)
        json.dump(cov, open(COVERAGE, "w"), indent=1)
        # The TRACKED copy is refreshed here too. It used to be written only at the end of a real
        # pull, so any repair done afterwards (the alias re-pull, the schema migration) left the
        # committed artifact describing a cache that no longer existed — a census that silently
        # goes stale is worse than no census.
        json.dump(cov, open(TRACKED_COVERAGE, "w"), indent=1)
        log(json.dumps({k: v for k, v in cov.items()
                        if k not in ("per_year", "per_symbol", "empty_units",
                                     "missing_units")}, indent=1))
        return

    scope = units
    if args.sample:
        scope = stratified_sample(units, args.sample, args.sizes)
        log(f"stratified sample: {len(scope)} units")

    run(scope, workers=args.workers, label=f"sample{args.sample}" if args.sample else "full")

    cov = coverage_report(units)
    json.dump(cov, open(COVERAGE, "w"), indent=1)
    json.dump(cov, open(TRACKED_COVERAGE, "w"), indent=1)
    log(f"coverage: {cov['units_with_data']} with data, {cov['units_empty']} empty, "
        f"{cov['units_missing']} missing, {cov['units_not_attempted']} not attempted, "
        f"{cov['gb_on_disk']}GB")


def stratified_sample(units, n: int, sizes_path: str) -> list:
    """N units spanning the chain-volume distribution, deterministically.

    A uniform random sample is the wrong instrument here: the top 5% of alert-days carry 50.2%
    of all contract volume, so a random 20 would miss the tail that dominates the total and the
    projection built on it would be confidently wrong. Equal-COUNT strata by volume, taking the
    median-volume unit of each, spans the range and needs no seed to reproduce.
    """
    if not sizes_path or not os.path.exists(sizes_path):
        return units[:n]
    per = json.load(open(sizes_path, encoding="utf-8"))["per_day"]
    ranked = sorted(units, key=lambda u: per.get(f"{u[0]}|{u[1]}", {}).get("chain_volume", 0))
    out, step = [], len(ranked) / n
    for i in range(n):
        lo, hi = int(i * step), int((i + 1) * step)
        block = ranked[lo:max(hi, lo + 1)]
        out.append(block[len(block) // 2])
    return out


if __name__ == "__main__":
    main()
