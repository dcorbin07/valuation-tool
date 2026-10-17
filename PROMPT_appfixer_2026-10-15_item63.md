# PROMPT — app fixer — 2026-10-15 — item 63: fix the auditor's blockers in the live path

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- the auditor's review on branch `origin/worktree-auditor-live-path-review`:
  `git show origin/worktree-auditor-live-path-review:AUDITOR_REVIEW_live_path.md`. It did not
  land, because its gate ran while main was red.

The verdict: **do not enter a live key yet.** There are two blockers plus two failed questions,
none of them in the real-money rails. Verify each against the code before changing it.

## Blockers

1. **The paper slot cannot place an order.**
   - `run_slot` calls `client.place_limit(...)`, but `AlpacaPaperBroker` has `place_equity`, so
     every paper order raises `AttributeError` into a `broker_error` alert and nothing is sent.
   - All 167 tests miss it because every suite uses a stub that defines `place_limit`.
   - The cycle is installed and runs every weekday, so until this lands it alerts every day and
     the paper slot will not trade the 2026-10-22 rebalance.
   - Fix the interface. Add an integration test that hands `run_slot` the **real** paper broker
     class, with recorded HTTP responses rather than a stub. Also add a test asserting that every
     method `run_slot` calls exists on both real client classes, read from the code itself.
2. **A duplicate buy-in is reachable.**
   - `preflight` iterates the slot's own record, so an empty record compares nothing and passes
     however much the broker holds.
   - `write_state`'s return is discarded at both call sites, so a failed write after orders have
     gone produces exactly that state.
   - Fix it in three places:
     - preflight compares in both directions: any broker position carrying this slot's
       client-order-id prefix that the record lacks means **refuse plus an alert**;
     - write the intended orders **before** sending, and refuse to send if that write fails;
     - check every `write_state` result.
   - Reproduce the auditor's case in a test that fails on the old code.

## Also failed

3. **Parity (question 2).**
   - A mismatch beyond the stated 0.5% tolerance must **block a live slot's sending**. Today it
     alerts and sends anyway. Paper may still trade.
   - If the paper client is down, a live slot does not send that cycle.
   - Diff **target weights**, not order deltas, so the two slots' different fill states do not
     cause false mismatches.
4. **An unreadable position list refuses (question 7).** Today it proceeds.

## The auditor's smaller recommendations, also to do

- Record the account id the keys resolve to, and alert if it changes. Right host but wrong keys is
  otherwise invisible.
- Add a retry ceiling on re-sending an unfilled remainder, after which the slot alerts and stops
  for that event.
- Give the feed-gap pair a denominator.
- Confirm `test_no_workflow_carries_an_alpaca_credential` reads the AST rather than banning a
  substring (item 62 may already have fixed it).

## Rules

Item 58's rules all stand: three events only, no loss stops, broken input means no orders plus an
alert, and no lane ever enters a key, sets a percentage or triggers a live order.

## Done

Tests that fail on the old code, the full suite green, and **one real paper order placed and
filled on Alpaca paper through the scheduled door**, verified on the service.

Done means on origin/main, with a plain-words summary for Don. The summary must say that the
auditor re-reviews before any live key.
