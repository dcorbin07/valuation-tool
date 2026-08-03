"""
T6 — Portfolio: reconcile current holdings against the target and produce the
orders needed to rebalance.

Trend-following doesn't "open" and "close" discrete trades like the options bot.
Instead it computes a TARGET portfolio (T5) and trades the DIFFERENCE between
where it is and where it wants to be. Most days the difference is small or zero
(12-month momentum changes slowly), so this is usually a light touch.

For each instrument we compare:
    current signed shares (+ long, − short)  vs  target signed shares
and emit the order(s) to close the gap. Sign flips (long → short or vice versa)
require two orders: flatten the existing position, then establish the new one,
because the four Tradier equity sides each only move position one direction:

    buy            : increase a long      (or open one)
    sell           : decrease a long      (or close one)
    sell_short     : increase a short     (or open one)
    buy_to_cover   : decrease a short     (or close one)

A no-trade deadband avoids churning tiny share differences (and their costs)
when the target barely moved.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core import EquitySide, TradierClient, parse_occ_symbol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PortfolioConfig:
    # Skip rebalancing a position if the share change is below this fraction of
    # the target (avoids churning a handful of shares). Also a small absolute
    # floor so tiny targets don't thrash.
    rebalance_deadband_pct: float = 0.10   # 10% of target shares
    min_share_change: int = 1


@dataclass
class RebalanceOrder:
    symbol: str
    side: EquitySide
    quantity: int
    reason: str


@dataclass
class RebalancePlan:
    orders: list[RebalanceOrder] = field(default_factory=list)
    current_positions: dict = field(default_factory=dict)   # symbol -> signed shares
    unrealized_pnl: float = 0.0


def _current_signed_shares(positions: list[dict]) -> dict[str, int]:
    """
    Build {symbol: signed_shares} from Tradier positions, EQUITIES ONLY.
    Long positions have positive quantity, shorts negative (Tradier reports
    short quantity as negative). Option legs (OCC symbols) are ignored.
    """
    out: dict[str, int] = {}
    for p in positions:
        symbol = (p.get("symbol") or "").upper()
        if not symbol:
            continue
        # Skip option positions (OCC symbols are 16+ chars and parse cleanly)
        if len(symbol) >= 16:
            try:
                parse_occ_symbol(symbol)
                continue  # it's an option; not ours
            except Exception:
                pass  # not an OCC symbol; treat as equity
        try:
            qty = int(float(p.get("quantity", 0)))
        except (TypeError, ValueError):
            qty = 0
        if qty != 0:
            out[symbol] = out.get(symbol, 0) + qty
    return out


def orders_to_reach_target(
    symbol: str, current: int, target: int, reason: str = ""
) -> list[RebalanceOrder]:
    """
    Compute the order(s) to move a single instrument from `current` signed
    shares to `target` signed shares. Returns [] if already there.

    Handles all cases including sign flips. Pure function — fully testable.
    """
    if current == target:
        return []

    orders: list[RebalanceOrder] = []

    # Sign flip (or crossing zero): flatten current, then establish target.
    if current != 0 and target != 0 and (current > 0) != (target > 0):
        # 1. Flatten current
        if current > 0:
            orders.append(RebalanceOrder(symbol, EquitySide.SELL, current, f"flatten long ({reason})"))
        else:
            orders.append(RebalanceOrder(symbol, EquitySide.BUY_TO_COVER, -current, f"flatten short ({reason})"))
        # 2. Establish target from zero
        if target > 0:
            orders.append(RebalanceOrder(symbol, EquitySide.BUY, target, f"open long ({reason})"))
        else:
            orders.append(RebalanceOrder(symbol, EquitySide.SELL_SHORT, -target, f"open short ({reason})"))
        return orders

    delta = target - current  # same side (or from/to zero)

    if current >= 0 and target >= 0:
        # Long side (or zero)
        if delta > 0:
            orders.append(RebalanceOrder(symbol, EquitySide.BUY, delta, f"add long ({reason})"))
        else:
            orders.append(RebalanceOrder(symbol, EquitySide.SELL, -delta, f"reduce long ({reason})"))
    else:
        # Short side (current <= 0 and target <= 0)
        if delta < 0:
            # more negative → increase short
            orders.append(RebalanceOrder(symbol, EquitySide.SELL_SHORT, -delta, f"add short ({reason})"))
        else:
            # less negative → cover some short
            orders.append(RebalanceOrder(symbol, EquitySide.BUY_TO_COVER, delta, f"reduce short ({reason})"))

    return orders


class TrendPortfolioManager:
    def __init__(self, config: PortfolioConfig, tradier: TradierClient):
        self.config = config
        self.tradier = tradier

    def build_rebalance_plan(self, sized_targets: dict,
                             current_override: dict | None = None) -> RebalancePlan:
        """
        sized_targets: {symbol: SizedTarget} from the risk layer.
        current_override: if provided (SIM mode), use these {symbol: signed_shares}
            as the current book instead of querying the broker. This is how the
            sim layer diffs against its own simulated holdings.
        Pulls current positions, diffs, and returns the orders to rebalance.
        Any currently-held equity NOT in the target is closed (target 0).
        """
        if current_override is not None:
            current = dict(current_override)
        else:
            positions = self.tradier.get_positions()
            current = _current_signed_shares(positions)

        plan = RebalancePlan(current_positions=current)

        # Union of symbols we hold and symbols we want
        all_symbols = set(current.keys()) | set(sized_targets.keys())

        for symbol in sorted(all_symbols):
            cur = current.get(symbol, 0)
            tgt_obj = sized_targets.get(symbol)
            tgt = tgt_obj.target_shares if tgt_obj else 0  # not in target → close

            # Deadband: skip trivial adjustments (but never skip a full close)
            if tgt != 0 and cur != 0:
                change = abs(tgt - cur)
                if change < max(self.config.min_share_change,
                                int(abs(tgt) * self.config.rebalance_deadband_pct)):
                    continue

            reason = "rebalance" if tgt != 0 else "exit (not in target)"
            plan.orders.extend(orders_to_reach_target(symbol, cur, tgt, reason))

        logger.info(
            "Rebalance plan: %d orders across %d instruments",
            len(plan.orders), len(all_symbols),
        )
        return plan
