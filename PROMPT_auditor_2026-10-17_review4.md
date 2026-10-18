# PROMPT — auditor — 2026-10-17 — fourth review of the §8 live path: item 67

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- your three reviews (`AUDITOR_REVIEW_live_path.md`, `AUDITOR_REREVIEW_live_path_2026-10-16.md`,
  `AUDITOR_REREVIEW2_live_path_2026-10-17.md`);
- item 67's commit `05f50d4` and its handoff section.

Verify against the code, using the real client classes and recorded HTTP. Read no commit message
as evidence. Your own lesson from the third review applies: reproduce a failure through the real
clients, not through a stub that raises.

1. **Your third blocker.** Does the remainder re-send now subtract this slot's resting same-side
   quantity? Check these cases end to end through `run_cycle`:
   - several cycles inside one session;
   - a resting order of unknown size;
   - an opposite-side order that is cancelled before the send.

   Then look for any other way a working order can be planned twice.
2. **Pagination:** a full page, a shared last timestamp, and a refused page must never under-count
   a holding.
3. **Settlement waits (item 67 part 1).**
   - Buys must be sized off non-marginable buying power, never margin.
   - A funds refusal becomes `awaiting_settlement`, and it cannot become a re-buy on top of
     itself across a day boundary or the extra crons.
   - The no-progress ceiling counts trading days.
   - The alert fires only after T+1 plus a trading day.
4. **The exit fix.** A name that leaves the book is now sold. It must be sold only to the slot's
   own recorded quantity, never touching Don's other holdings, and an unpriced exit must not
   fail open.
5. **Fractional reads (item 67 part 2).** Can reading `/v2/assets` or
   `/v2/account/configurations` inside the cycle change what is sent, other than by refusing?
6. **The pending `live-cycle.yml` (five crons).** Is it now safe to install? Say yes or no
   explicitly, because Don is holding it on your word.
7. Restate your eight questions' pass or fail as of today.

## Verdict

One of two, stated in the first line:

- **LIVE KEYS MAY BE ENTERED AT 0%**; or
- **NOT YET**, with the blockers named.

This is a review only: change no source file, and land the review on main.
