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
