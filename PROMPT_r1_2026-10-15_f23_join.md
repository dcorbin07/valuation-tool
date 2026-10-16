# PROMPT — r1 — 2026-10-15 — repair the SEC ticker join, then re-run F23-SECID as registered

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your F23-SECID
commit `f712be2` first. Do not touch app files.

## Why

F23-SECID did not clear. Your own commit shows the SEC-sourced cell measured a **different
population** from the one registered: 608 tickers against SF2's 1,344, sharing only 335, with a
point-in-time market cap resolved for 48.1% of events against 83.3%. You ruled out blank symbols
and traced it to the **join between the SEC's `ISSUERTRADINGSYMBOL` and the corrected panel**.

That is an instrument defect, not a property of the rule. The same join is what F-23's live feed
would use, so it has to be fixed before F-23 can ever fill, whatever this check says.

## Do

1. **Repair the join.** Prefer a CIK-to-ticker mapping that is valid on each filing date (SEC
   CIK to the panel's own identifier) over the trading symbol as filed.
   - Report the before-and-after ticker overlap with SF2 and the market-cap resolution rate.
   - Pin the repair with a test that fails on the old join.
2. **Re-run the registered F23-SECID check unchanged** on the build quadrant only: same arms,
   bar, null, halves, clusterings, costs and BH.
   - This is a correctness repair of the same read (the `U1-SPLIT` and SELL-PREMIUM-2 repair
     precedent), so **no new trial**.
   - Edit the F23-SECID research-log cell in place: the first read was on a broken join, and
     here is the corrected one.
   - Change nothing else. If the repaired cell still does not clear, F-23 stays declared and
     unfilled, and no variant is searched for.
3. **If it clears,** follow your F23-SECID register's own clearing branch:
   - move F-23 to the ID rule through the harness amendment route;
   - check the live SEC feed against the rule on a recent window;
   - give Don the one step, if any, that clears the fleet self-check block.

Paper only. Done means on origin/main, with a plain-words summary for Don.
