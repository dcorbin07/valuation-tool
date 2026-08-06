# CLAUDE.md — Valquo project brief (read every session)

> **FIRST: read `RUN_RULES.md` (repo root) before starting any work. It is short and
> non-negotiable — it governs pushing, handoffs, bug reporting, pre-committed thresholds, and
> never silencing a check. Every agent, every run, no exceptions.**

You are picking up **Valquo** (valquo.co), a Python/Flask stock-analysis SaaS owned by Don
(donniecorbin6@gmail.com). Be honest, concise, and never oversell. Architecture is in section 4 below;
the optimization/data research roadmap is in `OPTIMIZATION_RESEARCH.md` — read it once for detail.

## What it is
Hot-stocks screener (9-theme "hot score") + options/intraday signals + a point-in-time fundamental
**backtest / Edge Lab** that proves-or-disproves the edge and tunes the screener weights. A monthly,
purely-statistical, out-of-sample-gated self-learning loop re-tunes weights.

## How to run (you can run these directly — Don cannot / will not)
- Full backtest: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --json data/backtest/last_result.json` (or `run_backtest.bat`). Reads licensed Sharadar exports in `data/backtest`. Takes 20-40 min.
- 13F due-diligence: `python -m valuation.edge.fundamental_panel --data-dir data/backtest --validate-institutional` (or `validate_13f.bat`).
- Tests (keep green, currently 16/16): `python tests/test_edge.py`.
- Deploy: Don runs `git_push.bat` himself (pushes to GitHub -> Render; Actions run the scans).

## HARD RULES (do not violate)
- **Never commit/push `data/`** (licensed Sharadar exports; gitignored) or `*.db`.
- **`.env` holds real secrets** (SHARADAR_API_KEY, ANTHROPIC_API_KEY, TRADIER_TOKEN, SECRET_KEY) — never print, commit, or overwrite.
- **Do NOT execute trades or move money** — a Robinhood connector exists (Cowork side); produce target/rebalance lists, Don executes.
- **Ignore Don's resume files entirely.**
- Repo is private; keep it clean. Keep `tests/test_edge.py` passing after every change.

## Core file: `valuation/edge/fundamental_panel.py` (the backtest engine)
- `build_fundamental_panel()` — builds the 9 themes point-in-time (reuses the live `build_frame`). `_yoy()` computes revenue/asset-growth/issuance -> `growth` + `capital_discipline`. `inst_lag_days` param stress-tests the 13F lag.
- 8 weight schemes (`_weight_schemes`), incl. `max-ir-decorr` (Sigma^-1*mu).
- Selection/validation: `walk_forward` (single-path, params) and **`cpcv_validate`** (Combinatorial Purged CV — the AUTHORITY for weights; reports PBO + Deflated Sharpe). If CPCV runs and rejects, keep defaults — do NOT fall back to walk-forward.
- `quantile_backtest` (decile / long-short), `regime_split` (edge by market-cap tier), `institutional_dependence`, `validate_institutional`.

## CURRENT STATE — the honest findings (do not oversell)
Rewritten 2026-07-30 after P5. Everything below is measured on the **full 2,710-name × 110-date
universe** (~18y, gross of costs). Several long-standing claims here were WRONG, not merely
stale — they are corrected in place and the corrections are called out, because this file is
the project's memory and the old versions had been repeated for months.

- **THE THRESHOLDS ARE NOW CALIBRATED — READ THIS BEFORE QUOTING ANY t, IC OR PBO
  (2026-08-05, audit X7). Every bar in this project was a CONVENTION until this run; three of
  the four are too low, and one is at the noise level.** `scripts/placebo.py` shuffles the
  signal within each rebalance date (block permutation: per-date distribution, missingness
  pattern and cross-theme correlation all preserved exactly; `fwd_ret`/`marketcap`/`sector`
  untouched) and pushes 100 draws through the REAL pipeline — CPCV, weight selection,
  quantile backtest, theme ICs, the held-out gate. The harness reproduces the shipped run
  exactly (t 2.83606, alpha 0.071741, PBO 0.73333) before any draw, and the equal-weight
  benchmark is +18.14% on all 100 draws (sd 0.00004), which is the control.

  | bar | as used | CALIBRATED (placebo p95) | how often pure noise clears the OLD bar |
  |---|---|---|---|
  | theme IC t | 2.0 | **2.71** (noise max 3.93) | **39%** |
  | long-short t | 2.0 | **2.14** (noise max 3.44) | 8% |
  | top-decile alpha margin | 1.0pp | **1.95pp** | 18% |
  | PBO | <50% | **<19.7%** (placebo p5; noise MEDIAN is 46.7%) | **55%** |
  | Deflated Sharpe | >0.95 | **STANDS** (noise median 0.28) | 2% |

  **THE DEFLATED SHARPE ROW IS CONFIRMED AT THE TRUE N (2026-08-06, session 5). The
  PROVISIONAL marking is LIFTED.** The placebo was re-run at `N = 84` on the identical panel
  and identical seeds. **The statistic is MORE discriminating at the honest denominator, not
  less: 0 of 100 noise draws clear 0.95, against 2 at N = 8**, and the calibrated bar (placebo
  p95) falls 0.8567 → **0.7216**. Every OTHER rate in this table is identical to the last digit
  across the two sweeps (holdout 6%, ls_t≥2 8%, maxIC_t≥2 39%, PBO<50 55%), which is the
  harness-reproduction check — so no other calibrated bar was ever in question.
  **BOTH M1 AND X7 ARE RIGHT AND THEY NEVER CONFLICTED.** The edge's 0.8997 fails the >0.95
  convention (M1) **and sits above ALL 100 placebo draws** (max 0.8649, empirical p ≤ 0.01),
  because at the honest N the 0.95 convention is STRICTER than the noise floor requires.
  **Quote it whole or not at all:** *"Deflated Sharpe 0.8997 at N = 84 — fails the conventional
  >0.95 bar, while sitting above all 100 placebo draws (calibrated bar 0.72)."* It is the one
  bar where this strategy is distinguishable from noise and still fails its threshold.
  **M1 also made the adoption gate harder for noise to pass, as a free side effect:** CPCV
  adopts on **27% → 21%** of pure-noise draws, one-directional (six draws stopped adopting,
  none started), because the adopt gate reads the Deflated Sharpe. **This is NOT the run-to-run
  non-reproducibility** — that remains open; it was briefly mistaken for it before the
  one-directional pattern was checked.

  **Use these numbers, not the old ones.** They are floors for THIS panel/universe/69 dates,
  not universal constants — re-measure if the panel changes materially. Three consequences
  that are easy to get wrong: **(a)** 39% of noise draws produce at least one theme at IC
  t ≥ 2.0, because EIGHT themes are tested and the bar is applied to whichever looks best —
  the project has always read that bar as if one theme were being tested; **(b)** the
  **held-out gate (`holdout_theme_validate`) has a measured ~6% false-positive rate**, and
  `low_risk` — the theme actually zeroed on its verdict — turned up among the false confirms
  once in 100 draws, so that decision is not overturned but must be quoted with the rate;
  **(c)** the real headline is outside the placebo's [2.5, 97.5] interval on alpha (clearly),
  Deflated Sharpe, monotonicity, max theme IC t (narrowly) and long-short t (narrowly) — and
  **INSIDE it on PBO**, which is therefore not distinguishable from noise.
- **THE OPTIONS ENTRY SIGNAL IS DEAD, ON CORRECTED DATA (2026-08-05, audit session 5 / R2). The
  project's most consequential negative finding was re-derived after five defects were repaired,
  and it SURVIVED — the gap moved 0.61pp.** Every number in `HANDOFF_universe_backtest.md` was
  computed against a mis-stated underlying price (B1) plus B2/B3/B4/B15, and that file is now
  banner-marked SUPERSEDED. Re-run on the identical pinned 187-name universe:
  **real +3.41%/trade vs a random-entry control's +10.06%, gap −6.65pp, date-block CI95
  [−11.92pp, −2.13pp], paired sign-test z −4.903 (p < 1e−5)** over 1,334 name-year cells (5
  control seeds, 29,785 control trades — see the seed note below). The
  alert's day-selection subtracts value. **Do not describe the live options alert as a
  day-selection edge; it is an alert-generation mechanism.**
  * **THE BREADTH CLAIM IS VOID.** "The edge survives breadth but roughly halves" is false. The
    133 new names are now **−0.47%/trade (PF 0.988)**; all of the book's positive expectancy is
    the original 54 megacaps (**+9.37%**). It is a megacap phenomenon that a corrupted price
    basis made look broader.
  * **B1's signature, for the record:** trades ROSE 3,042 → 3,885 because `no_contract_in_band`
    rejects fell 2,911 → 1,729 — an adjusted spot against as-traded strikes was throwing the
    0.90–1.20 moneyness prefilter, silently discarding 1,182 alerts. Median entry IV
    **1.4200 → 0.2497** at 100% coverage (was 75.3%). 142% was never a vol.
  * **A SINGLE CONTROL SEED CAN FLIP THIS VERDICT — RUN FIVE, AND READ THE SIGN TEST.** The
    control's own mean ranges **+6.46% to +15.34%** across five draws. Seed 0 alone reads
    INCONCLUSIVE and is the most favourable of the five; **all five point estimates are
    negative and four of five are negative at significance.** A random-day book's mean on a
    barbell payoff is set by a few +600% trades. **More control draws SHARPEN the test** (2-seed
    z −2.907 → 5-seed z −4.903), because each name-year cell's control mean averages more draws.
    The paired *t* ranges +0.162 to −1.835 and is never significant even pooled (−1.227, p 0.22)
    — it is the wrong statistic here. **Standing rule: five seeds minimum, sign test carries the
    verdict.**
  * **`term_slope` is REJECTED on the arm that matters (R7).** Its +8.89pp out-of-sample
    replication was an artefact; corrected, the filter makes its own out-of-sample book WORSE
    (gain **−1.12pp** against a +5.00pp bar) and is no longer tail-enriching. It PASSES the
    re-committed retention floor (G3a 95.6 alerts/yr, G3b 96.2% of names and 98.2% of months,
    G3c 35.9%) — so the old 40% constant WAS rejecting a genuinely broad filter, and the
    rejection now rests on economics instead of on an underived number.
  * **Deflated Sharpe fell below 95% on both books:** unfiltered 88.13% → **49.59%**,
    term_slope-filtered 95.69% → **80.63%**. The autopsy re-confirms: 64 features, 127
    hypotheses, **zero survivors**.
- **OPTIONS STATISTICS ARE CLUSTERED, BUT LESS THAN THE AUDIT PREDICTED (2026-08-05, audit R3).**
  Every options interval ever published resampled TRADES and is optimistically narrow.
  `valuation/edge/options_stats.py` adds a date-block bootstrap (calendar months resampled
  together), `n_eff`, the paired name-year sign test and paired *t*, purge/embargo for the CSCV
  splits, and the Deflated Sharpe at `n_eff`. **Measured clustering factor 1.85 — BELOW the
  audit's predicted 2–4** — so every options *t* shrinks by ~1.36×, and **no verdict changes.**
  * **R3.3 is the one that mattered:** the paired sign test and paired *t* the entire options
    conclusion rested on existed in NO shipped file. They now reproduce the record exactly
    (441 of 1,052 cells, z −5.185 against the recorded −5.24; seed-0 paired t −2.6701 against
    −2.67), pinned by a test.
  * **A RAW DESIGN EFFECT IS NOT EVIDENCE OF CLUSTERING.** Found by a failing test: 600
    independent draws in 12 blocks of 50 report a design effect near 1.8 — pure sampling error
    in MSB/MSW, since that ratio is F(k−1, n−k). Applying it as a haircut would manufacture a
    correction out of noise. The design effect is now scored against its own shuffled null (the
    X7 method) and `clustering_measurable` gates it; the real book passes clearly (1.848 vs null
    p95 1.266). **Never quote a design effect without its null.**
- **POINT-IN-TIME LIQUIDITY RAISES THE OPTIONS HEADLINE — the audit expected it to fall
  (2026-08-05, audit O20).** Applying the miner's own screen at each entry date instead of to the
  name's first cached year: **PIT-liquid 3,359 trades at +4.82% vs PIT-illiquid 495 at −7.84%**,
  coverage 99.2%. **But it does NOT rescue the signal** — the control is screened by the same
  rule and benefits too, so on the liquid subset the real book loses to random entry MORE
  decisively (z −3.475, p 0.0005). The headline stays the whole book at aggression 1.0.
  **The audit's premise is half wrong and this is the correction:** names were ranked into the
  mining pool by TODAY's market cap (true), but the liquidity screen was already applied to the
  FIRST CACHED YEAR, not to a present-day chain (`mine_options_cache.py:160`). So O20 is an
  UPPER BOUND on the repair — names that would have failed in 2016 were never mined and no
  evaluation-time filter recovers them.
  **THE PATTERN WORTH KEEPING:** this is the third time in two sessions (R10, then O20) that a
  bias the record assumed ran in the strategy's favour ran the other way. **This project's
  expectations about the direction of its own biases have been wrong more often than right.
  Measure them; do not reason about them.**
- **THE EDGE DOES NOT CLEAR THE DEFLATED SHARPE BAR (2026-08-05, audit M1). The last bar the
  project claimed to clear fails once the denominator is honest.** Every multiple-testing claim
  was computed against `N = 8` — the eight weight schemes. `RESEARCH_LOG.md` is now populated and
  `valuation/edge/research_log.py` feeds the real count into `_deflated_sharpe` and
  `_trials_haircut`. Measured trial counts: **equity 84, options 139, infra 1, total 224** (session 5 added 4 options rows)
  (against the audit's ~146 estimate; 15 `FIXED` correctness rows correctly do NOT count).

  | | N = 8 (as shipped) | **N = 84 (measured)** |
  |---|---|---|
  | Deflated Sharpe | 0.9970 | **0.8997** — FAILS the >0.95 bar |
  | `sr0_benchmark` | 0.242 | **0.406** |
  | `metric` self-report | `probabilistic_sharpe_ratio_UNDEFLATED` | **`deflated_sharpe_ratio`** |
  | `_trials_haircut` | 2.04 | **2.977** |

  **There is a real win inside the failure: audit B9 is RESOLVED by measurement.** B9 argued the
  statistic was an undeflated PSR because `sr0` collapsed. With a real `N` it does not collapse —
  `sr0` rises to 0.406 against a per-period Sharpe of 0.550, deflating away 74% of it, and the
  statistic self-reports as a genuine Deflated Sharpe **for the first time**. The price of fixing
  it is that the bar is no longer cleared. That trade was pre-committed before the run.
  Also: **√(2·ln 84) = 2.977**, i.e. the multiple-testing haircut at the real `N` lands within
  0.03 of the Harvey–Liu–Zhu hurdle of 3.0 — exactly as the audit predicted.
  **`N` is domain-scoped** (the equity composite is charged the 84 equity trials, not the 218
  project-wide ones — the options autopsy is a different search for a different product), and a
  missing log degrades to `N = 8`, i.e. to the OLD behaviour, never to an unpenalised one.
- **THE HEADLINE NOW HAS A t, AND THE LONG-SHORT t IS 2.620 NOT 2.836 (2026-08-05, audit R9).**
  `top_decile_alpha` — the number on the front of the product — shipped with **no significance
  statistic of any kind**. It now carries **t +4.517, HAC t +4.376, hit rate 71.0%**. The
  long-short's naive i.i.d. t is joined by **HAC t +2.620** and a Ljung–Box diagnostic.
  **Ljung–Box rejects independence at p = 0.036** (lag-1 autocorrelation +0.189), so per the
  pre-commitment **the Newey–West t is now the number this project quotes** and the naive t is a
  diagnostic only. The 63d windows genuinely do not overlap — that dimension was fine — but
  factor spreads are autocorrelated and nothing anywhere measured it. Note the long-ONLY object
  is far better measured (t 4.38) than the long-short the project has always led with.
  Comparing 2.620 to X7's calibrated floor of 2.14 is **apples-to-oranges**: that floor was
  measured on the NAIVE t across 100 placebo draws. Re-deriving it on the HAC statistic is open.
- **THE UNINVESTABLE BENCHMARK WAS THE HARDEST ONE — the expectation was WRONG in the strategy's
  favour (2026-08-05, audit R10).** Alpha had only ever been measured against an equal-weighted
  average of every name in the panel, charged zero trading cost while the strategy pays. Both the
  audit and this session's own pre-commitment predicted that flattered the product. It does not:

  | benchmark | benchmark /yr | top-decile EXCESS /yr | HAC t |
  |---|---|---|---|
  | equal-weight universe (incumbent, cost-free) | +18.14% | **+7.17%** | +4.376 |
  | equal-weight, charged the strategy's own costs | +16.10% | +9.21% | +5.685 |
  | cap-weighted panel average | +14.85% | +10.46% | +4.292 |
  | **SPY total return** | +15.32% | **+9.99%** | +3.770 |

  Over 2009-01 → 2026-01 the equal-weighted panel returned **+18.14%/yr vs SPY's +15.32%** — a
  ~1,500-name equal-weighted book beat the cap-weighted index over a window starting at the
  post-GFC bottom. So the incumbent benchmark is uninvestable in the direction of being **too
  demanding**. **Keep publishing +7.17% as the headline** — it is the most conservative and the
  one every historical figure used, so changing it would break comparability for a number that
  only moves the flattering way. The edge now also survives an INVESTABLE benchmark: +9.99% over
  SPY (HAC t 3.77). Charging the equal-weight book the strategy's own cost table costs it
  2.04pp/yr, a genuine thumb on the scale that had sat in the strategy's favour and is now gone.
  All four ship in the `benchmarks` block on every run.
- **CPCV WEIGHT ADOPTION MANUFACTURES ~+1.4 OF LONG-SHORT t OUT OF NOTHING (X7, post-hoc —
  treat as a strong hypothesis, not a settled result).** Splitting the 100 placebo draws on
  whether CPCV adopted: when it did NOT (73 draws) mean long-short t is **−0.065** (se 0.119),
  a textbook null; when it DID (27 draws) mean t is **+1.343** (se 0.184) and mean alpha
  +0.82pp. It fires on **27% of pure-noise draws**. Mechanism: the adopted weights are chosen
  on the same panel the headline is then measured on. **The shipped strategy is UNAFFECTED —
  it does not adopt, it keeps `current-default`** — which is measured support for the existing
  rule that a CPCV rejection means keep the defaults. But any future run that DOES adopt a
  CPCV scheme has an optimistically biased headline unless measurement moves off the
  selection panel. Not pre-registered; wants a pre-registered replication.
- **CORRECTED 2026-08-03 (audit B9) — TWO OF THE THREE "statistical bars" MEASURE SOMETHING
  NARROWER THAN THE CLAIM THEY SUPPORT. Lead with the long-short t of 3.52 against the
  Harvey–Liu–Zhu hurdle of 3.0. That one is real.** The other two:
  * **The Deflated Sharpe IS deflating — the audit's mechanism for this one is REFUTED by
    measurement, and only half of its criticism survives.** The audit argued that the eight
    weight schemes are indistinguishable (out-of-sample median ICs spanning +0.061 to +0.062),
    so the cross-trial VARIANCE of Sharpes is ~0, `SR₀ ≈ 0`, and the statistic degenerates to
    Φ(SR·√(n−1)). **Measured on the full-universe run: `var_sr_across_trials` = 0.0276 (sd
    0.166, not ~0) and `sr0_benchmark` = 0.242 against a per-period Sharpe of 0.606** — the
    benchmark is deflating away 40% of the Sharpe. The audit inferred near-identical trial
    SHARPES from near-identical median ICs; those are different quantities, and the Sharpes are
    genuinely dispersed. It saturates because a per-period Sharpe of 0.61 over 110 periods is
    a large z, not because nothing is deflated. Every run now ships
    `deflated_sharpe_detail` (`sr0_benchmark`, `var_sr_across_trials`, `n_trials`) plus a
    `metric` field that reads `probabilistic_sharpe_ratio_UNDEFLATED` **if** `sr0` ever does
    collapse — so this is now a measured property of each run rather than an assumption in
    either direction.
  * **What DOES survive: `N = 8` is not the number of trials this project has run.** The
    ledger records of the order of 146 pre-registered tests. That criticism is untouched by
    the above and is the real one. Until a genuine trial counter exists (audit M1,
    `RESEARCH_LOG.md`, started but deliberately not wired), the deflated figure is computed
    against a denominator that is roughly 18x too small.
  * **PBO 6.7% scores the WEIGHT-SCHEME SELECTION STEP ONLY** — "the best of eight nearly
    identical weightings generalises". It says nothing about the ~146 signal-inclusion,
    theme-membership, universe, standardisation and construction decisions in the ledger, and
    the shipped strategy keeps `current-default` anyway, so the selection being scored is one
    the model never makes. Now shipped as `pbo_scope`.
  * The honest version of both needs a real trial counter (audit M1, the append-only research
    log). **Not done.** At N ≈ 100+, √(2·ln N) ≈ 3.0 — about the Harvey–Liu–Zhu hurdle.
- **CORRECTED 2026-08-03 (audit B8) — `low_risk` was NOT "confirmed out-of-sample". It passed a
  BOTH-HALVES STABILITY TEST.** `holdout_theme_validate`'s docstring describes a clean protocol
  — flag a theme on one half using a pre-specified rule, then measure the effect of removing it
  ONLY on the other half. **Verified in the code: `rule_fired` is computed at
  `fundamental_panel.py:3048` and never read.** The verdict is `all(improves)` across both split
  directions, which is a demanding test and a legitimate one — but it is a stability check on the
  full sample, not an out-of-sample confirmation, and `low_risk` reads `confirmed` while
  `rule_fired = false` in one direction, which is only possible because the flag is ignored.
  The measured numbers below are unchanged and still stand; the word "CONFIRMED" was the
  overstatement. Fixing the function (implement the rule, or rename it and its verdict labels)
  is audit item **B8** and is NOT yet done.
- **SUPERSEDED 2026-08-04 (audit session 2, B6) — EVERY NUMBER IN THE NEXT TWO BULLETS WAS
  MEASURED ON A PANEL WHOSE FIRST THIRD HAD AN INVERTED UNIVERSE. The corrected numbers are
  WORSE and TWO OF THE THREE BARS NOW FAIL. Read the "CORRECTED PANEL" bullet below first;
  the two bullets that follow are kept only as the record of what the defect was producing.**
- **CURRENT FULL-UNIVERSE NUMBERS (2026-08-04, after the audit's Part I corrections):
  long-short t 3.884, top-decile alpha +11.78%, monotonicity −0.988, PBO 13.3%.** Measured
  against a clean pre-audit baseline re-run on identical data (t 3.520, alpha +11.88%,
  monotonicity −0.952, PBO 6.7%): the composite sorts BETTER, top-decile alpha is a rounding
  change, PBO doubles off a low base. The equal-weight benchmark did not move (+16.55% in every
  run), which is the control. **Thirteen corrections and NOT ONE held-out verdict changed** —
  the record's decisions were not resting on the defects, and the defects were not hiding a
  different model. The sanity layer's flag count fell 5 → 2 (the three negative-multiple sign
  flags cleared). Full A/B in `HANDOFF_edge_audit.md` Part 2.
- **The edge clears PBO 13.3% (want <50%), long-short t 3.851 (want >2), top-decile alpha
  +11.69%.** The single biggest driver was zeroing `low_risk`, which passed the both-halves test
  described above (decide on one half, measure on the other, both directions). On the
  pre-registered direction the rule fires on the early half (median IC −0.0308) and, measured
  on the later half, **long-short t goes 0.97 → 2.56 and top-decile alpha +6.09% → +9.30%**; the
  reverse direction agrees more strongly (t 0.55 → 2.57, alpha +6.63% → +14.49%). Do not treat
  the edge as settled — caveats at the end.
- **CORRECTED PANEL, 2026-08-04 (audit session 2, B6+B7+B13) — THESE ARE THE LIVE NUMBERS.
  Long-short t 2.836, top-decile alpha +7.17%, monotonicity −0.891, PBO 73.3%, over 69
  rebalance dates on a genuine 18.5-year window (2008-01-16 → 2026-07-24).** The equal-weight
  benchmark moved +16.55% → +18.14%, which is the control and confirms the universe itself
  changed. **CORRECTED 2026-08-05 (audit session 3, X2+X7) — THE "TWO OF THREE BARS FAIL"
  READING WAS WRONG, IN BOTH DIRECTIONS, AND BOTH ERRORS CAME FROM UNCALIBRATED BARS MEASURED
  ON ONE ARBITRARY GRID.** It used to say: "t 2.836 is BELOW the Harvey–Liu–Zhu hurdle of 3.0
  it used to clear, and PBO 73.3% is far above the <50% bar." Both halves are now retired:
  * **t 2.836 vs the 3.0 hurdle is a GRID ARTEFACT.** X2 re-ran the whole backtest on seven
    equally valid rebalance grids (offsets 0/5/10/20/30/40/50 trading days; the grid always
    started at a hard-coded TD=252 and 62 other grids existed that nobody had ever looked at).
    All seven keep 69 dates over the identical window. **Long-short t ranges 2.703 → 3.517,
    median 2.926, and CLEARS 3.0 on three of the seven.** Quote **"t 2.7–3.5 depending on
    grid, straddling the hurdle"** — never one side of 3.0 as a fact.
  * **PBO <50% IS NOT A BAR AT ALL.** X7's placebo puts the MEDIAN PBO on a definitionally
    worthless signal at **46.7%**, i.e. the "<50%" bar sits exactly at the noise level and has
    almost no power. Calibrated bar is the placebo 5th percentile, **19.7%**. PBO is
    uninformative here in either direction — do not cite it as a pass or a fail.
  * **Top-decile alpha is the one headline that PASSED its robustness test:** spread across
    the seven grids is only **1.30pp** (median **+7.52%**, range +6.84% to +8.14%), against an
    equal-weight benchmark that itself moved 2.08pp across the same grids. The signal-driven
    number is steadier than the market-driven one it is measured against.
  Only the Deflated Sharpe still passes as originally stated — and X7 now DEFENDS it
  (see the calibrated-thresholds bullet below); per B9 the surviving criticism of it is the
  trial denominator, not the statistic.
  **ATTRIBUTED, one change per run, on the full universe — B6 IS ESSENTIALLY THE WHOLE DROP:**
  reverting B6 alone (B7+B13 still fixed) restores t 3.733, alpha +11.36%, PBO 26.7% at 110
  dates, so **B6 costs t −0.897, alpha −4.18pp and PBO +46.7pp — 100% of the PBO blow-out, 88%
  of the t drop, 89% of the alpha drop.** **B7 alone is NULL on the headline** (t −0.010, alpha
  +0.01pp, PBO and equal-weight unchanged to the digit) — a correctness fix with no performance
  consequence, which is the ideal outcome for one. **B13 alone is small and points both ways**
  (t +0.122, alpha −0.51pp, EW −0.24pp): dropping 384 penny names helps the long-short and costs
  the long-only book, consistent with penny names contributing at both ends of the ranking.
  **What this means: roughly 40% of the top-decile alpha was coming from the 41 early rebalance
  dates at which every name present was one that had already stopped trading.** State it as a
  hypothesis, not a finding — a repair's effect on a fitted statistic is not evidence about the
  repair. Costs still clear comfortably: breakeven 134 bps one-way against a **measured** 33.4
  bps realised (B11 — the old "37 bps" was an assumption quoted as a measurement). **No shipped
  decision changed:** `low_risk` still `confirmed` in both split directions, `insider` still
  `rejected`. Full three-way A/B in `HANDOFF_edge_audit.md` Part 3.
- **R1 RE-RUN, DONE 2026-08-05 (audit session 4) — THE THRESHOLD IS CLEARED AGAIN ON THE
  CORRECTED PANEL, AT A LOWER LEVEL AND WITH A DIFFERENT MECHANISM. CLAIM A STILL APPLIES.**
  The pre-commitment in `HANDOFF_r1.md` section 1 was honoured unchanged ("alpha" only if the
  FF5+MOM intercept is positive with NW t > 2.0; ambiguous is a NULL). Re-run on the corrected
  69-date panel → **68 non-overlapping 63d windows, 2009-01-15 → 2025-10-27**, deployed flat
  1/7 weights, NW lag 1. Alignment check passes (SPY on MKT: beta 0.933, R² 0.988).
  * **FF5+MOM alpha +6.99%/yr, NW t +3.984, R² 0.308** on the primary object (`top − ew`).
    **ALL SIX pre-registered specs are positive with t > 2.0** — compound/sum × full/first
    half/second half, spanning **+5.08% to +10.85%**. No disagreement, so the pre-registered
    NULL veto is not triggered. **QUOTE +6.99%/yr (range +5.1% to +10.9%)**; the conservative
    single number is the first half's +5.19%.
  * **THE OLD +8.81%/yr AND THE +6.6%–8.8% RANGE ARE VOID. Do not quote them anywhere.**
  * **THE MECHANISM REVERSED ON TWO OF ITS THREE LEGS — this is the part to re-read.** Now
    loading: **HML +0.251 (t +2.93)** and **UMD +0.205 (t +3.65)**. NOT loading: **SMB +0.208
    (t +1.39)** and **RMW +0.092 (t +0.90)**, both of which loaded strongly in the void run
    (SMB t 3.84, RMW t 4.49). So the old story — "`size`, `quality`, `momentum` ARE the
    standard premia; `value` and `capital_discipline` are not what FF measures" — is
    **backwards on size and profitability** and must not be repeated. Current honest reading:
    momentum is a genuine standard-premium exposure, the book now carries a real VALUE tilt,
    and the size/profitability exposures that dominated the old story were largely an artefact
    of the inverted-universe window B6 removed. R² fell 0.465 → 0.308 — the factor models
    explain LESS of this series than of the void one.
  * The unhedged small-cap tilt caveat WEAKENS for the spread (SMB +0.208, t 1.39, vs +0.885
    before) but SURVIVES for the long-only book (SMB +0.691, t 3.89).
  * Other objects: long-only book in excess of RF **+9.33%/yr (t 4.97)**; long-short
    **+14.86%/yr (t 4.18)**; the equal-weight universe's own unexplained excess +2.34% (t 2.92).
  * **CAVEAT THAT MUST TRAVEL: the secondary q-factor model does NOT clear on the first half**
    (q4 +3.17%, t 1.712; q5 +1.56%, t 0.702), though it clears on the full sample (+6.72%,
    t 3.19) and the second half (+11.49%, t 3.84). The pre-registered threshold is stated on
    FF5+MOM so this does not veto, but the early-period result is model-dependent.
  * Against X7's floor: raw top-decile alpha +7.13% is far outside the placebo null
    [−1.33pp, +2.38pp], so R1 is decomposing something real. **X7 does NOT calibrate a
    factor-regression intercept** — no placebo floor exists for R1's own t, and none was
    invented. Still ONE panel; **X8's international replication is the out-of-sample evidence,
    R1 is not.** Full entry: `HANDOFF_edge_audit.md` Part 5.
- **SUPERSEDED 2026-08-05 by the R1 RE-RUN above. Every number in the next bullet was measured
  on the pre-B6/B7 panel over a window that no longer exists, with a composite no shipped code
  path uses. Kept only as the record of what was claimed. DO NOT QUOTE IT.**
- **SETTLED 2026-08-04 (audit R1) — THE HEADLINE IS NOT MERELY FACTOR EXPOSURE. The word
  "alpha" is now permitted, as a RANGE and with caveats.** `top_decile_alpha` is still
  `4 × (mean top-decile 63d return − mean equal-weighted universe 63d return)` with no risk
  adjustment in it, but that object has now been regressed on the factors it was suspected of
  merely re-assembling. On the full 2,710-name universe, 109 non-overlapping 63-trading-day
  windows (1998-12-31 → 2026-01-21), deployed flat 1/7 weights: **FF5+MOM alpha +8.81%/yr,
  Newey–West(1) t +5.742, R² 0.465**; Hou–Xue–Zhang **q4 +9.14% (t +5.23)**, q5 +8.33%
  (t +4.37); long-short **+12.12% (t +4.14)**. Raw was +12.13%, so **the factor models absorb
  about 27% of the headline and leave the rest** — the opposite of the pre-registered
  expectation. It passes all four pre-registered specs (compound/sum × full/ex-B6), every
  subperiod, every NW lag 0–8, **net of costs (+7.85%, t 5.16)**, and a spanning test adding the
  EW universe's own excess return (+8.25%, t 5.88; universe loading t 0.63, insignificant).
  **QUOTE THE RANGE +6.6% to +8.8%/yr** — +6.6% (t 4.41) is the value after dropping the 37
  B6-contaminated early dates, and is the right single number when only one is wanted.
  **Mechanism:** SMB +0.39 (t 3.84), RMW +0.30 (t 4.49), UMD +0.18 (t 3.49) all load — `size`,
  `quality`, `momentum` ARE the standard premia — but **HML (t 1.08) and CMA (t 1.08) do not**,
  so `value` (six ratios, EV re-priced at the rebalance date) and `capital_discipline`
  (issuance/accruals) are not what FF measures. Not a benchmark artifact: alpha is linear, so
  α(top−ew) = 14.60 − 5.80 = 8.81 exactly and the +5.80% (t 5.41) that FF5+MOM fails to explain
  about the EW universe itself **cancels out of the spread**. **CAVEATS THAT MUST TRAVEL WITH
  IT:** it is still ONE panel — a regression is a control, not new data, and **X8's international
  replication is the out-of-sample evidence, R1 is not**; **t 5.74 is NOT multiplicity-corrected**
  (audit M1 still open), though the deployed weights are flat 1/7 and were never tuned; FF5+MOM
  is a poor description of this universe so read loadings as approximate; the book carries an
  unhedged SMB +0.885 small-cap tilt with borrow/impact/capacity unmodelled; and the benchmark
  is still uninvestable (audit R10). Reconciles with X4 rather than contradicting it — over X4's
  own 2014+ window R1 gets +6.06% (t 3.16) where X4 got t 1.10, because X4 differences two
  high-variance total-return series (low power) while R1 removes that variance first (high
  power). Full write-up and the pre-commitment (written before any number) in `HANDOFF_r1.md`;
  reproduce with `python -m scripts.factor_alpha`, pinned by `tests/test_factor_alpha.py`.
- **R1 FRAGILITY (2026-08-04, same lane) — the result SURVIVED a deliberate attempt to break it,
  but it is WINDOW-DEPENDENT and has a WEAK DECADE, and it is PROVISIONAL until re-run.** Four
  criteria were committed before any cut ran; all four passed. **(1) Stable-universe window
  (≥2008, the closest available preview of what B6 will do): alpha +6.24%, t +3.986, n 73 —
  DOWN 2.57pp, about 29% of the alpha.** The discarded early period is where the raw spread is
  biggest (first third raw +21.89%/yr vs +3.53% and +11.02%), exactly the inverted-universe
  signature. **Expect the post-B6 headline near +6%, not +8.8% — quote ~+6% when one number is
  wanted.** (2) No sign flip: halves +8.98% (t 3.38) / +5.48% (t 3.12); thirds +13.51 (t 3.59) /
  **+4.33 (t 2.412, the weakest cell in the study)** / +8.10 (t 3.82). (3) **Not concentrated:**
  the best 5 of 109 periods carry 23.0% of the alpha (38.0% on the stable window, the criterion
  that came closest to tripping); dropping the best 5 leaves +7.28% (t 5.19), dropping the worst
  5 gives +10.07% — nearly symmetric, and the best 5 are spread across four regimes. (4) **Not
  specification-dependent:** CAPM +12.99%, FF3 +12.28%, FF5-no-MOM +10.03%, FF5+MOM +8.81%,
  q4 +9.14%, q5 +8.33% — all t > 2 on BOTH windows, and **FF5+MOM is nearly the most conservative
  of the six**, so the headline is quoted from the most demanding pre-registered model, not the
  most flattering. **THE ONE THING THAT LOOKS BAD: a ~10-year rolling window centred on 2009-2019
  shows alpha of only +1.66% (t 1.39).** Alpha is positive in 70 of 70 rolling windows and never
  reverses, but 8 of 70 are not significant — the full-sample t 5.742 averages a weak decade in
  with strong ones. Windows confirmed **genuinely non-overlapping** (all exactly 63 factor days,
  zero shared days), so no inference correction is needed. **BINDING: R1 MUST be re-run after B6
  and B7 land** — B6 is expected to lower alpha to +5.5-7.0%; B7's direction is unknown; a
  post-re-run alpha < +4%/yr or full-sample t ≤ 3.0 is a MATERIAL REVISION that requires
  rewriting the headline, and a stable-window t ≤ 2.0 withdraws the word "alpha" entirely. Full
  contract and every cut in `HANDOFF_r1.md` §6-8; reproduce with
  `python -m scripts.factor_alpha_fragility`, pinned by `tests/test_factor_alpha_fragility.py`.
- **Zeroing `insider` was tested the same way and REJECTED — it stays at 0.125.** It helped one
  split direction by a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample
  t-stat is not a stable property. Same reasoning as `low_risk`, opposite outcome — which is
  why every theme change now has to clear `holdout_theme_validate()` before it ships.
- **CORRECTED — "the entire edge is the institutional (13F) theme" is OBSOLETE.** Strip the
  institutional theme now and top-decile alpha is still **+10.6%** with long-short t **2.86**
  (it used to collapse to 0.71). That finding was an artifact of `quality` and `low_risk`
  running on half their inputs. 13F is a contributor, not the whole edge.
- **CORRECTED — `monotonicity`'s SIGN WAS BEING READ BACKWARDS everywhere.** Deciles are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal) and +1.0 = backwards.**
  The old bullet "monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
  cleanly ordered" said the opposite of the truth: −0.68 meant they *were* well ordered.
  Current value −0.939. Pinned by `test_monotonicity_sign_convention`.
- **CORRECTED — `low_risk` does NOT have pooled IC −0.048.** With both its inputs finally
  populated it is **−0.0014 (t +0.71)** on the full universe: indistinguishable from zero.
  It was dead weight, not actively harmful. It is **−0.352 correlated with `size`** — the
  strongest anticorrelation in the theme matrix — so it was cancelling the small-cap tilt,
  which is why removing it helped so much despite having no signal of its own.
- **CORRECTED — `institutional` coverage is 61.4%**, not the 81.7% previously recorded (that
  came from a smaller universe). It is still empty before 2013-06-30, so any early-period
  comparison involving it is uninformative rather than negative.
- **Theme ICs (full universe, CURRENT 2026-08-04):** quality +3.57, momentum +2.62,
  capital_discipline +2.25, institutional +1.81, size +1.68, value +1.52, growth +1.45,
  low_risk +0.71, **insider −0.43**, sentiment empty.
- **A FULL BACKTEST IS NOT REPRODUCIBLE RUN TO RUN, AND THE INSIDER THEME IS WHERE IT SHOWS.
  Found 2026-08-04; unexplained; do not build on any single run's insider number.** Three
  full-universe runs on identical data gave `insider` median IC **−0.00335 (t −0.34)**,
  **+0.01551 (t +2.69)** and **−0.00339 (t −0.43)** at unchanged 85.0% coverage. The first and
  third bracket the second and agree to four decimals, so the middle run is the anomaly and
  **audit B26 (the same-day-filing exclusion) is NOT the cause** — an earlier note in this file
  said it was, and that was wrong. B26's effect was measured directly on 22,975 (ticker, date)
  score pairs: it alters **3.96% of scores at a level correlation of 0.9975**, consistent with
  the ~0 IC change between the runs that bracket it. Every other theme is stable to ±0.01 across
  all three runs. **What this means: `insider`'s IC sits so close to zero that its t-statistic is
  not a measurable quantity**, which is exactly why zeroing it came back `not_replicated`
  (Δt +0.08 one direction, −0.09 the other). It is also a reproducibility problem in its own
  right — a project whose memory is its results files needs its results files to be
  deterministic. **Next session: find the nondeterminism before trusting any marginal IC.**
  Audit item **S3** (the `+min(10, 2·buys)` bonus is unconditionally additive; `tanh(net/5e6)`
  saturates regardless of company size) is the thread that might make this theme measurable.
- **Historical note:** `insider` is the only negative theme, and still carries 12.5% weight — but
  zeroing it **did NOT replicate** out-of-sample, so it was deliberately left alone.
- **Theme ICs are NOT stable across time.** `low_risk` flips −0.031 → +0.041 between halves and
  `size` flips t +3.17 → −0.67 (the small-cap premium worked pre-2012, not after). Treat any
  single-period theme IC as weak evidence; the held-out split is what settles a decision.
- **13F is NOT a look-ahead artifact (settled July 2026, 800 names).** Feeding it *fresher,
  not-yet-filed* data at a 15d lag makes it WEAKER, not stronger (t 1.49 -> 0.66, Deflated
  Sharpe 84% -> 44%) — the opposite of the artifact signature. The panel's effective lag is
  already ~111 days (an April rebalance uses the December quarter, public since mid-February),
  i.e. more conservative than the 45d deadline. Its decay curve is sensible: peaks at Q-1,
  alive at Q-2 (t 1.36), dead by Q-3 (t -0.04).
- Edge is strongest in **large caps** (regime IC highest there).
- **P6: THE EDGE SURVIVES TRADING COSTS.** Top-decile breakeven is **236 bps one-way** against
  a **37 bps** actual cost profile (~6.4x margin); net alpha **+11.41%/yr** after costs on 249%
  annual turnover. The short side does not break it either — the BOTTOM decile is *larger*-cap
  than the top ($4.50B vs $1.95B median, 29.8 vs 37 bps), so the long-short t does not rest on
  unborrowable micro-caps. Borrow cost is not modelled (affects the long-short statistic, not
  the long-only book). Quote the BREAKEVEN, not the net alpha — it needs no belief in any
  particular cost calibration. Measured on every run now (`costs` block).
- **P6: three plausible refinements were tested and ALL THREE REJECTED.** Do not re-open them
  without a new reason: **(a) TTM ROE/ROIC is WORSE than quarterly** (roe t +2.84 vs +2.01,
  roic +3.38 vs +2.57) — recency beats smoothing, and the earlier note calling quarterly a
  "wart" was wrong; **(b) median/MAD robust z-scores HALVE the long-short t** (3.485 -> 1.721);
  **(c) consolidating momentum+institutional loses** (LS t 3.48 -> 2.53) — +0.50 correlated but
  complementary, both earn a full weight.
- **P6 lesson worth keeping: a signal's IC can be flat while the composite built from it moves
  a lot.** Robust z-scores left every theme IC essentially unchanged (quality +3.39 -> +3.35)
  while halving the long-short t. Rank-IC is INVARIANT to a monotone rescaling; the composite
  is a weighted SUM of z-scores and is very much scale-sensitive. **Never judge a
  standardization or scaling change by per-signal IC.**
- **CORRECTED — `sector_neutral` WAS silently inert; it is now wired, TESTED, and REJECTED.**
  The old text ("no sector column anywhere on disk ... BLOCKED until TICKERS is downloaded") is
  obsolete: TICKERS was downloaded in P10 and the panel populates `metrics["sector"]` from it.
  Sector coverage is **100.0% of panel rows** (2,710/2,710 names, 11 sectors), so the toggle
  genuinely changes every z-scored theme instead of grouping on a constant. It was then measured
  on the full universe and **rejected in both held-out directions, twice** (P10, and an
  independent re-run 2026-08-02 on a panel that had since gained several signals). Under the
  DEPLOYED weights it raises long-short t 3.396 → 3.896 but COSTS top-decile alpha
  +11.82% → +10.24%, worsens monotonicity −0.952 → −0.915 and nearly doubles PBO 26.7% → 46.7%;
  the later half is worse on both metrics. `sector_neutral` stays **OFF**. Full numbers in
  `HANDOFF_sector_neutral.md`; wiring pinned by `tests/test_sector_neutral.py` so it cannot
  silently go inert again. TICKERS gives TODAY's classification, so applying it to 1998 rows is
  a mild look-ahead — the one non-point-in-time input in the panel, which is a reason to be MORE
  sceptical of a positive sector result, not less. It rejected anyway, so nothing rests on it.
- **P7: THE VALUE THEME WAS CURRENCY-CORRUPTED and is now fixed.** `marketcap`/`ev` are USD but
  the raw line items are in the REPORTING currency, so every value ratio was wrong for the 4.1%
  of rows that report abroad — SK Telecom's `book_to_price` computed to **892 vs a true 0.589**.
  All six value inputs improved after the fix (**value theme t +1.34 → +1.46**), **PBO halved
  13.3% → 6.7%**, monotonicity −0.939 → −0.952, top-decile alpha +11.77% → +11.82%. Foreign
  over-representation in the top decile went **1.35x → 0.56x**; in the live book, foreign names
  fell from 21 of 86 positions (28.3% of weight) to 11 (10.7%).
- **`fxusd` IS A DIVISOR, NOT A MULTIPLIER** — local units per USD (SKM 1514.2 won/USD). Using
  it as a multiplier squares the error. There is **no `netincusd`** column; use `netinccmnusd`.
  `total_equity` must stay LOCAL — `gp_on_capital` divides local gross profit by it.
- **ENTERPRISE VALUE IS NOW PRICED AT THE REBALANCE DATE (2026-08-03, shipped ON).** Sharadar's
  `ev` embeds the FILING-date market cap, so `ebit_ev`/`ev_sales`/`ev_ebitda` measured cheapness
  against a ~111-day-old quote while `earnings_yield`/`fcf_yield`/`book_to_price` used the fresh
  one. `_pit_ev()` re-prices the EQUITY leg to the PIT market cap and holds the DEBT leg at its
  last filed value (net debt is only observable at a filing — that IS point-in-time). Net debt
  must be **currency-converted before it is added** — P7 in a second costume. Re-pricing moves EV
  a **median 5.1%** (26.7% of rows >10%), and `neg_ev_sales` median IC goes **+0.0214 → +0.0363**.
  The BOOK is a wash (LS t 3.396 → 3.520, alpha +11.82% → +11.88%, PBO/monotonicity unchanged,
  net top-decile alpha slightly worse) — **it ships on correctness, not performance.** Stale, not
  look-ahead, so no past result is invalidated upward. New **`ev_freshness`** block (100.0% fresh)
  makes a silent revert loud; `EDGE_EV_POINT_IN_TIME=false` reverts. `HANDOFF_ev_fix.md`.
  STILL OPEN: negative EV (net cash > market cap, 0.70% of rows) is read as maximally cheap by
  `neg_ev_sales` and as expensive by `ebit_ev` — a live sign inconsistency, deliberately not
  bundled into this change.
- **P8: a SANITY layer now runs every backtest** (`sanity_check` block): range / subgroup-pegging
  / market-cap divergence. Coverage says a factor is PRESENT, this says it is SANE — the
  currency bug filled every column and coverage was blind to it. Verified it WOULD have caught
  P7 (foreign names sat at the 86th percentile of book_to_price and earnings_yield pre-fix).
  It legitimately fires twice on corrected data (foreign names really are large caps; 1.45% of
  rows have a >3x market-cap divergence, AIV 71x / EQC 53x). **Do not silence a flag to make the
  run green** — investigate it or record why it is expected.
- **CODE_AUDIT.md's M2 (SanDisk/WDC ~10x) does NOT reproduce.** DAILY cap and shares x price
  agree to 1.6x, the share count is plausible, and the price ran 29.6x over 17 months with zero
  discontinuities (WDC 10.3x, MU 8.5x — the whole storage complex). If it is wrong the error is
  upstream in the PRICE, which both estimates share. Unresolved, not fixed.
- **Standing caveats, do not drop them:** Deflated Sharpe is a *saturated* 0.9999991 and, per
  the B9 correction at the top of this section, it is an **undeflated PSR** — not a proof of
  anything. Both halves of the held-out test come from the same panel and universe, the test is
  a **both-halves stability check rather than an out-of-sample confirmation** (B8), and the
  size-cancellation mechanism was hypothesised on the full sample — so neither the decision nor
  the hypothesis generation is out-of-sample in the strict sense. The concentrated top-25 book
  is the noisiest number in the file, and per audit **B17** it holds up to FIFTY names (it sells
  only below `exit_rank = top_n × 2`) and pays neither costs nor taxes, unlike every other book
  in the results file — so it is also mislabelled. Weight-tuning itself remains noise-chasing:
  CPCV still adopts no weighting over the defaults.
- **FIXED 2026-08-04 (audit session 2). The panel is now a genuine 18.5-year window,
  2008-01-16 → 2026-07-24, 69 rebalance dates, cross-sections 1,471–1,954.** `days=None` means
  the whole series and the shared calendar is cut ONCE, before the ffill. Each run ships
  `panel_window` (available vs retained range, the cut, per-date cross-section sizes) so the
  two-blocks-disagree-about-their-window failure cannot recur silently. **41 of the 110 dates
  were dropped and the headline fell with them — see the CORRECTED PANEL bullet above; this was
  the most expensive correction in the audit.** The description below is what the defect WAS:
- **The panel is 27 YEARS long, not 18, and its first third has an INVERTED universe (audit
  B6, FIXED — see above).** `WRDSProvider.price_history` truncates with `.tail(4659)`, so each
  ticker keeps its OWN last 18.5 years and the calendar is the union: 1998-12-31 → 2026-04-22,
  110 rebalance dates over 27.3 years. At a 2001 cross-section every name present is one that
  stopped trading by roughly 2019 — the inverse of classic survivorship bias, and it makes
  roughly the first 37 of 110 periods uninterpretable. Those same 37 dates have no benchmark,
  which is why `construction.n_periods` reads 110 while `portfolio.n_periods` reads 73 in the
  same JSON over undisclosed windows. Direction of the bias is genuinely unclear.
- **FIXED 2026-08-04 (audit session 2, B7/G). There is now ONE composite**, used by selection,
  measurement and live, and it renormalises by the present-weight mass — the convention
  SELECTION already used, so the deployed weights were chosen under it. `CONFIG.sector_neutral`
  and `CONFIG.residual_momentum` now default **false**. **Live and backtest score identically**
  (max abs difference 0.0), pinned by
  `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`. Measured effect on the
  headline: **NULL** (t −0.010, alpha +0.01pp) — the disagreement was real in mechanism but
  small in magnitude on this panel. The description below is what the defect WAS:
- **The LIVE product does not score names the way the backtest does (audit B7/G, FIXED — see
  above).** `screen.py:256` calls `build_frame(metrics)` with no keyword arguments, inheriting
  `CONFIG.sector_neutral` (default **true**) and `CONFIG.residual_momentum` (default **true**),
  while the backtest forces both `False`. Sector-neutral ranking was tested on the full universe
  and rejected in both held-out directions, twice. **Unless `SCREENER_SECTOR_NEUTRAL=false` is
  set in the environment, the hot list users see is scored under the intervention the research
  eliminated.** There are also three different composite functions in the tree (selection
  renormalises by present-weight mass, measurement does not, live renormalises AND adds the two
  interventions), so **no shipped code path reproduces the backtested composite exactly.**

**LATEST (2026-07-30) — SUPERSEDES much of CURRENT STATE above. Read this first.**
- **Five wired factors were SILENTLY EMPTY in every run this project has ever done.** The
  Sharadar export is ARQ-only and Sharadar fills its ratio/averaged columns only in ART/ARY:
  `roe`, `roic`, `assetturnover` are non-null in **0 of 197,265 rows**. `beta` was hard-coded
  `None`. `growth_accel` was overwritten with all-NaN by `build_frame`. So `quality` averaged
  **8 of its 10** inputs, `low_risk` **1 of 2**, `growth` **1 of 2** — with no error, ever.
  All four are now derived from line items that were present all along. `_f()` also returned
  NaN instead of None, which made `_f_score` count MISSING tests as FAILED ones.
- **A coverage guard now exists and would have caught every one of them**: `signal_coverage()`
  warns on any wired signal under 5% coverage and ships a `signal_coverage` block in
  BACKTEST_RESULTS.json. **Never trust a factor's IC without checking its coverage first.**
- **roic (t +3.38) and roe (t +2.84) are the 4th and 6th strongest signals in the panel** and
  were contributing nothing. `quality` is now the strongest theme (t +3.39).
- **`monotonicity`'s SIGN HAS BEEN READ BACKWARDS throughout these notes.** Buckets are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal), +1.0 = backwards.**
  The "monotonicity is negative ... the deciles aren't cleanly ordered" line above is WRONG,
  and P4's "−0.782 → −0.855, slightly worse" was an improvement. Now pinned by a test.
- **`low_risk` zeroed (live, reversible).** Its real full-universe IC is −0.0014 (t +0.71),
  NOT the −0.048 claimed below — dead weight, not harmful. It is **−0.352 correlated with
  `size`**, the strongest anticorrelation in the theme matrix: low-beta/low-vol names ARE
  large caps, so it was cancelling the small-cap tilt. `neg_asset_growth` also dropped
  (t −0.70, wrong sign).
- **The full-universe verdict CLEARS both bars for the first time: PBO 13.3%, Deflated Sharpe
  ~100% (saturated), long-short t 3.485, top-decile alpha +11.77%.** BUT the biggest
  contributor (zeroing low_risk) was chosen by looking at this same panel, so it is
  **in-sample-informed and needs out-of-sample confirmation** — HANDOFF_STATUS.md §5.
- **"The entire edge is 13F" is now OBSOLETE.** Without the institutional theme, top-decile
  alpha is still +10.6% and long-short t 2.86 (was 0.71). That finding was an artifact of
  quality/low_risk running on half their inputs.
- **`insider` is the only negative theme (t −0.34, now −0.43) and still carries 12.5% weight** —
  the obvious next candidate, deliberately NOT changed. **See the reproducibility note above:
  one of three identical-data runs returned +2.69, so this theme's t is not a measurable
  quantity in either direction. The held-out verdict is `rejected` in all three runs.**
- Real full-universe coverage: `institutional` **61.4%** (not the 81.7% below), `insider`
  85.0%. F-Score is **t +2.74** on the full universe, not +5.66.

**PREVIOUS (2026-07-29) — several claims below are corrected above:**
- **800-name large-cap run:** PBO 13%, Deflated Sharpe 77%, first CPCV "adopt" (`ic-ir`), top-decile
  +4.1%/yr vs equal-weight. BUT it's the friendlier large-cap universe (not the fair 3,000), still
  <95%, still ~1/3 13F-dependent. **The full 2,827-name run has STILL never completed** (scoring loop slow).
- **F-Score is the strongest new signal** (IC t +5.66), wired into quality; accruals + 13F-holder-breadth
  also kept. Classic anomalies (reversal, idio-vol, MAX, low-vol) did NOT replicate here.
- **`low_risk` theme has NEGATIVE pooled IC (-0.048)** and CPCV zeroed it — a live factor that's hurting;
  not yet changed (Don's call).
- **`assets` was silently dropped by the loader**, so `capital_discipline` was half-empty in every prior
  run — fixed; treat past capital_discipline conclusions as unreliable.
- **Bulk data loaded fast+safe** via `valuation/edge/bulk.py` (raw zips in `data/raw/`, extracts in
  `data/bulk/`, caches in `data/bulk/prepared/`): SF3 per-manager conviction, DAILY point-in-time
  marketcap+ratios, ACTIONS splits/delistings, EVENTS raw codes.
- **Now CONSUMED by the panel (2026-07-29 s3):** point-in-time market cap from DAILY (replaces the buggy
  shares×price path; AAPL 2015Q2 $722.6B verified), survivorship-free returns via the ACTIONS delisting
  mask (SEP is ALREADY split-adjusted, so split ratios deliberately NOT re-applied — don't "fix" that),
  SF3 conviction exposed as inputs (`sm_conviction/holders/breadth`, not yet in a theme). `institutional`
  coverage 70.5%→81.7%. STILL PENDING: scoring loop unvectorized; **full 2,827-name run has never completed.**

## METHODOLOGY RULE (hard — do not violate)
**Report verdicts ONLY from the full ~2,710-name universe.** 400/800-name subsets systematically
flatter results (PBO 13% on 800 → 53% on full; `sm_breadth` t 2.37 on 800 is unverified on full).
**CORRECTED 2026-08-03 (audit B12): the 800-name era was an ALPHABETICAL slice, not the 800
largest.** `WRDSProvider.universe` returned `sorted(keys)[:limit]`, so those runs were names
beginning with roughly A through C. "PBO 13% on 800 → 53% on full" was therefore never measuring
how much a large-cap tier flatters results — it was measuring how much an ARBITRARY 30%
alphabetical subsample does. The function is fixed (ranked by market cap, sort key printed in the
banner, subsets labelled smoke tests), but **every 800-name-era figure needs a full-universe
re-run before it is cited again**: the first CPCV "adopt", PBO 13%, Deflated Sharpe 77%,
`f_score` t +5.66, `sm_breadth` t 2.37, the 13F look-ahead stress test, and the four
classic-anomaly rejections (short-term reversal, idio-vol, MAX, low-vol).
Small samples are dev smoke-tests only ("does it compute / not crash") and MUST be labeled as such —
never the number a keep/reject/adopt decision rests on. The full run is now fast (~75s load + ~11s
score), so there is no performance excuse to judge on a subset. If you must screen small first, say
"smoke test" explicitly and re-run the survivor on the full universe before reporting a verdict.

## IMMEDIATE NEXT TASKS (in order) — updated 2026-07-30
1. ~~Wire the bulk caches into `build_fundamental_panel`~~ **DONE (2026-07-29 s3)** — PIT market cap from
   DAILY, ACTIONS delisting mask (splits NOT re-applied; SEP already adjusted), SF3 conviction exposed as
   inputs. (Coverage figure in that note was wrong: `institutional` is **61.4%** on the full universe.)
2. ~~**Add unit tests for `bulk.py`**~~ **DONE** — 12 tests.
3. ~~**Speed up scoring + complete the full 2,827-name run**~~ **DONE** — the full run now takes ~12 min
   end to end, and one duplicate full panel build was removed from it (2026-07-30).
4. ~~**P3 — SF3 smart-money conviction**~~ **DONE (P4 commit)** — `sm_breadth` kept, the rest rejected.
5. ~~**Fix hurting factors**~~ **DONE (2026-07-30)** — but only after discovering the factors were EMPTY;
   see LATEST. `neg_asset_growth` dropped (t −0.70), `low_risk` zeroed (IC −0.0014, −0.352 corr with size).
6. ~~**Confirm the `low_risk` removal out-of-sample**~~ **DONE (2026-07-30) — CONFIRMED.** Held-out
   time split, both directions: long-short t +1.59 / +2.02, top-decile alpha +3.21pp / +7.86pp on
   data that did not inform the decision. Now a PERMANENT check: `holdout_theme_validate()` runs on
   every backtest and ships a `holdout_validation` block in BACKTEST_RESULTS.json.
7. ~~**Test zeroing `insider`**~~ **DONE — REJECTED, left at 0.125.** Helped one split direction by
   a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample t is not stable.
8. ~~**TTM ROE/ROIC**~~ **DONE — REJECTED (P6.2).** Quarterly is BETTER (roe t +2.84 vs +2.01,
   roic +3.38 vs +2.57). Recency beats smoothing. Don't re-open without a new reason.
9. ~~**turnover/cost-aware construction**~~ **DONE (P6.1) — THE EDGE SURVIVES COSTS.** Breakeven
   236bps one-way vs ~37bps actual; net top-decile alpha +11.41%/yr. Measured on every run.
10. ~~**median/MAD robust z-scores**~~ **DONE — REJECTED (P6.3).** Halves the long-short t.
11. ~~**Consolidate momentum/institutional**~~ **DONE — REJECTED (P6.4).** Both earn full weight.

**OPEN, in priority order:**

12. **Forward paper-track vs SPY — the top priority.** The edge clears every internal bar and
    survives costs, but has still only ever seen this ONE 18-year Sharadar panel. A live track
    starting today is the only thing that tests it on data nobody has looked at.
    → **Cowork's lane** (tracked "Valquo Index vs SPY"). Tell Don to take it there.
13. ~~**Industry-relative ranking**~~ **DONE — unblocked (P10), then REJECTED and re-confirmed
    2026-08-02.** Sector is wired from TICKERS at 100% coverage and pinned by
    `tests/test_sector_neutral.py`; sector-neutral ranking fails the held-out gate in both
    directions under both flat and deployed weights (it buys long-short t and sells top-decile
    alpha — the wrong trade for a long-only book). Stays OFF. `HANDOFF_sector_neutral.md`.
    A NARROWER variant (sector-relative on the value theme alone) is now cheap to test and is
    the only version worth re-opening.
14. **Watch live behaviour after the P5 deploy.** `low_risk` 12.5% → 0 tilts the hot list
    smaller-cap. Intended, but eyeball the first scans; revert is one line in `settings.py`.
15. ~~**PEAD from EVENTS**~~ **DONE — REJECTED (2026-08-01, independently re-verified
    2026-08-03).** EVENTS code 22 was decoded, so it was finally testable. `pead_car` clears
    the standalone bar (median IC +0.0100, **t +2.215**, coverage 82.3%) but earns no weight;
    `pead_drift` fails outright (t −0.473, coverage 25.1% under the 30% floor). Two reasons the
    reject is solid, both stronger than the IC: **(a)** residualized on the three momentum
    inputs, pead_car's incremental IC t is **+0.020** — 89% of it is orthogonal to momentum and
    that 89% predicts nothing; **(b)** the book gain it does produce is beaten by a control
    using NO earnings data (counting `ret_6_1` twice: +0.83pp alpha vs pead_car's +0.52pp). It
    correlates most with the strongest momentum input and least with the weakest, so it acts as
    an implicit REWEIGHTING, not a new signal. Also **not actually PEAD**: theory says drift is
    strongest right after the announcement, but the recent-only window scores t −0.473 against
    the all-ages +2.215 — backwards. **Held-out deltas for PEAD are CONSTRUCTION-SENSITIVE and
    even flip sign** between the full composite and a restricted-universe book — never quote one
    without naming the book. Both variants stay MEASURED but score in no theme. Point-in-time is
    pinned by `tests/test_pead.py` (12 tests, incl. a tampering test). `HANDOFF_pead.md`.
    Re-open only with real point-in-time earnings surprises (IBES, parked — same blocker as #20).
16. **ML tree combiner** — clearly worthwhile now: several genuinely real signals exist, and P6
    showed the linear composite is sensitive to how inputs are scaled.
17. **Re-read every past "monotonicity" conclusion with the sign flipped** (see LATEST).
18. **Social preview:** add Open Graph + Twitter Card meta tags (esp. a 1200×630 `og:image`) so pasted
    valquo.co links auto-generate a rich card (LinkedIn etc.); re-scrape via LinkedIn Post Inspector after deploy.
19. **Later:** gated auto-apply of adopted weights.
20. **Estimate-revisions sentiment: PARKED** until WRDS/IBES (FMP has no point-in-time revisions at any tier;
    the free `stable/grades` workaround is real but weak and quota-starved). Don't fight the FMP free quota.

## COVERAGE RULE (hard — learned the expensive way 2026-07-30)
**Before reporting or acting on any factor's IC, check its coverage.** Five wired factors were empty
for this project's entire history and nothing surfaced it: an empty column contributes nothing to a
theme mean, raises no error, and the run completes normally. `signal_coverage()` now warns under 5%
and writes `signal_coverage.below_floor` into BACKTEST_RESULTS.json — **read that block first.**
The same class of bug has now bitten four times (`assets` in the loader allowlist, the SF3
positional-arg bug, these five, and `invcap`/`taxexp`/`ebt` missing from `_KEEP`). When adding any
signal, add its source columns to `WRDSProvider._KEEP` and confirm coverage in the next run.

## END OF EVERY SESSION: update `HANDOFF_STATUS.md`
Overwrite `HANDOFF_STATUS.md` in the repo root before you finish — what you did, concrete
numbers (test counts, PBO / Deflated Sharpe / IC / t-stats / alpha, row counts, adopt-or-reject
verdicts), what's blocked and why, and the recommended next step. Plain markdown, no colour
codes, factual. The Cowork agent reads that file directly instead of screenshots.

**Write your full end-of-session report — the complete recap you'd show Don (what shipped,
concrete numbers/verdicts, blockers, the recommended next step) — to your OWN
`HANDOFF_<name>.md`.** The Cowork agent reads that file directly, so Don never has to
screenshot. `HANDOFF_STATUS.md` stays the shared project state; `HANDOFF_<name>.md` is your
session's own full write-up, and parallel agents each own a separate file so they never
clobber each other.

## Working with Don
Concise, direct, honest. He is non-technical but sharp and rightly skeptical — show reasoning and caveats, don't inflate. Unlike the Cowork agent, you (Claude Code) can run commands yourself, so run the backtest/tests directly rather than handing him `.bat` files.

## Tool routing — Claude Code vs Cowork (IMPORTANT: tell Don when to switch)
Don runs TWO agents on this project. They do not talk live; they sync through this shared git repo/folder
(both see the same files). Each agent should explicitly tell Don to switch when a task is in the other's lane.

- **You (Claude Code)** own: running the backtest / `validate_13f.bat` / tests, editing this codebase, git,
  quant research, anything that needs to execute code locally. Do these yourself.
- **Cowork** owns: the Robinhood connector (read-only account data + producing rebalance lists — NEVER
  execute trades), the tracked "Valquo Index vs SPY", scheduled scans/tasks, and phone/mobile sessions.

**Git handoff — do NOT strand work on an unmerged branch (learned the hard way, July 2026).** Commit
directly to `main` in the primary checkout. If your harness forces a git worktree, you MUST land the work
on `main` before ending the session (`git checkout main && git merge --ff-only <branch>`) or hand Don the
exact commands — twice the entire P5 + held-out-confirmation work sat unmerged on a worktree branch while
`main` stayed on P4, and Don had to run the merge by hand to ship it. Don deploys from `main` with
`git_push.bat`. On Windows PowerShell that means: paste commands on SEPARATE lines (not joined with `&&`,
which its old shell rejects) and run the script as `.\git_push.bat`.

When a task needs Cowork, say so plainly, e.g.: **"→ Take this to the Cowork chat — it needs the Robinhood
connector, which I don't have here."** Cowork will likewise send Don back here for heavy backtests/code.
After you commit changes, the Cowork agent sees them in the same folder next time Don opens it.

Current handoff state (July 2026): task #1 is **done** — the 13F signal has been fairly tested and is real
but too weak to trade alone (details in CURRENT STATE). The ball is now on **task #2, estimate revisions**,
which needs an API key from Don (FMP or Intrinio). Do not spend more effort tuning or re-testing 13F.
