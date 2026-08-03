"""
Staleness — how old is the thing we are about to show someone.

This exists because of a specific failure: the scheduled scan stopped running on 2026-07-29
and the site kept serving that snapshot, undated and unqualified, for four days. Nothing was
broken from the outside; the numbers just quietly stopped being about today. Stale data
presented as fresh is worse than no data, because the reader acts on it.

So every surface that shows scan-derived numbers carries one of these blocks, and the rule
is: **age is measured in TRADING days, and anything over one trading day old says so.**

Weekends are the reason for trading days rather than calendar days. A Friday-evening scan
read on Sunday is perfectly current — flagging it as two days stale would train the reader
to ignore the badge, which is how staleness warnings stop working.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

# Age in TRADING days -> label. A scan runs after each weekday close, so "yesterday's close"
# is the freshest anything can be during a trading day.
WARN_AFTER = 2          # 2 trading days old: say so, quietly
STALE_AFTER = 3         # 3+: prominent warning; something is wrong with the pipeline


def trading_days_between(start: _dt.date, end: _dt.date) -> int:
    """Weekdays from start to end, exclusive of start. Holidays are not modelled — the cost
    of being one day generous around Thanksgiving is far lower than the cost of crying wolf."""
    if end <= start:
        return 0
    n, d = 0, start
    while d < end:
        d += _dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def _parse(date_str) -> Optional[_dt.date]:
    if not date_str:
        return None
    try:
        return _dt.date.fromisoformat(str(date_str)[:10])
    except (TypeError, ValueError):
        return None


def status(as_of, today: _dt.date = None, label: str = "data") -> dict:
    """Freshness of something dated `as_of` (an ISO date or datetime string).

    Returns a block the UI renders verbatim. `level` is one of fresh | warn | stale |
    unknown; `stale` is the boolean for "do not present this as current".
    """
    today = today or _dt.date.today()
    d = _parse(as_of)
    if d is None:
        return {"as_of": None, "age_trading_days": None, "level": "unknown", "stale": True,
                "label": label,
                "message": f"No {label} timestamp — treat anything shown here as undated."}

    age = trading_days_between(d, today)
    if age >= STALE_AFTER:
        level, stale = "stale", True
        msg = (f"⚠ This {label} is from {d.isoformat()} — {age} trading days old. The "
               f"scheduled update has not run. Do not treat it as current.")
    elif age >= WARN_AFTER:
        level, stale = "warn", True
        msg = f"This {label} is from {d.isoformat()} ({age} trading days old)."
    else:
        level, stale = "fresh", False
        msg = f"As of {d.isoformat()} ({'today' if age == 0 else 'last close'})."
    return {"as_of": d.isoformat(), "age_trading_days": age, "level": level, "stale": stale,
            "label": label, "message": msg}
