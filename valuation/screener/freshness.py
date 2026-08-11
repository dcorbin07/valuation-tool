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
    """Trading days from start to end, exclusive of start.

    LA7 — HOLIDAYS ARE NOW MODELLED, AND THE JUSTIFICATION FOR NOT MODELLING THEM WAS
    BACKWARDS. This used to end with: *"Holidays are not modelled — the cost of being one day
    generous around Thanksgiving is far lower than the cost of crying wolf."* Not modelling
    them counts Christmas Day as a trading day, which makes the computed age LARGER, which
    fires the badge EARLIER. That IS crying wolf. The stated reason argued for the opposite of
    what the code did. Measured before the fix: `status("2026-12-24", today=2026-12-28)`
    returned `age_trading_days: 2` for a gap containing exactly one session.

    It now delegates to `market_session`, which already computed the NYSE calendar and was
    already imported by `track_meter`. There is ONE calendar in this package again: before
    this, `market_session.trading_days_between` and this function had the SAME NAME, lived in
    sibling modules, and returned DIFFERENT answers for the same interval (1 vs 2 over
    Christmas). A reader importing "the" trading-day helper got whichever one they happened to
    reach for.

    `scripts/theme_health.py:175` still carries a private third copy (`_trading_days_between`).
    Out of scope here and reported rather than silently changed.
    """
    if not start or not end or end <= start:
        return 0
    from .market_session import trading_days_between as _elapsed
    return _elapsed(start, end, inclusive_start=False)


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
                "label": label, "as_of_is_trading_day": None,
                "message": f"No {label} timestamp — treat anything shown here as undated."}

    # LA7/LA4 — THE GUARD NOW VALIDATES ITS OWN INPUT. A snapshot dated a day the market never
    # opened cannot be "as of last close", because there was no close. Before this,
    # `status("2026-08-08", today=2026-08-10)` returned level `fresh` with the message
    # "As of 2026-08-08 (last close)." — 2026-08-08 is a Saturday, and the module whose whole
    # job is to stop stale data being presented as fresh was endorsing a session that does not
    # exist. `is_trading_day` lived one import away and was never asked.
    #
    # This is load-bearing for LA4 rather than cosmetic: LA4's misdated backup-cron snapshot is
    # exactly the input that arrived here, and this is what would have made it visible.
    #
    # DELIBERATELY NOT A NEW `level`. The vocabulary is fresh|warn|stale|unknown and
    # `app.js:1812-1815` switches on it, treating stale/unknown as red. A misdated snapshot is
    # not a dead pipeline, so it takes `warn` — a visible note rather than an alarm — and
    # carries the machine-readable `as_of_is_trading_day: False` for anything that wants to be
    # stricter. The one thing it may never be is `fresh`.
    from .market_session import is_trading_day
    on_session = is_trading_day(d)

    age = trading_days_between(d, today)
    if not on_session and age < STALE_AFTER:
        return {"as_of": d.isoformat(), "age_trading_days": age, "level": "warn", "stale": True,
                "label": label, "as_of_is_trading_day": False,
                "message": (f"This {label} is dated {d.isoformat()}, which was not a trading "
                            f"session — there was no close that day, so the date on it is "
                            f"wrong even if the numbers are current.")}
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
            "label": label, "as_of_is_trading_day": on_session, "message": msg}
