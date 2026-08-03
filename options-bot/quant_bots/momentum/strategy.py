"""
Strategy for Bot #3: convert the ranked long/short selection into target
portfolio weights.

The signal layer already decided WHICH names (top-N winners long, bottom-N
losers short). This layer decides the RELATIVE weight of each, using the same
inverse-volatility scheme as the trend bot so that a single high-vol name
doesn't dominate the book. Weights are gross-normalized to sum to 1.0; the risk
layer then scales to a target volatility and applies caps.

Keeping the weighting identical to the trend bot is deliberate — it means the
two bots' risk layers behave consistently, and it keeps the code shared in
spirit even though each bot has its own thin strategy module.

REGIME-SUPPRESSED SHORTS AND THE DENOMINATOR (read this before touching
build_target). The orchestrator's regime gate removes the short book when SPY
is above its 200-day MA. It used to do that by simply emptying
`selection.shorts`, after which this function gross-normalized over whatever
remained. Normalizing 30 longs to a gross of 1.0 does not reduce risk — it
DOUBLES each long's weight and takes net exposure from ~0 to +1.0. A bot
documented as dollar-neutral was, on every day SPY sat above its 200-day
average (which is most days), a fully invested single-sided long equity book
with undisguised market beta. Nothing in the logs said so.

The fix is one line of arithmetic: divide by the PRE-suppression gross. The
surviving longs keep exactly the share of the book they would have had, and the
capital freed by dropping the shorts is simply not deployed. Suppressing half
the book then halves gross and leaves net at +0.5 of the pre-suppression book
instead of +1.0 — which is what "we are not comfortable shorting today" should
cost you.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .signals import Direction, RankedSelection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyConfig:
    min_vol_floor: float = 0.05
    # Equal-weight instead of inverse-vol if you prefer the simplest classic
    # construction. Default False = inverse-vol (risk-balanced).
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


class MomentumStrategy:
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

        # The denominator includes the shorts the regime gate removed. They get
        # no weight and generate no order — but they still consume their share
        # of the book, so the longs cannot expand to fill the gap. See the
        # module docstring for why this one line is the difference between
        # "de-risk in a rally" and "go 100% net long in a rally".
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
            "Momentum target: %d positions (%d long, %d short), "
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
