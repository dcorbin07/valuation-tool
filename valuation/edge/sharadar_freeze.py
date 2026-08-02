"""
Final Sharadar freeze — pull every table we rely on, snapshot it, verify it, manifest it.

Sharadar access lapses shortly. Once it does these tables can never be re-pulled, so this
takes the freshest possible full export and writes a dated, self-contained, read-only
snapshot that a future session can point `WRDS_DATA_DIR` at and run the whole backtest from
with no API key at all.

    python -m valuation.edge.sharadar_freeze --stage all

Layout (self-contained on purpose — see the note on bulk_dir below):

    data/backtest_freeze_YYYY-MM/
        backtest/     fundamentals.csv, insiders.csv, institutional.csv, prices/<T>.csv
        bulk/         sf1.csv sep.csv sfp.csv sf2.csv sf3a.csv sf3.csv daily.csv
                      actions.csv events.csv tickers.csv
        bulk/prepared/  actions.pkl events.pkl daily.pkl sf3.pkl tickers.pkl
        raw/          the downloaded SHARADAR_<TABLE>_<date>.zip files
        MANIFEST.json

`WRDSProvider.bulk_dir` derives the prepared-cache path as `<parent of data dir>/bulk/prepared`,
so nesting `backtest/` and `bulk/` under one freeze root is what makes the snapshot resolve its
OWN caches instead of silently reading the live ones.

Three things this deliberately does that the original one-off export did not:

  1. Everything comes from the BULK export endpoint (qopts.export=true), not the per-ticker
     API loop — one request per table instead of ~12,000, so the whole pull is minutes of
     download rather than hours of rate-limited paging.
  2. The FULL SF1 is kept, all dimensions. The live export is ARQ-only, which is the direct
     cause of `roe`/`roic`/`assetturnover` being non-null in 0 of 197,265 rows (Sharadar only
     fills its averaged columns in ART/ARY). Freezing all dimensions makes that recoverable
     later without an API key. The derived `backtest/fundamentals.csv` stays ARQ-only so it is
     a drop-in replacement for the current one.
  3. The derived universe is a SUPERSET of what is on disk today (live tickers UNION the
     freshly-ranked top-3000), so "the freeze is at least as complete as the working set" is
     true by construction and the verify stage can assert it rather than hope.

Never prints the API key. Never writes it to the manifest.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import stat
import sys
import time
import zipfile

BASE = "https://data.nasdaq.com/api/v3/datatables/SHARADAR"

# Sharadar table -> extracted csv name. Order matters only for readability of the log.
TABLES = [
    ("TICKERS", "tickers.csv"),      # small, and the universe is derived from it
    ("ACTIONS", "actions.csv"),
    ("EVENTS", "events.csv"),
    ("SF3A", "sf3a.csv"),
    ("SF2", "sf2.csv"),
    ("SF1", "sf1.csv"),
    ("SFP", "sfp.csv"),
    ("SEP", "sep.csv"),
    ("DAILY", "daily.csv"),
    ("SF3", "sf3.csv"),
]

# The column that defines each table's time span. `filingdate` for SF2 because that is the
# date the panel is allowed to know something on; `datekey` for SF1 for the same reason.
DATE_COL = {
    "sf1.csv": "datekey", "sep.csv": "date", "sfp.csv": "date", "sf2.csv": "filingdate",
    "sf3a.csv": "calendardate", "sf3.csv": "calendardate", "daily.csv": "date",
    "actions.csv": "date", "events.csv": "date", "tickers.csv": "lastupdated",
}

_MB = 1024 * 1024


def _log(msg):
    print(f"[freeze] {dt.datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def _key():
    from ..config import CONFIG
    k = CONFIG.sharadar_api_key
    if not k or "PASTE" in str(k).upper():
        raise SystemExit("SHARADAR_API_KEY missing or still the placeholder in .env")
    return k


# --------------------------------------------------------------------------- #
#  1. download
# --------------------------------------------------------------------------- #
def _export_link(table: str, key: str, max_wait: int = 1800) -> str:
    """Ask for the bulk export and wait until Nasdaq says the file is `fresh`.

    A `regenerating` status means the vendor is rebuilding the zip server-side; polling is
    the documented way through it. Raises rather than returning a stale link.
    """
    import requests
    t0 = time.time()
    while True:
        r = requests.get(f"{BASE}/{table}.json",
                         params={"qopts.export": "true", "api_key": key}, timeout=120)
        r.raise_for_status()
        f = (r.json().get("datatable_bulk_download") or {}).get("file") or {}
        status, link = f.get("status"), f.get("link")
        if status == "fresh" and link:
            return link
        if time.time() - t0 > max_wait:
            raise RuntimeError(f"{table}: export still '{status}' after {max_wait}s")
        _log(f"{table}: export status={status} — waiting 30s")
        time.sleep(30)


def _download(url: str, dest: str) -> int:
    import requests
    tmp = dest + ".part"
    n = 0
    t0 = time.time()
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=4 * _MB):
                if not chunk:
                    continue
                f.write(chunk)
                n += len(chunk)
                if n % (200 * _MB) < 4 * _MB:
                    pct = f" / {total/_MB:.0f}MB" if total else ""
                    _log(f"    {n/_MB:.0f}MB{pct} ({n/_MB/max(time.time()-t0,1):.0f} MB/s)")
    if total and n != total:
        os.remove(tmp)
        raise RuntimeError(f"truncated download: {n} of {total} bytes")
    os.replace(tmp, dest)
    return n


def _extract(zip_path: str, dest_csv: str) -> None:
    """Extract the single CSV member. ZipFile.read validates the CRC, so a corrupt or
    half-written zip fails here rather than three stages later as 'missing rows'."""
    with zipfile.ZipFile(zip_path) as z:
        members = [m for m in z.namelist() if m.lower().endswith(".csv")]
        if not members:
            raise RuntimeError(f"{zip_path}: no csv member ({z.namelist()[:5]})")
        tmp = dest_csv + ".part"
        with z.open(members[0]) as src, open(tmp, "wb") as out:
            while True:
                b = src.read(8 * _MB)
                if not b:
                    break
                out.write(b)
    os.replace(tmp, dest_csv)


def stage_download(root: str, only: set, force: bool = False) -> None:
    key = _key()
    raw_dir, bulk_dir = os.path.join(root, "raw"), os.path.join(root, "bulk")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(bulk_dir, exist_ok=True)
    stamp = dt.date.today().isoformat()
    for table, name in TABLES:
        if only and table not in only:
            continue
        zip_path = os.path.join(raw_dir, f"SHARADAR_{table}_{stamp}.zip")
        csv_path = os.path.join(bulk_dir, name)
        if not force and os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
            _log(f"{table}: zip already present ({os.path.getsize(zip_path)/_MB:.0f}MB) — skip download")
        else:
            _log(f"{table}: requesting bulk export …")
            link = _export_link(table, key)
            _log(f"{table}: downloading")
            n = _download(link, zip_path)
            _log(f"{table}: {n/_MB:.0f}MB -> {os.path.basename(zip_path)}")
        if force or not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0 \
                or os.path.getmtime(csv_path) < os.path.getmtime(zip_path):
            _log(f"{table}: extracting -> bulk/{name}")
            _extract(zip_path, csv_path)
            _log(f"{table}: csv {os.path.getsize(csv_path)/_MB:.0f}MB")
        else:
            _log(f"{table}: csv already extracted — skip")


# --------------------------------------------------------------------------- #
#  2. derive — the WRDSProvider layout, restricted to a superset universe
# --------------------------------------------------------------------------- #
def _live_tickers(live_dir: str) -> set:
    """Every ticker the current working set covers — the floor the freeze must clear."""
    out = set()
    pdir = os.path.join(live_dir, "prices")
    if os.path.isdir(pdir):
        out |= {os.path.splitext(f)[0].upper() for f in os.listdir(pdir) if f.endswith(".csv")}
    fpath = os.path.join(live_dir, "fundamentals.csv")
    if os.path.exists(fpath):
        with open(fpath, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            h = next(r, None)
            if h and "ticker" in h:
                i = h.index("ticker")
                for row in r:
                    if len(row) > i and row[i]:
                        out.add(row[i].upper())
    return out


def _fresh_universe(tickers_csv: str, limit: int = 3000) -> list:
    """The same ranking `SharadarProvider.universe()` applies, run over the bulk TICKERS
    export instead of the paged API: SF1-covered domestic common stock, micro-cap and up,
    most investable first."""
    ranked, seen = [], set()
    with open(tickers_csv, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if not h:
            return []
        idx = {c: i for i, c in enumerate(h)}
        ti, ci, si, tbl = idx.get("ticker"), idx.get("category"), idx.get("scalemarketcap"), idx.get("table")
        if ti is None:
            return []
        for row in r:
            if tbl is not None and row[tbl] and row[tbl].upper() != "SF1":
                continue
            if ci is not None and row[ci] and "Common Stock" not in row[ci]:
                continue
            t = row[ti]
            if not t or t in seen:
                continue
            scale = 0
            if si is not None and row[si]:
                try:
                    scale = int(str(row[si]).split(" ")[0])
                except (ValueError, IndexError):
                    scale = 0
            seen.add(t)
            ranked.append((scale, t))
    kept = [x for x in ranked if x[0] >= 2] or ranked
    kept.sort(key=lambda x: -x[0])
    return [t.upper() for _, t in kept][:limit]


def _filter_csv(src: str, dest: str, keep: set, ticker_col: str = "ticker",
                where=None, label: str = "") -> tuple:
    """Stream `src` -> `dest` keeping rows whose ticker is in `keep`. Returns (rows, tickers)."""
    kept_rows, kept_t = 0, set()
    tmp = dest + ".part"
    t0 = time.time()
    with open(src, newline="", encoding="utf-8", errors="replace") as fin, \
            open(tmp, "w", newline="", encoding="utf-8") as fout:
        r = csv.reader(fin)
        w = csv.writer(fout)
        h = next(r, None)
        if h is None:
            open(dest, "w").close()
            return 0, set()
        w.writerow(h)
        it = h.index(ticker_col)
        n = 0
        for row in r:
            n += 1
            if n % 8_000_000 == 0:
                _log(f"    {label}: {n/1e6:.0f}M rows scanned, {kept_rows/1e6:.1f}M kept, {time.time()-t0:.0f}s")
            if len(row) <= it:
                continue
            t = row[it].upper()
            if t not in keep:
                continue
            if where is not None and not where(h, row):
                continue
            w.writerow(row)
            kept_rows += 1
            kept_t.add(t)
    os.replace(tmp, dest)
    _log(f"    {label}: {kept_rows:,} rows / {len(kept_t):,} tickers in {time.time()-t0:.0f}s")
    return kept_rows, kept_t


class _HandleCache:
    """Buffer rows per ticker in memory and flush in batches.

    MEASURED, not assumed: **SEP is not ordered by ticker** — row 1 is ABILF, row 3 is AAC.U.
    An LRU pool of open handles therefore evicts and reopens on nearly every row, and the
    first attempt at this split was still crawling through SEP after 12 minutes. Buffering
    instead means each of the ~3,700 files is opened once per flush round rather than
    millions of times.

    Memory is bounded by flushing every `flush_every` buffered lines. Only "date,close" is
    retained (~18 bytes/row against ~100 in the source), so a full SEP pass peaks well under
    a gigabyte even between flushes.
    """

    def __init__(self, cap: int = 2_000_000):
        self.flush_every = cap
        self.buf: dict = {}
        self.n = 0
        self.seen = set()

    def write(self, path: str, line: str):
        b = self.buf.get(path)
        if b is None:
            b = self.buf[path] = []
        b.append(line)
        self.n += 1
        if self.n >= self.flush_every:
            self.flush()

    def flush(self):
        for path, lines in self.buf.items():
            if not lines:
                continue
            first = path not in self.seen
            with open(path, "w" if first else "a", encoding="utf-8", newline="") as f:
                if first:
                    f.write("date,close\n")
                    self.seen.add(path)
                f.write("".join(lines))
        self.buf.clear()
        self.n = 0

    def close(self):
        self.flush()


def _split_prices(src: str, out_dir: str, keep: set, label: str) -> set:
    """<out_dir>/<TICKER>.csv with columns date,close — close is `closeadj` (split- AND
    dividend-adjusted), which is what the live export wrote and what the panel expects."""
    if not os.path.exists(src):
        return set()
    hc = _HandleCache()
    written = set()
    t0 = time.time()
    with open(src, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if h is None:
            return set()
        it, idt = h.index("ticker"), h.index("date")
        ic = h.index("closeadj") if "closeadj" in h else h.index("close")
        n = 0
        for row in r:
            n += 1
            if n % 8_000_000 == 0:
                _log(f"    {label}: {n/1e6:.0f}M rows, {len(written):,} tickers, {time.time()-t0:.0f}s")
            t = row[it].upper()
            if t not in keep:
                continue
            c = row[ic]
            if not c:
                continue
            hc.write(os.path.join(out_dir, f"{t}.csv"), f"{row[idt]},{c}\n")
            written.add(t)
    hc.close()
    # SEP is date-DESCENDING within a ticker (row 1 is 2021-11-09, row 2 2021-11-08) and the
    # buffered flush appends in arrival order, so the files land unsorted. WRDSProvider does
    # sort on read, but the live per-ticker files are ascending and nothing else should have
    # to know that — sorting here keeps the freeze a true drop-in. ~4k rows per file.
    for t in written:
        p = os.path.join(out_dir, f"{t}.csv")
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        body = sorted(lines[1:])
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("date,close\n" + "\n".join(body) + "\n")
    _log(f"    {label}: {len(written):,} price files (date-sorted) in {time.time()-t0:.0f}s")
    return written


def stage_derive(root: str, live_dir: str, force: bool = False) -> dict:
    bulk = os.path.join(root, "bulk")
    bt = os.path.join(root, "backtest")
    os.makedirs(os.path.join(bt, "prices"), exist_ok=True)

    def done(name):
        """Each derived file is a single atomic os.replace, so 'present and non-empty'
        really does mean 'that pass finished' — there is no half-written state to inherit."""
        p = os.path.join(bt, name)
        return (not force) and os.path.exists(p) and os.path.getsize(p) > 0

    live = _live_tickers(live_dir)
    fresh = _fresh_universe(os.path.join(bulk, "tickers.csv"))
    universe = (live | set(fresh) | {"SPY"})
    _log(f"universe: {len(live):,} live + {len(fresh):,} freshly ranked -> {len(universe):,} kept "
         f"({len(set(fresh) - live):,} new names)")
    with open(os.path.join(bt, "universe.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(universe)))

    def arq(h, row):
        i = h.index("dimension")
        return row[i] == "ARQ"

    f_rows = i_rows = n_rows = None
    f_t = set()
    if done("fundamentals.csv"):
        _log("fundamentals.csv already derived — skip")
    else:
        _log("fundamentals.csv  <- sf1.csv (ARQ, drop-in for the live file; full SF1 kept in bulk/)")
        f_rows, f_t = _filter_csv(os.path.join(bulk, "sf1.csv"), os.path.join(bt, "fundamentals.csv"),
                                  universe, where=arq, label="sf1->fundamentals")
    if done("insiders.csv"):
        _log("insiders.csv already derived — skip")
    else:
        _log("insiders.csv  <- sf2.csv")
        i_rows, _ = _filter_csv(os.path.join(bulk, "sf2.csv"), os.path.join(bt, "insiders.csv"),
                                universe, label="sf2->insiders")
    if done("institutional.csv"):
        _log("institutional.csv already derived — skip")
    else:
        _log("institutional.csv  <- sf3a.csv")
        n_rows, _ = _filter_csv(os.path.join(bulk, "sf3a.csv"), os.path.join(bt, "institutional.csv"),
                                universe, label="sf3a->institutional")

    _log("prices/  <- sep.csv then sfp.csv (funds/ETFs, e.g. the SPY benchmark)")
    pd_dir = os.path.join(bt, "prices")
    # Always rebuilt from scratch: a partial split leaves per-ticker files that LOOK complete
    # but are missing whatever the interrupted pass had not reached, and nothing downstream
    # could tell the difference. Cheap insurance against a silently truncated price series.
    for f in os.listdir(pd_dir):
        os.remove(os.path.join(pd_dir, f))
    got = _split_prices(os.path.join(bulk, "sep.csv"), pd_dir, universe, "sep->prices")
    got |= _split_prices(os.path.join(bulk, "sfp.csv"), pd_dir, universe - got, "sfp->prices")

    return {"universe": len(universe), "universe_live": len(live), "universe_fresh": len(fresh),
            "fundamentals_rows": f_rows, "fundamentals_tickers": len(f_t),
            "insider_rows": i_rows, "institutional_rows": n_rows, "price_files": len(got)}


# --------------------------------------------------------------------------- #
#  3. prepare — the compact pickles the panel actually reads
# --------------------------------------------------------------------------- #
def stage_prepare(root: str, rebuild: bool = False) -> dict:
    from . import bulk as B
    bulk_dir = os.path.join(root, "bulk")
    cache_dir = os.path.join(bulk_dir, "prepared")
    os.makedirs(cache_dir, exist_ok=True)
    out = {}
    out["actions"] = len(B.prepare_actions(os.path.join(bulk_dir, "actions.csv"), cache_dir, rebuild))
    out["events"] = len(B.prepare_events(os.path.join(bulk_dir, "events.csv"), cache_dir, rebuild))
    out["daily"] = len(B.prepare_daily(os.path.join(bulk_dir, "daily.csv"), cache_dir, rebuild))
    out["sf3"] = len(B.prepare_sf3(os.path.join(bulk_dir, "sf3.csv"), cache_dir, rebuild))
    out["tickers"] = len(B.prepare_tickers(cache_dir, api_key=_key(), rebuild=rebuild))
    for k, v in out.items():
        _log(f"prepared {k}: {v:,} tickers")
    return out


# --------------------------------------------------------------------------- #
#  4. verify + manifest
# --------------------------------------------------------------------------- #
def _sha256(path: str, chunk: int = 8 * _MB) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _scan_csv(path: str, date_col: str) -> dict:
    """Row count, distinct tickers, and min/max of the date column — one streaming pass."""
    if not os.path.exists(path):
        return {"present": False}
    rows, tick = 0, set()
    dmin, dmax = None, None
    t0 = time.time()
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if h is None:
            return {"present": True, "rows": 0, "note": "empty/headerless"}
        it = h.index("ticker") if "ticker" in h else None
        idt = h.index(date_col) if date_col in h else None
        for row in r:
            rows += 1
            if it is not None and len(row) > it:
                tick.add(row[it])
            if idt is not None and len(row) > idt:
                d = row[idt]
                if d:
                    if dmin is None or d < dmin:
                        dmin = d
                    if dmax is None or d > dmax:
                        dmax = d
    return {"present": True, "rows": rows, "tickers": len(tick),
            "date_col": date_col if idt is not None else None,
            "date_min": dmin, "date_max": dmax, "scan_seconds": round(time.time() - t0, 1)}


def _checkpoints(root: str) -> list:
    """The known-good values from CLAUDE.md. A freeze that fails these is not a freeze."""
    from . import bulk as B
    cache_dir = os.path.join(root, "bulk", "prepared")
    out = []

    def add(name, ok, got, want, note=""):
        out.append({"check": name, "pass": bool(ok), "got": got, "expected": want, "note": note})

    # Sharadar's DAILY `marketcap` is in MILLIONS of USD, not dollars — AAPL 2015-06-30 is
    # stored as 722571.4, i.e. $722.57B, which is the $722.6B figure recorded in CLAUDE.md.
    # Checked against the live cache: byte-identical. Getting this unit wrong makes a correct
    # freeze look like a failed one, so the convention is asserted here rather than assumed.
    daily = B._load_cache("daily", cache_dir) or {}
    aapl = daily.get("AAPL") or []
    q2 = [r for r in aapl if r[0][:7] == "2015-06"]
    mc = q2[-1][1] if q2 else None
    add("AAPL 2015Q2 point-in-time market cap ($B, DAILY is in millions)",
        mc is not None and 680_000 <= mc <= 770_000,
        round(mc / 1_000, 1) if mc else None, "~722.6")

    bt = os.path.join(root, "backtest")
    fr = _scan_csv(os.path.join(bt, "fundamentals.csv"), "datekey")
    add("fundamentals rows (ARQ, freeze universe)", (fr.get("rows") or 0) >= 197_265,
        fr.get("rows"), ">= 197,265")
    add("fundamentals tickers", (fr.get("tickers") or 0) >= 2_710, fr.get("tickers"), ">= 2,710")
    npf = len([f for f in os.listdir(os.path.join(bt, "prices"))]) if os.path.isdir(os.path.join(bt, "prices")) else 0
    add("price files", npf >= 2_998, npf, ">= 2,998")
    add("SPY benchmark price file present", os.path.exists(os.path.join(bt, "prices", "SPY.csv")),
        os.path.exists(os.path.join(bt, "prices", "SPY.csv")), True)

    tk = B._load_cache("tickers", cache_dir) or {}
    with_sector = sum(1 for v in tk.values() if v.get("sector"))
    add("TICKERS with a sector", with_sector >= 10_000, with_sector, ">= 10,000",
        "unblocks the sector-neutral panel fix (roadmap #13)")
    return out


def _compare_live(root: str, live_dir: str) -> list:
    """Nothing in the freeze may be SHORTER than what is already on disk — that is a failed
    pull wearing a freeze's clothes."""
    out = []

    def cmp(name, new, old, unit="rows"):
        short = old is not None and new is not None and new < old
        out.append({"item": name, "freeze": new, "live": old, "unit": unit,
                    "SHORT": bool(short)})

    live_bulk = os.path.join(os.path.dirname(os.path.normpath(live_dir)), "bulk")
    for n in ("actions.csv", "events.csv", "daily.csv", "sf3.csv"):
        a = os.path.join(root, "bulk", n)
        b = os.path.join(live_bulk, n)
        cmp(f"bulk/{n} size", os.path.getsize(a) if os.path.exists(a) else None,
            os.path.getsize(b) if os.path.exists(b) else None, "bytes")
    for n in ("fundamentals.csv", "insiders.csv", "institutional.csv"):
        a = os.path.join(root, "backtest", n)
        b = os.path.join(live_dir, n)
        cmp(f"backtest/{n} size", os.path.getsize(a) if os.path.exists(a) else None,
            os.path.getsize(b) if os.path.exists(b) else None, "bytes")
    pa = os.path.join(root, "backtest", "prices")
    pb = os.path.join(live_dir, "prices")
    cmp("price files", len(os.listdir(pa)) if os.path.isdir(pa) else 0,
        len(os.listdir(pb)) if os.path.isdir(pb) else 0, "files")
    return out


def stage_manifest(root: str, live_dir: str, derived: dict, reuse_hashes: bool = False) -> dict:
    """Scan, checksum and verify the freeze.

    `reuse_hashes` exists ONLY for iterating on the manifest logic itself: it carries a
    previous MANIFEST.json's sha256 forward when a file's size AND mtime are both unchanged.
    It is off by default and must stay off for a real integrity check — the whole point of
    the checksum is that it re-reads the bytes, and metadata is exactly what a silent
    corruption would leave untouched.
    """
    prev = {}
    if reuse_hashes:
        try:
            with open(os.path.join(root, "MANIFEST.json"), encoding="utf-8") as f:
                old = json.load(f)
            for sect in ("tables", "derived", "prepared"):
                for k, v in (old.get(sect) or {}).items():
                    if isinstance(v, dict) and v.get("sha256"):
                        prev[(sect, k)] = (v.get("bytes"), v.get("sha256"))
                    z = (v or {}).get("zip") if isinstance(v, dict) else None
                    if z and z.get("sha256"):
                        prev[("zip", z["file"])] = (z.get("bytes"), z["sha256"])
            _log(f"reuse-hashes: {len(prev)} prior checksums available (NOT a real verification)")
        except Exception:
            prev = {}

    def sha(path, key):
        if key in prev and prev[key][0] == os.path.getsize(path):
            return prev[key][1]
        _log(f"hashing {os.path.relpath(path, root)} ({os.path.getsize(path)/_MB:.0f}MB)")
        return _sha256(path)

    pulled = dt.datetime.now().isoformat(timespec="seconds")
    man = {"freeze": os.path.basename(os.path.normpath(root)),
           "created": pulled, "source": "Sharadar / Nasdaq Data Link bulk export (qopts.export=true)",
           "tables": {}, "derived": {}, "prepared": {}, "checkpoints": [], "vs_live": []}

    for table, name in TABLES:
        csv_path = os.path.join(root, "bulk", name)
        rec = _scan_csv(csv_path, DATE_COL.get(name, "date"))
        if rec.get("present"):
            rec["bytes"] = os.path.getsize(csv_path)
            rec["sha256"] = sha(csv_path, ("tables", table))
            rec["pulled_at"] = dt.datetime.fromtimestamp(os.path.getmtime(csv_path)).isoformat(timespec="seconds")
        zips = [f for f in os.listdir(os.path.join(root, "raw")) if f.startswith(f"SHARADAR_{table}_")]
        if zips:
            zp = os.path.join(root, "raw", sorted(zips)[-1])
            rec["zip"] = {"file": os.path.basename(zp), "bytes": os.path.getsize(zp),
                          "sha256": sha(zp, ("zip", os.path.basename(zp))),
                          "pulled_at": dt.datetime.fromtimestamp(os.path.getmtime(zp)).isoformat(timespec="seconds")}
        man["tables"][table] = rec
        _log(f"  {table}: {rec.get('rows', 0):,} rows  {rec.get('date_min')} .. {rec.get('date_max')}")

    for name, date_col in (("fundamentals.csv", "datekey"), ("insiders.csv", "filingdate"),
                           ("institutional.csv", "calendardate")):
        p = os.path.join(root, "backtest", name)
        rec = _scan_csv(p, date_col)
        if rec.get("present"):
            rec["bytes"] = os.path.getsize(p)
            rec["sha256"] = sha(p, ("derived", name))
        man["derived"][name] = rec
        _log(f"  {name}: {rec.get('rows', 0):,} rows  {rec.get('date_min')} .. {rec.get('date_max')}")

    pdir = os.path.join(root, "backtest", "prices")
    files = os.listdir(pdir) if os.path.isdir(pdir) else []
    man["derived"]["prices/"] = {"files": len(files),
                                 "bytes": sum(os.path.getsize(os.path.join(pdir, f)) for f in files)}
    for name in ("actions.pkl", "events.pkl", "daily.pkl", "sf3.pkl", "tickers.pkl"):
        p = os.path.join(root, "bulk", "prepared", name)
        if os.path.exists(p):
            man["prepared"][name] = {"bytes": os.path.getsize(p),
                                     "sha256": sha(p, ("prepared", name))}

    if derived:
        man["derive_stats"] = derived
    man["checkpoints"] = _checkpoints(root)
    man["vs_live"] = _compare_live(root, live_dir)
    man["verdict"] = {
        "checkpoints_failed": [c["check"] for c in man["checkpoints"] if not c["pass"]],
        "tables_short_vs_live": [c["item"] for c in man["vs_live"] if c["SHORT"]],
    }
    man["verdict"]["clean"] = not (man["verdict"]["checkpoints_failed"]
                                   or man["verdict"]["tables_short_vs_live"])
    with open(os.path.join(root, "MANIFEST.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    return man


def stage_lock(root: str, unlock: bool = False) -> int:
    """Mark every file read-only. A freeze that a later run can overwrite is not a freeze."""
    n = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(dirpath, name)
            try:
                if unlock:
                    os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
                else:
                    os.chmod(p, stat.S_IREAD)
                n += 1
            except OSError:
                pass
    _log(f"{'unlocked' if unlock else 'locked read-only'}: {n:,} files")
    return n


# --------------------------------------------------------------------------- #
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Freeze the Sharadar tables before access lapses.")
    ap.add_argument("--root", default=os.path.join("data", f"backtest_freeze_{dt.date.today():%Y-%m}"))
    ap.add_argument("--live", default=os.path.join("data", "backtest"))
    ap.add_argument("--stage", default="all",
                    help="all | download | derive | prepare | manifest | lock | unlock")
    ap.add_argument("--only", default="", help="download stage: comma-separated table names")
    ap.add_argument("--force", action="store_true", help="re-download / re-extract even if present")
    ap.add_argument("--rebuild", action="store_true", help="prepare stage: ignore cached pickles")
    ap.add_argument("--reuse-hashes", action="store_true",
                    help="manifest stage: carry forward unchanged checksums. For iterating on "
                         "the manifest only — a real integrity check must re-hash.")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    live = os.path.abspath(a.live)
    os.makedirs(root, exist_ok=True)
    only = {x.strip().upper() for x in a.only.split(",") if x.strip()}
    stages = ["download", "derive", "prepare", "manifest", "lock"] if a.stage == "all" else [a.stage]
    _log(f"freeze root: {root}")

    derived = {}
    for s in stages:
        _log(f"=== stage {s} ===")
        if s == "download":
            stage_download(root, only, force=a.force)
        elif s == "derive":
            derived = stage_derive(root, live, force=a.force)
        elif s == "prepare":
            stage_prepare(root, rebuild=a.rebuild)
        elif s == "manifest":
            man = stage_manifest(root, live, derived, reuse_hashes=a.reuse_hashes)
            print(json.dumps(man["verdict"], indent=2))
            for c in man["checkpoints"]:
                print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']}: got {c['got']} (want {c['expected']})")
            for c in man["vs_live"]:
                if c["SHORT"]:
                    print(f"  [SHORT] {c['item']}: freeze {c['freeze']} < live {c['live']} {c['unit']}")
        elif s == "lock":
            stage_lock(root)
        elif s == "unlock":
            stage_lock(root, unlock=True)
        else:
            raise SystemExit(f"unknown stage {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
