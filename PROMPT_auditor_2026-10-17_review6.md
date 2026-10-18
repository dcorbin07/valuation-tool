# PROMPT — auditor — after item 70 lands — sixth review of the §8 live path

**Start only once item 70 is on origin/main.** If it is not, stop and say so.

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), your five reviews and
item 70's commits first.

1. **Your fifth blocker.** Reproduce your three cases end to end through `run_cycle` with the real
   client class: the resting sell covering an exit, the resting buy covering a target, and the
   partial fill. Also reproduce the 0% sell-out across a `day`-order expiry.
   - An event must close only when holdings meet the targets and no order of this slot's is
     working.
   - Check the `PLAN_BLOCKED` branch really keeps the event open.
2. **Search for any other planner or close outcome** that can still record an event complete
   while the slot is not at its targets. Questions 6 and 7 have each failed for a new population
   several times, so look for the next population before it is found by a real rebalance.
3. **Confirm the installed workflows** match the pending ones on main, after Don's `git pull` and
   reinstall.
4. Restate your eight questions' pass or fail as of today.

## Verdict

One of two, stated in the first line:

- **LIVE KEYS MAY BE ENTERED AT 0%**; or
- **NOT YET**, with the blockers named.

This is a review only: change no source file, and land the review on main. Do not edit
`DECISIONS.md`.
