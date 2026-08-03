"""
Decision logic — what gets the expensive Opus dive, what fires an alert,
and the guardrails that keep cost and bad data from causing damage.
"""

from datetime import timedelta
import numpy as np
import config as C


# ---------------------------------------------------------------------------
#  Deep-dive eligibility
# ---------------------------------------------------------------------------

def deep_dive_eligible(ticker, in_top_today, last_dive_date, first_listed_date,
                       today, major_event=False):
    """
    Dive if:
      - a MAJOR EVENT fired (always, even for a known name), OR
      - the name is in today's top list AND wasn't dived in the last 30 days, OR
      - it's been continuously listed and its last dive is older than the staleness window.
    A name that dropped out and returned within 30 days reuses its prior analysis.
    """
    if major_event:
        return True, "major_event"
    if not in_top_today:
        return False, "not_in_top"
    if last_dive_date is None:
        return True, "new_entrant"
    age = (today - last_dive_date).days
    if age >= C.STALENESS_REFRESH_DAYS:
        return True, "staleness_refresh"
    if age >= C.DIVE_MEMORY_DAYS:
        return True, "memory_expired"
    return False, f"dived_{age}d_ago"


# ---------------------------------------------------------------------------
#  Major-event detection
# ---------------------------------------------------------------------------

def detect_major_events(d, prior_rank=None, current_rank=None):
    """Return a list of event strings. Drives both alerts and dive-overrides."""
    events = []

    # 1) large single open-market insider buy
    for t in (d.get("insider_transactions") or []):
        if t.get("code") == "P" and float(t.get("value_usd") or 0) >= C.INSIDER_ALERT_USD:
            events.append(f"insider_buy_${int(t['value_usd']):,}")

    # 2) material 8-K filing
    for item in (d.get("recent_8k_items") or []):
        if item in C.EVENT_8K_TYPES:
            events.append(f"8-K item {item}")

    # 3) abnormal price+volume move (both must spike)
    pz, vz = d.get("price_zscore"), d.get("volume_zscore")
    if pz is not None and vz is not None and abs(pz) >= C.ABNORMAL_MOVE_SIGMA and vz >= C.ABNORMAL_MOVE_SIGMA:
        events.append(f"abnormal_move (price z={pz:.1f}, vol z={vz:.1f})")

    # 4) broke into the top 3
    if current_rank is not None and current_rank <= 3 and (prior_rank is None or prior_rank > 3):
        events.append("entered_top_3")

    return events


# ---------------------------------------------------------------------------
#  Alert throttle
# ---------------------------------------------------------------------------

class AlertThrottle:
    """Caps alerts per name per rolling week to keep the channel readable."""
    def __init__(self, recent_alerts):
        # recent_alerts: list of (ticker, datetime)
        self._recent = list(recent_alerts)

    def allow(self, ticker, now):
        cutoff = now - timedelta(days=7)
        count = sum(1 for tk, ts in self._recent if tk == ticker and ts >= cutoff)
        if count >= C.MAX_ALERTS_PER_NAME_PER_WEEK:
            return False
        self._recent.append((ticker, now))
        return True


# ---------------------------------------------------------------------------
#  Cost circuit breaker
# ---------------------------------------------------------------------------

class CostBreaker:
    """Hard daily cap on AI spend. Stops diving (and signals an alert) when hit."""
    def __init__(self, spent_today=0.0):
        self.spent = float(spent_today)

    def can_dive(self):
        return (self.spent + C.EST_COST_PER_DIVE) <= C.MAX_DAILY_AI_SPEND

    def record(self, actual_cost):
        self.spent += float(actual_cost)

    @property
    def tripped(self):
        return self.spent >= C.MAX_DAILY_AI_SPEND


# ---------------------------------------------------------------------------
#  Data-health check
# ---------------------------------------------------------------------------

def health_check(universe_size, max_price_age_hours=None, feed_errors=0,
                 attempted=None):
    """
    Returns (ok, reasons). If not ok, skip posting and alert instead of quietly
    publishing garbage.

    THE GATE USED TO ABORT EVERY RUN. It was `if feed_errors > 0`, evaluated
    over ~13,000 tickers x 2 external feeds (SEC EDGAR + Stooq). Zero errors
    across 26,000 network calls is not an achievable target — one timeout, one
    rate-limit, one delisted ticker, and the entire day was skipped. With
    UNIVERSE_LIMIT = None by default it would have fired on the very first
    live run and every run after it.

    A health gate has to distinguish "the feed is broken" from "the internet is
    the internet." So it is now a RATE against the number of tickers actually
    attempted, with an absolute floor so a small universe cannot trip it on a
    handful of failures.

    The universe floor is likewise a rate, not a hard 500. The README
    recommends seeding from IWM + IJR holdings (~2,600 names); a curated list
    under 500 is a legitimate configuration and the old check called it broken.
    Pass `attempted` so the ratio is meaningful; without it we fall back to the
    absolute floor only.
    """
    reasons = []

    if attempted:
        yield_rate = universe_size / attempted
        if yield_rate < C.MIN_UNIVERSE_YIELD:
            reasons.append(
                f"only {universe_size}/{attempted} tickers produced usable data "
                f"({yield_rate:.0%}, floor {C.MIN_UNIVERSE_YIELD:.0%}) — feed likely broken")
        err_rate = (feed_errors / attempted) if attempted else 0.0
        if feed_errors > C.MAX_FEED_ERRORS_ABSOLUTE and err_rate > C.MAX_FEED_ERROR_RATE:
            reasons.append(
                f"{feed_errors}/{attempted} feed errors ({err_rate:.1%}, "
                f"limit {C.MAX_FEED_ERROR_RATE:.0%}) — feed likely degraded")
    else:
        # No denominator supplied: fall back to an absolute floor only.
        if universe_size < C.MIN_UNIVERSE_ABSOLUTE:
            reasons.append(
                f"universe too small ({universe_size} < {C.MIN_UNIVERSE_ABSOLUTE})")

    if universe_size == 0:
        reasons.append("no usable tickers at all")

    if max_price_age_hours is not None and max_price_age_hours > C.MAX_PRICE_AGE_HOURS:
        reasons.append(f"prices stale ({max_price_age_hours:.0f}h old, "
                       f"limit {C.MAX_PRICE_AGE_HOURS}h)")

    return (len(reasons) == 0), reasons


# ---------------------------------------------------------------------------
#  Day-over-day: what changed + rank trajectory
# ---------------------------------------------------------------------------

def rank_changes(today_ranks, yesterday_ranks):
    """
    today_ranks / yesterday_ranks: {ticker: rank}. Returns added, dropped, and
    climbers (names whose rank improved by >= 2 places).
    """
    today_set, yest_set = set(today_ranks), set(yesterday_ranks)
    added = sorted(today_set - yest_set, key=lambda t: today_ranks[t])
    dropped = sorted(yest_set - today_set, key=lambda t: yesterday_ranks[t])
    climbers = []
    for t in today_set & yest_set:
        delta = yesterday_ranks[t] - today_ranks[t]   # positive = moved up
        if delta >= 2:
            climbers.append((t, delta))
    climbers.sort(key=lambda x: -x[1])
    return {"added": added, "dropped": dropped, "climbers": climbers}
