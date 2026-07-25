"""
User + subscription store (SQLite, standard-library only).

Deliberately dependency-light so it runs and tests anywhere. For production scale
you can swap this for Postgres/SQLAlchemy (see SAAS_RUNBOOK.md) — the rest of the
SaaS layer only talks to this thin interface, so nothing else changes.

Passwords are hashed with werkzeug (ships with Flask). Subscription state mirrors
Stripe: `tier` (free/pro/premium) + `subscription_status` (active/canceled/…).
"""
from __future__ import annotations

import os
import sqlite3
import datetime as _dt
from contextlib import contextmanager

from werkzeug.security import generate_password_hash, check_password_hash

TIERS = ("free", "pro", "premium")


def _sqlite_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url[len("sqlite:///"):]
    return database_url  # treat as a plain path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    subscription_status TEXT DEFAULT 'none',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TEXT NOT NULL,
    email_opt_in INTEGER NOT NULL DEFAULT 1,
    alerts_email_opt_in INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS watchlist (
    user_id INTEGER, ticker TEXT, added_at TEXT,
    PRIMARY KEY (user_id, ticker)
);
CREATE TABLE IF NOT EXISTS usage (
    user_id INTEGER, day TEXT, action TEXT, count INTEGER,
    PRIMARY KEY (user_id, day, action)
);
"""


class UserStore:
    def __init__(self, database_url: str = "sqlite:///data/app.db"):
        self.path = _sqlite_path(database_url)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)
            # Lightweight migration for existing databases.
            cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
            if "alerts_email_opt_in" not in cols:
                c.execute("ALTER TABLE users ADD COLUMN alerts_email_opt_in INTEGER NOT NULL DEFAULT 0")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- accounts ----
    def create_user(self, email: str, password: str):
        email = email.strip().lower()
        if not email or "@" not in email:
            raise ValueError("Enter a valid email address.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        with self._conn() as c:
            if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                raise ValueError("An account with that email already exists.")
            c.execute("INSERT INTO users (email,password_hash,tier,created_at) VALUES (?,?,?,?)",
                      (email, generate_password_hash(password), "free", _dt.datetime.utcnow().isoformat()))
        return self.get_by_email(email)

    def verify(self, email: str, password: str):
        u = self.get_by_email(email)
        if u and check_password_hash(u["password_hash"], password):
            return u
        return None

    def get_by_email(self, email: str):
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        return dict(r) if r else None

    def get_by_id(self, uid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None

    def get_by_stripe_customer(self, customer_id):
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE stripe_customer_id=?", (customer_id,)).fetchone()
        return dict(r) if r else None

    # ---- subscription ----
    def set_subscription(self, user_id, tier=None, status=None,
                         stripe_customer_id=None, stripe_subscription_id=None):
        sets, vals = [], []
        for col, val in [("tier", tier), ("subscription_status", status),
                         ("stripe_customer_id", stripe_customer_id),
                         ("stripe_subscription_id", stripe_subscription_id)]:
            if val is not None:
                sets.append(f"{col}=?"); vals.append(val)
        if not sets:
            return
        vals.append(user_id)
        with self._conn() as c:
            c.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)

    def link_stripe_customer(self, user_id, customer_id):
        self.set_subscription(user_id, stripe_customer_id=customer_id)

    # ---- watchlist ----
    def watchlist(self, user_id):
        with self._conn() as c:
            return [r["ticker"] for r in c.execute(
                "SELECT ticker FROM watchlist WHERE user_id=? ORDER BY added_at", (user_id,)).fetchall()]

    def add_watch(self, user_id, ticker):
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO watchlist VALUES (?,?,?)",
                      (user_id, ticker.upper(), _dt.datetime.utcnow().isoformat()))

    def remove_watch(self, user_id, ticker):
        with self._conn() as c:
            c.execute("DELETE FROM watchlist WHERE user_id=? AND ticker=?", (user_id, ticker.upper()))

    def subscribers_opted_in(self):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM users WHERE email_opt_in=1 AND tier IN ('pro','premium')").fetchall()]

    # ---- alert opt-in (default OFF — users must opt in, can opt out anytime) ----
    def set_alerts_opt_in(self, user_id, on: bool):
        with self._conn() as c:
            c.execute("UPDATE users SET alerts_email_opt_in=? WHERE id=?", (1 if on else 0, user_id))

    def alert_subscribers(self):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM users WHERE alerts_email_opt_in=1").fetchall()]

    # ---- usage metering (free-tier daily limits) ----
    def bump_usage(self, user_id, action):
        day = _dt.date.today().isoformat()
        with self._conn() as c:
            c.execute("""INSERT INTO usage VALUES (?,?,?,1)
                         ON CONFLICT(user_id,day,action) DO UPDATE SET count=count+1""",
                      (user_id, day, action))
            r = c.execute("SELECT count FROM usage WHERE user_id=? AND day=? AND action=?",
                          (user_id, day, action)).fetchone()
        return r["count"] if r else 1

    def usage_today(self, user_id, action):
        day = _dt.date.today().isoformat()
        with self._conn() as c:
            r = c.execute("SELECT count FROM usage WHERE user_id=? AND day=? AND action=?",
                          (user_id, day, action)).fetchone()
        return r["count"] if r else 0
