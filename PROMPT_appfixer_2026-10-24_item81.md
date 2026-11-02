# PROMPT — app fixer — 2026-10-24 — item 81: make the January rebalance work without tonight's workarounds

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), your items 80 and 80b,
and the manager's one-off `rebalance_build_2026-10-22.py` (main folder, not committed). **Do not
edit `DECISIONS.md`.**

## What happened on 2026-10-23

The 10-22 rebalance is recorded: **HTTP 201, 81 positions**. Getting there took three fixes on the
night:

1. **The door read `ok` where `conformance()` returns `conforms`** (item 80).
2. **The door could not find the recorded row** (item 80b).
3. **The bulk caches were three months stale, and the runbook never mentioned it.**
   - `refresh_sharadar.bat` refreshes `data/backtest`, but not `data/bulk/prepared`. That still
     held 2026-07-29 caches.
   - So the build would have read July point-in-time **market caps** and July **13F**. Measured:
     84 names cross the $10B line, and caps moved −15% to +19% (10th–90th percentile).
   - The manager's helper took `daily` and `sf3` from the 2026-10-04 freeze's caches instead and
     changed nothing else.

## The fix, for 2027-01-25

- **Refresh the caches with the data.** Make `refresh_sharadar.bat`, or the build, refresh the
  bulk caches the build actually reads (`daily` and `sf3` at minimum) from the same fresh export.
  - Never overwrite the July caches that research scripts pin. Either:
    - write to a dated directory and point the build at it explicitly, or
    - version the caches and make the build name the vintage it used.
  - The build's printout must state the market-cap date it used.
- **Refuse stale caches.** The build refuses when the `daily` cache's newest row is more than a set
  number of trading days before `--as-of`. A three-month-old market cap must not pass silently
  again.
- **Fix the month-end blind spot.** The month-end down-sampling means a fresh export's October row
  is 10-23, which is later than an as-of of 10-22. The build would then fall back to 09-30. Make
  the cache keep the last row on or before the as-of, or state the limit plainly.
- **Rewrite the runbook as `REBALANCE_RUNBOOK_2027-01-25.md`.** The next rebalance is dated
  **2027-01-25** (63 trading days after 2026-10-22, holidays included). Fold in every step that
  worked on 10-23, including the `--as-of` build and the dry run.
  - **Sharadar access ends about 2026-11-03.** The runbook must say that a renewal is needed before
    2027-01-25, and that this is Don's purchase decision.
- **Test it.** Run a test build end to end on the refreshed caches, compared against tonight's
  recorded book. The comparison is a fidelity check, not a new book.

## Done

On origin/main, with a plain-words summary for Don.

No key, no `.github` change, nothing appended to the record.
