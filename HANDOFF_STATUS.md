# Valquo — handoff status

Written at the end of every Claude Code session. Overwritten each time, so this is always
the current state, not a log. Plain text, no colour codes — the Cowork agent reads this
file directly.

**Session date:** 2026-08-03 (external edge audit, session 1; deep research thread #2)
**Branch:** `worktree-options-live`, auto-lands to `main` via CI

> **Scope:** newest sections first — the external edge audit, then deep research #2, then the
> EV staleness fix, then PEAD, then options 22b, then P9b/P10, then P7/P8. Canonical numbers in
> `BACKTEST_RESULTS.json`; per-finding status in `CODE_AUDIT.md`.

---

## READ FIRST — AN EXTERNAL AUDIT HAS INVALIDATED SEVERAL HEADLINE CLAIMS (2026-08-03)

Full ledger: **`HANDOFF_edge_audit.md`**. Source: `VALQUO_EDGE_AUDIT.md`, a 108-item
code-reading review by an outside session. Session 1 of 8 is done — step 0 plus thirteen
Part I corrections. **What follows is what changed about what the project believes it knows.**

**Three claims in `CLAUDE.md` were unsupported and are now corrected in place:**

1. **The Deflated Sharpe: the audit's MECHANISM is refuted, its COUNT criticism stands.** It
   argued the eight weight schemes are indistinguishable so `SR0` collapses to ~0 and nothing is
   deflated. **Measured on the corrected full-universe run: `var_sr_across_trials` = 0.0276 and
   `sr0_benchmark` = 0.242 against a per-period Sharpe of 0.606** — it deflates away 40% of the
   Sharpe. The audit inferred near-identical trial SHARPES from near-identical median ICs; those
   are different quantities. What DOES stand: **`N = 8` against a ledger of ~146 real trials**, a
   denominator roughly 18x too small. Every run now ships `deflated_sharpe_detail` so this is a
   measured property per run, not an assumption either way. PBO likewise scores **only the
   weight-scheme selection step** — a selection the shipped strategy never makes, since it keeps
   `current-default` (now shipped as `pbo_scope`). **Lead with the long-short t against the
   Harvey-Liu-Zhu hurdle of 3.0.** That bar is real and it is cleared.
2. **`low_risk` was NOT "confirmed out-of-sample."** Verified in the code:
   `holdout_theme_validate` computes `rule_fired` at `fundamental_panel.py:3048` and **never
   reads it**; the verdict is `all(improves)` across both split directions. That is a demanding
   both-halves stability test and a legitimate one — it is not out-of-sample confirmation. The
   measured numbers are unchanged and still stand; the word was the overstatement. Fixing the
   function is audit **B8** and is NOT yet done.
3. **Every "800 largest names" result was an ALPHABETICAL slice** (`sorted(keys)[:limit]`), i.e.
   names beginning with roughly A through C. So "PBO 13% on 800 -> 53% on full" never measured
   what a large-cap tier does — it measured what an arbitrary subsample does. The function is
   fixed; **the affected figures are not citable until re-run**: the first CPCV "adopt", PBO 13%,
   Deflated Sharpe 77%, `f_score` t +5.66, `sm_breadth` t 2.37, the 13F look-ahead stress test,
   and the four classic-anomaly rejections.

**The biggest open question, and it is cheap: the headline has never been tested as alpha.**
`top_decile_alpha` is `4 x (top-decile 63d return - equal-weight universe 63d return)` and
nothing else — no beta adjustment, no factor model anywhere in the tree, and no t-statistic on
the headline metric at all. The composite is nearly FF5+MOM by construction. Pre-registered
thresholds and **both versions of the product claim** are written down in `HANDOFF_edge_audit.md`
Part 0, before the number exists. Until that regression runs, **the word "alpha" should not
appear in product copy.**

**A second live-product finding, not yet fixed (audit B7/G):** `screen.py:256` calls
`build_frame(metrics)` with no keyword arguments, so it inherits `CONFIG.sector_neutral`
(default **true**) and `CONFIG.residual_momentum` (default **true**), while the backtest forces
both `False`. Sector-neutral ranking was tested on the full universe and rejected in both
held-out directions, twice. **Unless `SCREENER_SECTOR_NEUTRAL=false` is set in the environment,
the hot list users see is scored under the intervention the research eliminated.**

**THE FULL-UNIVERSE RE-RUN — clean A/B against a pre-audit baseline on identical data.**
A throwaway worktree at `b67b07d` was re-run because the committed `BACKTEST_RESULTS.json`
stamped its own provenance as `commit 7eb0046, branch worktree-growth-valuation, dirty: true`.
(It reproduced to four decimals, so the stored file was fine — but that was not knowable in
advance, and it is only knowable at all because the results file records its git state.)

| metric | BASELINE | CORRECTED | delta |
|---|---|---|---|
| long-short t | 3.5202 | **3.8838** | +0.364 |
| top-decile alpha | +11.88% | **+11.78%** | -0.10pp |
| monotonicity | -0.9515 | **-0.9879** | better |
| equal-weight benchmark | +16.55% | +16.55% | 0 (the control) |
| PBO | 6.7% | **13.3%** | +6.7pp, still far under 50% |

**THIRTEEN CORRECTIONS AND NOT ONE HELD-OUT VERDICT CHANGED.** Every theme returns the same
verdict in both runs. The record's decisions were not resting on the defects, and the defects
were not hiding a different model — what moved is what the numbers MEAN.

**Two measured surprises, both reported against the audit's own expectations:**

- **A FULL BACKTEST IS NOT REPRODUCIBLE RUN TO RUN — unexplained, and it needs finding.**
  THREE full-universe runs on identical data gave `insider` median IC **-0.00335 (t -0.34)**,
  **+0.01551 (t +2.69)** and **-0.00339 (t -0.43)**, at unchanged 85.0% coverage. The first and
  third bracket the second and agree to four decimals, so the middle run is the anomaly — and
  **B26 is NOT the cause**, which an earlier draft of this file said it was. B26's effect was
  measured directly on 22,975 score pairs: 3.96% of scores move, correlation 0.9975, consistent
  with the ~0 IC change between the runs that bracket it. Every OTHER theme is stable to +/-0.01
  across all three. Two conclusions: `insider`'s IC sits so close to zero that its t is not a
  measurable quantity in either direction (which is why zeroing it came back `not_replicated`),
  and **a project whose memory is its results files needs those files to be deterministic.**
  Find the nondeterminism before trusting any marginal IC. Audit **S3** (the insider score's
  construction) is the thread that might make the theme measurable at all.
- **B10 recovered the WORSE signal.** The audit called it "one of the cheapest genuine signal
  recoveries available." Head to head: `accruals_q` as FCF/NI reads **t +1.26**; as the Sloan
  measure it reads **t +0.27**, at coverage 0.75 -> 0.97. The overwrite was a real defect — the
  column did not contain what its name said — but the thing it overwrote with was the better of
  the two. Both columns now exist (`accruals_fcf_ni`), so switching back is a one-line A/B that
  belongs in front of the held-out gate.

**B14 delivered its first number: `ended_early_unmasked` = 0 of 2,710 tickers**, 887 series
masked (32.7%) from a 19,207-name delisting map. No name's prices stop early without an ACTIONS
row — the first direct evidence the survivorship mask is not silently missing delistings.

**The new B18 sign check fired on its first run and caught my own incomplete fix:** `ev_ebitda`
still admitted negative EV (414 rows, 0.36%). It also found that the `ev_sales`/`ps` negatives
are NOT negative EV but negative **revenue** — 538 rows (0.273%), in agency mortgage REITs and
financial guarantors (DX, NLY, AGNC, MBI, RWT, FNMA). All three now take the same convention:
missing, not extreme.

**Corrected this session (13 items + 1 new finding), all with regression guards:**
B1 price basis in the options universe (and four MORE sites, including in roadmap 22c and deep
research thread #1 — **both of those need re-running**); B3 stale marks at expiry; B9 DSR/PBO
relabel; B10 the `accruals_q` overwrite; B12 the alphabetical universe; B14 delisting-mask
coverage now shipped with an `ended_early_unmasked` counter; B15 commission in `return_pct`;
B16 the dead exit module quarantined; B18 one convention for negative EV; B19 the Sharpe label;
B20 the `earnings_yield` numerator; B24 duplicate sanity evaluation; B26 same-day filings.
Plus **C7**: the CI gate now runs all 16 suites, not one of sixteen — it auto-merges to `main`
and Render auto-deploys, so this needed to land before any other edit.

**D10-a, a NEW defect not in the audit,** found by running `verify_sharadar.py` against the live
key: Sharadar **appends** a new ARQ row on restatement (3.15% of ticker-reportperiod groups,
1,818 of 2,827 tickers), and `_ttm` de-duplicated on **datekey**, which two filings of one
quarter never share. Blast radius is small — only `roe_ttm`/`roic_ttm`, already rejected — but it
is the fifth instance of "a guard that cannot see the failure it was written for."

**Also settled from the live Sharadar key before it lapses (D10/C5):** all 8 bundle tables are
reachable including SFP; SEP has **no `dividends` column** and `closeadj` is dividend-back-
adjusted, i.e. **total return** — which means audit item **R8**'s premise ("dividends are on
disk and unused") has to be re-checked before R8 is run; `TICKERS.category` has 15 real values
and the options-bot's universe filter knows 6, silently excluding 382 Canadian common-stock
rows; SF1 percentage fields are fractions, not percents.

**Not yet done, in the audit's own order:** session 2 (B2, B4, B5, B7, B11, B13, B17, B21-B23,
B25, begin B6), then X7/X2 (the noise floor), then **R1** (factor-adjusted alpha — do not start
Parts III-V until it returns), then R2/R3/R7 (the corrected options re-run). **P4 is urgent out
of band**: the forward track's `seed_book` never sells names that leave the book, so it only ever
adds — a track that silently drops losers is worse than no track.

---

## DEEP RESEARCH THREAD #2 — CROSS-SECTIONAL OPTION RETURNS: REJECT (2026-08-03)

Full report: **`HANDOFF_deep_xsection.md`**.

3,373 one-month ATM straddles, 242 names, 117 months (2016-02 to 2025-10), full mined universe,
both legs bought at the **ask**, held to expiry and settled at intrinsic. Coverage 82-100%.

**Zero adoptions. Zero BH-FDR discoveries at q = 0.10** (smallest p 0.291). PBO 41.4%.

- **`iv_rv` — Goyal-Saretto does NOT replicate**: monotonicity **+0.20**, i.e. no ordering in
  either direction, on the characteristic with the strongest published prior. Q1 excess t -0.69.
- **`idio_vol` CONTRADICTS Cao-Han**: a clean **+0.90** sort running the WRONG way — high-idio-vol
  straddles earned MORE (+0.110 vs +0.033). Reported as a contradiction of the literature, never
  re-signed into a result; the sign was declared before the panel existed. Caveat: the instrument
  is a straddle, not a delta-hedged call, so this may be the instrument and not the market.
- `idio_skew` (t +0.68) and `illiq` (t +1.06) have the right sign and no magnitude against
  MIN_T = 2.0. `illiq` is a mechanical control and can never be adopted; that it sorts at all
  (mono -0.70, the cleanest in the table) is the evidence the panel measures what it claims to.
- The long-short Q1-Q5 gates nothing — its short leg is a naked short straddle.
- **Not affected by audit B1**: this module uses `raw_close` for every option calculation.

---

## ENTERPRISE VALUE IS NOW PRICED AT THE REBALANCE DATE (2026-08-03), landed on `main` at 3f688d4 — **SHIPPED ON**

Full report: **`HANDOFF_ev_fix.md`**.

Sharadar's `ev` embeds the **filing-date** market cap, so `ebit_ev` / `ev_sales` / `ev_ebitda`
measured cheapness against a ~111-day-old quote while `earnings_yield` / `fcf_yield` /
`book_to_price` used the fresh one. `_pit_ev()` now re-prices the **equity leg** to the
point-in-time market cap and holds the **debt leg** at its last filed value (net debt is only
observable at a filing — that *is* the point-in-time answer). Net debt must be
currency-converted before it is added, which is P7 in a second costume.

Re-pricing moves EV a **median 5.1%** (mean 9.9%, p90 19.6%); **26.7% of rows move >10%**. The
direct evidence the staleness was real: `neg_ev_sales` median IC **+0.0214 → +0.0363 (+70%)**.

**The book is a wash, so it ships on correctness, not performance.** Long-short t 3.3957 →
**3.5202**, top-decile alpha +11.82% → **+11.88%**, PBO **6.67% unchanged**, monotonicity
unchanged, and net top-decile alpha slightly *worse*. The A/B is clean: the stale arm
reproduced the committed baseline exactly, and the panel diff showed exactly 9 changed columns
on identical keys.

The bias was **stale, not look-ahead** — the embedded price is always older than the
rebalance, never newer — so **no past result is invalidated upward**.

- New **`ev_freshness`** block in `BACKTEST_RESULTS.json` (schema v4): **100.0% fresh**, zero
  stale rows. It makes a silent revert loud. `EDGE_EV_POINT_IN_TIME=false` reverts.
- Fixing this also closed a latent bug in `results_file.build_payload`, which **silently drops
  any block it does not explicitly name** — the new guard would never have reached the JSON.
- Tests 22 → **34** in `tests/test_ev_multiples.py`, pinned by a test asserting EV tracks
  market cap across rebalances from a single filing.
- **One shipped number moved:** the Valquo Index paper-track book swaps **RF out, BP in** —
  one position of 86, **1.81% one-way weight turnover**. → **Tell Cowork.** The live web
  screener is unaffected (provider EVs are already current).
- **Deliberately NOT fixed:** negative EV (net cash > market cap, 909 → 950 rows, 0.70%) is
  read as *maximally cheap* by `neg_ev_sales` and as *expensive* by `ebit_ev` — a live sign
  inconsistency, pre-existing and unrelated to staleness. Bundling it would have confounded
  the before/after. One guard plus one held-out A/B.

---

## PEAD — REJECTION INDEPENDENTLY RE-VERIFIED, and the control that explains it (2026-08-03), landed on `main` at d86af01

Full report: **`HANDOFF_pead.md`**. The verdict below **supersedes nothing** — it confirms the
earlier PEAD section further down this file and adds the diagnostic that was missing.

PEAD was already built and rejected (`9323a08`, `2f75d60`); what was missing was the report.
So this session re-measured every claim on a fresh full-universe run built on the
**post-EV-fix** panel, rather than re-running a settled experiment.

**Replicates essentially exactly:** `pead_car` median IC **+0.01004, t +2.215, coverage
82.33%**; `pead_drift` **−0.00201, t −0.473, coverage 25.06%** (below the pre-committed 30%
floor). Orthogonality within rounding: `ret_6_1` +0.301, `high_prox` +0.239, `ret_12_1` +0.208.

**The control that settles it — correlation alone would have flattered this signal.** Momentum
explains only **R² 11.2%** of `pead_car`'s variance, so 89% of it is orthogonal — which reads
like a promising near-independent factor. It is not: residualized, its IC t is **+0.020**. And
the book movement it does produce is reproducible with **no earnings data at all** — counting
`ret_6_1` twice in the momentum mean gives **+0.83pp** alpha against `pead_car`'s **+0.52pp**,
beating it in the early half by more than 4x. Adding `pead_car` is an implicit **reweighting**
toward the strongest momentum input, not new information.

**One correction worth flagging:** my held-out deltas came out **positive** where `pead.py`
records negative ones. Chased down rather than resolved by preference — the deltas are
**construction-sensitive and flip sign** between the full composite and a restricted-universe
book (restricting to rows where the signal exists reproduces the original magnitudes and its
−1.06pp early-half alpha). **Every construction fails the pre-registered margins, so the
reject is robust** — but never quote a held-out delta for PEAD without naming the book.

`pead.py` runs on every panel row and had **zero test coverage**; added `tests/test_pead.py`
(**12 tests**), including a tampering test that multiplies every price *after* the CAR window
by 5 and asserts the signal does not move. A CAR is a forward-looking window by construction,
so an off-by-one there would manufacture edge from future returns while raising no error and
denting no coverage metric.

**All 16 suites green on merged `main`: 485 tests.** With this closed, the cheap signal ideas
are exhausted — the honest next steps are the **forward paper-track vs SPY** (Cowork's lane)
and the **ML tree combiner**, not another factor.

---

## DEEP RESEARCH THREAD #1 — EXIT OPTIMIZATION — **REJECT, AND A SIMULATOR BUG FOUND** (2026-08-03)

Full report: **`HANDOFF_deep_exits.md`**. Gate committed results-free at `56268b6` before scoring.
Full run: **278 complete names**, 3,119 signal entries + 5,986 random entries, 21 exit policies,
aggression 1.0. Catalog updated in `OPTIONS_DEEP_RESEARCH.md`; next thread is **#2 cross-sectional
option returns**.

**READ THIS BEFORE ANY THREAD THAT HOLDS POSITIONS LONGER (VRP, earnings, calendars).** The
production simulator marks a position that outlives its contract's last usable quote at **that
stale quote** — and a contract stops being quotable exactly when it is dying. For the
hold-to-expiry policy **44.6%** of trades land in that fall-through, their last quote is a **median
of 10 days before expiry**, it is **higher than true settlement in 94.7%** of cases, and **86.1%**
carry a positive mark on a contract that expired worthless (mean marked −77.8% vs a true −92.2%).
The bias **scales with holding period**, so it manufactures a monotone fake reward for holding
longer — worth **+6.45pp** on that policy. **The shipped exit hits it on 0.9% of trades, so 22b,
22c and every earlier options result are essentially unaffected**, and all of them use the same
exit so their comparisons are unaffected too. Honest settlement (`settle="intrinsic"`) is now the
default in `options_exitlab.apply_policy` and is pinned by a test.

**Verdict REJECT — nothing clears the +10pp bar.** But the direction is real, small and consistent,
and it **replicates on RANDOM entries** with equal or larger size, so whatever effect exists is a
property of the **EXIT**, not of the dead entry signal — which is exactly what the mandate asked:
- **cutting winners early is costly**: +50% target −3.61pp, +75% −1.19pp, **+150% +2.11pp, +200%
  +3.26pp**;
- **stopping out tight is costly**: −30% stop −2.61pp, −70% +3.13pp, no stop +3.20pp; trailing stops
  are the worst family (25% trail −4.06pp);
- so the optimum target sits nearer **+150–200%** than the shipped +100%, and the −50% stop is on
  the costly side. `tp200` is the only policy better on **every** axis — per trade, per day held,
  both entry sets, both halves, majority of the cells it changes (FDR 10%), DSR 99.8%.

**Do NOT be fooled by `tp100_only`**, the grid's biggest per-trade number (+6.71pp): per DAY of
capital committed it is *worse* than the shipped exit on both entry sets (+0.00250 vs +0.00256),
it simply holds **2.5x longer**, its paired direction **flips sign between entry sets**, and it
carries **21.5% total losses vs 0.67%**.

**The barbell, measured in two numbers:** tightening the stop (sl30) **wins a majority of cells
(z +10.6) and loses 2.61pp of expectancy**; holding to expiry **earns +6.71pp and loses a majority
of cells (z −3.97)**. Mean improvement and win-rate point in opposite directions — the same lesson
the autopsy taught about hit rate.

PBO by CSCV over the policy grid: **0.075 signal / 0.000 random** over 252 splits — not overfit,
there is just not much in it. Tests **166/166** edge (10 new).

**Two questions left open, deliberately not renegotiated:** whether an ABSOLUTE +10pp bar is right
for a proportional improvement (tp200 is a ~69% relative lift on a +4.71% book), and whether
requiring both a mean gain and a cell-win majority is self-defeating on a convex payoff.

---

## OPTIONS ENTRY TIMING (roadmap 22c) — **THE ANTI-TILT IS REAL AND STABLE, AND NOT SALVAGEABLE** (2026-08-03)

Full report: **`HANDOFF_entry_fix.md`**. Gate committed results-free at `52a4658` before the run.

22b found the scream-buy alert picks worse-than-random entry days. 22c asks why, and whether a
corrected entry beats BOTH the signal and the random-entry control. Full run, 187 names,
aggression 1.0, 2016-01-01..2025-10-15. The signal arm reproduces the 22b book **trade for
trade** (3,042 trades, zero P&L differences).

**The finding replicates and is STABLE — it is a property of the signal, not of a period.**
Signal +5.14% vs control +11.07% (5,919 control trades); paired −3.72pp over 1,080 name-year
cells, sign z = −3.48. Negative in **both** halves (−5.88pp early z −2.20, −5.96pp late z −2.69)
and significant in the two tiers that carry the book (mega −5.03pp z −2.61, large −7.37pp z −2.26).

**The hypothesis was WRONG, with the sign reversed.** The mandate expected the alert to chase
pumped IV. It does not — alert days carry **CHEAPER** vol than a random day in the same name-year:
~60-DTE ATM IV 0.2428 vs 0.2577 (paired z −11.13, only 32.9% of cells higher), IV rank 0.345 vs
0.425 (z −9.89), IV pop 0.968 vs 0.991 (z −6.56). **Zero of four IV proxies confirm.** What alert
days do carry is EXTENSION: the median alert buys **0.24% below the 52-week high** after a +4.1%
five-day run, against −4.68% and +0.78% for a random day (z +29.45 and +27.92). Sustained advances
compress vol, so the alert buys strength cheaply and still does worse. **E2 verdict: PARTIAL.**

**All FIFTEEN corrections fail** (9 simulated arms + 6 same-day context gates, all counted in the
deflation, DSR at n_trials = 14):
- **Delaying makes it monotonically WORSE**: +6.36% / +4.36% / +3.59% at 3 / 5 / 10 sessions. Not
  a timing offset.
- **Fading loses outright**: buying the put instead returns **−10.54%/trade**, PF 0.743, negative
  in both halves. The anti-tilt does not invert.
- **`pullback` is the sharpest picture and still fails.** On the 867 alerts followed by a 3% dip
  the signal returns **−43.59%/trade** and buying the dip returns +3.19% — paired +46.07pp, z
  +11.64, p = 2.5e-31, the only BH-FDR discovery. It still loses to the control by 8.45pp, is
  negative early, and loses to a same-sized random drop (+2.62% vs +4.99%).
- **Context gates 0 of 6.** "Skip the most-extended alerts" (ret_21d) clears FOUR of the §2 gate's
  five arms — late gain +5.93pp, retention 44.7%, beats its random filter — and fails the fifth
  (early-half gain −0.83pp). Rejected on the pre-committed bar, not renegotiated.

**Why nothing works: the underperformance is UNIFORM.** The alert loses to its control in every
quartile of run-up (−7.5/−2.3/−10.8/−3.1pp) and every quartile of IV pop (−11.7/−0.9/−3.4/−7.9pp).
Within the alert book neither run-up nor the alert score itself orders the outcome — a HIGHER
scream-buy score does not mean a better trade (+2.33/+8.55/+4.11/+4.34% by score quartile). There
is no slice to condition on. Nor does any label: all nine label families with a real sample sit in
a +4.3% to +6.8% band around the book's +5.14%, and the OPTIONS-FLOW labels do not separate from
the TECHNICAL ones — which answers 22b's open question about which half of the score does the
damage: **neither, distinguishably.**

**Held-out arm selection, both directions:** the best arm beats the signal by +40 to +50pp on the
half that did NOT choose it — and still cannot beat buying on a random day.

**THE CAVEAT THAT MUST TRAVEL WITH THIS.** The control is a yardstick, not a tradable strategy: it
only trades name-years the alert selected, and it is buying weakness inside years that by
construction contained a strong advance. The correct statement is "within the years the alert
selects, the alert picks a below-average day." Whether the book beats SPY is **still unanswered**
— every options comparison in this project is internal. **That is the forward paper track, and it
is Cowork's lane.**

**Do not re-open:** delayed entries, IV-normalisation waits, IV-cheap gating, extension gating,
fading the alert. All measured, all in `data/options_entry/ENTRY_RESULTS.json`.

Tests **156/156** edge (14 new).

---

## OPTIONS ON THE EXPANDED UNIVERSE (roadmap 22b) — **THE EDGE HALVES, AND THE SIGNAL FAILS ITS FIRST PLACEBO** (2026-08-03), landed on `main` at 1a2f95f

Full report: **`HANDOFF_universe_backtest.md`**.

The single-leg scream-buy backtest was re-run across the whole cached universe — **187
complete names, 3,042 trades**, NBBO at aggression 1.0, 2016-01-01..2025-10-15, nothing
re-tuned. The gate was committed in the module docstring before the run.

**The edge survives breadth but roughly halves: +12.33%/trade on 55 megacaps -> +5.14% on
187.** Both held-out halves positive so it passes, but Deflated Sharpe falls **98.62% ->
88.13% unfiltered**, below the 95% bar (95.69% on the term_slope-filtered book, only just
clearing). Mid/small caps are the BEST tier (+9.80%), not the worst; the home-run thesis is
NOT upheld (P(>=+100%) +1.86pp, CI spans zero).

**A control this project had never run on the options book changes what all of that means.**
Same name, same calendar year, RANDOM entry day, identical contract/fill/exit rules:
**+13.22% against the alert book's +5.14%.** The alert book loses in every cap tier, in 9 of
10 years, and in **58% of 1,052 name-year cells (sign-test z = -5.24, two independent seeds)**.
Contract characteristics are near-identical (DTE 58 vs 58, delta 0.355 vs 0.351), so this is
day-selection, not what gets bought. The scream-buy alert picked WORSE days than chance. The
book is profitable; the signal is not what makes it profitable. **Do not ship an options
alert change, and stop quoting +12.33%/trade, until this is settled.**

**The old-vs-new gap is 100% spread, not signal.** A full second pass at mid fills on the same
pinned names: the two cohorts are +11.99% and +11.56% at the mid, versus +6.95% and +3.90% at
the touch. Crossing the spread costs **6.59pp — more than half the surviving edge**. Mid/small
pay roughly double the megacap toll (-9.4pp / -11.0pp vs -5.4pp) but start from a gross edge
high enough to finish ahead net. Don's "spreads eat it" thesis is half-right and now measured.

**Universe selection is not neutral and the bias runs TOWARD the edge:** the miner skipped 55
of 245 names as thin, and today's-liquidity selection makes the `small` tier future winners in
their small days (median **14.8x** cap growth to today). Splitting each tier by that hindsight
growth puts the ENTIRE mega/large edge in the names that later grew, with the other half flat
to negative. That split is partly circular and can never be a filter — but combined with the
control it means **this cache cannot separate the strategy from its universe's upward
selection.** Only a forward track can.

**term_slope:** the economic effect DOES generalise out of sample — **+8.89pp** on 133 names
that never informed its threshold, against the +8.12pp that got it adopted, and it is mildly
tail-ENRICHING (keeps 41.2% of >=+100% winners while keeping 37.3% of trades). **But B2 FAILS
on retention** (36.4% vs the pre-committed 40% floor, which the 55-name run cleared at only
40.6%). Reported as FAIL: a pre-committed gate is not renegotiated after the run.

**The #23 autopsy headline re-confirms on the wider set** — the gate was re-run *unchanged*
(`options_autopsy.run()` gained a `trades` override so the two stay comparable): 64 features,
127 hypotheses, **zero survivors, zero FDR discoveries, PBO 35.7%**, combiner rejects. Mid/small
caps surface nothing that separates winners from losers.

Sanity clean, zero flags. `data/options/` read-only throughout. Suites: `test_edge.py`
**142/142** (9 new) and all 14 other suites green. Recommended next: decompose the control
finding (is it the technical run-up requirement or the options-flow score?), then the forward
paper track -> **Cowork's lane**.

---

## LAZY PRICES (roadmap #28) — TESTED AND **REJECTED** (2026-08-03), landed on `main`

Full report: **`HANDOFF_lazy_prices_ic.md`**. Dataset build: `HANDOFF_lazy_prices.md`.

The 10-K/10-Q language-change signal was built (195 filers, 7,095 scored pairs, free SEC
EDGAR, 0 fetch failures) and then put through the gate. It does nothing: rank-IC **-0.0156**,
t(NW) **-1.07**, long-short **-5.0%/yr**, top-decile alpha **-2.9%/yr**, and the deciles run
BACKWARDS (monotonicity +0.709, where -1.0 is ideal). Both time halves negative. Across 28
measure x horizon cells nothing clears the bar in the pre-registered direction, and the one
cell that looked good (`jaccard@252`, IC t +3.88 early) collapses to +0.24 on the later half.
It is genuinely orthogonal to every existing theme (|r| < 0.07) and genuinely uninformative —
residual IC after regressing the themes out is -0.001 (t -0.06). **Nothing wired in; roadmap
#28 closes.** Do not spend the ~1hr/250-names fetch on extending it — see §8 of the report.

One finding was left deliberately unexploited and is written up in §5: the MD&A-section
measure has a *significant* spread in the WRONG direction (biggest rewriters +8.6pp), stable
in both halves, not explained by the growth or momentum themes. It was NOT flipped into a
signal — the direction was pre-registered before returns were joined, so reading it backwards
is a new hypothesis, not a rescue of this one.

Suites on the merged tree: `test_edge.py` 123/123, `test_lazy_prices.py` 28/28,
`test_lazy_prices_ic.py` 24/24. Research code lives in `valuation/research/` and a test
asserts no production module imports it.

---

## Data mining (ThetaData cache expansion)

Running in its own session; status and design notes are in **`HANDOFF_miner.md`**, not here.

## ITEM 0 SHIPPED + A2 COMPLETE (2026-08-02)

**Item 0 - `git_push.bat` is now genuinely one command, and it is VERIFIED.**
Real `git merge --no-edit` for any `worktree-*` branch ahead of main (divergence stops
mattering), conflict -> abort + report + BLOCK the push, tests run and a red suite refuses the
push, auto-land skipped unless HEAD is main.

Verified, not eyeballed - it broke twice more during this work, exactly as the prompt warned:
LF-only line endings (a .bat with LF does not execute on Windows) and `2^^>nul` double-caret
inside the for-loop. Last session's failure was the HARNESS, not the script: the script does
`cd /d "%~dp0"` itself, so invoking it by FULL PATH lands it in the scratch repo regardless of
the caller's cwd. All three scenarios now pass:

    diverged branch merges + pushes    PASS  (main 2 -> 5 commits, remote updated)
    red tests block the push           PASS
    conflict aborts, nothing pushed    PASS  (dirty=0, no MERGE_HEAD)

The harness ships as `verify_git_push.ps1` so this stays re-testable. **`.\git_push.bat` will
now land the outstanding options commits by itself.**

**A2 - iv_rank made testable, then REJECTED on merit.**
Built a daily ATM-IV series across ALL trading days from the cached chains: **137,418
observations, 55 names, median 2,514 each**. iv_rank coverage went **0.0% -> 99.0%**. Through the
same pre-committed gate it fails every arm: late gain -0.93pp (bar +5pp), worse than the random
control (+3.83% vs +4.84%), early gain -1.25pp, retention 39.9% (bar 40%). By year it is
erratic - helps 2024/2025, destroys 2021 (-19.45%) and 2023 (-22.25%). Buying when vol is
already rich for the name is not a durable long-premium filter.

Series cached at `data/options/atm_iv_series.pkl`, reusable for any vol-regime read.

**A2 - tick flow INFEASIBLE at this scale, measured.** `option_history_trade` = 6,259 rows in
5.0s for ONE expiry-day; across 55 names x 2,500 days x 8 expiries that is **1,537-1,957 HOURS**.
`option_history_trade_quote` pairs trades with the prevailing quote (exactly what aggressor-side
needs), so the signal is constructible but not affordable historically. **Feasible alternative:
alert days only, ~1,841 x 6.4s ~ 3.3 hours** - the sensible way to test it if wanted.

**Standing after A2:** the only adopted new signal remains `term_slope` (phase 3b, +8.12pp late).
skew / VRP / GEX / iv_rank all rejected on evidence; tick flow untested by cost.

**A3-A5 NOT STARTED** (VRP credit-spread arm + correlation; options-bot fold-in; live book with
per-alert confidence + sizing).

## A2-A5 SESSION - item 0 attempted and NOT LANDED (2026-08-02)

**Nothing shipped this session. `git_push.bat` is UNCHANGED and still the known-good version.**

I wrote the upgrade (real `merge --no-edit` instead of FF-only so a diverged main stops
mattering; abort + report on a genuine conflict; run tests and refuse to push when red) but
**could not verify it**, and the prompt was explicit: "this script has broken twice on batch
escaping; test it, don't eyeball it." The scratch-repo harness never managed to get cmd.exe to
actually invoke the script - every scenario produced zero output - so not one of the three
behaviours was ever exercised.

The attempt DID find one real bug, which is exactly the argument for not shipping unverified:
the file had been written with **LF-only line endings**, and a .bat with LF endings does not
execute on Windows. Trusting the code review instead of the test would have silently broken
Don's ONE deploy command.

So the upgrade is parked as **`git_push_v2_UNVERIFIED.bat`** with a banner listing what to test,
and `git_push.bat` was restored via `git checkout --`. Replacing a working deploy script with an
unverified one risks leaving the repo mid-merge - worse than the manual merge it was meant to
remove.

**To finish item 0:** copy v2 into a throwaway repo containing a diverged `worktree-*` branch and
confirm (a) the branch merges, (b) red tests block the push, (c) a conflicting branch aborts
cleanly leaving no MERGE_HEAD. A three-scenario harness exists at `C:/Users/donni/.claude/jobs/7819c8eb/tmp/verify_push.ps1` - its `RunScript`
function is the part that does not work.

**A2-A5 NOT STARTED.** Item 0 was ordered first and consumed the session.

**MERGE STILL OUTSTANDING** - phases 1-3b and phase 4 A1 are on `worktree-p24-shortinterest`,
not on main. Verified conflict-free (zero overlapping files):

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 89/89)
    .\git_push.bat

## PHASE 4 - test fix + A1 term-structure filter WIRED LIVE (2026-08-02)

**Close-out item done first, as instructed: the env-sensitive test is fixed.**
`test_thetadata_provider_is_optional_and_dedupes` asserted a keyless provider returns an empty
chain - but `chain_on` consults its DISK CACHE before checking availability, so on any machine
with a real `data/bulk/prepared/theta/AAPL/2023-03-01.pkl` the keyless provider returned live
cached data and the assertion failed. It also read THETADATA_API_KEY from the environment/.env.
That is exactly why it was 88/88 here and 87/88 on Don's machine. Now pinned to an empty temp
cache dir with an explicit `api_key=""`. **Verified 88/88 with the key set AND unset.**

**A1 DONE - `term_slope` wired as a standing, reversible live filter.**
Chain: TradierProvider now also fetches a ~60-DTE expiry's ATM IV (term_slope needs both legs)
-> `options_signals` carries `atm_iv_60d` -> `screaming_buys` annotates via
`intraday/term_filter.py`. Config flag `OPTIONS_TERM_FILTER` = flag | suppress | off.

Three deliberate design choices:
- **Default is FLAG, not suppress.** The filter removes ~60% of alerts; that is too large a
  product change to inherit silently from a backtest. Every alert still appears carrying
  `term_ok` + a reason, so the UI can show backwardation ones as reduced confidence.
  `OPTIONS_TERM_FILTER=suppress` is one env var away.
- **Fails OPEN.** Missing/malformed IV -> `term_ok=None` (unknown), never False. A quote-feed
  hiccup must not masquerade as backwardation and silently halt alerting.
- **Sizing compensates.** Contango alerts get a 1.5x multiplier, backwardation 0.5x, unknown
  1.0x - so filtering 60% of signals does not quietly shrink sleeve exposure by 60%. Capped,
  because "trade less often but much bigger" is how a modest edge becomes a concentrated bet.

Tests 89/89 (one added pinning fail-open, flag-by-default, and reversibility).

**NOT DONE - the bulk of phase 4.** A2 (daily ATM-IV series to make iv_rank testable; tick
flow), A3 (VRP/credit-spread arm + correlation with the long arm), A4 (options-bot fold-in),
A5 (tracked book + per-alert confidence + suggested sizing), and ALL of PART B (live-app
backlog: data integrity, 861-name universe, remove Sharadar from the live path, dynamic net
alpha, trust/reliability) and PART C (growth/pre-profit valuation, RKLB $2.63 vs $65).

**§0 STILL BLOCKED and phase 4 assumed it was done.** Phases 1-3b are NOT on `main`. Dry-run
merge confirms NO conflicts, ZERO overlapping files:

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 89/89)
    .\git_push.bat

## OPTIONS PHASE 3b §2 - term structure ADOPTED, arrests most of the fade (2026-08-02)

Five ThetaData-derived signals tested, each fitted on 2016-2020 and judged ONLY on 2021-2025
(where the edge fades). **One adopted, three rejected, one not testable.**

    term_slope  kept 40.6%  late +4.76% -> +12.88%   +8.12pp   ADOPT
    skew_25d    kept 44.0%  late +5.33% ->  +6.43%   +1.10pp   reject
    vrp         kept 56.1%  late +4.76% ->  +5.30%   +0.54pp   reject
    gex_proxy   kept 50.2%  late +4.65% ->  +4.00%   -0.65pp   reject
    iv_rank                        NOT TESTABLE (see below)

**TERM STRUCTURE (contango: ~60-DTE IV above front IV) nearly triples late-half expectancy** and
is economically coherent - backwardation prices near-term stress or a pending event, a bad moment
to buy a 45-75 day call. On the losing years: **2022 -11.41% -> +19.78%, 2023 -4.61% -> +7.30%,
but 2025 -0.05% -> -5.90%.** Two of three repaired, one worsened; across ten years it helps six
and hurts four. A real filter, not a universal one.

Robust to its only parameter: over a 3x threshold range the gain stays +7.7 to +9.0pp. But it
DISCARDS ~60% of alerts (retention 40.6% against a 40% floor), so the book gets materially
smaller - that belongs in any sizing decision.

**Bug worth knowing:** 288 skew values were NaN (not None), so they passed the not-None filter,
the median came back NaN, and every comparison was False - the filter kept ZERO trades while
coverage reported 100%. Fixed; skew then tested fairly and rejected on merit.

**iv_rank is NOT TESTABLE as built, not rejected.** It needs 60 prior ATM-IV observations per
name, but IV history came only from that name's alerts (~28 avg), so coverage was 0%. Needs a
daily ATM-IV series per name across all trading days - straightforward, but a fresh compute pass.
Tick flow also remains untested (needs the tick feed, not cached).

**§0 STILL BLOCKED - BUT VERIFIED SAFE.** A dry-run merge shows NO conflicts and ZERO overlapping
files (main adds 166 under options-bot/ + prompts; this branch changes 23 under valuation/,
tests/, docs). My harness forbids merging/pushing to main, so this needs one manual step:

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 88/88)
    .\git_push.bat

**NOT DONE:** §4 VRP/credit-spread arm + correlation with the long arm; §5 options-bot fold-in
(also blocked - that code is on main, not in this worktree); §6 live engine, tracked book,
per-alert confidence + suggested sizing. Roadmap 22b (small/mid-cap) is the next iteration and
needs a fresh ThetaData pull.

## OPTIONS PHASE 3 - sizing adopted, DTE rejected, §0 BLOCKED (2026-08-02)

**§0 IS BLOCKED AND NEEDS DON.** `main` has DIVERGED from the options branch: main took in the
whole `options-bot` tree (164 files, ~27k lines) plus the PROMPT files in two automated "Update"
commits, while 28 phase-1/2/3 commits sit on `worktree-p24-shortinterest`. Because it is no
longer a fast-forward, **`git_push.bat` will SKIP it** ("not a clean fast-forward, merge by
hand"). The changes do not overlap - main added `options-bot/`, the branch touched `valuation/`,
`tests/` and the docs - so the merge should be clean. My harness forbids merging or pushing to
main, so this needs one manual step:

    git checkout main
    git merge worktree-p24-shortinterest
    python tests/test_edge.py        (expect 88/88)
    .\git_push.bat

**§1 FIXED-DOLLAR SIZING ADOPTED - and a phase-2 number is CORRECTED.** Phase 2 said fixed-dollar
sizing cuts the top-15 share to 42.0%; that deployed exactly $1,000 per trade, i.e. FRACTIONAL
contracts, which do not exist. With whole contracts:

    1 contract each (phase 1)          top-15 98.1%   ex-top-15  $2,767
    idealised fractional (phase 2)            42.0%              $92,998
    whole contracts, min 1                    62.9%              $83,986
    whole contracts, skip too-costly          50.3%              $54,853  (drops 13% of signals)

200 of 1,540 signals cost more than a $1,000 budget for one contract, so they can only be
skipped or taken oversized. **The conclusion survives - 98.1% -> ~45-63%, ex-tail $2,767 ->
$55k-$93k - but 42% is not reachable in any tradeable form.** Larger budgets are better on every
axis ($5,000: 98.4% of signals, +10.16%, 44.5% concentration). Percentage expectancy is identical
across sizing schemes (+10.42%), which is the check the re-weighting is correct.

**§3 65-75 DTE REJECTED.** +11.55pp on the first half, **+1.19pp on the second** against a
required +5pp. It inherits the very fade it was meant to arrest. Phase 2's +17.0% vs +7.8% was a
full-sample figure dominated by the early period. Live band stays 45-75. 35-delta remains
confirmed optimal and untouched.

**NOT DONE:** §2 (new ThetaData signals judged on the 2021-2025 fade - the core remaining
research), §4 (VRP/credit-spread arm + correlation with the long arm), §5 (options-bot fold-in -
also blocked, the code is on main and not in this worktree), §6 (live engine + tracked book +
annualized net-of-cost/after-tax returns). Roadmap 22b (small/mid-cap expansion) is explicitly
the iteration after this and needs a fresh ThetaData pull.

## OPTIONS PHASE 2 - tail analysis + spread comparison (2026-08-02)

**The phase-1 "too tail-dependent to size" verdict is CORRECTED.** The dollar concentration was
a position-sizing artefact: entry premiums span 1,076x, so 1 contract of a pre-split $3,000 AMZN
next to 1 of a $40 bank guarantees a few names dominate. At fixed $1,000 risk per trade the
top-15 share falls 98.1% -> 42.0% (idealised; 44-63% with whole contracts - see phase 3), profit ex-top-15 goes $2,767 -> $92,998, top-3 name
concentration 76% -> 34%, and total profit RISES to $160,461. **Size by fixed dollar risk, not
contract count.** Excluding the top 15 winners entirely, expectancy is still +8.96%/trade, and
30.7% of all trades returned >= +100% - big winners are common, not rare.

**No conviction tier ships.** A fingerprint fit on half 1 scored a 28.07% big-win rate on the
held-out half vs a 29.05% base and 29.04% random control (lift 0.966 vs a required 2.0). Worse
than random; fails every arm of the gate. The tail is unpredictable - 9 of the top 15 were 2020
AMZN/GOOGL/TSLA. Building a louder "scream-buy+" alert would have been false emphasis.

**Section 4 REJECTED:** matched vertical debit spread scores -4.46%/trade vs single-leg +12.33%
on 1,313 matched pairs, worse in every IV regime and both halves, and no better hit rate. The
+100% target is measured on the debit but a debit spread's max value is the strike width, so
targets sit at the ceiling while the -50% stop fires normally.

**STILL NOT DONE (mandate sections 3-6 of phase 2):** the new ThetaData signals (IV rank, VRP,
term structure, skew, tick flow, GEX); the VRP/credit-spread arm; the options-bot fold-in
(OPTIONS_BOT_INTEGRATION.md); and the live-engine + tracked-book wiring with annualized
net-of-cost and after-tax returns. Nothing in the live product has been changed.

## OPTIONS TRACK - scream-buy validated on real ThetaData (2026-08-02)

Full detail in `OPTIONS_BACKTEST_RESULTS.md`. 55 names, 2016-2025, **1,540 closed trades**, all
net of spread + commission at the punishing fill (buy ask / sell bid).

    hit rate 37.4%   avg win +120.4%   avg loss -55.3%   PF 1.30
    EXPECTANCY +10.4%/trade   cum $143,723 (1 contract/trade)
    held-out split: +16.4% (2016-2020) vs +4.4% (2021-2025) - positive in BOTH, bar met
    positive in 7/10 years; 2022, 2023, 2025 negative
    37 of 55 names positive

**THE DECISIVE CAVEAT: dollar P&L is tail-driven. Drop the best 1% of trades (15 of 1,540) and
$143,723 becomes $2,767; drop 5% and it is -$151,760.** Percentage expectancy is far more robust
(+10.4% -> +9.0% dropping the top 1%), because the book buys ONE CONTRACT per signal so
expensive contracts dominate dollars. **Sizing by fixed dollar risk instead of fixed contract
count is the obvious next test.**

Verdict: positive expectancy, survives costs, clears the pre-committed bar - but thin, fading,
and too tail-dependent to size aggressively. NOT "the scream-buy engine works". Nothing in the
live product was changed on the basis of it.

Useful sub-findings: realised stop loss is -59.1% not -50% (daily-mark trigger, worse fill);
the live 35-delta pick is the best of three delta buckets; 65-75 DTE more than doubles 45-55
(+17.0% vs +7.8%) and is a testable refinement, not yet gated.

**Infrastructure now in place** (all committed, tests 88/88):
- `theta_bulk.py` - year-chunked bulk loader, 4 concurrent, quarterly chunks with
  retry/backoff/timeout, resumable atomic cache in `data/options/`. Per name the pull went from
  280-640 calls to ~22; a full year of compute went from "did not finish in 500s" to 0.6s.
- `options_fill.py` - fill/cost engine. Honest fill is the DEFAULT (mid-fills are a diagnostic
  only), bad quotes rejected with named reasons, expired-worthless posts -100%.
- `blackscholes.py` - local greeks, validated against the vendor (delta 98.96%, IV 100% in the
  tradable band).
- `options_backtest.py` - reconstruction that CALLS the live alert + live scorecard functions,
  so backtest and forward tracker cannot diverge.
- `optbt_status.py` - progress + partial verdict at any time; `optbt_run.py` - the runner.

**Four silent bugs found and fixed** (each would have produced a confident wrong answer):
split-adjusted prices meeting unadjusted strikes; a failed FRED fetch retried every call (60s);
11 of 30 year-pulls failing with no retry and no record; and ticker renames (META/FB) silently
dropping six years.

**NOT DONE - mandate sections 4-6:** single-leg vs vertical spread (arm is built and committed,
not run), the new ThetaData signals (IV rank, VRP, term structure, skew, tick flow, GEX), and
the live-engine / tracked-options-book updates. Premium selling (CSP/covered calls) remains
deferred by the mandate as a separate short-vol track.

## P24.3 / P24.4 - USAspending REJECTED, congressional trades INCONCLUSIVE (2026-08-01)

This closes the alt-data question opened in P24: four external sources tested, four gates
pre-committed to git before any number came back, nothing adopted.

### USAspending federal contract awards - REJECTED

    signal                     median IC    IC t   dates   avg names   coverage
    govt_award_momentum          +0.0044   +0.70      62          89      4.03%
    govt_award_level (PLACEBO)   +0.0007   -0.52      62          96      4.34%
    -- POWER CONTROLS on the same restricted subset --
    inst_accum                   +0.0412   +2.27      50          90
    quality                      +0.0290   +1.61      62          88
    ret_6_1                      +0.0114   +0.78      62          88

**The power control earned its keep.** The FIRST run mapped only 89 tickers and produced a
70-ticker subset on which ret_6_1 fell from t +3.40 (full panel) to +0.83, with no control
clearing 2.0. By the pre-committed rule that was INCONCLUSIVE, and it was not written up as a
rejection. Going deeper into the recipient list (top 2,000 -> top 6,000) lifted the mapping to
137 tickers and the subset to 102, at which point inst_accum reached +2.27 and the null became
interpretable. Without that rule the thin first run would have been reported as "federal award
momentum does not work" on evidence that could not support the claim.

Limits that survive the verdict: coverage is 4%, so even a real signal there could not move a
broad book (it would have been a gov-exposure sleeve, not a composite change); and the
subsidiary problem is unsolved - no parent-rollup endpoint exists (parent_recipient /
recipient_parent / parent_duns all 404), so Electric Boat is still not credited to General
Dynamics. That adds noise, which biases toward rejection, so it does not undermine this null.

### Congressional trades - INCONCLUSIVE, explicitly NOT a rejection

    signal                     median IC    IC t   dates   avg names   coverage
    congress_net_buy             +0.0020   +0.97      49         314     11.27%
    congress_activity (PLACEBO)  -0.0040   +0.02      49         314     11.27%
    -- POWER CONTROLS on the same restricted subset --
    ret_6_1                      +0.0484   +1.87      49         313
    inst_accum                   +0.0230   +1.80      49         313

The signal shows nothing (t +0.97, and it would have to more than double to clear the bar), but
the subset cannot certify a null - the best known-real control reaches only +1.87 against a
pre-committed 2.0. So no verdict is claimed.

**The limit is TIME, not cross-section**, which says what would fix it. Coverage is healthy
(1,157 tickers, ~314 names/date - wider than the USAspending test that DID reach power). The
binding constraint is that the data starts 2014, giving 49 rebalance dates over a decade in
which momentum itself was weak. More tickers cannot fix that; only more years, which do not
exist.

**Point-in-time, now quantified rather than asserted.** Of 47,455 transactions, 21.9% were filed
late; days from trade to filing have a median of 29, a 90th PERCENTILE OF 210, and a max of
4,049. Using transaction_date injects up to SEVEN MONTHS of look-ahead for a tenth of the
sample, precisely during the window a member's presumed advantage would play out. The loader
DISCARDS the transaction date entirely rather than merely declining to filter on it, so it
cannot be reached later. Pinned by `test_congress_never_stores_transaction_date`.

**Second finding worth keeping:** the originally intended source (House/Senate Stock Watcher) is
defunct - S3 403, site dead - and its surviving GitHub mirror is Senate-only, stops in 2019, and
carries `transaction_date` as its ONLY date field. A test built on the first free dataset to hand
could not have been correct, and no field would have warned anyone. Source used instead:
kadoa-org/congress-trading-monitor, built from the official House Clerk and Senate eFD feeds,
which carries filing_date separately. The GATE (thresholds, orientation, placebo, power control)
was unchanged by the source switch.

### Where the alt-data question now stands

    source                  verdict        why
    FINRA short interest    REJECTED       t +1.04 vs 2.0; controls on the same window +3.53
    SEC EDGAR 13D/13G       REJECTED       activist t -0.69; passive placebo beat it by 2.35
    USAspending awards      REJECTED       t +0.70; subset had power (inst_accum +2.27)
    Congressional trades    INCONCLUSIVE   t +0.97 but no control cleared 2.0 on 49 dates

Nothing adopted. Three clean rejections and one honest inconclusive. Combined with the P6/P10
rejections, the standing conclusion is unchanged and now better supported: **the signal set is
saturated for this dataset, and free public alt-data did not add to it.** All eight signals stay
MEASURED (per-signal IC table) and score in no theme, so re-testing any of them is one line in
factors.py.

Tests 81/81.

### Recommended next step

The internal-research avenue is exhausted for now. The top priority remains what it was before
P24: **a forward paper-track vs SPY** - the edge has still only ever seen this one 18-year
Sharadar panel, and a live track on data nobody has looked at is the only remaining honest test.
That is Cowork's lane ("Valquo Index vs SPY").

## P24.2 - SEC EDGAR 13D/13G: TESTED AND REJECTED (2026-08-01)

352,332 filings -> 6,632 tickers from EDGAR quarterly form indexes (112s for 2007-2026).

    signal                  median IC    IC t   nonzero   coverage
    activist_13d              -0.0055   -0.69     4.56%      58.5%
    passive_13g (PLACEBO)     +0.0159   +1.66    18.59%      58.5%
    inst_accum (in the book)  +0.0314   +1.88        --      61.4%

    gate: standalone t >= 2.0              FAIL (-0.69)
          13D beats 13G placebo by >= 1.0  FAIL (-2.35)

**The activist signal came out NEGATIVE** - opposite to the direction fixed in advance - and the
PASSIVE placebo (the box index funds tick mechanically) outscored it by 2.35 t. Measuring 13D
alone would have given a bland "weak, rejected"; the pre-committed placebo gives a sharper
verdict: whatever these filings carry at a quarterly horizon, it is not activism creating value.
It also forecloses chasing passive_13g's +1.66, very likely a coarser echo of inst_accum (+1.88)
that the institutional theme already owns.

**Two silent-failure bugs caught, both now pinned by tests:**
1. The SEC RENAMED the forms during 2024 ("SC 13D" -> "SCHEDULE 13D"). The old spelling returns
   ~30 filings/quarter for 2025-2026 vs ~15,000 - the most recent panel dates would have carried
   a structurally-zero signal while looking perfectly healthy.
2. form.idx is nominally fixed-width but the column offsets have MOVED over EDGAR's history; a
   fixed-width parse scored 0/200 rows on 2015. Parsed by structure instead (98.6-99.5% across
   1998/2015/2024).

Honest deviation: the docstring specifies absence -> 0.0, but the panel wiring skips tickers with
no filing history at all, so coverage is 58.5% not ~100%. That made the test EASIER (the
never-filed mass is excluded) and activist_13d still went negative, so the verdict stands.

Point-in-time: only `Date Filed` is read - the public disclosure date. The event date (crossing
5%, up to 10 days earlier) is never parsed. Tests 79/79.

**Next - P24 items 3 and 4 are UNTOUCHED:**
- USAspending.gov contract awards (use the award ACTION/entry date)
- Congressional trades (use the PTR DISCLOSURE date, NEVER the transaction date - it lags up to
  45 days, and using the trade date would be look-ahead)

## P24.1 — FINRA short interest: TESTED AND REJECTED (2026-08-01)

Downloaded FINRA's consolidated short interest: **3,866,270 rows -> 48,539 tickers** (1,294s,
cached to `data/bulk/prepared/short_interest.pkl`). Two signals wired, measured, rejected.

    signal                    median IC    IC t   n_dates   gate (t >= 2.0)
    neg_days_to_cover           +0.0147   +1.04        33   FAIL
    neg_short_interest_chg      +0.0133   +0.42        33   FAIL
    -- controls, SAME 34-date window --
    ret_6_1                     +0.0643   +3.53        34
    inst_accum                  +0.0669   +3.27        34

**The controls are the point.** The pre-committed caveat was that 34 dates might be too few to
detect anything. They are not — on this exact window ret_6_1 shows at t +3.53. The window has
ample power to see an effect of that size, so t +1.04 is an absence of SIGNAL, not an absence of
EVIDENCE. That is a real verdict, not an inconclusive one.

Both signs came out as pre-committed (both median ICs positive). The orthogonality premise was
also correct and did not save it: neg_days_to_cover correlates only +0.048 with ret_6_1 and
+0.034 with inst_accum — genuinely new information, simply not predictive. It is -0.311
correlated with size, so days-to-cover partly re-expresses a size effect the book already has.

POINT-IN-TIME: FINRA exposes `settlementDate` and no dissemination field, so using it directly
would inject ~2 weeks of look-ahead. Every observation is stamped `settlementDate + 15 days` and
the raw settlement date is never returned to callers. Pinned by a test.

Coverage 90.4% within the 2018+ window (plumbing works); 40.0% of the full 110-date panel — a
data-availability ceiling, as FINRA publishes nothing before 2018. Standalone gate not cleared,
so the held-out comparison was not run. Both signals stay MEASURED, scoring in no theme.

Tests 78/78. Downloader and publication-lag machinery kept — correct and reusable; only more
history would change the verdict, and FINRA does not publish it.

**Next:** P24 items 2-4 untouched — SEC EDGAR 13D/13G (use FILING date), USAspending (award
action date), congressional trades (PTR DISCLOSURE date, never transaction date).

## Hot Stocks ⇄ Valquo Index unified, with a Roth/Taxable toggle — AND the UI is finally VERIFIED

**The blocker is gone.** `pip install flask werkzeug jinja2 openpyxl reportlab` (all already in
`requirements.txt` — it was purely a missing local env) means the app now imports, renders and
serves in tests. Everything shipped blind in earlier sessions is confirmed working:

| previously unverified | now |
|---|---|
| OG/Twitter meta tags | `GET /` → **200**, `og:image` present and **absolute** |
| signup/pricing gating | `/register` → 302, `/pricing` → 302, no signup CTA in the HTML |
| options endpoints | `/api/option-alerts/open` without a token → **401** |
| **`test_saas` suite** | **20/20 passing** — unrunnable for this entire project until now |

### One ranking, two views (no second index)

`/api/valquo-index?config=roth|taxable` builds the book from **the same snapshot the Hot Stocks
tab reads**, so the Index is a disciplined *slice* of the ranking rather than a competing
screen. A test pins that: the roth 25-name book is exactly the first 25 of the taxable decile,
and the Index never reorders the ranking.

The Hot Stocks tab now carries an **account-type toggle** (roth = top-25 / ~2-month / no band;
taxable = decile / quarterly / 20% band) and both blurbs — *Hot Stocks is the full ranked screen
(discovery)*, *Valquo Index is the disciplined, backtested book you would hold and track*.

**Gating fix found by a failing test:** `/api/valquo-index` was login-walled while
`/api/hotstocks` is a public read. Login-walling one view of a ranking while the other is open
makes no sense, so it is now public too — the endpoint, not the test, was wrong.

### What is NOT done, and the decision it needs

The scan still **sources Hot Stocks from the FMP snapshot**, not `score_universe_now`. Both
views now share one ranking, but that ranking is still the live-scan one. Pointing the scan at
the Sharadar full universe is a one-function change — the blocker is a real trade-off only Don
can settle:

* **Sharadar** is point-in-time and full-universe (2,827 names, the thing that was validated),
  but the export is a **static file, currently as-of 2026-07-24** — Hot Stocks would go stale
  between manual re-exports.
* **FMP** is live and daily, but is a smaller universe and is not point-in-time.

Recommendation: keep Hot Stocks on the live FMP scan for **discovery** (users expect current
data) and drive the **Index** off a periodic Sharadar scoring, since a book rebalanced every
~2 months does not care about a week of staleness. That keeps both honest without pretending a
weekly-stale screen is live.

---

## RESEARCH TRACK CLOSED — all three items tested, all three REJECTED

Every item got a gate committed results-free BEFORE it ran, and every one failed honestly. The
shipped model is unchanged: **nothing was adopted, and nothing needed to be un-adopted.**

| item | gate commit | verdict | headline |
|---|---|---|---|
| ML tree combiner | `620e0a5` | REJECT | OOS IC +0.0531 linear vs **+0.0393** GBM; net alpha −8.2pp roth / −4.0pp taxable |
| PEAD | `9323a08` | REJECT | `pead_car` t +2.21 standalone but fails the held-out margin **both** ways |
| Elite-manager 13F | `5a3ccfb` | REJECT | t **+1.32** vs a 2.0 bar, and *below* both signals already in the theme |

### Elite-manager 13F — the last swing

Built from 282,487 manager-quarters of quality, 235,271 **point-in-time** skill scores (a
manager's score at quarter *q* uses only quarters strictly before *q*), elite conviction for
13,110 tickers, via two bounded streaming passes over the 2.9GB SF3 file.

| signal | median IC | IC t | coverage |
|---|---|---|---|
| `sm_elite_conviction` | +0.0274 | **+1.32** | 58.5% |
| `sm_breadth` (already in theme) | +0.0204 | +1.73 | 61.4% |
| `inst_accum` (already in theme) | +0.0314 | +1.88 | 61.4% |

Weighting by manager track record moved conviction from t ≈1.26 → **1.32**: noise. It still
scores **below both signals already in the institutional theme**. The hypothesis that manager
identity carries information the crowd average lacks is **not supported**.

**This is not a plumbing failure** — the skill scores are real and point-in-time, and coverage
(58.5%) is near the ~61% ceiling that 13F starting in 2013 imposes. If revisited, the lever is a
better *definition* of elite (concentration, turnover, persistence of edge), **not** more careful
weighting of trailing returns, which is what failed.

### What this closes, and what it means

The ML result said the only lever likely to help was **new orthogonal data**. Two new-data swings
followed and both missed. Taken together the picture is consistent and worth stating plainly:
**the signal set is saturated for this dataset.** Value/quality/momentum/size/institutional over
18 years of quarterly Sharadar is what there is; more model capacity (ML), more of the same data
re-cut (PEAD from prices, 13F re-weighted) does not add to it.

The remaining levers are genuinely different data — the ones in VALQUO_NEXT_EDGE Tier 2 that were
never started: FINRA short interest, SEC EDGAR 13D/8-K, congressional trades, and IBES estimate
revisions (still parked, and the one thing that would make a *real* PEAD possible).

---

## PEAD — built and REJECTED (the decode that unblocked it stands regardless)

Gate committed results-free in `9323a08`. Signal = cumulative abnormal return over [t−1, t+1]
around the most recent announcement vs the benchmark (the surprise measured by the market's own
reaction, since we have no point-in-time estimates), plus a recent-only "drift" variant.

| signal | median IC | IC t | coverage | standalone gate |
|---|---|---|---|---|
| `pead_car` | +0.0100 | **+2.21** | 82.3% | PASS |
| `pead_drift` | −0.0020 | −0.47 | 25.1% | FAIL |

`pead_car` clears standalone but **fails the held-out margin in both directions** — early
+0.03 t / −0.08% alpha, late −0.09 t / −0.35% alpha. **REJECTED.**

**Two diagnostics that matter more than the verdict:**

1. **The drift variant has no signal.** PEAD theory says drift is *strongest* right after the
   announcement, yet the ≤63-day window scores **t −0.47** while the all-ages CAR scores +2.21.
   That is backwards — whatever `pead_car` measures, **it is not post-earnings drift**, so its
   +2.21 must not be read as evidence for PEAD.
2. **It is partly momentum we already own.** Within-date correlation **+0.286 with `ret_6_1`**,
   +0.241 with `high_prox`, +0.200 with `ret_12_1`. An earnings CAR from months ago is largely
   "this stock has been rising", which `ret_6_1` already captures at **t +3.40** — nearly double.
   Adding it dilutes a stronger signal with a weaker correlated one, exactly as the held-out
   numbers show.

Both variants stay **measured but score in no theme**, so the negative result is permanent and
re-testing is one line. A cleaner PEAD needs a real earnings *surprise* (reported vs expected),
which requires point-in-time estimates — IBES, still parked.

---

## EVENTS earnings-code legend DECODED — PEAD unblocked after being stuck since P2

Sharadar ships no legend with the EVENTS download, and the earlier guess (codes 11-17) was
wrong, so `bulk.EARNINGS_CODES` sat deliberately empty and `earnings_dates()` returned `[]`.
Rather than guess again, code **22** was identified by two INDEPENDENT signatures:

**1. Timing against the SF1 filing date.** Code 22 sits a median of **3 days BEFORE** the
filing with 46.4% of occurrences within ±3 days — the announce-then-file pattern a real
earnings release has. No other code comes close.

**2. Information content — the decisive test**, and the property PEAD actually needs. Median
absolute return on the event day, 372 tickers:

| code | events | \|ret\| on day | baseline | ratio |
|---|---|---|---|---|
| **22** | 17,996 | **2.121%** | 1.292% | **1.64×** |
| 91 | 48,207 | 1.482% | 1.293% | 1.15× |
| 71 | 14,258 | 1.459% | 1.288% | 1.13× |
| 81 / 52 / 11 / 34 / 57 | — | — | — | 0.84–0.98× |

Every other candidate is indistinguishable from a random day. `earnings_dates()` now returns
real dates (AAPL: 93 of them, cleanly quarterly — 2025-07-31, 2025-10-30, 2026-01-29,
2026-04-30).

**Coverage caveat, stated not buried:** code 22 appears ~2.83×/ticker/year, not the ~4 a full
quarterly calendar would give — EVENTS coverage of earnings is **partial**. Treat a missing
earnings date as *unknown*, never as "no announcement".

An existing test asserted `earnings_dates() == []` ("deliberately inert"). That behaviour was
correct while the legend was unknown and is now obsolete; the test was updated to assert the
new behaviour, and to check the OLD wrong guess (code 11) does *not* qualify.

---

## ML tree combiner — TESTED AND REJECTED on every criterion

Gate committed results-free in `620e0a5` before running. GBM over the 31 currency-correct
z-scored signals, target = cross-sectional rank of forward return, judged on the **same purged
CPCV paths** the linear weights face.

| metric | linear | GBM | delta |
|---|---|---|---|
| median OOS IC (15 paths) | **+0.0531** | +0.0393 | **−0.0138** |
| paths where GBM wins | — | **33%** | worse 2 in 3 |
| roth top-25 net alpha | **+10.27%** | +2.04% | **−8.23pp** |
| taxable decile net alpha | **+6.70%** | +2.66% | **−4.04pp** |
| roth net Sharpe | **0.99** | 0.68 | |

Both halves agree; the late half is brutal (roth **+16.31% → −4.48%**, −20.79pp). The one cell
where GBM wins — roth, early half, +3.86pp — is the classic signature of structure found in one
regime that does not survive into the next.

**The useful interpretation:** trees can *express* "value only pays when quality is high"; they
cannot *learn* it reliably from 110 dates of 8 themes. The linear composite is not leaving money
on the table — it is the right amount of structure for the evidence available. **Do not re-open
with a different model.** Re-open only with materially more data: longer history, higher
rebalance frequency, or genuinely new orthogonal features.

**A real bug found en route (kept):** sklearn's binner raised `window shape cannot be larger
than input array shape` because the 13F signals are empty before 2013-06-30, so an early CPCV
fold hands it an all-NaN column. The whole-panel coverage check passes *precisely because* the
later folds have data — the filter has to be **per-fold** (`_usable_features`). sklearn stays an
optional import (it is not in `requirements.txt`); a missing import returns a status dict.

---

## Valuation-regime overlay — REJECTED, harder than the trend filter

Rule + bar committed results-free in `f567d01` before running. Primary rule (**one** rule, not
three): market-cap-weighted earnings yield `sum(NI)/sum(mktcap)` per rebalance — summed, not
averaged, so one freak micro-cap cannot move it and loss-makers net off — risk-off when it sits
at or below its **20th percentile over all PRIOR dates** (expanding window, min 20 dates). An
absolute multiple would be hindsight: "over 20x is expensive" is a fact about the last 20 years
nobody knew in 1998. Median P/E and PEG were computed as **diagnostics only, explicitly not
alternative rules** — three rules would be three chances to get lucky on one episode.

| config | net ann | Sharpe | max DD | flips | invested |
|---|---|---|---|---|---|
| no overlay | +30.69% | 1.13 | −57.0% | — | — |
| off = 0% | +26.58% | 1.05 | **−57.0%** | 8 | 94% |
| off = 50% | +28.75% | 1.11 | **−57.0%** | 8 | 94% |

**Max drawdown does not move at all** — identical to three decimals in every configuration. The
rule fires on only 10 of 165 rebalances and never during the actual crash. Sharpe is worse in
**both** halves (early −0.07/−0.01, late −0.10/−0.04), and drawdown improves in neither.

**The mechanism is the failure the spec predicted:** while risk-off, the book returned
**+10.02% per period (+77.3% annualized)**. It sat out the *best* periods, not the worst.
*Expensive* and *about to fall* are different things, and an aggregate valuation percentile
picks up the former with no information about the latter. Unlike the trend filter there is not
even a tempting full-sample story to argue about.

**NOT ADOPTED.** `settings.VALUATION_REGIME_OVERLAY`, default off.

Two caveats on the reported levels (they do not affect the rule — a percentile against its own
history is invariant to a constant basis): the aggregate yield uses the panel's **quarterly**
ARQ net income, so the implied "P/E ~96x" is a quarterly-flow artifact (×4 ⇒ ~24x annualized,
which is plausible) and should not be quoted as a market P/E; and aggregate **PEG came back NaN**
because revenue growth is not persisted on panel rows — reported as unavailable rather than
approximated.

---

## Regime risk-off overlay — REJECTED, and the best argument yet for pre-commitment

The rule and its adoption bar were written and **committed in isolation (`bfbde7e`) before it
was run**, so the git history proves nothing was tuned to the outcome. Classic 200-day trend
filter: at each rebalance, benchmark close vs its own trailing 200-trading-day SMA (strictly
past closes); above → fully invested, at/below → risk-off exposure. Cash credited **0%**, which
is deliberately harsh — real bills paid 2–5% over this window, so the return give-up shown is
an overestimate.

**On the full sample it looks like an obvious adopt** (top-25, 42d, 165 rebalances):

| config | net ann | Sharpe | max DD | flips | invested |
|---|---|---|---|---|---|
| no overlay | +30.69% | 1.13 | −57.0% | — | — |
| off = 0% | +24.48% | 1.08 | −36.9% | 24 | 77% |
| **off = 50%** | +27.98% | **1.17** | **−37.0%** | 24 | 77% |

At 50% risk-off: drawdown **−57.0% → −37.0%** (20pp better), return give-up only **2.70pp**,
and Sharpe **improves** 1.13 → 1.17. **Both numeric criteria PASS.** I would have adopted it.

**The held-out criterion kills it:**

| half | base maxDD | off=50% | improvement | Sharpe Δ |
|---|---|---|---|---|
| early (has 2008) | −57.0% | −37.0% | **+20.0pp** | +0.18 |
| late | −34.8% | −34.8% | **+0.0pp** | **−0.08** |

**The entire benefit is one episode.** In the recent half it does nothing for drawdown and
*costs* Sharpe. That is exactly what criterion 3 ("must improve in BOTH halves — a rule that
only works in the half containing 2008 fits one episode") was written to catch, before any
number existed.

**Verdict: NOT ADOPTED.** Shipped as `settings.REGIME_OVERLAY`, **default `None` (off)** —
available to anyone who wants crash insurance and accepts paying for it the other ~90% of the
time. Whipsaw for the record: 24 flips over 165 rebalances (~15%), out of the market 23% of the
time.

**The transferable lesson:** a full-sample result that improves drawdown 20pp, costs almost no
return, AND raises Sharpe is exactly the shape of thing that gets adopted on sight. It took a
pre-committed out-of-sample rule to see that it was one crash wearing a strategy's clothes.

---

## Sector concentration cap — TESTED and REJECTED

A max-per-sector weight on the Roth top-25 (a concentration RISK control — **not** the
sector-NEUTRAL *ranking* rejected in P10, which re-scored every name against its sector peers;
this only skips a name once its sector is full and keeps composite order otherwise).

| cap | net α | Sharpe | max DD | Δ Sharpe | Δ maxDD | Δ α |
|---|---|---|---|---|---|---|
| none | +17.37% | 1.17 | −56.8% | — | — | — |
| 35% | +16.64% | 1.15 | −56.6% | −0.02 | +0.2pp | **−0.73pp** |
| 25% | +16.45% | 1.15 | −56.4% | −0.01 | +0.4pp | **−0.92pp** |

**REJECTED** — it costs 0.73–0.92pp of return and buys 0.2–0.4pp of drawdown and *negative*
Sharpe. No help in either half (none 1.12/1.20 · 35% 1.13/1.15 · 25% 1.11/1.18).

Two reasons *why*, which are more useful than the null: **the book is already diversified**
(mean max single-sector weight 27%, median 24%, above 35% on only 12% of dates, so the cap
rarely binds), and **the −56.8% drawdown is a market event** (2008–09), not a sector-
concentration event — capping sectors cannot help when everything falls together. If drawdown
is the worry, the lever is market exposure, not sector mix.

Sector is now persisted on panel rows and `max_sector_w` is a live parameter on both
backtests, so this is re-testable in one line if the book ever gets more concentrated.

---

## Options outcome API — the Cowork filler is unblocked

Two token-guarded endpoints (`X-Admin-Token`, same as the learning hook — the caller is a
scheduled process, not a browser):

- `GET /api/option-alerts/open?limit=N` → the work list of alerts awaiting outcomes.
- `POST /api/option-alerts/outcome` → one object or a list of
  `{alert_id | (ticker, alert_ts) | (occ_symbol, alert_ts), exit_premium, exit_ts, exit_reason,
  contracts}`. Returns `{written, failed, failures}` — an unmatched or already-closed alert is
  **reported, not silently dropped**, so the filler knows a write did not land.

**P&L is recomputed from the STORED entry premium**, never taken from the caller, so the
scorecard can never disagree with the prices the alert was logged against.

**Bug caught while writing it:** `store` inside `create_saas_app` is the **UserStore**
(accounts DB); `option_alerts` lives in the **screener** Store. My first version queried the
wrong database entirely. Both endpoints now construct the screener `Store()` explicitly, and a
test pins that source-level fact (flask is not installed here, so the routes cannot be
exercised at runtime — the endpoints are **runtime-unverified**, worth one curl after deploy).

---

## `roth` ADOPTED as the default book — and a cadence LABEL correction

`DEFAULT_BOOK_CONFIG = "roth"` (Don trades in a Roth, so no tax drag). The headless CLI takes
`--config roth` / `--config taxable`, which fixes width, cadence and band together so an
emitted book cannot drift from the construction that was validated:

```
python -m valuation.edge.valquo_index --full-universe data/backtest --config roth
  -> 25 of 861 eligible (1809 scored), rebalance every 42 trading days (~2.0 months), no band
```

**LABEL CORRECTION — the config is ~2 months, not 6 weeks.** `rebalance_days` is in TRADING
days, so 42d is ~8.4 calendar weeks. I had called it "6-week" in the previous handoff. Having
noticed, I measured the genuine 6-week point (30 trading days), which was never tested:

| cadence | Sharpe (full/early/late) | net α | turnover | cost drag |
|---|---|---|---|---|
| monthly (21d) | 1.09 (1.19/1.01) | +13.70% | 523% | 6.03% |
| 6-week (30d) | 1.11 (1.09/1.13) | +14.51% | 437% | 5.04% |
| **2-month (42d)** | **1.17** (1.12/**1.20**) | **+17.37%** | 379% | 4.40% |
| quarterly (63d) | 1.12 (1.17/1.06) | +14.99% | 300% | 3.35% |

**The construction Don adopted is still the right one** — 42d has the best Sharpe overall and in
the recent half. But a true 6-week cadence is *worse* than both its neighbours (1.11), so the
name mattered: anyone implementing "6 weeks" from the old note would have traded a worse book.
`taxable` is unchanged (decile / quarterly / 20% band).

---

## SCREAM-BUY OPTIONS: expectancy loop replacing the success-rate tracker

`options_exit.py` measured the UNDERLYING's move under an exit discipline. That answers the
wrong question twice: an option's P&L is not the stock's move (premium, theta and vega sit in
between), and a bare **"success rate" is meaningless for an asymmetric payoff** — a 40%-hit
setup whose winners triple beats a 70%-hit one that gives it all back on the losers.

New `valuation/edge/options_tracker.py` + an `option_alerts` store table:

1. **Log the CONTRACT and the fingerprint.** ticker, right, strike, expiry, entry premium,
   timestamp, plus what fired it: score, momentum/technical scores, IV and IV rank, horizon,
   target delta, DTE, options-flow read, labels, and a JSON `features` blob so a new feature
   never needs a migration. Deduped on (ticker, alert_ts, OCC symbol). Missing chain detail is
   allowed — the fingerprint is what the tuning loop learns from, so an alert with no strike is
   still worth recording.
2. **Score EXPECTANCY, never a bare hit rate:** hit rate *alongside* avg win, avg loss, profit
   factor, expectancy per trade, and cumulative P&L on a fixed 1-contract (100-share) basis.
   Profit factor with no losers reports **None, not infinity** — an undefined ratio must read as
   "no evidence", never as a spectacular score.
3. **Accrual-then-tune, hard-gated.** `MIN_CLOSED_PER_BUCKET = 30` on **both sides** of any
   comparison before a criterion may change. `tuning_candidates()` returns suggestions and never
   applies them, and lists what is `blocked` for want of trades. Options outcomes are
   heavy-tailed: with ten trades one triple-up decides the sign of every statistic.
4. **Surfaced on the Signals tab** (`/api/options-scorecard`), with thin buckets greyed and
   flagged, and an explicit "not enough closed trades to tune" line when below the floor.

**Cowork's half:** real fills and contract marks come from the Robinhood connector, which the
web app cannot reach. This app writes the alert; an external scheduled job calls
`record_outcome(...)` to fill `exit_ts / exit_premium / exit_reason`, and P&L is computed
**here** from the stored premiums so the scorecard can never disagree with them. Everything is
built to be useful while outcomes are still missing — an open alert is a complete record of the
setup, and the scorecard reports honestly how few closed trades exist.
→ **Take the outcome-filling job to the Cowork chat.**

---

## TWO SHIPPED BOOK CONFIGS — concentration chosen on Sharpe, not return

`settings.BOOK_CONFIGS` now carries two tuned constructions, and the run measures both
(`book_configs` in BACKTEST_RESULTS.json).

### Why risk-adjusted, in one table

| width | net α | net Sharpe (full / early / late) | max DD | turnover |
|---|---|---|---|---|
| top 5 | +7.20% | 0.68 / 0.92 / 0.54 | −50.2% | 336% |
| top 10 | **+20.19%** | 1.12 / 1.35 / 0.93 | −24.5% | 322% |
| **top 25** | +14.99% | **1.12 / 1.17 / 1.06** | −38.6% | 300% |
| top 40 | +12.85% | 1.10 / 1.14 / 1.05 | −37.0% | 286% |
| decile | +11.44% | 1.11 / 1.19 / 1.02 | −41.7% | 251% |

Ranking on raw alpha would have picked **top 10 (+20.19%)** by a mile — its Sharpe is a dead
tie with top 25. And **top 5 is the clean lesson**: worst return *and* worst risk.

**top 25 chosen over top 10** on stability: top 10 swings 1.35 → 0.93 across halves (gap 0.42)
vs top 25's 1.17 → 1.06 (gap 0.11), and top 25 **wins the recent half outright**. top 10's
better max drawdown is real in both halves and is the tighter alternative if wanted — but a
10-name book over 110 periods is a thin basis for a drawdown claim.

### `roth` — tax-free, Sharpe-optimal, full rotation
**top 25, 6-week rebalance, no band.** Net alpha **+17.37%**, net Sharpe **1.17**, turnover 379%.

Frequency swept (top 25, net of cost): monthly **1.09** (1.19/1.01) · 6-week **1.17**
(1.12/**1.20**) · quarterly **1.12** (1.17/1.06). Faster *does* pay — but only to a point:
monthly's 6.03% cost drag overwhelms the benefit. 6-week is best on the full sample **and** in
the recent half, with the smallest early/late gap.

Note: **fundamentals only update quarterly**, so a 6-week rebalance re-ranks on fresh prices
(momentum, market cap) over stale fundamentals. That it still wins says the price-based
components carry real short-horizon information.

**Correction worth carrying: max drawdown is NOT comparable across frequencies.** A quarterly
grid observes the equity curve 110 times vs monthly's 330, so a coarser grid systematically
UNDERSTATES drawdown. Quarterly's −38.6% vs 6-week's −56.8% is substantially a sampling
artifact — do not read it as lower risk.

### `taxable` — after-tax-optimal, decile + 20% band
**decile, quarterly, 20% no-trade band.** After-tax alpha **+4.86%**, after-tax Sharpe **0.89**
(vs 0.84 unbanded), turnover 172%.

Tax drag (7.8%/yr) is over 3× the trading cost, so this optimizes after-tax Sharpe, which
favours breadth plus the band. **The band failed the pre-committed held-out margin in one half
(see below), so it is enabled HERE — for the account where it actually matters — rather than
made the global default.**

**Method bug I caught mid-sweep:** my first band sweep silently applied the band *only* to the
decile row — `exit_frac` is a fraction of the UNIVERSE and is meaningless for a fixed-N book, so
every fixed-N "with band" row was a duplicate of its no-band row. Added `exit_mult` (band as a
multiple of book size) so fixed-N books can be banded too. With it: decile+2.5× **0.89**,
decile+20% **0.89**, top-25+2.5× 0.88.

---

## git_push.bat now auto-lands finished agent branches (no more manual merge)

Claude Code works on `worktree-*` branches because its harness will not push to `main`, so every
session ended with a hand merge. `git_push.bat` now merges them itself before committing:
**fast-forward ONLY**, and only where `main` is already the branch's ancestor — which cannot
conflict and cannot rewrite history. Anything not a clean FF prints `[skip] <branch>` and is left
for you. One `.\git_push.bat` now lands and deploys.

Verified in a scratch repo, not just eyeballed — which mattered: **the first two versions were
broken** (`--format` paren escaping, then nested quotes inside `for /f '...'` needing `usebackq`)
and both of my first two *test setups* were wrong too. Final form merges the FF branch and leaves
a diverged one untouched.

---

## No-trade band — measured, and it FAILS the pre-committed gate (kept OFF, but read this)

Today a name is sold the instant it leaves the top decile. A band enters on the top 10% and
holds until the name falls past X. Full universe, 110 dates:

| exit band | turnover | gross α | net-of-cost α | **after-tax α** | cost drag | tax drag |
|---|---|---|---|---|---|---|
| none (10%) | 251% | +13.76% | +11.44% | +3.63% | 2.32% | 7.81% |
| 12% | 232% | +13.66% | +11.51% | +3.83% | 2.15% | 7.68% |
| 15% | 206% | +12.77% | +10.86% | +3.78% | 1.91% | 7.08% |
| **20%** | **172%** | +13.32% | **+11.69%** | **+4.86%** | 1.62% | 6.83% |
| 25% | 148% | +11.93% | +10.52% | +4.40% | 1.41% | 6.12% |
| 30% | 129% | +11.97% | +10.72% | +4.70% | 1.25% | 6.02% |

**20% is the knee**: turnover −31%, gross alpha −0.45pp, net-of-cost **+0.25pp**, after-tax
**+1.23pp (a 34% relative gain)**. Long-short t is unchanged by construction (3.396) — it
measures the whole cross-section, not the book.

**Held out, it does not clear the margin.** Applying the same split discipline to the metric that
actually moves (after-tax alpha, since `quantile_backtest` cannot see turnover):

| half | no band | 20% band | Δ | |
|---|---|---|---|---|
| early | +6.82% | +7.42% | **+0.60%** | fail (< 1% margin) |
| late | +0.88% | +2.76% | **+1.88%** | pass |

**Verdict by the pre-committed rule: `not_replicated`. Left OFF.**

**But it differs from every other rejection this project has made, and that is worth weighing:**
it is **positive in both halves** and never hurts — sector-neutral and zeroing `insider` each hurt
in one direction. And the turnover reduction (251%→172%) is **mechanical, not estimated**: it is
an arithmetic property of the rule, so the cost saving is deterministic in a way a signal's IC
never is. The margin it fails was calibrated for *signals*.

I did not flip it on, because quietly re-reasoning past my own gate is the failure mode the gate
exists to prevent. **Recommendation: adopt at 20%** — `exit_frac=0.20` in `turnover_and_costs` /
`after_tax_backtest`, and the band sweep now ships in `BACKTEST_RESULTS.json` under
`no_trade_band` every run. Your call.

**Caveat on the width:** the surface is noisy — 15% is worse than both 12% and 20% on gross alpha,
which should not happen on a smooth tradeoff. Do not over-trust the exact number; 20% is the best
point measured, not a precisely located optimum.

---

## Signup + Pricing hidden behind a flag (no paid tier exists yet)

The site was still showing "Sign up" and "Pricing" with nothing to sell. Both are now gated on
**`CONFIG.signup_enabled`** — a flag, not a deletion. Every route, template and Stripe path is
intact.

It **reuses the existing free-mode flag** rather than inventing a parallel one:
`signup_enabled` defaults to `not OPEN_ACCESS` (open/free product → nothing to sign up for),
with **`FEATURE_BILLING`** as an explicit override in either direction.

| config | signup/pricing visible | Stripe checkout |
|---|---|---|
| `OPEN_ACCESS=true` (today) | **no** | no |
| `OPEN_ACCESS=true`, `FEATURE_BILLING=on` | yes | no |
| `OPEN_ACCESS=false` | yes | needs a Stripe key |

**To re-enable later: set `OPEN_ACCESS=false` (or `FEATURE_BILLING=on`) in the environment.
No code change.**

Gated at the **route** as well as in the templates — `/register` redirects to `/app` and
`/pricing` to `/`. Hiding a button leaves the URL reachable from a bookmark, a stale link or a
search result, and a half-gated signup would create accounts the product no longer expects.

Surfaces changed: nav Pricing link and "Get started" CTA, footer Pricing link, both landing
CTAs, the beta banner's "Create free account", the login page's "No account?" line, and the
account page's "Upgrade" button.

**Deliberately NOT gated: login.** Existing accounts (including Don's) must still be able to
sign in when new signups are hidden. Anonymous visitors get **"Open the app"** instead, which is
accurate — `OPEN_ACCESS` already means no account is required for anything.

Two tests pin it: the flag truth table, and a sweep asserting no template carries an ungated
`/register` or `/pricing` link (an ungated button would now silently bounce a visitor, since the
routes redirect).

---

## P9b — headless book generation (`--full-universe`)

`python -m valuation.edge.valquo_index --full-universe [DATA_DIR]` now builds the book by
scoring the **whole Sharadar universe point-in-time** instead of the last live-scan snapshot.
The store path is what produced the degraded book: a few hundred scanned names means a "top
decile" collapses to the 10-name `MIN_NAMES` floor — ten mega-caps wearing a decile's label.

Verified end-to-end: **86 positions from 861 eligible large caps, 1,809 scored, as of
2026-07-24**, no live API needed, so the Cowork quarterly rebalance can run unattended. The CLI
also warns when `n_scored < 200` and prints any names excluded for unverifiable market cap
(this run: FFAI 5x, IQMX 0x, LESL 8x).

---

## P10 — sector data unblocked, and industry-relative ranking REJECTED on its merits

**The download worked.** Sharadar TICKERS, one paged API call, cached like the bulk tables:
**48,925 tickers**, 11 sectors, plus country/exchange/category. **Sector coverage is 100.0%
(2,826 of 2,827) of the panel universe**, so `sector_neutral` — which had been grouping on a
constant `""` and was therefore INERT in every backtest ever run — is now functional.

**Then it failed the test.** Sector-neutral scoring rebuilds every z-score, so it is not a
weight change and `holdout_theme_validate` cannot express it; `holdout_compare_panels()` applies
the same discipline in the right shape (split by time, embargo the boundary, require the
**already-committed** `MIN_HOLDOUT_*` margin in BOTH directions):

| split | long-short t | top-decile alpha | |
|---|---|---|---|
| early half | 0.56 → **0.97** (+0.41) | +6.69% → +6.53% (**−0.16%**) | fail |
| late half | 0.83 → **0.61** (−0.22) | +5.06% → +4.44% (**−0.62%**) | fail |

**Verdict: REJECT.** It never clears the margin, and in the later half it is worse on both
metrics. `sector_neutral` stays **off**. The capability is now real and re-testable — a future
change (e.g. sector-relative applied to only the value theme) can be tried without re-doing the
data work.

**Look-ahead caveat, stated not hidden:** TICKERS carries *today's* classification, so applying
it to a 1998 row assumes the company was in the same sector then. Reclassification is rare and
not return-predictive, so this is normally considered benign — but it is **the one non-PIT input
in an otherwise strictly point-in-time panel**, and that is a reason to be *more* sceptical of a
positive sector result, not less. It rejected anyway, so nothing rests on it.

### The remaining ADRs in the book are genuinely cheap — not residual artifacts

With country/exchange/category finally available: ADRs are **270 of 2,827 (9.6%) of the universe
and 9 of 86 book positions (12.4% of weight)** — 1.3x representation, against 28.3% before the
currency fix. Measured against the 1,164-name large-cap cohort:

| name | book_to_price | earnings_yield | ps |
|---|---|---|---|
| WDS (Woodside) | 0.98 (97th pct) | — | — |
| SKM (SK Telecom) | 0.71 (91st) | 0.017 (80th) | 4.29 (12th) |
| TTE (TotalEnergies) | 0.75 (92nd) | 0.032 (96th) | 2.98 (8th) |
| VOD (Vodafone) | 1.85 (99th) | — | — |
| IX (Orix) | 0.66 (88th) | 0.008 (48th) | 7.42 (25th) |
| ZTO | 0.53 (81st) | 0.018 (82nd) | 8.89 (31st) |

Cheap on book, earnings AND sales simultaneously — real value names. **One exception: TSEM is
expensive on all three** (24th / 18th / 95th percentile) and is in the book on other themes, not
value. Worth an eye, but it is a single ~1% position.

---

## P7 — CURRENCY FIX. The value theme was corrupt for foreign names; fixing it IMPROVED the model.

`marketcap` and `ev` are USD, but the raw line items are in the company's REPORTING currency.
Every value ratio dividing one by the other was wrong for the 4.1% of panel rows reporting in a
foreign currency — and all were pushed the SAME way, toward fake cheapness: SK Telecom's
`book_to_price` computed to **892 against a true 0.589** (~1,500x).

### Full 2,710-name universe, before vs after

| metric | BEFORE | AFTER | |
|---|---|---|---|
| **PBO** | 13.33% | **6.67%** | halved |
| Deflated Sharpe | >99.9% | >99.9% | saturated, unchanged |
| **Top-decile alpha** | +11.77% | **+11.82%** | +0.05pp |
| **Monotonicity** | −0.9394 | **−0.9515** | better-ordered |
| Net alpha (after costs) | +11.41% | +11.44% | +0.03pp |
| Long-short t | 3.485 | 3.396 | −0.09 |
| Breakeven | 235.6bps | 235.4bps | flat |

**All six value inputs improved** — book_to_price +0.07→+0.15, earnings_yield +2.33→+2.41,
fcf_yield +3.16→+3.17, ebit_ev +2.24→+2.29, neg_ev_sales +2.00→+2.11, neg_ps +1.40→+1.51 —
lifting the **value theme t from +1.34 to +1.46**. Six for six in the same direction is a
coherent pattern, not noise, and confirms the audit's hypothesis that contamination was part of
value's weakness.

The headline barely moves because value is 1 of 7 weighted themes and only 4.1% of rows were
affected. The real wins are PBO halving and the foreign distortion disappearing.

### Foreign-name share of the top decile

| | share of top decile | universe | over-representation |
|---|---|---|---|
| BEFORE | 4.79% | 3.54% | **1.35x** |
| AFTER | 1.98% | 3.54% | **0.56x** |

From 35% over-represented to 44% under-represented — what correct ratios imply, since these
names are expensive on real numbers (TSM PE 34.8, SKM PE 61.5).

**In the live book the effect is far larger** (large-cap AND value-tilted, so it concentrated
the distortion): foreign names fell from **21 of 86 positions / 28.3% of weight to 11 / 10.7%**,
and the top 10 went from **7 ADRs to 1**.

### Two corrections to CODE_AUDIT.md itself

1. **`neg_ps` is broken too — the audit marked it "ok".** It assumed `ps` came from Sharadar's
   ratio column; the panel computes `ps = market_cap / revenue` itself (USD/local). SKM's `ps`
   was **0.00 against a correct 5.13**. Fixed. Outside the letter of the task, inside its
   intent — leaving one value input corrupt defeats the purpose.
2. **`fxusd` is a DIVISOR, not a multiplier.** It is LOCAL UNITS PER USD (SKM 1514.2 won/USD).
   The audit's suggested `fcf × fx` would have SQUARED the error (~2.3 million x for SKM).
   Verified `equityusd/equity == revenueusd/revenue == ebitusd/ebit == 1/fxusd` exactly. Also
   there is **no `netincusd` column** — `netinccmnusd` (income to COMMON) is the right numerator
   against market cap anyway.

`total_equity` deliberately stays local: `gp_on_capital` divides local gross profit by it and is
only correct while both sides share a currency. `book_to_price` is now computed in the panel in
USD, with `build_frame` preferring the supplied value.

---

## P8 — SANITY LAYER. Coverage says a factor is PRESENT; this says it is SANE.

Four foundation bugs have now shipped with one signature: the run completes, raises nothing, a
factor is silently wrong. `signal_coverage` catches only the two that left a column EMPTY. The
currency bug filled every column and was simply incorrect.

`sanity_check()` ships a `sanity_check` block in BACKTEST_RESULTS.json: **range** (ratio factors
inside a plausible band), **subgroup** (does an identifiable subgroup systematically peg a
factor), **market_cap** (DAILY vs shares × price divergence).

### Validated against the bug it was built for

On PRE-fix values the subgroup check flags `book_to_price` and `earnings_yield` — foreign
reporters sat at the **86th percentile** of both. Post-fix every value factor lands in
**0.49–0.61**. **P8 would have caught P7 on its first run.**

Bands were CALIBRATED against known-bad vs known-good values on the same rows, not guessed. My
first attempt flagged 6.1% of good rows because **negative book equity is legitimate**.
`ev_sales`/`ps` are exempt from range checks — their tails are real near-zero-revenue companies
and the band flagged identical shares before and after the fix, a pure no-op. The subgroup check
covers them.

### It fires twice on CORRECTED data. Both true; neither a currency bug.

1. **`neg_log_mktcap`, foreign reporters at the 20th percentile** — real and expected, foreign
   companies with US listings are large. A true subgroup tilt, not a defect. **Left flagged
   rather than exempted:** silencing a guard after seeing it fire is how it becomes decoration.
2. **1.45% of rows with DAILY market cap >3x from shares × price** — AIV 71x, EQC 53x, genuine
   recycled-ticker cases (AIV/AIRC spun off 2020).

### The audit's M2 (SanDisk/WDC) does NOT reproduce

The task assumed this check would catch SNDK/WDC. **It does not, and that case appears not to be
this bug:**
- SNDK's DAILY cap ($336.7B) and shares × price ($212.7B) agree to **1.6x** — inside any sane
  band. WDC 1.2x.
- Its **148M share count is plausible**.
- Its price ran **48.60 → 1436.56 over 17 months with ZERO day-over-day discontinuities**; WDC
  10.3x and MU 8.5x over the same window — the whole storage complex moved together.

The figure is internally consistent. If still wrong, the error is upstream in the PRICE, which
both estimates share and **no cross-check between them can see**. Recorded as unresolved rather
than claimed as fixed: the audit asserted "~10x reality" from outside knowledge, and nothing in
the data marks it as an error.

**In the live book**, names diverging >3x are now DROPPED — a book is meant to be traded, and a
name whose size cannot be established should not be in it. 3 dropped: FFAI (5x), IQMX (0x), LESL
(8x). SNDK/WDC are not among them and remain. The BACKTEST keeps such rows and only flags them,
so validated history is never silently re-cut by a later guard.

---

## A full run was lost to my own bug, and the guard that followed

`sanity_check`'s warning path wrote to the `sys` MODULE instead of `sys.stderr`. That
`AttributeError` was swallowed by `run_backtests`' blanket `except`, skipping CPCV, construction,
walk-forward and regime — and the run still wrote a canonical BACKTEST_RESULTS.json with **every
metric null**, exit code 0. It reads as "ran, found nothing" rather than "broke": this project's
recurring failure signature, reproduced by me.

Hardened rather than merely fixed: an **`errors` block** in the JSON and a **DEGRADED RUN
banner** in the markdown whenever a validation block throws. Plus a test exercising the WARN
path — my tests all called `warn=False` and never touched the branch that raised.

**Tests: 121 passing** (edge 63, bulk 13, engine 19, intraday 13, screener 13).

---

## P6 — IS IT TRADEABLE? Yes. Three refinements tested, all three REJECTED.

**The headline: the edge survives realistic trading costs with a ~6x margin.** Everything
else in P6 was a proposed improvement, and none of them improved anything — which is a
useful result, because two of the three were my own recommendations.

### P6.1 — COSTS. The edge is tradeable. (KEPT: the measurement is now permanent.)

Every performance number in this project had been gross of costs, and zeroing `low_risk` in
P5 tilted the book smaller-cap, which is where costs bite hardest.

| book | annual turnover | gross alpha | net alpha | cost drag | **breakeven one-way** |
|---|---|---|---|---|---|
| top decile | 249% | +13.71% | **+11.41%** | 2.30%/yr | **236 bps** |
| top 25 | 296% | +20.69% | **+17.34%** | 3.35%/yr | **293 bps** |

The weighted-average one-way cost of what the book actually holds is **37 bps**, so breakeven
sits at a **~6.4x margin**. Even a punitive flat 100 bps still leaves +7.74% net alpha.
Turnover is high (~62% of the book per quarter) but nowhere near enough to eat the edge.

**The short side does not break it either** — the thing most likely to. The BOTTOM decile is
*larger*-cap than the top (median $4.50B vs $1.95B) and cheaper to trade (29.8 vs 37 bps), so
the long-short t = 3.49 is not resting on unborrowable micro-caps. Only 17% of the long book
sits under ~$500M.

Both method choices are deliberately unfavourable to the strategy: turnover counts weight
DRIFT between rebalances (not just entries/exits), and only the strategy is charged while the
equal-weight benchmark is left gross. **Borrow cost is NOT modelled** — it affects the
long-short statistic, not the long-only book, which is the thing anyone would actually trade.

Quote the **breakeven**, not the net alpha: it needs no belief in any particular cost
calibration. Runs on every backtest now, as a `costs` block and a Tradeability table.

*Annualization caveat:* these figures compound; `construction.*` annualizes arithmetically.
Same data, +13.7% vs +11.8% gross alpha. Compare cost numbers to cost numbers.

### P6.2 — TTM ROE/ROIC: REJECTED. The quarterly figure is BETTER.

Head-to-head on identical rows in one run:

| signal | median IC | IC t | coverage |
|---|---|---|---|
| **roe** (quarterly) | **+0.0439** | **+2.84** | 93.4% |
| roe_ttm | +0.0279 | +2.01 | 91.0% |
| **roic** (quarterly) | **+0.0420** | **+3.38** | 96.7% |
| roic_ttm | +0.0354 | +2.57 | 94.2% |

Smoothing over four quarters LOSES signal on both. The likely reason is **recency**: last
quarter's profitability predicts the next quarter better than a smoothed year does, and that
outweighs the fiscal-quarter seasonality TTM removes.

**This contradicts my own P5 recommendation**, which called quarterly ROE/ROIC a
methodological wart and TTM "the obvious next refinement". It isn't — the ARQ quarterly
figure is an advantage. Section 5.6 of the P5 notes below is superseded.

Both TTM variants stay MEASURED (in `NUMBER_THEME`, in the IC table) but do not score, so the
negative result is permanent and re-testing is one edit.

### P6.3 — median/MAD robust z-scores: REJECTED, and the reason matters more than the verdict.

| metric | classic (shipped) | robust |
|---|---|---|
| long-short t | **3.485** | 1.721 |
| long-short ann | **+17.58%** | +8.42% |
| top-decile alpha | **+11.77%** | +8.99% |
| monotonicity | **−0.939** | −0.624 |
| net alpha | **+11.41%** | +8.34% |
| PBO / DSR | 0.1333 / 1.0000 | identical |

The long-short t **halved** — while every individual theme IC stayed essentially unchanged
(quality +3.39 → +3.35, momentum +2.62 → +2.68, value +1.34 → **+1.68**).

**Why: rank-IC is invariant to a monotone rescaling; the composite is not.** Theme IC is a
Spearman correlation and literally cannot see this change. The composite is a weighted SUM of
z-scores and is very much scale-sensitive. MAD < SD for fat-tailed data, so dividing by the
smaller scale INFLATES the tails, and the top decile then gets selected by whoever has one
extreme factor reading rather than broad strength across themes. **Making the scale estimate
robust made the selection less robust.**

Generalizable lesson: **a signal's IC can be flat while the composite built from it moves a
lot.** Judging this change by per-signal IC would have called it harmless; it costs half the
long-short t. Kept behind `VALQUO_ROBUST_Z` (default off) so the result is re-testable.

### P6.3b — industry-relative ranking: BLOCKED, no sector data exists.

`fundamentals.csv` has **no sector / industry / SIC column**, and the panel hard-codes
`"sector": ""` on every row — so `build_frame`'s `sector_neutral` path has been **inert in
every backtest ever run** (it groups on a constant). The metadata lives in Sharadar's
**TICKERS** table, which is API-only and not among the four bulk tables on disk.

To unblock: one TICKERS download → a ticker→sector map → populate `metrics["sector"]` in
`_sf1_to_metrics`. Not fetched here because it is an outward-facing call on Don's paid
subscription. **Caveat to carry:** TICKERS gives *today's* classification, so applying it to
1998 rows is a mild look-ahead. Sector reclassification is rare and not return-predictive so
this is normally considered benign, but it should be stated rather than hidden.

### P6.4 — consolidating momentum + institutional: REJECTED. Both earn full weight.

They are +0.50 correlated, so the hypothesis was that we pay two theme weights for one
signal. Tested on the full sample and both halves (the composite is a weighted sum, so giving
the pair 0.0625 each IS a merged theme at 0.125 — no code change needed):

| config | full LS t | full top-decile | net alpha | early t | late t |
|---|---|---|---|---|---|
| **A current (.125 / .125)** | **3.48** | **+11.77%** | **+11.41%** | 2.57 | 2.56 |
| B consolidated (.0625 each) | 2.53 | +9.21% | +8.10% | 2.01 | 1.59 |
| C momentum only | 2.86 | +10.64% | +10.18% | 2.57 | 1.29 |
| D institutional only | 2.33 | +9.40% | +7.16% | 1.70 | 1.81 |

+0.50 correlation still leaves ~75% of variance unshared: they are **complementary, not
redundant.** A useful cross-check falls out — in the early half A and C are *byte-identical*,
because `institutional` has no data before 2013-06-30, independently confirming its 61.4%
coverage. In the late half, where it does have data, A beats both single-theme variants
decisively.

### P6.0 — the holdout threshold was pre-specified, and it changed two verdicts

`MIN_HOLDOUT_ALPHA_GAIN = 0.01` (100 bps/yr — an economic floor: an "improvement" smaller
than the cost of implementing it cannot be harvested) and `MIN_HOLDOUT_TSTAT_GAIN = 0.25` (a
noise floor). **Committed in isolation, before any P6 run** (commit `4de6e71`), so the git
history is the proof of when it was fixed. Disclosed honestly: I already knew the P5 numbers,
so this is a principled tightening rather than a blind pre-registration.

Effect, exactly as designed: `capital_discipline` went **confirmed → not_replicated** (it had
only ever passed on ΔLS t +0.01) and `insider` went **not_replicated → rejected**. `low_risk`
remains the only **confirmed** theme — the only one clearing a real margin in both directions.

### P6 net effect on the shipped model: NOTHING CHANGED

Three proposed improvements, three rejections. The model is byte-identical to the end of P5
(PBO 0.1333, DSR 0.999999, long-short t 3.485, top-decile +11.77%). What P6 added is
**knowledge**: the edge is tradeable, and three plausible refinements are now measured dead
ends rather than open questions. Two of the three were my own prior recommendations.

---

## 0. HEADLINE — five factors were silently empty, and fixing them changed the verdict

Every backtest this project has ever run scored on **8 of quality's 10 inputs, 1 of
low_risk's 2, and 1 of growth's 2.** No error was ever raised. The factors were wired, the
runs completed, and the columns were blank.

After fixing that and acting on what the corrected numbers said, on the **full 2,710-name ×
110-date universe** (identical universe in every run below — 136,478 rows, 63d validated
horizon, same 16.55%/yr equal-weight bar):

| metric | baseline (P4) | final | want |
|---|---|---|---|
| **PBO** | 40.0% | **13.3%** | <50% |
| **Deflated Sharpe** | 71.7% | **~100%** | >95% |
| **Long-short ann** | +8.13% | **+17.58%** | positive |
| **Long-short t** | 1.175 | **3.485** | >2 |
| Long-short hit rate | — | 66.4% | >50% |
| **Monotonicity** | −0.782 | **−0.939** | −1.0 is ideal (see §4) |
| **Top-decile alpha** | +5.11% | **+11.77%** | positive |
| Portfolio CAGR | +15.45% | +27.91% | — |
| Alpha vs equal-weight | +1.49% | +13.95% | — |

**This is the first time the project has cleared both statistical bars** (PBO < 50%,
Deflated Sharpe > 95%, long-short t > 2) — **and the biggest single contributor, zeroing
`low_risk`, has since been CONFIRMED on a held-out time split in both directions (§4b).**
Read §5 for what that does and does not establish.

Also: **the edge no longer collapses without 13F.** Strip the institutional theme and
top-decile alpha goes +11.77% → +10.64% with long-short t 3.48 → 2.86. At baseline the same
test collapsed the t to 0.71. The "the entire edge is 13F" finding in CLAUDE.md is now
**obsolete** — that was an artifact of quality and low_risk running on half their inputs.

**Every change was kept only after confirming it improves the full-universe combined edge**
(long-short t / Deflated Sharpe / PBO / top-decile alpha). The one change that did not pass
on first measurement — dropping `neg_asset_growth` — was re-tested head-to-head in the final
configuration and does pass (§3c). The derived inputs (§3a) are a **correctness fix, not an
optimization**: they cost 0.22 of long-short t while improving PBO, DSR and top-decile alpha,
and the alternative is knowingly scoring on 8 of 10 quality inputs.

**Tests: 107 passing** (edge 50, bulk 12, engine 19, intraday 13, screener 13). `test_saas`
(18) cannot run here — no `flask`/`werkzeug` installed in this environment, unrelated to
these changes and true before them.

---

## 1. The bugs — all five produced a completed run and no error

The export is **ARQ-only**, and Sharadar populates its averaged/ratio fields only in the
ART/ARY dimensions. Verified directly against `fundamentals.csv`: `roe`, `roic`,
`assetturnover`, `roa`, `ros`, `equityavg`, `assetsavg` are **non-null in 0 of 197,265
rows.** The raw ingredients were all present (`netinc` 97.7%, `equity` 99.9%, `invcap`
99.9%, `taxexp`/`ebt` 97.7%, `assets` 100%).

1. **`roe` empty** → derived as `netinc / equity` (requires equity > 0; a negative book value
   inverts the sign and would rank a wiped-out loss-maker as the highest quality name).
2. **`roic` empty** → derived as `ebit × (1 − effective tax) / invcap`, effective rate =
   `taxexp / ebt` clipped to [0, 0.60], falling back to the **date-aware** statutory rate
   (35% pre-2018, 21% after — the TCJA cut) when pre-tax income ≤ 0 makes the rate
   meaningless.
3. **`assetturnover` empty** → derived as `revenue / assets`. This made **F-Score test 9
   evaluable for the first time**; the `≥6 usable tests` guard had been absorbing its absence
   silently.
4. **`beta` hard-coded `None`** → `low_risk` was `neg_vol` alone. The regression that
   produces beta was *already running* inside `_price_extras` for `neg_idio_vol`; only its
   slope was being discarded. Now exposed.
5. **`growth_accel` clobbered** (not on the original list — the guard found it). The panel
   computes it correctly in `_yoy` from two prior-year point-in-time rows; `build_frame` then
   overwrote it with `revenue_growth − revenue_growth_prior`, and the panel never supplies
   `revenue_growth_prior`. All-NaN. `growth` was `revenue_growth` alone.

### 1a. The mechanism that hid three of them: `_f()` returned NaN, not None

`pandas` reads a blank CSV cell as `float('nan')`, and `_f()` returned it. That is not
`None`, so **every `if x is not None` guard in the panel silently accepted missing data.**

The damaging case was **`_f_score`**: `cr > cr_p if (cr is not None and cr_p is not None)` is
`True` when `cr` is NaN, and `NaN > NaN` is `False` — so a missing input was scored as a test
the company **FAILED**, *and* still counted toward the `≥6 usable` guard. Thin rows came back
as confident low scores instead of `None`. This affected `currentratio` (blank in 18.4% of
rows) and `debtnc` (18.3%). Fixing it moved `f_score` t from +2.80 to **+2.74** and its
coverage from 96.8% to 95.1% — very slightly *weaker*, because it is now honest.

Fixing `_f` also exposed a **latent crash** in `_yoy` (`None - float`) that NaN arithmetic had
been absorbing: the growth_accel branch tested `"revenue_growth" in m`, but the metrics dict
is pre-seeded with `revenue_growth=None`, so that key is *always* present.

---

## 2. THE CHEAP FIX THAT WOULD HAVE CAUGHT ALL OF THIS — coverage guard

`signal_coverage()` measures every wired number and theme, warns to stderr under 5%
coverage, and ships the result in `BACKTEST_RESULTS.json` under `signal_coverage`
(`below_floor` is the load-bearing part). Coverage is measured on the **standardized**
column, so a present-but-constant column correctly reads as unusable rather than covered.

Confirmed against the committed baseline: `roe`, `roic`, `neg_beta`, `growth_accel` were all
at **exactly 0.0%**. The guard would have flagged all four on day one.

- The floor is 5% — far below any plausible real coverage. The thinnest genuine theme,
  `institutional`, sits at 61.4%.
- Exemptions are an **explicit list** (`COVERAGE_EXEMPT_THEMES = {"sentiment"}`), not
  "any zero-weight theme". I initially inferred it from the weight and that immediately
  went wrong: zeroing `low_risk` (§3) silently disabled the guard for `neg_beta`. A theme
  zeroed because it was *measured and found wanting* still has data, and a plumbing bug in
  it must still be reported. Only genuinely source-less hooks belong on the list.
- Free performance win: `run_backtests` now builds the validated panel once with
  `keep_numbers=True` and derives coverage + per-signal IC from it, **removing a whole
  duplicate full panel build** from every run (`main()` used to rebuild it).

---

## 3. Decisions taken, and the evidence for each

### 3a. `roic` / `roe` — the two strongest signals nobody was using

| signal | median IC | IC t | coverage | rank in panel |
|---|---|---|---|---|
| **roic** | +0.0420 | **+3.38** | 96.7% | 4th of 32 |
| **roe** | +0.0439 | **+2.84** | 93.4% | 6th of 32 |

Both were contributing nothing. `quality` is now the strongest theme in the model
(+0.0363, t **+3.39**). Alone, these lifted PBO 40% → 26.7% and DSR 71.7% → 80.8%.

Correctness check worth recording: **every other signal's IC t-stat matched the baseline to
two decimals**, confirming the change perturbed nothing it shouldn't have.

### 3b. `neg_beta` — no standalone signal, but it helped the composite

`neg_beta` measures median IC **+0.0019, t −0.05** (coverage 88.0%). Betting-against-beta
does **not** replicate here as a standalone factor. Yet adding it moved DSR 80.8% → 92.9%,
long-short t 0.951 → 1.065 and top-decile alpha +5.68% → +6.20%. A zero-IC input can
legitimately help by decorrelating, but a 12-point DSR move from a t = −0.05 signal is a
large effect from a weak cause — treat as encouraging, not established.

### 3c. `neg_asset_growth` — DROPPED (wrong sign, confirmed on the full universe)

Median IC **−0.0141, t −0.70.** The investment factor says *low* asset growth should predict
high returns; here high asset growth did. Averaging it in was cancelling `neg_issuance`
(+0.0232, **t +2.25**), the one input in the theme that works. `capital_discipline` is now
issuance alone and measures **+0.0232 / t +2.25** as a theme.

It stays computed and listed in `NUMBER_THEME` so it keeps being measured — re-adding it is
one column in `factors.py`.

Measured *sequentially* (i.e. while `low_risk` was still at 0.125) the drop looked **mixed**:
PBO 26.7% → 20.0% and DSR 92.9% → 94.95%, but long-short t fell 1.065 → 0.916 and the
concentrated book gave back ~2pp.

**Re-tested in the FINAL configuration (`low_risk` = 0) and the ambiguity disappears.** Both
runs below are the full universe and differ *only* in whether `neg_asset_growth` is in the
theme:

| metric | dropped (shipped) | restored |
|---|---|---|
| PBO | 0.1333 | 0.1333 (tie) |
| Deflated Sharpe | 1.0000 | 0.9999 |
| **long-short t** | **3.485** | 3.298 |
| **top-decile alpha** | **+11.77%** | +11.52% |
| long-short ann | +17.58% | +17.39% |
| portfolio CAGR | +27.91% | +25.25% |
| monotonicity | −0.939 | **−0.976** |
| **`capital_discipline` theme IC** | **+0.0232 (t +2.25)** | +0.0062 (t +0.77) |

Dropping it wins on every criterion except monotonicity, and restoring it cuts the theme's own
IC by roughly 4×. **The earlier "mixed" verdict was an artifact of measuring the change while
`low_risk` was still scrambling the ranking** — a reminder that sequential attribution can
mislead when the factors interact. Confirmed keep.

### 3d. `low_risk` — set to ZERO weight. The single biggest change.

**Corrected finding first:** CLAUDE.md records `low_risk` as having pooled IC **−0.048**.
That does **not** replicate. On the full universe with *both* inputs finally populated the
theme measures **−0.0014 (t +0.71)** — indistinguishable from zero. It was **dead weight,
not actively harmful.** The −0.048 came from a smaller universe with `neg_beta` empty.

Zeroing its 12.5% weight produced by far the largest single improvement of the session:

| metric | with low_risk | low_risk = 0 |
|---|---|---|
| PBO | 20.0% | **13.3%** |
| Deflated Sharpe | 94.95% | **~100%** |
| Long-short ann | +6.63% | **+17.58%** |
| Long-short t | 0.916 | **3.485** |
| Monotonicity | −0.794 | **−0.939** |
| Top-decile alpha | +6.24% | **+11.77%** |

**Why a ~zero-IC theme mattered so much — verified, not assumed.** I measured the
average within-date Spearman correlation between all themes on the full panel.
**`low_risk` vs `size` = −0.352, the strongest anticorrelation in the entire matrix.**
Low-beta/low-vol names *are* large caps, and `size` is an explicit small-cap tilt
(`neg_log_mktcap`, t +1.68). At 12.5% each they were fighting each other, and `low_risk`
brought no signal of its own to the fight. Removing it let the working themes express: the
deciles went from badly scrambled to nearly monotone (D1 22.8% → 28.3%, D10 16.2% → 10.7%).

Two other correlations worth knowing: **`momentum` vs `institutional` = +0.50** (half
redundant — a candidate for consolidation), and `insider` vs `size` = +0.24.

**Applied live and reversible:** `WEIGHTS_ESTABLISHED`/`WEIGHTS_SPECULATIVE` now carry
`low_risk: 0.0`. Restore by setting it back to 0.125. The weights need not sum to 1 — the
backtest ranks on a weighted sum (scale-invariant) and the live scorer renormalizes per name.

---

## 4. `monotonicity` HAS BEEN READ BACKWARDS — correct the mental model

`quantile_backtest` orders buckets by `argsort(-comp)`, so **bucket 0 is the HIGHEST
composite**, and `monotonicity` is `Spearman(bucket index, bucket return)`. A working signal
therefore makes it **NEGATIVE**:

- **−1.0 = returns fall perfectly from D1 to D10 → perfectly ordered, the ideal**
- 0.0 = no ordering
- **+1.0 = returns RISE from D1 to D10 → the composite is exactly backwards**

Verified numerically against synthetic perfect and inverted decile series.

CLAUDE.md's *"monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
cleanly ordered"* is **inverted**: −0.68 means they *were* well ordered. So is the P4 table
logging −0.782 → −0.855 as *"slightly worse"* — that was an improvement. Every past
"monotonicity is bad" conclusion in this repo needs re-reading with the sign flipped.

Now documented in the `quantile_backtest` docstring, shipped as
`construction.monotonicity_want` in the JSON, labelled in the MD table, and pinned by
`test_monotonicity_sign_convention`.

---

## 4b. HELD-OUT CONFIRMATION — `low_risk` survives, `insider` does not

The one check CPCV and the Deflated Sharpe cannot provide: they correct for the trials inside
the *weight search*, not for a human looking at a theme's IC on the whole panel and then
dropping it. Now a permanent part of the backtest (`holdout_theme_validate()`, shipped as
`holdout_validation` in the results file), not a one-off script.

**Protocol, fixed before looking at any result.** Split the 110 dates in half by time
(early 1998-12-31..2012-07-10, late 2013-01-10..2026-04-22); **embargo the boundary date**
(2012-10-08), whose 63-day forward window is the only one that can straddle the split. Decide
on one half using a pre-specified rule — *flag a theme whose median IC on the decide half is
≤ 0* — then measure on the other half only. Run both directions.

| theme | verdict | ΔLS t (E→L) | Δtop-dec (E→L) | ΔLS t (L→E) | Δtop-dec (L→E) |
|---|---|---|---|---|---|
| **low_risk** | **confirmed** | **+1.59** | **+3.21%** | **+2.02** | **+7.86%** |
| capital_discipline | confirmed | +0.43 | +1.22% | +0.01 | +1.04% |
| quality | not_replicated | +0.39 | +1.21% | +0.17 | −1.06% |
| **insider** | **not_replicated** | +0.08 | +0.78% | −0.09 | −0.47% |
| value | rejected | +0.05 | −0.94% | +0.11 | −0.11% |
| momentum | rejected | −0.61 | −1.46% | +0.11 | −0.76% |
| size | rejected | −0.84 | −3.41% | −0.92 | −5.59% |
| institutional | rejected | −1.10 | −3.67% | 0.00 | 0.00% |

**`low_risk` = 0 is CONFIRMED.** On the pre-registered direction (decide early → measure late)
the rule fires on the early half (median IC −0.0308) *and* the effect holds on untouched data:
long-short t 0.97 → 2.56, top-decile alpha +6.09% → +9.30%. The reverse direction agrees more
strongly still. This is the largest effect in the table by a wide margin.

**`insider` = 0 is REJECTED — left at 0.125.** It helped one direction by a hair and hurt the
other. Its −0.34 full-sample t is not a stable property. This is precisely why it was tested
rather than dropped on the strength of one number.

### Two things this table reveals that are more important than the verdicts

1. **A theme's own IC does not replicate, but the benefit of removing `low_risk` does.**
   `low_risk` measures −0.0308 on the early half and **+0.0411** on the late half — it flips
   sign. So "low_risk has ~zero IC" is really "its IC is noise that averages to zero", and the
   §3d framing was too confident. The benefit survives anyway **because it never came from the
   theme's own predictive power** — it came from removing the −0.352 cancellation of `size`.
2. **That mechanism is now independently corroborated.** `size` also flips (t **+3.17** early,
   **−0.67** late: the small-cap premium worked pre-2012 and not after), and the gain from
   removing `low_risk` **tracks it** — +7.86pp in the early half where `size` is strong, only
   +3.21pp in the late half where it is dead. The effect is largest exactly where the
   mechanism predicts. That is a prediction the data could have falsified and did not.
   `size` is also the theme most damaged by zeroing (−0.84 / −0.92 t), confirming it is
   carrying real weight rather than being redundant.

**Do NOT act on the `capital_discipline` "confirmed" row.** It passes on a knife edge
(ΔLS t **+0.01** in one direction — noise), and the verdict rule only requires the sign to be
right in both directions, not the magnitude to be meaningful. That is a genuine weakness of
the rule, left un-retrofitted on purpose: changing the threshold after seeing results is the
exact sin this whole section exists to prevent. Read `confirmed` as "the sign held up twice",
not "this is worth doing". `capital_discipline` also has a healthy theme IC (+0.0232, t +2.25),
which makes the row look more like decile-metric noise than a real finding.

---

## 5. WHAT I DO NOT TRUST — read before acting on §0

1. **The held-out test confirms the DECISION, not the hypothesis generation.** Both halves come
   from the same 18-year panel, the same universe and the same data vendor, and the
   size-cancellation mechanism was hypothesised on the full sample before being checked on the
   splits. A truly clean test needs data this project has never touched. What §4b does rule out
   is the specific failure I was worried about — that zeroing `low_risk` was fitted to noise in
   the very periods it was then scored on. It was not.
2. **Deflated Sharpe "100%" is a saturated probability**, not a proof. Report it as
   ">99.9%" and do not treat the bar as permanently cleared.
3. **CPCV vs long-short disagree on magnitude.** Removing `low_risk` moved median OOS IC
   only +0.059 → +0.060 while long-short t moved 0.92 → 3.48. The gain is concentrated in
   the *tails* (deciles), where fewest names sit and noise is highest. The IC evidence for
   this change is far weaker than the decile evidence.
4. **The concentrated top-25 hold book (CAGR +27.9%, alpha vs EW +13.95%) is the noisiest
   number in the file.** CLAUDE.md records top-25 as previously *losing*. Do not quote it.
5. **Sequential attribution misled me once already** (§3c): `neg_asset_growth`'s drop looked
   mixed when measured with `low_risk` still weighted, and clearly correct once re-tested in
   the final configuration. Every "stage N vs stage N−1" comparison in this document carries
   that caveat — the factors interact, so only the final head-to-head is authoritative.
6. **Derived ROE/ROIC are quarterly rates, not annualized.** Harmless for ranking
   (everything is z-scored cross-sectionally) and consistent with how `earnings_yield` /
   `op_margin` already work here, but it lets **fiscal-quarter seasonality into the
   cross-section** — different names sit at different fiscal quarters on a given rebalance
   date. A TTM version is the obvious next refinement and I deliberately did not fold it in
   silently.
7. **`institutional` coverage is 61.4% on the full universe**, not the 81.7% recorded in
   CLAUDE.md (that figure came from a smaller universe). `insider` is 85.0%.

---

## 6. NEW finding not asked for: `insider` is the actually-negative theme

With the per-theme table finally available:

| theme | median IC | IC t | coverage |
|---|---|---|---|
| quality | +0.0363 | +3.39 | 98.0% |
| momentum | +0.0517 | +2.62 | 96.6% |
| capital_discipline | +0.0232 | +2.25 | 96.8% |
| institutional | +0.0297 | +1.81 | 61.4% |
| size | +0.0126 | +1.68 | 100% |
| growth | +0.0221 | +1.45 | 93.0% |
| value | +0.0123 | +1.34 | 100% |
| low_risk | −0.0014 | +0.71 | 99.7% |
| **insider** | **−0.0034** | **−0.34** | 85.0% |
| sentiment | n/a | n/a | 0.0% |

**`insider` is the only theme with a negative t-stat, and it still carries 12.5% weight.**
It has since been tested properly on the held-out split (§4b) and **zeroing it did NOT
replicate** — +0.08 long-short t one direction, −0.09 the other. **Left at 0.125.** Its
negative full-sample t is not a stable property, and this is the clearest illustration in the
session of why a single number is not a decision: by the same reasoning that justified zeroing
`low_risk`, `insider` looked like the obvious next cut, and it did not survive the test.

`growth_accel`, now measurable for the first time: +0.0062, **t +0.50** — no real signal.

---

## 7. What's blocked / not done

1. **CLAUDE.md's separate "P5 — robustness" item is NOT done.** Winsorization already
   existed (`zscore` clips at 2%); **median/MAD robust z-scores and industry-relative
   ranking remain untouched.**
2. **Out-of-sample confirmation of the `low_risk` removal** — the single most important
   outstanding item (§5.1).
3. `sentiment` still has no point-in-time source (grades parked; `grades.csv` is 58 bytes).
4. `bulk.EARNINGS_CODES` still unpopulated, so `earnings_dates()` returns `[]` and PEAD is
   still blocked.
5. Social preview (og:image) untouched.
6. `inst_breadth` remains in `NUMBER_THEME` (so it is measured, t +1.08) but no longer feeds
   the institutional theme — `sm_breadth` replaced it in P4. Harmless drift, but the
   "single source of truth" comment in `settings.py` overstates what `NUMBER_THEME` controls:
   `factors.py` hardcodes the theme means.

---

## 8. Recommended next step, in order

1. ~~Confirm the `low_risk` removal out-of-sample~~ **DONE — confirmed (§4b).**
2. ~~Test zeroing `insider`~~ **DONE — rejected, left at 0.125 (§4b).**
3. ~~TTM ROE/ROIC~~ **DONE — REJECTED (P6.2); quarterly is better.**
4. ~~median/MAD robust z-scores~~ **DONE — REJECTED (P6.3); costs half the long-short t.**
5. ~~Consolidate momentum/institutional~~ **DONE — REJECTED (P6.4); both earn full weight.**
6. ~~Pre-specify the holdout magnitude threshold~~ **DONE (P6.0, commit `4de6e71`).**
7. ~~Are the returns achievable net of costs?~~ **DONE — YES, breakeven 236bps vs ~37bps
   actual (P6.1).**

**Now, in order:**

1. **Get data this project has never touched.** This is now clearly the top item. The edge
   clears every internal bar and survives costs; what it has never faced is data outside this
   one 18-year Sharadar panel. A forward paper-track starting today is the cleanest and
   costs nothing but time — **and it is the natural Cowork task** (tracked "Valquo Index vs
   SPY"). → *Take the paper-track to the Cowork chat.*
2. **Unblock industry-relative ranking** (P6.3b) — one Sharadar TICKERS download. It is the
   only P6 item that could not be tested at all, and `sector_neutral` has been silently inert
   in every backtest to date, so this is also a latent-bug fix.
3. **Live-behaviour watch after the P5 deploy.** `low_risk` went 12.5% → 0, so the hot list
   will tilt smaller-cap than before. That is intended, but the first post-deploy scans should
   be eyeballed. Revert is one line in `settings.py`.
4. **PEAD from EVENTS** — still blocked on `bulk.EARNINGS_CODES` (needs Sharadar's EVENTS
   legend). This is now the most promising *new* signal, since the cheap refinements are all
   exhausted.
5. **ML tree combiner**, now clearly worthwhile — there are several genuinely real signals to
   combine, and P6 shows the linear composite is sensitive to how inputs are scaled.
6. **Re-read every past "monotonicity" conclusion with the sign flipped** (§4).
7. Social preview (og:image) — still untouched, independent of everything else.

---

## 9. Standing notes

- `data/` is gitignored, as are `*.zip` / `*.csv.gz` / `*.parquet`. Nothing licensed was
  committed; `BACKTEST_RESULTS.*` carries derived metrics only (IC, t-stats, returns,
  weights) — no raw rows, prices or per-name fundamentals.
- Bulk layout: raw zips in `data/raw/`, extracted CSVs in `data/bulk/`, caches in
  `data/bulk/prepared/`.
- `DERIVE` in `fundamental_panel.py` toggles each derived input, so a validation change can
  be attributed to one signal instead of a bundle. All four ship **on**, and
  `test_all_derived_inputs_ship_enabled` fails the suite if one is left off.
- Results-file schema is now **version 2** (adds `signal_coverage` and `per_theme`; purely
  additive).
- The most recent SF3 quarter is always incomplete (filings arrive over following weeks) —
  the 45-day `inst_lag_days` convention handles it.
- The live hot-list scan runs at 22:23 UTC and uses the FMP key.
