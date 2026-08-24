# DECL DRAFT — F-11: DIP-REJECT PUTS (long book)
## Tag: [V6-B (the mechanism: rejects fall a further 20% some 10.2pp more often, HAC t −10.5847, both halves, 4–5× its own MDE — the strongest unconsumed separation in the record) + V6-OPT-scope (that corpse sold puts on the HEALTHY side; this buys them on the failing side) — B-10 is the freeze twin and neither gates the other]

**Entry rule (frozen):** daily: the live dip-detector REJECT list (down ≥20% from the 252-
session high AND failing the shipped health floors — the live classification READ, never
recomputed). Enter within **2 sessions of a name's FIRST appearance** on the list this
quarter; skip names already held or entered this quarter.

**Structure:** buy put, strike nearest **0.80× as-traded spot** (ties → lower), expiry
nearest above **91 DTE**. Hold to expiry, no exits. Entry at ask via the F-1 randomizer.

**Universe/sizing:** optionable rejects; cap 10; equal premium; sandbox; `O11` binds.

**Records:** the dip stats (drawdown, days since high), the failing floor values, quote
pair, first-appearance date.

**Verdict horizon — regime honesty:** dip frequency is the market's to give: est. 5–20
qualifying entries/quarter in normal tape, near zero in a melt-up (re-stated at launch from
a trailing-90-day count). **1–3 quarters to 30 fills, regime-dependent, and the book may
starve in calm markets — starving is data, not failure.** Meter: mean per-trade return on
premium vs 0; **MEI +25pp/trade**; both vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** entering HEALTHY dips (that is the
V6-OPT corpse's side); re-entry within a quarter; any exit rule; delta-targeting.

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
  "book": "f11_dip_reject_puts",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Daily: the dip-detector REJECT population -- names down >=20%% from the 252-session high that FAIL the shipped health floors, classified by the screen's own published functions valuation.web.dip.health_check and dip.clamp_drawdown on the same rows the live screen uses (the classifier is published; only screen()'s aggregation discards the failures). Enter within 2 sessions of a name's FIRST appearance this quarter; skip names already held or entered this quarter.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.8,
    "right": "put",
    "dte": 91,
    "dte_rule": "nearest above 91",
    "exit": "hold to expiry, no exits"
  },
  "universe": "optionable dip REJECTS",
  "sizing": "equal premium",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 4.0,
    "min_effect": 25.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 138,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "2.9 years at the projected 4.00 fills/month (138 fills). The draft said 30 fills; 30 is a round number and this is the derivation. Dip frequency is the market's to give: near zero in a melt-up. STARVING IS DATA, NOT FAILURE, and the fill count is printed.",
    "years_to_horizon_at_projected_rate": 2.88,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 107, reported beside it so the two vocabularies are both on the face."
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
