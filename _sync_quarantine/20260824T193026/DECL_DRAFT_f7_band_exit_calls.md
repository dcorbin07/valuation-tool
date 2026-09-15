# DECL DRAFT — F-7: COVERED CALLS ON BAND-EXITING NAMES (short book, covered)
## Tag: [S14/S23 (the band's stickiness is measured; no exit rule beats never-sell — this monetizes a decided exit, it does not invent one) + U6-partial]

**Entry rule (frozen):** at each monthly rebalance of the paper index book: every name the
shipped S14 band logic marks **pending-exit** (the live band state READ from the scoring
path, never recomputed here). No discretion: all such names enter.

**Structure:** sell one call per 100 shares held, strike nearest **1.05× as-traded spot**
(ties → higher strike), expiry nearest the **next rebalance date** (ties → shorter), covered
by the paper position (the S3-I3 covered-margin case: the position is the collateral,
validated by the harness refusal test). If assigned: the assignment IS the exit the band
already decided. If unassigned at expiry and the name is still pending-exit: plain-exit at
next rebalance per the book's normal rule (frozen — no re-sell cycle).

**Counterfactual recorded per name:** the plain-exit mark (same-day close at next rebalance)
so the read compares exit-via-call vs plain-exit on identical names.

**Records:** band state proof, both legs' quotes, assignment outcome, counterfactual mark.

**S3-I3 dependency:** covered-call collateral case; assignment-as-exit settlement.
**ASSUMPTION THAT COULD SHIFT:** the interface treats covered assignment as a position
close at strike; if r1's build settles differently the counterfactual pairing re-derives.

**Verdict horizon:** est. 3–8 band-exit names per rebalance (re-stated at launch) → 30
fills ≈ **2–3 quarters**. Meter: mean per-name (call-route minus plain-route) on position
value; **MEI +0.30% per position per month**; power line at commit.

**Verdict grammar:** CALL-ROUTE-PAYS / COSTS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** selling calls on any name the band
has not marked; strike or expiry chosen off-rule; holding past the assignment-or-exit rule.
