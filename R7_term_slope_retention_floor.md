# R7 — the `term_slope` retention floor, re-committed

**Status: COMMITTED, results-free, 2026-08-03.** This document is the bar. It is written
**before** any re-score, which is the whole point of it — the audit's instruction was to argue the
floor from first principles and commit it in writing *before* R2 touches the banked log.

**R2 must cite this file by name.** If R2 re-scores against any other bar, that re-score is void.

---

## 1. Disclosure, first

I set this floor **already knowing** the two numbers it will be applied to: the incumbent floor is
**40%** and the observed out-of-sample retention is **36.4%**. That is unavoidable — the audit item
exists precisely because those numbers are known and the gap is 3.6pp.

The defence is the derivation's inputs. The floor below is a function of four quantities:

| input | value | where it comes from |
|---|---|---|
| `n` — trades in the universe | 3,042 | count, unconditional |
| `σ` — per-trade return sd | 0.8354 | unconditional, whole banked log |
| `deff` — cluster design effect | 2.24 | unconditional, by calendar month |
| `D` — kept-vs-dropped separation | 0.13670 | **fixed at adoption time (2026)**, not re-estimated |

**None of them is a retention figure**, and none is conditional on `term_slope`. The banked broad
log (`data/options_universe/state.pkl`) carries a `term_slope` column; I computed `σ` and `deff`
without ever conditioning on it. The retention-versus-gain curve — the one object that could tune
this floor toward a desired verdict — was not consulted.

**The floor below is looser in percentage terms than the 40% it replaces.** I am flagging that
rather than burying it. A reader should weigh it against the derivation and decide for themselves.

---

## 2. What the floor is actually for

The incumbent 40% collapses three distinct worries into one percentage and serves none of them well.

### (a) Cherry-picking — a retention floor is the wrong instrument

The real cherry-pick risk is *selection among many thresholds*: trying twenty cut-offs and reporting
the best. That risk is controlled by **freezing the threshold**, which this filter already does.
`+0.0105` was fitted on the 55-name 2016–2020 half and applied **unchanged** to 133 names that never
informed it.

**Once a threshold is frozen and applied out of sample, retaining 36% rather than 40% adds no
cherry-pick risk at all.** The out-of-sample design, not the retention share, is what makes the
result honest. A percentage floor was never the instrument for this worry — it only looked like one.

The one residual version of the worry that *is* real: if retention were extremely low — say 2% — the
filter would be selecting a peculiar corner of the space, and the out-of-sample guarantee would rest
on very few trades per new name. That is a count problem, and §3 handles it.

### (b) Statistical power — real, and a count, not a percentage

A filter that keeps few trades measures its gain with a large standard error. This constraint scales
with the **number** of trades retained. A percentage floor gets it exactly backwards: as the universe
grows, the retained *count* rises even as the retained *share* falls.

That is not hypothetical — it is what happened. The 55-name run cleared 40.6%; the 187-name run
retains **more trades** at 36.4%. **The filter got statistically stronger and the percentage bar
called it weaker.** A bar that moves the wrong way as evidence accumulates is misspecified.

### (c) Deployability — real, also a count, and a *product* decision

A filter that keeps too few alerts cannot fill a book. True, but it is Don's call what book size to
target, not a research threshold.

**Therefore the percentage floor is retired** and replaced by two independent arms, reported
separately and never merged into one pass/fail.

---

## 3. Arm A — power (research-owned, binding)

> **The filter must retain enough trades that the effect size which originally justified it would be
> detectable at t ≥ 2.0 under month-clustered inference.**

Measured unconditionally on the banked broad log (n = 3,042 closed trades, 185 names,
2016-01-19 → 2025-10-15):

- σ = **0.8354** per-trade return sd
- **deff = 2.24, clustering by calendar month.** This is the binding correlation and it is not the
  one you would guess: clustering by *ticker* gives only 1.29, and ticker×month gives 1.00. A
  market-wide volatility regime moves every open long call together, so trades in the same month are
  the dependent ones. **The log's 3,042 trades carry the information of about 1,360 independent
  ones.** Any floor that ignores this is overstated by roughly 50%.
- σ_eff = σ·√deff = **1.2503**
- D = 0.0812/(1 − 0.406) = **0.13670** — the kept-vs-dropped separation implied by the +8.12pp gain
  at 40.6% retention that got the filter adopted.

Solving `t = D / (σ_eff·√(1/k + 1/(n−k)))` at t = 2.0 with n = 3,042:

> ## **Arm A floor: k ≥ 383 retained trades** (12.6% of the current broad book)

**For a re-score on any other universe the floor is the formula, not the number** — re-solved with
that run's own `n`, `σ` and `deff`, and with **D held fixed at 0.13670**. D is an adoption-time
constant and is *never* re-estimated from the run being judged. That clause is what stops the bar
drifting to meet whatever result arrives.

Context, so the bar's location is legible (these are not the verdict — R2 owns that):

| slice | retained | implied t |
|---|---|---|
| new names, late half — *the strict out-of-sample test* | 412/1,132 (36.4%) | 1.77 |
| new names, full sample | 630/1,695 (37.2%) | 2.18 |
| whole broad book, late | 656/1,759 (37.3%) | 2.22 |

Note what this shows: on the strict out-of-sample slice the retained count (412) clears the 383
floor, but that slice's *own* n is 1,132 rather than 3,042, so its implied t is 1.77. **R2 must
apply the formula to the universe it actually scores**, and state which n it used. Quoting a floor
derived on 3,042 against a 1,132-trade slice would be an error, and it is the most likely way this
document gets misused.

---

## 4. Arm B — deployability (product-owned, reported, not gated)

Mean holding period on the broad log is **18.3 days** (median 18), so a position occupies ~5.0% of a
year and the unfiltered book generates **312 alerts/yr**.

| target concurrency | alerts/yr needed | implied retention |
|---|---|---|
| **10** — the repo's committed `MAX_CONCURRENT` (`valuation/edge/options_vrp.py:211`) | 200 | **63.9%** |
| 5 | 100 | 31.9% |
| **3** — floor of "this is a book at all" | 60 | **19.2%** |

> ## **Arm B floor: ≥ 3 average concurrent positions (≥ 60 retained alerts/yr).**

Below three concurrent positions the book is a handful of lottery tickets and no filter statistic is
worth acting on.

**The tension I am surfacing rather than resolving.** The repo elsewhere commits to a 10-position
book, and filling one would need **63.9% retention** — far more than `term_slope` keeps, or has ever
kept, *including on the 55 names that adopted it at 40.6%*. `MAX_CONCURRENT = 10` belongs to the VRP
credit-spread arm, so importing it wholesale into the single-leg long arm is a stretch, and that is
why Arm B is set at 3 rather than 10.

But the fact stands and Don should see it plainly: **no version of this filter has ever produced a
10-position single-leg book.** Arm B's constant of 3 is a judgement call; Arm A's 383 is derived.
That asymmetry is deliberate — the statistical bar should not be a matter of taste, and the product
bar is not mine to set.

---

## 5. The integrity arm

The threshold stays frozen at **+0.0105**. If R2 re-fits it — for any reason, including "the data is
now broader" — every out-of-sample claim attached to this filter is void and `term_slope` reverts to
**untested**, not to FAIL. Re-fitting is not a smaller sin than missing a floor; it is a larger one.

---

## 6. Committed verdict language

| outcome | verdict |
|---|---|
| Arm A passes **and** Arm B passes | **term_slope retention PASSES on the corrected bar.** B2 is re-stated from FAIL to PASS, with the original FAIL preserved in the record beside it, never overwritten. |
| Arm A fails | **FAIL**, irrespective of Arm B. |
| Arm A passes, Arm B fails | **PASS (research) / NOT DEPLOYABLE (product)** — reported as two facts, never averaged into one. |

An ambiguous result against these bars is a **null**, not a judgement call.

---

## 7. What this does not do

This document does **not** re-score anything and does **not** claim `term_slope` passes. It replaces
a misspecified bar with a derived one and hands the scoring to R2.

**R2 is still gated on B1** — `term_slope` on the broad universe is computed from a corrupted spot
price, so no re-score is valid until the price basis is fixed. Committing this floor now is exactly
the right order of operations: the bar is fixed while the result is still unknowable.
