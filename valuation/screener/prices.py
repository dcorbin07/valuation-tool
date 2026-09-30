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

#: yfinance is the PRIMARY and is held to a short timeout on purpose. The point of the order
#: below is that a broken Yahoo reaches Stooq QUICKLY; a generous timeout on the primary would
#: reintroduce the very stall the flip exists to remove, one vendor along.
_YF_TIMEOUT = 8

#: Batch size and pause for `get_history_batch`. Small enough that one throttled chunk costs a
#: chunk rather than a run, with a pause between chunks so a long book does not look like a
#: scrape. Both overridable for tests.
_BATCH = 24
_BATCH_PAUSE_S = 0.5

_LOG = logging.getLogger(__name__)

#: the key the vendor label is written under, on `DataFrame.attrs`
SRC_ATTR = "valquo_src"
#: and the companion key recording how that vendor treats corporate actions
ADJ_ATTR = "valquo_adjusted"

SRC_STOOQ = "stooq"
SRC_YFINANCE = "yfinance"
#: Third resort, keyed and opt-in. See `_fmp_history` -- its seam is unmeasured.
SRC_FMP = "fmp"
FMP_HISTORY_URL = ("https://financialmodelingprep.com/api/v3/historical-price-full/{sym}")

#: What each vendor's `Close` MEANS. `unverified` is a real state and is never rounded to a
#: guess -- see the module docstring.
VENDOR_ADJUSTMENT = {
    SRC_STOOQ: "unverified",
    SRC_YFINANCE: "auto_adjusted",
    SRC_FMP: "unverified",
}

#: Counts by vendor plus the last vendor seen per ticker. The direct path's record; consumers
#: holding an injected `fetch` should read `source_of(df)` instead.
_CENSUS: dict = {"by_vendor": {}, "last_by_ticker": {}, "primary_failures": 0,
                 "stale_rejections": 0,
                 "unlabelled": 0}


def _stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower().replace('.', '-')}.us"


class _StaleFrame(ValueError):
    """A valid frame whose newest row precedes the date the caller needs. A `ValueError` so it
    travels the primary path's existing except-clause; a distinct class so that path can tell
    it from a transient failure and skip the backoff."""


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


def _yf_errors():
    """Exactly what the yfinance path can LEGITIMATELY raise, now that it is the primary.

    **A BROAD `except Exception` HERE IS NOT A SMALL SIN.** The primary runs for every name, and
    swallowing an `AttributeError` or an `ImportError` as "the vendor is down" turns one code
    error into an entire book with no prices and a census that blames Yahoo. The old primary
    path had `_primary_errors()` for exactly this reason; reversing the order without carrying
    the rule across would have quietly dropped it.

    `TypeError` is DELIBERATELY ABSENT. The call passes `timeout=`, so a yfinance release that
    changes that signature raises TypeError -- and catching it would silently unprice every name
    on the day of a library upgrade, which is the worst available failure. It propagates.
    """
    import pandas as pd
    import requests
    errs = [requests.RequestException,        # transport, timeout, HTTP status
            pd.errors.ParserError, pd.errors.EmptyDataError,
            UnicodeDecodeError,
            ValueError]                       # includes this module's own signals
    try:
        from yfinance import exceptions as _yfe
        # YFRateLimitError (the 429) and the missing-data classes derive from YFException.
        # YFNotImplementedError does NOT -- it derives from NotImplementedError/RuntimeError --
        # so listing only the base would let it propagate as a 500. Named explicitly rather than
        # widened to RuntimeError, which would catch genuine programming errors again.
        errs.append(_yfe.YFException)
        errs.append(_yfe.YFNotImplementedError)
    except Exception:                                                   # noqa: BLE001
        pass                                   # older yfinance: the list above still covers it
    return tuple(errs)


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


def _last_date(df):
    """The newest `Date` in a frame as an ISO string, or None when it cannot be read."""
    try:
        import pandas as pd
        d = pd.to_datetime(df["Date"], utc=True, errors="coerce").dropna()
        return None if d.empty else d.max().strftime("%Y-%m-%d")
    except Exception:                                                    # noqa: BLE001
        return None


def _stale(df, as_of) -> bool:
    """Is this frame's newest row EARLIER than the date the caller needs?

    **THE DEFECT THIS CLOSES, AND IT COST THE BOUND TRACK ELEVEN TRADING DAYS.** Stooq's
    success test was `df.empty or "Close" not in df.columns`. A CSV that is perfectly valid
    and simply STALE passes both, so `get_history_df` returned it as SUCCESS and the yfinance
    fallback never ran. The caller then built a date->close map that did not contain the mark
    date and reported the name as UNPRICED -- no exception, no warning, no fallback.

    The symptom was diagnostic: two PT-WRITER runs on different dates reported coverage
    identical to fifteen decimal places (0.812767489300428) and the same sixteen unpriced
    names. Throttling is stochastic; that is deterministic, and deterministic is what a
    consistently-stale vendor file looks like.

    `as_of` is OPTIONAL and omitting it preserves today's behaviour exactly -- a caller that
    does not name the date it needs cannot be told its frame is too old for it.
    """
    if not as_of:
        return False
    last = _last_date(df)
    if last is None:
        # Cannot tell. NOT treated as stale: a frame whose dates are unreadable is a different
        # failure, and the existing column check already rejects an unusable frame.
        return False
    return last < str(as_of)[:10]


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
    _CENSUS["stale_rejections"] = 0
    _CENSUS["throttled"] = 0
    _CENSUS["unpriced"] = 0


def get_history_df(ticker: str, days: int = 400, as_of=None):
    """Daily OHLCV DataFrame (oldest->newest) or None, LABELLED with the vendor that served it.

    **ORDER: yfinance FIRST, Stooq as the fallback, FMP third and gated.** This is a reversal,
    and it was made on measurement rather than preference:

    * **SPEED.** Stooq as primary costs every name a failing round trip before the working
      vendor is reached, and its failure MODE decides how much: a 404 is milliseconds, a
      connect timeout is `_TIMEOUT` x 3 attempts plus backoff. Measured 2026-09-30 --
      `Ticker.history` returned MSFT in **0.4s** while one Stooq request took **30.1s** to time
      out. That single ratio is the whole of the ~10-minute book price, the `/api/track` refresh
      that never finished, and the fleet door that could not answer inside 120s.
    * **BASIS.** The recorded track is ADJUSTED. Re-deriving the benchmark leg of all 24
      recorded rows on both bases: of the 6 rows that can discriminate (after SPY's ex-dividend,
      where the bases diverge ~0.256pp) **6 match adjusted exactly and 0 match plain**; the
      other 17 predate the divergence and carry no information either way. Stooq serves an
      AS-TRADED close and yfinance an adjusted one, so Stooq-first meant the recorded basis was
      whichever vendor happened to answer. yfinance-first makes the recorded basis the default.

    **AN EMPTY yfinance FRAME MEANS "NOT FOUND HERE", NOT "NO PRICE".** It falls through to
    Stooq. Only the exhaustion of every vendor is a missing price, and that returns None so the
    caller counts the name UNPRICED -- never a stale frame, never a last-known close.
    """
    out = _yf_history(ticker, days, as_of=as_of)
    if out is not None:
        return out
    out = _stooq_history(ticker, days, as_of=as_of)
    if out is not None:
        return out
    out = _fmp_history(ticker, days, as_of=as_of)
    if out is None:
        _CENSUS["unpriced"] = _CENSUS.get("unpriced", 0) + 1
        _LOG.warning("prices: NO VENDOR could price %s for %s - counted UNPRICED",
                     ticker, str(as_of)[:10] if as_of else "latest")
    return out


def _stooq_history(ticker: str, days: int = 400, as_of=None):
    """The FALLBACK. Keeps its retry/backoff, which is now cheap because it rarely runs.

    Returns None rather than raising: at this position a failure means "the next vendor", and
    the caller decides what exhaustion means.
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
            # FRESHNESS IS PART OF SUCCESS -- see `_stale`.
            if _stale(df, as_of):
                raise _StaleFrame(
                    "stooq's newest row is %s, older than the requested %s"
                    % (_last_date(df), str(as_of)[:10]))
            return _label(df.tail(days).reset_index(drop=True), ticker, SRC_STOOQ)
        except _primary_errors() as e:
            last = e
            # A STALE FRAME IS NOT A TRANSIENT BLIP: it comes back identical on every attempt,
            # so retrying buys nothing and costs the sleeps.
            if isinstance(e, _StaleFrame):
                _CENSUS["stale_rejections"] = _CENSUS.get("stale_rejections", 0) + 1
                break
            if attempt < 2:
                time.sleep(0.4 * (attempt + 1))
    _LOG.warning("prices: stooq (fallback) failed for %s after %d attempt(s) (%s: %s)",
                 ticker, attempt + 1, type(last).__name__, last)
    return None


def _is_throttle(e) -> bool:
    """HTTP 429 -- 'unpriced this run, retry next run', never an error that aborts a batch.

    The TYPE check comes first and is not decoration. yfinance's own rate-limit class is
    `YFRateLimitError`, and matching it only by message means a vendor rewording its string
    silently reclassifies every throttle as a vendor failure -- which counts the name against
    the wrong bucket and logs the wrong cause, with nothing raising. The class name alone does
    not save it either: `yfratelimiterror` contains neither "429" nor "rate limit" (no space),
    so the text rule matches today purely via the message this release happens to carry.
    """
    try:
        from yfinance.exceptions import YFRateLimitError
        if isinstance(e, YFRateLimitError):
            return True
    except Exception:                                                   # noqa: BLE001
        pass                                    # older yfinance: the text rule below still runs
    txt = ("%s %s" % (type(e).__name__, e)).lower()
    return "429" in txt or "too many requests" in txt or "rate limit" in txt


def get_history_batch(tickers, days: int = 400, as_of=None, chunk: int = None,
                      pause: float = None) -> dict:
    """{ticker: frame-or-None} for many names, batched on the primary with a small pause.

    One `yf.download` per chunk instead of one request per name, because the per-name path is
    what made a 410-pick refresh unfinishable. A chunk that throttles does NOT abort the batch:
    its names are left for the per-name pass, and if that throttles too they come back None and
    the caller counts them unpriced THIS RUN -- the next run retries them.

    Names the batch could not serve fall through to `get_history_df`, so every guarantee of the
    single-name path (Stooq fallback, freshness, fail-closed) still holds for them.
    """
    import time

    import pandas as pd

    ts = [str(t).upper() for t in tickers if t]
    if not ts:
        return {}
    chunk = int(chunk or _BATCH)
    pause = _BATCH_PAUSE_S if pause is None else pause
    period = _yf_period(days)
    out: dict = {}

    for i in range(0, len(ts), chunk):
        part = ts[i:i + chunk]
        try:
            import yfinance as yf
            df = yf.download(part, period=period, auto_adjust=True, progress=False,
                             threads=False, timeout=_YF_TIMEOUT, group_by="ticker")
        except Exception as e:                                          # noqa: BLE001
            if _is_throttle(e):
                _CENSUS["throttled"] = _CENSUS.get("throttled", 0) + len(part)
                _LOG.warning("prices: batch THROTTLED for %d name(s) - unpriced this run, "
                             "retrying next run", len(part))
            else:
                _LOG.warning("prices: batch failed (%s: %s) - falling back per name",
                             type(e).__name__, e)
            df = None

        for t in part:
            frame = None
            if df is not None:
                try:
                    sub = df[t] if hasattr(df, "columns") and t in getattr(
                        df.columns, "levels", [[]])[0] else (df if len(part) == 1 else None)
                    if sub is not None and not sub.empty and "Close" in sub.columns:
                        f = pd.DataFrame({"Date": sub.index.astype(str),
                                          "Open": sub["Open"].values, "High": sub["High"].values,
                                          "Low": sub["Low"].values, "Close": sub["Close"].values,
                                          "Volume": sub["Volume"].values}).dropna(subset=["Close"])
                        if not f.empty and not _stale(f, as_of):
                            frame = _label(f.tail(days).reset_index(drop=True), t, SRC_YFINANCE)
                except Exception:                                       # noqa: BLE001
                    frame = None
            out[t] = frame
        if pause and i + chunk < len(ts):
            time.sleep(pause)

    # Anything the batch could not serve goes down the full single-name chain, so the fallback
    # and the fail-closed rule apply to it exactly as they would have without batching.
    for t in ts:
        if out.get(t) is None:
            out[t] = get_history_df(t, days=days, as_of=as_of)
    return out


def _yf_period(days: int) -> str:
    # "max" ABOVE TEN YEARS, and it is additive: the largest `days` any shipped caller passes
    # is 2700, which still maps to "10y", so every existing consumer is bit-identical.
    return ("max" if days > 3650 else "10y" if days > 1825 else "5y" if days > 730
            else "2y" if days > 365 else "1y" if days > 180 else "6mo" if days > 60
            else "3mo")


def _yf_history(ticker: str, days: int, as_of=None):
    """THE PRIMARY. Fast, adjusted, and it fails fast so the fallback is reached quickly.

    **RETURNING None HERE MEANS "TRY THE NEXT VENDOR", NOT "NO PRICE".** That distinction is the
    whole contract with `get_history_df`: an empty frame from Yahoo is a name Yahoo does not
    carry, not a name without a price, and treating the two alike is how a working Stooq would
    never be consulted. Only `get_history_df` decides a name is unpriced, and only after every
    vendor has declined.

    **NO RETRY LOOP ON A CLEAR FAILURE.** The old primary spent three attempts and two sleeps
    before conceding. A 404, an empty frame or a refusal is deterministic -- retrying it buys
    nothing and costs the very seconds this reordering exists to save, and when Yahoo is broken
    for everyone that cost is paid by every name in the book.
    """
    import pandas as pd
    import yfinance as yf

    period = _yf_period(days)
    try:
        # auto_adjust is passed EXPLICITLY. yfinance defaults it to True today; inheriting a
        # vendor library's default is how a convention silently changes between releases -- and
        # this one now decides the basis of the recorded series, so it is named here.
        h = yf.Ticker(ticker).history(period=period, auto_adjust=True, timeout=_YF_TIMEOUT)
    except _yf_errors() as e:
        if _is_throttle(e):
            # 429 is NOT a vendor failure and must not be counted as one: the name is unpriced
            # THIS RUN and the next run retries it. Counting it as a failure would make a
            # throttled afternoon look like a dead vendor.
            _CENSUS["throttled"] = _CENSUS.get("throttled", 0) + 1
            _LOG.warning("prices: yfinance THROTTLED for %s - unpriced this run, retrying "
                         "next run", ticker)
            return None
        _CENSUS["primary_failures"] = _CENSUS.get("primary_failures", 0) + 1
        _LOG.warning("prices: yfinance (primary) failed for %s (%s: %s) - trying stooq",
                     ticker, type(e).__name__, e)
        return None
    if h is None or h.empty:
        _CENSUS["primary_failures"] = _CENSUS.get("primary_failures", 0) + 1
        _LOG.warning("prices: yfinance returned no rows for %s - NOT FOUND HERE, trying stooq",
                     ticker)
        return None
    h = h.tail(days)
    out = pd.DataFrame({"Date": h.index.astype(str), "Open": h["Open"].values,
                        "High": h["High"].values, "Low": h["Low"].values,
                        "Close": h["Close"].values, "Volume": h["Volume"].values})
    out = _label(out, ticker, SRC_YFINANCE)
    # THE SAME FRESHNESS RULE AS THE FALLBACK. A stale primary frame is exactly as unusable as
    # a stale fallback one, and if only one side were checked the defect would just move.
    if _stale(out, as_of):
        _CENSUS["stale_rejections"] = _CENSUS.get("stale_rejections", 0) + 1
        _LOG.warning("prices: yfinance's newest row for %s is %s, older than the requested %s "
                     "- trying stooq", ticker, _last_date(out), str(as_of)[:10])
        return None
    return out


def _fmp_history(ticker: str, days: int, as_of=None):
    """THIRD RESORT ONLY, keyed, and GATED ON AN UNMEASURED SEAM.

    **FMP IS NOT THE PRIMARY AND MUST NOT BECOME ONE BY DEFAULT.** Its closes have never been
    compared against the recorded series, so a row priced from it would carry an unmeasured
    discontinuity into the one dataset this project cannot rebuild. Twenty of the service's
    twenty-two recorded rows reproduce to under 0.0005pp from the yfinance-equivalent close;
    no such statement exists for FMP.

    So this tier requires TWO things, not one: a key, and `PRICES_ALLOW_FMP=1` set
    deliberately. Without the opt-in it returns None and says why. That is the fail-closed
    direction: a missing price refuses a row, and refusing a row is recoverable, while a row
    priced from an unvalidated vendor is a permanent entry in an append-only record.

    Measure the seam first: re-derive the 2026-08-27 and 2026-09-25 rows from FMP closes
    against the SERVICE's recorded values, and log the result as a disclosure.
    """
    import os
    key = (os.environ.get("FMP_API_KEY") or "").strip()
    if not key:
        return None
    if (os.environ.get("PRICES_ALLOW_FMP") or "").strip() not in ("1", "true", "True"):
        _LOG.warning("prices: FMP is configured but NOT enabled for %s. Its seam against the "
                     "recorded series is unmeasured, so it may not price a row until "
                     "PRICES_ALLOW_FMP=1 is set deliberately. No price returned.", ticker)
        return None
    import pandas as pd
    import requests
    try:
        r = requests.get(FMP_HISTORY_URL.format(sym=str(ticker).upper()),
                         params={"apikey": key, "serietype": "line"}, timeout=_TIMEOUT)
        r.raise_for_status()
        hist = ((r.json() or {}).get("historical") or [])
        if not hist:
            raise ValueError("FMP returned no historical rows")
        out = pd.DataFrame({"Date": [h.get("date") for h in hist],
                            "Close": [h.get("close") for h in hist]})
        out = out.dropna().iloc[::-1].reset_index(drop=True).tail(days)
        if out.empty:
            raise ValueError("FMP returned no usable closes")
        out = _label(out, ticker, SRC_FMP)
        if _stale(out, as_of):
            _CENSUS["stale_rejections"] = _CENSUS.get("stale_rejections", 0) + 1
            _LOG.warning("prices: FMP's newest row for %s is %s, older than %s — no price",
                         ticker, _last_date(out), str(as_of)[:10])
            return None
        return out
    except Exception as e:                                              # noqa: BLE001
        _LOG.warning("prices: FMP ALSO failed for %s (%s: %s) — no price data",
                     ticker, type(e).__name__, e)
        return None


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
