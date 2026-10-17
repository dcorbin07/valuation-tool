# DECL — F-4b — event-free premium at 25 DELTA, on the free forward calendar

**COMMITTED ALONE.** Don's ruling of 2026-10-17: *"F-4 is re-declared at 25 delta on the free
forward calendar. F-10 stays retired."*

**WHY THIS IS A NEW BOOK ID AND NOT AN AMENDMENT TO `DECL_f4_eventfree_premium.md`, AND THE
REASON IS THIS WEEK'S OWN DEFECT.** `f4_eventfree_premium` already has a record stream — 13 rows
— and the chain anchors at the **declaration's content hash**, so editing that file would break
its row 0 permanently. That is exactly what bricked `F-21` and `F-22`, and the re-anchor built
on 2026-10-17 is deliberately scoped to an allowlist of those two. **So the 0.90-moneyness
declaration is left untouched and stays RETIRED as the record of what was retired**, and the
25-delta expression — which is a different construction, not a tweak — gets its own id and its
own stream. `FLEET_RETIREMENTS.md` retired *"THE DECLARED 0.90-MONEYNESS EXPRESSION ONLY"* and
said the 25-delta route was *"NOT foreclosed"*; this is that route.

---

## What changed from the retired expression, and what did not

| | retired `f4_eventfree_premium` | **this book** |
|---|---|---|
| strike | 0.90 moneyness | **25 delta** |
| tenor | 30 DTE | **30 DTE — unchanged** |
| event source | the **I-4 licensed spine**, which holds **no forward dates** | **Yahoo's forward calendar** |
| buffer past expiry | 5 sessions | **9 calendar days, derived** |
| unknown event date | skipped and counted | **REFUSED, skipped and counted — unchanged in kind** |
| crash gate | `K3` fired at **11.57 years** | **4.7539 / 3.5185 years, clears 6.0** |

**THE STRIKE RULE IS THE WHOLE CHANGE AND ITS EFFECT IS MEASURED, NOT ASSERTED.**
`FLEET_RETIREMENTS.md`: at 0.90 moneyness and 30 DTE the crash stress read **11.57 years**
against a 6.0-year bar; **at 25 delta on that same tenor it is 4.7539**, a **2.43x improvement
from the strike rule alone**. On the check quadrant it is **3.5185 years** on **12.0122%/yr**
income (n 10,426) against **4.7539** on **9.0474%/yr** (n 5,974) on the build quadrant.

**AND THE WARNING THAT TRAVELS WITH THAT GATE, IN THE DECLARATION RATHER THAN A FOOTNOTE.**
A cleared crash gate *"establishes nothing about whether either book makes money"* —
`HANDOFF_optionsbot.md` §87 is this project's own demonstration, where `K3` passed on a window
whose real crash cost **82% of the account**. `SELL-PREMIUM-2`'s §87b measured the same family
of trade losing **−2.7788% per trade in 2020 at 33.52% assigned**, and that is the year this
book's stress arithmetic does not and cannot rule out. **`K3` is a stress arithmetic, not crash
survival.**

---

## The event filter, and why the buffer is 9 days

The licensed spine holds **385,426 code-22 rows and not one forward date**, which is why the
retired expression *"as declared enters nothing, ever"* and earned `RULE_ARMED_NEVER_FIRES`.
The forward calendar measured on 2026-10-16 over the fleet's own 487-name optionable gate:

* a future date for **444 of 487 (91.2%)**, of which **377 (84.9%) are CONFIRMED** rather than
  projected;
* realised 8-K Item 2.02 history for **414 (85.0%)**;
* **year-on-year drift over 3,391 pairs: median 1 day, p75 5, p90 6, p95 9, max 45** — exact
  only **9.6%** of the time, within 7 days **92.1%**.

> **THE BUFFER IS 9 CALENDAR DAYS BECAUSE 9 IS THE MEASURED p95 OF THAT DRIFT.** Don's
> instruction is *"at least the 7-day buffer your drift measurement implies"*; 7 is the 92.1%
> point and 9 is the 95th percentile, so 9 satisfies it and is the figure the measurement
> actually hands over. **It is a DERIVED constant, not a chosen one**, and raising it later
> would be a construction change.

**A NAME WITH NO FORWARD DATE IS REFUSED, NEVER TREATED AS EVENT-FREE.** That is Don's
instruction and it is also `O7`'s own expensive lesson: 29 foreign private issuers had zero
earnings coverage, and a filter reading *"no date"* as *"no announcement"* fails open on a
non-random tenth of the book. **The refusal is counted and reported**, so the 8.8% without a
date is visible as a coverage fact rather than as a quiet market.

**AN ESTIMATED DATE IS TREATED EXACTLY AS A CONFIRMED ONE, AND THAT IS A CHOICE WITH A REASON.**
The 9-day buffer is set at the p95 of the drift *of the projection rule itself*, so it already
absorbs the uncertainty that distinguishes the two. Using a wider buffer for estimated dates
would be a second parameter doing the same job, and `MA5`'s rule is that a parameter with no
measurement behind it is how a bar freezes.

---

```json
{
 "book": "f4b_eventfree_25d",
 "domain": "options",
 "hypothesis_class": "edge",
 "side": "short",
 "sells_premium": true,
 "margin_method": "cash_secured_put",
 "return_denominator": "secured_cash",
 "spot_basis": "as_traded",
 "assignment_model": "at expiry per moneyness, S3-I3 assignment_at_expiry",
 "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
 "entry_rule": "Every Monday: universe = optionable names that are (a) MA28 0-of-3 flags at the latest quarterly compute, (b) EVT-clean (E-4's tail flag, bottom 4 quintiles), (c) EVENT-FREE on the FREE FORWARD CALENDAR -- the next earnings date must be KNOWN from the Yahoo forward calendar AND fall outside [session, expiry + 9 calendar days]; a name whose next date is UNKNOWN is REFUSED, SKIPPED AND COUNTED, never treated as event-free -- and (d) no S3-I2 catalyst inside the same window. Take the 3 largest by market cap not already held; alphabetical tie-break. The date compared against is the CYCLE SESSION (fleet_books.cycle_session), never the runner's own UTC date: the cron lands 3.5-7.5 hours late and an exact match on date.today() is what made four books read RULE_ARMED_NEVER_FIRES while never seeing their data.",
 "structure": {
  "strike_selection": "delta",
  "delta": 0.25,
  "v6opt_argument": "V6-OPT measured that a delta-targeted strike sets moneyness from the name's OWN implied vol and so NEUTRALISES the very risk difference the trade was built to exploit -- assignment came back 25.30% healthy against 25.73% unhealthy, a 0.43pp gap, because the richer name simply got a further strike. THE ARGUMENT PAST IT IS THAT THIS BOOK'S EDGE IS NOT A CROSS-SECTIONAL RISK DIFFERENCE BETWEEN NAMES, SO THERE IS NOTHING FOR THE DELTA RULE TO NEUTRALISE. V6-OPT's signal WAS a per-name risk ranking, which is exactly the thing a per-name vol normalisation cancels. This book's condition is the ABSENCE OF A SCHEDULED JUMP inside the option's life -- a property of the calendar, not of the name -- and implied vol is what CARRIES the earnings jump premium. Removing the event and then striking off the remaining vol prices the diffusion the book intends to be short of, so the normalisation is aligned with the hypothesis rather than orthogonal to it. IT IS ALSO MEASURED RATHER THAN ARGUED: on this book's own tenor the strike rule moves the crash stress from 11.57 years to 4.7539, a 2.43x improvement, which is V6-OPT's mechanism operating in the direction this book wants. AND THE RESIDUAL EXPOSURE IS STATED: if the calendar misses a date, the delta strike is set off a vol that INCLUDES the unremoved event and therefore sits FURTHER out of the money than a fixed moneyness would -- so a filter failure is partly self-protecting, which is the opposite of the fixed-0.90 expression's behaviour and is the second reason to prefer delta here.",
  "right": "put",
  "dte": 30,
  "dte_rule": "nearest 30 and strictly < 40, ties -> shorter",
  "exit": "hold to expiry; assignment per S3-I3"
 },
 "universe": "optionable, MA28-clean, EVT-clean, event-free on the free forward calendar",
 "sizing": "equal secured cash per position",
 "concurrency_cap": 10,
 "records_schema": [],
 "verdict_horizon": {
  "expected_fills_per_month": 11.0,
  "min_effect": 0.75,
  "sigma": 5.047,
  "sigma_provenance": "MEASURED, not a prior: SELL-PREMIUM-2's realised per-trade SD of a 25-delta cash-secured put on secured cash, over 4,617 stage-2 trades. The retired expression carried 4.0 as an explicit PRIOR for a 0.90-moneyness strike; this is a different strike and the measured figure for it is larger, so the horizon is longer rather than shorter.",
  "sigma_may_only_be_raised": true,
  "rho": 3.0,
  "alpha": 0.05,
  "fills_needed": 507,
  "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma=5.047, rho=3.0, alpha=0.05)/n <= 0.75. DERIVED at the measured sigma; the retired expression's 306 was derived at the 4.0 prior and does not transfer.",
  "earliest_honest_read": "About 3.84 years at the projected 11.00 fills/month (507 fills). A premium book's verdict needs its LOSS TAIL, so no read before 2 quarters regardless of fill count, and the F-4b-versus-anything contrast may not be quoted before both books reach their horizons.",
  "years_to_horizon_at_projected_rate": 3.84,
  "power_gate_note": "Anytime-valid, so the 50%/80% vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*5.047/0.75)^2 = 355, reported beside it so both vocabularies are on the face."
 },
 "verdict_grammar": ["PAYS", "BLEEDS", "CANNOT-TELL(horizon)"],
 "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money.",
 "trial": {"domain": "options", "charged_at": "first_verdict_read"}
}
```

---

## What this declaration does NOT claim

It does **not** claim the crash gate makes the book safe — §87 is the counter-example and it is
quoted above. It does **not** re-open `F-10`, which stays retired: the short-side tenor
comparison favours 30 DTE in both quadrants and F-10's build cell clears the gate by **2.3%**,
a margin a successor should expect to lose on any construction change. It does **not** claim the
free calendar is exact — it is right to the day only **9.6%** of the time, which is why there is
a buffer at all. And it licenses **no real money**: `O11` binds, paper only.
