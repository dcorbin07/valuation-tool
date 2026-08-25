# DECL DRAFT — F-19: THE ALERT-DENSITY GATE (fleet-wide convention, not a book)
## Tag: [O11 (the measured, never-registered split: +14.28% expectancy above the 90th-percentile alert week vs −4.51% quiet, 51.5% of trades in >10-alert weeks) — B-13 is the freeze register twin; neither gates the other]

**A LABELING GATE — unlike F-2 it refuses nothing.** To be committed ALONE before any
opted-in host's first fill.

**The rule (frozen):** the harness computes, weekly, the market-wide alert-count percentile
vs the trailing 2 years (a descriptive count from the live daily scan). Every entry of an
opted-in host is **stamped** `density_pct` at order time and binned **HIGH (≥90th)** or
**NORMAL (<90th)**. No entry is blocked, sized, or timed by the stamp — the gate only
labels, so the cells are clean.

**Host attachment rule:** a host opts in **in its own declaration** via
`gates: [alert_density]`, before first fill; the stamp then rides every entry or none.
A host may also declare a **density-gated VARIANT** (trades only in HIGH weeks) — that is a
separate book with its own declaration, records, horizon, and trial; the gate itself never
mutates a host's behavior.

**Records:** the weekly percentile series (kept as a first-class fleet record with its
computation inputs), and the per-entry stamp on opted-in hosts.

**Verdict (cross-host):** at first read — HIGH-vs-NORMAL cell contrast per host and pooled,
with per-cell `O26`-floor (a cell under 15 fills is UNDERPOWERED, never null). Minimum
effect of interest, fixed now: a **+10pp per-trade** (long) / **+0.75% secured-cash**
(short) HIGH−NORMAL spread; `power_gate.state()` line at commit. **The HIGH cell will
accrue slowly by construction (~1 week in 10)** — the honest horizon is set by the HIGH
cell, not the calendar, and the declaration says so.

**Trial:** 1, options, at first cross-host verdict read.

**Void:** any host behavior change from the stamp outside a separately-declared variant;
re-binning after fills; reading cells below the floor.

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
  "book": "f19_density_gate",
  "domain": "options",
  "hypothesis_class": "cost",
  "entry_rule": "A LABELING GATE, refuses nothing. Weekly, compute the market-wide alert-count percentile against the trailing 2 years from the live daily scan; stamp every entry of an opted-in host with density_pct and bin HIGH (>=90th) or NORMAL. No entry is blocked, sized or timed by the stamp. Hosts opt in via gates:[alert_density] in their own declaration, before first fill.",
  "structure": {
    "strike_selection": "fixed",
    "note": "gate, no structure of its own"
  },
  "universe": "opted-in hosts' entries",
  "sizing": "none",
  "concurrency_cap": 1,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 4.0,
    "min_effect": 10.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 1015,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "21.1 years at the projected 4.00 fills/month (1015 fills). The draft said 30 fills; 30 is a round number and this is the derivation. THE HIGH CELL IS THE BINDING CONSTRAINT -- it accrues ~1 week in 10 by construction, so the horizon is set by that cell and not the calendar. A cell under 15 fills is UNDERPOWERED, never null (O26's floor).",
    "years_to_horizon_at_projected_rate": 21.15,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 671, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "HIGH-PAYS",
    "NO-MATERIAL-DIFFERENCE",
    "HIGH-COSTS",
    "CANNOT-TELL(horizon)",
    "UNDERPOWERED-CELL"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
