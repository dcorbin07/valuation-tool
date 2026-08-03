# Sharadar Core US Equities Bundle — Technical Reference

**Compiled:** 2026-07-26. Sources are official Nasdaq docs, Sharadar's own published code, and licensed redistributors. Items I could not verify are flagged in §8 rather than guessed at.

---

## 1. Platform status — Nasdaq Data Link is alive and canonical

Not sunset, not rebranded, not moved. Evidence, strongest first:

- **Sharadar's own bulk-download script hardcodes the host** — [www.sharadar.com/meta/bulk_fetch.py](http://www.sharadar.com/meta/bulk_fetch.py), linked from Nasdaq's help center:
  ```python
  URL = 'https://data.nasdaq.com/api/v3/datatables/SHARADAR/%s.json?qopts.export=true&api_key=%s'
  ```
- Official docs state it: *"The Tables API operates from `https://data.nasdaq.com/api/v3/datatables/`"* — [in-depth usage](https://docs.data.nasdaq.com/docs/in-depth-usage-1)
- [status.data.nasdaq.com](https://status.data.nasdaq.com/) — all systems operational, 100% uptime over 90 days, no incidents through July 2026
- Nasdaq is migrating *more* services onto Data Link (European File Delivery Service → "Nasdaq Data Link - Files (SFTP)" during 2026) — the opposite of a sunset signal

**Is Sharadar sold direct now?** No. `sharadar.com` is a shopfront whose product links point to Nasdaq Data Link. QuantRocket (a licensed redistributor) confirms: *"professional users must purchase Sharadar data from Nasdaq Data Link."* Your Nasdaq key is the right and only credential — grab it at `https://data.nasdaq.com/account/profile`.

| Host | Status | Use |
|---|---|---|
| **`data.nasdaq.com`** | **Canonical** | API + account. Build against this. |
| `docs.data.nasdaq.com` | Current | API documentation |
| `help.data.nasdaq.com` | Current | Sharadar specifics |
| `www.quandl.com` | Legacy | Product pages only. **Not for the API.** |

---

## 2. Tables in the bundle

Per [Nasdaq help article 533](https://help.data.nasdaq.com/article/533-what-are-the-column-definitions-for-the-sharadar-data-feeds), **SFA = `SF1, TICKERS, DAILY, SP500, ACTIONS, EVENTS, SF2, SF3, SF3A, SF3B, SEP, SFP`** — 12 tables.

| Code | Title | Sync watermark |
|---|---|---|
| `SF1` | Core US Fundamentals | `lastupdated` |
| `SEP` | Equity Prices (stocks only) | `date` |
| `SFP` | Fund Prices (ETFs, CEFs, ETNs) | `date` |
| `TICKERS` | Tickers and Metadata | `lastupdated` |
| `DAILY` | Daily Metrics | `lastupdated` |
| `ACTIONS` | Corporate Actions | `date` |
| `EVENTS` | Fundamental Events (8-K) | `date` |
| `SP500` | S&P 500 Current + Historical Constituents | `date` |
| `SF2` | Core US Insiders (Forms 3/4/5) | `filingdate` |
| `SF3` / `SF3A` / `SF3B` | Institutional (13F) detail / by-ticker / by-investor | `calendardate` |

**`SHARADAR/METRICS` does not exist.** You're thinking of **`DAILY`**, whose official title is "Daily Metrics."

### Make this your first API call

Sharadar publishes its own data dictionary as a table:

```
https://data.nasdaq.com/api/v3/datatables/SHARADAR/INDICATORS?table=SF1,SEP,TICKERS,ACTIONS,EVENTS,EVENTCODES&api_key=KEY&qopts.export=true
```

It's the source of truth for every column list, the ACTIONS enum, and the 8-K eventcode mapping. Resolves most of §8 in one request.

---

## 3. SEP — equity prices

| Column | Adjustment | Notes |
|---|---|---|
| `ticker` | — | Punctuation stripped (`BRK.B`→`BRKB`); recycled tickers suffixed (`GM` current, `GM1` the 2009 entity) |
| `date` | — | Trading date, US/Eastern session |
| `open` `high` `low` `close` | **Split only** | Not dividend-adjusted |
| `volume` | **Split-adjusted** | Hence frequently non-integer |
| `closeadj` | **Split + dividend** | The total-return series |
| `closeunadj` | **None** | Raw as-traded |
| `lastupdated` | — | Row modification date |

**Proof from real output** (AAPL 2018-12-31): `close=39.435`, `closeunadj=157.74`, `closeadj=37.949`. `closeunadj/close = 4.000` — the Aug-2020 4:1 split applied retroactively.

### Total return

```python
daily_total_return = df['closeadj'].pct_change()
```

Four traps:

1. **Never use `close` for returns** — omits dividends entirely, understating total return by the full yield.
2. **`closeadj` is back-adjusted** — the whole history is rewritten on every new split/dividend. Valid as a *return* series, **not** as a point-in-time price level. For "was this a sub-$5 stock at the time" screens use `closeunadj`.
3. **Don't build market cap from `closeadj`.** Sharadar defines `marketcap = sharesbas × price × sharefactor` where `price` is split-adjusted-only — consistent with `close`.
4. **Guard against distributions exceeding price.** `1 - dividend/close` goes negative on large special distributions and naive compounding blows up.

Round-trip back to raw OHLCV:
```python
m = df['closeunadj'] / df['close']    # cumulative split factor
df[['open','high','low']] *= m
df['close'] = df['closeunadj']
df['volume'] /= m
```

**Survivorship-free: confirmed.** Delisted tickers retain full price history — [help article 508](https://help.data.nasdaq.com/article/508-do-you-cover-delisted-stocks). History starts **December 1998**. SEP is US stocks only; ETFs/CEFs/ETNs are in **SFP** (identical schema — concatenate them).

---

## 4. SF1 — fundamentals, dimensions, and the look-ahead traps

**111 columns**, not the ~150 the marketing datasheet claims. Groups: Entity (9), Balance Sheet (28), Income Statement (25), Cash Flow (13), Metrics (36). Lowercase names — `revenue`, `netinc`, `ebitda`, `opinc`, `assets`, `equity`, `ncfo`, `fcf`, `marketcap`, `ev`, `pe`, `ps`, `pb`, `de`, `roe`, `roa`, `roic`, `eps`, `dps`, `sharesbas`, `shareswa`, `capex`, `depamor`, `debt`, `cashneq`.

### Currency — easiest thing to get wrong

Fields marked `unit: currency` are in the **company's reporting currency**, not USD. Sharadar covers ADRs and Canadian issuers, so a Canadian filer's `revenue` may be CAD. Every such field has a USD twin: `revenueusd`, `netinccmnusd`, `ebitusd`, `ebitdausd`, `epsusd`, `equityusd`, `cashnequsd`, `debtusd`.

**For any cross-sectional ranking, use the `*USD` variants.** `marketcap` and `ev` are always USD already.

Also: **include `sharefactor` in every per-share computation** — it adjusts for ADR ratios and multi-class structures. And note `roic` uses **EBIT** (pre-tax), not NOPAT; `invcap`/`invcapavg`/`roic` carry an explicit "calculation method subject to change" warning in their own definitions.

### Dimensions

> **ARQ**: Quarterly, excluding restatements · **MRQ**: Quarterly, including restatements · **ARY**: Annual, excluding · **MRY**: Annual, including · **ART**: TTM, excluding · **MRT**: TTM, including

AR = As Reported, MR = Most Recent Reported.

| Code | Period | Restatements | Backtest-safe |
|---|---|---|---|
| **ARQ** | Fiscal quarter | Excluded — as originally filed | **Yes** |
| **ARY** | Fiscal year | Excluded | **Yes** |
| **ART** | TTM | Excluded | **Yes** |
| MRQ/MRY/MRT | same | **Included — hindsight** | **No** |

ARQ is domestic-only for quarterly data (foreign private issuers don't file 10-Qs).

### The date fields — two independent traps in one column

Verbatim from Sharadar:

- **`datekey`** — *"the SEC filing date for AR dimensions (ARQ;ART;ARY); and the [REPORTPERIOD] for MR dimensions... this is the observation date used for [Price] based data such as [MarketCap]."*
- **`reportperiod`** — *"the end date of the fiscal period."*
- **`calendardate`** — *"the normalized [ReportPeriod]"* — two companies with quarters ending 2018-07-24 and 2018-06-28 both map to 2018-06-30 to maximize overlap.
- **`lastupdated`** — *"the last date that this database entry was updated."*

**`datekey` is the "when was this knowable" field — but only for AR dimensions.** For MR dimensions it's set to the *fiscal period end*, typically 30-90 days before the data existed. So joining MR data on `datekey` injects look-ahead **mechanically, independent of the restatement issue**. Two separate traps, same field.

`calendardate` can be *earlier* than `reportperiod`. It's a cross-sectional alignment key, never a time index.

| Field | Right use | Wrong use |
|---|---|---|
| `datekey` | Time index — **AR only, shifted +1 day** | Time-indexing MR |
| `reportperiod` | Accounting alignment | Backtest indexing |
| `calendardate` | Peer comparison within a period | Any time-series indexing |
| `lastupdated` | Incremental sync | Anything analytical |

**The recipe:** use `ART` or `ARQ`, index on `datekey`, **shift +1 day**, forward-fill. The +1 matters because `datekey` is a bare date — a filing accepted at 16:30 ET wasn't tradable at that day's close. This matches QuantRocket's implementation.

---

## 5. TICKERS — the survivorship-free universe

Columns: `table`, `permaticker`, `ticker`, `name`, `exchange`, `isdelisted`, `category`, `cusips`, `siccode`, `sicsector`, `sicindustry`, `famasector`, `famaindustry`, `sector`, `industry`, `scalemarketcap`, `scalerevenue`, `relatedtickers`, `currency`, `location`, `lastupdated`, `firstadded`, `firstpricedate`, `lastpricedate`, `firstquarter`, `lastquarter`, `secfilings`, `companysite`.

- **`table`** — which product table the row belongs to (`SEP`/`SFP`/`SF1`). TICKERS is keyed on `(table, ticker)`, so **the same ticker appears multiple times.** Filter or you get duplicates.
- **`permaticker`** — *"a unique and unchanging identifier for an issuer."* **Join on this, not `ticker`.**
- **`isdelisted`** — `Y`/`N` only, no reason or date. Use `lastpricedate` or ACTIONS.
- **`firstpricedate`** — IPO proxy. Min 1986-01-01, but price history starts Dec 1998.
- **`category`** — flags ADRs and SPACs: `Domestic Common Stock`, `Domestic Common Stock Primary Class`, `Domestic Common Stock Secondary Class`, `Domestic Preferred`, `ADR Common Stock`, `Canadian Common Stock`, `Blank Checks`. ETFs aren't here at all — they're `table='SFP'`.
- **`scalemarketcap`/`scalerevenue`** — buckets 1-6, but based on **maximum observed value over the issuer's entire life.** Not point-in-time. **Filtering on these leaks look-ahead.** Use `DAILY.marketcap` as of date *t*.
- Four independent classification schemes: SIC (`siccode`/`sicsector`/`sicindustry`), Fama-French 48 (`famaindustry`), and Sharadar's own `sector`/`industry` — *"based on SIC codes in a format which approximates to GICS."* GICS-shaped, SIC-derived, **not** licensed GICS. `famasector` is documented as "not currently active."

### Universe recipe

1. Filter `table = 'SEP'`
2. **Do not filter on `isdelisted`** — keeping the `Y` rows is what makes it bias-free
3. Filter `category` to domestic common stock; exclude `Blank Checks` to drop SPACs
4. Dedupe on `permaticker`
5. Point-in-time: include ticker at date *t* only where `firstpricedate <= t <= lastpricedate`
6. Don't condition on `scalemarketcap`/`scalerevenue`

---

## 6. API mechanics

### Python client

| | `Nasdaq-Data-Link` | `quandl` |
|---|---|---|
| Latest | **1.0.4**, Aug 2022 | 3.7.0, Nov 2021 |
| Repo | [Nasdaq/data-link-python](https://github.com/Nasdaq/data-link-python) | **Archived read-only Apr 2022** |
| Verdict | Current but ~4 years without a release | **Dead** |

The client still works (tested on Python 3.11 / pandas 3.x) but **go REST-direct for production**: ~60 lines, drops an unmaintained dependency, and sidesteps the client's hard **1,000,000-row ceiling** — it raises `LimitExceededError` at 101 pages and **returns nothing, not a partial frame**. SEP and SF1 both blow past it.

### REST

```
https://data.nasdaq.com/api/v3/datatables/SHARADAR/{TABLE}.{json|csv}?{filters}&api_key=KEY
```

- Operators: `col=v` (equals), `.gt` `.lt` `.gte` `.lte`. Comma-separated values = IN-list. `.gte`/`.lte` inclusive, `.gt`/`.lt` exclusive.
- `qopts.columns=` projects columns — big win on SF1's 111 fields
- **Auth: prefer the `x-api-token` header** over `?api_key=` (query strings leak into logs). No Bearer scheme.
- Discover filterable columns: `.../SHARADAR/SF1/metadata.json?api_key=KEY`

### Pagination

**10,000 rows per call, hard.** JSON only (CSV carries no cursor). Read `meta.next_cursor_id`; if non-null, re-issue the same query **plus** `&qopts.cursor_id=<value>`.

Two things that bite: `datatable.data` is a **bare array-of-arrays** (names live in `datatable.columns`), and **results are unsorted** — official docs: *"Data sorting must be done locally."*

### Rate limits

| Tier | 10-min | Daily |
|---|---|---|
| Authenticated free | 2,000 | 50,000 |
| **Premium subscriber** | **5,000** | **720,000** |
| `qopts.export=true` | — | **60 / hour** |
| `/v1/bulkdownloads` | — | 30 / table |

429s return `{"quandl_error": {"code": "QELx04", ...}}` (the Quandl name survives the rebrand). Code letters: `L`=limit, `A`=auth, `P`=forbidden, `S`=invalid, `C`=not found, `M`=server.

### Bulk export

Append `qopts.export=true` to a `.json` call → you get a job descriptor, not data. Poll until fresh, then GET the link.

- **The link is valid for only 30 minutes.** Don't cache it.
- **Status casing differs between sources** — docs say `Fresh`/`Creating`/`Regenerating`, Sharadar's own script checks lowercase `fresh`/`generating`/`regenerating`. **Compare case-insensitively**, treat anything not-fresh as "keep polling."
- **Poll ≥30s.** 60 exports/hour means a tight loop locks you out of the export you're waiting on.
- **Never send your API key to the presigned link** — it can trip signature validation.

### Working adapter

```python
"""Nasdaq Data Link Tables API — cursor pagination + bulk export."""
import os, time
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://data.nasdaq.com/api/v3/datatables"


class NDLError(RuntimeError):
    pass


def _session(api_key):
    s = requests.Session()
    s.headers["x-api-token"] = api_key          # header beats query param
    retry = Retry(total=5, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=frozenset(["GET"]),
                  respect_retry_after_header=True,
                  raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def _check(r):
    if r.status_code >= 300:
        try:
            e = r.json()["quandl_error"]
            raise NDLError(f"HTTP {r.status_code} {e['code']}: {e['message']}")
        except (ValueError, KeyError):
            raise NDLError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r


def _params(filters):
    """ticker='AAPL' | ticker=['AAPL','MSFT'] | date={'gte':'2024-01-01'}"""
    out = {}
    for k, v in filters.items():
        if isinstance(v, dict):
            for op, val in v.items():
                out[f"{k}.{op}"] = val
        elif isinstance(v, (list, tuple, set)):
            out[k] = ",".join(map(str, v))
        else:
            out[k] = v
    return out


def fetch_table(table, session, columns=None, max_pages=None, **filters):
    """Cursor-paginated pull. Raises rather than silently truncating."""
    params = _params(filters)
    if columns:
        params["qopts.columns"] = ",".join(columns)
    frames, cols, cursor, pages = [], None, None, 0
    while True:
        if cursor:
            params["qopts.cursor_id"] = cursor      # resend filters alongside cursor
        payload = _check(session.get(f"{BASE}/{table}.json",
                                     params=params, timeout=120)).json()
        dt = payload["datatable"]
        if cols is None:
            cols = [c["name"] for c in dt["columns"]]
        if dt["data"]:
            frames.append(pd.DataFrame(dt["data"], columns=cols))
        pages += 1
        cursor = payload.get("meta", {}).get("next_cursor_id")
        if not cursor:
            break
        if max_pages and pages >= max_pages:
            raise NDLError(f"stopped at {pages} pages, cursor open -> use export_table()")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols or [])


def export_table(table, dest, session, poll_seconds=30, timeout_seconds=3600, **filters):
    """Bulk export. Polls until fresh, streams the zip. Link expires in 30 min."""
    params = _params(filters)
    params["qopts.export"] = "true"
    deadline, link, status = time.time() + timeout_seconds, None, None
    while time.time() < deadline:
        payload = _check(session.get(f"{BASE}/{table}.json",
                                     params=params, timeout=120)).json()
        info = payload["datatable_bulk_download"]["file"]
        status = str(info["status"]).lower()     # docs say Fresh/Creating, script says fresh/generating
        if status == "fresh":
            link = info["link"]
            break
        time.sleep(poll_seconds)                 # >=30s: export budget is 60/hour
    if not link:
        raise NDLError(f"export not ready in {timeout_seconds}s (last status={status})")
    # presigned link - do NOT attach the api key or session headers
    with requests.get(link, stream=True, timeout=1800) as resp:
        _check(resp)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return dest
```

Usage:

```python
s = _session(os.environ["NASDAQ_DATA_LINK_API_KEY"])

# 1. Seed — bulk export is the only viable path for SEP/SF1
export_table("SHARADAR/SEP", "/data/SEP.zip", s)

# 2. Load without blowing up RAM
import duckdb
duckdb.sql("CREATE TABLE sep AS SELECT * FROM read_csv_auto('zip:///data/SEP.zip!*.csv')")

# 3. Daily delta — overlap by a day, let the upsert absorb it
df = fetch_table("SHARADAR/SF1", s, dimension=["ARQ", "ART"],
                 lastupdated={"gte": "2026-07-25"})
```

---

## 7. Gotchas

1. **Silent truncation at 10,000 rows.** Raw REST returns 10k and a cursor you may never inspect. The official client without `paginate=True` emits a `UserWarning` and returns 10k anyway — invisible in a notebook. **Never let a row count of exactly 10000 pass unexamined.**
2. **The 1M-row wall discards your data.** `paginate=True` raises at ~101 pages and returns *nothing*. Use bulk export.
3. **Sync on `lastupdated`, never on `date`.** Sharadar restates. A row for `calendardate=2023-03-31` can be rewritten months later — `date`/`calendardate` never move, `lastupdated` does. **Syncing on `date` permanently misses every restatement.** Overlap the delta window by a day and UPSERT.
4. **Duplicate rows are structural.** Suggested keys: SF1 `(ticker, dimension, calendardate, datekey)`; SEP `(ticker, date)`; TICKERS `(table, ticker)`; SF2 has no natural key and ships a `rownum` column for exactly this reason.
5. **Ticker changes and recycling.** Join on `permaticker`. Punctuation stripped. Recycled symbols get numeric suffixes. Prior tickers live in `relatedtickers`; changes are in ACTIONS.
6. **`AR*` vs `MR*`, and the `datekey` semantics shift** — two independent look-ahead traps (§4).
7. **Timezone.** All Sharadar date fields are **calendar dates, not timestamps.** Store as `DATE` — a naive timestamp cast plus local-tz conversion shifts every bar by a day.
8. **Dtypes differ by access path.** The official client parses dates to `datetime64[s]`; raw REST hands you strings. Cast explicitly.
9. **A missing or invalid key returns *sample* data, not an error.** A truncated sample looks exactly like a successful small query. **Assert on expected row counts and date ranges in your sync.**
10. **`scalemarketcap`/`scalerevenue` are max-observed-over-lifetime** — filtering on them leaks look-ahead into a universe you thought was clean.
11. **Don't hard-code an update time.** Poll table metadata's `refreshed_at` and/or `max(lastupdated)`. Nasdaq's own caveat: *"just because a table was 'refreshed' does not necessarily mean any new data was added."*

---

## 8. Unverified — check these with your key

1. **Whether a restatement appends a new ARQ row** (same `reportperiod`, later `datekey`) or leaves AR untouched. **Highest-value unknown.** If rows are appended, `groupby('reportperiod').last()` silently reintroduces look-ahead — always take the **earliest `datekey`**. Test against a known 10-K/A filer; check whether `(ticker, dimension, reportperiod)` is unique in ARQ.
2. Whether SEP currently has a `dividends` column (a 2023 response showed 10 columns without one; an older bulk dump had one).
3. The complete `ACTIONS.action` enum. Confirmed present: `split`, `dividend`, `spinoffdividend`. No source confirmed `listing`/`delisting`/`tickerchange`.
4. The 8-K `eventcodes` mapping and the EVENTS multi-value delimiter.
5. Exact column names for SF3 (detail) and SF3B. SF3A's 29 are verified.
6. Exhaustive current `category` list in TICKERS.
7. Whether `SHARADAR/*` is enabled on the newer `/api/v1/bulkdownloads` (parquet, multi-file — strictly better if it works; that page makes zero mention of `qopts.export`).
8. Whether SFP is genuinely inside your SFA entitlement — Nasdaq's help center says yes, the datasheet and QuantRocket imply otherwise.
9. SF1 history start — QuantRocket says 1990, Sharadar's datasheet says 1997.
10. Whether SF1's `%`-unit fields arrive as `0.15` or `15.0`.

**Items 2-6 and 10 are all resolvable in one call** — the `INDICATORS` request in §2.

---

## Key sources

- Sharadar's official bulk script: [www.sharadar.com/meta/bulk_fetch.py](http://www.sharadar.com/meta/bulk_fetch.py)
- API docs: [Usage](https://docs.data.nasdaq.com/docs/in-depth-usage-1) · [Tables](https://docs.data.nasdaq.com/docs/tables-1) · [Parameters](https://docs.data.nasdaq.com/docs/parameters-1) · [Large Table Download](https://docs.data.nasdaq.com/docs/large-table-download) · [Rate Limits](https://docs.data.nasdaq.com/docs/rate-limits-1) · [Error Codes](https://docs.data.nasdaq.com/docs/error-codes)
- Help center: [column definitions / bundle contents](https://help.data.nasdaq.com/article/533-what-are-the-column-definitions-for-the-sharadar-data-feeds) · [eventcodes](https://help.data.nasdaq.com/article/534-what-do-the-eventcodes-mean-in-the-sharadar-data) · [delisted coverage](https://help.data.nasdaq.com/article/508-do-you-cover-delisted-stocks) · [refresh timing](https://help.data.nasdaq.com/article/510-how-often-is-the-data-on-nasdaq-data-link-refreshed-or-updated)
- Status: [status.data.nasdaq.com](https://status.data.nasdaq.com/)
- SF1 indicator dictionary (verbatim mirror, 111 fields): [alphaville76/sharadar_db_bundle](https://github.com/alphaville76/sharadar_db_bundle/blob/master/doc/fundamentals.htm)
- Field literals for SF1/SF2/SF3A: [quantrocket-client/fundamental.py](https://github.com/quantrocket-llc/quantrocket-client/blob/master/quantrocket/fundamental.py)
- Licensing: [QuantRocket Sharadar pricing](https://www.quantrocket.com/pricing/data/sharadar/)
- Clients: [PyPI Nasdaq-Data-Link](https://pypi.org/project/Nasdaq-Data-Link/) · [Nasdaq/data-link-python](https://github.com/Nasdaq/data-link-python)
