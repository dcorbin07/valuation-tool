"""
Has the US market closed yet? — the guard the scheduled paper track runs behind.

WHY THIS EXISTS. The paper-track cron is pinned to a fixed UTC time (20:45 / 20:47), but the
NYSE closes at 4:00pm *Eastern*, which is a moving target in UTC:

    EDT (mid-Mar -> early Nov, UTC-4):  20:45 UTC = 4:45pm ET   -> after the close, correct
    EST (early Nov -> mid-Mar, UTC-5):  20:45 UTC = 3:45pm ET   -> FIFTEEN MINUTES EARLY

So from the first weekend in November the cycle would have started running mid-session every
weekday: marking the index book and entering option positions against intraday prices instead
of closing prices. Nothing would error — the run would look completely normal — and the daily
marks on the one record whose entire value is being a clean, out-of-sample forward track would
quietly stop meaning what they say.

A cron time cannot express "4pm Eastern". So the schedule fires generously (twice, covering
both offsets) and THIS decides whether the run is allowed to proceed. That makes the guard,
not the crontab, the thing that has to be right — and this file is unit-tested offline while
a crontab is not.

Market holidays are handled too: on a holiday there is no closing price, so a run would mark
the book against the previous session's stale quotes and write a duplicate-priced point.
Holidays are COMPUTED rather than listed, so this does not expire in a year and quietly start
writing holiday points. Early closes (1:00pm ET, the day after Thanksgiving and Christmas Eve)
need no special case: a guard that waits for 4:00pm is still satisfied on those days.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

MARKET_TZ = "America/New_York"
CLOSE_HOUR = 16          # 4:00pm ET
# Wait a little past the bell before marking: the closing print and the consolidated tape
# settle over the first minutes after 4:00, and a mark taken at 16:00:05 can catch a
# half-formed close. The crons fire ~45 min after, so this is a floor, not the schedule.
SETTLE_MINUTES = 15


def now_et() -> _dt.datetime:
    """Current time in US market time. Falls back to naive UTC if tzdata is unavailable."""
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo(MARKET_TZ))
    except Exception:                       # pragma: no cover - only without tzdata
        return _dt.datetime.utcnow()


def _easter(year: int) -> _dt.date:
    """Gregorian Easter Sunday (Anonymous/Meeus algorithm). Good Friday is 2 days earlier."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return _dt.date(year, month, day + 1)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> _dt.date:
    """The nth `weekday` (Mon=0) of a month; n=-1 means the LAST one."""
    if n > 0:
        d = _dt.date(year, month, 1)
        offset = (weekday - d.weekday()) % 7
        return d + _dt.timedelta(days=offset + 7 * (n - 1))
    last = _dt.date(year, month, 28)
    while (last + _dt.timedelta(days=1)).month == month:
        last += _dt.timedelta(days=1)
    return last - _dt.timedelta(days=(last.weekday() - weekday) % 7)


def _observed(d: _dt.date) -> _dt.date:
    """A fixed-date holiday falling at the weekend is observed on the adjacent weekday."""
    if d.weekday() == 5:                      # Saturday -> Friday before
        return d - _dt.timedelta(days=1)
    if d.weekday() == 6:                      # Sunday -> Monday after
        return d + _dt.timedelta(days=1)
    return d


def market_holidays(year: int) -> set:
    """The NYSE full-day closures for a year.

    Computed, not hard-coded, so this keeps working after 2026. Excludes the ad-hoc closures
    (national days of mourning, hurricanes) which no rule can predict — those are rare and the
    cost of a run on one is a single duplicate-priced mark, not a corrupted book.
    """
    return {
        _observed(_dt.date(year, 1, 1)),                      # New Year's Day
        _nth_weekday(year, 1, 0, 3),                          # MLK Jr Day
        _nth_weekday(year, 2, 0, 3),                          # Washington's Birthday
        _easter(year) - _dt.timedelta(days=2),                # Good Friday
        _nth_weekday(year, 5, 0, -1),                         # Memorial Day
        _observed(_dt.date(year, 6, 19)),                     # Juneteenth
        _observed(_dt.date(year, 7, 4)),                      # Independence Day
        _nth_weekday(year, 9, 0, 1),                          # Labor Day
        _nth_weekday(year, 11, 3, 4),                         # Thanksgiving
        _observed(_dt.date(year, 12, 25)),                    # Christmas
    }


def is_trading_day(d: _dt.date) -> bool:
    return d.weekday() < 5 and d not in market_holidays(d.year)


def session_state(now: Optional[_dt.datetime] = None) -> dict:
    """Whether the current session has closed, and why not if it hasn't.

    `ok` is the single thing callers should branch on: True means "today is a trading day and
    the closing prices are in, go ahead".
    """
    n = now or now_et()
    d = n.date()
    cutoff = _dt.time(CLOSE_HOUR, SETTLE_MINUTES)
    if d.weekday() >= 5:
        return {"ok": False, "date": d.isoformat(), "reason": "weekend — the market is closed",
                "local_time": n.strftime("%H:%M")}
    if d in market_holidays(d.year):
        return {"ok": False, "date": d.isoformat(),
                "reason": "market holiday — no closing prices today",
                "local_time": n.strftime("%H:%M")}
    if n.time() < cutoff:
        return {"ok": False, "date": d.isoformat(),
                "reason": (f"the session has not closed yet ({n.strftime('%H:%M')} ET; waiting "
                           f"for {cutoff.strftime('%H:%M')} ET) — marking now would use "
                           f"intraday prices, not the close"),
                "local_time": n.strftime("%H:%M")}
    return {"ok": True, "date": d.isoformat(), "reason": "the session has closed",
            "local_time": n.strftime("%H:%M")}
