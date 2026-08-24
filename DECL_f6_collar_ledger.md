# DECL DRAFT — F-6: THE UTILITY COLLAR LEDGER (fleet book #4)
## Insurance priced honestly, claimed as nothing. Tag: [U3-scope (the CALL overlay was the corpse; the PUT side was never an arm); DEEPITM-FIN's cards for the financing frame]

**To be committed ALONE by the options-bot lane before first fill. CLASSIFICATION: UTILITY —
no edge claim, and (pending Don's Q5 confirmation on the map) NO trial charge: this book
measures the COST of a service, not a hypothesis about returns.**

**Purpose:** run zero-cost collars on the paper index book's top-3 weights and record what
protection actually costs — the drag, the caps hit, the puts that paid. The deliverable is a
standing honest ledger of insurance economics on this book, the input Don needs the next
time a drawdown makes protection feel urgent (buying insurance during the storm is the
expensive reflex; this ledger prices the calm).

**Entry rule (frozen):** at each monthly rebalance, for the index book's top-3 positions:
buy the put nearest 0.90× as-traded spot, sell the call whose premium most nearly finances
it (nearest-to-zero net cost, never a net credit), both ~90 DTE, sized to the paper
position. Roll at expiry. Assignment and margin per the harness short-book module (the call
leg is covered by the paper position by construction — stated, and validated by the
harness's refusal test).

**Records:** net cost at entry, both legs' quotes, cap events (calls breached), floor events
(puts in the money at expiry), the per-quarter drag.

**Verdict horizon:** none in the edge sense — it reads QUARTERLY as an audit (the first read
is descriptive, not a verdict). If Don ever wants "was the insurance worth it" answered as a
hypothesis, that is a separate declaration with a meter and a charge; this one deliberately
is not it, and saying so here is what keeps it free.

**Trial:** 0 proposed (UTILITY class — Don confirms on map Q5; if he rules it charges, it
charges 1 options at first quarterly read and nothing else changes).

**Void:** any performance claim from this book anywhere; a net-credit collar (that is a
different structure with a different risk); real money.

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
  "book": "f6_collar_ledger",
  "domain": "options",
  "hypothesis_class": "utility",
  "entry_rule": "At each monthly rebalance, for the paper index book's top-3 weights read from the published data_export/paper_track_holdings.csv: buy the put nearest 0.90x as-traded spot and sell the call whose premium most nearly finances it (nearest-to-zero net cost, NEVER a net credit), both ~90 DTE, sized to the paper position. Roll at expiry.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.9,
    "dte": 90,
    "right": "collar: long put + short covered call",
    "exit": "roll at expiry"
  },
  "universe": "the paper index book's top-3 weights",
  "sizing": "one collar per paper position",
  "concurrency_cap": 3,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 3.0,
    "min_effect": 0.3,
    "sigma": 3.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of quarterly collar net drag as a %% of position. Replace with the realised SD at first read.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 1202,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "33.4 years at the projected 3.00 fills/month (1202 fills). The draft said 30 fills; 30 is a round number and this is the derivation. UTILITY: it reads QUARTERLY as a descriptive audit and carries NO verdict, so this horizon governs only a hypothesis nobody has declared.",
    "years_to_horizon_at_projected_rate": 33.39,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 784, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "NO VERDICT - utility ledger, descriptive quarterly audit only"
  ],
  "trial": {
    "domain": "none",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
