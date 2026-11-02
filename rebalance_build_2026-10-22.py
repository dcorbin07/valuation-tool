"""One-off rebalance build for 2026-10-22 (manager script, not committed).

Runs the SHIPPED builder exactly as REBALANCE_RUNBOOK_2026-10-22.md Path B says:

    python -m valuation.edge.valquo_index --full-universe data/backtest --config taxable
           --as-of 2026-10-22 --out data/valquo_index.json

with ONE difference: where five of the Sharadar bulk caches are read from.

`refresh_sharadar.bat` updates data/backtest (fundamentals, insiders, 13F, prices) but NOT the
bulk caches under data/bulk/prepared, which are still from 2026-07-29. Built the shipped way, the
book would take point-in-time MARKET CAPS from July: measured on 2026-10-23, that moves 84 of
about 1,280 names across the $10B line, and caps have moved -15% to +19% (10th-90th percentile).

So two caches are read from the 2026-10-04 freeze, built from the export taken that day:

    daily  -- point-in-time market cap and ratios, rows through 2026-10-02
    sf3    -- 13F holdings, which then include the Q2 2026 filings due 2026-08-14

Every other cache (actions, events, tickers, congress, usaspending, edgar13d, short_interest,
elite_conv) is read from data/bulk/prepared exactly as before. The freeze's actions and tickers
caches carry FEWER names than July's (31,206 vs 31,937 and 44,240 vs 48,925), so they are not
swapped. No file under data/bulk is modified, the freeze is
read-only and is only read, and the builder code is not changed.
"""
import os
import shutil
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

FRESH_DIR = os.path.join("data", "backtest_freeze_2026-10", "bulk", "prepared")
OLD_DIR = os.path.join("data", "bulk", "prepared")
FRESH = ("daily", "sf3")
BOOK = os.path.join("data", "valquo_index.json")
BACKUP = os.path.join("data", "valquo_index_before_2026-10-22.json")

for name in FRESH:
    p = os.path.join(FRESH_DIR, name + ".pkl")
    if not os.path.exists(p):
        sys.exit("STOP: %s is missing, so the fresh caches are not where expected." % p)
if not os.path.exists(BOOK):
    sys.exit("STOP: %s (the book in force) is missing, so the 30%% band cannot apply." % BOOK)

import valuation.edge.data_providers as D  # noqa: E402
from valuation.edge import bulk as B        # noqa: E402

_seen = {}


def _bulk(self, name):
    cache = getattr(self, "_bulk_cache", None)
    if cache is None:
        cache = self._bulk_cache = {}
    if name not in cache:
        src = FRESH_DIR if name in FRESH else OLD_DIR
        cache[name] = B._load_cache(name, src) or {}
        if name not in _seen:
            _seen[name] = src
            print("[cache] %-14s from %s  (%d entries)" % (name, src, len(cache[name])), flush=True)
    return cache[name]


D.WRDSProvider._bulk = _bulk

# Show the market-cap vintage actually in use, before anything is built.
_daily = B._load_cache("daily", FRESH_DIR) or {}
_last = Counter((rows[-1][0] if rows else None) for rows in _daily.values())
print("[cache] daily market-cap rows end on (most common): %s" % _last.most_common(2), flush=True)

if not os.path.exists(BACKUP):
    shutil.copy2(BOOK, BACKUP)
    print("[book ] backed up the book in force to %s" % BACKUP, flush=True)

from valuation.edge import valquo_index as V  # noqa: E402

V.main(["--full-universe", os.path.join("data", "backtest"), "--config", "taxable",
        "--as-of", "2026-10-22", "--out", BOOK])
