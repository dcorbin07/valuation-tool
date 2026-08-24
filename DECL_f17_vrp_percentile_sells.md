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
  "book": "f17_vrp_percentile_sells",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "First Monday of each month: universe = names passing F-4's cleanliness rules verbatim AND event-free per F-4's window rule, EXCLUDING any name F-4 or F-10 entered or could enter that week (priority F-4 > F-17 > F-10, stated in all three). Compute each name's own-history percentile (valuation.studies.name_percentile) of the 30-day VRP = ATM 30-DTE implied vol minus trailing-21-session realized vol. Enter the top 3 with percentile >= 90; fewer qualify -> fewer enter.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.9,
    "right": "put",
    "dte": 30,
    "exit": "hold to expiry"
  },
  "universe": "optionable, clean, event-free, VRP percentile >= 90",
  "sizing": "equal secured cash",
  "concurrency_cap": 5,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 3.0,
    "min_effect": 0.75,
    "sigma": 4.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of a 0.90-moneyness 30-DTE CSP return on secured cash. Replace with the realised SD at first read.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 306,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "8.5 years at the projected 3.00 fills/month (306 fills). The draft said 30 fills; 30 is a round number and this is the derivation.",
    "years_to_horizon_at_projected_rate": 8.5,
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
