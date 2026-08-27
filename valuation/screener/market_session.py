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

    LA14 — THE SET NOW CONTAINS ONLY DATES IN `year`, AND DROPPING THE STRAY IS THE
    FACTUALLY CORRECT NYSE RULE, NOT MERELY TIDINESS. `_observed` moves a Saturday holiday to
    the preceding Friday, so a Saturday New Year's Day became 31 December of `year - 1`:
    measured, `market_holidays(2028)` contained `2027-12-31` and `market_holidays(2033)`
    contained `2032-12-31`.

    The NYSE does **not** close on 31 December when 1 January falls on a Saturday — the
    Saturday-to-Friday rollback is not applied across the year boundary for New Year's Day — so
    the right answer is that the holiday is not observed at all, which is what filtering gives.
    `market_holidays(2027)` correctly does not gain 2027-12-31 either.

    It was inert for `is_trading_day`, which asks `market_holidays(d.year)` and so never saw the
    stray, and inert *correctly* for the same reason. The exposure is to any caller that
    ITERATES the set rather than testing membership: it would receive a date outside the year it
    asked for, while the year that date belongs to silently lacked it. Nothing iterates it today
    — this closes the hole before something does.
    """
    return {h for h in _holidays_unfiltered(year) if h.year == year}


def _holidays_unfiltered(year: int) -> set:
    """The raw observed dates, before the year filter. Split out so LA14's filter is visible
    and testable rather than folded into the set comprehension it corrects."""
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


def trading_days_between(start: _dt.date, end: _dt.date, *, inclusive_start: bool = True) -> int:
    """How many trading days ELAPSED from `start` to `end`. THE elapsed-time primitive.

    Added for LA3. `index_track.summarize` annualised on `len(series)` — the number of rows the
    recorder wrote — while the recorder was missing 71% of its days, so a missing day silently
    became a multi-day "daily" return and the published alpha was over-annualised by the ratio
    of elapsed days to recorded rows. Rows are the right denominator for a GATE ("have we
    recorded enough to say anything?") and the wrong one for an EXPONENT ("over how long did
    this return accrue?"), and those are different questions.

    It lives here, beside `is_trading_day`, rather than in either caller, because
    `valuation/edge/track_meter.py` already has a private `_trading_days` walking the same
    calendar. Two implementations of "which days should have a row" is precisely the
    two-sources-of-truth class the audit is full of; `tests/test_screener.py` pins the two to
    agree so they cannot drift apart.

    `inclusive_start=False` counts the half-open interval (start, end], which is what a series
    of cumulative-since-inception levels needs: inception is day 0 and carries a return of zero
    by definition, so the first recorded row is day 1.
    """
    if start is None or end is None or end < start:
        return 0
    n, d = 0, start
    while d <= end:
        if (inclusive_start or d > start) and is_trading_day(d):
            n += 1
        d += _dt.timedelta(days=1)
    return n


def last_closed_session(now: Optional[_dt.datetime] = None) -> Optional[_dt.date]:
    """The most recent session whose close is IN. Never a day that has not closed.

    THE DEFECT THIS EXISTS FOR, MEASURED ON THE SERVICE 2026-08-27. The track-row cron is
    scheduled for the evening ET, comfortably after the close. GitHub's scheduler delayed it
    past midnight and it ran at **00:58 ET** — at which point `session_state` reported the new
    calendar day, that day had obviously not closed, and the door refused with a 422 that was
    *correct on its own terms*: "the session has not closed yet (00:58 ET; waiting for 16:15
    ET)". The guard was doing its job. **The TARGET was wrong.** The run had been asked to mark
    TODAY, which cannot have closed, instead of YESTERDAY, which had — so it could only ever
    refuse, and the bound track silently lost a row it should have had.

    A delayed job must still record the session it was scheduled for. So the question a writer
    asks is not *"has today closed?"* but *"what is the last session that closed?"*, and those
    differ for exactly the eight hours between midnight and the close.

    Walks backwards from the current ET date:

        * a trading day AT OR AFTER the settle cutoff -> that day
        * anything else (before the cutoff, a weekend, a holiday) -> the previous trading day

    Returns `None` only if no trading day is found within a fortnight, which no real calendar
    produces; it is a bound rather than a behaviour.
    """
    n = now or now_et()
    d = n.date()
    cutoff = _dt.time(CLOSE_HOUR, SETTLE_MINUTES)
    # Today counts ONLY if it is a trading day whose close has actually passed. Every other
    # case falls through to the walk, which is what makes this incapable of naming an unclosed
    # session -- the property the intraday guard depends on.
    if is_trading_day(d) and n.time() >= cutoff:
        return d
    for _ in range(14):
        d -= _dt.timedelta(days=1)
        if is_trading_day(d):
            return d
    return None


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
