# DECL DRAFT — F-8: CSP ENTRY FINANCING (short book)
## Tag: [U6-partial + V6-OPT-scope (that corpse sold puts on DIP names gated on health; this sells puts only on names the book has ALREADY decided to buy — assignment is the plan, not the risk)]

**Entry rule (frozen):** at each monthly rebalance: every name **newly entering the paper
index book's top decile** (the shipped selection, read not recomputed), up to **cap 5**
(frozen tie-break if more qualify: highest composite score, then alphabetical).

**Structure:** sell cash-secured put, strike nearest **0.95× as-traded spot** (ties →
lower), expiry nearest **30 DTE** (ties → shorter). If assigned: the assignment is the
book's entry, done. If unassigned at expiry: re-sell per the same rule up to **3 cycles**,
then market-buy (all frozen — no judgement at execution time).

**Counterfactual recorded per name:** the plain-entry mark (same-day close at the original
rebalance) so the read prices the financing route against just buying.

**Records:** entry-decision proof, quote pair, cycle count, assignment outcome, secured
cash, counterfactual mark.

**S3-I3 dependency (harness §1.4 interface):** cash-secured denominator; expiry assignment;
early-assignment flagged. **ASSUMPTION THAT COULD SHIFT:** denominator convention (margin
vs full cash) rescales returns and the MEI mechanically.

**Verdict horizon:** est. 3–6 new entrants per rebalance (re-stated at launch) → 30
completed name-cycles ≈ **2–3 quarters**. Meter: mean per-name (CSP-route minus
plain-route) total entry cost; **MEI +0.50% of position per entry**; power line at commit.

**Verdict grammar:** FINANCING-PAYS / COSTS (the missed-rally case is exactly what the
counterfactual catches) / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** entries on names the book did not
select; a fourth cycle; delta-targeted strikes.
