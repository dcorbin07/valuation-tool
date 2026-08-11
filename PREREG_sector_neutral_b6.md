# PRE-REGISTRATION — sector-neutral ranking, re-run on the corrected (post-B6) panel

**Registered:** 2026-08-11 (session 20)
**Item:** `HANDOFF_parked_positives.md` §3 — member **B** of the parked-positives inventory.
**Ledger:** `SECTOR-NEUTRAL-B6` (new row; `S15` and `S25` are DIFFERENT items and stay open).
**Lane:** edge. **Adopts nothing by itself** — adoption is Don's call and a **vintage event**.

This file is committed **ALONE**, before any measurement code exists, and must be a strict git
**ancestor** of the commit that adds the measurement script. That is what makes the blindness
checkable rather than asserted. Nothing here may be edited after the run; corrections go in the
handoff, in the open, as they did for S22 and S23.

---

## 1 · The question, and why it is being asked again rather than left closed

`sector_neutral` scores every granular number against its **sector median** before the global
z-score, instead of against the whole market. It has been tested twice — P10 (2026-07-31) and
again on 2026-08-02 (`HANDOFF_sector_neutral.md`) — and **rejected both times**, in both held-out
split directions, under both weightings. The mechanism was understood, not mysterious: it **buys
long-short *t* and sells top-decile alpha**, and Valquo trades a long-only book.

**The reason to re-run is not doubt about that reasoning. It is that both rejections ran on a
panel the project has since declared void.** `HANDOFF_sector_neutral.md:58` records the universe
as *"2,710 usable, 136,478 panel rows, **110 rebalance dates**"*, dated **2026-08-02**. **B6 landed
2026-08-04** and cut the panel to **2,531 names / 69 dates**, because the first 41 dates had an
**inverted universe** — every name present at a 2001 cross-section was one that had already
stopped trading.

`CLAUDE.md` records B6's measured cost to the headline as **t −0.897, alpha −4.18pp,
PBO +46.7pp** — *"B6 is essentially the whole drop"*. **The sector-neutral decision turned on a
−1.58pp alpha difference, measured inside a panel whose alpha level moved −4.18pp when the defect
was removed.**

**This register does NOT assert the old verdict was wrong.** The two arms were compared against
each other on the same panel, which cancels a great deal. It asserts only that **the trade-off has
never been observed on the panel the project actually uses**, and that a decision resting on a
void panel is not closed.

**There is a specific reason to expect the answer to move, and it is stated here so it cannot be
claimed as a post-hoc insight** (see §8 for the direction it points). The corrected window
(2009-01 →) is approximately the **late** portion of the void panel. In the void panel's late
half sector-neutral was worse on **both** metrics; the single favourable cell — early-half
long-short *t* **+0.948** — sits inside the 41 dates B6 deleted.

---

## 2 · The panel: ONE build, two arms, provably identical rows

**Both arms come from a SINGLE pass of `build_fundamental_panel`.** At each rebalance date the
loop assembles one `metrics` list and calls `build_frame` **twice** on that same list — once with
`sector_neutral=False` (the shipped flat arm, which defines the rows) and once with
`sector_neutral=True` — emitting the flat theme columns plus `sn_{theme}` columns on the **same
row**.

**Why this and not two builds.** Two separate builds would differ by more than the flag:
`CLAUDE.md` records that *"a full backtest is not reproducible run to run, and the insider theme is
where it shows"* (median IC −0.0034 / +0.0155 / −0.0034 across three identical-data runs). A
per-arm build would let that nondeterminism land in the difference being measured. **One pass
makes it common-mode, so it cancels exactly** — the same argument that made S22 build one panel
for eight horizons.

`build_frame` takes `metrics: list[dict]` and immediately does `pd.DataFrame(metrics)`; it does
not mutate the caller's list, so the second call sees byte-identical inputs.

**Consequences fixed in advance:**

* The **row set is identical by construction** — same dates, same tickers, same `fwd_ret`. The
  2026-08-02 run could only assert this; here it is a property of the code, and C1 checks it.
* Median-subtraction on a group with at least one non-missing value cannot create a new missing
  value, so **the arms have the same missingness pattern**. If that is violated it is a defect and
  is reported as one, not smoothed over.
* A **singleton sector** would be mapped exactly to 0 by its own median. That is correct
  behaviour, not a bug, but the sector group-size distribution is reported (C4) so nobody has to
  guess whether it is happening.

Panel parameters are the shipped ones and are not swept: `rebalance_days = 63`, `horizon = 63`,
`lookback_years` from `CONFIG`, full universe (**no subset — methodology rule**), grid offset 0.

---

## 3 · The PRIMARY gate — the same one that rejected it, unchanged

`fundamental_panel.holdout_compare_panels(panel_flat, panel_sn, cols, base_weight=0.125)`, the
shipped function, with the margins **already committed to the repository before this register
existed**:

| constant | value | where |
|---|---|---|
| `MIN_HOLDOUT_TSTAT_GAIN` | **+0.25** long-short *t* | `fundamental_panel.py:3090` |
| `MIN_HOLDOUT_ALPHA_GAIN` | **+0.01** (+100 bps/yr top-decile alpha) | `fundamental_panel.py:3089` |

The gate splits the shared dates in half, **embargoes the boundary date**, and requires the
sector-neutral arm to beat the flat arm by **both** margins in **BOTH** halves. It returns
`adopt` only if both halves improve, `reject` if neither does, `not_replicated` otherwise.

**Two weightings, both pre-specified, no others:**

* **DEPLOYED** — the seven themes that actually trade, at 0.125 each:
  `value, quality, momentum, insider, capital_discipline, size, institutional`
  (`WEIGHTS_ESTABLISHED` with `low_risk` and `sentiment` zeroed). **This one carries the verdict**,
  because it is what ships — the same judgement the 2026-08-02 run made.
* **FLAT** — the nine themes that carry data, at 0.125 each: the seven above plus `growth` and
  `low_risk`. `sentiment` is excluded because it is empty (checked as C7). Reported as a
  robustness check on whether the answer depends on the weighting.

### 3a · The verdict rule, fixed now

| outcome | condition |
|---|---|
| **ADOPTED** | DEPLOYED gate returns `adopt` **and** FLAT gate does not return `reject` |
| **REJECTED** | DEPLOYED gate returns `reject` |
| **NOT REPLICATED** | anything else, including the two weightings disagreeing |

**Ambiguous is a NULL, never a pass** (`RUN_RULES.md` A6). A NOT REPLICATED outcome closes the
item exactly as firmly as a REJECT: it means the change cannot be shown to help on the panel the
project uses.

### 3b · What "closed permanently" means, committed before the result

Whatever this returns, **full sector-neutral ranking is closed and may not be re-run as a
re-run.** Re-opening requires one of exactly two things, both of which are different items with
their own registers:

* **new data** — a genuine point-in-time sector map (ledger `S25`), which would remove the
  look-ahead in §6; or
* **a materially different construction** — sector-relative on the **value theme alone** (ledger
  `S15`), which has never been tested at all.

"Run it again on a newer panel" is explicitly **not** a reason, and this clause exists so that a
future session cannot spend the denominator re-litigating a settled question.

---

## 4 · Secondary statistics — reported, with no verdict authority

Full-sample, both arms, on all 69 dates under the DEPLOYED weights:

top-decile alpha; long-short annualised; long-short *t* naive and **HAC at lag 1**; top-decile
alpha HAC *t*; monotonicity; both hit rates; the equal-weight benchmark.

**Calibrated bars (X7 / session 10), quoted because this is the configuration they were
calibrated in** — the full-universe decile book, 69 dates, H = 63, HAC lag 1:

| bar | floor |
|---|---|
| long-short HAC *t* | **2.2837** |
| top-decile alpha HAC *t* | **2.2913** |
| long-short naive *t* | **2.1437** |

**Stated as a limit, not buried:** those floors were calibrated by permuting the signal through
the **flat** pipeline. Applying them to the sector-neutral arm is a **mild extrapolation** — the
date count, the decile machinery and the null's shape are unchanged, but the composite is a
different transform of the same inputs. They are quoted **without caveat for the flat arm** and
**labelled an extrapolation for the sector-neutral arm** everywhere they appear. No new floor is
invented (see §5).

### 4a · The paired within-panel difference

The two arms score **the same dates**, so differencing them per date cancels the market move —
the V2G construction, using the shipped `quantile_backtest(..., return_series=True)` so the
arithmetic is the shipped arithmetic. Reported for the alpha series and the long-short series:
the mean paired difference, its **HAC *t* at lag 1**, and its standard error, full sample and
both halves.

**The bar for this statistic is 2.0 and it is UNCALIBRATED.** V2G already established that **no
calibrated floor exists for a paired within-panel difference** — X7 and session 10 calibrate
*levels*. It is labelled `uncalibrated` in the artifact and in every sentence that quotes it, and
**it cannot overturn the primary gate in either direction.** It exists because it is far better
powered than differencing two half-sample level statistics, and because reporting the resolution
of the design alongside the result is what V2G's power caveat taught.

---

## 5 · What is NOT run, and why — decided now, not after seeing the numbers

* **No placebo / null distribution for this study.** Sector-neutrality is a change to how the
  panel is *built*, so a null would have to permute **sector labels** and **rebuild the panel per
  draw** — not permute a finished panel, which is exactly the trap recorded in
  `x7-permutation-cannot-calibrate-a-score`. The primary gate is a **pre-committed margin** and
  needs no floor to be interpreted. This is a real limitation of the study and is stated as one.
* **No PBO and no Deflated Sharpe per arm**, though the 2026-08-02 run reported both. Two
  reasons, both from the project's own measurements: X7 found **PBO's noise median is 46.7%**, so
  the <50% bar sits at the noise level and the statistic is *"uninformative here in either
  direction"*; and running `cpcv_validate` per arm would put **weight selection inside the loop**,
  which X7 measured manufactures **~+1.4 of long-short *t* on 27% of pure-noise draws**. Omitting
  them is a deliberate improvement on the earlier design, not a shortcut.
* **No grid-offset sweep** (X2's seven grids). One grid, the shipped one, for both arms — the
  arms are compared to each other on identical dates, which is what the paired design needs.
* **No sweep of anything.** There is exactly one construction toggle, already implemented and
  shipped; there is no parameter to tune, and inventing one would be the param-search trap S23
  paid to avoid.
* **No S15 and no S25.** Named here so the boundary is checkable.

---

## 6 · The look-ahead caveat, restated because it cuts against a positive

Sharadar TICKERS carries **today's** sector classification, so applying it to a 2009 row assumes
the company was in the same sector then. This is **the one non-point-in-time input in an otherwise
strictly point-in-time panel.** Reclassification is rare and is not obviously return-predictive,
but the direction matters: **it is a reason to be MORE sceptical of a positive sector result, not
less.** If this run returns ADOPTED, that caveat must travel with it and `S25` becomes a
prerequisite rather than a nice-to-have. If it returns REJECTED, nothing rests on it.

---

## 7 · Controls — each is a named way for this study to fail

| # | control | what it proves | failure action |
|---|---|---|---|
| **C1** | the two arms' `(date, ticker)` key sets are **identical**, and both have 69 dates starting 2009-01-15 | the difference is the flag and nothing else | no verdict |
| **C2** | the toggle is **NOT inert**: mean absolute change per theme > 0 on shared rows, and the composite changes | this feature was **silently inert for years** (the panel hard-coded `sector: ""`, and `x − median(x)` over one group is a pure shift a z-score erases). It must be re-proved on THIS panel, not inherited | no verdict |
| **C3** | the **flat arm reproduces the published record to the digit**: alpha `0.071741423321`, LS *t* `2.8360640685320595`, LS HAC 2.6199, alpha HAC 4.3762, monotonicity `-0.8909090909090909`, EW `0.18137118752419476` | the harness is the shipped one | no verdict |
| **C4** | **sector coverage measured on the corrected panel** (rows and names with a non-blank sector), plus the per-date sector group-size distribution and the minimum group size | COVERAGE RULE — 100% was measured on the *void* panel and may not be assumed | reported; coverage below 95% is a **finding** and the verdict is withheld |
| **C5** | `insider` is **unchanged** by the toggle (it is a rescaled percentile, not a z-scored input; the 2026-08-02 run measured exactly 0.000) | the implementation has not drifted | reported as a defect |
| **C6** | arms have the **same missingness** per theme | median-subtraction created no new NaN | reported as a defect |
| **C7** | `sentiment` is empty, so excluding it from FLAT is correct | the FLAT column set is what it claims | reported |

**Every per-date draw is retained in the artifact** (`RUN_RULES.md` A9), not only the summaries.

---

## 8 · Expectations, written down BEFORE the run

`CLAUDE.md`: *"Do not reason about the direction of an effect in this project; measure it.
Writing the expectation down first is worth doing precisely because it keeps being wrong."* The
record is genuinely poor — R10, O20, the spread toll, U7, X3, and **both** of S22's headline
questions went against the stated prior. These are recorded to be **scored**, not trusted.

| # | prediction | confidence |
|---|---|---|
| 1 | **Primary verdict is REJECTED** (not ADOPTED, not NOT REPLICATED) | **80/20** |
| 2 | The full-sample long-short *t* **gain shrinks** below the void panel's +0.500, to **under +0.25** | 70/30 |
| 3 | The full-sample top-decile alpha difference is **negative** and lands between **0 and −3pp/yr** | 75/25 |
| 4 | The paired difference in §4a does **NOT** reach \|*t*\| 2.0 | 60/40 |
| 5 | Both halves agree in **sign** on the alpha difference (both negative) | 60/40 |

**Reasoning, so it can be checked rather than admired:** the corrected window is roughly the void
panel's late portion, and in that late half sector-neutral lost on both metrics (*t* −0.505,
alpha −1.26pp). The one cell that looked good lives in the deleted period. Prediction 4 is the
least confident because V2G's analogous paired design resolved about 1.87pp at \|*t*\| = 2 and the
effect being looked for is around 1pp — **the design may simply not be able to see it**, which
would itself be worth reporting.

**The outcome that would most change the project's mind, and it is reachable:** ADOPTED with the
alpha *cost* gone. That is prediction 1 and 3 both failing, and §3b's clause would then not apply
because the item would be adopted rather than closed.

---

## 9 · Adoption is a VINTAGE EVENT

Sector-neutral ranking ships in the live scoring path (`CONFIG.sector_neutral`, currently
`false`), so adopting it **closes vintage 2 and opens vintage 3**, resetting the whole accrued
paper-track clock for **zero statistical gain** (Rule 6). At 149 equity trials and a five-year
verdict horizon that is an expensive thing to spend, and **it is Don's call on this evidence, not
this session's.** This register produces a verdict about the *research question*; it does not flip
`CONFIG.sector_neutral`, and the session will not.

If ADOPTED, `shadow_vintage.py` is how the price of that adoption gets measured (V1), and the
handoff must say so.

---

## 10 · Trial cost, paid whatever the result

**One hypothesis, two pre-specified weightings, no grid: `n = 2`.**

**Equity `N` 149 → 151.** Deflated Sharpe and √(2·ln N) recomputed from the shipped
`research_log` and re-run into `BACKTEST_RESULTS.json` **from a clean tree** — the artifact goes
stale on the denominator otherwise, which sessions 13, 14, 15, 17, 18 and 19 each had to repair.
That refresh is logged as its own `ARTIFACT-N20` infra row.

The cost is charged **even if the verdict is REJECTED**, because a re-run of a rejected hypothesis
is another chance at the same hypothesis and understating `N` overstates the significance of every
DSR-gated claim in the project.

---

## 11 · Artifact and reproduction

* `data/free_analysis/SECTOR_NEUTRAL_B6.json` — every arm, every control, every per-date draw.
* `python -m scripts.sector_neutral_rerun` reproduces it.
* Write-up: `HANDOFF_edge_audit.md`, session 20. Ledger row `SECTOR-NEUTRAL-B6`.
* `tests/test_sector_neutral.py` gains tests for the paired-build path. The existing six tests
  pin the wiring and **deliberately do not pin the verdict**; that stays true.
