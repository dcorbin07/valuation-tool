# PROMPT — Frontier Scout — 2026-10-16 — what is still worth testing to find an options edge

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path), `IDEAS_LEDGER.md`,
`SEASON3_MAP.md` and `HANDOFF_optionsbot.md` sections 80–90 first.

Don, in chat on 2026-10-16: *"I really do want to find one. Maybe not use the same DTE for every
trade? I'm willing to do just about anything as long as it isn't super expensive."*

**You draft; you do not run.** Every draft gets a free kill condition first, a priced trial
count, and an honest prior. If the evidence says an idea is closed, say so; do not dress up a
re-run of the dead alert entry. Any draft that would read a check window already seen says so in
its §0.

Constraint: Don's Alpaca IRA is options **Level 2**:

- allowed: long calls and puts, cash-secured puts, covered calls;
- not allowed: spreads.

Fidelity, Schwab and tastytrade allow IRA spreads. Prefer Level-2 designs, and flag any design
that needs another broker.

## Draft these

1. **EARNINGS-CSP.** Sell a cash-secured put shortly before a scheduled announcement, expiring
   shortly after, and hold it to expiry.
   - The evidence for it is O7: earnings implied moves are rich on this universe (5.45% implied
     against 4.78% realised; the move beat the implied only 35% of the time). It has never been
     tested from the selling side.
   - Separate it explicitly from what is closed or already declared:
     - the killed calendar spread (O-SEED-5);
     - O9;
     - F-4, which deliberately avoids events.
   - Price the costs at one crossing.
   - Name the gap stress.
   - Use a random-day twin on the same names at the same tenor.
   - Use the EOD chain freeze and the code-22 spine; 29 foreign issuers have no earnings dates.
2. **A STRESS GATE FOR PUT SELLING, judged forward.**
   - SELL-PREMIUM-2's check window, including COVID, has been seen, so a gate tuned on 2016–2025
     cannot be confirmed on it.
   - Draft it as a forward twin of F-21 (an F-21b) on a rule taken from published work and fixed
     before any look, for example a VIX term-structure or market-trend rule. Say which, and why.
   - Use the build quadrant only if it is unseen for this question.
3. **O-1's data question, as a census only.** The option market prices about half of the crash
   risk the accounting flags carry (1.5x implied against 3.0x realised), and O-1 was underpowered
   at 74 flagged trades.
   - How many flagged name-dates have listed options?
   - How much put-chain history does a test need to reach its own power floor?
   - What would that pull cost? No purchase.
4. **The DTE question, answered from the record in plain words for Don.** Use:
   - O13 (expectancy rose with tenor on both the alert and the random-day book);
   - O17's DTE quartiles;
   - EVOWN;
   - SC-3;
   - F-4 (30 DTE) against F-10 (52 DTE).

   Then say whether any DTE design is untested and worth a register, on the long side or the
   short side.

## Then rank

Rank everything still open on the options side by expected value against cost, and name in one
line each what is closed, so nobody re-runs it.

## Done

Drafts committed on your branch and landed, with a plain-words summary for Don:

- the ranked list;
- the one thing you would test first;
- what it costs in trials and in dollars.
