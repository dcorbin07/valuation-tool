"""
Market-regime "risk-off" overlay — PRE-SPECIFIED RULE. Committed BEFORE it was ever run.

This file exists in its own commit, with no results in it, precisely so the git history proves
the rule and its thresholds were fixed before any number came back. Everything this project has
learned about itself says that matters: with ~18 years of data there are only one or two real
crashes, so ANY rule tuned after the fact can be made to "dodge 2008", and that tells you
nothing about the next one.

THE RULE (classic Faber-style trend filter, deliberately the plainest thing that could work):

    At each REBALANCE date, compare the benchmark's close to its own trailing simple moving
    average over TREND_MA_DAYS trading days, using only closes on or before that date.

        close >  MA  ->  exposure = 1.0            (fully invested)
        close <= MA  ->  exposure = RISK_OFF_EXPOSURE

    Exposure scales the book's period return; the rest sits in cash at CASH_ANNUAL_RATE.
    The signal is evaluated ONLY at rebalance dates, because that is when the book trades
    anyway — a daily-checked overlay would be a different (and much more turnover-heavy)
    strategy, and pretending we could act daily on a quarterly book would be dishonest.

PRE-COMMITTED PARAMETERS — not to be changed after seeing results:

    TREND_MA_DAYS      = 200        the standard ~10-month filter, not a swept value
    RISK_OFF_EXPOSURE  = 0.0, 0.5   full de-risk and half de-risk, both reported
    CASH_ANNUAL_RATE   = 0.0        cash earns NOTHING

CASH AT ZERO IS DELIBERATE AND CONSERVATIVE-AGAINST-THE-OVERLAY IN ONE DIRECTION AND NOT THE
OTHER, so state it: real T-bills paid ~2-5% over much of this window, so a real risk-off
investor would have earned something while out. Crediting 0% understates the overlay's return.
We have no point-in-time bill series on disk, and inventing one would be a fudge, so the
overlay is judged on the harsher assumption. If it wins ANYWAY, the win is real; if it loses on
return, some of that gap is missing interest.

ADOPTION BAR — also pre-committed:

    1. Max drawdown must improve MATERIALLY: at least MIN_DD_IMPROVEMENT.
    2. The return give-up must be at most MAX_RETURN_GIVEUP.
    3. It must HOLD UP OUT OF SAMPLE — improve drawdown in BOTH time halves. A rule that only
       works in the half containing 2008 is a rule that fits one episode.
    4. Whipsaw is reported (how many times it flips), because an overlay that flips constantly
       is one that will bleed in a chop even if the backtest likes it.

Failing any of these is a REJECT, and rejecting is the expected outcome — trend overlays are
among the most data-mined ideas in finance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TREND_MA_DAYS = 200
RISK_OFF_EXPOSURE = (0.0, 0.5)
CASH_ANNUAL_RATE = 0.0

# Adoption bar, fixed in advance.
MIN_DD_IMPROVEMENT = 0.05      # cut max drawdown by >= 5 percentage points
MAX_RETURN_GIVEUP = 0.03       # give up <= 3 percentage points of annualized return


def trend_signal(bench_dates, bench_closes, at_dates, ma_days: int = TREND_MA_DAYS) -> dict:
    """{date: True if invested} — benchmark close vs its own trailing MA, strictly past data.

    `at_dates` are the rebalance dates. For each, the MA uses the `ma_days` closes ending ON
    that date, so nothing after the decision point is ever used.
    """
    idx = pd.to_datetime(list(bench_dates))
    s = pd.Series(list(bench_closes), index=idx).sort_index()
    ma = s.rolling(ma_days, min_periods=ma_days).mean()
    out = {}
    for d in at_dates:
        ts = pd.to_datetime(d)
        past = s.index[s.index <= ts]
        if len(past) == 0:
            continue
        last = past[-1]
        m = ma.get(last)
        if m is None or m != m:
            out[d] = True          # not enough history yet -> stay invested (no free hindsight)
            continue
        out[d] = bool(s.loc[last] > m)
    return out


def apply_overlay(period_returns, dates, invested: dict, off_exposure: float,
                  cash_annual: float = CASH_ANNUAL_RATE, periods_per_year: float = 6.0):
    """Scale each period's book return by the regime exposure; the rest earns cash.

    Returns (overlaid_returns, n_flips, share_invested).
    """
    cash_per_period = (1.0 + cash_annual) ** (1.0 / periods_per_year) - 1.0
    out, flips, prev, inv_n = [], 0, None, 0
    for r, d in zip(period_returns, dates):
        on = invested.get(d, True)
        exp = 1.0 if on else float(off_exposure)
        if prev is not None and exp != prev:
            flips += 1
        prev = exp
        inv_n += 1 if on else 0
        out.append(exp * r + (1.0 - exp) * cash_per_period)
    return out, flips, (inv_n / len(out) if out else None)
