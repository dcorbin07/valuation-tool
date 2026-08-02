"""
Portfolio sync and position management.

This is the layer that lets the bot *manage* trades rather than just open them.
Each run it:

  1. Pulls current option positions from Tradier (one row per leg).
  2. Pairs legs back into spreads (Tradier doesn't track "spreads", only legs).
  3. Prices each spread at current market (buy-to-close cost).
  4. Computes unrealized P&L vs. the credit originally received.
  5. Decides per spread whether to: HOLD, CLOSE_PROFIT, CLOSE_STOP, or CLOSE_TIME.
  6. Builds closing orders (buy-to-close multileg) for anything not HOLD.

Exit rules (the management half of the strategy):
  - CLOSE_PROFIT: spread has captured >= profit_target_pct of the credit
    (default 50%). Take the win, free the capital, reduce gamma risk.
  - CLOSE_STOP: spread's current loss >= stop_loss_multiple × credit
    (default 2.0×). Cut the loser before it reaches max loss.
  - CLOSE_TIME: DTE <= time_exit_dte (default 21). Close regardless of P&L
    to avoid the high-gamma final weeks where small moves cause big swings.
  - HOLD: none of the above.

Pairing legs into spreads:
  Tradier returns positions as individual legs. To reconstruct a put credit
  spread we group option legs by (underlying, expiration), then within each
  group pair a short put (negative quantity) with the long put (positive
  quantity) one strike-width below it. For the simple 1-spread-per-underlying
  world V5's risk layer enforces, this is unambiguous. If you ever run multiple
  spreads per underlying, this pairing needs the order-tag metadata to be
  exact — noted as a future refinement.

A note on cost basis sign conventions:
  Tradier reports cost_basis as the TOTAL dollars for the whole leg position —
  premium-per-share × 100 × contracts — signed negative for short positions
  (you received money) and positive for long (you paid). We normalize to
  "credit received per spread" = (|short cost basis| - |long cost basis|) /
  contracts, in dollars. Every other module that needs the capital at risk on
  an open spread derives it from that same pairing (see pair_put_spread_legs
  and PairedPutSpread.max_loss_dollars) so there is exactly ONE definition.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from broker import (
    OptionLeg,
    OptionType,
    OrderSide,
    TradierClient,
    parse_occ_symbol,
)
from strategy import make_fingerprint

logger = logging.getLogger(__name__)

CONTRACT_MULTIPLIER = 100.0  # one option contract controls 100 shares


# ─── Config ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PortfolioConfig:
    profit_target_pct: float = 0.50      # close at 50% of max profit captured
    stop_loss_multiple: float = 2.0      # close if loss >= 2x credit received
    time_exit_dte: int = 21              # close at 21 DTE regardless of P&L


# ─── Types ──────────────────────────────────────────────────────────────────


class ExitDecision(Enum):
    HOLD = "hold"
    CLOSE_PROFIT = "close_profit"
    CLOSE_STOP = "close_stop"
    CLOSE_TIME = "close_time"
    CLOSE_EXPIRED = "close_expired"


# ─── Leg pairing (the ONE definition, shared by portfolio / risk / dedup) ────


@dataclass(frozen=True)
class PairedPutSpread:
    """
    Two Tradier position legs recognized as one put credit spread.

    This is the raw, quote-free view: identity, size, and the economics that
    follow from cost basis alone. It exists so that the portfolio manager, the
    risk manager's deployed-capital math, and the open-position fingerprint
    dedup all read the book the SAME way. Previously each had its own idea of
    what an open spread was — and they disagreed (risk measured deployed
    dollars in premium while sizing new orders in max loss, a ~2x mismatch).
    """

    underlying: str
    expiration: date
    short_strike: float
    long_strike: float
    contracts: int
    short_leg: dict
    long_leg: dict

    @property
    def width(self) -> float:
        """Strike width in dollars-per-share (e.g. 5.0 for a 565/560)."""
        return abs(self.short_strike - self.long_strike)

    @property
    def credit_received_per_spread(self) -> float:
        """
        Net credit collected when this spread was opened, in per-spread dollars
        (premium-per-share × 100).

        TRADIER COST-BASIS ASSUMPTION: `cost_basis` on an option position is the
        TOTAL dollars for that leg — premium-per-share × 100 × contracts —
        signed negative when we received money (short) and positive when we paid
        (long). So |short| - |long| is the net credit across ALL contracts, and
        dividing by contracts gives per-spread dollars. If Tradier ever switched
        to per-share cost basis this would be off by 100x, which is why the
        assumption is stated here rather than left implicit at four call sites.
        """
        if self.contracts <= 0:
            return 0.0
        short_cb = abs(_to_float(self.short_leg.get("cost_basis")))
        long_cb = abs(_to_float(self.long_leg.get("cost_basis")))
        return (short_cb - long_cb) / self.contracts

    @property
    def max_loss_dollars(self) -> float:
        """
        Capital genuinely at risk on this spread: (width - credit) × 100 ×
        contracts, floored at zero.

        This — NOT the premium that changed hands — is what a defined-risk
        spread ties up. A $5-wide spread opened for $1.00 has $400 at risk per
        contract while its legs' cost bases sum to only ~$200. Measuring the
        existing book in premium while measuring new orders in max loss put
        both sides of the buying-power cap in different units.
        """
        width_dollars = self.width * CONTRACT_MULTIPLIER
        return max(0.0, (width_dollars - self.credit_received_per_spread) * self.contracts)

    @property
    def fingerprint(self) -> str:
        """Idempotency key for this exact spread (see strategy.make_fingerprint)."""
        return make_fingerprint(
            self.underlying, self.expiration, self.short_strike, self.long_strike,
        )


def pair_put_spread_legs(
    option_legs: list[dict],
) -> tuple[list[PairedPutSpread], list[dict]]:
    """
    Group raw Tradier option-position legs into put credit spreads.

    Legs are bucketed by (underlying, expiration); within a bucket each short
    put (quantity < 0) is paired with the nearest long put strictly below it.
    Anything left over — a non-put, an unparseable symbol, a short with no long
    beneath it, a long nobody claimed — is returned as unpaired. Unpaired legs
    are always a signal that something is off with the book (a partial fill, a
    manually closed side) and every caller should say so out loud.

    Pure: no network, no config. Safe for the risk layer to call.
    """
    puts_by_group: dict[tuple, list[tuple[dict, object]]] = {}
    unpaired: list[dict] = []

    for leg in option_legs:
        symbol = leg.get("symbol", "")
        try:
            opt = parse_occ_symbol(symbol)
        except Exception:
            unpaired.append(leg)
            continue
        if opt.option_type != OptionType.PUT:
            # This strategy only does puts; anything else is unexpected
            unpaired.append(leg)
            continue
        puts_by_group.setdefault((opt.underlying, opt.expiration), []).append((leg, opt))

    spreads: list[PairedPutSpread] = []
    for (underlying, expiration), legs in puts_by_group.items():
        shorts = [(l, o) for (l, o) in legs if _to_float(l.get("quantity")) < 0]
        longs = [(l, o) for (l, o) in legs if _to_float(l.get("quantity")) > 0]

        used_longs: set[int] = set()
        for short_leg, short_opt in shorts:
            candidates = sorted(
                [
                    (i, lo)
                    for i, (ll, lo) in enumerate(longs)
                    if lo.strike < short_opt.strike and i not in used_longs
                ],
                key=lambda t: short_opt.strike - t[1].strike,
            )
            if not candidates:
                unpaired.append(short_leg)
                continue
            long_idx, long_opt = candidates[0]
            used_longs.add(long_idx)
            long_leg = longs[long_idx][0]

            spreads.append(PairedPutSpread(
                underlying=underlying,
                expiration=expiration,
                short_strike=short_opt.strike,
                long_strike=long_opt.strike,
                # 1 short contract = 1 spread.
                contracts=int(abs(_to_float(short_leg.get("quantity")) or 1)),
                short_leg=short_leg,
                long_leg=long_leg,
            ))

        for i, (ll, lo) in enumerate(longs):
            if i not in used_longs:
                unpaired.append(ll)

    return spreads, unpaired


def option_legs_only(positions: list[dict]) -> list[dict]:
    """Keep just the option legs from a Tradier positions list (OCC symbols are >= 16 chars)."""
    return [p for p in positions if len(p.get("symbol", "") or "") >= 16]


def fingerprints_from_positions(
    positions: list[dict], spread_width: float,
) -> set[str]:
    """
    Fingerprints of the spreads currently open, for the strategy's dedup check.

    WHY THIS LIVES IN ONE PLACE: this used to be copy-pasted into both
    orchestrator/jobs.py and scripts/build_orders.py, hard-coded to widths of
    (5.0, 10.0) and emitting SEVEN fingerprints per real spread — one correct
    and six imaginary. An open 565/560 also blocked 570/565, 560/555, 565/555,
    575/565, 560/550 and 570/560, none of which were open. That over-blocking
    was masked only because max_positions_per_ticker=1 rejected those anyway,
    and the hard-coded widths meant changing StrategyConfig.spread_width to,
    say, 2.5 silently disabled idempotency altogether — the same spread would
    re-open every single morning.

    Now: pair the legs and emit exactly one fingerprint per REAL spread.
    `spread_width` is only used for legs we could not pair, where the intended
    partner strike has to be inferred; pass StrategyConfig.spread_width so the
    inference tracks config instead of a hard-coded constant.
    """
    legs = option_legs_only(positions)
    spreads, unpaired = pair_put_spread_legs(legs)
    fingerprints = {s.fingerprint for s in spreads}

    if unpaired:
        logger.warning(
            "%d open option leg(s) could not be paired into spreads: %s. "
            "Falling back to an inferred %.2f-wide partner strike for dedup — "
            "verify the book; an unpaired short put is undefined risk.",
            len(unpaired),
            ", ".join(str(l.get("symbol")) for l in unpaired[:5]),
            spread_width,
        )
    for leg in unpaired:
        try:
            opt = parse_occ_symbol(leg.get("symbol", ""))
        except Exception:
            continue
        if opt.option_type != OptionType.PUT:
            continue
        # A leftover SHORT put is the short leg of a spread whose long we can't
        # see; a leftover LONG put is the long leg of one whose short we can't.
        if _to_float(leg.get("quantity")) < 0:
            fingerprints.add(make_fingerprint(
                opt.underlying, opt.expiration, opt.strike, opt.strike - spread_width))
        else:
            fingerprints.add(make_fingerprint(
                opt.underlying, opt.expiration, opt.strike + spread_width, opt.strike))

    return fingerprints


# ─── Spread pricing (the ONE definition, shared by live and SIM manage) ──────


@dataclass(frozen=True)
class SpreadPricing:
    """Result of trying to price a put credit spread's exit from live quotes."""

    priceable: bool
    close_cost_per_spread: float   # $ to buy-to-close ONE spread; 0.0 if unpriceable
    reason: str = ""               # populated when priceable is False


def price_credit_spread(short_quote: dict, long_quote: dict) -> SpreadPricing:
    """
    Cost to buy back one put credit spread right now, in per-spread dollars.

    We buy the short leg back at its ASK and sell the long leg at its BID, so
    close cost per share = short_ask - long_bid, ×100 for one spread.

    WHY PRICEABILITY IS ASYMMETRIC (this is the whole point of the function):

      * The SHORT leg is priceable only if its ask is positive. You cannot buy
        an option back for nothing — an ask of zero means we got no quote, not
        that the option is free. This is the leg that used to break things: if
        the short failed to quote (short_ask = 0) while the long quoted at
        0.20, the old `if short_ask <= 0 and long_bid <= 0` guard let it
        through and close cost came out NEGATIVE (-$20/spread). A negative
        close cost makes P&L exceed the credit collected, which trips the >=50%
        profit target, which fires a real closing order in live/paper and
        realizes phantom cash into the SIM equity curve. Missing quotes on
        illiquid legs are routine, so this was not a rare path.

      * The LONG leg is priceable if it has ANY live market data at all — a
        positive bid, ask, or last. A long-wing bid of exactly 0.00 is a REAL
        quote with real meaning: nobody will pay a cent for it. That is the
        normal state of the far-OTM long leg on a spread that is winning, and
        rejecting it as "unpriceable" would freeze exactly the spreads we most
        want to close (both the 50% profit target and the 21-DTE time exit
        would stop firing). So we require a market to exist, and then take the
        bid at face value even when it is zero.

    Both legs must be priceable before any close cost is computed.
    """
    short_ask = _to_float(short_quote.get("ask"))
    if short_ask <= 0:  # fall back to last trade before giving up
        short_ask = _to_float(short_quote.get("last"))
    long_bid = _to_float(long_quote.get("bid"))
    if long_bid <= 0:
        long_bid = _to_float(long_quote.get("last"))

    if short_ask <= 0:
        return SpreadPricing(False, 0.0, "short leg has no ask/last quote")
    if not _has_market(long_quote):
        return SpreadPricing(False, 0.0, "long leg has no bid/ask/last quote")

    close_cost_per_spread = (short_ask - long_bid) * CONTRACT_MULTIPLIER
    if close_cost_per_spread < 0:
        # Defensive backstop. A credit spread's buy-to-close cost cannot be
        # negative — nobody pays you to close a short position at a lower
        # strike than the long you sell alongside it. If we ever compute one,
        # the quotes are crossed or stale. Clamp to zero (the most optimistic
        # HONEST mark) and shout, rather than book free money.
        logger.error(
            "NEGATIVE close cost computed (%.2f/spread) from short ask %.4f and "
            "long bid %.4f — quotes are crossed or stale. Clamping to 0. This "
            "should be impossible for a put credit spread; investigate the feed.",
            close_cost_per_spread, short_ask, long_bid,
        )
        close_cost_per_spread = 0.0

    return SpreadPricing(True, close_cost_per_spread)


def _has_market(quote: dict) -> bool:
    """True if a quote carries any positive price at all (bid, ask, or last)."""
    return (
        _to_float(quote.get("bid")) > 0
        or _to_float(quote.get("ask")) > 0
        or _to_float(quote.get("last")) > 0
    )


@dataclass
class SpreadPosition:
    """A reconstructed put credit spread with current pricing and P&L."""

    underlying: str
    expiration: date
    short_strike: float
    long_strike: float
    contracts: int                 # number of spreads (1 contract = 1 spread)
    width: float

    # Original economics (from cost basis)
    credit_received_per_spread: float   # net credit when opened ($/spread)

    # Current market
    short_put_occ: str
    long_put_occ: str
    current_close_cost_per_spread: float  # cost to buy-to-close now ($/spread)

    # P&L. Only meaningful when is_priceable is True — see _price_and_decide.
    unrealized_pnl_dollars: float  # total across all contracts
    pnl_pct_of_credit: float       # fraction of credit captured (0.5 = +50%)
    dte: int

    # Did we get usable quotes for BOTH legs this cycle? When False the P&L
    # fields above are left at zero and must not be reported as a real mark:
    # an unpriced spread is a spread whose value we do not know, which is very
    # different from a spread worth nothing.
    is_priceable: bool = True
    pricing_note: str = ""

    decision: ExitDecision = ExitDecision.HOLD
    decision_reason: str = ""

    def to_closing_legs(self) -> list[OptionLeg]:
        """Closing a put credit spread: buy-to-close short, sell-to-close long."""
        return [
            OptionLeg(self.short_put_occ, OrderSide.BUY_TO_CLOSE, self.contracts),
            OptionLeg(self.long_put_occ, OrderSide.SELL_TO_CLOSE, self.contracts),
        ]


@dataclass
class PortfolioSnapshot:
    spreads: list[SpreadPosition] = field(default_factory=list)
    unpaired_legs: list[dict] = field(default_factory=list)  # legs we couldn't pair
    # Sum of unrealized P&L across the spreads we could actually PRICE. Spreads
    # that failed to quote contribute nothing — see unpriced_spreads.
    total_unrealized_pnl: float = 0.0

    def positions_to_close(self) -> list[SpreadPosition]:
        return [s for s in self.spreads if s.decision != ExitDecision.HOLD]

    @property
    def unpriced_spreads(self) -> list[SpreadPosition]:
        """Spreads we could not quote this cycle. Their P&L is UNKNOWN, not zero."""
        return [s for s in self.spreads if not s.is_priceable]

    @property
    def unpriced_count(self) -> int:
        return len(self.unpriced_spreads)

    def pnl_summary(self) -> str:
        """
        One-line P&L for logs and Discord, honest about coverage.

        The count of unpriced spreads is part of the number's meaning: "P&L
        $1,200 (3 of 8 spreads could not be priced)" tells you the figure
        covers five positions. Reporting a bare $1,200 there is a lie of
        omission, and the old code told a bigger one — it marked unpriceable
        spreads at a full 100% profit and summed that in.
        """
        base = f"P&L ${self.total_unrealized_pnl:,.0f}"
        if self.unpriced_count:
            base += (f" ({self.unpriced_count} of {len(self.spreads)} spreads "
                     f"could not be priced)")
        return base


# ─── Portfolio manager ──────────────────────────────────────────────────────


class PortfolioManager:
    def __init__(self, config: PortfolioConfig, tradier: TradierClient):
        self.config = config
        self.tradier = tradier

    def sync(self, today: Optional[date] = None) -> PortfolioSnapshot:
        """Pull positions, pair into spreads, price, decide exits."""
        today = today or date.today()
        positions = self.tradier.get_positions()

        # Keep only option legs
        option_legs = option_legs_only(positions)
        logger.info("Portfolio sync: %d option legs from Tradier", len(option_legs))

        paired, unpaired = pair_put_spread_legs(option_legs)
        spreads = [self._build_spread(p) for p in paired]
        if unpaired:
            logger.warning(
                "Paired into %d spreads but %d leg(s) are UNPAIRED: %s. An "
                "unpaired short put is undefined risk; check the book.",
                len(spreads), len(unpaired),
                ", ".join(str(l.get("symbol")) for l in unpaired[:5]),
            )
        else:
            logger.info("Paired into %d spreads (0 unpaired legs)", len(spreads))

        # Price all the legs in one batch quote call
        occ_symbols = []
        for s in spreads:
            occ_symbols.extend([s.short_put_occ, s.long_put_occ])
        quote_by_symbol = self._batch_quote(occ_symbols)

        snapshot = PortfolioSnapshot(unpaired_legs=unpaired)
        for spread in spreads:
            self._price_and_decide(spread, quote_by_symbol, today)
            snapshot.spreads.append(spread)
            # Unpriceable spreads contribute NOTHING to the total. Their P&L is
            # unknown, and the snapshot reports how many were skipped so the
            # total is never mistaken for full coverage.
            if spread.is_priceable:
                snapshot.total_unrealized_pnl += spread.unrealized_pnl_dollars

        if snapshot.unpriced_count:
            logger.warning(
                "Portfolio: %d of %d spreads could not be priced (%s); their "
                "P&L is EXCLUDED from the $%.2f total, not counted as zero.",
                snapshot.unpriced_count, len(snapshot.spreads),
                "; ".join(f"{s.underlying} {s.pricing_note}"
                          for s in snapshot.unpriced_spreads[:5]),
                snapshot.total_unrealized_pnl,
            )
        logger.info(
            "Portfolio: total unrealized P&L $%.2f, %d to close",
            snapshot.total_unrealized_pnl,
            len(snapshot.positions_to_close()),
        )
        return snapshot

    # ─── Pairing ─────────────────────────────────────────────────────────────

    def _build_spread(self, paired: PairedPutSpread) -> SpreadPosition:
        """Inflate a raw PairedPutSpread into the quote-carrying SpreadPosition."""
        return SpreadPosition(
            underlying=paired.underlying,
            expiration=paired.expiration,
            short_strike=paired.short_strike,
            long_strike=paired.long_strike,
            contracts=paired.contracts,
            width=paired.width,
            credit_received_per_spread=paired.credit_received_per_spread,
            short_put_occ=paired.short_leg["symbol"],
            long_put_occ=paired.long_leg["symbol"],
            current_close_cost_per_spread=0.0,  # filled in pricing step
            unrealized_pnl_dollars=0.0,
            pnl_pct_of_credit=0.0,
            dte=0,
        )

    # ─── Pricing & decision ──────────────────────────────────────────────────

    def _batch_quote(self, occ_symbols: list[str]) -> dict[str, dict]:
        if not occ_symbols:
            return {}
        result: dict[str, dict] = {}
        # Tradier quote endpoint takes up to ~50 symbols per call
        for i in range(0, len(occ_symbols), 50):
            batch = occ_symbols[i : i + 50]
            try:
                quotes = self.tradier.get_quotes(batch)
            except Exception as e:
                logger.warning("Quote batch failed: %s", e)
                continue
            for q in quotes:
                sym = q.get("symbol")
                if sym:
                    result[sym] = q
        return result

    def _price_and_decide(
        self, spread: SpreadPosition, quotes: dict[str, dict], today: date
    ) -> None:
        cfg = self.config

        short_q = quotes.get(spread.short_put_occ, {})
        long_q = quotes.get(spread.long_put_occ, {})

        spread.dte = (spread.expiration - today).days

        # ─── Price FIRST, and bail out before writing any P&L ────────────────
        # ORDER MATTERS HERE. This check used to sit forty lines further down,
        # AFTER the P&L fields were written. With both legs unquoted the close
        # cost came out as 0, so pnl_per_spread equalled the full credit and
        # every unpriceable spread was silently marked at 100% profit — then
        # summed into snapshot.total_unrealized_pnl and reported to Discord.
        # The DECISION was correctly HOLD; the NUMBER was fiction.
        pricing = price_credit_spread(short_q, long_q)
        if not pricing.priceable:
            spread.is_priceable = False
            spread.pricing_note = pricing.reason
            spread.current_close_cost_per_spread = 0.0
            spread.unrealized_pnl_dollars = 0.0
            spread.pnl_pct_of_credit = 0.0
            spread.decision = ExitDecision.HOLD
            spread.decision_reason = (
                f"Could not price spread ({pricing.reason}); holding. "
                f"P&L is UNKNOWN this cycle, not zero."
            )
            logger.warning(
                "Could not price %s %s/%s exp %s: %s. Holding; excluding from P&L.",
                spread.underlying, spread.short_strike, spread.long_strike,
                spread.expiration, pricing.reason,
            )
            return

        spread.is_priceable = True
        spread.pricing_note = ""
        spread.current_close_cost_per_spread = pricing.close_cost_per_spread

        # Unrealized P&L per spread = credit received - cost to close now.
        # (We collected the credit; we'd pay close_cost to exit. If close cost
        # is less than the credit, we're in profit.)
        pnl_per_spread = spread.credit_received_per_spread - spread.current_close_cost_per_spread
        spread.unrealized_pnl_dollars = pnl_per_spread * spread.contracts

        credit = spread.credit_received_per_spread
        if credit > 0:
            # pnl_pct_of_credit: +1.0 means captured the full credit (closed at 0),
            # -2.0 means lost twice the credit.
            spread.pnl_pct_of_credit = pnl_per_spread / credit
        else:
            spread.pnl_pct_of_credit = 0.0

        # ─── Decide ──────────────────────────────────────────────────────────
        if spread.pnl_pct_of_credit >= cfg.profit_target_pct:
            spread.decision = ExitDecision.CLOSE_PROFIT
            spread.decision_reason = (
                f"Captured {spread.pnl_pct_of_credit:.0%} of credit "
                f"(target {cfg.profit_target_pct:.0%})."
            )
        elif spread.pnl_pct_of_credit <= -cfg.stop_loss_multiple:
            spread.decision = ExitDecision.CLOSE_STOP
            spread.decision_reason = (
                f"Loss of {abs(spread.pnl_pct_of_credit):.1f}x credit "
                f"(stop at {cfg.stop_loss_multiple:.1f}x)."
            )
        elif spread.dte <= cfg.time_exit_dte:
            spread.decision = ExitDecision.CLOSE_TIME
            spread.decision_reason = (
                f"{spread.dte} DTE <= time exit {cfg.time_exit_dte}."
            )
        else:
            spread.decision = ExitDecision.HOLD
            spread.decision_reason = (
                f"P&L {spread.pnl_pct_of_credit:+.0%} of credit, {spread.dte} DTE."
            )


def _to_float(x) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0
