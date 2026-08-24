# DECL DRAFT — F-2: THE MENU-BREADTH GATE (fleet-wide convention, not a book)
## Tag: [O13-Q3a (its pool refused nothing — cited) / MB1 (the fillable-menu instrument) / MB1-SEL (coverage conditions outcomes in BOTH books)]

**A GATE: hosts attach it; it holds no positions.** To be committed ALONE before any opted-in
host's first fill.

**The rule (frozen):** at order time, compute the host entry's FILLABLE IN-BAND MENU by
`MB1`'s shipped prefilter definition verbatim (calls-or-puts per the host's side → DTE band
±25% of the host's target → moneyness 0.85–1.15 → two-sided usable quotes → volume > 0).
**If the fillable count < 4, the entry is REFUSED.** No overrides.

**Host attachment rule:** a host book opts in **in its own declaration** via a
`gates: [menu_breadth]` line, before its first fill. Attachment after fills is a new
declaration. The gate applies to every entry of an opted-in host, or none.

**Records (ride the host's rows):** the menu census at order time; for REFUSED entries, the
full would-have-been quote pair and menu detail — the counterfactual is quote-marked and the
declaration states that limitation now (a quote-mark is not a fill; `O10`'s C2 lesson).

**Verdict (cross-host, per-host cells):** at first read — refused-entry counterfactual
quote-marked outcomes vs taken-entry outcomes, per host and pooled. Minimum effect of
interest, fixed now: refusal improves an opted-in host's per-trade mean by **+5pp** (long
books) / **+0.5% of secured cash** (short books). `power_gate.state()` line filled at commit.

**Verdict horizon:** reads with its hosts — earliest when any single host reaches its own
horizon with ≥10 refusals recorded; the refusal RATE is reported descriptively from week one.

**Trial:** 1, options, at first cross-host verdict read (the gate is its own question).

**Void:** refusing on any feature other than the frozen menu count (`O13`-Q3a's single-
feature caution is faced by being exactly one pre-named feature, chosen for its `MB1-SEL`-
measured mechanism); host-selective application; reading cells before the host's horizon.

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
  "book": "f2_menu_gate",
  "domain": "options",
  "hypothesis_class": "cost",
  "entry_rule": "A GATE, holds no positions. At order time compute the host entry's fillable in-band menu by MB1's shipped prefilter verbatim (side-matched right -> DTE band +/-25%% of target -> moneyness 0.85-1.15 -> two-sided usable quotes -> volume > 0). If the fillable count < 4 the entry is REFUSED and the would-have-been quote pair recorded. Hosts opt in via gates:[menu_breadth] in their own declaration, before first fill; all entries or none.",
  "structure": {
    "strike_selection": "fixed",
    "note": "gate, no structure of its own"
  },
  "universe": "opted-in hosts' entries",
  "sizing": "none",
  "concurrency_cap": 1,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 8.0,
    "min_effect": 5.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 4563,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "47.5 years at the projected 8.00 fills/month (4563 fills). The draft said 30 fills; 30 is a round number and this is the derivation. The refusal RATE is descriptive from week one and does not wait for this. The counterfactual is QUOTE-MARKED, never filled (O10's C2).",
    "years_to_horizon_at_projected_rate": 47.53,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 2684, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "REFUSAL-HELPS",
    "NO-MATERIAL-DIFFERENCE",
    "REFUSAL-COSTS",
    "CANNOT-TELL(horizon)"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
