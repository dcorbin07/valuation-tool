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
"""


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or _DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
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
