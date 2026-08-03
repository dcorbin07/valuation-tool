"""
Screener.

Takes a UniverseSnapshot (~1000+ tickers) and produces a list of
ScreenedCandidate objects (~50-150 names) that meet all of:

    1. An option expiration exists in the configured DTE window
    2. No earnings between today and the target expiration
    3. The option chain has greeks populated
    4. A put exists at approximately the target delta (default 20)
    5. The short put has tight bid-ask spread (default <= 10% of mid)
    6. The short put has sufficient open interest
    7. A long put exists at the configured width below the short
    8. ATM IV is above the configured minimum (proxy signal — see note below)

Survivors are ranked by ATM IV descending: trade where the premium is richest.

A note on ATM IV: This is NOT IV rank. True IV rank requires historical IV
data, which Tradier does not expose. For now we use the current ATM put's
implied volatility as a soft filter. When a paid options data source is added
(V7 / backtesting), this gets swapped for real IV rank without changing the
rest of the pipeline.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from broker import TradierClient, TradierError
from data.earnings import EarningsCalendar
from data.universe import UniverseSnapshot, UniverseTicker

logger = logging.getLogger(__name__)


# ─── Config ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScreenerConfig:
    """All screening parameters in one place."""

    # Days-to-expiration window for picking the target expiration.
    # Within this window we pick the expiration closest to target_dte.
    min_dte: int = 25
    max_dte: int = 50
    target_dte: int = 35

    # Short put delta target. We pick the put whose absolute delta is closest
    # to this value (across all puts in the chain).
    target_short_delta: float = 0.20

    # Maximum acceptable distance from target_short_delta. Drops tickers whose
    # closest available put delta is too far from our target (e.g., illiquid
    # chains with sparse strikes).
    max_delta_distance: float = 0.05

    # Spread width in dollars (the gap between short and long strikes).
    spread_width: float = 5.0
    # Tolerance when looking up the long strike — sandbox chains sometimes
    # have strikes at 5.01 instead of 5.00 etc.
    long_strike_tolerance: float = 0.51

    # Liquidity gates on the short put leg.
    max_bid_ask_pct: float = 0.10  # bid-ask spread <= 10% of mid
    min_short_put_open_interest: int = 100

    # ATM IV proxy threshold (current 0.50-delta put IV, not historical rank).
    # 0.25 = 25% annualized vol minimum.
    min_atm_iv: float = 0.25

    # Filter toggles. The screener still computes the underlying values when
    # these are False, but doesn't drop tickers based on them.
    apply_earnings_filter: bool = True
    apply_atm_iv_filter: bool = True

    # Progress logging interval (log every N tickers processed).
    progress_log_every: int = 100


# ─── Output types ───────────────────────────────────────────────────────────


@dataclass
class ScreenedCandidate:
    """A ticker that has passed every screening filter, with all the data the
    strategy layer needs to construct the order."""

    symbol: str
    last_price: float
    is_etf: bool

    target_expiration: date
    dte: int

    # Short put leg
    short_put_strike: float
    short_put_delta: float
    short_put_bid: float
    short_put_ask: float
    short_put_mid: float
    short_put_iv: float
    short_put_open_interest: int

    # Long put leg
    long_put_strike: float
    long_put_bid: float
    long_put_ask: float
    long_put_mid: float

    # Spread economics
    spread_credit_mid: float       # net credit at chain mids ($ per spread, not per share)
    spread_max_loss: float         # (width - credit) * 100, per spread
    spread_return_on_risk: float   # credit / max_loss

    # IV signal
    atm_iv: float                  # ATM put IV; proxy for "is premium fat right now"

    # Earnings context (None means unknown, not "no earnings")
    next_earnings: Optional[date] = None


@dataclass
class FunnelStats:
    """How many tickers were dropped at each stage. Useful for debugging
    when the screener returns fewer candidates than expected."""

    input: int = 0
    no_expiration_in_dte: int = 0
    has_earnings_in_window: int = 0
    chain_empty: int = 0
    no_short_strike: int = 0
    short_strike_too_far_from_target: int = 0
    short_mid_invalid: int = 0
    bid_ask_too_wide: int = 0
    low_open_interest: int = 0
    no_long_strike: int = 0
    long_mid_invalid: int = 0
    no_atm_strike: int = 0
    atm_iv_too_low: int = 0
    api_error: int = 0
    passed: int = 0


@dataclass
class ScreenerResult:
    run_timestamp_utc: str
    universe_count: int
    config: dict
    stats: FunnelStats
    candidates: list[ScreenedCandidate] = field(default_factory=list)


# ─── Screener ───────────────────────────────────────────────────────────────


class Screener:
    """
    Run the full screening pipeline.

    Usage:
        screener = Screener(config, tradier_client, earnings_calendar)
        result = screener.screen(universe_snapshot)
        screener.save(result, Path("data/cache/candidates_2026-05-19.json"))
    """

    def __init__(
        self,
        config: ScreenerConfig,
        tradier: TradierClient,
        earnings: Optional[EarningsCalendar] = None,
    ):
        self.config = config
        self.tradier = tradier
        if config.apply_earnings_filter and earnings is None:
            raise ValueError(
                "Earnings filter enabled but no EarningsCalendar provided."
            )
        self.earnings = earnings

    def screen(self, universe: UniverseSnapshot) -> ScreenerResult:
        stats = FunnelStats(input=len(universe.tickers))
        candidates: list[ScreenedCandidate] = []
        today = date.today()

        for i, ticker in enumerate(universe.tickers, start=1):
            if i % self.config.progress_log_every == 0:
                logger.info(
                    "Screening progress: %d/%d (passed so far: %d)",
                    i,
                    len(universe.tickers),
                    stats.passed,
                )

            try:
                candidate = self._screen_one(ticker, today, stats)
            except TradierError as e:
                logger.debug("Tradier error on %s: %s", ticker.symbol, e)
                stats.api_error += 1
                continue
            except Exception as e:  # belt-and-suspenders for unexpected shapes
                logger.warning("Unexpected error screening %s: %s", ticker.symbol, e)
                stats.api_error += 1
                continue

            if candidate is not None:
                candidates.append(candidate)
                stats.passed += 1

        # Sort by ATM IV descending — we want the fattest premium first.
        candidates.sort(key=lambda c: c.atm_iv, reverse=True)

        logger.info(
            "Screener complete: %d/%d tickers passed all filters",
            stats.passed,
            stats.input,
        )

        return ScreenerResult(
            run_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            universe_count=len(universe.tickers),
            config=asdict(self.config),
            stats=stats,
            candidates=candidates,
        )

    # ─── The per-ticker pipeline ─────────────────────────────────────────────

    def _screen_one(
        self,
        ticker: UniverseTicker,
        today: date,
        stats: FunnelStats,
    ) -> Optional[ScreenedCandidate]:
        cfg = self.config

        # 1. Target expiration
        expirations = self.tradier.get_option_expirations(ticker.symbol)
        target_exp = self._pick_target_expiration(expirations, today)
        if target_exp is None:
            stats.no_expiration_in_dte += 1
            return None
        dte = (target_exp - today).days

        # 2. Earnings filter
        next_earnings: Optional[date] = None
        if cfg.apply_earnings_filter and self.earnings is not None:
            # ETFs typically don't have earnings; this returns None and the
            # safe-default in EarningsCalendar lets them through.
            next_earnings = self.earnings.get_next_earnings(ticker.symbol)
            if next_earnings is not None and today <= next_earnings <= target_exp:
                stats.has_earnings_in_window += 1
                return None

        # 3. Pull chain
        chain = self.tradier.get_option_chain(
            ticker.symbol, target_exp, with_greeks=True
        )
        puts = [o for o in chain if o.get("option_type") == "put"]
        if not puts:
            stats.chain_empty += 1
            return None

        # 4. Find short put at target delta
        short_put, delta_distance = self._find_target_delta_put(
            puts, cfg.target_short_delta
        )
        if short_put is None:
            stats.no_short_strike += 1
            return None
        if delta_distance > cfg.max_delta_distance:
            stats.short_strike_too_far_from_target += 1
            return None

        short_strike = float(short_put["strike"])
        short_bid = _to_float(short_put.get("bid"))
        short_ask = _to_float(short_put.get("ask"))
        short_mid = (short_bid + short_ask) / 2.0
        short_oi = int(short_put.get("open_interest") or 0)
        greeks = short_put.get("greeks") or {}
        short_delta = abs(_to_float(greeks.get("delta")))
        short_iv = _to_float(greeks.get("mid_iv") or greeks.get("smv_vol"))

        if short_mid <= 0 or short_ask <= 0:
            stats.short_mid_invalid += 1
            return None

        # 5. Bid-ask gate on short put
        bid_ask_pct = (short_ask - short_bid) / short_mid if short_mid > 0 else 1.0
        if bid_ask_pct > cfg.max_bid_ask_pct:
            stats.bid_ask_too_wide += 1
            return None

        # 6. Open interest gate
        if short_oi < cfg.min_short_put_open_interest:
            stats.low_open_interest += 1
            return None

        # 7. Long put at target width below
        long_strike_target = short_strike - cfg.spread_width
        long_put = self._find_strike(puts, long_strike_target, cfg.long_strike_tolerance)
        if long_put is None:
            stats.no_long_strike += 1
            return None
        long_strike = float(long_put["strike"])
        long_bid = _to_float(long_put.get("bid"))
        long_ask = _to_float(long_put.get("ask"))
        long_mid = (long_bid + long_ask) / 2.0

        if long_mid <= 0:
            stats.long_mid_invalid += 1
            return None

        # 8. ATM IV (use a put nearest 0.50 delta as the ATM reference)
        atm_put, _ = self._find_target_delta_put(puts, 0.50)
        if atm_put is None:
            stats.no_atm_strike += 1
            return None
        atm_greeks = atm_put.get("greeks") or {}
        atm_iv = _to_float(atm_greeks.get("mid_iv") or atm_greeks.get("smv_vol"))
        if cfg.apply_atm_iv_filter and atm_iv < cfg.min_atm_iv:
            stats.atm_iv_too_low += 1
            return None

        # Spread economics
        spread_credit = short_mid - long_mid
        spread_max_loss = (cfg.spread_width - spread_credit) * 100.0
        spread_return = (
            spread_credit / (cfg.spread_width - spread_credit)
            if (cfg.spread_width - spread_credit) > 0
            else 0.0
        )

        return ScreenedCandidate(
            symbol=ticker.symbol,
            last_price=ticker.last_price,
            is_etf=ticker.is_etf,
            target_expiration=target_exp,
            dte=dte,
            short_put_strike=short_strike,
            short_put_delta=short_delta,
            short_put_bid=short_bid,
            short_put_ask=short_ask,
            short_put_mid=short_mid,
            short_put_iv=short_iv,
            short_put_open_interest=short_oi,
            long_put_strike=long_strike,
            long_put_bid=long_bid,
            long_put_ask=long_ask,
            long_put_mid=long_mid,
            spread_credit_mid=spread_credit,
            spread_max_loss=spread_max_loss,
            spread_return_on_risk=spread_return,
            atm_iv=atm_iv,
            next_earnings=next_earnings,
        )

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _pick_target_expiration(
        self, expirations: list[date], today: date
    ) -> Optional[date]:
        """Pick the expiration in [min_dte, max_dte] closest to target_dte."""
        viable = [
            e
            for e in expirations
            if self.config.min_dte <= (e - today).days <= self.config.max_dte
        ]
        if not viable:
            return None
        return min(viable, key=lambda e: abs((e - today).days - self.config.target_dte))

    def _find_target_delta_put(
        self, puts: list[dict], target_abs_delta: float
    ) -> tuple[Optional[dict], float]:
        """Return (put closest to target |delta|, distance_in_delta) or (None, inf)."""
        best_opt: Optional[dict] = None
        best_dist = float("inf")
        for opt in puts:
            greeks = opt.get("greeks") or {}
            delta = greeks.get("delta")
            if delta is None:
                continue
            try:
                d = abs(abs(float(delta)) - target_abs_delta)
            except (TypeError, ValueError):
                continue
            if d < best_dist:
                best_dist = d
                best_opt = opt
        return best_opt, best_dist

    def _find_strike(
        self, puts: list[dict], target_strike: float, tolerance: float
    ) -> Optional[dict]:
        """Find a put whose strike is within `tolerance` dollars of target."""
        best_opt: Optional[dict] = None
        best_dist = float("inf")
        for opt in puts:
            try:
                strike = float(opt["strike"])
            except (KeyError, TypeError, ValueError):
                continue
            d = abs(strike - target_strike)
            if d < best_dist and d <= tolerance:
                best_dist = d
                best_opt = opt
        return best_opt

    # ─── Persistence ─────────────────────────────────────────────────────────

    @staticmethod
    def save(result: ScreenerResult, path: Path) -> None:
        """Persist a screener result to disk as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)

        def _serialize_candidate(c: ScreenedCandidate) -> dict:
            d = asdict(c)
            d["target_expiration"] = c.target_expiration.isoformat()
            d["next_earnings"] = (
                c.next_earnings.isoformat() if c.next_earnings else None
            )
            return d

        payload = {
            "run_timestamp_utc": result.run_timestamp_utc,
            "universe_count": result.universe_count,
            "config": result.config,
            "stats": asdict(result.stats),
            "candidate_count": len(result.candidates),
            "candidates": [_serialize_candidate(c) for c in result.candidates],
        }
        path.write_text(json.dumps(payload, indent=2))
        logger.info("Saved screener result to %s", path)


def _to_float(x) -> float:
    """Coerce a possibly-None / possibly-string value to float, defaulting to 0."""
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0
