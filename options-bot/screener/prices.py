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


# ---------------------------------------------------------------------------
#  Realized forward returns for the track record (C4)
# ---------------------------------------------------------------------------

# Horizons are expressed in TRADING SESSIONS, matching benchmark_return above,
# which indexes into the close array rather than into the calendar.
NOT_CLOSED = "not_closed"
DELISTED = "delisted"
NO_DATA = "no_data"


def forward_return_from(symbol, since_date, sessions, grace_sessions=10, df=None):
    """
    Realized return of `symbol` from the close on/just before `since_date` to
    `sessions` trading days later.

    Returns (value, status):
      (float, "ok")            the horizon closed and we have both bars
      (None,  NOT_CLOSED)      not enough sessions have elapsed yet — come back
      (float, DELISTED)        the series stops inside the horizon and has not
                               resumed within `grace_sessions`. We freeze the
                               LAST OBSERVED return rather than dropping the
                               row. Dropping names that stopped trading is
                               exactly how a track record lies.
      (None,  NO_DATA)         no usable price history at all

    `df` lets a caller fetch one history and reuse it across every horizon for
    the same name instead of re-downloading three times.
    """
    import datetime as _dt

    if df is None:
        df = get_history_df(symbol, days=sessions + 400)
    if df is None or len(df) < 2 or "Close" not in df:
        return None, NO_DATA

    d = df.copy()
    d["_d"] = pd.to_datetime(d["Date"], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    d = d.dropna(subset=["_d"]).sort_values("_d").reset_index(drop=True)
    if d.empty:
        return None, NO_DATA

    if isinstance(since_date, str):
        since_date = _dt.date.fromisoformat(since_date)
    cutoff = pd.Timestamp(since_date).normalize()

    at_or_before = d.index[d["_d"] <= cutoff]
    if len(at_or_before) == 0:
        return None, NO_DATA
    i = int(at_or_before[-1])
    closes = d["Close"].astype(float).values
    entry = closes[i]
    if not entry or entry <= 0:
        return None, NO_DATA

    j = i + sessions
    if j < len(closes):
        return float(closes[j] / entry - 1.0), "ok"

    # The horizon runs past the end of the series. Two very different reasons.
    last_bar = d["_d"].iloc[-1].date()
    # How many sessions SHOULD have printed by now? Approximate with the
    # calendar: 252 sessions/year. We only need to tell "the market has moved
    # on without this name" from "the market has not got there yet".
    today = _dt.date.today()
    sessions_since_last_bar = int((today - last_bar).days * 252 / 365)
    if sessions_since_last_bar > grace_sessions:
        # The name stopped printing and has not come back. Freeze what we saw.
        return float(closes[-1] / entry - 1.0), DELISTED
    return None, NOT_CLOSED
