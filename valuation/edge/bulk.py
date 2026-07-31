"""
Sharadar BULK full-table loaders — streaming, column-pruned, cached.

The bulk downloads are all-ticker exports, not the per-ticker format the rest of the
loader expects, and they are big: SF3 is 79.4M rows / 2.9GB unzipped, DAILY 2.5GB. The
existing WRDSProvider._indexed() materializes a whole file as a dict of per-row dicts,
which measured at 289s and 2.2GB of Python heap for the 580MB insiders file alone — that
is the reason the full-universe backtest never finished.

So nothing here ever loads a whole file. Each table is streamed ONCE with csv.reader,
pruned to the columns actually used, reduced to the compact aggregate the panel needs, and
cached to a small pickle. Re-runs read the pickle in under a second.

    SF3     79.4M rows -> per (ticker, quarter): holder count, total value, and
                          conviction = sum over managers of position / that manager's AUM.
                          Bounded memory: manager AUM is only 12.5k managers x 53 quarters.
    DAILY   2.5GB      -> per ticker: month-end marketcap / pe / pb / ps / evebitda.
                          Sharadar's own point-in-time values, so we stop deriving market
                          cap from shares x price (the path that hid the `assets` bug).
    EVENTS  53MB       -> per ticker: RAW (date, codes). The earnings-code legend is not
                          in the download and the obvious guess is wrong, so it is left
                          uninterpreted rather than fabricated — see prepare_events().
    ACTIONS 47MB       -> per ticker: splits, dividends and delistings.

Deliberate limitation, stated so nobody assumes otherwise: the conviction figure uses
each manager's position relative to their own book, and breadth uses the change in holder
COUNT. It does not separate "newly initiated" from "increased", because that needs
per-(ticker, manager) history across quarters — tens of millions of keys — which would
reintroduce exactly the memory problem this module exists to avoid. If the signal earns
its place, the next step is an on-disk sort by (ticker, manager, quarter) and one
sequential scan.
"""
from __future__ import annotations

import csv
import os
import pickle
import sys
import time
from typing import Optional

DEFAULT_BULK_DIR = os.path.join("data", "bulk")
DEFAULT_CACHE_DIR = os.path.join("data", "bulk", "prepared")
_PROGRESS_EVERY = 8_000_000


def _log(msg):
    print(f"[bulk] {msg}", flush=True)


def _cache_path(name: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, f"{name}.pkl")


def _load_cache(name: str, cache_dir: str):
    p = _cache_path(name, cache_dir)
    if os.path.exists(p):
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    return None


def _save_cache(name: str, cache_dir: str, obj) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    with open(_cache_path(name, cache_dir), "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)


def _header(reader):
    """First row, or None for an empty/truncated file.

    A zero-byte or header-less bulk CSV (a download that died part-way, say) must degrade
    to "no data" like a missing file does, not raise StopIteration out of the loader and
    take a panel build down with it.
    """
    try:
        return next(reader)
    except StopIteration:
        return None


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


# --------------------------------------------------------------------------- #
#  SF3 — per-manager 13F detail
# --------------------------------------------------------------------------- #
def prepare_sf3(csv_path: str, cache_dir: str = DEFAULT_CACHE_DIR,
                rebuild: bool = False, security_type: str = "SHR") -> dict:
    """{ticker: {quarter: {"holders": n, "value": v, "conviction": c}}}

    Two bounded streaming passes:
      A. manager AUM per quarter  (12.5k managers x 53 quarters — trivial)
      B. per (ticker, quarter) holder count, total value, and the AUM-relative conviction
    Only `security_type` rows count (SHR = common shares, 75% of the file); calls and puts
    are a different exposure and would pollute an ownership signal.
    """
    cached = None if rebuild else _load_cache("sf3", cache_dir)
    if cached is not None:
        _log(f"sf3: cache hit ({len(cached):,} tickers)")
        return cached
    if not os.path.exists(csv_path):
        _log(f"sf3: {csv_path} not found — skipping")
        return {}

    t0 = time.time()
    # ---- pass A: manager AUM per quarter
    aum: dict = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = _header(r)
        if h is None:
            return {}
        iM, iS, iD, iV = h.index("investorname"), h.index("securitytype"), h.index("calendardate"), h.index("value")
        n = 0
        for row in r:
            n += 1
            if row[iS] != security_type:
                continue
            v = _f(row[iV])
            if v is None or v <= 0:
                continue
            k = (row[iM], row[iD])
            aum[k] = aum.get(k, 0.0) + v
            if n % _PROGRESS_EVERY == 0:
                _log(f"sf3 pass A: {n/1e6:.0f}M rows, {time.time()-t0:.0f}s")
    _log(f"sf3 pass A done: {len(aum):,} manager-quarters in {time.time()-t0:.0f}s")

    # ---- pass B: per (ticker, quarter) aggregates
    t1 = time.time()
    out: dict = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = _header(r)
        if h is None:
            return {}
        iT, iM, iS, iD, iV = (h.index("ticker"), h.index("investorname"), h.index("securitytype"),
                              h.index("calendardate"), h.index("value"))
        n = 0
        for row in r:
            n += 1
            if row[iS] != security_type:
                continue
            v = _f(row[iV])
            if v is None or v <= 0:
                continue
            t, q = row[iT], row[iD]
            book = aum.get((row[iM], q))
            per_t = out.setdefault(t, {})
            rec = per_t.get(q)
            if rec is None:
                rec = per_t[q] = [0, 0.0, 0.0]        # holders, value, conviction
            rec[0] += 1
            rec[1] += v
            if book and book > 0:
                # Share of this manager's whole book committed to this name. Summed across
                # managers it is "how much conviction, weighted by who is expressing it".
                rec[2] += v / book
            if n % _PROGRESS_EVERY == 0:
                _log(f"sf3 pass B: {n/1e6:.0f}M rows, {time.time()-t1:.0f}s")

    prepared = {t: {q: {"holders": r[0], "value": r[1], "conviction": r[2]}
                    for q, r in qs.items()} for t, qs in out.items()}
    _save_cache("sf3", cache_dir, prepared)
    _log(f"sf3: {len(prepared):,} tickers prepared in {time.time()-t0:.0f}s total")
    return prepared


# --------------------------------------------------------------------------- #
#  DAILY — point-in-time market cap + valuation ratios
# --------------------------------------------------------------------------- #
def prepare_daily(csv_path: str, cache_dir: str = DEFAULT_CACHE_DIR,
                  rebuild: bool = False) -> dict:
    """{ticker: [(date, marketcap, pe, pb, ps, evebitda), ...]} sorted by date.

    Down-sampled to ONE ROW PER TICKER-MONTH (the last observation in each month). The
    panel rebalances quarterly, so daily granularity is 20x waste; this turns 2.5GB into
    a few MB while staying strictly point-in-time (we keep the last date actually present,
    never a future one).
    """
    cached = None if rebuild else _load_cache("daily", cache_dir)
    if cached is not None:
        _log(f"daily: cache hit ({len(cached):,} tickers)")
        return cached
    if not os.path.exists(csv_path):
        _log(f"daily: {csv_path} not found — skipping")
        return {}

    t0 = time.time()
    latest: dict = {}          # (ticker, YYYY-MM) -> tuple
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = _header(r)
        if h is None:
            return {}
        iT, iD = h.index("ticker"), h.index("date")
        iMC, iPE, iPB, iPS = h.index("marketcap"), h.index("pe"), h.index("pb"), h.index("ps")
        iEE = h.index("evebitda")
        n = 0
        for row in r:
            n += 1
            d = row[iD]
            key = (row[iT], d[:7])
            prev = latest.get(key)
            if prev is None or d > prev[0]:
                latest[key] = (d, _f(row[iMC]), _f(row[iPE]), _f(row[iPB]),
                               _f(row[iPS]), _f(row[iEE]))
            if n % _PROGRESS_EVERY == 0:
                _log(f"daily: {n/1e6:.0f}M rows, {time.time()-t0:.0f}s")

    out: dict = {}
    for (t, _m), rec in latest.items():
        out.setdefault(t, []).append(rec)
    for t in out:
        out[t].sort(key=lambda x: x[0])
    _save_cache("daily", cache_dir, out)
    _log(f"daily: {len(out):,} tickers, {sum(len(v) for v in out.values()):,} month-rows "
         f"in {time.time()-t0:.0f}s")
    return out


# --------------------------------------------------------------------------- #
#  EVENTS / ACTIONS — small tables
# --------------------------------------------------------------------------- #
# Which event code means "earnings announcement" is NOT settled here — see the note in
# prepare_events(). Set this from Sharadar's EVENTS documentation before relying on it.
EARNINGS_CODES: set = set()


def prepare_events(csv_path: str, cache_dir: str = DEFAULT_CACHE_DIR,
                   rebuild: bool = False) -> dict:
    """{ticker: [(date, [code, ...]), ...]} sorted ascending — RAW codes, uninterpreted.

    A word on why this doesn't return earnings dates. The file gives numeric `eventcodes`
    with no legend in the download, and the obvious guess is wrong: AAPL's recent rows
    carry 22 / 52 / 57 / 91, and the code frequencies don't fit a quarterly-earnings
    cadence either (code 11 appears ~18x per ticker over ~24 years, far too few; code 91
    appears ~95x, which is closer but unverified).

    Rather than ship a plausible-looking earnings calendar built on a guess — which would
    silently corrupt any earnings-aware factor downstream — this keeps the raw codes so the
    table is wired and queryable, and leaves the mapping to be filled in from Sharadar's
    EVENTS documentation. Populate EARNINGS_CODES and use earnings_dates() below.
    """
    cached = None if rebuild else _load_cache("events", cache_dir)
    if cached is not None:
        return cached
    if not os.path.exists(csv_path):
        return {}
    t0 = time.time()
    out: dict = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = _header(r)
        if h is None:
            return {}
        iT, iD, iC = h.index("ticker"), h.index("date"), h.index("eventcodes")
        for row in r:
            codes = row[iC].replace("|", " ").split()
            if codes:
                out.setdefault(row[iT], []).append((row[iD], codes))
    for t in out:
        out[t].sort(key=lambda x: x[0])
    _save_cache("events", cache_dir, out)
    _log(f"events: {len(out):,} tickers, raw codes kept (earnings mapping UNVERIFIED) "
         f"in {time.time()-t0:.0f}s")
    return out


def earnings_dates(events: dict, ticker: str, codes: Optional[set] = None) -> list:
    """Dates for `ticker` whose event codes intersect `codes`.

    Returns [] while EARNINGS_CODES is empty — deliberately inert until the mapping is
    confirmed, so a caller can wire against this now and get real data the moment the
    legend is filled in, without silently getting wrong dates in the meantime.
    """
    codes = codes if codes is not None else EARNINGS_CODES
    if not codes:
        return []
    return [d for d, cs in events.get(ticker, []) if any(c in codes for c in cs)]


def prepare_actions(csv_path: str, cache_dir: str = DEFAULT_CACHE_DIR,
                    rebuild: bool = False) -> dict:
    """{ticker: {"splits": [(date, ratio)], "delisted": date|None, "dividends": [(date, amt)]}}

    Splits and delistings are what make forward returns honest: an unadjusted split looks
    like a -50% return, and a silently-missing delisting is survivorship bias.
    """
    cached = None if rebuild else _load_cache("actions", cache_dir)
    if cached is not None:
        return cached
    if not os.path.exists(csv_path):
        return {}
    t0 = time.time()
    out: dict = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = _header(r)
        if h is None:
            return {}
        iD, iA, iT, iV = h.index("date"), h.index("action"), h.index("ticker"), h.index("value")
        for row in r:
            t, a = row[iT], (row[iA] or "").lower()
            rec = out.setdefault(t, {"splits": [], "delisted": None, "dividends": []})
            if a == "split":
                v = _f(row[iV])
                if v:
                    rec["splits"].append((row[iD], v))
            elif a == "delisted":
                rec["delisted"] = row[iD]
            elif a == "dividend":
                v = _f(row[iV])
                if v:
                    rec["dividends"].append((row[iD], v))
    for t in out:
        out[t]["splits"].sort()
        out[t]["dividends"].sort()
    _save_cache("actions", cache_dir, out)
    _log(f"actions: {len(out):,} tickers in {time.time()-t0:.0f}s")
    return out


def prepare_insiders(csv_path: str, cache_dir: str = DEFAULT_CACHE_DIR,
                     rebuild: bool = False) -> dict:
    """{ticker: [(filing_date, signed_value), ...]} sorted — streamed, not materialized.

    This is the single biggest performance fix in the loader. WRDSProvider._indexed()
    turned the 580MB insiders file into a dict of 5.6M per-row dicts: measured at 289
    seconds and 2.2GB of Python heap, before the panel had scored a single date. The panel
    only ever needs (filing date, signed transaction value) per ticker, so stream it once
    and keep just that — two floats per row instead of a dict of eight strings.
    """
    cached = None if rebuild else _load_cache("insiders", cache_dir)
    if cached is not None:
        _log(f"insiders: cache hit ({len(cached):,} tickers)")
        return cached
    if not os.path.exists(csv_path):
        _log(f"insiders: {csv_path} not found — skipping")
        return {}
    t0 = time.time()
    out: dict = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = _header(r)
        if h is None:
            return {}
        iT = h.index("ticker")
        iFD = h.index("filingdate") if "filingdate" in h else h.index("date")
        iV = h.index("transactionvalue") if "transactionvalue" in h else None
        iSh = h.index("transactionshares") if "transactionshares" in h else None
        iPx = h.index("transactionpricepershare") if "transactionpricepershare" in h else None
        n = 0
        for row in r:
            n += 1
            d = row[iFD]
            if not d:
                continue
            v = _f(row[iV]) if iV is not None else None
            if v is None and iSh is not None and iPx is not None:
                sh, px = _f(row[iSh]), _f(row[iPx])
                v = (sh * px) if (sh is not None and px is not None) else None
            if v is None:
                continue
            out.setdefault(row[iT], []).append((d, v))
            if n % _PROGRESS_EVERY == 0:
                _log(f"insiders: {n/1e6:.0f}M rows, {time.time()-t0:.0f}s")
    for t in out:
        out[t].sort(key=lambda x: x[0])
    _save_cache("insiders", cache_dir, out)
    _log(f"insiders: {len(out):,} tickers, {sum(len(v) for v in out.values()):,} rows "
         f"in {time.time()-t0:.0f}s")
    return out


def prepare_tickers(cache_dir: str = DEFAULT_CACHE_DIR, api_key: str = "",
                    rebuild: bool = False) -> dict:
    """Ticker -> {sector, industry, country, exchange, category, scale}, from Sharadar TICKERS.

    The ONLY table here fetched from the API rather than a bulk CSV — it is small (~21k rows,
    one paged call) and is not part of the bulk download. Everything else in this module
    streams a local file.

    This is what finally makes `sector_neutral` mean something: the panel had no sector column
    at all and hard-coded `"sector": ""`, so grouping by sector grouped on a constant and the
    whole sector-neutral path has been INERT in every backtest ever run.

    LOOK-AHEAD CAVEAT, state it wherever these are used: TICKERS carries TODAY's classification,
    so applying it to a 1998 row assumes the company was in the same sector then. Sector
    reclassification is rare and is not return-predictive, so this is normally considered
    benign — but it is not point-in-time, and it is the one non-PIT input in an otherwise
    strictly point-in-time panel.
    """
    cached = None if rebuild else _load_cache("tickers", cache_dir)
    if cached:
        return cached
    if not api_key:
        _log("tickers: no SHARADAR_API_KEY — skipping (sector data stays unavailable)")
        return {}
    from .data_providers import SharadarProvider

    class _Cfg:
        sharadar_api_key = api_key

    prov = SharadarProvider(_Cfg())
    cols, data = prov._get_paged("TICKERS")
    if not cols or not data:
        _log("tickers: empty response")
        return {}
    idx = {c: i for i, c in enumerate(cols)}
    ti, tbl = idx.get("ticker"), idx.get("table")
    if ti is None:
        return {}

    def g(row, name):
        i = idx.get(name)
        v = row[i] if (i is not None and i < len(row)) else None
        return str(v).strip() if v not in (None, "") else ""

    out = {}
    for r in data:
        t = r[ti]
        if not t:
            continue
        # Prefer the SF1-covered row when a ticker appears more than once (SF1/SFP/etc).
        is_sf1 = (tbl is not None and str(r[tbl]).upper() == "SF1")
        if t in out and not is_sf1:
            continue
        out[str(t).upper()] = {"sector": g(r, "sector"), "industry": g(r, "industry"),
                               "country": g(r, "location") or g(r, "country"),
                               "exchange": g(r, "exchange"), "category": g(r, "category"),
                               "scale": g(r, "scalemarketcap")}
    _log(f"tickers: {len(out):,} tickers with metadata "
         f"({sum(1 for v in out.values() if v['sector']):,} have a sector)")
    _save_cache("tickers", cache_dir, out)
    return out


def prepare_all(bulk_dir: str = DEFAULT_BULK_DIR, cache_dir: str = DEFAULT_CACHE_DIR,
                rebuild: bool = False) -> dict:
    """Prepare every bulk table that's present. Safe to re-run — caches are reused."""
    return {
        "actions": prepare_actions(os.path.join(bulk_dir, "actions.csv"),
                                   cache_dir=cache_dir, rebuild=rebuild),
        "events": prepare_events(os.path.join(bulk_dir, "events.csv"),
                                 cache_dir=cache_dir, rebuild=rebuild),
        "daily": prepare_daily(os.path.join(bulk_dir, "daily.csv"),
                               cache_dir=cache_dir, rebuild=rebuild),
        "sf3": prepare_sf3(os.path.join(bulk_dir, "sf3.csv"),
                           cache_dir=cache_dir, rebuild=rebuild),
    }


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Prepare Sharadar bulk tables into compact caches.")
    ap.add_argument("--bulk-dir", default=DEFAULT_BULK_DIR)
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated: actions,events,daily,sf3")
    a = ap.parse_args(argv)
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    fns = {"actions": prepare_actions, "events": prepare_events,
           "daily": prepare_daily, "sf3": prepare_sf3}
    for name, fn in fns.items():
        if only and name not in only:
            continue
        fn(os.path.join(a.bulk_dir, f"{name}.csv"),
           cache_dir=a.cache_dir, rebuild=a.rebuild)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
