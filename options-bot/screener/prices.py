"""
prices.py — free price/volume data (Stooq primary, yfinance fallback).

Stooq serves daily OHLCV as CSV with no key. We derive the momentum signal,
average dollar volume (liquidity gate), and price/volume z-scores (abnormal-move
detection) from the daily history. Current price = latest close (EOD), which is
fine for a once-daily screener.
"""

import io
import numpy as np
import pandas as pd
import requests

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}&i=d"
_TIMEOUT = 15


def _stooq_symbol(ticker):
    # Stooq uses lowercase with a market suffix for US names
    return f"{ticker.lower()}.us"


def get_history_df(ticker, days=400):
    """Return a daily OHLCV DataFrame (oldest→newest) or None."""
    try:
        url = STOOQ_URL.format(sym=_stooq_symbol(ticker))
        r = requests.get(url, timeout=_TIMEOUT)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Close" not in df.columns:
            raise ValueError("empty/no Close")
        df = df.tail(days).reset_index(drop=True)
        return df
    except Exception:
        return _yf_history(ticker, days)


def _yf_history(ticker, days):
    try:
        import yfinance as yf
        # yfinance accepts only enumerated period strings (not "400d"); pick the
        # smallest standard period that covers the requested day count, then trim.
        period = ("10y" if days > 1825 else "5y" if days > 730 else
                  "2y" if days > 365 else "1y" if days > 180 else "6mo" if days > 60 else "3mo")
        h = yf.Ticker(ticker).history(period=period)
        if h.empty:
            return None
        h = h.tail(days)
        return pd.DataFrame({
            "Date": h.index.astype(str), "Open": h["Open"].values,
            "High": h["High"].values, "Low": h["Low"].values,
            "Close": h["Close"].values, "Volume": h["Volume"].values,
        })
    except Exception:
        return None


def get_quote(ticker):
    """
    Return the price-derived fields scoring/decisions need:
      price, avg_dollar_volume, ret_12_1, price_zscore, volume_zscore.
    Returns None if data is unavailable.
    """
    df = get_history_df(ticker, days=400)
    if df is None or len(df) < 30:
        return None
    close = df["Close"].astype(float).values
    vol = df["Volume"].astype(float).values
    price = float(close[-1])

    # liquidity: average daily dollar volume over the last ~30 sessions
    n = min(30, len(close))
    avg_dollar_volume = float(np.mean(close[-n:] * vol[-n:]))

    # 12-1 momentum: ~252 sessions ago to ~21 sessions ago
    ret_12_1 = None
    if len(close) >= 252:
        ret_12_1 = float(close[-21] / close[-252] - 1)
    elif len(close) >= 60:
        ret_12_1 = float(close[-21] / close[0] - 1)  # best-effort with short history

    # abnormal-move z-scores: latest daily return / volume vs trailing distribution
    rets = np.diff(close) / close[:-1]
    price_zscore = None
    if len(rets) >= 20 and np.std(rets[-60:]) > 0:
        price_zscore = float((rets[-1] - np.mean(rets[-60:])) / np.std(rets[-60:]))
    volume_zscore = None
    if len(vol) >= 20 and np.std(vol[-60:]) > 0:
        volume_zscore = float((vol[-1] - np.mean(vol[-60:])) / np.std(vol[-60:]))

    return {
        "price": price, "avg_dollar_volume": avg_dollar_volume,
        "ret_12_1": ret_12_1, "price_zscore": price_zscore,
        "volume_zscore": volume_zscore,
    }


def benchmark_return(symbol, days):
    """Total return of a benchmark ETF (IWM, IJR) over the last `days` sessions."""
    df = get_history_df(symbol, days=days + 10)
    if df is None or len(df) < 2:
        return None
    close = df["Close"].astype(float).values
    k = min(days, len(close) - 1)
    return float(close[-1] / close[-1 - k] - 1)
