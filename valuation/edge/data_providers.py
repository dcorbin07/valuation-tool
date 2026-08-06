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
from ..safe_error import redact, safe_error


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

    def fundamentals_history(self, ticker: str) -> list:
        """All point-in-time fundamental rows for a ticker (each with a `datekey`),
        so a backtest can fetch once and do as-of lookups locally."""
        return []

    def universe(self, limit=None) -> list:
        """Tickers to backtest (survivorship-free sources include delisted names)."""
        return []

    def insider_history(self, ticker: str) -> list:
        """Insider (Form 4) transactions for a ticker, each with a filing date + signed size."""
        return []

    def institutional_history(self, ticker: str) -> list:
        """Per-quarter 13F institutional-holdings totals for a ticker (each with calendardate)."""
        return []

    def grades_history(self, ticker: str) -> list:
        """Dated analyst rating actions (upgrade / downgrade / maintain) for a ticker.

        Each row carries a `date`, an `action`, and the previous/new grade. These are
        published same-day, so unlike 13F there's no filing lag to model — the action IS
        the news. Point-in-time by construction: every row is stamped with when it happened.
        """
        return []


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
        if not self.key or "PASTE" in str(self.key).upper():
            return (False, "SHARADAR_API_KEY in your .env is still the placeholder — paste your real "
                           "Nasdaq Data Link key (data.nasdaq.com -> Account Settings -> API Key).")
        return (True, "ok")

    def check(self):
        """Live probe: is the key valid AND is the Sharadar subscription active? Returns
        (ok, human-readable reason) so a failed run says WHY instead of just 'failed'."""
        import requests
        try:
            r = requests.get(f"{self.BASE}/SF1.json",
                             params={"ticker": "AAPL", "qopts.per_page": "1", "api_key": self.key}, timeout=20)
            if r.status_code == 200:
                return True, "Sharadar OK — key valid and subscription active."
            # check()'s reason string is surfaced through /admin/run-fundamental-backtest,
            # and every URL this provider builds carries ?api_key= — so it goes through the
            # shared scrubber like any other error text (SECURITY_AUDIT.md M1).
            if r.status_code in (403, 400):
                return False, (f"Sharadar rejected the request (HTTP {r.status_code}). Usually this means the "
                               f"key is wrong OR you haven't subscribed to the Sharadar bundle yet. "
                               f"Detail: {redact(r.text[:200])}")
            return False, f"Sharadar HTTP {r.status_code}: {redact(r.text[:200])}"
        except Exception as e:
            return False, f"Could not reach Nasdaq Data Link: {safe_error(e)}"

    def _get(self, table, **params):
        import requests
        params["api_key"] = self.key
        r = requests.get(f"{self.BASE}/{table}.json", params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("datatable", {})

    def _get_paged(self, table, max_pages=12, **params):
        """Follow Nasdaq's cursor pagination so big tables (e.g. TICKERS ~21k rows) come
        back complete, not just the first page. Returns (columns, rows)."""
        import requests
        params["api_key"] = self.key
        cols, rows = None, []
        for _ in range(max_pages):
            r = requests.get(f"{self.BASE}/{table}.json", params=params, timeout=30)
            r.raise_for_status()
            j = r.json()
            dt = j.get("datatable", {})
            if cols is None:
                cols = [c["name"] for c in dt.get("columns", [])]
            rows.extend(dt.get("data", []))
            cur = (j.get("meta") or {}).get("next_cursor_id")
            if not cur:
                break
            params["qopts.cursor_id"] = cur
        return cols, rows

    def price_history(self, ticker, days=2700):
        import datetime as dt
        start = (dt.date.today() - dt.timedelta(days=int(days * 1.5))).isoformat()
        for table in ("SEP", "SFP"):          # SEP = stocks; SFP = funds/ETFs (e.g. the SPY benchmark)
            try:
                dtb = self._get(table, ticker=ticker.upper(), **{"date.gte": start},
                                **{"qopts.columns": "date,closeadj"})
                rows = dtb.get("data", [])
                if rows:
                    rows.sort(key=lambda x: x[0])
                    return [r[0] for r in rows], [float(r[1]) for r in rows]
            except Exception:
                continue
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

    def fundamentals_history(self, ticker):
        try:
            dtb = self._get("SF1", ticker=ticker.upper(), dimension="ARQ")
            cols = [c["name"] for c in dtb.get("columns", [])]
            return [dict(zip(cols, row)) for row in dtb.get("data", [])]
        except Exception:
            return []

    def universe(self, limit=None):
        # Domestic common stock, INCLUDING delisted (survivorship-free), ranked by market-cap
        # scale so the top-N is the most investable/liquid slice — NOT an arbitrary cut, and
        # NOT thousands of untradeable micro-caps that inflate backtests. Nano-caps (<~$50M,
        # matching the live screener's floor) are dropped.
        try:
            # Fetch the whole TICKERS table with NO server-side filters/column limits (most
            # robust — no dependency on exact filter syntax), then filter + rank in Python.
            cols, data = self._get_paged("TICKERS")
            if not cols or not data:
                return []
            idx = {c: i for i, c in enumerate(cols)}
            ti = idx.get("ticker")
            if ti is None:
                return []
            ci, si, tbl = idx.get("category"), idx.get("scalemarketcap"), idx.get("table")
            ranked, seen = [], set()
            for r in data:
                if tbl is not None and r[tbl] and str(r[tbl]).upper() != "SF1":
                    continue                                    # the fundamentals-covered row
                if ci is not None and r[ci] and "Common Stock" not in str(r[ci]):
                    continue                                    # common stock only
                t = r[ti]
                if not t or t in seen:
                    continue
                scale = 0
                if si is not None and r[si]:
                    try:
                        scale = int(str(r[si]).split(" ")[0])   # "6 - Mega" → 6 … "1 - Nano" → 1
                    except (ValueError, IndexError):
                        scale = 0
                seen.add(t)
                ranked.append((scale, t))
            kept = [x for x in ranked if x[0] >= 2] or ranked    # ≥ Micro ($50M+); fallback if no scale
            kept.sort(key=lambda x: -x[0])                       # most investable first
            return [t for _, t in kept][:limit] if limit else [t for _, t in kept]
        except Exception as e:
            import sys
            # Redacted: this exception is usually a requests HTTPError, whose text is the
            # full ?api_key=... URL, and Render/Actions logs are not a safe home for a live
            # credential (SECURITY_AUDIT.md M1).
            print(f"[universe] Sharadar TICKERS fetch failed: {safe_error(e)}", file=sys.stderr)
            return []

    def insider_history(self, ticker):
        try:
            dtb = self._get("SF2", ticker=ticker.upper())
            cols = [c["name"] for c in dtb.get("columns", [])]
            return [dict(zip(cols, row)) for row in dtb.get("data", [])]
        except Exception:
            return []

    def institutional_history(self, ticker):
        try:
            dtb = self._get("SF3A", ticker=ticker.upper())      # per-ticker per-quarter aggregate
            cols = [c["name"] for c in dtb.get("columns", [])]
            return [dict(zip(cols, row)) for row in dtb.get("data", [])]
        except Exception:
            return []


class WRDSProvider(HistoricalDataProvider):
    name = "local export files (Sharadar or CRSP)"
    survivorship_free = True
    has_pit_fundamentals = True

    # Only the columns each aggregation actually needs — so the big insiders file doesn't
    # blow up memory when we index it.
    _KEEP = {
        "insiders": ["ticker", "filingdate", "date", "transactionshares",
                     "transactionpricepershare", "transactionvalue"],
        # shrholders = how many institutions hold the shares (breadth), distinct from the
        # dollar total. It was missing here, which silently zeroed the breadth signal.
        "institutional": ["ticker", "calendardate", "date", "totalvalue", "value",
                          "sharesheld", "shares", "shrholders"],
        "grades": ["ticker", "date", "action", "gradingCompany", "previousGrade", "newGrade"],
        # NOTE: this allowlist is load-bearing — a column missing here is silently absent
        # downstream, and the factor that needs it reads as "no data" rather than erroring.
        # `assets` was missing, which meant asset_growth (capital discipline) was empty in
        # every backtest despite being wired up. The block after `price` is what the
        # F-Score / accruals / cash-based-profitability signals need.
        "fundamentals": ["ticker", "datekey", "dimension", "revenue", "netinc", "ebit", "ebitda",
                         "gp", "fcf", "equity", "debt", "cashneq", "ev", "intexp", "roic", "roe",
                         "ebitmargin", "grossmargin", "sharesbas", "shareswa", "shareswadil",
                         "sharefactor", "marketcap", "price",
                         "assets", "ncfo", "debtnc", "currentratio", "assetturnover",
                         "cor", "sgna", "rnd", "receivables", "inventory", "payables",
                         # Sharadar computes roe / roic / assetturnover ONLY for its averaged
                         # dimensions (ART/ARY); in the ARQ export they are blank in 100% of
                         # rows. These three are what the panel needs to derive them itself:
                         # roe = netinc/equity, roic = ebit x (1-effective tax)/invcap, and
                         # the effective rate = taxexp/ebt. See _sf1_to_metrics.
                         "invcap", "taxexp", "ebt",
                         # USD variants. `marketcap` and `ev` are USD but the raw line items
                         # are in the company's REPORTING currency, so every value ratio
                         # measured against them needs these (P7). `fxusd` is LOCAL UNITS PER
                         # USD — divide by it, never multiply. There is no `netincusd`;
                         # `netinccmnusd` is net income to common and is the right numerator
                         # against market cap.
                         "equityusd", "revenueusd", "ebitusd", "netinccmnusd", "fxusd",
                         # AUDIT B20 — the LOCAL-currency twin of netinccmnusd, so the
                         # USD fallback path keeps the same numerator DEFINITION (income
                         # to common) instead of switching to total net income.
                         # AUDIT D10-a — `reportperiod` is what identifies a fiscal
                         # quarter. Sharadar APPENDS a new ARQ row on restatement
                         # (verified against the live key 2026-08-03: 3.15% of
                         # (ticker, reportperiod) groups carry more than one datekey,
                         # 1,818 of 2,827 tickers), so a window de-duplicated on datekey
                         # cannot tell two filings of one quarter apart.
                         "netinccmn", "reportperiod"],
    }

    def __init__(self, cfg=CONFIG):
        self.dir = cfg.wrds_data_dir
        self._df_cache = {}      # base -> DataFrame (read once)
        self._idx_cache = {}     # base -> {TICKER: [record, ...]} (built once)

    def _indexed(self, base):
        """Read a combined file ONCE and group rows by ticker, so per-ticker lookups are
        O(1) instead of re-reading (and re-scanning) the whole file 3,000 times. Big files
        are read in chunks with only the needed columns to keep memory bounded."""
        if base in self._idx_cache:
            return self._idx_cache[base]
        import pandas as pd
        keep = self._KEEP.get(base)
        idx = {}

        def ingest(df):
            if "ticker" not in df.columns:
                return
            if keep:
                df = df[[c for c in keep if c in df.columns]]
            df = df.copy()
            df["ticker"] = df["ticker"].astype(str).str.upper()
            for tkr, grp in df.groupby("ticker", sort=False):
                idx.setdefault(tkr, []).extend(grp.to_dict("records"))

        pq = os.path.join(self.dir, base + ".parquet")
        csv = os.path.join(self.dir, base + ".csv")
        try:
            if os.path.exists(pq):
                ingest(pd.read_parquet(pq))
            elif os.path.exists(csv):
                for chunk in pd.read_csv(csv, chunksize=500_000):
                    ingest(chunk)
        except Exception as e:
            import sys
            print(f"[local] failed to index {base}: {e}", file=sys.stderr)
        self._idx_cache[base] = idx
        return idx

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
            # AUDIT B6 — `days=None` means the WHOLE series. The caller then truncates the
            # shared CALENDAR once, so every ticker is cut at the same date. Truncating here
            # gave each ticker its own last N rows and made the union calendar's early
            # cross-sections consist only of names that stopped trading before the window
            # closed. `days` is still honoured when passed, for callers that genuinely want a
            # per-ticker tail (the live book path), but it is never the panel's route now.
            df = df.sort_values("date")
            if days:
                df = df.tail(days)
            return [str(d) for d in df["date"]], [float(c) for c in df["close"]]
        except Exception:
            return None, None

    def fundamentals_pit(self, ticker, as_of):
        rows = [r for r in self._indexed("fundamentals").get(ticker.upper(), [])
                if (r.get("datekey") or "") <= as_of]
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("datekey") or "")
        return rows[-1]

    def fundamentals_history(self, ticker):
        return self._indexed("fundamentals").get(ticker.upper(), [])

    # AUDIT B12 — a `limit` on this provider used to take an ALPHABETICAL slice. Every
    # "800 largest names" result in the project's history was therefore names beginning with
    # roughly A through C: the first CPCV "adopt", PBO 13%, Deflated Sharpe 77%, f_score at
    # t +5.66, sm_breadth at t 2.37, the 13F look-ahead stress test and the four classic-anomaly
    # rejections. It also reframes the project's own calibration note — "PBO 13% on 800 -> 53%
    # on full" was not measuring how much a large-cap tier flatters results, it was measuring
    # how much an arbitrary alphabetical subsample does.
    #
    # NOTE the ranking below is by each ticker's LATEST market cap, which is a mild look-ahead
    # (it is today's size, applied to a 1998 cross-section). That is acceptable for a subset
    # used as a SMOKE TEST and is not acceptable for anything reported — per the METHODOLOGY
    # RULE, verdicts come from the full universe, where `limit` is None and no ranking applies.
    UNIVERSE_SORT_KEY = "market_cap_desc_latest_marketcap"

    def universe(self, limit=None):
        idx = self._indexed("fundamentals")
        # A `limit` at or above the export's size is the FULL universe, not a subset — the
        # caller's default is 3000 against a 2,827-name export. Ranking it would be harmless but
        # labelling it a smoke test would be a lie in the other direction.
        if not limit or limit >= len(idx):
            return sorted(idx.keys())

        def _cap(rows):
            for r in reversed(rows or []):          # rows are datekey-ascending
                v = r.get("marketcap")
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    continue
                if f == f and f > 0:
                    return f
            return 0.0

        ranked = sorted(idx.keys(), key=lambda t: (-_cap(idx[t]), t))
        n_capped = sum(1 for t in ranked[:limit] if _cap(idx[t]) > 0)
        print(f"[universe] {limit} of {len(ranked)} names, sort_key={self.UNIVERSE_SORT_KEY} "
              f"({n_capped} with a resolvable market cap) — SMOKE-TEST SUBSET, not a verdict",
              flush=True)
        return ranked[:limit]

    def insider_history(self, ticker):
        return self._indexed("insiders").get(ticker.upper(), [])

    def institutional_history(self, ticker):
        return self._indexed("institutional").get(ticker.upper(), [])

    def grades_history(self, ticker):
        return self._indexed("grades").get(ticker.upper(), [])

    # ---- Sharadar BULK caches (built by valuation.edge.bulk) --------------------
    # These are prepared once from the multi-GB bulk exports and cached as small
    # pickles; see bulk.py. Loaded lazily and shared, so a panel build pays for each
    # at most once. Absent caches degrade to empty -> every consumer falls back to its
    # previous behaviour rather than failing.
    @property
    def bulk_dir(self):
        d = getattr(self, "_bulk_dir", None)
        if d:
            return d
        # data/backtest -> data/bulk/prepared
        return os.path.join(os.path.dirname(os.path.normpath(self.dir or ".")),
                            "bulk", "prepared")

    def _bulk(self, name):
        cache = getattr(self, "_bulk_cache", None)
        if cache is None:
            cache = self._bulk_cache = {}
        if name not in cache:
            try:
                from .bulk import _load_cache
                cache[name] = _load_cache(name, self.bulk_dir) or {}
            except Exception:
                cache[name] = {}
        return cache[name]

    def daily_history(self, ticker):
        """[(date, marketcap, pe, pb, ps, evebitda), ...] month-end, ascending."""
        return self._bulk("daily").get(ticker.upper(), [])

    def actions_for(self, ticker):
        """{"splits": [...], "delisted": date|None, "dividends": [...]}"""
        return self._bulk("actions").get(ticker.upper(), {})

    def earnings_dates(self, ticker):
        """Announcement dates from the EVENTS cache (code 22 — see bulk.EARNINGS_CODES).

        Empty when the cache is absent, so the panel degrades to "no PEAD signal" rather than
        raising. Coverage is PARTIAL by nature: a missing date means unknown, not "no news".
        """
        from .bulk import earnings_dates as _ed
        return _ed(self._bulk("events"), ticker)

    def congress_for(self, ticker):
        """Congressional trades as (FILING date, signed dollars). Never the transaction date."""
        return self._bulk("congress").get(ticker.upper(), [])

    def usaspending_for(self, ticker):
        """Federal award quarters as (available_date, obligations) — already publication-lagged."""
        return self._bulk("usaspending").get(ticker.upper(), [])

    def edgar_13d_for(self, ticker):
        """SEC 13D/13G filings as (FILING date, form). Filing date == public disclosure date."""
        return self._bulk("edgar13d").get(ticker.upper(), [])

    def short_interest_for(self, ticker):
        """FINRA short-interest observations, already stamped with the PUBLICATION date.

        The cache stores settlementDate + publication lag, never the settlement date itself,
        so a caller cannot accidentally use the un-lagged figure.
        """
        return self._bulk("short_interest").get(ticker.upper(), [])

    def elite_conviction_for(self, ticker):
        """{quarter: elite conviction} from the elite13f cache, or {} when not built."""
        return self._bulk("elite_conv").get(ticker.upper(), {})

    def ticker_meta(self, ticker):
        """{sector, industry, country, exchange, category, scale} from the TICKERS cache.

        NOT point-in-time — it is today's classification (see bulk.prepare_tickers). Empty
        dict when the cache has not been built, so callers degrade to no sector rather than
        crashing.
        """
        return self._bulk("tickers").get(ticker.upper(), {})

    def sf3_for(self, ticker):
        """{quarter: {"holders": n, "value": v, "conviction": c}} — per-manager 13F detail."""
        return self._bulk("sf3").get(ticker.upper(), {})

    def delisted_map(self):
        """{TICKER: delisting_date} for every name that stopped trading.

        Needed because the panel forward-fills prices onto a shared calendar: without
        this, a delisted name's last close is carried forward forever and contributes
        fake flat 0% forward returns to every later rebalance date.
        """
        m = getattr(self, "_delisted", None)
        if m is None:
            m = self._delisted = {t: v["delisted"] for t, v in self._bulk("actions").items()
                                  if isinstance(v, dict) and v.get("delisted")}
        return m

    def _combined(self, base):
        if base in self._df_cache:
            return self._df_cache[base]
        import pandas as pd
        df = None
        for ext, rd in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
            p = os.path.join(self.dir, base + ext)
            if os.path.exists(p):
                df = rd(p)
                break
        self._df_cache[base] = df
        return df


def get_historical_provider(cfg=CONFIG) -> HistoricalDataProvider:
    choice = (cfg.edge_data_provider or "free").lower()
    if choice == "sharadar":
        return SharadarProvider(cfg)
    if choice == "wrds":
        return WRDSProvider(cfg)
    return FreeProvider()
