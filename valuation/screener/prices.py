"""
Free price/volume data (Stooq primary, yfinance fallback) — adapted from the
screener project. Used for the momentum factor (12-minus-1-month return), the
liquidity gate (average dollar volume), and backtest return series.

THE FALLBACK STAYS AND IT IS NO LONGER SILENT
----------------------------------------------
`get_history_df` used to wrap the whole primary path in a bare `except Exception` and fall
through to yfinance, so a reader of any downstream figure could not tell which vendor produced
it. Resilience is right — a screener that dies because one free vendor is having a bad afternoon
is worse than one that switches — but an UNLABELLED fallback silently swaps the meaning of the
number, which is the `COVERAGE-RULE` family: the run completes, nothing raises, and the figure
is a different quantity than the one its name implies.

**AND IT IS NOT HYPOTHETICAL. Measured 2026-08-20: Stooq served 0 of 10 probed tickers** —
SPY, AAPL, KO, NVDA, JNJ, MSFT, XOM, T, IBM, PG — so **every figure on this path is a yfinance
figure today**, and nothing recorded that. Two distinct refusals, depending on the header sent:
the default `requests` user-agent gets **HTTP 404** ("the page you requested does not exist"),
and a browser user-agent gets **HTTP 200 carrying a JavaScript bot-verification page**, never
CSV. Neither is a transient blip and the retry loop cannot help. **No attempt is made here to
defeat that challenge** — evading a vendor's access control is not a fix, and the honest
response to a primary that will not serve is to say so on every figure it did not serve.

THE ADJUSTMENT CONVENTIONS ARE DIFFERENT, WHICH IS WHY THE LABEL MATTERS
------------------------------------------------------------------------
`yfinance`'s `PriceHistory.history` defaults to **`auto_adjust=True`** (verified from its
signature on yfinance 1.3.0), so the fallback's `Close` is **split- AND dividend-adjusted**.
That is a *different quantity* from an as-traded close, and `U1-SPLIT` is this project's
standing measurement of what that confusion costs: NVDA in 2012 reads 0.27 adjusted against a
raw 11.97, a 43x ratio, and the mismatch **fails silently** because the number still looks like
a price.

`auto_adjust=True` is now passed **EXPLICITLY** rather than inherited. Relying on a vendor
library's default is how a convention changes under you between releases — and yfinance has
moved this particular default before.

**STOOQ'S CONVENTION IS RECORDED AS `unverified` AND MUST NOT BE ASSUMED.** It cannot be
measured from here, because Stooq will not serve this client at all; guessing it would be
inventing the one fact this module exists to stop people inventing. `VENDOR_ADJUSTMENT` says
`unverified` until somebody can fetch a Stooq bar across a known split or dividend and compare.

WHAT TRAVELS, AND WHY IT TRAVELS ON THE FRAME
----------------------------------------------
The vendor label is written to **`df.attrs["valquo_src"]`** rather than into a module-global
alone, because `index_mark.contract_row` takes an injectable `fetch` and a global would be
blind to it — the label has to ride the object that crossed the boundary. A module-level census
is kept as well, for the direct path and for health blocks.

`pandas` drops `.attrs` across many operations, so a consumer that needs the label must read it
from the frame this function returned rather than from a derived one. `source_of()` is the
accessor and it returns `None` for "unlabelled", never a vendor guess.

THE EXCEPT IS NARROW NOW
-------------------------
Only what the primary path actually throws — a `requests` transport/HTTP failure, a CSV that
will not parse, or this module's own "empty" signal — is treated as a vendor outage. An
`ImportError` used to route straight into the fallback, so a broken install looked exactly like
a bad afternoon at Stooq; it now propagates, along with `MemoryError`, `KeyboardInterrupt` and
`SystemExit`. A bug in this module is a bug, not a vendor problem.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}&i=d"
_TIMEOUT = 15

_LOG = logging.getLogger(__name__)

#: the key the vendor label is written under, on `DataFrame.attrs`
SRC_ATTR = "valquo_src"
#: and the companion key recording how that vendor treats corporate actions
ADJ_ATTR = "valquo_adjusted"

SRC_STOOQ = "stooq"
SRC_YFINANCE = "yfinance"

#: What each vendor's `Close` MEANS. `unverified` is a real state and is never rounded to a
#: guess -- see the module docstring.
VENDOR_ADJUSTMENT = {
    SRC_STOOQ: "unverified",
    SRC_YFINANCE: "auto_adjusted",
}

#: Counts by vendor plus the last vendor seen per ticker. The direct path's record; consumers
#: holding an injected `fetch` should read `source_of(df)` instead.
_CENSUS: dict = {"by_vendor": {}, "last_by_ticker": {}, "primary_failures": 0,
                 "unlabelled": 0}


def _stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower().replace('.', '-')}.us"


def _primary_errors():
    """Exactly what the primary path can legitimately raise. Built lazily so this module still
    imports on a machine without requests/pandas -- and so that a MISSING one of those raises
    rather than quietly becoming a vendor fallback."""
    import pandas as pd
    import requests
    return (requests.RequestException,        # transport, timeout, and raise_for_status
            pd.errors.ParserError,            # a body that is not CSV (Stooq's HTML refusals)
            pd.errors.EmptyDataError,
            UnicodeDecodeError,
            ValueError)                       # this module's own "empty" signal


def _label(df, ticker: str, src: str):
    """Stamp the frame and record the census. The ONE place a vendor label is written."""
    if df is None:
        return None
    try:
        df.attrs[SRC_ATTR] = src
        df.attrs[ADJ_ATTR] = VENDOR_ADJUSTMENT.get(src, "unverified")
    except Exception:                                                   # noqa: BLE001
        # `.attrs` is best-effort on exotic frame types; the census below is not, so a frame
        # that cannot be stamped is still counted rather than silently unrecorded.
        _CENSUS["unlabelled"] = _CENSUS.get("unlabelled", 0) + 1
    _CENSUS["by_vendor"][src] = _CENSUS["by_vendor"].get(src, 0) + 1
    _CENSUS["last_by_ticker"][str(ticker)] = src
    return df


def source_of(df) -> Optional[str]:
    """Which vendor served this frame, or None if it carries no label.

    **None means UNLABELLED, not a vendor.** A caller that needs to know must treat None as
    "cannot tell" rather than defaulting to the primary -- defaulting is the defect this module
    was changed to remove.
    """
    if df is None:
        return None
    try:
        return df.attrs.get(SRC_ATTR)
    except Exception:                                                   # noqa: BLE001
        return None


def adjustment_of(df) -> Optional[str]:
    """How the serving vendor treats corporate actions: `auto_adjusted`, `unverified`, or None."""
    if df is None:
        return None
    try:
        return df.attrs.get(ADJ_ATTR)
    except Exception:                                                   # noqa: BLE001
        return None


def source_census() -> dict:
    """A copy of the per-vendor record, for a health block or a handoff."""
    import copy
    return copy.deepcopy(_CENSUS)


def reset_census() -> None:
    """Tests and long-lived processes reset between runs; nothing else should call this."""
    _CENSUS["by_vendor"] = {}
    _CENSUS["last_by_ticker"] = {}
    _CENSUS["primary_failures"] = 0
    _CENSUS["unlabelled"] = 0


def get_history_df(ticker: str, days: int = 400):
    """Daily OHLCV DataFrame (oldest→newest) or None, LABELLED with the vendor that served it.

    The label is on `df.attrs["valquo_src"]`; read it with `source_of(df)`. A fallback is
    logged at WARNING with the primary's actual exception, so a run that switched vendors says
    so in its output instead of only in its numbers.
    """
    import time

    import pandas as pd
    import requests                                                     # noqa: F401

    last = None
    for attempt in range(3):                       # brief retry/backoff on transient blips
        try:
            r = requests.get(STOOQ_URL.format(sym=_stooq_symbol(ticker)), timeout=_TIMEOUT)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            if df.empty or "Close" not in df.columns:
                raise ValueError("stooq returned no usable Close column")
            return _label(df.tail(days).reset_index(drop=True), ticker, SRC_STOOQ)
        except _primary_errors() as e:
            last = e
            if attempt < 2:
                time.sleep(0.4 * (attempt + 1))

    _CENSUS["primary_failures"] = _CENSUS.get("primary_failures", 0) + 1
    _LOG.warning(
        "prices: STOOQ FAILED for %s after 3 attempts (%s: %s) — falling back to yfinance, "
        "whose Close is AUTO-ADJUSTED and is therefore a different quantity from an as-traded "
        "close. The returned frame is labelled %r=%r.",
        ticker, type(last).__name__, last, SRC_ATTR, SRC_YFINANCE)
    return _yf_history(ticker, days)


def _yf_history(ticker: str, days: int):
    import pandas as pd
    import yfinance as yf

    # "max" ABOVE TEN YEARS, and it is additive: the largest `days` any shipped caller passes
    # is 2700, which still maps to "10y", so every existing consumer is bit-identical. It
    # exists because a benchmark measured since an ETF's own inception needs more than ten
    # years -- SPMO listed 2015-10, and a 10y cap silently starts the comparison a year late
    # while still returning a full-looking frame, which is the worst kind of wrong.
    period = ("max" if days > 3650 else "10y" if days > 1825 else "5y" if days > 730
              else "2y" if days > 365 else "1y" if days > 180 else "6mo" if days > 60
              else "3mo")
    try:
        # auto_adjust is passed EXPLICITLY. yfinance defaults it to True today; inheriting a
        # vendor library's default is how a convention silently changes between releases.
        h = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    except Exception as e:                                              # noqa: BLE001
        # The LAST resort genuinely has no successor, so this one stays broad -- but it is
        # loud, and it returns None rather than a frame that would read as priced.
        _LOG.warning("prices: yfinance ALSO failed for %s (%s: %s) — no price data",
                     ticker, type(e).__name__, e)
        return None
    if h is None or h.empty:
        _LOG.warning("prices: yfinance returned no rows for %s — no price data", ticker)
        return None
    h = h.tail(days)
    out = pd.DataFrame({"Date": h.index.astype(str), "Open": h["Open"].values,
                        "High": h["High"].values, "Low": h["Low"].values,
                        "Close": h["Close"].values, "Volume": h["Volume"].values})
    return _label(out, ticker, SRC_YFINANCE)


def get_quote(ticker: str) -> dict | None:
    """Price + volume-derived signals: avg dollar volume, 12-1 and 6-1 momentum,
    52-week-high proximity, and realized volatility (annualized). None if no data.

    Carries `source` and `adjusted` so a consumer of these figures can see which vendor
    produced them.
    """
    df = get_history_df(ticker, days=400)
    if df is None or len(df) < 30:
        return None
    src, adj = source_of(df), adjustment_of(df)
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
            "ret_6_1": ret_6_1, "high_prox": high_prox, "realized_vol": realized_vol,
            "source": src, "adjusted": adj}


def close_series(ticker: str, days: int = 1500):
    """(dates, closes) as lists for the backtest, or (None, None).

    **The vendor label does NOT survive this call** — lists carry no `.attrs` — so a caller who
    needs it must either use `get_history_df` directly or read `source_census()`. Said here
    rather than left to be discovered, because this is the entry point almost every consumer
    uses and it is exactly where provenance is most easily lost.
    """
    df = get_history_df(ticker, days=days)
    if df is None or df.empty:
        return None, None
    return [str(d) for d in df["Date"].tolist()], [float(c) for c in df["Close"].tolist()]


def close_series_with_source(ticker: str, days: int = 1500):
    """`(dates, closes, source)` — the labelled form of `close_series`, for callers that record
    provenance. Added rather than changing `close_series`'s return shape, which ~20 call sites
    unpack as a pair."""
    df = get_history_df(ticker, days=days)
    if df is None or df.empty:
        return None, None, None
    return ([str(d) for d in df["Date"].tolist()],
            [float(c) for c in df["Close"].tolist()],
            source_of(df))
