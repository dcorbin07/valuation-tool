# PROMPT — app fixer — 2026-10-09 — item 46: the fleet has never filled an order

Read `DECISIONS.md` first.

Your item 45 found, across all 18 record streams in the 2026-10-04 service backup: 16 of 18 books
contain nothing but self-checks, and f3_bear_puts — the only book with orders — has 72 of them
(2026-08-26 to 2026-10-03), every one `fate=working` with `fill_price` and `venue` empty. Not one
filled order in the fleet, ever, and the Tradier deactivation is not the cause (the sandbox token
is alive).

This is a defect to diagnose before it is anyone's decision. Find out, from the code, the service's
records and the fleet-cycle runs (not by assumption):

1. **Why the 16 books never placed an order.** For each: did its declared entry rule ever fire,
   was it refused (and for what recorded reason), or is it not being run at all?
2. **Why f3's 72 orders never filled.** Are they limit orders the sandbox never fills, day orders
   that expire and are re-placed, fills that happen but are never polled and recorded, or
   something else? Check one order end to end against the sandbox's own order status (read-only).
3. **Whether the fleet-cycle job runs when it should** and what each run did.

Fix what is a plain defect (a fill that happened but was never recorded, a cycle that never runs).
Do NOT change any book's declared rules, fill source or order type — those are part of the book's
declaration; report what would have to change and why, for Don. Remember the records are
append-only: never edit or backfill a past row.

Done means on origin/main, verified on the service, with a plain-words summary for Don.
