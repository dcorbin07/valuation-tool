# PROMPT — auditor — tenth review of the live path, after item 83 (a buy may never spend more than cash)

**Start only once item 83 (`a7807d9`) is on origin/main.** If it is not, stop and say so. Do not
edit `DECISIONS.md`.

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), your ninth review
(`fb78445`) and item 83's commit.

## Why

Your ninth review said "safe to raise above 0% when Don chooses". On 2026-10-26 the **paper**
slot then borrowed $4,760 (4.75% of equity) on the rebalance. Buys were sized from
`non_marginable_buying_power`, which on a margin account is not cash: Alpaca's own sample reads
cash −23,140.20 against that field at +7,386.56. Item 83 changed the rule: the buy budget is now
cash minus open buys, and negative cash reads as zero.

## Check, with the real client classes and production's own arming

1. **Can any buy now spend more than cash, on any multiplier?** Cover:
   - an account read that fails or omits fields;
   - an open buy order that cannot be valued;
   - partial fills;
   - buys and sells in one cycle;
   - a deposit or withdrawal mid-event;
   - the IRA's limited-margin 1x.
2. **Does capping at cash stall a rebalance in the IRA?** Sells resting while buys wait: do the
   cash-wait and settlement-wait states, the no-progress ceiling and the alerts behave as
   designed?
3. **The paper self-heal trim.** Item 83 says the next cycle trims about $4,760 because targets
   sum to equity. Can that same trim logic ever sell, in a live slot, a holding the slot did not
   buy, or sell into a debit loop?
4. **Did anything in your ninth review rest on the old sizing rule?** Restate your questions as
   of today.

## Verdict

One of two, stated in the first line:

- **SAFE TO RAISE ABOVE 0% WHEN DON CHOOSES**; or
- **NOT YET**, with the blockers named.

This is a review only: change no source file, and land the review on main.
