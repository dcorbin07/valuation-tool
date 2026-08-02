"""
Strategy for the mean-reversion bot: convert the ranked long/short selection
into target portfolio weights.

The signal layer already decided WHICH names (most oversold long, most
overbought short). This layer decides the RELATIVE weight using the same
inverse-volatility scheme as the trend and momentum bots, so a single high-vol
name doesn't dominate. Identical weighting across all bots is deliberate — it
keeps their risk layers behaving consistently.

This mirrors momentum/strategy.py exactly (same TargetPortfolio/TargetWeight
shapes) so it plugs into the shared trend risk + portfolio machinery unchanged.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .signals import Direction, RankedSelection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyConfig:
    min_vol_floor: float = 0.05
    equal_weight: bool = False


@dataclass
class TargetWeight:
    symbol: str
    direction: Direction
    annualized_vol: float
    raw_weight: float
    normalized_weight: float


@dataclass
class TargetPortfolio:
    weights: list[TargetWeight] = field(default_factory=list)
    # Daily-return panel {symbol: [returns]} for the held names — the risk
    # layer's correlation-aware vol targeting reads this.
    recent_returns: dict = field(default_factory=dict)
    # Gross weight that WOULD have been deployed but was withheld by the regime
    # gate. Reported so a cycle's undeployed capital is an explicit number
    # rather than something you infer from a gross that looks low.
    suppressed_gross_weight: float = 0.0

    def net_weight(self) -> float:
        return sum(w.normalized_weight for w in self.weights)

    def gross_weight(self) -> float:
        """Sum of |normalized weight| — 1.0 normally, LESS after suppression."""
        return sum(abs(w.normalized_weight) for w in self.weights)

    def long_count(self) -> int:
        return sum(1 for w in self.weights if w.direction == Direction.LONG)

    def short_count(self) -> int:
        return sum(1 for w in self.weights if w.direction == Direction.SHORT)


class MeanReversionStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def _raw_weight(self, score, direction: Direction) -> float:
        cfg = self.config
        vol = max(score.annualized_vol, cfg.min_vol_floor)
        sign = 1.0 if direction == Direction.LONG else -1.0
        return sign * (1.0 if cfg.equal_weight else (1.0 / vol))

    def build_target(self, selection: RankedSelection) -> TargetPortfolio:
        raws: list[TargetWeight] = []

        picks = [(s, Direction.LONG) for s in selection.longs] + \
                [(s, Direction.SHORT) for s in selection.shorts]

        for score, direction in picks:
            raws.append(TargetWeight(
                symbol=score.symbol, direction=direction,
                annualized_vol=score.annualized_vol,
                raw_weight=self._raw_weight(score, direction),
                normalized_weight=0.0,
            ))

        traded_gross = sum(abs(w.raw_weight) for w in raws)

        # ── The regime gate must REDUCE exposure, not lever up the longs ──
        #
        # The gate suppresses shorts when SPY is above its 200-day MA. The old
        # code then normalized gross to 1.0 over the SURVIVING longs — so
        # removing the short book didn't shrink the position, it DOUBLED the
        # long one. Net weight went to +1.00. A strategy documented as
        # "dollar-neutral-ish" was running 100% net long, single-sided equity
        # beta, on most days of most years, and nothing said so.
        #
        # Normalizing by the PRE-suppression denominator fixes it: the longs
        # keep exactly the share of the book they would have had, and the
        # capital the shorts would have used simply stays undeployed. Gross
        # falls to roughly half on a fully-suppressed cycle, which is the
        # honest expression of "we don't want this exposure right now."
        suppressed = getattr(selection, "suppressed_shorts", None) or []
        suppressed_gross = sum(
            abs(self._raw_weight(s, Direction.SHORT)) for s in suppressed)
        denom = traded_gross + suppressed_gross

        if denom > 0:
            for w in raws:
                w.normalized_weight = w.raw_weight / denom

        suppressed_weight = (suppressed_gross / denom) if denom > 0 else 0.0
        held = {w.symbol for w in raws}
        panel = {sym: list(r) for sym, r in
                 (getattr(selection, "recent_returns", None) or {}).items()
                 if sym in held and len(r) >= 2}

        gross_w = sum(abs(w.normalized_weight) for w in raws)
        net_w = sum(w.normalized_weight for w in raws)
        logger.info(
            "Mean-reversion target: %d positions (%d long, %d short), "
            "GROSS weight %.2f, NET weight %.2f%s",
            len(raws),
            sum(1 for w in raws if w.direction == Direction.LONG),
            sum(1 for w in raws if w.direction == Direction.SHORT),
            gross_w, net_w,
            (f" — {len(suppressed)} regime-suppressed short(s) hold back "
             f"{suppressed_weight:.0%} of the book, UNDEPLOYED"
             if suppressed else ""),
        )
        return TargetPortfolio(weights=raws, recent_returns=panel,
                               suppressed_gross_weight=suppressed_weight)
