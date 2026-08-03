"""
Short-horizon mean-reversion signals — the 4th strategy.

This is the structural opposite of the momentum bot. Where momentum buys what
has gone UP over 3-12 months (continuation), mean-reversion buys what has gone
DOWN over a short window (reversal), betting the short-term move overshot and
will revert. The research basis: equity returns tend to revert over horizons
under ~3 months, while they trend over 3-12 months — so this bot deliberately
lives in the short-horizon reversal regime the other three miss.

Signal: a z-score of the current price relative to its recent moving average.
  - Price far BELOW its recent mean (very negative z) → oversold → LONG
  - Price far ABOVE its recent mean (very positive z) → overbought → SHORT
We rank the universe by z-score and go long the most oversold, short the most
overbought. This is cross-sectional (relative), like the momentum bot, so it's
dollar-neutral-ish and reuses the same risk/portfolio machinery.

IMPORTANT risk note (well-supported by the literature): mean-reversion has a
HIGH win rate but a nasty LEFT TAIL — it wins often but occasionally takes a big
loss when a short-term dislocation turns into a real trend (the dip that keeps
dipping). Evidence is consistent that mean-reversion performs BETTER WITHOUT
tight stop-losses (the further it goes against you, the stronger the reversion
signal), so risk is controlled by SIZING and breadth, not stops. We hold many
small names so no single blow-up dominates.
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
class MeanReversionConfig:
    # Short-horizon reversal window — the moving-average lookback the z-score is
    # measured against. ~21 trading days ≈ 1 month (well inside the <3mo
    # reversion regime).
    #
    # This knob USED TO BE DEAD. It was documented as the MA lookback but
    # compute_score_from_closes computed BOTH the mean and the standard
    # deviation over zscore_window_days, so ma_window_days was referenced
    # nowhere except a fetch-window calculation. Because both default to 21 the
    # breakage was invisible; anyone tuning ma_window_days=50 would have watched
    # the signal not move and drawn entirely the wrong conclusion about the
    # strategy. It is now genuinely the mean's window.
    ma_window_days: int = 21
    # Std-dev window for the z-score. Kept SEPARATE from the mean's window on
    # purpose: z = (price − mean) / σ has two estimates in it, and they answer
    # different questions. The mean defines "where should this be trading"; σ
    # defines "how big is a normal wobble". A longer mean window with a shorter
    # σ window measures dislocation against a slower anchor while staying
    # responsive to the current noise level. Equal by default, so the shipped
    # behaviour is the plain 21-day z-score.
    zscore_window_days: int = 21
    vol_window_days: int = 63          # ~3mo for the annualized-vol estimate
    # Floor on bars required. The EFFECTIVE requirement is required_bars(),
    # which also respects the MA / z-score / vol windows — so raising any of
    # those raises the data requirement instead of silently truncating them.
    min_bars_required: int = 90        # need enough history to be meaningful
    # Selection: hold many small names (breadth controls the left tail).
    long_count: int = 20
    short_count: int = 20              # set 0 for long-only (cash account safe)
    # Only act on genuine dislocations: require |z| past this to qualify.
    min_abs_zscore: float = 1.0


@dataclass
class ReversionScore:
    symbol: str
    zscore: float                      # how many std devs from the recent mean
    score: float                       # ranking score = -zscore (oversold ranks high)
    annualized_vol: float
    last_price: float
    bars_used: int
    usable: bool
    note: str = ""
    # The daily returns behind `annualized_vol` (oldest first, most recent
    # last) — retained for the risk layer's correlation estimate.
    recent_returns: list = field(default_factory=list)


@dataclass
class RankedSelection:
    """Final long/short selection after ranking the universe by reversion."""
    longs: list[ReversionScore]
    shorts: list[ReversionScore]
    # Last price for EVERY usable name we scored, not just the selected ones —
    # the orchestrator needs prices for positions it is EXITING, which are by
    # definition no longer selected. See core.sim_execution.resolve_prices.
    all_prices: dict[str, float] = field(default_factory=dict)
    # Daily-return panel {symbol: [returns]} for every scored name — feeds the
    # risk layer's correlation-aware vol targeting.
    recent_returns: dict = field(default_factory=dict)
    # Shorts the REGIME GATE removed this cycle. Not traded, but still counted
    # in the strategy layer's normalization denominator so that suppressing
    # them REDUCES exposure rather than doubling up the longs. See
    # MeanReversionStrategy.build_target.
    suppressed_shorts: list = field(default_factory=list)

    def directions(self) -> dict[str, Direction]:
        out = {s.symbol: Direction.LONG for s in self.longs}
        out.update({s.symbol: Direction.SHORT for s in self.shorts})
        return out

    def long_count(self) -> int:
        return len(self.longs)

    def short_count(self) -> int:
        return len(self.shorts)


def calendar_days_to_fetch(lookback_days: int, buffer: float = 1.7) -> int:
    return int(lookback_days * buffer) + 30


def required_bars(config: MeanReversionConfig) -> int:
    """
    Bars a name genuinely needs before it can be scored — the max over every
    window the computation actually touches, not a hand-kept constant.

    The old fetch-window arithmetic asked for `ma_window_days + vol_window_days`
    calendar-converted days, which is neither of the two things that matter: it
    is not the bar requirement (min_bars_required = 90 exceeded it) and it is
    not a window the estimator uses (nothing sums those two). Deriving the
    requirement means raising any window raises the data we demand for it,
    instead of the window being silently truncated to the history on hand.
    """
    return max(
        config.min_bars_required,
        config.ma_window_days,
        config.zscore_window_days,
        config.vol_window_days + 1,   # +1: N returns need N+1 prices
    )


def compute_score_from_closes(
    symbol: str, closes: list[float], config: MeanReversionConfig
) -> ReversionScore:
    """
    Compute the mean-reversion z-score from a list of daily closes (oldest
    first). z = (last_price − MA) / σ, where the MA runs over
    `ma_window_days` and σ over `zscore_window_days`.

    Ranking score = -z, so the most oversold (very negative z) gets the highest
    score and is selected LONG; the most overbought (very positive z) gets the
    lowest score and is selected SHORT.
    """
    clean = [c for c in closes if c is not None and c > 0]
    n = len(clean)
    needed = required_bars(config)
    if n < needed:
        return ReversionScore(symbol, 0.0, 0.0, 0.0,
                              (clean[-1] if clean else 0.0), n, False,
                              f"Only {n} bars; need {needed}.")

    last_price = clean[-1]

    # Moving average over ma_window_days, dispersion over zscore_window_days.
    # required_bars() guarantees both fit in the history we have, so neither
    # window gets quietly shortened to whatever happened to be available.
    ma_prices = clean[-config.ma_window_days:]
    ma = sum(ma_prices) / len(ma_prices)

    std_prices = clean[-config.zscore_window_days:]
    std_mean = sum(std_prices) / len(std_prices)
    var = sum((p - std_mean) ** 2 for p in std_prices) / (len(std_prices) - 1)
    std = math.sqrt(var)
    if std <= 0:
        return ReversionScore(symbol, 0.0, 0.0, 0.0, last_price, n, False,
                              "Zero price std in window.")
    zscore = (last_price - ma) / std

    # Annualized vol from recent daily returns (same approach as the other bots)
    vol_window = min(config.vol_window_days, n - 1)
    recent = clean[-(vol_window + 1):]
    rets = [(recent[i] / recent[i - 1]) - 1.0 for i in range(1, len(recent)) if recent[i - 1] > 0]
    if len(rets) >= 2:
        mean = sum(rets) / len(rets)
        rvar = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        annualized_vol = math.sqrt(rvar) * math.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        annualized_vol = 0.0

    return ReversionScore(
        symbol=symbol, zscore=zscore, score=-zscore,  # oversold (neg z) → high score
        annualized_vol=annualized_vol, last_price=last_price,
        bars_used=n, usable=(annualized_vol > 0), note="",
    )


def rank_and_select(
    scores: dict[str, ReversionScore], config: MeanReversionConfig
) -> RankedSelection:
    """
    Rank usable names by reversion score (= -zscore). Most oversold first →
    LONG; most overbought last → SHORT.

    We partition BY THE SIGN OF Z, then take the top N from each side —
    we do NOT rank the whole pool and slice off both ends.

    WHY THIS MATTERS: slicing both ends of a single ranked pool guarantees a
    full 20/20 book every day, which looks tidy and is wrong. In a market-wide
    selloff every name has z < 0, so the "bottom" of the pool is the LEAST
    oversold name — still oversold. The old code shorted names it had itself
    just classified as oversold, in exactly the fat-left-tail scenario this
    strategy is most exposed to, doubling the loss instead of hedging it.

    The cost of doing it correctly: on skewed days the book is lopsided
    (e.g. 20 longs, 3 shorts). That is the honest answer — there genuinely
    were only 3 overbought names. Accept the imbalance.
    """
    usable = [s for s in scores.values()
              if s.usable and abs(s.zscore) >= config.min_abs_zscore]

    # Oversold (z <= -threshold) → LONG candidates, most oversold first.
    oversold = sorted([s for s in usable if s.zscore < 0],
                      key=lambda s: s.zscore)
    # Overbought (z >= +threshold) → SHORT candidates, most overbought first.
    overbought = sorted([s for s in usable if s.zscore > 0],
                        key=lambda s: s.zscore, reverse=True)

    longs = oversold[: config.long_count]
    shorts = overbought[: config.short_count] if config.short_count > 0 else []

    logger.info(
        "Mean-reversion: %d names past |z|>=%.1f (%d oversold / %d overbought) "
        "→ %d longs, %d shorts",
        len(usable), config.min_abs_zscore, len(oversold), len(overbought),
        len(longs), len(shorts),
    )
    if longs and not shorts:
        logger.info("Broad selloff: no overbought names qualify — long-only this cycle.")
    elif shorts and not longs:
        logger.info("Broad rally: no oversold names qualify — short-only this cycle.")

    all_prices = {s.symbol: s.last_price for s in scores.values() if s.last_price > 0}
    return RankedSelection(longs=longs, shorts=shorts, all_prices=all_prices)


def _to_float(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


class MeanReversionSignalGenerator:
    """Fetches history for the universe, scores each name, ranks, and selects."""

    def __init__(self, config: MeanReversionConfig, tradier):
        self.config = config
        self.tradier = tradier

    def generate(self, symbols: list[str], today: Optional[date] = None) -> RankedSelection:
        today = today or date.today()
        start = today - timedelta(days=calendar_days_to_fetch(self.config.ma_window_days
                                                              + self.config.vol_window_days))
        scores: dict[str, ReversionScore] = {}
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
