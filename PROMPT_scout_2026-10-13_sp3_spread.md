# PROMPT — scout — 2026-10-13 — make the strategy that passed usable at a real account size

Read `DECISIONS.md` and `HANDOFF_optionsbot.md` sections 84 and 86 first.

SELL-PREMIUM-2 (cash-secured 25-delta puts on the dip events) is the first options strategy in this
project to pass every leg of Don's rule: +0.67% per trade on secured cash, 87% wins, beats its
random-day twin at z +9.9, survives sizing, clears the unrelaxed crash bar. But it earns about
1-2% a year at a realistic account size because it cannot deploy: at $25k it skips 2,060 of 2,610
trades, since one contract secures more than $2,500.

Design only, committed per the usual rules (draft, no measurement, no trials):

1. **SELL-PREMIUM-3: the same entries with less capital per trade.** The obvious candidate is a
   25-delta put credit spread (defined risk, so the capital tied up is the width minus the credit).
   Draft it as a legitimate successor: the entry events, the short leg and the tenor unchanged;
   say how the long-leg rule is chosen BEFORE any outcome; restate the crash bar for a capped loss
   without relaxing what it protects; and require the account-size table at $10k, $25k and $50k as
   a reported leg. Include the costs a second leg adds (two crossings in, two out unless left to
   expire), and whether the twin control still means the same thing. State as a fact to check, not
   an assumption, which brokers allow spreads in a Roth IRA. If no long-leg rule survives the cost
   and crash arithmetic on the measured income, say so and do not draft an arm.
2. **F-15 (insider clusters):** the options lane measured that the inputs exist and the expression
   is the problem (a 60-DTE at-the-money call prices a ±14.6% move). Say in a paragraph whether any
   expression is worth a register, or whether the signal belongs on the stock side.

Plain-words summary for Don of what the spread would change and why. Done means on origin/main.
