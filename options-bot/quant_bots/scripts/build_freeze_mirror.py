#!/usr/bin/env python3
"""
build_freeze_mirror.py — load the D10 Sharadar freeze into a SharadarStore.

C5. `core/pit_universe.py` has only ever been verified against a synthetic
30-name mirror. It needs real TICKERS + SEP + DAILY to be exercised, and the
D10 freeze has them:

    data/backtest_freeze_2026-08/bulk/tickers.csv     78,881 rows
    data/backtest_freeze_2026-08/bulk/sep.csv     46,248,674 rows   3.2 GB
    data/backtest_freeze_2026-08/bulk/daily.csv   40,007,542 rows   2.5 GB

WHY THIS FILTERS BY DATE
────────────────────────
A full mirror is ~86M rows and tens of GB of SQLite. The survivorship report
only ever asks two questions per as-of date — "what did this cost then"
(SEP.closeunadj), "what was it worth then" (DAILY.marketcap) — plus a 30-SESSION
volume lookback. So we keep only rows inside a short window before each as-of
date. That is a ~90% reduction with zero effect on the answer, and it is the
difference between a run you can do and one you plan and never do.

The windows are computed from the as-of dates you pass, so a DIFFERENT set of
dates needs a rebuild. The script says so rather than silently answering a
question about dates it does not hold.

LICENSING — READ
────────────────
The freeze is licensed Sharadar data. This script READS it and writes a derived
SQLite file. Neither the freeze nor the mirror may ever be committed. The output
path defaults under data/, which is gitignored at the repository root.

    python scripts/build_freeze_mirror.py \
        --freeze ../../data/backtest_freeze_2026-08/bulk \
        --db     ../../data/c5_pit_mirror.db \
        --dates  2000-06-30,2001-06-30,...
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.sharadar import SharadarStore

logger = logging.getLogger("build_freeze_mirror")

# csv.field_size_limit guards against a pathological row; SF1 payloads are the
# only thing near it and we do not load SF1 here, but raise it anyway so a
# single odd row cannot abort a 3 GB stream 40 minutes in.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def wanted_dates(as_of_dates, window_days):
    """
    The set of calendar dates any lookup could touch.

    `_avg_volume` takes the last 30 SESSIONS on or before the as-of date. Thirty
    sessions is ~42 calendar days; the default 60 leaves real slack for holidays
    and for `price_on`/`marketcap_on`, which walk back to the most recent
    non-null row and can need more than a week around a long market closure.
    """
    keep = set()
    for d in as_of_dates:
        for k in range(window_days + 1):
            keep.add((d - timedelta(days=k)).isoformat())
    return keep


def stream_filtered(path, keep_dates, label, expected_rows=None, date_col="date"):
    """
    Yield rows whose `date` is in `keep_dates`.

    Progress is reported against `expected_rows` (from the freeze MANIFEST), NOT
    against `fh.tell()`. Calling tell() on a file being consumed by an iterator
    raises `OSError: telling position disabled by next() call` — which is how the
    first attempt at this died 20 minutes into a 3 GB stream, having written a
    60 MB database that looked like partial success.
    """
    total = kept = 0
    t0 = time.time()
    with path.open("r", newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            total += 1
            if row.get(date_col) in keep_dates:
                kept += 1
                yield row
            if total % 2_000_000 == 0:
                pct = f"{100.0 * total / expected_rows:.0f}%" if expected_rows else "?"
                logger.info("  %s: %s scanned (%s), %s kept, %.0fs",
                            label, f"{total:,}", pct, f"{kept:,}", time.time() - t0)
    logger.info("  %s: DONE %s scanned, %s kept (%.1f%%), %.0fs",
                label, f"{total:,}", f"{kept:,}",
                100.0 * kept / max(total, 1), time.time() - t0)


def main() -> int:
    p = argparse.ArgumentParser(description="Load the Sharadar freeze into a SharadarStore.")
    p.add_argument("--freeze", required=True, help="directory holding tickers/sep/daily.csv")
    p.add_argument("--db", required=True)
    p.add_argument("--dates", required=True,
                   help="comma-separated ISO as-of dates the mirror must answer for")
    p.add_argument("--window-days", type=int, default=60)
    p.add_argument("--skip-sep", action="store_true")
    p.add_argument("--skip-daily", action="store_true")
    p.add_argument("--skip-tickers", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    freeze = Path(args.freeze)
    as_of = [date.fromisoformat(s.strip()) for s in args.dates.split(",") if s.strip()]
    keep = wanted_dates(as_of, args.window_days)
    logger.info("as-of dates: %d (%s .. %s); calendar dates retained: %d",
                len(as_of), min(as_of), max(as_of), len(keep))

    store = SharadarStore(Path(args.db))

    # TICKERS is small and is loaded WHOLE — it is the survivorship-free spine,
    # and filtering it by date would be self-defeating.
    if not args.skip_tickers:
        path = freeze / "tickers.csv"
        logger.info("TICKERS from %s", path)
        with path.open("r", newline="", encoding="utf-8", errors="replace") as fh:
            n = store.ingest_tickers(csv.DictReader(fh))
        logger.info("  TICKERS: %d rows", n)

    if not args.skip_sep:
        path = freeze / "sep.csv"
        logger.info("SEP from %s (filtered)", path)
        n = store.ingest_sep(stream_filtered(path, keep, "SEP", 46_248_674))
        logger.info("  SEP: %d rows kept", n)

    if not args.skip_daily:
        path = freeze / "daily.csv"
        logger.info("DAILY from %s (filtered)", path)
        n = store.ingest_daily(stream_filtered(path, keep, "DAILY", 40_007_542))
        logger.info("  DAILY: %d rows kept", n)

    logger.info("store stats: %s", store.stats())
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
