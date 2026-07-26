"""
Bearish setup score — the short-side mirror of technical_signals.

Same reputable indicators, read the other way: price below the 50/200-day
averages, a death cross, a negative/rolling-over MACD, an overbought RSI (reversal
risk), and breakdowns to new lows / below the lower Bollinger band. High score =
strong bearish setup. Reuses the indicator helpers so nothing is recomputed twice.
"""
from __future__ import annotations

import numpy as np

from .technical import sma_series, rsi, macd, bollinger_pctb


def bearish_technical(bars: dict) -> dict:
    close = np.asarray(bars.get("close", []), float)
    if len(close) < 50:
        return {"score": None, "labels": [], "detail": {}}
    price = float(close[-1])
    s50 = sma_series(close, 50)
    s200 = sma_series(close, 200) if len(close) >= 200 else np.full(len(close), np.nan)
    r = rsi(close, 14)
    mac = macd(close)
    pctb = bollinger_pctb(close, 20, 2)
    lo_252 = float(np.min(close[-252:])) if len(close) >= 60 else float(np.min(close))
    dist_low = price / lo_252 - 1.0

    labels, score = [], 50.0

    # Trend (down)
    if not np.isnan(s50[-1]) and not np.isnan(s200[-1]) and price < s50[-1] < s200[-1]:
        score += 12
        labels.append("Downtrend (<50 & <200 DMA)")
    elif not np.isnan(s50[-1]) and price < s50[-1]:
        score += 5
    # Death cross (recent)
    if not np.isnan(s50[-2]) and not np.isnan(s200[-2]):
        if s50[-1] < s200[-1] and s50[-2] >= s200[-2]:
            score += 9
            labels.append("Death cross")
    # MACD rolling over
    if mac:
        if mac["hist"] < 0:
            score += 6
            if mac["hist"] < mac["hist_prev"]:
                score += 4
            if mac["hist_prev"] >= 0 > mac["hist"]:
                score += 6
                labels.append("MACD bearish cross")
        else:
            score -= 4
    # RSI: overbought = reversal risk (bearish); very oversold = bounce risk (less bearish)
    if r is not None:
        if r > 70:
            score += 8
            labels.append(f"Overbought (RSI {r:.0f})")
        elif r < 25:
            score -= 6
    # Breakdown
    if dist_low < 0.03:
        score += 8
        labels.append("Near 52-wk low")
    if pctb is not None and pctb < 0.0:
        score += 5
        labels.append("Breakdown (lower band)")

    score = float(max(0, min(100, score)))
    detail = {"price": price, "rsi": r, "macd_hist": mac["hist"] if mac else None,
              "pct_b": pctb, "dist_52w_low": dist_low,
              "below_200dma": bool(not np.isnan(s200[-1]) and price < s200[-1])}
    return {"score": score, "labels": labels, "detail": detail}
