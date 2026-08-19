# PRE-REGISTRATION — S11 + S12: horizon ensemble, and ranking within bucket

**One register, both items, committed before any arm has been scored.**

---

## 0. THE PRIORS, PER ITEM, STATED FIRST

### S11 — the one item in this cluster with a measured mechanism

**FOR.** `S22` measured the composite's out-of-sample rank IC **rising** with horizon:
**+0.034 at one quarter → ~+0.072 at three-plus quarters**, and annualized top-decile alpha
essentially flat from three months to two years (+6.59% → +5.10%) with the alpha HAC *t* never
below 3.16. **So a longer-horizon component has measured signal to contribute** — this is not the
usual "try a construction and see".

**AGAINST, and it is the sharper argument.** **The deployed book already re-ranks quarterly**, so
a 252-day-weighted component may be **the same information twice**, not new information. S22 said
this itself in its own terms: `cum_alpha(H)` is the buy-and-hold return of a cohort selected on
**one** date, whereas a quarterly book **re-selects and compounds fresh selections** — *"those are
different claims and only the first is measured."* An ensemble that blends a slow ranking into a
fast book is betting the two are different objects; S22's caveat is that they may not be.

**A second caution the mechanism does not survive intact.** S22's persistence lives **entirely in
the long leg** — the long-short spread's HAC *t* **collapses 2.7167 → 0.6846** with horizon. So
whatever a 252-day component contributes, it is not long-short signal, and the arm's long-short
margin should be expected to move against it.

**Lean: REJECT, 65/35** — lower confidence than the weighting family precisely because the
mechanism is measured.

### S12 — motivated by a real result, and with a measured reason to expect harm

**FOR.** `regime_split` finds the edge strongest in **large caps**, and the audit's own argument is
that a single `value` column mixes two different factor definitions — established names scored on
`earnings_yield`/`fcf_yield`/`ebit_ev`/`book_to_price`, speculative on `neg_ev_sales`/`neg_ps` —
and then z-scores them against each other as if they were the same quantity.

**AGAINST, and this is measured rather than argued.** **X3 found that `size` has the WORST theme
IC (−0.30) and carries the composite's ENTIRE statistical significance**: adding it last takes
top-decile alpha +4.10% → +7.17% and long-short *t* **1.02 → 2.84**. **Ranking within cap tier
NEUTRALISES exactly that exposure.** So the cap-tier arm is, mechanically, a proposal to remove
the one theme the composite's significance rests on.

**And the sector-neutral precedent is directly on point.** Sector-neutral ranking was rejected
**three times**, most recently on the corrected panel, where it was worse on **both** metrics. The
audit anticipates this — *"run it expecting the same shape of result, and use the same metric
priority: top-decile alpha decides, not the t-statistic"* — and **that metric priority is adopted
here verbatim.**

**Lean: REJECT both S12 arms, 80/20 for the cap tier and 70/30 for the valuation bucket.** The
valuation bucket gets the lower confidence because it is the audit's actual argument and the
buckets really do carry different factor definitions.

---

## 1. PREMISE CHECK

**(a) A SCOPE DIVERGENCE, NAMED BEFORE ANY RESULT — the same class as S10's.** The task frames S12
as *"rank names inside their cap tier"*, motivated by the regime split. **The audit's S12 is not
that.** `VALQUO_EDGE_AUDIT.md:772` specifies the **VALUATION bucket** — established vs speculative,
*"the buckets are defined by how a name is valued, not by industry"*. **Both are tested here**, as
separate arms, so the ledger row can close on the audit's own definition **and** on the task's, and
neither is reported as the other.

**(b) S11 NEEDS NO REBUILD.** `panel_s22_h504.pkl` already carries **every theme plus
`fwd_ret_h252`**, and its `(date, ticker)` key set is **identical** to the corrected panel's
(113,945 both, verified). So the 63/252 blend is computable on banked data.

**(c) S12 DOES NEED A REBUILD, and the audit says where.** Its method is *"add a `bucket_relative`
toggle to the standardisation step"* — the step that operates on the **granular** metrics, exactly
where `sector_neutral` already subtracts a group median before z-scoring. The banked panels carry
**themes**, not granular metrics, so a theme-level approximation would be a **different, coarser
intervention**. It is rebuilt at the granular level instead, mirroring the proven plumbing.

**(d) THE BUCKET COLUMN IS REAL AND NOT DEGENERATE:** `established` 90,533 rows, `speculative`
23,412 — a 79/21 split, so both sides are substantial.

---

## 2. THE ARMS

* **A1 — S11 HORIZON ENSEMBLE.** Composite ranks are computed at two horizons and averaged.
  Weights at each horizon are **IC-proportional** (non-negative, normalised) from that horizon's
  own theme ICs — **fitted on the DECIDE half only and applied to the MEASURE half**, in both
  directions, so no weight is ever fitted on the data it is scored against. The blend is the
  **mean of within-date percentile ranks** of the two composites, backtested at the **63-day**
  rebalance against `fwd_ret`. **Turnover is reported for the blend and the incumbent**, because
  the audit's stated secondary claim is that a slower component should reduce it.
* **A2 — S12a VALUATION-BUCKET-RELATIVE** (the audit's own definition). Each granular metric has
  its within-`(date, bucket)` median subtracted before the global z-score, exactly as
  `sector_neutral` does with sector.
* **A3 — S12b CAP-TIER-RELATIVE** (the task's framing). The same operation grouped on a
  **market-cap tercile computed within each date** — pre-committed as terciles, not quintiles, so
  the smallest group stays large.

Every arm is a column set on **one panel build**, so arms differ in the construction and nothing
else.

---

## 3. THE GATE

The shipped margins: **≥ +100 bps top-decile alpha AND ≥ +0.25 long-short *t*, in BOTH halves,
boundary embargoed**. **ADOPT-ELIGIBLE** iff both clear in both halves; otherwise **REJECTED**;
ambiguous is a **NULL**.

**THE AUDIT'S METRIC PRIORITY IS ADOPTED VERBATIM FOR S12: *"top-decile alpha decides, not the
t-statistic."*** So if an S12 arm buys long-short *t* and sells top-decile alpha — the exact shape
sector-neutral produced three times — **it is REJECTED regardless of the *t***, and that is fixed
here before the numbers exist.

**BOOK-LEVEL VERDICTS ONLY.** No arm may be promoted on a per-signal or per-theme IC — now
demonstrated eight times.

**FAMILY-WISE:** three arms against one bar. A single clearing arm is recorded
**`ELIGIBLE — UNREPLICATED, 1 OF 3 SIBLING ARMS`**, never adopted; at-least-one-clears is roughly
a **14%** event under independence. **This clause has fired in each of the last three sessions**,
which is why it is written before the results rather than after.

---

## 4. WHAT ADOPTION WOULD COST

Any arm is a **VINTAGE EVENT** — it changes the composite users receive, closing the current
vintage and opening the next, resetting the five-year forward clock for zero statistical gain
(Rule 6). The current vintage is **DERIVED, never assumed** (`PT-GAPDUE`) at run time and recorded
in the write-up. **No arm is adopted by this register**; an eligible arm is recorded ELIGIBLE with
the §3 label, and the decision is Don's.

---

## 5. CONTROLS — read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record** (alpha 0.07174142332098163, LS *t*
  2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909). **ABORTS**
  otherwise.
* **C2 — identical rows** across arms, asserted.
* **C3 — no arm is inert:** within-date rank correlation against the deployed composite. S16's
  rank-identity result is why this control exists.
* **C4 — COVERAGE FIRST**, per arm, before any verdict.
* **C5 — S11's WEIGHTS ARE NEVER FITTED ON THE DATA THEY ARE SCORED AGAINST.** The decide-half
  weight vectors are reported for both horizons and both directions, so the separation is
  checkable rather than asserted. **A violation here would manufacture the result.**
* **C6 — THE TWO HORIZONS ARE ACTUALLY DIFFERENT.** The correlation between the h63 and h252
  weight vectors is reported. **If they are near-identical the "ensemble" is one composite twice**
  — §0's counter-prior made measurable — and the arm's verdict means nothing.
* **C7 — S12's GROUPS ARE NOT DEGENERATE:** the per-date group sizes are reported for both the
  valuation bucket and the cap tier. A group that is nearly the whole cross-section makes its
  arm a no-op.
* **C8 — THE SIZE EXPOSURE IS MEASURED, NOT ASSUMED.** For the cap-tier arm, the book's mean
  `size` z-score before and after is reported — the direct test of §0's claim that the arm
  neutralises the theme X3 says carries the composite's significance.

**TOP-25 BEFORE/AFTER BY NAME** is reported for every arm on the last scored date, as the task
requires.

---

## 6. EXPECTATIONS

1. **A1 fails — 65/35** (§0's counter-prior).
2. **A1's long-short margin moves AGAINST it — 70/30**, because S22 measured that the persistence
   lives entirely in the long leg while the spread's *t* collapses with horizon.
3. **A1 reduces turnover — 70/30.** The audit's stated secondary claim, and mechanically likely
   since a slower component reorders less.
4. **C6 shows the two horizons' weight vectors correlate above 0.8 — 60/40.** If so, the ensemble
   is largely one composite twice and §0's counter-prior is confirmed directly.
5. **A2 (valuation bucket) fails — 70/30.**
6. **A3 (cap tier) fails — 80/20**, and **more decisively than A2**, because it neutralises `size`.
7. **C8 shows the cap-tier arm materially shrinks the book's `size` exposure — 85/15.** This is
   close to mechanical; it is measured to confirm the mechanism rather than to test it.

---

## 7. TRIAL COST

**Three arms: equity `N` 180 → 183.** Charged whatever the verdicts are. The premise checks, the
controls and the top-25 tables charge nothing.

`BACKTEST_RESULTS.json` is re-run **from a clean tree**.

---

## 8. WHAT THIS REGISTER DOES NOT DO

* It does **not** sweep horizons. **Exactly two** are blended — 63 and 252, the audit's own pair —
  and no other combination is tested or mentioned.
* It does **not** re-open sector-neutral, which is closed permanently and may only return via
  `S25` (now closed as unobtainable) or `S15`.
* It does **not** change the rebalance frequency. S22 explicitly warned that its horizon result is
  **not** a finding that the book should rebalance less often.
* It does **not** adopt anything.
