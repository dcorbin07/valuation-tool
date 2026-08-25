# DECL DRAFT — F-5: THE IV-CHEAP CONVEXITY SCREEN (fleet book #3)
## Vol vs its own history — I-2's first contact with the surface. Tag: [I-2/VIRGIN; O9-scope-distinct (that closure was index SELL-timing; this is name-level LONG-side cheapness)]

**To be committed ALONE by the options-bot lane before first fill.**

**Hypothesis:** a name whose implied vol is cheap against ITS OWN history is cheap convexity
— the long side of the own-history axis, which no register has ever pointed at vol
(`I-2`'s engine exists; `S20`/`S21`'s cross-sectional-standardiser corpses are cited and
distinct: this is a temporal percentile, an added axis, on a different object).

**Entry rule (frozen):** monthly, first trading day: rank optionable universe names by the
expanding own-history percentile (burn-in: the `I-2` engine's observation-count rule as
shipped) of their **60-DTE ATM implied vol** (live chain snapshot); buy the **5 lowest-
percentile** names, skipping any name entered in the prior 2 months (no pyramiding).

**Structure:** long call OR long put per the live composite's sign for the name (the
direction is the composite's, the cheapness is the entry — both rules frozen; a name with no
composite verdict gets a call, stated arbitrarily now so it is not chosen later); strike
nearest ATM; expiry nearest 90 DTE; hold to expiry. Entry via the F-1 randomizer.

**Universe/sizing:** optionable universe; equal premium; cap 10 open; sandbox only; `O11`
binds.

**Records:** the IV percentile at entry, the surface snapshot reference, composite sign
used, quote pair.

**Verdict horizon:** 5 fills/month by construction → **30 fills ≈ 6 months**. Meter: mean
per-trade return on premium vs 0, anytime-valid; minimum effect of interest fixed now at
**+20pp/trade** (the long-premium bleed bar — same honesty as F-3, with the `power_gate`
line at both vocabularies filled at commit).

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read.

**Void:** any cross-sectional IV comparison creeping into the entry rule (the whole point is
own-history); mid-month discretionary entries; peeking before ~30 fills without booking.

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
  "book": "f5_ivcheap",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Monthly, first trading day: rank optionable names by the expanding own-history percentile (valuation.studies.name_percentile, its shipped burn-in) of their 60-DTE ATM implied vol from the live chain snapshot. Buy the 5 lowest-percentile names, skipping any entered in the prior 2 months.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.0,
    "dte": 90,
    "right": "call or put per the live composite's sign for the name; no composite verdict -> call, stated now so it is not chosen later",
    "exit": "hold to expiry"
  },
  "universe": "optionable universe",
  "sizing": "equal premium",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 5.0,
    "min_effect": 20.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 224,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "3.7 years at the projected 5.00 fills/month (224 fills). The draft said 30 fills; 30 is a round number and this is the derivation.",
    "years_to_horizon_at_projected_rate": 3.73,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 168, reported beside it so the two vocabularies are both on the face."
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
