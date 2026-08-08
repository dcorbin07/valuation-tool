# PRE-REGISTRATION — the ML tree combiner (roadmap #16)

**Design only. Written and committed BEFORE any model was fit, any feature matrix was built, or
any accuracy number existed.** No training run has been performed. This file is the whole
deliverable; a later session executes it exactly as written or not at all.

**Why it gets its own session and its own file.** This is the highest-overfitting-risk item the
project has ever queued. A tree ensemble can manufacture an arbitrarily good in-sample fit from
seven noisy columns, and this project has already measured what happens when selection and
measurement share a panel: **X7 found that CPCV weight adoption manufactures ~+1.4 of long-short
*t* out of nothing, firing on 27% of pure-noise draws.** Every choice below exists to keep that
from happening again, and each one is stated so that a later session cannot quietly relax it.

---

## 1. The question

**Does a shallow gradient-boosted tree ensemble over the seven deployed theme z-scores beat the
flat 1/7 linear composite, out-of-sample, on the corrected 69-date panel, by the calibrated bars?**

It is worth asking now for two measured reasons, not on general enthusiasm:

- **X3 (session 6):** theme IC does not predict marginal contribution. `size` has the *worst*
  theme IC (−0.30) and carries the composite's entire statistical significance; adding it last
  moves long-short *t* from 1.02 to 2.84. A linear sum cannot express "this theme matters because
  it is orthogonal to the others"; a tree can represent interaction directly.
- **P6:** the linear composite is *scale*-sensitive — median/MAD robust z-scores left every theme
  IC essentially unchanged while halving the long-short *t*. A rank-target tree is invariant to
  monotone rescaling of any feature, so it tests the same hypothesis without that fragility.

**What a positive result would and would not mean.** It would mean the composite's *functional
form* is leaving something on the table on this panel. It would **not** mean the model should
ship: X4 already showed the margin over what a user can buy is not demonstrable since 2014, and
adoption into the live screener is a separate decision requiring its own gate. **Nothing here
authorises a product change.**

---

## 2. Features, target, horizon — named exactly, and frozen

**Features — exactly seven, no others, ever:**

```
z_value  z_quality  z_momentum  z_insider  z_capital_discipline  z_size  z_institutional
```

cross-sectionally z-scored within each rebalance date by `screener.cross_sectional.zscore`,
**identically to `cpcv_validate`'s own `std["z_" + c]` construction** so the tree and the linear
baseline consume the same numbers. Missing values are passed to the model as NaN and handled by
the learner's native missing-value support; **no imputation**, because imputing would give the
tree information the linear composite does not have and the comparison would stop being fair.

**Explicitly excluded, and each exclusion is a commitment:**

- **`low_risk`** — deployed weight is 0. Including it is a theme-membership change smuggled in as
  a feature, which section 7 forbids.
- **`sentiment`** — empty on this panel (0% coverage). The COVERAGE RULE settles it.
- **The 56 raw `z_*` signal columns.** Tempting and wrong: the question X3 raised is about
  *themes*, and eight times the feature count multiplies the overfitting risk while answering a
  different question. **If a later session wants the raw-signal version it is a NEW
  pre-registration with its own trial cost, not an amendment to this one.**
- **Anything not already in the panel** — no new data, no macro state, no regime dummies.

**Target:** the **cross-sectional rank of `fwd_ret` within each rebalance date**, mapped to
[0, 1]. Not raw `fwd_ret`. The linear composite is scored by rank IC and the book is formed by
cross-sectional decile ranking, so the tree must learn the object the product actually uses; a
raw-return target lets the model chase a handful of extreme outcomes that decile formation
discards anyway.

**Horizon:** **63 trading days**, unchanged, non-overlapping — the panel's existing convention.

**Panel:** `data/free_analysis/panel_corrected_69d.pkl`, the corrected 69-date panel,
2009-01-15 → 2026-01-28, 113,945 rows. **Unchanged.** No universe, date-grid, or cost-table
change may be bundled into this test.

---

## 3. Validation — where selection happens, and where it must not

**The panel's existing authority is CPCV, and it is reused unchanged:**
`_cpcv_paths(dates, n_groups=6, k_test=2, embargo=1)` — the timeline is cut into 6 blocks, every
combination of 2 is held out (15 paths), and training rows adjacent to any test block are purged.

**The load-bearing rule: hyperparameter selection never touches the set the verdict is read from.**

- Split the 69 dates at the midpoint into a **DECIDE** half and a **VERDICT** half, with a
  **one-rebalance-date embargo** at the boundary (consistent with `_cpcv_paths`' own embargo).
- **All eight grid points are trained and scored by CPCV *within the DECIDE half only*.** The
  winner is the grid point with the highest mean out-of-sample rank IC across that half's paths.
- That **single frozen specification** is then refit on the whole DECIDE half and **measured
  exactly once** on the VERDICT half. One number, one shot.
- **Both directions are run** — decide-early/measure-late and decide-late/measure-early — per the
  project's standing both-halves convention (`holdout_theme_validate`, session 7's LOO).

**Pre-committed observation, not a criterion:** if the two directions select *different* grid
points, that is recorded prominently. Session 7's LOO found exactly this and the instability of
the selection *was* the finding.

---

## 4. Model class and grid — enumerated, FROZEN, and priced

**Model class:** `sklearn.ensemble.HistGradientBoostingRegressor` (sklearn 1.9.0, present).
Chosen over a random forest because boosting with a depth cap is the standard instrument for
"does a small amount of non-linearity help", and over a deep net because the panel has 69 dates.

**The complete grid — eight points, and no ninth:**

| hyperparameter | values |
|---|---|
| `max_depth` | **2, 3** |
| `learning_rate` | **0.03, 0.10** |
| `max_iter` | **100, 300** |

**Held fixed at these values, not searched:** `min_samples_leaf=200`, `l2_regularization=1.0`,
`max_bins=64`, `early_stopping=False`, `random_state=0`. Every one of these is set to an
anti-overfitting value on purpose; **moving any of them later is a new trial, not a clarification.**

### The grid's price, computed before registering — this is the item's entire risk

`N` is a project quantity and the equity family currently stands at **121** (Deflated Sharpe
**0.8628**, √(2·ln 121) = 3.097). Adding a grid of *G* points makes it 121 + *G*:

| grid | equity `N` | headline Deflated Sharpe | √(2·ln N) |
|---|---|---|---|
| **8 (registered)** | **129** | **0.8556** | **3.118** |
| 16 | 137 | 0.8487 | 3.137 |
| 32 | 153 | 0.8356 | 3.172 |
| 64 | 185 | 0.8118 | 3.231 |
| 128 | 249 | 0.7716 | 3.322 |
| **230** | **351** | **0.7213 — BELOW X7's calibrated floor of 0.7216** | 3.444 |

**A 230-point grid would push the shipped headline below the noise floor X7 measured — a grid of
that size does not test the model, it destroys the incumbent's evidence as a side effect.** That
is why the grid is eight. The registered grid costs the headline **0.0072 of Deflated Sharpe**,
which is the honest price of asking the question and is paid whatever the answer.

**Trial cost: 8 rows, equity `N` 121 → 129.** Logged to `RESEARCH_LOG.md` when the test runs, not
before — an un-run test costs nothing (session 8's standing rule). Running both split directions
does **not** double the count: session 7's LOO counted 7 arms across two directions, and the same
convention applies here.

---

## 5. The comparison

Against the **shipped flat 1/7 linear composite**, under **identical construction**: same panel,
same seven themes, same z-scores, same rebalance dates, same `quantile_backtest` decile formation
at `n_q=10, horizon=63`, same cost table. The only difference between the two arms is the function
mapping seven z-scores to one score.

**Scored on the calibrated bars, never the retired conventions:**

- **long-short *t*: the HAC (Newey–West) statistic**, against the floor re-derived in session 10
  item 1. Ljung–Box rejects independence on this series (p 0.036), so the naive *t* is a
  diagnostic only. **If item 1's floor is not established, this test does not run** — that
  dependency is deliberate and is the reason the two items shared a session.
- **top-decile alpha margin: ≥ 1.95pp** (X7's calibrated margin). The retired 1.0pp convention is
  below the noise floor and must not be used.
- **PBO is NOT a criterion.** X7 measured the median PBO on a worthless signal at 46.7%; it is
  uninformative here in either direction and will be reported without being scored.

---

## 6. Kill criteria — decided now, applied mechanically

**ADOPTED** requires **all** of the following, in **both** split directions:

1. the tree's verdict-half **top-decile alpha exceeds the linear composite's by ≥ 1.95pp**; and
2. the tree's verdict-half **long-short HAC *t* exceeds the linear composite's by ≥ 0.25**
   (the project's standing `MIN_HOLDOUT` t-margin); and
3. the tree's own **long-short HAC *t* clears the item-1 calibrated floor** on its own.

**REJECTED:** the tree is worse than the linear composite on criterion 1 in **both** directions.

**NULL:** everything else. Explicitly including — because these are the outcomes most likely to
be argued about later — a positive point estimate that misses the margin; one direction positive
and the other negative; and the two directions selecting different grid points with disagreeing
signs. **Ambiguous is a NULL (RUN_RULES A6).**

**No re-runs.** If the result is NULL, the answer is NULL. Re-fitting with a different grid, a
different target, or a different split after seeing it is the failure mode this file exists to
prevent, and it would void the registration entirely.

**The expectation, written down first:** **NULL, 70/30.** The panel has 69 dates and seven
features; the honest prior is that a tree cannot find stable interaction structure in that. If it
does, the interaction X3 identified around `size` is the most likely place for it. Recorded
because this project's directional expectations have been wrong more often than right.

---

## 7. Out of scope — not deferred, forbidden within this test

- **No re-tuning of the linear baseline's weights.** It is compared at its deployed flat 1/7.
  Re-tuning it in the same breath would make the comparison uninterpretable in both directions.
- **No theme membership changes.** No adding, removing, splitting or merging themes, and
  specifically no re-introducing `low_risk`, `sentiment` or `growth` as "features".
- **No raw-signal features.** Separate pre-registration if wanted.
- **No panel, universe, horizon, date-grid or cost-table changes.**
- **No product change on any outcome.** A positive result licenses a *further*, separately-gated
  decision; it does not license shipping. `EDGE_*` flags stay as they are.
- **No partial reporting.** If the test runs, all three criteria and both directions are reported
  whatever they say.
