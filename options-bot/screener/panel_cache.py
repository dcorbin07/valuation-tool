"""
panel_cache.py — an on-disk cache for the point-in-time backtest's raw inputs.

The screener backtest is built on free feeds that are slow (EDGAR is rate
limited to ~8 req/s by its own terms) and, in one case, gone (Stooq now answers
scripted requests with a JavaScript browser challenge instead of CSV — see
options_backtest/run_options_backtest.py). Re-fetching a thousand names on every
code edit is how a backtest stops being run at all, so everything lands on disk
once and is re-read from there.

Nothing in here changes what is measured. It changes only how many times we ask
for it.

WHAT IS AND IS NOT POINT-IN-TIME
--------------------------------
  companyfacts   POINT-IN-TIME. Every datapoint carries `filed`; pit_data
                 filters on it. Caching the whole document is safe because the
                 as-of filtering happens downstream, not at fetch time.
  Form 4 index   POINT-IN-TIME. Every filing carries `filingDate`.
  prices         POINT-IN-TIME by construction (a bar is dated).
  sector / SIC   *NOT* point-in-time. EDGAR's submissions feed reports TODAY's
                 classification with no history. SIC codes are near-static and
                 this is used for peer grouping and one liquidity-irrelevant
                 gate, not as a return predictor — but it IS a look-ahead input
                 and is recorded here so nobody has to rediscover that.
  the ticker list itself  NOT point-in-time, and this is the big one. EDGAR's
                 company_tickers.json is TODAY's filers. Anything that delisted
                 is structurally absent, so the panel is survivorship-biased no
                 matter how careful the as-of filtering is. Free data cannot fix
                 that; a Sharadar mirror can (audit item C5).
"""
import gzip
import json
import os
import time

import pandas as pd

import edgar

CACHE_DIR = os.environ.get("SCREENER_CACHE", os.path.join(os.path.dirname(__file__), ".cache"))


def _path(kind, key):
    d = os.path.join(CACHE_DIR, kind)
    os.makedirs(d, exist_ok=True)
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in str(key))
    return os.path.join(d, f"{safe}.json.gz")


def _read(kind, key):
    p = _path(kind, key)
    if not os.path.exists(p):
        return None
    try:
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _write(kind, key, obj):
    p = _path(kind, key)
    tmp = p + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    os.replace(tmp, p)


# ---------------------------------------------------------------------------
#  Fundamentals + filer metadata
# ---------------------------------------------------------------------------

_MISSING = {"__missing__": True}


def companyfacts(ticker):
    """Cached raw companyfacts. A negative result is cached too — a filer with
    no XBRL is a permanent fact, and re-asking EDGAR 1,200 times to be told so
    again is how you get rate-limited."""
    hit = _read("facts", ticker)
    if hit is not None:
        return None if hit.get("__missing__") else hit
    got = edgar.companyfacts(ticker)
    _write("facts", ticker, got if got else _MISSING)
    return got


def submission(ticker):
    """Cached EDGAR submissions document (name, SIC, filing index)."""
    hit = _read("sub", ticker)
    if hit is not None:
        return None if hit.get("__missing__") else hit
    cik = edgar._cik10(ticker)
    got = None
    if cik:
        try:
            got = edgar._get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
        except Exception:
            got = None
    if got:
        # The filing index is huge and we only need the header fields plus the
        # Form 4 rows, which form4_index() fetches separately.
        got = {"name": got.get("name"), "sicDescription": got.get("sicDescription"),
               "entityType": got.get("entityType")}
    _write("sub", ticker, got if got else _MISSING)
    return got


def sector_and_common(ticker):
    """(sector_string, is_common_equity). Mirrors edgar.get_fundamentals' rule."""
    sub = submission(ticker)
    if not sub:
        return None, True
    sic = sub.get("sicDescription")
    return (sic or "?"), ("fund" not in (sic or "").lower())


# ---------------------------------------------------------------------------
#  Prices — bulk, because one-at-a-time is the slow path
# ---------------------------------------------------------------------------

def bulk_prices(tickers, start, end, chunk=100, sleep=0.0):
    """
    Download daily OHLCV for many tickers at once and cache each separately.

    yfinance's multi-symbol download is roughly 20 symbols/second; the
    one-symbol-at-a-time path in prices.py is ~1/second. For a 1,200-name
    universe that is the difference between a minute and twenty.
    """
    import warnings
    warnings.filterwarnings("ignore")
    todo = [t for t in tickers if _read("px", t) is None]
    if not todo:
        return
    import yfinance as yf
    for i in range(0, len(todo), chunk):
        batch = todo[i:i + chunk]
        try:
            df = yf.download(batch, start=start, end=end, auto_adjust=False,
                             progress=False, threads=True, group_by="ticker")
        except Exception:
            df = None
        for t in batch:
            frame = None
            try:
                if df is not None and (t, "Close") in df.columns:
                    sub = df[t][["Close", "Volume"]].dropna(subset=["Close"])
                    if len(sub):
                        frame = {"Date": [d.strftime("%Y-%m-%d") for d in sub.index],
                                 "Close": [float(x) for x in sub["Close"]],
                                 "Volume": [float(x) if x == x else 0.0 for x in sub["Volume"]]}
            except Exception:
                frame = None
            _write("px", t, frame if frame else _MISSING)
        if sleep:
            time.sleep(sleep)


def prices(ticker):
    """Cached DataFrame[Date, Close, Volume], or None."""
    hit = _read("px", ticker)
    if hit is None or hit.get("__missing__"):
        return None
    return pd.DataFrame(hit)


# ---------------------------------------------------------------------------
#  Insider Form 4 — the part that makes the live model replayable at all
# ---------------------------------------------------------------------------

def form4_index(ticker):
    hit = _read("f4idx", ticker)
    if hit is not None:
        return hit if isinstance(hit, list) else []
    got = edgar.form4_index(ticker)
    _write("f4idx", ticker, got)
    return got


def form4_txns(url):
    key = url.rsplit("/edgar/data/", 1)[-1]
    hit = _read("f4", key)
    if hit is not None:
        return hit if isinstance(hit, list) else []
    got = edgar.form4_transactions(url)
    _write("f4", key, got)
    return got


def prefetch_insider(tickers, as_of_dates, limit=6, log_every=25):
    """
    Fetch exactly the Form 4 documents any (ticker, as_of) pair will ask for.

    The live pipeline calls `edgar.get_insider_txns(ticker, limit=6)` — the six
    most recent Form 4s, whatever their dates. Replayed point-in-time that is
    "the six most recent filed ON OR BEFORE as_of", so across N rebalance dates
    the union is far smaller than N x 6: consecutive dates mostly share the same
    six filings. We resolve the union first and fetch each document once.
    """
    iso = sorted(d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
                 for d in as_of_dates)
    wanted, done = set(), 0
    for t in tickers:
        idx = form4_index(t)          # newest first
        for d in iso:
            picked = 0
            for rec in idx:
                if rec["filed"] > d:
                    continue
                wanted.add(rec["url"])
                picked += 1
                if picked >= limit:
                    break
        done += 1
        if log_every and done % log_every == 0:
            print(f"  form4 index: {done}/{len(tickers)} filers, "
                  f"{len(wanted)} documents queued", flush=True)
    todo = [u for u in sorted(wanted) if _read("f4", u.rsplit("/edgar/data/", 1)[-1]) is None]
    print(f"  form4: {len(wanted)} documents needed, {len(todo)} not yet cached", flush=True)
    for i, u in enumerate(todo, 1):
        form4_txns(u)
        if log_every and i % (log_every * 4) == 0:
            print(f"  form4: {i}/{len(todo)} fetched", flush=True)
    return len(wanted)


def insider_asof(ticker, as_of, limit=6):
    """
    The live model's insider input, as it would have looked on `as_of`.

    Returns [] (a real "no qualifying activity" observation) when the filer has
    Form 4s but none of them parse into transactions, and None ONLY when the
    filer has no Form 4 history at all — the distinction `scoring.insider_score`
    is built on.
    """
    d = as_of.strftime("%Y-%m-%d") if hasattr(as_of, "strftime") else str(as_of)[:10]
    idx = form4_index(ticker)
    if not idx:
        return None
    out, picked = [], 0
    for rec in idx:
        if rec["filed"] > d:
            continue
        out.extend(form4_txns(rec["url"]))
        picked += 1
        if picked >= limit:
            break
    if picked == 0:
        # The filer exists but had filed nothing by this date. That is a real
        # observation ("no insider activity yet"), not missing data.
        return []
    return out
