# PROMPT — app fixer — 2026-10-07 (evening) — item 37

Read `DECISIONS.md` first.

## (a) Intraday signals and the GitHub scheduler

You found no Auto-scans run had been created between 03:43 and 17:03 UTC on 2026-10-07. The live
/api/signals now reads run_time 2026-10-07 19:28, so the scheduler delivered late rather than
never. Measure how often this happens: over the last 30 days, how many of the intraday crons
(`23 13-20 * * 1-5`) produced a run, and on how many sessions did zero runs land before 17:00 UTC.
If dropped or late runs are routine, write a backup schedule (offset minutes, the way the hot list
already has one) as `data/pending_workflows/auto-scan.yml` for Don to install with
`install_workflows.bat` — lanes cannot change `.github/`. Report the numbers either way.

## (b) HOLD until DECISIONS.md records Don's ruling

- The Dip Detector's handling of banks, insurers, REITs and regulated utilities (health
  sub-score withheld, counted as a failure, 31 of 110 health rejections).
- The public pages (/proof, /methodology, landing tiles).

Done means on origin/main, verified live.
