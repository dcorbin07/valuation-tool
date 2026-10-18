# PROMPT — app fixer — 2026-10-17 — item 70: the auditor's fifth blocker (an event closed while this slot's orders are still resting)

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), the auditor's fifth
review (`6b84008`) and your items 67–69 first. **Do part 1 before the 2026-10-22 rebalance**: the
paper slot acts on that event on its first in-hours cycle after it is appended.

## 1. The blocker: an empty plan is not "targets met"

Since item 67, the planner subtracts this slot's own resting same-side orders, so an empty plan
can now mean "my orders are still working". The close branch still reads it as "this event's
targets are already met".

The auditor reproduced three cases through `run_cycle` with the real `AlpacaPaperBroker` over
recorded HTTP:

- a resting sell that covers a whole exit;
- a resting buy that covers a whole target;
- a partial fill.

In all three, `plan_outcome=targets_met` is returned, the event closes, no alert is raised, and
nothing is retried once the `day` order expires.

**The worst case is the 0% sell-out.** The sells go out; a cycle 30 minutes later closes the event
and writes `last_pct 0.0`; the orders expire unfilled. The slot then stays **fully invested at a
declared 0%, silently, for good.**

- **An event closes only when the reconciled holdings meet the targets AND this slot has no
  resting or partially filled order for that event.** `reconcile` already computes
  `open_remainder` on every cycle, and nothing reads it. Use it. Each resting order id carries its
  event.
- **Make "orders still working" its own planner outcome.** The event stays open. There is no alert
  while the orders are fresh; the no-progress ceiling (trading days) escalates if they never fill.
  The subtraction still prevents re-stacking.
- **The latent second instance.** The `PLAN_BLOCKED` branch says "the event stays OPEN" and then
  writes `last_event_date` without setting `open_event`, so the rebalance is abandoned after one
  alert. Make it actually stay open.
- **Tests through the real client**, failing on the old code:
  - each of the three cases;
  - the 0% sell-out across a `day`-order expiry and a day boundary;
  - a re-check of item 67's `test_ACROSS_A_DAY_BOUNDARY`. The auditor showed it passes only
    because the slot had stopped acting.

## Done

On origin/main, with a plain-words summary for Don. The auditor reviews part 1 before any live key
goes in. No new pending workflow.

**Do not edit `DECISIONS.md`**. It is the manager's file, and lane edits to it block Don's
fast-forward. Put your results in `HANDOFF_appfixes.md`.
