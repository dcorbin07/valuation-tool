"""
Historical-data providers for the Edge Lab — free now, CRSP/Sharadar drop in later.

Same interface for all three, so switching data sources is a one-line config change
(EDGE_DATA_PROVIDER = free | sharadar | wrds) with zero code edits elsewhere:

  price_history(ticker, days)   -> (dates, closes)         # for price-factor backtests
  fundamentals_pit(ticker, as_of) -> dict | None           # point-in-time fundamentals
  survivorship_free              -> bool                    # so caveats are accurate
  ready()                        -> (bool, message)         # is it configured?

  * FreeProvider   — Stooq/yfinance. Works today. Survivorship-BIASED, no PIT fundamentals.
  * SharadarProvider — Nasdaq Data Link SEP (survivorship-free prices w/ delisted) + SF1
    (point-in-time fundamentals). Needs SHARADAR_API_KEY.
  * WRDSProvider   — reads CRSP/Compustat you've exported from WRDS to WRDS_DATA_DIR
    (the academic gold standard; likely free via William & Mary). Survivorship-free + PIT.

Sharadar/WRDS are wired and ready; they raise a clear setup message until you add the
key/data, so nothing breaks in the meantime.
"""
from __future__ import annotations

import os
from typing import Optional

from ..config import CONFIG


class HistoricalDataProvider:
    name = "base"
    survivorship_free = False
    has_pit_fundamentals = False

    def ready(self):
        return True, "ok"

    def price_history(self, ticker: str, days: int = 2700):
        raise NotImplementedError

    def fundamentals_pit(self, ticker: str, as_of: str) -> Optional[dict]:
        return None


class FreeProvider(HistoricalDataProvider):
    name = "free (Stooq/yfinance)"
    survivorship_free = False
    has_pit_fundamentals = False

    def price_history(self, ticker, days=2700):
        from ..screener.prices import close_series
        return close_series(ticker, days=days)


class SharadarProvider(HistoricalDataProvider):
    name = "Sharadar (Nasdaq Data Link)"
    survivorship_free = True
    has_pit_fundamentals = True
    BASE = "https://data.nasdaq.com/api/v3/datatables/SHARADAR"

    def __init__(self, cfg=CONFIG):
        self.key = cfg.sharadar_api_key

    def ready(self):
        return (bool(self.key), "Set SHARADAR_API_KEY (your Nasdaq Data Link key) to use Sharadar.")

    def _get(self, table, **params):
        import requests
        params["api_key"] = self.key
        r = requests.get(f"{self.BASE}/{table}.json", params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("datatable", {})

    def price_history(self, ticker, days=2700):
        import datetime as dt
        try:
            start = (dt.date.today() - dt.timedelta(days=int(days * 1.5))).isoformat()
            dtb = self._get("SEP", ticker=ticker.upper(), **{"date.gte": start},
                            **{"qopts.columns": "date,closeadj"})
            rows = dtb.get("data", [])
            rows.sort(key=lambda x: x[0])
            return [r[0] for r in rows], [float(r[1]) for r in rows]
        except Exception:
            return None, None

    def fundamentals_pit(self, ticker, as_of):
        try:
            dtb = self._get("SF1", ticker=ticker.upper(), dimension="ARQ",
                            **{"datekey.lte": as_of})
            cols = [c["name"] for c in dtb.get("columns", [])]
            rows = dtb.get("data", [])
            if not rows:
                return None
            rows.sort(key=lambda r: r[cols.index("datekey")], reverse=True)
            return dict(zip(cols, rows[0]))
        except Exception:
            return None


class WRDSProvider(HistoricalDataProvider):
    name = "WRDS (CRSP/Compustat local export)"
    survivorship_free = True
    has_pit_fundamentals = True

    def __init__(self, cfg=CONFIG):
        self.dir = cfg.wrds_data_dir

    def ready(self):
        ok = bool(self.dir) and os.path.isdir(self.dir)
        return (ok, "Export CRSP daily prices + Compustat fundamentals from WRDS to "
                    "WRDS_DATA_DIR (see DATA_AND_METHODS.md for the expected file layout).")

    def price_history(self, ticker, days=2700):
        # Expected layouts (either works): prices/<TICKER>.csv (date,close) or a
        # combined prices.parquet/csv with columns [date, ticker, close].
        try:
            import pandas as pd
            per = os.path.join(self.dir, "prices", f"{ticker.upper()}.csv")
            if os.path.exists(per):
                df = pd.read_csv(per)
            else:
                comb = self._combined("prices")
                if comb is None:
                    return None, None
                df = comb[comb["ticker"].str.upper() == ticker.upper()]
            df = df.sort_values("date").tail(days)
            return [str(d) for d in df["date"]], [float(c) for c in df["close"]]
        except Exception:
            return None, None

    def fundamentals_pit(self, ticker, as_of):
        try:
            comb = self._combined("fundamentals")
            if comb is None:
                return None
            df = comb[(comb["ticker"].str.upper() == ticker.upper()) & (comb["datekey"] <= as_of)]
            if df.empty:
                return None
            return df.sort_values("datekey").iloc[-1].to_dict()
        except Exception:
            return None

    def _combined(self, base):
        import pandas as pd
        for ext, rd in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
            p = os.path.join(self.dir, base + ext)
            if os.path.exists(p):
                return rd(p)
        return None


def get_historical_provider(cfg=CONFIG) -> HistoricalDataProvider:
    choice = (cfg.edge_data_provider or "free").lower()
    if choice == "sharadar":
        return SharadarProvider(cfg)
    if choice == "wrds":
        return WRDSProvider(cfg)
    return FreeProvider()
