# DECL DRAFT — F-4: EVENT-FREE SHORT-TENOR PREMIUM (short book)
## Tag: [EVOWN-inverse (ambient at 45–75 → only <40 DTE can avoid events; the structural finding stands regardless of EVOWN's NOT-DEMONSTRATED strategy verdict) + V6-OPT-inverse (flags that DO discriminate) + A3-hostile (selling richer vol lost −7.99%/trade — the standing corpse this book must out-select)]

**Entry rule (frozen):** every Monday (first trading day of week): universe = optionable
names that are (a) **MA28 0-of-3 flags** at the latest quarterly compute, (b) **EVT-clean**
(E-4's tail flag, bottom 4 quintiles), (c) **event-free**: next earnings date known via the
I-4 spine AND outside [today, expiry+5 sessions] — **names whose next event is UNKNOWN are
SKIPPED and counted** (coverage honesty; code-22 runs 1.65 events/ticker-yr) — and (d) no
S3-I2 catalyst inside the same window. Rank eligible names by highest own-history IV
percentile is NOT used (that is F-17); take the 3 largest by market cap not already held
(frozen tie-break: alphabetical).

**Structure:** sell cash-secured put, strike nearest **0.90× as-traded spot** (ties → lower
strike), expiry nearest **30 DTE and strictly < 40** (ties → shorter). Order at bid via the
F-1 randomizer's sell-side arms. Hold to expiry; assignment per S3-I3.

**Universe/sizing:** cap 10 open; equal secured cash per position; sandbox only; `O11`
binds.

**Records:** both flag states with compute date, the event-check proof (next-event date +
source), quote pair, secured cash, S3-I3 assignment outcome.

**S3-I3 dependency (r1 building now — written to the harness register §1.4 interface):**
cash-secured denominator; expiry assignment per moneyness; early-assignment FLAGGED not
simulated. **ASSUMPTION THAT COULD SHIFT:** if the build settles on a margin-requirement
denominator instead of full cash-securing, every return and the MEI below re-derive
mechanically (scale only, not design).

**Verdict horizon:** est. 8–15 eligible entries/month (descriptive projection, re-stated at
launch from a 30-day count) → 30 fills ≈ 1 quarter, **but a premium book's verdict needs its
loss tail: earliest honest read 2 quarters**, declared. Meter: mean per-trade return on
secured cash vs 0, anytime-valid; **MEI +0.75%/trade on secured cash** (both power
vocabularies via `power_gate.state()` at commit).

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon). The paired design fact, stated
now: **F-10 runs the same cleanliness rules at standard tenor with events ambient — the
F-4-vs-F-10 contrast is the fleet's own forward measurement of what event-avoidance is
worth**, and neither book may quote that contrast before both reach their horizons.

**Trial:** 1, options, at first verdict read. **Void:** delta-targeted strikes; any
event-window override; unknown-event names entered.
