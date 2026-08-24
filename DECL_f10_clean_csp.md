# DECL DRAFT — F-10: CLEAN-NAME CSPs AT STANDARD TENOR (short book)
## Tag: [V6-OPT (its closure's own reasoning: health floors didn't discriminate — MA28's flags DO, 3.04×/5-of-5, so selling where crash risk is measurably ABSENT is the un-closed inverse) + MA28-CARD + A3-hostile (the corpse quoted in full: alert-day credit spreads lost −7.99%/trade; this book's answer is selection, not structure)]

**Entry rule (frozen):** first Monday of each month: universe = optionable names MA28
0-of-3 AND EVT-clean (bottom 4 quintiles), **no event filter — deliberately** (EVOWN
measured ownership AMBIENT at this tenor; this book accepts events as they come, and the
F-4 contrast is the point). **Excludes any name F-4 entered or could enter that week**
(cross-book dedup frozen HERE, self-contained — no harness dedup assumed). Take the 3
largest eligible by market cap not already held (alphabetical tie-break).

**Structure:** sell cash-secured put, strike nearest **0.90× as-traded spot** (ties →
lower), expiry nearest **52 DTE** (ties → longer — squarely in the ambient-event band).
Hold to expiry; assignment per S3-I3.

**Universe/sizing:** cap 10; equal secured cash; sandbox; `O11` binds.

**Records:** flag states, quote pair, secured cash, any event that lands inside the holding
window (stamped from the I-4 spine at expiry — recorded ex post as a label, never used as a
rule).

**S3-I3 dependency (harness §1.4):** cash-secured denominator; expiry assignment;
early-assignment flag. **ASSUMPTION THAT COULD SHIFT:** the denominator convention (rescales
MEI mechanically).

**Verdict horizon:** est. 3/month by construction → 30 fills ≈ **10 months at cap; ~2
quarters to the first honest loss-tail read** — earliest read declared at 2 quarters with
the fill count printed. Meter: mean per-trade return on secured cash vs 0; **MEI
+0.75%/trade**; both vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon) — and the F-4 contrast is quoted
only after BOTH books' horizons, per F-4's declaration.

**Trial:** 1, options, at first verdict read. **Void:** delta-targeting; event-filtering
(that is F-4's design); entering F-4-eligible names.

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
  "book": "f10_clean_csp",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "First Monday of each month: universe = optionable names MA28 0-of-3 AND EVT-clean (bottom 4 quintiles), NO event filter deliberately. EXCLUDES any name F-4 entered or could enter that week (cross-book dedup frozen here, self-contained). Take the 3 largest eligible by market cap not already held; alphabetical tie-break.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.9,
    "right": "put",
    "dte": 52,
    "dte_rule": "nearest 52, ties -> longer",
    "exit": "hold to expiry"
  },
  "universe": "optionable, MA28-clean, EVT-clean, events ambient",
  "sizing": "equal secured cash",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 3.0,
    "min_effect": 0.75,
    "sigma": 4.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of a 0.90-moneyness 52-DTE CSP return on secured cash. Replace with the realised SD at first read.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 306,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "8.5 years at the projected 3.00 fills/month (306 fills). The draft said 30 fills; 30 is a round number and this is the derivation. At 3 fills/month this is the fleet's slowest short book. The F-4 contrast reads only after BOTH horizons.",
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
