# PROMPT — app fixer — 2026-10-18 — item 72 (low priority): the auditor's seventh-review leftovers

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and the auditor's
seventh review (`4d6f09e`) first. **Do not edit `DECISIONS.md`.**

The auditor cleared live keys at 0%, and Don has entered them. `/admin/live-slots` on 2026-10-18
03:09Z reads:

- slot 1 present, both keys present, `pct` 0.0;
- paused, not armed, holds nothing;
- isolation ok (no clash with the paper keys).

None of the items below can move a share. Do them before Don raises any percentage.

1. **The stale `open_event` message.** The auditor found that an event left open with nothing
   resting refuses with a reason claiming orders ARE working, and that the refusing branch returns
   before the no-progress ceiling.
   - The paper slot shows exactly this shape right now: `open_event: rebalance:2026-07-30` while
     `processed_events` already contains `rebalance:2026-07-30`, with 82 holdings recorded.
   - Fix the sentence so it says what is true.
   - Let a stale open event clear itself, or escalate, rather than hold silently.
   - Explain why the paper slot holds 82 names and not the book's full count.
2. **The combinations nobody has checked**, per the auditor:
   - an exhausted event crossed with modes and reads;
   - a quiet cycle;
   - an UPWARD resize;
   - a brand-new record;
   - a new book superseding an open percentage event.

   Add them to item 71's table and fix any row that is wrong.
3. **Watch the paper slot's 2026-10-22 rebalance** (its first real book change) on the first
   in-hours cycles after the event is appended on the evening of 10-23. Report in plain words:
   - sells first;
   - any settlement waits;
   - exits priced and sold;
   - whether the event closes only when the holdings match.

## Done

On origin/main, with a plain-words summary for Don. No new pending workflow, and no change to any
percentage or key.
