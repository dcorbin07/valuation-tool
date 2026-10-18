# PROMPT — app fixer — 2026-10-17 — item 68: the seam measurement ran to completion and did not pass — explain both failures

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your items 62, 64
and 65 part 5 first. **Nothing switches. Alpaca stays off the Index price path for the 2026-10-22
rebalance**, and the next segment boundary is the January rebalance.

Don's run completed on 2026-10-17 at 03:10Z, after he regenerated the stale paper keys (the
earlier 401). It covered 217 names and 58,318 bars, with 215 names compared and coverage 95.5%.

- **Daily closes on the declared `all` basis: 0.9020 against the declared 0.98. FAIL.**
  - The as-traded leg agrees at **0.9915** (57,824 of 58,318).
  - The worst rows:

    | ticker | date | Alpaca | yfinance |
    |---|---|---|---|
    | CTVA | 2025-12-03 | 64.87 | 9.73 |
    | AZN | 2025-09-12 | 78.21 | 157.48 |
    | APTV | 2025-11-20 | 59.53 | 70.28 |
    | UL | 2025-11-11 | 63.63 | 67.04 |
    | HAFN | 2026-06-03 | 7.038 | 7.311 |
- **Against the recorded Index series: FAIL, and it never ran.** The reason given: *"the benchmark
  SPY could not be priced on the inception 2026-07-30"*.

## 1. The recorded-series leg cannot pass as built

- Find out why SPY could not be priced on 2026-07-30. The manager's guess is that SPY, and perhaps
  the bound book's own names, are not in the 227-name pull.
- Make the pull include **SPY and every name in every bound-book segment since inception**, so
  this leg can run at all.
- Report whether it then passes.

## 2. Explain the adjusted-basis gap, by cause

Classify every disagreeing bar by cause:

- dividend-adjustment convention;
- spin-off (UL/Magnum, APTV, CTVA are candidates);
- listing or ADR change (AZN is a candidate);
- symbol reuse;
- a genuine wrong price on either side.

Say which vendor is right in each class, where that is knowable.

## 3. Which basis does the bound Index record actually use?

The record's own convention decides which comparison matters. Do not change the declared 0.98
bar or the declared basis after seeing this result. If the declared basis is the wrong comparison
for the record, say so, and put the choice to Don as a new, separately declared measurement.

Include what a vendor switch would do to the record's seam given these conventions. A switch is a
price-vendor change, not a vintage event, but a convention change is still a seam.

## Done

On origin/main, with a plain-words summary for Don: why it failed, whether Alpaca is wrong or only
different, and whether a January switch is worth preparing for. No switch, no opt-in, and no
change to the record.
