# PRE-REGISTRATION — `MA19` (recalibrate X7's floors at today's `N`) + `MA13` (tamper-evidence for `N`)

Committed **alone**, before any new floor is computed, as a strict git ancestor of every
measurement commit. Written 2026-08-14.

---

## 0. WHAT THIS IS, AND WHAT WAS ALREADY SEEN BEFORE IT WAS WRITTEN

`MA19` asks for a **recalibration**, not a hypothesis test. There is no edge being proposed, no
adoption available, and no arm that can "pass". The deliverable is a table: **old bar vs new bar
for every X7 floor**, plus a statement of which shipped claims change their relationship to their
bar. `MA13` is an **integrity check** on the denominator those bars are computed against.

**NON-BLINDNESS, DISCLOSED HERE RATHER THAN AFTERWARDS (the `U3` §0.5 precedent).** Scoping this
register required reading the bank, so the following were known before this file was written:

* the structure of `data/free_analysis/X7_RECONCILE.json` and `PLACEBO_HAC.json`;
* the **adopt curve**, and that at `N` = 224 there are **18 adopters** against 20 at `N` = 129 —
  so **exactly two draws flip**, seeds **1050** and **1096** (three flip against X7's own
  `N` = 84: 1005, 1050, 1096);
* that **only 1 of 100** banked rows (seed 1005) carries both weight-scorings;
* the banked `N` = 121 null percentiles, which are session 10's own published artifact.

**What is NOT known and is the object of this register: the `N` = 224 floors.** They cannot be
read from the bank, because the two flipped draws have never been scored under base weights.

---

## 1. THE PREMISE, MEASURED

* Live equity `N` = **224** (`research_log.detail()["by_domain"]`: equity 224, options 292,
  infra 14, unified 0).
* `_trials_haircut(n) = sqrt(2·ln(max(2, n, _trial_N())))`, so the haircut is
  **3.1176 at `N` = 129 → 3.2899 at `N` = 224**, a 5.5% higher adopt bar.
* The CPCV adopt gate (`fundamental_panel.py:3093`) is
  `margin > _trials_haircut(...) · se` **and** `folds_positive ≥ 0.6` **and**
  `median_oos_ic_best > 0`. Only the first term reads `N`, so **adoption is monotone decreasing
  in `N`** and the flip set can only shrink.

## 2. THREE CHANNELS, AND EACH IS TO BE **VERIFIED, NOT ASSUMED**

`N` reaches the placebo distribution by at most three routes. The register fixes the claim; the
measurement must confirm it, and a channel that behaves otherwise is reported as a finding.

* **CHANNEL A — ADOPTION (indirect).** `N` → haircut → which draws adopt → which weight vector
  scores that draw → `long_short_tstat`, `long_short_tstat_nw`, `top_decile_alpha` and its
  *t*-statistics, `monotonicity`. **Only the flipped draws can move.** 98 of 100 are unchanged
  by construction, and that is checkable rather than assumed.
* **CHANNEL B — DIRECT.** `N` enters the Deflated Sharpe's own formula through `sr0_benchmark`.
  **Every draw moves**, including the 98 that do not flip. This is arithmetic from the banked
  `sharpe_per_period`, `var_sr_across_trials` and `n_periods`.
* **CHANNEL C — NONE (claimed invariant).** `max_abs_theme_ic_t` is computed per theme from the
  panel with no weight vector and no haircut; `pbo` is computed inside `cpcv_validate` from the
  scheme comparison and never multiplies `se`. **Both are predicted EXACTLY invariant except
  through Channel A on the two flipped draws** — and PBO/theme-IC are per-draw quantities that
  do not depend on which scheme was adopted, so they are predicted invariant **even there**.
  If either moves on a non-flipped draw, the channel map is wrong and that is the finding.

## 3. METHOD — FIXED HERE, IN THIS ORDER

1. Reproduce the adopt curve from banked `(margin, se, folds_positive, median_oos_ic_best)`
   using the gate's own arithmetic. **Control C1 must pass before anything else runs.**
2. Compute the adopt set at `N` = 224 and take the flip set against `N` = 129 (as-run).
3. **Re-score ONLY the flipped draws**, on the **same panel checkpoint**
   (`data/free_analysis/panel_corrected_69d.pkl`), the **same seeds**, the **same permutation
   instrument** (`fundamental_panel.placebo_panel`), the **same horizon**, through the **same**
   `quantile_backtest` — under **base** weights (`current-default`), which is what a
   non-adopting draw is scored under. Re-scoring under **challenger** weights as well is the
   round-trip control (C4).
4. Rebuild the 100-draw distribution at `N` = 224 by substituting the re-scored draws, leaving
   the other 98 **bit-identical** to the bank.
5. Recompute the Deflated Sharpe for **all** draws at `N` = 224 (Channel B), from banked inputs.
6. Recompute every floor with the **same percentile definition the published floors used** —
   `np.percentile(v, p)`, linear interpolation, `p` = 95 for upper floors and `p` = 5 for PBO.
   No change of estimator, no bias correction, no smoothing.
7. Report **old bar → new bar** for: long-short naive p95, long-short HAC p95, top-decile alpha
   margin p95, top-decile alpha HAC *t* p95, theme IC *t* p95, PBO p05, Deflated Sharpe p95.
8. For every shipped claim gated on one of those bars, state whether its **relationship to its
   bar changes**. Corrections are made **in place, called out**, per house convention.

## 4. CONTROLS — pre-committed, and C1/C2 GATE the run

* **C1 (GATING).** The adopt curve recomputed from the bank must reproduce session 12's
  published curve **exactly**: `N` = 8 → 27, 84 → 21, 116/121/129 → 20, 200 → 18, 400 → 17.
  A mismatch means the gate arithmetic is not the shipped one; **abort before reading any floor.**
* **C2 (GATING).** At `N` = 129 the pipeline must reproduce session 10's published floors to the
  digit: naive p95 **2.1437**, HAC p95 **2.2837**, alpha HAC *t* p95 **2.2913**, PBO p05
  **0.1967**. This is the harness-reproduction check; a floor that cannot reproduce the old
  value may not be quoted as the new one.
* **C3.** Monotonicity of adoption: the `N` = 224 adopter set must be a **subset** of the
  `N` = 129 set. Any draw that *starts* adopting at higher `N` falsifies the stated mechanism.
* **C4 (ROUND TRIP).** Each flipped draw re-scored under **challenger** weights must reproduce
  its banked `PLACEBO_HAC` statistics to ≤ 1e-9. This proves the re-score harness is the same
  instrument that produced the bank, rather than a lookalike.
* **C5.** The 98 non-flipped draws must enter the new distribution **bit-identical** to the
  bank (max |Δ| exactly 0.000e+00). Any drift means the substitution touched more than it should.
* **C6.** Channel C invariance, **measured**: `max_abs_theme_ic_t` and `pbo` on the re-scored
  flipped draws must equal their banked values.
* **C7.** The real (unshuffled) headline must be quoted from the record unchanged — this
  register re-measures the **null**, never the strategy. `long_short_tstat_nw` stays
  2.6199121240414884.

## 5. PRE-COMMITTED EXPECTATIONS (scored afterwards, right or wrong)

1. The long-short HAC floor **falls** at `N` = 224 (fewer adopters → fewer draws receiving the
   adoption bonus). **75/25.** This is MA19's own stated hypothesis and it is charged as mine too.
2. The move is **small** — under 0.15 of a *t* — because 2 draws of 100 cannot shift a p95 far.
   **70/30.**
3. `max_abs_theme_ic_t` p95 and `pbo` p05 come back **exactly** invariant. **85/15.**
4. The Deflated Sharpe floor **falls** (Channel B: higher `N` → higher `sr0` → lower DSR for
   every draw). **90/10.**
5. **No shipped claim changes its relationship to its bar.** **70/30.**
6. At least one published bar turns out to have **already drifted** at `N` = 121 and been
   carried forward unread. **60/40.**

## 6. VOID CONDITIONS

1. Any change to the permutation instrument, the panel checkpoint, the seed list, the horizon,
   or the percentile estimator voids the comparison — the whole point is that only `N` moves.
2. Re-running with a different seed set and reporting whichever is friendlier.
3. Reporting a new floor without its old value beside it.
4. **Charging this work an equity trial.** See §7 — it would invalidate its own denominator.
5. Silencing or relaxing C1/C2 to let the run proceed.

## 7. TRIAL COST — **ZERO**, and the reason is not bookkeeping

A calibration searches nothing: no hypothesis is tested, no threshold is cleared, no adoption is
available. Session 10's HAC re-derivation is the precedent and it charged zero.

**There is also a self-referential reason, which is the sharper one.** `N` is the input to the
very floors being computed. A recalibration that charged itself a trial would move `N` to 225 and
**invalidate the number it had just produced** — the floors would describe a denominator that no
longer existed the moment they were written. **Equity `N` stays 224.** `MA13` likewise charges
nothing to equity; it is infrastructure.

## 8. `MA13` — THE INTEGRITY STAMP

The audit's specification, followed rather than reinterpreted: **assert `by_domain` against a
committed expected dict**, so changing `N` requires deliberately editing the expectation in the
same commit — the `test_track_meter` vintage idiom.

* The expected dict is **committed in the test file**, so a diff shows it.
* The failure message must name **what changed and by how much**, and must say that the correct
  response to an intentional change is to edit the expectation **in the same commit**, not to
  delete the assertion.
* It must fail in **both** directions — a silent *rise* in `N` is a smaller hazard than a fall
  but is still an unrecorded change to a published denominator.
* **The test must be checked for vacuity**: a guard that passes because it reads nothing is the
  defect it exists to prevent (M6's lesson). It must be demonstrated to FAIL on a tampered
  count before it is trusted.
* **Deliberately NOT done:** wiring `N` into a runtime assertion that could abort a backtest.
  `N` legitimately rises whenever research lands; the stamp is tamper-**evidence**, not a lock.

## 9. WHAT THIS DOES NOT DO

* It does **not** re-run the 3.4-hour sweep. It re-scores **two draws**. MA19's claim that "the
  check is arithmetic, not a sweep" is therefore **half right**, and the register says so before
  the result: the **adopt set** is arithmetic, the **floors** are not, because 99 of 100 banked
  rows carry only the scoring that the as-run adoption chose.
* It does **not** recalibrate the `fixed_weights_null` (`S22`/`X1`), the cost table (`B11`) or
  the fidelity bar — none reads `N`, and MA19 itself calls them provably insensitive.
* It does **not** touch the learner's 1.64σ floor (`MA2`), which is a separate row.
* It does **not** re-open any verdict. A floor moving does not re-adjudicate an arm; it changes
  what a future arm must clear, and changes how an existing claim is **quoted**.
