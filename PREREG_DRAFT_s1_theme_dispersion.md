# PREREG DRAFT — S-SEED-1: the conviction statistic — theme dispersion per name
## Does a name the themes disagree on behave differently from one they agree on?

**DRAFT, Frontier Scout lane, 2026-08-20.** Commit ALONE, markdown only, counters re-read
first. **Trials: 1, equity** (235 → 236 at this writing; hurdle 3.3044 → 3.3057).

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

`disp(i,t)` = standard deviation across the name's **available** theme z-scores at `t`
(shipped z-columns, `B7` handling), **eligibility ≥ 4 computable themes** — `C7` measured
22.01% of rows carrying fewer than two computable inputs, and a variance of two numbers is
noise; the eligibility partition is reported, ineligible rows never scored as zero.

## 3. Statistic, bars, halves

Primary: **incremental IC** on the seven incumbents, `MB7` gate, both bases co-primary,
`split_used="effective"`, effective coverage printed. **Declared sign: NEGATIVE** (high
dispersion → lower forward return, the DMS direction). Bar: X7-calibrated incremental
threshold (re-read at run), both halves, ambiguous = NULL.

## 4. Pre-outcome kills (separate pass, read first — `R6`'s ghost gets three locks)

* K1: |per-date mean Spearman| of `disp` vs the **size theme** > 0.60 → WITHDRAWN — `R6`'s
  conviction aggregate died as a size sort; this one is not allowed to.
* K2: vs **|composite|** (the level's absolute value) > 0.60 → WITHDRAWN — under z-scoring,
  extreme means and large variances can be mechanically linked; a dispersion that just flags
  extreme names re-ranks the product and answers nothing.
* K3: vs the **count of available themes** > 0.60 → WITHDRAWN — a dispersion that measures
  coverage is a data-quality column (`S9`'s corpse), not a conviction statistic.

## 5. Power (A-11, both numbers)

`MB18`'s design class: **≈0.43 / 0.51 SD at 80% power (≈0.30 / 0.36 at 50%)** on the two
bases; exact figures printed from `power_gate.state()` on realized (eligibility-filtered)
coverage before the verdict. NULL is quoted with the "nothing as large as the panel's best
single anchor" sentence.

## 6. Void conditions

1. Any weighting or sizing use of `disp` — this register tests a column, it does not touch
   the book (`S13`'s instrument-mismatch lesson).
2. Interaction arms (disp × level, disp × anything) — `S7` closed casual interactions; each
   would be its own register.
3. Kills read in the arm's pass; skipped A-11 line; skipped co-primary basis.
4. Winsorising or transforming `disp` after seeing any outcome (`S21`'s ghost).

## 7. Prior and expectations

Prior: **~10%** CONFIRMED. Expectations: (1) K2 is the kill most likely to fire — 40/60
against firing, stated because the mechanical link is real; (2) verdict NULL — 80/20;
(3) the sign, if anything shows, is negative as declared — 65/35; (4) dispersion's largest
input correlation is with `institutional` coverage effects on basis seven — 55/45;
(5) one number contradicts this list — 60/40.

## 8. What it does not do

No product copy (a "conviction" label on the site would be a per-name precision claim —
`V3` forbids it), no book change, no interaction family, no `MA55` claim (different lenses,
still unrun, its own register). One column, one bar, and either answer sharpens what the
composite's mean is silently averaging away.
