# DECL DRAFT — F-22: THE RANDOM-DAY TWIN OF F-21 (short book)
## Tag: [DECISIONS.md 2026-10-12 clause (b), which makes this book a REQUIREMENT and not an option: an options strategy passes only if it "beats the same trade placed on random days in the same names (so the timing is shown to matter)" + V6-OPT's own C-C control, which this book is the forward implementation of (five seeds, matched on (name, year), pooled +0.2612%/trade against the arm's +1.1342%, paired name-year sign test z +7.2506) + R2, the reason five seeds is a floor and not a preference]

**A DRAFT. NO FILL IS PLACED AND NO TRIAL IS BOOKED** — the harness charges at the **first verdict
read**. Committed **ALONE** (exactly one file in its commit) before any fill exists.

**THIS BOOK EXISTS SO THAT F-21 CAN HAVE A VERDICT AT ALL.** Don's 2026-10-12 clause (b) is not a
robustness check bolted on afterwards; it is one of three conditions, and without a twin F-21 can
only ever report *"the trade made money"* — which `R2` established is a different claim from *"the
timing mattered"*, having measured the options alert book **losing to random entry by
−5.0640pp/trade (z −4.9612 on 1,332 name-year cells)** while the book's own expectancy was
**positive**. **A positive book with a dead entry signal is the exact shape this project has
already found once.**

---

## THE STRUCTURE IS F-21'S, FIELD FOR FIELD, AND THAT IS THE WHOLE DESIGN

Same right, same 25-delta target solved on the put leg, same 30–45 DTE band, same hold-to-expiry,
same equal-secured-cash sizing, same cap, same as-traded spot basis, same S3-I3 assignment.
**Exactly one thing differs: WHEN it enters.** If anything else differed the comparison would be
measuring that instead.

**THE DELTA ARGUMENT IS F-21'S AND IS CARRIED VERBATIM**, because a twin that argued differently
about its own strike rule would not be the same trade. The harness requires it on this book too
(`fleet.py:308`), and satisfying it with a *different* argument would be the defect.

---

## HOW A RANDOM DAY IS DRAWN FORWARD, WHICH IS THE ONE GENUINELY NEW PROBLEM

`V6-OPT`'s control drew random days **inside the same name-year as each real trade**. That is not
available forward: you cannot draw from a year you have not lived. **Three properties have to
survive the translation, and the construction below is chosen to keep all three:**

1. **DETERMINISTIC AND SALTED.** The draw is `sha256(F22_SALT || book || ticker || session_date)`
   compared against a threshold — **not a call to a random number generator** — so any reader can
   reproduce every entry the book ever made from the declaration alone. `S3-I1`'s own day-1
   self-check requires exactly this (*"the randomizer is deterministic and salted"*), and the salt
   is frozen in the declaration below.
2. **TIMING UNCORRELATED WITH THE DIP SIGNAL.** The draw reads the calendar and the ticker and
   **nothing else** — no drawdown, no health score, no volatility. Pinned by the void condition
   that the entry rule may reference no price-derived quantity.
3. **PAIRABLE WITH F-21 ON `V6-OPT`'s OWN UNIT.** The twin's name pool is the **whole optionable
   $10B tier**, deliberately WIDER than F-21's healthy-dip list, so that there is something to pair
   with. **At read time the paired statistic uses only (name, calendar-quarter) cells in which BOTH
   books hold a fill**, which is `V6-OPT`'s (name, year) matching done forward at a finer grain.
   **Unmatched fills on both sides are counted and reported and excluded from the paired statistic**
   — reporting the unpaired means as if they were the comparison is how a matched design silently
   becomes an unmatched one.

**THE THRESHOLD IS CALIBRATED TO F-21'S OWN FILL RATE AND RE-STATED WITH IT.** A twin that fills
ten times as often is not the same trade sampled differently; it is a different book whose paired
cells are a biased subset of its own fills. The threshold `p` is set so expected entries/month
equals F-21's declared **2.0**, and **both numbers are re-stated together at launch** from the
trailing-90-day count.

**AND THE CONTAMINATION IS ACCEPTED AND MEASURED RATHER THAN FILTERED OUT.** A genuinely random day
will sometimes land on a day the name *is* in a healthy dip. **The twin does NOT exclude those
days**, because excluding them would make it a *"non-dip"* book and the comparison would become
dip-versus-no-dip rather than dip-timing-versus-random-timing. **The share of twin fills that
landed on a healthy-dip day is a REQUIRED reported field**, so a reader can see exactly how much
the control overlaps the arm. `V6-OPT`'s control had the same property and never reported it; this
one must.

---

## THE HORIZON, AND WHY THIS BOOK'S OWN HORIZON IS NOT THE HORIZON OF THE TEST

**`sigma` = 6.5633 pp, MEASURED, and it is the MAXIMUM across `V6-OPT`'s five control seeds**
(5.8881 / 6.0043 / 5.4852 / 6.5633 / 6.0772). The maximum rather than the mean because
`track_meter`'s rule is that sigma may only ever be **RAISED**, so declaring the largest measured
value is the only choice that cannot later need revising upward. **It is this structure's own
control SD and not F-21's** — borrowing F-21's 5.047 would be the `MB8` error, and the measurement
says the random-timing book is genuinely noisier.

**`fills_needed` = 1,652** at `min_effect` 0.5671 (F-21's, derived the same way), fixed-*n*
analogue **1,050**, which is about **68.8 years** at 2.0 fills/month.

> **THAT FIGURE IS NOT THE HORIZON OF DON'S CLAUSE (b), AND CONFLATING THEM WOULD BE A REAL
> ERROR.** 1,652 is what this book needs to say something about **ITSELF**. Clause (b) is a
> **PAIRED** comparison between two books holding the same structure on overlapping names, and
> `MB8` measured directly how much that matters: a paired difference between two highly correlated
> books came in at an se of **0.1106pp** where an unpaired difference between two different books
> was **0.9354pp** — **8.5× tighter**. **So clause (b) may resolve long before either book's
> standalone meter does.**

**AND THE PAIRED se IS MEASURED AT READ TIME, NEVER BORROWED** — not from `MB8`, not from F-21, not
from `V6-OPT`. `MB8`'s own closing rule is that an se may not travel across perturbation sizes, and
a random-timing difference is a different perturbation from either book's own dispersion. The read
reports the measured paired se, its **80%-power MDE** as `(crit + 0.84) · se` (`MB22`: every MDE
this project published before it was a 50%-power figure), and the **five-seed floor is not
available forward** — one live twin is one draw. **That is a real weakening against `V6-OPT`'s
five-seed control and is stated rather than glossed**: `R2` showed a single control seed can flip a
verdict, so the forward comparison is structurally weaker than the backtested one on exactly that
axis, and the paired sign test across many (name, quarter) cells is what partly replaces it.

**Verdict grammar:** `PAYS` / `BLEEDS` / `CANNOT-TELL(horizon)`. **Trial:** 1, options, charged at
the first verdict read. **Void:** referencing any price-derived quantity in the entry rule;
excluding dip days; a threshold not matched to F-21's rate; reading this book's verdict without
F-21's; using a non-deterministic randomiser; reporting unpaired means as the clause-(b) comparison.

---

## MACHINE-CHECKABLE DECLARATION

**THE FENCE READS `jsonc` AND NOT `json`, FOR THE REASON SET OUT IN F-21's OWN DECLARATION:** the
exporter globs every `DECL_*.md` and treats anything that parses as a book, the `DRAFT_` prefix
does not exempt it, and the only reason the three existing drafts are skipped is that they are
prose-only. **These two are the first parseable drafts in the repo and they turned
`test_the_committed_manifest_equals_a_fresh_build` red**, which blocks every lane's land, so the
fence is set to one `parse_declaration` does not claim.

**EVERY FIELD IS FINAL and with the fence set to `json` this declaration returns `ok = True` with
ZERO refusals** once `assignment.register()` is called. **ACCEPTANCE:** rename to
`DECL_f22_dip_csp_random_twin.md` **alone** in its own commit, change `jsonc` → `json`, re-run
`scripts/fleet_export_declarations.py`. **F-22 must be accepted at the same time as F-21 or
neither** — neither book's verdict may be read without the other's, so arming one alone would
produce exactly the unpaired reading Don's clause (b) exists to prevent.

```jsonc
{
  "book": "f22_dip_csp_random_twin",
  "domain": "options",
  "hypothesis_class": "cost",
  "side": "short",
  "sells_premium": true,
  "entry_rule": "Each session, for every optionable name with point-in-time market cap >= $10B (never ever-in-tier), compute h = sha256('F22-RANDOM-TWIN-v1|' + book + '|' + ticker + '|' + session_date) and enter if the leading 8 hex digits of h, read as an integer over 2^32, fall below the threshold p. NOTHING PRICE-DERIVED IS READ: no drawdown, no health score, no volatility, no composite. p is set so expected entries per month equals F-21's declared rate and is RE-STATED WITH IT at launch from the trailing-90-day count. Skip any name already held or already entered this quarter. Days on which the name happens to be in a healthy dip are NOT excluded -- excluding them would make this a non-dip book and change the comparison from random-timing-vs-dip-timing into no-dip-vs-dip -- and the share of fills landing on such a day is a required reported field.",
  "structure": {
    "strike_selection": "delta",
    "delta": 0.25,
    "delta_leg": "solved on the PUT leg, V6-OPT's convention",
    "right": "put",
    "dte": 37,
    "dte_rule": "nearest 37, restricted to 30-45; ties -> longer",
    "exit": "hold to expiry, no exits",
    "v6opt_argument": "CARRIED VERBATIM FROM F-21, because a twin that argued differently about its own strike rule would not be the same trade and the comparison would measure the difference in the argument. CONCEDED, NOT DODGED: V6-OPT's autopsy is correct that a delta target sets the strike from the name's own volatility and so equalises assignment by construction -- 25.303% assignment on healthy dips against 25.727% on unhealthy, a 0.43pp gap, where V6-B had measured a real further-20% difference of 2.797pp on those same covered rows. A RISK SIGNAL CANNOT PAY THROUGH A DELTA-TARGETED STRIKE. Neither book carries a risk signal. DECISIONS.md 2026-10-12 judges an options strategy as its own system and its three pass clauses are each unobstructed by a delta target; the only condition it obstructed has been withdrawn by the owner. For THIS book the argument is stronger still: its entry timing reads nothing price-derived at all, so there is no risk signal present even in principle for a strike rule to neutralise. And the alternative is measured to be worse on a gate the pair must pass -- SELL-PREMIUM's K3 fired at 8.900816 years of premium against a 6.0 bar on a fixed 0.90-moneyness rule, which collects 0.7778% of strike at a median 44 DTE = 4.4545%/yr against V6-OPT's 2.550% at a median 32 DTE.",
    "pairing": "At read time the clause-(b) statistic uses only (name, calendar-quarter) cells in which BOTH F-21 and F-22 hold a fill -- V6-OPT's (name, year) matching done forward at a finer grain. Unmatched fills on both sides are COUNTED AND REPORTED and excluded from the paired statistic. Reporting unpaired means as the comparison is a void condition."
  },
  "universe": "the whole optionable point-in-time $10B tier -- deliberately WIDER than F-21's healthy-dip list so that pairable cells exist; the pairing at read time discards the rest",
  "sizing": "equal secured cash per position, identical to F-21; the skip reason is recorded so an affordability skip is never read as a concurrency skip (MB3)",
  "concurrency_cap": 10,
  "assignment_model": "at expiry per moneyness, S3-I3 assignment_at_expiry",
  "margin_method": "cash_secured_put",
  "spot_basis": "as_traded",
  "early_assignment_flag": "S3-I3 early_assignment_flag, FLAGGED not simulated",
  "return_denominator": "secured_cash",
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 2.0,
    "expected_fills_provenance": "MATCHED TO F-21 BY CONSTRUCTION and re-stated with it at launch. A twin that fills ten times as often is not the same trade sampled differently; it is a different book whose paired cells are a biased subset of its own fills.",
    "min_effect": 0.5671,
    "min_effect_derivation": "F-21's, derived the same way: DECISIONS.md 2026-10-06 quotes a candidate's expected return at HALF its backtested size (McLean-Pontiff), and half of V6-OPT's measured +1.1342 pp/trade is 0.5671. Identical on both books so the two standalone meters are commensurable.",
    "sigma": 6.5633,
    "sigma_provenance": "MEASURED, and it is the MAXIMUM across V6-OPT's five C-C control seeds (5.8881 / 6.0043 / 5.4852 / 6.5633 / 6.0772 pp). The maximum rather than the mean because track_meter's rule is that sigma may only ever be RAISED. It is THIS structure's own control SD and NOT F-21's 5.047 -- borrowing that would be the MB8 error, and the measurement says random-timing is genuinely noisier.",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 1652,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED; the same derivation reproduces F-10's declared 306 and F-11's declared 138 exactly (MB15). Fixed-n analogue at crit 1.96: 1050.",
    "earliest_honest_read": "About 68.8 years at 2.0 fills/month (1652 fills) FOR THIS BOOK'S OWN STANDALONE METER -- which is NOT the horizon of Don's clause (b), and conflating the two would be a real error. Clause (b) is a PAIRED comparison between two books holding the same structure on overlapping names, and MB8 measured a paired se of 0.1106pp where an unpaired difference between two different books was 0.9354pp, 8.5x tighter. So clause (b) may resolve long before either standalone meter. THE PAIRED se IS MEASURED AT READ TIME AND NEVER BORROWED -- not from MB8, not from F-21, not from V6-OPT (MB8's own rule: an se may not travel across perturbation sizes). The read reports the measured paired se and its 80%-power MDE as (crit + 0.84) * se (MB22). AND THE FIVE-SEED FLOOR IS NOT AVAILABLE FORWARD: one live twin is one draw, R2 showed a single control seed can flip a verdict, so the forward comparison is structurally weaker than V6-OPT's backtested five-seed control on exactly that axis, and the paired sign test across many (name, quarter) cells is what partly replaces it.",
    "years_to_horizon_at_projected_rate": 68.83,
    "power_gate_note": "Anytime-valid, so the boundary IS the threshold at every n and fills_needed is where it falls to the declared minimum rather than where a verdict becomes possible. Both vocabularies are on the face. No X7 or CORRECTED-FLOORS floor is quoted -- none is calibrated for a per-trade return on secured cash, nor for a paired within-book difference (V2G, R1-VAR) -- and every critical value either book reports is LABELLED UNCALIBRATED."
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
