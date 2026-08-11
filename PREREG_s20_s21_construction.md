# PREREG — S20 (rank composite, not z-sum) and S21 (winsorise before standardising)

**Committed BEFORE any measurement code exists and BEFORE any number is produced.** This file is
pushed **alone**, so its commit is a strict git ancestor of whatever commit carries the
measurement script. Nothing in the study may restate a threshold from a result.

Ledger items **S20** and **S21**, both `OPEN`, both `src=auto` — mechanically proposed from the
external audit and, per their own ledger notes, with *"no mention anywhere in the corpus"*. Neither
has ever been run.

---

## 1. WHY THESE TWO TOGETHER, AND WHY NOW

They are the same decision seen twice: **how a cross-section is turned into a number before the
weighted sum happens.** P6 already measured one point in that space and the result is the reason
this pair is worth a register at all.

P6.3 replaced the classic z-score with a median/MAD robust z-score and the composite **fell apart** —
long-short *t* **3.485 → 1.721**, top-decile alpha **+11.77% → +8.99%**, monotonicity −0.939 →
−0.624 — while **every per-signal IC stayed flat** (quality +3.39 → +3.35, value +1.34 → +1.68).
`cross_sectional.py:16-42` records the mechanism: MAD < SD on fat-tailed data, so dividing by the
smaller scale **inflates** the tails, and the top decile then gets picked by whoever has one
extreme factor reading rather than broad strength across themes.

So the project already knows that (a) this layer is load-bearing, and (b) **per-signal IC cannot
see it.** S20 and S21 are the two untested moves in the same layer, and they push in *opposite*
directions on the one axis P6 identified — rank compresses tails maximally, removing
winsorisation lets them back in.

**THE STANDING RULE IS THE SPEC, AND IT IS RESTATED HERE AS A BINDING CONSTRAINT ON THIS STUDY:
never judge a construction change by per-signal IC.** Rank-IC is invariant to a monotone rescaling;
the composite is a weighted SUM and is very much scale-sensitive. **The verdict is carried by the
book — the decile structure and the top-decile alpha — and per-signal and per-theme ICs are
reported as DIAGNOSTICS that may not move a verdict in either direction.**

## 2. S21 IS ALREADY IMPLEMENTED — the premise is corrected HERE, in the register, before the run

Recorded in the V2F/V2G tradition of correcting a brief's premise in the register rather than
discovering it in the results.

**`cross_sectional.zscore` already winsorises before standardising.** `cross_sectional.py:83-87`:

```python
s = winsorize(s, p)                 # p = 0.02 by default
mu, sd = s.mean(), s.std(ddof=0)
...
return (s - mu) / sd
```

and `winsorize` clips to the 2nd/98th percentiles. This runs at **both** standardisation layers
(§3). The audit item proposes the shipped behaviour, which is what `src=auto` — *"mechanically
proposed and not yet read by a person; treat as a lead, not a fact"* — is there to warn about.

**Consequence for the design, fixed now: S21's testable form is INVERTED.** The informative
question is not *"should we winsorise?"* (we do) but **"does the winsorisation that already ships
earn its keep?"** The challenger arm is therefore **winsorisation OFF**, and the verdict must be
read in that direction:

* the gate returning **reject** means removing winsorisation does not clear the bar, i.e. **the
  shipped clipping is not shown to be costing anything** — S21 closes as *already implemented*;
* the gate returning **adopt** would mean **removing** the shipped winsorisation is an improvement,
  which is a live product change and a vintage event like any other.

Only one alternative is run. **No grid over `p` is swept** (§8).

## 3. THE TWO STANDARDISATION LAYERS, AND WHICH ONE EACH ARM CHANGES

Read this before interpreting any number. The pipeline standardises **twice**:

| layer | where | what it does |
|---|---|---|
| **L1 — per number** | `factors.build_frame:204-208`, `df["z_"+col] = zscore(...)` | each granular metric → `z_<num>`; a theme is then the **mean of its `z_*` inputs** |
| **L3 — per theme** | `fundamental_panel.composite_from_frame:1675`, `zscore(sub[c])` | each **theme column** is standardised again, then weight-summed and renormalised by present-weight mass |

**Both arms change BOTH layers.** A full-stack change is the honest object: an arm that swapped
only L3 would be testing "standardisation of the theme columns", which is not what either ledger
item says, and an arm that swapped only L1 would leave the actual weighted sum on the incumbent
scale. Both layers use the same `zscore`, so one substitution covers both.

**Two exceptions, stated in advance because they are asymmetries, not defects:**

* **`insider` is not z-scored at L1** — `factors.py:271` is `(insider_score − 50) / 25`, a fixed
  affine map. It is unaffected by the L1 swap and standardised normally at L3.
* **`size` is a single column** (`z_neg_log_mktcap`), so its theme value *is* an L1 output, where
  every other theme is a mean of several. X3 found `size` carries the composite's entire
  statistical significance despite the worst theme IC, so it is the theme most exposed to this
  change. This is a prediction about **where** any effect shows up, not about its sign.

### The arms, defined exactly

| arm | L1 and L3 standardiser | note |
|---|---|---|
| **INCUMBENT** | `zscore(s, p=0.02)` — winsorise at 2%, then `(x − μ) / σ` | the shipped construction |
| **A20 — RANK** | `(s.rank(pct=True) − 0.5) * 2.0` | **the repo's own existing rank convention**, `cross_sectional.standardize_factors(method="rank")`, which is implemented and which `build_frame` has never called |
| **A21 — NOWINSOR** | `zscore(s, p=0.0)` | `winsorize(s, 0)` clips to `[min, max]`, i.e. an exact no-op; **no code change to `winsorize`** |

NaN handling is identical in all three: pandas `rank` propagates NaN, so a missing input stays
missing and is renormalised away by `composite` exactly as now.

**A20 SUBSUMES A21 BY CONSTRUCTION, and this is checkable rather than asserted.** A rank transform
is invariant to any monotone transform of its input, and winsorisation is monotone — so the RANK
arm computed at `p=0.02` and at `p=0.0` must be **bit-identical**. That is control **C7**.

## 4. ONE PANEL BUILD, THREE SCORINGS

The panel is built **once**, and each cross-section calls `build_frame` **three times** on the same
`metrics` list — once per arm — persisting the two challenger theme sets alongside the incumbent's
under `rk_<theme>` and `nw_<theme>` prefixes. This is the `sector_neutral_pair` pattern from
`SECTOR-NEUTRAL-B6` (session 20), generalised.

The reason is not convenience. **A full backtest is not reproducible run to run** — this project
has three identical-data runs giving `insider` median IC −0.0034 / +0.0155 / −0.0034 — so building
the arms as separate runs puts that nondeterminism **inside the difference**. Building them in one
pass makes it **common-mode, and it cancels.** Both prior sector-neutral rejections were separate
runs; that defect is not repeated here.

`build_frame` copies its input (`pd.DataFrame(metrics)`) and never mutates the caller's list, so
the three calls differ by the standardiser and by nothing else.

## 5. THE PRIMARY GATE — the shipped one, at margins already committed

**`fundamental_panel.holdout_compare_panels`**, unmodified. It splits the shared rebalance dates in
half by time, **embargoes the boundary date**, and requires the challenger to beat the incumbent by
**BOTH** pre-committed margins in **BOTH** halves:

* `MIN_HOLDOUT_ALPHA_GAIN = 0.01` — **+100 bps/yr** top-decile alpha
* `MIN_HOLDOUT_TSTAT_GAIN = 0.25` — **+0.25** long-short *t*

Both constants are **already in the tree** at `fundamental_panel.py:3115-3116` and are not
restated, re-derived or adjusted by this study. Verdicts are the function's own words: `adopt` /
`reject` / `not_replicated`.

**Universe: the full corrected panel — ~2,531 names, 69 rebalance dates, 2009-01-15 → 2026,
H = 63.** Per the METHODOLOGY RULE a verdict may come from nothing smaller.

### Two weightings, fixed here, and no others

* **DEPLOYED** — `value, quality, momentum, insider, capital_discipline, size, institutional`.
  **This arm carries the verdict.**
* **FLAT** — DEPLOYED plus `growth` and `low_risk`, the two themes the deployed vector zeroes.
  This tests whether the answer depends on the weighting at all.

`base_weight = 0.125` in both, as the gate's own default. `sentiment` is excluded from both because
it is empty (control C6).

### 5a. Verdict rule, per arm, fixed in advance

* **ADOPTED** iff the **DEPLOYED** gate returns `adopt` **AND** the FLAT gate does not return
  `reject`.
* **REJECTED** iff the **DEPLOYED** gate returns `reject`.
* **NOT REPLICATED** in every other case.

An ambiguous result is a **NULL**, per `RUN_RULES.md` A6. The two arms are judged **independently**;
neither can rescue or condemn the other.

## 6. SECONDARY STATISTICS, AND THE CALIBRATED BARS

Reported for every arm under both weightings. **None of these can overturn §5a** — they are
described here so that no statistic gets promoted to a verdict after the fact.

Calibrated floors, quoted from X7 / session 10:

| floor | value |
|---|---|
| long-short **HAC** *t* (the statistic this project quotes, per R9) | **2.2837** |
| top-decile alpha **HAC** *t* | **2.2913** |
| long-short naive *t* | **2.1437** |

**These are valid at exactly one configuration — the full-universe decile book, 69 dates, H = 63,
HAC lag 1 — which is the configuration this study runs.** They are quoted without caveat for the
incumbent arm and are **an EXTRAPOLATION for the challenger arms**, because a floor is a percentile
of a null distribution generated under the incumbent construction and nobody has run a placebo
under a rank composite. Every appearance of a challenger-arm floor comparison must carry the word
**extrapolation**. (A calibrated floor is also a function of `N` — session 12 — and `N` moves in
§10; the floors were checked to be unchanged at the current `N` when session 20 last ran them.)

### 6a. The paired within-panel difference — UNCALIBRATED

Two arms scored on the same dates share the market move that dominates each level, so differencing
them cancels it. Computed via `quantile_backtest(..., return_series=True)`, which returns the
per-period draws so the pairing uses the **shipped** arithmetic (V2G).

**There is no calibrated floor for a paired within-panel difference** — X7 and session 10 calibrate
*levels*. The bar used is the conventional **|t| = 2.0**, and it is **UNCALIBRATED and labelled so
everywhere it appears.** It cannot overturn §5a.

## 7. THE TOP-25 BOOK, BY NAME — a deliverable, not a statistic

For the most recent rebalance date, the **top 25 names under each arm**, side by side, with the
overlap count and the names entering and leaving. The book is the deliverable; a construction
change that moves statistics by little may still hand the user a materially different list, and
that is worth seeing directly rather than inferring from a correlation.

**This carries NO verdict.** It is one date, chosen for recency and not for anything else, and a
single cross-section is not evidence about a construction.

## 8. WHAT IS DELIBERATELY NOT RUN

* **No grid over the winsorisation level `p`.** One alternative (`p = 0`) and no other. Sweeping
  `p ∈ {0, 0.01, 0.02, 0.05}` and reporting the best cell is exactly the in-search **+8.43%/yr →
  locked hold-out −0.04%/yr** failure this project has already paid for once.
* **No layer attribution.** Each arm moves L1 and L3 together, so this study **cannot** say which
  layer any effect came from. Splitting them is two more arms and would be a grid; if an arm
  produces a material effect, the attribution is a **separate future register**, and that is
  recorded in the ledger rather than left looking done.
* **No placebo, no per-arm PBO or Deflated Sharpe, no CPCV re-selection.** The weights are fixed by
  §5; nothing is selected, so there is nothing for CPCV to adopt.
* **No third arm**, no interaction of RANK with anything else, and no re-test of robust z (P6.3
  rejected it; re-running it is forbidden without a new reason).
* **`sector_neutral` stays `false`** and is not touched. `SECTOR-NEUTRAL-B6` closed it permanently.

## 9. CONTROLS — all seven measured and reported, pass or fail

* **C1 — the incumbent arm reproduces the published record to the digit.** `top_decile_alpha`
  0.071741423321, `long_short_tstat` 2.8360640685320595, `long_short_tstat_nw` 2.6199,
  `top_decile_alpha_tstat_nw` 4.3762, `monotonicity` −0.8909090909090909, `equal_weight_ann`
  0.18137118752419476. A miss means the harness is wrong and **no verdict is issued**.
* **C2 — identical row sets.** All three arms must carry the same `(date, ticker)` key set and the
  same row count. Two arms need not *score* the same names — an arm can rank a name the other
  cannot — so the scored counts are reported separately and any divergence is stated, not assumed
  away.
* **C3 — the toggles are NOT inert.** Cross-sectional correlation between each challenger composite
  and the incumbent, and the count of names changing decile. **If an arm is inert that IS the
  finding** and is reported as such — a null from an inert toggle is not evidence about the
  hypothesis, and saying so is the difference between a measurement and a formality.
* **C4 — no new missing values.** Per-theme non-null counts identical across arms.
* **C5 — per-NUMBER Spearman IC is EXACTLY invariant under A20 at L1.** Ranking a column is
  monotone, and Spearman IC is invariant to a monotone transform, so `max |ΔIC|` must be `< 1e-12`
  across every `z_*` column. **This is the P6 lesson in provable form**: the per-signal diagnostics
  are *mathematically incapable* of seeing this change, while the composite may move a great deal.
* **C6 — `sentiment` is empty** in every arm and carries no weight; `insider` is constant on the
  live path but not on the panel, and its L1 exemption (§3) is verified rather than assumed.
* **C7 — A20 is invariant to winsorisation.** The RANK arm computed at `p = 0.02` and at `p = 0.0`
  must be **bit-identical**, proving A20 subsumes A21.

## 10. TRIAL COST — charged before the result is known

Two hypotheses, each measured under two pre-specified weightings, no grid: **n = 4**.

**Equity `N` 151 → 155.** √(2·ln 155) = **3.1760**. Understating `N` overstates the significance of
every DSR-gated claim, so the count is charged whatever the outcome, including a null and including
an inert toggle. `BACKTEST_RESULTS.json` is re-run from a **clean tree** afterwards so the artifact
matches the record rather than going stale on the denominator.

## 11. VINTAGE — adoption QUEUES, it does not race

Under **Amendment 1** (`PAPER_TRACK_CONTRACT.md` §5a) an **ADOPTED** change to scoring, weights or
construction closes the current vintage and opens the next. Both arms here are construction changes
in the live scoring path, so **either adoption is a VINTAGE EVENT**: it would close vintage 2
(opened 2026-08-10, `params_id 0060c5ef3dda`), reset the entire accrued forward clock to zero, and
buy **nothing** statistically (§2 of the contract: 60 months at 49% power).

**FIXED HERE, BEFORE THE RESULT: an adoption from this study QUEUES BEHIND THE THEME RESTORATION
AND MUST NOT RACE IT.** `PREREG_v2g_live_theme_sources.md` §1 is building live sources for the three
dead themes — `insider`, `capital_discipline`, `institutional`, together **42.9% of the composite's
weight mass**, currently inert on the live path (V2G). That restoration is the larger change and
has the prior claim on the next vintage. Two adoptions landing separately would spend **two** clock
resets for one restart's worth of evidence.

So: **this study ADOPTS NOTHING on its own authority.** A challenger that clears §5a is recorded as
**ELIGIBLE**, not adopted, and is handed to Don with the queueing constraint attached — it ships,
if at all, **in the same vintage as the theme restoration or after it, never before and never in a
vintage of its own.** `settings.FACTOR_WEIGHTS`, `CONFIG` and every shipped default are untouched by
this study in every outcome.

## 12. EXPECTATIONS — written before the run, because they keep being wrong

This project's directional calls have been wrong more often than right (R10, O20, the spread toll,
U7, X3, S22 on both headline questions). They are recorded to be scored, not to be trusted.

1. **A20 (RANK) is REJECTED by the gate — 65/35.** The gate is demanding and almost everything
   rejects. But I expect it to be **materially non-inert**, composite correlation in **0.93–0.99**.
2. **A21 (NOWINSOR) is REJECTED by the gate — 70/30**, and I expect its effect to be **negative**:
   P6's mechanism says tail *inflation* hurts selection, and removing the clip inflates tails.
3. **The two arms move the composite in OPPOSITE directions — 60/40.** Rank compresses tails,
   nowinsor expands them; if P6's mechanism is the operative one they cannot both help or both hurt.
4. **C5 holds exactly** (a mathematical identity, so this is a check, not a prediction) **and the
   theme ICs move by less than the composite does — 70/30.** Concretely: at least one arm shows a
   max |Δ theme IC t| < 0.5 while its top-decile alpha moves by more than 1pp.
5. **`size` is the theme whose value changes most under A20 — 55/45**, being the only single-column
   theme.
6. **The top-25 books overlap by 15–22 of 25 under A20 — 50/50**, stated as a genuine coin flip:
   the composite correlation and the *book* overlap are different quantities and this project has
   no prior for the second.

## 13. ARTIFACT

`data/free_analysis/S20_S21_CONSTRUCTION.json` — every arm, both weightings, both halves, the
paired per-period draws, all seven controls, and the top-25 books by name. **Per `RUN_RULES.md` A9
the per-period draws are stored, not only the summaries.**

Reproduce with `python -m scripts.construction_rerun`.
