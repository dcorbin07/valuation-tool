# DECL DRAFT — F-17: OWN-HISTORY VRP-PERCENTILE SELLS (short book)
## Tag: [O2-scope (the XS-VRP audit closed an implementation, cross-sectionally) / O9-scope (index sell-TIMING) — the name-level OWN-HISTORY VRP percentile is VIRGIN; I-2 is the engine. A3-hostile carried: selling richer vol lost — this book's answer is that "rich vs ITSELF" is a different conditioning than "rich vs the market," and the fleet will say if that answer is wrong.]

**Entry rule (frozen):** first Monday of each month: universe = optionable names passing
F-4's cleanliness rules verbatim (MA28 0-of-3, EVT-clean) AND event-free per F-4's window
rule, **excluding any name F-4 or F-10 entered or could enter that week** (cross-book dedup
frozen here, self-contained; priority F-4 > F-17 > F-10 is stated in all three). Among the
remainder: compute each name's own-history percentile (I-2 engine, its shipped burn-in) of
the **30-day VRP** = ATM 30-DTE implied vol minus trailing-21-session realized vol (owned
closes; a descriptive input). Enter the **top 3 by that percentile** with percentile ≥ 90
(fewer qualify → fewer enter; alphabetical tie-break).

**Structure:** sell cash-secured put, strike nearest **0.90× as-traded spot** (ties →
lower), expiry nearest **30 DTE** (ties → shorter). Hold to expiry; assignment per S3-I3.

**Universe/sizing:** cap 5; equal secured cash; sandbox; `O11` binds.

**Records:** the VRP components and percentile, flag states, event-check proof, quote pair,
secured cash.

**S3-I3 dependency (harness §1.4):** cash-secured denominator; expiry assignment; early-
assignment flag. **ASSUMPTION THAT COULD SHIFT:** denominator convention (rescales MEI).

**Verdict horizon:** ≤3/month → **2 quarters to the first honest loss-tail read** (fill
count printed). Meter: mean per-trade return on secured cash vs 0; **MEI +0.75%/trade**;
both vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon) — and the F-4 comparison (same
cleanliness, VRP-conditioned vs unconditioned) reads only after both horizons.

**Trial:** 1, options, at first verdict read. **Void:** cross-sectional VRP ranking
anywhere in the rule; delta-targeting; entering F-4/F-10-claimed names.
