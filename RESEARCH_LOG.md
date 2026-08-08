# RESEARCH_LOG — one row per pre-registered test, append-only

**Audit item M1.** Started 2026-08-03 while executing `VALQUO_EDGE_AUDIT.md`.

## Why this file exists

Every multiple-testing claim in this project is currently computed against a denominator of **8**
— the eight weight schemes `_deflated_sharpe` is handed. The external audit reconstructed roughly
**146 distinct pre-registered tests** across the handoff corpus. Those two facts cannot both
inform the same claim, and the smaller one is the one shipping in `BACKTEST_RESULTS.json`.

The purpose here is a single, honest trial counter that survives sessions, so that:

- `_deflated_sharpe` can be fed a real `N` instead of 8;
- Benjamini–Hochberg can be applied across the family of *equity* signal tests, the way
  `options_autopsy` already does across its 126 option features;
- the Harvey–Liu–Zhu adjusted hurdle can be quoted for the number of trials **actually run**.

At N ≈ 146, √(2·ln N) ≈ 3.16 — which is, near enough, the Harvey–Liu–Zhu hurdle of 3.0 that the
long-short *t* of 3.52 already clears. **That is a stronger claim than the current one precisely
because it is defensible**, which is the whole argument for maintaining this file.

## Status — read this before using the count

**The retrospective population is NOT done, and `N` is NOT wired into `_deflated_sharpe`.**

The audit's own instruction was to populate this from "section A of the ledger", the reconstructed
list of ~146 prior tests. **That section is not in `VALQUO_EDGE_AUDIT.md` and no such document is
in the working folder** — only the count is quoted, in four places. So the retrospective rows have
to be re-extracted from the handoff corpus (`HANDOFF_*.md`, `OPTIONS_*.md`, the roadmap files),
which is real clerical work and was not attempted in a session already carrying thirteen
corrections.

**Wiring a partial count would be worse than the current state, not better.** A denominator of 30
carries the same false precision as a denominator of 8 while looking like it was measured. The
current statistic at least now *labels itself* as an undeflated PSR when `sr0` collapses (audit
B9), which is an honest signal. Wiring `N` happens when the count is complete, in one step.

## Schema

One row per test. A test earns a row when its threshold was committed **before** its run — that
is what makes it a trial rather than an observation. Exploratory looks, smoke tests and
diagnostics do **not** get rows; they get no claim either.

| Field | Meaning |
|---|---|
| `id` | stable, never reused. `<domain><n>` or the audit's own item ID where one exists |
| `date` | ISO date the verdict was recorded |
| `domain` | `equity` / `options` / `unified` / `infra` — BH-FDR families are formed within a domain |
| `hypothesis` | what was predicted, in one line, in the direction predicted |
| `universe` | the exact set. "full 2,710-name panel", "187-name options book", "smoke test: 12 names" |
| `metric` | the statistic the verdict rests on |
| `threshold` | the bar, as committed **before** the run |
| `verdict` | `ADOPTED` / `REJECTED` / `NULL` / `INCONCLUSIVE` / `SUPERSEDED` / `FIXED` |
| `source` | the handoff or commit carrying the numbers |

`FIXED` marks a correctness repair rather than a hypothesis test. **`FIXED` rows do NOT count
toward `N`** — repairing a bug is not a search over the data, and inflating the denominator with
bug fixes would understate the evidence rather than overstate it.

**`SUPERSEDED` ROWS DO COUNT. Resolved 2026-08-06, session 7.** This paragraph used to end
"Only `ADOPTED` / `REJECTED` / `NULL` / `INCONCLUSIVE` rows are trials", which excluded
`SUPERSEDED` — and `research_log.py` has never implemented that, because `_parse` skips `FIXED`
and nothing else. The prose and the counter disagreed, and it was not academic: the void X3 run
carries `n=12`, so the reading decides whether equity `N` is 92 or 104. Session 6 hit the
discrepancy, took the harsher number, and referred the rule here rather than settling it while
looking at its own results.

**The counter is right and the prose was wrong.** `N` is a multiple-testing denominator, and what
inflates the best-looking result is how many times the data was searched — not how the search was
labelled afterwards. A superseded search still happened, and what it found still shaped what was
run next. `SUPERSEDED` judges the validity of a RESULT; it says nothing about whether the data was
interrogated. This is the same argument the module's own docstring already makes for counting
trials that were never pre-committed, applied consistently. It is also the conservative reading:
it makes `N` larger and every threshold harder to clear.

---

## Rows

| id | date | domain | hypothesis | universe | metric | threshold (pre-committed) | verdict | source |
|---|---|---|---|---|---|---|---|---|
| C7 | 2026-08-03 | infra | The auto-merge gate covering one suite of sixteen lets regressions reach production | 16 suites, 552 tests | all suites green | every suite must pass locally before it may gate | FIXED | `HANDOFF_edge_audit.md` |
| D10 | 2026-08-03 | infra | Sharadar's schema questions can be settled from the live entitlement before it lapses | live API key | 6 documented questions | answer or record the failure | ADOPTED | `HANDOFF_edge_audit.md` |
| D10-a | 2026-08-03 | equity | Restatements append a new ARQ row, so a datekey-deduplicated TTM window can double-count a quarter | full export, 197,265 ARQ rows | share of (ticker, reportperiod) groups with >1 datekey | any non-zero share is a defect | FIXED | `HANDOFF_edge_audit.md` |
| B1 | 2026-08-03 | options | The broad options universe feeds an adjusted close into option maths that requires the as-traded price | 5 call sites, 4 modules | code + entry-IV sanity band | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B3 | 2026-08-03 | options | Expiry is marked at a stale quote rather than intrinsic value | `options_fill.round_trip` | mark age vs settlement | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B9 | 2026-08-03 | equity | The "Deflated Sharpe" is an undeflated PSR because the eight trials are indistinguishable | 8 weight schemes | `sr0` vs Sharpe | `sr0` < 5% of SR = undeflated | FIXED (relabel only) | `HANDOFF_edge_audit.md` |
| B10 | 2026-08-03 | equity | `accruals_q` is computed as Sloan and silently overwritten with FCF/NI | full panel | which definition survives `build_frame` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B12 | 2026-08-03 | equity | Every "800 largest names" result was an alphabetical slice | `WRDSProvider.universe` | sort key | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B14 | 2026-08-03 | equity | The delisting mask's coverage is measured and discarded, so a missed delisting is silent | full panel | `ended_early_unmasked` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B15 | 2026-08-03 | options | The per-trade headline is gross of commission, contrary to its documentation | all options trades | `return_pct` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B16 | 2026-08-03 | options | A dead exit module is the likeliest thing to be mistaken for the live exit logic | — | imports | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B18 | 2026-08-03 | equity | Negative enterprise value is read two opposite ways within one theme | full panel, ~0.70% of rows | sign convention | one convention across all three ratios | FIXED | `HANDOFF_edge_audit.md` |
| B19 | 2026-08-03 | equity | Every "Sharpe" in the results file is an information ratio versus zero | all books | `rf` passed to `risk_stats` | correctness, no threshold | FIXED | `HANDOFF_edge_audit.md` |
| B20 | 2026-08-03 | equity | `earnings_yield` switches numerator definition mid-cross-section | full panel | numerator basis | one definition throughout | FIXED | `HANDOFF_edge_audit.md` |
| B24 | 2026-08-03 | equity | `sanity_check` evaluates factors more than once, on different bases | full panel | scan-list duplicates | each factor once | FIXED | `HANDOFF_edge_audit.md` |
| B26 | 2026-08-03 | equity | A filing dated `as_of` is usable at that day's close | insider + grades | `searchsorted` side | exclude same-day | FIXED | `HANDOFF_edge_audit.md` |

**Trials counted toward `N` from this session: 1** (D10; the rest are `FIXED`). The pre-committed
thresholds for **R1**, **R2** and **R7** are recorded in `HANDOFF_edge_audit.md` Part 0 and become
rows when they run.

---

## How to add a row

1. Write the hypothesis and the threshold **before** the run, in the session handoff.
2. Run it.
3. Append one row here with the verdict — including, especially, the rejections and the nulls.
   A log that only records adoptions is a denominator of 8 with extra steps.
4. Never edit or delete a row. A superseded result gets a **new** row with verdict `SUPERSEDED`
   pointing at the one that replaced it.

---

## Rows — retrospective reconstruction (added 2026-08-05, audit M1)

**Counting rule (changed 2026-08-05, and the change matters):** a trial counts whether or not its
threshold was pre-committed. The original rule — "a row is earned when the threshold was committed
before the run" — is the right test for whether a RESULT is credible and the wrong one for a
multiple-testing DENOMINATOR. What inflates the best-looking result is how many times the data was
searched, not how well each search was documented. The old rule would have systematically
understated `N` and therefore OVERSTATED significance, which is the exact error M1 exists to fix.
`pre` records `yes` (threshold in writing beforehand) or `retro` (reconstructed from the record).
`FIXED` rows still do not count. `n=<k>` marks a pre-registered GRID of k cells counted as k.

| id | date | domain | pre | hypothesis | metric | verdict | n | source |
|---|---|---|---|---|---|---|---|---|
| P5-1 | 2026-07-30 | equity | yes | Zeroing `low_risk` improves the composite out-of-sample | held-out LS t + alpha, both directions | ADOPTED | n=1 | CLAUDE.md, HANDOFF_STATUS.md |
| P5-2 | 2026-07-30 | equity | yes | Zeroing `insider` improves the composite out-of-sample | held-out LS t + alpha, both directions | REJECTED | n=1 | CLAUDE.md |
| P5-3 | 2026-07-30 | equity | retro | `neg_asset_growth` earns its place in capital_discipline | signal IC t | REJECTED | n=1 | CLAUDE.md |
| P6-1 | 2026-07-31 | equity | yes | The edge survives realistic trading costs | breakeven one-way bps vs cost profile | ADOPTED | n=1 | CLAUDE.md |
| P6-2 | 2026-07-31 | equity | yes | TTM ROE/ROIC beat quarterly (smoothing beats recency) | signal IC t | REJECTED | n=2 | CLAUDE.md |
| P6-3 | 2026-07-31 | equity | yes | Median/MAD robust z-scores beat mean/sd | composite LS t | REJECTED | n=1 | CLAUDE.md |
| P6-4 | 2026-07-31 | equity | yes | momentum and institutional are redundant and should consolidate | composite LS t | REJECTED | n=1 | CLAUDE.md |
| P3 | 2026-07-29 | equity | retro | SF3 per-manager conviction predicts returns | signal IC t | REJECTED | n=3 | CLAUDE.md (sm_conviction/holders/breadth; breadth kept) |
| P4-1 | 2026-07-29 | equity | retro | F-Score adds to quality | signal IC t | ADOPTED | n=1 | CLAUDE.md |
| P4-2 | 2026-07-29 | equity | retro | Accruals add to quality | signal IC t | ADOPTED | n=1 | CLAUDE.md |
| P4-3 | 2026-07-29 | equity | yes | Classic anomalies replicate on this panel | signal IC t | REJECTED | n=4 | CLAUDE.md (reversal, idio-vol, MAX, low-vol) |
| P10 | 2026-08-01 | equity | yes | Sector-neutral ranking improves the composite | held-out LS t + alpha | REJECTED | n=1 | HANDOFF_sector_neutral.md |
| P10-b | 2026-08-02 | equity | yes | Sector-neutral replicates under the deployed weights | held-out LS t + alpha | REJECTED | n=1 | HANDOFF_sector_neutral.md |
| PEAD-1 | 2026-08-01 | equity | yes | `pead_car` predicts returns incrementally to momentum | residualized IC t | REJECTED | n=1 | HANDOFF_pead.md |
| PEAD-2 | 2026-08-01 | equity | yes | `pead_drift` predicts returns | signal IC t, coverage floor | REJECTED | n=1 | HANDOFF_pead.md |
| EV-PIT | 2026-08-03 | equity | yes | Pricing EV at the rebalance date improves the value theme | signal IC + composite | ADOPTED | n=1 | HANDOFF_ev_fix.md |
| 13F-LAG | 2026-07-28 | equity | yes | The 13F edge is a look-ahead artifact (fresher data = stronger) | LS t + Deflated Sharpe by lag | REJECTED | n=4 | CLAUDE.md (15/45/135/225d) |
| 13F-DEP | 2026-07-30 | equity | retro | The entire edge is the institutional theme | alpha and LS t with theme stripped | REJECTED | n=1 | CLAUDE.md |
| LAZY-1 | 2026-07-25 | equity | yes | Year-over-year 10-K language change predicts returns | NW t on long-short | REJECTED | n=28 | HANDOFF_lazy_prices.md (28-cell grid, measures x horizons) |
| LAZY-2 | 2026-07-26 | equity | retro | Lazy-prices signals survive as an IC on the main panel | signal IC t | REJECTED | n=6 | HANDOFF_lazy_prices_ic.md |
| X4 | 2026-08-02 | equity | yes | The book beats an investable ETF benchmark | total-return difference | INCONCLUSIVE | n=1 | HANDOFF_free_analysis.md |
| GROWTH-1 | 2026-07-20 | equity | retro | EV/Sales promotion improves the established value branch | composite metrics | REJECTED | n=1 | HANDOFF_growth_evsales.md |
| GROWTH-2 | 2026-07-21 | equity | retro | Growth-valuation calibration improves scoring | composite metrics | REJECTED | n=2 | HANDOFF_growth_calibration.md, HANDOFF_growth_valuation.md |
| XSECT | 2026-07-27 | equity | retro | Cross-sectional exit rules improve the book | book alpha | REJECTED | n=3 | HANDOFF_deep_xsection.md, HANDOFF_deep_exits.md |
| B21 | 2026-08-04 | equity | yes | A sector cap improves net alpha | net alpha across cap levels | NULL | n=4 | HANDOFF_edge_audit.md (none/25/30/40%) |
| R1 | 2026-08-05 | equity | yes | The headline survives FF5+MOM (the word "alpha" is earned) | NW t on the intercept | ADOPTED | n=1 | HANDOFF_r1.md, HANDOFF_edge_audit.md Part 5 |
| X2 | 2026-08-05 | equity | yes | The headline is stable across rebalance grids | spread of top-decile alpha | ADOPTED | n=7 | HANDOFF_edge_audit.md Part 4 (7 grids) |
| X7 | 2026-08-05 | equity | yes | The project's thresholds are calibrated against the pipeline's noise | placebo percentiles | REJECTED | n=1 | HANDOFF_edge_audit.md Part 4 |
| R10 | 2026-08-05 | equity | yes | The edge survives an investable benchmark | excess return + NW t | ADOPTED | n=3 | HANDOFF_edge_audit.md Part 5 (costed EW, cap-weighted, SPY) |
| OPT-ENTRY | 2026-07-22 | options | retro | The options entry signal beats a random-entry control | expectancy gap | REJECTED | n=1 | OPTIONS_BACKTEST_RESULTS.md |
| OPT-VRP | 2026-07-23 | options | retro | Variance-risk-premium selling is profitable net of costs | expectancy | INCONCLUSIVE | n=1 | HANDOFF_vrp.md, OPTIONS_VRP_RESULTS.md |
| OPT-AUTOPSY | 2026-07-24 | options | yes | Some option feature separates winners from losers | BH-FDR across the feature family | REJECTED | n=126 | HANDOFF_trade_autopsy.md (126 features, BH-corrected within family) |
| OPT-TERM | 2026-07-26 | options | yes | `term_slope` retention predicts option outcomes | retention floor + expectancy | INCONCLUSIVE | n=1 | R7_term_slope_retention_floor.md |
| OPT-GREEK | 2026-07-25 | options | retro | Greeks-based filters improve option selection | expectancy | REJECTED | n=4 | HANDOFF_greeks.md |
| R2 | 2026-08-05 | options | yes | The options entry signal beats a random-entry control, on B1-B15-corrected data | expectancy gap, date-block bootstrap | REJECTED | n=1 | HANDOFF_edge_audit.md Part 6 (gap -7.47pp, CI [-13.92, -2.43], sign-test z -2.907) |
| R3 | 2026-08-05 | options | yes | Options trades are not independent; clustered inference changes a verdict | design effect vs shuffled null | ADOPTED | n=1 | HANDOFF_edge_audit.md Part 6. **SCOPE NOTE appended 2026-08-06 (session 6):** the 1.848 / null p95 1.266 in this row is the PRE-CORRECTION 3,042-trade book. The corrected 3,885-trade book is **deff 2.2121 vs null p95 1.2037**, which is what `UNIVERSE_RESULTS.json` ships. Options *t* shrinks by sqrt(2.212) = 1.487x, not 1.36x. No verdict changes. |
| R7 | 2026-08-05 | options | yes | `term_slope` clears a properly-argued retention floor and its economic arm | G3a/G3b/G3c + MIN_LATE_GAIN | REJECTED | n=3 | HANDOFF_edge_audit.md Part 6 (floor passes; economic gain -1.12pp vs +5.00pp bar) |
| O20 | 2026-08-05 | options | yes | Point-in-time liquidity selection lowers the options headline | expectancy on the PIT-liquid subset | REJECTED | n=1 | HANDOFF_edge_audit.md Part 6 (it ROSE, +3.41% -> +4.82%; audit expectation refuted) |
| S5-3 | 2026-08-06 | options | yes | The old-vs-new options gap is spread, not signal dilution | mid-fill vs touch-fill toll, paired date-block | ADOPTED | n=1 | HANDOFF_edge_audit.md session-5 closeout item 3 (toll -8.28pp, replaces the void -6.59pp; 68% spread, not 100%) |
| S5-4 | 2026-08-06 | options | yes | The four B1-touching autopsy features are informative | per-feature p, both directions | REJECTED | n=4 | HANDOFF_edge_audit.md session-5 closeout item 4 (none informative; the passing direction SWAPS when B1 is repaired) |
| S5-5 | 2026-08-06 | options | yes | Published options statistics are single-control-seed safe | CI-endpoint movement as a share of CI width | ADOPTED | n=8 | HANDOFF_edge_audit.md session-5 closeout item 5 (7 of 8 safe; effective_n multi-seed by policy; no published boolean flips) |
| X3-VOID | 2026-08-03 | equity | yes | The 7-theme composite beats its best single signal (pre-B6 panel, retired bars) | top-decile alpha gain | SUPERSEDED | n=12 | data/free_analysis/ABLATION_RESULTS.json — 110-date pre-B6 panel, alpha +11.88%, 1.0pp bar below X7's 1.95pp noise floor. COUNTS toward N (12 of equity's 111); the earlier note here said it did not, which the counter has never implemented — schema corrected session 7 |
| X3 | 2026-08-06 | equity | yes | The 7-theme composite beats its own best single signal on the corrected panel | paired per-period alpha difference, CI95 excludes zero | NULL | n=8 | HANDOFF_edge_audit.md session 6 (+4.51%/yr, CI95 [-0.14%, +9.12%]; only the full arm clears X7's LS bar of 2.14) |
| U7 | 2026-08-06 | options | yes | Refusing alerts on bottom-composite-decile names lifts the options book | mean pnl_pct lift, date-block CI95 | REJECTED | n=3 | HANDOFF_edge_audit.md session 6 (lift -0.57pp / -1.04pp / -0.44pp; interaction vs control -0.08pp; bottom decile is the 3rd BEST) |
| S4 | 2026-08-06 | equity | yes | `growth` earns a place in WEIGHTS_ESTABLISHED | zeroing it must COST >=0.25 long-short t AND >=100bps alpha in BOTH held-out directions | NULL | n=1 | HANDOFF_signals.md (costs -0.263t/-0.48pp one way, HELPS +0.549t the other; direction-dependent) |
| S4b | 2026-08-06 | equity | yes | The SPECULATIVE branch is better WITHOUT growth | holdout_theme_validate, both directions | REJECTED | n=1 | HANDOFF_signals.md (zeroing growth there is `rejected` - no evidence to remove it) |
| S1a | 2026-08-06 | equity | yes | Dropping book_to_price from the established value branch helps | holdout_compare_panels, standing margins, both directions | REJECTED | n=1 | HANDOFF_signals.md (d_LS_t -0.207 / -0.079; value theme IC t RISES 0.84->1.57 while the composite falls) |
| S1b | 2026-08-06 | equity | yes | Swapping book_to_price for neg_ev_ebitda helps | holdout_compare_panels, standing margins, both directions | REJECTED | n=1 | HANDOFF_signals.md (d_LS_t -0.270 / +0.012; value IC t 0.84->1.37, composite LS t 2.836->2.741) |
| S2 | 2026-08-06 | equity | yes | cash_op_prof earns a place in the quality theme | coverage floor, then IC t >= 2.71 (X7 calibrated), then held-out gate | NULL | n=1 | HANDOFF_signals.md (cov 95.3%, median IC +0.0026, t +0.84; corr 0.27-0.44 so distinct yet uninformative; quality IC t 3.10->2.91) |
| LOO | 2026-08-06 | equity | yes | Choosing a theme to drop by its own leave-one-out effect on a decide half improves the composite on a held-out half | measure-half top-decile alpha gain and long-short t gain vs MIN_HOLDOUT margins (100bps, 0.25) | NULL | n=7 | HANDOFF_edge_audit.md session 7 (drop momentum: -1.30%/-0.706; drop capital_discipline: +0.20%/-0.201; different theme selected each direction; 4 of 7 arms change sign between halves) |
| B8 | 2026-08-06 | equity | n/a | holdout_theme_validate computed rule_fired and never read it, so its verdict was a both-halves stability check named as an out-of-sample confirmation | oos_verdicts added, verdicts semantics frozen | FIXED | n=1 | HANDOFF_edge_audit.md session 7 (neither shipped decision changes; low_risk confirmed_oos in 1 of 2 directions, not 2) |
| P4 | 2026-08-06 | infra | n/a | seed_book never sold names that left the exported book, so the paper index was an ever-growing union of everything ever held | departed names closed into paper_index_closed, not deleted | FIXED | n=1 | HANDOFF_edge_audit.md session 7 (45/45 paper-track tests; guard refuses to act on a truncated export) |
| SELRULE-GATE | 2026-08-07 | infra | yes | Cross-country co-movement can be measured and used to calibrate a sign test's critical count | design effect vs its own shuffled null (X7 method), `clustering_measurable` | ADOPTED | n=1 | valuation/edge/cross_country.py, HANDOFF_edge_audit.md session 9 (blocks=months, observations=countries; 4 tests pin rho=0 reproducing the exact binomial k=12, no false alarm on independent data, detection of planted co-movement, monotonicity of the bar in rho) |
| SELRULE | 2026-08-07 | equity | yes | A stability-first selection rule beats the incumbent decide-half argmax, measured on 16 held-out countries | paired per-country sign test at the co-movement-calibrated critical count | NO CONTRAST | n=5 | PREREG_session9_selection_rule.md; HANDOFF_edge_audit.md session 9. TWO independent kills: (a) the design is unreachable - clustering measurable on 10/10 arm-pairs, rho up to 0.484, n_eff 1.94-4.03 of 16, so critical k = 17 of 16 and even a unanimous 16/16 gives p 0.0546; the pre-registered 12/16 bar carries a true alpha of 28.7%, not 3.84%. (b) both rules select `size` on usa, so every paired difference is identically zero |
| HACFLOOR | 2026-08-07 | infra | yes | The placebo recorder must summarise the HAC statistic it already computes, so X7's long-short floor can be re-derived on the estimator the project actually quotes | placebo output schema carries long_short_tstat_nw and its p95 | ADOPTED | n=1 | scripts/placebo.py, PREREG_session10_hac_floor.md, HANDOFF_edge_audit.md session 10. quantile_backtest computed the Newey-West t on every draw since R9 and the writer dropped it, so the 2.14 floor was derived on the naive t while the shipped statistic became the HAC 2.620 - a bar and a number from different estimators. Calibration searches nothing, so equity N is unchanged; pinned by test_session10_the_placebo_writer_summarises_the_hac_statistic_it_computes |
| O16 | 2026-08-07 | options | yes | term_slope is a front-month IV level wearing a second name: its variance and its cross-section are carried by the atm_front leg, not by the ~60-DTE leg | identity arm decides - abs(Spearman(term_slope, atm_front)) and var(atm_front)/var(term_slope); predictive arm is Spearman IC vs pnl_pct for term_slope, -atm_front and the residual, each with a date-block (calendar-month) bootstrap CI95; no-new-data control ranks by -atm_front at term_slope's own 40.6% retention | INCONCLUSIVE | n=5 | STOPPED AT THE PRE-REGISTERED REPRODUCTION GATE, no verdict on the hypothesis. Recomputed term_slope matched the banked value on only 86.435% of 3,885 rows against a required 99%. Cause attributed, not guessed: the chain store is LIVE and 19.5% of the alerts' ticker-year files were re-mined after the book was banked; rows whose chain is untouched reproduce at 100.00% (3,127 of 3,127, zero exceptions) while re-mined rows reproduce at 30.47%. EXPLORATORY read on the 3,358 exactly-reproducing rows, carrying NO verdict: Spearman(ts, atm_front) -0.5405 CI [-0.576, -0.501], below the 0.60 distinct bar, so the committed rule WOULD have said IS DISTINCT; the residual of ts on atm_front predicts BETTER than raw ts (IC +0.0774 vs +0.0645, both CIs excluding zero) while atm_front alone predicts nothing (+0.0148, CI spans zero). SUPERSEDED BY THE 2026-08-08 RE-RUN (row O16-REFROZEN below), which delivers the verdict on a refrozen book. This row is KEPT and STILL COUNTS: the arms were run, and the exploratory read they produced is exactly why the re-run was not blind and is charged again. Thresholds committed in valuation/edge/options_signals_v2.py (O16_LEVEL_RHO 0.80, O16_LEVEL_VAR_SHARE 0.60, O16_DISTINCT_RHO 0.60); ambiguous is a NULL. Book = state_r2_corrected.pkl, 3,885 trades / 186 names / 118 months. Blocking reproduction gate: recomputed term_slope must match the banked value within 1e-6 on >=99% of rows or the study stops. If the raw feature's own IC CI95 spans zero the predictive arm is declared UNINFORMATIVE and carries no verdict weight - ruled in advance because two nulls cannot discriminate. |
| O24 | 2026-08-07 | options | yes | term_slope is an earnings calendar wearing a second name: front IV inflates mechanically before earnings, so the slope is a date offset rather than a vol-surface read | OLS term_slope ~ days-to-next-earnings bucket dummies, statistic is R2 (share of term_slope variance the calendar alone reconstructs); pre-committed direction Spearman(term_slope, days) > 0 with a date-block CI95 excluding zero, a significant wrong-sign slope refutes the mechanism whatever R2 says; no-new-data control keeps only alerts >30d from earnings | NULL | n=4 | R2 0.2144, date-block CI95 [0.183, 0.248] - the WHOLE interval sits below the committed 0.25 bar - and the pre-committed monotone direction test gives Spearman +0.0018, CI [-0.051, +0.055], spanning zero. The mechanism IS visible but LOCAL and NON-MONOTONE - mean term_slope is -0.1916 in the 0-7d bucket against roughly +0.01 to +0.02 at 8-30d and -0.031 at 61-120d - which is why a categorical R2 nearly clears while a monotone rank test is near-blind to it. The pre-committed direction test was the wrong SHAPE for the effect; it was chosen before any data was seen and the verdict stands as committed. No-new-data control runs the OTHER way: keeping only alerts >30d from earnings makes the book WORSE (-0.95% vs +3.81%, diff -4.76pp, CI [-7.59, -2.10], excludes zero). Thresholds committed in valuation/edge/options_signals_v2.py (O24_CALENDAR_R2 0.25, O24_DISTINCT_R2 0.10, O24_MAX_DAYS 120); ambiguous is a NULL. Earnings dates from EVENTS code 22, the PEAD study's own point-in-time source; coverage is PARTIAL (157/186 names, 3,495/3,885 alerts carry a forward date) and an alert whose next earnings is >120d away is excluded as UNKNOWN rather than scored as far-from-earnings - the scoping pass saw an apparent 3,004-day gap, which is a hole in the calendar and counting it would load the test toward the answer this lane finds convenient. RE-CHECKED 2026-08-08 on the REFROZEN feature (chain freeze, audit O16 follow-on) and the NULL is re-confirmed rather than assumed: identical eligibility (3,458 of 3,885, 157 names, 118 months), R2 0.21443 -> 0.21555 with CI95 [0.1840, 0.2498] still wholly below the 0.25 bar, direction +0.00183 -> +0.00579 still spanning zero, and every bucket mean moving by <=0.0014 (0-7d -0.19159 -> -0.19120). 13.6% of rows differ INDIVIDUALLY and the aggregate barely moves. NO NEW ARMS: this is a re-measurement of the same registered arms on repaired inputs, so it adds nothing to N. |
| MLCOMB | 2026-08-08 | equity | yes | A shallow gradient-boosted tree over the seven deployed theme z-scores beats the flat 1/7 linear composite out-of-sample | verdict-half top-decile alpha margin >= 1.95pp AND LS HAC t margin >= 0.25 AND tree's own LS HAC t >= 2.2837, in BOTH split directions | REJECTED | n=8 | PREREG_ml_combiner.md (blind, ec6c01d) + PREREG_session11_execution_protocol.md; HANDOFF_edge_audit.md session 11; data/free_analysis/ML_COMBINER.json. Worse on alpha in BOTH directions: decide-early/measure-late d_alpha -9.70pp, d_HAC_t -2.118; decide-late/measure-early d_alpha -5.48pp, d_HAC_t -2.877. THE TREE'S DECILES RUN BACKWARDS OUT OF SAMPLE (monotonicity +0.382 and +0.842, where negative is well-ordered) while the linear arm on the IDENTICAL rows through the IDENTICAL function is well-ordered (-0.903, -0.855) and the equal-weight benchmark is identical between arms - so the inversion is a property of the model, not the harness. Every one of the 16 grid x direction cells had a POSITIVE decide-half CPCV out-of-sample rank IC (+0.011 to +0.024), so the model generalises inside the decide half and reverses across the boundary. The two directions selected OPPOSITE ENDS of the grid - decide-early picked the most complex point (d3/lr0.10/it300), decide-late the least (d2/lr0.03/it100), with capacity helping monotonically in one half and hurting monotonically in the other. Equity N 121 -> 129, DSR 0.8628 -> 0.8556, sqrt(2 ln 129) 3.118. |
| CHAINFREEZE | 2026-08-08 | infra | n/a | The option-chain store is mutable, so a banked options verdict has no reproducible referent: `data/options` is re-mined in place and the authoritative book measured 86.435% reproducible against it, with 19.5% of its ticker-year files rewritten after banking | content-addressed byte fingerprints per symbol-year with a (size, mtime_ns) sidecar cache, trade-scope frozen row copies, and a replay pin that refuses a drifted read at theta_bulk's single load choke point; descriptive at bank time, blocking only for replays | FIXED | n=1 | HANDOFF_optionsbot.md 2026-08-08; valuation/edge/options_freeze.py, tests/test_options_freeze.py (42 tests) -- Design chosen on a MEASUREMENT the brief required before rejection: a trade-scope frozen copy of the R2 book costs 157.88 MB pickle / 27.44 MB gzip over 2,870,079 rows against a 26.98 GB store (0.585%), and the artifact actually banked is 23.30 MB over 2,870,811 rows (0.086%) -- so copying is ADOPTED, not rejected, because a book is SPARSE in the store (one day in ~250 per symbol-year). Fingerprinting adopted alongside it: the copy answers 'can this verdict still be checked', the fingerprint answers 'is what I read now what was read then'. Reconciliation across all ten banked books found drift is PROGRESSIVE and tracks AGE, not the book: everything banked 2026-08-03 sits at ~56% untouched, everything banked 2026-08-05 at ~80%. Nothing is lost (0 absent symbol-years) and the store has been quiet since 2026-08-06 04:29. Frozen: R2 corrected + its five controls; retired with annotation: pre-correction, state_mid, entry lab, exit lab. NOT COUNTED toward N -- this is instrument repair, not a search. |
| O16-REFROZEN | 2026-08-08 | options | yes | term_slope is a front-month IV level wearing a second name: its variance and its cross-section are carried by the atm_front leg, not by the ~60-DTE leg | register ad686 unamended (ad66468): identity arm decides via abs(Spearman(term_slope, atm_front)) against O16_LEVEL_RHO 0.80 and O16_DISTINCT_RHO 0.60 plus var(atm_front)/var(term_slope) against O16_LEVEL_VAR_SHARE 0.60; predictive arm is Spearman IC vs pnl_pct for term_slope, -atm_front and the residual with date-block (calendar-month) CI95; ambiguous is a NULL | IS DISTINCT | n=5 | HANDOFF_optionsbot.md 2026-08-08; data/options_freeze/R2_CORRECTED_2026-08-08/ -- THE OBJECT OF STUDY CHANGED AND IT IS DECLARED: the register's gate compares against the BANKED value, that comparison fails at 86.435% and can never pass because the drifted rows' inputs no longer exist, so the verdict is delivered on the REFROZEN book -- atm_front, atm_mid and term_slope recomputed together from one frozen store and therefore mutually consistent by construction. 3,885 of 3,885 rows, 186 names, 118 months, 0 errors, 0 drift, run under a replay pin re-verified afterwards at 1,429/1,429 clean. Spearman(ts, atm_front) -0.53966, CI95 [-0.5740, -0.5022], entirely below the 0.60 distinct bar. THE VERDICT HINGES ON THE PRE-REGISTERED CHOICE OF SPEARMAN AND MUST BE QUOTED WITH THAT: Pearson is -0.82793, which CLEARS the 0.80 level bar, so the same data under Pearson returns the OPPOSITE verdict (IS THE LEVEL). Variance shares front 1.88319 / mid 0.61088 / -2cov -1.49406 exceed 1 because the legs co-move (Spearman(front, mid) +0.79093) and are uninterpretable without the covariance term. Predictive arm informative (raw IC excludes zero, so the null-vs-null clause did not fire) and it CORROBORATES distinct: residual IC +0.07034 [+0.0287, +0.1131] beats raw term_slope +0.05673 [+0.0206, +0.0922] while -atm_front alone predicts nothing +0.01316 [-0.0333, +0.0626]. CHARGED AGAIN RATHER THAN WAIVED AS A REPAIR: last cycle's exploratory read on the 86.4% subset already showed this answer, so the re-run was not blind. Options N 164 -> 169. |
| M1-PARSE | 2026-08-08 | infra | n/a | The trial counter detects a FIXED verdict by searching the whole joined row, so any row whose free text contains the word "fixed" is silently dropped from N - understating trials and therefore OVERSTATING the significance of every DSR-gated claim | verdicts, the grid multiplier and the domain must each be read from their own column; pinned by a fixture the old parser gets wrong | FIXED | n=1 | PREREG_session12_recount.md; valuation/edge/research_log.py; test_session12_the_trial_counter_reads_verdicts_from_the_verdict_column_only. THE DEFECT IS REAL AND WAS NEVER LIVE: re-running both parsers over all TEN historical revisions of RESEARCH_LOG.md gives identical counts at every one, and no `fix*` word appears outside a verdict cell in any of the 72 data rows. Equity N stays 129, DSR 0.8556, sqrt(2 ln 129) 3.118 - no published number was ever wrong. Two sibling defects of the same class fixed with it: the `n=<k>` grid multiplier was grepped from the whole line and the domain was taken from the first cell matching any domain name. |
| X7RECON | 2026-08-08 | infra | yes | The 8-vs-7 `ls_t >= 2.0` gap between X7's placebo and session 10's re-run is caused by the two sweeps running at different project trial counts, because the CPCV adopt gate's haircut is floored at the research log's N and the adopted weights then feed quantile_backtest | name the specific draw and show it crosses 2.0 under one weighting and not the other, reproducible; a plausible story is explicitly NOT a diagnosis | ADOPTED | n=1 | PREREG_session12_recount.md section 6 (committed before the sweep); scripts/x7_reconcile.py; data/free_analysis/X7_RECONCILE.json (all 100 rows retained). SEED 1005, and it is the ONLY draw of 100 whose adopt decision differs between the two N. Margin 0.00287097 vs se 0.00094470: clears the N=84 bar of 0.0028122 and fails the N=121 bar of 0.0029257. Naive ls_t 2.1273 under the challenger's weights, 1.0454 under base; session 10's retained artifact records 1.0453572947436582, matching the base-weight recomputation to sixteen digits. Substituting the adopted value into session 10's 100 draws gives EXACTLY 8 at t>=2.0, which is X7's recorded figure; the adopt count at N=84 comes back 21, which is M1's recorded 21%; and the naive p95 stays 2.1437 with max 3.436, which is why session 10's control reproduced X7's percentiles to the digit while missing one draw - 2.1273 lands just below the 95th percentile. It also explains why the gap looked undiagnosable: seed 1005 did not drift across 2.0, it jumped 1.08 of a t because its weights changed, so "no draw near the boundary" was the wrong thing to look for. CONSEQUENCE THAT OUTLIVES IT: A CALIBRATED PLACEBO FLOOR IS A FUNCTION OF N. Here the floors did not move because the affected draw landed below the percentile, which is luck rather than design; every sweep must record the N it ran at and a floor may not be compared across sweeps run at different N without checking. The SHIPPED strategy is unaffected - it does not adopt, it keeps current-default, so no haircut touches its ls_t; the exposure is to the calibration, not the headline. Zero trial cost to equity, which stays 129; logged in infra on the HACFLOOR precedent. |
| ARTIFACT-N | 2026-08-08 | infra | n/a | The canonical BACKTEST_RESULTS.json ships a Deflated Sharpe computed at n_trials=84, a denominator 45 trials out of date, so a reader trusting the artifact over the brief gets the flattering number | the artifact's deflated_sharpe must equal research_log.detail()['n_used'] at the current N, with every other published figure unchanged | FIXED | n=1 | HANDOFF_edge_audit.md session 13. Full re-run on the 2,531-name / 69-date universe from a CLEAN tree at e83df30. DSR 0.8996589404135822 at n_trials 84 -> 0.855607566829599 at 129; n_trials_from_research_log 84 -> 129 and n_trials_source still reads RESEARCH_LOG.md (audit M1), confirming session 4's wiring; sr0_benchmark 0.4056 -> 0.4303; n_trials_from_weight_schemes stays 8 so the degrade path is intact. NOTHING ELSE MOVED: a leaf-by-leaf diff gives 15 moved / 32 added / 0 removed, of which five ARE the DSR chain and the other ten moved by 0.000% (last-digit float on costs and net_sharpe). long_short_tstat 2.8360640685320595, top_decile_alpha 0.07174142332098163, monotonicity -0.8909090909090909, universe 2531/69 and every benchmarks figure are bit-identical. The known-nondeterministic insider theme reproduced to sixteen digits. THE ARTIFACT WAS ALSO STALE IN A WAY NOBODY HAD NOTICED: it predated session 7's B8 repair and shipped NO oos_verdicts block at all, plus it predated the cash_op_prof signal - so 32 leaves are additions, not cosmetics. Both shipped decisions unchanged on the fresh run (low_risk confirmed_oos, insider rejected_oos) and the sanity layer fires its two expected flags, neither silenced. The replaced file carried git.dirty true at 4f41c9f; this one records a clean commit. No trial was run, so equity N stays 129. |
