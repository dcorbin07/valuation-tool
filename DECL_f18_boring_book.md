# DECL DRAFT — F-18: THE BORING BOOK (short book, buy-write)
## Tag: [V6-OPT + A3-hostile (both corpses quoted by every premium book) + E-3-null-honesty: theme dispersion FAILED as an equity IC signal and is reused here only as a dullness SCREEN input — a null signal can still describe, and the declaration says so rather than hiding the provenance]

**Entry rule (frozen):** first Monday of each month: rank the optionable universe by a
frozen dullness composite = the mean of two percentile ranks: (a) LOW cross-theme
dispersion (E-3's banked column definition, ≥4 computable themes), (b) LOW own-history
realized-vol percentile (I-2 engine, trailing-21-session realized vol vs own history).
Hard filters first: MA28 0-of-3 AND EVT-clean AND event-free per F-4's window rule. Take
the **5 dullest** (alphabetical tie-break), skipping names already held.

**Structure:** buy-write — buy 100 shares + sell the call at strike nearest **1.05×
as-traded spot** (ties → higher), expiry nearest **45 DTE** (ties → shorter). At expiry:
assigned = done; unassigned = re-write per the same rule while the name still qualifies at
the monthly recompute, else sell the shares at close (all frozen).

**Universe/sizing:** cap 5 concurrent buy-writes; equal position value; sandbox; `O11`
binds.

**Records:** both dullness components and the composite rank, flag states, event proof,
both legs' quotes, re-write count.

**S3-I3 dependency (harness §1.4):** covered-call collateral case (shares are the margin).
**ASSUMPTION THAT COULD SHIFT:** if the covered case nets legs differently than
position+short-call, the return denominator re-derives.

**Verdict horizon:** 5 names, monthly cycles → **2 quarters** to the first honest read
(fill count printed). Meter: mean monthly net return on position value vs 0; **MEI
+0.50%/month on position**; both vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** any dullness input beyond the two
frozen components; delta-targeted strikes; holding an unqualified name past its exit rule.

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
  "assignment_model": "at expiry per moneyness; covered assignment closes the position at strike, S3-I3 assignment_at_expiry",
  "margin_method": "covered_call",
  "spot_basis": "as_traded",
  "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
  "return_denominator": "secured_cash",
  "book": "f18_boring_book",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "First Monday of each month: hard filters first -- MA28 0-of-3 AND EVT-clean AND event-free per F-4's window rule. Rank the survivors by a frozen dullness composite = mean of two percentile ranks: (a) LOW cross-theme dispersion (E-3's banked column, >=4 computable themes), (b) LOW own-history realized-vol percentile. Take the 5 dullest; alphabetical tie-break; skip names held.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.05,
    "right": "buy-write: long 100 shares + short call",
    "dte": 45,
    "exit": "assigned -> done; unassigned -> re-write while the name still qualifies at the monthly recompute, else sell the shares at close"
  },
  "universe": "optionable, clean, event-free, dullest 5",
  "sizing": "equal position value",
  "concurrency_cap": 5,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 5.0,
    "min_effect": 0.5,
    "sigma": 5.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of a monthly buy-write net return as a %% of position. Replace with the realised SD at first read.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 1202,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "20.0 years at the projected 5.00 fills/month (1202 fills). The draft said 30 fills; 30 is a round number and this is the derivation. The longest horizon of any accepted book. It is on the face precisely so nobody reads it early; E-3's dispersion column is reused here as a descriptive DULLNESS input and its equity-IC NULL is not disturbed.",
    "years_to_horizon_at_projected_rate": 20.03,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 784, reported beside it so the two vocabularies are both on the face."
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
