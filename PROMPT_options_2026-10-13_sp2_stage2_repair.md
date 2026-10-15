# PROMPT — options lane — 2026-10-13 — SELL-PREMIUM-2 stage 2 is VOID: repair the settlement, re-run

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy
may be out of date; 2026-10-13, the SELL-PREMIUM-3 entry) first.

## The defect (found by the manager on `SELLPREMIUM2_STAGE2_BOOK.pkl`; verify it, do not take it on trust)

`scripts/sellpremium2_stage2.py` settles both the arm and the random-day twin through
`A2M.spot_maps(...)` imported from `scripts/sellpremium2_arm.py`, which builds each ticker's spot map
over `SP.era_years()` plus one year — STAGE 1's era, 2016-2020. `SP.settlement_spot` then returns
"the last session at or before the expiry" with no staleness limit. So every trade expiring after
2020-12-31 settled against that ticker's LAST 2020 PRICE:

- implied settlement on every assigned post-2020 trade: GE $10.80 (15 of 15), AAPL $132.69 (17 of
  17), CLS $8.07, HWM $28.54, NVDA $522.20 — each ticker's 2020-12-31 close;
- of the 177 tickers with two or more assigned post-2020 trades, all 177 settle at ONE price;
- 73% of the 4,522-trade book expires after 2020; the 1,220 trades expiring in 2020 are settled
  correctly (mean −2.78%, 33.5% assigned).

Recover the implied settlement as `strike − (bid − ret_pct/100 × strike)`. This is why late beat
early for losses in a bull market, and why the twin lost almost exactly as much: both used the same
stale map. `K3` reads premium income and is unaffected.

## What to do, in order

1. **Fix it at the root, with a test that fails on the old code** (GE expiring 2025-09-26 must not
   settle at $10.80): spot maps built from the years the trades actually span, and
   `settlement_spot` REFUSING a settlement whose last available session is more than a stated
   number of sessions before the expiry, with refusals counted rather than dropped silently.
2. **Census every caller** of `spot_maps`, `era_years`, `settlement_spot` and `spot_by_date` for the
   same era mismatch — `DIP-CALL`'s stage 2, the sizing-fix script, the F-4/F-10 cheap step, and
   anything else — and say which landed figures move. Stage 1 should be unaffected (its maps cover
   its own era); show it.
3. **Re-run stage 2 exactly as registered, with only the settlement repaired.** This is a correctness
   repair of the one check read, not a second look (the `U1-SPLIT` precedent): construction, bars,
   arms, seeds and halves unchanged, zero new trials. Edit SELL-PREMIUM-2's research-log cell in
   place to say the first stage-2 verdict was void and why, then give the corrected verdict, the
   full sizing table, and returns and assignment by year. Correct section 87 of your handoff the
   same way.
4. **Say what follows:** if SELL-PREMIUM-2 now passes stage 2, SELL-PREMIUM-3 (shelved on the void
   result) goes back to Don; if it fails, say so plainly.

Paper only; nothing adopted; no real trades. Done means on origin/main, with a plain-words summary
for Don.
