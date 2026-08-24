# DECL DRAFT — F-20: MARRIED-PUT STORM ENTRIES (long book + stock)
## Tag: [S10 (the book's worst peak-to-trough is one 63-day storm no name rule moves) + S28 (the headline's own distribution: 20 of 69 quarters negative) + U3-scope (the CALL overlay corpse; the put side was never an arm)]

**Entry rule (frozen):** at each monthly rebalance, IF the storm flag is on: every name
newly entering the paper index book's top decile (up to 3; composite-score tie-break, then
alphabetical) is entered as stock + put instead of plain stock. **The storm flag, frozen:**
the trailing 21-session realized vol of the paper index book's own daily series is at or
above its **own 80th percentile** over the trailing 2 years (I-2 engine; a descriptive
computation on the book's own record). Flag off → the book does nothing that month.

**Structure:** buy 100 shares + buy put, strike nearest **0.85× as-traded spot** (ties →
lower), expiry nearest above **91 DTE**. At put expiry: no roll — the position reverts to
plain stock (frozen; insurance is for the entry storm, not forever).

**Counterfactual recorded per name:** the plain-entry mark (same names, no put) so the read
prices the insurance against the drawdown it did or didn't absorb.

**Universe/sizing:** cap 6 concurrent; equal position value; sandbox; `O11` binds.

**Records:** the storm-flag inputs (vol, percentile, window), both legs' quotes,
counterfactual marks, the put's expiry outcome.

**Verdict horizon — the honest shape:** storm-gated means **possibly zero entries for
quarters at a stretch; an empty book in a calm regime is correct behavior, not failure**,
and the declaration says so. Est. fills only in elevated-vol months; the meter accrues per
entry whenever they come. Meter: mean per-entry (married minus plain) net return; **MEI
+0.50%/entry net of premium**; both vocabularies at commit.

**Verdict grammar:** INSURANCE-PAYS / COSTS / CANNOT-TELL(horizon-or-no-storm).

**Trial:** 1, options, at first verdict read. **Void:** entries with the flag off; rolling
the put; any flag input beyond the frozen three (vol, window, percentile).
