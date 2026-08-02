"""
Persistence (SQLite). Holds the universe cache, deep-dive memory, daily picks,
the track-record log (append-only, point-in-time), alert log, and spend log.

Append-only discipline on daily_picks / track_record: we NEVER retro-edit a
logged score or price, and we keep names that later delist — both are required
for the self-review to be honest rather than survivorship-biased.
"""

import sqlite3
import json
from datetime import datetime, date, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS universe (
    ticker TEXT PRIMARY KEY, sector TEXT, shares REAL,
    fundamentals_json TEXT, refreshed_at TEXT
);
CREATE TABLE IF NOT EXISTS dive_memory (
    ticker TEXT PRIMARY KEY, last_dive_date TEXT,
    first_listed_date TEXT, analysis_json TEXT
);
CREATE TABLE IF NOT EXISTS daily_picks (
    run_date TEXT, ticker TEXT, bucket TEXT, rank INTEGER,
    composite REAL, components_json TEXT, price REAL, market_cap REAL,
    PRIMARY KEY (run_date, bucket, ticker)
);
CREATE TABLE IF NOT EXISTS track_record (
    run_date TEXT, ticker TEXT, entry_price REAL,
    ret_7 REAL, ret_30 REAL, ret_90 REAL,
    bench_iwm_30 REAL, bench_ijr_30 REAL, delisted INTEGER DEFAULT 0,
    PRIMARY KEY (run_date, ticker)
);
CREATE TABLE IF NOT EXISTS alerts (
    ts TEXT, ticker TEXT, kind TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS spend (
    run_date TEXT PRIMARY KEY, ai_spend REAL
);
"""


class Store:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ---- universe cache ----
    def upsert_universe(self, ticker, sector, shares, fundamentals):
        self.db.execute(
            "INSERT OR REPLACE INTO universe VALUES (?,?,?,?,?)",
            (ticker, sector, shares, json.dumps(fundamentals),
             datetime.now(timezone.utc).isoformat()))
        self.db.commit()

    def get_universe_age_days(self, ticker, today):
        row = self.db.execute("SELECT refreshed_at FROM universe WHERE ticker=?", (ticker,)).fetchone()
        if not row:
            return None
        return (today - datetime.fromisoformat(row[0]).date()).days

    def get_cached_fundamentals(self, ticker):
        """Return the cached fundamentals dict for a ticker, or None."""
        row = self.db.execute("SELECT fundamentals_json FROM universe WHERE ticker=?", (ticker,)).fetchone()
        if not row or not row[0]:
            return None
        try:
            return json.loads(row[0])
        except (ValueError, TypeError):
            return None

    # ---- dive memory ----
    def last_dive_date(self, ticker):
        row = self.db.execute("SELECT last_dive_date FROM dive_memory WHERE ticker=?", (ticker,)).fetchone()
        return date.fromisoformat(row[0]) if row and row[0] else None

    def record_dive(self, ticker, dive_date, first_listed_date, analysis):
        self.db.execute(
            "INSERT OR REPLACE INTO dive_memory VALUES (?,?,?,?)",
            (ticker, dive_date.isoformat(),
             first_listed_date.isoformat() if first_listed_date else None,
             json.dumps(analysis)))
        self.db.commit()

    # ---- daily picks (append-only) ----
    def log_pick(self, run_date, score, price, market_cap, rank):
        self.db.execute(
            "INSERT OR REPLACE INTO daily_picks VALUES (?,?,?,?,?,?,?,?)",
            (run_date.isoformat(), score.ticker, score.bucket, rank,
             score.composite, json.dumps(score.components), price, market_cap))
        self.db.commit()

    def yesterday_ranks(self, run_date, bucket):
        rows = self.db.execute(
            "SELECT ticker, rank FROM daily_picks WHERE run_date=? AND bucket=?",
            (run_date.isoformat(), bucket)).fetchall()
        return {t: r for t, r in rows}

    # ---- track record ----
    def log_track(self, run_date, ticker, entry_price):
        self.db.execute(
            "INSERT OR IGNORE INTO track_record (run_date, ticker, entry_price) VALUES (?,?,?)",
            (run_date.isoformat(), ticker, entry_price))
        self.db.commit()

    def update_returns(self, run_date, ticker, **kw):
        cols = ", ".join(f"{k}=?" for k in kw)
        self.db.execute(f"UPDATE track_record SET {cols} WHERE run_date=? AND ticker=?",
                        (*kw.values(), run_date.isoformat(), ticker))
        self.db.commit()

    def track_count(self):
        return self.db.execute("SELECT COUNT(*) FROM track_record").fetchone()[0]

    # ---- alerts & spend ----
    def log_alert(self, ts, ticker, kind, detail):
        self.db.execute("INSERT INTO alerts VALUES (?,?,?,?)",
                        (ts.isoformat(), ticker, kind, detail))
        self.db.commit()

    def recent_alerts(self):
        return [(t, datetime.fromisoformat(ts))
                for ts, t in self.db.execute("SELECT ts, ticker FROM alerts").fetchall()]

    def spend_today(self, run_date):
        row = self.db.execute("SELECT ai_spend FROM spend WHERE run_date=?",
                              (run_date.isoformat(),)).fetchone()
        return row[0] if row else 0.0

    def set_spend(self, run_date, amount):
        self.db.execute("INSERT OR REPLACE INTO spend VALUES (?,?)",
                        (run_date.isoformat(), amount))
        self.db.commit()
