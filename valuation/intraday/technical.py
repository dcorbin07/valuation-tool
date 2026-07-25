"""
Technical indicators + a bullish-setup score.

Implements the widely-used, reputable indicators (RSI, MACD, moving-average
alignment/crosses, Bollinger %b, rate-of-change, volume surge, 52-week-high
proximity) and blends them into a 0-100 "buy-setup strength" with named pattern
labels. Pure functions over a bar series so they're fully testable offline.

Honest note: these are standard, popular signals — useful for spotting setups and
timing entries, NOT a proven edge. Validate with the backtest before trusting them.
"""
from __future__ import annotations

import numpy as np


def ema(x, n):
    x = np.asarray(x, float)
    k = 2.0 / (n + 1)
    e = np.empty_like(x)
    e[0] = x[0]
    for i in range(1, len(x)):
        e[i] = x[i] * k + e[i - 1] * (1 - k)
    return e


def sma_series(x, n):
    x = np.asarray(x, float)
    if len(x) < n:
        return np.full(len(x), np.nan)
    c = np.convolve(x, np.ones(n) / n, "valid")
    return np.concatenate([np.full(n - 1, np.nan), c])


def rsi(closes, n=14):
    c = np.asarray(closes, float)
    if len(c) < n + 1:
        return None
    d = np.diff(c)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    ru, rd = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(d)):
        ru = (ru * (n - 1) + up[i]) / n
        rd = (rd * (n - 1) + dn[i]) / n
    if rd == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ru / rd)


def macd(closes, fast=12, slow=26, sig=9):
    c = np.asarray(closes, float)
    if len(c) < slow + sig:
        return None
    line = ema(c, fast) - ema(c, slow)
    signal = ema(line, sig)
    hist = line - signal
    return {"line": float(line[-1]), "signal": float(signal[-1]),
            "hist": float(hist[-1]), "hist_prev": float(hist[-2])}


def bollinger_pctb(closes, n=20, k=2):
    c = np.asarray(closes, float)[-n:]
    if len(c) < n:
        return None
    m, s = c.mean(), c.std(ddof=0)
    if s == 0:
        return 0.5
    return float((c[-1] - (m - k * s)) / (2 * k * s))


def roc(closes, n=10):
    c = np.asarray(closes, float)
    return float(c[-1] / c[-1 - n] - 1) if len(c) > n else None


def technical_signals(bars: dict) -> dict:
    """bars: {'close':[...], 'high':[...], 'low':[...], 'volume':[...]} oldest→newest.
    Returns {score 0-100, labels[], detail{}}."""
    close = np.asarray(bars.get("close", []), float)
    vol = np.asarray(bars.get("volume", []), float) if bars.get("volume") else None
    if len(close) < 50:
        return {"score": None, "labels": [], "detail": {}, "note": "insufficient history"}

    price = float(close[-1])
    s50 = sma_series(close, 50)
    s200 = sma_series(close, 200) if len(close) >= 200 else np.full(len(close), np.nan)
    r = rsi(close, 14)
    mac = macd(close)
    pctb = bollinger_pctb(close, 20, 2)
    roc20 = roc(close, 20)
    hi_252 = float(np.max(close[-252:])) if len(close) >= 60 else float(np.max(close))
    dist_high = price / hi_252 - 1.0
    vol_ratio = None
    if vol is not None and len(vol) >= 20 and vol[-20:].mean() > 0:
        vol_ratio = float(vol[-1] / vol[-20:].mean())

    labels, score = [], 50.0

    # Trend alignment
    up_trend = not np.isnan(s50[-1]) and not np.isnan(s200[-1]) and price > s50[-1] > s200[-1]
    if up_trend:
        score += 12
        labels.append("Uptrend (>50 & >200 DMA)")
    elif not np.isnan(s50[-1]) and price > s50[-1]:
        score += 5
    # Golden / death cross (recent)
    if not np.isnan(s50[-2]) and not np.isnan(s200[-2]):
        if s50[-1] > s200[-1] and s50[-2] <= s200[-2]:
            score += 9; labels.append("Golden cross")
        elif s50[-1] < s200[-1] and s50[-2] >= s200[-2]:
            score -= 9; labels.append("Death cross")

    # MACD
    if mac:
        if mac["hist"] > 0:
            score += 6
            if mac["hist"] > mac["hist_prev"]:
                score += 4
            if mac["hist_prev"] <= 0 < mac["hist"]:
                score += 6; labels.append("MACD bullish cross")
        else:
            score -= 4
            if mac["hist_prev"] >= 0 > mac["hist"]:
                labels.append("MACD bearish cross")

    # RSI
    if r is not None:
        if r < 30:
            score += 8; labels.append(f"Oversold (RSI {r:.0f})")
        elif 45 <= r <= 65:
            score += 6
        elif r > 75:
            score -= 10; labels.append(f"Overbought (RSI {r:.0f})")

    # Breakout / 52w high proximity
    if dist_high > -0.02:
        score += 8; labels.append("Near 52-wk high")
    if pctb is not None and pctb > 1.0:
        score += 5; labels.append("Breakout (upper band)")
    elif pctb is not None and pctb < 0.0:
        score += 3

    # Volume confirmation
    if vol_ratio is not None and vol_ratio > 1.5:
        score += 6; labels.append(f"Volume surge {vol_ratio:.1f}x")

    score = float(max(0, min(100, score)))
    detail = {"price": price, "rsi": r, "macd_hist": mac["hist"] if mac else None,
              "pct_b": pctb, "roc20": roc20, "dist_52w_high": dist_high,
              "vol_ratio": vol_ratio, "above_50dma": bool(not np.isnan(s50[-1]) and price > s50[-1]),
              "above_200dma": bool(not np.isnan(s200[-1]) and price > s200[-1])}
    return {"score": score, "labels": labels, "detail": detail}
