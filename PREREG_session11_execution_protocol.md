# EXECUTION PROTOCOL — Session 11, executing `PREREG_ml_combiner.md`

**Written and committed BEFORE the executor was run and before any verdict-half row was read.**
This file adds nothing to the register and cannot loosen it. It states only (a) how ambiguities in
the register were resolved, and (b) the bug-discovery protocol, which the task required in advance.

## Bug-discovery protocol — stated before first touch

1. **Before either verdict half is touched**, the executor is exercised end-to-end **on decide-half
   dates only**. Anything found in that window may be repaired freely: no verdict row has been read,
   so nothing is spent.
2. **The verdict half of each direction is measured exactly once**, inside a single scripted run of
   `scripts/ml_combiner.py`, and that script is **committed before it is run**.
3. **After a direction's verdict measurement, that direction is FROZEN.** If a bug is discovered
   afterwards — in the model code, the scoring, the split, anything — the affected direction is
   reported as **CONTAMINATED** and its number is quoted with that label. **It is not quietly
   re-measured, and a re-measured number is not published as the result.** A corrected re-run may
   be reported only as an explicitly-labelled second, contaminated observation.
4. **A crash is not a measurement.** If the run fails before producing a verdict number for a
   direction, that direction has not been measured and may be re-run — the distinction being
   whether a verdict-half statistic was ever computed and observed.
5. **No inspection of verdict-half outcomes before both directions are complete.** The executor
   prints decide-half diagnostics as it goes and writes every verdict number at the end, so there
   is no point at which a partial verdict could inform a choice.

## Register ambiguities, resolved in the LESS favourable direction (RUN_RULES A6)

The register says "split the 69 dates at the midpoint into a DECIDE half and a VERDICT half, with
a one-rebalance-date embargo at the boundary". Three readings were possible; each is resolved
strictly:

1. **Which date the embargo consumes.** 69 dates do not halve evenly. **Resolved: the boundary
   date `dates[34]` is DROPPED ENTIRELY from both halves in both directions**, giving 34 decide
   dates and 34 verdict dates. The alternative — embargoing only the training side — would leave
   35 dates on one side and is the more generous reading. The dropped date is the same in both
   directions, so the two directions are exact mirrors.
2. **What "mean out-of-sample rank IC" averages over.** **Resolved: per-test-date Spearman of the
   model's prediction against `fwd_ret`, averaged over that path's test dates, then averaged over
   the 15 CPCV paths** — identical to `cpcv_validate.ic_score`'s own convention, so the tree is
   selected by exactly the statistic the linear weight schemes are selected by.
3. **Ties in grid selection.** **Resolved: the FIRST grid point in the registered enumeration
   order wins**, which is the lowest-capacity model (`max_depth=2, learning_rate=0.03,
   max_iter=100`). A tie broken toward the simpler model cannot flatter the tree.

## Two things the register fixes that this file restates only to be checkable

- **Eight grid points, not nine.** A grid point that fails to fit is a failed grid point and is
  recorded as such; it is not replaced.
- **Theme z-scores only.** The raw-signal variant is a separate future pre-registration.

## The comparison that travels with the result whatever it says

The concurrent parameter-search lane measured what selection on this panel does when it is allowed
to: **+8.43%/yr in-search collapsing to −0.04%/yr on a locked hold-out.** That is the base rate for
"a number chosen on this panel", and it is quoted next to the combiner's result whether the
combiner is favourable or not.
