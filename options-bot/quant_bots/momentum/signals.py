"""
Cross-sectional momentum signal (Bot #3's distinctive piece).

The key contrast with the trend bot:
  - Trend (Bot #2): each instrument vs. ITS OWN history. "Is SPY above where it
    was 12 months ago?" Absolute / time-series momentum.
  - Momentum (Bot #3): instruments ranked AGAINST EACH OTHER. "Of these 1,000
    stocks, which 50 had the best trailing return?" Relative / cross-sectional
    momentum.

The classic academic construction (Jegadeesh & Titman 1993):
  - Rank all stocks by trailing return over a lookback (commonly 12 months,
    SKIPPING the most recent month — the "12-1" momentum, because the very
    recent month tends to mean-revert and adding it weakens the signal).
  - Go LONG the top decile/quintile (winners).
  - Optionally SHORT the bottom decile/quintile (losers) for a market-neutral
    long/short book.
  - Rebalance monthly.

We compute, per stock:
  - The 12-1 momentum score (return from ~12 months ago to ~1 month ago).
  - A recent volatility estimate (for the risk layer's sizing, same as trend).

Then we RANK and select: top N as longs, bottom N as shorts (configurable;
long-only is also supported by setting short_count = 0).

The per-stock score computation is pure (testable on a list of closes); the
selection/ranking is also pure (testable on a dict of scores).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


class Direction(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass(frozen=True)
class MomentumConfig:
    # 12-1 momentum: total return from `lookback_days` ago to `skip_days` ago.
    lookback_days: int = 252      # ~12 months
    skip_days: int = 21           # skip most recent ~1 month (mean reversion)
    vol_window_days: int = 63     # ~3 months for the vol estimate
    min_bars_required: int = 252
    # Selection: how many names to hold on each side.
    long_count: int = 30
    short_count: int = 30         # set 0 for long-only (cash account safe)


@dataclass
class MomentumScore:
    symbol: str
    score: float                  # the 12-1 trailing return
    annualized_vol: float
    last_price: float
    bars_used: int
    usable: bool
    note: str = ""
    # The daily returns behind `annualized_vol` (oldest first, most recent
    # last). Retained so the risk layer can estimate correlations between the
    # names we actually hold without re-fetching every price series.
    recent_returns: list = field(default_factory=list)


@dataclass
class RankedSelection:
    """The final long/short selection after ranking the whole universe."""
    longs: list[MomentumScore]
    shorts: list[MomentumScore]
    # Last price for EVERY usable name we scored, not just the ones selected.
    # The orchestrator needs prices for names it is EXITING, and those are by
    # definition no longer in longs/shorts. Without this the exit order can't
    # be priced and gets silently dropped. Default-empty so existing callers
    # and tests that build a selection by hand keep working.
    all_prices: dict[str, float] = field(default_factory=dict)
    # Daily-return panel {symbol: [returns]} for every scored name — feeds the
    # risk layer's correlation-aware vol targeting.
    recent_returns: dict = field(default_factory=dict)
    # Shorts the REGIME GATE removed this cycle. They are not traded, but they
    # must still be visible to the strategy layer, because the capital they
    # would have used has to stay UNDEPLOYED rather than being re-normalized
    # onto the surviving longs. See MomentumStrategy.build_target — this field
    # is the whole mechanism by which "suppress shorts" reduces exposure
    # instead of turning a dollar-neutral book 100% net long.
    suppressed_shorts: list = field(default_factory=list)

    def directions(self) -> dict[str, Direction]:
        out = {s.symbol: Direction.LONG for s in self.longs}
        out.update({s.symbol: Direction.SHORT for s in self.shorts})
        return out


def calendar_days_to_fetch(lookback_days: int, buffer: float = 1.7) -> int:
    return int(lookback_days * buffer) + 10


def compute_score_from_closes(
    symbol: str, closes: list[float], config: MomentumConfig
) -> MomentumScore:
    """
    Pure 12-1 momentum + volatility from a list of daily closes (oldest first).
    The score is the return from `lookback_days` ago to `skip_days` ago — i.e.
    it deliberately excludes the most recent ~month.
    """
    clean = [c for c in closes if c is not None and c > 0]
    n = len(clean)
    if n < config.min_bars_required:
        return MomentumScore(symbol, 0.0, 0.0, (clean[-1] if clean else 0.0),
                             n, False, f"Only {n} bars; need {config.min_bars_required}.")

    last_price = clean[-1]

    # 12-1 window: price `lookback_days` ago → price `skip_days` ago
    start_idx = n - config.lookback_days
    end_idx = n - config.skip_days
    if start_idx < 0 or end_idx <= start_idx:
        return MomentumScore(symbol, 0.0, 0.0, last_price, n, False,
                             "Not enough history for 12-1 window.")
    p_start = clean[start_idx]
    p_end = clean[end_idx]
    score = (p_end / p_start) - 1.0 if p_start > 0 else 0.0

    # Volatility from recent daily returns (same approach as trend bot)
    vol_window = min(config.vol_window_days, n - 1)
    recent = clean[-(vol_window + 1):]
    rets = [(recent[i] / recent[i - 1]) - 1.0 for i in range(1, len(recent)) if recent[i - 1] > 0]
    if len(rets) >= 2:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        annualized_vol = math.sqrt(var) * math.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        annualized_vol = 0.0

    return MomentumScore(symbol, score, annualized_vol, last_price, n,
                         usable=(annualized_vol > 0), note="",
                         recent_returns=rets)


def rank_and_select(
    scores: dict[str, MomentumScore], config: MomentumConfig
) -> RankedSelection:
    """
    Pure ranking: take usable scores, sort by momentum, pick top N long and
    bottom N short. Fully testable without a broker.
    """
    usable = [s for s in scores.values() if s.usable]
    usable.sort(key=lambda s: s.score, reverse=True)  # best first

    longs = usable[: config.long_count]

    # Take the bottom N EXPLICITLY.
    #
    # This used to be `usable[len(usable) - config.short_count:]`, which turns
    # into a NEGATIVE index whenever the usable pool is smaller than
    # short_count — and Python then silently reinterprets it as "count from the
    # end". With 25 usable names and short_count=30 the expression is
    # usable[-5:], i.e. the 5 worst names, when the intent was plainly "all 25
    # of them (bar any that are already long)". The universe being too small to
    # fill both sides is a real condition — a thin day, a fetch failure, a
    # narrow universe cap — and it silently produced a differently-shaped book
    # rather than an error or a log line. clamp with min() so the slice index
    # can never go below zero.
    n_short = min(config.short_count, len(usable)) if config.short_count > 0 else 0
    shorts = usable[len(usable) - n_short:] if n_short > 0 else []
    if config.short_count > n_short:
        logger.warning(
            "Only %d usable name(s) for a requested %d shorts — taking all of "
            "them (minus any already selected long). The book will be lopsided.",
            len(usable), config.short_count,
        )

    # Guard against overlap when the universe is tiny
    long_syms = {s.symbol for s in longs}
    shorts = [s for s in shorts if s.symbol not in long_syms]

    logger.info(
        "Cross-sectional momentum: ranked %d usable names → %d longs, %d shorts",
        len(usable), len(longs), len(shorts),
    )
    all_prices = {s.symbol: s.last_price for s in scores.values() if s.last_price > 0}
    panel = {s.symbol: list(s.recent_returns) for s in scores.values()
             if len(getattr(s, "recent_returns", []) or []) >= 2}
    return RankedSelection(longs=longs, shorts=shorts, all_prices=all_prices,
                           recent_returns=panel)


class MomentumSignalGenerator:
    """Fetches history for the universe, scores each name, ranks, and selects."""

    def __init__(self, config: MomentumConfig, tradier):
        self.config = config
        self.tradier = tradier

    def generate(self, symbols: list[str], today: Optional[date] = None) -> RankedSelection:
        today = today or date.today()
        start = today - timedelta(days=calendar_days_to_fetch(self.config.lookback_days))
        scores: dict[str, MomentumScore] = {}

        for symbol in symbols:
            try:
                bars = self.tradier.get_history(symbol, start=start, end=today, interval="daily")
            except Exception as e:
                logger.debug("History fetch failed for %s: %s", symbol, e)
                continue
            closes = [_to_float(b.get("close")) for b in bars]
            score = compute_score_from_closes(symbol, closes, self.config)
            if score.usable:
                scores[symbol] = score

        return rank_and_select(scores, self.config)


def _to_float(x) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0
