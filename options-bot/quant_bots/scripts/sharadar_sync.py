"""
Sync the Sharadar bundle into the local sqlite mirror.

FIRST RUN (seed) — expect this to take a while; SEP is millions of rows:

    python scripts/sharadar_sync.py --tables TICKERS DAILY SEP SF1 --full

DAILY (incremental) — add to cron after the close:

    python scripts/sharadar_sync.py --tables TICKERS DAILY SEP SF1

WHY SYNC ON `lastupdated` AND NOT `date`
────────────────────────────────────────
Sharadar RESTATES. A fundamentals row for calendardate 2023-03-31 can be
rewritten months later when a company files a 10-K/A. `date` and
`calendardate` never move; `lastupdated` does. Syncing on `date` therefore
permanently misses every revision — your local mirror slowly diverges from the
source and you never get an error telling you so.

Price tables use `date` because a historical bar genuinely does not change.

The incremental window OVERLAPS by a day deliberately. Re-fetching a day you
already have is cheap; missing rows that landed after your last sync is not,
and the UPSERT absorbs the duplicates.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from core.sharadar import (
    BUNDLE_TABLES, SharadarClient, SharadarError, SharadarStore, iter_zip_csv,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sharadar_sync")

INGEST = {
    "SEP": "ingest_sep",
    "SFP": "ingest_sep",          # identical schema; concatenated with SEP
    "TICKERS": "ingest_tickers",
    "SF1": "ingest_sf1",
    "DAILY": "ingest_daily",
}

# Tables too large to page through 10,000 rows at a time. SEP alone is well
# past the official client's 1,000,000-row ceiling — and that client RAISES
# rather than returning a partial result, so paging these is not slow, it is
# broken.
BULK_ONLY = {"SEP", "SFP", "SF1", "DAILY"}


def sync_table(client, store, table, full, cache_dir, sf1_dimensions):
    ingest = getattr(store, INGEST[table])
    watermark_col = BUNDLE_TABLES[table]

    if full or table not in BULK_ONLY:
        if table in BULK_ONLY or full:
            logger.info("=== %s: FULL bulk export ===", table)
            zip_path = cache_dir / f"{table}.zip"
            filters = {}
            if table == "SF1" and sf1_dimensions:
                filters["dimension"] = sf1_dimensions
            client.bulk_export(table, zip_path, **filters)
            n = ingest(iter_zip_csv(zip_path))
        else:
            logger.info("=== %s: full paged fetch ===", table)
            n = ingest(client.fetch(table))
    else:
        since = store.watermark(table)
        if not since:
            raise SharadarError(
                f"{table}: no sync watermark, so there is nothing to be "
                f"incremental about. Seed it first with --full.")
        # Overlap a day; the UPSERT absorbs duplicates.
        start = (date.fromisoformat(since[:10]) - timedelta(days=1)).isoformat()
        logger.info("=== %s: incremental from %s (on %s) ===", table, start, watermark_col)
        filters = {watermark_col: {"gte": start}}
        if table == "SF1" and sf1_dimensions:
            filters["dimension"] = sf1_dimensions
        n = ingest(client.fetch(table, **filters))

    store.record_sync(table, date.today().isoformat(), n)
    logger.info("%s: %d rows ingested", table, n)
    return n


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tables", nargs="+", default=["TICKERS", "DAILY", "SEP", "SF1"],
                   choices=sorted(INGEST))
    p.add_argument("--full", action="store_true",
                   help="full bulk export rather than an incremental delta")
    p.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "sharadar.db")
    p.add_argument("--cache-dir", type=Path, default=PROJECT_ROOT / "data" / "sharadar_cache")
    p.add_argument("--sf1-dimensions", nargs="*", default=["ARQ", "ARY", "ART"],
                   help="AR* only. MR* dimensions are restated with hindsight "
                        "AND set datekey to the period end — two look-ahead "
                        "traps. Pass nothing to fetch every dimension.")
    args = p.parse_args()

    if not os.getenv("NASDAQ_DATA_LINK_API_KEY"):
        print("\nNASDAQ_DATA_LINK_API_KEY is not set.\n\n"
              "Add it to quant_bots/.env:\n"
              "    NASDAQ_DATA_LINK_API_KEY=your_key_here\n\n"
              "Get the key at https://data.nasdaq.com/account/profile\n"
              "NEVER commit .env — it is gitignored for exactly this reason.\n")
        return 1

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    client = SharadarClient()
    store = SharadarStore(args.db)

    try:
        total = 0
        for t in args.tables:
            try:
                total += sync_table(client, store, t, args.full,
                                    args.cache_dir, args.sf1_dimensions)
            except SharadarError as e:
                logger.error("%s FAILED: %s", t, e)
                # Keep going — a missing entitlement on one table should not
                # abort the tables you do have.
        s = store.stats()
        print(f"\n  Local mirror: {args.db}")
        print(f"    sep     {s['sep']:>12,} rows"
              + (f"   {s['sep_range'][0]} .. {s['sep_range'][1]}" if s["sep_range"] else ""))
        print(f"    tickers {s['tickers']:>12,} rows")
        print(f"    sf1     {s['sf1']:>12,} rows")
        print(f"    daily   {s['daily']:>12,} rows")
        print(f"\n  {total:,} rows ingested this run.\n")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
