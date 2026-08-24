# DECL DRAFT — F-12: POST-EVENT REVERSAL BUYS (long book)
## Tag: [O7-scope (that register priced PRE-event straddles and found the event move overpriced; the day-AFTER window — crush done, information fresh — was never an arm) / VIRGIN post-event. EVOWN's NOT-DEMONSTRATED strategy verdict is carried as a hostile family prior, stated here.]

**Entry rule (frozen):** each session: names whose earnings event (I-4 spine, code-22 date
known) occurred the **previous session**. Direction = the live composite's sign for the
name: **positive → call; negative or absent → SKIP** (direction IS half the hypothesis; no
arbitrary fills). Cap **3 entries/session** (tie-break: highest |composite z|, then
alphabetical); names with unknown event dates never enter (coverage honesty, stated).

**Structure:** buy the ATM option (nearest strike) per direction, expiry nearest **60
DTE** (ties → longer). Hold to expiry, no exits. Entry at ask via the F-1 randomizer.

**Universe/sizing:** optionable, event-covered names; cap 10 open; equal premium; sandbox;
`O11` binds.

**Records:** event date + source row, composite sign and z at entry, the post-event gap
(close-to-close through the event, a descriptive stamp), quote pair.

**Verdict horizon:** dozens of covered events/quarter in-universe; at cap-3/session, est.
15–30 fills/quarter (re-stated at launch) → **30 fills ≈ 1–2 quarters**. Meter: mean
per-trade return on premium vs 0; **MEI +15pp/trade**; both vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** entering BEFORE the event (that is
O7's corpse); direction from anything but the frozen composite sign; exits.

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
  "book": "f12_postevent_reversal",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Each session: names whose earnings event (I-4 spine, code-22 date KNOWN) occurred the PREVIOUS session. Direction = the live composite's sign: positive -> call; negative or absent -> SKIP. Cap 3 entries/session; tie-break highest |composite z| then alphabetical. Names with unknown event dates NEVER enter.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.0,
    "right": "call",
    "dte": 60,
    "dte_rule": "nearest 60, ties -> longer",
    "exit": "hold to expiry, no exits"
  },
  "universe": "optionable, I-4-covered names",
  "sizing": "equal premium",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 7.5,
    "min_effect": 15.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 420,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "4.7 years at the projected 7.50 fills/month (420 fills). The draft said 30 fills; 30 is a round number and this is the derivation. EVOWN's NOT-DEMONSTRATED family verdict is carried as an explicit hostile prior on this declaration's face.",
    "years_to_horizon_at_projected_rate": 4.67,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 298, reported beside it so the two vocabularies are both on the face."
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
