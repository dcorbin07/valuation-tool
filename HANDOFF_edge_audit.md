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
