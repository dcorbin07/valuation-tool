# PROMPT — app fixer — 2026-10-08 — item 39

Read `DECISIONS.md` first.

## (a) The engine's 52-week high came back empty for every name in the last scan

Your item-38 verification found the engine produced a 52-week high for NOT ONE name in the
2026-10-07 scan, so item 36's fallback is carrying the whole Dip screen. Live now at 0.20:
172 qualified, 73 unmeasured, 16 rows — down from 24 rows the day before. Find the cause (your
hypothesis was the per-name history call being throttled from the runner's IP — confirm or refute
it from the scan log, not by assumption), fix it at the source, and make a recurrence LOUD: the scan
should print how many names got a 52-week high from the engine, and the live check should fail if
that count is zero while names qualify — the fallback must not be able to hide a dead primary.
Verify live at 0.10 / 0.20 / 0.30 and report rows before and after.

## (b) Intraday reliability — WAIT for Don's ruling in DECISIONS.md

Your item 37 measured 72.2% of intraday cron slots producing no run. Don is deciding between a
paid Render cron and staying on GitHub. Do nothing on this until DECISIONS.md records his choice.

## (c) Public pages — still held until r1's canonical move lands (item 38b).

Done means on origin/main, verified live.
