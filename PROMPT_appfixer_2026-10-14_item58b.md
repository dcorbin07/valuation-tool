# PROMPT — app fixer — 2026-10-14 — item 58b: finish the live path and the paper switchover

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), your item 58 commit
`fb92ce8` with its "NOT BUILT YET" list, and §8 / §8a of `PAPER_TRACK_CONTRACT.md` first.

## First, item 57 A4 did not reach the page — fix it before anything else

The manager measured this live on MSFT on 2026-10-14. The company panel still prints
"$3,962,939,637,760" and "$331,839,000,000", because `app.js` lines ~500-501 still call
`money(p.market_cap * 1e6, 0)` and `money(p.revenue * 1e6, 0)`. A4 fixed `mcap()`, but these two
lines never use it. The growth-lens sentence (~line 649) has the same defect:
`money(gl.revenue_at_horizon, 0)` + "mm" printed "$395,246mm".

- Route all three through `mcap()` (×1e6 where the value is in $mm), so they read $3.96T,
  $331.84B and $395.25B.
- Sweep `app.js` for any other `money(` call on a value of $1M or more, and fix those too.
- Add a test that fails on the pre-fix lines, and verify it live on MSFT before moving on.

## Then the live path

Item 58 shipped the safety core (`alpaca_broker.py`, `live_slots.py`, §8a, the auditor prompt),
and nothing calls it yet. Build the rest, in this order.

1. **Confirm Don's paper keys are on Render.**
   - Add an owner-only status that says, for the paper keys and for each discovered slot, whether
     the variables are present. It never shows a value.
   - If the paper keys are missing, tell Don in your summary, give him the exact Render steps
     again, and stop before step 4.

2. **The cycle runner.** One service-side door ties discovery, preflight, targets and orders
   together, called by a scheduled workflow exactly as `fleet-cycle.yml` calls its door.
   - Fractional orders are `day` limit orders, so it runs during market hours. Pick the time and
     say why.
   - It acts only on the three events: a new rebalance event on the bound record, a percentage
     change since the last cycle, and re-sending that event's unfilled remainder.
   - It records which events each slot has already processed, so a restart never repeats an
     order.
   - Any failed preflight means no orders for that slot, plus an alert.

3. **A paper slot running the identical code.**
   - It is slot `paper`, on the Alpaca paper client, at 100% of the paper account, mirroring the
     same Index book through the same runner.
   - This is how the live path gets proven with real (paper) orders before any real money, and
     it is the "paper book" every live slot's dry run diffs against.
   - Start it now. Its first buy-in is today's book in force, and it then trades the 2026-10-22
     rebalance, so Don can watch a full rebalance go through on paper first.

4. **Switch the existing paper books from the Tradier sandbox to Alpaca paper**: the fleet books,
   the options paper book, the paper-trade door and the fleet self-check.
   - Record a dated switch event on each book.
   - Use the harness's amendment route wherever a declaration's frozen wording names the broker.
   - Then run one real Alpaca paper fill through the self-check.

5. **Dry-run parity for live slots at 0%.**
   - Each cycle, a live slot computes the orders it would place for its own account's equity and
     diffs them against the paper slot's orders, scaled to the same equity.
   - Show the diff in the status and log it.

6. **Alerts and status.**
   - Alerts go through the existing alert route for: a failed preflight, an unfilled remainder
     after the close, a slot frozen by a broken input, and any live order sent.
   - The owner-only status shows every slot's holder, percentage, armed or not and why, its next
     event, what it would trade, and its last parity diff. It explains in words how pause
     (`LIVE_PILOT_ENABLED=0`, sells nothing) differs from 0% (sells out).

7. **Feed-gap measurement** on the first 30 Alpaca paper fills: recorded mid against fill price,
   stock and option separately.

8. **Dividends for paper books.** Paper pays none, so any paper book or the paper slot holding
   through an ex-date credits them from a named source, or states the omission.

## Rules

Item 58's rules all stand:

- the three-event behaviour;
- no loss stops;
- broken input means no orders plus an alert;
- slot discovery and holder authorization;
- separation;
- no lane ever sets a percentage, enters a key, or triggers a live order.

Do not touch item 59's price-source work.

## Done

- Tests for each piece, and the full suite green.
- The paper slot's first buy-in filled on Alpaca paper, verified on the service.
- Slot 1 shown at 0% with a parity diff once Don's live keys exist. Without them, shown as "no
  keys yet".

Done means on origin/main, with a plain-words summary for Don. The summary must tell him that
the auditor review (`PROMPT_auditor_live_path.md`) runs next, and that live keys wait for it.
