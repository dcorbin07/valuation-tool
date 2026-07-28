"""
SQLite persistence for the screener.

Caches expensive fundamentals so a weekly scan doesn't re-fetch the whole market
every run, stores dated ranked snapshots ("hot stocks of the week"), and keeps a
history so we can see what changed week over week and, later, track how past picks
performed. Everything is local; no server required.
"""
from __future__ import annotations

import json
import os
import sqlite3
import datetime as _dt
from contextlib import contextmanager

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "screener.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS universe (
    ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, industry TEXT,
    market_cap REAL, updated_at TEXT
);

-- Cached raw fundamentals/metrics per ticker (refreshed periodically).
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker TEXT PRIMARY KEY, data TEXT, updated_at TEXT
);

-- A dated scan: one row = one ticker's factors + composite on that scan date.
CREATE TABLE IF NOT EXISTS snapshot_rows (
    scan_date TEXT, ticker TEXT, name TEXT, sector TEXT, bucket TEXT,
    price REAL, market_cap REAL, hot_score REAL, composite REAL, rank INTEGER,
    z_value REAL, z_quality REAL, z_growth REAL, z_momentum REAL, z_insider REAL,
    fair_value REAL, upside REAL, extra TEXT,
    PRIMARY KEY (scan_date, ticker)
);

CREATE TABLE IF NOT EXISTS scans (
    scan_date TEXT PRIMARY KEY, universe_size INTEGER, scored INTEGER,
    provider TEXT, params TEXT, created_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_snap_date ON snapshot_rows(scan_date);
CREATE INDEX IF NOT EXISTS ix_snap_rank ON snapshot_rows(scan_date, rank);

-- Intraday signals watcher (timestamped runs).
CREATE TABLE IF NOT EXISTS intraday (
    run_time TEXT, ticker TEXT, score REAL, rank INTEGER, price REAL,
    labels TEXT, summary TEXT, detail TEXT, ai TEXT,
    PRIMARY KEY (run_time, ticker)
);
CREATE TABLE IF NOT EXISTS intraday_runs (
    run_time TEXT PRIMARY KEY, universe INTEGER, provider TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_intraday ON intraday(run_time, rank);

-- Live track record (the "paper account"): picks logged over time + realized returns.
CREATE TABLE IF NOT EXISTS track_picks (
    source TEXT, run_date TEXT, ticker TEXT, rank INTEGER,
    PRIMARY KEY (source, run_date, ticker)
);
CREATE TABLE IF NOT EXISTS track_returns (
    source TEXT, run_date TEXT, ticker TEXT, horizon INTEGER,
    fwd_ret REAL, bench_ret REAL,
    PRIMARY KEY (source, run_date, ticker, horizon)
);
"""


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or _DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)
            # De-dupe alerts to at most one per ticker per day.
            c.execute("""CREATE TABLE IF NOT EXISTS alerts_sent (
                ticker TEXT, alert_date TEXT, run_time TEXT, PRIMARY KEY(ticker, alert_date))""")
            # Paper-account positions (Track Record sell logic).
            c.execute("""CREATE TABLE IF NOT EXISTS positions (
                source TEXT, ticker TEXT, entry_date TEXT, entry_price REAL,
                exit_date TEXT, exit_price REAL, exit_reason TEXT,
                PRIMARY KEY (source, ticker, entry_date))""")
            # Migration: track last-seen so a name that drops out of coverage gets
            # closed (else delisted losers live forever → survivorship bias).
            _pcols = {r[1] for r in c.execute("PRAGMA table_info(positions)").fetchall()}
            for _col, _decl in (("last_seen_date", "TEXT"), ("last_price", "REAL")):
                if _col not in _pcols:
                    c.execute(f"ALTER TABLE positions ADD COLUMN {_col} {_decl}")
            # Self-learning audit log + adopted factor weights.
            c.execute("""CREATE TABLE IF NOT EXISTS learned_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, bucket TEXT,
                weights TEXT, stats TEXT, adopted INTEGER, note TEXT)""")

    @contextmanager
    def _conn(self):
        # timeout so concurrent writers (background track-refresh + a request) wait
        # for the lock instead of erroring with "database is locked".
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- meta ----
    def set_meta(self, key, value):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(value)))

    def get_meta(self, key, default=None):
        with self._conn() as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(r["value"]) if r else default

    # ---- fundamentals cache ----
    def cache_fundamentals(self, ticker, data):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO fundamentals VALUES (?,?,?)",
                      (ticker.upper(), json.dumps(data), _dt.datetime.utcnow().isoformat()))

    def get_cached_fundamentals(self, ticker, max_age_days=None):
        with self._conn() as c:
            r = c.execute("SELECT data, updated_at FROM fundamentals WHERE ticker=?",
                          (ticker.upper(),)).fetchone()
        if not r:
            return None
        if max_age_days is not None:
            try:
                age = (_dt.datetime.utcnow() - _dt.datetime.fromisoformat(r["updated_at"])).days
                if age > max_age_days:
                    return None
            except Exception:
                pass
        return json.loads(r["data"])

    # ---- snapshots ----
    def save_snapshot(self, scan_date, rows, provider="", params=None):
        with self._conn() as c:
            c.execute("DELETE FROM snapshot_rows WHERE scan_date=?", (scan_date,))
            for r in rows:
                c.execute("""INSERT OR REPLACE INTO snapshot_rows
                    (scan_date,ticker,name,sector,bucket,price,market_cap,hot_score,composite,rank,
                     z_value,z_quality,z_growth,z_momentum,z_insider,fair_value,upside,extra)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (scan_date, r["ticker"], r.get("name"), r.get("sector"), r.get("bucket"),
                     r.get("price"), r.get("market_cap"), r.get("hot_score"), r.get("composite"),
                     r.get("rank"), r.get("z_value"), r.get("z_quality"), r.get("z_growth"),
                     r.get("z_momentum"), r.get("z_insider"), r.get("fair_value"), r.get("upside"),
                     json.dumps(r.get("extra", {}))))
            c.execute("INSERT OR REPLACE INTO scans VALUES (?,?,?,?,?,?)",
                      (scan_date, (params or {}).get("universe_size"), len(rows), provider,
                       json.dumps(params or {}), _dt.datetime.utcnow().isoformat()))

    def latest_scan_date(self):
        with self._conn() as c:
            r = c.execute("SELECT scan_date FROM scans ORDER BY scan_date DESC LIMIT 1").fetchone()
        return r["scan_date"] if r else None

    def load_snapshot(self, scan_date=None, top=None):
        scan_date = scan_date or self.latest_scan_date()
        if not scan_date:
            return []
        q = "SELECT * FROM snapshot_rows WHERE scan_date=? ORDER BY rank ASC"
        if top:
            q += f" LIMIT {int(top)}"
        with self._conn() as c:
            rows = [dict(r) for r in c.execute(q, (scan_date,)).fetchall()]
        for r in rows:
            try:
                r["extra"] = json.loads(r["extra"]) if r.get("extra") else {}
            except Exception:
                r["extra"] = {}
        return rows

    def list_scans(self):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM scans ORDER BY scan_date DESC").fetchall()]

    # ---- intraday signals ----
    def save_intraday(self, run_time, rows, provider=""):
        with self._conn() as c:
            for r in rows:
                c.execute("""INSERT OR REPLACE INTO intraday
                    (run_time,ticker,score,rank,price,labels,summary,detail,ai)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (run_time, r["ticker"], r.get("score"), r.get("rank"), r.get("price"),
                     json.dumps(r.get("labels", [])), r.get("summary"),
                     json.dumps(r.get("detail", {})), json.dumps(r.get("ai")) if r.get("ai") else None))
            c.execute("INSERT OR REPLACE INTO intraday_runs VALUES (?,?,?,?)",
                      (run_time, len(rows), provider, _dt.datetime.utcnow().isoformat()))

    def latest_intraday_time(self):
        with self._conn() as c:
            r = c.execute("SELECT run_time FROM intraday_runs ORDER BY run_time DESC LIMIT 1").fetchone()
        return r["run_time"] if r else None

    def load_intraday(self, run_time=None, top=None):
        run_time = run_time or self.latest_intraday_time()
        if not run_time:
            return []
        q = "SELECT * FROM intraday WHERE run_time=? ORDER BY rank ASC"
        if top:
            q += f" LIMIT {int(top)}"
        with self._conn() as c:
            rows = [dict(r) for r in c.execute(q, (run_time,)).fetchall()]
        for r in rows:
            for k in ("labels", "detail", "ai"):
                try:
                    r[k] = json.loads(r[k]) if r.get(k) else ([] if k == "labels" else ({} if k == "detail" else None))
                except Exception:
                    r[k] = [] if k == "labels" else ({} if k == "detail" else None)
        return rows

    def update_intraday_ai(self, run_time, ticker, ai_text):
        with self._conn() as c:
            c.execute("UPDATE intraday SET ai=? WHERE run_time=? AND ticker=?",
                      (json.dumps(ai_text), run_time, ticker))

    # ---- alert de-dupe (one per ticker per day) ----
    def alerted_today(self, ticker, day=None) -> bool:
        day = day or _dt.date.today().isoformat()
        with self._conn() as c:
            r = c.execute("SELECT 1 FROM alerts_sent WHERE ticker=? AND alert_date=?",
                          (ticker.upper(), day)).fetchone()
        return bool(r)

    def mark_alerted(self, ticker, run_time, day=None):
        day = day or _dt.date.today().isoformat()
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO alerts_sent VALUES (?,?,?)",
                      (ticker.upper(), day, run_time))

    # ---- paper-account positions ----
    def open_position(self, source, ticker, entry_date, entry_price):
        with self._conn() as c:
            c.execute("""INSERT OR IGNORE INTO positions
                         (source,ticker,entry_date,entry_price,last_seen_date,last_price)
                         VALUES (?,?,?,?,?,?)""",
                      (source, ticker.upper(), entry_date, entry_price, entry_date, entry_price))

    def touch_position(self, source, ticker, entry_date, seen_date, price):
        """Record that an open position was still in coverage today (+ its price)."""
        with self._conn() as c:
            c.execute("""UPDATE positions SET last_seen_date=?, last_price=?
                         WHERE source=? AND ticker=? AND entry_date=? AND exit_date IS NULL""",
                      (seen_date, price, source, ticker.upper(), entry_date))

    def close_position(self, source, ticker, entry_date, exit_date, exit_price, reason):
        with self._conn() as c:
            c.execute("""UPDATE positions SET exit_date=?, exit_price=?, exit_reason=?
                         WHERE source=? AND ticker=? AND entry_date=? AND exit_date IS NULL""",
                      (exit_date, exit_price, reason, source, ticker.upper(), entry_date))

    def open_positions(self, source):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM positions WHERE source=? AND exit_date IS NULL", (source,)).fetchall()]

    def all_positions(self, source):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM positions WHERE source=? ORDER BY entry_date DESC", (source,)).fetchall()]

    # ---- self-learning (adopted factor weights + audit log) ----
    def save_learned(self, bucket, weights, stats, adopted, note):
        with self._conn() as c:
            c.execute("INSERT INTO learned_config (created_at,bucket,weights,stats,adopted,note) VALUES (?,?,?,?,?,?)",
                      (_dt.datetime.utcnow().isoformat(), bucket, json.dumps(weights),
                       json.dumps(stats or {}), 1 if adopted else 0, note or ""))

    def latest_learned_weights(self, bucket):
        with self._conn() as c:
            r = c.execute("""SELECT weights FROM learned_config WHERE bucket=? AND adopted=1
                             ORDER BY id DESC LIMIT 1""", (bucket,)).fetchone()
        if not r:
            return None
        try:
            return json.loads(r["weights"])
        except Exception:
            return None

    def learning_history(self, limit=24):
        with self._conn() as c:
            rows = [dict(r) for r in c.execute(
                "SELECT * FROM learned_config ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()]
        for r in rows:
            for k in ("weights", "stats"):
                try:
                    r[k] = json.loads(r[k]) if r.get(k) else {}
                except Exception:
                    r[k] = {}
        return rows

    # ---- live track record ----
    def save_track_picks(self, source, run_date, rows):
        with self._conn() as c:
            for r in rows:
                c.execute("INSERT OR IGNORE INTO track_picks VALUES (?,?,?,?)",
                          (source, run_date, r["ticker"].upper(), r.get("rank")))

    def all_track_picks(self, source=None):
        q = "SELECT * FROM track_picks" + ("" if source is None else " WHERE source=?")
        with self._conn() as c:
            rows = c.execute(q, () if source is None else (source,)).fetchall()
        return [dict(r) for r in rows]

    def save_track_return(self, source, run_date, ticker, horizon, fwd_ret, bench_ret):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO track_returns VALUES (?,?,?,?,?,?)",
                      (source, run_date, ticker.upper(), horizon, fwd_ret, bench_ret))

    def has_track_return(self, source, run_date, ticker, horizon):
        with self._conn() as c:
            return c.execute("SELECT 1 FROM track_returns WHERE source=? AND run_date=? AND ticker=? AND horizon=?",
                             (source, run_date, ticker.upper(), horizon)).fetchone() is not None

    def track_returns(self, source, horizon=None):
        q = "SELECT * FROM track_returns WHERE source=?" + ("" if horizon is None else " AND horizon=?")
        args = (source,) if horizon is None else (source, horizon)
        with self._conn() as c:
            return [dict(r) for r in c.execute(q, args).fetchall()]
