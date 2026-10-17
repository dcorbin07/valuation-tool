# PROMPT — app fixer — 2026-10-16 — item 65: the auditor's last blocker, the wash-trade rejection, a readable cycle log, and the six unpriced exits

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path);
- the auditor's re-review `AUDITOR_REREVIEW_live_path_2026-10-16.md` (commit `4eb4fa6`, on main);
- your item 64 commits.

The verdict is still **NOT YET**: 7 of 8 questions pass and one route to a duplicate buy-in
survives. **Do parts 1 and 2 first; the auditor re-reviews them before any live key goes in.**

## 1. The auditor's residual: a failed order read must refuse

The route:

- the state record is lost;
- `/v2/orders` is **unreadable**;
- `/v2/positions` **is** readable.

`slot_symbols` is derived from reconcile, the recorded holdings and the recorded intent, and all
three are empty in that state. So the scope is empty, every broker position is skipped,
preflight and parity pass, and a second full buy-in transmits.

The auditor's fix is one `if`: a **FAILED** order read is the same state as a **TRUNCATED** one
("I do not know what I hold"), and the truncated case already refuses.

- Refuse and alert on a failed order read.
- Add an end-to-end test through `run_cycle` with the real client class and recorded HTTP
  responses for exactly that state. It must fail on the old code. A `slot_symbols=[...]`
  passed by hand does not count; that is why the earlier tests missed it.
- Close the auditor's notes too, or say why not:
  - the account-id pin silently does not engage when the broker returns no id;
  - the hand-typed `HOLDERS` list;
  - the 500-order page refuses rather than paginating, and fills in about 18 months.

## 2. "Potential wash trade detected. Use complex orders."

Alpaca refused one side of a name while an order rested on the other side. A book that re-prices
a remainder will hit this on real rebalances.

- Before sending an order, cancel any resting order on the opposite side of the same symbol, and
  confirm the cancel took.
- If the cancel cannot be confirmed, that name does not trade this cycle, and the cycle alerts.
- Do not use complex orders.
- Test it, and report how many of the item 64 cycles' rejections were this.

## 3. A cycle's outcome must be readable

Cycle 6's body was lost because GitHub dropped the single ~35KB line, so the two-counter fix is
unconfirmed on a real account.

- Print one short line per key field: sent, accepted, rejected with reasons, filled, held,
  refusal.
- Upload the full body as a workflow artifact.
- Hand the workflow to Don through `pending_workflows/` plus `install_workflows.bat`.
  - Check whether the pending `live-cycle.yml` schedule change is installed yet. If it is still
    pending, fold it in, so Don installs once.
- Then confirm the two-counter fix on the paper account in a market-hours cycle: distinct
  order ids across a reset, and no "must be unique" rejections.

## 4. The six hot-stock exits that were never priced (independent of parts 1–3; do it last)

The Track tab's hot-stock paper account leaves out 6 of its 29 exits:

- CNA, ABCL, BEAM, HIVE, IDYA, NUVB;
- bought 08-10 or 08-11, closed "left coverage" on 09-01 or 09-02;
- closed at their entry price, before the 2026-09-30 `price_fn` fix existed.

Re-price each one from a vendor close on its own exit date, as a **dated restatement** that keeps
the old value beside the new one. Use your own vendor, and do not copy these figures.

For reference, the manager's check from daily closes, entry day to exit day: CNA −4.5%, ABCL
+20.8%, BEAM +6.4%, HIVE +1.5%, IDYA +8.7%, NUVB +0.6%. SPY was about −1.5% over the same
window. So including them should raise the realised figure, not lower it.

On the Track tab, show "left coverage" closes separately from exits where the sell rule fired.
19 of the 29 exits are "left coverage", and those say nothing about the sell rule.

## Rules

Item 58's rules all stand:

- three events only;
- no loss stops;
- broken input means no orders plus an alert;
- no lane ever enters a key, sets a percentage or triggers a live order.

Paper only.

## Done

Tests that fail on the old code, the full suite green, all of it on origin/main, and a
plain-words summary for Don. The summary says that the auditor re-reviews parts 1 and 2 before
any live key.
