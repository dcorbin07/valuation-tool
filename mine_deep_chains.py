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


# ------------------------------------------------------------------ Tier C

TIER_C_YEARS = (2016, 2017, 2018)
PANEL = os.path.join(REPO, "data", "free_analysis", "panel_s22_h504.pkl")


def _attempted(sym: str, year: int) -> str:
    """Has this symbol-year EVER been attempted, and with what outcome?

    The breadth cache is tri-state -- `.pkl` (payload), `.pkl.empty` (the vendor served
    nothing), `.pkl.missing` (the vendor refused) -- so "never tried" is the absence of all
    three, and is a MINING SCOPE fact rather than a statement about the data.
    """
    d = os.path.join(OPT, sym)
    base = f"{sym}-{year}.pkl"
    if os.path.exists(os.path.join(d, base)):
        return "payload"
    for ext in (".empty", ".missing"):
        if os.path.exists(os.path.join(d, base + ext)):
            return "empty" if ext == ".empty" else "missing"
    return "never"


def tier_c_units():
    """(units_to_pull, skipped) for the optionable universe's 2016-2018 hole.

    Measured 2026-08-17 by scripts/options_coverage_census.py: of 906 optionable panel names,
    411 hold at least one 2016-2018 unit and 495 hold none. Those 495 split into 420 NEVER
    TRIED (414 have 2024 as their earliest year -- they were simply never in the breadth
    miner's scope) and 75 that WERE tried and came back genuinely empty.

    The 75 are skipped with a reason and NOT re-probed. Re-probing a recorded `.empty` spends
    an irreplaceable subscription window re-confirming a negative the cache already holds.
    """
    import pandas as pd

    panel_names = {str(t) for t in pd.read_pickle(PANEL)["ticker"].unique()}
    cache_dirs = {d for d in os.listdir(OPT) if os.path.isdir(os.path.join(OPT, d))}
    optionable = sorted(cache_dirs & panel_names)

    units, skipped = [], []
    for sym in optionable:
        state = {y: _attempted(sym, y) for y in TIER_C_YEARS}
        if any(v == "payload" for v in state.values()):
            continue                                    # already holds part of the window
        if all(v in ("empty", "missing") for v in state.values()):
            skipped.append({"symbol": sym, "reason": "known_empty_all_three_years",
                            "detail": state})
            continue
        for y in TIER_C_YEARS:
            if state[y] == "never":
                units.append(("C", sym, y))
            else:
                skipped.append({"symbol": sym, "year": y,
                                "reason": f"already_{state[y]}", "detail": None})
    return units, skipped


# ------------------------------------------------------------------ Tier E (tenor depth)

TIER_E_YEARS = (2016, 2017, 2018)


def tier_e_units():
    """(units, skipped) for the tenor axis: shallow 2016-2018 units never pulled at 1200 DTE.

    THIS TIER IS PERISHABLE AND MY OWN HANDOFF SAID IT WAS NOT. Standard's window rolls forward
    from roughly 2018-08-18, so 2016, 2017 and the first half of 2018 stop being reachable the
    day the Pro subscription lapses. "Nothing perishable remains" was true of the DATE axis,
    which Tier C closed, and I carried it across to the tenor axis without re-deriving it. These
    836 units are the last perishable thing in the harvest, so depth runs BEFORE Tier D, which
    stays reachable in perpetuity.

    Disjoint from Tier C by construction: C is the names holding NO 2016-2018 unit, this is the
    names holding one at shallow tenor only.

    SIZED BY PAIRING, not by sampling. 393 symbol-years exist in both stores, giving a measured
    deep/shallow byte ratio -- median 1.43x, mean 1.64x, p90 2.56x -- applied to the candidates'
    3.12 GB of shallow payload: ~5.1 GB expected, 8.0 GB at p90. Wall clock ~5.2 h from this
    harvest's own 995 timed 2016-2018 units (mean 22.6 s). Tier C's projection missed by 4x
    because it was sized on three names; 393 pairs is a different kind of estimate.
    """
    raw_syms = {}
    units = []
    for sym in sorted(os.listdir(OPT)):
        d = os.path.join(OPT, sym)
        if not os.path.isdir(d):
            continue
        for y in TIER_E_YEARS:
            if os.path.exists(os.path.join(d, f"{sym}-{y}.pkl")):
                units.append(("E", sym, y))
    return units, []


# ------------------------------------------------------------------ Tier D

TIER_D_YEARS = (2025, 2026)
INDEX_BOOK = os.path.join(REPO, "data", "valquo_index.json")


def tier_d_units(index_path: str = ""):
    """(units, skipped) for the published Index's names in the recent years.

    SCOPED AT max_dte=1200, NOT AT THE 60-90 DTE BAND IT WAS ASKED FOR, and the reason is
    arithmetic rather than preference. A 1200-DTE pull is a strict SUPERSET of the 60-90 band,
    and sized from this harvest's own record -- 2025 units run a mean of 17.9 MB -- the whole of
    Tier D comes to roughly 3 GB against 383 GB free on D:. Narrowing the band would save a
    couple of gigabytes and buy a SECOND unit namespace for the same symbol-years, which then
    cannot be compared with, or resumed alongside, the 1,865 units already banked at 1200. The
    band is a filter to apply when the data is read; it is not worth a fork in the store.

    Tier D is NOT perishable: 2025-26 sits well inside Standard's rolling 8-year window. It runs
    here only because the Pro subscription is already paid for through 2026-09-01.
    """
    idx = index_path or INDEX_BOOK
    with open(idx, encoding="utf-8") as fh:
        names = sorted({str(p["ticker"]).upper() for p in json.load(fh)["positions"]})
    units, skipped = [], []
    for sym in names:
        for y in TIER_D_YEARS:
            units.append(("D", sym, y))
    return units, skipped


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
    if rec and rec.get("status") in ("empty", "empty_vendor"):
        return False                      # terminal: the vendor has nothing. Do not re-probe.
    if not rec or rec.get("status") not in ("ok", "ok_partial"):
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


_PANEL_FIRST_YEAR = {}


def panel_first_year(sym: str) -> int:
    """First calendar year the panel knows this ticker, cached. A proxy for listing.

    WHY IT IS STAMPED ON EVERY TIER C UNIT. Option chains are keyed by the ticker as traded at
    the time, and tickers get RECYCLED. Probing found RPRX serving 1,320 rows for March 2016
    although RPRX listed in 2020 -- those rows belong to whoever held the symbol then. Tier C
    is precisely the population whose panel membership starts late, so it is the population
    most exposed to reuse.

    This does NOT gate the pull. Collection is not analysis, the bytes are what the vendor
    served, and a unit withheld before 2026-09-01 is unreachable afterwards. What it does is
    make the contamination DETECTABLE: any unit whose year predates its panel debut is stamped
    `pre_panel_history: true` and must be treated as suspect until the alias/reuse scan
    adjudicates it. Silent attribution of another company's chains to a modern name is the
    failure this exists to prevent.
    """
    if not _PANEL_FIRST_YEAR:
        import pandas as pd

        df = pd.read_pickle(PANEL)
        d = pd.to_datetime(df["date"], errors="coerce")
        for sym_, yr in zip(df["ticker"].astype(str), d.dt.year):
            if yr == yr:                                  # not NaN
                cur = _PANEL_FIRST_YEAR.get(sym_)
                if cur is None or yr < cur:
                    _PANEL_FIRST_YEAR[sym_] = int(yr)
    return _PANEL_FIRST_YEAR.get(sym, 0)


UNIT_CALL_TIMEOUT_S = 300


def _bounded(fn, timeout: int = UNIT_CALL_TIMEOUT_S):
    """A deadline that covers CLIENT CONSTRUCTION as well as the RPC. See BUG 3."""
    import concurrent.futures as _cf

    ex = _cf.ThreadPoolExecutor(max_workers=1)
    try:
        return ex.submit(fn).result(timeout=timeout)
    except _cf.TimeoutError:
        return "TIMEOUT"
    except Exception as e:                                           # noqa: BLE001
        return f"ERR:{type(e).__name__}"
    finally:
        ex.shutdown(wait=False)


def pull_unit(tb, sym: str, year: int, root: str):
    """One symbol-year, quarter by quarter (the span size theta_bulk found survivable)."""
    import pandas as pd

    frames, failed, errs, empty_q, future_q = [], [], [], [], []
    t0 = time.time()
    # BUG 9. THE CURRENT YEAR IS NOT A WHOLE YEAR, and asking for the rest of it is not a
    # question the vendor can answer. Tier D pulls 2026 on 2026-08-18: Q4 has not happened, and
    # Q3 is half unwritten. The first two units proved it -- ACGL-2026 and AEIS-2026 both came
    # back `failed` with Q4 NoDataFoundError and Q3 _MultiThreadedRendezvous. `failed` is the
    # damaging part: BUG 7's repair does not catch this because the Q3 error is a gRPC fault
    # rather than NoDataFound, so `nodata_only` is False and the WHOLE unit is refused --
    # throwing away seven and a half months of 2026 that the vendor serves perfectly well, and
    # re-probing it on every restart forever. All 86 of Tier D's 2026 units were on that path.
    #
    # A quarter that has not started yet is SKIPPED, not requested; a quarter in progress is
    # requested only up to the last completed session. Clamped to YESTERDAY rather than today
    # because an EOD bar does not exist until after the close.
    horizon = dt.date.today() - dt.timedelta(days=1)
    for q in range(4):
        s = dt.date(year, 1 + q * 3, 1)
        e = (dt.date(year + 1, 1, 1) if q == 3
             else dt.date(year, 4 + q * 3, 1)) - dt.timedelta(days=1)
        if s > horizon:
            future_q.append(f"Q{q+1}")          # not yet in the past: nothing to ask for
            continue
        e = min(e, horizon)
        # BUG 3, fixed here: `tb._cli()` used to be written as an ARGUMENT to
        # _call_with_timeout, so it was evaluated before the deadline existed. After a fault
        # nulls the client, the next connect is unbounded -- that hung PID 3172 for twelve
        # hours with no output and no error. Submitting a closure puts CONSTRUCTION inside the
        # bound. theta_bulk itself is another lane's file and is not touched.
        r = _bounded(lambda: tb._cli().option_history_eod(
            start_date=s, end_date=e, symbol=sym, expiration="*", max_dte=MAX_DTE))
        if isinstance(r, str):
            failed.append(f"Q{q+1}")
            errs.append(r)
            try:
                tb._client = None            # force a fresh channel; a dead one stays dead
            except Exception:                                        # noqa: BLE001
                pass
            continue
        if r is not None and len(r):
            frames.append(r)
        else:
            # BUG 8. A quarter that returns ZERO ROWS without raising used to be dropped here
            # in silence, so a year missing an entire quarter was banked as `ok` -- complete.
            # Measured on the finished harvest: 19 units carry status `ok` while holding under
            # 95% of their year's date count, and re-probing found the vendor WILL serve the
            # missing span for 15 of them (LLY/LOW/MA 2020, LLY/LMT/LOW 2022, WELL/CBRE 2018,
            # PEN 2016 among others). Recoverable data was sitting behind a label that said
            # there was nothing to recover, which is worse than losing it loudly.
            empty_q.append(f"Q{q+1}")
    nodata_only = bool(errs) and all("NoDataFound" in e for e in errs)
    if failed and (len(failed) == 4 or not frames):
        # "the vendor has nothing here" is a TERMINAL answer, not a transient fault, and the
        # two must not share a status. Tier C is ~22% pre-listing names (ABVX listed 2024, so
        # its 2016-2018 is empty by construction); recording those as `failed` would re-probe
        # every one on every restart, spending an irreplaceable window re-confirming a
        # negative. Mirrors the breadth cache's own `.pkl.empty` convention.
        if nodata_only:
            return {"status": "empty_vendor", "quarters_failed": failed, "errors": errs[:4],
                    "quarters_future": future_q or None,
                    "seconds": round(time.time() - t0, 1)}
        return {"status": "failed", "quarters_failed": failed, "errors": errs[:4],
                "seconds": round(time.time() - t0, 1)}
    if failed and not nodata_only:
        # a REAL fault on some quarter: refuse the unit rather than bank a short year silently
        return {"status": "failed", "quarters_failed": failed, "errors": errs[:4],
                "seconds": round(time.time() - t0, 1)}
    # BUG 7. A name that LISTED MID-YEAR legitimately has no data before its first trade, and
    # `if failed: return` discarded the quarters that DID have data -- 26 Tier C units thrown
    # away, all of them names like LIN, EQH and ARGX whose listing falls inside the window.
    # Tier C is exactly the late-listing population, so this defect is aimed at its own target.
    # A partial year is kept and LABELLED, never silently banked as whole: `quarters_missing`
    # records which quarters returned nothing, so a short year can never be mistaken for a
    # complete one downstream.
    if not frames:
        # A current-year unit with nothing yet is not the same object as a name the vendor
        # has never carried, so it must still say which quarters had not happened.
        return {"status": "empty", "quarters_future": future_q or None,
                "seconds": round(time.time() - t0, 1)}

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
    pfy = panel_first_year(sym)
    # A year short only because it is not OVER is `ok_partial` too, but for a reason that is not
    # a defect and must not read like one: `quarters_future` says the calendar has not caught up,
    # where `quarters_missing` says a request faulted. Conflating them would make a live year
    # look damaged, and would make it re-pull forever.
    return {"status": "ok_partial" if (failed or empty_q or future_q) else "ok",
            "quarters_missing": failed or None,
            "quarters_empty": empty_q or None,
            "quarters_future": future_q or None,
            "pulled_through": horizon.isoformat() if future_q else None,
            "rows": int(len(df)), "bytes": os.path.getsize(p),
            "panel_first_year": pfy,
            "pre_panel_history": bool(pfy and year < pfy),
            "sha256": sha256(p), "seconds": round(time.time() - t0, 1),
            "max_dte_seen": int(dte.max()), "rows_over_200dte": int((dte > 200).sum()),
            "dates": int(df["date"].nunique()),
            "overlap": verdict, "overlap_detail": detail}


SHORT_FRACTION = 0.95


def short_units(root: str) -> list:
    """Banked units holding fewer dates than their year's best-observed count. BUG 8.

    The reference is the MAXIMUM `dates` any unit reports for that year, which is the trading-day
    count the vendor actually served -- derived from the harvest itself rather than from a
    weekday calendar, because a weekday is not a trading day and a hand-written holiday list is
    one more thing to get wrong.

    A short unit is a QUESTION, not a defect: a name that listed in June is legitimately short,
    and so is one the vendor genuinely stops serving. Only re-pulling separates those from the
    ones that were banked short by mistake, so this returns candidates and `repair` adjudicates.
    """
    man = load_manifest(root)
    best = collections.defaultdict(int)
    for rec in man.values():
        if rec.get("dates"):
            best[rec["year"]] = max(best[rec["year"]], rec["dates"])
    out = []
    for rec in man.values():
        if rec.get("status") not in ("ok", "ok_partial") or not rec.get("dates"):
            continue
        ref = best[rec["year"]]
        if ref and rec["dates"] < SHORT_FRACTION * ref:
            out.append({"symbol": rec["symbol"], "year": rec["year"], "tier": rec.get("tier"),
                        "dates": rec["dates"], "year_best": ref, "status": rec["status"],
                        "quarters_missing": rec.get("quarters_missing"),
                        "panel_first_year": rec.get("panel_first_year")})
    return sorted(out, key=lambda r: (r["year"], r["symbol"]))


def relabel(root: str) -> dict:
    """Correct the STATUS of units already banked short. Offline, idempotent, no vendor calls.

    `repair` only writes when a re-pull strictly improves a unit, which is the right rule for
    PAYLOADS and the wrong one for LABELS: 43 units came back confirmed short, so their payloads
    were rightly left alone -- and their manifest records kept saying `ok`, meaning complete.
    That is the BUG 8 defect surviving its own repair.

    The correction needs no subscription. Which quarters a banked payload covers is a property
    of the payload, so this reads the file and marks a unit `ok_partial` with `quarters_empty`
    if any calendar quarter holds no dates at all. Bytes, sha256, rows and dates are copied from
    the existing record unchanged -- the payload is not touched and must not be, so a relabel can
    never be mistaken for a re-pull.
    """
    import pandas as pd

    man = load_manifest(root)
    cands = short_units(root)
    out = {"examined": len(cands), "relabelled": [], "already_correct": 0, "unreadable": []}
    for c in cands:
        sym, year = c["symbol"], c["year"]
        rec = dict(man[f"{sym}|{year}"])
        p = unit_path(root, sym, year)
        try:
            with open(p, "rb") as f:
                df = pickle.load(f)["rows"]
            months = set(pd.to_datetime(df["date"].astype(str)).dt.month)
        except Exception as e:                                       # noqa: BLE001
            out["unreadable"].append({"symbol": sym, "year": year, "error": type(e).__name__})
            continue
        # BUG 9's other half: a quarter that has not happened yet is not an EMPTY quarter. On the
        # current year every remaining quarter would otherwise be relabelled `quarters_empty`,
        # which reads as a data defect and is only the calendar.
        horizon = dt.date.today() - dt.timedelta(days=1)
        empty = [f"Q{q+1}" for q in range(4)
                 if dt.date(year, 1 + q * 3, 1) <= horizon
                 and not months & {1 + q * 3, 2 + q * 3, 3 + q * 3}]
        want_status = "ok_partial" if (empty or rec.get("quarters_missing")
                                       or rec.get("quarters_future")) else "ok"
        if rec.get("status") == want_status and (rec.get("quarters_empty") or None) == (empty or None):
            out["already_correct"] += 1
            continue
        rec.update({"status": want_status, "quarters_empty": empty or None,
                    "relabelled": {"was": rec.get("status"), "reason": "BUG8_offline_relabel"},
                    "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
        append_manifest(root, rec)
        out["relabelled"].append({"symbol": sym, "year": year, "was": c["status"],
                                  "now": want_status, "quarters_empty": empty})
    log(f"relabel: {len(out['relabelled'])} corrected, {out['already_correct']} already correct",
        root)
    return out


def repair(root: str, limit: int = 0, dry: bool = False) -> dict:
    """Re-pull short units and keep the result ONLY if it strictly improves. BUG 8.

    THE RULE THAT MATTERS: a repair may never shrink a unit. The re-pull is written only when it
    holds MORE dates than the banked payload; otherwise the payload is left exactly as it is and
    the unit is recorded `vendor_confirmed_short` -- an answer, not a failure. Without that rule
    a transient vendor hiccup during the repair would silently destroy good data, which is the
    opposite of what a repair is for.
    """
    from valuation.edge import theta_bulk as TB

    cands = short_units(root)
    if limit:
        cands = cands[:limit]
    log(f"repair: {len(cands)} short units to re-probe", root)
    if dry:
        for c in cands:
            print(f"   would repair {c['symbol']}-{c['year']}  {c['dates']}/{c['year_best']}"
                  f"  ({c['status']})")
        return {"candidates": len(cands), "dry_run": True}

    tb = TB.ThetaBulk(root=OPT, max_dte=MAX_DTE)
    out = {"candidates": len(cands), "improved": [], "confirmed_short": [], "failed": []}
    for i, c in enumerate(cands, 1):
        sym, year, before = c["symbol"], c["year"], c["dates"]
        p = unit_path(root, sym, year)
        keep = p + ".prerepair"
        if os.path.exists(p):
            shutil.copy2(p, keep)             # never trust an in-place overwrite with the only copy
        rec = pull_unit(tb, sym, year, root)
        after = rec.get("dates", 0)
        if rec.get("status") in ("ok", "ok_partial") and after > before:
            rec.update({"tier": c["tier"], "symbol": sym, "year": year,
                        "repair": {"dates_before": before, "dates_after": after,
                                   "reason": "BUG8_short_unit"},
                        "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            append_manifest(root, rec)
            os.remove(keep)
            out["improved"].append({"symbol": sym, "year": year, "before": before,
                                    "after": after, "rows": rec.get("rows")})
            log(f"repair {i}/{len(cands)} {sym}-{year}: {before} -> {after} dates", root)
        else:
            if os.path.exists(keep):
                os.replace(keep, p)           # restore byte-for-byte; a repair may not shrink
            note = {"symbol": sym, "year": year, "dates": before,
                    "probe_status": rec.get("status"), "probe_dates": after}
            out["confirmed_short"].append(note)
            log(f"repair {i}/{len(cands)} {sym}-{year}: no improvement "
                f"({rec.get('status')}, {after} dates) -- payload untouched", root)
    log(f"repair done: {len(out['improved'])} improved, "
        f"{len(out['confirmed_short'])} confirmed short", root)
    return out


def adopt_orphans(root: str) -> dict:
    """Re-checkpoint payloads that exist on disk but carry no manifest record.

    WHY THIS IS NEEDED. BUG 5 left 883 payloads (9.90 GB) on disk against 15 manifest records:
    the loop that writes checkpoints died while the executor kept pulling for twelve hours.
    `needs_pull` trusts the manifest, so without this every one of those units would be pulled
    a SECOND time -- roughly twelve hours of an irreplaceable subscription window, spent
    re-fetching bytes already paid for.

    It is deliberately conservative. A payload is adopted ONLY if it unpickles, carries the
    schema this miner writes, and its EMBEDDED symbol/year match its own path. Anything else is
    left alone to be re-pulled, because a wrong manifest record is worse than a missing one --
    it would mark a unit done that nobody has verified. Adopted records are stamped
    `adopted_from_disk: true` so they are never confused with a checkpoint written live.
    """
    man = load_manifest(root)
    base = os.path.join(root, "chains")
    adopted = skipped = 0
    reasons = collections.Counter()
    if not os.path.isdir(base):
        return {"adopted": 0, "skipped": 0}
    for sym in sorted(os.listdir(base)):
        d = os.path.join(base, sym)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".pkl"):
                continue
            try:
                year = int(fn[len(sym) + 1:-4])
            except ValueError:
                reasons["unparseable_name"] += 1
                skipped += 1
                continue
            if f"{sym}|{year}" in man:
                continue                                  # already checkpointed
            p = os.path.join(d, fn)
            try:
                with open(p, "rb") as f:
                    obj = pickle.load(f)
            except Exception as e:                                   # noqa: BLE001
                reasons[f"unreadable_{type(e).__name__}"] += 1
                skipped += 1
                continue
            if (not isinstance(obj, dict) or obj.get("symbol") != sym
                    or obj.get("year") != year or "rows" not in obj):
                reasons["schema_or_identity_mismatch"] += 1
                skipped += 1
                continue
            df = obj["rows"]
            try:
                import pandas as pd

                exp = pd.to_datetime(df["expiration"].astype(str), errors="coerce")
                dat = pd.to_datetime(df["date"].astype(str), errors="coerce")
                dte = (exp - dat).dt.days
                mx = dte.max()
                over = int((dte > 200).sum())
            except Exception:                                        # noqa: BLE001
                mx, over = None, None
            pfy = panel_first_year(sym)
            rec = {"status": "ok", "tier": tier_of(year), "symbol": sym, "year": year,
                   "rows": int(len(df)), "bytes": os.path.getsize(p), "sha256": sha256(p),
                   "max_dte_seen": (int(mx) if mx == mx and mx is not None else None),
                   "rows_over_200dte": over,
                   "dates": int(df["date"].nunique()),
                   "max_dte": obj.get("max_dte"),
                   "pulled_utc": obj.get("pulled_utc"),
                   "panel_first_year": pfy,
                   "pre_panel_history": bool(pfy and year < pfy),
                   "overlap": "not_compared_adopted",
                   "adopted_from_disk": True,
                   "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            append_manifest(root, rec)
            adopted += 1
    out = {"adopted": adopted, "skipped": skipped, "reasons": dict(reasons)}
    log(f"adopt-orphans: {adopted} payloads re-checkpointed, {skipped} skipped {dict(reasons)}",
        root)
    return out


# ------------------------------------------------------------------ driver

def run(root: str, tiers: str, limit: int, workers: int, dry: bool):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from valuation.edge import theta_bulk as TB

    os.makedirs(root, exist_ok=True)
    units = [(tier_of(y), s, y) for s, y in alert_symbol_years() if tier_of(y) in tiers]
    skipped = []
    if "E" in tiers:
        e_units, _ = tier_e_units()
        seen = {(s, y) for _, s, y in units}
        units += [u for u in e_units if (u[1], u[2]) not in seen]
    if "D" in tiers:
        d_units, _ = tier_d_units()
        # A symbol-year already banked by tier A/B/C is the SAME unit at the same max_dte, so it
        # is dropped here rather than re-keyed: needs_pull would skip it anyway, but leaving the
        # duplicate in `units` would double-count the tier's scope in every log line.
        seen = {(s, y) for _, s, y in units}
        units += [u for u in d_units if (u[1], u[2]) not in seen]
    if "C" in tiers:
        c_units, skipped = tier_c_units()
        units += c_units
        with open(os.path.join(root, "tier_c_skipped.json"), "w", encoding="utf-8") as fh:
            json.dump(skipped, fh, indent=1)
        n_empty = sum(1 for s in skipped if s["reason"] == "known_empty_all_three_years")
        log(f"tier C: {len(c_units)} units to pull, {len(skipped)} skipped "
            f"({n_empty} names known-empty in all three years, NOT re-probed) "
            f"-> tier_c_skipped.json", root)
    units.sort(key=lambda u: (u[0], u[1], u[2]))       # Tier A entirely before B, then C
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

    # BUG 5. The previous shape was `for fut in as_completed(futs): fut.result()` with the
    # executor in a `with` block. One unit raising propagated out of the loop, and
    # ThreadPoolExecutor.__exit__ then called shutdown(wait=True) -- which does NOT cancel the
    # ~1,340 already-submitted futures. So the workers kept pulling for TWELVE HOURS while the
    # loop that writes the manifest was dead: 883 payloads landed on disk against 15 manifest
    # records, and killing the process orphaned every one of them. The failure is silent by
    # construction -- no log line, no traceback until exit, and it LOOKS exactly like a hang.
    # A single unit's exception may never again stop the checkpointing of the others.
    ex = ThreadPoolExecutor(max_workers=workers)
    try:
        futs = {ex.submit(one, u): u for u in todo}
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                (tier, sym, year), rec = fut.result()
            except Exception as e:                                   # noqa: BLE001
                tier, sym, year = u
                rec = {"status": "failed", "error": f"{type(e).__name__}: {e}"[:300]}
                log(f"unit {sym}-{year} raised {type(e).__name__}: {e} -- recorded failed, "
                    f"run continues", root)
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

    finally:
        # cancel_futures: a stopped run must not keep pulling in the background
        ex.shutdown(wait=False, cancel_futures=True)

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


def census(root: str, out_md: str = "") -> dict:
    """THE PERMANENT RECORD OF THE HARVEST: what exists, what is unreachable, what was skipped.

    After 2026-09-01 the Pro window is gone and this is the answer to "what did we get, and what
    can never be got". It is deliberately three separate quantities, because collapsing them is
    how a gap gets mistaken for a decision:

      * BANKED     -- units with a payload on disk (`ok` whole years, `ok_partial` short ones).
      * UNREACHABLE -- `empty_vendor`: the feed has nothing, mostly names that had not listed.
                       No future subscription recovers these. NOT the same as "not pulled".
      * SKIPPED    -- never asked, with the reason recorded. A choice, not a fact about the world.

    `ok_partial` is reported separately from `ok` rather than summed into a "units" total, which
    is the BUG 7/BUG 8 lesson made structural: a short year that reads as a whole one is the
    defect this harvest hit twice.
    """
    man = load_manifest(root)
    tiers = collections.defaultdict(lambda: collections.Counter())
    rows = collections.Counter()
    byts = collections.Counter()
    deep = collections.Counter()
    for rec in man.values():
        t = rec.get("tier", "?")
        tiers[t][rec.get("status", "?")] += 1
        rows[t] += rec.get("rows", 0)
        byts[t] += rec.get("bytes", 0)
        deep[t] += rec.get("rows_over_200dte", 0)

    banked = [r for r in man.values() if r.get("status") in ("ok", "ok_partial")]
    out = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "raw_root": root,
        "max_dte": MAX_DTE,
        "per_tier": {t: {"by_status": dict(c), "rows": rows[t], "bytes": byts[t],
                         "rows_over_200dte": deep[t]} for t, c in sorted(tiers.items())},
        "banked_units": len(banked),
        "unreachable_empty_vendor": sum(1 for r in man.values()
                                        if r.get("status") == "empty_vendor"),
        "failed": sum(1 for r in man.values() if r.get("status") == "failed"),
        "total_rows": sum(rows.values()),
        "total_bytes": sum(byts.values()),
        "total_gb": round(sum(byts.values()) / 1e9, 3),
        "rows_over_200dte": sum(deep.values()),
        "short_years_ok_partial": sum(1 for r in banked if r.get("status") == "ok_partial"),
        "units_with_empty_quarters": sum(1 for r in banked if r.get("quarters_empty")),
        "units_with_failed_quarters": sum(1 for r in banked if r.get("quarters_missing")),
        "pre_panel_history_units": sum(1 for r in banked if r.get("pre_panel_history")),
        "pre_panel_history_symbols": sorted({r["symbol"] for r in banked
                                             if r.get("pre_panel_history")}),
        "overlap_verdicts": dict(collections.Counter(r.get("overlap") for r in man.values())),
        "relabelled_units": sum(1 for r in man.values() if r.get("relabelled")),
        "repaired_units": sum(1 for r in man.values() if r.get("repair")),
        "adopted_from_disk": sum(1 for r in man.values() if r.get("adopted_from_disk")),
    }
    for name, path in (("tier_c_skipped", os.path.join(root, "tier_c_skipped.json")),):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                sk = json.load(fh)
            out[name] = {"entries": len(sk),
                         "by_reason": dict(collections.Counter(s["reason"] for s in sk))}
    p = os.path.join(root, "HARVEST_CENSUS.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    if out_md:
        with open(out_md, "w", encoding="utf-8") as fh:
            fh.write("| tier | ok | ok_partial | empty_vendor | failed | rows | GB | rows >200 DTE |\n")
            fh.write("|---|---|---|---|---|---|---|---|\n")
            for t, c in sorted(tiers.items()):
                fh.write(f"| {t} | {c['ok']} | {c['ok_partial']} | {c['empty_vendor']} | "
                         f"{c['failed']} | {rows[t]:,} | {byts[t]/1e9:.2f} | {deep[t]:,} |\n")
    print(json.dumps({k: v for k, v in out.items()
                      if k != "pre_panel_history_symbols"}, indent=1))
    return out


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
    ap.add_argument("--tiers", default="AB", help="which tiers to run, e.g. A, AB, C")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--adopt-orphans", action="store_true",
                    help="re-checkpoint payloads on disk with no manifest record (BUG 5)")
    ap.add_argument("--census", action="store_true",
                    help="the permanent record: banked vs unreachable vs skipped, per tier")
    ap.add_argument("--census-md", default="", help="with --census, also write a markdown table")
    ap.add_argument("--relabel", action="store_true",
                    help="offline: correct ok->ok_partial for units missing a whole quarter")
    ap.add_argument("--repair", action="store_true",
                    help="re-pull units banked short of their year (BUG 8); never shrinks a unit")
    ap.add_argument("--verify", action="store_true", help="check payloads against the manifest")
    ap.add_argument("--full-hash", action="store_true", help="with --verify, re-hash every file")
    ap.add_argument("--mirror", default="", help="mirror manifest+summary to this dir")
    args = ap.parse_args()

    if args.verify:
        print(json.dumps(verify(args.raw_root, args.full_hash), indent=1))
        return
    if args.census:
        census(args.raw_root, args.census_md)
        return
    if args.relabel:
        print(json.dumps(relabel(args.raw_root), indent=1))
        if args.mirror:
            mirror(args.raw_root, args.mirror)
        return
    if args.repair:
        print(json.dumps(repair(args.raw_root, args.limit, args.dry_run), indent=1))
        if args.mirror:
            mirror(args.raw_root, args.mirror)
        return
    if args.adopt_orphans:
        print(json.dumps(adopt_orphans(args.raw_root), indent=1))
        print(json.dumps(summarise(args.raw_root), indent=1)[:800])
        if args.mirror:
            mirror(args.raw_root, args.mirror)
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
