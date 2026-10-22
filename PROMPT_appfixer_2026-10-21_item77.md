# PROMPT — app fixer — 2026-10-21 — item 77: the auditor's eighth review — three blockers before any percentage above 0

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path). **Do not edit
  `DECISIONS.md`.**
- The auditor's eighth review, commit message on `origin/worktree-auditor-live-path-review`.

Every reproduction it describes becomes a test that fails on today's code.

The live slot is at 0% and holds nothing, so none of this can hurt Don today. All three must be
fixed before he raises a percentage.

**Do not land between Friday 2026-10-23 4pm ET and the 10-22 rebalance being recorded that night.**

## Blocker A — a missing or misnamed percentage variable is read as 0% and sells the book

`slot_pct` returns `0.0, stated=False` for an absent value, and `armed` never reads `stated`. The
auditor reproduced it three ways: the variable removed, empty, and misspelled (`_PCT` instead of
`_LIVE_PCT`). Each one transmitted the sells.

- **A wind-down requires `stated=True`.** An absent, empty or unparseable percentage on a slot
  that holds positions refuses, sends nothing, and alerts in plain words, for example: *"slot 1
  has keys but no ALPACA_ACCOUNT_1_LIVE_PCT; nothing will trade until it is set."*
- **Alert on any `ALPACA_ACCOUNT_<n>_*` variable whose suffix is not a known one**, so a misspelling
  is named rather than silently ignored.
- Correct `slot_pct`'s docstring to what the code does.

## Blocker B — each percentage event works only once

`event_key` names a percentage event `pct:<from>-><to>` with nothing to tell occurrences apart.
The auditor's two failures:

- 0→5%, 5→0%, then 5% again is refused for ever.
- The dangerous one: after 5→0% has been processed and a rebalance has re-established positions,
  setting 0% again places nothing and sends **no alert**, while the dashboard reads 0%.

The fix:

- A new percentage change after a completed event is a NEW event: make each occurrence's key
  distinct, for example with a sequence number.
- A restart must still never repeat the SAME occurrence.
- Setting 0% while this slot holds its own positions must always sell them out, or refuse and
  alert. Never silently nothing.

## Blocker C — a price move inside an open event still trades the difference

Item 73 froze the dollar TARGETS, but the gap is `frozen_target − held_qty × CURRENT mark`. Inside
an open event, for example a cash wait, a price rise therefore plans sells: self-funding churn
that breaks Don's three-events rule.

**The rule to enforce:** inside an open event, the only sells are the ones planned when the event
opened (exits and resize-downs), and buys only top up toward the frozen targets. A price move
between cycles never creates a new sell or a bigger buy. Freezing target **quantities** at event
open is one way to get there; choose the design and prove it with the auditor's four-price test
(100/130/70/300).

`LIVE_MIN_TOPUP` keeps gating buys.

## Non-blocking, fix in the same item

- An order that never fills, sitting alongside a cash gap, must still reach the no-progress
  ceiling and escalate.
- Prune `frozen_targets` to the open event, so the map doesn't grow for ever.

## Tests

- Add every auditor reproduction to item 71's transition table, using the real client classes and
  recorded HTTP. Each must fail on today's code.
- Prove the paper slot is unaffected except where these rules bind.

## Done

- On origin/main, with a plain-words summary for Don.
- No key, no percentage, no arming change, and no `.github` change.
- Then the auditor does review 9.
