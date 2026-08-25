# DECL DRAFT — F-8: CSP ENTRY FINANCING (short book)
## Tag: [U6-partial + V6-OPT-scope (that corpse sold puts on DIP names gated on health; this sells puts only on names the book has ALREADY decided to buy — assignment is the plan, not the risk)]

**Entry rule (frozen):** at each monthly rebalance: every name **newly entering the paper
index book's top decile** (the shipped selection, read not recomputed), up to **cap 5**
(frozen tie-break if more qualify: highest composite score, then alphabetical).

**Structure:** sell cash-secured put, strike nearest **0.95× as-traded spot** (ties →
lower), expiry nearest **30 DTE** (ties → shorter). If assigned: the assignment is the
book's entry, done. If unassigned at expiry: re-sell per the same rule up to **3 cycles**,
then market-buy (all frozen — no judgement at execution time).

**Counterfactual recorded per name:** the plain-entry mark (same-day close at the original
rebalance) so the read prices the financing route against just buying.

**Records:** entry-decision proof, quote pair, cycle count, assignment outcome, secured
cash, counterfactual mark.

**S3-I3 dependency (harness §1.4 interface):** cash-secured denominator; expiry assignment;
early-assignment flagged. **ASSUMPTION THAT COULD SHIFT:** denominator convention (margin
vs full cash) rescales returns and the MEI mechanically.

**Verdict horizon:** est. 3–6 new entrants per rebalance (re-stated at launch) → 30
completed name-cycles ≈ **2–3 quarters**. Meter: mean per-name (CSP-route minus
plain-route) total entry cost; **MEI +0.50% of position per entry**; power line at commit.

**Verdict grammar:** FINANCING-PAYS / COSTS (the missed-rally case is exactly what the
counterfactual catches) / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** entries on names the book did not
select; a fourth cycle; delta-targeted strikes.

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
  "book": "f8_csp_entry_financing",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "At each monthly rebalance: every name NEWLY ENTERING the paper index book, read from the PUBLISHED data_export/paper_track_holdings.csv as a row whose entry_date equals the rebalance date -- a published artifact, never the scoring path. Cap 5; tie-break highest composite score then alphabetical.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 0.95,
    "right": "put",
    "dte": 30,
    "exit": "assigned -> that IS the book's entry; unassigned -> re-sell the same rule up to 3 cycles, then market-buy (frozen)"
  },
  "universe": "names newly entering the published paper index book",
  "sizing": "equal secured cash",
  "concurrency_cap": 5,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 4.5,
    "min_effect": 0.5,
    "sigma": 3.0,
    "sigma_provenance": "PRIOR, not measured: assumed SD of the paired CSP-route-minus-plain-route entry cost as a %% of position. Paired on the SAME name, so it is far tighter than an unpaired per-trade SD (MB8).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 395,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "7.3 years at the projected 4.50 fills/month (395 fills). The draft said 30 fills; 30 is a round number and this is the derivation.",
    "years_to_horizon_at_projected_rate": 7.31,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 282, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "FINANCING-PAYS",
    "FINANCING-COSTS",
    "CANNOT-TELL(horizon)"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```

---

## AMENDMENTS — added at ARMING, 2026-08-24, options-live lane

**A NEW SECTION, NEVER AN EDIT** (`PT-AMEND1`). Everything above is untouched. **They land
before this book's first fill**, which is mechanical: `verify_chain` anchors on the
declaration's CONTENT hash, so amending a book that already has records breaks its own chain
at row 0. F-8 has zero records.

### Amendment 1 — the declared tie-break is not in the declared source

**The frozen rule ends *"Cap 5; tie-break highest composite score then alphabetical"*, and the
artifact it names carries no composite score.** `data_export/paper_track_holdings.csv` is
`ticker, weight, entry_date, entry_price, bench_entry_price, shares, order_id, note`. **And
the rule forbids the obvious workaround in the same sentence** — *"a published artifact, never
the scoring path"* — so reaching into the scorer to recover the missing column is exactly what
it rules out.

**Resolved: `weight` descending, then alphabetical.** The published Index is score-weighted, so
weight is derived FROM the quantity the declaration asked for and is the closest thing the
permitted source contains.

**THE LIMIT IS STATED BECAUSE IT IS REAL: the weight cap compresses the top.** Where the cap
binds, two names with different composite scores carry the SAME weight, and the alphabetical
tie-break then decides between them — which is not what "highest composite score" would have
done. **It can only bite when more than `cap` names enter the book on one date**, and the
alternative readings are worse: the scoring path is forbidden, and an unstated tie-break is
not reproducible.

### Amendment 2 — "each monthly rebalance" needs no calendar, and does not get one

The rule identifies names *"NEWLY ENTERING ... as a row whose entry_date equals the rebalance
date"*. **A name is newly entering on date D exactly when its published `entry_date` IS D.**
So the artifact's own dates are the definition and no rebalance calendar is consulted, kept or
able to drift from it. On a day with no new entries the rule returns nothing — **a market
observation, not a build gap**, and `cycle()` reports the two apart.

Measured on the published file as it stands: entry dates are per-name (2026-08-11, 2026-08-12,
…) rather than one shared rebalance stamp, so a single-calendar reading would have matched
nothing on most days while looking correct.

### Amendment 3 — "equal secured cash" has no denominator

**No allocation figure appears anywhere in the declaration**, so the sizing rule cannot be
executed as written — the same gap F-3 has, and the same resolution: **one contract per
position** until an allocation is declared.

**It is measurement-neutral here for a reason specific to this book, and that is checkable:**
`return_denominator` is `secured_cash`, and secured cash scales with quantity exactly as the
premium does, so **return on secured cash is invariant to quantity.** Sizing cannot move this
book's verdict. It would matter to survivability, and `O11` already binds that.

### What is NOT amended

**This book is SHORT and stays refused unless `S3-I3`'s assignment provider is registered.**
The runner's door registers it; the rule ALSO checks for itself and returns nothing if it is
absent, rather than trusting the gate to have run. A rule that would place a short order is
the last place that should assume somebody else checked.
