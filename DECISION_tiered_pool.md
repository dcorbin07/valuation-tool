# Should smaller companies be let in on a stricter bar? — `TIERED-POOL`

**For Don. Prepared under `PREREG_tiered_pool.md`, whose pass rule was fixed in your own words
before any number was read. Nothing is adopted; the October 22 rebalance stays on the incumbent.**

---

## The short answer

**No. Neither version beats today's Index, and both fail your rule on the modern period — on
return *and* on drawdown.**

But the result is not uniform, and the split is the interesting part:

* **2009-2026** (the honest, corrected universe): the tiered arms **lose**. Arm A earns
  **14.45%** against the incumbent's **18.02%**, and its worst drawdown is **−41.96%** against
  **−28.96%** — **13 percentage points worse**, four times your 3pp allowance.
* **1999-2008** (a labelled five-theme proxy): the tiered arms **win**. Arm A earns **13.85%**
  against the incumbent's **8.30%**, with a *slightly better* drawdown.

Your rule requires **both** periods, so both arms fail. **The two periods disagree in sign** —
which is this project's most repeated pattern and the reason the rule asked for both.

---

## The numbers

**2009-2026, corrected universe, all seven themes, same construction throughout:**

| arm | net Roth | drawdown | early half | late half | turnover | cost |
|---|---|---|---|---|---|---|
| **incumbent $10B** | **18.02%** | **−28.96%** | 19.74% | 16.03% | 2.81 | 9.4 bps |
| A — stricter by size | 14.45% | −41.96% | 16.26% | 12.18% | 3.15 | 31.1 bps |
| B — A plus a junk filter | 15.51% | −35.98% | 17.75% | 12.92% | 3.25 | 24.1 bps |

**1999-2008, five-theme proxy (levels not comparable to the above):**

| arm | net Roth | drawdown | early half | late half |
|---|---|---|---|---|
| incumbent $10B | 8.30% | −41.76% | 7.40% | 8.99% |
| **A — stricter by size** | **13.85%** | **−40.98%** | 24.88% | 2.04% |
| B — A plus a junk filter | 12.41% | −46.80% | 25.37% | −0.02% |

**Your rule, step by step.** Arm A fails all three 2009-2026 return comparisons and the
2009-2026 drawdown clause; it passes both 1999-2008 legs. Arm B fails the same three return
comparisons and **both** drawdown clauses. Neither passes.

---

## Three things worth knowing beyond the verdict

**1. The junk filter genuinely helps — on the modern period.** Arm B beats arm A by **+1.06pp**
of return and **+5.98pp** of drawdown on 2009-2026, which is the direction the Asness et al.
paper predicts. It is just not enough to reach the incumbent. **And it reverses on 1999-2008**,
where arm B is 1.44pp *worse* than arm A and its drawdown is 5.8pp worse. So "control your junk"
helps in the recent era and hurts in the dot-com one, on this construction.

**2. Neither result is big enough to be sure of — and that cuts both ways.** Arm A's 2009-2026
shortfall is **0.40×** its own detection threshold, and arm A's 1999-2008 *win* is **0.28×**
its own. So the loss is not statistically established and neither is the win. The rule is a
**preference** rule — it decides on point estimates, by design — and I am not calling anything
significant.

**3. It is substantially a size bet, which is what §5 of the register existed to show.** Both
arms hold far smaller names and load far more on the size factor:

| | weight under $2B | SMB loading | unexplained residual |
|---|---|---|---|
| incumbent | **0.0%** | +0.219 | +1.82%/yr (t 1.05) |
| arm A | **37.8%** (max 55.0%) | **+0.602** | −1.98%/yr (t −1.04) |
| arm B | 24.1% (max 44.9%) | +0.458 | −0.16%/yr (t −0.10) |

**Not one arm's residual is separable from zero**, on either period. So there is no evidence the
tiering is picking better companies — only that it is holding smaller ones, and on 2009-2026 that
was punished. The micro-cap exclusion did work: **0.0% of weight below $300M on every arm**,
which is reported as a check on the construction rather than as a result.

---

## What I would and would not conclude

**Would:** the $10 billion tier remains the best pool this project has measured, and a stricter
bar at the small end does not rescue the small end. Combined with `UNIVERSE-BIAS` — where a flat
wider pool also lost once the universe was corrected — **two different ways of reaching down the
cap scale have now both failed on the honest universe.** That is a reasonably strong case for
leaving the pool where it is.

**Would not:** conclude that "stricter bars by size" cannot work. One set of band boundaries, one
set of percentiles and one junk definition were tested, each chosen before any number and none
swept. The 1999-2008 result is a real signal that the idea has *something* in it in a
small-cap-friendly decade — it is simply not demonstrable on the period that matters for a
decision today, and it is not separable from zero in either direction.

**A defect in my own register, reported rather than patched.** §3 asked for a "size-neutral
diagnostic — rank within each band". That **is** arm A, because arm A's percentile is already
taken within band, so the diagnostic is the same construction and reproduces it at exactly
`0.000e+00`. I have reported that rather than quietly substituting a different diagnostic after
seeing the arms, which would have been choosing a design on the outcome. A genuine version
(equalising the three bands' *weight*) is named and **not run**; it needs its own register.

---

## For January

If you want to come back to this, the one variant I would price as worth a trial is **arm B's
junk filter applied to the incumbent's own $10B tier** rather than used to let smaller names in —
because the filter's measured effect on 2009-2026 was positive, and that would test it without
also taking the size bet that sank both arms here. That is a new hypothesis and needs its own
register; it is not proposed as part of this item.

**For October 22: no change. The incumbent $10 billion tier.**

---

*Record: `HANDOFF_edge_audit.md` `TIERED-POOL`; `data/free_analysis/TIERED_POOL.json`,
`TIERED_POOL_KILL.json`, `TIERED_POOL_ADDENDUM.json`. Two equity trials, booked before any
runner existed. The §2c coverage kill passed at 91.6% and 91.3% against a 70% floor, so arm B ran
rather than being reported NOT-RUN.*
