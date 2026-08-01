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
KEEP = ["expiration", "strike", "right", "date", "bid", "ask", "volume", "open_interest"]

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
    def _fetch_year(self, symbol: str, year: int):
        """One EOD call + one open-interest call for the whole year."""
        import pandas as pd

        cli = self._cli()
        if cli is None:
            return None
        start = dt.date(year, 1, 1)
        end = min(dt.date(year, 12, 31), dt.date.today())
        if start > end:
            return None
        try:
            eod = cli.option_history_eod(start_date=start, end_date=end, symbol=symbol.upper(),
                                         expiration="*", max_dte=self.max_dte)
        except Exception as e:                                           # noqa: BLE001
            if "No data" not in str(e):
                _log(f"{symbol} {year} eod failed: {type(e).__name__}")
            return None
        if eod is None or len(eod) == 0:
            return None
        eod = eod.copy()
        eod["date"] = pd.to_datetime(eod["created"]).dt.date
        eod = (eod.sort_values("created")
                  .drop_duplicates(subset=["date", "expiration", "strike", "right"],
                                   keep="last"))
        try:
            oi = cli.option_history_open_interest(start_date=start, end_date=end,
                                                  symbol=symbol.upper(), expiration="*",
                                                  max_dte=self.max_dte)
        except Exception:                                                # noqa: BLE001
            oi = None
        if oi is not None and len(oi):
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
        slim["right"] = slim["right"].astype(str).str[0].str.upper().astype("category")
        return slim.reset_index(drop=True)

    def ensure_year(self, symbol: str, year: int) -> bool:
        """Pull + cache one symbol-year unless already on disk. Atomic write; resumable."""
        path = year_path(symbol, year, self.root)
        if os.path.exists(path):
            return True
        df = self._fetch_year(symbol, year)
        if df is None or len(df) == 0:
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
