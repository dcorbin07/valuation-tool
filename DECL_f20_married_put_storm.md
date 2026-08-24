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
  "sells_premium": false,
  "side": "long",
  "book": "f20_married_put_storm",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "At each monthly rebalance, IF the storm flag is on: every name newly entering the published paper index book (up to 3; composite-score tie-break then alphabetical) is entered as stock + put instead of plain stock. STORM FLAG, frozen: the trailing 21-session realized vol of the paper index book's own daily series is at or above its own 80th percentile over the trailing 2 years. Flag off -> the book does nothing that month.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.85,
    "right": "married put: long 100 shares + long put",
    "dte": 91,
    "dte_rule": "nearest above 91",
    "exit": "at put expiry the position reverts to plain stock; NO roll"
  },
  "universe": "names newly entering the published paper index book during a storm",
  "sizing": "equal position value",
  "concurrency_cap": 6,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 1.5,
    "min_effect": 0.5,
    "sigma": 3.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of the paired married-minus-plain net return as a %% of position. Paired on the SAME name, so far tighter than an unpaired per-trade SD (MB8).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 395,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "21.9 years at the projected 1.50 fills/month (395 fills). The draft said 30 fills; 30 is a round number and this is the derivation. STORM-GATED: possibly ZERO entries for quarters at a stretch. An empty book in a calm regime is CORRECT BEHAVIOUR, not failure.",
    "years_to_horizon_at_projected_rate": 21.94,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 282, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "INSURANCE-PAYS",
    "INSURANCE-COSTS",
    "CANNOT-TELL(horizon-or-no-storm)"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
