"""
Market-regime filter — a simple broad-market trend gate.

Research basis (Man Group and others): adding a layer that reduces exposure when
the broad market trend turns negative reduces drawdown — you give up some
turning-point upside, but you avoid sitting through (or shorting into) sharp
adverse moves. The cost is more turnover.

We implement the simplest robust version: is a broad-market proxy (default SPY)
above its own long moving average?
  - ABOVE its MA  → market is in an UPTREND  → "risk-on"
  - BELOW its MA  → market is in a DOWNTREND → "risk-off"

How each bot uses it (kept deliberately light):
  - Momentum bot: in an uptrend, suppress SHORTS (don't short individual names
    into a rising market, where short squeezes and reversals hurt most). In a
    downtrend, shorts are allowed.
  - Trend bot: in a downtrend, the bot can de-risk (the orchestrator decides how
    — e.g. skip new longs). This is a gate the bot can consult, not a forced
    action, so each bot stays in control of its own behavior.

This is a filter, not a forecast. It doesn't predict; it just classifies the
current regime so the bots can avoid their worst environments.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    RISK_ON = "risk_on"        # broad market in uptrend
    RISK_OFF = "risk_off"      # broad market in downtrend
    UNKNOWN = "unknown"        # not enough data to tell


@dataclass(frozen=True)
class RegimeConfig:
    proxy_symbol: str = "SPY"      # broad-market proxy
    ma_window_days: int = 200      # classic 200-day trend filter
    min_bars_required: int = 100


def classify_regime_from_closes(closes: list[float], config: RegimeConfig) -> MarketRegime:
    """Pure classification from a list of daily closes (oldest first)."""
    clean = [c for c in closes if c is not None and c > 0]
    n = len(clean)
    if n < config.min_bars_required:
        return MarketRegime.UNKNOWN
    win = min(config.ma_window_days, n)
    ma = sum(clean[-win:]) / win
    last = clean[-1]
    return MarketRegime.RISK_ON if last >= ma else MarketRegime.RISK_OFF


class RegimeFilter:
    """Fetches the proxy's history and classifies the current market regime."""

    def __init__(self, config: RegimeConfig, tradier):
        self.config = config
        self.tradier = tradier

    def current_regime(self, today: Optional[date] = None) -> MarketRegime:
        today = today or date.today()
        start = today - timedelta(days=int(self.config.ma_window_days * 1.7) + 30)
        try:
            bars = self.tradier.get_history(
                self.config.proxy_symbol, start=start, end=today, interval="daily")
        except Exception as e:
            logger.warning("Regime filter: history fetch failed for %s: %s; UNKNOWN.",
                           self.config.proxy_symbol, e)
            return MarketRegime.UNKNOWN
        closes = []
        for b in bars:
            c = b.get("close")
            try:
                if c is not None:
                    closes.append(float(c))
            except (TypeError, ValueError):
                continue
        regime = classify_regime_from_closes(closes, self.config)
        logger.info("Market regime (%s vs %d-day MA): %s",
                    self.config.proxy_symbol, self.config.ma_window_days, regime.value)
        return regime
