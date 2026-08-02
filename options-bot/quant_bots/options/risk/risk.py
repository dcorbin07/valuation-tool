"""
Risk management.

Takes a list of SpreadOrder objects from the strategy layer and returns a
filtered, properly-sized list that respects:

  1. Daily loss kill switch (top-level — stops everything for the day if hit)
  2. Position sizing (contracts per spread from account-size × risk %)
  3. Per-ticker concentration (default: max 1 spread per underlying)
  4. Max concurrent positions (default: 10 — matches our agreed risk profile)
  5. Total deployed buying power cap (default: 50%)

The module is pure given its inputs. The caller is responsible for providing:
  - account_value (e.g. tradier.get_account_value())
  - current_positions (e.g. tradier.get_positions())
  - account_state (loaded from disk, see state.py)

That makes the whole pipeline testable without a broker.

Notes on the math:

  Position sizing for a credit spread:
      max_loss_per_contract = (width - credit) * 100
      contracts = floor(risk_budget / max_loss_per_contract)
      where risk_budget = account_value * risk_pct_per_trade

  If contracts < 1, the order is too big to fit the risk budget. We DROP it,
  not size it to 1 anyway. This is the honest behavior: at a $4k account with
  2% risk, your budget is $80 per trade, but a $5-wide spread has $400+ max
  loss per contract — it simply doesn't fit. That's a signal to the user
  about account size, not something to silently override.

  Deployed capital — BOTH sides of the buying-power cap are measured as true
  max loss, (width - credit) * 100 * contracts. This module used to measure
  the EXISTING book by summing |cost_basis| across legs (i.e. the premium that
  changed hands) while measuring NEW orders as max loss, then compare the sum
  of the two against one cap. For a $5-wide spread opened at $1.00 credit that
  is |-150| + |50| = $200 of "deployed" versus $400 genuinely at risk — the
  existing-position term understated by about 2x, and the error grew with the
  book. Premium is not capital at risk; on a defined-risk spread the capital at
  risk is the width you cannot lose more than. See
  portfolio.PairedPutSpread.max_loss_dollars, which is now the single
  definition both this module and the sim book read.
"""
from __future__ import annotations

import logging
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Optional

# The pairing helper lives in portfolio because reconstructing spreads from
# broker legs is that module's whole job. Importing it keeps ONE definition of
# "what is an open spread" instead of a second, subtly different one here.
# (portfolio does not import risk, so there is no cycle.)
from portfolio import PairedPutSpread, option_legs_only, pair_put_spread_legs
from strategy import SpreadOrder

logger = logging.getLogger(__name__)


# ─── Config ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RiskConfig:
    """Caps and limits. Defaults match the '2% / 10 concurrent' profile."""

    # Per-trade risk as fraction of account.
    risk_pct_per_trade: float = 0.02

    # Maximum concurrent open positions (across all underlyings).
    max_concurrent_positions: int = 10

    # Maximum positions in any single underlying. 1 = no doubling up.
    max_positions_per_ticker: int = 1

    # Maximum total deployed buying power, as fraction of account.
    # 0.50 = at most half of account tied up in spreads at any time.
    max_total_deployed_pct: float = 0.50

    # Daily loss kill switch threshold. -0.05 = down 5% for the day → halt.
    daily_loss_limit_pct: float = -0.05

    # Position sizing bounds.
    min_contracts_per_spread: int = 1
    max_contracts_per_spread: int = 10  # sanity cap to prevent runaway sizing

    # ── Volatility-scaled sizing ──
    # Short-vol strategies benefit from sizing DOWN when IV is extreme (often a
    # priced binary event — earnings, FDA, etc. — where the "rich" premium is
    # compensation for a real jump risk, not free edge) and sizing normally when
    # IV is moderate. When enabled, the per-trade risk budget is multiplied by a
    # factor that shrinks as the candidate's ATM IV rises past iv_scale_start,
    # down to vol_scale_floor at/above iv_scale_cap.
    use_vol_scaled_sizing: bool = True
    iv_scale_start: float = 0.40   # below this IV, no shrink (factor = 1.0)
    iv_scale_cap: float = 1.00     # at/above this IV, full shrink (factor = floor)
    vol_scale_floor: float = 0.40  # smallest size multiple at extreme IV


# ─── Rejection reasons ──────────────────────────────────────────────────────


class RejectReason:
    DOES_NOT_FIT_RISK_BUDGET = "does_not_fit_risk_budget"
    EXCEEDS_PER_TICKER_LIMIT = "exceeds_per_ticker_limit"
    EXCEEDS_CONCURRENT_LIMIT = "exceeds_concurrent_limit"
    EXCEEDS_BUYING_POWER_CAP = "exceeds_buying_power_cap"
    KILL_SWITCH_ACTIVE = "kill_switch_active"


# ─── Output ─────────────────────────────────────────────────────────────────


@dataclass
class RejectedOrder:
    """An order the risk manager declined to send."""

    fingerprint: str
    symbol: str
    reason: str
    detail: str


@dataclass
class SizedOrder:
    """An order that passed risk checks, with adjusted contracts and max loss."""

    order: SpreadOrder
    contracts: int
    max_loss_dollars: float


@dataclass
class RiskCheckResult:
    """Output of RiskManager.filter_orders()."""

    accepted: list[SizedOrder] = field(default_factory=list)
    rejected: list[RejectedOrder] = field(default_factory=list)

    kill_switch_active: bool = False
    kill_switch_reason: Optional[str] = None

    # Inputs echoed back for the report
    account_value: float = 0.0
    risk_budget_per_trade: float = 0.0
    current_position_count: int = 0
    current_deployed_dollars: float = 0.0
    # Legs we could not pair into a spread. Non-zero means the book is in a
    # state the strategy never creates — a partial fill, a manually closed
    # side — and every cap derived from position counts is approximate.
    unpaired_leg_count: int = 0


# ─── Risk manager ───────────────────────────────────────────────────────────


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config

    def filter_orders(
        self,
        orders: list[SpreadOrder],
        account_value: float,
        current_positions: list[dict],
        today_pnl_pct: float = 0.0,
    ) -> RiskCheckResult:
        """
        Filter and size the proposed orders.

        Args:
            orders: list of SpreadOrders the strategy wants to place.
            account_value: total account equity (e.g. tradier.get_account_value()).
            current_positions: list of position dicts from Tradier
                (broker.get_positions()).
            today_pnl_pct: today's P&L as a fraction of starting equity
                (computed from AccountState).

        Returns:
            RiskCheckResult with accepted/rejected lists.
        """
        cfg = self.config
        result = RiskCheckResult(account_value=account_value)
        result.risk_budget_per_trade = account_value * cfg.risk_pct_per_trade

        # ─── 1. Daily kill switch ────────────────────────────────────────────
        if today_pnl_pct <= cfg.daily_loss_limit_pct:
            result.kill_switch_active = True
            result.kill_switch_reason = (
                f"Today's P&L of {today_pnl_pct:.2%} is at or below limit of "
                f"{cfg.daily_loss_limit_pct:.2%}; no new positions opened."
            )
            logger.warning("KILL SWITCH ACTIVE: %s", result.kill_switch_reason)
            for o in orders:
                result.rejected.append(RejectedOrder(
                    fingerprint=o.fingerprint,
                    symbol=o.symbol,
                    reason=RejectReason.KILL_SWITCH_ACTIVE,
                    detail=result.kill_switch_reason,
                ))
            return result

        # ─── 2. Build state from existing positions ──────────────────────────
        ticker_counts = self._count_open_by_ticker(current_positions)
        deployed_dollars = self._sum_deployed_dollars(current_positions)
        # Each spread is 2 legs, so leg count / 2 = spread count — but ONLY if
        # every leg has a partner. A stray unpaired leg (partial fill, one side
        # closed by hand) used to be silently floored away by integer division:
        # 3 legs read as 1 position instead of 2, loosening the concurrency cap
        # at exactly the moment the book is in a state nobody designed for.
        # We now round UP per ticker and say so loudly.
        odd = {t: c for t, c in ticker_counts.items() if c % 2}
        if odd:
            logger.warning(
                "ODD LEG COUNT on %s — %s. A put credit spread is always 2 legs, "
                "so an odd count means an unpaired leg (partial fill, or one side "
                "closed manually). An unpaired SHORT put is undefined risk. "
                "Counting each stray leg as a full position so the concurrency "
                "cap tightens rather than loosens; go inspect the book.",
                ", ".join(sorted(odd)),
                ", ".join(f"{t}={c} legs" for t, c in sorted(odd.items())),
            )
        result.unpaired_leg_count = len(odd)
        result.current_position_count = sum(
            self._spreads_from_leg_count(c) for c in ticker_counts.values()
        )
        result.current_deployed_dollars = deployed_dollars

        # Track running state as we accept orders
        running_position_count = result.current_position_count
        running_deployed = deployed_dollars
        running_ticker_counts = dict(ticker_counts)

        buying_power_cap = account_value * cfg.max_total_deployed_pct

        # ─── 3. Process each order ───────────────────────────────────────────
        for order in orders:
            # 3a. Size from risk budget
            scale = self._vol_scale_factor(order.atm_iv, cfg)
            scaled_budget = result.risk_budget_per_trade * scale
            contracts = self._size_from_risk_budget(order, scaled_budget)
            if contracts < cfg.min_contracts_per_spread:
                max_loss_per_ct = (order.spread_width - order.target_credit_per_contract) * 100
                result.rejected.append(RejectedOrder(
                    fingerprint=order.fingerprint,
                    symbol=order.symbol,
                    reason=RejectReason.DOES_NOT_FIT_RISK_BUDGET,
                    detail=(
                        f"Per-contract max loss ${max_loss_per_ct:,.0f} exceeds "
                        f"per-trade risk budget ${result.risk_budget_per_trade:,.0f} "
                        f"(account ${account_value:,.0f} × "
                        f"{cfg.risk_pct_per_trade:.1%}). "
                        f"Increase account size or reduce spread width to deploy."
                    ),
                ))
                continue

            contracts = min(contracts, cfg.max_contracts_per_spread)

            # 3b. Per-ticker cap (each spread = 2 legs; a stray leg rounds up —
            # see the odd-leg note above).
            current_ticker_spreads = self._spreads_from_leg_count(
                running_ticker_counts.get(order.symbol.upper(), 0))
            if current_ticker_spreads >= cfg.max_positions_per_ticker:
                result.rejected.append(RejectedOrder(
                    fingerprint=order.fingerprint,
                    symbol=order.symbol,
                    reason=RejectReason.EXCEEDS_PER_TICKER_LIMIT,
                    detail=(
                        f"Already have {current_ticker_spreads} open spread(s) on "
                        f"{order.symbol}; per-ticker limit is "
                        f"{cfg.max_positions_per_ticker}."
                    ),
                ))
                continue

            # 3c. Max concurrent cap
            if running_position_count >= cfg.max_concurrent_positions:
                result.rejected.append(RejectedOrder(
                    fingerprint=order.fingerprint,
                    symbol=order.symbol,
                    reason=RejectReason.EXCEEDS_CONCURRENT_LIMIT,
                    detail=(
                        f"Already at {running_position_count} concurrent positions; "
                        f"max is {cfg.max_concurrent_positions}."
                    ),
                ))
                continue

            # 3d. Buying power cap
            max_loss_for_this_order = (
                (order.spread_width - order.target_credit_per_contract) * 100 * contracts
            )
            if running_deployed + max_loss_for_this_order > buying_power_cap:
                result.rejected.append(RejectedOrder(
                    fingerprint=order.fingerprint,
                    symbol=order.symbol,
                    reason=RejectReason.EXCEEDS_BUYING_POWER_CAP,
                    detail=(
                        f"Adding this order (${max_loss_for_this_order:,.0f}) would "
                        f"push deployed buying power to "
                        f"${running_deployed + max_loss_for_this_order:,.0f}, "
                        f"above cap of ${buying_power_cap:,.0f} "
                        f"({cfg.max_total_deployed_pct:.0%} of account)."
                    ),
                ))
                continue

            # ─── Accepted ────────────────────────────────────────────────────
            result.accepted.append(SizedOrder(
                order=order,
                contracts=contracts,
                max_loss_dollars=max_loss_for_this_order,
            ))
            running_position_count += 1
            running_deployed += max_loss_for_this_order
            # Each new spread = 2 legs against the per-ticker counter
            running_ticker_counts[order.symbol.upper()] = (
                running_ticker_counts.get(order.symbol.upper(), 0) + 2
            )

        logger.info(
            "RiskManager: %d accepted, %d rejected (deployed $%.0f / $%.0f cap)",
            len(result.accepted), len(result.rejected),
            running_deployed, buying_power_cap,
        )
        return result

    # ─── Internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _vol_scale_factor(atm_iv: float, cfg: "RiskConfig") -> float:
        """
        Size multiplier in [vol_scale_floor, 1.0] based on the candidate's ATM
        IV. Full size below iv_scale_start; linearly shrinks to vol_scale_floor
        by iv_scale_cap. This pulls capital away from extreme-IV names (likely
        binary events) toward moderate-IV names where the vol premium is cleaner.
        """
        if not cfg.use_vol_scaled_sizing or atm_iv <= cfg.iv_scale_start:
            return 1.0
        if atm_iv >= cfg.iv_scale_cap:
            return cfg.vol_scale_floor
        # linear interpolation between (iv_scale_start, 1.0) and (iv_scale_cap, floor)
        span = cfg.iv_scale_cap - cfg.iv_scale_start
        frac = (atm_iv - cfg.iv_scale_start) / span if span > 0 else 1.0
        return 1.0 - frac * (1.0 - cfg.vol_scale_floor)

    @staticmethod
    def _size_from_risk_budget(order: SpreadOrder, risk_budget: float) -> int:
        """
        Compute the number of contracts such that max-loss-per-spread doesn't
        exceed risk_budget. Returns 0 if even 1 contract is too risky.
        """
        max_loss_per_contract = (order.spread_width - order.target_credit_per_contract) * 100
        if max_loss_per_contract <= 0:
            # Degenerate case — shouldn't happen if strategy did its job
            return 0
        return math.floor(risk_budget / max_loss_per_contract)

    @staticmethod
    def _count_open_by_ticker(positions: list[dict]) -> Counter:
        """
        Count open option legs per underlying symbol. Each spread contributes
        2 legs; we divide by 2 elsewhere when counting spreads.
        """
        counts: Counter = Counter()
        for p in positions:
            symbol = (p.get("symbol") or "")
            if len(symbol) < 16:
                continue  # not an option
            # OCC option symbol — the underlying is everything before the
            # 15-char date+type+strike suffix. Strip to handle any length.
            underlying = symbol[:-15].upper()
            if underlying:
                counts[underlying] += 1
        return counts

    @staticmethod
    def _spreads_from_leg_count(leg_count: int) -> int:
        """
        Spreads implied by a leg count, rounding UP.

        2 legs = 1 spread. 3 legs = 2 (one complete spread plus a stray leg
        that is still real exposure). Flooring here understated the position
        count whenever the book had an unpaired leg, which loosened the caps
        precisely when the book was in an unexpected state. Rounding up is the
        conservative direction: worst case we decline a trade we could have
        taken, versus taking one past the cap.
        """
        return (max(0, leg_count) + 1) // 2

    @staticmethod
    def _sum_deployed_dollars(positions: list[dict]) -> float:
        """
        Capital at risk across the open book, in TRUE MAX LOSS dollars —
        the same units used to measure every new order, so both sides of the
        buying-power cap finally mean the same thing (see module docstring).

        Legs are paired into spreads and each spread contributes
        (width - credit) * 100 * contracts.

        TRADIER COST-BASIS ASSUMPTION (also documented on PairedPutSpread):
        `cost_basis` on an option leg is TOTAL dollars for that leg —
        premium-per-share × 100 × contracts — negative for shorts (we received)
        and positive for longs (we paid). The credit per spread is therefore
        (|short| - |long|) / contracts.

        Unpaired legs cannot have a defined max loss computed, so they fall
        back to |cost_basis| and are logged. That fallback UNDERSTATES the risk
        of a naked short put badly, which is exactly why it shouts.
        """
        legs = option_legs_only(positions)
        spreads, unpaired = pair_put_spread_legs(legs)
        total = sum(s.max_loss_dollars for s in spreads)

        if unpaired:
            fallback = 0.0
            for p in unpaired:
                try:
                    fallback += abs(float(p.get("cost_basis") or 0))
                except (TypeError, ValueError):
                    continue
            logger.warning(
                "Deployed-capital estimate includes %d UNPAIRED leg(s) (%s) valued "
                "at |cost_basis| = $%.0f. That is premium, not max loss, and for a "
                "naked short put it understates the real risk by a wide margin. "
                "Treat the deployed figure as a floor until the book is clean.",
                len(unpaired),
                ", ".join(str(p.get("symbol")) for p in unpaired[:5]),
                fallback,
            )
            total += fallback

        return total
