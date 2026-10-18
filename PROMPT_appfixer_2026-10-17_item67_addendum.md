# PROMPT — app fixer — 2026-10-17 — item 67 addendum: the auditor's third review (`bff4532`), do this FIRST

Read `AUDITOR_REREVIEW2_live_path_2026-10-17.md` on main. The verdict is still **NOT YET**: 7 of
8 questions pass and question 6 fails for a third, different reason.

## Part 0, before item 67's parts 1 and 2

1. **A remainder re-send stacks on a resting same-side order.**
   - The auditor reproduced it end to end through `run_cycle` with the real `AlpacaPaperBroker`:
     five cycles, five full orders, 500 shares live against a 100-share target.
   - Why: holdings count fills only, the wash-trade clearing cancels only the opposite side, and
     `order_plan` re-plans the whole remainder.
   - The fix is either:
     - subtract this slot's own resting same-side quantity in `order_plan`; or
     - cancel and replace with item 65's confirmed-cancel machinery.

     Pick one and say why.
   - Add a test through the real client class that fails on the old code. Include several cycles
     inside one session, because that is what the pending schedule produces.
2. **Real cursor pagination on the order read.** One event produced 239 orders, so the 500-order
   page fills in about two events, not 18 months.
3. **Sequencing.** The pending five-cron `live-cycle.yml` is what makes the stacking routine.
   - Mark it in `pending_workflows/` with a plain **DO NOT INSTALL YET** note until part 0 is on
     origin/main.
   - Then tell Don when it is safe to double-click `install_workflows.bat`.
   - Check every other pending workflow for the same hazard.
4. **Item 67's settlement wait interacts with this.** Make sure a buy waiting on settlement is
   counted as resting or intended, so it is never re-planned on top of itself across a day
   boundary or across the extra cycles.

The auditor reviews part 0 and item 67 together before any live key goes in.
