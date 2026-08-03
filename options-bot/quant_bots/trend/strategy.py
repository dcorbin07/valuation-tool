"""
T4 — Strategy: turn signals into a target portfolio shape.

Given the per-instrument signals from T3, decide the RELATIVE target weights —
which instruments to hold, long or short, and in what proportion. The actual
dollar/share sizing and the risk caps happen in T5 (risk); this layer only
decides the SHAPE of the portfolio.

Weighting scheme: inverse-volatility.
  Each instrument with a (non-FLAT) signal gets a raw weight of
  direction × (1 / annualized_vol). Lower-volatility instruments get larger
  weights so that each position contributes roughly equal risk to the
  portfolio — this is the standard risk-balanced approach to trend-following
  and stops a single wild instrument (e.g. nat gas) from dominating.

  We then normalize so the gross weight (sum of absolute weights) equals 1.0.
  T5 scales this normalized shape up/down to hit a target portfolio volatility
  and applies exposure caps.

FLAT signals get zero weight (no position). Unusable signals (bad/insufficient
data) are skipped entirely.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .signals import Direction, Signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyConfig:
    # Floor on volatility used in the inverse-vol weight, to avoid a
    # near-zero-vol instrument getting an absurdly large weight.
    min_vol_floor: float = 0.05   # 5% annualized floor


@dataclass
class TargetWeight:
    symbol: str
    direction: Direction
    annualized_vol: float
    raw_weight: float          # signed, pre-normalization (direction / vol)
    normalized_weight: float   # signed, gross-normalized to sum |w| = 1.0


@dataclass
class TargetPortfolio:
    weights: list[TargetWeight] = field(default_factory=list)
    gross_before_norm: float = 0.0
    # Daily-return panel for the names in this target: {symbol: [r_oldest ...
    # r_most_recent]}. The risk layer uses it to estimate the CORRELATIONS
    # between holdings so it can vol-target the portfolio rather than the
    # average single name. Default-empty: absent or too short and the risk
    # layer falls back to the old weighted-average estimate (and says so).
    recent_returns: dict = field(default_factory=dict)

    def net_weight(self) -> float:
        return sum(w.normalized_weight for w in self.weights)

    def gross_weight(self) -> float:
        """
        Sum of |normalized weight|. Normally 1.0, but deliberately LESS when a
        gate (e.g. the momentum/reversion regime filter) suppressed part of the
        book — see those strategies' build_target. The risk layer must not
        assume 1.0.
        """
        return sum(abs(w.normalized_weight) for w in self.weights)

    def long_count(self) -> int:
        return sum(1 for w in self.weights if w.direction == Direction.LONG)

    def short_count(self) -> int:
        return sum(1 for w in self.weights if w.direction == Direction.SHORT)


class TrendStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def build_target(self, signals: dict[str, Signal]) -> TargetPortfolio:
        cfg = self.config
        raws: list[TargetWeight] = []

        for symbol, sig in signals.items():
            if not sig.usable or sig.direction == Direction.FLAT:
                continue
            vol = max(sig.annualized_vol, cfg.min_vol_floor)
            sign = 1.0 if sig.direction == Direction.LONG else -1.0
            raw = sign * (1.0 / vol)
            raws.append(TargetWeight(
                symbol=symbol, direction=sig.direction,
                annualized_vol=sig.annualized_vol,
                raw_weight=raw, normalized_weight=0.0,
            ))

        gross = sum(abs(w.raw_weight) for w in raws)
        if gross > 0:
            for w in raws:
                w.normalized_weight = w.raw_weight / gross

        # Carry the return series of the SELECTED names only — the risk layer
        # only needs the covariance of what we actually hold.
        held = {w.symbol for w in raws}
        panel = {
            sym: list(s.recent_returns)
            for sym, s in signals.items()
            if sym in held and len(getattr(s, "recent_returns", []) or []) >= 2
        }

        logger.info(
            "Target portfolio: %d positions (%d long, %d short), net weight %.2f, "
            "return history for %d/%d names",
            len(raws),
            sum(1 for w in raws if w.direction == Direction.LONG),
            sum(1 for w in raws if w.direction == Direction.SHORT),
            sum(w.normalized_weight for w in raws),
            len(panel), len(raws),
        )
        return TargetPortfolio(weights=raws, gross_before_norm=gross,
                               recent_returns=panel)
