"""
Derive greeks / GEX / IV-surface features for every FULLY-MINED name in the options cache.

    python greeks_enrich.py                       # resume: enrich whatever is ready
    python greeks_enrich.py --dry-run             # list what it would do, touch nothing
    python greeks_enrich.py --symbols AAPL,MSFT   # one or two names
    python greeks_enrich.py --workers 1           # quietest possible

RUNS ALONGSIDE THE MINER, WHICH IS THE ENTIRE DESIGN CONSTRAINT.

  * ZERO vendor option calls. Everything here is arithmetic on files already on disk, so it
    cannot compete with the miner for API budget. (The underlying close comes from the existing
    Sharadar bars cache; if a name is missing it is fetched ONCE, in the parent, before any
    worker starts — see `prefetch_spots`.)
  * READ-ONLY on `data/options/`. Nothing is written, renamed or deleted under the miner's
    cache. All output goes to `data/options_derived/`, a separate root, so there is no way to
    collide with the miner's atomic writes or confuse its skip-existing check.
  * A name is only touched when the manifest calls it `complete`, it is not one of the last few
    names in the miner's progress log, and none of its files have been written in the last
    `--min-age-min` minutes. When in doubt it is SKIPPED — the next pass will pick it up.
  * CPU-polite: BLAS threads are pinned to one per worker and the default worker count is 2,
    because four other agents are on this machine.

Resumable: a name whose `coverage.json` matches the current source files and schema version is
skipped. Re-mine a name and its signature changes, so it is re-derived automatically.
"""
from __future__ import annotations

import os

# Pin BLAS BEFORE numpy is imported anywhere. Each worker is single-threaded on purpose; the
# work is already parallel across names and thread-oversubscription would just starve the miner.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse                                                          # noqa: E402
import json                                                              # noqa: E402
import re                                                                # noqa: E402
import sys                                                               # noqa: E402
import time                                                              # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed         # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge import options_greeks as G                           # noqa: E402

DEFAULT_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MINER_ACTIVE_TAIL = 3           # exclude the last N names in the miner's log, not just one
MIN_AGE_MIN = 10.0              # a file written more recently than this is still settling


def _log(m):
    print(f"[greeks] {m}", flush=True)


# ============================== eligibility (the non-interference gate) =====================
def read_manifest(options_root: str) -> dict:
    """The miner's completed-name set. Schema is VERIFIED, not assumed: it is another agent's
    file and a silent shape change here would mean enriching half-mined names."""
    p = os.path.join(options_root, "cache_manifest.json")
    if not os.path.exists(p):
        raise SystemExit(f"no cache manifest at {p} — is the miner running?")
    with open(p, encoding="utf-8") as f:
        man = json.load(f)
    if not isinstance(man, dict) or not man:
        raise SystemExit(f"cache manifest is {type(man).__name__}, expected a non-empty dict")
    bad = [k for k, v in man.items() if not isinstance(v, dict) or "status" not in v]
    if bad:
        raise SystemExit(f"cache manifest entries lack a 'status' field: {bad[:5]}")
    return man


def miner_active_names(options_root: str, tail: int = MINER_ACTIVE_TAIL) -> list:
    """Names from the last few progress lines. The log records names as they FINISH, so the
    miner's current target is the one after the last line — excluding a small tail is the cheap
    way to stay clear of it without having to guess."""
    p = os.path.join(options_root, "MINING_PROGRESS.txt")
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8", errors="ignore") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
    except OSError:
        return []
    out = []
    for ln in lines[-tail:]:
        m = re.search(r"\]\s*([A-Z][A-Z0-9.\-]{0,9}):", ln)
        if m:
            out.append(m.group(1))
    return out


def newest_touch_min(sym: str, options_root: str) -> float:
    """Minutes since the most recent write to any of this name's cache files."""
    d = os.path.join(options_root, sym)
    newest = 0.0
    try:
        for f in os.listdir(d):
            if f.endswith(".pkl"):
                newest = max(newest, os.path.getmtime(os.path.join(d, f)))
    except OSError:
        return 0.0
    if not newest:
        return 1e9
    return (time.time() - newest) / 60.0


def eligible(options_root: str, out_root: str, min_age_min: float,
             only=None, force: bool = False):
    """(to_do, skipped) — every exclusion is reported, never silent."""
    man = read_manifest(options_root)
    active = set(miner_active_names(options_root))
    todo, skipped = [], {}
    for sym in sorted(man):
        if only and sym not in only:
            continue
        rec = man[sym]
        if rec.get("status") != "complete":
            skipped[sym] = f"manifest status {rec.get('status')!r}"
            continue
        if not os.path.isdir(os.path.join(options_root, sym)):
            skipped[sym] = "no cache directory"
            continue
        if sym in active:
            skipped[sym] = "at/near the miner's cursor"
            continue
        age = newest_touch_min(sym, options_root)
        if age < min_age_min:
            skipped[sym] = f"written {age:.1f}m ago (still settling)"
            continue
        if not force and G.already_enriched(sym, options_root, out_root):
            skipped[sym] = "already enriched"
            continue
        todo.append(sym)
    return todo, skipped


# ============================== underlying spot ============================================
def bars_cache_dir(data_root: str) -> str:
    return os.path.join(data_root, "bulk", "prepared", "bars")


def load_spots(sym: str, data_root: str, allow_fetch: bool = False) -> dict:
    """{date -> AS-TRADED close} for the underlying.

    `raw_close` (Sharadar `closeunadj`), never the adjusted close: option STRIKES are as-traded
    and are never retro-adjusted, so comparing a split-adjusted price against a 2019 strike
    ladder silently puts every contract in the wrong moneyness bucket. options_backtest.py
    documents that failure at length; this is the same trap and the same fix.
    """
    import datetime as dt

    from valuation.edge import options_backtest as OB

    cache = bars_cache_dir(data_root)
    if not allow_fetch and not os.path.exists(os.path.join(cache, f"{sym.upper()}.pkl")):
        return {}
    bars = OB.load_bars(sym, cache_dir=cache)
    if not bars or "raw_close" not in bars:
        return {}
    out = {}
    for ds, px in zip(bars["date"], bars["raw_close"]):
        try:
            out[dt.date.fromisoformat(str(ds)[:10])] = float(px)
        except (ValueError, TypeError):
            continue
    return out


def ensure_sharadar_key(data_root: str) -> bool:
    """Make SHARADAR_API_KEY available for the bars fetch, without printing it.

    `valuation.config` loads `.env` from the CURRENT directory, which is wrong when this runs
    from a worktree against the main checkout's data. Only the one key is taken, and only when
    it is not already set.
    """
    if os.environ.get("SHARADAR_API_KEY"):
        return True
    repo = os.path.dirname(os.path.abspath(data_root))
    for cand in (os.path.join(repo, ".env"), ".env"):
        if not os.path.exists(cand):
            continue
        try:
            with open(cand, encoding="utf-8", errors="ignore") as f:
                for ln in f:
                    k, _, v = ln.partition("=")
                    if k.strip() == "SHARADAR_API_KEY" and v.strip():
                        os.environ["SHARADAR_API_KEY"] = v.strip().strip("'\"")
                        return True
        except OSError:
            continue
    return False


def ensure_rate_cache(data_root: str, start_year: int = 2015) -> int:
    """Make sure a REAL 3-month Treasury series is on disk before any IV is solved.

    This was found by profiling, and it is a genuine correctness bug, not a speed one:
    `blackscholes._load_rates` fetches FRED, FRED is unreachable from this machine (the
    connection is reset), and the failure path is a SILENT fall back to a coarse hard-coded
    schedule — flat 2.0% for all of 2022, a year the actual 3-month bill went from 0.06% to
    4.4%. Every IV solved that way is off by up to ~0.8 vol points at 30 days.

    Treasury.gov serves the same series and IS reachable, so it is fetched once (one small CSV
    per year), converted to the exact two-column shape `_load_rates` already reads, and written
    to the shared `data/bulk/prepared/dgs3mo.csv`. Nothing in blackscholes.py changes — it finds
    the file and never touches the network.

    Returns the number of daily observations available (0 means the coarse fallback is in use,
    which is then recorded in every coverage file rather than passing silently).
    """
    import datetime as dt

    path = os.path.join(data_root, "bulk", "prepared", "dgs3mo.csv")
    if os.path.exists(path):
        return _rate_rows(path)
    try:
        import requests
    except ImportError:                                                  # pragma: no cover
        return 0
    rows = []
    this_year = dt.date.today().year
    for yr in range(start_year, this_year + 1):
        url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
               f"daily-treasury-rates.csv/{yr}/all")
        try:
            r = requests.get(url, timeout=45,
                             params={"type": "daily_treasury_bill_rates",
                                     "field_tdr_date_value": str(yr), "_format": "csv"},
                             headers={"User-Agent": "Valquo research"})
        except Exception as e:                                            # noqa: BLE001
            _log(f"treasury {yr}: {type(e).__name__}")
            continue
        if r.status_code != 200 or "," not in r.text:
            _log(f"treasury {yr}: HTTP {r.status_code}")
            continue
        rows.extend(_parse_treasury_csv(r.text))
    if not rows:
        _log("no Treasury series available — IV will use the COARSE fallback rate schedule")
        return 0
    rows.sort()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("DATE,DGS3MO\n")
        for d, v in rows:
            f.write(f"{d},{v}\n")
    os.replace(tmp, path)
    _log(f"wrote {len(rows)} daily 3-month Treasury observations -> {path}")
    return len(rows)


def _parse_treasury_csv(text: str):
    """13-week COUPON EQUIVALENT — the coupon-equivalent basis is what FRED's DGS3MO quotes, so
    the file stays interchangeable with the FRED one blackscholes.py expects."""
    import csv
    import datetime as dt

    rdr = csv.reader(text.splitlines())
    header = next(rdr, None) or []
    up = [h.strip().upper() for h in header]
    col = None
    for i, h in enumerate(up):
        if "13 WEEK" in h and "COUPON" in h:
            col = i
            break
    if col is None:
        for i, h in enumerate(up):
            if "13 WEEK" in h:
                col = i
                break
    if col is None:
        return []
    out = []
    for row in rdr:
        if len(row) <= col:
            continue
        try:
            d = dt.datetime.strptime(row[0].strip(), "%m/%d/%Y").date()
            v = float(row[col])
        except (ValueError, TypeError):
            continue
        out.append((d.isoformat(), v))
    return out


def _rate_rows(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)
    except OSError:
        return 0


def rate_cache_path(data_root: str) -> str:
    return os.path.join(data_root, "bulk", "prepared", "dgs3mo.csv")


def prefetch_spots(syms, data_root: str) -> dict:
    """Fetch every missing bar series ONCE, in the parent, before any worker starts.

    Two processes fetching and pickling the same bars file would race on the same path. The
    fetch is also the only network call in this whole job, so keeping it in one place makes it
    obvious that the workers are pure compute.
    """
    have = {}
    for sym in syms:
        s = load_spots(sym, data_root, allow_fetch=True)
        have[sym] = len(s)
        if not s:
            _log(f"{sym}: NO underlying close available — will be skipped")
    return have


# ============================== the work ====================================================
def enrich_one(sym: str, options_root: str, out_root: str, data_root: str, q: float) -> dict:
    # Point the rate loader at the on-disk series ONCE per worker process. Without this each
    # worker tries FRED, waits out a 15-second connection reset, and silently uses the coarse
    # fallback schedule for every contract it prices.
    import datetime as dt

    from valuation.edge import blackscholes as BS
    BS.risk_free_rate(dt.date(2020, 1, 2), cache_path=rate_cache_path(data_root))

    spots = load_spots(sym, data_root, allow_fetch=False)
    if not spots:
        return {"symbol": sym, "error": "no underlying close"}
    t0 = time.time()
    cov = G.enrich_symbol(sym, spots, options_root, out_root, q=q)
    cov["seconds"] = round(time.time() - t0, 1)
    return cov


def _worker(args):
    return enrich_one(*args)


def summarise(cov: dict) -> str:
    if cov.get("error"):
        return f"{cov['symbol']}: ERROR {cov['error']}"
    flags = cov.get("flags") or []
    return (f"{cov['symbol']}: {len(cov.get('years', {}))} years, "
            f"{cov.get('rows_iv_ok', 0):,} of {cov.get('rows_in', 0):,} rows priced "
            f"({cov.get('iv_ok_frac', 0):.1%}), {cov.get('dates', 0)} dates, "
            f"{cov.get('seconds', 0)}s"
            + (f" | FLAGS: {'; '.join(flags)}" if flags else ""))


def write_report(out_root: str, report_path: str):
    """Roll every per-name coverage.json into one manifest + a committable summary.

    The derived payload itself is gitignored with the rest of `data/`, so the coverage record is
    the only part of this job that survives into the repo. It is deliberately the part that says
    what DIDN'T work.
    """
    rows = {}
    if os.path.isdir(out_root):
        for sym in sorted(os.listdir(out_root)):
            p = os.path.join(out_root, sym, "coverage.json")
            if not os.path.exists(p):
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    rows[sym] = json.load(f)
            except (OSError, ValueError):
                continue
    man_path = os.path.join(out_root, "coverage_manifest.json")
    G._atomic_json(rows, man_path)

    tot_in = sum(r.get("rows_in", 0) for r in rows.values())
    tot_ok = sum(r.get("rows_iv_ok", 0) for r in rows.values())

    def _oi_missing(rec):
        """Prefer the per-name total, but fall back to summing the year records — a name derived
        before that total was aggregated still has the numbers, one level down."""
        if rec.get("oi_missing_rows"):
            return int(rec["oi_missing_rows"])
        return int(sum((y or {}).get("oi_missing_rows", 0)
                       for y in (rec.get("years") or {}).values()))

    tot_oi_missing = sum(_oi_missing(r) for r in rows.values())
    skipped = {}
    for r in rows.values():
        for k, v in (r.get("skipped") or {}).items():
            skipped[k] = skipped.get(k, 0) + v
    summary = {
        "schema_version": G.SCHEMA_VERSION,
        "band": dict(G.BAND),
        "names_enriched": len(rows),
        "contract_days_in": tot_in,
        "contract_days_priced": tot_ok,
        "iv_ok_frac": round(tot_ok / tot_in, 4) if tot_in else 0.0,
        "oi_sentinel_rows": tot_oi_missing,
        "oi_sentinel_frac": round(tot_oi_missing / tot_in, 4) if tot_in else 0.0,
        "skipped_by_reason": dict(sorted(skipped.items(), key=lambda kv: -kv[1])),
        # schema + rate source are per NAME, not global: a partially-resumed root can legitimately
        # hold names derived under an older schema or an older rate curve, and that must be
        # visible rather than averaged away.
        "schema_versions": sorted({r.get("schema_version") for r in rows.values()},
                                  key=lambda x: (x is None, x)),
        "rate_sources": sorted({r.get("rate_source", "unknown") for r in rows.values()}),
        "per_name": {
            s: {"years": sorted((r.get("years") or {}).keys()),
                "rows_in": r.get("rows_in", 0),
                "rows_priced": r.get("rows_iv_ok", 0),
                "iv_ok_frac": round(r.get("iv_ok_frac", 0), 4),
                "dates": r.get("dates", 0),
                "oi_sentinel_rows": _oi_missing(r),
                "schema_version": r.get("schema_version"),
                "rate_source": r.get("rate_source", "unknown"),
                "flags": r.get("flags", [])}
            for s, r in sorted(rows.items())},
    }
    G._atomic_json(summary, report_path)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default=DEFAULT_DATA)
    ap.add_argument("--options-root", default=None, help="default <data-root>/options")
    ap.add_argument("--out-root", default=None, help="default <data-root>/options_derived")
    ap.add_argument("--report", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "GREEKS_COVERAGE.json"))
    ap.add_argument("--symbols", default="", help="comma-separated subset")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-age-min", type=float, default=MIN_AGE_MIN)
    ap.add_argument("--dividend-yield", type=float, default=0.0)
    ap.add_argument("--force", action="store_true", help="re-derive names already done")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    options_root = a.options_root or os.path.join(a.data_root, "options")
    out_root = a.out_root or os.path.join(a.data_root, "options_derived")
    only = {s.strip().upper() for s in a.symbols.split(",") if s.strip()} or None

    todo, skipped = eligible(options_root, out_root, a.min_age_min, only, a.force)
    if a.limit:
        todo = todo[:a.limit]
    _log(f"eligible: {len(todo)} names | skipped: {len(skipped)}")
    for sym, why in sorted(skipped.items()):
        if why not in ("already enriched",):
            _log(f"  skip {sym}: {why}")
    n_done_before = sum(1 for w in skipped.values() if w == "already enriched")
    if a.dry_run:
        _log("dry run — nothing written. Would enrich: " + (", ".join(todo) or "(none)"))
        return 0
    if not todo:
        _log("nothing to do")
        write_report(out_root, a.report)
        return 0

    os.makedirs(out_root, exist_ok=True)
    n_rates = ensure_rate_cache(a.data_root)
    _log(f"risk-free series: {n_rates} daily observations"
         + ("" if n_rates else "  <-- COARSE FALLBACK, IVs will be biased; see coverage files"))
    _log("prefetching underlying closes (the only network call in this job)")
    if not ensure_sharadar_key(a.data_root):
        _log("no SHARADAR_API_KEY — only names with a cached bars file can be enriched")
    prefetch_spots(todo, a.data_root)

    prog_path = os.path.join(out_root, "DERIVED_PROGRESS.txt")
    t0 = time.time()
    total = len(todo)
    done = 0
    jobs = [(s, options_root, out_root, a.data_root, a.dividend_yield) for s in todo]

    def _record(cov):
        nonlocal done
        done += 1
        line = (f"[greeks] [{done}/{total}] {summarise(cov)} | "
                f"{n_done_before + done} of {n_done_before + total} names enriched | "
                f"{(time.time() - t0) / 60:.0f}m")
        _log(line)
        try:
            with open(prog_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    if a.workers <= 1:
        for j in jobs:
            _record(_worker(j))
    else:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(_worker, j): j[0] for j in jobs}
            for fut in as_completed(futs):
                try:
                    _record(fut.result())
                except Exception as e:                                    # noqa: BLE001
                    _record({"symbol": futs[fut], "error": f"{type(e).__name__}: {e}"})

    summary = write_report(out_root, a.report)
    _log(f"DONE {summary['names_enriched']} names | "
         f"{summary['contract_days_priced']:,} of {summary['contract_days_in']:,} "
         f"contract-days priced ({summary['iv_ok_frac']:.1%}) | report -> {a.report}")
    flagged = {s: v["flags"] for s, v in summary["per_name"].items() if v["flags"]}
    if flagged:
        _log(f"{len(flagged)} names carry sanity flags — see the report, do not silence them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
