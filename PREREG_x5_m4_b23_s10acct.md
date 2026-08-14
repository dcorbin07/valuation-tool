# PRE-REGISTRATION — X5 + M4 + B23 + S10-ACCT: the last four rows

**Registered 2026-08-14, blind.** Committed **ALONE** — one `.md`, zero `.py` — and a strict git
ancestor of every commit that measures anything.

**Four audit rows, two kinds.** `X5` and `S10-ACCT` are **measured hypotheses** charged to
`equity`. `M4` and `B23` are **correctness and speed** charged to `infra`; neither may change a
number, and B23's whole gate is that it does not.

---

## 0. Premise findings — measured BEFORE this register

### 0a. B23's premise HOLDS, and its line numbers have rotted

The audit cites `:3197` and `:3506`; today those are **`:4772`** (inside `run_backtests`' horizon
loop) and **`:4785`**. Re-derived from the code rather than trusted:

* `run_backtests` loops `horizons = [63, 252, 756]`, each calling `run_backtest`, which builds a
  panel at `:4418` — **three builds**.
* It then builds a **fourth** at 63d with `keep_numbers=True` (`:4785`).
* **So two of the four are at 63 days and differ only in the diagnostic `z_*` columns.**

**A partial fix already landed and is NOT the one B23 asks for.** The comment at `:4781` records
that the per-signal path was changed to reuse this panel *"instead of twice"*; the remaining
fallback at `:4694` is **guarded** by `if not _psig:` and does not fire on a normal run. **The
duplicate B23 names — the 63d horizon build versus the 63d `keep_numbers` build — is still there.**

### 0b. S10's accounting half is buildable, EXCEPT for the leg that cannot be built at all

All **eight** columns the S17/S19 register named as blockers are **present in the export and absent
from `_KEEP`** — verified today, column by column: `assetsc`, `ppnenet`, `depamor`,
`workingcapital`, `retearn`, `liabilities`, `ncfcommon`, `ncfdebt`. **So it forces a panel rebuild,
which is why S17/S19 declined it, and nothing else blocks three of the four legs.**

**NT filings remain unbuildable from anything we own.** The audit's veto is *"flagged by **two or
more**"* of **four**; this can only run **two or more of THREE**.

**THE DIRECTION OF THAT DEVIATION IS FIXED HERE, BEFORE ANY RESULT, BECAUSE IT IS NOT NEUTRAL:
dropping a flag makes the veto NARROWER, not stricter.** A name flagged by NT plus one other would
have been excluded under 2-of-4 and is not excluded under 2-of-3. **So this tests a WEAKER screen
than the audit specified, and a null here does not clear the audit's own four-flag rule** — it is
the closest testable relative of it. Choosing 2-of-3 *after* seeing the results would be the
different-rule-after-the-fact error; it is chosen now, with its direction stated.

### 0c. X5 cannot rebuild the panel per draw, and the number says why

The audit asks to *"re-run the full panel and decile backtest"* on each of ~200 resamples. **A full
panel build takes about twenty minutes on this machine** — measured repeatedly this session — so
200 rebuilds is **roughly 66 hours**. That is not a preference; it is out of reach.

**What is resampled, and what is not, stated so the result is not over-read:**

* **Resampled:** which names enter the cross-section, and therefore the **layer-3** standardisation
  (themes → composite) and the entire decile sort — because `quantile_backtest` calls
  `composite_from_frame`, which **re-standardises within whatever slice it is given.** Verified in
  the code, not assumed.
* **NOT resampled:** **layers 1–2** (raw numbers → theme columns), which `build_frame` computed once
  across the full universe per date. A true nested bootstrap would redo those too.

**So X5 as run bootstraps name-selection uncertainty in the SCORING AND SORTING, holding each
name's theme scores at their full-universe values.** That is the dominant term for a
cross-sectional strategy and it is the term the audit's own argument is about — but it is not the
whole of it, and **the resulting interval is therefore a LOWER BOUND on total name-selection
uncertainty, not the whole of it.**

**PBO IS NOT COMPUTED PER DRAW, and is declared absent rather than quietly dropped.** The audit
lists it; PBO comes from `cpcv_validate`, which is itself a multi-fit procedure, and 200 of them is
the same infeasibility again. **X5 reports alpha, long-short *t* and monotonicity. PBO is not in
this item's scope and no PBO figure from it may be quoted.**

### 0d. M4's target has already been fixed once, which changes what the harness is FOR

Audit **B7** found three composite functions and no shipped path reproducing the backtested one. It
was **fixed 2026-08-04**, and the record states *"Live and backtest score identically (max abs
difference 0.0), pinned by `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`."*

**So M4 is not expected to find a live-vs-backtest divergence today, and a harness that merely
confirms 0.0 would be worth little.** Its value is as a **standing detector**: B7's pin compares
*one* synthetic frame, while M4 replays a **real historical date on the real universe**. The
register's expectation is agreement; **the deliverable is the harness plus one verified replay**,
and the finding — if any — will be about what the replay exposes, not about the correlation number.

---

## 1. X5 — bootstrap the pipeline

**Method.** `B = 200` resamples of the 2,531-name universe **with replacement, at full size**,
seeded and banked. Each is scored by the shipped `quantile_backtest(n_q=10, horizon=63)` under the
deployed flat 1/7 weights, on the banked `panel_r5r6.pkl` (69 dates, 113,945 rows — the panel R5+R6
and R4+X1 both gated bit-identical).

**Duplicate names are kept as duplicates** — that is what a bootstrap is; a name drawn twice
contributes two rows to its date's cross-section and is twice as likely to enter a decile. **The
alternative (de-duplicating) would be a subsample, not a bootstrap, and would understate the
variance.**

**Reported:** the full distribution of `top_decile_alpha`, `long_short_tstat_nw` and
`monotonicity` — mean, median, p05, p25, p75, p95, min, max — via the shipped
`statistics.distribution`, plus every draw banked.

### Verdict rule, fixed now — the audit's own

> **A1 (alpha): STRONG** iff the **5th percentile of `top_decile_alpha` across the 200 draws is
> POSITIVE.** *"If the 5th percentile of that distribution is positive, the result is strong. If it
> straddles zero, the point estimate has been carrying more weight than it can bear."*
>
> **A2 (long-short *t*): STRONG** iff the 5th percentile of `long_short_tstat_nw` is **above zero**.
> Zero, not 2.0 and not X7's 2.2837 — this is a question about whether the *sign* survives
> name-selection uncertainty, and a bootstrap percentile is not a *t*-test.

**Ambiguous against either bar is a NULL** (`RUN_RULES` A6). **A p05 below zero is reported as
`STRADDLES ZERO`, in the audit's own words, and is its own verdict rather than a null.**

---

## 2. S10-ACCT — the red-flag veto, on three of four legs

**Registration of the eight columns into `_KEEP` is a data-availability change, not a scoring
change**, and **C-B23-1 gates that the composite is unmoved by it.**

**The three flags, per the audit and per their published definitions:**

* **Beneish M-score** — the eight-variable index (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA).
  Flag when **M > −1.78**, the published threshold.
* **Altman Z-score** — the manufacturing five-variable form. Flag in the **distress zone, Z < 1.81**,
  the published threshold.
* **External financing** — combined debt **and** equity issuance, `ncfcommon + ncfdebt` scaled by
  assets. Flag the **top decile** of issuance within each date.

**Both published thresholds are used as published.** Fitting either on this panel and then scoring
on it is the in-search → hold-out collapse this project has already paid for.

**Veto:** exclude any name flagged by **two or more of the three** (§0b), then re-run the decile
backtest on the survivors.

### Verdict rule — the audit's own threshold, with the caveats S10's first half established

> **ADOPT-ELIGIBLE** iff **maximum drawdown improves by more than 2.0pp** **AND** **top-decile
> alpha falls by less than 1.0pp**.

**Three caveats travel with it and are fixed here, because S10's first half paid for each:**

1. **`max_drawdown` is NEGATIVE, so an arm improves it by being LESS negative and the gain is
   `arm − base`.** S10's first cut computed `base − arm` and **reported a 2.61pp WORSENING as a
   2.61pp IMPROVEMENT.** Pinned by a test carrying a known-bad fixture.
2. **X7 calibrates NO drawdown floor anywhere**, so the 2.0pp bar is **UNCALIBRATED** and is
   labelled so wherever it appears.
3. **The 1.0pp alpha allowance sits BELOW X7's calibrated 1.95pp margin**, so it survives only as a
   **non-inferiority** allowance: **a pass means "no alpha loss detectable at this panel's
   resolution", NEVER "the loss is under 1pp".**

**Second arm, and the audit calls it the number that matters most:** **A2 — the count and identity
of excluded names that subsequently fell more than 50%**, against the same rate among the names
kept. **S10's first half found the valuation screen deleted names that crashed at HALF the rate of
those it kept**; this asks the same question of an accounting screen. **A2 carries no calibrated
floor and is reported as a measurement, not a verdict.**

---

## 3. M4 — the live-replay harness

**Build.** A harness that takes a historical rebalance date and the panel's universe, scores it
through the **live** path (`screen.build_frame` under production `CONFIG`), and compares the
resulting **ranks** against the backtest panel's composite on the identical `(date, ticker)` rows.

**Threshold, fixed now:** **Spearman rank correlation ≥ 0.99**, and the harness **raises** below it
rather than warning. **Given B7's fix the expectation is ~1.0**; the threshold is set where a
*material* divergence would trip it while ordinary floating-point and tie-handling would not.

**Deliverable: the harness plus ONE verified replay on a real historical date.** A harness with no
executed replay is the thing this catalogue keeps finding — a check that has never run.

**Not in scope, and named:** the options lane's own version (the audit's second paragraph — three
ATM implied-vol definitions in production). **That is the options lane's to build.**

---

## 4. B23 — one 63-day build instead of two

**Fix.** Build the 63-day panel **once with `keep_numbers=True`** and reuse it for the 63-day
horizon, since the `keep_numbers` panel is a **superset** of the plain one — the flag only *adds*
`z_*` columns.

> **THE GATE IS BIT-IDENTITY, AND IT IS THE WHOLE ITEM. Every leaf of
> `BACKTEST_RESULTS.json` must be unchanged except `generated_at*`, `git.*` and the `N`-chain
> fields that move because trials were logged this session. ZERO other moved leaves, ZERO removed.
> A single changed number means the reuse is not equivalent and the change is REVERTED, not
> explained.**

**Speed is reported and is NOT a threshold.** The audit predicts 40–50%; whatever it is, it is
recorded, and **a smaller saving is not a failure — a changed number is.**

---

## 5. Controls

| id | control | gating? |
|---|---|---|
| **C1** | The full-universe headline reproduces from the panel before any resample: `top_decile_alpha` 0.07174142332098163, LS naive 2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909. Runs in its **OWN pass**. | **YES** |
| **C2** | X5's resamples are genuine bootstraps: size 2,531 **with replacement**, duplicates retained, and the mean number of distinct names ≈ 63.2% of the universe (the 1−1/e limit) — asserted, so a silent switch to sampling without replacement is caught. | **YES** |
| **C3** | S10-ACCT: registering the eight columns leaves the composite **bit-identical** (same gate as B23). | **YES** |
| **C4** | **Coverage first**: per-flag coverage and the excluded-name count per date, before any alpha is read. A flag below 30% coverage is VOID, not null. | no |
| **C5** | The drawdown sign convention, pinned by a **known-bad fixture** carrying S10's real measured pair, so the first cut's inversion cannot recur. | no |
| **C6** | Beneish and Altman reproduce a **hand-worked example** each, so a transcription error in an eight-variable index is caught before any verdict. | no |
| **C7** | B23: the reused panel is **column-for-column a superset** of the plain 63-day build, asserted rather than assumed. | no |
| **C8** | M4's replay is on a **real historical date** with ≥ 500 shared names, and the harness **raises** below its threshold. | no |

---

## 6. Void conditions

1. Any `.py` in this file's commit, or this file not being a strict ancestor of every measurement
   commit.
2. Any arm, flag, threshold or draw count beyond those named here.
3. Fitting the Beneish or Altman thresholds on this panel.
4. Reporting a PBO figure from X5, or a four-flag verdict from S10-ACCT.
5. **Any changed leaf in `BACKTEST_RESULTS.json` attributable to B23 or to the `_KEEP` addition**,
   explained rather than reverted.
6. A failing **C1**, **C2** or **C3** with any number nevertheless read.
7. Editing this register after any result exists.

---

## 7. Expectations, with odds

1. **X5's alpha p05 is POSITIVE — the headline survives its own bootstrap.** 70/30. X1 already
   showed 200 of 200 half-books positive, and a full-size resample is a milder perturbation than a
   half.
2. **X5's long-short p05 is positive but close to zero.** 55/45.
3. **The bootstrap interval is WIDER than the half-universe spread X1 measured.** 60/40 — with
   replacement, a draw can over-weight a name.
4. **S10-ACCT is REJECTED**, like S10's valuation half. 75/25.
5. **The excluded names crash at a rate no higher than the kept names** — S10's first half's most
   striking finding, reproduced on an accounting screen. 60/40.
6. **M4's rank correlation is ≥ 0.999**, i.e. B7's fix holds on a real date. 80/20.
7. **B23 is bit-identical and saves 20–35%** — less than the audit's 40–50%, because only one of
   four builds is removed. 65/35.
8. **At least one of the four items turns up a defect in shipped code.** 55/45.

---

## 8. Trial cost

| item | domain | trials |
|---|---|---|
| X5 | equity | **2** (alpha, long-short) |
| S10-ACCT | equity | **2** (the veto, the crash-rate mechanism) |
| M4 | infra | **1** |
| B23 | infra | **1** |

**Equity `N` 220 → 224. Infra `N` 12 → 14.** Re-measured from `research_log.detail()` after this
session's merge (equity 220, options 292, unified 0, infra 12), not quoted from `CLAUDE.md`. The
`n` column is written as the literal `n=<k>` form the parser requires.

`BACKTEST_RESULTS.json` is refreshed from a clean tree at the new denominator.

---

## 9. What this register does NOT do

* **It does not rebuild the panel per bootstrap draw** (§0c) — infeasible at ~66 hours, and the
  scope limit is stated rather than hidden.
* **It does not report PBO from X5** (§0c).
* **It does not test the audit's four-flag veto** — NT filings are unbuildable, so this is the
  three-flag relative and a null here does not close the four-flag rule (§0b).
* **It does not build the options lane's live-replay harness** (§3).
* **It does not change any score, weight or threshold.** Three separate bit-identity gates say so.
