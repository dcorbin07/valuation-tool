"""Dividends and early exercise on the banked options book.  [O21]

Pre-registered in `PREREG_o21_dividends.md`, committed before this file existed.

THE DEFECT IS NOT A MISSING MODEL. `blackscholes.bs_price`, `implied_vol` and `greeks` all
already take a continuous dividend yield `q` and handle it correctly. **Every caller uses the
default `q = 0.0`** -- `options_backtest.pick_contract` and `optvrp_run` are the only two, and
neither passes it.

THE SCOPING FACT THAT DECIDES WHAT CAN MOVE. The banked book's P&L comes from QUOTED bid/ask in
the frozen chains, never from a model price, so a pricer that ignores dividends cannot move the
recorded P&L *directly*. It reaches the book through three doors, measured separately here:

    D1  early exercise    -- the sim always SELLS at the bid; a deep-ITM American call near
                             ex-div can be worth more exercised. Moves P&L. Model-free.
    D2  contract selection -- `pick_contract` picks nearest |delta| to 0.35 at q = 0, so it can
                             land on a different strike. Moves P&L.
    D3  derived fields     -- banked `iv` and `target_delta` feed O13's arms and `delta85`.
                             Does not move P&L.

Reading "the pricer ignores dividends" as "the headline expectancy is wrong" is the misreading
this module exists to prevent: D1 and D2 are the only routes by which it could become true.

EARLY EXERCISE IS MEASURED MODEL-FREE, DELIBERATELY. The textbook condition compares the dividend
to remaining time value, which needs a model -- and would make the answer a function of the very
pricer under test. A holder who could sell at `bid` but exercise for `S - K` left money on the
table exactly when `bid < S - K`. That needs no vol, no rate and no dividend estimate.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Optional

TRAILING_DAYS = 365


# ------------------------------------------------------------------------------------------- #
# Dividend table
# ------------------------------------------------------------------------------------------- #
def load_dividends(data_root: str) -> dict:
    """`{ticker: [(ex_date, amount), ...]}` from the prepared ACTIONS cache, sorted by date.

    Returns `{}` rather than raising when the cache is absent: `data/` is gitignored, so CI has
    none, and the tests pin the algebra with hand-built tables. A module that raised at import
    or on a missing file would fail the whole auto-land gate on a fresh checkout.
    """
    path = os.path.join(data_root, "bulk", "prepared", "actions.pkl")
    if not os.path.isfile(path):
        return {}
    import pandas as pd

    blob = pd.read_pickle(path)
    out = {}
    for tkr, rec in (blob or {}).items():
        divs = (rec or {}).get("dividends") or []
        rows = []
        for d, amt in divs:
            try:
                a = float(amt)
            except (TypeError, ValueError):
                continue
            if a > 0:
                rows.append((str(d)[:10], a))
        if rows:
            out[str(tkr)] = sorted(rows)
    return out


def _d(x) -> Optional[dt.date]:
    s = str(x or "")[:10]
    try:
        return dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, IndexError):
        return None


def dividends_between(divs: dict, ticker: str, start, end) -> list:
    """Dividends with ex-date in the half-open interval `(start, end]`.

    Half-open on the left because a dividend whose ex-date IS the entry date has already been
    priced out of the underlying by the time the position exists.
    """
    a, b = _d(start), _d(end)
    if a is None or b is None:
        return []
    out = []
    for ds, amt in (divs.get(str(ticker or "")) or []):
        x = _d(ds)
        if x is not None and a < x <= b:
            out.append((ds, amt))
    return out


def q_trailing(divs: dict, ticker: str, entry, spot: float,
               days: int = TRAILING_DAYS) -> Optional[float]:
    """PRIMARY yield: trailing-12-month dividends over spot. Strictly point-in-time.

    Uses only ex-dates STRICTLY BEFORE the entry date, so nothing resting on it can be accused
    of look-ahead. That is why it, and not the scheduled variant, is allowed to carry a verdict.
    """
    e = _d(entry)
    if e is None or not spot or float(spot) <= 0:
        return None
    lo = e - dt.timedelta(days=days)
    tot = 0.0
    for ds, amt in (divs.get(str(ticker or "")) or []):
        x = _d(ds)
        if x is not None and lo <= x < e:
            tot += amt
    return tot / float(spot)


def q_scheduled(divs: dict, ticker: str, entry, expiry, spot: float,
                t_years: Optional[float] = None) -> Optional[float]:
    """SECONDARY yield: dividends actually scheduled inside the contract's life, annualised.

    Realistic rather than clairvoyant -- an ex-date and amount are announced weeks ahead -- but
    it reads the future of the contract's life, so the register forbids it from carrying a
    verdict. It exists to bound how much the primary understates.
    """
    e, x = _d(entry), _d(expiry)
    if e is None or x is None or not spot or float(spot) <= 0:
        return None
    T = t_years if t_years is not None else max((x - e).days, 1) / 365.0
    if T <= 0:
        return None
    tot = sum(a for _, a in dividends_between(divs, ticker, entry, expiry))
    return (tot / float(spot)) / T


# ------------------------------------------------------------------------------------------- #
# D1 — early exercise, model-free
# ------------------------------------------------------------------------------------------- #
def spot_from_parity(call_mid: float, put_mid: float, strike: float,
                     rate: float, t_years: float) -> Optional[float]:
    """Recover the underlying from put-call parity: `S = C - P + K*exp(-rT)`.

    WHY THIS AND NOT A BOUND. The first version of this study estimated spot as
    `max(call_bid + strike)` over the chain. That is wrong in the direction that INFLATES the
    finding: parity gives `C >= S - K`, i.e. `S <= C + K`, so every `bid + K` is an UPPER bound
    on spot and the MAXIMUM of them is the loosest one available. Using it made intrinsic too
    large and the early-exercise gain too large. Parity recovers spot as an equality instead of
    a bound, and `tests/test_dividends.py` pins the direction of that old error.

    European parity is used on American options deliberately: the error it carries is the early
    exercise premium itself, which is second-order for the PUT leg here and is the conservative
    direction for a call-side measurement.
    """
    try:
        c, p, k = float(call_mid), float(put_mid), float(strike)
    except (TypeError, ValueError):
        return None
    # `p == 0` IS ALLOWED AND THE REASON MATTERS. A deep-ITM call's matching put is deep OTM and
    # legitimately quotes at or near zero -- which is exactly the situation early exercise lives
    # in. An earlier version rejected `p <= 0` and so discarded every case this study exists to
    # find, scoring zero rows on a smoke test. The caller must still require the put ROW to
    # exist with a real quote; a put that is merely absent would leave `S = C + K*exp(-rT)`,
    # which overstates spot in the same direction as the bound this function replaced.
    if c <= 0 or p < 0 or k <= 0 or t_years is None or t_years < 0:
        return None
    import math
    return c - p + k * math.exp(-float(rate) * float(t_years))


def intrinsic(spot: float, strike: float, right: str) -> float:
    is_put = str(right or "C")[0].upper() == "P"
    return max(0.0, (float(strike) - float(spot)) if is_put else (float(spot) - float(strike)))


def exercise_gain(bid: float, spot: float, strike: float, right: str) -> float:
    """How much a holder left on the table by SELLING at `bid` instead of exercising.

    Zero when the bid is at or above intrinsic, which is the normal case. Never negative: a
    holder always has the choice, so this is a floor on value, and reporting a negative here
    would mean claiming the backtest did BETTER than an optimising holder, which is impossible.
    """
    iv = intrinsic(spot, strike, right)
    b = float(bid or 0.0)
    return max(0.0, iv - b)


def exit_below_intrinsic(rows: list, spot_of, key="exit_premium") -> dict:
    """Count and size the exits that were booked below intrinsic value.

    `spot_of(row) -> underlying price at exit`, supplied by the caller because this module does
    not read price data.
    """
    n = 0
    hits = 0
    gain_sum = 0.0
    per_trade = []
    for r in rows:
        px = r.get(key)
        if px is None:
            continue
        s = spot_of(r)
        if s is None:
            continue
        n += 1
        g = exercise_gain(px, s, r.get("strike"), r.get("opt_right"))
        entry = float(r.get("entry_premium") or 0.0)
        rel = (g / entry) if entry > 0 else 0.0
        per_trade.append(rel)
        if g > 0:
            hits += 1
            gain_sum += g
    return {"n_scored": n, "n_below_intrinsic": hits,
            "share_below_intrinsic": (hits / n) if n else None,
            "total_gain_dollars_per_contract": gain_sum,
            "mean_expectancy_gain_pct": (sum(per_trade) / len(per_trade)) if per_trade else None}


def held_across_ex_div(rows: list, divs: dict) -> dict:
    """Descriptive: how many trades hold a call across an ex-dividend date."""
    n = 0
    for r in rows:
        if str(r.get("opt_right") or "C")[0].upper() != "C":
            continue
        d = dividends_between(divs, r.get("ticker"), r.get("alert_ts"), r.get("expiry"))
        if d:
            n += 1
    return {"n_calls_spanning_ex_div": n, "n_rows": len(rows)}
