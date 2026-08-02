"""
Put credit spread strategy.

Takes screener candidates and constructs concrete Tradier multi-leg orders.
This module is the *strategy* — the math of "given this candidate, what's the
trade?" — but it is deliberately NOT in charge of:

  - Position sizing or risk caps (that's V5 / risk.py)
  - Tracking what's already open (V6 / portfolio.py — the caller passes us
    a set of fingerprints to skip)
  - When to actually fire orders (V8 / orchestrator)
  - Account funding checks (broker preview will catch over-buying-power)

Outputs are SpreadOrder objects — fully constructed multi-leg credit spreads
ready to hand to TradierClient.place_multileg_order(). Each one also carries
a `fingerprint` field so the caller can check against open positions before
sending.

A note on width selection: We use a simple rule — $5 wide if spot < $300,
$10 wide otherwise. This roughly matches market strike granularity (cheap
stocks have $1-2.50 increments, expensive stocks have $5-10) and keeps the
trade structure (% of spot covered by the spread) more constant than a
fixed-$5 width would.

A note on idempotency: The strategy never reads from Tradier; the caller is
responsible for fetching open positions and passing fingerprints we should
skip. This keeps the strategy pure (testable without a broker) and lets
upstream code decide what "already open" means (same underlying? same
expiration? same exact strikes? all three?).
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from broker import (
    OptionLeg,
    OptionType,
    OrderDuration,
    OrderSide,
    OrderType,
    build_occ_symbol,
)
from screener import ScreenedCandidate

logger = logging.getLogger(__name__)


# ─── Config ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StrategyConfig:
    """Parameters that govern trade construction (not sizing — see risk.py)."""

    # Spread width in dollars. Flat across all underlyings — our analysis
    # showed dynamic width was an instinct, not an edge: width affects max
    # loss and credit collected proportionally, so the per-contract RoR is
    # invariant to width. Flat $5 means smaller positions, more breadth,
    # and lower capital tied up per spread. We can revisit if there's
    # evidence a different policy improves risk-adjusted returns.
    spread_width: float = 5.0

    # Number of contracts per spread. Strategy fixes this at 1; the risk
    # manager (V5) computes the actual contract count from account size
    # and per-trade risk %.
    contracts_per_spread: int = 1

    # Target credit as fraction of mid. 1.0 = exactly the mid (theoretical
    # fair value, rarely fills). 0.95 = accept 5% below mid (more realistic).
    # Tradier won't fill a credit order below this price.
    credit_target_fraction_of_mid: float = 0.95

    # Minimum acceptable credit ($ per spread, not per share). If the
    # target credit falls below this floor after the fraction-of-mid
    # adjustment, the order is dropped — not worth the round-trip costs.
    min_credit_dollars: float = 0.20

    # Order duration. DAY = cancel at end of day if not filled.
    duration: OrderDuration = OrderDuration.DAY


# ─── Output types ───────────────────────────────────────────────────────────


@dataclass
class SpreadOrder:
    """A fully-constructed put credit spread ready for the broker."""

    # Identity
    symbol: str                      # underlying (e.g. "SPY")
    expiration: date
    short_strike: float
    long_strike: float
    contracts: int

    # OCC symbols (computed from the above)
    short_put_occ: str
    long_put_occ: str

    # Pricing
    target_credit: float             # net credit we'll accept ($ per spread)
    target_credit_per_contract: float  # net credit per single spread
    estimated_max_loss: float        # (width - credit) * 100 * contracts

    # Source candidate context (for logging / reporting / debugging)
    short_delta: float
    atm_iv: float
    spread_width: float

    # Idempotency key (see make_fingerprint)
    fingerprint: str

    # Suggested order tag (Tradier accepts alphanumeric, <= 255 chars)
    tag: str

    def to_legs(self) -> list[OptionLeg]:
        """Return the OptionLeg list to pass to TradierClient.place_multileg_order."""
        return [
            OptionLeg(self.short_put_occ, OrderSide.SELL_TO_OPEN, self.contracts),
            OptionLeg(self.long_put_occ, OrderSide.BUY_TO_OPEN, self.contracts),
        ]


@dataclass
class StrategyResult:
    run_timestamp_utc: str
    config: dict
    input_candidates: int
    skipped_existing: int
    dropped_low_credit: int
    dropped_other: int
    orders: list[SpreadOrder] = field(default_factory=list)


# ─── Helpers ────────────────────────────────────────────────────────────────


def make_fingerprint(underlying: str, expiration: date, short_strike: float, long_strike: float) -> str:
    """
    Stable identifier for a spread. Two trades match (are "the same") iff they
    share underlying, expiration, and both strikes. Used to skip candidates
    that already have an open position.
    """
    return f"{underlying.upper()}|{expiration.isoformat()}|{short_strike:.4f}|{long_strike:.4f}"


# ─── Strategy ───────────────────────────────────────────────────────────────


class PutCreditSpreadStrategy:
    """
    Turns ScreenedCandidate objects into SpreadOrder objects.

    Usage:
        strategy = PutCreditSpreadStrategy(StrategyConfig())
        result = strategy.build_orders(
            candidates=candidates,
            already_open_fingerprints={"SPY|2026-06-20|565.0000|560.0000"},
        )
        for order in result.orders:
            preview = tradier.place_multileg_order(
                underlying=order.symbol,
                legs=order.to_legs(),
                order_type=OrderType.CREDIT,
                price=order.target_credit_per_contract,
                preview=True,  # KEEP THIS TRUE for V4
                tag=order.tag,
            )
    """

    def __init__(self, config: StrategyConfig):
        self.config = config

    def build_orders(
        self,
        candidates: list[ScreenedCandidate],
        already_open_fingerprints: Optional[set[str]] = None,
    ) -> StrategyResult:
        if already_open_fingerprints is None:
            already_open_fingerprints = set()

        orders: list[SpreadOrder] = []
        skipped_existing = 0
        dropped_low_credit = 0
        dropped_other = 0

        for candidate in candidates:
            try:
                order = self._build_one(candidate)
            except ValueError as e:
                logger.debug("Skipping %s: %s", candidate.symbol, e)
                dropped_other += 1
                continue

            if order is None:
                dropped_low_credit += 1
                continue

            if order.fingerprint in already_open_fingerprints:
                logger.info(
                    "Skipping %s — already have an open spread at "
                    "%s/%s exp %s",
                    candidate.symbol,
                    order.short_strike,
                    order.long_strike,
                    order.expiration,
                )
                skipped_existing += 1
                continue

            orders.append(order)

        logger.info(
            "Strategy built %d orders from %d candidates "
            "(skipped %d as already open, dropped %d low-credit, %d errors)",
            len(orders),
            len(candidates),
            skipped_existing,
            dropped_low_credit,
            dropped_other,
        )

        return StrategyResult(
            run_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            config=asdict(self.config),
            input_candidates=len(candidates),
            skipped_existing=skipped_existing,
            dropped_low_credit=dropped_low_credit,
            dropped_other=dropped_other,
            orders=orders,
        )

    # ─── Internal ────────────────────────────────────────────────────────────

    def _build_one(self, candidate: ScreenedCandidate) -> Optional[SpreadOrder]:
        cfg = self.config

        # Use the strikes the screener picked. The screener uses the same
        # spread_width as the strategy (both configured to the same value
        # via their respective configs), so the strikes are already correct.
        # If the configs ever diverged we'd just trust the screener's pricing
        # — that's the data we have.
        short_strike = candidate.short_put_strike
        long_strike = candidate.long_put_strike
        actual_width = abs(short_strike - long_strike)
        short_mid = candidate.short_put_mid
        long_mid = candidate.long_put_mid

        # Net credit at mid, scaled by our target fraction.
        # Convention: credit is *per single spread* in dollars (e.g., $1.25
        # means $125 net cash if filled with 1 contract).
        credit_at_mid = short_mid - long_mid
        target_credit_per_contract = credit_at_mid * cfg.credit_target_fraction_of_mid

        # Floor: skip junk premium.
        if target_credit_per_contract < cfg.min_credit_dollars:
            logger.debug(
                "%s: target credit %.3f below floor %.3f; skipping",
                candidate.symbol,
                target_credit_per_contract,
                cfg.min_credit_dollars,
            )
            return None

        contracts = cfg.contracts_per_spread
        target_credit_total = target_credit_per_contract * contracts

        # Max loss in dollars: (width - credit) * 100 * contracts
        # Width is in dollars-per-share, multiplied by 100 shares/contract.
        max_loss = (actual_width - target_credit_per_contract) * 100.0 * contracts
        max_loss = max(max_loss, 0.0)  # paranoia; should never be negative

        short_occ = build_occ_symbol(
            candidate.symbol, candidate.target_expiration,
            OptionType.PUT, short_strike,
        )
        long_occ = build_occ_symbol(
            candidate.symbol, candidate.target_expiration,
            OptionType.PUT, long_strike,
        )

        fingerprint = make_fingerprint(
            candidate.symbol, candidate.target_expiration,
            short_strike, long_strike,
        )

        tag = f"pcs-{candidate.symbol}-{candidate.target_expiration.isoformat()}"
        # Tradier tags accept alphanumeric only; strip dashes/dots just in case.
        tag = "".join(c if c.isalnum() else "-" for c in tag)[:64]

        return SpreadOrder(
            symbol=candidate.symbol,
            expiration=candidate.target_expiration,
            short_strike=short_strike,
            long_strike=long_strike,
            contracts=contracts,
            short_put_occ=short_occ,
            long_put_occ=long_occ,
            target_credit=target_credit_total,
            target_credit_per_contract=target_credit_per_contract,
            estimated_max_loss=max_loss,
            short_delta=candidate.short_put_delta,
            atm_iv=candidate.atm_iv,
            spread_width=actual_width,
            fingerprint=fingerprint,
            tag=tag,
        )
