"""
Market calendar and clock.

Two responsibilities:
  1. Decide whether the US equity options market is open right now (or on a
     given date), accounting for weekends and holidays.
  2. Provide the canonical "now" in US/Eastern so scheduling is timezone-correct
     regardless of where the bot runs (your laptop, a cloud box in another
     region, etc.).

Holiday handling: we ship a hard-coded list of US market holidays for
2026-2027. This avoids a dependency on pandas_market_calendars (heavy) or a
live API (fragile). The list needs updating annually — there's a clear comment
and the orchestrator logs a warning if "today" is past the last known holiday
year, so it won't silently run on a holiday in an un-updated year.

The orchestrator ALSO defers to Tradier's own /markets/clock endpoint as the
source of truth for intraday open/closed state. This module is the belt; the
Tradier clock is the suspenders. We use both.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

# US equity market regular session hours (Eastern).
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

# US market holidays. UPDATE ANNUALLY. Sources: NYSE/Nasdaq holiday calendars.
# Half-days (early close at 1pm ET) are listed separately; we treat them as
# open for our purposes since we trade well before close.
_MARKET_HOLIDAYS: set[date] = {
    # 2026
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # MLK Jr. Day
    date(2026, 2, 16),   # Washington's Birthday
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
    # 2027
    date(2027, 1, 1),    # New Year's Day
    date(2027, 1, 18),   # MLK Jr. Day
    date(2027, 2, 15),   # Washington's Birthday
    date(2027, 3, 26),   # Good Friday
    date(2027, 5, 31),   # Memorial Day
    date(2027, 6, 18),   # Juneteenth (observed)
    date(2027, 7, 5),    # Independence Day (observed)
    date(2027, 9, 6),    # Labor Day
    date(2027, 11, 25),  # Thanksgiving
    date(2027, 12, 24),  # Christmas (observed)
}

_LAST_KNOWN_HOLIDAY_YEAR = 2027


def now_eastern() -> datetime:
    """Current time in US/Eastern."""
    return datetime.now(EASTERN)


def is_market_holiday(d: date) -> bool:
    """True if `d` is a known US market holiday."""
    if d.year > _LAST_KNOWN_HOLIDAY_YEAR:
        logger.warning(
            "Date %s is past the last known holiday year (%d). Holiday list "
            "needs updating in orchestrator/calendar.py — treating as a "
            "non-holiday, which may be wrong.",
            d, _LAST_KNOWN_HOLIDAY_YEAR,
        )
    return d in _MARKET_HOLIDAYS


def is_trading_day(d: date) -> bool:
    """True if `d` is a weekday and not a holiday."""
    if d.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    return not is_market_holiday(d)


def is_market_open(dt: datetime | None = None) -> bool:
    """
    True if the regular session is open at `dt` (default: now Eastern).

    This is the local calculation. The orchestrator cross-checks against
    Tradier's /markets/clock for the authoritative answer.
    """
    dt = dt or now_eastern()
    # Ensure we're comparing in Eastern
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=EASTERN)
    dt_eastern = dt.astimezone(EASTERN)

    if not is_trading_day(dt_eastern.date()):
        return False
    return MARKET_OPEN <= dt_eastern.time() <= MARKET_CLOSE


def describe_market_state(dt: datetime | None = None) -> str:
    """Human-readable market state for logging."""
    dt = dt or now_eastern()
    dt_eastern = dt.astimezone(EASTERN) if dt.tzinfo else dt.replace(tzinfo=EASTERN)
    d = dt_eastern.date()
    if d.weekday() >= 5:
        return f"Weekend ({d.strftime('%A')}) — market closed"
    if is_market_holiday(d):
        return f"Market holiday ({d.isoformat()}) — market closed"
    t = dt_eastern.time()
    if t < MARKET_OPEN:
        return f"Pre-market ({t.strftime('%H:%M')} ET) — opens at 09:30"
    if t > MARKET_CLOSE:
        return f"After-hours ({t.strftime('%H:%M')} ET) — closed at 16:00"
    return f"Market open ({t.strftime('%H:%M')} ET)"
