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


def _vendor_close(ticker):
    """The latest close from the price vendor, for a held name today's scan skipped. None if
    unpriced. Only ever called for open positions absent from the scan (a handful a day)."""
    from ..screener.prices import close_series
    d, c = close_series(ticker, days=10)
    return float(c[-1]) if c else None


def log_hot(store, scan_date, rows, cfg=None, top=10, price_fn=_vendor_close):
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
                                   max_hold_days=cfg.paper_max_hold_days, exit_score=cfg.paper_exit_score,
                                   coverage_gap_days=cfg.paper_coverage_gap_days, exit_band=cfg.paper_exit_band,
                                   price_fn=price_fn)
    except Exception:
        pass


def log_options(store, rows, min_score, day=None, run_time=None):
    """E10 -- the refusal is RETURNED rather than dropped.

    This used to date a row `today()` with no calendar check, so a scan on Labor Day
    2026-09-07 logged picks for a session that never happened. `track.log_picks` refuses that
    now and returns the reason; returning it here means a caller that wants to know can tell
    a skip from a write. The bare `except` stays -- logging a pick must never break a scan --
    but it no longer hides the one outcome that is not an error.
    """
    try:
        from .notify import screaming_buys
        picks = screaming_buys(rows, min_score)
        if picks:
            return track.log_picks(store, "options", day or _session_date(run_time),
                                   [r["ticker"] for r in picks])
        return {"written": False, "n": 0, "reason": "no screaming buys in this scan"}
    except Exception:
        return None


def _session_date(run_time=None) -> str:
    """The trading SESSION this run's data belongs to.

    ITEM 20 CORRECTED MY OWN FIRST REPAIR. That one returned `now_et().date()` and let
    `track.log_picks` REFUSE a non-trading day. Correct for a holiday scan and wrong here:
    GitHub delivers these ingests 3-5 hours late, so a Friday-evening ET run arrives after
    00:00 UTC Saturday, and refusing it loses Friday's picks ENTIRELY -- Monday logs Monday's
    picks, never Friday's. It also made `test_tracker_logs_and_summary` calendar-dependent,
    which is what failed the land gate at 01:50 UTC on Saturday 2026-10-03.

    `market_session.session_date` answers the right question: the most recent trading day on or
    before the run's AMERICA/NEW_YORK date. `run_time` is passed through from the ingest, and
    is interpreted as UTC when naive because that is what both producers emit.
    """
    from ..screener.market_session import session_date
    d = session_date(run_time)
    if d is not None:
        return d.isoformat()
    # No trading day within a fortnight is not a real calendar; fall through to the ET date
    # rather than invent one, and let the writer's own guard have the last word.
    return _old_session_date()


def _old_session_date() -> str:
    """The ET calendar date. A LAST RESORT ONLY, reached when the calendar finds no trading day
    within a fortnight -- which no real calendar produces.

    **THE FINDING THIS RECORDS STANDS; ITS CONCLUSION WAS SUPERSEDED BY ITEM 20.** The original
    defect is real and worth keeping: this function's predecessor returned `_dt.date.today()`,
    and both production call sites run in a container on **UTC**, so an intraday scan firing
    after 20:00 ET is already the next calendar day in UTC and a Friday-evening run dated its
    picks **Saturday** -- a row for a session that does not exist. It surfaced on a CI runner
    rather than in review, because the land gate ran at 01:56 UTC on a Saturday and
    `test_tracker_logs_and_summary` went red while passing locally. **A clock-dependent test is
    the cheapest possible place to find a clock-dependent bug.**

    **WHAT WAS WRONG WAS MY REASONING ABOUT THE REMEDY.** I argued here that
    `last_closed_session()` *"would file a weekend run under Friday, which is a different and
    wrong thing -- it would invent a second Friday row"*, and chose the ET calendar date plus a
    refusal. **That loses the row.** GitHub delivers these ingests 3-5 hours late, so Friday's
    ET evening arrives on Saturday UTC; refusing it drops Friday's picks for good, since Monday
    logs Monday's. And the second-row worry is answered by `save_track_picks` being
    `INSERT OR IGNORE`.

    The shipped answer is `market_session.session_date` -- the most recent trading day on or
    before the run's ET date -- which is neither of the two things I weighed: it has no
    time-of-day cutoff, so an intraday run at 14:24 ET still belongs to that day's session.
    """
    from ..screener.market_session import now_et
    return now_et().date().isoformat()
