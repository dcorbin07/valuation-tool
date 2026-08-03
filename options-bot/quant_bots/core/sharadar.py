"""
Sharadar (Nasdaq Data Link) data adapter — the survivorship-bias-free backbone.

WHY THIS EXISTS
───────────────
Every backtest in this project has, until now, been built on a universe of
"companies that are listed TODAY, filtered by TODAY's market cap, sorted by
TODAY's size." That is not a mild flatter. For a momentum strategy it is close
to fatal: you are pre-selecting the winners of the very period you are
measuring, and every delisted, acquired or bankrupt name simply does not exist
in the data. Sharadar's SEP table retains full price history for delisted
tickers, so the historical universe can be reconstructed as it ACTUALLY was.

That single property is what the subscription buys. Everything else here is
plumbing to get at it without introducing look-ahead bias by another route.

DESIGN CHOICES, AND WHY
───────────────────────
1. STDLIB ONLY. No pandas, no numpy, no nasdaq-data-link client. The bots run
   on a 1GB free-tier VM and their requirements.txt is four packages. Bulk CSV
   through sqlite3 is entirely adequate for a few million rows and adds nothing
   to the deployment. It also sidesteps the official Python client's hard
   1,000,000-row ceiling, which SEP and SF1 both blow past — and which raises
   rather than returning a partial frame, so you get NOTHING.

2. sqlite3 AS THE LOCAL STORE. Indexed on (ticker, date), so the O(n) linear
   scans that made the old PriceHistory ~10^8 operations become index seeks.
   The file is portable, inspectable with any SQLite browser, and needs no
   server.

3. DUCK-TYPED HISTORY ADAPTER. Every signal generator in this codebase stores
   an untyped `self.tradier` and calls exactly one method on it:
   `get_history(symbol, start, end, interval) -> [{"date": iso, "close": f}]`.
   SharadarHistory implements that shape, so it drops into all five call sites
   with ZERO changes to any strategy code. That decoupling was already there;
   this just takes advantage of it.

4. closeadj FOR RETURNS, closeunadj FOR PRICE-LEVEL SCREENS. Every signal in
   this project is a ratio of two closes at different times. `close` is
   split-adjusted but NOT dividend-adjusted, so using it silently understates
   total return by the full dividend yield. `closeadj` is the total-return
   series. But `closeadj` is BACK-adjusted — the whole history is rewritten
   whenever a new split or dividend lands — so it is NOT a point-in-time price
   level. "Was this a sub-$20 stock at the time?" must be answered with
   `closeunadj`. Getting this backwards is subtle and silent.

5. AR* DIMENSIONS, INDEXED ON datekey + 1 DAY. Sharadar's MR* dimensions are
   restated with hindsight AND set `datekey` to the fiscal period end, which is
   typically 30-90 days before the data existed. Two independent look-ahead
   traps in one column. The +1 day shift matters because `datekey` is a bare
   date: a filing accepted at 16:30 ET was not tradable at that day's close.

OPEN QUESTION, DELIBERATELY NOT ASSUMED
───────────────────────────────────────
Whether a restatement APPENDS a new ARQ row (same reportperiod, later datekey)
or leaves the as-reported series untouched. If it appends, the obvious
`GROUP BY reportperiod ... ORDER BY datekey DESC LIMIT 1` silently pulls in
restated data and reintroduces look-ahead. `pit_fundamental()` below takes the
EARLIEST datekey per reportperiod, which is correct under both behaviours —
strictly safer than guessing. scripts/verify_sharadar.py probes this against
a real 10-K/A filer so we can stop being defensive about it.

USAGE
─────
    # One-time seed (SEP is ~2GB of CSV; this takes a while)
    python scripts/sharadar_sync.py --tables SEP TICKERS SF1 --full

    # Daily incremental
    python scripts/sharadar_sync.py --tables SEP TICKERS SF1

    # Then, anywhere a TradierClient was used for history:
    store   = SharadarStore(Path("data/sharadar.db"))
    history = SharadarHistory(store)
    signals = MomentumSignalGenerator(MomentumConfig(), history)   # unchanged
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://data.nasdaq.com/api/v3/datatables"

# Tables in the Core US Equities Bundle (SFA). Values are the column used for
# incremental sync — Sharadar RESTATES, so syncing on `date` permanently misses
# every revision. `lastupdated` moves when a row is rewritten; `date` never does.
BUNDLE_TABLES = {
    "SEP":     "date",          # equity prices (stocks only) — survivorship-free
    "SFP":     "date",          # fund prices (ETFs/CEFs/ETNs) — same schema as SEP
    "SF1":     "lastupdated",   # core fundamentals
    "SF2":     "filingdate",    # insiders (Forms 3/4/5)
    "TICKERS": "lastupdated",   # metadata, delisting flags, sector
    "DAILY":   "lastupdated",   # daily marketcap / ev / ratios
    "ACTIONS": "date",          # splits, dividends, corporate actions
    "SP500":   "date",          # index constituents, current + historical
}

# Dimensions that are safe for backtesting: As-Reported, restatements EXCLUDED.
SAFE_DIMENSIONS = ("ARQ", "ARY", "ART")


class SharadarError(RuntimeError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
#  REST client
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SharadarClient:
    """
    Minimal Tables-API client. urllib only.

    Auth goes in the `x-api-token` HEADER rather than an `api_key` query
    parameter. Both work; the header keeps the key out of proxy logs, server
    access logs, and any error message that echoes the URL.
    """
    api_key: str = field(default_factory=lambda: os.getenv("NASDAQ_DATA_LINK_API_KEY", ""))
    timeout: int = 120
    max_retries: int = 5

    def __post_init__(self):
        if not self.api_key:
            raise SharadarError(
                "No API key. Set NASDAQ_DATA_LINK_API_KEY in the environment or "
                "quant_bots/.env — never hardcode it."
            )

    # ── low level ──────────────────────────────────────────────────────────

    def _get(self, url: str, send_token: bool = True) -> bytes:
        """
        GET with exponential backoff on 429/5xx.

        send_token=False for pre-signed bulk-download links: attaching our
        credentials to an already-signed S3 URL can invalidate the signature.
        """
        delay = 1.0
        last_err = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(url)
            if send_token:
                req.add_header("x-api-token", self.api_key)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                body = e.read()[:400].decode("utf-8", "replace")
                # Nasdaq still uses the Quandl error envelope post-rebrand.
                try:
                    err = json.loads(body)["quandl_error"]
                    detail = f"{err.get('code')}: {err.get('message')}"
                except Exception:
                    detail = body
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries - 1:
                    logger.warning("HTTP %s (%s) — retrying in %.0fs", e.code, detail, delay)
                    time.sleep(delay)
                    delay *= 2
                    last_err = detail
                    continue
                raise SharadarError(f"HTTP {e.code} — {detail}") from e
            except urllib.error.URLError as e:
                if attempt < self.max_retries - 1:
                    logger.warning("Network error (%s) — retrying in %.0fs", e.reason, delay)
                    time.sleep(delay)
                    delay *= 2
                    last_err = str(e.reason)
                    continue
                raise SharadarError(f"Network error: {e.reason}") from e
        raise SharadarError(f"Exhausted retries: {last_err}")

    @staticmethod
    def _encode(filters: dict) -> str:
        """
        ticker='AAPL' | ticker=['AAPL','MSFT'] | date={'gte': '2024-01-01'}

        Note .gte/.lte are INCLUSIVE and .gt/.lt EXCLUSIVE — a bare
        `date=2024-01-02` is exact equality, which is a common accident when a
        range was meant.
        """
        parts = []
        for k, v in filters.items():
            if isinstance(v, dict):
                for op, val in v.items():
                    parts.append((f"{k}.{op}", str(val)))
            elif isinstance(v, (list, tuple, set)):
                parts.append((k, ",".join(str(x) for x in v)))
            else:
                parts.append((k, str(v)))
        return urllib.parse.urlencode(parts)

    # ── paged fetch ────────────────────────────────────────────────────────

    def fetch(self, table: str, columns: Optional[list[str]] = None,
              max_pages: Optional[int] = None, **filters) -> Iterator[dict]:
        """
        Yield rows, following the cursor to completion.

        The API caps a page at 10,000 rows and hands back `meta.next_cursor_id`.
        A caller that ignores the cursor gets exactly 10,000 rows and no error —
        which looks identical to a small result set. NEVER let a row count of
        exactly 10000 pass unexamined.

        Results are UNSORTED by design ("Data sorting must be done locally"),
        so do not assume page N+1 follows page N chronologically.
        """
        params = dict(filters)
        if columns:
            params["qopts.columns"] = ",".join(columns)

        cursor, pages, total = None, 0, 0
        while True:
            q = dict(params)
            if cursor:
                q["qopts.cursor_id"] = cursor       # filters must be RESENT with the cursor
            url = f"{BASE_URL}/SHARADAR/{table}.json?{self._encode(q)}"
            payload = json.loads(self._get(url))

            dt = payload["datatable"]
            cols = [c["name"] for c in dt["columns"]]
            for row in dt["data"]:
                yield dict(zip(cols, row))
                total += 1

            pages += 1
            cursor = (payload.get("meta") or {}).get("next_cursor_id")
            if not cursor:
                logger.info("%s: %d rows over %d page(s)", table, total, pages)
                return
            if max_pages and pages >= max_pages:
                raise SharadarError(
                    f"{table}: stopped at {pages} pages with the cursor still open. "
                    f"This is a bulk-sized table — use bulk_export() instead of "
                    f"paging, or you will silently truncate."
                )

    # ── bulk export ────────────────────────────────────────────────────────

    def bulk_export(self, table: str, dest: Path, poll_seconds: int = 30,
                    timeout_seconds: int = 3600, **filters) -> Path:
        """
        Full-table export. The ONLY viable path for SEP and SF1.

        Returns a job descriptor rather than data; poll until it is fresh, then
        download the (large) zip. Three details that bite:

          * The pre-signed link is valid for 30 MINUTES. Don't cache it.
          * Status casing differs between Nasdaq's docs (Fresh/Creating/
            Regenerating) and Sharadar's own published script (fresh/generating/
            regenerating). Compare case-insensitively.
          * Exports are rate-limited to 60/HOUR. A tight poll loop will lock you
            out of the very export you are waiting for — hence the 30s floor.
        """
        params = dict(filters)
        params["qopts.export"] = "true"
        url = f"{BASE_URL}/SHARADAR/{table}.json?{self._encode(params)}"

        deadline = time.time() + timeout_seconds
        link, status = None, None
        while time.time() < deadline:
            info = json.loads(self._get(url))["datatable_bulk_download"]["file"]
            status = str(info.get("status", "")).lower()
            if status == "fresh":
                link = info["link"]
                break
            logger.info("%s export status=%s — waiting %ds", table, status, poll_seconds)
            time.sleep(max(poll_seconds, 30))

        if not link:
            raise SharadarError(
                f"{table}: export not ready within {timeout_seconds}s (last status={status})")

        logger.info("Downloading %s export...", table)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Pre-signed link — do NOT attach our token.
        dest.write_bytes(self._get(link, send_token=False))
        logger.info("%s -> %s (%.1f MB)", table, dest, dest.stat().st_size / 1e6)
        return dest


def iter_zip_csv(path: Path) -> Iterator[dict]:
    """Stream rows out of a bulk-export zip without loading it into memory."""
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with zf.open(name) as raw:
                yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════════
#  Local store
# ═══════════════════════════════════════════════════════════════════════════

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sep (
    ticker TEXT NOT NULL, date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    closeadj REAL, closeunadj REAL, lastupdated TEXT,
    PRIMARY KEY (ticker, date)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS tickers (
    tbl TEXT NOT NULL, permaticker TEXT, ticker TEXT NOT NULL, name TEXT,
    exchange TEXT, isdelisted TEXT, category TEXT, sector TEXT, industry TEXT,
    siccode TEXT, famaindustry TEXT, currency TEXT, location TEXT,
    firstpricedate TEXT, lastpricedate TEXT, firstquarter TEXT, lastquarter TEXT,
    PRIMARY KEY (tbl, ticker)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sf1 (
    ticker TEXT NOT NULL, dimension TEXT NOT NULL,
    calendardate TEXT, datekey TEXT NOT NULL, reportperiod TEXT,
    lastupdated TEXT, payload TEXT NOT NULL,
    PRIMARY KEY (ticker, dimension, reportperiod, datekey)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS daily (
    ticker TEXT NOT NULL, date TEXT NOT NULL,
    marketcap REAL, ev REAL, pe REAL, ps REAL, pb REAL,
    PRIMARY KEY (ticker, date)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sync_log (
    tbl TEXT PRIMARY KEY, watermark TEXT, rows INTEGER, synced_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sep_date       ON sep(date);
CREATE INDEX IF NOT EXISTS idx_sf1_datekey    ON sf1(ticker, dimension, datekey);
CREATE INDEX IF NOT EXISTS idx_daily_date     ON daily(date);
CREATE INDEX IF NOT EXISTS idx_tickers_perma  ON tickers(permaticker);
"""


def _f(v) -> Optional[float]:
    try:
        return float(v) if v not in (None, "", "NA") else None
    except (TypeError, ValueError):
        return None


class SharadarStore:
    """
    sqlite3-backed local mirror. Indexed so point-in-time slices are seeks
    rather than scans — the old PriceHistory did linear scans per symbol per
    day, roughly 10^8 operations for a 150-symbol, 3-year backtest.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)
        # Bulk ingest of millions of rows: WAL + relaxed sync is ~5x faster and
        # the only cost is losing the last transaction on a power cut, which for
        # a re-downloadable mirror is not a real cost.
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")

    def close(self):
        self.db.commit()
        self.db.close()

    # ── ingest ─────────────────────────────────────────────────────────────

    def ingest_sep(self, rows: Iterable[dict], batch: int = 20_000) -> int:
        sql = ("INSERT INTO sep (ticker,date,open,high,low,close,volume,"
               "closeadj,closeunadj,lastupdated) VALUES (?,?,?,?,?,?,?,?,?,?) "
               "ON CONFLICT(ticker,date) DO UPDATE SET "
               "close=excluded.close, closeadj=excluded.closeadj, "
               "closeunadj=excluded.closeunadj, volume=excluded.volume, "
               "lastupdated=excluded.lastupdated")
        return self._ingest(sql, rows, batch, lambda r: (
            r["ticker"], r["date"], _f(r.get("open")), _f(r.get("high")),
            _f(r.get("low")), _f(r.get("close")), _f(r.get("volume")),
            _f(r.get("closeadj")), _f(r.get("closeunadj")), r.get("lastupdated"),
        ))

    def ingest_tickers(self, rows: Iterable[dict], batch: int = 5_000) -> int:
        cols = ("permaticker", "name", "exchange", "isdelisted", "category",
                "sector", "industry", "siccode", "famaindustry", "currency",
                "location", "firstpricedate", "lastpricedate", "firstquarter",
                "lastquarter")
        sql = (f"INSERT INTO tickers (tbl,ticker,{','.join(cols)}) "
               f"VALUES ({','.join('?' * (len(cols) + 2))}) "
               f"ON CONFLICT(tbl,ticker) DO UPDATE SET " +
               ", ".join(f"{c}=excluded.{c}" for c in cols))
        return self._ingest(sql, rows, batch,
                            lambda r: (r.get("table") or "SEP", r["ticker"],
                                       *[r.get(c) for c in cols]))

    def ingest_sf1(self, rows: Iterable[dict], batch: int = 10_000) -> int:
        """
        SF1 has 111 columns and we cannot know today which the screener will
        want tomorrow. Store the identifying columns natively for indexing and
        keep the full row as JSON. Costs some space, saves a re-download every
        time a new factor is added.
        """
        sql = ("INSERT INTO sf1 (ticker,dimension,calendardate,datekey,"
               "reportperiod,lastupdated,payload) VALUES (?,?,?,?,?,?,?) "
               "ON CONFLICT(ticker,dimension,reportperiod,datekey) DO UPDATE SET "
               "payload=excluded.payload, lastupdated=excluded.lastupdated, "
               "calendardate=excluded.calendardate")
        return self._ingest(sql, rows, batch, lambda r: (
            r["ticker"], r["dimension"], r.get("calendardate"), r["datekey"],
            r.get("reportperiod"), r.get("lastupdated"), json.dumps(r),
        ))

    def ingest_daily(self, rows: Iterable[dict], batch: int = 20_000) -> int:
        sql = ("INSERT INTO daily (ticker,date,marketcap,ev,pe,ps,pb) "
               "VALUES (?,?,?,?,?,?,?) "
               "ON CONFLICT(ticker,date) DO UPDATE SET "
               "marketcap=excluded.marketcap, ev=excluded.ev")
        return self._ingest(sql, rows, batch, lambda r: (
            r["ticker"], r["date"], _f(r.get("marketcap")), _f(r.get("ev")),
            _f(r.get("pe")), _f(r.get("ps")), _f(r.get("pb")),
        ))

    def _ingest(self, sql, rows, batch, to_tuple) -> int:
        n, buf = 0, []
        for r in rows:
            try:
                buf.append(to_tuple(r))
            except (KeyError, TypeError) as e:
                logger.debug("skipping malformed row: %s", e)
                continue
            if len(buf) >= batch:
                self.db.executemany(sql, buf); self.db.commit()
                n += len(buf); buf.clear()
                logger.info("  ...%d rows", n)
        if buf:
            self.db.executemany(sql, buf); self.db.commit()
            n += len(buf)
        return n

    def record_sync(self, table: str, watermark: str, rows: int) -> None:
        from datetime import datetime, timezone
        self.db.execute(
            "INSERT INTO sync_log (tbl,watermark,rows,synced_at) VALUES (?,?,?,?) "
            "ON CONFLICT(tbl) DO UPDATE SET watermark=excluded.watermark, "
            "rows=excluded.rows, synced_at=excluded.synced_at",
            (table, watermark, rows, datetime.now(timezone.utc).isoformat()))
        self.db.commit()

    def watermark(self, table: str) -> Optional[str]:
        row = self.db.execute("SELECT watermark FROM sync_log WHERE tbl=?",
                              (table,)).fetchone()
        return row["watermark"] if row else None

    def stats(self) -> dict:
        out = {}
        for t in ("sep", "tickers", "sf1", "daily"):
            try:
                out[t] = self.db.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
            except sqlite3.Error:
                out[t] = 0
        row = self.db.execute("SELECT MIN(date) a, MAX(date) b FROM sep").fetchone()
        out["sep_range"] = (row["a"], row["b"]) if row and row["a"] else None
        return out

    # ── point-in-time reads ────────────────────────────────────────────────

    def closes(self, ticker: str, start: date, end: date,
               adjusted: bool = True) -> list[tuple[date, float]]:
        """
        Daily closes in [start, end], oldest first.

        adjusted=True returns `closeadj` — split AND dividend adjusted, i.e. the
        TOTAL RETURN series. Every signal in this project is a ratio of two
        closes at different times, so this is what they must use. Using plain
        `close` understates return by the full dividend yield, silently.
        """
        col = "closeadj" if adjusted else "closeunadj"
        rows = self.db.execute(
            f"SELECT date, {col} v FROM sep WHERE ticker=? AND date BETWEEN ? AND ? "
            f"AND {col} IS NOT NULL AND {col} > 0 ORDER BY date",
            (ticker, start.isoformat(), end.isoformat())).fetchall()
        return [(date.fromisoformat(r["date"]), r["v"]) for r in rows]

    def price_on(self, ticker: str, as_of: date, adjusted: bool = False) -> Optional[float]:
        """
        Most recent close on or before `as_of`. Defaults to UNADJUSTED, because
        the usual question here is "what would this have cost" — a price LEVEL.
        closeadj is back-adjusted and is not a valid historical price level.
        """
        col = "closeadj" if adjusted else "closeunadj"
        row = self.db.execute(
            f"SELECT {col} v FROM sep WHERE ticker=? AND date<=? AND {col} IS NOT NULL "
            f"ORDER BY date DESC LIMIT 1", (ticker, as_of.isoformat())).fetchone()
        return row["v"] if row else None

    def trading_dates(self, start: date, end: date) -> list[date]:
        rows = self.db.execute(
            "SELECT DISTINCT date FROM sep WHERE date BETWEEN ? AND ? ORDER BY date",
            (start.isoformat(), end.isoformat())).fetchall()
        return [date.fromisoformat(r["date"]) for r in rows]

    def pit_fundamental(self, ticker: str, as_of: date,
                        dimension: str = "ART") -> Optional[dict]:
        """
        Most recent as-reported fundamentals KNOWABLE on `as_of`.

        Three deliberate choices, each preventing a distinct look-ahead route:

          * `dimension` must be an AR* code. MR* is restated with hindsight.
          * `datekey < as_of` (strict) rather than <=. datekey is a bare date;
            a filing accepted at 16:30 ET was not tradable at that close. This
            is the "+1 day shift" the literature recommends, expressed as a
            strict inequality.
          * Among rows sharing a reportperiod we take the EARLIEST datekey. If
            Sharadar appends a new AR row on restatement, the latest datekey is
            the RESTATED figure — taking the earliest gets the originally filed
            number, which is what was actually knowable. If Sharadar does not
            append, this is a no-op. Correct under both behaviours, which is
            why it is written this way rather than the obvious way.
        """
        if dimension not in SAFE_DIMENSIONS:
            raise SharadarError(
                f"dimension {dimension!r} is restated with hindsight. Backtests "
                f"must use one of {SAFE_DIMENSIONS}.")
        row = self.db.execute(
            "SELECT payload FROM sf1 WHERE ticker=? AND dimension=? AND datekey<? "
            "ORDER BY reportperiod DESC, datekey ASC LIMIT 1",
            (ticker, dimension, as_of.isoformat())).fetchone()
        return json.loads(row["payload"]) if row else None

    def marketcap_on(self, ticker: str, as_of: date) -> Optional[float]:
        """Point-in-time market cap from DAILY — genuinely as-of, unlike
        TICKERS.scalemarketcap which is a MAX-OVER-LIFETIME bucket and leaks
        look-ahead into any universe filtered on it."""
        row = self.db.execute(
            "SELECT marketcap FROM daily WHERE ticker=? AND date<=? "
            "AND marketcap IS NOT NULL ORDER BY date DESC LIMIT 1",
            (ticker, as_of.isoformat())).fetchone()
        return row["marketcap"] if row else None


# ═══════════════════════════════════════════════════════════════════════════
#  Duck-typed history adapter
# ═══════════════════════════════════════════════════════════════════════════

class SharadarHistory:
    """
    Drop-in replacement for TradierClient wherever price HISTORY is read.

    Every signal generator in this codebase holds an untyped `self.tradier` and
    calls exactly one method on it. Implementing that method here means
    momentum, reversion, trend and the regime filter all run on
    survivorship-free data with no change to a single line of strategy code.

    It does NOT implement order placement or account queries — this is a data
    source, not a broker. Live trading still needs the real TradierClient.
    """

    def __init__(self, store: SharadarStore, adjusted: bool = True):
        self.store = store
        self.adjusted = adjusted

    def get_history(self, symbol: str, start: date, end: date,
                    interval: str = "daily") -> list[dict]:
        if interval != "daily":
            raise SharadarError(f"SEP is end-of-day only; got interval={interval!r}")
        return [{"date": d.isoformat(), "close": c}
                for d, c in self.store.closes(symbol, start, end, self.adjusted)]

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        """
        Latest stored close per symbol, shaped like a Tradier quote.

        This exists so resolve_prices() can back-fill an exit price in a
        historical run. It is NOT a live quote — in a backtest that is exactly
        right, and in live trading you must use the real broker.
        """
        out = []
        for s in symbols:
            row = self.store.db.execute(
                "SELECT date, closeunadj FROM sep WHERE ticker=? "
                "AND closeunadj IS NOT NULL ORDER BY date DESC LIMIT 1", (s,)).fetchone()
            if row:
                out.append({"symbol": s, "last": row["closeunadj"], "close": row["closeunadj"]})
        return out


class AsOfHistory:
    """
    A SharadarHistory pinned to a simulated date.

    THIS IS THE LOOK-AHEAD BACKSTOP. A backtest that passes `end=today` by
    accident sees the future and produces a beautiful, worthless equity curve.
    Wrapping the source in an object that CANNOT return a bar after `as_of`
    makes that class of bug structurally impossible rather than something you
    have to remember. Set `as_of` as the simulation advances.
    """

    def __init__(self, store: SharadarStore, as_of: date, adjusted: bool = True):
        self._inner = SharadarHistory(store, adjusted)
        self.as_of = as_of

    def get_history(self, symbol: str, start: date, end: date,
                    interval: str = "daily") -> list[dict]:
        return self._inner.get_history(symbol, start, min(end, self.as_of), interval)

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        out = []
        for s in symbols:
            p = self._inner.store.price_on(s, self.as_of, adjusted=False)
            if p:
                out.append({"symbol": s, "last": p, "close": p})
        return out
