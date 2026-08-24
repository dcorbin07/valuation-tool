# DECL DRAFT — F-1: THE FILL A/B (fleet book #1)
## A cost experiment riding every other book's orders. Tag: [O10/O18 — the live question O10 itself named open]

**To be committed ALONE by the options-bot lane before any fleet order is placed.** This is
the harness's first citizen because it consumes every other book's fills and therefore has
the fleet's shortest verdict horizon.

**Hypothesis (cost, not alpha):** working entries as mid-limit orders captures a material
fraction of the quoted half-spread vs marketable orders. `O18` measured ρ = 0.6743 on banked
prints (real trades pay ~67% of the half-spread) — the A/B asks what THIS operator's paper
flow captures, forward, with zero look-ahead risk.

**Entry rule (frozen):** every order any fleet book submits is assigned by the harness's
deterministic randomizer to arm A (marketable) or arm B (limit at mid, worked 60 seconds,
then cancel-and-market; the fallback fill is recorded as B-fallback, never silently pooled).
No exceptions, no overrides; a book may opt out only in its own declaration, before fills.

**Structure/universe/sizing:** none of its own — it inherits the fleet's.

**Records:** per order — book id, arm, quote pair at submission, fill price and time (or
unfilled fate), fallback flag, venue if reported. The per-order half-spread capture is
computed at read time, not stored (no derived outcome statistics in the record stream).

**Verdict horizon:** ~60 paired fills. At the fleet's Wave-1 cadence (est. 30–60 orders/
month across books — a descriptive projection from the entry rules' firing rates, to be
re-stated at launch) that is **1–2 months**. Meter: paired mean capture difference,
anytime-valid CI per the harness; minimum effect of interest fixed now at **10% of the
quoted half-spread** (below that, execution style is a matter of taste, and the declaration
says so).

**Verdict grammar:** B-CAPTURES (CI above +10%) / NO-MATERIAL-DIFFERENCE (CI inside ±10%) /
B-COSTS (unfilled-fallback drag pushes CI below −10%) / horizon-not-reached.

**Trial:** 1, options domain, at first verdict read (harness §2).

**Void:** overriding the randomizer; reading before horizon without booking the charge;
quoting capture as strategy P&L anywhere.

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
  "book": "f1_fill_ab",
  "domain": "options",
  "hypothesis_class": "cost",
  "entry_rule": "No entries of its own. Every order any fleet book submits is assigned by fleet.arm(book, date, symbol, decl_sha) to arm A (marketable) or arm B (limit at mid, worked 60s, then cancel-and-market; the fallback fill is recorded as B-fallback and never pooled). Deterministic and salted by the declaration hash, so the split is fixed the moment this lands.",
  "structure": {
    "strike_selection": "fixed",
    "note": "inherits the host book's structure"
  },
  "universe": "whatever the other fleet books trade",
  "sizing": "inherits the host's",
  "concurrency_cap": 1,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 45.0,
    "min_effect": 10.0,
    "sigma": 40.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of per-order half-spread capture in pp of the quoted half-spread. Replace with the realised SD at first read.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 164,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "0.3 years at the projected 45.00 fills/month (164 fills). The draft said 30 fills; 30 is a round number and this is the derivation.",
    "years_to_horizon_at_projected_rate": 0.3,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 125, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "B-CAPTURES",
    "NO-MATERIAL-DIFFERENCE",
    "B-COSTS",
    "horizon-not-reached"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
