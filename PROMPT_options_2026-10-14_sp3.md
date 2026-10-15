# PROMPT — options lane — 2026-10-14 — SELL-PREMIUM-3: test it as drafted

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy
may be out of date; the 2026-10-14 SELL-PREMIUM-3 entry), the scout's draft
`PREREG_DRAFT_sellpremium3.md` (`a1d37ff`), and your handoff sections 84, 86 and 87b first.

Don reversed the shelving: SELL-PREMIUM-3 (the same dip entries as a 25-delta put credit spread,
long leg at 7.5% of spot) is to be tested **as drafted**.

## The disclosure the register must carry

The check quadrant is not blind to this book. SELL-PREMIUM-2's corrected stage 2 already read the
same entries' short legs there (−0.4258%/trade, the loss in 2020, 2022-2026 positive, twin sign test
z +12.53). The draft's construction predates that read: `a1d37ff` is 2026-10-13 18:18 and the first
stage-2 commit `a525fa6` is 20:05. **Verify both from git and state them in the register.** Then say
plainly what follows: a stage-2 pass here would be consistent with the draft, not a blind
confirmation, because a capped version of a book whose loss sat in one known crash is predictable.

## Amendments: correctness only

Each amendment is named, and justified without reference to any check-quadrant figure.

1. **The repaired settlement for BOTH legs.** Use `settlement_spot` with the required
   `max_stale_days`, and `spot_maps` with years taken from the trades. Refusals are counted. A test
   must fail on the old era-import code.
2. **The hurdle derived from the live options `N`**, never the draft's 319.
3. **Measured where the draft forecast.** The draft's own void condition 6 applies: `K3` and every
   return come from measured net credit, not §3's Black-Scholes table.

Nothing else moves: one width (7.5% of spot), 25 delta, the tenor band, hold to expiry, and the
shares sold in the middle band (exercising the long put is refused). `K3-POS` stays at 6.0 with the
synthetic row, and `K3-ACCT` stays at 35%. The expectations are scored exactly as written.

## Order

1. **§8 first: Roth IRA spread permissions, from the brokers' own published pages** (quote, URL,
   date). Tradier and Robinhood are out per DECISIONS.
   - If every candidate clearly refuses, stop before the arm. Zero trials are booked.
   - If it cannot be settled from published pages, record it as UNRESOLVED for Don and continue.
2. **Commit the register ALONE.** It states the stage-2 bars now, so no second register is needed.
   Then **book the 4 options trials** before any runner exists.
3. **`K1` on the two-leg strike rule.** The floor is 1,200 priceable events and 300 covered days;
   stop below it.
4. **`K3-POS` and `K3-ACCT` in their own pass.** The arm runner refuses to start without a passing
   artifact.
5. **Stage 1: `B1`-`B4` on the build quadrant**, the same population SELL-PREMIUM-2's stage 1 used.
   - The twin is a spread twin at the identical width rule, five seeds, sign test on dollars, with
     pooled means reported beside it.
   - The account table covers $10k, $25k and $50k on the one repaired current-equity sizing loop.
     Only the 35% cap rows are offered configurations.
6. **If stage 1 passes, the one stage-2 read** on SELL-PREMIUM-2's stage-2 population: kills again
   in their own pass, read ONCE. If stage 1 fails, stop and say so.

## Rules and done

Report in the three-state vocabulary, with each verdict's MDE beside it. Paper only: nothing is
adopted, no orders are placed, and `O11` binds.

Check landing once after each push, with no wait loops. Done means on origin/main, with a
plain-words summary for Don. The summary must say whether a broker allows this in his Roth.
