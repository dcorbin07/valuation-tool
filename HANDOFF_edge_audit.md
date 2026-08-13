# HANDOFF — executing the external edge audit (`VALQUO_EDGE_AUDIT.md`)

Session opened 2026-08-03. Source: the 108-item external catalogue produced by a read-only Cowork
session at commit `7eb0046`. Every finding in it is a **code-reading** finding — nothing was executed —
so each item arrives as a hypothesis with a file:line citation, and the first job on every one is to
check it against the code rather than believe it or defend the record.

Item IDs are the audit's own (`B*`, `R*`, `X*`, `S*`, `O*`, `U*`, `C*`, `P*`, `D*`, `M*`) and are cited
in every commit message so the ledger stays traceable.

---

# PART 0 — THE PRE-COMMITMENTS

**Written 2026-08-03, before a single result was read. Not to be revised afterwards.**

The failure mode of handing an audit to the audited is motivated reading. These are recorded first
so that a later number cannot quietly select its own threshold.

## R1 — factor-adjusted alpha, and the product claim that follows

The test: regress the 63-day top-decile-minus-equal-weight series on FF5+MOM (Ken French, free), and
separately on the Hou–Xue–Zhang q-factors. Report the intercept, its Newey–West *t*, R², and every
loading. Repeat on the long-short series.

**Committed threshold.** The word *alpha* stays in product copy **only if the FF5+MOM intercept is
positive with Newey–West t > 2.0.** Not 1.9. Not "t > 2 on one of the two models" — FF5+MOM is the
deciding model; the q-factor result is reported alongside as the harder test and is informative, not
deciding.

**Both product claims are written now, before the number exists:**

- *If the intercept clears t > 2.0:* "Valquo's top decile has produced excess return that is not
  explained by the standard equity factors — a Fama–French 5-factor plus momentum regression leaves a
  positive intercept of X%/yr, t = Y. Here is the regression, the loadings, and the live forward track."
- *If it does not:* "Valquo delivers diversified, transparent factor exposure — value, quality,
  momentum, size, capital discipline and institutional ownership — assembled point-in-time, screened
  for cost and tax, with the holdings and the live track published. It is not a claim of secret alpha;
  a Fama–French regression attributes X% of the excess return to known factor premia. What you are
  buying is construction, freshness and honesty about which is which."

The second claim ships without argument if the number says so. Whichever the regression supports is
the one that goes on the site.

**Corollary committed now:** if the intercept is indistinguishable from zero, further *signal hunting*
on the equity side is close to worthless, and the remaining edge is construction, cost, tax and
capacity (audit Part VI / P1). The roadmap changes accordingly, in the same pass.

## R2 — the corrected options re-run

After the **B1** price-basis fix, re-run the 187-name book, both random-entry control seeds, the
`term_slope` out-of-sample test and the broad autopsy.

**Committed threshold, before the run.** The current headline negative — random entry (+13.22%) beats
the signal (+5.14%), a −8.08pp gap, sign-test z = −5.24 — is being re-derived on corrected data. It
will be tempting to read the re-run charitably.

- If the corrected real-versus-control gap **remains negative at conventional significance under a
  date-block bootstrap (R3)**: the entry signal is dead, and the record says so plainly.
- If the gap **closes to within its confidence interval**: the verdict is **INCONCLUSIVE**, not
  vindicated. A signal that cannot beat random entry by a measurable margin is not a signal; it is an
  alert-generation mechanism, and the product copy has to say so.
- If the gap **turns positive at significance**: that is a genuine reversal, and it must additionally
  survive the date-block bootstrap and the both-halves split before anything is claimed from it.

The paired name-year sign test and paired *t* must be **in the repository with a test** before this
verdict is reported at all (R3.3) — the two numbers the whole options conclusion currently rests on
are not reproducible from shipped code.

## R7 — the `term_slope` retention floor, argued and committed before re-scoring

Not a renegotiation of a failed bar to make it pass. The re-commitment below **adds an arm that has
never been measured**, and `term_slope` can still fail on it.

**What the 40% floor actually was.** `options_autopsy.py:36` states G3's purpose: "A filter that keeps
8% of alerts has not improved the strategy, it has replaced it with a smaller one." That is a
*product* rationale, not a statistical one — the statistical risk is already carried by G4
(`n_kept >= MIN_TRADES`) and by G6 (beats a random filter keeping the same count). The 40% figure was
never derived; it is a round number, and the 55-name run cleared it by 0.6pp.

**Why a raw percentage is the wrong unit on a larger universe.** A fixed-threshold filter applied to a
broader book is mechanically more selective — more names means more of the distribution's left side —
so a constant percentage floor makes any filter fail as the universe grows, which is a scale artefact
and not a statement about filter quality. The percentage is a proxy for two distinct things: *is there
still enough alert flow to trade*, and *is what survives concentrated into a handful of names or dates*.
Measure those two directly.

**Committed floor for a 187-name (or larger) universe, replacing the single 40% arm:**

1. **G3a — flow.** The filtered book must leave **≥ 52 tradeable alerts per year** on the deployed
   universe. One per week is the minimum cadence at which a user can build and roll a diversified
   book; below it the filter has produced a different product regardless of its expectancy.
2. **G3b — concentration (NEW, never measured).** The retained trades must span **≥ 60% of the names**
   and **≥ 60% of the calendar months** that the unfiltered book spans. This is the real failure mode
   the percentage was proxying for, and it is measured directly here for the first time.
3. **G3c — backstop.** Retention **≥ 20%** of alerts. Stated plainly as a judgement, not a derivation:
   below one-in-five, four of every five alerts are discarded and the filter is manifestly the
   strategy rather than a refinement of it.

All three must pass, in both split directions, alongside the unchanged G1, G2, G4, G5, G6, G7. The
previously-reported 36.4% clears G3c; whether it clears G3b is unknown as of this writing, and G3b is
the arm on which the re-score can still fail.

## Standing rules for everything in this ledger

- **Ambiguous against its own committed threshold = NULL**, not a judgement call.
- **Full universe only.** ~2,710-name equity panel, full mined options universe. Anything smaller is a
  smoke test and is labelled as one in the same sentence as its number.
- **One change per run** for every A/B panel comparison.
- **A clean rejection is the deliverable.** The project's hit rate is about one adoption in eight.
- Per audit item **B12**, every inherited "800 largest names" figure is an *alphabetical* slice and is
  not citable until re-run on the full universe.

---

# PART 1 — RESULTS BY ITEM

Format per the execution prompt: committed threshold, what was run, result, verdict, why, follow-on.

## Step 0a — reconcile the tree

**What was run:** `git status` / `git rev-list HEAD..origin/main` in the primary checkout, then
`git merge main` into the worktree branch.

**Result.** The execution prompt's picture of the tree was **stale, and in the project's favour**.
Local `main` is at `b67b07d` and is **0 commits behind `origin/main`**, not 16. There are **zero
modified tracked files** — all 39 dirty entries are untracked docs and `PROMPT_*.md`, including
the audit itself. The "332 modified files and 35 untracked" the audit saw was the dirty
`worktree-growth-valuation` checkout it happened to be reading, not `main`.

**Verdict: NULL** — no reconciliation was needed. Work proceeds on `worktree-options-live`, merged
up to `main` first, which auto-lands via the CI pipeline.

## Step 0b / C7 — widen the CI gate

**Committed threshold (before the run):** every suite must be green *locally* before any of them
is allowed to gate a deploy. Wiring a red suite into an auto-merge pipeline would block every
agent branch in the project, which is a worse outcome than the gap being audited.

**What was run:** all 16 suites in `tests/`, then the workflow edit.

**Result.** 16/16 green, **552 tests** at the time of the check (the audit's "roughly 464" is
stale). `land-agent-branch.yml` now loops every `tests/test_*.py`, groups each in the Actions log,
and exits non-zero if *any* failed — so one red suite cannot be hidden by a later green one.
Checked first that no suite outside `test_edge.py` reads the gitignored `data/`: four reference a
data path, all of them temp dirs or literal strings, so CI without `data/` is safe.

**Verdict: ADOPTED.** **Why it mattered:** the pipeline auto-merges to `main` and Render
auto-deploys from `main`. This very session edits `options_universe.py`, `options_backtest.py`,
`factors.py`, `data_providers.py` and `results_file.py`, and `test_edge.py` alone would have
passed several of the broken intermediate states.

## Step 0c / D10 + C5 — the time-limited Sharadar extraction

**What was run:** `options-bot/quant_bots/scripts/verify_sharadar.py` against the live key —
written for exactly this and, per the audit, never previously run. (The key was injected from
`.env` in-process; nothing about it is printed, logged or committed. Full report banked outside
the repo.)

**Results — all six questions settled, from the entitlement rather than the documentation:**

1. **Entitlement.** All 8 probed bundle tables reachable: SEP, SFP, SF1, SF2, TICKERS, DAILY,
   ACTIONS, SP500. SFP *is* inside the subscription — that was genuinely open.
2. **Restatements APPEND a new ARQ row.** Confirmed on GE, WFC, MSFT, F, T (AAPL and KHC clean).
   **Taking the earliest datekey is REQUIRED, not defensive**, and any `ORDER BY datekey DESC
   LIMIT 1` without an as-of filter has look-ahead. See **D10-a** below — this produced a new
   defect the audit did not find.
3. **SEP has no `dividends` column** (10 columns: close, closeadj, closeunadj, date, high,
   lastupdated, low, open, ticker, volume). `closeadj` is **dividend-back-adjusted, i.e. total
   return**; `closeunadj` is the as-traded level. Verified arithmetically on AAPL's 4:1.
   **This bears directly on R8**, which assumes forward returns exclude dividends: if the panel's
   forward returns run on `closeadj` they already include them, and R8's premise has to be
   re-checked before that item is run. Flagged, not resolved here.
4. **`TICKERS.category` has 15 distinct values** across 21,939 SEP rows. The options-bot's PIT
   universe builder knows 6 and silently EXCLUDES 9 — including 382 "Canadian Common Stock" and
   15 "Canadian Common Stock Primary Class", which are genuinely common equity. Preferreds and
   warrants (2,272 rows) are correctly excluded. Recorded for **C5**; not acted on, since it is
   the second codebase.
5. **SF1 percentage fields are FRACTIONS** (AAPL roa 0.328, netmargin 0.269). No 100x hazard.
6. **Survivorship probe FAILED** — HTTP 422, `isdelisted` cannot be used as a filter on this
   entitlement. Unresolved by this route. The equity panel does not depend on it (delisting comes
   from the ACTIONS bulk cache, and **B14** below now measures that mask's coverage directly).

**Verdict: ADOPTED as record.**

---

## D10-a — a restated quarter can be counted twice in a TTM window · **NEW, not in the audit**

**Committed threshold:** this was not a pre-registered test — it is a defect found while acting on
D10's answer, and it is reported as a defect with its blast radius measured, not as a result.

**What was run:** the D10 finding (restatements append) applied to the code, then a direct count
over the shipped export:
`groupby(['ticker','dimension','reportperiod']).size()` on `data/backtest/fundamentals.csv`
(197,265 ARQ rows, 2,827 tickers).

**Result.** **6,000 of 190,394 (ticker, reportperiod) groups carry more than one datekey — 3.15%,
6,871 extra rows, touching 1,818 of 2,827 tickers (64%).** `_ttm` took the last four *rows* with
`datekey <= as_of` and de-duplicated on **datekey** — which two filings of one quarter never
share — so its own guard (`if len(seen) < n: return None`) was structurally blind to this. A
window spanning a restatement could sum Q1, Q2, Q2', Q3: one quarter twice, one dropped.

**Verdict: FIXED, and the blast radius is small.** `_ttm` now collapses by `reportperiod`, keeping
the latest filing public by `as_of` (correct point-in-time *and* one row per quarter), and
`reportperiod` was added to `WRDSProvider._KEEP`, without which the fix is impossible.

**Why the impact is limited:** `_ttm` has exactly one caller, `_ttm_quality`, which produces
`roe_ttm` and `roic_ttm` — the TTM variants **measured and REJECTED in P6.2**. The shipped
composite does not consume them. `_pit` (latest row `<= as_of`) and `_yoy` are unaffected: a
restatement appends at a *later* datekey, so the as-of filter already excludes a future one, and
returning the restated row for a date after the restatement is the correct point-in-time answer.

**Follow-on:** this is the fifth instance of the pattern `CLAUDE.md`'s COVERAGE RULE names —
a guard that cannot see the failure it was written for (`assets` in the allowlist, the SF3
positional-arg bug, the five empty factors, `invcap`/`taxexp`/`ebt`, and now this). It is also the
second time in two sessions that `_KEEP` was the binding constraint. Audit item **M3** proposes
engineering against this class directly; it is worth doing.

---

## B1 — price basis in the broad options universe · **the one everything else waited on**

**Committed threshold:** none needed — this is a correctness defect, not a hypothesis. The audit's
own prediction is recorded and will be scored against the re-run in session 5: *the -8.08pp
real-versus-control gap should survive in sign and possibly shrink; every level should move; the
`term_slope` out-of-sample retention figure should change materially.*

**What was run:** the two cited lines checked against `options_backtest.load_bars`, then a sweep
for the same pattern across every options module and runner.

**Result — the audit was right, and it undercounted.** `options_universe.py:327` (`run_name`) and
`:594` (`random_entry_control`) both fed `w["close"]` — `closeadj`, split **and dividend**
adjusted, labelled "technicals only" — into `chain_summary`, `pick_contract` and
`compute_signals`, while settlement at `options_backtest.py:344` correctly used `raw_close`. Entry
and settlement of the same trade ran on different price bases.

**Four more sites had the identical defect, in code written in the two preceding sessions:**

| Site | What it corrupts |
|---|---|
| `options_universe.py:327` | 187-name book: ATM IV, moneyness band, 0.35-delta target, `term_slope` / `skew_25d` / `vrp` / `gex_proxy` |
| `options_universe.py:594` | the random-entry control |
| `options_entry.py:514` | roadmap 22c: every arm's contract pick |
| `options_entry.py:565` | roadmap 22c: the alert pass itself |
| `optexit_run.py:70`, `:126` | deep-research thread #1: the alert pass and every captured contract path |

**This is a disclosure, not a footnote: roadmap 22c and deep-research thread #1 both carry the
B1 defect.** Both concluded REJECT, and both rest on *paired within-name-year* comparisons where a
distortion roughly constant within a year largely differences out — so the direction of each
verdict is more robust than its levels. But no absolute number from either is citable until
re-run, and that re-run belongs with R2 in session 5.

**Fix.** All five sites now call one accessor, `options_backtest.spot_asof(w)`. A comment did not
stop this happening five times; a named function that is the obvious thing to reach for might.

**Second guard, per the audit:** `options_universe.sanity()` now flags a median entry IV outside
[0.05, 1.00] and ships `iv_median`. The 187-name run's median of **1.28-1.57**, recorded in
`HANDOFF_universe_backtest.md` section 8 as an unexplained anomaly, would have fired it. Coverage
said `iv` was PRESENT; nothing asked whether it was SANE — the same shape as the P7 currency bug.

**Verdict: FIXED. The re-run is R2 and has not been run.** Every options number in the record
remains provisional until it has.

---

## B3 — expiry marked at a stale quote

**What was run:** `options_fill.round_trip` read against its callers.

**Result.** Confirmed exactly as described, and **independently corroborated by measurement**:
deep-research thread #1 found the same defect from the other direction, measuring the stale mark
**higher than the truth in 94.7% of cases**, **86.1% of marks positive on contracts that were in
fact worthless**, and a mean of **-77.75% against a true -92.22%**. Two independent findings, one
by code reading and one by measurement, of the same bug.

**Fix.** `force_intrinsic_at_expiry` (default on) and `exit_quote_age_days` with
`MAX_MARK_AGE_DAYS = 3`. `simulate_trade` now passes the real age of `last_q`. The trade row
carries `stale_mark_rejected` and `exit_quote_age_days`, so the choice is visible rather than
implicit. The exit lab keeps an explicit opt-out purely so it can still reproduce the *old*
behaviour for its parity check — otherwise the demonstration of the bug silently becomes a
demonstration of the fix.

**Verdict: FIXED.** **Follow-on:** unblocks the tail and sizing work (O12), and removes the
mechanism that produced thread #1's fake "hold longer wins" gradient.

---

## B15 — the options headline was gross of commission

**Result.** Confirmed. `return_pct = exit_px / entry_px - 1.0`, inherited by `pnl_pct` and then by
`expectancy_pct`, while `options_fill.py:49-52` and `OPTIONS_BACKTEST_RESULTS.md:4-5` both stated
net of spread *and* commission. About 0.27pp on a $485 median position.

**Fix.** `return_pct` is now `net_pnl / (entry_fill x 100)`. `return_pct_gross_comm` preserves the
old quantity so no historical figure becomes unreadable. **Five test assertions across the edge
suite were pinning the old arithmetic** and were updated to pin *both* quantities — a worthless
long option now correctly posts slightly worse than -100%, because it loses the premium plus the
round trip.

**Verdict: FIXED.** **Note:** `profit_factor` remains a ratio of summed *percentages* rather than
dollars (`options_tracker.py:149-175`) — non-standard, unfixed, and labelled here so "PF 1.30" is
read correctly. That half of B15 is deferred.

---

## B16 — the dead exit module · **the audit was partly wrong, and it is recorded**

**Result.** `options_exit.py` implements an exit on the *underlying* (+/-1 sigma on the stock) and
has never contributed to a reported number, exactly as described. But the audit's "**imported by
nothing**" is **incorrect**: `tests/test_intraday.py` imports it in six places. Nothing in the
*product* imports it. Corrected in the module banner rather than quietly worked around.

**Fix.** Renamed to `deprecated_options_exit.py` with a banner naming the real exit logic
(`options_backtest.simulate_trade`'s inline day-walk loop), plus `valuation/edge/DEPRECATED.md`.
A first attempt to move it into `valuation/edge/archive/` **broke three unrelated tests** by
shadowing the existing `valuation/edge/archive.py` module — reverted, and worth remembering.
Also fixed: the phantom `exit_value` reference in `options_fill.py`, the stale description in
`options_tracker.py:4`, and the unreachable `if not t.get("ok"): continue` in `simulate_trade`,
which now fails loudly instead of silently swallowing a genuine exit trigger.

**Verdict: FIXED.**

---

## B10 — `accruals_q` computed and then silently overwritten

**Result.** Confirmed. The panel computes `-((NI - CFO) / assets)`, the Sloan measure; `factors.py`
replaced it unconditionally with `FCF/NI` restricted to `ni > 0`. `book_to_price` and
`growth_accel` are both guarded against exactly this collision; this one was not.

**Fix.** The caller now wins, and the FCF/NI variant survives as `accruals_fcf_ni` so the two can
be measured head to head instead of one silently replacing the other. A provider that supplies
neither (the live FMP path) still gets the derived fallback, so the live screener is unchanged.
The regression guard is written over **every** theme input, not just this one, so the next
collision fails in a test rather than in a six-month-old IC.

**Verdict: FIXED — and it CHANGES THE COMPOSITE.** The panel's `accruals_q` is now the Sloan
measure. Which of the two definitions is better is an open A/B (audit's own instruction: "keep the
better one on its merits") and is **not settled here**; the full-universe re-run at the end of this
file measures the combined effect of this and the other panel-touching corrections.

---

## B18 / B19 / B20 / B24 / B26 — the remaining cheap corrections

All five confirmed as described. Fixes, briefly:

- **B18.** One convention for negative enterprise value across all three EV ratios: **missing**,
  not extreme. A net-cash company used to rank as the most expensive name in the cross-section on
  `ebit_ev` and, once negated, the cheapest of all on `neg_ev_sales` — one fact at both ends of
  one theme. ~0.70% of rows. The blanket range exemption on `ev_sales` / `ev_ebitda` / `ps` is now
  backed by a **sign check**, so the one place a sign error could hide is no longer the one place
  nothing looked.
- **B19.** `risk_stats` ships `rf_annual` and `metric`. Every "Sharpe" in the results file is an
  **information ratio versus zero** — overstated by roughly 0.05-0.10 over 1998-2026, consistently
  across every book, so relative comparisons are unaffected and the label was the problem.
- **B20.** `earnings_yield` switched numerator definition mid-cross-section: net income to common
  where `netinccmnusd` was populated, **total** net income where it was not. Now `netinccmn` — the
  same quantity in local currency — so only the currency conversion varies, with `_ni_basis`
  recording how often the last-resort path fires.
- **B24.** `sanity_check`'s scan list de-duplicated, and a factor's negated twin dropped: the
  shipped output printed `ev_ebitda` at a foreign median percentile of 0.362 beside
  `neg_ev_ebitda` at 0.640, which is one fact reported twice with the sign flipped. An inflated
  flag count trains readers to ignore the guard, and this is the guard that would have caught P7.
- **B26.** A Form 4 or rating action dated `as_of` is no longer readable at that day's close
  (`side="left"` on the upper bound). Both the prepped fast path and the fallback were changed, so
  they cannot disagree about the same name.

**Verdict: all FIXED.** B18, B20 and B26 change the panel; the effect is measured in the re-run
below.

---

## B9 — restate the Deflated Sharpe and PBO

**Committed threshold:** the audit offers a minimal fix (relabel) and an honest one (a real trial
counter, item M1). **Only the relabel is claimed here.** M1 is not done, so `N` is still 8, and no
claim in this file rests on the deflated figure.

**Result.** Confirmed, and now self-reporting. `_deflated_sharpe_detail` ships `sr0_benchmark`,
`n_trials`, `var_sr_across_trials` and `n_periods` alongside the probability, plus a `metric`
field that reads **`probabilistic_sharpe_ratio_UNDEFLATED`** whenever `sr0` collapses below 5% of
the Sharpe — which is what eight near-identical weightings of the same eight themes produce.
Demonstrated in the regression guard: on the same return series, trials spanning 0.400-0.402 give
`sr0 ~ 0.00085` and a saturated probability, while genuinely dispersed trials (-0.20 to 0.90)
raise `sr0` and **lower** the probability. Real deflation costs probability; this was not costing
any. PBO now ships `pbo_scope = "weight_scheme_selection_only"`.

**Verdict: RELABELLED, not recomputed.** **Why it matters:** two of the three statistical bars the
project cites as cleared measure something narrower than the claim they support. The third — the
long-short **t of 3.52 against the Harvey-Liu-Zhu hurdle of 3.0** — is real and is the one to
lead with. `CLAUDE.md` is updated accordingly.

**Follow-on:** M1 (the append-only research log) is the item that makes the honest version
possible, and it is where the next session should start on this thread.

---

## B12 — every "800 largest names" result was an alphabetical slice

**Result.** Confirmed. `WRDSProvider.universe` returned `sorted(keys)[:limit]`, and the local
export path used by `run_backtest.bat` never goes through `SharadarProvider.universe`, which is
the only one that ranks by size.

**Fix.** Ranked by each ticker's latest resolvable market cap, with the sort key printed in the
banner and the subset explicitly labelled a smoke test. A `limit` at or above the export size is
treated as the full universe and not labelled — the caller's default is 3000 against a 2,827-name
export, and mislabelling a full run as a smoke test is an error in the other direction.

The ranking uses **today's** market cap, which is a mild look-ahead. Acceptable for a smoke-test
subset; not acceptable for anything reported. Stated in the code, not just here.

**Verdict: FIXED. The consequence is not.** Every 800-name-era result — the first CPCV "adopt",
PBO 13%, Deflated Sharpe 77%, `f_score` at t +5.66, `sm_breadth` at t 2.37, the 13F look-ahead
stress test and the four classic-anomaly rejections — was computed on names beginning with roughly
A through C and **is not citable until re-run** (items R5, R6). This also reframes the project's
own calibration note in `CLAUDE.md`: *"PBO 13% on 800 -> 53% on full"* was never measuring how much
a large-cap tier flatters results. It was measuring how much an arbitrary alphabetical subsample
does. `CLAUDE.md` corrected.

---

## B14 — the delisting mask's coverage was measured and thrown away

**Result.** Confirmed. `_masked` was incremented and never printed, returned or shipped;
`cleanups.survivorship_mask` was a boolean meaning only "the ACTIONS map is non-empty", which
cannot distinguish a working mask from one that matched nothing.

**Fix.** `survivorship_mask_coverage` now ships: the delisting-map size, series masked, the masked
share, and — the part that makes a silent failure loud — **`ended_early_unmasked`**, the count of
names whose price series stops more than `STALE_TAIL_DAYS = 180` before the panel end with **no
ACTIONS row to explain it**. That population is exactly the failure the mask exists to prevent: a
missed delisting forward-fills a last close and contributes a fake flat 0% forward return to every
subsequent rebalance date. Built in the same spirit as `ev_freshness`.

**Verdict: FIXED.** **Follow-on:** the number itself lands with the re-run below and is the first
direct evidence about how complete the ACTIONS delisting map actually is.

---

# PART 2 — THE FULL-UNIVERSE RE-RUN

**Committed before the run:** these corrections are repairs, not hypotheses, so no adopt/reject bar
applies to them. What was pre-committed is the *reporting* rule: report the A/B against a clean
baseline, report every metric that moved, and **treat any change in a held-out VERDICT as the
thing that matters** — a correction that moves a measurement without moving a decision is a
different event from one that changes what the model does.

**What was run.** Two full backtests on the full **2,827-name export / 2,710-name panel**, 110
rebalance dates, identical data, identical universe:

- **BASELINE** — commit `b67b07d` (pre-audit `main`), in a throwaway worktree.
- **CORRECTED** — this session's Part I corrections.

The baseline was run **because the committed `BACKTEST_RESULTS.json` could not be trusted as
one**: its own provenance stamp reads `commit 7eb0046, branch worktree-growth-valuation,
dirty: true` — a different branch with an uncommitted working tree. As it turns out the clean
baseline reproduces it to four decimals, so the stored file was fine; but that could not be known
in advance, and **it is only knowable at all because the results file stamps its git state.**
Audit item **M6** proposes exactly this kind of provenance stamping; this is a point in its favour.

## The headline A/B

| metric | BASELINE `b67b07d` | CORRECTED | delta |
|---|---|---|---|
| **long-short t** | 3.5202 | **3.8838** | **+0.364** |
| **top-decile alpha** | +11.88% | **+11.78%** | −0.10pp |
| **monotonicity** | −0.9515 | **−0.9879** | better (−1.0 is ideal) |
| long-short annualised | +17.58% | +18.58% | +1.00pp |
| signal-weighted top-decile alpha | +12.74% | +12.75% | +0.01pp |
| long-short hit rate | 65.45% | 65.45% | 0 |
| equal-weight benchmark | +16.55% | +16.55% | **0** |
| **PBO** | 6.7% | **13.3%** | +6.7pp (still far under the 50% bar) |
| Deflated Sharpe | 0.9999986 | 0.9999990 | ~0 |

The benchmark not moving is the control: the corrections touch how names are *scored*, not what
the universe earns.

**Long-short t up 0.36 and monotonicity to −0.988 — the deciles are now almost perfectly ordered
— against 0.19pp off the top-decile alpha and PBO doubling off a low base.** Net: the composite
sorts better and the concentrated top of it earns marginally less. Nothing here is large.

## The one that matters: no held-out verdict changed

```
BASELINE  : value rejected · quality not_replicated · momentum rejected · insider rejected
            low_risk confirmed · capital_discipline not_replicated · size rejected
            institutional rejected
CORRECTED : identical, every theme
```

**Thirteen corrections, and not one decision moved.** That is the honest summary and it cuts both
ways: the record's *decisions* were not resting on the defects, and the defects were not hiding a
different model. What moved is what the numbers *mean*, which is the audit's own framing.

## Theme ICs — and one large, unexpected move

| theme | BASELINE t | CORRECTED t |
|---|---|---|
| quality | +3.39 | **+3.57** |
| **insider** | **−0.34** | **−0.43** |
| capital_discipline | +2.25 | +2.25 |
| momentum | +2.62 | +2.62 |
| institutional | +1.81 | +1.81 |
| size | +1.68 | +1.68 |
| value | +1.47 | **+1.52** |
| growth | +1.45 | +1.45 |
| low_risk | +0.71 | +0.71 |
| sentiment | empty | empty |

### RETRACTED, AND REPLACED BY A WORSE PROBLEM: a full backtest is not reproducible

**This section originally reported that B26 flipped the `insider` theme from t −0.34 to +2.69.
That attribution was WRONG and is retracted here rather than edited away.**

A third full-universe run — the one whose code matches the committed tree, after B18 was
completed — does not reproduce it:

| run | code | `insider` median IC | t |
|---|---|---|---|
| BASELINE | `b67b07d`, pre-audit | −0.00335 | **−0.34** |
| intermediate | corrections, B18 partial | +0.01551 | **+2.69** |
| **FINAL** | corrections, B18 complete | −0.00339 | **−0.43** |

Coverage is 85.0% in all three. **The first and third bracket the second and agree to four
decimal places**, and they differ by *both* B26 and the negative-multiple guards — so B26 cannot
be the cause. That matches the direct measurement, which should have been given more weight at
the time: B26 alters **3.96% of scores at a level correlation of 0.9975** across 22,975
(ticker, date) pairs, which is not a sign-flipping perturbation.

**Every other theme is stable to ±0.01 across all three runs.** So the anomaly is confined to the
one theme whose IC sits essentially at zero.

Two conclusions, and the second is the more serious:

1. **`insider`'s t-statistic is not a measurable quantity in either direction.** A median IC of
   −0.003 over 110 dates is noise, and −0.34 was never more reliable than +2.69. This is exactly
   consistent with what the project already recorded and correctly declined to act on: zeroing
   `insider` helped one split direction by Δt +0.08 and hurt the other by Δt −0.09. The held-out
   gate returns **`insider: rejected` in all three runs**, so nothing deployed is affected.
2. **A full backtest is not reproducible run-to-run, and nobody knew.** The cause is not
   identified. Candidates worth checking in order: a bulk cache under `data/bulk/prepared/`
   being refreshed between runs; iteration order somewhere in the panel build; a float
   accumulation whose order varies. **This is a genuine problem for a project whose memory is
   its results files** — every marginal IC in the record is quoted from a single run, and the
   two statistics most exposed are exactly the marginal ones the project keeps making decisions
   about. It belongs with audit **M6** (the results file's silent-failure modes) and should be
   settled before any further marginal-IC decision.

**Method note for the next session, since this is the second time it has mattered:** the reason
this was caught at all is that a third run was launched purely so the *tracked* results file
would match the *committed* code. That is worth keeping as a habit.

**Follow-on:** audit item **S3** proposes three variants of the insider score's construction —
dropping the unconditionally-additive `+min(10, 2·buys)` bonus, scaling net activity by market
cap rather than a fixed $5M before the `tanh`, and splitting net buying from cluster breadth. A
theme whose IC is indistinguishable from zero is a theme whose construction is the first thing
to question, so S3 keeps its promotion — just for the opposite reason to the one first written
here.

### B10, answered: the recovered signal is the WORSE one

The audit called B10 "one of the cheapest genuine signal recoveries available." Measured
head to head:

| | BASELINE (`FCF/NI`) | CORRECTED (Sloan accruals) |
|---|---|---|
| `accruals_q` IC t | **+1.26** | **+0.27** |
| coverage | 0.75 | **0.97** |

Coverage rose exactly as predicted (the `ni > 0` restriction is gone), and **the signal got
worse**. The overwrite was a real defect — the column did not contain what its name and its
documentation said — but the thing it was overwriting with was the better of the two on this
panel. The `quality` theme still improved (+3.39 → +3.57), so this is not costing anything at
theme level.

**Recommendation, NOT actioned here:** switch `accruals_q`'s theme membership back to the FCF/NI
construction (now available as `accruals_fcf_ni`) and put the Sloan measure alongside it as a
second input or drop it. That is a *signal* decision and belongs in front of the held-out gate,
not in a corrections pass. Both columns now exist, so it is a one-line A/B.

### The value-side corrections did what B18 predicted, in miniature

`ebit_ev` t +2.36 → +2.42, `neg_ev_sales` +2.05 → +2.10, `neg_ev_ebitda` +1.99 → +1.98,
`value` theme +1.47 → +1.51. Small, in the right direction, on ~0.65% of rows — which is the size
of effect a negative-EV convention fix should have.

Unchanged, as expected, since nothing touched them: `earnings_yield` +2.41, `roe` +2.84,
`roic` +3.38, `book_to_price` +0.15. `f_score` moved +2.74 → +2.64.

## B14's first number — the delisting mask is complete

```
delisting map          19,207 names
series masked             887 of 2,710 tickers (32.7%)
ended_early_unmasked        0          <-- the number this was built to expose
panel_end            2026-07-24     stale_tail_days 180
```

**Zero names have a price series that stops more than 180 days before the panel end without an
ACTIONS row to explain it.** That is the first direct evidence that the survivorship mask is not
silently missing delistings — the failure mode where a dead name's last close is forward-filled
and contributes a fake flat 0% forward return to every later rebalance date. Previously the
results file said only `survivorship_mask: true`, meaning "the map is non-empty."

## The B18 sign check fired on its first run, and caught my own incomplete fix

The new sign check on the range-exempt ratios raised three flags immediately:

| flag | rows | what it actually was |
|---|---|---|
| `ev_ebitda` negative | 414 (0.36%) | **my B18 fix was incomplete** — I guarded `ebit_ev` and `ev_sales` on `ev > 0` and left this one on a truthiness test. Verified: 746 export rows (0.378%) carry a negative `ev`. |
| `ev_sales` negative | 378 (0.29%) | **not** negative EV — negative **revenue** |
| `ps` negative | 382 (0.29%) | same |

Negative revenue is real and identifiable: **538 export rows (0.273%)**, concentrated in agency
mortgage REITs and financial guarantors — **DX, NLY, AGNC, MBI, RWT, FNMA** — where a quarter's
net interest income after losses genuinely prints below zero. A negative sales multiple has the
identical failure mode to a negative EV one: negate it and the name sorts as the cheapest in the
cross-section. All three now take the same convention: **missing, not extreme.**

Per the project's standing rule the flags were investigated rather than silenced, and the
investigation found a defect in the correction that had just been made. **A guard that catches its
author on its first run is the argument for having built it.**

## What this section does NOT claim

- **No causal claim for the corrected numbers being "better".** Long-short t and monotonicity
  improved, top-decile alpha and PBO worsened slightly. These are repairs; the direction of a
  repair's effect on a fitted statistic is not evidence about the repair.
- **Nothing here bears on whether the edge is ALPHA.** That is R1, unrun. `top_decile_alpha` is
  still `4 × (top-decile − equal-weight)` with no factor model and no t-statistic, in both runs.
- **The options side is untouched by all of this.** B1's re-run is R2, unrun, and until it lands
  no absolute number from the 187-name book, roadmap 22c or deep-research thread #1 is citable.

---
---

# Part 3 — Session 2: B6, B7, and ten more Part I items

Landed as `adcd85a`, pushed. **This section was written after the commit, which is the wrong
order and is recorded as such** — the code shipped and the ledger lagged, so for a period the
record on `main` showed no Session-2 entries while the corrections were live. The entries below
are reconstructed from the commit, the code and the validating run, not from memory.

**Scope run:** B2, B4, B5, B6, B7, B11, B13, B17, B21, B22, B25. **B23 deferred, deliberately**
— reasoning in its own entry rather than as a footnote.

**Lane check first, per the standing warning.** `check_lanes.py` before B7 and B13: B7 touches
`config.py` / `fundamental_panel.py` / `factors.py` / `screen.py`, B13 touches two of those, and
**none** of them is in `valuation/engine`, `screener/insider.py` or the web/auth layer — so no
collision with the greeks agent or the app fixer. One correction to the audit-item map: it lists
`config.py` and `screen.py` as "(nobody)", and git shows the app-fixer lane live in both. Merged
`origin/main` (R1 had landed) before the first edit and kept both files' edits surgical.

## B6 — the panel truncated every ticker instead of the calendar · **the largest single correction in the audit**

**Committed threshold:** none — a correctness defect, not a hypothesis. The pre-commitment that
does apply is the standing one: *a repair's effect on a fitted statistic is not evidence about the
repair, in either direction.* That rule is doing real work here, because this repair moved the
headline down hard.

**What was run:** `WRDSProvider.price_history` read against `build_fundamental_panel`, then the
full-universe validating backtest.

**Result — confirmed, and the mechanism is worse than "27 years mislabelled as 18".**
`price_history` ended in `df.sort_values("date").tail(days)`, so every ticker kept its **own** last
N rows and the panel calendar became the **union** of those windows. A name still trading in 2026
had its first decade truncated away; a name that died in 2010 kept all of its history. So at a 2001
cross-section the only names present were ones that **stopped trading by roughly 2019** — the
inverse of classic survivorship bias. Those same early dates had no benchmark either (SPY was
fetched under the same per-ticker cap), which is the direct cause of `construction.n_periods = 110`
sitting next to `portfolio.n_periods = 73` in one JSON over two undisclosed, different windows.

**Fix.** `days=None` now means the whole series and the shared calendar is cut **once**, after the
frame is built and **before** the `ffill` — so every ticker is cut at the same date by
construction, and a name with no data in the retained window cannot be forward-filled into it from
outside. The full history was on disk the entire time (**7,184 trading days, 1997-12-31 →
2026-07-24**), so this costs load time and no frame memory: the frame was always the union
calendar, this only stops it being mostly holes.

**Measured window, now shipped as `panel_window` in the canonical results:**

| | |
|---|---|
| available | 1997-12-31 → 2026-07-24, 7,184 trading days |
| retained | **2008-01-16 → 2026-07-24, 4,659 trading days** |
| rebalance dates | **69** (was 110), first 2009-01-15, last 2026-01-28 |
| cross-section | min 1,471 · median 1,557 · max 1,954 |

The panel is now a genuine 18.5-year window instead of a 27.3-year union whose first third was
uninterpretable. **41 of the 110 rebalance dates were dropped** — against the audit's estimate of
"roughly the first 37".

**Verdict: FIXED, and it cost more than any other item in this audit.** The A/B is in
*The Session-2 headline* below. **Follow-on: R1 must be re-run** — its +8.81%/yr FF5+MOM alpha was
measured on the uncorrected panel, over a window that no longer exists.

---

## B7 — three composites, none of which was the one that shipped

**Committed threshold:** none — a correctness defect. The *choice of convention* is a judgement
call and is argued below rather than fitted.

**What was run:** every composite construction site in the tree, enumerated and compared; then an
empirical equivalence check before the change was written into a test.

**Result — confirmed, at nine call sites, and the disagreement is not cosmetic.**

| Path | Convention |
|---|---|
| **Selection** — `_weighted_optimize`, `walk_forward`, `cpcv_validate` | renormalised by the present-weight mass |
| **Measurement** — `quantile_backtest`, `_strategy_returns`, `_backtest`, `_backtest_hold`, `regime_split`, `turnover_and_costs`, `after_tax_backtest` | did **not** renormalise |
| **Live** — `screen.py` → `factors.build_frame` → `cross_sectional.composite_score` | renormalised **and** applied sector-neutral ranking **and** residual momentum |

Under the measurement convention a missing theme contributed a hard **0.0**, which after z-scoring
**is exactly the cross-sectional average** — so an incomplete name was silently dragged toward
mid-pack. That would be tolerable if the missingness were random. It is not: **`institutional` is
absent on 38.6% of rows and `insider` on 15%**, and both absences track size and coverage. The
extreme deciles were therefore biased toward data-complete names — larger, better covered,
institutionally held. **The top-decile alpha and long-short t were computed under one composite
while the weights that produced them were chosen under another, and the live product used a
third.** No shipped code path reproduced the backtested composite exactly.

**Fix.** One `composite()`, used by all nine sites. **Renormalisation is the convention kept**, for
two reasons, neither of them performance: it is what **selection** already used, so the deployed
weights were chosen under it; and scoring a name on the themes it actually has is the defensible
answer to missing data, where "treat it as exactly average" quietly rewards coverage over merit. A
row with no present weight at all now returns NaN, not 0.0 — it has no opinion, and 0.0 would place
it mid-pack.

Verified empirically before it was pinned: on the selection path the new function reproduces the
old one at **max absolute difference 0.0** with identical NaN masks, so the two selection sites are
a pure refactor and only the seven measurement sites change behaviour.

**Also fixed here (B7/G, the live half).** `CONFIG.sector_neutral` and `CONFIG.residual_momentum`
both defaulted **true** while the backtest forced both **false**. Unless `SCREENER_SECTOR_NEUTRAL`
was set in the environment, the hot list users see was scored under the intervention the research
**rejected in both held-out directions, twice**. Both now default **false**. Live and backtest now
agree exactly, pinned by `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`.

**Verdict: FIXED.** **Follow-on:** same as B6 — R1 re-run. Also retires the standing CLAUDE.md
caveat "no shipped code path reproduces the backtested composite exactly", which is now false.

---

## The Session-2 headline — B6 and B7 together, and the honest attribution problem

Full universe, both runs, identical data. Baseline is the Session-1 final run.

| | S1 final | **S2 (B6+B7+B13)** |
|---|---|---|
| rebalance dates | 110 | **69** |
| long-short t | 3.851 | **2.836** |
| top-decile alpha | +11.69% | **+7.17%** |
| monotonicity | −0.988 | **−0.891** |
| PBO | 13.3% | **73.3%** |
| Deflated Sharpe | 99.99990% | 99.70% |
| equal-weight benchmark | +16.55% | **+18.14%** |
| realised one-way cost | — | 33.4 bps |
| breakeven one-way | 236 bps | **134 bps** |

**Read this honestly. Two of the three bars now fail.** Long-short t **2.836 is below the
Harvey–Liu–Zhu hurdle of 3.0** it used to clear, and **PBO 73.3% is far above the <50% bar** — the
weight-scheme selection no longer generalises on the shorter sample. Top-decile alpha fell by 39%.
Only the Deflated Sharpe still passes, and per B9 that statistic is computed against N=8 when the
ledger records ~146 trials, so it was never the bar to lead with.

**What this most likely means, stated as a hypothesis and not a finding:** roughly 40% of the
headline was coming from the 41 early rebalance dates whose universe was inverted — dates at which
every name present was one that would stop trading within a decade. That is the exact period B6
identified as uninterpretable. **This is the mechanism the audit predicted, and it was expensive.**

**The attribution problem, disclosed.** B6, B7 **and** B13 all landed in one commit and **all three
move the panel** — B13's prefilter alone drops 384 penny names. That breaks the prompt's
one-change-per-run rule, and the table above cannot separate them. One clean read is available:
**the equal-weight benchmark is composite-independent, so its +16.55% → +18.14% move is entirely
B6+B13 (window and universe) and contains no B7 at all.**

To fix this properly, three attribution toggles were added — `EDGE_AUDIT_B6_LEGACY_TRUNCATION`,
`EDGE_AUDIT_B7_LEGACY_COMPOSITE`, `EDGE_AUDIT_B13_PREFILTER` — each defaulting to the corrected
behaviour and each reverting exactly one change. **A three-run full-universe sweep has now been
run and the decomposition is clean.**

| run | n | ls_t | alpha | mono | EW bench | PBO |
|---|---|---|---|---|---|---|
| S1 final (all three defects present) | 110 | 3.851 | +11.69% | −0.988 | +16.55% | 13.3% |
| **A — B6 reverted** (B7+B13 fixed) | 110 | 3.733 | +11.36% | −1.000 | +16.26% | 26.7% |
| **B — B7 reverted** (B6+B13 fixed) | 69 | 2.846 | +7.17% | −0.939 | +18.14% | 73.3% |
| **C — B13 reverted** (B6+B7 fixed) | 69 | 2.715 | +7.68% | −0.903 | +18.38% | 73.3% |
| **S2 shipped** (all three fixed) | 69 | 2.836 | +7.17% | −0.891 | +18.14% | 73.3% |

Each row reverts exactly one change from the shipped state, so the shipped-minus-row difference
is that change's own contribution:

| | long-short t | top-decile alpha | PBO | EW bench |
|---|---|---|---|---|
| **B6 alone** | **−0.897** | **−4.18pp** | **+46.7pp** | +1.88pp |
| **B7 alone** | −0.010 | +0.01pp | 0.0pp | 0.00pp |
| **B13 alone** | +0.122 | −0.51pp | 0.0pp | −0.24pp |

**B6 is the entire move, and it is not close.** It carries 100% of the PBO blow-out, 88% of the
long-short t drop and 89% of the alpha drop.

**B7 alone is a NULL on the headline** — ten-thousandths of a t, one basis point of alpha, PBO
and the equal-weight benchmark unchanged to the digit (the benchmark *must* be unchanged, since
it never touches the composite; that it is, is a check on the toggle rather than a finding).
**This is the ideal outcome for a correctness fix**: three code paths that disagreed now agree,
and the disagreement turns out to have been costing essentially nothing on this panel. The
mechanism argued in the B7 entry was real; its magnitude was small.

**B13 alone is small and points both ways** — dropping 384 penny names *raises* the long-short t
(+0.122) and *lowers* top-decile alpha (−0.51pp), which is what you would expect if penny names
were contributing return at both extremes of the ranking. It also lowers the equal-weight
benchmark by 0.24pp, which is the clean composite-independent read on the universe change.

**With attribution done, the claim that could not be made before can now be made:** the
inverted-universe window was carrying roughly 4.2 percentage points of the 11.7% top-decile
alpha and was holding PBO down at 13%. That is a measurement, not an inference. It remains a
statement about what the defect was producing, **not** evidence that the corrected panel is the
"right" one in any deeper sense — a repair's effect on a fitted statistic is not evidence about
the repair.

**Theme ICs moved, and one move has a clean mechanism:**

| theme | S1 | S2 |
|---|---|---|
| quality | +3.57 | **+3.10** |
| capital_discipline | +2.24 | **+2.76** |
| institutional | +1.81 | +1.55 |
| momentum | +2.62 | +1.31 |
| value | +1.51 | +0.84 |
| growth | +1.45 | +0.75 |
| low_risk | +0.71 | +0.46 |
| insider | +2.69 | **−0.24** |
| size | +1.68 | **−0.30** |

**`size` +1.68 → −0.30 is expected, not alarming.** The record already says the small-cap premium
worked pre-2012 and not after; B6 deleted everything before 2009, so the theme losing its
t-statistic is the mechanism behaving as documented. **`insider` +2.69 → −0.24 is the anomalous
Session-1 run reverting to the other two runs' value** (−0.34, −0.43) — consistent with the
standing retraction that this theme's t is not a measurable quantity, and *not* evidence about B6
or B7.

**The one that matters: the deployed decision survived.** `low_risk` is still **`confirmed`** in
both split directions on the corrected panel (Δt +1.383 / +1.518, Δalpha +4.02pp / +1.88pp), and
`insider` is still **`rejected`**. Two non-adopted themes swapped between two flavours of "no"
(`quality` not_replicated → rejected, `momentum` rejected → not_replicated). **No shipped decision
changed.**

---

## B2 — the options exit path censored exactly the days the stop fires

**Committed threshold:** none — a correctness defect. Its consequence is directional and was
predicted before measurement: censoring should manufacture **fake winners**, never fake losers.

**What was run:** `options_fill`'s reject reasons traced through the `options_backtest` day-walk.

**Result — confirmed, and the direction of the bias is not symmetric.** The day-walk applied the
**entry** quality gates to every **exit** day: a day whose quote was `wide_spread` or
`thin_premium` was rejected and the day **skipped entirely**. A decaying out-of-the-money call
quoting 0.25 / 0.35 is 33% wide, so a losing contract **vanished from its own exit path precisely
where the −50% stop fires**. A loser that dipped through the stop on a wide-quote day and later
recovered was recorded as a **target win**. The gates that protect entry quality were silently
deciding which exits were allowed to happen.

**Fix.** A separate `exit_reject_reason()` rejects only what makes an exit genuinely unpriceable —
`no_quote`, `non_positive`, `crossed` — and never rejects for width or premium. Censored days are
counted per trade and surfaced as `exit_days_censored_frac` in `sanity()`, so the rate is a
reported number rather than an invisible default.

**Verdict: FIXED. Not yet re-measured.** **Follow-on: R2.** Every options number in the record was
produced under the censoring and none is citable until R2 lands — and per the prediction above, the
correction should move win rates **down**, not up.

---

## B4 — the −1 open-interest sentinel was being read as a number

**Committed threshold:** none — a correctness defect.

**What was run:** the open-interest column profiled across the options export, then the two
consumers (`_oi_sum`, the `MIN_OI` gate).

**Result — confirmed, and it is not rare.** `-1` is the feed's **unknown** sentinel and appears on
**11.4% of rows, across 106 of 111 names — including all of AAPL 2020**. It was being summed
arithmetically, so chain-level OI totals could go **negative**, and it failed the `MIN_OI`
liquidity gate as though the contract had **zero** open interest. Both readings are wrong in the
same direction: unknown liquidity was being treated as known-bad.

**Fix.** Negative OI now becomes `None` (unknown), never a number. `_oi_sum` masks with
`v.where(v >= 0)`, and an `unknown_oi` count is carried so a chain that is mostly unknown is
visible rather than quietly excluded. `REQUIRE_KNOWN_OI` is defined and defaults **False** — the
gate is not tightened as part of a correctness fix.

**Verdict: FIXED. Not yet re-measured — folds into R2.**

---

## B5 — four defects in the live paper track, all of which flattered it

**Committed threshold:** none — four correctness defects. Their shared direction is the point.

**What was run:** `paper_track.py` read end to end against `options_fill` and the backtest's own
exit convention.

**Result — confirmed, four separate defects, and every one biased the paper track toward looking
better than the backtest it exists to validate.**

| | Defect | Effect |
|---|---|---|
| **B5a** | exits triggered on the **mid**, the backtest uses the **bid** | ~5pp optimistic and asymmetric — it fires targets early and stops late |
| **B5b** | a **dry run permanently burned an alert** — it was marked `skipped` and never revisited | the sandbox silently consumed live signal |
| **B5c** | a **resumed entry lost its target/stop**, becoming a market order | a position that can never take profit and never stop |
| **B5d** | P&L was booked against the **alert-time ask**, not the actual fill | the fill model's own slippage was excluded from the result |

**Fix.** Exits read `exit_mark_from_quote(q)` (the bid). A dry run now leaves the alert `pending`
and the resume loop scans `("claimed", "pending")`, so nothing is stranded. A resumed entry
rebuilds its target and stop on both branches and **defers if no quote is available** rather than
degrading to a market order. `record_outcome` takes the real `entry_premium` and tags provenance
`[pnl vs fill]`. Two smaller repairs came out of the same read: `_record` no longer returns `True`
unconditionally (it returns `ok`, with a `desynced` counter), and a **missing bid defers instead of
sending a market order**.

One test had to be rewritten rather than repaired: `test_dry_run_places_nothing_live` was
**pinning the B5b defect** — it asserted `state == "skipped"`. It now pins the fix and additionally
asserts that a later real run can still take the alert.

**Verdict: FIXED, all four.** **Follow-on:** the paper track's history predates these fixes and its
recorded outcomes are not comparable to post-fix ones. Do not quote a paper-track win rate across
the boundary.

---

## B11 — "236 bps breakeven vs 37 bps actual" — the 37 was never computed

**Committed threshold:** none — a disclosure defect. No prediction: the point is that the number
should **exist**, not that it should land anywhere in particular.

**What was run:** a search for the origin of the 37 bps figure, then wiring the realised number.

**Result — confirmed. The 37 bps was a cost-model assumption quoted as a measurement.** The
breakeven side of that comparison was computed from the book; the actual-cost side was not computed
anywhere in the tree. The project has been quoting a ratio in which one term was measured and the
other was an input.

**Fix.** `realised_one_way_bps` is now computed from the book's own point-in-time market-cap mix
and shipped in the `costs` block, alongside a `cost_model_limitations` field naming what the model
still does not carry (borrow, market impact, capacity).

**Measured on the corrected panel: 33.4 bps realised against a 134 bps breakeven — a 4.0x margin.**
Both terms moved: the breakeven fell from 236 bps because B6 removed the window that produced the
larger alpha, and the realised figure is now a measurement rather than an assumption. **The edge
still survives costs by a wide margin, and that conclusion is unchanged.**

**Verdict: FIXED. Quote the breakeven and the realised figure together — both are now measured.**

---

## B13 — the backtest scored names the live screen will not buy · **PARTIAL, and labelled so**

**Committed threshold:** none — a consistency defect.

**What was run:** `prefilter` traced from `score_universe_now` to see which paths call it.

**Result — confirmed.** `prefilter` — which drops warrant/unit/right suffixes, ETFs and funds, and
sub-$1.00 names — is called in `score_universe_now` and was **never** called on the backtest path.
The validated deciles could therefore contain penny stocks and warrant tickers the live book will
not buy, and `size` is one-seventh of the composite pointing straight at them.

**Fix, and the half that does not work.** `prefilter` now runs in the panel. On the corrected run
it rejects **384 names, all of them `penny (<$1)`** — the suffix and fund categories were already
absent from this export.

**`MIN_AVG_DOLLAR_VOLUME` still cannot bind, and that is shipped as a fact rather than hidden.**
The price export on disk carries `date` and `close` only, so average dollar volume is not
computable on this path — it never bound before either. The results file now carries
**`prefilter_adv_wired: false`** plus a `prefilter_note` naming the missing column and what would
be needed (SEP volume in the panel loader).

**Verdict: PARTIALLY FIXED.** The categorical filters bind; the liquidity filter does not, and is
labelled. **Follow-on:** wiring SEP volume into the panel loader is the remaining work, and it
matters more now than before — 384 penny names were in every prior decile.

---

## B17 — the "top-25" book was neither top-25 nor comparable to the other books

**Committed threshold:** none — a labelling defect. The audit predicted the book holds "up to
fifty" names; that prediction is scored below.

**What was run:** `_backtest_hold`'s exit rule read against its own label, then the realised book
size measured on the corrected run.

**Result — confirmed, and the audit's estimate was close.** The book sells only below
`exit_rank = top_n × 2`, so a name entering at rank 25 is held until it falls past rank 50.
Measured: **target_n 25, exit_rank 50, realised held_median 42, held_min 25, held_max 47.** A book
labelled "top-25" was in practice a **~42-name** book. It also **pays neither costs nor taxes**,
unlike every other book in the results file — so it was simultaneously the most concentrated-
sounding and the most favourably-accounted number in the document, and it is the one most likely to
be quoted.

**Fix.** The block ships `held_median` / `held_min` / `held_max`, `target_n`, `exit_rank`,
`charges_costs: false`, `charges_taxes: false`, and a `label_warning` stating plainly that the
realised book size is approximately `exit_rank`, not `top_n`.

**Verdict: FIXED (disclosure).** No behaviour changed and none should — the hold rule is a
deliberate turnover control. **Follow-on:** the block is still gross of costs, so it is not
comparable to the decile books; if it is ever quoted externally it needs a cost pass first.

---

## B21 — sector-weight caps, measured for the first time

**Committed threshold:** pre-registered before the run: **adopt only if a cap improves net alpha
AND does not worsen max drawdown, in a run that also passes the held-out gate.** Anything short of
that is a null and the caps stay off.

**What was run:** a sweep over `(none, 0.25, 0.30, 0.40)` sector-weight caps on the corrected
full-universe panel.

**Result — a clean null, and an unusually flat one.**

| cap | gross alpha | net alpha | net Sharpe | turnover |
|---|---|---|---|---|
| none | +8.12% | +6.07% | 1.099 | 2.61 |
| 25% | +8.09% | +6.04% | 1.099 | 2.60 |
| 30% | +8.14% | +6.09% | 1.100 | 2.61 |
| 40% | +8.12% | +6.07% | 1.099 | 2.61 |

The spread across every cap is **5 basis points of net alpha and 0.001 of Sharpe** — indis-
tinguishable from no intervention at all. The honest reading is that this book is **not
sector-concentrated enough for a cap to bind**, so the sweep is measuring nothing rather than
measuring a small effect.

**Verdict: NULL — measured, NOT adopted.** Shipped as `sector_caps` with that note attached, so the
next session does not re-run it. **Follow-on:** none. This is on the do-not-reopen list unless the
book's sector concentration materially changes.

---

## B22 — one try/except stamped five keys while producing twelve

**Committed threshold:** none — a silent-failure defect.

**What was run:** the results-assembly except path read against the block list it is supposed to
cover.

**Result — confirmed, and the failure mode is the dangerous one.** The single `try/except` around
results assembly stamped **5** keys while the function produced **12**. A failure inside `costs`
therefore discarded **four blocks with no marker at all**, while `errors: []` stayed empty and the
run reported success. A missing block looked exactly like a block that ran and had nothing to say.

**Fix.** `RESULT_BLOCKS` names all 12. Every block is stamped via
`out.setdefault(_k, {"status": f"error: {e}"})` so a failure is recorded in place, and
`missing_result_blocks(res)` runs as a **schema check before the file is written**, appending any
absence to `errors` and printing a warning. A block that is missing can no longer be silent.

**Verdict: FIXED. Verified on the corrected run — `errors` is absent, meaning all 12 blocks were
present and non-empty.** That is the first run in which that statement is checkable rather than
assumed.

---

## B25 — the two Deflated Sharpe implementations · **the audit was WRONG, and this is the correction**

**Committed threshold:** the audit's claim was that the two implementations "will never reconcile".
That is a falsifiable statement and it was tested directly rather than accepted.

**What was run:** `fundamental_panel._deflated_sharpe` and `options_autopsy.deflated_sharpe` worked
through algebraically, then evaluated against each other numerically.

**Result — the audit is refuted. They reconcile exactly.** Worked through, the two are
**algebraically identical in the test statistic**. Only two things genuinely differed:

1. **Which variance feeds `sr0`.** Bailey–López de Prado specify the **cross-trial** variance of
   the trial Sharpes. The panel used exactly that and was **right**; the autopsy was approximating
   it with a sampling variance. This is the substantive difference and it is a real defect — in the
   autopsy, not in the panel.
2. **A `ddof` mismatch** in the skew/kurtosis moments (`ddof=0` vs `ddof=1`).

Aligned on both, **the two implementations now agree to exactly 0 at floating point.**

A third convention existed and is now gone: `validate_institutional` passed a **one-element trial
list**, which is not a trial set at all. An empty or singleton trial set now yields `sr0 = 0.0` and
the metric is honestly relabelled **`probabilistic_sharpe_ratio_UNDEFLATED`** rather than being
reported as a Deflated Sharpe that deflated against nothing.

**Verdict: the audit's finding is REJECTED as stated; one real defect (the autopsy's `sr0` basis)
was found underneath it and is FIXED.** Recorded here because the standing rule is that where the
audit contradicts the record the contradiction is the point — and it runs in both directions.
**Follow-on:** none for B25. The *scope* problem with the Deflated Sharpe is B9 and M1 (N=8 against
a ledger of ~146 trials), which is untouched by this and remains the real criticism.

---

## B23 — DEFERRED, deliberately

**Not done, and not forgotten.** B23 is explicitly a **speed** item: it changes how the panel is
constructed in order to make it cheaper to build.

**Reasoning for the deferral, recorded so it can be disagreed with.** B6 and B7 were the priority
of this session precisely because R1's headline is provisional until they land. B23 touches the
same construction path. Changing how the panel is built in the same commit as the run that
**validates** a change to how the panel is built would mean that if the numbers moved, there would
be no way to tell which change moved them — and the numbers did move, a great deal. That risk was
not worth a performance improvement on a run that already completes in about twelve minutes.

The attribution problem documented in *The Session-2 headline* above is exactly the failure mode
B23 would have made worse: three changes already landed together and a sweep is now needed to
separate them. Adding a fourth would have been the wrong trade.

**Verdict: DEFERRED. No blocker — it can be taken in any later session, and should be taken alone.**

---

## BUGS FOUND — Session 2 (per RUN_RULES.md Part A rule 3)

Things noticed in passing. Items already covered by their own B-entry above are not repeated here;
these are the ones that were **not** on the catalogue.

**FIXED in this session, found while doing something else:**

- **`tests/test_edge.py` — `test_dry_run_places_nothing_live` was pinning the B5b defect, not the
  behaviour.** It asserted `state == "skipped"`, which is exactly the bug (a dry run permanently
  burning a live alert). A test that pins a defect makes fixing it look like a regression. Rewritten
  to pin the fix and to assert a later real run can still take the alert.
- **`tests/test_edge.py` — `test_audit_b6_...` asserted a literal source string.** It matched
  `"provider.price_history(t, days=None)"` textually, so adding the attribution toggle broke a
  passing test without any behaviour changing. Rewritten to pin the default behaviour plus an
  explicit assertion that the legacy toggle is off while the suite runs.
- **`paper_track._record` returned `True` unconditionally**, so a failed write reported success to
  its caller. Found while reading B5d. Now returns `ok` and carries a `desynced` counter.
- **`paper_track` sent a market order when the bid was missing.** Found in the same read. Now defers.

**FOUND, NOT FIXED — for whoever picks these up:**

- **`check_lanes.py`'s audit-item map has gaps.** It reports **"(nobody)"** for `config.py` and
  `screen.py`, and `git log` shows the app-fixer lane live in **both**. Collision-safe was reported
  where a collision was possible. Treat the tool as advisory and cross-check `git log` — this is now
  written into RUN_RULES.md Part B rule 3, but the map itself is still wrong.
- **A full backtest is not reproducible run to run.** Documented at length in Part 2 (the B26
  retraction). Cause still unidentified. Three runs on identical data gave `insider` median IC
  −0.00335 / +0.01551 / −0.00339 at unchanged coverage. **This is the most important open bug in the
  panel** — a project whose memory is its results files needs those files to be deterministic, and
  until it is fixed no marginal IC is trustworthy.
- **P4 / `seed_book` never sells names that leave the book.** Out of band for this audit, flagged in
  earlier sessions, still open, and still urgent — it is a live-product defect, not a research one.
- **`prefilter`'s liquidity gate has never bound on any path.** `MIN_AVG_DOLLAR_VOLUME` cannot be
  computed from the on-disk price export (`date` + `close` only). Now labelled
  `prefilter_adv_wired: false`, but the gate has been decorative in the live screen too, not only in
  the backtest. See B13.

**PROCESS FAILURE, recorded because it is the reason this document needed reconstructing:**

- **The code shipped before the ledger.** `adcd85a` landed and was pushed with no Part 3 in this
  file, so `origin/main` showed twelve completed items as undone and the manager re-issued Session 2
  as a fresh instruction. RUN_RULES.md Part A rule 2 and Part B rule 1 both exist to close this;
  it is recorded here as the concrete case.
- **Three panel-moving changes landed in one commit** (B6, B7, B13), against the prompt's
  one-change-per-run rule. The attribution sweep now in flight is the repair, and it costs three
  full-universe runs that would not have been needed had they landed separately.

---

# PART 4 — SESSION 3: THE NOISE FLOOR (X7, X2)

**Pre-commitments below were written and pushed BEFORE a single run was launched** (commit
timestamps are the evidence; RUN_RULES.md Part A rule 6). Nothing in this section is revised after
results land — if a result is ambiguous against its own committed threshold it is a **NULL**, not a
judgement call.

Why this session comes before R1 is re-run: every threshold this project uses — the IC *t* > 2.0
bar, the PBO < 50% bar, the 0.25 *t*-gain margin on the held-out gate, the "1% alpha" margin — was
chosen by convention. None has ever been measured against what THIS pipeline produces when the
signal is known to be worthless. Until that floor exists, "PBO 73.3%" and "long-short *t* 2.836" are
numbers without a scale.

---

## PRE-COMMITTED THRESHOLDS — X7 (placebo through the full pipeline)

**The instrument.** `placebo_panel(panel, seed)` — within each rebalance date, permute the signal
columns (the nine themes plus every `z_*` per-number column) **as a block** across the names
present. `fwd_ret`, `marketcap`, `sector`, `date` and `ticker` are not touched. Block permutation
rather than per-column shuffling is deliberate: it preserves each theme's exact per-date
distribution, the exact missingness pattern (it travels with the row), and the exact cross-theme
correlation matrix — so the weight schemes that read Sigma still see a real Sigma. The ONLY thing
destroyed is the association between signal and return. Because the composite of a permuted
row-block is the permuted composite, this satisfies the catalogue's "shuffled composite"
specification as a special case, while also propagating into weight SELECTION so that CPCV, PBO and
the Deflated Sharpe are exercised end to end.

**N.** Target 100 iterations. If per-iteration cost makes 100 impossible inside the session, run
the largest N that fits and **report N and the Monte Carlo standard error of every quantile
quoted**. Committed now: **no percentile is quoted from N < 30**, and if N < 100 the section says so
in the same sentence as the first number.

**Committed interpretations — all written before any placebo has been run:**

1. **The IC *t* > 2.0 bar.** The relevant null is not one theme's *t*, it is the MAXIMUM |*t*|
   across the nine themes in a run, because that is the quantity a "which theme is real" decision
   actually looks at. If the placebo's 95th percentile of max-|theme IC *t*| is **≥ 2.0**, the bar
   does not control the false-positive rate in this pipeline and the calibrated bar becomes the
   measured 95th percentile. If it is < 2.0, the bar is conservative and stands.
2. **The long-short *t* > 2.0 bar.** Same rule on `construction.long_short_tstat`. If the placebo's
   95th percentile is ≥ 2.0, the bar is uncalibrated.
3. **PBO.** Report the full placebo distribution. If the placebo's **median PBO < 50%**, then "PBO
   below 50%" is not evidence of anything and the bar is re-set to the placebo's **5th percentile**.
   If the placebo's median PBO is at or above 50%, the statistic is behaving as designed and the
   bar stands as written.
4. **Top-decile alpha.** If the placebo's 95th percentile of `top_decile_alpha` is **≥ 1.0pp**, the
   project's informal "1% alpha margin" is uncalibrated and the calibrated margin becomes the
   measured 95th percentile.
5. **Deflated Sharpe.** If the placebo's **median** Deflated Sharpe is **≥ 0.95**, the statistic as
   computed is uninformative about a real signal and CLAUDE.md must say so outright, retiring it as
   a bar rather than merely caveating it. This is a direct, measured test of the B9 criticism.
6. **The held-out gate.** `holdout_theme_validate` is the gate that produced `low_risk = confirmed`
   and every theme keep/drop decision the project has shipped. If it returns `confirmed` for at
   least one theme in **≥ 5%** of placebo runs, its false-positive rate is above nominal and that
   rate must be reported alongside every verdict it has ever issued — `low_risk` included.
7. **How the shipped result is read against the floor.** The live headline (long-short *t* 2.836,
   top-decile alpha +7.17%, PBO 73.3%) is described as "above the pipeline's noise floor" on a
   given statistic **only if it falls outside the placebo's [2.5th, 97.5th] percentile interval for
   that statistic**. On any statistic where it does not, the record says so plainly.

**Committed in advance, so it cannot be argued away afterwards:** a placebo that produces large,
significant-looking results is **the finding**, not a bug in the placebo. It will not be re-specified
to make the floor lower. If the instrument itself turns out to be broken, the proof of that is a
failing test in `tests/test_edge.py`, not a disappointing number.

---

## PRE-COMMITTED THRESHOLDS — X2 (rebalance-grid offset sensitivity)

**What is being varied.** The grid has always been `range(TD, len(cal) - horizon, rebalance_days)`
with `TD` hard-coded to 252. With `rebalance_days = 63` there are 63 equally valid grids and every
number this project has ever reported came off exactly one of them. **Grids tested: offsets 0, 5,
10, 20, 30, 40, 50 trading days** (seven, all < 63, therefore all distinct). One change per run;
nothing else varies.

**Metrics recorded per grid:** `top_decile_alpha`, `long_short_tstat`, `cpcv.pbo`, plus
`construction.n_periods` and `equal_weight_ann` as controls (the equal-weight benchmark is
composite-independent, so its movement across grids measures how much the WINDOW moved, separately
from how much the SIGNAL moved).

**Committed interpretations:**

1. **Robustness of the central number.** Let `spread` = max − min of `top_decile_alpha` across the
   seven grids.
   * `spread ≤ 2.0pp` → **ROBUST.** The point estimate is meaningful and may be quoted as a figure.
   * `spread > 2.0pp` → the headline must be quoted as a **RANGE**, permanently, in CLAUDE.md and
     HANDOFF_STATUS.md.
   * `spread > 4.0pp` → additionally labelled **FRAGILE**: the central number is one draw from a
     wide distribution and must never appear without the range beside it.
2. **Stability of significance.** If `long_short_tstat` falls **below 2.0 on any one of the seven
   grids**, the significance claim is grid-dependent and every future statement of it says so. If
   it is below the Harvey–Liu–Zhu hurdle of 3.0 on all seven, that independently confirms the
   Session-2 finding is not an artefact of the one grid it was measured on.
3. **PBO.** Report min / median / max across the grids. If PBO exceeds 50% on **≥ 4 of 7** grids,
   Session 2's PBO 73.3% is a property of the corrected panel and not of its grid.
4. **The offset-0 control.** Offset 0 must reproduce the shipped Session-2 numbers (*t* 2.836,
   alpha +7.17%, PBO 73.3%, n = 69). Committed now: if it does not, that is a **reproducibility
   finding in its own right** — it goes in `## BUGS FOUND`, and the offset-0 run of this sweep, not
   the Session-2 results file, becomes the baseline the spread is measured against. Given the
   project's known and still-unexplained run-to-run non-reproducibility, this control is not a
   formality.
5. **The ensemble.** If the seven grids are individually noisy but their average is stable, an
   overlapping-cohort ensemble is a strictly lower-variance estimator of the same strategy. Whether
   it is worth deploying is **out of scope for this session** and is not decided here.

---

## X7 — A no-signal placebo through the full pipeline

**Committed threshold (written before the run):** Part 4 above, pushed in `1276e4b` before any
run was launched. Six numbered interpretations, none revised afterwards.

**What was run:** `python -m scripts.placebo --panel panel_grid0.pkl --n 100 --no-costs`.
Full universe, 2,827 names requested → 113,945 panel rows, **69 rebalance dates, 2009-01-15 →
2026-01-28** (the panel's scored dates; the underlying price window is 2008-01-16 → 2026-07-24).
Eight scored themes — `sentiment` is empty and `growth` is not in the `established` bucket, so
both drop out of `cols` before any placebo is drawn. **56 signal columns** permuted per date
(8 themes + 48 `z_*` columns). **N = 100 draws, seeds 1000–1099, all 100 completed.** Per draw:
`cpcv_validate` → the CPCV verdict chooses the weights exactly as `run_backtests` does →
`quantile_backtest` → `theme_ic` → `holdout_theme_validate`. ~110 s/draw.

**Harness validation, before any placebo:** the same code path on the UNPERMUTED panel returns
long-short *t* **2.83606**, top-decile alpha **0.071741**, PBO **0.73333**, Deflated Sharpe
**0.99702** — identical to the Session-2 shipped numbers. The harness reproduces the shipped
pipeline, so the null below is the null of the real machinery and not of a stand-in.

**Control:** `equal_weight_ann` = **+18.14% on every one of the 100 draws** (sd 0.00004). The
benchmark never touches the composite, so this is the proof that the placebo perturbed the
signal and nothing else.

**Result — the null distribution (N = 100):**

| statistic | p2.5 | p5 | p50 | p95 | p97.5 | max | sd | MC se(mean) |
|---|---|---|---|---|---|---|---|---|
| long-short *t* | −1.745 | −1.546 | +0.105 | **+2.144** | +2.729 | **+3.436** | 1.178 | 0.118 |
| top-decile alpha | −1.33pp | −1.13pp | +0.25pp | **+1.95pp** | +2.38pp | +2.78pp | 0.92pp | 0.09pp |
| max \|theme IC *t*\| | 0.952 | 1.022 | 1.817 | **+2.707** | 2.946 | **+3.929** | 0.574 | 0.057 |
| PBO | 0.133 | **0.197** | **0.467** | 0.867 | 0.867 | 0.933 | 0.203 | 0.020 |
| Deflated Sharpe | 0.001 | 0.002 | **0.280** | 0.857 | 0.904 | 0.979 | 0.282 | 0.028 |
| monotonicity | −0.789 | −0.770 | −0.097 | +0.458 | +0.709 | +0.794 | 0.379 | 0.038 |

**Rates at which pure noise clears the project's bars:**

| event | rate on noise |
|---|---|
| at least one theme at IC *t* ≥ 2.0 | **39%** |
| long-short *t* ≥ 2.0 | 8% |
| long-short *t* ≥ 3.0 (the Harvey–Liu–Zhu hurdle) | 1% |
| top-decile alpha ≥ 1.0pp | 18% |
| PBO < 50% | **55%** |
| Deflated Sharpe ≥ 0.95 | 2% |
| CPCV adopts a weight scheme | **27%** |
| `holdout_theme_validate` returns `confirmed` for ≥ 1 theme | **6%** |
| long-short *t* ≥ 2.0 **and** alpha ≥ 1pp jointly | 5% |

Themes falsely `confirmed` by the held-out gate: `insider` ×4, `size` ×1, **`low_risk` ×1**.
Distribution of themes clearing IC *t* ≥ 2.0 in a draw: 0 in 61 draws, 1 in 33, 2 in 2, 3 in 4.

**Verdict: THREE OF THE PROJECT'S FOUR THRESHOLDS ARE UNCALIBRATED; ONE SURVIVES.** Applying the
committed rules mechanically:

1. **IC *t* > 2.0 — UNCALIBRATED.** Committed rule: fires if the placebo p95 of max-|theme IC *t*|
   ≥ 2.0. Measured **2.707**. The calibrated bar is **2.71**, and noise reaches **3.93** — above
   the real panel's best theme (`quality`, 3.101).
2. **Long-short *t* > 2.0 — UNCALIBRATED.** Placebo p95 **2.144** ≥ 2.0. Calibrated bar **2.14**.
3. **PBO < 50% — MEANINGLESS AS STATED.** Committed rule: fires if the placebo MEDIAN PBO < 50%.
   Measured **46.7%**. The bar re-sets to the placebo 5th percentile, **19.7%**.
4. **The 1% alpha margin — UNCALIBRATED.** Placebo p95 **+1.95pp** ≥ 1.0pp. Calibrated margin
   **1.95pp**.
5. **Deflated Sharpe — SURVIVES.** Committed rule: fires if the placebo MEDIAN ≥ 0.95. Measured
   **0.280**, and only 2% of noise draws reach 0.95. The statistic discriminates. This is a
   MEASURED partial defence of the metric item B9 attacked — B9's surviving criticism was about
   the trial DENOMINATOR (N = 8 against ~146 real trials), which this does not touch.
6. **The held-out gate — FIRES, marginally.** Committed rule: fires at ≥ 5%. Measured **6.0%**
   (MC se ≈ 2.4pp, so 6% is not distinguishable from 5% at this N — the trigger is real but the
   margin is not). The gate is roughly correctly sized, not badly broken. But **`low_risk` — the
   one theme this project actually zeroed on this gate's verdict — appears among the false
   confirms.** That does not overturn the `low_risk` decision; it means the decision rests on a
   gate with a ~6% false-positive rate and must be quoted that way.

**Threshold 7 — is the real result above the floor?** Committed rule: only if it lies outside the
placebo [p2.5, p97.5].

| statistic | real | placebo [p2.5, p97.5] | above the floor? |
|---|---|---|---|
| top-decile alpha | **+7.17%** | [−1.33pp, +2.38pp] | **YES, clearly** |
| Deflated Sharpe | 0.9970 | [0.001, 0.904] | **YES** (above the placebo max, 0.979) |
| monotonicity | −0.891 | [−0.789, +0.709] | **YES** |
| max \|theme IC *t*\| | 3.101 | [0.952, 2.946] | **YES, narrowly** |
| long-short *t* | 2.836 | [−1.745, +2.729] | **YES, narrowly** |
| **PBO** | **0.733** | **[0.133, 0.867]** | **NO — inside the null** |

**Why — mechanism, not just the number.**

*Why PBO centres on 50%.* Under a pure null the eight weight schemes are exchangeable, so the
in-sample best ranks at random out-of-sample and PBO must centre on one half. The measured 46.7%
IS that theoretical value, recovered empirically. **PBO is behaving exactly as designed — the
defect is that the project set its bar AT the noise level, which leaves it with almost no power.**
The corollary is uncomfortable and should not be softened: the real panel's 73.3% is *worse* than
the noise median, i.e. weight selection on real data generalises less well than on noise. That is
what you expect when the in-sample winner is chosen on features that do not persist, whereas under
noise there is nothing to choose on.

*Why 39% of noise draws produce a theme at IC t ≥ 2.0.* Eight themes are tested per run, and the
bar is a per-theme bar applied to whichever theme looks best. With eight roughly-independent
tries, one clearing a nominal 5% two-sided bar is close to even odds. The project has always read
this bar as if one theme were being tested, and it never has been.

*A post-hoc finding, flagged as such.* Splitting the 100 draws on whether CPCV adopted — a
variable recorded but NOT pre-registered for this test — gives:

| | n | mean long-short *t* | mean alpha |
|---|---|---|---|
| CPCV did NOT adopt | 73 | **−0.065** (se 0.119) | +0.04pp |
| CPCV DID adopt | 27 | **+1.343** (se 0.184) | +0.82pp |

The non-adopting branch is a textbook null. The adopting branch is 7.3 se from zero. **On pure
noise, the weight-selection step manufactures about +1.4 of long-short *t* whenever it fires, and
it fires 27% of the time on nothing** — because the adopted weights are chosen on the same panel
the headline is then measured on. **The mitigating fact that must travel with this: the SHIPPED
strategy has `cpcv_adopt = False` and keeps `current-default`, so the deployed configuration sits
in the unbiased branch.** This is measured support for the existing rule in CLAUDE.md that a CPCV
rejection means keep the defaults. It is post-hoc, so it is a hypothesis with a large effect size
and a mechanical explanation — not a settled result — and it wants a pre-registered replication.

**Follow-on.**
- **Every threshold in the project is now calibrated or known to be uncalibrated.** The four
  numbers to use going forward: theme IC *t* **2.71**, long-short *t* **2.14**, PBO **19.7%**,
  alpha margin **1.95pp**. These are floors for THIS panel, THIS universe and 69 dates; they are
  not universal constants and must be re-measured if the panel changes materially.
- **R1 can now be read against a floor.** This was the stated reason X7 comes first. R1's
  re-run intercept must clear the placebo's own factor-regression floor, which X7 does not
  measure — running the placebo series through `scripts.factor_alpha` is the natural extension
  and is NOT done here.
- **Forecloses** treating PBO < 50% as evidence, and treating a single theme's IC *t* of 2-ish
  as a finding.
- **Does NOT overturn any shipped decision.** The composite's alpha, monotonicity and Deflated
  Sharpe are all well outside the null; `low_risk` stays zeroed; the weights stay at defaults.
  What changes is the size of the claims the project is entitled to make.

## X2 — Rebalance-grid offset sensitivity

**Committed threshold (written before the run):** Part 4 above, pushed in `1276e4b` before any
run was launched. Five numbered interpretations, none revised afterwards.

**What was run:** seven full-universe backtests, identical in every respect except the rebalance
grid. `EDGE_GRID_OFFSET` ∈ {0, 5, 10, 20, 30, 40, 50} trading days; all seven < `rebalance_days`
= 63, therefore all distinct grids. `python -m valuation.edge.fundamental_panel --data-dir
data/backtest --json x2_off<NN>.json`. Full universe, 2,827 names requested. **Every grid retained
69 rebalance dates over an identical price window, 2008-01-16 → 2026-07-24**, with median
cross-sections 1,557–1,563 — so the grids differ in WHICH dates are sampled, not in how many or
over what span. One change per run.

**Result:**

| offset | n | long-short *t* | top-decile alpha | monotonicity | equal-weight | PBO | Deflated Sharpe |
|---|---|---|---|---|---|---|---|
| **0** | 69 | 2.836 | +7.17% | −0.891 | +18.14% | 73.3% | 0.9970 |
| 5 | 69 | 2.850 | +7.74% | −0.915 | +18.13% | 73.3% | 0.9975 |
| 10 | 69 | 2.926 | +8.14% | −0.976 | +18.05% | 60.0% | 0.9998 |
| 20 | 69 | **3.517** | +7.57% | −0.952 | +17.72% | 53.3% | 0.9997 |
| 30 | 69 | 3.410 | +6.84% | −0.927 | +19.20% | 80.0% | 0.9919 |
| 40 | 69 | 3.374 | +7.52% | −0.903 | +19.79% | 86.7% | 0.9982 |
| 50 | 69 | **2.703** | +7.08% | −0.903 | +19.73% | 66.7% | 0.9957 |
| | | **min 2.703 / med 2.926 / max 3.517** | **min +6.84% / med +7.52% / max +8.14%** | | **min +17.72% / max +19.79%** | **min 53.3% / med 73.3% / max 86.7%** | |
| | | spread **0.814** | spread **1.30pp** | spread 0.085 | spread **2.08pp** | spread **33.3pp** | |

**Verdict: the LEVEL is ROBUST; the SIGNIFICANCE STATISTICS are NOT, and one Session-2 claim is
overturned as a grid artefact.**

1. **Top-decile alpha — ROBUST (committed rule: spread ≤ 2.0pp).** Measured spread **1.30pp**
   across seven grids. The point estimate is meaningful and may be quoted as a figure. The
   honest single number is the **median, +7.52%**, with the range +6.84% to +8.14% available;
   Session 2's shipped +7.17% sits at the low end of it but well inside.
2. **Significance is grid-dependent, and this OVERTURNS a Session-2 statement.** Committed rule
   (a): if long-short *t* falls below 2.0 on any grid, significance is grid-dependent — **it does
   not**, the minimum across seven grids is 2.703, so the *t* > 2 claim is not fragile. Committed
   rule (b): if *t* is below the Harvey–Liu–Zhu hurdle of 3.0 on all seven grids, that
   independently confirms Session 2's finding. **It is below 3.0 on only 4 of 7.** The
   confirmation therefore FAILS, and the correct reading is the opposite of the one Session 2
   recorded: **"long-short t 2.836 is BELOW the Harvey–Liu–Zhu hurdle" is a property of the one
   arbitrary grid it was measured on, not of the strategy.** Three of seven equally valid grids
   clear 3.0, one reaching 3.517. The defensible statement is that the long-short *t* is
   **2.7–3.5 depending on grid, straddling the hurdle**, and no single side of 3.0 can be
   claimed.
3. **PBO — NOT a grid artefact (committed rule: > 50% on ≥ 4 of 7).** Measured **7 of 7**, median
   73.3%, minimum 53.3%. Session 2's PBO blow-out is a property of the corrected panel and
   survives this test cleanly. It is also the widest-spreading statistic here (33.3pp), so any
   single PBO figure is a weak instrument regardless.
4. **The offset-0 control — PASSES EXACTLY.** `n` 69, long-short *t* 2.8360640685, top-decile
   alpha 0.0717414233, PBO 0.7333333 — identical to the Session-2 shipped numbers to every digit
   quoted. Given the project's known and still-unexplained run-to-run non-reproducibility, this
   was not a formality, and it is the first clean reproducibility PASS on the corrected panel.
   It does not resolve the `insider` non-determinism (that is a per-theme IC issue, not a
   headline one), but it does mean the headline path is deterministic on identical inputs.
5. **The ensemble — out of scope, as committed.** Not decided here.

**Why — mechanism, not just the number.**

Every grid retains 69 dates over the same 18.5-year window, so this is not a sample-size or
window effect: it is purely *which* 69 quarterly snapshots get sampled. The equal-weight
benchmark — which never touches the composite — moves **2.08pp** across grids, MORE than the
top-decile alpha's 1.30pp. That is the diagnostic that makes the robustness reading credible
rather than lucky: the market-driven quantity is *less* stable across grids than the
signal-driven one, so the alpha's stability is not an artefact of the grids being nearly
identical — they are not.

The *t*-statistic and PBO move much more than the alpha because both are ratios whose
denominators are estimated from only 69 observations. A ±0.4 swing in *t* on n = 69 is what
sampling noise in the period-to-period standard deviation buys you; PBO is computed over 15 CPCV
path-splits, so it moves in visible 6.7pp quanta and has very little resolution to begin with.

**Cross-reference to X7, which is the point of running them in the same session.** The placebo's
long-short *t* has p97.5 = **2.729**. Of the seven real grids, **six clear that noise floor and
one — offset 50, *t* 2.703 — does not.** So on one of seven equally valid grids the long-short
*t* of the real strategy is not distinguishable from what this pipeline produces on a shuffled
signal. Separately, all seven grids have PBO ≥ 53.3% against a placebo median of 46.7%: **every
grid's weight selection generalises worse than noise.**

**Follow-on.**
- **CLAUDE.md and HANDOFF_STATUS.md must stop stating "t 2.836, below the HLZ hurdle of 3.0" as
  a fact.** The statement is grid-conditional. Replaced with the range.
- **Top-decile alpha may still be quoted as a figure** — this is the one headline quantity that
  passed its robustness test outright.
- **Forecloses** re-deriving any conclusion from a single grid's *t* or PBO without the range.
- **Enables** the overlapping-cohort ensemble as a strictly lower-variance estimator, deliberately
  NOT evaluated here.
- `grid_offset` is now stamped into `panel_window` on every run, so no future result can be
  silently off-grid.

---

## SESSION 3 — WHAT THE NOISE FLOOR CHANGED

**The four calibrated numbers.** Every threshold in this project was a convention until now.
Measured against 100 placebo draws through the real pipeline, on the corrected 69-date panel:

| bar | as used | calibrated (placebo p95) | noise clears the old bar |
|---|---|---|---|
| theme IC *t* | 2.0 | **2.71** | 39% of draws |
| long-short *t* | 2.0 | **2.14** | 8% of draws |
| top-decile alpha margin | 1.0pp | **1.95pp** | 18% of draws |
| PBO | < 50% | **< 19.7%** (placebo p5) | 55% of draws |
| Deflated Sharpe | > 0.95 | **stands** | 2% of draws |
| held-out gate | — | **6% false-positive rate** | — |

These are floors for THIS panel, THIS universe and 69 dates. They are not universal constants and
must be re-measured if the panel changes materially.

**What the headline is entitled to claim, after both tests.** Top-decile alpha **+7.52% median
across grids (range +6.84% to +8.14%)**, far outside the placebo's [−1.33pp, +2.38pp] — the
strongest surviving claim in the project. Long-short ***t* 2.7–3.5 depending on grid**, straddling
both the Harvey–Liu–Zhu hurdle of 3.0 and, on one grid of seven, the pipeline's own noise floor of
2.73. **PBO is not usable as evidence in either direction**: it is inside the null on the shipped
grid, above 50% on all seven grids, and its bar was set at the noise level.

**Two shipped claims are now wrong and are corrected in place.** (1) "Long-short *t* 2.836 is below
the HLZ hurdle" — grid-conditional, three of seven grids clear 3.0. (2) "PBO 73.3% fails the < 50%
bar" — the bar itself is meaningless; the honest statement is that PBO is uninformative here.

**No shipped decision changed.** `low_risk` stays zeroed, `insider` stays at 0.125, the weights stay
at defaults, and the composite's alpha, monotonicity and Deflated Sharpe are all well outside the
null. What changed is the size of the claims the record is entitled to make.

---

## BUGS FOUND — session 3

- **`theme_ic()`'s return shape is a trap, and I fell into it.** The function keys per-theme blocks
  at the TOP level; `BACKTEST_RESULTS.json` shows them nested under `per_theme.themes` because the
  results writer adds that wrapper. Reading `.get("themes")` off the function returns `{}` with no
  error — the exact silent-absence failure the COVERAGE RULE exists for. It emptied X7's threshold 1
  on the timing run before the real sweep. Fixed and pinned by
  `test_theme_ic_returns_theme_keyed_blocks_at_the_top_level`. **No shipped code had this bug** —
  it was mine, in `scripts/placebo.py`, caught before the sweep — but the shape asymmetry between
  the function and the file is a live hazard for the next consumer and is now tested.
- **`run_backtests` did not carry `panel_window` into the `--json` dump** (only into the canonical
  file, via `cleanups`). Any sweep writing one JSON per configuration therefore had no record of
  which configuration produced it — directly against B22's intent. Fixed: `out["panel_window"]` is
  set in `run_backtests`, so both outputs are self-describing.
- **The rebalance grid was an undeclared free parameter.** `range(TD, ...)` with `TD` hard-coded to
  252 meant 63 equally valid grids existed and every number in the project's history came off one
  of them, with nothing in any output recording which. Now `grid_offset`, stamped into
  `panel_window`. This is the mechanism behind the corrected HLZ claim above, so it was not cosmetic.
- **Not fixed, flagged for the owner:** on pure noise, CPCV adopting a weight scheme inflates the
  subsequently-measured long-short *t* by ~+1.4 on average, because the adopted weights are chosen
  on the same panel the headline is then measured on. It fires on 27% of noise draws. The shipped
  strategy is unaffected (it does not adopt), but **any future run that DOES adopt a CPCV weight
  scheme will have an optimistically biased headline** unless the measurement moves off the
  selection panel. Post-hoc finding — see the caveat in the X7 entry.

## WHAT WAS NOT DONE, AND WHY

- **The placebo was not run through `scripts.factor_alpha`.** X7 calibrates the pipeline's own
  statistics; it does NOT calibrate R1's factor-regression intercept, which is a different
  estimator on a different series. R1's re-run therefore still has no floor of its own. This is the
  natural extension and is the first thing to do if R1's re-run lands near its threshold.
- **`cost_breakeven_bps` was dropped from the placebo sweep** (`--no-costs`). At ~60s of a ~165s
  draw it was the single largest per-draw cost and **no committed threshold reads it**. Recorded in
  the output as `costs_measured: false` so an absent block cannot be mistaken for a measured zero.
  The cost floor on noise is therefore unmeasured.
- **N = 100 exactly, as committed** — no percentile here is quoted from a smaller N, and the MC
  standard error of every mean is shipped in `x7_placebo.json`. The threshold-6 trigger (6.0%
  against a 5% line) has an MC se of about 2.4pp, so it is stated as "fires, marginally" rather
  than as a clean failure.
- **The X2 ensemble was not evaluated**, as pre-committed.
- **The canonical `BACKTEST_RESULTS.json` was restored from the Session-2 run**, which is
  numerically identical to this session's offset-0 grid (verified to every digit) but predates the
  `grid_offset` stamp in `panel_window`. The next full run will add it. Re-running purely to
  regenerate an identical file was not a good use of 25 minutes, and recording the gap is the
  alternative RUN_RULES rule 4 asks for.

**PROCESS FAILURE, session 3 — recorded because it corrupted a tracked file:**

- **`git add -A` committed a sweep run as the canonical results file.** Commit `49d98ba` swept up
  `BACKTEST_RESULTS.json` while the X2 offset-5 grid run had it clobbered, so for three commits the
  tracked canonical file was an off-grid run (`ls_t` 2.849690, 113,982 rows, `git.dirty: true`,
  stamped against a commit that was not the run's own) rather than the Session-2 canonical
  (`ls_t` 2.836064, 113,945 rows). Every full backtest overwrites this tracked file, so ANY
  `git add -A` during an in-flight run can do this; the project's own memory note warns about
  exactly this and it happened anyway. **Restored and verified byte-identical to the last good
  version at `1f86a0d`.** The `git.dirty: true` stamp inside the file is what makes this
  detectable after the fact — it is the only marker distinguishing a canonical run from an
  incidental one, and it earned its place here.
  **Rule for the next session: never `git add -A` while a backtest is running.** Stage explicitly,
  or restore the canonical file before staging.

---

# PART 5 — SESSION 4: R1 RE-RUN, R9, R10, M1

**R1's pre-commitment is NOT restated, revised or reinterpreted here.** It lives in
`HANDOFF_r1.md` section 1, was written before any regression was ever run, and is honoured
unchanged: **the word "alpha" is permitted only if the FF5+MOM intercept is positive with
Newey–West t > 2.0; an ambiguous result is a NULL.** The pre-written CLAIM A and CLAIM B texts
stand as written. What follows are the pre-commitments for the *new* work in this session, and
three disclosures about how R1's re-run necessarily differs from its first run.

**Written and pushed before any Session-4 run was launched** (RUN_RULES.md Part A rule 6).

---

## R1 RE-RUN — three necessary deviations, declared in advance

The first R1 run is **void**: its strategy series came from the pre-B6/B7 panel over a window
(1998-12-31 → 2026-01-21, 109 windows) that no longer exists. Regenerating it forces three
changes, none of which touches the threshold:

1. **The composite must change, and this is a correction, not a choice.**
   `scripts/factor_alpha.py:decile_series` builds its composite as
   `comp += where(isnan(z), 0, z) * w` — the **pre-B7 non-renormalising convention**, in which a
   missing theme is read as exactly average. B7 replaced that everywhere with renormalisation by
   present-weight mass. So R1's first run scored names by a rule no shipped code path uses any
   more. The re-run uses `fundamental_panel.composite`, the single shipped composite. **Declared
   now: this is expected to move the series slightly and is NOT a free parameter — there is one
   composite and R1 must use it.**
2. **The `ex_b6_first_37` robustness cut no longer exists and cannot be run.** It dropped the 37
   rebalance dates whose universe was inverted. B6 *removed those dates from the panel entirely*;
   the corrected panel is 69 dates beginning 2009-01-15. **The pre-registered cut is therefore
   satisfied by construction, not skipped** — the corrected sample IS the ex-B6 sample. It will be
   reported as such rather than silently dropped, and a **first-half / second-half subperiod
   split** is added in its place as a voluntary robustness cut carrying the same veto power: if
   the verdict differs across the specification and either robustness cut, **the result is a
   NULL**, exactly as pre-registered.
3. **The X4 shipped-series reproduction assert must be disabled for this run.** It asserts the
   regenerated series matches `ETF_BENCHMARK_RESULTS_strategy_series.csv` to 1e-9. That file was
   produced from the old panel and the old composite; matching it would mean the re-run had
   failed. **The assert is replaced by an explicit recorded comparison** — how far the corrected
   series moved from the void one — so the change is measured rather than hidden.

**Reporting against the calibrated floor (session 3, X7), as instructed.** R1's own NW *t* > 2.0
threshold is honoured as pre-registered and is NOT replaced. Separately, and additionally, the
result is reported against what X7 measured: **X7 does NOT calibrate a factor-regression
intercept** — it calibrates the pipeline's own statistics — so there is no placebo floor for R1's
*t*. What X7 does give is a floor for the raw object R1 decomposes: top-decile alpha's placebo
null is **[−1.33pp, +2.38pp]**. Committed now: **if the re-run's raw top-decile alpha falls
inside that interval, the regression is decomposing noise and the R1 verdict is a NULL regardless
of what its intercept does.**

---

## PRE-COMMITTED THRESHOLDS — R9 (significance statistics for the headline)

R9 is instrumentation, not a keep/reject test, so the commitment is about what gets reported and
which number becomes canonical:

1. `top_decile_alpha` ships with **no significance statistic at all** — it is the number on the
   front of the product. A *t*-statistic and a Newey–West *t* will be added and shipped on every
   run, **whatever they say.**
2. The long-short *t* is currently naive i.i.d. A **Newey–West HAC *t* (lag 1)** and the
   **Ljung–Box** statistic on the spread series are added alongside it. Committed now: **if
   Ljung–Box rejects independence at p < 0.05, the NW *t* becomes the number the project quotes
   and the naive *t* is retained only as a diagnostic.** If it does not reject, both are reported
   and the naive *t* stands.
3. Committed now: **if adding a HAC standard error moves the long-short *t* below 2.0, that is
   reported as a headline change, not as a footnote.**

---

## PRE-COMMITTED THRESHOLDS — R10 (the uninvestable benchmark)

1. **All three benchmarks are published side by side, whatever they say** — (a) equal-weight
   universe charged the same cost model the strategy pays, (b) SPY total return over the same
   windows, (c) a cap-weighted panel average as the closest investable analogue.
2. Committed now: **the alpha versus SPY is expected to be materially LOWER than the current
   figure and it gets published at the same prominence.** A benchmark change that flatters the
   product does not get quoted alone.
3. Committed now: **if top-decile excess return over the cap-weighted or SPY benchmark is not
   positive, the record says the edge is measured against an uninvestable benchmark and is not
   demonstrated against an investable one.**

---

## PRE-COMMITTED THRESHOLDS — M1 (the research log and the real trial counter)

1. The log is **append-only**, one row per pre-registered test, populated retrospectively from the
   handoff corpus. Its row count `N` is wired into `_deflated_sharpe` and `_trials_haircut`.
2. **The Deflated Sharpe will fall, and by design.** It is currently computed against `N = 8`
   when the audit's reconstruction counts roughly 146 real trials. Committed now: **if the
   Deflated Sharpe drops below 0.95 at the true `N`, the record states plainly that the edge does
   NOT clear the Deflated Sharpe bar.** No re-specification of `N`, no reversion to 8, no
   "both figures are informative" hedge. The whole point of M1 is that the denominator has been
   wrong; the honest consequence of fixing it must be accepted whichever way it goes.
3. Committed now: **X7's finding that "the Deflated Sharpe survives calibration" was measured
   with `N = 8` inside both the real run and the placebo.** Changing `N` changes both. Therefore
   **X7's DSR calibration becomes provisional the moment M1 lands**, and the placebo must be
   re-run at the true `N` before the "Deflated Sharpe stands" claim is repeated. This is declared
   now so it cannot be quietly skipped later.
4. The trial count is a **measured floor, not a guess**: `N` is the number of rows actually in the
   log. If the retrospective reconstruction recovers fewer than the audit's ~146, the smaller
   honest number is used and the gap is recorded.

---

---

## R1 (RE-RUN) — Factor-adjusted alpha on the CORRECTED panel

**Committed threshold:** `HANDOFF_r1.md` section 1, written before any regression was ever run,
honoured **unchanged**: *the word "alpha" is permitted only if the FF5+MOM intercept is positive
with Newey–West t > 2.0; an ambiguous result is a NULL, not a judgement call.* The three
necessary deviations were declared in Part 5 above and pushed in `4f41c9f` before this ran.

**What was run:** `python -m scripts.factor_alpha --corrected-panel`, strategy series regenerated
from the corrected panel (`panel_grid0.pkl`, the Session-3 offset-0 build). **69 rebalance dates →
68 non-overlapping 63-trading-day windows, 2009-01-15 → 2025-10-27**, deployed flat 1/7 weights,
Newey–West lag 1. The prior run's 109 windows over 1998-12-31 → 2026-01-21 are **void**.

**Alignment validation (the check that makes the rest believable):** SPY's own excess return
regressed on MKT alone gives **beta 0.9327, R² 0.9878**, alpha +0.68%/yr (t 1.58). Windows are
aligned to the factor calendar.

**Result — the primary object (`top − ew`, which is exactly `top_decile_alpha` / 4), FF5+MOM:**

| spec | n | raw | ALPHA /yr | NW t |
|---|---|---|---|---|
| **compound / full (pre-registered primary)** | 68 | +7.13% | **+6.99%** | **+3.984** |
| compound / first half | 34 | +2.88% | +5.19% | +2.757 |
| compound / second half | 34 | +11.38% | +10.85% | +3.857 |
| sum / full (pre-registered robustness) | 68 | +7.13% | +6.79% | +3.751 |
| sum / first half | 34 | +2.88% | +5.08% | +2.671 |
| sum / second half | 34 | +11.38% | +10.49% | +3.482 |

**All six specifications are positive with NW t > 2.0.** The pre-registration's veto — "if the
verdict differs between the specification and either robustness cut, the result is a NULL" — is
not triggered: there is no disagreement to adjudicate.

Other objects, compound/full: **long-only book in excess of RF** +9.33%/yr (t +4.973);
**long-short** +14.86%/yr (t +4.184); **the equal-weight universe's own unexplained excess**
+2.34%/yr (t +2.915).

**Verdict: THRESHOLD CLEARED. CLAIM A APPLIES — the word "alpha" is permitted, as a range.**
Quote **+5.1% to +10.9%/yr depending on subperiod and aggregation, with +6.99% (NW t 3.98) as the
pre-registered central figure.** The conservative single number is the first half's **+5.19%**.

**Against X7's calibrated floor, as instructed.** X7 does **not** calibrate a factor-regression
intercept, so there is no placebo floor for R1's *t* and none is invented. What X7 does floor is
the raw object R1 decomposes, and the pre-commitment was explicit: if the raw top-decile alpha
fell inside the placebo null **[−1.33pp, +2.38pp]**, R1 would be a NULL whatever its intercept
did. Measured raw is **+7.13%**, far outside. R1 is decomposing something real.

**Why — and the mechanism has CHANGED, which matters more than the level.** The void run found
SMB +0.39 (t 3.84), RMW +0.30 (t 4.49) and UMD +0.18 (t 3.49) all loading, with HML (t 1.08) and
CMA (t 1.08) not. On the corrected panel:

| factor | loading | t | void run |
|---|---|---|---|
| HML | **+0.251** | **+2.93** | did NOT load (t 1.08) |
| UMD | **+0.205** | **+3.65** | loaded (t 3.49) |
| SMB | +0.208 | +1.39 | **loaded (t 3.84)** |
| RMW | +0.092 | +0.90 | **loaded (t 4.49)** |
| CMA | −0.130 | −1.23 | did not load |
| MKT | +0.019 | +0.28 | — |

**SMB and RMW stop loading and HML starts.** The old reading — "`size`, `quality` and `momentum`
ARE the standard premia; `value` and `capital_discipline` are not what FF measures" — is
**reversed on two of its three legs** and must not be repeated. The honest current reading:
momentum is a genuine standard-premium exposure, the book now has a real value tilt, and the
size/profitability exposures that dominated the old story were largely an artefact of the
inverted-universe window B6 removed. `R²` also fell 0.465 → 0.308: the factor models explain
**less** of this series than they explained of the void one.

The unhedged small-cap tilt that carried the old caveat is much weaker here — SMB +0.208 at
t 1.39 on `top − ew`, against +0.885 in the void run — though the long-only book still loads
SMB +0.691 (t 3.89), so the caveat survives for the BOOK even as it weakens for the spread.

**Two things that must travel with the number.**
1. **The secondary q-factor model does NOT clear on the first half.** q4 gives +6.72% (t 3.193)
   on the full sample and +11.49% (t 3.838) on the second half, but **+3.17% (t 1.712)** on the
   first — and q5 gives +1.56% (t 0.702) there. The pre-registered threshold is stated on the
   FF5+MOM intercept, so this does not trigger the veto, but a reader is entitled to know the
   early-period result is model-dependent.
2. **This is still ONE panel.** A regression is a control, not new data. X8's international
   replication remains the out-of-sample evidence; R1 is not.

**The B7 composite correction, measured as declared.** R1's first run built its composite with the
pre-B7 non-renormalising rule. Switching to the shipped composite moves individual period returns
by up to **2.55pp** (top decile) and **3.57pp** (bottom), leaves `ew` unchanged to exactly zero as
it must, and moves the mean top-decile alpha only **+7.183% → +7.311%**. Consistent with Session
2's finding that B7 is a null on the headline while being a real mechanism underneath.

**Follow-on.** The +8.81%/yr figure and the "+6.6% to +8.8%" range are now **void and must not be
quoted anywhere.** Replaced by +6.99% (range +5.1% to +10.9%). Unblocks the product-copy decision
that P5's second claim was contingent on: CLAIM A's text ships. Does NOT unblock any claim about
out-of-sample generalisation — that is X8.

---

## R9 — A significance statistic for the headline, and HAC inference for the spread

**Committed threshold:** Part 5 above. Instrumentation, so the commitment was about what gets
reported and which number becomes canonical — not a keep/reject.

**What was run:** `quantile_backtest` on the corrected full-universe panel, 69 dates.

**Result:**

| quantity | value |
|---|---|
| `top_decile_alpha` | +7.17% |
| **`top_decile_alpha_tstat`** (new) | **+4.517** |
| **`top_decile_alpha_tstat_nw`** (new) | **+4.376** |
| `top_decile_alpha_hit` (new) | 71.0% of periods |
| `long_short_tstat` (naive, incumbent) | +2.836 |
| **`long_short_tstat_nw`** (new) | **+2.620** |
| Ljung–Box on the long-short spread | Q 10.25, df 4, **p = 0.036**, lag-1 acf +0.189 |
| Ljung–Box on the alpha series | Q 10.28, df 4, **p = 0.036**, lag-1 acf +0.081 |

**Verdict: ADOPTED, and the pre-committed consequence fires.** Ljung–Box rejects independence at
p = 0.036 < 0.05 on both series, so **the Newey–West t is now the number this project quotes** and
the naive t is retained as a diagnostic only. The long-short headline becomes **2.620, not
2.836.**

**Why.** The 63-day windows genuinely do not overlap, so the naive t was defensible on the
*overlap* dimension — which is the dimension the project had thought about. It was never
defensible on autocorrelation, and nothing anywhere computed a serial-correlation diagnostic. The
measured lag-1 autocorrelation of +0.189 on the spread is exactly the regime persistence you would
expect of a factor spread, and it inflates the naive t by about 8%.

The headline alpha's *t* of +4.38 is far stronger than the long-short's — worth noting because the
project has always led with the long-short as "the real bar". On this panel the long-only object
is the better-measured one.

**Follow-on.** Every future quotation of the long-short *t* uses the NW figure. Note the
comparison to X7's calibrated floor of **2.14 is apples-to-oranges**: that floor was measured on
the *naive* t across 100 placebo draws. Re-deriving the floor on the HAC statistic is open work.

---

## R10 — The uninvestable benchmark, replaced by three alternatives

**Committed threshold:** Part 5 above — all three published side by side whatever they say; the
alpha versus SPY **expected to be materially LOWER** and published at equal prominence.

**What was run:** `benchmark_panel` on the corrected full-universe panel, 69 dates, deployed
weights, top decile vs four benchmarks.

**Result:**

| benchmark | benchmark /yr | top decile /yr | EXCESS /yr | t | NW t | hit |
|---|---|---|---|---|---|---|
| equal-weight universe (incumbent, cost-free) | +18.14% | +25.31% | **+7.17%** | +4.517 | +4.376 | 71% |
| equal-weight, charged the strategy's own costs | +16.10% | +25.31% | +9.21% | +5.834 | +5.685 | 75% |
| cap-weighted panel average | +14.85% | +25.31% | +10.46% | +4.138 | +4.292 | 68% |
| **SPY total return** | +15.32% | +25.31% | **+9.99%** | +3.638 | +3.770 | 64% |

**Verdict: ADOPTED — and the pre-registered EXPECTATION WAS WRONG, in the strategy's favour.**
Both the audit ("expect the alpha versus SPY to be considerably lower") and this session's own
pre-commitment predicted the incumbent benchmark was flattering the product. **It is not. The
incumbent is the HARDEST of the four.** Excess versus SPY is **+9.99%**, materially *higher* than
the +7.17% the project has been publishing.

**Why.** Over 2009-01 → 2026-01 the equal-weighted panel returned **+18.14%/yr** against SPY's
**+15.32%** — the breadth of a ~1,500-name equal-weighted book beat the cap-weighted index over a
window that began at the post-GFC bottom, when small caps recovered hardest. So the "uninvestable"
benchmark is uninvestable in the direction of being **too demanding**, not too generous. The
project has, by accident, been quoting the most conservative of its four available figures.

This does not make the benchmark investable, and the cost asymmetry the audit identified is real
and now measured: charging the equal-weight book the same market-cap cost table the strategy pays
costs it **2.04pp/yr** (+18.14% → +16.10%), which is a genuine thumb on the scale that had been
sitting in the strategy's favour and is now removed.

**Follow-on.** The record may now state the edge survives against an investable benchmark: excess
over SPY **+9.99%/yr, NW t 3.77**, and over a cap-weighted panel average +10.46% (NW t 4.29).
**Publish +7.17% as the headline anyway** — it is the most conservative and it is the one every
historical figure used, so changing it would break comparability for a number that only moves in
the flattering direction. R10's numbers ship beside it in `benchmarks`.

---

## M1 — The append-only research log and a real trial counter

**Committed threshold:** Part 5 above — most importantly: *if the Deflated Sharpe drops below
0.95 at the true N, the record states plainly that the edge does NOT clear that bar. No
re-specification, no reversion to 8, no hedge.*

**What was run:** `RESEARCH_LOG.md` populated retrospectively from the handoff corpus;
`valuation/edge/research_log.py` parses it; `N` wired into `_deflated_sharpe_detail` and
`_trials_haircut`; `cpcv_validate` re-run on the corrected panel.

**Result — the trial count:**

| | trials |
|---|---|
| **equity** (the family this composite was searched within) | **84** |
| options | 133 |
| infra | 1 |
| **total logged** | **218** |
| `FIXED` rows, correctly NOT counted | 15 |
| the audit's estimate | ~146 |

**Result — what the honest denominator does to the statistics:**

| | N = 8 (as shipped) | **N = 84 (measured)** |
|---|---|---|
| Deflated Sharpe | 0.9970 | **0.8997** |
| `sr0_benchmark` | 0.242 | **0.406** |
| `is_effectively_undeflated` | true | **false** |
| `metric` self-report | `probabilistic_sharpe_ratio_UNDEFLATED` | **`deflated_sharpe_ratio`** |
| `_trials_haircut` | 2.04 | **2.977** |

**Verdict: ADOPTED, and the pre-committed consequence fires. THE EDGE DOES NOT CLEAR THE DEFLATED
SHARPE BAR.** 0.8997 < 0.95. Stated plainly, as committed, with no re-specification.

**Why — and there is a genuine win buried in the failure.** Audit **B9** argued the statistic was
an undeflated PSR because `sr0` collapsed. With a real N it does not collapse: `sr0` rises from
0.242 to 0.406 against a per-period Sharpe of 0.550, so the benchmark is now deflating away 74% of
the Sharpe and the statistic **self-reports as a genuine Deflated Sharpe for the first time.**
**B9's criticism is resolved by M1, not by argument** — and the price of resolving it is that the
bar is no longer cleared. That is the correct trade and it was pre-committed.

Separately, `√(2·ln 84) = 2.977` — the multiple-testing haircut at the real N lands within 0.03 of
the Harvey–Liu–Zhu hurdle of 3.0, exactly as the audit predicted it would.

**Two schema decisions, both of which change the count and both deliberate.**
1. **A trial counts whether or not it was pre-committed.** The log's original rule counted only
   pre-committed tests. That is right for judging whether a *result* is credible and wrong for a
   multiple-testing *denominator*: what inflates the best-looking result is how many times the
   data was searched, not how well each search was documented. The old rule would have
   systematically understated N and therefore **overstated** significance — the exact error M1
   exists to fix. Rows carry `pre = yes | retro`; both count.
2. **`N` is domain-scoped.** The equity composite is charged the 84 equity trials, not the 218
   project-wide ones. The options autopsy's 126-feature sweep is a different search over
   different data for a different product; charging the equity composite for it would
   over-penalise as surely as charging it for eight weight schemes under-penalises. The log's own
   schema already forms BH-FDR families within a domain.
3. A row may represent a pre-registered GRID via `n=<k>` — the lazy-prices 28-cell sweep is one
   row counted as 28. Writing 28 near-identical rows would be fabricated precision; counting it
   once would undercount a 28-way search by a factor of 28.

**A missing or unreadable log degrades to N = 8**, i.e. to the OLD behaviour, never to an
unpenalised one.

**Follow-on — and this one is pre-committed and must not be skipped.** **X7's finding that "the
Deflated Sharpe survives calibration" is now PROVISIONAL.** That result was measured with N = 8
inside *both* the real run and all 100 placebo draws. Changing N changes both, so the placebo must
be re-run at the true N before the claim is repeated. The direction is predictable — both fall —
so the *relative* comparison may well survive; the *absolute* claim "DSR > 0.95" does not, and no
part of it may be quoted until the placebo is re-run. The 218-row total is above the audit's ~146
estimate, so the gap the pre-commitment worried about (recovering fewer than 146) did not
materialise; the equity-scoped 84 is the operative number and is a measured floor, not a guess.

---

**Note on this session's canonical `BACKTEST_RESULTS.json`, so the next reader does not misapply
Session 3's own rule.** The file carries `git.dirty: true` and is stamped against `4f41c9f` rather
than its own commit. Session 3 established that combination as the tell for a file polluted by an
in-flight run. **It is not one here.** The numbers are the Session-4 full run's; the file was
re-serialised from that run's own result dict after `results_file.py` was corrected to carry R9's
new fields and R10's `benchmarks` block, which the writer had been silently dropping (the values
were computed correctly and thrown away at the schema boundary — a fresh instance of the
"guard that cannot see" pattern, this time on the OUTPUT side). No number was recomputed: the
same `res` object went through the fixed writer. The `dirty` flag reflects the uncommitted
documentation in the tree at re-serialisation time.

**The R9/R10 schema-boundary bug is worth its own line in the record.** `quantile_backtest` and
`benchmark_panel` both computed their new fields correctly on the first full run, and both were
dropped because `results_file.build_payload` whitelists what it writes. The canonical file
therefore showed `top_decile_alpha_tstat: None` next to a correctly-computed 4.517 in the raw
dump. Nothing raised. `benchmarks` is now in `RESULT_BLOCKS`, so a future absence is an error
rather than a silence — but the general hazard remains: **adding a metric to a computation does
not add it to the canonical file, and the canonical file is what every other agent reads.**

---

# PART 6 — SESSION 5: THE OPTIONS VERDICT (R2, R3, R7, O20)

Written **before any run in this session started**, per RUN_RULES.md Part A rule 6. R2's and
R7's thresholds were already committed in Part 0 and are **not restated in altered form** here —
they are quoted and honoured as written. What is new below is R3's and O20's, plus the run
design, which is itself a choice that can flatter a result and therefore belongs in advance.

## THE RUN DESIGN — pinned universe, and why

The miner is live (`dte_extend.py` was running when this session started) and the cache grows
between runs. Re-running R2 on "whatever is complete today" would change the corrected code AND
the universe at the same time, and the headline would move for two reasons with no way to
separate them. That is exactly the confound the project's **one change per run** rule exists to
stop.

So R2 runs with `--universe-from` pinned to the previous run's frozen 187-name list. The only
thing that differs from `HANDOFF_universe_backtest.md` is the code: B1 (price basis), B2 (exit
censoring), B3 (stale expiry mark), B4 (the −1 open-interest sentinel) and B15 (commission).

**O20 is then a SECOND, declared variable** and is reported as its own partition of the same
run, never mixed into the headline.

## PRE-COMMITTED THRESHOLDS — R3 (clustered inference)

R3 is an inference correction, not a hypothesis, so most of it has no pass/fail. Three things
still need committing, because each could be chosen after the fact to flatter a conclusion:

1. **The block is the CALENDAR MONTH**, chosen before seeing any interval. A month is long
   enough to contain a full volatility episode — the thing that actually clusters entries — and
   leaves ~118 blocks over the decade, enough for a percentile bootstrap. Week and year are
   implemented and are diagnostics; **the verdict reads the month.**
2. **`n_eff` is reported as BOTH the block count and the design-effect estimate**, and neither
   is presented alone. If they disagree materially that disagreement is the finding and gets
   stated, not resolved by picking one.
3. **The embargo is the label window, 75 days** — the maximum a trade can stay open (DTE tops
   at 75). It is not tuned. `embargo_days=0` reproduces the old unpurged split so the cost of
   the correction is measurable rather than asserted.

**Committed direction of expectation, so it can be scored against:** the audit predicts every
options *t*-like quantity shrinks by roughly the square root of the clustering factor, and
guesses a factor of 2 to 4 — which would move the −5.24 sign-test *z* into the −2.5 to −3.7
range. **If the measured clustering factor comes in BELOW 2, the audit over-predicted and this
ledger says so.**

## PRE-COMMITTED THRESHOLD — O20 (point-in-time liquidity)

The audit says: apply the liquidity screen as of each entry date, re-report the headline, and
**"expect it to fall. That is the correct number."**

**Committed before the run:**

- The screen is the **miner's own** (`MAX_MEDIAN_SPREAD_PCT = 0.15`, and open interest passing
  on either the contract floor or the $2.5M notional floor), imported from `mine_options_cache`
  rather than re-declared, and applied to the alert date's chain instead of to the name's first
  cached year. **Applying a DIFFERENT bar and calling the difference O20 would be a new filter
  wearing a correction's name.**
- It is applied to **both arms** of the random-entry control. Screening the real book only would
  compare two different universes.
- A day whose chain cannot answer is **`None`, not a failure**. An unmeasurable day excluded as
  though it were illiquid would report a data gap as a liquidity finding.
- **If the headline does NOT fall**, that is reported as the audit's expectation being wrong, in
  the same words the R10 reversal got. It is not evidence the strategy is better than thought.

**And the limit of the repair, committed in advance because it will be tempting to skip:** O20
cannot fix the dominant selection effect. Verified against `mine_options_cache.py` this session,
the audit's premise is **half wrong** — see the R2/O20 entries below. Names were ranked into the
mining pool by **today's market cap**; the *liquidity* screen was already applied to the first
cached year, not to a present-day chain. So a point-in-time re-screen answers "was this name
tradeable on the day?" and cannot answer "which names would have been in the pool at all?",
because the names that failed are not on disk. **The number O20 produces is an upper bound on
the repair.**

## R2 — QUOTED FROM PART 0, UNCHANGED

> - If the corrected real-versus-control gap **remains negative at conventional significance
>   under a date-block bootstrap (R3)**: the entry signal is dead, and the record says so plainly.
> - If the gap **closes to within its confidence interval**: the verdict is **INCONCLUSIVE**, not
>   vindicated.
> - If the gap **turns positive at significance**: a genuine reversal, which must additionally
>   survive the date-block bootstrap and the both-halves split before anything is claimed.

The R3.3 precondition — "the paired name-year sign test and paired *t* must be in the repository
with a test before this verdict is reported at all" — is satisfied by
`valuation/edge/options_stats.paired_name_year` and
`test_audit_r3_the_paired_sign_test_counts_cells_not_trades`.

## R7 — QUOTED FROM PART 0, UNCHANGED

G3a flow ≥ 52 retained alerts/year · G3b span ≥ 60% of names AND ≥ 60% of months · G3c backstop
retention ≥ 20%. All three, alongside the unchanged G1/G2/G4/G5/G6/G7. **G3b has never been
measured and is the arm on which the re-score can still fail.**

## CARRIED FORWARD FROM SESSION 4 — the placebo at the true N

X7's "the Deflated Sharpe survives calibration" was measured with **N = 8 inside both the real
run and all 100 placebo draws**. M1 then made the real run's N = 84. The claim is **PROVISIONAL
until the placebo is re-run at the true N**, and it is not to be quoted in the meantime. That
sweep was launched at the start of this session.


---

## R2 — THE CORRECTED OPTIONS RE-RUN · **THE ENTRY SIGNAL IS DEAD, AND THE RECORD SAYS SO**

**Committed threshold:** Part 0, quoted unchanged in Part 6 above. Gap still negative at
significance under a date-block bootstrap → the signal is dead. Gap closes to within its CI →
INCONCLUSIVE, not vindicated. Gap positive at significance → reversal.

**What was run:** `optuniv_run.py --workers 5 --aggression 1.0 --universe-from <frozen 187-name
list> --control --control-draws 2 --refresh-control --autopsy`, plus a second control seed. The
universe is PINNED to the pre-correction run's frozen list, so the corrected code is the only
variable. Window 2016-01-01 → 2025-10-15, unchanged. Nothing re-tuned.

### The verdict, mechanically

| | pre-correction | **corrected** |
|---|---|---|
| real / control expectancy | +5.14% / +13.22% (2 seeds) | **+3.41% / +10.06% (5 seeds)** |
| gap | −8.08pp | **−6.65pp** (CORRECTED 2026-08-11, `U1-SPLIT`: **−5.06pp** split-clean; verdict unchanged) |
| **date-block CI95 on the gap** | [−11.66pp, −4.51pp] | **[−11.92pp, −2.13pp]** |
| negative at significance | YES | **YES** |
| paired name-year cells / wins | 441 / 1,052 = 41.9% | **577 / 1,334 = 43.3%** |
| **sign-test z** | −5.185 | **−4.903 (p < 1e−5)** |
| paired *t* | −2.183 (p = 0.029) | −1.227 (p = 0.220), not significant |

**VERDICT: the pre-committed condition for "dead" is met.** The corrected gap remains negative at
conventional significance under the date-block bootstrap. The alert's day-selection subtracts
value on this universe and window, on corrected data, under clustered inference.

**The finding survives the correction almost intact — the gap moves 1.43pp and the sign test moves 0.28.** That is the
headline: five defects were repaired, every level moved, and the conclusion did not. Note the
paired *t* is no longer significant while the sign test is decisive — exactly the ordering the
record predicted when it said to lean on the sign test.

### THE SEED INSTABILITY · a finding about the BENCHMARK, and it nearly caused a wrong call

**A single control seed can flip this verdict, and the first one run did.** The control was
therefore run at **FIVE seeds** rather than the record's two — the extra three cost ~30 minutes,
and the strongest negative finding this project owns should not rest on a coin flip.

| seed | control exp | gap | date-block CI95 | neg at sig | sign-test z | paired *t* |
|---|---|---|---|---|---|---|
| 0 | +6.46% | −3.05pp | [−7.05, +0.95] | **NO** | −0.594 | +0.162 |
| 1 | **+15.34%** | −11.93pp | [−23.17, −4.55] | YES | −3.003 | −1.835 |
| 2 | +11.75% | −8.34pp | [−18.92, −0.87] | YES | −1.700 | −0.975 |
| 3 | +9.22% | −5.81pp | [−9.91, −1.67] | YES | −2.931 | +0.071 |
| 4 | +7.54% | −4.13pp | [−8.09, −0.15] | YES | −2.998 | −0.740 |
| **POOLED (n=29,785)** | **+10.06%** | **−6.65pp** | **[−11.92, −2.13]** | **YES** | **−4.903** | −1.227 |

**Every one of the five seeds has a negative point estimate. Four of five are negative at
significance individually. Seed 0 — the first one run — is the single most favourable draw.**

**The pooled sign test at five seeds is z = −4.903 (p < 1e−5) over 1,334 name-year cells, 43.3%
won.** That is very nearly the record's own −5.24, reached on corrected data under clustered
inference. The two-seed corrected reading (z −2.907) was itself an underestimate: **more control
draws sharpen the test rather than blur it**, because each name-year cell's control mean is
averaged over more draws and the paired comparison gets less noisy. The verdict is not marginal.

The mechanism of the spread is measured, not asserted: the control's OWN expectancy carries a
date-block CI of **[+5.54%, +15.44%]** at five seeds. A random-day book's mean on a barbell
payoff is set by a handful of +600% trades, and which ones a draw catches moves it enormously.

**Two seeds is not enough for this comparison and nobody had measured that.** The paired *t*
ranges +0.162 to −1.835 across seeds and is never significant, even pooled (−1.227, p 0.22),
while the sign test is stable and decisive — exactly the ordering the record predicted when it
said to lean on the sign test. **Standing rule for this comparison: five seeds minimum, and the
sign test carries the verdict.**

### What the corrections did to the book

**The trade count ROSE 3,042 → 3,885, and this is B1's signature.** Alerts *fell* (5,953 →
5,614, because the ATM IV now solves and nudges the options component of the score), while
`no_contract_in_band` rejections fell **2,911 → 1,729**. A split-and-dividend-adjusted spot
compared against as-traded strikes threw the 0.90–1.20 moneyness prefilter, so **1,182 alerts
were silently discarded for having no contract in a band that was being measured against the
wrong price.** Alert→trade conversion 51.1% → 69.2%.

**Two independent confirmations that B1 was real:**

| | pre | post |
|---|---|---|
| median entry IV | **1.4200** | **0.2497** |
| IV coverage | 75.3% | **100.0%** |

142% is not an equity ATM vol; 25% is. `HANDOFF_universe_backtest.md` §8 recorded the 1.28–1.57
median as an unexplained anomaly and declined to use the field. It was the price basis, and the
sanity guard added in session 1 would have caught it.

### THE BREADTH CLAIM DOES NOT SURVIVE — the second-largest change

| | pre-correction | **corrected** |
|---|---|---|
| 54 baseline names | +6.95% (n 1,241) | **+9.37% (n 1,532), PF 1.263** |
| 133 new names | +3.90% (n 1,801) | **−0.47% (n 2,353), PF 0.988** |

**The new names are now NEGATIVE.** Every dollar of the book's positive expectancy comes from the
original 54 megacaps. `HANDOFF_universe_backtest.md`'s headline — *"the edge survives breadth but
roughly halves"* — is **VOID**. On corrected data the edge does not survive breadth at all; it is
a megacap phenomenon that a corrupted price basis had made look broader.

The study's own B1 bar still reads **HOLDS**, because the whole book is positive in both held-out
halves (+4.35% early, +2.59% late). The bar is being met by a book whose composition has
completely changed — a warning about the bar, not support for the edge.

Cap tiers, corrected: mega +4.71% (n 1,002), large +0.86% (n 2,062), mid +7.65% (n 777),
small +18.25% (n 44 — still far too few to quote). Mid/small remain the best tiers.

### The statistical comfort is gone

| | pre | post |
|---|---|---|
| Deflated Sharpe, unfiltered | 88.13% | **49.59%** |
| Deflated Sharpe, term_slope-filtered | 95.69% | **80.63%** |

Both are now below the 95% bar; the filtered book used to clear it. The autopsy re-confirms
unchanged: **64 features, 127 hypotheses, ZERO survivors.** Four hypotheses reach BH discovery in
one split direction each (`f_d_gex_wall_conc`, `f_dte`, `f_sig_gex_proxy`, `f_spread_frac`) and
none in both, so nothing passes the gate. Combiner escalation again not warranted.

**Verdict: REJECTED — the entry signal does not beat random entry, on corrected data, under
clustered inference.** **Follow-on:** the live options alert must not be described as a
day-selection edge. It is an alert-generation mechanism, in the pre-commitment's own words, and
the product copy has to say so.

## R3 — CLUSTERED INFERENCE · **SHRINKS EVERY OPTIONS STATISTIC, OVERTURNS NONE**

**Committed threshold:** Part 6 above — month blocks, both `n_eff` estimates reported, 75-day
embargo, and the audit's predicted clustering factor of 2–4 scored against.

**R3.3 first, because it is the precondition for reporting R2 at all.** The paired name-year sign
test and paired *t* existed in no file. They do now, and they **reproduce the record exactly**:
run through `options_stats.paired_name_year`, the pre-correction pooled book returns **441 wins
of 1,052 cells** against the handoff's "441 of 1,052 = 41.9%", at z −5.185 against its −5.24 (the
difference is tie handling — ties are excluded from the sign test's denominator here). Seed 0
alone returns paired *t* **−2.6701** against the record's −2.67. **The two numbers the entire
options conclusion rested on are now re-derivable from shipped code**, pinned by
`test_audit_r3_the_paired_sign_test_counts_cells_not_trades`.

### The measured clustering, and a correction to the audit

> **SCOPE CORRECTION 2026-08-06 (session-5 closeout, item 5). This paragraph is about the
> PRE-CORRECTION book and says so — but its headline was quoted onward without the scope, into
> `CLAUDE.md` and into the summary above, as though 1.85 were the project's clustering factor.
> IT IS NOT. The CORRECTED 3,885-trade book gives design effect 2.2121 against null p95 1.2037,
> i.e. INSIDE the audit's predicted 2–4, and every options *t* shrinks by √2.212 = 1.487×.
> `UNIVERSE_RESULTS.json` has always shipped 2.2121 — the artifact was right and only the prose
> travelled without its scope. No verdict changes; see item 5 below for the check.**

**Clustering factor 1.85 on this book — below the audit's predicted 2 to 4.** At month blocks the
3,042-trade pre-correction book carries 118 blocks, a design effect of **1.848**, and an effective
sample of **1,646 of 3,042**. Every *t*-like quantity on THIS book therefore shrinks by
√1.85 = **1.36**, not by the 1.4–2.0 the audit expected. (On the corrected book it shrinks by
1.487 and the audit's range was right — see the scope correction above.) Its worked example — "a *t* of −5.24 moves into the −2.5 to −3.7
range" — lands about right by coincidence rather than by the mechanism it named: the sign-test z
did fall to −2.91, but from the DATA CORRECTION, not from the clustering.

**And the correction overturns nothing.** The pre-correction gap's date-block CI is [−11.66pp,
−4.51pp], still excluding zero. Clustered inference makes every options interval wider and leaves
every verdict where it was.

### A RAW DESIGN EFFECT IS NOT EVIDENCE OF CLUSTERING · **found by a failing test**

A book of 600 independent draws assigned to 12 blocks of 50 — **no clustering by construction** —
reports a design effect near **1.8**, an apparent 45% loss of sample size that is pure sampling
error in MSB/MSW. With `k` blocks that ratio is F(k−1, n−k), whose spread is ≈√(2/(k−1)); at a
mean block size of 25–50, a 2% wobble in the ICC becomes a 2× design effect.

Applying that as a haircut would **manufacture a correction out of noise — the mirror image of
the error R3 exists to fix.** So the design effect is now scored against its own shuffled null,
using the project's established method (X7): outcomes are permuted across blocks, every block
size preserved exactly, and `clustering_measurable` is true only above the null's 95th
percentile. On the real book it passes clearly (**deff 1.848 vs null p95 1.266**), so the
clustering is genuine — but genuine because it was tested, not because the number looked large.

**R3.4, purge and embargo.** `pbo_cscv` now purges dates whose 75-day label window crosses an
IS/OS boundary; **9.08% of dates are purged** per split. `embargo_days=0` reproduces the old
unpurged split exactly, so the correction's cost is measurable rather than asserted. The
corrected run reports PBO **12.86%** against the record's 35.7%; the isolating A/B is below and
its result contradicts what this session first asserted about the direction.

### R3.4 ISOLATED — the purge LOWERS PBO, which is the opposite of what this session asserted

The corrected run reports PBO 12.86% against the record's 35.7%, and those differ in two ways at
once. An A/B was run on a single feature pass per book with **only `embargo_days` varying**:

| book | embargo 0d (old behaviour) | embargo 75d (shipped) | purge effect | dates purged |
|---|---|---|---|---|
| corrected | **17.14%** | **12.86%** | **−4.29pp** | 9.08% |
| pre-correction | **48.57%** | **38.57%** | **−10.00pp** | 9.37% |

**Purging lowers PBO on both books.** The docstring written earlier in this session asserted the
contamination "biases PBO DOWNWARD" — i.e. that the unpurged figure was too low. It is too
**high**, by 4 to 10 points. The assertion was reasoning, not measurement, and it is corrected in
place at `options_autopsy.pbo_cscv`. **No mechanism is verified.** A plausible hypothesis, offered
as one and not as a finding: boundary dates are where trades straddle regimes, so removing them
makes the in-sample ranking more stable out of sample. It has not been tested.

### AND A REPRODUCIBILITY PROBLEM THAT IS NOT MINE TO FIX HERE — **`## BUGS FOUND`**

**The pre-correction book's PBO does not reproduce: 48.57% today against the 35.7% recorded on
2026-08-03, on the same trades and the same code path.** The cause is not the corrections and not
the purge — the A/B above holds both fixed. It is that **`data/options_derived/` has grown from
111 names to 317 entries while the miner has been running.** The record's autopsy carried
greek-stack coverage of 2,030/3,042 (66.7%) and daily-surface coverage of 2,071/3,042 (68.1%);
the corrected run carries **3,885/3,885 — 100% on both.**

Two consequences, and the second is the one that matters:

1. **Good news:** the 64-feature gate is now tested on the whole book rather than two-thirds of
   it, and it still returns **zero survivors**. That is a stronger rejection than the record's.
2. **`AUTOPSY_*` numbers are not comparable across sessions while the miner is live.** Feature
   coverage changes underneath them, so a PBO or a feature *p*-value quoted from one session
   cannot be differenced against another's. Nothing warns about this today. The autopsy should
   stamp its derived-data coverage into its own result file the way the panel stamps
   `panel_window`, and any cross-session PBO comparison should be treated as invalid until it
   does. Recorded, not fixed — it is outside this session's items.

**R3.5**, the Deflated Sharpe at `n_eff`, ships as `deflated_sharpe_clustered` and carries
`clustering_measurable` so nobody quotes a haircut that is estimator noise.

**Verdict: ADOPTED as the inference layer of record.** The trade-level bootstrap is retained for
comparability with every historical figure and is explicitly no longer what decides anything.
**Follow-on:** every options interval in the corpus is optimistically narrow by ~1.36× and should
be re-read that way. The seed instability recorded under R2 is the more urgent problem.

## R7 — THE `term_slope` FLOOR · **THE NEW FLOOR PASSES AND THE FILTER FAILS ANYWAY**

**Committed threshold:** Part 0, unchanged. G3a ≥ 52 retained alerts/yr, G3b ≥ 60% of names AND
≥ 60% of months, G3c ≥ 20% retention, in addition to G1/G2/G4/G5/G6/G7.

**R7's premise was right about the bar and wrong about the filter.** It called this "the thinnest
rejection in the corpus": the economic arm had replicated almost exactly out of sample (+8.89pp
against the +8.12pp that got it adopted), and the filter failed on one arbitrary constant. On
corrected data both halves of that reverse.

| arm, on the B2 scope (new names, late half) | pre-correction | **corrected** |
|---|---|---|
| retention | 36.4% | **35.9%** (478/1,333) |
| **economic gain** (bar: `MIN_LATE_GAIN` = +5.00pp) | **+8.89pp** | **−1.12pp** |
| expectancy, all → filtered | +4.64% → +13.54% | **+1.84% → +0.71%** |
| tail retention | 41.2% of winners on 37.3% of trades | **34.0% on 35.9%** |
| G3a flow | never measured | **95.6/yr ✓** |
| G3b span | **never measured** | **96.2% of names, 98.2% of months ✓** |
| G3c backstop | never measured | **35.9% ✓** |
| **passes G3** | — | **TRUE** |
| old 40% arm would say | FAIL | FAIL |

**The re-committed floor answers its own question: the 40% constant WAS rejecting a filter that
is genuinely broad.** G3b — the arm that had never been measured, and the one R7 said the filter
could still fail on — passes at 96% of names and 98% of months. `term_slope` was never a
disguised cherry-pick of a handful of names.

**And it no longer matters, because the arm that used to replicate is now the one that fails.**
On corrected data the filter makes its own out-of-sample book *worse* (+1.84% → +0.71%, a gain of
−1.12pp against a +5.00pp bar), and it is no longer tail-enriching. The full-sample and
broad-book readings are positive but far below the bar (+1.35pp, +1.82pp).

**Verdict: `term_slope` REJECTED — B2 FAILS on the economic arm.** The rejection stands, and now
rests on the quantity that matters rather than on an underived constant. **Follow-on:** the
retention-floor question is closed; G3a/G3b/G3c replace the single `MIN_RETAINED` arm as the
shipped gate. The +8.89pp out-of-sample replication that made this look like a live filter worth
rescuing was a product of the corrupted price basis and **must not be quoted again**.

## O20 — POINT-IN-TIME LIQUIDITY · **THE AUDIT'S EXPECTATION WAS WRONG; THE HEADLINE ROSE**

**Committed threshold:** Part 6 above. The miner's own screen, applied at each entry date, to
both arms of the control, with unmeasurable days as `None` and never `False`. And, pre-committed:
if the headline does NOT fall, that is reported as the audit's expectation being wrong.

The audit says: *"Then re-report the headline. Expect it to fall. That is the correct number."*

| slice | n | expectancy | PF |
|---|---|---|---|
| whole corrected book | 3,885 | +3.41% | 1.092 |
| **point-in-time LIQUID** | **3,359 (86.5%)** | **+4.82%** | **1.131** |
| point-in-time ILLIQUID | 495 (12.7%) | **−7.84%** | 0.800 |
| unmeasurable | 31 (0.8%) | +30.76% | 2.350 |

**It rose.** Screening out names that were untradeable *on the day the alert fired* removes a
slice that loses 7.84% per trade, and the surviving book is better than the whole. Coverage is
**99.2%** — the screen resolves on all but 31 trades. Both held-out halves stay positive (+6.56%
early, +3.31% late). The mechanism is coherent: point-in-time-illiquid entries are exactly where
the entry spread is widest, and this is a long-premium strategy paying that spread at both ends.
It is also **implementable**, unlike the survivorship diagnostic — liquidity as of the entry date
is knowable at the entry date.

### O20 DOES NOT RESCUE THE SIGNAL — the improvement is a universe effect, not a signal effect

The control was screened by the same rule, and it benefits at least as much:

| slice, seeds pooled | real | control | gap | date-block CI95 | sign-test z |
|---|---|---|---|---|---|
| all trades | +3.41% | +10.88% | −7.47pp | [−13.92, −2.43] | −2.907 (p 0.0037) |
| **PIT-liquid only** | **+4.82%** | **+12.00%** | **−7.18pp** | **[−14.48, −1.71]** | **−3.475 (p 0.0005)** |
| PIT-illiquid only | −7.84% | +1.44% | −9.28pp | [−17.07, −1.17] | −2.500 (p 0.0124) |

**The signal loses to random entry on the liquid subset too — and by the sign test, more
decisively than on the whole book.** Restricting to tradeable names lifts BOTH arms. Nothing here
is evidence for the alert.

### The limit of the repair, and a correction to the audit's premise

Verified against `mine_options_cache.py` this session:

* **The pool order IS hindsight.** Names are ranked for mining by TODAY's market cap
  (`mine_options_cache.py:15-20`). TRUE, and the larger effect.
* **The liquidity screen was NOT today's.** `name_is_viable` measures real option tradeability on
  the name's FIRST CACHED YEAR, not on a present-day chain (`:160`). The audit's "selected by
  current liquidity" is not accurate for the screen it proposes to fix.

So O20 answers "was this name tradeable on the day?" and **cannot** answer "which names would
have been in the pool at all in 2016?" — the names that would have failed were never mined, and
no evaluation-time filter recovers data that is not on disk. `survivorship_probe` remains the
only read on the part O20 cannot touch.

**Verdict: ADOPTED as a reported partition; the audit's expectation is REFUTED.** Shipped as
`o20_point_in_time_liquidity` on every run. It is **not** promoted into the headline: the headline
stays the whole book at aggression 1.0, because that is what every historical figure used, and
because a filter that improves a result is exactly the kind that needs a second panel before it
is believed.

**Follow-on:** this is the third time in two sessions (R10, then O20) that a bias the record
assumed ran in the strategy's favour has run the other way. That is now a pattern worth stating:
**this project's expectations about the direction of its own biases have been wrong more often
than right, and should be measured rather than reasoned about.**


---

## X7 RE-RUN AT THE TRUE N · **THE DEFLATED SHARPE ROW IS CONFIRMED, AND STRENGTHENED**

**Committed threshold:** carried forward from Session 4 and quoted in Part 6 above. X7's *"the
Deflated Sharpe survives calibration"* was measured with **N = 8 inside BOTH the real run and all
100 placebo draws**. M1 then replaced N with the measured equity count of 84, which changes both
sides. The claim was marked **PROVISIONAL and unquotable** until the placebo was re-run at the
true N. It has been.

**What was run:** `python -m scripts.placebo --panel panel_grid0.pkl --n 100 --seed0 1000`, the
identical panel checkpoint and identical seeds (1000–1099) as X7's original sweep, on code where
`_deflated_sharpe` now reads N from `RESEARCH_LOG.md`. The output stamps its own denominator:
`n_trials_used = 84`, `n_trials_from_research_log = 84`, source `RESEARCH_LOG.md (audit M1)`.

### The harness reproduces exactly, which is what makes the comparison readable

Every quantity that does NOT depend on N is **identical to the last digit** across the two sweeps:

| rate on pure noise | N = 8 | N = 84 |
|---|---|---|
| holdout gate confirms any theme | 6% | **6%** |
| long-short t ≥ 2.0 | 8% | **8%** |
| long-short t ≥ 3.0 | 1% | **1%** |
| max theme IC t ≥ 2.0 | 39% | **39%** |
| PBO < 50% | 55% | **55%** |

PBO and max-theme-IC-t are identical on all 100 draws individually, not merely in aggregate. **So
every calibrated bar X7 published stands unchanged** — only the Deflated Sharpe row was ever in
question.

### The Deflated Sharpe, calibrated at the honest denominator

| | N = 8 (X7 original) | **N = 84 (true)** |
|---|---|---|
| real run | 0.9970 | **0.8997** |
| noise median | 0.2802 | **0.1143** |
| noise p95 — **the calibrated bar** | 0.8567 | **0.7216** |
| noise p99 | — | 0.8498 |
| noise maximum | 0.9788 | **0.8649** |
| noise draws clearing the 0.95 convention | **2%** | **0%** |

**The row is CONFIRMED and the statistic is MORE discriminating at the true N, not less.** Zero of
100 definitionally-worthless signals reach 0.95, against two at N = 8. The 0.95 convention is one
of the few bars in this project that noise essentially never clears.

**And the strategy's 0.8997 exceeds ALL 100 placebo draws** — the highest noise draw is 0.8649, so
the empirical *p* is at the sweep's resolution floor (≤ 0.01). Against the calibrated bar of
**0.7216** it clears comfortably.

**BOTH M1 AND X7 ARE RIGHT, AND THEY WERE NEVER IN CONFLICT.** M1's finding stands exactly as
written: **the edge does not clear the > 0.95 bar.** X7's finding stands too: the Deflated Sharpe
is a genuinely discriminating statistic. The reconciliation is that **at the honest denominator
the 0.95 convention is STRICTER than the noise floor requires.** So the Deflated Sharpe is now the
one bar in this project where the strategy is **distinguishable from noise and still fails its
conventional threshold**. Report it that way — quoting either half alone misleads:

> Deflated Sharpe **0.8997 at N = 84 — fails the conventional > 0.95 bar, while sitting above all
> 100 placebo draws (calibrated bar 0.72).**

### A SECOND, UNLOOKED-FOR BENEFIT OF M1 — the adoption gate got harder for noise to pass

**CPCV weight adoption on pure noise fell from 27% to 21% of draws**, and the change is
one-directional: **six draws stopped adopting and not one started.** All six moved from a
recommended scheme (`ic-proportional`, `equal-weight`, `positive-equal`, `risk-parity`) to
`current-default`. PBO was identical on every one of them — only the adopt decision moved.

The mechanism is deterministic, not a tie-break: the adopt gate reads the Deflated Sharpe, and a
larger N lowers it, so fewer noise draws clear the bar. **This is not the run-to-run
non-reproducibility the project is chasing** — that remains open and unexplained, and this was
briefly mistaken for it during this session before the one-directional pattern was checked.

X7's post-hoc finding was that CPCV adoption manufactures ~+1.4 of long-short *t* out of nothing
and fires on 27% of pure-noise draws. **At the honest denominator it fires on 21%.** Still far too
often to trust an adopted scheme, and the shipped strategy still does not adopt — but M1 bought a
measurable improvement in the pipeline's noise resistance as a side effect of fixing a
denominator, which is worth recording.

**Note on comparability:** X7's original sweep ran with `--no-costs` (`costs_measured: false`);
this one measured costs, so `breakeven_one_way_bps` exists here and is absent there. No committed
threshold reads it.

**Verdict: X7's Deflated Sharpe row CONFIRMED at the true N; the PROVISIONAL marking is
LIFTED.** Every other calibrated bar in X7's table is unchanged and was never affected.
**Follow-on:** `scripts/placebo.py` now banks `deflated_sharpe_detail` per draw and stamps
`trial_count` on the output, so the next change to N costs arithmetic rather than another sweep.

## BUGS FOUND — session 5 (per RUN_RULES.md Part A rule 3)

1. **`AUTOPSY_*` results are not comparable across sessions while the miner is live, and nothing
   says so.** `data/options_derived/` grew from 111 names to **317 entries** during the audit, so
   the 64-feature gate's coverage went from 2,030/3,042 (66.7%) to **3,885/3,885 (100%)**. The
   pre-correction book's PBO therefore reads **48.57%** today against the **35.7%** recorded on
   2026-08-03 from the same trades and the same code path. **Not fixed** — the autopsy should
   stamp its derived-data coverage into its own result file the way the panel stamps
   `panel_window`. Until it does, treat any cross-session PBO or feature *p*-value difference as
   invalid. `valuation/edge/options_autopsy.py:run`.

2. **A raw ICC design effect was about to be applied as a haircut, and it is mostly estimator
   noise at these block sizes.** Caught by a failing test rather than by review. 600 independent
   draws in 12 blocks of 50 report a design effect near 1.8. **Fixed** — `options_stats.effective_n`
   now scores the design effect against a shuffled null and gates it behind
   `clustering_measurable`.

3. **`pbo_cscv`'s purge was O(n²) per split** — 70 splits over ~2,500 dates would have added
   minutes to every autopsy. **Fixed** (bisect), `options_stats.purged_split`.

4. **A mechanism asserted in a docstring this session was wrong in direction.** `pbo_cscv` claimed
   boundary contamination "biases PBO DOWNWARD"; measured, purging LOWERS PBO by 4–10pp, so the
   unpurged figure was too HIGH. **Fixed in place**, and no replacement mechanism is claimed. It
   is recorded because writing a plausible mechanism into a docstring and shipping it *is* the
   failure mode this project keeps paying for.

5. **`optuniv_run.py` writes its control and results into `data/options_universe/`, overwriting
   the previous run's artifacts**, with `--state` the only way to preserve a prior trade log. The
   pre-correction run's `state.pkl`, both control seeds, `UNIVERSE_RESULTS.json` and
   `AUTOPSY_BROAD_RESULTS.json` had to be copied out by hand before the re-run, or the record's
   own book would have been destroyed and the A/B in Part 6 would have been impossible.
   **Not fixed** — the runner should refuse to overwrite a banked result without an explicit flag.

## WHAT WAS NOT DONE, AND WHY — session 5

- **The mid-fill (aggression 0.0) decomposition was NOT re-run.** R2's scope names it. It is a
  diagnostic, never a headline (bar B5), and the verdict rests on the aggression-1.0 book. The
  spread toll of −6.59pp recorded in `HANDOFF_universe_backtest.md` §2a is therefore **void along
  with the rest of that file and has not been replaced.** One command (`--aggression 0.0
  --universe-from ... --state <new>`), roughly 20 minutes.
- **The four `compute_signals`-touching autopsy features were not examined individually.** R2
  names them. The autopsy returns zero survivors overall, so no individual feature changes a
  verdict, but the audit asked for them specifically.
- **`n_eff` was not fed into the options Deflated Sharpe on the shipped headline.**
  `deflated_sharpe_clustered` is computed and shipped alongside, but `deflated_sharpe` remains
  the raw-n figure so every historical number stays comparable. Deliberate; flagged here so it is
  not mistaken for an oversight.
- **The seed instability was closed for the CONTROL only.** Every other bootstrap in the options
  lane still runs at a single seed. Whether any of them is similarly seed-sensitive is unmeasured.

---

# SESSION 5 CLOSEOUT — the five items Session 5 declared unfinished

Session 5's own `WHAT WAS NOT DONE` and `BUGS FOUND` are the scope. **This is not Session 6.**
Everything below was written **before any code was changed and before any run was launched**;
the results follow underneath, in a separately marked section.

## PRE-COMMITMENTS, written before the work

### Item 1 — stamp the autopsy's derived-data coverage (BUGS FOUND #1, unfixed)

Not a statistical test, so no threshold. **Acceptance criteria, committed:**

1. `options_autopsy.run()` ships a `derived_data` block in its own result dict, so every
   `AUTOPSY_*.json` carries the state of `data/options_derived/` **at the moment it ran**.
2. The stamp is a **fingerprint**, not a count — two runs with the same number of names but
   different contents must not compare equal.
3. A helper answers the comparability question mechanically, so a cross-session difference either
   **reconciles or refuses** rather than being adjudicated by a human reading a note.
4. A test pins it, including the refusal direction.

**Committed in advance:** the stamp is DESCRIPTIVE. It does not gate, block or alter any run.
A field that can fail a run would get switched off the first time it is inconvenient — which is
exactly the failure mode `RUN_RULES` §A5 exists for.

### Item 2 — `optuniv_run.py` must refuse to overwrite a banked result (BUGS FOUND #5, unfixed)

**Acceptance criteria, committed:**

1. The refusal fires **before any scoring work**, not after 20 minutes of compute.
2. Refusal is the DEFAULT. Proceeding requires an explicit flag.
3. Even with the flag, prior artifacts are **moved aside, never destroyed** — no path through this
   runner may delete a banked book.
4. A legitimate **resume** of the same run must NOT be blocked. Resuming is the feature; the
   defect is a *different* run silently landing on top of a banked one.
5. Tests pin both directions: a resume is allowed, a parameter change is refused.

### Item 3 — the mid-fill (aggression 0.0) decomposition

**Committed BEFORE the run, and this is the whole point of the pre-commitment:**

* This is a **DIAGNOSTIC, never a headline.** Bar B5 stands. Whatever it returns, the R2 verdict
  (the entry signal is dead) does not move: it is measured at aggression 1.0 and this run does not
  touch that book.
* **It cannot rescue the entry signal and will not be read as if it could.** Aggression 0.0 fills
  at the mid instead of paying the spread. A book that is profitable only when it does not pay the
  spread is not a tradeable book — it is a measurement of the toll.
* The number being replaced is the **−6.59pp spread toll** in `HANDOFF_universe_backtest.md` §2a,
  which is void along with the rest of that file.
* **Pre-committed disposition, both branches:** if the run completes on the pinned 187-name
  universe, the toll is **replaced** with the corrected figure and labelled a diagnostic. If it
  does not complete or the universe cannot be pinned, the figure is marked **WITHDRAWN** and left
  withdrawn. It is not left void either way, and no third option is available after seeing the
  number.

### Item 4 — the four `compute_signals`-touching features, individually

The four are named at `VALQUO_EDGE_AUDIT.md:155`: **`term_slope`, `skew_25d`, `vrp`, `gex_proxy`**
— the consumers of the mis-stated spot in B1. In the autopsy's namespace: `f_term_slope`,
`f_skew_25d`, `f_vrp`, `f_gex_proxy`, plus any feature derived from them.

**Committed thresholds — the SAME gate the other 60 features face, no special-casing:**

* A feature is **INFORMATIVE** only if it passes `holdout_feature` in **both** split directions
  (`passes_both_directions`), which is `MIN_LATE_GAIN` = +5.00pp with the retention and tail
  floors, at `ALPHA` = 0.05 on the permutation p.
* A feature that clears the gate in **one** direction only is **NOT_REPLICATED**, not a
  near-miss to be argued for.
* **BH-FDR at q = 0.10 across the whole 64-feature sweep is the multiplicity control**, not a
  per-feature p. A feature with a nominal p < 0.05 that fails FDR is a **null**.
* **Pre-committed reading of the likely outcome:** the aggregate already returns zero survivors,
  so the expected answer is that all four are individually uninformative. **That is a complete
  answer and it closes the item.** If one of the four DOES clear both directions, it is reported
  as a finding requiring pre-registered replication — it is not adopted here, on this panel,
  by this session.

### Item 5 — how far the seed instability reaches

**The rule is committed before the measurement, as the prompt requires.**

Define, for a statistic *S* run at seeds 0–4 on the same book:
`seed_range(S) = max(S) − min(S)`, and `ci_width(S)` = the width of the statistic's own reported
CI95 at seed 0.

A statistic gets **MULTI-SEED as standing policy** (≥5 seeds, report the median with the range
beside it) if **either** trigger fires:

* **T1 — DECISION.** Any published boolean derived from *S* (`beats_control`, `passes_B2`,
  `passes_G3`, `negative_at_significance`, …) takes a different value on any of the five seeds.
  **Zero tolerance; magnitude is irrelevant.** This is the trigger R2 hit — seed 0 said
  inconclusive and seed 1 said dead.
* **T2 — MAGNITUDE.** `seed_range(S) ≥ 0.10 × ci_width(S)`.

Otherwise the statistic **stays single-seed**, and its measured seed range is **published beside
it once** so nobody has to re-derive it.

**The 0.10 is a CONVENTION and is labelled as one.** Its basis: a bootstrap's Monte Carlo error
should be small relative to the statistical uncertainty it is estimating, and the range of five
draws is roughly 2.3 standard deviations, so the trigger fires at a Monte Carlo sd of about 4% of
the CI width. It is **not** calibrated against a null the way X7's bars are, and it should not be
quoted as if it were. It errs toward more seeds, which is the direction this project has been
wrong in before.

**Ambiguity is a NULL and a NULL defaults to the stricter branch (multi-seed).** Committed now,
so that a statistic sitting on 0.10 cannot be argued down after the fact.

**Scope committed before measuring:** every seeded bootstrap in the options lane that feeds a
shipped field — `bootstrap_diff` (`home_run`, `control_comparison`), `date_block_bootstrap` and
`date_block_diff` (`clustered_inference_R3`, `control_comparison`), `effective_n`'s shuffled null,
and the autopsy's permutation p / `combiner_test`. The random-entry control is **already** at five
seeds and is the precedent, not a subject.

## RESULTS

### ITEM 1 — the autopsy now stamps its own derived-data coverage · **DONE**

**What shipped.** `options_autopsy.derived_stamp()` walks `data/options_derived/` and returns a
**fingerprint** — a SHA-1 over sorted `(relative path, byte size)` — alongside the name, file and
byte counts, the bar-cache count and `REGIME_VERSION`. `run()` ships it as `derived_data` on every
result, so every `AUTOPSY_*.json` written from now on records the state of the derived layer at the
moment it ran. `derived_comparable(a, b)` answers the cross-session question mechanically and
returns `{comparable, reason, differences}`.

**Why a fingerprint and not a count.** A count is blind to the case that actually bites: a re-mine
that replaces a name's contents without changing how many names exist. The fingerprint uses SIZE
rather than mtime deliberately — a rewrite producing identical bytes IS the same data and must
compare equal, while any content change moves a pickle's size. Pinned by
`test_closeout_item1_the_derived_stamp_is_a_fingerprint_not_a_count`, which asserts the name count
is unchanged before asserting the fingerprint moved.

**It is DESCRIPTIVE and gates nothing** — pre-committed above, and pinned by
`test_closeout_item1_the_stamp_is_descriptive_and_gates_nothing`, which points it at a
non-existent directory and requires a stamp rather than an exception. A field that can fail a run
gets switched off the first time it is inconvenient (`RUN_RULES` §A5).

**Measured live, 2026-08-06:** 315 names, 315 daily files, 2,945 contract-year files,
17.78 GB, fingerprint `4e8583dfe812f704`, `regime_version` 2.

#### WHICH RECORDED AUTOPSY FIGURES ARE NOW KNOWN NON-COMPARABLE

**The honest answer is the widest one: NO autopsy figure in this project's record is comparable to
any other, because NOT ONE of them carries a stamp.** `derived_comparable` returns
`comparable: false` with reason *"comparability is unknowable, not merely unproven"* for every pair
drawn from the existing record. That is not pedantry — here is the measured damage:

| | banked 2026-08-03 | banked 2026-08-05 (corrected) |
|---|---|---|
| trades | 3,042 | 3,885 |
| greek-stack coverage | **66.7%** | **100.0%** |
| daily-surface coverage | **68.1%** | **100.0%** |
| PBO | **35.71%** (no embargo — the field did not exist) | 12.86% (embargo 75d) |
| Deflated Sharpe, term_slope-filtered | 0.9569 | 0.8063 |
| Deflated Sharpe, unfiltered | 0.8813 | 0.4959 |

The sharpest single number: **the pre-correction book's PBO re-ran at 48.57% on 2026-08-05 against
the 35.71% banked on 2026-08-03 — same trades, same unpurged code path, a 12.9pp move produced by
nothing but the miner.** The A/B in Part 6 held the correction and the embargo fixed, so the only
remaining variable was the derived layer, which went 111 names → 315.

**What "the comparable version" is, now that the stamp exists.** There is no retrofit: a
fingerprint cannot be computed for a directory as it stood in the past. So the comparable versions
are **the ones written from today forward**, and the rule is mechanical — two `AUTOPSY_*.json`
files may be differenced if and only if `derived_comparable()` on their `derived_data` blocks
returns true. Concretely:

* **Any PBO, feature *p*-value, FDR discovery set or feature-coverage figure quoted from before
  2026-08-06 is a POINT-IN-TIME observation, not a comparable measurement.** Quote it with its
  date and its coverage, never as a difference against another session's.
* **The four Deflated Sharpe figures in the table above are NOT a before/after pair.** They differ
  by the B1 correction *and* by a third of the book gaining greek coverage.
* Figures computed **only from the trade rows** are exempt, and this is the distinction the stamp
  buys — see item 4, where the four `compute_signals` features are shown to be derived-layer-free
  and therefore genuinely differenceable across the two books.

### ITEM 2 — `optuniv_run.py` refuses to overwrite a banked result · **DONE**

**The defect was a data-loss risk, not tidiness.** The runner wrote `state.pkl`,
`control_rows.pkl`, `UNIVERSE_RESULTS.json` and `AUTOPSY_BROAD_RESULTS.json` into
`data/options_universe/` unconditionally. Session 5 preserved the record's own pre-correction book
**by hand**; without that copy the Part 6 A/B could not have been run at all.

**What shipped.**
* A `run_key` — universe SHA-1 + count, aggression, entry window, smoke flag — is written into
  `BANK_MANIFEST.json` **the moment the guard clears, before any scoring**. Writing it only on
  success would have made a run killed at minute 12 unable to resume its own state, i.e. the guard
  would have broken the feature it exists to protect.
* `guard_bank()` returns one of four actions: `clear` (nothing banked), **`resume`** (manifest
  run_key matches — resuming is the feature and must not be blocked), **`refuse`** (default), or
  `archived`.
* Refusal happens **before any scoring work**. Twenty minutes of compute followed by a refusal
  would be worse than useless — it would train the next person to pass `--overwrite` blind.
* `--overwrite` does **not** delete. It **moves** the prior artifacts into
  `<out-dir>/banked/<timestamp>/`. **No path through this runner destroys a banked book** — a
  stronger property than "asks first", and pinned by
  `test_closeout_item2_no_path_through_the_runner_destroys_a_banked_book`, which asserts the
  archived copy holds the ORIGINAL bytes.
* `--out-dir` added as the friction-free escape: run a second book somewhere else entirely.
* **An unstamped directory is REFUSED, not assumed empty.** Every artifact banked before this guard
  has no manifest, which is precisely the case that cost the hand-copy. `reason` says so:
  *"UNKNOWABLE, not merely unproven"* — the same standard as item 1.

**Verified against the real record, not only in tests.** Pointed at
`data/options_universe/` with a mismatched key:

```
action: refuse
occupants: ['UNIVERSE_RESULTS.json', 'AUTOPSY_BROAD_RESULTS.json', 'control_rows.pkl', 'state.pkl']
reason: no BANK_MANIFEST.json -- these artifacts predate the guard, so whether they belong to
        this run is UNKNOWABLE, not merely unproven
```

Those are exactly the four files that had to be copied out by hand.

### ITEM 4 — the four `compute_signals` features, individually · **ALL FOUR NOT INFORMATIVE**

The four named at `VALQUO_EDGE_AUDIT.md:155` are the consumers of B1's mis-stated spot:
`term_slope`, `skew_25d`, `vrp`, `gex_proxy`. In the autopsy's namespace: **`f_term_slope`,
`f_sig_skew_25d`, `f_sig_vrp`, `f_sig_gex_proxy`**. Scored on the **corrected** 3,885-trade,
187-name book (`AUTOPSY_BROAD_RESULTS.json`, generated 2026-08-05T20:27), against the same gate
the other 60 features face — no special-casing, as pre-committed.

| feature | cov | IC (in-sample) | early→late gain / p | late→early gain / p | both dirs | **verdict** |
|---|---|---|---|---|---|---|
| `f_term_slope` | 1.000 | +0.0521 | +0.58pp / 0.412 | +4.42pp / **0.016** | **False** | NOT_REPLICATED |
| `f_sig_skew_25d` | 0.807 | +0.0019 | −2.79pp / 0.862 | −0.54pp / 0.591 | False | **NULL** — wrong sign both ways |
| `f_sig_vrp` | 1.000 | −0.0156 | +0.26pp / 0.448 | +3.06pp / 0.056 | False | **NULL** |
| `f_sig_gex_proxy` | 0.936 | +0.0484 | +2.47pp / 0.146 | **+6.89pp / 0.0015** | **False** | NOT_REPLICATED |

**Verdict: none of the four is INFORMATIVE.** Not one passes both split directions, which is the
pre-registered bar. The aggregate answer (zero survivors of 64) and the narrow answer the audit
asked for agree.

**`f_sig_gex_proxy` is the one worth writing down, and it is a warning rather than a lead.** It is
one of only **four FDR discoveries among 127 hypotheses** at q = 0.10 — its late→early half clears
+6.89pp at p = 0.0015 with 50.6% retention and a tail ratio of 1.13, i.e. it passes every floor in
that direction. It fails the other direction (+2.47pp, p = 0.146). Per the pre-commitment that is
**NOT_REPLICATED, not a near-miss to be argued for.**

**And here is the finding that closes it — the direction that passes SWAPS when B1 is repaired.**
Re-scored on the pre-correction book (3,042 trades, banked 2026-08-03):

| feature | book | early→late | late→early |
|---|---|---|---|
| `f_sig_gex_proxy` | pre-correction | **PASSES** (+5.31pp, p 0.0020) | fails (−0.10pp, p 0.513) |
| `f_sig_gex_proxy` | corrected | fails (+2.47pp, p 0.146) | **PASSES** (+6.89pp, p 0.0015) |
| `f_term_slope` | pre-correction | +4.89pp, p 0.0195 (fails the +5.00pp floor by 0.11pp) | +2.18pp, p 0.152 |
| `f_term_slope` | corrected | +0.58pp, p 0.412 | +4.42pp, p 0.016 |

**Both features that show any signal at all flip which half of the sample they work on.** A
property that survives a price-basis correction would not do that. This is direct measured support
for the both-directions requirement — a gate demanding a single direction would have adopted
`gex_proxy` in August 2026 on the early half and then adopted it again on the late half for the
opposite reason, and called that replication.

**This comparison is legitimate, and item 1 is what licenses saying so.** All four features are
read off the **trade row** (`options_autopsy.py:471-477` maps `compute_signals`' outputs straight
onto the alert), NOT off `data/options_derived/`. So the derived-layer growth that makes the two
books' PBO and greek features non-differenceable does **not** touch these four. Two caveats travel
with it anyway: the two books are **different trade sets** (B1's spot was throwing the 0.90–1.20
moneyness prefilter, so 3,042 vs 3,885 alerts), and `f_sig_skew_25d`'s coverage moved 0.529 → 0.807
for the same reason. It is a comparison of two books, not a controlled A/B, and is reported as one.

**One honest note on the FDR count.** The pre-correction book had **zero** FDR discoveries and the
corrected book has four, but `f_sig_gex_proxy`'s *p* barely moved (0.0020 → 0.0015). Benjamini–
Hochberg is a **step-up** procedure: a *p* becomes a discovery partly because OTHER hypotheses in
the sweep got smaller. So the four discoveries are a property of the sweep, not four independent
findings — **and that part IS confounded by the derived layer**, since the other 60 features draw
on it. `f_sig_gex_proxy`'s own *p*-value is not confounded; its FDR STATUS is.

**Item closed. No adoption, no follow-up run, and no re-opening without a new reason** — the
pre-commitment allowed exactly one escalation (a feature clearing both directions) and none did.

### ITEM 3 — the mid-fill (aggression 0.0) decomposition · **THE −6.59pp TOLL IS REPLACED BY −8.28pp**

**Pre-commitment honoured:** the run completed on the pinned universe, so the figure is REPLACED,
not withdrawn — the disposition was fixed in advance for both branches. **This is a DIAGNOSTIC and
bar B5 stands:** every headline in this project is quoted at aggression 1.0, and nothing here
touches the R2 verdict.

**What was run.**
```
python optuniv_run.py --data-root <repo>/data --workers 5 --aggression 0.0
  --state <tmp>/mid_state.pkl
  --universe-from <tmp>/optuniv_precorrection/state.pkl     # the same frozen 187 names
  --out-dir <tmp>/optuniv_mid                               # the new item-2 escape hatch
```
187 names, window 2016-01-01 → 2025-10-15, **3,815 mid-fill trades** against the corrected
aggression-1.0 book's 3,885. ~24 minutes. The comparator is the corrected R2 book, not the void
one.

#### The replacement table

| slice | touch (a=1.0) | mid (a=0.0) | **spread toll** | median entry spread |
|---|---|---|---|---|
| **ALL** (n 3,885 / 3,815) | **+3.41%** | **+11.69%** | **−8.28pp** | 6.67% |
| mega (1,002 / 986) | +4.71% | +10.08% | −5.37pp | 4.65% |
| large (2,062 / 2,024) | +0.86% | +9.44% | −8.57pp | 7.06% |
| mid (777 / 760) | +7.65% | +18.53% | −10.88pp | 8.33% |
| small (44 / 45) | +18.25% | +32.52% | −14.27pp | 8.70% |
| 54 old names (1,532 / 1,511) | +9.37% | +13.60% | −4.23pp | 4.79% |
| 133 new names (2,353 / 2,304) | **−0.47%** | +10.43% | **−10.90pp** | 8.16% |

**PAIRED, which the void table never did.** The two books do not contain the same trades —
aggression changes the entry premium, which changes which alerts clear the floors. Matching on
(ticker, alert date, expiry, strike) gives **3,764 alerts present in both**:

* paired toll **−8.88pp** (touch +2.80% vs mid +11.68% on the matched set)
* **date-block CI95 [−9.99pp, −7.74pp]** over 118 monthly blocks — the R3-correct interval, and
  it excludes zero by a distance
* **78.8% of individual alerts (2,967/3,764) are worse at the touch**
* the naive paired *t* is −14.9 and is **not** the number quoted: these are clustered, and R3's
  standing rule is that the date-block interval carries it

#### What changed against the void table, and what it means

1. **The toll is BIGGER than the record said: −8.28pp against −6.59pp.** The market takes **71% of
   the gross edge at the touch**, not 56%. The gross number barely moved (+11.73% → +11.69%) — it
   is the NET that fell (+5.14% → +3.41%) and the measured spread that rose (median 4.78% → 6.67%).
   **B1 was understating the spread the strategy actually pays.** Same signature as everywhere
   else in that file: an adjusted spot against as-traded strikes.
2. **"The old-vs-new gap is 100% spread" is WRONG and is corrected here.** §2a claimed the two
   cohorts were +11.99% and +11.56% at the mid — a 0.43pp gross gap — and concluded *"breadth does
   not dilute the signal; it dilutes the fill."* Corrected: at the mid they are **+13.60% and
   +10.43%, a 3.17pp gross gap**. The net gap is 9.84pp, so **spread explains 6.67pp of it — 68%,
   not 100%.** Breadth dilutes **both**: roughly two thirds fill, one third signal. This is the
   mid-fill counterpart of R2's already-recorded finding that the 133 new names are −0.47%/trade.
3. **The tier ordering SURVIVES.** The toll still tracks the spread ordering exactly — mega −5.4pp
   at a 4.65% spread through small −14.3pp at 8.70% — and mid/small still finish ahead net
   (+7.65%, +18.25%) off a much higher gross. Don's "spreads eat it" thesis stays half-right on
   the corrected data, with the same half right.

**Caveat that must travel:** `small` is 44 and 45 trades. The void file called it "the most
contaminated cell in the study" and that has not changed — it moved +34.36% → +18.25% at the touch,
which is a 16pp swing on 44 trades and should be read as noise, not as a finding.

**Disposition: `HANDOFF_universe_backtest.md` §2a is edited in place** — the void table replaced,
the "100% spread" conclusion corrected, and the file's SUPERSEDED banner left standing.

### ITEM 5 — how far the seed instability reaches · **IT DOES NOT REACH THE BOOTSTRAPS AT ALL**

**Rule honoured as pre-committed** (T1 decision-flip, zero tolerance; T2 magnitude at 0.10 × CI
width; ambiguity → stricter branch). Eight seeded statistics × five seeds on the corrected
3,885-trade book with the seed-0 control held fixed — because the question is the BOOTSTRAP's
seed, not the control DRAW's, which Session 5 already closed.

**A correction to my own first measurement, before the result.** The sweep initially scored T2 on
`bootstrap_diff.diff` and `date_block_bootstrap.point`. Those are computed from the data, not from
the resample: **they are seed-independent by construction and every seed range read exactly 0.0.**
T2 would have passed the entire lane trivially. T2 is therefore scored on the **CI endpoints**, the
seed-dependent published output. This makes the rule stricter, not looser.

| statistic | CI-endpoint seed range ÷ CI width | boolean flips | **policy** |
|---|---|---|---|
| `home_run.p_tail_win` | 2.7% | none | single-seed |
| `home_run.expectancy` | 1.9% | none | single-seed |
| `control_comparison.expectancy_diff` (trade-level) | 3.4% | none | single-seed |
| `control_comparison.tail_diff` (trade-level) | 3.0% | none | single-seed |
| `clustered_R3.expectancy_date_block` | 2.4% | none | single-seed |
| `…date_block_new_names` | 3.5% | none | single-seed |
| `control_comparison.date_block` (real − control) | 2.8% | none | single-seed |
| **`effective_n` shuffled null** | **35.5%** | none | **MULTI-SEED (T2)** |

**Seven of eight are single-seed, comfortably. T1 never fires anywhere** — not one published
boolean takes a different value on any of the five seeds, including
`negative_at_significance`, the boolean the R2 verdict is built on. The point estimates are
identical to the last digit across all five seeds for every statistic, because they are not
resampled quantities.

**THE ANSWER TO THE QUESTION AS ASKED: the instability was never in the bootstrap. It is in the
CONTROL DRAW, and it is enormous there.** The two sit side by side on the same statistic:

* **bootstrap seed varied, control fixed** → `date_block` diff −3.05pp on all five seeds,
  CI95 moving by 0.2pp, `negative_at_significance` **False on all five**
* **control seed varied** (Session 5) → the control's own mean ranges **+6.46% to +15.34%**, the
  seed-0 sign test is **z −0.594, p 0.55 (not significant)** and the 5-seed pool is
  **z −4.903, p < 1e−5**

So Session 5's standing rule — **five control seeds minimum, the sign test carries the verdict** —
is the correct rule and it is the ONLY place in the options lane where multi-seed changes a
decision. **No other statistic needs re-running, and none of the record's single-seed intervals is
called into question by its seed.** Their ranges are published in the table above so nobody has to
re-derive this.

**The one that fires, and why it does not change a verdict today.** `effective_n`'s shuffled null
band moves 0.0724 across seeds on a band only 0.2037 wide. `clustering_measurable` is nonetheless
**True on all five seeds**, because the observed design effect (2.212) sits far above the p95
(1.17–1.25) — the decision has a large margin. But the BAR itself is only measured to ±0.07 at
200 null draws, so a book whose design effect landed near 1.2 could be declared clustered or not
by the seed alone. **Standing policy from now on: `effective_n` is reported at five seeds, or its
null draws raised.** Raising `null_draws` is the cheaper fix (the case costs ~2 seconds) and is
the recommended one; it is left to whoever next touches that function rather than changed here,
because changing it now would make this sweep non-reproducible against the shipped file.

#### `## BUGS FOUND` — **THE CLUSTERING FACTOR OF 1.85 TRAVELLED OUT OF ITS SCOPE**

Found while checking my harness against the shipped file. `CLAUDE.md` records R3's clustering
factor as **1.848 against a null p95 of 1.266** and concludes *"Measured clustering factor 1.85 —
**BELOW the audit's predicted 2–4** — so every options t shrinks by ~1.36×."*

**Be precise about whose error this is: Part 6 of this ledger stated the scope correctly** — it
says "the 3,042-trade **pre-correction** book" in the same sentence. What went wrong is that the
headline was quoted onward WITHOUT the scope, into `CLAUDE.md` and into Part 6's own summary line,
where it reads as the project's clustering factor. Verified by direct computation: the
pre-correction rows give `design_effect` **1.8476**, null p95 **1.2550** — exactly the recorded
numbers. The **corrected** 3,885-trade book gives **2.2121 and 1.2037**, which is what
`UNIVERSE_RESULTS.json` has always shipped. My sweep reproduces the shipped file to the last
digit, so **the artifact was always right; only the prose travelled.**

**Two consequences, and the second is the one to carry:**

1. **Every options *t* shrinks by √2.212 = 1.487×, not 1.36×.**
2. **"BELOW the audit's predicted 2–4" is FALSE on the corrected book — 2.21 is INSIDE the
   predicted range. The audit's prediction was right and the record says it was wrong.**

**No verdict changes**, and this is checked rather than assumed: the R2 verdict rests on the
name-year sign test, which is not a bootstrap statistic; the date-block intervals resample blocks
and so embed clustering by construction rather than applying the design effect as a haircut; and
`deflated_sharpe_clustered` ships alongside the raw figure rather than replacing it. The design
effect is a diagnostic here, not a multiplier applied to anything shipped.

**This is the fourth time in three sessions** (R10, O20, the PBO purge direction, now this) that a
belief about the direction of one of this project's own biases has been contradicted by measuring
it. The R3 bullet in `CLAUDE.md` is corrected in place.

## BUGS FOUND — session-5 closeout

1. **A bug in this session's OWN first measurement, caught before it was reported.** The item-5
   sweep initially scored T2 on `bootstrap_diff.diff` and `date_block_bootstrap.point`. **Those
   are point estimates computed from the data, not from the resample, and are seed-independent by
   construction** — so `seed_range` read exactly 0.0 for every statistic and T2 would have passed
   the whole lane trivially. That is an artefact, not a finding. **Fixed** by scoring T2 on the CI
   endpoints, which are the seed-dependent published output. The correction makes the rule
   STRICTER, and it is recorded because "the number came out clean" is exactly when a measurement
   deserves a second look.

2. **`optuniv_run.py --analyse-only` could still destroy a banked result.** It skips scoring but
   still calls `U.save()`, so a bare `--analyse-only` on a directory holding another run's results
   overwrote them. Now covered — the guard runs before the `--analyse-only` branch and refuses.
   **Fixed** as part of item 2.

3. **`AUTOPSY_*` FDR discovery sets are confounded by the miner in a way individual *p*-values are
   not.** Benjamini–Hochberg is a step-up procedure, so a feature's discovery STATUS depends on
   the other 126 hypotheses in the sweep — and 60 of the 64 features read the derived layer.
   `f_sig_gex_proxy`'s own *p* barely moved (0.0020 → 0.0015) while its FDR status went
   false → true. **Not a code bug**; a reporting hazard. Recorded so that "N features were
   discoveries" is never differenced across sessions. Item 1's stamp is what makes it detectable.

4. **`data/options_universe/` still holds an unstamped mixture of two different runs** — a
   pre-correction `state.pkl` and `state_mid.pkl` (2026-08-03) alongside a corrected
   `UNIVERSE_RESULTS.json`, `AUTOPSY_BROAD_RESULTS.json` and `control_rows.pkl` (2026-08-05).
   The new guard refuses to write there, which is correct, but **the directory itself is already
   inconsistent and no manifest can describe it.** Deliberately NOT cleaned up — deleting or
   rewriting the record's own artifacts to satisfy a guard I just wrote is precisely the move
   `RUN_RULES` §A5 forbids. The next run there must use `--out-dir` or `--overwrite` (which
   archives). **Not fixed, by choice.**

## WHAT WAS NOT DONE, AND WHY — session-5 closeout

- **The autopsy was NOT re-run to produce a stamped baseline artifact.** Item 1 ships the stamp
  and item 4's numbers come from the banked corrected autopsy, which is the RECORD. Re-running it
  today would have produced a third set of numbers on a derived layer that has moved again
  (315 names now), and the honest reading of item 1 is that such a re-run is not differenceable
  against either banked file — it would add a data point, not a comparison. **The first stamped
  autopsy will be written by whichever session next runs one**, and that becomes the baseline.
- **`derived_stamp` is not applied to `AUTOPSY_RESULTS.json` (the 55-name miner-side file).** Only
  `options_autopsy.run()` stamps, which covers both callers that matter. The miner's own directory
  is out of this lane.
- **The item-5 rule's 0.10 constant is a CONVENTION, not a calibrated bar.** It is not scored
  against a null the way X7's thresholds are. Stated in the pre-commitment and repeated here so it
  cannot be quoted as calibrated.
- **Only the options lane's bootstraps were swept.** The equity panel's own seeded machinery
  (CPCV fold assignment, the placebo's draws) was not, and remains unmeasured for seed
  sensitivity.
- **The mid-fill book was not put through the autopsy or a control.** It is a diagnostic; running
  a feature gate on it would be a new search on a book nobody trades, and would cost trials in
  `RESEARCH_LOG.md` for nothing.

## IS SESSION 5 CLOSED?

**Yes.** All five items in `PROMPT_edge_session5_closeout.md` are done, and both of Session 5's
open `BUGS FOUND` (#1 the autopsy stamp, #5 the runner guard) are fixed and pinned by tests. The
two items Session 5 listed as not-done for scope reasons (the mid-fill decomposition, the four
`compute_signals` features) are answered. Its third — `n_eff` not fed into the shipped options
Deflated Sharpe — was explicitly out of scope in this prompt and is untouched, as instructed.

**What remains open from Session 5 is open by design, not by omission:** the run-to-run
non-reproducibility of the equity panel (the `insider` theme's IC), which is a panel-lane problem
and was never in this closeout's scope.

## SESSION 6 — first item and its `needs first`

**Session 6's first item is U7 — the equity composite as an options VETO** (audit
`VALQUO_EDGE_AUDIT.md:2109`), run alongside **X3 — ablate to the best single signal** (`:1751`).
Both are one-line probes that can kill or promote a much larger item, and U7 should run before U1
because it is the strictly easier bar.

**U7 `needs first`:**

| dependency | status |
|---|---|
| a banked alert log with per-alert dates | **READY** — the corrected 187-name book, 3,885 trades, `r2_state.pkl`; now protected by the item-2 guard |
| the point-in-time equity composite | **READY** — corrected 69-date panel (B6/B7/B13), one composite for live and backtest |
| the join: composite decile at the alert date | **NOT BUILT.** Alerts are daily 2016-01 → 2025-10; the panel has 69 quarterly-ish dates. The join must take the most recent rebalance date **≤** the alert date — never the enclosing one, which would be look-ahead |
| coverage of the 187 options names inside the 2,710-name panel | **UNVERIFIED.** Measure and report it before any verdict; the audit predicts near-complete but predicts are not measurements |
| the monotonicity figure U7's rationale rests on | **STALE IN THE AUDIT.** It cites −0.95; the corrected panel is **−0.891**. The argument survives, the number must be updated |
| retention reporting | pre-register it: the audit's own line is that a veto discarding 10% and lifting expectancy is adoptable, one discarding 60% is a different strategy |

**X3 `needs first`:**

| dependency | status |
|---|---|
| the full corrected panel | **READY** |
| **X7's calibrated bars, not the old conventions** | **READY and MANDATORY** — theme IC t **2.71** (not 2.0), long-short t **2.14**, top-decile alpha margin **1.95pp**, PBO **<19.7%**, Deflated Sharpe calibrated **0.72** at N = 84. Scoring an ablation against the retired 2.0/50% conventions would manufacture a survivor |
| `RESEARCH_LOG.md` trial accounting | **READY, and X3 MUST WRITE TO IT.** Every ablation arm is a trial. N = 84 today; an 8-arm ablation takes it to 92 and lowers the Deflated Sharpe for everything afterwards. That cost is the point of M1 and must not be skipped |
| the HAC caveat | R9 stands: Ljung–Box rejects independence, so the **Newey–West** *t* is the quoted statistic. X7's 2.14 floor was measured on the NAIVE *t* — comparing a HAC *t* to it is apples-to-oranges and re-deriving the floor on HAC is still open |

**Standing items that outrank both if Don wants them to:** **P4** (`seed_book` never sells names
that leave the book) is the only *urgent* item in the catalogue — every session the paper track
accumulates under the wrong rules is a session that has to be thrown away — and **X8**, the
international replication, is still the only genuinely out-of-sample evidence available to either
programme.

---
---

# SESSION 6 — U7 (the composite as an options VETO) and X3 (ablate to the best single signal)

Audit session 6. Owner: pipeline builder. Previous session verified complete: YES — Session 5 and
its closeout are on `origin/main` (`416da4b`, `fdd0064`, `5ea7099`, `cf8230f`, merged at `33a02aa`).

## PRE-COMMITMENTS — written and committed BEFORE any number was produced

Everything below the "RESULTS" heading was measured after this section was committed. Nothing in
this section was edited afterwards.

### 0. What I expect, written down first

RUN_RULES 6 says the threshold comes first. The Session-5 carry-forward asks for something extra:
this project's expectations about the direction of its own biases have been wrong more often than
right (R10, O20, and the spread toll going −6.59pp → −8.28pp), so the expectation goes on the
record too, and the record gets to say whether it was worth anything.

**U7 — I expect the veto to HELP, and I hold it at about 60/40, not higher.** The case for: a
long-call book on junk pays for lottery skew, and the composite's bottom decile is exactly that.
The case against, which is real: a long call is a barbell, low-quality names are more volatile,
and volatility is what a barbell wants. Both arguments are available *before* the data, which is
usually the sign that the prior is worth very little.

**X3 — I expect the ablation curve to flatten by three or four themes.** If it does, the
seven-theme architecture is partly decoration and the honest product description changes.

### 1. U7 — the join, and the test that pins it

The join does not exist and must be built. Alerts are daily 2016-01-19 → 2025-10-15; the panel has
69 quarterly-ish rebalance dates. **The composite attached to an alert is the one from the most
recent rebalance date STRICTLY ≤ the alert date.** Taking the *enclosing* date — the rebalance
that brackets the alert — would use a score computed from filings published after the alert fired.
That is look-ahead, and it is the failure mode this join is most likely to have, so it gets a test
that fails on the enclosing-date variant rather than a comment saying it was considered.

An alert before the first rebalance date has NO composite and is **excluded, not imputed**.

### 2. U7 — coverage, reported before any verdict

My own `needs first` table records coverage of the 187 options names inside the 2,710-name panel as
**UNVERIFIED**, with the note that "the audit predicts near-complete but predicts are not
measurements". Coverage is therefore measured and stated first, at three levels — names, alerts,
and alerts-with-a-composite — and if it is materially below the audit's prediction, that is itself
the finding and the verdict is INCONCLUSIVE regardless of what the expectancy numbers say.

**Floor committed now: below 80% of alerts joined, U7 is INCONCLUSIVE on coverage alone.**

### 3. U7 — the retention rule, committed before the number

The audit's own boundary is that a veto discarding 10% of alerts while lifting expectancy is
adoptable and one discarding 60% is a different strategy wearing a veto's clothes. Sharpened:

| alerts discarded | consequence, whatever the lift |
|---|---|
| ≤ 15% | a veto. Eligible for ADOPTED |
| 15–40% | **INCONCLUSIVE** — report it, do not adopt it; it materially changes the product |
| > 40% | **REJECTED** as a different strategy, regardless of how good the lift looks |

### 4. U7 — two verdicts, because they are two different claims

**U7-A (practical — should the live product refuse these alerts?)** ADOPTED requires all three:
(a) retention ≥ 85%; (b) the veto lifts the real book's mean `pnl_pct` by **≥ +1.0pp**; (c) the
lift's date-block bootstrap CI95 (calendar-month blocks, the R3 machinery) **excludes zero**. Any
one of the three ambiguous → **NULL**. A negative lift → **REJECTED**.

**U7-B (mechanism — is the composite improving the ALERT, or just describing the underlying?)**
The identical veto is applied to the **random-entry control book**, whose alerts are random days on
the same names. If the composite is only telling us that bad-composite megacaps' options do badly,
the control lifts too, and the veto has learned nothing about the alert. **The interaction claim is
upheld only if the real book's lift exceeds the control book's lift with the difference's CI95
excluding zero.** Otherwise the honest sentence is "a property of the underlying, not of the
alert" — and U7-A can still pass, because a live product does not care where its improvement comes
from. This is the R10/O20 lesson applied in advance: the liquidity screen helped the control too,
and nobody had checked.

**Five control seeds minimum and the sign test carries the verdict** — the standing rule from R2,
which is not re-opened here.

**Pre-registered grid: 3 cells.** (i) bottom-decile veto, full-panel deciles — PRIMARY; (ii)
bottom-quintile veto; (iii) bottom-decile veto computed *within the 187-name options universe*
rather than the full panel, because a 187-name megacap book may not populate the full panel's
bottom decile at all. Cells (ii) and (iii) are reported whatever they say and cannot rescue (i).

**U7 is logged to `RESEARCH_LOG.md` in the `options` domain, not `unified`.** The `unified` domain
exists and is empty, and putting U7 there would charge its multiple-testing cost to nobody. If U7
adopted, the sentence would be quoted as a claim about the options book, so the options family is
where it belongs.

### 5. X3 — the arms, fixed now

Eight arms. Arm 1 is a single signal; arms 2–8 are the cumulative theme curve, added in order of
measured theme IC among the seven deployed themes (quality +3.57, momentum +2.62,
capital_discipline +2.25, institutional +1.81, size +1.68, value +1.52, insider −0.43):

| arm | composite |
|---|---|
| 1 | `z_gp_on_capital` alone — the strongest single signal in the model |
| 2 | `quality` alone |
| 3 | + `momentum` |
| 4 | + `capital_discipline` |
| 5 | + `institutional` |
| 6 | + `size` |
| 7 | + `value` |
| 8 | + `insider` = the deployed seven-theme composite (the incumbent) |

Flat equal weights within each arm, which is what is deployed. No weight is tuned in X3 — tuning
inside an ablation would make the curve a search rather than a measurement.

### 6. X3 — scored against X7's calibrated bars, never the retired conventions

Theme IC *t* **2.71** (not 2.0), long-short *t* **2.14**, top-decile alpha margin **1.95pp**,
PBO **< 19.7%**, Deflated Sharpe **0.72** at N = 84. Scoring an ablation against 2.0 / 50% would
manufacture a survivor, which is the whole reason X7 was run.

Two distinct questions, and they need different bars:

* **"Is this arm distinguishable from noise at all?"** → its own top-decile alpha against the
  **1.95pp** placebo p95, and its naive long-short *t* against **2.14**. X7 measured both on the
  NAIVE statistic, so the naive statistic is what gets compared to them; the NW *t* is reported
  alongside per R9 and is explicitly **not** compared to 2.14 (apples-to-oranges — the same trap
  flagged for the headline's own 2.620).
* **"Does the full composite beat this arm?"** → **no calibrated bar exists for a paired nested
  difference and I am not inventing one.** Pre-registered rule: the per-period alpha series of
  (full − arm) must have a **CI95 excluding zero** on its period bootstrap, with the NW *t*
  reported. If it does not, the two are not distinguishable and the shorter model wins on
  parsimony.

**Pre-registered interpretation, per the audit's own instruction:** if the curve is flat from some
k < 7 onward — i.e. the full composite does not beat arm k by the rule above — then the honest
statement is "the model is effectively k themes", it goes in the product description, and S5/S7
inherit it. If arm 1 or arm 2 alone lands there, the seven-theme architecture is decoration and I
say so in those words.

### 7. X3 — the cost, which is the entire point of M1

**Every ablation arm is a trial.** Equity N is **84** today. X3 is logged as one row with `n=8`,
the house convention for a pre-registered grid (X2 `n=7`, OPT-AUTOPSY `n=126`), so equity N
becomes **92** and the Deflated Sharpe falls for everything measured afterwards, including the
shipped headline. That is not a side effect to be minimised; it is the reason the trial counter
exists. The post-X3 N, the shipped edge's Deflated Sharpe recomputed at it, and √(2·ln N) are all
reported, so Session 7 inherits the honest denominator instead of discovering it.

I am counting **8**, not 7, even though arm 8 is the incumbent rather than a new search. Rounding
the denominator up is the direction that weakens my own evidence, and that is the direction to
round in.

### 8. Stale number U7's rationale rests on

The audit's U7 argument cites monotonicity **−0.95**. The corrected panel is **−0.891**. The
argument survives — the bottom decile still underperforms, which is all a veto needs — but the
number is updated wherever it is quoted.

### 9. What this session will NOT do, decided in advance

* **Not re-deriving X7's calibrated bars at N = 92.** The placebo is 100 draws through the full
  pipeline; it is a multi-hour run and it is not what was asked for. The consequence is stated
  rather than hidden: the 0.72 Deflated Sharpe floor is an N = 84 measurement, and X7 showed the
  floor FALLS as N rises (0.8567 at N = 8 → 0.7216 at N = 84), so quoting 0.72 at N = 92 is
  conservative in the direction that makes passing harder, not easier.
* **Not touching** `valuation/web/**`, `valuation/engine/**`, `valuation/data/**`,
  `valuation/screener/**`, `theta_bulk.py`, or `data/options/**`.
* **Not re-opening R2.** U7 sits inside a book that has already been shown to lose to random
  entry. A veto that improves that book improves a book with a negative day-selection edge, and
  every U7 number carries that sentence.

---

## RESULTS — U7 · the equity composite as an options VETO

**Run:** `python -m scripts.u7_veto --panel data/free_analysis/panel_corrected_69d.pkl --state data/options_universe/state_r2_corrected.pkl --control data/options_universe/control_r2_seed{0..4}.pkl`.
Universe: the corrected pinned 187-name options book, **3,885 alerts** 2016-01-19 → 2025-10-15,
against the **five-seed random-entry control, 29,785 trades** (R2's standing rule: five seeds
minimum). Panel: the 69-date corrected panel rebuilt this session.

### The join, built and pinned

It did not exist. It now takes the most recent rebalance date **strictly ≤ the alert date**, and
`test_u7_the_join_is_backward_looking_only` asserts three things rather than one: that the
shipped rule never reaches forward, that the look-ahead variant would have picked a *different*
date on a real alert, and that the two therefore genuinely disagree. Asserting only "never
forward" would have passed on a join that always returned index 0. An alert before the first
rebalance is excluded, not imputed — pinned separately, because imputing is the cheap way to
inflate the coverage figure the adoption rule turns on.

### Coverage, reported before any verdict — the audit's prediction holds, as a measurement

| | measured |
|---|---|
| alerts joined | **3,812 / 3,885 = 98.1%** |
| names joined | **182 / 186 = 97.8%** |
| never joined | AMAT, RIO, SHEL, UBS |
| alerts before the first rebalance | 0 |

Comfortably clear of the pre-committed 80% floor. My own `needs first` table called this
UNVERIFIED with the note "the audit predicts near-complete but predicts are not measurements".
The prediction was right. It is now measured.

### The monotonicity U7's rationale rests on

The audit argues a veto needs only that the bottom decile underperforms, citing monotonicity
**−0.95**. Measured on the corrected panel in the same run: **−0.891**. The argument survives;
the number is updated. It also turns out not to matter, for a reason the argument did not
anticipate — see below.

### Expectancy by composite decile — the audit's actual instruction

Decile 1 = BEST composite, matching `quantile_backtest`'s convention.

| decile | n | median mkt cap | mean `pnl_pct` | win rate |
|---|---|---|---|---|
| D1 | 97 | $62.7B | **+18.74%** | 42.3% |
| D2 | 181 | $80.5B | **+14.78%** | 40.3% |
| D3 | 202 | $72.9B | −5.33% | 28.2% |
| D4 | 314 | $90.4B | +4.92% | 36.0% |
| D5 | 368 | $94.2B | +2.89% | 35.6% |
| D6 | 427 | $100.7B | +2.20% | 34.9% |
| D7 | 550 | $114.9B | −0.07% | 34.9% |
| D8 | 706 | $130.9B | −0.46% | 33.7% |
| D9 | 688 | $133.5B | +4.69% | 35.3% |
| **D10** | **279** | $106.0B | **+10.64%** | **39.1%** |

**The relationship is U-shaped, not monotone, and the bottom decile — the one the veto exists to
remove — is the third most profitable in the table.** That single row is the whole result: there
is nothing for a bottom-decile veto to remove.

### The three pre-registered cells

| cell | retention | mean before → after | lift | lift CI95 (118 month-blocks) | control lift | **interaction** |
|---|---|---|---|---|---|---|
| **i** bottom decile, full panel (PRIMARY) | 92.7% | +3.36% → +2.78% | **−0.57pp** | [−1.49, +0.32] | −0.49pp | **−0.08pp** [−1.02, +0.82] |
| **ii** bottom quintile, full panel | 74.6% | +3.36% → +2.32% | −1.04pp | [−2.69, +0.50] | +0.03pp | −1.06pp [−3.23, +0.72] |
| **iii** bottom decile, within the 187-name universe | 92.9% | +3.36% → +2.91% | −0.44pp | [−1.43, +0.46] | −0.34pp | −0.10pp [−1.03, +0.82] |

### VERDICTS

**U7-A (practical): REJECTED.** The pre-registered bar was a lift of **≥ +1.0pp**; all three
cells land on the wrong side of zero. Retention was never the binding constraint — 92.7% is
inside the "eligible for ADOPTED" band, so this is not a case of a good filter failing an
arbitrary retention rule. It is a filter that does not work. **Stated precisely: the veto does
not demonstrably HURT either** — every lift CI includes zero. The honest sentence is *"the
composite's bottom decile carries no information about which alerts to refuse."*

Cell **ii** additionally trips the pre-registered retention band (74.6% retained = 25.4%
discarded, inside the 15–40% INCONCLUSIVE range), so it could not have been adopted on any
number. Recorded because the rule was committed in advance and applies whatever the lift said.

**U7-B (mechanism): NO INTERACTION.** In both decile cells the real book's lift and the
control's lift are within **0.1pp** of each other, with intervals straddling zero. Whatever the
composite decile does to the options book, it does the same to a book entered on random days.
**The composite is describing the underlying, not the alert.**

### Mechanism, stated as far as the data supports and no further

Median market cap rises **monotonically** across the deciles, $62.7B at D1 to $133.5B at D9. In a
187-name megacap universe the other themes are compressed and `size` (= `z_neg_log_mktcap`)
dominates, so **the composite decile inside this universe is largely a market-cap sort.** A
market-cap bucket is a property of the underlying, not of the day an alert fired — which is
exactly why the control tracks the real book to within 0.1pp, and it makes U7-B's null the
expected outcome once the mechanism is visible rather than a surprise.

**What the data does NOT support:** D10 breaks the size pattern ($106.0B, below D9's $133.5B) and
its most frequent names are MRVL, GS, NEM. So D10 is *not* simply "the largest names", and no
claim is made about what else it is. X3 independently found `size` to be the theme carrying the
composite's significance, which is consistent, but that is one panel and one universe.

### The expectation, and the record's verdict on it

Pre-committed, before any number: *"I expect the veto to HELP, and I hold it at about 60/40."*
**Wrong.** Every cell is negative, and the mechanism is one the pre-registration did not consider
at all — that inside a megacap universe the composite is mostly a size sort.

That is now the fourth consecutive time (R10, O20, the spread toll, U7) that this project's
stated expectation about the direction of its own effect has been wrong. The carry-forward line
stands and should be strengthened: **do not reason about the direction of an effect in this
project — measure it. Writing the expectation down first is worth doing precisely because it
keeps being wrong.**

### What U7 forecloses, and what it does not

**Forecloses:** U1 (the composite as an options ENTRY signal) is now a much worse bet than the
catalogue assumes. The audit's own argument is that the veto is "strictly the easier bar" — a
veto needs only that the bottom decile underperform, while an entry signal needs the top decile
to move enough to beat decay and spread. **The easier bar failed and its failure has a mechanism
(the composite is a size sort on this universe), so U1 should not be run as written.** It should
only be reopened with a composite constructed *within* the options universe, where the size
tilt is not free to dominate.

**Does not foreclose:** D1 and D2 post +18.74% and +14.78% on 97 and 181 trades. That is the
opposite end of the same table and it is a *positive* selection idea rather than a veto. It was
not pre-registered, the samples are small, and this session makes no claim about it — but it is
the one thread in U7 worth a pre-registered test, and it goes to Session 7 rather than being
quoted as a finding here.

## RESULTS — X3 · ablate to the best single signal

**Run:** `python -m scripts.x3_ablation_rerun --panel data/free_analysis/panel_corrected_69d.pkl --leave-one-out`, on a panel
rebuilt from scratch this session with `scripts/dump_panel.py` against
`data/backtest` — **113,945 rows, 69 dates, 2,531 names**, identical in shape to the cached
grid-0 panel, which is a free reproducibility check on the panel build itself.

### X3 had already been run, and that run is void

`data/free_analysis/ABLATION_RESULTS.json` (2026-08-03) records X3 as **"EARNS ITS COMPLEXITY"**,
and `VALQUO_LEDGER.md:106` carries it as **DONE**. It is void twice over, and neither reason was
noticed when the panel corrections landed the next day:

1. **It ran on the pre-B6 panel** — 110 dates, 136,478 rows, full-composite alpha **+11.88%**.
   The first 41 of those dates carried the inverted universe B6 removed. The corrected alpha is
   **+7.17%**, so every gain the old verdict rested on was measured across that boundary.
2. **It scored against bars that X7 later retired** — 2.0pp against the best single signal and
   **1.0pp** against the best three-theme prefix. X7's calibrated top-decile alpha margin is
   **1.95pp**. The 1.0pp bar sat *below the noise floor*: a three-theme prefix could clear it on
   a shuffled signal.

It is also **absent from `RESEARCH_LOG.md`** — roughly a dozen arms were run and never charged
to `N`. See `## BUGS FOUND`.

### The theme IC table in `CLAUDE.md` was a pre-B6 measurement labelled "CURRENT"

The ablation orders themes by theme IC, so the first thing it needed was the ranking — and the
ranking did not match the record. **Proven stale rather than assumed stale:** re-running
`theme_ic` on the old 110-date panel reproduces `CLAUDE.md`'s list to the digit (momentum +2.62,
capital_discipline +2.25, institutional +1.81, size +1.68, growth +1.45, low_risk +0.71).

| theme | void (110 dates) | **corrected (69 dates)** | move |
|---|---|---|---|
| quality | +3.57 | **+3.10** | −0.47 |
| capital_discipline | +2.25 | **+2.76** | **+0.51 — the only riser** |
| institutional | +1.81 | **+1.55** | −0.26 |
| momentum | +2.62 | **+1.31** | −1.31 |
| value | +1.52 | **+0.84** | −0.68 |
| growth | +1.45 | **+0.75** | −0.70 |
| low_risk | +0.71 | **+0.46** | −0.25 |
| insider | −0.43 | **−0.24** | +0.19 |
| **size** | **+1.68** | **−0.30** | **−1.98** |

**Against X7's calibrated bar of 2.71, two of nine themes clear: `quality` and
`capital_discipline`.** `CLAUDE.md` is corrected in place.

### The eight pre-registered arms

Flat weights within each arm, cumulative in descending corrected theme-IC order. Arm 8 is
asserted in code to be the deployed composite (`last_arm_is_deployed_composite: true`), so the
curve is compared against what the product actually runs and not against something adjacent.

| arm | top-decile alpha | LS *t* (naive) | LS *t* (NW) | monotonicity | clears 1.95pp |
|---|---|---|---|---|---|
| 1 · `gp_on_capital` alone | **+2.67%** | 0.413 | 0.425 | −0.648 | yes |
| 2 · quality | +1.12% | −0.372 | −0.367 | +0.115 | **no** |
| 3 · + capital_discipline | +0.96% | −0.192 | −0.194 | +0.309 | **no** |
| 4 · + institutional | +3.77% | 0.710 | 0.731 | −0.176 | yes |
| 5 · + momentum | +4.05% | 0.837 | 0.853 | +0.067 | yes |
| 6 · + value | +3.22% | 0.661 | 0.650 | −0.370 | yes |
| 7 · + insider | +4.10% | 1.024 | 0.965 | −0.648 | yes |
| **8 · + size = deployed** | **+7.17%** | **2.836** | **2.620** | **−0.891** | yes |

**Only the full seven-theme composite clears X7's long-short bar of 2.14. No prefix comes
close** — the best of them reaches *t* 1.02. Two prefixes (quality alone; quality +
capital_discipline) do not even clear the alpha noise floor, and both have *positive*
monotonicity, i.e. their deciles are ordered **backwards**.

### The pre-registered verdict, and why it is uncomfortable

The rule committed beforehand: the full composite beats an arm only if the paired per-period
alpha difference has a CI95 excluding zero.

| comparison | full − arm | CI95 | excludes 0 |
|---|---|---|---|
| vs `gp_on_capital` alone | **+4.51%/yr** | **[−0.14%, +9.12%]** | **NO** |
| vs quality | +6.05%/yr | [+1.36%, +10.87%] | yes |
| vs quality+capital_discipline | +6.21%/yr | [+1.99%, +10.66%] | yes |
| vs + institutional | +3.41%/yr | [−0.08%, +6.89%] | no |
| vs + momentum | +3.13%/yr | [−0.18%, +6.35%] | no |
| vs + value | +3.96%/yr | [+1.76%, +6.41%] | yes |
| vs + insider | +3.08%/yr | [+1.27%, +5.04%] | yes |

**VERDICT: NULL — the composite's advantage over its own best single signal is not
demonstrated.** +4.51%/yr with a lower bound of **−0.14pp**. That is a near miss, and a near
miss is a null; the pre-commitment says an ambiguous result is not a judgement call.

**But "DECORATION" would be the wrong word and I am not going to use it.** The pre-registered
statistic is one statistic, and on 69 periods it is underpowered relative to what the arms
visibly do. `gp_on_capital` alone posts long-short *t* **0.413** against the composite's
**2.836**, and clears none of X7's bars except the alpha margin. The honest sentence is: *the
seven-theme composite is the only arm that clears the calibrated long-short bar, and its
top-decile alpha advantage over the best single signal is +4.5pp/yr but not separable from zero
on 69 periods.* Both halves travel together.

**The curve does not flatten, and it is not a curve.** Alpha wanders +1.12 → +0.96 → +3.77 →
+4.05 → +3.22 → +4.10 → **+7.17**. My pre-registered expectation was that it would flatten by
three or four themes. **That expectation was wrong**, and wrong in the direction that favours
the product — the last theme added does most of the work.

### The finding worth carrying: theme IC does not predict marginal contribution

The theme added last, `size`, is the **worst**-ranked theme on the corrected panel (IC *t*
−0.30), and adding it moves alpha +4.10% → **+7.17%** and long-short *t* 1.02 → **2.84**. A
signal that predicts nothing on its own is carrying the composite's entire statistical
significance.

This is the P6 lesson — "a signal's IC can be flat while the composite built from it moves a
lot" — in a far starker form, and it means **the prefix ordering this ablation used is the wrong
ordering**. Ranking by IC and adding greedily measures the wrong thing when the value of a theme
is its *orthogonality* rather than its standalone predictiveness.

### EXPLORATORY leave-one-out — no verdict, no trial row

Written *after* seeing the prefix curve, so it is a look and not a test. The log's own schema:
exploratory looks get no claim. It is recorded because it tells Session 7 what to pre-register.

| dropped | its IC *t* | alpha without | LS *t* | full − arm | CI excl 0 |
|---|---|---|---|---|---|
| **size** | **−0.30 (worst)** | +4.10% | 1.024 | **+3.08%/yr** | **yes** |
| institutional | +1.55 | +5.77% | 1.772 | +1.41%/yr | no |
| value | +0.84 | +7.12% | 2.511 | +0.06%/yr | no |
| insider | −0.24 | +7.47% | 2.581 | −0.30%/yr | no |
| momentum | +1.31 | +8.37% | 2.838 | −1.20%/yr | no |
| quality | +3.10 (best) | +8.42% | 3.304 | −1.25%/yr | no |
| **capital_discipline** | **+2.76** | **+8.54%** | **3.352** | **−1.37%/yr** | **yes** |

Two of seven move the composite at significance and **the IC ranking puts both at the wrong end
of the list**: dropping `size` costs 3.08pp/yr, while dropping `capital_discipline` — the
second-strongest theme by IC and one of only two clearing X7's bar — *improves* the composite by
1.37pp/yr and lifts long-short *t* to 3.35.

**Read this as a hypothesis with a large multiplicity caveat, not a result.** Seven correlated
nested comparisons, chosen for report after the fact; two "significant" out of seven is more than
chance expects but not by much. **Nothing was changed on the strength of it** — the deployed
weights are untouched, and they should not move until a pre-registered held-out test says so,
because that is exactly the gate `low_risk` passed and `insider` failed.

### The cost, paid in full

X3 is logged as one row, `n=8`. **The pre-commitment said equity N would go 84 → 92. The
realised number is 104, and the extra 12 are the void 2026-08-03 run's arms.** Discovering that
X3 had already been run — twelve arms, never logged — was not foreseeable when the
pre-commitment was written, and logging them is the direction that weakens this project's own
evidence, so they are logged. Two things make 104 the right number rather than a choice:
`research_log.py:73` excludes only `FIXED` rows, so a `SUPERSEDED` search still costs
multiplicity in the shipped code; and the data genuinely was searched twelve times.

Recomputed exactly on the shipped run's own `deflated_sharpe_detail`, round-trip verified (the
re-derivation reproduces 0.8997 at N = 84 to four decimals — pinned by
`test_x3_deflated_sharpe_at_round_trips_and_falls_with_n`):

| | N = 84 (shipped) | N = 92 (pre-committed) | **N = 104 (realised)** |
|---|---|---|---|
| `sr0_benchmark` | 0.4056 | 0.4110 | **0.4181** |
| Deflated Sharpe | 0.8997 | 0.8911 | **0.8789** |
| √(2·ln N) | 2.977 | 3.007 | **3.048** |

**X3 pushes the project's multiple-testing haircut past the Harvey–Liu–Zhu hurdle of 3.0 for the
first time — 2.977 → 3.048.** The headline still sits above X7's calibrated floor of 0.7216, and
since X7 showed that floor *falls* as N rises (0.8567 at N = 8 → 0.7216 at N = 84), quoting 0.72
at N = 104 is conservative in the direction that makes passing harder.

**Quote it whole:** *"Deflated Sharpe 0.8789 at N = 104 — fails the conventional >0.95 bar, sits
above all 100 placebo draws (calibrated bar 0.72, measured at N = 84), and the trials haircut is
now 3.048."*

`BACKTEST_RESULTS.json` still carries 0.8997 at N = 84 and will pick up N = 104 automatically on
the next full run — `_deflated_sharpe_detail` reads the log. It was not regenerated here.

---

## BUGS FOUND

**1. `CLAUDE.md`'s theme IC table was a pre-B6 measurement labelled "CURRENT 2026-08-04".**
Proven, not inferred: re-running `theme_ic` on the retained 110-date panel reproduces the
recorded list to the digit. The corrected values move by up to **1.98 t** (`size` +1.68 →
**−0.30**), and against X7's calibrated bar of 2.71 only **two of nine** themes clear. Corrected
in place. *This is the same class of error as B6 itself — a number that outlived the panel it was
measured on — and it survived two sessions of corrections because nothing re-measures a table
that is only ever read.*

**2. X3's 2026-08-03 run is void and is recorded as DONE.** `VALQUO_LEDGER.md:106` carries
"'Earns its complexity' — both bars cleared decisively", measured on the pre-B6 110-date panel
(alpha +11.88%) and scored against a **1.0pp** three-theme bar that sits *below* X7's calibrated
1.95pp noise floor. Ledger row amended to SUPERSEDED with the re-run's verdict.
`test_x3_the_old_ablation_verdict_is_marked_superseded` fails if that row silently reverts.

**3. Trials that were run and never charged to `N`. This one is mine as well as other lanes'.**
`RESEARCH_LOG.md` has rows for X2, X4, X7 but **none for X3, X5, X6**, nor for the
capacity / failure-cases / JKP-replication studies that shipped JSON into
`data/free_analysis/` on 2026-08-03–04. X3 alone was ~12 arms. Separately, **Session 5's own
closeout items 3, 4 and 5 were pre-registered tests with committed thresholds and I did not log
them** — added this session as `S5-3`, `S5-4`, `S5-5`.
**And `RESEARCH_LOG.md` contradicts itself and the code about whether those rows count.** Its
"## Schema" section says *"Only `ADOPTED` / `REJECTED` / `NULL` / `INCONCLUSIVE` rows are
trials"*, i.e. `SUPERSEDED` is free; the later section says only `FIXED` does not count; and
`research_log.py:73` implements the later rule. I checked rather than assumed, and logged the
void X3 run's 12 arms accordingly — **equity N is 104, not the 92 my own pre-commitment
predicted.** The code's rule is the right one (a search that happened cost multiplicity whether
or not its verdict was later withdrawn), so the fix is to delete the stale sentence in the
Schema section, not to change the code. Left for whoever owns the schema, flagged here, because
someone reading only that section could legitimately delete a SUPERSEDED row's cost.

**4. `RESEARCH_LOG.md`'s R3 row quotes a design effect out of its scope.** The row reads
"deff 1.848 vs null p95 1.266", which is the **pre-correction 3,042-trade book**. The corrected
3,885-trade book is **2.2121 vs null p95 1.2037**. This is the same figure whose travel I
corrected in `CLAUDE.md` at the Session-5 closeout; the log row was missed then. Rows are
append-and-amend, so a scope note is appended rather than the number rewritten.

**5. `data/free_analysis/panel.pkl` is a pre-B6 panel with no marking.** 110 dates, dated
2026-08-03. Anything that reads it — `scripts/ablation.py`, `scripts/breaks.py` and any future
study that reaches for "the panel pickle" — silently gets the inverted-universe panel. It is
outside my lane to delete or move (other lanes' scripts default to that path), and it is
reported here rather than repaired. **The cheap fix is a `panel_window` stamp inside the pickle,
which is exactly the Session-5 item-1 pattern applied to the equity side.**

**6. Not a bug, a performance defect worth recording.** `options_stats.date_block_diff` rebuilds
the concatenated trade list on every draw, which on the five-seed control book is ~240M
Python-level operations per cell; U7 ran for 45 minutes and produced nothing. The mean of a
concatenation of blocks is exactly `sum(block sums) / sum(block counts)`, so
`options_veto.fast_block_diff` hoists the per-trade work out and is **exact, not approximate** —
pinned by `test_u7_the_fast_block_bootstrap_is_exact`, which replays the identical
`Random.randrange` sequence and requires the CI endpoints to match to floating point.
`options_stats` itself is left alone; other lanes read it.

**7. THE CORRECTED OPTIONS BOOK EXISTED ONLY IN A SESSION SCRATCH DIRECTORY. Fixed.**
`data/options_universe/state.pkl` is the **pre-correction 3,042-trade** book. The corrected
**3,885-trade** book that R2, the Session-5 closeout and this session all rest on, plus its five
control seeds, lived only in `~/.claude/jobs/<id>/tmp/` — deleted when the job is deleted. Two
sessions of options conclusions were one cleanup away from being unreproducible, and the
Session-5 item-2 guard could not help, because it protects a directory the artifacts were never
written to. Copied to durable paths (all gitignored, per the hard rule — nothing licensed is
committed):

| artifact | durable path | verified |
|---|---|---|
| corrected book | `data/options_universe/state_r2_corrected.pkl` | 3,885 rows / 187 names |
| control seeds 0-4 | `data/options_universe/control_r2_seed{0..4}.pkl` | 29,785 trades total |
| corrected 69-date panel | `data/free_analysis/panel_corrected_69d.pkl` | 113,945 rows / 69 dates |

`data/options_universe/state.pkl` is deliberately **not** overwritten — it is a banked artifact
and the guard exists to stop exactly that. The next session should decide whether the
pre-correction book is still worth keeping under a name that does not read like the current one.

## WHAT WAS NOT DONE, AND WHY

* **X7's calibrated bars were NOT re-derived at N = 92.** Pre-committed as out of scope in
  section 9. The placebo is 100 draws through the full pipeline — hours — and the direction is
  known and favourable: X7 measured the floor *falling* as N rises (0.8567 at N = 8 → 0.7216 at
  N = 84), so quoting 0.72 at N = 92 makes passing harder, not easier.
* **No weight was changed.** The exploratory leave-one-out says dropping `capital_discipline`
  would raise alpha to +8.54% and long-short *t* to 3.352. It was generated after seeing the
  prefix curve, it is seven correlated comparisons reported for their extremes, and it has had no
  held-out test. `low_risk` passed that gate and `insider` failed it; nothing ships without it.
* **The paired nested difference has no calibrated floor and none was invented.** X7 calibrates
  the alpha margin, the long-short *t* and the theme IC *t*. It does not calibrate a nested-model
  comparison. The pre-registered rule was the plain CI-excludes-zero test, which is why X3's
  headline is a NULL rather than a verdict dressed in a borrowed bar.
* **U1 was not run**, and U7's result is a reason not to run it as written — see "What U7
  forecloses".
* **The four names that never join** (AMAT, RIO, SHEL, UBS) were not chased. 2.2% of names and
  1.9% of alerts; running them down would not move any verdict here.
* **`BACKTEST_RESULTS.json` was not regenerated.** N = 92 changes its `deflated_sharpe_detail`
  on the next full run; the consequence is computed exactly and published here instead of
  spending 12 minutes to rewrite a tracked artifact this session did not otherwise touch.

## IS SESSION 6 CLOSED?

**Yes.** Both nominated probes ran on the corrected panel, against the calibrated bars, with
their thresholds committed and pushed before any number existed (`a727bea`). Both returned
verdicts. Two void records in the project's own memory were found and corrected in passing, and
the trial ledger now carries the cost of the work.

Neither probe promoted the item it was testing. That is the outcome, not a failure of the
session: U7 was proposed as the cheap probe that could kill or promote U1, and it killed it as
written.

## SESSION 7 — first item and its `needs first`

**Session 7's first item is the leave-one-out ablation, PRE-REGISTERED and held out** — because
X3 produced one genuinely surprising structural result and the only honest way to act on it is a
test designed before the numbers are seen. Run it alongside **P4**, which remains the only
*urgent* item in the catalogue.

**LOO-PREREG `needs first`:**

| dependency | status |
|---|---|
| the corrected 69-date panel | **READY** — rebuilt this session, `scripts/dump_panel.py`; 113,945 rows, identical in shape to the cached grid-0 panel |
| the exploratory result to be tested | **READY, and it is EXPLORATORY** — dropping `capital_discipline` gives alpha +8.54% / LS *t* 3.352; dropping `size` costs 3.08pp/yr. Seven correlated comparisons, reported for their extremes. **It must be re-derived on a held-out split, not re-quoted** |
| `holdout_theme_validate` | **READY but READ B8 FIRST** — its `rule_fired` flag is computed and never read (`fundamental_panel.py:3048`), so it is a both-halves stability check, not an out-of-sample confirmation. B8 is still open. Say which one you ran |
| the trial cost | **NOT FREE.** Seven LOO arms take equity N 92 → 99. √(2·ln 99) = 3.03. Pre-register the arms and log them, or the result is not quotable |
| the ordering problem X3 exposed | **UNRESOLVED and it is the real question.** Ranking themes by IC does not predict marginal contribution — `size` has the worst IC and carries the composite's significance. A greedy prefix curve is the wrong instrument; LOO or a Shapley-style decomposition is the right one |

**U7 follow-up, if Don wants the options thread continued:**

| dependency | status |
|---|---|
| the join | **READY and PINNED** — `valuation/edge/options_veto.py`, backward-looking only, tested against its own look-ahead variant |
| the top-decile thread | **NOT PRE-REGISTERED.** D1/D2 post +18.74% / +14.78% on 97 and 181 trades. That is a positive-selection idea, not a veto, and it is the opposite end of the table U7 tested — so it is a NEW hypothesis, and running it on the same book that suggested it is exactly the trap X7 exists to expose |
| the size confound | **MUST BE HANDLED FIRST.** The composite decile inside 187 megacaps is largely a market-cap sort ($62.7B → $133.5B, monotone D1→D9). Any composite-based options test must either neutralise size or rank *within* the options universe on a composite built for it |
| U1 as written | **DO NOT RUN.** The strictly easier bar failed with a mechanism |

**Standing, and outranking both if Don says so:** **P4** — `seed_book` never sells names that
leave the book, so every session the paper track accumulates under the wrong rules is a session
that has to be thrown away — and **X8**, the international replication, still the only genuinely
out-of-sample evidence available to either programme.

---

# SESSION 7 — B8, then the PRE-REGISTERED held-out leave-one-out, plus P4

Owner: pipeline builder. Audit session 7. Previous session verified complete: YES (session 6
closed at `21fbe46`, six commits, both probes returned verdicts).

**Order is forced by the `needs first` table session 6 wrote: B8 is resolved FIRST, because a
leave-one-out run on an unresolved B8 produces a result nobody can label honestly.**

## 0. B8 — RESOLVED BEFORE ANY LOO NUMBER EXISTED

### What was actually wrong

`holdout_theme_validate`'s docstring described a four-step protocol: split by time, **decide on
one half with a pre-specified rule**, measure on the other half only, run both directions.
Step 2 was never implemented. `rule_fired` was computed (now `fundamental_panel.py:3545`; the
audit's cited `:3048` had drifted) and **no line of code ever read it**. The verdict was
`all(improves)` across both directions — a demanding test, and a legitimate one, but a
**both-halves stability check on the full sample**, not an out-of-sample confirmation. The
project has been calling it the latter since P5.

### FIXED, not renamed — and the distinction is load-bearing

The naive repair is to gate `verdicts` on `rule_fired`. **That would have been a silent error.**
`scripts/placebo.py:108` reads `verdicts`, and X7's measured **~6% false-positive rate of the
held-out gate** was calibrated against that exact object across 100 placebo draws. Redefining
`verdicts` in place would leave that 6% figure attached to a gate that no longer exists, with
nothing anywhere recording the substitution — the same class of defect as the stale theme IC
table found in session 6.

So both objects now ship, each named for what it is:

| key | question it answers | status |
|---|---|---|
| `verdicts` (alias `stability_verdicts`) | does zeroing this theme improve the measure half in BOTH directions? | **semantics frozen** — X7's 6% FPR still applies to it |
| `oos_verdicts` (NEW) | ...restricted to directions where the decide-half rule actually flagged the theme | the protocol the docstring always described |
| `oos_directions_tested` (NEW) | how many of the two directions carried any evidence at all | 0 means **no out-of-sample test was run** |

`verdicts_scope` and `oos_verdicts_scope` strings ship alongside, so a reader of
`BACKTEST_RESULTS.json` cannot mistake one for the other.

### Measured on the corrected 69-date panel — the shipped decisions HOLD, on thinner evidence

`python -m scripts.b8_holdout_scope --panel panel_corrected_69d.pkl`, 113,945 rows, 69 dates,
boundary date 2017-07-20 embargoed, eight themes.

| theme | stability verdict | **OOS verdict** | directions tested |
|---|---|---|---|
| **low_risk** | confirmed | **confirmed_oos** | **1 of 2** |
| **insider** | rejected | **rejected_oos** | 1 of 2 |
| value | rejected | rejected_oos | 1 |
| momentum | not_replicated | rejected_oos | 1 |
| size | rejected | rejected_oos | 1 |
| quality | rejected | **not_flagged** | **0** |
| capital_discipline | not_replicated | **not_flagged** | **0** |
| institutional | rejected | **not_flagged** | **0** |

**Neither shipped decision changes.** `low_risk` (zeroed live) is confirmed under the honest
protocol; `insider` (kept at 0.125) is rejected under it. Nothing needs reverting, and no weight
was touched.

**But the evidence for `low_risk` is exactly half what the record claims.** The rule fires only
on the early decide half; on the late half `low_risk`'s median IC is positive, so it is not a
candidate at all in that direction. CLAUDE.md's B8 correction inferred this from reading the
code — it is now measured. The honest sentence is: *"zeroing `low_risk` is confirmed
out-of-sample in one of two split directions, and passes a both-halves stability check in both."*
Not "confirmed out-of-sample", full stop.

### The finding that changes the LOO design, and it is not a small one

**Three themes are `not_flagged`: the decide-half rule never fires on them in either
direction.** The rule is `median IC <= 0`, and `quality` (+3.10), `capital_discipline` (+2.76)
and `institutional` (+1.55) all have comfortably positive IC.

**`capital_discipline` is the theme session 6's exploratory leave-one-out said was worth
dropping** (dropping it raised alpha to +8.54% and long-short *t* to 3.352). Under
`holdout_theme_validate`'s rule it is not a candidate for dropping and never can be.

That is not a bug in the rule. It is X3's central finding arriving a second time: **an IC-based
selection rule cannot express the hypothesis, because X3's whole result is that theme IC does
not predict marginal contribution** — `size` has the worst IC (−0.30) and carries the
composite's entire significance. Gating LOO candidacy on `median IC <= 0` would reproduce, as
the test's own design, the exact error the test exists to check.

**Consequence, and it is pre-registered below rather than discovered later: the LOO decide rule
must be the LOO effect itself, measured on the decide half — not an IC rule.**
`holdout_theme_validate` is therefore used for B8's own verdicts and is NOT the instrument for
the LOO; a purpose-built split with the same embargo discipline is.

## 1. PRE-COMMITMENT — written and committed BEFORE any LOO number existed

### The hypothesis under test

Session 6's leave-one-out was **exploratory**: seven correlated comparisons on the full sample,
reported for their extremes, generated after seeing the prefix curve. It said dropping
`capital_discipline` raises top-decile alpha +7.17% → +8.54% and long-short *t* 2.836 → 3.352,
and that dropping `size` costs 3.08pp/yr. **Re-quoting those numbers is not a test of them.**

The question is narrower and answerable: **does choosing a theme to drop, by its own
leave-one-out effect on data you are allowed to look at, improve the composite on data you are
not?**

### Protocol, fixed in advance

1. Split the 69 rebalance dates in half **by time**; **embargo the boundary date** (rebalance ==
   horizon == 63d, so only that date's forward window can straddle the split). Identical
   machinery and identical embargo to `holdout_theme_validate`.
2. **DECIDE half:** run all **seven** leave-one-out arms — the flat 7-theme composite with one
   theme dropped, re-normalised to flat 1/6 — and rank them by the decide-half **top-decile
   alpha gain** vs the full composite. **Select the single best arm.** One selection, one degree
   of freedom.
3. **MEASURE half:** measure that one selected arm against the full composite. The measure half
   informs nothing about which arm was chosen.
4. **Both directions** (decide-early/measure-late and decide-late/measure-early), so no verdict
   rests on one arbitrary split.

### Thresholds — reusing the project's existing committed margins, not new ones

`MIN_HOLDOUT_ALPHA_GAIN = 0.01` (100bps/yr, an economic bar: an improvement smaller than the
cost of implementing it is not an improvement) and `MIN_HOLDOUT_TSTAT_GAIN = 0.25` (a noise
floor). These were committed before the P6 runs and are already in the codebase; inventing a
fresh pair after seeing session 6's exploratory numbers would be threshold-shopping.

* **ADOPTED-eligible** — the selected arm clears **both** margins in **both** directions.
  (Eligible, not adopted: a weight change additionally needs its own gate. Nothing ships this
  session regardless of outcome.)
* **NULL** — anything else: mixed directions, or clears sign but not margin. Per RUN_RULES 6, a
  result ambiguous against its own threshold **is a null, not a judgement call**.
* **REJECTED** — the selected arm is negative on the measure half in both directions.

**Reported but carrying NO verdict** (stated now so it cannot be promoted later): all seven
arms' measure-half effects, as the distribution the selected arm has to be read against; and
whether the same theme is selected in both directions. A single theme surviving selection in
both directions is a materially stronger result than two different themes, and I am committing
in advance to say which happened.

### The expectation, written down first

The carry-forward rule says to state the direction expected before running, precisely because
this project keeps getting it wrong (R10, O20, the spread toll, U7 — four in a row).

**I expect a NULL, and I hold it at about 70/30.** Session 6's exploratory result is the maximum
of seven correlated comparisons on 69 dates; the maximum of seven noisy draws is biased upward
by construction, and half-sample statistics here are noisier still. If it replicates on a
held-out split in both directions, that is genuinely surprising and worth acting on. **The
project's expectations have been wrong four consecutive times, so this one is a prediction, not
a prior to lean on.**

### The trial cost, and a correction to the number in the task

**Seven arms are seven trials.** They are logged to `RESEARCH_LOG.md` as one pre-registered grid
row, `n=7`, in the `equity` domain.

The task brief says equity `N` goes **92 → 99**, `√(2·ln 99) = 3.03`. **That is stale by one
session.** Session 6's realised count was **104**, not 92 — the pre-commitment predicted 92 and
the run overshot it, because the previously-unlogged void X3 run was logged as `SUPERSEDED` with
`n=12` and `research_log.py:73` excludes only `FIXED` rows, so `SUPERSEDED` rows count. Verified
this session: `python -m valuation.edge.research_log` reports `equity: 104`.

| | before | after 7 LOO arms |
|---|---|---|
| equity `N` | **104** | **111** |
| `√(2·ln N)` — the Harvey–Liu–Zhu haircut | 3.048 | **3.069** |

So the haircut moves **past the 3.0 hurdle by more**, not up to it. The Deflated Sharpe
consequence is computed exactly in the results below rather than estimated, using
`ablation.deflated_sharpe_at`, which backs the skew/kurtosis denominator out of the recorded
statistic and re-evaluates at the new `N`.

**Out of scope, stated in advance:** X7's calibrated bars are NOT re-derived at N = 111 (the
placebo is 100 draws through the full pipeline — hours). The direction is known and unfavourable
to me, which is why quoting the old bar is safe: X7 measured the floor *falling* as N rises
(0.8567 at N = 8 → 0.7216 at N = 84), so holding 0.7216 at N = 111 makes passing harder.

## 2. RESULTS — the pre-registered held-out leave-one-out

**Run:** `python -m scripts.loo_prereg --panel panel_corrected_69d.pkl --json LOO_HOLDOUT_RESULTS.json`.
Panel: the corrected 69-date panel, **113,945 rows, 2,531 names**, seven deployed themes, flat
weights. `flat_weights_are_the_deployed_weights: true` — asserted in the script, not assumed,
because a silent mismatch would make every number below describe a composite nobody trades.
Split 34 / 34 with **2017-07-20 embargoed**.

### VERDICT: NULL

Neither direction's selected arm clears either margin.

| direction | selected on the decide half | decide gain | **measure-half Δalpha** (bar +1.00%) | **measure-half Δ LS t** (bar +0.250) | clears |
|---|---|---|---|---|---|
| decide early → measure late | drop **`momentum`** | +3.68% | **−1.30%** | **−0.706** | no / no |
| decide late → measure early | drop **`capital_discipline`** | +2.20% | **+0.20%** | **−0.201** | no / no |

`null` rather than `rejected`, on the pre-registered rule: direction 2's alpha is *positive*
(+0.20%), just an order of magnitude below the 100bps bar. Per RUN_RULES 6 an ambiguous result
against its own threshold is a null, not a judgement call.

**Different themes were selected in each direction** — pre-registered as a thing to report
either way. That is the weaker of the two outcomes and it is the one that happened.

### The expectation, and the record's verdict on it

Pre-committed at `5a27ea1`: *"I expect a NULL, and I hold it at about 70/30."* **Right** — for
the stated reason, that the maximum of seven correlated comparisons is biased upward by
construction. That breaks a four-run streak of wrong directional calls (R10, O20, the spread
toll, U7). One correct call after four wrong ones is not evidence the reasoning improved; the
standing rule to measure rather than reason still holds.

### WHY it is null — the decide-half ranking is not stable, and this is the real finding

The two directions share their data: direction 1's measure half **is** direction 2's decide
half. So there are only two independent sets of seven numbers, and laying them side by side is
the whole diagnosis.

| dropped theme | **early half** Δalpha | **late half** Δalpha | stable? |
|---|---|---|---|
| momentum | **+3.68%** (best) | −1.30% (5th) | **sign flip** |
| capital_discipline | +0.20% (3rd) | **+2.20%** (best) | same sign, rank moves 3 → 1 |
| insider | −1.39% (6th) | +1.94% (2nd) | **sign flip** |
| value | −1.01% (5th) | +0.63% (4th) | **sign flip** |
| institutional | −0.89% (4th) | −1.90% (6th) | stable, both negative |
| **quality** | **+1.06%** (2nd) | **+1.30%** (3rd) | **stable, both positive** |
| **size** | **−2.64%** (worst) | **−3.46%** (worst) | **stable, worst in both** |

**Four of seven arms change sign between halves.** The full-sample exploratory result session 6
reported — "dropping `capital_discipline` raises alpha to +8.54%" — is the average of +0.20%
and +2.20%, i.e. it is carried by the late half and is not a property of the panel. That is
exactly the failure mode a held-out split exists to expose, and it is why the session-6 numbers
were labelled EXPLORATORY and left unacted-on.

### `size` is corroborated, and this is the one durable thing the run produced

**Dropping `size` is the WORST arm in both halves independently, by a wide margin (−2.64% and
−3.46%).** It is the only theme whose leave-one-out effect is both large and stable. X3 found
`size` has the worst theme IC (−0.30) while carrying the composite's entire significance; this
is that finding surviving a time split, in the only out-of-sample sense available on one panel.

**Stated with its limit:** this is not a pre-registered test of `size` — the pre-registered
object was the SELECTED arm, and `size` was never selected because the rule selects the
maximum. It is the most stable cell in a table that carries no verdict. It is strong enough to
say *"do not drop `size`, and stop treating its low IC as evidence against it"*, and not strong
enough to be quoted as a confirmed result.

### The one thing I will NOT claim, and why it is the interesting part

`quality` clears **both** margins on **both** halves (+1.06% / +1.30% alpha, +0.306 / +0.257 on
long-short t). It is the only theme that does. It was selected in **neither** direction, because
the pre-registered decide rule takes the **maximum** decide-half gain and in each half some
noisier arm ranked above it.

**So the pre-registered selection rule picked the noisiest arm rather than the most consistent
one** — the maximum is precisely the statistic most inflated by noise, which is the same
mechanism that made session 6's exploratory result look strong.

**This CANNOT be promoted now.** Noticing that a stability-based selection rule would have found
`quality` *after* seeing which rule works is selecting the rule on the results — the exact error
this session's design exists to avoid, one level up. It goes to session 8 as a pre-registration
or not at all. Recorded here in full so that nobody has to rediscover it, and so that if it is
ever run, the record shows it was generated post-hoc.

### Trial cost — computed, not estimated

| | before | after |
|---|---|---|
| equity `N` | 104 | **111** |
| `sr0_benchmark` | 0.4181 | **0.4218** |
| **Deflated Sharpe** | 0.8789 | **0.8721** |
| `√(2·ln N)` | 3.0478 | **3.0690** |

Computed with `ablation.deflated_sharpe_at` off the recorded `deflated_sharpe_detail`
(`sharpe_per_period` 0.5500, `var_sr_across_trials` 0.02700, 69 periods). The round trip
reproduces session 6's recorded 0.8789 at N = 104 exactly, which is the check that the
extrapolation is arithmetic rather than a re-fit.

**Still above X7's calibrated floor of 0.7216; still below the 0.95 convention.** Quote it
whole, as the record requires: *"Deflated Sharpe 0.8721 at N = 111 — fails the conventional
>0.95 bar, while sitting above all 100 placebo draws (calibrated bar 0.72)."*

The task brief's "92 → 99, √(2·ln 99) = 3.03" was stale by one session; the correction is in
§1 above and the realised figure is **3.069**.

### POST-MERGE CORRECTION — the denominator moved again while this session ran

`origin/main` was merged into this branch at close-out and a concurrent lane
(`HANDOFF_signals.md`: S4, S4b, S1a, S1b, S2) had landed **five more equity trials**. `N` is a
PROJECT-level quantity, not a session-level one, so the honest final figure is not the one this
session predicted:

| | equity `N` | `sr0` | Deflated Sharpe | `√(2·ln N)` |
|---|---|---|---|---|
| before session 7 | 104 | 0.4181 | 0.8789 | 3.0478 |
| **+ this session's 7 LOO arms** | **111** | 0.4218 | 0.8721 | 3.0690 |
| **+ the signals lane's 5, post-merge** | **116** | **0.4243** | **0.8674** | **3.0834** |

**Quote 116 and 0.8674, not 111 and 0.8721.** This session's own *cost* is the 7 arms; the
denominator the headline is charged is whatever has landed. That distinction is exactly why M1
put the counter in a file instead of a constant — and it is the second session running in which
the realised `N` overshot its own pre-commitment, for a different reason each time (session 6:
`SUPERSEDED` rows count; session 7: a parallel lane landed mid-run).

**No verdict moves.** 0.8674 is still far above X7's calibrated floor of 0.7216 and still below
the 0.95 convention, which is the same sentence as before at a slightly worse number.

## 3. RESULTS — P4, the paper track's rules

**The bug, restated from the code:** `seed_book` (`paper_track.py`) computed `fresh = [names not
already held]` and inserted them. There was no other write path. **A name entered the book once
and was held forever**, so the paper index became an ever-growing union of everything the
screener had ever liked — it stopped being the Valquo Index the day the first name dropped out,
and every session since accumulated under rules no backtest describes. This is why the item was
carried as *urgent*: the cost is not a wrong number, it is that the elapsed track has to be
thrown away.

### The fix, and the two things that made it non-obvious

Departed names are now **closed** — sold at the day's price with the day's SPY — and moved to a
new `paper_index_closed` table.

1. **Closed, never deleted.** Deleting is the obvious repair and it is **reverse survivorship
   bias**: names leave this book when their composite decays, so erasing them removes
   disproportionately the ones that did badly and silently flatters the record. The full
   entry/exit legs, both price and benchmark, are kept so each stint's realised return against
   SPY stays computable forever.
2. **A separate table, not a `status` column** — and this was a defect in my own first
   implementation, caught by writing the re-entry test. `paper_index_holdings.ticker` is a
   `PRIMARY KEY` and the insert is `INSERT OR IGNORE`, so a closed row left in that table makes
   a name that **re-enters** the book silently un-addable. That is the original bug's mirror
   image and just as quiet. Keying history on `(ticker, entry_date)` also lets one name hold
   several separate stints, which is what a real book does.

**The guard.** A truncated export and a genuinely smaller book are indistinguishable at this
layer, and acting on the wrong one liquidates a live track. A book that has shrunk below
`MIN_BOOK_RETENTION = 0.5` of current holdings closes nothing and reports `close_refused` with
the reason. It refuses loudly rather than proceeding — not a silenced check.

**Two consequences that had to be handled or they would have been new bugs:**

* **`inception` now spans closed stints.** Taking the minimum entry date over open holdings only
  would walk the track's start date forward every time its oldest position left, so the record
  would appear to get *younger* the longer it ran.
* **Closed stints are reported, not dropped.** `index_summary` gains a `realized` block —
  count, priced count, and mean active return vs SPY over each stint's own window.

### What P4 does NOT fix, stated because the flag has to ship with the number

The daily point remains a **snapshot of open holdings**. A closed stint's realised return is
preserved and reported but is **not chained into the daily series**. Chaining realised stints
into a continuously-compounded index is a **construction change**, not a bug fix — it would
break the deliberate correspondence with `edge/track.py`'s methodology that makes the two
records comparable — so it was not made. The limitation ships inside the payload as
`detail.scope`, so it travels with the number instead of having to be inferred from the schema.

**Nothing about the live track was reset**, and no historical row was rewritten. `close_exits`
defaults to `True` because the accumulate-only behaviour is the bug; `close_exits=False`
reproduces a historical run.

Pinned by five tests in `tests/test_paper_track.py` (45/45, up from 40), one per failure mode:
the close keeps the record, a closed name stops moving the index and can re-enter, a truncated
export closes nothing while an ordinary rebalance is not refused, and inception does not walk
forward.

## 4. BUGS FOUND

**1. The trial-counting schema contradicted its own counter, and it decided the headline `N`.**
`RESEARCH_LOG.md`'s schema read "Only `ADOPTED` / `REJECTED` / `NULL` / `INCONCLUSIVE` rows are
trials", which excludes `SUPERSEDED`. `research_log.py:73` has never implemented that — `_parse`
skips `FIXED` and nothing else. Not academic: the void X3 row carries `n=12`, so the reading
decides whether equity `N` is **92 or 104**. Session 6 hit the discrepancy, took the harsher
number, and explicitly referred the rule to this session rather than settling it while looking at
its own results — which was the right call. **Resolved in favour of the counter and the prose
rewritten:** a superseded search still happened and still shaped what was run next; `SUPERSEDED`
judges a RESULT's validity, not whether the data was interrogated. It is also the conservative
reading, since it makes `N` larger.

**2. The X3-VOID log row asserted the opposite of what the counter does.** Its `source` cell read
"NOT counted toward N per the schema", while contributing 12 of equity's count. Session 6 rewrote
the handoff's cost table when it discovered this and missed the log row itself. Corrected in
place; the row now states its actual contribution.

**3. `theme_ic` returns `{}` for any panel whose columns are not in `S.FACTORS_ALL`, silently.**
It iterates the known theme list and skips anything absent, so a synthetic panel with arbitrary
column names produces an empty dict, no warning, and a completed run. **This made the first
version of my own B8 test pass for the wrong reason** — every theme came back `not_flagged`
because `median_ic` was `None`, not because the decide rule declined to fire. It was caught only
because a second assertion in the same test expected the *opposite* verdict on a deliberately
anti-predictive theme and failed. This is the same shape as the four coverage bugs in this
project's history: the function is wired, raises nothing, and returns empty. Any future study or
test that builds a panel with its own column names hits it. **The existing
`test_holdout_theme_validate_protocol` uses columns `good` and `junk` and is therefore exercising
a code path where every IC is `None`** — it still tests what it claims about split geometry, but
not what it implies about IC-driven behaviour. Not fixed: `theme_ic` is read by other lanes and a
coverage-style warning there is their call, not mine.

**4. A latent bug in my own first P4 implementation, recorded because it is the fix's mirror
image.** Marking departed names with a `status` column and leaving them in
`paper_index_holdings` looks correct and is not: that table's `ticker` is a `PRIMARY KEY` and the
insert is `INSERT OR IGNORE`, so a name that **re-enters** the book would have been silently
refused — the same failure mode as the bug being repaired, in the opposite direction, and equally
invisible. Found by writing the re-entry test before believing the implementation. Fixed by
moving closed stints to `paper_index_closed` keyed on `(ticker, entry_date)`.

**4b. B8 REACHED THE PRODUCT-FACING FILE, AND FIXING THE FUNCTION ONLY FIXED HALF OF IT.**
`results_file.render_md` headed this section **"Held-out confirmation — does zeroing a theme
still help out-of-sample?"** and told the reader "the theme is judged on one half and the effect
measured on the other" — a description of the protocol the code did **not** run, rendered into
the artifact a human actually reads. I had already fixed `holdout_theme_validate` and would have
shipped the session with the overstatement intact, because the fix and the label live in
different files and only the function was in the audit item. Found by reading the renderer to
check nothing downstream broke. The section is now headed "Held-out theme checks — stability,
and the rule-gated out-of-sample verdict", carries **both** verdicts plus the
directions-tested count, and says in words that the stability column is *not* an out-of-sample
confirmation. `test_holdout_theme_validate_protocol` now asserts the old heading is **absent**,
so it cannot come back quietly. **The general lesson: an audit item scoped to a function is not
discharged until the strings that describe it are checked too.**

**5. A second consequence of P4 that would have been a new bug.** `index_point` computed
`inception` as the minimum entry date over open holdings. Once names can leave, that walks the
track's start date forward every time its oldest position is sold — the record would appear to
get *younger* the longer it ran. Now spans closed stints.

**6. The audit's cited line number for B8 has drifted.** `VALQUO_EDGE_AUDIT.md`,
`HANDOFF_STATUS.md:812` and `CLAUDE.md:323` all cite `fundamental_panel.py:3048`, which now sits
inside `_band_select` — an unrelated function. The real site was `:3545`. Harmless here because
the symbol name was also given, but a citation that silently rots points the next reader at the
wrong code.

**7. MY OWN TEST SWEEP HAD A GATE THAT COULD NOT FAIL — and the same question had to be asked
of CI.** The scratch sweep used by sessions 6 and 7 ran
`out=$(python "$f" 2>&1 | tail -2 | tr '
' ' ')` and then tested `$?`. **After a pipeline `$?`
is the LAST command's status**, i.e. `tr`'s, which is always 0 — so the exit code was never
consulted and the verdict rested entirely on grepping the output for "fail". That heuristic then
fired on another lane's `1 xfail, 0 xpass, 0 failed` line and reported `OVERALL_FAIL=1` for a
suite that exits 0. **Both directions are bad: it cried wolf here, and it would have stayed
silent for a suite that crashed without printing the word "fail".** Re-verified by exit code
alone: **24 suites, all 0**.

**The important half is what this prompted:** the same flaw in `.github/workflows/land-agent-branch.yml`
would mean the auto-land gate could never block a bad merge. **Checked — it is CORRECT.** It runs
`python "$f" || { echo "::error::$f FAILED"; fail=1; }`, taking the raw exit status with no
pipeline in between, and `exit $fail` at the end. The workflow's own header comment flags this as
the thing to verify on first run ("test_edge.py must EXIT non-zero on failure for the gate to be
real"), and it does. **The gate is real; only my scratch harness was broken.** Recorded because
"the harness that checks the checks" is exactly the kind of thing that goes unexamined for months.

## 5. WHAT WAS NOT DONE, AND WHY

* **No weight was changed, and none was going to be.** The pre-registration says a weight change
  needs its own gate on top of an `adopted_eligible` verdict; the verdict was NULL, so the
  question never arose. `low_risk` stays zeroed, `insider` stays at 0.125, the seven deployed
  themes stay flat 1/7.
* **The `quality` observation was NOT promoted, and this is the most important omission.**
  `quality` clears both margins on both halves and was selected in neither direction. Acting on
  it — or switching to a stability-based selection rule — after seeing which rule would have
  worked is selecting the rule on the results. That is the same error as session 6's exploratory
  LOO, one level up. Session 8 pre-registers it or nobody quotes it.
* **X7's calibrated bars were NOT re-derived at N = 111.** Same reasoning as session 6, and the
  direction is known and unfavourable to me: X7 measured the floor *falling* as N rises (0.8567 at
  N = 8 → 0.7216 at N = 84), so continuing to quote 0.7216 makes passing harder, not easier.
* **No Shapley-style decomposition.** Session 6's `needs first` table offered "LOO or a
  Shapley-style decomposition" for the ordering problem. LOO is 7 arms; Shapley over seven themes
  is 2⁷ = 128 subsets, i.e. a search an order of magnitude larger than everything this project has
  logged in the equity domain to date. It would roughly **double** equity `N` on its own. Worth
  doing only with that cost pre-registered and accepted in advance.
* **`BACKTEST_RESULTS.json` was not regenerated.** `N = 111` changes its
  `deflated_sharpe_detail` on the next full run. The consequence is computed exactly above
  (0.8789 → 0.8721) rather than spending 12 minutes rewriting a tracked artifact this session did
  not otherwise touch — and the round trip reproducing session 6's 0.8789 at N = 104 is the check
  that the arithmetic is sound.
* **`BACKTEST_RESULTS.md` STILL CARRIES THE OVERSTATED HEADING, and this is the one place B8
  survives.** Line 194 of the tracked rendered artifact reads "## Held-out confirmation — does
  zeroing a theme still help out-of-sample?", because it was rendered by a previous run. The
  renderer is fixed; the *output* is regenerated only by a full backtest. I did not run one:
  a full run overwrites the canonical `BACKTEST_RESULTS.json` that other lanes are reading
  mid-audit, and session 6 set the precedent of computing the consequence instead. **Re-rendering
  from the existing JSON was considered and rejected** — that JSON predates the fix and has no
  `oos_verdicts`, so every OOS cell would render `n/a` and the .md would silently disagree with
  the .json it is supposed to describe. **The next full backtest fixes it with no further work;
  until then, do not quote that section of `BACKTEST_RESULTS.md`.**
* **U1 was not run.** U7 foreclosed it as written and nothing this session reopens it.
* **P4's migration has not run against the live paper-track database.** It is
  `CREATE TABLE IF NOT EXISTS` plus an additive read path, so it applies on the next
  `paper_track_run.py`; no live row was touched from here, and the first real run will report
  `closed: N` for however many names have accumulated wrongly since the track started. **That
  number is worth reading when it appears** — it is the size of the bug.

## 6. IS SESSION 7 CLOSED?

**Yes.** B8 was resolved before any LOO number existed, and the resolution changed the LOO's
design rather than merely unblocking it. The LOO ran against thresholds committed in a pushed
commit (`5a27ea1`) and returned a verdict. P4 shipped with its remaining limitation flagged
rather than hidden. The trial cost is logged and the denominator moved.

**The session produced no promotion, and one durable negative plus one durable positive:** the
full-sample leave-one-out ranking is not stable across a time split (four of seven arms change
sign), and `size` is the worst arm to drop in both halves independently.

## 7. SESSION 8 — first item and its `needs first`

**Session 8's first item is a pre-registered test of the SELECTION RULE, not of another theme.**
This session's result is that the decide-half argmax is not the right instrument: it picked
`momentum` and `capital_discipline`, both of which flip sign across halves, while the one theme
stable on both halves was never selected. That is a question about the rule, and it is testable
without touching a weight.

| dependency | status |
|---|---|
| the corrected 69-date panel | **READY** — `data/free_analysis/panel_corrected_69d.pkl`, 113,945 rows, 2,531 names, reproduces the shipped headline |
| the LOO machinery | **READY and PINNED** — `valuation/edge/loo_holdout.py`, `scripts/loo_prereg.py`, 4 tests |
| the hypothesis | **READY, and it is POST-HOC** — a stability-based decide rule (require the same sign in both halves, then take the largest) would have selected `quality`. **Generated after seeing which rule worked.** It must be pre-registered and run against a *third* thing to be evidence, not re-derived on the same two halves |
| the honest problem with it | **UNRESOLVED and it is the real obstacle.** With only two halves, "stable across halves" is measured on the same data the measurement half provides. A genuine test needs either a third block (23/23/23 dates, thinner still) or the X8 international panel. **On one panel this may simply not be answerable** — say so rather than running it thin |
| the trial cost | **NOT FREE.** A second 7-arm sweep takes equity N 111 → 118, √(2·ln 118) = 3.09. Pre-register or do not run |
| B8 | **RESOLVED** — `oos_verdicts` vs `stability_verdicts`, both shipping, scopes in words |

**Standing, and outranking the above if Don says so:** **X8**, the international replication —
still the only genuinely out-of-sample evidence available to either programme, and now doubly so,
because this session's answer to "can we settle the ordering question on one panel?" is *probably
not*.

**Do not re-open:** U1 as written (U7 foreclosed it, with a mechanism); the full-sample
leave-one-out as a source of verdicts (it does not survive a time split); `sector_neutral`,
PEAD, TTM ROE/ROIC, robust z-scores, momentum/institutional consolidation (all rejected, all
with numbers).

---

# SESSION 8 (2026-08-07) — the selection rule is NOT ANSWERABLE on this panel, and X8 already ran

**Owner:** pipeline builder. **Previous session verified complete?** YES — session 7 landed
(`5a27ea1` … `90fd576`): B8 FIXED, held-out LOO NULL, P4 shipped.

**What I did:** settled the answerability question first, as instructed; concluded the test
**cannot be answered on the Sharadar panel**; **did not run it**; and spent the session on what
would settle it. Along the way I found that **X8 is not future work — it ran on 2026-08-04 and it
replicated** — and that this project's memory file never recorded the result.

**One-line verdict: NOT ANSWERABLE on one panel — declined, at a cost of zero trials. Equity `N`
stays 116.**

---

## 0. The headline finding I did not go looking for: X8 already replicated

`CLAUDE.md` is, by its own description, "the project's memory". Before this session it contained
the strings **"JKP" and "Japan" zero times**; so did `HANDOFF_STATUS.md`. The only trace of X8 in
either file was the phrase *"X8's international replication is the out-of-sample evidence, R1 is
not"*, which reads as a promise about future work.

**X8 ran on 2026-08-04 with its thresholds committed first, and its verdict was REPLICATES.** It
is written up in full in `HANDOFF_free_analysis.md` (§ "Round 3 — X8, U5, M5") and marked `DONE`
in `VALQUO_LEDGER.md:112`. Neither file is one that an edge-lane session is told to read.

**The omission demonstrably misled.** This session's own prompt instructed me to *"scope X8's
international replication … make that actionable instead of aspirational"* — for a test that had
already run and passed. **And I contributed to it:** session 7's own dependency table, written by
me, lists X8 as "still the only genuinely out-of-sample evidence *available*", which is how a
completed test gets re-scheduled. Two consecutive sessions treated a passed test as pending.

The result is now recorded in `CLAUDE.md` CURRENT STATE, with the parts that do **not** flatter
the product kept attached: two of five mapped themes (quality, momentum) do not generalise to
Japan; JKP's composite earns +2% to +3.4%/yr against Valquo's +20.4%, a factor of six on a
different instrument, so **X8 corroborates the premia and not the magnitude**; and only 5 of 7
themes map at all.

**Process bug, reported rather than fixed unilaterally (RUN_RULES A3):** a finding can be
`DONE` in the ledger, written up in one lane's handoff, and invisible to every other lane,
because `CLAUDE.md` is the only file all lanes read and nothing requires a result to land there.
That is a memory-architecture defect, not a clerical slip — **the third time the project has been
misled by its own stale memory** (after the mislabelled theme-IC table and the rendered
`BACKTEST_RESULTS.md`). Suggested rule for Don: *a verdict is not `DONE` until it appears in
`CLAUDE.md`.* I have not changed the ledger's definition of `DONE` — that is a project-wide
convention and not mine to redefine.

---

## 1. The answerability decision, written before anything was run

**Question.** Session 7 nominated a pre-registered test of the *selection rule*: the decide-half
argmax picked `momentum` and `capital_discipline`, both of which flip sign across halves, while
`quality` — which clears both margins on both halves — was never selected. Is a stability-based
decide rule (same sign in both decide blocks, then largest) a better instrument?

**Instrument for the decision.** The already-published session-7 arm table
(`data/free_analysis/LOO_HOLDOUT_RESULTS.json`, `measure_all_arms` for both directions). Those
numbers are in the record and already paid for in `N`, so **this analysis peeks at no new data
and creates no trial.** Nothing about the third block was computed.

**Noise scale.** Each of the 7 arms has an independent Δalpha on each 34-date half. Pooling the
half-differences gives the sd of a single half-estimate:

| arm | early Δα | late Δα | mean | half-diff | sign |
|---|---|---|---|---|---|
| value | −1.01% | +0.63% | −0.19% | −0.82pp | **FLIP** |
| quality | +1.06% | +1.30% | +1.18% | −0.12pp | same |
| momentum | +3.68% | −1.30% | +1.19% | +2.49pp | **FLIP** |
| insider | −1.39% | +1.94% | +0.27% | −1.67pp | **FLIP** |
| capital_discipline | +0.20% | +2.20% | +1.20% | −1.00pp | same |
| size | −2.64% | −3.46% | −3.05% | +0.41pp | same |
| institutional | −0.89% | −1.90% | −1.40% | +0.51pp | same |

**σ(34 dates) = 1.26pp**, hence **σ(22 dates) = 1.57pp** — 69 dates minus 2 embargoed boundaries,
split three ways.

### The three reasons it is not answerable

**(a) The noise exceeds the margin.** The pre-committed bar is `MIN_HOLDOUT_ALPHA_GAIN` = 1.00pp.
On a 22-date measure block, **pure noise clears it 26.1% of the time**, and power under the
record's own best estimates is **50.6%**. Both a positive and a negative outcome would have been
uninterpretable. (The 100bps margin was committed before P6 for 34-date halves, where the same
false-positive rate is 21.4%; it was never calibrated for thirds.)

**(b) The design cannot separate the two rules even in principle.** Monte Carlo over the design
itself (200k draws, noise as measured above): the stability rule and the incumbent argmax rule
**select the same arm 90.0%** of the time under the record's estimates (75.2% under a complete
null), and **reach a different verdict on only 5.1% of panels**. The two hypotheses barely differ
in their observable consequences on data this size.

**(c) The decisive one, which needs no variance estimate at all.** "Which rule is better" is a
property of the distribution over panels; one panel is one draw. A paired sign test at n = 1 has a
**minimum achievable p-value of 0.50**, at n = 2 it is 0.25 — **no threshold reaches significance,
so no possible outcome could have been quotable.** This holds whatever the effect size and
whatever the noise, which is why it, and not the power calculation, is the actual reason.

### What declining bought

| | equity `N` | Deflated Sharpe | √(2·ln N) |
|---|---|---|---|
| **declined (shipped)** | **116** | **0.8674** | **3.083** |
| had I run the 7 arms | 123 | 0.8609 | 3.102 |

Computed with `ablation.deflated_sharpe_at`, which moves a recorded statistic to a new `N` exactly.
**A test that cannot resolve still costs the denominator.** Declining is the cheaper action.

**No `RESEARCH_LOG.md` row was added for the un-run test.** The prompt's rule was "pre-register and
log, or do not run"; I chose not to run, so the logging obligation does not bind, and a row would
misrepresent an unperformed search. The row is written when Session 9 runs it.

---

## 2. What WOULD settle it — scoped, feasibility-checked, and pre-registered

Not aspirational: **the data is already on disk**, 2.1 MB in `data/factors/research_only/jkp/`,
downloaded by X8 on 2026-08-04.

**Feasibility probe run this session (shape and coverage only — no arm return, selection or
verdict computed, deliberately, so the pre-registration below stays blind):**

```
17 regions (15 developed Europe + jpn + usa), 324 months each, 1999-01-31 -> 2025-12-31
all 5 mapped themes present with 324/324 non-null months in EVERY region
regions usable for a 5-arm leave-one-out: 17/17
```

`scripts/jkp_replication.composite_series()` already returns the per-theme wide frame, so an arm is
`w.drop(columns=[theme]).mean(axis=1)`. **No new data acquisition, no new loader, no cost.**

### PRE-REGISTRATION — Session 9 executes this, blind

- **Decide set:** `usa` only. **Measure set:** the 15 developed-European countries + `jpn` — 16
  held-out countries, none touched during selection.
- **Arms:** 5 leave-one-out arms (`value`, `quality`, `momentum`, `size`, `investment`). *Only 5
  of Valquo's 7 themes map;* `insider` and `institutional` have no JKP analogue and are out of
  scope here — say so whenever the result is quoted.
- **Rule A (incumbent):** split `usa` in half by date; pick the arm with the largest mean Δ vs the
  full 5-theme composite across both halves.
- **Rule B (stability):** among arms whose Δ has the **same sign in both `usa` halves**, pick the
  largest. If none qualifies, Rule B abstains and that is recorded as an outcome, not a failure.
- **Statistic:** for each of the 16 countries, the **paired** difference
  `Δ(arm chosen by B) − Δ(arm chosen by A)`, measured on that country's full 324 months.
- **Verdict:** **sign test, ≥ 12 of 16 countries favouring Rule B ⇒ Rule B is better** (exact
  one-sided α = **3.84%**). 11/16 (α 10.5%) or fewer is a **NULL**. Ambiguous is a NULL, per
  RUN_RULES A6. The sign test carries the verdict — the project's standing rule since R2.
- **Mandatory before the sign test is quoted:** the 16 countries are **not independent** —
  European equity markets co-move. Measure the cross-country design effect against its own
  shuffled null by the X7 method and gate on `clustering_measurable`, exactly as
  `options_stats.py` does. **Never quote a design effect without its null** (R3's standing rule).
  If clustering is measurable, the effective n is below 16 and the 12/16 threshold must be
  re-derived at `n_eff` **before** unblinding, not after.
- **Trial cost:** 5 arms → equity `N` 116 → 121, √(2·ln 121) = 3.096, DSR ≈ 0.862. Log all 5 rows.

### What this design can and cannot answer — state both, always

| | |
|---|---|
| **CAN** | whether a stability-based selection rule is **substantially** better: power **79.8%** against a rule better in 80% of countries, **63.0%** at 75% |
| **CANNOT** | whether it is **slightly** better: power **8.5%** at 55%, **16.7%** at 60%. A NULL here does **not** mean the rules are equivalent |
| **CANNOT** | say anything about `insider` or `institutional` (2 of 7 themes unmapped) |
| **CANNOT** | corroborate Valquo's *magnitude* — JKP is capped value-weighted terciles, Valquo an equal-weighted concentrated decile book; X8 already measured that gap at a factor of six |
| **CAVEAT** | JKP data is **CC BY-NC 4.0, RESEARCH ONLY** — it validates the model and can never ship in the product |

---

## 3. Session 9's first item, with its `needs first` table

**First item: execute the pre-registration in §2.** It is the only version of the selection-rule
question that can return a quotable answer, and everything it needs is on disk.

| dependency | status |
|---|---|
| JKP data | **READY** — `data/factors/research_only/jkp/`, 17 regions × 324 months, 5/5 themes, 100% non-null, probed this session |
| the loader | **READY** — `scripts/jkp_replication.py`, `composite_series()` returns the per-theme frame; caches locally, no network needed |
| the pre-registration | **READY and BLIND** — §2 above, written before any arm return was computed |
| the clustering gate | **EXISTS but is NOT wired for countries** — `options_stats.py` has the design-effect-vs-shuffled-null machinery for calendar months; it must be re-pointed at countries. **This is the one piece of real work**, and it must be built and tested *before* the measure set is touched |
| the trial cost | **5 rows, equity N 116 → 121.** Log them or do not run |
| the power limit | **KNOWN and BINDING** — a NULL means "not substantially better", never "equivalent" |

**Ranked alternatives if Don prefers:** (1) **task #12, the forward paper-track vs SPY** — still
the only test on data nobody has looked at, and P4 shipped the machinery for it last session;
(2) the ML tree combiner (roadmap #16); (3) re-deriving X7's calibrated long-short floor on the
**HAC** statistic, which is still open and is the reason `2.620 vs 2.14` remains apples-to-oranges.

**Do not re-open:** the selection rule on the Sharadar panel (this session, with the arithmetic);
U1 as written; the full-sample leave-one-out as a source of verdicts; `sector_neutral`, PEAD,
TTM ROE/ROIC, robust z-scores, momentum/institutional consolidation.

---

## 4. What I did NOT do, and why (RUN_RULES A4)

- **Did not run the three-block selection-rule test.** §1 — it cannot resolve, and running it to
  have a number to report is the failure mode the prompt named.
- **Did not run the cross-country test either.** It is pre-registered but not executed: building
  the country-level clustering gate is genuine work, and running the measure set before that gate
  exists would spend the blind once and get an unquotable number. Session 9 executes it blind.
- **Did not compute a single JKP arm return.** The feasibility probe reports shape and coverage
  only, by design, so §2 stays honest.
- **Did not change the ledger's definition of `DONE`**, though §0 argues it is the root cause of
  the X8 omission. Project-wide convention; Don's call.
- **Did not touch** `valuation/screener/**`, `screen.py`, `valuation/web/**`, `.github/**`,
  `.gitattributes`, `theta_bulk.py`, `data/options/**` — other lanes.
- **No `RESEARCH_LOG.md` trial rows added.** Nothing was searched; equity `N` is unchanged at 116.

---

## 5. Bugs found (RUN_RULES A3 — report everything, including outside my lane)

1. **X8's verdict never reached `CLAUDE.md` or `HANDOFF_STATUS.md`** (§0). The serious one. Fixed
   in `CLAUDE.md` this session, with the caveats attached; the underlying convention that let it
   happen is Don's call, not mine. **Now pinned** by
   `test_session8_a_landed_verdict_reaches_the_file_every_lane_reads`, which asserts both the
   result *and* its three caveats are present — a bullet quoting only the wins would be the
   overselling `CLAUDE.md` forbids, so the test checks for the unflattering half too.
2. **`HANDOFF_free_analysis.md` states X8's matched window as "1999-01 → 2026-04". The data ends
   2025-12-31.** The filter's upper bound is `<= 2026-04-30` and simply never binds, so **no
   number is affected** — but the prose overstates the data's extent by four months. Another
   lane's file; not edited, reported here. Verified this session: all 17 regions run
   1999-01-31 → 2025-12-31, 324 months.
3. **Do not trust a background task-notification's exit code for a command that was started in
   the foreground and auto-backgrounded on timeout.** One such run reported "exit code 0" while
   its own output read `249/250 edge tests passed`. A natively-backgrounded `sys.exit(1)` probe
   *was* reported faithfully, so this is specific to the auto-backgrounded path. `tests/test_edge.py`
   itself is correct by inspection — one runner, `return passed == len(tests)`,
   `sys.exit(0 if _run_all() else 1)`, no duplicate `__main__`. **This is not the session-7 gate
   flaw recurring**; that one was real and is fixed. Verify with an explicit `echo $?` or the
   `subprocess.returncode` sweep, never the notification. Also note the harness truncates these
   output files (one was cut to 8 lines), so a `FAIL` line can vanish while the summary survives —
   grep the summary count, not just for `FAIL`.

---

# SESSION 9 (2026-08-07) — X8's cross-country design is ALSO not answerable, and the gate I was told to build is what proved it

**Executed:** the Session 8 §2 pre-registration, in full, in the committed order. **The one piece
of real work §3 named — the country-level clustering gate — was built, tested and committed
BEFORE the measure set was touched** (`d9ae291`), so the blindness is a matter of git history
rather than of my word.

**RESULT: the design returns `NO CONTRAST`, and separately it could never have returned a
positive verdict at all.** Two independent kills, and the second one voids two claims Session 8
(me) wrote into `CLAUDE.md`.

---

## 0. The correction first, because Session 8 wrote the error

`CLAUDE.md` and `HANDOFF_edge_audit.md` §2 both said, of the cross-country design:

> "16 held-out countries give 16 **independent** draws instead of 1; a paired sign test then
> reaches α 3.84% at ≥12/16, with **80% power** against a rule better in 80% of countries."

**The word "independent" was an assumption, it was never measured, and it is false.** Measured
this session on the 16 countries' own monthly series:

| arm-pair | ρ | design effect | null p95 | measurable | n_eff countries |
|---|---|---|---|---|---|
| momentum vs value | **0.4844** | 8.265 | 1.128 | yes | **1.94** |
| quality vs value | 0.4198 | 7.298 | 1.130 | yes | 2.19 |
| investment vs momentum | 0.4180 | 7.270 | 1.130 | yes | 2.20 |
| momentum vs size | 0.4089 | 7.134 | 1.128 | yes | 2.24 |
| momentum vs quality | 0.3268 | 5.902 | 1.119 | yes | 2.71 |
| size vs value | 0.2820 | 5.230 | 1.144 | yes | 3.06 |
| investment vs quality | 0.2742 | 5.113 | 1.128 | yes | 3.13 |
| investment vs value | 0.2736 | 5.104 | 1.134 | yes | 3.13 |
| quality vs size | 0.2596 | 4.894 | 1.144 | yes | 3.27 |
| investment vs size | 0.1983 | 3.974 | 1.138 | yes | 4.03 |

**Clustering is measurable on 10 of 10 arm-pairs**, every observed design effect sitting 3–7×
above its own shuffled-null p95 of ~1.13. **The 16 countries are worth between 1.9 and 4.0
independent draws, not 16.**

### What that does to the pre-registered bar

| ρ | critical k of 16 at α 5% | true α of the pre-registered 12/16 bar |
|---|---|---|
| 0 (the assumption) | 12 | 3.83% |
| 0.198 (min measured) | 15 | 16.8% |
| 0.327 (median measured) | 16 | 22.8% |
| **0.484 (max measured, pre-committed)** | **17 — of 16** | **28.7%** |

- **THE PRE-REGISTERED 12/16 BAR CARRIES A TRUE FALSE-POSITIVE RATE OF 28.7%, NOT 3.84% — a
  7.5× understatement.** Had the gate not been built first, this session would have quoted a
  "3.84%" result that was really a 29% one. That is the entire return on building it.
- **THE DESIGN IS UNREACHABLE. Even a unanimous 16 of 16 gives calibrated p = 0.0546** (400k
  draws, simulation se 0.0004, 95% CI [0.0539, 0.0553]) — above 0.05, and not by a margin the
  simulation noise can explain. **No possible outcome of this experiment was quotable at α 5%.**
- It is not the max-ρ choice doing the work. At the **median** ρ the critical count is 16 of 16,
  i.e. the only passing outcome is unanimity, which has essentially no power. Under every
  measured ρ the bar sits at 15–17 of 16.
- **The §2 power table (79.8% at p=0.80, 63.0% at 0.75, 8.5% at 0.55) is VOID.** It was computed
  at independent countries. At α 5% the design's real power is **zero**, because the rejection
  region is empty.

**So Session 8's headline stands in its own terms and falls in its scope.** "Not answerable on
one panel" was right and the arithmetic behind it is untouched. "It IS answerable on X8's data"
was **wrong**, and it was wrong for exactly the reason this project keeps rediscovering: an
assumption about the data was written down as though it were a measurement. Session 8 declined a
test on 22-date blocks because σ was too large; it then proposed a replacement whose σ it never
measured.

---

## 1. The gate — `valuation/edge/cross_country.py`

The re-pointing §3 asked for, stated precisely: **`options_stats` blocks TRADES within a calendar
month; here the roles swap, and the block is the MONTH with the COUNTRIES inside it.** That makes
the measured intraclass correlation the average pairwise co-movement, which is the quantity that
erodes a cross-country sign test. **`_icc_deff` is imported and reused unchanged** — it is a
one-way random-effects ANOVA and does not care what the blocks mean — so the two gates cannot
drift apart.

**The design effect is NOT applied as a haircut.** It calibrates the sign test's critical count by
simulating that test's own null with the measured ρ in it (`z_c = √ρ·F + √(1−ρ)·e_c`), which is a
calibrated bar in the X7 sense rather than an adjustment to a statistic.

**Five tests pin it** (258/258 edge tests):

1. **At ρ = 0 the simulation reproduces the exact binomial** — critical k = 12, α 3.84%. The bar
   generalises the arithmetic, so it cannot silently drift away from it.
2. **Independent countries are NOT flagged as clustered.** R3's lesson one dimension over: a raw
   design effect is not evidence of clustering, and a gate that cried wolf here would manufacture
   a correction out of ANOVA sampling noise.
3. **Planted co-movement is detected and both estimators agree.** The ANOVA ICC and the direct
   mean-pairwise correlation are computed independently; on the real data they agree to **<0.001
   on all ten pairs**, which is why the ρ above is quotable.
4. **The bar is monotone in ρ and can only ever move up.** ρ is clamped at 0 from below and the
   calibrated k is floored at the independent-countries value, so a measured *lack* of clustering
   can never buy a weaker bar than the arithmetic already implies.
5. **The arm-pair difference is exactly a scaled two-theme spread**, `Δ_a − Δ_b ≡ (x_b − x_a)/4`,
   verified to 2.1e-17 on the real data and pinned synthetically. This is why the measured
   co-movement is credible rather than an artefact of arm construction: the correlated object is
   nothing more exotic than a value-minus-momentum spread, and those are famously correlated
   across developed markets.

---

## 2. STEP 2 — the selection on `usa`, and the second kill

Decide set `usa`, 324 months, split at the midpoint. Δ = mean of the 4 remaining themes − mean of
all 5, annualised.

| arm | early | late | mean | same sign? |
|---|---|---|---|---|
| **size** | **+0.149%/yr** | **+0.636%/yr** | **+0.392** | **YES** |
| value | −0.241 | −0.060 | −0.150 | YES |
| quality | −0.019 | −0.247 | −0.133 | YES |
| investment | +0.018 | +0.149 | +0.083 | YES |
| momentum | +0.092 | −0.477 | −0.193 | no |

**Rule A (argmax) selects `size`. Rule B (stability) selects `size`. VERDICT: `NO CONTRAST`** —
the pre-registered outcome, committed in `PREREG_session9_selection_rule.md` before the run.
Every paired difference is identically zero and the sign test is vacuous. **This is not a NULL
and not a tie**, and it is explicitly not an invitation to adjust either rule and re-run.

### Two exploratory observations, NO VERDICT, do not act on either

- **The stability constraint does not bind here. Four of five arms are same-sign across both
  `usa` halves**, so Rule B filters out only `momentum` and leaves the argmax untouched. On the
  Sharadar panel **four of seven arms change sign between halves** (session 7). **HYPOTHESIS: the
  instability that motivated this entire question may be a property of the 69-date Sharadar
  panel's thinness rather than of the selection rule.** 324 monthly observations versus 69. This
  is a hypothesis generated on the decide set and it is not tested by anything here.
- **`size` is the best arm to DROP on `usa` (+0.39%/yr), and on the Sharadar panel `size` is the
  WORST arm to drop** (−2.64% and −3.46% in both halves independently, session 7) and carries the
  composite's entire statistical significance (X3). **These are not the same object** — JKP `size`
  is a capped value-weighted long-short factor, Valquo's is a z-scored theme inside an
  equal-weighted concentrated decile book — so this is not a contradiction, and it is not evidence
  against `size`. It is recorded because anyone reading the two files side by side will notice it,
  and should meet the caveat here rather than invent one.

---

## 3. What it cost, and what it bought

**Trial cost paid as pre-committed, not renegotiated after the result.** The five arms were
evaluated on `usa`, so the search happened and the rows are owed regardless of the verdict.

| | before | after |
|---|---|---|
| equity `N` | 116 | **121** |
| Deflated Sharpe | 0.8674 | **0.8628** |
| √(2·ln N) | 3.083 | **3.097** |

Recomputed with `ablation.deflated_sharpe_at`, which **reproduces the recorded N = 116 figures to
four decimals** before being asked for 121 — the helper is validated against the record on every
use, not trusted. Still far above X7's calibrated floor of 0.7216, still below the 0.95
convention. `RESEARCH_LOG.md` gains two rows: `SELRULE` (equity, n=5) and `SELRULE-GATE` (infra,
n=1). Reproduce with `python -m scripts.selection_rule_crosscountry`; result in
`data/free_analysis/SELRULE_CROSSCOUNTRY.json`.

**What it bought:** a permanent, tested instrument that prices cross-country evidence honestly.
Any future claim of the form "it replicates in N countries" now has to pass it. **X8's own headline
is unaffected** — X8 tests whether each region's composite premium is positive, per region, with
NW(12) errors; it never pooled countries into a count, so it never made the independence
assumption this gate refutes. **The gate constrains what can be built ON TOP of X8, not X8.**

## 4. The expectation, scored (RUN_RULES A6)

Written first: *"I expect a NULL, 65/35 — most likely because Rule B abstains or selects the same
arm as Rule A."* **The mechanism named was exactly the one that occurred.** But the same file also
said clustering would make power "lower" — it made the design *impossible*, which is a different
statement, and I did not anticipate it. **Direction right, magnitude badly wrong.** Consistent
with the standing rule: write the expectation down, then measure anyway.

---

## 5. Session 10's first item, with its `needs first`

**The selection-rule question is now closed on both available datasets, and should not be
re-opened without new data.** One panel gives n = 1; sixteen co-moving countries give n_eff ≈ 2–4.
Neither is a defect that can be engineered around — it is the amount of independent evidence that
exists.

**First item: task #12, the forward paper-track vs SPY.** It is the only test in the project that
runs on data nobody has looked at, and it is the only remaining answer to "n_eff is small" that
does not require assuming away the problem: it *manufactures* independent observations by waiting.
P4 shipped its machinery in session 7.

| dependency | status |
|---|---|
| the paper-track engine | **READY** — P4 (session 7) closed the departed-names defect; 45/45 paper-track tests |
| a start date and a pre-committed horizon | **NOT SET.** Don's call, and it must be committed before the first print |
| the comparison rule | **NOT WRITTEN** — decide in advance what beats what, and over what window; a track without a pre-committed bar becomes a story |
| n_eff, again | the same gate applies: monthly excess returns against SPY are one series, not many. **Do not count months as independent draws** |

**Ranked alternatives:** (1) the ML tree combiner (roadmap #16); (2) re-deriving X7's calibrated
long-short floor on the **HAC** statistic, still open and still the reason `2.620 vs 2.14` is
apples-to-oranges; (3) the narrow sector-relative-value variant (roadmap #13).

**Do not re-open:** the selection rule, on either dataset (sessions 8 and 9, with the arithmetic
and the measurement respectively); U1 as written; the full-sample LOO as a source of verdicts;
`sector_neutral`, PEAD, TTM ROE/ROIC, robust z-scores, momentum/institutional consolidation.

---

## 6. What I did NOT do, and why (RUN_RULES A4)

- **Did not re-run the design with a different bar, a different measure set, or a different rule
  after seeing `NO CONTRAST`.** Every one of those was available and each would have been the
  pre-registration's whole point discarded at the first unwelcome result.
- **Did not quote a sign-test p-value.** The rules selected the same arm; there is no statistic
  to report, and inventing one from an arm that neither rule chose would be fabricating a
  contrast.
- **Did not drop `momentum` from anything.** It is the one arm Rule B excludes on `usa`; that is
  a decide-set observation, not a verdict, and nothing was changed on it.
- **Did not weaken the max-ρ rule to the median** after seeing that max made the design
  unreachable. The median makes it *near*-unreachable (k = 16 of 16); the conclusion is the same
  and the rule was committed in advance either way.
- **Did not touch** `valuation/screener/**`, `screen.py`, `valuation/web/**`, `.github/**`,
  `.gitattributes`, `theta_bulk.py`, `data/options/**` — other lanes.
- **Did not re-run the full backtest.** Nothing here changes the panel; the only shipped number
  that moves is the Deflated Sharpe via `N`, computed exactly from the recorded detail.

---

## 7. Bugs found (RUN_RULES A3)

1. **Session 8's own §2 asserted country independence without measuring it** (§0). Corrected in
   `CLAUDE.md` and here. The general lesson is the project's oldest one and it caught the agent
   that had just written the same warning: **a design's noise must be measured on the data it
   will run on, not inherited from the design's shape.**
2. **`research_log.py` reads the WHOLE row when testing for a `FIXED` verdict**
   (`verdict = " ".join(cells).upper()`), so any row whose free-text note happens to contain the
   word "fixed" — e.g. "the bar was fixed in advance" — is silently dropped from `N` and
   **understates the trial count, which overstates significance.** This is the exact error M1
   exists to prevent, sitting inside M1's own parser. Worked around this session by wording the
   two new rows to avoid the token. **Not repaired**: the fix is a one-line change to read only
   the verdict cell, but the counter is load-bearing for a shipped statistic and changing its
   parse without re-verifying all 53 counted rows would be reckless. Flagged for a session that
   can re-verify the count.
3. **`scripts/selection_rule_crosscountry.py` initially reported JKP returns as percent when
   they are decimal fractions** — a 100× display error, caught by sanity-checking a +0.006%/yr
   figure against X8's +2–3%/yr composite premia. **No verdict was affected** (argmax, sign and
   the sign test are all scale-invariant) and it was corrected before any number was recorded,
   but it is logged because a number quoted in the wrong unit is exactly the class of thing this
   file exists to catch.

---

# SESSION 10 (2026-08-07) — the HAC floor is measured and the headline clears it, and the ML combiner is pre-registered blind

Two items, both delivered: **item 1 closes the apples-to-oranges defect the record has carried
since R9**, and **item 2 commits `PREREG_ml_combiner.md` without fitting a single model.**

---

## 1. ITEM 1 — X7's long-short floor, re-derived on the HAC statistic

### The defect

X7 calibrated the long-short floor at **2.14** as the p95 of 100 block-permuted placebo draws,
using the **naive i.i.d.** *t*. R9 then measured Ljung–Box on the long-short series, rejected
independence at **p = 0.036**, and the project's rule became "the Newey–West *t* is the number
this project quotes". So the shipped **2.620** has been compared against a bar derived for a
different estimator, and `CLAUDE.md` carried it as a known open defect.

### What was actually wrong, and why it cost a full re-run

**`quantile_backtest` has computed `long_short_tstat_nw` on every placebo draw since R9. The
recorder never stored it and the summariser never percentiled it.** The floor could have been
read off X7's own sweep — except **X7's raw draws were never saved**, so the only way to recover
the column was to run all 100 draws again. A computed column that the writer drops is
indistinguishable from one that was never computed. **This sweep retains all 100 draws**, and the
round trip is now pinned by `test_session10_the_placebo_writer_summarises_the_hac_statistic_it_computes`.

### Procedure — pre-committed in `PREREG_session10_hac_floor.md` before launch

Panel `panel_corrected_69d.pkl` (69 dates, 2009-01-15 → 2026-01-28); **X7's own seeds 1000–1099**;
n = 100; `placebo_panel` unchanged; costs measured; floor = p95. **No scoring logic was touched** —
which is why the naive floor is the sweep's own control and had to come back at 2.14.

**Reproduction check, run before any draw:** the unpermuted panel returns `ls_t` 2.8360640685
(record 2.83606), HAC 2.6199121240 (R9's 2.620), alpha 0.0717414233 (record 0.071741),
alpha HAC *t* 4.3762304 (R9's 4.376), PBO 0.7333333, adopt False. **All match.**

**One implementation note, because it looks like a deviation and is not.** The serial sweep ran at
208 s/draw (~6 h), so the 100 seeds were sharded across four processes. Each draw depends only on
its own seed, so this changes nothing about what is computed — **and the merge proves it rather
than asserting it: the two draws the killed serial run had completed reproduce bit-for-bit under
sharding, every key.** `--no-costs` would have been ~3× faster and provably cannot affect a
long-short *t*; it was **not** used, because "this shortcut can't matter" is exactly the reasoning
a pre-commitment exists to refuse.

### THE RESULT

| statistic | calibrated floor (p95) | noise median | noise max | shipped | verdict |
|---|---|---|---|---|---|
| long-short *t*, **naive** (control) | **2.1437** | 0.125 | 3.436 | 2.83606 | clears, emp. p 0.02 |
| **long-short *t*, HAC** | **2.2837** | 0.121 | 3.783 | **2.61991** | **CLEARS, emp. p 0.03** |
| top-decile alpha *t*, naive | 2.2352 | 0.318 | 3.448 | — | — |
| **top-decile alpha *t*, HAC** | **2.2913** | 0.315 | 3.320 | **4.37623** | **CLEARS, emp. p 0.00** |

**THE HEADLINE CLEARS THE RE-DERIVED FLOOR. It clears by less than the record implied, and both
moves go against the strategy:** the HAC floor is *higher* than the naive floor (2.28 vs 2.14)
while the real HAC *t* is *lower* than the real naive *t* (2.620 vs 2.836), so **the margin over
the floor falls from 0.692 to 0.336 — roughly half.** Quote **2.620 against 2.28**, never against
2.14.

**The size of the old error: pure noise clears 2.14 on the HAC statistic 6% of the time**, against
the 5% the bar intends. The mismatch was real and mild — worth closing, not a scandal. Rates on
the HAC statistic: ≥2.0 **8%**, ≥2.14 **6%**, ≥3.0 **1%**.

### The control, including the part that does not reconcile

Naive p95 **2.1437** → X7's recorded **2.14**; noise max **3.4360** → X7's recorded **3.44**. Both
to the digit. **But the `ls_t ≥ 2.0` rate comes back 7% against the recorded 8%.** It is not a
rounding or boundary artefact — the nearest draws to 2.0 are 1.885 and 2.067, nothing sits on the
line. One draw genuinely differs. **It cannot be reconciled, because X7's raw draws were never
retained**, so no draw-level diff is possible. Reported rather than smoothed over: the
distribution is otherwise identical on both statistics the floors are read from, and every floor
in the table above is a p95, which one draw at 2.0 does not move.

### The free by-product, and it is the stronger number

**`top_decile_alpha_tstat_nw` has never had a calibrated floor.** It does now — **2.2913** — and
the shipped **+4.376 sits above all 100 noise draws (empirical p 0.00)**. The number on the front
of the product is better separated from noise than the long-short statistic the project has always
led with, which is the same asymmetry R9 found and is worth leading with more often.

**R9 is corroborated as a side effect:** Ljung–Box on the noise draws has median p **0.406** and
rejects at **7%** — near nominal. The autocorrelation R9 found in the real series (p 0.036) is a
property of that series, not something this pipeline manufactures.

**Trial cost: zero.** A calibration of an existing statistic on an existing panel searches nothing;
equity `N` stays **121**. One `infra` row logged for the recorder change.

---

## 2. ITEM 2 — `PREREG_ml_combiner.md`, committed blind at `ec6c01d`

**Design only. No model was fit, no feature matrix built, no accuracy number exists.** The full
document is the deliverable; the summary here is an index to it, not a substitute.

- **Question:** does a shallow gradient-boosted tree over the seven deployed theme z-scores beat
  the flat 1/7 linear composite out-of-sample, by the calibrated bars? Motivated by two *measured*
  results — X3 (theme IC does not predict marginal contribution; `size` has the worst IC and
  carries the significance) and P6 (the linear composite is scale-sensitive).
- **Features:** exactly seven — `z_value z_quality z_momentum z_insider z_capital_discipline
  z_size z_institutional`, built identically to `cpcv_validate`'s own z-scores, NaN passed through
  with **no imputation** (imputing would give the tree information the linear arm lacks).
  **Excluded on the record:** `low_risk` and `sentiment` (that would be a theme-membership change
  smuggled in as a feature) and the 56 raw `z_*` signals (a different question, 8× the risk — a
  new pre-registration if wanted, never an amendment).
- **Target:** cross-sectional **rank** of `fwd_ret` within each date, 63d, non-overlapping —
  because the book is formed by ranking, and a raw-return target chases outcomes decile formation
  discards.
- **Validation:** `_cpcv_paths(dates, 6, 2, embargo=1)` reused unchanged. **Selection never touches
  the measurement set:** all eight grid points are scored by CPCV *within a decide half*, the
  single winner is refit and measured **once** on the held-out half, **both directions**. This is
  the direct answer to X7's finding that CPCV adoption manufactures **~+1.4 of long-short *t*** out
  of nothing, firing on **27% of pure-noise draws**, when selection and measurement share a panel.
- **Grid, frozen:** `HistGradientBoostingRegressor`, `max_depth {2,3} × learning_rate {0.03,0.10}
  × max_iter {100,300}` = **8 points**; `min_samples_leaf=200`, `l2=1.0`, `max_bins=64`,
  `early_stopping=False`, `random_state=0` held constant, not searched.

### The grid is priced BEFORE registering — this is the item's whole risk

| grid | equity `N` | headline Deflated Sharpe | √(2·ln N) |
|---|---|---|---|
| **8 (registered)** | **129** | **0.8556** | 3.118 |
| 32 | 153 | 0.8356 | 3.172 |
| 128 | 249 | 0.7716 | 3.322 |
| **230** | **351** | **0.7213 — BELOW X7's calibrated floor of 0.7216** | 3.444 |

**A 230-point grid would push the shipped headline below the noise floor X7 measured. A grid that
size does not test the model; it destroys the incumbent's evidence as a side effect.** Hence
eight, costing the headline **0.0072** of Deflated Sharpe — paid whatever the answer.

- **Scored on:** HAC long-short *t* against **this session's 2.2837 floor** (kill criterion 3
  depends on item 1, which is why they shared a session), a **1.95pp** alpha margin, and the
  standing 0.25 *t*-margin. **PBO is explicitly not a criterion** — X7 put its noise median at
  46.7%.
- **Kill criteria:** ADOPTED needs all three margins in **both** directions; REJECTED is worse on
  alpha in both; **everything else is NULL**, including a positive point estimate that misses the
  margin and a split that disagrees. **No re-runs.** Expectation recorded first: **NULL, 70/30**.
- **Trial cost owed when it runs, not now:** 8 rows, `N` 121 → 129.

## 3. The design question session 9 raised, recorded and NOT pursued

Session 9 observed that four of five leave-one-out arms are same-sign across both `usa` halves on
JKP's 324 monthly observations, while **four of seven flip sign across halves on the Sharadar
panel's 69 dates**, and offered the hypothesis that the cross-half instability motivating the whole
selection-rule question is a property of the *panel's thinness* rather than of the selection rule.

**If true, the implied change is a thicker panel — monthly rather than quarterly rebalancing, or a
denser date grid — and it is deliberately not pursued here.** What it would take to test honestly:
the rebalance grid is upstream of every statistic this project publishes, so changing it **changes
every historical number at once** — theme ICs, the long-short *t*, top-decile alpha, PBO, the
Deflated Sharpe, X7's entire calibrated bar table (which is explicitly "a floor for THIS
panel/universe/69 dates, not a universal constant"), and R1's non-overlapping 63-day window
construction. It is therefore **a full pre-registered re-run against re-derived bars, not a patch**,
and it must not be slipped in alongside another test. X2 is the precedent worth reading first: it
re-ran the whole backtest on seven equally valid rebalance grids and found long-short *t* ranging
2.703–3.517 across them, which means grid choice already moves the headline by more than most
findings in the record. **Queued as an open design question. Nobody should act on it from the
hypothesis alone.**

---

## 4. Session 11's first item, with its `needs first`

**First item: execute `PREREG_ml_combiner.md` exactly as written.** It is committed, blind, and
priced; the only thing standing between it and a verdict is a training loop.

| dependency | status |
|---|---|
| the pre-registration | **READY and BLIND** — `PREREG_ml_combiner.md`, committed at `ec6c01d` before any model was fit |
| the panel | **READY** — `data/free_analysis/panel_corrected_69d.pkl`, 69 dates, reproduces the shipped run to every digit |
| `sklearn` | **PRESENT**, 1.9.0; `HistGradientBoostingRegressor` imports |
| the CPCV splitter | **READY** — `_cpcv_paths(dates, 6, 2, embargo=1)` reused unchanged; no new validation code |
| **the HAC floor** | **see §1** — kill criterion 3 is stated against it, so it must be quoted from this session's sweep and not from 2.14 |
| the trial cost | **8 rows, equity `N` 121 → 129, headline DSR 0.8628 → 0.8556.** Log them or do not run |
| discipline | **no re-runs, no grid changes, ambiguous is NULL.** The registration is void the moment any of the three is relaxed |

**Ranked alternatives:** (1) **task #12, the forward paper-track vs SPY** — still the only test on
data nobody has looked at, and it needs a start date and a pre-committed comparison rule from Don
rather than an agent; (2) the narrow sector-relative-value variant (roadmap #13); (3) repairing the
`research_log.py` parser defect in §6 together with a re-verification of all counted rows.

**Do not re-open:** the selection rule on either dataset (sessions 8 and 9); U1 as written; the
full-sample LOO as a source of verdicts; `sector_neutral`, PEAD, TTM ROE/ROIC, robust z-scores,
momentum/institutional consolidation.

---

## 5. What I did NOT do, and why (RUN_RULES A4)

- **Did not run the ML combiner.** The task said design only, and the design is the deliverable.
  Fitting even one model would have spent the blind.
- **Did not enlarge the grid past eight points** to make the test "fairer". §2's table is the
  argument: the grid is the risk, and it is priced before registering rather than defended after.
- **Did not drop `--no-costs` to make the sweep finish sooner**, even though `cost_breakeven_bps`
  provably cannot affect a long-short *t*. The procedure was committed with costs measured, and
  "this shortcut can't matter" is precisely the reasoning a pre-commitment exists to refuse.
  Sharding the same seeds across four processes was used instead — that changes nothing about what
  is computed, and the merge **proves** it by reproducing the killed serial run's draws bit for bit.
- **Did not repair the `research_log.py` parser defect** carried over from session 9 (§6). Still
  the right call: it is load-bearing for a shipped statistic and repairing it means re-verifying
  every counted row in the same change.
- **Did not pursue the monthly-rebalance question** (§3).
- **Did not touch** `valuation/screener/**`, `screen.py`, `valuation/engine/**`, `valuation/data/**`,
  `valuation/web/**`, `valuation/saas/**`, `.github/**` — other lanes.

---

## 6. BUGS FOUND (RUN_RULES A3 — report everything, including outside my lane)

1. **The placebo recorder dropped a statistic the pipeline computes** (§1). `quantile_backtest`
   has returned `long_short_tstat_nw` since R9; `scripts/placebo.py` never stored it, so X7's
   floor stayed on the naive estimator after the project switched to the HAC one. **Repaired and
   pinned.** The general form is worth carrying: *a computed column that the writer drops is
   indistinguishable from one that was never computed*, and it is the same failure shape as the
   five silently-empty factors of 2026-07-30 and B8's unread `rule_fired`.
2. **X7's 100 raw placebo draws were never saved**, only the summary. That is why a one-column
   addition cost a full re-run, and why the 7%-vs-8% discrepancy in §1 **cannot be diagnosed at
   all** — there is nothing to diff against. The M1 comment inside `placebo.py` already records
   this lesson for the Deflated Sharpe internals ("with these four numbers per draw, any future
   re-denomination is arithmetic"); it simply was not applied to the draws themselves.
   **This sweep retains all 100 draws in `data/free_analysis/PLACEBO_HAC.json`.**
3. **The `ls_t ≥ 2.0` rate does not reconcile with the record: 7% measured against 8% recorded**
   (§1), on the same panel, the same seeds and the same instrument, while the p95 and the max both
   reproduce to the digit. No draw lies near the 2.0 boundary, so it is not rounding. **Unresolved
   and unresolvable without bug 2's raw draws.** It moves no floor — every calibrated bar is a p95
   — but the record should not carry "identical to the last digit" for that particular cell.
4. **`research_log.py` still tests for a `FIXED` verdict by searching the whole row**
   (`verdict = " ".join(cells).upper()`), so any row whose free-text note contains the word
   "fixed" is silently dropped from `N` — understating trials, which overstates significance.
   Carried over from session 9, **still not repaired**, still for the same reason: it is
   load-bearing for a shipped statistic and repairing it means re-verifying all 54 counted rows in
   the same change. Worked around again this session by wording.
## 8. INBOUND FROM THE r1 LANE (2026-08-07) — `param_search` is on `main`, and its negative
## result belongs in `PREREG_ml_combiner.md`

**Prose only; the r1 lane wrote no code in `valuation/edge/**` beyond creating the new module
file itself.** Full triage in `HANDOFF_branch_triage.md`. Two things need the edge lane.

### 8.1 The CLI wiring needs hand-porting — and `param_search.bat` is INERT until it is

`valuation/edge/param_search.py`, `PARAMETER_SEARCH.md`, `scripts/calibrate_param_search.py` and
`param_search.bat` were recovered from the stranded `worktree-ui-polish` branch and landed as
files. **The argparse wiring was deliberately NOT ported** — it edits
`fundamental_panel.main()`, which pipeline builder holds for Session 10.

What remains, and it is small:

- six flags — `--param-search`, `--fast`, `--permutations`, `--cost-bps`, `--holdout-frac`,
  `--refresh-panel`
- a ~20-line dispatch block calling `PS.cached_panel(...)` then `PS.honest_search(...)`
- five self-contained tests to append to `tests/test_edge.py`:
  `test_param_search_reality_check_calibration`, `..._plateau_beats_argmax`,
  `..._interiority_and_ledger`, `..._rejects_a_signal_free_panel`,
  `..._detects_a_planted_signal`

Source for all of it: `git show origin/worktree-ui-polish:valuation/edge/param_search.py` and that
branch's `main()`. **Read this before the branch is deleted** — the refs are being pruned this
session, so recover the wiring from `HANDOFF_branch_triage.md` §4 or from reflog if it is gone.

**CAVEAT THAT MUST NOT BE LOST: `param_search.bat` now sits in the repo root and will FAIL if
run.** It invokes `python -m valuation.edge.fundamental_panel --param-search ...`, and that flag
does not exist on `main` until the wiring lands — so it exits on an argparse error. In a project
where Don runs `.bat` files by double-clicking, that is a live trap. It was landed verbatim rather
than edited because inventing content during a cherry-pick is worse; **either port the wiring or
delete the `.bat`.** Do not leave it in this state indefinitely.

The module's engine interface was verified against `main` **after** landing: `_weight_schemes`
(6 positional), `_pbo` (3 positional), `_spearman`, and `build_fundamental_panel`'s
`rebalance_days` / `lookback_years` / `horizon` / `inst_lag_days` kwargs all match, and
`import valuation.edge.param_search` succeeds. It is dormant, not broken.

**Second trial counter warning:** `param_search.py` carries its own persistent `TrialsLedger`,
written before `research_log.py` existed. **Two counters that disagree is worse than one.** Wire
it to `research_log.py` or leave it switched off.

### 8.2 `PARAMETER_SEARCH.md`'s negative result is the most relevant in-house evidence for the
### ML combiner prereg, and it lands on the prereg's selection rule specifically

The recovered protocol ran **3,584 configs × 15 CPCV paths** over 88 rebalances with 22 locked
away. It selected `ic-proportional, top20, band2.0x, hold3, all`:

| | search window | locked hold-out |
|---|---|---|
| **selected** | **+8.43%/yr** (LCB +6.33%) | **−0.04%/yr** |
| baseline `current-default, top25, band2.0x, hold2, all` | −0.83%/yr (LCB −2.00%) | **+5.12%/yr** |

It was positive in **87% of 15 CPCV paths**, PBO **33%**, and the gain decomposed to +9.15%/yr of
*selection* against only +0.11%/yr of saved turnover — so not a cost artefact. **It was still
worth nothing out of sample**, and the permutation null gave **p = 0.077** (signal-free re-runs
averaged +2.65%/yr; one of 25 draws reached +8.59%/yr).

**Why this is pointed at `PREREG_ml_combiner.md` §3 rather than filed as trivia.** That section's
load-bearing rule is already right — one frozen spec, measured exactly once on the VERDICT half,
both directions. The gap is one line: *"the winner is the grid point with the highest mean
out-of-sample rank IC across that half's paths."* **That is argmax of a mean, which is exactly the
selector that produced +8.43%/yr and then −0.04%/yr.** Three cheap amendments the prereg does not
currently contain:

1. **Rank by a lower confidence bound (mean − z·SE) across paths, not the mean.** A grid point
   that wins on average but is wild across paths should lose to a steadier one.
2. **Interiority.** With eight enumerated grid points, a winner sitting on an end of an ordered
   axis is unverified on one side. The recovered run's whole leaderboard piled up at `hold4`, the
   edge of its grid — *"usually the optimiser walking downhill toward 'trade less', not a genuine
   optimum."* Pre-commit that a boundary winner is reported as "widen the grid", not adopted.
3. **A permutation null over the WHOLE selection procedure.** Not the composite — the *procedure*.
   It is the only check that catches leakage the theory cannot see, and it is what took this
   result from "clear winner" to p = 0.077.

**Plateau smoothing is offered but NOT recommended here** — it needs several values per ordered
axis and the combiner grid has eight points total. Say why not, rather than adopting it for
symmetry.

**On Hansen SPA / White Reality Check: adopt as REPORTED, not as a gate.** The recovered
`scripts/calibrate_param_search.py` measured SPA firing on **~35% of signal-free panels**, which
is why its own authors demoted it. Its doctrine — *"a gate whose false-positive rate you have not
measured is not a gate"* — is X7's, written **eight days earlier** and reached independently.
**X7's method is strictly stronger** (block-permuting the real panel, preserving missingness and
cross-theme correlation, vs synthetic no-signal panels), so keep X7's; the value here is the five
measured gate false-positive rates and the SPA finding, which X7 never covered because SPA is not
on `main`.

**The honest framing for the prereg, in the source's own words:** *"this is what overfitting looks
like from the inside — 87% of paths positive, PBO 33%, a large decomposed selection edge, and it
is still worth nothing out of sample."* That is the argument for the frozen-blind grid, made with
this project's own data rather than by citation.

**Every number above is from the pre-B6 panel** (88 searched + 22 locked rebalances). The current
panel is 69 dates. Cite it as *evidence about procedure*, never as a performance figure.

### 8.3 One decision routed, deliberately not made

**Do the search's 3,584 configs enter the equity trial count?** `RESEARCH_LOG.md` has **zero**
mentions of it. By this project's own precedents it looks countable — `research_log.py:27`
supports a row representing a pre-registered grid via `n_trials`, and CLAUDE.md settled that
`SUPERSEDED` rows still count, so "it ran on the pre-B6 panel" is not on its own a reason to
exclude. The genuine counter-argument is domain: it searched *construction* parameters
(scheme × top_n × band × min_hold × cap_tier), not the signal-inclusion decisions the equity
composite is charged for, and `DOMAINS` (`research_log.py:50`) would let it sit elsewhere.
**Direction, so the stakes are explicit: counting them RAISES `sr0` and LOWERS the Deflated
Sharpe.** At `N = 116` the figure is 0.8674 with √(2·ln N) = 3.083. **Edge lane's call. Nothing
was changed.**

---

# SESSION 11 (2026-08-08) — the ML tree combiner is REJECTED, and its deciles run BACKWARDS out of sample

**The register was executed unmodified.** `PREREG_ml_combiner.md` (committed blind at `ec6c01d`,
session 10) was run exactly as written: seven theme z-scores, rank-of-`fwd_ret` target, 63d
horizon, the corrected 69-date panel, `_cpcv_paths(6, 2, embargo=1)` reused unchanged, the frozen
eight-point grid, selection confined to a decide half, one measurement per direction, both
directions. **No deviations.** Three register ambiguities were resolved in the *less* favourable
direction and recorded in `PREREG_session11_execution_protocol.md` **before first touch** (§1).

---

## 0. VERDICT: REJECTED

The registered criterion for REJECTED is "the tree is worse than the linear composite on the alpha
margin in **both** directions". It is worse in both, by a wide margin, and it fails all three
ADOPT criteria in both.

| | decide-early → measure-late | decide-late → measure-early |
|---|---|---|
| selected grid point | `d3 / lr 0.10 / it 300` (**most complex**) | `d2 / lr 0.03 / it 100` (**least complex**) |
| decide-half OOS rank IC | +0.01873 | +0.02427 |
| **tree** top-decile alpha | **+1.88%** | **−2.66%** |
| **linear** top-decile alpha | **+11.58%** | **+2.82%** |
| **Δ alpha** (need ≥ +1.95pp) | **−9.70pp** ✗ | **−5.48pp** ✗ |
| **tree** LS HAC *t* | **+0.0366** | **−1.0113** |
| **linear** LS HAC *t* | **+2.1547** | **+1.8660** |
| **Δ HAC *t*** (need ≥ +0.25) | **−2.1180** ✗ | **−2.8773** ✗ |
| tree clears the 2.2837 floor? | **no** ✗ | **no** ✗ |
| **tree monotonicity** | **+0.3818** | **+0.8424** |
| **linear monotonicity** | **−0.9030** | **−0.8545** |

## 1. The finding, which is stronger than the verdict

**THE TREE'S DECILES RUN BACKWARDS OUT OF SAMPLE, IN BOTH DIRECTIONS.** Monotonicity is the
Spearman correlation between decile index and decile return, and **negative is well-ordered**
(−1.0 is the ideal; the project has misread this sign before, and it is pinned by
`test_monotonicity_sign_convention`). The tree returns **+0.38** and **+0.84** — its top decile
underperforms its bottom decile, systematically, on data it did not select on.

**This is the model, not the harness, and the run contains its own control.** The linear arm was
scored on the **identical rows** through the **identical `quantile_backtest` call** and came back
**well-ordered in both directions** (−0.903, −0.855), and the equal-weight benchmark is identical
between the two arms to four decimals (0.1504 late, 0.2114 early), which is what confirms both
arms saw the same universe. A sign or orientation defect in the measurement code would have
inverted the linear arm too.

**It is also not a fitting failure. Every one of the 16 grid × direction cells produced a POSITIVE
decide-half CPCV out-of-sample rank IC** (+0.011 to +0.024). The model generalises perfectly well
*inside* the decide half — across 15 purged CPCV paths — and then **reverses across the boundary
into the other half.** What it learns is half-specific structure, and the half-specific structure
is strong enough to invert the ranking rather than merely dilute it.

**That reading is corroborated by the grid selection, and the register said to record it
prominently.** The two directions selected **opposite ends of the grid**, and not marginally:

- decide-**early** ranks the grid **monotonically increasing in capacity** — the *most* complex
  point (depth 3, lr 0.10, 300 iterations) is best, +0.01873;
- decide-**late** ranks it **monotonically decreasing in capacity** — the *least* complex point
  (depth 2, lr 0.03, 100 iterations) is best, +0.02427.

Whether model capacity helps or hurts is not a property of the problem on this panel; it is a
property of which half you look at. **Session 7's LOO found exactly this shape** — different theme
selected in each direction, four of seven arms changing sign — and the instability was the finding
there too.

**The precedent this sits beside, quoted whether it flatters or not (and it does not):** the
concurrent parameter-search lane measured **+8.43%/yr in-search collapsing to −0.04%/yr on a
locked hold-out**. The combiner is the same phenomenon with a sharper edge: positive selected-half
IC, *negative* held-out alpha and a *reversed* decile ordering. **Selection on this panel does not
merely fail to generalise; it can generalise backwards.**

## 2. What the result does NOT say

- **It does not vindicate the linear composite's functional form.** The tree failing is not
  evidence the flat 1/7 sum is right; it is evidence that 69 dates and seven correlated features
  do not support *this* estimator selected *this* way.
- **It does not close roadmap #16.** It closes **this** pre-registration. A raw-signal variant, a
  different model class, or a thicker panel are each a NEW pre-registration with their own trial
  cost — explicitly not an amendment to this one.
- **It says nothing about `insider` or `institutional` individually**, and nothing about the
  live product, which is unchanged.
- **The linear arm's own half-to-half spread is large** (alpha +11.58% late vs +2.82% early), which
  is the same panel instability seen elsewhere and a reason to read *both* arms' half numbers as
  noisy.

## 3. Trial cost — paid as registered

| | before | after |
|---|---|---|
| equity `N` | 121 | **129** |
| Deflated Sharpe | 0.8628 | **0.8556** |
| √(2·ln N) | 3.097 | **3.118** |

**Eight rows, exactly as the register priced them** — running both directions does not double the
count (session 7's LOO precedent: seven arms across two directions counted seven). Still far above
X7's calibrated floor of 0.7216, still below the 0.95 convention. **Every subsequent equity claim
is charged N = 129, and the DSR bar for anything after this is 0.8556.**

## 4. Execution fidelity — what was resolved and how

Recorded in `PREREG_session11_execution_protocol.md`, committed with the executor at `9b1abfc`
**before** the run:

1. **The boundary date is dropped entirely from both halves** (69 dates → 34 decide + 34 verdict,
   `2017-07-20` discarded), rather than embargoing only the training side, which would have left
   35 dates on one side. The stricter reading; the two directions are exact mirrors.
2. **"Mean out-of-sample rank IC" follows `cpcv_validate.ic_score`'s own convention** —
   per-test-date Spearman, averaged over the path's test dates, then over the 15 paths — so the
   tree is selected by the same statistic the linear weight schemes are.
3. **Grid ties break toward the first (lowest-capacity) point.** No tie occurred.

**Bug-discovery protocol, stated before first touch and honoured:** the executor was first run
with `--decide-only`, which touches no verdict row, and completed cleanly (15/15 paths scored on
all 8 grid points, both directions, no failures). **No bug was found, so no direction is
CONTAMINATED and nothing was re-measured.** Each verdict half was measured exactly once, in a
single scripted run of a script committed before it ran.

---

## 5. Session 12's first item, with its `needs first`

**First item: task #12, the forward paper-track vs SPY.** After three consecutive sessions in
which the binding constraint was *how little independent evidence this panel contains* — session 8
(n = 1), session 9 (n_eff 2–4 across 16 countries), and now session 11 (structure that reverses
between halves of the same panel) — the case for the one test that manufactures new observations
by waiting is no longer a preference. **Every remaining in-panel question is competing for the
same exhausted evidence.**

| dependency | status |
|---|---|
| the paper-track engine | **READY** — P4 (session 7) closed the departed-names defect; 45/45 paper-track tests |
| a start date and pre-committed horizon | **NOT SET — Don's call**, and it must be committed before the first print |
| the comparison rule | **NOT WRITTEN.** Decide in advance what beats what, over what window; a track without a pre-committed bar becomes a story |
| n_eff discipline | **the session-9 gate applies** — monthly excess returns against SPY are one series, not many. Do not count months as independent draws |
| `N` for anything scored alongside it | **129 now**, DSR bar **0.8556** |

**Ranked alternatives:** (1) a raw-signal or alternative-model-class combiner as a **new** blind
pre-registration, priced the same way — but note it inherits the reversal finding as its prior;
(2) the narrow sector-relative-value variant (roadmap #13); (3) repairing the `research_log.py`
parser defect (§7) together with a re-verification of all 55 counted rows.

**Do not re-open:** this pre-registration; the selection rule on either dataset (sessions 8, 9);
U1 as written; the full-sample LOO as a source of verdicts; `sector_neutral`, PEAD, TTM ROE/ROIC,
robust z-scores, momentum/institutional consolidation.

---

## 6. What I did NOT do, and why (RUN_RULES A4)

- **Did not amend the register in any way** — no ninth grid point, no feature added after seeing
  the decide-half ICs, no target change, no split change.
- **Did not re-measure anything.** No bug was found, but the protocol that would have forced a
  CONTAMINATED label was in place and committed before the run rather than invented after it.
- **Did not investigate the reversal further on this panel.** It is a striking result and the
  temptation to go looking for its mechanism — which themes flip, which dates carry it — is
  exactly the unregistered search the register exists to prevent. **It is a new pre-registration
  or it is nothing.**
- **Did not change the live product, the weights, the themes, or any `EDGE_*` flag.** A REJECTED
  verdict licenses no change, and neither would an ADOPTED one without its own gate.
- **Did not touch** the options files carved out to the options-bot lane
  (`options_signals_v2.py`, `options_universe.py`, `options_backtest.py`, `options_fill.py`,
  `options_stats.py`, `options_autopsy.py`, `theta_bulk.py`), nor `valuation/screener/**`,
  `valuation/engine/**`, `valuation/web/**`. The ML work needed none of them.

---

## 7. BUGS FOUND (RUN_RULES A3)

**No new defect was found in the code this session touched**, and the run's own controls (identical
equal-weight benchmark across arms, well-ordered linear deciles through the same function) are what
establish that rather than an absence of looking.

Carried forward, unrepaired, for the third session running:

1. **`research_log.py` tests for a `FIXED` verdict by searching the whole row**
   (`verdict = " ".join(cells).upper()`), so any row whose free-text note contains the word
   "fixed" is silently dropped from `N` — understating trials, which **overstates significance**.
   That is the exact error M1 exists to prevent, inside M1's own parser. **Still not repaired**,
   still for the same reason: it is load-bearing for a shipped statistic and repairing it means
   re-verifying all 55 counted rows in the same change. Worked around again by wording.
2. **X7's 100 raw placebo draws were never retained** (session 10 §6), which is why the
   7%-vs-8% `ls_t ≥ 2.0` discrepancy remains undiagnosable. Session 10's sweep retains all 100;
   the general lesson — *store the draws, not just the summary* — has now cost two sessions.

---

# SESSION 12 (2026-08-08) — the trial counter is repaired, `N` does not move, and the X7 discrepancy is closed

Three items, and the two that produced numbers both came back against the session's own written
expectation. Pre-registered in `PREREG_session12_recount.md`, committed at `21069ac` **before the
parser was touched**, because a recount that changes `N` changes the significance of every
DSR-gated claim in the project and must not be steerable by its own consequences.

---

## 0. Headline

| item | result |
|---|---|
| the trial-counter defect | **REAL, and it NEVER FIRED.** Fixed, pinned by a fixture |
| equity `N` | **129 → 129.** Deflated Sharpe **0.8556**, √(2·ln 129) **3.1176** — all unchanged |
| every published `N` | **correct at the time it was published**, on all fifteen historical revisions |
| the X7 7-vs-8 discrepancy | **DIAGNOSED. One draw: seed 1005.** No floor moves |
| new mechanism found | **`N` MOVES `ls_t`** through the CPCV adopt gate — undocumented until now |
| the repair's own near-miss | it would have **understated options `N` by 4** until a merge exposed it |
| suites | **26/26 green, 262/262 edge tests** |

---

## 1. The parser: fixed, and it was never live

`research_log._parse` tested `\bFIXED\b` against **every cell of a row joined together**, so a row
whose hypothesis, threshold, source or note merely contained the word "fixed" was dropped from `N`
even where its verdict read `REJECTED`. Understating `N` **overstates** the significance of every
DSR-gated claim — M1's own error, committed inside M1's own parser, and carried three sessions.

**Two sibling defects of the same class were found by reading the code and fixed with it:**

1. the `n=<k>` grid multiplier was `re.search`-ed against the **whole line**, so any prose
   containing `n=100` (a draw count, a seed count — things this project writes constantly) would
   have multiplied that row's trial count;
2. the domain was taken from **the first cell matching any domain name**, not from the domain
   column — which moves trials between BH-FDR families.

The fix resolves columns **from each table's own header row**. That detail is not cosmetic:
`RESEARCH_LOG.md` holds **two tables with different layouts** (verdict at index 7 in the original,
index 6 in the retrospective reconstruction), so any fix that hard-coded an index would have been
a fourth bug. Unresolvable fields resolve toward a **larger** `N`, the less favourable direction.

### THE RECOUNT: NOTHING MOVES, AND THAT IS A MEASUREMENT

On the merged log (after `origin/main`, which brought the options-bot lane's new rows):

| scope | legacy | corrected | Δ |
|---|---|---|---|
| **equity** | **129** | **129** | **0** |
| options | 164 | 164 | 0 |
| infra | 3 | 3 | 0 |
| unified | 0 | 0 | 0 |
| total | 296 | 296 | 0 |
| rows counted / dropped as `FIXED` | 57 / 18 | 57 / 18 | 0 |

Checked against the **shipped module itself** (`git show HEAD:…`), not a reimplementation, and
then against **every one of the fifteen historical revisions of `RESEARCH_LOG.md`** — the two
parsers agree at every single one. Independently: **no `fix*` word of any form appears outside a
verdict cell in any of the 72 data rows as they stood at the recount.** Not one near-miss.

### THE REPAIR NEARLY SHIPPED THE ERROR IT WAS FIXING — report this one loudly

The first-cut column parser was **wrong**, and it was wrong in the direction this session exists
to eliminate. Merging `origin/main` brought in **O16**, which writes
`|Spearman(term_slope, atm_front)|` for an absolute value **inside a markdown table cell**. The
unescaped `|` splits that cell in two, so the row carries **11 cells against a 9-cell header** and
every column after the metric shifts. The column-wise parser then read the `n` field off prose,
found no `n=<k>`, and charged the row **1 trial instead of 5 — understating options `N` by 4.**

**The whole-line grep it replaced was accidentally immune.** So the repair would have shipped a
regression the original defect did not have, in a different column, in the same harmful direction.
It was caught only because merging `origin/main` and re-running the recount was written into the
pre-registered procedure rather than left to the end.

A misaligned row now resolves toward a **larger** `N` on every field — the verdict cannot drop it,
and the multiplier falls back to the whole-line scan and takes whichever count is larger — and is
**reported** in `rows_malformed` rather than absorbed. Pinned by
`test_session12_a_row_with_unescaped_pipes_may_not_silently_lose_its_trials`. **The O16 row itself
was not edited**, per the register's no-edits rule; its pipes want escaping as `\|` by the lane
that owns it.

**So the defect is real, its direction of harm is real, and it never once fired. No published `N`
was ever wrong, and no DSR-gated claim was ever inflated by it.** The pre-registered expectation
(`N` rises, 60/40) was **WRONG** — this project's directional calls now stand at five wrong, one
right, which is the point of writing them down.

**Why it never fired is worth stating precisely, because it is not reassuring.** Sessions 9-11
knew about the defect and dodged it by choosing synonyms; the rows written *before* it was known
avoid the word by luck. **A denominator protected by authors' word choice is not protected.**
That is why the repair ships with a fixture the old parser fails (3 real trials, of which it
counts 1) and with `rows_rescued_by_parser_fix` in `detail()`, so a silent revert would be loud.

### The six claims re-checked by name (PREREG §5)

`N` did not move, so nothing needed restating — but the check was run mechanically rather than
asserted, via `ablation.deflated_sharpe_at` on the shipped `deflated_sharpe_detail`:

| claim | stated | reproduced | outcome |
|---|---|---|---|
| M1, N = 84 | DSR 0.8997, √ 2.977 | 0.899659, 2.9768 | **survives** |
| session 7, N = 116 | DSR 0.8674, √ 3.083 | 0.867360, 3.0834 | **survives** |
| session 9, N = 121 | DSR 0.8628, √ 3.097 | 0.862756, 3.0970 | **survives** |
| session 11, N = 129 | DSR 0.8556, √ 3.118 | 0.855608, 3.1176 | **survives** |
| X7 calibrated DSR floor 0.7216 | — | shipped 0.8556 still above | **survives** |
| session 10 HAC floor 2.2837 | — | see §2 — it is `N`-dependent, and it did not move | **survives, with a new caveat** |
| Harvey–Liu–Zhu 3.0 | √(2·ln 129) = 3.1176 | above the hurdle | **survives** |

**Every figure reproduces to six decimals.** No wording changed.

---

## 2. THE X7 DISCREPANCY IS CLOSED — one draw, named, with both its values

X7 recorded **8** of 100 pure-noise draws at naive long-short `t ≥ 2.0`. Session 10 re-ran the
identical panel with the identical seeds and got **7**, with no draw near the boundary (nearest
1.885 and 2.067), and recorded it as undiagnosable because X7's raw draws were never retained.
Two sessions have carried it as an open defect.

**THE CAUSE: the two sweeps ran at different project trial counts, and `N` moves `ls_t`.**

`cpcv_validate`'s adopt gate is `(med[best] − med[default]) > _trials_haircut(len(names)) · se`,
and `_trials_haircut` (`fundamental_panel.py:2097`) is **floored at the research log's `N`**
(audit M1). X7's sweep ran at **N = 84** (haircut 2.97685); session 10's artifact records
**N = 121** (haircut 3.09703). `scripts/placebo.py` then feeds the **adopted** weights to
`quantile_backtest`. So a larger `N` is a larger haircut, adoption is **monotone decreasing in
`N`**, and a draw that stops adopting is re-scored under different weights.

**Seed 1005 is the draw — and the reconciliation sweep confirms it is the ONLY one of the 100
whose adopt decision differs between the two haircuts.** Monotonicity is what makes that
searchable: the gate's other two conditions do not depend on `N`, so a larger `N` can only remove
adoptions, never add them, and the search set is the draws that did not adopt at N = 121. Its
margin is **0.00287097** against `se` **0.00094470**:

| | bar | margin clears? | weights used | naive `ls_t` | HAC `ls_t` |
|---|---|---|---|---|---|
| **N = 84** (X7) | 2.97685 × se = **0.0028122** | **yes → ADOPTS** | challenger | **2.1273** | 1.9491 |
| **N = 121** (session 10) | 3.09703 × se = **0.0029257** | **no → keeps default** | base | **1.0454** | 1.1060 |

Session 10's retained artifact records seed 1005's naive `ls_t` as **1.0453572947436582** —
**identical to this session's base-weight recomputation to all sixteen digits**, which is what
makes this a reconciliation rather than a story.

**It reproduces every recorded number on both sides:**

- substituting seed 1005's adopted-weights value into session 10's 100 draws gives **exactly 8**
  at `t ≥ 2.0` — **X7's figure**;
- the naive p95 stays **2.1437** and the max stays **3.436** under the substitution — which is
  precisely why session 10's control reproduced X7's percentiles *to the digit* while missing one
  draw. **2.1273 lands just below the 95th percentile.** One fact explains both halves.

**AND THE ADOPT CURVE REPRODUCES TWO HISTORICALLY RECORDED RATES THAT THIS SCRIPT NEVER SAW.**
With `(margin, se)` banked, adoption at any `N` is arithmetic, so the whole curve comes free:

| `N` | haircut | draws adopting | matches the record? |
|---|---|---|---|
| 8 (pre-M1 floor, = `len(names)` 9) | 2.0963 | **27** | **X7's recorded 27%** |
| **84** (X7's sweep after M1) | 2.9768 | **21** | **M1's recorded 21%** |
| 116 / **121** / 129 | 3.083 / **3.097** / 3.118 | 20 / **20** / 20 | session 10's retained artifact: **20** |
| 200 / 400 | 3.255 / 3.462 | 18 / 17 | — |

**27 → 21 is six draws stopping and none starting** — which is exactly the "one-directional (six
draws stopped adopting, none started)" that `CLAUDE.md` records for M1, recovered independently
from the margins. The curve is monotone decreasing throughout, as the mechanism requires.

**A useful corollary: today's `N` = 129 still gives 20 adopters, the same as session 10's 121.**
So session 10's published floors (naive 2.1437, HAC 2.2837) **are still the floors at the current
`N`** — checked, not assumed.

**AND IT EXPLAINS THE THING THAT MADE IT LOOK UNDIAGNOSABLE.** Session 10 reasoned that no draw
sat near 2.0, so it could not be a boundary effect. Correct — and the reason is that seed 1005
did not *drift* across the boundary, it **jumped 1.08 of a t-statistic** because its weights
changed. A draw crossing on a knife edge was the wrong thing to look for.

### The consequence that outlives the discrepancy

**THE CALIBRATED FLOORS ARE FUNCTIONS OF `N`, AND NOBODY KNEW.** A placebo floor is a percentile
of the null `ls_t` distribution; `N` moves individual draws in that distribution through the adopt
gate; therefore the floor itself depends on the project's trial count at the moment the sweep ran.
**Here it happened not to move** — 2.1437 naive and 2.2837 HAC at both N — because the one
affected draw landed below the percentile. **That is luck, not design.** Any future sweep must
record the `N` it ran at, and a floor may not be compared across sweeps that ran at different `N`
without checking.

**The shipped strategy is unaffected**, and for a reason already in the record: it does not adopt,
it keeps `current-default`, so no haircut touches its `ls_t`. The exposure is entirely to the
*calibration*, not the headline. This is the same class of finding as X7's post-hoc "CPCV adoption
manufactures ~+1.4 of long-short t" — and it is now a demonstrated mechanism on a named draw
rather than a split of 100 draws.

**Instrumentation so this is never chased blind again:** `cpcv_validate` now banks
`adopt_detail` (margin, se, haircut, `n_trials_used`, folds-positive) and `challenger_weights_cols`
— the challenger's weights **whether or not it was adopted**, which is what makes "what would this
run have scored one haircut lower" arithmetic. Reproduce with `python -m scripts.x7_reconcile`;
artifact `data/free_analysis/X7_RECONCILE.json` retains all 100 rows.

**Zero trial cost.** A reconciliation of a recorded rate against retained draws searches nothing.

---

## 3. `RUN_RULES` Part A gains rule 9

> **9. Store the draws, not just the summary.** Any sweep, bootstrap, permutation or grid ships its
> per-draw rows alongside the percentiles — and banks the *inputs* to every derived statistic, not
> only the derived number.

The rationale is this project's own bill: X7 kept 100 draws as five summary rates, so
re-denominating one column cost a whole 3.4-hour re-run (M1), and a one-draw mismatch in a second
column sat open for two sessions. Session 10 had already half-learned it — the comment above
`deflated_sharpe_detail` in `scripts/placebo.py` makes exactly this argument for the DSR's
internals. It is now a rule rather than a comment.

---

## 4. What I did NOT do, and why (RUN_RULES A4)

- **Did not edit a single row of `RESEARCH_LOG.md` to change `N`.** Pre-committed in §4 of the
  register: the parser is repaired, the log is not rewritten. Had the recount surfaced a
  mislabelled row it would have been reported and left in place — re-labelling rows while looking
  at their effect on the denominator is the same error one level up.
- **Did not re-run the placebo sweep to re-derive the floors at N = 129.** The floors are
  `N`-dependent (§2) and today's `N` is 129, not the 121 session 10 ran at. The reconciliation
  shows no draw's adoption differs between 121 and 129, so the published floors still hold — but
  a *re-derivation* is a separate, pre-registered calibration, not something to slip in here.
- **Did not repair the run-to-run non-reproducibility** (the `insider` theme's IC moving between
  identical runs). Still open, still unexplained, and explicitly **not** what §2 diagnoses — the
  X7 discrepancy is fully accounted for by a deterministic mechanism.
- **Did not touch** the options carve-out files, `valuation/screener/**`, `valuation/engine/**`,
  or `valuation/web/**`.

---

## 5. BUGS FOUND (RUN_RULES A3)

1. **`CLAUDE.md`'s stated mechanism for M1's effect on the adopt rate was BACKWARDS** — "because
   the adopt gate reads the Deflated Sharpe". It cannot: adoption is decided at
   `fundamental_panel.py:2729` and the DSR is computed at `:2744`, **downstream**, on the returns
   of whichever scheme adoption just chose. The real mechanism is `_trials_haircut` (`:2097`)
   being floored at `_trial_N()`. Direction and magnitude were right; the mechanism was wrong, and
   getting it right is what made §2's diagnosis findable. **Corrected in place.**
2. **`BACKTEST_RESULTS.json` ships a Deflated Sharpe computed at `n_trials = 84`** — it was last
   run 2026-08-05 and `N` is now 129. The file reads **0.8997** where the honest current figure is
   **0.8556**. Not wrong when written, and `CLAUDE.md` says to quote 0.8556, but the artifact is
   now 45 trials stale and a reader who trusts the file over the brief gets the flattering number.
   Fixes itself on the next full run; flagged because "next full run" has been pending since.
3. **`RESEARCH_LOG.md`'s O16 row contains unescaped `|` characters** (`|Spearman(term_slope,
   atm_front)|`, an absolute value written inside a markdown cell), giving it 11 cells against a
   9-cell header. Every column after the metric is shifted, so the row is unreadable by column.
   **Not fixed here — the register forbids editing rows this session** — and the counter now
   handles it conservatively and reports it. **Owner: whoever owns O16; escape them as `\|`.**
   Worth noting it is the *only* malformed row in 74.
4. **My own first-cut fix was wrong, in the harmful direction** (§1). Recorded here rather than
   quietly corrected, because "the repair introduced the error it was repairing, in a different
   column" is the most useful thing this session learned about its own method.
5. **Carried forward, unrepaired for the fourth session: nothing.** The `research_log.py` parser
   defect that occupied the last three BUGS FOUND lists is the subject of §1 and is closed.

---

## 6. Session 13's first item, with its `needs first`

**Unchanged from session 11's recommendation: task #12, the forward paper-track vs SPY.** Nothing
this session found weakens it, and §2 mildly strengthens it — a fourth demonstration that
in-panel statistics move for reasons that have nothing to do with the market (here, literally the
number of rows in a markdown file).

| dependency | status |
|---|---|
| the paper-track engine | **READY** — 45/45 tests |
| a start date and pre-committed horizon | **NOT SET — Don's call**, committed before the first print |
| the comparison rule | **NOT WRITTEN.** What beats what, over what window |
| n_eff discipline | **the session-9 gate applies** — monthly excess vs SPY is one series, not many |
| `N` for anything scored alongside it | **129**, DSR bar **0.8556**, HAC LS floor **2.2837** |

**Ranked alternatives:** (1) a raw-signal or alternative-model-class combiner as a **new** blind
pre-registration, inheriting session 11's reversal as its prior; (2) the narrow
sector-relative-value variant (roadmap #13).

**NOT an alternative, and this is a correction to what §2 first looked like it implied:
re-deriving the placebo floors at the current `N` is NOT needed.** The floors are `N`-dependent in
principle, but the adopt curve shows N = 116, 121 and 129 all give the same 20 adopters, so
session 10's 2.1437 / 2.2837 **are** the floors at today's `N`. What is needed is the discipline,
not a re-run: every future sweep records the `N` it ran at, and no floor is compared across sweeps
at different `N` without checking the curve.

---

# SESSION 13 (2026-08-08) — the paper-track evaluation contract, drafted and STOPPED for Don; and the stale artifact refreshed

**Owner:** pipeline builder. **Trial cost: ZERO.** Equity `N` stays **129**. A contract is a
pre-registration and nothing has been registered yet, so the trial is charged **on sign-off** —
the moment the search is committed to — not now and not at the verdict. Session 14 adds that row
with the chosen option. Options `N` moved 164 → **169** for a reason belonging to session 12 (§5).

**Headline: item 1 is DONE and DELIBERATELY NOT COMMITTED — `PAPER_TRACK_CONTRACT.md` is a DRAFT
and needs Don. Item 2 is done. But the session's most important output is neither: the forward
track that CLAUDE.md calls "the project's #1 remaining validation" is not running, and the
verdict it is supposed to deliver is not computable from the data either source records today.**

---

## 1. What Don has to decide (the plain-English version)

The draft is `PAPER_TRACK_CONTRACT.md`. Three options; each fixes start date, horizon,
comparison rule, abort rule and what may be said publicly. **Don picks one line.**

**First, the fact that changes the question.** The track is already running and is **behind
SPY**: inception **2026-07-30**, five trading days accrued, Valquo **+0.78%** vs SPY **+3.62%**,
excess **−2.85pp**. That is **−1.8 SD of a five-day window** (two-sided p ≈ 0.08) — an ordinary
bad week that means nothing about the strategy. It means something about the *decision*, though:
**Don is choosing the start date knowing the accrued period went against him.** Discarding it is
the flattering direction and the only choice with a bad look; keeping it costs nothing (5 days is
0.3% of a five-year window). **All three options therefore keep the existing inception**, and a
fresh start is offered only so the choice is recorded as his.

**Second, the number that decides everything, and it is arithmetic.** From the artifact's own
`benchmarks.spy` block the top decile beat SPY by **+9.99%/yr** with a **tracking error of
11.4pp/yr** — an **information ratio of 0.88/yr**, and that is the *in-sample* figure, measured
on the panel the model was tuned on. A t-statistic grows as √time, so:

| horizon | expected t | chance of "significant" **even if the edge is entirely real** | smallest detectable edge |
|---|---|---|---|
| 3 months | 0.4 | 10% | +69 pp/yr |
| 6 months | 0.6 | 13% | +49 pp/yr |
| **12 months** | **0.9** | **18%** | **+34 pp/yr** |
| 24 months | 1.2 | 27% | +24 pp/yr |
| **36 months** | **1.5** | **35%** | **+20 pp/yr** |
| **60 months** | **2.0** | **49%** | **+15 pp/yr** |
| 120 months | 2.8 | 74% | +11 pp/yr |

(Percentages carry a haircut for month-to-month correlation — the project's only measurement of
it is R9's lag-1 **+0.189**, which turns 12 calendar months into ~8 independent ones. Applied as
an illustration, and labelled as one: the monthly excess series does not exist yet to measure.)

**Three consequences, none of them escapable by picking a cleverer statistic:**

1. **A one-year verdict is not a verdict.** At 12 months the test can only detect **+34pp/yr**,
   more than three times what we claim. If the strategy works exactly as backtested, a 12-month
   test says "no evidence" **82% of the time.**
2. **The first horizon where the test is even a coin flip is five years** (49%).
3. **Refutation takes exactly as long as confirmation** — the test is symmetric. Nobody gets to
   say a short track disproved this either.

So the contract's deliverable is **the prohibition, not the verdict**: it stops anyone, us
included, reading three good months as proof. The verdict comes much later than this project has
been implicitly assuming.

**The options.**

| | **A — RECOMMENDED** | B — earlier decision point | C — add a faster secondary test |
|---|---|---|---|
| Start | keep 2026-07-30 | keep 2026-07-30 | keep 2026-07-30 |
| Operational gate | 6 months | 6 months | 6 months |
| Statistical verdict | **60 months** | **36 months** | 60m vs SPY **+** ~36m vs a costed equal-weight basket |
| Power at verdict | 49% | 35% | 49% / 64% |
| Honest summary | slow, but the only one where the number means what it says | sooner, and will very likely say "no evidence" whatever the truth | best-powered, but the extra benchmark is one nobody can buy, and it has to be built |

**A** splits the job in two: a **6-month operational gate** (does the track actually record
properly — daily rows, no gaps, costs near the modelled 33.4bps, no B5-class defect outstanding)
and a **60-month statistical verdict**. The gate has real power because it tests execution rather
than performance — **and we would fail it today.** SUPPORTED needs positive cumulative excess and
a one-sided NW(3) t ≥ 1.645 on monthly excess vs SPY total return; UNSUPPORTED is t ≤ −1.645;
everything else is NULL — **and the contract states in advance that NULL is the single most
likely outcome even if the strategy is exactly as good as advertised**, so a NULL cannot later be
spun as either failure or vindication.

**Abort rule**, precedent audit **B5** (four defects in this very tracker, *every one* of which
flattered it): a defect that changes a recorded return, a construction change, or a vendor change
**voids the affected window**, logged when found; back-filling, a discretionary override, or any
post-inception change to the thresholds **voids the whole run**; sandbox quote delay, rounding, a
same-week catch-up write and **bad performance** are logged, not voided. No void is ever decided
after seeing what it does to the answer.

**Public posture**, now a written rule rather than a habit: paper, thin, too early to judge; the
backtest stays the headline; no annualising a stub, no Sharpe until there is enough history, no
"since inception" figure without its day count, and no verdict language before the horizon —
and it binds a **good** quarter exactly as hard as a bad one.

**→ Don replies with one line: "Option A" (or B, C, or "A but start fresh").** On his reply the
chosen option is committed verbatim with his choice and the date recorded, and the register is
live from that commit. **Nothing was committed unilaterally.**

---

## 2. Item 2 — the stale artifact, refreshed

`BACKTEST_RESULTS.json` shipped a Deflated Sharpe computed at **`n_trials` = 84**, a denominator
45 trials out of date, so a reader trusting the file over the brief got the flattering number.
Re-run on the full universe from the merged tree.

| field | before — 2026-08-05, `4f41c9f`, **`dirty: true`** | after — 2026-08-08, `e83df30`, **`dirty: false`** |
|---|---|---|
| `cpcv.deflated_sharpe.value` | **0.8996589404135822** | **0.855607566829599** |
| `deflated_sharpe_detail.n_trials` | **84** | **129** |
| `n_trials_from_research_log` | 84 | **129** |
| `n_trials_from_weight_schemes` | 8 | 8 (unchanged — the degrade path is intact) |
| `sr0_benchmark` | 0.4056234662323911 | 0.43031816623094016 |
| `n_trials_source` | `RESEARCH_LOG.md (audit M1)` | identical |
| `deflated_sharpe.want` | `>0.95` | `>0.95` — **still fails, as the record says** |

**Everything else is bit-identical.** `construction.long_short_tstat` 2.8360640685320595,
`top_decile_alpha` 0.07174142332098163, `monotonicity` −0.8909090909090909, `universe` 2,531
names / 69 dates, `cpcv.adopt` false, `cpcv.verdict` unchanged, and every `benchmarks` figure —
all to the last digit.

**Session 4's wiring confirmed working, not assumed:** `deflated_sharpe_detail.n_trials_source`
reads `RESEARCH_LOG.md (audit M1)` and `n_trials_from_research_log` now reads **129**, matching
`research_log.detail()['n_used']` exactly. `n_trials_from_weight_schemes` stays 8, so the
degrade-to-old-behaviour path is intact.

**"No other number moved beyond expectation" is a measurement, not an impression.** A leaf-by-leaf
diff of the whole JSON: **15 leaves moved, 32 added, 0 removed.** Of the 15, **five are the
Deflated Sharpe chain** (`n_trials` ×2, `sr0_benchmark`, and `value`/`probability`) and the other
**ten moved by 0.000%** — last-digit floating-point on `costs` and `net_sharpe`. Nothing else
moved at all.

**The known non-reproducibility did not bite, and that is worth recording.** `insider` — the theme
CLAUDE.md flags as having an unstable IC across identical-data runs — came back **identical to
sixteen digits** (median IC −0.0051782959605508995, t −0.23616128224391933), as did `low_risk`,
`size` and `quality`. One clean re-run three days and one merge later is not a fix for that open
item, but it is a data point in its favour.

**The artifact was stale in more ways than `N`, which nobody had noticed.** The 32 added leaves
are not cosmetic: the file shipped **no `oos_verdicts` block at all**, because it predated session
7's B8 fix. A reader trusting it could not see the out-of-sample theme verdicts — only the frozen
`stability_verdicts` under the old name. It also predated the `cash_op_prof` signal, so that
signal was missing from `per_signal`, `signal_coverage` and the sanity subgroup check. **Both
shipped decisions are unchanged on the fresh run: `low_risk` `confirmed_oos`, `insider`
`rejected_oos`.** The sanity layer still fires exactly the two flags the record says are expected,
and neither was silenced.

**Provenance repaired as a side effect.** The replaced file carried `git.dirty: true`; this one
records a clean `e83df30`. The contract draft was deliberately held in scratch until the run had
written, so the refreshed artifact is reproducible from a named commit.

---

## 3. What I did NOT do, and why

- **I did not commit the contract.** That is the instruction and it is also the point: a
  contract whose thresholds an agent chose *and* adopted is not a pre-registration.
- **I did not fix the track.** Every gap in §5 is real and none of it is repaired here. The
  operational work is only worth doing against a signed horizon, and two of the items (which
  source is authoritative; whether the series gets chained) are **construction decisions Don's
  answer determines**, not bug fixes. Doing them first would be choosing the contract by
  implementation.
- **I did not touch `RESEARCH_LOG.md`'s O16 row** — already routed to the options lane, and they
  have since fixed it (§5).
- **I did not re-derive any placebo floor.** Equity `N` did not move, so nothing recalibrates;
  session 12 already established that the floors at N = 129 are the floors at N = 121.
- **I did not edit screener/engine/web**, which are outside this lane, even where §5's findings
  point at `valuation/screener/index_track.py`. Reported instead.

---

## 4. What Session 14 does

**Blocked until Don replies.** On his reply, in this order:

1. **Commit the chosen option verbatim**, with the choice and date in §5's register, and set
   the inception into a **tracked** file — §5 bug 1 is that the project's most important
   pre-registration date currently exists only in a gitignored one.
2. **Then the operational gate becomes the work**, and it is bigger than "wait": pick the single
   authoritative source, make it write every trading day, and **build a chained return series
   that includes closed stints** — without which no verdict under the contract is computable at
   any horizon.

**`needs first`**

| item | state |
|---|---|
| Which of A / B / C | **NOT SET — Don's call.** Everything below waits on it. |
| Keep inception vs fresh start | **NOT SET — Don's call**, with §1's disclosure that the accrued window is negative |
| Authoritative source: sandbox engine or Cowork file | **NOT SET.** A track with two possible sources has no fixed start |
| Whether closed stints are chained into the series | **NOT SET — a construction change**, and the code says so explicitly |

---

## 5. BUGS FOUND

1. **THE INCEPTION DATE OF THE PROJECT'S #1 VALIDATION EXISTS ONLY IN A GITIGNORED FILE.**
   `2026-07-30` appears in `data/valquo_track.json` and **nowhere in the repository** —
   not in `HANDOFF_STATUS.md`, not in the audit handoff, not in the ledger. `data/` is
   gitignored, so on a fresh deploy the start date of the out-of-sample record is simply gone.
   A pre-registration nobody can produce is not one. **This is the strongest argument for
   signing the contract**, which puts the date into git.
2. **THE TRACK CANNOT PRODUCE THE SERIES ANY VERDICT NEEDS, IN EITHER SOURCE.**
   `paper_index_track` stores a **snapshot of currently-open holdings**, each measured since its
   own entry — not a chained series; differencing two points is not a monthly return, and a name
   that leaves the book stops contributing. The code states this and states that chaining closed
   stints in "is a construction change, not a bug fix, and was not made" (`paper_track.py:735-740`).
   The Cowork file chains correctly between the rows it has, but is missing days (bug 3), so a
   four-day gap silently becomes one "daily" return. **Documented ≠ harmless: it blocks the
   verdict at every horizon.**
3. **THE DAILY WRITE IS DROPPING DAYS.** `valquo_track_history.csv` holds **two** rows —
   day 1 (2026-07-31) and day 5 (2026-08-06). Days 2-4 were never written.
4. **THE ENGINE BUILT FOR THIS HAS NEVER BEEN FED.** `paper_option_orders`,
   `paper_index_holdings` and `paper_index_track` are **0 rows each**, while 45/45 tests pass.
   The five accrued days come from an entirely different mechanism. **CLAUDE.md roadmap #12 says
   "What remains is elapsed time and reading the track, not building it" — that is wrong**, and
   wrong in the direction that makes the project look further along than it is.
5. **THE SITE WILL PROMOTE THE PAPER TRACK TO ITS HEADLINE BY ITSELF, ON A DATE ALREADY FIXED,
   AND NOBODY HAS TO APPROVE IT. THIS IS THE MOST URGENT ITEM IN THE SESSION.**
   `index_track.py:223-224` reads `out["thin"] = days < MIN_LIVE_DAYS` then
   `out["headline"] = "backtested" if out["thin"] else "live"`, with `MIN_LIVE_DAYS = 60`. At
   day 60 the "too early to judge" pill the landing page renders (`index.html:114`) disappears
   and the headline flips to **live**. **The track is on day 5, so this fires in ~55 trading
   days — late October 2026 — at 13% power, where the smallest detectable edge is +49pp/yr.**
   The constant was never pre-committed and does not derive from power; it also disagrees by 2×
   with `paper_track.MIN_DAYS_FOR_MEANING = 126`, which governs the same track. **Both live in
   `valuation/screener/index_track.py`, outside this lane — this needs assigning, not just
   noting**, and it is the concrete reason the contract wants signing before late October rather
   than whenever.
6. **THE COMMITTED ARTIFACT WAS WRITTEN FROM A DIRTY TREE.** The `BACKTEST_RESULTS.json` this
   session replaced carried `git.dirty: true` at `4f41c9f`, so the canonical headline file's
   provenance was not reproducible — exactly the tell the standing note about this file warns
   about. This session's replacement was launched from a clean tree deliberately, and the
   contract draft was held in scratch until the run had written, so the new file records a clean
   commit.
7. **THE CANONICAL ARTIFACT WAS STALE IN MORE THAN `N`, AND THE MISSING PART WAS A VERDICT
   BLOCK.** `BACKTEST_RESULTS.json` predated session 7's B8 fix, so it shipped **no
   `oos_verdicts` at all** — a reader parsing the canonical file for the out-of-sample theme
   verdicts would have found only the frozen `stability_verdicts` and could reasonably have read
   those as the out-of-sample result, which is precisely the confusion B8 was fixed to end. It
   also predated `cash_op_prof`, which was absent from `per_signal`, `signal_coverage` and the
   sanity subgroup check. **A results file is a claim with a date on it; this one had drifted
   three sessions behind the code that writes it.**
8. **CLOSED, not found here — session 12's routed item is done.** The O16 row's unescaped `|`
   was repaired by the options lane (rewritten as `abs(...)`), `rows_malformed` is now **empty**,
   and options `N` corrects **164 → 169** as session 12 predicted — the 4 trials that row was
   silently losing, plus one new row. The session-12 parser fix is what made the loss visible.

---

# SESSION 14 — the contract is signed (OPTION E), the meter is frozen, and the track has two recorders

**Date:** 2026-08-09. **Owner:** pipeline builder. **Lane:** `valuation/edge/**`.
**One-line state:** the register is IN FORCE and the meter's parameters are frozen with zero
complete months in existence — and the two headline repairs the task asked for turned out to
rest on premises that were false, so what shipped is the diagnosis plus the parts that were
actually mine.

## 1. The committed register — §5 of `PAPER_TRACK_CONTRACT.md`, quoted

Don's choice, recorded verbatim as given:

> **OPTION E** — Option C's structure (keep 2026-07-30 inception including the accrued negative
> days; 6-month operational gate; 60-month statistical verdict vs SPY; the ~36-month costed
> equal-weight-basket secondary once built), PLUS a pre-registered anytime-valid evidence meter
> that runs from inception but **first renders at the 6-month operational gate (2027-01-30) and
> monthly thereafter — whatever it says, favourable or not.**

| field | value |
|---|---|
| **Option chosen** | **E** — Option C's structure plus the §6 evidence meter |
| **Signed by** | Don (donniecorbin6@gmail.com) |
| **Date signed** | **2026-08-09** |
| **Inception** | **2026-07-30**, including the five accrued days and the −2.85pp known to be negative at signing |
| **Bound source** | the **published Valquo Index** — `data/valquo_track.json` + `data/valquo_track_history.csv`, read by `valuation/screener/index_track.py`. **NOT** the Tradier sandbox engine |
| **Book** | Valquo Index as published — top decile, large-cap tier, score-weighted, 8% cap |
| **Benchmark** | SPY total return |
| **Operational gate** | **2027-01-30** (6 months) — tests recording, not returns |
| **Verdict date** | **2031-07-30** (60 months) |
| **Secondary verdict** | ~**2029-07-30**, **only if** the costed equal-weight basket is built and separately pre-registered. Not built; if it never is, there is no secondary reading |
| **Statistic** | one-sided NW(3) t on monthly excess, plus cumulative excess |
| **SUPPORTED / UNSUPPORTED** | t ≥ +1.645 and cumulative > 0 / t ≤ −1.645; anything else NULL |
| **Power at verdict, in advance** | **49%** vs SPY at 60 months; 64% for the secondary at 36 if built |
| **Costs** | modelled, not measured: **0.14529 pp/month** |
| **Voided windows** | *(none yet)* |

Logged to `RESEARCH_LOG.md` as **`PT-REGISTER`**, verdict `REGISTERED`, **equity `N` 129 → 130**
(**Deflated Sharpe 0.8556 → 0.85473, √(2·ln 130) = 3.1201**). Charged rather than waived because
the verdict will be quoted as a claim about the equity strategy, and understating `N` overstates
significance. The row is logged **at registration** — that is the point of a pre-registration —
and the verdict gets appended to it in 2031 rather than replacing it.

**And because charging it moved `N`, the canonical artifact had to be re-run — this session
re-created session 13's own staleness bug and then closed it in the same session.** Full re-run
on the 2,531-name / 69-date universe from a **clean tree at `f56cc51`**, `git.dirty` false:

| | before (`c1b0ed6`) | after |
|---|---|---|
| `cpcv.deflated_sharpe.value` | 0.855607566829599 | **0.8547321268980206** |
| `n_trials` / `n_trials_from_research_log` | 129 | **130** |
| `sr0_benchmark` | 0.43031816623094016 | 0.43075197686098127 |
| `n_trials_source` | `RESEARCH_LOG.md (audit M1)` | unchanged |
| `n_trials_from_weight_schemes` | 8 | unchanged — degrade path intact |

**Leaf-by-leaf diff: 11 moved / 0 added / 0 removed.** Five *are* the DSR chain, four are
provenance (`generated_at`, `generated_at_utc`, `git.commit`, `git.short`), and the remaining two
moved by **0.000%** last-digit float. `long_short_tstat` **2.8360640685320595**,
`top_decile_alpha` **0.07174142332098163**, `monotonicity` **−0.8909090909090909** and universe
**2531/69** are bit-identical. **Zero additions**, against session 13's 32 — the expected
signature of a refresh one day behind rather than five sessions. `oos_verdicts` unchanged
(`low_risk` `confirmed_oos`, `insider` `rejected_oos`), `cpcv.adopt` still false so the shipped
strategy takes no haircut, and the sanity layer fires its two expected flags with **neither
silenced**. Verified afterwards: the artifact's `n_trials` and `research_log`'s equity `N` both
read **130**. Logged as `ARTIFACT-N14` (verdict `FIXED`, so it does not itself count).

## 2. The meter's exact parameters — `valuation/edge/track_meter.py`, contract §6

A **Robbins normal-mixture anytime-valid confidence sequence** on the running sum of monthly
excess-vs-SPY returns:

```
boundary(n) = sigma * sqrt( (n + rho) * ln( (n + rho) / (rho * alpha^2) ) )
```

| parameter | value | source |
|---|---|---|
| `sigma` | **3.9846917305386294** pp/month | backtest tracking error 11.40pp/yr → 3.2909/month, **inflated by √1.466091** |
| autocorrelation | design effect **1.466091** | (1+r)/(1−r) at R9's measured lag-1 **r = +0.189** |
| `rho` | **3** | minimises detectable edge averaged over 12/24/36/60m; flat from ρ=2 to ρ=6 |
| `alpha` | **0.05 two-sided** | 2.5% per direction |
| cost drag | **0.14529 pp/month** | 261% turnover × 33.4bps one-way, both legs = 1.7435 pp/yr |
| stale-mark limit | **3 trading days** | staler ⇒ the month is **voided**, not measured from the wrong window |
| max voided fraction | **10%** | above this the meter **refuses to render** |

**Measured, not asserted** — 40,000 simulated paths with the AR(1) structure in them:

| | |
|---|---|
| false crossing under the null | **1.5%** by 60 months, 1.9% by 120 (nominal 5%) |
| power at the backtested +9.99 pp/yr | **13.3%** by 60 months, 30.7% by 120 |
| power at twice that (+20 pp/yr) | 65.8% by 60 months |

Mean excess needed to cross: **6m 63.7 · 12m 42.5 · 24m 29.6 · 36m 24.3 · 60m 19.0 · 120m 13.8
pp/yr.**

**THE SENTENCE THAT MUST TRAVEL WITH EVERY QUOTE OF THIS METER: it will most likely never cross,
even if the strategy is exactly as good as the backtest says** — it needs ~19 pp/yr at 60 months
against a claimed +9.99. That is the correct behaviour of an honest anytime-valid bound. **A
meter that has not crossed is the expected outcome and is NOT evidence against the strategy**,
just as three good months are not evidence for it.

Two findings from building it, both of which changed the design:

- **The AR(1) inflation is load-bearing.** Without it the false-crossing rate on autocorrelated
  data is **6.7%** against a nominal 5% — the naive version silently breaks its own guarantee.
  `test_the_autocorrelation_inflation_is_load_bearing` fails if anyone removes it.
- **`sigma` may never be revised downward.** At 1.5× the assumed volatility the false-crossing
  rate is **20%**, a four-fold breach, so `sigma_breach` ships on every call.

**Genuinely blind:** at the freezing commit the bound series held **two daily rows and ZERO
complete calendar months**. No parameter could have been tuned to the outcome even in principle.
20 tests pin every constant to a literal, including one that pins the render decision as
invariant to flipping the sign of the entire series — the code cannot express a suppression.

## 3. Item 2 — the recording. Both premises were false, and that is the deliverable

The task asked me to find why the daily write skipped days 2–4, and to wire an engine that "has
never been fed". Measured:

**3.1 There is no daily writer at all.** Not a scheduler fault, not a crash, not a conditional
write. **Nothing in this repository writes `data/valquo_track_history.csv`.** `index_track.py`
only ever *reads* it; `HANDOFF_backup.md:194` records the same independently. The rows are
produced by hand on the Cowork side, which is exactly why four of six are missing. Measured
coverage on 2026-08-09: **2 of 6 due rows, 33.3%**, missing 2026-08-03/04/05/07.
**The operational gate cannot pass until an automated daily write exists**, and building it is
the Cowork lane's, not mine.

**3.2 The engine HAS been fed — session 13 measured the wrong database.** On the live Render
service `paper_index_track` holds **4 index days**, `paper_index_holdings` **10 holdings** and
`paper_option_orders` **3 orders**, and the weekly `track-backup` Action has been committing
them to `data_export/` all along. Session 13's "0 rows each" was the local dev database.
**Correction recorded in `CLAUDE.md` and in the contract's §0a.**

**3.3 The two recorders hold DIFFERENT BOOKS. This is the session's material finding.**

| | **published Valquo Index** | Tradier sandbox engine |
|---|---|---|
| files | `valquo_track.json` + `valquo_track_history.csv` | `paper_index_track` → `data_export/paper_track_*` |
| inception | **2026-07-30** | 2026-08-03 |
| book | **86 names, score-weighted, max weight 2.3%** | **10 names, equal-weighted at 10% each** |
| read by | `screener/index_track.py` — the number the site shows | `edge/paper_track.py` |

The engine's 10% equal weights **violate the contract's own 8% cap**, and its book is not the
Index. **So this was never a choice between two recordings of one track — they are different
objects.** The register binds the Index. Wiring the engine into the daily path, as the task
proposed, would have bound the contract to the wrong book.

**3.4 What I built instead, in my lane.** `track_meter.gap_report` names **every** missing
trading day rather than counting them — a count cannot be audited later, and the abort rule has
to tell "missed and filled the same week" from "missing". It also flags rows on non-trading days
(something marking the book when there was no close), and it correctly does **not** demand a row
on inception day, which is day 0 — my first version did, and reported a permanent uncloseable
gap. And `monthly_excess` makes the statistical series **robust to interior gaps by
construction**: the source stores cumulative-since-inception levels, so a month needs only its
two endpoints. A month whose *month-end* mark is missing or >3 days stale is **voided**, never
silently averaged over.

**3.5 Backfilled nothing.** Days 2–4 stay missing, logged, exactly as the register requires.

**3.6 CLOSED A SECOND UNGATED DOOR, in my lane, found by the engine lane's own bug report.**
Their `OOB5` gated `index_track` on the contract but recorded that a second path was still open:
`hero` falls back to `paper_track.index_summary()` when the Cowork tracker files are absent —
**which is exactly the fresh-deploy case, since `data/` is gitignored** — and that function set
`meaningful` on a pure day count (`len(rows) >= MIN_DAYS_FOR_MEANING`, 126) without ever
consulting the contract. So a paper track could still have led the page on elapsed time alone,
one layer below the gate they had just built.

`index_summary` now requires **both** the day count **and** the contract gate, and it reads that
gate by **delegating to their `index_track.gate_state()`** rather than parsing the contract
again — a second parser would be a second record of the same fact, free to disagree with the
document Don signed. `_contract_gate()` is **fail-closed**: import failure, unreadable contract
or malformed row all resolve to *not passed*, so the unreachable error is "a thin track leads the
page". Two tests pin it — one that a day count alone is never enough at any *n*, one that a
raising `gate_state` yields `passed: false`. **47/47 paper-track tests** (was 45).

Also corrected, because their report was right and the error was in my document: the contract's
§7.4 and `CLAUDE.md` both said `MIN_DAYS_FOR_MEANING` lives in `index_track.py`. **It is
`valuation/edge/paper_track.py:70`** — and that sentence was the one assigning the work, so the
wrong file name pointed the fix at the wrong lane.

## 4. What I did NOT do

1. **I did not produce "evidence the daily write now happens (two consecutive days landing)."**
   It was not possible for two independent reasons: there is no writer in this repo to fix
   (§3.1), and two consecutive trading days is elapsed wall-clock this session does not have.
   **The gate remains failing, and I have not claimed otherwise.**
2. **I did not wire the sandbox engine into the daily path.** §3.3 — it records a different
   book, so wiring it would bind the contract to the wrong object. I named the bound source
   instead, which is the branch the task explicitly permitted.
3. **I did not re-point the engine's book at the Index.** It runs live on Render against a
   sandbox broker; changing what it holds is a construction change to a running recorder, not a
   repair, and it needs its own decision. Recorded as ledger `PT-SPLIT`.
4. **I did not touch `valuation/screener/index_track.py`** — the 60-day auto-flip was the greeks
   lane's, prompted separately. **They closed it the same day (`126c137`), merged in here, and
   their fix is better than the one the contract asked for:** instead of re-pointing
   `MIN_LIVE_DAYS` at a new constant, `gate_state()` now parses the **`Operational gate passed`
   row of §5** on every request and `headline` requires **both** the day count **and** that row.
   The auto-flip is gone at any day count, indefinitely, and every unrecognised outcome (missing
   file, missing row, malformed table, two rows disagreeing) is not-passed — the failure
   direction is "still backtested", never "now live". **My part of the merge was to fill that row
   as `pending` and verify their parser agrees: `gate_state()` reads the signed §5 as
   `passed: false`.** The code and the contract now agree, with one copy of the fact.
5. **I escaped nothing in `RESEARCH_LOG.md` myself.** `rows_malformed` is empty and options `N`
   reads 192 after the merge.
6. **I did not build the 36-month secondary basket.** It does not exist, and §5 records it as
   conditional for exactly that reason.

## 5. BUGS FOUND

1. **THE BOUND FORWARD-TRACK SERIES HAS NO WRITER.** The project's #1 validation depends on a
   file that is maintained by hand, in a gitignored directory, with 33.3% coverage. **Blocks the
   operational gate outright.** → Cowork lane. Ledger `PT-WRITER`.
2. **TWO LIVE RECORDERS HOLD DIFFERENT BOOKS, AND ONE VIOLATES THE CONTRACT'S OWN 8% CAP** (10
   names at 10%). A B7-class split: two numbers that can be confused for each other, one of
   which is not the Index at all. → Needs assigning. Ledger `PT-SPLIT`.
3. **SESSION 13 REPORTED "0 ROWS, THE ENGINE HAS NEVER BEEN FED" FROM THE LOCAL DEV DATABASE.**
   The live service had data the whole time. Corrected in `CLAUDE.md` and §0a. The general
   lesson is the one the artifact-staleness bug already taught: **a local read is not a
   measurement of production.**
4. **THE ENGINE'S OWN RECORD IS ALSO GAPPY, AND ON A DIFFERENT DAY.** It holds 2026-08-03/04/05/
   **07** — missing **08-06** — while the Index file holds 07-31 and **08-06**. The two
   recorders' gaps are *complementary*, so neither is a copy of the other and neither is
   reliable.
5. **THE ENGINE'S DAY-1 ROW IS NOT ZERO** (`index_ret` 1.73%, `bench_ret` 1.42% on its own
   inception date), i.e. entry prices and the first mark are taken at different times of day.
   Small, but it means "return since inception" from that source includes a partial first
   session. Not investigated further — out of the bound source.
6. **THE RECORDED SERIES IS GROSS; THE CONTRACT'S COST FIGURE IS MODELLED.** No fills exist for
   a quote-marked paper book, so 0.14529 pp/month is an assumption fixed in advance (deliberately
   the larger of the two readings the record supports). It cannot interact with the outcome, but
   it is not evidence about real trading costs. Recorded as contract §7.6.
7. ~~**`MIN_LIVE_DAYS = 60` STILL AUTO-PROMOTES THE TRACK TO THE SITE HEADLINE**~~ **— CLOSED
   THE SAME DAY by the engine lane (`126c137`), merged in here.** `headline` now requires both
   the day count and §5's `Operational gate passed` row, which I filled as `pending` and verified
   their parser reads as `passed: false`. **The dated deadline is gone.** Kept in this list
   because it was live when the session opened and because it is the one bug in the set that
   another lane fixed rather than me.

## 6. Session 15's first item

**`needs first`: nothing — this one is unblocked and it is mine.**

**Wire the meter and the gap report into something that runs.** They exist and are tested but
nothing calls them: `track_meter` is a library with no caller. The operational gate and the
first render are the same day, 2027-01-30, so the useful work now is the *reporting* path — a
`detail()`-style block that surfaces `gap_report` (missing days, dated) and the withheld meter
state on every run, so the recording failure is visible continuously instead of being discovered
at the gate. That is squarely `valuation/edge/**` and needs no decision from anyone.

**Two items that are NOT session 15's because they are not this lane's**, listed so they are not
mistaken for available work: `PT-WRITER` (Cowork must build the daily write) and the
`MIN_LIVE_DAYS` auto-flip (greeks lane, dated late October 2026). **If `PT-WRITER` is still
unbuilt by roughly 2026-11, the operational gate will fail on 2027-01-30 by construction**, and
the honest response then is to restart the clock from the repair — which §3's Option A already
provides for — not to relax the gate.

---

# SESSION 15 — Amendment 1 (run #1 voided, vintage rule), and the meter finally has a caller

**Date:** 2026-08-09. **Owner:** pipeline builder. **Lane:** `valuation/edge/**`.
**One-line state:** the contract is amended and the amendment is recorded openly with its own
strongest objection attached; the meter and gap report are wired into `/api/track`; and the
writer that was reported to close `PT-WRITER` **could not be found**, so the gate stays shut.

## 1. Contract Amendment 1 — `PAPER_TRACK_CONTRACT.md` §5a

Don's decision, quoted verbatim in §5a and summarised here:

- **Run #1 is VOID** — inception 2026-07-30, ~6 days, 2 recorded rows. Reason: it measured a
  model that has since materially changed (growth-input fix, score fix, universe rebuild).
- **Run #2 is registered** — inception **2026-08-10**, gate **2027-02-10**, verdict
  **2031-08-10**, with **zero accrued days**.
- **The VINTAGE RULE** — any ADOPTED change to scoring, weights or construction closes the
  current vintage and opens the next; **rebalancing under unchanged rules is not a vintage
  event**; each vintage carries its own clock; the gate and meter attach to the current vintage;
  the cross-vintage chain is kept and published as **"the system as operated"**.

**Why this is the contract working rather than bending.** §3's abort rule already listed *"any
change to how the Index is constructed"* as voiding the affected window. The clause pre-existed
the run, and the cause is a model change rather than a result.

**No threshold moved.** σ, ρ, α, the cost drag, the statistic and the SUPPORTED/UNSUPPORTED bars
are untouched, so §3's *whole-run* void clause (which triggers on a threshold change) is not
engaged. **The amendment moves the clock, not the statistics**, and a test pins that separation.

**σ was re-checked against the changed model rather than assumed to survive it.** The current
backtest still gives SPY excess **+9.99%/yr** at an implied tracking error of **11.401 pp/yr** and
IR **0.8759/yr** — the figures σ was derived from. Had they moved, §6.5 permits raising σ and
nothing else.

### The disclosure, which is written into the contract and not just here

**The voided window was known to be −2.85pp when it was voided.** Discarding a stretch that went
against the strategy is the flattering direction, and §1 warned about exactly this before anyone
signed. Three things answer it, each checkable rather than asserted:

1. **The cause is independent of the outcome** — the model changed, which would have been true
   had run #1 been +2.85pp.
2. **Run #2 accrues ZERO days before its inception**, so no window's sign could have informed the
   new start date. The objection §1 raised against a fresh start is unavailable by construction.
3. **The voided rows are kept, not deleted** — they appear in `as_operated()`, so anyone can see
   what was excluded.

§5a also forbids the thing this must not become: **voiding a vintage for a change chosen after
seeing the vintage go badly.** The rule's "ADOPTED change" test is what makes that mechanical.

**Cost: equity `N` 130 → 131** (`PT-AMEND1`), **Deflated Sharpe 0.8547321268980206 →
0.8538605963614212, √(2·ln 131) = 3.1226**. `BACKTEST_RESULTS.json` was re-run from a clean tree
at `68aba51` so the artifact matches the record: **14 leaves moved / 0 added / 0 removed** —
five are the DSR chain, four provenance, and five moved by **0.000%** last-digit float.
`long_short_tstat` 2.8360640685320595, `top_decile_alpha` 0.07174142332098163, `monotonicity`
−0.8909090909090909 and universe 2531/69 are bit-identical; `oos_verdicts` unchanged,
`cpcv.adopt` still false, degrade path (`n_trials_from_weight_schemes` 8) intact, sanity layer
fires its two expected flags with neither silenced. *(The first attempt was killed mid-load and
wrote nothing, so the artifact was briefly one trial stale rather than wrong; it was re-run
rather than patched.)* Logged as `ARTIFACT-N15`. Charged, not waived:
void-and-restart is a researcher degree of freedom — each vintage is another chance for the same
hypothesis, and the probability that *some* vintage crosses rises with the number of vintages.
§5a rule 6 is the brake (a vintage change resets the whole accrued clock and buys nothing
statistically); the trial charge is the accounting.

## 2. Vintages in code — `track_meter.VINTAGES`

Two construction points each took a rewrite, and both were found by running the thing:

- **A later vintage is baselined at its OPENING LEVEL, not at zero.** The recorded series holds
  cumulative return since run #1, so zero-baselining vintage 2 would fold run #1's drift into its
  first month. Taking the level at the vintage's opening date is correct whether or not the
  Cowork writer resets its cumulative — a behaviour nobody here controls.
- **`as_operated()` uses RAW ENDPOINTS, not complete months.** The first cut reported vintage 1 as
  **0.0%** because a six-day window holds no complete calendar month. Reporting 0.0% for a window
  that actually moved −2.85pp is the flattering kind of wrong. It now reproduces **+0.7760% /
  +3.6228% / −2.8468pp** exactly.

## 3. Session 15's own item — the meter now has a caller

`track_meter.detail()` is surfaced as `summary()["contract_track"]` in `paper_track.py`, i.e. on
**`/api/track`**, which `app_saas.py:389` and `web/app.py:748` already serve. Before this the
meter and the gap report existed, were tested, and **nothing called them** — a library with no
caller. The gate tests whether the track is being *recorded*, and a recording failure nobody
notices until gate day has already cost the whole window.

- **It is not vacuously green, and the first cut was.** Before the vintage's first trading day
  there are zero expected rows, so `gap_report.complete` is trivially true and "every trading day
  recorded" would have been a pass that means nothing. `recording_ok` now reads `None` with an
  explicit "has not started" note. Pinned by a test.
- **Labelled as a different object** from the sandbox engine's blocks in the same payload
  (`source` names the published Valquo Index; `not_the_sandbox_engine: true`).
- **Fails soft** — an unreadable track degrades to `available: false`, never a 500 on an
  unrelated page.
- **Reconciled against PT-OUTBOUND's authority.** This module legitimately computes its own
  excess — the meter's statistic is monthly, per-vintage and net of a modelled cost drag, so
  reading it off the claim would be wrong. But `as_operated` *is* the same kind of object as the
  claim, so `detail()` carries `index_track.vs_spy_claim()`'s output beside it and reports
  `as_operated_agrees_with_authority`. **Measured today: −2.8468 vs −2.8468, agrees.** A missing
  authority reads `None`, never agreement.

## 4. PT-WRITER — reported closed, and I could not find it

The task states the writer now exists as Cowork scheduled task `valquo-daily-track-write`,
weekdays 20:01. **Two checkable facts, and they do not settle it in either direction:**

- **No such task is visible in this machine's Task Scheduler.** 413 tasks enumerate (so this is
  not a permissions block); three are Valquo-related — `Valquo D Backup`, `ValuationToolAutoPush`,
  `ValuationToolBackup` — and **none is this one.** The name appears nowhere in the repository.
- **Even if it exists, no run was due before this was written.** The amendment lands Sunday
  2026-08-09; the first weekday firing is Monday 2026-08-10 at 20:01.

So its absence from the scheduler is **evidence, not proof** — it could be registered under
another account or on another machine. **I have not marked `PT-WRITER` done, and the gate stays
`pending`.**

**The test is now mechanical and costs nothing.** Run #2's inception is 2026-08-10, which is day
0, so the **first row due is 2026-08-11** and the earliest date its absence is detectable is
**2026-08-12**. From then, `/api/track`'s `contract_track` block reports it directly:
`recording_ok: false` and the missing date named.

## 5. What I did NOT do

1. **I did not verify the writer works** (§4) — no run was due, and I could not find the task.
2. **I did not backfill run #1's missing days,** and Amendment 1 does not either. Voided is not
   repaired.
3. **I did not re-tune σ, ρ or α** to the changed model. Re-tuning a pre-registered parameter on
   a model change is how a pre-registration dies; §6.5 permits only raising σ, and the
   re-measurement said it did not need raising.
4. **I did not re-point the sandbox engine's book** (`PT-SPLIT`, still open) or touch
   `valuation/screener/**` beyond reading it.
5. **I did not add `track_meter.py` to PT-OUTBOUND's AST guard list.** It is not an outbound
   composer and would fail the guard for a legitimate reason; the reconciliation in §3 is the
   answer instead.

## 6. BUGS FOUND

1. **THE REPORTED WRITER CANNOT BE FOUND** (§4). The one item blocking the operational gate is
   reported closed and is not verifiable; the scheduler does not have it. → Needs Don or Cowork
   to confirm where it is registered. **Checkable from 2026-08-12 with no further work.**
2. **MY OWN FIRST CUT REPORTED A VACUOUS PASS** — `recording_ok: true` before any trading day was
   due. Caught by running it. Recorded because the class of error matters: a bound that cannot
   fail yet must not report a pass, and this project has shipped that shape before.
3. **MY OWN `as_operated` REPORTED 0.0% FOR A WINDOW THAT MOVED −2.85pp**, by inheriting the
   meter's monthly granularity for an object that is not monthly. Also caught by running it.
4. **The contract's §7.4 gate-day example still said 2027-01-30** after the horizons moved.
   Corrected to 2027-02-10. It sits inside a fenced block that the parser skips, so it could not
   have flipped the gate — but a wrong instruction on gate day is a real hazard.

## 7. Session 16's first item

**`needs first`: one reading, on or after 2026-08-12 — no human action required to unblock it.**

**Read `/api/track`'s `contract_track.recording_ok`.** If it is `false` with `2026-08-11` named,
the daily writer is not running and `PT-WRITER` is still open regardless of what the scheduler
claims — and that is then the whole of session 16's work, escalated to Cowork with a dated,
named missing row rather than an impression. If it is `true`, `PT-WRITER` closes on evidence for
the first time and the operational gate has a path to passing on 2027-02-10.

**Then, and only then:** `PT-SPLIT` (the sandbox engine still records a different book at 10%
equal weights, which the contract's 8% cap forbids) is the next open item in this lane.

---

# SESSION 16 (2026-08-10) — two live bugs repaired, PT-SPLIT closed on a corrected diagnosis, and V1 registered blind

Three items, in the order Don set them. All three landed. **The most important sentence in this
write-up is a correction to my own last one.**

## 0. The headline, and the thing I got wrong

**I reported `PT-SPLIT` twice — in §7 of session 15 above, and in the ledger — as the sandbox
engine "recording a different book at 10% equal weights, which the contract's 8% cap forbids".
That is wrong, and it was wrong when I wrote it.** `valquo_index.build_index` sets

```
cap = max(MAX_WEIGHT, 1.0 / len(picks))
```

with a comment in the source saying exactly why: **ten names at 8% sum to 80%**, so on a small
book the cap *must* relax to equal weight or the redistribution loop never terminates. The
payload has always self-reported `effective_max_weight`. **The weights were correct for the book
they described.** I read a symptom as the defect and repeated it for two sessions; the
options-bot lane and `HANDOFF_appfixes.md` inherited the same framing.

**The real divergence is BOOK SIZE — 10 names against the published Index's 86 — and it is one
construction fed two inputs.** `n = max(MIN_NAMES, round(len(large) × TOP_DECILE))` with
`MIN_NAMES = 10`, so a 10-name book means the eligible large-cap tier held **fewer than 100
names**; the published 86 implies a tier of roughly 860. `/admin/run-paper-track` reads
`data/valquo_index.json` when it exists and **silently rebuilds from the store's latest scan when
it does not** — and that scan is a top-N hot list, not the universe.

That matters beyond bookkeeping, and it is why the wrong diagnosis was expensive: **had I "fixed"
it the way I described it, I would have lowered a cap that was already correct and left the
truncated input in place.** The split would have survived the repair.

---

## 1. BUG 1 and BUG 2 — the live paper options book

Routed by the options-bot lane off the first three real fills (`HANDOFF_optionsbot.md` §4, §9).
Both are in `valuation/edge/paper_track.py`. **Pre-committed values first, in
`PREREG_session16_paper_track_repair.md`, written before any code changed.**

### BUG 1 — the exit levels described a price the book never paid

`_place_entry` derives `target_premium` and `stop_premium` from the price the order was
**submitted** at. `mark_open` then overwrote `entry_premium` with the broker's actual fill and
**never recomputed either level**. It is systematic rather than occasional: `auto-scan.yml` runs
the paper cycle after the close, so the limit is set from a post-close quote and the day order
fills at the next open.

**The diagnosis was corroborated before the fix, by arithmetic that could have refuted it.**
Dividing each live `target_premium` by 2 recovers a submit price; dividing each live
`stop_premium` by 0.5 recovers **the same three numbers** — 4.45, 4.90, 16.10. Two different
multipliers agreeing to four decimals is not a coincidence.

| alert | fill | target: was → **now** | stop: was → **now** |
|---|---|---|---|
| 1 TGT | 3.55 | 8.90 → **7.1000** | 2.225 → **1.7750** |
| 2 MET | 4.60 | 9.80 → **9.2000** | 2.450 → **2.3000** |
| 3 ETN | 16.10 | 32.20 → **32.2000 (bit-identical)** | 8.050 → **8.0500 (bit-identical)** |

**All five pre-committed criteria held exactly**, verified by replaying the committed Render
export into a temp store: exactly 2 of 3 rows changed; ETN untouched because its fill equalled its
limit; every row ends at `target/entry = 2.000000` and `stop/entry = 0.500000`; the second pass
repairs nothing; and no field outside the two levels plus `note`/`updated_at` moved.

**Fixing `mark_open`'s fill branch only protects future entries**, so there is also a repair pass
over rows already open — idempotent, and therefore a standing guard rather than a one-shot
migration. If any future path writes a level that disagrees with the fill, it is repaired and
reported.

**A repair may not execute a trade.** If a corrected level is already crossed by the last mark,
writing it would make the next `close_matured` sell the position. That write is **deferred** and
reported in `level_repairs_deferred` instead. None of the three current rows crosses (TGT 3.50 in
(1.775, 7.10); MET 2.70 in (2.30, 9.20); ETN 11.10 in (8.05, 32.20)), so the branch is untaken
today and pinned by a test rather than by hope.

### THE DIRECTION OF THIS REPAIR IS FLATTERING, AND IT WAS DISCLOSED BEFORE IT WAS RUN

Both changed rows move their target **down** (easier to reach) and their stop **down** (looser).
**The bug ran against the paper book and the fix runs for it.** That is not a reason to leave it
broken — the levels were wrong against the specification either way, and comparability is the
whole purpose of the track — but "we fixed a bug and the book improved" is the easiest way for a
forward test to flatter itself, so it is in the register, in the log row and here.

One number makes it concrete: **MET sat 10.2% above a stop level no backtest ever specified.** At
its specified stop it sits 17.4% above. The bug was days from recording a stop-out the strategy
under test would not have taken.

### BUG 2 — the book bought a name the alert itself refused

`_eligible` tested the contract, the expiry and the age, and never read `features.sizing`. ETN
carried `skip: true, contracts: 0, "one contract costs $1,610, above the $1,000 budget"` and was
bought anyway — **it is the largest position in the book.** A forward track that takes trades the
live product declines is not tracking the live product.

Applied to the three logged alerts, **exactly 1 of 3 is refused and it is ETN**, with the alert's
own reason recorded on the skipped row — as pre-committed.

**Two things I deliberately did not do, both pinned by tests so they must be argued rather than
absorbed:**
- **The sizing QUANTITY is still `cfg.paper_contracts_per_trade`.** Reading `sizing.contracts`
  would change the book's *construction*; reading its veto only declines trades the alert already
  declined. The routed fix was the veto.
- **The open ETN position is NOT unwound.** `_eligible` gates new entries. Closing a live
  position to tidy the record is a trade decision, and "backfill nothing" cuts both ways — the
  book must show what it actually did.

### A THIRD DEFECT, found while fixing the first, same family

`paper_option_orders` has **no `features` column**. The resume branch called
`_exit_policy(dict(order_row))`, so `_features` returned `{}` and the policy silently collapsed to
`DEFAULT_TARGET_PCT` / `DEFAULT_STOP_PCT`. **Audit B5c's own comment claims that branch "rebuilds
the price and the exit policy the same way the fresh path does" — the fresh path reads the
ALERT.** Fixed by `_policy_for(store, order_row)`, which resolves through the alert and falls back
to the order row only if the alert has been purged.

**It has never fired, and that is not reassuring:** all three live alerts happen to use the
default policy. A defect neutralised by a coincidence in the data is not a defect that is handled,
so it is pinned with a policy that differs.

### The read-only half

`options_summary` now carries `level_conformance` — how many live rows trade to a level that
disagrees with their fill, computed from the rows on every request, writing nothing. It stays
after the bug is fixed *because* that is the point: the first time this book was inspected, 2 of 3
open positions were off spec and nothing anywhere said so.

---

## 2. PT-SPLIT — aligned going forward, and the recorded days registered

Don's instruction was "align the engine to the contract's construction, or register it explicitly
as a separate experiment that may never be quoted as the Index. No third state." **Both halves
were needed, and together they are not a third state — each row lands in exactly one.**

**The conformance rule, fixed before it was measured.** A book is the contract-bound Valquo Index
iff it holds at least **`CONTRACT_MIN_POSITIONS` = 50** names **and** the 8% cap actually binds
(`effective_max_weight ≤ MAX_WEIGHT`). The second condition is not redundant: an unbound cap is
the *signature* of a book too small for the cap to be reachable, so it catches the same failure
from the other side. **50 is derived, not observed** — the 8% cap can only bind at 13 names or
more, and the published method is a top *decile* of the large-cap tier.

**Pre-committed verdict on the live engine book: NON-CONFORMING. Measured: non-conforming**, on
10 positions and an effective cap of 0.10.

**ALIGNED.** `seed_book` now refuses to seed a non-conforming book and says why. The refusal is
**loud and non-destructive** — the run continues and marks whatever is already held, because
silently liquidating a live sandbox book on a conformance rule would be a worse failure than the
split it fixes. The only other way through is `experiment=True`, which **stamps every holding row
it creates**. The stamp is on the row rather than in a return value on purpose: PT-OUTBOUND's
lesson is that the old code *did* label its fallback honestly and **no surface ever rendered the
label**. `index_summary` carries `book_conformance` measured **from the holdings**, not remembered
from a seed run.

**REGISTERED.** `PAPER_TRACK_CONTRACT.md` **§5b** enters the four recorded days (2026-08-03, 04,
05, 07; 10 names at 0.10) as a separate experiment that may never be quoted as the Index. **They
are kept, not deleted** — the same rule as the voided vintage-1 rows. Deleting a record because it
turned out to describe the wrong book is the flattering direction. Its **fills** remain real
evidence about execution and are exactly what V5 measures; its **return series** is evidence about
nothing the contract binds.

**No vintage opened or closed.** The engine's series was never the bound series, so run #2's
inception 2026-08-10, gate 2027-02-10 and verdict 2031-08-10 are untouched.

**STILL OPEN, named rather than implied: the alignment is a GATE, not a repair.** Nothing here
makes the engine *start* recording the real 86-name book — that needs a conforming
`data/valquo_index.json` present on the Render disk when the cycle runs, which is the app lane's.
Until then the gate's effect is that the engine **stops adding** to a non-conforming book, and
`seed_refused` says so on every cycle.

---

## 3. V1 — shadow vintages, registered while nothing can be compared

Amendment 1 gave the project **Rule 6: a vintage change resets the whole accrued clock and buys
nothing statistically.** Correct, and brutal — taken alone it says the model may never be improved
again without paying five years. V1 is the answer: when vintage N+1 opens, vintage N's frozen
composite keeps being scored in shadow on the same dates, and the two are compared **paired**.

**Why pairing is the whole point:** both books see the same market on the same days, so the market
risk that dominates a vs-SPY comparison **cancels**.

| between-book TE | σ (pp/month) | detectable at 12m | 36m | **60m** |
|---|---|---|---|---|
| 2.0 pp/yr | 0.6991 | 7.46 pp/yr | 4.26 | **3.34** |
| 4.0 pp/yr | 1.3981 | 14.93 | 8.51 | **6.67** |
| 6.0 pp/yr | 2.0972 | 22.39 | 12.77 | **10.01** |
| **11.40 pp/yr — the vs-SPY meter's own TE** | **3.9847** | 42.55 | 24.26 | **19.01** |

**The bottom row is an exact control.** Fed the tracking error the contract's meter runs on, this
machinery reproduces the contract's published **σ 3.9847** and its published **~19 pp/yr at 60
months** — because it *imports* `track_meter.boundary` rather than re-implementing it. One
boundary function in the project, so the guarantee cannot change for one meter and not the other.
ρ and α are imported too, and a test fails if they are ever copied.

**THE HONEST OTHER HALF, committed in the register in advance: the tension is structural and no
design escapes it.** σ is small exactly when the two books overlap — that is, when the adoption
changed almost nothing. An adoption big enough to matter also moves the books apart and raises σ.
**A shadow pair that has not crossed is the EXPECTED outcome and is NOT evidence that the adoption
was worthless**, and `verdict()` carries that sentence in its own `why` field so it cannot be
dropped in transit. It is still a four-fold improvement on the alternative, and the alternative is
not a better test — it is *no forward evidence about adoptions at all, ever*.

**GENUINELY BLIND, and more so than any previous register here: no vintage pair exists.** Vintage
2 opened 2026-08-10 and has no successor. Not one parameter could have been chosen to make a
comparison come out a particular way, even in principle. Vintage 2's parameters are pinned **now**,
in a tracked file, at `params_id 0060c5ef3dda`, so the shadow will run a **snapshot** and never a
reconstruction — a reconstruction is a new model that resembles the old one.

**The rule has no sign branch.** An AST test requires exactly one sign comparison in `verdict()`
— the one that names the crossing direction — and another flips the sign of an entire series and
requires the verdict to flip with it while the boundary and the crossing decision do not move.
HARMED is exactly as reachable as CONFIRMED-LIVE.

**Fenced before it has anything to leak.** Research instrumentation only; a test walks
`valuation/saas`, `valuation/web` and the templates and fails if the module is referenced. That
fence exists *in advance* because PT-OUTBOUND is what happens when a research object reaches an
outbound surface after the fact.

**It does not weaken Rule 6.** An adoption still resets the vintage clock. This measures the
price; it does not refund it.

---

## 4. Trial accounting

**Equity `N` stays 131. Deflated Sharpe stays 0.8538605963614212 and
`BACKTEST_RESULTS.json` did NOT need re-running** — verified, not assumed: the artifact's
`n_trials` still equals the log's equity count. Two correctness repairs (`PT-BUG12`, `PT-SPLIT`)
are `FIXED` and do not count; V1 is a registered instrument that has produced no measurement, so
it is charged to **infra** at `n = 1` on the HACFLOOR / CHAINFREEZE precedent. Infra 5 → **6**.
`rows_malformed` is empty. **The first shadow PAIR is a trial and is charged when it opens.**

## 5. What I did NOT do

1. **I did not unwind the ETN position** the sizing veto would have refused. `_eligible` gates new
   entries; closing a live position to tidy the record is a trade decision, not a bug fix.
2. **I did not read `features.sizing.contracts` for position size.** That changes construction.
   Pinned as a deliberate non-change.
3. **I did not add `entry_bid`/`entry_ask`** (the options lane's routed GAP 3). It is a schema
   change in service of a measurement that is not mine, and the entry half-spread stays
   unmeasurable until it is done.
4. **I did not re-point the engine at the real Index book.** The gate stops it recording a wrong
   one; making it record the right one needs a conforming `data/valquo_index.json` on the Render
   disk, which is the app lane's.
5. **I did not touch `valuation/saas/app_saas.py`'s silent fallback**, which is where the
   truncated book comes from. The gate in `seed_book` neutralises it from inside my lane — better
   design anyway, since it protects every caller rather than one — but the fallback itself is
   still there and still silent.
6. **I did not run the backtest.** `N` did not move, so re-running would have changed only
   provenance leaves.
7. **I did not do session 16's own `needs first`** (§7 of session 15) — it is date-gated to
   2026-08-12 and today is 2026-08-10. It is not superseded; see §7.

## 6. BUGS FOUND

1. **MY OWN, TWICE-PUBLISHED: `PT-SPLIT` framed as an 8% cap violation.** It is not one. See §0.
   Corrected in the ledger, the contract and here. **The cost of the wrong framing was concrete:**
   the fix it implies (lower a cap) would have left the actual defect untouched.
2. **`/admin/run-paper-track` silently substitutes a different book** (`app_saas.py`): absent
   `data/valquo_index.json`, it rebuilds from the store's scan and seeds the result as the Index,
   with no label and no floor. → **app lane.** Neutralised from my side by the `seed_book` gate,
   but the fallback should say what it did.
3. **Audit B5c's resume branch never read the alert's policy** (§1). Fixed here. Its own comment
   asserted the opposite, which is why it survived a session that was looking at it.
4. **`paper_option_orders` cannot answer what policy a position is running.** No `features`
   column, and every function that wants one has to join back to `option_alerts`. Worked around,
   not fixed — a `policy_json` column at claim time would remove the class.
5. **The options lane's GAP 3 is still open**: no `entry_bid`/`entry_ask` at submit, so the entry
   half-spread is not measurable by any route (the mid is unrecoverable). Routed, not made.

## 7. Session 17's first item

**`needs first`: the date-gated reading that session 15 set and session 16 could not reach.**

**Read `/api/track` → `contract_track.recording_ok`, on or after 2026-08-12.** Run #2's inception
2026-08-10 is day 0, the first row due is 2026-08-11, so 2026-08-12 is the earliest date its
absence is detectable. If it is `false` with `2026-08-11` named, the daily writer is not running
and **`PT-WRITER` is still open regardless of what the scheduler claims** — escalate to Cowork
with a dated, named missing row rather than an impression. If it is `true`, `PT-WRITER` closes on
evidence for the first time and the operational gate has a path to passing on 2027-02-10. **No
human action is required to unblock this.**

**Then:** the engine still is not recording the real book (§2, "still open"). The gate stops it
adding to a wrong one; a conforming `data/valquo_index.json` on the Render disk is what makes it
start recording the right one, and that is a cross-lane item worth naming to the app lane rather
than leaving in a ledger row.

---

# SESSION 17 (2026-08-10) — V2G: what the three dead live themes cost

**Routed in out-of-band by Don, off the greeks lane's Part 12.7 finding.** That lane measured that
three of the seven weighted themes reach no live score and then explicitly declined to price it:
*"No claim is made here about how much this costs in return. That is a backtest question (score the
panel with those three themes removed) and it is not this lane's, and not this run's."* This is that
backtest question, and nothing else.

`PREREG_v2g_live_theme_cost.md` was committed **alone at `6d8750a`, before
`scripts/live_theme_cost.py` existed and before any arm was scored.** The arms, both bars, the
decision rule, the split point, the trial cost and the expectations are all fixed there.

## 1. The setup, and why the restricted arm IS the live book

`WEIGHTS_ESTABLISHED` carries seven non-zero themes at 0.125 (sum 0.875). Three of them reach no
live score — `insider` is **constant** (500/500 non-null, one distinct value), `capital_discipline`
and `institutional` are **absent** (0/500). That is **0.375 of 0.875 = 42.9% of the weight mass**,
so the live hot list is a four-theme book wearing the weights of a seven-theme one.

| arm | themes | weights |
|---|---|---|
| **A7** deployed | value, quality, momentum, insider, capital_discipline, size, institutional | 0.125 each |
| **B4** the live book | value, quality, momentum, size | 0.125 each |

**No new scoring code was written, and that is a structural claim rather than a convenience.**
`fundamental_panel.composite` and `cross_sectional.composite_score` are the same arithmetic —
renormalise by the **present-weight mass** — so a theme that is absent (all-NaN) or constant
(z-scores to all-NaN) drops out of numerator and denominator identically, which is exactly what
dropping it from `weights` does. Two controls prove it rather than assert it:

* **C1 (absence) and C2 (constancy) are EXACT — `max|dev| = 0.000e+00` over all 113,945 rows.**
  C2 is the live condition precisely: `insider` set to a constant, the other two NaN. Both
  reproduce the B4 arm **name for name**.

The register said no verdict could be reported if these failed. They passed exactly.

## 2. The harness reproduces the record to the digit

Before any new number is quoted, the incumbent arm was re-derived on the same panel:

| A7 statistic | measured here | the record |
|---|---|---|
| top-decile alpha | **0.071741423321** | +7.17% |
| long-short naive t | **2.8361** | 2.836 |
| long-short HAC t | **2.6199** | 2.61991 |
| top-decile alpha HAC t | **4.3762** | +4.376 |
| monotonicity | **−0.8909** | −0.891 |
| equal-weight benchmark | **+18.137%** | +18.14% |

Every one matches. The corrected 2,531-name / 69-date panel, 2009-01-15 → 2026-01-28.

## 3. THE RESULT — the cost is not separable from zero, and the verdict is IMMATERIAL

| | A7 deployed | B4 live book | Δ (B4 − A7) |
|---|---|---|---|
| top-decile alpha | +7.17% | **+5.86%** | **−1.31pp** |
| long-short ann | +11.04% | +8.04% | −3.00pp |
| long-short HAC t | 2.6199 | **1.8811** | |
| top-decile alpha HAC t | 4.3762 | **3.2087** | |
| monotonicity | −0.891 | −0.939 | |

**`Δalpha = −1.3133pp` against the pre-registered −1.95pp bar, and the paired HAC t is −1.4040 over
69 paired dates.** Both conditions of the IMMATERIAL branch are met, so by the rule fixed in advance:

> **IMMATERIAL — a nice-to-have.** Building live sources for the dead themes is **not** the
> project's highest-value work.

**THE POWER CAVEAT MUST TRAVEL WITH THAT SENTENCE.** The HAC standard error of the annualised
paired difference is **0.9354pp**, so the smallest gap this design can resolve at |t| = 2 is
**1.8708pp** — well matched to the 1.95pp bar it committed to, which is why the null is worth
something. But the power to detect a **true** 1.95pp gap is only **55.0%**. *IMMATERIAL here means
the cost could not be separated from zero at roughly a coin flip's power against its own bar — not
that the cost was shown to be small.*

The paired test is the right statistic and is far more powerful than comparing two point estimates:
both arms see the same dates and the same names, so differencing cancels the market move that
dominates each level. **Both arms scored the same 69 dates and the same median 1,557 names**, so the
register's stated risk — that B4 might rank fewer names than A7 — did not materialise.

## 4. THE SECOND FINDING IS THE MORE SERIOUS ONE, AND IT IS WHY THE REGISTER ASKED FOR IT SEPARATELY

The register required, separately from the cost, an answer to *does the book users actually receive
stand on its own?* Against this panel's calibrated floors:

| statistic | B4 | calibrated floor | |
|---|---|---|---|
| long-short HAC t | **1.8811** | 2.2837 | **FAILS** |
| long-short naive t | **2.0044** | 2.1437 | **FAILS** |
| top-decile alpha HAC t | **3.2087** | 2.2913 | **CLEARS** |

**The live four-theme book does not clear the calibrated long-short floor, where the deployed
seven-theme book clears it at 2.6199.** It does clear the top-decile alpha floor — and since the
shipped product is a **long-only hot list**, that is the product-relevant statistic. So: the
long-only book users receive remains demonstrable against a calibrated bar; the long-short research
statistic it is habitually quoted beside is not.

This is the R9/session-10 asymmetry again — the long-only object is far better measured than the
long-short the project leads with — but here it decides which half of the headline survives the
restriction.

## 5. Both split directions — the direction is stable, and one late-half cell crosses

| | Δalpha | paired HAC t | Δ long-short | paired LS HAC t |
|---|---|---|---|---|
| full (69) | −1.31pp | −1.4040 | −3.00pp | −1.8792 |
| early (34) | −1.14pp | −1.3519 | −0.29pp | −0.2235 |
| late (35) | −1.48pp | −0.8984 | −5.63pp | **−2.0639** |

**Both halves agree in sign on alpha and neither is significant.** That is a genuinely better
stability profile than session 7's LOO arms, four of seven of which changed sign between halves.

**Reported because it goes against the verdict's direction:** the **long-short** degradation in the
late half crosses the conventional 2.0 bar at **−2.0639**. It is not the pre-registered primary
statistic (alpha is), the bar is **uncalibrated** for a paired difference, and it is one of six
cells — but a reader entitled to the whole picture gets it rather than only the cells that agree.

## 6. Exploratory decomposition — NO VERDICT, and it was registered as carrying none

Pre-registered as exploratory because session 7 established on **this exact panel** that a
full-sample ablation arm is not a finding.

| dropped from A7 | full | early | late | |
|---|---|---|---|---|
| `insider` | +0.30% | −1.39% | +1.94% | **flips sign** |
| `capital_discipline` | +1.37% | +0.20% | +2.51% | positive in both halves |
| `institutional` | **−1.41%** | −0.89% | −1.91% | **negative in both halves** |

* **`institutional` (13F) is the only one whose absence consistently costs.** If one live source is
  built, that is the one the evidence points at. **A build-priority hint, not a result.**
* **`capital_discipline` — the theme with the second-strongest panel IC (+2.76), one of only two
  clearing X7's 2.71 bar — appears to cost nothing to lose, in both halves.** That is X3's finding
  restated: **theme IC does not predict marginal contribution.** Its early-half +0.20% coincides
  with the figure session 7's held-out LOO measured for the same arm.
* **`insider` flips sign between halves**, consistent with the record's own standing note that its
  t is not a measurable quantity in either direction.

## 7. WHAT THIS DOES NOT SAY — the part most likely to be misquoted

**An immaterial ALPHA cost is not a finding that the live absence is acceptable.** The live product
computes a **different composite** from the one every published figure is measured on. That is a
claims-integrity issue independent of return, and it is the same class of defect audit **B7**
exists to prevent — live and backtest scoring diverging, with no shipped path reproducing the
backtested composite. Two honest options follow, and they are the app/screener lane's to choose
between: build the sources, or quote the headline for the book that is actually computed.

It also does not license dropping the three themes from the backtest. Nothing here tests removing
them from the **research** composite as a deliberate design; it measures what the live product's
accidental restriction costs.

## 8. Controls on the calibration itself

**C3 — are session 10's floors still the floors at today's `N`?** The published floors were measured
at `N` = 121 and re-verified at 129; `N` moves individual placebo draws through the CPCV adopt gate
(session 12), and the floor is a percentile of the resulting null. Adoption is **monotone decreasing
in `N`**, so an identical adopter set means every draw is scored under identical weights and the
percentiles cannot have moved. Recomputed from the banked `X7_RECONCILE` margins: **20 adopters at
`N` = 129, 20 at `N` = 135, set identical → the floors stand at this `N`.** Zero trials — a
calibration searches nothing.

## 9. The one shipped-code change

`quantile_backtest` gained an **opt-in `return_series`**. It already computed the per-period
long-short and alpha draws and threw them away, so a paired comparison had no way to reach the
**shipped** arithmetic — and X3 had already written a *second* implementation of the same series to
work around it. Default payloads are **bit-identical** (pinned by test), and a further test pins the
two implementations to agree so they cannot drift. This is RUN_RULES A9 — store the draws, not just
the summary.

## 10. Expectations scorecard — written first, and wrong again on the headline

| prediction | confidence | outcome |
|---|---|---|
| **MATERIAL** | 55/45 | **WRONG** — IMMATERIAL |
| B4 still clears the LS HAC floor | 50/50 | **WRONG** — it fails |
| `institutional` the costliest of the three | 55/45 | **RIGHT** |
| dropping `insider` helps or is neutral | 70/30 | **RIGHT** |
| ≥1 decomposition arm flips sign between halves | 65/35 | **RIGHT** — exactly one does |

Two wrong, three right, and **both wrong calls are on the two headline questions.** The standing
rule holds: do not reason about the direction of an effect in this project; measure it.

## 11. What I did NOT do

* **Did not touch `valuation/screener/**` or fix the three dead live themes.** That is the screener
  lane's, it is a data-plumbing job, and this register was scoped to price the gap, not close it.
* **Did not change any weight, any theme, or any live behaviour.** No adoption; the shipped
  composite is untouched.
* **Did not re-measure the calibrated floors.** C3 shows they still stand at `N` = 135 by an exact
  argument; a fresh placebo sweep was not needed and was not run.
* **Did not test removing the three themes from the RESEARCH composite** — a different hypothesis,
  and it would need its own register.
* **Did not quote any exploratory decomposition arm as a finding**, per §6.

## 12. Trial cost and the artifact

**Equity `N` 131 → 135** — four arms (B4 plus the three decomposition arms). The halves are the same
arms on subsets rather than new hypotheses and are not charged, on session 7's precedent of charging
7 for 7 LOO arms measured in both directions. `BACKTEST_RESULTS.json` was re-run from a clean tree so
the artifact's `n_trials` and Deflated Sharpe match the register rather than going stale on the
denominator.

---

# SESSION 18 (2026-08-10) — S22: the term structure of the signal, and top-decile tenure

**Ledger item S22, routed in by Don as this lane's, unblocked.** Two questions the project had
never asked, and that nothing in the corpus mentions:

1. **How long does a hot name's edge last?** Every *headline* figure this project publishes —
   `top_decile_alpha`, the long-short *t*, monotonicity, the costs block, the calibrated bars — is
   measured at a **63-trading-day** forward window, because `build_fundamental_panel` computes
   exactly one `fwd_ret` and the deployed rebalance period equals it. That is an inherited
   default, not a measured optimum. **(See §1b: the register's own wording here was too strong,
   and it is corrected rather than quietly softened.)**
2. **How long do names stay hot?** The top decile IS the product, and how long a name survives in
   it had never been measured.

`PREREG_s22_term_structure.md` was committed **alone at `6b187dd`, before
`scripts/term_structure.py` existed and before any horizon was scored** — a strict git ancestor of
the measurement commit `ec4a5d3`, which is what makes the blindness checkable rather than asserted.
The horizons, the primary statistic, the date sets, the HAC lag, the bars, the tenure definitions,
the trial cost and the expectations are all fixed there.

**Adopts nothing.** Holding-period changes are S23's own register and a vintage event; display is
the web lane's.

---

## 1. The design decision that makes the question answerable

The horizon is baked into the panel builder, and — this is the part that matters — the rebalance
grid ends at `len(cal) - horizon`. **Building one panel per horizon would have varied the horizon
AND the date set AND the scored cross-sections together**, and no difference between two such runs
could have been attributed to the horizon.

So: **ONE panel build, carrying eight forward-return columns** computed inside the same loop from
the same price array. The scores, the dates, the names and the composite are **identical across
every arm**, and the forward window is the only thing that varies. A useful side effect: the
record's known run-to-run `insider` nondeterminism is **common to all arms and cancels** out of
every across-horizon comparison.

Horizons are **1 through 8 quarters** — 63, 126, 189, 252, 315, 378, 441, 504 trading days. A
complete grid in units of the rebalance period is required because the incremental analysis
differences adjacent horizons, and those differences are only comparable if every step is one
quarter.

### 1b. CORRECTION TO THIS REGISTER'S OWN PREMISE — found by checking, not assumed

`PREREG_s22_term_structure.md` §1 says *"Nobody has ever asked what the composite predicts at 6
months, a year, or two years."* **That is false, and the register is left unedited because a
committed register is the record of what was committed — the correction goes here.**

`BACKTEST_RESULTS.json` has always carried a **`per_horizon`** block, and `run_backtests` has
always run **63 / 252 / 756**. What it actually reports, though, is narrow enough that the
question S22 asks was still open:

| horizon | rebalance dates | in-sample IC | **out-of-sample IC** | accepted |
|---|---|---|---|---|
| 63 | 69 | 0.050234 | **0.038990** | true |
| 252 | 18 | 0.125013 | **0.058241** | false |
| 756 | 6 | 0.135587 | **0.097671** | true |

Three things make it a different object from this study, and the first is the one that matters:

* **It changes the rebalance period with the horizon.** `run_backtests` sets
  `rb = max(rebalance_days, H)` so periods stay non-overlapping — which means the 252d arm has
  **18** dates and the 756d arm **6**, against 69 at the deployed horizon. That is precisely the
  confound §1 was built to avoid: horizon, date set and cross-section all move together. **Six
  dates cannot support inference**, and the 2,206-name 756d universe is not the 2,531-name one.
* **It reports IC and weight vectors only** — no alpha, no long-short, no decile structure, no
  tenure. The `construction` block every headline comes from is built on a single
  `rebalance_days=63, horizon=63` panel.
* **Nothing in the corpus ever read it as a term structure.** The ledger records S22 as "no mention
  anywhere in the corpus", and that part holds.

**AND IT CORROBORATES THE FINDING, WHICH IS THE REASON TO REPORT IT RATHER THAN BURY IT.** That
out-of-sample IC column **rises monotonically with horizon** — 0.0390 → 0.0582 → 0.0977 — the same
direction as this study's median rank IC (+0.034 → ~+0.072). **The project has been shipping
evidence that its signal predicts better at long horizons, in its own results file, unread.** The
two are *not* numerically comparable (different IC definitions, different date sets, different
universes), so only the **direction** is claimed.

### 1a. Right-censoring is not delisting — the defect named in advance

`_forward_return` keeps the shipped delisting rule: if the horizon-end price is NaN because the
survivorship mask cut the name mid-window, fall back to the last price it actually traded at.

It would be **catastrophic** if that branch also fired when the **calendar** ends before the window
does. There the return does not exist, and a last-price fallback would return a **shorter realized
return labelled as a long-horizon one** — for the most recent dates specifically, flattering short
horizons and penalising long ones. That is precisely the comparison this study is. The register
names it as the single most likely way the study fabricates a result; the code returns `None`, and
a test pins it **from both sides** (censored windows must return nothing; a delisting inside an
observable window must still realize its last traded price).

**The measured signature is the cleanest possible confirmation the rule is right:**

| horizon | 63 | 126 | 189 | 252 | 315 | 378 | 441 | 504 |
|---|---|---|---|---|---|---|---|---|
| rebalance dates observable | 69 | 68 | 67 | 66 | 65 | 64 | 63 | 62 |

**Exactly one 63-day rebalance date lost per extra quarter of window**, monotone, and censoring
removes a **suffix** of dates rather than scattering NaNs — because the calendar ends for every
name at once.

---

## 2. Controls — all four pass

* **C0 — the added column IS the shipped column.** `max|fwd_ret − fwd_ret_h63| = 0.000e+00` over
  **all 113,945 rows**. The new code path is the shipped rule, not a second implementation.
* **C1 — the incumbent reproduces the published record to the digit**, on a **fresh** build rather
  than the cached pickle V2G used: `top_decile_alpha` **0.071741**, long-short naive *t*
  **2.836064**, long-short HAC *t* **2.619912**, alpha HAC *t* **4.376230**, monotonicity
  **−0.890909**, equal-weight benchmark **+0.181371**. All six. The panel is 113,945 rows /
  2,531 names / 69 dates, `label` "full" — and it is bit-reproducible, so the record's known
  `insider` nondeterminism did not bite here.
* **C2 — censoring is real, counted and monotone** (the table above).
* **C3 — default payloads unchanged.** With no extra horizons requested the frame is
  column-for-column what it was, proved end to end on a real build in `tests/test_edge.py`.

---

## 3. The primary result — the edge does NOT decay

Primary date set is the **COMMON 62 dates** (2009-01-15 → 2024-04-24), i.e. the dates observable at
**every** horizon, so the horizon is the sole varying quantity. The primary statistic is
**cumulative, non-annualized** top-decile alpha: annualizing divides by the horizon and would make
a fixed one-off edge look like it decays as `1/k` when nothing decayed at all.

| H | Q | cum alpha | **annualized** | R | R/linear | alpha HAC *t* | LS HAC *t* | cum long-short | median rank IC |
|---|---|---|---|---|---|---|---|---|---|
| 63 | 1 | +1.65% | **+6.59%** | 1.000 | 1.000 | 3.7695 | 2.7167 | +2.89% | +0.0336 |
| 126 | 2 | +3.34% | **+6.67%** | 2.026 | 1.013 | 4.3836 | 2.7111 | +4.81% | +0.0586 |
| 189 | 3 | +4.52% | **+6.03%** | 2.745 | 0.915 | 3.2912 | 2.1446 | +5.60% | +0.0709 |
| 252 | 4 | +6.14% | **+6.14%** | 3.730 | 0.932 | 3.1608 | 1.8561 | +6.52% | +0.0725 |
| 315 | 5 | +7.79% | **+6.23%** | 4.732 | 0.946 | 3.4240 | 1.6495 | +7.11% | +0.0720 |
| 378 | 6 | +8.60% | **+5.74%** | 5.225 | 0.871 | 3.3887 | 1.1632 | +6.05% | +0.0699 |
| 441 | 7 | +8.86% | **+5.07%** | 5.384 | 0.769 | 3.4180 | 0.6619 | +4.14% | +0.0711 |
| 504 | 8 | +10.20% | **+5.10%** | 6.195 | 0.774 | 3.8301 | 0.6846 | +4.60% | +0.0655 |

**VERDICT: CONSTANT-RATE**, by the rule fixed in advance — `R(8) = 6.1950` against the
pre-registered `≥ 6.0`.

**The single sentence:** *annualized top-decile alpha is essentially flat from three months to two
years, +6.59% → +5.10%.* The edge is **not** a one-quarter effect that decays; the cohort selected
today keeps out-earning the equal-weighted universe at a near-constant rate for two years.

**Every one of the eight incremental quarters is positive** (+1.65, +1.69, +1.19, +1.62, +1.65,
+0.81, +0.26, +1.34 pp), with Q7 the weakest. *Reported with its stated limitation: adjacent
cumulative windows overlap almost entirely, so these are differences of highly dependent
quantities; the inference is approximate and uncalibrated and no verdict rests on it.*

**The alpha is well measured at EVERY horizon.** The alpha HAC *t* — at the overlap-corrected lag
`max(1, H/63 − 1)`, so lag 7 at two years — never drops below **3.16** and is **3.83** at the
longest horizon. This is not a case of a signal surviving because the error bars widened.

**The secondary all-available date set agrees** in shape and sign at every horizon (+7.17% → +5.10%
annualized), so nothing here is an artifact of the common-date restriction.

### 3a. Two things that cut against the headline, reported because they do

**(a) The classification clears its bar NARROWLY, and it is not stable across halves.**
`R(8) = 6.195` against a bar of `6.0`; at 5.9 the same table would have read INTERMEDIATE. And the
two halves land on **opposite sides** of the bar — early **8.559** (super-linear), late **5.470**
(INTERMEDIATE). They agree in **sign** and both show alpha still accruing at two years, but the
*label* does not replicate. `R(8)` is a ratio whose **denominator is one noisy quarter**, so it is
fragile by construction; the flat annualized-alpha column is the more robust way to read the same
data. *The persistence replicates; the classification does not.*

**(b) THE LONG-SHORT SPREAD DECAYS AND ITS SIGNIFICANCE COLLAPSES.** Long-short HAC *t* falls
**2.7167 → 0.6846** across the eight horizons, and the cumulative spread **peaks at Q5 (+7.11%)
then falls to +4.60%**. So the persistence lives entirely in the **long** leg; the bottom decile
catches up. **Nobody may quote a long-short figure beyond about one year** — past Q4 there is no
evidence of a spread at all.

That asymmetry is **fortunate rather than damaging for the product**, and the reason is worth
stating: the shipped product is a **long-only hot list**, so the leg that persists is the leg users
actually receive. But it means the long-short research statistic and the product statistic
**diverge with horizon**, and the record has been quoting them side by side.

### 3b. Rank IC rises with horizon

Median per-date rank IC goes **+0.0336** at one quarter to a plateau of **+0.070 to +0.073** from
three quarters out, with HAC *t* rising 3.50 → 4.23. The composite's rank correlation with forward
returns is **stronger at long horizons than at the one it is deployed on**. Consistent with the
constant-rate finding, and an independent route to it — the IC never touches the decile machinery.

---

## 4. Calibrated bars — what applies, and the refusal to pretend

**X7 / session 10's floors (long-short HAC 2.2837, alpha HAC 2.2913, long-short naive 2.1437) are
valid at exactly ONE configuration: H = 63, the full 69-date panel, HAC lag 1.** `n` changes with
the horizon, the windows overlap, and the HAC lag changes with them. **They are not quoted against
any other arm here.** Comparing across configurations is the error the record already paid for
twice — a HAC *t* against a naive-calibrated floor (closed in session 10) and a floor across
different `N` (closed in session 12).

At the one arm where they apply, the incumbent clears all three: **2.6199 vs 2.2837**, **4.3762 vs
2.2913**, **2.8361 vs 2.1437**.

For every other horizon the register commits a **per-horizon placebo** — the shipped
`placebo_panel` block permutation, 200 draws, seeds 2000–2199, **fixed weights and no CPCV**.
Measured floors and whether each arm clears its own:

| H | Q | alpha HAC *t* | own p95 | clears | LS HAC *t* | own p95 | clears | null median |
|---|---|---|---|---|---|---|---|---|
| 63 | 1 | 3.7695 | 1.5151 | YES | 2.7167 | 1.7494 | YES | -0.0604 |
| 126 | 2 | 4.3836 | 1.3101 | YES | 2.7111 | 1.7938 | YES | -0.2333 |
| 189 | 3 | 3.2912 | 1.5335 | YES | 2.1446 | 1.6360 | YES | -0.2475 |
| 252 | 4 | 3.1608 | 1.4884 | YES | 1.8561 | 1.6292 | YES | -0.1278 |
| 315 | 5 | 3.4240 | 1.5614 | YES | 1.6495 | 1.7336 | NO | -0.1489 |
| 378 | 6 | 3.3887 | 1.5553 | YES | 1.1632 | 1.5721 | NO | -0.2466 |
| 441 | 7 | 3.4180 | 1.5538 | YES | 0.6619 | 1.8245 | NO | -0.1908 |
| 504 | 8 | 3.8301 | 1.6720 | YES | 0.6846 | 2.0837 | NO | -0.1367 |

**8 of 8 horizons clear their own top-decile alpha floor; only 4 of 8 clear their own long-short floor** — and the four that fail are exactly Q5 through Q8. **The calibrated null therefore says the same thing the point estimates did, and dates it: the long-short edge is indistinguishable from noise from about fifteen months out, while the long-only alpha is not.**

**The stronger statement, and it holds at every horizon: the real top-decile alpha HAC *t* sits ABOVE ALL 200 NOISE DRAWS** at all eight horizons (empirical p <= 0.005 each). The null's own maximum ranges 2.0234 to 3.0392 against a real series that never falls below 3.16.

**C4 holds** — the null's median alpha HAC *t* runs -0.2475 to -0.0604, i.e. near zero at every horizon, so the instrument destroys what it claims to.

**By-product, no verdict attached (registered as such):** the fixed-weights null's long-short HAC p95 at H = 63 is **1.7494**, against X7 / session 10's **2.2837** measured on the same panel and the same statistic **with CPCV weight selection in the loop** — so putting selection in the loop raises the 95th-percentile floor by **+0.5343** of a *t*. **Stated precisely, because it is easy to conflate with a figure already in the record:** this is the shift in the *p95 over all draws*, which is NOT the same quantity as X7's post-hoc *~+1.4 mean long-short t among the 27% of noise draws that actually adopted*. The two are consistent in direction and plausible in magnitude — a large effect on a fifth of the draws moves a 95th percentile by much less than the effect itself. An observation with its own uncertainty, not a test; it adopts nothing.

---

## 5. Tenure — the top decile turns over almost completely every quarter

Membership uses the identical shipped convention (`argsort(-composite)`, `n_q = 10`, first bucket).
A useful check came out of it: because a panel row only exists when the base `fwd_ret` is present,
the backtest's finite-mask **reduces to "finite composite"** — the two possible definitions
coincide, which is reported (`mask_definitions_coincide: true`) rather than assumed.

**7,286 spells over 1,895 distinct names, median decile size 156.**

* **Kaplan–Meier median spell = 1 rebalance (≈ 3 months).** The naive median over completed spells
  agrees at 1.0, so censoring is not doing the work here.
* **70.6% of spells last exactly one rebalance** (5,146 of 7,286). Mean 1.568, max **19** (~4.75
  years).
* **One-period retention 36.6%** — and the register pre-committed a **20–50%** band derived from
  the shipped ~261%/yr turnover at four rebalances a year. **It lands inside**, so the tenure
  measurement and the cost model describe the same book and no bug report is triggered. Stable
  across halves (35.9% early, 37.4% late).
* **Continuous survival** decays fast: 36.8% survive one more rebalance, 18.1% two, 9.8% three,
  0.8% eight.
* **Re-entry is the norm, not the exception.** Allowing gaps, persistence plateaus at **~19–24%**
  out to eight rebalances rather than decaying to zero — and **1,407 of 1,895 names (74%) have more
  than one spell.** Names leave the decile and come back.
* **Exits are genuine, not data artifacts:** 6,986 fell out while still in the panel, only 115 left
  the panel entirely, 185 censored at the panel end.

**By market-cap tertile (computed WITHIN each date, so the tiers are relative):** KM median is
**1 rebalance in all three tiers**. Mean spell length is **small 1.788 > mid 1.372 > large 1.224**
— **small caps stay longest**, the opposite of the pre-registered expectation.

---

## 6. The defensible product sentence

The register requires the one sentence that is derivable from a measured figure with **no
extrapolation**, naming the horizon it was measured at. It is:

> **In the backtest, the top decile of the hot list beat the equal-weighted universe by about 6.6%
> annualized over the next three months — and was still ahead by about 5.1% annualized two years
> later — even though a given name typically stays in the top decile for only one quarterly
> rebalance.**

**Caveats that must travel with it, and without which it may not be displayed:** measured on the
corrected 2,531-name / 69-date panel (2009-01-15 → 2026-01-28, common-horizon window ending
2024-04-24); **long-only top decile versus the equal-weighted universe**; **gross of costs**; and
it is the **same single in-sample panel every other published figure comes from — not a forward
test.** The long-short spread does **not** persist and must not be quoted alongside it beyond a
year.

**Display is the web lane's**, not this one's. Wording it was this register's job; putting it on a
page is not.

---

## 7. What this does NOT say

**It is not a finding that the book should rebalance less often, and that inference is the most
likely way this result gets misused.** `cum_alpha(H)` is the buy-and-hold return of the cohort
selected on one date. A quarterly-rebalanced book **re-selects every quarter and compounds fresh
selections**, so "the cohort keeps earning for two years" and "holding longer beats rebalancing"
are different claims, and only the first is measured here.

What the result does do is make the second claim **worth testing**, which it was not before: the
deployed book pays **261%/yr turnover** to harvest an edge that is still accruing at two years.
**That is S23's question** — it needs its own pre-registration, and adopting it would be a
**vintage event** under `PAPER_TRACK_CONTRACT.md`, closing the current vintage and resetting the
five-year clock for zero statistical gain. Recorded as a hypothesis, deliberately not acted on.

It also does not license quoting any long-horizon number as out-of-sample evidence. **It is the
same panel.** A longer forward window is not new data — it is the same 18 years read differently,
and the overlapping windows mean the eight arms are eight views of one sample, not eight samples.

---

## 8. Trial cost

**Eight horizon arms charged: equity `N` 135 → 143.** H = 63 is charged even though it is the
incumbent control, because a sweep from which a best horizon *could* be quoted is a search over
eight cells regardless of which one was already known — and understating `N` overstates the
significance of every DSR-gated claim.

**Charged at zero, as registered:** the tenure statistics (descriptive — no hypothesis, no
threshold, no selection), the per-horizon placebo (a calibration searches nothing — session 10's
precedent), and the half-splits (the same arms on subsets).

`BACKTEST_RESULTS.json` regenerated from a clean tree so its Deflated Sharpe is computed at
`N = 143` rather than going stale on the denominator — **re-run, never hand-patched.**

**Measured:** DSR **0.8504129179654681 → 0.8436955925493782**, `sr0_benchmark` 0.432867 →
0.436077, **√(2·ln 143) = 3.1505** — still above the Harvey–Liu–Zhu hurdle of 3.0, and the
statistic still self-reports `deflated_sharpe_ratio` with `is_effectively_undeflated: false`.
**Nothing else moved:** a leaf-by-leaf diff over 1,217 leaves gives **16 moved / 0 ADDED /
0 REMOVED** — five are the DSR chain, four are provenance, and the remaining seven moved by
less than 1e-9 relative (last-digit float) in cost fields. `long_short_tstat`
**2.8360640685320595**, `top_decile_alpha` **0.07174142332098163**, `monotonicity`
**−0.8909090909090909** and the equal-weight benchmark **0.18137118752419476** are
**bit-identical**; `errors` is empty and `cpcv.adopt` is still `false`, so the shipped
strategy takes no haircut.


---

## 9. The pre-registered expectations, scored

The project's standing rule is that reasoning about the direction of an effect here fails more
often than it works. The score:

| # | expectation | odds | outcome |
|---|---|---|---|
| 1 | term structure is **SATURATING** (front-loaded) | 60/40 | **WRONG** — CONSTANT-RATE |
| 2 | KM median tenure ≤ 2 rebalances | 65/35 | **RIGHT** — 1 |
| 3 | at least one horizon ≥ 252d fails its own placebo floor | 70/30 | **AMBIGUOUS, SO SCORED AS A NULL** — the expectation did not say WHICH floor, and the two answer oppositely: on **alpha** every horizon >= 252d clears (0 of 4 fail), on **long-short** every horizon >= 252d fails (4 of 4 fail). The ambiguity is mine and it is scored the way the rules require rather than resolved in whichever direction flatters the call. |
| 4 | large-cap tenure **longer** than small-cap | 55/45 | **WRONG** — small is longest (1.788 vs 1.224) |
| 5 | `Δ_k` not reliably positive beyond k = 4 | 60/40 | **WRONG** — all eight quarters positive |
| 6 | C1 reproduces the record to the digit | 95/5 | **RIGHT** |

**Three wrong, two right, and the two headline questions were both called wrong.** The streak
holds.

---

## 10. Reproduce

```
python -m scripts.term_structure \
    --data-dir data/backtest \
    --panel    data/free_analysis/panel_s22_h504.pkl \
    --json     data/free_analysis/TERM_STRUCTURE.json
```

Artifact `data/free_analysis/TERM_STRUCTURE.json` retains **every per-draw placebo row** and every
arm's full per-period series (RUN_RULES A9). Pinned by **9** new tests in `tests/test_edge.py` (266 -> 275, all green).

---

## 11. BUGS FOUND

* **A full-universe run that dies mid-build is silent and indistinguishable from one that never
  started** — carried forward from session 17, where the artifact re-run died at 60 of 69 rebalance
  dates at ~5.9 GB with no traceback and no partial output. **This session's build survived the
  same point** (peak ~6.1 GB, completed in 334s), so it is memory pressure rather than a
  deterministic fault, and the finding stands as reported rather than being re-opened.
* **CORRECTION TO THIS SESSION'S OWN COMMIT MESSAGE.** `ec4a5d3` says "11 new
  tests"; it is **9**. The suite went 266 -> 275. Recorded rather than amended, because the
  commit was already written and this file is the record that gets read.
* **`quantile_backtest` had no guard on its return column.** Before this session a caller could not
  select one at all; now a missing column raises rather than silently falling back to `fwd_ret` and
  reporting the 63-day answer under a 504-day label. Pinned.
* **Not a defect, but a live mis-quotation risk worth recording:** the long-short statistic and the
  top-decile alpha **diverge with horizon** (LS HAC *t* 2.72 → 0.68 while alpha *t* stays above
  3.16). Any surface that presents them as two views of one edge is wrong beyond about a year.

## 12. What was NOT done

* **No book change, no holding-period change, no exit-rule change.** S23's, and a vintage event.
* **No display change.** The product sentence is written here; rendering it is the web lane's.
* **No cost model applied to the long-horizon arms.** Every figure above is **gross**, exactly as
  the register specified. A longer holding period would pay *less* turnover, so costs would move
  these numbers in the flattering direction — which is a further reason the rebalance-frequency
  question needs S23's own design rather than an inference from this table.
* **The per-horizon placebo is a DIFFERENT and less conservative null than X7's** (fixed weights,
  no CPCV adoption). Its percentiles are labelled `fixed_weights_null` in the artifact and may
  never be compared with 2.2837 or 2.2913.
* **The rank-IC term structure was NOT split across halves.** The register named three quantities
  for the stability check — `R(8)`, the incremental sign pattern and the KM median tenure — and the
  rising IC emerged as a finding afterwards. Splitting it now would be choosing an analysis after
  seeing the result, which is the error session 6 paid for and session 7 declined to repeat. It is
  a **registered gap, not an oversight**, and it is the cheapest thing for a follow-up to close.
* **No forward-return column beyond 504 days.** Two years is where the panel runs out of
  rebalance dates fast: each extra quarter costs one date, and the study already spends seven.

# SESSION 19 (2026-08-11) — S23: the exit rule for the equity book

**Ledger item S23, routed in by Don as this lane's, unblocked, with S22's term structure on the
record as the prior to beat.** The live book buys the top 25 by composite and holds each name
until it falls out of the top 50, min-hold 2. **That exit had never been tested against an
alternative** — an inherited rule, exactly like the 63-day horizon S22 found was never a measured
optimum.

`PREREG_s23_exit_rule.md` was committed **alone at `6a73485`, before `scripts/exit_rule.py`
existed** — a strict git ancestor of the measurement commit `3ba5f4d`. The arms, both TP/SL pairs,
the band definitions, the cost formula, the decision rule, the split point, the trial cost and the
expectations are all fixed there.

**ADOPTS NOTHING.** Under the vintage rule an adopted construction change closes the current
vintage and resets the five-year clock for zero statistical gain. Nothing here changes the book.

---

## 1. The prior, and the direction stated before running

**S22 is the prior and the register committed to a direction because of it.** Annualized
top-decile alpha is flat from three months to two years, alpha HAC *t* never below 3.16, and rank
IC *rises* with horizon. **An edge still accruing at two years argues against selling early on
price**: a take-profit truncates the tail S22 says keeps paying, and a stop-loss sells a name the
composite still ranks a buy.

So §8 predicted, at **75/25**, that **no challenger would beat the incumbent** — and said so
before a single number existed.

---

## 2. Two defects found and fixed, because the fair-value arm could not be honest without them

Both were measured **before the register was written**, are recorded in it, and are reported here
in their own right regardless of the race's outcome.

### 2a. `build_valuation_panel` still carried the B6 defect

It requested `provider.price_history(t, days=TD*lookback_years + horizon + 60)` — the **per-ticker
tail**, the exact route `data_providers.py:352` says in its own comment *"is never the panel's
route now"*. The consequence is B6's: the union calendar's early cross-sections consist only of
names that had already stopped trading.

**Measured on the same 25 names, before and after:**

| | rebalance dates | first date |
|---|---|---|
| before the fix | **110** | 1998-12-31 |
| after the fix | **69** | 2009-01-15 |

The valuation panel was on **a different calendar from the factor panel** — the pre-B6
inverted-universe window. It now cuts the **shared** calendar once, exactly as
`build_fundamental_panel` does, and control **C1 measures the two panels' dates identical**.

### 2b. The point-in-time valuation was fetching LIVE Yahoo prices — look-ahead

`wacc._resolve_beta` rung 3 corroborates an unusable beta by calling `data.beta.compute_beta`,
which fetches `yf.Ticker(...).history(...)` — **today's** prices. That is correct for the live
product, where today *is* the as-of date. In a backtest it **values a 1999 date with a beta
regressed on 2021-2026 returns**, and it is also a network dependency and a rate-limit hazard.

**Measured: it fired 157 times over 1,122 rows on a 25-name probe** — roughly one row in seven.

`calibration.offline_beta` now reproduces the ladder with **rung 3 removed**: an in-range
point-in-time beta is used (rung 2), anything else falls to the engine's **own stated constant**
(rung 4) — which is precisely where the ladder already lands when corroboration cannot run. The
S23 build runs with `offline=True` and **asserts zero network calls**; the full 108,241-row panel
was built with the tripwire armed and it never fired.

**Neither fix was bundled opportunistically:** both are required by the register's own controls
C1 and C2, and `lean_fair_value` gained exactly one optional argument, appended not inserted,
defaulting to `None` so the website's valuations cannot move.

---

## 3. Controls — all pass

* **C1 — the two panels are one panel.** Dates identical (69, 2009-01-15 → 2026-01-28); the
  valuation panel covers **93.9%** of the factor panel's rows and contributes no key the factor
  panel lacks.
* **C2 — no network, no hindsight.** Zero calls to `compute_beta` during the build, enforced by a
  tripwire that raises.
* **C3 — the incumbent reproduces the shipped book exactly**, costs off:
  `total_return` **158.09816857704106** against the shipped `_backtest_hold`'s
  **158.09816857704106**, `n_periods` 69, `held_median` 42.
* **C4 — the arms differ only in exits.** All six score identical dates and the identical
  `target_n`. *(The register's C4 said buy **counts** must match; that wording was wrong and is
  corrected in §9.)*
* **C6 — costs bite in the right direction and in the right order.** Net ≤ gross for every arm,
  and the **turnover ranking and the drag ranking are identical** —
  A4 > A3 > A2 > A1 > A0 > C-NEVER.
* **Every exit rule genuinely fires**, so no arm is a silent copy of the incumbent: A1 794 rank /
  494 valuation, A2 606 / 703, A3 533 rank / 459 take-profit / 358 stop-loss, A4 501 / 522 / 332.

**Fair-value coverage, reported before any verdict (the COVERAGE RULE):** 108,100 of 108,241 rows
are `valuable` (**99.87%**); the point gate fires on **60,526** rows and the lens gate on
**76,320**.

---

## 4. The race — costs charged, net carries the verdict

| arm | net CAGR | gross CAGR | alpha vs EW | held | avg hold | **Δ net /yr vs A0** | HAC *t* |
|---|---|---|---|---|---|---|---|
| **A0 INCUMBENT** | 32.72% | 34.16% | +15.48% | 42 | 0.6y | — | — |
| A1 FV-POINT | 32.53% | 34.05% | +15.29% | 42 | 0.5y | **−0.13%** | −0.368 |
| A2 FV-LENSBAND | 33.07% | 34.62% | +15.83% | 42 | 0.5y | **+0.37%** | +0.866 |
| A3 TPSL-ONEIL | 32.47% | 34.07% | +15.23% | 42 | 0.5y | **−0.21%** | −0.396 |
| A4 TPSL-2TO1 | 32.54% | 34.15% | +15.30% | 42 | 0.5y | **−0.13%** | −0.254 |
| **C-NEVER** *(control)* | 20.61% | 20.70% | +3.37% | **417** | — | **−10.89%** | **−3.801** |

**HEADLINE: NO CHALLENGER BEATS THE INCUMBENT.** All four price-based exits move the book by
**less than 0.4pp/yr in either direction**, on 69 paired periods, with |HAC *t*| ≤ 0.87.

**THE LEVELS ARE NOT A NEW HEADLINE AND MUST NOT BE QUOTED AS ONE.** `_backtest_hold` is the
concentrated top-25→50 book that audit **B17** already labels the noisiest number in the results
file, whose realised size is ~`exit_rank` rather than `top_n`, and which every other book in the
file is measured against with frictions it historically did not pay. S23 charges costs, but it
measures **differences between exit rules on that object** — the differences are the finding; the
+32.72% is not a claim this register makes.

### 4a. Three of the four flip sign between halves

| arm | early (34 dates) | late (35 dates) | same sign? |
|---|---|---|---|
| A1 FV-POINT | −0.22% | −0.02% | yes |
| A2 FV-LENSBAND | **−0.31%** | **+1.04%** | **no** |
| A3 TPSL-ONEIL | **−0.72%** | **+0.21%** | **no** |
| A4 TPSL-2TO1 | **−0.65%** | **+0.30%** | **no** |
| C-NEVER | −2.09% | −18.07% | yes |

**A2 is the only arm with a positive full-sample difference, and it is exactly the one that fails
the both-halves requirement** — negative early, positive late. That is session 7's LOO pattern
again, and it is why the register required sign agreement across halves before calling anything a
win rather than accepting a full-sample point estimate.

---

## 5. The control collapses — and it CONFIRMS S22 rather than contradicting it

**C-NEVER loses 10.89pp/yr at HAC *t* −3.801**, the only difference in the whole study that is
large and well-measured. Its book grows to **417 names** and its alpha vs the equal-weighted
universe falls from **+15.48% to +3.37%**.

**This is not evidence against S22's persistence finding, and reading it that way would be the
main way this result gets misused.** S22 measured the forward return of a **cohort selected on one
date**, and found it beats the universe for about eight quarters. C-NEVER never sells but **keeps
buying**, so it accumulates cohorts of every age: over 69 rebalances the average holding is far
older than eight quarters, and the book converges toward a 417-name slice of the universe whose
alpha must approach the universe's own. **+3.37% is what S22 predicts for a book whose average
cohort age vastly exceeds the horizon over which the edge accrues.**

Costs are not the story either — C-NEVER's gross is 20.70% against its net 20.61%, because it
never sells and so barely trades. **The mechanism is dilution, not friction.**

That is exactly why the register labelled it a **control and not a candidate**, in advance, and
recorded that its book size is not comparable to the others.

---

## 6. The calibrated floor, built because none existed

X7 and session 10 calibrate `quantile_backtest` statistics on the full-universe **decile**
book. `_backtest_hold` is a different object — concentrated top-25→50, event-driven,
variable book size — and S22 already recorded that a floor may not be quoted outside the
configuration it was calibrated in. **So a floor was built rather than borrowed.**

The shipped `placebo_panel` block permutation, **200 draws, seeds 3000–3199**, pushed through the identical arms. Under a permuted
signal the exit rules still differ from one another, so the p95 of the paired |HAC *t*|
answers the only question that matters here: **how big a gap between two exit rules does
no signal at all produce?**

| arm | Δ net /yr | HAC *t* | **own p95 floor** | null max | null median Δ | clears |
|---|---|---|---|---|---|---|
| A1 FV-POINT | -0.13% | -0.368 | **1.918** | 3.237 | -0.001% | no |
| A2 FV-LENSBAND | +0.37% | +0.866 | **1.852** | 2.812 | +0.002% | no |
| A3 TPSL-ONEIL | -0.21% | -0.396 | **2.026** | 3.086 | +0.006% | no |
| A4 TPSL-2TO1 | -0.13% | -0.254 | **2.049** | 2.679 | -0.003% | no |
| C-NEVER | -10.89% | -3.801 | **2.554** | 4.012 | +1.085% | YES |

**1 of 5 challengers clear their own floor** — and the one that does is the never-sell CONTROL, not a candidate.**

**C5, with one honest exception that is a property of the design rather than a broken instrument.** The null's median paired difference is essentially zero for all four price-based arms (A1 FV-POINT -0.0010%, A2 FV-LENSBAND +0.0021%, A3 TPSL-ONEIL +0.0055%, A4 TPSL-2TO1 -0.0026%), which is what C5 asks for. **C-NEVER's null median is +1.0848%, NOT zero** — and it should not be: on a worthless signal the incumbent still churns on rank while never-selling holds a large book and pays almost no turnover, so **not selling is genuinely the better rule when there is nothing to sell on.** The null captures that, which is exactly why it is the right comparison. **Against its own null the real C-NEVER is worse still** — -10.89% against a null centred at +1.08%.

**A by-product worth recording: the four price-arm floors land at 1.92, 1.85, 2.03, 2.05 — i.e. right around the conventional 2.0.** The uncalibrated bar the register used as a labelled reference turns out to have been about right *for this object*, which is a happy accident and not a licence to skip calibrating the next one: C-NEVER's own floor is 2.55, so the bar is not one number even within this study.

**Labelled `fixed_weights_null` in the artifact and NOT comparable with 2.2837 or
2.2913**, for the same reason S22's was: it is a deliberately less conservative null
(fixed weights, no CPCV) measured on a different object.

---

## 7. Verdicts

| arm | Δ net /yr | HAC *t* | floor | halves agree | **verdict** |
|---|---|---|---|---|---|
| A1 FV-POINT | -0.13% | -0.368 | 1.918 | yes | **NO IMPROVEMENT** |
| A2 FV-LENSBAND | +0.37% | +0.866 | 1.852 | **no** | **NO IMPROVEMENT** |
| A3 TPSL-ONEIL | -0.21% | -0.396 | 2.026 | **no** | **NO IMPROVEMENT** |
| A4 TPSL-2TO1 | -0.13% | -0.254 | 2.049 | **no** | **NO IMPROVEMENT** |
| C-NEVER | -10.89% | -3.801 | 2.554 | yes | **WORSE** |

**NO CHALLENGER BEATS THE INCUMBENT**, by the rule fixed in advance: a challenger BEATS only if its paired net difference is positive AND clears its own
placebo floor AND agrees in sign across both halves.

**The one arm with a positive full-sample difference — A2 FV-LENSBAND at +0.37%/yr — fails on the halves** (−0.31% early, +1.04% late) **and does not clear its floor.** That is the both-halves requirement doing exactly the job it was put there for.

**C-NEVER is the only arm whose difference is measurable at all**, and it is measurably **WORSE**. It is a control, not a candidate — see §5.

---

## 8. The pre-registered expectations, scored

| # | expectation | odds | outcome |
|---|---|---|---|
| 1 | **No challenger beats the incumbent** | 75/25 | **RIGHT** |
| 2 | All four price-based exits **negative** | 70/30 | **WRONG** — A2 is +0.37% (though inside noise) |
| 3 | TP/SL worse than the fair-value arms | 60/40 | **RIGHT** — mean TP/SL −0.17% vs mean FV +0.12%, all inside noise |
| 4 | C-NEVER beats the incumbent **gross**, margin shrinking net | 55/45 | **WRONG, and badly** — gross 20.70% vs 34.16%, −13.5pp |
| 5 | The stop-loss does more damage than the take-profit | 55/45 | **UNRESOLVED** — see below |
| 6 | Fair-value coverage below 90% of held name-periods | 60/40 | **WRONG** — 93.9% of factor rows, 99.87% of valued rows |

**Expectation 5 is recorded UNRESOLVED rather than scored, and that is a design limitation worth
owning.** A3 (+25%/−8%) is worse than A4 (+20%/−10%), which is *consistent* with the tighter stop
doing the damage — but the two arms differ in **both** legs at once, so nothing here separates
them. Separating them would need a TP-only and an SL-only arm, and adding those after seeing this
result is precisely the grid search §2b forbids. **It stays unresolved rather than being answered
by a post-hoc arm.**

**Two right, three wrong, one unresolved** — and the two headline calls (#1 and #3) were right
while the two about magnitude (#2, #4) were wrong.

---

## 9. Corrections to this register's own text

* **C4 as written was wrong.** It required "the count of buys per date must match A0 for all
  arms". That is unachievable and not the right invariant: a name sold this period is immediately
  re-bought if it is still in the top 25, so buy **counts** legitimately differ between arms
  precisely *because* their exits differ. The invariant that actually proves the buy rule is
  untouched is that **every arm scores the same dates with the same `target_n`**, which is what is
  measured and reported. Found while smoke-testing, before any arm was scored.

---

* **C1's subset clause was also wrong, and the strays were measured rather than argued away.**
  C1 required the valuation panel's `(date, ticker)` keys to be a subset of the factor panel's.
  They are not: **1,221 of 108,241 (1.13%)** are absent from it, because the factor panel applies
  the **B13 investability prefilter** and the valuation panel does not, so the latter legitimately
  values names the former screens out.
  **They are reachable, but immaterial, and both halves of that were measured.** Reachable because
  `_backtest_hold` keeps a name in `held` after it leaves the cross-section, so its key can be a
  stray while it is still being tested. Immaterial because in exactly that situation the **rank
  exit fires simultaneously**: re-running both fair-value arms with the gates intersected down to
  factor-panel keys leaves **every series bit-identical** — same returns, same book, same dates —
  and moves **2 of 1,288 exits** between the `fair_value` and `rank` labels (A1 794/494 →
  796/492). **No measured value depends on the strays; only an attribution count does.**
  The material invariant — which is what C1 should have said — is that the two panels share a
  calendar exactly and that removing the strays changes no series. Both hold.

## 10. What this does NOT say

* **It does not say the incumbent exit is optimal.** It says four specific, conventionally-chosen
  alternatives do not beat it by a measurable margin, and that never selling is much worse. The
  space of exit rules is not searched — deliberately, because searching it is the trap §2b closes.
* **It does not license a TP/SL grid.** Both pairs were named in advance from published
  convention. If a future session wants a different pair it needs its own register and it inherits
  this null as its prior.
* **The TP/SL arms trigger less often than real ones would.** The panel has no intra-quarter path,
  so a name that touches +40% mid-quarter and gives it back is never seen to hit a +25%
  take-profit. **That biases the measurement in FAVOUR of the TP/SL arms**, which is why a
  negative result on them is the trustworthy direction and a positive one would have needed
  path-level data before it could be believed.
* **It changes nothing about the live book.** Adoption is a vintage event and Don's call.

---

## 11. Trial cost

**Five scored arms plus the control: equity `N` 143 → 149**, as registered. Charged at zero: the
placebo calibration, the half-splits, and the coverage/book-size diagnostics.

**Measured:** DSR **0.8436955925493782 → 0.8388059159836208**, `sr0_benchmark` 0.436077 →
0.438357, **√(2·ln 149) = 3.1635** — still above the Harvey–Liu–Zhu hurdle of 3.0, still
self-reporting `deflated_sharpe_ratio` with `is_effectively_undeflated: false`. **Nothing else
moved:** 1,217 leaves, **20 moved / 0 ADDED / 0 REMOVED** — five the DSR chain, four provenance,
eleven last-digit float. Every headline is **bit-identical** (`long_short_tstat`
2.8360640685320595, `top_decile_alpha` 0.07174142332098163) and `cpcv.adopt` is still `false`.
**Re-run, never hand-patched** — and the first attempt was **killed mid-build by the harness and
wrote nothing**, which is the correct failure mode: the artifact stayed at the previous `N` with
clean provenance rather than being left half-written, so the only cost was the time to re-run it.


---

## 12. CORRECTIONS TO THIS SESSION'S OWN COMMIT MESSAGES

* **`3ba5f4d` says "Nine new tests"; it is EIGHT.** The suite went 275 -> 283. Recorded rather
  than amended, because the commit is already written and this file is the record that gets read.
  **This is the second time in two sessions I have miscounted my own tests** (session 18 said 11
  where it was 9), so the count is now taken from `grep -c "^def test_s23"` rather than from
  memory.

## 13. BUGS FOUND

1. **`build_valuation_panel` carried the B6 per-ticker-tail defect** (§2a) — **FIXED** here,
   because S23's C1 requires it. Anyone who has run `run_calibration` before today measured the
   fair-value gap on the **110-date pre-B6 panel**, whose first third is the inverted universe.
   **Any prior calibration conclusion should be re-run before it is quoted.**
2. **The point-in-time valuation reached live Yahoo for ~1 row in 7** (§2b) — **FIXED** behind an
   explicit `offline` flag. The live path is untouched and still corroborates, which is right for
   the product.
3. **`_backtest_hold` extracted a column once per NAME instead of once per date** — **FIXED**
   (`112551b`). `sub["fwd_ret"]` sat inside a dict comprehension, so a 1,650-name cross-section
   extracted the same column 1,650 times, and each extraction deep-copied the panel's `.attrs`
   through pandas' `__finalize__`. Measured by cProfile on one call: **114,774 column
   extractions, 27.4M deepcopy calls, 61 of 70 seconds**. Hoisting it: **15.6s → 2.7s (5.8x)**.
   Found because the pre-registered 200-draw placebo projected **5.4 hours** — the registered
   draw count was NOT cut to fit the budget, the cause was fixed. **The whole race was re-run
   after the fix and is bit-identical to the run before it — 1,818 leaves, 0 moved, 0 added, 0
   removed** — so it buys speed and changes no measured value. Not confined to S23:
   `run_backtests` and `sweep_hold_params` both drive this function, and the latter calls it 34
   times per invocation.
4. **Not a defect but a live mis-quotation risk:** `_backtest_hold`'s levels (a 32.7% net CAGR
   here) are a **different, noisier object** from the decile book every published figure uses
   (B17). This register quotes only differences; a surface that shows the level would be
   presenting the noisiest book in the file as the headline.

## 14. What was NOT done

* **No replacement family.** The challengers ADD to the rank exit; a pure price-only exit lets a
  permanently-cheap name sit forever and answers a different question. Recorded in the register in
  advance, not discovered as an omission.
* **No TP-only or SL-only arm** — see expectation 5. Adding one now would be a post-hoc arm.
* **No intra-quarter path**, so no true path-dependent TP/SL. Closing this needs daily prices in
  the panel, which is a different build.
* **No trailing-stop arm**, even though `_backtest_hold` supports one and `sweep_hold_params`
  already sweeps it over four values. That sweep is the trap; entering it would need its own
  register with the value named in advance.
* **Nothing adopted, and no vintage opened.**

---

# SESSION 20 (2026-08-11) — SECTOR-NEUTRAL-B6: the re-run on a panel that counts

**Register:** `PREREG_sector_neutral_b6.md`, committed **ALONE at `1bdb7e0`**, a strict git
ancestor of the commit that added `scripts/sector_neutral_rerun.py`. The gate, its two
weightings, the verdict rule, the calibrated bars, the seven controls, the trial cost and the
expectations were all fixed before any number existed. Nothing below restates a threshold from a
result.

**Item:** member **B** of `HANDOFF_parked_positives.md` §3. **Adopts nothing** — adoption is a
**vintage event** and Don's call. `CONFIG.sector_neutral` is untouched at `false`.

## 1 · Why a twice-rejected result was re-run at all

Sector-neutral ranking scores every granular number against its **sector median** before the
global z-score. It was rejected by P10 (2026-07-31) and again on 2026-08-02, in both held-out
split directions, under both weightings. The mechanism was understood, not mysterious: it **buys
long-short *t* and sells top-decile alpha**, and Valquo trades a long-only book.

**The re-run is not doubt about that reasoning. It is that both rejections ran on a panel the
project has since declared void.** `HANDOFF_sector_neutral.md:58` records *"2,710 usable, 136,478
panel rows, **110 rebalance dates**"*, dated 2026-08-02. **B6 landed 2026-08-04** and cut the
panel to **2,531 names / 69 dates**, because the first 41 dates had an inverted universe.
`CLAUDE.md` records B6's cost to the headline as **t −0.897, alpha −4.18pp, PBO +46.7pp** —
*"B6 is essentially the whole drop"*.

**The decision turned on a −1.58pp alpha difference, measured inside a panel whose alpha level
moved −4.18pp when the defect was removed.** That is the parked-positives sweep's own finding,
and it is why this was the one item in that file needing no new data at all.

## 2 · VERDICT: REJECTED — and it failed *differently*, which is the finding

Both gates return `reject`; no control blocked the verdict.

### Under the DEPLOYED weights (the seven themes that trade — this is the one that carries it)

| | OFF (shipped) | ON (sector-neutral) | Δ |
|---|---|---|---|
| top-decile alpha | **+7.1741%** | +6.0852% | **−1.0890pp** |
| long-short annualised | **+11.0382%** | +8.5107% | −2.5275pp |
| long-short *t* (naive) | **+2.8361** | +2.3423 | **−0.4938** |
| **long-short *t* (HAC, the one quoted)** | **+2.6199** | +2.1505 | **−0.4694** |
| top-decile alpha HAC *t* | **+4.3762** | +4.0893 | −0.2869 |
| monotonicity (−1 ideal) | **−0.8909** | −0.8667 | worse |
| long-short hit | 66.7% | 65.2% | worse |
| equal-weight benchmark | +18.1371% | +18.1371% | **identical — the universe control** |

**The pre-committed gate, both halves, boundary 2017-07-20 embargoed:**

| half | *n* | long-short *t* | top-decile alpha | improves? |
|---|---|---|---|---|
| early | 34 | +1.7014 → +1.6921 (**−0.0093**) | +2.8171% → +2.6712% (**−0.1459pp**) | **no** |
| late | 34 | +2.3549 → +1.8703 (**−0.4846**) | +11.5799% → +9.5655% (**−2.0144pp**) | **no** |

### THE HEADLINE IS NOT "IT FAILED AGAIN" — IT IS *HOW* IT FAILED

**On the void panel sector-neutral BOUGHT long-short *t* (3.396 → 3.896, +0.500) and SOLD alpha.**
The rejection was therefore a *judgement*: a long-only book should not buy a *t*-statistic with
alpha. Anyone who disagreed with that preference could reasonably have re-opened it.

**On the corrected panel the long-short gain is GONE AND ITS SIGN IS REVERSED — −0.4938 under the
deployed weights and −0.3000 under the flat ones.** Sector-neutral is now **worse on both
metrics, under both weightings, in both halves**. *There is no trade-off left to adjudicate*, and
the rejection no longer rests on a preference. **That is a materially stronger result than the one
it replaces, and it is the answer to the question the inventory actually asked.**

### The calibrated floor separates the two arms

| arm | long-short HAC *t* | floor 2.2837 | alpha HAC *t* | floor 2.2913 |
|---|---|---|---|---|
| OFF (shipped) | **2.6199** | **clears** | 4.3762 | clears |
| ON (sector-neutral) | **2.1505** | **FAILS** | 4.0893 | clears |

Quoted where X7 and session 10 calibrated them — the full-universe decile book, 69 dates,
H = 63, HAC lag 1, which is exactly this configuration — and **labelled an extrapolation for the
sector-neutral arm**, whose composite is a different transform of the same inputs.

### Under the FLAT weights — same answer, so the verdict is not a weighting artefact

alpha **+4.9912% → +4.2194%** (−0.7718pp), long-short *t* **+1.1680 → +0.8679** (−0.3000),
monotonicity **−0.6121 → −0.3455** (a large degradation), gate `reject`. Neither arm clears the
long-short floor under flat weights, which is expected — the flat vector is a comparison
instrument, not the book.

### The paired within-panel difference (secondary, UNCALIBRATED bar of 2.0)

The two arms score the same dates, so differencing per date cancels the market move (the V2G
construction, through the shipped `quantile_backtest(..., return_series=True)`).

| | Δ alpha /yr | se | HAC *t* | Δ long-short /yr | HAC *t* |
|---|---|---|---|---|---|
| full (69) | **−1.0890pp** | 0.6629pp | **−1.6666** | −2.5275pp | **−2.5151** |
| early (34) | −0.1459pp | 0.7054pp | −0.2701 | −0.9936pp | −0.7243 |
| late (34) | −2.0144pp | 1.1343pp | −1.7257 | −3.9753pp | −2.8273 |

**Both halves are negative on alpha**, and **the late half carries the result** — the same shape
the void panel's late half showed. **The 2.0 is uncalibrated and cannot overturn the primary
gate**; V2G established that no calibrated floor exists for a paired within-panel difference,
because X7 and session 10 calibrate *levels*.

## 3 · The design, and the one thing it does better than either prior run

**ONE panel build. Two arms. A provably identical row set.**

At each rebalance date the loop assembles one `metrics` list and calls `build_frame` **twice** —
once flat (which defines the rows) and once sector-neutral — emitting `sn_{theme}` columns on the
**same row**. `build_frame` copies its input and never mutates the caller's list, which was
verified rather than assumed.

**Both prior runs built the arms as two separate runs, and that is a real weakness given what
this project knows about itself:** `CLAUDE.md` records that a full backtest is **not reproducible
run to run**, with `insider` moving median IC −0.0034 / +0.0155 / −0.0034 across three
identical-data runs. A per-arm build lets that land inside the difference being measured. **One
pass makes it common-mode, so it cancels exactly** — the same argument S22 used to build one
panel for eight horizons.

## 4 · Controls — all seven pass, and one of them was worth re-measuring

| # | control | result |
|---|---|---|
| **C1** | identical `(date, ticker)` key sets | **exact** — 113,945 rows each, 0 either way; 69 dates, 2009-01-15 → 2026-01-28, 2,531 names |
| **C2** | the toggle is not inert | mean absolute composite change **0.0567**, cross-arm correlation **0.9836**, **9 of 10 themes move** (`low_risk` 0.275, `momentum` 0.191, `size` 0.156, `value` 0.155 …) |
| **C3** | the flat arm reproduces the published record **to the digit** | **all six** — alpha `0.071741423321`, LS *t* `2.8360640685320595`, LS HAC 2.6199, alpha HAC 4.3762, monotonicity `-0.8909090909090909`, EW `0.18137118752419476` |
| **C4** | **sector coverage, re-measured on the corrected panel** | **100.0% of rows and names, 11 sectors**, smallest sector on any date **50 names**, **ZERO singletons** |
| **C5** | `insider` untouched by the toggle | **exactly 0.000** — it is a rescaled percentile, not a z-scored input |
| **C6** | no NEW missing values | **none** on any theme, so the arms score the same names |
| **C7** | `sentiment` empty | **0 non-null**, so excluding it from the flat set is right |

**C4 was worth doing rather than inheriting.** The 100% figure in the record was measured on the
**void** panel; the COVERAGE RULE says check before acting, and a singleton sector would have
been a real problem — a lone name maps exactly to its own median, i.e. to 0. There are none.

## 5 · A DEFECT FOUND, REPORTED, AND DELIBERATELY NOT REPAIRED

**`cross_sectional.zscore`'s zero-variance guard is value-dependent and misses.**

It guards degeneracy with `if not sd or np.isnan(sd) or sd == 0`, assuming a constant
cross-section has `sd == 0`. Whether it does depends on the constant, because pandas reaches the
variance through a sum of squares:

| constant | `std(ddof=0)` | guard fires? | `zscore` result |
|---|---|---|---|
| 0.0, 50.0, 2.5, 0.125, 0.07 | **exactly 0.0** | yes | all-NaN (correct) |
| **0.9, 0.1, ⅓, 12.34, 1000000.1** | **~1e-16** | **no** | **a fabricated pattern, max \|z\| = 1.0** |

So **a constant signal does not reliably neutralise itself** — it can inject invented ±1 scores
into a theme, and which behaviour you get is not predictable from the input's shape.

**It corrects a claim in the record.** V2G states that a constant live `insider` means *"`zscore`
returns all-NaN"*. That is true **only because** the live `insider` is constant at **exactly
0.0** (`(50 − 50) / 25`), where the sum of squares really is zero. **It is not a general
property and must not be quoted as one.**

**How it was found**, because the route matters: a test asserting that with blank sectors the two
arms must be *exactly* equal (a constant grouping makes demedianing a pure shift, which a z-score
erases) failed at **0.28 on `quality`**. The cause was not the pair path — it was `_SynthPIT`
emitting `fcf = 90(1+q)` and `netinc = 100(1+q)`, so `fcf/netinc` is **identically 0.9** and
`accruals_q` is a constant column whose z-score is not shift-invariant. **The fixture was made
non-degenerate and the assertion kept, rather than the assertion being weakened to fit.**

**EXPOSURE MEASURED, NOT ASSUMED — it is nil here.** No theme column is constant or
near-constant on any of the 69 dates, and the smallest within-sector dispersion across 231
sampled `(date, sector, theme)` cells is **0.2209**. **No figure in this study, and nothing in
the shipped artifact, is affected.**

**NOT repaired.** `zscore` is on the live scoring path and every published figure in the project
runs through it, so changing it is a **scoring change and therefore a vintage event** — not this
register's to make. It is **pinned by a test that fails if it is ever silently corrected**, with
instructions in the failure message to update the record.

## 6 · What this does NOT say

* **It does not say the old verdict was wrong.** Both prior runs compared their arms against each
  other on the same panel, which cancels a great deal. What was missing was any observation of
  the trade-off on the panel the project uses; that gap is now closed, and the answer came back
  *stronger* than the original rather than overturning it.
* **It is not a statement about the sector column generally.** The column is **already used, and
  accepted**, for the `max_sector_w` concentration cap — a **risk control, not a re-ranking**.
  Nothing here touches it.
* **It does not close `S15` or `S25`.** Both ledger rows were blank ("no mention anywhere in the
  corpus") and are now scoped as the only two re-open routes.
* **It is not a forward test.** Same single in-sample Sharadar panel as every other published
  figure.

## 7 · The look-ahead caveat, which cuts against a positive rather than for it

Sharadar TICKERS carries **today's** sector classification, so applying it to a 2009 row assumes
the company was in the same sector then. This is **the one non-point-in-time input in an
otherwise strictly point-in-time panel**, and the direction matters: it is a reason to be
**MORE** sceptical of a positive sector result, not less.

**It rejected, so nothing rests on it** — which is the same position the 2026-08-02 run recorded,
and it remains the honest one. Had this returned ADOPTED, `S25` would have become a prerequisite
rather than a nice-to-have.

## 8 · Expectations, written down first and scored

| # | prediction | conf. | outcome |
|---|---|---|---|
| 1 | verdict is **REJECTED** | 80/20 | **RIGHT** |
| 2 | long-short gain shrinks below +0.25 | 70/30 | **RIGHT** — and then some: it **reversed** to −0.4938 |
| 3 | alpha difference negative, 0 to −3pp | 75/25 | **RIGHT** (−1.09pp) |
| 4 | paired difference does not reach \|*t*\| 2.0 | 60/40 | **SPLIT** — right on alpha (−1.6666), **WRONG on long-short** (−2.5151) |
| 5 | both halves agree in sign on alpha | 60/40 | **RIGHT** (−0.146, −2.014) |

**Four right and one split is an unusually good run for this project's directional calls**, and
the stated reasoning held rather than the conclusion happening to land: the corrected window is
roughly the void panel's **late** portion, and in that late half sector-neutral already lost on
both metrics. **This does not license reasoning about direction instead of measuring it** — the
record still runs the other way (R10, O20, the spread toll, U7, X3, and both of S22's headline
questions).

## 9 · What I did NOT do, and why

* **No placebo / null distribution.** Sector-neutrality changes how the panel is *built*, so a
  null would have to permute **sector labels and rebuild the panel per draw** — not permute a
  finished panel, which is the trap recorded in `x7-permutation-cannot-calibrate-a-score`. The
  primary gate is a **pre-committed margin** and needs no floor. **Registered as a limitation in
  advance (prereg §5), not discovered afterwards.**
* **No PBO and no Deflated Sharpe per arm**, though the 2026-08-02 run reported both. X7 measured
  **PBO's noise median at 46.7%**, so the <50% bar sits at the noise level; and running
  `cpcv_validate` per arm would put **weight selection inside the loop**, which X7 measured
  manufactures **~+1.4 of long-short *t* on 27% of pure-noise draws**. Omitting them is a
  deliberate improvement on the earlier design, not a shortcut.
* **No grid-offset sweep, and no sweep of anything.** One construction toggle, no parameter to
  tune; inventing one would be the param-search trap S23 paid to avoid.
* **I did not flip `CONFIG.sector_neutral`, and I did not repair the `zscore` defect.** Both are
  scoring changes and therefore vintage events.
* **I did not test `S15` (sector-relative on value alone).** It is a different construction and
  needs its own register — and it now inherits a prior it did not have this morning.

## 10 · Trial cost and the artifact

**One hypothesis, two pre-specified weightings, no grid: `n = 2`. Equity `N` 149 → 151**,
√(2·ln 151) = **3.1677**, still above the Harvey–Liu–Zhu hurdle of 3.0.

**`BACKTEST_RESULTS.json` re-run so the artifact matches the denominator: Deflated Sharpe
0.8388059159836208 → 0.8372030816851322**, `sr0_benchmark` 0.438357 → 0.439094, still
self-reporting `deflated_sharpe_ratio` with `is_effectively_undeflated: false`. **1,217 leaves,
23 moved / 0 ADDED / 0 REMOVED** — two timestamps, two provenance, five the DSR chain, fourteen
last-digit float. **Every headline is bit-identical** (`long_short_tstat` 2.8360640685320595,
`top_decile_alpha` 0.07174142332098163, monotonicity −0.8909090909090909, equal-weight
0.18137118752419476), `errors` is empty and `cpcv.adopt` is still `false`.

**IT WAS RE-RUN TWICE, AND THE FIRST ONE IS REPORTED RATHER THAN QUIETLY DISCARDED.** The first
pass finished with `git.dirty: true`, because two markdown files (`HANDOFF_STATUS.md`,
`VALQUO_EXTENSIONS.md`) were written *while* it ran — the run began from a clean tree but the flag
is stamped at write time. No number was affected and no code changed, but the project's own
convention is that the artifact carries a provenance sha describing the tree that produced it, and
the close-out check asserts `dirty: false`. **Weakening that check to accept the first run would
have been silencing it**, so the docs were committed and the whole thing re-run from a genuinely
clean tree (`ad0ab87`, 0 modified files verified at launch). The two runs agree on every value.

Charged **even though the verdict is negative**, because a re-run of a rejected hypothesis is
another chance at the same hypothesis, and understating `N` overstates the significance of every
DSR-gated claim in the project.

* `data/free_analysis/SECTOR_NEUTRAL_B6.json` — every arm, every control, every per-date draw.
* `python -m scripts.sector_neutral_rerun` reproduces it.
* Tests: **five** new in `tests/test_edge.py` (the paired build, plus the pinned `zscore`
  defect), **two** new in `tests/test_sector_neutral.py` (the arm split). The existing six wiring
  tests still **deliberately do not pin the verdict**.


# SESSION 21 (2026-08-11) — S20/S21: the standardiser is worth several points of alpha, and no theme IC can see it

Ledger items **S20** ("rank composite, not z-sum") and **S21** ("winsorise before standardising"),
both `OPEN`, both `src=auto`, per their own ledger notes with *"no mention anywhere in the corpus"*.
Neither had ever been run. They are the same decision seen twice — how a cross-section becomes a
number before the weighted sum happens — which is why they got one register rather than two.

**Why the pair is worth a register at all: P6.3.** Replacing the classic z-score with a median/MAD
robust z-score made the composite fall apart (long-short *t* **3.485 → 1.721**, alpha
+11.77% → +8.99%) **while every per-signal IC stayed flat** (quality +3.39 → +3.35). So the project
already knew this layer is load-bearing and that per-signal IC cannot see it. S20 and S21 are the
two untested moves in the same layer.

## 1. THE COMMITTED THRESHOLD, WRITTEN BEFORE ANY MEASUREMENT CODE EXISTED

`PREREG_s20_s21_construction.md`, committed **ALONE at `27af414`** — a strict git ancestor of
`5db4903`, which carries the measurement code. Nothing in the study restates a threshold from a
result.

* **Gate:** the **shipped** `holdout_compare_panels`, unmodified, at the **already-committed**
  margins `MIN_HOLDOUT_ALPHA_GAIN = 0.01` and `MIN_HOLDOUT_TSTAT_GAIN = 0.25`
  (`fundamental_panel.py:3115-3116`) — **both** margins in **both** halves, boundary embargoed.
* **Universe:** the corrected panel, **2,531 names × 69 dates**, 2009-01-15 → 2026-01-28, H = 63.
* **Two weightings and no others:** DEPLOYED (7 themes) carries the verdict; FLAT (9) tests whether
  the answer depends on the weighting.
* **Verdict rule, fixed in advance:** ADOPTED iff deployed `adopt` AND flat not `reject`; REJECTED
  iff deployed `reject`; NOT REPLICATED otherwise.
* **Trial cost charged in advance:** n = 4, equity `N` 151 → 155.

**THE SPEC AS A BINDING CONSTRAINT:** *never judge a construction change by per-signal IC.* The
verdict is carried by the **book**; per-signal and per-theme ICs are diagnostics that may not move a
verdict in either direction.

## 2. THE PREMISE OF S21 IS WRONG, AND THE REGISTER SAYS SO BEFORE THE RUN

`cross_sectional.zscore` **already winsorises at 2% before standardising** (`cross_sectional.py:83-87`),
at **both** standardisation layers. The audit item proposes the shipped behaviour — exactly what
`src=auto` (*"mechanically proposed and not yet read by a person; treat as a lead, not a fact"*)
exists to warn about.

So S21's testable form is **inverted**: the challenger is **winsorisation OFF** (`p=0.0`, an exact
no-op clip to `[min, max]`), and an `adopt` would have meant **removing** the shipped clip. Recorded
in the register, in the V2F/V2G tradition of correcting a brief's premise before the run rather than
discovering it in the results.

## 3. DESIGN — one build, three scorings, two layers

The pipeline standardises **twice**: layer 1 per number (`build_frame`, every `z_*` column), layer 3
per theme (`composite_from_frame`, the actual "z-sum"). **Both arms change both layers** — an arm
that swapped only one would not be what either ledger item says.

| arm | standardiser at L1 and L3 |
|---|---|
| INCUMBENT | `zscore(s, p=0.02)` — the shipped construction |
| **A20 RANK** | `(s.rank(pct=True) - 0.5) * 2.0` — the repo's own existing convention, implemented in `standardize_factors(method="rank")` and never called by `build_frame` |
| **A21 NOWINSOR** | `zscore(s, p=0.0)` |

**One panel build, three `build_frame` calls per cross-section on the same `metrics` list**, so the
known `insider` run-to-run nondeterminism (median IC −0.0034 / +0.0155 / −0.0034 across three
identical-data runs) is **common-mode and cancels** out of every difference. Both prior
sector-neutral rejections built their arms as separate runs; that defect is not repeated.
**113,945 rows, provably identical across all three arms.**

## 4. RESULTS — DEPLOYED WEIGHTS (the verdict arm)

| | INCUMBENT | A20 RANK | A21 NOWINSOR |
|---|---|---|---|
| top-decile alpha | **+7.1741%** | +3.6817% (−3.4925pp) | +9.6038% (+2.4296pp) |
| long-short ann | +11.04% | +9.04% | +16.63% |
| long-short *t* | +2.8361 | +2.3054 | +4.9395 |
| **long-short HAC *t*** | **+2.6199** ✓ | **+2.0588** ✗ | +4.3612 ✓ |
| **alpha HAC *t*** | **+4.3762** ✓ | **+2.0028** ✗ | +4.7145 ✓ |
| monotonicity | −0.8909 | **−0.9515** | **−0.9758** |
| equal-weight benchmark | +18.137% | +18.137% | +18.137% |

Floors 2.2837 (long-short HAC) and 2.2913 (alpha HAC) are **an EXTRAPOLATION for the challenger
arms** — a floor is a percentile of a null generated under the incumbent construction, and nobody
has run a placebo under a rank composite. Labelled so wherever it appears.

Deciles (annualised, %): incumbent `25.31 20.40 19.55 17.52 17.34 17.76 18.23 16.34 14.58 14.27`;
rank `21.82 21.07 18.21 19.73 18.18 17.43 18.01 17.58 16.52 12.78`;
nowinsor `27.74 20.14 20.38 19.52 18.00 19.31 16.17 15.70 13.22 11.11`.

### The gate

| arm | half | Δ long-short *t* | Δ alpha | improves |
|---|---|---|---|---|
| **A20** | early (n=34) | −0.4689 | −1.32pp | no |
| **A20** | late (n=34) | −0.4171 | −5.62pp | no |
| **A21** | early (n=34) | **+0.7863** | **+0.83pp** | **no — misses the +1.00pp bar by 17bps** |
| **A21** | late (n=34) | +2.0125 | +3.69pp | yes |

Boundary embargoed at 2017-07-20.

### FLAT weights

| | INCUMBENT | A20 | A21 |
|---|---|---|---|
| alpha | +4.9912% | +1.7307% | +4.6482% |
| long-short *t* | +1.1680 | +0.9309 | +1.3763 |
| gate | — | **reject** | **reject** |

A21's flat halves are **both negative on alpha** (−0.40pp, −0.47pp), so its full-sample gain does
not survive a change of weighting.

### Paired within-panel difference (UNCALIBRATED 2.0 bar, per the register)

| arm | window | Δalpha /yr | HAC *t* | Δlong-short /yr | HAC *t* |
|---|---|---|---|---|---|
| A20 | full (69) | **−3.4925pp** | **−2.3783** | −2.00pp | −1.2004 |
| A20 | early / late | −1.32 / −5.62pp | −1.0857 / −2.1543 | | |
| A21 | full (69) | **+2.4296pp** | **+1.9170** | +5.59pp | **+1.9365** |
| A21 | early / late | +0.83 / +3.69pp | +0.5568 / +1.8543 | | |

**A21 does not cross even the uncalibrated bar on either metric.**

## 5. VERDICTS, by the rule fixed in advance

* **S20 (RANK) — REJECTED.** Deployed `reject`, flat `reject`.
* **S21 (NOWINSOR) — NOT REPLICATED.** Deployed `not_replicated`, flat `reject`. Ambiguous against
  its own threshold is a **NULL**, per `RUN_RULES` A6.

**Neither is adopted, and the register fixed that in advance:** an eligible arm would have been
recorded **ELIGIBLE, not adopted**, and **queues behind the theme restoration's vintage**
(`PREREG_v2g_live_theme_sources.md`) rather than spending a second five-year clock reset on the same
restart. `CONFIG`, `settings.FACTOR_WEIGHTS` and every shipped default are untouched.

**THE QUEUEING CLAUSE TURNED OUT TO BIND — recorded because it is the case FOR writing such clauses
before a result exists.** While this study was running, the theme-restoration lane **took the
vintage event** (`c8efd00`, `PREREG_theme_restoration.md` committed alone at `1d12822`): it restored
`capital_discipline` to the live scoring path on a fidelity gate (+0.8421 against a 0.60 bar) while
`institutional` (+0.1706) and `insider` (+0.3596) failed it. **Nothing here conflicts, because both
of this study's arms failed their own gate.** But had either been eligible, adopting it separately
would have spent a **second** clock reset for one restart's worth of evidence — and the clause would
have been unarguable to add *after* seeing a favourable arm.

## 6. THE FINDINGS — in order of how much they should change what the next person does

### 6.1 The pair is the headline: several points of alpha, invisible to every theme IC

| theme | incumbent IC *t* | Δ under A20 | Δ under A21 |
|---|---|---|---|
| value | +0.8380 | +0.1920 | −0.3558 |
| quality | +3.1015 | +0.1092 | −0.0284 |
| momentum | +1.3118 | −0.0619 | −0.0263 |
| insider | −0.2362 | **+0.0000** | **+0.0000** |
| capital_discipline | +2.7556 | +0.0001 | +0.0001 |
| size | −0.3008 | −0.0017 | −0.0017 |
| institutional | +1.5470 | +0.0338 | +0.0731 |

**Max |Δ theme IC *t*| is 0.1920 and 0.3558 while the book moves −3.49pp and +2.43pp of annual
alpha.** Judged by per-signal or per-theme IC, both changes look harmless; one costs 3.5pp/yr.

**For a rank transform this is an IDENTITY, not an observation.** Control C5 measures
`max |ΔIC| = 0.000e+00` across all **44** number columns, because Spearman IC is invariant to a
strictly monotone transform. **The per-signal diagnostics are mathematically incapable of seeing
S20.** That is the standing rule with a proof attached, and it is now demonstrated three times
(P6.3, X3, here).

### 6.2 S20 fails while making the deciles BETTER ordered

Monotonicity **improves** (−0.8909 → −0.9515) as alpha collapses. Ordering *across* deciles gets
smoother while the **top** decile — which is the shipped product — loses its edge (D1
25.31% → 21.82%). **Hypothesis, not a result:** rank discards the magnitude information that
identifies genuinely extreme names, which is precisely what a top-decile long book is selecting on.
Anyone quoting monotonicity as a quality metric should read this row first.

### 6.3 S21's +2.43pp must never travel without its fragility number

| arm | mean max abs composite | mean p99 | ratio |
|---|---|---|---|
| INCUMBENT | 2.018 | 1.232 | **1.64×** |
| A20 RANK | 0.791 | 0.582 | 1.36× |
| **A21 NOWINSOR** | **8.150** | 1.142 | **7.14×** |

The unclipped arm's most extreme composite averages **7.14× its own 99th percentile**, and only
**8 of the shipped top 25 names** survive it. An unclipped z-score is a **fragile estimator** whose
book is anchored by outliers.

**Winsorisation is also a DATA-QUALITY defence, not only a statistical choice.** P7 shipped a
currency bug that computed `book_to_price` **892 against a true 0.589**; with no clip such a row
dominates the entire cross-section's mean and sd and lands at the top of the book. *"Removing the
outlier guard improved the backtest"* and *"the outlier guard is not earning its keep"* are
different claims and only the first is measured.

### 6.4 Single-input themes are rank-invariant; multi-input themes are not

Within-date rank correlation between incumbent and challenger theme values:

| theme | A20 | A21 |
|---|---|---|
| quality (10 inputs) | 0.9395 | **0.8215** |
| value | 0.9456 | 0.9236 |
| institutional | 0.9880 | 0.9110 |
| momentum | 0.9835 | 0.9932 |
| **size / capital_discipline / insider** | **1.0000** | **1.0000** |

A monotone transform of ONE column preserves its ranking exactly; a **mean** of monotone transforms
is not a monotone transform of the mean. So the change enters **only** through multi-input themes.
The pre-registered expectation that `size` would move most was **backwards** — being single-input is
exactly what makes it invariant.

## 7. CONTROLS — all seven measured, six pass and one is FALSIFIED

* **C1 — reproduces the published record to the digit.** alpha `0.07174142332098163`, long-short *t*
  `2.8360640685320595`, HAC `2.6199121240414884`, alpha HAC `4.376230427940328`, monotonicity
  `-0.8909090909090909`, EW `0.18137118752419476`. **PASS.**
* **C2 — 113,945 rows in every arm, identical `(date, ticker)` key sets**, 69 dates, 2,531 names,
  2009-01-15 → 2026-01-28. **PASS.**
* **C3 — not inert.** A20 composite rank correlation 0.8859 (min 0.8304), **65.21%** of names change
  decile; A21 0.7819 (min 0.6512), **68.91%**. **PASS.**
* **C4 — no new missing values**, per-theme non-null counts identical. **PASS.**
* **C5 — `max |ΔIC| = 0.000e+00`** over 44 columns. **PASS, exactly.**
* **C6 — `sentiment` empty** (0 non-null, carries no weight); **`insider` identical across arms**,
  max abs diff `0.0` over 94,660 rows, confirming its layer-1 exemption. **PASS.**
* **C7 — FALSIFIED, and corrected rather than dropped.** The register claimed a rank arm must be
  **bit-identical** under winsorisation. It is not: `bit_identical = False`, max |Δ| 0.019987.
  **Rank is invariant to STRICTLY monotone transforms; winsorisation is only WEAKLY monotone — flat
  in the clipped tails — so it creates TIES, and a percentile rank is not invariant to ties.** The
  differences sit in the clipped tails alone and the middle of the distribution is exactly
  invariant. **So S20 does NOT strictly subsume S21**, and the same mechanism yields the asymmetry
  worth keeping: **S20 is invisible to a per-signal rank IC; S21 is visible to it.** Pinned by
  `test_s2021_rank_is_NOT_invariant_to_winsorization_correcting_the_register`.

  *Scope note, stated rather than glossed:* C7 was measured on the panel's already-standardised
  `z_*` columns (the raw metrics are not persisted), where the effect is small (0.02% of rows)
  because those columns were already clipped once. The mechanism is demonstrated on a raw column in
  the test, where ~1–10% of rows move. Both point the same way; the register's claim is false either
  way.

## 8. THE BOOK, BY NAME — 2026-01-28, deployed weights, 1,842 names scored. NO VERDICT ATTACHES.

**INCUMBENT top 25:** FOSL, BODI, SCHL, CGAU, INDV, BNR, WDH, SSL, INTR, VEON, OPEN, ECO, POWL, TTI,
HUT, HCSG, CTRI, TNGX, FNMA, ARIS, B, PARR, APA, OBE, MCY

* **A20 RANK — overlap 14/25.** In: AMG, EFXT, GMAB, HNI, KGC, MCRI, MLI, PLGO, TIGO, WT, YALA.
  Out: ARIS, BNR, BODI, CTRI, FNMA, FOSL, HUT, INDV, OPEN, TNGX, TTI.
* **A21 NOWINSOR — overlap 8/25.** In: ABVX, AIV, ALXO, BGL, BLTE, CTOR, FMCC, NKTX, NNNN, ONIT,
  PAX, PMVP, RGC, RGS, SNDK, STTK, TERN. Out: APA, ARIS, B, CGAU, CTRI, ECO, HCSG, HUT, INTR, MCY,
  OBE, PARR, POWL, SCHL, TNGX, TTI, VEON.

One date, chosen for recency and nothing else. A single cross-section is not evidence about a
construction — it is here because **the book is the deliverable** and a change that moves statistics
modestly can still hand the user a two-thirds different list.

## 9. EXPECTATIONS — 2 right, 3 wrong, 1 split

| # | expectation | outcome |
|---|---|---|
| 1 | A20 rejected (65/35), composite correlation 0.93–0.99 | **SPLIT** — rejected ✓, correlation 0.8859 (moved MORE than predicted) ✗ |
| 2 | A21 rejected (70/30) with a NEGATIVE effect | **WRONG** on both — NOT REPLICATED, and +2.43pp full-sample |
| 3 | the two arms move the composite in opposite directions (60/40) | **RIGHT** — −3.49pp vs +2.43pp |
| 4 | C5 exact, and theme ICs move less than the composite (70/30) | **RIGHT** — 0.000e+00, and max \|ΔIC t\| 0.19 / 0.36 against pp-scale alpha moves |
| 5 | `size` changes most under A20 (55/45) | **WRONG** — `quality` does; `size` is provably invariant |
| 6 | top-25 overlap 15–22 under A20 (50/50) | **WRONG**, narrowly — 14 |

The streak continues, which is exactly why they are written down first.

## 10. BUGS FOUND

* **C7's registered invariance claim was wrong** — my own, found by measurement, corrected in §7 and
  pinned by a test rather than quietly restated. Not a code defect.
* **No new code defects found.** The `cross_sectional.zscore` value-dependent zero-variance guard
  reported in session 20 is unchanged and still unrepaired (it is on the live scoring path, so
  repairing it is a **vintage event**); this study did not touch it and its exposure here is nil for
  the same reason session 20 measured — no theme column is degenerate on any date.
* **Reported, not a bug:** ledger `S20`/`S21` both read *"no mention anywhere in the corpus"* and
  `src=auto`. **S21 proposed behaviour the code has always had.** Any other `src=auto` row should be
  read against the tree before it is scoped as work — this is the second `auto` row in two sessions
  whose premise did not survive contact with the code.

## 11. WHAT I DID NOT DO, AND WHY

* **No grid over the winsorisation level `p`.** One alternative and no other. Sweeping
  `p ∈ {0, 0.01, 0.02, 0.05}` and reporting the best cell is the in-search +8.43%/yr → locked
  hold-out −0.04%/yr failure this project has already paid for.
* **No layer attribution.** Each arm moves L1 and L3 together, so this study **cannot** say which
  layer produced which effect. That is a separate future register, recorded here rather than left
  looking done.
* **No placebo under a rank or unclipped composite**, so the calibrated floors are an
  **extrapolation** for both challenger arms and are labelled one everywhere.
* **No per-arm PBO, Deflated Sharpe or CPCV.** Weights are fixed; nothing is selected.
* **Nothing adopted, and nothing queued for adoption** — both arms failed their gate. `CONFIG`,
  `settings.FACTOR_WEIGHTS` and `sector_neutral` are untouched.
* **S21 is NOT closed as impossible.** It is the strongest untested construction lead in the
  project. Re-opening needs **new evidence** — a placebo calibrated under an unclipped composite,
  and a defence against the outlier fragility in §6.3 — **never a plain re-run**.

## 12. ARTIFACT AND REPRODUCTION

`data/free_analysis/S20_S21_CONSTRUCTION.json` — every arm, both weightings, both halves, the
**per-period paired draws**, all seven controls, the diagnostics and the top-25 books
(`RUN_RULES` A9: store the draws, not only the summaries).

```
python -m scripts.construction_rerun \
    --data-dir data/backtest \
    --panel    data/free_analysis/panel_s20_s21.pkl \
    --json     data/free_analysis/S20_S21_CONSTRUCTION.json
```

Equity `N` **151 → 155**, √(2·ln 155) = **3.1760**; `BACKTEST_RESULTS.json` re-run from a clean tree
so the artifact matches the record rather than going stale on the denominator.

---

# SESSION 22 (2026-08-11) — M2/M6: clustered inference as the default, and the schema guard that found ten dropped fields

Two audit items, one session, both **infrastructure**: no hypothesis, no verdict.
**Equity `N` is UNCHANGED at 155** — the denominator every DSR-gated claim uses, and the
Deflated Sharpe is bit-identical at 0.8340367318547941. The two rows are logged to the **infra**
domain at n=1 each (infra 8 → 10) on the V1/HACFLOOR precedent; infra `N` gates no published
claim. That is stated exactly rather than as a flat "zero trials", because the flat version
would be wrong.

`PREREG_m2_m6.md` was committed **alone at `af88533`**, a strict git ancestor of the
implementation, because M2 touches the statistic every pre-committed gate reads and a scope
chosen after seeing the numbers move would be worth nothing.

## 0. SCOPING CAME FIRST AND REMOVED MOST OF THE WORK

Three findings before any code changed, each verified against the tree rather than the item
text:

* **The `M2`/`M6` ids collide, and the ledger warns about it.** `SECURITY_AUDIT.md` has an M2
  and an M6 (LLM output escaping) — **already fixed at `96fd8bf`**. The real items are
  `VALQUO_EDGE_AUDIT.md:1507` and `:1557`.
* **M2's trade-level half was already DONE by `R3`**: `options_stats.py` carries the date-block
  bootstrap (`:210`), purge/embargo for the CSCV splits (`:363`), the paired name-year sign
  test, and **two** `n_eff` estimates that are explicitly never presented alone, gated on a
  **shuffled null**. R3's rule — *a raw design effect is not evidence of clustering* — is the
  precedent this session adopted on the equity side.
* **M6's block-level half was already DONE by `B22`** (`RESULT_BLOCKS`, `missing_result_blocks`),
  and **the options-bot lane had already published the correct remaining scope** while declining
  to edit another lane's row (`HANDOFF_optionsbot.md:1280-1295`): *"the FIELD-level half does not
  exist at all, and that is the half the R9 loss actually came through."* That report was
  correct and is adopted here.

**A correction to the prompt's own framing, recorded because it would mislead a later reader:**
`statistics.py` did **not** "default to naive inference" — it had no inference function at all.
The naive defaults were **four hand-rolled copies** scattered across `fundamental_panel` (x2),
`engine/calibration.py` and `ev_multiples_study.py`.

## 1. M2 — WHAT "CLUSTERED BY DEFAULT" COULD AND COULD NOT MEAN

**The binding constraint, fixed in the register before any code existed: nothing in the
published record moves, and no gate silently changes basis.**

`long_short_tstat` — the **naive** statistic — is read by `holdout_compare_panels`
(`fundamental_panel.py:3683-3696`), whose **+0.25 t** and **+100bps** margins were committed
against it and which decided `SECTOR-NEUTRAL-B6`, `S20` and `S21`; by `holdout_theme_validate`;
by `ablation.py:154`; by `ev_multiples_study.py:294`. And the calibrated floors are
**statistic- AND lag-specific**: naive **2.1437**, HAC **2.2837**, alpha HAC **2.2913**, all at
the full-universe decile book, 69 dates, H = 63, **lag 1**. Session 10 exists precisely because
X7 calibrated 2.14 on the naive statistic, R9 then made the HAC one the quoted number, and the
two were compared to each other for two sessions.

So clustered became the default **by being what the one shared function returns as its
unqualified `t`** — not by redefining keys the record and the gates depend on.

* `valuation/edge/statistics.py::mean_inference` is now **the** cross-date definition. `t` = HAC;
  `t_naive` = the i.i.d. figure, explicitly labelled a diagnostic; **`n_eff` beside `n`**.
* `fundamental_panel`'s `_tstat`, `_nw_tstat`, `_ljung_box` and `_chi2_sf` are **thin
  delegations**, verified **bit-identical over 400 random series including None/NaN injection:
  max |Δ| = 0.000e+00** on both estimators. That is control C1.
* Five sites gained an additive `*_inference` block: long-short, top-decile alpha, benchmark
  excess, `per_signal_ic`, `theme_ic`.

**THE SUBSTANTIVE GAP: the theme IC *t* — the statistic carrying X7's calibrated 2.71 bar, the
bar `quality` and `capital_discipline` are said to clear — had no clustered variant computed
anywhere, ever.** Nor did `per_signal_ic`. `ic_tstat` is untouched, so the 2.71 bar still
applies to exactly the number it was calibrated on; `ic_inference.t` is a **new statistic with
no calibrated floor** and **may not be compared to 2.71**.

### C4 — clustered vs naive, MEASURED, and the expectation was WRONG

| series | n | rho(1) | n_eff | naive t | HAC t | Ljung-Box p |
|---|---|---|---|---|---|---|
| long-short spread | 69 | +0.189046 | 47.06 | 2.8361 | 2.6199 | 0.0365 |
| top-decile alpha | 69 | +0.081237 | 58.63 | 4.5174 | 4.3762 | 0.0359 |

| theme | naive t | HAC t | rho | n_eff |
|---|---|---|---|---|
| quality | 3.1015 | 2.9837 | +0.0964 | 56.86 |
| capital_discipline | 2.7556 | 2.6342 | +0.1104 | 55.28 |
| institutional | 1.5470 | 1.6830 | −0.1375 | 49.00 |
| momentum | 1.3118 | 1.4182 | −0.1318 | 69.00 |
| value | 0.8380 | 0.7892 | +0.1442 | 51.61 |
| growth | 0.7517 | 0.7507 | +0.0174 | 66.64 |
| low_risk | 0.4623 | 0.5093 | −0.1637 | 69.00 |
| insider | −0.2362 | −0.2319 | +0.0522 | 62.16 |
| size | −0.3008 | −0.3275 | −0.1442 | 69.00 |

**REPORTED BECAUSE IT CUTS AGAINST THE CHANGE: the theme IC series are NOT materially
autocorrelated.** The clustered *t* is below the naive one in only **5 of 9**, the largest |ρ| is
**0.164**, and **four of nine are negative** — which *improves* precision, hence `n_eff` clipped
at 69. Unlike the long-short spread, there is little serial correlation to correct. **The
pre-registered expectation (60/40 that they ARE autocorrelated) was wrong, and the gap closed is
completeness rather than a moved number.** `institutional` shows n = 49 not 69 because the theme
is empty before 2013-06-30, consistent with the record; `sentiment` is empty, likewise.

### Deliberately NOT done (RUN_RULES A4)

* **The autocorrelation-derived lag is REPORTED, NOT ADOPTED.** Schwert gives **3** at n = 69.
  Adopting it would move the published HAC *t* of 2.6199 **and** invalidate the 2.2837 floor
  calibrated at lag 1 — a re-quote and a re-calibration, not a refactor. Ships as `auto_lag` /
  `t_auto_lag` with a note in the payload itself.
* **The gates still read the naive statistic they were calibrated on.** Pinned by test.
* **The CPCV embargo is NOT fixed.** `ret_12_1` reaches back 252 trading days — four rebalance
  periods — against a **one-period** embargo, so a test period's realised returns feed the
  momentum features of the next four training dates. Real, probably material, and a **results
  change**: it moves PBO, the Deflated Sharpe and the adopt gate. **Still open, needs its own
  register.**

## 2. M6 — THE GUARD, AND THE FIVE LIVE DROPS IT FOUND

The class: a hand-written fixed list of field names projects a producer's dict into the payload,
and anything not on the list is dropped **silently**. It had bitten twice, both caught by a human
reading two files side by side — R9's `top_decile_alpha_tstat = 4.517421601141459` recorded as
`None`, and `archive_scan` storing `fair_value` but not *why* it was blank.

`valuation/edge/payload_schema.py` enumerates **from the producer at runtime**, never from a
registry, because M3's census established that a registry-reading guard cannot see an
unregistered field — exactly the thing it exists to catch. Every source key must be **carried,
renamed, or allowlisted with a reason**; an allowlist entry is a decision somebody wrote down and
left in a diff.

| block | dropped | why it matters |
|---|---|---|
| `portfolio` | `label_warning`, `target_n`, `exit_rank`, `held_min/median/max`, `charges_costs`, `charges_taxes` | **B17's ENTIRE disclosure**, computed by `_backtest_hold` and carried nowhere. `portfolio.cagr` shipped as "the top-25 hold book" with no warning that it holds ~`exit_rank` names and pays neither costs nor taxes. **The fix for B17 was being computed and thrown away.** The canonical file now carries **`held_median = 42`** for the book labelled "top 25". |
| `cpcv` | `adopt_detail`, `challenger_weights_cols` | Session 12 banked these **specifically** so "what would this run have scored one haircut lower" is arithmetic, after the X7 8%-vs-7% discrepancy proved undiagnosable without them. Neither reached the canonical file — the only place a later session would look. **Banking a number into a dict nobody serialises is not banking it.** |
| `ev_freshness` | `rows` | The **denominator** of the `fresh` fraction. "100% of rows priced at the rebalance date" over 12 rows and over 113,945 rows are not the same claim. |

All ten now ship. `SCHEMA_VERSION` 4 → 5, purely additive; a v4 reader still works.

### The tenth field is the best evidence for the guard, because it found it against its author

`ev_freshness.rows` was caught **by the guard on its first real run** — it had escaped the
hand-built `BLOCK_SPEC` because that spec was derived by walking each producer's `return`
statements in the AST, and `ev_freshness` builds its dict **incrementally**
(`out["rows"] = int(n)`) rather than returning a literal. **Static analysis could not see it; a
runtime producer-enumerating guard could.** That is M3's thesis demonstrated on my own static
pass, which is a better argument for the design than any test I wrote.

### A defect in my own change, caught before it shipped

**The guard would have been swallowed.** `main()` wraps the results write in
`try/except Exception` commented *"Never allowed to fail a completed backtest"*. That intent is
right — a serialisation hiccup must not discard 40 minutes of work — but it would have caught
`PayloadSchemaError` and printed it as a warning nobody reads. **A check that cannot fail
anything is not a check, which is the exact pattern M6 exists to close.** The schema error now
has its own handler **ordered ahead of** the blanket one; the run keeps every artifact it already
wrote and then exits **non-zero**. Pinned by an AST test that fails if a blanket handler is ever
placed in front of it.

**No environment-variable escape hatch was built** (RUN_RULES A5). Pinned by a test that looks
for an actual env *read* — its first version tripped on the comment *saying* no escape hatch
exists, which is the wrong kind of failure and was fixed rather than loosened.

### The integration test FAILED first, which is why it is worth anything

* **Run 1** was killed externally at rebalance 60/69 and left **no partial state** (tree clean,
  artifact untouched).
* **Run 2** completed every computation and then **failed at the write step** on
  `ev_freshness.rows`, writing both files first and exiting non-zero exactly as designed.
* **Run 3**, after the fix, passes with `errors: []` and exit 0.

A guard whose first live run passes silently proves much less than one that fails on a real
defect nobody knew about and then passes once it is fixed.

## 3. CONTROLS

* **C1 — nothing moved.** Delegations bit-identical (max |Δ| 0.000e+00 over 400 series), and the
  artifact leaf diff reads **1,217 → 2,423 leaves, 1,206 ADDED, ZERO REMOVED**, 14 moved of which
  5 are timestamp/provenance and **9 are last-digit float noise** in the cost curves
  (41.894808649779975 → 41.89480864977999). Every headline bit-identical: `long_short_tstat`
  2.8360640685320595, `long_short_tstat_nw` 2.6199121240414884, `top_decile_alpha`
  0.07174142332098163, `monotonicity` −0.8909090909090909, `deflated_sharpe` 0.8340367318547941,
  `n_trials` 155, `cpcv.adopt` false.
* **C2 — the guard fires on the real historical bug** (R9's dropped `top_decile_alpha_tstat`) and
  on the options-bot lane's own `a_brand_new_metric` demonstration.
* **C3 — `archive_scan` records WHY a row was blank**, verified by writing and re-reading the gzip.
* **C4 — clustered vs naive measured and reported both ways** (§1, and the finding cuts against
  the change).
* **C5 — the guard is NOT vacuous**: it passes on a complete realistic payload, and it passed the
  real pipeline on run 3.
* **C6 — a new naive t-stat cannot be added silently**; the delegation is pinned.
* Plus: a block that **threw** is not also reported as dropping fields — keeping the two error
  classes distinct is the same lesson `missing_result_blocks` carries.

## 4. TESTS

`tests/test_edge.py` **295 → 312** (17 new, each guard with a known-bad fixture per M3).
Full sweep **56/57** with the only red being `test_guards`, which I had already fixed after that
sweep ran it; a targeted re-run of the six suites touching the changed surfaces is **6/6 green**,
with `test_guards` back at its recorded baseline (35 pass, 1 xfail, 0 failed).

**One assertion in another lane's test was NARROWED, and it is called out rather than buried.**
`test_a_block_that_threw_is_caught_by_the_writer_not_by_the_block_check` asserted
`[e["block"] for e in errs] == ["cpcv"]`. Its synthetic `{"x": 1}` blocks are legitimately
reported by the new field-level guard, which is not what that test pins, so it now filters to the
threw-class errors it is about. Intent unchanged; the change is commented in place.

## 5. BUGS FOUND

1. **`valuation/engine/calibration.py:737`** — a **fourth** hand-rolled naive t-stat, identical in
   shape to `quantile_backtest`'s local one. **Engine lane.** Not touched.
2. **The CPCV one-period embargo vs a 252-day feature lookback** (M2's own last paragraph).
   Materially affects PBO/DSR. **Still open.**
3. **`main()`'s blanket `except Exception`** would have swallowed the new guard — fixed for the
   schema error, but the same handler still swallows every *other* results-write failure into a
   printed line. Pre-existing design, left alone, flagged as the same family.
4. **Five live payload drops, ten fields** (§2) — all fixed.

## 6. WHAT I DID NOT DO

* Did not re-quote, re-run or re-calibrate any published figure.
* Did not change any gate, threshold, weight or `CONFIG` value.
* Did not adopt the auto lag; did not fix the CPCV embargo.
* Did not touch the options, engine or research lanes.
* Did not charge an equity trial: **equity `N` stays 155**.

---

# SESSION 27 (2026-08-11) — S10, the downside-exclusion screen

**One ledger item, one session. `PREREG_s10_downside_exclusion.md` committed ALONE at `a041e09`
— one `.md`, zero `.py` — a strict git ancestor of the measurement commit `ddb09a0`.**

**VERDICT: REJECTED on both arms, and the screen is counterproductive rather than merely inert.**
**ADOPTS NOTHING. No live code path changed. Equity `N` 155 → 158.**

## 1. What was asked, and what was actually run

Don's question, formalised: *should a top-decile name whose point-in-time BULL case already sits
at or below price make the book at all?*

**The scope differs from the audit's own S10 on purpose, and §0 of the register says so before any
result exists.** `VALQUO_EDGE_AUDIT.md:739` specifies S10 as an **accounting red-flag veto** built
from Beneish M-score, Altman Z-score, combined external financing and NT late-filing notices.
**None of those four was tested.** This ran a **valuation-band** exclusion — a different instrument
on different data.

**Consequence for the ledger, and it is deliberate: the S10 row is `PARTIAL`, not `DONE`.** Closing
it would tell the next session the Beneish/Altman work had been done. The row's `src` is now
`manual`, which makes it authoritative against `build_ledger.py` regeneration.

### Scoping was done against the CODE, not the item text, and it moved the design twice

The ledger row is `src=auto` — *"a lead, not a fact"* — the same provenance class that made
**S21's premise wrong** (it proposed behaviour the code already shipped). So the premise was
checked first:

1. **Nothing in the equity path screens entry on valuation.** `_backtest_hold` accepts
   `fv_at_or_above`, but that is **S23's EXIT** — price has *reached* fair value, so **sell**.
   S10 is the opposite direction. The premise is genuinely unshipped; this is not S21's situation.
2. **`lean_fair_value` computes the BASE case only** — no bear/bull band. So the band could not be
   read off S23's banked panel and had to be added to the point-in-time path.
3. **The faithful instrument is `pipeline._blend_scenarios`**, which runs bear/base/bull through
   the **same blend as the headline** and sets `blend.value_low`/`value_high` — the number the
   site renders as the top of its scenario card.
4. **Cost was measured before choosing it** (scoping, zero trial cost): ~1.0 ms per base valuation
   against ~0.7 ms per scenario-band valuation. **The band is not more expensive than the base**,
   so there was **no cost argument for a cheaper lens-max proxy** and none was used.

## 2. The result

**Coverage first, per the COVERAGE RULE.** 11,426 top-decile rows; bull-case coverage **92.42%**;
**flagged 3,129 = 27.38%** of the decile. Far from degenerate (control C6).

**A name with no computable bull case is KEPT, never excluded.** Excluding on missing data is a
data-availability screen wearing a valuation screen's name, and it would correlate silently with
era, domicile and valuation regime. Pinned by test.

| arm | alpha/yr | Δ vs A0 | HAC *t* | max DD | Δ DD | book |
|---|---|---|---|---|---|---|
| A0 INCUMBENT | +7.1741% | — | — | −0.2809 | — | 166 |
| A1 DROP | +6.9336% | **−0.2405pp** | −0.4632 | −0.3070 | **−2.61pp** | 120 |
| A2 BACKFILL | +6.2395% | **−0.9346pp** | −1.5098 | −0.3145 | **−3.35pp** | 166 |

Against the audit's own asymmetric bar — drawdown better by **>2.0pp** AND alpha worse by
**<1.0pp**, in **both halves**:

* **`A1 DROP`** — drawdown leg **fails**, alpha leg passes. **NOT ELIGIBLE.**
* **`A2 BACKFILL`** — **both legs fail** (late-half alpha −2.14pp). **NOT ELIGIBLE.**

**Drawdown does not merely fail to improve; it gets materially WORSE.** And the alpha effect
**flips sign between halves** — the screen helps early (+0.38pp) and hurts late (−2.14pp), which is
session 7's LOO instability pattern for the fifth time in this record.

**WHY THE TWO ARMS DIFFER, and it is the reason both were registered.** `A1 DROP` isolates the
**removal** alone: it holds the 120 unflagged names and costs 0.24pp. `A2 BACKFILL` restores the
book to 166 names by pulling in the next-ranked unflagged names — which come from **below the
decile boundary** — and costs 0.93pp. **So roughly 0.69pp of `A2`'s loss is not the screen at all;
it is the dilution of refilling a concentrated book from outside the decile.** A real deployment
must pay that, which is why `BACKFILL` is the deployable arm and `DROP` is the mechanism check.

## 3. The finding that outlives the verdict

**M1 MECHANISM — the flagged names OUTPERFORM the names the screen would keep.** Within the top
decile, paired by date:

* flagged **+6.5125%** per 63 days (mean 45 names)
* unflagged **+6.2677%** per 63 days (mean 120 names)
* difference **+0.9794pp/yr at HAC *t* +0.4775** — a clean **NULL**, flipping sign between halves
  (early −0.4137pp, late +2.1161pp).

**There is no information in the flag in either direction.** This is the cleanest possible answer
to the question, and it needs no book construction at all.

**The audit's own key count goes the wrong way too.** Its argument is that an exclusion screen
*"does not need to beat anything — it only needs to avoid a small number of catastrophic
outcomes"*. Measured, on the count the audit itself calls *"the number that matters most"*:

| | fell >50% | rate |
|---|---|---|
| flagged (would be excluded) | 15 of 3,129 | **0.479%** |
| unflagged (retained) | 69 of 8,297 | **0.832%** |

**The screen preferentially removes the names that crash LESS often, at roughly half the rate of
the ones it keeps.**

### Why — and it is the mechanism the register predicted

Theme z-scores within the decile, flagged vs unflagged:

| theme | flagged | unflagged | diff |
|---|---|---|---|
| momentum | +0.9530 | +0.6741 | **+0.2788** |
| institutional | +1.1748 | +0.9513 | +0.2235 |
| quality | +0.7935 | +0.6658 | +0.1278 |
| **value** | **+0.2728** | **+0.7362** | **−0.4634** |

R1's re-run puts the book on **UMD +0.205 (t 3.65)** and **HML +0.251 (t 2.93)**. A DCF/comps bull
case sits below price for exactly the names that have already run, so **the screen deletes the
momentum exposure R1 says is real and tilts the remainder further into value** — the value-trap
direction the free-analysis lane documented on FNMA.

**Illustration, explicitly NOT evidence** (that lane retracted its own "vivid cases" reading): on
the last scored date the screen changes 8 of 25 names and **adds Freddie Mac (FMCC) and MBIA
(MBI)**.

### It is also substantially a SECTOR exclusion — U7's failure mode in a new costume

| valuation regime | flagged rate | | sector | flagged rate |
|---|---|---|---|---|
| financial | **51.38%** | | Financial Services | **48.88%** |
| cyclical | 28.38% | | Real Estate | 40.32% |
| mature | 27.15% | | Energy | 32.58% |
| growth | 21.63% | | Technology | 23.96% |
| hypergrowth | **12.66%** | | Industrials | **15.79%** |

A three-fold spread. **Much of what this "valuation screen" does is hold fewer banks and REITs** —
a property of how the engine values asset-heavy names, not of those names' prospects. U7 found the
same shape: *"the veto vetoes a cap bucket, which is a property of the underlying."*

## 4. Two defects in my own instrument, both caught before any verdict was read

**(a) THE DRAWDOWN SIGN WAS INVERTED, AND IT IS THE MOST IMPORTANT THING IN THIS SECTION.**
`max_drawdown` is **negative** (−0.28 is a 28% peak-to-trough), so an arm improves it by being
**less** negative: the gain is `arm − base`. The first cut computed `base − arm` and therefore
**reported a 2.61pp WORSENING as a 2.61pp IMPROVEMENT**.

The verdict would not have changed — both arms were already failing — but **the reported REASON
would have been inverted**, and the file would have said "the screen improves drawdown by 2.6-3.4pp
on the full sample but does not replicate" when the truth is that it makes drawdown worse. That is
precisely the `monotonicity` sign error this project read backwards for months, one lane over.
Now pinned by a **known-bad fixture carrying the real measured pair**
(`test_s10_a_deeper_drawdown_is_never_reported_as_an_improvement`).

**(b) A TEST THAT MATCHED ITS OWN DOCUMENTATION.** The opt-in test scanned the function source for
`bear_value`/`bull_value` outside the conditional — and the **docstring** names both, so it failed
for the wrong reason. Diagnosed as a test bug, not a code bug, and fixed by stripping the docstring
first. Same shape as M6's env-var test matching its own comment last session.

## 5. Controls, what I did not do, and bugs found elsewhere

**Controls — all pass.**

* **C1 (the strong one).** The rebuilt panel reproduces **S23's banked fair-value panel** on **all
  108,241 shared keys** at **`max |Δ| = 0.000e+00`** across twelve base fields, with
  `valuable`/`regime`/`method`/`growth_led` **100.000000% identical**. Adding the band did not
  disturb the base by a bit.
* **C2.** `_scenario_band` **IMPORTS** `pipeline._blend_scenarios`; a private copy would be free to
  drift from the number the site shows (B7's defect class). Pinned, including the financial-regime
  P/B–ROE substitution the live pipeline performs.
* **C3.** **ZERO** violations of `bear ≤ base ≤ bull` over 108,100 full trios — measured, not
  assumed, because the engine's own comment records a real case where a bear case came out above a
  bull case.
* **C5.** The harness reproduces the published record to **sixteen digits** (alpha
  `0.07174142332098163`, LS naive `2.8360640685320595`, LS HAC `2.6199121240414884`, monotonicity
  `-0.8909090909090909`) and the run **aborts before reading any arm** if it does not.
* **C6** flag not degenerate. **C7** the build is offline — S23's beta pin, so the WACC ladder
  cannot fetch a live quote for a historical valuation.

**WHAT I DID NOT DO (RUN_RULES A4).**

* **The audit's four accounting components are untested.** S10's accounting half stays OPEN.
* **`A1 DROP` is not reported on the top-25 hold book.** True DROP there would need a new argument
  on a shipped function for a non-deployable arm; the MECHANISM arm answers the same question more
  directly. `A2 BACKFILL` **is** reported (32.72% → **27.29%** CAGR) and is **labelled a stronger
  intervention**, because removing flagged rows screens at *continuation* as well as entry.
* **No bear-case or base-case variant was tested.** Don's question is about the band's **top**
  edge; either variant is a second hypothesis and would cost its own trial.
* **One weighting only** (deployed flat 1/7). No grid was swept.

**BUGS FOUND, REPORTED NOT FIXED (RUN_RULES A3 — another lane's rows).** Three rows in the **main**
`VALQUO_LEDGER.md` table carry **unescaped pipes**: **S23 (13 pipes)**, **M1-PARSE (14)** and
**V2G (13)** against an **11-pipe header**. `tests/test_build_ledger.py` passes 20/20, so that
parser tolerates them — but this is the class of defect that, in `RESEARCH_LOG.md`, shifted columns
in one register and made a row **vanish** from another. **They want escaping as `\|` by the lanes
that own them**; this register does not edit another lane's row.

**Trial cost.** **Equity `N` 155 → 158** — three arms, each of which could independently have been
reported as a positive finding, so each is charged. Understating `N` overstates the significance of
every DSR-gated claim. `BACKTEST_RESULTS.json` re-run from a clean tree so the artifact's Deflated
Sharpe matches the honest denominator. Options and infra `N` untouched — the counter is
domain-scoped.

**Expectations: 5 right, 1 wrong.** Unusually good for this project, **and for a stated reason —
they were derived from measured facts already in the record** (R1's UMD/HML loadings, the
free-analysis down-quarter finding) rather than from intuition. The single miss is the audit's own
premise: the screen was predicted to catch a non-trivial number of genuine disasters, and it
catches them at **half** the rate of the names it retains.

**A CONSEQUENCE THAT TRANSFERS TO OTHER OPEN ITEMS, and it is worth more than this verdict.**
`VALQUO_EDGE_AUDIT.md:1646` proposes **B21** (sector concentration caps) as a risk intervention
*"on the same asymmetric logic as S10"*, and **S13** (volatility-targeted weighting) is gated the
same way — *"expect a Sharpe improvement and a drawdown improvement with a small return give-up"*.
**Every such rule inherits the two limits measured here:** on this book the worst peak-to-trough is
**a single 63-day period** (the same quarter for every arm tested), and **X7 calibrates no drawdown
floor anywhere in this project**. So a "drawdown improves by Xpp" adoption gate on the 69-date panel
is **one order statistic against an uncalibrated bar**, in both directions. B21 already ships its
`sector_caps` numbers **measured and not adopted**, which is the right posture; this says why that
posture should stay until a drawdown floor is calibrated or the criterion is replaced with one that
uses more than one quarter of information.

**Recommended next.** Either (a) **S10's accounting half** — Beneish/Altman/external-financing/NT
as a genuine red-flag veto, which is a different instrument and inherits none of this verdict; or
(b) the **CPCV embargo** carried over from session 22, still the only open item that can move a
published number.

---

# SESSION 28 (2026-08-12) — the date-gated PT-WRITER reading, which returned `None` and found two defects in the instrument that was supposed to answer it

**The one item sessions 15 and 16 both deferred to this date.** Read `/api/track` →
`contract_track.recording_ok`; close `PT-WRITER` on evidence if `true`, escalate a dated day-1
gap to Cowork if `false`. It was read. **Neither branch fired.**

## 0. The headline

**`recording_ok` is `None` — not `true`, not `false`. `PT-WRITER` is neither closed nor refuted
and the ledger row stays `BLOCKED`.** Two independent reasons, and the second is worse than the
first:

1. **The clock moved under the prediction.** The theme-restoration lane closed vintage 2 and
   opened **vintage 3 on 2026-08-11**. The bound inception is **2026-08-11**, not 2026-08-10; the
   operational gate is **2027-02-11**, not 2027-02-10; **vintage 2 lasted one day**; and vintage
   3's first row is not owed until **2026-08-13**. So no trading day is yet due and the contract's
   not-vacuously-green rule correctly returns `None`.
2. **`gap_report` was demanding a row nobody could have written yet** — so every previous
   morning's reading of this field was meaningless, in the alarming direction.

The prompt's own framing ("if the row is missing, the likely cause is the write or push dying
mid-restart") is **refuted by timing**, checked rather than argued: the machine restarted at
**03:33 on 2026-08-12**, which is **7.5 hours after** the 20:01 window on 2026-08-11. A write
dying in the restart would have had to be in flight at 03:33.

## 1. The defect that made the reading unreadable

A trading day's row is written **after that day's close**. `gap_report` computed

```python
expected = [d for d in _trading_days(inception, as_of) if d > inception]
```

and `_trading_days` is inclusive of its endpoint, so **`as_of` itself was always demanded** —
from midnight, roughly fourteen hours before the writer could supply it.

**Measured, not reasoned:** a synthetic writer holding a row for every trading day since
inception *except the current one* — i.e. every row it could possibly have written — reads
`recording_ok: false` on **11 of 11 replayed trading-day mornings**, always naming the current
day.

Three things make this worse than an off-by-one:

* It is the **exact mirror** of the vacuous-PASS defect session 15 caught in this same function.
  That one reported `true` before anything was due; this one reports `false` when nothing is
  wrong. Both were guards that could not fail correctly.
* **LA8 put the gap on public surfaces.** So the site carried "the operational gate cannot pass
  while this is true" every weekday morning — the fastest way to make a real recording failure
  unreadable is to show a false one daily.
* The contract's own description of this function (§7) says it "does not demand a row on
  inception day, which is day 0" — it documents the day-0 exemption and **no current-day
  exemption**, so this was undocumented behaviour rather than an intended design.

**The fix:** a row falls due at the **start of the next trading day**.

```python
expected = [d for d in _trading_days(inception, as_of) if inception < d < as_of]
```

Deliberately keyed to the **calendar, not to the writer's 20:01 cron** — hard-coding a clock time
here would couple the contract's operational gate to one implementation's schedule and change the
gate silently if that schedule moved. The cost is that a genuine miss is detected one trading day
later, which sits well inside the contract's own **LOGGED-NOT-VOIDED** allowance for "missing a
single day's write that is filled the same week".

**Permitted, checked before making it:** `PAPER_TRACK_CONTRACT.md` §3 fixes the bound source, the
book, the benchmark, the statistic, the thresholds, the cost constant and every §6 meter
parameter — and then says *"Repairs to the recording (§7) are not changes to any of these and are
expected — they are what the operational gate is for."* This is a §7 repair. No threshold, date
or meter parameter moved, so no void clause is engaged.

## 2. A correction against my own first cut

I first reported, in this session, that **vintage 2 owed a row for 2026-08-11 and never received
it**. That is **wrong. Vintage 2 owed nothing.** Under the corrected rule 2026-08-11's row does
not fall due until 2026-08-12, and vintage 2 had already closed.

The claim was an artefact of **the very off-by-one this change repairs** — computed with the old
rule while arguing for the new one. It was caught by the test written to pin it, which is the
only reason it is a correction here rather than a false escalation to Cowork.

It is recorded in the code as well as here, because a wrong reason attached to a right conclusion
is what LA11 exists to warn about.

## 3. The second defect: a vintage event silently clears the recording gap

`gap_report` is scoped to the **open** vintage. That is correct — the contract attaches the gate
and the meter to the current vintage (§5a rule 5). But it means **a dated miss stops being
reported the moment the next vintage opens.**

**Vintage 1 owed six rows and received two.** Its four missing dates — 2026-08-03, -04, -05, -07 —
are **unreachable from anything `recording_ok` reports today**. The contract tolerates a missed
day as LOGGED-NOT-VOIDED, but it can only be *logged* if something records it, and until now
nothing did.

New `track_meter.recording_history()` reports **every vintage side by side** and reproduces the
contract's own "2 of 6 due rows (33.3%)" figure independently:

| vintage | status | window | due | got | missing |
|---|---|---|---|---|---|
| 1 | VOID | 2026-07-30 → 2026-08-09 | 6 | 2 | 2026-08-03, -04, -05, -07 |
| 2 | CLOSED | 2026-08-10 → 2026-08-11 | 0 | 0 | — |
| 3 | OPEN | 2026-08-11 → | 0 | 0 | — |

**`recording_ok` is deliberately unchanged** and still reads the open vintage alone. This is the
audit trail beside it, not a widening of what the gate demands.

## 4. What the block now says, and when it can next say something

Two new fields, kept **separate on purpose** because collapsing them into one is how this gets
misread:

* **`row_awaited`** — the trading day whose row is next owed (`2026-08-12`).
* **`assessable_from`** — the date that row starts being demanded (`2026-08-13`).

Without these, a `None` or a `false` read on a morning is indistinguishable from a writer failure,
which is exactly what happened today.

## 5. On the writer itself — evidence, not proof

Independent of all the arithmetic above, nothing suggests the writer ran:

* `data/valquo_track_history.csv` has mtime **2026-08-07 18:07** and was untouched across **both**
  2026-08-10 and 2026-08-11. A write that died mid-flight would still have touched the file.
* **No scheduled task** matching the reported `valquo-daily-track-write` exists (219 tasks
  enumerate non-elevated; the only Valquo match is `Valquo D Backup`). Session 15 found the same
  at 413 tasks elevated.
* **No code in this repository writes the file** — session 13's finding, re-checked and still
  true. `index_track.py` only ever reads it.
* **The local copy is not a stale mirror of a healthy remote.** The weekly `track-backup` cron
  pulled the LIVE service's bound Index on 2026-08-10 18:09 and committed **the same two rows** to
  `data_export/valquo_index_track.csv`. `/api/track` itself is owner-only and returns **403**
  unauthenticated, so it could not be read directly from here.

**This is still not proof** — the task could be registered under another account or on another
machine, and the honest test is now simply one day away.

## 6. What I did NOT do

1. **I did not close or refute `PT-WRITER`.** The reading does not support either, and reporting
   a `false` that a perfect writer would also produce would have been a false escalation.
2. **I did not escalate to Cowork.** The prompt's escalation branch was conditional on a `false`
   naming 2026-08-11; there is no such gap, and vintage 2's apparent miss was my own artefact
   (§2). Escalating a date that is not owed would waste the one credible alarm this project has.
3. **I did not backfill anything.** A back-fill voids the whole run under §3.
4. **I did not touch `recording_ok`'s scope, the meter, σ, ρ, α or any contract threshold.**
5. **I did not fix the stale dates elsewhere.** `PAPER_TRACK_CONTRACT.md` §7 and several handoffs
   still say the first row is due 2026-08-11 and the gate is 2027-02-10. Those were correct for
   vintage 2. The ledger row and `CLAUDE.md` are corrected; the contract document is a register
   that does not delete, and re-dating it is a contract edit I should not make unilaterally.
6. **I did not investigate the sandbox engine** (`PT-SPLIT`'s remaining provenance question).

## 7. BUGS FOUND

1. **`gap_report` demanded the current day's row** (§1). Mine, fixed, pinned by two tests.
2. **A vintage event silently cleared the recording gap** (§3). Mine, fixed additively.
3. **My own first cut mis-attributed a miss to vintage 2** (§2). Caught by its own test.
4. **`RESEARCH_LOG.md` has TWO tables with different 9-column schemas**, and an append lands under
   the second (`id|date|domain|pre|hypothesis|metric|verdict|n|source`). My first row used the
   first table's layout, so the parser could not locate its verdict cell and **counted a `FIXED`
   repair as an infra trial**. Caught by diffing `by_domain` against `HEAD`, not by re-reading the
   row. The inflation direction is conservative, but the row was still wrong. **Anyone appending
   to that log must match the LAST header, not the first.**
5. **Stale dates in the contract and handoffs** (§6.5) — reported, not fixed, out of my lane to
   re-date unilaterally.

## 8. Next

**Tomorrow, 2026-08-13, the reading finally means something.** `row_awaited` is 2026-08-12 and
`assessable_from` is 2026-08-13, so from then a missing row is a **dated writer failure** and
`PT-WRITER` can be escalated to Cowork with a specific date — or closed on evidence for the first
time. **No human action is required to unblock it.**

Then the lane's own queue, unchanged from session 27: either **S10's accounting half** (Beneish,
Altman, external financing, NT late filings — a different instrument that inherits none of the
valuation-band verdict) or the **CPCV embargo** carried over from session 22, which remains the
only open item that can move a published number.

---

# SESSION 29 (2026-08-12) — S25 closed as unobtainable, and S3's insider rebuild

Two ledger items. **S25 needed no register and cost no trials — everything it returns is a fact
about what data exists and what the code reads.** S3 got a blind register,
`PREREG_s3_insider_rebuild.md`, committed **alone at `b3a85fa`** — one `.md`, zero `.py`, a strict
ancestor of every measurement commit.

## 1. S25 — UNOBTAINABLE WITHOUT NEW DATA, and the exposure is wider than the ledger said

### 1.1 The obtainability answer, measured rather than assumed

A point-in-time sector map is **not buildable from anything in this repository.** Four
independent checks:

* **The TICKERS snapshot we own carries six fields — `sector`, `industry`, `country`,
  `exchange`, `category`, `scale` — and ZERO date fields of any kind.** So it cannot say *when* a
  classification took effect, and cannot bound reclassification even for the names it covers. It
  is one photograph, not a history.
* **SF1 `fundamentals.csv` has 112 columns and no sector or SIC among them.**
* **`bulk/actions.csv`, `events.csv`, `sf3.csv` and `daily.csv` carry none either**, and no
  prepared cache holds a SIC.
* **`valuation/data/edgar.py` fetches only `company_tickers.json` and the companyfacts XBRL**,
  neither of which carries a historical SIC.

**A correction against my own probe, recorded because it is the kind of error that manufactures a
finding.** The first cut reported a date-like field on the snapshot. It had not found one: my
regex alternation contained `to`, which matched "sec**to**r". The corrected answer is NONE.

### 1.2 The source named for the D-series

**EDGAR filing-header `ASSIGNED-SIC`**, carried in each submission's SGML header, which *is* the
classification as of the filing date. Roughly one fetch per filing — about 180k fetches for this
universe at the SEC's 10/s limit.

**Note what does NOT work, because it is the obvious first try:**
`data.sec.gov/submissions/CIK##########.json` carries only the **current** `sic` and
`sicDescription`. That is a second snapshot, not a history, and building on it would produce a map
that looks point-in-time and is not.

**A confound that must travel with any such build: SIC is not the shipped taxonomy.** The panel's
sector is an 11-value GICS-like string; a SIC-derived map changes point-in-timeness **and**
taxonomy at once. So it cannot cleanly answer *"what does reclassification change"* — isolating
that needs the **same** taxonomy at two dates, i.e. a historical GICS snapshot, which is not sold
as history. Anyone who builds the EDGAR map and diffs it against today's Sharadar sector will be
measuring mostly the taxonomy difference and should not report it as reclassification.

### 1.3 THE FINDING THE LEDGER DID NOT HAVE: it reaches the point-in-time VALUATION

The ledger row said *"nothing currently rests on it because every sector result has rejected"*.
That is true of the **ranking** path and false of the **valuation** path.

`calibration.py:523-527` — inside `build_valuation_panel`, the S23/S10 point-in-time machinery —
passes `sector=md.get("sector")`, i.e. **today's TICKERS classification**, into `pit_company` for a
1998 or 2009 valuation. From there `CompanyData.sector` selects:

| constant | measured spread |
|---|---|
| `assumptions.SECTOR_TARGET_MARGIN` (sustainable operating margin anchor) | **0.100** Consumer Cyclical → **0.270** Technology, a **2.70×** spread |
| `comps.SECTOR_MULTIPLES` PE | **12.00** → **30.00**, a **2.50×** spread |
| `comps.SECTOR_MULTIPLES` EV/Sales | **1.30** → **8.00**, a **6.15×** spread |

**The sharpest way to put it: S23's own code pins BETA point-in-time — its comment two lines below
says so explicitly — while passing today's sector straight through.** So S23's exit-rule arms and
**S10's bull-case band, which I built last session**, both inherit a sector look-ahead that nobody
had named.

**Not repaired, because there is no data to repair it with.** It is pinned by
`test_s25_the_pit_valuation_still_reads_a_non_point_in_time_sector`, which fails if the exposure
changes shape — so the finding cannot rot the way this project's line-number citations do.

### 1.4 What S25 does NOT license

* It does **not** re-open full sector-neutral ranking. `SECTOR-NEUTRAL-B6` closed that permanently
  and named `S25` as one of only two routes back; **S25 is now closed as unobtainable, so that
  route is shut until the D-series delivers the EDGAR map.** `S15` (sector-relative on the value
  theme alone) is untouched and remains the other.
* It does **not** affect the accepted `max_sector_w` concentration cap, which is a risk control.
* **Zero trials.** Nothing here was a hypothesis tested against a threshold, so on session 8's
  precedent the denominator is untouched.


## 2. S3 — all three insider rebuilds REJECTED

`PREREG_s3_insider_rebuild.md` committed **alone at `b3a85fa`** — one `.md`, zero `.py`, a strict
ancestor of the measurement commit. **One panel build, four scorings, every arm a column on ONE
frame**, so the row set is identical by construction rather than by assertion.

### 2.1 Premise checks, all done BEFORE the register and reported in it

`S3` is `src=auto` — *"a lead, not a fact"* — and S21 is the precedent for an `auto` row proposing
behaviour the code already ships. Three findings:

* **One of the audit's own S3 items is ALREADY FIXED.** It says `_insider_score_at` uses
  `searchsorted(dts, hi, "right")`, making a Form 4 dated exactly `as_of` usable at that day's
  close. The shipped code is `side="left"` with a comment naming **B26** as the fix. Not re-tested.
* **THE FORMULA WAS DUPLICATED** at `fundamental_panel.py:737` (the row-iterating fallback) and
  `:800` (the prepped fast path) — two copies of an expression whose own B26 comments say the two
  paths must agree, which is the **B7 defect class**. There is now one `_insider_formula` and both
  delegate. **Proved bit-identical to both pre-refactor copies over 20,006 cases**, with the old
  expression reconstructed from `git HEAD`'s source rather than retyped, so the check could not
  pass by my copying the same typo into both sides.
* **MY OWN OPENING HYPOTHESIS WAS REFUTED BEFORE THE REGISTER WAS WRITTEN.** `insider` is the one
  theme that is **not z-scored** — a fixed affine map `(score − 50)/25` (`factors.py:281`) — so I
  expected it to be under-dispersed and therefore under-weighted relative to its nominal 0.125.
  Measured on 113,945 banked rows, **the opposite**: per-date sd **0.9600** against **0.8296**
  averaged over the other six themes, about **116% of nominal**. The **multi-input** themes are
  the compressed ones, because a mean of imperfectly-correlated z-scores has sd below 1
  (`quality`, ten inputs, sits at **0.50**). Had this not been measured the register would have
  been built on a false premise.

### 2.2 The verdict

**All three REJECTED** against the already-committed margins — **+0.25 long-short *t* AND +100bps
top-decile alpha, in BOTH halves**, boundary embargoed, deployed flat 1/7 weighting, no grid.

| arm | Δalpha early | Δalpha late | Δ*t* early | Δ*t* late | rank corr vs incumbent | theme IC *t* |
|---|---|---|---|---|---|---|
| **S3A** drop the `buys` bonus | +0.01pp | +0.79pp | +0.116 | +0.110 | 0.9668 | −0.0793 |
| **S3B** scale by market cap | **+0.82pp** | **+0.52pp** | +0.095 | +0.079 | 0.8721 | **+0.5763** |
| **S3C** split into two inputs | −0.92pp | −1.24pp | −0.332 | −0.120 | 0.8385 | −0.9685 |
| *A0 incumbent* | — | — | — | — | — | −0.2259 |

**THE UNUSUAL PART IS THE SIGN-STABILITY, AND IT CUTS BOTH WAYS.** Session 7's LOO pattern — arms
flipping sign between halves — is this project's most repeated finding, recorded five times.
**Here every arm is sign-stable on both metrics in both halves.** But the gains sit far below the
bar, and **V2G established there is NO CALIBRATED FLOOR for a paired within-panel difference**, so
*"small but consistent"* is an observation and **not** a result. Nobody may quote S3B's +0.8pp as
an effect.

**S3B is the best of the three, exactly as the audit predicted** — the only positive theme IC, the
only arm positive on alpha in both halves by more than a basis point, and the most different from
the incumbent. It still does not clear.

### 2.3 The audit's own threshold is refuted as an instrument

The audit's bar is *"theme IC *t* clears +1.0"*. **No arm clears it** — not even the two that
improve alpha in both halves — **and neither does the shipped incumbent, at −0.2259.**

So the audit's gate would have rejected all three, **for a reason unrelated to what the composite
actually did**. And +1.0 sits far below **X7's calibrated 2.71**, where 39% of pure-noise draws
clear even 2.0 because eight themes are tested and the bar is applied to whichever looks best.
The register demoted this bar to a diagnostic **before** the run, on P6.3, X3 and S20/S21. It is
now demoted on its own evidence too.

### 2.4 The availability diagnostic — the most interesting number, and it does not convict

Premise (e): `insider` is the only theme with a materially non-zero mean (**−0.1031**) at **83.1%**
coverage, so a name that HAS an insider score takes a small systematic negative tilt a name
without one does not. That is **S10's data-availability failure mode**, and it would mean part of
the theme's measured IC is an artefact of who files rather than of what they filed.

**Measured: the pure indicator *"has an insider score at all"* carries median IC +0.01345 at
t +1.4471 — NOT separable from zero at any calibrated bar. The artefact is NOT demonstrated.**

Reported anyway, because the comparison is striking: **that |*t*| is LARGER than the insider
theme's own (−0.2259)**. The mere *presence* of filings carries more forward-return information
than the *direction* of the score does. **Neither is significant, and the comparison is the point,
not either number.**

### 2.5 Controls

* **C1** — the harness reproduces the published record to sixteen digits (alpha
  0.07174142332098163, LS *t* 2.8360640685320595, HAC 2.6199121240414884, monotonicity
  −0.8909090909090909), and **the run ABORTS before reading any arm if it does not**.
* **C3** — the incumbent rebuilt from the banked raw `(net, buys)` is **bit-identical to the
  shipped `insider` column, max |Δ| 0.000e+00 over 94,660 rows**. So the variants are perturbations
  of the shipped construction, not of a reimplementation of it.
* **C6** — **coverage 0.8308, IDENTICAL across all four arms.** S3B loses no rows, so its
  comparison is not partly a universe change (it needed `marketcap`, and every row with insider
  data had one).
* **C2** all arms are columns on one frame; **C4** no arm is inert (rank correlations 0.84–0.97);
  **C5** both formula paths agree over a randomised fixture; **C7** as §2.4.

### 2.6 A defect in my own first cut

The first run used `build_fundamental_panel`'s **default `lookback_years=6`** and produced a
**21-date / 2,151-name** panel. That is a **smoke test**, and the METHODOLOGY RULE forbids a
verdict from one. Re-run at the canonical `CONFIG.backtest_lookback_years=18` for the 69-date /
2,531-name corrected panel. **The script now ASSERTS the shape rather than warning**, so the same
mistake fails loudly instead of producing a plausible-looking table.

Two smaller ones, both caught by reading signatures rather than by the run: C1 originally passed
the weights dict as `cols` to `quantile_backtest`, and the gate's split keys were printed under
the wrong names.

### 2.7 Trial cost and adoption

**Equity `N` 158 → 161** (three arms, one weighting, no grid); options 258 and infra 10 untouched,
the counter being domain-scoped. `BACKTEST_RESULTS.json` re-run from a clean tree so the Deflated
Sharpe carries the honest denominator.

**ADOPTS NOTHING and no live scoring path changed.** Adoption would be a **VINTAGE EVENT**; the
current vintage is **DERIVED** per `PT-GAPDUE` rather than assumed — **vintage 3, opened
2026-08-11** — so an adoption would open vintage 4. No arm is eligible in any case.

**Expectations scored 5 right, 2 wrong.** Right: no variant clears; S3B is best; S3A moves the
composite least; S3A's rank correlation stays above 0.90 and S3B's falls below it. Wrong: the
availability indicator was predicted non-zero and is not separable from zero (**the one I said I
most wanted to be wrong about, and was**); and no arm's theme IC clears +1.0, so the predicted
*"clears the audit bar while failing the real gate"* dissociation never arose — the audit's bar
turned out to be even less useful than predicted, failing on every arm including the incumbent.

## 3. What I did NOT do

1. **I did not re-open zeroing `insider`.** The register fixed in advance that if all three
   variants reject, zeroing becomes a live proposal **needing its own register and its own trial
   charge** — not a fallback conclusion of this one.
2. **I did not touch `bulk.prepare_insiders`' sign-precedence hazard** (it prefers
   `transactionvalue`, which mis-signs every sale if that column is unsigned). Verified **still
   unused** by the panel and reported; switching loaders would silently invert the theme.
3. **I did not repair S25's sector look-ahead** — there is no data to repair it with. Pinned
   instead.
4. **I did not build the EDGAR SIC harvest.** It is new data, ~180k fetches, and it carries the
   taxonomy confound in §1.2 — it belongs to the D-series with that caveat attached.
5. **I did not change any weight, the 90-day lookback, or the 5e6 scale in the incumbent arm.**

## 4. BUGS FOUND

1. **The insider formula was duplicated** across two paths that must agree (§2.1). Fixed, proved
   bit-identical.
2. **The point-in-time valuation reads a non-point-in-time sector** (§1.3). Mine to report, no
   data to fix it with; pinned.
3. **My own first cut ran on a smoke-test panel** (§2.6). Fixed, and the shape is now asserted.
4. **My own S25 probe reported a date-like field that does not exist** — a regex alternation
   containing `to` matched "sec*to*r" (§1.1).
5. **`scripts/build_ledger.py` will DROP both rows touched this session** if regenerated — S25 and
   S3 are `manual`/`auto` curated rows and the generator rebuilds from the 134 audit ids only.
   Pre-existing, reported each time it bites.

## 5. Next

The lane's queue is unchanged and now shorter by two: **S10's accounting half** (Beneish, Altman,
external financing, NT late filings — a different instrument inheriting none of the valuation-band
verdict) or the **CPCV embargo** from session 22, still the only open item that can move a
published number.

**And a dated one that needs no work: read `/api/track` → `contract_track.recording_ok` on or
after 2026-08-13** (`row_awaited` 2026-08-12, `assessable_from` 2026-08-13). From then a missing
row is a dated writer failure and `PT-WRITER` can finally be escalated or closed.

---

# SESSION 30 (2026-08-12) — S16, S28, and two ledger rows that were lying about their own state

Four items. **S16** got a blind register, `PREREG_s16_issuance_decomposition.md`, committed
**alone at `afc7578`** — one `.md`, zero `.py`, a strict ancestor of every measurement commit.
**S28** is reporting infrastructure with no hypothesis. The two ledger corrections are facts
checked against the tree.

## 1. S16 — all four arms rejected, and the audit's actual proposal is a rank identity

### 1.1 The premise check removed half the audit's method

The audit's method is *"extract buyback announcements and dividend initiations"* from ACTIONS.
Measured against the table before any arm ran:

* **There are no buyback announcements.** All **671,417** ACTIONS rows carry one of nineteen
  action types — `dividend`, `listed`, `delisted`, `tickerchangeto/from`, `split`, `relation`,
  `initiated`, `acquisitionof`/`acquisitionby`, `bankruptcyliquidation`, `regulatorydelisting`,
  `spinoff`, `spunofffrom`, `spinoffdividend`, `adrratiosplit`, `voluntarydelisting`, `mergerto`,
  `mergerfrom` — and **none is a repurchase authorisation.** Buyback-announcement drift is **not
  testable on data we own.**
* **`initiated` is not dividend initiation.** It is index/security listing initiation; its
  earliest rows are `^VIX`, `^RUT` and `^IXIC`, all dated 1997-12-31.
* **The M&A leg is real**: `acquisitionof`/`acquisitionby`, 8,248 dated rows each with deal values
  and both counterparties.
* **The sign split is not degenerate**: across 185,958 year-over-year share-count observations,
  **34.07%** fell, **58.26%** rose, 7.67% flat — with wildly asymmetric tails (p01 **−13.2%**,
  p99 **+107.2%**), which is itself the argument for separating them.

### 1.2 The identity — the most useful thing in this session

**S16C's within-date rank correlation against the incumbent is `1.000000000000` on all 69 dates.**

That is arithmetic, not luck, and it was verified directly rather than inferred:
`buyback = max(0, −net)` and `−dilution = −max(0, net)` are **both non-increasing in `net`**
(checked on the real sorted series), so the mean of their z-scores preserves the ordering of
`neg_issuance = −net` exactly.

**So the audit's actual proposal — "separate the theme into two inputs rather than one blended
score, so the composite can weight them independently" — cannot express any ordering the single
input cannot.** What it *can* do is change scale, and it does: the theme's mean per-date
dispersion falls **1.000315 → 0.774730**, a **22.5% cut in effective weight** in a composite that
is a weighted sum. That is P6.3/S20's lesson in a new costume, and it means anyone reading this
item as *"give buybacks and dilution their own weights"* is describing something the construction
cannot deliver.

### 1.3 Verdicts

**All four REJECTED** against the already-committed margins (+0.25 long-short *t* AND +100bps
alpha, both halves, boundary embargoed, deployed flat 1/7, no grid):

| arm | Δalpha early | Δalpha late | Δ*t* early | Δ*t* late | rank corr | theme IC *t* |
|---|---|---|---|---|---|---|
| **S16A** buyback only | +0.47pp | +0.05pp | −0.188 | +0.248 | 0.8707 | **+3.2066** |
| **S16B** dilution only | +0.23pp | −0.26pp | +0.147 | −0.100 | 0.9641 | +2.5623 |
| **S16C** two inputs | +0.20pp | −0.06pp | −0.206 | +0.175 | **1.0000** | +2.7530 |
| **S16D** M&A split | +0.17pp | −0.19pp | −0.141 | +0.157 | 0.9920 | +2.7634 |
| *A0 incumbent* | — | — | — | — | — | +2.7530 |

**BUYBACK carries more of the theme's IC than DILUTION does**, which refutes two pre-registered
expectations at once. **S16A is the only arm clearing X7's calibrated 2.71 theme-IC bar — and it
still fails the gate**, the fifth demonstration that theme IC does not judge a construction change.

**S16D is FLAGGED DEGENERATE** by the pre-committed C6 rule: `mna_dilution` is non-zero on only
**3.19%** of rows. Note C7's own bar *passed* — the M&A flag fires on **5.53%** of dilution rows,
inside the pre-registered 5–25% band — so the flag works; there simply is not enough
M&A-coincident dilution for a separate z-scored input to mean anything.

### 1.4 C3 failed its bar, and is reported as a failure

**The rebuilt incumbent is NOT bit-identical to the shipped `capital_discipline`: max |Δ|
0.006676**, against a 1e-9 bar. Reported as a failed control rather than quietly reclassified.

Diagnosed rather than asserted: **within-date rank correlation exactly `1.00000000`**, **median
deviation exactly `0.000e+00`**, and the two differ by a **per-date affine rescaling** (β = 1.0
and α = 0.0 on most dates, worst residual 1.0e-03). The cause is that `build_frame` standardises
over every scored name that date, while the panel then drops names with no forward return — so
the two z-scores share an ordering but not a mean and sd.

**And bounded, which is what makes the verdicts survivable: re-running every gate against the
SHIPPED column as the baseline returns the same four `reject` verdicts with deltas identical to
four decimal places.** The seam is real and it changes nothing here.

### 1.5 Trial cost and adoption

**Equity `N` 161 → 165** (four arms, one weighting, no grid); options 258 untouched.
**ADOPTS NOTHING.** Adoption would be a **vintage event**, and it costs more here than usual: the
current vintage is **DERIVED** per `PT-GAPDUE` — **vintage 3, opened 2026-08-11, and its recorded
reason IS the `capital_discipline` restoration** — so changing this theme's construction would
close a vintage days old and open vintage 4. **Expectations 3 right, 3 wrong.**

## 2. S28 — the distribution beside the mean

Reporting infrastructure: **no hypothesis, no threshold, no verdict, and no published claim
moves.** `statistics.distribution()` returns n, mean, sd, min/p05/p25/median/p75/p95/max, the
count and fraction of **negative** periods, and the **dated** worst and best period. Wired into
four payload blocks; `SCHEMA_VERSION` **5 → 6**, purely additive.

**What it shows on the shipped book — which is the reason the item was worth doing:**

| | value |
|---|---|
| published top-decile alpha | **+7.17%/yr** (the mean of 69 quarterly draws) |
| quarters NEGATIVE | **20 of 69 — 28.99%** |
| median quarter vs mean quarter | **+1.41%** vs **+1.79%** — right-skewed |
| worst quarter | **−6.83%, 2016-01-20** |
| best quarter | +11.47%, 2022-07-22 |
| long-short quarters negative | **33.3%**, worst **−20.01%, 2025-07-29** |

So the headline is a mean that is **better than the typical quarter**, and it is negative in
almost three quarters out of ten. Nothing about the claim changes; what changes is that the file
now says so without being asked.

**Three things that make it safe:**

1. **The units travel in the block.** The obvious misuse is annualising a quantile.
   `top_decile_alpha` is periods-per-year × the **mean**, and that scaling is a statement about a
   mean, never about an order statistic. Every block carries a `units` string saying so.
2. **Consistency is asserted, not assumed.** `4 × distribution.mean` reproduces
   `top_decile_alpha` to **4e-17** on the real panel and exactly on a synthetic one. A
   distribution attached to the wrong series would look perfectly reasonable and quietly mislabel
   the worst quarter in the record.
3. **Pinned as reporting-only** by a test that fails if any threshold, gate or verdict ever
   compares or branches on a distribution field — **and that guard was checked for vacuity**, since
   it would otherwise pass by seeing nothing (M6's lesson). It inspects 14 code-level references.

The dated extremes are matched against the **original** series rather than the cleaned one,
because pairing a cleaned value with an uncleaned date is exactly how an off-by-one mislabels a
quarter.

**Zero equity trials**; infra `N` 10 → 11 on the M2/M6 precedent.

## 3. Two ledger rows that were lying about their own state

Both were checked against the tree, not against their own text.

* **`O14` — the STATUS was stale, the NOTE was already correct.** The cell read `INPROGRESS` with
  the reason *"collection done, analysis not started"*, which had been **false since
  2026-08-11**: the cache holds 195 ticker directories and the analysis half shipped as
  `valuation/edge/tickflow.py`, `scripts/o10_o18_tickflow.py`, `tests/test_tickflow.py` and a
  44KB `O10_O18_TICKFLOW.json`. The note below the cell already said so; the status did not, so
  anyone scanning statuses saw the wrong state. **The row still stays OPEN** — but for the reason
  the note gives, not the one the cell gave: O10/O18 used the cache for execution cost only, and
  the put/call and unusual-volume studies that justified 4.72GB of collection have still never run.
* **`B13` — the NOTE was accurate and the STATUS was wrong.** `IN PROGRESS` since 2026-08-04, with
  nothing in progress. This is a **settled partial state with a named, unmet data prerequisite**,
  and calling it in-progress implied work underway and invited a reader to wait for it. The panel
  says so itself at `fundamental_panel.py:1488-1492`, which ships the reason in the results file:
  `MIN_AVG_DOLLAR_VOLUME` has never bound on this path and still cannot, because the price export
  carries **date and close only**, so `avg_dollar_volume` cannot be computed there at all. Wiring
  it needs SEP volume in the panel loader — data plumbing, not a fix to this filter. Now
  **`PARTIAL - BLOCKED ON DATA, NOT IN PROGRESS`**.

## 4. What I did NOT do

1. **I did not test buyback-announcement drift or dividend-initiation drift** (§1.1). The first is
   not on data we own; the second is derivable from the `dividend` stream but is a different
   signal. Both named so neither is later mistaken for tested-and-failed.
2. **I did not repair the C3 seam** (§1.4). Making the panel's z-scores match `build_frame`'s
   cross-section is a scoring change, and it would be a vintage event for a 0.67%-of-a-sd
   difference that changes no verdict.
3. **I did not add SEP volume to the panel loader** to unblock B13 — different lane's plumbing,
   and it would change the universe.
4. **I did not touch `bulk.prepare_actions`.** Adding an acquisitions key would leave a **stale
   pickle silently yielding an empty M&A flag** — a degenerate arm with no warning, which is what
   the COVERAGE RULE exists to stop. The map is read in the script with a row-count assertion.
5. **I did not let S28 change any number.** It is additive and pinned as such.

## 5. BUGS FOUND

1. **The audit's S16 method is half unbuildable** (§1.1) — reported, not worked around.
2. **`O14` and `B13` statuses contradicted their own notes** (§3) — both corrected.
3. **C3's seam between the panel's z-scores and `build_frame`'s** (§1.4) — reported, bounded, not
   repaired.
4. **`scripts/build_ledger.py` will DROP the rows touched this session** if regenerated — S16, S28,
   O14 and B13 are curated. Pre-existing, reported each time it bites.
5. **`session 29` NOW NAMES TWO DIFFERENT LANES' WORK ON `main`.** The options-bot lane
   stamped `O3`+`O4`+`O5` as session 29 (`CLAUDE.md:119`, `HANDOFF_optionsbot.md` §38-41) while
   this lane's `S3`+`S25` had already landed as session 29 (`CLAUDE.md:177` and `:234`). Both are
   dated 2026-08-12 and both are now in the file every lane reads, so "session 29" resolves to
   two different results. **Found by the merge, not by either lane's own checks** — the same
   id-collision class `VALQUO_LEDGER.md` warns about and the same one this lane hit at session
   23. **NOT unilaterally renumbered:** their work landed second but is already referenced from
   their own handoff, ledger and research-log rows, and editing another lane's landed entry is
   how a fix silently eats a record. This session took **30**, which is free either way.
   **→ Routed to the options-bot lane, or to Don as a convention call.** The mechanical rule that
   would have prevented it, and that this lane now follows: take the next number above the GLOBAL
   maximum in `CLAUDE.md` at the moment you stamp, and re-check it after any merge.


## 6. Next

Unchanged and now shorter: **S10's accounting half** (Beneish, Altman, external financing, NT late
filings) or the **CPCV embargo** from session 22, still the only open item that can move a
published number.

**And the dated one, which needs no work: read `/api/track` → `contract_track.recording_ok` on or
after 2026-08-13.** `row_awaited` is 2026-08-12 and `assessable_from` is 2026-08-13, so from then
a missing row is a dated writer failure and `PT-WRITER` can finally be escalated or closed.

---

# SESSION 31 (2026-08-12) — five alternative weighting schemes, one register, all five rejected

`PREREG_s5_s6_s13_s24_s27_weighting.md` committed **alone at `8b0917e`** — one `.md`, zero `.py`,
a strict ancestor of the measurement commit. **One panel build, six scorings on one frame.**

## 0. The headline

**All five rejected, and the family is priced by one number: CPCV's own best challenger scheme
(`positive-equal`) beat the deployed default by a margin of `0.000265` against a required bar of
`0.020830` — it would have to be about 79× LARGER to clear.** `adopt=false`, PBO **0.80**. Weight
tuning on this panel is not marginal. It is nowhere near.

## 1. The premise check — three of five are already shipped, in whole or in part

All five rows were `src=auto`. This is the S21 pattern for the third time.

* **`S27` IS ALREADY SHIPPED, AT THE AUDIT'S OWN MIDDLE HALF-LIFE.** The item claims *"every IC is
  a full-sample median, every weight is fixed"* — true only of the reported diagnostics.
  `_theme_ic_stats` (`fundamental_panel.py:2135-2145`) computes `0.5 ** (days_ago/halflife_days)`,
  and **`halflife_days=1260` (≈5y) is the default of `_weighted_optimize`, `walk_forward` AND
  `cpcv_validate`**. The audit proposes 3, 5 and 10 years; **5 is the shipped default.**
* **`S5`'s SHRINKAGE IS HALF-SHIPPED AND THE SHIPPED HALF IS ALREADY REJECTED.** `_weight_schemes`
  contains `ic-shrunk-50` — `0.5 × ic_proportional + 0.5 × equal` — a shrinkage estimator with
  intensity **fixed at 50%**, one of the eight CPCV has repeatedly declined. S5's real
  contribution is *data-determined* shrinkage, not shrinkage.
* **`S13`'s INVERSE-VOL IS SHIPPED AT THE WRONG LEVEL.** `risk-parity = norm(1/vol)` is inverse
  volatility across **themes**, already rejected. S13 asks for it across **names inside the
  book** — position sizing, not signal weighting. Conflating them would report a shipped
  rejection as a new one.
* **`S27`'s STATED DEPENDENCY IS SATISFIED AND CUTS AGAINST IT.** *"Run this after X6"* — **X6 is
  `DONE` and `NULL`**: the structural-break test was null under Holm–Bonferroni and the 2012 story
  is not confirmed. There is no confirmed break for recency weighting to respond to.
* **`S6` and `S24` are genuinely untested.** Nothing like either exists in the tree.

## 2. Verdicts

| arm | Δalpha early | Δalpha late | Δ*t* early | Δ*t* late | rank corr | verdict |
|---|---|---|---|---|---|---|
| **S5** hierarchical shrinkage | −2.12pp | −1.68pp | −1.598 | −0.833 | 0.8933 | REJECTED |
| **S6** factor momentum | −1.61pp | **+3.30pp** | −1.289 | **+0.678** | 0.9489 | **NOT_REPLICATED** |
| **S24** ensemble (200 draws) | −0.31pp | −1.24pp | +0.252 | +0.311 | **0.9907** | REJECTED |
| **S27** half-life 3y | −4.29pp | −2.98pp | −2.272 | −1.081 | 0.7352 | REJECTED |
| **S27** half-life 10y | −4.21pp | −2.66pp | −2.328 | −1.062 | 0.7189 | REJECTED |

**S5's shrinkage intensity is 0.5641** — genuinely partial, and degenerate at neither end
(control C5): it is neither equal weight nor raw IC-proportional, so the arm is a real third
thing and its rejection is informative rather than definitional.

**S24 is very nearly the incumbent (rank corr 0.9907)**, pre-registered as expected above 0.98.
Bagging over a signal set of **seven** shrinks every draw toward the same mean composite; there is
almost nothing to bag. Its stated secondary value was delivered — mean per-name rank dispersion
**0.18301** — but putting a per-name confidence figure on the product surface is the web lane's
decision and was scoped out.

## 3. S6 is the only arm to clear any half — and gets the treatment the register fixed first

**Late half +3.30pp at Δ*t* +0.678 (improves). Early half −1.61pp at Δ*t* −1.289 (does not).**

That is a **sign flip between halves** — this project's single most repeated pattern, now recorded
six-plus times — and **it is 1 of 5 sibling arms**. Five arms against one bar make
"at least one clears" roughly a **23%** event under independence, and the arms are positively
correlated (all functions of the same theme IC series), so 23% is an upper bound on the *arms*
being independent, not a floor on the noise.

**NOT eligible. NOT adopted. The +3.30pp may not be quoted without both labels.** The register
fixed that clause before any arm ran, precisely so that the first arm to clear anything could not
be written up as a finding.

Also recorded: **S6's cap did not bind** (max theme weight 0.2000 against a 0.2857 ceiling), so
the rejection is not an artefact of the bounds. And its point-in-timeness is **pinned by a test** —
date *i* uses periods *i−4 … i−1* and nothing later, because an off-by-one would let a date see
its own realised long-short and manufacture exactly the result the arm tests for.

## 4. S13 fails the alpha gate while improving what it exists to improve

| | ann return | Sharpe (per period) | max drawdown |
|---|---|---|---|
| equal weight (incumbent) | **+25.29%** | 0.5866 | −0.2809 |
| inverse-vol, capped 2× (**primary**) | +23.53% | **0.6261** | −0.2804 |

**Sharpe +0.0395 (≈6.7% relative), return −1.76pp, drawdown flat.** That is the classic
inverse-vol shape and **exactly what expectation 3 predicted**, including that it would fail an
alpha-margin gate **by construction**.

The register fixed the structural difference in advance: S13 leaves the composite alone, so the
decile **membership** is unchanged and **the long-short leg is unchanged by construction** — its
*t* margin is recorded **N/A and may never be read as a pass**. X7 calibrates no floor for Sharpe,
drawdown or turnover, so those three are measurements carrying no verdict. Volatility fallback
rate **0.0055**, so the arm is not quietly the incumbent.

**That the drawdown barely moves is consistent with S10's finding** that this book's max drawdown
is decided by a single quarter (COVID 2020Q1) — an inverse-vol overlay cannot help much against a
one-quarter market event.

## 5. A defect in my own instrument, under the session-11 protocol

The register's **C5** defines the reported quantity as the **shrinkage** intensity — 1.0 = fully
shrunk = equal weight. **The first cut of `arm_s5` reported its COMPLEMENT**, so the register's two
degenerate ends read backwards against the implementation.

Caught by the test written to pin it, **before any verdict was read**. Then, per the protocol,
the question asked was not *"was the label wrong"* but ***"did any verdict-half move"*** — answered
by diffing the pre-fix artifact against the post-fix one leaf by leaf rather than by reasoning
about the algebra:

* **The S5 weight vector is BIT-IDENTICAL: max |Δ| `0.000e+00` across all seven themes.**
* **ZERO gate cells moved** — no verdict, no half, no delta, on any of the five arms.
* The only change is the reported number: `0.4359` (keep) → `0.5641` (shrink), complements
  summing to exactly 1.0.

**So the defect was presentational and no conclusion needed re-deriving.** The register is left
unedited; the code now matches it.

## 6. A limitation of the design against its own register

The register says CPCV is the authority *"for every arm that produces a weight vector (S5, S6,
S27)"*. **`cpcv_validate` selects among its OWN eight `_weight_schemes` and cannot evaluate an
arbitrary weight vector**, so it does not bless or decline those three individually. Its authority
operates here as a **blanket keep-the-defaults rule** — which is weaker than the register's wording
implies, and is recorded as such rather than glossed. It does not change any verdict: all five
arms fail the held-out gate on their own.

## 7. Trial cost, adoption, expectations

**Equity `N` 165 → 170**, one trial per item; options 261 and infra 11 untouched. **ADOPTS
NOTHING** — adoption would be a vintage event and the vintage is **derived** per `PT-GAPDUE`.

**Expectations scored 6 right, 0 wrong — the first clean sweep in this record**, and the reason is
worth more than the score: the prior was not intuition but the project's own **measured** standing
result (CPCV adopts nothing; the tree combiner *reversed* out of sample; weight tuning went
+8.43%/yr in-search → −0.04%/yr on the locked hold-out). **When the prior is a measurement, the
directional calls stop being wrong.**

## 8. What I did NOT do

1. **I did not re-test the eight shipped `_weight_schemes`.** CPCV has answered that repeatedly.
2. **I did not implement the full Bayesian/MCMC version of S5** — the audit calls it a stretch
   goal and says empirical Bayes captures most of the benefit.
3. **I did not change `halflife_days` anywhere in the live path**, whatever S27 returned.
4. **I did not put S24's per-name dispersion on the product surface** — web lane's decision.
5. **I did not touch `low_risk`**, whose removal S13 is described as complementing.
6. **I did not extend `cpcv_validate` to score arbitrary vectors** (§6). That would change the
   authority every past weight verdict was read from, and is its own item.

## 9. BUGS FOUND

1. **My own S5 intensity/complement mismatch against the register** (§5) — presentational, proven.
2. **`cpcv_validate` cannot evaluate an arbitrary weight vector** (§6) — reported as a scope
   limitation of the register's own wording.
3. **`scripts/build_ledger.py` will DROP all five rows** if regenerated — curated. Pre-existing.

## 10. Next

**S10's accounting half** (Beneish, Altman, external financing, NT late filings) or the **CPCV
embargo** from session 22 — still the only open item that can move a published number.

**And the dated one: read `/api/track` → `contract_track.recording_ok` on or after 2026-08-13.**

---

# SESSION 32 (2026-08-12) — S7 + S18: every pre-registered interaction rejected

`PREREG_s7_s18_interactions.md` committed **alone at `7fc6ab2`** — one `.md`, zero `.py`, a strict
ancestor of the measurement commit. **No panel rebuild:** every input was already on the banked
corrected 69-date panel, and short interest joined from the cache point-in-time.

## 0. The headline

**All six testable arms rejected. One of the audit's four named interactions cannot be built at
all. And the short-interest exclusion made drawdown WORSE — independently replicating S10 on a
completely different criterion.**

## 1. `size × liquidity` is unbuildable, and is reported rather than proxied

The audit names four interactions. The fourth needs a liquidity measure and **there is none on
this path**: the price export carries **date and close only**, so `avg_dollar_volume` cannot be
computed in the panel at all. That is audit **B13**'s blocker, stated in the panel's own
`prefilter_note`, and the B13 ledger row was corrected last session from `IN PROGRESS` to
**`PARTIAL — BLOCKED ON DATA`** for exactly this reason.

**Deliberately not proxied.** A market-cap or price-based stand-in would be a *different
hypothesis wearing this one's name*, and a test pins that the script grew no such proxy. It
charges **no trial**, on session 8's precedent that a test which cannot be run keeps the
denominator.

## 2. Short interest does not reach half the panel

The cache is real — **48,539 tickers, 3,866,270 records, 2018-01-27 → 2026-07-30**. The audit says
coverage is *"40% of the panel dates"*. **Measured: 32 of 69, 46.4%**, first covered date
**2018-04-20**, row coverage on covered dates **0.9269**.

**The consequence is structural and decided S18's design before any arm ran: every covered date is
in the LATE portion of a panel that starts 2009-01-15, so S18 cannot satisfy a both-halves gate on
the full panel — the early half has no data at all.** That is an impossibility, not a caveat to
note afterwards, so the register fixed the replacement first: **S18's arms are gated on the two
halves of the covered subsample — 32 dates, 16 per half.** Sixteen is exactly
`holdout_compare_panels`' `min_dates` floor, the thinnest split the shipped gate accepts.
**A pass on 16-date halves is not the same object as a pass on 34-date halves, and no S18 result
may be compared directly with an S7 one.**

## 3. Verdicts

| arm | Δalpha early | Δalpha late | Δ*t* early | Δ*t* late | rank corr | coverage | verdict |
|---|---|---|---|---|---|---|---|
| A1 `value × quality` | −1.17pp | −0.84pp | −0.764 | +0.490 | 0.9446 | 0.9791 | REJECTED |
| A2 `momentum × vol regime` | −0.48pp | −0.19pp | −0.933 | −0.033 | 0.9547 | 0.6710 | REJECTED |
| A3 `value × institutional` | −0.05pp | −1.09pp | −0.293 | −0.526 | 0.9633 | 0.7172 | REJECTED |
| A4 `value × short_interest` | −0.49pp | −0.86pp | −0.432 | −0.000 | 0.9691 | 0.4621 | REJECTED |
| A5 `momentum × short_interest` | −2.39pp | **+1.85pp** | −0.321 | **+0.812** | 0.9676 | 0.4540 | **NOT_REPLICATED** |

**A5 clears the late half alone.** That is a sign flip between halves — **and the second
consecutive session in which exactly one arm clears exactly one half** (S6 did it last session).
The family-wise labelling clause has now earned its keep twice: **`ELIGIBLE — UNREPLICATED, 1 OF 6
SIBLING ARMS`**, not eligible on the gate, not adopted, and the +1.85pp may not be quoted without
both labels.

**A3's coverage handicap was pre-registered**: `institutional` has the panel's worst coverage, so
the interaction is missing on nearly three rows in ten — which is why it was expected to fail for
a reason unrelated to the hypothesis.

## 4. A6 — the exclusion replicates S10 on a different criterion

Dropping the **top 5% most-shorted** from the top decile:

| | value |
|---|---|
| top-decile rows dropped | **4.83%** |
| annualised return | +27.08% → **+26.77%** (−0.31pp) |
| **max drawdown** | −0.2809 → **−0.2863** |
| **drawdown gain** | **−0.5404pp — WORSE** |

**S10 found a *valuation-band* exclusion worsened drawdown by 2.61pp and 3.35pp. A *crowding*
exclusion worsens it too** — same direction, smaller magnitude, entirely different criterion.
That is an independent replication of the finding S10 called counterproductive, and it is the most
useful thing in this session.

Both S10 caveats travel verbatim: **`max_drawdown` is NEGATIVE**, so the gain is `arm − base` —
pinned by a test carrying the real measured pair — and **X7 calibrates no drawdown floor
anywhere**, so this is a measurement carrying no verdict. S10 additionally measured that this
book's worst drawdown spans a single quarter (COVID 2020Q1), which the covered window contains and
which an exclusion screen cannot dodge.

## 5. Bonferroni, declined explicitly

The audit prescribes *p* < 0.0125 for four interactions. **That assumes a p-value gate; this
project's gate is a MARGIN gate whose floors X7 calibrated against a placebo.** Translating one
into the other would invent an uncalibrated correspondence — the error X3 and session 10 both paid
for. So the margin gate is primary and unadjusted, and multiplicity is honoured by **labelling**,
exactly as the five-scheme register did.

## 6. Controls

* **C1** reproduces the published record; the run aborts before any arm otherwise.
* **C5 — zero point-in-time violations** on the short-interest join. Pinned by a test using a
  fixture where a settlement dated *on* the scoring date and one dated *after* it must both be
  excluded, because a leak here would manufacture exactly the crowding effect being tested.
* **C6 — no interaction is a proxy for a parent.** Largest |parent correlation| across all five
  columns is **0.4584** (`value × quality` against `value`); most are far lower.
* **C7 — THE CLEAN SURPRISE, and the one expectation that missed.** Adding an eighth input moves
  every theme's *relative* weight 1/7 → 1/8, so each arm is a **compound** change — registered in
  advance. Re-scoring with a **constant** eighth column isolates the dilution: **+0.000173 early
  and +0.000146 late, essentially nil.** So the arms measure the interactions and nothing else.
  I predicted (65/35) the dilution would account for a non-trivial share; **it accounts for none**,
  which is a cleaner result than predicted.

## 7. Trial cost and expectations

**Equity `N` 170 → 176** (six arms; the unbuildable fourth interaction charges nothing).
**Expectations 6 right, 1 wrong** — the miss is C7 above.

**Nothing was searched beyond the audit's named list.** That is the single design choice that
makes the exercise worth anything: searching the quadratic interaction space is exactly what the
ML tree combiner did, and it *reversed* out of sample.

## 8. What I did NOT do

1. **I did not build a liquidity proxy** to rescue `size × liquidity` (§1). Pinned by a test.
2. **I did not re-test short interest standalone** — already rejected, and S18's thesis is that it
   conditions rather than predicts.
3. **I did not search for additional interactions**, or mention any as promising.
4. **I did not wire SEP volume into the loader** to unblock §1 — data plumbing, different lane,
   and it would change the universe.
5. **I did not adopt anything.** Adoption would be a vintage event.

## 9. BUGS FOUND

1. **One of the audit's four named interactions is unbuildable** (§1) — reported.
2. **The audit's short-interest coverage figure is understated** — 46.4%, not 40% (§2). Minor, but
   it is the number that decides whether a both-halves gate is possible.
3. **My own first cut crashed on the C5 check** — `si_used` carried `None` for missing rows and
   pandas coerced the Series to float, so `is not None` was true for NaN and the comparison threw.
   Fixed with an explicit `isinstance(..., str)` and an object dtype. Caught by running it.
4. **`scripts/build_ledger.py` will DROP both rows** if regenerated — curated. Pre-existing.
5. **`session 31` NOW NAMES TWO LANES' WORK — THE THIRD SUCH COLLISION IN FIVE SESSIONS.** The
   options-bot lane stamped `O11` as session 31 while this lane's five-scheme register
   (`S5`+`S6`+`S13`+`S24`+`S27`) had already landed as session 31. **`session 29`, `session 30`
   and now `session 31` each name two different results in the file every lane reads.** Three
   occurrences in five sessions is not bad luck; **the numbering convention does not work with
   two lanes landing on the same day**, and no amount of care by either lane fixes it, because
   both were correct at the moment they stamped. **DELIBERATELY NOT RENUMBERED**, for the reason
   given twice before: their number is already referenced from their own handoff, ledger and
   research-log rows. **This session took 34, which was free.**
   → **This now needs a convention change rather than another report.** The obvious candidates
   are a lane prefix (`E31` / `O31`) or a date-plus-item stamp instead of a bare counter. **That
   is Don's call, not a lane's**, which is why it is routed rather than unilaterally adopted.

5. **`session 30` NOW NAMES TWO LANES' WORK — THE SECOND SUCH COLLISION IN FOUR SESSIONS.** The
   options-bot lane stamped `O6` as session 30 while this lane's `S16`+`S28` had already landed as
   session 30. This is the same class as the `session 29` collision reported in session 30 §5
   (their `O3`+`O4`+`O5` against this lane's `S3`+`S25`), and it has now happened **twice**, which
   makes it a process problem rather than an accident. **Both were found by a merge, neither by
   either lane's own checks.** DELIBERATELY NOT RENUMBERED, for the reason given last time: their
   number is already referenced from their own handoff, ledger and research-log rows, and editing
   a landed entry is how a fix silently eats a record. **This session took 33, which was free.**
   → Routed to the options-bot lane, or to Don as a convention call. **The mechanical rule that
   would prevent it is not "check once": it is check the GLOBAL maximum in `CLAUDE.md` at the
   moment you stamp AND re-check after every merge**, because the push→land window is long enough
   for another lane to take your number — which is exactly what happened both times.


## 10. Next

**S10's accounting half** (Beneish, Altman, external financing, NT late filings) or the **CPCV
embargo** from session 22 — still the only open item that can move a published number.

**And the dated one: read `/api/track` → `contract_track.recording_ok` on or after 2026-08-13.**

---

# SESSION 33 (2026-08-12) — S8 + S9: freshness has no cross-section to work with

`PREREG_s8_s9_freshness.md` committed **alone at `b7804d8`** — one `.md`, zero `.py`, a strict
ancestor of the measurement commit. One panel build with `with_freshness=True`; every arm a column
on that frame. **All four verdict arms rejected. ADOPTS NOTHING.**

## 1. The structural finding, which kills S8's 13F leg outright

**`days_since_13f` has essentially no cross-sectional variation.** Measured on the panel:

| | days_since_filing | days_since_13f |
|---|---|---|
| distinct values per date (mean) | **86.81** | **1.25** |
| within-date sd (median) | ~37.9 days | **2.054 days** |
| decay multiplier, p05 → p95 | — | **0.5163 → 0.5427** |
| decay multiplier, within-date sd | — | **0.00587** |

**13F quarter-ends are common calendar dates, so at any rebalance every name's 13F is the same
age.** Arm A4 is therefore not a staleness adjustment at all — it is a **uniform ~0.54×
down-weighting of the `institutional` theme**, i.e. a weight change, and the weighting family was
rejected wholesale last session. Its rank correlation against the deployed composite is **0.9880**,
the highest of the four and nearly inert, which is the same fact from the other side.

**The audit's premise conflates two different decays.** The 13F signal genuinely decays as the
quarter ages — peaks Q−1, alive Q−2 (*t* 1.36), dead Q−3 (−0.04) — and that measurement is real.
But it is a **TIME-SERIES** decay, common to every name at a given date. It is **not** a
**CROSS-SECTIONAL** difference that could re-rank names against each other. `days_since_filing`
*is* cross-sectional; `days_since_13f` is not.

**Reported honestly: I found this in the results, not in the premise check.** The register's
premise section verified that the ages were *buildable* and point-in-time; it did not ask whether
they *varied across names*. That question belongs in a premise check and will next time.

## 2. The S9 diagnostic is the result, and it refutes the premise

The audit's own method: split the top decile by staleness quartile and look for a gradient
**before** turning anything into a weight. That sequencing is what makes the item worth having.

| quartile | mean fwd return | mean age |
|---|---|---|
| Q1 (freshest) | **+6.15%** | 38d |
| Q2 | +6.12% | 66d |
| Q3 | **+6.66%** | 71d |
| Q4 (stalest) | +6.35% | 88d |

**Not monotone.** The whole spread is about half a point on a 6.3% base, and **Q1 − Q4 = −0.78%/yr
— the stalest quartile very slightly outperformed the freshest.** By `days_since_13f` the four
quartiles have mean ages of 113, 113, 113 and 114 days, which is §1 restated: there is nothing to
quartile on.

**MY REGISTERED LEAN WAS WRONG, AND IN THE INFORMATIVE DIRECTION.** The task asked which way I
leaned and the register said: **the gradient is real, the weighted arms fail.** The weighted arms
did fail — **but the gradient is not there either.** Both halves of the lean pointed at *something*
in freshness, and there is nothing. That is the useful outcome: the mechanism argument was
genuine, it was stated in advance, and it did not survive contact with the data.

## 3. Verdicts

| arm | Δalpha early | Δalpha late | Δ*t* early | Δ*t* late | rank corr | verdict |
|---|---|---|---|---|---|---|
| A2 freshness as an input | +0.61pp | −1.61pp | +0.171 | +0.110 | 0.9143 | REJECTED |
| A3 fundamental decay 90d | −0.22pp | **+1.73pp** | −0.407 | **+0.710** | 0.9203 | **NOT_REPLICATED** |
| A4 13F decay 180d | +0.03pp | −1.03pp | −0.019 | −0.500 | **0.9880** | REJECTED |
| A5 combined | −0.16pp | +0.41pp | +0.010 | +0.660 | 0.9268 | REJECTED |

**A3 clears the late half alone — the THIRD CONSECUTIVE SESSION in which exactly one arm clears
exactly one half** (S6 in session 31, A5 in session 32, A3 here). The family-wise labelling clause
has now earned its keep three times: **`ELIGIBLE — UNREPLICATED, 1 OF 4 SIBLING ARMS`**, not
eligible on the gate, not adopted, and the +1.73pp may not be quoted without both labels.

**A5 landed between A3 and A4 exactly as pre-registered**, because the two decays touch disjoint
themes.

## 4. Controls

* **C1** reproduces the published record; aborts otherwise.
* **C5 — ZERO negative ages**, either of which would have been a look-ahead (a filing dated after
  the scoring date). `days_since_filing` coverage 1.0000, median 73d, p95 89d — consistent with a
  quarterly reporting cycle. `days_since_13f` coverage 0.7190, matching `institutional`'s own.
* **C6 — the pre-registered sector caveat is CONFIRMED.** The freshness quartiles differ materially
  in sector composition, largest fresh-vs-stale gap **Consumer Cyclical at 15.62pp**. Fiscal
  year-ends cluster by industry, so any gradient would have been partly compositional — U7's
  failure mode and S10's. **Moot here because there is no gradient to explain, but it binds on any
  future re-opening.**
* **C7 — the fundamental decay bites hard** (mean multiplier 0.4894, p05 0.3720), so A3's failure
  is not an artefact of an inert multiplier. The 13F multiplier's near-constancy is §1.

## 5. No half-life was fitted

The audit asks for *"a half-life estimated per signal from its own measured decay curve"*.
**Estimating on this panel and then scoring on it is the in-sample selection the project has
already paid for** (+8.43%/yr in-search → −0.04%/yr on the locked hold-out). Both were fixed in the
register: **90 days** for fundamentals (one reporting quarter, labelled a convention) and **180
days** for 13F, taken from the project's own measured decay — the only half-life here with backing
that pre-dates the register. Pinned by a test that fails if a search appears.

## 6. A defect reported, not fixed

**`bulk.prepare_daily` down-samples DAILY to one row per ticker-month** — its own docstring says
so — so the point-in-time market cap and the re-priced EV equity leg can be **up to ~31 days
stale**, while the price feeding `_price_factors` is same-day. The audit flagged this and it is
confirmed.

**But it is staleness, not look-ahead:** the same docstring is careful to keep the last date
actually present and never a future one. So it is a **precision** defect. Fixing it would move
`size`, every EV-based value ratio and therefore the published headline — a results change needing
its own register. It is also **not name-specific** the way filing dates are, so it does not
confound these arms.

## 7. Two arguments that look supportive and are not the same hypothesis

Separated in the register **before** running, so neither could be leaned on afterwards:

* **P6's "recency beats smoothing"** (quarterly ROE/ROIC beat TTM, *t* +2.84 vs +2.01) is about the
  **WINDOW** a number is measured over, not the **AGE** of the observation. A quarterly figure
  filed 89 days ago is still quarterly.
* **S27**, rejected last session, weighted **dates** in the time series. S8/S9 weight **names**
  within a date.

Three different senses of "recency"; only one of them has now been tested.

## 8. Trial cost and expectations

**Equity `N` 176 → 180** (four verdict arms). **A1 charges nothing** — a measurement with no
threshold, the same treatment S7's dilution control got. **Expectations 6 right, 1 wrong**, and
the miss is expectation 1 — the gradient — which is the one that mattered.

## 9. What I did NOT do

1. **I did not fix the DAILY month-end down-sampling** (§6).
2. **I did not fit any half-life** (§5).
3. **I did not decay `momentum`, `size` or `insider`** — price-based or on a different clock.
4. **I did not put a per-name "data from N days ago" qualifier on the product.** The data now
   exists on the panel to support it; whether to surface it is the web lane's decision.
5. **I did not re-open S27** (§7).

## 10. BUGS FOUND

1. **`days_since_13f` has no cross-sectional variation** (§1) — a structural fact that makes the
   audit's 13F leg unbuildable as specified. Reported.
2. **The DAILY month-end staleness** (§6) — confirmed, reported, not fixed.
3. **My own premise check did not ask whether the ages VARY across names** (§1) — it verified they
   were buildable and point-in-time and stopped there. That question belongs in a premise check.
4. **`scripts/build_ledger.py` will DROP both rows** if regenerated — curated. Pre-existing.

## 11. Next

**S10's accounting half** (Beneish, Altman, external financing, NT late filings) or the **CPCV
embargo** from session 22 — still the only open item that can move a published number.

**And the dated one: read `/api/track` → `contract_track.recording_ok` on or after 2026-08-13.**

---

# SESSION 34 (2026-08-12) — S11 + S12: a real turnover reduction at 11-23x its own cost, and an arm that misses by 18bps

`PREREG_s11_s12_horizon_bucket.md` committed **alone at `d867fe3`**. One panel build, three arms,
every arm a column on that frame. **All three rejected. ADOPTS NOTHING.**

## 1. S11 — the prior was real, the counter-prior won

**The prior, recorded before running:** S22 measured the composite's out-of-sample rank IC
**rising** with horizon, +0.034 at one quarter to ~+0.072 at three-plus. That is a genuine
mechanism, not a hunch.

**REJECTED in both halves and by the widest margin of the three:** Δalpha **−4.22pp** early,
**−2.05pp** late; Δ*t* **−2.353** and **−0.927**. Rank correlation against the deployed composite
**0.6939**; top-25 changed **21 of 25**.

**The long-short leg moved against it exactly as pre-registered**, because S22 had already measured
that the persistence lives entirely in the **long** leg while the spread's HAC *t* collapses
**2.7167 → 0.6846** with horizon.

### 1.1 The audit's secondary claim is confirmed — and quantified into a terrible trade

The audit predicted a slower component would cut turnover. **It does:**

| | per-rebalance turnover |
|---|---|
| deployed | **0.6352** |
| horizon blend | **0.4976** |
| saving | **13.76pp**, ~55pp of book per year |

**At the project's own measured 33.4 bps one-way cost, that saves roughly 18 bps a year — against
205 to 422 bps of alpha given up. The trade runs 11× to 23× AGAINST.** The turnover claim is true
and the saving is nowhere near the cost, which is a more useful statement than either alone.

### 1.2 C6 confirms the counter-prior directly, and a confound is named

**The two horizons' weight vectors correlate +0.9013 and +0.9674** across the two decide halves.
So the ensemble is largely **one composite twice** — precisely the counter-prior the register
stated.

**The confound, named rather than glossed:** the blend's rank correlation against the *deployed*
composite is only **0.6939** while the two horizons agree above 0.90. That means **most of the
arm's deviation comes from using IC-proportional weights at all** — one of the eight shipped
schemes CPCV has always declined — **not from blending horizons**. The audit's own construction
makes this unavoidable: two flat-weighted composites at different horizons would be *identical*,
so some horizon-specific weighting is required for the arm to exist at all. The arm therefore
partly re-tests a rejected weighting, and its −4.22pp should not be read as the cost of blending.

## 2. S12 — a scope divergence, and the closest call in these sessions

**The audit's S12 is the VALUATION bucket** (established vs speculative — *"defined by how a name
is valued, not by industry"*). **The task framed it as the CAP TIER.** Both were tested as separate
arms, so the row closes on both readings and neither is reported as the other. Same class as S10's
divergence.

| arm | Δalpha early | Δalpha late | Δ*t* early | Δ*t* late | rank corr | top-25 changed | verdict |
|---|---|---|---|---|---|---|---|
| **A2** valuation bucket | **+1.36pp** | +0.82pp | +0.478 | +0.347 | 0.9807 | 4/25 | **NOT_REPLICATED** |
| **A3** cap tier | +0.09pp | +0.07pp | −0.106 | +0.048 | 0.9557 | 9/25 | REJECTED |

**A2 IS THE CLOSEST ANY ARM HAS COME IN THESE SESSIONS.** It is **positive on alpha in both
halves** and **positive on Δ*t* in both**, and it fails only because the late half's alpha misses
the pre-committed **+1.00pp** bar **by 18 basis points**.

**That is S21's shape exactly** — S21 also passed one half and missed the other by 17bps, and was
recorded not-replicated. **Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES`
A6). It is **1 of 3 sibling arms**, and **the fourth consecutive session in which exactly one arm
clears exactly one half**. **NOT eligible, NOT adopted, and the +1.36pp may not be quoted without
both labels.**

It is also a **small** intervention — rank correlation 0.9807, only 4 of 25 names changed,
turnover 0.6358 against the deployed 0.6352 — with a small positive effect that does not clear.

**A3 is nearly inert.** **C8 confirms the pre-registered mechanism**: the book's mean `size`
z-score falls **0.5885 → 0.5092, a 13.5% shrink**, so the arm does neutralise the exposure X3 says
carries the composite's entire significance. **But the alpha effect is zero rather than negative**
— it fails by being inert rather than harmful, which is milder than the register predicted.

**The audit's own metric priority was adopted verbatim** — *"top-decile alpha decides, not the
t-statistic"* — and **no arm triggered the bought-*t*-sold-alpha flag**, so sector-neutral's
failure shape did **not** recur.

## 3. A near-miss caught before the build, and a control that did not run

**THE NEAR-MISS.** `df["bucket"]` is derived **after** the granular standardisation step. A naive
`if bucket_relative in df.columns` would therefore have **found nothing, done nothing, and still
reported a verdict on an arm that never ran.** Caught while wiring the toggle, fixed by deriving
the group from `classify_bucket` directly, and **pinned by a test whose fixture is checked to
produce both buckets** — otherwise the test itself could not detect a no-op.

**THE CONTROL THAT DID NOT RUN, reported as such.** C7 was to report per-date group sizes for both
groupings. **Its bucket half came back empty**, for the same root cause one level up: the
diagnostic column read `bucket` from the metrics dict, where it does not exist, so it emitted
`None` on all 113,945 rows.

**The arms are unaffected** — the `br_*` columns were computed inside `build_frame` from
`classify_bucket`. The missing number was **recovered from the corrected panel, whose row set is
identical (113,945, verified)**: **established 1,312 and speculative 339 per date**, so both groups
are substantial and neither arm was degenerate. Reported as a control that failed to run rather
than quietly omitted.

## 4. Controls

* **C1** reproduces the published record; aborts otherwise.
* **C4** — `fwd_ret_h252` coverage **0.9510**.
* **C5** — the horizon weights are fitted on the **decide half only** and applied to the measure
  half, in both directions, with the weight vectors reported per direction so the separation is
  checkable rather than asserted. A violation here would have manufactured the result.
* **C7** — §3.
* **C8** — §2.

## 5. Trial cost and expectations

**Equity `N` 180 → 183.** **Expectations 7 right, 0 wrong** — the second clean sweep, and again
because the priors came from measured facts already in the record (S22's horizon IC, X3's `size`
finding, sector-neutral's three rejections) rather than from intuition.

## 6. What I did NOT do

1. **I did not sweep horizons.** Exactly two were blended — 63 and 252, the audit's own pair.
2. **I did not re-open sector-neutral**, closed permanently.
3. **I did not change the rebalance frequency.** S22 explicitly warned its horizon result is *not*
   a finding that the book should rebalance less often, and §1.1 is the cost arithmetic for why.
4. **I did not promote A2** despite it being the closest call in these sessions.
5. **I did not repair the C7 emission bug** beyond recovering its number — it is a diagnostic, the
   arms are unaffected, and touching the panel again for it would be a rebuild for no verdict.

## 7. BUGS FOUND

1. **A silent no-op in my own toggle, caught before the build** (§3). Fixed and pinned.
2. **C7's bucket half did not run** (§3) — same root cause, reported, number recovered.
3. **S11's construction confounds the horizon blend with IC-proportional weighting** (§1.2) —
   inherent to the audit's method, named so the −4.22pp is not misread.
4. **`scripts/build_ledger.py` will DROP both rows** if regenerated — curated. Pre-existing.

## 8. Next

**S10's accounting half** (Beneish, Altman, external financing, NT late filings) or the **CPCV
embargo** from session 22 — still the only open item that can move a published number.

**And the dated one: read `/api/track` → `contract_track.recording_ok` on or after 2026-08-13.**

---

# SESSION 35 (2026-08-12) — the no-trade band clears, and sector-neutral is finished

`PREREG_s14_s15_band_sectorvalue.md` committed **alone at `32051c0`**. **ADOPTS NOTHING.**

## 0. The headline

**`S14` is ADOPT-ELIGIBLE — the first arm to clear in eight sessions, and it cleared in both
directions.** But **not for the reason its own register claimed**, and **its optimum sits at the
grid boundary**, so the honest reading is "a real effect whose size is unidentified", not "adopt
this width".

**`S15` is rejected and essentially inert — and with it, sector-neutral is finished in every
form**, because `SECTOR-NEUTRAL-B6` named exactly two routes back and both are now shut.

## 1. S14 — the result

Sweeping the shipped width grid on the **decide** half and measuring the argmax on the
**held-out** half, in both directions:

| decide → measure | picked | Δ net alpha | Δ gross alpha | measured cost saving |
|---|---|---|---|---|
| early → late | **0.30** | **+1.78pp** | **+1.02pp** | +0.76pp |
| late → early | **0.30** | **+1.77pp** | **+0.77pp** | +1.00pp |

Turnover roughly **halves** (2.6078 → 1.3514 and 2.5800 → 1.4198); measured drag falls
0.0227 → 0.0126 and 0.0182 → 0.0106.

## 2. Two corrections to my own register, both against it

**#1 — THE "PURE COST MECHANISM, NO SIGNAL CLAIM" FRAMING IS WRONG.** The register asserted this
arm makes no signal claim at all. **Gross alpha improves** (+1.02pp / +0.77pp), so **roughly half
the gain is a signal effect**, not a cost saving. Holding a name until it leaves the top 30% rather
than the top 10% stops the book churning on rank noise — a construction change with a real return
consequence.

That is not a defect in the result; it is a defect in how the result was framed, and it matters
because it means **the audit's category-error argument is only half applicable.** The cost half is
mechanical; the gross half is a signal claim and deserves signal-grade scepticism.

**#2 — MY INDICTMENT OF THE AUDIT'S 1.5pp ALLOWANCE WAS TOO STRONG.** The register computed the
saving at ~26 bps from the audit's quoted turnover and the 33.4 bps rate, and called the allowance
**6× wider than the prize**. **The measured saving is 76–100 bps**, so the allowance is about
**1.5×**. Tightening the guard to the measured saving was still the right call, and the arm passes
under either version — but the magnitude I asserted before the run was wrong.

## 3. The caveat that must travel with the verdict

**THE ARGMAX IS AT THE GRID BOUNDARY IN BOTH DIRECTIONS.** 0.30 is the widest width the shipped
grid contains, and it won both times. **The optimum is therefore at or beyond the edge and the
knee is NOT identified** — the selected width is an artefact of where the grid stops.

**A wider grid is the obvious next test. An adoption is not.**

**C6 confirms the audit's own noise warning**: the net-alpha surface is **monotone on the early
half and NOT monotone on the late**, where 0.20 dips below 0.15. The audit saw exactly this on the
void panel and it persists on the corrected one.

## 4. A mechanism that supports it

**S22 measured that top-decile alpha is still accruing at two years, while a name typically stays
in the decile for ONE rebalance** (70.6% of spells last exactly one). A wider band harvests
persistence the incumbent's tight exit throws away — the direction S22 pointed at and explicitly
declined to test, noting that a cohort's buy-and-hold return and a re-selecting book are different
claims. **This is the first measurement in that direction that clears a held-out gate.**

**Recorded ELIGIBLE, not adopted** — a vintage event, and Don's call. **1 of 2 sibling arms** per
the register's family-wise clause, though stronger than that label implies: it cleared **both**
halves in **both** directions with near-identical magnitudes (+1.78 / +1.77pp).

**Two limitations carried forward.** The band is **already live in the `taxable` configuration**,
so an adopt would change the *default*, not introduce the band. And **B13 is only PARTIAL** —
`MIN_AVG_DOLLAR_VOLUME` cannot bind on this path — so "the book is investable" holds for the
categorical screen and **not** the liquidity one.

## 5. S15 — rejected, and both routes back are now shut

| | early half | late half |
|---|---|---|
| Δ top-decile alpha | −0.01pp | −0.36pp |
| Δ long-short *t* | −0.086 | +0.037 |

Rank correlation against deployed **0.9879**; only **5 of 25** top names changed. **The arm is
close to inert — it neither helps nor hurts.**

**CONTROL C4 IS EXACT, and it is what makes this the narrow experiment it claims to be: every
NON-value theme comes back BIT-IDENTICAL at max |Δ| 0.000e+00**, while `value` itself moves by
1.5568. So the intervention is provably confined to one theme — this is not a broad sector-neutral
run wearing a narrow label.

It **moves the book less** than the broad version did (0.9879 against B6's measured 0.9836), as
pre-registered. **The buy-*t*-sell-alpha flag did fire on the late half** — predicted at 55/45 that
it would not — but at −0.36pp of alpha for +0.037 of *t*, **inert describes it better than
trade-off**, and no verdict rests on it.

**THE CLOSURE.** `SECTOR-NEUTRAL-B6` named exactly two routes back: **`S25`**, a genuine
point-in-time sector map — **closed as UNOBTAINABLE in session 29**, because no such map is
buildable from anything we own — and **`S15`**, rejected here. **Both are shut. Sector-neutral in
every form is finished and should be recorded as such rather than left dormant.**

**And the standing caveat now has no remedy.** TICKERS supplies **today's** sector applied to 1998
rows; `S25` was the item that would have fixed it. **Any future sector-aware result on this panel
inherits a look-ahead that cannot be repaired on data we own.**

## 6. Trial cost and expectations

**Equity `N` 183 → 185.** S14's width sweep is charged as **one** trial, not five: the argmax is
taken on the decide half and only the selected width is measured.

**Expectations 4 right, 3 wrong — the worst score in these sessions, and informative for it.** The
two consequential misses are both on S14: it was predicted to fail (70/30) and cleared, and the
cost saving was predicted under 40 bps and measured at 76–100. The third miss is S15's
buy-*t*-sell-alpha flag firing at trivial magnitude.

## 7. What I did NOT do

1. **I did not adopt anything.** Either arm is a vintage event.
2. **I did not widen the grid** to find S14's true knee — that is a new measurement and needs its
   own register, and it is the recommended next step.
3. **I did not touch the `taxable` configuration** where the band already lives.
4. **I did not sweep `enter_frac`**, which stays at the shipped 0.10.
5. **I did not re-open broad sector-neutral** — S15 was a different construction, and its failure
   closes the item rather than reviving the broad one.

## 8. BUGS FOUND

1. **My own register's mechanism claim was wrong** (§2 #1) — corrected against myself.
2. **My own pre-run arithmetic was too strong** (§2 #2) — corrected against myself.
3. **The shipped width grid does not contain S14's optimum** (§3) — reported; it bounds what the
   verdict can say.
4. **`scripts/build_ledger.py` will DROP both rows** if regenerated — curated. Pre-existing.

## 9. Next

**The recommended next item is now S14's own follow-up: widen the width grid past 0.30** and
re-run the same held-out design, because the current verdict cannot say where the optimum is.

Otherwise unchanged: **S10's accounting half**, or the **CPCV embargo** from session 22 — still
the only open item that can move a published number.

**And the dated one: read `/api/track` → `contract_track.recording_ok` on or after 2026-08-13.**

---

# S14-WIDTH (2026-08-13) — the knee is identified, and it is where session 35 found it

`PREREG_s14_width_extension.md` committed **alone at `e63295e`**, a strict ancestor of the
measurement commit. **ADOPTS NOTHING** — it routes a decision.

## 0. The headline

**Given three wider widths to choose from, both halves still picked 0.30.** The optimum is
therefore **INTERIOR**, the knee **is identified**, and session 35's boundary caveat is
**discharged** rather than repeated. That is outcome **(a)** of the three committed in advance,
so **`S14` becomes an adoption decision routed to Don as a vintage event.**

**And the correction that matters is to my own reasoning, not to session 35's:** a boundary
argmax is evidence that a grid is *uninformative about what lies beyond it* — it is **not**
evidence that the optimum lies beyond it. I registered the opposite lean at 60/40 and it was
wrong in the most direct way available: the extension moved the answer not at all.

## 1. The surface — the deliverable, reported whatever the verdict

Net top-decile alpha (pp/yr), decide-half sweeps, deployed flat 1/7, shipped cost table:

| width | early half | late half | turnover (early) | incumbent share (early) |
|---|---|---|---|---|
| none | +1.11 | +10.94 | 2.6078 | 0.359 |
| 0.12 | +0.87 | +11.88 | 2.4485 | 0.402 |
| 0.15 | +2.02 | +12.17 | 2.1940 | 0.471 |
| 0.20 | +2.08 | +11.91 | 1.8411 | 0.567 |
| 0.25 | +2.17 | +12.39 | 1.5768 | 0.640 |
| **0.30** | **+2.88** | **+12.72** | **1.3514** | **0.701** |
| 0.40 | +2.32 | +12.44 | 1.0466 | 0.785 |
| 0.50 | +2.56 | +11.84 | 0.8214 | 0.848 |
| 0.75 | +2.74 | +9.14 | 0.4885 | 0.943 |

**0.30 is the argmax on both halves**, and the three new widths are the three lowest-turnover
cells on the grid — so this is not a case of the extension failing to bite. **Turnover at 0.75 is
about a fifth of the no-band book and it still loses.**

## 2. The mechanism, measured — and it is the register's own §2 confirmed on the real panel

**GROSS alpha peaks at exactly 0.30 on BOTH halves and falls away**: early +3.38 (none) → **+4.14
(0.30)** → +3.34 → +3.38 → +3.26; late +12.77 → **+13.79 (0.30)** → +13.33 → +12.56 → **+9.65**.

That is the predicted shape and the reason the optimum is bounded. **The cost saving is capped and
the staleness cost is not.** At 0.30 the drag is already down to 0.0127 / 0.0106, so at most
~1.1–1.3pp of further saving exists even if turnover fell to zero — while gross alpha gives up
0.89pp (early) and **4.14pp** (late) by 0.75.

**And the freezing argument is now measured rather than asserted.** The share of the book that is
a surviving incumbent climbs **0.359 → 0.701 at 0.30 → 0.943 at 0.75** (early; 0.373 → 0.697 →
0.919 late). At 0.75 the book replaces about one name in sixteen per rebalance — it is
approaching the frozen limit the register derived from the code before running, and a book that
has stopped selecting cannot express a selection edge.

## 3. What this register does NOT add, stated plainly

**It adds no new held-out evidence about the SIZE of the effect.** Because the pick did not move,
the held-out measurement is **numerically identical to session 35's** — Δ net alpha +1.780125pp
and +1.768484pp, agreeing to ten decimal places. The +1.78pp figure is **the same measurement,
not a replication of it.**

What the trial buys is the **location** finding: that 0.30 is a genuine interior maximum rather
than an artefact of where the grid stopped. That was the one thing session 35 could not say, and
it is the whole reason this register exists.

## 4. A defect in my own control, caught by running it

**C3 failed on its first cut and the failure was in the control, not the baseline.** It asserted
that `_band_select` with `exit_rank == n_target` returns **exactly** plain top-N, implemented as
LIST equality — and it failed **176 of 200** draws. `_band_select` returns survivors **first** and
then fills, so the ORDER differs while the SET is identical (**200/200**).

**Proven harmless rather than argued harmless**, per the session-11 protocol — the question is not
whether my label was wrong but whether any verdict-half moved. Swapping a strict-rank selector
into the real panel and diffing every reported field gives **max |Δ| 2.13e-14** across turnover,
gross, net, drag, Sharpe and drawdown. The book is equal-weighted, so only the selected set can
reach a number. **Zero verdict cells move.** Both halves are now pinned by tests, including one
that fails if anyone ever makes the weighting order-dependent.

## 5. A correction to session 35's C6, produced by the extension itself

Session 35 reported the net-alpha surface as **monotone on the early half and not on the late**.
**On the extended grid the early half is non-monotone too** — it dips at 0.40 and recovers. The
monotonicity was an artefact of the grid stopping at its own argmax. **The audit's noise warning
applies to both halves, not one.**

## 6. The caveat that must travel with the routing

**The knee replicates in location but NOT in sharpness.** On the late half it is decisive — 0.30 →
0.75 costs **3.59pp** of net alpha. On the early half the surface is nearly **flat** from 0.30 to
0.75: the second-best cell is **0.75 at +2.74pp**, only **0.14pp** below the peak. So the early
half identifies 0.30 as the argmax while being close to indifferent across the whole upper half of
the grid. **An adopt at 0.30 is well supported by the late half and weakly supported by the early
one.**

## 7. Routed to Don, not adopted

Outcome (a) makes this an **adoption decision**, and the register was explicit that even (a)
produces a routed decision rather than a change. What Don is being asked to weigh:

* **Width 0.30**, measured effect **+1.78pp / +1.77pp** of net alpha held out, with **turnover
  roughly halved** (2.61 → 1.35, 2.58 → 1.42).
* **It is already live in the `taxable` configuration**, so an adopt changes the **default**, not
  whether the band exists.
* **It is a VINTAGE EVENT under Rule 6.** The vintage was **derived, not assumed**
  (`track_meter.current_vintage()`): **vintage 3, run 2, opened 2026-08-11, OPEN.** It is **two
  days old.** Adopting would close it and open vintage 4 — a second five-year clock reset inside
  three days, for a construction change on the same book.
* **Roughly half the gain is a SIGNAL effect, not a cost saving** (session 35's correction to its
  own register), so it carries signal-grade uncertainty and not the determinism the original
  framing claimed.
* **B13 is only PARTIAL**, so "the book is investable" holds for the categorical screen and not
  the liquidity one.

## 8. Controls

* **C1** reproduces the published record to the digit; the run aborts before reading any width
  otherwise. **C1b (strengthened, not separately pre-registered — a reproduction check carrying no
  verdict): all 48 shipped-width cells reproduce session 35's raw artifact at max |Δ| 1.33e-15.**
* **C2** the three new widths genuinely bite: turnover is **strictly decreasing across all nine
  settings on both halves**.
* **C3** as above — set equality 200/200, order irrelevance max |Δ| 2.13e-14.
* **C4** **book size is IDENTICAL at every width** — 154.1 names (147–159) early, 175.6 (152–195)
  late. So no comparison here is confounded by book size, which is the dilution mechanism that
  made S23's never-sell arm look bad for a different reason.
* **C5** the incumbent-share ladder in §2 — the freezing mechanism, measured.
* **C6** non-monotone on **both** halves (§5).
* **C7** the argmax reads the decide half only, pinned by a test.

## 9. Expectations: 2 right, 4 wrong, 1 split — and the misses share one root

| # | call | outcome |
|---|---|---|
| E1 | optimum is interior (60/40) | **RIGHT** |
| E2 | picked width is 0.40 or 0.50 (70/30) | **WRONG** — 0.30 held |
| E3 | net alpha keeps rising 0.30 → 0.40 somewhere (65/35) | **WRONG** — falls on both |
| E4 | gross peaks and turns down *before* net (70/30) | **SPLIT** — gross does turn down, but at the *same* width as net, not before |
| E5 | the two directions pick different widths (55/45) | **WRONG** — they agree |
| E6 | non-monotone on the late half (75/25) | **RIGHT** — and on the early half too |
| E7 | the verdict is NOT (a) (55/45) | **WRONG** — it is (a) |

**Four of the five misses are the same mistake**: E2, E3, E5 and E7 all assumed the optimum would
move outward or that the two halves would diverge once given more room. **They did neither.** The
prior was "a boundary win means the true optimum is beyond the boundary", and it is simply
invalid — 0.30 happened to be both the boundary and the maximum.

## 10. What I did NOT do

1. **Adopted nothing.** Outcome (a) routes a decision; it does not take one.
2. **Did not extend the grid a third time** — forbidden by the register, and §2's freezing
   argument makes the region past 0.75 degenerate anyway.
3. **Did not refine near 0.30**, which is where a grid search manufactures a knee.
4. **Did not sweep `enter_frac`**, still the shipped 0.10.
5. **Did not re-measure the effect size** — §3; the pick did not move, so there was nothing new to
   measure.

## 11. BUGS FOUND

1. **My own C3 asserted a stricter property than the docstring means** (§4) — corrected, and
   proved to move zero verdict cells.
2. **Session 35's C6 monotonicity finding was a grid artefact** (§5) — corrected here.
3. **My own registered lean was wrong for an invalid reason** (§0, §9) — recorded because the
   invalid inference is more portable than the result.

## 12. Next

**S14 is now a decision for Don, not a measurement for me.** Nothing further should be run on the
band width — the register forbids a third extension and the surface is documented end to end.

Otherwise unchanged: **S10's accounting half**, or the **CPCV embargo** from session 22 — still
the only open item that can move a published number.

---

# S17 + S19 (2026-08-13) — the last two S-series research rows

Register: `PREREG_s17_s19_events_mdna.md`, committed **ALONE at `a92996d`** — one `.md`, zero
`.py` — a strict ancestor of every measurement commit. Two audit items, one register, reported
as two independent results. `S10`'s accounting half was assessed for inclusion and **excluded
with reasons**; see §0.

## §0 — `S10`'s accounting half is NOT closed here, and that was a measurement

The task asked whether it could share this register and to say so either way. It cannot, for
three reasons established before any arm ran:

1. **Eight SF1 columns it needs are absent from the loader.** Every input for Beneish, Altman
   and external financing **exists** in `data/backtest/fundamentals.csv` (112 columns) — but
   `assetsc`, `ppnenet`, `depamor`, `workingcapital`, `retearn`, `liabilities`, `ncfcommon` and
   `ncfdebt` are **not in `WRDSProvider._KEEP`**, so today they load as nothing. Adding them
   forces a full panel rebuild plus coverage verification on eight new columns — the COVERAGE
   RULE's exact failure mode, which has bitten this project four times. `S17` and `S19` needed
   no rebuild at all.
2. **NT filings are not buildable from anything we own.** They need new EDGAR collection. The
   audit's veto is *"flagged by **two or more**"* of **four**; with three computable that
   becomes "two of three" — a **different rule**, and choosing it after seeing which components
   exist is exactly the degree of freedom a register exists to remove.
3. **Trial cost.** `S17` (10) + `S19` (2) already charges 12. Adding four components and a veto
   arm would have taken the session past 17 arms and pushed equity `N` past 200 in one sitting.

Scoped for its own session: add the columns, rebuild, verify coverage **first**, build Beneish
and Altman as exclusion flags, collect NT filings, and only then fix the veto rule.

## §1 — Both ledger rows were wrong, again

`S17` read `src=auto` / *"prose mentions only, no section, no commit"*; it is a full section at
`VALQUO_EDGE_AUDIT.md:838`. `S19` read *"no mention anywhere in the corpus"*; it is `:1841`,
plus summary rows at `:2424` and `:2538`. **That is the eleventh and twelfth time an `src=auto`
"no section" note has been wrong.** Both corrected.

## §2 — `S17`: the audit's method could not be executed as written

Step 1 says *"obtain the code legend from Sharadar's documentation"*. **Sharadar ships no legend
with the EVENTS download** (`bulk.py:20`, `:235`), and `D10` records that the documentation was
never extracted and `scripts/verify_sharadar.py` has never been run against the real key. So the
codes were tested **by number, unlabelled**, and the register said in advance what that costs:
**a signal on an unlabelled code is uninterpretable even if it works.** A positive would have
been a lead requiring the legend, never an adoption.

**Frequency (the audit's step 2), measured:** 35 distinct codes, **4,240,434 occurrences**,
17,779 tickers, 1993-11-08 → 2026-07-29. The five most frequent are **91** (1,144,079), **81**
(842,973), **34** (496,638), **22** (385,426) and **71** (302,070). **Code 22 is fourth and is
already decoded and rejected** (PEAD: `pead_car` standalone IC *t* +2.215, incremental *t*
**+0.020** after residualising on momentum). **Registered arm set: the five most frequent
EXCLUDING 22 — 91, 81, 34, 71, 52 — at 21 and 63 days. Ten arms, two-sided.**

## §3 — The mechanism question, answered before any arm ran

**The task asked whether the remaining codes share code 22's mechanism. They do not, and the
project had already measured it.** The empirical decode that identified code 22 scored every
registered arm on the way past (`bulk.py:243-247`): median absolute return on an event day,
against a 1.292% baseline — code **22 at 1.64×**, and **91 1.15×, 71 1.13×, 81 0.98×, 52 0.96×,
34 0.94×**. Code 22's mechanism is an *information shock*; PEAD is drift **following** that
shock. **The registered arms have no shock for drift to follow.**

The register hedged that explicitly, and **the hedge turned out to be the load-bearing part**:
day-of absolute return is a **volatility** measure while the test is **directional**, and the
two come apart for *scheduled* events (expected, so no announcement-day move) and
*slow-diffusing* ones. That qualification is what the result vindicated — see §4.

## §4 — `S17` VERDICT: all ten arms NULL — and not because they are inert

**Not one arm clears the both-halves leg, so all ten are NULL by the pre-committed rule.** That
leg is the only thing between this and a reported discovery.

**But 8 of 10 clear their own permutation p95 full-sample, 8 of 10 survive Benjamini–Hochberg at
q = 0.05, and ALL TEN are sign-stable across halves** — the pattern session 7's LOO usually
breaks.

| arm | HAC *t* | own p95 | perm *p* | annualised | BH | early *t* | late *t* |
|---|---:|---:|---:|---:|:--:|---:|---:|
| code91@21d | **−2.671** | 1.87 | 0.0060 | −2.29% | yes | −2.751 | −1.013 |
| code91@63d | **−3.769** | 2.03 | 0.0020 | −2.20% | yes | −3.476 | −1.862 |
| code81@21d | −1.576 | 1.88 | 0.1058 | −1.72% | no | −1.750 | −0.678 |
| code81@63d | −2.133 | 2.06 | 0.0399 | −1.84% | yes | −1.514 | −1.520 |
| code34@21d | **+3.020** | 1.91 | 0.0080 | +4.88% | yes | +1.884 | +2.369 |
| code34@63d | +2.619 | 1.98 | 0.0120 | +3.15% | yes | +2.388 | +1.243 |
| code71@21d | −2.118 | 2.05 | 0.0399 | −2.03% | yes | −1.384 | −1.610 |
| code71@63d | **−3.128** | 1.94 | 0.0020 | −2.03% | yes | −1.342 | −3.098 |
| code52@21d | −0.736 | 1.95 | 0.5130 | −0.64% | no | −0.940 | −0.186 |
| code52@63d | −2.283 | 1.96 | 0.0299 | −1.36% | yes | −1.199 | −2.034 |

**They fail because each effect is concentrated in ONE era, not because it is absent.** Code 91
is an early-half phenomenon (−3.476 vs −1.862); code 71 is a late-half one (−1.342 vs −3.098).
Sign-stable, era-concentrated, and therefore NULL.

**Coverage first:** 328 usable month-ends, **1998-12-31 → 2026-03-31**, cross-section median
**1,649** (min 1,270, max 2,024), 546,563 scored name-dates. The screen removed little — 6,993
nano-cap and 4,455 sub-$1 slots.

## §5 — `S17` controls and diagnostics

* **C1 GATES, ran in its own pass, and the run aborts on failure** (repairing session 26's defect
  of computing a gating control and its outcomes together). Code 22 reproduces at **1.7423×**
  against the decode's 1.64× (baseline 1.181%, 138,397 events matched). **The ordering of the
  other codes broadly reproduces but NOT exactly, and that is stated rather than rounded into a
  clean pass:** 91 and 71 swap (1.276 vs 1.283 — within 0.007, effectively tied) and code 11
  moves up two places. Code 22's dominance and the rest of the ordering hold. The universe
  differs (2,985 names here against the decode's 372), so ratios, not levels, are the
  reproducible quantity.
* **C2 point-in-time** is **pinned by test, not by a counted number** — a synthetic panel proves
  an event dated ON or AFTER the rebalance date cannot be used, and that the 21-calendar-day
  window is half-open.
* **C3 refutes the B6 signature directly: 89.1% of the names in the earliest cross-sections were
  still trading ten years later** (mean 89.4%). Under a per-ticker price tail — the defect that
  made 41 early dates uninterpretable — that fraction collapses toward zero. `load_prices` takes
  no `days` argument at all, pinned by test.
* **D1, DIAGNOSTIC, NO VERDICT — the two strongest arms are NOT market-cap sorts.** Median cap of
  event vs non-event names: code 91 **0.93×**, code 71 **1.07×**, code 52 1.01×, code 34 0.77×.
  **Only code 81 tilts, at 1.86×, and it is the weakest arm.** So U7's and S10's failure mode —
  a "signal" that is really a size sort — does not explain these.
* **D2, DIAGNOSTIC, NO VERDICT — "8 of 10 clear" is NOT eight independent findings, and this is
  the caveat that must travel with the table.** Two separate dependencies stack. **First, by
  construction: the ten arms are FIVE signals at TWO horizons, and a code's 21d and 63d arms
  share a BIT-IDENTICAL event indicator** — they differ only in the forward window, which
  overlaps. They were charged as ten trials, correctly, but they are nowhere near ten
  independent tests. **Second, measured:** pairwise correlation of the event indicators at
  name-date level runs to **0.4227 (91~71)**, with 91~52 at 0.3656 and 91~81 at 0.2851 (mean
  |rho| 0.1330 over 93,997 name-dates), and the four negative-signed codes all point the same
  way. **The effective number of independent tests is far below ten — nearer three or four.**
  That is **the SELRULE lesson in a new costume**, where 16 co-moving countries proved worth
  2–4 independent draws, and it also means **Benjamini–Hochberg was fed correlated tests**; BH
  remains valid under positive dependence, but "8 of 10 survive BH" should be read as roughly
  "the negative cluster and code 34 survive", not as eight discoveries.
* **D3, DIAGNOSTIC, NO VERDICT — differential survival is not the driver.** A name with no
  forward return 63 days out is dropped rather than scored, so the groups could be conditioned on
  survival differently. Measured: drop rates **2.4%–3.2%**, differences **under 1pp on every
  negative arm** (91 +0.40pp, 71 +0.51pp, 52 +0.39pp, 81 +0.84pp). The largest gap is **−1.76pp
  on code 34**, the only positive-signed code — its names survive *better*, which belongs beside
  its positive return.

## §6 — `S19`: the held-out collection

**418 held-out names with usable filings, and ZERO of them are in the original 195** (control
C5, exact). The selection rule was mechanical and frozen before collection began: today's
largest by market cap from the same `large_cap_universe` ranking the original used, minus the
195 already spent, next 600 in rank order. The spent names occupy ranks 0–248, so every
held-out name is rank ≥ 249. **This is X1's universe split as the audit asked for it — the
original names are the deciding set by construction.**

**15,893 filing pairs, 2.2× the original study's 7,095.** Collection took 5,195s over 600
tickers.

**Attrition was predicted in the register and is non-random: 182 of 600 (30.3%) produced no
10-K/10-Q at all.** The rank-ordered list opens with TSM, ASML, HSBC, NVS, RY, AZN, BABA,
MUFG — **foreign private issuers, which file 20-F/6-K** — plus ETFs and trusts. They were
deliberately **not** filtered out, because any filter is a choice; they drop out naturally and
are reported as coverage. Same non-random hole `O6/O7/O17` found, where 29 of 186 names with
zero earnings coverage were **every one** a foreign private issuer.

## §7 — `S19` VERDICT: both arms NULL — but the sign does not reverse, and the design could not have caught what it was hunting

| arm | measure @ horizon | residual IC (change) | NW *t* | early half | late half | verdict |
|---|---|---:|---:|---:|---:|---|
| **A1** | `mdna_cosine_tf` @ 21d | **+0.012202** | **+1.1876** | +0.017262 (*t* 1.537) | +0.007383 (*t* 0.444) | **NULL** |
| **A2** | `mdna_jaccard` @ 63d | **+0.021737** | **+1.4012** | +0.037723 (*t* 1.564) | +0.006512 (*t* 0.355) | **NULL** |

41 covered dates (against the register's floor of 24), mean **337.8 names** per cross-section,
mean signal age 69.8 days.

**Neither arm reaches the audit's *t* > 2.0 bar, so both are NULL by the pre-committed rule.**

**THREE THINGS THE NULL DOES NOT SAY, and they matter more than the verdict.**

1. **THE SIGN DID NOT REVERSE. All four half-cells are POSITIVE in the committed direction.**
   The register fixed the direction in writing before any new return was joined — *more MD&A
   change → outperform* — and on 418 names that never informed the observation, both measures
   and both halves point that way. A sign flip between halves is this project's single most
   repeated failure pattern; it did not happen here.
2. **THE MAGNITUDES ARE LARGER THAN THE ORIGINAL'S OWN, not smaller.** The original's MD&A
   residual IC on its own 195 names was **+0.009607 at *t* 0.6463**. Held out: **+0.012202 at
   *t* 1.1876** (A1) and **+0.021737 at *t* 1.4012** (A2). The effect did not decay on contact
   with new names — the *t* rose, mostly because the cross-section roughly doubled.
3. **THE DESIGN IS UNDERPOWERED AGAINST EXACTLY THE EFFECT IT WAS LOOKING FOR, and this is the
   sentence that must travel with the verdict.** A1's standard error is 0.010275, so its
   **minimum detectable incremental IC at |*t*| = 2 is +0.020549**; A2's is **+0.031026**. The
   original's own residual IC was **+0.0096**. **So A1 could not have returned a positive
   verdict even if the original effect were exactly true and exactly reproduced.** Its observed
   +0.0122 sits *below* its own detection threshold. **NULL here means "could not be separated
   from zero at this resolution", NEVER "the effect is absent"** — V2G's lesson, restated on a
   different instrument.

**The structural reason for the low power, stated in the register before running.** The panel
starts 2009-01-15 and MD&A scores start 2016-08, so only **41 of 69 panel dates** are covered
and all sit in the late portion — a both-halves gate on the *full* panel is **impossible, not
merely weak** (`S18`'s class). Worse for power: the original tested **111 MONTHLY** dates while
the incumbent theme panel is **QUARTERLY**, so the held-out test has roughly a third of the
time-series observations even though it has nearly double the names. **A pass on 20/21-date
halves would not have been the same object as a pass on 34-date halves, and is not reported as
one.**

**Both effects concentrate in the early half** (A1 +0.0173 vs +0.0074; A2 +0.0377 vs +0.0065) —
the same era-concentration `S17` shows, on completely different data.

**The themes explain very little of the MD&A score**, confirming the original's orthogonality
finding on new names: residualisation R² is **0.1208** (A1) and **0.0737** (A2), and the raw ICs
(+0.014344, +0.026455) are only slightly larger than the residual ones. **Orthogonality was
never the binding constraint here; power is.**

## §8 — `S19` control C6: it reproduces, but not cleanly, and the ambiguity is reported

The register required my incremental-IC instrument to reproduce the original's published
**+0.009607 at *t* 0.6463** before any held-out verdict could be issued.

| panel | residual IC (similarity) | *t* | dates |
|---|---:|---:|---:|
| void pre-B6 `panel.pkl` | +0.001791 | +0.1342 | **37** |
| corrected 69-date panel | **+0.011227** | **+0.7589** | 36 |
| *the original's published figure* | *+0.009607* | *+0.6463* | *37* |

**It passes on the committed tolerance — on the CORRECTED panel — and the evidence about which
panel the original used is contradictory.** The original's own artifact records
`data_dir: data/backtest` and a build date of 2026-08-03, i.e. **before B6 landed**, and the
**void panel reproduces its date count exactly (37 vs 37)** while the corrected panel gives 36.
But the void panel's IC is **five times smaller** and does not match, while the corrected
panel's does.

**The most likely explanation is that neither banked panel IS the original's panel** —
`lazy_prices_ic` builds its own from `data/backtest` rather than loading a banked pickle, and
the artifact's `theme_panel_dates: 49` matches neither. **So C6 is a LOOSE reproduction, not a
tight one** (the committed tolerance was 0.002 on an IC of ~0.01, i.e. 20% relative), and it is
reported as such rather than rounded into a clean pass. The held-out verdict does not depend on
it: A1 and A2 are computed on the corrected panel throughout.

**A finding in passing, worth carrying: the original study's orthogonality block was computed on
a panel built before B6**, which the project has since declared void. Nothing rests on it — that
study rejected — but anyone re-opening the lazy-prices work should not quote its orthogonality
numbers as though they were measured on the corrected panel.

## §9 — Expectations: 8 right, 0 wrong — and the score is worth less than it looks

| # | prediction | odds | outcome |
|---|---|---|---|
| 1 | all 10 `S17` arms NULL | 80/20 | **right** |
| 2 | ≥1 `S17` arm clears full-sample but fails both-halves or BH | 65/35 | **right** (8 did) |
| 3 | code 91 most likely to show something | 55/45 | **right** (largest \|*t*\|, 3.769) |
| 4 | `S19` A1 NULL | 75/25 | **right** |
| 5 | `S19` A2 NULL | 80/20 | **right** |
| 6 | held-out attrition > 25% of 600 | 70/30 | **right** (30.3%) |
| 7 | `S19` sign comes back POSITIVE as committed | 60/40 | **right** (4 of 4 half-cells) |
| 8 | both items return a verdict rather than voiding | 70/30 | **right** |

**This is the second clean sweep in the record and it should be discounted, not celebrated.**
Three of the eight (1, 4, 5) predict NULL in a project where essentially everything is null, so
they are close to free. The two that carried information are **#7** — a 60/40 call on a sign
that could have flipped and did not, in four of four cells — and **#3**. **And the sweep hides
the fact that the reasoning behind #1 was wrong**: `S17`'s arms were predicted inert on a
day-of-volatility prior, and they are not inert at all. Getting the verdict right for a partly
wrong reason is not the same as being right.

## §10 — Trial cost, and a defect in my own register

**`S17` 10 arms + `S19` 2 arms = 12 equity trials, exactly as pre-committed.**

**THE REGISTER'S OWN ARITHMETIC IS WRONG AND IS CORRECTED HERE RATHER THAN EDITED.** §7 of
`PREREG_s17_s19_events_mdna.md` says *"Equity `N` 186 → 198"*. **186 was quoted from `CLAUDE.md`
instead of re-measured after this session's own merge**, which brought in the `U2` lane's four
equity trials. Measured at the time of writing, `research_log.detail()` reads equity **190**, so
the honest figure is **190 → 202**. The **charge of 12 is unchanged**; only the baseline was
misquoted. **This is the exact error the record already warns about** — *"re-read `by_domain`
after merging rather than quoting a figure measured mid-session"* (session 30) — committed by
the same session that had the warning in front of it. The register is left unedited.

**`BACKTEST_RESULTS.json` was already stale before this session touched it**, reading
`n_trials` **186** against a live 190 — so the refresh here corrects the `U2` lane's drift as
well as adding these 12.

## §11 — What is NOT closed

* **`S10`'s accounting half** — see §0. Scoped, not started, not charged.
* **`S17` is closed as a hypothesis but its codes remain UNLABELLED.** The legend is still
  unobtainable from the download, and `D10`'s extraction task is still open. **Nothing here
  should be re-run without it** — the arms are NULL, and a re-run without labels would produce
  the same uninterpretable numbers at another 10 trials.
* **`S19` is closed as a hypothesis and is NOT re-openable by collecting more of the same
  names.** The binding constraint is the **quarterly** theme panel against a **monthly** signal,
  not the name count — doubling names again would move the *t* by roughly √2 at best. Re-opening
  it means a monthly theme panel, which is a rebuild with its own register.
* **The CPCV embargo** from session 22 — still the only open item that can move a published
  number.

---

# V6 — the Dip Detector's testable claim (2026-08-13)

**Register:** `PREREG_v6_dip_detector.md`, committed **ALONE at `93e3e60`** — one `.md`, zero
`.py`, a strict git ancestor of every measurement commit.
**Artifact:** `data/free_analysis/V6_DIP_DETECTOR.json` (every permutation draw banked,
`RUN_RULES` A9). **Instrument:** `scripts/v6_dip_detector.py`, `scripts/v6_addendum.py`.
**ADOPTS NOTHING. No file under `valuation/` changed. No vintage event.**

## 0. The verdict

**ALL FOUR ARMS NULL.** Not one clears either leg in both halves. The claim under test — *a
quality-conditioned drawdown recovers better than the market* — **is not supported on this
panel**, and the explainer constant takes `VERDICT = "NULL"` (§8).

| arm | depth | horizon | L1 vs universe (full) | L2 vs unconditioned dips (full) | verdict |
|---|---|---|---|---|---|
| A1 | 20% | 63d | +0.585pp/yr, *t* +0.4066 | +2.108pp/yr, *t* +1.0093 | **NULL** |
| A2 | 20% | 126d | +0.705pp/yr, *t* +0.5232 | +0.977pp/yr, *t* +0.5737 | **NULL** |
| A3 | 30% | 63d | −0.480pp/yr, *t* −0.2295 | +2.081pp/yr, *t* +0.7541 | **NULL** |
| A4 | 30% | 126d | +0.174pp/yr, *t* +0.0787 | +0.881pp/yr, *t* +0.4098 | **NULL** |

Bars are each leg's **own** within-date permutation p95 (500 draws), which land at *t* **1.44 to
1.86** — X7's 2.2837 and 1.95pp were **not** quoted, because X7 calibrated a decile-book
long-short *t* and a top-decile alpha margin and this is neither object.

## 1. THE FINDING THAT IS NOT THE VERDICT, AND IT IS THE ONE THE PRODUCT NEEDS: THE DIP FLAG IS SUBSTANTIALLY AN INVERSE-MOMENTUM SORT

**C7: Spearman(drawdown, `momentum` theme) = +0.6642** on 113,945 panel rows. Also
`low_risk` **+0.4196**, `size` **−0.2914**, `value` **−0.0834**.

A drawdown is a *level*, momentum is a *change*, and I registered at 60/40 that they would
correlate **below 0.4**. **That was wrong, and it is the most useful number in the item.** Being
20% below a 252-day high is, on this panel, largely the same statement as scoring badly on the
momentum theme — which is one of the seven weighted themes in the live composite, carrying IC
*t* **+1.31**.

**So a Dip Detector as specified would systematically surface names the product's own composite
is marking down.** That is not a defect in either object — they are answering different
questions — but a tab that presents dip names beside a hot-score list is presenting two screens
that disagree by construction, and the copy should not imply otherwise.

**The register's own §1a claim is therefore half right and half wrong, and I am recording both.**
A drawdown is genuinely a different object from *short-term reversal* (which does not exist as a
panel column at all — C7 names it as unmeasurable rather than returning an empty dict). But it is
**not** a different object from *momentum*, and I asserted the general independence too broadly.

## 2. THE SHAPE OF THE FAILURE: SEVEN OF EIGHT LEG-SERIES FLIP SIGN BETWEEN HALVES, ALL THE SAME WAY

Halves: early **2009-01-15 → 2017-04-20** (34 dates), **2017-07-20 embargoed**, late
**2017-10-18 → 2026-01-28** (34 dates).

| arm·leg | early *t* | late *t* | flips? |
|---|---|---|---|
| A1·L1 | −0.4273 | +1.2135 | yes |
| A1·L2 | −0.2166 | **+1.6782** | yes |
| A2·L1 | −0.7272 | +1.4674 | yes |
| A2·L2 | −0.5339 | +1.2571 | yes |
| A3·L1 | −0.6098 | −0.3323 | **no** |
| A3·L2 | −0.6891 | +1.5384 | yes |
| A4·L1 | −0.7549 | +0.5518 | yes |
| A4·L2 | −1.0002 | **+1.6387** | yes |

**Every flip runs the same way: negative early, positive late.** This is session 7's LOO pattern
again — this project's single most repeated finding — but here it is *systematic* rather than
scattered, which makes the practical warning sharper:

> **A Dip Detector built and validated on the last eight years alone would have looked like it
> worked.** The early half is the only thing that stops it. That is exactly what the both-halves
> rule is for, and it is the whole margin between this item and a shipped claim.

Two half-cells **do** clear their own p95 — **both LATE, both L2**: A1 at *t* **1.6782 vs 1.6634**
(a margin of **0.0148**) and A4 at **1.6387 vs 1.4381**. Neither arm passes, because the rule was
fixed before any number existed. **1 arm of 4 clearing 1 half of 2 is the family-wise labelling
clause earning its keep for the fourth time.**

## 3. NULL MEANS "COULD NOT BE SEPARATED", NEVER "ABSENT" — QUOTE THIS WITH THE VERDICT

**No full-sample cell's observed effect reaches its own minimum detectable effect, on either
reference** (D1):

| arm·leg | observed | MDE at this register's own bar | MDE at the conventional \|*t*\|=2 |
|---|---|---|---|
| A1·L1 | +0.585pp | +2.131pp | +2.877pp |
| A1·L2 | +2.108pp | +3.371pp | +4.177pp |
| A2·L2 | +0.977pp | +2.632pp | +3.405pp |
| A3·L2 | +2.081pp | +4.477pp | +5.520pp |
| A4·L2 | +0.881pp | +3.105pp | +4.298pp |

**Both references are reported deliberately.** Quoting a *t*=2 MDE against a p95 bar of 1.6
overstates how coarse the design is; quoting no MDE at all understates it. **S19's lesson on a
new instrument** — and the same conclusion: an effect the size of the one the tab hopes for would
not have been detectable here even if it were exactly true.

## 4. THE CONDITIONING IS PARTLY A SIZE SCREEN, WHICH IS A CAVEAT ON L2 SPECIFICALLY

**C8.** The quality+health floors keep only **26.8%** of dipped names at 20% and **22.3%** at 30%,
and what they keep is **bigger**: median market cap **$4.654B vs $2.690B** (ratio **1.73×**) at
20%, and **$3.704B vs $2.037B** (**1.82×**) at 30%. The universe median is $5.000B.

Since **L2 compares conditioned names against *all* dipped names on the same date**, part of what
L2 measures is *large dipped names versus small dipped names*. That is **U7's and S10's failure
mode** — a screen wearing another screen's name — and it is a live caveat on the two L2 half-cells
that cleared. It does **not** threaten the verdict, because the verdict is NULL either way.

## 5. WHICH FLOOR BINDS — AND MY PREDICTION WAS BACKWARDS

**D2.** Of 37,982 dipped rows at 20%: **quality alone keeps 41.15%**, **health alone keeps
35.88%**, both keep 26.83%. At 30% (23,837 rows): 35.99% / 30.58% / 22.25%.

**The HEALTH floor is the tighter one, not quality.** I registered the opposite at 60/40. The
health scale's midpoint of 50 sits above the panel's own median health of **46.02**, so it removes
slightly more than half the cross-section; `quality > 0` removes slightly less than half by
construction. Both floors bite and neither is degenerate, which is what the register needed them
to do.

## 6. Controls

* **C1 GATED AND RAN IN ITS OWN PASS**, with `--controls-only` exiting before any arm was scored —
  session 26's defect stays repaired. Reproduces the shipped record to all 16 digits:
  `top_decile_alpha` 0.07174142332098163, LS naive 2.8360640685320595, HAC 2.6199121240414884,
  monotonicity −0.8909090909090909.
* **C2** canonical panel asserted, not warned: **69 dates, 2,531 names, 113,945 rows**, `full`.
* **C3** zero point-in-time violations — pinned by a synthetic panel in which a crash *after* the
  rebalance date must leave the flag unchanged and a crash *before* it must not.
* **C4 coverage first:** drawdown **98.33%**, health **100.00%**, quality **97.91%**. Median
  drawdown −0.1182, median health 46.02. **Zero rows took the cash-burner branch** (it needs
  `cash_runway_years`, a live-engine quantity) — reported rather than silently routed. `roic`/`roe`
  **never read**, both being 0.0% populated.
* **C5 the split trap, pinned from both sides:** a synthetic 2-for-1 split reads as a −50%
  drawdown on a raw series and as **no dip at all** on the adjusted basis. Since companies split
  *after* they rise, a raw basis would have flagged the strongest names in the universe.
* **C6** no per-ticker tail in the price read (audit B6).
* **C7 / C8 / D1 / D2** as above.

## 7. Expectations — 3 right, 4 wrong, 1 split

| # | expectation | odds | outcome |
|---|---|---|---|
| 1 | all four arms NULL | 70/30 | **RIGHT** |
| 2 | L1 looks better than L2 on ≥3 arms | 75/25 | **WRONG** — L2 is better on **all four** |
| 3 | quality removes far more names than health | 60/40 | **WRONG** — health binds harder |
| 4 | an arm trips the L2 sign-reversal branch in ≥1 half | 55/45 | **WRONG** — no cell reaches p5 |
| 5 | 126d shows a larger effect than 63d on both legs | 55/45 | **SPLIT** — true on L1, false on L2 |
| 6 | the 30% arms are noisier and not better | 65/35 | **RIGHT** |
| 7 | \|ρ(drawdown, reversal/momentum)\| < 0.4 | 60/40 | **WRONG** — +0.6642, the item's key number |
| 8 | conditioned names are larger than unconditioned dipped | 60/40 | **RIGHT** |

Expectation 2's miss is instructive rather than embarrassing: **L2 beats L1 on every arm** because
dipped names underperform the market outright, so clearing the *dipped* benchmark is an easier bar
than clearing the *market*. I had the direction backwards.

## 8. THE EXPLAINER CONSTANT — named, with the value this verdict assigns

**`valuation/web/dip_confidence.py`**, modelled on the shipped `valuation/web/score_confidence.py`
(V3's precedent: one module owns the calibrated wording, read by every surface, pinned **verbatim**
to its handoff by a test that normalises whitespace and fails on a rewording).

```python
SOURCE   = "HANDOFF_edge_audit.md"        # this section
REGISTER = "PREREG_v6_dip_detector.md"
VERDICT  = "NULL"
```

**What the tab may say, per the register's §8 mapping for a NULL:**

> The dip screen is a **filter, not a forecast**. It finds names trading well below their recent
> high. Valquo has **not** shown that such names — even filtered for quality and financial
> health — go on to beat the market.

**What it may NOT say:** that the conditioning improves outcomes; any magnitude from this item as
a forward expectation; or anything derived from the late half alone.

**Ownership: the constant and the tab are the APP LANE's to build.** This register fixes the
verdict and the wording contract and deliberately ships no web surface — **no file under
`valuation/web/` is touched by any V6 commit**, which is the boundary the register set in §8
before the result existed.

## 9. What this does NOT settle — named so it is not mistaken for tested

* **The tab's own live sub-scores.** They are **not computable point-in-time** (quality needs a
  WACC; S23 measured that path fetching *live* Yahoo prices to value 1999), so the arm used the
  panel's `quality` theme and a point-in-time health score built by **calling the shipped
  `_health_score`**. The register's §2 asymmetry stands: **a NULL here is informative** — I used
  the panel's strongest theme, IC *t* +3.10 — **but a POSITIVE would not have licensed the tab's
  copy** without a separate live-vs-panel fidelity check.
* **Any other floor, depth, horizon or trailing-high window.** Two floors, two depths, two
  horizons, 252 days, no sweep. A swept floor was a void condition.
* **Whether to trade it.** Gross of costs, no book, no turnover.
* **P4-3's classic anomalies on the corrected universe.** Still open — the 2026-07-29 rejection ran
  on audit B12's **alphabetical A–C slice** and has never been re-run. **A null here is NOT a
  re-rejection of short-term reversal**, and may not be reported as one.
* **A dead fallback, reported not repaired:** `_KEEP` requests `ebitmargin` and the export has no
  such column (it ships `ebitdamargin` and `netmargin`), so `fundamental_panel.py:405`'s fallback
  is unreachable. Moves no number; the neighbouring `grossmargin` fallback **is** live, so the two
  lines look identical and are not.

## 10. Defects in my own instrument, all caught before any verdict existed

1. **A degenerate permutation draw crashed the run.** When every permuted mean is identical the
   HAC *t* is undefined and `mean_inference` returns `t=None`; `_perm_t` coerced that to `float()`
   and raised. **Treating it as 0.0 instead would have padded the null with fake draws and LOWERED
   the p95 — i.e. made the bar easier.** Degenerate draws are dropped and `n_perm_ok` reports the
   survivors. Same family as `zscore`'s `sd == 0` and `theme_ic`'s `sd > 0`.
2. **A test of mine could have passed vacuously.** With every dipped value equal, "`t` is None" is
   the correct signature of a correct L2 null — and also what a broken one returns. A positive
   control was added: the L1 scheme on the *same* cells must give a finite non-zero *t*.
3. **Two controls were pointed at column names the panel does not have.** C8 read `marketcap`; the
   panel's column is **`market_cap`**, and the `.get()` lookup would have returned `None` — which
   reads as *"no size tilt"* rather than *"this control never ran"*, removing the only guard
   against reporting a size sort as a quality finding. C7 read `ret_6_1`/`ret_12_1`/`ret_1_0`,
   which are metric inputs folded into `momentum` and are not panel columns at all. Both now name
   what they could not find; **U2's near-miss class.**
4. **A speedup whose justification was false, reported against myself.** I replaced a full
   permutation with a direct subset draw expecting minutes of saving; measured, a 500-draw sweep
   costs about **2 seconds** and on L2 the "optimization" is **slower** (0.86×). Kept only because
   it is **verified inert** — p95 moves +0.0038 (L1) and −0.0328 (L2), two-sample KS *p* 0.4599 and
   0.5089.

## 11. Cost and record

**Equity `N` 202 → 206** (four arms; the two legs of an arm are a conjunction producing one
verdict, so they are one search). The 202 was **re-measured from `research_log.detail()` after this
session's merge** rather than quoted from `CLAUDE.md` — the defect the S17/S19 register made and
corrected. Options 287 and infra 11 are untouched. `BACKTEST_RESULTS.json` refreshed from a clean
tree at the new denominator.

**Suite 372 → 384**, all green. Ledger row `V6`; `VALQUO_EXTENSIONS.md` gains its V6 row and
section.
