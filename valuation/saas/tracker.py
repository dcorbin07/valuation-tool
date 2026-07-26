"""
Log the user-facing picks into the live track record.

Two "paper portfolios" accrue forward, survivorship-free:
  * hot10   — the daily top-10 hot stocks (by hot score).
  * options — the screaming-buy options signals (tracked by the underlying's
              forward return, i.e. signal accuracy, not option P&L).
The Edge Lab's track.update_returns/summary then measure realized returns vs SPY.
"""
from __future__ import annotations

import datetime as _dt

from ..edge import track


def log_hot(store, scan_date, rows, cfg=None, top=10):
    from ..config import CONFIG
    cfg = cfg or CONFIG
    try:
        picks = sorted([r for r in rows if r.get("ticker")],
                       key=lambda r: r.get("rank") or 999)[:top]
        if picks:
            track.log_picks(store, "hot10", scan_date, [r["ticker"] for r in picks])
    except Exception:
        pass
    # Update the paper account (entries/exits by the sell rules).
    try:
        from ..edge import positions
        positions.update_positions(store, "hot10", scan_date, rows,
                                   top_n=cfg.paper_top_n, min_hold_days=cfg.paper_min_hold_days,
                                   max_hold_days=cfg.paper_max_hold_days, exit_score=cfg.paper_exit_score)
    except Exception:
        pass


def log_options(store, rows, min_score, day=None):
    try:
        from .notify import screaming_buys
        picks = screaming_buys(rows, min_score)
        if picks:
            track.log_picks(store, "options", day or _dt.date.today().isoformat(),
                            [r["ticker"] for r in picks])
    except Exception:
        pass
