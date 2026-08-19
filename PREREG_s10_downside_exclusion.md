# PRE-REGISTRATION — S10, the downside-exclusion screen

**Committed ALONE, before any measurement code exists.** Every threshold, arm, control,
expectation and trial charge below is fixed here and is not restated from a result. This file is
a strict git ancestor of the commit that implements the measurement.

Ledger row: `S10 | S | Downside-exclusion screen | OPEN | ... | src=auto | only forward
references -- mentioned as a dependency, never written up`.

---

## §0 — WHICH S10. THIS REGISTER RUNS A DIFFERENT INSTRUMENT FROM THE AUDIT'S TEXT, DELIBERATELY

`VALQUO_EDGE_AUDIT.md:739` specifies S10 as an **accounting red-flag veto**: Beneish M-score,
Altman Z-score, combined external financing, and NT late-filing notices from EDGAR, adopted as a
two-or-more-flags exclusion.

**This register does not test any of those four.** It runs **Don's own question**, formalised:

> *Should names whose scenario band sits at or below price make the book at all?*

That is a **valuation-band** exclusion, not an accounting-fraud one. Both are "downside exclusion"
in spirit; they are different instruments, they use different data, and a verdict on one is not a
verdict on the other. **After this register lands, the audit's four accounting components remain
untested and S10's accounting half stays OPEN.** The ledger row must not be closed as though the
Beneish/Altman work had been done.

The row is `src=auto` — *"a lead, not a fact"*, the same provenance class that made **S21's
premise wrong** (it proposed behaviour the code already shipped). So §1 checks the premise against
the code before anything is built.

## §1 — PREMISE CHECK, AGAINST THE CODE, BEFORE BUILDING

Verified by reading, not by trusting the item text:

1. **Nothing in the equity path applies a valuation screen to entry.** `_backtest_hold` accepts
   `fv_at_or_above`, but that is **S23's EXIT** — a set of `(date, ticker)` pairs at which price
   has *reached* fair value and the name is **sold**. S10 is the opposite direction (refuse to
   *buy*). The premise is genuinely unshipped; this is not S21's situation.
2. **`lean_fair_value` — the S23 point-in-time path — computes the BASE case only.** It returns
   `fair_value`, `gap`, `upside`, `dcf_ps`, `comps_fv`, `growth_ps`. It has **no bear/bull band**.
   So the band must be added to the PIT path; it cannot be read off the banked panel.
3. **`financial_scenarios` is financials-only** (flexes ROE ±20%) and is not the general band.
4. **The general band is `pipeline._blend_scenarios`**, which runs bear/base/bull through the
   **same blend as the headline** and sets `blend.value_low` / `blend.value_high`. `value_high` is
   the number the website shows as the top of the scenario card. **That is the instrument.**
5. **A full-universe PIT fair-value panel already exists** from S23 —
   `data/free_analysis/panel_s23_fairvalue.pkl`, 108,241 rows, 69 dates 2009-01-15 → 2026-01-28,
   2,441 tickers, `valuable` 99.9%, covering 93.92% of the corrected factor panel. It is reused as
   a **control** (§6 C1), not as the source of the band.
6. **Cost measured before committing to the faithful instrument** (scoping, zero trial cost):
   ~1.0 ms per base valuation and ~0.7 ms per scenario-band valuation on a 60-name probe, i.e.
   **the band is not more expensive than the base**. A full-panel rebuild is ~2 min of valuation
   plus load. There is therefore **no cost argument for substituting a cheaper proxy**, and none
   is used.

## §2 — THE INSTRUMENT

For each `(date, ticker)` the point-in-time **blended bull case** is computed as

```
cls      = classify(cd)
w        = compute_wacc(cd, CONFIG, beta_override=offline_beta(pit_beta))
base     = build_base_assumptions(cd, cls, w.risk_free, CONFIG)
scen     = build_scenarios(cd, cls, base, w.wacc)
comps    = compute_comps(cd)
maturity, parts = maturity_from_company(cd, growth=cls.blended_growth)
gscn     = build_growth_scenarios(...)          # {} for the financial regime
rev      = reverse_dcf(cd, base, w.wacc)
band     = _blend_scenarios(cd, cls, scen, comps, rev, gscn, maturity, parts)
bull     = band["bull"]                          # == blend.value_high on the live path
```

**`_blend_scenarios` is IMPORTED from `valuation.engine.pipeline`, never reimplemented.** A second
copy would be free to drift from the number the site displays, which is the **B7** defect class
(*"no shipped code path reproduces the backtested composite exactly"*). Pinned by §6 C2.

`offline_beta(pit_beta)` is **S23's** pin: it stops the WACC ladder reaching its network rung and
valuing a 2011 cross-section with a beta regressed on 2021-2026 returns. **No hindsight.**

## §3 — THE FLAG

```
bull_below_price(date, ticker)  :=  bull is not None  AND  bull <= price
```

`price` is the point-in-time close already stored on the panel row — the same price the forward
return is measured from, so the flag and the outcome share one price basis.

**A name with NO computable bull case is KEPT, never excluded.** Excluding on missing data is a
*data-availability* screen wearing a valuation screen's name, and it would silently correlate with
company type (early-period, foreign, financial). The kept-on-missing rule is pinned by test.

**Coverage is reported before any verdict** (the COVERAGE RULE): the bull-case coverage of
top-decile rows, and the flagged fraction, are stated first. §6 C6 voids the test if the flag is
degenerate.

## §4 — ARMS

Panel: the corrected **69-date** factor panel (2,531 names, 113,945 rows). Weights: the **deployed
flat 1/7** over the seven weighted themes (`low_risk` zeroed) — V2G's A7 vector. **ONE weighting,
named here, no sweep, no grid.** Books built with the **shipped** `quantile_backtest` and
`_backtest_hold`; nothing re-implemented.

| arm | construction |
|---|---|
| **A0 INCUMBENT** | the shipped book, no screen. Free — it is the published record. |
| **A1 DROP** | flagged names removed from the book; **book shrinks**. Isolates whether the excluded names' returns are worse than the book they leave. |
| **A2 BACKFILL** | flagged names replaced by the next-ranked unflagged name; **book size constant**. **This is the PRIMARY arm** — it is the only deployable form, and it controls for concentration. |
| **M1 MECHANISM** | no book at all: within the top decile, mean forward return of flagged vs unflagged names, **paired by date**, HAC *t* at lag 1. |

The screen is applied **to the book**, after ranking — per the instruction *"excluding top-decile
names"*. It is **not** applied to the whole universe, which would also change the short leg and
confound the long-short statistic with a different intervention.

Both books are reported for each arm: the **decile book** (the research object, which carries the
calibrated floors) and the **top-25 hold book** (the product). **B17's caveat travels with the
second**: it holds up to `exit_rank` ≈ 50 names and pays neither costs nor taxes, and this file
calls it the noisiest number in the results.

## §5 — DECISION RULE, AND ITS TWO HONEST LIMITS

The audit's own asymmetric bar, restated unchanged:

> **ADOPT-ELIGIBLE iff max drawdown improves by more than 2.0pp AND top-decile alpha falls by
> less than 1.0pp — in BOTH halves.**

Halves: the 69 dates split early/late with the boundary embargoed, as in S20/S21 and
SECTOR-NEUTRAL-B6. Ambiguous against the threshold is a **NULL**, per `RUN_RULES` A6.

**LIMIT 1 — the 1.0pp alpha leg cannot be resolved from noise on this panel, and saying otherwise
would repeat X3's error.** X7's calibrated top-decile alpha margin is **1.95pp**; the audit's
1.0pp allowance sits *below* it. The direction of the bar saves it: this is a **non-inferiority**
allowance ("alpha must not fall by more than 1pp"), not a detection claim. **So a pass on the
alpha leg means "no alpha loss detectable at this panel's resolution", NOT "the loss is under
1pp".** That sentence must travel with any pass.

**LIMIT 2 — the 2.0pp drawdown bar is UNCALIBRATED and is labelled so everywhere it appears.**
X7 calibrates *t*-statistics, alpha margins, PBO and the Deflated Sharpe. **It calibrates nothing
for drawdown, and no placebo floor for drawdown exists anywhere in this project.** Max drawdown on
69 periods is a single order statistic and is far noisier than a mean. It is reported with
`risk_stats` — the **shipped** function — and never quoted as though a floor backed it.

**Comparator, for scale rather than as a bar:** audit **B21** already measures sector concentration
caps as a risk intervention on *"the same asymmetric logic as S10"*, measured and not adopted. Its
`sector_caps` block is the nearest existing reading of what a drawdown improvement on this book
looks like, and S10's drawdown move is reported beside it.

## §6 — CONTROLS, fixed before the run

* **C1 — the rebuild does not disturb the base.** The rebuilt panel's `fair_value`, `gap`,
  `dcf_ps`, `comps_fv`, `growth_ps` must reproduce the **banked S23 panel** on the shared keys.
  Any move is a defect in the scenario addition and is investigated before a verdict is read.
* **C2 — `_blend_scenarios` is the SHIPPED function.** Pinned by a test asserting identity with
  `valuation.engine.pipeline._blend_scenarios`, so a future copy-paste fails loudly.
* **C3 — band ordering is MEASURED, not assumed.** Count rows violating `bear <= base <= bull`
  and report them. The engine's own comment records a real case where a bear case came out above
  the bull case, so zero violations is a finding to verify, not a premise.
* **C4 — coverage.** Bull-case coverage of top-decile rows, and the flagged fraction, reported
  before any verdict. The kept-on-missing rule is pinned.
* **C5 — the incumbent reproduces the published record to the digit**: top-decile alpha
  `0.07174142332098163`, long-short naive *t* `2.8360640685320595`, HAC *t* `2.6199121240414884`,
  monotonicity `-0.8909090909090909`, equal-weight benchmark `+18.137%`. A mismatch voids the run
  before any arm is read — this is the harness check, and the known `insider` nondeterminism is
  exactly what it is there to catch.
* **C6 — the screen is not degenerate.** If the flagged fraction of the top decile is 0% or 100%,
  the test is **VOID**, not a null.
* **C7 — offline.** Zero network calls during the panel build, asserted (S23's rule). A live quote
  reaching a historical valuation is the defect S23 found and fixed.

## §7 — EXPECTATIONS, WRITTEN DOWN FIRST

This project's directional expectations have been **wrong more often than right** — the record
says so repeatedly and in those words. They are written first precisely because they keep failing.

1. **The screen COSTS top-decile alpha** (alpha falls rather than rises) — **70/30**. R1's re-run
   puts the book on **UMD +0.205 (t 3.65)** and **HML +0.251 (t 2.93)**. A DCF/comps bull case
   sits below price for exactly the names that have already run, so the screen should
   preferentially delete the momentum exposure R1 says is real and load further into value.
2. **Drawdown does NOT improve by 2.0pp** — **60/40**. The free-analysis lane measured that the
   book **beats the universe MORE in down quarters than up** (+3.54% vs +2.74%) and explicitly
   retracted the crisis-fragility reading. If the book is not crisis-fragile, there is less tail
   for an exclusion to remove than the audit's argument assumes.
3. **The flagged fraction of the top decile is LARGE — above 25%** — **65/35**. A 60-name smoke
   probe at 2017-07-20 (30 largest + 30 median-cap, **not** the top decile, **not** a verdict) read
   21/60 flagged.
4. **Flagged names skew HIGH momentum and LOW value** relative to the unflagged decile — **75/25**.
   This is the mechanism behind expectation 1 and is checkable directly from the theme z-scores.
5. **VERDICT: REJECT** — **70/30**.
6. **The screen does catch some genuine disasters** — the count of excluded names that
   subsequently fell more than 50% will be non-trivial in absolute terms — **while still failing
   the bar**, because it removes winners at the same time. The audit calls that count *"the number
   that matters most"*, so it is reported either way.

## §8 — TRIAL COST

**Three equity trials: A1 DROP, A2 BACKFILL, M1 MECHANISM.** Each could independently be reported
as a positive finding, so each is charged; understating `N` overstates the significance of every
DSR-gated claim. A0 is free (it is the record) and the controls search nothing.

**Equity `N` 155 → 158.** `BACKTEST_RESULTS.json` is re-run from a clean tree afterwards so the
artifact's Deflated Sharpe matches the honest denominator rather than going stale on it.

Options `N` and infra `N` are untouched — the counter is domain-scoped.

## §9 — ADOPTION

**ADOPTS NOTHING.** An adopted entry screen is a change to the live scoring path and is therefore
a **VINTAGE EVENT**: it closes the current vintage and resets the five-year forward clock for zero
statistical gain. On this evidence that is Don's call, not this session's.

If an arm clears the bar it is recorded **ELIGIBLE, not adopted**, and **queues behind the theme
restoration's vintage** rather than spending a second clock reset on the same restart — the clause
S20/S21 fixed in advance, which then bound.

## §10 — WHAT THIS REGISTER DOES NOT DO

* It does **not** test Beneish M-score, Altman Z-score, external financing or NT filings (§0).
  S10's accounting half stays OPEN.
* It does **not** change any live code path. The scenario band is added to the **calibration**
  path only; `screen.py` and the live composite are untouched.
* It does **not** re-quote any existing figure. Every published number stands.
* It does **not** sweep a grid. One weighting, one flag definition, two book arms and one
  mechanism arm, all named above.
* It does **not** test a *bear*-case or *base*-case screen. Only the **bull** case is registered,
  because Don's question is about the band's **top** edge. A base-case variant would be a second
  hypothesis and would cost its own trial.
