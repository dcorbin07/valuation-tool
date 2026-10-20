# PROMPT — auditor — after item 73 lands — eighth review of the §8 live path

**Start only once item 73 is on origin/main.** If it is not, stop and say so. Do not edit
`DECISIONS.md`.

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), your seventh review
and item 73's commits.

Item 73 changes how buys are sized:

- proportional scaling to spendable cash;
- a shortfall kept open against **frozen** event targets and topped up as cash appears;
- a top-up threshold;
- a "waiting for cash" state that does not burn the no-progress ceiling.

Check, with the real client classes and production's own arming:

1. **Can a top-up ever buy past the frozen event targets,** including across a new deposit, a
   price move, a split, or an event replacing the gap?
2. **Can the slot ever spend cash by selling, or touch** a holding it did not buy?
3. **Can "waiting for cash" hide a real failure,** such as an order sent and never filled, a
   refused buy that is not a cash shortage, or a malformed threshold?
4. **Does any of it re-introduce daily drift trading** between events?
5. Restate your eight questions as of today.

## Verdict

One of two, stated in the first line:

- **SAFE TO RAISE ABOVE 0% WHEN DON CHOOSES**; or
- **NOT YET**, with the blockers named.

This is a review only: change no source file, and land the review on main.
