# HANDOFF — final Sharadar freeze (roadmap #4)

**Session date:** 2026-08-02
**Branch:** `worktree-sharadar-freeze`
**Scope:** data-layer only. Nothing in the options work, the live web app or the valuation
engine was touched.

## One line

**All 10 Sharadar tables froze clean to `data/backtest_freeze_2026-08/` (13.4 GB) — every table
is at least as complete as the live working set, nothing came back short, and the snapshot is
self-contained enough to run the whole backtest from with no API key.**

---

## Where it is and how to use it

```
data/backtest_freeze_2026-08/          <- READ-ONLY (every file has the Windows read-only bit)
    MANIFEST.json                      <- rows, date range, bytes, sha256, pull time, per table
    backtest/                          <- point WRDS_DATA_DIR / --data-dir here
        fundamentals.csv insiders.csv institutional.csv universe.txt prices/<T>.csv
    bulk/                              <- the extracted bulk CSVs
        sf1 sep sfp sf2 sf3a sf3 daily actions events tickers .csv
        prepared/                      <- actions/events/daily/sf3/tickers .pkl
    raw/                               <- the 10 downloaded SHARADAR_<TABLE>_2026-08-02.zip
```

To run the backtest entirely off the freeze (no key, no network):

```
python -m valuation.edge.fundamental_panel --data-dir data/backtest_freeze_2026-08/backtest
```

That path matters. `WRDSProvider.bulk_dir` derives its cache directory as
`<parent of the data dir>/bulk/prepared`, so nesting `backtest/` and `bulk/` under one freeze
root is what makes the snapshot resolve its OWN caches instead of silently reading the live
ones. **The live `data/backtest` and `data/bulk` were left completely untouched** — nothing
else in the project changes behaviour because of this freeze.

To unlock it (e.g. to delete or re-derive):
`python -m valuation.edge.sharadar_freeze --root data/backtest_freeze_2026-08 --stage unlock`

## Everything froze clean — no table came in short

Verified against the live working set; the freeze is a superset on every comparison.

| table | rows | date range |
|---|---|---|
| SF1 (fundamentals, ALL dimensions) | 3,203,836 | 1990-06-06 .. 2026-07-31 |
| SEP (equity prices) | 46,248,674 | 1997-12-31 .. 2026-07-31 |
| SFP (fund/ETF prices) | 15,432,513 | 1997-12-31 .. 2026-07-31 |
| DAILY (PIT market cap + ratios) | 40,007,542 | 1998-12-01 .. 2026-07-31 |
| SF3 (13F per-manager) | 79,530,816 | 2013-06-30 .. 2026-06-30 |
| SF2 (insiders) | 11,807,135 | 2008-01-02 .. 2026-07-31 |
| SF3A (13F per-ticker) | 666,561 | 2013-06-30 .. 2026-06-30 |
| EVENTS | 2,537,722 | 1993-11-08 .. 2026-07-31 |
| ACTIONS | 671,781 | 1997-12-31 .. 2026-07-31 |
| TICKERS | 78,881 | .. 2026-08-01 |

Derived into the offline backtest layout:

| file | freeze | live working set |
|---|---|---|
| `fundamentals.csv` (ARQ) | **230,488 rows / 3,506 tickers** | 197,265 rows |
| `insiders.csv` | **6,638,128 rows / 3,080 tickers** | (553 MB) |
| `institutional.csv` | **131,194 rows / 3,463 tickers** | (15 MB) |
| `prices/` | **3,735 files**, date-sorted | 2,998 files |

Prepared caches: actions 31,939 tickers - events 17,782 - daily 17,421 (1,919,853 month-rows)
- sf3 13,790 (289,058 manager-quarters) - tickers 48,925 (25,843 with a sector).

**Integrity checkpoints — all pass.** AAPL 2015Q2 PIT market cap, fundamentals row count,
ticker count, price-file count, SPY present, TICKERS sector coverage. Per-table sha256 of both
the extracted CSV and the source zip is in MANIFEST.json, so "is this freeze still whole?"
is answerable months from now without Sharadar.

## Three things worth knowing

**1. The freeze is a strict SUPERSET of the working set, by construction.** The universe is
`live tickers UNION freshly-ranked top-3000` = 3,737 names (3,001 live + 736 new). A name
already on disk survives into the freeze even if it has since shrunk out of the top 3,000, so
"at least as complete" is guaranteed rather than hoped for, and the verify stage asserts it.

**2. The full SF1 is frozen with ALL dimensions — the live export is ARQ-only.** This is the
direct cause of the bug in CLAUDE.md's LATEST section: `roe`, `roic` and `assetturnover` are
non-null in 0 of 197,265 rows because Sharadar only fills its averaged columns in ART/ARY.
Those dimensions are now on disk permanently (sf1.csv, 2.29 GB, 3.2M rows vs the 230k ARQ rows
we derive). The derived `backtest/fundamentals.csv` stays ARQ-only so it is a drop-in for the
current file — **nothing about the current panel's behaviour changes.** If a future session
wants Sharadar's own ART/ARY ratios instead of the derived ones, the data is there.

**3. Sharadar's DAILY `marketcap` is in MILLIONS, not dollars.** AAPL 2015-06-30 is stored as
`722571.4`, which IS the "$722.6B verified" checkpoint in CLAUDE.md — confirmed byte-identical
between the freeze and the live cache. My first verify pass read it as dollars, reported 0.0
and flagged a FAIL on a perfectly good freeze. Now asserted by
`test_aapl_checkpoint_reads_daily_marketcap_as_millions` so nobody re-learns it.

## A real bug I hit, since it will bite anyone else streaming these files

**The bulk exports are NOT ordered by ticker.** SEP row 1 is ABILF, row 3 is AAC.U, and rows
within a ticker are date-DESCENDING. The first price-split implementation used a bounded pool
of open file handles on the assumption of ticker ordering; it thrashed, evicting and reopening
on nearly every row, and was still crawling after 12 minutes. Rewritten to buffer per ticker
and flush in batches: **40M+ rows in ~90k rows/s, 3,735 files in 727s.** Both properties are
pinned by tests (`..._survives_interleaved_tickers_and_multiple_flushes`,
`..._sorts_a_date_descending_source`).

## Note for the next session: the prompt's closing note is STALE

The brief said the sector-neutral panel fix (stock roadmap #13) is "DATA-unblocked and only
needs wiring into `build_fundamental_panel` (which still hard-codes `sector=""`)". That is out
of date on both counts:

- `fundamental_panel.py:907` **already populates** `m["sector"]` from the TICKERS metadata.
  The `"sector": ""` at line 252 is just the default in `_sf1_to_metrics`, overwritten later.
- Per `CODE_AUDIT.md` M3, sector-neutral ranking was **unblocked, then TESTED AND REJECTED on
  merit** — it fails the pre-committed held-out margin in both directions (early +0.41 t but
  -0.16% alpha; late -0.22 t, -0.62% alpha). It is deliberately kept off.

So roadmap #13 is closed, not pending. Nothing to do there.

## What was committed

Code and docs only — **no data**, per the hard rule. `data/` is gitignored and the freeze lives
entirely inside it.

- `valuation/edge/sharadar_freeze.py` — the freeze tool (5 resumable stages: download, derive,
  prepare, manifest, lock/unlock)
- `tests/test_freeze.py` — 13 tests, all passing
- `HANDOFF_sharadar_freeze.md` — this file

Test suites green: **119/119 edge, 14/14 bulk, 13/13 freeze.**

## Caveats, stated rather than buried

- **The freeze has not been proven by running a full backtest against it.** Structure, row
  counts, date ranges, checksums and the AAPL checkpoint all verify, and the prepared caches
  are byte-identical to the live ones where they overlap — but a full `fundamental_panel` run
  off `--data-dir data/backtest_freeze_2026-08/backtest` is the only thing that proves the
  whole chain end to end. That run takes ~12 min and is the recommended next step.
- Prices are `closeadj` (split- AND dividend-adjusted), matching what the live export wrote.
  SEP is already split-adjusted, so ACTIONS split ratios are deliberately NOT re-applied —
  don't "fix" that.
- `--reuse-hashes` exists for iterating on the manifest and is OFF by default. A genuine
  integrity check must re-hash; metadata is exactly what a silent corruption leaves untouched.
- The EVENTS earnings mapping is still code 22 and still PARTIAL (~2.83/ticker/yr vs ~4
  expected) — unchanged by this work, just frozen as-is.
