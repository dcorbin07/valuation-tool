"""
Black-Scholes pricing + greeks for European puts.

Used by the options backtest to (a) find the strike at a target delta and
(b) reprice spreads each day as spot moves, vol changes, and time decays.

These are EUROPEAN-style formulas applied to AMERICAN-style ETF options — a
deliberate, documented approximation. For OTM puts held to a profit/stop/time
exit (not to expiration deep ITM), the early-exercise premium is small, so this
is a reasonable proxy. We note it honestly rather than pretend it's exact.
"""
from __future__ import annotations

import math


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via erf (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1_d2(spot, strike, t, r, sigma, q=0.0):
    """d1, d2 for Black-Scholes with continuous dividend yield q."""
    if t <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        return None, None
    vol_sqrt_t = sigma * math.sqrt(t)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * t) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return d1, d2


def put_price(spot, strike, t, r, sigma, q=0.0) -> float:
    """European put price. t in years. Returns price per share."""
    if t <= 0:
        return max(0.0, strike - spot)  # intrinsic at expiry
    d1, d2 = _d1_d2(spot, strike, t, r, sigma, q)
    if d1 is None:
        return max(0.0, strike - spot)
    return (strike * math.exp(-r * t) * _norm_cdf(-d2)
            - spot * math.exp(-q * t) * _norm_cdf(-d1))


def put_delta(spot, strike, t, r, sigma, q=0.0) -> float:
    """
    Put delta, returned as a POSITIVE magnitude in [0, 1] (the convention the
    strategy uses — "20-delta put" means |delta| ≈ 0.20). True put delta is
    negative; we return its absolute value for strike selection.
    """
    if t <= 0:
        return 1.0 if spot < strike else 0.0
    d1, _ = _d1_d2(spot, strike, t, r, sigma, q)
    if d1 is None:
        return 0.0
    # put delta = -e^{-qt} N(-d1); magnitude = e^{-qt} N(-d1)
    return math.exp(-q * t) * _norm_cdf(-d1)


def find_strike_for_delta(spot, target_delta, t, r, sigma, q=0.0,
                          strike_step=1.0) -> float:
    """
    Find the put strike whose |delta| ≈ target_delta, by scanning strikes below
    spot (OTM puts). Returns the strike (rounded to strike_step).

    A 20-delta put is OTM (below spot). We walk strikes down from spot until the
    delta magnitude drops to the target, then snap to the strike grid.
    """
    if spot <= 0 or t <= 0 or sigma <= 0:
        return round(spot * 0.9 / strike_step) * strike_step
    # Start near the money and step down; delta magnitude falls as strike falls.
    strike = round(spot / strike_step) * strike_step
    best_strike = strike
    best_diff = float("inf")
    # scan a wide band below spot
    n_steps = int((spot * 0.5) / strike_step) + 1
    for i in range(n_steps):
        k = strike - i * strike_step
        if k <= 0:
            break
        d = put_delta(spot, k, t, r, sigma, q)
        diff = abs(d - target_delta)
        if diff < best_diff:
            best_diff = diff
            best_strike = k
        # deltas are monotonic in strike; once we're well past target, stop
        if d < target_delta - 0.05:
            break
    return best_strike
