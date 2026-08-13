# PRE-REGISTRATION — U2 · The options surface as a STOCK signal

**Written and committed BEFORE any measurement code exists.** This file is committed ALONE — one
`.md`, zero `.py` — and is a strict git ancestor of every commit that measures anything. If a
`.py` file appears in the same commit, this register is void.

Ledger row **U2** (`VALQUO_LEDGER.md:302`), audit section **`VALQUO_EDGE_AUDIT.md:1227`**.

---

## 0 · PREMISE FINDINGS — measured BEFORE this register was written

These are facts about what data exists and what the shipped columns are. They are not results,
they cost no trials, and each one changed the design. They are recorded here so that the design
below reads as a consequence of them rather than as a choice made after seeing an outcome.

### 0.1 · The ledger row is `src=human` and it is CORRECT

Six `src=auto` rows in this lane's recent series claimed no audit section existed and **all six
were wrong**. U2's row is `src=human`, cites `VALQUO_ACTION_PLAN.md`, and the audit does carry a
full section at `:1227` with named features, named literature and a pre-registered threshold. The
row is accurate. This is the second consecutive human-written row in this lane that needed no
correction.

### 0.2 · `skew_25d` **IS** the "call-minus-put implied-vol spread". They are ONE column and its negation

The audit's U2 §Method names four features and the first two are *"`skew_25d` (already shipped)"*
and *"the ATM call-minus-put implied-vol spread"*. Measured on 217,706 non-null rows of the
derived layer across 120 names:

```
max | (iv_put_25d - iv_call_25d) - skew_25d |  =  0.000e+00
Pearson( skew_25d , iv_put_25d - iv_call_25d ) = +1.000000
Spearman( skew_25d , iv_call_25d - iv_put_25d ) = -1.0000
```

`skew_25d` is **exactly** `iv_put_25d − iv_call_25d`. The call-minus-put spread at 25 delta is
therefore **exactly `−skew_25d`**. A rank IC of one is the exact negative of the other, so they
cannot carry independent information and **testing both would be testing one hypothesis twice
while charging two trials.**

This is the `illiq`/`spread_pct` defect class the O3/O4/O5 lane found in a prior lane's
`panel.pkl` — the same column under two names — **caught here before the register rather than
after the verdict.** They are ONE arm.

The audit's phrasing says **ATM**, and the ATM matched-strike version is a genuinely different
object. It is not on this layer. See §0.5.

### 0.3 · The shipped `term_slope_60_30` is **NOT** the O16-validated construction

The task names *"the O16-validated construction"*. O16 validated the **book's** `term_slope`,
which `options_signals_v2.py:182` defines as **`atm_mid` (~60-DTE ATM IV) − `atm_front`
(front-expiry ATM IV)**. The derived layer ships a column called `term_slope_60_30`, and measured
over 191,276 rows it is **exactly** `atm_iv_60 − atm_iv_30` (max |Δ| 0.000e+00) — the 30-day
tenor, **not the front expiry**.

The two are different objects: **Spearman +0.5744**, Pearson +0.7732.

**This is a near-miss and it is pinned in §5 as a control.** A lookup by column name would have
found `term_slope_60_30`, computed cleanly, raised no error, and **reported a U2 verdict on a
construction O16 never validated** — while O16's entire finding was about separating `term_slope`
from a front-end IV level. The arm below uses **`atm_iv_60 − atm_iv_front`**, the closest
reproduction of the O16 construction available on this layer, and the shipped `term_slope_60_30`
is deliberately **not** substituted for it.

### 0.4 · Coverage — the binding constraint, and it forbids a both-halves gate on the full panel

The derived layer spans **2016-01-04 → 2025-12-31**; the corrected panel spans **2009-01-15 →
2026-01-28**, 69 rebalance dates. Measured (latest derived row ≤ rebalance date, staleness ≤ 7
calendar days):

| | |
|---|---|
| panel dates with ZERO coverage | **29 of 69** — dates 0–27 (2009-01-15 … 2015-10-19) **and the final date 2026-01-28** |
| panel dates with ≥20 covered names | **40** (2016-01-20 … 2025-10-27) |
| mean covered names per covered date | **436.9** |
| covered rows as a fraction of the panel cross-section | **0.244 – 0.283** |
| names with a derived directory that appear in the panel | **486 of 2,531 (19.2%)** |

Two consequences, both fixed here before any number exists:

1. **Every covered date is in the LATE portion of the panel.** A both-halves gate on the *full*
   panel is therefore not underpowered, it is **impossible** — the early half contains no
   observations at all. This is **S18's situation exactly**, and the replacement is the same one:
   **every half-split in this register is a split of the COVERED SUBSAMPLE (40 dates → 20 early /
   19 late after embargoing the boundary), never of the full panel.** Both halves clear the
   shipped `min_dates=16`. **A pass on 20-date halves is not the same object as a pass on 34-date
   halves, and may not be quoted as one.**
2. **The final panel date (2026-01-28) is uncovered** because the derived layer ends 2025-12-31.
   It is dropped, and it is dropped for a data-availability reason that is independent of any
   outcome.

Coverage is ~25% of the panel cross-section, better than the audit's predicted 4–14%. Per the
audit's own guidance this is tested **within the covered subset as a self-contained
cross-sectional study**, which it calls *"a legitimate finding and the right first step"*.

### 0.5 · What is NOT tested, named so it is not mistaken for tested

The task says **"no new features beyond the named list"**. Two of the audit's four named features
require building something that does not exist on this layer, and both are declined:

- **The put–call parity deviation on matched strikes** — Cremers–Weinbaum's *actual* measure, and
  the single largest published effect the audit cites (51 bps/week). It needs matched call/put
  pairs at the same strike and expiry, which lives in the raw chain pickles, not the derived
  daily layer. Building it is a new feature. **NOT TESTED.**
- **The 21-day change in each feature.** A change is a different hypothesis from a level —
  momentum *in the surface* rather than the surface itself — and it would double the arm count.
  **NOT TESTED.**

**CONSEQUENCE, fixed here rather than argued afterwards: the U2 ledger row closes as `PARTIAL`,
not `DONE`, whatever this register returns.** The level half is tested; the parity-deviation and
change halves are not, and marking the row `DONE` would tell the next session they had been.
This is the **S10 precedent** (its valuation-band arm ran, its accounting-red-flag half did not,
and the row is `PARTIAL`).

### 0.6 · The three surviving candidates are not one effect three times

Pooled Spearman between them: `term_slope_O16` vs `iv_rank` **−0.3305**, vs `skew_25d`
**−0.2145**; `iv_rank` vs `skew_25d` **+0.2232**. Modest, so they are genuinely three arms.
Pooled non-null availability: `term_slope_O16` **0.7640**, `iv_rank` **0.8827**, `skew_25d`
**0.8078**.

---

## 1 · DISCLOSED PRIOR KNOWLEDGE, AND A SCOPE DIVERGENCE NAMED BEFORE ANY RESULT

**What I already know, which this register cannot un-know:**

- Every input to this item has already been tested **as an options signal** and none survived:
  `term_slope` **IS DISTINCT** but on the options book (O16); the surface anomalies `idio_vol`,
  `exp_idio_skew`, `vol_of_vol` are **NULL** (O3/O4/O5); tick flow is **NULL** (O14). U2 asks a
  **different question** — do these predict the *underlying's* return — and that question has
  never been asked here.
- **U1, the reverse direction, was REJECTED** (2026-08-11). U7, the veto direction, was
  **REJECTED**. U2 is the last live direction of the unification.
- The project's standing record is **0 discoveries in 131 options hypotheses** and an equity side
  that has adopted nothing in eleven sessions. §6 states expectations against that prior.
- `iv_rank` is recorded in `antisignal.py:33` as **0.0% populated on the options book**. That is a
  fact about the *book*, not about the derived layer, where it is 88.3% populated. The arm below
  reads the derived layer.

**THE SCOPE DIVERGENCE (S12's class, named before any result).** The task names the feature list
as *"term_slope, IV rank, the O16-validated construction"*. The audit's own U2 §Method names a
different list: *"`skew_25d`, the ATM call-minus-put implied-vol spread, the put–call parity
deviation on matched strikes, and the change in each over 21 days"*. These are not the same list.

Handled as S12 was — **both readings are tested as separate arms so the row closes on both and
neither is reported as the other**, subject to §0.2 (two of the audit's features are one column)
and §0.5 (two require new features and are declined). The union that survives is three level
features plus their composite.

---

## 2 · DEFINITIONS — fixed here, not at runtime

### 2.1 · The features

All read from `data/options_derived/<TKR>/<TKR>-daily.pkl`.

| arm | column expression | source of the name |
|---|---|---|
| **A1 `term_slope`** | `atm_iv_60 − atm_iv_front` | task ("the O16-validated construction"), §0.3 |
| **A2 `iv_rank`** | `iv_rank` as shipped | task |
| **A3 `skew_25d`** | `skew_25d` as shipped | audit U2; subsumes its "call-minus-put spread" exactly (§0.2) |
| **A4 `surface`** | equal-weighted mean of the available A1–A3 z-scores | the "occupies the `sentiment` slot" claim |

No other column is read. No feature is constructed from the raw chains.

### 2.2 · The join — STRICTLY BEFORE, deliberately stricter than necessary

For each (rebalance date `D`, ticker `T`), take the **last derived row with date STRICTLY < `D`**,
and require its age ≤ **7 calendar days**; otherwise the cell is missing.

`fwd_ret` runs from `D`'s close (`_forward_return`: `closes[i+h]/closes[i] − 1`), so a same-day
EOD surface would be contemporaneous rather than look-ahead. **Strictly-before is used anyway**,
because it costs one day of staleness on a quarterly signal and removes the argument entirely.
C3 measures zero violations.

### 2.3 · Standardisation and the incumbent set

Each feature is z-scored **within each rebalance date over the covered names only**, using the
shipped `cross_sectional.zscore` (which winsorises at 2% first — S21's finding).

The **seven incumbent themes** are `value`, `quality`, `momentum`, `insider`,
`capital_discipline`, `size`, `institutional` — the seven that carry weight. `low_risk` (zeroed),
`growth` and `sentiment` (empty) are **not** in the incumbent set; `low_risk`'s correlation with
each arm is reported as a diagnostic in §5 C6, because a volatility-surface feature is a
candidate volatility proxy and that is the most likely way one of these arms is not new.

### 2.4 · The verdict statistic — incremental IC, the PEAD template

Per rebalance date, on the covered rows only:

1. Cross-sectional OLS of the candidate z-score on the seven incumbent theme columns **with an
   intercept**. Rows missing any input are dropped for that date; ≥ 20 names required.
2. Keep the **residual** — the part of the surface feature the composite already in the panel
   cannot explain.
3. Spearman IC of that residual against `fwd_ret`, giving one IC per date.
4. `ic_tstat = mean / (sd / √n)` on that IC series — **the shipped `theme_ic` arithmetic**, so the
   number compared against a calibrated bar is the same statistic the bar was calibrated on.

Also reported per arm, as diagnostics carrying no verdict: the **raw** (non-residualised) IC and
its `ic_tstat`; the mean per-date **R²** of the candidate on the incumbents; and coverage.

This is the PEAD template verbatim — PEAD's `pead_car` cleared a standalone bar at t +2.215 and
its incremental IC t was **+0.020**, i.e. 89% orthogonal and the orthogonal part predicted
nothing. **The whole point is that a raw IC does not settle this and the residual does.**

---

## 3 · BARS — and the exact extent to which they are calibrated here

| bar | value | status **on this subsample** |
|---|---|---|
| theme IC *t* | **2.71** | X7's calibrated p95 — **an EXTRAPOLATION here** |
| long-short HAC *t* | **2.2837** | session 10's calibrated p95 — **an EXTRAPOLATION here** |
| held-out gate margins | **+0.25** *t* AND **+100 bps** alpha, both halves | shipped `MIN_HOLDOUT_*`, unchanged |

**BOTH CALIBRATED BARS ARE EXTRAPOLATIONS AND MUST BE LABELLED SO EVERY TIME THEY ARE QUOTED.**
X7 and session 10 calibrated them on the **full 69-date, 2,531-name panel at h63, lag 1**. This
register runs on a **40-date, ~437-name covered subsample**. `n`, the cross-section width and the
IC series length all differ. Session 12 established that a calibrated floor is a function of the
run's own `N`, and `SECTOR-NEUTRAL-B6` labelled exactly this kind of transfer an extrapolation.
**Re-calibrating on the subsample is not attempted** — that is its own placebo sweep, and doing it
after seeing the arms is the error this project already paid for twice.

`ic_tstat` is the statistic compared to 2.71. **`ic_inference.t` may NEVER be compared to 2.71**
(audit M2's explicit prohibition — it is a new statistic with no calibrated floor).

**THE AUDIT'S OWN POWER CONTROL IS MANDATORY AND IS A GATE ON INTERPRETATION, NOT A NICETY.**
The audit requires *"the subset's own power control … verify that a known-real signal such as
`ret_6_1` or `gp_on_capital` clears 2.0 on the same restricted subset, so a null is interpretable
as a null rather than as low power."* Both are run (`z_gp_on_capital`, `z_ret_6_1`), raw and
residualised, on the identical covered rows.

**If NEITHER power control clears 2.0 on the covered subsample, every null in this register is
reported as UNINTERPRETABLE — "not measurable here" — and NOT as a negative result.** That
sentence is fixed now, before the controls have been run.

---

## 4 · VERDICT RULES

### 4.1 · Sign, declared per arm before running

- **A3 `skew_25d` has a DECLARED sign: NEGATIVE.** Xing–Zhang–Zhao (2010): steepest-smirk stocks
  **underperform** flattest-smirk by ~10.9%/yr, persisting six months. `skew_25d` is
  put-minus-call IV, i.e. the smirk, so **high `skew_25d` ⇒ LOW forward return ⇒ negative IC**.
  Cremers–Weinbaum agrees in direction (expensive calls outperform), which is expected since
  §0.2 shows it is the same column negated. A **positive** incremental IC on A3, however large,
  is **NOT a pass** — it contradicts the declared sign and is reported as a contradiction.
- **A1 and A2 are TWO-SIDED.** The audit cites no cross-sectional stock-return sign for a term
  slope or an IV rank, and O16 is a statement about the options book, not about stock returns.
  Declaring a sign now would be inventing one. Two-sided costs power and that is the honest
  price — **O14's precedent, and the same substitute is used: a sign-agreement clause between
  halves does the work a declared sign would.**
- **A4's components are oriented on the DECIDE half and the composite is measured on the OTHER
  half**, in both directions. No sign is declared for the composite; the orientation is learned
  where the measurement is not taken. This is the S14/LOO decide-then-measure discipline.

### 4.2 · The rule

An arm is **ADOPT-ELIGIBLE** only if **all** of:

1. Incremental-IC `ic_tstat` **≥ 2.71 in absolute value in BOTH halves** of the covered
   subsample, boundary embargoed.
2. **Signs agree between the halves** (and, for A3, both equal the declared negative sign).
3. At least one power control clears 2.0 on the same rows (§3).

Anything else is a **NULL**. Specifically:

- Clears one half only → **NOT_REPLICATED**, and must be quoted with **"1 of 4 sibling arms"**.
  Four arms against one bar make at-least-one-clears a material event under independence; the
  last four sessions each produced exactly one arm clearing exactly one half.
- Clears neither → **REJECTED**.
- **Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6). A miss by any
  margin is a miss and will not be rounded into a pass.

**Nothing here is ADOPTED by this register.** An eligible arm is recorded **ELIGIBLE** and routed
to Don, because occupying the `sentiment` slot changes the live scoring path and is therefore a
**VINTAGE EVENT** — it would close the open vintage and reset the five-year clock (Rule 6). The
vintage number is **derived at write time, never quoted from this file.**

### 4.3 · The book arm (A4 only)

If and only if A4 is eligible on §4.2, it is additionally run through the shipped
`holdout_compare_panels` on the covered subsample: incumbent seven themes vs the same seven plus
`surface` as an eighth, flat weights, the shipped margins, both directions. The long-short HAC
floor **2.2837** is quoted against the eight-theme book **labelled an extrapolation**.

**C7 (§5) is required for this arm and is not optional:** adding an eighth input moves every
theme's relative weight 1/7 → 1/8, so the arm is a **compound** change. S7/S18 measured that
dilution at +0.000173 of alpha on the full panel — **essentially nil, but measured on a different
row set**, so it is re-measured here with a constant eighth column rather than assumed to carry
over.

---

## 5 · CONTROLS — every one fixed now, and C1/C2 are GATES

- **C1 — HARNESS REPRODUCTION (gate).** On the FULL 69-date panel the seven-theme flat-weight
  `quantile_backtest` must reproduce the record to 1e-9: `top_decile_alpha` 0.07174142332098163,
  `long_short_tstat` 2.8360640685320595, NW 2.6199121240414884, monotonicity −0.8909090909090909.
  **If it does not, the run ABORTS before any arm is read.**
- **C2 — POWER (gate on interpretation, §3).** `z_gp_on_capital` and `z_ret_6_1` on the covered
  rows, raw and residualised.
- **C3 — POINT-IN-TIME.** Count of joined cells whose derived date is ≥ the rebalance date.
  **Must be exactly 0.**
- **C4 — THE O16 CONSTRUCTION IS THE ONE USED.** Assert the A1 column is built from
  `atm_iv_60 − atm_iv_front` and that the shipped `term_slope_60_30` appears nowhere in the arm
  path; report the Spearman between them on the joined rows (expected ≈ +0.57 from §0.3). This
  pins §0.3's near-miss so it cannot silently reappear.
- **C5 — NO DUPLICATE ARM.** Assert `corr(skew_25d, iv_call_25d − iv_put_25d) = −1` on the joined
  rows, i.e. that §0.2 still holds, and that no arm is the negation of another.
- **C6 — IS THIS A VOLATILITY THEME IN A NEW COSTUME?** Per-date Spearman of each arm against the
  panel's `low_risk` theme and against `z_neg_log_mktcap`. Reported as a diagnostic with **no
  verdict** — but a |correlation| above 0.8 against either would mean the arm is substantially an
  incumbent exposure, and that must travel with any positive result.
- **C7 — THE EIGHTH-INPUT DILUTION (A4 only).** Re-score with a **constant** eighth column to
  isolate the 1/7 → 1/8 reweighting from the surface information.
- **C8 — COVERAGE IS NOT FIDELITY.** Coverage per arm per half, reported before any IC. A signal
  present is not a signal correct.

---

## 6 · EXPECTATIONS — written before any arm has been run, scored afterwards whatever they say

Stated because this project's directional calls have been wrong more often than right, and
writing them down first is the only thing that keeps that visible.

| # | expectation | confidence |
|---|---|---|
| 1 | At least one power control clears 2.0 on the covered subsample | 60/40 |
| 2 | **A3 `skew_25d` FAILS** — no incremental IC clearing 2.71 in both halves | 75/25 |
| 3 | **A1 `term_slope` FAILS** | 85/15 |
| 4 | **A2 `iv_rank` FAILS** | 85/15 |
| 5 | **A4 composite FAILS** | 85/15 |
| 6 | The residual IC is SMALLER in magnitude than the raw IC for every arm | 65/35 |
| 7 | At least one arm is NOT_REPLICATED (clears exactly one half) | 60/40 |
| 8 | The largest \|C6 correlation\| is against `low_risk`, not against size | 60/40 |
| 9 | A3's raw IC carries the DECLARED negative sign on the full covered sample | 55/45 |

Expectation 9 is deliberately near a coin flip: XZZ's effect is published, megacaps are the most
efficiently priced names in the market, and McLean–Pontiff's 58% post-publication decay applies.

---

## 7 · TRIAL COST — pre-committed

**Four arms, four equity trials: A1, A2, A3, A4.** Equity `N` **185 → 189**.

Charged to **equity**, not options, because the claim is about **stock** forward returns — the
task's own framing, *"a stock-signal claim pays stock-signal rent"*. Options `N` is untouched at
285. Controls, the power check and the coverage measurement charge **zero**: they search nothing.

`N` must be **re-read from `research_log.detail()` after merging `main`** and never quoted from
this file — four consecutive sessions in this lane found the equity count had moved under them
between the register and the push.

---

## 8 · VOID CONDITIONS — this register returns NO VERDICT if any of these fire

1. Any `.py` file is committed alongside this `.md`.
2. C1 fails to reproduce the record to 1e-9.
3. C3 finds any point-in-time violation.
4. C5 finds that an arm is the negation of another arm.
5. A feature outside the §2.1 table is read, or any feature is built from the raw chains.
6. A bar is re-calibrated, moved, or re-derived on the covered subsample after any arm has been
   read.
7. Any half-split is taken on the full panel rather than on the covered subsample (§0.4).
8. The U2 ledger row is closed as `DONE` rather than `PARTIAL` (§0.5).
9. `ic_inference.t` is compared against the 2.71 bar anywhere.
