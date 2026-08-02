"""
ThetaData provider — historical option chains for the options backtest.

Cloud-direct via ThetaData's Python client (an API key, no local Theta Terminal). Optional in
exactly the way the sklearn import is optional: with no key, every method returns empty and
`status()` says so, so tests and stock-model runs never break because an options credential is
missing.

--------------------------------------------------------------------------------------------
THINGS VERIFIED AGAINST THE LIVE FEED BEFORE THIS FILE WAS WRITTEN (do not re-litigate):

  * Auth is cloud-direct with `api_key=`; no local terminal process is needed.
  * 15,669 optionable symbols; AAPL has 814 expirations spanning 2012-06 to 2028-12.
  * EOD rows carry a real NBBO: bid/ask, bid_size/ask_size, volume, plus OHLC.
  * `expiration="*"` returns the WHOLE chain in one call and does NOT truncate. This was
    checked rather than assumed: a wildcard pull for AAPL 2023-03-01 returned exactly 1,000
    rows, which looks like a page cap, but summing per-expiry queries gave exactly 1,000 too.
    Coincidence, not truncation. If a future change makes wildcard pulls lossy, this is the
    check to repeat.

  * EOD RETURNS MORE THAN ONE ROW PER CONTRACT PER DAY. Each contract appears with several
    `created` timestamps (e.g. 17:16 and 18:38 ET). Left unhandled, every trade would be
    counted two or more times and every average silently corrupted. `_dedupe` keeps the LAST
    snapshot per (date, expiration, strike, right) - the closing NBBO, which is the quote a
    decision made at the close could actually have hit.

--------------------------------------------------------------------------------------------
POINT-IN-TIME. A chain is fetched for a specific date and used only for decisions ON that date.
Nothing in this module can see a future quote: `chain_on` takes one date and the caller holds
the expiry. Contracts that later expired worthless are retained, because a chain is pulled as it
stood, not as it ended - which is what keeps the backtest free of the survivorship bias that
comes from only sampling contracts with a nice exit price.
"""
from __future__ import annotations

import datetime as dt
import os
import pickle
import time
from typing import Optional

CACHE_DIR = os.path.join("data", "bulk", "prepared", "theta")
MAX_DTE_PULL = 240          # we never trade beyond ~180 DTE; pulling more is wasted bandwidth
RETRY = 3
RETRY_PAUSE = 2.0


def _log(m):
    print(f"[theta] {m}", flush=True)


def _api_key() -> str:
    key = os.environ.get("THETADATA_API_KEY", "")
    if key:
        return key
    # Fall back to the project's .env without importing app config (keeps this standalone).
    for base in (os.getcwd(), os.path.dirname(os.path.dirname(os.path.dirname(__file__)))):
        p = os.path.join(base, ".env")
        if os.path.exists(p):
            try:
                for line in open(p, encoding="utf-8", errors="replace"):
                    if line.strip().startswith("THETADATA_API_KEY") and "=" in line:
                        return line.split("=", 1)[1].strip()
            except OSError:
                pass
    return ""


class ThetaProvider:
    """Historical option chains, cached to disk. Degrades to a no-op without a key."""

    def __init__(self, api_key: Optional[str] = None, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self._key = api_key if api_key is not None else _api_key()
        self._client = None
        self._err = None
        self._contract_cache = {}
        if not self._key:
            self._err = "no THETADATA_API_KEY"

    # -- lifecycle ---------------------------------------------------------------------
    def status(self) -> dict:
        """Never raises. The no-op status dict that keeps callers honest about availability."""
        return {"available": self.available, "reason": self._err,
                "cache_dir": self.cache_dir, "source": "thetadata-cloud"}

    @property
    def available(self) -> bool:
        if not self._key:
            return False
        if self._client is None:
            try:
                import thetadata as td
                self._client = td.ThetaClient(api_key=self._key, dataframe_type="pandas")
            except Exception as e:                                       # noqa: BLE001
                self._err = f"{type(e).__name__}: {e}"
                return False
        return True

    # -- helpers -----------------------------------------------------------------------
    @staticmethod
    def _dedupe(df):
        """One row per (date, expiration, strike, right): the LAST snapshot of the day.

        Not cosmetic. The feed returns several `created` timestamps per contract per day, so
        without this every trade is counted more than once.
        """
        import pandas as pd

        if df is None or len(df) == 0:
            return df
        d = df.copy()
        d["date"] = pd.to_datetime(d["created"]).dt.date if "created" in d.columns else None
        d = d.sort_values([c for c in ("date", "expiration", "strike", "right", "created")
                           if c in d.columns])
        keys = [c for c in ("date", "expiration", "strike", "right") if c in d.columns]
        return d.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)

    def _cache_path(self, symbol: str, date: dt.date) -> str:
        return os.path.join(self.cache_dir, symbol.upper(), f"{date.isoformat()}.pkl")

    def _call(self, fn, **kw):
        """Retry a feed call; return None rather than raising so one bad day cannot kill a run."""
        for i in range(RETRY):
            try:
                return fn(**kw)
            except Exception as e:                                       # noqa: BLE001
                # "No data" is an ANSWER (an expiry with no quotes), not a transient fault.
                # Retrying it wasted seconds per call across tens of thousands of calls.
                if type(e).__name__ == "NoDataFoundError" or "No data found" in str(e):
                    return None
                if i == RETRY - 1:
                    self._err = f"{type(e).__name__}: {str(e)[:160]}"
                    return None
                time.sleep(RETRY_PAUSE * (i + 1))
        return None

    # -- the one method the backtest needs ----------------------------------------------
    def chain_on(self, symbol: str, date: dt.date, max_dte: int = MAX_DTE_PULL,
                 use_cache: bool = True):
        """Full option chain for `symbol` as of `date`: NBBO + volume + OI + IV + delta.

        Returns a DataFrame (possibly empty). Cached per (symbol, date) so a resumed run costs
        nothing for days already pulled.
        """
        import pandas as pd

        path = self._cache_path(symbol, date)
        if use_cache and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except (OSError, pickle.UnpicklingError):
                pass
        if not self.available:
            return pd.DataFrame()

        eod = self._call(self._client.option_history_eod, start_date=date, end_date=date,
                         symbol=symbol.upper(), expiration="*", max_dte=max_dte)
        if eod is None or len(eod) == 0:
            out = pd.DataFrame()
            self._save(path, out)
            return out
        eod = self._dedupe(eod)

        oi = self._call(self._client.option_history_open_interest, start_date=date,
                        end_date=date, symbol=symbol.upper(), expiration="*", max_dte=max_dte)
        if oi is not None and len(oi):
            oi = oi.copy()
            keys = ["expiration", "strike", "right"]
            oi = oi.drop_duplicates(subset=keys, keep="last")
            eod = eod.merge(oi[keys + ["open_interest"]], on=keys, how="left")

        # NO greeks call here. The endpoint rejects expiration="*", so it could only ever
        # fail - and each failure cost 3 retries with backoff on EVERY chain pull, which was
        # the dominant cost of the whole backtest. Greeks come from blackscholes.enrich_chain.
        self._save(path, eod)
        return eod

    def contract_history(self, symbol, expiration, strike, right, start, end):
        """One contract's ENTIRE daily NBBO life in a single call.

        The alternative - pulling the full chain on every holding day - costs ~30 calls per
        trade instead of one, which is the difference between a backtest that finishes and one
        that does not. Strike must be passed as a plain string ("150"); other encodings return
        NOT_FOUND rather than an error you would notice.
        """
        import pandas as pd

        key = (symbol.upper(), str(expiration), str(strike), str(right)[:1].upper(),
               str(start), str(end))
        if key in self._contract_cache:
            return self._contract_cache[key]
        if not self.available:
            return pd.DataFrame()
        st = f"{float(strike):g}"
        df = self._call(self._client.option_history_eod, start_date=start, end_date=end,
                        symbol=symbol.upper(), expiration=expiration, strike=st,
                        right=str(right)[:1].upper())
        if df is None or len(df) == 0:
            out = pd.DataFrame()
        else:
            out = df.copy()
            out["date"] = pd.to_datetime(out["created"]).dt.date
            out = out.sort_values("created").drop_duplicates(subset=["date"], keep="last")
        if len(self._contract_cache) < 20000:
            self._contract_cache[key] = out
        return out

    def _save(self, path, obj):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        except OSError as e:
            _log(f"cache write failed {path}: {e}")

    def cached_dates(self, symbol: str) -> list:
        """Which days are already on disk - the basis for a resumable pull."""
        d = os.path.join(self.cache_dir, symbol.upper())
        if not os.path.isdir(d):
            return []
        out = []
        for fn in os.listdir(d):
            if fn.endswith(".pkl"):
                try:
                    out.append(dt.date.fromisoformat(fn[:-4]))
                except ValueError:
                    pass
        return sorted(out)

    def prefetch(self, symbols, dates, progress_every: int = 25) -> dict:
        """Chunked, resumable bulk pull. Skips days already cached; safe to re-run after a kill."""
        done = skipped = failed = 0
        t0 = time.time()
        total = len(symbols) * len(dates)
        for s in symbols:
            have = set(self.cached_dates(s))
            for d in dates:
                if d in have:
                    skipped += 1
                    continue
                df = self.chain_on(s, d)
                if df is None or len(df) == 0:
                    failed += 1
                else:
                    done += 1
                if (done + skipped + failed) % progress_every == 0:
                    _log(f"{done+skipped+failed}/{total} "
                         f"(new {done}, cached {skipped}, empty {failed}) {time.time()-t0:.0f}s")
        return {"fetched": done, "cached": skipped, "empty": failed,
                "seconds": round(time.time() - t0, 1)}
