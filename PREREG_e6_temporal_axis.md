# PREREG_e6_temporal_axis.md — E-6 / S-SEED-2: the temporal axis (TIDEMARK transform)
## Is a name cheap against its OWN history, over and above being cheap against its peers?

**Season 2 register `E-6`, gated on `I-2`. Domain EQUITY, 1 trial. Committed ALONE, markdown
only, zero `.py`, as a strict git ancestor of every measurement commit; the trial is booked in
its own commit BEFORE the runner exists.**

---

# §0. THE CONTAMINATION, AND HOW IT IS RESOLVED — read this before anything else

## 0.1 The problem, stated against myself

`E-6`'s pre-outcome kill, from the seed: *"the burn-in census must leave >= 60% of panel rows
eligible, else UNPOWERED-BY-CONSTRUCTION."* `I-2`'s census is **already published** and gives
two readings of the seed's *"burn-in pre-committed at 5y"*:

| reading | eligible rows | share | against the 60% kill |
|---|---|---|---|
| **20 observations** | 69,059 | **60.607%** | clears, by 0.61pp |
| 20 observations AND 5 calendar years | 67,098 | **58.886%** | fails, by 1.11pp |
| (21 observations, for context) | 67,041 | 58.836% | fails |

**Both are visible. They land on opposite sides. Choosing between them now, with those numbers
on the page, is `MA58`'s void condition 5 — choosing the design to buy power — and no argument
from which side either lands is admissible.** I do not make one anywhere below.

`I-2` handled its own half correctly: it published both, **recorded no comparison to 60%**, and
wrote that `E-6` *"must DECLARE which reading of 'five years' it means BEFORE it runs"*. The
contamination is that the declaration is now being written after the census exists.

## 0.2 The internal anchor cannot decide it — checked, not assumed

The obvious move is to read the seed literally. It does not settle anything, because the seed
uses years and quarters interchangeably and its own worked examples point both ways:

* *"burn-in pre-committed at 5y"* — calendar language;
* *"first usable date ~2014"* — 2009-01-15 plus **20** quarterly observations is 2014-01;
  plus 21 is 2014-04. Consistent with both;
* *"a 10y burn-in leaves ~28 dates"* — 69 minus 40 observations is 29; minus 41 is 28.
  Consistent with both, and marginally favouring the calendar reading.

**The seed's language is indeterminate to within one quarter, which is exactly the size of the
disagreement.** So it cannot arbitrate, and leaning on it would be picking the gloss that suits.

## 0.3 The external anchor, VERIFIED IN THE SOURCE RATHER THAN CITED

`TIDEMARK/tidemark/stats/percentile.py`, rule 3, quoted verbatim:

> *"A BURN-IN, BELOW WHICH THE ANSWER IS `NaN` AND NOT A NUMBER. A percentile computed on
> eleven observations is not a percentile. Committed: 360 months (30 years) for monthly
> series, 30 observations for annual."*

and its `expanding_percentile` *"returns NaN before `burn_in` valid **observations** exist"*,
implemented as `dropna()` then positional indexing — **an observation count, with "(30 years)"
as a parenthetical gloss on a dense monthly series.** That is the same shape as the seed's
*"5y"* gloss on a quarterly one, which is why it is the right anchor rather than a convenient
one.

**PROVENANCE, MEASURED IN THAT REPOSITORY'S GIT RATHER THAN TAKEN ON TRUST: commit `76fa895`,
`2026-08-16`** — the commit that first introduces `BURN_IN_ANNUAL`. **A CORRECTION TO THE
INSTRUCTION THAT SENT ME: it is 2026-08-16, not 2026-08-17** — one day earlier, and four days
before `I-2`'s census of 2026-08-20. The correction runs toward the anchor being safer, and it
is recorded because a provenance argument whose date is wrong is not a provenance argument.

## 0.4 Three independent grounds, none of which mentions the census outcome

1. **PROVENANCE.** The convention predates the census by four days, in a separate repository,
   written for a different question.
2. **THE PORT ALREADY IMPLEMENTS IT, AND THE CALENDAR READING IS AN ADDITION RATHER THAN A
   READING.** `name_percentile.name_percentiles` takes `burn_in` as an observation count;
   `eligible_rows` accepts `min_history_years` as an **optional** extra condition with **no
   default**. So 60.607% is what the ported engine does, and 58.886% is what it does *plus a
   filter a register must choose to impose*. The question is not which of two readings to take
   but whether to add a condition — and adding one needs a reason.
3. **STATISTICAL PRINCIPLE.** A percentile's precision is a function of the number of order
   statistics behind it, not of the calendar time they span. Burn-in for an expanding
   percentile is inherently an observation-count concept, and TIDEMARK's rule 3 says so in
   those words (*"a percentile computed on eleven observations"*).

## 0.5 The counterfactual test, stated so a reader can check I am not rationalising

**Had the census come out the other way — observation count 58.886%, calendar 60.607% — every
one of §0.4's three grounds would have selected the observation count anyway, and the kill
would have fired.** None of them can see the outcome. That is the test for whether a rule is
being chosen on its result, and this rule passes it. If a later reader thinks it does not, the
row is there to amend, and the sensitivity in §4.3 bounds what the choice can have bought.

## 0.6 WHY NOT `VOID-BY-CONTAMINATION`, WHICH WAS AVAILABLE AND ACCEPTABLE

Voiding is the maximally conservative move and I decline it, for a stated reason: **a
legitimate external anchor exists, predates the census, is the engine this item is gated on,
and passes §0.5.** Voiding where a principled resolution exists discards a real question to
settle a definitional coin-flip. The residual risk — that I have rationalised toward the
reading that lets the arm run — is bounded by §4.3's sensitivity rather than left to a reader's
trust.

## 0.7 A FINDING ABOUT THE KILL ITSELF, WHICH IS NOT AN ARGUMENT FOR EITHER SIDE

The two defensible definitions differ by **ONE QUARTER of burn-in** (20 observations against
21, since 20 quarterly observations span 19 intervals = **4.75** years, not 5), and that one
quarter is worth **1.77pp** of eligibility. **The 60% bar sits inside that single step.** So
the kill cannot discriminate between two definitions at the resolution that separates them —
`MB15`'s *"a gate more than half of arbitrary mappings pass"* in a smaller costume. This is
reported because it is true of the bar whichever side it falls on, and it is **not** offered as
a reason to prefer either. **Any successor should set a burn-in bar that is not knife-edge to a
one-quarter definitional choice.**

## 0.8 THE DECLARATION, AND THE KILL'S OUTCOME ACCEPTED AS IT FALLS

**`E-6` MEANS THE OBSERVATION COUNT: `burn_in = 20`, `min_history_years = None`.**
Under it the census reads **60.607%**, the kill **does not fire**, and the arm runs. Both
census numbers travel with every statement of that fact, here and in the write-up.

**AND THE OBSERVATION COUNT IS NOT THE WEAKER CALENDAR REQUIREMENT IN PRACTICE, which is a
census fact rather than an argument:** at `burn_in = 20` the **median eligible row carries
10.018 calendar years** of its own history; only rows sitting exactly at the eligibility
boundary carry 4.75. The port invited precisely this check — *"a register can say '20
observations' and check whether its median row got five years or nine"* — and the answer is
**ten**.

---

## 1. THE QUESTION, AND WHY IT IS NOT ONE OF THE GRAVEYARDS

The composite scores a name against its PEERS at a date. It has never once scored a name
against **ITSELF**. `TIDEMARK`'s entire thesis is that "cheap versus its own history" is a
different statement from "cheap versus everything else", and this panel has never tested it.

**NOT `S20`/`S21`, AND THIS IS THE DISTINCTION THE WHOLE ITEM RESTS ON.** Those two swapped
the cross-sectional **standardiser** — rank instead of z-score, winsorised instead of not —
and both were rejected, `S20` while making the deciles *better* ordered. **`E-6` swaps
nothing.** It adds a COLUMN on a new axis and leaves every incumbent bit-identical; the
composite, the weights and the standardiser are untouched, and a test pins that the arm path
computes no book statistic at all. A standardiser swap changes how existing information is
expressed; this adds information that is not in the cross-section at any date.

**NOT `MA55`** (valuation-engine lens disagreement, design-recorded, different inputs).
**NOT `E-3`** (cross-theme dispersion — a non-linear function OF the incumbents, and its
orthogonality was guaranteed by construction; **this candidate uses the name's own PAST, which
is genuinely absent from every incumbent at date `t`**, so its orthogonality is earned rather
than automatic). **NOT the weighting family**, which moved weights.

## 2. THE OBJECT, FIXED EXACTLY

`value_pct(i,t)` = the expanding percentile of name `i`'s own `value` theme history up to and
including `t`, from the shipped `name_percentile.name_percentiles`, with:

* `burn_in = 20` **observations** (§0.8), `min_history_years = None`;
* `invert = False`. The panel's `value` theme is oriented high = cheap = good (its theme IC is
  positive), so a high percentile already means *"cheap against its own history"*, which is
  TIDEMARK's `cheapness` orientation. **`invert` is required by the API and is declared here
  because a sign error inverts every conclusion** — TIDEMARK's own words, and this record has
  three sign incidents already.
* `lag_days = 0`. The `value` theme is already point-in-time on the panel; adding a lag would
  double-count a lag the panel has applied.

**`history_years` and `n_history` are carried on EVERY scored row and shipped in the artifact**,
so *"five years"* is checkable by a reader rather than promised (the task's own requirement, and
the port's).

## 3. STATISTIC, BARS, HALVES

Primary: **incremental IC** on the incumbent themes, computed by the **shipped**
`surface_stock.arm_ic` / `residualise` and judged by the **shipped** `arm_verdict`. **The
incremental gate is what removes the cross-sectional value level by construction** — `value` is
itself an incumbent, so residualising on the seven leaves only what the name's own history adds.

`MB7`'s repaired gate via `incremental_ic.effective_coverage` and
`require_effective_coverage(..., split_used="effective")`, **effective coverage printed**.
**BOTH bases co-primary and the arm must clear BOTH** (`MB18`'s rule; taking one alone is
`MA58`'s void condition 5). The basis choice is not free here and is declared for `MB7`'s stated
reason: E-6's eligible window begins **2013-10-17**, which reaches back one quarter before
`institutional`'s first scoreable date of 2014-01-17, so the register is exposed and chooses
both rather than picking the kinder one.

**Declared sign: POSITIVE** — high own-history cheapness predicts HIGHER forward return. A
negative incremental IC is a **CONTRADICTION, never a pass, however large.**

Bar: **`IC_BAR = 2.71`** in **both halves**, X7's calibrated theme-IC p95. Stated plainly, as
the shipped constant states it: **AN EXTRAPOLATION** — X7 calibrated it on a RAW theme IC, and
`U2`, `MA31`, `MA32`, `MA58`, `MB18` and `E-3` have all applied it to an INCREMENTAL one. This
register inherits that precedent and does not pretend it is a calibration. Ambiguous against
the threshold is a **NULL** (`RUN_RULES` A6).

## 4. PRE-OUTCOME GATES — computed and read in their own pass

`--controls` writes `data/free_analysis/E6_CONTROLS.json`; **`--arms` REFUSES without it and
without `all_gating_pass`** (session 26's process defect, `O10`'s).

**K1 — THE BURN-IN CENSUS.** Re-derived from the shipped `burn_in_census` rather than read from
`I-2`'s JSON, and required to reproduce it. Kill: eligible row share **>= 0.60** at the declared
burn-in. **Resolved in §0 and accepted as it falls.** Both readings printed.

**K2 — `S18`'s DATE FLOOR.** The effective dates must split into halves of at least
`MIN_DATES = 16` each, checked by `MB7`'s gate on the EFFECTIVE dates rather than the raw ones.
Failing it is **UNPOWERED-BY-CONSTRUCTION**, not a null.

**K3 — NOT A RENAMED INCUMBENT (executor's addition; a control, never a producer).** Mean
per-date Spearman of `value_pct` against each incumbent; **|rho| > 0.90 against any single one
means the column is that incumbent under a new name** and the item is WITHDRAWN. The bar is
deliberately loose because the incremental gate already handles ordinary overlap by
construction; this catches only a duplicate. **Reported in full either way**, because the
interesting number is the one against `momentum`: a name at a high own-history value percentile
is one whose value score has RISEN, which is a change signal, and `V6` measured drawdown at
+0.66 against the momentum theme. **That correlation is a diagnostic and carries no verdict.**

**K4 — NO LOOK-AHEAD.** The port's own test asserts it; this register additionally requires the
census artifact's real-panel check (`max |delta| 0.000e+00` on a truncated panel) to be present
and passing.

### 4.3 THE CALENDAR SENSITIVITY — bounds §0's choice, carries NO verdict, charges NO trial

The identical arm is re-scored at `min_history_years = 5.0`, the reading §0 declined. **Same
hypothesis, same bar, one stated sensitivity on a definitional choice** — `E-5`'s C4 precedent,
and it can only ever WEAKEN the result, so it adds no degree of freedom.

**THE ASYMMETRY IS STATED BECAUSE IT IS REAL:** under that reading the burn-in census fails its
own kill (58.886%), so the calendar arm is **UNDERPOWERED BY ITS OWN GATE**. Therefore:

* if the two **DISAGREE**, the item is **UNRESOLVED** — conservative, and it is the outcome
  that would show §0's choice to have mattered;
* if they **AGREE**, that is **NOT** evidence the choice was immaterial, because an
  underpowered arm agreeing with a powered one is weak corroboration. Saying so is the point.

## 5. POWER — rule 11, both `MB22` vocabularies, printed BEFORE the verdict

`MB18`'s design class (~0.43 / 0.51 SD at 80% power; ~0.30 / 0.36 at 50%), with the **exact**
figures computed from `power_gate` on the realised effective rows and each labelled. A NULL is
quoted with `MB18`'s anchor: the strongest RAW anchor on rows of this shape is `z_fcf_margin`
at **0.4346 SD**, so a null means *"no effect at least as large as the best thing this panel has
ever carried"*, never *"no effect"*.

## 6. VOID CONDITIONS

1. Arguing from which side of 60% either census reading falls (§0.1).
2. Re-declaring the burn-in, `invert`, `lag_days`, the bar, the declared sign, either basis, or
   `MIN_DATES` after any arm value is read.
3. Any standardiser swap, weighting change, or use of `value_pct` in the book. **This adds an
   AXIS; `S20`/`S21` are the graveyard for the alternative.**
4. A second theme's percentile, a burn-in grid, or an interaction arm — each is a new
   hypothesis and charges its own trial. **One arm, no grid**, per the seed.
5. Reading the §4.3 sensitivity as a verdict, or quoting agreement there as evidence the
   burn-in choice was immaterial.
6. Reporting the primary verdict when it disagrees with §4.3 as anything but **UNRESOLVED**.

## 7. PRIOR AND EXPECTATIONS

**Prior: ~10% CONFIRMED**, the seed's own figure, adopted unchanged. The record's base rate
dominates; what argues faintly the other way is that unlike `E-3` this candidate carries
information genuinely absent from the cross-section, so its orthogonality is earned.

1. Verdict NULL — **85/15**.
2. `K3`'s largest |rho| is against **`value`** itself, not `momentum` — **60/40**.
3. The mean R2 on incumbents is **below 0.20** on both bases, i.e. materially lower than
   `E-3`'s 0.347/0.413, because this column carries out-of-cross-section information —
   **70/30**.
4. The sign, if anything shows, is POSITIVE as declared — **60/40**.
5. The two bases give the same verdict — **80/20**.
6. §4.3's calendar sensitivity agrees with the primary — **85/15**.
7. Median `history_years` on scored rows exceeds **8 years** — **80/20**.

## 8. WHAT IT DOES NOT DO

No product copy, no book change, no weighting, no second theme, no grid, no `MA55` claim, and
no adoption on any outcome — an eligible arm would be recorded **ELIGIBLE, not adopted**, and
would queue behind whatever vintage is open (`S20`/`S21`'s clause). One column, one bar, on an
axis this panel has never had.
