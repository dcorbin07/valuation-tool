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

---

## MACHINE-CHECKABLE DECLARATION — added at ACCEPTANCE by the options-bot lane, 2026-08-24

**The prose above is the scout's, preserved verbatim.** It carries the citations and the
corpses this book must out-select, and none of it is edited. What follows is the same book in
the form `valuation/edge/fleet.py` can ENFORCE: prose cannot be validated, and the harness
refuses a declaration it cannot read. Converting is part of acceptance, not a rewrite.

**TWO FIELDS DIFFER FROM THE DRAFT, DELIBERATELY, AND BOTH ARE HARDER.**

1. **`fills_needed` IS DERIVED, AND IT IS NOT 30.** Every draft wrote "30 fills". Thirty is a
   round number, not a derivation. The figure below is the smallest `n` at which
   `track_meter.boundary(n, sigma, rho, alpha)/n` falls to this book's OWN declared minimum
   effect — the boundary the harness actually uses. Across the fleet it runs **93 to 4,563**,
   so the drafts were optimistic by 3x to 40x. The runbook's §3 exists for exactly this:
   *"the number goes on the declaration so nobody reads a six-month book at six weeks."*
2. **`sigma` is a PRIOR unless it says MEASURED**, and `track_meter`'s rule binds: it may only
   ever be **RAISED**, never lowered. `book_meter` reports `sigma_breach` when realised
   volatility exceeds it, and a breach means the band was too narrow, not that the book did
   well.

```json
{
  "sells_premium": true,
  "side": "short",
  "assignment_model": "at expiry per moneyness, S3-I3 assignment_at_expiry",
  "margin_method": "cash_secured_put",
  "spot_basis": "as_traded",
  "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
  "return_denominator": "secured_cash",
  "book": "f4_eventfree_premium",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Every Monday: universe = optionable names that are (a) MA28 0-of-3 flags at the latest quarterly compute, (b) EVT-clean (E-4's tail flag, bottom 4 quintiles), (c) event-free -- next earnings date KNOWN via the I-4 spine AND outside [today, expiry+5 sessions]; names whose next event is UNKNOWN are SKIPPED AND COUNTED -- and (d) no S3-I2 catalyst inside the same window. Take the 3 largest by market cap not already held; alphabetical tie-break.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.9,
    "right": "put",
    "dte": 30,
    "dte_rule": "nearest 30 and strictly < 40, ties -> shorter",
    "exit": "hold to expiry; assignment per S3-I3"
  },
  "universe": "optionable, MA28-clean, EVT-clean, event-free",
  "sizing": "equal secured cash per position",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 11.0,
    "min_effect": 0.75,
    "sigma": 4.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of a 0.90-moneyness 30-DTE CSP return on secured cash. Replace with the realised SD at first read; it may move this materially in either direction.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 306,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "2.3 years at the projected 11.00 fills/month (306 fills). The draft said 30 fills; 30 is a round number and this is the derivation. A premium book's verdict needs its LOSS TAIL, so no read before 2 quarters regardless of fill count. The F-4-vs-F-10 contrast may not be quoted before BOTH books reach their horizons.",
    "years_to_horizon_at_projected_rate": 2.32,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 223, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "PAYS",
    "BLEEDS",
    "CANNOT-TELL(horizon)"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```


---

## SCOUT AMENDMENT ACCEPTED — applied at arming, 2026-08-25, options-live lane

**A NEW DATED SECTION, NEVER AN EDIT** (`PT-AMEND1`). Everything above is untouched, so the
ceremony's `--diff-filter=A` evidence that this declaration predates every line of fleet code
is intact. **It lands before this book's first fill**, which is mechanical: `verify_chain`
anchors on the declaration's CONTENT hash, so amending a book that already has records breaks
its own chain at row 0. This book has zero records.

**The scout's amendment is `AMEND_f4_eventfree_premium.md` (Frontier Scout lane, commit `6b6426f`), and it is
ACCEPTED IN FULL.** Its text is the record; this section states the operational consequence
for the harness, and nothing here reinterprets it.

**F-4 CARRIES F-13's DEFECT AND THE CEREMONY ACCEPTED IT — self-reported by the scout,
not refused by this lane.** The rule needs *"next earnings date KNOWN via the I-4 spine"*, the
spine holds no forward dates, so the next event is UNKNOWN for every name always and F-4's own
honesty clause then skips the entire universe on every cycle.

**AND IT FAILS WORSE THAN F-13 DID, WHICH IS THE PART TO CARRY.** F-13's rule is visibly
unsatisfiable and refuses loudly at arming. **F-4's is satisfiable-LOOKING and always false: it
arms cleanly, runs every cycle, places nothing, and reports `skip_rate = 1.0` — which is
indistinguishable from a quiet market in the records.** That is the same defect class this
harness has now caught three times, one level further out.

**OPERATIONAL CONSEQUENCE HERE: F-4 IS NOT ARMED AND MAY NOT BE UNTIL A ROUTE RESOLVES.** No
entry rule is registered for it. The three routes are the scout's and this lane picks none:
a daily-SNAPSHOTTED forward calendar read AS OF the entry date (recommended, and the snapshot
requirement is non-negotiable — re-reading a live calendar later is look-ahead wearing a
forward instrument's clothes), a LABELLED cadence-exclusion proxy, or withdrawal.

**`RULE_ARMED_NEVER_FIRES` IS IMPLEMENTED** as the scout proposed, so a book in exactly this
condition raises rather than reporting an empty book quietly for a quarter.
