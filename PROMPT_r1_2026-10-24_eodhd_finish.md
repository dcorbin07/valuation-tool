# PROMPT — r1 — 2026-10-24 — EODHD: finish the harvest, and close out what is left

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.** The licence fence and key rules from `PROMPT_r1_2026-10-22_eodhd.md` still apply,
unchanged.

## Where things stand, from your own commits

| Step | Status | Commit |
|---|---|---|
| 1. Census | Done | `c31262e` |
| 2. Harvest | Earnings calendar, insider and most market cap banked (6,150 of 6,150 units verify). The full fundamentals pass (~9,705 names, about one day's allowance) was **still running** at your last report. | `3d82e32`, `4adab40` |
| 3. Cross-vendor check | **GO, by zero names of margin** (50 of 82 top-decile names overlap; 50 is the minimum) | `4adab40` |
| 4. 1999–2008 out-of-sample replication | Dead on both sides: the panel has no rows before 2009, and EODHD's pre-2009 dead companies are empty | `4adab40` |

Nothing has landed from you since `4adab40` (2026-10-23 01:10 UTC). The EODHD plan runs about a
month from 2026-10-22, so anything it is needed for must finish well before about 2026-11-20.

## Work, in order

1. **Finish and verify the harvest.**
   - Resume the fundamentals pass; do not restart it.
   - Verify the whole freeze against its manifest: units, checksums, zero mismatched, zero absent.
   - Report the final counts, by feed.
   - The weekly market cap (2021 onward only) is low value. Finish its remainder only from spare
     allowance.
2. **Decide whether a 2009–2026 second-vendor replication is worth a register.** Step 4's
   out-of-sample half is dead; the build-era half was never closed.
   - Measure feasibility for free first: dated EODHD coverage of the panel's cells, per date, on the
     rows a replication would score.
   - Say plainly what it could show. Prices would still be Sharadar's and the period is the same
     one the model was tuned on, so it tests vendor independence of the fundamentals only. It is
     not out-of-sample.
   - If feasibility clears a bar you fix before looking, draft the blind register, commit it ALONE
     and book the trials first. Do not run the arm in this item.
   - If it does not clear, say so and stop.
3. **`tracelead` K1, before WRDS script access lapses (about 2026-11-03).**
   - One connection, one attempt, never a retry loop.
   - If access has already lapsed, say so in one line and leave it.
4. **OSAP `EquityDuration`.** Retry the download once. If the Google Drive quota still blocks it,
   say so and leave it.
5. **Hand-offs.** Confirm that the forward earnings-calendar finding (dates to 2027-11-19) reached
   the options lane with the licence fence attached. Report it; do not act on it.

## Rules

- Key read from the environment, never printed. Raw rows only under `D:\eodhd\` and `D:\wrds\`.
- Nothing from EODHD reaches valquo.co, the public repo, `data_export/` or any public page.
- No trades, nothing on Render, nothing in `.github`.
- Nothing is adopted and no vendor is switched. Those are Don's decisions.
- Do not raise Sharadar renewal. Don has ruled on it (`DECISIONS.md`, 2026-10-24).

## Done

On origin/main, with a plain-words summary for Don. It must say whether anything still needs the
EODHD subscription once the harvest is verified.
