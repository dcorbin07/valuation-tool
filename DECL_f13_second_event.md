# DECL DRAFT — F-13: SECOND-EVENT STRUCTURES (long book)
## Tag: [EVOWN (ambient finding: at 45–75 DTE a contract owns the next event and pays its crush premium; owning event #2 while skipping #1's premium is the untested cell) / VIRGIN — carried with EVOWN's NOT-DEMONSTRATED strategy verdict as an explicit hostile prior: the event-ownership family's first forward register did not clear, and this declaration says so on its face.]

**Entry rule (frozen):** each session: names whose earnings event #1 occurred exactly **5
sessions ago** (crush complete per O7's decay shape) AND whose event #2 date is **known**
from the I-4 spine (both dates known or no entry — cadence inference is banned; S3-I6's
table may only ever CONFIRM a known date, never supply one). Direction = live composite
sign, **positive only → call; else SKIP**. Cap 2 entries/session (tie-break: highest
|composite z|, then alphabetical).

**Structure:** buy ATM call (nearest strike), expiry nearest above **event-#2 date + 10
sessions**. **Exit at event-#2 date + 1 session** (frozen — the book owns exactly one
event, which is its entire design), exit at bid.

**Universe/sizing:** optionable, double-covered names; cap 8 open; equal premium; sandbox;
`O11` binds.

**Records:** both event dates + sources, entry-vs-#1 lag proof, composite sign/z, quote
pairs both ends.

**Verdict horizon:** double-date coverage cuts the universe hard (code-22 coverage 1.65/
ticker-yr — both-dates-known is the binding constraint; the eligible count is printed
weekly from launch): est. **2 quarters to 30 fills**, re-stated at launch. Meter: mean
per-trade return on premium vs 0; **MEI +15pp/trade**; both vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** cadence-inferred dates; holding
through event #2 past the frozen exit; entering inside #1's crush window.

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
  "book": "f13_second_event",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Each session: names whose earnings event #1 occurred EXACTLY 5 sessions ago AND whose event #2 date is KNOWN from the I-4 spine. Both dates known or no entry; cadence inference is BANNED. Direction = live composite sign, positive only -> call, else SKIP. Cap 2 entries/session; tie-break highest |composite z| then alphabetical.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.0,
    "right": "call",
    "dte": "nearest above event-#2 date + 10 sessions",
    "exit": "EXIT at event-#2 date + 1 session, at bid (frozen)"
  },
  "universe": "optionable, double-date-covered names",
  "sizing": "equal premium",
  "concurrency_cap": 8,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 40.0,
    "min_effect": 15.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 420,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "0.9 years at the projected 40.00 fills/month (420 fills). The draft said 30 fills; 30 is a round number and this is the derivation. ELIGIBILITY CENSUS RUN BEFORE ACCEPTANCE, as the runbook demands: on the owned events file the last two years carry 32,129 code-22 event-1s of which 27,861 (86.7%%) have a KNOWN next event, median 1,084/month universe-wide against the runbook's ~5/month reject bar. THAT IS AN UPPER BOUND computed with hindsight -- the owned data records no ANNOUNCEMENT date, so it cannot say when a date became knowable, and live eligibility will be lower. The eligible count is printed weekly from launch and the book CLOSES with a zero-charge row if it starves.",
    "years_to_horizon_at_projected_rate": 0.88,
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


---

## SCOUT AMENDMENT ACCEPTED — applied at arming, 2026-08-25, options-live lane

**A NEW DATED SECTION, NEVER AN EDIT** (`PT-AMEND1`). Everything above is untouched, so the
ceremony's `--diff-filter=A` evidence that this declaration predates every line of fleet code
is intact. **It lands before this book's first fill**, which is mechanical: `verify_chain`
anchors on the declaration's CONTENT hash, so amending a book that already has records breaks
its own chain at row 0. This book has zero records.

**The scout's amendment is `AMEND_f13_second_event.md` (Frontier Scout lane, commit `6b6426f`), and it is
ACCEPTED IN FULL.** Its text is the record; this section states the operational consequence
for the harness, and nothing here reinterprets it.

**F-13 IS WITHDRAWN.** The refusal at `2ef8e5d` is accepted in full: the rule asks a
backward record for a forward date, and it closes its own only exit by banning cadence
inference. **The condition cannot be satisfied — not "is not satisfied today".**

**OPERATIONAL CONSEQUENCE HERE: F-13 IS NOT ARMED AND MUST NOT BE.** No entry rule is
registered for it, its declaration stays on disk unedited, and it holds zero records. A
withdrawn book is not a refused one and not a failed one: **no trial is charged, no meter
exists and no verdict is implied in either direction.**

**The drafting rule the scout adopts from it travels further than the book did:** *naming a
data source is not enough — a declaration must name the FIELD and its DIRECTION IN TIME.*
`is_known` answered *"do we have history for this name"* truthfully, and answering a different
question truthfully is what hid the gap from every machine check the ceremony could run.
