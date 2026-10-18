# PROMPT — app fixer — 2026-10-17 — item 71: the auditor's sixth review (three blockers), and a full transition table so a seventh review finds nothing new

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and the auditor's sixth
review, `AUDITOR_REVIEW6_live_path_2026-10-17.md` (commit `439eef1`; on main once its land
completes, otherwise read it from `origin/worktree-auditor-live-path-review`). Read your item 70
first. **Do not edit `DECISIONS.md`.**

## The three blockers, verified in your own reproduction before any fix

**A. The X→0 sell-out cannot execute on a live slot. It is Don's documented way out.**

- `armed()` refuses at pct ≤ 0, so no live client is built, so a slot holding positions at a
  declared 0% can never sell them. pct = 0 means both "never traded" and "still holding", and
  `armed` cannot tell them apart.
- Arm a **sell-only** mode when the slot's own record holds positions and pct = 0. It sells only
  the slot's own recorded quantities and never buys. Keep the global pause (`LIVE_PILOT_ENABLED=0`)
  exactly as it is: it pauses without selling.
- Fix `armed`'s false refusal text.
- Test it through the real client with a live-host fixture. Production withholds `armed_state` and
  the client at 0%, so a test that passes either of them in by hand does not count.

**B. A second event closes the first event's remainder.** The close branch clears `open_event`
unconditionally. Clear it only when it is the event being closed. Test the auditor's route:

1. buy-in sent, nothing filled;
2. Don sets 0% mid-session;
3. the sell-out closes;
4. the resting buys fill.

The slot must never hold shares at a declared 0% with both events recorded complete.

**C. The close fires on a read that was never attempted.** In `?run=paper` and dry modes, a live
slot has `order_read = not_attempted`. The close branch still writes state, so every scheduled
paper cycle can close a live slot's events. A GET of `/admin/live-cycle` also writes state.

- A slot whose order read was not attempted computes a plan and writes **nothing**.
- A GET writes nothing for any slot.

## Then: one transition table, so the next review stops finding the next population

Six reviews have each found a new state the close or send logic mishandled. Instead of a seventh
patch, enumerate every combination below and pin the expected outcome for each in one table-driven
test, through `run_cycle` with the real client classes and recorded HTTP.

- **Slot state:**
  - fresh;
  - holding;
  - holding with resting orders (same side, opposite side, partial);
  - mid-event.
- **Event:**
  - rebalance;
  - 0→X;
  - X→Y;
  - X→0;
  - two events overlapping inside one session.
- **Read outcomes:** ok, truncated, failed, not_attempted, for orders, positions and quotes
  separately.
- **Mode:** live (`?run=1`), paper, dry, GET.
- **Pilot:** `LIVE_PILOT_ENABLED` 0 or 1.

For each combination, pin what is sent, what is written, whether the event stays open or closes,
and whether Don is alerted. Every row the code handles differently from the table is a defect,
fixed here. Report how many rows the table has and how many were wrong before this item.

## Done

On origin/main, with a plain-words summary for Don. The auditor reviews it before any live key.
No new pending workflow.
