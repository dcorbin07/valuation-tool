# PROMPT — app fixer — 2026-10-26 — item 83: the paper account went to NEGATIVE CASH on the rebalance. Buys must never borrow, on any account.

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.** Run after item 82, or alongside it if the files do not overlap.

## What Don saw

After Monday's rebalance cycles, the Alpaca **paper** account shows **negative cash**. The paper
slot sent sells at 17:30Z (run `40369206418`) and buys at 17:46Z (run `40371817752`); the 18:50Z
cycle sent nothing.

The dashboard at 2026-10-26 5:57pm ET (Don's screenshot):

- equity **$100,220.70**
- cash **−$4,759.68**
- buying power **$267,096.84**

So the book holds about **$104,980** of stock on $100,221 of equity: **about 4.75% borrowed**.
The buying power at roughly 2.7× equity confirms a margin account.

## The likely cause (verify it; do not trust it)

`settlement.spendable()` sizes buys from `non_marginable_buying_power`, on the premise that it is
"spendable without borrowing". **On a margin account that premise is false.** Alpaca's own sample
account object (docs.alpaca.markets/us/docs/account-plans) reads:

- `cash` −23,140.20
- `non_marginable_buying_power` +7,386.56
- `multiplier` 4

The paper account is a margin account. So a buy budget taken from that field can spend more than
the cash on hand. That is most likely to happen when some of the 17:30Z sells had not filled by
17:46Z.

The live slot is Don's Alpaca IRA. Alpaca IRAs are limited margin (1x) and Alpaca extends no
credit in them, so the IRA should refuse rather than borrow. **That rests on Alpaca's
documentation and has not been observed.** It also means the paper rehearsal is NOT a faithful
test of how cash behaves in the IRA.

## The fix

1. **Measure first.** From the two cycles' saved bodies and artifacts, and a read-only account
   read:
   - the paper account's `multiplier`, `cash`, `non_marginable_buying_power` and `buying_power`
     before and after;
   - the budget each buy was sized from;
   - which sells had filled by 17:46Z;
   - how large the debit is now.

   State the cause plainly. If it is not the one above, say what it is.
2. **A buy may never spend more than cash, on any account type.**
   - The budget is at most `cash`, after open buy orders are reserved, whatever the margin
     fields say. A negative cash reads as zero, so nothing is bought.
   - One definition, in `settlement.py`. The existing AST guard must still prove no other line
     reads a buying-power field.
   - Test with Alpaca's documented sample above: the budget must be **0**, not 7,386.56. Test a
     multiplier-1 account where the two fields agree too.
3. **Fix the paper account's current state without borrowing more.**
   - Say whether the next cycle restores cash to zero or above by itself: for example, does it
     trim back to 100% of equity?
   - If it does not, propose the smallest fix and wait for Don's yes before any extra sell.
   - Report how far the paper book is now off the Index weights because of the debit.
4. **Check the live slot reads the same rule.** Report the IRA's `multiplier` and fields from a
   read-only account read at 0%. No order, and the percentage stays 0.
5. Ask the auditor lane to re-check this one change before anyone raises the live percentage.
   Report this; do not do it.

## Done

On origin/main, with a plain-words summary for Don:

- why cash went negative, and by how much;
- whether the IRA could ever overdraw, now and before the fix;
- what happens to the paper account next.

No key printed, no percentage changed, no live order, no `.github` change, nothing appended to the
record.
