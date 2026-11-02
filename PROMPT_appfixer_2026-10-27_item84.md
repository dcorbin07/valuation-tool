# PROMPT — app fixer — 2026-10-27 — item 84: the refresh rebuilt the prices and NOT the fundamentals; and Monday's hot list never ran

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first, including its
2026-10-24 correction entry. **Do not edit `DECISIONS.md`.** Read your items 81, 82 and 83.

## Part A — the 10-22 book was scored on fundamentals filed through 2026-10-02

Measured by the manager on 2026-10-27, read-only:

- `data/backtest/fundamentals.csv`, `insiders.csv` and `institutional.csv` are byte-identical to
  the 10-04 export: mtime 2026-10-04 15:20–15:22, and the same sizes in `vs_live`.
  `fundamentals.csv` has `datekey` max **2026-10-02**.
- `data/backtest_freeze_2026-10/MANIFEST.json` (created 2026-10-23T20:00) shows the 10-23 raw
  zips all pulled (SF1, SF2, SF3, SEP, DAILY …). But `derive_stats` reads
  `fundamentals_rows: null, fundamentals_tickers: 0, insider_rows: null, institutional_rows: null`,
  and `verdict.clean` is **false**.
- So the derive stage produced nothing, and the old files stayed in place. `refresh_sharadar.bat`
  printed SUCCESS anyway, because `refresh_backtest_from_freeze` checks only that the newest
  **close** moved.
- In the 10-23 raw SF1, **230 tickers** filed an ARQ row with `datekey` in (2026-10-02,
  2026-10-22]. **69** of them are $10B+ by that row's `marketcap`. **5 are in the recorded book**:
  GGG, JEF, MEDP, MU, SYF.
- The book's JSON still says `data_as_of: 2026-10-22`. Item 81's 70-of-81 fidelity check used the
  same 10-02 fundamentals.

**The fix, for 2027-01-25:**

1. **Find why derive produced zero rows** on the 10-23 run, and fix it. Re-derive from the 10-23
   raw zips into the freeze, never into the pinned July caches. Confirm that fundamentals,
   insiders and 13F reach their expected dates.
2. **The refresh fails loudly** when any derived table did not move, or did not reach the export
   date. Prices moving is not enough. Make the manifest's `clean: false` fail the run.
3. **The build refuses stale fundamentals**, as item 81 does for the `daily` cache:
   - refuse when `fundamentals.csv`'s newest `datekey` is more than a set number of trading days
     before `--as-of`;
   - print the fundamentals, insider and 13F dates it used;
   - make `data_as_of` say which date each input actually reaches.
4. **Re-run item 81's fidelity build** on fully fresh inputs as a scratch file and report the
   overlap with the recorded book. It is not a new book, and nothing is appended.
5. **Update `REBALANCE_RUNBOOK_2027-01-25.md`** with the check Don reads on the night.

## Part B — Monday's hot list never ran (item 82's finding)

GitHub delivered neither hot-list cron slot on 2026-10-26, so the public hot list still shows
10-23's scan and tonight's LIVE CHECK will fail on `hot list is fresh`.

- **Design a scheduler fix that does not depend on GitHub honouring one exact cron string.** For
  example, a catch-up: any later job that does fire runs the hot scan if `scan_date` is older than
  the last closed session, while it is still before the next open. Keep the scan idempotent per
  session.
- It must scan on the last closed session's closes, never intraday prices.
- `.github` changes go in `data/pending_workflows/` plus `install_workflows.bat`, for Don to
  install. Say exactly what he runs.
- Give Don the one-time manual catch-up as well: which workflow, which `kind`, and when it is
  safe to run.

## Done

On origin/main, with a plain-words summary for Don for each part. No key printed, no live order,
no percentage changed, nothing appended to the record.
