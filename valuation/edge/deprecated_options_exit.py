"""
ARCHIVED — NOT LIVE, NOT TESTED AS PRODUCTION, NOT PART OF ANY RESULT.
Quarantined by AUDIT B16 and renamed so it cannot be mistaken for live code.

THE LIVE EXIT LOGIC IS THE INLINE DAY-WALK LOOP IN
`valuation/edge/options_backtest.simulate_trade`. This module evaluates an exit on the
UNDERLYING (+/-1 sigma on the stock) and has never contributed to a reported number.
It is imported only by tests/test_intraday.py — contrary to the audit's 'imported by
nothing', which was a code-reading finding and is corrected here.

--------------------------------------------------------------------------------------
Options exit rule — a first-cut, honest placeholder.

Until we have real options price history, "how did the screaming-buy options signals do?"
can only be answered on the UNDERLYING. Reporting the raw forward return of the underlying
overstates the case badly, because a real options position is closed out long before the
horizon ends — by a profit target, a stop, or expiry.

So we apply the exit discipline an options trader would actually use, evaluated on the
underlying, and take whichever triggers FIRST:

  * take-profit  at +1 expected move (1 sigma) from entry
  * stop-loss    at -1 expected move
  * time stop    at the contract's days-to-expiry

The expected move is the same one contracts.py frames the trade with:

    sigma = price * vol * sqrt(DTE / 365)

using the entry implied vol when we have it, and otherwise the realized volatility of the
60 trading days BEFORE entry (strictly pre-entry, so there's no look-ahead).

Known limits, stated plainly so nobody reads more into this than it supports:
  * It measures the *underlying*, not option P&L. It ignores premium paid, theta, vega and
    the fact that a 1-sigma underlying move does not translate linearly into option value.
  * Daily closes only — an intraday spike through the target or stop isn't seen.
  * When a single day's move clears BOTH levels we record the STOP, not the profit. That's
    the conservative reading and it keeps the number from flattering itself.

It is a directional-discipline proxy, and a placeholder until real options-history
backtesting replaces it.
"""
from __future__ import annotations

import math
from typing import Optional

# Mid days-to-expiry per horizon, matching the bands in intraday/contracts.py.
DTE_MID = {"short": 28, "swing": 60, "position": 135}
DEFAULT_VOL = 0.30            # used only when neither IV nor enough history is available
VOL_LOOKBACK = 60             # trading days before entry for the realized-vol fallback
TRADING_DAYS_PER_YEAR = 252


def realized_vol(closes, end_idx: int, lookback: int = VOL_LOOKBACK) -> Optional[float]:
    """Annualized realized vol from the `lookback` closes ENDING AT end_idx (exclusive).

    Strictly pre-entry by construction — `end_idx` is the entry bar and is not included,
    so this can never see the move it's being used to size.
    """
    start = max(0, end_idx - lookback)
    window = [float(c) for c in closes[start:end_idx] if c is not None and float(c) > 0]
    if len(window) < 20:
        return None
    rets = [math.log(window[i] / window[i - 1]) for i in range(1, len(window))]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    sd = math.sqrt(var)
    return sd * math.sqrt(TRADING_DAYS_PER_YEAR)


def simulate_exit(closes, entry_idx: int, horizon: str = "swing", direction: str = "bull",
                  iv: Optional[float] = None, dates=None) -> Optional[dict]:
    """Walk forward from `entry_idx` and return the first-triggered exit.

    `closes` is a list/array of daily closes; `entry_idx` indexes the entry bar.
    Returns None when there isn't a valid entry price.
    """
    if entry_idx is None or entry_idx < 0 or entry_idx >= len(closes) - 1:
        return None
    try:
        entry = float(closes[entry_idx])
    except (TypeError, ValueError):
        return None
    if entry <= 0:
        return None

    dte = DTE_MID.get(horizon, DTE_MID["swing"])
    vol = iv if (iv and iv > 0) else realized_vol(closes, entry_idx)
    if not vol or vol <= 0:
        vol = DEFAULT_VOL
    em_pct = vol * math.sqrt(dte / 365.0)          # 1 sigma over the contract's life

    bull = direction != "bear"
    target = entry * (1 + em_pct) if bull else entry * (1 - em_pct)
    stop = entry * (1 - em_pct) if bull else entry * (1 + em_pct)

    # The time stop is DTE calendar days; the series is trading days.
    max_bars = max(1, int(round(dte * TRADING_DAYS_PER_YEAR / 365.0)))
    last = min(entry_idx + max_bars, len(closes) - 1)

    outcome, exit_idx, exit_px = "time_stop", last, None
    for i in range(entry_idx + 1, last + 1):
        try:
            px = float(closes[i])
        except (TypeError, ValueError):
            continue
        if px <= 0:
            continue
        hit_tp = px >= target if bull else px <= target
        hit_sl = px <= stop if bull else px >= stop
        # Both on one bar: record the stop. Daily closes can't tell us which came
        # first intraday, and the pessimistic read is the honest one.
        if hit_sl:
            outcome, exit_idx, exit_px = "stop_loss", i, px
            break
        if hit_tp:
            outcome, exit_idx, exit_px = "take_profit", i, px
            break
    if exit_px is None:
        try:
            exit_px = float(closes[exit_idx])
        except (TypeError, ValueError):
            return None

    raw = exit_px / entry - 1.0
    directional = raw if bull else -raw            # a bearish signal profits when price falls
    return {"outcome": outcome, "entry_price": entry, "exit_price": exit_px,
            "entry_idx": entry_idx, "exit_idx": exit_idx,
            "bars_held": exit_idx - entry_idx,
            "underlying_return": raw, "signal_return": directional,
            "expected_move_pct": em_pct, "target": target, "stop": stop,
            "dte": dte, "horizon": horizon, "direction": "bear" if not bull else "bull",
            "entry_date": (dates[entry_idx] if dates is not None and entry_idx < len(dates) else None),
            "exit_date": (dates[exit_idx] if dates is not None and exit_idx < len(dates) else None)}


def summarize_exits(exits) -> dict:
    """Aggregate simulated exits: win rate, average return, and the exit-reason mix."""
    rows = [e for e in exits if e]
    if not rows:
        return {"n": 0}
    rets = [e["signal_return"] for e in rows]
    by_outcome = {}
    for e in rows:
        by_outcome[e["outcome"]] = by_outcome.get(e["outcome"], 0) + 1
    wins = sum(1 for r in rets if r > 0)
    return {
        "n": len(rows),
        "avg_return": sum(rets) / len(rets),
        "win_rate": wins / len(rets),
        "avg_bars_held": sum(e["bars_held"] for e in rows) / len(rows),
        "by_outcome": by_outcome,
        "take_profit_rate": by_outcome.get("take_profit", 0) / len(rows),
        "stop_loss_rate": by_outcome.get("stop_loss", 0) / len(rows),
        "time_stop_rate": by_outcome.get("time_stop", 0) / len(rows),
        "note": ("Exits simulated on the underlying (first of +1σ target, −1σ stop, or the "
                 "contract's DTE). Not option P&L — no premium, theta or vega. A placeholder "
                 "until real options history is available."),
    }
