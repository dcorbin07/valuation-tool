# PROMPT — r1 — 2026-10-07 — addendum 2 (batch 3)

The scout's `PREREG_DRAFT_stage1_batch3.md` landed (nine arms, C1-C9). Two changes to your queue:

1. **Fold batch 3's columns into your ONE rebuild** if you have not built it yet (or, if you
   already have, say so and do not rebuild just for this). Read the draft for every source column
   each arm needs — including `capex` (in the raw export, dropped by the loader allowlist; the
   scout measured the identity as `capex = fcf - ncfo`, with Sharadar storing capex as a NEGATIVE
   outflow — pin that sign) and C9's four (`liabilities`, `assetsc`, `workingcapital`, `retearn`).
   Add them to `_KEEP` with coverage confirmed (the COVERAGE RULE), so no batch-3 arm is later NOT
   RUN for a missing column. Adding columns must leave every existing figure bit-identical — prove
   it by leaf diff.
2. **After batch 2, execute batch 3** the same way (executor review and amendments BEFORE any
   outcome, register ALONE, trials booked before any runner, kills in their own pass, build quadrant
   only, the $10B tier governing). B4 stays NOT RUN unless a tier-level IBES coverage census — a
   different population from the 0.69999551 full-universe figure — clears the inherited 0.70; never
   read 0.69999551 as a pass.

The canonical move (addendum 1) still comes after items 1-4 of your original prompt; batch 3 may
run after it.
