# PROMPT — app fixer — 2026-10-18 — item 73: spread buys proportionally, keep a cash shortfall open, and top up only in useful amounts

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your items 67–72
first. **Do not edit `DECISIONS.md`.** This changes the live path, so the auditor reviews it before
any percentage above 0.

## Don's rulings (chat, 2026-10-18)

Example: a $10,000 account, 50%, so a $5,000 Index target, with only $2,000 in cash.

1. **Buys are spread PROPORTIONALLY, never filled stock by stock.**
   - Today the buys are taken in plan order until the no-borrow budget runs out (the loop after
     `SETTLE.spendable` in `run_slot`). That leaves the first names at full size and the rest at
     zero.
   - Instead, after the sells, scale every buy by the same fraction:
     `f = min(1, spendable / total buy cost)`. With $2,000 against $5,000, every name is bought
     at 40% of its gap.
   - Names whose scaled order falls under `min_order_value` are skipped and stay in the gap.
2. **The shortfall stays OPEN until it is filled or the next event replaces it.**
   - The gap is measured against **that event's own per-name targets, frozen when the event
     opened**. It is NOT re-derived from today's equity. Otherwise this becomes daily drift
     trading, which Don's three-events rule forbids.
   - When new cash appears, the next cycle tops up proportionally toward those frozen targets.
     It never goes past them, and never sells anything this slot did not buy.
   - A new rebalance or percentage change replaces the open gap with its own targets.
3. **No cash budget or cap.** Don rejected it: a "spend up to $X of outside cash" rule resets when
   the cash is spent and spends the next $X. The slot simply uses whatever spendable cash exists,
   up to its frozen targets.
4. **Don't fire 86 tiny orders for every small deposit.** A top-up happens only when the
   uninvested gap's fillable amount is at least a threshold, and the shortfall waits otherwise.
   - Default **$250**, set by ONE environment variable, **`LIVE_MIN_TOPUP`**, that applies to
     every live slot and to the paper slot alike (so parity still compares like with like). There
     is no per-account variable; Don chose one universal setting on 2026-10-18. Don can change it
     on Render.
   - Smaller names lagging behind, because their share of a top-up is under `min_order_value`, is
     accepted by Don. They stay in the gap and catch up on a later top-up.
   - A malformed value refuses and alerts, as `LIVE_PCT` does.
   - The first fill of a new event is not held back by the threshold.

## Waiting for cash is a normal state, not a failure

Today a gap with no cash runs into the no-progress ceiling: it alerts and closes the event after 5
trading days.

- Add a declared **"waiting for cash"** outcome. It keeps the event open, sends nothing, and alerts
  Don **once** in plain words, for example: *"$3,000 of the Index target is waiting for cash; it
  will be bought automatically when cash is available."*
- It does not re-alert every cycle and does not burn the ceiling.
- The ceiling still applies to orders that are sent and never fill.

## Cost, which Don asked about

Report the measured cost of a $1,000 top-up across the book on the paper account: the number of
orders, the fill price against the mid, and any fees (Alpaca charges no commission, and regulatory
fees apply to sales only). Put it in the summary.

## Tests

Use the real client classes and recorded HTTP, and add the cases to item 71's transition table:

- a partial cash buy-in spread proportionally;
- a later deposit topping up to the frozen targets and no further;
- a deposit under the threshold waiting;
- a new event replacing an open gap;
- an ETF Don holds by hand never sold or counted;
- no daily re-sizing when prices move between events.

Each must fail on the old code.

## Done

On origin/main, with a plain-words summary for Don. No new pending workflow, and no key or
percentage touched.
