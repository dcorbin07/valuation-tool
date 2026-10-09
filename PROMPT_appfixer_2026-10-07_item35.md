# PROMPT — app fixer — 2026-10-07 — item 35

Read `DECISIONS.md` first.

Verified live 2026-10-07: all seven themes contribute (institutional 0.85, insider 0.86), the
single-stock routing holds, exports work, daily-doors runs green, and the live check reads 27
passed / 1 failed / 1 skipped. Two things remain, and the first is the one Don has asked about
three times.

## (a) The Dip Detector still shows almost nothing — and the live check was changed to accept it

Live: at min_drawdown 0.10, **218 names qualify, 12 are valued, 2 rows show** (AGI, KSPI); at
0.20, 165 qualify, 12 valued, 3 rows. Item 34(a) asked to value every qualifying name AHEAD of
time (in the nightly pipeline, or by reusing the scan's own fair values and health) so the screen
serves the full qualifying set. That was not done: the budget was raised to 18, measured as
buying nothing, and reverted. Meanwhile the live check's dip assertion now reads "PASS dip spends
its budget on qualifying names — 12 of 218 qualifiers valued, 206 reported as capped". **A check
that passes on the broken state is the defect item 30 exists to prevent.**

Do it properly: precompute the dip valuation for every name the nightly scan marks as qualifying
at the slider's floor (0.10), cache it beside the snapshot, and have /api/dip serve from that
cache, so a request never spends a live valuation budget. Report how long the precompute takes
inside the scan job and confirm it fits. Then change the live check to assert the real property:
at 0.10, rows shown + names rejected by checks + names rejected on health == names qualifying,
with nothing silently capped. Verify live at 0.10, 0.20 and 0.30 and report the three counts.

## (b) The live check's evening run fails on a row that is not due yet

The 02:15 UTC run on 2026-10-07 failed "Index track has the last session: no row for 2026-10-06"
— but track-row.yml writes a session's row the NEXT morning (cron 03:07 UTC, typically delivered
09:00-11:00 UTC). Require the last session's row only after 12:00 UTC on the following day;
before that, require the session before it. A daily false alarm teaches everyone to ignore the
check.

## Not needed: the token list in your last report

/admin/score-alerts and /admin/record-dip-rejects run every weekday via daily-doors.yml (green on
10-06 and 10-07); the dip-span invalidation was applied by Don on 2026-10-03/04; and the bound
record has been seeded and writing daily since August, so `seed_track --send` is not a pending
action. Remove these from your "needs Don" list, or say exactly why any one of them is still
needed.

Done means on origin/main, verified live, and a clean live-check run reported.
