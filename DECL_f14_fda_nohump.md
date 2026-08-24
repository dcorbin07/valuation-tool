# DECL DRAFT — F-14: FDA NO-HUMP CONVEXITY (long book)
## Tag: [O7-scope (earnings only — the market's overpricing was measured on its CALENDAR; a date the IV surface shows no hump for is definitionally not on it) / VIRGIN for non-earnings catalysts. S3-I2 (built — the calendar starts 2026-08-2x) and I-1 are the instruments.]

**Entry rule (frozen):** weekly: every optionable name with an S3-I2 catalyst date
(PDUFA/decision class) inside **90 days**. Hump check at entry via I-1's term structure:
compute event-month ATM IV vs the adjacent later month; **if event-month ≤ 1.10× adjacent
(NO hump), enter; if > 1.10× (priced), RECORD-AND-SKIP** — the skips are the control
population and are first-class records. All qualifying no-hump names enter (sparse; if >8
in a week, largest by market cap, alphabetical tie-break, skips counted).

**Structure:** buy the straddle (nearest-ATM call + put, same strike where listed, else
nearest strangle — rule: minimize |call strike − put strike|, ties → tighter around spot),
expiry nearest above the catalyst date. **Exit at catalyst date + 2 sessions** at bid
(frozen). Entry at ask via the F-1 randomizer.

**Universe/sizing:** optionable S3-I2-covered names; cap 6 open; equal premium; sandbox;
`O11` binds.

**Records:** the calendar source row (vendor, scrape date), the hump ratio and both months'
IVs, quote pairs both ends, the skip population's identical fields.

**Verdict horizon — the honest number:** binary-catalyst names ∩ optionable is thin; est.
**a handful of qualifying entries per quarter → 12+ months to 30 fills**, declared plainly
(the map's own number). The no-hump RATE and skip census are reported descriptively from
week one — those are findings about pricing even before any P&L verdict. Meter: mean
per-trade return on premium vs 0; **MEI +30pp/trade** (sparse books must clear big); both
vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** entering humped names (they are the
control); holding past the frozen exit; any earnings-date entry through this book (I-4
events belong to F-12/F-13).

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
  "book": "f14_fda_nohump",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Weekly: every optionable name with an S3-I2 catalyst date (PDUFA/decision class) inside 90 days. Hump check at entry: event-month ATM IV vs the adjacent later month. If event-month <= 1.10x adjacent (NO hump) ENTER; if > 1.10x (priced) RECORD-AND-SKIP -- the skips ARE the control population and are first-class records. If more than 8 qualify in a week take the largest by market cap, alphabetical tie-break, skips counted.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.0,
    "right": "straddle (nearest-ATM call + put, same strike where listed, else the strangle minimising |call strike - put strike|)",
    "dte": "nearest above the catalyst date",
    "exit": "EXIT at catalyst date + 2 sessions, at bid (frozen)"
  },
  "universe": "optionable names on the S3-I2 catalyst calendar",
  "sizing": "equal premium",
  "concurrency_cap": 6,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 2.7,
    "min_effect": 30.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 93,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "2.9 years at the projected 2.70 fills/month (93 fills). The draft said 30 fills; 30 is a round number and this is the derivation. FORWARD-ONLY BY CONSTRUCTION: the S3-I2 calendar's first snapshot is 2026-08-24T02:39Z with 452 rows (82 PDUFA, 124 day-precision), so this book has NO history and can never be backfilled. The no-hump RATE and the skip census are reported descriptively from week one and are findings about PRICING before any P&L verdict exists.",
    "years_to_horizon_at_projected_rate": 2.87,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 75, reported beside it so the two vocabularies are both on the face."
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
