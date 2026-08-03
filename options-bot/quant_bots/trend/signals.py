"""
T3 — Signal generation for the trend-following bot.

For each instrument we compute two things from its daily price history:

  1. Time-series momentum — the trailing 12-month total return. Its SIGN is the
     core long/short decision: if the instrument is up over the last year, the
     trend is up, go long; if down, go short. This is the canonical
     managed-futures signal (Moskowitz/Ooi/Pedersen 2012). We also keep the
     magnitude in case we later want to weight by trend strength.

  2. Annualized volatility — the standard deviation of recent daily returns,
     annualized. This feeds position sizing in the risk layer: lower-vol
     instruments get bigger positions so each contributes comparable risk.

Design notes:
  - We fetch ~400 calendar days of daily bars to guarantee ~252 trading days
    for the 12-month lookback plus buffer.
  - The signal computation is pure given a price series, so it's fully testable
    without a broker (we inject a list of closes).
  - A small deadband around zero momentum prevents whipsawing long/short on
    instruments hovering near flat. Inside the deadband the signal is FLAT.
  - MULTI-HORIZON BLEND (the default, not a future option). SignalConfig carries
    a LIST of lookbacks — (63, 126, 252) ≈ 3/6/12 months — and the signal is
    built from all three. Be precise about WHICH blend this is, because two
    plausible constructions behave very differently:
        (a) average the trailing RETURN over each horizon, then take ONE sign;
        (b) take the sign of each horizon, then average the SIGNS (a vote).
    This code does (a). Under (a) a single dominant horizon can carry the
    others: +40% over 12 months and −5% over 3 and 6 months still averages
    positive, so the name goes LONG. Under (b) that same name would be 1 long
    vote vs 2 short votes and would go SHORT. (a) is return-weighted (it
    respects the SIZE of each move); (b) is a robust majority vote that ignores
    magnitude. Neither is "the" answer, but they are materially different
    estimators — do not describe one and implement the other.
  - Every horizon in the blend is GUARANTEED computable: required_bars() takes
    the max over the configured lookbacks, so a name that passes the bar check
    can always be scored on all of them. See required_bars() for why that used
    to silently fail at exactly the boundary.

The daily returns used for the volatility estimate are also RETAINED on the
Signal (`recent_returns`). The risk layer needs them to build a covariance
matrix for correlation-aware portfolio-vol targeting; recomputing them there
would mean re-fetching every price series. Fetch once, carry the returns along.
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
class SignalConfig:
    # Lookback(s) for momentum, in trading days. 252 ≈ 12 months.
    momentum_lookback_days: int = 252
    # Multi-lookback blending: if non-empty, the signal blends the trailing
    # return over EACH of these horizons instead of using the single
    # momentum_lookback_days. Averaging several horizons is a well-supported
    # robustness improvement — it stops the whole strategy hinging on one
    # arbitrary lookback. Default blends 3/6/12 months. Set to [] to fall back
    # to the single momentum_lookback_days window.
    momentum_lookback_days_list: tuple = (63, 126, 252)
    # Window for the volatility estimate, in trading days. 63 ≈ 3 months.
    vol_window_days: int = 63
    # Deadband: |blended return| below this is treated as FLAT (no position).
    #
    # WHY NON-ZERO (this default used to be 0.0, which made FLAT unreachable —
    # it required a trailing return of EXACTLY 0.0, a measure-zero event for a
    # float): the blended 3/6/12-month return of a typical ~20%-annualized-vol
    # instrument has a standard error on the order of 10 percentage points. A
    # blend sitting at ±1% is indistinguishable from zero. Taking a directional
    # position on it buys you an expected trend return of ~0 while paying the
    # full round-trip cost every time the noise changes sign — the classic
    # whipsaw this deadband exists to prevent.
    #
    # 1% is deliberately SMALL relative to that standard error: it is not
    # trying to filter weak trends (the inverse-vol weighting and the risk
    # layer already handle sizing), only to make "no discernible trend" an
    # outcome the code can actually reach. Widening it toward 0.05 trades
    # turnover for participation; that is a tuning decision, not a bug fix.
    momentum_deadband: float = 0.01
    # Floor on bars required to compute a signal at all. The EFFECTIVE
    # requirement is required_bars(), which also respects the longest lookback
    # and the vol window — see that function.
    min_bars_required: int = 252


@dataclass
class Signal:
    symbol: str
    direction: Direction
    momentum_return: float        # trailing total return over the lookback
    annualized_vol: float         # annualized stdev of daily returns
    last_price: float
    bars_used: int
    usable: bool                  # False if not enough data / bad data
    note: str = ""
    # The daily returns behind `annualized_vol` (oldest first, most recent
    # last). Carried so the risk layer can estimate CORRELATIONS between names
    # without re-fetching history. Default-empty so hand-built Signals in tests
    # and callers that don't care keep working.
    recent_returns: list = field(default_factory=list)


def required_bars(config: SignalConfig) -> int:
    """
    The number of clean bars a name genuinely needs before it can be scored.

    This exists because `min_bars_required` alone was a TRAP. It was 252 and the
    longest lookback was also 252, but the blend guarded each horizon with
    `if lb < n` — strictly less than. At exactly n == 252 the 252-day leg was
    silently dropped and the "3/6/12-month blend" quietly became a 3/6-month
    blend. That is not a rare edge: it is every newly listed name and the first
    day of every backtest, i.e. precisely the observations where the signal is
    already most fragile. The blend changed meaning with no log line anywhere.

    The fix is two-sided: the index guard is now `lb <= n` (correct, since
    clean[-lb] exists whenever lb <= n), AND the bar requirement is derived from
    the config rather than being a hand-kept constant that happens to match. Any
    horizon a caller configures is therefore guaranteed computable for every
    name that passes the check.
    """
    lookbacks = list(config.momentum_lookback_days_list) or [config.momentum_lookback_days]
    return max(
        config.min_bars_required,
        max(lookbacks),
        config.vol_window_days + 1,   # +1: N returns need N+1 prices
    )


def calendar_days_to_fetch(lookback_days: int, buffer: float = 1.7) -> int:
    """
    How many CALENDAR days of history to request to be sure of getting
    `lookback_days` TRADING days. ~252 trading days ≈ 365 calendar; we add
    buffer for holidays/weekends and a little slack.
    """
    return int(lookback_days * buffer) + 10


def compute_signal_from_closes(
    symbol: str, closes: list[float], config: SignalConfig
) -> Signal:
    """
    Pure signal computation from a list of daily closing prices (oldest first).
    No network — this is the testable heart of the strategy.
    """
    clean = [c for c in closes if c is not None and c > 0]
    n = len(clean)
    needed = required_bars(config)
    if n < needed:
        return Signal(
            symbol=symbol, direction=Direction.FLAT, momentum_return=0.0,
            annualized_vol=0.0, last_price=(clean[-1] if clean else 0.0),
            bars_used=n, usable=False,
            note=f"Only {n} bars; need {needed}.",
        )

    last_price = clean[-1]

    # ── Momentum: trailing total return, blended across lookback horizons ──
    # If a lookback list is configured, average the trailing return over each
    # horizon (skipping any that need more history than we have). Otherwise use
    # the single momentum_lookback_days window. The blended figure smooths out
    # dependence on any one arbitrary lookback.
    #
    # The guard is `lb <= n`, NOT `lb < n`. clean[-lb] is the price lb-1 bars
    # before the last one, so it exists for every lb up to and including n.
    # `lb < n` rejected lb == n and silently dropped the longest horizon at
    # exactly the bar count required_bars() admits — see required_bars().
    lookbacks = list(config.momentum_lookback_days_list) or [config.momentum_lookback_days]
    horizon_returns = []
    skipped = []
    for lb in lookbacks:
        if lb <= n and clean[-lb] > 0:
            horizon_returns.append((last_price / clean[-lb]) - 1.0)
        else:
            skipped.append(lb)
    if skipped:
        # required_bars() should make this unreachable for the configured
        # horizons. If it ever fires, the blend is NOT the blend the config
        # claims, and that must be visible rather than inferred from returns.
        logger.warning(
            "%s: blending only %s of the configured horizons %s (%d bars) — "
            "the signal is not the horizon mix the config describes.",
            symbol, [lb for lb in lookbacks if lb not in skipped], list(lookbacks), n,
        )
    if horizon_returns:
        momentum_return = sum(horizon_returns) / len(horizon_returns)
    else:
        # Fall back to the longest window we can actually compute
        past_price = clean[-min(config.momentum_lookback_days, n - 1)]
        momentum_return = (last_price / past_price) - 1.0 if past_price > 0 else 0.0

    # ── Direction from momentum sign, with deadband ──
    if momentum_return > config.momentum_deadband:
        direction = Direction.LONG
    elif momentum_return < -config.momentum_deadband:
        direction = Direction.SHORT
    else:
        direction = Direction.FLAT

    # ── Annualized volatility from recent daily returns ──
    vol_window = min(config.vol_window_days, n - 1)
    recent = clean[-(vol_window + 1):]
    daily_returns = [
        (recent[i] / recent[i - 1]) - 1.0
        for i in range(1, len(recent))
        if recent[i - 1] > 0
    ]
    if len(daily_returns) >= 2:
        mean = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        daily_vol = math.sqrt(variance)
        annualized_vol = daily_vol * math.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        annualized_vol = 0.0

    return Signal(
        symbol=symbol, direction=direction, momentum_return=momentum_return,
        annualized_vol=annualized_vol, last_price=last_price,
        bars_used=n, usable=(annualized_vol > 0),
        note="" if annualized_vol > 0 else "Zero volatility estimate.",
        # Carry the same returns the vol estimate was built from — the risk
        # layer pairs them across names to estimate correlations.
        recent_returns=daily_returns,
    )


class SignalGenerator:
    """Fetches history via the broker and produces signals for a basket."""

    def __init__(self, config: SignalConfig, tradier):
        self.config = config
        self.tradier = tradier

    def generate(self, symbols: list[str], today: Optional[date] = None) -> dict[str, Signal]:
        today = today or date.today()
        # Fetch against required_bars(), not momentum_lookback_days: the blend's
        # longest horizon (or the vol window) can exceed the single-window
        # lookback, and asking for too little history silently degrades the
        # signal for every name.
        start = today - timedelta(days=calendar_days_to_fetch(required_bars(self.config)))
        signals: dict[str, Signal] = {}

        for symbol in symbols:
            try:
                bars = self.tradier.get_history(symbol, start=start, end=today, interval="daily")
            except Exception as e:
                logger.warning("History fetch failed for %s: %s", symbol, e)
                signals[symbol] = Signal(symbol, Direction.FLAT, 0.0, 0.0, 0.0, 0, False,
                                          note=f"History error: {e}")
                continue
            closes = [_to_float(b.get("close")) for b in bars]
            signals[symbol] = compute_signal_from_closes(symbol, closes, self.config)

        n_long = sum(1 for s in signals.values() if s.direction == Direction.LONG)
        n_short = sum(1 for s in signals.values() if s.direction == Direction.SHORT)
        n_flat = sum(1 for s in signals.values() if s.direction == Direction.FLAT)
        n_rets = sum(1 for s in signals.values() if len(s.recent_returns) >= 2)
        logger.info("Signals: %d long, %d short, %d flat (of %d); "
                    "%d carry a usable return series for correlation estimation",
                    n_long, n_short, n_flat, len(symbols), n_rets)
        return signals


def _to_float(x) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0
