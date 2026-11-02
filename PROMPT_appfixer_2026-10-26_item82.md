# PROMPT — app fixer — 2026-10-26 — item 82: the daily live check fails on a correct 81-name book

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.**

## What happened

`LIVE CHECK` run #31 (2026-10-26 19:32 UTC, run id `40387659164`) **failed** and posted to
#valquo-alerts. Runs #26–#30 had passed.

The likely cause, measured from the outside (verify it from the run's log or artifact):

- `scripts/live_check.py::check_index` asserts `n_positions >= 85`.
- Since the 2026-10-22 rebalance the book in force holds **81** names, and it conforms.
- The contract's own floor is 50 (`CONTRACT_MIN_POSITIONS`), and conformance passed when the
  rebalance was recorded.
- So the check fails on a correct book. It will fire on both weekday runs until fixed, which
  teaches Don to ignore #valquo-alerts.

## The fix

1. **Read run #31's log or uploaded report first.** List every FAIL line. If anything other than
   "Index holds 85+ names" failed, fix that too, or report it plainly if it is real.
2. **Replace the hard-coded 85 with the contract's own rule, from one definition.**
   - The checker is stdlib-only and imports only `market_session`. Either:
     - check a conformance verdict the public `/api/valquo-index` payload already carries, or adds; or
     - import the floor from a stdlib-only module that defines it once.
   - Never retype 50, and never type 81.
   - The check must still fail on a truncated book. Use the same rule the rebalance door
     enforces.
3. **Add a test** that fails on today's code with an 81-name conforming payload and passes after
   the fix. Also show that a payload below the floor still fails.
4. Grep `live_check.py` and the other monitors (rebalance watch, alert routing) for any other
   hard-coded count of the old 86-name book.

## Done

On origin/main, with a one-line summary for Don. The next scheduled LIVE CHECK must pass.

No key, no `.github` change, nothing appended to the record.
