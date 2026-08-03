# CLAUDE.md — Valquo project brief (read every session)

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

- **The edge now clears both statistical bars for the first time: PBO 13.3% (want <50%),
  Deflated Sharpe >99.9% (want >95%), long-short t 3.485 (want >2), top-decile alpha +11.77%.**
  The single biggest driver was zeroing `low_risk` — **and that has since been CONFIRMED on a
  held-out time split** (decide on one half, measure on the other, both directions). On the
  pre-registered direction the rule fires on the early half (median IC −0.0308) and, measured
  on the later half that did NOT inform the decision, **long-short t goes 0.97 → 2.56 and
  top-decile alpha +6.09% → +9.30%**; the reverse direction agrees more strongly (t 0.55 →
  2.57, alpha +6.63% → +14.49%). Do not treat the edge as settled anyway — caveats at the end.
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
- **Theme ICs (full universe):** quality +3.39, momentum +2.62, capital_discipline +2.25,
  institutional +1.81, size +1.68, growth +1.45, value +1.34, low_risk +0.71, **insider −0.34**,
  sentiment empty. `insider` is the only negative theme and still carries 12.5% weight — but
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
- **`sector_neutral` HAS BEEN SILENTLY INERT IN EVERY BACKTEST.** There is no sector/industry
  column anywhere on disk and the panel hard-codes `"sector": ""`, so `build_frame` groups on a
  constant. Industry-relative ranking is BLOCKED until Sharadar's TICKERS table is downloaded
  (API-only, not one of the four bulk tables). Note when doing it: TICKERS gives TODAY's
  classification, so applying it to 1998 rows is a mild look-ahead — usually considered benign
  (reclassification is rare and not return-predictive) but say so rather than hide it.
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
- **Standing caveats, do not drop them:** Deflated Sharpe is a *saturated* 0.9999991, not a
  proof. Both halves of the held-out test come from the same 18-year panel and universe, and
  the size-cancellation mechanism was hypothesised on the full sample — so the *decision* is
  confirmed out-of-sample, the *hypothesis generation* is not. The concentrated top-25 book is
  the noisiest number in the file. Weight-tuning itself remains noise-chasing: CPCV still
  adopts no weighting over the defaults.

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
- **`insider` is now the only negative theme (t −0.34) and still carries 12.5% weight** — the
  obvious next candidate, deliberately NOT changed.
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
13. **Industry-relative ranking — BLOCKED, and it's also a latent bug.** `sector_neutral` has
    been silently inert in every backtest (no sector column on disk; panel hard-codes
    `"sector": ""`). Needs one Sharadar TICKERS download → ticker→sector map → populate
    `metrics["sector"]`. Mind the today's-classification look-ahead caveat (see LATEST).
14. **Watch live behaviour after the P5 deploy.** `low_risk` 12.5% → 0 tilts the hot list
    smaller-cap. Intended, but eyeball the first scans; revert is one line in `settings.py`.
15. **PEAD from EVENTS** — now the most promising NEW signal, since the cheap refinements are
    exhausted. Still needs `bulk.EARNINGS_CODES` from Sharadar's EVENTS legend first.
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
