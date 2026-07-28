"""
Free price/volume data (Stooq primary, yfinance fallback) — adapted from the
screener project. Used for the momentum factor (12-minus-1-month return), the
liquidity gate (average dollar volume), and backtest return series.
"""
from __future__ import annotations

import io

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}&i=d"
_TIMEOUT = 15


def _stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower().replace('.', '-')}.us"


def get_history_df(ticker: str, days: int = 400):
    """Daily OHLCV DataFrame (oldest→newest) or None."""
    try:
        import time
        import pandas as pd
        import requests
        last = None
        for attempt in range(3):                       # brief retry/backoff on transient blips
            try:
                r = requests.get(STOOQ_URL.format(sym=_stooq_symbol(ticker)), timeout=_TIMEOUT)
                r.raise_for_status()
                df = pd.read_csv(io.StringIO(r.text))
                if df.empty or "Close" not in df.columns:
                    raise ValueError("empty")
                return df.tail(days).reset_index(drop=True)
            except Exception as e:
                last = e
                if attempt < 2:
                    time.sleep(0.4 * (attempt + 1))
        raise last
    except Exception:
        return _yf_history(ticker, days)


def _yf_history(ticker: str, days: int):
    try:
        import pandas as pd
        import yfinance as yf
        period = ("10y" if days > 1825 else "5y" if days > 730 else "2y" if days > 365
                  else "1y" if days > 180 else "6mo" if days > 60 else "3mo")
        h = yf.Ticker(ticker).history(period=period)
        if h.empty:
            return None
        h = h.tail(days)
        return pd.DataFrame({"Date": h.index.astype(str), "Open": h["Open"].values,
                             "High": h["High"].values, "Low": h["Low"].values,
                             "Close": h["Close"].values, "Volume": h["Volume"].values})
    except Exception:
        return None


def get_quote(ticker: str) -> dict | None:
    """Price + volume-derived signals: avg dollar volume, 12-1 and 6-1 momentum,
    52-week-high proximity, and realized volatility (annualized). None if no data."""
    df = get_history_df(ticker, days=400)
    if df is None or len(df) < 30:
        return None
    close = [float(x) for x in df["Close"].tolist()]
    vol = [float(x) for x in df["Volume"].tolist()]
    price = close[-1]
    n = len(close)
    # average dollar volume over the last ~60 sessions
    tail = min(60, n)
    adv = sum(close[-i] * vol[-i] for i in range(1, tail + 1)) / tail
    # 12-1 month momentum: return from ~252d ago to ~21d ago
    ret_12_1 = None
    if n >= 252:
        p_then, p_recent = close[-252], close[-21]
        if p_then > 0:
            ret_12_1 = p_recent / p_then - 1.0
    elif n >= 150:
        p_then, p_recent = close[0], close[-21]
        if p_then > 0:
            ret_12_1 = p_recent / p_then - 1.0
    # 6-1 month momentum: return from ~126d ago to ~21d ago
    ret_6_1 = None
    if n >= 126:
        p6 = close[-126]
        if p6 > 0:
            ret_6_1 = close[-21] / p6 - 1.0
    # 52-week-high proximity: price / trailing max (0..1, higher = nearer the high)
    win = close[-min(252, n):]
    hi = max(win) if win else None
    high_prox = (price / hi) if (hi and hi > 0) else None
    # realized volatility: annualized stdev of daily returns over ~120 sessions
    vlook = close[-min(120, n):]
    rets = [vlook[i] / vlook[i - 1] - 1.0 for i in range(1, len(vlook)) if vlook[i - 1] > 0]
    realized_vol = None
    if len(rets) >= 20:
        mu = sum(rets) / len(rets)
        var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)
        realized_vol = (var ** 0.5) * (252 ** 0.5)
    return {"price": price, "avg_dollar_volume": adv, "ret_12_1": ret_12_1,
            "ret_6_1": ret_6_1, "high_prox": high_prox, "realized_vol": realized_vol}


def close_series(ticker: str, days: int = 1500):
    """(dates, closes) as lists for the backtest, or (None, None)."""
    df = get_history_df(ticker, days=days)
    if df is None or df.empty:
        return None, None
    return [str(d) for d in df["Date"].tolist()], [float(c) for c in df["Close"].tolist()]
