"""
ThetaData BULK loader — one call per symbol-year, cached to data/options/, 4 concurrent.

WHY THIS REPLACED THE PER-DAY PULLER. The first version called the feed once per candidate day
and once per contract. Measured on the real run that was ~9s per call and 280-640 serial calls
per name: about 51 minutes per name, ~12.7 hours for a 15-name smoke, and hopeless at full
scale. It was also effectively serial while the Standard tier allows 4 concurrent requests, and
it wrote nothing to disk, so a kill lost everything.

The fix is that `option_history_eod` accepts a DATE RANGE and `expiration="*"`, so ONE call
returns an entire year of the entire chain:

    AAPL 2019, max_dte=90  ->  203,666 deduped rows across 253 trading days in 49s, 11MB cached

That is 0.19s per trading day against ~9s before. Per name the pull drops from 280-640 calls to
22 (one EOD + one open-interest call per year), and afterwards every "chain on day D" and every
"contract's full history" is a SLICE of a cached frame rather than a network call.

WHAT IS CACHED, AND WHY IT IS SLIM. Only the columns the backtest actually uses are kept
(expiration, strike, right, date, bid, ask, volume, open_interest), downcast to float32/int32.
The full response is ~5x larger and nothing downstream reads the extra columns.

MAX_DTE=90 IS DELIBERATE, NOT ARBITRARY. The strategy needs two things: the FRONT expiry (for
the put/call ratio and ATM IV, always < ~10 DTE) and the 45-75 DTE band the contract is picked
from. 90 covers both with margin. Raising it multiplies storage for contracts nothing reads.

RESUMABILITY. Each symbol-year is written atomically (temp file then replace) so a kill mid-write
cannot leave a half-file that later loads as truncated data. `ensure_year` skips anything already
on disk, so a re-run costs nothing for work already done - the failure mode that lost the first
run's progress entirely.

--------------------------------------------------------------------------------------------
WHY QUARTERLY CHUNKS, RETRY, AND AN EXPLICIT GAP RECORD (added after the first bulk run).

The first bulk attempt requested a whole year per call and had NO retry. Measured on the real
run, 11 of 30 year-pulls died with gRPC `_MultiThreadedRendezvous` errors - and because there
was no retry and no record, those years were SILENTLY ABSENT. AAPL was missing 2021, 2022 and
2023 while the run carried on as if the history were complete. A backtest that reports a
confident verdict with a third of its data missing is precisely the silent-corruption failure
this project has been bitten by four times.

Three fixes, in order of importance:

  1. GAPS ARE RECORDED, NOT SWALLOWED. A symbol-year that cannot be fetched writes a `.missing`
     marker, and `coverage_report` returns exactly which symbol-years are absent. The backtest
     REFUSES to score a symbol with an incomplete history rather than quietly under-sampling it.
  2. QUARTERLY CHUNKS. The failures are size-related: a quarter of AAPL 2022 returns in 18s
     where the full year fails outright. A year is assembled from four quarter calls, and a
     quarter that fails is retried before the year is abandoned.
  3. TIMEOUT + BACKOFF. Each call runs with a deadline so a hung stream cannot pin a worker,
     and transient failures are retried with increasing backoff. "No data" is still treated as
     an answer, not an error, so empty quarters cost nothing.

`strike_range` was tested as a way to cut payload and REJECTED: it cut rows 38% but made the
call 6x SLOWER (110s vs 18s), because the filtering happens server-side after the scan.

--------------------------------------------------------------------------------------------
TWO FURTHER BUGS, both caught by running the status tool against the live job rather than
waiting for the run to finish.

  A. "MISSING" WAS STICKY. A failed year wrote a marker that blocked every future retry, so one
     transient gRPC error removed that year permanently. AAPL 2026 was marked missing, yet
     re-requesting 2026Q1 by hand returned 83,040 rows immediately - the failure was transient
     and the marker was the real damage. Markers are now split:
        `.empty`   - the feed genuinely has no data (NoDataFoundError). COVERED, never refetched.
        `.missing` - the fetch FAILED. Counted as a gap and RETRIED on the next run.
     The distinction matters because "this ticker did not trade yet" and "the request broke"
     look identical downstream and have opposite correct responses.

  B. TICKER RENAMES BREAK THE JOIN. Options are stored under the symbol as it was AT THE TIME.
     META returns nothing before June 2022; FB returns 101,544 rows for 2019Q1 alone. Scoring
     META on 2022+ only, while treating the earlier years as gaps, would silently drop six years
     of a name we do have data for. `ALIASES` maps a current ticker to its historical symbols and
     `_fetch_span` retries an empty span under the alias, which also handles the mid-year
     boundary (FB until 2022-06-09, META after) without hard-coding the date.

     This is the same class of problem as the today-snapshot caveats already recorded for the
     P10 sector map and the P24.2 CIK map: an identifier that is correct now is not correct for
     history.
"""
from __future__ import annotations

import datetime as dt
import os
import pickle
import threading
import time
from typing import Optional

CACHE_ROOT = os.path.join("data", "options")
MAX_DTE = 90
WORKERS = 4                    # ThetaData Standard allows 4 concurrent requests
CALL_TIMEOUT = 75              # seconds. Was 180, which let ONE pathological symbol-year burn
                               # 8 calls x 3 retries x 180s = 72 minutes, and ten such years
                               # half a day - enough to stall an unattended queue on one name.
                               # A healthy quarter returns in ~5-20s, so 75s is generous.
RETRIES = 2                    # a call that fails twice at 75s is not going to succeed
MIN_SPAN_DAYS = 20             # floor for adaptive splitting; below a month, stop halving

# --- throughput controls (added after names took ~17 min each) ------------------------------
# A name that fails once keeps its SMALLER chunk size for every remaining span, instead of
# rediscovering the failure quarter by quarter. Paying the ~150s failure cost once per name
# rather than once per quarter is the single biggest win here.
DEFAULT_CHUNK_DAYS = 30        # a MONTH, not a quarter. Measured: quarterly spans were both
                               # slower and failure-prone. AAPL is 110,416 rows in 41.4s per
                               # quarter but 34,996 in 9.0s per month (3 months = 27s), and
                               # BKNG's quarter times out at 396,240 rows / 72.8s while its
                               # month returns in 20.9s. Smaller responses are simply more
                               # efficient here, so monthly is faster AND removes the failure
                               # -discovery cost that made every large name burn ~150s.
MIN_CHUNK_DAYS = 22            # ~a month; BKNG returns 122,488 rows in 30s at this size
NAME_BUDGET_S = 900            # hard wall-clock ceiling per symbol-year; then give up
MAX_MISSING_ATTEMPTS = 2       # after this many failed runs a year is EXHAUSTED, not retried
BACKOFF = 4.0                  # seconds, multiplied by attempt number
KEEP = ["expiration", "strike", "right", "date", "bid", "ask", "volume", "open_interest"]

# Current ticker -> symbols it traded under earlier. Options history is stored under the
# symbol of the day, so without this a renamed name silently loses its pre-rename history.
ALIASES = {"META": ["FB"], "GOOGL": ["GOOG"], "RTX": ["UTX"], "WBD": ["T"]}

_LOAD_LOCK = threading.Lock()


def _log(m):
    print(f"[theta-bulk] {m}", flush=True)


def year_path(symbol: str, year: int, root: str = CACHE_ROOT) -> str:
    return os.path.join(root, symbol.upper(), f"{symbol.upper()}-{year}.pkl")


class ThetaBulk:
    """Year-chunked option history. Degrades to a no-op with no API key."""

    def __init__(self, api_key: Optional[str] = None, root: str = CACHE_ROOT,
                 max_dte: int = MAX_DTE, max_years_in_memory: int = 6):
        from .thetadata_provider import _api_key

        self.root = root
        self.max_dte = max_dte
        self._key = api_key if api_key is not None else _api_key()
        self._client = None
        self._err = None if self._key else "no THETADATA_API_KEY"
        self._mem = {}
        self._mem_order = []
        self._max_mem = max_years_in_memory
        self._client_lock = threading.Lock()
        self._chunk_days = {}          # symbol -> span size that actually works
        self._budget_start = {}        # symbol -> wall-clock start for its pull

    def status(self) -> dict:
        return {"available": bool(self._key), "reason": self._err, "root": self.root,
                "max_dte": self.max_dte, "workers": WORKERS}

    def _cli(self):
        # One client, guarded: the gRPC client is shared across the 4 worker threads.
        with self._client_lock:
            if self._client is None:
                if not self._key:
                    return None
                try:
                    import thetadata as td
                    self._client = td.ThetaClient(api_key=self._key, dataframe_type="pandas")
                except Exception as e:                                   # noqa: BLE001
                    self._err = f"{type(e).__name__}: {e}"
                    return None
            return self._client

    # ---------------- fetching ----------------
    def _call_with_timeout(self, fn, **kw):
        """Run a feed call with a deadline and backoff. None means 'no data' or gave up."""
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FTimeout

        for attempt in range(1, RETRIES + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as one:
                    return one.submit(lambda: fn(**kw)).result(timeout=CALL_TIMEOUT)
            except FTimeout:
                _log(f"timeout after {CALL_TIMEOUT}s (attempt {attempt}/{RETRIES})")
            except Exception as e:                                       # noqa: BLE001
                # "No data" is an ANSWER (an empty quarter), not a fault worth retrying.
                if type(e).__name__ == "NoDataFoundError" or "No data found" in str(e):
                    return None
                if attempt == RETRIES:
                    _log(f"gave up after {RETRIES}: {type(e).__name__}")
                    return "FAILED"
            if attempt < RETRIES:
                time.sleep(BACKOFF * attempt)
        return "FAILED"

    def _fetch_span_once(self, symbol: str, start: dt.date, end: dt.date):
        """One EOD + one open-interest call for a span. Returns (frame_or_None, failed_bool)."""
        import pandas as pd

        cli = self._cli()
        if cli is None:
            return None, True
        tried = [symbol.upper()] + [a for a in ALIASES.get(symbol.upper(), [])]
        eod = None
        for sym in tried:
            eod = self._call_with_timeout(cli.option_history_eod, start_date=start, end_date=end,
                                          symbol=sym, expiration="*", max_dte=self.max_dte)
            if isinstance(eod, str):        # "FAILED" - a fault, not an absence; stop here
                return None, True
            if eod is not None and len(eod):
                symbol_used = sym
                break
        else:
            symbol_used = None
        if eod is None or len(eod) == 0:
            return None, False              # genuinely empty span, not a failure
        eod = eod.copy()
        eod["date"] = pd.to_datetime(eod["created"]).dt.date
        eod = (eod.sort_values("created")
                  .drop_duplicates(subset=["date", "expiration", "strike", "right"],
                                   keep="last"))
        oi = self._call_with_timeout(cli.option_history_open_interest, start_date=start,
                                     end_date=end, symbol=symbol_used or symbol.upper(),
                                     expiration="*", max_dte=self.max_dte)
        if oi is not None and not isinstance(oi, str) and len(oi):
            oi = oi.copy()
            oi["date"] = pd.to_datetime(oi["timestamp"]).dt.date
            oi = (oi.sort_values("timestamp")
                    .drop_duplicates(subset=["date", "expiration", "strike", "right"],
                                     keep="last"))
            eod = eod.merge(oi[["date", "expiration", "strike", "right", "open_interest"]],
                            on=["date", "expiration", "strike", "right"], how="left")
        if "open_interest" not in eod.columns:
            eod["open_interest"] = None
        slim = eod[[c for c in KEEP if c in eod.columns]].copy()
        slim["expiration"] = pd.to_datetime(slim["expiration"]).dt.date
        for c in ("bid", "ask", "strike"):
            slim[c] = pd.to_numeric(slim[c], errors="coerce").astype("float32")
        slim["volume"] = pd.to_numeric(slim["volume"], errors="coerce").fillna(0).astype("int32")
        slim["open_interest"] = (pd.to_numeric(slim["open_interest"], errors="coerce")
                                 .fillna(-1).astype("int32"))
        slim["right"] = slim["right"].astype(str).str[0].str.upper()
        return slim.reset_index(drop=True), False


    def _fetch_span(self, symbol: str, start: dt.date, end: dt.date, depth: int = 0):
        """Fetch a span, HALVING it on failure until it succeeds or hits MIN_SPAN_DAYS.

        Response size, not flakiness, is what makes these calls fail. Measured: a quarter of
        BKNG is 396,240 rows and takes 72.8s against a 75s deadline, because it is the
        highest-priced US stock and carries an enormous strike ladder; the same quarter of AAPL
        is 110,416 rows in 41.4s. So BKNG failed whenever the connection was under any load,
        and it failed the SAME way every run - which is why BKNG and NOW each came back missing
        exactly four consecutive years rather than random ones.

        A longer deadline is the wrong fix: it makes a slow name slower without making a large
        response smaller. Halving the span halves the rows (BKNG one month: 122,488 rows in
        30.0s), and it adapts automatically to whatever a name's chain size demands rather than
        needing a per-name tuning table.
        """
        import pandas as pd

        df, failed = self._fetch_span_once(symbol, start, end)
        if not failed:
            return df, False
        span_days = (end - start).days
        if span_days <= MIN_SPAN_DAYS:
            return df, True
        mid = start + dt.timedelta(days=span_days // 2)
        _log(f"{symbol} {start}..{end} failed; splitting ({span_days}d -> 2x{span_days//2}d)")
        a, fa = self._fetch_span(symbol, start, mid, depth + 1)
        b, fb = self._fetch_span(symbol, mid + dt.timedelta(days=1), end, depth + 1)
        parts = [x for x in (a, b) if x is not None and len(x)]
        if not parts:
            return None, (fa or fb)
        return pd.concat(parts, ignore_index=True), (fa or fb)

    def _fetch_year(self, symbol: str, year: int):
        """A year assembled from adaptive chunks. Returns (frame_or_None, any_chunk_failed).

        Two behaviours matter for throughput:

        * THE CHUNK SIZE IS REMEMBERED PER NAME. Response size, not flakiness, is what fails:
          a quarter of BKNG is 396,240 rows and takes 72.8s against a 75s deadline, while the
          same quarter of AAPL is 110,416 rows in 41.4s. Rediscovering that quarter by quarter
          cost ~150s of dead time four times over; now the first failure halves the chunk for
          the REST of the name.
        * THERE IS A WALL-CLOCK BUDGET. Past NAME_BUDGET_S the name is abandoned with whatever
          it has. One pathological symbol must never consume a whole unattended run.
        """
        import pandas as pd

        today = dt.date.today()
        t_start = time.time()
        chunk = self._chunk_days.get(symbol.upper(), DEFAULT_CHUNK_DAYS)
        parts, failed = [], False

        cur = dt.date(year, 1, 1)
        year_end = min(dt.date(year, 12, 31), today)
        while cur <= year_end:
            if time.time() - t_start > NAME_BUDGET_S:
                _log(f"{symbol} {year}: budget {NAME_BUDGET_S}s exhausted; abandoning the rest")
                failed = True
                break
            span_end = min(cur + dt.timedelta(days=chunk - 1), year_end)
            df, fail = self._fetch_span_once(symbol, cur, span_end)
            if fail and chunk > MIN_CHUNK_DAYS:
                # Halve for this span AND every later one - the name has told us its size.
                chunk = max(MIN_CHUNK_DAYS, chunk // 2)
                self._chunk_days[symbol.upper()] = chunk
                _log(f"{symbol}: chunk -> {chunk}d for the rest of this name")
                continue                      # retry the same start at the smaller size
            if fail:
                failed = True
            if df is not None and len(df):
                parts.append(df)
            cur = span_end + dt.timedelta(days=1)

        if not parts:
            return None, failed
        out = pd.concat(parts, ignore_index=True)
        out = out.drop_duplicates(subset=["date", "expiration", "strike", "right"], keep="last")
        out["right"] = out["right"].astype("category")
        return out.reset_index(drop=True), failed

    def ensure_year(self, symbol: str, year: int) -> bool:
        """Pull + cache one symbol-year unless already on disk. Atomic write; resumable."""
        path = year_path(symbol, year, self.root)
        if os.path.exists(path):
            return True
        if os.path.exists(path + ".empty"):
            return True          # genuinely no data (pre-IPO / pre-rename): covered, not a gap
        if os.path.exists(path + ".exhausted"):
            # Tried MAX_MISSING_ATTEMPTS times across runs and never succeeded. Retrying it
            # again is the blackhole that made every run spend ~17 minutes on the same name.
            return False
        df, failed = self._fetch_year(symbol, year)
        if df is None or len(df) == 0:
            # Distinguish "the feed has nothing" from "the request broke". A silently-absent
            # year is how the first run nearly reported a verdict on a third of its data gone.
            marker = ".missing" if failed else ".empty"
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                attempts = 0
                if failed and os.path.exists(path + ".missing"):
                    try:
                        attempts = int(open(path + ".missing").read().split()[0])
                    except (OSError, ValueError, IndexError):
                        attempts = 1
                attempts += 1
                if failed and attempts >= MAX_MISSING_ATTEMPTS:
                    # Give up permanently rather than re-burning the budget every run.
                    with open(path + ".exhausted", "w", encoding="utf-8") as f:
                        f.write(f"{attempts} failed attempts, last "
                                f"{dt.date.today().isoformat()}\n")
                    try:
                        os.remove(path + ".missing")
                    except OSError:
                        pass
                    _log(f"{symbol} {year}: EXHAUSTED after {attempts} attempts; will not retry")
                else:
                    with open(path + marker, "w", encoding="utf-8") as f:
                        f.write(f"{attempts} {'fetch failed' if failed else 'no data'} "
                                f"{dt.date.today().isoformat()}\n")
            except OSError:
                pass
            return not failed
        if failed:
            # Partial year: do NOT cache it as if complete.
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + ".missing", "w", encoding="utf-8") as f:
                    f.write(f"partial (a quarter failed) {dt.date.today().isoformat()}\n")
            except OSError:
                pass
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + f".tmp{os.getpid()}"
        try:
            with open(tmp, "wb") as f:
                pickle.dump(df, f, protocol=5)
            os.replace(tmp, path)                 # atomic: a kill cannot leave a partial file
        except OSError as e:
            _log(f"write failed {path}: {e}")
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False
        return True

    def prefetch(self, symbols, years, workers: int = WORKERS) -> dict:
        """Bulk pull with the tier's 4 concurrent requests. Skips anything already cached."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        jobs = [(s, y) for s in symbols for y in years
                if not os.path.exists(year_path(s, y, self.root))]
        got = miss = 0
        t0 = time.time()
        if not jobs:
            return {"fetched": 0, "missing": 0, "already_cached": len(symbols) * len(years),
                    "seconds": 0.0}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(self.ensure_year, s, y): (s, y) for s, y in jobs}
            for i, fu in enumerate(as_completed(futs), 1):
                s, y = futs[fu]
                try:
                    ok = fu.result()
                except Exception as e:                                   # noqa: BLE001
                    _log(f"{s} {y}: {type(e).__name__} {str(e)[:90]}")
                    ok = False
                got += 1 if ok else 0
                miss += 0 if ok else 1
                if i % 10 == 0 or i == len(jobs):
                    _log(f"{i}/{len(jobs)} year-files ({got} ok, {miss} empty) "
                         f"{time.time()-t0:.0f}s")
        return {"fetched": got, "missing": miss,
                "already_cached": len(symbols) * len(years) - len(jobs),
                "seconds": round(time.time() - t0, 1)}

    # ---------------- reading (no network) ----------------
    def _year_frame(self, symbol: str, year: int):
        key = (symbol.upper(), year)
        with _LOAD_LOCK:
            if key in self._mem:
                return self._mem[key]
        path = year_path(symbol, year, self.root)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                df = pickle.load(f)
        except (OSError, pickle.UnpicklingError):
            return None
        with _LOAD_LOCK:
            self._mem[key] = df
            self._mem_order.append(key)
            while len(self._mem_order) > self._max_mem:
                old = self._mem_order.pop(0)
                self._mem.pop(old, None)
        return df

    def chain_on(self, symbol: str, date):
        """The chain as of one date - a SLICE of the cached year, not a network call."""
        import pandas as pd

        d = date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date)[:10])
        df = self._year_frame(symbol, d.year)
        if df is None:
            return pd.DataFrame()
        out = df[df["date"] == d]
        return out.reset_index(drop=True)

    def contract_history(self, symbol, expiration, strike, right, start, end):
        """One contract's daily life across the entry->expiry window. Spans year boundaries."""
        import pandas as pd

        s = start if isinstance(start, dt.date) else dt.date.fromisoformat(str(start)[:10])
        e = end if isinstance(end, dt.date) else dt.date.fromisoformat(str(end)[:10])
        exp = expiration if isinstance(expiration, dt.date) else \
            dt.date.fromisoformat(str(expiration)[:10])
        frames = []
        for yr in range(s.year, e.year + 1):
            df = self._year_frame(symbol, yr)
            if df is None:
                continue
            m = df[(df["expiration"] == exp)
                   & (df["strike"].astype(float).round(3) == round(float(strike), 3))
                   & (df["right"].astype(str).str[0] == str(right)[0].upper())
                   & (df["date"] >= s) & (df["date"] <= e)]
            if len(m):
                frames.append(m)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames).sort_values("date").reset_index(drop=True)

    def coverage_report(self, symbols, years) -> dict:
        """Exactly which symbol-years are present vs missing. The backtest must consult this
        before scoring: a symbol with gaps is under-sampled, not merely smaller."""
        complete, gaps = {}, {}
        for s_ in symbols:
            have = set(self.cached_years(s_))
            # A year the feed genuinely has no data for (pre-IPO, pre-rename) is COVERED.
            for y in years:
                if os.path.exists(year_path(s_, y, self.root) + ".empty"):
                    have.add(y)
            miss = [y for y in years if y not in have]
            complete[s_] = sorted(have & set(years))
            if miss:
                gaps[s_] = miss
        return {"complete": complete, "gaps": gaps,
                "fully_covered": [s_ for s_ in symbols if s_ not in gaps],
                "n_fully_covered": len([s_ for s_ in symbols if s_ not in gaps])}

    def cached_years(self, symbol: str) -> list:
        d = os.path.join(self.root, symbol.upper())
        if not os.path.isdir(d):
            return []
        out = []
        for fn in os.listdir(d):
            if fn.endswith(".pkl") and "-" in fn:
                try:
                    out.append(int(fn.rsplit("-", 1)[1][:-4]))
                except ValueError:
                    pass
        return sorted(out)


# ---------------------------------------------------------------------------------------
# Standalone entry point so the pull is NOT driven by an agent session:
#     python -m valuation.edge.theta_bulk
# It delegates to the miner, which owns the ranked universe and the liquidity screen.
if __name__ == "__main__":
    import runpy
    import sys

    _here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, _here)
    runpy.run_path(os.path.join(_here, "mine_options_cache.py"), run_name="__main__")
