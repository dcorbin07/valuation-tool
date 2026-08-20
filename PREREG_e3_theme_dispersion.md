# PREREG_e3_theme_dispersion.md — E-3 / S-SEED-1: the conviction statistic
## Does a name the seven themes DISAGREE on behave differently from one they agree on?

---

# EXECUTOR'S ACCEPTANCE — read this first

**I ACCEPT the Frontier Scout's draft `PREREG_DRAFT_s1_theme_dispersion.md` and adopt its
object, its mechanism, its three kills, its void conditions and its verdict grammar. The
draft's body is reproduced below from §0, edited only where this block says so.** The draft is
good work: the not-a-costume clause was checked rather than asserted and it HOLDS (verified
independently below), the three kills are the right three, and §6.1's refusal to let `disp`
touch the book is exactly `S13`'s lesson.

**Committed ALONE, markdown only, zero `.py`, as a strict git ancestor of every measurement
commit. ONE equity trial, booked in its own commit BEFORE the runner exists.**

## A. COUNTERS RE-READ, NOT QUOTED (`MA37`, fifth time on this record)

The draft says *"235 -> 236 at this writing; hurdle 3.3044 -> 3.3057"*. Measured from
`research_log.detail()` after merging `origin/main`: **equity 238, options 305, infra 19**, so
this item takes equity **238 -> 239** and the HLZ hurdle **3.3082535192066147 ->
3.3095206758476405**. The draft's figures were correct when written and are stale now; two
lanes (`E-5`, `E-1`) landed equity trials in between. **Nothing in the draft depends on them.**

## B. FIVE DEPARTURES, DECLARED BEFORE ANYTHING IS RUN

**(B1) THE DRAFT'S ELIGIBILITY JUSTIFICATION CITES AN UNRELATED MEASUREMENT.** §2 supports the
`>= 4` floor with *"`C7` measured 22.01% of rows carrying fewer than two computable inputs"*.
That figure is `MA28-CARD`'s C7 and it counts **accounting-flag inputs** — `beneish_m`,
`altman_z`, external financing (`scripts/ma28_riskcard.py:244`) — **not theme columns**. It
says nothing about theme availability. **The floor is KEPT at `>= 4`** on its own merits — the
sample SD of two or three numbers is a poor estimate of a spread, and a variance over two
points is a rescaled absolute difference — **and the real theme-availability distribution is
MEASURED in the controls pass and printed, rather than borrowed.**

**(B2) "SHIPPED z-COLUMNS" IS NOT WHAT THE COMPOSITE AVERAGES, AND THE DIFFERENCE IS LARGE.**
The panel's theme columns are *means of z-scored numbers*, so their cross-sectional spreads
differ by theme — `S3` measured `quality` (ten inputs) at a per-date sd near **0.50** against
`insider` (one input) near **0.96**. A dispersion taken over those raw columns would be
dominated by the single-input themes and would not be the spread of the quantities the
composite actually averages, because `composite_from_frame` **re-standardises every theme
column per date** before weighting. So `disp` is defined over the **per-date standardised
theme columns produced by the shipped `zscore`**, and an identity control (C-IDENT, gating)
proves they are the same numbers.

**(B3) `disp` IS DEFINED PER BASIS.** The draft scores both bases co-primary but leaves `disp`
defined over "available themes". Residualising on six incumbents while dispersing over seven
would put `institutional` inside the statistic and outside the control. **`disp` is computed
over the themes of the basis it is scored against**, and the two bases therefore carry two
`disp` columns, named `disp_six` and `disp_seven`.

**(B4) `K3` IS DEGENERATE ON THE ARM'S OWN ROWS, BY CONSTRUCTION.** `residualise` drops any row
missing an incumbent, so every scored row carries the **complete** basis and the count of
available themes is **constant** there — a Spearman against a constant is undefined, not a
pass. `MB21`'s C1 scored a perfect 0.000e+00 by comparing nothing, and this would be the same
shape. So the three kills are evaluated on **BOTH** populations — the eligible panel rows,
where the count genuinely varies, **and** the arm's scored rows — and a kill **FIRES IF EITHER
EXCEEDS ITS BAR**, which is stricter than either alone (`MB16`'s device). On the scored rows
K3 is reported **STRUCTURALLY ABSENT** rather than passing.

**(B5) THE COMPOSITE COMES FROM `composite_from_frame` AND IS NEVER RE-IMPLEMENTED** (`B7`, and
`E-1` re-proved the cost of a second copy days ago). The one thing this register supplies is
the standardised matrix `Z` it takes a row-wise SD over, and **C-IDENT gates on
`composite(Z, w)` reproducing `composite_from_frame(...)` elementwise at max |delta|
0.000e+00** — both sides shipped functions, so the identity is what proves `disp` and the
composite are two moments of ONE object rather than two lookalikes.

## C. AN INTERPRETIVE CONSTRAINT THE DRAFT DOES NOT STATE, AND IT BINDS THE HEADLINE

**`disp` IS A DETERMINISTIC FUNCTION OF THE VERY COLUMNS IT IS RESIDUALISED AGAINST, AND
`residualise` IS LINEAR.** `surface_stock.residualise` runs a cross-sectional OLS of the
candidate on the incumbents and keeps the residual; a row-wise standard deviation is a
NON-linear function of those same incumbents, so **a linear projection cannot remove it and
orthogonality here is guaranteed by construction.** Two consequences, both binding:

1. **A high mean R2-on-incumbents would be the surprise, not a low one.** The `R2` figure this
   template usually reports as evidence of new information is, here, evidence of nothing.
2. **A surviving incremental IC may NOT be described as "new information".** It would mean that
   a particular non-linear transform of the incumbents predicts where their weighted mean does
   not — a claim about FUNCTIONAL FORM, which is a real and interesting claim and a different
   one. `CLAUDE.md` records structural orthogonality as a motivation nobody should run again
   after four failures; **this register does not rest on it and must not be read as doing so.**

## D. WHAT I CHECKED RATHER THAN ACCEPTED

The draft's §0 premise **HOLDS**. No module computes a cross-theme dispersion: the only `disp`
in the tree is `scripts/s5_s6_s13_s24_s27_weighting.py:343`, `S24`'s mean per-name **rank**
dispersion across bootstrap **draws** — a stability object over resamples, not a spread across
themes within a name — exactly as the draft says. `MA55` is confirmed
`DESIGN-RECORDED - NOT RUN` and is about the **valuation engine's three lenses**, different
inputs entirely. The weighting family (`S5`/`S6`/`S13`/`S24`/`S27`) moved WEIGHTS and is
rejected; **this adds a column and moves no weight**, which §6.1 then forbids it from ever
doing.

## E. PRIOR — MINE, NOT THE DRAFT'S

The draft says **~10%**. I register **~8%**, and the reason is §C: the arm's chief structural
advantage — surviving residualisation — is guaranteed rather than earned, so the usual reading
of a surviving residual does not apply. Everything else in the draft's §7 I adopt unchanged and
score as written.

---

# (the Scout's draft follows, edited only as declared above)

## 0. Premise, verified

The composite is a weighted MEAN of theme z-scores; **no row in the 289-row ledger or the
134-item audit set has ever made the cross-theme VARIANCE for a name an object.** The nearest
relatives, cited so this is checked rather than asserted: `MA55` (disagreement across the
*valuation engine's three lenses* — design-recorded, never run, different inputs); `S24`
(ensemble across bootstrap *draws* — a stability object, not a per-name statistic); `R6`
(the SF3 "conviction" family — six *signals* whose aggregate decomposed into a **size sort**
and was closed; the autopsy, not the name, is what binds here); the weighting family
(rejected — but this adds a COLUMN and moves no weight).

## 1. Mechanism, with literature and status

Disagreement-as-signal has a real literature: Diether–Malloy–Scherbina (JF 2002) — high
analyst-forecast dispersion predicts LOW returns (Miller overpricing under short constraints);
Johnson (JF 2004) reframes it as levered unpriced risk. Status: published, heavily cited,
**weakened post-2000s and concentrated in small caps** per later work — treated as hypothesis.
The local translation is an *analog*, not an import: the seven themes are seven measurement
lenses on one firm; a name where they disagree violently is a contested-information name, and
the composite's mean throws that state away. Whether contested names underperform (Miller) or
merely carry noise is exactly what the declared sign encodes.

## 2. The object, fixed exactly

For a basis `B` (six or seven themes, §3) and a date `t`, let `Z` be the per-date standardised
theme matrix over `B` — **the shipped `zscore`, the same standardisation
`composite_from_frame` applies**, gated by C-IDENT (B2, B5).

`disp(i,t)` = the **sample standard deviation (`ddof=1`) across name `i`'s available columns of
`Z`**, eligibility **`>= 4` available themes**. Ineligible rows are **never scored as zero**;
the eligibility partition is measured and printed. Two columns result, `disp_six` and
`disp_seven`, each scored only against its own basis (B3).

## 3. Statistic, bars, halves

Primary: **incremental IC** on the basis incumbents, computed by the **shipped**
`surface_stock.arm_ic` / `residualise` and judged by the **shipped** `arm_verdict` — no second
implementation of either (`B7`). `MB7` gate via `incremental_ic.effective_coverage` and
`require_effective_coverage(..., split_used="effective")`, **both bases co-primary and the arm
must clear BOTH** (`MB18`'s rule; taking one basis alone is choosing the design to buy power,
`MA58`'s void condition 5). Effective coverage printed.

**Declared sign: NEGATIVE** (high dispersion -> lower forward return, the DMS direction). A
positive incremental IC is a **CONTRADICTION, never a pass, however large** — `arm_verdict`
enforces this and it is the shipped behaviour.

Bar: **`IC_BAR = 2.71`**, X7's calibrated theme-IC p95, in **both halves**. Stated plainly
because the shipped constant says it too: this is **AN EXTRAPOLATION** — X7 calibrated it on a
RAW theme IC, and `U2`, `MA31`, `MA32`, `MA58` and `MB18` have all applied it to an INCREMENTAL
one. This register inherits that precedent and does not pretend it is a calibration.
Ambiguous against the threshold is a **NULL** (`RUN_RULES` A6).

## 4. Pre-outcome kills (separate pass, read first — `R6`'s ghost gets three locks)

Evaluated on **BOTH** the eligible panel rows and the arm's scored rows; **a kill fires if
EITHER reading exceeds its bar** (B4). Mean per-date Spearman throughout.

* K1: |mean per-date Spearman| of `disp` vs the **size theme** > 0.60 -> WITHDRAWN — `R6`'s
  conviction aggregate died as a size sort; this one is not allowed to.
* K2: vs **|composite|** (the level's absolute value) > 0.60 -> WITHDRAWN — under z-scoring,
  extreme means and large variances can be mechanically linked (`mean^2 + var = mean of
  squares`, so a name of near-constant norm has them in exact opposition); a dispersion that
  just flags extreme names re-ranks the product and answers nothing.
* K3: vs the **count of available themes** > 0.60 -> WITHDRAWN — a dispersion that measures
  coverage is a data-quality column (`S9`'s corpse), not a conviction statistic. **On the arm's
  scored rows this count is CONSTANT by the complete-case rule, so K3 is reported STRUCTURALLY
  ABSENT there and its verdict comes from the eligible population** (B4).

The controls pass writes its artifact and **`--arms` REFUSES without it and without
`all_gating_pass`** (session 26's process defect, `O10`'s, not repeated).

## 5. Power (A-11, both numbers)

`MB18`'s design class: **~0.43 / 0.51 SD at 80% power (~0.30 / 0.36 at 50%)** on the two
bases; **exact figures printed from `power_gate` on the realized (eligibility-filtered,
effective) rows BEFORE the verdict**, in both `MB22` vocabularies and each labelled. A NULL is
quoted with the *"nothing as large as the panel's best single anchor"* sentence — and with the
`MB18` measurement behind it: the strongest RAW anchor on rows of this shape is
`z_fcf_margin` at **0.4346 SD**, so a null here means *"no effect at least as large as the best
thing this panel has ever carried"*, never *"no effect"*.

## 6. Void conditions

1. Any weighting or sizing use of `disp` — this register tests a column, it does not touch
   the book (`S13`'s instrument-mismatch lesson).
2. Interaction arms (disp x level, disp x anything) — `S7` closed casual interactions; each
   would be its own register.
3. Kills read in the arm's pass; skipped A-11 line; skipped co-primary basis.
4. Winsorising or transforming `disp` after seeing any outcome (`S21`'s ghost).
5. Changing the eligibility floor, `ddof`, the bar, the declared sign, or either basis after
   any arm value is read.
6. Describing a surviving incremental IC as **new information** (§C).

## 7. Prior and expectations

Prior: **~8% CONFIRMED** (the draft's ~10%, revised down for §C's reason — see E).
Expectations: (1) K2 is the kill most likely to fire — **40/60** against firing, stated because
the mechanical link is real; (2) verdict NULL — **80/20**; (3) the sign, if anything shows, is
negative as declared — **65/35**; (4) dispersion's largest input correlation is with
`institutional` coverage effects on basis seven — **55/45**; (5) one number contradicts this
list — **60/40**. Added by the executor and scored the same way: (6) the mean R2 on incumbents
is **above 0.20 on both bases**, i.e. materially higher than the 0.027-0.145 band four
orthogonality-motivated items reported, because `disp` is a function of those very columns —
**70/30**; (7) the `>= 4` eligibility floor costs **under 2%** of otherwise-scoreable rows —
**75/25**.

## 8. What it does not do

No product copy (a "conviction" label on the site would be a per-name precision claim —
`V3` forbids it), no book change, no interaction family, no `MA55` claim (different lenses,
still unrun, its own register). One column, one bar, and either answer sharpens what the
composite's mean is silently averaging away.
