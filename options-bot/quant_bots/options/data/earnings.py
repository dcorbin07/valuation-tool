"""
Earnings calendar.

Wraps yfinance to fetch next earnings date per symbol. yfinance is free and
key-less but has known reliability issues:

- Yahoo occasionally changes their HTML/API; yfinance breaks for a few days
  until upstream patches.
- A small fraction of tickers have missing or stale earnings data.
- Rate limiting kicks in if you hammer it (we add a small delay).

We handle these gracefully: any failure returns None, and the screener treats
None as "unknown — don't filter on earnings." That's the conservative default
for paper trading. When we eventually move to a paid earnings data source
(Polygon, Finnhub, FMP), only this module changes.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


class EarningsCalendar:
    """
    Simple per-process cache around yfinance earnings lookups.

    The cache is in-memory only — re-running the bot fetches fresh data.
    That's intentional: a stale earnings date is worse than a fresh fetch,
    and at one call per ticker per day the cost is reasonable.

    `unknown_means_safe` controls how `has_earnings_in_window` treats lookup
    failures:
      - True  -> tickers with unknown earnings are NOT filtered (let through)
      - False -> tickers with unknown earnings ARE filtered (dropped)
    Default True is the right call for paper trading; we don't want to drop a
    third of the universe because yfinance is having a bad day.
    """

    def __init__(
        self,
        unknown_means_safe: bool = True,
        request_delay_secs: float = 0.05,
    ):
        self._cache: dict[str, Optional[date]] = {}
        self.unknown_means_safe = unknown_means_safe
        self.request_delay_secs = request_delay_secs

    def get_next_earnings(self, symbol: str) -> Optional[date]:
        """
        Return the next earnings date for `symbol`, or None if unknown.

        None is returned for any of:
          - Symbol not found by yfinance
          - Earnings calendar empty (e.g., for ETFs)
          - yfinance import or network failure
          - Earnings date in an unexpected type/format
        """
        if symbol in self._cache:
            return self._cache[symbol]

        result: Optional[date] = None
        try:
            # Import inside the method so the entire process doesn't break
            # if yfinance isn't installed and the screener was configured to
            # skip earnings filtering. (The screener's __init__ also doesn't
            # construct this class unless needed.)
            import yfinance as yf

            time.sleep(self.request_delay_secs)
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar

            # In current yfinance versions calendar is a dict like:
            #   {'Earnings Date': [datetime.date(2025, 7, 28), ...],
            #    'Earnings Average': 1.23, 'Earnings Low': 1.10, ...}
            # In older versions it was a DataFrame. Both are handled below.
            earnings_dates = None
            if isinstance(cal, dict):
                earnings_dates = cal.get("Earnings Date")
            elif cal is not None and hasattr(cal, "loc"):
                try:
                    earnings_dates = cal.loc["Earnings Date"].tolist()
                except (KeyError, AttributeError):
                    earnings_dates = None

            if earnings_dates:
                first = earnings_dates[0]
                if isinstance(first, datetime):
                    result = first.date()
                elif isinstance(first, date):
                    result = first
                # else: unexpected type, leave result as None

        except ImportError:
            logger.error(
                "yfinance is not installed. Either install it "
                "(pip install yfinance) or disable earnings filtering "
                "in the screener config."
            )
        except Exception as e:
            # yfinance throws all manner of exceptions — JSON decode errors,
            # network errors, attribute errors on unexpected response shapes.
            # We log at debug level because some failures are expected (e.g.,
            # ETFs have no earnings) and warning would be too noisy.
            logger.debug("Could not fetch earnings for %s: %s", symbol, e)

        self._cache[symbol] = result
        return result

    def has_earnings_in_window(
        self, symbol: str, window_start: date, window_end: date
    ) -> bool:
        """
        Return True if the next earnings date falls inside [start, end]
        (inclusive). If the earnings date is unknown, defer to
        `unknown_means_safe` — True returns False (don't filter), False
        returns True (filter out).
        """
        next_earnings = self.get_next_earnings(symbol)
        if next_earnings is None:
            return not self.unknown_means_safe
        return window_start <= next_earnings <= window_end
