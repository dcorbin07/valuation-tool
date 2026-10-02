# PREREG — IC7: what renormalisation does to a name with a coverage hole

**Committed ALONE, markdown only, before any arm is scored**, and a strict git ancestor of every
commit that computes an outcome. The equity trial is booked in its own commit before the scoring
runner exists. **Executor pass on the Frontier Scout's `PREREG_DRAFT_ic7_coverage_renormalisation.md`
(ranked 2 of 6, on `origin/main` at `9c36d2a`): ACCEPTED WITH THREE AMENDMENTS**, each with its
reason, below.

---

## 0. The counter, re-read rather than quoted

`research_log.detail()` at this register's merge base: **equity 251, options 310, unified 0,
infra 20** — `REBAL-CADENCE` landed three equity trials since the draft was written, so the
draft's *"equity N 248, hurdle 3.3206712"* is **stale and is corrected here**. Equity `N` = 251,
`sqrt(2 ln 251)` = **3.3242902818892888**. This register books **1 equity trial** → `N` = 252,
`sqrt(2 ln 252)` = **3.3254861561917**. Derived, not typed (`MA19`, `MA37`).

**No permutation floor can move**: `MB31`'s mechanism — `N` reaches a floor only through the
CPCV adopt gate, so a floor moves only when a banked draw flips, and the next flip is seed
**1017 at `N` = 688**. Nothing here reads a permutation floor in any case.

---

## 1. The question

`composite_from_frame` **renormalises by the present-weight mass** (the `B7`/`G` convention, and
the one SELECTION has always used, which is why the deployed weights were chosen under it). So a
name missing a theme is scored on the themes it has, each carrying a larger share of the mass —
and **a name with a hole is being compared, inside one ranking, against a name scored on a
different composite.** Which one a name gets is decided by whether a 13F filer happened to
report it.

**ARM — ONE arm, no grid.** Impute a missing weighted theme at **the date's own cross-sectional
median of that theme** instead of renormalising, so every name is scored on seven themes at
identical weight mass. The deployed flat 1/7 is held fixed; no weight changes.

**IMPUTATION IS AN ASSUMPTION, NOT A CORRECTION**, and the register says so before the run. It
hands a name about which nothing is known the middle of the distribution.
`SECTOR-NEUTRAL-B6` measured the sharper version: both engine sector dicts fail open, so blanking
an unknown *"does not abstain — it hands the row the middle of a 2.70x range."* The arm's
abstention count is reported rather than a filled cell being treated as knowledge.

---

## 2. The free kills — ALL FIVE RUN AND READ BEFORE THIS REGISTER WAS COMMITTED

`MB1-SEL`: a control can only BLOCK, so all five cost nothing and precede the register.
`scripts/ic7_kills.py`, artifact `IC7_KILLS.json`.

| | kill | bar | measured | |
|---|---|---|---|---|
| **K1** | the exposure is not inert | >= 10% of rows | **41.69%** | **PASS** |
| **K2** | the era structure is REPORTED, not discovered | report it | see §3 | **REPORTED** |
| **K3** | not a size costume | mean per-date \|rho\| vs `size` < **0.60** (`R6`'s own, verbatim) | **0.0718** over 49 dates | **PASS** |
| **K4** | fidelity, and it ABORTS | max \|Δ\| **0.000e+00** on four published fields | **0.000e+00** | **PASS** |
| **K5** | no look-ahead | the date's OWN cross-section only | by construction, pinned by test | **PASS** |

**AMENDMENT 1 — THE DRAFT'S OWN EXPOSURE ESTIMATE IS LOW BY HALF, AND THE CORRECTION RUNS IN THE
ARM'S FAVOUR.** It predicts *"roughly 28% of panel rows"* from `institutional`'s 71.7% coverage.
Measured: **41.69%**, because `institutional` (28.28% missing) is not the only hole —
**`insider` 16.92%**, `capital_discipline` 3.18%, `quality` 2.09%, `momentum` 1.70%, while
`value` and `size` are **0.00%**. The draft reasoned from one theme and the exposure is the union
of five. Stated in advance as the draft asked, so the surprise is visible rather than
rationalised afterwards.

**`K4` reproduces the published record EXACTLY** — `top_decile_alpha` 0.07174142332098163,
long-short naive *t* 2.8360640685320595, HAC 2.6199121240414884, monotonicity
−0.8909090909090909, all at **0.000e+00** with the field count gated (`MB21`'s `C1` scored a
perfect zero on an empty frame by comparing nothing).

---

## 3. AMENDMENT 2 — THE ERA STRUCTURE IS SHARPER THAN THE DRAFT STATES, AND ONE HYPOTHESIS OF MINE ABOUT IT IS REFUTED

The draft says `institutional` is *"empty before 2013-06-30"*. **Measured, its first value on this
panel is 2014-01-17** — which is `RUN_RULES` rule 10's own figure, independently reproduced here.
The split is **20 dates before, 49 on or after**:

| | dates | WHOLLY absent | PARTIALLY absent |
|---|---|---|---|
| before 2014-01-17 | 20 | **`institutional` (all 20)** | `quality`, `momentum`, `insider`, `capital_discipline` |
| on/after | 49 | none | `institutional` (48), `insider`, `quality`, `capital_discipline`, `momentum` |

**A HYPOTHESIS OF MINE, TESTED BEFORE THIS REGISTER WAS WRITTEN AND REFUTED.** `V2G` proved a
UNIFORM absence cannot re-rank — renormalisation turns it into a scalar rescale identical for
every name — so I expected the 20 early dates to be **provably inert**, which would have made
the both-halves gate unclearable by construction and killed the item at zero trials. **Measured:
0 of 69 dates are uniform-only.** Even on the early dates where `institutional` is wholly
absent, `insider` and three smaller holes vary name by name, so the arm can re-rank on **every**
date. The kill does not exist and the item proceeds.

**WHAT SURVIVES IS `K2`'s REAL POINT, NOW QUANTIFIED: the two halves test DIFFERENT
INTERVENTIONS.** Early, the largest hole (`institutional`) contributes a uniform, non-re-ranking
component, so the arm's bite there is essentially **`insider`**; late, `institutional` is the
main re-ranking driver. The both-halves gate is therefore not measuring one thing twice, and the
write-up must say which half measured what rather than averaging them into a sentence.

---

## 4. Primary metric and the gate

**The shipped `holdout_compare_panels`, VERBATIM** — Δ long-short *t* **> +0.25** AND Δ
top-decile alpha **> +100 bps**, in **BOTH** halves, boundary embargoed, under **BOTH**
weightings, deployed flat 1/7 held fixed. The gate `SECTOR-NEUTRAL-B6`, `S14`, `S15`, `S3`,
`S16`, `W-1`, `MB20` and `REBAL-CADENCE` all used; reusing it verbatim is what stops a bar being
chosen after the fact.

**One panel, two scorings, a provably identical row set** — the arm differs from the incumbent in
the imputation alone, so a difference cannot be a difference of rows (`S3`'s and
`S25-REPAIR`'s construction).

**Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6). **ELIGIBLE, NOT
ADOPTED** — see §6.

## 5. THE MDE, measured before scoring

`V2G` and `R1-VAR`: **no calibrated floor exists for a paired within-panel difference**; `X7`
calibrates LEVELS. So every critical value here is **LABELLED UNCALIBRATED**, and the paired HAC
se is **measured on this arm** (`MB8` forbids borrowing one — `V2G`'s 0.9354pp was a whole-theme
swap, `MB8`'s 0.1106pp a sizing haircut, `REBAL-CADENCE`'s 0.6991–1.0586pp a cadence change, and
none is this perturbation).

**AMENDMENT 3 — THE DRAFT'S MDE PRIOR IS STATED AS A PRIOR AND NOT INHERITED.** It reasons the
perturbation *"moves each row by at most the difference between a 1/6 and a 1/7 weighting of one
theme"* and so should sit near `MB8`'s 0.1106pp, giving ~0.31pp at crit 2.0. **That reasoning
understates it**: 41.69% of rows are touched rather than 28%, and a row missing TWO themes moves
from 1/5 to 1/7 of mass, not 1/6 to 1/7. The register therefore commits to **measuring** the se
in the arm pass and printing the 80%-power MDE beside the verdict at the conventional crit 2.0
and at the honest hurdle, **rather than quoting the draft's figure**. If the margin sits below
the MDE the null is BOUNDED and must be reported as such — `S19` and `V6` both published nulls
their designs could not have distinguished from a true effect.

## 6. ADOPTS NOTHING — adoption is a VINTAGE EVENT

Changing how every live score is assembled ships in the live scoring path, so it closes the open
vintage and opens the next under `PAPER_TRACK_CONTRACT.md` §5a, **resetting the accrued
five-year clock for zero statistical gain** (`RUN_RULES` rule 6; the meter has 13.3% power at 60
months). **The vintage is DERIVED from `track_meter.VINTAGES` at write-up time and never quoted**
(`PT-GAPDUE`: three resets in four days, and the draft's own *"vintage 4, opened 2026-08-13"* is
a quoted date this register declines to repeat).

An eligible arm is recorded **ELIGIBLE — ROUTED TO DON** and is not adopted here. `CONFIG`
untouched, `settings.BOOK_CONFIGS` untouched, the banked panel not overwritten — pinned by test.

**The draft's asymmetry is accepted and is worth restating: this is a FIDELITY argument as much
as an alpha one.** Even a null is useful, because it would establish that the
two-composites-in-one-ranking exposure is immaterial — currently assumed rather than measured.

## 7. Void conditions

1. **No grid.** One arm, one imputation rule. A second imputation (zero, last-observation,
   cross-sectional mean) chosen after seeing this one voids the item.
2. **No bar relaxed after watching it fail** (`W-28`).
3. **No X7 floor quoted** on a paired difference (`V2G`, `R1-VAR`).
4. **The MDE travels with the verdict** (§5).
5. **The two halves may not be averaged into one sentence** without saying they test different
   interventions (§3).
6. **The deployed weights were selected under the incumbent convention**, so a pass is a
   statement about the shipped weights scored under a convention they were not chosen for. That
   confound runs AGAINST the arm and must be stated with any eligible result.

## 8. Expectations, registered before scoring

| | prediction | odds |
|---|---|---|
| 1 | **REJECTED on the primary.** Five weighting-family arms were rejected and CPCV's best challenger missed by 79x; anything changing how the composite is assembled inherits that prior | 75/25 |
| 2 | The paired HAC se lands **above** the draft's ~0.1106pp prior, because 41.69% of rows move and some move by more than a 1/6-to-1/7 step | 70/30 |
| 3 | The halves **disagree** — in sign or in magnitude by more than 2x — because §3 shows they test different interventions | 65/35 |
| 4 | The arm moves the composite **measurably but not much**: per-date rank correlation vs the incumbent above 0.97 | 70/30 |
| 5 | The LATE half shows the larger effect, because that is where `institutional` re-ranks | 60/40 |

## 9. What this register does NOT claim

It does not re-open `V2G`, whose IMMATERIAL verdict stands and which measured a different
object — a uniform, three-theme absence, which cannot re-rank. It does not re-open the weighting
family (`S5`, `S6`, `S13`, `S24`, `S27`). It says nothing about the LIVE path's coverage holes,
which `FIDELITY-2` changed and which are a separate question. It licenses no trade and changes no
product copy.
